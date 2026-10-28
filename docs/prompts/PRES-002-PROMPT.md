# PRES-002 — Build prompt: background-concepts.html

Oct 28, 2026 · @lukexa

*APC-authored standalone prompt · 2026-10-28 · for one local coding agent · follows PRES-001 (status: needs-review)*

> **Live document.** Sections are added one at a time and saved as each is finished. Anything marked **(pending)** has not been written yet.

Corrections found by checking this prompt against the PRES-001 bundle are in §11 (verification log). Where §11 disagrees with §0–§10, **§11 wins**. The original text above it is unchanged.

## 0. Read this first

**What this is.** A self-contained task prompt. You, the local agent, have no memory of the planning chat. This document plus the repo files named in §1 is the whole hand-over.

**What you build.** One file, `docs/presentation/background-deck/background-concepts.html`: an offline, single-file, 22-scene presentation that teaches the thesis’s background concepts to defense panelists as if they were high-school students. It stops before Chapter 4: background concepts, research gaps, research questions, conceptual framework. **No results.**

**Who owns what.** The APC (this document) owns the creative plan: scene order, on-screen copy, visual metaphors, animation (§5–§7). You own implementation craft. You may adjust layout coordinates, timing and wording so things fit on screen. You may **not** change a fact, a required caveat, the scene order, or the content boundary without recording it in your report (§10).

**Two requirements added by Luke on 2026-10-28 (not in BRIEF.md or CONTENT-PACK.md):**

- **R1 — Title terms come first.** Right after the title card, the deck explains the words of the thesis title, one at a time, in plain language (Scene 2).
- **R2 — Every possibly unfamiliar technical term is explained**, even if the pack does not define it: recall, precision, F1, micro, macro, shortlist, and everything else in the gloss bank (§7). No term may be used on screen before it has been explained.

**Labels** (Luke’s convention):

- **\[Verified\]**: the APC read it in the uploaded bundle.
- **\[Unverified\]**: the APC could not check (no filesystem or browser access), so you must.
- **\[Inference\]**: APC judgment; challenge it if the repo says otherwise.

**Conflict rule.** The repo wins over this prompt for any checkable fact. The thesis wins over `CONTENT-PACK.md`. Report every conflict; never silently pick one side.

## 1. Role, worktree, required reading

- **Assigned agent:** claude-code, or any agent with filesystem access and a headless browser.
- **Task ID:** PRES-002. **Branch:** `task/PRES-002`. **Worktree:** `../llm-graph-insertion-complexity-PRES-002`.
- **Base commit:** \[Unverified\] whether `task/PRES-001` has been merged. Run `git worktree list`, then check whether `master` contains `docs/presentation/background-deck/BRIEF.md`. If it does, branch from `master`. If not, branch from the PRES-001 tip: `git worktree add ../llm-graph-insertion-complexity-PRES-002 -b task/PRES-002 task/PRES-001`. State which you used in the report.
- **Status row:** \[Verified\] `docs/tasks/status.md` has a PRES-001 row but **no PRES-002 row**. Add one (`in-progress`, then `needs-review` at the end) in your own row only; re-read the file immediately before editing.

**Read, in this order, before writing code:**

1. `AGENTS.md`, then `docs/context/complete-context.md`.
2. `docs/tasks/status.md`, then the tail of `docs/decisions/decision-log.md` (latest is \[D-93\]).
3. `docs/presentation/background-deck/BRIEF.md` (requirements; §1, §6, §9 still apply except where §3 below overrides).
4. `docs/presentation/background-deck/CONTENT-PACK.md` (facts), then `DECK-EXTRACT.md` (style).
5. `docs/presentation/script/Defense_Script_and_Background_Guide—Comprehensive Version.md` (the voice to match).
6. The thesis, **Chapters 1 and 3 only**. Do not mine Chapter 4 for content (you will grep it only to confirm that forbidden numbers are absent from your HTML).
7. The two logos in `docs/presentation/background-deck/assets/`.

## 2. APC review of PRES-001: corrections that supersede the pack

The APC checked the pack against the thesis. Where the pack and this section disagree, **this section wins**. Line numbers refer to the `[REVISED] …With Chapter 4.md` thesis file in the bundle.

- **C1 — Per-call time is a Chapter 4 result.** CONTENT-PACK §3 (“API call”) says one call takes “roughly 0.8–0.9 seconds”. \[Verified\] That figure is measured in thesis §4.2.3 (line 602) and repeated in §4.7 (line 839). It is out of scope. **Use no per-call duration.** Say: “each call takes real time and costs real money.”
- **C2 — BRIEF’s number-sense example is a result.** BRIEF §3 rule 8 uses “1,713 seconds — about 28 minutes”. \[Verified\] 1,713 is the Chapter 4 brute-force time at n = 2,000 (lines 602, 839), and CONTENT-PACK §11 item 1 forbids it. Ignore that example. The principle (say “about 28 minutes”, not “1,713 s”) stands, applied only to made-up or structural numbers.
- **C3 — Funk et al. “22–50 prompts” is not brute force.** \[Verified\] Thesis §1.1 (line 119) calls it “their brute-force approach”, but §2.3.1 (line 243) says it is a pruned, KRIS-adapted insertion algorithm, and that brute force means n calls. The pack’s caveat is right. **Decision \[Inference\]:** omit the 22–50 figure and the dollar range from the deck entirely; the concept does not need them. Report the §1.1 wording to Luke as a thesis inconsistency; do not try to fix the thesis.
- **C4 — Strategy labels.** \[Verified\] Thesis §3.3.2–3.3.5 headings call them Strategy A–D; Chapter 4 and the `.pptx` call them S1–S4. Use **S1–S4 only** on screen (A = S1 brute force, B = S2 threshold, C = S3 ANN, D = S4 bucket). Never show letters.
- **C5 — Gaps versus questions.** The pack implies the four RQs follow from two gaps. \[Verified\] Thesis §1.1 states **two gaps**; §1.2 (from line 135) lists **four unresolved issues** that map in order to RQ1–RQ4. Do not claim a strict one-gap-per-question mapping. Scene 20 uses the wording in this plan.
- **C6 — FAISS acronym.** BRIEF §3 rule 6 says expand FAISS on first use; CONTENT-PACK §11 item 12 forbids facts from outside the sources. \[Verified\] Thesis §3.3.4 describes FAISS only as “a widely used open-source library for efficient similarity search”. **Describe it that way; do not expand the letters.**
- **C7 — Terms the pack never defines.** \[Verified\] Micro and macro averaging and shortlist recall are defined in thesis §3.5 (line 463) and in the comprehensive script (line 874) but not in CONTENT-PACK §3. Together with the title words and many others, they are covered by R2 and the gloss bank in §7. No numbers.
- **C8 — Scene count.** R1 and the split of the accuracy material raise the plan to **22 scenes**, the top of BRIEF’s 18–22 range. A pre-approved fallback to 20 scenes is given in §6 if pacing runs long.

## 3. What stays fixed, and where this plan goes beyond BRIEF.md

`BRIEF.md` §1, §6 and §9 apply in full. Below are the constraints most likely to be broken, then five places where the APC deliberately departs from or extends the brief. Luke has not yet approved the departures; list each as accepted or changed in your report.

**Fixed:**

- One file, offline: inline CSS, JS and SVG; the two logos as base64 `data:` URIs. No `<link>`, `<script src>`, `@import`, external URL, CDN, framework or web font. Under 1.5 MB.
- 16:9 stage that letterboxes cleanly. Click or Space = one reveal step; after a scene’s last step the next click goes to the next scene.
- Overview menu on `O` or `Esc`; scene cards jump. **No** speaker-notes panel, **no** print or handout mode, no quiz, audio, video, timer or live API call.
- MMSU palette from BRIEF §5.1 (green, white, gold; no PowerPoint blue or orange). Georgia serif titles, Arial body.
- The content boundary: nothing from Chapter 4, no gates, rankings, TOPSIS, measured numbers, model version name or reference numbers.
- The five-node running example is always labeled **“illustration”**, never thesis data.

**Departures from the brief** \[Inference: APC judgment\]:

1. **D1 — Type scales with the stage, not the window.** Put `container-type: size` on the stage and size text in `cqw`: title `clamp(2rem, 4.2cqw, 5rem)`, body `clamp(1rem, 1.9cqw, 2.4rem)`, labels `clamp(0.8rem, 1.15cqw, 1.4rem)`. Why: BRIEF’s `vw` clamps stop growing at 1.5 rem body text, so on a projector the text looks smaller relative to the slide than on a laptop. With `cqw`, 1920×1080, 1366×768 and 1280×720 render the same layout. Add an `@supports not (width: 1cqw)` fallback using BRIEF’s `vw` values. At 1280×720 body text should compute to about 24 px.
2. **D2 — Step back.** BRIEF has no way to undo one reveal. Add `Backspace`, `Shift+Space` and `ArrowUp` = previous step, crossing into the previous scene’s last step; tap on the left third does the same. `ArrowLeft` and `ArrowRight` stay scene-level as in BRIEF §6.2. Arriving at a scene by `ArrowLeft` shows it **fully revealed**; arriving by `ArrowRight` or by clicking through shows step 0.
3. **D3 — Terms tab.** The overview has two tabs: **Scenes** (BRIEF §6.3) and **Terms**, an A–Z list of every term, its plain-language gloss and the scene that first explains it. Build it at runtime from `data-term` and `data-gloss` attributes (§8). Why: R2, and it lets the presenter jump to a definition during questions. If it threatens the size limit or the schedule, drop it and say so in the report.
4. **D4 — 22 scenes** instead of “about 20” (see C8).
5. **D5 — Scene state is a pure function of (scene, step).** Back-navigation and overview jumps must never leave stale visuals (§8).

Letterbox bars use `--green-900`.

## 4. Teaching design: title first, every term explained

The deck teaches in one fixed order: the words of the title, the problem, the fix, the fair test, then the questions. No term is used before its plain meaning has been shown.

**4.1 Title first (R1).** Scene 1 shows the title card and nothing else. Scene 2 reads the title back **word by word**, each word lighting up with a one-line plain gloss, then shows a five-stop roadmap. Later scenes return to the title words (the scene plan in §6 says where), so the title works as the deck’s table of contents.

**4.2 The term chip (R2).** The first time a technical term appears, it appears as a *term chip*: the word in bold serif with a thin gold underline, and its gloss in plain words in the **same reveal step**. After that it is ordinary text. Rules:

- **Analogy before term.** Show the familiar thing first, then attach the name (“a shortlist is like screening résumés”).
- **No forward references.** A gloss may only use words already explained. A term may not appear anywhere on screen (including inside another gloss) before its own chip.
- **Short glosses.** At most 14 words each.
- **Machine-readable.** Every chip carries `data-term` and `data-gloss`, so the Terms tab (D3) and the coverage test (§10) can be generated from the same source.
- **Reminders.** When a term returns after five or more scenes, show one small reminder line next to it; do not repeat the full chip.

**4.3 Voice.** Calm, concrete, never childish. One new idea per step. At most three short lines on screen per step. Spoken detail belongs to the presenter’s script, not the slide. Match the level and tone of the comprehensive script.

**4.4 Numbers.**

- Plain words first (“double the graph, double the calls”), the formal symbol (`n`, `θ`, `k`) second, in a small label.
- Every invented number on screen carries the tag **“made-up numbers, for illustration”**.
- Study **design settings** are allowed because they are not results: four strategies; `θ = 0.6`; `k = 10`; 12 yes/no questions; buckets of 5–10 concepts; 384 numbers per concept; the two expert graphs of 29 and 141 concepts; the planned graph sizes of 50 to 2,000.
- Nothing measured in Chapter 4 appears, in any form (§9).

**4.5 Bookends.** The five-stop roadmap in Scene 2 returns in Scene 22 with each stop ticked, as the recap.

## 5. Visual grammar and motion language

The deck reuses a few pieces and moves them calmly. Every animation must answer one question: *what changed, and why does it matter?*

**5.1 Stage and chrome.**

- White paper stage. Thin green ribbon on the right edge with a soft inner curve. A faint interlocking-circle watermark (low contrast; hidden below 900 px wide). A gold 4 px progress bar along the bottom and a small `NN / NN` counter.
- **One** MMSU lockup element in the DOM. It is large and centred on Scene 1 and Scene 22 (with the 50th-anniversary logo beside it) and glides, by `transform`, to a small top-right position on content scenes.
- Scene title: Georgia, bold, dark green, at most six words, with a thin gold rule under it.
- Gold on white fails contrast (2.4:1, \[Verified\] by calculation). Gold is for rules, underlines and large shapes only; **never** body text on white. Gold text is allowed only at large size on `--green-900` (4.3:1). Do not set `--green-500` text on `--green-100` (4.3:1); use `--green-900` or `--ink` there.

**5.2 Shapes.**

- **Concept** = rounded-rectangle chip, `--green-100` fill, 2 px `--green-900` outline, Arial label.
- **New concept** = same chip with `--gold-100` fill and a gold outline, tagged “new”.
- **Edge** = 2 px `--line` stroke. A *directed* edge has an arrowhead and reads “this first, then that” (prerequisite → dependent). Emphasised edges turn `--green-700`.
- **LLM call** = speech-bubble icon with a small counter. **Shortlist** = a green-outlined tray the chips slide into.
- `--alert` appears only where cost blows up (the brute-force growth in Scene 7).
- Icons: inline SVG, 2 px stroke, rounded caps. No emoji, photos or clip-art.

**5.3 The running example (one source of truth).** Define it once in JavaScript and draw it from there in every scene that shows it. Coordinates in a 1100 × 560 SVG viewBox; **the arrangement never moves between scenes**, so the audience recognises it instantly.

- Existing concepts: Arrays (120, 120), Loops (120, 360), Sorting (400, 120), Recursion (400, 360), Trees (680, 360).
- New concept: Binary Search Tree (940, 230).
- Existing edges (illustration): Arrays → Sorting, Loops → Sorting, Loops → Recursion, Recursion → Trees.
- True links of the new concept (illustration): Trees → Binary Search Tree, Recursion → Binary Search Tree.
- Made-up similarity scores of the new concept to each existing one: Trees 0.90, Sorting 0.70, Recursion 0.62, Arrays 0.55, Loops 0.30.
- Every scene that shows it carries a small tag: **“illustration — not thesis data”**.

**5.4 Motion language.**

- **Reveal:** opacity 0→1 plus a 12 px upward `translateY`, 380 ms ease-out; groups stagger by 80 ms.
- **Draw:** edges draw by `stroke-dashoffset` over 500 ms (paint-only, so allowed), arrowhead fades in after.
- **Focus:** one gold halo pulse (scale 1→1.06→1, 600 ms). Never loops.
- **Select by dimming, not deleting:** when a strategy shortlists, chosen chips slide into the tray and the rest drop to 35% opacity, so the audience sees what was left out.
- **Counters** tick in discrete steps (like calls being made), at most 1.2 s in total; the final value is in the DOM at once.
- No bounce, spin, parallax or looping motion. One main motion per step; 250–600 ms each.
- **Reduced motion:** with `prefers-reduced-motion: reduce`, each click still reveals the next step (the presenter needs the pacing) but it appears instantly, with no transform, draw or tick. \[Inference\] This is how BRIEF’s “shows all steps without animation” is read; flag it in the report if you read it differently.

## 6. Scene plan (22 scenes, about 21 minutes)

Each scene lists its **menu title** and **menu line** (these feed the overview cards), its target time, and its reveal steps. Step 0 is what is on screen when the scene opens. Quoted text is the on-screen copy; keep it as written unless it will not fit, and keep every fact. **Term chips** are in bold; their glosses are in §7. The time column is a target for the presenter, not a timer; no timer appears in the deck.

### Part A — The title and the problem (Scenes 1–7)

#### Scene 1 — Title

*Menu line: what the thesis is called · \~25 s*

- **Step 0:** large MMSU lockup and 50th-anniversary logo; the full thesis title in serif, exactly: “An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction”; the four authors (Adrian Luke A. Labasan, Alejandrei Jazz F. Lopez, Geila May C. Rigayen, Melvie Jeanna O. Abad; \[Verified\] from the thesis title page, lines 1–11). Small “Click to continue” cue, first scene only.
- **Step 1:** subtitle line: “Background concepts: the ideas behind the study, built from the ground up. No results yet.”

**Motion:** lockup and title fade in together; nothing else moves. **Guard:** no model name, no date or venue line that is not on the thesis title page.

#### Scene 2 — Reading the title

*Menu line: what each word of the title means · \~90 s · this is requirement R1*

The title sentence sits at the top in smaller type. Each step lights one word group in gold-100 and dims the rest to 55%; the gloss appears on the right.

1. **Empirical**: “learned by measuring, not by arguing.”
2. **Complexity**: “how much more work a job takes as the job gets bigger.”
3. **Analysis**: “looking at the measurements to find the pattern.”
4. **Candidate-narrowing**: “a candidate is an idea that might fit; narrowing is cutting a long list down to a short one.”
5. **Strategies**: “four different recipes for doing the narrowing.”
6. **Incremental**: “adding one thing at a time to something that already exists.”
7. **LLM-driven**: “an AI that reads and writes language makes the judgment calls. LLM = Large Language Model.”
8. **Graph construction**: “building a map of ideas joined by links.”
9. Plain-words line replaces the gloss: “We measure how the cost and accuracy of adding one new idea to a growing map of ideas change, using an AI judge and four ways to shortlist.”
10. Five-stop roadmap strip: ① Maps of ideas ② The cost problem ③ Four shortlists ④ A fair test ⑤ The open questions. Footer: “This briefing stops before the results.”

**Motion:** the highlight moves left to right in title order; passed words keep a thin underline, so by step 8 the whole title is underlined (“everything is explained”). **Guard:** each gloss is a first look; later scenes deepen it. Do not mention any measured result.

#### Scene 3 — Maps made of dots and arrows

*Menu line: node, edge, graph, direction, prerequisite · \~60 s*

1. A road map: five city dots appear. Chip **node**: “a thing on the map.”
2. Roads draw between the dots. Chip **edge**: “a connection between two things.”
3. A brace around the whole map. Chip **graph**: “things plus connections.” Beside it a small second example: “A social network is a graph too: people and friendships.”
4. Roads become one-way arrows. Chip **directed edge**: “an arrow; it goes one way only.”
5. Two nodes, Limits → Calculus. Chip **prerequisite**: “something you must understand first.” Copy: “Limits come before Calculus.”
6. The arrow flips to Calculus → Limits, shown dashed with a ✗. Copy: “Flip the arrow and the claim is wrong.” Then it flips back.

**Motion:** roads draw; the arrow flip is a 180° `transform` rotation about its midpoint. **Guard:** use the thesis meaning of prerequisite: needed *directly or indirectly* before the other (the decision step uses it).

#### Scene 4 — A map of ideas, and why we cannot draw it by hand

*Menu line: knowledge graph, domain expert, scale · \~60 s*

1. The running example appears (tag: “illustration — not thesis data”): Arrays, Loops, Sorting, Recursion, Trees with their four arrows. Chip **knowledge graph**: “a map of ideas: ideas are the dots, relationships are the arrows.”
2. The path Loops → Recursion → Trees glows. Copy: “Start anywhere. Follow the arrows to what you need first.”
3. Three small icons: “Used in web search, recommendations and education.”
4. A person at a desk drawing arrows by hand. Chip **domain expert**: “a person who knows a subject deeply.” Copy: “Built by hand, it is accurate but slow.”
5. A pile of books grows past the expert while new books keep arriving. Chip **scale**: “still working when the job gets much bigger.” Copy: “By hand, this does not scale.”

**Motion:** books stack with an 80 ms stagger; the pile ends taller than the expert icon. **Guard:** no statistic about expert time; the thesis states the limit qualitatively.

#### Scene 5 — The AI helper and what one question costs

*Menu line: LLM, prompt, API call, wall-clock time · \~55 s*

1. Copy: “What if a helper could read and judge?” Chip **LLM (Large Language Model)**: “an AI trained on huge amounts of text that can read, write and judge language.”
2. A speech bubble from the running example: “Is Trees needed before Binary Search Tree?” Chip **prompt**: “the question we send it.” An answer bubble returns: “Yes. Trees first.”
3. A call counter ticks 0 → 1. Chip **API call**: “one question sent, one answer back.” Small line: “API: the doorway one program uses to ask another.”
4. Clock and coin icons. Copy: “Every call takes time and costs money, so we count calls.” Chip **wall-clock time**: “how long you actually wait, by the clock on the wall.”
5. Copy: “It is not a database. It can be wrong.” Then: “That is why we later check it against experts.” (foreshadows Scene 17)

**Motion:** the bubble travels left to right by `transform`; the counter ticks once. **Guard:** **no per-call duration and no model name** (see C1).

#### Scene 6 — Build it all at once, or add one idea

*Menu line: batch, incremental insertion, n, what an insertion decides · \~50 s*

1. Analogy: a whole library built in one go. Chip **batch construction**: “give the AI everything and ask for the finished map in one pass.”
2. Analogy: one new book filed into a library that already exists. Chip **incremental insertion**: “adding one new idea to a map that already exists.” Copy: “This study is only about this.” The new chip *Binary Search Tree* slides in beside the running example.
3. Copy: “New ideas keep arriving. Rebuilding everything for each one is wasteful.”
4. Chip **n**: “the number of ideas already on the map.” Label: “n = 5 now; n + 1 = 6 after.” (tag: illustration)
5. Dashed question-mark links from the new chip to every old chip. Copy: “Inserting means deciding which old ideas it connects to, and which way each arrow points.”

**Motion:** the new chip glides in; dashed links fade in with an 80 ms stagger, setting up Scene 7. **Guard:** the thesis studies only the insertion phase.

#### Scene 7 — The obvious way: ask about everything

*Menu line: brute force, linear growth, the control · \~60 s*

1. Copy: “Simplest idea: ask the AI about every old idea.” Chip **brute force**: “try everything; no shortcuts.” A call bubble lands on each dashed link while the counter ticks 1 … 5. Label: “5 old ideas → 5 calls.”
2. Label: “n ideas → n calls.”
3. Abstract dots (no names) grow 5 → 10 → 20; the counter follows: 5 → 10 → 20, drawn as three bars, the tallest tinted `--alert`. Chip **linear growth**: “twice the size means twice the work.” Tag: “made-up numbers, for illustration.”
4. Copy: “A map with thousands of ideas means thousands of calls for every new idea.” (\[Verified\] the thesis §1.1 says a graph “may already contain thousands” of nodes.)
5. Chip **control**: “the plain version we compare everything else against.” Copy: “Brute force is our control.”

**Motion:** call bubbles drop in with ticks; bars grow by `transform: scaleY`. **Guard:** **omit Funk et al.’s 22–50 prompts and the dollar range** (C3); do not call anything but S1 “brute force”.

### Part B — The fix: shortlists and the four strategies (Scenes 8–16)

#### Scene 8 — Interview the shortlist, not everyone

*Menu line: candidate, shortlist, candidate narrowing, the two stages and the risk · \~50 s*

1. Analogy: 500 résumés arrive as a stack of cards. Copy: “You do not interview everyone.”
2. A quick screen leaves a handful. Chip **shortlist**: “the short list of the likeliest choices.” Chip **candidate**: “an old idea that might connect to the new one.”
3. Back to the running example (illustration). A funnel icon sends Trees and Sorting into a tray; the other three dim. Chip **candidate narrowing**: “cut the long list to a shortlist before asking the AI.”
4. Two labelled stages: “Stage 1: make the shortlist. Cheap and fast; no AI call.” “Stage 2: the AI judges only the shortlist. Slow and costly.”
5. The dimmed Recursion chip gets a gold tag, “a true link left out”. Copy: “The risk: a real connection can miss the shortlist.”

**Motion:** chips slide into the tray; the rest dim to 35%. **Guard:** the thesis calls this the trade of computation against the risk of excluding the correct connection point (§1.2). Foreshadows Scene 11.

#### Scene 9 — Meaning written as numbers

*Menu line: embedding, vector, a map of meaning, computed locally · \~60 s*

1. Copy: “How can a computer tell which ideas are close in meaning?” A blank 2-D map appears.
2. Each running-example chip lands on the map, with a tiny bracket of made-up numbers beside it. Chip **embedding**: “a list of numbers that stands for the meaning of a word or phrase.” Chip **vector**: “a list of numbers, read as a point or an arrow.”
3. Trees, Recursion and Binary Search Tree sit close together; Loops sits far away. Copy: “Similar meanings get nearby points.”
4. Copy: “Our embeddings have 384 numbers per idea. We can only draw 2.” Small note: “The input is just the idea’s name.”
5. Chip **local model**: “a small program on the researcher’s own computer; no AI call.” Copy: “Cheap and fast.”

**Motion:** chips drop onto the map with the 80 ms stagger. **Guard:** the 384 and “bare names” are design facts (thesis §3.3.4 and §1.5). Naming the model (`all-MiniLM-L6-v2`) is optional and only as a tiny footnote; never name the decision-step model.

#### Scene 10 — Closeness is an angle

*Menu line: cosine similarity and what a score does not mean · \~55 s*

1. Each idea becomes an arrow from one shared starting point. Binary Search Tree and Trees point almost the same way.
2. Chip **cosine similarity**: “how closely two arrows point the same way.” Scale: same direction = 1; sideways ≈ 0.
3. The Trees arrow swings away from Binary Search Tree; a dial reads 0.90 → 0.30, passing about 0 at a right angle.
4. Horizontal score bars for the running example (made-up numbers, in the sort order): Trees 0.90, Sorting 0.70, Recursion 0.62, Arrays 0.55, Loops 0.30.
5. Copy: “Close in meaning is not the same as connected. The AI still has to judge.” (Sorting scores high yet is not a prerequisite in the illustration.)

**Motion:** the swinging arrow is a `transform: rotate`; the bars grow by `scaleX`. **Guard:** cosine similarity measures the angle between the vectors, nothing more.

#### Scene 11 — A cutoff, or a fixed number of seats

*Menu line: threshold and top-k, side by side · \~60 s*

1. The score bars stay. Copy: “Now decide who makes the shortlist.”
2. Chip **threshold**: “keep every score above a set line.” A line at 0.6 (label “θ = 0.6”) slides in; Trees, Sorting and Recursion light up. Small note: “strictly above”.
3. Two tiny made-up cases: one where nobody clears the line (empty tray) and one where everybody does. Copy: “The shortlist can be empty, or almost everyone.”
4. Chip **top-k**: “always keep the k highest scores; k fixed seats.” Two seats (k = 2): Trees and Sorting sit. Recursion (0.62) gets the gold tag “a true link left out”.
5. Side-by-side labels: “Cutoff: size varies. Seats: size fixed. Same scores, different shortlist.”

**Motion:** the threshold line slides down the bars; seats appear as empty slots, then fill. **Guard:** threshold means *strictly above*; S3 later uses k = 10, not 2 (k = 2 is illustration only).

#### Scene 12 — Strategies 1 and 2

*Menu line: S1 brute force, S2 embedding threshold, why S2 is not always cheap · \~45 s*

1. Four lanes appear, each with an empty tray: S1, S2, S3, S4. Copy: “Four ways to make the shortlist.” Only the names are shown yet; S3 and S4 stay dim.
2. **S1 — Brute force:** “Shortlist = every old idea.” All five chips enter the tray. Label: “most calls: n”.
3. **S2 — Embedding threshold:** “Shortlist = ideas scoring above 0.6.” Three chips enter. Small note: “0.6 chosen in advance, not adjusted after seeing results.”
4. The tray is empty. Copy: “Nobody clears the line: no AI call at all.”
5. Chip **cap**: “a fixed upper limit.” Copy: “S2 has no cap. If everyone clears the line, it costs n calls, the same as brute force.”

**Motion:** chips slide into their tray; the empty-tray case fades in as a ghost. **Guard:** S2 is uncapped and can be empty (do-not-use list items 7).

#### Scene 13 — Strategy 3: finding the closest ideas fast

*Menu line: S3 ANN retrieval, HNSW, FAISS, approximate by design · \~60 s*

1. Copy: “S3 uses the same scores, but picks by count, not by cutoff.” Chip **nearest neighbour**: “the old idea whose meaning is closest to the new one.”
2. Chip **ANN (approximate nearest-neighbour search)**: “finds the closest ideas fast, without checking every one. It can rarely miss one.”
3. A layered map: a sparse top layer, denser layers below. Chip **HNSW (Hierarchical Navigable Small World)**: “a layered map of shortcuts: start high, hop closer, drop a layer, repeat.”
4. A search path starts at the top layer and takes long hops toward the new idea. Chip **greedy**: “always takes the step that looks best right now.”
5. The path drops a layer and takes shorter hops, then arrives near the new idea.
6. Copy: “It keeps the 10 closest ideas: at most 10 AI calls.” (k = 10)
7. Chip **FAISS**: “a widely used open-source library that does this fast search.” Copy: “Approximate by design: it may rarely miss a true nearest neighbour.”

**Motion:** the path draws layer by layer (`stroke-dashoffset`); the glow moves with `transform`. **Guard:** keep “approximate” and “may rarely miss”. Do not claim a miss rate.

#### Scene 14 — Strategy 4: size-capped folders

*Menu line: S4 bounded bucket, hyperplane, binary code, Gray order, EraRAG · \~85 s*

1. Analogy: a filing cabinet with small folders. Chip **bucket**: “a small folder of similar ideas.” Copy: “A new item goes into one folder. Only that folder gets searched.”
2. The 2-D map returns. A random line cuts it. Chip **random hyperplane**: “a random dividing wall through the map of meaning.” Chip **bit**: “one yes/no answer, written 0 or 1.” Each idea gets a 0 or 1 by its side of the wall.
3. More walls cut the map. Chip **binary code**: “the string of 0s and 1s an idea collects.” Copy: “Similar ideas land on the same side of most walls, so their codes are alike.” Label: “12 walls = 12 bits = 4,096 possible codes, more than the 2,000-idea maximum.”
4. Codes line up in a row, neighbours differing by one bit. Chip **Gray order**: “an order where neighbouring codes differ in just one bit.”
5. The row is cut into folders of 5 to 10 ideas; an oversize folder splits in half, an undersize one joins its closest neighbour. Chip **bounded**: “kept within a fixed size limit.”
6. The new idea gets its code and drops into its home folder; only that folder’s members go to the AI. Copy: “At most 10 calls.”
7. Copy: “Inspired by EraRAG’s size-capped buckets, adapted to this task; not a copy of it.” Chip **EraRAG**: “an earlier research system built on size-capped buckets.” Small note: “The random walls come from a fixed starting number (seed 42), so every run repeats.” Chip **seed**: “a fixed starting number that makes random choices repeatable.”

**Motion:** walls draw one by one; chips colour by side; folders form as brackets under the row. **Guard:** do not claim this reproduces EraRAG’s full architecture (thesis §3.3.5).

#### Scene 15 — One shared judge

*Menu line: the decision step, the three answers, why sharing makes the test fair · \~65 s*

1. The four lanes from Scene 12 flow into one box: “Same AI judge for all four.”
2. Chip **decision step**: “the AI judges each shortlisted pair, one call per pair.” The AI sees only the two names and the subject area, e.g. “data structures and algorithms”.
3. Chip **label**: “a short fixed answer the AI must choose from.” Three cards: “the new idea is needed first” (Limits, Calculus); “the old idea is needed first” (Calculus, Limits); “neither” (poetry, plumbing). Show the internal names `X_PREREQ_Y`, `Y_PREREQ_X`, `NONE` in small type.
4. Running example (illustration): Trees → Binary Search Tree and Recursion → Binary Search Tree arrows are added; Sorting gets “neither”. The new idea is now connected.
5. Chip **temperature 0**: “turns off random variety, so the same question gets the same answer.” Copy: “Same AI, same wording, one question at a time.”
6. Chip **fair test**: “change one thing and keep everything else the same.” Analogy: “To compare engines, keep the car the same. The judge is the car; the shortlist is the engine.”

**Motion:** the arrows draw in after each label lands. **Guard:** “an AI, called through an API” only; no model name or version (C1 and pack §11 item 3).

#### Scene 16 — The four, side by side

*Menu line: shortlist rules, call limits, and the caveat · \~65 s*

1. A table builds one row per step, columns: Strategy, Shortlist rule, Most calls for one insertion. Row S1: “every old idea”, “n”.
2. Row S2: “ideas scoring above 0.6”, “up to n; often far fewer; can be 0”.
3. Row S3: “the 10 closest ideas”, “10”.
4. Row S4: “the ideas in its own folder (5–10)”, “at most 10”.
5. Four bars for a made-up map of 100 ideas: 100, up to 100, 10, at most 10. Tag: “the most each could ever need; not measured.” Chip **worst case**: “the most work a method could ever need.”
6. A gold-outlined card: “S3 and S4 both cap at 10. So this test cannot fully separate how folders are built from how long the shortlist is.”
7. Copy: “Every setting was chosen before any run, not adjusted after seeing results.”

**Motion:** rows slide in; the bars grow by `scaleY`. **Guard:** the S3/S4 cap caveat is required here (BRIEF §9). The bars are *bounds*, not results.

### Part C — The fair test, the gaps and the questions (Scenes 17–22)

#### Scene 17 — The answer key

*Menu line: gold standard, leave-one-out, direction, why cost needs no key · \~55 s*

1. Copy: “How do we know the AI put an idea in the right place? We need an answer key.”
2. Chip **gold-standard graph**: “a map of ideas that experts have checked: our answer key.” Chip **ground truth**: “the known right answer.” Copy: “Two expert-checked maps: 29 ideas (Data Structures and Algorithms) and 141 ideas (Metacademy).”
3. Chip **leave-one-out**: “hide one idea, put it back using a strategy, check it against the key.” A small expert map: one chip lifts out, leaving a dashed hole; proposed links come back and are compared with the key. Copy: “Then repeat for every idea.”
4. A proposed arrow reversed against the key turns gold-outlined. Copy: “An arrow the wrong way counts as wrong.”
5. Chip **synthetic data**: “invented but realistic data.” Copy: “Cost needs no answer key, so large invented maps (up to 2,000 ideas) can measure it. Accuracy never uses them.”
6. Copy: “Accuracy is judged against experts, not against the AI’s own opinion.”

**Motion:** the lifted chip rises by `translateY` and its hole stays; proposed links draw back in. **Guard:** show **no** accuracy number. The 29, 141 and 2,000 are design facts. \[Verified\] thesis §3.2.1 and §3.2.2.

#### Scene 18 — Scoring a placement

*Menu line: precision, recall, F1, micro vs macro, shortlist recall, random baseline · \~90 s*

Tag every number in this scene: “made-up numbers, for illustration”.

1. Setup: “The key says 4 links are true. The strategy proposes 5. 3 of those are right.” Four green link icons, five outlined proposals, three overlapping.
2. Chip **precision**: “of the links you proposed, how many were right.” “3 ÷ 5 = 0.60”. Copy: “Of what you said, how much was right?”
3. Chip **recall**: “of the true links, how many you found.” “3 ÷ 4 = 0.75”. Copy: “Of what was true, how much did you find?”
4. Chip **F1**: “one score that is high only when precision and recall are both high.” Show “about 0.67” for the example. Then the lopsided case: “precision 1.00, recall 0.10: ordinary average 0.55, F1 only 0.18.” Chip **harmonic mean**: “a balanced average that falls if either number is low.” (F1 is the harmonic mean of the two.) \[Verified\] 2·0.60·0.75 ÷ 1.35 = 0.667; 2·1.00·0.10 ÷ 1.10 = 0.182.
5. The reversed arrow from Scene 17: “A link drawn the wrong way is one wrong proposal and one missed true link.”
6. Chip **micro**: “many ideas are tested one by one. Micro pools every link from every test, then scores once. Ideas with many links count more.” Example: idea A has 10 proposed links, 9 right; idea B has 1 proposed, 0 right. Pooled precision: 9 ÷ 11 ≈ 0.82.
7. Chip **macro**: “score each idea on its own, then average the scores. Every idea counts equally.” Same example: (0.90 + 0.00) ÷ 2 = 0.45. Copy: “Same tests, two honest averages. Which one is used is always stated.”
8. Chip **shortlist recall**: “of an idea’s true neighbours, how many even made the shortlist.” Chip **neighbour**: “an idea joined to it by a link, either direction.” Copy: “It shows what narrowing throws away before the AI looks.”
9. Chip **random baseline**: “what a shortlist picked blindly would score.” Copy: “A good shortlist should beat blind luck.”

**Motion:** the true and proposed link sets slide together; the overlap glows; the F1 bar is drawn next to the plain average so the gap is visible. **Guard:** §7 defines each of these in the same words; micro and macro definitions follow thesis §3.5 (line 463) and the comprehensive script (line 874). Do not state any real F1, precision or recall value.

#### Scene 19 — What is still missing: the two gaps

*Menu line: research gap, aggregate cost, head-to-head, how sure we are · \~55 s*

1. Copy: “Others have narrowed candidates before. What is still missing?” Chip **research gap**: “a question the studies we read do not answer.”
2. **Gap 1.** A restaurant shows one big monthly total; beside it a menu grows. Chip **aggregate**: “added up into one total.” Copy: “Studies report one total for a whole experiment. None of the studies we reviewed measures what one insertion costs as the map grows.”
3. **Gap 2.** Three whole cars drive past, each with a different engine. Chip **head-to-head**: “compared directly, one against another.” Chip **like-for-like**: “same task, same rules, same measurements.” Copy: “Each system is tested whole. None of the studies we reviewed compares the narrowing methods head-to-head, like-for-like.”
4. Chip **literature search**: “looking through published research for what is already known.” Copy: “Our search was structured, but not exhaustive. So we say: *none of the studies we reviewed*.”

**Motion:** the menu list grows while the monthly total stays a single fixed number; in the cars scene the engines swap while the car body stays put. **Guard:** never “nobody has ever”. The restaurant and car analogies come from the pack’s analogy bank.

#### Scene 20 — Four questions

*Menu line: RQ1–RQ4 in plain words, without answers · \~55 s*

1. Chip **research question (RQ)**: “the question a study sets out to answer.” Card **RQ1 · Cost**: “How do time and AI calls per insertion change as the map grows?” A blank axis: map size 50 → 2,000 across, cost up; a dashed “?” curve.
2. Card **RQ2 · Accuracy**: “Does placement accuracy hold up as the map grows?” (judged against the expert maps)
3. Card **RQ3 · Comparison**: “How do the four strategies compare under identical conditions?” Four lanes, one shared judge.
4. Card **RQ4 · One insertion, one folder**: “Does one insertion cost the same however big the map is, when only one capped folder is searched?” Two ghost options, “flat?” and “rising?”, neither drawn as an answer.
5. Copy: “Gap 1 → questions 1 and 4. Gap 2 → question 3. Question 2 asks whether the savings cost accuracy.” \[Inference\] This mapping follows thesis §1.1 and §1.2; do not present it as strict one-to-one (C5).

**Motion:** cards slide in by `transform`; every graph shows only dashed “?” shapes. **Guard:** **no hint of any answer**: no solid curve, no arrow trending up or flat, no number on the axes except the planned 50 and 2,000.

#### Scene 21 — The premise behind question 4

*Menu line: amortized cost, premise versus theorem, what changes in our test · \~45 s*

1. Analogy: a growing list. Chip **amortized cost**: “cost averaged over many operations.” A row of cells fills one at a time; at the end it copies itself into a longer row (a flash), then keeps going. Copy: “Rare big copy, many cheap steps: a small average.”
2. Copy: “EraRAG gives a proof of a bound like this for its folders.” Chip **theorem**: “a claim proved by logic.” Chip **premise**: “the assumption a claim rests on.” Copy: “The proof rests on a premise: one insertion touches only one capped folder, so it does not cost more just because the map is bigger.”
3. Two sliders: “How much new material arrives at once” (batch size) and “How big the map already is.” EraRAG’s experiments move the first slider only.
4. The second slider starts moving. Copy: “We move the second, one insertion at a time. So we test the premise, not the theorem.”

**Motion:** the row-copy flash is one gold pulse; the sliders’ knobs move by `transform: translateX`. **Guard:** use “premise” and “single insertion”; never “we prove EraRAG’s bound”. This scene may be merged into Scene 20 under the fallback.

#### Scene 22 — The whole study in one picture

*Menu line: input, process, output, and the recap · \~50 s*

1. Three green panels (the look of the existing deck’s slide 17): INPUT, PROCESS, OUTPUT. Chip **conceptual framework**: “a one-page picture of how the study is set up.”
2. INPUT fills: “an existing map of n ideas · one new idea · one narrowing strategy”.
3. PROCESS fills: “1 Narrow to a shortlist. 2 The shared AI judge decides each pair. 3 Update the map and measure.” The narrowing box cycles S1 → S2 → S3 → S4 while the other boxes stay put. Copy: “Only this box changes.”
4. OUTPUT fills: “an updated map of n + 1 ideas · cost: time and AI calls · accuracy: precision, recall, F1”.
5. The Scene 2 roadmap returns; the five stops tick one by one, each with a four-word takeaway: “dots and arrows”, “n calls is too many”, “four ways to shortlist”, “one fair judge”, “four open questions”.
6. The lockup and 50th-anniversary logo return large. Copy: “Next: the results, in the main defense presentation.”

**Motion:** the panels fill left to right; ticks pop in with a 0.8→1 `scale`; the S1–S4 cycle is a 700 ms crossfade. **Guard:** the deck ends here. No result, ranking, gate or number from Chapter 4 anywhere, including in the last line.

### Fallback if the run is too long

If rehearsal timing exceeds 22 minutes, the pre-approved cut is **20 scenes**: merge Scenes 10 and 11 (cosine plus threshold and top-k) and merge Scenes 20 and 21 (four questions plus the premise). No other cut is pre-approved. Report which you used.

## 7. Gloss bank: every term, in plain words (requirement R2)

This table is the master list of on-screen glosses, in order of first appearance. Use these words (shortened to fit if needed, never made more technical). Each row becomes one `data-term` / `data-gloss` pair in the HTML and one line in the Terms tab (D3). A term with no chip in the scene text above is a **patch**: add the chip exactly as listed under “Patches” below the table.

| Term | Plain gloss | Scene |
| --- | --- | --- |
| Empirical | learned by measuring, not by arguing | 2 |
| Complexity | how much more work a job takes as the job gets bigger | 2 |
| Analysis | looking at the measurements to find the pattern | 2 |
| Narrowing | cutting a long list down to a short one | 2 |
| Strategy | a recipe for doing a job; here, four recipes for narrowing | 2 |
| Incremental | adding one thing at a time to something that already exists | 2 |
| LLM (Large Language Model) | an AI trained on huge amounts of text that can read, write and judge language | 2, 5 |
| Graph construction | building a map of ideas joined by links | 2 |
| Node | a thing on the map | 3 |
| Edge | a connection between two things | 3 |
| Graph | things plus connections | 3 |
| Directed edge | an arrow; it goes one way only | 3 |
| Prerequisite | something you must understand first (directly or indirectly) | 3 |
| Knowledge graph | a map of ideas: ideas are the dots, relationships are the arrows | 4 |
| Concept | the thesis’s word for an idea on the map (the deck says “idea”) | 4 (patch) |
| Domain expert | a person who knows a subject deeply | 4 |
| Scale | still working when the job gets much bigger | 4 |
| Prompt | the question we send the AI | 5 |
| API call | one question sent, one answer back | 5 |
| API | the doorway one program uses to ask another | 5 |
| Wall-clock time | how long you actually wait, by the clock on the wall | 5 |
| Database | an organised store of facts you look things up in | 5 (patch) |
| Batch construction | give the AI everything and ask for the finished map in one pass | 6 |
| Incremental insertion | adding one new idea to a map that already exists | 6 |
| Insertion | adding the new idea and deciding which old ideas it connects to, and which way | 6 |
| n | the number of ideas already on the map | 6 |
| Brute force | try everything; no shortcuts | 7 |
| Linear growth | twice the size means twice the work | 7 |
| Control | the plain version we compare everything else against | 7 |
| Shortlist | the short list of the likeliest choices | 8 |
| Candidate | an old idea that might connect to the new one | 8 |
| Candidate narrowing | cut the long list to a shortlist before asking the AI | 8 |
| Embedding | a list of numbers that stands for the meaning of a word or phrase | 9 |
| Vector | a list of numbers, read as a point or an arrow | 9 |
| Local model | a small program on the researcher’s own computer; no AI call | 9 |
| Cosine similarity | how closely two arrows point the same way | 10 |
| Threshold | keep every score above a set line | 11 |
| θ (theta) | the Greek letter we use for the cutoff value | 11 (patch) |
| Top-k | always keep the k highest scores; k fixed seats | 11 |
| Cap | a fixed upper limit | 12 |
| Nearest neighbour | the old idea whose meaning is closest to the new one | 13 |
| ANN (approximate nearest-neighbour search) | finds the closest ideas fast, without checking every one; it can rarely miss one | 13 |
| HNSW (Hierarchical Navigable Small World) | a layered map of shortcuts: start high, hop closer, drop a layer, repeat | 13 |
| Greedy | always takes the step that looks best right now | 13 |
| FAISS | a widely used open-source library that does this fast search | 13 |
| Bucket | a small folder of similar ideas | 14 |
| Random hyperplane | a random dividing wall through the map of meaning | 14 |
| Bit | one yes/no answer, written 0 or 1 | 14 |
| Binary code | the string of 0s and 1s an idea collects | 14 |
| Gray order | an order where neighbouring codes differ in just one bit | 14 |
| Bounded | kept within a fixed size limit | 14 |
| EraRAG | an earlier research system built on size-capped buckets | 14 |
| Seed | a fixed starting number that makes random choices repeatable | 14 |
| Decision step | the AI judges each shortlisted pair, one call per pair | 15 |
| Label | a short fixed answer the AI must choose from | 15 |
| Temperature 0 | turns off random variety, so the same question gets the same answer | 15 |
| Fair test | change one thing and keep everything else the same | 15 |
| Worst case | the most work a method could ever need | 16 |
| Gold-standard graph | a map of ideas that experts have checked: our answer key | 17 |
| Ground truth | the known right answer | 17 |
| DSA (Data Structures and Algorithms) | a core computer-science subject; the first expert map covers it | 17 (patch) |
| Metacademy | the name of the second expert-checked map | 17 (patch) |
| Leave-one-out | hide one idea, put it back using a strategy, check it against the key | 17 |
| Synthetic data | invented but realistic data | 17 |
| Precision | of the links you proposed, how many were right | 18 |
| Recall | of the true links, how many you found | 18 |
| F1 | one score that is high only when precision and recall are both high | 18 |
| Harmonic mean | a balanced average that falls if either number is low | 18 |
| Micro | pool every link from every test, then score once; ideas with many links count more | 18 |
| Macro | score each idea on its own, then average; every idea counts equally | 18 |
| Shortlist recall | of an idea’s true neighbours, how many even made the shortlist | 18 |
| Neighbour | an idea joined to another by a link, in either direction | 18 |
| Random baseline | what a shortlist picked blindly would score | 18 |
| Research gap | a question the studies we read do not answer | 19 |
| Aggregate | added up into one total | 19 |
| Head-to-head | compared directly, one against another | 19 |
| Like-for-like | same task, same rules, same measurements | 19 |
| Literature search | looking through published research for what is already known | 19 |
| Research question (RQ) | the question a study sets out to answer | 20 |
| Amortized cost | cost averaged over many operations | 21 |
| Theorem | a claim proved by logic | 21 |
| Premise | the assumption a claim rests on | 21 |
| Conceptual framework | a one-page picture of how the study is set up | 22 |
| Input / Process / Output | what goes in, what happens, what comes out | 22 (patch) |

**Patches to the scene text** (add these chips; they were left out above):

- **Scene 4, step 1:** a small note under the chip: “Ideas, which the thesis calls *concepts*.”
- **Scene 5, step 5:** chip **database** on the words “not a database”.
- **Scene 11, step 2:** chip **θ (theta)** on the “θ = 0.6” label.
- **Scene 17, step 2:** chips **DSA** (expanded as shown) and **Metacademy**.
- **Scene 22, step 1:** chip **Input / Process / Output** on the three panel headings.

**Reserve glosses for questions (not on any slide; ask Luke before adding):** *true positive*: a proposed link that matches the key; *false positive*: a proposed link the key does not have; *false negative*: a true link that was never proposed; *transitive*: if A leads to B and B leads to C, then A leads to C; *pilot*: a small trial run before the real study; *latency*: the delay before an answer comes back.

## 8. Build notes beyond BRIEF §6

BRIEF §6 (file shape, navigation, overview, progress, responsiveness, performance) stands. These notes add what the scene plan needs.

**8.1 Markup contract.** One `<main id="deck">` holding 22 `<section class="scene">` elements.

- Each scene has `id="s01"` … `"s22"`, `data-title` (the menu title), `data-teaches` (the menu line) and `data-type="title|content|close"`. The overview cards are built from these at runtime; there is no second list to keep in sync.
- Reveal steps: `data-step="N"` means “visible once the step is at least N”. `data-until="M"` means “hidden again from step M” (for things that are replaced). Step 0 is the opening state. A scene’s last step = the highest `data-step` inside it.
- Term chips: `<span class="term" data-term="Prompt" data-gloss="the question we send the AI">prompt</span>`, placed in the step that first explains the term, with its gloss shown beside it in the same step. The Terms tab is generated from these, in A–Z order, each row linking to the scene and step where the chip appears.
- Unrevealed content is `visibility: hidden` (not just transparent), so it cannot be tabbed to or read by a screen reader before its step.

**8.2 State machine.** The whole visible state is a pure function of `(scene, step)`.

- `next()`: if `step < last` then `step + 1`, else next scene at step 0. `prevStep()`: if `step > 0` then `step - 1`, else the previous scene at its last step. `gotoScene(i, "start" | "end")` for arrows, Home, End and overview clicks.
- **Animate only a forward move of exactly one step.** Any other change (back, jump, overview, Home, End) renders the end state of that step instantly. Custom scene code is a `render(step)` function that sets everything idempotently; it never relies on having seen the previous step.
- Expose a read-only `window.__deck = { sceneCount, stepCounts, goto(scene, step), state() }` so a browser test can reach any state. It changes nothing for the audience.

**8.3 Accessibility.**

- A visually hidden `aria-live="polite"` region announces “Scene N of 22: title” on scene change only, not on every step.
- Every SVG illustration has `role="img"` and an `aria-label` that describes its **final** state in one sentence, plus a `<title>`.
- Focus ring: 3 px `--green-900` with a 2 px `--paper` gap, visible on every focusable element, including overview cards and tabs.
- Never carry meaning by colour or dimming alone. Chips that are “left out” also get a text tag. `--alert` always sits beside a label.
- Text contrast at least 4.5:1 (body) and 3:1 (large text); see §5.1 for the gold and green-500 limits. Test every text/background pair you use, and list the lowest in the report.

**8.4 Overview.** Two tabs, **Scenes** and **Terms** (D3), as `role="tablist"`. Focus-trapped; `Esc` closes; focus returns to the stage. Clicking a scene card or a term row jumps there and closes the overview. A card shows number, title, menu line.

**8.5 Source layout.** Hand-readable and in this order: CSS custom properties, base CSS, chrome CSS, per-scene CSS (commented by scene number), markup, then one script: constants (`EXAMPLE` geometry, scene metadata), state, render, input handling, overview, init. No minifier; no build step committed. A throwaway script to inline the logos as base64 is fine, but do not commit it; commit only the HTML. When JavaScript is off, show Scene 1 with every step visible and a short “Enable JavaScript to present this deck” note (add the `js` class to `<html>` from script, and hide steps only under `html.js`).

**8.6 Size.** Two logos once each as `data:image/png;base64,…` in the single lockup element. Total file under 1.5 MB. The expected size is well under 400 KB, \[Inference\] since the logos are 38 KB and 25 KB as PNG.

## 9. Content guardrails and the static test

**9.1 Facts and caveats that must appear.** The panel is most likely to ask about these.

- **S2:** keeps scores *strictly above* 0.6; the shortlist can be empty (no AI call); it has no cap, so its worst case is n calls. (Scenes 11, 12, 16)
- **S3:** picks by count (k = 10), not by cutoff; approximate, may rarely miss a true nearest neighbour; at most 10 calls. (Scenes 13, 16)
- **S4:** folders of 5–10; at most 10 calls; adapted from EraRAG’s size-capped buckets, not a reproduction of it. (Scenes 14, 16)
- **S3/S4 cap caveat:** both cap at 10, so the comparison cannot fully separate folder construction from shortlist size. (Scene 16)
- **Shared decision step:** same AI, same wording, temperature 0, one call per candidate; the AI is never named. (Scene 15)
- **Accuracy is measured against experts**, never against the AI’s opinion; synthetic maps are for cost only. (Scene 17)
- **“None of the studies we reviewed”**, with the structured-but-not-exhaustive note. (Scene 19)
- **RQ4 tests a premise, not EraRAG’s theorem.** (Scenes 20, 21)
- The running example is tagged “illustration — not thesis data” wherever it appears (Scenes 4, 6, 8–11, 15), and every invented number is tagged “made-up numbers, for illustration” (Scenes 7, 10, 11, 16, 18).

**9.2 Forbidden content.** None of these may appear anywhere in the HTML, visible or hidden, in comments or in attributes:

- Chapter 4 values and anything derived from them: `1,713`, `1713`, `8.28`, `0.586`, `0.294`, any per-call duration such as “0.8–0.9 s”, F1/recall/precision values from the results, “TOPSIS”, “Kendall”, “Pareto”, “dominat…”, `G1`/`G2`/`G3` as gates, “effective” as a class, weights, rankings.
- **Chapter 3 pilot and calibration numbers**, which are also measured results: `0.541`, `0.611`, `0.485`, `15.38`, `85.71`, `0.841`, `0.968`, `0.999`. (My made-up illustration numbers do not collide with these: 0.90, 0.70, 0.62, 0.55, 0.30, 0.60, 0.75, 0.67, 0.82, 0.45, 0.18, 1.00, 0.10.)
- Model identity: `DeepSeek`, `deepseek`, `V3`, `V4`, `Flash`.
- Reference-number markers such as `[1]` or `[13]–[21]`.
- The Funk et al. figures: `22 to 50`, `22–50`, `$0.11`, `12.45`.
- The phrases “nobody has ever” and “we prove”.
- Strategy letters (“Strategy A”…“Strategy D”); use S1–S4 only.
- Anything networked: `http://`, `https://`, `<link`, `<script src`, `@import`, `url(http`, `fetch(`, `XMLHttpRequest`. **One exception:** the SVG `xmlns="http://www.w3.org/2000/svg"` attribute, which is a name, not a request. Allow that exact string and nothing else.

**9.3 `tests/test_background_deck_static.py`.** A pytest file that reads the HTML as text and checks, with no browser:

1. Every pattern in §9.2 is absent (case-insensitive where sensible).
2. Exactly 22 `<section class="scene">` elements (or 20 if the §6 fallback was used, then the test says so), each with non-empty `data-title` and `data-teaches`.
3. File size under 1,500,000 bytes; exactly two `data:image/png;base64,` URIs; no other `data:` URI.
4. The required phrases of §9.1 are present (“none of the studies we reviewed”, “strictly above”, “premise”, “illustration”, “made-up numbers”, the S3/S4 cap sentence).
5. Every row of §7 exists as a `data-term`; no `data-gloss` is longer than 16 words.
6. **Term-before-chip lint:** from Scene 3 on, for each term, its first appearance in document order is its chip. Scene 1–2 are exempt (the title words are glossed in Scene 2 itself). Treat the output as a **lint list to resolve or justify in the report**, not a hard failure, because ordinary English words will trip it.
7. The JavaScript (extracted from the `<script>` block) passes `node --check` if `node` is installed; otherwise the test is skipped with a stated reason.

The test must pass under the repo’s normal `pytest`, must not need a browser, and must not touch `results/`.

**9.4 Copy provenance.** Every on-screen sentence that states a fact needs a source. In the report, give a table of scene → sources (pack section, thesis section, or script slide). A sentence with no source in the pack, the thesis (Chapters 1 and 3) or the two scripts is cut, not kept.

## 10. Deliverables, testing, acceptance, reporting

**10.1 Files.**

- **New:** `docs/presentation/background-deck/background-concepts.html`; `tests/test_background_deck_static.py`; `docs/reports/PRES-002-claude-code-background-concepts-deck.md` (follow `docs/reports/TASK-TEMPLATE.md`); `patch/PRES-002-claude-code-background-concepts-deck.patch`.
- **New, if absent:** `docs/prompts/PRES-002-PROMPT.md`, containing this prompt exactly as Luke gave it to you (the repo, not the chat, is the source of truth).
- **Edit, your own rows only, after re-reading each file:** `docs/tasks/status.md` (add the PRES-002 row: `in-progress`, then `needs-review` with a link to your report); `docs/decisions/decision-log.md` (append **\[D-94\]**, below).
- **Do not touch:** `BRIEF.md`, `CONTENT-PACK.md`, `DECK-EXTRACT.md`, the thesis, the scripts, the existing `.pptx`, `scripts/`, `src/`, `results/`, `repositories/`. Record pack corrections by a later decision entry, not by editing the pack (the same practice as \[D-92\]).
- Make **one commit** so `git diff HEAD~1` captures the whole unit of work. Message: `feat(PRES-002): background-concepts HTML deck`.

**10.2 Testing.** Run everything you can and mark the rest **not run** in the report; never claim a check you did not do.

1. `pytest tests/test_background_deck_static.py`, then the full `pytest` to prove no regression.
2. **Browser tests** with headless Chromium (Playwright or whatever is installed; \[Unverified\] whether one is). If none is installed, try a throwaway virtual environment **outside the repo**; if the network blocks it, say so and mark every browser check below as not run. At **1920×1080, 1366×768 and 1280×720**:
   - Open by `file://` with the network switched off. Zero requests, zero console errors.
   - Visit **every scene at every step** (use `window.__deck.goto`). At each: the stage has no scrollbars; no element extends beyond the stage; no text is clipped (`scrollHeight` against `clientHeight` on text boxes).
   - Keyboard only, start to finish: Space through all steps (the count must equal the total number of steps), `ArrowRight`/`ArrowLeft`, `Home`, `End`, `O`, `Esc`, `Backspace`, `Tab` inside the overview (focus must stay trapped), `Esc` returns focus to the stage. A click on an overview card must **not** also advance the deck.
   - Overview: 22 scene cards; the Terms tab lists every chip; clicking a term jumps to its scene and step.
   - Reduced motion (`prefers-reduced-motion: reduce`): after each step `document.getAnimations()` is empty, and steps still advance one click at a time.
   - JavaScript off: Scene 1 shows with the “Enable JavaScript” note and every step visible.
3. **Look at the pictures.** Save a screenshot of each scene’s last step at each resolution into a directory **outside git**, for example `../llm-graph-insertion-complexity-PRES-002-qa/`, and build one contact sheet per resolution. View them yourself, fix what is wrong, and say in the report that you did. Do not commit screenshots.
4. **Contrast.** List every text/background colour pair used and its ratio; report the lowest. Anything under 4.5:1 (body) or 3:1 (large) is fixed, not excused.
5. **What you cannot test:** a real projector, Firefox and Safari behaviour (`cqw` support), and an actual rehearsal. Write a short manual checklist for Luke covering these.

**10.3 Acceptance.** Done means all of BRIEF §9, plus:

- [ ] 22 scenes (or 20 under the §6 fallback), each with a menu title and menu line, in the order of §6.
- [ ] Scene 2 explains the title words in title order; Scene 1 shows only the title card, authors and logos.
- [ ] Every row of the §7 gloss bank is a term chip; the Terms tab lists them all; the five patches are applied; no gloss is over 16 words.
- [ ] Every §9.1 fact is present; nothing from §9.2 appears; the static test passes.
- [ ] Step-back works (D2); arriving by `ArrowLeft` shows the previous scene fully revealed.
- [ ] Animation only on a one-step forward move; every other jump is instant; reduced motion honoured.
- [ ] Every text pair meets contrast; focus ring visible everywhere; no meaning carried by colour alone.
- [ ] File under 1.5 MB, two data URIs, no external reference.
- [ ] Branch, worktree path and base commit reported; nothing merged; worktree left in place.

**10.4 Reserved decision ID: \[D-94\].** One entry recording: the 22-scene plan with R1 (title first) and R2 (every term explained); corrections **C1–C8** to the PRES-001 pack; the departures **D1–D5**, each accepted or changed; the static test as a standing guard. If `D-94` is already used, stop and report; do not renumber. Check with `./scripts/manage-decisions.py check`.

**10.5 Report contents.** Beyond the template: (a) base commit and how you chose it; (b) departures D1–D5, accepted or changed, with reasons; (c) every place you changed APC copy and why; (d) the **coverage map**: each of the 24 questions in CONTENT-PACK §14, plus each term in §7, → the scene and step that answers it; (e) the copy-provenance table (§9.4); (f) the term-before-chip lint list, each item resolved or justified; (g) the step count per scene and the total; (h) the contrast table; (i) screenshot directory path; (j) what was **not run**; (k) the thesis §1.1 “brute-force” wording issue (C3) for Luke.

**10.6 Report back to Luke.** Executive summary, test results, the patch path, `git diff HEAD~1 --stat` (not the full HTML diff), the branch name and worktree path. Do **not** paste the HTML into the chat.

**10.7 If something is missing.** If a fact you need is not in the pack, the thesis (Chapters 1 and 3) or the two scripts, do not invent it: leave the line out and list it in the report, or ask Luke for the thesis section.
