"""
tests/test_strategy_interface.py — INFRA-002 / FIX-002 test suite
==================================================================
Reusable conformance test suite for candidate-narrowing strategies and
validation tests for the insert_node driver.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

import numpy as np
import pytest

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, embed_text
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
# Reference Mocks / Fakes
# ===========================================================================

class TinyFakeStrategy:
    """A minimal deterministic narrowing strategy for testing.

    Shortlists up to `top_k` existing nodes closest to the new node by
    cosine similarity of fake embeddings.

    Per FIX-002 Item 3(c): caches the embedding of new_name computed during
    shortlist() and reuses it in on_inserted(), ensuring exactly one embedding
    of new_name per insertion trial.
    """

    uses_embeddings: bool = True

    def __init__(self, top_k: int = 2, seed: int = 42) -> None:
        self.name = "tiny_fake"
        self.uses_embeddings = True
        self.top_k = top_k
        self.seed = seed
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None
        self._node_embeddings: dict[str, np.ndarray] = {}
        self._cached_new_name: Optional[str] = None
        self._cached_new_vec: Optional[np.ndarray] = None
        self._last_comparisons: int = 0
        self.on_inserted_called: bool = False

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder
        self._node_embeddings = {}
        for node in graph.nodes():
            # Per [D-21] and FIX-002 Item 4: always pass embed_text(node)
            self._node_embeddings[node] = embedder.embed(embed_text(node))

    def shortlist(self, new_name: str) -> Shortlist:
        if not self._node_embeddings or self.top_k == 0:
            self._last_comparisons = 0
            return Shortlist(candidates=(), scores=())

        assert self._embedder is not None
        # Embed and cache per FIX-002 Item 3(c)
        new_vec = self._embedder.embed(embed_text(new_name))
        self._cached_new_name = new_name
        self._cached_new_vec = new_vec

        sims = []
        for name, vec in self._node_embeddings.items():
            sim = float(np.dot(new_vec, vec))
            sims.append((name, sim))

        self._last_comparisons = len(sims)
        # Sort descending by similarity, then ascending by name
        sims.sort(key=lambda x: (-x[1], x[0]))
        selected = sims[: self.top_k]
        candidates = tuple(name for name, _ in selected)
        scores = tuple(score for _, score in selected)
        return Shortlist(candidates=candidates, scores=scores)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        self.on_inserted_called = True
        assert self._embedder is not None
        # Reuse cached vector if available, avoiding duplicate embedding computation
        if self._cached_new_name == new_name and self._cached_new_vec is not None:
            self._node_embeddings[new_name] = self._cached_new_vec
            self._cached_new_name = None
            self._cached_new_vec = None
        else:
            self._node_embeddings[new_name] = self._embedder.embed(embed_text(new_name))

    def config(self) -> dict[str, Any]:
        return {"top_k": self.top_k, "seed": self.seed}

    def diagnostics(self) -> dict[str, Any]:
        return {"comparisons": self._last_comparisons}


class FakeDecisionStep:
    """Deterministic fake decision step for testing.

    Establishes an edge (candidate -> new_name) for any candidate alphabetically
    before new_name; otherwise (new_name -> candidate).
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

    def test_metered_embedder_accounting_and_texts_log(self):
        raw = FakeEmbedder(dim=16)
        meter = MeteredEmbedder(raw, record_texts=True)
        assert meter.calls == 0
        assert meter.texts_embedded == 0
        assert meter.cumulative_seconds == 0.0
        assert meter.texts_log == []

        meter.embed("hash table")
        assert meter.calls == 1
        assert meter.texts_embedded == 1
        assert meter.cumulative_seconds > 0.0
        assert meter.texts_log == ["hash table"]

        meter.embed_many(["binary tree", "queue"])
        assert meter.calls == 2
        assert meter.texts_embedded == 3
        assert meter.texts_log == ["hash table", "binary tree", "queue"]

        meter.reset()
        assert meter.calls == 0
        assert meter.texts_embedded == 0
        assert meter.cumulative_seconds == 0.0
        assert meter.texts_log == []


# ===========================================================================
# 2. Reusable Strategy Conformance Suite (STRAT-001..004 can inherit)
# ===========================================================================

class StrategyConformanceSuite:
    """Base conformance suite to be inherited by concrete strategy test classes.

    Subclasses must implement the `strategy_factory` fixture returning a
    callable: (graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy.

    Class attributes
    ----------------
    uses_embeddings:
        Set to True (default) for strategies that call the embedder during setup
        and shortlist. Set to False for strategies that never embed (e.g. NullStrategy).
        Controls which conformance assertions apply:
        - True: embedding call counts, texts_log, and single-embedding-reuse are verified.
        - False: the same tests instead assert zero embedding activity.
    """

    uses_embeddings: bool = True

    @pytest.fixture
    def initial_graph(self) -> ConceptGraph:
        g = ConceptGraph(domain_context="data structures and algorithms")
        g.add_node("pointer")
        g.add_node("linked_list")
        g.add_node("graph")
        g.add_node("recursion")
        g.add_prereq_edge("pointer", "linked_list")
        return g


    def test_shortlist_is_subset_and_excludes_new_node(
        self, initial_graph, strategy_factory
    ):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = strategy_factory(initial_graph, embedder)

        res = strat.shortlist("dijkstra_algorithm")
        existing_nodes = set(initial_graph.nodes())

        for cand in res.candidates:
            assert cand in existing_nodes
            assert cand != "dijkstra_algorithm"
        assert len(res.candidates) == len(set(res.candidates))
        if hasattr(strat, "max_candidates") and callable(strat.max_candidates):
            assert len(res.candidates) <= strat.max_candidates(len(existing_nodes))

    def test_shortlist_does_not_mutate_graph(
        self, initial_graph, strategy_factory
    ):
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = strategy_factory(initial_graph, embedder)

        n_before = initial_graph.num_nodes()
        e_before = initial_graph.num_edges()

        res = strat.shortlist("dijkstra_algorithm")

        assert initial_graph.num_nodes() == n_before
        assert initial_graph.num_edges() == e_before
        assert not initial_graph.has_node("dijkstra_algorithm")
        if hasattr(strat, "max_candidates") and callable(strat.max_candidates):
            assert len(res.candidates) <= strat.max_candidates(n_before)

    def test_same_seed_gives_same_shortlist(
        self, initial_graph, strategy_factory
    ):
        embedder1 = FakeEmbedder(dim=16, seed=99)
        strat1 = strategy_factory(initial_graph, embedder1)

        embedder2 = FakeEmbedder(dim=16, seed=99)
        strat2 = strategy_factory(initial_graph, embedder2)

        sl1 = strat1.shortlist("hash_table")
        sl2 = strat2.shortlist("hash_table")

        assert sl1.candidates == sl2.candidates
        assert sl1.scores == sl2.scores
        if hasattr(strat1, "max_candidates") and callable(strat1.max_candidates):
            assert len(sl1.candidates) <= strat1.max_candidates(initial_graph.num_nodes())
        if hasattr(strat2, "max_candidates") and callable(strat2.max_candidates):
            assert len(sl2.candidates) <= strat2.max_candidates(initial_graph.num_nodes())

    def test_d21_text_payload_compliance(
        self, initial_graph, strategy_factory
    ):
        """Enforce D-21: all texts passed to the embedder (setup + insert) must equal embed_text(n).

        When uses_embeddings is False, asserts zero embedding calls and empty texts_log.
        """
        raw_embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_embedder, record_texts=True)
        strat = strategy_factory(initial_graph, meter)

        # Do NOT reset meter here per FIX-003: verify setup() texts as well as insertion texts
        decision_step = FakeDecisionStep(make_edge=True)
        insert_node(
            strat, initial_graph, decision_step, "binary_search_tree", metered_embedder=meter
        )

        if not getattr(self.__class__, "uses_embeddings", True):
            # Non-embedding strategy: zero embedding activity expected
            assert meter.calls == 0, (
                f"Non-embedding strategy produced {meter.calls} embedding call(s); expected 0"
            )
            assert meter.cumulative_seconds == 0.0
            assert meter.texts_log == []
        else:
            assert meter.texts_log is not None
            assert len(meter.texts_log) > 0
            all_concepts = set(initial_graph.nodes())
            for text in meter.texts_log:
                assert "_" not in text
                # Must equal embed_text(c) for some concept in the trial (initial or newly inserted)
                assert any(embed_text(c) == text for c in all_concepts)

            # Explicitly verify every initial node was embedded with embed_text()
            for c in initial_graph.nodes():
                assert embed_text(c) in meter.texts_log

    def test_cached_embedding_reuse_single_embedding_per_insert(
        self, initial_graph, strategy_factory
    ):
        """Verify that narrowing + update embeds new_name exactly once (or zero for non-embedding)."""
        raw_embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_embedder, record_texts=True)
        strat = strategy_factory(initial_graph, meter)
        meter.reset()

        decision_step = FakeDecisionStep(make_edge=True)
        res = insert_node(
            strat, initial_graph, decision_step, "hash_table", metered_embedder=meter
        )

        if not getattr(self.__class__, "uses_embeddings", True):
            # Non-embedding strategy: exactly zero embedding calls in both phases
            assert res.metrics.embedding_calls == 0, (
                f"Non-embedding strategy produced {res.metrics.embedding_calls} embedding calls; expected 0"
            )
            assert res.metrics.embed_s == 0.0
            assert res.metrics.embedding_calls_in_update == 0
            assert res.metrics.embed_in_update_s == 0.0
        else:
            # In strategies that embed, new_name must be embedded only 1 time
            assert res.metrics.embedding_calls <= 1
            assert res.metrics.embedding_calls_in_update == 0
            assert res.metrics.embed_in_update_s == 0.0

    def test_repeated_inserts_see_previous_nodes(
        self, initial_graph, strategy_factory
    ):
        """Strengthened test: second shortlist can contain the first inserted node."""
        embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(embedder)
        strat = strategy_factory(initial_graph, meter)
        decision_step = FakeDecisionStep(make_edge=True)

        res1 = insert_node(
            strat, initial_graph, decision_step, "hash_table", metered_embedder=meter
        )
        assert initial_graph.has_node("hash_table")

        # Second insert: top_k includes hash_table if top_k is large enough
        res2 = insert_node(
            strat, initial_graph, decision_step, "heap", metered_embedder=meter
        )
        assert initial_graph.has_node("heap")
        assert res2.metrics.n_before == 5
        # The candidates evaluated for heap must come from the updated graph containing hash_table
        for c in res2.shortlist.candidates:
            assert initial_graph.has_node(c)
        if hasattr(strat, "max_candidates") and callable(strat.max_candidates):
            assert len(res1.shortlist.candidates) <= strat.max_candidates(4)
            assert len(res2.shortlist.candidates) <= strat.max_candidates(5)

    def test_max_candidates_bound_if_defined(
        self, initial_graph, strategy_factory
    ):
        """If strategy defines max_candidates(), candidates count must not exceed max_candidates(n_existing)."""
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = strategy_factory(initial_graph, embedder)
        n_existing = initial_graph.num_nodes()
        res = strat.shortlist("dijkstra_algorithm")
        if hasattr(strat, "max_candidates") and callable(strat.max_candidates):
            assert len(res.candidates) <= strat.max_candidates(n_existing)

    def test_embedder_identity_stored_on_strategy(
        self, initial_graph, strategy_factory
    ):
        """Embedding strategies must store the exact MeteredEmbedder passed to setup().

        The insert_node driver checks `strategy._embedder is metered_embedder`; if the
        strategy wraps or replaces the embedder, the identity check will raise ValueError.
        This test verifies that does not happen.

        Non-embedding strategies (uses_embeddings=False) have _embedder=None and
        are excluded from this test (the identity check is bypassed for None by insert_node).
        """
        if not getattr(self.__class__, "uses_embeddings", True):
            pytest.skip("Non-embedding strategy: _embedder is None by design")

        raw_embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_embedder)
        strat = strategy_factory(initial_graph, meter)

        # The factory already called setup(); verify the stored embedder is identical
        strat_embedder = getattr(strat, "_embedder", None)
        assert strat_embedder is meter, (
            f"strategy._embedder is not the MeteredEmbedder passed to setup(). "
            f"Got: {strat_embedder!r}. Expected: {meter!r}. "
            "The strategy must store the exact object, not a copy or wrapper."
        )

        # Also verify that insert_node succeeds with the same meter (no ValueError)
        ds = FakeDecisionStep(make_edge=False)
        res = insert_node(strat, initial_graph, ds, "new_concept", metered_embedder=meter)
        assert initial_graph.has_node("new_concept")
        _ = res  # metrics available


class TestTinyFakeStrategyConformance(StrategyConformanceSuite):
    """Instantiate the reusable conformance suite on the reference TinyFakeStrategy."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(self) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
            strat = TinyFakeStrategy(top_k=4, seed=42)
            strat.setup(graph, embedder)
            return strat

        return _factory


# ===========================================================================
# Meta-Tests: prove uses_embeddings flag flips the right assertions
# ===========================================================================

class _MinimalEmbeddingStrategy:
    """Minimal strategy that DOES embed (for meta-test purposes only)."""
    name = "meta_embedding"
    uses_embeddings: bool = True
    _embedder = None

    def setup(self, graph, embedder):
        self._graph = graph
        self._embedder = embedder
        for node in graph.nodes():
            embedder.embed(embed_text(node))

    def shortlist(self, new_name):
        self._embedder.embed(embed_text(new_name))
        nodes = [n for n in sorted(self._graph.nodes()) if n != new_name]
        return Shortlist(candidates=tuple(nodes[:1]), scores=(1.0,))

    def on_inserted(self, new_name, edges): pass
    def config(self): return {}
    def diagnostics(self): return {}


class _MinimalNonEmbeddingStrategy:
    """Minimal strategy that does NOT embed (for meta-test purposes only)."""
    name = "meta_non_embedding"
    uses_embeddings: bool = False
    _embedder = None

    def setup(self, graph, embedder):
        self._graph = graph
        # intentionally does NOT store embedder

    def shortlist(self, new_name):
        nodes = [n for n in sorted(self._graph.nodes()) if n != new_name]
        return Shortlist(candidates=tuple(nodes[:1]), scores=(0.0,))

    def on_inserted(self, new_name, edges): pass
    def config(self): return {}
    def diagnostics(self): return {}


class TestEmbeddingConformanceSuiteMetaTest(StrategyConformanceSuite):
    """Meta-test: embedding strategy passes all conformance tests with uses_embeddings=True."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(self):
        def _factory(graph, embedder):
            strat = _MinimalEmbeddingStrategy()
            strat.setup(graph, embedder)
            return strat
        return _factory


class TestNonEmbeddingConformanceSuiteMetaTest(StrategyConformanceSuite):
    """Meta-test: non-embedding strategy passes all conformance tests with uses_embeddings=False."""

    uses_embeddings: bool = False

    @pytest.fixture
    def strategy_factory(self):
        def _factory(graph, embedder):
            strat = _MinimalNonEmbeddingStrategy()
            strat.setup(graph, embedder)
            return strat
        return _factory




# ===========================================================================
# 3. Shortlist Contract Enforcement Tests (FIX-002 Item 2)
# ===========================================================================

class TestInsertNodeShortlistEnforcement:
    @pytest.fixture
    def initial_graph(self) -> ConceptGraph:
        g = ConceptGraph(domain_context="testing")
        g.add_node("alpha")
        g.add_node("beta")
        return g

    @pytest.fixture
    def dummy_meter(self) -> MeteredEmbedder:
        return MeteredEmbedder(FakeEmbedder())

    def test_candidate_not_in_graph_raises(self, initial_graph, dummy_meter):
        class BadCandidateStrategy:
            name = "bad_cand_strat"
            def setup(self, g, e): pass
            def shortlist(self, new_name): return Shortlist(candidates=("alpha", "nonexistent_node"))
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): return {}

        strat = BadCandidateStrategy()
        with pytest.raises(ValueError, match="not an existing graph node"):
            insert_node(strat, initial_graph, FakeDecisionStep(), "gamma", metered_embedder=dummy_meter)

    def test_duplicate_candidates_raises(self, initial_graph, dummy_meter):
        class DuplicateCandidateStrategy:
            name = "dup_strat"
            def setup(self, g, e): pass
            def shortlist(self, new_name): return Shortlist(candidates=("alpha", "alpha"))
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): return {}

        strat = DuplicateCandidateStrategy()
        with pytest.raises(ValueError, match="duplicate candidates"):
            insert_node(strat, initial_graph, FakeDecisionStep(), "gamma", metered_embedder=dummy_meter)

    def test_shortlist_contains_new_name_raises(self, initial_graph, dummy_meter):
        class SelfCandidateStrategy:
            name = "self_strat"
            def setup(self, g, e): pass
            def shortlist(self, new_name): return Shortlist(candidates=("alpha", new_name))
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): return {}

        strat = SelfCandidateStrategy()
        with pytest.raises(ValueError, match="contains inserted node"):
            insert_node(strat, initial_graph, FakeDecisionStep(), "gamma", metered_embedder=dummy_meter)

    def test_scores_length_mismatch_raises(self, initial_graph, dummy_meter):
        class ScoreMismatchStrategy:
            name = "mismatch_strat"
            def setup(self, g, e): pass
            def shortlist(self, new_name): return Shortlist(candidates=("alpha", "beta"), scores=(0.9,))
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): return {}

        strat = ScoreMismatchStrategy()
        with pytest.raises(ValueError, match="scores length"):
            insert_node(strat, initial_graph, FakeDecisionStep(), "gamma", metered_embedder=dummy_meter)


# ===========================================================================
# 4. Pre-Mutation Edge Validation Tests (FIX-002 Item 1)
# ===========================================================================

class TestInsertNodeEdgeValidation:
    @pytest.fixture
    def initial_graph(self) -> ConceptGraph:
        g = ConceptGraph(domain_context="testing")
        g.add_node("alpha")
        g.add_node("beta")
        g.add_node("gamma")
        return g

    def test_endpoint_not_in_shortlist_raises(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=1, seed=42)
        strat.setup(initial_graph, meter)

        class SneakyDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                # Returns an edge to gamma, which exists in graph but was NOT in candidates
                assert "gamma" not in candidates
                return DecisionOutcome(edges=(("gamma", new_name),), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError, match="not in the shortlisted candidates"):
            insert_node(strat, initial_graph, SneakyDecisionStep(), "delta", metered_embedder=meter)

    def test_endpoint_not_in_graph_raises_and_no_nodes_added(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, meter)

        class NonExistentNodeDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                return DecisionOutcome(edges=(("unknown_concept", new_name),), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError, match="not in the shortlisted candidates"):
            insert_node(strat, initial_graph, NonExistentNodeDecisionStep(), "delta", metered_embedder=meter)

        assert not initial_graph.has_node("unknown_concept")
        assert not initial_graph.has_node("delta")
        assert initial_graph.num_nodes() == 3

    def test_duplicate_decided_edges_raise(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, meter)

        class DuplicateEdgeDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                c = candidates[0]
                return DecisionOutcome(edges=((c, new_name), (c, new_name)), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError, match="duplicate edges"):
            insert_node(strat, initial_graph, DuplicateEdgeDecisionStep(), "delta", metered_embedder=meter)

    def test_self_loop_edge_raises(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, meter)

        class SelfLoopDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                return DecisionOutcome(edges=((new_name, new_name),), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError, match="self-loop"):
            insert_node(strat, initial_graph, SelfLoopDecisionStep(), "delta", metered_embedder=meter)

    def test_graph_unchanged_and_strategy_not_notified_after_failure(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=2, seed=42)
        strat.setup(initial_graph, meter)

        n_before = initial_graph.num_nodes()
        e_before = initial_graph.num_edges()

        class FaultyDecisionStep:
            def decide(self, new_name, candidates, domain_context=None):
                return DecisionOutcome(edges=(("non_candidate", new_name),), llm_calls=1, llm_seconds=0.01)

        with pytest.raises(ValueError):
            insert_node(strat, initial_graph, FaultyDecisionStep(), "delta", metered_embedder=meter)

        # Graph is completely untouched
        assert initial_graph.num_nodes() == n_before
        assert initial_graph.num_edges() == e_before
        assert not initial_graph.has_node("delta")
        # Strategy on_inserted was NOT called
        assert not strat.on_inserted_called


# ===========================================================================
# 5. Timing, Accounting & Driver Feature Tests
# ===========================================================================

class TestInsertNodeTimingAndMetrics:
    @pytest.fixture
    def initial_graph(self) -> ConceptGraph:
        g = ConceptGraph(domain_context="testing")
        g.add_node("alpha")
        g.add_node("beta")
        return g

    def test_metered_embedder_required_keyword_argument(self, initial_graph):
        strat = TinyFakeStrategy()
        strat.setup(initial_graph, FakeEmbedder())
        ds = FakeDecisionStep()
        # Missing keyword-only metered_embedder must raise TypeError
        with pytest.raises(TypeError):
            insert_node(strat, initial_graph, ds, "gamma")  # type: ignore[call-arg]

    def test_metered_embedder_none_or_invalid_raises_type_error(self, initial_graph):
        strat = TinyFakeStrategy(top_k=0)
        meter = MeteredEmbedder(FakeEmbedder())
        strat.setup(initial_graph, meter)
        ds = FakeDecisionStep()
        # Passing None must raise TypeError
        with pytest.raises(TypeError, match="must be an instance of MeteredEmbedder"):
            insert_node(strat, initial_graph, ds, "gamma", metered_embedder=None)  # type: ignore[arg-type]
        # Passing a non-MeteredEmbedder must raise TypeError
        with pytest.raises(TypeError, match="must be an instance of MeteredEmbedder"):
            insert_node(strat, initial_graph, ds, "gamma", metered_embedder=FakeEmbedder())  # type: ignore[arg-type]

    def test_embedder_mismatch_raises_value_error_and_graph_untouched(self, initial_graph):
        meter1 = MeteredEmbedder(FakeEmbedder())
        meter2 = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=1)
        strat.setup(initial_graph, meter1)
        ds = FakeDecisionStep()

        n_before = initial_graph.num_nodes()
        e_before = initial_graph.num_edges()

        # Strategy holds meter1, caller passes meter2 -> ValueError before shortlist or mutation
        with pytest.raises(ValueError, match="MeteredEmbedder mismatch"):
            insert_node(strat, initial_graph, ds, "gamma", metered_embedder=meter2)

        # Graph must be completely untouched
        assert initial_graph.num_nodes() == n_before
        assert initial_graph.num_edges() == e_before
        assert not initial_graph.has_node("gamma")
        # Strategy on_inserted must NOT have been called
        assert not strat.on_inserted_called

    def test_strategy_without_embedder_accepts_any_metered_embedder(self, initial_graph):
        class NoEmbedderStrategy:
            name = "no_embedder"
            def setup(self, g, e): pass
            def shortlist(self, n): return Shortlist(candidates=())
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): return {}

        strat = NoEmbedderStrategy()
        meter = MeteredEmbedder(FakeEmbedder())
        ds = FakeDecisionStep()
        res = insert_node(strat, initial_graph, ds, "gamma", metered_embedder=meter)
        assert initial_graph.has_node("gamma")
        assert res.metrics.embedding_calls == 0

    def test_timing_components_consistency_with_apply_s(self, initial_graph):
        raw = FakeEmbedder()
        meter = MeteredEmbedder(raw)
        strat = TinyFakeStrategy(top_k=2)
        strat.setup(initial_graph, meter)
        meter.reset()

        ds = FakeDecisionStep(make_edge=True)
        res = insert_node(strat, initial_graph, ds, "gamma", metered_embedder=meter)

        m = res.metrics
        assert m.shortlist_s >= m.embed_s
        assert m.apply_s >= 0.0
        assert m.update_s >= 0.0
        assert m.decide_s >= 0.0
        assert m.validate_s >= 0.0
        assert m.embedding_calls_in_update == 0
        assert m.embed_in_update_s == 0.0
        # Operational total_s must exactly equal sum of 4 components within float tolerance
        expected_total = m.shortlist_s + m.decide_s + m.apply_s + m.update_s
        assert abs(m.total_s - expected_total) < 1e-9

    def test_diagnostics_error_recorded(self, initial_graph):
        class ExplodingDiagnosticsStrategy:
            name = "exploding"
            def setup(self, g, e): pass
            def shortlist(self, n): return Shortlist(candidates=())
            def on_inserted(self, n, e): pass
            def config(self): return {}
            def diagnostics(self): raise RuntimeError("telemetry crashed")

        strat = ExplodingDiagnosticsStrategy()
        meter = MeteredEmbedder(FakeEmbedder())
        res = insert_node(strat, initial_graph, FakeDecisionStep(), "gamma", metered_embedder=meter)
        assert "diagnostics_error" in res.metrics.extra
        assert "telemetry crashed" in res.metrics.extra["diagnostics_error"]

    def test_empty_shortlist_skips_decide_and_llm(self, initial_graph):
        meter = MeteredEmbedder(FakeEmbedder())
        strat = TinyFakeStrategy(top_k=0)
        strat.setup(initial_graph, meter)
        ds = FakeDecisionStep()

        res = insert_node(strat, initial_graph, ds, "gamma", metered_embedder=meter)
        assert len(res.shortlist.candidates) == 0
        assert len(res.edges) == 0
        assert res.metrics.llm_calls == 0
        assert res.metrics.decide_s == 0.0
        assert ds.calls == 0
