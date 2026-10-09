"""tests/test_embedding_threshold_strategy.py — STRAT-002
=======================================================
Unit and integration tests for EmbeddingThresholdStrategy.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph, embed_text
from graph_insertion.harness import HarnessConfig, SyntheticNameSource, run_sweep_experiment
from graph_insertion.strategies.embedding_threshold import (
    DEFAULT_THETA,
    EmbeddingThresholdStrategy,
)
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

class TestEmbeddingThresholdConformance(StrategyConformanceSuite):
    """Instantiate the reusable conformance suite on EmbeddingThresholdStrategy."""

    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(self) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
            strat = EmbeddingThresholdStrategy(theta=DEFAULT_THETA, seed=42)
            strat.setup(graph, embedder)
            return strat

        return _factory


# ===========================================================================
# 2. Threshold Logic with ControllableEmbedder
# ===========================================================================

class TestThresholdLogic:
    def test_threshold_shortlisting_and_ordering(self):
        base = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        vectors = {
            "probe": base,
            "c_95": vector_with_cosine(base, 0.95),
            "c_70": vector_with_cosine(base, 0.70),
            "c_61": vector_with_cosine(base, 0.61),
            "c_59": vector_with_cosine(base, 0.59),
            "c_00": vector_with_cosine(base, 0.0),
            "c_neg50": vector_with_cosine(base, -0.5),
        }
        embedder = ControllableEmbedder(vectors, dim=4)
        meter = MeteredEmbedder(embedder, record_texts=True)

        graph = ConceptGraph(domain_context="computer science")
        for node in ["c_95", "c_70", "c_61", "c_59", "c_00", "c_neg50"]:
            graph.add_node(node)

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        res = strat.shortlist("probe")
        # Exactly the three nodes with cosine > 0.6
        assert res.candidates == ("c_95", "c_70", "c_61")
        assert res.scores is not None
        assert len(res.scores) == 3
        expected_scores = (0.95, 0.70, 0.61)
        for s, exp in zip(res.scores, expected_scores):
            assert abs(s - exp) < 1e-6

        # Diagnostics check
        diag = strat.diagnostics()
        assert diag["cosine_comparisons"] == 6
        assert diag["threshold"] == 0.6
        assert diag["shortlist_size"] == 3
        assert abs(diag["max_cosine"] - 0.95) < 1e-6
        assert diag["index_size"] == 6

    def test_tie_breaking_alphabetical(self):
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        shared_vec = vector_with_cosine(base, 0.8)
        embedder = ControllableEmbedder(
            {
                "probe": base,
                "node_b": shared_vec,
                "node_a": shared_vec,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("node_b")
        graph.add_node("node_a")

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        res = strat.shortlist("probe")
        assert res.candidates == ("node_a", "node_b")

    def test_strict_boundary(self):
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        target_vec = vector_with_cosine(base, 0.6)
        embedder = ControllableEmbedder(
            {
                "probe": base,
                "target_node": target_vec,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("target_node")

        # Read exact score s
        strat_low = EmbeddingThresholdStrategy(theta=-1.0, seed=42)
        strat_low.setup(graph, meter)
        res_low = strat_low.shortlist("probe")
        assert len(res_low.scores) == 1
        s = res_low.scores[0]

        # theta == s must exclude (strict >)
        strat_exact = EmbeddingThresholdStrategy(theta=s, seed=42)
        strat_exact.setup(graph, meter)
        res_exact = strat_exact.shortlist("probe")
        assert "target_node" not in res_exact.candidates
        assert len(res_exact.candidates) == 0

        # theta slightly below s must include
        theta_below = float(np.nextafter(np.float32(s), np.float32(-2)))
        strat_below = EmbeddingThresholdStrategy(theta=theta_below, seed=42)
        strat_below.setup(graph, meter)
        res_below = strat_below.shortlist("probe")
        assert res_below.candidates == ("target_node",)

    def test_sensitivity_values_nested_sets(self):
        base = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        embedder = ControllableEmbedder(
            {
                "probe": base,
                "c_70": vector_with_cosine(base, 0.70),
                "c_55": vector_with_cosine(base, 0.55),
                "c_45": vector_with_cosine(base, 0.45),
                "c_30": vector_with_cosine(base, 0.30),
            },
            dim=4,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        for n in ["c_70", "c_55", "c_45", "c_30"]:
            graph.add_node(n)

        strat_06 = EmbeddingThresholdStrategy(theta=0.6)
        strat_06.setup(graph, meter)
        s_06 = strat_06.shortlist("probe").candidates

        strat_05 = EmbeddingThresholdStrategy(theta=0.5)
        strat_05.setup(graph, meter)
        s_05 = strat_05.shortlist("probe").candidates

        strat_04 = EmbeddingThresholdStrategy(theta=0.4)
        strat_04.setup(graph, meter)
        s_04 = strat_04.shortlist("probe").candidates

        assert s_06 == ("c_70",)
        assert s_05 == ("c_70", "c_55")
        assert s_04 == ("c_70", "c_55", "c_45")
        assert set(s_06).issubset(set(s_05))
        assert set(s_05).issubset(set(s_04))

    def test_unnormalised_vectors_handled_correctly(self):
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v1 = vector_with_cosine(base, 0.8)
        v2 = vector_with_cosine(base, 0.7)

        # Supply wildly unnormalised vectors
        embedder = ControllableEmbedder(
            {
                "probe": base * 3.5,
                "node_scaled_large": v1 * 7.3,
                "node_scaled_small": v2 * 0.01,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("node_scaled_large")
        graph.add_node("node_scaled_small")

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        res = strat.shortlist("probe")
        assert res.candidates == ("node_scaled_large", "node_scaled_small")
        assert abs(res.scores[0] - 0.8) < 1e-6
        assert abs(res.scores[1] - 0.7) < 1e-6

    def test_zero_candidates_skips_llm_and_indexes_node(self):
        base = np.array([1.0, 0.0], dtype=np.float32)
        embedder = ControllableEmbedder(
            {
                "probe": base,
                "node_low": vector_with_cosine(base, 0.2),
            },
            dim=2,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("node_low")

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        decision_step = FakeDecisionStep(make_edge=True)
        res = insert_node(strat, graph, decision_step, "probe", metered_embedder=meter)

        assert res.shortlist.candidates == ()
        assert res.shortlist.scores == ()
        assert res.edges == ()
        assert res.metrics.llm_calls == 0
        assert graph.has_node("probe")
        assert strat.diagnostics()["index_size"] == 2


# ===========================================================================
# 3. Single-Embedding Invariant & Lifecycle
# ===========================================================================

class TestSingleEmbeddingInvariantAndLifecycle:
    def test_single_embedding_invariant_through_insert_node(self):
        raw_embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("alpha")
        graph.add_node("beta")

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)
        meter.reset()

        decision_step = FakeDecisionStep(make_edge=False)
        res = insert_node(strat, graph, decision_step, "gamma", metered_embedder=meter)

        assert res.metrics.embedding_calls == 1
        assert res.metrics.embedding_calls_in_update == 0
        assert res.metrics.embed_in_update_s == 0.0

    def test_empty_initial_graph(self):
        raw_embedder = FakeEmbedder(dim=16, seed=42)
        meter = MeteredEmbedder(raw_embedder)

        graph = ConceptGraph(domain_context="computer science")
        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        # Before shortlist on empty graph
        assert strat.diagnostics()["index_size"] == 0
        assert strat.diagnostics()["max_cosine"] is None

        decision_step = FakeDecisionStep(make_edge=False)
        res = insert_node(strat, graph, decision_step, "first_node", metered_embedder=meter)

        assert res.metrics.embedding_calls == 1
        assert res.metrics.embedding_calls_in_update == 0
        assert res.metrics.embed_in_update_s == 0.0
        assert strat.diagnostics()["index_size"] == 1
        assert graph.has_node("first_node")

    def test_on_inserted_updates_index_and_subsequent_shortlist_sees_it(self):
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v_x = vector_with_cosine(base, 0.9)
        v_y = vector_with_cosine(v_x, 0.85)

        embedder = ControllableEmbedder(
            {
                "node_x": v_x,
                "node_y": v_y,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        # Insert node_x
        decision_step = FakeDecisionStep(make_edge=False)
        insert_node(strat, graph, decision_step, "node_x", metered_embedder=meter)

        # Shortlist node_y: node_x should now be in the index and shortlisted
        res = strat.shortlist("node_y")
        assert "node_x" in res.candidates

    def test_on_inserted_without_shortlist_raises_runtime_error(self):
        strat = EmbeddingThresholdStrategy(theta=0.6)
        graph = ConceptGraph(domain_context="computer science")
        meter = MeteredEmbedder(FakeEmbedder(dim=16))
        strat.setup(graph, meter)

        with pytest.raises(RuntimeError, match="without matching prior shortlist"):
            strat.on_inserted("unseen_node", ())

    def test_inserting_duplicate_name_raises_value_error(self):
        strat = EmbeddingThresholdStrategy(theta=0.6)
        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("existing")
        meter = MeteredEmbedder(FakeEmbedder(dim=16))
        strat.setup(graph, meter)

        # shortlist existing
        strat.shortlist("existing")
        with pytest.raises(ValueError, match="already indexed"):
            strat.on_inserted("existing", ())


# ===========================================================================
# 4. Buffer Growth & Brute-Force Match
# ===========================================================================

class TestBufferGrowthAndEquivalence:
    def test_buffer_growth_matches_brute_force_numpy_reference(self):
        dim = 16
        embedder = ControllableEmbedder(dim=dim, seed=42)
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        for init_node in ["init_1", "init_2", "init_3"]:
            graph.add_node(init_node)

        strat = EmbeddingThresholdStrategy(theta=0.4, seed=42)
        strat.setup(graph, meter)

        decision_step = FakeDecisionStep(make_edge=False)

        # Insert 300 nodes to exercise buffer doubling multiple times (16 -> 32 -> 64 -> 128 -> 256 -> 512)
        for i in range(300):
            node_name = f"concept_{i:04d}"
            insert_node(strat, graph, decision_step, node_name, metered_embedder=meter)
            assert strat.diagnostics()["index_size"] == graph.num_nodes()

        assert graph.num_nodes() == 303

        # Run a probe through shortlist and compare with exact brute-force numpy computation
        probe = "probe_concept"
        res = strat.shortlist(probe)

        # Brute-force calculation:
        raw_probe = meter.embed(embed_text(probe))
        q = raw_probe / np.linalg.norm(raw_probe)

        all_nodes = sorted(graph.nodes())
        all_vecs = [meter.embed(embed_text(n)) for n in all_nodes]
        mat = np.vstack([v / np.linalg.norm(v) for v in all_vecs]).astype(np.float32)

        bf_scores = mat @ q.astype(np.float32)
        bf_matches = [
            (float(bf_scores[i]), all_nodes[i])
            for i in range(len(all_nodes))
            if bf_scores[i] > 0.4 and all_nodes[i] != probe
        ]
        bf_matches.sort(key=lambda item: (-item[0], item[1]))

        expected_cands = tuple(name for _, name in bf_matches)
        expected_scores = tuple(score for score, _ in bf_matches)

        assert res.candidates == expected_cands
        assert len(res.scores) == len(expected_scores)
        for s, exp in zip(res.scores, expected_scores):
            assert abs(s - exp) < 1e-6


# ===========================================================================
# 5. Validation, Safety, and Bound Checks
# ===========================================================================

class TestValidationAndContracts:
    def test_theta_validation(self):
        with pytest.raises(ValueError, match="real number"):
            EmbeddingThresholdStrategy(theta=True)
        with pytest.raises(ValueError, match="finite number"):
            EmbeddingThresholdStrategy(theta=float("nan"))
        with pytest.raises(ValueError, match="within \\[-1.0, 1.0\\]"):
            EmbeddingThresholdStrategy(theta=1.5)
        with pytest.raises(ValueError, match="within \\[-1.0, 1.0\\]"):
            EmbeddingThresholdStrategy(theta=-1.1)
        with pytest.raises(ValueError, match="real number"):
            EmbeddingThresholdStrategy(theta="0.6")

    def test_float32_boundary_strict_greater_than(self):
        """Test F-2: strict > comparison acts on float64 values, not float32."""
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        target_vec = vector_with_cosine(base, 0.6)
        
        embedder = ControllableEmbedder(
            {
                "probe": base,
                "target_node": target_vec,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        graph.add_node("target_node")

        # Read exact float32 score s with theta=-1.0
        strat_low = EmbeddingThresholdStrategy(theta=-1.0, seed=42)
        strat_low.setup(graph, meter)
        res_low = strat_low.shortlist("probe")
        assert len(res_low.scores) == 1
        s = res_low.scores[0]  # This is the float32 score as returned

        # theta = float(np.nextafter(s, -2.0)) is strictly below s in float64
        theta_below = float(np.nextafter(np.float64(s), np.float64(-2.0)))
        strat_below = EmbeddingThresholdStrategy(theta=theta_below, seed=42)
        strat_below.setup(graph, meter)
        res_below = strat_below.shortlist("probe")
        # s > theta_below must be True, so target_node must be shortlisted
        assert res_below.candidates == ("target_node",), \
            f"Score {s} > theta {theta_below} should shortlist target_node"

        # theta = s must exclude (strict >)
        strat_exact = EmbeddingThresholdStrategy(theta=s, seed=42)
        strat_exact.setup(graph, meter)
        res_exact = strat_exact.shortlist("probe")
        assert "target_node" not in res_exact.candidates, \
            f"Score {s} is not > theta {s}, so target_node should be excluded"

    def test_embedder_error_validation(self):
        # Zero-norm during setup
        bad_emb_zero = ControllableEmbedder({"node_a": [0.0, 0.0]}, dim=2)
        g = ConceptGraph(domain_context="cs")
        g.add_node("node_a")
        strat = EmbeddingThresholdStrategy(theta=0.6)
        with pytest.raises(ValueError, match="Zero-norm embedding vector for node 'node_a'"):
            strat.setup(g, bad_emb_zero)

        # Dimension mismatch in shortlist
        good_emb = FakeEmbedder(dim=4)
        g2 = ConceptGraph(domain_context="cs")
        g2.add_node("node_a")
        strat2 = EmbeddingThresholdStrategy(theta=0.6)
        strat2.setup(g2, good_emb)

        strat2._embedder = FakeEmbedder(dim=8)
        with pytest.raises(ValueError, match="Dimension mismatch for 'node_b'"):
            strat2.shortlist("node_b")

    def test_no_max_candidates_and_upper_bound_fallback(self):
        strat = EmbeddingThresholdStrategy(theta=0.6)
        assert not hasattr(strat, "max_candidates")
        for n in (0, 29, 2000):
            assert candidate_upper_bound(strat, n) == n

    def test_json_serialization_safety(self):
        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        g = ConceptGraph(domain_context="cs")
        g.add_node("node_a")
        emb = FakeEmbedder(dim=8)
        strat.setup(g, emb)

        # Before shortlist
        json.dumps(strat.config())
        json.dumps(strat.diagnostics())

        res = strat.shortlist("node_b")
        json.dumps(strat.diagnostics())
        json.dumps(res.scores)

    def test_inserted_rows_are_normalized(self):
        """Test T-2: inserted rows are normalized (kills mutation G8)."""
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v_high = vector_with_cosine(base, 0.9)
        
        # Register an unnormalized vector (scaled by 7.3)
        embedder = ControllableEmbedder(
            {
                "inserted": v_high * 7.3,
                "probe": base * 0.01,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="cs")
        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        # Insert via driver
        decision_step = FakeDecisionStep(make_edge=False)
        insert_node(strat, graph, decision_step, "inserted", metered_embedder=meter)

        # Now shortlist probe: if inserted row is normalized, cosine should be 0.9
        res = strat.shortlist("probe")
        assert "inserted" in res.candidates
        idx = res.candidates.index("inserted")
        score = res.scores[idx]
        assert abs(score - 0.9) < 1e-6, f"Expected cosine 0.9, got {score}"

    def test_exclusion_of_new_name_when_already_indexed(self):
        """Test T-3: new_name excluded even if already in index (kills mutation G6)."""
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v_high = vector_with_cosine(base, 0.9)
        
        embedder = ControllableEmbedder(
            {
                "aa": base,
                "bb": v_high,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="cs")
        graph.add_node("aa")
        graph.add_node("bb")

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)

        # shortlist("aa") when aa is already indexed: self-cosine is 1.0 but must be excluded
        res = strat.shortlist("aa")
        assert "aa" not in res.candidates, "new_name must be excluded even if already indexed"
        assert res.candidates == ("bb",), "Only bb should be shortlisted"

    def test_setup_twice_resets_state(self):
        """Test T-4: setup() twice resets all state correctly."""
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v1 = vector_with_cosine(base, 0.8)
        v2 = vector_with_cosine(base, 0.7)
        
        embedder = ControllableEmbedder(
            {
                "a1": v1,
                "a2": v1,
                "a3": v1,
                "b1": v2,
                "b2": v2,
                "probe": base,
            },
            dim=3,
        )
        meter = MeteredEmbedder(embedder)

        graph_a = ConceptGraph(domain_context="cs")
        for n in ["a1", "a2", "a3"]:
            graph_a.add_node(n)

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph_a, meter)
        assert strat.diagnostics()["index_size"] == 3

        res_a = strat.shortlist("probe")
        assert set(res_a.candidates) == {"a1", "a2", "a3"}

        # Setup again on graph_b
        graph_b = ConceptGraph(domain_context="cs")
        for n in ["b1", "b2"]:
            graph_b.add_node(n)
        strat.setup(graph_b, meter)
        assert strat.diagnostics()["index_size"] == 2

        res_b = strat.shortlist("probe")
        assert set(res_b.candidates) == {"b1", "b2"}
        assert "a1" not in res_b.candidates

        # Setup on empty graph
        graph_empty = ConceptGraph(domain_context="cs")
        strat.setup(graph_empty, meter)
        assert strat.diagnostics()["index_size"] == 0
        res_empty = strat.shortlist("probe")
        assert len(res_empty.candidates) == 0

    def test_failed_setup_leaves_strategy_not_set_up(self):
        """Test T-4 (failed setup): a failed setup() leaves strategy not set up."""
        class BadEmbedder:
            """Returns a zero vector on second call."""
            def __init__(self, dim):
                self.dim = dim
                self.call_count = 0
            
            def embed(self, text):
                return np.ones(self.dim, dtype=np.float32)
            
            def embed_many(self, texts):
                self.call_count += 1
                if self.call_count == 1:
                    # First call: good vectors
                    return np.ones((len(texts), self.dim), dtype=np.float32)
                else:
                    # Second call: zero row triggers ValueError
                    mat = np.ones((len(texts), self.dim), dtype=np.float32)
                    mat[0] = 0.0
                    return mat

        graph1 = ConceptGraph(domain_context="cs")
        graph1.add_node("node_a")

        bad_emb = BadEmbedder(dim=8)
        strat = EmbeddingThresholdStrategy(theta=0.6)
        strat.setup(graph1, bad_emb)
        assert strat._setup_called == True
        assert strat.diagnostics()["index_size"] == 1

        # Second setup with bad embedder
        graph2 = ConceptGraph(domain_context="cs")
        graph2.add_node("node_b")
        
        with pytest.raises(ValueError, match="Zero-norm"):
            strat.setup(graph2, bad_emb)

        # After failed setup, strategy is not set up
        assert strat._setup_called == False
        assert strat.diagnostics()["index_size"] == 0
        
        with pytest.raises(RuntimeError, match="setup.*must be called"):
            strat.shortlist("node_c")

        # A subsequent successful setup works
        good_emb = FakeEmbedder(dim=8)
        graph3 = ConceptGraph(domain_context="cs")
        graph3.add_node("node_d")
        strat.setup(graph3, good_emb)
        assert strat._setup_called == True
        assert strat.diagnostics()["index_size"] == 1

    def test_payload_and_identity_via_metered_embedder(self):
        """Test T-5: payload is embed_text only, and identity is preserved."""
        base = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v1 = vector_with_cosine(base, 0.8)
        v2 = vector_with_cosine(base, 0.7)
        
        embedder = ControllableEmbedder(
            {
                "concept_a": v1,
                "concept_b": v2,
                "new_concept": base,
            },
            dim=3,
            strict=True,  # KeyError on any unregistered text
        )
        meter = MeteredEmbedder(embedder, record_texts=True)

        graph = ConceptGraph(domain_context="cs")
        for n in ["concept_a", "concept_b"]:
            graph.add_node(n)

        strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
        strat.setup(graph, meter)
        
        # Verify identity
        assert strat._embedder is meter

        meter.reset()
        decision_step = FakeDecisionStep(make_edge=False)
        insert_node(strat, graph, decision_step, "new_concept", metered_embedder=meter)

        # All logged texts must be embed_text(c) for registered concepts
        all_concepts = {"concept_a", "concept_b", "new_concept"}
        for text in meter.texts_log:
            assert "_" not in text
            assert any(embed_text(c) == text for c in all_concepts)

        # Exactly 1 embed call during insertion (single-embedding invariant)
        # This is already covered by conformance, but we verify here too
        assert meter.calls == 1

    def test_validation_of_embedder_output_in_shortlist(self):
        """Test T-6: validation of embedder output (NaN, zero, dimension)."""
        class BadEmbedder:
            def __init__(self, dim, bad_type):
                self.dim = dim
                self.bad_type = bad_type
            
            def embed(self, text):
                if self.bad_type == "nan":
                    vec = np.ones(self.dim, dtype=np.float32)
                    vec[0] = np.nan
                    return vec
                elif self.bad_type == "zero":
                    return np.zeros(self.dim, dtype=np.float32)
                elif self.bad_type == "wrong_dim":
                    return np.ones(self.dim + 5, dtype=np.float32)
                else:
                    return np.ones(self.dim, dtype=np.float32)
            
            def embed_many(self, texts):
                if self.bad_type == "nan_in_setup":
                    mat = np.ones((len(texts), self.dim), dtype=np.float32)
                    mat[0, 0] = np.nan
                    return mat
                elif self.bad_type == "non_2d":
                    return np.ones(self.dim, dtype=np.float32)  # 1-D instead of 2-D
                else:
                    return np.ones((len(texts), self.dim), dtype=np.float32)

        graph = ConceptGraph(domain_context="cs")
        graph.add_node("existing")

        # NaN in shortlist
        strat_nan = EmbeddingThresholdStrategy(theta=0.6)
        strat_nan.setup(graph, BadEmbedder(dim=8, bad_type="ok"))
        strat_nan._embedder = BadEmbedder(dim=8, bad_type="nan")
        with pytest.raises(ValueError, match="non-finite"):
            strat_nan.shortlist("new_node")
        # After failed shortlist, on_inserted should raise RuntimeError (no cached vector)
        with pytest.raises(RuntimeError, match="without matching prior shortlist"):
            strat_nan.on_inserted("new_node", ())

        # Zero norm in shortlist
        strat_zero = EmbeddingThresholdStrategy(theta=0.6)
        strat_zero.setup(graph, BadEmbedder(dim=8, bad_type="ok"))
        strat_zero._embedder = BadEmbedder(dim=8, bad_type="zero")
        with pytest.raises(ValueError, match="Zero-norm"):
            strat_zero.shortlist("new_node")

        # Wrong dimension in shortlist
        strat_dim = EmbeddingThresholdStrategy(theta=0.6)
        strat_dim.setup(graph, BadEmbedder(dim=8, bad_type="ok"))
        strat_dim._embedder = BadEmbedder(dim=8, bad_type="wrong_dim")
        with pytest.raises(ValueError, match="Dimension mismatch"):
            strat_dim.shortlist("new_node")

        # NaN in setup (embed_many)
        strat_setup_nan = EmbeddingThresholdStrategy(theta=0.6)
        graph2 = ConceptGraph(domain_context="cs")
        graph2.add_node("node_a")
        with pytest.raises(ValueError, match="non-finite"):
            strat_setup_nan.setup(graph2, BadEmbedder(dim=8, bad_type="nan_in_setup"))

        # Non-2D from embed_many
        strat_setup_2d = EmbeddingThresholdStrategy(theta=0.6)
        with pytest.raises(ValueError, match="2-D ndarray"):
            strat_setup_2d.setup(graph2, BadEmbedder(dim=8, bad_type="non_2d"))

    def test_buffer_growth_non_vacuity(self):
        """Test T-7: non-vacuity assertion in buffer growth test."""
        dim = 16
        embedder = ControllableEmbedder(dim=dim, seed=42)
        meter = MeteredEmbedder(embedder)

        graph = ConceptGraph(domain_context="computer science")
        for init_node in ["init_1", "init_2", "init_3"]:
            graph.add_node(init_node)

        strat = EmbeddingThresholdStrategy(theta=0.4, seed=42)
        strat.setup(graph, meter)

        decision_step = FakeDecisionStep(make_edge=False)

        # Insert 300 nodes
        for i in range(300):
            node_name = f"concept_{i:04d}"
            insert_node(strat, graph, decision_step, node_name, metered_embedder=meter)

        # Probe and compute expected
        probe = "probe_concept"
        res = strat.shortlist(probe)

        # Brute-force reference
        raw_probe = meter.embed(embed_text(probe))
        q = raw_probe / np.linalg.norm(raw_probe)

        all_nodes = sorted(graph.nodes())
        all_vecs = [meter.embed(embed_text(n)) for n in all_nodes]
        mat = np.vstack([v / np.linalg.norm(v) for v in all_vecs]).astype(np.float32)

        bf_scores = mat @ q.astype(np.float32)
        bf_matches = [
            (float(bf_scores[i]), all_nodes[i])
            for i in range(len(all_nodes))
            if bf_scores[i] > 0.4 and all_nodes[i] != probe
        ]
        bf_matches.sort(key=lambda item: (-item[0], item[1]))

        expected_cands = tuple(name for _, name in bf_matches)
        
        # Non-vacuity assertion
        assert len(expected_cands) >= 1, "Expected non-empty candidate set at theta=0.4"
        assert res.candidates == expected_cands

    def test_no_reallocation_on_first_insert_after_setup(self):
        """Test T-8: first insert after setup() does not reallocate (F-1 fix)."""
        for n in [1, 15, 16, 50, 2000]:
            embedder = ControllableEmbedder(dim=16, seed=42 + n)
            meter = MeteredEmbedder(embedder)

            graph = ConceptGraph(domain_context="cs")
            for i in range(n):
                graph.add_node(f"node_{i:04d}")

            strat = EmbeddingThresholdStrategy(theta=0.6, seed=42)
            strat.setup(graph, meter)

            # Capacity after setup should be >= n + 1
            assert strat._mat.shape[0] >= n + 1, \
                f"Capacity {strat._mat.shape[0]} < {n + 1} after setup with {n} nodes"

            mat_before = strat._mat
            new_name = f"node_{n:04d}"
            
            decision_step = FakeDecisionStep(make_edge=False)
            insert_node(strat, graph, decision_step, new_name, metered_embedder=meter)

            # Same object => no reallocation
            assert strat._mat is mat_before, \
                f"Matrix reallocated on first insert after setup for n={n}"

        # Also test that growth happens on a sequence crossing a doubling
        embedder2 = ControllableEmbedder(dim=16, seed=999)
        meter2 = MeteredEmbedder(embedder2)
        graph2 = ConceptGraph(domain_context="cs")
        for i in range(16):
            graph2.add_node(f"base_{i:04d}")

        strat2 = EmbeddingThresholdStrategy(theta=0.6, seed=999)
        strat2.setup(graph2, meter2)
        
        # Capacity should be max(16, 2*16) = 32
        assert strat2._mat.shape[0] == 32

        # Insert 16 more (fills to 32)
        ds2 = FakeDecisionStep(make_edge=False)
        for i in range(16):
            insert_node(strat2, graph2, ds2, f"added_{i:04d}", metered_embedder=meter2)
        
        assert strat2._n == 32
        mat_at_32 = strat2._mat

        # Next insert triggers doubling
        insert_node(strat2, graph2, ds2, "trigger_double", metered_embedder=meter2)
        assert strat2._mat is not mat_at_32, "Should have reallocated at capacity boundary"
        assert strat2._mat.shape[0] == 64, "Should have doubled to 64"


# ===========================================================================
# 6. Harness Smoke Test
# ===========================================================================

class TestHarnessSmoke:
    def test_embedding_threshold_through_sweep_harness(self, tmp_path: Path):
        out_dir = tmp_path / "sweep_thresh"
        name_source = SyntheticNameSource(
            names=[f"synth_{i:04d}" for i in range(20)],
            domain_context="computer science",
        )
        config = HarnessConfig(
            mode="sweep",
            run_id="test_sweep_strat2",
            output_dir=out_dir,
            seed=42,
            sweep_sizes=(3,),
            sweep_trials_per_size=1,
            confirm=True,
        )

        res = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: EmbeddingThresholdStrategy(theta=0.6, seed=42),
            decision_step=FakeDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
            name_source=name_source,
        )
        assert res["status"] == "completed"

        raw_path = out_dir / "raw.jsonl"
        assert raw_path.exists()
        records = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
        assert len(records) == 1

        rec = records[0]
        assert rec["strategy"] == "embedding_threshold"
        assert rec["status"] == "success"
        m = rec["metrics"]
        assert m["embedding_calls"] == 1
        assert m["embedding_calls_in_update"] == 0
        assert m["extra"]["threshold"] == 0.6
        assert m["extra"]["cosine_comparisons"] == 3
        assert m["extra"]["index_size"] == 4
