# Analysis plan (FROZEN): Phase 4 of the candidate-narrowing study

Status: **FROZEN under [D-79].** Adopted with Luke's confirmation of Decisions D1 to D6 on 2026-10-18/19 for initial defense (with post-defense adviser reconciliation provision). Pre-registered before opening any sweep data.

Sources: thesis Sections 3.3 to 3.5; D-35(5), D-68, D-75(3)(a), D-77(4), D-78, D-80; the harness output formats (`raw.jsonl`, `summary.csv`, `manifest.json`, `strategy_config.json`).

Disclosure: the plan was derived from Sections 3.4 and 3.5 and the harness formats. Before this plan is frozen, the accuracy-mode summaries of all 12 accuracy configurations (and the excluded DSA-only run 1) have been seen by the APC and by the local analysis agent, so accuracy-side choices in this plan (per-corpus reporting, the 0.025 F1 label in F6) were not made blind to accuracy results. Sweep data is unopened: no sweep run has been analysed, and the freeze precedes the opening of any sweep `raw.jsonl`. Analysis code written before the freeze is a draft and is not pre-registered.

## 0. Decisions D1 to D6 (confirmed by Luke for initial defense)

- **D1.** Intervals: 95% percentile bootstrap over trials, 10,000 resamples, fixed seed; mean, SD, min and max also reported.
- **D2.** Flatness bins as in 4.3. The values are a convention chosen for this study, not a standard; confirmed by Luke for initial defense, subject to post-defense adviser reconciliation.
- **D3.** Single runs for the benchmark matrix. The excluded DSA-only run 1 may be cited as **one observed difference** between two runs of the same configuration (see 4.2). It is not an estimated noise floor.
- **D4.** Accuracy is reported per corpus (DSA, 29-node gold graph; Metacademy, 141-node gold graph), not as a curve over `n`.
- **D5.** A mechanical dominance statement is made in F6, with the labelling rule in the F6 row.
- **D6.** Mean as the headline wall-clock statistic, median reported alongside.

## 1. Scope and rules

1. Cost claims come **only** from sweep runs (synthetic data, Section 3.3.2). Accuracy claims come **only** from accuracy runs on the gold corpora (Section 3.3.1). Latencies measured in accuracy runs are not used for any cost claim.
2. One script generates every figure and table from data that has passed the validation gate (Section 2). No hand edits.
3. No result-driven choices after the freeze: no change of metric, axis, bin, threshold, exclusion or plot type. Accuracy data was already seen before the freeze (see Disclosure); sweep data is opened only after the freeze. Anything added later is labelled **exploratory** in the text and captions.
4. No trimming or removal of outlier trials. Failed or missing trials are counted and reported, never imputed.
5. A run that fails the gate is not analysed until the APC records how it is resolved.
6. All 24 runs use the same commit and environment (checked by the gate). Single-threaded embedding is a protocol, not a measured effect (D-72, D-73).

## 2. Validation gate (runs before any figure)

For each of the 24 run directories, report pass/fail and the value:

- trial count equals the plan; LLM calls within the planned upper bound (590 / 295 / 1,180 / 5,012 accuracy; 600 / 300 / 1,200 / 38,500 sweep); retries and failed trials listed
- `git_dirty` is false and `git_commit` is identical across all runs; `libraries` identical across all runs
- `cpu_threads` and `torch_threads` equal 1 for every embedding strategy
- embedder identity (model, revision) identical across embedding runs
- no run was resumed, or each resumed run is flagged
- `summary.csv` agrees with an independent recomputation from `raw.jsonl` (micro and macro P, R, F1; shortlist recall; mean calls; mean `total_s`) within floating-point tolerance
- the sha256 of each run directory is recorded in the run inventory (Table T3)

## 3. Definitions

### 3.1 Metrics (as in Section 3.4; not redefined here)

- Cost per insertion: `total_s = shortlist_s + decide_s + apply_s + update_s`, and the LLM call count per insertion. `validate_s` is excluded.
- Accuracy: precision, recall and F1, micro and macro; shortlist recall (undefined for concepts with no gold neighbours, so excluded from macro means); the expected shortlist recall of a uniform random baseline, `min(k, m) / m`.
- Primary accuracy columns are the non-sensitivity columns of `summary.csv`. The `*_sensitivity` columns and `unjudged_predictions_total` are reported in a separate table and are never mixed into the primary figures. (To confirm against Section 3.3.1.)

### 3.2 The size variable

- **Cost curves:** `n` is the graph size of the sweep, `n in {50, 100, 200, 500, 1000, 2000}`, 10 trials per size.
- **Accuracy (D4):** the gold graphs give only two sizes (DSA 29 nodes, Metacademy 141 nodes), and trials withhold individual concepts. Accuracy is reported **per corpus**, not as a curve over `n`, and the text states that Section 3.5's "accuracy against graph size" is answered only at the sizes the gold corpora provide.

## 4. Statistics

### 4.1 Descriptive (all cost and accuracy figures)

Per (strategy, configuration, size): number of trials, mean, SD, min, max, median. Interval (D1): 95% percentile bootstrap over trials, 10,000 resamples, fixed seed. Headline (D6): mean for wall-clock time (Section 3.4 speaks of an "average"), median beside it because latency distributions are heavy-tailed.

### 4.2 Inference

No hypothesis tests between strategies. Each configuration is a single run, LLM judgement is non-deterministic (two identical DSA runs differed by about 0.025 micro-F1), and 10 trials per size is small. Comparisons are descriptive and are stated as such. (D3) The benchmark matrix is single runs. The excluded DSA-only run 1 (micro-F1 0.4859, against 0.5111 on the DSA trials of the full re-run, same configuration and seed) may be cited as one observed difference between two runs. It is archived outside `results/` and appears in no benchmark figure or table. If replicates are added later, they are specified before they are run and use the same procedure for every configuration.

### 4.3 Flatness of cost against `n` (Research Question 4, structural premise only)

For each strategy and each of calls and `total_s`: an OLS fit of log(mean cost) on log(n) across the six sizes, with a bootstrap interval for the slope (resampling trials within size). (D2) Descriptive bins (a convention for this study, not a standard): slope below 0.1 = "approximately flat"; 0.1 to 0.9 = "sub-linear"; above 0.9 = "approximately linear". The bins are fixed before sweep data is opened.

Constraints on interpretation, stated in the text:

- For Strategies 3 and 4 the call count per insertion is bounded by `k` or `s_max` by construction, so a flat call curve is close to guaranteed. The informative evidence for the premise is the **wall-clock curve** (shortlist step, HNSW search, hashing) and the **realised** call counts below the cap.
- The curves describe one **un-amortised** insertion (Section 3.5). They do not test amortised behaviour, and no fitted theoretical curve is overlaid (D-68(1), D-75(3)(a), D-77(4)).

## 5. Figures and tables

| ID | Content | Data |
|----|---------|------|
| F1 | LLM calls per insertion vs `n`, log-x, one line per strategy (primary configurations), interval bars | sweep |
| F2 | `total_s` vs `n`, same layout; and a second panel splitting `shortlist_s` from `decide_s` | sweep |
| F3 | Premise check: calls and `total_s` vs `n` for Strategies 3 and 4 on a linear y-axis, with the cap (`k`, `s_max`) drawn as a reference line | sweep |
| F4 | Accuracy by strategy and corpus: P, R, F1 (micro and macro) and shortlist recall, with the random baseline | accuracy |
| F5 | One-at-a-time sensitivity panels: `k`, efSearch, `(s_min, s_max)`, theta, each showing calls and F1 or shortlist recall | accuracy, sweep |
| F6 | Cost beside accuracy for each strategy and corpus (calls against F1). (D5) Dominance is computed mechanically from the plotted points. An F1 difference below 0.025 (the one observed run-to-run difference, D3) is labelled "not distinguishable", not "dominated". | both |
| T1 | All 12 accuracy configurations side by side | accuracy |
| T2 | Cost per (strategy, size): mean, SD, min, max, median of calls, `total_s`, `shortlist_s`, `decide_s` | sweep |
| T3 | Run inventory: 24 runs with commit, library versions, status, trial and call counts, sha256 | manifests |
| T4 | Sensitivity-variant metrics and unjudged predictions, reported apart from T1 | accuracy |

Every figure is saved as vector (PDF) and as the CSV it was drawn from. Fonts, colours and axis styles are fixed once in a style module.

## 6. Threats to validity to state in the thesis

- One run per configuration; the one observed difference between two runs of the same configuration was 0.025 micro-F1 on the DSA trials (D3), so the size of run-to-run variation is not established.
- Timing is from a single laptop (i5-8250U, 4 cores, 8 threads) with no controlled load. Run latency varied by up to 3.7x between two identical DSA runs; a per-run load log exists for the batch.
- Single-threaded embedding is a protocol choice. Whether it removed a confound in real runs is unestablished (D-73).
- The synthetic concept names are unverified for pedagogical validity and are used only for cost (Section 3.3.2).
- The decision-step model's behaviour may change with provider-side updates; the model alias and run dates are recorded per run.

## 7. Freeze procedure

1. Luke confirms D1 to D6 as written in Section 0; the adviser confirms D2 and D3.
2. The plan is committed under `docs/` and its sha256 is recorded in a decision-log entry **before** any sweep `raw.jsonl` is opened.
3. Later changes are made only by a dated amendment entry that states what changed and why, never by editing the frozen text.

## 8. Dated Amendments

### Amendment 1 (2026-10-19):
1. **Clarification of Primary Accuracy Columns (§3.1)**: Confirmed against thesis Section 3.3.1; the parenthetical check note is settled (non-sensitivity columns are primary; sensitivity variants and unjudged totals are isolated in T4).
2. **Resumed Run Accounting (§2)**: Clarified that a resumed run is identified by duplicate trial keys in `raw.jsonl` (failed trial record followed by retried success record); failed trials and retries are tracked directly without imputation.

### Amendment 2 (2026-10-19):
1. **Commit gate (§2)**: `git_commit` must be identical within a mode; across modes, accept differing commits only when a documented argument (e.g. `--src-diff-clean`, with the zero-diff command output of `src`, `scripts/run_experiment.py` and `pyproject.toml` against `3323bfb`, supplied by Luke) is given; otherwise fail closed.
2. **Directory name and configuration slug (§2)**: Directory name must match `manifest.json` `run_id` and the canonical strategy/config slug derived from `strategy_config.json`; mismatch fails.
3. **Duplicate keys and failure accounting (§2)**: Confirmed from `harness.py` that successful keys are skipped on resume; a duplicate trial key whose earlier record is a success fails validation as corrupt. Failed-then-succeeded keys are listed separately from still-failed keys, and Table T3 reports both counts.

### Amendment 3 (2026-10-20):
Amendment 3 (2026-10-20), made after the sweep campaign and after an agent-written draft of the pipeline had been run on the real results (see [D-84] for what is and is not known about who saw its numbers):
1. Amendment 1's statement that the primary-column choice is 'confirmed against thesis Section 3.3.1' is clarified: Section 3.3.1 defines 'standard scores' (unjudged pair omitted) and a separate sensitivity variant (unjudged pair counted as a false positive); the plan's non-sensitivity columns are the standard scores. The thesis text does not use the word 'primary' (D-82).
2. Strategy 1 and Strategy 2 sweep runs were first executed at sizes 50, 100, 200 and 500 and then extended by --resume to the full six sizes before any analysis of the final data; the frozen design on sizes is unchanged ([D-84]).
3. Failed-then-succeeded keys, retried trials and the single peak-hour trial are reported as sensitivity analyses, labelled post-hoc.
4. A log-log slope is undefined when any size has zero mean cost. Such fits are reported as undefined and receive no D2 category. An exploratory fit on positive-mean sizes may be shown, labelled exploratory.
5. The post-hoc timing sensitivity excludes trials with retries > 0 and the single trial sweep:brute_force:2000:t9, the only trial launched with --allow-peak inside a peak window ([D-84]).


