## HNSW's Layered Hierarchy: Stacked Navigable Small-World Graphs, from Sparse Top to Dense Bottom

### Recap of the Two Pieces Being Fused

Recall that a skip list gets $O(\log n)$ search out of a sorted linked list by stacking sparse "express lane" levels over a dense "local lane," where each node's height is chosen independently by a geometric coin-flip process, and searches descend level by level rather than staying in one flat structure. Recall separately that a navigable small-world (NSW) graph gets greedy routing to work over an *unordered* vector space by mixing long-range and short-range edges within a single flat proximity graph, with the long-range edges arising as an accidental side effect of insertion order rather than by explicit design — and recall that this flat mixing leaves two problems unresolved: the long/short split isn't tunable, and the earliest-inserted hub nodes accumulate disproportionate degree as the graph grows, becoming a bottleneck.

HNSW (Hierarchical Navigable Small World) is the fusion of exactly these two ideas: it keeps NSW's graph-based greedy routing (necessary because embedding vectors have no total order to sort by) but reinstates the skip list's *explicit, level-based* separation of long-range and short-range structure, instead of leaving that separation to insertion-order accident.

### The Core Structural Idea

An HNSW index is not one graph — it is a **stack of NSW-style graphs**, one per layer, numbered from layer $L$ (the top, sparsest) down to layer $0$ (the bottom, containing every vector in the index). Each layer is itself a proximity graph built and searched with the same greedy-routing mechanics: nodes connected to their approximate nearest neighbors *within that layer*, searched by hopping to whichever neighbor is closer to the query, stopping at a local optimum.

The layers are related by strict containment: every node present at layer $i$ is also present at every layer below it, down to layer $0$. So layer $0$ contains the full dataset; layer 1 contains some smaller subset of it; layer 2 an even smaller subset; and so on up to the top layer, which typically holds only a handful of nodes. This mirrors a skip list precisely: a node with skip-list height $h$ appears at every level from $1$ up to $h$, never only at a single level in isolation — a node that participates at level 2 is, by construction, also present and linked at level 1.

### Where Each Node's Height Comes From

Just as a skip list assigns each node a height via repeated coin flips with success probability $p$, HNSW assigns each node a maximum layer $\ell$ by drawing from an exponentially-decaying random distribution at insertion time:

$$\ell = \lfloor -\ln(\text{unif}(0,1)) \cdot m_L \rfloor$$

where $\text{unif}(0,1)$ is a uniform random draw and $m_L$ is a normalization constant (commonly set to $1/\ln(M)$, where $M$ is the target per-node connectivity, discussed as its own parameter separately). This is the continuous-valued cousin of the skip list's discrete geometric coin-flip process: both produce a distribution where most nodes get a small height/layer (most mass near $\ell=0$), and the chance of reaching a much higher layer shrinks multiplicatively the higher you go. The practical effect is identical to a skip list's: the top layers end up sparse almost by mathematical necessity, not because anyone hand-picks which nodes go where.

**Worked comparison, small scale.** For a dataset of $n=1{,}000{,}000$ vectors with $m_L = 1/\ln(16) \approx 0.36$, the expected number of nodes at layer $\ell$ shrinks by roughly a factor of $M=16$ per layer: layer 0 holds all $1{,}000{,}000$; layer 1 holds roughly $62{,}500$; layer 2 roughly $3{,}900$; layer 3 roughly $244$; layer 4 roughly $15$; by layer 5 the expected count is close to $1$. This is why a real HNSW index over a million vectors typically has only 4–6 layers total — the exponential decay compresses the "distance-covering" work into a tiny number of nodes at the top, exactly the way a skip list over a million keys needs only about $\log_2(1{,}000{,}000) \approx 20$ levels.

### Why This Solves NSW's Two Open Problems

**Tunability.** In flat NSW, the long-range/short-range split was whatever insertion order happened to produce, with no dial to adjust it. In HNSW, the split is governed directly by $m_L$ (and by $M$, which $m_L$ is derived from): increasing $m_L$ makes the layer-height distribution heavier-tailed, pushing more nodes into higher layers and creating a richer hierarchy at the cost of more memory and construction time; decreasing it flattens the hierarchy back toward something closer to a single-layer NSW graph. This is a genuine engineering knob, unlike NSW's accidental structure.

**The hub-bottleneck problem.** In flat NSW, the earliest-inserted nodes kept accumulating edges indefinitely as the graph grew, because every later greedy search kept passing through them. In HNSW, a node's participation at high layers is capped by its randomly assigned $\ell$, independent of insertion order — a node inserted very late in the process can still draw a high $\ell$ and become part of the sparse top-layer structure, while a node inserted very early can draw $\ell=0$ and remain confined to the dense bottom layer only. Layer membership is decoupled from arrival time, which prevents the same handful of nodes from being forced to mediate every single query indefinitely as $n$ grows.

### Visualizing the Stack

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 480" font-family="monospace" font-size="14">
<text x="450" y="25" text-anchor="middle" font-size="16" font-weight="bold">HNSW Layered Hierarchy: Sparse Top to Dense Bottom (svg_diagram)</text>
<text x="30" y="75" font-weight="bold">Layer 3</text>
<rect x="120" y="55" width="660" height="40" fill="none" stroke="#d1d5db" stroke-dasharray="3,3" />
<circle cx="420" cy="75" r="16" fill="#1e40af" stroke="#1f2937" stroke-width="2" />
<text x="420" y="80" text-anchor="middle" fill="white" font-size="11">E</text>
<line x1="420" y1="75" x2="420" y2="145" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />

<text x="30" y="155" font-weight="bold">Layer 2</text>
<rect x="120" y="135" width="660" height="40" fill="none" stroke="#d1d5db" stroke-dasharray="3,3" />
<circle cx="220" cy="155" r="16" fill="#2563eb" stroke="#1f2937" stroke-width="2" />
<text x="220" y="160" text-anchor="middle" fill="white" font-size="11">A</text>
<circle cx="420" cy="155" r="16" fill="#2563eb" stroke="#1f2937" stroke-width="2" />
<text x="420" y="160" text-anchor="middle" fill="white" font-size="11">E</text>
<circle cx="620" cy="155" r="16" fill="#2563eb" stroke="#1f2937" stroke-width="2" />
<text x="620" y="160" text-anchor="middle" fill="white" font-size="11">H</text>
<line x1="220" y1="155" x2="420" y2="155" stroke="#1f2937" stroke-width="1.5" />
<line x1="420" y1="155" x2="620" y2="155" stroke="#1f2937" stroke-width="1.5" />
<line x1="220" y1="155" x2="220" y2="225" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="420" y1="155" x2="420" y2="225" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="620" y1="155" x2="620" y2="225" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />

<text x="30" y="235" font-weight="bold">Layer 1</text>
<rect x="120" y="215" width="660" height="40" fill="none" stroke="#d1d5db" stroke-dasharray="3,3" />
<circle cx="170" cy="235" r="16" fill="#3b82f6" stroke="#1f2937" stroke-width="2" />
<text x="170" y="240" text-anchor="middle" fill="white" font-size="11">A</text>
<circle cx="270" cy="235" r="16" fill="#3b82f6" stroke="#1f2937" stroke-width="2" />
<text x="270" y="240" text-anchor="middle" fill="white" font-size="11">C</text>
<circle cx="420" cy="235" r="16" fill="#3b82f6" stroke="#1f2937" stroke-width="2" />
<text x="420" y="240" text-anchor="middle" fill="white" font-size="11">E</text>
<circle cx="520" cy="235" r="16" fill="#3b82f6" stroke="#1f2937" stroke-width="2" />
<text x="520" y="240" text-anchor="middle" fill="white" font-size="11">F</text>
<circle cx="620" cy="235" r="16" fill="#3b82f6" stroke="#1f2937" stroke-width="2" />
<text x="620" y="240" text-anchor="middle" fill="white" font-size="11">H</text>
<line x1="170" y1="235" x2="270" y2="235" stroke="#1f2937" stroke-width="1.5" />
<line x1="270" y1="235" x2="420" y2="235" stroke="#1f2937" stroke-width="1.5" />
<line x1="420" y1="235" x2="520" y2="235" stroke="#1f2937" stroke-width="1.5" />
<line x1="520" y1="235" x2="620" y2="235" stroke="#1f2937" stroke-width="1.5" />
<line x1="170" y1="235" x2="145" y2="300" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="270" y1="235" x2="270" y2="300" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="420" y1="235" x2="420" y2="300" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="520" y1="235" x2="520" y2="300" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />
<line x1="620" y1="235" x2="655" y2="300" stroke="#9ca3af" stroke-width="1" stroke-dasharray="2,2" />

<text x="30" y="405" font-weight="bold">Layer 0</text>
<text x="30" y="422" font-size="11" fill="#4b5563">(all nodes)</text>
<rect x="120" y="290" width="660" height="120" fill="none" stroke="#d1d5db" stroke-dasharray="3,3" />
<circle cx="145" cy="320" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="145" y="325" text-anchor="middle" font-size="10">A</text>
<circle cx="220" cy="380" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="220" y="385" text-anchor="middle" font-size="10">B</text>
<circle cx="270" cy="320" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="270" y="325" text-anchor="middle" font-size="10">C</text>
<circle cx="340" cy="380" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="340" y="385" text-anchor="middle" font-size="10">D</text>
<circle cx="420" cy="320" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="420" y="325" text-anchor="middle" font-size="10">E</text>
<circle cx="520" cy="320" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="520" y="325" text-anchor="middle" font-size="10">F</text>
<circle cx="590" cy="380" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="590" y="385" text-anchor="middle" font-size="10">G</text>
<circle cx="655" cy="320" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="655" y="325" text-anchor="middle" font-size="10">H</text>
<circle cx="730" cy="380" r="15" fill="#93c5fd" stroke="#1f2937" stroke-width="1.5" />
<text x="730" y="385" text-anchor="middle" font-size="10">I</text>
<line x1="145" y1="320" x2="220" y2="380" stroke="#1f2937" stroke-width="1" />
<line x1="145" y1="320" x2="270" y2="320" stroke="#1f2937" stroke-width="1" />
<line x1="270" y1="320" x2="340" y2="380" stroke="#1f2937" stroke-width="1" />
<line x1="220" y1="380" x2="340" y2="380" stroke="#1f2937" stroke-width="1" />
<line x1="270" y1="320" x2="420" y2="320" stroke="#1f2937" stroke-width="1" />
<line x1="420" y1="320" x2="520" y2="320" stroke="#1f2937" stroke-width="1" />
<line x1="520" y1="320" x2="590" y2="380" stroke="#1f2937" stroke-width="1" />
<line x1="520" y1="320" x2="655" y2="320" stroke="#1f2937" stroke-width="1" />
<line x1="655" y1="320" x2="730" y2="380" stroke="#1f2937" stroke-width="1" />
<line x1="590" y1="380" x2="730" y2="380" stroke="#1f2937" stroke-width="1" />
</svg>

Node $E$ is the tallest here, appearing at layers 0 through 3; nodes $A$, $C$, $F$, $H$ reach layer 1; every node down to $B$, $D$, $G$, $I$ exists only at layer 0. This is the exact containment property a skip list enforces (a node's presence at level $i$ implies its presence at every level below $i$), now applied to graph nodes instead of linked-list nodes.

### Why the Shape (Sparse Top, Dense Bottom) Is the Point

The functional reason for this shape is a direct inheritance from the skip list's cost-balancing logic. Recall that a single express lane over a sorted list balanced $n/k$ express hops against $k$ local hops, and that stacking levels recursively pushed the total cost down to $O(\log n)$ by making each level responsible for a geometrically shrinking fraction of the remaining search distance. HNSW's layers do the same job over a graph instead of a line:

- **Top layer(s):** extremely sparse (a handful of nodes), so any greedy walk here covers enormous distances across the vector space in very few hops — this is the graph equivalent of the skip list's express lane, purpose-built for closing most of the gap to the query's general region quickly.
- **Middle layers:** progressively denser, refining the search's position within an increasingly narrow region.
- **Bottom layer (layer 0):** contains every vector and the densest set of edges, providing the fine-grained precision needed to actually identify the true (or near-true) nearest neighbor once the search has been routed to the right neighborhood.

A query descends through this stack top-down: greedy-search the sparse top layer to find a good-enough entry point into the next layer down, repeat at each successively denser layer, and only do the expensive, fine-grained work at layer 0 where it's actually needed. This is precisely why a flat NSW graph's implicit hub structure was an *approximation* of something HNSW makes exact and controllable: the hubs that emerged accidentally from early insertion order in NSW are replaced by a principled, geometrically-decaying membership rule that guarantees the sparse-to-dense shape holds regardless of insertion order.

### What This Item Deliberately Leaves Open

This item establishes the *static shape* of the hierarchy — what the layers are, why they're nested, and why the population thins out geometrically from bottom to top. It does not yet walk through the mechanics of an actual query traversing the stack layer by layer (how the entry point at each layer is chosen, when the search switches from a single running best to a candidate list, and how the descent terminates), nor does it cover the $M$ and $ef$ parameters that govern each layer's internal connectivity and search breadth, nor the asymmetry between how expensive it is to build this structure versus how expensive it is to query it. Those are each their own separate concern, building directly on the layered structure established here.

**Key Points**
- HNSW stacks multiple NSW-style graphs into explicit layers, numbered from sparse layer $L$ (top) to dense layer $0$ (bottom, containing every vector), with strict containment: a node present at layer $i$ is also present at every layer below it.
- Each node's maximum layer is drawn from an exponentially-decaying random distribution at insertion time — the continuous-valued analogue of a skip list's geometric coin-flip height assignment — which is why layer population shrinks by roughly a constant factor ($\approx M$) at each level up.
- This explicit, distribution-driven layering directly resolves flat NSW's two open problems: the long/short-range split becomes tunable via $m_L$/$M$ instead of being an insertion-order accident, and layer membership is decoupled from arrival time, preventing the same early hub nodes from bottlenecking every query indefinitely.
- The sparse-top/dense-bottom shape mirrors a skip list's cost-balancing logic: top layers close most of the distance to the query's region in very few hops, and the dense bottom layer supplies the fine-grained precision to pin down the actual answer.

**Related Topics**
- The full step-by-step HNSW query algorithm: layer-by-layer descent, entry-point selection, and the switch to a candidate list at layer 0
- The $M$ and $ef$ (efConstruction / efSearch) parameters and what each one controls
- HNSW build cost versus query cost, and why construction is more expensive than search
- Sub-linear scaling behavior of HNSW compared to brute-force linear scan as $n$ grows