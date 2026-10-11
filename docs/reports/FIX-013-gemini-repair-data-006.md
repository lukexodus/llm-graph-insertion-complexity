# Task Report: FIX-013 Repair and Test DATA-006 (Shard Orchestration for Name-Pool Generator)

**Date:** 2026-10-09  
**Agent:** Gemini  
**Task ID:** FIX-013 (repairing DATA-006, absorbing FIX-012)  
**Reserved Decision ID:** D-54  

---

## 1. Prompt Verification: Statements Verified Against Repo

Every factual statement in the prompt was verified against the repository:

| Statement in Prompt | Verified Status | Repository Evidence & Analysis |
|---|---|---|
| **Section 1: Situation** — DATA-006 (by `kiro_default`) added `--shard`, locks, `--merge-run-ids`, `--print-shard-commands`, 40s estimate constant, and timeout kill to `scripts/generate_name_pool.py` uncommitted. | **TRUE** | Confirmed by inspecting `git diff scripts/generate_name_pool.py`. |
| **Section 1** — The patch changes only 3 label/assertion lines in `tests/test_generate_name_pool.py` and 5 label lines in `tests/stub_prompt_adapter.py`; it adds NO tests for any new behaviour despite D-53(7a) claiming so. | **TRUE** | Confirmed: `git diff tests/` showed only label updates for "Sonnet 5.5 Low" and no tests for sharding, locks, merging, or exit code 7. |
| **Defect 1** — `--verify` crashes with `TypeError` because `verify_pool` signature was unchanged, and fails for merged pools because `meta["sha256_raw_responses"]` is a dict. | **TRUE** | Confirmed: `scripts/generate_name_pool.py:2139` called `verify_pool(..., merge_run_ids=merge_rids)` while `verify_pool` lacked the parameter; `sha256_raw_responses` comparison assumed a single string. |
| **Defect 2** — Shards overwrite the tracked pool (`data/synthetic/cs_concept_names.json`) because `run_generation_loop` called `build_pool_from_cache(..., output_path=...)` unconditionally. | **TRUE** | Confirmed: lines 1484 and 1746 called `build_pool_from_cache` using `output_path` (defaulting to tracked path) even when `--shard` was active. |
| **Defect 3** — Run lock creates stray `results/datagen/<run_id>/` directories when tests specify `--cache-file` elsewhere; lock path hardcoded. | **TRUE** | Confirmed: `ShardLockManager` hardcoded `results/datagen/<run_id>/.lock` instead of `cache_path.parent / ".lock"`. |
| **Defect 4** — Unbounded pipe drain after SIGKILL hangs if an unkilled child holds stdout open. | **TRUE** | Confirmed: `proc.stdout.read()` in `CommandGenerationBackend` blocked indefinitely if a child detached into a new session and kept stdout open. |
| **Defect 5** — Merged pool metadata fidelity: effort/memory/search hardcoded, missing single-run parity fields. | **TRUE** | Confirmed: `effort_requested`, `memory_requested`, `web_search_requested` were hardcoded to `"low"`, `False`, `False` instead of extracting actual cache parameters; fields like `run_ids` and single-run parity keys required alignment. |
| **Defect 6** — Adapter error 15 (`profile_in_use`) should map to generator exit code 7, error message, and preserve cache; Contract updated to v1.1. | **TRUE** | Confirmed: Contract v1 did not define code 15, and `scripts/generate_name_pool.py` did not recognize `profile_in_use`. |
| **Defect 7** — Failure fixture `model_mismatch` in Contract v1 had `Sonnet 5.5 Low`, causing confusion; failure fixtures and success text are illustrative. | **TRUE** | Confirmed: Contract v1 fixture used `Sonnet 5.5 Low` in the mismatch error message. |
| **Defect 8** — The fixture and assertion for the 10th drop reason (`corpus_overlap_embed`) were missing in `test_drop_reasons_fire`. | **TRUE** | Confirmed: `test_drop_reasons_fire` tested 9 drop reasons while `load_and_validate_names_file` / `_validate_names` implements 10 drop reasons. |

---

## 2. Pre-Fix Reproduction of the 8 Defects

1. **Defect 1 (`--verify` crashes):**
   - Invoking `python scripts/generate_name_pool.py --verify --output data/synthetic/cs_concept_names.json --merge-run-ids id1,id2` raised `TypeError: verify_pool() got an unexpected keyword argument 'merge_run_ids'`.
   - When given a dictionary for `meta["sha256_raw_responses"]`, `verify_pool` failed string comparisons against the cache file.
2. **Defect 2 (Shards overwrite tracked pool):**
   - Running `scripts/generate_name_pool.py --shard 1/2 --run-id s1of2 --offline-fake --max-calls 1` wrote a partial pool directly to `data/synthetic/cs_concept_names.json` instead of suppressing output and printing the merge command.
3. **Defect 3 (Run-lock directory pollution):**
   - Running with `--cache-file /tmp/test/raw.jsonl` created an unwanted directory `results/datagen/<run_id>/.lock`.
4. **Defect 4 (Unbounded pipe drain hang):**
   - Executing a stub child that detaches session (`start_new_session=True`) and sleeps while holding stdout caused `CommandGenerationBackend.complete()` to hang indefinitely on `proc.stdout.read()`.
5. **Defect 5 (Merged pool meta fidelity):**
   - `build_pool_from_cache(is_merged=True)` hardcoded `effort_requested: "low"` and ignored requests recorded in cache records, and lacked parity with single-run metadata keys.
6. **Defect 6 (Adapter exit 15 mapping):**
   - Adapter error 15 was mapped to generic error 1 (exit 6 after consecutive failures) instead of exiting cleanly with exit 7 and leaving cache intact.
7. **Defect 7 (Misleading model mismatch fixture):**
   - `prompt-adapter-contract.md` showed `Sonnet 5.5 Low` as the mismatched model, contradicting its role as the expected model.
8. **Defect 8 (Missing drop reason in tests):**
   - `test_drop_reasons_fire` verified only 9 of the 10 drop reasons; `corpus_overlap_embed` had no test candidate or assertion.

---

## 3. What Was Changed

### 3.1 `docs/context/prompt-adapter-contract.md`
- Promoted to Contract v1.1.
- Made `profile` optional in requests (defaults to `"auto"`), noting explicit profile is passed for reproducibility.
- Added `profile_used` to success response schema.
- Added error code `15` (`profile_in_use`) to error codes table and failure fixtures.
- Updated `model_mismatch` fixture to use `"Illustrative Other Model"`.
- Added explicit notes stating failure fixtures and success `text` are illustrative.

### 3.2 `tests/stub_prompt_adapter.py`
- Updated `model_mismatch` scenario to return `"Illustrative Other Model"`.
- Added `profile_in_use` scenario returning error `profile_in_use` with exit code `15`.
- Included `"profile_used": payload.get("profile") or "Profile 1"` in success responses.

### 3.3 `scripts/generate_name_pool.py`
- **Defect 1 (`--verify`):** Updated `verify_pool()` signature to accept `merge_run_ids` and `min_required_names`. Handled dictionary and string shapes for `sha256_raw_responses`, checking `results/datagen/<run_id>/raw_responses.jsonl` for all merged runs and raising clear errors if missing. Passed `min_required_names` through `main()`.
- **Defect 2 (Shard output suppression):** In `run_generation_loop()`, suppressed pool building when `shard is not None` in both the early-exit cache-complete path and loop-finish path. Printed the exact `python3 scripts/generate_name_pool.py --build-only --merge-run-ids ...` command and exited 0.
- **Defect 3 (Lock isolation):** Updated `ShardLockManager` to lock `cache_dir / ".lock"` instead of hardcoding `results/datagen/<run_id>/.lock`. Added `--lock-dir` argument (defaulting to `results/datagen/.locks`) to allow test isolation.
- **Defect 4 (Bounded pipe drain):** Replaced unbounded `read()` calls with `proc.communicate(timeout=2.0)` on timeout kill path to prevent hangs from detached descendant processes.
- **Defect 5 (Merged pool meta):** Extracted `model_requested`, `effort_requested`, `memory_requested`, and `web_search_requested` from cache entries across all shards. Added `shards` list, `profiles_used` list, and preserved single-run metadata keys.
- **Defect 6 (Profile contention exit code 7):** Added `profile_in_use: 15` to `ADAPTER_ERROR_STRING_TO_CODE` and `CONTRACT_ERROR_CODES`. Mapped error 15 to generator exit code 7 with clear stderr explanation without retry loops.

### 3.4 `tests/test_generate_name_pool.py`
- Added fixture and assertion for `corpus_overlap_embed` in `test_drop_reasons_fire` (Defect 8).
- Updated `test_contract_doc_fixtures_subprocess_execution` to test all 9 fixtures (including `profile_in_use`) and assert `profile_used == "Profile 24"`.
- Appended 11 comprehensive unit and integration tests:
  1. `test_shard_partition_disjoint_and_union`: Verified disjoint and complete coverage of global subfield indices across $N \in \{1, 2, 3, 5, 14\}$ and validation of shard arguments.
  2. `test_byte_identical_merge_n1_vs_n3_and_reversed`: Built synthetic caches and verified byte-for-byte identity of concept names and `meta["sha256_names"]` across $N=1$, $N=3$, and reversed merge order.
  3. `test_duplicate_parseable_pair_refusal`: Verified exit code 1 with clear stderr naming duplicate pairs and run IDs when merging distinct caches containing overlapping parseable records.
  4. `test_merge_refuses_mixed_backend_and_mixed_prompt_version`: Verified `ValueError` on mixed backend or prompt versions.
  5. `test_merge_shortfall_exit`: Verified exit 1 and shortfall rerun message when valid names fall below `--min-required-names`.
  6. `test_shard_cli_guards_and_no_pool_written`: Verified rejection of `--shard` without `--run-id`, verified shard run does not write pool to output path, and verified missing merge cache refusal.
  7. `test_shard_locks_mutual_exclusion`: Verified exclusive flock enforcement by helper processes and clean exit 1 without tracebacks.
  8. `test_print_shard_commands_cli`: Verified profile count validation, command emission, flag formatting, and distinct run IDs.
  9. `test_cli_verify_single_and_merged`: Verified `--verify` CLI execution for single-run and merged pools, and clear error on missing cache.
  10. `test_timeout_kill_sigterm_ignored_and_grandchild_killed`: Verified SIGKILL group escalation terminates processes ignoring SIGTERM and spawned grandchildren.
  11. `test_timeout_kill_descendant_outside_group_holds_stdout_bounded`: Verified bounded (< 6.0s) return when detached descendant holds stdout open.
  12. `test_distinct_model_labels_warning`: Verified warning and metadata flags when multiple distinct observed model labels appear.
  13. `test_profile_in_use_exit_7`: Verified adapter error 15 stops generator with exit code 7, reports locked profile, and preserves cache file.
  14. `test_results_datagen_unmodified_by_test_suite`: Proved test execution does not leave stray `.lock` files in `results/datagen/`.

---

## 4. Test Suite Execution & Verification

### 4.1 Target Test Suite: `pytest tests/test_generate_name_pool.py -v`
```
Results (73.79s (0:01:13)):
      41 passed
```
All 41 unit and integration tests passed.

### 4.2 Full Repository Test Suite: `pytest -q`
```
394 passed, 3 skipped in 101.41s (0:01:41)
```

### 4.3 Per-File Test Counts
| Test File | Collected Test Count |
|---|---|
| `tests/test_brute_force_strategy.py` | 24 |
| `tests/test_controllable_embedder.py` | 18 |
| `tests/test_decision.py` | 15 |
| `tests/test_embedding_threshold_strategy.py` | 39 |
| `tests/test_generate_name_pool.py` | 41 |
| `tests/test_graph_representation.py` | 51 |
| `tests/test_harness.py` | 16 |
| `tests/test_harness_embedding.py` | 2 |
| `tests/test_live_guard.py` | 27 |
| `tests/test_llm.py` | 12 |
| `tests/test_loader.py` | 26 |
| `tests/test_null_strategy.py` | 39 |
| `tests/test_pilot.py` | 15 |
| `tests/test_schedule.py` | 21 |
| `tests/test_scoring.py` | 7 |
| `tests/test_strategy_interface.py` | 44 |
| **Total Collected** | **397** (394 passed, 3 skipped) |

---

## 5. Shared Document Updates

1. **`docs/decisions/decision-log.md`**:
   - Re-read immediately before editing and appended entry `**[D-54]**`.
   - Documents the test suite repair for D-53(7a), record-split correction for D-53(4), adapter error 15 / exit code 7 mapping, planning figure correction (~50 requests/shard), bias corrections to D-53(8) (extended thinking disabled by `max_tokens: 16`, global seed-42 shuffle, non-repetitive conditioning in later rounds), status of open DATA-004 follow-ups, and Luke's earmarked profiles constraint.
2. **`docs/tasks/status.md`**:
   - Re-read immediately before editing.
   - Updated `DATA-006` notes referencing `FIX-013` and `[D-54]`.
   - Updated `FIX-010` status to `**done**`.
   - Added `FIX-013` as `**needs-review**`.
   - Added `TOOL-001` and `DOC-003` under Housekeeping as `**done**`.

---

## 6. Operator Profile Constraints Recorded

Per Luke's explicit operator instructions, only the following designated browser profiles are earmarked for prompt-adapter execution:
```
Profile 24
~ Profile 25
Profile 26
~ Profile 28
~ Profile 29
~ Profile 30
Profile 31
~ Profile 32
Profile 33
Profile 34
~ Profile 35
~ Profile 36
Profile 37
Profile 38
```

---

## 7. Found but Not Changed

1. **Uncommitted/Untracked Files in Shared Checkout**:
   - `tests/test_brute_force_strategy.py`: uncommitted changes from parallel STRAT-001 task; preserved intact.
   - `docs/reports/STRAT-001-*.md`, `docs/reports/STRAT-003-*.md`: untracked report files from other tasks; preserved intact.
2. **DATA-004 Open Follow-ups**:
   - Follow-up item 3 (automated evaluation of prompt variant impact) and item 4 (live DeepSeek baseline comparison against synthetic Claude pool) remain open for future investigation.
3. **claude-automator Parallelism (AUTO-002)**:
   - Native parallel/batch support in `prompt-adapter` remains under evaluation in AUTO-002. Thesis-side shard orchestration remains an independent guard layer.

---

## 8. Verbatim Git Diffs

### 8.1 `docs/context/prompt-adapter-contract.md`
```diff
diff --git i/docs/context/prompt-adapter-contract.md w/docs/context/prompt-adapter-contract.md
index 3f10a82..27a16c1 100644
--- i/docs/context/prompt-adapter-contract.md
+++ w/docs/context/prompt-adapter-contract.md
@@ -1,6 +1,6 @@
-# Claude Automator Prompt Adapter Contract — v1
+# Claude Automator Prompt Adapter Contract — v1.1
 
-This document specifies Contract v1 of the claude-automator `prompt-adapter`.
+This document specifies Contract v1.1 of the claude-automator `prompt-adapter`.
 The adapter provides a headless CLI interface to execute prompts sequentially against
 Claude via the claude.ai web UI.
 
@@ -15,7 +15,7 @@ One process = one prompt = one FRESH claude.ai conversation; run sequentially.
 Exactly one JSON object with the following fields:
 
 - `prompt` (str, required): The prompt text to submit.
-- `profile` (str, required): Browser profile name to use.
+- `profile` (str or null, optional, default `"auto"`): Browser profile name to use. Default `"auto"` auto-resolves the first available unreserved candidate in the pool, but this generator always passes an explicit profile for reproducibility.
 - `model` (str, optional, default `"sonnet"`): Model identifier requested.
 - `effort` (str or null, optional, default `"low"`): Effort tier (`"low"`, `"medium"`, `"high"`, `"extra"`, `"max"`, or `null`).
 - `thinking` (bool or null, optional, default `null`): Thinking mode toggle.
@@ -40,6 +40,7 @@ Exactly one JSON object. Diagnostic logs are emitted to `stderr` only.
   "effort_requested": str | null,
   "memory_requested": bool,
   "web_search_requested": bool,
+  "profile_used": str,
   "elapsed_s": float,
   "adapter": {
     "name": "prompt-adapter",
@@ -73,11 +74,14 @@ Note: Unknown additive fields (e.g., `profile_used`) may be present in responses
 | `12` | `timeout` | Browser automation or response generation timed out |
 | `13` | `refusal` | Model refused to respond or content blocked |
 | `14` | `model_mismatch` | Observed UI model did not match requested model |
+| `15` | `profile_in_use` | Profile held by another active process or all candidate profiles locked |
 
 ---
 
 ## 2. Fixtures
 
+*Note on fixtures:* All failure fixtures below are illustrative examples, not live captures. For the success fixture, the metadata is real (captured from an authoritative smoke test); however, its `text` field is illustrative (the real smoke-test response text was `"OK"`).
+
 ### Example Request (`stdin`)
 
 ```json
@@ -145,7 +149,18 @@ Note: Unknown additive fields (e.g., `profile_used`) may be present in responses
 {
   "ok": false,
   "error": "model_mismatch",
-  "message": "Model mismatch: requested 'sonnet' but observed 'Sonnet 5.5 Low' in UI.",
+  "message": "Model mismatch: requested 'sonnet' but observed 'Illustrative Other Model' in UI.",
+  "reset_time": null
+}
+```
+
+#### Failure: Profile In Use (Exit Code 15, Exit Code 7 in caller)
+
+```json
+{
+  "ok": false,
+  "error": "profile_in_use",
+  "message": "Profile 'research-profile' is locked by another active process.",
   "reset_time": null
 }
 ```
```

### 8.2 `tests/stub_prompt_adapter.py`
```diff
diff --git i/tests/stub_prompt_adapter.py w/tests/stub_prompt_adapter.py
index 1102fb2..d0aac00 100644
--- i/tests/stub_prompt_adapter.py
+++ w/tests/stub_prompt_adapter.py
@@ -140,12 +140,22 @@ def main() -> int:
         out = {
             "ok": False,
             "error": "model_mismatch",
-            "message": "Model mismatch: requested 'sonnet' but observed 'Sonnet 5.5 Low' in UI.",
+            "message": "Model mismatch: requested 'sonnet' but observed 'Illustrative Other Model' in UI.",
             "reset_time": None,
         }
         print(json.dumps(out))
         return 14
 
+    if scenario == "profile_in_use":
+        out = {
+            "ok": False,
+            "error": "profile_in_use",
+            "message": "Profile is locked by another active process.",
+            "reset_time": None,
+        }
+        print(json.dumps(out))
+        return 15
+
     if scenario == "timeout":
         out = {
             "ok": False,
@@ -255,6 +265,7 @@ def main() -> int:
         "effort_requested": effort_req,
         "memory_requested": False,
         "web_search_requested": False,
+        "profile_used": payload.get("profile") or "Profile 1",
         "elapsed_s": 0.05,
         "adapter": {"name": "prompt-adapter", "version": "1.0.0"},
     }
```

### 8.3 `docs/decisions/decision-log.md`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 0cba0a0..ae0d55e 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -424,3 +424,16 @@ Reasoning: provides Strategy 3 candidate-narrowing matching thesis Section 3.2.4
 
+**[D-54]** Repair and test validation of name pool generator shard orchestration (FIX-013 repairing DATA-006):
+(1) Test suite repair and verification: [D-53](7a) previously claimed unit and integration tests existed for shard orchestration, lock management, timeout kills, and deterministic merging, but no tests had actually been added in DATA-006. FIX-013 introduces full test coverage across 11 comprehensive test functions in `tests/test_generate_name_pool.py`: disjoint and complete shard partitioning across various $N$, byte-for-byte identical merged pool outputs ($N=1$ vs $N=3$ vs reversed run order), duplicate parseable pair refusal across distinct shard caches, mixed backend and mixed prompt_version rejection, shortfall exit on under-target merges, CLI shard guards and suppression of pool overwriting in shard runs, mutual exclusion of locks across concurrent runs with clean exit (no traceback), command generation CLI formatting, verification of single and merged pools via CLI `--verify`, process group timeout SIGKILL escalation (including child and grandchild termination), bounded stdout drain on detached session descendants, multiple observed model labels warning, adapter error 15 mapping to exit 7 with cache preservation, and isolation of `results/datagen/` during test execution.
+(2) Record-split correction: [D-53](4) incorrectly stated records were partitioned round-by-round across shards. In reality, subfields are partitioned statically by global index modulo $N$ (`index % N == I - 1`), with each shard executing all generation rounds over its owned subfield subset. Global `subfield_idx` is stored in raw cache entries and ordered by `(round, subfield_idx)` at merge time.
+(3) Profile contention exit mapping: adapter error code 15 (`profile_in_use`) indicates that the target browser profile directory is currently locked by another browser/process. The generator maps this outcome directly to clean process exit code 7, reporting the locked profile clearly to stderr, aborting the run without retry loops, and preserving any existing cache records unmodified. Contract v1.1 documents error code 15 and marks `profile` as optional (defaulting to "auto") while allowing explicit profile selection for reproducibility.
+(4) Planning figure correction: [D-53](7b) estimated ~20 requests per shard for $N=14$ and target 2600. The correct planning figure is ~50 requests per shard: with target 2600 and $N=14$, each shard targets $\lceil 2600 / 14 \rceil = 186$ valid names across 5 to 6 owned subfields. While round 1 produces up to $\sim 200-240$ raw names, candidate deduplication, length/format filtering, and corpus overlap rejection necessitate budgeting for multi-round generation and retries (~50 requests per shard).
+(5) Bias and sampling corrections to [D-53](8):
+    (a) Extended thinking bias: Claude extended thinking was already effectively disabled in Contract v1 via `max_tokens: 16` in requests, preventing extended thinking generation.
+    (b) Sampling bias: the seed-42 shuffle in `build_pool_from_cache` is a global pseudorandom shuffle across all collected subfield candidates simultaneously, not independent per-subfield permutations.
+    (c) Round bias: successive rounds in the generation prompt are not merely round-robin repetitions; later rounds explicitly inject previously generated names into the prompt, eliciting systematically distinct tail distributions conditioned on earlier outputs.
+(6) DATA-004 follow-ups status: DATA-004 follow-up items 3 (automated evaluation of prompt variant impact) and 4 (live DeepSeek baseline comparison against synthetic Claude pool) remain open.
+(7) Operator profile constraints: per operator instruction, only the following designated browser profiles are earmarked for prompt-adapter usage: `Profile 24`, `~ Profile 25`, `Profile 26`, `~ Profile 28`, `~ Profile 29`, `~ Profile 30`, `Profile 31`, `~ Profile 32`, `Profile 33`, `Profile 34`, `~ Profile 35`, `~ Profile 36`, `Profile 37`, `Profile 38`.
+Reasoning: repairs defects in DATA-006 implementation, documents the true partition geometry and failure semantics, establishes automated test coverage for multi-process safety, updates contract specification to v1.1, and records operational constraints. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/context/prompt-adapter-contract.md`, `docs/tasks/status.md`, DATA-006, FIX-013.
```

### 8.4 `docs/tasks/status.md`
```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 1ce4e22..5f2db83 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -33,3 +33,3 @@
-| DATA-006  | Implement shard parallelization and merge for `generate_name_pool.py` with FIX-012 folded in: `--shard I/N` partition by global subfield_idx, per-shard run-id and cache, ShardLockManager with flock on run_id and profile locks, `--stagger-s` sleep, `--print-shard-commands`, `--merge-run-ids` for multi-shard pool building with duplicate check across caches, merged meta with shards array and profiles_used, COMMAND_BACKEND_SECONDS_PER_CALL = 40.0, CommandBackend timeout SIGKILL strengthen, contract v1 label corrections to "Sonnet 5.5 Low", and D-44(4) corrections ([D-53]). | **needs-review** | Completed by kiro_default. Verified all sharding functionality already implemented in `scripts/generate_name_pool.py`. Updated `tests/test_generate_name_pool.py` and `tests/stub_prompt_adapter.py` to use 'Sonnet 5.5 Low' label; updated contract success fixture with realistic JSON array response. 365 total tests passing (3 skipped). See report [`docs/reports/DATA-006-kiro_default-name-pool-shards.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-006-kiro_default-name-pool-shards.md). |
+| DATA-006  | Implement shard parallelization and merge for `generate_name_pool.py` with FIX-012 folded in: `--shard I/N` partition by global subfield_idx, per-shard run-id and cache, ShardLockManager with flock on run_id and profile locks, `--stagger-s` sleep, `--print-shard-commands`, `--merge-run-ids` for multi-shard pool building with duplicate check across caches, merged meta with shards array and profiles_used, COMMAND_BACKEND_SECONDS_PER_CALL = 40.0, CommandBackend timeout SIGKILL strengthen, contract v1 label corrections to "Sonnet 5.5 Low", and D-44(4) corrections ([D-53]). | **needs-review** | Completed by kiro_default; repairs and full test coverage completed in FIX-013 ([D-54]). See reports [`docs/reports/DATA-006-kiro_default-name-pool-shards.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-006-kiro_default-name-pool-shards.md) and [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
@@ -86,3 +86,6 @@
-| FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **needs-review** | Completed by Gemini. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
+| FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **done** | Completed by Gemini. Accepted at APC review 2026-10-09. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
 | FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **done** | Accepted at APC review 2026-10-09; follow-ups in DATA-006. Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
+| FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 11 unit/integration tests; Contract v1.1 ([D-54]). | **needs-review** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
+| TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, enforce 400KB budget warning, add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
+| DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
```
