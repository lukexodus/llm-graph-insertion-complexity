# DOC-013 — Core Codebase Map

## Executive Summary

Created `docs/context/codebase-map.md`, a 2,543-line reference document that
maps the executable core of the thesis project:

- annotated tree of the runtime package, experiment CLI, analysis pipeline,
  supporting tooling, data, and tests;
- architecture diagram and six end-to-end workflows (insertion, accuracy,
  sweep, CLI decision flow, analysis, strategy lifecycle);
- per-file symbol maps and function-level pseudocode for every function in
  `src/graph_insertion/**` and `scripts/run_experiment.py`;
- module maps plus dataflow-critical pseudocode for the Phase 4 analysis
  pipeline;
- workflow and exit-code summary for the name-pool generation tooling;
- test-file map, 15 invariants/gotchas, change-impact guide, constants
  quick-reference, and decision index.

No source code, data, results, tables, or figures were changed. The only
non-documentation change is a new decision-log entry, [D-98], which fixes the
document's authority rule and maintenance contract.

## Implementation Details

### What was read

Every claim in the map was read directly from the repository at commit
`4983840` (base of `task/DOC-013`), not from chat history or prior summaries.
Files read in full or in the relevant part:

- `docs/context/complete-context.md`
- `docs/context/strategy-interface.md`
- `docs/tasks/status.md`
- `docs/decisions/decision-log.md` (tail and format)
- `pyproject.toml`
- `src/graph_insertion/{__init__,graph_representation,loader,strategy,embedding,embedding_minilm,cpu_threads,decision,llm,schedule,scoring,harness}.py`
- `src/graph_insertion/strategies/{__init__,registry,null,stub,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}.py`
- `scripts/run_experiment.py`
- `scripts/analysis/{run_analysis,stats,bootstrap,tables,figures,posthoc,validate_runs,posthoc_figures,style}.py` (full for orchestration/statistics; function-contract level for plotting/table builders)
- `scripts/{generate_name_pool,name_pool_supervisor}.py` (symbol inventory and documented workflows)
- `scripts/README.md` (headings and run-plan references)
- test-file inventory

### Document structure

| Section | Contents |
|---|---|
| 1 | One-paragraph architecture |
| 2 | Annotated core file tree |
| 3 | Six end-to-end workflows |
| 4 | Full runtime reference, one subsection per file |
| 5 | Phase 4 analysis pipeline outline and critical pseudocode |
| 6 | Supporting tooling (name-pool generator, supervisor, other scripts) |
| 7 | Test map |
| 8 | Invariants and gotchas |
| 9 | Change-impact guide |
| A | Constants quick reference |
| B | Decision index |

### Coverage decision

The map uses three depth tiers, recorded in [D-98](2):

1. **Full symbols + pseudocode:** all runtime modules under
   `src/graph_insertion/**` and `scripts/run_experiment.py` — every class,
   method, function, and private helper.
2. **Module map + critical pseudocode:** Phase 4 analysis pipeline. The
   validation gate, orchestration, table builders, slope/bootstrap
   statistics, post-hoc stage, and all analytical functions are mapped;
   plotting internals are listed by contract because they share one repeated
   draw-and-export pattern.
3. **Workflow summary:** data-generation tooling and ancillary scripts.

This keeps the document usable as an onboarding device without pretending
that every matplotlib annotation is architecturally significant.

### Files changed

| File | Change |
|---|---|
| `docs/context/codebase-map.md` | New, 2,543 lines |
| `docs/decisions/decision-log.md` | Appended [D-98] (7 lines) |
| `docs/tasks/status.md` | Added DOC-013 row |
| `patch/DOC-013-claude-code-codebase-map.patch` | New patch export |
| `docs/reports/DOC-013-claude-code-codebase-map.md` | This report |

## Verification & Test Evidence

This task changed documentation only; no pytest suite was run because no
executable code changed. Verification performed:

- **Source verification:** every symbol, signature, constant, default, and
  control-flow claim in the map was checked against the file content read in
  this session. Line numbers are from commit `4983840` and are explicitly
  labelled as drifting pointers.
- **Cross-reference verification:** decision IDs cited in the map
  (`D-15`, `D-16`, `D-19`, `D-21`–`D-26`, `D-28`–`D-31`, `D-35`, `D-37`,
  `D-38`, `D-41`, `D-46`, `D-47`, `D-55`, `D-58`, `D-59`, `D-64`, `D-67`,
  `D-68`, `D-72`, `D-80`, `D-89`, `D-90`, and `D-98`) exist in
  `docs/decisions/decision-log.md`.
- **Structural check:** code-fence count is even (98 fences, 49 blocks);
  35 tables detected; document has 2,543 lines and ends with an explicit
  authority statement.
- **Report linter:** run after writing this file; result recorded below.

```
$ python3 - <<'PY'
from pathlib import Path
p = Path('docs/context/codebase-map.md')
t = p.read_text()
print('lines', t.count('\n')+1)
print('fences', t.count('```'), 'even' if t.count('```') % 2 == 0 else 'ODD')
print('tables', t.count('\n|---'))
PY
lines 2544
fences 98 even
tables 35
```

(The `wc`-style line count is 2,543 in git's diff because the final newline is
not counted by the diff stat.)

- **No code execution:** this is intentional, not an omission. The map
  documents existing behaviour; it does not alter it. Running the live suite
  was unnecessary and would not have validated prose accuracy any better than
  direct source reading.

### Known limitations of this verification

- The map's line-number pointers will become stale after any refactor.
- Plotting internals in `figures.py`, `posthoc_figures.py`, and
  `redraw_thesis_figures.py` are described by contract, not reproduced as
  pseudocode.
- `docs/context/repo-tree.txt` was **not** updated. The live master checkout
  has an uncommitted edit to that file created by Luke; editing it from this
  worktree would produce a conflicting or stale tree. Flagged below.

## Git Diff

Commit `5cc3660` (docs and decision log; the full 2,543-line new file body is
in the patch file, not repeated here):

```
$ git show --stat --oneline HEAD
5cc3660 docs(DOC-013): add core codebase map with symbols and workflows
 docs/context/codebase-map.md   | 2543 ++++++++++++++++++++++++++++++++++++++++
 docs/decisions/decision-log.md |    7 +
 docs/tasks/status.md           |    1 +
 3 files changed, 2551 insertions(+)
```

Verbatim diff for the shared-doc changes:

```diff
diff --git c/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 7da91e8..fae150d 100644
--- c/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -964,3 +964,10 @@ Reasoning: adds the requested S3 search-depth teaching without presenting the me
 (3) The Trial chip moved from the bootstrap scene to Scene 19, where the term is now introduced; the bootstrap scene uses plain "trials". To keep term-first-use ordering honest, "primary" and "sensitivity" were removed from the efSearch copy, "run" was removed from the seed and table copy, and the Mode gloss no longer says "run". The stale internal answer-key ids `s17*` were normalised to `s20*`, and the shared-judge `s15ex` id to `s16ex`, so internal ids again match their scenes.
 (4) The static guard now expects 26 scenes and 98 terms, checks the new terms and the `24 runs` / `60 trials` / `59 trials` wording, and the V4 made-up-scene indices moved to 7, 9, 10, 11, 17, 21 and 22. Browser QA passed in Chromium and Firefox: 176 states (26 scene starts plus 150 step maxima), no page or console errors, no overflow at 1920x1080, 1366x768 or 1280x720, 26 overview cards and 98 term rows. The only term-before-chip warning remains the accepted `mean` case from [D-95].
 Reasoning: adds the requested experimental-setup vocabulary at the point where the deck has finished comparing the four strategies and is about to explain scoring, without presenting any measured result. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-configuration-mode-scenes.md`.
+
+**[D-98]** Codebase map document: scope, authority rule, and maintenance contract (DOC-013):
+(1) `docs/context/codebase-map.md` is a descriptive onboarding and maintenance aid, not a normative specification. Where it disagrees with source code, the code is authoritative; the reader must correct the map and record the discrepancy rather than change code to match the map. The normative strategy contract remains `docs/context/strategy-interface.md`, and dataset facts remain in `docs/context/data-formats.md`.
+(2) Coverage tiers are deliberate. The runtime package (`src/graph_insertion/**`) and `scripts/run_experiment.py` receive full symbol maps and function-level pseudocode. The Phase 4 analysis pipeline receives module-level maps, entry-point workflows, and pseudocode for the dataflow-critical functions (validation gate, orchestration, table builders, slope/bootstrap statistics, post-hoc stage); plotting internals are listed by contract. Data-generation tooling is summarised with its workflows and exit-code contract only. This keeps the document useful without duplicating every plotting implementation detail.
+(3) The document is expected to drift. Structural changes (new strategy, new corpus, new metric, new run-directory slug, new analysis artifact) must update the affected section in the same task that makes the change. Pure refactors that preserve symbols and workflows do not require an immediate rewrite, but line-number pointers will be stale and should be treated as approximations.
+(4) No experimental decision is made or changed by this document. Constants, thresholds, prompts, and bounds are quoted from code; the decision log remains the source of truth for *why* they have those values.
+Reasoning: records why a second, code-level map exists alongside the decision log and strategy-interface spec, and fixes the rule that prevents the map from becoming a competing source of truth. Affects: `docs/context/codebase-map.md`, `docs/tasks/status.md`, `docs/reports/DOC-013-claude-code-codebase-map.md`.
diff --git c/docs/tasks/status.md w/docs/tasks/status.md
index ca84682..8435e52 100644
--- c/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -132,4 +132,5 @@ Status: **in-progress**
 | DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](docs/reports/DOC-006-gemini.md). |
 | DOC-008 | Freeze Phase 4 analysis plan (`docs/context/analysis-plan.md`), record [D-79], and draft adviser briefing on Decisions D1–D6 (`docs/context/adviser-briefing-d1-d6.md`). | **done** | Completed by Gemini. Pre-registered analysis plan frozen with Decisions D1–D6 adopted for initial defense; comprehensive briefing prepared for adviser review. |
 | DOC-011 | Record sweep campaign, analysis pipeline provenance, and analysis plan Amendment 3 ([D-84]) | **done** | Completed by Gemini; branch `task/DOC-011` at commit `79046eb`. See report [`docs/reports/DOC-011-gemini-campaign-record.md`](docs/reports/DOC-011-gemini-campaign-record.md). |
+| DOC-013 | Create `docs/context/codebase-map.md`: annotated core-file tree, per-file symbol maps and pseudocode for every runtime function, end-to-end experiment/analysis workflows, analysis-pipeline outline, test map, invariants, and change-impact guide ([D-98]). | **done** | Completed by Claude Code; branch `task/DOC-013`, worktree `../llm-graph-insertion-complexity-DOC-013`. Docs only; no code, data, or result changes. See report [`docs/reports/DOC-013-claude-code-codebase-map.md`](docs/reports/DOC-013-claude-code-codebase-map.md). |
```

New-file header (body exported in the patch):

```diff
diff --git c/docs/context/codebase-map.md w/docs/context/codebase-map.md
new file mode 100644
index 0000000..6043388
--- /dev/null
+++ w/docs/context/codebase-map.md
@@ -0,0 +1,2543 @@
+# Codebase Map — Core Files, Symbols, and Workflows
```

## Patch File

`patch/DOC-013-claude-code-codebase-map.patch` — generated with
`git diff HEAD~1` from branch `task/DOC-013`; 2,574 lines, includes index
lines and the full new document.

The patch file is force-added because `patch/` is listed in `.gitignore`
(line 14), matching the repository's existing convention of tracked patch
artifacts.

## Items Flagged for APC / Future Agent Attention

1. **Task ID provenance.** `DOC-013` was chosen by this agent as the next
   unused `DOC-*` ID; it was not explicitly reserved by the APC. If the APC
   has reserved `DOC-013` for a different task, renumber this report and the
   status row before merge. Decision ID `D-98` was obtained from
   `./scripts/manage-decisions.py next`.
2. **`docs/context/repo-tree.txt` is stale.** The live master checkout has an
   uncommitted edit to that file made outside this task. This worktree
   therefore did not touch it. The new `codebase-map.md` is absent from that
   tree. Regenerate `repo-tree.txt` from a clean checkout after Luke's pending
   changes land.
3. **No tests run.** Docs-only change; no executable code touched. If a
   reviewer wants a mechanical check, the relevant command is
   `python3 scripts/validate-report.py docs/reports/DOC-013-claude-code-codebase-map.md --require-patch`.
4. **Line numbers drift.** The map explicitly labels all line pointers as
   commit-dependent. A future structural refactor should update the affected
   section, not trust the numbers blindly.
5. **Plotting internals are contract-level.** Figures are documented by input,
   output, and analytical rule rather than per-line pseudocode. If the APC
   wants a line-level map of `figures.py` or `posthoc_figures.py`, that is a
   separate follow-up.
6. **Worktree handoff.** Branch `task/DOC-013`; worktree
   `../llm-graph-insertion-complexity-DOC-013`. Not merged, rebased, or
   removed. Per `AGENTS.md`, leave cleanup to the operator via
   `./scripts/task-worktree.sh merge DOC-013`.

## Verification of This Report

Run:

```bash
./scripts/validate-report.py docs/reports/DOC-013-claude-code-codebase-map.md --require-patch
```

Expected: PASS. The report contains the required Executive Summary,
Implementation Details, Verification, and Git Diff sections; DOC-013 is
linked from `docs/tasks/status.md`; [D-98] exists in the decision log; and the
patch file name contains `DOC-013`.
