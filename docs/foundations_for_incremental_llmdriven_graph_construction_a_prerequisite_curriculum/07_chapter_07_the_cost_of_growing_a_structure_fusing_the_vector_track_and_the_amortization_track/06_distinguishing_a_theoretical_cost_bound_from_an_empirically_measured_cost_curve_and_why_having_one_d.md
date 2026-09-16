## Distinguishing a Theoretical Cost Bound from an Empirically Measured Cost Curve, and Why Having One Does Not Automatically Give You the Other

### Two Different Kinds of Claims, One Familiar Analogy

Anyone who has tuned a slow SQL query already understands this distinction, even without the vocabulary for it. A query planner's `EXPLAIN` output gives you a *predicted* cost: an estimate derived from a cost model, based on table statistics, index structures, and assumptions about selectivity. `EXPLAIN ANALYZE`, by contrast, actually runs the query and reports what happened: real elapsed time, real rows scanned, real buffer hits and misses. The two numbers are related — the planner's model was built to approximate reality — but they are not the same claim, and a mismatch between them is a routine, expected, diagnostically useful event rather than a sign that something is broken.

A theoretical cost bound is the `EXPLAIN` side of algorithm analysis: a prediction derived from a mathematical model of computation. An empirically measured cost curve is the `EXPLAIN ANALYZE` side: what you get when you actually run the code and record what happened. This item is about the gap between them — why a correct bound does not hand you an accurate curve for free, and why a clean-looking curve does not hand you a proven bound for free. Both directions of this gap matter directly to any argument about how an insertion strategy's cost behaves as a structure scales, which is the exact question this chapter is building toward.

### What a Theoretical Cost Bound Actually Claims

A cost bound is a statement about growth rate, not about wall-clock seconds. When you write that an operation costs $O(f(n))$, you are claiming that, past some threshold and up to a hidden constant multiplier, the cost grows no faster than $f(n)$ as $n$ grows without bound. Three things are baked into that claim, and each one is a place where the bound can quietly stop describing reality:

**It hides constants.** $O(n)$ and $O(1000n)$ are the same asymptotic class. If your actual constant factor is large, an algorithm with a "better" asymptotic bound can still be slower at every $n$ you will ever run.

**It picks a computation model.** The standard model used for these bounds is the RAM model, which assumes every basic operation — an array read, a pointer dereference, an arithmetic step — costs a fixed unit of time regardless of where the data lives. Real hardware does not work this way; a value sitting in L1 cache and a value sitting in main memory cost wildly different amounts of time to read, and the RAM model has no vocabulary for that difference at all.

**It picks a cost regime.** A bound can describe the worst possible input (worst-case), the average over some assumed input distribution (average-case), or the average over any sequence of operations even if individual operations spike (amortized). Recall from amortized analysis that a worst-case-per-operation bound and an amortized-per-operation bound answer genuinely different questions: worst-case bounds every single operation individually, while amortized analysis bounds the *total* cost of a sequence of operations divided by the number of operations, allowing some individual operations to be expensive as long as the sequence as a whole pays for it. A structure can have a bad worst-case-per-operation bound and an excellent amortized-per-operation bound simultaneously, and both statements are true at once — they are just answering different questions.

The canonical illustration is a dynamic array that doubles its backing capacity whenever it fills up. A single insertion that triggers a resize costs $O(n)$, because every existing element has to be copied into the new backing array. So the honest worst-case-per-operation bound is $O(n)$. But because each doubling roughly quadruples the number of insertions you get before the next doubling, the total copying work across any sequence of $n$ insertions sums to $O(n)$, which spread evenly across those $n$ insertions gives an amortized cost of $O(1)$ per insertion. Both bounds are correct. They are correct answers to different questions, and a curriculum or a paper that only quotes one of them without saying which regime it belongs to has told you less than it appears to.

### What an Empirically Measured Cost Curve Actually Measures

An empirical cost curve is produced by instrumenting real code, running it on real data, on real hardware, and recording something concrete per operation — wall-clock time, CPU cycles, number of comparisons, number of memory accesses — then plotting that quantity against $n$, the size of the structure at the time of the operation.

Everything the RAM model abstracted away is fully present here. Cache locality matters: whether the data your operation touches happens to already be sitting in a fast cache line or has to be fetched from main memory changes the real cost by an order of magnitude, and no asymptotic notation captures that. Memory allocator behavior matters: a language runtime's allocator might reuse freed memory cheaply in one run and have to request a fresh page from the operating system in another. Background system noise matters: another process stealing CPU time, an operating system scheduling quantum expiring mid-operation, a garbage collector pausing execution — all of these show up in a measured curve and none of them appear anywhere in a Big-O statement. And critically, the *actual distribution of the input data you tested* matters: a measured curve only tells you about the inputs you actually ran, not about every input the algorithm could ever encounter.

None of this makes empirical measurement inferior to theory — it makes it a different kind of evidence, answering a different kind of question: not "what does this algorithm's cost do in principle, in the limit, under this cost model," but "what did this specific implementation actually do, on this specific hardware, for these specific inputs, up to the specific scale I tested."

### Direction One: Why a Correct Bound Does Not Guarantee a Well-Behaved Curve

Suppose you have derived — correctly, honestly, with no error in the analysis — that an operation is amortized $O(1)$. There are still several ways the resulting empirical curve can look nothing like a flat, boring, constant-cost line.

**The spikes are real and individually visible.** Amortized analysis is a claim about the *sequence total*, not about any individual operation. If you plot per-operation cost against operation number for a doubling dynamic array, you will not see a flat line at all — you will see a mostly-flat baseline punctuated by sharp spikes exactly at the doubling points, where a single insertion pays for copying the entire array. The amortized bound is a true statement about the average, and it is simultaneously true that the curve, examined point by point, is deeply non-flat. A reader who expects "amortized $O(1)$" to mean "every point on the curve is small" has misread what the bound claims.

**The constants can dominate at practical scale.** An amortized $O(1)$ operation with a large hidden constant — say, one that always touches a moderately expensive hash function or acquires a lock — can be measurably slower in absolute terms than a worse-looking $O(\log n)$ operation with a tiny constant, for every $n$ that will ever actually occur in your experiments. The bound correctly describes the shape of growth; it says nothing about where the curve sits vertically.

**The RAM model's blind spot toward memory hierarchy can invert the expected ordering.** Two operations that the RAM model scores as equally cheap — both $O(1)$ — can differ by two orders of magnitude in real time if one touches data that is cache-resident and the other causes a cache miss or a page fault. This is not a violation of the theoretical bound; the bound was never making a claim about cache behavior in the first place, because the RAM model has no concept of a cache.

**A worked table makes the spike behavior concrete.** Consider a dynamic array starting at capacity 1, doubling whenever full, where a "unit" of cost is one element write. The table below traces per-insertion cost, cumulative cost, and the running amortized average across the first sixteen insertions:

| Insertion # | Array size before | Resize triggered? | Cost this insertion | Cumulative cost | Cumulative cost ÷ n |
| --- | --- | --- | --- | --- | --- |
| 1 | 0 → cap 1 | yes (alloc) | 1 | 1 | 1.00 |
| 2 | 1 → cap 2 | yes (copy 1) | 2 | 3 | 1.50 |
| 3 | 2 → cap 4 | yes (copy 2) | 3 | 6 | 2.00 |
| 4 | 3, cap 4 | no | 1 | 7 | 1.75 |
| 5 | 4 → cap 8 | yes (copy 4) | 5 | 12 | 2.40 |
| 6–8 | fits in cap 8 | no | 1 each | 15 | 1.88 |
| 9 | 8 → cap 16 | yes (copy 8) | 9 | 24 | 2.67 |
| 10–16 | fits in cap 16 | no | 1 each | 31 | 1.94 |

Notice two things at once. First, the per-insertion cost column is exactly the jagged, spiky picture described above — nothing about it looks like a constant. Second, the running amortized average in the last column, while it wobbles, never grows without bound and keeps settling back down toward a small constant as $n$ increases; this is the amortized $O(1)$ bound doing exactly what it promised, but only visible in the *aggregate* column, never in the raw per-operation column. If your empirical instrumentation only logged the per-operation column and someone concluded "this contradicts the amortized bound," they would be reading the wrong column.

### Direction Two: Why a Clean Empirical Curve Does Not Establish a Bound

Now flip the direction. Suppose you run an implementation, measure its per-operation cost across a wide range of $n$, and the resulting curve looks beautifully sub-linear — smooth, flat, exactly the shape you hoped for. This is real, useful evidence, but it does not by itself constitute a proof of any asymptotic bound, for reasons that mirror the first direction.

**A measured curve only covers the range you tested.** An asymptotic bound is a claim about behavior as $n \to \infty$. If you measured up to $n = 10^5$, you have evidence about $n$ up to $10^5$, not a guarantee about $n = 10^9$. Many real cost curves look flat right up until they hit a resource boundary — available RAM, cache size, an index structure's internal degree limit — and then bend sharply. A curve that looks $O(\log n)$ over your tested range can be doing something else entirely once it crosses a boundary your experiment never reached. Extrapolating an asymptotic claim from a finite measured range is a genuinely different act of reasoning from deriving the bound analytically, and it carries genuine risk of being wrong precisely where it matters most.

**A measured curve reflects the inputs you actually fed it, not the worst case.** A theoretical worst-case bound is deliberately pessimistic: it accounts for the input an adversary would choose to make things as bad as possible. An empirical curve measured on typical, "well-behaved" data can look excellent while a worst-case bound for the same algorithm remains poor, simply because your test data never exercised the pathological case. This gap is not a flaw in the measurement — it is telling you something true about typical performance — but it is a different claim from "this algorithm cannot be made to behave badly," and conflating the two is a common source of unpleasant surprises when a system meets a new distribution of real-world data.

**Implementation-specific overhead can be mistaken for algorithm-intrinsic cost, or vice versa.** A measured curve is produced by a specific implementation, in a specific language, using a specific library's memory layout. A poorly optimized implementation of an algorithm with an excellent theoretical bound can produce an empirical curve that looks mediocre, and a highly optimized implementation of an algorithm with a mediocre theoretical bound can produce an empirical curve that looks excellent, at least over the range tested. The curve alone cannot tell you which situation you are in; you need the theoretical analysis as a separate cross-check to know what to attribute the measured shape to.

**This gap is not hypothetical for the approximate nearest-neighbor structures central to this chapter's neighbor topics.** Recall from the discussion of approximate nearest-neighbor search that HNSW (Hierarchical Navigable Small World) builds a multi-layer graph and answers queries by greedily routing through it layer by layer. In practice, published and reproduced measurements consistently show query cost scaling roughly poly-logarithmically with the number of stored vectors, which is the empirical basis for calling it sub-linear. [Unverified] Whether this empirically observed scaling is matched by a tight, general worst-case theoretical bound comparable to the clean guarantee available for, say, a balanced binary search tree is a genuinely open and more delicate question in the literature: the construction relies on heuristics — bounded node degree $M$, a probabilistic layer assignment, and a greedy search procedure — whose favorable behavior is argued for specific, structured input distributions (data that is, informally, "navigable") rather than proven for arbitrary adversarial input. That is precisely an instance of this item's second direction: an excellent, reproducible empirical curve exists, but it does not by itself constitute a theorem that no input distribution could make behave worse, and papers in this area are careful to keep those two kinds of claims separate rather than treating a strong benchmark as if it were a closed-form proof.

### Illustration: Bound Versus Curve, Side by Side

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 420">
<text x="350" y="24" text-anchor="middle" font-size="15" font-weight="bold" fill="#222">Amortized Bound vs. Worst-Case Bound vs. Empirical Per-Operation Cost (svg_diagram)</text>
<line x1="60" y1="350" x2="660" y2="350" stroke="#333" stroke-width="2" />
<line x1="60" y1="350" x2="60" y2="50" stroke="#333" stroke-width="2" />
<text x="360" y="390" text-anchor="middle" font-size="13" fill="#333">insertion number (n)</text>
<text x="25" y="200" text-anchor="middle" font-size="13" fill="#333" transform="rotate(-90 25 200)">cost of this operation</text>
<line x1="60" y1="70" x2="660" y2="70" stroke="#c0392b" stroke-width="2" stroke-dasharray="8,6" />
<text x="480" y="62" font-size="12" fill="#c0392b">worst-case per-operation bound: O(n) — reached only at resize points</text>
<line x1="60" y1="308" x2="660" y2="308" stroke="#1a6fb0" stroke-width="2" stroke-dasharray="8,6" />
<text x="470" y="325" font-size="12" fill="#1a6fb0">amortized per-operation bound: O(1) — describes the average, not each point</text>

<polyline points="60,310 90,312 120,70 150,306 180,300 200,70 230,304 260,298 300,70 340,302 380,296 420,70 460,300 500,298 540,70 580,302 620,296 640,70 660,300" fill="none" stroke="`#2c8c4a`" stroke-width="2.5" />

<text x="180" y="130" font-size="12" fill="`#2c8c4a`" font-weight="bold">empirically measured cost (spikes at each doubling)</text>

<circle cx="120" cy="70" r="4" fill="#2c8c4a" />
<circle cx="200" cy="70" r="4" fill="#2c8c4a" />
<circle cx="300" cy="70" r="4" fill="#2c8c4a" />
<circle cx="420" cy="70" r="4" fill="#2c8c4a" />
<circle cx="540" cy="70" r="4" fill="#2c8c4a" />
<circle cx="640" cy="70" r="4" fill="#2c8c4a" />
</svg>

Neither dashed line is "the curve." The worst-case bound (top) is only touched at the resize points and would grossly overstate typical cost if mistaken for the norm. The amortized bound (bottom) is never actually realized at any single point on the green curve, yet it correctly describes where the sequence average settles. The measured curve is the only line in the picture that actually happened; the two dashed lines are two different, both-true theoretical summaries of it, each answering a different question.

### Applying This to the Insertion-Cost Curves Central to This Chapter

This distinction is not academic decoration for the specific comparisons this chapter is built around. Recall that brute-force nearest-neighbor search, as established when exact search was shown not to scale, has a cost model with essentially no hidden structure to it: every insertion compares the new item against all $n$ existing items, so the theoretical bound is a tight $\Theta(n)$, and because there is no data-dependent branching, resizing, or skipped work, the empirical curve for brute-force insertion tends to track that straight line closely — theory and measurement agree almost by construction, because the algorithm has nothing for hardware or data distribution to exploit or ambush. Embedding-threshold insertion, which decides where to attach a new node by comparing its embedding against existing nodes and testing against a similarity threshold, is still performing that same linear scan under the hood; the added test-against-threshold step changes the constant factor slightly but not the asymptotic shape, so it inherits the same close agreement between bound and curve.

An ANN-index-based insertion strategy is the case where this item's caution earns its keep. The theoretical story for the index's build and query cost is looser and more assumption-laden than a straightforward $\Theta(n)$ scan, resting on heuristic degree bounds and distributional assumptions about "navigability" rather than a clean worst-case guarantee. That means the empirical curve is not merely a confirmation of an already-airtight bound — it is carrying real evidentiary weight of its own, filling in exactly the gap that the theory leaves open. Anyone building or evaluating an ANN-index insertion strategy needs both pieces and needs to keep straight which one is doing which job: the theory tells you what shape to expect and why, under stated assumptions; the measurement tells you whether those assumptions actually held for your data, at the scales you tested, on your hardware — and neither one is a substitute for the other.

### How to Use a Bound and a Curve Correctly, Together

The productive relationship between the two is neither "trust the theory and skip measuring" nor "just measure and skip the theory," but a specific back-and-forth. Derive or recall the theoretical bound first, because it tells you what *shape* of curve to expect — flat, logarithmic, linear — and under what regime (worst-case, amortized, average-case) that shape is supposed to hold, which tells you what kind of empirical plot would even be a fair test of it. Then measure, because the measurement tells you whether the real constant factor is small enough to matter, whether the hardware's memory hierarchy is being kind or unkind to this particular implementation, and whether your actual data resembles the input distribution the theory assumed closely enough for the bound's guarantees to be relevant at all. When the two disagree — when a curve is much worse than its bound predicted, or much better — that disagreement is not a failure of either tool; it is a diagnostic signal pointing at exactly the kind of hidden factor this item has catalogued: a dominant constant, a cache effect, a worst-case-versus-typical-case mismatch, or a measurement range too narrow to see the asymptote. Reading that signal correctly requires knowing, precisely, which claim each side was making in the first place.

**Related Topics**

- Reading and correctly interpreting a formally stated amortized-cost theorem
- The RAM model of computation and its blind spots relative to real memory hierarchies
- Worst-case versus average-case versus amortized cost as three distinct claims
- Why HNSW's favorable empirical scaling rests on distributional assumptions rather than a universal worst-case guarantee
- Designing an experiment that can actually distinguish two competing asymptotic shapes (avoiding a measurement range too narrow to tell them apart)
- Micro-benchmarking pitfalls: cache warming, JIT warm-up, garbage collection pauses, and system noise as confounds in a cost curve