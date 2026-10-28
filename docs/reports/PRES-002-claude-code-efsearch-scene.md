# Task Report: PRES-002 — efSearch scene

**Date:** 2026-10-28
**Agent:** claude-code
**Task ID:** PRES-002 (follow-up to the original deck build)
**Status:** needs-review
**Commit:** one commit on `task/PRES-002` — `feat(PRES-002): add efSearch scene`
**Patch File:** `patch/PRES-002-claude-code-efsearch-scene.patch`

---

## 1. Executive Summary

Added one scene to `docs/presentation/background-deck/background-concepts.html`: **Scene 14, "How hard the search looks"**, teaching `efSearch` as the search-time candidate-list size inside Strategy 3's HNSW/FAISS search. It sits immediately after Scene 13 (Strategy 3: nearest ideas), where the ANN graph is introduced, and before Scene 15 (Strategy 4). The former Scenes 14–23 are now Scenes 15–24. The deck is **24 scenes and 93 gloss-bank terms**.

The scene covers: S3 keeps a candidate list while walking the ANN graph; `efSearch` caps that list and is often shortened to `ef`; the primary setting is 128, with sensitivity runs at 64 and 256 one at a time; lower efSearch means fewer distance checks and faster search, with more risk of missing a true neighbour; higher efSearch means more checks, slower search, and a result closer to exact search; the AI still sees at most `k = 10` ideas, so efSearch changes search effort, not AI-call count; and `efConstruction` is the build-time twin, fixed at 200 and not varied.

No Chapter 4 result, measured recall, F1 value, model name, gate, ranking or model identity appears. The knob graphic is labelled as an illustration; the three settings and the fixed build-time value are method facts from the thesis.

Verification: static guard 10/10; Chromium and Firefox visited 161 states (24 scene starts plus 137 per-scene step maxima) with no page or console errors and no overflow at 1920×1080, 1366×768 or 1280×720; overview builds 24 scene cards and 93 term rows.

## 2. Implementation Details

### 2.1 Changes Made

- `docs/presentation/background-deck/background-concepts.html`: new `#s14` section and scoped CSS, an idempotent `RENDER.s14` that moves the dial from 64 to 128 to 256 from the step alone, two new term chips (`efSearch`, `efConstruction`), and positional renumbering of the former Scenes 14–23 to 15–24 (HTML ids, CSS class prefixes, renderer names, comments, timer variable). Size is now 282,503 bytes; SHA-256 `1de45f07382c7134130b70a1e3a03d6454803e16ab94124df519e510cfe1d8a5`.
- `tests/test_background_deck_static.py`: scene default 24; new terms in the gloss-bank list; required phrases `efsearch = 128` and `efconstruction`; V4 scene indices shifted for the insertion.
- `docs/tasks/status.md`: PRES-002 row updated to 24 scenes and linked to this report.
- `docs/decisions/decision-log.md`: `[D-96]`, including a correction to the step-count arithmetic in `[D-95]`.
- `patch/PRES-002-claude-code-efsearch-scene.patch`: full unit of work.

### 2.2 Placement and renumbering

`efSearch` only makes sense after Scene 13 has introduced S3, ANN, HNSW, greedy search and `k = 10`. It therefore goes directly after Scene 13, before the S4 folder mechanism:

| Now | Was | Title |
| --- | --- | --- |
| 14 | — | How hard the search looks |
| 15 | 14 | Strategy 4: size-capped folders |
| 16 | 15 | One shared judge |
| 17 | 16 | The four, side by side |
| 18 | 17 | The answer key |
| 19 | 18 | Scoring a placement |
| 20 | 19 | How sure is an average? |
| 21 | 20 | What is still missing: the two gaps |
| 22 | 21 | Four questions |
| 23 | 22 | The premise behind question 4 |
| 24 | 23 | The whole study in one picture |

The engine derives scene count, step maxima, progress, counter and overview from DOM order; no separate scene array was edited. The dial is the only dynamic element: `RENDER.s14` sets `--p` and the visible value from the step, so direct jumps and back-steps agree.

### 2.3 Content and source basis

- **HNSW settings:** M = 16 links per node, `efConstruction = 200`, `efSearch = 128` primary (thesis Section 3.3.4).
- **Sensitivity:** `efSearch ∈ {64, 256}`, varied one at a time around 128 (Section 3.3.4 and Section 3.4).
- **Call cap:** `k = 10`; planned call bounds are independent of `efSearch` (Section 3.4). The scene's "at most k = 10 calls" line reflects that.
- **Trade-off:** the scene teaches the standard HNSW search-depth trade-off (more candidates checked, slower, closer to exact; fewer candidates, faster, more risk of a miss). It does **not** report the study's measured sensitivity outcome, which belongs to the main defense deck and Chapter 4.
- **Naming:** `efSearch` is the FAISS/ HNSW search-time parameter; the scene states that some write it as `ef`. `efConstruction` is the build-time analogue, fixed at 200 and not varied.
- **Illustration:** the queue dots and the dial are visual metaphor; the values 64, 128, 256 and 200 are real method settings. The section carries "illustration — not thesis data".

### 2.4 Conformance to the deck's rules

- Scope unchanged: no Chapter 4 result, measured value, model identity, reference marker, gate, rank or TOPSIS.
- New terms are `data-term` chips with glosses under 16 words: `efSearch`, `efConstruction`.
- The scene state is a pure function of `(scene, step)`; no renderer reads history.
- The scene uses `cqw` units, the MMSU palette, the content-scene lockup, and no network asset.
- Visible heading is "How hard the search looks", not "The efSearch dial", so the term is not printed before its chip. The overview title remains "The efSearch dial" in `data-title`.

### 2.5 Flags for the APC / Luke

- **Mechanism only:** the scene deliberately omits the measured efSearch sensitivity result. If a panelist asks whether varying efSearch changed the outcome, answer from Chapter 4 / the main deck, not from this slide. The slide's claim is about what efSearch *does*, not what the study *found*.
- **Illustration:** the queue and the dial are not data. The 64/128/256/200 values are settings, not measured results.
- **Renumbering:** notes that say "Scene 14 = S4", "Scene 19 = two gaps", etc. must shift. The table above is the mapping.
- **Step-count correction:** `[D-96](0)` corrects the arithmetic in `[D-95](5)`. The earlier "151 reveal steps" phrase was wrong; the 153 states were 23 scene starts plus 130 step maxima. No behaviour changed.
- **Time:** this scene adds roughly 50–60 seconds at the APC's pace. With the bootstrap scene, the deck is about 23:30 if both get a full slot; rehearse before committing to that.

## 3. Verification & Test Evidence

### 3.1 Static guard

```bash
python3 -m pytest tests/test_background_deck_static.py -q
# 10 passed, 1 warning in 2.15s
```

The warning is the non-fatal term-before-chip lint:

```text
edge, graph, insertion, mean, neighbour, node, premise, prerequisite
```

The `mean` warning is the accepted case from the bootstrap follow-up (harmonic mean appears earlier); `efSearch` is not in the warning list. The guard now checks 24 scenes and 93 terms, the new term chips, the `efSearch = 128` / `efConstruction` wording, and the shifted made-up tag indices.

### 3.2 Browser QA

Playwright, Chromium and Firefox, local file URL, no server:

| Check | Chromium | Firefox |
| --- | --- | --- |
| Scene count | 24 | 24 |
| Step maxima | `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,7,6,7,6,9,7,4,5,4,6]` | same |
| All states visited | 161 | 161 |
| Page or console errors | 0 | 0 |
| Overview scene cards | 24 | 24 |
| Overview term rows | 93 | 93 |
| Overflow at 1920×1080 | none | none |
| Overflow at 1366×768 | none | none |
| Overflow at 1280×720 | none | none |

Screenshots for every step of Scene 14 at all three resolutions are in `/tmp/pres002-efsearch-qa/` (temporary, not committed). Visual checks covered the dial at 64, 128 and 256, the fixed ten AI seats, and the efConstruction line.

### 3.3 Dynamic checks

- `window.__deck.sceneCount === 24`.
- `window.__deck.stepCounts[13] === 7`.
- `#s14-val` is `64` at step 4, `256` at step 5, and `128` otherwise.
- Overview card 14 opens Scene 14 at step 0.
- Terms tab shows both new rows and jumps to Scene 14.
- Logo payloads remain byte-identical to the original deck (two PNG SHA-256 prefixes `e7f45fcb6555cd93` and `32e7c2d8df6ecdbd`).
- `git diff --check` reports no whitespace errors.

### 3.4 Git diff

`git diff --stat`:

```text
 docs/decisions/decision-log.md                     |   8 +
 docs/presentation/background-deck/background-concepts.html | 1599 +++++++++++---------
 docs/tasks/status.md                               |   2 +-
 tests/test_background_deck_static.py               |  12 +-
 4 files changed, 874 insertions(+), 747 deletions(-)
```

The deck diff is large because the insertion renumbers Scenes 14–23 and every scoped CSS selector and renderer name that belongs to them. The complete deck diff is in the patch file. Selected verbatim hunks for the supporting files:

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 18acde8..d71e438 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -97,7 +97,7 @@ Status: **in-progress**
 | ID | Task | Status | Notes / Report |
 | --- | --- | --- | --- |
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
-| PRES-002 | Build the single-file, offline background-concepts HTML deck (23 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval scene follow-up. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md) and [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md). |
+| PRES-002 | Build the single-file, offline background-concepts HTML deck (24 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval and efSearch scene follow-ups. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md), [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md) and [`docs/reports/PRES-002-claude-code-efsearch-scene.md`](docs/reports/PRES-002-claude-code-efsearch-scene.md). |
 
 ## Housekeeping
 
```

```diff
diff --git i/tests/test_background_deck_static.py w/tests/test_background_deck_static.py
index 727776c..0f9edbd 100644
--- i/tests/test_background_deck_static.py
+++ w/tests/test_background_deck_static.py
@@ -6,10 +6,10 @@ from pathlib import Path
 import pytest
 
 HTML_PATH = Path(os.environ.get("DECK_HTML") or Path(__file__).resolve().parents[1] / "docs/presentation/background-deck/background-concepts.html")
-EXPECTED_SCENES = int(os.environ.get("DECK_SCENES", "23"))
+EXPECTED_SCENES = int(os.environ.get("DECK_SCENES", "24"))
 STARTER = os.environ.get("DECK_STARTER") == "1"
 PAYLOAD = re.compile(r"data:image/png;base64,[A-Za-z0-9+/=]+")
-TERMS = ["Empirical", "Complexity", "Analysis", "Narrowing", "Strategy", "Incremental", "LLM (Large Language Model)", "Graph construction", "Node", "Edge", "Graph", "Directed edge", "Prerequisite", "Knowledge graph", "Concept", "Domain expert", "Scale", "Prompt", "API call", "API", "Wall-clock time", "Database", "Batch construction", "Incremental insertion", "Insertion", "n", "Brute force", "Linear growth", "Control", "Shortlist", "Candidate", "Candidate narrowing", "Embedding", "Vector", "Local model", "Cosine similarity", "Threshold", "θ (theta)", "Top-k", "Cap", "Nearest neighbour", "ANN (approximate nearest-neighbour search)", "HNSW (Hierarchical Navigable Small World)", "Greedy", "FAISS", "Bucket", "Random hyperplane", "Bit", "Binary code", "Gray order", "Bounded", "EraRAG", "Seed", "Decision step", "Label", "Temperature 0", "Fair test", "Worst case", "Gold-standard graph", "Ground truth", "DSA (Data Structures and Algorithms)", "Metacademy", "Leave-one-out", "Synthetic data", "Precision", "Recall", "F1", "Harmonic mean", "Micro", "Macro", "Shortlist recall", "Neighbour", "Random baseline", "Trial", "Mean", "Bootstrap", "With replacement", "Resample", "Percentile", "95% bootstrap interval", "Research gap", "Aggregate", "Head-to-head", "Like-for-like", "Literature search", "Research question (RQ)", "Amortized cost", "Theorem", "Premise", "Conceptual framework", "Input / Process / Output"]
+TERMS = ["Empirical", "Complexity", "Analysis", "Narrowing", "Strategy", "Incremental", "LLM (Large Language Model)", "Graph construction", "Node", "Edge", "Graph", "Directed edge", "Prerequisite", "Knowledge graph", "Concept", "Domain expert", "Scale", "Prompt", "API call", "API", "Wall-clock time", "Database", "Batch construction", "Incremental insertion", "Insertion", "n", "Brute force", "Linear growth", "Control", "Shortlist", "Candidate", "Candidate narrowing", "Embedding", "Vector", "Local model", "Cosine similarity", "Threshold", "θ (theta)", "Top-k", "Cap", "Nearest neighbour", "ANN (approximate nearest-neighbour search)", "HNSW (Hierarchical Navigable Small World)", "efSearch", "efConstruction", "Greedy", "FAISS", "Bucket", "Random hyperplane", "Bit", "Binary code", "Gray order", "Bounded", "EraRAG", "Seed", "Decision step", "Label", "Temperature 0", "Fair test", "Worst case", "Gold-standard graph", "Ground truth", "DSA (Data Structures and Algorithms)", "Metacademy", "Leave-one-out", "Synthetic data", "Precision", "Recall", "F1", "Harmonic mean", "Micro", "Macro", "Shortlist recall", "Neighbour", "Random baseline", "Trial", "Mean", "Bootstrap", "With replacement", "Resample", "Percentile", "95% bootstrap interval", "Research gap", "Aggregate", "Head-to-head", "Like-for-like", "Literature search", "Research question (RQ)", "Amortized cost", "Theorem", "Premise", "Conceptual framework", "Input / Process / Output"]
 
 raw = HTML_PATH.read_text(encoding="utf-8")
 scan = PAYLOAD.sub("data:image/png;base64,PAYLOAD", raw)            # V3: never scan the logo bytes
@@ -64,17 +64,17 @@ def test_required_phrases():
     low = re.sub(r"\s+", " ", text.lower().replace("&mdash;", "\u2014").replace("&rsquo;", "\u2019"))
     for p in ("none of the studies we reviewed", "strictly above", "premise", "illustration", "made-up numbers",
               "s3 and s4 both cap at 10", "not thesis data", "95% bootstrap interval", "with replacement",
-              "2.5th", "97.5th", "fixed seed"):
+              "2.5th", "97.5th", "fixed seed", "efsearch = 128", "efconstruction"):
         assert p in low or p in scan.lower(), f"missing phrase: {p}"
 
 def test_tags_on_every_scene_that_needs_them():                         # V4
     secs = {int(m.group(1)): m.group(0) for m in re.finditer(r'<section class="scene[^"]*" id="s(\d\d)".*?</section>', scan, re.S)}
     miss = []
-    for n in list(range(4, 13)) + [15]:
+    for n in list(range(4, 15)) + [16]:
         s = secs.get(n, "")
         if ("data-ex=" in s and '"tag"' in s) or "not thesis data" in s: continue
-        if n in (4, 5, 6, 7, 8, 9, 10, 11, 12, 15) and "illustration" not in s: miss.append(("illustration", n))
-    for n in (7, 9, 10, 11, 16, 18, 19):
+        if n in (4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16) and "illustration" not in s: miss.append(("illustration", n))
+    for n in (7, 9, 10, 11, 17, 19, 20):
         if "made-up numbers" not in secs.get(n, ""): miss.append(("made-up numbers", n))
     assert not miss, miss
```

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 232d35d..a1db39c 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -949,3 +949,11 @@ Reasoning: keeps the deck inside the pre-registered scope and the APC's teaching
 (4) Seven gloss-bank terms were added: Trial, Mean, Bootstrap, With replacement, Resample, Percentile, 95% bootstrap interval. The deck now carries **91 terms**. The `mean` term-before-chip lint warning remains because "harmonic mean" appears earlier in Scene 18; it is accepted and recorded rather than renaming a standard statistic.
 (5) The static guard now expects 23 scenes and 91 terms, checks the interval phrases and fixed seed, and checks the made-up tag on Scene 19. Browser QA passed in Chromium and Firefox: 153 states (23 scene starts plus 151 revealed steps) with no page or console errors, no overflow at 1920×1080, 1366×768 or 1280×720, 23 overview cards and 91 term rows.
 Reasoning: adds the requested uncertainty teaching without touching Chapter 4 or presenting measured values, and keeps scene order, CSS, renderers and navigation consistent after insertion. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`.
+
+**[D-96]** Background-concepts deck: add the efSearch scene (PRES-002 follow-up):
+(0) **Correction to [D-95](5):** the 153 browser states are 23 scene starts plus 130 per-scene step maxima, not "23 scene starts plus 151 revealed steps". The "151" was a carry-over arithmetic error from counting the original deck's transitions; it did not affect the build, tests or any scene. The correct per-scene step maxima at that commit were `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,6,7,6,9,7,4,5,4,6]`.
+(1) Luke requested one scene on `ef` / `efSearch`. It is inserted as **Scene 14**, immediately after Scene 13 (Strategy 3: nearest ideas), because efSearch is the search-time knob inside S3. The former Scenes 14–23 become Scenes 15–24; scene ids, CSS class prefixes, renderer names, comments, overview cards and the visible counter are renumbered together. The deck is now **24 scenes and 93 terms**; per-scene step maxima are `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,7,6,7,6,9,7,4,5,4,6]`.
+(2) Content: S3 keeps a candidate list while walking the ANN graph; `efSearch` caps that list (often shortened to `ef`); primary setting 128, sensitivity runs 64 and 256 one at a time; lower efSearch means fewer distance checks, faster, more likely to miss a true neighbour; higher means more checks, slower, closer to an exact search. The AI still sees at most `k = 10` ideas: efSearch changes search effort, not AI calls. `efConstruction` is the build-time twin, fixed at 200 and not varied.
+(3) Source: thesis Section 3.3.4 (HNSW M = 16, efConstruction = 200, efSearch = 128; sensitivity efSearch ∈ {64, 256}; k = 10) and Section 3.4 (planned call bounds independent of efSearch). No Chapter 4 result, measured recall, F1 value, model name, gate or ranking appears. The knob label is an illustration; the three settings and the fixed build-time value are method facts.
+(4) The static guard now expects 24 scenes and 93 terms, checks the `efSearch` / `efConstruction` chips and the `efSearch = 128` wording, and the V4 scene indices were shifted with the insertion. Browser QA passed in Chromium and Firefox: 161 states (24 scene starts plus 137 step maxima), no page or console errors, no overflow at 1920×1080, 1366×768 or 1280×720, 24 overview cards and 93 term rows. The only term-before-chip warning is the accepted `mean` case from [D-95]; `efSearch` was removed from that warning by keeping the visible heading term-free.
+Reasoning: adds the requested S3 search-depth teaching without presenting the measured sensitivity outcome, and keeps scene order, CSS, renderers and navigation consistent after insertion. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-efsearch-scene.md`.
```

The complete patch is `patch/PRES-002-claude-code-efsearch-scene.patch`.

## 4. Items Flagged for Attention

- **No measured result:** the scene teaches the mechanism and the chosen settings, not the sensitivity outcome. Do not let it imply that varying efSearch did or did not change accuracy.
- **Time:** the new scene adds roughly 50–60 seconds at the APC's pace; rehearse the full deck after both additions.
- **Renumbering:** all scene references after Scene 13 shift by one; use the table in §2.2.
- **Correction recorded:** `[D-96](0)` fixes the arithmetic in `[D-95](5)`. The earlier report's "151 reveal steps" phrase should be read as superseded; the correct state count at that commit was 153 = 23 starts + 130 step maxima.
