# DOC-012 Task Report: Correcting D-84 (docs only)

- **Session ID**: `97a3cd80-ce9f-4146-ac43-05b81b76da31`
- **Model Label**: `deepseek-flash[1m]`
- **Agent**: `claude-code`
- **Task**: DOC-012 (docs only)
- **Worktree**: `/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-012`
- **Branch**: `task/DOC-012`
- **Base commit**: `554bde34d77fe5807bf897ac034cc59be4206e34` (`554bde3`)
- **D-88 entry commit**: `6f198c5b358a3eb90e339a821d9e4ff57ec5b966` (`6f198c5`)
- **Status row and this report commit**: the follow-up commit on `task/DOC-012` (this report cannot cite its own commit hash)

## Independence Certification

Session `97a3cd80-ce9f-4146-ac43-05b81b76da31` is not one of the excluded sessions
(`1b3efbca`, `512aecca`, `098dcdd4`, `2ebf9668`, `f4b13de1`, `562e3bc6`, `f339a846`,
`d67eabb0`, `c143398c`, `26156499`, `bd54cd76`, `7e5d65e7`, `2d8d6b52`, `c492c7fc`,
`60ce976a`) and does not carry any of the excluded prefixes (`455d24de`, `b8ab4203`,
`900404ed`, `2b098fc9`, `ede0cb54`). This session continued none of them.

## Executive Summary

Appended one correcting entry, [D-88], to `docs/decisions/decision-log.md`, and one
status row, DOC-012, to `docs/tasks/status.md`. No earlier entry, row, or other file was
edited. Docs only: no code, scripts, tests, results, or context documents were touched;
no live API calls, keys, network access, or model downloads were used.

Preflight: the worktree already existed at `task/DOC-012` at `554bde3` and was clean;
`figures/` etc. were untouched. `git worktree list` before writing:

```
/home/lukexodus/projects/llm-graph-insertion-complexity                f6f1b31 [master]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-001-G 48037e3 [task/ANALYSIS-001-G]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002   17ed1f8 [task/ANALYSIS-002]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-003   5ab04a6 [task/ANALYSIS-003]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-007        0b132f7 [task/DOC-007]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-012        554bde3 [task/DOC-012]
```

`git status --short` in the DOC-012 worktree was empty. Master HEAD (`f6f1b31`) is a
descendant of `554bde3` (one line added to `CLAUDE.md`); the task worktree is based on
`554bde3` as required.

## ID reservation evidence (raw)

Run before any edit:

```
$ git grep -n '\[D-88\]' $(git for-each-ref --format='%(refname)' refs/heads refs/remotes | grep -v task/DOC-012)
exit=1
$ git show 554bde3:docs/tasks/status.md | grep -n DOC-012
exit=1
$ git show 554bde3:docs/decisions/decision-log.md | grep -n 'D-88'
exit=1
$ for wt in ...(each worktree)...; do grep -c '\[D-88\]' "$wt/docs/decisions/decision-log.md"; done
ANALYSIS-001-G: 0 (no match)
ANALYSIS-002:   0 (no match)
ANALYSIS-003:   0 (no match)
DOC-007:        0 (no match)
DOC-012:        1 (this task's own edit, added after the checks above)
```

D-88 was free on every ref and in every worktree, and no DOC-012 status row existed.
The prompt's reservation command was run literally (all refs); the re-run above excludes
`task/DOC-012` only because that branch now contains this task's own entry.

## Implementation Details

### 1. Appended entry [D-88] (exact text)

```
**[D-88]** Corrections to the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures (DOC-012):
(1) Correction to [D-84](7)(b), which records the answer as "NOT PROVIDED" and the question as "not confirmed by Luke": the answers were given in conversation on 2026-10-21. The APC's first question (2026-10-21) was whether Luke had looked at any numbers from the first pipeline run in `/tmp/phase4_analysis_output` before the evening of 2026-10-20 [APC wording]. [Luke, 2026-10-21] "I looked at it, there were some label overlaps." The APC's follow-up question was [APC wording]: "besides the label overlaps, did you notice any numbers or results in that output, and did you ask for any change because of what you saw?" [Luke, 2026-10-21] "None". No interpretation is added here.
(2) Peak launches:
  (a) Luke's recollection, typed by him in conversation on 2026-10-21 [Luke]: "i only remember one instance of peak launch, i already told you, around 3PM tuesday"
  (b) File evidence, and not a statement by Luke: [D-84](5)(b) lists four launches with `ALLOW_PEAK=1` set: 2026-10-19 02:55, 2026-10-19 07:08/07:09, 2026-10-19 08:36, and 2026-10-20 15:02. Of these, only the 15:02 launch on 2026-10-20 ran inside a peak window. DeepSeek peak is 09:00 to 12:00 and 14:00 to 18:00 PHT Monday to Friday (the guard defines the windows as `[(1, 4), (6, 10)]` in UTC, `src/graph_insertion/schedule.py`). The other three launches ran and finished before 09:00 PHT on 2026-10-19 (a Monday). `~/run-logs/load.log` records the launch times: "Mon Oct 19 02:55:01 AM PST 2026", "Mon Oct 19 07:08:59 AM PST 2026", "Mon Oct 19 07:13:34 AM PST 2026", "Mon Oct 19 07:14:01 AM PST 2026", "Mon Oct 19 08:36:14 AM PST 2026". The stderr capture modification times record completion, all on 2026-10-19: `sweep_s1_primary.20261019-030410.stderr` at 03:51:14 +0800, `sweep_s1_primary.20261019-071401.stderr` at 08:35:14 +0800, `sweep_s2_06.20261019-083614.stderr` at 08:38:24 +0800, `sweep_s2_05.20261019-083828.stderr` at 08:41:39 +0800, and `sweep_s2_04.20261019-084142.stderr` at 08:47:37 +0800, all under `~/run-logs/`.
  (c) Luke's recollection of one peak launch is therefore consistent with the file evidence; it is a recollection of peak-hour launches, and it is not a statement that the flag was set once.
  (d) Individual `run_sweep` invocations that received `--allow-peak`: 11 [agent-relayed, not re-derived]. This could not be re-derived from the two named files: `~/run-logs/run_sweep_batch.sh` does not exist at that path (the batch script present is `~/projects/thesis-analysis/run_sweep_batch.sh`, sha256 `669eaf9398e2c2804ea74e51dcd33262c7175fe0e79810ab266c58eb387f920b`), and although that script reads `ALLOW_PEAK` from the environment and appends `--allow-peak` to every `run_sweep` invocation in the stage, neither it nor `~/run-logs/load.log` records the environment value used at each launch.
  (e) The earlier count of six counted recovery targets separately; it is superseded by the four batch launches as the unit of count.
  (f) Whether the two failed launches at 15:02 on 2026-10-20 also carried the flag is not established; no file shows it. File note: `~/run-logs/` holds three failed stderr captures in that window, at 15:01:30 (missing key), 15:02:00 and 15:02:26 (bad key string), and none records the command line or the flag.
(3) Status-row corrections, recorded as statements and not as edits to the rows:
  (a) The DOC-011 row of `docs/tasks/status.md` cites commit `79046eb`; `79046eb` is that work's base (merge of `task/ANALYSIS-002-G`), and DOC-011's own commit is `f50c947` (subject "docs(DOC-011): record sweep campaign, pipeline provenance, and plan Amendment 3 (D-84)", parent `79046eb`).
  (b) The ANALYSIS-002 row of `docs/tasks/status.md` says "done" at commit `17ed1f8`, but the initial ANALYSIS-002 pipeline was not accepted by independent review and was superseded by ANALYSIS-002-F (`f5e085d`), which resolved the defects and recommendations identified in that review ([D-84](6)(b); ANALYSIS-002-F report).
(4) Final pipeline run:
  (a) The final output directory is `~/projects/thesis-analysis/final_output_final`, generated at commit `554bde3` (master at the time; master has since advanced to `f6f1b31`). Its `RUN_INFO.txt` records `git_commit: 554bde34d77fe5807bf897ac034cc59be4206e34`, `src_diff_clean: True`, and `overall_gate_status: PASS`.
  (b) `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` returned exit 0 at that HEAD [Luke, raw terminal output, 2026-10-21].
  (c) The first run of the APC checker on that directory reported two failures in the row-count checks for F1b and F2b; this was a defect in the checker (it compared the companion files with all variants of Table T2 instead of the figure files F1 and F2), corrected outside the repo; the corrected checker then reported 0 failures on the same, unmodified output [Luke, raw terminal output].
(5) Known limits of the exploratory companion figures:
  (a) As stated by the APC from a visual read of the PNGs [APC]: in F2b Panel B the points for Strategy 2 decide time at n=50 and n=500 are omitted without a footnote on that panel and the line is drawn across the gap (Panel A is the panel to use); in F6b the legend overlaps the Strategy 4 label on the DSA panel and the Strategy 1 label is clipped at the right edge on the Metacademy panel.
  (b) The pre-registered figures, tables and the F6 dominance files are unchanged by ANALYSIS-003; this was verified by byte comparison of the CSV and Markdown outputs against the earlier `final_output` (the six PDFs differ between the two directories while their CSVs are identical) [agent-relayed, from the CHK-001 comparison].
Reasoning: corrects the [D-84] record with Luke's answers of 2026-10-21, separates peak-hour launches from flag settings using file evidence, corrects two status-row commit claims, records final pipeline provenance, and records the APC's stated limits of the exploratory companion figures, all by later entry rather than by editing earlier text. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`.
```

### 2. Appended status row (exact text)

```
| DOC-012 | Correct the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures ([D-88]) | **needs-review** | Docs only. Completed by Claude Code; branch `task/DOC-012` at commit `6f198c5` (base `554bde3`). See report [`docs/reports/DOC-012-claude-code-correction.md`](docs/reports/DOC-012-claude-code-correction.md). |
```

The cited `6f198c5` is the commit that contains the [D-88] entry. This row and this
report are added in the follow-up commit; the row therefore does not claim to cite the
commit that contains itself.

## Verification & Evidence

### Point (2): peak launches — commands and raw output

```
$ grep -n 'Mon Oct 19 02:55:01\|Mon Oct 19 07:08:59\|Mon Oct 19 07:13:34\|Mon Oct 19 07:14:01\|Mon Oct 19 08:36:14\|Tue Oct 20 03:0' ~/run-logs/load.log
43:Mon Oct 19 02:55:01 AM PST 2026
51:Mon Oct 19 07:08:59 AM PST 2026
53:Mon Oct 19 07:13:34 AM PST 2026
55:Mon Oct 19 07:14:01 AM PST 2026
57:Mon Oct 19 08:36:14 AM PST 2026
69:Tue Oct 20 03:01:30 PM PST 2026
71:Tue Oct 20 03:02:00 PM PST 2026
73:Tue Oct 20 03:02:26 PM PST 2026
75:Tue Oct 20 03:02:43 PM PST 2026

$ ls -la --time-style=full-iso <stderr files>
-rw-r--r-- 1 lukexodus lukexodus  5281 2026-10-19 03:51:14.142596157 +0800 /home/lukexodus/run-logs/sweep_s1_primary.20261019-030410.stderr
-rw-r--r-- 1 lukexodus lukexodus 14042 2026-10-19 08:35:14.998768527 +0800 /home/lukexodus/run-logs/sweep_s1_primary.20261019-071401.stderr
-rw-r--r-- 1 lukexodus lukexodus  1257 2026-10-19 08:47:37.146303557 +0800 /home/lukexodus/run-logs/sweep_s2_04.20261019-084142.stderr
-rw-r--r-- 1 lukexodus lukexodus   772 2026-10-19 08:41:39.313623038 +0800 /home/lukexodus/run-logs/sweep_s2_05.20261019-083828.stderr
-rw-r--r-- 1 lukexodus lukexodus   584 2026-10-19 08:38:24.435580088 +0800 /home/lukexodus/run-logs/sweep_s2_06.20261019-083614.stderr

$ ls -la ~/run-logs/run_sweep_batch.sh
ls: cannot access '/home/lukexodus/run-logs/run_sweep_batch.sh': No such file or directory
exit=2

$ sha256sum ~/projects/thesis-analysis/run_sweep_batch*.sh
669eaf9398e2c2804ea74e51dcd33262c7175fe0e79810ab266c58eb387f920b  /home/lukexodus/projects/thesis-analysis/run_sweep_batch.sh
669eaf9398e2c2804ea74e51dcd33262c7175fe0e79810ab266c58eb387f920b  /home/lukexodus/projects/thesis-analysis/run_sweep_batch_v3.sh

$ date -d 2026-10-19 +%A; date -d 2026-10-20 +%A
Monday
Tuesday

$ sed -n '19,21p;24,28p' src/graph_insertion/schedule.py
# Peak windows as (start_hour_inclusive, end_hour_exclusive) in UTC, Mon–Fri only.
# [D-37]: 01:00–04:00 and 06:00–10:00 UTC.
_PEAK_WINDOWS: list[tuple[int, int]] = [(1, 4), (6, 10)]
def is_deepseek_peak(dt_utc: datetime.datetime) -> bool:
    """Return True if *dt_utc* falls in a DeepSeek peak-pricing window.

    Peak is defined as Monday–Friday (weekday 0–4) during either
    01:00–03:59:59 UTC or 06:00–09:59:59 UTC [D-37].

$ grep -n 'ALLOW_PEAK' ~/projects/thesis-analysis/run_sweep_batch.sh
12:#   ALLOW_PEAK=1    pass --allow-peak to run_experiment.py to permit execution during DeepSeek peak pricing hours
29:ALLOW_PEAK="${ALLOW_PEAK:-0}"
60:echo "Start: $(date -Is)  weekday=$(date +%A)  HEAD=$(git rev-parse --short HEAD)  stage=$STAGE  dryrun=$DRYRUN  allow_peak=$ALLOW_PEAK"
92:  [ "$ALLOW_PEAK" = 1 ] && extra+=(--allow-peak)
```

The `15:01:30`/`15:02:00`/`15:02:26` stderr captures in full:

```
ERROR: DEEPSEEK_API_KEY is required for live execution. Set the environment variable or pass api_key.
[brute_force/n=2000] 1/2000 calls (trial 1/1) elapsed=0.6s ETA=1242.8s retries=0
Experiment execution failed: Illegal header value b'Bearer \nexport DEEPSEEK_API_KEY="$(wl-paste -n)"'
[brute_force/n=2000] 1/2000 calls (trial 1/1) elapsed=0.4s ETA=724.9s retries=0
Experiment execution failed: Illegal header value b'Bearer \nexport DEEPSEEK_API_KEY="$(wl-paste -n)"'
```

UTC window `[(1, 4), (6, 10)]` maps to 09:00–12:00 and 14:00–18:00 at UTC+8 (PHT).
All three 2026-10-19 launches and all their completions are before 09:00 PHT.

### Point (3): status-row commit corrections — commands and raw output

```
$ git log -1 --format='%H%n%s%nparents: %P' f50c947
f50c94779931bd2e0647ce8731286ceda4e761f3
docs(DOC-011): record sweep campaign, pipeline provenance, and plan Amendment 3 (D-84)
parents: 79046ebf1fd6f419701e815d55ea9fc7d59a49bb

$ git log -1 --format='%H%n%s%nparents: %P' 79046eb
79046ebf1fd6f419701e815d55ea9fc7d59a49bb
Merge branch 'task/ANALYSIS-002-G'
parents: 7997e1b379ab955f914b46722ce33486c4f6cbf5 ccec59c992aecc90d0a61ad5bae231a77e0518e0

$ git log --oneline --all | grep -i 'DOC-011\|ANALYSIS-002'
f50c947 docs(DOC-011): record sweep campaign, pipeline provenance, and plan Amendment 3 (D-84)
79046eb Merge branch 'task/ANALYSIS-002-G'
ccec59c docs(ANALYSIS-002-G): add independent review report for ANALYSIS-002-F
f5e085d fix(ANALYSIS-002-F): repair Phase 4 analysis pipeline after review and record D-86
17ed1f8 feat(analysis): implement and wire Phase 4 analysis pipeline and record D-85 (ANALYSIS-002)

$ git log --oneline task/ANALYSIS-002 -5
17ed1f8 feat(analysis): implement and wire Phase 4 analysis pipeline and record D-85 (ANALYSIS-002)
aa88e7d feat: adopt framework improvements (...)
48037e3 docs: add ANALYSIS-001-G independent review of ANALYSIS-001-F validator
ad81414 docs: add ANALYSIS-001-F gemini verification and execution report
939a2bf docs: append analysis plan Amendment 2 and record [D-83] (ANALYSIS-001-F)

$ grep -n 'ANALYSIS-002 |' docs/tasks/status.md
77:| ANALYSIS-002 | Implement and wire Phase 4 empirical analysis pipeline (`scripts/analysis/`), benchmark figures, tables, and record D-85 | **done** | Completed by Gemini; branch `task/ANALYSIS-002` at commit `17ed1f8` (base `48037e3`). See report [`docs/reports/ANALYSIS-002-gemini-report.md`](docs/reports/ANALYSIS-002-gemini-report.md). |

$ grep -n 'resolves all defects' docs/reports/ANALYSIS-002-F-gemini-report.md
14:This task resolves all defects and recommendations identified in the independent review of the Phase 4 empirical analysis pipeline:
```

`task/DOC-011` no longer exists as a branch (`git log task/DOC-011` returns
`fatal: ambiguous argument`), so the DOC-011 commit was confirmed from `f50c947`'s
parentage instead. The "not accepted by independent review" statement also rests on
[D-84](6)(b); the review report of the initial ANALYSIS-002 implementation is not in
`docs/reports/` (only ANALYSIS-002, ANALYSIS-002-F and ANALYSIS-002-G reports exist).

### Point (4): final pipeline run

```
$ cat ~/projects/thesis-analysis/final_output_final/RUN_INFO.txt
argv: scripts/analysis/run_analysis.py --results-dir /home/lukexodus/projects/llm-graph-insertion-complexity/results --output-dir /home/lukexodus/projects/thesis-analysis/final_output_final --src-diff-clean --hashes /home/lukexodus/run-logs/final-results-hashes.txt
results_dir: /home/lukexodus/projects/llm-graph-insertion-complexity/results
git_commit: 554bde34d77fe5807bf897ac034cc59be4206e34
...
src_diff_clean: True
overall_gate_status: PASS

$ git rev-parse HEAD
554bde34d77fe5807bf897ac034cc59be4206e34
$ git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml; echo "src-diff exit=$?"
src-diff exit=0
```

The re-executed diff check at `554bde3` returned 0, matching the exit 0 Luke reported
as raw terminal output [Luke, 2026-10-21]. The APC checker runs (two failures from the
checker defect, then 0 failures after correcting the checker outside the repo) were not
re-executed here; they are recorded in [D-88](4)(c) as [Luke, raw terminal output].

## Git Diff

`git diff --stat 554bde3 6f198c5` (decision-log entry commit):

```
 docs/decisions/decision-log.md | 21 +++++++++++++++++++++
 1 file changed, 21 insertions(+)
```

Unified diff of the [D-88] entry (`git diff 554bde3 6f198c5`):

```diff
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index 9633806..d5cf71e 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -805,3 +805,24 @@ Reasoning: records the complete operational timeline and protocol deviations of
 (5) F6b deterministic annotation placement and dominance reuse: Annotations in F6b are placed deterministically by sorting points by x and alternating vertical offsets with leader lines and bounding boxes, preventing pairwise annotation label collisions. Pairwise Pareto dominance evaluation reuses `stats.evaluate_dominance` unchanged from F6 and displays results in an identical text box without duplicate dominance CSV generation.
 (6) Pre-registered figures and tables unmodified: Pre-registered Figures F1, F2, F4, F5, and F6, dominance files (`F6_dominance.csv`, `F6_dominance.md`), and all benchmark and inventory tables (T1, T2, T2b, T3, T4) remain strictly unchanged, certified by byte-level diffs against `final_output` (see no-change proof in task report).
 Reasoning: provides readable log-scale visualisations of candidate-narrowing scaling behaviour and resolves label collision without altering pre-registered analysis artifacts or pre-registration commitments. Affects: `scripts/analysis/figures.py`, `scripts/analysis/run_analysis.py`, `tests/test_analysis_pipeline.py`, `docs/decisions/decision-log.md`.
+
+**[D-88]** Corrections to the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures (DOC-012):
+(1) Correction to [D-84](7)(b), which records the answer as "NOT PROVIDED" and the question as "not confirmed by Luke": the answers were given in conversation on 2026-10-21. The APC's first question (2026-10-21) was whether Luke had looked at any numbers from the first pipeline run in `/tmp/phase4_analysis_output` before the evening of 2026-10-20 [APC wording]. [Luke, 2026-10-21] "I looked at it, there were some label overlaps." The APC's follow-up question was [APC wording]: "besides the label overlaps, did you notice any numbers or results in that output, and did you ask for any change because of what you saw?" [Luke, 2026-10-21] "None". No interpretation is added here.
+(2) Peak launches:
+  (a) Luke's recollection, typed by him in conversation on 2026-10-21 [Luke]: "i only remember one instance of peak launch, i already told you, around 3PM tuesday"
+  (b) File evidence, and not a statement by Luke: [D-84](5)(b) lists four launches with `ALLOW_PEAK=1` set: 2026-10-19 02:55, 2026-10-19 07:08/07:09, 2026-10-19 08:36, and 2026-10-20 15:02. Of these, only the 15:02 launch on 2026-10-20 ran inside a peak window. DeepSeek peak is 09:00 to 12:00 and 14:00 to 18:00 PHT Monday to Friday (the guard defines the windows as `[(1, 4), (6, 10)]` in UTC, `src/graph_insertion/schedule.py`). The other three launches ran and finished before 09:00 PHT on 2026-10-19 (a Monday). `~/run-logs/load.log` records the launch times: "Mon Oct 19 02:55:01 AM PST 2026", "Mon Oct 19 07:08:59 AM PST 2026", "Mon Oct 19 07:13:34 AM PST 2026", "Mon Oct 19 07:14:01 AM PST 2026", "Mon Oct 19 08:36:14 AM PST 2026". The stderr capture modification times record completion, all on 2026-10-19: `sweep_s1_primary.20261019-030410.stderr` at 03:51:14 +0800, `sweep_s1_primary.20261019-071401.stderr` at 08:35:14 +0800, `sweep_s2_06.20261019-083614.stderr` at 08:38:24 +0800, `sweep_s2_05.20261019-083828.stderr` at 08:41:39 +0800, and `sweep_s2_04.20261019-084142.stderr` at 08:47:37 +0800, all under `~/run-logs/`.
+  (c) Luke's recollection of one peak launch is therefore consistent with the file evidence; it is a recollection of peak-hour launches, and it is not a statement that the flag was set once.
+  (d) Individual `run_sweep` invocations that received `--allow-peak`: 11 [agent-relayed, not re-derived]. This could not be re-derived from the two named files: `~/run-logs/run_sweep_batch.sh` does not exist at that path (the batch script present is `~/projects/thesis-analysis/run_sweep_batch.sh`, sha256 `669eaf9398e2c2804ea74e51dcd33262c7175fe0e79810ab266c58eb387f920b`), and although that script reads `ALLOW_PEAK` from the environment and appends `--allow-peak` to every `run_sweep` invocation in the stage, neither it nor `~/run-logs/load.log` records the environment value used at each launch.
+  (e) The earlier count of six counted recovery targets separately; it is superseded by the four batch launches as the unit of count.
+  (f) Whether the two failed launches at 15:02 on 2026-10-20 also carried the flag is not established; no file shows it. File note: `~/run-logs/` holds three failed stderr captures in that window, at 15:01:30 (missing key), 15:02:00 and 15:02:26 (bad key string), and none records the command line or the flag.
+(3) Status-row corrections, recorded as statements and not as edits to the rows:
+  (a) The DOC-011 row of `docs/tasks/status.md` cites commit `79046eb`; `79046eb` is that work's base (merge of `task/ANALYSIS-002-G`), and DOC-011's own commit is `f50c947` (subject "docs(DOC-011): record sweep campaign, pipeline provenance, and plan Amendment 3 (D-84)", parent `79046eb`).
+  (b) The ANALYSIS-002 row of `docs/tasks/status.md` says "done" at commit `17ed1f8`, but the initial ANALYSIS-002 pipeline was not accepted by independent review and was superseded by ANALYSIS-002-F (`f5e085d`), which resolved the defects and recommendations identified in that review ([D-84](6)(b); ANALYSIS-002-F report).
+(4) Final pipeline run:
+  (a) The final output directory is `~/projects/thesis-analysis/final_output_final`, generated at commit `554bde3` (master at the time; master has since advanced to `f6f1b31`). Its `RUN_INFO.txt` records `git_commit: 554bde34d77fe5807bf897ac034cc59be4206e34`, `src_diff_clean: True`, and `overall_gate_status: PASS`.
+  (b) `git diff --quiet 3323bfb HEAD -- src scripts/run_experiment.py pyproject.toml` returned exit 0 at that HEAD [Luke, raw terminal output, 2026-10-21].
+  (c) The first run of the APC checker on that directory reported two failures in the row-count checks for F1b and F2b; this was a defect in the checker (it compared the companion files with all variants of Table T2 instead of the figure files F1 and F2), corrected outside the repo; the corrected checker then reported 0 failures on the same, unmodified output [Luke, raw terminal output].
+(5) Known limits of the exploratory companion figures:
+  (a) As stated by the APC from a visual read of the PNGs [APC]: in F2b Panel B the points for Strategy 2 decide time at n=50 and n=500 are omitted without a footnote on that panel and the line is drawn across the gap (Panel A is the panel to use); in F6b the legend overlaps the Strategy 4 label on the DSA panel and the Strategy 1 label is clipped at the right edge on the Metacademy panel.
+  (b) The pre-registered figures, tables and the F6 dominance files are unchanged by ANALYSIS-003; this was verified by byte comparison of the CSV and Markdown outputs against the earlier `final_output` (the six PDFs differ between the two directories while their CSVs are identical) [agent-relayed, from the CHK-001 comparison].
+Reasoning: corrects the [D-84] record with Luke's answers of 2026-10-21, separates peak-hour launches from flag settings using file evidence, corrects two status-row commit claims, records final pipeline provenance, and records the APC's stated limits of the exploratory companion figures, all by later entry rather than by editing earlier text. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`.
```

Unified diff of the status row (`git diff -- docs/tasks/status.md`):

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 29ea861..427c90c 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -78,6 +78,7 @@ Status: **in-progress**
 | ANALYSIS-002-F | Remediate Phase 4 analysis pipeline review defects, enforce validation gate, implement Rules R1–R3, and record D-86 | **done** | Completed by Gemini; branch `task/ANALYSIS-002-F` at commit `f5e085d` (base `17ed1f8`). See report [`docs/reports/ANALYSIS-002-F-gemini-report.md`](docs/reports/ANALYSIS-002-F-gemini-report.md). |
 | ANALYSIS-002-G | Independent review of ANALYSIS-002-F Phase 4 analysis pipeline remediation | **done** | Completed by Gemini; branch `task/ANALYSIS-002-G` at commit `ccec59c` (base `f5e085d`). See report [`docs/reports/ANALYSIS-002-G-gemini-review.md`](docs/reports/ANALYSIS-002-G-gemini-review.md). |
 | ANALYSIS-003 | Add exploratory log-scale companion figures F1b, F2b, F6b and record D-87 | **done** | Completed by Gemini; branch `task/ANALYSIS-003` at commit `5ab04a6` (base `79046eb`). See report [`docs/reports/ANALYSIS-003-gemini-report.md`](docs/reports/ANALYSIS-003-gemini-report.md). |
+| DOC-012 | Correct the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures ([D-88]) | **needs-review** | Docs only. Completed by Claude Code; branch `task/DOC-012` at commit `6f198c5` (base `554bde3`). See report [`docs/reports/DOC-012-claude-code-correction.md`](docs/reports/DOC-012-claude-code-correction.md). |
 
 ## Thesis document status (separate track from the code work above)
```

The `i/` and `w/` prefixes above are git's own output (mnemonic diff prefixes for index
and worktree), not retyped.

## Patch Files

```
$ mkdir -p patch
$ git format-patch -1 -o patch/ master
patch/0001-CLAUDE.md.patch
$ git format-patch -o patch/ master
patch/0001-docs-DOC-012-record-D-88-corrections-to-D-84.patch
patch/0002-docs-DOC-012-add-status-row-and-correction-report.patch
```

Deviation from the prompt's literal command, reported rather than hidden:
`git format-patch -1 -o patch/ master` exports the topmost commit of `master` itself
(`f6f1b31`, the `CLAUDE.md` commit), not the DOC-012 commits, because `-1` applies to
the named revision. The exported `patch/0001-CLAUDE.md.patch` was therefore removed: it
is not part of this unit of work. The DOC-012 series is the two files above, produced by
`git format-patch -o patch/ master`, one per commit (entry; status row plus report).
`patch/` is gitignored, so these files are deliverables, not tracked changes.

## Hashes and Line Counts

```
$ sha256sum docs/decisions/decision-log.md docs/tasks/status.md
a104b64860e3e99ef563eaa24cb60ea645210d5b9c74fc80de42efccb2de200c  docs/decisions/decision-log.md
4b27a5e59e8df04312abcf7d253139df18de71a38a21a606a3b0e7d6c831cd3e  docs/tasks/status.md
$ wc -l docs/decisions/decision-log.md docs/tasks/status.md docs/reports/DOC-012-claude-code-correction.md
828 docs/decisions/decision-log.md
126 docs/tasks/status.md
352 docs/reports/DOC-012-claude-code-correction.md
```

The sha256 of this report is not self-embedded (writing it would change the file); the
APC can compute it with `sha256sum docs/reports/DOC-012-claude-code-correction.md`.

## Items Not Verified / Flagged for the APC

1. **`11` allow-peak invocations** — `[agent-relayed, not re-derived]`. Neither
   `~/run-logs/load.log` nor the batch script records which launches had
   `ALLOW_PEAK=1`; the script only propagates an environment variable. The count is
   consistent with 4+3+3+1 across the four launches, but that decomposition depends on
   [D-84](5)(b)'s list, not on the two files.
2. **Prompt path mismatch**: `~/run-logs/run_sweep_batch.sh` does not exist. The batch
   script that exists is `~/projects/thesis-analysis/run_sweep_batch.sh` (identical
   sha256 to `run_sweep_batch_v3.sh`). It was read instead.
3. **Failed launches at 15:02**: [D-84](1)(f) says "two failed launches"; the run logs
   hold three failed stderr captures in that window (15:01:30 missing key, 15:02:00 and
   15:02:26 bad key string). No file shows whether any carried `--allow-peak`.
4. **CHK-001 byte-comparison claim** in [D-88](5)(b) — `[agent-relayed, from the
   CHK-001 comparison]`; not re-run here.
5. **Visual-read limits of F2b and F6b** in [D-88](5)(a) — `[APC]` statement; not
   re-inspected here.
6. **APC checker outcomes** in [D-88](4)(c) — [Luke, raw terminal output]; the checker
   lives outside the repo and was not re-run.
7. **"Master at the time"** for `final_output_final` — inferred from `RUN_INFO.txt`
   recording `554bde3` while master now stands at `f6f1b31`.
8. **Review report of the initial ANALYSIS-002 implementation** — not present in
   `docs/reports/`; the "not accepted" statement rests on [D-84](6)(b) and the
   ANALYSIS-002-F report's wording.
9. **Status-row commit field** — the row cites `6f198c5` (the [D-88] entry commit); the
   row and this report are in the following commit. No self-referential hash was written.
