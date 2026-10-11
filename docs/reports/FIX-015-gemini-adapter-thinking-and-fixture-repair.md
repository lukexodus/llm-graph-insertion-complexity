# FIX-015 Report: Explicit Thinking Control for `generate_name_pool.py` and `results/datagen` Fixture Repair

**Task ID:** FIX-015  
**Agent:** `gemini`  
**Date:** 2026-10-11  
**Branch / Checkout:** `master` at `6cd360a` (`/home/lukexodus/projects/llm-graph-insertion-complexity`, main checkout per operator override)

---

## 1. What Changed

### Part A: `--adapter-thinking {auto,on,off}`
1. **CLI Flag and Mapping (`scripts/generate_name_pool.py`)**:
   - Added `ADAPTER_THINKING_MAP: dict[str, Optional[bool]] = {"auto": None, "on": True, "off": False}` and `parse_adapter_thinking(val: Optional[str]) -> Optional[bool]`.
   - Added `--adapter-thinking` (`choices=["auto", "on", "off"]`, `default="auto"`) to `build_parser()`.
   - Passed `thinking=parse_adapter_thinking(adapter_thinking)` into `CommandGenerationBackend` in `run_generation_loop()`.
   - Updated `CommandGenerationBackend.__init__` and `complete()` to accept `thinking: Optional[bool] = None` and send `"thinking": self.thinking` in the stdin JSON request payload.
2. **Dry-Run and Shard Commands (`scripts/generate_name_pool.py`)**:
   - Added `print(f"Adapter thinking:      {args.adapter_thinking}")` to the `--dry-run` output for `--backend command`.
   - Added `cmd_parts.extend(["--adapter-thinking", shlex.quote(str(args.adapter_thinking))])` to `--print-shard-commands`.
3. **Cache `backend_meta` and Pool `meta` Provenance (`scripts/generate_name_pool.py`)**:
   - In `CommandGenerationBackend.complete()`, added `backend_meta.setdefault("thinking_requested", self.thinking)` on success so `thinking_requested` is always recorded in each cache record's `backend_meta` even when `prompt-adapter` does not echo `thinking_requested` in stdout.
   - In `build_pool_from_cache()`, extracted `thinking_requested` from `backend_meta` and recorded `"requested_thinking": req_thinking` in `meta` for both single-run and merged command-backend pools.
   - In both `load_completed_cache()` and the merged path of `build_pool_from_cache()`, enforced consistency of `thinking_requested` across all records/shards using `(type(thinking_val), thinking_val)` comparison, raising `ValueError("... contains mixed thinking settings: ...")` on any mismatch.
4. **Stub and End-to-End Tests (`tests/stub_prompt_adapter.py`, `tests/test_generate_name_pool.py`)**:
   - Extended `tests/stub_prompt_adapter.py` with `--record-payload-file` to append the exact JSON payload received on stdin to a file, and included `"thinking_requested": thinking_req` in the stub's `success`, `prose_wrapped`, and `unparseable` JSON responses.
   - Added `test_adapter_thinking_payload_and_meta_e2e`, `test_merge_refuses_mixed_thinking_settings`, and `test_adapter_thinking_dry_run_and_print_shard_commands` to `tests/test_generate_name_pool.py`.

### Part A(6): `claude-automator` Source Findings (Read-Only)
Inspected `/home/lukexodus/projects/claude-automator` (read-only):
1. **Model identifiers accepted by `prompt-adapter`**:
   - In `apps/prompt-adapter/src/prompt_adapter/runner.py:90-92` (`validate_request`), `model` is validated only as a non-empty string (`default "sonnet"`).
   - In `apps/prompt-adapter/src/prompt_adapter/runner.py:265-285` (`get_expected_model_ui_label`) and `packages/claude-engine/src/claude_engine/browser/claude_ui.py:302-330` (`select_model`), `norm_model = model_name.lower().replace("_", "-").replace(" ", "-")` is mapped as follows:
     - `("haiku", "haiku-4.5", "haiku-3.5")` $\rightarrow$ `target_model_id = "claude-haiku-4-5-20251001"`, expected UI label `"Haiku 4.5"`
     - `("opus", "opus-5", "opus-5.5")` $\rightarrow$ `target_model_id = "claude-opus-5-5"`, expected UI label `"Opus 5.5"`
     - `("fable", "fable-5", "fable-5.1")` $\rightarrow$ `target_model_id = "claude-fable-5-1"`, expected UI label `"Fable 5.1"`
     - `("sonnet-4.6", "4.6")` $\rightarrow$ `target_model_id = "claude-sonnet-4-6"`, expected UI label `"Sonnet 4.6"`
     - `("sonnet-5", "5")` $\rightarrow$ `target_model_id = "claude-sonnet-5"`, expected UI label `"Sonnet 5"` (verified via regex `\bSonnet 5(?!\.\d)\b` in `runner.py:310-315` so `"Sonnet 5.5"` does not match `"Sonnet 5"`)
     - `("sonnet-5.5", "5.5")` $\rightarrow$ `target_model_id = "claude-sonnet-5-5"`, expected UI label `"Sonnet 5.5"`
     - Any other string (including `"sonnet"`) $\rightarrow$ defaults to `target_model_id = "claude-sonnet-5-5"`, expected UI label `"Sonnet 5.5"`.
2. **Whether `effort` is accepted for Sonnet 5 (and how `thinking` interacts)**:
   - In `apps/prompt-adapter/src/prompt_adapter/runner.py:57, 95-99` (`validate_request`), `effort` is accepted for all models (including `"sonnet-5"` / `"5"`) if it is in `VALID_EFFORTS = ("low", "medium", "high", "extra", "max", None)` (default `"low"`). *(Caveat: passing `"effort": null` passes `validate_request` in `runner.py`, but `claude_ui.py:58` executes `model_cfg.get('effort', 'low').lower().strip()`, which raises `AttributeError` if `model_cfg['effort']` is `None`; string values `"low"`, `"medium"`, `"high"`, `"extra"`, `"max"` work cleanly.)*
   - In `packages/claude-engine/src/claude_engine/browser/claude_ui.py:458-568` (`select_model`), all non-Haiku models (`norm_model not in ("haiku", "haiku-4.5", "haiku-3.5")`, which includes `"sonnet-5"`) enter the effort/thinking configuration branch:
     - **UI Variations 1 & 2 (Inline effort controls)**: If `[data-effort-id]` buttons exist in the open model menu, `select_model` clicks `[data-effort-id="{target_effort_id}"]` (or `[role="menuitemradio"]:has-text("{target_effort_text}")`) and does not toggle a separate `Thinking` checkbox.
     - **UI Variation 3 (Legacy submenu)**: If inline `[data-effort-id]` controls are absent, it looks for `[role="menuitem"]:has-text("Effort"), [aria-haspopup="menu"]:has-text("Effort")`. If found, it hovers `"Effort"`, locates `[role="menuitemcheckbox"]:has-text("Thinking")`, toggles it if its state (`aria-checked` / `data-state="checked"`) differs from `thinking = bool(model_cfg.get('thinking', False))`, and then clicks the effort radio item. If no effort controls are present in the menu at all, it logs `"select_model: no effort controls found in menu"` and closes the menu without error.
   - Note also: in `runner.py:249-250`, `model_cfg["thinking"] = thinking` is only written when `thinking is not None`; in `claude_ui.py:59`, `thinking = bool(model_cfg.get('thinking', False))`. Moreover, `runner.py:536-551` (`format_success`) does not include `thinking_requested` in `prompt-adapter`'s stdout JSON, which is why `CommandGenerationBackend.complete()` uses `backend_meta.setdefault("thinking_requested", self.thinking)`.

### Part B: `results/datagen` Fixture Repair & Lock-Test Handshake (`tests/test_generate_name_pool.py`)
1. Removed the destructive cleanup loop (`for p in datagen_dir.iterdir(): ... shutil.rmtree(p, ignore_errors=True)`) from `guard_results_datagen_unmodified` so that it is strictly a before/after recursive relative-path snapshot assertion.
2. Fixed the five CLI tests that created files or directories under `results/datagen`:
   - `test_live_mode_refuses_without_confirm_and_without_key`: passed `--cache-file` and `--lock-dir` under `tmp_path` on the second subprocess invocation (which reaches `ShardLockManager.acquire()` before checking `DEEPSEEK_API_KEY`).
   - `test_offline_fake_refuses_default_output_path`: added `tmp_path: Path` fixture parameter and passed `--cache-file` and `--lock-dir` under `tmp_path`.
   - `test_command_backend_success_e2e`: passed `--lock-dir` under `tmp_path` (previously omitted, which caused `ShardLockManager` to create `results/datagen/.locks/test_prof.lock`).
   - `test_stop_and_resume_after_rate_limit`: passed `--lock-dir` under `tmp_path` to both subprocess calls (`res1` and `res2`).
   - `test_cli_verify_merged_success_and_tampered_cache`: moved `results/datagen/<run_id>/raw_responses.jsonl` under `tmp_path / "results" / "datagen"` and ran the `--verify` subprocesses with `cwd=tmp_path`.
3. Replaced `time.sleep(0.3)` in `test_profile_lock_mutual_exclusion` with a ready-file handshake (`ready_file = tmp_path / "profile_lock.ready"` written by the helper immediately after `fcntl.flock`, polled by the parent up to 5.0 s before failing with a clear timeout message).

### Part C: Shared Documentation (`docs/decisions/decision-log.md`, `docs/tasks/status.md`)
- Appended `**[D-57]**` to `docs/decisions/decision-log.md` covering (1) `--adapter-thinking` flag, mapping, and recording, (2) `guard_results_datagen_unmodified` repair and `test_profile_lock_mutual_exclusion` handshake, and (3) the `[D-54]` historical note (`test_results_datagen_unmodified_by_test_suite` replaced by fixture in `FIX-014`; `[D-54]` committed in `63cddfb` and rewritten in place in `8429122`).
- Added the `FIX-015` row (`**needs-review**`) to `docs/tasks/status.md`.

---

## 2. Probe Test Proof: `guard_results_datagen_unmodified` Fails on Stray Files

### 2a. Probe Test Failure Output (with temporary `test_probe_results_datagen_guard_fails` creating `results/datagen/_probe/.lock`)
```text
Test session starts (platform: linux, Python 3.14.7, pytest 9.1.0, pytest-sugar 1.1.1)
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: instafail-0.5.0, sugar-1.1.1, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, inline-snapshot-0.32.6, typeguard-4.6.0, time-machine-3.5.0, anyio-4.15.1, hypothesis-6.167.1
collecting ... collected 48 items / 47 deselected / 1 selected                                



――――――――― ERROR at teardown of test_probe_results_datagen_guard_fails ――――――――――

    @pytest.fixture(scope="module", autouse=True)
    def guard_results_datagen_unmodified() -> Generator[None, None, None]:
        """Module-scoped autouse fixture that snapshots the full recursive relative-path
        state of results/datagen before test execution and asserts exact equality after.
        Guarantees that no test in this module creates stray files or directories in results/datagen.
        """
        datagen_dir = Path("results/datagen")
    
        def _snapshot() -> set[str] | None:
            if not datagen_dir.exists():
                return None
            items: set[str] = set()
            for root, dirs, files in os.walk(datagen_dir):
                for d in dirs:
                    items.add(os.path.relpath(os.path.join(root, d), datagen_dir))
                for f in files:
                    items.add(os.path.relpath(os.path.join(root, f), datagen_dir))
            return items
    
        before = _snapshot()
        yield
        after = _snapshot()
>       assert after == before, (
            f"results/datagen was modified by tests in test_generate_name_pool!\n"
            f"Added: {after - before if (after and before) else after}\n"
            f"Removed: {before - after if (after and before) else before}"
        )
E       AssertionError: results/datagen was modified by tests in test_generate_name_pool!
E         Added: {'_probe/.lock', '_probe'}
E         Removed: set()
E       assert {'_probe', '_probe/.lock'} == set()
E         
E         Extra items in the left set:
E         '_probe/.lock'
E         '_probe'
E         Use -v to get more diff

tests/test_generate_name_pool.py:80: AssertionError

                                                                 100% ██████████
=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_probe_results_datagen_guard_fails

Results (1.40s):
       1 passed
       1 error
      47 deselected
```

### 2b. Clean Run Output After Removing Probe
```text
tests/test_generate_name_pool.py ....................................... [ 82%]
........                                                                 [100%]

======================== 47 passed in 98.71s (0:01:38) =========================
```

---

## 3. How I Know Each Test Can Fail (Local Mutation Verification)

Before mutating, `scripts/generate_name_pool.py` was backed up to `/tmp/fix015_bak/generate_name_pool.py` and verified byte-identical after restoration with `cmp -s`.

### 3.1 `test_adapter_thinking_payload_and_meta_e2e`
- **Mutation**: Replaced `"thinking": self.thinking,` with `"thinking": None,` in `CommandGenerationBackend.complete()` (`scripts/generate_name_pool.py`).
- **Failing Output**:
```text
―――――――――――――――――― test_adapter_thinking_payload_and_meta_e2e ――――――――――――――――――

tmp_path = PosixPath('/tmp/pytest-of-lukexodus/pytest-81/test_adapter_thinking_payload_0')

            # 1. Check exact payload received by stub_prompt_adapter
            payload_lines = [ln for ln in payload_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
            assert len(payload_lines) == 1
            received_payload = json.loads(payload_lines[0])
            assert "thinking" in received_payload
>           assert received_payload["thinking"] is expected_val
E           assert None is True

tests/test_generate_name_pool.py:2411: AssertionError

=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_adapter_thinking_payload_and_meta_e2e

Results (7.16s):
       1 failed
         - tests/test_generate_name_pool.py:2347 test_adapter_thinking_payload_and_meta_e2e
      46 deselected
```

### 3.2 `test_merge_refuses_mixed_thinking_settings`
- **Mutation**: Replaced `elif (type(thinking_val), thinking_val) != (type(first_thinking), first_thinking):` with `elif False:` in `load_completed_cache()` and `build_pool_from_cache()` (`scripts/generate_name_pool.py`).
- **Failing Output**:
```text
―――――――――――――――――― test_merge_refuses_mixed_thinking_settings ――――――――――――――――――

tmp_path = PosixPath('/tmp/pytest-of-lukexodus/pytest-84/test_merge_refuses_mixed_think0')

        c_off = _make_shard_cache("shard_off", "algorithms", 0, False)
        c_on = _make_shard_cache("shard_on", "data_structures", 1, True)
        c_auto = _make_shard_cache("shard_auto", "operating_systems", 2, None)
    
        # 1. off (False) vs on (True) across merged caches
>       with pytest.raises(ValueError, match="mixed thinking settings"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_generate_name_pool.py:2550: Failed

=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_merge_refuses_mixed_thinking_settings

Results (3.10s):
       1 failed
         - tests/test_generate_name_pool.py:2490 test_merge_refuses_mixed_thinking_settings
      46 deselected
```

### 3.3 `test_adapter_thinking_dry_run_and_print_shard_commands`
- **Mutation**: Replaced `print(f"Adapter thinking:      {args.adapter_thinking}")` with `pass` in `main()` (`scripts/generate_name_pool.py`).
- **Failing Output**:
```text
―――――――――――― test_adapter_thinking_dry_run_and_print_shard_commands ――――――――――――

tmp_path = PosixPath('/tmp/pytest-of-lukexodus/pytest-82/test_adapter_thinking_dry_run_0')

            res_dry = subprocess.run(cmd, capture_output=True, text=True)
            assert res_dry.returncode == 0
>           assert f"Adapter thinking:      {expected}" in res_dry.stdout
E           assert 'Adapter thinking:      auto' in "=== DATA-005 Concept Name Pool Generator Plan (Dry Run - Command Backend) ===\nSubfields count:       80\nTarget vali...te memory from chats' must be OFF on target Claude account.\nDry run complete (no API calls made, no files created).\n"

tests/test_generate_name_pool.py:2606: AssertionError

=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_adapter_thinking_dry_run_and_print_shard_commands

Results (3.55s):
       1 failed
         - tests/test_generate_name_pool.py:2585 test_adapter_thinking_dry_run_and_print_shard_commands
      46 deselected
```

### 3.4 `test_profile_lock_mutual_exclusion`
- **Mutation**: Replaced `if self.adapter_profile:` with `if False and self.adapter_profile:` in `ShardLockManager.acquire()` (`scripts/generate_name_pool.py`).
- **Failing Output**:
```text
―――――――――――――――――――――― test_profile_lock_mutual_exclusion ――――――――――――――――――――――

tmp_path = PosixPath('/tmp/pytest-of-lukexodus/pytest-83/test_profile_lock_mutual_exclu0')

        try:
            deadline = time.monotonic() + 5.0
            while not ready_file.exists():
                if time.monotonic() >= deadline:
                    pytest.fail(f"Timed out after 5.0s waiting for lock helper ready file: {ready_file}")
                time.sleep(0.02)
    
            res = subprocess.run(cmd, capture_output=True, text=True)
>           assert res.returncode == 1
E           assert 0 == 1

tests/test_generate_name_pool.py:1767: AssertionError

=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_profile_lock_mutual_exclusion

Results (6.35s):
       1 failed
         - tests/test_generate_name_pool.py:1704 test_profile_lock_mutual_exclusion
      46 deselected
```

---

## 4. Test Suite and `results/datagen` Verification

### `pytest -q | tail -3`
```text
.....                                                                    [100%]

================== 400 passed, 4 skipped in 110.64s (0:01:50) ==================
```

### `pytest -q tests/test_generate_name_pool.py | tail -3`
```text
........                                                                 [100%]

======================== 47 passed in 98.71s (0:01:38) =========================
```

### `ls -la results/datagen` after full run
```text
total 0
drwxr-xr-x 1 lukexodus lukexodus  0 Oct 11 17:30 .
drwxr-xr-x 1 lukexodus lukexodus 24 Oct 11 17:21 ..
```

---

## 5. Found But Not Changed
1. **Uncommitted files from concurrent/prior tasks in the main checkout**:
   - `docs/context/apc-bundle-quickref.md` (untracked), `docs/reports/STRAT-003-A-claude-code.md` (untracked), `scripts/README.md` (modified), `scripts/apc-bundle.sh` (modified), and lines 48–51 of `docs/tasks/status.md` (`STRAT-001`, `STRAT-002`, `STRAT-003` status updates from `STRAT-003-A`) were already present in the working tree when `FIX-015` began and were left untouched.
2. **`effort: null` handling in `claude-automator`**:
   - In `/home/lukexodus/projects/claude-automator/apps/prompt-adapter/src/prompt_adapter/runner.py:57`, `VALID_EFFORTS` includes `None`, so `"effort": null` passes request validation, but `packages/claude-engine/src/claude_engine/browser/claude_ui.py:58` executes `model_cfg.get('effort', 'low').lower().strip()`, which raises `AttributeError: 'NoneType' object has no attribute 'lower'` when `model_cfg['effort']` is `None`. `scripts/generate_name_pool.py` always sends a string (`default="low"`, choices `["low", "medium", "high"]`), so this does not affect the generator, and `claude-automator` is read-only.
3. **`prompt-adapter` stdout omits `thinking_requested`**:
   - `runner.py:536-551` (`format_success`) in `claude-automator` returns `model_requested` and `effort_requested` in stdout JSON, but does not include `thinking_requested`. Handled on the generator side via `backend_meta.setdefault("thinking_requested", self.thinking)` in `CommandGenerationBackend.complete()`.

---

## 6. Prompt Statements Verified Against the Repo (Right vs. Wrong)
1. **Worktree instruction vs. operator override**:
   - Prompt Section 0 instructed: *"Work in a git worktree, not the main checkout (APC-B has uncommitted edits there): `git worktree add ../llm-graph-insertion-complexity-fix015 --detach HEAD` and work inside it."*
   - However, the user appended an explicit override at the end of the prompt: *"update: do not work in a worktree since all the previous work are already committed"*.
   - **Verification**: `STRAT-003-A` was indeed already committed to `HEAD` (`ab7096d`, followed by `6cd360a`), though `docs/tasks/status.md` (lines 48–51), `scripts/README.md`, `scripts/apc-bundle.sh`, and two untracked files (`docs/context/apc-bundle-quickref.md`, `docs/reports/STRAT-003-A-claude-code.md`) remained uncommitted in the main checkout. Per the user's explicit override, work was performed directly in the main checkout without touching those files.
2. **Decision ID `D-55` collision**:
   - Prompt Section 0 & Section 4 instructed: *"Decision ID: use D-55 only (D-56 is reserved by the APC)."*
   - **Verification**: **Wrong / stale in prompt.** `**[D-55]**` was already committed in `docs/decisions/decision-log.md` (line 434) by commit `ab7096d` (`STRAT-003-A: fix F-1 cache clear on shortlist entry, raise default ef_search to 128`). Per `AGENTS.md` Parallel Work Rule 4 (*"If a reserved ID is already used in the file, stop and report the conflict; do not renumber"*), we stopped and asked the user via `ask_question`; the user instructed us to use **`[D-57]`**.
3. **Commit hashes for `D-54`**:
   - Prompt Section 0 & Section 4 stated: *"D-54 is committed and on origin (commit 63cddfb; its rewrite is in 8429122)."*
   - **Verification**: **Right.** `git log --oneline -n 5` confirmed `63cddfb` (*"Finalize DATA-006 and FIX-013 shard orchestration and tests"*) initially committed `[D-54]`, and `8429122` (*"Complete FIX-014: rewrite D-54, close test gaps, and update status"*) rewrote `[D-54]` in place.
4. **Defective `guard_results_datagen_unmodified` fixture and `test_profile_lock_mutual_exclusion` sleep**:
   - Prompt Sections 1 & 3 stated that `guard_results_datagen_unmodified` in `tests/test_generate_name_pool.py` deleted 16-character timestamped directories under `results/datagen` before comparing, and `test_profile_lock_mutual_exclusion` used `time.sleep(0.3)`.
   - **Verification**: **Right.** Both were present in `tests/test_generate_name_pool.py` (lines 79–83 and line 1744) and were repaired in Part B.

---

## 7. Verbatim `git diff`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 56dfd5a..1e4419b 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -440,3 +440,9 @@ Reasoning: removes unverified claims and inaccuracies from D-54, defines the exa
 (6) Equivalent-mutant findings: analysis confirms that review mutation 18 (full `_index.ntotal` variant in `diagnostics()`) is equivalent through the public API because the only node that can exist between `_n_at_query` and `_index.ntotal` is `new_name` itself, which is explicitly filtered out by name in `valid_items`; review mutation 17 (omitting `_names = []` and `_name_to_idx = {}` at the top of `setup()`) is unobservable because a successful setup overwrites both collections while a failed setup sets `_setup_called = False` and `_embedder = None`, blocking all query entry points.
 (7) Thesis-text synchronization flag for APC-A: thesis Section 3.2.4 currently names only $k$ as a tunable parameter and states $k$ is fixed "empirically per Section 3.4", while Section 3.4 provides no calibration procedure; furthermore, index hyperparameters ($M=16, \text{efConstruction}=200, \text{efSearch}=128$) and the `exact_topk_overlap` fidelity metric are not yet described in the thesis text. A synchronization edit is required in Chapter 3 to document a-priori parameter fixing and approximation fidelity diagnostics.
 Reasoning: resolves review defect F-1, improves approximation fidelity from $\approx 84\%$ to $\approx 97\%$ under uniform vector dispersion with negligible latency cost, hardens setup and shortlist cache invalidation, closes test coverage gaps without vacuous assertions, and documents mutant equivalences. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, STRAT-002, STRAT-003, INFRA-007.
+
+**[D-57]** Explicit adapter thinking control, `results/datagen` guard fixture repair, and D-54 historical note (FIX-015):
+(1) Explicit `--adapter-thinking` control: `scripts/generate_name_pool.py` adds `--adapter-thinking {auto,on,off}` (default `auto`), mapping `auto -> None`, `on -> True`, and `off -> False` via `parse_adapter_thinking()`. `CommandGenerationBackend` sends the mapped value as `"thinking"` in the stdin request payload to `prompt-adapter`, displays `Adapter thinking:` in `--dry-run` output for the command backend, and emits `--adapter-thinking <val>` in `--print-shard-commands` output. Each cache record's `backend_meta` records `"thinking_requested"` (with `backend_meta.setdefault("thinking_requested", self.thinking)` in `CommandGenerationBackend.complete()` because `prompt-adapter`'s stdout dict does not echo `thinking_requested`), and pool `meta` records `"requested_thinking"` in both single-run and merged command-backend pools. Both `load_completed_cache()` and `build_pool_from_cache()` reject mixed `thinking_requested` values across records or shard caches with a `ValueError` containing `"mixed thinking settings"`.
+(2) `results/datagen` guard fixture repair and lock-test handshake: removed the destructive cleanup loop in `guard_results_datagen_unmodified` (`tests/test_generate_name_pool.py`) that previously deleted 16-character timestamped directories under `results/datagen` before snapshotting, which masked stray directory creation by tests. The fixture is now strictly a read-only before/after recursive relative-path snapshot assertion. Updated the five CLI tests that previously wrote to `results/datagen` (`test_live_mode_refuses_without_confirm_and_without_key`, `test_offline_fake_refuses_default_output_path`, `test_command_backend_success_e2e`, `test_stop_and_resume_after_rate_limit`, and `test_cli_verify_merged_success_and_tampered_cache`) to keep all cache files, run directories, and lock directories under `tmp_path` without altering production defaults. Replaced the fixed `time.sleep(0.3)` in `test_profile_lock_mutual_exclusion` with a ready-file handshake (polling up to 5.0 s).
+(3) Historical note on [D-54]: [D-54](1) lists `test_results_datagen_unmodified_by_test_suite`, which FIX-014 replaced with the module-scoped autouse fixture `guard_results_datagen_unmodified`. Furthermore, [D-54] was rewritten in place in commit `8429122` after already being committed in `63cddfb`, so the original [D-54] text remains in git history at `63cddfb`. (Note: the FIX-015 prompt specified decision ID `D-55`, which was already assigned to STRAT-003-A in commit `ab7096d`, and `D-56` was reserved by the APC; `D-57` is used per operator instruction.)
+Reasoning: enables explicit thinking configuration (such as `sonnet-5` with `--adapter-thinking off`) with full cache and pool provenance and merge consistency checks, ensures `guard_results_datagen_unmodified` fails on any stray file or directory creation in `results/datagen`, eliminates a timing race in profile lock testing, and records the git history of [D-54]. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, DATA-005, DATA-006, FIX-014, FIX-015.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 7395c48..d759a47 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -43,12 +43,12 @@ Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-1
 
 Status: **open** (unblocked following Phase 1 completion; four parallel tracks ready for implementation)
 
-| ID        | Task                                       | Status | Notes                                                                          |
-| --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
-| STRAT-001 | Implement Strategy 1 (brute-force)         | **done** | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11. |
-| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done** | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
-| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md). |
-| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |
+| ID        | Task                                       | Status           | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
+| --------- | ------------------------------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
+| STRAT-001 | Implement Strategy 1 (brute-force)         | **done**         | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11.                                    |
+| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done**         | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
+| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md).                                                                                                                                                                                                                                 |
+| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open             | Most conceptually involved — recommend close review per `high-level-tasks.md`.                                                                                                                                                                                                                                                                                                                                                                                                                             |
 
 ## Phase 3 — Integration & Full Sweep
 
@@ -87,5 +87,6 @@ Status: **not started** (blocked on Phase 3)
 | FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **done** | Accepted at APC review 2026-10-09; follow-ups in DATA-006. Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
 | FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 14 unit/integration tests; Contract v1.1 ([D-54]). | **needs-review** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
 | FIX-014 | Finish FIX-013: rewrite D-54 in place to remove unsupported claims, close 6 test gaps (merged verify success and tampered cache, recursive results/datagen fixture, profile-lock exclusion, prompt-version-only mismatch, merged meta fidelity, exit-7 cache sha256 preservation), and correct status rows ([D-54]). | **needs-review** | Completed by Gemini. See report [`docs/reports/FIX-014-gemini-finish-fix-013.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-014-gemini-finish-fix-013.md). |
+| FIX-015 | Explicit `--adapter-thinking {auto,on,off}` control for `generate_name_pool.py` (payload, dry-run, shard commands, cache `thinking_requested`, pool `requested_thinking`, mixed-thinking merge refusal), repair `guard_results_datagen_unmodified` fixture by removing destructive cleanup loop and isolating CLI tests to `tmp_path`, replace `sleep` with ready-file handshake in `test_profile_lock_mutual_exclusion` ([D-57]). | **needs-review** | Completed by Gemini. 47 generator tests passing; full test suite 400 passing, 4 skipped. See report [`docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md). |
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
diff --git i/scripts/generate_name_pool.py w/scripts/generate_name_pool.py
index b7d1fdf..8f301ec 100755
--- i/scripts/generate_name_pool.py
+++ w/scripts/generate_name_pool.py
@@ -211,6 +211,25 @@ def slugify_profile(profile: str) -> str:
     return s or "default"
 
 
+ADAPTER_THINKING_MAP: dict[str, Optional[bool]] = {
+    "auto": None,
+    "on": True,
+    "off": False,
+}
+
+
+def parse_adapter_thinking(thinking_str: Optional[str]) -> Optional[bool]:
+    """Map --adapter-thinking {auto,on,off} to None, True, False."""
+    if thinking_str is None:
+        return None
+    norm = thinking_str.strip().lower()
+    if norm not in ADAPTER_THINKING_MAP:
+        raise ValueError(
+            f"Invalid --adapter-thinking value {thinking_str!r}. Expected one of: auto, on, off."
+        )
+    return ADAPTER_THINKING_MAP[norm]
+
+
 class ShardLockManager:
     """Manages exclusive non-blocking file locks for a generation session.
 
@@ -417,6 +436,8 @@ def load_completed_cache(cache_path: Path) -> dict[tuple[int, str], CacheEntry]:
 
     first_backend: Optional[str] = None
     first_prompt_version: Optional[str] = None
+    first_thinking_seen: bool = False
+    first_thinking: Any = None
 
     with open(cache_path, "r", encoding="utf-8") as f:
         for line_no, line in enumerate(f, start=1):
@@ -453,6 +474,18 @@ def load_completed_cache(cache_path: Path) -> dict[tuple[int, str], CacheEntry]:
                         f"and '{first_prompt_version}' (line {line_no})."
                     )
 
+            bm_raw = record.get("backend_meta")
+            if isinstance(bm_raw, dict):
+                thinking_val = bm_raw.get("thinking_requested", None)
+                if not first_thinking_seen:
+                    first_thinking = thinking_val
+                    first_thinking_seen = True
+                elif (type(thinking_val), thinking_val) != (type(first_thinking), first_thinking):
+                    raise ValueError(
+                        f"Cache {cache_path} contains mixed thinking settings: found {thinking_val!r} "
+                        f"and {first_thinking!r} (line {line_no})."
+                    )
+
             try:
                 parsed = parse_json_array_response(resp_text)
             except ValueError:
@@ -687,9 +720,11 @@ def build_pool_from_cache(
             )
             sys.exit(1)
 
-        # 2. Consistency check across shards (mixed backends / prompt versions)
+        # 2. Consistency check across shards (mixed backends / prompt versions / thinking settings)
         first_backend: Optional[str] = None
         first_prompt_version: Optional[str] = None
+        first_thinking_seen: bool = False
+        first_thinking: Any = None
         all_entries: list[CacheEntry] = []
         shard_infos: list[dict[str, Any]] = []
 
@@ -712,6 +747,16 @@ def build_pool_from_cache(
                             f"Cache {p} contains mixed prompt versions: found '{entry.prompt_version}' "
                             f"and '{first_prompt_version}' in earlier shard."
                         )
+                if entry.backend_meta is not None:
+                    thinking_val = entry.backend_meta.get("thinking_requested", None)
+                    if not first_thinking_seen:
+                        first_thinking = thinking_val
+                        first_thinking_seen = True
+                    elif (type(thinking_val), thinking_val) != (type(first_thinking), first_thinking):
+                        raise ValueError(
+                            f"Cache {p} contains mixed thinking settings: found {thinking_val!r} "
+                            f"and {first_thinking!r} in earlier shard."
+                        )
                 all_entries.append(entry)
 
             entries = list(cdict.values())
@@ -806,6 +851,8 @@ def build_pool_from_cache(
 
         req_model: Optional[str] = None
         req_effort: Optional[str] = None
+        req_thinking: Optional[bool] = None
+        req_thinking_seen = False
         req_memory = False
         req_web_search = False
 
@@ -816,6 +863,9 @@ def build_pool_from_cache(
                     req_model = str(bm["model_requested"])
                 if req_effort is None and "effort_requested" in bm:
                     req_effort = str(bm["effort_requested"])
+                if not req_thinking_seen and "thinking_requested" in bm:
+                    req_thinking = bm["thinking_requested"]
+                    req_thinking_seen = True
                 if "memory_requested" in bm:
                     req_memory = bool(bm["memory_requested"])
                 if "web_search_requested" in bm:
@@ -829,6 +879,7 @@ def build_pool_from_cache(
                 "prompt_version": first_prompt_version or NAME_POOL_PROMPT_VERSION_COMMAND,
                 "requested_model": req_model or configured_model,
                 "requested_effort": req_effort or "low",
+                "requested_thinking": req_thinking,
                 "requested_memory": req_memory,
                 "requested_web_search": req_web_search,
                 "observed_models": agg_observed,
@@ -934,6 +985,8 @@ def build_pool_from_cache(
 
         req_model: Optional[str] = None
         req_effort: Optional[str] = None
+        req_thinking: Optional[bool] = None
+        req_thinking_seen = False
         req_memory = False
         req_web_search = False
 
@@ -944,6 +997,9 @@ def build_pool_from_cache(
                     req_model = str(bm["model_requested"])
                 if req_effort is None and "effort_requested" in bm:
                     req_effort = str(bm["effort_requested"])
+                if not req_thinking_seen and "thinking_requested" in bm:
+                    req_thinking = bm["thinking_requested"]
+                    req_thinking_seen = True
                 if "memory_requested" in bm:
                     req_memory = bool(bm["memory_requested"])
                 if "web_search_requested" in bm:
@@ -969,6 +1025,7 @@ def build_pool_from_cache(
             "prompt_version": NAME_POOL_PROMPT_VERSION_COMMAND,
             "requested_model": req_model or configured_model,
             "requested_effort": req_effort or "low",
+            "requested_thinking": req_thinking,
             "requested_memory": req_memory,
             "requested_web_search": req_web_search,
             "observed_models": observed_counts,
@@ -1306,6 +1363,7 @@ class CommandGenerationBackend(GenerationBackend):
         profile: str,
         model: str = "sonnet",
         effort: Optional[str] = "low",
+        thinking: Optional[bool] = None,
         timeout_s: int = 300,
         sigterm_wait_s: float = 10.0,
     ) -> None:
@@ -1313,6 +1371,7 @@ class CommandGenerationBackend(GenerationBackend):
         self.profile = profile
         self.model = model
         self.effort = effort
+        self.thinking = thinking
         self.timeout_s = timeout_s
         self.sigterm_wait_s = sigterm_wait_s
 
@@ -1331,7 +1390,7 @@ class CommandGenerationBackend(GenerationBackend):
             "profile": self.profile,
             "model": self.model,
             "effort": self.effort,
-            "thinking": None,
+            "thinking": self.thinking,
             "web_search": False,
             "memory": False,
             "headless": False,
@@ -1456,6 +1515,7 @@ class CommandGenerationBackend(GenerationBackend):
             model_id = str(model_obs or model_req or self.model)
             elapsed = float(resp_json.get("elapsed_s", 0.0))
             backend_meta = {k: v for k, v in resp_json.items() if k != "text"}
+            backend_meta.setdefault("thinking_requested", self.thinking)
             return GenerationResult(
                 text=str(resp_json.get("text", "")),
                 model_id=model_id,
@@ -1519,6 +1579,7 @@ def run_generation_loop(
     adapter_profile: Optional[str] = None,
     adapter_model: str = "sonnet",
     adapter_effort: Optional[str] = "low",
+    adapter_thinking: str = "auto",
     adapter_timeout: int = 300,
     pause_s: float = 3.0,
     shard: Optional[str] = None,
@@ -1616,6 +1677,7 @@ def run_generation_loop(
                     profile=adapter_profile,
                     model=adapter_model,
                     effort=adapter_effort,
+                    thinking=parse_adapter_thinking(adapter_thinking),
                     timeout_s=adapter_timeout,
                 )
 
@@ -1998,6 +2060,13 @@ def build_parser() -> argparse.ArgumentParser:
         default="low",
         help="Effort tier for command adapter: low, medium, high, extra, max (default: low).",
     )
+    parser.add_argument(
+        "--adapter-thinking",
+        type=str,
+        choices=["auto", "on", "off"],
+        default="auto",
+        help="Thinking mode control for command adapter: auto (null), on (true), off (false) (default: auto).",
+    )
     parser.add_argument(
         "--adapter-timeout",
         type=int,
@@ -2103,6 +2172,7 @@ def main() -> int:
             cmd_parts.extend(["--adapter-profile", shlex.quote(prof)])
             cmd_parts.extend(["--adapter-model", shlex.quote(args.adapter_model)])
             cmd_parts.extend(["--adapter-effort", shlex.quote(str(args.adapter_effort))])
+            cmd_parts.extend(["--adapter-thinking", shlex.quote(str(args.adapter_thinking))])
             if args.adapter_timeout != 300:
                 cmd_parts.extend(["--adapter-timeout", str(args.adapter_timeout)])
             if args.pause_s != 3.0:
@@ -2231,6 +2301,7 @@ def main() -> int:
             print(f"Command string:        {args.command or '[not set]'}")
             print(f"Adapter profile:       {args.adapter_profile or '[not set]'}")
             print(f"Adapter model:         {args.adapter_model}")
+            print(f"Adapter thinking:      {args.adapter_thinking}")
             print(f"Serial duration:       {serial_duration:.1f} s (@ {COMMAND_BACKEND_SECONDS_PER_CALL:.1f}s/call)")
             if args.shard:
                 shard_i, shard_n = parse_shard_arg(args.shard)
@@ -2293,6 +2364,7 @@ def main() -> int:
         adapter_profile=args.adapter_profile,
         adapter_model=args.adapter_model,
         adapter_effort=args.adapter_effort,
+        adapter_thinking=args.adapter_thinking,
         adapter_timeout=args.adapter_timeout,
         pause_s=args.pause_s,
         shard=args.shard,
diff --git i/tests/stub_prompt_adapter.py w/tests/stub_prompt_adapter.py
index d0aac00..deadba9 100644
--- i/tests/stub_prompt_adapter.py
+++ w/tests/stub_prompt_adapter.py
@@ -53,6 +53,12 @@ def main() -> int:
         action="store_true",
         help="Spawn a child process that also hangs.",
     )
+    parser.add_argument(
+        "--record-payload-file",
+        type=str,
+        default=None,
+        help="Optional path to append received stdin JSON payload lines for inspection in tests.",
+    )
     args = parser.parse_args()
 
     # Read stdin
@@ -69,9 +75,16 @@ def main() -> int:
         print(json.dumps(out))
         return 2
 
+    if args.record_payload_file:
+        rec_path = Path(args.record_payload_file)
+        rec_path.parent.mkdir(parents=True, exist_ok=True)
+        with open(rec_path, "a", encoding="utf-8") as f:
+            f.write(json.dumps(payload) + "\n")
+
     scenario = args.scenario or payload.get("profile") or "success"
     model_req = payload.get("model", "sonnet")
     effort_req = payload.get("effort", "low")
+    thinking_req = payload.get("thinking", None)
 
     # Determine subfield from prompt if possible
     prompt = payload.get("prompt", "")
@@ -223,6 +236,7 @@ def main() -> int:
             "model_requested": model_req,
             "model_observed": "Sonnet 5.5 Low",
             "effort_requested": effort_req,
+            "thinking_requested": thinking_req,
             "memory_requested": False,
             "web_search_requested": False,
             "elapsed_s": 0.05,
@@ -246,6 +260,7 @@ def main() -> int:
             "model_requested": model_req,
             "model_observed": "Sonnet 5.5 Low",
             "effort_requested": effort_req,
+            "thinking_requested": thinking_req,
             "memory_requested": False,
             "web_search_requested": False,
             "elapsed_s": 0.05,
@@ -263,6 +278,7 @@ def main() -> int:
         "model_requested": model_req,
         "model_observed": "Sonnet 5.5 Low",
         "effort_requested": effort_req,
+        "thinking_requested": thinking_req,
         "memory_requested": False,
         "web_search_requested": False,
         "profile_used": payload.get("profile") or "Profile 1",
diff --git i/tests/test_generate_name_pool.py w/tests/test_generate_name_pool.py
index 47bf90e..c8d56f1 100644
--- i/tests/test_generate_name_pool.py
+++ w/tests/test_generate_name_pool.py
@@ -76,11 +76,6 @@ def guard_results_datagen_unmodified() -> Generator[None, None, None]:
 
     before = _snapshot()
     yield
-    # Clean up any default timestamped directories created in results/datagen by CLI tests that did not specify --run-id
-    if datagen_dir.exists():
-        for p in datagen_dir.iterdir():
-            if p.is_dir() and len(p.name) == 16 and p.name.endswith("Z") and "_" in p.name:
-                shutil.rmtree(p, ignore_errors=True)
     after = _snapshot()
     assert after == before, (
         f"results/datagen was modified by tests in test_generate_name_pool!\n"
@@ -456,7 +451,17 @@ def test_live_mode_refuses_without_confirm_and_without_key(tmp_path: Path) -> No
     env = dict(os.environ)
     env.pop("DEEPSEEK_API_KEY", None)
     res2 = subprocess.run(
-        [sys.executable, script, "--live", "--confirm", "--allow-peak"],
+        [
+            sys.executable,
+            script,
+            "--live",
+            "--confirm",
+            "--allow-peak",
+            "--cache-file",
+            str(tmp_path / "raw.jsonl"),
+            "--lock-dir",
+            str(tmp_path / "locks"),
+        ],
         capture_output=True,
         text=True,
         env=env,
@@ -466,12 +471,20 @@ def test_live_mode_refuses_without_confirm_and_without_key(tmp_path: Path) -> No
     assert "Traceback" not in res2.stderr
 
 
-def test_offline_fake_refuses_default_output_path() -> None:
+def test_offline_fake_refuses_default_output_path(tmp_path: Path) -> None:
     """Verify offline-fake refuses to overwrite default tracked path data/synthetic/cs_concept_names.json."""
     script = str(Path("scripts/generate_name_pool.py").resolve())
 
     res = subprocess.run(
-        [sys.executable, script, "--offline-fake"],
+        [
+            sys.executable,
+            script,
+            "--offline-fake",
+            "--cache-file",
+            str(tmp_path / "raw.jsonl"),
+            "--lock-dir",
+            str(tmp_path / "locks"),
+        ],
         capture_output=True,
         text=True,
     )
@@ -661,6 +674,7 @@ def test_command_backend_success_e2e(tmp_path: Path) -> None:
     stub = str(Path("tests/stub_prompt_adapter.py").resolve())
     pool_path = tmp_path / "claude_pool.json"
     cache_path = tmp_path / "raw.jsonl"
+    lock_dir = tmp_path / "locks"
 
     cmd_str = f"{sys.executable} {stub} --scenario success"
     res = subprocess.run(
@@ -685,6 +699,8 @@ def test_command_backend_success_e2e(tmp_path: Path) -> None:
             str(pool_path),
             "--cache-file",
             str(cache_path),
+            "--lock-dir",
+            str(lock_dir),
         ],
         capture_output=True,
         text=True,
@@ -701,6 +717,7 @@ def test_command_backend_success_e2e(tmp_path: Path) -> None:
     assert meta["prompt_version"] == "np1w"
     assert meta["requested_model"] == "sonnet"
     assert meta["requested_effort"] == "low"
+    assert meta["requested_thinking"] is None
     assert meta["requested_memory"] is False
     assert meta["requested_web_search"] is False
     assert "Sonnet 5.5 Low" in meta["observed_models"]
@@ -891,6 +908,7 @@ def test_stop_and_resume_after_rate_limit(tmp_path: Path) -> None:
     state_file = tmp_path / "state.txt"
     cache_path = tmp_path / "raw.jsonl"
     pool_path = tmp_path / "pool.json"
+    lock_dir = tmp_path / "locks"
 
     cmd1 = f"{sys.executable} {stub} --scenario rate_limit_after_n --state-file {state_file} --limit-n 2"
 
@@ -917,6 +935,8 @@ def test_stop_and_resume_after_rate_limit(tmp_path: Path) -> None:
             str(pool_path),
             "--cache-file",
             str(cache_path),
+            "--lock-dir",
+            str(lock_dir),
         ],
         capture_output=True,
         text=True,
@@ -952,6 +972,8 @@ def test_stop_and_resume_after_rate_limit(tmp_path: Path) -> None:
             str(pool_path),
             "--cache-file",
             str(cache_path),
+            "--lock-dir",
+            str(lock_dir),
         ],
         capture_output=True,
         text=True,
@@ -1696,17 +1718,18 @@ def test_profile_lock_mutual_exclusion(tmp_path: Path) -> None:
     profile_name = "Profile 24"
     profile_slug = slugify_profile(profile_name)  # "profile_24"
     profile_lock_file = lock_dir / f"{profile_slug}.lock"
+    ready_file = tmp_path / "profile_lock.ready"
 
     stub = str(Path("tests/stub_prompt_adapter.py").resolve())
 
-    # Helper process holds exclusive lock on profile_24.lock
-    helper_code = f"""import fcntl, os, time
+    # Helper process holds exclusive lock on profile_24.lock and signals readiness via ready_file
+    helper_code = f"""import fcntl, os, pathlib, time
 fd = os.open({repr(str(profile_lock_file))}, os.O_CREAT | os.O_RDWR)
 fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
-time.sleep(3)
+pathlib.Path({repr(str(ready_file))}).write_text("ready", encoding="utf-8")
+time.sleep(5)
 """
     p_helper = subprocess.Popen([sys.executable, "-c", helper_code])
-    time.sleep(0.3)
 
     cmd = [
         sys.executable,
@@ -1734,6 +1757,12 @@ time.sleep(3)
     ]
 
     try:
+        deadline = time.monotonic() + 5.0
+        while not ready_file.exists():
+            if time.monotonic() >= deadline:
+                pytest.fail(f"Timed out after 5.0s waiting for lock helper ready file: {ready_file}")
+            time.sleep(0.02)
+
         res = subprocess.run(cmd, capture_output=True, text=True)
         assert res.returncode == 1
         assert "is locked by another process" in res.stderr
@@ -1925,113 +1954,112 @@ def test_cli_verify_merged_success_and_tampered_cache(tmp_path: Path) -> None:
         build_pool_from_cache,
     )
 
+    script = str(Path("scripts/generate_name_pool.py").resolve())
     r1_id = f"_test_verify_merge_{uuid.uuid4().hex[:8]}_1"
     r2_id = f"_test_verify_merge_{uuid.uuid4().hex[:8]}_2"
-    datagen_base = Path("results/datagen")
+    datagen_base = tmp_path / "results" / "datagen"
     c1_dir = datagen_base / r1_id
     c2_dir = datagen_base / r2_id
     c1 = c1_dir / "raw_responses.jsonl"
     c2 = c2_dir / "raw_responses.jsonl"
 
-    try:
-        c1_dir.mkdir(parents=True, exist_ok=True)
-        c2_dir.mkdir(parents=True, exist_ok=True)
+    c1_dir.mkdir(parents=True, exist_ok=True)
+    c2_dir.mkdir(parents=True, exist_ok=True)
 
-        names1 = [f"verify_synth_concept_a_{i:03d}" for i in range(1, 25)]
-        e1 = CacheEntry(
-            round=1,
-            subfield="algorithms",
-            subfield_idx=0,
-            request_system="",
-            request_user="",
-            response_text=json.dumps(names1),
-            model_id="test",
-            token_usage={},
-            timestamp_utc="2026-10-11T00:00:00Z",
-            retries=0,
-            latency_s=0.1,
-            parsed_names=names1,
-            backend="deepseek",
-            prompt_version="np1",
-        )
-        names2 = [f"verify_synth_concept_b_{i:03d}" for i in range(1, 25)]
-        e2 = CacheEntry(
-            round=1,
-            subfield="data_structures",
-            subfield_idx=1,
-            request_system="",
-            request_user="",
-            response_text=json.dumps(names2),
-            model_id="test",
-            token_usage={},
-            timestamp_utc="2026-10-11T00:00:00Z",
-            retries=0,
-            latency_s=0.1,
-            parsed_names=names2,
-            backend="deepseek",
-            prompt_version="np1",
-        )
-        append_cache_record(c1, e1)
-        append_cache_record(c2, e2)
+    names1 = [f"verify_synth_concept_a_{i:03d}" for i in range(1, 25)]
+    e1 = CacheEntry(
+        round=1,
+        subfield="algorithms",
+        subfield_idx=0,
+        request_system="",
+        request_user="",
+        response_text=json.dumps(names1),
+        model_id="test",
+        token_usage={},
+        timestamp_utc="2026-10-11T00:00:00Z",
+        retries=0,
+        latency_s=0.1,
+        parsed_names=names1,
+        backend="deepseek",
+        prompt_version="np1",
+    )
+    names2 = [f"verify_synth_concept_b_{i:03d}" for i in range(1, 25)]
+    e2 = CacheEntry(
+        round=1,
+        subfield="data_structures",
+        subfield_idx=1,
+        request_system="",
+        request_user="",
+        response_text=json.dumps(names2),
+        model_id="test",
+        token_usage={},
+        timestamp_utc="2026-10-11T00:00:00Z",
+        retries=0,
+        latency_s=0.1,
+        parsed_names=names2,
+        backend="deepseek",
+        prompt_version="np1",
+    )
+    append_cache_record(c1, e1)
+    append_cache_record(c2, e2)
 
-        pool_merged = tmp_path / "pool_merged.json"
-        build_pool_from_cache(
-            cache_path=[c1, c2],
-            output_path=pool_merged,
-            generator_kind="deepseek",
-            configured_model="deepseek-flash",
-            seed=42,
-            run_ids=[r1_id, r2_id],
-            allow_fake=True,
-            is_merged=True,
-            min_required_names=10,
-        )
+    pool_merged = tmp_path / "pool_merged.json"
+    build_pool_from_cache(
+        cache_path=[c1, c2],
+        output_path=pool_merged,
+        generator_kind="deepseek",
+        configured_model="deepseek-flash",
+        seed=42,
+        run_ids=[r1_id, r2_id],
+        allow_fake=True,
+        is_merged=True,
+        min_required_names=10,
+    )
 
-        # 1. Success path: verify passes
-        res_ok = subprocess.run(
-            [
-                sys.executable,
-                "scripts/generate_name_pool.py",
-                "--verify",
-                "--output",
-                str(pool_merged),
-                "--merge-run-ids",
-                f"{r1_id},{r2_id}",
-                "--allow-fake",
-                "--min-required-names",
-                "10",
-            ],
-            capture_output=True,
-            text=True,
-        )
-        assert res_ok.returncode == 0, f"Verify failed unexpectedly: {res_ok.stderr}"
-        assert "Pool verification PASSED" in res_ok.stdout
+    # 1. Success path: verify passes
+    res_ok = subprocess.run(
+        [
+            sys.executable,
+            script,
+            "--verify",
+            "--output",
+            str(pool_merged),
+            "--merge-run-ids",
+            f"{r1_id},{r2_id}",
+            "--allow-fake",
+            "--min-required-names",
+            "10",
+        ],
+        cwd=tmp_path,
+        capture_output=True,
+        text=True,
+    )
+    assert res_ok.returncode == 0, f"Verify failed unexpectedly: {res_ok.stderr}"
+    assert "Pool verification PASSED" in res_ok.stdout
 
-        # 2. Tampered cache path: append a line to one cache, assert it fails with SHA256 mismatch
-        with open(c1, "a", encoding="utf-8") as f:
-            f.write('{"tampered": true}\n')
+    # 2. Tampered cache path: append a line to one cache, assert it fails with SHA256 mismatch
+    with open(c1, "a", encoding="utf-8") as f:
+        f.write('{"tampered": true}\n')
 
-        res_tampered = subprocess.run(
-            [
-                sys.executable,
-                "scripts/generate_name_pool.py",
-                "--verify",
-                "--output",
-                str(pool_merged),
-                "--merge-run-ids",
-                f"{r1_id},{r2_id}",
-                "--allow-fake",
-                "--min-required-names",
-                "10",
-            ],
-            capture_output=True,
-            text=True,
-        )
-        assert res_tampered.returncode == 1
-        assert f"Cache SHA256 mismatch for run_id '{r1_id}'" in res_tampered.stderr
-    finally:
-        shutil.rmtree(c1_dir, ignore_errors=True)
-        shutil.rmtree(c2_dir, ignore_errors=True)
+    res_tampered = subprocess.run(
+        [
+            sys.executable,
+            script,
+            "--verify",
+            "--output",
+            str(pool_merged),
+            "--merge-run-ids",
+            f"{r1_id},{r2_id}",
+            "--allow-fake",
+            "--min-required-names",
+            "10",
+        ],
+        cwd=tmp_path,
+        capture_output=True,
+        text=True,
+    )
+    assert res_tampered.returncode == 1
+    assert f"Cache SHA256 mismatch for run_id '{r1_id}'" in res_tampered.stderr
 
 
 def test_timeout_kill_sigterm_ignored_and_grandchild_killed(tmp_path: Path) -> None:
@@ -2312,3 +2340,295 @@ def test_merged_meta_fidelity_requested_fields(tmp_path: Path) -> None:
     assert meta.get("requested_web_search") is True
 
 
+# ===========================================================================
+# 12. FIX-015 Explicit Adapter Thinking Control Tests
+# ===========================================================================
+
+def test_adapter_thinking_payload_and_meta_e2e(tmp_path: Path) -> None:
+    """Verify via real CLI and stub_prompt_adapter that --adapter-thinking {auto,on,off}:
+    1. Sends null (None), true (True), false (False) in the stdin payload received by the stub.
+    2. Records thinking_requested in each cache record's backend_meta.
+    3. Records requested_thinking in pool meta for both single-run and merged pools.
+    """
+    from scripts.generate_name_pool import build_pool_from_cache
+
+    script = str(Path("scripts/generate_name_pool.py").resolve())
+    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
+    lock_dir = tmp_path / "locks"
+
+    cases: list[tuple[str | None, bool | None]] = [
+        (None, None),      # default (auto)
+        ("auto", None),
+        ("on", True),
+        ("off", False),
+    ]
+
+    for idx, (flag_val, expected_val) in enumerate(cases):
+        case_dir = tmp_path / f"case_{idx}_{flag_val or 'default'}"
+        payload_log = case_dir / "payloads.jsonl"
+        cache_file = case_dir / "raw_responses.jsonl"
+        pool_file = case_dir / "pool.json"
+
+        cmd_str = f"{sys.executable} {stub} --scenario success --record-payload-file {payload_log}"
+        cli_args = [
+            sys.executable,
+            script,
+            "--live",
+            "--confirm",
+            "--backend",
+            "command",
+            "--command",
+            cmd_str,
+            "--adapter-profile",
+            f"prof_{idx}",
+            "--adapter-model",
+            "sonnet-5",
+            "--pause-s",
+            "0",
+            "--target-names",
+            "30",
+            "--max-calls",
+            "1",
+            "--output",
+            str(pool_file),
+            "--cache-file",
+            str(cache_file),
+            "--lock-dir",
+            str(lock_dir),
+        ]
+        if flag_val is not None:
+            cli_args.extend(["--adapter-thinking", flag_val])
+
+        res = subprocess.run(cli_args, capture_output=True, text=True)
+        assert res.returncode == 0, f"CLI failed for {flag_val}: {res.stderr}"
+        assert payload_log.exists(), f"Stub did not write payload log for {flag_val}"
+
+        # 1. Check exact payload received by stub_prompt_adapter
+        payload_lines = [ln for ln in payload_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
+        assert len(payload_lines) == 1
+        received_payload = json.loads(payload_lines[0])
+        assert "thinking" in received_payload
+        assert received_payload["thinking"] is expected_val
+        assert received_payload["model"] == "sonnet-5"
+
+        # 2. Check cache record backend_meta["thinking_requested"]
+        cache_lines = [ln for ln in cache_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
+        assert len(cache_lines) == 1
+        cache_rec = json.loads(cache_lines[0])
+        assert "backend_meta" in cache_rec
+        assert "thinking_requested" in cache_rec["backend_meta"]
+        assert cache_rec["backend_meta"]["thinking_requested"] is expected_val
+
+        # 3. Check single-run pool meta["requested_thinking"]
+        pool_data = json.loads(pool_file.read_text(encoding="utf-8"))
+        assert "requested_thinking" in pool_data["meta"]
+        assert pool_data["meta"]["requested_thinking"] is expected_val
+        assert pool_data["meta"]["requested_model"] == "sonnet-5"
+
+    # 4. Check merged pool meta["requested_thinking"] across two shards run via CLI with --adapter-thinking off
+    s1_cache = tmp_path / "merge_off_s1" / "raw_responses.jsonl"
+    s2_cache = tmp_path / "merge_off_s2" / "raw_responses.jsonl"
+    s1_payload = tmp_path / "merge_off_s1" / "payload.jsonl"
+    s2_payload = tmp_path / "merge_off_s2" / "payload.jsonl"
+
+    for shard_idx, (scache, spayload) in enumerate([(s1_cache, s1_payload), (s2_cache, s2_payload)], start=1):
+        res_s = subprocess.run(
+            [
+                sys.executable,
+                script,
+                "--live",
+                "--confirm",
+                "--backend",
+                "command",
+                "--command",
+                f"{sys.executable} {stub} --scenario success --record-payload-file {spayload}",
+                "--adapter-profile",
+                f"Profile {23 + shard_idx}",
+                "--adapter-model",
+                "sonnet-5",
+                "--adapter-thinking",
+                "off",
+                "--shard",
+                f"{shard_idx}/2",
+                "--run-id",
+                f"s5off-s{shard_idx}of2",
+                "--pause-s",
+                "0",
+                "--stagger-s",
+                "0",
+                "--target-names",
+                "30",
+                "--max-calls",
+                "1",
+                "--output",
+                str(tmp_path / "unused_shard_out.json"),
+                "--cache-file",
+                str(scache),
+                "--lock-dir",
+                str(lock_dir),
+            ],
+            capture_output=True,
+            text=True,
+        )
+        assert res_s.returncode == 0, f"Shard {shard_idx} failed: {res_s.stderr}"
+
+    merged_out = tmp_path / "merged_off_pool.json"
+    merged_res = build_pool_from_cache(
+        cache_path=[s1_cache, s2_cache],
+        output_path=merged_out,
+        generator_kind="command",
+        configured_model="sonnet-5",
+        run_ids=["s5off-s1of2", "s5off-s2of2"],
+        allow_fake=True,
+        is_merged=True,
+        min_required_names=20,
+    )
+    assert merged_res["meta"]["requested_thinking"] is False
+    assert merged_res["meta"]["requested_model"] == "sonnet-5"
+
+
+def test_merge_refuses_mixed_thinking_settings(tmp_path: Path) -> None:
+    """Verify that merging caches (or loading a single cache) with different thinking_requested
+    values raises ValueError containing 'mixed thinking settings'."""
+    from scripts.generate_name_pool import (
+        CacheEntry,
+        CommandGenerationBackend,
+        append_cache_record,
+        build_pool_from_cache,
+        load_completed_cache,
+    )
+
+    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
+
+    def _make_shard_cache(name: str, subfield: str, sf_idx: int, thinking_val: bool | None) -> Path:
+        payload_log = tmp_path / name / "payload.jsonl"
+        be = CommandGenerationBackend(
+            command=f"{sys.executable} {stub} --scenario success --record-payload-file {payload_log}",
+            profile="Profile 24",
+            model="sonnet-5",
+            effort="low",
+            thinking=thinking_val,
+        )
+        gen_res = be.complete(
+            subfield=subfield,
+            round_num=1,
+            previous_names=[],
+            system_prompt="",
+            user_prompt="",
+        )
+        assert gen_res.ok is True
+        assert gen_res.backend_meta is not None
+        assert gen_res.backend_meta["thinking_requested"] is thinking_val
+
+        cpath = tmp_path / name / "raw_responses.jsonl"
+        entry = CacheEntry(
+            round=1,
+            subfield=subfield,
+            subfield_idx=sf_idx,
+            request_system="",
+            request_user="prompt",
+            response_text=gen_res.text,
+            model_id=gen_res.model_id,
+            token_usage=gen_res.token_usage,
+            timestamp_utc="2026-10-11T12:00:00Z",
+            retries=0,
+            latency_s=gen_res.latency_s,
+            parsed_names=json.loads(gen_res.text),
+            backend="command",
+            prompt_version="np1w",
+            backend_meta=gen_res.backend_meta,
+            shard="1/2",
+        )
+        append_cache_record(cpath, entry)
+        return cpath
+
+    c_off = _make_shard_cache("shard_off", "algorithms", 0, False)
+    c_on = _make_shard_cache("shard_on", "data_structures", 1, True)
+    c_auto = _make_shard_cache("shard_auto", "operating_systems", 2, None)
+
+    # 1. off (False) vs on (True) across merged caches
+    with pytest.raises(ValueError, match="mixed thinking settings"):
+        build_pool_from_cache(
+            cache_path=[c_off, c_on],
+            output_path=tmp_path / "out_off_on.json",
+            generator_kind="command",
+            configured_model="sonnet-5",
+            run_ids=["shard_off", "shard_on"],
+            allow_fake=True,
+            is_merged=True,
+            min_required_names=10,
+        )
+
+    # 2. off (False) vs auto (None) across merged caches
+    with pytest.raises(ValueError, match="mixed thinking settings"):
+        build_pool_from_cache(
+            cache_path=[c_off, c_auto],
+            output_path=tmp_path / "out_off_auto.json",
+            generator_kind="command",
+            configured_model="sonnet-5",
+            run_ids=["shard_off", "shard_auto"],
+            allow_fake=True,
+            is_merged=True,
+            min_required_names=10,
+        )
+
+    # 3. Single cache file mixing off (False) and on (True)
+    mixed_single = tmp_path / "mixed_single.jsonl"
+    mixed_single.write_text(
+        c_off.read_text(encoding="utf-8") + c_on.read_text(encoding="utf-8"),
+        encoding="utf-8",
+    )
+    with pytest.raises(ValueError, match="mixed thinking settings"):
+        load_completed_cache(mixed_single)
+
+
+def test_adapter_thinking_dry_run_and_print_shard_commands(tmp_path: Path) -> None:
+    """Verify --dry-run displays 'Adapter thinking:' and --print-shard-commands includes --adapter-thinking."""
+    script = str(Path("scripts/generate_name_pool.py").resolve())
+
+    # 1. --dry-run default (auto) and explicit (off, on)
+    for expected in ("auto", "off", "on"):
+        cmd = [
+            sys.executable,
+            script,
+            "--dry-run",
+            "--backend",
+            "command",
+            "--cache-file",
+            str(tmp_path / "raw.jsonl"),
+            "--lock-dir",
+            str(tmp_path / "locks"),
+        ]
+        if expected != "auto":
+            cmd.extend(["--adapter-thinking", expected])
+        res_dry = subprocess.run(cmd, capture_output=True, text=True)
+        assert res_dry.returncode == 0
+        assert f"Adapter thinking:      {expected}" in res_dry.stdout
+
+    # 2. --print-shard-commands default (auto) and explicit (off, on)
+    for expected in ("auto", "off", "on"):
+        cmd_psc = [
+            sys.executable,
+            script,
+            "--print-shard-commands",
+            "--shards",
+            "2",
+            "--profiles",
+            "Profile 24,Profile 26",
+            "--run-id-prefix",
+            "thinktest",
+            "--adapter-model",
+            "sonnet-5",
+        ]
+        if expected != "auto":
+            cmd_psc.extend(["--adapter-thinking", expected])
+        res_psc = subprocess.run(cmd_psc, capture_output=True, text=True)
+        assert res_psc.returncode == 0
+        lines = [ln.strip() for ln in res_psc.stdout.strip().splitlines() if ln.strip()]
+        assert len(lines) == 2
+        for ln in lines:
+            assert f"--adapter-thinking {expected}" in ln
+            assert "--adapter-model sonnet-5" in ln
+
+
+
```
