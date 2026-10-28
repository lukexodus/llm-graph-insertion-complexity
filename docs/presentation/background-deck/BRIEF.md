# Background-Concepts Deck — APC Brief

**Status:** brief frozen for APC planning on 2026-10-28. Luke approved the
scope and packaging choices recorded here.

**What to build:** one self-contained `background-concepts.html` presentation
that teaches the thesis's foundational concepts to defense panelists as if
they were high-school students. The deck must use progressive,
first-principles explanations and visual animation. It is a **separate
deliverable** from the main `.pptx` defense deck: it is a background briefing,
not a results presentation.

**Division of work:** this file and `CONTENT-PACK.md` give the APC the
requirements, source material, facts, and style constraints. **The APC owns
the creative plan: scene composition, copy, visual metaphors, and all
animation/interaction design.** Do not treat any suggested sequence here as a
locked storyboard.

**Who reads this:** the APC AI writing the implementation prompt, then a local
coding agent with filesystem access that creates the HTML. The APC has no
filesystem access. Everything needed is in this file, `CONTENT-PACK.md`,
`DECK-EXTRACT.md`, and the source files named in Section 8.

---

## 1. User requirements (non-negotiable)

| Requirement | Decision |
| --- | --- |
| Runtime | 18–22 minutes |
| Scene count | About 20 scenes (roughly 18–22) |
| Content endpoint | Background concepts + research gaps + research questions + conceptual framework. **No Chapter 4 results, rankings, gates, or findings.** |
| Audience | Defense panelists treated as high-school students: every technical term defined in plain language before use |
| Teaching method | Progressive, first-principles, one new idea at a time; concrete analogy before formal term |
| Format | One **self-contained** `.html` file: inline CSS, inline JavaScript, inline SVG, logos embedded as data URIs |
| Dependencies | None. No CDN, no frameworks, no external fonts, no network access |
| Aspect ratio | 16:9 stage that letterboxes cleanly on any projector or laptop |
| Navigation | Click / Space advances one reveal step; at the end of a scene, next click moves to the next scene. Arrow keys move between scenes. `O` or `Esc` opens/closes an overview menu. `Home` goes to scene 1. |
| Presenter aids | Click-to-advance reveal steps + scene-jump overview menu. **No speaker-notes panel. No print/handout mode.** |
| Visual identity | MMSU green, white, and gold; the same simple, professional look as the existing `.pptx` |
| Offline safety | Opening the file by double-click must work with Wi-Fi off |
| Accessibility | Keyboard-only usable, visible focus, `prefers-reduced-motion` respected, body-text contrast at least WCAG AA |
| Animation | **APC's creative decision.** Use animation to teach the concept, not to decorate. Keep it purposeful and calm. |

**Out of scope:** quiz, score, audio, video, timer, chatbot, external images,
live API calls, speaker notes, print mode.

---

## 2. One-line message

> A knowledge graph stores ideas as nodes and relationships as edges. Adding a
> new idea naively means asking an LLM about every existing idea. Four
> candidate-narrowing strategies reduce that shortlist in different ways, and
> the thesis measures their cost and accuracy as the graph grows.

The deck should leave the panel able to explain, in their own words:

1. What a graph, a knowledge graph, a node, an edge, and edge direction are.
2. Why building a knowledge graph by hand does not scale.
3. What an LLM call is, and why the number of calls is the main cost.
4. Why incremental insertion differs from batch construction.
5. Why brute force costs `n` calls for `n` existing nodes.
6. What candidate narrowing is and why a cheap shortlist helps.
7. What an embedding is, and what cosine similarity measures.
8. How each of the four strategies builds its shortlist.
9. Why all four strategies share one identical LLM decision step.
10. What the two research gaps are, and how the four RQs follow from them.
11. What goes in, what happens, and what comes out in the conceptual framework.

They do **not** need the thesis's numeric results for this deck.

---

## 3. Teaching rules

Use the same voice and level as
`docs/presentation/script/Defense_Script_and_Background_Guide—Comprehensive Version.md`.
That file is the model for progressive explanation.

1. **Start from something familiar.** A road map, a friendship network, a
   filing cabinet, a résumé shortlist, a table of contents.
2. **One new idea per reveal step.** Do not put a definition and three
   consequences on screen at once.
3. **Define before use.** If the deck says "embedding", an earlier step must
   already have shown "a list of numbers that stands for meaning".
4. **Analogy first, term second.** "A shortlist is like screening résumés; in
   this thesis it is called candidate narrowing."
5. **Use one running example.** Suggested illustration: existing graph
   `Arrays`, `Loops`, `Recursion`, `Trees`, `Sorting`; new concept
   `Binary Search Tree`. This is a teaching illustration, not thesis data.
   Label it as such.
6. **Expand every acronym on first use.** LLM, ANN, HNSW, FAISS, KG, F1, RQ.
7. **Short on-screen text.** The audience should listen, not read paragraphs.
   Full explanations belong in the presenter's script, not the slide.
8. **Plain number sense.** "1,713 seconds — about 28 minutes" rather than
   "1,713 s"; "10 calls" rather than "O(1) calls". The formal term can appear
   as a small label after the intuition.

Tone: calm, concrete, non-patronizing. "As if the panel were high-school
students" means *no unexplained jargon*, not childish visuals. Keep the
professional MMSU look.

---

## 4. Scope boundary

### In scope

- Graphs, directed edges, knowledge graphs, prerequisite graphs.
- Why knowledge graphs matter; why manual construction does not scale.
- What an LLM is and what one API call means.
- Batch versus incremental construction; the symbol `n`; single insertion.
- Brute force and linear cost.
- Candidate narrowing; embeddings; cosine similarity; threshold; top-k;
  bucket.
- The four strategies and their shortlist rules.
- The shared decision step and why sharing it makes the comparison fair.
- Accuracy as precision, recall, and F1 against a gold-standard graph;
  leave-one-out evaluation.
- The two research gaps.
- The four research questions.
- The conceptual framework: input → process → output.

### Out of scope

- Any measured result from Chapter 4 (times, call counts, F1 values, gates,
  rankings, dominance, weights, TOPSIS).
- The post-hoc ranking framework and the three gates.
- Implementation details that do not help the panel understand the concept
  (exact prompt text, full HNSW parameter list, code architecture).
- Amortized-analysis formalism. Mention only that EraRAG's theorem is about
  average cost over many insertions and that the thesis tests a single
  insertion's premise, not the theorem.
- Any new claim not grounded in the thesis or the two defense scripts.

---

## 5. Visual identity — reference data

The existing `.pptx` is the visual reference Luke wants aligned with. The
tokens and motifs below are **observed facts about that deck**, not a layout
specification. The APC decides how to compose scenes and apply the style.

### 5.1 Colour tokens

Use CSS custom properties with these values:

```css
:root {
  --green-900: #0C4B05;   /* primary: MMSU green */
  --green-700: #146B12;   /* hover, secondary shapes */
  --green-500: #05812B;   /* accent green from the seal/logo */
  --green-100: #E8F1E6;   /* light wash, cards, highlight bands */
  --gold-500:  #C9A227;   /* thin rules, small emphasis, 50th logo */
  --gold-100:  #F3E7BF;   /* highlight background for one word */
  --paper:     #FEFEFE;   /* main background */
  --paper-2:   #F7F8F4;   /* alternate card background */
  --ink:       #1B1B1B;   /* body text */
  --muted:     #5B6B5B;   /* captions, secondary labels */
  --line:      #CFDCCB;   /* hairlines, graph edges */
  --alert:     #A33A2B;   /* use sparingly: "cost blows up" only */
}
```

Do not use the `.pptx` theme's blue/orange accents. They are PowerPoint
defaults, not part of the MMSU identity used on the title and content slides.

### 5.2 Typography

- Display / scene titles: `Georgia, "Times New Roman", serif`, bold, dark
  green. The `.pptx` uses a serif display face; Georgia is the safe local
  fallback.
- Body / labels / numbers: `Arial, Helvetica, sans-serif`.
- No web-font download. These are system fonts; the file must render offline.
- Title scale: `clamp(2rem, 4.2vw, 4.2rem)`. Body: `clamp(1rem, 1.55vw, 1.5rem)`.
  Small labels: `clamp(0.75rem, 1vw, 0.95rem)`.
- Maximum body line length about 65 characters.

### 5.3 Motifs observed in the existing deck (reference only)

- White paper background with a green vertical ribbon on the right edge and a
  soft inner curve; some title/closing slides also use a thinner left ribbon.
- Subtle interlocking-circle watermark in light grey-green.
- MMSU lockup on title/closing slides; smaller lockup on content slides; the
  50th-anniversary logo beside the lockup on title/closing slides.
- Green filled panels for emphasis; thin gold rules; serif scene titles.

The APC may reuse, simplify, or reinterpret these motifs. The fixed constraints
are only the colour/typography identity above, the offline single-file format,
and the navigation/accessibility requirements in Section 1.

**Animation and scene composition are entirely the APC's design.** No motion
prescription is intended here.

### 5.4 Iconography

- Simple inline SVG line icons, 2 px stroke, rounded caps: nodes, arrows,
  magnifier, layers, bucket, speech bubble, sieve/funnel.
- No emoji, stock photos, or clip-art.
- The only raster assets are the two MMSU logos in
  `docs/presentation/background-deck/assets/`.

---

## 6. Technical specification

### 6.1 File shape

Ship exactly one file:

```text
background-concepts.html
```

It must contain:

- `<!doctype html>`, `<html lang="en">`, `<meta charset="utf-8">`,
  `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- One `<style>` block with all CSS.
- One `<main id="deck">` containing the scenes.
- One `<script>` block with all JavaScript.
- The two logos inlined as `data:image/png;base64,...` URIs.

No `<link>`, no `<script src>`, no `@import`, no external URL.

### 6.2 Navigation

Implement a small scene/step state machine.

- Click or Space: reveal the next step; after the last step, move to the next
  scene.
- Left/Right arrows: previous/next scene.
- `Home`: first scene. `End`: last scene.
- `O` or `Esc`: open/close the overview menu.
- In the overview, clicking a scene card jumps to that scene.
- Clicking a card or control must not bubble to the stage's next handler.
- Touch (optional but recommended): tap right two-thirds to advance, left
  third to go back.
- Prevent page scroll while the deck is active.

### 6.3 Overview menu

- Full-stage overlay with a responsive grid of scene cards.
- Each card shows scene number, title, and a one-line "what this teaches".
- Generate cards from the scene headings at runtime so there is one source of
  truth.
- Focus-trapped; closable with `Esc`.

### 6.4 Progress

- Thin progress bar: width = current scene / total scenes.
- Small `NN / NN` counter.
- A "click to continue" cue only on the first scene; it disappears after the
  first advance.

### 6.5 Responsiveness

- Stage: `aspect-ratio: 16 / 9`, `width: min(100vw, calc(100vh * 16 / 9))`,
  centred.
- Internal sizes use `clamp()` or relative units, not fixed pixels tied to one
  projector.
- At `max-width: 900px` or `max-height: 520px`, reduce type and hide
  non-essential decorative detail.
- No horizontal overflow at 1920×1080, 1366×768, or 1280×720.

### 6.6 Performance and robustness

- Total file under 1.5 MB with logos inlined.
- Animate `transform` and `opacity`, not layout properties.
- All JavaScript in one `DOMContentLoaded` handler.
- Test by opening `file://.../background-concepts.html` with no network.
- If JavaScript is disabled, show scene 1 and a short "enable JavaScript"
  message; the primary requirement is that JavaScript works offline.

---

## 7. Content organization

`CONTENT-PACK.md` is the consolidated source material. It contains:

- The concept ladder (what must be taught before what).
- Canonical definitions and facts, each with a source reference.
- The four-strategy table and the caveats that must survive rewriting.
- The two research gaps, four RQs, and conceptual framework.
- An analogy bank.
- A "do not use" list.
- A topic inventory: every in-scope idea, not a scene sequence or storyboard.

The APC should use it to plan scenes, write on-screen copy, choose visual
metaphors, and design animations. It should not invent facts outside that
pack without checking the thesis or the defense scripts.

---

## 8. Files the APC and implementer should read

In priority order:

1. `docs/presentation/background-deck/CONTENT-PACK.md` — consolidated facts,
   definitions, caveats, concept ladder, and coverage map.
2. `docs/presentation/background-deck/DECK-EXTRACT.md` — text and theme
   extracted from the existing `.pptx`, plus asset notes.
3. `docs/presentation/script/Defense_Script_and_Background_Guide—Comprehensive Version.md`
   — full first-principles explanations and caveats.
4. `docs/presentation/script/Defense_Script_and_Background_Guide.md` — shorter
   script, useful for tighter phrasing.
5. `docs/thesis/[REVISED] An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction—With Chapter 4.md`
   — authoritative thesis text. Use Chapter 1 (problem, gaps, scope) and
   Chapter 3 (strategies, decision step). **Do not use Chapter 4 results**;
   they are out of scope.
6. `docs/presentation/background-deck/assets/mmsu-lockup.png` and
   `mmsu-50-logo.png` — the only raster assets. Inline as base64 in the final
   HTML.
7. The original `.pptx` — visual reference only; do not embed it.

Do not read `results/` or the analysis pipeline for this deck.

---

## 9. Acceptance checklist

- [ ] Opening the HTML with Wi-Fi disabled works.
- [ ] No external URL, `<link>`, or `<script src>`.
- [ ] About 20 scenes; every in-scope concept from Section 4 is covered.
- [ ] Every scene advances one reveal step per click/Space.
- [ ] Arrow keys move between scenes; `Home` and `End` work.
- [ ] `O` and `Esc` open the overview; clicking a card jumps to that scene.
- [ ] Progress bar and scene counter update correctly.
- [ ] At 1920×1080, 1366×768, and 1280×720 the stage is fully visible with no
      scrollbars or clipped text.
- [ ] `prefers-reduced-motion: reduce` shows all steps without animation.
- [ ] Keyboard-only usable from first scene to last.
- [ ] MMSU green/white/gold styling matches Section 5; no PowerPoint blue or
      orange.
- [ ] No Chapter 4 result, gate, ranking, or TOPSIS number appears.
- [ ] The running example is labeled as an illustration.
- [ ] S2/S3/S4 shortlist rules and the S3/S4 cap caveat are stated accurately.
- [ ] The deck ends with the gaps/questions/framework, not with results.
- [ ] File size under 1.5 MB.
- [ ] The local agent reports the branch/worktree path and tests at three
      resolutions.

---

## 10. What the APC should produce next

Write a standalone implementation prompt for one local agent that:

- Points to this brief and `CONTENT-PACK.md`.
- Restates the single-file, offline, no-dependency constraint.
- Leaves scene composition, copy, visual metaphors, and animation design to
  the agent/APC, within the teaching rules and content boundary.
- Requires testing at the three resolutions, keyboard-only navigation, and
  reduced-motion mode.
- Requires a committed HTML, logo assets, and a report with the branch/
  worktree path.

The APC does not need to re-derive the thesis content. It is consolidated in
`CONTENT-PACK.md`.
