"""
test_dry_run_plan.py — FIX-016 Unit Tests
=========================================
Tests for estimate_and_print_plan() candidate upper bound calculation:
  1. Sweep plan over the D-35 matrix across all strategies (BruteForce,
     EmbeddingThreshold, AnnRetrieval, BoundedBucket, NullStrategy) and
     clamping when sweep size < cap.
  2. Accuracy plan with small fake corpora across all strategies, including
     per-corpus clamping when (nodes_count - 1) < cap.
  3. Parity between estimate_and_print_plan() and live guard
     compute_planned_calls_upper_bound() in scripts/run_experiment.py.
  4. Probe strategy instances work before setup() without mutating state.
  5. StubNarrowingStrategy(top_k=5) preserves min(5, n) cap behavior.
  6. Strategies without max_candidates fall back to n_existing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pytest

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    estimate_and_print_plan,
)
from graph_insertion.strategies.brute_force import BruteForceStrategy
from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
from graph_insertion.strategies.null import NullStrategy
from graph_insertion.strategy import Shortlist, candidate_upper_bound
from scripts.run_experiment import (
    StubNarrowingStrategy,
    compute_planned_calls_upper_bound,
)


D35_SWEEP_SIZES: tuple[int, ...] = (50, 100, 200, 500, 1000, 2000)
D35_TRIALS_PER_SIZE: int = 10


@dataclass
class _FakeLoadedCorpus:
    """Lightweight corpus stub exposing .graph.nodes() for accuracy dry-run tests."""

    graph: ConceptGraph


def _make_fake_corpus(n_nodes: int) -> _FakeLoadedCorpus:
    graph = ConceptGraph(domain_context="testing")
    for i in range(n_nodes):
        graph.add_node(f"node_{i:03d}")
    return _FakeLoadedCorpus(graph=graph)


def _make_name_source(n: int = 32) -> SyntheticNameSource:
    return SyntheticNameSource(
        names=[f"concept_{i:04d}" for i in range(n)],
        domain_context="computer science",
    )


class TestSweepDryRunPlan:
    """Verify sweep dry-run candidate and LLM call bounds across strategies."""

    def test_d35_sweep_matrix_non_faiss_strategies(self, capsys: pytest.CaptureFixture[str]) -> None:
        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=D35_SWEEP_SIZES,
            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
            dry_run=True,
        )
        source = _make_name_source()

        cases: list[tuple[Any, int]] = [
            (BruteForceStrategy(), 38_500),
            (EmbeddingThresholdStrategy(theta=0.45), 38_500),
            (BoundedBucketStrategy(s_min=5, s_max=10), 600),
            (BoundedBucketStrategy(s_min=2, s_max=5), 300),
            (BoundedBucketStrategy(s_min=10, s_max=20), 1_200),
            (NullStrategy(k=1), 60),
            (NullStrategy(k=5), 300),
        ]

        for strategy, expected_calls in cases:
            plan = estimate_and_print_plan(config, strategy, name_source=source)
            out = capsys.readouterr().out
            assert f"Strategy: {strategy.name}" in out
            assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out

            assert set(plan.keys()) == {
                "mode",
                "strategy",
                "strategy_config",
                "total_insertions",
                "upper_bound_llm_calls",
                "details",
            }
            assert plan["mode"] == "sweep"
            assert plan["strategy"] == strategy.name
            assert plan["strategy_config"] == strategy.config()
            assert plan["total_insertions"] == 60
            assert plan["upper_bound_llm_calls"] == expected_calls
            assert len(plan["details"]) == len(D35_SWEEP_SIZES)

            for detail, sz in zip(plan["details"], D35_SWEEP_SIZES):
                expected_cands = candidate_upper_bound(strategy, sz)
                assert detail == {
                    "size": sz,
                    "trials": D35_TRIALS_PER_SIZE,
                    "max_candidates_per_trial": expected_cands,
                    "upper_bound_llm_calls": D35_TRIALS_PER_SIZE * expected_cands,
                }

    def test_d35_sweep_matrix_ann_retrieval(self, capsys: pytest.CaptureFixture[str]) -> None:
        pytest.importorskip("faiss")
        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy

        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=D35_SWEEP_SIZES,
            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
            dry_run=True,
        )
        source = _make_name_source()

        for k, expected_calls in [(5, 300), (10, 600), (20, 1_200)]:
            strategy = AnnRetrievalStrategy(k=k)
            plan = estimate_and_print_plan(config, strategy, name_source=source)
            out = capsys.readouterr().out
            assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out
            assert plan["total_insertions"] == 60
            assert plan["upper_bound_llm_calls"] == expected_calls
            for detail, sz in zip(plan["details"], D35_SWEEP_SIZES):
                assert detail["max_candidates_per_trial"] == k
                assert detail["upper_bound_llm_calls"] == D35_TRIALS_PER_SIZE * k

    def test_sweep_clamps_when_graph_size_smaller_than_strategy_cap(self) -> None:
        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=(3, 7, 10, 25),
            sweep_trials_per_size=4,
            dry_run=True,
        )
        source = _make_name_source()
        strategy = BoundedBucketStrategy(s_min=5, s_max=10)

        plan = estimate_and_print_plan(config, strategy, name_source=source)
        cands_by_size = {d["size"]: d["max_candidates_per_trial"] for d in plan["details"]}
        assert cands_by_size == {3: 3, 7: 7, 10: 10, 25: 10}
        assert plan["upper_bound_llm_calls"] == 4 * (3 + 7 + 10 + 10)


class TestAccuracyDryRunPlan:
    """Verify accuracy dry-run candidate and LLM call bounds across strategies."""

    def test_accuracy_plan_non_faiss_strategies_and_clamping(self) -> None:
        # small_corpus has 7 nodes -> n_existing = 6 (clamps s_max=10 and s_max=20 to 6)
        # metacademy_mini has 15 nodes -> n_existing = 14, sampled at 8 nodes
        corpora: dict[str, Any] = {
            "small_corpus": _make_fake_corpus(7),
            "metacademy_mini": _make_fake_corpus(15),
        }
        config = HarnessConfig(
            mode="accuracy",
            repeats=2,
            metacademy_sample_size=8,
            dry_run=True,
        )

        strategies: list[Any] = [
            BruteForceStrategy(),
            EmbeddingThresholdStrategy(theta=0.45),
            BoundedBucketStrategy(s_min=5, s_max=10),
            BoundedBucketStrategy(s_min=2, s_max=5),
            BoundedBucketStrategy(s_min=10, s_max=20),
            NullStrategy(k=1),
            NullStrategy(k=5),
        ]

        for strategy in strategies:
            plan = estimate_and_print_plan(config, strategy, corpora=corpora)
            # small_corpus: sample_k = 7, trials = 14, n_existing = 6
            # metacademy_mini: sample_k = 8, trials = 16, n_existing = 14
            expected_small_cands = candidate_upper_bound(strategy, 6)
            expected_meta_cands = candidate_upper_bound(strategy, 14)
            expected_total_llm = 14 * expected_small_cands + 16 * expected_meta_cands

            assert plan["mode"] == "accuracy"
            assert plan["total_insertions"] == 30
            assert plan["upper_bound_llm_calls"] == expected_total_llm
            assert len(plan["details"]) == 2

            d_small, d_meta = plan["details"]
            assert d_small == {
                "corpus": "small_corpus",
                "nodes_in_graph": 7,
                "sample_size": 7,
                "held_out_trials": 14,
                "max_candidates_per_trial": expected_small_cands,
                "upper_bound_llm_calls": 14 * expected_small_cands,
            }
            assert d_meta == {
                "corpus": "metacademy_mini",
                "nodes_in_graph": 15,
                "sample_size": 8,
                "held_out_trials": 16,
                "max_candidates_per_trial": expected_meta_cands,
                "upper_bound_llm_calls": 16 * expected_meta_cands,
            }

        # Explicit clamp check on BoundedBucketStrategy(5, 10): n_existing=6 < s_max=10
        bb_plan = estimate_and_print_plan(
            config, BoundedBucketStrategy(s_min=5, s_max=10), corpora=corpora
        )
        assert bb_plan["details"][0]["max_candidates_per_trial"] == 6
        assert bb_plan["details"][1]["max_candidates_per_trial"] == 10
        assert bb_plan["upper_bound_llm_calls"] == 14 * 6 + 16 * 10

    def test_accuracy_plan_ann_retrieval_and_clamping(self) -> None:
        pytest.importorskip("faiss")
        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy

        corpora: dict[str, Any] = {
            "small_corpus": _make_fake_corpus(7),
            "metacademy_mini": _make_fake_corpus(15),
        }
        config = HarnessConfig(
            mode="accuracy",
            repeats=2,
            metacademy_sample_size=8,
            dry_run=True,
        )

        for k, expected_small, expected_meta in [(5, 5, 5), (10, 6, 10), (20, 6, 14)]:
            strategy = AnnRetrievalStrategy(k=k)
            plan = estimate_and_print_plan(config, strategy, corpora=corpora)
            assert plan["details"][0]["max_candidates_per_trial"] == expected_small
            assert plan["details"][1]["max_candidates_per_trial"] == expected_meta
            assert plan["upper_bound_llm_calls"] == 14 * expected_small + 16 * expected_meta


class TestLiveGuardParity:
    """Verify dry-run planner upper_bound_llm_calls matches compute_planned_calls_upper_bound."""

    def test_parity_with_live_guard_non_faiss(self) -> None:
        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=D35_SWEEP_SIZES,
            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
            dry_run=True,
        )
        acc_cfg = HarnessConfig(
            mode="accuracy",
            repeats=2,
            metacademy_sample_size=8,
            dry_run=True,
        )
        corpora: dict[str, Any] = {
            "small_corpus": _make_fake_corpus(7),
            "metacademy_mini": _make_fake_corpus(15),
        }
        source = _make_name_source()

        strategies: list[Any] = [
            BruteForceStrategy(),
            EmbeddingThresholdStrategy(theta=0.45),
            BoundedBucketStrategy(s_min=2, s_max=5),
            BoundedBucketStrategy(s_min=5, s_max=10),
            BoundedBucketStrategy(s_min=10, s_max=20),
            NullStrategy(k=1),
            NullStrategy(k=5),
        ]

        for strategy in strategies:
            sweep_plan = estimate_and_print_plan(sweep_cfg, strategy, name_source=source)
            sweep_guard = compute_planned_calls_upper_bound(sweep_cfg, strategy=strategy)
            assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound
            assert sweep_plan["total_insertions"] == sweep_guard.full_plan_trials

            acc_plan = estimate_and_print_plan(acc_cfg, strategy, corpora=corpora)
            acc_guard = compute_planned_calls_upper_bound(
                acc_cfg, corpora=corpora, strategy=strategy
            )
            assert acc_plan["upper_bound_llm_calls"] == acc_guard.full_plan_bound
            assert acc_plan["total_insertions"] == acc_guard.full_plan_trials

    def test_parity_with_live_guard_ann_retrieval(self) -> None:
        pytest.importorskip("faiss")
        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy

        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=D35_SWEEP_SIZES,
            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
            dry_run=True,
        )
        acc_cfg = HarnessConfig(
            mode="accuracy",
            repeats=2,
            metacademy_sample_size=8,
            dry_run=True,
        )
        corpora: dict[str, Any] = {
            "small_corpus": _make_fake_corpus(7),
            "metacademy_mini": _make_fake_corpus(15),
        }
        source = _make_name_source()

        for k in (5, 10, 20):
            strategy = AnnRetrievalStrategy(k=k)
            sweep_plan = estimate_and_print_plan(sweep_cfg, strategy, name_source=source)
            sweep_guard = compute_planned_calls_upper_bound(sweep_cfg, strategy=strategy)
            assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound

            acc_plan = estimate_and_print_plan(acc_cfg, strategy, corpora=corpora)
            acc_guard = compute_planned_calls_upper_bound(
                acc_cfg, corpora=corpora, strategy=strategy
            )
            assert acc_plan["upper_bound_llm_calls"] == acc_guard.full_plan_bound


class TestUnsetupProbeAndFallbackStrategies:
    """Verify probe strategies before setup(), StubNarrowingStrategy, and no-max_candidates fallback."""

    def test_unsetup_probe_strategies_work_and_remain_unsetup(self) -> None:
        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=(10, 50),
            sweep_trials_per_size=2,
            dry_run=True,
        )
        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
        corpora: dict[str, Any] = {"mini": _make_fake_corpus(6)}
        source = _make_name_source()

        probes: list[Any] = [
            BruteForceStrategy(),
            EmbeddingThresholdStrategy(),
            BoundedBucketStrategy(s_min=5, s_max=10),
            NullStrategy(k=5),
        ]
        for probe in probes:
            assert getattr(probe, "_setup_called", False) is False
            assert getattr(probe, "_graph", None) is None
            estimate_and_print_plan(sweep_cfg, probe, name_source=source)
            estimate_and_print_plan(acc_cfg, probe, corpora=corpora)
            assert getattr(probe, "_setup_called", False) is False
            assert getattr(probe, "_graph", None) is None

    def test_unsetup_ann_retrieval_probe_works_and_remains_unsetup(self) -> None:
        pytest.importorskip("faiss")
        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy

        probe = AnnRetrievalStrategy(k=10)
        assert probe._setup_called is False
        assert probe._index is None

        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=(10, 50),
            sweep_trials_per_size=2,
            dry_run=True,
        )
        plan = estimate_and_print_plan(sweep_cfg, probe, name_source=_make_name_source())
        assert plan["upper_bound_llm_calls"] == 40
        assert probe._setup_called is False
        assert probe._index is None

    def test_stub_narrowing_strategy_top_k_cap_unchanged(self) -> None:
        stub = StubNarrowingStrategy(top_k=5)
        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=(3, 5, 10, 50),
            sweep_trials_per_size=2,
            dry_run=True,
        )
        sweep_plan = estimate_and_print_plan(
            sweep_cfg, stub, name_source=_make_name_source()
        )
        assert [d["max_candidates_per_trial"] for d in sweep_plan["details"]] == [3, 5, 5, 5]
        assert sweep_plan["upper_bound_llm_calls"] == 2 * (3 + 5 + 5 + 5)

        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
        corpora: dict[str, Any] = {
            "tiny": _make_fake_corpus(4),   # n_existing = 3 -> min(5, 3) = 3
            "medium": _make_fake_corpus(9), # n_existing = 8 -> min(5, 8) = 5
        }
        acc_plan = estimate_and_print_plan(acc_cfg, stub, corpora=corpora)
        assert [d["max_candidates_per_trial"] for d in acc_plan["details"]] == [3, 5]
        assert acc_plan["upper_bound_llm_calls"] == 4 * 3 + 9 * 5

    def test_strategy_without_max_candidates_falls_back_to_n_existing(self) -> None:
        class NoCapStrategy:
            name = "no_cap_custom"
            uses_embeddings = False

            def setup(self, graph: Any, embedder: Any) -> None:
                pass

            def shortlist(self, new_name: str) -> Shortlist:
                return Shortlist(candidates=())

            def on_inserted(self, new_name: str, edges: Any) -> None:
                pass

            def config(self) -> dict[str, Any]:
                return {}

            def diagnostics(self) -> dict[str, Any]:
                return {}

        strat = NoCapStrategy()
        assert not hasattr(strat, "max_candidates")
        assert not hasattr(EmbeddingThresholdStrategy(), "max_candidates")

        sweep_cfg = HarnessConfig(
            mode="sweep",
            sweep_sizes=(12, 25),
            sweep_trials_per_size=3,
            dry_run=True,
        )
        sweep_plan = estimate_and_print_plan(
            sweep_cfg, strat, name_source=_make_name_source()
        )
        assert [d["max_candidates_per_trial"] for d in sweep_plan["details"]] == [12, 25]
        assert sweep_plan["upper_bound_llm_calls"] == 3 * (12 + 25)

        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
        corpora: dict[str, Any] = {"c1": _make_fake_corpus(11)}
        acc_plan = estimate_and_print_plan(acc_cfg, strat, corpora=corpora)
        assert acc_plan["details"][0]["max_candidates_per_trial"] == 10
        assert acc_plan["upper_bound_llm_calls"] == 11 * 10
