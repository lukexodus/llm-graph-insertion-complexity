# FIX-008: Harden INFRA-005 (Live Guard, Progress, Embedding-Through-Harness, Test Strength)

**Agent:** Claude Code  
**Task ID:** FIX-008  
**Date:** 2026-10-07  
**Status:** needs-review (hardening pass on Phase 1 exit criterion)  
**Decision appended:** `[D-40]` in `docs/decisions/decision-log.md`

---

## 1. Executive Summary

This task hardens the Phase 1 infrastructure established in INFRA-005:
1. **Live Guard & Pre-Flight Cost Telemetry (`scripts/run_experiment.py`, `src/graph_insertion/schedule.py`):**
   - Replaced the hard-coded 600 s window with an analytic worst-case estimate:
     $$\text{planned\_calls\_upper\_bound} = \sum_{n} (n \times \text{trials}) \quad \text{(sweep)}$$
     $$\text{planned\_calls\_upper\_bound} = \sum_{\text{corpora}} k_{\text{sample}} \times (n_{\text{nodes}} - 1) \times \text{repeats} \quad \text{(accuracy)}$$
     $$\text{estimated\_seconds} = \text{planned\_calls\_upper\_bound} \times \text{--est-seconds-per-call (default 1.0 s)}$$
   - Prints full pre-flight telemetry before any live call: planned calls, estimated duration, estimated cost using `--price-in 0.15` and `--price-out 0.60` per 1M tokens with prompt v2 pilot assumptions (~152 input and ~2.5 output tokens per call), current UTC, Philippine Time (PHT, UTC+8), and DeepSeek peak pricing status.
   - Refuses execution if $[\text{now}, \text{now} + \text{estimate}]$ intersects DeepSeek peak pricing hours unless `--allow-peak` is given.
   - Fixed `window_intersects_peak()` to check the exact window end point (as well as 1-minute steps) and corrected docstring.
2. **Call-Driven Progress Reporting & Heartbeat (`scripts/run_experiment.py`, `src/graph_insertion/llm.py`):**
   - Added `on_call` hook and `set_on_call()` to `MeteredLLMClient` invoked with `(calls_done, cumulative_retries)` on every call.
   - Re-architected `ProgressReporter` so that progress and ETA are driven by LLM calls completed rather than trial boundaries. Emits a heartbeat line every 30 s mid-trial:
     `[strategy/size] calls/total_calls (trial X/total_trials) elapsed=Xs ETA=Xs retries=N`
   - Retained per-trial completion lines.
   - Verified that `harness.py` passes per-trial retry deltas (`delta.retries`). Resolved potential double-counting: when the hook is active, `ProgressReporter` tracks cumulative retries directly from the meter and ignores per-trial deltas in `update()`.
3. **Embedding Strategy Through Full Harness (`tests/test_harness_embedding.py`, `src/graph_insertion/harness.py`):**
   - Added end-to-end tests exercising `TinyFakeStrategy` (`uses_embeddings = True`) through both `run_sweep_experiment` and `run_accuracy_experiment`.
   - Verified: `embedding_calls == 1` per insertion, `embedding_calls_in_update == 0` (cached embedding reuse in `on_inserted`), `embed_s > 0`, and no `MeteredEmbedder` identity `ValueError`.
   - Added `"embed_s"` to `timing_keys` in `generate_summary_csv()`, ensuring that `embed_s` statistics (`embed_s_mean`, `embed_s_median`, etc.) appear in `summary.csv` alongside `embedding_calls_mean`.
   - Verified that the harness passes the exact same `MeteredEmbedder` instance to both `strategy.setup()` and `insert_node()` (accuracy: `harness.py` lines 748, 750, 783; sweep: `harness.py` lines 983, 986, 1019).
4. **Strict Names Validation (`scripts/run_experiment.py`, `tests/test_null_strategy.py`):**
   - In `load_and_validate_names_file()`, stopped swallowing exceptions during corpus loading; now raises `RuntimeError` identifying the failed corpus name.
   - Validates zero overlap with benchmark corpora on both exact concept names and their normalized `embed_text()` string representation.
5. **Strengthened Test Suite (`tests/test_null_strategy.py`, `tests/test_live_guard.py`):**
   - **Resume:** First run verified to stop early ($1 \le \text{partial} < \text{total}$); after resume, record count equals total, partial records are unchanged, keys unique.
   - **Process-local call cap:** Verified exact counts ($2 \to 4$) that fail under cumulative semantics.
   - **Spot-check recall:** Selected nodes with nonzero recall (`asymptotic_complexity`, `b_tree`) and zero recall (`avl_tree`, `binary_search`); removed silent None skips; asserted both branches ran.
   - **Analytic recall:** Verified that over 2000 seeds for $n=11, k=2, d=2$, sample mean shortlist recall converges to $k/(n-1) = 2/10 = 0.20$ within $\pm 0.03$ tolerance ($\approx 7$ standard errors).
   - **Client defaults & parity:** Confirmed `DeepSeekClient` defaults (temperature 0.0, max_tokens 16, thinking disabled) and tested that `run_experiment.py` builds the client identically to `pilot_dsa_zero_shot.py`.

---

## 2. Repo Verification vs. Prompt Statements

| Prompt Statement | Repository Verification | Resolution / Finding |
|---|---|---|
| "The --live path (added in INFRA-005) hard-codes a 600 s window" | **Verified True.** `run_experiment.py` line 499 hard-coded `estimated_duration_s = 600.0`. | Replaced with `compute_planned_calls_upper_bound()` and `compute_preflight_estimate()`. |
| "window_intersects_peak checks only 1-minute samples, not exact end; docstring says 1440 checks" | **Verified True.** `schedule.py` stepped in 1-minute increments without testing `end_utc` directly, and docstring asserted a 1440 check upper bound (valid only for 24h windows). | Fixed: explicitly checks `is_deepseek_peak(start_utc)` and `is_deepseek_peak(end_utc)`, plus intermediate steps. Corrected docstring. Added boundary tests in `tests/test_schedule.py`. |
| "Verify whether the harness passes per-trial or cumulative retries to the callback" | **Verified.** In `harness.py` line 795 & 830 (accuracy) and line 1056 (sweep), `retries_count = delta.retries` (per-trial delta). | `ProgressReporter` tracks cumulative retries from `MeteredLLMClient`'s hook when active, preventing double-counting. |
| "DeepSeekClient defaults give thinking disabled, max_tokens 16, temperature 0" | **Verified True.** `src/graph_insertion/llm.py` defines `temperature = 0.0`, `max_tokens = 16`, `thinking = {"type": "disabled"}`. | Confirmed and unit-tested in `tests/test_live_guard.py`. |
| "Harness passes the same metered embedder object to setup() and insert_node" | **Verified True.** Cited lines: accuracy lines 748, 750, 783; sweep lines 983, 986, 1019. | Both runners construct `metered_embedder = MeteredEmbedder(...)` once per trial and pass that exact instance to both `strategy.setup()` and `insert_node()`. |

---

## 3. Test Suite Status & Breakdown

- **Total collected tests:** **252 items**
- **Results:** **250 passed, 2 skipped in 10.69s**

### Per-File Test Count Split (`pytest --collect-only -q`)

```
tests/test_decision.py:           15
tests/test_graph_representation.py: 51
tests/test_harness.py:            16
tests/test_harness_embedding.py:   2  [NEW in FIX-008]
tests/test_live_guard.py:          9  [NEW in FIX-008]
tests/test_llm.py:                12
tests/test_loader.py:             26
tests/test_null_strategy.py:      38  (+3 tests strengthened in FIX-008)
tests/test_pilot.py:              15
tests/test_schedule.py:           20  (+4 boundary tests in FIX-008)
tests/test_scoring.py:             7
tests/test_strategy_interface.py: 41
------------------------------------
TOTAL:                           252
```

### `pytest -q | tail -3`

```
..                                                                       [100%]

======================= 250 passed, 2 skipped in 10.69s ========================
```

*(Note: The 2 skipped tests remain the non-embedding conformance tests where `_embedder = None` intentionally bypasses the embedder identity test per [D-38](2)).*

---

## 4. Harness Embedder Object Passing Verification

In `src/graph_insertion/harness.py`:
- **Accuracy Runner (`run_accuracy_experiment`):**
  - Line 748: `metered_embedder = MeteredEmbedder(embedder_factory())`
  - Line 750: `strategy.setup(g_prime, metered_embedder)`
  - Line 783: `insert_node(..., metered_embedder=metered_embedder)`
  *The exact instance `metered_embedder` is supplied to both `setup()` and `insert_node()`.*
- **Sweep Runner (`run_sweep_experiment`):**
  - Line 983: `metered_embedder = MeteredEmbedder(raw_embedder)`
  - Line 986: `strategy.setup(graph, metered_embedder)`
  - Line 1019: `insert_node(..., metered_embedder=metered_embedder)`
  *The exact instance `metered_embedder` is supplied to both `setup()` and `insert_node()`.*

---

## 5. INFRA-005 Report Errata

The following inaccuracies in `docs/reports/INFRA-005-claude-code-null-strategy-e2e.md` were identified during FIX-008 verification (the report file itself has been preserved untouched):

1. **Section 5 ("`--max-llm-calls` Semantics") Item 2:**
   - *Claim:* "This behavior has been documented in: ... Decision log entry `[D-38](3)`."
   - *Correction:* `[D-38](3)` documented `--names-file` format and validation. The process-local semantics of `--max-llm-calls` was omitted from `[D-38]` and is now formally recorded in `[D-40](1)`.
2. **Section 1 Item 4 & Section 2 Row "Peak Windows":**
   - *Claim:* "Refuses live execution intersecting peak hours unless `--allow-peak` is passed."
   - *Correction:* The live execution guard in INFRA-005 hardcoded a 600 s window rather than computing duration from planned calls, and `window_intersects_peak()` sampled 1-minute points without checking the exact end timestamp. This is resolved in FIX-008 per `[D-40](2)`.
3. **Section 1 Item 4 & Section 2 Row "Progress Lines":**
   - *Claim:* Progress lines were periodically emitted.
   - *Correction:* In INFRA-005, progress was strictly trial-driven (`update()` called after trial completion, with prints gated on `interval_n=10` or `interval_s=30`). During a single long insertion trial with many calls, no progress was printed. In FIX-008, progress is driven by LLM calls with a mid-trial 30 s heartbeat hook on `MeteredLLMClient` per `[D-40](3)`.
4. **Section 6 ("Status of Embedding-Based Strategies in Harness"):**
   - *Claim:* "running a real embedding-based strategy through `run_experiment()` / `HarnessConfig` awaits the implementation of Strategy 2 in Phase 2."
   - *Correction:* An embedding strategy was not yet run at that time, but it did not require waiting for Strategy 2. In FIX-008, a test-only embedding strategy (`TinyFakeStrategy` with `uses_embeddings = True`) was successfully wired and verified end-to-end through both `run_sweep_experiment` and `run_accuracy_experiment` (`tests/test_harness_embedding.py`).
5. **Section 6 Strategy Architecture Categorization:**
   - *Claim:* Section 6 lists "Strategy 1: Full pairwise (no shortlist / brute force)" under "four candidate-narrowing strategies that utilize embeddings".
   - *Correction:* Strategy 1 is brute force pairwise comparison and does not utilize embeddings.

---

## 6. Found but Not Changed

1. **`concept_descriptions/` folder:** Retained for repository history (unused per [D-21]).
2. **`results/pilot/20261007_053743Z/`:** Staged pilot run artifacts remain untouched.
3. **`docs/tasks/status.md` DOC-002 and DATA-004:** Left untouched per instruction.
4. **`docs/reports/INFRA-005-claude-code-null-strategy-e2e.md`:** Left completely unedited; all corrections documented in Section 5 above.
5. **Phase 1 Status:** INFRA-005 left as `needs-review`; FIX-008 row added as `needs-review`.

---

## 7. Shared Doc Edits (Git Diff)

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 4e5e9e6..d2ea2e9 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -316,6 +316,14 @@ Reasoning: acceptance criteria were locked a priori ([D-34]); `evaluate_acceptan
 (5) Pilot price defaults updated to off-peak rates: CLI argument defaults in `scripts/pilot_dsa_zero_shot.py` are updated from legacy values (`0.14/0.28`) to current DeepSeek-V4.1-Flash off-peak rates per [D-37]: `--price-in 0.15` and `--price-out 0.60` per 1M tokens. Cost reporting explicitly prints the rates applied in summaries.
 Reasoning: establishes the complete harness testing pipeline with a verified non-embedding strategy, formalizes conformance requirements for both embedding and non-embedding strategy architectures, guarantees synthetic name hygiene, enforces budget guardrails against peak-rate API consumption, and synchronizes script defaults with vendor pricing. Affects: `src/graph_insertion/strategies/null.py`, `src/graph_insertion/schedule.py`, `src/graph_insertion/harness.py`, `scripts/run_experiment.py`, `scripts/pilot_dsa_zero_shot.py`, `tests/test_strategy_interface.py`, `tests/test_null_strategy.py`, `tests/test_schedule.py`, `tests/test_pilot.py`, INFRA-005.
 
+**[D-40]** Process-local call cap semantics, live guard estimation rule, call-driven progress heartbeat, and strict names validation:
+(1) `--max-llm-calls` process-local semantics: `--max-llm-calls` is strictly process-local, counting successful LLM calls executed during the current process invocation only. It does not carry over or count resumed records from prior runs (correcting the INFRA-005 report's mistaken assertion that [D-38](3) documented this; [D-38](3) documented `--names-file`). When resuming with `--resume`, the process starts with a fresh counter (0 calls) and can execute up to the configured limit in that run.
+(2) Live guard estimation rule and pre-flight telemetry: in `scripts/run_experiment.py`, the hard-coded 600 s window is replaced by an analytic worst-case estimate: `planned_calls_upper_bound = sum(n * trials)` in sweep mode or `sum(k_sample * (n_nodes - 1) * repeats)` in accuracy mode; `estimated_seconds = planned_calls_upper_bound * --est-seconds-per-call` (default 1.0 s/call). Pre-flight printout displays planned calls, estimated duration, estimated cost using `--price-in`/`--price-out` (defaults 0.15/0.60 per 1M tokens) with ~152 input and ~2.5 output tokens per call (based on prompt v2 pilot telemetry), current UTC and PHT time, and DeepSeek peak status. Execution is refused if `[now, now + estimated_seconds]` intersects peak pricing hours unless `--allow-peak` is given. `window_intersects_peak()` checks the exact window end point and intermediate 1-minute steps.
+(3) Call-driven progress reporting and heartbeat: progress tracking is driven by LLM calls completed rather than trial boundaries. `MeteredLLMClient` provides an `on_call` hook invoked on every call with `(calls_done, cumulative_retries)`. `ProgressReporter` emits a heartbeat every 30 s mid-trial displaying `[strategy/size] calls/total_calls (trial X/total_trials) elapsed=Xs ETA=Xs retries=N`, where ETA is computed from call completion rate. Per-trial completion lines are retained. Retry counts use cumulative retries from the meter directly, preventing double-counting against per-trial deltas reported by the harness.
+(4) Strict names validation: `load_and_validate_names_file()` does not swallow exceptions during benchmark corpus discovery/loading, but raises `RuntimeError` identifying the failed corpus name. Concept names are validated to ensure zero overlap with all 12 benchmark corpora on both bare concept names and their normalized text payload representation (`embed_text()` form).
+Reasoning: hardens experiment harness safety and cost guardrails, provides mid-trial operator visibility during long-running insertions, ensures unambiguous process-local resumption semantics, and enforces strict synthetic name isolation from ground truth corpora. Affects: `scripts/run_experiment.py`, `src/graph_insertion/schedule.py`, `src/graph_insertion/llm.py`, `src/graph_insertion/harness.py`, `tests/test_schedule.py`, `tests/test_null_strategy.py`, `tests/test_harness_embedding.py`, `tests/test_live_guard.py`, FIX-008.
+
+
 
 
 
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 3980678..d075890 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -77,5 +77,7 @@ Status: **not started** (blocked on Phase 3)
 | FIX-005 | Promote decision prompt to PROMPT_VERSION v2 with 3 few-shot examples ([D-33]); pilot acceptance criteria G1/G2 and line count correction ([D-34]); sweep/eval/embedding/Strategy-2 specs ([D-35]); fix macro F1 definition and undefined handling; add evaluate_acceptance. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 155 tests passing. See report [`docs/reports/FIX-005-claude-code-prompt-v2.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-005-claude-code-prompt-v2.md). |
 | FIX-006 | Enforce response model_id provenance in DeepSeekClient, eliminate fabricated manifest defaults, amend G1 validity model check to single observed ID with informational configured_equals_observed ([D-36]), add G2 boundary tests, update default model alias to deepseek-flash, and document off-peak execution window. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 167 tests passing. See report [`docs/reports/FIX-006-claude-code-observed-model-integrity.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-006-claude-code-observed-model-integrity.md). |
 | FIX-007 | Record DSA pilot outcome and acceptance ([D-37]), correct off-peak window in D-36(3), verify rescore equivalence, stage accepted pilot artifacts, and analyze transitive closure implications. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. See report [`docs/reports/FIX-007-claude-code-pilot-outcome.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-007-claude-code-pilot-outcome.md). |
+| FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **needs-review** | Completed by Claude Code. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
+
 
 
```
