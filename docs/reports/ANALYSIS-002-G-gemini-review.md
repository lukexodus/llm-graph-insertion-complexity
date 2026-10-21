# Independent Review Report: ANALYSIS-002-G

- **Session ID**: `7e5d65e7-fe39-4644-bf8c-58c970c70313`
- **Model Label**: Gemini 3.8 Flash (Medium)
- **Base Commit**: `f5e085d774d59afc3b256a586e8cb8943cc890d8`
- **Task Worktree Path**: `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002-G`
- **Verdict**: **ACCEPT WITH FOLLOW-UPS**
  - Follow-up 1: Fix external checker script `apc_check_f_outputs.py` at line 196 to accept `"PASS (resumed)"` status alongside `"PASS"`.
  - Follow-up 2: Disambiguate exploratory row condition labels in `scripts/analysis/tables.py` when both all-trials and clean-trials fits trigger Rule R1.
  - Follow-up 3: Enhance `scripts/analysis/figures.py` `plot_f3_premise_check` to handle unequal `k_cap` and `smax_cap` reference lines.
  - Follow-up 4: Add floating-point tolerance `1e-9` to dominance boundary checks in `scripts/analysis/stats.py`.
  - Follow-up 5: Remove silent default `corpus_m.get(corpus, 28)` in `scripts/analysis/tables.py` and fail closed or set NaN on unknown corpora.
  - Follow-up 6: Close test suite coverage gaps for surviving mutants M3, M6, M7, M8, M9, M11, M12, M14.

---

## 1. Executive Summary & Independence Certification

- **Independence Check** [Executed]: Session ID `7e5d65e7-fe39-4644-bf8c-58c970c70313` was verified against the exclusion list (`1b3efbca`, `512aecca`, `098dcdd4`, `2ebf9668`, `f4b13de1`, `562e3bc6`, `f339a846`, `d67eabb0`, `c143398c`, `26156499`, `bd54cd76`, DOC-011 session, and prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`). The session is strictly independent.
- **Review Only Scope** [Executed]: No production code, tests, decision log entries, or context documents were modified. Scratch copies and mutations were confined strictly to `/tmp`.

---

## 2. Setup & Implementation Review (Part A: Scope, Diffs, and Hashes)

### A1. Git Diff Stat and Unified Diff
- **Command** [Executed]: `git diff --stat 17ed1f8 f5e085d`
- **Output** [Executed]:
  ```
   docs/decisions/decision-log.md               |   31 +
   docs/reports/ANALYSIS-002-F-gemini-report.md | 2003 ++++++++++++++++++++++++++
   scripts/analysis/figures.py                  |   75 +-
   scripts/analysis/run_analysis.py             |  146 +-
   scripts/analysis/stats.py                    |  123 +-
   scripts/analysis/tables.py                   |  316 ++--
   tests/test_analysis_pipeline.py              |  423 +++++-
   7 files changed, 2800 insertions(+), 317 deletions(-)
  ```
- **Unified Diff (Decision Log Append Hunk)** [Executed]:
  ```diff
  diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
  index fd7c5e3..e56cd82 100644
  --- a/docs/decisions/decision-log.md
  +++ b/docs/decisions/decision-log.md
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
  Reasoning: resolves defects identified in independent review of the Phase 4 analysis pipeline, corrects inaccuracies in D-85, enforces the validation gate fail-closed without bypass, renders Table T3 verbatim from validator output, implements Rules R1–R3, and documents complete pipeline execution provenance without modifying raw experimental data. Affects: `scripts/analysis/`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
  ```
- **File Count & Decision Log Check** [Executed]: Exactly 7 files changed. `docs/decisions/decision-log.md` diff inspected; hunk consists strictly of 31 additions (lines 717–747, entry [D-86]) with 0 deleted lines.

### A2. Checksum Verification
- **Command** [Executed]: `sha256sum docs/decisions/decision-log.md scripts/analysis/figures.py scripts/analysis/run_analysis.py scripts/analysis/stats.py scripts/analysis/tables.py tests/test_analysis_pipeline.py scripts/analysis/validate_runs.py tests/test_analysis_validate_runs.py scripts/analysis/bootstrap.py scripts/analysis/style.py`
- **Results vs Expected** [Executed]:
  | File | Actual SHA256 | Expected SHA256 | Match |
  | --- | --- | --- | --- |
  | `docs/decisions/decision-log.md` | `266302bf9d333753b84ff90e45c32d382dc794f6658eb88c01c5b28059609a2d` | `266302bf9d333753b84ff90e45c32d382dc794f6658eb88c01c5b28059609a2d` | YES |
  | `scripts/analysis/figures.py` | `47b04a9434e9012a6225049ad59346c1adc22935d2c348a5c46160ef75c3250a` | `47b04a9434e9012a6225049ad59346c1adc22935d2c348a5c46160ef75c3250a` | YES |
  | `scripts/analysis/run_analysis.py` | `6603aa32a44c2ce8900d287f2dcb6248ce18ad2ffea743f7d7a1e53087a67cae` | `6603aa32a44c2ce8900d287f2dcb6248ce18ad2ffea743f7d7a1e53087a67cae` | YES |
  | `scripts/analysis/stats.py` | `c8ddc4bbd5603251522e7af8a08538ac49d03152ec8ca2919354403f172efacb` | `c8ddc4bbd5603251522e7af8a08538ac49d03152ec8ca2919354403f172efacb` | YES |
  | `scripts/analysis/tables.py` | `39a664ec89fccd3138440771021ed1b20115b582f1f88a4c92ec48c3958e22b2` | `39a664ec89fccd3138440771021ed1b20115b582f1f88a4c92ec48c3958e22b2` | YES |
  | `tests/test_analysis_pipeline.py` | `0c82cc6a3a8dd1e54a79627b48e7533f1b9206ef512631db48c9234e8e70697c` | `0c82cc6a3a8dd1e54a79627b48e7533f1b9206ef512631db48c9234e8e70697c` | YES |
  | `scripts/analysis/validate_runs.py` | `d93597eb3bba7b11b7a7b7cfee775067667d63880a5cc7eae7c4a14b01b2d11d` | `d93597eb3bba7b11b7a7b7cfee775067667d63880a5cc7eae7c4a14b01b2d11d` | YES |
  | `tests/test_analysis_validate_runs.py` | `a85fbb5b1397d18109ececea1cf9b8e88e879b20824c6c473e2f83230fc4b145` | `a85fbb5b1397d18109ececea1cf9b8e88e879b20824c6c473e2f83230fc4b145` | YES |
  | `scripts/analysis/bootstrap.py` | `9451e8a1c586bc2c90797f92bbb30c1da3393fdf7feb5d3ce73271c0aaaac44c` | `9451e8a1c586bc2c90797f92bbb30c1da3393fdf7feb5d3ce73271c0aaaac44c` | YES |
  | `scripts/analysis/style.py` | `e9f4539d20ddb62ea11b4a0bfa4bae61f1dc6059c2072eacc80197831e149e26` | `e9f4539d20ddb62ea11b4a0bfa4bae61f1dc6059c2072eacc80197831e149e26` | YES |

### A3. Source Code Pattern Greps
- **Pattern Greps** [Executed]:
  - `skip-gate`: 0 occurrences across `scripts/analysis/*.py`.
  - `/home/`: 0 occurrences across `scripts/analysis/*.py`.
  - `1e-12`: 0 occurrences across `scripts/analysis/*.py`.
  - file URI scheme (`file:`): 0 occurrences across `scripts/analysis/*.py`.
  - placeholder token (`F`+`I`+`L`+`L`): 0 occurrences across `scripts/analysis/*.py`.
- **Audit of `.get(` Usage** [Read]:
  - `run_analysis.py`: Lines 245–246 read `strat_cfg.get("strategy")` and `strat_cfg.get("config", {})`. Missing keys result in explicit None/empty dict handled safely.
  - `tables.py`: Lines 158, 230, 351 read `strat_cfg.get("strategy", r_dir.name)` falling back to directory name. Line 166 reads `rec_list[-1].get("corpus", "")`. Lines 173–176 read `k` and `s_max` with fallback to `None` (which triggers NaN for random baseline recall). Line 181 uses `corpus_m.get(corpus, 28)` (a silent default if corpus is unknown; see Finding 5).
  - `tables.py`: All required summary metrics and trial fields (`num_trials`, `num_success`, `llm_calls_mean`, `precision_micro`, `recall_micro`, `f1_micro`, `precision_macro`, `recall_macro`, `f1_macro`, `shortlist_recall_micro`, `shortlist_recall_macro`, `sensitivity` columns, `unjudged_predictions_total`, `corpus_or_size`, `n_with_retries`, `key`, `status`, `retries`, and `metrics` dict entries) are accessed strictly via `_require_col(row, col, run_name)`, which raises `KeyError` on missing, None, or empty values. No silent defaults remain on required metric fields.

---

## 3. Part B: Tests and Mutations

### B1. Test Suite Execution
- **Unset Environment Run** [Executed]:
  - Command: `python3 -m pytest -q tests/test_analysis_validate_runs.py tests/test_analysis_pipeline.py -rs`
  - Result: 40 passed, 1 skipped in 46.85s.
  - Skipped Test: `tests/test_analysis_pipeline.py:672` (`test_parity_with_validator_on_real_accuracy_directories` cleanly skipped when `PHASE4_RESULTS_DIR` unset).
- **With PHASE4_RESULTS_DIR Run** [Executed]:
  - Command: `PHASE4_RESULTS_DIR=/home/lukexodus/projects/llm-graph-insertion-complexity/results python3 -m pytest -q tests/test_analysis_validate_runs.py tests/test_analysis_pipeline.py -rs`
  - Result: 41 passed, 0 skipped, 0 failed in 46.97s.
  - Parity test ran against all 12 real accuracy runs and passed 100%.

### B2. Mutation Suite (M1–M10)
Executed in fresh scratch copies outside the repository (`/tmp/scratch_mutant`). Baseline control verified passing (13 passed, 1 skipped).

| ID | Module & Mutation | Command | Status | Verbatim Failing Line / Summary | APC Confirmation & Risk Analysis |
| --- | --- | --- | --- | --- | --- |
| **M1** | `run_analysis.py`: `if not overall_passed:` $\to$ `if False and not overall_passed:` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E assert 0 == 1` in `test_gate_failure_aborts_and_writes_nothing` | Confirmed killed by gate failure test. |
| **M2** | `stats.py` `fit_log_log_slope`: replace `<= 0` return with `1e-12` clamp | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E AssertionError: assert np.False_ where np.False_ = <ufunc 'isnan'>(9.25311250591608)` in `test_ols_log_log_slope` | Confirmed killed by zero-mean OLS unit test. |
| **M3** | `run_analysis.py`: write `t3_csv_str.replace("libraries_hash,", "", 1)` into T3 CSV | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Confirmed surviving; test gap only because `test_end_to_end_without_skip_gate` checks file existence rather than header fields on disk. |
| **M4** | `stats.py` `evaluate_dominance`: insert branch returning dominance when $|dF1| < 0.025$ and $calls_a \le calls_b$ | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E AssertionError: assert 'A dominates ...' == 'not distinguishable (F1 within 0.025)'` in `test_r2_dominance_including_boundary` | Confirmed killed by dominance boundary test. |
| **M5** | `tables.py`: delete `retries == 0` condition from clean timing set | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E assert 9 == 8` in `test_r3_post_hoc_sensitivity_exclusion` | Confirmed killed by R3 retry exclusion count check. |
| **M6** | `stats.py` `evaluate_dominance`: `<` becomes `<=` in 0.025 comparison | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Confirmed surviving; test gap only as existing unit tests check strict inequalities ($0.01$ and $0.03$), not exact boundary float values. |
| **M7** | `stats.py` `bootstrap_slope_ci`: replace `if has_zero_or_nonfinite: continue` with `if False:` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Confirmed surviving; test gap only because test fixture zero mean occurs at the empirical level, triggering the early exit before reaching resample loop. |
| **M8** | `figures.py` `plot_f3_premise_check`: give `k_cap` and `smax_cap` default 10 | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Confirmed surviving; test gap only because `run_analysis.py` passes caps explicitly and unit tests do not call the function with omitted caps. |
| **M9** | `tables.py` `_fit_metric_slopes`: `len(pos_sizes) >= 3` becomes `>= 2` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Confirmed surviving; test gap only because test fixtures have either $\ge 3$ or $< 2$ positive sizes, never exactly 2. |
| **M10** | `tables.py`: change clean exclusion key from `t9` to `t8` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E assert 9 == 8` in `test_r3_post_hoc_sensitivity_exclusion` | Confirmed killed by trial exclusion key check. |

### B3. Custom Mutants (M11–M14)

| ID | Module & Mutation | Command | Status | Failing Line / Summary | Risk & Impact |
| --- | --- | --- | --- | --- | --- |
| **M11** | `bootstrap.py`: `ddof=1` becomes `ddof=0` in `compute_series_stats` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Test gap; tests verify means, medians, and CIs, but do not assert sample standard deviation degrees of freedom. |
| **M12** | `stats.py`: `calls_b <= calls_a` becomes `calls_b < calls_a` in `evaluate_dominance` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Test gap; existing unit test checks strategy A call-parity dominance but does not test strategy B call-parity dominance. |
| **M13** | `run_analysis.py`: omit `hashes_file` line from `RUN_INFO.txt` | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **KILLED** | `E AssertionError: assert 'hashes_file: NOT SUPPLIED' in ...` in `test_gate_success_and_run_info` | Confirmed killed; provenance metadata in `RUN_INFO.txt` is strictly enforced. |
| **M14** | `tables.py`: scale `precision_micro` by 2.0 | `pytest tests/test_analysis_pipeline.py -q -p no:sugar` | **SURVIVED** | 13 passed, 1 skipped (Exit code: 0) | Test gap when `PHASE4_RESULTS_DIR` is unset; killed when parity test runs against real data. |

---

## 4. Part C: Plan Conformity

1. **Table Column Requirements (Plan §5)** [Read]:
   - **T1** (Accuracy Matrix): **CONFORMS**. Implemented in `scripts/analysis/tables.py:145-215`. Emits all 12 accuracy configurations with strategy, variant, corpus, trial/success/fail counts, retries, mean calls, micro/macro P/R/F1, shortlist recall, and random baseline.
   - **T2** (Sweep Cost Summary): **CONFORMS**. Implemented in `scripts/analysis/tables.py:340-440`. Emits distributional statistics (mean, median, std, min, max, 95% bootstrap CIs) for `llm_calls`, `total_s`, `shortlist_s`, `decide_s`, retry counts, and clean timing columns.
   - **T3** (Run Inventory): **CONFORMS**. Implemented in `scripts/analysis/run_analysis.py:198` and `scripts/analysis/tables.py:465-495`. Emits validator's verbatim 18-column inventory.
   - **T4** (Sensitivity Metrics): **CONFORMS**. Implemented in `scripts/analysis/tables.py:220-265`. Emits micro/macro sensitivity metrics and `unjudged_predictions_total` isolated from primary tables.
2. **Figure Specifications (Plan §5)** [Read]:
   - **F1** (Calls Scaling): **CONFORMS**. Implemented in `scripts/analysis/figures.py:350-410`. Log-x axis, primary configurations, error bars from 95% bootstrap CIs.
   - **F2** (Wall-Clock Scaling): **CONFORMS**. Implemented in `scripts/analysis/figures.py:415-485`. Two panels: Panel A total wall-clock time, Panel B shortlist vs decide step breakdown.
   - **F3** (Premise Check): **CONFORMS** (with follow-up). Implemented in `scripts/analysis/figures.py:485-550`. Linear y-axis, calls and wall-clock vs n, cap reference line drawn. No theoretical overlay curves plotted (conforms to Plan line 69). (See Finding 3 for cap reference line behavior when $k_{cap} \ne s_{max}$).
   - **F4** (Accuracy Comparison): **CONFORMS**. Implemented in `scripts/analysis/figures.py:35-135`. Micro/macro P, R, F1, shortlist recall, random baseline per corpus.
   - **F5** (Sensitivity Panels): **CONFORMS**. Implemented in `scripts/analysis/figures.py:140-240`. One-at-a-time variations for $k$, $efSearch$, $(s_{min}, s_{max})$, and $\theta$.
   - **F6** (Cost vs Accuracy & Dominance): **CONFORMS**. Implemented in `scripts/analysis/figures.py:245-345` and `scripts/analysis/stats.py:157-186`. LLM calls vs F1, mechanical dominance labeling.
3. **Decisions D1, D2, D3/D5** [Read]:
   - **D1** (Bootstrap Intervals): **CONFORMS**. 95% percentile bootstrap, 10,000 resamples, fixed seed 42 in `scripts/analysis/bootstrap.py:14-50` and `scripts/analysis/stats.py:80-155`.
   - **D2** (Flatness Bins): **CONFORMS**. Thresholds $<0.1$ ("approximately flat"), $0.1$ to $0.9$ ("sub-linear"), $>0.9$ ("approximately linear") in `scripts/analysis/stats.py:20-35`.
   - **D3 / D5** (Single Runs & Dominance): **CONFORMS**. Descriptive comparisons only; mechanical Pareto dominance in `scripts/analysis/stats.py:157-186`.
4. **Amendment 2 and Rules R1, R2, R3** [Read]:
   - **Amendment 2**: **CONFORMS**. Commit verification allows cross-mode differences only with `--src-diff-clean` verified against `3323bfb` in `scripts/analysis/validate_runs.py:800-860`. Canonical directory slug and duplicate-key failure checks enforced.
   - **Rule R1**: **CONFORMS**. Log-log OLS fits with zero-mean or non-finite costs evaluate to undefined (NaN slope, intercept, R2, no clamp) in `scripts/analysis/stats.py:40-115`. Exploratory row emitted if $\ge 3$ positive sizes present.
   - **Rule R2**: **CONFORMS**. $|\Delta F_1| < 0.025 \implies$ "not distinguishable (F1 within 0.025)" regardless of call counts in `scripts/analysis/stats.py:157-186`.
   - **Rule R3**: **CONFORMS**. Post-hoc clean timing columns exclude trials with retries $>0$ and `sweep:brute_force:2000:t9` in `scripts/analysis/tables.py:415-425`.
5. **Run Discovery Substring vs Manifest Mode** [Read]:
   - **Status**: **CONFORMS IN CONTEXT / MINOR RISK**. `run_analysis.py:191-192` partitions runs via `"accuracy" in d.name` and `"sweep" in d.name`. Under Amendment 2 (§2), directory slugs must match canonical slugs derived from strategy configuration, which always prefix with `accuracy_` or `sweep_`. Therefore, in valid datasets, substring discovery matches manifest mode. However, direct inspection of `manifest.json["mode"]` would be strictly robust against non-standard directory naming.

---

## 5. Part D: Specific Questions

### D1. Dual Exploratory Rows in `_fit_metric_slopes`
- **Answer** [Executed]: **YES**. Two indistinguishable exploratory rows can occur. In `scripts/analysis/tables.py:313`, the condition label for positive-mean fallback fits is hardcoded as `"exploratory (positive-mean sizes only)"`. When both the all-trials series and clean-trials series contain a zero-mean size (e.g. at $n=50$), both calls to `_fit_metric_slopes` append an exploratory row with identical strategy, variant, metric, and condition fields.
- **Fixture Verification** [Executed]: A synthetic fixture with zero cost at $n=50$ and positive costs at sizes 100, 200, 500 emitted two identical rows:
  `s1 | v1 | total_s | exploratory (positive-mean sizes only) | slope= 1.0000`
  `s1 | v1 | total_s | exploratory (positive-mean sizes only) | slope= 0.9538`

### D2. Dominance Floating-Point Boundary at 0.025
- **Answer** [Executed]:
  - Pair 1 (`0.525` vs `0.5`): Difference evaluates to `0.025000000000000022`. Since `0.025000000000000022 < 0.025` is `False`, the function treats this as exceeding the threshold, evaluating call dominance (returning `"A dominates B"`).
  - Pair 2 (Values evaluating to $< 0.025$, e.g. difference `0.02499999999999991`): The condition `abs(f1_diff) < 0.025` is `True`, returning `"not distinguishable (F1 within 0.025)"`.
  - Determinism: "Exactly 0.025" is **not deterministic** across arbitrary float representations because 0.025 has no exact binary representation in IEEE-754 floating point.
  - Proposed Fix: Compare using an explicit epsilon: `if abs(f1_diff) < f1_delta_threshold - 1e-9:` or `if math.isclose(abs(f1_diff), f1_delta_threshold, abs_tol=1e-7) or abs(f1_diff) < f1_delta_threshold:`.

### D3. Constant Series Slope and $R^2$
- **Answer** [Executed]:
  - Execution of constant series ($10.0$ calls across all 6 sizes):
    - `fit_log_log_slope`: `slope = 5.99e-32` ($\approx 0.0$), `intercept = 2.3026`, `r_squared = 2.99e-32` ($\approx 0.0$).
    - `bootstrap_slope_ci`: `slope = 5.99e-32`, 95% CI `[5.99e-32, 5.99e-32]`, `category = "approximately flat"`, `n_boot_used = 10000`.
  - Meaning of $R^2$: $R^2$ is **not mathematically meaningful** for a constant series. Because the total sum of squares $SS_{tot} = 0$, variance cannot be explained by any predictor.

### D4. Bootstrap Resample Dropping Bias
- **Answer** [Executed]:
  - Fixture execution (size 50 has 1 positive trial out of 10, remaining 9 trials are 0; sizes 100–2000 are all positive):
    - Result: `slope = 1.0796`, 95% CI `[0.8744, 1.0796]`, `category = "approximately linear"`, `r_squared = 0.7811`, `n_boot_used = 6443`.
  - Bias: Resample dropping **biases the interval**. Dropping all-zero bootstrap samples conditions the sampling distribution on size 50 having at least one positive trial, artificially inflating the mean at size 50 and flattening the fitted slope.
  - Disclosure: The output table records `n_boot_used = 6443` (disclosing the reduced count), but does **not** provide a textual warning or disclosure explaining that sample conditioning occurred.

### D5. Empty Column Handling in `_require_col`
- **Answer** [Read]:
  - In `validate_runs.py` lines 747–752, accuracy fields (`precision_micro`, `recall_micro`, `f1_micro`, `shortlist_recall_macro`, etc.) can legitimately be empty string `""` or None in `summary.csv` when gold neighbours are 0 or predictions are 0.
  - Furthermore, `error_type` and `error_message` in `raw.jsonl` are legitimately empty or null for successful trials.
  - In real runs: All 12 real accuracy runs had valid non-empty values for primary metrics, so no real-run table encountered `KeyError`. However, on edge-case synthetic runs with 0 predictions, `_require_col` would crash.

### D6. Premise Check Reference Line with Unequal Caps
- **Answer** [Executed]:
  - In `scripts/analysis/figures.py:534`, the plot draws a single horizontal reference line: `ax_calls.axhline(k_cap, color="red", linestyle="--", lw=1.5, label="cap (k / s_max)")`.
  - Execution with `k_cap=10, smax_cap=7`: The resulting figure displays only a single red dashed line at $y=10$. Strategy 4's data (bounded at 7) is plotted against a reference line drawn at 10, visually misrepresenting Strategy 4's theoretical bound.

### D7. Silent Default in `corpus_m.get(corpus, 28)`
- **Answer** [Read]:
  - In `scripts/analysis/tables.py:181`, `corpus_m = {"DSA_gold_standard_MEKG": 28, "metacademy_gold_standard_MEKG": 140}`.
  - The silent default `28` applies whenever `corpus` does not exactly match those two dictionary keys (e.g. if a new corpus is added, a typo occurs in directory/metadata, or `corpus` is empty string). It silently calculates random baseline recall as $\min(k, 28) / 28$.

---

## 6. Part E: Real-Data Run and Independent Check

### E1. Source Tree Cleanliness
- **Command** [Executed]: `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml; echo $?`
- **Output** [Executed]: `0`
- **Verification**: Exactly zero diff against commit `3323bfb` across core code and harness.

### E2. Real Pipeline Execution Output
- **Command** [Executed]:
  ```bash
  python3 scripts/analysis/run_analysis.py \
    --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results \
    --output-dir /tmp/phase4_analysis_output_002g \
    --src-diff-clean \
    --hashes /home/lukexodus/run-logs/final-results-hashes.txt
  ```
- **Console Log Output** [Executed]:
  ```
  ================================================================================
  PHASE 4 EMPIRICAL ANALYSIS PIPELINE
  Results Directory: /home/lukexodus/projects/llm-graph-insertion-complexity/results
  Output Directory:  /tmp/phase4_analysis_output_002g
  ================================================================================

  >>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...

  [OK] Validation gate passed 100%. Proceeding with analysis.

  Discovered: 24 total runs (12 accuracy, 12 sweep)

  >>> STEP 2: Generating Table T3 (Run Inventory)...
      Saved: /tmp/phase4_analysis_output_002g/tables/T3_run_inventory.csv and .md (24 entries)

  >>> STEP 3: Generating Accuracy Tables (T1, T4)...
      Saved: /tmp/phase4_analysis_output_002g/tables/T1_accuracy_benchmark.csv and .md (24 rows)
      Saved: /tmp/phase4_analysis_output_002g/tables/T4_sensitivity_metrics.csv and .md (24 rows)

  >>> STEP 4: Generating Accuracy Figures (F4, F5, F6)...
      Saved: /tmp/phase4_analysis_output_002g/figures/F4_accuracy_by_strategy.pdf (.png, .csv)
      Saved: /tmp/phase4_analysis_output_002g/figures/F5_sensitivity_panels.pdf (.png, .csv)
      Saved: /tmp/phase4_analysis_output_002g/figures/F6_cost_vs_accuracy_dominance.pdf (.png, .csv)
      Saved: /tmp/phase4_analysis_output_002g/figures/F6_dominance.csv and .md

  >>> STEP 5: Generating Sweep Cost Table (T2) and Slope Fits...
      Saved: /tmp/phase4_analysis_output_002g/tables/T2_sweep_cost_summary.csv and .md (72 rows)
      Saved: /tmp/phase4_analysis_output_002g/tables/T2_slope_fits.csv and .md (38 fits)

  >>> STEP 6: Generating Sweep Figures (F1, F2, F3)...
      Saved: /tmp/phase4_analysis_output_002g/figures/F1_calls_scaling.pdf (.png, .csv)
      Saved: /tmp/phase4_analysis_output_002g/figures/F2_wallclock_scaling.pdf (.png, .csv)
      Saved: /tmp/phase4_analysis_output_002g/figures/F3_premise_check.pdf (.png, .csv)

  ================================================================================
  PHASE 4 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY (100% PASS).
  ================================================================================
  ```
- **RUN_INFO.txt Contents** [Executed]:
  ```
  argv: scripts/analysis/run_analysis.py --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results --output-dir /tmp/phase4_analysis_output_002g --src-diff-clean --hashes /home/lukexodus/run-logs/final-results-hashes.txt
  results_dir: /home/lukexodus/projects/llm-graph-insertion-complexity/results
  git_commit: f5e085d774d59afc3b256a586e8cb8943cc890d8
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

### E3. Verification with Independent Checker
- **Checker SHA256 Verification** [Executed]:
  - `sha256sum /home/lukexodus/projects/thesis-analysis/apc_check_f_outputs.py`
  - Output: `fbea5dde8493261b4879682e9f06d91b8e94240fb9e5fd837d5966eedecf887b` (Matches expected hash).
- **Execution Against 002g Output** [Executed]:
  - Command:
    ```bash
    python3 /home/lukexodus/projects/thesis-analysis/apc_check_f_outputs.py \
      --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results \
      --output-dir /tmp/phase4_analysis_output_002g \
      --repo-root /home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002-G \
      --certified-t3 /home/lukexodus/projects/thesis-analysis/output/table_t3.csv
    ```
  - Verbatim Output:
    ```
    results: /home/lukexodus/projects/llm-graph-insertion-complexity/results
    output:  /tmp/phase4_analysis_output_002g
    runs: 24 (12 accuracy, 12 sweep)

    3227 checks, 1 failures
    FAIL: T3: a row is not PASS
    RESULT: FAIL
    ```
  - Exit Code: `1`
  - Root Cause Analysis: Out of 3,228 checks performed, exactly 1 check failed: `FAIL: T3: a row is not PASS`. Line 196 of `apc_check_f_outputs.py` tests `check(all(r.get("status") == "PASS" for r in rows), "T3: a row is not PASS")`. However, `validate_runs.py` line 876 sets status to `"PASS (resumed)"` for resumed runs per Amendment 2, and the certified `table_t3.csv` supplied to the checker itself has `status="PASS (resumed)"` on 4 runs. Indeed, the checker's own line 198 check (`check(t3p.read_bytes() == a.certified_t3.read_bytes(), "T3 differs from the gate-certified table_t3.csv")`) **passed**. The failure is due to a defect in `apc_check_f_outputs.py:196` (see Finding 1).
- **Status of Previous Author Output (`/tmp/phase4_analysis_output_002f`)** [Executed]:
  - `ls: cannot access '/tmp/phase4_analysis_output_002f': No such file or directory` (cleaned up from temporary storage).
  - Checker execution against pre-repair archive `/home/lukexodus/projects/thesis-analysis/output`: produced 179 failures (Exit code: 1), confirming that the repairs made in ANALYSIS-002-F resolved all 178 table/figure defects.

### E4. Determinism & Certified Data Parity
- **Certified Table T3 Comparison** [Executed]:
  - `diff -u /home/lukexodus/projects/thesis-analysis/output/table_t3.csv /tmp/phase4_analysis_output_002g/tables/T3_run_inventory.csv`
  - Output: Empty (0 bytes difference; bit-for-bit identical).

### E5. Structural Facts of Real Run (No Findings Interpretation)
- **Table & Figure Output Row Counts** [Executed]:
  - `T1_accuracy_benchmark.csv`: 24 rows
  - `T2_sweep_cost_summary.csv`: 72 rows
  - `T2_slope_fits.csv`: 38 rows
  - `T3_run_inventory.csv`: 24 rows
  - `T4_sensitivity_metrics.csv`: 24 rows
  - `F1_calls_scaling.csv`: 24 rows
  - `F2_wallclock_scaling.csv`: 24 rows
  - `F3_premise_check.csv`: 12 rows
  - `F4_accuracy_by_strategy.csv`: 8 rows
  - `F5_sensitivity_panels.csv`: 12 rows
  - `F6_cost_vs_accuracy_dominance.csv`: 8 rows
  - `F6_dominance.csv`: 12 rows
- **Rows Marked "Undefined" in `T2_slope_fits.csv`** [Executed]:
  1. `embedding_threshold | theta=0.5 | llm_calls | pre-registered (all trials) | undefined (zero mean at n=50)`
  2. `embedding_threshold | primary (theta=0.6) | llm_calls | pre-registered (all trials) | undefined (zero mean at n=50, 500)`
- **Rows Marked "Exploratory" in `T2_slope_fits.csv`** [Executed]:
  1. `embedding_threshold | theta=0.5 | llm_calls | exploratory (positive-mean sizes only) | sub-linear`
  2. `embedding_threshold | primary (theta=0.6) | llm_calls | exploratory (positive-mean sizes only) | sub-linear`
- **F6 Pairwise Dominance Classifications (`figures/F6_dominance.csv`)** [Executed]:
  - **DSA_gold_standard_MEKG**:
    1. `ann_retrieval` vs `bounded_bucket`: `trade-off`
    2. `ann_retrieval` vs `brute_force`: `trade-off`
    3. `ann_retrieval` vs `embedding_threshold`: `trade-off`
    4. `bounded_bucket` vs `brute_force`: `trade-off`
    5. `bounded_bucket` vs `embedding_threshold`: `trade-off`
    6. `brute_force` vs `embedding_threshold`: `trade-off`
  - **metacademy_gold_standard_MEKG**:
    7. `ann_retrieval` vs `bounded_bucket`: `trade-off`
    8. `ann_retrieval` vs `brute_force`: `A dominates B`
    9. `ann_retrieval` vs `embedding_threshold`: `not distinguishable (F1 within 0.025)`
    10. `bounded_bucket` vs `brute_force`: `trade-off`
    11. `bounded_bucket` vs `embedding_threshold`: `B dominates A`
    12. `brute_force` vs `embedding_threshold`: `B dominates A`

---

## 7. Findings Table

| ID | Severity | Evidence | File:Line | Finding Description | Proposed Fix (Not Applied) |
| --- | --- | --- | --- | --- | --- |
| **F-01** | **High** | [Executed] | `apc_check_f_outputs.py:196` | External checker fails with `FAIL: T3: a row is not PASS` because line 196 expects `status == "PASS"` for all rows, failing on legitimate resumed runs labeled `"PASS (resumed)"` per Amendment 2. | Change line 196 to: `check(all(r.get("status") in ("PASS", "PASS (resumed)") for r in rows), "T3: a row is not PASS")`. |
| **F-02** | **Low** | [Executed] | `scripts/analysis/tables.py:313` | Dual indistinguishable exploratory rows occur when both all-trials and clean-trials fits encounter zero-mean sizes. | Disambiguate condition string: `condition=f"exploratory ({condition}, positive-mean sizes only)"`. |
| **F-03** | **Low** | [Executed] | `scripts/analysis/figures.py:534` | Premise check plot draws only a single reference line at `y = k_cap`, ignoring `smax_cap` when caps differ. | Draw distinct reference lines for $k$ and $s_{max}$ when `k_cap != smax_cap`. |
| **F-04** | **Low** | [Executed] | `scripts/analysis/stats.py:177` | Floating-point rounding at boundary $|dF1| = 0.025$ causes non-deterministic classification. | Add explicit epsilon: `abs(f1_diff) < f1_delta_threshold - 1e-9`. |
| **F-05** | **Low** | [Read] | `scripts/analysis/tables.py:181` | Silent default `corpus_m.get(corpus, 28)` assumes DSA size for any unknown corpus name. | Replace with fail-closed key validation: `if corpus not in corpus_m: raise KeyError(f"Unknown corpus: {corpus}")`. |
| **F-06** | **Low** | [Executed] | `scripts/analysis/stats.py:136` | Resample dropping in bootstrap slope calculation conditions on positive trials, biasing slope interval without textual disclosure. | Record a warning or disclosure flag when `n_boot_used < n_resamples`. |
| **F-07** | **Low** | [Executed] | `tests/test_analysis_pipeline.py` | Unit test gaps allow mutants M3, M6, M7, M8, M9, M11, M12, M14 to survive. | Add unit tests for T3 disk CSV content, exact boundary float dominance, and standard deviation ddof. |

---

## 8. Exclusions and Delimitations

In accordance with instructions, this review did **NOT**:
1. Modify any repository source code, tests, decision log entries, or context documents.
2. Push any branch or commit to origin.
3. Access network resources or use any live LLM API keys.
4. Interpret empirical metric values as scientific conclusions (no evaluations such as "strategy X is superior" or "premise confirmed").
5. Merge, rebase, or delete task worktrees.
