"""tests/test_ann_retrieval_strategy.py — STRAT-003
===================================================
Unit, conformance, mutation, and integration tests for AnnRetrievalStrategy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, embed_text
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_sweep_experiment,
)
from graph_insertion.decision import PairwiseDecisionStep
from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
from graph_insertion.strategy import (
    NarrowingStrategy,
    Shortlist,
    candidate_upper_bound,
    insert_node,
)
from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine
from tests.test_strategy_interface import FakeDecisionStep, StrategyConformanceSuite


# ===========================================================================
# 1. Strategy Conformance Suite (uses_embeddings = True)
# ===========================================================================

class TestAnnRetrievalConformance(StrategyConformanceSuite):
    """Instantiate the reusable conformance suite on AnnRetrievalStrategy."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(self) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
            strat = AnnRetrievalStrategy(k=10, seed=42)
            strat.setup(graph, embedder)
            return strat

        return _factory


# ===========================================================================
# 2. Top-k Semantics, Threshold Absence, and Tie Breaking
# ===========================================================================

class TestTopKSemantics:
    def test_topk_descending_order_and_no_threshold(self):
        """Top-k returns candidates in descending score order without thresholding."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0

        target_cosines = [0.95, 0.90, 0.80, 0.70, 0.60, 0.50, 0.20, -0.50]
        node_names = [
            "c_95",
            "c_90",
            "c_80",
            "c_70",
            "c_60",
            "c_50",
            "c_20",
            "c_neg50",
        ]
        vectors = {"probe_b": base}
        for name, cos_val in zip(node_names, target_cosines):
            vectors[name] = vector_with_cosine(base, cos_val)

        embedder = ControllableEmbedder(vectors, dim=16)
        graph = ConceptGraph()
        for name in node_names:
            graph.add_node(name)

        # k=3: exactly top 3 in descending order, scores within 1e-6
        strat3 = AnnRetrievalStrategy(k=3, seed=42)
        strat3.setup(graph, embedder)
        res3 = strat3.shortlist("probe_b")

        assert res3.candidates == ("c_95", "c_90", "c_80")
        assert res3.scores is not None
        assert np.allclose(res3.scores, (0.95, 0.90, 0.80), atol=1e-6)
        # Strictly descending scores
        assert res3.scores[0] > res3.scores[1] > res3.scores[2]

        # k=8: returns all eight candidates including 0.20 and -0.50 (no threshold)
        strat8 = AnnRetrievalStrategy(k=8, seed=42)
        strat8.setup(graph, embedder)
        res8 = strat8.shortlist("probe_b")

        assert len(res8.candidates) == 8
        assert res8.candidates == tuple(node_names)
        assert res8.scores is not None
        assert np.allclose(res8.scores, target_cosines, atol=1e-6)
        assert "c_20" in res8.candidates
        assert "c_neg50" in res8.candidates

    def test_ties_ordered_by_name_ascending(self):
        """Identical vectors break ties by concept name ascending."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0
        v_tied = vector_with_cosine(base, 0.85)

        vectors = {
            "probe": base,
            "zeta_concept": v_tied,
            "alpha_concept": v_tied,
            "beta_concept": vector_with_cosine(base, 0.50),
        }
        embedder = ControllableEmbedder(vectors, dim=16)
        graph = ConceptGraph()
        for name in ["zeta_concept", "alpha_concept", "beta_concept"]:
            graph.add_node(name)

        strat = AnnRetrievalStrategy(k=3, seed=42)
        strat.setup(graph, embedder)
        res = strat.shortlist("probe")

        assert res.candidates[:2] == ("alpha_concept", "zeta_concept")
        assert res.candidates[2] == "beta_concept"


# ===========================================================================
# 3. k Greater Than n and -1 Padding Handling
# ===========================================================================

class TestKGreaterThanN:
    def test_k_greater_than_n_no_minus_one_leakage(self):
        """When k > n, shortlist contains exactly n candidates with no -1 leakage."""
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        graph = ConceptGraph()
        for n in nodes:
            graph.add_node(n)

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=10, seed=42)
        strat.setup(graph, embedder)

        res = strat.shortlist("probe_node")
        assert len(res.candidates) == 4
        assert set(res.candidates) == set(nodes)
        assert len(set(res.candidates)) == len(res.candidates)
        assert -1 not in res.candidates
        assert "-1" not in res.candidates
        assert res.scores is not None
        assert len(res.scores) == 4
        for s in res.scores:
            assert isinstance(s, float)
            assert -1.05 <= s <= 1.05

    def test_search_receives_k_eff_min_k_n(self):
        """Shortlist passes min(k, n) to index.search when new_name is unindexed."""
        nodes = ["node_a", "node_b", "node_c", "node_d"]
        graph = ConceptGraph()
        for n in nodes:
            graph.add_node(n)

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=10, seed=42)
        strat.setup(graph, embedder)

        orig_search = strat._index.search
        search_k_arg = []

        def spy_search(q, k):
            search_k_arg.append(k)
            return orig_search(q, k)

        strat._index.search = spy_search
        res = strat.shortlist("probe_node")

        assert search_k_arg == [4], f"Expected search called with k=4, got {search_k_arg}"
        assert len(res.candidates) == 4

    def test_minus_one_padding_dropped_explicitly(self, monkeypatch):
        """Labels with -1 returned by FAISS are dropped and never mapped to self._names[-1]."""
        nodes = ["node_0", "node_1", "node_2"]
        graph = ConceptGraph()
        for n in nodes:
            graph.add_node(n)

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, embedder)

        def mock_search(q, k):
            return np.array([[0.9, -1.0]], dtype=np.float32), np.array([[0, -1]], dtype=np.int64)

        monkeypatch.setattr(strat._index, "search", mock_search)
        res = strat.shortlist("probe")

        # Must contain only node_0, NOT node_2 (which is self._names[-1])
        assert res.candidates == ("node_0",)
        assert res.scores is not None
        assert np.allclose(res.scores, (0.9,), atol=1e-6)


# ===========================================================================
# 4. Unnormalised Vectors, Setup and Insert Paths
# ===========================================================================

class TestUnnormalisedVectors:
    def test_setup_and_insert_with_unnormalised_vectors(self):
        """Unnormalised vectors in setup and on_inserted are normalised correctly."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0

        dir_90 = vector_with_cosine(base, 0.90)
        dir_60 = vector_with_cosine(base, 0.60)

        # Scaled directions
        vectors = {
            "probe": 0.01 * base,
            "c_90": 7.3 * dir_90,
            "c_60": 0.005 * dir_60,
            "inserted_90": 7.3 * dir_90,
        }
        embedder = ControllableEmbedder(vectors, dim=16)
        graph = ConceptGraph()
        graph.add_node("c_90")
        graph.add_node("c_60")

        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, embedder)

        # Setup path check
        res = strat.shortlist("probe")
        assert res.candidates == ("c_90", "c_60")
        assert res.scores is not None
        assert np.isclose(res.scores[0], 0.90, atol=1e-6)
        assert np.isclose(res.scores[1], 0.60, atol=1e-6)

        # Insert path check via insert_node
        meter = MeteredEmbedder(embedder, record_texts=True)
        strat2 = AnnRetrievalStrategy(k=5, seed=42)
        strat2.setup(graph, meter)

        decision_step = FakeDecisionStep(make_edge=False)
        insert_node(
            strat2,
            graph,
            decision_step,
            "inserted_90",
            metered_embedder=meter,
        )

        # Query with probe scaled by 0.01
        res_after = strat2.shortlist("probe")
        assert "inserted_90" in res_after.candidates
        idx = res_after.candidates.index("inserted_90")
        assert res_after.scores is not None
        assert np.isclose(res_after.scores[idx], 0.90, atol=1e-6)


# ===========================================================================
# 5. new_name Exclusion When Already Indexed
# ===========================================================================

class TestNewNameExclusion:
    def test_new_name_excluded_when_already_in_index(self):
        """If new_name is already in index, shortlist excludes it and returns remaining."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0

        v_bb = vector_with_cosine(base, 0.90)
        vectors = {
            "aa": base,
            "bb": v_bb,
        }
        embedder = ControllableEmbedder(vectors, dim=16)
        graph = ConceptGraph()
        graph.add_node("aa")
        graph.add_node("bb")

        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, embedder)

        res = strat.shortlist("aa")
        assert "aa" not in res.candidates
        assert res.candidates == ("bb",)
        assert res.scores is not None
        assert np.isclose(res.scores[0], 0.90, atol=1e-6)


# ===========================================================================
# 6. Single-Embedding Invariant and Payload (D-21)
# ===========================================================================

class TestSingleEmbeddingInvariant:
    def test_single_embedding_and_payload_compliance(self):
        """insert_node embeds new_name exactly once; zero embedding during update."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0

        vectors = {
            "node_initial": base,
            "node_new": vector_with_cosine(base, 0.70),
            "node_second": vector_with_cosine(base, 0.50),
        }
        # strict=True raises on any text not registered via embed_text
        raw_embedder = ControllableEmbedder(vectors, dim=16, strict=True)
        meter = MeteredEmbedder(raw_embedder, record_texts=True)

        graph = ConceptGraph()
        graph.add_node("node_initial")

        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, meter)
        assert strat._embedder is meter

        initial_log_len = len(meter.texts_log)
        assert initial_log_len == 1
        assert meter.texts_log[0] == embed_text("node_initial")

        decision_step = FakeDecisionStep(make_edge=True)
        res = insert_node(
            strat,
            graph,
            decision_step,
            "node_new",
            metered_embedder=meter,
        )

        assert res.metrics.embedding_calls == 1
        assert res.metrics.embedding_calls_in_update == 0
        assert res.metrics.embed_in_update_s == 0.0
        assert len(meter.texts_log) == initial_log_len + 1
        assert meter.texts_log[-1] == embed_text("node_new")
        assert "_" not in meter.texts_log[-1]

    def test_empty_initial_graph_single_embedding(self):
        """First insertion into empty graph embeds once in shortlist, zero in update."""
        base = np.zeros(16, dtype=np.float32)
        base[0] = 1.0

        vectors = {"first_node": base}
        raw_embedder = ControllableEmbedder(vectors, dim=16, strict=True)
        meter = MeteredEmbedder(raw_embedder, record_texts=True)

        graph = ConceptGraph()
        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, meter)

        assert meter.calls == 0
        assert meter.texts_log == []

        decision_step = FakeDecisionStep(make_edge=False)
        res = insert_node(
            strat,
            graph,
            decision_step,
            "first_node",
            metered_embedder=meter,
        )

        assert res.metrics.embedding_calls == 1
        assert res.metrics.embedding_calls_in_update == 0
        assert res.metrics.embed_in_update_s == 0.0
        assert strat._index.ntotal == 1
        assert len(meter.texts_log) == 1
        assert meter.texts_log[0] == embed_text("first_node")


# ===========================================================================
# 7. Lifecycle Errors
# ===========================================================================

class _BadEmbedder:
    """Local Embedder implementing protocol with bad vectors for specific texts."""

    def __init__(self, bad_text: str, bad_vector: np.ndarray) -> None:
        self.bad_text = bad_text
        self.bad_vector = bad_vector
        self.good_vector = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def embed(self, text: str) -> np.ndarray:
        if text == self.bad_text:
            return self.bad_vector
        return self.good_vector

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        return np.stack([self.embed(t) for t in texts])


class TestLifecycleErrors:
    def test_shortlist_before_setup_raises_runtime_error(self):
        strat = AnnRetrievalStrategy(k=5)
        with pytest.raises(RuntimeError, match="setup.*must be called before shortlist"):
            strat.shortlist("some_node")

    def test_on_inserted_without_matching_shortlist_raises_runtime_error(self):
        graph = ConceptGraph()
        graph.add_node("existing")
        embedder = FakeEmbedder(dim=16)
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph, embedder)

        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("unqueried_node", ())

    def test_inserting_already_indexed_name_raises_value_error(self):
        graph = ConceptGraph()
        graph.add_node("indexed_node")
        embedder = FakeEmbedder(dim=16)
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph, embedder)

        # Call shortlist on already indexed name
        strat.shortlist("indexed_node")
        with pytest.raises(ValueError, match="already present in the index"):
            strat.on_inserted("indexed_node", ())

    @pytest.mark.parametrize(
        "bad_vec",
        [
            np.array([np.nan, 0.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            np.array([1.0, 0.0], dtype=np.float32),  # Wrong dim (expected 4)
        ],
    )
    def test_failed_shortlist_leaves_no_cached_vector(self, bad_vec):
        graph = ConceptGraph()
        graph.add_node("valid_node")

        bad_embedder = _BadEmbedder(embed_text("bad_concept"), bad_vec)
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph, bad_embedder)

        with pytest.raises(ValueError, match="bad_concept"):
            strat.shortlist("bad_concept")

        assert strat._cached_new_name is None
        assert strat._cached_new_vec is None

        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("bad_concept", ())


# ===========================================================================
# 8. Setup Semantics and Determinism Under Re-setup
# ===========================================================================

class _FailingSetupEmbedder:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def embed(self, text: str) -> np.ndarray:
        return np.ones(4, dtype=np.float32)

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        if self.mode == "zero_row":
            mat = np.ones((len(texts), 4), dtype=np.float32)
            mat[0] = 0.0
            return mat
        elif self.mode == "nan_row":
            mat = np.ones((len(texts), 4), dtype=np.float32)
            mat[0, 0] = np.nan
            return mat
        elif self.mode == "non_2d":
            return np.ones(4, dtype=np.float32)
        raise ValueError("Unknown mode")


class TestSetupSemantics:
    def test_setup_twice_resets_state_completely(self):
        graph_a = ConceptGraph()
        graph_a.add_node("a1")
        graph_a.add_node("a2")

        graph_b = ConceptGraph()
        graph_b.add_node("b1")
        graph_b.add_node("b2")
        graph_b.add_node("b3")

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)

        strat.setup(graph_a, embedder)
        assert strat._index.ntotal == 2

        strat.setup(graph_b, embedder)
        assert strat._index.ntotal == 3
        res = strat.shortlist("probe")
        assert all(c.startswith("b") for c in res.candidates)

    def test_setup_nonempty_then_empty(self):
        graph_nonempty = ConceptGraph()
        graph_nonempty.add_node("x1")

        graph_empty = ConceptGraph()
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)

        strat.setup(graph_nonempty, embedder)
        assert strat._index.ntotal == 1

        strat.setup(graph_empty, embedder)
        assert strat.diagnostics()["index_size"] == 0
        res = strat.shortlist("probe")
        assert res.candidates == ()

    @pytest.mark.parametrize("fail_mode", ["zero_row", "nan_row", "non_2d"])
    def test_failed_second_setup_leaves_strategy_not_set_up(self, fail_mode):
        graph = ConceptGraph()
        graph.add_node("valid_node")

        good_embedder = FakeEmbedder(dim=4, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, good_embedder)

        failing_embedder = _FailingSetupEmbedder(fail_mode)
        with pytest.raises(ValueError):
            strat.setup(graph, failing_embedder)

        assert not strat._setup_called
        assert strat._embedder is None
        with pytest.raises(RuntimeError, match="setup.*must be called before shortlist"):
            strat.shortlist("probe")

        # Later successful setup works cleanly
        strat.setup(graph, good_embedder)
        assert strat._setup_called
        res = strat.shortlist("probe")
        assert res.candidates == ("valid_node",)

    def test_faiss_omp_threads_set_to_one(self):
        graph = ConceptGraph()
        graph.add_node("n1")
        embedder = FakeEmbedder(dim=16)
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph, embedder)

        assert faiss.omp_get_max_threads() == 1
        assert strat.config()["faiss_threads"] == 1


# ===========================================================================
# 9. Growth and Fidelity Across 300 Insertions
# ===========================================================================

class TestGrowthAndFidelity:
    def test_growth_and_exact_fidelity(self):
        """Start with 3 nodes, insert 300 through driver; check >=0.95 mean recall@10."""
        rng = np.random.default_rng(42)
        dim = 16

        # Build initial 3 nodes
        init_names = ["init_0", "init_1", "init_2"]
        graph = ConceptGraph()
        for name in init_names:
            graph.add_node(name)

        embedder = FakeEmbedder(dim=dim, seed=123)
        meter = MeteredEmbedder(embedder)
        strat = AnnRetrievalStrategy(k=10, seed=42)
        strat.setup(graph, meter)

        decision_step = FakeDecisionStep(make_edge=False)

        # Insert 300 nodes
        insert_names = [f"concept_{i:04d}" for i in range(300)]
        for name in insert_names:
            insert_node(
                strat,
                graph,
                decision_step,
                name,
                metered_embedder=meter,
            )
            assert strat._index.ntotal == graph.num_nodes()

        assert graph.num_nodes() == 303

        # Compute exact reference matrix for all 303 nodes
        all_nodes = sorted(graph.nodes())
        all_texts = [embed_text(n) for n in all_nodes]
        all_vectors = embedder.embed_many(all_texts)
        norms = np.linalg.norm(all_vectors, axis=1, keepdims=True)
        normed_all = all_vectors / norms

        # Query 20 probes
        probe_names = [f"probe_{j:02d}" for j in range(20)]
        probe_texts = [embed_text(p) for p in probe_names]
        probe_vectors = embedder.embed_many(probe_texts)
        probe_norms = np.linalg.norm(probe_vectors, axis=1, keepdims=True)
        normed_probes = probe_vectors / probe_norms

        overlaps = []
        for j, p_name in enumerate(probe_names):
            res = strat.shortlist(p_name)
            assert len(res.candidates) == 10
            # Scores must be sorted descending
            assert res.scores is not None
            for idx in range(len(res.scores) - 1):
                assert res.scores[idx] >= res.scores[idx + 1]

            # Exact top-10
            q_vec = normed_probes[j]
            cosines = normed_all @ q_vec
            ranked_indices = np.argsort(-cosines)[:10]
            exact_top10 = {all_nodes[idx] for idx in ranked_indices}
            assert len(exact_top10) == 10

            overlap = len(set(res.candidates) & exact_top10) / 10.0
            overlaps.append(overlap)

        mean_overlap = float(np.mean(overlaps))
        assert mean_overlap >= 0.95, f"Expected mean overlap >= 0.95, got {mean_overlap:.4f}"


# ===========================================================================
# 10. Determinism Across Independent Instances
# ===========================================================================

class TestDeterminism:
    def test_two_independent_strategies_return_identical_results(self):
        graph = ConceptGraph()
        for i in range(50):
            graph.add_node(f"concept_{i:03d}")

        embedder = FakeEmbedder(dim=16, seed=42)

        strat1 = AnnRetrievalStrategy(k=10, seed=42)
        strat1.setup(graph, embedder)

        strat2 = AnnRetrievalStrategy(k=10, seed=42)
        strat2.setup(graph, embedder)

        for j in range(20):
            probe = f"query_{j:02d}"
            res1 = strat1.shortlist(probe)
            res2 = strat2.shortlist(probe)

            assert res1.candidates == res2.candidates
            assert res1.scores == res2.scores


# ===========================================================================
# 11. max_candidates Bound and candidate_upper_bound
# ===========================================================================

class TestCandidateBound:
    def test_max_candidates_and_matrix_sum(self):
        strat = AnnRetrievalStrategy(k=10)

        for n in (0, 1, 9, 10, 11, 2000):
            assert strat.max_candidates(n) == min(10, n)
            assert candidate_upper_bound(strat, n) == min(10, n)

        sweep_sizes = (50, 100, 200, 500, 1000, 2000)
        trials = 10

        # k=10 bound: 600
        bound_k10 = sum(candidate_upper_bound(strat, s) * trials for s in sweep_sizes)
        assert bound_k10 == 600

        # k=5 bound: 300
        strat_k5 = AnnRetrievalStrategy(k=5)
        bound_k5 = sum(candidate_upper_bound(strat_k5, s) * trials for s in sweep_sizes)
        assert bound_k5 == 300

        # k=20 bound: 1200
        strat_k20 = AnnRetrievalStrategy(k=20)
        bound_k20 = sum(candidate_upper_bound(strat_k20, s) * trials for s in sweep_sizes)
        assert bound_k20 == 1200


# ===========================================================================
# 12. JSON Safety and Native Python Types
# ===========================================================================

def _assert_no_numpy_types(obj: Any) -> None:
    if isinstance(obj, (np.generic, np.ndarray)):
        raise AssertionError(f"Found numpy type {type(obj)} in {obj!r}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_numpy_types(k)
            _assert_no_numpy_types(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _assert_no_numpy_types(item)


class TestJSONSafety:
    def test_json_serialization_and_diagnostics_keys(self):
        graph = ConceptGraph()
        graph.add_node("c1")
        graph.add_node("c2")

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=10, seed=42)

        # Before setup/shortlist diagnostics
        diag_init = strat.diagnostics()
        expected_keys = {
            "top_k",
            "index_size",
            "shortlist_size",
            "max_cosine",
            "ef_search",
            "exact_topk_overlap",
        }
        assert set(diag_init.keys()) == expected_keys
        json.dumps(diag_init)
        _assert_no_numpy_types(diag_init)

        cfg = strat.config()
        json.dumps(cfg)
        _assert_no_numpy_types(cfg)

        strat.setup(graph, embedder)
        res = strat.shortlist("probe")
        json.dumps(res.scores)
        _assert_no_numpy_types(res.scores)

        diag_after = strat.diagnostics()
        assert set(diag_after.keys()) == expected_keys
        json.dumps(diag_after)
        _assert_no_numpy_types(diag_after)


# ===========================================================================
# 13. exact_topk_overlap Diagnostic Behavior
# ===========================================================================

class TestExactTopKOverlap:
    def test_exact_topk_overlap_lifecycle(self):
        strat = AnnRetrievalStrategy(k=5, seed=42)

        # 1. Before any shortlist: None
        assert strat.diagnostics()["exact_topk_overlap"] is None

        # 2. Empty index: None
        empty_graph = ConceptGraph()
        embedder = FakeEmbedder(dim=16, seed=42)
        strat.setup(empty_graph, embedder)
        strat.shortlist("probe")
        assert strat.diagnostics()["exact_topk_overlap"] is None

        # 3. Small controlled set where HNSW is exact: 1.0
        graph = ConceptGraph()
        for i in range(8):
            graph.add_node(f"node_{i}")
        strat.setup(graph, embedder)

        res1 = strat.shortlist("probe_1")
        diag1 = strat.diagnostics()
        overlap1 = diag1["exact_topk_overlap"]
        assert overlap1 == 1.0

        # Stable across repeated calls
        diag1_repeat = strat.diagnostics()
        assert diag1_repeat["exact_topk_overlap"] == 1.0

        # Resets and recomputes after next shortlist
        res2 = strat.shortlist("probe_2")
        diag2 = strat.diagnostics()
        assert diag2["exact_topk_overlap"] is not None
        assert 0.0 <= diag2["exact_topk_overlap"] <= 1.0


# ===========================================================================
# 14. Parameter Validation
# ===========================================================================

class TestParameterValidation:
    @pytest.mark.parametrize("bad_val", [True, 0, -1, 2.5, "10"])
    def test_k_validation(self, bad_val):
        with pytest.raises(ValueError):
            AnnRetrievalStrategy(k=bad_val)

    @pytest.mark.parametrize("bad_val", [True, 1, 0, -1, 2.5, "16"])
    def test_M_validation(self, bad_val):
        with pytest.raises(ValueError):
            AnnRetrievalStrategy(M=bad_val)

    @pytest.mark.parametrize("bad_val", [True, 0, -1, 2.5, "200"])
    def test_ef_construction_validation(self, bad_val):
        with pytest.raises(ValueError):
            AnnRetrievalStrategy(ef_construction=bad_val)

    @pytest.mark.parametrize("bad_val", [True, 0, -1, 2.5, "128"])
    def test_ef_search_validation(self, bad_val):
        with pytest.raises(ValueError):
            AnnRetrievalStrategy(ef_search=bad_val)

    def test_defaults(self):
        strat = AnnRetrievalStrategy()
        assert strat.k == 10
        assert strat.M == 16
        assert strat.ef_construction == 200
        assert strat.ef_search == 128


# ===========================================================================
# 15. Missing faiss Import Guard
# ===========================================================================

class TestMissingFaiss:
    def test_missing_faiss_raises_import_error(self, monkeypatch):
        import graph_insertion.strategies.ann_retrieval as ann_mod

        monkeypatch.setattr(ann_mod, "faiss", None)
        with pytest.raises(ImportError, match=r"pip install -e '\.\[ann\]'"):
            ann_mod.AnnRetrievalStrategy()


# ===========================================================================
# 16. Scale Sanity
# ===========================================================================

class TestScaleSanity:
    def test_scale_sanity_2000_nodes(self):
        """2000 nodes with FakeEmbedder(dim=64): shortlist returns 10 distinct candidates."""
        graph = ConceptGraph()
        for i in range(2000):
            graph.add_node(f"concept_{i:04d}")

        embedder = FakeEmbedder(dim=64, seed=42)
        strat = AnnRetrievalStrategy(k=10, seed=42)
        strat.setup(graph, embedder)

        res = strat.shortlist("new_query_concept")
        assert len(res.candidates) == 10
        assert len(set(res.candidates)) == 10
        assert all(c in graph.nodes() for c in res.candidates)
        assert res.scores is not None
        for i in range(len(res.scores) - 1):
            assert res.scores[i] >= res.scores[i + 1]


# ===========================================================================
# 17. Harness Smoke Test
# ===========================================================================

def make_placeholder_names(n: int, offset: int = 0) -> list[str]:
    return [f"placeholder_concept_{i + offset:05d}" for i in range(n)]


class TestHarnessSmoke:
    def test_sweep_harness_smoke(self, tmp_path):
        """End-to-end smoke test through run_sweep_experiment."""
        name_source = SyntheticNameSource(
            names=make_placeholder_names(200),
            domain_context="computer science",
        )
        client = MeteredLLMClient(FakeLLMClient())
        decision_step = PairwiseDecisionStep(client)

        config = HarnessConfig(
            mode="sweep",
            run_id="test_ann_harness_smoke",
            output_dir=tmp_path / "smoke_out",
            seed=42,
            sweep_sizes=(12, 30),
            sweep_trials_per_size=2,
            confirm=True,
        )

        res = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: AnnRetrievalStrategy(k=10, seed=42),
            decision_step=decision_step,
            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
            name_source=name_source,
        )

        assert res["status"] == "completed"

        raw_path = tmp_path / "smoke_out" / "raw.jsonl"
        assert raw_path.exists()
        records = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]

        assert len(records) == 4  # 2 sizes x 2 trials

        for rec in records:
            assert rec["status"] == "success"
            assert rec["strategy"] == "ann_retrieval"
            m = rec["metrics"]
            expected_k = min(10, rec["size"])
            assert m["shortlist_size"] == expected_k
            assert m["llm_calls"] == expected_k
            assert m["embedding_calls"] == 1
            assert m["embedding_calls_in_update"] == 0
            assert m["extra"]["top_k"] == 10


# ===========================================================================
# 18. Specific Mutation-Killing Tests for (12), (13), (14)
# ===========================================================================

class TestMutationKillers:
    def test_mutation12_exact_topk_overlap_not_computed_in_shortlist(self):
        """reconstruct_n is NOT called during shortlist(); called in diagnostics()."""
        graph = ConceptGraph()
        for i in range(5):
            graph.add_node(f"n_{i}")

        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)
        strat.setup(graph, embedder)

        reconstruct_calls = []
        orig_reconstruct = strat._index.reconstruct_n

        def spy_reconstruct(start, n):
            reconstruct_calls.append((start, n))
            return orig_reconstruct(start, n)

        strat._index.reconstruct_n = spy_reconstruct

        # Call shortlist: must NOT call reconstruct_n
        strat.shortlist("probe_concept")
        assert len(reconstruct_calls) == 0, "reconstruct_n was called during shortlist()!"

        # Call diagnostics: must call reconstruct_n
        diag = strat.diagnostics()
        assert len(reconstruct_calls) == 1, "reconstruct_n was NOT called during diagnostics()!"
        assert diag["exact_topk_overlap"] == 1.0

    def test_mutation13_omp_set_num_threads_called_in_setup(self, monkeypatch):
        """faiss.omp_set_num_threads(1) must be called during setup()."""
        graph = ConceptGraph()
        graph.add_node("n1")
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5, seed=42)

        omp_calls = []
        orig_omp = faiss.omp_set_num_threads

        def spy_omp(threads):
            omp_calls.append(threads)
            return orig_omp(threads)

        monkeypatch.setattr(faiss, "omp_set_num_threads", spy_omp)
        strat.setup(graph, embedder)

        assert 1 in omp_calls, f"Expected omp_set_num_threads(1) called, got {omp_calls}"

    def test_mutation14_ef_construction_set_before_add(self):
        """index.hnsw.efConstruction must be set before index.add() is invoked."""
        graph = ConceptGraph()
        graph.add_node("n1")
        embedder = FakeEmbedder(dim=16, seed=42)

        ef_c_at_add = []
        orig_add = faiss.IndexHNSWFlat.add

        def spy_add(self, x):
            ef_c_at_add.append(self.hnsw.efConstruction)
            return orig_add(self, x)

        faiss.IndexHNSWFlat.add = spy_add
        try:
            strat = AnnRetrievalStrategy(k=5, ef_construction=200, seed=42)
            strat.setup(graph, embedder)
            assert ef_c_at_add == [200], f"Expected efConstruction=200 at add, got {ef_c_at_add}"
        finally:
            faiss.IndexHNSWFlat.add = orig_add


# ===========================================================================
# 19. Post-Review Amendment Tests (A-4: T-1, T-2, T-3, T-4)
# ===========================================================================

class _SelectiveFailingEmbedder:
    """Local Embedder implementing protocol with failing vectors only for specified concepts."""

    def __init__(self, base_embedder: Embedder, fail_concept: str) -> None:
        self.base = base_embedder
        self.fail_text = embed_text(fail_concept)

    def embed(self, text: str) -> np.ndarray:
        if text == self.fail_text:
            return np.zeros(16, dtype=np.float32)
        return self.base.embed(text)

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        return self.base.embed_many(texts)


class TestPostReviewAmendments:
    def test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector(self):
        """Test T-1 (A-1 regression): failed shortlist clears per-insertion cache."""
        graph = ConceptGraph()
        graph.add_node("existing_node")
        base_emb = FakeEmbedder(dim=16, seed=42)
        emb = _SelectiveFailingEmbedder(base_emb, "failing_node")
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph, emb)

        # 1. shortlist("good_node") succeeds and caches "good_node"
        res = strat.shortlist("good_node")
        assert len(res.candidates) == 1
        assert strat._cached_new_name == "good_node"
        assert strat._cached_new_vec is not None

        # 2. Failing shortlist("failing_node") raises ValueError
        with pytest.raises(ValueError, match="Zero-norm"):
            strat.shortlist("failing_node")

        # 3. Must leave NO cached vector from earlier successful shortlist
        assert strat._cached_new_name is None
        assert strat._cached_new_vec is None

        # 4. on_inserted("good_node") must now raise RuntimeError
        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("good_node", ())

        # 5. After failed shortlist on a fresh strategy, on_inserted raises RuntimeError
        strat_fresh = AnnRetrievalStrategy(k=5)
        strat_fresh.setup(graph, emb)
        with pytest.raises(ValueError, match="Zero-norm"):
            strat_fresh.shortlist("failing_node")
        assert strat_fresh._cached_new_name is None
        assert strat_fresh._cached_new_vec is None
        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat_fresh.on_inserted("failing_node", ())

    def test_t2_setup_clears_cached_shortlist_vector(self):
        """Test T-2 (kills Mutation 15): setup() clears any previously cached shortlist vector."""
        graph_a = ConceptGraph()
        graph_a.add_node("n_a")
        embedder = FakeEmbedder(dim=16, seed=42)
        strat = AnnRetrievalStrategy(k=5)
        strat.setup(graph_a, embedder)

        strat.shortlist("p")
        assert strat._cached_new_name == "p"
        assert strat._cached_new_vec is not None

        graph_b = ConceptGraph()
        graph_b.add_node("n_b")
        strat.setup(graph_b, embedder)

        assert strat._cached_new_name is None
        assert strat._cached_new_vec is None

        with pytest.raises(RuntimeError, match="without matching shortlist"):
            strat.on_inserted("p", ())

    def test_t3_diagnostics_after_on_inserted_through_driver(self):
        """Test T-3: diagnostics exact_topk_overlap matches independent float64 top-k through driver."""
        init_names = [f"initial_concept_{i:03d}" for i in range(35)]
        graph = ConceptGraph()
        for name in init_names:
            graph.add_node(name)

        embedder = ControllableEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(embedder)
        decision_step = FakeDecisionStep(make_edge=False)

        strat = AnnRetrievalStrategy(k=10, seed=42)
        strat.setup(graph, meter)

        probes = ["query_concept_alpha", "query_concept_beta", "query_concept_gamma"]
        for probe in probes:
            nodes_at_query = list(strat._names)
            n_at_q = len(nodes_at_query)
            reconstructed_64 = strat._index.reconstruct_n(0, n_at_q).astype(np.float64)
            q_vec_raw = embedder.embed(embed_text(probe))
            q_vec_64 = (q_vec_raw / np.linalg.norm(q_vec_raw)).astype(np.float64)
            cosines_64 = reconstructed_64 @ q_vec_64
            pairs = [
                (float(cosines_64[i]), nodes_at_query[i])
                for i in range(n_at_q)
                if nodes_at_query[i] != probe
            ]
            pairs.sort(key=lambda item: (-item[0], item[1]))
            k_eff = min(10, len(pairs))
            exact_set = {cand for _, cand in pairs[:k_eff]}

            n_before = graph.num_nodes()
            res = insert_node(strat, graph, decision_step, probe, metered_embedder=meter)

            assert res.shortlist is not None
            ret_cands = res.shortlist.candidates
            expected_overlap = (
                sum(1 for c in ret_cands if c in exact_set) / len(ret_cands)
                if ret_cands
                else (1.0 if k_eff == 0 else 0.0)
            )

            diag = strat.diagnostics()
            assert diag["exact_topk_overlap"] == expected_overlap
            assert 0.0 <= diag["exact_topk_overlap"] <= 1.0
            assert diag["index_size"] == n_before + 1

        # Deterministic low ef_search case (ef_search=1, n >= 100) where overlap < 1.0 is observed
        g_low = ConceptGraph()
        for i in range(120):
            g_low.add_node(f"node_low_{i:03d}")
        emb_low = FakeEmbedder(dim=16, seed=42)
        meter_low = MeteredEmbedder(emb_low)
        strat_low = AnnRetrievalStrategy(k=10, ef_search=1, seed=42)
        strat_low.setup(g_low, meter_low)
        insert_res_low = insert_node(strat_low, g_low, decision_step, "probe_low", metered_embedder=meter_low)
        diag_low = strat_low.diagnostics()
        assert diag_low["exact_topk_overlap"] is not None
        assert 0.0 <= diag_low["exact_topk_overlap"] < 1.0

    def test_t4_ef_search_applied_and_configured(self):
        """Test T-4: efSearch is correctly applied to HNSW index, config, and diagnostics."""
        graph = ConceptGraph()
        graph.add_node("n1")
        embedder = FakeEmbedder(dim=16, seed=42)

        # 1. Default ef_search is 128
        strat_def = AnnRetrievalStrategy()
        assert strat_def.ef_search == 128
        assert strat_def.config()["ef_search"] == 128
        strat_def.setup(graph, embedder)
        assert strat_def._index.hnsw.efSearch == 128
        assert strat_def.diagnostics()["ef_search"] == 128

        # 2. Non-default ef_search (e.g. 7) on non-empty graph
        strat_7 = AnnRetrievalStrategy(ef_search=7)
        assert strat_7.ef_search == 7
        assert strat_7.config()["ef_search"] == 7
        strat_7.setup(graph, embedder)
        assert strat_7._index.hnsw.efSearch == 7
        assert strat_7.diagnostics()["ef_search"] == 7

        # 3. Non-default ef_search on empty graph with lazy creation
        strat_empty_7 = AnnRetrievalStrategy(ef_search=7)
        strat_empty_7.setup(ConceptGraph(), embedder)
        assert strat_empty_7._index is None
        strat_empty_7.shortlist("concept_lazy")
        assert strat_empty_7._index.hnsw.efSearch == 7
        assert strat_empty_7.config()["ef_search"] == 7
        assert strat_empty_7.diagnostics()["ef_search"] == 7

        # 4. Default ef_search on empty graph with lazy creation
        strat_empty_def = AnnRetrievalStrategy()
        strat_empty_def.setup(ConceptGraph(), embedder)
        assert strat_empty_def._index is None
        strat_empty_def.shortlist("concept_lazy_def")
        assert strat_empty_def._index.hnsw.efSearch == 128
        assert strat_empty_def.config()["ef_search"] == 128
        assert strat_empty_def.diagnostics()["ef_search"] == 128

        # 5. Pre-search reapplication before search (kills mutation deleting pre-search assignment)
        strat_def._index.hnsw.efSearch = 1
        strat_def.shortlist("recheck_concept")
        assert strat_def._index.hnsw.efSearch == 128
