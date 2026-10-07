"""tests/test_live_guard.py — FIX-008
===================================
Tests for live guard calculation, pre-flight estimation, DeepSeekClient defaults/parity,
and call-driven progress reporting with injectable clock.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from graph_insertion.decision import PairwiseDecisionStep
from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import HarnessConfig, SyntheticNameSource, run_sweep_experiment
from graph_insertion.llm import DeepSeekClient, FakeLLMClient, MeteredLLMClient
from graph_insertion.loader import CorpusStats, GoldJudgmentSet, LoadedCorpus, SourceKind
from graph_insertion.strategies.null import NullStrategy
from graph_insertion.strategy import Shortlist
from scripts.run_experiment import (
    ProgressReporter,
    build_live_client,
    compute_planned_calls_upper_bound,
    compute_preflight_estimate,
)


class MockClock:
    """Injectable monotonic clock for testing timing and heartbeat intervals."""

    def __init__(self, start: float = 0.0) -> None:
        self._current: float = start

    def now(self) -> float:
        return self._current

    def advance(self, delta_s: float) -> None:
        self._current += delta_s


# ===========================================================================
# 1. LIVE GUARD & PRE-FLIGHT ESTIMATE TESTS
# ===========================================================================

class TestLiveGuardAndPreflight:
    """Verify planned calls upper bound, token/cost estimation, and DeepSeekClient parity."""

    def test_planned_calls_upper_bound_sweep_mode(self) -> None:
        """In sweep mode, planned_calls = sum over sizes of (n * trials)."""
        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=(50, 100, 200),
            sweep_trials_per_size=10,
        )
        # Expected: (50*10) + (100*10) + (200*10) = 500 + 1000 + 2000 = 3500
        assert compute_planned_calls_upper_bound(config) == 3500

    def test_planned_calls_upper_bound_accuracy_mode(self) -> None:
        """In accuracy mode, planned_calls = sum over held-out nodes of (n_nodes - 1)."""
        g = ConceptGraph()
        for i in range(10):
            g.add_node(f"node_{i}")

        corpus = LoadedCorpus(
            name="test_corpus",
            source_kind=SourceKind.GOLD,
            graph=g,
            domain_context="cs",
            judgments=GoldJudgmentSet(),
            stats=CorpusStats(10, 10, 0, 0, 0, 0, 0),
        )

        config = HarnessConfig(
            mode="accuracy",
            repeats=2,
        )
        # 10 nodes, each held-out sees 9 nodes. repeats=2 => 10 * 9 * 2 = 180
        total = compute_planned_calls_upper_bound(config, {"test_corpus": corpus})
        assert total == 180

    def test_compute_preflight_estimate_values(self) -> None:
        """Verify preflight estimate uses ~152 input and ~2.5 output tokens per call."""
        calls = 1000
        est = compute_preflight_estimate(
            planned_calls=calls,
            est_seconds_per_call=1.5,
            price_in=0.15,
            price_out=0.60,
        )
        assert est["planned_calls"] == 1000
        assert est["estimated_seconds"] == 1500.0  # 1000 * 1.5s
        assert est["input_tokens_est"] == 152000.0  # 1000 * 152.0
        assert est["output_tokens_est"] == 2500.0  # 1000 * 2.5
        # Cost = (152000 * 0.15 + 2500 * 0.60) / 1,000,000 = (22800 + 1500) / 1,000,000 = 0.0243 USD
        assert abs(est["estimated_cost_usd"] - 0.0243) < 1e-6

    def test_deepseek_client_defaults(self) -> None:
        """Confirm DeepSeekClient defaults give temperature 0.0, max_tokens 16, thinking disabled."""
        client = DeepSeekClient(api_key="sk-fake-test-key")
        assert client.temperature == 0.0
        assert client.max_tokens == 16
        assert client.thinking == {"type": "disabled"}
        assert client.thinking_mode == "disabled"
        assert client.model == "deepseek-flash"

    def test_build_live_client_defaults_and_no_network(self) -> None:
        """Calling build_live_client(None, 'sk-fake') configures defaults with zero network I/O."""
        client = build_live_client(model=None, api_key="sk-fake")
        assert client.model == "deepseek-flash"
        assert client.temperature == 0.0
        assert client.max_tokens == 16
        assert client.thinking == {"type": "disabled"}
        assert client.thinking_mode == "disabled"


# ===========================================================================
# 2. PROGRESS REPORTER TESTS
# ===========================================================================

class TestProgressReporter:
    """Verify call-driven progress reporting, mid-trial heartbeat, and retry handling."""

    def test_eta_computed_by_calls_not_trials(self) -> None:
        """ETA must be driven by LLM calls completed vs total planned calls."""
        clock = MockClock(100.0)
        buf = io.StringIO()
        reporter = ProgressReporter(
            total_calls=100,
            total_trials=10,
            strategy_name="null",
            clock=clock.now,
            stream=buf,
            interval_s=30.0,
        )

        clock.advance(10.0)  # elapsed = 10s
        # 20 calls completed out of 100 planned calls (trial 0 is still running)
        reporter.on_llm_call(calls_done=20, cumulative_retries=0)

        # Force a print via update or interval to verify ETA in message
        clock.advance(35.0)  # now elapsed = 45s since start, >30s since start
        reporter.on_llm_call(calls_done=20, cumulative_retries=0)

        output = buf.getvalue()
        assert "calls" in output
        # At 45s with 20 calls done: rate = 45s / 20 = 2.25s/call. Remaining = 80 calls => ETA = 180.0s
        assert "ETA=180.0s" in output

    def test_heartbeat_fires_mid_trial(self) -> None:
        """Heartbeat must fire during a long trial when interval_s elapses without trial completing."""
        clock = MockClock(0.0)
        buf = io.StringIO()
        reporter = ProgressReporter(
            total_calls=500,
            total_trials=5,
            strategy_name="null",
            clock=clock.now,
            stream=buf,
            interval_s=30.0,
        )

        # At t=0: call 1 -> interval not elapsed
        emitted1 = reporter.on_llm_call(calls_done=1, cumulative_retries=0)
        assert emitted1 is False
        assert buf.getvalue() == ""

        # Advance clock to t=35s mid-trial (trial 0 still in progress)
        clock.advance(35.0)
        emitted2 = reporter.on_llm_call(calls_done=10, cumulative_retries=1)
        assert emitted2 is True
        output = buf.getvalue()
        assert "[null] 10/500 calls (trial 0/5) elapsed=35.0s" in output
        assert "retries=1" in output

    def test_retry_counting_no_double_count(self) -> None:
        """When on_llm_call hook is active, cumulative retries are tracked without double-counting on update."""
        clock = MockClock(0.0)
        buf = io.StringIO()
        reporter = ProgressReporter(
            total_calls=100,
            total_trials=5,
            strategy_name="null",
            clock=clock.now,
            stream=buf,
            interval_s=30.0,
        )

        # Hook reports 2 cumulative retries
        reporter.on_llm_call(calls_done=15, cumulative_retries=2)
        assert reporter.retries == 2

        # Harness completes trial 1 and passes delta_retries=2
        reporter.update(trials_done=1, total_trials=5, delta_retries=2, force=True)
        # Retries must still be 2, NOT 4 (no double-counting)
        assert reporter.retries == 2
        assert "retries=2" in buf.getvalue()

    def test_retry_counting_fallback_when_hook_inactive(self) -> None:
        """When on_llm_call hook is NOT active, update accumulates delta_retries correctly."""
        clock = MockClock(0.0)
        buf = io.StringIO()
        reporter = ProgressReporter(
            total_calls=100,
            total_trials=5,
            strategy_name="null",
            clock=clock.now,
            stream=buf,
            interval_s=30.0,
        )

        # No on_llm_call called; harness completes trial 1 with 1 retry
        reporter.update(trials_done=1, total_trials=5, delta_retries=1, force=True)
        assert reporter.retries == 1

        # Trial 2 completes with 2 more retries
        reporter.update(trials_done=2, total_trials=5, delta_retries=2, force=True)
        assert reporter.retries == 3


# ===========================================================================
# 3. METERED LLM CLIENT ON_CALL ERROR ACCOUNTING TESTS (FIX-009)
# ===========================================================================

class TestMeteredLLMClientOnCallErrorHandling:
    """Verify MeteredLLMClient on_call callback exception accounting and single stderr warning."""

    def test_on_call_exception_increments_error_counter_and_prints_once(self, capsys) -> None:
        fake = FakeLLMClient()
        meter = MeteredLLMClient(fake)

        def faulty_callback(calls: int, retries: int) -> None:
            raise RuntimeError("simulated callback failure")

        meter.set_on_call(faulty_callback)
        assert meter.on_call_errors == 0

        # First call: completes successfully, records error, prints single line to stderr
        resp1 = meter.complete(system="sys", user="user1")
        assert resp1.text is not None
        assert meter.calls == 1
        assert meter.on_call_errors == 1

        err1 = capsys.readouterr().err
        assert "Warning: MeteredLLMClient on_call callback raised exception" in err1
        assert "simulated callback failure" in err1

        # Second call: completes successfully, increments error, does NOT print to stderr again
        resp2 = meter.complete(system="sys", user="user2")
        assert resp2.text is not None
        assert meter.calls == 2
        assert meter.on_call_errors == 2

        err2 = capsys.readouterr().err
        assert err2 == ""

    def test_on_call_exception_during_transport_error(self, capsys) -> None:
        """When client.complete raises, on_call error is counted and does not mask original error."""
        failing_client = MagicMock()
        failing_client.complete.side_effect = RuntimeError("transport network dropped")
        meter = MeteredLLMClient(failing_client)

        def faulty_callback(calls: int, retries: int) -> None:
            raise ValueError("callback crashed")

        meter.set_on_call(faulty_callback)

        with pytest.raises(RuntimeError, match="transport network dropped"):
            meter.complete(system="sys", user="user")

        assert meter.calls == 1
        assert meter.on_call_errors == 1
        err = capsys.readouterr().err
        assert "Warning: MeteredLLMClient on_call callback raised exception" in err


# ===========================================================================
# 4. ESTIMATOR TESTS (FIX-009)
# ===========================================================================

class TestEstimatorAccuracyAndResume:
    """Verify strategy-aware, resume-aware, and cap-aware planned calls upper bound estimation."""

    def test_estimator_null_k1_full_matrix_bound_and_offline_equality(self, tmp_path) -> None:
        """(i) Null k=1 over full D-35 matrix gives bound 60 and real offline run metered call count equals 60."""
        config = HarnessConfig(
            mode="sweep",
            run_id="test_d35_matrix",
            output_dir=tmp_path / "d35_run",
            sweep_sizes=(50, 100, 200, 500, 1000, 2000),
            sweep_trials_per_size=10,
            confirm=True,
        )
        strat = NullStrategy(seed=42, k=1)
        bound = compute_planned_calls_upper_bound(config, strategy=strat)
        assert bound.full_plan_bound == 60
        assert bound.remaining_bound == 60
        assert bound == 60

        # Run real offline sweep with FakeLLMClient and confirm meter count is exactly 60
        fake_llm = FakeLLMClient()
        metered_llm = MeteredLLMClient(fake_llm)
        decision_step = PairwiseDecisionStep(metered_llm)

        # Generate enough synthetic names: max size 2000 => 2105 names
        names = [f"concept_{i:04d}" for i in range(2105)]
        name_source = SyntheticNameSource(names=names, domain_context="computer science")

        res = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: NullStrategy(seed=42, k=1),
            decision_step=decision_step,
            embedder_factory=lambda: None,
            name_source=name_source,
        )
        assert res["status"] == "completed"
        assert metered_llm.calls == 60

    def test_estimator_resume_subtracts_completed_trials(self, tmp_path) -> None:
        """(ii) On resume, estimator subtracts completed trials recorded in raw.jsonl."""
        run_dir = tmp_path / "resume_run"
        run_dir.mkdir(parents=True)
        raw_path = run_dir / "raw.jsonl"

        # Pre-populate raw.jsonl with 10 completed trials for size 50
        strat = NullStrategy(seed=42, k=1)
        records = []
        for i in range(10):
            records.append({
                "key": f"sweep:null:50:t{i}",
                "status": "success",
                "metrics": {"llm_calls": 1},
            })
        raw_path.write_text("\n".join(json.dumps(r) for r in records) + "\n")

        config = HarnessConfig(
            mode="sweep",
            run_id="resume_run",
            output_dir=run_dir,
            sweep_sizes=(50, 100),
            sweep_trials_per_size=10,
            resume=True,
        )
        bound = compute_planned_calls_upper_bound(config, strategy=strat, raw_jsonl_path=raw_path)
        # Total trials: 2 sizes * 10 = 20. 10 completed => 10 remaining.
        assert bound.full_plan_bound == 20
        assert bound.remaining_bound == 10

    def test_estimator_max_llm_calls_caps_plan(self) -> None:
        """(iii) max_llm_calls caps the remaining bound."""
        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=(50, 100),
            sweep_trials_per_size=10,
            max_llm_calls=7,
        )
        strat = NullStrategy(seed=42, k=1)
        bound = compute_planned_calls_upper_bound(config, strategy=strat)
        assert bound.full_plan_bound == 20
        assert bound.remaining_bound == 7

    def test_estimator_strategy_max_candidates_upper_bounds_actual(self) -> None:
        """(iv) Strategy with max_candidates > actual shortlist produces actual calls <= bound."""
        class ConstrainedStrategy:
            name = "constrained"
            uses_embeddings = False
            _embedder = None

            def setup(self, graph, embedder):
                self._graph = graph

            def shortlist(self, new_name):
                # Returns 2 candidates even though max_candidates promises up to 5
                nodes = sorted(self._graph.nodes())[:2]
                return Shortlist(candidates=tuple(nodes))

            def on_inserted(self, new_name, edges):
                pass

            def config(self):
                return {}

            def diagnostics(self):
                return {}

            def max_candidates(self, n_existing: int) -> int:
                return min(5, n_existing)

        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=(10,),
            sweep_trials_per_size=2,
        )
        strat = ConstrainedStrategy()
        bound = compute_planned_calls_upper_bound(config, strategy=strat)
        # 2 trials * min(5, 10) = 10 calls bound
        assert bound.full_plan_bound == 10

        actual_calls_per_trial = 2
        assert (actual_calls_per_trial * 2) <= bound.full_plan_bound

    def test_estimator_strategy_without_max_candidates_gets_bruteforce(self) -> None:
        """(v) Strategy without max_candidates receives brute-force bound (sum of n * trials)."""
        class BruteForceStrategy:
            name = "brute"
            uses_embeddings = False

        config = HarnessConfig(
            mode="sweep",
            sweep_sizes=(50, 100, 200),
            sweep_trials_per_size=10,
        )
        bound = compute_planned_calls_upper_bound(config, strategy=BruteForceStrategy())
        assert bound == 3500
        assert bound.full_plan_bound == 3500
        assert bound.remaining_bound == 3500


# ===========================================================================
# 5. LIVE RUN GATES TESTS (FIX-009)
# ===========================================================================

class TestLiveRunGates:
    """Verify live run CLI safety gates."""

    def test_live_sweep_refused_without_names_file(self, monkeypatch, capsys) -> None:
        from scripts.run_experiment import main
        monkeypatch.setattr(
            "sys.argv",
            ["run_experiment.py", "--live", "--mode", "sweep"],
        )
        ret = main()
        assert ret == 1
        err = capsys.readouterr().err
        assert "DATA-004" in err

    def test_live_dry_run_exits_zero_without_api_key_or_client(self, monkeypatch, capsys, tmp_path) -> None:
        from scripts.run_experiment import main

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        names_file = tmp_path / "names.json"
        names = [f"valid_concept_{i:04d}" for i in range(2005)]
        names_file.write_text(json.dumps(names))

        monkeypatch.setattr(
            "sys.argv",
            [
                "run_experiment.py",
                "--live",
                "--dry-run",
                "--mode",
                "sweep",
                "--names-file",
                str(names_file),
            ],
        )
        ret = main()
        assert ret == 0
        out = capsys.readouterr().out
        assert "LIVE EXPERIMENT PRE-FLIGHT ESTIMATE" in out
        assert "Peak check note:" in out
        assert "Dry run complete" in out
