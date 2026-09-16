## Phase 0 — Design Lock & Adviser Approval (pre-code, you personally, ~1–2 weeks)

**What the design doc must contain:**

- The reframed research question (insertion-narrowing strategy comparison, as scoped in the handoff)
- The four strategies, named and justified, each tied to a specific citation (Funk et al. for brute-force's failure mode, iText2KG for the embedding-threshold baseline, HNSW/FAISS literature for the ANN strategy, EraRAG for the bucket-capped strategy)
- **EraRAG's Theorem 4 stated as the anchor** — this is the single most important sentence in the whole document, because it's what converts "we compared four things" into "we empirically tested whether a specific, named, existing theoretical claim holds." Without this framing, the adviser has no way to distinguish this from a class project.
- The three dependent variables (wall-clock time, LLM call count, placement accuracy) and _why_ three, not one — specifically the argument that speed alone would be a weak result, and accuracy alone ignores the actual research question
- The gold-standard decision, already made (reuse existing structured data), with the _specific_ corpus candidates named (Metacademy, DSA, a Wikipedia/WordNet/DBpedia subset) even if the final pick isn't locked yet — an adviser will want to see that this was a deliberate choice, not a placeholder
- The log-spaced n sweep (50, 100, 200, 500, 1000, 2000+) with the cost-bounding rationale stated explicitly
- One paragraph naming the two failure outcomes as _both_ being defensible results (convergence vs. divergence across strategies) — this preempts the "what if your results are boring" objection before the adviser raises it

**Why this has to be a standalone doc and not a slide deck or verbal pitch:** you have a 4-person team waiting on this gate. If the adviser wants a change, you want that change captured in one place that becomes the literal spec for Phase 1 — not scattered across meeting notes that only you have. This document _is_ Phase 1's requirements input.

**Exit criterion:** adviser has seen and approved (or amended) this design. Nothing in Phase 1 starts until this happens, because Phase 1 output is expensive to redo and directly depends on what's locked here.

---

## Phase 1 — Shared Infrastructure & Interface Contract (you, lead-authored; ~1–2 weeks, can overlap tail end of Phase 0 for scaffolding only)

This is the phase I flagged as needing to be yours specifically, not delegated, because it's the contract everyone else's narrower work depends on. If this interface is wrong or ambiguous, Phase 2's four parallel tracks will diverge and Phase 3 integration will cost more than building it right the first time would have.

**What must exist before any strategy code is written:**

1. **The strategy interface itself.** A fixed contract — something like: every strategy is a module/class that receives (a) the existing graph state at whatever size it's currently at, and (b) a new node to insert, and must return (a) the decided placement/edges, (b) the wall-clock time taken, and (c) the LLM call count consumed. This needs to be locked as an actual interface (function signature, expected data shapes) before four people start building against it independently.
    
2. **The graph representation itself.** One canonical in-memory (or lightly persisted) representation of "a graph at size n" that every strategy reads and writes. If each strategy invents its own graph representation, comparing them later is not a small refactor, it's a rewrite.
    
3. **The gold-standard corpus, loaded and normalized.** This is where the Phase 0 decision becomes real: pulling the actual chosen dataset (Metacademy/DSA/Wikipedia-subset) into whatever normalized format the harness expects, so "placement accuracy" has something concrete to check against. This is genuinely shared work — doing it once, correctly, and having all four strategies read from the same normalized ground truth, is what makes the accuracy comparison meaningful at all. Doing it four times independently risks four slightly different notions of ground truth, which would quietly invalidate any accuracy comparison.
    
4. **The measurement harness.** The actual sweep runner: given a strategy module conforming to the interface, run it at n=50, 100, 200, 500, 1000, 2000+, log wall-clock/call-count/accuracy at each checkpoint, and emit results in one consistent format (e.g., one row per (strategy, n) pair). This is what turns four independent strategy implementations into one comparable dataset.
    
5. **A trivial "null strategy"** (e.g., always attach the new node to a random existing node) built and run through the full harness _first_, before any real strategy exists. This is the single highest-leverage thing in this phase: it proves the harness itself works end-to-end — corpus loads, sweep runs across all six sizes, metrics get logged, output format is usable — without the confound of also debugging a real strategy's logic at the same time. This directly operationalizes the handoff's own advice to "validate the full harness end-to-end at small scale before adding strategies 3 and 4," just widened to "before adding any real strategy at all."
    

**Why this order (interface → representation → corpus → harness → null-strategy smoke test) and not some other order:** each item depends on the one before it. You can't build the harness without a fixed interface to call. You can't run a meaningful null-strategy test without the corpus already loaded and normalized. Reordering this risks building something on a shifting foundation.

**Handoff to Claude Code here:** since you're using an agentic coding tool, this phase is where you'd hand it a _tightly scoped_ spec — "implement this exact interface, this exact graph representation, this exact corpus loader, this exact harness, then implement and run the null strategy through it" — rather than an open-ended "build the experiment infrastructure" prompt. The narrower and more literal the spec, the less drift between what you designed and what gets built.

**Exit criterion:** the null strategy runs cleanly through all six graph sizes and produces a results file in the agreed format. This is the point where Phase 2 can safely start, because the four team members are now building against something proven to work, not something theoretical.

---

## Phase 2 — Four Parallel Strategy Tracks (one person each, ~2–4 weeks, timeboxed loosely per strategy complexity)

Each team member takes exactly one strategy and implements it against the fixed interface from Phase 1. Because the interface is already locked, this is genuinely parallelizable — no team member's work blocks another's during this phase.

**Suggested implementation order within this phase, if sequencing help is wanted even though people work in parallel:**

- **Strategy 1 (brute-force) and Strategy 2 (embedding-threshold)** are the cheapest to implement correctly — brute-force has no real design decisions (compare against everything, no cleverness required), and embedding-threshold just adds one filtering step on top of it. These can realistically be done by the two least experienced team members, matching your "narrower, more structured tasks" framing directly — brute-force in particular is close to unable to be gotten wrong.
- **Strategy 3 (ANN-index)** requires understanding a real library (FAISS or similar) and its indexing/query API — moderate complexity, a reasonable middle assignment.
- **Strategy 4 (bucket-capped, EraRAG-style)** is the most conceptually involved, since it's implementing a bounded-size structure with split/merge logic, not just a filter or a library call — this is the one most worth you personally reviewing closely or pairing on, since it's also the strategy that most directly operationalizes the thesis's actual theoretical anchor.

Each strategy module, in isolation, should be validated against the _same_ small-n smoke test the null strategy proved out in Phase 1 — n=50 and n=100 only, at this stage. Do not let anyone jump straight to the full sweep with an unvalidated strategy; that's how a subtle bug burns real LLM API budget across six graph sizes before anyone notices.

**Your role in this phase specifically (as lead/integrator):** not implementing a fifth thing in parallel, but reviewing each incoming strategy module against the Phase 1 interface contract as it lands — catching interface drift early, before four modules have each quietly diverged in some small incompatible way.

**Exit criterion:** all four strategies pass the n=50/n=100 smoke test independently, each producing well-formed output through the shared harness.

---

## Phase 3 — Integration & the Real Sweep (you, as integrator, ~1–2 weeks)

This is where the four independently-built strategies get run together, for real, across the full n=50→2000+ sweep, through the one shared harness.

**Sequence:**

1. Merge all four strategy modules into one codebase (this should be low-friction if Phase 1's interface was actually held to — this is the direct payoff of front-loading that contract).
2. Run the full sweep for all four strategies across all six graph sizes.
3. **Budget-check before the largest sizes fire**, especially for brute-force and embedding-threshold, since those are the two strategies whose LLM call count scales worst with n — this is the practical reason the handoff called out cost-bounding explicitly. Consider running the two cheap strategies (3, 4) to full n first, and the two expensive ones (1, 2) last, so if a budget problem surfaces, it surfaces before the expensive runs rather than after.
4. Collect the full results table: one row per (strategy, n) with wall-clock, call count, and placement accuracy.

**Exit criterion:** one complete, clean results table covering all 4 strategies × 6 sizes × 3 metrics, with no missing cells and no known-bad runs silently included.

---

## Phase 4 — Analysis & Writeup

- Plot insertion cost (wall-clock and call count separately — the handoff's own point that separating these tells you "LLM is slow" from "algorithm makes too many calls") against n, one line per strategy, log-scale n.
- Plot placement accuracy against n, same structure.
- **Directly compare the bucket-capped strategy's empirical curve against EraRAG's Theorem 4's predicted shape** — this is the actual thesis contribution landing: does the measured curve look like what the theorem promises, or does it diverge, and either answer is a real finding.
- Write the results section around whichever outcome actually occurred (convergence or divergence across strategies), using the framing already locked in Phase 0 so the writeup isn't scrambling to justify results after the fact.

---

**One structural thing worth naming plainly, since it's a real risk with a 4-person team and no hard deadline:** the absence of a deadline is exactly the condition under which Phase 1 (shared infrastructure) tends to sprawl, because "let's get the interface perfect" has no natural forcing function to stop. I'd treat the null-strategy-passes-the-full-sweep exit criterion in Phase 1 as a hard internal deadline even without an external one — it's a concrete, binary, unambiguous "done," and it's the one gate that most directly unblocks four other people's work.