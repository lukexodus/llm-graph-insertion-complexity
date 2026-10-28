# Existing Defense Deck — Extracted Reference

This file records what is in the existing `.pptx` so the APC can align the HTML
background deck without opening the binary. It is a reference, not a content
source for results. The background deck must **not** copy the results slides.

**File:**
`docs/presentation/An Empirical Complexity Analysis Of Candidate-Narrowing Strategies For Incremental LLM-Driven Graph Construction—Presentation.pptx`

**Metadata:** 52 slides, 16:9 (13.333 in × 7.5 in), 9.4 MB.

---

## 1. Visual identity observed in the deck

### Colours

The deck's title and content slides use:

- Primary dark green: `#0C4B05`
- White / near-white paper: `#FEFEFE`
- Accent green from the seal: `#05812B`
- Gold from the 50th-anniversary logo and thin rules: approximately `#C9A227`
- Body ink: near-black `#1B1B1B`
- Light green wash used on panels: approximately `#E8F1E6`

The PowerPoint theme file also carries default Office blue/orange accents
(`#4472C4`, `#ED7D31`, etc.). Those are **not** part of the visible MMSU
identity on the title/content slides. Do not use them in the HTML.

### Typography

- Scene titles: serif display face, bold, dark green. Use
  `Georgia, "Times New Roman", serif` in HTML.
- Body, bullets, tables: Arial / Helvetica sans-serif.
- The `.pptx` theme declares Arial for both major and minor fonts, but the
  rendered title slides clearly use a serif display face. Match the rendered
  look, not the theme declaration.

### Layout

- White paper background.
- Green vertical ribbon on the right edge, with a soft inner curve.
- A thinner green ribbon on the left edge on some title/closing slides.
- Subtle interlocking-circle watermark in light grey-green.
- MMSU lockup (seal + wordmark) top-left on title/closing slides; a smaller
  lockup at top-right on content slides.
- Gold 50th-anniversary logo beside the lockup on title/closing slides.
- Green filled panels for emphasis (for example, the Conceptual Framework
  INPUT/PROCESS/OUTPUT columns).
- Thin gold rules under some section titles.

### Assets extracted for the HTML build

| Asset | Path | Size | Use |
| --- | --- | --- | --- |
| MMSU lockup (seal + wordmark) | `docs/presentation/background-deck/assets/mmsu-lockup.png` | 635×155 px | Title and closing scenes |
| MMSU 50th-anniversary logo | `docs/presentation/background-deck/assets/mmsu-50-logo.png` | 170×150 px | Title and closing scenes |

Both were cropped from the deck's background image, not recreated. Inline them
as base64 data URIs in the final HTML.

---

## 2. Slide-by-slide outline

The deck has 52 slides. Slides marked "visual only" contain a figure or image
with no extractable text; the figure is not needed for the background deck.

### Opening and Chapter I

| Slide | Title / content | Notes |
| --- | --- | --- |
| 1 | (blank cover) | Visual only |
| 2 | Thesis title; authors | MMSU lockup + 50th logo; serif title; green ribbon |
| 3 | `Chapter I — INTRODUCTION` | Section divider |
| 4 | `BACKGROUND OF THE STUDY` | Two columns: what is a knowledge graph; how they are built today |
| 5 | `The problem: knowledge keeps growing` | Batch vs incremental; incremental insertion problem |
| 6 | `Why brute force doesn't work` | "huge number of queries"; Funk 22–50 prompts; $0.11–$12.45 |
| 7 | `The solution: candidate narrowing` | Two-stage idea; iText2KG, SAC-KG, EraRAG |
| 8 | `The research gaps` | Gap 1 aggregate cost; Gap 2 no head-to-head |
| 9 | `STATEMENT OF THE PROBLEM` | Central question + RQ1–RQ4 |
| 10 | `OBJECTIVES OF THE STUDY` | General + five specific objectives |
| 11 | `SIGNIFICANCE OF THE STUDY` | Three-audience table |
| 12 | `SCOPE OF THE STUDY` | Incremental phase; four strategies; data; measures |
| 13 | `LIMITATIONS OF THE STUDY` | Bare names, one model/prompt, synthetic unverified, single insertions, no hypothesis tests, two accuracy sizes, post-hoc ranking |

### Chapter II

| Slide | Title / content | Notes |
| --- | --- | --- |
| 14 | `Chapter II — REVIEW OF RELATED LITERATURE` | Section divider |
| 15 | Related literature, part 1 | Funk, iText2KG, HNSW/FAISS, EraRAG, SAC-KG |
| 16 | Related literature, part 2 | ACE/gold graphs, evaluation methods, amortized analysis, EraRAG batch-size gap, Philippine context |
| 17 | `Conceptual Framework` | INPUT / PROCESS / OUTPUT panels |

### Chapter III

| Slide | Title / content | Notes |
| --- | --- | --- |
| 18 | `Chapter III — RESEARCH METHODOLOGY` | Section divider |
| 19 | `Research Design` | Developmental, experimental; IVs and DVs |
| 20 | `Data Sources` | Synthetic pool 2,254; DSA 29; Metacademy 141; leave-one-out |
| 21 | `Experimental Design` | Input → narrowing → decision → output; only narrowing differs |
| 22 | `Research Design` | Visual only (thesis Figure 3.1) |
| 23 | `The Four Strategies` | S1–S4 table: rule and max calls |
| 24 | `The Shared Decision Step` | One call per candidate; DeepSeek; three labels; pilot F1 |
| 25 | `Experimental Procedure` | Sizes; 10 trials; 59 accuracy trials; 12 configurations |
| 26 | `Measures and Analysis` | Time, calls, precision/recall/F1, shortlist recall, log-log slope, bootstrap |
| 27 | `Decision and Ranking Framework (Post Hoc)` | Gates G1–G3; classes; weighted ranking; TOPSIS |

### Chapter IV — **out of scope for the background deck**

| Slide | Title / content | Notes |
| --- | --- | --- |
| 28 | `Chapter IV — RESULTS AND DISCUSSIONS (INITIAL RESULT)` | Section divider |
| 29 | `DATA COLLECTED` | 24 runs; 12 configurations; 3 data sources |
| 30 | `SETUP — The four strategies compared` | Table; model name inconsistency ("DeepSeek V4 Flash") |
| 31 | RQ1 wall-clock time at n = 2,000 | Results |
| 32 | visual only | RQ1 chart |
| 33 | visual only | RQ1 chart |
| 34 | RQ1 LLM calls by graph size | Results table |
| 35 | visual only | RQ2 chart |
| 36 | RQ2 accuracy of primary configurations | Results table |
| 37 | RQ2 why accuracy differs | Results |
| 38 | visual only | RQ2 chart |
| 39 | RQ2 looser settings | Results table |
| 40 | visual only | RQ3 chart |
| 41 | RQ3 trade-offs / dominance | Results |
| 42 | visual only | RQ3 chart |
| 43 | RQ3 only S3 passes every gate | Results table |
| 44 | visual only | RQ3 chart |
| 45 | RQ3 S3 most stable across weights | Results |
| 46 | visual only | RQ3 chart |
| 47 | RQ4 bucket cost does not grow | Results |
| 48 | visual only | RQ4 chart |
| 49 | `LIMITS OF THESE RESULTS` | Results limitations |
| 50 | `SUMMARY` | RQ1–RQ4 findings |
| 51 | `Thank you!` | Closing |
| 52 | Contact details | CCIS address/email |

**Do not import slides 28–50 into the background deck.** They are the results
half of the defense and are explicitly out of scope.

---

## 3. Observed style cues (reference only)

These are observations about the existing deck, not requirements for the HTML:

- Section dividers are simple: a large `Chapter I` / `Chapter II` line and a
  green rule.
- Content slides use two columns or a large visual with short callouts.
- Green filled panels are used for the conceptual framework and high-emphasis
  blocks.
- Gold is an accent, not a main fill.
- The title slide is centred, serif, and formal.
- Tables are used for strategy comparisons and literature.

---

## 4. Known inconsistencies in the source deck

Recorded so the HTML does not inherit them.

1. **Model name.** Slide 22 says "DeepSeek V4 Flash"; slide 24 and the thesis
   say DeepSeek V3 via the alias `deepseek-flash`. The background deck should
   avoid naming a version at all.
2. **Reference ranges.** Slide 16 cites `[13]–[21]` for evaluation methods,
   while the thesis reference list numbers them `[12]–[20]`. The background
   deck should not use reference numbers.
3. **Results-table provenance.** The defense script warns that some Chapter IV
   tables were regenerated from a scratch script and must be checked against
   the pipeline. This is irrelevant to the background deck because results are
   out of scope, but do not quote those tables.
4. **"Initial result" stage.** The main deck ends at Chapter IV's summary; it
   has no conclusions/recommendations chapter. The background deck does not
   need to discuss this.

---

## 5. Reference facts to carry forward

- The colour and typography tokens in Section 1.
- The two logo assets.
- The general level of formality.
- The fact that the existing deck is text- and table-heavy.
- The explicit exclusion of slides 28–50.

How to balance text, visuals, and motion is the APC's creative decision.

Do not copy the deck's result numbers, model version, reference ranges, or
post-hoc ranking framework.
