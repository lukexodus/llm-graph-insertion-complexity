# FIX-003: Follow-Up Hardening on FIX-002 (Strategy Driver)

**Agent:** Gemini  
**Task ID:** FIX-003  
**Date:** 2026-10-03  
**Status:** Completed  
**Working tree:** Uncommitted (per task instructions)

---

## 1. Executive Summary

Task FIX-003 addressed six specific discrepancies and fragility issues identified in the review of FIX-002 concerning the `insert_node` strategy driver, metrics accounting, typing, and test rigor. All claims were verified directly against the codebase. The driver was hardened to require a non-Optional `MeteredEmbedder`, enforce identity with any embedder held by the strategy prior to execution or mutation, isolate validation overhead from the operational timing equation, track discrete update embedding calls, verify setup embeddings against D-21 text formatting rules, and fix a missing typing import. All 101 tests in the repository pass cleanly.

---

## 2. Verification of Claims (Problems 1–6)

1. **Unmetered embedding error type and timing (Claim 1):**  
   *Verified.* In `src/graph_insertion/strategy.py`, the previous unmetered check raised `ValueError` (not `RuntimeError` as claimed in D-26 / FIX-002 report). Crucially, this check occurred after graph mutation (`graph.add_node`, `graph.add_prereq_edge`) and `strategy.on_inserted()` had already executed, violating fail-fast semantics and leaving a mutated graph on error.
2. **Missing `MeteredEmbedder` identity check (Claim 2):**  
   *Verified.* The driver previously accepted any `metered_embedder` without checking if it matched `strategy._embedder`. If a caller passed one meter while the strategy held another, embedding costs during narrowing were silently undercounted / reported as zero.
3. **`total_s` validation overhead inclusion (Claim 3):**  
   *Verified.* `total_s` was measured start-to-finish as wall clock time across the driver, which subsumed candidate contract validation and edge validation ($O(|\text{shortlist}|)$ operations). This caused `total_s` to exceed the documented operational sum $shortlist\_s + decide\_s + apply\_s + update\_s$.
4. **Setup embedding unverified in D-21 compliance test (Claim 4):**  
   *Verified.* `test_d21_text_payload_compliance` in `StrategyConformanceSuite` called `meter.reset()` immediately after `strategy.setup(initial_graph, meter)`, discarding the record of embeddings generated during initial graph indexing.
5. **Float duration noise in update embedding assertion (Claim 5):**  
   *Verified.* The conformance test asserted `res.metrics.embed_in_update_s == 0.0`. Floating-point durations can be non-zero due to timer jitter or clock precision, whereas discrete call counts provide an exact integer invariant.
6. **Missing `Optional` import in `embedding.py` (Claim 6):**  
   *Verified.* `src/graph_insertion/embedding.py` used `Optional[Sequence[float]]` on line 125, but `typing` only imported `Protocol, Sequence, runtime_checkable`.

---

## 3. Implemented Changes

### A. Core Strategy Driver & Metrics (`src/graph_insertion/strategy.py`)
- **Required `MeteredEmbedder`:** Changed `metered_embedder: MeteredEmbedder` to a required, non-Optional keyword-only parameter. If `metered_embedder` is `None` or not an instance of `MeteredEmbedder`, `insert_node` raises `TypeError`.
- **Pre-execution Embedder Identity Check:** At the very start of `insert_node`:
  ```python
  strat_embedder = getattr(strategy, "_embedder", None)
  if strat_embedder is not None and strat_embedder is not metered_embedder:
      raise ValueError(
          f"MeteredEmbedder mismatch: strategy {strategy.name!r} holds embedder {strat_embedder!r}, "
          f"which is not identical to metered_embedder passed to insert_node: {metered_embedder!r}. "
          "The metered_embedder passed to insert_node must be identical to the strategy's internal embedder."
      )
  ```
  If mismatched, `ValueError` is raised before calling `strategy.shortlist()` and before mutating `ConceptGraph`. Strategies without an `_embedder` (or where `_embedder is None`) accept any valid `MeteredEmbedder`.
- **Validation Timing Isolation (`validate_s`):** Shortlist contract validation and pre-mutation edge validation are timed together into `InsertionMetrics.validate_s = val_shortlist_s + val_edge_s`.
- **Operational Total Equation (`total_s`):** `total_s` is defined strictly as:
  $$\text{total\_s} = \text{shortlist\_s} + \text{decide\_s} + \text{apply\_s} + \text{update\_s}$$
  Validation overhead is excluded from `total_s` per [D-28].
- **Discrete Update Call Metric:** Added `InsertionMetrics.embedding_calls_in_update: int = 0` tracking the exact call delta during `strategy.on_inserted()`. `embed_in_update_s` is preserved.

### B. Embedding Module (`src/graph_insertion/embedding.py`)
- Imported `Optional` from `typing` alongside `Protocol, Sequence, runtime_checkable`.

### C. Test Suite Hardening (`tests/test_strategy_interface.py`)
- **D-21 Text Compliance:** Removed `meter.reset()` after `setup()`. Added explicit assertions that all concepts embedded during `setup()` and `shortlist()` match `embed_text(c)`, explicitly checking each node in `initial_graph.nodes()`.
- **Single-Embedding Invariant:** Conformance test asserts `res.metrics.embedding_calls_in_update == 0` (and `embed_in_update_s == 0.0`).
- **Embedder Validation Tests:**
  - `test_metered_embedder_none_or_invalid_raises_type_error`: verifies `TypeError` on `None` or non-`MeteredEmbedder`.
  - `test_embedder_mismatch_raises_value_error_and_graph_untouched`: verifies `ValueError` on embedder identity mismatch, asserting that `initial_graph` has no node added and edge count unchanged, and `strategy.on_inserted` was not called.
  - `test_strategy_without_embedder_accepts_any_metered_embedder`: verifies embedder-less strategies function with any valid `MeteredEmbedder`.
- **Timing Consistency:** `test_timing_components_consistency_with_apply_s` asserts:
  $$\left|\text{total\_s} - (\text{shortlist\_s} + \text{decide\_s} + \text{apply\_s} + \text{update\_s})\right| < 10^{-9}$$
  and verifies $\text{validate\_s} \ge 0.0$.
- **Telemetry and Empty-Shortlist Tests:** Updated test cases to pass valid `MeteredEmbedder` instances.

### D. Documentation & Decision Log
- **`docs/decisions/decision-log.md`:** Appended entry `[D-28]` (superseding item 1 of `[D-26]`), formalizing the non-optional embedder identity check, validation timing exclusion, and discrete update embedding metric.
- **`docs/context/strategy-interface.md`:** Updated Section 2 lifecycle snippet and Section 3 table and notes to document `validate_s`, `embedding_calls_in_update`, `total_s` operational definition, and embedder identity check.
- **`docs/tasks/status.md`:** Added `FIX-003` to Housekeeping table as `done`.

---

## 4. Found but Not Changed

1. **Reserved Architecture & Evaluation Decisions (Luke):**
   - Granularity of LLM calls (per-pair vs. batch-prompting) in INFRA-006.
   - Concurrency model for the decision step across insertion trials.
   - Missing-pair evaluation scoring for DSA (1 missing row out of $141 \times 140$).
2. **Strategy Protocol Invariance:**
   - As required, the `NarrowingStrategy` and `DecisionStep` protocols were left unchanged.
3. **Uncommitted Changes:**
   - In accordance with task instructions, all modified files remain uncommitted in the working directory.

---

## 5. Verification Results

All 101 tests across the entire test suite passed:
- `tests/test_strategy_interface.py`: 26 tests (including conformance suite, identity checking, timing equations, edge/shortlist contract validations)
- `tests/test_loader.py`: 26 tests (discovering and loading 12 corpora)
- `tests/test_graph_representation.py`: 49 tests (NetworkX wrapper, dual-mapping, GoldJudgmentSet)
