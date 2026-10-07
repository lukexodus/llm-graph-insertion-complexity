# FIX-009 — Pre-Live Hardening of run_experiment.py Guard and Progress Path

- **Task ID:** FIX-009
- **Agent:** Claude Code
- **Date:** 2026-10-07
- **Status:** needs-review
- **Related Tasks & Decisions:** INFRA-005, FIX-008, [D-35], [D-38], [D-40], [D-41]

---

## 1. Executive Summary

Task FIX-009 hardens the experimental CLI harness (`scripts/run_experiment.py`), strategy interface contract, and LLM metering infrastructure prior to live API execution:

1. **Strategy-Aware & Resume-Aware Planned Calls Estimator:**
   Replaced the crude brute-force calculation (`sum(n * trials)`) with a strategy-aware worst-case candidate estimator. The harness instantiates the uninitialized strategy once via factory (prior to `setup()`) and calls `candidate_upper_bound(strategy, n_existing)` multiplied by `CALLS_PER_CANDIDATE = 1`.
   On `--resume`, completed trials recorded in `raw.jsonl` are deducted from planned trials (reusing unified `_load_existing_keys`), and the remaining bound is optionally capped by `--max-llm-calls`. Both the `ProgressReporter` and live peak window intersection guard are wired directly to `bound.remaining_bound`.
   For `NullStrategy(k=1)` over the full D-35 sweep matrix (6 sizes × 10 trials), the planned upper bound drops from 38,500 calls to exactly 60 calls.

2. **Live-Run Gates & Pre-Flight Dry Run:**
   - Enforced that `--live` in sweep mode strictly requires `--names-file` pointing to the verified DATA-004 synthetic concept pool; placeholder synthetic names are strictly forbidden in live sweeps.
   - Implemented `--live --dry-run` to print full pre-flight telemetry, evaluate the peak schedule window, report whether a live run would be accepted or refused, and exit 0 without requiring `DEEPSEEK_API_KEY` or instantiating a live network client.
   - Centralized live client construction into `build_live_client(model, api_key)`, guaranteeing zero network I/O during client initialization.
   - Corrected `--model` CLI help text regarding `DEEPSEEK_MODEL` environment variable precedence.

3. **`MeteredLLMClient` Progress Callback Hardening:**
   Protected `MeteredLLMClient._invoke_on_call()` against exceptions thrown by `on_call` hooks (e.g., `ProgressReporter`). If an error occurs, `self.on_call_errors` increments, a single warning is emitted to `sys.stderr` on the first failure only, and the completion call succeeds normally without corrupting call or retry accounting.

4. **Unit & Conformance Test Hardening:**
   - Added `test_non_minute_aligned_end_point_in_peak` verifying that windows ending on peak boundaries with non-minute offsets are caught.
   - Added 5 estimator unit tests verifying D-35 NullStrategy exact bound (60), resume deduction, max-llm-calls capping, bounded strategy vs actual, and brute-force fallback.
   - Added conformance suite assertion verifying that if a strategy defines `max_candidates(n_existing)`, `len(shortlist.candidates) <= max_candidates(n_existing)`.
   - Corrected the hypergeometric standard error docstring in `tests/test_null_strategy.py` to "about 5 standard errors (SE about 0.006)".

5. **Shared Documentation & Status Updates:**
   - Updated `docs/context/strategy-interface.md` with `uses_embeddings` ([D-38](2)) and `max_candidates` ([D-41]).
   - Appended decision `[D-41]` to `docs/decisions/decision-log.md`.
   - Updated `docs/tasks/status.md`: advanced INFRA-005 and FIX-008 to `done`, marked Phase 1 `done`, opened Phase 2, and registered FIX-009 as `needs-review`.

The test suite expanded from 252 collected (250 passing, 2 skipped) to **266 collected (264 passing, 2 skipped)**. All tests pass with zero network access and zero API expenditure.

---

## 2. Prompt Assumptions vs Repository Reality

As required by `AGENTS.md`, every statement in the prompt was verified directly against the repository filesystem. The following discrepancies were identified and resolved:

1. **`_load_existing_keys` Existence in `harness.py`:**
   - *Prompt Statement:* "harness.py's existing _load_existing_keys logic".
   - *Reality:* In the baseline repository, `_load_existing_keys` did not exist. Only `load_existing_results(jsonl_path: Path)` existed in `src/graph_insertion/harness.py`, which parsed complete trial dictionaries.
   - *Resolution:* Implemented `_load_existing_keys(raw_jsonl_path: Path, retry_failed: bool = False) -> set[str]` in `src/graph_insertion/harness.py`, deduplicating trial keys and filtering out error status rows unless `retry_failed=True`. This function was reused directly in `scripts/run_experiment.py`.

2. **`DEEPSEEK_MODEL` Environment Variable:**
   - *Prompt Statement:* "DEEPSEEK_MODEL is not actually read anywhere in the repo (only DEEPSEEK_API_KEY is read, in llm.py line 282)."
   - *Reality:* `DEEPSEEK_MODEL` **is** read in `src/graph_insertion/llm.py` line 293:
     ```python
     self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"
     ```
     `scripts/pilot_dsa_zero_shot.py` lines 86–87 also explicitly documents this environment variable fallback.
   - *Resolution:* Preserved `src/graph_insertion/llm.py` without modification. Updated `scripts/run_experiment.py` `--model` CLI argument help string to accurately explain that omitting `--model` defers to `os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`.

3. **Hypergeometric Standard Error in `tests/test_null_strategy.py`:**
   - *Prompt Statement:* "the 7 SE claim in tests/test_null_strategy.py:test_null_strategy_recall_converges_to_analytic_expectation: the actual SE for N=10, K=2, n=2 across 2,000 trials is about 0.006, so tolerance 0.03 is about 5 SE, not 7. Fix the comment."
   - *Reality:* Verified mathematically: For $N=10$, $K=2$ gold parents, and $n=2$ sampled candidates, the number of retrieved parents $X \sim \text{Hypergeometric}(N=10, K=2, n=2)$ has support $\{0, 1, 2\}$ with probabilities $P(X=0) = 28/45$, $P(X=1) = 16/45$, $P(X=2) = 1/45$. Recall $R = X/2 \in \{0, 0.5, 1.0\}$.
     $\mathbb{E}[R] = 0.20$.
     $\text{Var}(R) = \frac{1}{4} \text{Var}(X) = \frac{1}{4} \cdot \frac{2 \cdot 8 \cdot 2 \cdot 8}{100 \cdot 9} = \frac{64}{900} = \frac{16}{225} \approx 0.07111$.
     Standard deviation $\sigma = \sqrt{16/225} = 4/15 \approx 0.26667$.
     Across $M = 2000$ seeds, standard error of the mean $SE = \sigma / \sqrt{2000} \approx 0.0059628 \approx 0.00596 \approx 0.006$.
     The tolerance interval $\pm 0.03$ represents $0.03 / 0.0059628 \approx 5.03$ standard errors.
   - *Resolution:* Corrected the test docstring in `tests/test_null_strategy.py` to state: "about 5 standard errors (SE about 0.006)".

4. **Non-Minute-Aligned Schedule Sampling Boundary:**
   - *Prompt Statement:* "Monday 2026-10-05 00:50:30 UTC with duration 570s ... pre-FIX-008 1-minute step would miss 01:00:00 peak onset because 00:50:30 + 10*60 = 01:00:30 > 00:50:30 + 570s = 01:00:00."
   - *Reality:* Confirmed. Pre-FIX-008 sampled points were $t_k = t_0 + 60k$. Here $t_0 = 00:50:30$, $t_0 + 570\text{s} = 01:00:00$. The loop sampled $00:50:30, 00:51:30, \dots, 00:59:30$. The next step $01:00:30 > 01:00:00$, so the loop terminated. All sampled points ended in `:30` and were off-peak; the onset at $01:00:00$ fell strictly between $00:59:30$ and the end of the window. FIX-008 added `is_deepseek_peak(end_utc)`, which catches $01:00:00$ exactly.
   - *Resolution:* Added unit test `test_non_minute_aligned_end_point_in_peak` in `tests/test_schedule.py`.

---

## 3. Detailed Changes Implemented

### Part A — Strategy-Aware & Resume-Aware Planned Calls Estimator

- **`src/graph_insertion/strategy.py`:**
  - Added helper function `candidate_upper_bound(strategy: NarrowingStrategy, n_existing: int) -> int`. Checks if `strategy` implements `max_candidates(n_existing: int) -> int`, calls it, and clamps the return value to `[0, n_existing]`. If undefined or an exception is raised, gracefully falls back to `n_existing` (brute force upper bound).
  - Documented the optional `max_candidates` method in `NarrowingStrategy` class docstring.
- **`src/graph_insertion/strategies/null.py`:**
  - Implemented `max_candidates(self, n_existing: int) -> int: return min(self.k, n_existing)` on `NullStrategy`.
- **`src/graph_insertion/decision.py`:**
  - Defined and exported `CALLS_PER_CANDIDATE: int = 1`, establishing the constant for single-call pairwise LLM decisions ([D-29]).
- **`src/graph_insertion/harness.py`:**
  - Implemented `_load_existing_keys(raw_jsonl_path: Path, retry_failed: bool = False) -> set[str]`.
- **`scripts/run_experiment.py`:**
  - Added `PlannedCallsBound(int)` class subclassing `int` to hold `.full_plan_bound` and `.remaining_bound` while preserving backwards-compatible integer semantics.
  - Rewrote `compute_planned_calls_upper_bound()`:
    1. Instantiates `uninitialized_strategy = strategy_factory(dummy_graph, embedder)` once without running `setup()`.
    2. Computes per-trial bounds: `CALLS_PER_CANDIDATE * candidate_upper_bound(uninitialized_strategy, n_existing)`.
    3. Handles `--resume`: loads existing keys from `raw.jsonl` using `_load_existing_keys` and skips completed trials unless `args.retry_failed=True`.
    4. Caches both `full_plan_bound` and `remaining_bound`.
    5. Cops `remaining_bound` to `min(remaining_bound, args.max_llm_calls)` if `--max-llm-calls` is set.
  - Updated `ProgressReporter(total_calls=...)` and peak schedule guard in `run_experiment.py` to use `planned_calls.remaining_bound`.
  - Updated pre-flight output to display:
    ```
    Pre-flight estimate:
      Full plan upper bound:      <full_plan_bound> LLM calls
      Remaining calls (to run):   <remaining_bound> LLM calls
    ```

### Part B — Live-Run Gates & Pre-Flight Dry Run

- **`scripts/run_experiment.py`:**
  - Sweep mode gate: when `--live` is passed in sweep mode, asserts `args.names_file is not None` and that the file exists and is not empty. If omitted, raises a clear error instructing the operator to generate concept names via DATA-004.
  - Added `--live --dry-run` branch: computes `planned_calls`, checks peak window intersection for the estimated duration, prints the pre-flight telemetry and peak check verdict (e.g. `[LIVE DRY-RUN] Peak check: run permitted...` or `[LIVE DRY-RUN] Peak check: run WOULD BE REFUSED...`), and exits 0 immediately without inspecting `DEEPSEEK_API_KEY` or instantiating a client.
  - Extracted helper `build_live_client(model: Optional[str] = None, api_key: Optional[str] = None) -> MeteredLLMClient`: validates `DEEPSEEK_API_KEY`, constructs `DeepSeekClient(model=model, api_key=api_key)`, and wraps it in `MeteredLLMClient`. Verified to perform zero network I/O upon creation.
  - Corrected `--model` CLI help text.

### Part C — `MeteredLLMClient` on_call Error Accounting & Tests

- **`src/graph_insertion/llm.py`:**
  - Added `self.on_call_errors: int = 0` to `MeteredLLMClient`.
  - Added `_invoke_on_call(self, snapshot: LLMMeterSnapshot)`: wraps `self.on_call(snapshot)` in `try...except Exception`. On exception, increments `self.on_call_errors` and emits a single warning to `sys.stderr` on the first error only (`self.on_call_errors == 1`).
  - Added `self.on_call_errors = 0` to `MeteredLLMClient.reset()`.
- **`tests/test_live_guard.py`:**
  - Added `TestMeteredLLMClientOnCallErrorHandling`:
    - `test_on_call_exception_increments_error_counter_and_does_not_crash_complete`: verifies completion succeeds, counters match, and `on_call_errors` is incremented.
    - `test_on_call_warning_emitted_only_once_to_stderr`: verifies exactly one warning line is emitted to `stderr` across multiple failing calls.
  - Added `TestEstimatorAccuracyAndResume`:
    - `test_d35_null_strategy_estimator_exact_bound_vs_metered_run`: verifies NullStrategy(k=1) has bound 60 across 6 sizes × 10 trials, matching metered run calls exactly.
    - `test_estimator_with_resume_subtracts_completed_trials`: verifies completed trials in `raw.jsonl` decrement remaining bound.
    - `test_estimator_capped_by_max_llm_calls`: verifies `--max-llm-calls` caps the remaining bound.
    - `test_estimator_with_max_candidates_greater_than_actual_nodes`: verifies clamping to `n_existing` when $k > n_{\text{existing}}$.
    - `test_estimator_fallback_for_strategy_without_max_candidates`: verifies fallback to brute force $N$ when strategy lacks `max_candidates`.
  - Added `TestLiveRunGates`:
    - `test_live_sweep_refused_without_names_file`: verifies refusal when `--names-file` is missing in live sweep.
    - `test_live_dry_run_exits_zero_without_api_key`: verifies `--live --dry-run` exits 0 with no environment variables set.
  - Replaced test `test_client_construction_parity_with_pilot` with `test_build_live_client_defaults_and_no_network`.
- **`tests/test_schedule.py`:**
  - Added `test_non_minute_aligned_end_point_in_peak`.
- **`tests/test_strategy_interface.py`:**
  - Added `test_max_candidates_bound_if_defined` in `StrategyConformanceSuite`.
  - Verified assertions across all conformance tests.
- **`tests/test_null_strategy.py`:**
  - Updated docstring for `test_null_strategy_recall_converges_to_analytic_expectation`.

---

## 4. Test Suite Verification

All 266 tests collected across the 12 test modules pass cleanly (264 passed, 2 skipped due to non-embedding identity tests on `NullStrategy` and `FakeNarrowingStrategy`).

### Per-File Collected Test Breakdown

| Test File | Collected Tests | Passed | Skipped | Failed |
| :--- | :---: | :---: | :---: | :---: |
| `tests/test_decision.py` | 15 | 15 | 0 | 0 |
| `tests/test_graph_representation.py` | 51 | 51 | 0 | 0 |
| `tests/test_harness.py` | 16 | 16 | 0 | 0 |
| `tests/test_harness_embedding.py` | 2 | 2 | 0 | 0 |
| `tests/test_live_guard.py` | 18 | 18 | 0 | 0 |
| `tests/test_llm.py` | 12 | 12 | 0 | 0 |
| `tests/test_loader.py` | 26 | 26 | 0 | 0 |
| `tests/test_null_strategy.py` | 39 | 39 | 0 | 0 |
| `tests/test_pilot.py` | 15 | 15 | 0 | 0 |
| `tests/test_schedule.py` | 21 | 21 | 0 | 0 |
| `tests/test_scoring.py` | 7 | 7 | 0 | 0 |
| `tests/test_strategy_interface.py` | 44 | 42 | 2 | 0 |
| **Total** | **266** | **264** | **2** | **0** |

### Test Runner Summary (`pytest -q | tail -3`)

```
======================= 264 passed, 2 skipped in 14.43s ========================
```

---

## 5. Found but Not Changed

1. **Completion-Driven Progress & Heartbeat Reporting:**
   As noted in [D-41](4), `MeteredLLMClient._invoke_on_call()` is triggered synchronously inside `complete()`. Consequently, progress updates and 30-second heartbeat checks fire after each LLM call returns. If a single HTTP network request hangs indefinitely at the socket level, no heartbeat will emit during the wait itself. This is governed by socket/HTTP transport timeouts (`httpx.Timeout`), not by asynchronous background timers. Left unchanged to preserve a single-threaded, lock-free architecture without thread management complexity.

2. **Pending Documentation & Corpus Stales (DOC-002):**
   The minor discrepancies noted in `complete-context.md` (source text status) and `data-formats.md` (underscore file count) belong to task DOC-002 and were left untouched.

3. **DATA-004 Synthetic Name Sets:**
   The `--names-file` requirement in live sweep mode is now hard-gated. Synthetic name sets will be generated under task DATA-004.

---

## 6. Shared Documentation Git Diffs

### Diff: `docs/context/strategy-interface.md`

```diff
diff --git i/docs/context/strategy-interface.md w/docs/context/strategy-interface.md
index 102c30c..df5258e 100644
--- i/docs/context/strategy-interface.md
+++ w/docs/context/strategy-interface.md
@@ -47,6 +47,15 @@ class NarrowingStrategy(ABC):
         ...
 
     @abstractmethod
+    def max_candidates(self, n_existing: int) -> int:
+        """Return an upper bound on candidates shortlisted given n_existing nodes.
+
+        Optional method. When implemented, harness pre-flight estimators use it
+        to compute tight call bounds ([D-41]). If omitted, the harness defaults
+        to n_existing (brute-force upper bound).
+        """
+        ...
+
     def on_inserted(
         self,
         new_name: str,
@@ -107,6 +116,14 @@ class MyConcreteStrategy(NarrowingStrategy):
     def shortlist(self, new_name: str) -> ShortlistResult:
         # Narrow candidates from self.graph
         ...
+
+    def max_candidates(self, n_existing: int) -> int:
+        # Optional upper bound on candidates shortlisted when graph has n_existing nodes.
+        # For fixed-k strategies, min(self.k, n_existing).
+        # For unconstrained strategies, can be omitted (defaults to n_existing).
+        return n_existing
 
     def on_inserted(
         self,
@@ -170,6 +187,8 @@ from tests.test_strategy_interface import StrategyConformanceSuite
 from graph_insertion.strategies.my_strategy import MyConcreteStrategy
 
 class TestMyConcreteStrategyConformance(StrategyConformanceSuite):
+    uses_embeddings: bool = True
+
     @pytest.fixture
     def strategy_factory(self):
         def _factory(graph, embedder):
@@ -183,6 +202,8 @@ The conformance suite automatically verifies:
 1. **Candidate subset & exclusion:** `shortlist()` returns a subset of existing graph nodes, containing no duplicates, and never containing `new_name`.
 2. **Graph immutability:** `shortlist()` does not mutate node or edge sets in `ConceptGraph`.
 3. **Determinism:** Identical seeds produce identical shortlists and score sequences.
-4. **D-21 text payload compliance:** All texts passed to embedders match `embed_text(c)` for some concept $c$ in the trial (lowercase, no raw underscores, no domain descriptions).
-5. **Cached single-embedding reuse ([D-26]):** An insertion triggers exactly 1 embedding call (`embed_in_update_s == 0.0`), verifying that `on_inserted` reuses the vector computed in `shortlist`.
+4. **D-21 text payload compliance:** All texts passed to embedders match `embed_text(c)` for some concept $c$ in the trial (lowercase, no raw underscores, no domain descriptions). When `uses_embeddings=False`, asserts zero embedding calls, zero embedding time, and empty texts log.
+5. **Cached single-embedding reuse ([D-26]):** An insertion triggers exactly 1 embedding call (`embed_in_update_s == 0.0`), verifying that `on_inserted` reuses the vector computed in `shortlist`. When `uses_embeddings=False`, asserts exactly zero embedding calls in both phases.
 6. **Repeated insertions:** Successive calls to `insert_node()` correctly expose newly added nodes as candidates for subsequent insertions.
+7. **Embedder identity contract ([D-28]):** The exact `MeteredEmbedder` passed to `setup()` is stored as `strategy._embedder` (verified for embedding strategies; bypassed for non-embedding strategies where `_embedder is None`).
+8. **Max candidates bound ([D-41]):** If the strategy defines `max_candidates(n_existing)`, verifies `len(shortlist.candidates) <= max_candidates(n_existing)` across all shortlisting steps.
```

### Diff: `docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index d2ea2e9..e4a6851 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -323,6 +323,14 @@ Reasoning: establishes the complete harness testing pipeline with a verified non
 (4) Strict names validation: `load_and_validate_names_file()` does not swallow exceptions during benchmark corpus discovery/loading, but raises `RuntimeError` identifying the failed corpus name. Concept names are validated to ensure zero overlap with all 12 benchmark corpora on both bare concept names and their normalized text payload representation (`embed_text()` form).
 Reasoning: hardens experiment harness safety and cost guardrails, provides mid-trial operator visibility during long-running insertions, ensures unambiguous process-local resumption semantics, and enforces strict synthetic name isolation from ground truth corpora. Affects: `scripts/run_experiment.py`, `src/graph_insertion/schedule.py`, `src/graph_insertion/llm.py`, `src/graph_insertion/harness.py`, `tests/test_schedule.py`, `tests/test_null_strategy.py`, `tests/test_harness_embedding.py`, `tests/test_live_guard.py`, FIX-008.
 
+**[D-41]** Strategy-aware bound estimator, candidate bounds, calls-per-candidate, live execution gates, and client construction:
+(1) Strategy-aware & resume-aware planned calls upper bound: in `scripts/run_experiment.py`, `compute_planned_calls_upper_bound()` replaces the crude brute-force estimate with an exact worst-case bound evaluated per planned trial: `trial_bound = CALLS_PER_CANDIDATE * candidate_upper_bound(strategy, n_existing_at_trial)`. The strategy is instantiated once via factory before setup (`uninitialized_strategy`). On `--resume`, trials already successfully completed in `raw.jsonl` (using shared completed-key logic `_load_existing_keys`) are subtracted from the planned trials; failed trials are skipped unless `--retry-failed` is passed. If `--max-llm-calls` is set, the remaining calls bound is capped to `min(remaining_bound, max_llm_calls)`. Pre-flight telemetry prints both full-plan upper bound and remaining upper bound. The remaining bound is passed to `ProgressReporter(total_calls=...)` and used for the live peak window intersection check.
+(2) Strategy `max_candidates` contract and `CALLS_PER_CANDIDATE`: strategies may optionally define `max_candidates(self, n_existing: int) -> int`, returning an upper bound on candidates shortlisted when $n_{\text{existing}}$ nodes exist in the graph. Helper `candidate_upper_bound(strategy, n_existing)` invokes this method and clamps the result to `[0, n_existing]`, falling back to $n_{\text{existing}}$ (brute force) if undefined or raising. For `NullStrategy`, `max_candidates(n_existing)` returns `min(self.k, n_existing)`. Over the full D-35 matrix (6 sizes × 10 trials), $k=1$ yields an exact bound of 60 calls (vs 38,500 under brute-force estimation). `CALLS_PER_CANDIDATE: int = 1` is locked in `src/graph_insertion/decision.py`, reflecting the single-call contract of `PairwiseDecisionStep` ([D-29]). The conformance suite enforces that if `max_candidates` is defined, `len(shortlist.candidates) <= max_candidates(n_existing)`.
+(3) Live-run execution gates and `build_live_client`: in sweep mode, `--live` execution strictly requires an external names file (`--names-file`) sourced from the verified DATA-004 concept name pool; placeholder names are prohibited in live sweeps. `--live --dry-run` computes and prints the pre-flight telemetry and notes whether a real live run would be permitted or refused by the peak check, then exits 0 without requiring `DEEPSEEK_API_KEY` or constructing a live client. Live client construction is centralized in `build_live_client(model, api_key)` in `run_experiment.py`, which validates the presence of `DEEPSEEK_API_KEY`, configures `DeepSeekClient`, and performs zero network I/O upon instantiation. When `--model` is omitted (None), `DeepSeekClient` uses its internal default `os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`.
+(4) `MeteredLLMClient` on_call error accounting and completion-driven heartbeat limitation: `MeteredLLMClient` protects against exceptions in `on_call` progress callbacks: if a callback raises, `self.on_call_errors` is incremented, a single warning line is printed to `sys.stderr` on the first exception only, and the completion call proceeds normally without corrupting call/retry counters. Heartbeat limitation: because the heartbeat hook is invoked synchronously within `complete()`, mid-trial heartbeats are completion-driven (emitted after individual LLM requests return). A single long or hanging network call will not trigger a heartbeat during the wait itself.
+(5) Phase 1 exit criterion declared met: the Phase 1 exit criterion (INFRA-005) was declared formally met at APC review on 2026-10-07 upon acceptance of FIX-008. Phase 2 (four parallel strategy tracks) is unblocked.
+Reasoning: prevents gross overestimation of API run durations and costs for sub-linear strategies, secures live execution against accidental unmetered or synthetic placeholder runs, guarantees robust progress reporting without crashing on logging failures, and formalizes Phase 1 sign-off. Affects: `src/graph_insertion/strategy.py`, `src/graph_insertion/strategies/null.py`, `src/graph_insertion/decision.py`, `src/graph_insertion/harness.py`, `src/graph_insertion/llm.py`, `scripts/run_experiment.py`, `tests/test_live_guard.py`, `tests/test_schedule.py`, `tests/test_strategy_interface.py`, `tests/test_null_strategy.py`, `docs/context/strategy-interface.md`, `docs/tasks/status.md`, FIX-009.
```

### Diff: `docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index ebcd340..a0cbbe7 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -21,6 +21,8 @@ without reconstructing status from scattered report files.
 
 ## Phase 1 — Shared Infrastructure & Interface Contract
 
+Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-10-07).
+
 | ID        | Task                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Status   | Notes / Report                                                                                                                                                               |
 | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
 | DATA-001  | Independently re-verify every claim in `docs/context/data-formats.md` against the full raw files (not just head/tail excerpts). Specifically: confirm DSA and Metacademy delimiter/label conventions; check for delimiter-collision edge cases in both; inspect at least two of the ten example MEKG files (one small, one large) to confirm their format; inspect `concept_descriptions/` folder contents and assess sufficiency as build-phase source text. | **done** | Completed by Gemini. See report [`docs/reports/DATA-001-gemini-verify-file-formats.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-001-gemini-verify-file-formats.md). |
@@ -30,7 +32,7 @@ without reconstructing status from scattered report files.
 | INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **done** | Completed. Strategy contract, lifecycle, Embedder protocol, MeteredEmbedder, FakeEmbedder, and insert_node driver defined ([D-24], [D-25]). Conformance suite passes (62 tests). See spec [`docs/context/strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/strategy-interface.md) and report [`docs/reports/INFRA-002-gemini-strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-002-gemini-strategy-interface.md). |
 | INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **done** | Completed by Gemini. Discovers 12 corpora, loads into `ConceptGraph` and `GoldJudgmentSet` with strict parsing, canonical orientations via `oriented_edge` ([D-15], [D-19], [D-23]), and graph-level domain context table ([D-27]). All 12 graphs confirmed DAGs. See report [`docs/reports/INFRA-003-gemini-corpus-loader.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-003-gemini-corpus-loader.md). |
 | INFRA-004 | Build the measurement harness (accuracy runner + cost sweep runner): leave-one-out evaluation on DSA/Metacademy and cost-only scaling sweep over synthetic name sets. | **done** | Completed by Gemini. `ConceptGraph.without_node()` implemented, scoring module (pure functions, micro/macro precision/recall/F1, shortlist recall, DSA unjudged row sensitivity) built ([D-30]), harness driver with trial isolation, overhead accounting, streaming raw.jsonl and summary.csv, CLI runner with dry-run and safety limits ([D-31]). 141 tests passing. See report [`docs/reports/INFRA-004-gemini-measurement-harness.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-004-gemini-measurement-harness.md). |
-| INFRA-005 | Build and run the trivial "null strategy" (e.g., attach new node to a random existing node) through the full harness, end-to-end, at all graph sizes.                                                                                                                                                                                                                                                                                                         | **needs-review** | Completed by Claude Code and Gemini. NullStrategy implemented in `src/graph_insertion/strategies/null.py` with random-k shortlist ([D-38](1)), conformance suite enhanced with `uses_embeddings` flag ([D-38](2)), full D-35 matrix (6 sizes × 10 trials) executed offline through harness with 100% success, progress reporting and peak schedule guard ([D-38](4)), pilot price defaults updated to off-peak values ([D-38](5)), and `--names-file` validation implemented ([D-38](3)). 234 total tests collected (232 passing, 2 skipped). See report [`docs/reports/INFRA-005-claude-code-null-strategy-e2e.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-005-claude-code-null-strategy-e2e.md). (Phase 1 exit criterion pending APC review). |
+| INFRA-005 | Build and run the trivial "null strategy" (e.g., attach new node to a random existing node) through the full harness, end-to-end, at all graph sizes.                                                                                                                                                                                                                                                                                                         | **done** | Completed by Claude Code and Gemini. Accepted at APC review 2026-10-07. NullStrategy implemented in `src/graph_insertion/strategies/null.py` with random-k shortlist ([D-38](1)), conformance suite enhanced with `uses_embeddings` flag ([D-38](2)), full D-35 matrix (6 sizes × 10 trials) executed offline through harness with 100% success, progress reporting and peak schedule guard ([D-38](4)), pilot price defaults updated to off-peak values ([D-38](5)), and `--names-file` validation implemented ([D-38](3)). 234 total tests collected (232 passing, 2 skipped). See report [`docs/reports/INFRA-005-claude-code-null-strategy-e2e.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-005-claude-code-null-strategy-e2e.md). |
 | INFRA-006 | Build the shared decision step (the identical final step all four strategies use) and its metered LLM client: prompt semantics (is A a prerequisite of B, indirect allowed, since the gold graphs are not transitively reduced per INFRA-001), call granularity (reserved for Luke), parsing, call and time metering.                                                                                                                                         | **done** | Completed by Gemini. PairwiseDecisionStep, MeteredLLMClient, DeepSeekClient via httpx, and leave-one-out DSA pilot script implemented ([D-29]). 123 tests passing. See report [`docs/reports/INFRA-006-gemini-decision-step-llm-client.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-006-gemini-decision-step-llm-client.md). |
 | PILOT-001 | Execute live leave-one-out DSA pilot on DeepSeek API (prompt v2, n=29, 812 calls).                                                                                                                                                                                                                                                                                                                                            | **done** | CONDITIONAL acceptance per [D-37]. All 812 calls completed (0 retries, 0 transport/parse failures, cost $0.0198). Micro F1 0.541, recall 0.611, flip rate 15.38%, swap consistency 85.71%. Results in `results/pilot/20261007_053743Z/` (force-added per [D-35]). |
 
 ## Phase 2 — Four Parallel Strategy Tracks
 
-Status: **not started** (blocked on Phase 1's exit criterion, INFRA-005)
+Status: **open** (unblocked following Phase 1 completion; four parallel tracks ready for implementation)
 
 | ID        | Task                                       | Status | Notes                                                                          |
 | --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
@@ -77,7 +79,8 @@ Status: **not started** (blocked on Phase 3)
 | FIX-005 | Promote decision prompt to PROMPT_VERSION v2 with 3 few-shot examples ([D-33]); pilot acceptance criteria G1/G2 and line count correction ([D-34]); sweep/eval/embedding/Strategy-2 specs ([D-35]); fix macro F1 definition and undefined handling; add evaluate_acceptance. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 155 tests passing. See report [`docs/reports/FIX-005-claude-code-prompt-v2.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-005-claude-code-prompt-v2.md). |
 | FIX-006 | Enforce response model_id provenance in DeepSeekClient, eliminate fabricated manifest defaults, amend G1 validity model check to single observed ID with informational configured_equals_observed ([D-36]), add G2 boundary tests, update default model alias to deepseek-flash, and document off-peak execution window. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 167 tests passing. See report [`docs/reports/FIX-006-claude-code-observed-model-integrity.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-006-claude-code-observed-model-integrity.md). |
 | FIX-007 | Record DSA pilot outcome and acceptance ([D-37]), correct off-peak window in D-36(3), verify rescore equivalence, stage accepted pilot artifacts, and analyze transitive closure implications. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. See report [`docs/reports/FIX-007-claude-code-pilot-outcome.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-007-claude-code-pilot-outcome.md). |
-| FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **needs-review** | Completed by Claude Code. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
+| FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
+| FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **needs-review** | Completed by Claude Code. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
```
