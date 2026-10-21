# DOC-012: correcting docs entry D-88 (docs only)

You are a local coding agent. Luke relays this prompt and your report to the APC AI, which has no filesystem access. Your report is a claim; the APC will check hashes, line counts and the patch. Paste raw command output, not summaries.

## Independence

Excluded sessions (you must not be, or continue, any of these). Put your own session ID and model label at the top of your report.

`1b3efbca-895e-4b87-bbbd-80fb31a3230d`, `512aecca-d185-438b-b8e7-d6dba3b507fb`, `098dcdd4-c444-4fcd-af8f-1b2054b31802`, `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`, `f4b13de1-a057-445e-a788-0523b774b94d`, `562e3bc6-c12a-4372-85af-70eb9ecebfc7`, `f339a846-e963-4b8f-a62e-4090862002e7`, `d67eabb0-ae97-48c6-b5a3-90791aa4f3e2`, `c143398c-85ce-4b37-b9ae-1f4bc1a9283d`, `26156499-0953-4f34-b42f-1cf073f8d16e`, `bd54cd76-ba2e-4b6e-9804-b9a3b8968b1e`, `7e5d65e7-fe39-4644-bf8c-58c970c70313`, `2d8d6b52-5ea6-4d73-b1fb-4ab2294eb5ac`, `c492c7fc-3f03-4c2b-987c-8469a46cf74e`, `60ce976a-8f34-483d-9224-f305b731e309`; prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`.

If your session is one of these, stop and say so.

## Task

Append one correcting entry, D-88, to `docs/decisions/decision-log.md`, and one status row for DOC-012 to `docs/tasks/status.md`. Docs only. Corrections are made by a later entry, never by editing an earlier one. Do not edit D-84, D-87, or any other existing text.

## Before writing

1. `git worktree list` and `git status --short`. Work in a fresh worktree off `master` (HEAD should be `554bde3` or a descendant; report it).
2. Reserve the IDs. Run `git grep -n '\[D-88\]' $(git for-each-ref --format='%(refname)' refs/heads refs/remotes)` and the same for each worktree's decision log. If D-88 is taken, stop and report. Check that no task or status row named DOC-012 exists; if one does, stop.
3. Read: `docs/decisions/decision-log.md` entries D-84, D-86 and D-87 (the log is not in ID order; search by ID), `docs/context/analysis-plan.md` (Disclosure paragraph and Section 8), and the DOC-011 and ANALYSIS-003 rows of `docs/tasks/status.md`.

## Files you may touch

- `docs/decisions/decision-log.md`: append D-88 only.
- `docs/tasks/status.md`: append your own DOC-012 row only. Do not edit other rows.
- `docs/reports/DOC-012-<agent>-correction.md`: new report.

Everything else is forbidden, including `docs/context/analysis-plan.md`, all of `src/`, `scripts/`, `tests/`, `pyproject.toml`, and `results/`. No live API calls, keys, network or model downloads.

## Rules for the entry

- No test counts. Do not write numbers of checks or tests.
- Luke's statements are quoted only from the two blocks below, character for character, marked `[Luke]`, with the date 2026-10-21. Do not paraphrase them, extend them, or write any other statement in his voice. Do not add a rationale he did not give.
- Everything you did not verify yourself from a file or a command is marked `[agent-relayed]` or `[APC]`, as given below.
- No accuracy figures or slope values.

## Luke's words (typed by him in conversation, 2026-10-21; copy verbatim)

Block A (inspection of the first pipeline run in `/tmp/phase4_analysis_output`). Question from the APC, 2026-10-21 (first question): whether he looked at any numbers from that run before the evening of 2026-10-20. His answer:

> I looked at it, there were some label overlaps.

Follow-up question from the APC: "besides the label overlaps, did you notice any numbers or results in that output, and did you ask for any change because of what you saw?" His answer:

> None

Block B (peak launches). His words:

> i only remember one instance of peak launch, i already told you, around 3PM tuesday

Earlier typed statement already recorded in D-84 (2)(b), do not repeat as new: "I had to allow peak at 3PM because of time constraints". No statement by Luke exists on the 08:36 S2 launch; do not add one.

## Contents of D-88

(1) Correction to D-84 (7)(b), which says the answer was "NOT PROVIDED" and "not confirmed by Luke": record Block A, both answers, with the two questions as asked (marked as the APC's wording). Do not add any interpretation.

(2) Peak launches. Record Block B as Luke's recollection. Then state, as file evidence and not as his statement, the distinction that D-84 (5)(b) already lists: four launches with `ALLOW_PEAK=1` set (2026-10-19 02:55, 07:08/07:09, 08:36; 2026-10-20 15:02), of which only the 15:02 launch on 2026-10-20 ran inside a peak window (DeepSeek peak is 09:00 to 12:00 and 14:00 to 18:00 PHT Monday to Friday; the other three ran and finished before 09:00 PHT). Luke's recollection of one peak-hour launch is therefore consistent with the file evidence; it is a recollection of peak-hour launches, and it is not a statement that the flag was set once. Check the three off-peak times against the stderr and log files yourself (read-only: `~/run-logs/load.log`, `~/run-logs/run_sweep_batch.sh`) and quote the lines. Add how many individual `run_sweep` invocations received `--allow-peak`; if you cannot re-derive it from those two files, write `[agent-relayed, not re-derived]` with the figure 11. State that the earlier count of six counted recovery targets separately and is superseded by the four batch launches as the unit of count. State that whether the two failed launches at 15:02 on 2026-10-20 also carried the flag is "not established" unless a file shows it (then quote file and line).

(3) Status row corrections, as statements and not edits: the DOC-011 row cites `79046eb`, which is its base, and its own commit is `f50c947`; the ANALYSIS-002 row says "done" but the ANALYSIS-002 pipeline was not accepted by independent review and was superseded by ANALYSIS-002-F. Verify both against `git log` and the report text before writing them, and quote the commands you used in your report.

(4) Final pipeline run. The final output directory is `~/projects/thesis-analysis/final_output_final`, generated at `master` HEAD `554bde3` (confirm the commit name from that directory's `RUN_INFO.txt`; read-only). The source diff `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` returned exit 0 at that HEAD `[Luke, raw terminal output, 2026-10-21]`. The first run of the APC checker on that directory reported two failures in the row-count checks for F1b and F2b; this was a defect in the checker (it compared the companion files with all variants of Table T2 instead of the figure files F1 and F2), corrected outside the repo; the corrected checker then reported 0 failures on the same, unmodified output `[Luke, raw terminal output]`. Write this as provenance, with no counts.

(5) Known limits of the exploratory companion figures, as stated by the APC from a visual read of the PNGs `[APC]`: in F2b Panel B the points for Strategy 2 decide time at n=50 and n=500 are omitted without a footnote on that panel and the line is drawn across the gap (Panel A is the panel to use); in F6b the legend overlaps the Strategy 4 label on the DSA panel and the Strategy 1 label is clipped at the right edge on the Metacademy panel. The pre-registered figures, tables and the F6 dominance files are unchanged by ANALYSIS-003 (this was verified by byte comparison of the CSV and Markdown outputs against the earlier `final_output`; the six PDFs differ between the two directories while their CSVs are identical) `[agent-relayed, from the CHK-001 comparison]`.

(6) Reasoning line and an `Affects:` line naming the two files.

## Status row

One row for DOC-012 in the existing table format, with your branch and commit, and a link to your report. State "docs only".

## Git

Commit in your worktree. `git format-patch -1 -o patch/ master`. Do not push, do not merge, do not remove the worktree.

## Report

Session ID and model label first. Then: the grep outputs for the ID reservation (raw), the exact text of D-88 and the new row, `git diff --stat`, `sha256sum` and `wc -l` of `decision-log.md`, `status.md` and the report, the commands behind point (3) and (2), and a list of everything you could not verify.
