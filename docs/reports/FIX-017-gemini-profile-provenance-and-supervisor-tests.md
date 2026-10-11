# FIX-017 Report: Multi-Profile Shard Provenance in Merged Pool Metadata and Supervisor Test-Coverage Follow-Ups

- **Task ID:** `FIX-017` (issued by APC-A as `FIX-016`; renumbered to `FIX-017` per operator instruction because `FIX-016` was already assigned to APC-B's dry-run planner task in commit `42890e9`)
- **Decision IDs:** `[D-56]` (APC-A Part A delta) and `[D-63]` (renumbered because `[D-61]` was assigned to `FIX-016` in commit `42890e9` and `[D-63]` was assigned to `STRAT-004-A` in commit `21d8e12`)
- **Agent:** `gemini`
- **Model Label:** `unknown` (tool does not expose a runtime model version string in the environment)
- **Date:** 2026-10-11
- **Branch:** `task/FIX-017` (rebased on `master`)
- **Worktree Path:** `/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017`

---

## 0. Verification of Prompt Statements Against the Repository

1. **Task ID and Decision ID Collisions (`FIX-016` / `D-61` -> `FIX-017` / `D-63`, `D-56` unused):**
   - APC-A computed the delta and prompt against bundle `apc-bundle-fix-20261011-2153` (commit `7b36f95`), before APC-B's `FIX-016` task (`[D-61]`) was committed at `42890e9`.
   - Verified `grep -o '\*\*\[D-56\]\*\*' docs/decisions/decision-log.md` returned nothing at `42890e9`.
   - Later, commit `21d8e12` on `master` assigned `[D-63]` to `STRAT-004-A`. Therefore, this task uses `FIX-017` and `[D-63]`, and applies APC-A's Part A (`[D-56]`) and Part B (`docs/tasks/status.md` updates for `DATA-006`, `DATA-007`, `FIX-013`, `FIX-014`, `FIX-015`).

2. **Background Claims on `scripts/generate_name_pool.py` (`build_pool_from_cache`, merged path):**
   - **Verified exact (including line numbers):** Prior to this change, `build_pool_from_cache()` in `scripts/generate_name_pool.py` (merged branch, starting at line `691`) iterated over `entries = list(cdict.values())` at lines `770–785`, captured only the first seen `profile_used` via `if prof is None and "profile_used" in bm: prof = str(bm["profile_used"])` (lines `773–774`), stored `shard_infos.append({..., "profile": prof, ...})` at line `791`, and computed `profiles_used = sorted({s["profile"] for s in shard_infos if s["profile"]})` at line `849` (attached to `meta["profiles_used"]` at line `893` and printed in dry-run/build output at line `919`). When a shard failed over mid-run from one profile to a spare, only the first profile appeared in `meta["shards"][i]["profile"]` and `meta["profiles_used"]`.

3. **Claims on `scripts/name_pool_supervisor.py` and `tests/test_name_pool_supervisor.py`:**
   - **`_launch_shard` line number and pass-through flags (Part 2c):** Verified `_launch_shard` is defined at line `803` of `scripts/name_pool_supervisor.py` and passes `adapter_model=args.adapter_model` (line `812`), `adapter_effort=args.adapter_effort` (line `813`), and `adapter_thinking=args.adapter_thinking` (line `814`) to `build_shard_cli_tokens(...)`.
   - **Subtlety in `build_shard_cli_tokens` default parameter (`adapter_effort="low"`):** At line `142` of `scripts/name_pool_supervisor.py`, `build_shard_cli_tokens` defines `adapter_effort: str = "low"` as its default argument (whereas `adapter_model: str = "sonnet"` and `adapter_thinking: str = "auto"`). Consequently, if a test only runs with `--adapter-effort low`, removing `adapter_effort=args.adapter_effort` from `_launch_shard` falls back to the function default `"low"` and would not fail! Including a second assertion case with `--adapter-effort medium` in `test_live_adapter_flags_passthrough` ensures that removing `adapter_effort=args.adapter_effort` from `_launch_shard` causes the test to fail without modifying `scripts/name_pool_supervisor.py`.
   - **`test_loader_value_error_stops_everything` vacuous guard (Part 2d):** Verified that in `tests/test_name_pool_supervisor.py` (lines `638–686` prior to our edit), `s1_cache` was pre-populated with conflicting records *before* `supervisor_main` was called. As a result, `load_completed_cache()` raised `ValueError` on the very first poll before the shard subprocess's stub adapter ever ran and wrote `child_pid_file`, and the assertion `if child_pid_file.exists():` at line `684` was always skipped.
   - **`--record-payload-file` in `tests/stub_prompt_adapter.py`:** Verified `tests/stub_prompt_adapter.py` (line `64`, lines `115–119`) already supports `--record-payload-file` and appends each raw stdin payload line to the file before parsing/responding. No modification to `tests/stub_prompt_adapter.py` was needed.

---

## 1. What Was Changed

1. **`scripts/generate_name_pool.py` (Part 1 — merged path of `build_pool_from_cache` only):**
   - **Choice of raw-line scanning:** We chose to scan all raw JSONL lines of each shard's cache file `p` (skipping blank lines, JSON decode errors, and non-dict JSON values identically to `load_completed_cache()`) rather than iterating only over `cdict.values()`. Reason: `load_completed_cache()` deduplicates by `(entry.round, entry.subfield)` keeping the last entry, so if an earlier call on profile A was later overwritten on the same `(round, subfield)` key by a retry on profile B, raw-line scanning still preserves `"A"` in `"profiles"`.
   - **Per-shard `"profiles"` key:** Added `"profiles": shard_profiles` to each `shard_infos[i]` dict (`meta["shards"][i]`), preserving first-appearance order of distinct non-empty `backend_meta.profile_used` strings across the shard's raw JSONL lines.
   - **Unchanged `"profile"` key:** Kept `meta["shards"][i]["profile"]` completely unchanged (first-seen profile string or `None`).
   - **Union for `meta["profiles_used"]`:** Updated `profiles_used` at line `870` to `sorted({prof_name for s in shard_infos for prof_name in s["profiles"] if prof_name})`.
   - **Metadata-only guarantee & scope:** Single-run (non-merged) pools and caches without `profile_used` are untouched. `"names"`, `meta["n_raw"]`, `meta["n_valid"]`, `meta["drop_counts"]`, and `meta["sha256_names"]` are byte-identical before and after.
   - **`scripts/name_pool_supervisor.py` was not modified.**

2. **`tests/test_generate_name_pool.py` (Part 2a):**
   - Added `test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256`: writes a two-shard cache set in `tmp_path` where shard 1 has records with `profile_used` `"A"` then `"B"` and shard 2 has `"C"`, builds the merged pool, and asserts `shards[0]["profiles"] == ["A", "B"]`, `shards[0]["profile"] == "A"`, `shards[1]["profiles"] == ["C"]`, `meta["profiles_used"] == ["A", "B", "C"]`, and byte-identical `names`, `sha256_names`, `n_raw`, `n_valid`, and `drop_counts` compared to building from the same caches with `profile_used` removed from every record (`shards[i]["profiles"] == []`, `meta["profiles_used"] == []`).
   - No existing test in `tests/test_generate_name_pool.py` or `tests/test_name_pool_supervisor.py` needed adaptation for the new `"profiles"` key.

3. **`tests/test_name_pool_supervisor.py` (Parts 2b, 2c, 2d):**
   - **Part 2b (`test_failover_on_rate_limit_to_spare_profile`):** Added assertions on the merged pool that shard 1 has `s1_meta["profile"] == "rate_limit_after_1_p1"` and `s1_meta["profiles"] == ["rate_limit_after_1_p1", "Spare_P3"]`, shard 2 has `s2_meta["profiles"] == ["Profile_2"]`, and `pool_data["meta"]["profiles_used"] == sorted(["rate_limit_after_1_p1", "Profile_2", "Spare_P3"])`.
   - **Part 2c (`test_live_adapter_flags_passthrough`):** Added live supervisor pass-through test running with `--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off` and `--record-payload-file` on the stub adapter, asserting every recorded stdin payload has `model == "sonnet-5"`, `effort == "low"`, `thinking is False` (JSON `false`, not `null`), every cache record has `backend_meta["thinking_requested"] is False`, and every `shard_launch` event in `supervisor-log.jsonl` contains `"--adapter-thinking off"` and `"--adapter-model sonnet-5"` in its `"command"` string; plus Case B with `--adapter-effort medium` so removing `adapter_effort` from `_launch_shard` is caught despite `build_shard_cli_tokens` defaulting `adapter_effort="low"`.
   - **Part 2d (`test_loader_value_error_stops_everything`):** Rewrote the test so a background thread polls for `child_pid_file.exists()` (with a 10 s deadline) before writing the conflicting mixed-backend cache records mid-run, removed the vacuous `if child_pid_file.exists():` guard, and asserted `rc == SUP_EXIT_ERROR`, `child_pid_file.exists()`, `not _pid_is_alive(cpid)`, and the `"loader_error"` event in `supervisor-log.jsonl`.

4. **`docs/decisions/decision-log.md` and `docs/tasks/status.md` (Part A, Part B, Part 3):**
   - Appended `[D-56]` (APC-A delta) and `[D-63]` (`FIX-017` decision entry) to `docs/decisions/decision-log.md`.
   - Updated `DATA-006`, `DATA-007`, `FIX-013`, `FIX-014`, and `FIX-015` to `**done**` in `docs/tasks/status.md` per APC-A Part B, and added row `FIX-017` as `**needs-review**`.

---

## 2. How I Know Each Test Can Fail (Mutation Evidence)

### 2a & 2b. Mutating `scripts/generate_name_pool.py`

Saved copy SHA256 before and after mutations:
`a89728656c11dc7949d8e0d3733748f3c2196db2859bdc6bd20ff530d07865b3  scripts/generate_name_pool.py`

**Mutation 1 (revert `scripts/generate_name_pool.py` to `HEAD`):**
```text
=== Mutation 1a: test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256 ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 48 items / 47 deselected / 1 selected

tests/test_generate_name_pool.py F                                       [100%]

=================================== FAILURES ===================================
__ test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256 __
tests/test_generate_name_pool.py:2720: in test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256
    assert shards[0]["profiles"] == ["A", "B"]
           ^^^^^^^^^^^^^^^^^^^^^
E   KeyError: 'profiles'
=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256
======================= 1 failed, 47 deselected in 0.49s =======================
=== Mutation 1b: test_failover_on_rate_limit_to_spare_profile ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_________________ test_failover_on_rate_limit_to_spare_profile _________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:215: in test_failover_on_rate_limit_to_spare_profile
    assert s1_meta["profiles"] == ["rate_limit_after_1_p1", "Spare_P3"]
           ^^^^^^^^^^^^^^^^^^^
E   KeyError: 'profiles'
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_failover_on_rate_limit_to_spare_profile
======================= 1 failed, 11 deselected in 4.11s =======================
```

**Mutation 2 (keep only the first profile in `shard_profiles`: `if prof_val and not shard_profiles:`):**
```text
=== Mutation 1c (first-profile-only in profiles): test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256 ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 48 items / 47 deselected / 1 selected

tests/test_generate_name_pool.py F                                       [100%]

=================================== FAILURES ===================================
__ test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256 __
tests/test_generate_name_pool.py:2720: in test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256
    assert shards[0]["profiles"] == ["A", "B"]
E   AssertionError: assert ['A'] == ['A', 'B']
E     
E     Right contains one more item: 'B'
E     Use -v to get more diff
=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256
======================= 1 failed, 47 deselected in 0.36s =======================
=== Mutation 1d (first-profile-only in profiles): test_failover_on_rate_limit_to_spare_profile ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_________________ test_failover_on_rate_limit_to_spare_profile _________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:215: in test_failover_on_rate_limit_to_spare_profile
    assert s1_meta["profiles"] == ["rate_limit_after_1_p1", "Spare_P3"]
E   AssertionError: assert ['rate_limit_after_1_p1'] == ['rate_limit_...', 'Spare_P3']
E     
E     Right contains one more item: 'Spare_P3'
E     Use -v to get more diff
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_failover_on_rate_limit_to_spare_profile
======================= 1 failed, 11 deselected in 5.73s =======================
a89728656c11dc7949d8e0d3733748f3c2196db2859bdc6bd20ff530d07865b3  scripts/generate_name_pool.py
```

### 2c. Mutating `_launch_shard` in `scripts/name_pool_supervisor.py` (lines 812–814)

Saved copy SHA256 before and after all mutations:
`440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91  scripts/name_pool_supervisor.py`

```text
440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91  scripts/name_pool_supervisor.py
=== Mutation 2c-1: remove adapter_model from _launch_shard ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_____________________ test_live_adapter_flags_passthrough ______________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:755: in test_live_adapter_flags_passthrough
    assert p["model"] == "sonnet-5"
E   AssertionError: assert 'sonnet' == 'sonnet-5'
E     
E     - sonnet-5
E     ?       --
E     + sonnet
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_live_adapter_flags_passthrough
======================= 1 failed, 11 deselected in 5.51s =======================
=== Mutation 2c-2: remove adapter_effort from _launch_shard ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_____________________ test_live_adapter_flags_passthrough ______________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:808: in test_live_adapter_flags_passthrough
    assert payloads_b[0]["effort"] == "medium"
E   AssertionError: assert 'low' == 'medium'
E     
E     - medium
E     + low
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_live_adapter_flags_passthrough
======================= 1 failed, 11 deselected in 9.32s =======================
=== Mutation 2c-3: remove adapter_thinking from _launch_shard ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_____________________ test_live_adapter_flags_passthrough ______________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:758: in test_live_adapter_flags_passthrough
    assert p["thinking"] is False
E   assert None is False
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_live_adapter_flags_passthrough
======================= 1 failed, 11 deselected in 3.45s =======================
=== Mutation 2c-4: remove all three (adapter_model, adapter_effort, adapter_thinking) from _launch_shard ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
_____________________ test_live_adapter_flags_passthrough ______________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:755: in test_live_adapter_flags_passthrough
    assert p["model"] == "sonnet-5"
E   AssertionError: assert 'sonnet' == 'sonnet-5'
E     
E     - sonnet-5
E     ?       --
E     + sonnet
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_live_adapter_flags_passthrough
======================= 1 failed, 11 deselected in 3.36s =======================
440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91  scripts/name_pool_supervisor.py
```

### 2d. Mutating `_terminate_all_children` in `scripts/name_pool_supervisor.py` (line 294) to a no-op

```text
440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91  scripts/name_pool_supervisor.py
=== Mutation 2d: _terminate_all_children made a no-op at its top ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 12 items / 11 deselected / 1 selected

tests/test_name_pool_supervisor.py F                                     [100%]

=================================== FAILURES ===================================
___________________ test_loader_value_error_stops_everything ___________________
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017/tests/test_name_pool_supervisor.py:707: in test_loader_value_error_stops_everything
    assert not _pid_is_alive(cpid)
E   assert not True
E    +  where True = _pid_is_alive(901237)
=========================== short test summary info ============================
FAILED tests/test_name_pool_supervisor.py::test_loader_value_error_stops_everything
======================= 1 failed, 11 deselected in 2.04s =======================
440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91  scripts/name_pool_supervisor.py
```

Confirmed `git diff scripts/name_pool_supervisor.py` is empty and `sha256sum scripts/name_pool_supervisor.py` matches `440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91`.

---

## 3. Found But Not Changed

- `scripts/name_pool_supervisor.py`: `build_shard_cli_tokens` (line `142`) has default parameters `adapter_model: str = "sonnet"`, `adapter_effort: str = "low"`, `adapter_thinking: str = "auto"`. Not modified per the hard rule (`Do NOT modify scripts/name_pool_supervisor.py`).
- `tests/stub_prompt_adapter.py`: Already supported `--record-payload-file` (line `64`, lines `115–119`), so no changes to the stub were required.

---

## 4. Test Suite Outputs and `results/datagen` Check

```text
$ pytest -q tests/test_name_pool_supervisor.py tests/test_generate_name_pool.py | tail -3
.........                                                                [100%]

======================== 60 passed in 131.58s (0:02:11) ========================
```

```text
$ pytest -q | tail -3
.....                                                                    [100%]

================== 583 passed, 3 skipped in 142.15s (0:02:22) ==================
```

- **`results/datagen` in the worktree after the full test run:** `results/datagen` is completely absent (`results/datagen does not exist`).

---

## 5. Verbatim `git diff` Output (Including Index Lines)

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 610e9e9..009a6d1 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -480,3 +480,20 @@
 (3) Consequence for planned budgets over the D-35 sweep matrix (`sweep_sizes = (50, 100, 200, 500, 1000, 2000)`, `sweep_trials_per_size = 10`, 60 total insertions): `BruteForceStrategy` plans 38,500 LLM calls; Strategy 2 (`EmbeddingThresholdStrategy`) remains uncapped at 38,500 calls (no `max_candidates`); Strategy 3 (`AnnRetrievalStrategy`) plans 600 calls at primary $k = 10$ (300 at $k = 5$, 1,200 at $k = 20$); Strategy 4 (`BoundedBucketStrategy`) plans 600 calls at primary $(s_{\min}, s_{\max}) = (5, 10)$ (300 at $(2, 5)$, 1,200 at $(10, 20)$); and `NullStrategy` plans 60 calls at $k = 1$ (300 at $k = 5$). Any earlier dry-run printouts saved for Strategies 3 and 4 (or `NullStrategy`) prior to this fix overstated the planned LLM call upper bound.
 (4) Tests added: `tests/test_dry_run_plan.py` adds offline unit tests covering the D-35 sweep matrix and small-size clamping across all strategies, accuracy-mode candidate bounds and per-corpus clamping, exact parity with `compute_planned_calls_upper_bound` in `scripts/run_experiment.py`, pre-`setup()` probe strategy invariance, `StubNarrowingStrategy(top_k=5)` compatibility, and the uncapped `n_existing` fallback for strategies without `max_candidates`. (Note: the FIX-016 prompt specified decision ID `D-60`, which was already assigned to DATA-007; `D-61` is used per operator instruction.)
 Reasoning: aligns the dry-run execution planner with the live pre-flight guard by delegating candidate upper-bound computation to `candidate_upper_bound(strategy, n_existing)` instead of inspecting a strategy-specific `"top_k"` config key. Affects: `src/graph_insertion/harness.py`, `tests/test_dry_run_plan.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/FIX-016-gemini-dry-run-planner.md`, INFRA-004, INFRA-005, FIX-009, FIX-016, STRAT-003, STRAT-004.
+
+**[D-56]** Name-pool generation model and thinking settings, DATA-007 acceptance with follow-ups, and corrections to [D-57] and [D-60] (APC-A):
+(1) Generator model for the np1w pool: Claude Sonnet 5 through the claude.ai web UI (adapter id `sonnet-5`), effort `low`, thinking requested OFF on every call (`--adapter-thinking off`). This replaces the "Sonnet 5.5 Low" plan of [D-53](8) and the contract fixture label for the generation run. Reason: thinking is a nuisance variable for a task of 40 snake_case names per call, and the engine can set and report the toggle. Bare `sonnet` selects Sonnet 5.5 (agent-reported reading of claude-automator), so `--adapter-model sonnet-5` must be passed explicitly; the supervisor's own default is `sonnet`.
+(2) Evidence: smoke calls on 2026-10-11 (19:15-19:17 on Profile 24; 21:06-21:10 on Profiles 24, 25, 26, 28, 29, 30) with `{"model":"sonnet-5","effort":"low","thinking":false}` reported `model_observed` "Sonnet 5 Low" on every call. The engine log shows Profile 24 toggled Thinking True -> False (state after toggle False) and Profiles 25, 26, 28, 29, 30 already False. These are engine log lines plus the label. The generator discards the adapter's stderr on success, so the per-call observed thinking state is not recorded, and the model label does not distinguish thinking states. The 21:07 smoke call on Profile 26 returned text other than the requested "OK" (tier 1 instead of 2); Profile 26 is excluded from the generation run until it is re-smoked.
+(3) Effort must not be sent as null: agent-reported (Gemini, reading claude-automator `claude_ui.py:58`): null passes validation but raises AttributeError. Not checked by the APC.
+(4) Correction to [D-57](1): the adapter's stdout echoes `thinking_requested` as of claude-automator commit 072e709 (committed 2026-10-11 19:44:50 +08:00; `apps/prompt-adapter/src/prompt_adapter/runner.py:545` per RECON-parallel-2 section 5, agent: Antigravity). The 16:04 smoke JSON predates it. The generator's `setdefault` fallback is harmless. [D-57] is not edited.
+(5) Corrections to [D-60](1) ([D-60] is not edited): the profile lock is `/tmp/claude_profile_locks/<sanitized>.lock` (RECON-parallel Q2b; RECON-parallel-2 section 1), not `~/.config/claude-automator/locks/<slug>.lock`; the auto-resolution function is `resolve_profile_for_prompt_adapter` (`runner.py:179-224`), not `resolve_candidate_profiles`; syllabot's worker pool is `apps/syllabot/src/syllabot/orchestrate.py`, not `runner.py`; the figures "560-970 MB RSS per Chromium" and "N = 2-3 fit comfortably in 15 GiB" appear in neither RECON-parallel.md nor RECON-parallel-2.md and are unverified. The conclusion that concurrency and failover belong in a thesis-side supervisor still stands on RECON-parallel Q1-Q3 (the adapter runs one prompt on one profile and never rotates).
+(6) Facts from RECON-parallel-2 (agent: Antigravity; not independently verified by the APC) relevant to the supervisor: `accounts.yaml` at the workspace root is the account catalog and is shared by prompt-adapter and `claude-accounts`; prompt-adapter does not record a cooldown and its exit-10 payload carries no `profile_used`; an explicit profile with a recorded cooldown is run, not refused; profile resolution and locking are not atomic; the adapter's `-dirty` version suffix counts untracked files (`runner.py:365-374`). The supervisor's own cooldown table is in memory and is not reloaded when the supervisor is restarted.
+(7) DATA-007 (committed 7b36f95) is accepted at APC review with follow-ups. Findings from the patch, from running the 11 tests in a shimmed sandbox (not the repo), and from three mutations: (a) no test checks that `--adapter-model`, `--adapter-effort` and `--adapter-thinking` reach a live shard process (a mutation removing them from `_launch_shard`, `scripts/name_pool_supervisor.py:803`, leaves all 11 tests passing; only the dry-run test checks the flags); (b) the child-death assertion in `test_loader_value_error_stops_everything` never executes (the child pid file does not exist at the assertion; the test also passes with `_terminate_all_children` disabled), while `test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches` and `test_sigterm_propagation_kills_children_and_exits_130` do fail when descendant discovery is removed; (c) merged-pool provenance keeps only the first `profile_used` per shard (`scripts/generate_name_pool.py:773-774`, `791`, `849`), so after a mid-shard failover `meta.shards[i].profile` and `meta.profiles_used` are incomplete although each cache line records its own `profile_used` and `supervisor-log.jsonl` records the rotation. Follow-up task FIX-016. Generation may start before FIX-016 because the pool is rebuilt offline from the caches (`--build-only --merge-run-ids`); a meta-only fix must leave `names` and `meta.sha256_names` unchanged, which the FIX-016 review will check.
+(8) Process notes: [D-54] was committed in 63cddfb before APC acceptance and rewritten in place in 8429122. Luke commits each task before APC acceptance (DATA-006, FIX-013, FIX-014, FIX-015, DATA-007), so review happens on committed code and corrections are made by follow-up entries. Decision-ID collisions in FIX-015 (prompt D-55, used D-57) and DATA-007 (prompt D-58, used D-60) were resolved by Luke choosing the next free number; D-56 was reserved for this entry and is appended after D-60.
+Reasoning: records the model and thinking decision with its evidence limits, corrects two committed entries without editing them, and gives DATA-007 an explicit acceptance with the defects found. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`, DATA-004, DATA-006, DATA-007, FIX-015, FIX-016.
+
+**[D-63]** Per-shard multi-profile provenance in merged pool metadata and supervisor test-coverage follow-ups (FIX-017):
+(1) Per-shard `"profiles"` list and `"profiles_used"` union in merged pools: In `build_pool_from_cache()` (`scripts/generate_name_pool.py`, merged path only), each `meta["shards"][i]` dictionary now includes `"profiles"`: the ordered list (in first-appearance order) of every distinct `backend_meta.profile_used` string across all raw JSONL lines of that shard's `raw_responses.jsonl`. Raw-line scanning was chosen over scanning only the de-duplicated `(round, subfield)` entries returned by `load_completed_cache()` because a call that was later overwritten by a retry on the same `(round, subfield)` key still executed on that profile; undecodable or non-dict lines are skipped identically to `load_completed_cache()`. The existing scalar `meta["shards"][i]["profile"]` key is kept unchanged (first-seen profile string or `None`) for backward compatibility, and `meta["profiles_used"]` is computed as the sorted union of all shards' `"profiles"` lists (`sorted({prof_name for s in shard_infos for prof_name in s.get("profiles", [])})`). This resolves [D-60](6) and [D-56](7)(c). Single-run (non-merged) pools and caches without `profile_used` are unchanged.
+(2) Metadata-only guarantee: The change touches only `meta["shards"][i]["profiles"]` and `meta["profiles_used"]` in the merged branch of `build_pool_from_cache()`. For any cache set, `"names"`, `meta["n_raw"]`, `meta["n_valid"]`, `meta["drop_counts"]`, and `meta["sha256_names"]` are byte-identical to those produced when `profile_used` is absent or before this change. `scripts/name_pool_supervisor.py` was not modified.
+(3) Tests added and repaired: (a) `test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256` in `tests/test_generate_name_pool.py` verifies `shards[0]["profiles"] == ["A", "B"]`, `shards[0]["profile"] == "A"`, `shards[1]["profiles"] == ["C"]`, `meta["profiles_used"] == ["A", "B", "C"]`, and byte-identical `names`, `n_raw`, `n_valid`, `drop_counts`, and `sha256_names` against the same caches with `profile_used` removed from every record; (b) `test_failover_on_rate_limit_to_spare_profile` in `tests/test_name_pool_supervisor.py` adds assertions that shard 1's merged metadata has `"profiles" == ["rate_limit_after_1_p1", "Spare_P3"]` and `meta["profiles_used"] == ["Profile_2", "Spare_P3", "rate_limit_after_1_p1"]`; (c) `test_live_adapter_flags_passthrough` in `tests/test_name_pool_supervisor.py` verifies live supervisor pass-through of `--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off` (and `--adapter-effort medium` so `build_shard_cli_tokens`'s default `adapter_effort="low"` cannot mask removing `adapter_effort` from `_launch_shard`) across recorded stdin payloads, cache `backend_meta["thinking_requested"]`, and `supervisor-log.jsonl` `shard_launch` commands, resolving [D-56](7)(a); (d) `test_loader_value_error_stops_everything` in `tests/test_name_pool_supervisor.py` now injects the conflicting cache record mid-run only after polling for `child_pid_file.exists()`, removes the vacuous `if child_pid_file.exists():` guard, and asserts the child is dead, resolving [D-56](7)(b). (Note: the APC-A prompt specified task ID `FIX-016` and decision ID `D-61`, which were already used by APC-B's dry-run planner fix; `FIX-017` and `D-63` are used per operator instruction.)
+Reasoning: makes merged pool provenance self-contained after mid-shard profile failover without affecting pool names or hashes, and closes the live flag pass-through and child-termination test gaps in `tests/test_name_pool_supervisor.py`. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/test_name_pool_supervisor.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/FIX-017-gemini-profile-provenance-and-supervisor-tests.md`, DATA-006, DATA-007, FIX-017.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 4349689..a3f4c7c 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -30,8 +30,8 @@ Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-1
 | DATA-003  | Decide where build-phase source text comes from now that `concept_descriptions/` is ruled out for DSA/Metacademy (D-17).                                                                                                                                                                                                                                                                                                                                     | **done** | Decided by Luke 2026-10-03: names only, no node text ([D-21]). Evidence in [`docs/reports/DATA-003-gemini-source-text-evidence.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-003-gemini-source-text-evidence.md). |
 | DATA-004  | Generate the synthetic large-n concept-name sets (sweep sizes 50, 100, 200, 500, 1000, 2000 x 10 trials; CS domain, graph-level domain string "computer science", snake_case per D-21, no edges, fixed seed, cached, deduplicated, no overlap with any corpus node, >=2100 names; [D-35]). Embedding model choice is settled: local sentence-transformers all-MiniLM-L6-v2 on CPU. | **needs-review** | Completed by Claude Code. Script delivered; pool not yet generated; Luke runs the live step ([D-39]). 291 total tests collected (289 passing, 2 skipped). See report [`docs/reports/DATA-004-claude-code-name-pool-generator.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-004-claude-code-name-pool-generator.md). |
 | DATA-005  | Add secondary concept-name generation backend via external command adapter (claude-automator prompt-adapter), Contract v1, np1w prompt schema, weaker provenance controls, and DATA-004 independent review ([D-43]). | **done** | Accepted at APC review 2026-10-09; follow-ups FIX-011, DATA-006. Completed by Gemini. Adapter contract v1 specified in [`docs/context/prompt-adapter-contract.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/prompt-adapter-contract.md); command backend added to `scripts/generate_name_pool.py`; 25 generator tests passing; full test suite 298 passing, 2 skipped. See report [`docs/reports/DATA-005-gemini-claude-web-backend.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-005-gemini-claude-web-backend.md). |
-| DATA-006  | Implement shard parallelization and merge for `generate_name_pool.py` with FIX-012 folded in: `--shard I/N` partition by global subfield_idx, per-shard run-id and cache, ShardLockManager with flock on run_id and profile locks, `--stagger-s` sleep, `--print-shard-commands`, `--merge-run-ids` for multi-shard pool building with duplicate check across caches, merged meta with shards array and profiles_used, COMMAND_BACKEND_SECONDS_PER_CALL = 40.0, CommandBackend timeout SIGKILL strengthen, contract v1 label corrections to "Sonnet 5.5 Low", and D-44(4) corrections ([D-53]). | **needs-review** | Completed by kiro_default; repairs and full test coverage completed in FIX-013 ([D-54]). See reports [`docs/reports/DATA-006-kiro_default-name-pool-shards.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-006-kiro_default-name-pool-shards.md) and [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
-| DATA-007  | Implement thesis-side supervisor (`scripts/name_pool_supervisor.py`) for unattended sharded name-pool generation: launch N shard subprocesses in process groups, rotate rate-limited (exit 3) or busy (exit 7) profiles onto spare profiles with cooldown tracking, monitor caches via generator loader, write atomic `<state-dir>/status.json` and `supervisor-log.jsonl`, provide `--status` and `--dry-run`, handle `SIGINT`/`SIGTERM` (exit 130) with descendant process-tree termination, and automatically run `--build-only --merge-run-ids` and `--verify --merge-run-ids` on completion ([D-60]). | **needs-review** | Completed by Gemini. 11 supervisor tests passing (`tests/test_name_pool_supervisor.py`); full test suite 499 passing, 4 skipped. See report [`docs/reports/DATA-007-gemini-name-pool-supervisor.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-007-gemini-name-pool-supervisor.md). |
+| DATA-006  | Implement shard parallelization and merge for `generate_name_pool.py` with FIX-012 folded in: `--shard I/N` partition by global subfield_idx, per-shard run-id and cache, ShardLockManager with flock on run_id and profile locks, `--stagger-s` sleep, `--print-shard-commands`, `--merge-run-ids` for multi-shard pool building with duplicate check across caches, merged meta with shards array and profiles_used, COMMAND_BACKEND_SECONDS_PER_CALL = 40.0, CommandBackend timeout SIGKILL strengthen, contract v1 label corrections to "Sonnet 5.5 Low", and D-44(4) corrections ([D-53]). | **done** | Completed by kiro_default; repairs and full test coverage completed in FIX-013 ([D-54]). See reports [`docs/reports/DATA-006-kiro_default-name-pool-shards.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-006-kiro_default-name-pool-shards.md) and [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). Accepted at APC review 2026-10-11 together with FIX-013, FIX-014, FIX-015 ([D-56]). |
+| DATA-007  | Implement thesis-side supervisor (`scripts/name_pool_supervisor.py`) for unattended sharded name-pool generation: launch N shard subprocesses in process groups, rotate rate-limited (exit 3) or busy (exit 7) profiles onto spare profiles with cooldown tracking, monitor caches via generator loader, write atomic `<state-dir>/status.json` and `supervisor-log.jsonl`, provide `--status` and `--dry-run`, handle `SIGINT`/`SIGTERM` (exit 130) with descendant process-tree termination, and automatically run `--build-only --merge-run-ids` and `--verify --merge-run-ids` on completion ([D-60]). | **done** | Completed by Gemini. 11 supervisor tests passing (`tests/test_name_pool_supervisor.py`); full test suite 499 passing, 4 skipped. See report [`docs/reports/DATA-007-gemini-name-pool-supervisor.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-007-gemini-name-pool-supervisor.md). Accepted at APC review 2026-10-11 with follow-ups ([D-56](7)); follow-up FIX-016 (executed as FIX-017). |
 | INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                                                         | **done** | Completed. Library locked as NetworkX via `ConceptGraph` wrapper ([D-22]); canonical edge direction locked as prereq -> dependent ([D-23]); dual-mapping implemented and verified without conflict against all 10 MEKG files. See report [`docs/reports/INFRA-001-claude-code-graph-representation.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-001-claude-code-graph-representation.md). |
 | INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **done** | Completed. Strategy contract, lifecycle, Embedder protocol, MeteredEmbedder, FakeEmbedder, and insert_node driver defined ([D-24], [D-25]). Conformance suite passes (62 tests). See spec [`docs/context/strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/strategy-interface.md) and report [`docs/reports/INFRA-002-gemini-strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-002-gemini-strategy-interface.md). |
 | INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **done** | Completed by Gemini. Discovers 12 corpora, loads into `ConceptGraph` and `GoldJudgmentSet` with strict parsing, canonical orientations via `oriented_edge` ([D-15], [D-19], [D-23]), and graph-level domain context table ([D-27]). All 12 graphs confirmed DAGs. See report [`docs/reports/INFRA-003-gemini-corpus-loader.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-003-gemini-corpus-loader.md). |
@@ -86,9 +86,10 @@ Status: **not started** (blocked on Phase 3)
 | FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07; follow-up FIX-010. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
 | FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **done** | Completed by Gemini. Accepted at APC review 2026-10-09. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
 | FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **done** | Accepted at APC review 2026-10-09; follow-ups in DATA-006. Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
-| FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 14 unit/integration tests; Contract v1.1 ([D-54]). | **needs-review** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
-| FIX-014 | Finish FIX-013: rewrite D-54 in place to remove unsupported claims, close 6 test gaps (merged verify success and tampered cache, recursive results/datagen fixture, profile-lock exclusion, prompt-version-only mismatch, merged meta fidelity, exit-7 cache sha256 preservation), and correct status rows ([D-54]). | **needs-review** | Completed by Gemini. See report [`docs/reports/FIX-014-gemini-finish-fix-013.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-014-gemini-finish-fix-013.md). |
-| FIX-015 | Explicit `--adapter-thinking {auto,on,off}` control for `generate_name_pool.py` (payload, dry-run, shard commands, cache `thinking_requested`, pool `requested_thinking`, mixed-thinking merge refusal), repair `guard_results_datagen_unmodified` fixture by removing destructive cleanup loop and isolating CLI tests to `tmp_path`, replace `sleep` with ready-file handshake in `test_profile_lock_mutual_exclusion` ([D-57]). | **needs-review** | Completed by Gemini. 47 generator tests passing; full test suite 400 passing, 4 skipped. See report [`docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md). |
+| FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 14 unit/integration tests; Contract v1.1 ([D-54]). | **done** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). Accepted at APC review 2026-10-11 ([D-56]). |
+| FIX-014 | Finish FIX-013: rewrite D-54 in place to remove unsupported claims, close 6 test gaps (merged verify success and tampered cache, recursive results/datagen fixture, profile-lock exclusion, prompt-version-only mismatch, merged meta fidelity, exit-7 cache sha256 preservation), and correct status rows ([D-54]). | **done** | Completed by Gemini. See report [`docs/reports/FIX-014-gemini-finish-fix-013.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-014-gemini-finish-fix-013.md). Accepted at APC review 2026-10-11 ([D-56]). |
+| FIX-015 | Explicit `--adapter-thinking {auto,on,off}` control for `generate_name_pool.py` (payload, dry-run, shard commands, cache `thinking_requested`, pool `requested_thinking`, mixed-thinking merge refusal), repair `guard_results_datagen_unmodified` fixture by removing destructive cleanup loop and isolating CLI tests to `tmp_path`, replace `sleep` with ready-file handshake in `test_profile_lock_mutual_exclusion` ([D-57]). | **done** | Completed by Gemini. 47 generator tests passing; full test suite 400 passing, 4 skipped. See report [`docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md). Accepted at APC review 2026-10-11 ([D-56]). |
 | FIX-016 | Make `estimate_and_print_plan()` in `src/graph_insertion/harness.py` use `candidate_upper_bound(strategy, n_existing)` instead of `strategy.config().get("top_k", None)` so dry-run plans for Strategies 3 (`k`), 4 (`s_max`), and `NullStrategy` (`k`) match the live guard `compute_planned_calls_upper_bound`; add unit and parity tests in `tests/test_dry_run_plan.py` ([D-61]). | **needs-review** | Completed by Gemini. 11 dry-run planner tests passing; full test suite 581 passing, 3 skipped. See report [`docs/reports/FIX-016-gemini-dry-run-planner.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-016-gemini-dry-run-planner.md). |
+| FIX-017 | Record every profile used per shard in merged pool meta; add live flag pass-through test and repair the vacuous child-death assertion in the supervisor tests ([D-63]). | **needs-review** | Issued by APC-A 2026-10-11 (as FIX-016 / [D-61]; renumbered to FIX-017 / [D-63]). Completed by Gemini. 60 generator/supervisor tests passing; full test suite 583 passing, 3 skipped. See report [`docs/reports/FIX-017-gemini-profile-provenance-and-supervisor-tests.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-017-gemini-profile-provenance-and-supervisor-tests.md). |
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
diff --git i/scripts/generate_name_pool.py w/scripts/generate_name_pool.py
index 8f301ec..fa1c3ad 100755
--- i/scripts/generate_name_pool.py
+++ w/scripts/generate_name_pool.py
@@ -784,11 +784,32 @@ def build_pool_from_cache(
                 elif e.model_id:
                     obs_counts[e.model_id] = obs_counts.get(e.model_id, 0) + 1
 
+            shard_profiles: list[str] = []
+            seen_shard_profiles: set[str] = set()
+            with open(p, "r", encoding="utf-8") as f:
+                for line in f:
+                    line_str = line.strip()
+                    if not line_str:
+                        continue
+                    try:
+                        raw_rec = json.loads(line_str)
+                    except Exception:
+                        continue
+                    if not isinstance(raw_rec, dict):
+                        continue
+                    bm_raw = raw_rec.get("backend_meta")
+                    if isinstance(bm_raw, dict) and bm_raw.get("profile_used") is not None:
+                        prof_val = str(bm_raw["profile_used"])
+                        if prof_val and prof_val not in seen_shard_profiles:
+                            seen_shard_profiles.add(prof_val)
+                            shard_profiles.append(prof_val)
+
             p_sha = hashlib.sha256(p.read_bytes()).hexdigest()
             shard_infos.append({
                 "run_id": rid,
                 "shard": shard_label,
                 "profile": prof,
+                "profiles": shard_profiles,
                 "call_count": call_count,
                 "observed_models": obs_counts,
                 "tier_histogram": t_counts,
@@ -846,7 +867,7 @@ def build_pool_from_cache(
             agg_adapter_vers.update(s["adapter_versions"])
 
         is_command_backend = (first_backend == "command") or (generator_kind == "claude-web-ui-via-prompt-adapter")
-        profiles_used = sorted({s["profile"] for s in shard_infos if s["profile"]})
+        profiles_used = sorted({prof_name for s in shard_infos for prof_name in s["profiles"] if prof_name})
         sha256_raw_dict = {s["run_id"]: s["sha256_raw_responses"] for s in shard_infos}
 
         req_model: Optional[str] = None
diff --git i/tests/test_generate_name_pool.py w/tests/test_generate_name_pool.py
index c8d56f1..02d1dc7 100644
--- i/tests/test_generate_name_pool.py
+++ w/tests/test_generate_name_pool.py
@@ -2631,4 +2631,126 @@ def test_adapter_thinking_dry_run_and_print_shard_commands(tmp_path: Path) -> No
             assert "--adapter-model sonnet-5" in ln
 
 
+# ===========================================================================
+# 13. FIX-017 Multi-Profile Shard Provenance in Merged Pool
+# ===========================================================================
 
+def test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256(
+    tmp_path: Path,
+) -> None:
+    """Verify that when shard 1 has records with profile_used 'A' then 'B' and shard 2
+    has only 'C', build_pool_from_cache (merged path) records:
+      - shards[0]['profiles'] == ['A', 'B']
+      - shards[0]['profile'] == 'A'
+      - shards[1]['profiles'] == ['C']
+      - meta['profiles_used'] == ['A', 'B', 'C']
+    and that names, n_raw, n_valid, drop_counts, and meta['sha256_names'] are identical
+    to those produced from the same caches with profile_used removed from every record.
+    """
+    from scripts.generate_name_pool import (
+        CacheEntry,
+        append_cache_record,
+        build_pool_from_cache,
+    )
+
+    def _entry(
+        round_num: int,
+        subfield: str,
+        sf_idx: int,
+        names: list[str],
+        shard: str,
+        profile_used: str | None,
+    ) -> CacheEntry:
+        bm: dict[str, Any] = {
+            "model_requested": "sonnet-5",
+            "model_observed": "Sonnet 5 Low",
+            "effort_requested": "low",
+            "thinking_requested": False,
+            "tier": 2,
+            "adapter": {"name": "prompt-adapter", "version": "1.1"},
+        }
+        if profile_used is not None:
+            bm["profile_used"] = profile_used
+        return CacheEntry(
+            round=round_num,
+            subfield=subfield,
+            subfield_idx=sf_idx,
+            request_system="sys",
+            request_user="usr",
+            response_text=json.dumps(names),
+            model_id="Sonnet 5 Low",
+            token_usage={},
+            timestamp_utc=f"2026-10-11T10:0{sf_idx}:00Z",
+            retries=0,
+            latency_s=0.1,
+            parsed_names=names,
+            backend="command",
+            prompt_version="np1w",
+            backend_meta=bm,
+            shard=shard,
+        )
+
+    names_s1_a = [f"synth_algo_item_{i:02d}" for i in range(1, 11)]
+    names_s1_b = [f"synth_comp_item_{i:02d}" for i in range(1, 11)]
+    names_s2_c = [f"synth_ds_item_{i:02d}" for i in range(1, 11)]
+
+    # 1. Caches WITH profile_used ("A" then "B" on shard 1; "C" on shard 2)
+    c1_with = tmp_path / "with_prof" / "s1" / "raw_responses.jsonl"
+    c2_with = tmp_path / "with_prof" / "s2" / "raw_responses.jsonl"
+    append_cache_record(c1_with, _entry(1, "algorithms", 0, names_s1_a, "1/2", "A"))
+    append_cache_record(c1_with, _entry(1, "compilers", 2, names_s1_b, "1/2", "B"))
+    append_cache_record(c2_with, _entry(1, "data_structures", 1, names_s2_c, "2/2", "C"))
+
+    pool_with = build_pool_from_cache(
+        cache_path=[c1_with, c2_with],
+        output_path=tmp_path / "pool_with.json",
+        generator_kind="command",
+        configured_model="sonnet-5",
+        seed=42,
+        run_ids=["s1", "s2"],
+        allow_fake=True,
+        is_merged=True,
+        min_required_names=10,
+    )
+
+    shards = pool_with["meta"]["shards"]
+    assert len(shards) == 2
+    assert shards[0]["shard"] == "1/2"
+    assert shards[0]["profile"] == "A"
+    assert shards[0]["profiles"] == ["A", "B"]
+    assert shards[1]["shard"] == "2/2"
+    assert shards[1]["profile"] == "C"
+    assert shards[1]["profiles"] == ["C"]
+    assert pool_with["meta"]["profiles_used"] == ["A", "B", "C"]
+
+    # 2. Same caches with profile_used removed from every record
+    c1_without = tmp_path / "without_prof" / "s1" / "raw_responses.jsonl"
+    c2_without = tmp_path / "without_prof" / "s2" / "raw_responses.jsonl"
+    append_cache_record(c1_without, _entry(1, "algorithms", 0, names_s1_a, "1/2", None))
+    append_cache_record(c1_without, _entry(1, "compilers", 2, names_s1_b, "1/2", None))
+    append_cache_record(c2_without, _entry(1, "data_structures", 1, names_s2_c, "2/2", None))
+
+    pool_without = build_pool_from_cache(
+        cache_path=[c1_without, c2_without],
+        output_path=tmp_path / "pool_without.json",
+        generator_kind="command",
+        configured_model="sonnet-5",
+        seed=42,
+        run_ids=["s1", "s2"],
+        allow_fake=True,
+        is_merged=True,
+        min_required_names=10,
+    )
+
+    assert pool_without["meta"]["shards"][0]["profile"] is None
+    assert pool_without["meta"]["shards"][0]["profiles"] == []
+    assert pool_without["meta"]["shards"][1]["profile"] is None
+    assert pool_without["meta"]["shards"][1]["profiles"] == []
+    assert pool_without["meta"]["profiles_used"] == []
+
+    # Metadata-only guarantee: names, n_raw, n_valid, drop_counts, and sha256_names are identical
+    assert pool_with["names"] == pool_without["names"]
+    assert pool_with["meta"]["sha256_names"] == pool_without["meta"]["sha256_names"]
+    assert pool_with["meta"]["n_raw"] == pool_without["meta"]["n_raw"]
+    assert pool_with["meta"]["n_valid"] == pool_without["meta"]["n_valid"]
+    assert pool_with["meta"]["drop_counts"] == pool_without["meta"]["drop_counts"]
diff --git i/tests/test_name_pool_supervisor.py w/tests/test_name_pool_supervisor.py
index 267d369..6e7c9c0 100644
--- i/tests/test_name_pool_supervisor.py
+++ w/tests/test_name_pool_supervisor.py
@@ -209,6 +209,14 @@ def test_failover_on_rate_limit_to_spare_profile(
     assert len(pool_data["names"]) == 160
     assert pool_data["meta"]["run_ids"] == ["failover-s1of2", "failover-s2of2"]
     assert len(pool_data["meta"]["shards"]) == 2
+    s1_meta = next(s for s in pool_data["meta"]["shards"] if s["shard"] == "1/2")
+    s2_meta = next(s for s in pool_data["meta"]["shards"] if s["shard"] == "2/2")
+    assert s1_meta["profile"] == "rate_limit_after_1_p1"
+    assert s1_meta["profiles"] == ["rate_limit_after_1_p1", "Spare_P3"]
+    assert s2_meta["profiles"] == ["Profile_2"]
+    assert pool_data["meta"]["profiles_used"] == sorted(
+        ["rate_limit_after_1_p1", "Profile_2", "Spare_P3"]
+    )
 
 
 def test_profile_in_use_rotates_to_next_profile_with_short_cooldown(
@@ -626,6 +634,8 @@ def test_loader_value_error_stops_everything(
     tmp_path: Path, monkeypatch: pytest.MonkeyPatch
 ) -> None:
     """10. Loader ValueError (corrupt / conflicting cache lines mid-run) stops everything cleanly."""
+    import threading
+
     monkeypatch.chdir(tmp_path)
     state_dir = tmp_path / "sup_valerr"
     lock_dir = tmp_path / "locks_valerr"
@@ -635,10 +645,7 @@ def test_loader_value_error_stops_everything(
         f"--child-pid-file {child_pid_file} --hang-seconds 30"
     )
 
-    # Pre-populate shard 1 cache with mixed backend records ('command' vs 'deepseek')
-    # so load_completed_cache() raises ValueError during the supervisor's poll.
-    s1_cache = tmp_path / "results" / "datagen" / "valerr-s1of2" / "raw_responses.jsonl"
-    s1_cache.parent.mkdir(parents=True, exist_ok=True)
+    s1_cache = tmp_path / "results" / "datagen" / "valerr-s1of1" / "raw_responses.jsonl"
     rec1 = {
         "round": 1,
         "subfield": "algorithms",
@@ -661,14 +668,28 @@ def test_loader_value_error_stops_everything(
         "backend": "deepseek",
         "prompt_version": "np1",
     }
-    s1_cache.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")
+
+    def _inject_conflicting_cache_after_child_spawn() -> None:
+        deadline = time.monotonic() + 10.0
+        while time.monotonic() < deadline:
+            if child_pid_file.exists() and child_pid_file.read_text(encoding="utf-8").strip():
+                break
+            time.sleep(0.02)
+        s1_cache.parent.mkdir(parents=True, exist_ok=True)
+        s1_cache.write_text(
+            json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n",
+            encoding="utf-8",
+        )
+
+    injector = threading.Thread(target=_inject_conflicting_cache_after_child_spawn, daemon=True)
+    injector.start()
 
     rc = supervisor_main([
-        "--shards", "2",
-        "--profiles", "hang_p1,hang_p2",
+        "--shards", "1",
+        "--profiles", "hang_p1",
         "--run-id-prefix", "valerr",
         "--command", stub_cmd,
-        "--target-names", "160",
+        "--target-names", "80",
         "--pause-s", "0",
         "--stagger-s", "0",
         "--poll-s", "0.05",
@@ -678,14 +699,111 @@ def test_loader_value_error_stops_everything(
         "--live",
         "--confirm",
     ])
+    injector.join(timeout=5.0)
     assert rc == SUP_EXIT_ERROR
 
-    if child_pid_file.exists():
-        cpid = int(child_pid_file.read_text(encoding="utf-8").strip())
-        assert not _pid_is_alive(cpid)
+    assert child_pid_file.exists(), "Stub did not write child_pid_file before loader_error!"
+    cpid = int(child_pid_file.read_text(encoding="utf-8").strip())
+    assert not _pid_is_alive(cpid)
 
     events = _read_jsonl(state_dir / "supervisor-log.jsonl")
     assert any(
         e["event"] == "loader_error" and "mixed backends" in e.get("error", "")
         for e in events
     )
+
+
+def test_live_adapter_flags_passthrough(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """11. Live pass-through of --adapter-model, --adapter-effort, and --adapter-thinking
+    reaches shard subprocesses, stdin payloads, cache backend_meta, and supervisor-log.jsonl.
+    """
+    monkeypatch.chdir(tmp_path)
+
+    # Case A: primary generation settings (--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off)
+    state_dir_a = tmp_path / "sup_flags_a"
+    lock_dir_a = tmp_path / "locks_flags_a"
+    out_pool_a = tmp_path / "pool_a.json"
+    payload_file_a = tmp_path / "payloads_a.jsonl"
+    stub_cmd_a = f"{sys.executable} {_STUB_SCRIPT} --record-payload-file {payload_file_a}"
+
+    rc_a = supervisor_main([
+        "--shards", "2",
+        "--profiles", "Prof_Flag_1,Prof_Flag_2",
+        "--run-id-prefix", "flagpass",
+        "--command", stub_cmd_a,
+        "--adapter-model", "sonnet-5",
+        "--adapter-effort", "low",
+        "--adapter-thinking", "off",
+        "--target-names", "120",
+        "--max-calls", "5",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir_a),
+        "--lock-dir", str(lock_dir_a),
+        "--output", str(out_pool_a),
+        "--live",
+        "--confirm",
+    ])
+    assert rc_a == SUP_EXIT_OK
+
+    payloads_a = _read_jsonl(payload_file_a)
+    assert len(payloads_a) == 4
+    for p in payloads_a:
+        assert p["model"] == "sonnet-5"
+        assert p["effort"] == "low"
+        assert "thinking" in p
+        assert p["thinking"] is False
+
+    for rid in ("flagpass-s1of2", "flagpass-s2of2"):
+        cpath = tmp_path / "results" / "datagen" / rid / "raw_responses.jsonl"
+        crecs = _read_jsonl(cpath)
+        assert len(crecs) == 2
+        for rec in crecs:
+            assert rec["backend_meta"]["thinking_requested"] is False
+            assert rec["backend_meta"]["model_requested"] == "sonnet-5"
+            assert rec["backend_meta"]["effort_requested"] == "low"
+
+    events_a = _read_jsonl(state_dir_a / "supervisor-log.jsonl")
+    launch_events_a = [e for e in events_a if e["event"] == "shard_launch"]
+    assert len(launch_events_a) == 2
+    for le in launch_events_a:
+        assert "--adapter-thinking off" in le["command"]
+        assert "--adapter-model sonnet-5" in le["command"]
+        assert "--adapter-effort low" in le["command"]
+
+    # Case B: non-default effort (--adapter-effort medium) so removing adapter_effort from
+    # _launch_shard (where build_shard_cli_tokens defaults adapter_effort='low') is caught
+    state_dir_b = tmp_path / "sup_flags_b"
+    lock_dir_b = tmp_path / "locks_flags_b"
+    out_pool_b = tmp_path / "pool_b.json"
+    payload_file_b = tmp_path / "payloads_b.jsonl"
+    stub_cmd_b = f"{sys.executable} {_STUB_SCRIPT} --record-payload-file {payload_file_b}"
+
+    rc_b = supervisor_main([
+        "--shards", "1",
+        "--profiles", "Prof_Flag_Med",
+        "--run-id-prefix", "flagmed",
+        "--command", stub_cmd_b,
+        "--adapter-model", "sonnet-5",
+        "--adapter-effort", "medium",
+        "--adapter-thinking", "off",
+        "--target-names", "40",
+        "--max-calls", "2",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir_b),
+        "--lock-dir", str(lock_dir_b),
+        "--output", str(out_pool_b),
+        "--live",
+        "--confirm",
+    ])
+    assert rc_b == SUP_EXIT_OK
+    payloads_b = _read_jsonl(payload_file_b)
+    assert len(payloads_b) == 1
+    assert payloads_b[0]["model"] == "sonnet-5"
+    assert payloads_b[0]["effort"] == "medium"
+    assert payloads_b[0]["thinking"] is False
```
