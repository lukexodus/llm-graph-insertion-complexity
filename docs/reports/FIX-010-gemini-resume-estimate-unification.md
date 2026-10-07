# FIX-010: Resume Estimation Unification & Pre-Live Hardening Closure

**Task ID:** FIX-010  
**Agent:** Gemini  
**Date:** 2026-10-07  
**Status:** Complete (needs-review)  
**Pre-assigned Decision ID:** `[D-42]`  

---

## 1. Executive Summary

Task FIX-010 completes the hardening of `scripts/run_experiment.py` and `src/graph_insertion/harness.py`, eliminating code duplication and potential drift between the pre-flight worst-case call estimator (`compute_planned_calls_upper_bound`) and the execution harness runners (`run_sweep_experiment` and `run_accuracy_experiment`).

Key outcomes:
1. **Single Source of Truth for Trial Keys and Held-Out Sampling:** Extracted shared helpers `sweep_trial_key`, `accuracy_trial_key`, and `sample_heldout_nodes` in `src/graph_insertion/harness.py`. Replaced duplicated logic across both runners and `compute_planned_calls_upper_bound`.
2. **Unified Resume Record Filtering:** Unified resume filtering so both the runners and the estimator utilize `_load_existing_keys(raw_jsonl_path, retry_failed=config.retry_failed)`. Records with `status == "success"` are skipped; records with `status in ("failed", "error")` are skipped unless `--retry-failed` is requested.
3. **Aligned Trial and Call Accounting:** `PlannedCallsBound` now tracks both `remaining_trials` and `full_plan_trials`. In `scripts/run_experiment.py:main()`, `total_planned_trials` is set to `planned_calls_bound.remaining_trials`, matching `total_calls` passed to `ProgressReporter`.
4. **Hardened and Realistic Tests:** Replaced synthetic JSONL tests with real interrupted harness executions through `run_sweep_experiment` and `run_accuracy_experiment` using `FakeLLMClient` with `max_llm_calls`, verifying that resuming actually subtracts completed trials in both harness execution and estimator bound calculation. Replaced candidate upper bound assertions with a metered sweep test executing a custom `ConstrainedStrategy`. Added dedicated unit tests for clamping (`max_candidates > n_existing`), negative bounds (`< 0`), exception fallback, and absent method fallback.
5. **CLI and Telemetry Polish:** Missing `DEEPSEEK_API_KEY` on non-dry-run `--live` runs produces a clean single-line error on `sys.stderr` and exits with code 1 (no Python traceback). Centralized model alias resolution in `src/graph_insertion/llm.py:resolve_model_alias` (`model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`) and surfaced `"Model alias: <resolved>"` in pre-flight output.
6. **Errata Closure:** Documented and verified four specific discrepancies and errata from the FIX-009 report.

The test suite now collects **275 tests**, with **273 passing and 2 skipped** (100% pass rate among runnable tests).

---

## 2. Prompt Verification and Analysis

| Item / Claim in Prompt | Verification Result | Details |
| :--- | :--- | :--- |
| **Harness trial key parity** | **Confirmed** | FIX-009's key formats (`f"{strat_name}:{n}:{trial_idx}"` and `f"{strat_name}:{corpus}:{node}:{rep}"`) matched `harness.py` lines 739 and 969. Centralized in shared helpers `sweep_trial_key` and `accuracy_trial_key`. |
| **Harness failure statuses** | **Confirmed** | Grep of `harness.py` confirmed `"failed"` is the only failure string written to `raw.jsonl` (lines 773, 855, 883, 1009, 1081, 1108). `_load_existing_keys` filters on `status == "success"` and `status in ("failed", "error") and not retry_failed`. |
| **`strategy_name` derivation parity** | **Confirmed & Unified** | In both runners, `strategy_name` is taken from `probe_strat.name` (where `probe_strat = strategy_factory()`). In `compute_planned_calls_upper_bound`, it is evaluated via `getattr(strategy, "name", "unknown")`. Both evaluate to `"null"` for `NullStrategy`. For `StubNarrowingStrategy`, its `.name` attribute is `"stub_narrowing"` while its registry key is `"stub"`; both evaluate to `"stub_narrowing"`. In `run_experiment.py`, `ProgressReporter` was updated to use `getattr(uninitialized_strategy, "name", args.strategy)` for total consistency. |
| **Metacademy held-out sampling parity** | **Confirmed & Unified** | Both the harness accuracy runner and the estimator used identical logic (`sorted(graph.nodes)` with seed `config.seed`), but duplicated the sampling code. Centralized into `sample_heldout_nodes`. |
| **Total planned trials vs calls** | **Confirmed & Fixed** | FIX-009 computed `total_planned_trials` over the full configuration (e.g. 60 trials), but `total_calls` was remaining calls (e.g. 30). Updated `main()` so `total_planned_trials` matches remaining trials (`planned_calls_bound.remaining_trials`). |
| **Missing API key exit behavior** | **Confirmed & Fixed** | Previously crashed with an unhandled `ValueError` traceback from `build_live_client`. Now caught in `main()`, printing `ERROR: <msg>` to `sys.stderr` and exiting code 1. |
| **Model alias resolution** | **Confirmed & Added** | Created `resolve_model_alias(model)` in `llm.py` with precedence `model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`. Surfaced in pre-flight telemetry. |

---

## 3. Errata for FIX-009 Report

Task FIX-010 conducted an audit of `docs/reports/FIX-009-claude-code-prelive-hardening.md` against git history (`git show --stat HEAD~0`):

1. **Diff Fabrication & Mismatched Index Hashes:**
   In Section 6 of the FIX-009 report, a unified diff was presented for `docs/context/strategy-interface.md` claiming to add `def max_candidates(self, n_existing: int) -> int:` with git index hashes `102c30c..df5258e`. However, `docs/context/strategy-interface.md` was never modified in the FIX-009 commit or git history, and the index hashes were fabricated. Similarly, the index hashes shown for `docs/decisions/decision-log.md` (`2cae2c2..2b325ee`) and `docs/tasks/status.md` (`8bdf1f5..42cb7fb`) did not match git reality.
2. **Paraphrased Prompt Quotes:**
   In Section 2 of the FIX-009 report, several entries under "Prompt Statement" did not quote the prompt verbatim, but instead presented paraphrased summaries or editorial commentary as direct quotes.
3. **Test Name and Coverage Divergence:**
   In Section 3 Part C of the FIX-009 report, test names listed did not match the code in `tests/test_live_guard.py` (e.g., reported `test_estimator_with_resume_subtracts_completed_trials` vs code `test_estimator_resume_subtracts_completed_trials`). Furthermore, the clamping test `test_estimator_with_max_candidates_greater_than_actual_nodes` reported in Section 3 Part C was omitted from `tests/test_live_guard.py` in that commit.
4. **Strategy Factory Signature Misstatement:**
   In Section 1 of the FIX-009 report, the strategy factory in `run_experiment.py` was described as accepting `(dummy_graph, embedder)`, whereas in `run_experiment.py` it was a zero-argument callable `lambda: strat_factory_fn(config.seed, args.k)`.

---

## 4. Implementation Details

### A. Shared Harness Helpers (`src/graph_insertion/harness.py`)
- Added `sweep_trial_key(strategy_name: str, n: int, trial_idx: int) -> str`: produces `f"{strategy_name}:{n}:{trial_idx}"`.
- Added `accuracy_trial_key(strategy_name: str, corpus_name: str, node: str, rep: int) -> str`: produces `f"{strategy_name}:{corpus_name}:{node}:{rep}"`.
- Added `sample_heldout_nodes(graph: ConceptGraph, corpus_name: str, seed: int, metacademy_sample_size: int = 30) -> list[str]`: deterministic sampling for accuracy held-out evaluation.
- Updated `_load_existing_keys(raw_jsonl_path: Path, retry_failed: bool = False) -> set[str]`:
  ```python
  status = record.get("status")
  if status == "success":
      keys.add(key)
  elif status in ("failed", "error") and not retry_failed:
      keys.add(key)
  ```
- Replaced key generation, skip checks, and sampling in `run_sweep_experiment` and `run_accuracy_experiment` with these helpers.
- Updated runner `total_trials` calculation to reflect remaining trials: `sum(1 for k in all_planned_keys if k not in skipped_keys)`.

### B. LLM Model Alias Resolution (`src/graph_insertion/llm.py`)
- Implemented `resolve_model_alias(model: Optional[str] = None) -> str`:
  ```python
  def resolve_model_alias(model: Optional[str] = None) -> str:
      return model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"
  ```
- Refactored `DeepSeekClient.__init__` to delegate directly to `resolve_model_alias(model)`.

### C. Guard and Live Run Polish (`scripts/run_experiment.py`)
- Updated `PlannedCallsBound` dataclass to include `remaining_trials: int` and `full_plan_trials: int`.
- Updated `compute_planned_calls_upper_bound`:
  - Uses `sweep_trial_key`, `accuracy_trial_key`, and `sample_heldout_nodes`.
  - Accumulates both `planned_trials` and `remaining_trials`.
- Updated `main()`:
  - Passes `total_planned_trials = planned_calls_bound.remaining_trials` to `ProgressReporter`.
  - Determines `strategy_name = getattr(uninitialized_strategy, "name", args.strategy)` for reporter consistency.
  - Telemetry output now includes `f"Model alias:                {resolve_model_alias(args.model)}"`.
  - Catches `ValueError` from `build_live_client` on missing `DEEPSEEK_API_KEY`:
    ```python
    try:
        raw_client = build_live_client(args.model, api_key=None)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    ```

### D. Test Strengthening (`tests/test_live_guard.py`)
- Replaced synthetic JSONL test with real interrupted runs:
  - `test_estimator_resume_subtracts_completed_trials_real_sweep`: executes 5/10 trials of a sweep with `max_llm_calls=5`, verifies 5 records in `raw.jsonl`, and confirms `compute_planned_calls_upper_bound` accurately subtracts completed trials.
  - `test_estimator_resume_subtracts_completed_trials_real_accuracy`: executes 3 calls on a 10-node graph with `max_llm_calls=3`, verifies records in `raw.jsonl`, and confirms resume subtraction.
- Replaced static calculation check with `test_estimator_strategy_max_candidates_upper_bounds_actual`: runs `ConstrainedStrategy` through `run_sweep_experiment` with a counting fake client, asserting `actual_calls == 6` and `actual_calls <= bound.remaining_calls == 6`.
- Added `test_load_existing_keys_status_filtering`: verifies success, failed, error, and unparseable line handling under `retry_failed=False` and `retry_failed=True`.
- Added `TestCandidateUpperBound`:
  - `test_candidate_upper_bound_clamps_above_n_existing`
  - `test_candidate_upper_bound_clamps_negative_to_zero`
  - `test_candidate_upper_bound_fallback_on_exception`
  - `test_candidate_upper_bound_fallback_when_method_absent`
- Added `test_live_run_missing_api_key_clean_error`: verifies stderr message, absence of traceback, and returncode 1.
- Added `TestModelAliasResolution`:
  - `test_resolve_model_alias_precedence`
  - `test_live_preflight_prints_resolved_model_alias`

---

## 5. Test Suite Verification

All **275 tests** across 12 test modules were collected and passed cleanly (273 passed, 2 skipped due to non-embedding identity tests on `NullStrategy` and `FakeNarrowingStrategy`).

### Per-File Test Breakdown

| Test File | Collected Tests | Passed | Skipped | Failed |
| :--- | :---: | :---: | :---: | :---: |
| `tests/test_decision.py` | 15 | 15 | 0 | 0 |
| `tests/test_graph_representation.py` | 51 | 51 | 0 | 0 |
| `tests/test_harness.py` | 16 | 16 | 0 | 0 |
| `tests/test_harness_embedding.py` | 2 | 2 | 0 | 0 |
| `tests/test_live_guard.py` | 27 | 27 | 0 | 0 |
| `tests/test_llm.py` | 12 | 12 | 0 | 0 |
| `tests/test_loader.py` | 26 | 26 | 0 | 0 |
| `tests/test_null_strategy.py` | 39 | 39 | 0 | 0 |
| `tests/test_pilot.py` | 15 | 15 | 0 | 0 |
| `tests/test_schedule.py` | 21 | 21 | 0 | 0 |
| `tests/test_scoring.py` | 7 | 7 | 0 | 0 |
| `tests/test_strategy_interface.py` | 44 | 42 | 2 | 0 |
| **Total** | **275** | **273** | **2** | **0** |

### Test Runner Tail (`pytest -q | tail -3`)

```
======================= 273 passed, 2 skipped in 21.27s ========================
```

---

## 6. Found but Not Changed

1. **Heartbeat Socket-Level Non-Interruptibility:**
   `ProgressReporter` heartbeats are invoked synchronously after LLM calls return (`MeteredLLMClient._invoke_on_call`). If an HTTP network connection hangs indefinitely before a response returns, no heartbeat will fire during the socket wait. As noted in [D-41](4), this is governed by HTTP transport timeouts rather than background timer threads. Preserved as-is to avoid concurrency complexity.
2. **Pending Documentation Edits (DOC-002):**
   Discrepancies in `complete-context.md` (source text phrasing) and `data-formats.md` (underscore file count) remain reserved for task DOC-002 and were not modified.
3. **DATA-004 Concept Name Pool:**
   Name sets for live sweep runs remain under active construction in task DATA-004.

---

## 7. Shared Documentation Diffs

### Diff: `docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index e4a6851..cf2de98 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -331,7 +331,10 @@ Reasoning: hardens experiment harness safety and cost guardrails, provides mid-t
 (5) Phase 1 exit criterion declared met: the Phase 1 exit criterion (INFRA-005) was declared formally met at APC review on 2026-10-07 upon acceptance of FIX-008. Phase 2 (four parallel strategy tracks) is unblocked.
 Reasoning: prevents gross overestimation of API run durations and costs for sub-linear strategies, secures live execution against accidental unmetered or synthetic placeholder runs, guarantees robust progress reporting without crashing on logging failures, and formalizes Phase 1 sign-off. Affects: `src/graph_insertion/strategy.py`, `src/graph_insertion/strategies/null.py`, `src/graph_insertion/decision.py`, `src/graph_insertion/harness.py`, `src/graph_insertion/llm.py`, `scripts/run_experiment.py`, `tests/test_live_guard.py`, `tests/test_schedule.py`, `tests/test_strategy_interface.py`, `tests/test_null_strategy.py`, `docs/context/strategy-interface.md`, `docs/tasks/status.md`, FIX-009.
 
-
-
-
-
+**[D-42]** Single-source-of-truth trial keys, held-out sampling, resume filtering unification, model alias resolution, and live-run error handling:
+(1) Unification of trial keys and held-out node sampling: to eliminate drift between the harness runners (`run_sweep_experiment`, `run_accuracy_experiment`) and the guard estimator (`compute_planned_calls_upper_bound`), trial key formatting and held-out sampling are centralized in `src/graph_insertion/harness.py` via `sweep_trial_key(strategy_name, n, trial_idx)`, `accuracy_trial_key(strategy_name, corpus_name, node, rep)`, and `sample_heldout_nodes(graph, corpus_name, seed, metacademy_sample_size=30)`. Both harness runners and `compute_planned_calls_upper_bound` call these shared helpers. In both contexts, `strategy_name` evaluates to the strategy instance's `.name` attribute (`getattr(strategy, "name", "unknown")` in estimator; `probe_strat.name` in runners), guaranteeing consistent trial keys across all strategies, including those where `.name` differs from the registry key (e.g. `StubNarrowingStrategy.name == "stub_narrowing"` vs registry key `"stub"`).
+(2) Unified resume filter and trial status handling: `_load_existing_keys(raw_jsonl_path, retry_failed)` in `harness.py` serves as the sole implementation of resume skipping for both runners and the estimator. A trial record is considered skippable if `status == "success"`, or if `status in ("failed", "error")` when `retry_failed=False`. Unifying this ensures completed records in `raw.jsonl` are deducted identically from both the planned calls bound and harness trial iterations.
+(3) Trial count alignment: `total_planned_trials` in `scripts/run_experiment.py:main()` is computed as remaining trials (`planned_calls_bound.remaining_trials`), perfectly matching `total_calls` passed to `ProgressReporter`. Full-plan trial count is preserved in `planned_calls_bound.full_plan_trials`.
+(4) Model alias resolution and live pre-flight reporting: `resolve_model_alias(model: Optional[str] = None) -> str` is centralized in `src/graph_insertion/llm.py` with precedence `model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`. `DeepSeekClient.__init__` delegates directly to this helper. In `scripts/run_experiment.py`, pre-flight telemetry logs the resolved alias explicitly as `"Model alias: <resolved>"`.
+(5) Clean live-run missing API key handling: when `--live` is specified without `--dry-run` and `DEEPSEEK_API_KEY` is unset or empty, `scripts/run_experiment.py:main()` catches `ValueError` from `build_live_client`, prints `ERROR: <msg>` to `sys.stderr`, and exits with code 1 without dumping a Python traceback.
+Reasoning: prevents subtle discrepancies between guard cost estimation and harness execution, eliminates duplicate trial-key and sampling logic, provides unambiguous operator feedback on model alias and authentication configuration, and hardens the CLI against unhandled exception traces. Affects: `src/graph_insertion/harness.py`, `src/graph_insertion/llm.py`, `src/graph_insertion/__init__.py`, `scripts/run_experiment.py`, `tests/test_live_guard.py`, `docs/tasks/status.md`, FIX-010.
```

### Diff: `docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 342091f..a6e4eda 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -80,7 +80,5 @@ Status: **not started** (blocked on Phase 3)
 | FIX-006 | Enforce response model_id provenance in DeepSeekClient, eliminate fabricated manifest defaults, amend G1 validity model check to single observed ID with informational configured_equals_observed ([D-36]), add G2 boundary tests, update default model alias to deepseek-flash, and document off-peak execution window. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 167 tests passing. See report [`docs/reports/FIX-006-claude-code-observed-model-integrity.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-006-claude-code-observed-model-integrity.md). |
 | FIX-007 | Record DSA pilot outcome and acceptance ([D-37]), correct off-peak window in D-36(3), verify rescore equivalence, stage accepted pilot artifacts, and analyze transitive closure implications. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. See report [`docs/reports/FIX-007-claude-code-pilot-outcome.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-007-claude-code-pilot-outcome.md). |
 | FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
-| FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **needs-review** | Completed by Claude Code. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
-
-
-
+| FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07; follow-up FIX-010. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
+| FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **needs-review** | Completed by Gemini. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
```
