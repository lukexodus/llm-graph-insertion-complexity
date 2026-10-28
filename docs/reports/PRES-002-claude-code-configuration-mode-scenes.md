# Task Report: PRES-002 — Configuration, mode, run, trial scenes

**Date:** 2026-10-28
**Agent:** claude-code
**Task ID:** PRES-002 (follow-up to the original deck build)
**Status:** needs-review
**Commit:** one commit on `task/PRES-002` — `feat(PRES-002): add configuration and mode scenes`
**Patch File:** `patch/PRES-002-claude-code-configuration-mode-scenes.patch`

---

## 1. Executive Summary

The two earlier follow-ups (95% bootstrap interval scene, efSearch scene) were merged to `master` as `e5137fd`. After that merge, two scenes were added to `docs/presentation/background-deck/background-concepts.html`:

- **Scene 18, "One dial at a time"** — configuration, primary setting, sensitivity setting, and the 12-configuration matrix.
- **Scene 19, "From setup to one insertion"** — mode, run, trial, 24 runs, and the 60/59 trial counts.

They sit after Scene 17 (The four, side by side) and before the accuracy material. The former Scenes 18–24 are now Scenes 20–26. The deck is **26 scenes and 98 gloss-bank terms**.

Scene 18 teaches: a configuration is one strategy plus its settings; the primary configuration is the main setting chosen before measurements; a sensitivity configuration moves one setting and holds the rest; 4 primary + 8 sensitivity = 12 configurations; and the eight sensitivity settings are θ 0.4/0.5, k 5/20, efSearch 64/256, and bucket bounds (2,5)/(10,20).

Scene 19 teaches: mode is what we measure (cost or accuracy); a run is one complete execution of one configuration in one mode; a trial is one insertion inside a run; 12 configurations × 2 modes = 24 runs; a cost run has 60 trials (10 at each of six map sizes); an accuracy run has 59 trials (29 DSA + 30 from the other gold map); and the trial is the unit averaged and compared.

No Chapter 4 result, measured value, model identity, gate, ranking or TOPSIS appears. The counts (12 configurations, 24 runs, 60/59 trials) are method facts from the analysis plan, not results.

Verification: static guard 10/10; Chromium and Firefox visited 176 states (26 scene starts plus 150 per-scene step maxima) with no page or console errors and no overflow at 1920×1080, 1366×768 or 1280×720; overview builds 26 scene cards and 98 term rows. The earlier merge was verified with the static guard on `master`.

## 2. Implementation Details

### 2.1 Changes Made

- `docs/presentation/background-deck/background-concepts.html`: new `#s18` and `#s19` sections and scoped CSS; five new terms (`Configuration`, `Primary`, `Sensitivity`, `Mode`, `Run`); `Trial` moved to Scene 19; positional renumbering of the former Scenes 18–24 to 20–26 (HTML ids, CSS class prefixes, renderer names, comments, timer variable). Size is now 291,561 bytes; SHA-256 `ae671e85e6bfa5bcdfcce800f6c9401881b8119b417be2b5bd4165c4905dc48a`.
- `tests/test_background_deck_static.py`: scene default 26; new terms in the gloss-bank list; required phrases `24 runs`, `60 trials`, `59 trials`, `primary`, `sensitivity`; V4 made-up-scene indices moved to 7, 9, 10, 11, 17, 21 and 22.
- `docs/tasks/status.md`: PRES-002 row updated to 26 scenes and linked to this report.
- `docs/decisions/decision-log.md`: `[D-97]`.
- `patch/PRES-002-claude-code-configuration-mode-scenes.patch`: full unit of work.

### 2.2 Placement and renumbering

| Now | Was | Title |
| --- | --- | --- |
| 17 | 17 | The four, side by side |
| 18 | — | One dial at a time |
| 19 | — | From setup to one insertion |
| 20 | 18 | The answer key |
| 21 | 19 | Scoring a placement |
| 22 | 20 | How sure is an average? |
| 23 | 21 | What is still missing: the two gaps |
| 24 | 22 | Four questions |
| 25 | 23 | The premise behind question 4 |
| 26 | 24 | The whole study in one picture |

Both new scenes are reveal-only; they need no custom renderer. The engine derives scene count, step maxima, progress, counter and overview from DOM order.

### 2.3 Content and source basis

**Scene 18 — configurations**

- Primary settings shown: S1 brute force (every idea), S2 threshold θ = 0.6, S3 ANN with k = 10 and efSearch = 128, S4 buckets (5, 10).
- Sensitivity settings shown: θ = 0.4/0.5; k = 5/20; efSearch = 64/256; bucket bounds (2,5)/(10,20).
- 4 primary + 8 sensitivity = 12 configurations. This is the matrix described in the analysis plan and thesis Section 3.4.
- The visual is a fixed four-card row plus eight one-at-a-time variants; no measured outcome.

**Scene 19 — modes, runs, trials**

- Two modes: cost (synthetic map sizes) and accuracy (expert gold maps).
- 12 configurations × 2 modes = 24 runs.
- Cost run: 60 trials = 10 at each of six sizes.
- Accuracy run: 59 trials = 29 DSA + 30 from the other gold map.
- A trial is one insertion inside a run.
- The 59/60 and 29/30 counts are the planned run composition, not results.

The exact `Metacademy` term is defined later, in the answer-key scene, so Scene 19 says "the other gold map" rather than printing the term before its chip.

### 2.4 Copy-order cleanup

- `Trial` was previously introduced in the bootstrap scene. It is now introduced in Scene 19, before bootstrap; the bootstrap scene uses plain "trials".
- "Primary" and "sensitivity" were removed from the efSearch copy (now "Main setting" / "Extra settings tested") so the new chips are the first definition.
- "Run" was removed from the S4 seed caption ("every repeat starts the same") and the comparison table's final line ("before any measurements").
- The Mode gloss no longer says "run" before the Run chip exists.
- Stale internal ids from earlier insertions were normalised: answer-key `s17*` → `s20*`, shared-judge `s15ex` → `s16ex`, so internal ids again match their scenes.

### 2.5 Flags for the APC / Luke

- **No results:** the 12/24/60/59 counts are design facts. The scenes do not reveal which configuration won, which sensitivity setting changed accuracy, or any measured number.
- **Time:** the two scenes add roughly 110–130 seconds at the APC's pace. With the bootstrap and efSearch scenes, the deck is now about 25 minutes; rehearse before the defense.
- **Renumbering:** every reference after Scene 17 shifts by two. Use the table in §2.2.
- **Trial ordering:** if anyone asks why bootstrap says "10 trials" after Scene 19 defines trial, that is intentional: the term is introduced once, then reused.

## 3. Verification & Test Evidence

### 3.1 Static guard

```bash
python3 -m pytest tests/test_background_deck_static.py -q
# 10 passed, 1 warning in 2.03s
```

The warning is the non-fatal term-before-chip lint:

```text
edge, graph, insertion, mean, neighbour, node, premise, prerequisite
```

`mean` is the accepted earlier case; the new terms (`Configuration`, `Primary`, `Sensitivity`, `Mode`, `Run`, `Trial`) are not flagged. The guard checks 26 scenes and 98 terms, the new terms, the `24 runs` / `60 trials` / `59 trials` wording, and the shifted made-up-scene indices.

The merged `master` was also checked at `e5137fd` before these scenes were added: 10/10 static tests passed.

### 3.2 Browser QA

Playwright, Chromium and Firefox, local file URL, no server:

| Check | Chromium | Firefox |
| --- | --- | --- |
| Scene count | 26 | 26 |
| Step maxima | `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,7,6,7,6,7,6,9,7,4,5,4,6]` | same |
| All states visited | 176 | 176 |
| Page or console errors | 0 | 0 |
| Overview scene cards | 26 | 26 |
| Overview term rows | 98 | 98 |
| Overflow at 1920×1080 | none | none |
| Overflow at 1366×768 | none | none |
| Overflow at 1280×720 | none | none |

Screenshots for every step of Scenes 18 and 19 at all three resolutions are in `/tmp/pres002-config-qa/` (temporary, not committed). Visual checks covered the four primary cards, the eight sensitivity chips, the 12-configuration count, the two mode cards, the 24-run formula, and the trial box.

### 3.3 Dynamic checks

- `window.__deck.sceneCount === 26`.
- `window.__deck.stepCounts[17] === 6`, `window.__deck.stepCounts[18] === 7`.
- Overview cards 18 and 19 open the new scenes at step 0.
- Terms tab shows the five new rows and jumps to their scenes; `Trial` jumps to Scene 19.
- Answer-key renderer still works after the internal `s17*` → `s20*` id normalisation (all 176 states visited without errors).
- Logo payloads remain byte-identical to the original deck.
- `git diff --check` reports no whitespace errors.

### 3.4 Git diff

`git diff --stat`:

```text
 docs/decisions/decision-log.md                     |   7 +
 docs/presentation/background-deck/background-concepts.html | 1185 +++++++++++++---------
 docs/tasks/status.md                               |   2 +-
 tests/test_background_deck_static.py               |   8 +-
 4 files changed, 685 insertions(+), 517 deletions(-)
```

The deck diff is large because the insertion renumbers Scenes 18–24 and every scoped CSS selector and renderer name that belongs to them. The complete deck diff is in the patch file. Selected verbatim hunks:

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index d71e438..ca84682 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -97,7 +97,7 @@ Status: **in-progress**
 | ID | Task | Status | Notes / Report |
 | --- | --- | --- | --- |
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
-| PRES-002 | Build the single-file, offline background-concepts HTML deck (24 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval and efSearch scene follow-ups. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md), [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md) and [`docs/reports/PRES-002-claude-code-efsearch-scene.md`](docs/reports/PRES-002-claude-code-efsearch-scene.md). |
+| PRES-002 | Build the single-file, offline background-concepts HTML deck (26 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval, efSearch, and configuration/mode/run/trial scene follow-ups. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md), [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md), [`docs/reports/PRES-002-claude-code-efsearch-scene.md`](docs/reports/PRES-002-claude-code-efsearch-scene.md) and [`docs/reports/PRES-002-claude-code-configuration-mode-scenes.md`](docs/reports/PRES-002-claude-code-configuration-mode-scenes.md). |
 
 ## Housekeeping
 
```

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index a1db39c..7da91e8 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -957,3 +957,10 @@ Reasoning: adds the requested uncertainty teaching without touching Chapter 4 or
 (3) Source: thesis Section 3.3.4 (HNSW M = 16, efConstruction = 200, efSearch = 128; sensitivity efSearch ∈ {64, 256}; k = 10) and Section 3.4 (planned call bounds independent of efSearch). No Chapter 4 result, measured recall, F1 value, model name, gate or ranking appears. The knob label is an illustration; the three settings and the fixed build-time value are method facts.
 (4) The static guard now expects 24 scenes and 93 terms, checks the `efSearch` / `efConstruction` chips and the `efSearch = 128` wording, and the V4 scene indices were shifted with the insertion. Browser QA passed in Chromium and Firefox: 161 states (24 scene starts plus 137 step maxima), no page or console errors, no overflow at 1920×1080, 1366×768 or 1280×720, 24 overview cards and 93 term rows. The only term-before-chip warning is the accepted `mean` case from [D-95]; `efSearch` was removed from that warning by keeping the visible heading term-free.
 Reasoning: adds the requested S3 search-depth teaching without presenting the measured sensitivity outcome, and keeps scene order, CSS, renderers and navigation consistent after insertion. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-efsearch-scene.md`.
+
+**[D-97]** Background-concepts deck: add the configuration / mode / run / trial scenes (PRES-002 follow-up):
+(1) The two earlier follow-ups (bootstrap interval, efSearch) were merged to `master` as `e5137fd`. Luke then requested slide(s) on configuration (primary and sensitivity), mode, run and trial. Two scenes are added after Scene 17 (The four, side by side) and before the accuracy material: **Scene 18 — One dial at a time** and **Scene 19 — From setup to one insertion**. The former Scenes 18–24 become 20–26. The deck is now **26 scenes and 98 terms**; per-scene step maxima are `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,7,6,7,6,7,6,9,7,4,5,4,6]`.
+(2) Scene 18 teaches: a configuration is one strategy plus its settings; the primary configuration is the main setting chosen before measurements; a sensitivity configuration moves one setting and holds the rest; the study has 4 primary + 8 sensitivity = 12 configurations. The eight sensitivity settings shown are theta 0.4/0.5, k 5/20, efSearch 64/256, and bucket bounds (2,5)/(10,20). Scene 19 teaches: mode is what we measure (cost or accuracy); a run is one complete execution of one configuration in one mode; a trial is one insertion inside a run; 12 configurations x 2 modes = 24 runs; a cost run has 60 trials (10 at each of six sizes); an accuracy run has 59 trials (29 DSA + 30 from the other gold map). No Chapter 4 result, measured value, model name, gate or ranking appears.
+(3) The Trial chip moved from the bootstrap scene to Scene 19, where the term is now introduced; the bootstrap scene uses plain "trials". To keep term-first-use ordering honest, "primary" and "sensitivity" were removed from the efSearch copy, "run" was removed from the seed and table copy, and the Mode gloss no longer says "run". The stale internal answer-key ids `s17*` were normalised to `s20*`, and the shared-judge `s15ex` id to `s16ex`, so internal ids again match their scenes.
+(4) The static guard now expects 26 scenes and 98 terms, checks the new terms and the `24 runs` / `60 trials` / `59 trials` wording, and the V4 made-up-scene indices moved to 7, 9, 10, 11, 17, 21 and 22. Browser QA passed in Chromium and Firefox: 176 states (26 scene starts plus 150 step maxima), no page or console errors, no overflow at 1920x1080, 1366x768 or 1280x720, 26 overview cards and 98 term rows. The only term-before-chip warning remains the accepted `mean` case from [D-95].
+Reasoning: adds the requested experimental-setup vocabulary at the point where the deck has finished comparing the four strategies and is about to explain scoring, without presenting any measured result. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-configuration-mode-scenes.md`.
```

The complete patch is `patch/PRES-002-claude-code-configuration-mode-scenes.patch`.

## 4. Items Flagged for Attention

- **Merge already done:** prior work is on `master` at `e5137fd`. These two scenes are on `task/PRES-002` and are **not** merged; the branch tip after commit is reported in the handoff.
- **No measured result:** the scenes explain the design matrix, not its outcome. If a panelist asks which sensitivity setting changed the result, answer from Chapter 4, not from these slides.
- **Time:** the deck is now about 25 minutes at the APC's original pace; rehearse the added four scenes (bootstrap, efSearch, configuration, modes/runs/trials) together.
- **Renumbering:** all references after Scene 17 shift by two.
