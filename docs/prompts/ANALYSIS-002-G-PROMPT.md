# Prompt ANALYSIS-002-G (review of ANALYSIS-002-F)

Send to a fresh window that is not an excluded session. Before sending, copy
`apc_check_f_outputs.py` to `~/projects/thesis-analysis/apc_check_f_outputs.py`
and check `sha256sum` equals
`fbea5dde8493261b4879682e9f06d91b8e94240fb9e5fd837d5966eedecf887b`.
The prompt is everything below the line.

---

```
TASK ANALYSIS-002-G: independent review of ANALYSIS-002-F (Phase 4 analysis pipeline fix). REVIEW ONLY: you change no code, no tests, no decision log.
INDEPENDENCE: state your session ID and exact model label. Stop if you are any of 1b3efbca-895e-4b87-bbbd-80fb31a3230d, 512aecca-d185-438b-b8e7-d6dba3b507fb, 098dcdd4-c444-4fcd-af8f-1b2054b31802, 2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6, f4b13de1-a057-445e-a788-0523b774b94d, 562e3bc6-c12a-4372-85af-70eb9ecebfc7, f339a846-e963-4b8f-a62e-4090862002e7, d67eabb0-ae97-48c6-b5a3-90791aa4f3e2, c143398c-85ce-4b37-b9ae-1f4bc1a9283d, 26156499-0953-4f34-b42f-1cf073f8d16e (ANALYSIS-002 author), bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e (ANALYSIS-002-F author), the DOC-011 session, or any session starting 455d24de, b8ab4203, 900404ed, 2b098fc9, ede0cb54.
FILES YOU MAY CREATE: docs/reports/ANALYSIS-002-G-<agent>-review.md (replace <agent> with your agent family name in lowercase). Nothing else in the repo. Scratch work goes under /tmp. Forbidden to edit: everything else, including scripts/analysis/*, tests/*, docs/decisions/decision-log.md, docs/context/analysis-plan.md, results/.
RULES: no network, no live API calls, no key use. Do not run anything in the main checkout. Do not rewrite, recreate or truncate any file under results/ or ~/run-logs. Agent reports are claims: the ANALYSIS-002-F report is a claim, check it. Label every statement [Executed], [Read], [Inference] or [Unverified]. Do not interpret metric values from the real run (no "S2 is better", no "this confirms the premise"); you check correctness, not findings. Time box: 90 minutes; if you run out, report what is done and what is not.

SETUP
1. git worktree list; git status --short. Create your own worktree: git worktree add ../llm-graph-insertion-complexity-ANALYSIS-002-G -b task/ANALYSIS-002-G f5e085d774d59afc3b256a586e8cb8943cc890d8 . Report git log --oneline -3 there.
2. Grep for a reserved decision ID is NOT needed (you write no decision entry).
3. Read first: docs/context/analysis-plan.md Sections 3 to 6 and 8 (frozen; sha256 981136e97d86d1a765aaa71c318d170d3644c4f6eec938743710162730cf8bf7); scripts/analysis/validate_runs.py (read-only); the diff of commit f5e085d against 17ed1f8.

PART A: SCOPE AND HASHES
A1. git diff --stat 17ed1f8 f5e085d. Expected: exactly 7 files (decision-log.md append only, docs/reports/ANALYSIS-002-F-gemini-report.md, figures.py, run_analysis.py, stats.py, tables.py, tests/test_analysis_pipeline.py). Confirm the decision-log hunk has no deleted lines.
A2. sha256sum those files and compare with: decision-log.md 266302bf9d333753b84ff90e45c32d382dc794f6658eb88c01c5b28059609a2d; figures.py 47b04a9434e9012a6225049ad59346c1adc22935d2c348a5c46160ef75c3250a; run_analysis.py 6603aa32a44c2ce8900d287f2dcb6248ce18ad2ffea743f7d7a1e53087a67cae; stats.py c8ddc4bbd5603251522e7af8a08538ac49d03152ec8ca2919354403f172efacb; tables.py 39a664ec89fccd3138440771021ed1b20115b582f1f88a4c92ec48c3958e22b2; tests/test_analysis_pipeline.py 0c82cc6a3a8dd1e54a79627b48e7533f1b9206ef512631db48c9234e8e70697c. Also confirm validate_runs.py is d93597eb3bba7b11b7a7b7cfee775067667d63880a5cc7eae7c4a14b01b2d11d, tests/test_analysis_validate_runs.py a85fbb5b1397d18109ececea1cf9b8e88e879b20824c6c473e2f83230fc4b145 and bootstrap.py 9451e8a1c586bc2c90797f92bbb30c1da3393fdf7feb5d3ce73271c0aaaac44c, style.py e9f4539d20ddb62ea11b4a0bfa4bae61f1dc6059c2072eacc80197831e149e26 are unchanged.
A3. grep scripts/analysis/*.py for: skip-gate, /home/, 1e-12, file:///, FILL, .get(  (list every .get( that touches a required field of a run record, summary row or sidecar, and say whether a silent default remains).

PART B: TESTS AND MUTATIONS (executed, in a scratch copy outside the repo)
B1. Run: python3 -m pytest -q tests/test_analysis_validate_runs.py tests/test_analysis_pipeline.py -rs . Report passed/skipped/failed. Then repeat with PHASE4_RESULTS_DIR=/home/lukexodus/projects/llm-graph-insertion-complexity/results and report whether the parity test ran and passed.
B2. Mutation table, each with: exact change, command, verbatim failing line, and a passing baseline control first (a collection or import error is not a kill). Run each mutant against tests/test_analysis_pipeline.py in a fresh scratch copy.
  M1 run_analysis.py: `if not overall_passed:` becomes `if False and not overall_passed:`
  M2 stats.py fit_log_log_slope: replace the y_arr <= 0 early return with `y_arr = np.where(y_arr <= 0, 1e-12, y_arr)`
  M3 run_analysis.py: write `t3_csv_str.replace("libraries_hash,", "", 1)` into T3_run_inventory.csv
  M4 stats.py evaluate_dominance: insert before the first `if abs(f1_diff) ...` a branch returning "A dominates B (calls advantage, F1 equivalent)" when |diff| < 0.025 and calls_a <= calls_b
  M5 tables.py: delete the `retries == 0` condition from the clean set
  M6 stats.py evaluate_dominance: `<` becomes `<=` in the 0.025 comparison
  M7 stats.py bootstrap_slope_ci: replace the `if has_zero_or_nonfinite: continue` branch with `if False: continue`
  M8 figures.py plot_f3_premise_check: give k_cap and smax_cap the defaults 10
  M9 tables.py _fit_metric_slopes: `len(pos_sizes) >= 3` becomes `>= 2`
  M10 tables.py: change the clean exclusion key from "sweep:brute_force:2000:t9" to "sweep:brute_force:2000:t8"
The APC observed M3, M6, M7, M8, M9 surviving (tests pass). Confirm or refute each, and say in one sentence whether the survivor is a real risk for the real results or only a test gap.
B3. Design and run at least three mutants of your own in areas the table does not cover (suggestions: T1 numeric pass-through, T2 std using ddof=0, T2 num_trials counting failed records, RUN_INFO hashes_file line, F6 dominance using calls_b < calls_a). Same evidence format.

PART C: PLAN CONFORMITY (read the plan, then the code and the real outputs' file lists; do not interpret values)
For each item say CONFORMS / DEVIATES / UNCLEAR with file and line: (1) T1, T2, T3, T4 column requirements in Section 5; (2) F1 to F6 specifications including axes, the F3 cap line (plan line 77), and the no-theory-overlay rule; (3) D1 (95% percentile bootstrap, 10,000 resamples, seed 42), D2 thresholds (<0.1, 0.1 to 0.9, >0.9), D3/D5 dominance; (4) Amendment 2 and the three rules R1, R2, R3 as stated in docs/reports/ANALYSIS-002-F report and D-86: R1 zero-mean => undefined; R2 |dF1| < 0.025 => not distinguishable; R3 clean timing excludes retries>0 and key sweep:brute_force:2000:t9; (5) whether run discovery by name substring ("accuracy" / "sweep") can disagree with the validator's discovery by manifest mode.

PART D: SPECIFIC QUESTIONS (answer each in 2 to 6 lines with evidence)
D1. _fit_metric_slopes emits the exploratory row with the same condition text for the all-trials fit and the clean fit. Can two indistinguishable exploratory rows occur for one (strategy, variant, metric)? Show with a fixture.
D2. Dominance at the boundary: with values such as 0.525 and 0.5 the floating-point difference is 0.025000000000000022; with 0.6 and 0.575 it is 0.02499999999999991. Execute both through evaluate_dominance and state what the rule returns. Is "exactly 0.025" deterministic? Propose, do not apply, a fix.
D3. Constant series (every size has the same mean, e.g. 10.0 calls): execute fit_log_log_slope and bootstrap_slope_ci and report slope, r_squared and category. Is r_squared meaningful?
D4. Bootstrap resample dropping: on a fixture where one size has 1 positive trial out of 10 and the rest are positive, report n_boot_used and the CI, and say whether dropping can bias the interval and whether the output discloses this.
D5. _require_col treats "" as missing. Which required summary.csv / raw.jsonl fields can legitimately be empty in the real validator schema (read validate_runs.py)? Does any real-run table depend on one?
D6. plot_f3_premise_check draws one horizontal line at k_cap. If k_cap != smax_cap, what does the figure show? Execute with k_cap=10, smax_cap=7 and look at the PNG.
D7. tables.py corpus_m.get(corpus, 28): when would the silent default apply?

PART E: REAL-DATA RUN AND INDEPENDENT CHECK (read results, write outside the repo)
E1. In your worktree: git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml; echo $?   (paste the output)
E2. python3 scripts/analysis/run_analysis.py --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results --output-dir /tmp/phase4_analysis_output_002g --src-diff-clean --hashes /home/lukexodus/run-logs/final-results-hashes.txt   (paste the verbatim console output and RUN_INFO.txt)
E3. Verify the checker first: sha256sum /home/lukexodus/projects/thesis-analysis/apc_check_f_outputs.py must equal fbea5dde8493261b4879682e9f06d91b8e94240fb9e5fd837d5966eedecf887b; if not, stop this part. Then run:
    python3 /home/lukexodus/projects/thesis-analysis/apc_check_f_outputs.py --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results --output-dir /tmp/phase4_analysis_output_002g --repo-root <your worktree> --certified-t3 /home/lukexodus/projects/thesis-analysis/output/table_t3.csv
    Paste the full output and the exit code. Run the same checker against /tmp/phase4_analysis_output_002f (the author's output) if it still exists.
E4. Determinism: diff -r /tmp/phase4_analysis_output_002f/tables /tmp/phase4_analysis_output_002g/tables and the same for the figures/*.csv and figures/F6_dominance.*; paste the result. Differences in PDF/PNG bytes are expected and not findings.
E5. Do not interpret metric values. You may state structural facts only (row counts, which rows say "undefined", which rows are labelled exploratory, which F6 pairs carry which label) as a list, without commentary on what they mean for the thesis.

REPORT (docs/reports/ANALYSIS-002-G-<agent>-review.md)
Header: session ID, model label, base commit, worktree path. Verdict line: ACCEPT, ACCEPT WITH FOLLOW-UPS (list them) or REJECT (list blockers). Then: Part A to E results with evidence; a findings table (id, severity High/Medium/Low, evidence label, file:line, proposed fix without applying it); the mutation table; a list of what you did NOT do. No agent-written confirmations of Luke's statements. No test counts in any proposed decision text. Run sha256sum and wc -l on the report after your last edit. Commit only the report, git format-patch -N -o patch/ master, no push, leave the worktree for Luke. Paste the report's sha256, line count, the git diff --stat, and the grep output for 'file:///', 'FILL', '<agent>' over the report.
```
