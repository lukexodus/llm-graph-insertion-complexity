## Why HNSW Search Is Sub-Linear in the Number of Candidates, and What That Scaling Claim Does and Does Not Guarantee

### An Analogy from Systems You Already Know

Think about how a routing table works in a large hierarchical network (BGP-style inter-domain routing, or even just how a B+-tree index scales with table size). A router doesn't need a distinct entry for every possible destination host on the internet — it needs enough hierarchical structure (network prefixes, autonomous system boundaries) that the number of hops a packet takes to its destination grows far more slowly than the number of hosts on the internet does. Doubling the number of hosts in the world does not double the number of router hops a typical packet needs; it might add one more hop, if that. That property — where a **useful quantity grows dramatically while the cost of operating on it grows only modestly** — is the general shape of "sub-linear scaling," and it is the same shape a B+-tree index gives a database: doubling the number of rows in a table doesn't double the number of page reads a lookup needs, it adds roughly one more level to the tree.

HNSW is built to exhibit exactly this shape for nearest-neighbor search: the claim is that as the number of stored vectors $n$ grows, the number of distance comparisons a query needs grows much more slowly than $n$ itself.

### Defining "Sub-Linear" Precisely

A cost function $T(n)$ is **sub-linear** if $T(n)/n \to 0$ as $n \to \infty$ — informally, doubling $n$ does not double (or even come close to doubling) the cost. $O(\log n)$, $O(\sqrt n)$, and $O(n^{0.1})$ are all sub-linear; $O(n)$ and $O(n \log n)$ are not. Recall that brute-force linear scan — the honest baseline for exact nearest-neighbor search — has cost model $T(n) = c \cdot n$: every query touches every stored vector, so cost is exactly proportional to $n$, not sub-linear at all. Sub-linear scaling is the entire reason approximate methods like HNSW exist rather than simply optimizing the constant $c$ in the brute-force scan.

### Where HNSW's Sub-Linear Claim Comes From

Recall that an HNSW index's layer count grows with the exponentially-decaying height-assignment process, producing roughly $O(\log n)$ layers total (the same shape as a skip list's level count, since both come from the identical style of geometric/exponential decay). Recall also that a full query descends this stack top-down: a cheap, single-candidate greedy search at each of the sparse upper layers, followed by one wider search at the dense bottom layer.

The claimed cost model composes these two facts:

$$T_{\text{HNSW}}(n) \approx \underbrace{O(\log n)}_{\text{number of layers descended}} \times \underbrace{O(M \cdot ef)}_{\text{work done per layer}}$$

The key structural fact making this sub-linear is that the *per-layer* work — bounded by the graph degree $M$ (how many neighbors each node connects to) and the candidate-list width $ef$ — does **not** depend on $n$ at all. $M$ and $ef$ are fixed configuration constants chosen by whoever builds the index, not quantities that grow as more vectors are inserted. If per-layer cost is a constant independent of $n$, and the number of layers grows only as $O(\log n)$, the product is $O(\log n)$ overall — sub-linear, in the same asymptotic family as a B-tree lookup or a skip list search.

### Worked Comparison: The Growth Curves Side by Side

Take $c = 1$ comparison-cost unit per candidate examined, $M = 16$, $ef = 50$ (so roughly $M \cdot ef \approx 800$ comparisons per layer, as a rough upper-bound stand-in — real per-layer cost is typically much lower in practice because most candidates get pruned early, but this keeps the arithmetic conservative and simple):

| $n$ (vectors) | Brute-force: $T(n) = n$ | HNSW layers $\approx \log_{16}(n)$ | HNSW: $\approx 800 \times$ layers |
| --- | --- | --- | --- |
| $1{,}000$ | $1{,}000$ | $\approx 2.5$ | $\approx 2{,}000$ |
| $100{,}000$ | $100{,}000$ | $\approx 4.2$ | $\approx 3{,}360$ |
| $10{,}000{,}000$ | $10{,}000{,}000$ | $\approx 5.8$ | $\approx 4{,}640$ |
| $1{,}000{,}000{,}000$ | $1{,}000{,}000{,}000$ | $\approx 7.5$ | $\approx 6{,}000$ |

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 400" font-family="monospace" font-size="13">
<text x="380" y="25" text-anchor="middle" font-size="16" font-weight="bold">Linear vs. Sub-Linear Query Cost Growth (svg_diagram)</text>
<line x1="80" y1="340" x2="720" y2="340" stroke="#1f2937" stroke-width="2" />
<line x1="80" y1="340" x2="80" y2="60" stroke="#1f2937" stroke-width="2" />
<text x="400" y="375" text-anchor="middle">n (number of stored vectors, log-scale intuition) →</text>
<text x="30" y="200" text-anchor="middle" transform="rotate(-90 30 200)">query cost (comparisons)</text>
<polyline points="90,335 200,300 320,240 440,160 560,90 700,65" fill="none" stroke="#dc2626" stroke-width="3" />
<text x="620" y="55" fill="#dc2626" font-weight="bold">brute-force: O(n)</text>
<polyline points="90,335 200,325 320,315 440,308 560,302 700,297" fill="none" stroke="#16a34a" stroke-width="3" />
<text x="500" y="290" fill="#16a34a" font-weight="bold">HNSW: O(log n)</text>
<circle cx="90" cy="335" r="4" fill="#4b5563" />
<circle cx="700" cy="65" r="4" fill="#dc2626" />
<circle cx="700" cy="297" r="4" fill="#16a34a" />
</svg>

At $n=1{,}000$, HNSW is already doing *more* raw comparison work than brute force in this deliberately conservative estimate ($2{,}000 > 1{,}000$) — the crossover point where the sub-linear curve actually beats the linear one only appears once $n$ is large enough. This is worth sitting with: sub-linear scaling is a statement about the *slope* of the growth curve, not a promise that the sub-linear method is cheaper at every $n$. For small datasets, the constant overhead of graph traversal, layer bookkeeping, and cache-unfriendly pointer-chasing can make brute force genuinely faster in wall-clock terms — the asymptotic advantage only compounds once $n$ is large enough for the linear curve to overtake the logarithmic one, which is exactly what the diverging curves above show happening as $n$ increases further to the right.

### What the Scaling Claim Does Guarantee

- **The number of layers a query descends grows logarithmically in expectation**, as a direct consequence of the exponential-decay height-assignment rule — this part of the argument is mechanical and follows the same well-understood shape as a skip list's expected level count.
- **Per-layer work is bounded by fixed configuration constants ($M$, $ef$), independent of $n$** — this is true by construction, since nothing in the algorithm makes $M$ or $ef$ grow automatically as more vectors are inserted.
- Composing those two facts gives a genuine, structurally-grounded argument that query cost grows much more slowly than $n$ — this is not a vague marketing claim, it follows directly from how the index is built.

### What the Scaling Claim Does Not Guarantee

**It is not a tight, worst-case theorem the way binary search's $O(\log n)$ bound is.** Recall that skip lists have a specific, well-established probabilistic proof technique (backward analysis over the independent coin-flip process) that yields a rigorous expected-cost bound. [Unverified] HNSW's original paper (Malkov & Yashunin) presents the layered-structure argument summarized above along with strong empirical validation across benchmark datasets, but the broader ANN literature does not treat this as an equally tight, universally-proven worst-case guarantee for arbitrary data distributions — the argument depends on the graph actually maintaining good navigability properties as it grows, which is an empirical property of the construction heuristics rather than something proven to hold for every possible dataset. This is a difference in the *type* of guarantee, not a claim that HNSW's scaling is unreliable in practice — benchmark evidence for the sub-linear shape is extensive — but a technical advisor would rightly distinguish "empirically well-supported and mechanistically well-motivated" from "formally proven for the worst case."

**It says nothing about recall.** HNSW is an *approximate* nearest-neighbor method — the layered greedy search can, and sometimes does, miss the true nearest neighbor, returning a close-but-not-exact match instead. The sub-linear scaling claim describes how many comparisons a query costs, not how often the returned answer is correct. A method could be extremely fast and sub-linear while also having degraded accuracy; the two properties are measured, tuned, and reported separately (commonly as **recall@k**, the fraction of true top-$k$ neighbors actually returned).

**It assumes fixed parameters — and that assumption can quietly break down.** The $O(\log n)$ derivation above depends on $M$ and $ef$ staying constant as $n$ grows. In practice, maintaining acceptable recall on a much larger dataset often requires *increasing* $ef$ (searching a wider candidate list) to compensate for the graph becoming proportionally sparser relative to the space it covers. If $ef$ must grow with $n$ to hold recall steady, the effective cost curve is no longer purely $O(\log n)$ — it becomes some faster-growing function of both $n$ and whatever schedule $ef$ is forced to follow, which is a genuinely dataset- and parameter-dependent question rather than a fixed guarantee.

**It says nothing about build cost or memory.** Sub-linear *query* cost does not imply sub-linear *total* cost for the system. Building the index means inserting all $n$ vectors one at a time, and each insertion itself costs roughly $O(\log n)$ (it is, after all, a query-like graph search used to find where to attach the new node) — so total construction cost across all $n$ insertions is roughly $O(n \log n)$, which is *not* sub-linear in $n$; it is worse than plain linear, just by a slowly-growing logarithmic factor. Memory is worse still: every stored vector and its edge list must be kept resident, so memory usage is $O(n \cdot M)$ — straightforwardly linear in $n$. "Sub-linear" describes only the cost of *answering one query* against an already-built index, not the cost of building or storing that index in the first place.

### Why This Distinction Matters Going Forward

The gap between "per-query cost is sub-linear" and "total system cost is sub-linear" is not a pedantic technicality — it is precisely the distinction that separates a theoretical asymptotic bound from an empirically measured cost curve when reasoning about how a system's costs behave as it scales. A structure can look excellent by one measure (query time) and considerably less favorable by another (build time, memory, or recall stability) — and knowing which measure a given scaling claim actually describes is what keeps a cost analysis honest.

**Key Points**

- A cost function is sub-linear when it grows strictly more slowly than $n$ itself ($T(n)/n \to 0$); brute-force linear scan's $O(n)$ cost is the non-sub-linear baseline HNSW is contrasted against.
- HNSW's $O(\log n)$ query-cost claim follows from composing two structural facts: roughly $O(\log n)$ layers (from the exponential-decay height assignment) times a per-layer cost bounded by fixed constants $M$ and $ef$ that don't grow with $n$.
- Sub-linear scaling is a statement about growth rate, not a guarantee of being cheaper at every $n$ — at small $n$, brute force can still win in raw comparison count or wall-clock time.
- The claim is empirically well-supported and mechanistically well-motivated, but it is not an equally rigorous worst-case theorem the way a skip list's expected-cost bound is; it depends on the graph maintaining good navigability, which is an empirical property of the construction heuristics.
- The scaling claim says nothing about recall (approximate answers can be wrong), assumes fixed $M$/$ef$ (which real deployments often must grow to preserve recall at larger $n$), and covers only per-query cost — build cost ($O(n \log n)$ total) and memory ($O(n \cdot M)$) remain linear or worse in $n$.

**Related Topics**

- The $M$, `efConstruction`, and `efSearch` parameters and how they trade off recall, speed, and memory
- HNSW build cost versus query cost, and why construction is the more expensive phase overall
- Recall@k as the standard way approximate nearest-neighbor accuracy is measured and reported
- Insertion cost as a function of existing structure size, and how theoretical bounds compare to empirically measured cost curves