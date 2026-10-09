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
