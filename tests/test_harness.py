"""
test_harness.py — INFRA-004 Unit Tests
======================================
Tests for measurement harness:
  - Seeded determinism
  - Held-out isolation (strategy never sees h or its incident edges)
  - Same meter object used in setup and insert ([D-28])
  - Resume skips completed keys, retry-failed re-runs failures
  - Failure rows recorded and execution continues unless fail-fast
  - Max LLM calls cap halts cleanly
  - Manifest secret sanitization
  - Summary CSV aggregation
  - Dry run makes no insertions
  - Live run requires --confirm
  - Cost sweep runner execution
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable, Optional
import pytest

from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
from graph_insertion.graph_representation import (
    ConceptGraph,
    GoldJudgmentSet,
    SourceKind,
)
from graph_insertion.llm import LLMTransportError
from graph_insertion.harness import (
    HarnessConfig,
    SyntheticNameSource,
    load_existing_results,
    run_accuracy_experiment,
    run_experiment,
    run_sweep_experiment,
    sanitize_metadata,
)
from graph_insertion.loader import CorpusSpec, LoadedCorpus
from graph_insertion.strategy import (
    DecisionOutcome,
    DecisionStep,
    NarrowingStrategy,
    Shortlist,
)


# ===========================================================================
# Test Fixtures & Fakes
# ===========================================================================

class SpyStrategy:
    """Spy strategy capturing graph topology seen during setup and embedder instance."""

    def __init__(self, top_k: int = 2) -> None:
        self.name = "spy_strategy"
        self.top_k = top_k
        self._graph: Optional[ConceptGraph] = None
        self._embedder: Optional[Embedder] = None
        self.seen_nodes: set[str] = set()
        self.seen_edges: set[tuple[str, str]] = set()
        self.setup_embedder_id: Optional[int] = None

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder
        self.setup_embedder_id = id(embedder)
        self.seen_nodes = set(graph.nodes())
        self.seen_edges = set(graph.edges())

    def shortlist(self, new_name: str) -> Shortlist:
        if not self._graph:
            return Shortlist(candidates=())
        nodes = sorted(self._graph.nodes())
        cands = tuple(nodes[: self.top_k])
        return Shortlist(candidates=cands)

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        pass

    def config(self) -> dict[str, Any]:
        return {"name": self.name, "top_k": self.top_k}

    def diagnostics(self) -> dict[str, Any]:
        return {}


class DeterministicDecisionStep:
    """Decision step returning canonical edges for testing."""

    def __init__(self, edges_to_predict: Sequence[tuple[str, str]] = ()) -> None:
        self.edges_to_predict = tuple(edges_to_predict)
        self.PROMPT_VERSION = "v1"

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        matched = tuple(
            e for e in self.edges_to_predict
            if (e[0] == new_name and e[1] in candidates) or (e[1] == new_name and e[0] in candidates)
        )
        return DecisionOutcome(
            edges=matched,
            llm_calls=len(candidates),
            llm_seconds=0.001 * len(candidates),
        )


class FlakyDecisionStep:
    """Decision step that fails when evaluating a specific node."""

    def __init__(self, failing_node: str) -> None:
        self.failing_node = failing_node
        self.PROMPT_VERSION = "v1"

    def decide(
        self,
        new_name: str,
        candidates: tuple[str, ...],
        domain_context: Optional[str] = None,
    ) -> DecisionOutcome:
        if new_name == self.failing_node:
            raise LLMTransportError(f"Simulated network transport error on {new_name}")
        return DecisionOutcome(
            edges=(),
            llm_calls=len(candidates),
            llm_seconds=0.001 * len(candidates),
        )


@pytest.fixture
def mini_corpus() -> LoadedCorpus:
    """Create a minimal 4-node loaded corpus for harness tests."""
    graph = ConceptGraph(domain_context="testing")
    for n in ("a", "b", "c", "d"):
        graph.add_node(n)
    # Directed prereq edges: a -> b, b -> c, c -> d
    graph.add_prereq_edge("a", "b")
    graph.add_prereq_edge("b", "c")
    graph.add_prereq_edge("c", "d")

    judgments = GoldJudgmentSet(source_kind=SourceKind.GOLD)
    # a -> b
    judgments.record("b", "a", 1)
    judgments.record("a", "b", 0)
    # b -> c
    judgments.record("c", "b", 1)
    judgments.record("b", "c", 0)
    # c -> d
    judgments.record("d", "c", 1)
    judgments.record("c", "d", 0)
    # Non-edges
    for u in ("a", "b", "c", "d"):
        for v in ("a", "b", "c", "d"):
            if u != v and (u, v) not in (("b", "a"), ("c", "b"), ("d", "c")):
                judgments.record(u, v, 0)

    return LoadedCorpus(
        name="mini_corpus",
        source_kind=SourceKind.GOLD,
        graph=graph,
        judgments=judgments,
        domain_context="testing",
        stats=None,
    )


# ===========================================================================
# Test Cases
# ===========================================================================

class TestHarnessGuardsAndSafety:
    """Verify safety guardrails: confirm requirement, dry-run, max-llm-calls."""

    def test_live_run_requires_confirm(self, tmp_path, mini_corpus):
        config = HarnessConfig(
            mode="accuracy",
            output_dir=tmp_path / "run",
            dry_run=False,
            confirm=False,
        )
        with pytest.raises(RuntimeError, match="Live experiment runs require explicit confirmation"):
            run_accuracy_experiment(
                config=config,
                strategy_factory=lambda: SpyStrategy(),
                decision_step=DeterministicDecisionStep(),
                embedder_factory=lambda: FakeEmbedder(dim=8),
                corpora={"mini_corpus": mini_corpus},
            )

    def test_dry_run_makes_no_insertions(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "dry_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            dry_run=True,
            confirm=False,
        )

        created_strategies = []

        def factory():
            strat = SpyStrategy()
            created_strategies.append(strat)
            return strat

        plan = run_accuracy_experiment(
            config=config,
            strategy_factory=factory,
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        assert plan["mode"] == "accuracy"
        assert plan["total_insertions"] == 4  # 4 nodes in mini_corpus
        assert (run_dir / "manifest.json").exists()
        assert not (run_dir / "raw.jsonl").exists()
        assert not (run_dir / "summary.csv").exists()

        # Probe strategy was instantiated for config reflection, but setup() was never invoked
        for s in created_strategies:
            assert s._graph is None

    def test_max_llm_calls_halts_cleanly(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "max_calls_run"
        # Each trial on mini_corpus asks for top_k=2 candidates -> 2 LLM calls per trial
        # With max_llm_calls=3, trial 1 uses 2 calls; trial 2 uses 2 calls (cumulative 4 >= 3), halts cleanly
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            max_llm_calls=3,
        )
        res = run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(top_k=2),
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        assert res["status"] == "max_llm_calls_reached"
        assert res["cumulative_llm_calls"] >= 3

        # Check raw.jsonl and summary.csv were saved
        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) >= 1
        assert (run_dir / "summary.csv").exists()


class TestHarnessTrialIsolationAndAccounting:
    """Verify trial isolation, held-out integrity, and embedder meter sharing."""

    def test_held_out_isolation(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "isolation_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
        )

        spies: list[SpyStrategy] = []

        def factory():
            s = SpyStrategy()
            spies.append(s)
            return s

        run_accuracy_experiment(
            config=config,
            strategy_factory=factory,
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        # We had probe strat + 4 node trials = 5 spy strategies
        trials_spies = [s for s in spies if s._graph is not None]
        assert len(trials_spies) == 4

        # For each trial, verify held-out node h was NOT in seen_nodes or seen_edges
        nodes_order = sorted(mini_corpus.graph.nodes())
        for h, spy in zip(nodes_order, trials_spies):
            assert h not in spy.seen_nodes
            for u, v in spy.seen_edges:
                assert u != h and v != h

    def test_same_meter_object_used_in_setup_and_insert(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "meter_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
        )

        spies: list[SpyStrategy] = []

        def factory():
            s = SpyStrategy()
            spies.append(s)
            return s

        run_accuracy_experiment(
            config=config,
            strategy_factory=factory,
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        # If strategy._embedder != metered_embedder passed to insert_node,
        # [D-28] would have raised ValueError. Since all succeeded, meter identity held.
        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) == 4
        for r in raw_lines:
            assert r["status"] == "success"
            assert "unaccounted_s" in r
            assert r["harness_wall_s"] >= r["metrics"]["total_s"]


class TestHarnessResumeAndFailureHandling:
    """Verify resume skipping, retry-failed, and failure record logging."""

    def test_failure_row_recorded_and_continues_unless_fail_fast(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "flaky_run"
        # Fail on node 'b'
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            fail_fast=False,
        )

        run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=FlakyDecisionStep(failing_node="b"),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) == 4

        b_records = [r for r in raw_lines if r["node"] == "b"]
        assert len(b_records) == 1
        assert b_records[0]["status"] == "failed"
        assert b_records[0]["error_type"] == "LLMTransportError"

        other_records = [r for r in raw_lines if r["node"] != "b"]
        assert len(other_records) == 3
        for r in other_records:
            assert r["status"] == "success"

    def test_fail_fast_aborts_immediately(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "fail_fast_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            fail_fast=True,
        )

        with pytest.raises(LLMTransportError, match="Simulated network transport error on b"):
            run_accuracy_experiment(
                config=config,
                strategy_factory=lambda: SpyStrategy(),
                decision_step=FlakyDecisionStep(failing_node="b"),
                embedder_factory=lambda: FakeEmbedder(dim=8),
                corpora={"mini_corpus": mini_corpus},
            )

    def test_resume_skips_completed_keys_and_retry_failed(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "resume_run"
        config1 = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            fail_fast=False,
        )

        # Run 1: b fails, a, c, d succeed
        run_accuracy_experiment(
            config=config1,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=FlakyDecisionStep(failing_node="b"),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        recs1 = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(recs1) == 4

        # Run 2: resume=True, retry_failed=False, now with fixed decision step
        config2 = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            resume=True,
            retry_failed=False,
        )
        run_accuracy_experiment(
            config=config2,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        # No new records added because a,c,d succeeded and b is failed (retry_failed=False)
        recs2 = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(recs2) == 4

        # Run 3: resume=True, retry_failed=True -> b should be re-executed and succeed
        config3 = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            resume=True,
            retry_failed=True,
        )
        run_accuracy_experiment(
            config=config3,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        recs3 = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(recs3) == 5  # Initial 4 + re-executed b record
        assert recs3[-1]["node"] == "b"
        assert recs3[-1]["status"] == "success"


class TestManifestSanitizationAndSummaryAggregation:
    """Verify secret sanitization and summary.csv generation."""

    def test_manifest_secret_sanitization(self, tmp_path):
        dirty_dict = {
            "normal_key": "safe_value",
            "api_key": "sk-real_secret_token_12345",
            "deepseek_auth": "Bearer abcd1234efgh",
            "nested": {
                "user_password": "super_secret_password",
                "count": 42,
            },
            "list_values": ["safe", "sk-another_secret_key"],
        }
        clean = sanitize_metadata(dirty_dict)
        assert clean["normal_key"] == "safe_value"
        assert clean["api_key"] == "[REDACTED]"
        assert clean["deepseek_auth"] == "[REDACTED]"
        assert clean["nested"]["user_password"] == "[REDACTED]"
        assert clean["nested"]["count"] == 42
        assert clean["list_values"] == ["safe", "[REDACTED]"]

    def test_summary_aggregation(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "summary_test_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
        )
        # Gold edges: a -> b, b -> c, c -> d
        # Provide correct decisions for all
        gold_edges = (("a", "b"), ("b", "c"), ("c", "d"))
        run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(top_k=3),
            decision_step=DeterministicDecisionStep(edges_to_predict=gold_edges),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        csv_path = run_dir / "summary.csv"
        assert csv_path.exists()

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) == 1
        row = reader[0]
        assert row["strategy"] == "spy_strategy"
        assert row["corpus_or_size"] == "mini_corpus"
        assert int(row["num_trials"]) == 4
        assert int(row["num_success"]) == 4
        assert int(row["num_failed"]) == 0

        # Timing columns present and non-negative
        for tk in ("total_s", "shortlist_s", "decide_s", "apply_s", "update_s", "validate_s", "unaccounted_s"):
            assert float(row[f"{tk}_mean"]) >= 0.0
            assert float(row[f"{tk}_min"]) >= 0.0

        # Accuracy micro/macro metrics
        assert float(row["precision_micro"]) == 1.0
        assert float(row["recall_micro"]) == 1.0
        assert float(row["f1_micro"]) == 1.0
        assert float(row["precision_macro"]) == 1.0
        assert float(row["recall_macro"]) == 1.0
        assert float(row["f1_macro"]) == 1.0


class TestSweepRunner:
    """Verify cost sweep runner scaling and synthetic name generation."""

    def test_sweep_runner_execution_and_summary(self, tmp_path):
        run_dir = tmp_path / "sweep_run"
        config = HarnessConfig(
            mode="sweep",
            output_dir=run_dir,
            confirm=True,
            sweep_sizes=(5, 10),
            sweep_trials_per_size=3,
        )
        names = [f"concept_{i:03d}" for i in range(25)]
        source = SyntheticNameSource(names=names, domain_context="test_domain")

        res = run_sweep_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(top_k=2),
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            name_source=source,
        )

        assert res["status"] == "completed"
        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) == 6  # 2 sizes * 3 trials = 6

        # Check summary.csv has 2 rows (one for size 5, one for size 10)
        with open(run_dir / "summary.csv", "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) == 2
        sizes_in_csv = {int(r["corpus_or_size"]) for r in reader}
        assert sizes_in_csv == {5, 10}
        for r in reader:
            assert int(r["num_trials"]) == 3
            assert int(r["num_success"]) == 3
            assert float(r["total_s_mean"]) >= 0.0


class TestHarnessHardeningAndEnrichment:
    """Verify FIX-004 hardening policies: driver contract aborts, setup aborts, manifest enrichment."""

    def test_driver_contract_error_aborts_immediately_and_writes_failure_row(self, tmp_path, mini_corpus):
        class BadShortlistStrategy(SpyStrategy):
            def shortlist(self, new_name: str) -> Shortlist:
                # Return non-existent candidate to trigger ValueError in insert_node
                return Shortlist(candidates=("non_existent_node",))

        run_dir = tmp_path / "driver_error_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            fail_fast=False,  # Even with fail_fast=False, driver contract error must abort immediately
        )

        with pytest.raises(ValueError, match="not an existing graph node"):
            run_accuracy_experiment(
                config=config,
                strategy_factory=lambda: BadShortlistStrategy(),
                decision_step=DeterministicDecisionStep(),
                embedder_factory=lambda: FakeEmbedder(dim=8),
                corpora={"mini_corpus": mini_corpus},
            )

        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) == 1
        assert raw_lines[0]["status"] == "failed"
        assert raw_lines[0]["error_type"] == "ValueError"

    def test_setup_error_aborts_immediately_and_writes_failure_row(self, tmp_path, mini_corpus):
        class FailingSetupStrategy(SpyStrategy):
            def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
                raise RuntimeError("Setup failed explicitly")

        run_dir = tmp_path / "setup_error_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
            fail_fast=False,
        )

        with pytest.raises(RuntimeError, match="Setup failed explicitly"):
            run_accuracy_experiment(
                config=config,
                strategy_factory=lambda: FailingSetupStrategy(),
                decision_step=DeterministicDecisionStep(),
                embedder_factory=lambda: FakeEmbedder(dim=8),
                corpora={"mini_corpus": mini_corpus},
            )

        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        assert len(raw_lines) == 1
        assert raw_lines[0]["status"] == "failed"
        assert raw_lines[0]["error_type"] == "RuntimeError"

    def test_manifest_model_and_tokens_not_redacted(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "manifest_test_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            dry_run=True,
        )

        class DummyStep:
            PROMPT_VERSION = "v1"
            class InnerClient:
                model = "deepseek-v4-flash"
                base_url = "https://api.deepseek.com"
            llm_client = InnerClient()

        run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=DummyStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["configured_model"] == "deepseek-v4-flash"
        assert manifest["base_url"] == "https://api.deepseek.com"
        assert manifest["temperature"] == 0.0
        assert manifest["thinking_mode"] == "disabled"
        assert manifest["max_tokens"] == 16  # NOT redacted!
        assert manifest["prompt_version"] == "v1"

    def test_trial_key_has_strategy_name_and_summary_deduplicates(self, tmp_path, mini_corpus):
        run_dir = tmp_path / "dedupe_run"
        config = HarnessConfig(
            mode="accuracy",
            output_dir=run_dir,
            confirm=True,
        )

        run_accuracy_experiment(
            config=config,
            strategy_factory=lambda: SpyStrategy(),
            decision_step=DeterministicDecisionStep(),
            embedder_factory=lambda: FakeEmbedder(dim=8),
            corpora={"mini_corpus": mini_corpus},
        )

        raw_lines = [json.loads(line) for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
        for r in raw_lines:
            assert r["key"].startswith("accuracy:spy_strategy:mini_corpus:")

        # Append duplicate line with higher total_s
        dup_rec = dict(raw_lines[0])
        dup_rec["metrics"] = dict(dup_rec["metrics"])
        dup_rec["metrics"]["total_s"] = 999.0
        with open(run_dir / "raw.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(dup_rec) + "\n")

        from graph_insertion.harness import generate_summary_csv
        summary_csv = run_dir / "summary.csv"
        generate_summary_csv(run_dir / "raw.jsonl", summary_csv, mode="accuracy")

        with open(summary_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        # Number of trials is still 4 because the duplicate was deduped (last record wins)
        assert int(rows[0]["num_trials"]) == 4

