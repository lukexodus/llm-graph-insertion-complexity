# ANALYSIS-001-G: Independent Review of ANALYSIS-001-F (Validator Fix)

## 1. Independence Certification and Identification

- **Task ID**: `ANALYSIS-001-G`
- **Agent Name**: `gemini`
- **Session ID**: `c143398c-85ce-4b37-b9ae-1f4bc1a9283d`
- **Model Label**: `Gemini 3.8 Flash`
- **Independence Certification**: Confirmed independent. This session is **NOT** any of the excluded sessions:
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`
  - `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
  - `f4b13de1-a057-445e-a788-0523b774b94d` (ANALYSIS-001 author session)
  - `562e3bc6-c12a-4372-85af-70eb9ecebfc7` (ANALYSIS-001-R session)
  - `f339a846-e963-4b8f-a62e-4090862002e7`
  - `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2` (ANALYSIS-001-F author session)
  - The `DOC-011` session
  - Any session starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.
- **Dedicated Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-001-G`
- **Worktree Branch**: `task/ANALYSIS-001-G`
- **Base Commit**: `ad81414138e6c7802cf3e45a5d8a17ac833beb32` (`ad81414`, verified clean master)

---

## 2. Setup and Worktree Status (Dataset-Related Failures Report)

### 2.1 Dedicated Worktree Verification
The review was executed from a freshly provisioned git worktree branching from master at `ad81414`:
```bash
git worktree add ../llm-graph-insertion-complexity-ANALYSIS-001-G -b task/ANALYSIS-001-G
```
Git commit status verified at `ad81414` (`docs: add ANALYSIS-001-F gemini verification and execution report`).

### 2.2 Dataset-Related Test Failures in New Worktrees
As expected in any git worktree created without cloning untracked local data directories, the worktree lacks the untracked/gitignored directory `repositories/dataset/EKG-Dataset`.

When running the full test suite (`pytest`) in this worktree:
- **Test execution summary**: `560 passed, 61 failed, 3 errors, 34 skipped in 149.53s`.
- **Root-cause audit of all 61 failures and 3 errors**:
  Every single failure was caused exclusively by the missing dataset files:
  `FileNotFoundError: Dataset root directory does not exist: .../repositories/dataset/EKG-Dataset`.
  These failures occur in `test_generate_name_pool.py`, `test_name_pool_supervisor.py`, `test_null_strategy.py`, and `test_run_experiment_cli.py` (which attempt to load the real gold-standard EKG corpora).
- **Validator test suite isolation**:
  The validator suite (`pytest tests/test_analysis_validate_runs.py`) has **zero** dependency on `repositories/` or external data; all 27 tests construct hermetic synthetic fixtures in `tmp_path`.
  **Result**: `27 passed in 5.66s` (100% pass rate).

---

## 3. Scope & Code Analysis: Validator Verification

### 3.1 `--hashes` Parsing and Missing/Extra/Malformed Line Handling
- **Parsing Implementation** (`scripts/analysis/validate_runs.py:118-135`):
  `parse_hashes_file` reads a `sha256sum`-format file:
  - Lines are stripped; empty lines and lines starting with `#` are skipped (`lines 123-125`).
  - Lines are split on the first whitespace token: `parts = line.split(maxsplit=1)` (`line 126`).
  - If `len(parts) == 2`, the hash and path are parsed: `sha, filepath_str = parts[0], parts[1].lstrip("*").strip()` (`line 128`).
  - Multi-part suffixes are stored in the lookup dict (`filepath_str`, `<run_dir>/<file>`, and `results/<run_dir>/<file>`) (`lines 129-134`).
- **Validation Execution** (`scripts/analysis/validate_runs.py:431-458`):
  `validate_single_run` checks each of the 4 required files (`manifest.json`, `strategy_config.json`, `raw.jsonl`, `summary.csv`).
- **Behavior on specific line variants**:
  1. **Missing lines**: If a required artifact is missing from the hash list, `matched_hash` is `None` (`line 444`), appending:
     `Missing expected hash entry for '<run_dir>/<file>' in hashes file` (`line 450`). Validation fails closed.
  2. **Extra lines**: Extra lines in the hash file (e.g. referencing other directories or unrelated files) are parsed into `hashes` in `parse_hashes_file`, but `validate_single_run` only queries the 4 required artifacts for the directory under evaluation. Extra lines are **silently ignored** (see Gaps Ranked by Risk).
  3. **Malformed lines**:
     - Lines with only one token (no whitespace delimiter) have `len(parts) != 2` and are **silently skipped** (`line 127`). If the skipped line was intended for a required artifact, validation fails closed downstream with `Missing expected hash entry`.
     - Lines with malformed SHA strings (e.g. wrong character count or non-hex characters) are accepted by `parse_hashes_file`, but fail closed in `line 454` with `File SHA256 mismatch`.

### 3.2 Commit Gate
- **Manifest Commit Integrity** (`scripts/analysis/validate_runs.py:466-470`):
  Checks that `"git_commit"` exists, is a string, and is non-empty. Otherwise appends `Manifest missing or invalid 'git_commit'` and records failure.
- **Intra-Mode Commit Uniformity** (`scripts/analysis/validate_runs.py:803-807, 844-854`):
  Commits are grouped by mode: `mode_commits.setdefault(m, set()).add(commit)`.
  If more than one distinct commit is found within any single mode (`len(commits) > 1`), validation unconditionally fails:
  `Intra-mode git_commit mismatch within mode '<mode>': found multiple commits ...`.
- **Cross-Mode Commit Gate & `--src-diff-clean`** (`scripts/analysis/validate_runs.py:856-867`):
  If the union of commits across different modes contains more than one commit, validation fails closed *unless* the `--src-diff-clean` flag was passed:
  `Cross-mode git_commit mismatch: commits differ across modes ... Must pass --src-diff-clean to accept differing commits across modes.`
  Passing `--src-diff-clean` explicitly accepts known documentation/non-source commit divergences across modes.

### 3.3 Directory and Run ID Checks
- **Canonical Slug Derivation** (`scripts/analysis/validate_runs.py:138-183`):
  `build_strategy_slug` encodes strategy parameters deterministically:
  - `embedding_threshold`: `theta<theta>`
  - `ann_retrieval`: `k<k>_ef<ef_search>`
  - `bounded_bucket`: `smin<s_min>_smax<s_max>_nb<n_bits>`
  - `brute_force`: `""` (empty slug)
  - Non-default seed: appends `_seed<seed>` if `seed != 42`.
  `derive_expected_run_id` prepends the mode prefix (`accuracy` or `sweep`).
- **Enforcement of Three-Way Agreement** (`scripts/analysis/validate_runs.py:491-496, 522-536`):
  1. `run_dir.name == manifest["run_id"]`: Directory name must match `manifest.json:run_id` (`line 493`).
  2. `run_dir.name == expected_slug`: Directory name must match the canonical strategy/config slug (`line 526`).
  3. `manifest["run_id"] == expected_slug`: Manifest run ID must match the canonical strategy/config slug (`line 530`).
  Any swap, mismatch, or manual rename triggers an immediate error.

### 3.4 Duplicate-Key Rule and Failed-then-Succeeded Partition
- **Duplicate-Key Rule** (`scripts/analysis/validate_runs.py:255-273, 579-589`):
  `parse_raw_jsonl` records chronological trial occurrences per key into `key_history`.
  In `lines 581-588`, if a key appears more than once (`len(history) > 1`), all preceding executions (`history[:-1]`) are verified:
  ```python
  if prev_rec.get("status") == "success":
      errors.append(
          f"Invalid duplicate trial key '{k}': earlier record at index {idx_prev} "
          f"has status 'success' (harness skips successful keys on resume)"
      )
  ```
  This guarantees that duplicate successful executions (which the harness `_load_existing_keys` skips upon resume) are rejected fail-closed as corruption.
- **Partitioning of Failed-then-Succeeded vs Still-Failed Keys** (`scripts/analysis/validate_runs.py:590-605`):
  For each key in `key_history`:
  - If any attempt had `status in ("failed", "error")` and the latest status is `"success"`, the key is classified into `failed_then_succeeded_keys`.
  - If the latest status is not `"success"`, the key is classified into `still_failed_keys`.
  - Runs with legitimate retries/resumes are flagged `resumed = True` and displayed as `PASS (resumed)` in CLI and Table T3 (`lines 876, 938`), while still-failed keys increment `still_failed_count` and appear in the report inventory.

### 3.5 Per-Config Call Bounds: Sweep (12 Configs & 60 Keys) and Accuracy (12 Configs)
- **Implementation** (`scripts/analysis/validate_runs.py:185-242`, `get_planned_call_bound`):
  Bounds map directly to the authoritative D-68 run plan table in `scripts/README.md:210-224`.
- **Sweep Call Bounds (All 12 Sweep Configs, 60 Trials across $\{50, 100, 200, 500, 1000, 2000\}$)**:
  1. `ann_retrieval` ($k=10, \text{ef}=128$): **600** ($60 \times 10$)
  2. `ann_retrieval` ($k=5, \text{ef}=128$): **300** ($60 \times 5$)
  3. `ann_retrieval` ($k=20, \text{ef}=128$): **1,200** ($60 \times 20$)
  4. `ann_retrieval` ($k=10, \text{ef}=64$): **600** ($60 \times 10$)
  5. `ann_retrieval` ($k=10, \text{ef}=256$): **600** ($60 \times 10$)
  6. `bounded_bucket` ($s_{\min}=5, s_{\max}=10, nb=12$): **600** ($60 \times 10$)
  7. `bounded_bucket` ($s_{\min}=2, s_{\max}=5, nb=12$): **300** ($60 \times 5$)
  8. `bounded_bucket` ($s_{\min}=10, s_{\max}=20, nb=12$): **1,200** ($60 \times 20$)
  9. `embedding_threshold` ($\theta=0.6$): **38,500** ($10 \times \sum \{50, 100, 200, 500, 1000, 2000\} = 10 \times 3,850$)
  10. `embedding_threshold` ($\theta=0.5$): **38,500** ($10 \times 3,850$)
  11. `embedding_threshold` ($\theta=0.4$): **38,500** ($10 \times 3,850$)
  12. `brute_force` (primary): **38,500** ($10 \times 3,850$)
  **Group pattern**: `600/300/1,200/600/600; 600/300/1,200; 38,500 x4`. Total sweep calls ceiling = **159,400**.
- **Accuracy Bounds Verification (All 12 Accuracy Configs, 59 Trials)**:
  The 12 accuracy bounds are **100% verified and correct**:
  - $k=10$ / $s_{\max}=10$ (4 configs: S3 primary, S3 ef64, S3 ef256, S4 primary): $59 \times 10 =$ **590** each.
  - $k=5$ / $s_{\max}=5$ (2 configs: S3 k5, S4 smin2_smax5): $59 \times 5 =$ **295** each.
  - $k=20$ / $s_{\max}=20$ (2 configs: S3 k20, S4 smin10_smax20): $59 \times 20 =$ **1,180** each.
  - Uncapped / brute force (4 configs: S1 brute_force, S2 $\theta \in \{0.6, 0.5, 0.4\}$): **5,012** each (theoretical candidate ceiling across all 59 gold-standard trials).
  - Total accuracy calls ceiling: $4 \times 590 + 2 \times 295 + 2 \times 1,180 + 4 \times 5,012 = 25,358$. Matches `scripts/README.md:224`.

### 3.6 Fail-Closed Behaviour
Every validation stage in `validate_runs.py` appends descriptive errors to an `errors` list and marks the run failed:
- Missing mandatory artifacts (`lines 418-422`) -> fails immediately.
- Malformed JSON in manifest or sidecar (`lines 460-464, 499-503`) -> fails immediately.
- Corrupted lines in `raw.jsonl` (`lines 573-577`) -> fails immediately.
- Boolean strictness on `git_dirty` (`manifest.get("git_dirty") is not False`, `line 471`) -> rejects `True`, `None`, or string `"False"`.
- Missing required libraries in manifest (`lines 485-488`) -> fails closed.
- Thread pins for embedding strategies (`cpu_threads != 1` or `torch_threads != 1`, `lines 549-552`) -> fails closed.
- Embedder presence on non-embedding strategy (`brute_force`, `lines 567-571`) -> fails closed.
- Mismatched trial counts against expected per-group specification (`lines 640-656`) -> fails closed.
- Realised calls exceeding planned bound (`lines 668-672`) -> fails closed.
- Any integer column in `summary.csv` containing invalid string/float (`lines 691-693, 708-710`) -> catches `ValueError` and fails closed.
- Intra-mode or unapproved cross-mode commit discrepancies (`lines 844-867`) -> fails closed.
- Main exit code (`line 961`): returns `1` on any failure across any evaluated run; returns `0` strictly if every run passes all checks.

---

## 4. Executed Corruption Table

All 12 corruptions were executed against real accuracy run copies and synthetic sweep fixtures under `/tmp/corruption_matrix`. For every case, a pristine baseline control was executed first (confirming `PASS`, exit code 0), followed by the corrupted mutant (confirming `FAIL`, exit code 1, and exact failing lines).

| # | Corruption Case | Fixture Type | Control Command & Result | Mutant Command & Result | Failing Lines / Validator Errors |
|---|---|---|---|---|---|
| 1 | **Tamper one raw.jsonl byte against --hashes** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_01/accuracy_ann_retrieval_k10_ef128 --hashes /tmp/corruption_matrix/case_01/sha256.txt`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_01/accuracy_ann_retrieval_k10_ef128 --hashes /tmp/corruption_matrix/case_01/sha256.txt`<br>**Code 1 (FAIL)** | `-> ERROR: File SHA256 mismatch for 'accuracy_ann_retrieval_k10_ef128/raw.jsonl': computed 'e63563...' != expected '203a91...'`<br>`-> ERROR: Invalid JSON/format in raw.jsonl: Expecting ',' delimiter` |
| 2 | **Delete one line from the hash list** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_02/accuracy_ann_retrieval_k10_ef128 --hashes /tmp/corruption_matrix/case_02/sha256.txt`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_02/accuracy_ann_retrieval_k10_ef128 --hashes /tmp/corruption_matrix/case_02/sha256.txt`<br>**Code 1 (FAIL)** | `-> ERROR: Missing expected hash entry for 'accuracy_ann_retrieval_k10_ef128/manifest.json' in hashes file` |
| 3 | **Rename a directory** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_03/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_03/accuracy_ann_retrieval_k10_ef128_renamed`<br>**Code 1 (FAIL)** | `-> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128_renamed' does not match manifest.json run_id 'accuracy_ann_retrieval_k10_ef128'`<br>`-> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128_renamed' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'` |
| 4 | **Change a manifest run_id** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_04/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_04/accuracy_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Directory name 'accuracy_ann_retrieval_k10_ef128' does not match manifest.json run_id 'accuracy_ann_retrieval_k10_ef128_tampered'`<br>`-> ERROR: Manifest run_id 'accuracy_ann_retrieval_k10_ef128_tampered' does not match expected strategy/config slug 'accuracy_ann_retrieval_k10_ef128'` |
| 5 | **Drop one sweep key (59 keys instead of 60)** | Synthetic sweep fixture (`sweep_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_05/sweep_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_05/sweep_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Unique trial count mismatch: raw.jsonl has 59 unique keys, expected 60 for mode 'sweep'`<br>`-> ERROR: Per-group trial count mismatch for '50': got 9, expected 10`<br>`-> ERROR: Trial count disagreement between summary.csv (60) and raw.jsonl unique keys (59)`<br>`-> ERROR: num_trials mismatch for group '50': summary=10 vs raw=9`<br>`-> ERROR: num_success mismatch for group '50': summary=10 vs raw=9`<br>`-> ERROR: llm_calls_sum mismatch for group '50': summary=10 vs raw=9`<br>`-> ERROR: total_s_mean mismatch for group '50': summary=0.7250 vs raw=0.7500`<br>`-> ERROR: total_s_median mismatch for group '50': summary=0.7250 vs raw=0.7500` |
| 6 | **Add a 61st key** | Synthetic sweep fixture (`sweep_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_06/sweep_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_06/sweep_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Unique trial count mismatch: raw.jsonl has 61 unique keys, expected 60 for mode 'sweep'`<br>`-> ERROR: Per-group trial count mismatch for '50': got 11, expected 10`<br>`-> ERROR: Trial count disagreement between summary.csv (60) and raw.jsonl unique keys (61)`<br>`-> ERROR: num_trials mismatch for group '50': summary=10 vs raw=11`<br>`-> ERROR: num_success mismatch for group '50': summary=10 vs raw=11`<br>`-> ERROR: llm_calls_sum mismatch for group '50': summary=10 vs raw=11`<br>`-> ERROR: total_s_mean mismatch for group '50': summary=0.7250 vs raw=0.7045`<br>`-> ERROR: total_s_median mismatch for group '50': summary=0.7250 vs raw=0.7000` |
| 7 | **Set a bound-exceeding call count (calls > 600)** | Synthetic sweep fixture (`sweep_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_07/sweep_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_07/sweep_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Realised LLM calls 601 exceeds planned upper bound 600 for strategy 'ann_retrieval'`<br>`-> ERROR: llm_calls_sum mismatch for group '50': summary=10 vs raw=551`<br>`-> ERROR: llm_calls_mean mismatch for group '50': summary=1.0000 vs raw=55.1000` |
| 8 | **Change cpu_threads to 4** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_08/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_08/accuracy_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Sidecar cpu_threads != 1: got 4` |
| 9 | **Set git_dirty true** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_09/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_09/accuracy_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Manifest git_dirty is not False: True` |
| 10 | **Mismatch libraries (cross-run library version mismatch)** | Real accuracy copies (`accuracy_ann_retrieval_k10_ef128` & `k5_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_10`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_10`<br>**Code 1 (FAIL)** | `-> ERROR: Cross-run libraries block mismatch between this run and baseline run` |
| 11 | **Truncate raw.jsonl (corrupted trailing line)** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_11/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_11/accuracy_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Invalid JSON/format in raw.jsonl: Expecting ':' delimiter: line 1 column 1303 (char 1302)` |
| 12 | **Make an earlier record for a key a success (duplicate success record)** | Real accuracy copy (`accuracy_ann_retrieval_k10_ef128`) | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_12/accuracy_ann_retrieval_k10_ef128`<br>**Code 0 (PASS)** | `python3 scripts/analysis/validate_runs.py /tmp/corruption_matrix/case_12/accuracy_ann_retrieval_k10_ef128`<br>**Code 1 (FAIL)** | `-> ERROR: Invalid duplicate trial key 'accuracy:ann_retrieval:DSA_gold_standard_MEKG:asymptotic_complexity:r0': earlier record at index 0 has status 'success' (harness skips successful keys on resume)` |

---

## 5. Remaining Gaps Ranked by Risk

1. **Gap 1: `--hashes` performs no reverse-lookup or orphan check (Medium Risk)**
   - *Detail*: In `validate_single_run` (`lines 431-458`), the validator loops exclusively over the 4 required files (`manifest.json`, `strategy_config.json`, `raw.jsonl`, `summary.csv`) and checks their presence in `expected_hashes`.
   - *Risk*: If the hashes file contains extra, orphaned, or misnamed lines, or if extra extraneous files exist in the run directory, `--hashes` does not raise an error.
   - *Mitigation*: The composite directory hash (`dir_sha256`, `lines 109-115`) hashes all files in the directory sorted by filename, ensuring that any extraneous file in the directory changes the directory hash.

2. **Gap 2: `--src-diff-clean` relies on operator assertion rather than automated git diff (Low/Medium Risk)**
   - *Detail*: In `validate_all_runs` (`lines 856-867`), cross-mode commit differences are accepted if `args.src_diff_clean` is `True`. The validator does not invoke `git diff 3323bfb..commit -- src/ scripts/run_experiment.py pyproject.toml` programmatically.
   - *Risk*: An operator could pass `--src-diff-clean` inadvertently on runs with actual algorithmic code drift.
   - *Mitigation*: In the authoritative protocol, Luke and the APC verify git diffs offline before applying acceptance flags.

3. **Gap 3: `parse_hashes_file` silently ignores malformed single-token lines (Low Risk)**
   - *Detail*: In `validate_runs.py:126-128`, if a line in the hash file cannot be split into two tokens (`len(parts) != 2`), it is silently dropped without syntax error or warning.
   - *Risk*: If a required file's hash line lost its space due to editing corruption, the error emitted downstream is "Missing expected hash entry" rather than a syntax parse error on the hashes file itself.
   - *Mitigation*: The downstream missing hash error still fails closed and prevents validation from passing.

4. **Gap 4: `accuracy_dsa` uses the 59-trial bound rather than 29-trial bound (Low Risk)**
   - *Detail*: In `get_planned_call_bound` (`lines 190-215`), `mode in ("accuracy", "accuracy_dsa")` returns 590 calls for $k=10$ rather than $29 \times 10 = 290$.
   - *Risk*: For a standalone legacy/pilot 29-trial DSA run, the planned bound ceiling is looser than optimal.
   - *Mitigation*: Affects legacy test fixtures only; all 12 production accuracy runs are 59 trials ($29 + 30$).

---

## 6. Test Counts and Final Assessment

- **Validator Test Suite (`tests/test_analysis_validate_runs.py`)**:
  - `27 passed` in 5.66s.
  - Covers all baseline fixtures, synthetic sweep fixtures, corruption matrices, resume logic, thread pins, float/integer validation, slug generation, and Table T3 generation.
- **Full Test Suite (`pytest`)**:
  - `560 passed, 61 failed, 3 errors, 34 skipped in 149.53s`.
  - All 61 failures and 3 errors are dataset-related (`repositories/dataset/EKG-Dataset` absent in worktree); zero validator regressions.
- **Verdict**:
  TASK `ANALYSIS-001-F` is **APPROVED**. The validator is robust, fails closed across all edge cases, enforces exact three-way slug/directory/run_id agreement, enforces the D-68 planned call bounds for all 12 sweep and 12 accuracy configurations, separates failed-then-succeeded resume retries, and verifies machine-written file hashes.
