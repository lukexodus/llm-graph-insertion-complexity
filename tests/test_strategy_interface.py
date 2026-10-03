"""
tests/test_strategy_interface.py — INFRA-002 conformance test suite
====================================================================
Tests for Embedder implementations, strategy interface contract, and insert_node.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np
import pytest

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    InsertionMetrics,
    InsertionResult,
    NarrowingStrategy,
    Shortlist,
    insert_node,
)


# ===========================================================================
# Test In-Test Mocks / Fakes
# ===========================================================================

class TinyFakeStrategy:
    """A minimal deterministic narrowing strategy for conformance testing.

    Shortlists up to `top_k` existing nodes closest to the new node by
    cosine similarity of fake embeddings.
    """

    def __init__(self, top_k: int = 2, seed: int = 42) -> None:
        self.name = "tiny_fake"
        self.top_k = top_k
        self.seed = seed
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None
        self._node_embeddings: dict[str, np.ndarray] = {}
        self._last_comparisons: int = 0

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder
        self._node_embeddings = {}
        for node in graph.nodes():
            self._node_embeddings[node] = embedder.embed(node)

    def shortlist(self, new_name: str) -> Shortlist:
        if not self._node_embeddings or self.top_k == 0:
            self._last_comparisons = 0
            return Shortlist(candidates=(), scores=())

        assert self._embedder is not None
        new_vec = self._embedder.embed(new_name)
        sims = []
        for name, vec in self._node_embeddings.items():
            sim = float(np.dot(new_vec, vec))
            sims.append((name, sim))

        self._last_comparisons = len(sims)
        # Sort descending by similarity, then ascending by name for determinism
        sims.sort(key=lambda x: (-x[1], x[0]))
        selected = sims[: self.top_k]
        candidates = tuple(name for name, _ in selected)
        scores = tuple(score for _, score in selected)
        return Shortlist(candidates=candidates, scores=scores)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        assert self._embedder is not None
        self._node_embeddings[new_name] = self._embedder.embed(new_name)

    def config(self) -> dict[str, Any]:
        return {"top_k": self.top_k, "seed": self.seed}

    def diagnostics(self) -> dict[str, Any]:
        return {"comparisons": self._last_comparisons}


class FakeDecisionStep:
    """Deterministic fake decision step for testing.

    Establishes an edge (candidate -> new_name) for any candidate with
    name alphabetically before new_name; otherwise (new_name -> candidate).
    """

    def __init__(self, make_edge: bool = True) -> None:
        self.make_edge = make_edge
        self.calls: int = 0

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        self.calls += 1
        t0 = time.perf_counter()
        edges = []
        if self.make_edge:
            for cand in candidates:
                if cand < new_name:
                    # cand is prereq of new_name (canonical prereq -> dependent)
                    edges.append((cand, new_name))
                else:
                    edges.append((new_name, cand))
        elapsed = time.perf_counter() - t0
        return DecisionOutcome(
            edges=tuple(edges),
            llm_calls=len(candidates),
            llm_seconds=elapsed,
        )


# ===========================================================================
# 1. Embedder Tests
# ===========================================================================

class TestEmbedder:
    def test_fake_embedder_dimension_and_norm(self):
        emb = FakeEmbedder(dim=32, seed=123)
        v = emb.embed("hash_table")
        assert isinstance(v, np.ndarray)
        assert v.shape == (32,)
        assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-5)

    def test_fake_embedder_determinism(self):
        emb1 = FakeEmbedder(dim=32, seed=42)
        emb2 = FakeEmbedder(dim=32, seed=42)
        v1 = emb1.embed("linked_list")
        v2 = emb2.embed("linked_list")
        assert np.array_equal(v1, v2)

    def test_fake_embedder_embed_many(self):
        emb = FakeEmbedder(dim=16, seed=42)
        texts = ["graph", "tree", "pointer"]
        mat = emb.embed_many(texts)
        assert mat.shape == (3, 16)
        for i, text in enumerate(texts):
            assert np.array_equal(mat[i], emb.embed(text))

    def test_metered_embedder_accounting(self):
        raw = FakeEmbedder(dim=16)
        meter = MeteredEmbedder(raw)
        assert meter.calls == 0
        assert meter.texts_embedded == 0
        assert meter.cumulative_seconds == 0.0

        meter.embed("a")
        assert meter.calls == 1
        assert meter.texts_embedded == 1
        assert meter.cumulative_seconds > 0.0

        meter.embed_many(["b", "c", "d"])
        assert meter.calls == 2
        assert meter.texts_embedded == 4

        meter.reset()
        assert meter.calls == 0
        assert meter.texts_embedded == 0
        assert meter.cumulative_seconds == 0.0


# ===========================================================================
# 2. Conformance Tests for Strategy & insert_node
# ===========================================================================

class TestStrategyConformance:
    """Reusable conformance test suite for candidate-narrowing strategies."""

    @pytest.fixture
    def initial_graph(self) -> ConceptGraph:
        g = ConceptGraph(domain_context="data structures and algorithms")
        g.add_node("pointer")
        g.add_node("linked_list")
        g.add_node("graph")
        g.add_node("recursion")
        g.add_prereq_edge("pointer", "linked_list")
        return g

    def test_shortlist_is_subset_and_excludes_new_node(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, embedder)

        res = strat.shortlist("dijkstra_algorithm")
        existing_nodes = set(initial_graph.nodes())

        assert len(res.candidates) <= 2
        for cand in res.candidates:
            assert cand in existing_nodes
            assert cand != "dijkstra_algorithm"
        # No duplicates
        assert len(res.candidates) == len(set(res.candidates))

    def test_shortlist_does_not_mutate_graph(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, embedder)

        n_before = initial_graph.num_nodes()
        e_before = initial_graph.num_edges()

        _ = strat.shortlist("dijkstra_algorithm")

        assert initial_graph.num_nodes() == n_before
        assert initial_graph.num_edges() == e_before
        assert not initial_graph.has_node("dijkstra_algorithm")

    def test_new_name_already_in_graph_raises(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, embedder)
        decision_step = FakeDecisionStep()

        with pytest.raises(ValueError, match="already exists"):
            insert_node(strat, initial_graph, decision_step, "pointer")

    def test_same_seed_gives_same_shortlist(self, initial_graph):
        embedder1 = FakeEmbedder(dim=16, seed=99)
        strat1 = TinyFakeStrategy(top_k=3, seed=99)
        strat1.setup(initial_graph, embedder1)

        embedder2 = FakeEmbedder(dim=16, seed=99)
        strat2 = TinyFakeStrategy(top_k=3, seed=99)
        strat2.setup(initial_graph, embedder2)

        sl1 = strat1.shortlist("hash_table")
        sl2 = strat2.shortlist("hash_table")

        assert sl1.candidates == sl2.candidates
        assert sl1.scores == sl2.scores

    def test_repeated_inserts_see_previous_nodes(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(embedder)
        strat = TinyFakeStrategy(top_k=3, seed=42)
        strat.setup(initial_graph, meter)
        decision_step = FakeDecisionStep(make_edge=True)

        res1 = insert_node(strat, initial_graph, decision_step, "hash_table", meter)
        assert initial_graph.has_node("hash_table")
        assert initial_graph.num_nodes() == 5

        # Second insert should be able to shortlist the newly added node
        res2 = insert_node(strat, initial_graph, decision_step, "heap", meter)
        assert initial_graph.has_node("heap")
        assert initial_graph.num_nodes() == 6
        assert res2.metrics.n_before == 5

    def test_edges_involve_new_node_and_are_canonical(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, embedder)
        decision_step = FakeDecisionStep(make_edge=True)

        new_concept = "dijkstra_algorithm"
        res = insert_node(strat, initial_graph, decision_step, new_concept)

        for prereq, dependent in res.edges:
            assert new_concept in (prereq, dependent)
            assert initial_graph.has_prereq_edge(prereq, dependent)

    def test_edge_not_involving_new_node_raises(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, embedder)

        class IllegalEdgeDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                # Returns an edge between two existing nodes, not involving new_name
                return DecisionOutcome(edges=(("pointer", "graph"),), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError, match="does not involve inserted node"):
            insert_node(strat, initial_graph, IllegalEdgeDecisionStep(), "dijkstra_algorithm")

    def test_empty_shortlist_legal_and_skips_decision_calls(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = TinyFakeStrategy(top_k=0, seed=42)  # top_k=0 produces empty shortlist
        strat.setup(initial_graph, embedder)
        decision_step = FakeDecisionStep()

        res = insert_node(strat, initial_graph, decision_step, "hash_table")

        assert len(res.shortlist.candidates) == 0
        assert len(res.edges) == 0
        assert res.metrics.llm_calls == 0
        assert res.metrics.decide_s == 0.0
        assert decision_step.calls == 0
        assert initial_graph.has_node("hash_table")

    def test_timing_and_metrics_consistency(self, initial_graph):
        embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(embedder)
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, meter)
        meter.reset()  # setup is untimed per [D-25]

        decision_step = FakeDecisionStep(make_edge=True)
        res = insert_node(strat, initial_graph, decision_step, "bloom_filter", meter)

        m = res.metrics
        assert m.n_before == 4
        assert m.shortlist_size == 2
        assert m.embedding_calls > 0
        assert m.embed_s >= 0.0
        assert m.shortlist_s >= m.embed_s
        assert m.decide_s >= 0.0
        assert m.update_s >= 0.0
        # Total wall clock must be at least the sum of components
        assert m.total_s >= (m.shortlist_s + m.decide_s + m.update_s) * 0.95
        assert "comparisons" in m.extra
        assert m.extra["comparisons"] == 4
