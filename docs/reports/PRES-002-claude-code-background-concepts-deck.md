# Task Report: PRES-002 — Background-concepts HTML deck

**Date:** 2026-10-28
**Agent:** claude-code
**Task ID:** PRES-002
**Status:** needs-review
**Commit:** one commit on `task/PRES-002` — `feat(PRES-002): background-concepts HTML deck`
**Patch File:** `patch/PRES-002-claude-code-background-concepts-deck.patch`

---

## 1. Executive Summary

Built `docs/presentation/background-deck/background-concepts.html`: one offline, self-contained 16:9 deck of 22 scenes that teaches the thesis background from first principles and stops before Chapter 4. The APC's starter engine and scene shells were completed with 20 scene fragments, the 84-row gloss bank, per-scene CSS and idempotent renderers; the two logos are inlined as the only `data:` URIs.

Base commit is `3586cc7`, the `task/PRES-001` tip, because `master` does not contain `docs/presentation/background-deck/BRIEF.md`. Worktree: `/home/lukexodus/projects/llm-graph-insertion-complexity-PRES-002`.

The static guard passes (10/10), browser QA passes 57/57 at 1920×1080, 1366×768 and 1280×720, and the full suite shows no regression: the same 20 pre-existing environment failures as the `master` baseline, with the 10 new deck tests passing. One user-reported defect was fixed during review: the overview panels could not scroll because a global `wheel` handler swallowed the event.

## 2. Implementation Details

### 2.1 Changes Made

- `docs/presentation/background-deck/background-concepts.html` (new, 263,664 bytes): 22 scenes; inline CSS/JS/SVG; two base64 PNG logos; scene metadata, reveal engine, overview Scenes + Terms tabs, `window.__deck`.
- `tests/test_background_deck_static.py` (new): APC-supplied static guard, unchanged except it now runs against the finished deck (no `DECK_STARTER`).
- `docs/prompts/PRES-002-PROMPT.md` (new): the APC prompt exactly as supplied.
- `docs/tasks/status.md`: PRES-002 row, `needs-review`, linked to this report.
- `docs/decisions/decision-log.md`: `[D-94]`.
- `patch/PRES-002-claude-code-background-concepts-deck.patch`: whole unit of work.

### 2.2 Conformance to Specifications & Decisions

- BRIEF §1, §6, §9 and PRES-002 §3–§10 applied. `[D-93]` scope honoured: no Chapter 4 result, gate, ranking, TOPSIS, model name or reference marker.
- `[D-94]` records the 22-scene plan, R1, R2, C1–C8, D1–D5 and the static test as a standing guard.

**Departures D1–D5 — all accepted, none changed:**

| ID | Status | Evidence |
| --- | --- | --- |
| D1 container-query type | accepted | `container-type:size` on `#stage`; `cqw` tokens with a `vw` fallback |
| D2 step-back | accepted | Backspace / Shift+Space / ArrowUp / left-third tap; ArrowLeft lands fully revealed; ArrowRight lands at step 0 as specified |
| D3 Terms tab | accepted | 84 rows generated from `data-term` / `data-gloss`; jump to scene and step |
| D4 22 scenes | accepted | `__deck.sceneCount === 22`; fallback not used |
| D5 pure state | accepted | every `RENDER.sNN(step)` sets all visuals from `step`; jump/back tests match direct renders |

**Copy changed from the APC plan (all repo-backed; each is also in the fragment notes):**

- Scene 2 and the Scene 22 recap: the roadmap stops read “Four ways to narrow” and “Same rules for all” instead of “Four shortlists” and “A fair test”, so no term appears before its chip; the plain-words line says “four ways to narrow the list”.
- Scene 5: added the “illustration — not thesis data” tag; counter label reads “questions sent” so the word “call” does not precede the API-call chip.
- Scene 6: analogy bands shown sequentially (batch then incremental) to fit 720p; step-5 sentence shortened to “It decides…” because the auto-gloss already carries the clause.
- Scene 7: growth is three numbered bars (5/10/20) rather than a ticking shared counter, so the five-call counter still matches the five dashed links.
- Scene 8: heading “Interview the few” instead of “The shortlist” (the word appeared before its chip); “500 résumés” removed as an untagged invented number.
- Scene 9: the 384-number design fact is stated with no citation.
- Scene 10: the dial marks 0 at the right angle and travels 0.90→0.30 without a through-zero bounce; only the Trees/BST arrow pair is drawn.
- Scene 11: the θ chip sits in the copy line, not inside the “θ = 0.6” label; a note keeps “k = 2 is illustration only”.
- Scene 12: added the “illustration — not thesis data” tag (the prompt's §9.1 list omits it).
- Scene 13: ANN “can occasionally miss” (thesis line 405), not “rarely”; added a caption for the previously copy-free drop-layer step.
- Scene 14: added a caption for the code-row step and the illustration tag.
- Scene 15: Temperature 0 gloss is “turns off random variety, so answers are as repeatable as the service allows”; subject area “when one is set”.
- Scene 17: “Then repeat for many concepts” (not every idea); synthetic-data gloss “invented, not expert-checked data”; maps shown as a heading plus two fact cards.
- Scene 18: F1 shown as ≈ 0.67; the macro example adds the two per-idea precisions (0.90, 0.00) needed by the formula.
- Scene 19: restaurant shows a labelled “one total”, no invented number.
- Scene 20: the unsourced gap-grouping line is replaced by the thesis's four-unresolved-issues-in-order wording.
- Scene 21: two slider captions (“EraRAG's experiments move this one.” / “We move this one.”) sourced to CONTENT-PACK §8.
- Scene 22: heading shortened to “Whole study”; step 6 clears the panels and roadmap so the engine lockup and 50th logo return alone.

**Engine change:** `wheel` is now prevented only when the overview is closed; inside the overview the Scenes and Terms panels scroll normally. Verified in Chromium and Firefox (scrollTop 0 → 600 / 529 px).

## 3. Verification & Test Evidence

### 3.1 Test Execution

Static guard:

```bash
python3 -m pytest tests/test_background_deck_static.py -q
# 10 passed, 1 warning in 1.10s
```

The warning is the non-fatal term-before-chip lint, resolved in §3.4.

Browser QA (APC `qa_browser.py`, headless Chromium):

```bash
python3 tools/qa_browser.py docs/presentation/background-deck/background-concepts.html ../llm-graph-insertion-complexity-PRES-002-qa
# 57 passed, 0 failed
```

Covered: zero network requests and zero console errors at 1920×1080, 1366×768, 1280×720; every scene at every step with no stage scroll, no out-of-stage element and no clipped text; the full keyboard run (Space × 144, arrows, Home, End, Backspace, Shift+Space); 22 overview cards; focus trap and Esc; card click does not advance; Terms tab lists all 84 chips; reduced motion leaves no running animations; normal motion animates a forward step; JavaScript off shows Scene 1 and the notice.

Full suite, with the gitignored `results/` and `repositories/` symlinked to the main checkout:

```bash
python3 -m pytest -q
# 20 failed, 670 passed, 13 skipped, 1 warning in 245.84s
```

Baseline on the unmodified `master` checkout, same interpreter:

```bash
python3 -m pytest -q
# 20 failed, 660 passed, 13 skipped in 239.18s
```

The 20 failures are identical and pre-existing (missing FAISS, model assets and data fixtures); the worktree adds exactly the 10 passing deck tests. No regression.

Firefox smoke (Playwright Firefox 157): every one of the 144 scene/step states reached by forward clicks has the same visible set as a direct `goto`, after the 0.8 s stagger settles; zero mismatches. Wheel scrolling of the Terms panel works.

### 3.2 Edge Cases & Negative Testing

- Full forbidden-string scan (`§9.2`) passes in markup, attributes and script; the only `http://` is the SVG namespace exception.
- Exactly two `data:image/png;base64,` URIs; no other `data:` URI; file 263,664 bytes (< 1.5 MB).
- `node --check` on the inline script passes (node 26.10.0).
- Term coverage: all 84 gloss-bank terms present; longest gloss 15 words (limit 16).
- Step-back after a jump restores the correct prior state; renderers do not read history.
- Wheel over the deck still does not scroll the page; wheel inside the overview scrolls the panel.

### 3.3 Contrast

Every text/background pair used, lowest first:

| Pair | Ratio | Need | Use |
| --- | --- | --- | --- |
| gold-500 on green-900 | 4.29 | 3.0 (large) | large gold text only |
| muted on paper-2 | 5.32 | 4.5 | card numbers |
| muted on paper | 5.63 | 4.5 | tags, captions, counter |
| alert on paper | 6.51 | 4.5 | cost blow-up label |
| green-700 on paper | 6.63 | 4.5 | emphasised edges (graphic) |
| green-900 on gold-100 | 8.40 | 4.5 | new-concept label |
| green-900 on green-100 | 8.97 | 4.5 | nodes, tabs |
| green-900 / ink on paper | 10.29 / 17.08 | 4.5 | titles, body |

Gold on white (2.40) and `--line` on white (1.41) are decorative only — rules, underlines, hairlines — never text or graph edges.

### 3.4 Term-before-chip lint (resolve or justify)

| Flagged | Cause | Resolution |
| --- | --- | --- |
| node, edge, graph, prerequisite | appear in Scene 3's `data-teaches` menu metadata, not visible copy | justified; no on-screen forward use |
| insertion | “incremental insertion” chip appears before the standalone “Insertion” chip in the same scene | justified; the compound is itself a chip and the standalone term is defined before any other use |
| neighbour | “nearest neighbour” chip (Scene 13) precedes the general “Neighbour” chip (Scene 18) | justified; distinct compound term |
| premise | scene title “The premise behind question 4” precedes its definition at step 2 | justified; the heading announces the topic and the chip defines it in the same scene |

No visible-body forward reference survives.

### 3.5 Screenshots

Directory (outside git): `../llm-graph-insertion-complexity-PRES-002-qa/` — 22 scenes × 3 resolutions, plus `contact-1920x1080.png`, `contact-1366x768.png`, `contact-1280x720.png`. All contact sheets viewed; individual defect checks on Scenes 1–3, 5, 7, 12–14, 18, 20–22 at 1280×720.

### 3.6 Not run

- Real projector and an actual rehearsal/timing run.
- Safari/iOS `cqw` rendering.
- Firefox full 3-resolution matrix (only the 144-state reveal comparison and wheel test ran).
- No live API, no network (by design).

### 3.7 Step counts

`[1, 10, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 7, 7, 6, 7, 6, 9, 4, 5, 4, 6]` — 144 reveal steps across 22 scenes.

## 4. Decisions Recorded

- **[D-94]**: 22 scenes with R1/R2, C1–C8 applied, D1–D5 accepted, fact-check copy corrections, engine/overview behaviour, and the static test as a standing guard.

## 5. Unified Git Diff

`git diff --stat` for the unit of work (the new HTML is 263 KB; its full added-file diff is in the patch, not pasted here):

```diff
 docs/decisions/decision-log.md                     |    9 +
 .../background-deck/background-concepts.html       | 2631 ++++++++++++++++++++
 docs/prompts/PRES-002-PROMPT.md                    |  658 +++++
 ...RES-002-claude-code-background-concepts-deck.md |  300 +++
 docs/tasks/status.md                               |    1 +
 tests/test_background_deck_static.py               |  107 +
 6 files changed, 3706 insertions(+)
```

Verbatim diff headers and the tracked-file hunks (index lines included):

```diff
diff --git i/docs/presentation/background-deck/background-concepts.html w/docs/presentation/background-deck/background-concepts.html
new file mode 100644
index 0000000..8a3949e
--- /dev/null
+++ w/docs/presentation/background-deck/background-concepts.html
@@ -0,0 +1,2631 @@
+<!doctype html>
+<html lang="en">
```

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 119a3c0..bf3c1b2 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -97,6 +97,7 @@ Status: **in-progress**
 | ID | Task | Status | Notes / Report |
 | --- | --- | --- | --- |
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
+| PRES-002 | Build the single-file, offline background-concepts HTML deck (22 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See report [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md). |
 
 ## Housekeeping
```

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 693d4f1..c453d95 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -932,3 +932,12 @@ Reasoning: records that the merged ANALYSIS-004 state reproduces and computes co
 (5) Content provenance: the pack consolidates the two defense scripts and thesis Chapters 1 and 3 (authoritative facts), plus the existing deck for style. It records the reusable traps: the 22–50 prompts figure is Funk et al.'s pruned algorithm, not brute force; S2 is uncapped and can be empty; S3 and S4 both cap at 10; RQ4 tests a single-insertion premise, not EraRAG's amortized theorem; avoid the deck's model-version and reference-range inconsistencies; say "none of the studies we reviewed", never "nobody has ever".
 (6) A `presentation` profile was added to `scripts/apc-bundle.sh` (and documented in `scripts/README.md`). It is intended to carry all material the APC may need, including the existing `.pptx`; if an upload limit rejects the 9.4 MB binary, exclude it with `--exclude '*.pptx'` and rely on `DECK-EXTRACT.md`.
 Reasoning: keeps the APC focused on creative/build work while preserving every fact, constraint, caveat, and style reference in repo files, and prevents the background deck from accidentally inheriting results, post-hoc claims, or known inconsistencies from the main deck. Affects: `docs/presentation/background-deck/`, `docs/presentation/assets` logos, `scripts/apc-bundle.sh`, `scripts/README.md`, `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/reports/PRES-001-claude-code-background-deck-materials.md`.
+
+**[D-94]** Background-concepts HTML deck build (PRES-002):
+(1) The deck was built as specified by the APC's PRES-002 prompt: 22 scenes (the top of BRIEF's 18–22 range), title-first teaching (R1), every term explained on first use via `data-term`/`data-gloss` chips (R2), and the glossary-derived Terms tab. It stops after the conceptual framework; no Chapter 4 result, ranking, gate, model name, or reference marker appears.
+(2) The APC's corrections C1–C8 were applied: no per-call duration; no 1,713-second example; Funk et al.'s 22–50 prompts and dollar range omitted; S1–S4 only; two gaps and four unresolved issues kept distinct; FAISS described but not expanded; micro/macro/shortlist recall defined; 22 scenes with the 20-scene fallback not used.
+(3) Departures D1–D5 were accepted: container-query type scaling with a `vw` fallback; step-back keys and left-third tap; Scenes/Terms overview tabs; 22 scenes; and scene state as a pure function of `(scene, step)`. Renderers set every visual from the step and never from history.
+(4) Fact-check corrections beyond the prompt: the leave-one-out line says "repeat for many concepts", not every idea; Temperature 0 says answers are "as repeatable as the service allows" because the thesis notes the decision-step model is not fully deterministic; ANN "can occasionally miss" rather than "rarely"; synthetic data gloss says invented, not expert-checked; the Scene 20 mapping uses the thesis's four-issues-in-order wording instead of the unsourced gap grouping.
+(5) Engine additions kept from the starter kit: a single lockup element that moves between title and content scenes, a 22-card scene overview, and a term index generated from the same chip attributes. A global `wheel` handler was narrowed so the overview's scene and term panels can scroll; the deck itself still suppresses page scroll.
+(6) `tests/test_background_deck_static.py` is adopted as a standing guard: forbidden-content scan, 22 scenes and metadata, size and logo-URI checks, required caveats, all 84 gloss-bank terms, gloss length, shell-marker removal, a term-before-chip lint (non-fatal), and `node --check` on the inline script.
+Reasoning: keeps the deck inside the pre-registered scope and the APC's teaching plan while recording every copy deviation caused by a repo-backed fact check. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/prompts/PRES-002-PROMPT.md`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-background-concepts-deck.md`.
```

The complete patch is `patch/PRES-002-claude-code-background-concepts-deck.patch`.

## 6. Content Coverage

### 6.1 CONTENT-PACK §14 questions

| # | Question | Scene |
| --- | --- | --- |
| 1 | node / edge / graph | 3 |
| 2 | knowledge graph vs graph | 4 |
| 3 | edge direction | 3 |
| 4 | why experts cannot build at scale | 4 |
| 5 | LLM / API call | 5 |
| 6 | batch vs incremental | 6 |
| 7 | n and n+1 | 6 |
| 8 | brute force n calls / linear | 7 |
| 9 | candidate / shortlist / narrowing | 8 |
| 10 | embedding | 9 |
| 11 | cosine similarity | 10 |
| 12 | threshold vs top-k | 11 |
| 13 | S1 rule | 12, 16 |
| 14 | S2 rule and cost | 12, 16 |
| 15 | S3 rule and approximation | 13, 16 |
| 16 | S4 rule and bound | 14, 16 |
| 17 | shared decision step | 15 |
| 18 | three labels | 15 |
| 19 | accuracy against gold graph | 17 |
| 20 | precision / recall / F1 | 18 |
| 21 | two research gaps | 19 |
| 22 | four research questions | 20 |
| 23 | framework input/process/output | 22 |
| 24 | RQ4 premise vs theorem | 21 |

### 6.2 Gloss bank

All 84 terms in PRES-002 §7 are chips; the Terms tab lists all 84 with the scene that first explains them. The five patches (Concept, Database, θ, DSA + Metacademy, Input/Process/Output) are applied.

### 6.3 Copy provenance (scene → source)

| Scene | Primary sources |
| --- | --- |
| 1 | thesis title page (lines 3–9); prompt §6 |
| 2 | prompt §6 + §7; BRIEF requirements R1 |
| 3 | prompt §6; CONTENT-PACK §3 (node/edge/graph/direction/prerequisite) |
| 4 | prompt §6; CONTENT-PACK §3, §5 |
| 5 | prompt §6; CONTENT-PACK §3 (LLM, prompt, API call, wall-clock) |
| 6 | prompt §6; CONTENT-PACK §3–§4 (batch, incremental, n) |
| 7 | prompt §6; thesis §1.1 “thousands” |
| 8 | prompt §6; CONTENT-PACK §3–§4 (candidate, shortlist) |
| 9 | prompt §6; thesis §3.3.4 (384-dim local embeddings, names only) |
| 10 | prompt §6; CONTENT-PACK §3 (cosine) |
| 11 | prompt §6; thesis §3.3.2 (strictly above, θ = 0.6), §3.3.4 (k = 10) |
| 12 | prompt §6; thesis §3.3.2–3.3.3; CONTENT-PACK §11 |
| 13 | prompt §6; thesis §3.3.4; CONTENT-PACK §3, §11 |
| 14 | prompt §6; thesis §3.3.5; CONTENT-PACK §4, §11 |
| 15 | prompt §6; thesis §3.4 (labels, temperature, shared decision step) |
| 16 | prompt §6; thesis §3.3.5 (S3/S4 cap caveat) |
| 17 | prompt §6; thesis §3.2.1–3.2.2, §3.4 (leave-one-out, synthetic costs) |
| 18 | prompt §6; thesis §3.4 (metric definitions) |
| 19 | prompt §6; thesis §1.1, §1.2; CONTENT-PACK §8 |
| 20 | prompt §6; thesis §1.2 (four issues in order) |
| 21 | prompt §6; thesis §1.2, §2.3/§3.3.5 premise discussion; CONTENT-PACK §8 |
| 22 | prompt §6; CONTENT-PACK §9 (framework) |

The fact-check pass covered 190 claim rows: 161 sourced, 26 ordinary/structural, 2 conflicts and 1 unsourced line; all four were corrected before build.

## 7. Flagged for APC / Operator Attention

- **Thesis inconsistency (C3) remains in the thesis:** §1.1 line 119 calls Funk et al. “their brute-force approach”, while §2.3.1 line 243 describes a pruned, KRIS-adapted algorithm. The deck avoids both the label and the 22–50 figures. Do not “fix” the thesis from this task.
- **RQ4 framing:** the deck says “we test the premise, not the theorem”; keep that wording if the thesis is edited.
- **Scene 20 mapping:** the deck now uses the thesis's four-unresolved-issues-in-order sentence, not the prompt's gap grouping. If the APC wants the grouping back, it needs a source or an explicit [Inference] label.
- **Scene 12 tag:** added because the scene shows the five named example chips; the prompt's §9.1 list omits Scene 12.
- **Navigation semantics:** ArrowRight lands on the next scene's step 0; ArrowLeft lands on the previous scene's last step. This is D2 as written and was confirmed as intended after Luke tested it.
- **Not reviewed by a second agent:** Playwright/Chromium and Firefox checks were run by the implementing agent; a different-model review of the deck copy is still advisable before the defense.
- **Manual checklist for Luke:** project from the actual venue laptop; test Firefox and Safari once; rehearse to confirm the 21-minute target and the 22-scene cut is comfortable; check that the projector's 16:9 scaling does not crop the gold progress bar.
