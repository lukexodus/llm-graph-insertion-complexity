## Why evaluating placement correctness is its own separate problem from evaluating insertion speed, and why a fast but wrong insertion is not a solved problem

### The routing analogy: two independent questions about the same event

Consider a network router deciding where to forward an incoming packet. Two completely separate questions can be asked about that single forwarding decision: *how quickly did the router make it*, and *did the router send the packet to the correct destination*. A router with a corrupted routing table can answer in microseconds and still send every packet to the wrong subnet. A router doing an exhaustive table scan can take milliseconds and get every packet right. Latency and correctness are measured with different instruments, on different scales, and neither one tells you anything about the other.

Inserting a new node into an LLM-constructed knowledge graph is the same kind of event. The insertion strategy has to decide, for a new node, which existing nodes it should be connected to. "How long did that decision take" and "was that decision the right one" are two independent measurements of the same act, and a curriculum or a thesis that reports only one of them has not actually evaluated the insertion strategy — it has only evaluated half of it.

### Formalizing the two axes

For any insertion strategy $S$ operating on a graph that has grown to $n$ existing nodes, define two separate functions:

**Cost metric.** $C_S(n)$ is the amount of work (comparisons, distance computations, LLM calls) spent placing the $n$-th node. This is a purely mechanical quantity: recall that amortized analysis measures the average cost per operation across a sequence, smoothing out occasional expensive steps, and that this kind of analysis produces bounds like $C_S(n) = O(\log n)$ purely by reasoning about the shape of the data structure and the traversal algorithm. Nothing about $C_S(n)$ refers to what the new node's embedding actually means.

**Correctness metric.** $Q_S(n)$ measures whether the edges the strategy attached the new node to are the *semantically right* edges — the ones a domain expert, or an LLM acting as a careful judge, would agree belong there. A standard way to quantify this borrows precision and recall from information retrieval:

$$\text{Precision} = \frac{\text{edges added that are semantically correct}}{\text{total edges added}}, \quad \text{Recall} = \frac{\text{edges added that are semantically correct}}{\text{total edges that should exist}}$$

These two functions, $C_S(n)$ and $Q_S(n)$, are defined over the same input but computed from completely different evidence: $C_S(n)$ comes from counting operations, $Q_S(n)$ comes from a semantic judgment about meaning. There is no algebraic relationship that lets you derive one from the other. A proof that $C_S(n)$ is small says literally nothing about $Q_S(n)$, in the same way that a proof that a sorting algorithm runs in $O(n \log n)$ says nothing about whether the comparator function it was given was implemented correctly.

### A worked example: the same fast lookup, two different outcomes

Suppose the graph already contains four nodes arranged as a small taxonomy: `Mammal` is the parent of `Dog`, and `Dog` is the parent of `Golden Retriever`; `Cat` sits as a second child of `Mammal`. A new node, `Wolf`, needs to be inserted.

**Fast, wrong.** An approximate nearest-neighbor index is queried with a small candidate list — recall that in HNSW, the parameter `ef` controls how many candidates are explored during a search, and a small `ef` trades recall for speed. With a small `ef`, the search returns `Dog` as the closest existing node, because in the underlying text corpus "wolf" and "dog" co-occur heavily (shared habitat and behavior vocabulary), pulling their embeddings close together under cosine similarity — recall that cosine similarity measures the angle between two vectors, ignoring magnitude, and is engineered to track topical or semantic proximity, not formal taxonomic relationships. `Wolf` gets attached as a child of `Dog`. The insertion is genuinely fast: a small, bounded traversal through the graph's upper layers. It is also wrong: `Wolf` is not a subtype of `Dog`, it is a sibling of `Dog` under `Mammal`.

**Slow, correct.** A brute-force linear scan — recall that brute-force linear scan computes similarity against every existing node and is the honest $O(n)$ baseline — retrieves both `Dog` and `Mammal` as candidates. An LLM acting as a semantic judge is then asked directly whether `Wolf` is a subtype of `Dog` or a subtype of `Mammal`. Recall that an LLM-as-judge call is a distinct operation from a similarity score: it produces an entailment or subsumption judgment ("is a Wolf a kind of Dog?") rather than a distance number. The judge correctly answers that `Wolf` is a sibling of `Dog`, and the node is attached under `Mammal`. This insertion did more work — a full scan plus a language-model call — but placed the node correctly.

Nothing prevents the two remaining combinations from existing too. A **fast, correct** strategy is possible: run the approximate search for candidate generation, then add a cheap LLM verification step before committing the edge, so the speed of ANN retrieval is preserved but the correctness of the final decision is checked before it is written to the graph. A **slow, wrong** strategy is also possible: a brute-force scan combined with a badly specified verification prompt still produces a full $O(n)$ scan and can still attach the node to the wrong parent. All four cells of this matrix are occupied by real, buildable strategies, which is itself the proof that speed and correctness vary independently.



```
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 460">
  <text x="310" y="28" font-size="16" font-weight="bold" text-anchor="middle" fill="#222">Insertion Speed vs. Placement Correctness (svg_diagram)</text>

  
  <line x1="80" y1="400" x2="580" y2="400" stroke="#333" stroke-width="2" />
  <line x1="80" y1="400" x2="80" y2="60" stroke="#333" stroke-width="2" />
  <text x="330" y="430" font-size="14" text-anchor="middle" fill="#333">Insertion Speed →</text>
  <text x="40" y="230" font-size="14" text-anchor="middle" fill="#333" transform="rotate(-90 40 230)">Placement Correctness →</text>

  
  <line x1="330" y1="60" x2="330" y2="400" stroke="#bbb" stroke-dasharray="6,6" />
  <line x1="80" y1="230" x2="580" y2="230" stroke="#bbb" stroke-dasharray="6,6" />

  
  <circle cx="180" cy="120" r="9" fill="#2b6cb0" />
  <text x="195" y="115" font-size="12" fill="#2b6cb0">Brute-force + LLM judge (slow, correct)</text>

  <circle cx="480" cy="330" r="9" fill="#c53030" />
  <text x="380" y="355" font-size="12" fill="#c53030">Low-ef ANN, no verification (fast, wrong)</text>

  <circle cx="480" cy="140" r="9" fill="#2f855a" />
  <text x="380" y="130" font-size="12" fill="#2f855a">ANN + verification stage (fast, correct)</text>

  <circle cx="230" cy="300" r="9" fill="#b7791f" />
  <text x="245" y="320" font-size="12" fill="#b7791f">Embedding-threshold only (moderate, unreliable)</text>
</svg>
```

### Why complexity bounds carry no semantic information

A useful way to see why the two axes are irreducibly separate is to notice what a complexity proof actually talks about. When Chapter 04's HNSW analysis or Chapter 05's amortized-cost machinery establishes that an operation costs $O(\log n)$, the proof reasons entirely about the *shape* of the traversal: how many layers are visited, how many neighbors are examined at each layer, how the potential function bounds the cost of occasional expensive rebuilds. None of that reasoning ever inspects *what the vectors mean*. The proof would go through unchanged if every embedding in the graph were replaced with random noise, because the proof is about operation counts, not about semantic content.

This means a cost bound and a correctness guarantee are proven by completely different kinds of arguments, using completely different evidence, and a thesis or system that only reports the cost curve from Chapter 07's growth-cost framing has made a claim about *how the algorithm scales*, not a claim about *whether the algorithm is right*. Both claims are needed, and neither substitutes for the other.

### Why a fast-but-wrong insertion is not a solved problem

Two compounding effects make a fast-but-wrong strategy actively worse than simply "incomplete," rather than merely half-finished:

**Errors propagate through routing.** Recall that HNSW's query procedure works by greedy routing — at each layer, the search moves to whichever neighbor is closest to the query, using the graph's *existing* edges to decide where to look next. If an early insertion attached a node to the wrong neighbor, every later approximate search that routes through that node inherits a corrupted path. The graph does not merely contain one wrong edge; it contains one wrong edge that actively misdirects the traversal decisions used to place every subsequent node. This is structurally identical to a routing table with one bad entry silently degrading every packet that happens to route through it, and it means placement errors compound with $n$ rather than staying fixed in number.

**Errors are silent, unlike speed regressions.** A slow insertion announces itself: a timeout, a latency spike, a visible drop in throughput. A wrong insertion announces nothing — the system reports "node inserted successfully" whether or not the edge it created is semantically defensible. This asymmetry means a correctness defect can persist through months of otherwise-successful operation, exactly the kind of silent failure Chapter 08 illustrates with the Healthcare Facilities and Hospitals example, where an LLM's inconsistent subsumption judgments produced a structurally plausible-looking graph that was nevertheless topologically wrong.

Put together, a fast-but-wrong strategy is not a partially working solution that merely needs a correctness patch bolted on later — the wrongness actively degrades the very structure that future fast lookups depend on. "Fast" was never evidence toward "solved"; it was only ever evidence toward one of the two independent requirements a solved strategy has to meet.

### Two separate evaluation protocols, run independently

Because the two properties are independent, validating an insertion strategy honestly requires two separate experimental protocols, neither of which can be inferred from the other:

- **A speed benchmark**: measure wall-clock time or operation count as a function of $n$, across a range of graph sizes, and compare the empirical curve against the theoretical bound the strategy claims (this is exactly the empirical-versus-theoretical comparison framed in Chapter 07).
- **A correctness benchmark**: compare the edges each strategy produces against a gold-standard graph, or against a panel of independent LLM/human subsumption judgments, and compute precision and recall as defined above, at the *same* range of graph sizes used for the speed benchmark.

**Key Points**

- Insertion cost $C_S(n)$ and placement correctness $Q_S(n)$ are functions of the same event but are computed from entirely different evidence — operation counts versus semantic judgment — so neither can be inferred from the other.
- Every cell of the fast/slow × correct/wrong matrix is populated by a real strategy; speed and correctness vary independently, not together.
- A complexity proof (amortized or worst-case) never inspects the meaning of the vectors involved, so it can never serve as evidence of correctness.
- Placement errors compound because later approximate searches route through earlier, possibly-wrong edges, and they are silent because the system reports success regardless of semantic accuracy.
- A strategy is only "solved" when it has passed a speed benchmark and a correctness benchmark separately, at matching graph sizes — passing only one leaves the other question completely open.

**Conclusion**

Treating insertion speed and placement correctness as a single evaluation is a category error: one is a statement about an algorithm's mechanics, the other is a statement about whether a semantic decision was right, and a fast wrong answer is not a discount version of a solved problem — it is a different, unsolved problem wearing the appearance of progress.

```mermaid
flowchart TD
    A[New node candidate] --> B[Insertion strategy]
    B --> C[Speed benchmark: measure C(n) across graph sizes]
    B --> D[Correctness benchmark: precision/recall vs gold graph]
    C --> E{Meets speed target?}
    D --> F{Meets correctness target?}
    E -- No --> G[Fails: too slow]
    F -- No --> H[Fails: fast but wrong]
    E -- Yes --> I{Both targets met?}
    F -- Yes --> I
    I -- Yes --> J[Strategy considered solved]
    I -- No --> H
```

**Related Topics**

- Precision/recall against a gold-standard graph as a formal correctness metric for incremental construction
- How ef and M parameter choices in HNSW trade recall for speed, and how that tradeoff maps directly onto the correctness axis
- The generator-verifier-pruner architectural pattern as a design that explicitly separates fast candidate generation from a correctness-checking stage
- Graph drift under streaming updates as the accumulated, compounding effect of repeated silent placement errors
- Designing a two-stage benchmark suite (speed harness plus correctness harness) for comparing brute-force, embedding-threshold, ANN-index, and bounded-bucket insertion strategies at matching graph sizes