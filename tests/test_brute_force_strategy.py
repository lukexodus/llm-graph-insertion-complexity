"""
tests/test_brute_force_strategy.py — STRAT-001
================================================
Unit tests, conformance tests, driver tests, scale sanity, and harness smoke test
for BruteForceStrategy (Strategy 1).

Decisions tested:
  - [D-24]: Narrowing-only protocol (zero LLM calls within strategy).
  - [D-29]: Pairwise decision step (llm_calls == n_existing).
  - [D-38](2): uses_embeddings = False conformance semantics (zero embedder activity).
  - [D-41]: max_candidates(n) = n exact upper bound.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

from graph_insertion.embedding import FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    run_sweep_experiment,
)
from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
from graph_insertion.decision import PairwiseDecisionStep
from graph_insertion.strategies.brute_force import BruteForceStrategy
from graph_insertion.strategy import (
    DecisionStep,
    candidate_upper_bound,
    insert_node,
)
from tests.test_strategy_interface import (
    FakeDecisionStep,
    StrategyConformanceSuite,
)


# ===========================================================================
# Helpers
# ===========================================================================

def make_placeholder_names(n: int, offset: int = 0) -> list[str]:
    """Generate n unique placeholder concept names for offline test harness use only."""
    return [f"placeholder_concept_{i + offset:05d}" for i in range(n)]


def make_fake_decision_step() -> DecisionStep:
    """Return an offline pairwise decision step with FakeLLMClient."""
    client = MeteredLLMClient(FakeLLMClient())
    return PairwiseDecisionStep(client)


def make_fake_embedder() -> FakeEmbedder:
    return FakeEmbedder(dim=16, seed=42)


# ===========================================================================
# 1. Conformance Suite (StrategyConformanceSuite)
# ===========================================================================

class TestBruteForceConformance(StrategyConformanceSuite):
    """BruteForceStrategy must satisfy all non-embedding conformance invariants."""

    uses_embeddings: bool = False

    @pytest.fixture
    def strategy_factory(self) -> Callable[[ConceptGraph, FakeEmbedder], BruteForceStrategy]:
        def _factory(graph: ConceptGraph, embedder: FakeEmbedder) -> BruteForceStrategy:
            strat = BruteForceStrategy(seed=42)
            strat.setup(graph, embedder)
            return strat

        return _factory


# ===========================================================================
# 2. Unit Tests
# ===========================================================================

class TestBruteForceUnit:
    """Unit tests covering the BruteForceStrategy API contract."""

    def test_shortlist_all_nodes_sorted_ascending_and_scores_zero(self) -> None:
        g = ConceptGraph(domain_context="computer science")
        for name in ["delta", "beta", "alpha", "gamma"]:
            g.add_node(name)
        strat = BruteForceStrategy(seed=42)
        strat.setup(g, FakeEmbedder())
        sl = strat.shortlist("epsilon")
        assert sl.candidates == ("alpha", "beta", "delta", "gamma")
        assert sl.scores == (0.0, 0.0, 0.0, 0.0)
        assert len(sl.scores) == len(sl.candidates)

    def test_shortlist_excludes_new_name_even_if_already_in_graph(self) -> None:
        g = ConceptGraph(domain_context="computer science")
        for name in ["alpha", "beta", "gamma"]:
            g.add_node(name)
        strat = BruteForceStrategy(seed=42)
        strat.setup(g, FakeEmbedder())
        sl = strat.shortlist("beta")
        assert sl.candidates == ("alpha", "gamma")
        assert "beta" not in sl.candidates
        assert sl.scores == (0.0, 0.0)

    def test_shortlist_empty_graph(self) -> None:
        g = ConceptGraph()
        strat = BruteForceStrategy(seed=42)
        strat.setup(g, FakeEmbedder())
        sl = strat.shortlist("alpha")
        assert sl.candidates == ()
        assert sl.scores == ()

    def test_shortlist_order_independent_of_graph_insertion_order(self) -> None:
        g1 = ConceptGraph()
        for name in ["zebra", "apple", "mango"]:
            g1.add_node(name)
        g2 = ConceptGraph()
        for name in ["mango", "zebra", "apple"]:
            g2.add_node(name)
        strat1 = BruteForceStrategy(seed=1)
        strat1.setup(g1, FakeEmbedder())
        strat2 = BruteForceStrategy(seed=2)
        strat2.setup(g2, FakeEmbedder())
        sl1 = strat1.shortlist("banana")
        sl2 = strat2.shortlist("banana")
        assert sl1.candidates == sl2.candidates == ("apple", "mango", "zebra")
        assert sl1.scores == sl2.scores == (0.0, 0.0, 0.0)

    def test_max_candidates_unsetup_instance(self) -> None:
        strat = BruteForceStrategy(seed=42)
        for n in (0, 1, 29, 2000):
            assert strat.max_candidates(n) == n
            assert candidate_upper_bound(strat, n) == n

    def test_full_matrix_bound_d35(self) -> None:
        """Sum of candidate_upper_bound over the D-35 matrix (6 sizes x 10 trials) == 38,500."""
        strat = BruteForceStrategy(seed=42)
        sweep_sizes = (50, 100, 200, 500, 1000, 2000)  # D-35 sweep sizes
        total = sum(candidate_upper_bound(strat, n) * 10 for n in sweep_sizes)
        assert total == 38_500

    def test_shortlist_before_setup_raises_runtime_error(self) -> None:
        strat = BruteForceStrategy(seed=42)
        with pytest.raises(RuntimeError, match="setup.*must be called"):
            strat.shortlist("new_concept")

    def test_embedder_remains_none_after_setup(self) -> None:
        g = ConceptGraph()
        g.add_node("concept_a")
        meter = MeteredEmbedder(FakeEmbedder())
        strat = BruteForceStrategy(seed=42)
        strat.setup(g, meter)
        assert strat._embedder is None

    def test_config_and_diagnostics_json_serializable(self) -> None:
        strat = BruteForceStrategy(seed=123)
        cfg = strat.config()
        diag_before = strat.diagnostics()
        assert json.dumps(cfg) == '{"seed": 123}'
        assert json.dumps(diag_before) == '{"candidate_count": 0}'

        g = ConceptGraph()
        g.add_node("alpha")
        g.add_node("beta")
        strat.setup(g, FakeEmbedder())
        strat.shortlist("gamma")
        diag_after = strat.diagnostics()
        assert json.dumps(diag_after) == '{"candidate_count": 2}'


# ===========================================================================
# 3. Driver Tests via insert_node
# ===========================================================================

class TestBruteForceDriver:
    """Driver tests executing insert_node pipeline with BruteForceStrategy."""

    @pytest.mark.parametrize("n", [1, 5, 29])
    def test_driver_insert_node_metrics_at_sizes_1_5_29(self, n: int) -> None:
        g = ConceptGraph(domain_context="computer science")
        for i in range(n):
            g.add_node(f"node_{i:04d}")

        strat = BruteForceStrategy(seed=42)
        meter = MeteredEmbedder(FakeEmbedder())
        strat.setup(g, meter)
        decision_step = FakeDecisionStep(make_edge=True)

        res = insert_node(
            strat, g, decision_step, "new_node", metered_embedder=meter
        )
        assert res.metrics.n_before == n
        assert res.metrics.shortlist_size == n
        assert res.metrics.llm_calls == n
        assert meter.calls == 0
        assert meter.cumulative_seconds == 0.0
        assert res.metrics.embedding_calls == 0
        assert res.metrics.embed_s == 0.0
        assert res.metrics.embedding_calls_in_update == 0
        assert res.metrics.embed_in_update_s == 0.0

    def test_driver_successive_insertions_accumulate(self) -> None:
        initial_n = 3
        g = ConceptGraph(domain_context="computer science")
        for i in range(initial_n):
            g.add_node(f"initial_{i}")

        strat = BruteForceStrategy(seed=42)
        meter = MeteredEmbedder(FakeEmbedder())
        strat.setup(g, meter)
        decision_step = FakeDecisionStep(make_edge=True)

        inserted_nodes = ["added_1", "added_2", "added_3", "added_4"]
        for k, name in enumerate(inserted_nodes):
            res = insert_node(
                strat, g, decision_step, name, metered_embedder=meter
            )
            assert res.metrics.n_before == initial_n + k
            assert res.metrics.shortlist_size == initial_n + k
            for prev_name in inserted_nodes[:k]:
                assert prev_name in res.shortlist.candidates

        final_sl = strat.shortlist("final_probe")
        assert len(final_sl.candidates) == initial_n + len(inserted_nodes)
        for name in inserted_nodes:
            assert name in final_sl.candidates


# ===========================================================================
# 4. Scale Sanity
# ===========================================================================

class TestBruteForceScaleSanity:
    """Scale sanity verification with a 2000-node graph (no timing assertions)."""

    def test_scale_sanity_2000_nodes(self) -> None:
        g = ConceptGraph(domain_context="computer science")
        names = [f"concept_{i:05d}" for i in range(2000)]
        for name in names:
            g.add_node(name)

        strat = BruteForceStrategy(seed=42)
        strat.setup(g, FakeEmbedder())
        sl = strat.shortlist("probe_concept")
        assert len(sl.candidates) == 2000
        assert len(set(sl.candidates)) == 2000
        assert sl.candidates == tuple(sorted(names))
        assert len(sl.scores) == 2000
        assert all(s == 0.0 for s in sl.scores)


# ===========================================================================
# 5. Harness Smoke Test
# ===========================================================================

class TestBruteForceHarnessSmoke:
    """Harness smoke test mirroring sweep-mode test in test_null_strategy.py."""

    def test_sweep_smoke(self, tmp_path: Path) -> None:
        name_source = SyntheticNameSource(
            names=make_placeholder_names(200),
            domain_context="computer science",
        )
        config = HarnessConfig(
            mode="sweep",
            run_id="test_brute_force_sweep_smoke",
            output_dir=tmp_path / "sweep_smoke",
            seed=42,
            sweep_sizes=(5, 10),
            sweep_trials_per_size=2,
            confirm=True,
        )
        result = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: BruteForceStrategy(seed=42),
            decision_step=make_fake_decision_step(),
            embedder_factory=make_fake_embedder,
            name_source=name_source,
        )
        assert result["status"] == "completed"

        raw_path = tmp_path / "sweep_smoke" / "raw.jsonl"
        records = [json.loads(line) for line in raw_path.read_text().strip().splitlines() if line.strip()]
        assert len(records) == 4  # 2 sizes x 2 trials
        for rec in records:
            assert rec["status"] == "success"
            assert rec["strategy"] == "brute_force"
            n = rec["size"]
            assert rec["metrics"]["llm_calls"] == n
            assert rec["metrics"]["shortlist_size"] == n
            assert rec["metrics"]["embedding_calls"] == 0
