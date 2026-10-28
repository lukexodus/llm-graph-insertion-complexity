# Task Report: PRES-002 — Bootstrap interval scene

**Date:** 2026-10-28
**Agent:** claude-code
**Task ID:** PRES-002 (follow-up to the original deck build)
**Status:** needs-review
**Commit:** one commit on `task/PRES-002` — `feat(PRES-002): add bootstrap interval scene`
**Patch File:** `patch/PRES-002-claude-code-bootstrap-interval-scene.patch`

---

## 1. Executive Summary

Added one scene to `docs/presentation/background-deck/background-concepts.html`: **Scene 19, "How sure is an average?"**, teaching the 95% percentile bootstrap interval used by the analysis plan. It sits immediately after Scene 18 (Scoring a placement), where the deck has just introduced means and scores, and before the gaps/RQ material. The former Scenes 19–22 are now Scenes 20–23. The deck is **23 scenes, 151 reveal steps, 91 gloss-bank terms**.

The scene teaches the procedure in seven steps: 10 trials per map size; the mean is one estimate; bootstrap redraws 10 trials with replacement; 10,000 resamples with a fixed seed; the 2.5th and 97.5th percentiles cut the tails; the middle 95% is the 95% bootstrap interval; and the interval is a measure of wobble, not a promise, and can be wide with only 10 trials. All trial values and the resampled-mean histogram are made up and tagged. No Chapter 4 result, measured value, gate, ranking, or model name appears.

Verification: static guard 10/10; browser QA in Chromium and Firefox across 153 states (23 scene starts plus every reveal step) with no page or console errors; no overflow at 1920×1080, 1366×768 or 1280×720; overview builds 23 scene cards and 91 term rows.

## 2. Implementation Details

### 2.1 Changes Made

- `docs/presentation/background-deck/background-concepts.html`: new `#s19` section, scoped CSS, seven new term chips, and the positional renumbering of the old Scenes 19–22 to 20–23 (HTML ids, CSS class prefixes, renderer names, comments, timer variable). Size is now 275,414 bytes; SHA-256 `e262ce5e8e047fa3d36c0df6ce2e8d3656cab94a79b0908e61f53e6d6c0d0636`.
- `tests/test_background_deck_static.py`: scene default 23; new terms in the gloss-bank list; required phrases for the interval, replacement, percentiles and fixed seed; made-up tag check now includes Scene 19.
- `docs/tasks/status.md`: PRES-002 row updated to 23 scenes and linked to this report.
- `docs/decisions/decision-log.md`: `[D-95]`.
- `patch/PRES-002-claude-code-bootstrap-interval-scene.patch`: full unit of work.

### 2.2 Placement and renumbering

The visual ordering is deliberate: Scene 18 gives precision, recall, F1, micro/macro, and shortlist recall; Scene 19 then explains how much the mean of a small set of trials could move. Scenes 20–23 keep their original content and order:

| Now | Was | Title |
| --- | --- | --- |
| 19 | — | How sure is an average? |
| 20 | 19 | What is still missing: the two gaps |
| 21 | 20 | Four questions |
| 22 | 21 | The premise behind question 4 |
| 23 | 22 | The whole study in one picture |

The engine derives `N`, `meta`, `stepCounts`, progress, counter and overview cards from DOM order, so no separate scene array needed editing. The scene itself is reveal-only; it has no custom `RENDER.s19` and therefore no new state surface. The old renderers were renamed with the scenes they belong to (`RENDER.s20`–`RENDER.s23`).

### 2.3 Content and source basis

- **Trials and mean:** the cost runs use 10 trials per size (`docs/context/analysis-plan.md` §3.2).
- **Interval:** 95% percentile bootstrap over trials, 10,000 resamples, fixed seed (`analysis-plan.md` D1 and §4.1; `scripts/analysis/bootstrap.py`).
- **Percentiles:** the middle 95% lies between the 2.5th and 97.5th percentiles of the resampled means.
- **Reproducibility:** fixed seed means the same data produces the same interval; the deck says "fixed seed" without naming the seed value, avoiding an unnecessary implementation detail.
- **Interpretation:** the closing step says the interval shows how much the mean could wobble, is not a promise, and can be wide with 10 trials. It does not make a "95% chance the true mean is inside" claim.
- **Illustrations:** trial values 4–9, the example resample (mean 6.7), and the histogram are invented. The slide carries "made-up numbers, for illustration" in the first two acts and "made-up trial values and resampled means" in the last.

### 2.4 Conformance to the deck's rules

- Scope unchanged: no Chapter 4 result, measured value, model identity, reference marker, gate, rank or TOPSIS.
- Every new technical term is a `data-term` chip with a `data-gloss` under 16 words: Trial, Mean, Bootstrap, With replacement, Resample, Percentile, 95% bootstrap interval.
- Scene state remains a pure function of `(scene, step)`. The new scene uses only `data-step` / `data-until`; no renderer reads history.
- The scene uses `cqw` units, the MMSU palette, the existing content-scene lockup, and no network asset.

### 2.5 Flags for the APC / Luke

- **Term-before-chip lint:** the non-fatal warning now includes `mean`, because "harmonic mean" appears in Scene 18 before the new Mean chip. This is accepted: renaming a standard statistic just to silence a lint would make the deck worse. All other warnings are the pre-existing ones.
- **Time:** the APC's original scene targets total about 21:35. This scene adds roughly 60–70 seconds at the same pace, so the deck is about 22:40 if the new scene is given a 65-second slot. This is an estimate, not a measured rehearsal.
- **Use in a live defense:** if time is tight, the scene can be shortened by skipping the example resample (step 3–4) and reading the interval steps directly; the concept still lands. Do not cut Scene 19 if the panel is likely to ask how uncertainty was handled.

## 3. Verification & Test Evidence

### 3.1 Static guard

```bash
python3 -m pytest tests/test_background_deck_static.py -q
# 10 passed, 1 warning in 1.10s
```

The warning is the non-fatal term-before-chip lint:

```text
edge, graph, insertion, mean, neighbour, node, premise, prerequisite
```

`mean` is explained in §2.5; the rest are pre-existing and were justified in the original PRES-002 report.

The guard now checks:

- 23 scenes, each with `data-title` and `data-teaches`.
- Inline logos only; no external network references.
- Required phrases including `95% bootstrap interval`, `with replacement`, `2.5th`, `97.5th`, and `fixed seed`.
- All 91 gloss-bank terms are present as chips.
- Every gloss is 16 words or fewer.
- Scene 19 carries the made-up-numbers tag.
- The inline script passes `node --check`.

### 3.2 Browser QA

Playwright, Chromium and Firefox, local file URL, no server:

| Check | Chromium | Firefox |
| --- | --- | --- |
| Scene count | 23 | 23 |
| Step counts | `[1,10,6,5,5,5,5,5,5,5,5,5,7,7,6,7,6,9,7,4,5,4,6]` | same |
| All states visited | 153 | 153 |
| Page or console errors | 0 | 0 |
| Overview scene cards | 23 | 23 |
| Overview term rows | 91 | 91 |
| Overflow at 1920×1080 | none | none |
| Overflow at 1366×768 | none | none |
| Overflow at 1280×720 | none | none |

Screenshots for every step of Scene 19 at all three resolutions are in `/tmp/pres002-bootstrap-qa/` (temporary, not committed). The visual checks covered the legend, the ghost mean lines, the resample chips, the histogram band and tails, and the final caveat.

### 3.3 Dynamic checks

- `window.__deck.sceneCount === 23`.
- `window.__deck.stepCounts[18] === 7`.
- Overview card 19 opens Scene 19 at step 0.
- Terms tab shows all seven new rows and jumps to Scene 19.
- Logo payloads are byte-identical to the original deck (two PNG SHA-256 prefixes `e7f45fcb6555cd93` and `32e7c2d8df6ecdbd`).
- `git diff --check` reports no whitespace errors.

### 3.4 Git diff

`git diff --stat`:

```text
 docs/decisions/decision-log.md                     |   8 +
 docs/presentation/background-deck/background-concepts.html | 519 ++++++++++++++-------
 docs/tasks/status.md                               |   2 +-
 tests/test_background_deck_static.py               |   9 +-
 4 files changed, 355 insertions(+), 183 deletions(-)
```

Selected verbatim hunks (the full patch is the authoritative diff):

```diff
diff --git i/docs/presentation/background-deck/background-concepts.html w/docs/presentation/background-deck/background-concepts.html
index 8a3949e..b2d4a34 100644
--- i/docs/presentation/background-deck/background-concepts.html
+++ w/docs/presentation/background-deck/background-concepts.html
@@ -674,109 +674,158 @@ svg.ex{width:100%;height:auto;align-self:start}
 #s18 .s18-revrow b{color:var(--green-900);margin-right:.4cqw}
 #s18 .s18-revrow em{font-style:normal;color:var(--muted);text-decoration:line-through}
 
+/* ===== Scene 19 — How sure is an average? ===== */
+#s19 .gloss{font-size:.78em;line-height:1.3;color:var(--muted);font-family:Arial,Helvetica,sans-serif;font-weight:400}
+#s19 .s19-grid{display:grid;grid-template-columns:46% 1fr;gap:2.6cqw;flex:1;min-height:0}
+#s19 .s19-copy{display:flex;flex-direction:column;gap:1.05cqw;min-height:0;
+  font-size:clamp(.82rem,1.38cqw,1.7rem);line-height:1.3}
+#s19 .s19-block{border-left:.3cqw solid var(--gold-500);padding-left:1.1cqw}
+#s19 .s19-block p{margin:0 0 .42cqw}
+#s19 .s19-block p:last-child{margin-bottom:0}
+#s19 .s19-lead{color:var(--green-900);font-weight:700}
+#s19 .s19-vis{position:relative;min-width:0;min-height:0}
+#s19 .s19-act{position:absolute;inset:0;display:flex;flex-direction:column;gap:1.1cqw;min-height:0}
+#s19 .s19-h{margin:0;font:700 var(--t-label)/1.2 Arial,Helvetica,sans-serif;color:var(--green-900)}
+#s19 .s19-legend{display:flex;flex-wrap:wrap;gap:.6cqw 1.4cqw;align-items:center;
+  font:var(--t-label)/1.2 Arial,Helvetica,sans-serif;color:var(--muted)}
+#s19 .s19-legend span{display:inline-flex;align-items:center;gap:.45cqw}
+#s19 .s19-legend i{display:inline-block;width:2.4cqw;border-top:.22cqw solid var(--green-900)}
+#s19 .s19-legend i.dash{border-top-style:dashed;border-top-color:var(--muted)}
+#s19 .s19-cap{margin:0;font-size:.82em;line-height:1.3;color:var(--ink)}
+#s19 .s19-bars{position:relative;display:flex;align-items:flex-end;gap:1.1cqw;height:24cqw;
+  padding:0 .7cqw;border-bottom:.16cqw solid var(--line)}
+#s19 .s19-bar{position:relative;flex:1;height:calc(var(--h)*2.05cqw);background:var(--green-100);
+  border:.12cqw solid var(--green-700);border-radius:.35cqw .35cqw 0 0}
+#s19 .s19-bar b{position:absolute;left:0;right:0;top:-2.2cqw;text-align:center;
+  font:700 var(--t-label)/1 Arial,Helvetica,sans-serif;color:var(--green-700)}
+#s19 .s19-mean{position:absolute;left:0;right:0;z-index:2;border-top:.24cqw solid var(--green-900)}
+#s19 .s19-mean-a{bottom:calc(6*2.05cqw)}
+#s19 .s19-ghost{border-top-style:dashed;border-top-color:var(--muted);opacity:.75}
+#s19 .s19-g1{bottom:calc(5.4*2.05cqw)}
+#s19 .s19-g2{bottom:calc(6.6*2.05cqw)}
+#s19 .s19-draw{display:grid;grid-template-columns:1fr auto 1fr;gap:1.2cqw;align-items:center;
+  background:var(--paper-2);border:.12cqw solid var(--line);border-radius:1cqw;padding:1.3cqw}
+#s19 .s19-side{min-width:0}
+#s19 .s19-lab{margin:0 0 .65cqw;font:700 var(--t-label)/1.15 Arial,Helvetica,sans-serif;color:var(--green-900)}
+#s19 .s19-chips{display:flex;flex-wrap:wrap;gap:.42cqw}
+#s19 .s19-chip{display:inline-flex;align-items:center;justify-content:center;width:2.15cqw;height:2.15cqw;
+  border-radius:50%;background:var(--green-100);border:.12cqw solid var(--green-700);
+  font:700 var(--t-label)/1 Arial,Helvetica,sans-serif;color:var(--green-900)}
+#s19 .s19-chip.out{background:var(--paper);border-style:dashed;border-color:var(--muted);color:var(--muted)}
+#s19 .s19-chip.dup{background:var(--gold-100);border-color:var(--gold-500)}
+#s19 .s19-arrow{display:flex;flex-direction:column;align-items:center;gap:.3cqw;text-align:center;
+  font:700 var(--t-label)/1.2 Arial,Helvetica,sans-serif;color:var(--green-700)}
+#s19 .s19-arrow span{font-weight:400;color:var(--muted)}
+#s19 .s19-hist{width:100%;height:auto;max-height:32cqw;display:block}
+#s19 .s19-hist .s19-band{fill:var(--gold-100);opacity:.65}
+#s19 .s19-hist .s19-tail{fill:var(--green-100);stroke:var(--green-700);stroke-width:1}
+#s19 .s19-hist .s19-mid{fill:var(--green-700)}
+#s19 .s19-hist .s19-cut{stroke:var(--green-900);stroke-width:2;stroke-dasharray:6 5}
+#s19 .s19-hist text{font-family:Arial,Helvetica,sans-serif}
+
 /* ===== batch F ===== */
 /* ============================================================
-   PRES-002 scenes 19-22 — every rule is scoped by its scene id.
+   PRES-002 scenes 19-23 — every rule is scoped by its scene id.
    No global selectors, no infinite animations.
    ============================================================ */
 
-/* ===== Scene 19 — What is still missing: the two gaps ===== */
-#s19 .s19-grid{display:grid;grid-template-columns:1.08fr .92fr;gap:2.2cqw;flex:1;min-height:0}
-#s19 .s19-copy{display:flex;flex-direction:column;gap:1.05cqw;min-height:0;
+/* ===== Scene 20 — What is still missing: the two gaps ===== */
+#s20 .s20-grid{display:grid;grid-template-columns:1.08fr .92fr;gap:2.2cqw;flex:1;min-height:0}
+#s20 .s20-copy{display:flex;flex-direction:column;gap:1.05cqw;min-height:0;
   font-size:clamp(.85rem,1.5cqw,1.9rem);line-height:1.28}
-#s19 .s19-block{border-left:.3cqw solid var(--gold-500);padding-left:1.2cqw}
-#s19 .s19-block p{margin:0 0 .35cqw}
-#s19 .s19-block p:last-child{margin-bottom:0}
-#s19 .s19-lead{color:var(--green-900);font-weight:700}
-#s19 .s19-label{font:700 var(--t-label) Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;
+#s20 .s20-block{border-left:.3cqw solid var(--gold-500);padding-left:1.2cqw}
+#s20 .s20-block p{margin:0 0 .35cqw}
+#s20 .s20-block p:last-child{margin-bottom:0}
+#s20 .s20-lead{color:var(--green-900);font-weight:700}
+#s20 .s20-label{font:700 var(--t-label) Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;
   color:var(--green-700)}
-#s19 .s19-chip{margin:0 0 .3cqw}
-#s19 em{color:var(--green-900);font-style:italic}
-#s19 .s19-vis{display:grid;grid-template-rows:1fr 1fr;gap:1.2cqw;min-height:0}
-#s19 .s19-fig{margin:0;display:flex;align-items:center;justify-content:center;min-height:0}
-#s19 .s19-fig svg{width:100%;height:100%;display:block}
-#s19 .s19-more{opacity:0}
-#s19 #s19-menu.grown .s19-more{opacity:1}
-#stage.animate #s19 .s19-more{transition:opacity .4s ease-out}
+#s20 .s20-chip{margin:0 0 .3cqw}
+#s20 em{color:var(--green-900);font-style:italic}
+#s20 .s20-vis{display:grid;grid-template-rows:1fr 1fr;gap:1.2cqw;min-height:0}
+#s20 .s20-fig{margin:0;display:flex;align-items:center;justify-content:center;min-height:0}
+#s20 .s20-fig svg{width:100%;height:100%;display:block}
+#s20 .s20-more{opacity:0}
+#s20 #s20-menu.grown .s20-more{opacity:1}
+#stage.animate #s20 .s20-more{transition:opacity .4s ease-out}
 
-/* ===== Scene 20 — Four questions ===== */
-#s20 .s20-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1.2cqw;flex:1;min-height:0}
-#s20 .s20-card{display:flex;flex-direction:column;gap:.45cqw;min-height:0;
+/* ===== Scene 21 — Four questions ===== */
+#s21 .s21-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1.2cqw;flex:1;min-height:0}
+#s21 .s21-card{display:flex;flex-direction:column;gap:.45cqw;min-height:0;
   background:var(--paper-2);border:.15cqw solid var(--line);border-radius:1cqw;padding:1.1cqw 1.1cqw 1.2cqw}
-#s20 .s20-term{margin:0;font-size:clamp(.78rem,1.25cqw,1.55rem);line-height:1.2}
-#s20 .s20-tag{margin:0;font:700 clamp(.72rem,1.1cqw,1.35rem) Arial,sans-serif;letter-spacing:.06em;
+#s21 .s21-term{margin:0;font-size:clamp(.78rem,1.25cqw,1.55rem);line-height:1.2}
+#s21 .s21-tag{margin:0;font:700 clamp(.72rem,1.1cqw,1.35rem) Arial,sans-serif;letter-spacing:.06em;
   text-transform:uppercase;color:var(--green-700);padding-bottom:.5cqw;border-bottom:.2cqw solid var(--gold-500)}
-#s20 .s20-q{margin:0;font-size:clamp(.82rem,1.45cqw,1.8rem);line-height:1.25;color:var(--ink)}
-#s20 .s20-sub{margin:0;font-size:clamp(.68rem,1.05cqw,1.3rem);line-height:1.2;color:var(--muted)}
-#s20 .s20-mini{width:100%;height:auto;margin-top:auto;display:block}
-#s20 .s20-map{margin:0;padding-top:.8cqw;border-top:.3cqw solid var(--gold-500);
+#s21 .s21-q{margin:0;font-size:clamp(.82rem,1.45cqw,1.8rem);line-height:1.25;color:var(--ink)}
+#s21 .s21-sub{margin:0;font-size:clamp(.68rem,1.05cqw,1.3rem);line-height:1.2;color:var(--muted)}
+#s21 .s21-mini{width:100%;height:auto;margin-top:auto;display:block}
+#s21 .s21-map{margin:0;padding-top:.8cqw;border-top:.3cqw solid var(--gold-500);
   font-size:clamp(.82rem,1.4cqw,1.75rem);line-height:1.25;color:var(--ink);min-height:4.6cqw}
-#s20 .s20-map.lit{color:var(--green-900)}
+#s21 .s21-map.lit{color:var(--green-900)}
 
-/* ===== Scene 21 — The premise behind question 4 ===== */
-#s21 .s21-grid{display:grid;grid-template-columns:1fr 1fr;gap:2.4cqw;flex:1;min-height:0}
-#s21 .s21-copy{display:flex;flex-direction:column;gap:1.15cqw;min-height:0;
+/* ===== Scene 22 — The premise behind question 4 ===== */
+#s22 .s22-grid{display:grid;grid-template-columns:1fr 1fr;gap:2.4cqw;flex:1;min-height:0}
+#s22 .s22-copy{display:flex;flex-direction:column;gap:1.15cqw;min-height:0;
   font-size:clamp(.85rem,1.5cqw,1.9rem);line-height:1.28}
-#s21 .s21-block{border-left:.3cqw solid var(--gold-500);padding-left:1.2cqw}
-#s21 .s21-block p{margin:0 0 .4cqw}
-#s21 .s21-block p:last-child{margin-bottom:0}
-#s21 .s21-lead{color:var(--green-900);font-weight:700}
-#s21 .s21-rem{font:var(--t-label) Arial,sans-serif;color:var(--muted);font-style:italic}
-#s21 .s21-chip{margin:0 0 .3cqw}
-#s21 .s21-vis{display:flex;flex-direction:column;gap:1.1cqw;min-height:0}
-#s21 .s21-fig{margin:0;min-height:0}
-#s21 .s21-fig svg{width:100%;height:auto;display:block}
-#s21 .s21-sliders{display:flex;flex-direction:column;gap:1.1cqw;margin-top:auto}
-#s21 .s21-slabel{margin:0;font-size:clamp(.78rem,1.3cqw,1.6rem);color:var(--green-900);font-weight:700}
-#s21 .s21-slabel span{display:block;font:400 var(--t-label) Arial,sans-serif;color:var(--muted);font-weight:400}
-#s21 .s21-track{position:relative;width:26cqw;height:1.1cqw;margin:.75cqw 0 .4cqw;
+#s22 .s22-block{border-left:.3cqw solid var(--gold-500);padding-left:1.2cqw}
+#s22 .s22-block p{margin:0 0 .4cqw}
+#s22 .s22-block p:last-child{margin-bottom:0}
+#s22 .s22-lead{color:var(--green-900);font-weight:700}
+#s22 .s22-rem{font:var(--t-label) Arial,sans-serif;color:var(--muted);font-style:italic}
+#s22 .s22-chip{margin:0 0 .3cqw}
+#s22 .s22-vis{display:flex;flex-direction:column;gap:1.1cqw;min-height:0}
+#s22 .s22-fig{margin:0;min-height:0}
+#s22 .s22-fig svg{width:100%;height:auto;display:block}
+#s22 .s22-sliders{display:flex;flex-direction:column;gap:1.1cqw;margin-top:auto}
+#s22 .s22-slabel{margin:0;font-size:clamp(.78rem,1.3cqw,1.6rem);color:var(--green-900);font-weight:700}
+#s22 .s22-slabel span{display:block;font:400 var(--t-label) Arial,sans-serif;color:var(--muted);font-weight:400}
+#s22 .s22-track{position:relative;width:26cqw;height:1.1cqw;margin:.75cqw 0 .4cqw;
   background:var(--green-100);border:.18cqw solid var(--green-900);border-radius:1cqw}
-#s21 .s21-knob{position:absolute;left:0;top:50%;width:2.2cqw;height:2.2cqw;border-radius:50%;
+#s22 .s22-knob{position:absolute;left:0;top:50%;width:2.2cqw;height:2.2cqw;border-radius:50%;
   background:var(--green-900);border:.25cqw solid var(--paper);
   transform:translateY(-50%) translateX(calc(var(--p,0) * 23cqw))}
-#s21 .s21-snote{margin:0;font:var(--t-label) Arial,sans-serif;color:var(--muted)}
-#stage.animate #s21 .s21-knob{transition:transform .5s ease-out}
+#s22 .s22-snote{margin:0;font:var(--t-label) Arial,sans-serif;color:var(--muted)}
+#stage.animate #s22 .s22-knob{transition:transform .5s ease-out}
 
-/* ===== Scene 22 — The whole study in one picture ===== */
-#s22 .s22-cf,#s22 .s22-cio{margin:0;font-size:clamp(.8rem,1.4cqw,1.75rem);line-height:1.2}
-#s22 .s22-cio{margin-top:.35cqw}
-#s22 .s22-panels{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2cqw;flex:1;min-height:0;margin-top:.8cqw}
-#s22 .s22-panel{display:flex;flex-direction:column;min-height:0;padding:1.1cqw 1.2cqw;
+/* ===== Scene 23 — The whole study in one picture ===== */
+#s23 .s23-cf,#s23 .s23-cio{margin:0;font-size:clamp(.8rem,1.4cqw,1.75rem);line-height:1.2}
+#s23 .s23-cio{margin-top:.35cqw}
+#s23 .s23-panels{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2cqw;flex:1;min-height:0;margin-top:.8cqw}
+#s23 .s23-panel{display:flex;flex-direction:column;min-height:0;padding:1.1cqw 1.2cqw;
   background:var(--green-100);border:.22cqw solid var(--green-900);border-radius:1cqw}
-#s22 .s22-panel h3{margin:0 0 .7cqw;padding-bottom:.4cqw;border-bottom:.22cqw solid var(--gold-500);
+#s23 .s23-panel h3{margin:0 0 .7cqw;padding-bottom:.4cqw;border-bottom:.22cqw solid var(--gold-500);
   font:700 clamp(.8rem,1.3cqw,1.6rem) Arial,sans-serif;letter-spacing:.1em;color:var(--green-900)}
-#s22 .s22-body{display:flex;flex-direction:column;gap:.45cqw;font-size:clamp(.76rem,1.25cqw,1.55rem);line-height:1.28;color:var(--ink)}
-#s22 .s22-body p{margin:0}
-#s22 .s22-rem{font:var(--t-label) Arial,sans-serif;color:var(--green-700);font-style:italic}
-#s22 .s22-step{display:flex;align-items:center;flex-wrap:wrap;gap:.4cqw}
-#s22 .s22-step b{display:inline-flex;align-items:center;justify-content:center;width:1.5cqw;height:1.5cqw;
+#s23 .s23-body{display:flex;flex-direction:column;gap:.45cqw;font-size:clamp(.76rem,1.25cqw,1.55rem);line-height:1.28;color:var(--ink)}
+#s23 .s23-body p{margin:0}
+#s23 .s23-rem{font:var(--t-label) Arial,sans-serif;color:var(--green-700);font-style:italic}
+#s23 .s23-step{display:flex;align-items:center;flex-wrap:wrap;gap:.4cqw}
+#s23 .s23-step b{display:inline-flex;align-items:center;justify-content:center;width:1.5cqw;height:1.5cqw;
   border-radius:50%;background:var(--green-900);color:var(--paper);font-size:.85em}
-#s22 .s22-cycle{display:inline-flex;gap:.25cqw;margin-left:.35cqw}
-#s22 .s22-s{padding:.1cqw .38cqw;border:.12cqw solid var(--green-900);border-radius:.4cqw;
+#s23 .s23-cycle{display:inline-flex;gap:.25cqw;margin-left:.35cqw}
+#s23 .s23-s{padding:.1cqw .38cqw;border:.12cqw solid var(--green-900);border-radius:.4cqw;
   font-size:.82em;font-weight:700;color:var(--green-900);opacity:.35}
-#s22 .s22-s.on{opacity:1;background:var(--green-900);color:var(--paper)}
-#s22 .s22-only{margin-top:.35cqw;font:italic var(--t-label) Arial,sans-serif;color:var(--green-700)}
-#s22 .s22-road{display:grid;grid-template-columns:repeat(5,1fr);gap:.9cqw;margin-top:.9cqw;
+#s23 .s23-s.on{opacity:1;background:var(--green-900);color:var(--paper)}
+#s23 .s23-only{margin-top:.35cqw;font:italic var(--t-label) Arial,sans-serif;color:var(--green-700)}
+#s23 .s23-road{display:grid;grid-template-columns:repeat(5,1fr);gap:.9cqw;margin-top:.9cqw;
   padding-top:.8cqw;border-top:.3cqw solid var(--gold-500)}
-#s22 .s22-stop{display:grid;grid-template-columns:auto 1fr auto;grid-template-rows:auto auto;
+#s23 .s23-stop{display:grid;grid-template-columns:auto 1fr auto;grid-template-rows:auto auto;
   column-gap:.5cqw;align-items:center;padding:.5cqw .65cqw;
   background:var(--paper-2);border:.15cqw solid var(--line);border-radius:.7cqw}
-#s22 .s22-num{grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;
+#s23 .s23-num{grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;
   width:1.55cqw;height:1.55cqw;border-radius:50%;border:.15cqw solid var(--green-900);
   color:var(--green-900);font-size:.85em;font-weight:700}
-#s22 .s22-lab{font-size:clamp(.68rem,1.1cqw,1.35rem);font-weight:700;color:var(--green-900);line-height:1.15}
-#s22 .s22-take{grid-column:2;font-size:clamp(.62rem,1.02cqw,1.25rem);color:var(--muted);line-height:1.15}
-#s22 .s22-tick{grid-column:3;grid-row:1/3;font-size:clamp(.85rem,1.5cqw,1.9rem);color:var(--green-700);
+#s23 .s23-lab{font-size:clamp(.68rem,1.1cqw,1.35rem);font-weight:700;color:var(--green-900);line-height:1.15}
+#s23 .s23-take{grid-column:2;font-size:clamp(.62rem,1.02cqw,1.25rem);color:var(--muted);line-height:1.15}
+#s23 .s23-tick{grid-column:3;grid-row:1/3;font-size:clamp(.85rem,1.5cqw,1.9rem);color:var(--green-700);
   transform:scale(.8)}
-#s22 .s22-stop.in .s22-tick{transform:scale(1)}
-#stage.animate #s22 .s22-tick{transition:transform .4s ease-out;transition-delay:calc(var(--i,0) * 80ms)}
+#s23 .s23-stop.in .s23-tick{transform:scale(1)}
+#stage.animate #s23 .s23-tick{transition:transform .4s ease-out;transition-delay:calc(var(--i,0) * 80ms)}
```

The new scene body is below this CSS in the same patch; the full patch file contains every changed line, including the scene markup, the seven term chips, and the renderer renames.

```diff
diff --git i/tests/test_background_deck_static.py w/tests/test_background_deck_static.py
index 1167e3c..727776c 100644
--- i/tests/test_background_deck_static.py
+++ w/tests/test_background_deck_static.py
@@ -6,10 +6,10 @@ from pathlib import Path
 import pytest
 
 HTML_PATH = Path(os.environ.get("DECK_HTML") or Path(__file__).resolve().parents[1] / "docs/presentation/background-deck/background-concepts.html")
-EXPECTED_SCENES = int(os.environ.get("DECK_SCENES", "22"))
+EXPECTED_SCENES = int(os.environ.get("DECK_SCENES", "23"))
 STARTER = os.environ.get("DECK_STARTER") == "1"
 PAYLOAD = re.compile(r"data:image/png;base64,[A-Za-z0-9+/=]+")
-TERMS = ["Empirical", "Complexity", "Analysis", "Narrowing", "Strategy", "Incremental", "LLM (Large Language Model)", "Graph construction", "Node", "Edge", "Graph", "Directed edge", "Prerequisite", "Knowledge graph", "Concept", "Domain expert", "Scale", "Prompt", "API call", "API", "Wall-clock time", "Database", "Batch construction", "Incremental insertion", "Insertion", "n", "Brute force", "Linear growth", "Control", "Shortlist", "Candidate", "Candidate narrowing", "Embedding", "Vector", "Local model", "Cosine similarity", "Threshold", "θ (theta)", "Top-k", "Cap", "Nearest neighbour", "ANN (approximate nearest-neighbour search)", "HNSW (Hierarchical Navigable Small World)", "Greedy", "FAISS", "Bucket", "Random hyperplane", "Bit", "Binary code", "Gray order", "Bounded", "EraRAG", "Seed", "Decision step", "Label", "Temperature 0", "Fair test", "Worst case", "Gold-standard graph", "Ground truth", "DSA (Data Structures and Algorithms)", "Metacademy", "Leave-one-out", "Synthetic data", "Precision", "Recall", "F1", "Harmonic mean", "Micro", "Macro", "Shortlist recall", "Neighbour", "Random baseline", "Research gap", "Aggregate", "Head-to-head", "Like-for-like", "Literature search", "Research question (RQ)", "Amortized cost", "Theorem", "Premise", "Conceptual framework", "Input / Process / Output"]
+TERMS = ["Empirical", "Complexity", "Analysis", "Narrowing", "Strategy", "Incremental", "LLM (Large Language Model)", "Graph construction", "Node", "Edge", "Graph", "Directed edge", "Prerequisite", "Knowledge graph", "Concept", "Domain expert", "Scale", "Prompt", "API call", "API", "Wall-clock time", "Database", "Batch construction", "Incremental insertion", "Insertion", "n", "Brute force", "Linear growth", "Control", "Shortlist", "Candidate", "Candidate narrowing", "Embedding", "Vector", "Local model", "Cosine similarity", "Threshold", "θ (theta)", "Top-k", "Cap", "Nearest neighbour", "ANN (approximate nearest-neighbour search)", "HNSW (Hierarchical Navigable Small World)", "Greedy", "FAISS", "Bucket", "Random hyperplane", "Bit", "Binary code", "Gray order", "Bounded", "EraRAG", "Seed", "Decision step", "Label", "Temperature 0", "Fair test", "Worst case", "Gold-standard graph", "Ground truth", "DSA (Data Structures and Algorithms)", "Metacademy", "Leave-one-out", "Synthetic data", "Precision", "Recall", "F1", "Harmonic mean", "Micro", "Macro", "Shortlist recall", "Neighbour", "Random baseline", "Trial", "Mean", "Bootstrap", "With replacement", "Resample", "Percentile", "95% bootstrap interval", "Research gap", "Aggregate", "Head-to-head", "Like-for-like", "Literature search", "Research question (RQ)", "Amortized cost", "Theorem", "Premise", "Conceptual framework", "Input / Process / Output"]
 
 raw = HTML_PATH.read_text(encoding="utf-8")
 scan = PAYLOAD.sub("data:image/png;base64,PAYLOAD", raw)            # V3: never scan the logo bytes
@@ -63,7 +63,8 @@ def test_size_and_logos():
 def test_required_phrases():
     low = re.sub(r"\s+", " ", text.lower().replace("&mdash;", "\u2014").replace("&rsquo;", "\u2019"))
     for p in ("none of the studies we reviewed", "strictly above", "premise", "illustration", "made-up numbers",
-              "s3 and s4 both cap at 10", "not thesis data"):
+              "s3 and s4 both cap at 10", "not thesis data", "95% bootstrap interval", "with replacement",
+              "2.5th", "97.5th", "fixed seed"):
         assert p in low or p in scan.lower(), f"missing phrase: {p}"
 
 def test_tags_on_every_scene_that_needs_them():                         # V4
@@ -73,7 +74,7 @@ def test_tags_on_every_scene_that_needs_them():                         # V4
         s = secs.get(n, "")
         if ("data-ex=" in s and '"tag"' in s) or "not thesis data" in s: continue
         if n in (4, 5, 6, 7, 8, 9, 10, 11, 12, 15) and "illustration" not in s: miss.append(("illustration", n))
-    for n in (7, 9, 10, 11, 16, 18):
+    for n in (7, 9, 10, 11, 16, 18, 19):
         if "made-up numbers" not in secs.get(n, ""): miss.append(("made-up numbers", n))
     assert not miss, miss
```

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index bf3c1b2..18acde8 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -97,7 +97,7 @@ Status: **in-progress**
 | ID | Task | Status | Notes / Report |
 | --- | --- | --- | --- |
 | PRES-001 | Consolidate the source material, requirements, style reference, and asset pack for the APC to plan a separate background-concepts HTML presentation for defense panelists (first-principles teaching; no Chapter 4 results). | **needs-review** | Completed by Claude Code; branch `task/PRES-001`, worktree `../llm-graph-insertion-complexity-PRES-001`. Materials in `docs/presentation/background-deck/` (`BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, logos). See report [`docs/reports/PRES-001-claude-code-background-deck-materials.md`](docs/reports/PRES-001-claude-code-background-deck-materials.md). |
-| PRES-002 | Build the single-file, offline background-concepts HTML deck (22 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See report [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md). |
+| PRES-002 | Build the single-file, offline background-concepts HTML deck (23 scenes, no Chapter 4 results) from the APC prompt and starter kit, with the static guard test and the bootstrap-interval scene follow-up. | **needs-review** | Completed by Claude Code; branch `task/PRES-002`, worktree `../llm-graph-insertion-complexity-PRES-002`. See reports [`docs/reports/PRES-002-claude-code-background-concepts-deck.md`](docs/reports/PRES-002-claude-code-background-concepts-deck.md) and [`docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`](docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md). |
 
 ## Housekeeping
 
```

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index c453d95..232d35d 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -941,3 +941,11 @@ Reasoning: keeps the APC focused on creative/build work while preserving every f
 (5) Engine additions kept from the starter kit: a single lockup element that moves between title and content scenes, a 22-card scene overview, and a term index generated from the same chip attributes. A global `wheel` handler was narrowed so the overview's scene and term panels can scroll; the deck itself still suppresses page scroll.
 (6) `tests/test_background_deck_static.py` is adopted as a standing guard: forbidden-content scan, 22 scenes and metadata, size and logo-URI checks, required caveats, all 84 gloss-bank terms, gloss length, shell-marker removal, a term-before-chip lint (non-fatal), and `node --check` on the inline script.
 Reasoning: keeps the deck inside the pre-registered scope and the APC's teaching plan while recording every copy deviation caused by a repo-backed fact check. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/prompts/PRES-002-PROMPT.md`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-background-concepts-deck.md`.
+
+**[D-95]** Background-concepts deck: add the 95% bootstrap interval scene (PRES-002 follow-up):
+(1) Luke requested one additional scene teaching the 95% bootstrap interval. It is inserted as **Scene 19**, immediately after Scene 18 (Scoring a placement), because the interval qualifies the means and scores just taught. The former Scenes 19–22 become Scenes 20–23; scene ids, CSS class prefixes, renderer names, overview cards and the visible counter are renumbered together so DOM order, styles and state remain aligned. The deck is now **23 scenes and 151 reveal steps**.
+(2) Content is taught from first principles: each cost run has 10 trials; the mean is one estimate; bootstrap redraws 10 trials with replacement; 10,000 resamples with a fixed seed, one mean each; the 2.5th and 97.5th percentiles cut the tails; the middle 95% is the 95% bootstrap interval. The closing step says it shows how much the mean could wobble, is not a promise, and can be wide with only 10 trials. No Chapter 4 number or result appears.
+(3) Facts follow the frozen analysis plan D1 and `scripts/analysis/bootstrap.py`: 95% percentile bootstrap over trials, 10,000 resamples, fixed seed. The ten trial values, the example resample (mean 6.7) and the resampled-mean histogram are made up and carry "made-up numbers, for illustration" / "not thesis data" tags.
+(4) Seven gloss-bank terms were added: Trial, Mean, Bootstrap, With replacement, Resample, Percentile, 95% bootstrap interval. The deck now carries **91 terms**. The `mean` term-before-chip lint warning remains because "harmonic mean" appears earlier in Scene 18; it is accepted and recorded rather than renaming a standard statistic.
+(5) The static guard now expects 23 scenes and 91 terms, checks the interval phrases and fixed seed, and checks the made-up tag on Scene 19. Browser QA passed in Chromium and Firefox: 153 states (23 scene starts plus 151 revealed steps) with no page or console errors, no overflow at 1920×1080, 1366×768 or 1280×720, 23 overview cards and 91 term rows.
+Reasoning: adds the requested uncertainty teaching without touching Chapter 4 or presenting measured values, and keeps scene order, CSS, renderers and navigation consistent after insertion. Affects: `docs/presentation/background-deck/background-concepts.html`, `tests/test_background_deck_static.py`, `docs/tasks/status.md`, `docs/reports/PRES-002-claude-code-bootstrap-interval-scene.md`.
```

The complete patch is `patch/PRES-002-claude-code-bootstrap-interval-scene.patch`.

## 4. Items Flagged for Attention

- **No measured timing:** the 60–70 second estimate is not a rehearsal. Luke should time the scene once in the browser.
- **Made-up data:** as with the rest of the deck, the trial values and histogram are illustrative; they are not from `results/`.
- **Renumbering:** any external notes that refer to "Scene 19 = two gaps", "Scene 20 = four questions", "Scene 21 = premise", or "Scene 22 = whole study" must shift by one. This report and D-95 record the mapping.
- **Next request already queued:** Luke asked for a separate scene on `ef` / `efSearch` after this one. It is not part of this commit.
