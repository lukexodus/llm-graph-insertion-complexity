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
   # Attributes:
   #   uses_embeddings: bool (default True; False for non-embedding strategies like NullStrategy, [D-38](2))
   # Optional method ([D-41]):
   #   max_candidates(n_existing: int) -> int
   #   Evaluated pre-flight (BEFORE setup) by harness and CLI estimators via candidate_upper_bound().

2. Initialization (UNTIMED):
   strategy.setup(initial_graph, embedder)
   # Embeds initial graph concepts, populates baseline indexes/buckets.
   # Note: Trial isolation requires a fresh strategy instance and a deep copy of the graph (graph.copy()).
   # Embedding strategies store embedder as self._embedder; non-embedding strategies leave self._embedder = None.

3. Incremental Insertion (TIMED via insert_node):
   result = insert_node(strategy, graph, decision_step, new_concept, metered_embedder=metered_embedder)
   ├─ Step 0: Driver verifies metered_embedder identity (strategy._embedder is metered_embedder; bypassed if None)
   ├─ Step 1: strategy.shortlist(new_concept)          --> Shortlist(candidates, scores)
   │          (Driver validates candidates: must be subset of existing nodes, no duplicates, excludes new_concept; timed in validate_s)
   │          (If max_candidates is implemented, len(candidates) <= max_candidates(n_existing))
   ├─ Step 2: decision_step.decide(...)                --> DecisionOutcome(edges, llm_calls, llm_seconds)
   │          (Empty shortlist skips LLM calls: 0 calls, 0 edges)
   ├─ Step 3: driver validates edges (timed in validate_s) and mutates ConceptGraph (timed via apply_s):
   │          (Validates: canonical 2-tuples, no self-loops, no duplicates, other endpoint in shortlist.candidates)
   │          (Adds new_concept and applies decided edges to ConceptGraph)
   └─ Step 4: strategy.on_inserted(new_concept, edges) --> Incremental index update (timed via update_s)
              (Reuses cached vector from Step 1; must NOT re-embed new_concept; embedding_calls_in_update must be 0)
```

---

## 3. Timing & Metrics Accounting Model ([D-25], [D-26], [D-28])

All timing uses `time.perf_counter()`. Measurements are reported inside `InsertionMetrics`:

| Metric Field | Measured Operation | Scope / Source |
| :--- | :--- | :--- |
| `n_before` | Graph size before insertion | `graph.num_nodes()` |
| `shortlist_size` | Number of shortlisted candidates | `len(shortlist.candidates)` |
| `llm_calls` | Number of LLM API requests made | `outcome.llm_calls` (0 if shortlist is empty) |
| `embedding_calls` | Number of embedding calls during narrowing | Recorded via `MeteredEmbedder` delta during shortlist |
| `embed_s` | Cumulative seconds generating embeddings | From `MeteredEmbedder` during shortlist |
| `embedding_calls_in_update` | Number of embedding calls made during on_inserted | Discrete call count delta from `MeteredEmbedder` during `on_inserted` (must be 0 under [D-26]/[D-28]) |
| `embed_in_update_s` | Cumulative seconds generating embeddings during update | From `MeteredEmbedder` during `on_inserted` (must be 0.0 under single-embedding invariant) |
| `shortlist_s` | Wall-clock seconds for candidate narrowing | `t1 - t0` around `strategy.shortlist()` (subsumes `embed_s`) |
| `decide_s` | Wall-clock seconds in shared decision step | `t3 - t2` around `decision_step.decide()` (0.0 if empty shortlist) |
| `apply_s` | Wall-clock seconds committing to graph | `time.perf_counter()` around graph node and edge addition |
| `update_s` | Wall-clock seconds updating strategy index | `time.perf_counter()` around `strategy.on_inserted()` |
| `validate_s` | Wall-clock seconds for contract validation | Separate timing for shortlist contract checks and pre-mutation edge validation |
| `total_s` | Total operational wall-clock seconds for insertion | `shortlist_s + decide_s + apply_s + update_s` (validation overhead excluded per [D-28]) |
| `extra` | Diagnostic metadata dictionary | Emitted by `strategy.diagnostics()` (or `{"diagnostics_error": repr(e)}` on failure) |

*Notes:*
- `setup()` is strictly untimed preparation and excluded from `total_s`.
- **Single-Embedding Invariant ([D-26], [D-28]):** An insertion of `new_name` requires computing its embedding at most once. Strategies compute and cache `new_name`'s vector in `shortlist()`, and reuse that vector in `on_inserted()`. Embedding `new_name` a second time in `on_inserted()` is strictly prohibited (`embedding_calls_in_update == 0` and `embed_in_update_s == 0.0`).
- **Embedder Metering & Identity Contract ([D-28], superseding item 1 of [D-26]):** `metered_embedder` is a required, non-Optional keyword-only argument (`MeteredEmbedder`). Passing `None` or a non-`MeteredEmbedder` raises `TypeError`. At the start of `insert_node`, the driver verifies embedder identity: if `strategy._embedder is not None and strategy._embedder is not metered_embedder`, it raises `ValueError` before candidate narrowing or graph mutation, preventing silent undercounting of embedding costs. A strategy without an embedder accepts any valid `MeteredEmbedder`.
- **Validation Timing Exclusion ([D-28]):** Overhead from driver assertions and contract verification (which scales as $O(|\\text{shortlist}|)$) is isolated in `validate_s` and excluded from `total_s`, guaranteeing that `total_s` strictly reflects operational strategy and decision execution.

---

## 4. Implementer Skeleton

```python
from typing import Any
import numpy as np
from graph_insertion import ConceptGraph, Embedder, Shortlist, embed_text

class StrategySkeleton:
    """Template for implementing a candidate-narrowing strategy."""

    uses_embeddings: bool = True  # Set to False for non-embedding strategies ([D-38](2))

    def __init__(self, seed: int = 42, **kwargs: Any) -> None:
        self.name = "strategy_name"
        self.seed = seed
        self._embedder: Embedder | None = None
        self._graph: ConceptGraph | None = None
        self._cached_new_vec: np.ndarray | None = None
        # Internal state (e.g. index, matrices, buckets)

    def max_candidates(self, n_existing: int) -> int:
        """Optional ([D-41]): upper bound on shortlist candidate count given n_existing nodes.

        Can be called before setup() to compute pre-flight planned LLM call budgets.
        If omitted, harness defaults to brute-force n_existing.
        """
        return n_existing

    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
        self._graph = graph
        self._embedder = embedder if self.uses_embeddings else None
        # Build initial search structures over existing graph nodes

    def shortlist(self, new_name: str) -> Shortlist:
        # 1. Embed new_name via self._embedder.embed(embed_text(new_name)) if applicable
        #    and cache the resulting vector to avoid re-embedding in on_inserted.
        if self._embedder is not None:
            self._cached_new_vec = self._embedder.embed(embed_text(new_name))
        
        # 2. Query internal search structures
        # 3. Return candidates tuple (must be subset of graph nodes, no duplicates, no new_name)
        return Shortlist(candidates=(...))

    def on_inserted(self, new_name: str, edges: tuple[tuple[str, str], ...]) -> None:
        # Incrementally update index/matrix/bucket with new_name and its edges
        # Reuses self._cached_new_vec; does NOT call self._embedder.embed(new_name) again.
        new_vec = self._cached_new_vec
        self._cached_new_vec = None
        # update internal index structures with (new_name, new_vec, edges)...

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
| **S2: Embedding Threshold** | Computes and caches embedding matrix for all $n$ concepts. | Appends cached vector from `shortlist()` to matrix row. | `{"cosine_comparisons": n, "threshold": theta}` |
| **S3: ANN Retrieval (FAISS)** | Builds and populates vector index (e.g. `IndexFlatIP` or `IndexHNSWFlat`). | Inserts cached vector from `shortlist()` into ANN index. | `{"top_k": k, "index_size": n}` |
| **S4: Bounded Buckets (EraRAG-style)** | Partitions initial nodes into bounded-size buckets ($\le B$). Computes bucket centroids/summaries. | Adds `new_name` with cached vector to target bucket; triggers bucket split if size exceeds $B$, or recomputes centroid. | `{"bucket_id": bid, "split_occurred": bool, "bucket_size": s}` |

---

## 6. Conformance Testing Suite Guide

To ensure consistent behavior across all four strategies (STRAT-001 through STRAT-004) and baselines, a reusable conformance test base class is provided in `tests/test_strategy_interface.py`: `StrategyConformanceSuite`.

Every strategy test module must subclass `StrategyConformanceSuite`, set `uses_embeddings = True` (or `False` for non-embedding strategies, [D-38](2)), and define a `strategy_factory` fixture returning a factory function `(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy`:

```python
import pytest
from tests.test_strategy_interface import StrategyConformanceSuite
from graph_insertion.strategies.my_strategy import MyConcreteStrategy

class TestMyConcreteStrategyConformance(StrategyConformanceSuite):
    uses_embeddings: bool = True

    @pytest.fixture
    def strategy_factory(self):
        def _factory(graph, embedder):
            strat = MyConcreteStrategy(seed=42)
            strat.setup(graph, embedder)
            return strat
        return _factory
```

The conformance suite automatically verifies:
1. **Candidate subset & exclusion:** `shortlist()` returns a subset of existing graph nodes, containing no duplicates, and never containing `new_name`.
2. **Graph immutability:** `shortlist()` does not mutate node or edge sets in `ConceptGraph`.
3. **Determinism:** Identical seeds produce identical shortlists and score sequences.
4. **D-21 text payload compliance:** All texts passed to embedders match `embed_text(c)` for some concept $c$ in the trial (lowercase, no raw underscores, no domain descriptions). When `uses_embeddings=False`, asserts zero embedding calls, zero embedding time, and empty texts log.
5. **Cached single-embedding reuse ([D-26]):** An insertion triggers exactly 1 embedding call (`embed_in_update_s == 0.0`), verifying that `on_inserted` reuses the vector computed in `shortlist`. When `uses_embeddings=False`, asserts exactly zero embedding calls in both phases.
6. **Repeated insertions:** Successive calls to `insert_node()` correctly expose newly added nodes as candidates for subsequent insertions.
7. **Embedder identity contract ([D-28]):** The exact `MeteredEmbedder` passed to `setup()` is stored as `strategy._embedder` (verified for embedding strategies; bypassed for non-embedding strategies where `_embedder is None`).
8. **Max candidates bound ([D-41]):** If the strategy defines `max_candidates(n_existing)`, verifies `len(shortlist.candidates) <= max_candidates(n_existing)` across all shortlisting steps.
