# Thesis Orientation: Comparing How LLMs Decide Where New Information Goes in a Growing Graph

## The one-sentence version

We're testing which of four different methods for "should this new node connect here?" actually works best as an LLM-built knowledge graph gets bigger — measuring speed, API cost, and accuracy, not just picking one method and assuming it's fine.

## The problem, explained plainly

Imagine an LLM is building a graph of concepts one at a time — like it reads a document, pulls out a new topic, and has to decide: does this connect to anything already in the graph? Where?

The obvious way to do this is brute force: compare the new thing against everything already there. That works fine when the graph has 20 nodes. It falls apart when the graph has 2,000 nodes, because now every single insertion requires (in the worst case) comparing against all 2,000 existing things, and if any of those comparisons involve calling an LLM, that gets slow and expensive fast.

People have proposed smarter ways to narrow down what needs comparing before involving the LLM at all — filter by embedding similarity, use approximate nearest-neighbor search, use bucket/tree structures that only ever compare against nearby buckets. Each of these has been used in some published system. What's never been done is putting all of them side by side and actually measuring: as the graph grows, which one is fastest, which one costs the fewest LLM calls, and — critically — which one still gets the *placement right*, because speed doesn't matter if the graph ends up wrong.

That's the thesis.

## The four things we're comparing

1. **Brute-force** — LLM checks the new node against every existing node. This is the "obviously doesn't scale" baseline everyone assumes is bad — we're going to actually prove it, with numbers, instead of assuming it.
2. **Embedding-threshold narrowing** — filter candidates first using cosine similarity (a fixed cutoff, e.g. 0.6), then only ask the LLM to decide among the survivors. This is roughly what current published systems do (iText2KG uses this). Worth noting: even this is still technically checking against the *whole* graph for the similarity filter — it's just cheaper per-check, not fundamentally different in scaling. That distinction hasn't really been called out clearly in the literature, so it's part of what we're contributing.
3. **ANN index (approximate nearest-neighbor, e.g. FAISS/HNSW)** — instead of scanning everything, use a proper index structure to sub-linearly retrieve only the top-k most-similar existing nodes, then have the LLM decide among just those.
4. **Bucket-capped / tree structure** — nodes get organized into size-bounded buckets or a tree, so a new node only ever gets compared within its local bucket, never the whole graph. There's actually a real math proof behind this approach in a 2025 paper (EraRAG) — but that paper never tested it against a growing graph size empirically, it only proved it on paper. We're the ones actually running that experiment.

## What we measure, at each graph size

We'll build the graph up in stages (roughly 50 → 100 → 200 → 500 → 1000 → 2000+ nodes) and at each stage, for each strategy, record:

- **Wall-clock time** per insertion
- **Number of LLM API calls** per insertion (this separates "the LLM itself is slow" from "our algorithm is calling it too many times")
- **Placement accuracy** — did the new node actually connect to where it should have, compared against a known-correct answer

## Why this isn't a "well, obviously" result waiting to happen

If we only tested one strategy, the risk is a boring result nobody can act on. Testing all four against each other means either outcome is interesting: if they all converge to similar performance despite very different theoretical guarantees, that itself is a finding. If they diverge the way theory predicts, we get an actual evidence-backed recommendation for which strategy to use and when. There's no version of this where the comparison itself fails to produce something worth writing up.

## Suggested work breakdown (4 people — rearrange freely)

- **Person A — Harness + Strategy 1 & 2:** Build the core insertion pipeline/test harness everyone else plugs into. Implement brute-force and embedding-threshold strategies (the two simplest, get real data flowing first).
- **Person B — Strategy 3 (ANN index):** Implement the FAISS/HNSW-based narrowing strategy. Likely the most "systems engineering"-heavy piece.
- **Person C — Strategy 4 (bucket-capped/EraRAG-style):** Implement the bucket/tree-based strategy. This is the one with a real theorem behind it (EraRAG, Theorem 4) — worth reading that paper closely, since it's our main anchor citation.
- **Person D — Corpus, ground truth, and evaluation:** Decide and prepare the dataset we test against (options: reuse an existing structured hierarchy with known-correct answers — like Wikipedia categories, WordNet, or the graphs released by the ACE paper — or hand-build a small labeled set ourselves). Own the placement-accuracy measurement and the eventual results write-up/figures.

## Rough sequencing

1. Lock the corpus/ground-truth decision first — it shapes what "correct placement" even means for everyone else.
2. Get strategies 1 and 2 running end-to-end at small scale (n=50, 100) to validate the whole harness works before the harder strategies (3, 4) get built on top of it.
3. Add strategies 3 and 4 once the harness is proven.
4. Run the full size sweep, collect all three metrics across all four strategies, analyze and write up.

## Key thing to keep in mind

This is a pure computer-science/algorithms contribution — no education-domain framing needed, even though a couple of the source papers come from educational-graph research. If we want to bring in an application angle later that's fine, but it's not required for the thesis to be complete or defensible.