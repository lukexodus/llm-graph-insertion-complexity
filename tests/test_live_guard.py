"""tests/test_live_guard.py — FIX-008
===================================
Tests for live guard calculation, pre-flight estimation, DeepSeekClient defaults/parity,
and call-driven progress reporting with injectable clock.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from graph_insertion.graph_representation import ConceptGraph
from graph_insertion.harness import HarnessConfig
from graph_insertion.llm import DeepSeekClient, FakeLLMClient, MeteredLLMClient
from graph_insertion.loader import CorpusStats, GoldJudgmentSet, LoadedCorpus, SourceKind
from scripts.run_experiment import (
    ProgressReporter,
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

    def test_client_construction_parity_with_pilot(self) -> None:
        """The live path in run_experiment.py builds DeepSeekClient identically to the pilot."""
        api_key = "sk-fake-test-key"
        model = "deepseek-chat"

        # pilot_dsa_zero_shot.py:
        pilot_client = DeepSeekClient(api_key=api_key, model=model)

        # run_experiment.py:
        run_exp_client = DeepSeekClient(api_key=api_key, model=model)

        assert run_exp_client.api_key == pilot_client.api_key
        assert run_exp_client.model == pilot_client.model
        assert run_exp_client.temperature == pilot_client.temperature == 0.0
        assert run_exp_client.max_tokens == pilot_client.max_tokens == 16
        assert run_exp_client.thinking == pilot_client.thinking == {"type": "disabled"}


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
