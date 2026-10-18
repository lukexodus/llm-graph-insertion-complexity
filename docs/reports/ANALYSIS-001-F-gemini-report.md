# ANALYSIS-001-F: Fix `validate_runs.py` Gaps and Record Plan Amendment 2

## 1. Independence Certification and Identification

- **Task ID**: `ANALYSIS-001-F`
- **Agent Name**: `gemini`
- **Session ID**: `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2`
- **Exact Model Label**: `Gemini 3.8 Flash (Medium)`
- **Independence Certification**: Confirmed independent. This session is NOT any of the excluded sessions:
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`
  - `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
  - `f4b13de1-a057-445e-a788-0523b774b94d`
  - `562e3bc6-c12a-4372-85af-70eb9ecebfc7`
  - `f339a846-e963-4b8f-a62e-4090862002e7`
  - Any session starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.

---

## 2. Setup and ID Check

- **Base Master Commit**: `git rev-parse --short master` returned `8d9b212` (expected `8d9b212`, verified clean).
- **Dedicated Worktree**: `../llm-graph-insertion-complexity-ANALYSIS-001-F`
- **Branch**: `task/ANALYSIS-001-F`
- **Decision ID Check**:
  - `git grep -n '\[D-83\]' $(git rev-list --all)` returned zero matches.
  - Checked `decision-log.md` across main repo and existing worktrees (`DOC-007`); zero occurrences of `[D-83]`.

---

## 3. Test Suite Executions and Worktree Dataset Failure Report

### 3.1 Validator Specific Suite (`tests/test_analysis_validate_runs.py`)
- **Command**: `pytest tests/test_analysis_validate_runs.py`
- **Result**: **27 passed** in 1.85s.

### 3.2 Full Repository Test Suite (`pytest`)
- **Command**: `pytest`
- **Result**: **550 passed, 61 failed, 3 errors, 34 skipped** in 82.41s.
- **Root Cause Analysis of Worktree Failures**:
  - Every single failure (61 failed) and collection error (3 errors) was caused exclusively by the missing untracked/gitignored dataset directory:
    `FileNotFoundError: Dataset root directory does not exist: .../repositories/dataset/EKG-Dataset`
  - The dataset `repositories/dataset/` is untracked and gitignored in the main repository checkout. Standard git worktrees created via `git worktree add` do not clone untracked directories.
  - Zero test failures were related to validator code, embedding logic, or analysis plan modifications.

---

## 4. Resume Skip Logic and Duplicate Key Confirmation

Confirmation from `src/graph_insertion/harness.py`:
In `_load_existing_keys` (`harness.py:362-375`):
```python
362: def _load_existing_keys(raw_jsonl_path: Path, retry_failed: bool = False) -> set[str]:
363:     """Load trial keys from raw.jsonl that should be skipped on resume.
364: 
365:     A trial is skipped if status is 'success', or if status is 'failed'/'error' and retry_failed is False.
366:     """
367:     existing_results = load_existing_results(raw_jsonl_path)
368:     skipped_keys: set[str] = set()
369:     for key, rec in existing_results.items():
370:         status = rec.get("status")
371:         if status == "success":
372:             skipped_keys.add(key)
373:         elif status in ("failed", "error") and not retry_failed:
374:             skipped_keys.add(key)
375:     return skipped_keys
```

In `run_accuracy_experiment` (`harness.py:747, 770-772`):
```python
747:     skipped_keys = _load_existing_keys(raw_jsonl_path, retry_failed=config.retry_failed) if config.resume else set()
...
770:                     trial_key = accuracy_trial_key(strategy_name, corpus_name, h, rep)
771: 
772:                     if trial_key in skipped_keys:
773:                         continue
```

In `run_sweep_experiment` (`harness.py:977, 1001-1004`):
```python
977:     skipped_keys = _load_existing_keys(raw_jsonl_path, retry_failed=config.retry_failed) if config.resume else set()
...
1001:                 trial_key = sweep_trial_key(strategy_name, n, trial_idx)
1002: 
1003:                 if trial_key in skipped_keys:
1004:                     continue
```

**Conclusion**:
Because `_load_existing_keys` unconditionally adds any key with `status == "success"` to `skipped_keys` and the harness loop skips keys present in `skipped_keys`, a trial key that already completed successfully is **never re-executed or appended again** by the harness. Therefore, any duplicate key in `raw.jsonl` where an earlier record has `status == "success"` is invalid and rejected fail-closed as corrupt.

---

## 5. Zero-Trial Resume Mechanics

When `--resume` is invoked on a completed run directory where all planned keys have already succeeded:
1. `_load_existing_keys` loads all existing successful keys into `skipped_keys`.
2. `all_planned_keys` matches `skipped_keys`, so `total_trials = sum(1 for k in all_planned_keys if k not in skipped_keys)` evaluates to `0`.
3. In the execution loops, every trial key is skipped via `if trial_key in skipped_keys: continue`.
4. As a result, **zero lines are appended to `raw.jsonl`**, leaving no trace of duplicate keys in `raw.jsonl`.
5. However, `write_manifest` (line 740 / line 972) is called before the execution loop, which **rewrites `manifest.json`** with a new timestamp and git state.
6. Similarly, `generate_summary_csv` (line 839 / line 1047) is called at conclusion, which **rewrites `summary.csv`**.
7. Because `raw.jsonl` contains zero duplicate keys, static analysis of `raw.jsonl` alone reports `resumed: False`. The only evidence of a zero-trial resume is the discrepancy between the `manifest.json` timestamp and the latest record timestamp in `raw.jsonl`.

---

## 6. Optional `--hashes FILE` Argument and External Hash File Absence

- An optional `--hashes FILE` argument has been implemented in `scripts/analysis/validate_runs.py`. It parses standard `sha256sum` output files and validates the SHA256 of `manifest.json`, `strategy_config.json`, `raw.jsonl`, and `summary.csv` against the machine-written hash list, failing closed on mismatch.
- **Absence Confirmation**: A search for `run-logs/results-file-hashes.txt` (or any `results-file-hashes.txt` on the filesystem) confirms that this file is currently **absent** from disk. When `--hashes` is not specified on the CLI, the validation gate proceeds without external hash comparison and Table T3 continues to compute and record the deterministic composite SHA256.

---

## 7. Executed Corruption Matrix (Baselines and Mutants)

All mutants and baseline controls were executed live under `/tmp/eval_analysis_001_f/` with `scripts/analysis/validate_runs.py`.

### 7.1 Summary Table

| ID | Category | Change Description | Command Executed | Caught? | Verbatim Failing Line / Error | Exit Code |
|---|---|---|---|---|---|---|
| **B1** | Commit Gate | Baseline clean runs (identical commits across accuracy and sweep) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b1_commits` | N/A (PASS) | Baseline passed cleanly | `0` |
| **M1a** | Commit Gate | Intra-mode commit mismatch (two accuracy runs with different commits) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m1a_intra_commit` | **YES** | `-> ERROR: Intra-mode git_commit mismatch within mode 'accuracy': found multiple commits ['1111111111111111111111111111111111111111', '3323bfbd03b6490aeef2d864b9d77271bd9a340e']` | `1` |
| **M1b** | Commit Gate | Cross-mode commit mismatch without `--src-diff-clean` | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m1b_cross_commit` | **YES** | `-> ERROR: Cross-mode git_commit mismatch: commits differ across modes {'accuracy': ['3323bfbd03b6490aeef2d864b9d77271bd9a340e'], 'sweep': ['2222222222222222222222222222222222222222']}. Must pass --src-diff-clean to accept differing commits across modes.` | `1` |
| **C1c** | Commit Gate | Cross-mode commit mismatch accepted with `--src-diff-clean` | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m1b_cross_commit --src-diff-clean` | N/A (PASS) | Passed cleanly under `--src-diff-clean` | `0` |
| **B2** | Directory / Slug | Baseline canonical directory slug and `manifest.json` `run_id` | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b2_slug/accuracy_ann_retrieval_k10_ef128` | N/A (PASS) | Baseline passed cleanly | `0` |
| **M2a** | Directory / Slug | Directory name vs `manifest.json` `run_id` mismatch | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m2a_manifest_id/accuracy_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k5_ef128'` | `1` |
| **M2b** | Directory / Slug | Directory name vs `strategy_config.json` slug mismatch (dir k5, config k10) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m2b_slug_mismatch/accuracy_ann_retrieval_k5_ef128` | **YES** | `-> ERROR: Directory name 'accuracy_ann_retrieval_k5_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'` | `1` |
| **M2c** | Directory / Slug | Swapped run directories on disk (Mutation h) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m2c_swapped` | **YES** | `-> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k5_ef128'` | `1` |
| **B3** | Duplicate Keys | Resumed run with recovered failure (failed then succeeded) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b3_resume/accuracy_ann_retrieval_k10_ef128` | N/A (PASS) | `[PASS (resumed)]` reported with 1 failed-then-succeeded key | `0` |
| **M3a** | Duplicate Keys | Duplicate key where earlier record was success (Mutation c) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m3a_dup_success/accuracy_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Invalid duplicate trial key 'accuracy:ann_retrieval:DSA_gold_standard_MEKG:node_0:r0': earlier record at index 0 has status 'success' (harness skips successful keys on resume)` | `1` |
| **B5** | External Hashes | Valid machine-written hash list matching all 4 files | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b5_hashes/accuracy_ann_retrieval_k10_ef128 --hashes ...` | N/A (PASS) | Baseline passed cleanly | `0` |
| **M5a** | External Hashes | SHA256 mismatch in `--hashes` file | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b5_hashes/accuracy_ann_retrieval_k10_ef128 --hashes ...` | **YES** | `-> ERROR: File SHA256 mismatch for 'accuracy_ann_retrieval_k10_ef128/raw.jsonl': computed 'ee001348...' != expected '00000000...'` | `1` |
| **B6** | Sweep Mode | Clean 60-trial sweep run with k=10 within 600 bound | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b6_sweep/sweep_ann_retrieval_k10_ef128` | N/A (PASS) | Baseline passed cleanly | `0` |
| **M6a** | Sweep Mode | Sweep missing size 2000 (50 trials instead of 60) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m6a_sweep_count/sweep_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Unique trial count mismatch: raw.jsonl has 50 unique keys, expected 60 for mode 'sweep'` | `1` |
| **M6b** | Sweep Mode | Sweep call bound exceeded (660 realized calls for k10, cap 600) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m6b_sweep_calls/sweep_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Realised LLM calls 660 exceeds planned upper bound 600 for strategy 'ann_retrieval'` | `1` |
| **M6c** | Sweep Mode | Thread pin violated in sweep (`cpu_threads=4` in sidecar) | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m6c_sweep_threads/sweep_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Sidecar cpu_threads != 1: got 4` | `1` |
| **F7** | Resumed Fixture | 64 lines in raw.jsonl, 59 keys, 5 failed-then-succeeded keys | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/b7_resumed_fixture/accuracy_brute_force` | N/A (PASS) | `[PASS (resumed)]` with 5 failed-then-succeeded, 0 still-failed | `0` |
| **M8** | Integer Parsing | Non-integer literal (`NaN`) in summary.csv `num_trials` | `python3 scripts/analysis/validate_runs.py /tmp/eval_analysis_001_f/m8_nan/accuracy_ann_retrieval_k10_ef128` | **YES** | `-> ERROR: Invalid integer value 'NaN' for field 'num_trials' in summary.csv: invalid literal for int() with base 10: 'NaN'` | `1` |

---

### 7.2 Verbatim Command Outputs

#### Baseline 1: Commit Gate Clean
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b1_commits
================================================================================
[PASS] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
--------------------------------------------------------------------------------
[PASS] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 3323bfb | git_dirty: False
       Calls:    60 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   69a86dab7f706fcbaeee2847ff46971b9b151ec429e8f10f814af9ff831ae2f4
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 1a: Intra-Mode Commit Mismatch
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m1a_intra_commit
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
       -> ERROR: Intra-mode git_commit mismatch within mode 'accuracy': found multiple commits ['1111111111111111111111111111111111111111', '3323bfbd03b6490aeef2d864b9d77271bd9a340e']
       -> ERROR: Cross-mode git_commit mismatch: commits differ across modes {'accuracy': ['1111111111111111111111111111111111111111', '3323bfbd03b6490aeef2d864b9d77271bd9a340e']}. Must pass --src-diff-clean to accept differing commits across modes.
--------------------------------------------------------------------------------
[FAIL] accuracy_ann_retrieval_k5_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 1111111 | git_dirty: False
       Calls:    295 / 295 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   f0f8ba0e77887856aed477bf914f56d17be308839c16eadf71a3376829de3e8d
       -> ERROR: Intra-mode git_commit mismatch within mode 'accuracy': found multiple commits ['1111111111111111111111111111111111111111', '3323bfbd03b6490aeef2d864b9d77271bd9a340e']
       -> ERROR: Cross-mode git_commit mismatch: commits differ across modes {'accuracy': ['1111111111111111111111111111111111111111', '3323bfbd03b6490aeef2d864b9d77271bd9a340e']}. Must pass --src-diff-clean to accept differing commits across modes.
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Mutant 1b: Cross-Mode Commit Mismatch Without `--src-diff-clean`
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m1b_cross_commit
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
       -> ERROR: Cross-mode git_commit mismatch: commits differ across modes {'accuracy': ['3323bfbd03b6490aeef2d864b9d77271bd9a340e'], 'sweep': ['2222222222222222222222222222222222222222']}. Must pass --src-diff-clean to accept differing commits across modes.
--------------------------------------------------------------------------------
[FAIL] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 2222222 | git_dirty: False
       Calls:    60 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   97f245a2d8d78e9937b9856628dc338b6ec43214a131f40c494275142dd71775
       -> ERROR: Cross-mode git_commit mismatch: commits differ across modes {'accuracy': ['3323bfbd03b6490aeef2d864b9d77271bd9a340e'], 'sweep': ['2222222222222222222222222222222222222222']}. Must pass --src-diff-clean to accept differing commits across modes.
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Control 1c: Cross-Mode Commit Difference Accepted With `--src-diff-clean`
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m1b_cross_commit
================================================================================
[PASS] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
--------------------------------------------------------------------------------
[PASS] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 2222222 | git_dirty: False
       Calls:    60 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   97f245a2d8d78e9937b9856628dc338b6ec43214a131f40c494275142dd71775
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Baseline 2: Canonical Directory Slug and Run ID
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b2_slug/accuracy_ann_retrieval_k10_ef128
================================================================================
[PASS] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 2a: Directory Name vs `manifest.json` `run_id` Mismatch
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m2a_manifest_id/accuracy_ann_retrieval_k10_ef128
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   3ec70ac26b2e6a91b59ae1dbb3f775f9c7377ffe7a6efd0ba97d4aecaa7beb71
       -> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k5_ef128'
       -> ERROR: Manifest run_id 'accuracy_ann_retrieval_k5_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Mutant 2b: Directory Name vs `strategy_config.json` Slug Mismatch
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m2b_slug_mismatch/accuracy_ann_retrieval_k5_ef128
================================================================================
[FAIL] accuracy_ann_retrieval_k5_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   dcfb10ce07cfd413a09d33f42c2b7f8e5899e8a19f776051237e2bf51bd377d3
       -> ERROR: Directory name 'accuracy_ann_retrieval_k5_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'
       -> ERROR: Manifest run_id 'accuracy_ann_retrieval_k5_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Mutant 2c: Swapped Run Directories (Mutation h)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m2c_swapped
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 295 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   b6a640474ad904a7d0022be70ee58f743637805be192ca285ae13ea9eba4b662
       -> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k5_ef128'
       -> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k5_ef128'
--------------------------------------------------------------------------------
[FAIL] accuracy_ann_retrieval_k5_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
       -> ERROR: Directory name 'accuracy_ann_retrieval_k5_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k10_ef128'
       -> ERROR: Directory name 'accuracy_ann_retrieval_k5_ef128' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Baseline 3: Clean Resumed Run with Recovered Failure
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b3_resume/accuracy_ann_retrieval_k10_ef128
================================================================================
[PASS (resumed)] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=1, still_failed=0, retries=2)
       Failed-then-succeeded keys (1): accuracy:ann_retrieval:DSA_gold_standard_MEKG:node_0:r0
       SHA256:   9f46f923661f0baf514196ab3a1fb33a11bc194dda663edbc3dd7f0601f3a1f0
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 3a: Duplicate Key Whose Earlier Record Was Success (Mutation c)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m3a_dup_success/accuracy_ann_retrieval_k10_ef128
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   884ebc101b6bbb232f6c7987064c5d98342e516cafd7dbe18b166a87990e6d81
       -> ERROR: Invalid duplicate trial key 'accuracy:ann_retrieval:DSA_gold_standard_MEKG:node_0:r0': earlier record at index 0 has status 'success' (harness skips successful keys on resume)
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Baseline 5: Matching Machine-Written Hashes File
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b5_hashes/accuracy_ann_retrieval_k10_ef128
================================================================================
[PASS] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 5a: SHA256 Mismatch in `--hashes`
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b5_hashes/accuracy_ann_retrieval_k10_ef128
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   2676cd53b41c4b1fcdbd3a3a2e9d9e20986f3c5aa03c9564fe9bf7607a90cbf3
       -> ERROR: File SHA256 mismatch for 'accuracy_ann_retrieval_k10_ef128/raw.jsonl': computed 'ee001348b4d44a4ccedd29f3718d10d0f4b1c6fbd40dfc54c20b0db5ae55038e' != expected '0000000000000000000000000000000000000000000000000000000000000000'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Baseline 6: Clean Sweep Run
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b6_sweep/sweep_ann_retrieval_k10_ef128
================================================================================
[PASS] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 3323bfb | git_dirty: False
       Calls:    60 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   69a86dab7f706fcbaeee2847ff46971b9b151ec429e8f10f814af9ff831ae2f4
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 6a: Sweep Wrong Key Count (50 vs 60)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m6a_sweep_count/sweep_ann_retrieval_k10_ef128
================================================================================
[FAIL] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 3323bfb | git_dirty: False
       Calls:    50 / 600 bound | Trials: 50 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   fd753b1deda509aee4eedf583c6e7c12725b4836e6a18981208af751231c8604
       -> ERROR: Unique trial count mismatch: raw.jsonl has 50 unique keys, expected 60 for mode 'sweep'
       -> ERROR: Missing expected group '2000' in raw.jsonl
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Mutant 6b: Sweep Call Bound Exceeded (660 vs 600)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m6b_sweep_calls/sweep_ann_retrieval_k10_ef128
================================================================================
[FAIL] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 3323bfb | git_dirty: False
       Calls:    660 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   69d890609a9eba5c5ad54062683bdb0c15f7a247fee627d5ec5f2968ceaabbae
       -> ERROR: Realised LLM calls 660 exceeds planned upper bound 600 for strategy 'ann_retrieval'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Mutant 6c: Sweep Thread Pin Violated (`cpu_threads=4`)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m6c_sweep_threads/sweep_ann_retrieval_k10_ef128
================================================================================
[FAIL] sweep_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: sweep | Commit: 3323bfb | git_dirty: False
       Calls:    60 / 600 bound | Trials: 60 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   29d9296d3474f823aa3ef301a98ee86b86f38969d552b99bf047283e654d2390
       -> ERROR: Sidecar cpu_threads != 1: got 4
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

#### Fixture 7: 64-Line Resumed Directory Fixture (59 Keys, 5 Recovered)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/b7_resumed_fixture/accuracy_brute_force
================================================================================
[PASS (resumed)] accuracy_brute_force
       Strategy: brute_force | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 5012 bound | Trials: 59 (failed_then_succeeded=5, still_failed=0, retries=15)
       Failed-then-succeeded keys (5): accuracy:brute_force:metacademy_gold_standard_MEKG:node_0:r0, accuracy:brute_force:metacademy_gold_standard_MEKG:node_1:r0, accuracy:brute_force:metacademy_gold_standard_MEKG:node_2:r0, accuracy:brute_force:metacademy_gold_standard_MEKG:node_3:r0, accuracy:brute_force:metacademy_gold_standard_MEKG:node_4:r0
       SHA256:   87e238d4846e0bfa29243f74c11454093ab6f23ed693e1ecdf2be54015599c1b
--------------------------------------------------------------------------------
OVERALL GATE STATUS: PASS
```

#### Mutant 8: Non-Integer Value in `summary.csv` (`NaN`)
```text
================================================================================
RUN VALIDATION GATE: /tmp/eval_analysis_001_f/m8_nan/accuracy_ann_retrieval_k10_ef128
================================================================================
[FAIL] accuracy_ann_retrieval_k10_ef128
       Strategy: ann_retrieval | Mode: accuracy | Commit: 3323bfb | git_dirty: False
       Calls:    295 / 590 bound | Trials: 59 (failed_then_succeeded=0, still_failed=0, retries=0)
       SHA256:   49fb5ee9c1b5d996be1f5b78df7a85044380e3295d796e20fc746fd8d6375bc9
       -> ERROR: Invalid integer value in summary.csv num_trials: invalid literal for int() with base 10: 'NaN'
       -> ERROR: Invalid integer value 'NaN' for field 'num_trials' in summary.csv: invalid literal for int() with base 10: 'NaN'
--------------------------------------------------------------------------------
OVERALL GATE STATUS: FAIL
```

---

## 8. Analysis Plan Amendment 2 and Decision [D-83] Record

### 8.1 Amendment 2 Content
Appended to Section 8 of `docs/context/analysis-plan.md`:
```markdown
### Amendment 2 (2026-10-19):
1. **Commit gate (§2)**: `git_commit` must be identical within a mode; across modes, accept differing commits only when a documented argument (e.g. `--src-diff-clean`, with the zero-diff command output of `src`, `scripts/run_experiment.py` and `pyproject.toml` against `3323bfb`, supplied by Luke) is given; otherwise fail closed.
2. **Directory name and configuration slug (§2)**: Directory name must match `manifest.json` `run_id` and the canonical strategy/config slug derived from `strategy_config.json`; mismatch fails.
3. **Duplicate keys and failure accounting (§2)**: Confirmed from `harness.py` that successful keys are skipped on resume; a duplicate trial key whose earlier record is a success fails validation as corrupt. Failed-then-succeeded keys are listed separately from still-failed keys, and Table T3 reports both counts.
```

### 8.2 Decision [D-83] Record
Appended to `docs/decisions/decision-log.md`:
- Records gap closures in `validate_runs.py` (commit gate with `--src-diff-clean`, directory slug and run_id validation, duplicate key validity and failure partition, zero-trial resume accounting, `--hashes` comparison, and summary integer parsing).
- Records new SHA256 of `docs/context/analysis-plan.md`: `981136e97d86d1a765aaa71c318d170d3644c4f6eec938743710162730cf8bf7` (updating `78f87738...` from `[D-82]`).
- Contains no test counts.

---

## 9. Self-Checks

Grepped git diff across all modified and untracked files:
- Grep for `file:///`: **0 occurrences**.
- Grep for `<agent>`: **0 occurrences**.
- Grep for `FILL`: **0 occurrences**.

---

## 10. File Checksums and Line Counts

Computed after all edits:

| File | SHA256 Checksum | Line Count (`wc -l`) |
|---|---|---|
| `docs/context/analysis-plan.md` | `981136e97d86d1a765aaa71c318d170d3644c4f6eec938743710162730cf8bf7` | 112 |
| `docs/decisions/decision-log.md` | `c5244c2c25fcb8f57af1d8de689373e15618e42ff8d70fb7434faed700fcc965` | 704 |
| `scripts/analysis/validate_runs.py` | `d93597eb3bba7b11b7a7b7cfee775067667d63880a5cc7eae7c4a14b01b2d11d` | 965 |
| `tests/test_analysis_validate_runs.py` | `a85fbb5b1397d18109ececea1cf9b8e88e879b20824c6c473e2f83230fc4b145` | 838 |
| `docs/reports/ANALYSIS-001-F-gemini-report.md` | `59e890b40a9e706262bda8f321e2113c371057cc9406a3b25d4290b88be258ab` (post-edit) | 469 |

