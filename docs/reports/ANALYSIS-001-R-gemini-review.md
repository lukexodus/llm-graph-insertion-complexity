# ANALYSIS-001-R: Independent Review of `scripts/analysis/validate_runs.py`

## 1. Independence and Task Context

- **Task ID**: `ANALYSIS-001-R`
- **Reviewer Agent**: `gemini`
- **Session ID**: `562e3bc6-c12a-4372-85af-70eb9ecebfc7`
- **Exact Model Label**: `Gemini 3.8 Flash`
- **Independence Certification**: Confirmed independent. This session is NOT any of the excluded sessions:
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`
  - `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
  - `f4b13de1-a057-445e-a788-0523b774b94d` (author session of `ANALYSIS-001`)
  - Any session running `DOC-010`
  - Any session starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.
- **Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-001-R`
- **Branch**: `task/ANALYSIS-001-R`
- **Base Commit**: `aa58fc9f2a31a79fe244e6892766d28f607aa9b8` (`aa58fc9`, verified clean master)

---

## 2. Review Scope: Answers to Key Verification Questions (1 to 8)

### Question 1: Independent Recomputation
> *Is the recomputation independent (no import of harness or analysis-pipeline code; its own parsing of raw.jsonl and its own P/R/F1, shortlist recall, mean calls, mean total_s)?*

**Answer**: **YES.** The recomputation in `scripts/analysis/validate_runs.py` is fully independent.
- **Imports (`validate_runs.py:41-50`)**: Contains only Python standard library modules (`argparse`, `csv`, `hashlib`, `json`, `math`, `statistics`, `sys`, `pathlib`, `typing`). It imports **no code** from `src.graph_insertion.harness`, `src.graph_insertion.loader`, or any downstream analysis plotting/reporting modules.
- **Parsing `raw.jsonl` (`validate_runs.py:182-198`)**: `parse_raw_jsonl` reads the file line by line directly, deserializing each line with `json.loads(line)` and indexing by `rec.get("key")`.
- **Metrics Recomputation (`validate_runs.py:207-320`)**:
  - **LLM Calls (`lines 239-240`)**: `total_calls = sum(r.get("metrics", {}).get("llm_calls", 0) for r in successes)` and `mean_calls = (total_calls / num_success) if num_success > 0 else 0.0`.
  - **Timings (`lines 243-245`)**: Extracts `total_s` across successes; derives `mean_total_s` via `statistics.mean` and `med_total_s` via `statistics.median`.
  - **Micro Precision, Recall, F1, Shortlist Recall (`lines 288-294`)**: Computes `tot_tp`, `tot_fp`, `tot_fn`, `shortlist_hits_tot`, and `gold_neighbours_tot` directly from individual trial `score` dictionaries; derives micro metrics from raw contingency counts.
  - **Macro Precision, Recall, F1, Shortlist Recall (`lines 296-301`)**: Averages trial-level precision, recall, and F1. Macro shortlist recall correctly excludes nodes with no gold neighbours (`if gn > 0 and sr is not None`, matching Section 3.1 of `docs/context/analysis-plan.md`).

---

### Question 2: Trial Counting and Deduplication Consistency
> *Trial counting by UNIQUE key per corpus; last record per key wins, matching `load_existing_results` and `generate_summary_csv` in `harness.py` (confirm the harness behaviour yourself and quote the lines).*

**Answer**: **CONFIRMED.** Both `harness.py` and `validate_runs.py` implement the exact same semantic: sequential dict insertion by key where later records overwrite earlier records (last record per key wins).
- **In `src/graph_insertion/harness.py`**:
  - `load_existing_results` (`lines 316-326`):
    ```python
    316:     results = {}
    317:     with open(jsonl_path, "r", encoding="utf-8") as f:
    318:         for line in f:
    319:             line = line.strip()
    320:             if not line:
    321:                 continue
    322:             try:
    323:                 rec = json.loads(line)
    324:                 key = rec.get("key")
    325:                 if key:
    326:                     results[key] = rec
    ```
  - `generate_summary_csv` (`lines 441-455`):
    ```python
    441:     records_by_key: dict[str, dict[str, Any]] = {}
    442:     if not jsonl_path.exists():
    443:         return
    444:     with open(jsonl_path, "r", encoding="utf-8") as f:
    445:         for idx, line in enumerate(f):
    446:             line = line.strip()
    447:             if line:
    448:                 try:
    449:                     rec = json.loads(line)
    450:                     key = rec.get("key") or f"unkeyed_{idx}"
    451:                     records_by_key[key] = rec
    452:                 except Exception:
    453:                     pass
    454: 
    455:     records = list(records_by_key.values())
    ```
- **In `scripts/analysis/validate_runs.py`**:
  - `recompute_metrics` (`lines 214-219`):
    ```python
    214:     records_by_key: Dict[str, Dict[str, Any]] = {}
    215:     for idx, r in enumerate(records):
    216:         k = r.get("key") or f"unkeyed_{idx}"
    217:         records_by_key[k] = r
    218: 
    219:     deduped_records = list(records_by_key.values())
    ```
  - `unique_trial_keys` is tracked via `key_counts` (`line 467`), requiring `unique_trial_keys == expected_total` (59 for accuracy, 60 for sweep). Per-group counts are derived from `recomputed[grp]["num_trials"]` (`lines 485-492`), which groups `deduped_records` by corpus/size.

---

### Question 3: Resume Detection and Failure Accounting
> *Resume detection: duplicate keys flagged; does the report state that a zero-trial resume leaves no trace in raw.jsonl and rewrites manifest.json and summary.csv? Failed-then-succeeded keys listed separately from still-failed keys; nothing imputed.*

**Answer**:
1. **Duplicate keys flagged**: In `validate_runs.py:195-196`, `has_duplicates` is set if any `key_counts[k] > 1`. In `line 445`, `info["resumed"] = has_duplicates`, and in `line 661 / 705`, runs with duplicate keys are labelled `PASS (resumed)`.
2. **Zero-trial resume gap**: **NO.** The report (`docs/reports/ANALYSIS-001-validator-report.md`) and the validator script do NOT state or account for the fact that a zero-trial resume leaves no trace in `raw.jsonl` while overwriting `manifest.json` and `summary.csv`. In `harness.py:747, 977`, when all keys are already present as successes, `_load_existing_keys` skips all planned keys. `write_manifest` (line 740) overwrites `manifest.json` with a new timestamp and git state, and `generate_summary_csv` (line 932) rewrites `summary.csv`, but `raw.jsonl` receives 0 new lines. Because `raw.jsonl` contains no duplicate keys, `validate_runs.py` reports `resumed: False`.
3. **Failed-then-succeeded vs still-failed**: **NOT SEPARATED.** In `validate_runs.py:449-462`, `failed_trials_list` iterates through `raw_records` (the raw, undeduplicated lines) and records every line where `status == "failed"`. It does **not** cross-reference against the final status of that key. In `accuracy_brute_force`, 5 trials initially failed and were retried and succeeded on resume; the validator reports `Trials: 59 (failed=5, retries=18)` in Table T3/CLI, while the recomputed summary metrics show `num_failed = 0`. The validator never categorizes them as "failed-then-succeeded" vs "still-failed".
4. **Imputation**: Nothing is imputed; failed trials and retries are directly tallied.

---

### Question 4: Embedder Thread Check and Bound Enforcement
> *The thread check: is it gated on embedder.model_name being non-None or on directory name? Bounds keyed by directory name? Could a renamed directory slip through?*

**Answer**:
1. **Thread check gating (`validate_runs.py:404-437`)**: It is **NOT** gated on `embedder.model_name` being non-None, nor on the directory name. It is gated strictly fail-closed on `strategy`:
   `is_embedding_strategy = strat in ("embedding_threshold", "ann_retrieval", "bounded_bucket")`
   If True: `embedder` MUST be a dict in `strategy_config.json`, `cpu_threads` must equal 1, and `torch_threads` must equal 1.
   If False (`brute_force`): `embedder.model_name` and `embedder.cpu_threads` must be `None` or absent (`lines 434-437`).
2. **Bound lookup (`validate_runs.py:112-169, 496`)**: Call bounds in `get_planned_call_bound` are keyed strictly by `(strategy, config, mode)`. They are **NOT** keyed by directory name.
3. **Could a renamed directory slip through?**: **YES.** The validator **never compares directory name against `manifest["run_id"]` or `strategy_config.json`**. Although module docstring line 14 claims `Directory slug cross-checked`, this check was **never implemented**. A swapped or renamed run directory passes validation completely unnoticed with exit code 0 (verified in Mutation h).

---

### Question 5: Provenance and Uniformity Checks
> *Does it check git_commit identical across runs, git_dirty false, libraries identical, cpu_threads and torch_threads equal 1 for embedding strategies, embedder identity identical?*

**Answer**: **YES to all.**
- `git_dirty`: Must be strictly boolean `False` (`validate_runs.py:364-365`).
- `git_commit`: Checked for non-empty string in single run (`validate_runs.py:359-362`), and enforced identical across all runs (`validate_runs.py:610-616`).
- `libraries`: Must contain all 7 `REQUIRED_LIBRARIES` (`networkx`, `pytest`, `httpx`, `numpy`, `torch`, `faiss-cpu`, `sentence-transformers`) in single run (`lines 373-382`), and enforced identical across all runs (`lines 618-623`).
- `cpu_threads` & `torch_threads`: Strictly enforced `== 1` for all 3 embedding strategies (`lines 415-418`).
- Embedder identity: Verified against constants `EXPECTED_EMBEDDER_MODEL = "all-MiniLM-L6-v2"` and `EXPECTED_EMBEDDER_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"` in single runs (`lines 419-426`), and cross-run uniformity enforced in `validate_all_runs` (`lines 625-644`).

---

### Question 6: Fail-Closed Behavior
> *Fail-closed: what happens on a missing file, malformed JSON line, empty raw.jsonl, extra unexpected key, NaN? Exit code in each case.*

**Answer**:
- **Missing file**: Detected at `validate_runs.py:334-344`. Emits `Missing required file: <name>`, returns `False`, exits with **code 1**.
- **Malformed JSON line in `raw.jsonl`**: Caught at `validate_runs.py:441-443`. Emits `Invalid JSON/format in raw.jsonl: ...`, returns `False`, exits with **code 1**.
- **Empty `raw.jsonl`**: Returns 0 unique trial keys; fails count check at `line 477` (`Unique trial count mismatch: raw.jsonl has 0 unique keys, expected 59`), returns `False`, exits with **code 1**.
- **Extra unexpected key**:
  - *In trial keys*: If an extra trial key exists, unique trial count exceeds expected total (e.g. 60 instead of 59); caught at `line 477`, returns `False`, exits with **code 1**.
  - *In JSON records/manifest schema*: Extra dictionary keys (e.g. `rec["extra_field"] = 123`) are **ignored** because no strict schema validation is applied. Exits with **code 0**.
- **NaN**:
  - *In float accuracy metrics / total_s*: `math.isclose(nan, nan)` evaluates to `False`. Triggers metric mismatch error (`lines 550, 578`), returns `False`, exits with **code 1**.
  - *In integer fields (`num_trials`, `llm_calls_sum`)*: `int(s_row.get(cnt_field, 0))` (`line 538`) is unhandled; raises uncaught `ValueError: invalid literal for int() with base 10: 'NaN'`. Process terminates with exception traceback and exits with **code 1** (fail-closed, but unhandled).

---

### Question 7: Sweep Mode Coverage
> *Sweep mode: has it ever run on anything but a synthetic fixture? Is the sweep call bound and trial count logic exercised by a test?*

**Answer**:
- **Has it run on anything but a synthetic fixture?**: **NO.** The repo's `results/` directory contains only the 12 accuracy directories (`accuracy_*`), `datagen`, `pilot`, and `np1w-artifacts.tar.gz`. Zero sweep runs exist in `results/`. As pre-registered in `analysis-plan.md` Section 7, sweep data remains unopened and unexecuted. `validate_runs.py` has run only on synthetic sweep fixtures generated in `tests/test_analysis_validate_runs.py`.
- **Is the sweep call bound and trial count logic exercised by a test?**: **PARTIALLY.**
  - `test_baseline_control_sweep` (`tests/test_analysis_validate_runs.py:310-319`) creates a valid synthetic sweep run and verifies that it passes (`trials == 60`, `total_calls == 60`).
  - **However**, there are **ZERO negative mutant tests for sweep mode**. All 13 mutants in `tests/test_analysis_validate_runs.py` test only accuracy mode fixtures. Sweep trial count mismatches (e.g. 59 trials or missing size bins) and sweep call bound violations (e.g. calls > 600) have **no test coverage whatsoever**.

---

### Question 8: Test Suite Mutant Verification
> *Do the tests' mutants kill real changes, or are they self-graded?*

**Answer**: **The mutants kill real changes on disk.**
- Each mutant test in `tests/test_analysis_validate_runs.py` writes a mutated file structure to `tmp_path` and directly executes `validate_single_run` or `validate_all_runs`.
- The tests verify that `passed` is `False` and assert the presence of specific error strings in `errors`. They are not self-graded stubs or mock assertions.
- **Blind spots**: As documented below, several failure modes are completely untested (sweep mutants, mid-line truncation, slug mismatch, resume trace deletion).

---

## 3. Corruption Table (Executed Live under `/tmp`)

### Baseline Control Run
- **Target**: Pristine copy of `/home/lukexodus/projects/llm-graph-insertion-complexity/results/accuracy_ann_retrieval_k10_ef128` copied to `/tmp/eval_baseline/`
- **Command**: `python3 scripts/analysis/validate_runs.py /tmp/eval_baseline`
- **Verbatim Output**:
  ```text
  ================================================================================
  RUN VALIDATION GATE: /tmp/eval_baseline
  ================================================================================
  [PASS] accuracy_ann_retrieval_k10_ef128
         Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
         Calls:    590 / 590 bound | Trials: 59 (failed=0, retries=0)
         SHA256:   78470a52494b51af6e2fac98caffc737f79c37f5110ad47a18fb92a2d934e72c
  --------------------------------------------------------------------------------
  OVERALL GATE STATUS: PASS
  ```
- **Exit Code**: `0` (Baseline passed cleanly).

---

### Executed Mutations (a) through (j)

| ID | Mutation Applied | Command Executed | Caught? | Verbatim Failing Line / Result | Exit Code |
|---|---|---|---|---|---|
| **(a)** | Change one `summary.csv` F1 value by 0.001 (`0.511111` -> `0.512111`) | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_a` | **YES** | `-> ERROR: f1_micro mismatch for 'DSA_gold_standard_MEKG': summary=0.512111 vs raw=0.511111` | `1` |
| **(b)** | Delete one `raw.jsonl` line (leaving 58 trials) | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_b` | **YES** | `-> ERROR: Unique trial count mismatch: raw.jsonl has 58 unique keys, expected 59 for mode 'accuracy'` | `1` |
| **(c)** | Duplicate one `raw.jsonl` line (appended identical record to end) | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_c` | **NO (SILENT PASS)** | `[PASS (resumed)] accuracy_ann_retrieval_k10_ef128` <br>`OVERALL GATE STATUS: PASS` | `0` |
| **(d)** | Make final record for a key a failure (`status: failed`) while summary says success | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_d` | **YES** | `-> ERROR: num_success mismatch for group 'DSA_gold_standard_MEKG': summary=29 vs raw=28` | `1` |
| **(e)** | Delete duplicate-key trace from resumed copy of `accuracy_brute_force` (64 lines -> 59 keys) while summary is unchanged | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_e` | **NO (SILENT PASS)** | `[PASS] accuracy_brute_force` <br>`OVERALL GATE STATUS: PASS` | `0` |
| **(f)** | Change `git_dirty` to `true` in manifest | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_f` | **YES** | `-> ERROR: Manifest git_dirty is not False: True` | `1` |
| **(g)** | Change `cpu_threads` to `4` in `strategy_config.json` | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_g` | **YES** | `-> ERROR: Sidecar cpu_threads != 1: got 4` | `1` |
| **(h)** | Swap two run directory names (`..._k10_ef128` <-> `..._k5_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_h` | **NO (SILENT PASS)** | `[PASS] accuracy_ann_retrieval_k10_ef128` (reported with 295 calls) <br>`[PASS] accuracy_ann_retrieval_k5_ef128` (reported with 590 calls) <br>`OVERALL GATE STATUS: PASS` | `0` |
| **(i)** | Change one library version in manifest (`torch = '9.9.9'`) across two runs | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_i` | **YES** | `-> ERROR: Cross-run libraries block mismatch between this run and baseline run` | `1` |
| **(j)** | Truncate a `raw.jsonl` mid-line | `python3 scripts/analysis/validate_runs.py /tmp/eval_mut_j` | **YES** | `-> ERROR: Invalid JSON/format in raw.jsonl: Unterminated string starting at: line 1 column 1558 (char 1557)` | `1` |

---

## 4. Test Suite Execution Counts

1. **Validator Specific Tests (`tests/test_analysis_validate_runs.py`)**:
   - Command: `../llm-graph-insertion-complexity/.venv-ann/bin/pytest tests/test_analysis_validate_runs.py`
   - Result: **17 passed** in 0.36s.

2. **Full Repository Test Suite**:
   - Command: `../llm-graph-insertion-complexity/.venv-ann/bin/pytest`
   - Result in this dedicated task worktree (`task/ANALYSIS-001-R`):
     - **647 passed, 43 failed, 26 skipped, 3 errors** in 100.35s.
   - **Root Cause Analysis of Worktree Failures**:
     - All 43 failures and 3 errors are caused by `FileNotFoundError: Dataset root directory does not exist: .../repositories/dataset/EKG-Dataset`.
     - In the main repository, `repositories/` is untracked and gitignored (`repositories/ -> repositories/dataset`). When a standard git worktree is created (`git worktree add`), untracked/gitignored folders are not automatically cloned or symlinked into the worktree.
     - On the main checkout (`/home/lukexodus/projects/llm-graph-insertion-complexity`), where the untracked `repositories/dataset/` exists, the full test suite passes with the baseline count: **716 passed, 3 skipped**.

---

## 5. List of Gaps Ranked by Risk to Pre-Registered Analysis

### Rank 1 (HIGH RISK): Directory Name / Slug Blindness (Silent Misattribution)
- **Vulnerability**: As demonstrated in Mutation (h), swapping or renaming directory names is completely undetected by the validator. The validator uses `run_dir.name` solely for terminal display and Table T3 output, but never validates `run_dir.name` against `manifest["run_id"]` or against the configuration in `strategy_config.json`.
- **Impact on Pre-Registered Analysis**: If a run directory is renamed or misnamed before running analysis plotting scripts (e.g. `plot_figures.py`), data will be attributed to the wrong strategy or configuration in Figures F1–F6 and Table T1–T2 without tripping the validation gate.
- **Recommended Fix**: Enforce canonical slug matching: `expected_slug = derive_slug(strat, strat_cfg, mode); if run_dir.name != expected_slug: errors.append(...)` and require `manifest["run_id"] == run_dir.name`.

### Rank 2 (HIGH RISK): Resumed Run History Tampering & Duplicate Blindness
- **Vulnerability**:
  - As demonstrated in Mutation (e), deleting the duplicated failed trials from `raw.jsonl` in a resumed run leaves the exact planned number of unique keys and matching summary metrics. The validator reports `[PASS]` as an unresumed clean run.
  - As demonstrated in Mutation (c), duplicating an identical line in `raw.jsonl` does not fail the gate; it is silently promoted to `PASS (resumed)`.
  - Furthermore, zero-trial resumes (resuming a fully completed run) modify `manifest.json` and `summary.csv` but leave no trace in `raw.jsonl`, causing the run to be falsely reported as non-resumed.
- **Impact on Pre-Registered Analysis**: Violates Section 2 and Amendment 1 of `analysis-plan.md`, which mandates that "no run was resumed, or each resumed run is flagged" and "retries and failed trials listed".
- **Recommended Fix**:
  - In `raw.jsonl`, verify that any duplicate key corresponds to an actual state transition (e.g. earlier trial was `status: failed` and later trial was `status: success`). An exact duplicate success record must be rejected as corrupt.
  - Cross-check `manifest.json` timestamp against the latest timestamp in `raw.jsonl`. A manifest written significantly after the last trial record indicates a zero-trial resume.

### Rank 3 (MEDIUM RISK): Zero Negative/Mutant Tests for Sweep Mode
- **Vulnerability**: No tests in `test_analysis_validate_runs.py` mutate or corrupt a sweep run.
- **Impact on Pre-Registered Analysis**: Sweep data is unopened and unexecuted. When the 12 sweep runs are generated, if there is a discrepancy in how sweep group sizes (`{50, 100, 200, 500, 1000, 2000}`) or sweep trial keys (`sweep:<strat>:<n>:t<idx>`) are formatted, or if bounds are breached, it will be the first time this code path is tested under failure conditions.
- **Recommended Fix**: Add unit tests in `test_analysis_validate_runs.py` asserting that sweep runs fail on: (1) 59 trials instead of 60, (2) missing size bin (e.g. only 5 sizes), and (3) realized LLM calls exceeding 600 / 300 / 1200 / 38500.

### Rank 4 (MEDIUM RISK): Ambiguous Failure Accounting in Table T3
- **Vulnerability**: `failed_trials_count` in `validate_runs.py:460` counts all historical failed records in `raw.jsonl`. For `accuracy_brute_force`, it reports `failed=5`, even though all 5 trials were retried and succeeded on resume (`num_failed = 0` in `summary.csv`).
- **Impact on Pre-Registered Analysis**: Table T3 conflates recovered failures with unrecovered failures. A reader looking at Table T3 cannot tell whether `failed=5` means 5 missing/unusable trials or 5 transient retries.
- **Recommended Fix**: Explicitly partition failed trials into `recovered_failures` (failed then succeeded) and `terminal_failures` (final record is failed).

### Rank 5 (LOW RISK): Unhandled Exception on Non-Numeric Fields in `summary.csv`
- **Vulnerability**: Line 538 executes `s_val = int(s_row.get(cnt_field, 0))` without a try-except block. Non-integer strings like `"NaN"` or `"12.5"` cause the validator to crash with an unhandled `ValueError` rather than appending a structured validation error to `errors`.
- **Impact on Pre-Registered Analysis**: Minimal; still fails closed (exit code 1), but degrades error diagnostics.

---

## 6. Handoff Note
- This review report is committed on branch `task/ANALYSIS-001-R` in worktree `../llm-graph-insertion-complexity-ANALYSIS-001-R`.
- No code in `scripts/analysis/validate_runs.py` or `tests/test_analysis_validate_runs.py` was altered.
- Formatted patch exported to `patch/`.
- Ready for Luke and APC review.
