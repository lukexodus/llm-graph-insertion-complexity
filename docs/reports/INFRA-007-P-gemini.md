# INFRA-007-P — Post-Review Amendments: Embedder Pins & Runtime Check, Resume-Guard Identity, Dry-Run Hygiene, Standalone Stub Module, and Test/Mutation Gaps (`[D-66]`)

- **Task ID:** `INFRA-007-P`
- **Decision ID:** `[D-66]`
- **Date:** 2026-10-12
- **Branch:** `master` (in-place checkout, uncommitted until Step 8 per Rule 1)

---

## 1. Agent Identity

- **Agent:** `gemini` (Google Antigravity)
- **Model Label:** `Gemini 3.8 Flash (High)` (session started under `Gemini 3.8 Flash (Low)` and switched by user to `Gemini 3.8 Flash (High)`)
- **Session / Conversation ID:** `098dcdd4-c444-4fcd-af8f-1b2054b31802` (`[Confirmed]` distinct from the `INFRA-007-R` review session `ede0cb54-0124-4d2a-b94b-45d52a9541f9`)

---

## 2. What Was Asked / What I Did

### 2.1 Section 0 Inputs Status (`<FILL...>` Placeholders)
- Both `SENTENCE_TRANSFORMERS_VERSION` and `MODEL_REVISION` in Section 0 of the relayed prompt remained `<FILL...>` placeholders (`[Confirmed]`).
- Per Section 0 rules:
  - Did **not** guess either pin value and did **not** edit `pyproject.toml`'s `embed` line (`Step A.1` skipped).
  - Kept `SENTENCE_TRANSFORMERS_VERSION_PIN = None` and `MODEL_REVISION_PIN = None` in [`src/graph_insertion/embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py) so `MiniLMEmbedder()` fails closed until Luke supplies both values.
  - Completed `Steps A.2–A.4` (fail-closed check on both pins, runtime comparison of `sentence_transformers.__version__` against `SENTENCE_TRANSFORMERS_VERSION_PIN`, installed version in `identity()`, and unit tests with stubbed `sentence_transformers`) and all of `Steps B–I`.
  - Per Section 0 and Section 5, left the `INFRA-007` status row in [`docs/tasks/status.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/tasks/status.md) at `**needs-review**` with a one-line note recording `INFRA-007-R`, `INFRA-007-P` (`[D-66]`), and what remains pending (Luke supplying the two pins, one-time model download, and OpenMP timing check).

### 2.2 Summary of Completed Work (Steps A.2–I)
1. **Step A.2–A.4 (`src/graph_insertion/embedding_minilm.py`, `tests/test_embedding_minilm.py`):**
   - `MiniLMEmbedder.__init__` now fails closed with `ValueError` (naming the missing pin) if **either** `SENTENCE_TRANSFORMERS_VERSION_PIN` or the resolved model revision (`MODEL_REVISION_PIN` unless overridden by `revision=`) is `None` or blank/whitespace.
   - After lazily importing `sentence_transformers`, `__init__` reads `getattr(sentence_transformers, "__version__", None)` and raises `ValueError` showing both installed and pinned versions on mismatch. Passing `revision=` overrides only `MODEL_REVISION_PIN`, never the version check.
   - `MiniLMEmbedder.identity()` now records `"sentence_transformers_version": self.installed_version` alongside `"sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN`, `"model_name"`, `"dim"`, `"revision"`, `"device"`, and `"dtype"`.
2. **Step B (`scripts/run_experiment.py`, `tests/test_run_experiment_cli.py`):**
   - Replaced the inline sidecar check with `get_current_embedder_info()` and `check_resume_or_existing_directory_guard()`, executed whenever `has_existing_raw` (`<output_dir>/raw.jsonl` exists, with or without `--resume`) or `config.resume and sidecar_path.exists()`.
   - In addition to `strategy` and `config()`, the guard compares `mode` (`"sweep"` vs `"accuracy"`) and the `embedder` dictionary (`"type"`, `"model_name"`, `"dim"`, `"revision"`, `"sentence_transformers_version"` for `minilm`; `"type"`, `"dim"`, `"seed"` for `fake`), refusing any mismatch with exit code `1` and an `ERROR:` message on `stderr` showing both stored and current values.
   - Backward compatibility: a directory with `raw.jsonl` and no `strategy_config.json` keeps the legacy `WARNING:` behaviour; a sidecar written before `INFRA-007-P` that lacks `"sentence_transformers_version"` is not refused for that missing key alone (treats it as unrecorded, prints a single `WARNING:` to `stderr`, and still enforces all other keys).
3. **Step C (`scripts/run_experiment.py`, `tests/test_run_experiment_cli.py`):**
   - Deferred `MiniLMEmbedder()` construction until after both the `--dry-run` early exit and the explicit offline `if not config.confirm:` check, so `MiniLMEmbedder()` is constructed only when trials will actually execute.
   - Added end-to-end offline `--embedder minilm --confirm` sweep tests (`sizes=(12, 30)`, `2` trials) for `embedding_threshold` and `bounded_bucket` using a stub `sentence_transformers` module and monkeypatched pins, plus call-counter assertions proving zero `MiniLMEmbedder` constructions under `--dry-run` or without `--confirm`.
4. **Step D (`scripts/run_experiment.py`, `scripts/README.md`, `tests/test_run_experiment_cli.py`):**
   - On offline `--dry-run`, `main()` now calls `estimate_and_print_plan()` directly and returns `0` before `run_experiment()`, creating zero directories and zero files on disk (matching `--live --dry-run`).
   - On real runs (`--confirm`), `<output_dir>/strategy_config.json` is written via `warmup_fn=_write_sidecar_before_trials` passed to `run_experiment()` rather than before `run_experiment()`. Because `harness.py:write_manifest()` creates the empty `<output_dir>` (`git status --porcelain` ignores empty directories) and immediately captures `get_git_info()` before calling `warmup_fn` (which runs before `_load_existing_keys()`, `raw.jsonl`, and trial 1), `manifest.json` records `"git_dirty": false` on a clean checkout while `strategy_config.json` still exists on disk before the first trial starts — without touching `harness.py`.
5. **Step E (`src/graph_insertion/strategies/stub.py`, `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/run_experiment.py`, `tests/test_strategy_registry.py`):**
   - Created `src/graph_insertion/strategies/stub.py` containing `StubNarrowingStrategy` (unchanged class name, `.name == "stub_narrowing"`, and `.config()` keys).
   - Removed `register_stub` and `_get_stub_cls` from `registry.py` and imported `StubNarrowingStrategy` directly from `graph_insertion.strategies.stub`.
   - Re-exported `StubNarrowingStrategy` in `scripts/run_experiment.py` and lazily in `src/graph_insertion/strategies/__init__.py`.
6. **Step F & Step G (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`):**
   - Added non-vacuous unit and CLI tests with one-line docstrings closing all 7 surviving review mutants (`R-M11`, `R-M16`, `R-M19`, `R-M20`, `R-M24`, `R-M25`, `R-M26`) and all 8 new mutants (`P-M1`..`P-M8`), and verified on an isolated `/tmp` copy that **15/15 mutants are KILLED**.
   - Updated 3 existing dry-run assertions in `tests/test_run_experiment_cli.py` that previously encoded the old disk-writing `--dry-run` behaviour:
     1. `TestRunDirectoryKeysAndSidecarGuard::test_section_2d_default_run_directories_and_bounds_via_cli`: changed from asserting `strategy_config.json` exists after `--dry-run` to asserting `not expected_dir.exists()` and `not expected_acc_dir.exists()`.
     2. `TestRunDirectoryKeysAndSidecarGuard::test_non_default_seed_included_in_default_directory_and_strategy_config`: changed `--dry-run` check to assert `not expected_dir.exists()`, followed by a 1-trial `--confirm` run (`--sweep-sizes 6 --sweep-trials 1`) asserting `sidecar["config"]["seed"] == 99`.
     3. `TestRunDirectoryKeysAndSidecarGuard::test_explicit_run_id_and_output_dir_precedence`: changed from asserting `(custom_dir / "strategy_config.json").exists()` and `manifest.json` on `--dry-run` to asserting `not (tmp_path / "results" / "my_custom_id").exists()` and `not custom_dir.exists()` while checking the printed output path.
7. **Step H (`docs/decisions/decision-log.md`):**
   - Re-read `docs/decisions/decision-log.md` immediately before editing and appended `[D-66]` (covering all 5 required items, with no test counts and without editing `[D-64]`).

---

## 3. Prompt Corrections (Verification of Findings `F-1` to `F-7`)

Every background claim in Section 1 of the prompt was verified directly against the repository before editing:

- **Reserved Decision ID `D-66`:** `[Confirmed]` `grep -n "D-66" docs/decisions/decision-log.md` returned no matches prior to Step H (`[D-65]` was the highest used ID, added in commit `8d55ca6`).
- **F-1 (resume guard gap):** `[Confirmed]` In `fda97db` (`scripts/run_experiment.py:787-807`), the guard compared only `stored_sidecar.get("strategy")` and `stored_sidecar.get("config")`, ignoring `stored_sidecar.get("embedder")` and `stored_sidecar.get("mode")`.
- **F-2 (untested `minilm` branch and premature construction):** `[Confirmed]` Every `--embedder minilm` test in `tests/test_run_experiment_cli.py` passed `--live --dry-run` (returning at line 890 before line 929), and in offline mode without `--dry-run` or `--confirm`, `MiniLMEmbedder()` was constructed at lines 942–961 before `run_experiment()` validated `config.confirm` in `HarnessConfig` / `run_experiment()`.
- **F-3 (pins and runtime package version check):** `[Confirmed]` `src/graph_insertion/embedding_minilm.py:67-75` checked only `actual_revision` (`MODEL_REVISION_PIN`), never `SENTENCE_TRANSFORMERS_VERSION_PIN` or `sentence_transformers.__version__`, and `identity()` recorded only `"sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN`.
- **F-4 (dry-run side effect, pre-INFRA-007 `--dry-run` check, and `R-M26`):** `[Confirmed]`
  - Verified pre-`INFRA-007` behaviour via `git show fda97db~1:scripts/run_experiment.py`: before `INFRA-007`, `--live --dry-run` exited `0` before `run_experiment()` and wrote nothing to disk, whereas plain offline `--dry-run` called `run_experiment()` which called `write_manifest(config, plan)` (`src/graph_insertion/harness.py:938`), creating `<output_dir>/manifest.json`.
  - `INFRA-007` (`fda97db`) added `strategy_config.json` creation before `run_experiment()` (even on offline `--dry-run`). Because `results/` is not git-ignored, writing `results/<run_id>/strategy_config.json` before `write_manifest()` runs `get_git_info()` (`git status --porcelain`) caused `manifest.json` to record `"git_dirty": true` on a clean checkout.
- **F-5 (library depends on `scripts`):** `[Confirmed]` `src/graph_insertion/strategies/registry.py:30-35` (`_get_stub_cls`) imported `from scripts.run_experiment import StubNarrowingStrategy`, which raised `ModuleNotFoundError: No module named 'scripts'` when `cwd=/tmp` and `PYTHONPATH=src`.
- **F-6 (implementer report):** `[Confirmed]` `docs/reports/INFRA-007-gemini-strategy-wiring.md` lacked a "Found but not changed" section and line 2562 passed `revision='<MODEL_REVISION_PIN>'` in its OpenMP timing snippet.
- **F-7 (surviving mutants `R-M11, 16, 19, 20, 24, 25, 26`):** `[Confirmed]` All 7 surviving mutants from `docs/reports/INFRA-007-R-gemini.md` matched the exact code lines and test gaps reported by the reviewer.

---

## 4. Verification Output

### 4.1 Pre-Edit State (`git status --short`, `git log --oneline -5`, `sha256sum`, `wc -l`, Baseline Pytest)

```text
$ git status --short && git log --oneline -5
M  docs/context/complete-context.md
M  docs/context/data-formats.md
A  docs/reports/DOC-002-gemini.md
M  docs/tasks/status.md
M  "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
00938dc (HEAD -> master, origin/master, origin/HEAD) INFRA-007-R: independent review of strategy wiring (D-64)
e276c37 docs: update name-pool generation runbook for sharded supervisor flow (D-65)
8d55ca6 docs: record DATA-004 pool acceptance (D-65), close DATA-004 and FIX-017
fda97db INFRA-007: wire four strategies, parameters, run-directory keys and pinned embedder into the experiment CLI (D-64)
4f6de3d DATA-004: add generated name pool np1w (2254 names, 3 shards, Sonnet 5 Low, adapter ba3a8a2)
```
*(Note: The `DOC-002` changes above were from a concurrent task merged by Luke into `master` as commit `babd0b8` during this session; only the Section 2 files for `INFRA-007-P` are staged/committed in Step 8.)*

```text
=== BEFORE sha256sum ===
944969492d8d3c5e75713c127d3e5262c7d2d1ca3beada4df11c3639afa2fbce  scripts/run_experiment.py
73cf5c85d55e0782a5fd2497fdc5c5467a1963e433f99105e133b4d1ef08723a  src/graph_insertion/embedding_minilm.py
e8b596ce52f9e2239f2d8b7cfbe6d96e8d08957a51a934eea5d53334014b3e7a  src/graph_insertion/strategies/registry.py
130d5d62b8e41c9ec783df80a2fe8f050c86ce515ed99c79d885996ae628b291  src/graph_insertion/strategies/__init__.py
c800a37d021c63210ad795d30812cb38bb979625fcf06c2b4a91d6b49d7bf9ab  scripts/README.md
27c646b28c96eaf105c25e5174f48a1602cdbcfda7d70db282fb43f3e63d4bec  tests/test_strategy_registry.py
36b2c4326cbcd14cde2ce4fd9a71c315c95d0a889c8afb76841c3248cfc36369  tests/test_embedding_minilm.py
66b5472a55cdda5ce7059e344f546e85d5b67db2e4929ae2876e37140727168a  tests/test_run_experiment_cli.py
66517502485d323747108062c9876c3254887c90cf531fa26341ebd7cfb8e4e2  docs/decisions/decision-log.md
eca1cf139a73c647e050f3e9e38ba33eb25022374e314de78082a0f6272c481d  docs/tasks/status.md

=== BEFORE wc -l ===
  1038 scripts/run_experiment.py
   128 src/graph_insertion/embedding_minilm.py
   250 src/graph_insertion/strategies/registry.py
    36 src/graph_insertion/strategies/__init__.py
   199 scripts/README.md
   195 tests/test_strategy_registry.py
   199 tests/test_embedding_minilm.py
   814 tests/test_run_experiment_cli.py
   530 docs/decisions/decision-log.md
    99 docs/tasks/status.md
```

Baseline full-suite run (Rule 3, run once before edits):
```text
$ .venv-ann/bin/python -m pytest | tail -3
tests/test_strategy_registry.py::TestStrategyRegistry::test_lazy_exports_from_strategies_package PASSED [100%]

================== 674 passed, 3 skipped in 115.75s (0:01:55) ==================
```

### 4.2 Post-Edit Targeted & Full-Suite Test Runs

Targeted 6-file run after edits (Rule 3):
```text
$ .venv-ann/bin/python -m pytest tests/test_strategy_registry.py tests/test_embedding_minilm.py tests/test_run_experiment_cli.py tests/test_null_strategy.py tests/test_live_guard.py tests/test_dry_run_plan.py
================== 171 passed, 1 skipped in 19.24s ==================
```

Final single full-suite run (Rule 3):
```text
$ .venv-ann/bin/python -m pytest | tail -3
tests/test_strategy_registry.py::TestStrategyRegistry::test_stub_isolated_import_and_no_scripts_dependency_kills_pm7 PASSED [100%]

================== 683 passed, 3 skipped in 137.56s (0:02:17) ==================
```

### 4.3 Dry-Run Zero-Disk-Write Transcript (`ls` Before and After)

```text
$ rm -rf /tmp/infra007p-dryrun-check && mkdir -p /tmp/infra007p-dryrun-check && ls -la /tmp/infra007p-dryrun-check && .venv-ann/bin/python scripts/run_experiment.py --mode sweep --strategy bounded_bucket --dry-run --output-dir /tmp/infra007p-dryrun-check/out_offline && ls -la /tmp/infra007p-dryrun-check && .venv-ann/bin/python scripts/run_experiment.py --live --dry-run --mode sweep --strategy bounded_bucket --embedder minilm --names-file data/synthetic/cs_concept_names.json --output-dir /tmp/infra007p-dryrun-check/out_live && ls -la /tmp/infra007p-dryrun-check
total 0
drwxr-xr-x  2 lukexodus lukexodus  40 Oct 12 17:51 .
drwxrwxrwt 30 root      root      880 Oct 12 17:51 ..
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: bounded_bucket
Strategy Config: {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  100 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  200 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  500 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 1000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 2000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 600
======================================================================
Default/resolved output directory: /tmp/infra007p-dryrun-check/out_offline
Dry run complete.
total 0
drwxr-xr-x  2 lukexodus lukexodus  40 Oct 12 17:51 .
drwxrwxrwt 30 root      root      880 Oct 12 17:51 ..
=================================================================
LIVE EXPERIMENT PRE-FLIGHT ESTIMATE
Strategy:                      bounded_bucket
Strategy config:               {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
Embedder:                      minilm
Output directory:              /tmp/infra007p-dryrun-check/out_live
Model alias:                   deepseek-flash
Full-plan calls (upper bound): 600
Remaining calls (upper bound): 600
Estimated duration:            600.0s (10.0 min) (assuming 1.0s/call)
Estimated cost:                $0.0146 USD
Cost assumptions:              ~152 in, ~2.5 out tokens/call at $0.15/M in, $0.60/M out
-----------------------------------------------------------------
Current UTC:  2026-10-12 09:51:25 UTC
Philippine:   2026-10-12 17:51:25 PHT (UTC+8)
DeepSeek:     PEAK (charged at peak rates)
=================================================================
Peak check note: Planned execution window [09:51:25, 10:01:25 UTC] intersects DeepSeek peak pricing hours (01:00-04:00 or 06:00-10:00 UTC Mon-Fri). A real live run would be REFUSED unless '--allow-peak' is passed.
Dry run complete (live pre-flight estimation only; no API calls or client construction).
total 0
drwxr-xr-x  2 lukexodus lukexodus  40 Oct 12 17:51 .
drwxrwxrwt 30 root      root      880 Oct 12 17:51 ..
```

### 4.4 Post-Edit `sha256sum`, `wc -l`, and `git status --short`

```text
=== AFTER sha256sum ===
e1d8a5047c2f4120d5e8b81ce81c57956f4aeafcac27fe45c6467fd2edaa34f5  scripts/run_experiment.py
95593ed28d6b6469d474255fa5bef0d3c71652ab74ec44a834664a142f3f50e1  src/graph_insertion/embedding_minilm.py
243837aac38275a482f8791442434cadca747085862a184f5d0bf08ad8268e10  src/graph_insertion/strategies/registry.py
d149b13380237a8e03aa604e9803974787901435d5bde5835bc85b069aa286f8  src/graph_insertion/strategies/stub.py
1951cacbf7d7039cabfbebd919c788200b7fe40fac6b295bf0b750674b6a84fc  src/graph_insertion/strategies/__init__.py
faf4ad5f45c0b6dcb1a8c6397f33bc1f5366d30daa333a80a9540a4e3cd88247  scripts/README.md
6eff921412506b31e60aa020f8d3d2b1a1793a933c7dac8a01bc5d9b36af1478  tests/test_strategy_registry.py
a42a0f707ce21a673994f37773633c346d48591060adf17dbda6205b9cf64a04  tests/test_embedding_minilm.py
af144db8c9087f7380069279a16d7eed56a1e9d11b794258fff1a5953c4b1b9c  tests/test_run_experiment_cli.py
8e9d0d0fc5475864886327aa8b5193cf71e35d75db8f9616be2f5970eadff87a  docs/decisions/decision-log.md
99a40706f997bc6e0b195499ed5be8d7217dcb496e353dd7bf5cca2b55294698  docs/tasks/status.md

=== AFTER wc -l ===
  1140 scripts/run_experiment.py
   148 src/graph_insertion/embedding_minilm.py
   235 src/graph_insertion/strategies/registry.py
    47 src/graph_insertion/strategies/stub.py
    40 src/graph_insertion/strategies/__init__.py
   200 scripts/README.md
   233 tests/test_strategy_registry.py
   308 tests/test_embedding_minilm.py
  1312 tests/test_run_experiment_cli.py
   536 docs/decisions/decision-log.md
    99 docs/tasks/status.md
  4298 total

=== git status --short ===
 M docs/context/repo-tree.txt
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M scripts/README.md
 M scripts/run_experiment.py
 M src/graph_insertion/embedding_minilm.py
 M src/graph_insertion/strategies/__init__.py
 M src/graph_insertion/strategies/registry.py
 M tests/test_embedding_minilm.py
 M tests/test_run_experiment_cli.py
 M tests/test_strategy_registry.py
?? src/graph_insertion/strategies/stub.py
```

---

## 5. Mutation Table (`R-M11, 16, 19, 20, 24, 25, 26` and `P-M1` .. `P-M8`)

All 15 mutants (the 7 surviving mutants from `INFRA-007-R` remapped to the new line locations plus the 8 new `INFRA-007-P` mutants `P-M1`..`P-M8`) were executed one at a time with `-x` against `/tmp/infra007p-mutants` (`PYTHONPATH=/tmp/infra007p-mutants/src:/tmp/infra007p-mutants`) using only the single relevant test file.

**Summary:** **`15/15 KILLED`**, **`0 SURVIVED`** (`[Confirmed]`).

| Mutant | Remapped Target `file:line` | Mutation Applied | Test File Run (`-x`) | Result | Killer Test (`[Confirmed]`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-M11** | `scripts/run_experiment.py:724` ( also `712`) | Require `config_resume` before checking sidecar mismatch (`if not config_resume: return 0`) even when `has_existing_raw` is `True` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw` (and `test_older_directory_with_raw_jsonl_but_no_sidecar_warns_and_does_not_refuse` if gated at line 712) |
| **R-M16** | `src/graph_insertion/embedding_minilm.py:130-131` | Remove `if arr.ndim == 1 and len(texts) == 1: arr = arr.reshape(1, -1)` in `embed_many` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_embed_many_single_item_reshape_kills_rm16` |
| **R-M19** | `scripts/run_experiment.py:1059` | Replace `if not uses_embeddings or args.embedder == "fake":` with `if True:` (always use `FakeEmbedder`) | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw` (also killed by `test_minilm_offline_execution_and_construction_timing_kills_rm19_and_pm5`) |
| **R-M20** | `src/graph_insertion/embedding_minilm.py:129` | Replace `np.asarray(mat, dtype=np.float32)` with `np.asarray(mat)` in `embed_many` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_embed_many_float64_casted_to_float32_kills_rm20` |
| **R-M24** | `src/graph_insertion/strategies/__init__.py:37-39` | Remove `STRATEGY_FACTORIES` branch from `strategies/__init__.py:__getattr__` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_lazy_export_strategy_factories_kills_rm24` |
| **R-M25** | `src/graph_insertion/embedding_minilm.py:118-121` | Remove `if arr.shape != (self.dim,): raise ValueError(...)` in `MiniLMEmbedder.embed` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_wrong_dimension_encoder_output_raises_value_error_kills_rm25` |
| **R-M26** | `scripts/run_experiment.py:1122-1131` | Pass `warmup_fn=None` to `run_experiment()` and call `_write_sidecar_before_trials()` *after* `run_experiment()` returns | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_dry_run_creates_nothing_and_real_run_sidecar_before_trial1_and_git_dirty_false_kills_rm26_and_pm6` |
| **P-M1** | `src/graph_insertion/embedding_minilm.py:71-79` | Pin check compares only `MODEL_REVISION_PIN` (remove `SENTENCE_TRANSFORMERS_VERSION_PIN` fail-closed check) | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_refuses_when_pin_is_none_or_empty` |
| **P-M2** | `src/graph_insertion/embedding_minilm.py:101-105` | Remove runtime check `if installed_ver != SENTENCE_TRANSFORMERS_VERSION_PIN:` in `MiniLMEmbedder.__init__` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_version_mismatch_refused_and_match_passes` |
| **P-M3** | `scripts/run_experiment.py:753-754` | Resume guard ignores `embedder` block (`if False and stored_embedder is not None:`) | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw` |
| **P-M4** | `scripts/run_experiment.py:744-745` | Resume guard ignores `mode` (`if False and stored_mode is not None and stored_mode != current_mode:`) | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw` |
| **P-M5** | `scripts/run_experiment.py:1048` | Construct `MiniLMEmbedder()` unconditionally in the offline branch before `if not config.confirm:` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestINFRA007PAmendments::test_minilm_offline_execution_and_construction_timing_kills_rm19_and_pm5` |
| **P-M6** | `scripts/run_experiment.py:1036-1045` | Write `strategy_config.json` inside `if config.dry_run:` before returning `0` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_section_2d_default_run_directories_and_bounds_via_cli[primary_s1_brute_force-...]` (and `test_dry_run_creates_nothing_and_real_run_sidecar_before_trial1_and_git_dirty_false_kills_rm26_and_pm6`) |
| **P-M7** | `src/graph_insertion/strategies/registry.py:59` | Import `StubNarrowingStrategy` from `scripts.run_experiment` inside `_factory_stub` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_stub_isolated_import_and_no_scripts_dependency_kills_pm7` |
| **P-M8** | `src/graph_insertion/embedding_minilm.py:144` | `identity()` records `SENTENCE_TRANSFORMERS_VERSION_PIN` instead of `self.installed_version` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_identity_metadata_content_and_json_serializable` |

---

## 6. Diffs

### 6.1 `scripts/run_experiment.py` (`git diff`)

```diff
diff --git i/scripts/run_experiment.py w/scripts/run_experiment.py
index b637119..3acfb8a 100644
--- i/scripts/run_experiment.py
+++ w/scripts/run_experiment.py
@@ -46,6 +46,7 @@ from graph_insertion.harness import (
     SyntheticNameSource,
     _load_existing_keys,
     accuracy_trial_key,
+    estimate_and_print_plan,
     run_experiment,
     sample_heldout_nodes,
     sweep_trial_key,
@@ -61,7 +62,6 @@ from graph_insertion.strategies.registry import (
     build_strategy_slug,
     check_applicability,
     derive_default_run_id,
-    register_stub,
 )
 from graph_insertion.strategy import (
     DecisionOutcome,
@@ -78,39 +78,7 @@ _SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
 # Local Test Stubs
 # ===========================================================================
 
-class StubNarrowingStrategy:
-    """Minimal deterministic narrowing strategy for harness testing and dry runs."""
-
-    name: str = "stub_narrowing"
-    uses_embeddings: bool = False
-
-    def __init__(self, top_k: int = 5) -> None:
-        self.top_k = top_k
-        self._graph: Optional[ConceptGraph] = None
-        self._embedder: Optional[Embedder] = None
-
-    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
-        self._graph = graph
-        self._embedder = None
-
-    def shortlist(self, new_name: str) -> Shortlist:
-        if not self._graph:
-            return Shortlist(candidates=())
-        nodes = sorted(self._graph.nodes())
-        candidates = tuple(nodes[: self.top_k])
-        return Shortlist(candidates=candidates)
-
-    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
-        pass
-
-    def config(self) -> dict[str, Any]:
-        return {"name": self.name, "top_k": self.top_k}
-
-    def diagnostics(self) -> dict[str, Any]:
-        return {}
-
-    def max_candidates(self, n_existing: int) -> int:
-        return min(self.top_k, n_existing)
+from graph_insertion.strategies.stub import StubNarrowingStrategy
 
 
 class StubDecisionStep:
@@ -136,7 +104,6 @@ class StubDecisionStep:
 # Strategy Registry (INFRA-007)
 # ===========================================================================
 
-register_stub(StubNarrowingStrategy)
 STRATEGY_REGISTRY: dict[str, Callable[..., NarrowingStrategy]] = STRATEGY_FACTORIES
 
 
@@ -691,6 +658,148 @@ def build_sidecar_payload(
     return payload
 
 
+def get_current_embedder_info(
+    args: Any,
+    uses_embeddings: bool,
+    seed: int,
+) -> dict[str, Any]:
+    """Determine expected embedder information block without eagerly instantiating models."""
+    if not uses_embeddings or args.embedder == "fake":
+        return {
+            "type": "fake",
+            "uses_embeddings": uses_embeddings,
+            "dim": 32,
+            "seed": int(seed),
+        }
+    from graph_insertion.embedding_minilm import (
+        MODEL_DIM,
+        MODEL_NAME,
+        MODEL_REVISION_PIN,
+        SENTENCE_TRANSFORMERS_VERSION_PIN,
+    )
+    st_version = SENTENCE_TRANSFORMERS_VERSION_PIN
+    try:
+        import sentence_transformers
+        st_version = getattr(sentence_transformers, "__version__", SENTENCE_TRANSFORMERS_VERSION_PIN)
+    except Exception:
+        pass
+
+    return {
+        "type": "minilm",
+        "uses_embeddings": True,
+        "model_name": MODEL_NAME,
+        "dim": int(MODEL_DIM),
+        "revision": MODEL_REVISION_PIN,
+        "sentence_transformers_version": st_version,
+        "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
+        "device": "cpu",
+        "dtype": "float32",
+    }
+
+
+def check_resume_or_existing_directory_guard(
+    output_dir: Path,
+    raw_jsonl_path: Path,
+    sidecar_path: Path,
+    has_existing_raw: bool,
+    config_resume: bool,
+    current_strategy: str,
+    current_config: dict[str, Any],
+    current_mode: str,
+    current_embedder_info: dict[str, Any],
+) -> int:
+    """Check resume and existing-directory compatibility against sidecar."""
+    if not (has_existing_raw or (config_resume and sidecar_path.exists())):
+        return 0
+
+    if not sidecar_path.exists():
+        if has_existing_raw:
+            print(
+                f"WARNING: Existing {raw_jsonl_path} found without {sidecar_path}; "
+                "proceeding without sidecar mismatch check and not writing sidecar to non-fresh directory.",
+                file=sys.stderr,
+            )
+        return 0
+
+    try:
+        stored_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
+    except Exception as err:
+        print(
+            f"ERROR: Failed to parse existing {sidecar_path}: {err}",
+            file=sys.stderr,
+        )
+        return 1
+
+    stored_strategy = stored_sidecar.get("strategy")
+    stored_config = stored_sidecar.get("config")
+    if stored_strategy != current_strategy or stored_config != current_config:
+        print(
+            f"ERROR: Strategy configuration mismatch in {output_dir}: "
+            f"stored strategy={stored_strategy!r} config={stored_config} vs "
+            f"current strategy={current_strategy!r} config={current_config}",
+            file=sys.stderr,
+        )
+        return 1
+
+    stored_mode = stored_sidecar.get("mode")
+    if stored_mode is not None and stored_mode != current_mode:
+        print(
+            f"ERROR: Harness mode mismatch in {output_dir}: "
+            f"stored mode={stored_mode!r} vs current mode={current_mode!r}",
+            file=sys.stderr,
+        )
+        return 1
+
+    stored_embedder = stored_sidecar.get("embedder")
+    if stored_embedder is not None:
+        stored_type = stored_embedder.get("type")
+        current_type = current_embedder_info.get("type")
+
+        if stored_type != current_type:
+            print(
+                f"ERROR: Embedder type mismatch in {output_dir}: "
+                f"stored embedder={stored_embedder} vs current embedder={current_embedder_info}",
+                file=sys.stderr,
+            )
+            return 1
+
+        if current_type == "minilm":
+            keys_to_compare = ["model_name", "dim", "revision"]
+            for k in keys_to_compare:
+                if stored_embedder.get(k) != current_embedder_info.get(k):
+                    print(
+                        f"ERROR: Embedder configuration mismatch in {output_dir} (key {k!r}): "
+                        f"stored embedder={stored_embedder} vs current embedder={current_embedder_info}",
+                        file=sys.stderr,
+                    )
+                    return 1
+            if "sentence_transformers_version" not in stored_embedder:
+                print(
+                    f"WARNING: Existing sidecar in {output_dir} does not record sentence_transformers_version; "
+                    "treating as legacy/unrecorded and proceeding.",
+                    file=sys.stderr,
+                )
+            else:
+                if stored_embedder.get("sentence_transformers_version") != current_embedder_info.get("sentence_transformers_version"):
+                    print(
+                        f"ERROR: Embedder configuration mismatch in {output_dir} (key 'sentence_transformers_version'): "
+                        f"stored embedder={stored_embedder} vs current embedder={current_embedder_info}",
+                        file=sys.stderr,
+                    )
+                    return 1
+        elif current_type == "fake":
+            for k in ["dim", "seed"]:
+                if stored_embedder.get(k) != current_embedder_info.get(k):
+                    print(
+                        f"ERROR: Embedder configuration mismatch in {output_dir} (key {k!r}): "
+                        f"stored embedder={stored_embedder} vs current embedder={current_embedder_info}",
+                        file=sys.stderr,
+                    )
+                    return 1
+
+    return 0
+
+
 def main() -> int:
     parser = build_parser()
     args = parser.parse_args()
@@ -773,35 +882,22 @@ def main() -> int:
     sidecar_path = output_dir / "strategy_config.json"
     has_existing_raw = raw_jsonl_path.exists()
 
+    current_embedder_info = get_current_embedder_info(args, uses_embeddings, config.seed)
+
     # Configuration guard on --resume or any run into an existing directory with raw.jsonl
-    if has_existing_raw or (config.resume and sidecar_path.exists()):
-        if sidecar_path.exists():
-            try:
-                stored_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
-            except Exception as err:
-                print(
-                    f"ERROR: Failed to parse existing {sidecar_path}: {err}",
-                    file=sys.stderr,
-                )
-                return 1
-            stored_strategy = stored_sidecar.get("strategy")
-            stored_config = stored_sidecar.get("config")
-            current_strategy = uninitialized_strategy.name
-            current_config = uninitialized_strategy.config()
-            if stored_strategy != current_strategy or stored_config != current_config:
-                print(
-                    f"ERROR: Strategy configuration mismatch in {output_dir}: "
-                    f"stored strategy={stored_strategy!r} config={stored_config} vs "
-                    f"current strategy={current_strategy!r} config={current_config}",
-                    file=sys.stderr,
-                )
-                return 1
-        elif has_existing_raw:
-            print(
-                f"WARNING: Existing {raw_jsonl_path} found without {sidecar_path}; "
-                "proceeding without sidecar mismatch check and not writing sidecar to non-fresh directory.",
-                file=sys.stderr,
-            )
+    guard_rc = check_resume_or_existing_directory_guard(
+        output_dir=output_dir,
+        raw_jsonl_path=raw_jsonl_path,
+        sidecar_path=sidecar_path,
+        has_existing_raw=has_existing_raw,
+        config_resume=config.resume,
+        current_strategy=uninitialized_strategy.name,
+        current_config=uninitialized_strategy.config(),
+        current_mode=config.mode,
+        current_embedder_info=current_embedder_info,
+    )
+    if guard_rc != 0:
+        return guard_rc
 
     # Corpora selection
     corpora = None
@@ -915,7 +1011,49 @@ def main() -> int:
         except ImportError:
             decision_step = StubDecisionStep()
 
-    # Embedder factory wiring
+    # Synthetic name source for sweep (C4, FIX-008)
+    name_source = None
+    if config.mode == "sweep":
+        max_size = max(config.sweep_sizes) if config.sweep_sizes else 2000
+        min_names_needed = max_size + 1
+
+        if args.names_file:
+            try:
+                names = load_and_validate_names_file(Path(args.names_file), min_names_needed)
+            except Exception as err:
+                print(f"Experiment execution failed: {err}", file=sys.stderr)
+                return 1
+            name_source = SyntheticNameSource(names=names, domain_context="computer science")
+        else:
+            total_names_needed = max_size + 100
+            placeholder_names = [f"synthetic_concept_{i:05d}" for i in range(total_names_needed)]
+            name_source = SyntheticNameSource(
+                names=placeholder_names,
+                domain_context="computer science",
+            )
+
+    # Offline dry-run: print plan and resolved output directory without creating any directory or file on disk
+    if config.dry_run:
+        estimate_and_print_plan(
+            config,
+            uninitialized_strategy,
+            corpora=corpora,
+            name_source=name_source,
+        )
+        print(f"Default/resolved output directory: {output_dir}")
+        print("Dry run complete.")
+        return 0
+
+    # Offline confirm check: abort before constructing expensive or download-triggering models
+    if not config.confirm:
+        print(
+            "Experiment execution failed: Live experiment runs require explicit confirmation "
+            "via config.confirm=True (or CLI flag --confirm) to prevent accidental API consumption.",
+            file=sys.stderr,
+        )
+        return 1
+
+    # Embedder factory wiring (constructed only when trials will actually execute)
     embedder_factory: Callable[[], Embedder]
     embedder_info: dict[str, Any]
     if not uses_embeddings or args.embedder == "fake":
@@ -927,55 +1065,19 @@ def main() -> int:
             "seed": int(config.seed),
         }
     else:
-        from graph_insertion.embedding_minilm import (
-            MODEL_DIM,
-            MODEL_NAME,
-            MODEL_REVISION_PIN,
-            SENTENCE_TRANSFORMERS_VERSION_PIN,
-            MiniLMEmbedder,
-        )
+        from graph_insertion.embedding_minilm import MiniLMEmbedder
 
-        if config.dry_run:
-            embedder_factory = lambda: FakeEmbedder(dim=MODEL_DIM, seed=config.seed)
-            embedder_info = {
-                "type": "minilm",
-                "uses_embeddings": True,
-                "model_name": MODEL_NAME,
-                "dim": int(MODEL_DIM),
-                "revision": MODEL_REVISION_PIN,
-                "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
-                "device": "cpu",
-                "dtype": "float32",
-            }
-        else:
-            try:
-                minilm_instance = MiniLMEmbedder()
-            except (ImportError, ValueError) as err:
-                print(f"ERROR: {err}", file=sys.stderr)
-                return 1
-            embedder_factory = lambda: minilm_instance
-            embedder_info = {
-                "type": "minilm",
-                "uses_embeddings": True,
-                **minilm_instance.identity(),
-            }
-
-    # Synthetic name source for sweep (C4, FIX-008)
-    name_source = None
-    if config.mode == "sweep":
-        max_size = max(config.sweep_sizes) if config.sweep_sizes else 2000
-        min_names_needed = max_size + 1
-
-        if args.names_file:
-            names = load_and_validate_names_file(Path(args.names_file), min_names_needed)
-            name_source = SyntheticNameSource(names=names, domain_context="computer science")
-        else:
-            total_names_needed = max_size + 100
-            placeholder_names = [f"synthetic_concept_{i:05d}" for i in range(total_names_needed)]
-            name_source = SyntheticNameSource(
-                names=placeholder_names,
-                domain_context="computer science",
-            )
+        try:
+            minilm_instance = MiniLMEmbedder()
+        except (ImportError, ValueError) as err:
+            print(f"ERROR: {err}", file=sys.stderr)
+            return 1
+        embedder_factory = lambda: minilm_instance
+        embedder_info = {
+            "type": "minilm",
+            "uses_embeddings": True,
+            **minilm_instance.identity(),
+        }
 
     # Progress reporter setup (call-driven heartbeat)
     progress_reporter = ProgressReporter(
@@ -1002,17 +1104,20 @@ def main() -> int:
     }
 
     try:
-        # Write sidecar strategy_config.json BEFORE the first trial on a fresh directory
-        if not has_existing_raw and (config.dry_run or config.confirm):
-            output_dir.mkdir(parents=True, exist_ok=True)
+        sidecar_payload: Optional[dict[str, Any]] = None
+        if not has_existing_raw:
             sidecar_payload = build_sidecar_payload(
                 strategy=uninitialized_strategy,
                 embedder_info=embedder_info,
                 mode=config.mode,
                 command_line_params=command_line_params,
             )
-            with open(sidecar_path, "w", encoding="utf-8") as sf:
-                json.dump(sidecar_payload, sf, indent=2)
+
+        def _write_sidecar_before_trials() -> None:
+            if sidecar_payload is not None:
+                output_dir.mkdir(parents=True, exist_ok=True)
+                with open(sidecar_path, "w", encoding="utf-8") as sf:
+                    json.dump(sidecar_payload, sf, indent=2)
 
         result = run_experiment(
             config=config,
@@ -1021,13 +1126,10 @@ def main() -> int:
             embedder_factory=embedder_factory,
             corpora=corpora,
             name_source=name_source,
+            warmup_fn=_write_sidecar_before_trials,
             progress_callback=progress_reporter.update,
         )
-        if config.dry_run:
-            print(f"Default/resolved output directory: {output_dir}")
-            print("Dry run complete. Plan recorded in manifest.json.")
-        else:
-            print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
+        print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
         return 0
     except Exception as e:
         print(f"Experiment execution failed: {e}", file=sys.stderr)
```

### 6.2 `src/graph_insertion/embedding_minilm.py` (`git diff`)

```diff
diff --git i/src/graph_insertion/embedding_minilm.py w/src/graph_insertion/embedding_minilm.py
index b461eaa..80331d5 100644
--- i/src/graph_insertion/embedding_minilm.py
+++ w/src/graph_insertion/embedding_minilm.py
@@ -10,6 +10,8 @@ Decisions:
     version pinned.
   - [D-64]: Live runs of embedding strategies require ``--embedder minilm``;
     ``--embedder fake`` is refused for live embedding strategies.
+  - [D-66]: Version and model revision pins, runtime check against installed
+    package version, fail-closed on unset pins.
 """
 
 from __future__ import annotations
@@ -21,17 +23,13 @@ import numpy as np
 
 # ---------------------------------------------------------------------------
 # Pins — MUST be set to actual values before any live run.
-# If MODEL_REVISION_PIN is None the embedder refuses to initialise (fail-closed).
+# If either pin is None or blank, MiniLMEmbedder refuses to initialise (fail-closed).
 # ---------------------------------------------------------------------------
 
 # Pin: sentence-transformers package version installed in .venv-ann.
-# Cannot be determined offline (sentence-transformers is not installed).
-# Luke must supply this value.
 SENTENCE_TRANSFORMERS_VERSION_PIN: Optional[str] = None
 
 # Pin: Hugging Face model revision (commit hash) for all-MiniLM-L6-v2.
-# Cannot be determined offline (model is not cached locally).
-# Luke must supply this value.
 MODEL_REVISION_PIN: Optional[str] = None
 
 MODEL_NAME: str = "all-MiniLM-L6-v2"
@@ -50,7 +48,7 @@ class MiniLMEmbedder:
     Parameters
     ----------
     revision :
-        Model revision (commit hash).  Defaults to ``MODEL_REVISION_PIN``.
+        Model revision (commit hash). Defaults to ``MODEL_REVISION_PIN``.
         If ``None`` or empty at construction time, raises ``ValueError``
         (fail-closed).
 
@@ -62,23 +60,36 @@ class MiniLMEmbedder:
         Always 384.
     revision : str
         Pinned model revision hash.
+    installed_version : str
+        Installed version of sentence-transformers library.
     """
 
     model_name: str = MODEL_NAME
     dim: int = MODEL_DIM
 
     def __init__(self, revision: Any = _UNSET) -> None:
+        if (
+            not isinstance(SENTENCE_TRANSFORMERS_VERSION_PIN, str)
+            or not SENTENCE_TRANSFORMERS_VERSION_PIN.strip()
+        ):
+            raise ValueError(
+                "MiniLMEmbedder requires a pinned sentence-transformers package version. "
+                f"SENTENCE_TRANSFORMERS_VERSION_PIN is currently {SENTENCE_TRANSFORMERS_VERSION_PIN!r}. "
+                "Cannot proceed without a version pin (fail-closed)."
+            )
+
         actual_revision = MODEL_REVISION_PIN if revision is _UNSET else revision
         if not isinstance(actual_revision, str) or not actual_revision.strip():
             raise ValueError(
                 "MiniLMEmbedder requires a pinned model revision. "
-                "Set MODEL_REVISION_PIN in embedding_minilm.py or pass a non-empty "
-                "revision= string to the constructor. Cannot proceed without a pin (fail-closed)."
+                f"MODEL_REVISION_PIN is currently {MODEL_REVISION_PIN!r} (passed revision={revision!r}). "
+                "Cannot proceed without a revision pin (fail-closed)."
             )
         self.revision: str = actual_revision
 
         # Lazy import of sentence_transformers
         try:
+            import sentence_transformers
             from sentence_transformers import SentenceTransformer
         except ImportError:
             raise ImportError(
@@ -86,6 +97,14 @@ class MiniLMEmbedder:
                 "Install with: pip install -e \".[embed]\""
             ) from None
 
+        installed_ver = getattr(sentence_transformers, "__version__", None)
+        if installed_ver != SENTENCE_TRANSFORMERS_VERSION_PIN:
+            raise ValueError(
+                f"sentence-transformers version mismatch: installed={installed_ver!r} "
+                f"vs pinned={SENTENCE_TRANSFORMERS_VERSION_PIN!r}."
+            )
+        self.installed_version: str = str(installed_ver)
+
         self._model = SentenceTransformer(
             self.model_name,
             revision=self.revision,
@@ -122,6 +141,7 @@ class MiniLMEmbedder:
             "model_name": self.model_name,
             "dim": int(self.dim),
             "revision": self.revision,
+            "sentence_transformers_version": self.installed_version,
             "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
             "device": "cpu",
             "dtype": "float32",
```

### 6.3 `src/graph_insertion/strategies/registry.py` (`git diff`)

```diff
diff --git i/src/graph_insertion/strategies/registry.py w/src/graph_insertion/strategies/registry.py
index 40e9f73..cf17a9d 100644
--- i/src/graph_insertion/strategies/registry.py
+++ w/src/graph_insertion/strategies/registry.py
@@ -18,21 +18,7 @@ from typing import Any, Callable, Optional
 
 from graph_insertion.strategy import NarrowingStrategy
 
-_STUB_CLS: Optional[type] = None
-
-
-def register_stub(stub_cls: type) -> None:
-    """Register the StubNarrowingStrategy class from scripts/run_experiment.py."""
-    global _STUB_CLS
-    _STUB_CLS = stub_cls
-
-
-def _get_stub_cls() -> type:
-    global _STUB_CLS
-    if _STUB_CLS is None:
-        from scripts.run_experiment import StubNarrowingStrategy
-        _STUB_CLS = StubNarrowingStrategy
-    return _STUB_CLS
+from graph_insertion.strategies.stub import StubNarrowingStrategy
 
 
 def _factory_null(
@@ -67,11 +53,10 @@ def _factory_stub(
     n_bits: Optional[int] = None,
     **params: Any,
 ) -> NarrowingStrategy:
-    stub_cls = _get_stub_cls()
     actual_k = 5 if k is None else k
     if isinstance(actual_k, bool) or not isinstance(actual_k, int) or actual_k < 1:
         raise ValueError(f"k must be >= 1, got {actual_k}")
-    return stub_cls(top_k=actual_k)
+    return StubNarrowingStrategy(top_k=actual_k)
 
 
 def _factory_brute_force(
```

### 6.4 `src/graph_insertion/strategies/__init__.py` (`git diff`)

```diff
diff --git i/src/graph_insertion/strategies/__init__.py w/src/graph_insertion/strategies/__init__.py
index 5cce12b..6bde015 100644
--- i/src/graph_insertion/strategies/__init__.py
+++ w/src/graph_insertion/strategies/__init__.py
@@ -13,6 +13,7 @@ __all__ = [
     "EmbeddingThresholdStrategy",
     "AnnRetrievalStrategy",
     "BoundedBucketStrategy",
+    "StubNarrowingStrategy",
     "STRATEGY_FACTORIES",
 ]
 
@@ -30,6 +31,9 @@ def __getattr__(name: str):  # noqa: ANN201 — lazy module-level exports
     if name == "BoundedBucketStrategy":
         from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
         return BoundedBucketStrategy
+    if name == "StubNarrowingStrategy":
+        from graph_insertion.strategies.stub import StubNarrowingStrategy
+        return StubNarrowingStrategy
     if name == "STRATEGY_FACTORIES":
         from graph_insertion.strategies.registry import STRATEGY_FACTORIES
         return STRATEGY_FACTORIES
```

### 6.5 `scripts/README.md` (`git diff`)

```diff
diff --git i/scripts/README.md w/scripts/README.md
index 40e8e84..e9d62ce 100644
--- i/scripts/README.md
+++ w/scripts/README.md
@@ -175,8 +175,9 @@ bash tests/test_apc_bundle.sh
 ### Deterministic Default Run Directories & Configuration Sidecar
 
 - When neither `--output-dir` nor `--run-id` is passed, the default output directory is `results/<mode>_<strategy>` (for `brute_force` at seed 42) or `results/<mode>_<strategy>_<slug>`, where `<slug>` encodes the strategy's keyed `config()` fields in fixed order (`_seed<seed>` is appended when `--seed != 42` for strategies with a seed). Explicit `--output-dir` or `--run-id` takes precedence unchanged.
-- Before the first trial on a fresh directory, the CLI writes `<output_dir>/strategy_config.json` containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`.
-- On `--resume` (or any run into an existing directory containing `raw.jsonl`), the CLI compares the stored `strategy` and `config` in `strategy_config.json` with the current configuration and refuses with exit code `1` on mismatch. Older directories containing `raw.jsonl` without `strategy_config.json` emit a warning to `stderr` and proceed without overwriting.
+- `--dry-run` (both offline and `--live --dry-run`) prints the plan and resolved output directory without creating the output directory or any file on disk.
+- On a real run (`--confirm`) into a fresh directory, `<output_dir>/strategy_config.json` (containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`) is written immediately after `manifest.json` and before the first trial begins, preserving clean `git_dirty` status in `manifest.json` while remaining crash-safe before trial execution.
+- On `--resume` (with an existing sidecar) or any run into an existing directory containing `raw.jsonl`, the CLI compares `strategy`, `config`, `mode`, and the `embedder` identity block (`type`, `model_name`, `dim`, `revision`, and installed `sentence_transformers_version` for `minilm`; `type`, `dim`, and `seed` for `fake`) in `strategy_config.json` with the current configuration and refuses with exit code `1` on mismatch. Older sidecars without `sentence_transformers_version` emit a single warning for that missing key and proceed; older directories containing `raw.jsonl` without `strategy_config.json` emit a warning to `stderr` and proceed without overwriting.
 
 ### Primary & Sensitivity Run Table (D-35, D-46, D-47, D-55, D-58, D-59, D-62)
 
```

### 6.6 `tests/test_strategy_registry.py` (`git diff`)

```diff
diff --git i/tests/test_strategy_registry.py w/tests/test_strategy_registry.py
index 4bad42c..c54ff0a 100644
--- i/tests/test_strategy_registry.py
+++ w/tests/test_strategy_registry.py
@@ -193,3 +193,41 @@ class TestStrategyRegistry:
         )
         assert derive_default_run_id("sweep", "null", {"k": 1, "seed": 42}) == "sweep_null_k1"
         assert derive_default_run_id("sweep", "stub", {"top_k": 5}) == "sweep_stub_k5"
+
+    def test_lazy_export_strategy_factories_kills_rm24(self) -> None:
+        """Kills R-M24: graph_insertion.strategies.STRATEGY_FACTORIES resolves via lazy export and matches registry."""
+        import graph_insertion.strategies as strats
+        from graph_insertion.strategies.registry import STRATEGY_FACTORIES as REG_FACTORIES
+
+        assert hasattr(strats, "STRATEGY_FACTORIES")
+        assert strats.STRATEGY_FACTORIES is REG_FACTORIES
+
+    def test_stub_isolated_import_and_no_scripts_dependency_kills_pm7(self) -> None:
+        """Kills P-M7: STRATEGY_FACTORIES['stub'] works from /tmp with PYTHONPATH=src only, and re-export from scripts.run_experiment still works."""
+        repo_root = Path(__file__).resolve().parent.parent
+        src_dir = repo_root / "src"
+        code = (
+            "import sys\n"
+            "from graph_insertion.strategies.registry import STRATEGY_FACTORIES\n"
+            "strat = STRATEGY_FACTORIES['stub'](42, None)\n"
+            "assert strat.name == 'stub_narrowing'\n"
+            "assert strat.config() == {'name': 'stub_narrowing', 'top_k': 5}\n"
+            "assert 'scripts' not in sys.modules\n"
+        )
+        proc = subprocess.run(
+            [sys.executable, "-c", code],
+            cwd="/tmp",
+            env={"PYTHONPATH": str(src_dir)},
+            capture_output=True,
+            text=True,
+            check=False,
+        )
+        assert proc.returncode == 0, f"stderr: {proc.stderr}"
+
+        # Also verify re-export from scripts.run_experiment works from repo root
+        from graph_insertion.strategies.stub import StubNarrowingStrategy as LibStub
+        from scripts.run_experiment import StubNarrowingStrategy as ScriptStub
+
+        assert ScriptStub is LibStub
+        assert ScriptStub(top_k=3).config() == {"name": "stub_narrowing", "top_k": 3}
+
```

### 6.7 `tests/test_embedding_minilm.py` (`git diff`)

```diff
diff --git i/tests/test_embedding_minilm.py w/tests/test_embedding_minilm.py
index 4fa7cbc..c6f5c30 100644
--- i/tests/test_embedding_minilm.py
+++ w/tests/test_embedding_minilm.py
@@ -1,5 +1,5 @@
-"""tests/test_embedding_minilm.py — INFRA-007
-==============================================
+"""tests/test_embedding_minilm.py — INFRA-007 / INFRA-007-P
+=========================================================
 Offline unit tests for ``graph_insertion.embedding_minilm.MiniLMEmbedder``.
 
 No network access, no model downloads, and no real ``sentence_transformers``
@@ -66,19 +66,21 @@ class _StubSentenceTransformer:
 
 
 @pytest.fixture
-def stub_st_module(monkeypatch: pytest.MonkeyPatch) -> type[_StubSentenceTransformer]:
-    """Inject stub ``sentence_transformers`` into ``sys.modules``."""
+def stub_st_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
+    """Inject stub ``sentence_transformers`` into ``sys.modules`` with configurable version."""
     _StubSentenceTransformer.instances.clear()
     mod = types.ModuleType("sentence_transformers")
     mod.SentenceTransformer = _StubSentenceTransformer  # type: ignore[attr-defined]
+    mod.__version__ = "3.1.1"  # type: ignore[attr-defined]
     monkeypatch.setitem(sys.modules, "sentence_transformers", mod)
-    return _StubSentenceTransformer
+    return mod
 
 
 class TestMiniLMEmbedderOffline:
     """Offline tests for MiniLMEmbedder using injected stub module."""
 
     def test_module_imports_lazily_without_sentence_transformers(self) -> None:
+        """Module loads cleanly without sentence_transformers present."""
         repo_root = Path(__file__).resolve().parent.parent
         src_dir = repo_root / "src"
         code = (
@@ -101,44 +103,87 @@ class TestMiniLMEmbedderOffline:
     def test_refuses_when_pin_is_none_or_empty(
         self,
         monkeypatch: pytest.MonkeyPatch,
-        stub_st_module: type[_StubSentenceTransformer],
+        stub_st_module: types.ModuleType,
     ) -> None:
-        # 1. Default when MODEL_REVISION_PIN is None -> raises ValueError
+        """Both version and revision pins fail-closed if None, blank, or empty."""
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
         monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", None)
         with pytest.raises(ValueError, match="pinned model revision"):
             MiniLMEmbedder()
-        assert len(stub_st_module.instances) == 0
+        assert len(_StubSentenceTransformer.instances) == 0
 
-        # 2. Explicit revision=None refused even when MODEL_REVISION_PIN is set (kills I-M13)
+        # Version pin None refused
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", None)
         monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "abc123456789")
+        with pytest.raises(ValueError, match="pinned sentence-transformers package version"):
+            MiniLMEmbedder()
+        assert len(_StubSentenceTransformer.instances) == 0
+
+        # Version pin empty string refused
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "   ")
+        with pytest.raises(ValueError, match="pinned sentence-transformers package version"):
+            MiniLMEmbedder()
+        assert len(_StubSentenceTransformer.instances) == 0
+
+        # Explicit revision=None refused even when pins are set (kills I-M13)
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
         with pytest.raises(ValueError, match="pinned model revision"):
             MiniLMEmbedder(revision=None)
-        assert len(stub_st_module.instances) == 0
+        assert len(_StubSentenceTransformer.instances) == 0
 
-        # 3. Empty/whitespace revision string refused
+        # Empty/whitespace revision string refused
         with pytest.raises(ValueError, match="pinned model revision"):
             MiniLMEmbedder(revision="   ")
-        assert len(stub_st_module.instances) == 0
+        assert len(_StubSentenceTransformer.instances) == 0
+
+    def test_version_mismatch_refused_and_match_passes(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: types.ModuleType,
+    ) -> None:
+        """Version check validates installed library against pin."""
+        stub_st_module.__version__ = "3.1.1"  # type: ignore[attr-defined]
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev42")
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.2.0")
+
+        with pytest.raises(ValueError, match="sentence-transformers version mismatch: installed='3.1.1' vs pinned='3.2.0'"):
+            MiniLMEmbedder()
+        assert len(_StubSentenceTransformer.instances) == 0
+
+        # Passing an explicit revision= still never bypasses the version check
+        with pytest.raises(ValueError, match="sentence-transformers version mismatch: installed='3.1.1' vs pinned='3.2.0'"):
+            MiniLMEmbedder(revision="custom-rev-override")
+        assert len(_StubSentenceTransformer.instances) == 0
+
+        # Matching version succeeds
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        emb = MiniLMEmbedder()
+        assert emb.installed_version == "3.1.1"
+        assert len(_StubSentenceTransformer.instances) == 1
 
     def test_missing_sentence_transformers_raises_import_error_with_install_hint(
         self, monkeypatch: pytest.MonkeyPatch
     ) -> None:
+        """Missing library import error gives clear pip install instruction."""
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "test-rev-001")
         monkeypatch.setitem(sys.modules, "sentence_transformers", None)
         with pytest.raises(ImportError, match=r'pip install -e "\.\[embed\]"'):
-            MiniLMEmbedder(revision="test-rev-001")
+            MiniLMEmbedder()
 
     def test_embed_and_embed_many_shapes_dtypes_and_call_counts(
         self,
         monkeypatch: pytest.MonkeyPatch,
-        stub_st_module: type[_StubSentenceTransformer],
+        stub_st_module: types.ModuleType,
     ) -> None:
+        """Validates shapes, dtypes, and call delegation."""
         monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev-sha-42")
-        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.0.0-test")
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
 
         emb = MiniLMEmbedder()
         assert isinstance(emb, Embedder)
-        assert len(stub_st_module.instances) == 1
-        underlying = stub_st_module.instances[0]
+        assert len(_StubSentenceTransformer.instances) == 1
+        underlying = _StubSentenceTransformer.instances[0]
         assert underlying.model_name_or_path == MODEL_NAME
         assert underlying.revision == "rev-sha-42"
         assert underlying.device == "cpu"
@@ -183,17 +228,81 @@ class TestMiniLMEmbedderOffline:
     def test_identity_metadata_content_and_json_serializable(
         self,
         monkeypatch: pytest.MonkeyPatch,
-        stub_st_module: type[_StubSentenceTransformer],
+        stub_st_module: types.ModuleType,
     ) -> None:
+        """Identity records installed library version (not pin constant) and revision (kills P-M8)."""
+        stub_st_module.__version__ = "3.1.1"  # type: ignore[attr-defined]
         monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "default-pin-rev")
         emb = MiniLMEmbedder(revision="commit-hash-xyz")
         ident = emb.identity()
         assert ident == {
             "model_name": "all-MiniLM-L6-v2",
             "dim": 384,
             "revision": "commit-hash-xyz",
+            "sentence_transformers_version": "3.1.1",
             "sentence_transformers_version_pin": "3.1.1",
             "device": "cpu",
             "dtype": "float32",
         }
         assert json.loads(json.dumps(ident)) == ident
+
+        # Prove sentence_transformers_version comes from installed version, not SENTENCE_TRANSFORMERS_VERSION_PIN (kills P-M8)
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "9.9.9-changed-pin")
+        ident_after = emb.identity()
+        assert ident_after["sentence_transformers_version"] == "3.1.1"
+        assert ident_after["sentence_transformers_version_pin"] == "9.9.9-changed-pin"
+
+
+    def test_embed_many_single_item_reshape_kills_rm16(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: types.ModuleType,
+    ) -> None:
+        """Kills R-M16: single-text embed_many preserves 2-D shape (1, 384) even if encoder returns (384,)."""
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev42")
+        emb = MiniLMEmbedder()
+        underlying = _StubSentenceTransformer.instances[0]
+        # Monkeypatch encode to return a 1-D vector of shape (384,) for a single item list
+        underlying.encode = lambda texts, **kw: np.ones(384, dtype=np.float32)  # type: ignore[assignment]
+        res = emb.embed_many(["single item"])
+        assert res.shape == (1, 384)
+        assert res.dtype == np.float32
+
+    def test_embed_many_float64_casted_to_float32_kills_rm20(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: types.ModuleType,
+    ) -> None:
+        """Kills R-M20: float64 encoder output is explicitly cast to float32."""
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev42")
+        emb = MiniLMEmbedder()
+        underlying = _StubSentenceTransformer.instances[0]
+        # Monkeypatch encode to return float64
+        underlying.encode = lambda texts, **kw: np.ones((len(texts), 384), dtype=np.float64)  # type: ignore[assignment]
+        res = emb.embed_many(["text a", "text b"])
+        assert res.dtype == np.float32
+        assert res.shape == (2, 384)
+
+    def test_wrong_dimension_encoder_output_raises_value_error_kills_rm25(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: types.ModuleType,
+    ) -> None:
+        """Kills R-M25: wrong-dimension encoder output raises ValueError in embed and embed_many."""
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev42")
+        emb = MiniLMEmbedder()
+        underlying = _StubSentenceTransformer.instances[0]
+
+        # embed with wrong dim
+        underlying.encode = lambda text, **kw: np.ones(128, dtype=np.float32)  # type: ignore[assignment]
+        with pytest.raises(ValueError, match=r"Expected 1-D embedding of shape \(384,\)"):
+            emb.embed("test text")
+
+        # embed_many with wrong dim
+        underlying.encode = lambda texts, **kw: np.ones((len(texts), 128), dtype=np.float32)  # type: ignore[assignment]
+        with pytest.raises(ValueError, match=r"Expected 2-D embedding matrix of shape \(1, 384\)"):
+            emb.embed_many(["test text"])
```

### 6.8 `tests/test_run_experiment_cli.py` (`git diff`)

```diff
diff --git i/tests/test_run_experiment_cli.py w/tests/test_run_experiment_cli.py
index 5690c73..85bf87f 100644
--- i/tests/test_run_experiment_cli.py
+++ w/tests/test_run_experiment_cli.py
@@ -267,15 +267,12 @@ class TestRunDirectoryKeysAndSidecarGuard:
         slug_part = expected_sweep_dir.removeprefix("results/")
         assert re.fullmatch(r"[a-z0-9._-]+", slug_part) is not None
 
-        # Verify sidecar and manifest written to expected default directory inside tmp_path
+        # Dry run must not create output directory or sidecar file on disk (INFRA-007-P Step D)
         run_dir = tmp_path / expected_sweep_dir
-        sidecar_file = run_dir / "strategy_config.json"
-        assert sidecar_file.exists()
-        sidecar = json.loads(sidecar_file.read_text(encoding="utf-8"))
-        for k, v in expected_keyed_cfg.items():
-            assert sidecar["config"][k] == v
+        assert not run_dir.exists(), f"dry-run should not create {run_dir}"
+        assert list(tmp_path.iterdir()) == []
 
-        # Also check accuracy mode slug derivation
+        # Also check accuracy mode slug derivation and keyed strategy config
         parser = build_parser()
         args = parser.parse_args(["--mode", "accuracy", *cli_tokens])
         strat = STRATEGY_FACTORIES[args.strategy](
@@ -287,7 +284,10 @@ class TestRunDirectoryKeysAndSidecarGuard:
             s_max=args.s_max,
             n_bits=args.n_bits,
         )
-        acc_dir = f"results/{derive_default_run_id('accuracy', args.strategy, strat.config())}"
+        cfg = strat.config()
+        for k, v in expected_keyed_cfg.items():
+            assert cfg[k] == v
+        acc_dir = f"results/{derive_default_run_id('accuracy', args.strategy, cfg)}"
         assert acc_dir == expected_sweep_dir.replace("results/sweep_", "results/accuracy_", 1)
 
     @pytest.mark.parametrize(
@@ -332,6 +332,26 @@ class TestRunDirectoryKeysAndSidecarGuard:
         assert rc == 0
         out = capsys.readouterr().out
         assert f"Default/resolved output directory: {expected_dir}" in out
+        # Dry run must not create directory or sidecar (INFRA-007-P Step D)
+        assert not (tmp_path / expected_dir).exists()
+
+        # Real tiny run writes strategy_config.json with seed 99
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                *cli_tokens,
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
         sidecar = json.loads((tmp_path / expected_dir / "strategy_config.json").read_text())
         assert sidecar["config"]["seed"] == 99
 
@@ -343,7 +363,7 @@ class TestRunDirectoryKeysAndSidecarGuard:
     ) -> None:
         monkeypatch.chdir(tmp_path)
 
-        # 1. Explicit --run-id wins over default slug
+        # 1. Explicit --run-id wins over default slug; dry-run writes nothing to disk
         monkeypatch.setattr(
             "sys.argv",
             [
@@ -360,9 +380,9 @@ class TestRunDirectoryKeysAndSidecarGuard:
         assert main() == 0
         out1 = capsys.readouterr().out
         assert "Default/resolved output directory: results/custom_run_123" in out1
-        assert (tmp_path / "results" / "custom_run_123" / "manifest.json").exists()
+        assert not (tmp_path / "results" / "custom_run_123").exists()
 
-        # 2. Explicit --output-dir wins over both default slug and --run-id
+        # 2. Explicit --output-dir wins over both default slug and --run-id; dry-run writes nothing to disk
         explicit_dir = tmp_path / "my_explicit_dir"
         monkeypatch.setattr(
             "sys.argv",
@@ -382,7 +402,7 @@ class TestRunDirectoryKeysAndSidecarGuard:
         assert main() == 0
         out2 = capsys.readouterr().out
         assert f"Default/resolved output directory: {explicit_dir}" in out2
-        assert (explicit_dir / "manifest.json").exists()
+        assert not explicit_dir.exists()
 
     def test_sidecar_written_and_resume_mismatch_refused(
         self,
@@ -812,3 +832,481 @@ class TestEndToEndOfflineCLISmoke:
         assert all(r["strategy"] == strategy and r["status"] == "success" for r in acc_records)
         acc_sidecar = json.loads((acc_dir / "strategy_config.json").read_text(encoding="utf-8"))
         assert acc_sidecar["strategy"] == strategy
+
+
+class _CLIStubSentenceTransformer:
+    """Deterministic offline stub for sentence_transformers.SentenceTransformer in CLI tests."""
+
+    instances: list["_CLIStubSentenceTransformer"] = []
+
+    def __init__(
+        self,
+        model_name_or_path: str,
+        *,
+        revision: str | None = None,
+        device: str | None = None,
+        **kwargs: Any,
+    ) -> None:
+        self.model_name_or_path = model_name_or_path
+        self.revision = revision
+        self.device = device
+        self.kwargs = kwargs
+        self.encode_calls: int = 0
+        _CLIStubSentenceTransformer.instances.append(self)
+
+    def encode(self, sentences: Any, **kwargs: Any) -> Any:
+        import hashlib
+        import numpy as np
+
+        self.encode_calls += 1
+        if isinstance(sentences, str):
+            digest = hashlib.sha256(sentences.encode("utf-8")).digest()
+            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
+            vec = rng.standard_normal(384).astype(np.float32)
+            return vec / (np.linalg.norm(vec) + 1e-12)
+        rows = []
+        for s in sentences:
+            digest = hashlib.sha256(str(s).encode("utf-8")).digest()
+            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
+            vec = rng.standard_normal(384).astype(np.float32)
+            rows.append(vec / (np.linalg.norm(vec) + 1e-12))
+        return np.vstack(rows).astype(np.float32)
+
+
+def _install_stub_st(
+    monkeypatch: pytest.MonkeyPatch,
+    version: str = "3.1.1",
+    revision_pin: str = "a" * 40,
+    version_pin: str = "3.1.1",
+) -> tuple[type[_CLIStubSentenceTransformer], Any]:
+    import types
+    import graph_insertion.embedding_minilm as minilm_mod
+
+    _CLIStubSentenceTransformer.instances.clear()
+    mod = types.ModuleType("sentence_transformers")
+    mod.SentenceTransformer = _CLIStubSentenceTransformer  # type: ignore[attr-defined]
+    mod.__version__ = version  # type: ignore[attr-defined]
+    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)
+    monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", version_pin)
+    monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", revision_pin)
+    return _CLIStubSentenceTransformer, mod
+
+
+class TestINFRA007PAmendments:
+    """INFRA-007-P tests for resume-guard embedder/mode checks, minilm execution & timing, and dry-run/git_dirty."""
+
+    def test_resume_guard_embedder_identity_and_mode_and_non_resume_existing_raw(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        """Kills R-M11, P-M3, P-M4: guard checks embedder block, mode, and non-resume runs with existing raw.jsonl."""
+        stub_cls, st_mod = _install_stub_st(
+            monkeypatch,
+            version="3.1.1",
+            revision_pin="1" * 40,
+            version_pin="3.1.1",
+        )
+
+        # 1. Start a 'fake' embedder run
+        fake_dir = tmp_path / "run_fake_et"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "fake",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(fake_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        # 1a. Resuming a 'fake' run with '--embedder minilm' is refused (exit 1, shows both blocks; kills P-M3)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "minilm",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(fake_dir),
+            ],
+        )
+        assert main() == 1
+        err_type = capsys.readouterr().err
+        assert "embedder" in err_type.lower() and "mismatch" in err_type.lower()
+        assert "'type': 'fake'" in err_type
+        assert "'type': 'minilm'" in err_type
+
+        # 1b. Non---resume run into a directory with raw.jsonl and mismatching sidecar is refused (kills R-M11)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--theta",
+                "0.4",
+                "--embedder",
+                "fake",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(fake_dir),
+            ],
+        )
+        assert main() == 1
+        err_no_resume = capsys.readouterr().err
+        assert "mismatch" in err_no_resume.lower()
+
+        # 1c. Mode change (sweep vs accuracy in the same directory) is refused (kills P-M4)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "accuracy",
+                "--corpus",
+                "DSA",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "fake",
+                "--max-llm-calls",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(fake_dir),
+            ],
+        )
+        assert main() == 1
+        err_mode = capsys.readouterr().err
+        assert "mode mismatch" in err_mode.lower()
+        assert "'sweep'" in err_mode and "'accuracy'" in err_mode
+
+        # 2. Start a 'minilm' embedder run
+        minilm_dir = tmp_path / "run_minilm_et"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "minilm",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(minilm_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        # 2a. Matching resume with minilm passes
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "minilm",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(minilm_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        # 2b. minilm revision change refused
+        import graph_insertion.embedding_minilm as minilm_mod
+
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "2" * 40)
+        assert main() == 1
+        err_rev = capsys.readouterr().err
+        assert "embedder configuration mismatch" in err_rev.lower()
+        assert "1" * 40 in err_rev and "2" * 40 in err_rev
+
+        # Restore revision, change installed sentence_transformers version -> refused
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "1" * 40)
+        st_mod.__version__ = "3.2.0"
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.2.0")
+        assert main() == 1
+        err_ver = capsys.readouterr().err
+        assert "sentence_transformers_version" in err_ver
+        assert "3.1.1" in err_ver and "3.2.0" in err_ver
+
+        # 2c. Legacy pre-INFRA-007-P sidecar without sentence_transformers_version key warns once and succeeds
+        st_mod.__version__ = "3.1.1"
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        sidecar_path = minilm_dir / "strategy_config.json"
+        sc_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
+        del sc_data["embedder"]["sentence_transformers_version"]
+        sidecar_path.write_text(json.dumps(sc_data, indent=2), encoding="utf-8")
+
+        assert main() == 0
+        err_legacy = capsys.readouterr().err
+        assert "WARNING:" in err_legacy
+        assert "sentence_transformers_version" in err_legacy
+
+    def test_minilm_offline_execution_and_construction_timing_kills_rm19_and_pm5(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        """Kills R-M19 and P-M5: offline --embedder minilm runs end-to-end; never constructed without --confirm or on --dry-run."""
+        stub_rev = "abcdef0123456789abcdef0123456789abcdef01"
+        stub_cls, _ = _install_stub_st(
+            monkeypatch,
+            version="3.1.1",
+            revision_pin=stub_rev,
+            version_pin="3.1.1",
+        )
+
+        # 1. Without --confirm and without --dry-run: MiniLMEmbedder constructor is NEVER called (kills P-M5)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "minilm",
+                "--sweep-sizes",
+                "12",
+                "--sweep-trials",
+                "1",
+                "--output-dir",
+                str(tmp_path / "no_confirm_dir"),
+            ],
+        )
+        assert main() == 1
+        err_nc = capsys.readouterr().err
+        assert "--confirm" in err_nc
+        assert len(stub_cls.instances) == 0
+
+        # 2. With --dry-run: MiniLMEmbedder constructor is NEVER called
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--embedder",
+                "minilm",
+                "--sweep-sizes",
+                "12",
+                "--sweep-trials",
+                "1",
+                "--dry-run",
+                "--output-dir",
+                str(tmp_path / "dry_run_dir"),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+        assert len(stub_cls.instances) == 0
+
+        # 3. End-to-end offline --embedder minilm --confirm for embedding_threshold and bounded_bucket (sizes (12, 30), 2 trials) (kills R-M19)
+        for strat_name in ("embedding_threshold", "bounded_bucket"):
+            stub_cls.instances.clear()
+            out_dir = tmp_path / f"minilm_e2e_{strat_name}"
+            monkeypatch.setattr(
+                "sys.argv",
+                [
+                    "run_experiment.py",
+                    "--mode",
+                    "sweep",
+                    "--strategy",
+                    strat_name,
+                    "--embedder",
+                    "minilm",
+                    "--sweep-sizes",
+                    "12",
+                    "30",
+                    "--sweep-trials",
+                    "2",
+                    "--confirm",
+                    "--output-dir",
+                    str(out_dir),
+                ],
+            )
+            assert main() == 0, f"Failed for {strat_name}: {capsys.readouterr().err}"
+            capsys.readouterr()
+
+            assert len(stub_cls.instances) == 1
+            assert stub_cls.instances[0].revision == stub_rev
+            assert stub_cls.instances[0].encode_calls == 8
+
+            sidecar = json.loads((out_dir / "strategy_config.json").read_text(encoding="utf-8"))
+            assert sidecar["embedder"]["type"] == "minilm"
+            assert sidecar["embedder"]["revision"] == stub_rev
+            assert sidecar["embedder"]["sentence_transformers_version"] == "3.1.1"
+            assert sidecar["embedder"]["dim"] == 384
+
+            records = [
+                json.loads(line)
+                for line in (out_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
+                if line.strip()
+            ]
+            assert len(records) == 4
+            assert all(r["status"] == "success" and r["strategy"] == strat_name for r in records)
+            assert all(r["metrics"]["embedding_calls"] == 1 for r in records)
+
+    def test_dry_run_creates_nothing_and_real_run_sidecar_before_trial1_and_git_dirty_false_kills_rm26_and_pm6(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        """Kills R-M26 and P-M6: dry-run creates nothing on disk; real run records git_dirty==False and writes sidecar before trial 1."""
+        import subprocess
+        import graph_insertion.harness as harness_mod
+
+        # 1. Offline --dry-run creates nothing in tmp_path (kills P-M6)
+        empty_check_dir = tmp_path / "dry_run_workspace"
+        empty_check_dir.mkdir()
+        monkeypatch.chdir(empty_check_dir)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--dry-run",
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+        assert list(empty_check_dir.iterdir()) == []
+
+        # 2. Clean git repo under tmp_path: real offline --confirm run records git_dirty == False in manifest.json
+        clean_repo = tmp_path / "clean_git_repo"
+        clean_repo.mkdir()
+        subprocess.run(["git", "init"], cwd=clean_repo, check=True, capture_output=True)
+        subprocess.run(["git", "config", "user.name", "test"], cwd=clean_repo, check=True)
+        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clean_repo, check=True)
+        (clean_repo / "README.md").write_text("clean repo\n", encoding="utf-8")
+        subprocess.run(["git", "add", "README.md"], cwd=clean_repo, check=True)
+        subprocess.run(["git", "commit", "-m", "initial"], cwd=clean_repo, check=True, capture_output=True)
+
+        monkeypatch.chdir(clean_repo)
+        monkeypatch.setattr(harness_mod, "REPO_ROOT", clean_repo)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "null",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        default_out = clean_repo / "results" / "sweep_null_k1"
+        manifest = json.loads((default_out / "manifest.json").read_text(encoding="utf-8"))
+        assert manifest["git_dirty"] is False
+        assert (default_out / "strategy_config.json").exists()
+
+        # 3. Ordering & crash-safety check: sidecar exists BEFORE the first trial starts (kills R-M26)
+        crash_dir = tmp_path / "crash_trial1_dir"
+        sidecar_existed_at_trial_1: list[bool] = []
+
+        import scripts.run_experiment as run_exp_mod
+
+        class _CrashOnTrial1DecisionStep:
+            PROMPT_VERSION = "v2"
+
+            def decide(
+                self,
+                new_name: str,
+                candidates: tuple[str, ...],
+                domain_context: str | None = None,
+            ) -> Any:
+                sidecar_existed_at_trial_1.append((crash_dir / "strategy_config.json").exists())
+                raise RuntimeError("simulated crash during trial 1")
+
+        monkeypatch.setattr(
+            run_exp_mod,
+            "PairwiseDecisionStep",
+            lambda client: _CrashOnTrial1DecisionStep(),
+        )
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "null",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--fail-fast",
+                "--output-dir",
+                str(crash_dir),
+            ],
+        )
+        assert main() == 1
+        capsys.readouterr()
+        assert sidecar_existed_at_trial_1 == [True]
+        assert (crash_dir / "strategy_config.json").exists()
+
```

### 6.9 `docs/decisions/decision-log.md` (`git diff`)

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index aec05b8..fdaf5d8 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -527,4 +527,10 @@ Reasoning: completes the CLI wiring for all four candidate-narrowing strategies
 (8) FIX-017 ([D-63]) is accepted with limits: the APC read the generator hunk, the added and repaired tests and the mutation section headings of the report, and did not re-run the mutations or the suite. The pool meta was written before FIX-017 and lacks the per-shard `profiles` list; no rebuild is needed because there was no failover, and rebuilding would add risk for no benefit. The skip counts differ because `faiss-cpu` is not installed in the main checkout: `pytest -rs` there lists 5 faiss import skips plus 3 "non-embedding strategy by design" skips [Confirmed: pasted output]; the 583 passed, 3 skipped in the FIX-017 report is [agent-reported]. Pass counts across checkouts are not reconciled ([Unverified]).
 Reasoning: records what was run, what the adapter did differently from the smoke tests, and what the pool does and does not support, so Chapter 3 can describe the generator accurately and a reader can reproduce the run from the caches. Affects: DATA-004, FIX-017, `data/synthetic/cs_concept_names.json`, DOC-002, `docs/guide/Name-pool generation runbook.md`.
 
-
+**[D-66]** INFRA-007 post-review amendments: fail-closed version/revision pin and runtime package checks, embedder identity and mode in the resume guard, deferred embedder construction, zero dry-run disk writes and clean `git_dirty` sidecar timing, standalone `stub.py`, and test/mutation gap closures (INFRA-007-P):
+(1) Pins and runtime check (`src/graph_insertion/embedding_minilm.py`, `pyproject.toml`): `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` were not yet supplied and remain `None` (`pyproject.toml` `embed` extra left unchanged). `MiniLMEmbedder.__init__` now fails closed with `ValueError` (naming the missing pin) if either `SENTENCE_TRANSFORMERS_VERSION_PIN` or the resolved model revision (`MODEL_REVISION_PIN` unless overridden by `revision=`) is `None` or blank/whitespace. After lazily importing `sentence_transformers`, `__init__` compares `sentence_transformers.__version__` against `SENTENCE_TRANSFORMERS_VERSION_PIN` and raises `ValueError` showing both values on any mismatch; passing `revision=` overrides only the revision constant, never the package version check. `MiniLMEmbedder.identity()` records the installed package version (`"sentence_transformers_version": self.installed_version`) alongside `"sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN`, `"model_name"`, `"dim"`, `"revision"`, `"device"`, and `"dtype"`.
+(2) Embedder identity and `mode` in the resume/existing-directory guard (`scripts/run_experiment.py`): `check_resume_or_existing_directory_guard()` runs whenever `<output_dir>/raw.jsonl` exists (whether or not `--resume` is passed) or `--resume` is given with an existing `<output_dir>/strategy_config.json`. In addition to comparing `strategy` and `config()`, it compares `mode` (`"sweep"` vs `"accuracy"`) and the `embedder` block: `"type"`, `"model_name"`, `"dim"`, `"revision"`, and `"sentence_transformers_version"` (installed) for `minilm`, and `"type"`, `"dim"`, and `"seed"` for `fake`. Any mismatch refuses with exit code 1 and prints both stored and current values to `stderr`. A directory containing `raw.jsonl` without `strategy_config.json` preserves the legacy/pilot warning behaviour without refusing or writing a sidecar. A pre-INFRA-007-P sidecar lacking `"sentence_transformers_version"` is not refused for that missing key alone: the guard treats a missing `"sentence_transformers_version"` key as unrecorded, emits a single `WARNING:` to `stderr`, and still enforces all other keys.
+(3) Deferred `MiniLMEmbedder` construction, zero disk writes on `--dry-run`, and `git_dirty` preservation on real runs (`scripts/run_experiment.py`): (a) `MiniLMEmbedder()` is constructed only when trials will actually execute — never under `--dry-run` (with or without `--live`) and never when an offline run omits `--confirm` (which now exits 1 with the harness confirmation message before any embedder construction). (b) Offline `--dry-run` invokes `estimate_and_print_plan()` directly and returns 0 before `run_experiment()`, creating neither `<output_dir>`, `manifest.json`, nor `strategy_config.json` on disk (matching `--live --dry-run`). (c) For real runs (`--confirm`) on a fresh directory (`not has_existing_raw`), `<output_dir>/strategy_config.json` is written via `warmup_fn` passed to `run_experiment()` rather than before `run_experiment()`. Because `harness.py:write_manifest()` creates the empty `<output_dir>` (`git status --porcelain` ignores empty directories) and immediately captures `get_git_info()` before invoking `warmup_fn` (which runs before `_load_existing_keys()`, `raw.jsonl` opening, and trial 1), `manifest.json` records `"git_dirty": false` on a clean checkout just as before INFRA-007 while `strategy_config.json` is still on disk before the first trial starts, without modifying `harness.py`.
+(4) Standalone `StubNarrowingStrategy` module (`src/graph_insertion/strategies/stub.py`, `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/run_experiment.py`): moved `StubNarrowingStrategy` out of `scripts/run_experiment.py` into `src/graph_insertion/strategies/stub.py` (preserving class name, `.name == "stub_narrowing"`, and `.config()` keys), re-exported it in `scripts/run_experiment.py` and lazily in `src/graph_insertion/strategies/__init__.py`, and replaced `register_stub`/`_get_stub_cls` in `registry.py` with a direct import from `graph_insertion.strategies.stub` so library callers can instantiate `STRATEGY_FACTORIES["stub"]` when `scripts/` is not on `sys.path`.
+(5) Test and mutation gaps closed (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`): added unit and CLI integration tests closing all seven surviving mutants from the INFRA-007-R review (`R-M11` non-`--resume` mismatch guard when `raw.jsonl` exists; `R-M16` 1-row reshape in `embed_many` when encoder returns 1-D `(384,)`; `R-M19` offline end-to-end `--embedder minilm --confirm` execution for `embedding_threshold` and `bounded_bucket`; `R-M20` explicit `float32` cast from `float64` in `embed_many`; `R-M24` lazy `graph_insertion.strategies.STRATEGY_FACTORIES` export identity; `R-M25` wrong-dimension `ValueError` in `embed()` and `embed_many()`; `R-M26` sidecar existence before trial 1 and `git_dirty == False` in a clean git repo) plus all eight INFRA-007-P mutants (`P-M1`..`P-M8`).
+Reasoning: resolves all four should-fix items and three nits from the independent INFRA-007-R review (`docs/reports/INFRA-007-R-gemini.md`) so resume guards, embedder pins, dry-run hygiene, library packaging, and mutation coverage are airtight before live runs. Affects: `scripts/run_experiment.py`, `src/graph_insertion/embedding_minilm.py`, `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/stub.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/README.md`, `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/INFRA-007-P-gemini.md`, INFRA-007.
```

### 6.10 `docs/tasks/status.md` (`git diff`)

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 2e18c2a..bfb65ca 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -57,7 +57,7 @@ Status: **in-progress** (unblocked following Phase 2 completion)
 
 | ID        | Task                                                                                                                                                                                                 | Status           | Notes / Report                                                                                                                                                                                                                                                                                                                                           |
 | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
-| INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **needs-review** | Completed by Gemini. 86 new tests (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`), 13/13 mutants `I-M1`..`I-M13` killed; full test suite 674 passing, 3 skipped. Awaiting `sentence-transformers` version and `all-MiniLM-L6-v2` revision pins from Luke. See report [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md). |
+| INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **needs-review** | Implemented by Gemini ([D-64], report [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md)); independently reviewed under INFRA-007-R (report [`docs/reports/INFRA-007-R-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-R-gemini.md), ACCEPT WITH AMENDMENTS); amendments applied under INFRA-007-P ([D-66], report [`docs/reports/INFRA-007-P-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-P-gemini.md), 15/15 mutants killed). Pending: Luke supplying `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py` and `pyproject.toml`, one-time model download, and the OpenMP timing check. |
 
 ## Phase 4 — Analysis & Writeup
 
```

### 6.11 `src/graph_insertion/strategies/stub.py` (`diff -u /dev/null`)

```diff
--- /dev/null	2026-10-12 16:40:48.057798533 +0800
+++ src/graph_insertion/strategies/stub.py	2026-10-12 17:22:21.325668962 +0800
@@ -0,0 +1,47 @@
+"""strategies/stub.py — StubNarrowingStrategy implementation.
+
+Provides a minimal deterministic candidate-narrowing strategy for harness testing
+and dry runs without external dependencies.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from graph_insertion.graph_representation import ConceptGraph
+from graph_insertion.strategy import Embedder, NarrowingStrategy, Shortlist
+
+
+class StubNarrowingStrategy:
+    """Minimal deterministic narrowing strategy for harness testing and dry runs."""
+
+    name: str = "stub_narrowing"
+    uses_embeddings: bool = False
+
+    def __init__(self, top_k: int = 5) -> None:
+        self.top_k = top_k
+        self._graph: Optional[ConceptGraph] = None
+        self._embedder: Optional[Embedder] = None
+
+    def setup(self, graph: ConceptGraph, embedder: Any) -> None:
+        self._graph = graph
+        self._embedder = None
+
+    def shortlist(self, new_name: str) -> Shortlist:
+        if not self._graph:
+            return Shortlist(candidates=())
+        nodes = sorted(self._graph.nodes())
+        candidates = tuple(nodes[: self.top_k])
+        return Shortlist(candidates=candidates)
+
+    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
+        pass
+
+    def config(self) -> dict[str, Any]:
+        return {"name": self.name, "top_k": self.top_k}
+
+    def diagnostics(self) -> dict[str, Any]:
+        return {}
+
+    def max_candidates(self, n_existing: int) -> int:
+        return min(self.top_k, n_existing)
```

---

## 7. Found But Not Changed

In accordance with Section 2 and Rule 1, none of the following pre-existing items noticed during this session were modified:

1. **Unstaged modification in `docs/context/repo-tree.txt`:** `git status --short` shows ` M docs/context/repo-tree.txt` (updated outside this task when `DOC-002` was merged); left untouched and unstaged.
2. **Existing task worktrees:** `git worktree list` shows `../llm-graph-insertion-complexity-FIX-017` and `../llm-graph-insertion-complexity-gen`; neither was touched.
3. **Misleading offline missing-`--confirm` error wording in `src/graph_insertion/harness.py:703`:** When running in offline mode without `--dry-run` or `--confirm`, `HarnessConfig.__post_init__` raises `ValueError("Live experiment runs require explicit confirmation via config.confirm=True (or CLI flag --confirm)...")` even though the run is offline. To preserve exact message parity without editing `harness.py`, `scripts/run_experiment.py:1048-1054` prints the identical message before `MiniLMEmbedder` construction.
4. **`.gitignore` coverage of `results/`:** `.gitignore` ignores `results/datagen/` but not `results/`. While `warmup_fn` sidecar ordering now ensures `manifest.json` records `"git_dirty": false` on the initial run in a clean checkout, any subsequent run starts with untracked files in `results/` unless cleaned, moved, or committed.

---

## 8. Timing Snippet and Install & Download Commands for Luke

### 8.1 One-Time Install and Model Download Commands (Run in `.venv-ann`)

```bash
# 1. Install sentence-transformers via the [embed] extra and inspect the installed version:
.venv-ann/bin/pip install -e ".[embed]"
.venv-ann/bin/pip show sentence-transformers

# 2. Download all-MiniLM-L6-v2 once to the local Hugging Face cache and print its 40-hex snapshot revision:
.venv-ann/bin/python -c '
from pathlib import Path
from sentence_transformers import SentenceTransformer
import sentence_transformers

model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
snaps = sorted(
    Path.home().glob(
        ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*"
    )
)
print("SENTENCE_TRANSFORMERS_VERSION =", sentence_transformers.__version__)
print("MODEL_REVISION                =", snaps[-1].name if snaps else "NOT_FOUND")
'
```

After setting `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py` and pinning `embed = ["sentence-transformers==<VERSION>"]` in `pyproject.toml`, run the OpenMP timing check below.

### 8.2 Corrected OpenMP / PyTorch Thread-Count & Latency Snippet (`MiniLMEmbedder()` with No Arguments)

```bash
.venv-ann/bin/python -c '
import time
import torch
import faiss
from graph_insertion.embedding_minilm import MiniLMEmbedder

emb = MiniLMEmbedder()
print("Identity:", emb.identity())

names_200 = [f"concept_node_{i:04d}" for i in range(200)]
names_50 = [f"single_query_{i:04d}" for i in range(50)]

# Warmup call
_ = emb.embed("warmup_concept")

print("Before faiss.omp_set_num_threads(1): torch.get_num_threads() =", torch.get_num_threads())
t0 = time.perf_counter()
_ = emb.embed_many(names_200)
t_batch_before = time.perf_counter() - t0

t0 = time.perf_counter()
for name in names_50:
    _ = emb.embed(name)
t_single_before = time.perf_counter() - t0
print(f"Before: embed_many(200) = {t_batch_before*1000:.2f} ms | 50x embed(1) = {t_single_before*1000:.2f} ms ({t_single_before*20:.2f} ms/call)")

faiss.omp_set_num_threads(1)
print("After  faiss.omp_set_num_threads(1): torch.get_num_threads() =", torch.get_num_threads())

t0 = time.perf_counter()
_ = emb.embed_many(names_200)
t_batch_after = time.perf_counter() - t0

t0 = time.perf_counter()
for name in names_50:
    _ = emb.embed(name)
t_single_after = time.perf_counter() - t0
print(f"After : embed_many(200) = {t_batch_after*1000:.2f} ms | 50x embed(1) = {t_single_after*1000:.2f} ms ({t_single_after*20:.2f} ms/call)")
'
```

---

## 9. Open Questions

1. **[`Luke`]** Once you run the Section 8.1 commands in `.venv-ann`, what are the exact `SENTENCE_TRANSFORMERS_VERSION` and 40-hex `MODEL_REVISION` values to lock in `src/graph_insertion/embedding_minilm.py` and `pyproject.toml`, and what does the Section 8.2 OpenMP timing snippet report before and after `faiss.omp_set_num_threads(1)`?
2. **[`APC` / `APC-A`]** Because default run directories (`results/<mode>_<strategy>_<slug>`) do not include the embedder type (`fake` vs `minilm`), an offline `--confirm` smoke run that uses `--output-dir` defaults will write `"type": "fake"` into `results/<mode>_<strategy>_<slug>/strategy_config.json`, causing the tightened resume guard (`[D-66](2)`) to refuse a subsequent `--live --embedder minilm` run into the same default directory unless the offline smoke directory is deleted or uses `--output-dir` / `--run-id`. Should offline `--embedder fake` runs append `_fake` to the default `run_id`, or is refusing to mix/overwrite an offline smoke directory with a live run the desired guard behavior?
