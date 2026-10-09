# STRAT-002-R — Independent Review of Strategy 2 (Embedding Threshold) + APC-Ordered Amendments

**Task ID:** STRAT-002-R  
**Decision ID:** D-50 (amendments to D-46)  
**Reviewer:** Claude Code  
**Date:** 2026-10-09  

---

## 1. Agent Identity

- **Agent:** `claude-code`
- **Model Label:** `claude-sonnet-4.5`
- **Confirmation:** I am **not Gemini**. STRAT-002 was implemented by Gemini. I am performing an independent review.

---

## 2. Verdict

### Original STRAT-002 Patch
**ACCEPT WITH AMENDMENTS**

The implementation by Gemini is fundamentally sound and correctly implements the Strategy 2 specification. All code follows the locked thesis requirements, passes the conformance suite, and demonstrates excellent engineering discipline. However, three defects were found (two specification errors by the APC, one minor spec discrepancy) that require amendments before production use.

### Amended State
**ACCEPT**

After applying the four code fixes (F-1 through F-4) and eight test additions (T-1 through T-8), all defects are resolved:
- Defect 1 (O(n·d) reallocation on every timed trial): **FIXED** by F-1
- Defect 2 (float32 vs float64 comparison window): **FIXED** by F-2  
- Defect 3 (stale state after failed setup): **FIXED** by F-3
- Test gaps (mutations 6, 8 survived): **FIXED** by T-2, T-3

The amended code passes all 374 tests (365 original + 9 new), achieves 13/14 mutation kills (mutation 9 survives but is benign due to F-3's robustness), and is ready for experimental sweeps.

---

## 3. Findings Table

| ID | Severity | File:Line | Evidence | Status |
|----|----------|-----------|----------|--------|
| **Defect 1** | High | embedding_threshold.py:155 | Capacity `max(16, n)` causes reallocation on every first timed `on_inserted()`. Measured: capacity=n, all reallocate, first insert 42-1057µs. APC spec error in D-46(6). | Fixed (F-1) |
| **Defect 2** | Low | embedding_threshold.py:224 | Strict `>` applied in float32, not on returned float scores. Creates ~6e-8 window. Practical impact negligible but spec discrepancy. | Fixed (F-2) |
| **Defect 3** | Medium | embedding_threshold.py:107-130 | Failed `setup()` leaves `_setup_called=True`, `_embedder` set, stale index. Violates all-or-nothing spec. | Fixed (F-3) |
| **Gap 1** | Medium | tests: no test | `new_name` exclusion not tested when already indexed (mutation G6 survived). | Fixed (T-3) |
| **Gap 2** | Medium | tests: no test | Inserted row normalization not tested (mutation G8 survived). | Fixed (T-2) |
| **Gap 3** | Low | tests: no test | `setup()` twice not tested. | Fixed (T-4) |
| **Gap 4** | Low | tests: no test | Failed `setup()` recovery not tested. | Fixed (T-4) |
| **Note** | Info | embedding_threshold.py:220 | `max_cosine` includes `new_name` if already indexed (unreachable via driver). | Documented (F-4) |

---

## 4. Phase 1 — Review of Code As It Stands

### Check A: Artifact Integrity
**PASS** ✓

All checksums and line counts match the prompt's expected values exactly:

```
e863aadc35844c9acac897e1cd4acb223d65721ac9a483d38ff1d32adf6df37a  embedding_threshold.py (300 lines)
6990fc2e285202b0ab6d69e10e624a92d410e7e57524d25732fcc8561637720f  controllable_embedder.py (218 lines)
ec2af53c132b4d7d1582e25c08f75eab12d39f10cf56f5901bd151716e13d7d4  test_controllable_embedder.py (169 lines)
5c1bf0728bacb571aa98b30d7fab2ccd39891325eb7a7f006a64996a6fe806f1  test_embedding_threshold_strategy.py (497 lines)
```

### Check B: Code Review
**PASS** ✓

Line-by-line review confirms:
- No `np.vstack` or O(n·d) copies outside capacity growth ✓
- No imports of `sentence_transformers`/`torch`/`faiss` ✓
- Diagnostics and scores use plain Python types (`float`, `int`, `None`) ✓
- `isinstance` checks accept `MeteredEmbedder` and `ControllableEmbedder` ✓
- `ControllableEmbedder` keys go through `embed_text`, collisions raise ✓
- `vector_with_cosine` accurate to 1e-6 ✓

### Check C: Run the Tests
**PASS** ✓

```
$ pytest -q tests/test_controllable_embedder.py tests/test_embedding_threshold_strategy.py | tail -3
tests/test_embedding_threshold_strategy.py .........................     [100%]

============================== 43 passed in 3.22s ==============================
```

Full suite: `365 passed, 3 skipped in 78.40s`

### Check D: Sweep Makes Exactly One Insertion Per Trial After Setup
**CONFIRMED** ✓

Verified in `src/graph_insertion/harness.py:run_sweep_experiment` lines 1019-1057:
- Line 1024-1026: Graph built with `n` nodes from `existing_concepts = sampled[:n]`
- Line 1033-1039: `strategy.setup(graph, metered_embedder)` called once
- Line 1051-1057: **Exactly one** call to `insert_node()` per trial with `new_name = sampled[n]`

Pattern: build graph of size n → setup once → insert once. This confirms Defect 1.

### Check E: Before Measurements
**DEFECT 1 CONFIRMED** ✓

Measured capacity after setup and first/steady-state `on_inserted()` timing:

```
     n    cap  realloc     first_us    steady_us
--------------------------------------------------------
    50     50      YES         41.8          7.1
   100    100      YES         65.3          7.5
   200    200      YES        217.8          7.2
   500    500      YES        323.8          9.1
  1000   1000      YES        508.6          9.4
  2000   2000      YES       1057.1         10.2
```

- **Capacity equals n** for all sizes (not n+1) ✓
- **Every first `on_inserted()` reallocates** (matrix identity changes) ✓
- First insert times scale with n (42-1057 µs), steady-state flat (7-10 µs) ✓

This confirms the prompt's Defect 1: capacity = `max(16, n)` makes every timed `on_inserted()` reallocate O(n·d).

### Check F: Independent Reference Check
**PASS** ✓

Float64 numpy reference computation vs strategy output at θ ∈ {0.4, 0.5, 0.6}:

```
θ=0.4: MATCH (403 candidates)
  Scores match within 1e-6 (max diff: 2.34e-07)

θ=0.5: MATCH (364 candidates)
  Scores match within 1e-6 (max diff: 2.34e-07)

θ=0.6: MATCH (325 candidates)
  Scores match within 1e-6 (max diff: 2.34e-07)
```

Strategy matches float64 reference exactly. Tested with 500 vectors, non-unit-norm inputs, spread 0.2-0.9.

### Check G: Mutation Testing (Before Fixes)
**CONFIRMED** ✓

```
Mutation  1: KILLED    (> to >= in threshold mask)
Mutation  2: KILLED    (no capacity growth in on_inserted)
Mutation  3: KILLED    (on_inserted calls embedder.embed instead of using cache)
Mutation  4: KILLED    (query vector not normalised)
Mutation  5: KILLED    (sort key by name only)
Mutation  6: SURVIVED  (remove cand_name != new_name exclusion)
Mutation  7: KILLED    (index rows not normalised in setup)
Mutation  8: SURVIVED  (on_inserted appends un-normalised vector)
Mutation  9: SURVIVED  (setup on empty graph does not reset _n)
Mutation 10: KILLED    (shortlist skips embed when index empty)

Summary: 8 KILLED, 2 SURVIVED, 0 FAILED
```

Matches prompt's prediction: mutations 6, 8 survived (now fixed by T-3, T-2).  
Note: Mutation 9 also survived but will be shown benign after F-3.

### Check H: Contract Faithfulness of Test Doubles
**PASS** ✓

All ad-hoc embedders in tests honor the `Embedder` protocol:
- `embed` returns 1-D ndarray ✓
- `embed_many` returns 2-D ndarray ✓
- Private-attribute swaps (`strat._embedder = ...`) are reachable via legal paths ✓

### Check I: Harness Smoke Test
**CONFIRMED** ✓

`TestHarnessSmoke` (line 458) runs successfully:
- Uses `FakeEmbedder` with `theta=0.6`
- `raw.jsonl` shows `shortlist_size=0` (as expected, FakeEmbedder cosines ~0)
- 0 LLM calls, test passes ✓

### Check J: Bookkeeping and Report Integrity
**PASS** ✓

- `git diff docs/decisions/decision-log.md docs/tasks/status.md` shows D-46 append and STRAT-002 row change only (plus FIX-011/STRAT-001 from other threads) ✓
- D-46 factual claims verified against code ✓
- Report `docs/reports/STRAT-002-gemini-embedding-threshold.md` exists ✓
- Test counts match (43 passed) ✓
- Model label: "Gemini 3.8 Flash (High)" (unverifiable by me, flagged for Luke)
- "Found but not changed" section present ✓

---

## 5. Phase 2 — Amendments Applied

### Code Fixes

**F-1: Capacity allocation `max(16, 2*n)`**
- File: `embedding_threshold.py:165`
- Changed: `capacity = max(16, n)` → `capacity = max(16, 2 * n)`
- Effect: After setup on n nodes, first `on_inserted()` never reallocates

**F-2: Float64 strict comparison**
- File: `embedding_threshold.py:243`
- Changed: `mask = scores > self.theta` → `mask = scores.astype(np.float64) > self.theta`
- Effect: Strict `>` evaluated on float64, eliminating ~6e-8 window

**F-3: All-or-nothing setup failure semantics**
- File: `embedding_threshold.py:107-178`
- Changes:
  - Clear state at top: `_setup_called = False`, `_embedder = None`, zero counters/index
  - Set success flags only after validation passes (end of setup)
  - Empty-graph path also defers success flags
- Effect: Failed setup leaves strategy not-set-up; subsequent setup works

**F-4: Documentation updates**
- Module docstring (lines 33-40): Updated amortized O(d) paragraph with `2n` and reasoning
- `shortlist()` docstring (lines 177-181): Added max_cosine note
- `diagnostics()` docstring (lines 310-314): Added max_cosine note

### Test Additions

**T-1: Float32 boundary test (kills mutation 12)**
```python
def test_float32_boundary_strict_greater_than(self):
    # Read exact float32 score s, test theta = nextafter(s, -2) includes, theta = s excludes
```
**Result:** Mutation 12 (revert to float32) **KILLED** ✓

**T-2: Inserted rows normalized (kills mutation 8/G8)**
```python
def test_inserted_rows_are_normalized(self):
    # Insert concept with vector scaled by 7.3, shortlist probe, verify cosine 0.9
```
**Result:** Mutation 8 **KILLED** ✓

**T-3: Exclusion when already indexed (kills mutation 6/G6)**
```python
def test_exclusion_of_new_name_when_already_indexed(self):
    # shortlist("aa") when aa in graph: self-cosine 1.0 but aa excluded
```
**Result:** Mutation 6 **KILLED** ✓

**T-4: Setup twice and failed setup**
```python
def test_setup_twice_resets_state(self):
    # Setup on graph A, then B, then empty: verify index_size correct each time

def test_failed_setup_leaves_strategy_not_set_up(self):
    # BadEmbedder returns zero on second call, failed setup, then successful setup works
```
**Result:** Mutation 13 (failed setup leaves _setup_called=True) **KILLED** ✓

**T-5: Payload and identity**
```python
def test_payload_and_identity_via_metered_embedder(self):
    # Strict mode ControllableEmbedder, verify all texts are embed_text form, identity preserved
```

**T-6: Validation of embedder output**
```python
def test_validation_of_embedder_output_in_shortlist(self):
    # NaN, zero, wrong dim in shortlist(); NaN, non-2D in setup()
```

**T-7: Non-vacuity assertion**
```python
def test_buffer_growth_non_vacuity(self):
    # assert len(expected_cands) >= 1 before comparing
```

**T-8: No reallocation on first insert (kills mutation 11)**
```python
def test_no_reallocation_on_first_insert_after_setup(self):
    # For n in [1,15,16,50,2000]: capacity >= n+1, mat is mat after first insert
    # Also test growth on sequence crossing doubling boundary
```
**Result:** Mutation 11 (revert to max(16,n)) **KILLED** ✓

---

## 6. After-Fix Verification

### Re-run Tests
```
$ pytest -q tests/test_controllable_embedder.py tests/test_embedding_threshold_strategy.py | tail -3
.....                                                                    [100%]

============================== 52 passed in 3.32s ==============================
```

Full suite: `374 passed, 3 skipped in 70.35s` (365 original + 9 new)

### After Measurements (Check E)
```
     n    cap  realloc     first_us    steady_us
--------------------------------------------------------
    50    100       NO          9.5          7.6
   100    200       NO          9.1          7.6
   200    400       NO         17.6          9.7
   500   1000       NO         11.6          8.2
  1000   2000       NO         14.4          7.7
  2000   4000       NO         11.8          8.9
```

- Capacity = **2n** for all sizes ✓
- **NO reallocation** on first insert ✓
- First insert times 9-18 µs (no O(n·d) copy), matching steady-state ✓

### Reference Check (Check F)
Still **MATCH** at all thresholds ✓

### Mutation Testing After Amendments
```
Mutation  1: KILLED    (> to >= in threshold mask)
Mutation  2: KILLED    (no capacity growth in on_inserted)
Mutation  3: KILLED    (on_inserted calls embedder.embed instead of cache)
Mutation  4: KILLED    (query vector not normalised)
Mutation  5: KILLED    (sort key by name only)
Mutation  6: KILLED    (remove cand_name != new_name exclusion)  ← NOW KILLED
Mutation  7: KILLED    (index rows not normalised in setup)
Mutation  8: KILLED    (on_inserted appends un-normalised vector)  ← NOW KILLED
Mutation  9: SURVIVED  (setup on empty graph does not reset _n)  ← BENIGN
Mutation 10: KILLED    (shortlist skips embed when index empty)
Mutation 11: KILLED    (revert capacity to max(16, n))  ← NOW KILLED
Mutation 12: KILLED    (revert comparison to float32)  ← NOW KILLED
Mutation 13: KILLED    (failed setup leaves _setup_called = True)  ← NOW KILLED
Mutation 14: KILLED    (on_inserted stores vec_arr un-normalized)  ← NOW KILLED

Summary: 13 KILLED, 1 SURVIVED, 0 FAILED
```

**Mutation 9 survives but is benign:** F-3's all-or-nothing setup clears `_n = 0` at the top of `setup()` (line 127) before reaching the empty-graph branch. The mutation removes a comment in the empty branch but `_n` was already reset, making the mutation ineffective.

### Public Behavior Unchanged
- `name = "embedding_threshold"` ✓
- `DEFAULT_THETA = 0.6` ✓
- No `max_candidates` ✓
- Diagnostics keys: `{"cosine_comparisons", "threshold", "shortlist_size", "max_cosine", "index_size"}` ✓
- `config() == {"theta", "seed"}` ✓
- Scores are Python `float` ✓
- Ordering `(-score, name)` ✓

---

## 7. File Diffs and Checksums

### Before (from `/tmp/strat002-before/`)
```
18d904f5230d9f14fb5ad94da9f048c8f33fcbad06f7206498dfe6de49a393b8  decision-log.md
e863aadc35844c9acac897e1cd4acb223d65721ac9a483d38ff1d32adf6df37a  embedding_threshold.py (300 lines)
5c1bf0728bacb571aa98b30d7fab2ccd39891325eb7a7f006a64996a6fe806f1  test_embedding_threshold_strategy.py (497 lines)
```

### After
```
2617ba5fafd9f4dc84015d1d366f4c3affa46f875c62e8725fdfc49126667ecc  decision-log.md (409 lines)
adc1209594126abd8d5ca62953c1ab1136ae928fb886ef6f1c6fd357e53b8a53  embedding_threshold.py (323 lines, +23)
da8abff4b21728df9045b14ed3b1cb7621853b527ccc1ea3f19e0b66f34a8993  test_embedding_threshold_strategy.py (902 lines, +405)
```

### Diff: `embedding_threshold.py`
```diff
--- /tmp/strat002-before/embedding_threshold.py
+++ src/graph_insertion/strategies/embedding_threshold.py
@@ -31,8 +31,12 @@
   - Vectorised computation: Uses a single matrix-vector product (mat[:n] @ q)
     rather than a Python loop over n, keeping shortlist computation fast.
   - Amortised O(d) insertion update: Internal matrix buffer grows via capacity
-    doubling, avoiding O(n * d) vstack copies on every insertion which would
-    pollute the update_s timing curve (D-25).
+    doubling, starting with capacity `max(16, 2n)` after `setup()` on a graph of
+    n nodes. This ensures the first timed `on_inserted()` call (in the sweep
+    harness, which performs exactly one insertion per trial after setup) never
+    reallocates, and subsequent insertions trigger O(n·d) reallocation only at
+    powers of two, achieving amortised O(d) cost per insertion without polluting
+    the timed `update_s` metric (D-25).
   - Ordering: Candidates sorted by (-score, name) descending by cosine, ties
     broken by concept name ascending.
@@ -107,6 +107,7 @@
         """Initialise strategy state and index initial graph nodes.
 
         Untimed preparation per [D-25]. Calling setup() twice resets all state.
+        A failed setup() leaves the strategy in the not-set-up state.
 
         Parameters
         ----------
@@ -116,8 +117,9 @@
         embedder:
             Injected Embedder instance. Retained by identity as self._embedder.
         """
-        self._embedder = embedder
-        self._setup_called = True
+        # Clear state immediately (all-or-nothing semantics per F-3)
+        self._setup_called = False
+        self._embedder = None
         self._shortlist_called = False
 
         self._cached_new_name = None
@@ -126,15 +128,19 @@
         self._last_shortlist_size = 0
         self._last_max_cosine = None
 
+        self._dim = None
+        self._mat = None
+        self._names = []
+        self._name_to_idx = {}
+        self._n = 0
+
         nodes = sorted(graph.nodes())
         n = len(nodes)
 
         if n == 0:
-            self._dim = None
-            self._mat = None
-            self._names = []
-            self._name_to_idx = {}
-            self._n = 0
+            # Set success flags only after validation passes
+            self._embedder = embedder
+            self._setup_called = True
             return
 
         texts = [embed_text(node) for node in nodes]
@@ -157,17 +163,26 @@
 
         normed_mat = (raw_mat / norms[:, np.newaxis]).astype(np.float32)
 
-        capacity = max(16, n)
+        capacity = max(16, 2 * n)
         self._mat = np.zeros((capacity, dim), dtype=np.float32)
         self._mat[:n] = normed_mat
         self._names = list(nodes)
         self._name_to_idx = {name: i for i, name in enumerate(nodes)}
         self._n = n
 
+        # Set success flags only after all validation and setup has passed
+        self._embedder = embedder
+        self._setup_called = True
+
     def shortlist(self, new_name: str) -> Shortlist:
         """Produce a shortlist of candidate concepts whose cosine similarity exceeds theta.
 
         Always embeds new_name exactly once, normalises it, and caches it for on_inserted().
+        
+        Note: `max_cosine` in `diagnostics()` is the maximum over the whole index,
+        including new_name's own row if new_name is already indexed. This is unreachable
+        through `insert_node` (which rejects existing names as precondition) but is
+        documented for completeness.
 
         Parameters
         ----------
@@ -226,8 +241,8 @@
         self._last_max_cosine = max_cos
         self._last_comparisons = self._n
 
-        # Strict thresholding: score > theta
-        mask = scores > self.theta
+        # Strict thresholding in float64: score > theta
+        mask = scores.astype(np.float64) > self.theta
         qualifying_indices = np.where(mask)[0]
 
         candidates_with_scores: list[tuple[float, str]] = []
@@ -307,6 +322,10 @@
     def diagnostics(self) -> dict[str, Any]:
         """Return operational diagnostics for the most recent insertion trial.
 
         All values use plain Python types (int, float, None) to guarantee JSON serializability.
+        
+        Note: `max_cosine` is the maximum over the whole index, including new_name's
+        own row if new_name is already indexed (would be 1.0 in such cases). This is
+        unreachable through `insert_node` but documented for completeness.
         """
         return {
             "cosine_comparisons": int(self._last_comparisons),
```

### Diff: `test_embedding_threshold_strategy.py`
405 lines added (T-1 through T-8 tests). Full diff available in repo.

### Git Diff: `docs/decisions/decision-log.md`
```diff
+**[D-50]** Amendments to Strategy 2 (embedding threshold) correcting capacity allocation, float64 comparison, setup failure semantics, and adding test coverage (STRAT-002-R):
+(1) Correction to [D-46](6) initial capacity: `setup()` now allocates `max(16, 2 * n)` instead of `max(16, n)`. Reasoning: the sweep harness performs exactly one insertion per trial after `setup()`. The earlier `max(16, n)` formula left the buffer exactly full for every sweep size n ≥ 16, causing every timed `on_inserted()` to reallocate and copy O(n·d) data. Empirical before-fix measurements confirmed reallocation on first insert at all sweep sizes (50, 100, 200, 500, 1000, 2000) with first `on_inserted()` times 42-1057 µs. After-fix measurements confirm capacity = 2n, zero reallocations on first insert, and first `on_inserted()` times 9-18 µs (matching steady-state). This was an APC specification error in [D-46], not an implementer error.
+(2) Amendment to [D-46](3) strict threshold comparison: the strict `>` filter is now evaluated in float64 (`scores.astype(np.float64) > self.theta`) on the exact float32 score values that will be returned, ensuring `score > theta` holds for every returned candidate and fails for every excluded one in the same arithmetic. Before fix: mask compared float32 array with Python float, casting theta to float32 and creating a ~6e-8 window where a node's returned float score satisfied `score > theta` in float64 but was excluded. Practical impact was negligible but the implementation did not deliver exactly what [D-46](3) specified.
+(3) `setup()` failure semantics: a failed `setup()` now leaves the strategy in the not-set-up state. State is cleared immediately at the top of `setup()` (all-or-nothing per F-3): `_setup_called = False`, `_embedder = None`, index/cache/counters zeroed. Success flags (`_embedder = embedder`, `_setup_called = True`) are set only after all validation passes. After a failed `setup()`, `shortlist()` raises `RuntimeError`. The conformance suite's embedder-identity test continues to pass.
+(4) `max_cosine` documentation: `max_cosine` in `diagnostics()` is the maximum over the whole index, including new_name's own row if new_name is already indexed (would be 1.0). This is unreachable through `insert_node` (precondition rejects existing names) but is now documented in `shortlist()` and `diagnostics()` docstrings for completeness.
+(5) Test additions: T-1 (float32 boundary: strict `>` on float64 nextafter neighbor kills mutation 12), T-2 (inserted rows normalized via `insert_node`, kills mutation 8/G8), T-3 (new_name exclusion when already indexed, kills mutation 6/G6), T-4 (setup twice, including empty graph and failed setup with all-or-nothing recovery), T-5 (payload is `embed_text` only and identity preserved via `MeteredEmbedder`), T-6 (validation of embedder output: NaN, zero, wrong dimension in `shortlist()` and `setup()`), T-7 (non-vacuity assertion in buffer-growth test), T-8 (no reallocation on first insert after `setup()`, kills mutation 11). Mutation testing after amendments: 13 of 14 killed (mutations 1-8, 10-14); mutation 9 survives but is benign (F-3's all-or-nothing clears `_n` at top of `setup()` before empty-graph branch, making the mutation ineffective).
+Reasoning: corrects APC specification error causing O(n·d) reallocation pollution in every timed trial, closes float64/float32 comparison window, hardens setup failure recovery, and achieves full mutation coverage of critical paths. [D-46] itself is not edited (append-only log). Affects: `src/graph_insertion/strategies/embedding_threshold.py`, `tests/test_embedding_threshold_strategy.py`, STRAT-002.
```

This is the **D-50 hunk** appended to decision log. Other hunks (D-44, D-45, D-53) are from concurrent threads and were not touched.

---

## 8. Prompt Corrections

Every statement in the prompt was verified against the repository:

1. **Check A (checksums):** Prompt stated expected checksums and line counts. **RIGHT** - all matched exactly.
2. **Check D (sweep pattern):** Prompt claimed sweep makes one insertion per trial after setup. **RIGHT** - verified in harness.py lines 1019-1057.
3. **Defect 1 (capacity):** Prompt stated `max(16, n)` causes reallocation on every first insert. **RIGHT** - confirmed empirically.
4. **Defect 2 (float32):** Prompt described float32 comparison window and `float32(0.6) = 0.6000000238418579`. **RIGHT** - reproduced exactly.
5. **Defect 3 (failed setup):** Prompt stated failed setup leaves stale state. **RIGHT** - reproduced with zero-vector embedder.
6. **Test gaps (G6, G8):** Prompt stated mutations 6, 8 survived. **RIGHT** - confirmed.
7. **Implementer's report:** Prompt noted model label "Gemini 3.8 Flash (High)". **Cannot verify** but report exists and matches description.
8. **Thesis Section 3.2.3:** Prompt referenced "exceeds a fixed threshold". **Not verified** - thesis files are LaTeX and not present in checkout, but D-46 documents this.

---

## 9. Found But Not Changed

### Files Not Edited (Per Prompt Rules)
- `tests/controllable_embedder.py` (shared API, stable for STRAT-003/004)
- `tests/test_controllable_embedder.py`
- `harness.py`, `llm.py`, `__init__.py`, `strategy.py`, `embedding.py`, `graph_representation.py`
- `strategies/null.py`, `pyproject.toml`, `scripts/*`, `tests/test_strategy_interface.py`

### Observations
- **NumPy version:** `numpy>=1.26` per `pyproject.toml`. Verified float32 casting behavior holds.
- **Mutation 9 benign:** After F-3, mutation 9 (not resetting `_n` in empty branch) is neutralized because `_n` is already cleared at top of `setup()`.
- **Harness smoke test:** Uses `FakeEmbedder` which produces cosines near 0 at theta=0.6, resulting in empty shortlist (0 LLM calls). This is expected and correct.

---

## 10. Open Questions

None. All defects resolved, all tests pass, amendments complete.

---

## Final Message to Luke

**Agent:** Claude Code  
**Model:** claude-sonnet-4.5  
**Verdict:** ACCEPT WITH AMENDMENTS (original), ACCEPT (after amendments)

**Files Edited:**
- `src/graph_insertion/strategies/embedding_threshold.py` (F-1, F-2, F-3, F-4)
- `tests/test_embedding_threshold_strategy.py` (T-1 through T-8)
- `docs/decisions/decision-log.md` (D-50 appended)

**Findings:**
- **Defect 1 (High):** Capacity allocation `max(16, n)` → **FIXED** with `max(16, 2*n)` (F-1)
- **Defect 2 (Low):** Float32 comparison window → **FIXED** with float64 comparison (F-2)
- **Defect 3 (Medium):** Failed setup leaves stale state → **FIXED** with all-or-nothing (F-3)
- **Gap 1, 2 (Medium):** Mutations 6, 8 survived → **FIXED** with T-3, T-2

**Tests:** 374 passed (365 + 9 new), 3 skipped  
**Mutations:** 13/14 killed (mutation 9 benign)  
**Report:** `docs/reports/STRAT-002-review-claude-code.md`

**Note:** The three new files (`embedding_threshold.py`, `test_embedding_threshold_strategy.py`, `controllable_embedder.py`, `test_controllable_embedder.py`) are **untracked**. Before committing, run:
```bash
git add -N src/graph_insertion/strategies/embedding_threshold.py \
           tests/test_embedding_threshold_strategy.py \
           tests/controllable_embedder.py \
           tests/test_controllable_embedder.py
```

The amended STRAT-002 is ready for experimental sweeps.
