# Strategy Interface Specification

This document defines the formal contract that all four candidate-narrowing strategies (and the null baseline strategy) must satisfy.

---

## 1. Overview & Separation of Concerns

Candidate insertion proceeds in two distinct stages:
1. **Candidate Narrowing (Strategy Module):** Given an existing `ConceptGraph` and one new concept name, retrieve a shortlisted set of existing candidate nodes that might connect with the new concept. Strategies own their internal data structures (embedding matrices, vector indexes, or partition buckets), but **read `ConceptGraph` immutably and never call an LLM directly** ([D-24]).
2. **Relationship Decision (Shared Driver & Decision Step):** The shared decision step ([D-02], [D-24]) takes the shortlisted candidates, prompts an LLM to decide pairwise prerequisite relationships, and the driver applies the resulting canonical directed edges (`prereq -> dependent`, [D-23]) to the `ConceptGraph`.

```
                    ┌─────────────────────────┐
                    │      ConceptGraph       │ (read-only to strategy)
                    └────────────┬────────────┘
                                 │
                     setup(graph, embedder)
                                 │
                                 ▼
                     ┌───────────────────────┐
   new_concept ─────>│  NarrowingStrategy    │ (no LLM calls; uses injected Embedder)
                     │  .shortlist()         │
                     └───────────┬───────────┘
                                 │
                        Shortlist(candidates)
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ Shared Decision Step  │ (LLM prompt; identical across strategies)
                     │ .decide(new, cand)    │
                     └───────────┬───────────┘
                                 │
                     DecisionOutcome(edges)
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  Shared insert_node   │ ──> commits edges to ConceptGraph
                     │      Driver           │ ──> calls strategy.on_inserted(new, edges)
                     └───────────────────────┘
```

---

## 2. Strategy Lifecycle Sequence

```
1. Instantiation:
   strategy = ConcreteStrategy(config_params..., seed=seed)

2. Initialization (UNTIMED):
   strategy.setup(initial_graph, embedder)
   # Embeds initial graph concepts, populates baseline indexes/buckets.
   # Note: Trial isolation requires a fresh strategy instance and a deep copy of the graph (graph.copy()).

3. Incremental Insertion (TIMED via insert_node):
   result = insert_node(strategy, graph, decision_step, new_concept, metered_embedder)
   ├─ Step 1: strategy.shortlist(new_concept)          --> Shortlist(candidates, scores)
   ├─ Step 2: decision_step.decide(...)                --> DecisionOutcome(edges, llm_calls, llm_seconds)
   │          (Empty shortlist skips LLM calls: 0 calls, 0 edges)
   ├─ Step 3: driver adds new_concept and edges to ConceptGraph
   └─ Step 4: strategy.on_inserted(new_concept, edges) --> Incremental index update
```

---

## 3. Timing & Metrics Accounting Model ([D-25])

All timing uses `time.perf_counter()`. Measurements are reported inside `InsertionMetrics`:

| Metric Field | Measured Operation | Scope / Source |
| :--- | :--- | :--- |
| `n_before` | Graph size before insertion | `graph.num_nodes()` |
| `shortlist_size` | Number of shortlisted candidates | `len(shortlist.candidates)` |
| `llm_calls` | Number of LLM API requests made | `outcome.llm_calls` (0 if shortlist is empty) |
| `embedding_calls` | Number of embedding calls during narrowing | Recorded via `MeteredEmbedder` delta during shortlist |
| `embed_s` | Cumulative seconds generating embeddings | From `MeteredEmbedder` during shortlist |
| `shortlist_s` | Wall-clock seconds for candidate narrowing | `t1 - t0` around `strategy.shortlist()` (subsumes `embed_s`) |
| `decide_s` | Wall-clock seconds in shared decision step | `t3 - t2` around `decision_step.decide()` (0.0 if empty shortlist) |
| `update_s` | Wall-clock seconds updating strategy index | `t5 - t4` around `strategy.on_inserted()` |
| `total_s` | Total wall-clock seconds for insertion | Measured end-to-end across Steps 1–4 (subsumes all above) |
| `extra` | Diagnostic metadata dictionary | Emitted by `strategy.diagnostics()` |

*Note on exclusions:* `setup()` is strictly untimed preparation and excluded from `total_s`.

---

## 4. Implementer Skeleton

```python
from typing import Any
import numpy as np
from graph_insertion import ConceptGraph, Embedder, Shortlist, embed_text

class StrategySkeleton:
    """Template for implementing a candidate-narrowing strategy."""

    def __init__(self, seed: int = 42, **kwargs: Any) -> None:
        self.name = "strategy_name"
        self.seed = seed
        self._embedder: Embedder | None = None
        self._graph: ConceptGraph | None = None
        # Internal state (e.g. index, matrices, buckets)

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder
        # Build initial search structures over existing graph nodes

    def shortlist(self, new_name: str) -> Shortlist:
        # 1. Embed new_name via self._embedder.embed(embed_text(new_name)) if applicable
        # 2. Query internal search structures
        # 3. Return candidates tuple (must be subset of graph nodes, no duplicates)
        return Shortlist(candidates=(...))

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        # Incrementally update index/matrix/bucket with new_name and its edges
        pass

    def config(self) -> dict[str, Any]:
        return {"seed": self.seed}

    def diagnostics(self) -> dict[str, Any]:
        return {}
```

---

## 5. Non-Binding State Sketch for the Four Strategies

| Strategy | `setup(graph, embedder)` Action | `on_inserted(new_name, edges)` Action | Primary Diagnostics |
| :--- | :--- | :--- | :--- |
| **S1: Brute-Force** | None (no embeddings, no index). | None (stateless). | `{"candidate_count": n}` |
| **S2: Embedding Threshold** | Computes and caches embedding matrix for all $n$ concepts. | Computes embedding for `new_name` and appends row to matrix. | `{"cosine_comparisons": n, "threshold": theta}` |
| **S3: ANN Retrieval (FAISS)** | Builds and populates vector index (e.g. `IndexFlatIP` or `IndexHNSWFlat`). | Inserts embedding of `new_name` into the ANN index. | `{"top_k": k, "index_size": n}` |
| **S4: Bounded Buckets (EraRAG-style)** | Partitions initial nodes into bounded-size buckets ($\le B$). Computes bucket centroids/summaries. | Adds `new_name` to target bucket; triggers bucket split if size exceeds $B$, or recomputes centroid. | `{"bucket_id": bid, "split_occurred": bool, "bucket_size": s}` |
