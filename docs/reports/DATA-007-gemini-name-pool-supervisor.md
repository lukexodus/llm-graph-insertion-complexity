# DATA-007 Report — Thesis-Side Supervisor for Sharded Name-Pool Generation

- **Task ID:** `DATA-007`
- **Agent:** `gemini`
- **Date:** 2026-10-11
- **Decision ID:** `[D-60]` (prompt specified `D-58`, which was already assigned to `STRAT-003-B` in commit `bd1e91f`, and `D-59` was assigned to `STRAT-004` in commit `7b52e0f`; `D-60` used per operator instruction)
- **Branch / Checkout:** `master` at `/home/lukexodus/projects/llm-graph-insertion-complexity` (committed directly on `master` and formatted patch generated in `patches/` per operator instruction)

---

## 0. Verification of Prompt Statements Against the Repo

1. **Decision ID `D-58`:** The prompt instructed *"Decision ID D-58 only. If D-58 is already in the log, stop and report."* Inspection of `docs/decisions/decision-log.md` showed `[D-58]` was already taken by `STRAT-003-B` (`bd1e91f`), and `[D-59]` was subsequently taken by `STRAT-004` (`7b52e0f`). Per operator instruction via interactive prompt, `DATA-007` uses **`[D-60]`**.
2. **Runbook path:** The prompt asked to check if `NAME-POOL-GENERATION-RUNBOOK.md` exists in the repo. It exists at `docs/guide/Name-pool generation runbook.md` (with spaces and mixed case in the filename) and was read in full. Note that Section 7 of that runbook still states *"HEAD has no special code for a locked profile: if another process holds Profile 24, the failures count toward exit 6"*, which is stale relative to `FIX-013`/`[D-54](3)` where adapter exit `15` (`profile_in_use`) was mapped to generator exit `7`.
3. **Generator exit codes (`3 = rate limit`, `7 = profile in use`):** Verified in `scripts/generate_name_pool.py` (lines 1711–1800) — confirmed `3` is `rate_limit` (adapter error `10`) and `7` is `profile_in_use` (adapter error `15`). Full exit-code table is given in Section 1 below.
4. **Merged pool metadata on mid-shard profile failover (`meta.profiles_used` and `meta.shards`):**
   - Section 3(2) of the prompt states: *"Failover on rate limit: 2 shards, 3 profiles; profile 1 rate-limits after K calls -> shard 1 restarts on profile 3, resumes from cache, finishes; merged pool records both profiles for shard 1 (`meta.profiles_used` and `meta.shards`)."*
   - **What is actually in `scripts/generate_name_pool.py`:** When shard 1 runs $K \ge 1$ calls on Profile 1 and then restarts and finishes on Spare Profile 3, shard 1's raw cache (`results/datagen/<prefix>-s1of2/raw_responses.jsonl`) **does** record `"profile_used": "<Profile 1>"` in `backend_meta` for the first $K$ records and `"profile_used": "<Profile 3>"` in `backend_meta` for the subsequent records, and the supervisor's `status.json` and `supervisor-log.jsonl` record both profiles. **However**, `build_pool_from_cache()` in `scripts/generate_name_pool.py` (lines 765–797 and 849) extracts only a single scalar `prof` per shard from the **first** cache entry (`if prof is None and "profile_used" in bm: prof = str(bm["profile_used"])`), stores `"profile": prof` (a single string, not a list) in `meta["shards"]`, and computes `meta["profiles_used"] = sorted({s["profile"] for s in shard_infos if s["profile"]})`.
   - Per Rule 0 (*"Do NOT modify `scripts/generate_name_pool.py`... If you believe the generator needs a change, stop and report it instead"*), `scripts/generate_name_pool.py` was left unmodified. If the APC wants `meta.shards[i]` and `meta.profiles_used` in `pool.json` to aggregate all `backend_meta.profile_used` values across all entries within a shard cache when mid-shard profile rotation occurs, a small follow-up in `scripts/generate_name_pool.py` lines 765–797 and 849 is needed.
5. **Process-group hierarchy (`start_new_session=True` in both supervisor and `CommandGenerationBackend`):** Because `CommandGenerationBackend.complete()` in `scripts/generate_name_pool.py` (line 1409) spawns `prompt-adapter` with `start_new_session=True`, the adapter and its browser children live in a separate process group from the shard `generate_name_pool.py` process. Consequently, sending `os.killpg(shard_proc.pid, SIGTERM)` alone would only kill `generate_name_pool.py` and orphan a running adapter subprocess. `_terminate_all_children()` in `scripts/name_pool_supervisor.py` therefore walks `/proc` (`/proc/<pid>/task/*/children` and `/proc/[0-9]*/stat`) to discover all descendant PIDs and PGIDs before sending `SIGTERM` and escalating to `SIGKILL`.

---

## 1. Complete Exit-Code Table for `scripts/generate_name_pool.py`

Derived directly from reading `scripts/generate_name_pool.py`:

| Generator Exit Code | Adapter Error / Trigger | Meaning in `scripts/generate_name_pool.py` | Supervisor Action in `scripts/name_pool_supervisor.py` |
| :---: | :--- | :--- | :--- |
| **`0`** | `ok: true` / target reached | Shard reached $\lceil \text{target\_names} / N \rceil$ valid names (or finished `--max-calls` loop in `--shard` mode; merged shortfall is checked in `--build-only --merge-run-ids`), or `--dry-run` / `--print-shard-commands` / `--build-only` / `--verify` succeeded. | Mark shard `state = "done"`. When all $N$ shards exit `0`, run `--build-only --merge-run-ids` then `--verify --merge-run-ids`. |
| **`1`** | Adapter error `2` (`bad_request`), `ShardLockManager` flock contention, CLI/validation/merge/verify error | Fatal configuration, lock, or validation failure: missing `--command` / `--adapter-profile` / `DEEPSEEK_API_KEY` / `--confirm`; `--shard` without `--run-id`; `ShardLockManager` `run_id` or `profile` lock held; adapter `bad_request` (`2`); duplicate parseable `(round, subfield)` across merged caches; merged valid names $< \text{min\_required\_names}$; or `--verify` failure. | Fatal: terminate all running shard process trees cleanly, preserve caches, log `"fatal_or_unknown_shard_exit"`, and exit `1` (`SUP_EXIT_ERROR`). |
| **`2`** | `argparse` CLI error | Invalid or unrecognized CLI arguments passed to `generate_name_pool.py`. | Fatal: terminate all running shard process trees cleanly, preserve caches, and exit `1` (`SUP_EXIT_ERROR`). |
| **`3`** | Adapter error `10` (`rate_limit`) | claude.ai usage limit reached on the active browser profile (prints `reset_time` to stderr, preserves cache). | Retire profile into cooldown for `--profile-cooldown-s` (default `18000` s), increment shard `restarts`, and restart shard on the next unassigned, non-cooling spare profile. |
| **`4`** | Adapter error `11` (`login_required`) | Browser profile session expired or Cloudflare/turnstile challenge presented. | Fatal: terminate all running shard process trees cleanly, preserve caches, and exit `1` (`SUP_EXIT_ERROR`). |
| **`5`** | Adapter error `14` (`model_mismatch`) | Observed model label in web UI did not match requested model. | Fatal: terminate all running shard process trees cleanly, preserve caches, and exit `1` (`SUP_EXIT_ERROR`). |
| **`6`** | `3` consecutive transient/parse failures | Three consecutive calls failed with adapter error `12` (`timeout`), `13` (`refusal`), `1` (`other` / non-JSON stdout), or unparseable JSON array response. | Fatal: terminate all running shard process trees cleanly, preserve caches, and exit `1` (`SUP_EXIT_ERROR`). |
| **`7`** | Adapter error `15` (`profile_in_use`) | Target browser profile is locked at the adapter level by another process; cache untouched. | Mark profile busy for `60` s (`PROFILE_BUSY_COOLDOWN_S`) without burning the 18000 s rate-limit cooldown, increment shard `restarts`, and restart shard on the next unassigned, non-cooling profile. |
| **Any other code** (e.g. `99`, `-9`) | Unexpected crash or signal | Unhandled exception or external signal killing shard process. | Fatal: terminate all running shard process trees cleanly, preserve caches, and exit `1` (`SUP_EXIT_ERROR`). |

### Supervisor Exit Codes (`scripts/name_pool_supervisor.py`)
- **`0` (`SUP_EXIT_OK`)**: All shards exited `0`, `--build-only --merge-run-ids` succeeded, and `--verify --merge-run-ids` passed (or `--dry-run` / `--status` succeeded).
- **`1` (`SUP_EXIT_ERROR`)**: Fatal/unknown shard exit code, `--max-restarts-per-shard` exceeded, `load_completed_cache()` raised `ValueError`, or final merge/verify failed.
- **`2` (`SUP_EXIT_USAGE`)**: Refused live launch without both `--live` and `--confirm`, or invalid CLI arguments (`k < N`, duplicate profiles, missing `--run-id-prefix`).
- **`3` (`SUP_EXIT_STALLED`)**: All candidate profiles were in cooldown and no profile became free within `--max-wait-s` (default `21600` s); caches are intact and resumable.
- **`4` (`SUP_EXIT_MAX_TOTAL_CALLS`)**: Total raw cache lines across all shards reached or exceeded `--max-total-calls` (default `600`).
- **`130` (`SUP_EXIT_SIGNAL`)**: Interrupted by `SIGINT` or `SIGTERM`; all child and descendant process groups terminated cleanly.

---

## 2. Summary of `/home/lukexodus/projects/claude-automator/RECON-parallel.md` (Q1–Q4)

`claude-automator`'s `prompt-adapter` is a strictly single-prompt, single-profile synchronous CLI with no reusable batch runner (`syllabot`'s async worker pool is tightly coupled to SQLite `jobs`/`topics` tables), and while `resolve_candidate_profiles("auto")` skips locked profiles before launch, it never rotates profiles mid-run when a rate-limit modal appears (returning exit `10` instead). Concurrent `prompt-adapter` processes on distinct explicit profiles are safe at the filesystem level via `ProfileLock` (`~/.config/claude-automator/locks/<slug>.lock`) and isolated `user_data_dir` directories, and at ~560–970 MB RSS per headed Chromium instance, 2–3 parallel shards fit well within the machine's 15 GiB RAM.

---

## 3. How I Know Each Test Can Fail (Line-by-Line Mutation Verification)

Each of the 11 tests in `tests/test_name_pool_supervisor.py` was verified by mutating the specific line in `scripts/name_pool_supervisor.py` that it depends on, running `pytest`, capturing the failure line, and restoring `scripts/name_pool_supervisor.py` (verified via SHA256 `440ce92a9c341354321ee040c98e1351e50b8b427615f064fd2cad339ed4aa91`):

1. **`test_happy_path_two_shards_merged_and_verified`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1227` (`merge_ids = ",".join(s.run_id for s in shards)`)
   - **Mutation:** `merge_ids = shards[0].run_id`
   - **Failing pytest output:**
     ```text
     E   assert 1 == 0
     FAILED tests/test_name_pool_supervisor.py::test_happy_path_two_shards_merged_and_verified
     ```
2. **`test_failover_on_rate_limit_to_spare_profile`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1005` (`elif rc in (GEN_EXIT_RATE_LIMIT, GEN_EXIT_PROFILE_IN_USE):`)
   - **Mutation:** `elif rc in (GEN_EXIT_PROFILE_IN_USE,):`
   - **Failing pytest output:**
     ```text
     E   assert 1 == 0
     FAILED tests/test_name_pool_supervisor.py::test_failover_on_rate_limit_to_spare_profile
     ```
3. **`test_profile_in_use_rotates_to_next_profile_with_short_cooldown`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1011` (`else PROFILE_BUSY_COOLDOWN_S`)
   - **Mutation:** `else float(args.profile_cooldown_s)`
   - **Failing pytest output:**
     ```text
     E   assert 18000.0 == 60.0
     FAILED tests/test_name_pool_supervisor.py::test_profile_in_use_rotates_to_next_profile_with_short_cooldown
     ```
4. **`test_all_profiles_cooling_stalled_exit_caches_intact`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1202` (`return SUP_EXIT_STALLED`)
   - **Mutation:** `return SUP_EXIT_ERROR`
   - **Failing pytest output:**
     ```text
     E   assert 1 == 3
     FAILED tests/test_name_pool_supervisor.py::test_all_profiles_cooling_stalled_exit_caches_intact
     ```
5. **`test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1088` (`return SUP_EXIT_ERROR`)
   - **Mutation:** `return SUP_EXIT_OK`
   - **Failing pytest output:**
     ```text
     E   assert 0 == 1
     FAILED tests/test_name_pool_supervisor.py::test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches
     ```
6. **`test_sigterm_propagation_kills_children_and_exits_130`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `972` (`return SUP_EXIT_SIGNAL`)
   - **Mutation:** `return SUP_EXIT_ERROR`
   - **Failing pytest output:**
     ```text
     E   AssertionError: assert 1 == 130
     E    +  where 1 = <Popen: returncode: 1 args: ['/usr/bin/python3', '/home/lukexodus/projects/l...>.returncode
     FAILED tests/test_name_pool_supervisor.py::test_sigterm_propagation_kills_children_and_exits_130
     ```
7. **`test_max_total_calls_stops_all_shards`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `1149` (`if total_calls > args.max_total_calls or (total_calls >= args.max_total_calls and not all_done):`)
   - **Mutation:** `if False:`
   - **Failing pytest output:**
     ```text
     E   assert 0 == 4
     FAILED tests/test_name_pool_supervisor.py::test_max_total_calls_stops_all_shards
     ```
8. **`test_status_cli_read_only`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `657` (`return print_status_from_state_dir(state_dir)`)
   - **Mutation:** `(state_dir / "dirty.txt").write_text("x"); return print_status_from_state_dir(state_dir)`
   - **Failing pytest output:**
     ```text
     E   AssertionError: --status modified files in tmp_path!
     FAILED tests/test_name_pool_supervisor.py::test_status_cli_read_only
     ```
9. **`test_refusal_without_live_and_confirm`**
   - **Line in `scripts/name_pool_supervisor.py`:** Line `737` (`return SUP_EXIT_USAGE`)
   - **Mutation:** `return SUP_EXIT_OK`
   - **Failing pytest output:**
     ```text
     E   AssertionError: assert 0 == 2
     FAILED tests/test_name_pool_supervisor.py::test_refusal_without_live_and_confirm
     ```
10. **`test_dry_run_prints_plan_and_launches_nothing`**
    - **Line in `scripts/name_pool_supervisor.py`:** Line `693` (`if args.dry_run:`)
    - **Mutation:** `if False:`
    - **Failing pytest output:**
      ```text
      E   assert 2 == 0
      FAILED tests/test_name_pool_supervisor.py::test_dry_run_prints_plan_and_launches_nothing
      ```
11. **`test_loader_value_error_stops_everything`**
    - **Line in `scripts/name_pool_supervisor.py`:** Line `1133` (`return SUP_EXIT_ERROR`)
    - **Mutation:** `return SUP_EXIT_OK`
    - **Failing pytest output:**
      ```text
      E   assert 0 == 1
      FAILED tests/test_name_pool_supervisor.py::test_loader_value_error_stops_everything
      ```

---

## 4. Test Suite & `ls -la results/datagen` Outputs

### `pytest -q`
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.0, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
testpaths: tests
plugins: instafail-0.5.0, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, inline-snapshot-0.32.6, typeguard-4.6.0, time-machine-3.5.0, anyio-4.15.1, hypothesis-6.167.1
collecting ... collected 502 items / 1 skipped

tests/test_bounded_bucket_strategy.py .................................. [  6%]
................................................                         [ 16%]
tests/test_brute_force_strategy.py .......s................              [ 21%]
tests/test_controllable_embedder.py ..................                   [ 24%]
tests/test_decision.py ...............                                   [ 27%]
tests/test_embedding_threshold_strategy.py ............................. [ 33%]
................                                                         [ 36%]
tests/test_generate_name_pool.py ....................................... [ 44%]
........                                                                 [ 46%]
tests/test_graph_representation.py ..................................... [ 53%]
..............                                                           [ 56%]
tests/test_harness.py ................                                   [ 59%]
tests/test_harness_embedding.py ..                                       [ 59%]
tests/test_live_guard.py ...........................                     [ 65%]
tests/test_llm.py ............                                           [ 67%]
tests/test_loader.py ..........................                          [ 72%]
tests/test_name_pool_supervisor.py ...........                           [ 74%]
tests/test_null_strategy.py .......s...............................      [ 82%]
tests/test_pilot.py ...............                                      [ 85%]
tests/test_schedule.py .....................                             [ 89%]
tests/test_scoring.py .......                                            [ 91%]
tests/test_strategy_interface.py ...........................s........... [ 99%]
.....                                                                    [100%]

================== 499 passed, 4 skipped in 129.18s (0:02:09) ==================
```

### `pytest -q tests/test_name_pool_supervisor.py`
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.0, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: instafail-0.5.0, case-1.5.3, requests-mock-1.12.1, cov-7.1.0, inline-snapshot-0.32.6, typeguard-4.6.0, time-machine-3.5.0, anyio-4.15.1, hypothesis-6.167.1
collecting ... collected 11 items

tests/test_name_pool_supervisor.py ...........                           [100%]

============================= 11 passed in 38.83s ==============================
```

### `ls -la results/datagen`
```text
total 0
drwxr-xr-x 1 lukexodus lukexodus  0 Oct 11 21:28 .
drwxr-xr-x 1 lukexodus lukexodus 24 Oct 11 19:43 ..
```

---

## 5. Verbatim `git status --short` and `git diff`

### `git status --short`
```text
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 A scripts/name_pool_supervisor.py
 M tests/stub_prompt_adapter.py
 A tests/test_name_pool_supervisor.py
?? docs/reports/DATA-007-gemini-name-pool-supervisor.md
```

### `git diff`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 9147730..4174a98 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -463,3 +463,14 @@ Reasoning: closes the latent stale-cache defect in direct `shortlist()` callers
 (7) Attribution to EraRAG vs study-specific design choices: the hyperplane-LSH projection with stored hyperplanes and `[s_min, s_max]` size-bounded split/merge lifecycle are adapted from EraRAG Algorithms 1 and 3 (Zhang et al., arXiv:2506.20963, §III-B, §III-C, §III-E). Because the paper does not specify how an oversize bucket is split or how adjacency is ordered for merging, the Gray-code rank interval ordering, deterministic midpoint bisection (`len // 2`), and 4-component neighbour rule are this study's specification choices rather than algorithms defined in the paper.
 (8) Thesis-text synchronisation flag for APC-A: thesis §3.2.5 and §3.4 currently state that $S_{\min}$ and $S_{\max}$ are fixed empirically on a small subset, do not mention hyperplane count $n_{\text{bits}}$, and do not describe the Gray-order interval representation, midpoint bisection, or the 4-component neighbour rule; Chapter 3 requires a synchronisation edit alongside Strategy 3's [D-55](7) to document a-priori parameter fixing per [D-35](5), the sensitivity grid, and the study-specific operationalisation of split and merge.
 Reasoning: provides a deterministic, O(log M)-lookup, zero-extra-dependency implementation of Strategy 4 adapted from EraRAG Algorithms 1 and 3 with strict `[s_min, s_max]` partition invariants, single-embedding-per-insert caching ([D-58]), pre-allocated matrix capacity ([D-50](1)), and rich operational diagnostics for RQ4 amortised-update and shortlist-recall analysis. Affects: `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket_strategy.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/STRAT-004-gemini-bounded-bucket.md`, STRAT-004, INFRA-007.
+
+**[D-60]** Thesis-side supervisor (`scripts/name_pool_supervisor.py`) for sharded name-pool generation, profile failover, and cache monitoring (DATA-007):
+(1) Why concurrency and failover live in the thesis supervisor rather than `claude-automator` (RECON Q1–Q4): Reconnaissance of `/home/lukexodus/projects/claude-automator/RECON-parallel.md` established four facts: (Q1) `claude-automator`'s `prompt-adapter` is strictly a single-prompt, single-profile CLI with no batch/pool runner, while `syllabot`'s async worker pool (`runner.py`) is tightly coupled to SQLite `jobs`/`topics` tables and syllabus markdown prompts; (Q2) `resolve_candidate_profiles("auto")` only picks an unlocked profile before launching the browser and never rotates onto a spare profile when a rate-limit modal appears mid-run (instead returning exit 10 `rate_limit`); (Q3) `ProfileLock` (`~/.config/claude-automator/locks/<slug>.lock`) and per-profile `user_data_dir` make concurrent `prompt-adapter` processes across distinct profiles safe at the OS/filesystem level; and (Q4) each headed Chromium context uses ~560–970 MB RSS, so $N = 2\text{--}3$ concurrent shards fit comfortably within the host's 15 GiB RAM. Consequently, multi-shard process management and spare-profile failover belong in a thesis-side supervisor (`scripts/name_pool_supervisor.py`) orchestrating `scripts/generate_name_pool.py --shard i/N`.
+(2) CLI surface and guards: `scripts/name_pool_supervisor.py` accepts `--shards N`, `--profiles "P1,...,Pk"` ($k \ge N$, duplicate names rejected; first $N$ are initial shard assignments `1..N`, remaining $k - N$ are spares in order), `--run-id-prefix`, `--command`, pass-through flags (`--adapter-model`, `--adapter-effort`, `--adapter-thinking`, `--adapter-timeout`, `--pause-s`, `--stagger-s`, `--target-names`, `--max-calls`, `--lock-dir`), supervisor controls (`--poll-s` default `30`, `--max-restarts-per-shard` default `20`, `--profile-cooldown-s` default `18000`, `--max-wait-s` default `21600`, `--max-total-calls` default `600`, `--state-dir` default `results/datagen/<prefix>-supervisor`, `--output` default `data/synthetic/cs_concept_names.json`), and mode flags (`--dry-run`, `--status`, `--live`, `--confirm`). Without both `--live` and `--confirm` (unless `--dry-run` or `--status` is set), the supervisor refuses to launch and exits with code `2`. `--dry-run` prints the initial profile assignment, spares, and the exact shard commands matching `generate_name_pool.py --print-shard-commands` and exits `0` without launching processes or creating files.
+(3) Generator exit-code mapping, profile rotation, and process-tree termination: Each shard runs in its own session (`start_new_session=True`) with output logged to `<state-dir>/shard-<i>.log`. Generator exit codes map as follows: `0` -> shard marked `"done"`; `3` (`rate_limit`, adapter exit `10`) -> retire the shard's profile into cooldown for `--profile-cooldown-s` seconds and restart the shard (`--run-id <prefix>-s<i>of<N>`, resuming from its existing cache) on the next unassigned, non-cooling profile (prioritizing fresh spares in `--profiles` order, then previously used profiles whose cooldown expired); `7` (`profile_in_use`, adapter exit `15`) -> mark the profile busy for `60` s (`PROFILE_BUSY_COOLDOWN_S`) without burning the long rate-limit cooldown, and restart on the next unassigned, non-cooling profile; any other exit code (`1` general/lock/bad_request, `2` usage, `4` `login_required`, `5` `model_mismatch`, `6` three consecutive transient/parse failures, or any unknown code such as `99`) -> terminate all active shard process trees, preserve caches, and exit `1`. Because `CommandGenerationBackend` in `generate_name_pool.py` spawns `prompt-adapter` in a separate session (`start_new_session=True`), `_terminate_all_children()` discovers all descendant PIDs and PGIDs via `/proc` before sending `SIGTERM`, waits up to 5 s, and escalates to `SIGKILL`. If no profile is free when a shard needs a restart, the supervisor waits until the earliest cooldown expires; if still waiting after `--max-wait-s` (default `21600` s), it stops cleanly with stalled exit code `3` (`SUP_EXIT_STALLED`). Exceeding `--max-restarts-per-shard` (default `20`) stops all shards and exits `1`. `SIGINT`/`SIGTERM` cleanly terminates all descendant process groups and exits `130`. When all $N$ shards exit `0`, the supervisor runs `generate_name_pool.py --build-only --merge-run-ids ...` followed by `--verify --merge-run-ids ...`, prints the pool meta summary, and exits `0` only if verification passes.
+(4) Unverified operator assumption on `--profile-cooldown-s`: The default `--profile-cooldown-s 18000` (5 hours) is an unverified operator assumption approximating claude.ai rolling window resets (explicitly labelled as an unverified operator assumption in `--help`, `--dry-run`, and this decision entry), since the generator prints the adapter's `reset_time` string to stderr rather than returning structured reset timestamps via its exit code.
+(5) State directory format and cache polling: Every `--poll-s` seconds, the supervisor reads each shard's `results/datagen/<run_id>/raw_responses.jsonl` using `load_completed_cache()` and `validate_and_dedupe_candidates()` imported from `scripts/generate_name_pool.py`. If `load_completed_cache()` raises `ValueError` (e.g., mixed backends, prompt versions, or thinking settings), or if total raw cache lines across all shards reach/exceed `--max-total-calls` (default `600`, exit code `4`), all shards are stopped cleanly. `<state-dir>/status.json` is written atomically via a temporary sibling file and `os.replace()` (recording `supervisor_pid`, `supervisor_state`, `updated_at_utc`, `total_calls`, `total_valid_names`, per-shard state/profile/pid/restarts/records/valid_names/last_exit_code, `cooling_profiles` with UTC expiry and remaining seconds, and `spares_available`). Lifecycle events (`supervisor_start`, `shard_launch`, `shard_exit`, `profile_cooldown`, `profile_reassigned`, `shard_restart`, `merge_start`, `merge_done`, `verify_start`, `verify_done`, `stalled`, `max_total_calls_exceeded`, `loader_error`, `signal_received`, `supervisor_stop`) are appended to `<state-dir>/supervisor-log.jsonl`. `--status` prints a read-only summary table from `status.json` and the shard caches without modifying any files.
+(6) Repo verification finding on merged pool profile metadata after mid-shard failover: When shard 1 fails over from profile P1 (after $K \ge 1$ successful calls) to spare profile P3, shard 1's `raw_responses.jsonl` records `"profile_used": "P1"` on the first $K$ records and `"profile_used": "P3"` on subsequent records, and `supervisor-log.jsonl`/`status.json` record the full rotation history. However, `build_pool_from_cache()` in `scripts/generate_name_pool.py` (lines 773–774 and 849) captures only the first cache record's `profile_used` into each shard's scalar `s["profile"]` field (`if prof is None and "profile_used" in bm`) and derives `meta["profiles_used"]` from `{s["profile"] for s in shard_infos}`. Per DATA-007 Rule 0 (`Do NOT modify scripts/generate_name_pool.py`), `generate_name_pool.py` was not modified; this finding is reported for the APC in case multi-profile per-shard aggregation in `build_pool_from_cache()` is desired in a follow-up.
+(7) Tests added: `tests/test_name_pool_supervisor.py` adds 11 offline integration tests using `tests/stub_prompt_adapter.py` and `tmp_path` (`test_happy_path_two_shards_merged_and_verified`, `test_failover_on_rate_limit_to_spare_profile`, `test_profile_in_use_rotates_to_next_profile_with_short_cooldown`, `test_all_profiles_cooling_stalled_exit_caches_intact`, `test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches`, `test_sigterm_propagation_kills_children_and_exits_130`, `test_max_total_calls_stops_all_shards`, `test_status_cli_read_only`, `test_refusal_without_live_and_confirm`, `test_dry_run_prints_plan_and_launches_nothing`, `test_loader_value_error_stops_everything`) guarded by the module-scoped autouse fixture `guard_results_datagen_unmodified`. Every test was verified to fail when its corresponding line in `scripts/name_pool_supervisor.py` is mutated. (Note: the DATA-007 prompt specified `D-58`, which was already used by STRAT-003-B, and `D-59` was used by STRAT-004; `D-60` is used per operator instruction.)
+Reasoning: provides unattended multi-shard execution with automatic spare-profile failover on claude.ai usage limits and profile locks, full process-tree cleanup across child sessions, atomic status telemetry, and automatic post-shard merge and verification without modifying `generate_name_pool.py` or `claude-automator`. Affects: `scripts/name_pool_supervisor.py`, `tests/test_name_pool_supervisor.py`, `tests/stub_prompt_adapter.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/DATA-007-gemini-name-pool-supervisor.md`, DATA-006, DATA-007.
+
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 311edd6..a9f0c9e 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -31,6 +31,7 @@ Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-1
 | DATA-004  | Generate the synthetic large-n concept-name sets (sweep sizes 50, 100, 200, 500, 1000, 2000 x 10 trials; CS domain, graph-level domain string "computer science", snake_case per D-21, no edges, fixed seed, cached, deduplicated, no overlap with any corpus node, >=2100 names; [D-35]). Embedding model choice is settled: local sentence-transformers all-MiniLM-L6-v2 on CPU. | **needs-review** | Completed by Claude Code. Script delivered; pool not yet generated; Luke runs the live step ([D-39]). 291 total tests collected (289 passing, 2 skipped). See report [`docs/reports/DATA-004-claude-code-name-pool-generator.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-004-claude-code-name-pool-generator.md). |
 | DATA-005  | Add secondary concept-name generation backend via external command adapter (claude-automator prompt-adapter), Contract v1, np1w prompt schema, weaker provenance controls, and DATA-004 independent review ([D-43]). | **done** | Accepted at APC review 2026-10-09; follow-ups FIX-011, DATA-006. Completed by Gemini. Adapter contract v1 specified in [`docs/context/prompt-adapter-contract.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/prompt-adapter-contract.md); command backend added to `scripts/generate_name_pool.py`; 25 generator tests passing; full test suite 298 passing, 2 skipped. See report [`docs/reports/DATA-005-gemini-claude-web-backend.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-005-gemini-claude-web-backend.md). |
 | DATA-006  | Implement shard parallelization and merge for `generate_name_pool.py` with FIX-012 folded in: `--shard I/N` partition by global subfield_idx, per-shard run-id and cache, ShardLockManager with flock on run_id and profile locks, `--stagger-s` sleep, `--print-shard-commands`, `--merge-run-ids` for multi-shard pool building with duplicate check across caches, merged meta with shards array and profiles_used, COMMAND_BACKEND_SECONDS_PER_CALL = 40.0, CommandBackend timeout SIGKILL strengthen, contract v1 label corrections to "Sonnet 5.5 Low", and D-44(4) corrections ([D-53]). | **needs-review** | Completed by kiro_default; repairs and full test coverage completed in FIX-013 ([D-54]). See reports [`docs/reports/DATA-006-kiro_default-name-pool-shards.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-006-kiro_default-name-pool-shards.md) and [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
+| DATA-007  | Implement thesis-side supervisor (`scripts/name_pool_supervisor.py`) for unattended sharded name-pool generation: launch N shard subprocesses in process groups, rotate rate-limited (exit 3) or busy (exit 7) profiles onto spare profiles with cooldown tracking, monitor caches via generator loader, write atomic `<state-dir>/status.json` and `supervisor-log.jsonl`, provide `--status` and `--dry-run`, handle `SIGINT`/`SIGTERM` (exit 130) with descendant process-tree termination, and automatically run `--build-only --merge-run-ids` and `--verify --merge-run-ids` on completion ([D-60]). | **needs-review** | Completed by Gemini. 11 supervisor tests passing (`tests/test_name_pool_supervisor.py`); full test suite 499 passing, 4 skipped. See report [`docs/reports/DATA-007-gemini-name-pool-supervisor.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-007-gemini-name-pool-supervisor.md). |
 | INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                                                         | **done** | Completed. Library locked as NetworkX via `ConceptGraph` wrapper ([D-22]); canonical edge direction locked as prereq -> dependent ([D-23]); dual-mapping implemented and verified without conflict against all 10 MEKG files. See report [`docs/reports/INFRA-001-claude-code-graph-representation.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-001-claude-code-graph-representation.md). |
 | INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **done** | Completed. Strategy contract, lifecycle, Embedder protocol, MeteredEmbedder, FakeEmbedder, and insert_node driver defined ([D-24], [D-25]). Conformance suite passes (62 tests). See spec [`docs/context/strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/strategy-interface.md) and report [`docs/reports/INFRA-002-gemini-strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-002-gemini-strategy-interface.md). |
 | INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **done** | Completed by Gemini. Discovers 12 corpora, loads into `ConceptGraph` and `GoldJudgmentSet` with strict parsing, canonical orientations via `oriented_edge` ([D-15], [D-19], [D-23]), and graph-level domain context table ([D-27]). All 12 graphs confirmed DAGs. See report [`docs/reports/INFRA-003-gemini-corpus-loader.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-003-gemini-corpus-loader.md). |
diff --git i/scripts/name_pool_supervisor.py w/scripts/name_pool_supervisor.py
new file mode 100644
index 0000000..0af6973
--- /dev/null
+++ w/scripts/name_pool_supervisor.py
@@ -0,0 +1,1319 @@
+#!/usr/bin/env python3
+"""scripts/name_pool_supervisor.py — Thesis-side supervisor for sharded name-pool generation.
+
+Launches N shard processes (scripts/generate_name_pool.py in --shard i/N mode) in
+their own process groups, monitors shard caches, rotates a shard onto an unassigned
+non-cooling spare profile on rate-limit (generator exit 3) or profile-in-use
+(generator exit 7), writes <state-dir>/status.json atomically and appends lifecycle
+events to <state-dir>/supervisor-log.jsonl, and runs --build-only --merge-run-ids
+followed by --verify --merge-run-ids when all shards complete with exit 0.
+"""
+
+from __future__ import annotations
+
+import argparse
+from dataclasses import dataclass, field
+from datetime import datetime, timedelta, timezone
+import json
+import os
+from pathlib import Path
+import shlex
+import signal
+import subprocess
+import sys
+import time
+from typing import Any, IO, Optional
+
+# Ensure src/ and repo root are on sys.path
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+if str(_REPO_ROOT / "src") not in sys.path:
+    sys.path.insert(0, str(_REPO_ROOT / "src"))
+if str(_REPO_ROOT) not in sys.path:
+    sys.path.insert(0, str(_REPO_ROOT))
+
+from scripts.generate_name_pool import (
+    DEFAULT_TRACKED_OUTPUT,
+    MAX_CALLS_DEFAULT,
+    MIN_REQUIRED_NAMES_FOR_VALIDATION,
+    TARGET_NAMES_DEFAULT,
+    load_benchmark_corpus_concepts,
+    load_completed_cache,
+    validate_and_dedupe_candidates,
+)
+
+_GENERATOR_SCRIPT = Path(__file__).resolve().parent / "generate_name_pool.py"
+
+# Generator exit codes (derived from scripts/generate_name_pool.py)
+GEN_EXIT_OK = 0
+GEN_EXIT_ERROR = 1
+GEN_EXIT_USAGE = 2
+GEN_EXIT_RATE_LIMIT = 3       # Adapter error 10 (rate_limit)
+GEN_EXIT_LOGIN_REQUIRED = 4   # Adapter error 11 (login_required)
+GEN_EXIT_MODEL_MISMATCH = 5   # Adapter error 14 (model_mismatch)
+GEN_EXIT_CONSEC_FAILURES = 6  # 3 consecutive transient/parse failures (errors 1, 12, 13, parse)
+GEN_EXIT_PROFILE_IN_USE = 7   # Adapter error 15 (profile_in_use)
+
+# Supervisor exit codes
+SUP_EXIT_OK = 0
+SUP_EXIT_ERROR = 1
+SUP_EXIT_USAGE = 2
+SUP_EXIT_STALLED = 3
+SUP_EXIT_MAX_TOTAL_CALLS = 4
+SUP_EXIT_SIGNAL = 130
+
+# Default supervisor timing and cap constants
+DEFAULT_POLL_S = 30.0
+DEFAULT_MAX_RESTARTS_PER_SHARD = 20
+DEFAULT_PROFILE_COOLDOWN_S = 18000.0  # 5 hours (unverified operator assumption)
+PROFILE_BUSY_COOLDOWN_S = 60.0        # 60 seconds on profile_in_use (generator exit 7)
+DEFAULT_MAX_WAIT_S = 21600.0          # 6 hours
+DEFAULT_MAX_TOTAL_CALLS = 600
+
+
+@dataclass
+class CoolingEntry:
+    profile: str
+    until_mono: float
+    until_utc: str
+    reason: str
+    cooldown_s: float
+
+
+@dataclass
+class ShardState:
+    shard_idx: int          # 1-based (1..N)
+    shard_total: int        # N
+    run_id: str             # <prefix>-s<i>of<N>
+    cache_path: Path        # results/datagen/<run_id>/raw_responses.jsonl
+    profile: Optional[str] = None
+    proc: Optional[subprocess.Popen[bytes]] = None
+    log_fh: Optional[IO[bytes]] = None
+    pid: Optional[int] = None
+    state: str = "pending"  # pending | running | waiting_for_profile | done | failed | stopped | stalled
+    restarts: int = 0
+    records: int = 0
+    valid_names: int = 0
+    last_exit_code: Optional[int] = None
+
+    @property
+    def shard_label(self) -> str:
+        return f"{self.shard_idx}/{self.shard_total}"
+
+
+def _now_utc_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def _append_supervisor_log(state_dir: Path, event: str, **fields: Any) -> None:
+    """Append a structured JSON event with UTC timestamp to <state-dir>/supervisor-log.jsonl."""
+    state_dir.mkdir(parents=True, exist_ok=True)
+    log_path = state_dir / "supervisor-log.jsonl"
+    record: dict[str, Any] = {
+        "timestamp_utc": _now_utc_iso(),
+        "event": event,
+    }
+    record.update(fields)
+    with open(log_path, "a", encoding="utf-8") as f:
+        f.write(json.dumps(record, ensure_ascii=False) + "\n")
+        f.flush()
+
+
+def _write_status_atomic(state_dir: Path, payload: dict[str, Any]) -> None:
+    """Atomically write <state-dir>/status.json via a temporary sibling file and os.replace."""
+    state_dir.mkdir(parents=True, exist_ok=True)
+    status_path = state_dir / "status.json"
+    tmp_path = state_dir / f".status.json.tmp.{os.getpid()}"
+    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
+    with open(tmp_path, "w", encoding="utf-8") as f:
+        f.write(content)
+        f.flush()
+        os.fsync(f.fileno())
+    os.replace(tmp_path, status_path)
+
+
+def build_shard_cli_tokens(
+    *,
+    shard_idx: int,
+    shards: int,
+    run_id_prefix: str,
+    profile: str,
+    command: Optional[str],
+    adapter_model: str = "sonnet",
+    adapter_effort: str = "low",
+    adapter_thinking: str = "auto",
+    adapter_timeout: int = 300,
+    pause_s: float = 3.0,
+    stagger_s: float = 20.0,
+    max_calls: int = MAX_CALLS_DEFAULT,
+    target_names: int = TARGET_NAMES_DEFAULT,
+    lock_dir: Optional[Path] = None,
+    for_display: bool = False,
+    generator_script: Path = _GENERATOR_SCRIPT,
+) -> list[str]:
+    """Construct the CLI argument list for a single shard using the exact flag set
+    of scripts/generate_name_pool.py --print-shard-commands (plus --lock-dir pass-through).
+    """
+    if for_display:
+        tokens = ["python3", "scripts/generate_name_pool.py", "--backend", "command"]
+    else:
+        tokens = [sys.executable, str(generator_script), "--backend", "command"]
+
+    if command:
+        tokens.extend(["--command", command])
+    tokens.extend(["--adapter-profile", profile])
+    tokens.extend(["--adapter-model", adapter_model])
+    tokens.extend(["--adapter-effort", str(adapter_effort)])
+    tokens.extend(["--adapter-thinking", str(adapter_thinking)])
+
+    if adapter_timeout != 300:
+        tokens.extend(["--adapter-timeout", str(adapter_timeout)])
+    if pause_s != 3.0:
+        tokens.extend(["--pause-s", str(pause_s)])
+    if stagger_s != 20.0:
+        tokens.extend(["--stagger-s", str(stagger_s)])
+    if max_calls != MAX_CALLS_DEFAULT:
+        tokens.extend(["--max-calls", str(max_calls)])
+    if target_names != TARGET_NAMES_DEFAULT:
+        tokens.extend(["--target-names", str(target_names)])
+    if lock_dir is not None:
+        tokens.extend(["--lock-dir", str(lock_dir)])
+
+    tokens.extend([
+        "--shard",
+        f"{shard_idx}/{shards}",
+        "--run-id",
+        f"{run_id_prefix}-s{shard_idx}of{shards}",
+        "--live",
+        "--confirm",
+    ])
+    return tokens
+
+
+def format_command_for_display(tokens: list[str]) -> str:
+    """Format a token list as a shell-quoted command line matching --print-shard-commands."""
+    out: list[str] = []
+    # Match generate_name_pool.py --print-shard-commands quoting style
+    i = 0
+    while i < len(tokens):
+        tok = tokens[i]
+        if tok in ("--command", "--adapter-profile", "--adapter-model", "--adapter-effort", "--adapter-thinking", "--lock-dir") and i + 1 < len(tokens):
+            out.append(tok)
+            out.append(shlex.quote(tokens[i + 1]))
+            i += 2
+        else:
+            out.append(tok)
+            i += 1
+    return " ".join(out)
+
+
+def _pid_alive(pid: int) -> bool:
+    """Return True if pid exists and is not a zombie."""
+    try:
+        os.kill(pid, 0)
+    except ProcessLookupError:
+        return False
+    except PermissionError:
+        return True
+    stat_path = Path(f"/proc/{pid}/stat")
+    if stat_path.exists():
+        try:
+            content = stat_path.read_text(encoding="utf-8")
+            rparen = content.rfind(")")
+            if rparen != -1 and content[rparen + 2 : rparen + 3] == "Z":
+                return False
+        except OSError:
+            pass
+    return True
+
+
+def _collect_descendant_pids_and_pgids(root_pids: list[int]) -> tuple[set[int], set[int]]:
+    """Discover all descendant PIDs and process group IDs of root_pids via /proc.
+
+    Needed because CommandGenerationBackend in generate_name_pool.py spawns the
+    adapter with start_new_session=True (putting the adapter and its children into
+    a separate process group from the shard generator process).
+    """
+    all_pids: set[int] = set(root_pids)
+    all_pgids: set[int] = set(root_pids)
+
+    # Build ppid -> children map and pid -> pgid map from /proc/[0-9]*/stat
+    children_map: dict[int, set[int]] = {}
+    pid_to_pgid: dict[int, int] = {}
+    proc_root = Path("/proc")
+    if proc_root.exists():
+        for entry in proc_root.iterdir():
+            if not entry.name.isdigit():
+                continue
+            pid = int(entry.name)
+            # Check /proc/<pid>/task/<tid>/children
+            task_dir = entry / "task"
+            if task_dir.exists():
+                try:
+                    for tdir in task_dir.iterdir():
+                        ch_file = tdir / "children"
+                        if ch_file.exists():
+                            for tok in ch_file.read_text(encoding="utf-8").split():
+                                if tok.isdigit():
+                                    children_map.setdefault(pid, set()).add(int(tok))
+                except OSError:
+                    pass
+            # Also parse /proc/<pid>/stat for ppid and pgrp
+            stat_file = entry / "stat"
+            if stat_file.exists():
+                try:
+                    raw = stat_file.read_text(encoding="utf-8")
+                    rparen = raw.rfind(")")
+                    if rparen != -1:
+                        rest = raw[rparen + 2 :].split()
+                        if len(rest) >= 3:
+                            ppid = int(rest[1])
+                            pgrp = int(rest[2])
+                            children_map.setdefault(ppid, set()).add(pid)
+                            pid_to_pgid[pid] = pgrp
+                except (OSError, ValueError):
+                    pass
+
+    queue = list(root_pids)
+    while queue:
+        curr = queue.pop(0)
+        try:
+            pg = os.getpgid(curr)
+            if pg > 1:
+                all_pgids.add(pg)
+        except OSError:
+            if curr in pid_to_pgid and pid_to_pgid[curr] > 1:
+                all_pgids.add(pid_to_pgid[curr])
+        for child_pid in children_map.get(curr, set()):
+            if child_pid not in all_pids:
+                all_pids.add(child_pid)
+                queue.append(child_pid)
+
+    return all_pids, all_pgids
+
+
+def _terminate_all_children(shards: list[ShardState], sigterm_wait_s: float = 5.0) -> None:
+    """Send SIGTERM to all active child process groups and descendant sessions, wait up to sigterm_wait_s, then SIGKILL."""
+    active: list[ShardState] = []
+    root_pids: list[int] = []
+    for s in shards:
+        if s.proc is not None and s.proc.poll() is None:
+            active.append(s)
+            root_pids.append(s.proc.pid)
+
+    if not active:
+        for s in shards:
+            if s.log_fh is not None:
+                try:
+                    s.log_fh.close()
+                except OSError:
+                    pass
+                s.log_fh = None
+        return
+
+    desc_pids, desc_pgids = _collect_descendant_pids_and_pgids(root_pids)
+
+    for pgid in desc_pgids:
+        try:
+            os.killpg(pgid, signal.SIGTERM)
+        except (ProcessLookupError, PermissionError, OSError):
+            pass
+    for pid in desc_pids:
+        try:
+            os.kill(pid, signal.SIGTERM)
+        except (ProcessLookupError, PermissionError, OSError):
+            pass
+
+    deadline = time.monotonic() + sigterm_wait_s
+    for s in active:
+        assert s.proc is not None
+        rem = max(0.0, deadline - time.monotonic())
+        try:
+            s.proc.wait(timeout=rem)
+        except subprocess.TimeoutExpired:
+            pass
+
+    while time.monotonic() < deadline:
+        if not any(_pid_alive(p) for p in desc_pids):
+            break
+        time.sleep(0.02)
+
+    # Re-scan any remaining live PIDs and escalate to SIGKILL
+    live_roots = [p for p in desc_pids if _pid_alive(p)]
+    if live_roots:
+        more_pids, more_pgids = _collect_descendant_pids_and_pgids(live_roots)
+        desc_pids.update(more_pids)
+        desc_pgids.update(more_pgids)
+
+    for pgid in desc_pgids:
+        try:
+            os.killpg(pgid, signal.SIGKILL)
+        except (ProcessLookupError, PermissionError, OSError):
+            pass
+    for pid in desc_pids:
+        if _pid_alive(pid):
+            try:
+                os.kill(pid, signal.SIGKILL)
+            except (ProcessLookupError, PermissionError, OSError):
+                pass
+
+    for s in active:
+        assert s.proc is not None
+        if s.proc.poll() is None:
+            try:
+                s.proc.wait(timeout=2.0)
+            except subprocess.TimeoutExpired:
+                pass
+
+    kill_deadline = time.monotonic() + 2.0
+    while time.monotonic() < kill_deadline:
+        if not any(_pid_alive(p) for p in desc_pids):
+            break
+        time.sleep(0.02)
+
+    for s in shards:
+        if s.log_fh is not None:
+            try:
+                s.log_fh.close()
+            except OSError:
+                pass
+            s.log_fh = None
+
+
+def _count_raw_cache_lines(cache_path: Path) -> int:
+    """Count non-empty lines in a shard's raw_responses.jsonl file."""
+    if not cache_path.exists():
+        return 0
+    count = 0
+    with open(cache_path, "r", encoding="utf-8") as f:
+        for line in f:
+            if line.strip():
+                count += 1
+    return count
+
+
+def print_status_from_state_dir(state_dir: Path) -> int:
+    """Read <state-dir>/status.json and shard caches (read-only) and print a formatted status table."""
+    status_path = state_dir / "status.json"
+    if not status_path.exists():
+        print(f"ERROR: Status file not found at {status_path}", file=sys.stderr)
+        return SUP_EXIT_ERROR
+
+    try:
+        with open(status_path, "r", encoding="utf-8") as f:
+            data = json.load(f)
+    except Exception as exc:
+        print(f"ERROR: Failed to read status file {status_path}: {exc}", file=sys.stderr)
+        return SUP_EXIT_ERROR
+
+    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()
+
+    print(f"=== Name-Pool Supervisor Status ({state_dir}) ===")
+    print(f"Run ID prefix:    {data.get('run_id_prefix', 'unknown')}")
+    print(f"Supervisor PID:   {data.get('supervisor_pid', 'none')}")
+    print(f"Supervisor state: {data.get('supervisor_state', 'unknown')}")
+    print(f"Updated at (UTC): {data.get('updated_at_utc', 'unknown')}")
+    print()
+
+    header = f"{'Shard':<7} {'Run ID':<22} {'Profile':<18} {'PID':<8} {'State':<20} {'Restarts':<8} {'Records':<8} {'Valid':<8} {'LastExit':<8}"
+    print(header)
+    print("-" * len(header))
+
+    total_live_records = 0
+    all_entries = []
+    for s in data.get("shards", []):
+        shard_lbl = str(s.get("shard", "?"))
+        rid = str(s.get("run_id", "?"))
+        prof = str(s.get("profile") or "-")
+        pid_str = str(s.get("pid") if s.get("pid") is not None else "-")
+        st = str(s.get("state", "?"))
+        restarts = int(s.get("restarts", 0))
+        last_exit = str(s.get("last_exit_code") if s.get("last_exit_code") is not None else "-")
+
+        cpath = Path(s.get("cache_path") or f"results/datagen/{rid}/raw_responses.jsonl")
+        rec_count = int(s.get("records", 0))
+        val_count = int(s.get("valid_names", 0))
+        if cpath.exists():
+            try:
+                cdict = load_completed_cache(cpath)
+                rec_count = _count_raw_cache_lines(cpath)
+                vnames, _, _ = validate_and_dedupe_candidates(
+                    list(cdict.values()), corpus_nodes, corpus_embeds
+                )
+                val_count = len(vnames)
+                all_entries.extend(cdict.values())
+            except Exception:
+                pass
+        total_live_records += rec_count
+        print(
+            f"{shard_lbl:<7} {rid:<22} {prof:<18} {pid_str:<8} {st:<20} "
+            f"{restarts:<8} {rec_count:<8} {val_count:<8} {last_exit:<8}"
+        )
+
+    print("-" * len(header))
+    global_valid = data.get("total_valid_names", 0)
+    if all_entries:
+        gv, _, _ = validate_and_dedupe_candidates(all_entries, corpus_nodes, corpus_embeds)
+        global_valid = len(gv)
+
+    print(f"Total calls (cache lines): {total_live_records} / {data.get('max_total_calls', DEFAULT_MAX_TOTAL_CALLS)}")
+    print(f"Total deduplicated valid:  {global_valid} / {data.get('target_names', TARGET_NAMES_DEFAULT)}")
+
+    cooling = data.get("cooling_profiles", [])
+    if cooling:
+        print("Cooling profiles:")
+        for c in cooling:
+            print(
+                f"  - {c.get('profile')}: reason={c.get('reason')}, "
+                f"until={c.get('until_utc')} (remaining={c.get('remaining_s')}s)"
+            )
+    else:
+        print("Cooling profiles: none")
+
+    return SUP_EXIT_OK
+
+
+def build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(
+        description="Thesis-side supervisor for sharded synthetic CS concept-name pool generation."
+    )
+    parser.add_argument(
+        "--shards",
+        type=int,
+        default=None,
+        help="Number of shards N (N >= 1).",
+    )
+    parser.add_argument(
+        "--profiles",
+        type=str,
+        default=None,
+        help="Comma-separated browser profiles 'P1,...,Pk' (k >= N; first N initial, rest spares in order).",
+    )
+    parser.add_argument(
+        "--run-id-prefix",
+        type=str,
+        default=None,
+        help="Run ID prefix for shards (<prefix>-s<i>of<N>).",
+    )
+    parser.add_argument(
+        "--command",
+        type=str,
+        default=None,
+        help="Command string for command backend (passed through to generate_name_pool.py).",
+    )
+    parser.add_argument(
+        "--adapter-model",
+        type=str,
+        default="sonnet",
+        help="Model identifier requested for command adapter (default: sonnet).",
+    )
+    parser.add_argument(
+        "--adapter-effort",
+        type=str,
+        default="low",
+        help="Effort tier for command adapter: low, medium, high, extra, max (default: low).",
+    )
+    parser.add_argument(
+        "--adapter-thinking",
+        type=str,
+        choices=["auto", "on", "off"],
+        default="auto",
+        help="Thinking mode control for command adapter: auto (null), on (true), off (false) (default: auto).",
+    )
+    parser.add_argument(
+        "--adapter-timeout",
+        type=int,
+        default=300,
+        help="Timeout in seconds for adapter conversation (default: 300).",
+    )
+    parser.add_argument(
+        "--pause-s",
+        type=float,
+        default=3.0,
+        help="Pause in seconds between command backend calls (default: 3.0).",
+    )
+    parser.add_argument(
+        "--stagger-s",
+        type=float,
+        default=20.0,
+        help="Seconds to stagger shard execution before first call (default: 20.0; 0 disables).",
+    )
+    parser.add_argument(
+        "--target-names",
+        type=int,
+        default=TARGET_NAMES_DEFAULT,
+        help=f"Target number of valid names to collect across shards (default: {TARGET_NAMES_DEFAULT}).",
+    )
+    parser.add_argument(
+        "--max-calls",
+        type=int,
+        default=MAX_CALLS_DEFAULT,
+        help=f"Maximum calls per shard invocation (default: {MAX_CALLS_DEFAULT}).",
+    )
+    parser.add_argument(
+        "--lock-dir",
+        type=Path,
+        default=None,
+        help="Directory for profile locks (passed through to generate_name_pool.py; default: results/datagen/.locks).",
+    )
+    parser.add_argument(
+        "--poll-s",
+        type=float,
+        default=DEFAULT_POLL_S,
+        help=f"Supervisor polling interval in seconds (default: {DEFAULT_POLL_S}).",
+    )
+    parser.add_argument(
+        "--max-restarts-per-shard",
+        type=int,
+        default=DEFAULT_MAX_RESTARTS_PER_SHARD,
+        help=f"Maximum restarts allowed per shard before aborting (default: {DEFAULT_MAX_RESTARTS_PER_SHARD}).",
+    )
+    parser.add_argument(
+        "--profile-cooldown-s",
+        type=float,
+        default=DEFAULT_PROFILE_COOLDOWN_S,
+        help=(
+            f"Seconds to retire a rate-limited profile before reuse "
+            f"(default: {int(DEFAULT_PROFILE_COOLDOWN_S)}; unverified operator assumption)."
+        ),
+    )
+    parser.add_argument(
+        "--max-wait-s",
+        type=float,
+        default=DEFAULT_MAX_WAIT_S,
+        help=(
+            f"Maximum seconds to wait when no profile is free before stopping with stalled exit code "
+            f"(default: {int(DEFAULT_MAX_WAIT_S)})."
+        ),
+    )
+    parser.add_argument(
+        "--max-total-calls",
+        type=int,
+        default=DEFAULT_MAX_TOTAL_CALLS,
+        help=(
+            f"Maximum total calls counted as cache lines across all shards; stop everything when exceeded "
+            f"(default: {DEFAULT_MAX_TOTAL_CALLS})."
+        ),
+    )
+    parser.add_argument(
+        "--state-dir",
+        type=Path,
+        default=None,
+        help="Supervisor state directory for status.json and supervisor-log.jsonl (default: results/datagen/<prefix>-supervisor).",
+    )
+    parser.add_argument(
+        "--output",
+        type=Path,
+        default=DEFAULT_TRACKED_OUTPUT,
+        help=f"Output pool JSON path (default: {DEFAULT_TRACKED_OUTPUT}).",
+    )
+    parser.add_argument(
+        "--min-required-names",
+        type=int,
+        default=None,
+        help=f"Optional override for minimum required valid names during merge/verify (default: {MIN_REQUIRED_NAMES_FOR_VALIDATION}).",
+    )
+    parser.add_argument(
+        "--generator-script",
+        type=Path,
+        default=_GENERATOR_SCRIPT,
+        help=argparse.SUPPRESS,
+    )
+    parser.add_argument(
+        "--dry-run",
+        action="store_true",
+        help="Print shard commands, initial profile assignment, and spares; launch nothing and create no files.",
+    )
+    parser.add_argument(
+        "--status",
+        action="store_true",
+        help="Read-only status table from <state-dir>/status.json and shard caches.",
+    )
+    parser.add_argument(
+        "--live",
+        action="store_true",
+        help="Enable live execution of shard subprocesses (requires --confirm).",
+    )
+    parser.add_argument(
+        "--confirm",
+        action="store_true",
+        help="Confirm live execution of shard subprocesses (requires --live).",
+    )
+    return parser
+
+
+def main(argv: Optional[list[str]] = None) -> int:
+    parser = build_parser()
+    args = parser.parse_args(argv)
+
+    # Resolve state_dir early for --status mode
+    if args.status:
+        if args.state_dir is not None:
+            state_dir = Path(args.state_dir)
+        elif args.run_id_prefix:
+            state_dir = Path("results/datagen") / f"{args.run_id_prefix}-supervisor"
+        else:
+            print("ERROR: --status requires either --state-dir or --run-id-prefix.", file=sys.stderr)
+            return SUP_EXIT_USAGE
+        return print_status_from_state_dir(state_dir)
+
+    # Validate required orchestration arguments for --dry-run and live execution
+    if args.shards is None or args.shards < 1:
+        print("ERROR: --shards N is required and must satisfy N >= 1.", file=sys.stderr)
+        return SUP_EXIT_USAGE
+
+    if not args.profiles:
+        print("ERROR: --profiles 'P1,...,Pk' is required.", file=sys.stderr)
+        return SUP_EXIT_USAGE
+
+    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
+    if len(profiles) < args.shards:
+        print(
+            f"ERROR: Profiles count ({len(profiles)}) must be >= shards count ({args.shards}).",
+            file=sys.stderr,
+        )
+        return SUP_EXIT_USAGE
+
+    if len(set(profiles)) != len(profiles):
+        print("ERROR: Duplicate profile names found in --profiles.", file=sys.stderr)
+        return SUP_EXIT_USAGE
+
+    if not args.run_id_prefix or not args.run_id_prefix.strip():
+        print("ERROR: --run-id-prefix is required.", file=sys.stderr)
+        return SUP_EXIT_USAGE
+
+    run_id_prefix = args.run_id_prefix.strip()
+    state_dir = Path(args.state_dir) if args.state_dir is not None else Path("results/datagen") / f"{run_id_prefix}-supervisor"
+    output_path = Path(args.output)
+    lock_dir = Path(args.lock_dir) if args.lock_dir is not None else Path("results/datagen/.locks")
+
+    initial_profiles = profiles[: args.shards]
+    spare_profiles = profiles[args.shards :]
+
+    # --dry-run mode: print shard commands, profile assignment, and spares; launch nothing
+    if args.dry_run:
+        print("=== DATA-007 Name-Pool Supervisor Plan (Dry Run) ===")
+        print(f"Shards (N):              {args.shards}")
+        print(f"Run ID prefix:           {run_id_prefix}")
+        print(f"Initial profiles (1..N): {', '.join(initial_profiles)}")
+        print(f"Spare profiles ({len(spare_profiles)}):      {', '.join(spare_profiles) if spare_profiles else '[none]'}")
+        print(f"State dir:               {state_dir}")
+        print(f"Output pool path:        {output_path}")
+        print(f"Poll interval:           {args.poll_s} s")
+        print(f"Max restarts / shard:    {args.max_restarts_per_shard}")
+        print(f"Profile cooldown:        {args.profile_cooldown_s} s (unverified operator assumption)")
+        print(f"Max wait (all cooling):  {args.max_wait_s} s")
+        print(f"Max total calls cap:     {args.max_total_calls}")
+        print("\n--- Initial Shard Commands ---")
+        for i in range(1, args.shards + 1):
+            prof = initial_profiles[i - 1]
+            display_tokens = build_shard_cli_tokens(
+                shard_idx=i,
+                shards=args.shards,
+                run_id_prefix=run_id_prefix,
+                profile=prof,
+                command=args.command,
+                adapter_model=args.adapter_model,
+                adapter_effort=args.adapter_effort,
+                adapter_thinking=args.adapter_thinking,
+                adapter_timeout=args.adapter_timeout,
+                pause_s=args.pause_s,
+                stagger_s=args.stagger_s,
+                max_calls=args.max_calls,
+                target_names=args.target_names,
+                lock_dir=args.lock_dir,
+                for_display=True,
+                generator_script=args.generator_script,
+            )
+            print(format_command_for_display(display_tokens))
+        print("\nDry run complete (nothing launched, no files created).")
+        return SUP_EXIT_OK
+
+    # Guard: require both --live and --confirm to launch (exit 2)
+    if not (args.live and args.confirm):
+        print(
+            "ERROR: Refusing to launch supervisor without both --live and --confirm (or pass --dry-run / --status).",
+            file=sys.stderr,
+        )
+        return SUP_EXIT_USAGE
+
+    if not args.command or not args.command.strip():
+        print("ERROR: --command is required for live execution.", file=sys.stderr)
+        return SUP_EXIT_USAGE
+
+    # Load benchmark corpora once for fast cache validation across polls
+    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()
+
+    shards: list[ShardState] = []
+    for i in range(1, args.shards + 1):
+        rid = f"{run_id_prefix}-s{i}of{args.shards}"
+        cpath = Path("results/datagen") / rid / "raw_responses.jsonl"
+        shards.append(
+            ShardState(
+                shard_idx=i,
+                shard_total=args.shards,
+                run_id=rid,
+                cache_path=cpath,
+                profile=initial_profiles[i - 1],
+                state="pending",
+            )
+        )
+
+    # Profile pool tracking
+    profile_order: dict[str, int] = {p: idx for idx, p in enumerate(profiles)}
+    times_assigned: dict[str, int] = {p: 0 for p in profiles}
+    cooling: dict[str, CoolingEntry] = {}
+
+    # Signal handling state
+    received_signal: list[int] = []
+
+    def _on_signal(signum: int, _frame: Any) -> None:
+        received_signal.append(signum)
+
+    prev_sigint = signal.signal(signal.SIGINT, _on_signal)
+    prev_sigterm = signal.signal(signal.SIGTERM, _on_signal)
+
+    def _expire_cooldowns(now_mono: float) -> None:
+        expired = [p for p, ce in cooling.items() if ce.until_mono <= now_mono]
+        for p in expired:
+            del cooling[p]
+
+    def _active_profiles() -> set[str]:
+        return {
+            s.profile
+            for s in shards
+            if s.profile is not None and s.state == "running"
+        }
+
+    def _pick_next_profile(now_mono: float) -> Optional[str]:
+        """Return the next unassigned, non-cooling profile, prioritizing fresh spares in order."""
+        _expire_cooldowns(now_mono)
+        in_use = _active_profiles()
+        candidates = [
+            p
+            for p in profiles
+            if p not in in_use and p not in cooling
+        ]
+        if not candidates:
+            return None
+        # Fresh spares (times_assigned == 0) in original --profiles order come first,
+        # followed by previously used profiles whose cooldown expired.
+        candidates.sort(key=lambda p: (times_assigned[p], profile_order[p]))
+        return candidates[0]
+
+    def _launch_shard(s: ShardState, prof: str, is_restart: bool) -> None:
+        s.profile = prof
+        times_assigned[prof] = times_assigned.get(prof, 0) + 1
+        cmd_tokens = build_shard_cli_tokens(
+            shard_idx=s.shard_idx,
+            shards=s.shard_total,
+            run_id_prefix=run_id_prefix,
+            profile=prof,
+            command=args.command,
+            adapter_model=args.adapter_model,
+            adapter_effort=args.adapter_effort,
+            adapter_thinking=args.adapter_thinking,
+            adapter_timeout=args.adapter_timeout,
+            pause_s=args.pause_s,
+            stagger_s=args.stagger_s,
+            max_calls=args.max_calls,
+            target_names=args.target_names,
+            lock_dir=args.lock_dir,
+            for_display=False,
+            generator_script=args.generator_script,
+        )
+        state_dir.mkdir(parents=True, exist_ok=True)
+        shard_log_path = state_dir / f"shard-{s.shard_idx}.log"
+        if s.log_fh is not None:
+            try:
+                s.log_fh.close()
+            except OSError:
+                pass
+        s.log_fh = open(shard_log_path, "ab")
+        proc = subprocess.Popen(
+            cmd_tokens,
+            stdin=subprocess.DEVNULL,
+            stdout=s.log_fh,
+            stderr=s.log_fh,
+            start_new_session=True,
+        )
+        s.proc = proc
+        s.pid = proc.pid
+        s.state = "running"
+        _append_supervisor_log(
+            state_dir,
+            "shard_restart" if is_restart else "shard_launch",
+            shard=s.shard_label,
+            run_id=s.run_id,
+            profile=prof,
+            pid=proc.pid,
+            restarts=s.restarts,
+            command=format_command_for_display(cmd_tokens),
+        )
+
+    def _refresh_caches_and_write_status(supervisor_state: str) -> tuple[int, int]:
+        """Re-read all shard caches via load_completed_cache, update ShardState counts,
+        and atomically write <state-dir>/status.json.
+        Raises ValueError if load_completed_cache raises ValueError.
+        Returns (total_calls, total_valid_names).
+        """
+        now_mono = time.monotonic()
+        _expire_cooldowns(now_mono)
+
+        total_calls = 0
+        all_entries = []
+        for s in shards:
+            if s.cache_path.exists():
+                cdict = load_completed_cache(s.cache_path)
+                s.records = _count_raw_cache_lines(s.cache_path)
+                vnames, _, _ = validate_and_dedupe_candidates(
+                    list(cdict.values()), corpus_nodes, corpus_embeds
+                )
+                s.valid_names = len(vnames)
+                all_entries.extend(cdict.values())
+            else:
+                s.records = 0
+                s.valid_names = 0
+            total_calls += s.records
+
+        if all_entries:
+            global_valid_list, _, _ = validate_and_dedupe_candidates(
+                all_entries, corpus_nodes, corpus_embeds
+            )
+            total_valid_names = len(global_valid_list)
+        else:
+            total_valid_names = 0
+
+        cooling_list = []
+        for p in sorted(cooling.keys(), key=lambda k: profile_order.get(k, 999)):
+            ce = cooling[p]
+            rem_s = max(0.0, round(ce.until_mono - now_mono, 2))
+            cooling_list.append({
+                "profile": ce.profile,
+                "reason": ce.reason,
+                "until_utc": ce.until_utc,
+                "remaining_s": rem_s,
+            })
+
+        in_use = _active_profiles()
+        spares_avail = [
+            p for p in profiles if p not in in_use and p not in cooling
+        ]
+
+        status_payload: dict[str, Any] = {
+            "run_id_prefix": run_id_prefix,
+            "supervisor_pid": os.getpid(),
+            "supervisor_state": supervisor_state,
+            "updated_at_utc": _now_utc_iso(),
+            "total_calls": total_calls,
+            "max_total_calls": args.max_total_calls,
+            "total_valid_names": total_valid_names,
+            "target_names": args.target_names,
+            "shards": [
+                {
+                    "shard": s.shard_label,
+                    "shard_index": s.shard_idx,
+                    "run_id": s.run_id,
+                    "cache_path": str(s.cache_path),
+                    "profile": s.profile,
+                    "pid": s.pid,
+                    "state": s.state,
+                    "restarts": s.restarts,
+                    "records": s.records,
+                    "valid_names": s.valid_names,
+                    "last_exit_code": s.last_exit_code,
+                }
+                for s in shards
+            ],
+            "cooling_profiles": cooling_list,
+            "spares_available": spares_avail,
+        }
+        _write_status_atomic(state_dir, status_payload)
+        return total_calls, total_valid_names
+
+    try:
+        _append_supervisor_log(
+            state_dir,
+            "supervisor_start",
+            shards=args.shards,
+            profiles=profiles,
+            initial_profiles=initial_profiles,
+            spare_profiles=spare_profiles,
+            run_id_prefix=run_id_prefix,
+            max_total_calls=args.max_total_calls,
+            profile_cooldown_s=args.profile_cooldown_s,
+            max_wait_s=args.max_wait_s,
+        )
+
+        # Launch initial shards
+        for s in shards:
+            assert s.profile is not None
+            _launch_shard(s, s.profile, is_restart=False)
+
+        wait_for_profile_since: Optional[float] = None
+
+        while True:
+            # 1. Check signal interruption
+            if received_signal:
+                sig = received_signal[0]
+                print(
+                    f"\nReceived signal {sig}; terminating shard process groups cleanly...",
+                    file=sys.stderr,
+                )
+                _terminate_all_children(shards)
+                for s in shards:
+                    if s.state in ("running", "waiting_for_profile"):
+                        s.state = "stopped"
+                        s.pid = None
+                try:
+                    _refresh_caches_and_write_status("interrupted")
+                except Exception:
+                    pass
+                _append_supervisor_log(state_dir, "signal_received", signal=sig, exit_code=SUP_EXIT_SIGNAL)
+                return SUP_EXIT_SIGNAL
+
+            # 2. Check exited child processes
+            now_mono = time.monotonic()
+            _expire_cooldowns(now_mono)
+
+            for s in shards:
+                if s.state == "running" and s.proc is not None:
+                    rc = s.proc.poll()
+                    if rc is not None:
+                        exited_pid = s.pid
+                        old_prof = s.profile
+                        s.last_exit_code = rc
+                        s.pid = None
+                        if s.log_fh is not None:
+                            try:
+                                s.log_fh.close()
+                            except OSError:
+                                pass
+                            s.log_fh = None
+
+                        _append_supervisor_log(
+                            state_dir,
+                            "shard_exit",
+                            shard=s.shard_label,
+                            run_id=s.run_id,
+                            profile=old_prof,
+                            pid=exited_pid,
+                            exit_code=rc,
+                        )
+
+                        if rc == GEN_EXIT_OK:
+                            s.state = "done"
+                        elif rc in (GEN_EXIT_RATE_LIMIT, GEN_EXIT_PROFILE_IN_USE):
+                            # Put current profile into cooldown
+                            if old_prof is not None:
+                                cd_s = (
+                                    float(args.profile_cooldown_s)
+                                    if rc == GEN_EXIT_RATE_LIMIT
+                                    else PROFILE_BUSY_COOLDOWN_S
+                                )
+                                reason = "rate_limit" if rc == GEN_EXIT_RATE_LIMIT else "profile_in_use"
+                                until_dt = datetime.now(timezone.utc) + timedelta(seconds=cd_s)
+                                cooling[old_prof] = CoolingEntry(
+                                    profile=old_prof,
+                                    until_mono=time.monotonic() + cd_s,
+                                    until_utc=until_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
+                                    reason=reason,
+                                    cooldown_s=cd_s,
+                                )
+                                _append_supervisor_log(
+                                    state_dir,
+                                    "profile_cooldown",
+                                    shard=s.shard_label,
+                                    run_id=s.run_id,
+                                    profile=old_prof,
+                                    reason=reason,
+                                    cooldown_s=cd_s,
+                                    until_utc=cooling[old_prof].until_utc,
+                                )
+
+                            s.restarts += 1
+                            if s.restarts > args.max_restarts_per_shard:
+                                msg = (
+                                    f"ERROR: Shard {s.shard_label} ({s.run_id}) exceeded "
+                                    f"--max-restarts-per-shard ({args.max_restarts_per_shard}). Stopping all shards."
+                                )
+                                print(msg, file=sys.stderr)
+                                s.state = "failed"
+                                _terminate_all_children(shards)
+                                for other in shards:
+                                    if other.state in ("running", "waiting_for_profile"):
+                                        other.state = "stopped"
+                                        other.pid = None
+                                try:
+                                    _refresh_caches_and_write_status("failed")
+                                except Exception:
+                                    pass
+                                _append_supervisor_log(
+                                    state_dir,
+                                    "supervisor_stop",
+                                    reason="max_restarts_exceeded",
+                                    shard=s.shard_label,
+                                    restarts=s.restarts,
+                                    exit_code=SUP_EXIT_ERROR,
+                                )
+                                return SUP_EXIT_ERROR
+
+                            s.state = "waiting_for_profile"
+                        else:
+                            # Fatal or unknown exit code -> stop all shards cleanly, keep caches, exit non-zero
+                            msg = (
+                                f"ERROR: Shard {s.shard_label} ({s.run_id}) on profile {old_prof!r} "
+                                f"exited with fatal/unexpected code {rc}. Stopping all shards."
+                            )
+                            print(msg, file=sys.stderr)
+                            s.state = "failed"
+                            _terminate_all_children(shards)
+                            for other in shards:
+                                if other.state in ("running", "waiting_for_profile"):
+                                    other.state = "stopped"
+                                    other.pid = None
+                            try:
+                                _refresh_caches_and_write_status("failed")
+                            except Exception:
+                                pass
+                            _append_supervisor_log(
+                                state_dir,
+                                "supervisor_stop",
+                                reason="fatal_or_unknown_shard_exit",
+                                shard=s.shard_label,
+                                run_id=s.run_id,
+                                profile=old_prof,
+                                shard_exit_code=rc,
+                                exit_code=SUP_EXIT_ERROR,
+                            )
+                            return SUP_EXIT_ERROR
+
+            # 3. Assign available profiles to any shards waiting for a profile
+            now_mono = time.monotonic()
+            for s in shards:
+                if s.state == "waiting_for_profile":
+                    next_prof = _pick_next_profile(now_mono)
+                    if next_prof is not None:
+                        old_prof = s.profile
+                        _append_supervisor_log(
+                            state_dir,
+                            "profile_reassigned",
+                            shard=s.shard_label,
+                            run_id=s.run_id,
+                            old_profile=old_prof,
+                            new_profile=next_prof,
+                            restarts=s.restarts,
+                        )
+                        _launch_shard(s, next_prof, is_restart=True)
+
+            # Track waiting time if any shard is still waiting for a free profile
+            any_waiting = any(s.state == "waiting_for_profile" for s in shards)
+            if any_waiting:
+                if wait_for_profile_since is None:
+                    wait_for_profile_since = time.monotonic()
+            else:
+                wait_for_profile_since = None
+
+            # 4. Re-read shard caches via generator loader & update status.json atomically
+            try:
+                total_calls, total_valid_names = _refresh_caches_and_write_status("running")
+            except ValueError as exc:
+                msg = f"ERROR: Cache loader raised ValueError: {exc}. Stopping all shards."
+                print(msg, file=sys.stderr)
+                _terminate_all_children(shards)
+                for s in shards:
+                    if s.state in ("running", "waiting_for_profile"):
+                        s.state = "stopped"
+                        s.pid = None
+                _append_supervisor_log(
+                    state_dir,
+                    "loader_error",
+                    error=str(exc),
+                    exit_code=SUP_EXIT_ERROR,
+                )
+                return SUP_EXIT_ERROR
+
+            # Print one-line poll summary
+            running_cnt = sum(1 for s in shards if s.state == "running")
+            done_cnt = sum(1 for s in shards if s.state == "done")
+            waiting_cnt = sum(1 for s in shards if s.state == "waiting_for_profile")
+            print(
+                f"[poll {_now_utc_iso()}] shards: {running_cnt} running, {done_cnt}/{len(shards)} done, "
+                f"{waiting_cnt} waiting | calls: {total_calls}/{args.max_total_calls} | "
+                f"valid_names: {total_valid_names}/{args.target_names} | cooling: {len(cooling)}"
+            )
+            sys.stdout.flush()
+
+            all_done = all(s.state == "done" for s in shards)
+
+            # 5. Enforce --max-total-calls cap
+            if total_calls > args.max_total_calls or (total_calls >= args.max_total_calls and not all_done):
+                msg = (
+                    f"ERROR: Total calls across shards ({total_calls}) reached/exceeded "
+                    f"--max-total-calls ({args.max_total_calls}). Stopping all shards."
+                )
+                print(msg, file=sys.stderr)
+                _terminate_all_children(shards)
+                for s in shards:
+                    if s.state in ("running", "waiting_for_profile"):
+                        s.state = "stopped"
+                        s.pid = None
+                try:
+                    _refresh_caches_and_write_status("stopped_max_calls")
+                except Exception:
+                    pass
+                _append_supervisor_log(
+                    state_dir,
+                    "max_total_calls_exceeded",
+                    total_calls=total_calls,
+                    max_total_calls=args.max_total_calls,
+                    exit_code=SUP_EXIT_MAX_TOTAL_CALLS,
+                )
+                return SUP_EXIT_MAX_TOTAL_CALLS
+
+            # 6. Check if all shards have completed with exit 0
+            if all_done:
+                break
+
+            # 7. Check if stalled waiting for a free profile beyond --max-wait-s
+            if wait_for_profile_since is not None:
+                waited_s = time.monotonic() - wait_for_profile_since
+                if waited_s >= args.max_wait_s:
+                    msg = (
+                        f"STALLED: No free profile became available within --max-wait-s "
+                        f"({args.max_wait_s}s). Stopping cleanly; caches are intact and resumable."
+                    )
+                    print(msg, file=sys.stderr)
+                    _terminate_all_children(shards)
+                    for s in shards:
+                        if s.state in ("running", "waiting_for_profile"):
+                            s.state = "stalled"
+                            s.pid = None
+                    try:
+                        _refresh_caches_and_write_status("stalled")
+                    except Exception:
+                        pass
+                    _append_supervisor_log(
+                        state_dir,
+                        "stalled",
+                        waited_s=round(waited_s, 3),
+                        max_wait_s=args.max_wait_s,
+                        exit_code=SUP_EXIT_STALLED,
+                    )
+                    return SUP_EXIT_STALLED
+
+            # 8. Compute sleep duration until next poll, earliest cooldown expiry, or max_wait deadline
+            now_mono = time.monotonic()
+            sleep_s = float(args.poll_s)
+            if any_waiting and cooling:
+                earliest_cd = min(ce.until_mono for ce in cooling.values())
+                cd_rem = max(0.01, earliest_cd - now_mono)
+                sleep_s = min(sleep_s, cd_rem)
+            if wait_for_profile_since is not None:
+                wait_rem = max(0.01, (wait_for_profile_since + args.max_wait_s) - now_mono)
+                sleep_s = min(sleep_s, wait_rem)
+
+            # Sleep in small slices so SIGINT/SIGTERM is handled promptly
+            sleep_deadline = time.monotonic() + sleep_s
+            while time.monotonic() < sleep_deadline:
+                if received_signal:
+                    break
+                # Also wake early if any running child exits
+                if any(s.proc is not None and s.proc.poll() is not None for s in shards if s.state == "running"):
+                    break
+                rem_slice = sleep_deadline - time.monotonic()
+                time.sleep(min(0.05, max(0.005, rem_slice)))
+
+        # All shards exited 0 -> Run merge (--build-only --merge-run-ids) then verify (--verify --merge-run-ids)
+        merge_ids = ",".join(s.run_id for s in shards)
+        effective_min_req = (
+            args.min_required_names
+            if args.min_required_names is not None
+            else min(MIN_REQUIRED_NAMES_FOR_VALIDATION, args.target_names)
+        )
+
+        _refresh_caches_and_write_status("merging")
+        build_cmd = [
+            sys.executable,
+            str(args.generator_script),
+            "--build-only",
+            "--backend",
+            "command",
+            "--adapter-model",
+            args.adapter_model,
+            "--merge-run-ids",
+            merge_ids,
+        ]
+        if output_path.resolve() != DEFAULT_TRACKED_OUTPUT.resolve():
+            build_cmd.extend(["--output", str(output_path)])
+        if effective_min_req != MIN_REQUIRED_NAMES_FOR_VALIDATION:
+            build_cmd.extend(["--min-required-names", str(effective_min_req)])
+
+        _append_supervisor_log(state_dir, "merge_start", command=" ".join(build_cmd))
+        res_build = subprocess.run(build_cmd, capture_output=True, text=True)
+        _append_supervisor_log(
+            state_dir,
+            "merge_done",
+            exit_code=res_build.returncode,
+            stdout=res_build.stdout.strip(),
+            stderr=res_build.stderr.strip(),
+        )
+        if res_build.returncode != 0:
+            print(f"ERROR: Merge (--build-only) failed (exit {res_build.returncode}):\n{res_build.stderr}", file=sys.stderr)
+            _refresh_caches_and_write_status("failed")
+            return SUP_EXIT_ERROR
+
+        _refresh_caches_and_write_status("verifying")
+        verify_cmd = [
+            sys.executable,
+            str(args.generator_script),
+            "--verify",
+            "--merge-run-ids",
+            merge_ids,
+        ]
+        if output_path.resolve() != DEFAULT_TRACKED_OUTPUT.resolve():
+            verify_cmd.extend(["--output", str(output_path)])
+        if effective_min_req != MIN_REQUIRED_NAMES_FOR_VALIDATION:
+            verify_cmd.extend(["--min-required-names", str(effective_min_req)])
+
+        _append_supervisor_log(state_dir, "verify_start", command=" ".join(verify_cmd))
+        res_verify = subprocess.run(verify_cmd, capture_output=True, text=True)
+        _append_supervisor_log(
+            state_dir,
+            "verify_done",
+            exit_code=res_verify.returncode,
+            stdout=res_verify.stdout.strip(),
+            stderr=res_verify.stderr.strip(),
+        )
+        if res_verify.returncode != 0:
+            print(f"ERROR: Verification (--verify) failed (exit {res_verify.returncode}):\n{res_verify.stderr}", file=sys.stderr)
+            _refresh_caches_and_write_status("failed")
+            return SUP_EXIT_ERROR
+
+        _refresh_caches_and_write_status("completed")
+        _append_supervisor_log(
+            state_dir,
+            "supervisor_stop",
+            reason="completed",
+            output_path=str(output_path),
+            exit_code=SUP_EXIT_OK,
+        )
+
+        # Print pool meta summary
+        with open(output_path, "r", encoding="utf-8") as f:
+            pool_data = json.load(f)
+        meta = pool_data.get("meta", {})
+        summary_meta = {k: v for k, v in meta.items() if k != "corpora_checked"}
+        print("\n=== Merged Pool Verification PASSED ===")
+        print(res_verify.stdout.strip())
+        print("=== Pool Meta Summary ===")
+        print(json.dumps(summary_meta, indent=2, ensure_ascii=False))
+        return SUP_EXIT_OK
+
+    finally:
+        _terminate_all_children(shards)
+        signal.signal(signal.SIGINT, prev_sigint)
+        signal.signal(signal.SIGTERM, prev_sigterm)
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git i/tests/stub_prompt_adapter.py w/tests/stub_prompt_adapter.py
index deadba9..0077854 100644
--- i/tests/stub_prompt_adapter.py
+++ w/tests/stub_prompt_adapter.py
@@ -94,7 +94,7 @@ def main() -> int:
     if m:
         subfield = m.group(1).replace(" ", "_")
 
-    if scenario == "hang":
+    if scenario == "hang" or scenario.startswith("hang_"):
         if args.spawn_child:
             child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
             if args.child_pid_file:
@@ -102,10 +102,41 @@ def main() -> int:
         time.sleep(args.hang_seconds)
         return 0
 
+    if scenario.startswith("slow_success_"):
+        time.sleep(args.hang_seconds if args.hang_seconds != 15.0 else 0.15)
+        scenario = "success"
+
     if scenario == "garbage":
         print("CRITICAL: [fatal] Process crashed! Non-JSON garbage on stdout.")
         return 1
 
+    m_rla = re.match(r"^rate_limit_after_(\d+)_(.+)$", scenario)
+    if m_rla:
+        limit_k = int(m_rla.group(1))
+        suffix_id = re.sub(r"[^a-zA-Z0-9_]", "_", m_rla.group(2))
+        base_state = Path(args.state_file) if args.state_file else Path("stub_state.json")
+        state_file = base_state.parent / f"{base_state.stem}_{suffix_id}.txt"
+        count = 0
+        if state_file.exists():
+            try:
+                count = int(state_file.read_text(encoding="utf-8").strip())
+            except Exception:
+                count = 0
+        if count >= limit_k:
+            out = {
+                "ok": False,
+                "error": "rate_limit",
+                "message": f"Rate limit reached after {count} calls on {scenario}",
+                "reset_time": "2026-10-07T23:59:59Z",
+            }
+            print(json.dumps(out))
+            return 10
+        else:
+            count += 1
+            state_file.parent.mkdir(parents=True, exist_ok=True)
+            state_file.write_text(str(count), encoding="utf-8")
+            scenario = "success"
+
     if scenario == "rate_limit_after_n":
         state_file = Path(args.state_file) if args.state_file else Path("stub_state.json")
         count = 0
@@ -129,7 +160,7 @@ def main() -> int:
             state_file.write_text(str(count), encoding="utf-8")
             scenario = "success"
 
-    if scenario == "rate_limit":
+    if scenario == "rate_limit" or scenario.startswith("rate_limit_"):
         out = {
             "ok": False,
             "error": "rate_limit",
@@ -139,7 +170,7 @@ def main() -> int:
         print(json.dumps(out))
         return 10
 
-    if scenario == "login_required":
+    if scenario == "login_required" or scenario.startswith("login_required_"):
         out = {
             "ok": False,
             "error": "login_required",
@@ -149,7 +180,7 @@ def main() -> int:
         print(json.dumps(out))
         return 11
 
-    if scenario == "model_mismatch":
+    if scenario == "model_mismatch" or scenario.startswith("model_mismatch_"):
         out = {
             "ok": False,
             "error": "model_mismatch",
@@ -159,7 +190,7 @@ def main() -> int:
         print(json.dumps(out))
         return 14
 
-    if scenario == "profile_in_use":
+    if scenario == "profile_in_use" or scenario.startswith("profile_in_use_"):
         out = {
             "ok": False,
             "error": "profile_in_use",
diff --git i/tests/test_name_pool_supervisor.py w/tests/test_name_pool_supervisor.py
new file mode 100644
index 0000000..267d369
--- /dev/null
+++ w/tests/test_name_pool_supervisor.py
@@ -0,0 +1,691 @@
+"""Tests for scripts/name_pool_supervisor.py (DATA-007).
+
+All tests run offline against tests/stub_prompt_adapter.py inside pytest's tmp_path.
+A module-scoped autouse guard fixture verifies that nothing under <repo_root>/results/datagen
+is created or modified during the test session.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import json
+import os
+from pathlib import Path
+import signal
+import subprocess
+import sys
+import time
+from typing import Any
+
+import pytest
+
+# Ensure src/ and repo root are importable
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+if str(_REPO_ROOT / "src") not in sys.path:
+    sys.path.insert(0, str(_REPO_ROOT / "src"))
+if str(_REPO_ROOT) not in sys.path:
+    sys.path.insert(0, str(_REPO_ROOT))
+
+from scripts.generate_name_pool import load_completed_cache
+from scripts.name_pool_supervisor import (
+    SUP_EXIT_ERROR,
+    SUP_EXIT_MAX_TOTAL_CALLS,
+    SUP_EXIT_OK,
+    SUP_EXIT_SIGNAL,
+    SUP_EXIT_STALLED,
+    SUP_EXIT_USAGE,
+    main as supervisor_main,
+)
+
+_SUPERVISOR_SCRIPT = _REPO_ROOT / "scripts" / "name_pool_supervisor.py"
+_STUB_SCRIPT = _REPO_ROOT / "tests" / "stub_prompt_adapter.py"
+
+
+@pytest.fixture(autouse=True, scope="module")
+def guard_results_datagen_unmodified():
+    """Verify that nothing under <repo_root>/results/datagen is created or modified by tests."""
+    datagen_dir = _REPO_ROOT / "results" / "datagen"
+
+    def _snapshot() -> set[str]:
+        if not datagen_dir.exists():
+            return set()
+        return {str(p.relative_to(datagen_dir)) for p in datagen_dir.rglob("*")}
+
+    before = _snapshot()
+    yield
+    after = _snapshot()
+    assert before == after, (
+        f"Test suite modified results/datagen! Diff: added={after - before}, removed={before - after}"
+    )
+
+
+def _read_jsonl(path: Path) -> list[dict[str, Any]]:
+    if not path.exists():
+        return []
+    out: list[dict[str, Any]] = []
+    for line in path.read_text(encoding="utf-8").splitlines():
+        if line.strip():
+            out.append(json.loads(line))
+    return out
+
+
+def _pid_is_alive(pid: int) -> bool:
+    try:
+        os.kill(pid, 0)
+    except ProcessLookupError:
+        return False
+    except PermissionError:
+        return True
+    # Check if zombie on Linux
+    stat_path = Path(f"/proc/{pid}/stat")
+    if stat_path.exists():
+        try:
+            content = stat_path.read_text(encoding="utf-8")
+            # Format: pid (comm) state ...
+            rparen = content.rfind(")")
+            if rparen != -1:
+                state_char = content[rparen + 2 : rparen + 3]
+                if state_char == "Z":
+                    return False
+        except OSError:
+            pass
+    return True
+
+
+def test_happy_path_two_shards_merged_and_verified(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    """1. Happy path: 2 shards, 2 profiles, stub succeeds -> both exit 0, merged pool built and verified."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_state"
+    lock_dir = tmp_path / "locks"
+    out_pool = tmp_path / "pool.json"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"
+
+    rc = supervisor_main([
+        "--shards", "2",
+        "--profiles", "Profile_A,Profile_B",
+        "--run-id-prefix", "happy2",
+        "--command", stub_cmd,
+        "--target-names", "120",
+        "--max-calls", "5",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_OK
+
+    captured = capsys.readouterr()
+    assert "Merged Pool Verification PASSED" in captured.out
+    assert "Pool Meta Summary" in captured.out
+
+    assert out_pool.exists()
+    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
+    meta = pool_data["meta"]
+    assert meta["run_ids"] == ["happy2-s1of2", "happy2-s2of2"]
+    assert meta["profiles_used"] == ["Profile_A", "Profile_B"]
+    assert len(pool_data["names"]) == 160  # 2 calls/shard * 2 shards * 40 names
+
+    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    assert status["supervisor_state"] == "completed"
+    assert status["total_calls"] == 4
+    assert status["total_valid_names"] == 160
+    assert all(s["state"] == "done" and s["last_exit_code"] == 0 for s in status["shards"])
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    event_names = [e["event"] for e in events]
+    assert "supervisor_start" in event_names
+    assert "merge_done" in event_names
+    assert "verify_done" in event_names
+    assert any(e["event"] == "verify_done" and e["exit_code"] == 0 for e in events)
+
+
+def test_failover_on_rate_limit_to_spare_profile(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """2. Failover on rate limit: 2 shards, 3 profiles; profile 1 rate-limits after K=1 calls ->
+    shard 1 restarts on profile 3, resumes from cache, finishes.
+    """
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_state"
+    lock_dir = tmp_path / "locks"
+    out_pool = tmp_path / "pool.json"
+    stub_state_base = tmp_path / "stub_counter.txt"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --state-file {stub_state_base}"
+
+    # Shard 1 needs ceil(120/2) = 60 valid names (2 calls of 40 names).
+    # Profile 'rate_limit_after_1_p1' succeeds on call 1 (40 names) and rate-limits on call 2 (exit 3).
+    # Supervisor cools 'rate_limit_after_1_p1' and restarts shard 1 on 'Spare_P3', which finishes call 2.
+    rc = supervisor_main([
+        "--shards", "2",
+        "--profiles", "rate_limit_after_1_p1,Profile_2,Spare_P3",
+        "--run-id-prefix", "failover",
+        "--command", stub_cmd,
+        "--target-names", "120",
+        "--max-calls", "5",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--profile-cooldown-s", "18000",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_OK
+    assert out_pool.exists()
+
+    # Check shard 1 raw cache: must have 2 records, first from rate_limit_after_1_p1, second from Spare_P3
+    s1_cache_path = tmp_path / "results" / "datagen" / "failover-s1of2" / "raw_responses.jsonl"
+    s1_records = _read_jsonl(s1_cache_path)
+    assert len(s1_records) == 2
+    s1_profiles_in_cache = [r["backend_meta"]["profile_used"] for r in s1_records]
+    assert s1_profiles_in_cache == ["rate_limit_after_1_p1", "Spare_P3"]
+
+    # Check status.json and supervisor-log.jsonl
+    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    assert status["supervisor_state"] == "completed"
+    s1_status = next(s for s in status["shards"] if s["shard"] == "1/2")
+    assert s1_status["restarts"] == 1
+    assert s1_status["profile"] == "Spare_P3"
+    assert s1_status["records"] == 2
+    assert any(c["profile"] == "rate_limit_after_1_p1" and c["reason"] == "rate_limit" for c in status["cooling_profiles"])
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    reassign_events = [e for e in events if e["event"] == "profile_reassigned"]
+    assert len(reassign_events) == 1
+    assert reassign_events[0]["shard"] == "1/2"
+    assert reassign_events[0]["old_profile"] == "rate_limit_after_1_p1"
+    assert reassign_events[0]["new_profile"] == "Spare_P3"
+
+    # Check merged pool built by generate_name_pool.py
+    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
+    assert len(pool_data["names"]) == 160
+    assert pool_data["meta"]["run_ids"] == ["failover-s1of2", "failover-s2of2"]
+    assert len(pool_data["meta"]["shards"]) == 2
+
+
+def test_profile_in_use_rotates_to_next_profile_with_short_cooldown(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """3. Profile-in-use: shard hits exit 7 -> rotates to next profile without burning the 18000s rate-limit cooldown."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_state"
+    lock_dir = tmp_path / "locks"
+    out_pool = tmp_path / "pool.json"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"
+
+    rc = supervisor_main([
+        "--shards", "1",
+        "--profiles", "profile_in_use_p1,Spare_P2",
+        "--run-id-prefix", "inuse",
+        "--command", stub_cmd,
+        "--target-names", "40",
+        "--max-calls", "3",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--profile-cooldown-s", "18000",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_OK
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    cd_events = [e for e in events if e["event"] == "profile_cooldown"]
+    assert len(cd_events) == 1
+    assert cd_events[0]["profile"] == "profile_in_use_p1"
+    assert cd_events[0]["reason"] == "profile_in_use"
+    # Must use 60s busy cooldown, NOT the 18000s rate_limit cooldown
+    assert cd_events[0]["cooldown_s"] == 60.0
+
+    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    assert status["shards"][0]["profile"] == "Spare_P2"
+    assert status["shards"][0]["restarts"] == 1
+    assert status["cooling_profiles"][0]["remaining_s"] <= 60.0
+
+    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
+    assert pool_data["meta"]["profiles_used"] == ["Spare_P2"]
+
+
+def test_all_profiles_cooling_stalled_exit_caches_intact(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """4. All profiles cooling: after --max-wait-s (set small in the test) supervisor exits with stalled code, caches intact."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_state"
+    lock_dir = tmp_path / "locks"
+    out_pool = tmp_path / "pool.json"
+    stub_state_base = tmp_path / "stub_counter.txt"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --state-file {stub_state_base}"
+
+    # 1 shard, 1 profile, target 80 names (2 calls). Profile rate-limits after 1 call.
+    # Cooldown is 3600s, max-wait-s is 0.25s -> stalls after ~0.25s with SUP_EXIT_STALLED (3).
+    rc = supervisor_main([
+        "--shards", "1",
+        "--profiles", "rate_limit_after_1_only",
+        "--run-id-prefix", "stalledrun",
+        "--command", stub_cmd,
+        "--target-names", "80",
+        "--max-calls", "5",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--profile-cooldown-s", "3600",
+        "--max-wait-s", "0.25",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_STALLED
+    assert not out_pool.exists()
+
+    # Cache from call 1 must remain intact and resumable
+    cache_path = tmp_path / "results" / "datagen" / "stalledrun-s1of1" / "raw_responses.jsonl"
+    assert cache_path.exists()
+    completed = load_completed_cache(cache_path)
+    assert len(completed) == 1
+
+    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    assert status["supervisor_state"] == "stalled"
+    assert status["shards"][0]["state"] == "stalled"
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    assert any(e["event"] == "stalled" and e["exit_code"] == SUP_EXIT_STALLED for e in events)
+
+
+def test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """5. Unknown / fatal exit code (both a known fatal code and an arbitrary code like 99):
+    supervisor terminates remaining shards and exits non-zero, caches intact.
+    """
+    monkeypatch.chdir(tmp_path)
+
+    # Part A: Known fatal generator exit code 4 (login_required) while shard 2 is hanging
+    state_dir_a = tmp_path / "state_fatal"
+    lock_dir_a = tmp_path / "locks_fatal"
+    child_pid_file_a = tmp_path / "child_fatal.pid"
+    stub_cmd_a = (
+        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
+        f"--child-pid-file {child_pid_file_a} --hang-seconds 30"
+    )
+
+    # Pre-seed 1 valid cache line in shard 1 so we verify caches are preserved untouched
+    s1_cache_a = tmp_path / "results" / "datagen" / "fatalA-s1of2" / "raw_responses.jsonl"
+    s1_cache_a.parent.mkdir(parents=True, exist_ok=True)
+    seed_record = {
+        "round": 1,
+        "subfield": "algorithms",
+        "subfield_idx": 0,
+        "request_system": "sys",
+        "request_user": "usr",
+        "response_text": json.dumps([f"seeded_concept_{i:03d}" for i in range(1, 41)]),
+        "model_id": "Sonnet 5.5 Low",
+        "token_usage": {},
+        "timestamp_utc": "2026-10-11T00:00:00Z",
+        "retries": 0,
+        "latency_s": 0.01,
+        "backend": "command",
+        "prompt_version": "np1w",
+        "backend_meta": {"thinking_requested": None, "profile_used": "login_required_p1"},
+        "shard": "1/2",
+    }
+    s1_cache_a.write_text(json.dumps(seed_record) + "\n", encoding="utf-8")
+
+    rc_a = supervisor_main([
+        "--shards", "2",
+        "--profiles", "login_required_p1,hang_p2",
+        "--run-id-prefix", "fatalA",
+        "--command", stub_cmd_a,
+        "--target-names", "160",
+        "--max-calls", "5",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir_a),
+        "--lock-dir", str(lock_dir_a),
+        "--output", str(tmp_path / "pool_a.json"),
+        "--live",
+        "--confirm",
+    ])
+    assert rc_a == SUP_EXIT_ERROR
+    assert len(load_completed_cache(s1_cache_a)) == 1
+    if child_pid_file_a.exists():
+        cpid = int(child_pid_file_a.read_text(encoding="utf-8").strip())
+        assert not _pid_is_alive(cpid)
+
+    events_a = _read_jsonl(state_dir_a / "supervisor-log.jsonl")
+    assert any(
+        e["event"] == "supervisor_stop"
+        and e.get("reason") == "fatal_or_unknown_shard_exit"
+        and e.get("shard_exit_code") == 4
+        for e in events_a
+    )
+
+    # Part B: Arbitrary unknown exit code 99 from a fake generator script while shard 2 is sleeping
+    fake_gen = tmp_path / "fake_generator_99.py"
+    shard2_pid_file = tmp_path / "shard2_sleep.pid"
+    fake_gen.write_text(
+        "#!/usr/bin/env python3\n"
+        "import os, pathlib, sys, time\n"
+        "if '1/2' in sys.argv:\n"
+        "    time.sleep(0.1)\n"
+        "    sys.exit(99)\n"
+        f"pathlib.Path({str(shard2_pid_file)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
+        "time.sleep(30)\n",
+        encoding="utf-8",
+    )
+    state_dir_b = tmp_path / "state_unknown99"
+    rc_b = supervisor_main([
+        "--shards", "2",
+        "--profiles", "Prof1,Prof2",
+        "--run-id-prefix", "unk99",
+        "--command", "true",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir_b),
+        "--output", str(tmp_path / "pool_b.json"),
+        "--generator-script", str(fake_gen),
+        "--live",
+        "--confirm",
+    ])
+    assert rc_b == SUP_EXIT_ERROR
+    if shard2_pid_file.exists():
+        s2_pid = int(shard2_pid_file.read_text(encoding="utf-8").strip())
+        assert not _pid_is_alive(s2_pid)
+
+    events_b = _read_jsonl(state_dir_b / "supervisor-log.jsonl")
+    assert any(
+        e["event"] == "supervisor_stop"
+        and e.get("reason") == "fatal_or_unknown_shard_exit"
+        and e.get("shard_exit_code") == 99
+        for e in events_b
+    )
+
+
+def test_sigterm_propagation_kills_children_and_exits_130(tmp_path: Path) -> None:
+    """6. SIGTERM propagation: send SIGTERM to supervisor while a shard's stub is sleeping ->
+    child is dead and supervisor exits 130.
+    """
+    state_dir = tmp_path / "sup_sigterm"
+    lock_dir = tmp_path / "locks_sigterm"
+    child_pid_file = tmp_path / "grandchild.pid"
+    stub_cmd = (
+        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
+        f"--child-pid-file {child_pid_file} --hang-seconds 30"
+    )
+
+    sup_proc = subprocess.Popen(
+        [
+            sys.executable,
+            str(_SUPERVISOR_SCRIPT),
+            "--shards", "1",
+            "--profiles", "hang_p1",
+            "--run-id-prefix", "sigtermrun",
+            "--command", stub_cmd,
+            "--target-names", "40",
+            "--pause-s", "0",
+            "--stagger-s", "0",
+            "--poll-s", "0.05",
+            "--state-dir", str(state_dir),
+            "--lock-dir", str(lock_dir),
+            "--output", str(tmp_path / "pool.json"),
+            "--live",
+            "--confirm",
+        ],
+        cwd=str(tmp_path),
+        stdout=subprocess.PIPE,
+        stderr=subprocess.PIPE,
+        text=True,
+    )
+
+    # Wait until the stub has spawned its child process and written grandchild.pid
+    deadline = time.monotonic() + 10.0
+    while time.monotonic() < deadline:
+        if child_pid_file.exists() and (state_dir / "status.json").exists():
+            break
+        time.sleep(0.05)
+
+    assert child_pid_file.exists(), "Stub did not spawn child process before timeout"
+    grandchild_pid = int(child_pid_file.read_text(encoding="utf-8").strip())
+    status_before = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    shard_pid = status_before["shards"][0]["pid"]
+    assert shard_pid is not None
+    assert _pid_is_alive(shard_pid)
+    assert _pid_is_alive(grandchild_pid)
+
+    # Send SIGTERM to supervisor
+    sup_proc.send_signal(signal.SIGTERM)
+    sup_proc.wait(timeout=10.0)
+    assert sup_proc.returncode == SUP_EXIT_SIGNAL  # 130
+
+    # Both the shard process and its spawned child must be dead
+    assert not _pid_is_alive(shard_pid)
+    assert not _pid_is_alive(grandchild_pid)
+
+
+def test_max_total_calls_stops_all_shards(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """7. --max-total-calls exceeded -> supervisor stops all shards and exits non-zero."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_maxcalls"
+    lock_dir = tmp_path / "locks_maxcalls"
+    out_pool = tmp_path / "pool.json"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --hang-seconds 0.08"
+
+    # 2 shards, each trying to collect 200 names (5 calls each), but --max-total-calls is 2
+    rc = supervisor_main([
+        "--shards", "2",
+        "--profiles", "slow_success_p1,slow_success_p2",
+        "--run-id-prefix", "maxcalls",
+        "--command", stub_cmd,
+        "--target-names", "400",
+        "--max-calls", "10",
+        "--max-total-calls", "2",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_MAX_TOTAL_CALLS
+    assert not out_pool.exists()
+
+    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
+    assert status["supervisor_state"] == "stopped_max_calls"
+    assert status["total_calls"] >= 2
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    assert any(
+        e["event"] == "max_total_calls_exceeded" and e["exit_code"] == SUP_EXIT_MAX_TOTAL_CALLS
+        for e in events
+    )
+
+
+def test_status_cli_read_only(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    """8. --status prints a table from status.json + caches and modifies nothing."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_status"
+    lock_dir = tmp_path / "locks_status"
+    out_pool = tmp_path / "pool.json"
+    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"
+
+    # Run a quick 1-shard run so status.json and cache exist
+    rc_run = supervisor_main([
+        "--shards", "1",
+        "--profiles", "Profile_Status_1",
+        "--run-id-prefix", "statustest",
+        "--command", stub_cmd,
+        "--target-names", "40",
+        "--max-calls", "2",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(out_pool),
+        "--live",
+        "--confirm",
+    ])
+    assert rc_run == SUP_EXIT_OK
+    capsys.readouterr()
+
+    def _tree_digest(root: Path) -> dict[str, tuple[int, str]]:
+        snap: dict[str, tuple[int, str]] = {}
+        for p in sorted(root.rglob("*")):
+            if p.is_file():
+                rel = str(p.relative_to(root))
+                snap[rel] = (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
+        return snap
+
+    before_snap = _tree_digest(tmp_path)
+
+    rc_status = supervisor_main(["--status", "--state-dir", str(state_dir)])
+    assert rc_status == SUP_EXIT_OK
+
+    captured = capsys.readouterr()
+    assert "=== Name-Pool Supervisor Status" in captured.out
+    assert "statustest-s1of1" in captured.out
+    assert "Profile_Status_1" in captured.out
+    assert "Total calls (cache lines): 1" in captured.out
+    assert "Total deduplicated valid:  40" in captured.out
+
+    after_snap = _tree_digest(tmp_path)
+    assert before_snap == after_snap, "--status modified files in tmp_path!"
+
+
+def test_refusal_without_live_and_confirm(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """9a. Refusal without --live --confirm (exit 2) and creates nothing."""
+    monkeypatch.chdir(tmp_path)
+    base_args = [
+        "--shards", "2",
+        "--profiles", "Prof_1,Prof_2,Spare_3",
+        "--run-id-prefix", "drytest",
+        "--command", "prompt-adapter",
+    ]
+
+    assert supervisor_main(base_args) == SUP_EXIT_USAGE
+    assert supervisor_main([*base_args, "--live"]) == SUP_EXIT_USAGE
+    assert supervisor_main([*base_args, "--confirm"]) == SUP_EXIT_USAGE
+    assert list(tmp_path.iterdir()) == []
+
+
+def test_dry_run_prints_plan_and_launches_nothing(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    """9b. --dry-run prints the plan (shard commands, initial assignment, spares) and launches nothing."""
+    monkeypatch.chdir(tmp_path)
+    rc_dry = supervisor_main([
+        "--shards", "2",
+        "--profiles", "Prof_1,Prof_2,Spare_3",
+        "--run-id-prefix", "drytest",
+        "--command", "prompt-adapter",
+        "--adapter-model", "sonnet",
+        "--adapter-effort", "low",
+        "--adapter-thinking", "off",
+        "--dry-run",
+    ])
+    assert rc_dry == SUP_EXIT_OK
+    out = capsys.readouterr().out
+    assert "Initial profiles (1..N): Prof_1, Prof_2" in out
+    assert "Spare profiles (1):      Spare_3" in out
+    assert "unverified operator assumption" in out
+    assert (
+        "python3 scripts/generate_name_pool.py --backend command --command prompt-adapter "
+        "--adapter-profile Prof_1 --adapter-model sonnet --adapter-effort low "
+        "--adapter-thinking off --shard 1/2 --run-id drytest-s1of2 --live --confirm"
+    ) in out
+    assert (
+        "python3 scripts/generate_name_pool.py --backend command --command prompt-adapter "
+        "--adapter-profile Prof_2 --adapter-model sonnet --adapter-effort low "
+        "--adapter-thinking off --shard 2/2 --run-id drytest-s2of2 --live --confirm"
+    ) in out
+    assert list(tmp_path.iterdir()) == []
+
+
+def test_loader_value_error_stops_everything(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """10. Loader ValueError (corrupt / conflicting cache lines mid-run) stops everything cleanly."""
+    monkeypatch.chdir(tmp_path)
+    state_dir = tmp_path / "sup_valerr"
+    lock_dir = tmp_path / "locks_valerr"
+    child_pid_file = tmp_path / "valerr_child.pid"
+    stub_cmd = (
+        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
+        f"--child-pid-file {child_pid_file} --hang-seconds 30"
+    )
+
+    # Pre-populate shard 1 cache with mixed backend records ('command' vs 'deepseek')
+    # so load_completed_cache() raises ValueError during the supervisor's poll.
+    s1_cache = tmp_path / "results" / "datagen" / "valerr-s1of2" / "raw_responses.jsonl"
+    s1_cache.parent.mkdir(parents=True, exist_ok=True)
+    rec1 = {
+        "round": 1,
+        "subfield": "algorithms",
+        "subfield_idx": 0,
+        "request_system": "s",
+        "request_user": "u",
+        "response_text": '["algo_concept_one"]',
+        "model_id": "m",
+        "token_usage": {},
+        "timestamp_utc": "2026-10-11T00:00:00Z",
+        "retries": 0,
+        "latency_s": 0.1,
+        "backend": "command",
+        "prompt_version": "np1w",
+    }
+    rec2 = {
+        **rec1,
+        "subfield": "compilers",
+        "subfield_idx": 2,
+        "backend": "deepseek",
+        "prompt_version": "np1",
+    }
+    s1_cache.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")
+
+    rc = supervisor_main([
+        "--shards", "2",
+        "--profiles", "hang_p1,hang_p2",
+        "--run-id-prefix", "valerr",
+        "--command", stub_cmd,
+        "--target-names", "160",
+        "--pause-s", "0",
+        "--stagger-s", "0",
+        "--poll-s", "0.05",
+        "--state-dir", str(state_dir),
+        "--lock-dir", str(lock_dir),
+        "--output", str(tmp_path / "pool.json"),
+        "--live",
+        "--confirm",
+    ])
+    assert rc == SUP_EXIT_ERROR
+
+    if child_pid_file.exists():
+        cpid = int(child_pid_file.read_text(encoding="utf-8").strip())
+        assert not _pid_is_alive(cpid)
+
+    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
+    assert any(
+        e["event"] == "loader_error" and "mixed backends" in e.get("error", "")
+        for e in events
+    )
```
