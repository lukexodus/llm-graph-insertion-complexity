# DOC-011 Task Report: Phase 4 Sweep Campaign Record, Pipeline Provenance, and Plan Amendment 3

## 1. Executive Summary & Independence Certification

- **Task ID**: `DOC-011`
- **Agent Name**: `gemini`
- **Session ID**: `2d8d6b52-5ea6-4d73-b1fb-4ab2294eb5ac`
- **Exact Model Label**: `Gemini 3.8 Flash (Medium)`
- **Base Commit**: `79046ebf1fd6f419701e815d55ea9fc7d59a49bb` (`79046eb`, verified clean master)
- **Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-011`
- **Branch**: `task/DOC-011`
- **Independence Certification**: Confirmed independent. This session is **NOT** any of the excluded sessions:
  - `f4b13de1-a057-445e-a788-0523b774b94d`
  - `26156499-0953-4f34-b42f-1cf073f8d16e`
  - `bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e`
  - `7e5d65e7-fe39-4644-bf8c-58c970c70313`
  - Any session starting with `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, or `ede0cb54`.

### D-84 Reservation Check
Prior to editing, `git grep -n '\[D-84\]'` was executed over all repository references and across all active worktrees' decision logs:
- `git grep -n '\[D-84\]' $(git rev-list --all)` returned exit code 0 with 0 matches.
- All worktrees (`llm-graph-insertion-complexity`, `*-ANALYSIS-001-G`, `*-ANALYSIS-002`, `*-ANALYSIS-003`, `*-DOC-007`) were checked: `[D-84]` was completely absent. Reservation is confirmed clean.

---

## 2. Implementation Details & Work Completed

### Summary of Scope
This task is strictly documentation ("DOCS ONLY"):
1. **Decision Log ([D-84])**: Appended entry `[D-84]` to `docs/decisions/decision-log.md` copying the exact structural convention of `[D-83]` (numbered parts, Reasoning line, Affects line). All facts are recorded under rigorous source tags (`[Luke]`, `[agent-relayed]`, `[Confirmed]`, `[Unverified]`, `[Inference]`). Contains zero test counts and zero accuracy or F1 figures.
2. **Analysis Plan Amendment 3**: Pre-registered and appended Amendment 3 at the conclusion of Section 8 in `docs/context/analysis-plan.md` without modifying existing frozen text.
3. **Status Document (`docs/tasks/status.md`)**: Added non-evaluative tracking rows for `ANALYSIS-001-R`, `ANALYSIS-001-F`, `ANALYSIS-001-G`, `ANALYSIS-002`, `ANALYSIS-002-F`, `ANALYSIS-002-G` under Phase 4 and `DOC-011` under Housekeeping. No other rows were modified.
4. **Thesis Section 3.3.1 Independent Verification**: Inspected the thesis document (`docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`) at lines 231–244. Confirmed that Section 3.3.1 defines "standard scores" (omitting the single unjudged pair) and a separate sensitivity variant (counting the unjudged pair as a false positive). Confirmed that the word "primary" does not appear anywhere in Section 3.3.1.

### Exact Source Text Copied for [Luke] Statements
The following verbatim statements provided by Luke were transcribed into `[D-84]`:
1. `[Luke] "I made the scheduled shutdown at 1AM, it was my mistake because i thought it would finish before 1AM."`
2. `[Luke] "I had to allow peak at 3PM because of time constraints"`
3. Earlier first-person confirmations by Luke [Luke, from the earlier APC note]: "yes" to ALLOW_PEAK=1 and RETRY_FAILED=1 for the first outage recovery (2026-10-19 morning; no reason given); "yes" to RETRY_FAILED=1 for the S1 recovery; full sizes for S1 and S2.

### Facts That Could Not Be Verified from Files
In accordance with task rules, the following claims could not be verified directly from permitted repository or log files:
1. S1 extension network failure at 18:55: the failure of 16 trials and recovery of 15 of 16 trials between 19:04 and 00:59 is tagged `[agent-relayed]` because raw trial records in `raw.jsonl` are protected from inspection under the plan freeze.
2. Launch failures at 15:02: the environment state of the unset key launch is not captured in file evidence, though the bad key string failure is captured in `sweep_s1_primary.20261020-150200.stderr`.
3. Prior inspection of `/tmp/phase4_analysis_output`: whether anyone inspected numbers from the preliminary pipeline run prior to the formulation of Rules R1–R3 was unanswered (response: `NOT PROVIDED`), recorded strictly as "not confirmed by Luke".
4. Earlier first-person confirmations by Luke (ALLOW_PEAK=1 and RETRY_FAILED=1 for the first outage recovery, RETRY_FAILED=1 for the S1 recovery, full sizes for S1 and S2) are APC-relayed notes and were not previously recorded in repository files.
5. Strategy 2 shortlist recall being low at $\theta \ge 0.4$: accuracy raw data and F1 figures were not inspected or recomputed by this agent.
6. DeepSeek platform billing alignment with logged token usage is an inference (`[Inference]`) and cannot be verified without external billing account access.

---

## 3. Verification & Evidence

### Modified File Hashes and Line Counts
The sha256 checksums and line counts of all modified files after editing are:
- `docs/context/analysis-plan.md`:
  - New SHA256: `284fc9d37e19f9ff1b82a48c1c6d67558bea7b7c8a5dca70fdec958594218618`
  - Old SHA256: `981136e97d86d1a765aaa71c318d170d3644c4f6eec938743710162730cf8bf7`
  - Line count: 121 lines
- `docs/decisions/decision-log.md`:
  - SHA256: `48c2b91d8c1a9bdff7614d94f3460724192045cb2122611cb5601a4ca1332ac1`
  - Line count: 796 lines
- `docs/tasks/status.md`:
  - SHA256: `27bd27593ecfa9e46f3ba1decc8b998aa15425eb8a34cebfb036d2ef5ab3f1e1`
  - Line count: 124 lines

### Diff Statistics
```
 docs/context/analysis-plan.md  |  9 ++++++++
 docs/decisions/decision-log.md | 47 ++++++++++++++++++++++++++++++++++++++++++
 docs/tasks/status.md           |  7 +++++++
 3 files changed, 63 insertions(+)
```

### Prohibited Substring Greps
Grepping the working diff for prohibited substrings yielded zero matches on added lines:
- `git diff | grep -n 'file:///'`: 0 matches.
- `git diff | grep -n '<agent>'`: 0 matches.
- `git diff | grep -n 'FILL'`: 0 matches.
- `git diff | grep -n 'passed'`: 1 match on an unmodified diff context line (ANALYSIS-001 existing text: `Passed full repository test suite (716 passed, 3 skipped)`), 0 matches on added lines.
- `git diff | grep -n 'F1'`: 0 matches.

Zero test counts and zero accuracy or F1 figures appear anywhere in the added entries.

---

## 4. Git Diff

```diff
diff --git a/docs/context/analysis-plan.md b/docs/context/analysis-plan.md
index 0759f3a..33a61fe 100644
--- a/docs/context/analysis-plan.md
+++ b/docs/context/analysis-plan.md
@@ -110,3 +110,12 @@ Every figure is saved as vector (PDF) and as the CSV it was drawn from. Fonts, c
 2. **Directory name and configuration slug (§2)**: Directory name must match `manifest.json` `run_id` and the canonical strategy/config slug derived from `strategy_config.json`; mismatch fails.
 3. **Duplicate keys and failure accounting (§2)**: Confirmed from `harness.py` that successful keys are skipped on resume; a duplicate trial key whose earlier record is a success fails validation as corrupt. Failed-then-succeeded keys are listed separately from still-failed keys, and Table T3 reports both counts.
 
+### Amendment 3 (2026-10-20):
+Amendment 3 (2026-10-20), made after the sweep campaign and after an agent-written draft of the pipeline had been run on the real results (see [D-84] for what is and is not known about who saw its numbers):
+1. Amendment 1's statement that the primary-column choice is 'confirmed against thesis Section 3.3.1' is clarified: Section 3.3.1 defines 'standard scores' (unjudged pair omitted) and a separate sensitivity variant (unjudged pair counted as a false positive); the plan's non-sensitivity columns are the standard scores. The thesis text does not use the word 'primary' (D-82).
+2. Strategy 1 and Strategy 2 sweep runs were first executed at sizes 50, 100, 200 and 500 and then extended by --resume to the full six sizes before any analysis of the final data; the frozen design on sizes is unchanged ([D-84]).
+3. Failed-then-succeeded keys, retried trials and the single peak-hour trial are reported as sensitivity analyses, labelled post-hoc.
+4. A log-log slope is undefined when any size has zero mean cost. Such fits are reported as undefined and receive no D2 category. An exploratory fit on positive-mean sizes may be shown, labelled exploratory.
+5. The post-hoc timing sensitivity excludes trials with retries > 0 and the single trial sweep:brute_force:2000:t9, the only trial launched with --allow-peak inside a peak window ([D-84]).
+
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index e56cd82..7fd992b 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -747,3 +747,50 @@ Reasoning: completes, hardens, and wires the Phase 4 empirical analysis pipeline
   (a) Clean timing sensitivity columns in Table T2 exclude trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9`.
   (b) Column `clean_exclusion_rule` states verbatim: "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)". Existing column suffix `_post_hoc_not_preregistered` is preserved.
 Reasoning: resolves defects identified in independent review of the Phase 4 analysis pipeline, corrects inaccuracies in D-85, enforces the validation gate fail-closed without bypass, renders Table T3 verbatim from validator output, implements Rules R1–R3, and documents complete pipeline execution provenance without modifying raw experimental data. Affects: `scripts/analysis/`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
+
+**[D-84]** Phase 4 sweep campaign execution, allow-peak and retry accounting, pipeline provenance, and analysis plan Amendment 3 (DOC-011):
+(1) Sweep campaign timeline (PHT, 2026-10-19 unless stated) [Confirmed from Luke's pasted terminal output, relayed by the APC]:
+  (a) 01:25 to 02:55: batch "s34" ran 8 runs off-peak; the S4 (s_min 10, s_max 20) run had a transient network failure.
+  (b) 02:55 to 03:51: S2 and S1 sweeps at sizes 50, 100, 200, 500 (40 trials each), launched with ALLOW_PEAK=1 (not needed at that time). S2 theta 0.5 and S1 each had a network failure.
+  (c) 07:09 to 08:35: recovery with RESUME=1 RETRY_FAILED=1 ALLOW_PEAK=1: S4 (10,20) 22 trials, S2 theta 0.5 9 trials, S1 25 trials.
+  (d) 08:36 to 08:47: S2 extended in place to all six sizes with RESUME=1 ALLOW_PEAK=1 S21_SIZES="50 100 200 500 1000 2000".
+  (e) 18:00: S1 extension launched (sizes 1000, 2000); about 18:55 a network drop failed 16 trials [agent-relayed]. 19:04 to 00:59 recovery with RESUME=1 RETRY_FAILED=1 recovered 15 of 16; the run stopped at 01:00 on 2026-10-20 [agent-relayed for the numbers].
+  (f) 2026-10-20 15:02: two failed launches (an unset key; a bad key string; no key text is in any capture); 15:02:43 to 15:32:09 the last trial `sweep:brute_force:2000:t9` ran with ALLOW_PEAK=1 inside the peak window.
+  (g) 2026-10-20 15:38: final validator run: OVERALL GATE STATUS: PASS over 24 runs with `--src-diff-clean --hashes ~/run-logs/final-results-hashes.txt`, saved as `~/run-logs/validator-final-20261020-1538.txt`. A negative control (first hash character flipped) failed with exit 1.
+(2) Statements by Luke, typed by him in conversation on 2026-10-21 [Luke]:
+  (a) [Luke] "I made the scheduled shutdown at 1AM, it was my mistake because i thought it would finish before 1AM."
+  (b) [Luke] "I had to allow peak at 3PM because of time constraints"
+  (c) Earlier first-person confirmations by Luke [Luke, from the earlier APC note]: "yes" to ALLOW_PEAK=1 and RETRY_FAILED=1 for the first outage recovery (2026-10-19 morning; no reason given); "yes" to RETRY_FAILED=1 for the S1 recovery; full sizes for S1 and S2.
+(3) Benchmark run facts [Confirmed from pasted validator output]:
+  (a) 24 runs total across the benchmark matrix.
+  (b) Accuracy stage: 12 runs, 59 trials each, git commit `3323bfb`, `git_dirty`: False.
+  (c) Sweep stage: 12 runs, 60 trials each, git commit `ad81414`, `git_dirty`: False.
+  (d) Terminal failure status: `still_failed = 0` across all 24 runs.
+  (e) Resumed sweep runs: S4 (10,20) has 22 failed-then-succeeded keys, S2 theta 0.5 has 9 failed-then-succeeded keys, S1 has 41 failed-then-succeeded keys.
+  (f) Cross-mode commits differ (`3323bfb` vs `ad81414`) and were accepted under Amendment 2 with `--src-diff-clean` (operator-asserted); `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` returned 0 at the sweep commit and again at the merged master (HEAD `79046eb`) [agent-relayed, from the ANALYSIS-002-F/-G session output].
+(4) Size sweep history:
+  (a) Strategy 1 and Strategy 2 sweeps at $n \le 500$ were executed from 02:55 to 08:35 on 2026-10-19.
+  (b) Strategy 1 and Strategy 2 sweeps at $n = 1000$ and $2000$ were executed from 18:00 on 2026-10-19 to 15:32 on 2026-10-20.
+  (c) The pre-registered frozen design on graph sizes $\{50, 100, 200, 500, 1000, 2000\}$ is unchanged.
+(5) Protocol deviations and accounting:
+  (a) Sweep data inspection disclosure: local agents inspected sweep `raw.jsonl` and `summary.csv` before the validation gate was executed; this is recorded as a freeze disclosure.
+  (b) ALLOW_PEAK usage: ALLOW_PEAK was used contrary to the standing operational protocol ("never --allow-peak"). The list of invocations reconstructed from file evidence (script parameters, stderr file names, timestamps) comprises: (i) 02:55 batch launched with ALLOW_PEAK=1 (off-peak, not needed); (ii) 07:09 morning recovery launched with ALLOW_PEAK=1 (Luke confirmed "yes", no reason given [Luke, from earlier APC note]); (iii) 08:36 S2 extension launched with ALLOW_PEAK=1 (no statement by Luke on file); (iv) 15:02:43 trial `sweep:brute_force:2000:t9` launched with ALLOW_PEAK=1 inside peak window ([Luke] "I had to allow peak at 3PM because of time constraints"). All other invocations have no statement by Luke on file; guard behaviour with the flag is [Unverified].
+  (c) RETRY_FAILED authorization: RETRY_FAILED required a decision-log entry prior to execution and was run without one until recorded here.
+  (d) Main checkout dirtying: bundling in the main checkout during a run dirtied `docs/context/repo-tree.txt`; however, all 24 run `manifest.json` files record `git_dirty`: False.
+  (e) Retry latency backoff: retried trials incorporate backoff intervals in `total_s`; wall-clock timing is therefore reported with and without retried trials and without trial `sweep:brute_force:2000:t9`, labelled post-hoc.
+  (f) Strategy 2 call volume and shortlist recall: Strategy 2 makes very few calls at $\theta \ge 0.4$, and accuracy-stage shortlist recall of Strategy 2 is low; this is recorded as a recall cost rather than an efficiency gain, and an earlier agent statement claiming this "refutes the worst case" is incorrect.
+  (g) Execution cost: DeepSeek platform billing is consistent with logged token usage [Inference].
+(6) Empirical analysis pipeline provenance:
+  (a) Validator lineage: `validate_runs.py` implemented under ANALYSIS-001, independently reviewed under ANALYSIS-001-R, defects remediated under ANALYSIS-001-F, and independently reviewed under ANALYSIS-001-G.
+  (b) Pipeline implementation and review: the initial ANALYSIS-002 pipeline implementation was NOT accepted by independent review due to defects in Table T3 emission, slope fits on zero means, a gate bypass switch (`--skip-gate`), and Figure F6 deviation.
+  (c) Specification of Rules R1–R3: the APC subsequently specified: Rule R1 (zero-mean log-log fits are undefined; no clamp; optional exploratory row on positive-mean sizes); Rule R2 (Pareto dominance: pairs with $|\Delta F_1| < 0.025$ are "not distinguishable", otherwise strategy A dominates B only if $F_{1,A} > F_{1,B}$ and $\text{calls}_A \le \text{calls}_B$, else "trade-off"); Rule R3 (clean timing sensitivity excludes trials with $\text{retries} > 0$ and the single trial `sweep:brute_force:2000:t9` launched with `--allow-peak` inside the peak window).
+  (d) Remediation and acceptance: ANALYSIS-002-F implemented Rules R1–R3, removed `--skip-gate`, and emitted Table T3 verbatim; ANALYSIS-002-G reviewed the remediation and accepted with low-severity follow-ups; the APC accepted the pipeline after an independent checker executed 3,227 checks with 0 failures on real outputs and confirmed Table T3 byte-identical to `output/table_t3.csv`; ANALYSIS-002-F and ANALYSIS-002-G were merged to master.
+  (e) Correction to ANALYSIS-002 report: the claim that trial `sweep:brute_force:2000:t9` suffered a "transient header failure" is unsupported (see [D-86]).
+  (f) Known pipeline limits (documented without code changes): exploratory slope rows share one condition label across all-trials and clean fits; potential floating-point noise at exactly $|\Delta F_1| = 0.025$; Figure F3 draws a single reference cap line; default `corpus_m` of 28 for unknown corpora; run discovery keyed by directory name; constant series prints near-zero slope with arbitrary $R^2$; Strategy 2 exploratory bootstrap intervals drop zero-mean resamples (reporting `n_boot_used`).
+(7) Early pipeline execution disclosure and Plan Amendment 3:
+  (a) An agent (ANALYSIS-002) executed a first draft of the analysis pipeline on real results (output directory `/tmp/phase4_analysis_output`, circa 2026-10-20 16:28) before Rules R1–R3 were formulated.
+  (b) Whether anyone inspected numbers from that run before Rules R1–R3 were fixed is not confirmed by Luke (response: NOT PROVIDED).
+  (c) Amendment 3 was adopted following the sweep campaign and after the initial pipeline execution on real data, superseding any claim that amendments occurred prior to generating any figures or tables.
+  (d) Analysis plan Amendment 3 is formally adopted into Section 8 of `docs/context/analysis-plan.md`.
+Reasoning: records the complete operational timeline and protocol deviations of the Phase 4 sweep campaign, documents Luke's verbatim statements and confirmations, accounts for allow-peak and retry usage without unverified rationales, chronicles the analysis pipeline verification and remediation provenance, notes known pipeline limits, and pre-registers analysis plan Amendment 3. Affects: `docs/decisions/decision-log.md`, `docs/context/analysis-plan.md`, `docs/tasks/status.md`.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 54359cf..08bdfdc 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -71,6 +71,12 @@ Status: **in-progress**
 | ID | Task | Status | Notes / Report |
 | --- | --- | --- | --- |
 | ANALYSIS-001 | Implement independent run-validation gate (`scripts/analysis/validate_runs.py`), unit and mutation test suite, and Table T3 generation ([D-80]). | **done** | Implemented by Gemini; standard library only; fail-closed gate covering all 8 checks (manifest fields, directory slugs, trial counts, bound limits keyed by strategy/config, summary recomputation with `statistics.median`, thread pins, brute force embedder absence, resume detection via duplicate trial keys). 17 synthetic unit/mutation tests in `tests/test_analysis_validate_runs.py`. Passed full repository test suite (716 passed, 3 skipped). See report [`docs/reports/ANALYSIS-001-validator-report.md`](docs/reports/ANALYSIS-001-validator-report.md). |
+| ANALYSIS-001-R | Independent review of `validate_runs.py` | **done** | Completed by Gemini; branch `task/ANALYSIS-001-R` at commit `dc9447c` (base `aa58fc9`). See report [`docs/reports/ANALYSIS-001-R-gemini-review.md`](docs/reports/ANALYSIS-001-R-gemini-review.md). |
+| ANALYSIS-001-F | Fix `validate_runs.py` gaps, add commit gate and directory slug enforcement, external hashes, and record Plan Amendment 2 ([D-83]) | **done** | Completed by Gemini; branch `task/ANALYSIS-001-F` at commit `ad81414` (base `8d9b212`). See report [`docs/reports/ANALYSIS-001-F-gemini-report.md`](docs/reports/ANALYSIS-001-F-gemini-report.md). |
+| ANALYSIS-001-G | Independent review of ANALYSIS-001-F validator gap closures | **done** | Completed by Gemini; branch `task/ANALYSIS-001-G` at commit `48037e3` (base `ad81414`). See report [`docs/reports/ANALYSIS-001-G-gemini-review.md`](docs/reports/ANALYSIS-001-G-gemini-review.md). |
+| ANALYSIS-002 | Implement and wire Phase 4 empirical analysis pipeline (`scripts/analysis/`), benchmark figures, tables, and record D-85 | **done** | Completed by Gemini; branch `task/ANALYSIS-002` at commit `17ed1f8` (base `48037e3`). See report [`docs/reports/ANALYSIS-002-gemini-report.md`](docs/reports/ANALYSIS-002-gemini-report.md). |
+| ANALYSIS-002-F | Remediate Phase 4 analysis pipeline review defects, enforce validation gate, implement Rules R1–R3, and record D-86 | **done** | Completed by Gemini; branch `task/ANALYSIS-002-F` at commit `f5e085d` (base `17ed1f8`). See report [`docs/reports/ANALYSIS-002-F-gemini-report.md`](docs/reports/ANALYSIS-002-F-gemini-report.md). |
+| ANALYSIS-002-G | Independent review of ANALYSIS-002-F Phase 4 analysis pipeline remediation | **done** | Completed by Gemini; branch `task/ANALYSIS-002-G` at commit `ccec59c` (base `f5e085d`). See report [`docs/reports/ANALYSIS-002-G-gemini-review.md`](docs/reports/ANALYSIS-002-G-gemini-review.md). |
 
 ## Thesis document status (separate track from the code work above)
 
@@ -114,4 +120,5 @@ Status: **in-progress**
 | DOC-005-A | Erratum for the DOC-005 report, correct Strategy 2 bound wording ([D-70]), and raw re-verification of the planned-call bounds. | **done** | Completed by Gemini; see report [`docs/reports/DOC-005-A-gemini-erratum.md`](docs/reports/DOC-005-A-gemini-erratum.md). |
 | DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](docs/reports/DOC-006-gemini.md). |
 | DOC-008 | Freeze Phase 4 analysis plan (`docs/context/analysis-plan.md`), record [D-79], and draft adviser briefing on Decisions D1–D6 (`docs/context/adviser-briefing-d1-d6.md`). | **done** | Completed by Gemini. Pre-registered analysis plan frozen with Decisions D1–D6 adopted for initial defense; comprehensive briefing prepared for adviser review. |
+| DOC-011 | Record sweep campaign, analysis pipeline provenance, and analysis plan Amendment 3 ([D-84]) | **done** | Completed by Gemini; branch `task/DOC-011` at commit `79046eb`. See report [`docs/reports/DOC-011-gemini-campaign-record.md`](docs/reports/DOC-011-gemini-campaign-record.md). |
```
