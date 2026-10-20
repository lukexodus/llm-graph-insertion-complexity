# ANALYSIS-002: Implementation and Wiring of Phase 4 Empirical Analysis Pipeline

## 1. Independence Certification and Identification

- **Task ID**: `ANALYSIS-002`
- **Agent Name**: `gemini`
- **Session ID**: `26156499-0953-4f34-b42f-1cf073f8d16e`
- **Exact Model Label**: `Gemini 3.8 Flash (Medium)`
- **Independence Certification**: Confirmed independent. This session is **NOT** any of the excluded sessions:
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`
  - `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
  - `f4b13de1-a057-445e-a788-0523b774b94d` (ANALYSIS-001 author session)
  - `562e3bc6-c12a-4372-85af-70eb9ecebfc7` (ANALYSIS-001-R session)
  - `f339a846-e963-4b8f-a62e-4090862002e7`
  - `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2` (ANALYSIS-001-F author session)
  - `c143398c-85ce-4b37-b9ae-1f4bc1a9283d` (ANALYSIS-001-G session)
  - The `DOC-011` session
  - Any session starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.
- **Dedicated Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002`
- **Branch**: `task/ANALYSIS-002`
- **Base Commit**: `48037e3` (`docs: add ANALYSIS-001-G independent review of ANALYSIS-001-F validator`)

---

## 2. Executive Summary

TASK ANALYSIS-002 completed and wired the Phase 4 empirical analysis pipeline into the repository. The pipeline:
1. Imports the fail-closed validation gate directly from `scripts/analysis/validate_runs.py` in the repo using its real 3-argument signature (`results_dir`, `src_diff_clean=False`, `hashes_path=None`), exiting with code 1 if any check fails.
2. Contains zero hardcoded machine paths; `--results-dir` and `--output-dir` are explicit CLI arguments. Outputs are written outside the repo and are not tracked.
3. Implements all required figures and tables from Phase 4 Analysis Plan Sections 3 to 6:
   - **Table T1**: Accuracy Benchmark Matrix (12 accuracy configurations x 2 corpora, reporting micro/macro P, R, F1, shortlist recall, random baseline recall, and retry metrics).
   - **Table T2**: Sweep Cost Summary (12 sweep configurations across sizes, reporting distribution metrics and 95% percentile bootstrap CIs for calls, `total_s`, `shortlist_s`, and `decide_s`).
   - **Table T2b / Slope Fits**: Log-log OLS slope fits of $\log(\text{mean cost})$ on $\log(n)$ across $\{50, 100, 200, 500, 1000, 2000\}$ with 95% bootstrap slope CIs and D2 descriptive flatness categories ("approximately flat", "sub-linear", "approximately linear").
   - **Table T3**: Empirical Run Inventory (all 24 runs with commit, library versions, call bounds, trial counts, failure partitions, and directory SHA256 hashes).
   - **Table T4**: Sensitivity Variant Metrics and unjudged predictions.
   - **Figures F1 to F6**: Figures rendered as vector PDF, PNG, and underlying CSVs. Figures F1, F2 (with shortlist/decide split panel), and F3 (linear scale with cap reference line) implemented per plan lines 75-77.
4. Fully implements Requirement 4: reports `failed_then_succeeded_keys` and `n_with_retries`, and adds post-hoc timing sensitivity columns to Table T2 that exclude trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9`, labelled explicitly `"post-hoc, not pre-registered"`.
5. Accompanied by a comprehensive test suite (`tests/test_analysis_pipeline.py`, 9 tests passing) verifying bootstrap determinism, slope fits, dominance mechanics, post-hoc exclusions, end-to-end synthetic pipeline execution, and exact parity between pipeline metrics and validator recomputations (`validate_runs.py::recompute_metrics`) on the real accuracy directories.
6. Reserved and appended decision **[D-85]** only (D-84 reserved for DOC-011).

---

## 3. Files Read by the Pipeline

The pipeline reads the following artifacts from each run directory under `--results-dir`:
1. `manifest.json`: Run ID, mode, strategy, git commit hash, git dirty status, and environment library versions.
2. `strategy_config.json`: Strategy name, parameter configuration dictionary (`k`, `ef_search`, `s_min`, `s_max`, `theta`), seed, and embedder thread pins/provenance.
3. `summary.csv`: Pre-aggregated trial summary metrics.
4. `raw.jsonl`: Trial-level execution records containing trial keys, completion status, call counts, timing breakdown (`total_s`, `shortlist_s`, `decide_s`, `apply_s`, `update_s`), scoring evaluation dictionaries (`tp`, `fp`, `fn`, `precision`, `recall`, `f1`, `shortlist_hits`, `gold_neighbours`), and retry attempt metadata.

---

## 4. Verbatim Pipeline Execution Output

Execution command on the full 24-run experimental dataset:
```bash
python3 scripts/analysis/run_analysis.py \
  --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results \
  --output-dir /tmp/phase4_analysis_output \
  --src-diff-clean
```

### Verbatim Console Output
```text
================================================================================
PHASE 4 EMPIRICAL ANALYSIS PIPELINE
Results Directory: /home/lukexodus/projects/llm-graph-insertion-complexity/results
Output Directory:  /tmp/phase4_analysis_output
================================================================================

>>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...

[OK] Validation gate passed 100%. Proceeding with analysis.

Discovered: 24 total runs (12 accuracy, 12 sweep)

>>> STEP 2: Generating Table T3 (Run Inventory)...
    Saved: /tmp/phase4_analysis_output/tables/T3_run_inventory.csv and .md (24 entries)

>>> STEP 3: Generating Accuracy Tables (T1, T4)...
    Saved: /tmp/phase4_analysis_output/tables/T1_accuracy_benchmark.csv and .md (24 rows)
    Saved: /tmp/phase4_analysis_output/tables/T4_sensitivity_metrics.csv and .md (24 rows)

>>> STEP 4: Generating Accuracy Figures (F4, F5, F6)...
    Saved: /tmp/phase4_analysis_output/figures/F4_accuracy_by_strategy.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output/figures/F5_sensitivity_panels.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output/figures/F6_cost_vs_accuracy_dominance.pdf (.png, .csv)

>>> STEP 5: Generating Sweep Cost Table (T2) and Slope Fits...
    Saved: /tmp/phase4_analysis_output/tables/T2_sweep_cost_summary.csv and .md (72 rows)
    Saved: /tmp/phase4_analysis_output/tables/T2_slope_fits.csv and .md (36 fits)

>>> STEP 6: Generating Sweep Figures (F1, F2, F3)...
    Saved: /tmp/phase4_analysis_output/figures/F1_calls_scaling.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output/figures/F2_wallclock_scaling.pdf (.png, .csv)
    Saved: /tmp/phase4_analysis_output/figures/F3_premise_check.pdf (.png, .csv)

================================================================================
PHASE 4 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY (100% PASS).
================================================================================
```

---

## 5. Cross-Check Against Validator Recomputation (Five Numbers per Table)

All numbers produced by the pipeline were cross-checked directly against the validator's recomputations (`validate_runs.py::recompute_metrics`) from the raw trial records. Parity was verified with zero discrepancy ($0.0000$ difference).

### 5.1 Table T1 Cross-Check (Accuracy Benchmark Matrix)
| Run / Corpus | Metric | Pipeline Value | Validator Recomputed Value | Discrepancy |
|---|---|---|---|---|
| `accuracy_ann_retrieval_k10_ef128` (DSA) | `f1_micro` | `0.5111` | `0.5111` | $0.0000$ |
| `accuracy_ann_retrieval_k10_ef128` (Metacademy) | `f1_micro` | `0.2941` | `0.2941` | $0.0000$ |
| `accuracy_brute_force` (DSA) | `recall_micro` | `0.6111` | `0.6111` | $0.0000$ |
| `accuracy_embedding_threshold_theta0.6` (DSA) | `llm_calls_mean` | `0.9655` | `0.9655` | $0.0000$ |
| `accuracy_bounded_bucket_smin5_smax10_nb12` (Metacademy) | `shortlist_recall_micro` | `0.1468` | `0.1468` | $0.0000$ |

### 5.2 Table T2 Cross-Check (Sweep Cost Summary)
| Run / Size ($n$) | Metric | Pipeline Value | Summary / Raw Value | Discrepancy |
|---|---|---|---|---|
| `sweep_brute_force` ($n=50$) | `llm_calls_mean` | `50.0000` | `50.0000` | $0.0000$ |
| `sweep_brute_force` ($n=2000$) | `total_s_mean` | `1713.0988` | `1713.0988` | $0.0000$ |
| `sweep_ann_retrieval_k10_ef128` ($n=1000$) | `total_s_median` | `7.8447` | `7.8447` | $0.0000$ |
| `sweep_bounded_bucket_smin5_smax10_nb12` ($n=500$) | `decide_s_mean` | `5.9919` | `5.9919` | $0.0000$ |
| `sweep_embedding_threshold_theta0.6` ($n=2000$) | `total_s_mean` | `0.8174` | `0.8174` | $0.0000$ |

### 5.3 Table T3 Cross-Check (Run Inventory)
| Run Directory | Metric | Pipeline Value | Validator Inventory Value | Discrepancy |
|---|---|---|---|---|
| `accuracy_brute_force` | `total_calls` | `5012` | `5012` | $0$ |
| `accuracy_brute_force` | `failed_then_succeeded_count` | `5` | `5` | $0$ |
| `sweep_brute_force` | `total_calls` | `38500` | `38500` | $0$ |
| `sweep_brute_force` | `failed_then_succeeded_count` | `41` | `41` | $0$ |
| `sweep_bounded_bucket_smin10_smax20_nb12`| `retries` | `67` | `67` | $0$ |

### 5.4 Table T4 Cross-Check (Sensitivity Metrics)
| Run / Corpus | Metric | Pipeline Value | Validator Summary Value | Discrepancy |
|---|---|---|---|---|
| `accuracy_brute_force` (DSA) | `f1_micro_sensitivity` | `0.5410` | `0.5410` | $0.0000$ |
| `accuracy_ann_retrieval_k10_ef128` (DSA) | `precision_micro_sensitivity` | `0.6389` | `0.6389` | $0.0000$ |
| `accuracy_bounded_bucket_smin10_smax20_nb12` (DSA) | `recall_micro_sensitivity` | `0.4074` | `0.4074` | $0.0000$ |
| `accuracy_embedding_threshold_theta0.4` (DSA) | `f1_micro_sensitivity` | `0.4873` | `0.4873` | $0.0000$ |
| `accuracy_bounded_bucket_smin2_smax5_nb12` (DSA) | `unjudged_predictions_total`| `0` | `0` | $0$ |

---

## 6. Post-Hoc Timing Sensitivity Analysis (Requirement 4)

In `sweep_brute_force` ($n=2000$):
- **Pre-registered (all 10 trials)**:
  - $N = 10$ trials
  - `total_s_mean`: `1713.0988 s`
  - `total_s_max`: `1763.6963 s`
  - `total_s_std`: `31.6814 s`
- **Post-hoc clean sensitivity (excluding retries > 0 and trial `sweep:brute_force:2000:t9`)**:
  - $N_{\text{clean}} = 8$ trials (trial 8 excluded due to retries=2; trial 9 excluded per Requirement 4)
  - `clean_total_s_mean_post_hoc_not_preregistered`: `1709.8927 s`
  - `clean_total_s_max_post_hoc_not_preregistered`: `1748.0415 s`
  - `clean_total_s_std_post_hoc_not_preregistered`: `28.7097 s`
- **Impact**: Removing the protocol retry and the transient header failure in `sweep:brute_force:2000:t9` reduces the observed latency outlier max from `1763.70 s` to `1748.04 s`, with mean latency dropping by `3.21 s`.

---

## 7. Test Suite Summary

### 7.1 Pipeline Test Suite (`tests/test_analysis_pipeline.py`)
```bash
pytest tests/test_analysis_pipeline.py -v
```
Results: **9 passed in 33.00s**:
- `test_bootstrap_ci_deterministic`: Passed (deterministic bounds with fixed seed)
- `test_bootstrap_empty_and_single_point`: Passed (clean NaN and single-point handling)
- `test_flatness_classification`: Passed (D2 boundary checks: 0.099 flat, 0.10 sub-linear, 0.901 linear)
- `test_ols_log_log_slope`: Passed (slope 1.0 on linear costs, 0.0 on flat costs)
- `test_bootstrap_slope_ci_synthetic`: Passed (bootstrap OLS slope estimation on synthetic matrix)
- `test_dominance_evaluation`: Passed (D3/D5 Pareto dominance and 0.025 equivalence band)
- `test_post_hoc_sensitivity_exclusion`: Passed (Requirement 4 exclusion of retries>0 and brute_force:2000:t9)
- `test_synthetic_pipeline_end_to_end`: Passed (end-to-end execution producing all 5 tables and 6 figures)
- `test_parity_with_validator_on_real_accuracy_directories`: Passed (exact parity across all 12 real accuracy directories)

### 7.2 Validator Test Suite (`tests/test_analysis_validate_runs.py`)
```bash
pytest tests/test_analysis_validate_runs.py
```
Results: **27 passed in 1.64s** (100% pass rate, zero regression).

---

## 8. Reserved Decision Log Entry [D-85]

Appended to `docs/decisions/decision-log.md` (D-84 left reserved for DOC-011):

```markdown
**[D-85]** Phase 4 empirical analysis pipeline implementation, validation gate integration, and post-hoc timing sensitivity accounting (ANALYSIS-002):
(1) Pipeline architecture: Implemented the repository-native empirical analysis pipeline under `scripts/analysis/{run_analysis,tables,figures,stats,bootstrap,style}.py` driven entirely by CLI arguments (`--results-dir`, `--output-dir`, `--src-diff-clean`, `--hashes`), free of hardcoded paths.
(2) Validation gate integration: `run_analysis.py` imports `validate_all_runs` from the repo's `scripts/analysis/validate_runs.py` using its real 3-argument signature (`results_dir`, `src_diff_clean=False`, `hashes_path=None`) and fails closed on validation failure (exit code 1), strictly upholding Section 1 Rule 2 and Section 2 of the frozen Analysis Plan.
(3) Figures and tables:
  (a) Tables T1 (accuracy benchmark), T2 (sweep cost summary), T3 (run inventory), T4 (sensitivity metrics), and T2b (slope fits) generated in both CSV and Markdown formats.
  (b) T2 reports mean, median, SD, min, max, and 95% percentile bootstrap CIs (10,000 resamples, fixed seed 42 per D1) for `llm_calls`, `total_s`, `shortlist_s`, and `decide_s`.
  (c) Log-log OLS regressions fit $\log(\text{mean cost})$ on $\log(n)$ across the six graph sizes $\{50, 100, 200, 500, 1000, 2000\}$ with 95% bootstrap slope CIs (resampling trials within size) and classified into D2 descriptive bins (<0.1 "approximately flat", 0.1–0.9 "sub-linear", >0.9 "approximately linear").
  (d) Figures F1 (calls scaling), F2 (wall-clock total and shortlist/decide split), F3 (premise check for Strategies 3 and 4 against theoretical caps), F4 (accuracy comparison), F5 (sensitivity panels), and F6 (cost vs accuracy with D3/D5 Pareto dominance) generated as vector PDF, PNG, and underlying CSVs.
(4) Post-hoc timing sensitivity accounting (Requirement 4):
  (a) Reported `failed_then_succeeded_count`, `failed_then_succeeded_keys`, and `n_with_retries` across all tables.
  (b) Added dedicated timing sensitivity columns to Table T2 (`clean_total_s_mean_post_hoc_not_preregistered`, `clean_total_s_median_post_hoc_not_preregistered`, etc.) that explicitly exclude all trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9`, labelled "post-hoc, not pre-registered".
(5) Test suite and parity verification: Implemented comprehensive unit, integration, and parity test suite (`tests/test_analysis_pipeline.py`, 9 tests passing). Verified exact numerical parity between pipeline outputs and validator recomputations (`validate_runs.py::recompute_metrics`) across all 12 accuracy configurations.
Reasoning: completes, hardens, and wires the Phase 4 empirical analysis pipeline into the repository, enforcing the pre-registered Analysis Plan [D-79], Decisions D1–D6, and post-hoc retry sensitivity accounting without altering raw experiment outputs. Affects: `scripts/analysis/`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
```
