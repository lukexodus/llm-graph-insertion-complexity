# ANALYSIS-002-F Task Report: Phase 4 Empirical Analysis Pipeline Review Remediation

## Executive Summary & Independence Certification

- **Task ID**: `ANALYSIS-002-F`
- **Agent Lineage**: `gemini`
- **Model Label**: `Gemini 3.8 Flash (Medium)`
- **Session ID**: `bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e`
- **Base Commit**: `17ed1f833b07ce9356fb7ed7281f68b39336c376` (`17ed1f8`)
- **Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002-F` on branch `task/ANALYSIS-002-F`
- **Independence Certification**: The executing agent explicitly certifies that it is independent from the excluded sessions: `1b3efbca-895e-4b87-bbbd-80fb31a3230d`, `512aecca-d185-438b-b8e7-d6dba3b507fb`, `098dcdd4-c444-4fcd-af8f-1b2054b31802`, `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`, `f4b13de1-a057-445e-a788-0523b774b94d`, `562e3bc6-c12a-4372-85af-70eb9ecebfc7`, `f339a846-e963-4b8f-a62e-4090862002e7`, `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2`, `c143398c-85ce-4b37-b9ae-1f4bc1a9283d`, `26156499-0953-4f34-b42f-1cf073f8d16e`, the DOC-011 session, and all sessions with prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`.

### Overview of Work Completed
This task resolves all defects and recommendations identified in the independent review of the Phase 4 empirical analysis pipeline:
1. **Validation Gate Enforcement**: Completely removed `--skip-gate`. The pipeline runs the independent validator `validate_runs.py` first and fails closed (exit code 1, writes nothing) on validation failure. Output directories are created only after the gate passes. Writes provenance record `RUN_INFO.txt`.
2. **Verbatim Table T3 Inventory**: Writes validator `t3_csv` output verbatim with all 18 validator fieldnames. Removed duplicate single-run validation and ad-hoc recomputations in `tables.py`.
3. **Table & Figure Robustness**: Implemented strict accessor `_require_col` across `tables.py`, raising `KeyError` naming run and column on missing fields. Corrected `n_with_retries` in T1 to source only from `summary.csv`. Set random baseline recall to NaN for strategies without shortlist caps ($k$ or $s_{max}$). Added 95% bootstrap CIs for `shortlist_s` and `decide_s` in Table T2.
4. **Figure F3 Caps**: Read $k$ and $s_{max}$ strictly from primary S3/S4 `strategy_config.json` sidecars, labeled "cap (k / s_max)".
5. **Rule R1 (Zero-Mean Rule)**: Log-log fits with any size having mean $\le 0$ or non-finite are undefined (NaN slope, intercept, $R^2$; no D2 category; category string "undefined (zero mean at n=...)"). Completely eliminated arbitrary `1e-12` clamp. Emitted exploratory row when $\ge 3$ sizes have positive mean. In bootstrap resamples, dropped zero-mean resamples and reported `n_boot_used`.
6. **Rule R2 (Mechanical Pareto Dominance)**: $|\Delta F_1| < 0.025$ yields "not distinguishable (F1 within 0.025)" regardless of calls. $\ge 0.025$ assigns dominance if higher F1 and $\le$ calls; otherwise "trade-off". Emitted labels to `F6_dominance.csv` / `.md` and rendered in a text box on Figure F6.
7. **Rule R3 (Post-Hoc Timing Exclusion)**: Excluded trials with `retries > 0` and the single trial `sweep:brute_force:2000:t9`. Added column `clean_exclusion_rule` with verbatim text: `"retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)"`.
8. **Decision Log**: Appended `[D-86]` in `docs/decisions/decision-log.md` copying the exact structural convention of `[D-83]` with no test counts.

---

## Implementation Details

### 1. `scripts/analysis/run_analysis.py`
- Deleted the `--skip-gate` CLI flag and all associated bypass logic.
- Implemented gate-first execution: calls `validate_all_runs(results_dir, src_diff_clean=args.src_diff_clean, hashes_path=hashes_path)`. On failure, prints failing run IDs, exits with code 1, and creates no output directories.
- Output directories (`tables/`, `figures/`) are created only after the validation gate passes.
- Writes `RUN_INFO.txt` capturing:
  - Invocation `argv`
  - Canonical `results_dir`
  - Git commit hash via `git rev-parse HEAD`
  - SHA256 hashes of `validate_runs.py` and each pipeline module (`run_analysis.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`)
  - External hashes file path and SHA256 (or "NOT SUPPLIED")
  - `--src-diff-clean` flag value
  - Overall gate status (`PASS`)
- Passes `t3_csv` string directly to `tables.generate_t3_inventory_table`.
- Loads primary S3 (`ann_retrieval`) and S4 (`bounded_bucket`) `strategy_config.json` sidecars to extract $k$ and $s_{max}$ caps, passing them strictly to `figures.generate_f3_premise_check_figure`.

### 2. `scripts/analysis/tables.py`
- Implemented `_require_col(record, col_name, run_name)` which raises `KeyError(f"Run \"{run_name}\" missing required column \"{col_name}\"")`. Replaced all permissive `.get(col, 0.0)` / `.get(col, "")` calls on required fields.
- Removed `validate_single_run` import. `generate_t3_inventory_table` now parses the validator-provided `t3_csv` content and writes it verbatim to `tables/T3_run_inventory.csv`, ensuring all 18 validator fieldnames are preserved identically.
- Removed `retry_counts` misuse in `generate_t1_accuracy_table`; `n_with_retries` is read strictly from `summary.csv`.
- Evaluated random baseline recall as NaN for strategies without $k$ or $s_{max}$ (`brute_force`, `embedding_threshold`).
- Added 95% percentile bootstrap CIs for `shortlist_s` and `decide_s` in Table T2 (`shortlist_s_ci_mean_low`, `shortlist_s_ci_mean_high`, `decide_s_ci_mean_low`, `decide_s_ci_mean_high`).
- Implemented Rule R3: `clean_successes` excludes `retries > 0` and trial key `sweep:brute_force:2000:t9`. Added `clean_exclusion_rule` stating: `"retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)"`.
- Implemented Rule R1 in `_fit_metric_slopes`: emits `min_trials_per_size` and `n_boot_used`. If undefined due to zero-mean sizes but at least 3 sizes have positive means, emits an exploratory row labeled `"exploratory (positive-mean sizes only)"`.
- Updated `write_csv` and `export_markdown_table` to always write table headers even when row lists are empty, ensuring predictable schema emission.

### 3. `scripts/analysis/stats.py`
- Implemented Rule R1:
  - Removed `1e-12` clamp completely from `fit_log_log_slope` and `bootstrap_slope_ci`.
  - Non-positive or non-finite empirical size means return `(NaN, NaN, NaN)` from `fit_log_log_slope`.
  - In `bootstrap_slope_ci`, empirical non-positive/non-finite means return category `"undefined (zero mean at n=...)"` and `n_boot_used = 0`.
  - Bootstrap resamples containing any non-positive mean size are dropped; returns valid percentiles over remaining resamples along with `n_boot_used`.
- Implemented Rule R2:
  - `evaluate_dominance`: when `abs(f1_diff) < 0.025`, returns `"not distinguishable (F1 within 0.025)"` regardless of calls.
  - At or above 0.025: A dominates B if `f1_a > f1_b and calls_a <= calls_b`; B dominates A if `f1_b > f1_a and calls_b <= calls_a`; otherwise `"trade-off"`.

### 4. `scripts/analysis/figures.py`
- Implemented Rule R2 in Figure F6: writes pairwise dominance labels to `figures/F6_dominance.csv` and `figures/F6_dominance.md` without dummy 0.0 rows in the plotting CSV; renders dominance summary directly in a text box on Figure F6.
- In Figure F3: accepts `s3_k` and `s4_smax` parameters from `run_analysis.py`, asserting their presence; labels dashed cap lines as `"cap (k / s_max)"` instead of `"Theoretical Bound"`.
- Preserved F1 and F2 axes unchanged (no log-y transformations).

### 5. `tests/test_analysis_pipeline.py`
- Completely removed all hardcoded `/home/` paths.
- Sourced real-data parity test path from `PHASE4_RESULTS_DIR` environment variable, skipping with explicit message if unset.
- Implemented comprehensive test suite covering:
  - R1 zero-mean undefined behaviour and exploratory row generation
  - R2 dominance classification including exact 0.025 boundary condition
  - R3 post-hoc timing exclusion of retries > 0 and trial t9
  - Strict accessor failure on missing columns
  - T3 verbatim 18 fieldnames header and trial count validation
  - Validation gate failure aborting and writing nothing
  - Validation gate success and `RUN_INFO.txt` generation
  - End-to-end execution without any `--skip-gate` flag
  - Source grep assertion verifying absence of forbidden patterns (`skip-gate`, `/home/`, `1e-12`) in `scripts/analysis/*.py`.

### 6. `docs/decisions/decision-log.md`
- Appended `[D-86]` strictly copying the structure of `[D-83]`.
- Recorded only required corrections to D-85, T3 defects, Rules R1–R3, and removal of `--skip-gate`. Contains zero test counts.

---

## Verification & Test Evidence

### Baseline Commit Check
Before executing real-data analysis, verified zero diff against baseline `3323bfb` for core execution files:
```bash
git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml; echo $?
```
Output:
```
0
```

### Real Run Execution
Executed full empirical analysis pipeline against the real experimental dataset (`results/`), writing outputs outside the repository:
```bash
python3 scripts/analysis/run_analysis.py \
  --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results \
  --output-dir /tmp/phase4_analysis_output_002f \
  --src-diff-clean \
  --hashes /home/lukexodus/run-logs/final-results-hashes.txt
```

Verbatim Console Output:
```
================================================================================
PHASE 4 EMPIRICAL ANALYSIS PIPELINE
Results Directory: /home/lukexodus/projects/llm-graph-insertion-complexity/results
Output Directory:  /tmp/phase4_analysis_output_002f
================================================================================

>>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...

[OK] Validation gate passed 100%. Proceeding with analysis.

Discovered: 24 total runs (12 accuracy, 12 sweep)

>>> STEP 2: Generating Table T3 (Run Inventory)...
    Saved: /tmp/phase4_analysis_output_002f/tables/T3_run_inventory.csv and .md (24 entries)

>>> STEP 3: Generating Accuracy Tables (T1, T4)...
    Saved: /tmp/phase4_analysis_output_002f/tables/T1_accuracy_benchmark.csv and .md (24 rows)
    Saved: /tmp/phase4_analysis_output_002f/tables/T4_sensitivity_metrics.csv and .md (24 rows)

>>> STEP 4: Generating Accuracy Figures (F4, F5, F6)...
    Saved: /tmp/phase4_analysis_output_002f/figures/F4_accuracy_by_strategy.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output_002f/figures/F5_sensitivity_panels.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output_002f/figures/F6_cost_vs_accuracy_dominance.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output_002f/figures/F6_dominance.csv and .md

>>> STEP 5: Generating Sweep Cost Table (T2) and Slope Fits...
    Saved: /tmp/phase4_analysis_output_002f/tables/T2_sweep_cost_summary.csv and .md (72 rows)
    Saved: /tmp/phase4_analysis_output_002f/tables/T2_slope_fits.csv and .md (38 fits)

>>> STEP 6: Generating Sweep Figures (F1, F2, F3)...
    Saved: /tmp/phase4_analysis_output_002f/figures/F1_calls_scaling.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output_002f/figures/F2_wallclock_scaling.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output_002f/figures/F3_premise_check.pdf (.png, .csv)

================================================================================
PHASE 4 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY (100% PASS).
================================================================================
```

### Verified `RUN_INFO.txt`
```
argv: scripts/analysis/run_analysis.py --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results --output-dir /tmp/phase4_analysis_output_002f --src-diff-clean --hashes /home/lukexodus/run-logs/final-results-hashes.txt
results_dir: /home/lukexodus/projects/llm-graph-insertion-complexity/results
git_commit: 17ed1f833b07ce9356fb7ed7281f68b39336c376
pipeline_modules_sha256:
  validate_runs.py: d93597eb3bba7b11b7a7b7cfee775067667d63880a5cc7eae7c4a14b01b2d11d
  run_analysis.py: 6603aa32a44c2ce8900d287f2dcb6248ce18ad2ffea743f7d7a1e53087a67cae
  tables.py: 39a664ec89fccd3138440771021ed1b20115b582f1f88a4c92ec48c3958e22b2
  figures.py: 47b04a9434e9012a6225049ad59346c1adc22935d2c348a5c46160ef75c3250a
  stats.py: c8ddc4bbd5603251522e7af8a08538ac49d03152ec8ca2919354403f172efacb
  bootstrap.py: 9451e8a1c586bc2c90797f92bbb30c1da3393fdf7feb5d3ce73271c0aaaac44c
  style.py: e9f4539d20ddb62ea11b4a0bfa4bae61f1dc6059c2072eacc80197831e149e26
hashes_file: /home/lukexodus/run-logs/final-results-hashes.txt (sha256: a4f7109b792ae18031a705abddaf14851580d2c6a49d56ffbe2cd20263c10ce4)
src_diff_clean: True
overall_gate_status: PASS
```

### Test Suite Execution
- **Unit & Integration Suite (Standard)**:
  - Command: `pytest -v tests/test_analysis_pipeline.py`
  - Result: 13 passed, 1 skipped (parity test skipped due to unset `PHASE4_RESULTS_DIR`), 0 failed.
- **Full Suite (with Real Data Parity Enabled)**:
  - Command: `PHASE4_RESULTS_DIR=/home/lukexodus/projects/llm-graph-insertion-complexity/results pytest -v tests/test_analysis_pipeline.py`
  - Result: 14 passed, 0 skipped, 0 failed.

### Mutation Testing Table
A passing baseline control was verified prior to mutation testing (13 passed, 1 skipped). All five required mutants were systematically executed and confirmed killed with verbatim failing assertions:

| Mutant ID | Description & Exact Code Modification | Test Command | Verbatim Failing Line | Status |
| --- | --- | --- | --- | --- |
| **M1** | `run_analysis.py`: ignore `overall_passed` (`if False and not overall_passed:`) | `pytest -v tests/test_analysis_pipeline.py -k test_gate_failure_aborts_and_writes_nothing` | `tests/test_analysis_pipeline.py:461: AssertionError: assert 0 == 1` | **KILLED** |
| **M2** | `stats.py`: restore `1e-12` clamp in `fit_log_log_slope` (`y_clamped = np.where(y_arr <= 0, 1e-12, y_arr)`) | `pytest -v tests/test_analysis_pipeline.py -k test_r1_zero_mean_undefined_and_all_positive` | `tests/test_analysis_pipeline.py:122: AssertionError: assert np.isnan(slope)` (received `9.253`) | **KILLED** |
| **M3** | `tables.py`: T3 reads `total_trials` instead of validator `trials` | `pytest -v tests/test_analysis_pipeline.py -k test_t3_header_and_trial_count` | `tests/test_analysis_pipeline.py:436: KeyError: "Run 'synthetic_run' missing required column 'total_trials'"` | **KILLED** |
| **M4** | `stats.py`: dominance back to `<=` with calls advantage in `evaluate_dominance` | `pytest -v tests/test_analysis_pipeline.py -k test_r2_dominance_including_boundary` | `tests/test_analysis_pipeline.py:172: AssertionError: assert 'A dominates B (calls advantage, F1 equivalent)' == 'not distinguishable (F1 within 0.025)'` | **KILLED** |
| **M5** | `tables.py`: drop `retries == 0` filter in `clean_successes` | `pytest -v tests/test_analysis_pipeline.py -k test_r3_post_hoc_sensitivity_exclusion` | `tests/test_analysis_pipeline.py:365: AssertionError: assert 9 == 8` | **KILLED** |

### File Hashes and Line Counts (After Last Edit)
```
sha256sum:
266302bf9d333753b84ff90e45c32d382dc794f6658eb88c01c5b28059609a2d  docs/decisions/decision-log.md
47b04a9434e9012a6225049ad59346c1adc22935d2c348a5c46160ef75c3250a  scripts/analysis/figures.py
6603aa32a44c2ce8900d287f2dcb6248ce18ad2ffea743f7d7a1e53087a67cae  scripts/analysis/run_analysis.py
c8ddc4bbd5603251522e7af8a08538ac49d03152ec8ca2919354403f172efacb  scripts/analysis/stats.py
39a664ec89fccd3138440771021ed1b20115b582f1f88a4c92ec48c3958e22b2  scripts/analysis/tables.py
0c82cc6a3a8dd1e54a79627b48e7533f1b9206ef512631db48c9234e8e70697c  tests/test_analysis_pipeline.py

wc -l:
   749 docs/decisions/decision-log.md
   550 scripts/analysis/figures.py
   284 scripts/analysis/run_analysis.py
   186 scripts/analysis/stats.py
   503 scripts/analysis/tables.py
   710 tests/test_analysis_pipeline.py
  2982 total
```

### Decision D-86 Grep Output
```bash
grep -n "\[D-86\]" docs/decisions/decision-log.md
```
Output:
```
720:**[D-86]** Corrections to D-85, Phase 4 analysis pipeline defect remediation, validation gate enforcement, Table T3 verbatim inventory, Rules R1–R3, and execution provenance (ANALYSIS-002-F):
```

### Source and Diff Grep Audits
Grep for forbidden patterns across `scripts/analysis/*.py`:
```bash
grep -rnE "file:///|<agent>|FILL|skip-gate|/home/|1e-12" scripts/analysis/*.py
```
Output:
```
ALL CLEAN (0 matches)
```

Grep of the unified git diff against master for forbidden literals:
- `file:///`: 0 matches
- `<agent>`: 0 matches
- `FILL`: 0 matches
- `skip-gate`: Only in removal hunks, D-86 text describing removal, and test docstrings/lists
- `/home/`: Only in removal hunk of hardcoded path and test docstrings/lists
- `1e-12`: Only in removal hunks of clamp and test docstrings/lists

---

## Verbatim Git Diff

### `git diff --stat master`
```
 docs/decisions/decision-log.md   |  31 +++
 scripts/analysis/figures.py      |  75 +++++--
 scripts/analysis/run_analysis.py | 146 +++++++++++---
 scripts/analysis/stats.py        | 123 ++++++++----
 scripts/analysis/tables.py       | 316 +++++++++++++++--------------
 tests/test_analysis_pipeline.py  | 423 ++++++++++++++++++++++++++++++++-------
 6 files changed, 797 insertions(+), 317 deletions(-)
```

### Unified Git Diff
```diff
diff --git c/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index fd7c5e3..e56cd82 100644
--- c/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -716,3 +716,34 @@ Reasoning: closes the validation gate blind spots identified in ANALYSIS-001-R r
   (b) Added dedicated timing sensitivity columns to Table T2 (`clean_total_s_mean_post_hoc_not_preregistered`, `clean_total_s_median_post_hoc_not_preregistered`, etc.) that explicitly exclude all trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9`, labelled "post-hoc, not pre-registered".
 (5) Test suite and parity verification: Implemented comprehensive unit, integration, and parity test suite (`tests/test_analysis_pipeline.py`, 9 tests passing). Verified exact numerical parity between pipeline outputs and validator recomputations (`validate_runs.py::recompute_metrics`) across all 12 accuracy configurations.
 Reasoning: completes, hardens, and wires the Phase 4 empirical analysis pipeline into the repository, enforcing the pre-registered Analysis Plan [D-79], Decisions D1–D6, and post-hoc retry sensitivity accounting without altering raw experiment outputs. Affects: `scripts/analysis/`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
+
+**[D-86]** Corrections to D-85, Phase 4 analysis pipeline defect remediation, validation gate enforcement, Table T3 verbatim inventory, Rules R1–R3, and execution provenance (ANALYSIS-002-F):
+(1) Corrections to [D-85] and ANALYSIS-002 report:
+  (a) In [D-85](3)(b), bootstrap confidence intervals were erroneously claimed to be generated for `shortlist_s` and `decide_s`, whereas the initial implementation only computed CIs for `llm_calls` and `total_s`; 95% bootstrap CIs for `shortlist_s` and `decide_s` are now computed and emitted in Table T2.
+  (b) An ephemeral test count was erroneously embedded in [D-85](5); decision log entries record enduring architecture, protocols, and data decisions, not transient suite sizes.
+  (c) The real-data parity test in `tests/test_analysis_pipeline.py` previously contained a hardcoded path; it now accepts the results directory from the `PHASE4_RESULTS_DIR` environment variable and skips cleanly when unset.
+  (d) The claim in the ANALYSIS-002 report that trial `sweep:brute_force:2000:t9` suffered a "transient header failure" was factually unsupported; trial t9 is excluded from post-hoc timing sensitivity strictly because it was executed inside the DeepSeek peak-hours window using `--allow-peak`.
+(2) Validation gate enforcement and removal of `--skip-gate`:
+  (a) Removed `--skip-gate` CLI flag entirely from `run_analysis.py`; the pipeline unconditionally enforces the independent validation gate before performing any analysis or creating output directories. On gate failure, failing runs are printed, the process exits with code 1, and no output files are written.
+  (b) Output directory writes `RUN_INFO.txt` recording invocation argv, results directory, git commit, sha256 hashes of `validate_runs.py` and all analysis modules, external hashes file path and its sha256, `--src-diff-clean` status, and overall validation gate status.
+(3) Table T3 run inventory verbatim emission:
+  (a) Table T3 writes the independent validator's `t3_csv` output verbatim to `tables/T3_run_inventory.csv` with the exact 18 fieldnames defined by `validate_runs.py`.
+  (b) Removed ad-hoc recomputations and calls to `validate_single_run` in `tables.py`; Markdown rendering parses the verbatim CSV.
+(4) Table and Figure robustness and strict accessors:
+  (a) Replaced permissive `.get(col, 0.0)` accessors on required fields with strict accessors raising `KeyError` naming the run directory and missing column.
+  (b) Removed `retry_counts` misuse in Table T1; `n_with_retries` is sourced strictly from `summary.csv`.
+  (c) Random baseline recall in Table T1 evaluates to NaN for strategies without a $k$ or $s_{\max}$ shortlist cap (`brute_force`, `embedding_threshold`).
+  (d) Figure F3 theoretical caps for Strategies 3 and 4 are read strictly from primary run `strategy_config.json` sidecars passed by `run_analysis.py`, failing closed if missing, with the line labeled "cap (k / s_max)".
+(5) Rule R1 (Zero-mean log-log slope fits):
+  (a) Any log-log OLS fit where any graph size has an empirical mean $\le 0$ or non-finite cost is mathematically undefined, yielding NaN for slope, intercept, and $R^2$, no D2 category assignment, and category string "undefined (zero mean at n=...)". The arbitrary $10^{-12}$ clamp is eliminated from all fitting and bootstrap code.
+  (b) If a fit is undefined due to zero-mean sizes but at least three sizes have positive means, an additional exploratory row is emitted labeled "exploratory (positive-mean sizes only)".
+  (c) Bootstrap resampling drops resamples containing any zero-mean size, records `n_boot_used`, and assigns NaN CIs if no valid resamples remain.
+  (d) Sizes with no trials are treated as undefined rather than padded with zero; Table T2b records `min_trials_per_size`.
+(6) Rule R2 (Mechanical Pareto dominance):
+  (a) When $|\Delta F_1| < 0.025$, the pair is classified as "not distinguishable (F1 within 0.025)" regardless of call difference.
+  (b) When $|\Delta F_1| \ge 0.025$, strategy A dominates B if $F_{1,A} > F_{1,B}$ and $\text{calls}_A \le \text{calls}_B$; strategy B dominates A if $F_{1,B} > F_{1,A}$ and $\text{calls}_B \le \text{calls}_A$; otherwise the relationship is classified as "trade-off".
+  (c) Pairwise dominance labels are exported to `figures/F6_dominance.csv` and `.md` and rendered directly in a text box on Figure F6; no dummy placeholder rows are written to the figure plotting data.
+(7) Rule R3 (Post-hoc timing exclusion):
+  (a) Clean timing sensitivity columns in Table T2 exclude trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9`.
+  (b) Column `clean_exclusion_rule` states verbatim: "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)". Existing column suffix `_post_hoc_not_preregistered` is preserved.
+Reasoning: resolves defects identified in independent review of the Phase 4 analysis pipeline, corrects inaccuracies in D-85, enforces the validation gate fail-closed without bypass, renders Table T3 verbatim from validator output, implements Rules R1–R3, and documents complete pipeline execution provenance without modifying raw experimental data. Affects: `scripts/analysis/`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
diff --git c/scripts/analysis/figures.py w/scripts/analysis/figures.py
index 2662cd8..37c46d7 100644
--- c/scripts/analysis/figures.py
+++ w/scripts/analysis/figures.py
@@ -17,10 +17,13 @@ try:
     from .style import apply_thesis_style, export_figure, STRATEGY_PALETTE, STRATEGY_LABELS, STRATEGY_MARKERS
     from .stats import evaluate_dominance
     from .bootstrap import compute_series_stats
+    from .tables import export_markdown_table, write_csv
 except ImportError:
     from style import apply_thesis_style, export_figure, STRATEGY_PALETTE, STRATEGY_LABELS, STRATEGY_MARKERS
     from stats import evaluate_dominance
     from bootstrap import compute_series_stats
+    from tables import export_markdown_table, write_csv
+
 
 
 def plot_f4_accuracy_comparison(
@@ -236,7 +239,9 @@ def plot_f6_cost_vs_accuracy(
 ) -> None:
     """Figure F6: Cost beside accuracy for each strategy and corpus (calls against F1).
 
-    Evaluates Pareto dominance mechanics per Decisions D3 and D5.
+    Evaluates Pareto dominance mechanics per Decisions D3, D5, and Rule R2.
+    Pairwise labels are written to F6_dominance.csv and .md (not into the figure CSV)
+    and rendered in a text box on each panel.
     """
     apply_thesis_style()
 
@@ -249,7 +254,8 @@ def plot_f6_cost_vs_accuracy(
         return
 
     fig, axes = plt.subplots(1, len(corpora), figsize=(7.0 * len(corpora), 5.5), squeeze=False)
-    csv_data = []
+    csv_data: List[Dict[str, Any]] = []
+    dominance_rows: List[Dict[str, Any]] = []
 
     for c_idx, corpus in enumerate(corpora):
         ax = axes[0][c_idx]
@@ -285,20 +291,35 @@ def plot_f6_cost_vs_accuracy(
                 "f1": f1,
             })
 
-        # Evaluate dominance pairs
+        # Evaluate dominance pairs per Rule R2
         strat_names = list(points.keys())
+        text_lines: List[str] = []
         for i in range(len(strat_names)):
             for j in range(i + 1, len(strat_names)):
                 s_a, s_b = strat_names[i], strat_names[j]
                 dom = evaluate_dominance(points[s_a], points[s_b])
-                csv_data.append({
+                dominance_rows.append({
                     "corpus": corpus,
-                    "strategy": f"{s_a} vs {s_b}",
-                    "variant": "dominance_evaluation",
-                    "calls": 0.0,
-                    "f1": 0.0,
-                    "dominance_result": dom,
+                    "strategy_a": s_a,
+                    "strategy_b": s_b,
+                    "calls_a": points[s_a]["calls"],
+                    "calls_b": points[s_b]["calls"],
+                    "f1_a": points[s_a]["f1"],
+                    "f1_b": points[s_b]["f1"],
+                    "f1_diff": points[s_a]["f1"] - points[s_b]["f1"],
+                    "dominance": dom,
                 })
+                text_lines.append(f"{s_a} vs {s_b}: {dom}")
+
+        if text_lines:
+            ax.text(
+                0.03, 0.97, "\n".join(text_lines),
+                transform=ax.transAxes,
+                fontsize=7,
+                verticalalignment="top",
+                horizontalalignment="left",
+                bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.85, edgecolor="gray"),
+            )
 
         ax.set_ylim(0, 1.05)
         ax.legend(loc="lower right", fontsize=8)
@@ -307,6 +328,19 @@ def plot_f6_cost_vs_accuracy(
     export_figure(fig, output_dir / "F6_cost_vs_accuracy_dominance", csv_data)
     plt.close(fig)
 
+    fieldnames = [
+        "corpus", "strategy_a", "strategy_b", "calls_a", "calls_b",
+        "f1_a", "f1_b", "f1_diff", "dominance"
+    ]
+    write_csv(output_dir / "F6_dominance.csv", dominance_rows, fieldnames=fieldnames)
+    export_markdown_table(
+        dominance_rows, output_dir / "F6_dominance.md",
+        "Figure F6: Pairwise Pareto Dominance Summary (D5 / D3 / R2)",
+        headers=fieldnames,
+    )
+
+
+
 
 def plot_f1_calls_scaling(
     t2_rows: List[Dict[str, Any]],
@@ -451,14 +485,16 @@ def plot_f2_wallclock_scaling(
 def plot_f3_premise_check(
     t2_rows: List[Dict[str, Any]],
     output_dir: Path,
-    k_cap: int = 10,
-    smax_cap: int = 10,
+    k_cap: int,
+    smax_cap: int,
 ) -> None:
     """Figure F3: Premise check: calls and total_s vs n for Strategies 3 and 4
-
     on a linear y-axis, with the cap (k, s_max) drawn as a reference line (plan line 77).
     Two panels: Left panel = LLM calls vs n; Right panel = total_s vs n.
     """
+    if k_cap is None or smax_cap is None:
+        raise ValueError("F3 caps (k_cap, smax_cap) must be provided from primary strategy_config.json")
+
     apply_thesis_style()
     fig, (ax_calls, ax_time) = plt.subplots(1, 2, figsize=(14, 5.5))
     csv_data = []
@@ -466,13 +502,13 @@ def plot_f3_premise_check(
     # Strategy 3 (primary: k=10)
     s3_rows = [r for r in t2_rows if r["strategy"] == "ann_retrieval" and "primary" in r.get("variant", "")]
     if not s3_rows:
-        s3_rows = [r for r in t2_rows if r["strategy"] == "ann_retrieval" and "k=10" in r.get("variant", "")]
+        s3_rows = [r for r in t2_rows if r["strategy"] == "ann_retrieval" and f"k={k_cap}" in r.get("variant", "")]
     s3_rows.sort(key=lambda x: int(x["size_n"]))
 
     # Strategy 4 (primary: s_max=10)
     s4_rows = [r for r in t2_rows if r["strategy"] == "bounded_bucket" and "primary" in r.get("variant", "")]
     if not s4_rows:
-        s4_rows = [r for r in t2_rows if r["strategy"] == "bounded_bucket" and "s_max=10" in r.get("variant", "")]
+        s4_rows = [r for r in t2_rows if r["strategy"] == "bounded_bucket" and f"s_max={smax_cap}" in r.get("variant", "")]
     s4_rows.sort(key=lambda x: int(x["size_n"]))
 
     # Panel A: LLM Calls on linear scale
@@ -480,8 +516,8 @@ def plot_f3_premise_check(
         sizes_3 = [int(r["size_n"]) for r in s3_rows]
         calls_3 = [float(r["llm_calls_mean"]) for r in s3_rows]
         tot_3 = [float(r["total_s_mean"]) for r in s3_rows]
-        ax_calls.plot(sizes_3, calls_3, "o-", label="Strategy 3 (ANN, k=10)", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
-        ax_time.plot(sizes_3, tot_3, "o-", label="Strategy 3 (ANN, k=10)", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
+        ax_calls.plot(sizes_3, calls_3, "o-", label=f"Strategy 3 (ANN, k={k_cap})", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
+        ax_time.plot(sizes_3, tot_3, "o-", label=f"Strategy 3 (ANN, k={k_cap})", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
         for s, c, t in zip(sizes_3, calls_3, tot_3):
             csv_data.append({"strategy": "ann_retrieval", "n": s, "llm_calls_mean": c, "total_s_mean": t, "cap": k_cap})
 
@@ -489,13 +525,13 @@ def plot_f3_premise_check(
         sizes_4 = [int(r["size_n"]) for r in s4_rows]
         calls_4 = [float(r["llm_calls_mean"]) for r in s4_rows]
         tot_4 = [float(r["total_s_mean"]) for r in s4_rows]
-        ax_calls.plot(sizes_4, calls_4, "s-", label="Strategy 4 (Bucket, s_max=10)", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
-        ax_time.plot(sizes_4, tot_4, "s-", label="Strategy 4 (Bucket, s_max=10)", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
+        ax_calls.plot(sizes_4, calls_4, "s-", label=f"Strategy 4 (Bucket, s_max={smax_cap})", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
+        ax_time.plot(sizes_4, tot_4, "s-", label=f"Strategy 4 (Bucket, s_max={smax_cap})", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
         for s, c, t in zip(sizes_4, calls_4, tot_4):
             csv_data.append({"strategy": "bounded_bucket", "n": s, "llm_calls_mean": c, "total_s_mean": t, "cap": smax_cap})
 
     # Reference cap line on calls panel
-    ax_calls.axhline(k_cap, color="red", linestyle="--", lw=1.5, label=f"Theoretical Bound (k = s_max = {k_cap})")
+    ax_calls.axhline(k_cap, color="red", linestyle="--", lw=1.5, label="cap (k / s_max)")
 
     ax_calls.set_xlabel("Graph Size n (linear scale)")
     ax_calls.set_ylabel("Realised LLM Calls per Insertion")
@@ -511,3 +547,4 @@ def plot_f3_premise_check(
     fig.tight_layout()
     export_figure(fig, output_dir / "F3_premise_check", csv_data)
     plt.close(fig)
+
diff --git c/scripts/analysis/run_analysis.py w/scripts/analysis/run_analysis.py
index 442ebf5..e3d584b 100644
--- c/scripts/analysis/run_analysis.py
+++ w/scripts/analysis/run_analysis.py
@@ -12,9 +12,12 @@ Usage:
 from __future__ import annotations
 
 import argparse
+import hashlib
+import json
+import subprocess
 import sys
 from pathlib import Path
-from typing import List
+from typing import List, Optional
 
 # Ensure scripts/analysis and repo root are in sys.path
 _current_dir = Path(__file__).resolve().parent
@@ -27,6 +30,7 @@ if str(_repo_root) not in sys.path:
 try:
     from .validate_runs import validate_all_runs
     from .tables import (
+        extract_variant_label,
         generate_t1_accuracy_table,
         generate_t2_sweep_cost_table,
         generate_t3_inventory_table,
@@ -45,6 +49,7 @@ try:
 except ImportError:
     from validate_runs import validate_all_runs
     from tables import (
+        extract_variant_label,
         generate_t1_accuracy_table,
         generate_t2_sweep_cost_table,
         generate_t3_inventory_table,
@@ -62,6 +67,15 @@ except ImportError:
     )
 
 
+def _file_sha256(path: Path) -> str:
+    """Compute sha256 of a file in 64 KB chunks."""
+    h = hashlib.sha256()
+    with open(path, "rb") as f:
+        while chunk := f.read(65536):
+            h.update(chunk)
+    return h.hexdigest()
+
+
 def main() -> int:
     parser = argparse.ArgumentParser(description="Master Phase 4 Empirical Analysis Pipeline")
     parser.add_argument(
@@ -88,12 +102,6 @@ def main() -> int:
         default=None,
         help="Optional path to machine-written sha256 hashes file to verify against",
     )
-    parser.add_argument(
-        "--skip-gate",
-        action="store_true",
-        default=False,
-        help="Bypass validation gate (for development / unit testing only)",
-    )
     args = parser.parse_args()
 
     results_dir = args.results_dir.resolve()
@@ -101,34 +109,78 @@ def main() -> int:
     tables_dir = output_dir / "tables"
     figures_dir = output_dir / "figures"
 
-    tables_dir.mkdir(parents=True, exist_ok=True)
-    figures_dir.mkdir(parents=True, exist_ok=True)
-
     print("=" * 80)
     print("PHASE 4 EMPIRICAL ANALYSIS PIPELINE")
     print(f"Results Directory: {results_dir}")
     print(f"Output Directory:  {output_dir}")
     print("=" * 80)
 
-    # 1. Validation Gate (Real signature: returns (overall_passed, run_results, table_t3_csv_string))
-    if not args.skip_gate:
-        print("\n>>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...")
-        overall_passed, run_results, t3_csv_str = validate_all_runs(
-            results_dir,
-            src_diff_clean=args.src_diff_clean,
-            hashes_path=args.hashes,
-        )
-        if not overall_passed:
-            print("\n[ABORT] Validation gate failed. Analysis halted per Rule 5 of Analysis Plan.")
-            for r in run_results:
-                if not r.get("passed"):
-                    print(f"  FAILED RUN: {r.get('run_dir')}")
-                    for err in r.get("errors", []):
-                        print(f"    -> ERROR: {err}")
-            return 1
-        print("\n[OK] Validation gate passed 100%. Proceeding with analysis.\n")
+    # 1. Validation Gate (fail-closed: do not create output dirs or write anything on failure)
+    print("\n>>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...")
+    overall_passed, run_results, t3_csv_str = validate_all_runs(
+        results_dir,
+        src_diff_clean=args.src_diff_clean,
+        hashes_path=args.hashes,
+    )
+    if not overall_passed:
+        print("\n[ABORT] Validation gate failed. Analysis halted per Rule 5 of Analysis Plan.")
+        for r in run_results:
+            if not r.get("passed"):
+                print(f"  FAILED RUN: {r.get('run_dir')}")
+                for err in r.get("errors", []):
+                    print(f"    -> ERROR: {err}")
+        return 1
+
+    print("\n[OK] Validation gate passed 100%. Proceeding with analysis.\n")
+
+    # Create output directories only after the gate passes
+    tables_dir.mkdir(parents=True, exist_ok=True)
+    figures_dir.mkdir(parents=True, exist_ok=True)
+
+    # Write RUN_INFO.txt
+    pipeline_modules = [
+        "validate_runs.py",
+        "run_analysis.py",
+        "tables.py",
+        "figures.py",
+        "stats.py",
+        "bootstrap.py",
+        "style.py",
+    ]
+    module_hashes = {}
+    for mod in pipeline_modules:
+        p = _current_dir / mod
+        if p.is_file():
+            module_hashes[mod] = _file_sha256(p)
+        else:
+            module_hashes[mod] = "MISSING"
+
+    try:
+        git_head = subprocess.check_output(
+            ["git", "rev-parse", "HEAD"], cwd=_repo_root, text=True
+        ).strip()
+    except Exception:
+        git_head = "UNKNOWN"
+
+    if args.hashes and args.hashes.is_file():
+        hashes_info = f"{args.hashes.resolve()} (sha256: {_file_sha256(args.hashes)})"
     else:
-        print("\n[WARNING] Validation gate skipped via --skip-gate.\n")
+        hashes_info = "NOT SUPPLIED"
+
+    run_info_lines = [
+        f"argv: {' '.join(sys.argv)}",
+        f"results_dir: {results_dir}",
+        f"git_commit: {git_head}",
+        "pipeline_modules_sha256:",
+    ]
+    for mod, h in module_hashes.items():
+        run_info_lines.append(f"  {mod}: {h}")
+    run_info_lines.extend([
+        f"hashes_file: {hashes_info}",
+        f"src_diff_clean: {args.src_diff_clean}",
+        "overall_gate_status: PASS",
+    ])
+    (output_dir / "RUN_INFO.txt").write_text("\n".join(run_info_lines) + "\n", encoding="utf-8")
 
     # Discover run directories
     if (results_dir / "manifest.json").is_file():
@@ -141,9 +193,10 @@ def main() -> int:
 
     print(f"Discovered: {len(all_runs)} total runs ({len(acc_runs)} accuracy, {len(sweep_runs)} sweep)\n")
 
-    # 2. Table T3: Run Inventory (always generated for provenance)
+    # 2. Table T3: Run Inventory (write validator's t3_csv verbatim as T3_run_inventory.csv)
     print(">>> STEP 2: Generating Table T3 (Run Inventory)...")
-    t3_rows = generate_t3_inventory_table(all_runs, tables_dir / "T3_run_inventory.csv")
+    (tables_dir / "T3_run_inventory.csv").write_text(t3_csv_str, encoding="utf-8")
+    t3_rows = generate_t3_inventory_table(t3_csv_str)
     export_markdown_table(t3_rows, tables_dir / "T3_run_inventory.md", "Table T3: Empirical Run Inventory")
     print(f"    Saved: {tables_dir / 'T3_run_inventory.csv'} and .md ({len(t3_rows)} entries)")
 
@@ -167,6 +220,7 @@ def main() -> int:
 
         plot_f6_cost_vs_accuracy(t1_rows, figures_dir)
         print(f"    Saved: {figures_dir / 'F6_cost_vs_accuracy_dominance.pdf'} (.png, .csv)")
+        print(f"    Saved: {figures_dir / 'F6_dominance.csv'} and .md")
 
     # 4. Sweep Tables & Figures (if sweep runs present)
     if sweep_runs:
@@ -180,6 +234,35 @@ def main() -> int:
             export_markdown_table(slope_fit_rows, tables_dir / "T2_slope_fits.md", "Table T2b: Log-Log OLS Slope Fits & Flatness Classification (D2)")
             print(f"    Saved: {tables_dir / 'T2_slope_fits.csv'} and .md ({len(slope_fit_rows)} fits)")
 
+        # Extract primary caps for F3
+        k_cap: Optional[int] = None
+        smax_cap: Optional[int] = None
+        for d in sweep_runs:
+            sidecar_p = d / "strategy_config.json"
+            if not sidecar_p.is_file():
+                continue
+            strat_cfg = json.loads(sidecar_p.read_text(encoding="utf-8"))
+            strat = strat_cfg.get("strategy")
+            strat_params = strat_cfg.get("config", {}) if isinstance(strat_cfg.get("config"), dict) else {}
+            variant = extract_variant_label(d.name)
+
+            if strat == "ann_retrieval" and "primary" in variant:
+                if "k" in strat_params:
+                    k_cap = int(strat_params["k"])
+                elif "k" in strat_cfg:
+                    k_cap = int(strat_cfg["k"])
+
+            if strat == "bounded_bucket" and "primary" in variant:
+                if "s_max" in strat_params:
+                    smax_cap = int(strat_params["s_max"])
+                elif "s_max" in strat_cfg:
+                    smax_cap = int(strat_cfg["s_max"])
+
+        if k_cap is None:
+            raise ValueError("Missing 'k' cap in primary Strategy 3 (ann_retrieval) strategy_config.json")
+        if smax_cap is None:
+            raise ValueError("Missing 's_max' cap in primary Strategy 4 (bounded_bucket) strategy_config.json")
+
         print("\n>>> STEP 6: Generating Sweep Figures (F1, F2, F3)...")
         plot_f1_calls_scaling(t2_rows, figures_dir)
         print(f"    Saved: {figures_dir / 'F1_calls_scaling.pdf'} (.png, .csv)")
@@ -187,7 +270,7 @@ def main() -> int:
         plot_f2_wallclock_scaling(t2_rows, figures_dir)
         print(f"    Saved: {figures_dir / 'F2_wallclock_scaling.pdf'} (.png, .csv)")
 
-        plot_f3_premise_check(t2_rows, figures_dir, k_cap=10, smax_cap=10)
+        plot_f3_premise_check(t2_rows, figures_dir, k_cap=k_cap, smax_cap=smax_cap)
         print(f"    Saved: {figures_dir / 'F3_premise_check.pdf'} (.png, .csv)")
 
     print("\n" + "=" * 80)
@@ -198,3 +281,4 @@ def main() -> int:
 
 if __name__ == "__main__":
     sys.exit(main())
+
diff --git c/scripts/analysis/stats.py w/scripts/analysis/stats.py
index e98a213..4be1ec0 100644
--- c/scripts/analysis/stats.py
+++ w/scripts/analysis/stats.py
@@ -1,14 +1,19 @@
 """
 stats.py — Statistical Modeling, Flatness Fits, and Dominance Logic
 ===================================================================
-Implements Sections 4.2, 4.3, and Figure F6 rules from Phase 4 Analysis Plan:
+Implements Sections 4.2, 4.3, and Figure F6 rules from Phase 4 Analysis Plan
+and APC Rules R1 and R2:
 - OLS regression of log(mean_cost) on log(n)
-- Bootstrap confidence interval for slope (resampling trials within size)
+- R1 Zero-mean rule: log-log fit with any non-positive or non-finite size mean is
+  UNDEFINED (NaN slope, no CI, no D2 category, category text "undefined (zero mean at n=...)").
+  No clamp. Bootstrap resamples with zero-mean sizes are dropped and n_boot_used reported.
 - Categorization into pre-registered flatness bins (D2):
     * slope < 0.1: "approximately flat"
     * 0.1 <= slope <= 0.9: "sub-linear"
     * slope > 0.9: "approximately linear"
-- Mechanical Pareto dominance rule (D5) with 0.025 F1 equivalence band (D3).
+- R2 Mechanical Pareto dominance rule:
+    * |F1 diff| < 0.025: "not distinguishable (F1 within 0.025)" regardless of calls
+    * |F1 diff| >= 0.025: A dominates B if F1_A > F1_B and calls_A <= calls_B; otherwise "trade-off".
 """
 
 from __future__ import annotations
@@ -19,6 +24,8 @@ import numpy as np
 
 def classify_slope_flatness(slope: float) -> str:
     """Classify log-log scaling slope per Decision D2."""
+    if np.isnan(slope):
+        return "undefined"
     if slope < 0.1:
         return "approximately flat"
     elif slope <= 0.9:
@@ -33,17 +40,26 @@ def fit_log_log_slope(
 ) -> Tuple[float, float, float]:
     """Fits OLS: log(mean_cost) = slope * log(n) + intercept.
 
+    Per Rule R1: A log-log fit with any size whose mean is <= 0 or non-finite
+    is UNDEFINED (returns NaN slope, intercept, and r_squared). No clamp.
+
+
     Returns (slope, intercept, r_squared).
     """
     x_arr = np.asarray(sizes, dtype=np.float64)
     y_arr = np.asarray(mean_costs, dtype=np.float64)
 
-    # Filter out non-positive sizes or costs safely
-    # If cost is 0, clamp to small epsilon for log calculation
-    y_clamped = np.where(y_arr <= 0, 1e-12, y_arr)
+    if len(x_arr) < 2 or len(y_arr) < 2 or len(x_arr) != len(y_arr):
+        return (float("nan"), float("nan"), float("nan"))
+
+    if np.any(x_arr <= 0) or not np.all(np.isfinite(x_arr)):
+        return (float("nan"), float("nan"), float("nan"))
+
+    if np.any(y_arr <= 0) or not np.all(np.isfinite(y_arr)):
+        return (float("nan"), float("nan"), float("nan"))
 
     x = np.log(x_arr)
-    y = np.log(y_clamped)
+    y = np.log(y_arr)
 
     x_mean = np.mean(x)
     y_mean = np.mean(y)
@@ -66,47 +82,76 @@ def bootstrap_slope_ci(
     n_resamples: int = 10_000,
     ci_level: float = 0.95,
     seed: int = 42,
-) -> Tuple[float, float, float, str, float]:
+) -> Tuple[float, float, float, str, float, int]:
     """Resample trials within each size, compute mean per size, and fit OLS slope.
 
-    Returns (point_estimate_slope, ci_low, ci_high, flatness_category, r_squared).
+    Per Rule R1:
+    - If any size has no trials or an empirical mean <= 0 / non-finite:
+      returns (NaN, NaN, NaN, "undefined (zero mean at n=...)", NaN, 0).
+    - In bootstrap resamples, drops any resample with a zero-mean size.
+    - Reports n_boot_used (NaN CIs if n_boot_used == 0).
+
+    Returns:
+      (point_estimate_slope, ci_low, ci_high, flatness_category, r_squared, n_boot_used)
     """
     sizes = sorted(size_to_trials.keys())
-    emp_means = [float(np.mean(size_to_trials[s])) if len(size_to_trials[s]) > 0 else 0.0 for s in sizes]
+    if len(sizes) < 2:
+        return (float("nan"), float("nan"), float("nan"), "undefined (< 2 sizes)", float("nan"), 0)
+
+    empty_sizes = [s for s in sizes if len(size_to_trials[s]) == 0]
+    if empty_sizes:
+        cat_str = f"undefined (no trials at n={', '.join(str(s) for s in empty_sizes)})"
+        return (float("nan"), float("nan"), float("nan"), cat_str, float("nan"), 0)
+
+    emp_means = [float(np.mean(size_to_trials[s])) for s in sizes]
+    zero_sizes = [sizes[i] for i, m in enumerate(emp_means) if m <= 0 or not np.isfinite(m)]
+    if zero_sizes:
+        cat_str = f"undefined (zero mean at n={', '.join(str(s) for s in zero_sizes)})"
+        return (float("nan"), float("nan"), float("nan"), cat_str, float("nan"), 0)
+
     point_slope, _, r_squared = fit_log_log_slope(sizes, emp_means)
+    if np.isnan(point_slope):
+        return (float("nan"), float("nan"), float("nan"), "undefined", float("nan"), 0)
 
     rng = np.random.default_rng(seed)
-    boot_slopes = np.empty(n_resamples, dtype=np.float64)
-
-    trials_arrays = [
-        np.asarray(size_to_trials[s], dtype=np.float64) if len(size_to_trials[s]) > 0 else np.array([0.0])
-        for s in sizes
-    ]
+    trials_arrays = [np.asarray(size_to_trials[s], dtype=np.float64) for s in sizes]
     log_sizes = np.log(np.asarray(sizes, dtype=np.float64))
     x_mean = np.mean(log_sizes)
     ss_xx = np.sum((log_sizes - x_mean) ** 2)
 
     if ss_xx == 0:
-        return (point_slope, point_slope, point_slope, classify_slope_flatness(point_slope), r_squared)
+        return (point_slope, point_slope, point_slope, classify_slope_flatness(point_slope), r_squared, n_resamples)
 
-    for i in range(n_resamples):
+    valid_slopes: List[float] = []
+    for _ in range(n_resamples):
         b_means = np.empty(len(sizes), dtype=np.float64)
+        has_zero_or_nonfinite = False
         for s_idx, t_arr in enumerate(trials_arrays):
             resamp = rng.choice(t_arr, size=len(t_arr), replace=True)
-            b_means[s_idx] = np.mean(resamp)
+            m = np.mean(resamp)
+            if m <= 0 or not np.isfinite(m):
+                has_zero_or_nonfinite = True
+                break
+            b_means[s_idx] = m
+        if has_zero_or_nonfinite:
+            continue
 
-        b_clamped = np.where(b_means <= 0, 1e-12, b_means)
-        log_b_means = np.log(b_clamped)
+        log_b_means = np.log(b_means)
         y_mean = np.mean(log_b_means)
         ss_xy = np.sum((log_sizes - x_mean) * (log_b_means - y_mean))
-        boot_slopes[i] = ss_xy / ss_xx
+        valid_slopes.append(float(ss_xy / ss_xx))
+
+    n_boot_used = len(valid_slopes)
+    if n_boot_used == 0:
+        ci_low = float("nan")
+        ci_high = float("nan")
+    else:
+        alpha = (1.0 - ci_level) / 2.0
+        ci_low = float(np.percentile(valid_slopes, 100.0 * alpha))
+        ci_high = float(np.percentile(valid_slopes, 100.0 * (1.0 - alpha)))
 
-    alpha = (1.0 - ci_level) / 2.0
-    ci_low = float(np.percentile(boot_slopes, 100.0 * alpha))
-    ci_high = float(np.percentile(boot_slopes, 100.0 * (1.0 - alpha)))
     category = classify_slope_flatness(point_slope)
-
-    return (point_slope, ci_low, ci_high, category, r_squared)
+    return (point_slope, ci_low, ci_high, category, r_squared, n_boot_used)
 
 
 def evaluate_dominance(
@@ -114,34 +159,28 @@ def evaluate_dominance(
     point_b: Dict[str, float],
     f1_delta_threshold: float = 0.025,
 ) -> str:
-    """Evaluate mechanical dominance between strategy A and strategy B per D5 and D3.
+    """Evaluate mechanical dominance between strategy A and strategy B per D5, D3, and Rule R2.
 
     point_a and point_b contain keys: 'calls' and 'f1'.
 
-    Returns one of:
-      - "A dominates B"
-      - "B dominates A"
-      - "not distinguishable" (if F1 difference <= threshold and calls are similar)
-      - "trade-off" (one has higher F1 but also higher calls)
+    Per Rule R2:
+    - |F1 difference| < 0.025 => "not distinguishable (F1 within 0.025)", regardless of calls.
+    - At or above 0.025: A dominates B if A has higher F1 and calls <= B's;
+      B dominates A if B has higher F1 and calls <= A's;
+      otherwise "trade-off".
     """
     calls_a, f1_a = point_a["calls"], point_a["f1"]
     calls_b, f1_b = point_b["calls"], point_b["f1"]
 
     f1_diff = f1_a - f1_b
 
-    if abs(f1_diff) <= f1_delta_threshold:
-        # F1 is indistinguishable within empirical run-to-run noise band (D3)
-        if calls_a < calls_b:
-            return "A dominates B (calls advantage, F1 equivalent)"
-        elif calls_b < calls_a:
-            return "B dominates A (calls advantage, F1 equivalent)"
-        else:
-            return "not distinguishable"
+    if abs(f1_diff) < f1_delta_threshold:
+        return "not distinguishable (F1 within 0.025)"
 
-    # F1 difference is distinguishable (> 0.025)
     if f1_a > f1_b and calls_a <= calls_b:
         return "A dominates B"
     elif f1_b > f1_a and calls_b <= calls_a:
         return "B dominates A"
     else:
         return "trade-off"
+
diff --git c/scripts/analysis/tables.py w/scripts/analysis/tables.py
index a2cee73..95d6df1 100644
--- c/scripts/analysis/tables.py
+++ w/scripts/analysis/tables.py
@@ -21,28 +21,29 @@ import numpy as np
 
 try:
     from .validate_runs import (
-        compute_directory_sha256,
-        parse_manifest,
         parse_sidecar,
         parse_summary_csv,
         parse_raw_jsonl,
-        validate_single_run,
     )
     from .bootstrap import compute_series_stats
     from .stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness
 except ImportError:
     from validate_runs import (
-        compute_directory_sha256,
-        parse_manifest,
         parse_sidecar,
         parse_summary_csv,
         parse_raw_jsonl,
-        validate_single_run,
     )
     from bootstrap import compute_series_stats
     from stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness
 
 
+def _require_col(row: Dict[str, Any], col: str, run_name: str) -> Any:
+    """Strictly access a required column, raising KeyError naming run and column if missing."""
+    if col not in row or row[col] == "" or row[col] is None:
+        raise KeyError(f"Run '{run_name}' missing required column '{col}'")
+    return row[col]
+
+
 def extract_variant_label(run_name: str) -> str:
     """Extract a clean human-readable variant label from run directory name."""
     if "k10_ef128" in run_name and "smin" not in run_name:
@@ -72,33 +73,41 @@ def extract_variant_label(run_name: str) -> str:
     return run_name
 
 
-def write_csv(output_path: Path, rows: List[Dict[str, Any]]) -> None:
+def write_csv(output_path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
     """Write rows to a CSV file with deterministic column order."""
-    if not rows:
+    if not rows and not fieldnames:
         return
     output_path.parent.mkdir(parents=True, exist_ok=True)
-    seen_keys: Dict[str, None] = {}
-    for r in rows:
-        for k in r.keys():
-            seen_keys[k] = None
-    fieldnames = list(seen_keys.keys())
+    if not fieldnames:
+        seen_keys: Dict[str, None] = {}
+        for r in rows:
+            for k in r.keys():
+                seen_keys[k] = None
+        fieldnames = list(seen_keys.keys())
 
     with open(output_path, "w", newline="", encoding="utf-8") as f:
         writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
         writer.writeheader()
-        writer.writerows(rows)
+        if rows:
+            writer.writerows(rows)
 
 
-def export_markdown_table(rows: List[Dict[str, Any]], output_md_path: Path, title: str) -> None:
+def export_markdown_table(
+    rows: List[Dict[str, Any]],
+    output_md_path: Path,
+    title: str,
+    headers: Optional[List[str]] = None,
+) -> None:
     """Write table rows as a GitHub-flavored markdown table."""
-    if not rows:
+    if not rows and not headers:
         return
     output_md_path.parent.mkdir(parents=True, exist_ok=True)
-    seen_keys: Dict[str, None] = {}
-    for r in rows:
-        for k in r.keys():
-            seen_keys[k] = None
-    headers = list(seen_keys.keys())
+    if not headers:
+        seen_keys: Dict[str, None] = {}
+        for r in rows:
+            for k in r.keys():
+                seen_keys[k] = None
+        headers = list(seen_keys.keys())
 
     lines = [f"# {title}\n", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
     for r in rows:
@@ -121,6 +130,7 @@ def export_markdown_table(rows: List[Dict[str, Any]], output_md_path: Path, titl
     output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
 
 
+
 def generate_t1_accuracy_table(
     accuracy_run_dirs: List[Path],
     output_csv_path: Optional[Path] = None,
@@ -148,13 +158,10 @@ def generate_t1_accuracy_table(
         strat = strat_cfg.get("strategy", r_dir.name)
         variant = extract_variant_label(r_dir.name)
 
-        # Parse raw.jsonl for failure / retry inspection per corpus
+        # Parse raw.jsonl for failure tracking per corpus
         failed_then_succ_by_corpus: Dict[str, List[str]] = {}
-        retries_by_corpus: Dict[str, int] = {}
-        n_with_retries_by_corpus: Dict[str, int] = {}
-
         if raw_p.exists():
-            records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_p)
+            records, is_resumed, _, key_records = parse_raw_jsonl(raw_p)
             for k, rec_list in key_records.items():
                 corp = rec_list[-1].get("corpus", "")
                 earlier_failed = any(x.get("status") in ("failed", "error") for x in rec_list[:-1])
@@ -162,11 +169,6 @@ def generate_t1_accuracy_table(
                 if earlier_failed and final_success:
                     failed_then_succ_by_corpus.setdefault(corp, []).append(k)
 
-                r_cnt = retry_counts.get(k, 0)
-                if r_cnt > 0 and final_success:
-                    retries_by_corpus[corp] = retries_by_corpus.get(corp, 0) + r_cnt
-                    n_with_retries_by_corpus[corp] = n_with_retries_by_corpus.get(corp, 0) + 1
-
         # Effective shortlist size k for random baseline
         cfg = strat_cfg.get("config", {}) if isinstance(strat_cfg.get("config"), dict) else {}
         k_val = cfg.get("k", strat_cfg.get("k"))
@@ -175,31 +177,33 @@ def generate_t1_accuracy_table(
 
         summary_rows = parse_summary_csv(summary_p)
         for s in summary_rows:
-            corpus = s.get("corpus_or_size", "")
+            corpus = _require_col(s, "corpus_or_size", r_dir.name)
             m = corpus_m.get(corpus, 28)
-            rand_baseline = (min(k_val, m) / m) if k_val is not None else 1.0
+            # Random baseline is blank/NaN where the strategy has no k or s_max cap
+            rand_baseline = (min(k_val, m) / m) if k_val is not None else float("nan")
 
             fts_keys = failed_then_succ_by_corpus.get(corpus, [])
-            n_with_retries = int(s.get("n_with_retries", n_with_retries_by_corpus.get(corpus, 0)))
+            # T1 n_with_retries comes only from summary.csv
+            n_with_retries = int(_require_col(s, "n_with_retries", r_dir.name))
 
             row = {
                 "strategy": strat,
                 "variant": variant,
                 "corpus": corpus,
-                "num_trials": int(s.get("num_trials", 0)),
-                "num_success": int(s.get("num_success", 0)),
+                "num_trials": int(_require_col(s, "num_trials", r_dir.name)),
+                "num_success": int(_require_col(s, "num_success", r_dir.name)),
                 "failed_then_succeeded_count": len(fts_keys),
                 "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
                 "n_with_retries": n_with_retries,
-                "llm_calls_mean": float(s.get("llm_calls_mean", 0.0)),
-                "precision_micro": float(s.get("precision_micro", 0.0)),
-                "recall_micro": float(s.get("recall_micro", 0.0)),
-                "f1_micro": float(s.get("f1_micro", 0.0)),
-                "precision_macro": float(s.get("precision_macro", 0.0)),
-                "recall_macro": float(s.get("recall_macro", 0.0)),
-                "f1_macro": float(s.get("f1_macro", 0.0)),
-                "shortlist_recall_micro": float(s.get("shortlist_recall_micro", 0.0)),
-                "shortlist_recall_macro": float(s.get("shortlist_recall_macro", 0.0)),
+                "llm_calls_mean": float(_require_col(s, "llm_calls_mean", r_dir.name)),
+                "precision_micro": float(_require_col(s, "precision_micro", r_dir.name)),
+                "recall_micro": float(_require_col(s, "recall_micro", r_dir.name)),
+                "f1_micro": float(_require_col(s, "f1_micro", r_dir.name)),
+                "precision_macro": float(_require_col(s, "precision_macro", r_dir.name)),
+                "recall_macro": float(_require_col(s, "recall_macro", r_dir.name)),
+                "f1_macro": float(_require_col(s, "f1_macro", r_dir.name)),
+                "shortlist_recall_micro": float(_require_col(s, "shortlist_recall_micro", r_dir.name)),
+                "shortlist_recall_macro": float(_require_col(s, "shortlist_recall_macro", r_dir.name)),
                 "random_baseline_recall": rand_baseline,
             }
             rows.append(row)
@@ -231,14 +235,14 @@ def generate_t4_sensitivity_table(
             row = {
                 "strategy": strat,
                 "variant": variant,
-                "corpus": s.get("corpus_or_size", ""),
-                "precision_micro_sensitivity": float(s.get("precision_micro_sensitivity", 0.0)),
-                "recall_micro_sensitivity": float(s.get("recall_micro_sensitivity", 0.0)),
-                "f1_micro_sensitivity": float(s.get("f1_micro_sensitivity", 0.0)),
-                "precision_macro_sensitivity": float(s.get("precision_macro_sensitivity", 0.0)),
-                "recall_macro_sensitivity": float(s.get("recall_macro_sensitivity", 0.0)),
-                "f1_macro_sensitivity": float(s.get("f1_macro_sensitivity", 0.0)),
-                "unjudged_predictions_total": int(s.get("unjudged_predictions_total", 0)),
+                "corpus": _require_col(s, "corpus_or_size", r_dir.name),
+                "precision_micro_sensitivity": float(_require_col(s, "precision_micro_sensitivity", r_dir.name)),
+                "recall_micro_sensitivity": float(_require_col(s, "recall_micro_sensitivity", r_dir.name)),
+                "f1_micro_sensitivity": float(_require_col(s, "f1_micro_sensitivity", r_dir.name)),
+                "precision_macro_sensitivity": float(_require_col(s, "precision_macro_sensitivity", r_dir.name)),
+                "recall_macro_sensitivity": float(_require_col(s, "recall_macro_sensitivity", r_dir.name)),
+                "f1_macro_sensitivity": float(_require_col(s, "f1_macro_sensitivity", r_dir.name)),
+                "unjudged_predictions_total": int(_require_col(s, "unjudged_predictions_total", r_dir.name)),
             }
             rows.append(row)
 
@@ -249,48 +253,74 @@ def generate_t4_sensitivity_table(
 
 
 def generate_t3_inventory_table(
-    all_run_dirs: List[Path],
+    t3_csv_content_or_path: str | Path,
     output_csv_path: Optional[Path] = None,
 ) -> List[Dict[str, Any]]:
-    """Generate Table T3: Run inventory for reproducibility and provenance."""
-    rows = []
-    for r_dir in sorted(all_run_dirs):
-        manifest_p = r_dir / "manifest.json"
-        if not manifest_p.exists():
-            continue
+    """Parse validator's Table T3 CSV verbatim and optionally write to output_csv_path."""
+    if isinstance(t3_csv_content_or_path, Path):
+        content = t3_csv_content_or_path.read_text(encoding="utf-8")
+    else:
+        content = str(t3_csv_content_or_path)
 
-        passed, errors, info = validate_single_run(r_dir)
-        manifest = parse_manifest(manifest_p)
+    reader = csv.DictReader(content.splitlines())
+    rows = list(reader)
 
-        fts_keys = info.get("failed_then_succeeded_keys", [])
-        still_failed_keys = info.get("still_failed_keys", [])
-
-        row = {
-            "run_dir": r_dir.name,
-            "strategy": info.get("strategy", ""),
-            "mode": info.get("mode", ""),
-            "variant": extract_variant_label(r_dir.name),
-            "git_commit": str(info.get("git_commit", ""))[:7],
-            "git_dirty": info.get("git_dirty", ""),
-            "total_trials": info.get("total_trials", 0),
-            "total_calls": info.get("total_calls", 0),
-            "call_bound": info.get("call_bound", ""),
-            "failed_trials": info.get("failed_trials", 0),
-            "failed_then_succeeded_count": len(fts_keys),
-            "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
-            "still_failed_count": len(still_failed_keys),
-            "retries": info.get("total_retries", 0),
-            "gate_status": "PASS (resumed)" if (passed and info.get("resumed")) else ("PASS" if passed else "FAIL"),
-            "dir_sha256": info.get("dir_sha256", ""),
-        }
-        rows.append(row)
-
-    if output_csv_path and rows:
-        write_csv(output_csv_path, rows)
+    if output_csv_path:
+        output_csv_path.parent.mkdir(parents=True, exist_ok=True)
+        output_csv_path.write_text(content, encoding="utf-8")
 
     return rows
 
 
+def _fit_metric_slopes(
+    strat: str,
+    variant: str,
+    metric: str,
+    condition: str,
+    size_map: Dict[int, List[float]],
+    slope_fit_rows: List[Dict[str, Any]],
+) -> None:
+    """Helper to compute log-log slope fit and bootstrap CI per Rule R1."""
+    sizes = sorted(size_map.keys())
+    min_trials = min((len(size_map[s]) for s in sizes), default=0)
+    point_slope, ci_low, ci_high, cat, r2, n_boot = bootstrap_slope_ci(size_map)
+    slope_fit_rows.append({
+        "strategy": strat,
+        "variant": variant,
+        "metric": metric,
+        "condition": condition,
+        "slope": point_slope,
+        "ci_95_low": ci_low,
+        "ci_95_high": ci_high,
+        "r_squared": r2,
+        "flatness_category_D2": cat,
+        "min_trials_per_size": min_trials,
+        "n_boot_used": n_boot,
+    })
+
+    # If undefined due to zero mean, but at least 3 sizes have positive mean, emit exploratory row per R1
+    pos_sizes = {
+        s: trials for s, trials in size_map.items()
+        if len(trials) > 0 and np.mean(trials) > 0 and np.isfinite(np.mean(trials))
+    }
+    if (np.isnan(point_slope) or "undefined (zero mean" in cat) and len(pos_sizes) >= 3:
+        p_min_trials = min(len(pos_sizes[s]) for s in pos_sizes)
+        p_slope, p_low, p_high, p_cat, p_r2, p_n_boot = bootstrap_slope_ci(pos_sizes)
+        slope_fit_rows.append({
+            "strategy": strat,
+            "variant": variant,
+            "metric": metric,
+            "condition": "exploratory (positive-mean sizes only)",
+            "slope": p_slope,
+            "ci_95_low": p_low,
+            "ci_95_high": p_high,
+            "r_squared": p_r2,
+            "flatness_category_D2": p_cat,
+            "min_trials_per_size": p_min_trials,
+            "n_boot_used": p_n_boot,
+        })
+
+
 def generate_t2_sweep_cost_table(
     sweep_run_dirs: List[Path],
     output_csv_path: Optional[Path] = None,
@@ -301,13 +331,14 @@ def generate_t2_sweep_cost_table(
     - calls, total_s, shortlist_s, decide_s distributions (mean, median, std, min, max, 95% bootstrap CIs)
     - failed-then-succeeded keys and n_with_retries
     - timing sensitivity columns that exclude trials with retries > 0 and the single trial
-      sweep:brute_force:2000:t9, labelled "post-hoc, not pre-registered" (Requirement 4).
-    - log-log OLS slope fits with 95% bootstrap CIs and D2 flatness classifications (Requirement 3).
+      sweep:brute_force:2000:t9, labelled "post-hoc, not pre-registered" (Requirement 4 / R3).
+    - log-log OLS slope fits with 95% bootstrap CIs, min_trials_per_size, n_boot_used,
+      and D2 flatness classifications (Requirement 3 / R1).
 
     Returns (t2_rows, slope_fit_rows).
     """
     rows = []
-    slope_fit_rows = []
+    slope_fit_rows: List[Dict[str, Any]] = []
 
     for r_dir in sorted(sweep_run_dirs):
         summary_p = r_dir / "summary.csv"
@@ -321,20 +352,24 @@ def generate_t2_sweep_cost_table(
         variant = extract_variant_label(r_dir.name)
 
         # Parse raw.jsonl
-        records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_p)
+        records, is_resumed, _, key_records = parse_raw_jsonl(raw_p)
 
         # Deduplicate records by trial key, keeping latest record per key
         records_by_key: Dict[str, Dict[str, Any]] = {}
         for r in records:
-            k = r.get("key")
-            if k:
-                records_by_key[k] = r
+            k = _require_col(r, "key", r_dir.name)
+            records_by_key[k] = r
         deduped = list(records_by_key.values())
 
         # Group by size
         by_size: Dict[int, List[Dict[str, Any]]] = {}
         for r in deduped:
-            s_val = int(r.get("size", r.get("metrics", {}).get("n_before", 0)))
+            if "size" in r:
+                s_val = int(r["size"])
+            elif "metrics" in r and "n_before" in r["metrics"]:
+                s_val = int(r["metrics"]["n_before"])
+            else:
+                raise KeyError(f"Run '{r_dir.name}' missing required size field in trial record")
             by_size.setdefault(s_val, []).append(r)
 
         # Track per-size arrays for slope fitting
@@ -344,24 +379,30 @@ def generate_t2_sweep_cost_table(
 
         for size_n in sorted(by_size.keys()):
             size_records = by_size[size_n]
-            successes = [r for r in size_records if r.get("status") == "success"]
+            successes = [r for r in size_records if _require_col(r, "status", r_dir.name) == "success"]
 
             # Failure and retry tracking
             fts_keys = []
             for r in successes:
-                k = r.get("key", "")
+                k = _require_col(r, "key", r_dir.name)
                 rec_hist = key_records.get(k, [])
                 if any(x.get("status") in ("failed", "error") for x in rec_hist[:-1]):
                     fts_keys.append(k)
 
-            n_with_retries = sum(1 for r in successes if r.get("retries", 0) > 0)
-            total_retries = sum(r.get("retries", 0) for r in successes)
+            n_with_retries = sum(1 for r in successes if int(_require_col(r, "retries", r_dir.name)) > 0)
+            total_retries = sum(int(_require_col(r, "retries", r_dir.name)) for r in successes)
 
             # Metric series across all pre-registered successful trials
-            calls_list = [float(r.get("metrics", {}).get("llm_calls", 0.0)) for r in successes]
-            tot_s_list = [float(r.get("metrics", {}).get("total_s", 0.0)) for r in successes]
-            short_s_list = [float(r.get("metrics", {}).get("shortlist_s", 0.0)) for r in successes]
-            dec_s_list = [float(r.get("metrics", {}).get("decide_s", 0.0)) for r in successes]
+            calls_list = []
+            tot_s_list = []
+            short_s_list = []
+            dec_s_list = []
+            for r in successes:
+                metrics = _require_col(r, "metrics", r_dir.name)
+                calls_list.append(float(_require_col(metrics, "llm_calls", r_dir.name)))
+                tot_s_list.append(float(_require_col(metrics, "total_s", r_dir.name)))
+                short_s_list.append(float(_require_col(metrics, "shortlist_s", r_dir.name)))
+                dec_s_list.append(float(_require_col(metrics, "decide_s", r_dir.name)))
 
             size_calls_map[size_n] = calls_list
             size_total_s_map[size_n] = tot_s_list
@@ -371,14 +412,15 @@ def generate_t2_sweep_cost_table(
             short_stats = compute_series_stats(short_s_list)
             dec_stats = compute_series_stats(dec_s_list)
 
-            # Post-hoc timing sensitivity: exclude trials with retries > 0 and sweep:brute_force:2000:t9
+            # Post-hoc timing sensitivity per Rule R3: exclude retries > 0 and sweep:brute_force:2000:t9
             clean_successes = [
                 r for r in successes
-                if r.get("retries", 0) == 0 and r.get("key") != "sweep:brute_force:2000:t9"
+                if int(_require_col(r, "retries", r_dir.name)) == 0
+                and _require_col(r, "key", r_dir.name) != "sweep:brute_force:2000:t9"
             ]
-            clean_tot_s_list = [float(r.get("metrics", {}).get("total_s", 0.0)) for r in clean_successes]
-            clean_short_s_list = [float(r.get("metrics", {}).get("shortlist_s", 0.0)) for r in clean_successes]
-            clean_dec_s_list = [float(r.get("metrics", {}).get("decide_s", 0.0)) for r in clean_successes]
+            clean_tot_s_list = [float(_require_col(r["metrics"], "total_s", r_dir.name)) for r in clean_successes]
+            clean_short_s_list = [float(_require_col(r["metrics"], "shortlist_s", r_dir.name)) for r in clean_successes]
+            clean_dec_s_list = [float(_require_col(r["metrics"], "decide_s", r_dir.name)) for r in clean_successes]
 
             size_total_s_clean_map[size_n] = clean_tot_s_list
             clean_tot_stats = compute_series_stats(clean_tot_s_list)
@@ -411,18 +453,23 @@ def generate_t2_sweep_cost_table(
                 "total_s_max": tot_stats["max"],
                 "total_s_ci_mean_low": tot_stats["ci_mean_low"],
                 "total_s_ci_mean_high": tot_stats["ci_mean_high"],
-                # Pre-registered components: shortlist_s and decide_s
+                # Pre-registered components: shortlist_s and decide_s with 95% bootstrap CIs
                 "shortlist_s_mean": short_stats["mean"],
                 "shortlist_s_median": short_stats["median"],
                 "shortlist_s_std": short_stats["std"],
                 "shortlist_s_min": short_stats["min"],
                 "shortlist_s_max": short_stats["max"],
+                "shortlist_s_ci_mean_low": short_stats["ci_mean_low"],
+                "shortlist_s_ci_mean_high": short_stats["ci_mean_high"],
                 "decide_s_mean": dec_stats["mean"],
                 "decide_s_median": dec_stats["median"],
                 "decide_s_std": dec_stats["std"],
                 "decide_s_min": dec_stats["min"],
                 "decide_s_max": dec_stats["max"],
-                # Post-hoc sensitivity timing (labelled "post-hoc, not pre-registered")
+                "decide_s_ci_mean_low": dec_stats["ci_mean_low"],
+                "decide_s_ci_mean_high": dec_stats["ci_mean_high"],
+                # Post-hoc sensitivity timing (labelled "post-hoc, not pre-registered") per Rule R3
+                "clean_exclusion_rule": "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)",
                 "clean_num_trials_post_hoc_not_preregistered": len(clean_successes),
                 "clean_total_s_mean_post_hoc_not_preregistered": clean_tot_stats["mean"],
                 "clean_total_s_median_post_hoc_not_preregistered": clean_tot_stats["median"],
@@ -434,52 +481,23 @@ def generate_t2_sweep_cost_table(
             }
             rows.append(row)
 
-        # Compute log-log OLS slope fits across the 6 sizes for this run
+        # Compute log-log OLS slope fits across sizes for this run per Rule R1
         if len(size_calls_map) >= 2:
             # 1. LLM calls slope fit
-            calls_slope, calls_ci_low, calls_ci_high, calls_cat, calls_r2 = bootstrap_slope_ci(size_calls_map)
+            _fit_metric_slopes(
+                strat, variant, "llm_calls", "pre-registered (all trials)", size_calls_map, slope_fit_rows
+            )
             # 2. total_s slope fit (pre-registered)
-            tot_slope, tot_ci_low, tot_ci_high, tot_cat, tot_r2 = bootstrap_slope_ci(size_total_s_map)
+            _fit_metric_slopes(
+                strat, variant, "total_s", "pre-registered (all trials)", size_total_s_map, slope_fit_rows
+            )
             # 3. total_s clean slope fit (post-hoc)
-            tot_clean_slope, tot_clean_ci_low, tot_clean_ci_high, tot_clean_cat, tot_clean_r2 = bootstrap_slope_ci(
-                size_total_s_clean_map
+            _fit_metric_slopes(
+                strat, variant, "total_s", "clean (post-hoc, not pre-registered)", size_total_s_clean_map, slope_fit_rows
             )
-
-            slope_fit_rows.append({
-                "strategy": strat,
-                "variant": variant,
-                "metric": "llm_calls",
-                "condition": "pre-registered (all trials)",
-                "slope": calls_slope,
-                "ci_95_low": calls_ci_low,
-                "ci_95_high": calls_ci_high,
-                "r_squared": calls_r2,
-                "flatness_category_D2": calls_cat,
-            })
-            slope_fit_rows.append({
-                "strategy": strat,
-                "variant": variant,
-                "metric": "total_s",
-                "condition": "pre-registered (all trials)",
-                "slope": tot_slope,
-                "ci_95_low": tot_ci_low,
-                "ci_95_high": tot_ci_high,
-                "r_squared": tot_r2,
-                "flatness_category_D2": tot_cat,
-            })
-            slope_fit_rows.append({
-                "strategy": strat,
-                "variant": variant,
-                "metric": "total_s",
-                "condition": "clean (post-hoc, not pre-registered)",
-                "slope": tot_clean_slope,
-                "ci_95_low": tot_clean_ci_low,
-                "ci_95_high": tot_clean_ci_high,
-                "r_squared": tot_clean_r2,
-                "flatness_category_D2": tot_clean_cat,
-            })
 
     if output_csv_path and rows:
         write_csv(output_csv_path, rows)
 
     return rows, slope_fit_rows
+
diff --git c/tests/test_analysis_pipeline.py w/tests/test_analysis_pipeline.py
index 920965f..8f3a9f8 100644
--- c/tests/test_analysis_pipeline.py
+++ w/tests/test_analysis_pipeline.py
@@ -1,24 +1,25 @@
 """
 test_analysis_pipeline.py — Unit and Integration Tests for Phase 4 Analysis Suite
 ================================================================================
-Implements tests for TASK ANALYSIS-002:
+Implements tests for TASK ANALYSIS-002-F:
 - Vectorized percentile bootstrap CI (D1)
 - Flatness classification into pre-registered bins (D2)
-- Log-log OLS slope fits with bootstrap CI and descriptive categories
-- Pareto dominance mechanics (D3, D5)
-- Failed-then-succeeded and retry accounting
-- Timing sensitivity columns excluding retries > 0 and sweep:brute_force:2000:t9 (Requirement 4)
-- Gate integration and fail-closed behavior (Requirement 1)
-- Synthetic fixture end-to-end execution of all tables (T1-T4, T2b) and figures (F1-F6)
-- Parity check: per-run numbers equal the validator's recomputation on the real accuracy directories (Requirement 5)
+- Log-log OLS slope fits with R1 zero-mean rule (NaN slope, undefined category, dropping resamples)
+- Pareto dominance mechanics per Rule R2 (< 0.025 indistinguishable; >= 0.025 dominance / trade-off)
+- Post-hoc timing sensitivity exclusion per Rule R3 (retries>0 and t9 peak trial excluded)
+- Gate integration: fail-closed on failure (exit 1, write nothing) and success without skip-gate
+- Table T3 header matching 18 validator fieldnames and trial count on 60-trial fixture
+- Strict accessor raising KeyError naming run and column
+- Source grep test verifying absence of "skip-gate", "/home/", and "1e-12" in scripts/analysis/*.py
+- Parity test with validator taking path from PHASE4_RESULTS_DIR (skipping if unset)
 """
 
 from __future__ import annotations
 
 import csv
 import json
-import shutil
-import tempfile
+import os
+import sys
 from pathlib import Path
 from typing import Any, Dict, List
 import numpy as np
@@ -38,6 +39,8 @@ from scripts.analysis.tables import (
     generate_t2_sweep_cost_table,
     generate_t3_inventory_table,
     generate_t4_sensitivity_table,
+    _require_col,
+    _fit_metric_slopes,
 )
 from scripts.analysis.figures import (
     plot_f1_calls_scaling,
@@ -47,7 +50,8 @@ from scripts.analysis.figures import (
     plot_f5_sensitivity_panels,
     plot_f6_cost_vs_accuracy,
 )
-from scripts.analysis.validate_runs import parse_raw_jsonl, recompute_metrics
+from scripts.analysis.validate_runs import parse_raw_jsonl, recompute_metrics, validate_all_runs
+from scripts.analysis.run_analysis import main as run_pipeline_main
 
 
 def test_bootstrap_ci_deterministic():
@@ -75,6 +79,7 @@ def test_flatness_classification():
     assert classify_slope_flatness(0.90) == "sub-linear"
     assert classify_slope_flatness(0.901) == "approximately linear"
     assert classify_slope_flatness(1.05) == "approximately linear"
+    assert classify_slope_flatness(float("nan")) == "undefined"
 
 
 def test_ols_log_log_slope():
@@ -91,35 +96,108 @@ def test_ols_log_log_slope():
     assert np.isclose(slope_flat, 0.0, atol=1e-5)
 
 
-def test_bootstrap_slope_ci_synthetic():
+def test_r1_zero_mean_undefined_and_all_positive():
+    """Rule R1: A log-log fit with any size whose mean is <= 0 or non-finite is UNDEFINED.
+
+    (NaN slope, no D2 category, no CI, category text "undefined (zero mean at n=...)").
+    Remove the 1e-12 clamp everywhere. If at least 3 sizes have positive mean,
+    emit one extra row labelled "exploratory (positive-mean sizes only)".
+    In bootstrap resamples drop any resample with a zero-mean size and report n_boot_used.
+    """
     sizes = [50, 100, 200, 500, 1000, 2000]
-    size_map: Dict[int, List[float]] = {}
-    for s in sizes:
-        # Linear calls = s
-        size_map[s] = [float(s)] * 10
 
-    point_slope, ci_low, ci_high, cat, r2 = bootstrap_slope_ci(size_map, n_resamples=500, seed=42)
-    assert np.isclose(point_slope, 1.0, atol=1e-5)
-    assert np.isclose(ci_low, 1.0, atol=1e-5)
-    assert np.isclose(ci_high, 1.0, atol=1e-5)
-    assert cat == "approximately linear"
+    # S2-like data: zero calls at n=50 and n=100, positive at 200, 500, 1000, 2000
+    s2_data: Dict[int, List[float]] = {
+        50: [0.0] * 5,
+        100: [0.0] * 5,
+        200: [2.0] * 5,
+        500: [5.0] * 5,
+        1000: [10.0] * 5,
+        2000: [20.0] * 5,
+    }
+
+    # Direct fit_log_log_slope test
+    emp_means = [float(np.mean(s2_data[s])) for s in sizes]
+    slope, intercept, r2 = fit_log_log_slope(sizes, emp_means)
+    assert np.isnan(slope)
+    assert np.isnan(intercept)
+    assert np.isnan(r2)
+
+    # bootstrap_slope_ci test
+    point_slope, ci_low, ci_high, cat, r2, n_boot = bootstrap_slope_ci(s2_data, n_resamples=500, seed=42)
+    assert np.isnan(point_slope)
+    assert np.isnan(ci_low)
+    assert np.isnan(ci_high)
+    assert np.isnan(r2)
+    assert cat == "undefined (zero mean at n=50, 100)"
+    assert n_boot == 0
+
+    # Test table slope row generation helper: emits main undefined row + extra exploratory row
+    slope_rows: List[Dict[str, Any]] = []
+    _fit_metric_slopes("embedding_threshold", "primary", "llm_calls", "pre-registered (all trials)", s2_data, slope_rows)
+    assert len(slope_rows) == 2
+    # Row 0: Pre-registered undefined
+    assert slope_rows[0]["condition"] == "pre-registered (all trials)"
+    assert np.isnan(slope_rows[0]["slope"])
+    assert np.isnan(slope_rows[0]["ci_95_low"])
+    assert slope_rows[0]["flatness_category_D2"] == "undefined (zero mean at n=50, 100)"
+    assert slope_rows[0]["min_trials_per_size"] == 5
+    assert slope_rows[0]["n_boot_used"] == 0
+    # Row 1: Exploratory positive-mean sizes only
+    assert slope_rows[1]["condition"] == "exploratory (positive-mean sizes only)"
+    assert not np.isnan(slope_rows[1]["slope"])
+    assert np.isclose(slope_rows[1]["slope"], 1.0, atol=1e-5)
+    assert slope_rows[1]["flatness_category_D2"] == "approximately linear"
+    assert slope_rows[1]["min_trials_per_size"] == 5
+    assert slope_rows[1]["n_boot_used"] == 10000
+
+    # Unchanged behaviour on all-positive data
+    pos_data = {s: [float(s)] * 5 for s in sizes}
+    pos_slope, pos_low, pos_high, pos_cat, pos_r2, pos_n_boot = bootstrap_slope_ci(pos_data, n_resamples=500, seed=42)
+    assert np.isclose(pos_slope, 1.0, atol=1e-5)
+    assert np.isclose(pos_low, 1.0, atol=1e-5)
+    assert np.isclose(pos_high, 1.0, atol=1e-5)
+    assert pos_cat == "approximately linear"
+    assert pos_n_boot == 500
 
 
-def test_dominance_evaluation():
-    # A has fewer calls and higher F1 (> 0.025 diff) -> A dominates B
-    pt_a = {"calls": 10.0, "f1": 0.55}
-    pt_b = {"calls": 20.0, "f1": 0.40}
-    assert evaluate_dominance(pt_a, pt_b) == "A dominates B"
+def test_r2_dominance_including_boundary():
+    """Rule R2: |F1 difference| < 0.025 => "not distinguishable (F1 within 0.025)", regardless of calls.
+
+    At or above 0.025: A dominates B if A has higher F1 and calls <= B's; otherwise "trade-off".
+    """
+    # 1. Strictly below 0.025 (|diff| = 0.010 and 0.024) -> not distinguishable even with calls advantage
+    pt_a = {"calls": 10.0, "f1": 0.500}
+    pt_b = {"calls": 100.0, "f1": 0.524}
+    assert evaluate_dominance(pt_a, pt_b) == "not distinguishable (F1 within 0.025)"
+    assert evaluate_dominance(pt_b, pt_a) == "not distinguishable (F1 within 0.025)"
 
-    # F1 difference is within 0.025 noise floor, but A has fewer calls -> A dominates on calls
     pt_c = {"calls": 10.0, "f1": 0.510}
-    pt_d = {"calls": 25.0, "f1": 0.520}  # diff = 0.010 <= 0.025
-    assert evaluate_dominance(pt_c, pt_d) == "A dominates B (calls advantage, F1 equivalent)"
+    pt_d = {"calls": 25.0, "f1": 0.520}  # diff = 0.010 < 0.025
+    assert evaluate_dominance(pt_c, pt_d) == "not distinguishable (F1 within 0.025)"
 
-    # Trade-off: A has fewer calls but B has significantly higher F1 (> 0.025)
-    pt_e = {"calls": 5.0, "f1": 0.40}
-    pt_f = {"calls": 50.0, "f1": 0.60}
-    assert evaluate_dominance(pt_e, pt_f) == "trade-off"
+    # 2. Boundary condition: EXACTLY 0.025
+    # A has higher F1 (+0.025) and fewer calls -> A dominates B
+    pt_e = {"calls": 10.0, "f1": 0.525}
+    pt_f = {"calls": 20.0, "f1": 0.500}
+    assert evaluate_dominance(pt_e, pt_f) == "A dominates B"
+
+    # A has higher F1 (+0.025) but more calls -> trade-off
+    pt_g = {"calls": 30.0, "f1": 0.525}
+    pt_h = {"calls": 20.0, "f1": 0.500}
+    assert evaluate_dominance(pt_g, pt_h) == "trade-off"
+
+    # Inverse boundary: B has higher F1 (+0.025) and fewer calls -> B dominates A
+    assert evaluate_dominance(pt_f, pt_e) == "B dominates A"
+
+    # 3. Strictly above 0.025 (e.g. diff = 0.050)
+    pt_i = {"calls": 10.0, "f1": 0.600}
+    pt_j = {"calls": 20.0, "f1": 0.500}
+    assert evaluate_dominance(pt_i, pt_j) == "A dominates B"
+
+    pt_k = {"calls": 50.0, "f1": 0.600}
+    pt_l = {"calls": 10.0, "f1": 0.500}
+    assert evaluate_dominance(pt_k, pt_l) == "trade-off"
 
 
 def create_mock_run_directory(
@@ -130,7 +208,7 @@ def create_mock_run_directory(
     records: List[Dict[str, Any]],
     config: Dict[str, Any],
 ) -> Path:
-    """Helper to create a hermetic synthetic run directory with manifest, config, raw.jsonl, and summary.csv."""
+    """Helper to create a synthetic run directory with manifest, config, raw.jsonl, and summary.csv."""
     run_dir = root / run_name
     run_dir.mkdir(parents=True, exist_ok=True)
 
@@ -186,7 +264,6 @@ def create_mock_run_directory(
     with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
         writer = csv.DictWriter(f, fieldnames=summary_fields)
         writer.writeheader()
-        # Group by corpus_or_size
         sizes = set(str(r.get("corpus", r.get("size", "50"))) for r in records if r.get("status") == "success")
         for s in sorted(sizes):
             writer.writerow({
@@ -237,16 +314,13 @@ def create_mock_run_directory(
     return run_dir
 
 
-def test_post_hoc_sensitivity_exclusion(tmp_path: Path):
-    """Verifies Requirement 4: trials with retries > 0 and the single trial
+def test_r3_post_hoc_sensitivity_exclusion(tmp_path: Path):
+    """Rule R3: trials with retries > 0 and the single trial sweep:brute_force:2000:t9
 
-    sweep:brute_force:2000:t9 are excluded from the post-hoc timing sensitivity columns.
+    are excluded from the post-hoc timing sensitivity columns.
+    clean_exclusion_rule column records exact exclusion rule.
     """
     records = []
-    # 10 trials for size 2000 of brute force:
-    # trial 0..7: normal success (retries=0, total_s=100.0)
-    # trial 8: success with retries=2, total_s=250.0 (should be excluded)
-    # trial 9 (key sweep:brute_force:2000:t9): retries=0, total_s=300.0 (should be excluded)
     for i in range(8):
         records.append({
             "key": f"sweep:brute_force:2000:t{i}",
@@ -287,20 +361,174 @@ def test_post_hoc_sensitivity_exclusion(tmp_path: Path):
     assert row["num_trials"] == 10
     assert np.isclose(row["total_s_mean"], 135.0)
 
-    # Post-hoc clean excludes trial 8 (retries=2) and trial 9 (key sweep:brute_force:2000:t9)
-    # Remaining trials = 8, mean = 100.0 exactly
+    # Post-hoc clean excludes trial 8 (retries=2) and trial 9 (sweep:brute_force:2000:t9)
     assert row["clean_num_trials_post_hoc_not_preregistered"] == 8
     assert np.isclose(row["clean_total_s_mean_post_hoc_not_preregistered"], 100.0)
     assert np.isclose(row["clean_total_s_max_post_hoc_not_preregistered"], 100.0)
 
+    # Check clean_exclusion_rule column
+    expected_rule = "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)"
+    assert row["clean_exclusion_rule"] == expected_rule
 
-def test_synthetic_pipeline_end_to_end(tmp_path: Path):
-    """End-to-end execution of the full analysis pipeline on synthetic data."""
+
+def test_strict_accessor_raises_on_missing_column(tmp_path: Path):
+    """Verifies that _require_col raises KeyError naming run and column."""
+    with pytest.raises(KeyError) as exc_info:
+        _require_col({"a": 1}, "missing_col", "run_xyz")
+    assert "run_xyz" in str(exc_info.value)
+    assert "missing_col" in str(exc_info.value)
+
+    with pytest.raises(KeyError) as exc_info_empty:
+        _require_col({"col_b": ""}, "col_b", "run_xyz")
+    assert "run_xyz" in str(exc_info_empty.value)
+    assert "col_b" in str(exc_info_empty.value)
+
+    # Verify generate_t1_accuracy_table fails strictly on missing required column
+    run_dir = tmp_path / "bad_acc_run"
+    run_dir.mkdir(parents=True)
+    (run_dir / "strategy_config.json").write_text(json.dumps({"strategy": "brute_force"}), encoding="utf-8")
+    with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
+        writer = csv.DictWriter(f, fieldnames=["corpus_or_size", "num_trials"])
+        writer.writeheader()
+        writer.writerow({"corpus_or_size": "DSA_gold_standard_MEKG", "num_trials": "29"})
+
+    with pytest.raises(KeyError) as exc_info_table:
+        generate_t1_accuracy_table([run_dir])
+    assert "bad_acc_run" in str(exc_info_table.value)
+
+
+def test_t3_header_and_trial_count(tmp_path: Path):
+    """Verifies Table T3 header equals the 18 validator fieldnames and trials == 60 on a 60-trial fixture."""
+    expected_18_fields = [
+        "run", "strategy", "config", "mode", "commit", "libraries_hash",
+        "trials", "calls", "failed", "failed_then_succeeded", "still_failed", "retries", "status",
+        "manifest_sha256", "config_sha256", "raw_sha256", "summary_sha256", "dir_sha256"
+    ]
+
+    # Build 60-trial sweep fixture (6 sizes x 10 trials)
+    records = []
+    for s in [50, 100, 200, 500, 1000, 2000]:
+        for t in range(10):
+            records.append({
+                "key": f"sweep:brute_force:{s}:t{t}",
+                "size": s,
+                "status": "success",
+                "retries": 0,
+                "metrics": {"total_s": 5.0, "shortlist_s": 0.01, "decide_s": 4.99, "llm_calls": s},
+            })
+
+    run_dir = create_mock_run_directory(
+        tmp_path,
+        "sweep_brute_force",
+        "brute_force",
+        "sweep",
+        records,
+        config={},
+    )
+
+    passed, results, t3_csv_str = validate_all_runs(tmp_path)
+    header_line = t3_csv_str.splitlines()[0]
+    actual_fields = header_line.split(",")
+    assert actual_fields == expected_18_fields
+
+    t3_rows = generate_t3_inventory_table(t3_csv_str)
+    assert len(t3_rows) == 1
+    assert int(t3_rows[0]["trials"]) == 60
+    assert "total_trials" not in t3_rows[0]
+
+
+def test_gate_failure_aborts_and_writes_nothing(tmp_path: Path, monkeypatch):
+    """Verifies that gate failure exits 1 and writes no output files."""
+    results_dir = tmp_path / "results"
+    output_dir = tmp_path / "output"
+    results_dir.mkdir()
+
+    # Monkeypatch validate_all_runs to fail
+    def mock_validate_fail(*args, **kwargs):
+        return (False, [{"run_dir": "failing_run", "passed": False, "errors": ["Mock error"]}], "")
+
+    import scripts.analysis.run_analysis as ra
+    monkeypatch.setattr(ra, "validate_all_runs", mock_validate_fail)
+
+    test_argv = [
+        "run_analysis.py",
+        "--results-dir", str(results_dir),
+        "--output-dir", str(output_dir),
+    ]
+    monkeypatch.setattr(sys, "argv", test_argv)
+
+    rc = run_pipeline_main()
+    assert rc == 1
+    assert not output_dir.exists()
+
+
+def test_gate_success_and_run_info(tmp_path: Path, monkeypatch):
+    """Verifies that gate success writes RUN_INFO.txt with all required fields."""
+    results_dir = tmp_path / "results"
+    output_dir = tmp_path / "output"
+    results_dir.mkdir()
+
+    # Create dummy primary runs for F3 caps
+    create_mock_run_directory(
+        results_dir,
+        "sweep_ann_retrieval_k10_ef128",
+        "ann_retrieval",
+        "sweep",
+        [{"key": "sweep:ann_retrieval:50:t0", "size": 50, "status": "success", "retries": 0, "metrics": {"total_s": 1.0, "shortlist_s": 0.01, "decide_s": 0.99, "llm_calls": 10}}],
+        config={"k": 10, "ef_search": 128},
+    )
+    create_mock_run_directory(
+        results_dir,
+        "sweep_bounded_bucket_smin5_smax10_nb12",
+        "bounded_bucket",
+        "sweep",
+        [{"key": "sweep:bounded_bucket:50:t0", "size": 50, "status": "success", "retries": 0, "metrics": {"total_s": 1.0, "shortlist_s": 0.01, "decide_s": 0.99, "llm_calls": 10}}],
+        config={"s_min": 5, "s_max": 10, "num_hyperplanes": 12},
+    )
+
+    mock_t3_csv = (
+        "run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,failed_then_succeeded,still_failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256\n"
+        'sweep_ann_retrieval_k10_ef128,ann_retrieval,"{}",sweep,3323bfb,h1,1,10,0,0,0,0,PASS,m1,c1,r1,s1,d1\n'
+    )
+
+    import scripts.analysis.run_analysis as ra
+    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], mock_t3_csv))
+
+    test_argv = [
+        "run_analysis.py",
+        "--results-dir", str(results_dir),
+        "--output-dir", str(output_dir),
+        "--src-diff-clean",
+    ]
+    monkeypatch.setattr(sys, "argv", test_argv)
+
+    rc = run_pipeline_main()
+    assert rc == 0
+    assert (output_dir / "RUN_INFO.txt").exists()
+
+    run_info = (output_dir / "RUN_INFO.txt").read_text(encoding="utf-8")
+    assert "argv:" in run_info
+    assert "results_dir:" in run_info
+    assert "git_commit:" in run_info
+    assert "pipeline_modules_sha256:" in run_info
+    assert "validate_runs.py:" in run_info
+    assert "run_analysis.py:" in run_info
+    assert "tables.py:" in run_info
+    assert "figures.py:" in run_info
+    assert "stats.py:" in run_info
+    assert "bootstrap.py:" in run_info
+    assert "style.py:" in run_info
+    assert "hashes_file: NOT SUPPLIED" in run_info
+    assert "src_diff_clean: True" in run_info
+    assert "overall_gate_status: PASS" in run_info
+
+
+def test_end_to_end_without_skip_gate(tmp_path: Path, monkeypatch):
+    """End-to-end execution of the full analysis pipeline on synthetic data WITHOUT skip-gate."""
     results_dir = tmp_path / "results"
     output_dir = tmp_path / "output"
     results_dir.mkdir()
 
-    # Create 1 accuracy run and 1 sweep run
     acc_records = [
         {
             "key": f"acc:ann_retrieval:DSA_gold_standard_MEKG:node_{i}",
@@ -321,6 +549,26 @@ def test_synthetic_pipeline_end_to_end(tmp_path: Path):
         config={"k": 10, "ef_search": 128},
     )
 
+    acc_bf_records = [
+        {
+            "key": f"acc:brute_force:DSA_gold_standard_MEKG:node_{i}",
+            "corpus": "DSA_gold_standard_MEKG",
+            "status": "success",
+            "retries": 0,
+            "metrics": {"total_s": 15.0, "shortlist_s": 0.0, "decide_s": 14.99, "llm_calls": 28},
+            "score": {"tp": 2, "fp": 1, "fn": 1, "precision": 0.66, "recall": 0.66, "f1": 0.66, "shortlist_hits": 28, "gold_neighbours": 3, "shortlist_recall": 1.0},
+        }
+        for i in range(29)
+    ]
+    create_mock_run_directory(
+        results_dir,
+        "accuracy_brute_force",
+        "brute_force",
+        "accuracy",
+        acc_bf_records,
+        config={},
+    )
+
     sweep_records = []
     for s in [50, 100, 200, 500, 1000, 2000]:
         for t in range(10):
@@ -339,26 +587,37 @@ def test_synthetic_pipeline_end_to_end(tmp_path: Path):
         sweep_records,
         config={"k": 10, "ef_search": 128},
     )
+    create_mock_run_directory(
+        results_dir,
+        "sweep_bounded_bucket_smin5_smax10_nb12",
+        "bounded_bucket",
+        "sweep",
+        sweep_records,
+        config={"s_min": 5, "s_max": 10, "num_hyperplanes": 12},
+    )
 
-    from scripts.analysis.run_analysis import main as run_pipeline_main
-    import sys
+    mock_t3_csv = (
+        "run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,failed_then_succeeded,still_failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256\n"
+        'accuracy_ann_retrieval_k10_ef128,ann_retrieval,"{}",accuracy,3323bfb,h1,29,290,0,0,0,0,PASS,m1,c1,r1,s1,d1\n'
+        'accuracy_brute_force,brute_force,"{}",accuracy,3323bfb,h1,29,812,0,0,0,0,PASS,m0,c0,r0,s0,d0\n'
+        'sweep_ann_retrieval_k10_ef128,ann_retrieval,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m2,c2,r2,s2,d2\n'
+        'sweep_bounded_bucket_smin5_smax10_nb12,bounded_bucket,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m3,c3,r3,s3,d3\n'
+    )
+
+    import scripts.analysis.run_analysis as ra
+    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], mock_t3_csv))
 
-    # Execute pipeline via main with --skip-gate (since synthetic commit hashes aren't in git)
     test_argv = [
         "run_analysis.py",
         "--results-dir", str(results_dir),
         "--output-dir", str(output_dir),
-        "--skip-gate",
     ]
-    old_argv = sys.argv
-    try:
-        sys.argv = test_argv
-        rc = run_pipeline_main()
-        assert rc == 0
-    finally:
-        sys.argv = old_argv
+    monkeypatch.setattr(sys, "argv", test_argv)
 
-    # Check generated tables
+    rc = run_pipeline_main()
+    assert rc == 0
+
+    # Verify generated tables
     assert (output_dir / "tables" / "T1_accuracy_benchmark.csv").exists()
     assert (output_dir / "tables" / "T1_accuracy_benchmark.md").exists()
     assert (output_dir / "tables" / "T2_sweep_cost_summary.csv").exists()
@@ -370,7 +629,7 @@ def test_synthetic_pipeline_end_to_end(tmp_path: Path):
     assert (output_dir / "tables" / "T4_sensitivity_metrics.csv").exists()
     assert (output_dir / "tables" / "T4_sensitivity_metrics.md").exists()
 
-    # Check generated figures (both PDF, PNG, and CSV)
+    # Verify generated figures
     for fig_name in [
         "F1_calls_scaling",
         "F2_wallclock_scaling",
@@ -383,27 +642,48 @@ def test_synthetic_pipeline_end_to_end(tmp_path: Path):
         assert (output_dir / "figures" / f"{fig_name}.png").exists()
         assert (output_dir / "figures" / f"{fig_name}.csv").exists()
 
+    # Verify F6 dominance files
+    assert (output_dir / "figures" / "F6_dominance.csv").exists()
+    assert (output_dir / "figures" / "F6_dominance.md").exists()
+
+
+def test_source_grep_forbidden_patterns():
+    """Verifies that 'skip-gate', '/home/', and '1e-12' are absent from scripts/analysis/*.py."""
+    repo_root = Path(__file__).resolve().parent.parent
+    analysis_dir = repo_root / "scripts" / "analysis"
+    py_files = sorted(list(analysis_dir.glob("*.py")))
+    assert len(py_files) >= 6
+
+    forbidden = ["skip-gate", "/home/", "1e-12"]
+
+    for pf in py_files:
+        content = pf.read_text(encoding="utf-8")
+        for pattern in forbidden:
+            assert pattern not in content, f"Forbidden pattern '{pattern}' found in {pf.name}"
+
 
 def test_parity_with_validator_on_real_accuracy_directories():
     """Requirement 5: Test that pipeline numbers equal validator recomputations
 
-    directly on the real accuracy directories.
+    directly on real accuracy directories from PHASE4_RESULTS_DIR (skips if unset).
     """
-    real_results_path = Path("/home/lukexodus/projects/llm-graph-insertion-complexity/results")
+    res_env = os.environ.get("PHASE4_RESULTS_DIR")
+    if not res_env:
+        pytest.skip("PHASE4_RESULTS_DIR environment variable is unset")
+
+    real_results_path = Path(res_env).resolve()
     if not real_results_path.exists():
-        pytest.skip("Real results directory not present on this host")
+        pytest.skip(f"PHASE4_RESULTS_DIR path '{real_results_path}' does not exist")
 
     acc_dirs = sorted([d for d in real_results_path.iterdir() if d.is_dir() and d.name.startswith("accuracy_") and (d / "manifest.json").exists()])
     if not acc_dirs:
-        pytest.skip("No real accuracy directories found")
+        pytest.skip(f"No accuracy directories found in '{real_results_path}'")
 
     t1_rows = generate_t1_accuracy_table(acc_dirs)
     assert len(t1_rows) == 24  # 12 configurations x 2 corpora
 
-    # Map T1 rows by (run_strategy, variant, corpus)
     t1_map = {(r["strategy"], r["variant"], r["corpus"]): r for r in t1_rows}
 
-    # Cross-check each accuracy run directly against validator recompute_metrics
     for acc_dir in acc_dirs:
         raw_path = acc_dir / "raw.jsonl"
         sidecar_path = acc_dir / "strategy_config.json"
@@ -411,7 +691,7 @@ def test_parity_with_validator_on_real_accuracy_directories():
         strat = strat_cfg.get("strategy")
         variant = extract_variant_label(acc_dir.name)
 
-        records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_path)
+        records, is_resumed, _, key_records = parse_raw_jsonl(raw_path)
         val_metrics = recompute_metrics(records, "accuracy")
 
         for corpus, expected in val_metrics.items():
@@ -419,21 +699,12 @@ def test_parity_with_validator_on_real_accuracy_directories():
             assert key in t1_map, f"Missing {key} in Table T1"
             t1_row = t1_map[key]
 
-            # 1. Number of trials and successes
             assert t1_row["num_trials"] == expected["num_trials"]
             assert t1_row["num_success"] == expected["num_success"]
-
-            # 2. LLM calls mean
             assert np.isclose(t1_row["llm_calls_mean"], expected["llm_calls_mean"], atol=1e-5)
-
-            # 3. Micro F1, Precision, Recall
             assert np.isclose(t1_row["f1_micro"], expected["f1_micro"], atol=1e-5)
             assert np.isclose(t1_row["precision_micro"], expected["precision_micro"], atol=1e-5)
             assert np.isclose(t1_row["recall_micro"], expected["recall_micro"], atol=1e-5)
-
-            # 4. Shortlist recall micro
             assert np.isclose(t1_row["shortlist_recall_micro"], expected["shortlist_recall_micro"], atol=1e-5)
-
-            # 5. Macro F1
             if expected["f1_macro"] is not None:
                 assert np.isclose(t1_row["f1_macro"], expected["f1_macro"], atol=1e-5)

```
