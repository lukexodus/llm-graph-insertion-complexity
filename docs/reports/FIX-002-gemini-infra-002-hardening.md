# FIX-002: Hardening Pass on INFRA-002 Strategy Interface

**Task ID:** FIX-002  
**Agent:** Gemini  
**Date:** 2026-10-03  
**Status:** Complete  

---

## 1. Executive Summary

Task `FIX-002` performed a hardening pass on the candidate-narrowing strategy interface and driver introduced in `INFRA-002`. All six focus areas identified by the APC AI review were verified directly against the repository, addressed with minimal and robust code changes, and validated with an expanded test suite (74 tests passing, up from 62).

Key improvements delivered:
1. **Pre-mutation edge validation:** Decided edges are validated before modifying `ConceptGraph`. Decided edges must be canonical 2-tuples involving `new_name`, non-self-loops, unique (no duplicates), and have their other endpoint present in `shortlist.candidates`. Violations raise `ValueError` and leave `ConceptGraph` and strategy state strictly untouched.
2. **Shortlist contract enforcement in driver:** Candidate lists returned from `strategy.shortlist()` are validated to ensure they form a duplicate-free subset of current graph nodes, exclude `new_name`, and align in length with `scores` if provided.
3. **Embedder accounting and single-embedding invariant ([D-26]):** Made `metered_embedder: Optional[MeteredEmbedder]` a required keyword-only argument in `insert_node()`. If `None`, unmetered embedding activity is detected and rejected with `RuntimeError`. Strategies compute and cache `new_name`'s embedding during `shortlist()`, reusing it during `on_inserted()`. `InsertionMetrics` tracks `embed_in_update_s` (enforcing `0.0`).
4. **D-21 text payload verification:** Added `record_texts: bool = False` and `texts_log: Optional[list[str]]` to `MeteredEmbedder`, verifying in conformance tests that all embedded strings equal `embed_text(c)` for some concept $c$ in the trial (lowercase, no raw underscores, no domain descriptions).
5. **Reusable conformance test suite:** Factored base test logic into `StrategyConformanceSuite` with a documented `strategy_factory` fixture pattern so STRAT-001 through STRAT-004 can inherit directly. Strengthened the repeated-insert test to verify that previous inserts become candidates for subsequent inserts.
6. **Diagnostics error capture and timing precision:** Wrapped strategy diagnostics retrieval in try-except capturing `{"diagnostics_error": repr(e)}`. Added `apply_s` timing to `InsertionMetrics`, ensuring complete timing attribution where `total_s ≈ shortlist_s + decide_s + apply_s + update_s` (slack $< 0.02$s).

---

## 2. Verification of APC AI Claims

| APC Claim | Direct Repo Verification | Result |
| :--- | :--- | :--- |
| **1. Edge validation occurs during/after mutation** | Checked `src/graph_insertion/strategy.py`: `insert_node` previously called `graph.add_node(new_name)` and iterated over `outcome.edges` calling `graph.add_prereq_edge(u, v)`. If an edge was invalid or raised an exception mid-iteration, `new_name` and prior edges remained in the graph, and edges outside the shortlist were not checked. | **Confirmed.** Fixed: all edges validated against `shortlist.candidates` before any graph mutation occurs. |
| **2. Shortlist contract not enforced by driver** | Checked `insert_node`: accepted any `Shortlist` returned from `strategy.shortlist()`, trusting candidate membership, uniqueness, exclusion of `new_name`, and score length alignment. | **Confirmed.** Fixed: driver validates shortlist integrity prior to invoking the decision step. |
| **3. Embedder accounting does not cover `on_inserted`** | Checked `insert_node`: `metered_embedder` was optional positional, and embedding metrics were only sampled across `strategy.shortlist()`. Any embedding call inside `strategy.on_inserted()` was unmetered. | **Confirmed.** Fixed: `metered_embedder` is keyword-only; embedding delta is tracked across both `shortlist()` and `on_inserted()`, with `embed_in_update_s` explicitly verified to be `0.0`. |
| **4. [D-21] not enforced in tests** | Checked `MeteredEmbedder`: tracked call counts and durations, but discarded the input text strings, making it impossible to assert D-21 text compliance. | **Confirmed.** Fixed: added `record_texts` and `texts_log` to `MeteredEmbedder` and added `test_d21_text_payload_compliance`. |
| **5. Conformance suite tightly coupled to fake strategy** | Checked `tests/test_strategy_interface.py`: test methods directly instantiated `TinyFakeStrategy` rather than using an extensible base class. | **Confirmed.** Fixed: created `StrategyConformanceSuite` base class parameterized via `strategy_factory` fixture. |
| **6. Silent diagnostic failure and missing `apply_s`** | Checked `insert_node`: bare `except Exception: extra = {}` silently swallowed errors; graph mutation time was unmeasured, leaving unaccounted slack in `total_s`. | **Confirmed.** Fixed: records `{"diagnostics_error": repr(e)}` and measures `apply_s`. |

---

## 3. Implementation Details

### A. `src/graph_insertion/embedding.py`
- Added `record_texts: bool = False` parameter to `MeteredEmbedder.__init__`.
- Maintained `texts_log: Optional[list[str]]` containing strings passed to `embed()` and `embed_many()`.
- Resetting `MeteredEmbedder` clears `texts_log` back to `[]`.

### B. `src/graph_insertion/strategy.py`
- Added `apply_s: float` and `embed_in_update_s: float = 0.0` to `InsertionMetrics`.
- Updated signature of `insert_node`:
  ```python
  def insert_node(
      strategy: NarrowingStrategy,
      graph: ConceptGraph,
      decision_step: DecisionStep,
      new_name: str,
      *,
      metered_embedder: Optional[MeteredEmbedder],
  ) -> InsertionResult:
  ```
- **Shortlist validation:** Ensures `candidates` is a tuple of existing graph nodes, has no duplicates, excludes `new_name`, and matches `scores` length if `scores` is provided.
- **Edge validation:** Validates `outcome.edges` before mutating `graph`. Enforces canonical 2-tuples `(u, v)`, no self-loops, no duplicate edges, at least one endpoint matching `new_name`, and the other endpoint present in `shortlist.candidates`.
- **Pre-mutation failure semantics:** If edge or shortlist validation fails, `ConceptGraph` is not touched and `strategy.on_inserted()` is never invoked.
- **Unmetered detection:** If `metered_embedder=None`, checks if `getattr(strategy, "_embedder", None)` is a `MeteredEmbedder` whose call count increases during insertion; if so, raises `RuntimeError`.
- **Timing and diagnostics:** Measures `apply_s` around graph mutation and captures `diagnostics_error` on telemetry exception.

### C. `tests/test_strategy_interface.py`
- Updated `TinyFakeStrategy` to cache `_cached_new_vec` in `shortlist()` and consume it in `on_inserted()`, eliminating re-embedding.
- Extracted `StrategyConformanceSuite` with 6 standard conformance tests:
  1. `test_shortlist_is_subset_and_excludes_new_node`
  2. `test_shortlist_does_not_mutate_graph`
  3. `test_same_seed_gives_same_shortlist`
  4. `test_d21_text_payload_compliance`
  5. `test_cached_embedding_reuse_single_embedding_per_insert`
  6. `test_repeated_inserts_see_previous_nodes`
- Added `TestInsertNodeShortlistEnforcement` (4 tests).
- Added `TestInsertNodeEdgeValidation` (5 tests).
- Added `TestInsertNodeTimingAndMetrics` (6 tests).

---

## 4. Verification & Test Results

The full test suite was executed:
```bash
PYTHONPATH=src pytest
```
Output:
```
74 passed in 2.64s
```
All existing tests from `INFRA-001` and `FIX-001` (40 tests) continue to pass cleanly, and all 34 interface and hardening tests pass.

---

## 5. Diffs of Edited Shared Docs

### A. `docs/context/strategy-interface.md`
```diff
@@ -54,17 +54,21 @@
    # Note: Trial isolation requires a fresh strategy instance and a deep copy of the graph (graph.copy()).
 
 3. Incremental Insertion (TIMED via insert_node):
-   result = insert_node(strategy, graph, decision_step, new_concept, metered_embedder)
+   result = insert_node(strategy, graph, decision_step, new_concept, metered_embedder=metered_embedder)
    ├─ Step 1: strategy.shortlist(new_concept)          --> Shortlist(candidates, scores)
+   │          (Driver validates candidates: must be subset of existing nodes, no duplicates, excludes new_concept)
    ├─ Step 2: decision_step.decide(...)                --> DecisionOutcome(edges, llm_calls, llm_seconds)
    │          (Empty shortlist skips LLM calls: 0 calls, 0 edges)
-   ├─ Step 3: driver adds new_concept and edges to ConceptGraph
-   └─ Step 4: strategy.on_inserted(new_concept, edges) --> Incremental index update
-```
-
----
-
-## 3. Timing & Metrics Accounting Model ([D-25])
+   ├─ Step 3: driver validates edges and mutates ConceptGraph (timed via apply_s):
+   │          (Validates: canonical 2-tuples, no self-loops, no duplicates, other endpoint in shortlist.candidates)
+   │          (Adds new_concept and applies decided edges to ConceptGraph)
+   └─ Step 4: strategy.on_inserted(new_concept, edges) --> Incremental index update (timed via update_s)
+              (Reuses cached vector from Step 1; must NOT re-embed new_concept)
+```
+
+---
+
+## 3. Timing & Metrics Accounting Model ([D-25], [D-26])
 
 All timing uses `time.perf_counter()`. Measurements are reported inside `InsertionMetrics`:
 
@@ -74,13 +74,18 @@
 | `llm_calls` | Number of LLM API requests made | `outcome.llm_calls` (0 if shortlist is empty) |
 | `embedding_calls` | Number of embedding calls during narrowing | Recorded via `MeteredEmbedder` delta during shortlist |
 | `embed_s` | Cumulative seconds generating embeddings | From `MeteredEmbedder` during shortlist |
+| `embed_in_update_s` | Cumulative seconds generating embeddings during update | From `MeteredEmbedder` during `on_inserted` (must be 0.0 under single-embedding invariant) |
 | `shortlist_s` | Wall-clock seconds for candidate narrowing | `t1 - t0` around `strategy.shortlist()` (subsumes `embed_s`) |
 | `decide_s` | Wall-clock seconds in shared decision step | `t3 - t2` around `decision_step.decide()` (0.0 if empty shortlist) |
-| `update_s` | Wall-clock seconds updating strategy index | `t5 - t4` around `strategy.on_inserted()` |
-| `total_s` | Total wall-clock seconds for insertion | Measured end-to-end across Steps 1–4 (subsumes all above) |
-| `extra` | Diagnostic metadata dictionary | Emitted by `strategy.diagnostics()` |
-
-*Note on exclusions:* `setup()` is strictly untimed preparation and excluded from `total_s`.
+| `apply_s` | Wall-clock seconds committing to graph | `t5 - t4` around graph mutation and edge application |
+| `update_s` | Wall-clock seconds updating strategy index | `t7 - t6` around `strategy.on_inserted()` |
+| `total_s` | Total wall-clock seconds for insertion | Measured end-to-end across Steps 1–4 (`total_s ≈ shortlist_s + decide_s + apply_s + update_s`) |
+| `extra` | Diagnostic metadata dictionary | Emitted by `strategy.diagnostics()` (or `{"diagnostics_error": repr(e)}` on failure) |
+
+*Notes:*
+- `setup()` is strictly untimed preparation and excluded from `total_s`.
+- **Single-Embedding Invariant ([D-26]):** An insertion of `new_name` requires computing its embedding at most once. Strategies compute and cache `new_name`'s vector in `shortlist()`, and reuse that vector in `on_inserted()`. Embedding `new_name` a second time in `on_inserted()` is strictly prohibited (`embed_in_update_s` must remain 0.0).
+- **Unmetered Embedding Detection ([D-26]):** Passing `metered_embedder=None` indicates an unmetered run; if any strategy embedder performs unmetered embedding calls during insertion, `insert_node` raises `RuntimeError`.
```

### B. `docs/decisions/decision-log.md`
```diff
@@ -226,4 +226,7 @@
 **[D-24]** Strategy interface contract & lifecycle locked: candidate-narrowing strategies implement candidate shortlisting and internal index upkeep (`setup`, `shortlist`, `on_inserted`), read `ConceptGraph` immutably, and never call an LLM. Reasoning: thesis Section 3.2.6 defines the shared LLM decision step as the controlled variable held constant across all strategies; placing the decision step outside strategy modules guarantees identical prompt structure and decision mechanics while isolating the narrowing mechanism under test. Affects: INFRA-002, INFRA-004, INFRA-005, INFRA-006, STRAT-001 through STRAT-004.
 
 **[D-25]** Insertion timing and metrics accounting model locked: timed insertion covers candidate narrowing (including embedding the new concept), the shared decision step, driver graph edge application, and the strategy's incremental update (`on_inserted`). Initial graph indexing (`setup()`) is excluded as pre-trial preparation. Reasoning: matches thesis Section 3.4 measurement definition while isolating incremental insertion cost from batch initialization; breaking down `embed_s`, `shortlist_s`, `decide_s`, `update_s`, and `total_s` via `time.perf_counter()` disentangles retrieval overhead from LLM latency. Affects: INFRA-002, INFRA-004, STRAT-001 through STRAT-004.
+
+**[D-26]** Strategy interface hardening & embedder injection contract: (1) `insert_node` requires keyword-only `metered_embedder: Optional[MeteredEmbedder]`; passing `None` explicitly indicates an unmetered run, and any strategy embedding activity during such runs raises `RuntimeError`; (2) candidate shortlists are validated by the driver before invoking the decision step (candidates must be a subset of current graph nodes, contain no duplicates, and exclude the new concept); (3) decided edges are strictly validated before mutating `ConceptGraph` (edges must be canonical 2-tuples, non-self-loops, no duplicates, involve `new_name`, and have the other endpoint present in `shortlist.candidates`); failure raises `ValueError` and leaves `ConceptGraph` unchanged without notifying the strategy; (4) single-embedding invariant: strategies embedding `new_name` must compute its embedding at most once per insertion (cached in `shortlist()`, reused in `on_inserted()`), verified by `embed_in_update_s == 0.0`; (5) `apply_s` timing explicitly captures graph mutation overhead in `InsertionMetrics`, ensuring `total_s ≈ shortlist_s + decide_s + apply_s + update_s`. Reasoning: guarantees fail-fast trial isolation, protects `ConceptGraph` topology from hallucinated or invalid LLM decision edges, prevents double-embedding performance inflation in STRAT-002..004, and achieves complete timing attribution across all insertion phases. Affects: `insert_node`, `InsertionMetrics`, `StrategyConformanceSuite`, INFRA-002, FIX-002, STRAT-001 through STRAT-004.
```

### C. `docs/tasks/status.md`
```diff
@@ -69,4 +69,5 @@
 | DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md). |
 | DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; and note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked. | **open** | Prompt not yet written; can wait until after INFRA-001. |
 | FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-001-gemini-infra-001-followup.md). |
+| FIX-002 | Hardening pass on INFRA-002: edge validation before graph mutation, shortlist contract validation, required keyword-only metered_embedder, single-embedding caching and unmetered detection, texts_log for D-21 enforcement, diagnostics error handling, apply_s timing, reusable StrategyConformanceSuite. | **done** | Completed by Gemini. See report [`docs/reports/FIX-002-gemini-infra-002-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-002-gemini-infra-002-hardening.md). |
```

---

## 6. Found but Not Changed / Attention Flags

1. **Unmetered detection mechanism:**
   When `metered_embedder=None` is passed to `insert_node()`, the driver inspects `getattr(strategy, "_embedder", None)`. If that embedder is an instance of `MeteredEmbedder`, any call made on it is detected and raises `RuntimeError`. If a custom unmetered embedder (or raw `FakeEmbedder`) is used without metering, Python cannot detect calls without intrusive proxying or monkey-patching. The test suite enforces that in benchmark sweeps, all embedders wrapped in `MeteredEmbedder` obey this injection contract.
2. **Luke's reserved items preserved:**
   No decisions were made on:
   - LLM call granularity (batch prompt vs pairwise prompt).
   - Decision-step concurrency.
   - Evaluation scoring of DSA missing rows.
3. **Commit status:**
   All changes remain uncommitted in the local working copy.
