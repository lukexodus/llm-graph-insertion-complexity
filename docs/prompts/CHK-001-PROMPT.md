# CHK-001: fix the APC checker's F1b/F2b row-count check, re-run it, and finish the final-output comparison

You are a local coding agent. Luke relays this prompt and your report to the APC AI, which has no filesystem access. Your report is a claim; the APC will check anything that matters against your raw output. Paste raw command output, not summaries.

## Independence

Excluded sessions (you must not be, or continue, any of these). Report your own session ID and model label at the top of your report.

`1b3efbca-895e-4b87-bbbd-80fb31a3230d`, `512aecca-d185-438b-b8e7-d6dba3b507fb`, `098dcdd4-c444-4fcd-af8f-1b2054b31802`, `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`, `f4b13de1-a057-445e-a788-0523b774b94d`, `562e3bc6-c12a-4372-85af-70eb9ecebfc7`, `f339a846-e963-4b8f-a62e-4090862002e7`, `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2`, `c143398c-85ce-4b37-b9ae-1f4bc1a9283d`, `26156499-0953-4f34-b42f-1cf073f8d16e`, `bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e`, `7e5d65e7-fe39-4644-bf8c-58c970c70313`, `2d8d6b52-5ea6-4d73-b1fb-4ab2294eb5ac`, `c492c7fc-3f03-4c2b-987c-8469a46cf74e`; prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`.

If your session is one of these, stop and say so.

## Background

Running `~/projects/thesis-analysis/apc_check_f_outputs.py` (sha256 `a5c2d1f7...9855`) on `~/projects/thesis-analysis/final_output_final` printed:

```
3391 checks, 2 failures
FAIL: F1b_calls_scaling_logy: 24 rows vs 72 T2 rows
FAIL: F2b_wallclock_scaling_logy: 24 rows vs 72 T2 rows
```

A previous agent diagnosed this as a checker bug: the row-count check compares the F1b/F2b CSV against all of Table T2 (72 rows, all variants), while F1b/F2b plot only the 24 primary rows (4 strategies x 6 sizes), like F1/F2. That diagnosis is plausible but unverified. Do not accept it without evidence, and do not make the checker pass by loosening it.

## What you may touch

- `~/projects/thesis-analysis/apc_check_f_outputs.py` (keep the pre-change copy as `apc_check_f_outputs.py.pre-chk001`; do not delete it).
- New scratch files under `/tmp/chk001/`.

## Forbidden

The whole repo `~/projects/llm-graph-insertion-complexity/` (read-only for you; do not run anything in it that writes), `results/`, `~/run-logs/`, `~/projects/thesis-analysis/final_output/`, `~/projects/thesis-analysis/final_output_final/` (read-only; all mutation experiments go on copies in `/tmp/chk001/`), and `~/projects/thesis-analysis/output/table_t3.csv`. No live API calls, keys, network or model downloads. Do not write any statement on Luke's behalf.

## Steps

1. `sha256sum` and `wc -l` the current checker; copy it to `.pre-chk001`. Reproduce the failure with the exact arguments below and paste the verbatim output and exit code.

   ```
   python3 ~/projects/thesis-analysis/apc_check_f_outputs.py \
     --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results \
     --output-dir /home/lukexodus/projects/thesis-analysis/final_output_final \
     --repo-root /home/lukexodus/projects/llm-graph-insertion-complexity \
     --certified-t3 /home/lukexodus/projects/thesis-analysis/output/table_t3.csv
   ```

2. Paste the checker code around the F1/F2/F1b/F2b/F6/F6b checks (about lines 300 to 380) verbatim.

3. Establish the facts from the data, with commands and raw output:
   - number of rows, and the distinct `(strategy, variant, n)` keys, in `figures/F1_calls_scaling.csv`, `figures/F1b_calls_scaling_logy.csv`, `figures/F2_wallclock_scaling.csv`, `figures/F2b_wallclock_scaling_logy.csv`;
   - whether the F1b key set equals the F1 key set, and the F2b key set equals the F2 key set (state the exact relationship, including any panel or component column in F2/F2b that changes the row count);
   - which T2 variants are "primary" and how many T2 rows they cover.

   If the key sets do not match as the diagnosis claims, stop and report that; do not patch.

4. Fix the checker so that the row-count and key-set check does not depend on the guessed substring "primary" alone. Required behaviour:
   - the expected F1b key set is the F1 CSV's key set, and the expected F2b key set is the F2 CSV's key set (adjusted only for the relationship you established in step 3);
   - F1b/F2b must fail if a key is missing, extra, or duplicated, and the failure message must name the keys;
   - the existing value checks against T2 (matched by key, not by position) stay as they are;
   - keep the primary-variant selection for F6/F6b exactly as it is.

5. Test the fix. All mutations go on a copy: `cp -r final_output_final /tmp/chk001/out_copy`, and run the checker with `--output-dir /tmp/chk001/out_copy`. Run a passing baseline control on the unmodified copy first. Then, one at a time, restoring the copy between mutations, show each mutation's exact change, the command, and the verbatim failing line:
   - delete one data row from the F1b CSV;
   - delete one data row from the F2b CSV;
   - append a duplicate of one F1b row;
   - append one F1b row for a non-primary variant (copy a non-primary T2 row's key);
   - change one `llm_calls_mean` value in the F1b CSV;
   - change one `total_s_mean` value in the F2b CSV.

   Each must fail with a specific message. A nonzero exit from an import or parse error is not a kill. If a mutation does not fail, report it as a survivor; do not hide it.

6. If a test fixture for the checker exists (the earlier session used one with 1,114 checks), find it and add one non-primary variant to its T2 so the fixture covers the real-data case that was missed. If no fixture can be found, say so and do not invent one.

7. Run the fixed checker on the real, unmodified `final_output_final` with the exact arguments from step 1. Paste the full verbatim output and exit code. Then print `sha256sum` and `wc -l` of the new checker.

8. Finish the final-output comparison. Run `diff -rq ~/projects/thesis-analysis/final_output ~/projects/thesis-analysis/final_output_final` and paste the full output. Then, for `tables/*.csv`, `tables/*.md`, `figures/*.csv` and `figures/F6_dominance.*`, excluding `F1b*`, `F2b*`, `F6b*` and `RUN_INFO.txt`, show a `sha256sum` listing for both directories side by side. If a file differs, show the differing lines (`diff`), do not describe them. If the old directory is missing or a file is absent from one side, say exactly which.

9. Do not write "identical" or "all checks pass" unless the pasted output shows it.

## Report format

Session ID and model label first. Then, in order: the reproduction (step 1), the facts (step 3), the patch as a unified diff (`diff -u` of `.pre-chk001` against the new file), the mutation table (step 5, with raw lines), the real-data run (step 7), the comparison (step 8), and a list of anything you could not do or did not verify.
