# Report: FIX-011 — Command Backend Error Codes, Process-Group Session Termination, and Contract Alignment

**Agent:** Gemini  
**Date:** 2026-10-09  
**Task ID:** FIX-011  
**Decision Log:** [D-44]  
**Status:** needs-review  

---

## 1. Overview & Objectives

TASK FIX-011 hardened and corrected the prompt-adapter command backend introduced in DATA-005 across `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, and `docs/context/prompt-adapter-contract.md`:
1. **Contract String Error Code Parsing**: Implemented `parse_adapter_error` in `scripts/generate_name_pool.py` mapping string error codes per Contract v1 (`bad_request` -> 2, `rate_limit` -> 10, `login_required` -> 11, `timeout` -> 12, `refusal` -> 13, `model_mismatch` -> 14, `other` or unknown string -> 1). If stdout has no usable `"error"` field (non-JSON output, empty string, or missing key), falls back to process exit code when it is one of the contract codes (`{1, 2, 10, 11, 12, 13, 14}`), else 1. Preserved existing loop exit semantics (10 -> exit 3, 11 -> exit 4, 14 -> exit 5, 2 -> exit 1, 12/13/1/parse errors -> exit 6 after 3 consecutive failures).
2. **Contract Doc & Stub Exact Alignment**: Updated fixtures in `docs/context/prompt-adapter-contract.md` to use string error codes and clarified the exit code vs error string specification table. Updated `tests/stub_prompt_adapter.py` to emit contract-exact JSON string error codes and matching exit codes for all scenarios. Added `test_contract_doc_fixtures_subprocess_execution` verifying that the doc's failure fixtures use string codes and that each fixture executes cleanly through the real subprocess path with correct `GenerationResult` and exit code fallback behavior.
3. **Process-Group Session Termination on Timeout**: Replaced `subprocess.run(timeout)` with `subprocess.Popen(..., start_new_session=True)` in its own session. On timeout (`timeout_s + 60`), `os.killpg` sends `SIGTERM` to the entire process group (`proc.pid`), waits up to 10 seconds (`proc.wait(timeout=10)`), and escalates to `SIGKILL` if any process remains alive. Added `test_command_backend_process_group_timeout_kills_child` verifying with a stub that spawns an external child process that both parent and child are terminated upon timeout.
4. **Decision Log & Status Tracking**: Appended `[D-44]` to `docs/decisions/decision-log.md` (leaving `[D-43]` unmodified), correcting `[D-43](2)` (adapter runs headed by default, `headless: false`) and `[D-43](6)` (generator is Sonnet-tier via web UI with label as observed, not immutable "Claude 3.5 Sonnet", and different model family reduces but does not eliminate shared-vocabulary bias). Updated `docs/tasks/status.md` with `FIX-011` row.
5. **DATA-004 Defect Verification**: Re-audited and confirmed all six DATA-004 defects documented in the DATA-005 report with exact `file:line` references.

---

## 2. Verification of Prompt Statements & Assumptions

All statements and assumptions in the prompt were verified against the repository:

1. **"CommandGenerationBackend must parse the adapter's string error codes per the contract... If stdout has no usable 'error', fall back to the process exit code..."**:
   - *Verification:* Verified. In DATA-005, `CommandGenerationBackend` attempted integer parsing (`int(raw_err)`), failing to parse contract string error codes such as `"rate_limit"` or `"login_required"`. It also lacked fallback to `proc.returncode` when stdout was non-JSON or lacked an error key. Both have been implemented and verified.
2. **"Make the stub emit contract-exact JSON (string 'error', matching process exit code) for every scenario, and add one test that feeds the exact fixtures from the contract doc through the real subprocess path. Check that the doc's fixtures use string codes and fix them if not."**:
   - *Verification:* Verified. The fixtures in `docs/context/prompt-adapter-contract.md` previously used integer error codes (e.g. `"error": 10`). They were updated to string error codes (`"error": "rate_limit"`). `tests/stub_prompt_adapter.py` was updated to emit matching string error codes and process exit codes. `test_contract_doc_fixtures_subprocess_execution` parses the contract document directly and executes each fixture through the real subprocess path.
3. **"Replace subprocess.run(timeout) with Popen in its own session; on timeout send SIGTERM to the process group, wait 10 s, then SIGKILL. Test with a stub that spawns a child."**:
   - *Verification:* Verified. `CommandGenerationBackend` now uses `Popen(..., start_new_session=True)`. Process group signaling via `os.killpg` with `SIGTERM`, 10-second wait, and `SIGKILL` escalation was implemented. `test_command_backend_process_group_timeout_kills_child` verifies child process termination.
4. **"Decision log, as a NEW entry (D-44; do not edit D-43), correcting D-43: (2) the adapter runs headed by default; (6) the generator is Sonnet-tier via the web UI with the label as observed, not 'Claude 3.5 Sonnet', and using a different model family from the decision step reduces but does not eliminate shared-vocabulary bias. Update status.md."**:
   - *Verification:* Verified. `[D-44]` was appended to `docs/decisions/decision-log.md` without modifying `[D-43]`, and `docs/tasks/status.md` was updated.
5. **Prompt Filename Convention**:
   - *Prompt statement:* Specifies `docs/reports/FIX-011-claude-code-command-backend-error-codes.md`.
   - *Verification:* Followed verbatim despite agent lineage being Gemini, adhering strictly to the user's explicit filename specification.

---

## 3. Test Results & Verification

### 3.1 Exact `pytest -q | tail -3` Output
```
.....                                                                    [100%]

================== 300 passed, 2 skipped in 73.68s (0:01:13) ===================
```

### 3.2 Per-File Collected Test Counts
Total collected: **302** tests across 13 modules (300 passed, 2 skipped):
- `tests/test_decision.py`: 15
- `tests/test_generate_name_pool.py`: 27 (+2 new tests)
- `tests/test_graph_representation.py`: 51
- `tests/test_harness.py`: 16
- `tests/test_harness_embedding.py`: 2
- `tests/test_live_guard.py`: 27
- `tests/test_llm.py`: 12
- `tests/test_loader.py`: 26
- `tests/test_null_strategy.py`: 39
- `tests/test_pilot.py`: 15
- `tests/test_schedule.py`: 21
- `tests/test_scoring.py`: 7
- `tests/test_strategy_interface.py`: 44

---

## 4. Found but not changed (Re-Auditing the Six DATA-004 Defects)

Per prompt instructions, each of the six DATA-004 defects identified in the DATA-005 report was re-verified against the codebase:

### 1. Empty string run ID when `cache_path` is a flat filename
- **Location:** `scripts/generate_name_pool.py:567` (formerly `ab4e104:503`)
- **Code:**
  ```python
  all_run_ids = list(run_ids or [cache_path.parent.name])
  ```
- **Status:** **CONFIRMED**. If `cache_path` is a flat path without directory components (e.g., `Path("raw_responses.jsonl")`), `cache_path.parent` is `Path(".")`, whose `.name` attribute is `""` (empty string). If `run_ids` is omitted or empty, `all_run_ids` evaluates to `[""]`, producing an invalid empty string run ID in output metadata (`meta["run_ids"] = [""]`).

### 2. Live pre-flight cache check stamped `"generator": "live"` instead of `"deepseek"`
- **Location:** `scripts/generate_name_pool.py:1074-1078` (in original DATA-004 `ab4e104:721`)
- **Code in `ab4e104`:**
  ```python
  if len(valid_names) >= target_names:
      print(f"Cache already contains {len(valid_names)} valid names (target: {target_names}). Building pool.")
      build_pool_from_cache(
          cache_path=cache_path,
          output_path=output_path,
          generator_kind=mode,
          ...
      )
  ```
- **Status:** **CONFIRMED**. In original commit `ab4e104`, when resuming an already-sufficient cache in live mode (`mode="live"`), `build_pool_from_cache` was passed `generator_kind=mode`, stamping `"generator": "live"` into the JSON metadata instead of `"generator": "deepseek"`. (Addressed in DATA-005 by mapping to `gen_kind`, but confirmed as a defect in original DATA-004).

### 3. `--build-only` unconditionally stamped `"generator": "deepseek"`
- **Location:** `scripts/generate_name_pool.py:1523` (in original DATA-004 `ab4e104:1003`)
- **Code in `ab4e104`:**
  ```python
  built = build_pool_from_cache(
      cache_path=cache_path,
      output_path=output_path,
      generator_kind="deepseek",
      ...
  )
  ```
- **Status:** **CONFIRMED**. The original `--build-only` branch in `ab4e104` hardcoded `generator_kind="deepseek"`, meaning offline-fake caches or alternative backend caches rebuilt via `--build-only` falsely reported DeepSeek provenance. (Addressed in DATA-005 via backend inspection, but confirmed as an original DATA-004 bug).

### 4. Plural pair heuristic only checks regular `-s` and `-es` suffixes
- **Location:** `scripts/generate_name_pool.py:511-514` (formerly `ab4e104:447-450`)
- **Code:**
  ```python
  if name.endswith("s") and len(name) > 1 and name[:-1] in pool_set:
      is_plural = True
  elif name.endswith("es") and len(name) > 2 and name[:-2] in pool_set:
      is_plural = True
  ```
- **Status:** **CONFIRMED**. The heuristic checks only trailing `s` and `es`. Common irregular or Latin/Greek CS plural pairs (e.g. `matrix`/`matrices`, `vertex`/`vertices`, `query`/`queries`, `automaton`/`automata`) evade detection and remain duplicates in the generated concept pool.

### 5. `test_drop_reasons_fire` did not assert `corpus_overlap_embed`
- **Location:** `tests/test_generate_name_pool.py:156-162` (in `ab4e104:156-162`)
- **Code:**
  ```python
  assert n_raw == len(candidates)
  assert drop_counts["ends_with_txt"] == 1
  assert drop_counts["invalid_snake_case"] == 1
  assert drop_counts["invalid_length"] == 2
  assert drop_counts["invalid_word_count"] == 1
  assert drop_counts["corpus_overlap_exact"] == 2
  assert drop_counts["duplicate_exact"] == 1
  assert drop_counts["plural_pair"] == 2
  ```
- **Status:** **CONFIRMED**. While lines 148-150 commented that candidate embed text matching corpus was being tested, `drop_counts["corpus_overlap_embed"]` was never asserted in `test_drop_reasons_fire` (a separate test was later added, leaving the comment and missing assertion unaddressed in the original test).

### 6. Unparseable responses cause divergent behavior between live loops and resume runs
- **Location:** `scripts/generate_name_pool.py:1296-1299` (formerly `ab4e104:840-843`)
- **Code:**
  ```python
  append_cache_record(cache_path, entry)
  if parsed:
      cache[(round_num, sf)] = entry
      subfield_collected[sf].extend(parsed)
  ```
- **Status:** **CONFIRMED**. When an LLM produces an unparseable response (`parsed = []`), `entry` is written to `cache_path` on disk, but in-memory `cache[(round_num, sf)]` is only updated `if parsed:`. During an active generation run, the loop continues and increments `round_num += 1` at the end of the round, leaving the unparseable subfield unattempted in round 1. However, on a resumed run, `load_completed_cache` skips unparseable records from the disk cache, causing the resumed run to retry `(1, sf)` before proceeding to round 2.

---

## 5. Shared Document Diffs

### 5.1 `git diff docs/decisions/decision-log.md`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 80f5244..ab414ec 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -356,3 +356,10 @@ Reasoning: delivers a reproducible, fully-auditable synthetic concept pool satis
 (5) Weaker provenance & operator controls: Claude Web UI generation lacks controllable temperature and max_tokens, and response payloads report model labels without immutable snapshot IDs. To record provenance accurately, pool metadata sets `temperature: null`, `max_tokens: null`, logs `parameter_note`, records requested settings, observed model labels, adapter version, and tier histogram. For benchmark validity, 'Generate memory from chats' must be disabled in the target Claude profile.
 (6) Cross-model independence vs [D-39] limitation: unlike the default DeepSeek generator where both generator and decision step belong to the DeepSeek family ([D-39](6)), the Claude web backend decouples the concept-name generator (Anthropic Claude 3.5 Sonnet) from the downstream experimental decision step (DeepSeek Flash, [D-29]). This eliminates potential intra-model vocabulary bias while preserving zero-overlap disjunction with benchmark corpora.
 Reasoning: provides a robust fallback generation pipeline bypassing DeepSeek API constraints, eliminates model-family co-dependence between name generation and evaluation, enforces clean failure recovery and caching across web UI sessions, and maintains rigorous data provenance. Affects: `scripts/generate_name_pool.py`, `docs/context/prompt-adapter-contract.md`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/tasks/status.md`, DATA-005.
+
+**[D-44]** Adapter contract error code parsing, process-group session termination, and headed/model bias corrections to [D-43] (FIX-011):
+(1) Error code contract parsing: `CommandGenerationBackend` in `scripts/generate_name_pool.py` parses the adapter's string error codes per Contract v1: `bad_request` -> 2, `rate_limit` -> 10, `login_required` -> 11, `timeout` -> 12, `refusal` -> 13, `model_mismatch` -> 14, and `other` or unknown string -> 1. If stdout has no usable "error" field (non-JSON output, empty error, or missing error key), it falls back to the process exit code when it is one of the contract codes (`{1, 2, 10, 11, 12, 13, 14}`), else 1. The generation loop's existing exit semantics are preserved: code 10 -> exit 3, code 11 -> exit 4, code 14 -> exit 5, code 2 -> exit 1, and 3 consecutive failures (12, 13, 1, parse errors) -> exit 6.
+(2) Process-group session termination: replaces `subprocess.run(timeout)` with `subprocess.Popen(..., start_new_session=True)` in its own session. On timeout (`timeout_s + 60`), `os.killpg` sends `SIGTERM` to the entire process group (`proc.pid`), waits up to 10 seconds (`proc.wait(timeout=10)`), and escalates to `SIGKILL` if any child process remains alive. This prevents leaked or orphaned browser/adapter child processes upon timeout.
+(3) Correction to [D-43](2) on headed execution: the adapter runs headed by default (`headless: false` in stdin payload). The operator can monitor browser execution and manually solve any interactive Cloudflare/turnstile challenges if needed.
+(4) Correction to [D-43](6) on generator model identity and bias: the generator is Sonnet-tier via the web UI with the label as observed (e.g. "Claude 3.5 Sonnet" or whatever label the web UI presents), not guaranteed immutable "Claude 3.5 Sonnet". Furthermore, using a different model family from the experimental decision step (DeepSeek Flash, [D-29]) reduces but does not eliminate shared-vocabulary bias, as both model families share internet pretraining corpora and standard computer-science curriculum terminology.
+Reasoning: hardens adapter error handling against string code mismatches and orphan processes, aligns contract doc and test stubs with exact specification, and documents precise browser and provenance realities. Affects: `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/context/prompt-adapter-contract.md`, `tests/test_generate_name_pool.py`, `docs/tasks/status.md`, FIX-011.
```

### 5.2 `git diff docs/tasks/status.md`
```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index ece2b7a..e57ad04 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -83,3 +83,4 @@ Status: **not started** (blocked on Phase 3)
 | FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
 | FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07; follow-up FIX-010. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
 | FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **needs-review** | Completed by Gemini. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
+| FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **needs-review** | Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
```

### 5.3 `git diff docs/context/prompt-adapter-contract.md`
```diff
diff --git i/docs/context/prompt-adapter-contract.md w/docs/context/prompt-adapter-contract.md
index a275a88..f6c23d1 100644
--- i/docs/context/prompt-adapter-contract.md
+++ w/docs/context/prompt-adapter-contract.md
@@ -53,7 +53,7 @@ Exactly one JSON object. Diagnostic logs are emitted to `stderr` only.
 ```json
 {
   "ok": false,
-  "error": CODE,
+  "error": str,
   "message": str,
   "reset_time": str | null
 }
@@ -61,9 +61,9 @@ Exactly one JSON object. Diagnostic logs are emitted to `stderr` only.
 
 ### Exit and Error Codes
 
-| Code | Name | Meaning |
+| Exit Code | Error String (`error`) | Meaning |
 | :--- | :--- | :--- |
-| `0` | `ok` | Successful execution |
+| `0` | (none / `ok`) | Successful execution |
 | `1` | `other` | Unclassified error / internal adapter failure |
 | `2` | `bad_request` | Invalid stdin JSON or missing required parameter |
 | `10` | `rate_limit` | Rate limit or usage quota reached on claude.ai |
@@ -114,78 +114,78 @@ Exactly one JSON object. Diagnostic logs are emitted to `stderr` only.
 }
 ```
 
-#### Failure: Rate Limit (Error Code 10, Exit Code 3 in caller)
+#### Failure: Rate Limit (Exit Code 10, Exit Code 3 in caller)
 
 ```json
 {
   "ok": false,
-  "error": 10,
+  "error": "rate_limit",
   "message": "You have reached your usage limit for Claude 3.5 Sonnet.",
   "reset_time": "2026-10-07T23:00:00Z"
 }
 ```
 
-#### Failure: Login Required (Error Code 11, Exit Code 4 in caller)
+#### Failure: Login Required (Exit Code 11, Exit Code 4 in caller)
 
 ```json
 {
   "ok": false,
-  "error": 11,
+  "error": "login_required",
   "message": "Login session expired or Cloudflare turnstile challenge presented.",
   "reset_time": null
 }
 ```
 
-#### Failure: Model Mismatch (Error Code 14, Exit Code 5 in caller)
+#### Failure: Model Mismatch (Exit Code 14, Exit Code 5 in caller)
 
 ```json
 {
   "ok": false,
-  "error": 14,
+  "error": "model_mismatch",
   "message": "Model mismatch: requested 'sonnet' but observed 'Claude 3 Haiku' in UI.",
   "reset_time": null
 }
 ```
 
-#### Failure: Timeout (Error Code 12, Exit Code 6 in caller if 3 consecutive)
+#### Failure: Timeout (Exit Code 12, Exit Code 6 in caller if 3 consecutive)
 
 ```json
 {
   "ok": false,
-  "error": 12,
+  "error": "timeout",
   "message": "Response generation timed out after 300 seconds.",
   "reset_time": null
 }
 ```
 
-#### Failure: Refusal (Error Code 13, Exit Code 6 in caller if 3 consecutive)
+#### Failure: Refusal (Exit Code 13, Exit Code 6 in caller if 3 consecutive)
 
 ```json
 {
   "ok": false,
-  "error": 13,
+  "error": "refusal",
   "message": "Model refused to answer the prompt.",
   "reset_time": null
 }
 ```
 
-#### Failure: Bad Request (Error Code 2, Exit Code 1 in caller)
+#### Failure: Bad Request (Exit Code 2, Exit Code 1 in caller)
 
 ```json
 {
   "ok": false,
-  "error": 2,
+  "error": "bad_request",
   "message": "Missing required field 'prompt' in stdin JSON.",
   "reset_time": null
 }
 ```
 
-#### Failure: Other (Error Code 1, Exit Code 6 in caller if 3 consecutive)
+#### Failure: Other (Exit Code 1, Exit Code 6 in caller if 3 consecutive)
 
 ```json
 {
   "ok": false,
-  "error": 1,
+  "error": "other",
   "message": "Browser process crashed unexpectedly.",
   "reset_time": null
 }
```
