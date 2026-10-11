# STRAT-003-A — Strategy 3 Review Amendments, ef_search Calibration, and Status Relay

Task: STRAT-003-A  
Written: 2026-10-11  
Target: `src/graph_insertion/strategies/ann_retrieval.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`  
Decision ID: **[D-55]** (appended to `docs/decisions/decision-log.md`)  
Status update: `docs/tasks/status.md` (STRAT-001 and STRAT-002 rows updated to `**done**`)

---

## 1. Agent Identity

- **Agent:** `gemini`
- **Model label:** `Gemini 3.1 Pro (High)`
- **Independence confirmation:** I am **NOT** the Gemini 3.8 Flash (High) session that implemented STRAT-003 (`docs/reports/STRAT-003-gemini-ann-retrieval.md`). This follow-up task was executed independently using Gemini 3.1 Pro (High) to implement the amendments specified by the APC following independent review (`docs/reports/STRAT-003-review-gemini.md`).

---

## 2. What Was Asked / What I Did

### What was asked
1. **A-1 (Defect F-1):** In `AnnRetrievalStrategy.shortlist()`, clear `self._cached_new_name = None` and `self._cached_new_vec = None` on entry immediately after the not-set-up check and concept name validation, before embedding or vector validation occurs.
2. **A-2 (Review F-2 documentation):** Document in `shortlist()` and `diagnostics()` docstrings that `max_cosine` takes the maximum over raw search results across the whole index, including `new_name`'s own row if `new_name` is already indexed (1.0 in such cases), matching Strategy 2 semantics per [D-50](4).
3. **A-3 (Hyperparameter calibration):** Update default `ef_search` from 64 to 128 in `AnnRetrievalStrategy.__init__`, class docstring, and module docstring.
4. **X-1 (STRAT-002 test tweak):** Strengthen `test_third_setup_recovery` in `tests/test_embedding_threshold_strategy.py` by providing explicit cosine vectors using `vector_with_cosine` on `ControllableEmbedder`, eliminating vacuous `all()` assertions on empty candidate tuples.
5. **A-4 (STRAT-003 test suite additions):** Update default assertion in `test_defaults()` to `strat.ef_search == 128`, and add post-review amendment tests:
   - **T-1:** Cache cleared on entry; failed shortlist leaves no cached vector and subsequent `on_inserted` raises `RuntimeError` (kills Mutation 20).
   - **T-2:** `setup()` clears previously cached shortlist vector across successive setups (kills Mutation 15).
   - **T-3:** `diagnostics()` exact top-$k$ overlap matches independent float64 NumPy top-$k$ calculation through `insert_node` driver, and exercises deterministic low-recall regime ($\text{ef_search}=1$) where overlap < 1.0.
   - **T-4:** `efSearch` application and configuration across default, custom, non-empty, lazy-empty setups, and pre-search reapplication (kills Mutations 21a, 21b, 21c).
6. **A-5 (Equivalent mutant analysis):** Formally evaluate and document why Mutation 17 and Mutation 18 survive without posing a defect.
7. **Status relay:** Update `docs/tasks/status.md` STRAT-001 and STRAT-002 rows to `**done**` with exact review acceptance notes. Keep STRAT-003 as `**needs-review**`.
8. **Decision entry:** Append **`[D-55]`** to `docs/decisions/decision-log.md`.

### What I did
1. Backed up all three target files to `/tmp/strat003a-before/` and verified `sha256sum` and `wc -l`.
2. Applied amendments **A-1**, **A-2**, and **A-3** to `src/graph_insertion/strategies/ann_retrieval.py`.
3. Applied amendment **X-1** to `tests/test_embedding_threshold_strategy.py`.
4. Added Section 19 with tests **T-1**, **T-2**, **T-3**, **T-4** and updated default assertion in `tests/test_ann_retrieval_strategy.py`.
5. Evaluated all 22 mutations in `/tmp/strat003a-mut/`: 20 killed, exactly 2 survived (Mutations 17 and 18, proven equivalent).
6. Ran the synthetic benchmark script (`/tmp/strat003a_recall_table.py`) measuring recall and timing across clustered and Gaussian distributions ($n \in \{500, 2000\}$, $\text{efSearch} \in \{64, 128, 256\}$).
7. Verified harness smoke execution and pre-flight upper bound calculation in `/tmp/check_step4_harness.py`.
8. Re-read shared files immediately before editing and appended **`[D-55]`** to `docs/decisions/decision-log.md` and updated STRAT-001/002 rows in `docs/tasks/status.md`.
9. Ran the full pytest suite: 463 passed, 3 skipped, 0 failures across the repository.

---

## 3. Prompt Corrections

Every statement in the prompt was verified against the repository:

| Prompt Statement | Status | Verification / Evidence |
| :--- | :--- | :--- |
| Pre-assigned decision ID D-55 | **Correct** | Confirmed next free ID in `decision-log.md` was D-55 (D-54 belonged to FIX-013/014). |
| Review defect F-1 in `ann_retrieval.py` | **Correct** | `_cached_new_vec` was only overwritten upon embedding; a failed `shortlist()` call left stale cached state. |
| Review mutation 15 survives on baseline | **Correct** | Prior test suite lacked a test checking cache invalidation across successive `setup()` calls. |
| STRAT-002 `test_third_setup_recovery` had vacuous assertion | **Correct** | `assert all(c.startswith("node_3") for c in res.candidates)` vacuously passed when `res.candidates == ()`. |
| Isotropic Gaussian recall drops to ~0.84 at efSearch=64 ($n=2000$) | **Correct** | Benchmark yielded mean exact top-10 overlap of 0.8410 at $\text{efSearch}=64$, climbing to 0.9680 at 128 and 0.9990 at 256. |
| STRAT-001 and STRAT-002 review acceptance notes | **Correct** | Both tasks accepted at APC review 2026-10-11; status table rows updated verbatim. |
| Upper bound function signature / return type | **Clarification** | Prompt referenced `planned_calls_bound(k=10)`; in `scripts/run_experiment.py`, the actual function is `compute_planned_calls_upper_bound(sweep_sizes, trials_per_size, k)` returning `PlannedCallsBound` dataclass with attribute `.full_plan_bound`. |

---

## 4. Verification Output

### 4.1 Strategy 3 Test Suite (`tests/test_ann_retrieval_strategy.py`)
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 66 items

tests/test_ann_retrieval_strategy.py ................................... [ 53%]
...............................                                          [100%]

============================== 66 passed in 1.21s ==============================
```

### 4.2 Strategy 2 Test Suite (`tests/test_embedding_threshold_strategy.py`)
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 39 items

tests/test_embedding_threshold_strategy.py ............................. [ 74%]
..........                                                               [100%]

============================== 39 passed in 0.63s ==============================
```

### 4.3 Full Repository Test Suite (`.venv-ann/bin/python -m pytest -q`)
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 466 items

tests/test_ann_retrieval_strategy.py ................................... [  7%]
...............................                                          [ 14%]
tests/test_brute_force_strategy.py .......s................              [ 19%]
tests/test_controllable_embedder.py ..................                   [ 23%]
tests/test_decision.py ...............                                   [ 26%]
tests/test_embedding_threshold_strategy.py ............................. [ 32%]
..........                                                               [ 34%]
tests/test_generate_name_pool.py ....................................... [ 43%]
.....                                                                    [ 44%]
tests/test_graph_representation.py ..................................... [ 52%]
..............                                                           [ 55%]
tests/test_harness.py ................                                   [ 58%]
tests/test_harness_embedding.py ..                                       [ 59%]
tests/test_live_guard.py ...........................                     [ 64%]
tests/test_llm.py ............                                           [ 67%]
tests/test_loader.py ..........................                          [ 72%]
tests/test_null_strategy.py .......s...............................      [ 81%]
tests/test_pilot.py ...............                                      [ 84%]
tests/test_schedule.py .....................                             [ 89%]
tests/test_scoring.py .......                                            [ 90%]
tests/test_strategy_interface.py ...........................s........... [ 98%]
.....                                                                    [100%]

================== 463 passed, 3 skipped in 63.96s (0:01:03) ===================
```

### 4.4 Harness Smoke & Pre-Flight Upper Bound Check
Output from `/tmp/check_step4_harness.py`:
```text
=== Verification Step 4: Harness Smoke and Pre-Flight Bound ===
Harness status: completed
Total raw records: 4
Record 0 ef_search in metrics.extra: 128
Record 0 full extra: {"top_k": 10, "index_size": 13, "shortlist_size": 10, "max_cosine": 0.35536032915115356, "ef_search": 128, "exact_topk_overlap": 1.0}
compute_planned_calls_upper_bound return type: PlannedCallsBound
bound_res.full_plan_bound: 600 (expected 600)
bound_k5.full_plan_bound: 300 (expected 300)
bound_k20.full_plan_bound: 1200 (expected 1200)
```

### 4.5 Integrity Hashes (`sha256sum`) and Line Counts (`wc -l`)
```text
e61054cf260c4e9608d14e116c9951cce9a423f071a1c272bff2dd975e5a3f3b  /tmp/strat003a-before/ann_retrieval.py (441 lines)
b8f9783367df3994d54d6cf7fe861c1abc8996a23d089f3a1a9a31ebb9840d75  /tmp/strat003a-before/test_ann_retrieval_strategy.py (970 lines)
a787c580e9a6745b7c76590a818717e861785eb060ab5b294d4551b3efd8d4b8  /tmp/strat003a-before/test_embedding_threshold_strategy.py (1019 lines)

b479f32dc3a3a205fb2f1e5b368cd92375b89456f39dfb2e8b210ec39fbc3ada  src/graph_insertion/strategies/ann_retrieval.py (461 lines)
46e70cdf36173dddd7546424a99df8a06502051254c8525cdd3b3292a0b8310c  tests/test_ann_retrieval_strategy.py (1156 lines)
136c2cf0c0f9ee16eace1e7a86278db8b39a820bd45e6db1f0054c9efc856459  tests/test_embedding_threshold_strategy.py (1040 lines)
```

### 4.6 `git status --short`
```text
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M src/graph_insertion/strategies/ann_retrieval.py
 M tests/test_ann_retrieval_strategy.py
 M tests/test_embedding_threshold_strategy.py
?? docs/guide/
?? docs/reports/STRAT-003-A-gemini.md
?? docs/reports/STRAT-003-review-gemini.md
```

---

## 5. Mutation Table

Executed across all 22 mutations in `/tmp/strat003a-mut/` via `/tmp/run_all_mutations_a.py`:

| # | Mutation Description | Result | Killer Test |
| :--- | :--- | :--- | :--- |
| 1 | results ascending: sort by `(item[1], item[0])` | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 2 | $k_{\text{eff}} = k$: ignore $n_{\text{indexed}}$ bound | **KILLED** | `test_search_receives_k_eff_min_k_n` |
| 3 | no -1 filter: omit `if label == -1: continue` | **KILLED** | `test_minus_one_padding_dropped_explicitly` |
| 4 | rows not normalized in `setup()` | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 5 | `on_inserted()` stores un-normalized vector | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 6 | `on_inserted()` re-embeds concept | **KILLED** | `test_cached_embedding_reuse_single_embedding_per_insert` |
| 7 | `shortlist()` skips embed on empty index | **KILLED** | `test_empty_initial_graph_single_embedding` |
| 8 | omit `new_name` exclusion check | **KILLED** | `test_new_name_excluded_when_already_in_index` |
| 9 | `max_candidates()` returns $k$ unconditionally | **KILLED** | `test_max_candidates_and_matrix_sum` |
| 10 | metric set to `METRIC_L2` instead of `METRIC_INNER_PRODUCT` | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 11 | failed setup leaves `_setup_called = True` | **KILLED** | `test_failed_second_setup_leaves_strategy_not_set_up[zero_row]` |
| 12 | overlap computed inside `shortlist()` | **KILLED** | `test_exact_topk_overlap_lifecycle` |
| 13 | omit `faiss.omp_set_num_threads(1)` | **KILLED** | `test_faiss_omp_threads_set_to_one` |
| 14 | `efConstruction` set after index add | **KILLED** | `test_mutation14_ef_construction_set_before_add` |
| 15 | delete cache clearing at top of `setup()` | **KILLED** | `test_t2_setup_clears_cached_shortlist_vector` |
| 16 | delete `_index = None` at top of `setup()` | **KILLED** | `test_setup_nonempty_then_empty` |
| 17 | delete `_names = []` / `_name_to_idx = {}` at top of `setup()` | **SURVIVED** | *Equivalent mutant (see analysis below)* |
| 18 | `diagnostics()` full `ntotal` reconstruction variant | **SURVIVED** | *Equivalent mutant (see analysis below)* |
| 19 | `shortlist()` forgets to refresh `_last_query_vec` | **KILLED** | `test_exact_topk_overlap_lifecycle` |
| 20 | remove A-1 (cache clear on entry in `shortlist()`) | **KILLED** | `test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` |
| 21a | delete `hnsw.efSearch = self.ef_search` in `setup()` | **KILLED** | `test_t4_ef_search_applied_and_configured` |
| 21b | delete `hnsw.efSearch = self.ef_search` in lazy creation | **KILLED** | `test_t4_ef_search_applied_and_configured` |
| 21c | delete `hnsw.efSearch = self.ef_search` in pre-search | **KILLED** | `test_t4_ef_search_applied_and_configured` |
| 22 | default `ef_search` back to 64 | **KILLED** | `test_defaults` |

### Equivalent Mutant Analysis (A-5)

#### Mutation 17: Omit `self._names = []` and `self._name_to_idx = {}` at top of `setup()`
- **Mechanism:** In `setup()`, the strategy initializes `_setup_called = False` and `_embedder = None`.
  - If `setup()` succeeds, it unconditionally overwrites `self._names = list(nodes)` and `self._name_to_idx = {name: i for i, name in enumerate(nodes)}`.
  - If `setup()` fails, `_setup_called` remains `False` and `_embedder` remains `None`. Any subsequent call to `shortlist()` or `on_inserted()` immediately raises `RuntimeError("setup() must be called before shortlist()")` without ever reading `_names` or `_name_to_idx`.
  - Therefore, clearing `_names` and `_name_to_idx` on failure is purely defensive hygiene; omitting the assignment at the top of `setup()` is completely unobservable across all public methods.

#### Mutation 18: `diagnostics()` uses `self._index.reconstruct_n(0, self._index.ntotal)`
- **Mechanism:** In `diagnostics()`, exact top-$k$ overlap computes inner products between the cached query vector and the index vectors. The baseline uses `reconstruct_n(0, self._n_at_query)`, whereas Mutation 18 reconstructs all `ntotal` vectors.
  - The only difference between `self._n_at_query` and `self._index.ntotal` occurs if `on_inserted(new_name, ...)` was called between `shortlist(new_name)` and `diagnostics()`.
  - In that case, exactly one new vector was added to the index at index `self._n_at_query`, corresponding to `new_name` (enforced by the single-embedding invariant and `_cached_new_name` check).
  - When iterating through candidates to compute exact cosine similarities, candidates are mapped through `self._names[i]`. If index $i$ corresponds to `new_name`, `valid_items` explicitly filters it out:
    ```python
    valid_items = [
        (float(sims[i]), self._names[i])
        for i in range(len(names_to_score))
        if self._names[i] != self._cached_query_name
    ]
    ```
  - Because `self._cached_query_name == new_name`, the extra row in the `ntotal` variant is always excluded from `valid_items`.
  - Consequently, the top-$k$ candidates and the resulting `exact_topk_overlap` fraction are mathematically and floating-point identical under both implementations, even in low-recall regimes (verified via `/tmp/test_a5_analysis.py`).

---

## 6. Recall and Timing Table

Generated via `/tmp/strat003a_recall_table.py` using $d=384, k=10, M=16, \text{efConstruction}=200$, 100 evaluation probes per configuration:

| Distribution | Graph Size $n$ | `ef_search` | Mean `exact_topk_overlap` | Recall vs True Top-10 |
| :--- | :--- | :--- | :--- | :--- |
| **Clustered** | 500 | 64 | 1.0000 | 100.0% |
| **Clustered** | 500 | 128 | 1.0000 | 100.0% |
| **Clustered** | 500 | 256 | 1.0000 | 100.0% |
| **Clustered** | 2000 | 64 | 0.9990 | 99.9% |
| **Clustered** | 2000 | 128 | 1.0000 | 100.0% |
| **Clustered** | 2000 | 256 | 1.0000 | 100.0% |
| **Gaussian** (isotropic) | 500 | 64 | 0.9920 | 99.2% |
| **Gaussian** (isotropic) | 500 | 128 | 1.0000 | 100.0% |
| **Gaussian** (isotropic) | 500 | 256 | 1.0000 | 100.0% |
| **Gaussian** (isotropic) | 2000 | 64 | 0.8410 | 84.1% |
| **Gaussian** (isotropic) | 2000 | **128** | **0.9680** | **96.8%** |
| **Gaussian** (isotropic) | 2000 | 256 | 0.9990 | 99.9% |

### Latency at $n=2000$ (15 setups each)
- **`ef_search = 64`:** Median `shortlist()` search: $678.1\,\mu\text{s}$ | Median first `on_inserted()`: $1265.8\,\mu\text{s}$
- **`ef_search = 128`:** Median `shortlist()` search: $832.5\,\mu\text{s}$ | Median first `on_inserted()`: $1322.3\,\mu\text{s}$
- **Overhead:** $+154.4\,\mu\text{s}$ retrieval latency (+22.8%), negligible compared to ~1.5–3.0 s LLM pairwise decision call latency, while boosting recall under uniform dispersion from ~84% to ~97%.

---

## 7. Diffs

### 7.1 Unified Diff for `src/graph_insertion/strategies/ann_retrieval.py`
```diff
--- /tmp/strat003a-before/ann_retrieval.py	2026-10-11 16:42:45.603810789 +0800
+++ src/graph_insertion/strategies/ann_retrieval.py	2026-10-11 16:46:20.199527907 +0800
@@ -19,13 +19,16 @@
   - [D-26], [D-28]: Single-embedding invariant: new_name embedded exactly once
     in shortlist(), cached, and reused in on_inserted(). No embedding in update.
   - [D-35](4)(5): Embedding model is all-MiniLM-L6-v2 on CPU; parameters fixed
-    a priori: k=10, M=16, efConstruction=200, efSearch=64; no tuning on evaluation corpora.
+    a priori: k=10, M=16, efConstruction=200, efSearch=64 (updated to 128 per [D-55]);
+    no tuning on evaluation corpora.
   - [D-41]: max_candidates defined as min(k, n_existing); guard bound evaluates
     to exactly 600 calls over the D-35 sweep matrix (6 sizes x 10 trials x 10).
   - [D-47]: Locked Strategy 3 specification: IndexHNSWFlat with inner product on
     L2-normalised unit vectors, single-threaded determinism (omp_set_num_threads(1)),
     -1 padding filtering, exact_topk_overlap diagnostic computed in diagnostics(),
     all-or-nothing setup(), and guarded faiss import.
+  - [D-55]: Strategy 3 review amendments: shortlist() cache clearing on entry (A-1),
+    default ef_search updated from 64 to 128 (A-3), and max_cosine documentation note (A-2).
 
 Key semantics & design choices:
   - Similarity metric: Inner product on L2-normalised float32 vectors. This is
@@ -96,7 +99,7 @@
     ef_construction:
         HNSW search depth during index construction (default 200).
     ef_search:
-        HNSW search depth during nearest-neighbour queries (default 64).
+        HNSW search depth during nearest-neighbour queries (default 128 per [D-55]).
     """
 
     name: str = "ann_retrieval"
@@ -108,7 +111,7 @@
         seed: int = 42,
         M: int = 16,
         ef_construction: int = 200,
-        ef_search: int = 64,
+        ef_search: int = 128,
     ) -> None:
         if faiss is None:
             raise ImportError(
@@ -259,12 +262,24 @@
         -------
         Shortlist:
             Candidates ordered by (-score, name) and matching float scores.
+
+        Notes
+        -----
+        `max_cosine` in diagnostics is taken over the raw search results and
+        includes `new_name`'s own row if `new_name` is already indexed (would be
+        1.0 in such cases). This is unreachable through `insert_node` but
+        documented for completeness per [D-50](4) and [D-55].
         """
         if not self._setup_called or self._embedder is None:
             raise RuntimeError("setup() must be called before shortlist()")
 
         _validate_concept_name(new_name)
 
+        # Clear per-insertion cache on entry (D-55 / A-1) so a failed shortlist
+        # leaves no cached vector from an earlier successful shortlist
+        self._cached_new_name = None
+        self._cached_new_vec = None
+
         # Invalidate cached diagnostic overlap for previous query
         self._cached_exact_topk_overlap = None
 
@@ -404,6 +419,11 @@
 
         exact_topk_overlap is computed here outside every timed window using
         index.reconstruct_n() to isolate exact calculation from shortlist_s.
+
+        Note: `max_cosine` is the maximum over the raw search results across the
+        whole index, including `new_name`'s own row if `new_name` is already indexed
+        (would be 1.0 in such cases). This is unreachable through `insert_node`
+        but documented for completeness per [D-50](4) and [D-55].
         """
         index_size = self._index.ntotal if self._index is not None else 0
```

### 7.2 Unified Diff for `tests/test_embedding_threshold_strategy.py`
```diff
--- /tmp/strat003a-before/test_embedding_threshold_strategy.py	2026-10-11 16:42:45.603928910 +0800
+++ tests/test_embedding_threshold_strategy.py	2026-10-11 16:46:51.455476635 +0800
@@ -933,41 +933,62 @@
 
     def test_third_setup_recovery(self):
         """Test V-E: successful setup, failed setup, successful third setup works correctly."""
-        embedder_good = ControllableEmbedder(dim=8, seed=42)
-        
+        base = np.zeros(8, dtype=np.float32)
+        base[0] = 1.0
+        v_high = vector_with_cosine(base, 0.85)  # > 0.6
+        v_mid = vector_with_cosine(base, 0.75)   # > 0.6
+        v_low = vector_with_cosine(base, 0.35)   # < 0.6
+
+        embedder_good = ControllableEmbedder(
+            {
+                "node_1a": v_high,
+                "node_1b": v_mid,
+                "node_2": v_high,
+                "node_3a": v_high,
+                "node_3b": v_mid,
+                "node_3c": v_low,
+                "probe": base,
+            },
+            dim=8,
+            seed=42,
+        )
+
         class BadEmbedder(ControllableEmbedder):
             def embed_many(self, texts):
                 raise ValueError("Simulated failure")
-                
+
         strat = EmbeddingThresholdStrategy(theta=0.6)
-        
+
         # 1. Successful setup
         graph1 = ConceptGraph(domain_context="cs")
         graph1.add_node("node_1a")
         graph1.add_node("node_1b")
         strat.setup(graph1, embedder_good)
-        
+
         # 2. Failed setup
         graph2 = ConceptGraph(domain_context="cs")
         graph2.add_node("node_2")
         with pytest.raises(ValueError, match="Simulated failure"):
             strat.setup(graph2, BadEmbedder(dim=8, seed=42))
-            
+
         # 3. Successful third setup
         graph3 = ConceptGraph(domain_context="cs")
         graph3.add_node("node_3a")
         graph3.add_node("node_3b")
         graph3.add_node("node_3c")
         strat.setup(graph3, embedder_good)
-        
+
         # Verify shortlist candidates come only from graph 3
         res = strat.shortlist("probe")
-        assert all(c.startswith("node_3") for c in res.candidates)
-        
+        assert len(res.candidates) >= 1
+        assert res.candidates == ("node_3a", "node_3b")
+        assert "node_1a" not in res.candidates
+        assert "node_1b" not in res.candidates
+
         # Verify index size and on_inserted
         d = strat.diagnostics()
         assert d["index_size"] == 3
-        
+
         strat.on_inserted("probe", ())
         d2 = strat.diagnostics()
         assert d2["index_size"] == 4
```

### 7.3 Excerpt Diff for `tests/test_ann_retrieval_strategy.py`
```diff
--- /tmp/strat003a-before/test_ann_retrieval_strategy.py	2026-10-11 16:42:45.603869150 +0800
+++ tests/test_ann_retrieval_strategy.py	2026-10-11 16:50:48.415725201 +0800
@@ -790,7 +790,7 @@
         with pytest.raises(ValueError):
             AnnRetrievalStrategy(ef_construction=bad_val)
 
-    @pytest.mark.parametrize("bad_val", [True, 0, -1, 2.5, "64"])
+    @pytest.mark.parametrize("bad_val", [True, 0, -1, 2.5, "128"])
     def test_ef_search_validation(self, bad_val):
         with pytest.raises(ValueError):
             AnnRetrievalStrategy(ef_search=bad_val)
@@ -800,7 +800,7 @@
         assert strat.k == 10
         assert strat.M == 16
         assert strat.ef_construction == 200
-        assert strat.ef_search == 64
+        assert strat.ef_search == 128
 
 
 # ===========================================================================
@@ -968,3 +968,189 @@
             assert ef_c_at_add == [200], f"Expected efConstruction=200 at add, got {ef_c_at_add}"
         finally:
             faiss.IndexHNSWFlat.add = orig_add
+
+
+# ===========================================================================
+# 19. Post-Review Amendment Tests (A-4: T-1, T-2, T-3, T-4)
+# ===========================================================================
+
+class _SelectiveFailingEmbedder:
+    """Embedder that raises ValueError on a specific concept text."""
+
+    def __init__(self, base_embedder: Embedder, fail_concept: str) -> None:
+        self.base = base_embedder
+        self.fail_text = embed_text(fail_concept)
+
+    def embed(self, text: str) -> np.ndarray:
+        if text == self.fail_text:
+            return np.zeros(16, dtype=np.float32)
+        return self.base.embed(text)
+
+    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
+        return self.base.embed_many(texts)
+
+
+class TestPostReviewAmendments:
+    def test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector(self):
+        """Test T-1 (A-1 regression): failed shortlist clears per-insertion cache."""
+        graph = ConceptGraph()
+        graph.add_node("existing_node")
+        base_emb = FakeEmbedder(dim=16, seed=42)
+        emb = _SelectiveFailingEmbedder(base_emb, "failing_node")
+        strat = AnnRetrievalStrategy(k=5)
+        strat.setup(graph, emb)
+
+        # 1. shortlist("good_node") succeeds and caches "good_node"
+        res = strat.shortlist("good_node")
+        assert len(res.candidates) == 1
+        assert strat._cached_new_name == "good_node"
+        assert strat._cached_new_vec is not None
+
+        # 2. Failing shortlist("failing_node") raises ValueError
+        with pytest.raises(ValueError, match="Zero-norm"):
+            strat.shortlist("failing_node")
+
+        # 3. Must leave NO cached vector from earlier successful shortlist
+        assert strat._cached_new_name is None
+        assert strat._cached_new_vec is None
+
+        # 4. on_inserted("good_node") must now raise RuntimeError
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("good_node", ())
+
+        # 5. After failed shortlist on a fresh strategy, on_inserted raises RuntimeError
+        strat_fresh = AnnRetrievalStrategy(k=5)
+        strat_fresh.setup(graph, emb)
+        with pytest.raises(ValueError, match="Zero-norm"):
+            strat_fresh.shortlist("failing_node")
+        assert strat_fresh._cached_new_name is None
+        assert strat_fresh._cached_new_vec is None
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat_fresh.on_inserted("failing_node", ())
+
+    def test_t2_setup_clears_cached_shortlist_vector(self):
+        """Test T-2 (kills Mutation 15): setup() clears any previously cached shortlist vector."""
+        graph_a = ConceptGraph()
+        graph_a.add_node("n_a")
+        embedder = FakeEmbedder(dim=16, seed=42)
+        strat = AnnRetrievalStrategy(k=5)
+        strat.setup(graph_a, embedder)
+
+        strat.shortlist("p")
+        assert strat._cached_new_name == "p"
+        assert strat._cached_new_vec is not None
+
+        graph_b = ConceptGraph()
+        graph_b.add_node("n_b")
+        strat.setup(graph_b, embedder)
+
+        assert strat._cached_new_name is None
+        assert strat._cached_new_vec is None
+
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("p", ())
+
+    def test_t3_diagnostics_after_on_inserted_through_driver(self):
+        """Test T-3: diagnostics exact_topk_overlap matches independent float64 top-k through driver."""
+        init_names = [f"initial_concept_{i:03d}" for i in range(35)]
+        graph = ConceptGraph()
+        for name in init_names:
+            graph.add_node(name)
+
+        embedder = ControllableEmbedder(dim=16, seed=42)
+        meter = MeteredEmbedder(embedder)
+        decision_step = FakeDecisionStep(make_edge=False)
+
+        strat = AnnRetrievalStrategy(k=10, seed=42)
+        strat.setup(graph, meter)
+
+        probes = ["query_concept_alpha", "query_concept_beta", "query_concept_gamma"]
+        for probe in probes:
+            nodes_at_query = list(strat._names)
+            n_at_q = len(nodes_at_query)
+            reconstructed_64 = strat._index.reconstruct_n(0, n_at_q).astype(np.float64)
+            q_vec_raw = embedder.embed(embed_text(probe))
+            q_vec_64 = (q_vec_raw / np.linalg.norm(q_vec_raw)).astype(np.float64)
+            cosines_64 = reconstructed_64 @ q_vec_64
+            pairs = [
+                (float(cosines_64[i]), nodes_at_query[i])
+                for i in range(n_at_q)
+                if nodes_at_query[i] != probe
+            ]
+            pairs.sort(key=lambda item: (-item[0], item[1]))
+            k_eff = min(10, len(pairs))
+            exact_set = {cand for _, cand in pairs[:k_eff]}
+
+            n_before = graph.num_nodes()
+            res = insert_node(strat, graph, decision_step, probe, metered_embedder=meter)
+
+            assert res.shortlist is not None
+            ret_cands = res.shortlist.candidates
+            expected_overlap = (
+                sum(1 for c in ret_cands if c in exact_set) / len(ret_cands)
+                if ret_cands
+                else (1.0 if k_eff == 0 else 0.0)
+            )
+
+            diag = strat.diagnostics()
+            assert diag["exact_topk_overlap"] == expected_overlap
+            assert 0.0 <= diag["exact_topk_overlap"] <= 1.0
+            assert diag["index_size"] == n_before + 1
+
+        # Deterministic low ef_search case (ef_search=1, n >= 100) where overlap < 1.0 is observed
+        g_low = ConceptGraph()
+        for i in range(120):
+            g_low.add_node(f"node_low_{i:03d}")
+        emb_low = FakeEmbedder(dim=16, seed=42)
+        meter_low = MeteredEmbedder(emb_low)
+        strat_low = AnnRetrievalStrategy(k=10, ef_search=1, seed=42)
+        strat_low.setup(g_low, meter_low)
+        insert_res_low = insert_node(strat_low, g_low, decision_step, "probe_low", metered_embedder=meter_low)
+        diag_low = strat_low.diagnostics()
+        assert diag_low["exact_topk_overlap"] is not None
+        assert 0.0 <= diag_low["exact_topk_overlap"] < 1.0
+
+    def test_t4_ef_search_applied_and_configured(self):
+        """Test T-4: efSearch is correctly applied to HNSW index, config, and diagnostics."""
+        graph = ConceptGraph()
+        graph.add_node("n1")
+        embedder = FakeEmbedder(dim=16, seed=42)
+
+        # 1. Default ef_search is 128
+        strat_def = AnnRetrievalStrategy()
+        assert strat_def.ef_search == 128
+        assert strat_def.config()["ef_search"] == 128
+        strat_def.setup(graph, embedder)
+        assert strat_def._index.hnsw.efSearch == 128
+        assert strat_def.diagnostics()["ef_search"] == 128
+
+        # 2. Non-default ef_search (e.g. 7) on non-empty graph
+        strat_7 = AnnRetrievalStrategy(ef_search=7)
+        assert strat_7.ef_search == 7
+        assert strat_7.config()["ef_search"] == 7
+        strat_7.setup(graph, embedder)
+        assert strat_7._index.hnsw.efSearch == 7
+        assert strat_7.diagnostics()["ef_search"] == 7
+
+        # 3. Non-default ef_search on empty graph with lazy creation
+        strat_empty_7 = AnnRetrievalStrategy(ef_search=7)
+        strat_empty_7.setup(ConceptGraph(), embedder)
+        assert strat_empty_7._index is None
+        strat_empty_7.shortlist("concept_lazy")
+        assert strat_empty_7._index.hnsw.efSearch == 7
+        assert strat_empty_7.config()["ef_search"] == 7
+        assert strat_empty_7.diagnostics()["ef_search"] == 7
+
+        # 4. Default ef_search on empty graph with lazy creation
+        strat_empty_def = AnnRetrievalStrategy()
+        strat_empty_def.setup(ConceptGraph(), embedder)
+        assert strat_empty_def._index is None
+        strat_empty_def.shortlist("concept_lazy_def")
+        assert strat_empty_def._index.hnsw.efSearch == 128
+        assert strat_empty_def.config()["ef_search"] == 128
+        assert strat_empty_def.diagnostics()["ef_search"] == 128
+
+        # 5. Pre-search reapplication before search (kills mutation deleting pre-search assignment)
+        strat_def._index.hnsw.efSearch = 1
+        strat_def.shortlist("recheck_concept")
+        assert strat_def._index.hnsw.efSearch == 128
```

### 7.4 Verbatim Git Diff for Shared Documents
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 10c144b..aa0fca9 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -433,3 +433,12 @@ Reasoning: removes unverified claims and inaccuracies from D-54, defines the exa
 
+**[D-55]** Strategy 3 review amendments, ef_search default calibration, and lifecycle hardening (STRAT-003-A):
+(1) Correction to [D-47](6) per-insertion cache lifecycle: `shortlist()` clears the per-insertion cache (`_cached_new_name = None`, `_cached_new_vec = None`) on entry, right after the not-set-up check and concept name validation, before any embedding or vector validation occurs. Consequently, a failed `shortlist()` call leaves no cached vector from any earlier successful `shortlist()` call, guaranteeing that `on_inserted()` cannot erroneously succeed with a stale vector (resolves review defect F-1).
+(2) Amendment to [D-47](2) HNSW search parameter calibration: the default `ef_search` hyperparameter is increased from 64 to 128 in `AnnRetrievalStrategy.__init__`. Synthetic benchmark measurements on near-isotropic Gaussian vectors ($d=384, n=2000, M=16, \text{efConstruction}=200$) demonstrated that $\text{efSearch}=64$ achieves mean recall@10 of $\approx 0.83\text{--}0.85$, while $\text{efSearch}=128$ increases recall@10 to $\approx 0.96\text{--}0.97$ ($\approx 1.0$ at 256; clustered synthetic data achieves $\ge 0.999$ across all evaluated settings). Because thesis Section 3.2.4 frames Strategy C as approximate top-$k$ retrieval whose only experimental variable is $k$, an index that silently drops $\approx 16\%$ of its own true nearest neighbours under uniform dispersion would conflate retrieval approximation error with candidate narrowing capability. This parameter adjustment is made prior to any evaluation corpus execution based strictly on synthetic geometric benchmarks and thus complies with [D-35](5). The computational overhead is minimal ($\approx 154\,\mu\text{s}$ at $n=2000$, negligible compared to LLM call latency), and the candidate upper bound is unchanged (`min(k, n)` = 600 calls over the D-35 sweep matrix for $k=10$). Real MiniLM embeddings may exhibit different dispersion; `exact_topk_overlap` in `diagnostics()` monitors actual trial fidelity. Parameters $k=10$, $M=16$, and $\text{ef_construction}=200$ remain unchanged. [D-47] text itself is not edited (append-only log).
+(3) `max_cosine` documentation alignment: documented in `shortlist()` and `diagnostics()` docstrings that `max_cosine` is taken over the raw search results across the whole index, including `new_name`'s own row if `new_name` is already indexed (would be 1.0 in such cases), matching Strategy 2 semantics per [D-50](4).
+(4) Sensitivity runs and configuration keys: sensitivity sweeps at $\text{ef_search}=64$ and candidate limits $k=5$, $k=20$ retain the canonical strategy identifier `name = "ann_retrieval"`. Experimental execution and analysis must partition runs into separate directories keyed on `config()["k"]` and `config()["ef_search"]` (an INFRA-007 concern). Planned call upper bounds over the D-35 sweep matrix evaluate to 600 calls ($k=10$), 300 calls ($k=5$), and 1,200 calls ($k=20$), independent of `ef_search`.
+(5) Test suite additions: regression test T-1 (`test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector`) verifies cache invalidation on entry; test T-2 (`test_t2_setup_clears_cached_shortlist_vector`) verifies cache invalidation across successive `setup()` calls (killing review mutation 15); test T-3 (`test_t3_diagnostics_after_on_inserted_through_driver`) verifies `exact_topk_overlap` and `index_size` consistency through the `insert_node` driver against independent float64 NumPy top-$k$ calculations across multiple inserts and deterministic low-recall regimes ($\text{ef_search}=1$); test T-4 (`test_t4_ef_search_applied_and_configured`) verifies `efSearch` application across default, custom, non-empty, lazy-empty setups, and pre-search reapplication. In Strategy 2 (`tests/test_embedding_threshold_strategy.py`), `test_third_setup_recovery` is strengthened with explicit `vector_with_cosine` vectors to eliminate vacuous `all()` checks on empty tuples.
+(6) Equivalent-mutant findings: analysis confirms that review mutation 18 (full `_index.ntotal` variant in `diagnostics()`) is equivalent through the public API because the only node that can exist between `_n_at_query` and `_index.ntotal` is `new_name` itself, which is explicitly filtered out by name in `valid_items`; review mutation 17 (omitting `_names = []` and `_name_to_idx = {}` at the top of `setup()`) is unobservable because a successful setup overwrites both collections while a failed setup sets `_setup_called = False` and `_embedder = None`, blocking all query entry points.
+(7) Thesis-text synchronization flag for APC-A: thesis Section 3.2.4 currently names only $k$ as a tunable parameter and states $k$ is fixed "empirically per Section 3.4", while Section 3.4 provides no calibration procedure; furthermore, index hyperparameters ($M=16, \text{efConstruction}=200, \text{efSearch}=128$) and the `exact_topk_overlap` fidelity metric are not yet described in the thesis text. A synchronization edit is required in Chapter 3 to document a-priori parameter fixing and approximation fidelity diagnostics.
+Reasoning: resolves review defect F-1, improves approximation fidelity from $\approx 84\%$ to $\approx 97\%$ under uniform vector dispersion with negligible latency cost, hardens setup and shortlist cache invalidation, closes test coverage gaps without vacuous assertions, and documents mutant equivalences. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, STRAT-002, STRAT-003, INFRA-007.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 3419a3f..7395c48 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -45,8 +45,8 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 
 | ID        | Task                                       | Status | Notes                                                                          |
 | --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
-| STRAT-001 | Implement Strategy 1 (brute-force)         | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC. See report [`docs/reports/STRAT-001-gemini-brute-force.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-gemini-brute-force.md). |
-| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds shared tests/controllable_embedder.py. See report [`docs/reports/STRAT-002-gemini-embedding-threshold.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-gemini-embedding-threshold.md). |
+| STRAT-001 | Implement Strategy 1 (brute-force)         | **done** | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11. |
+| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done** | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
 | STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md). |
 | STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |
```

---

## 8. Found But Not Changed

1. **Thesis Chapter 3 Section 3.2.4 text synchronization:** The thesis text currently lists only $k$ as a tunable parameter for Strategy C and states that $k$ is fixed "empirically per Section 3.4" without documenting the fixed index construction parameters ($M=16, \text{efConstruction}=200, \text{efSearch}=128$) or the `exact_topk_overlap` fidelity diagnostic. Flagged in **[D-55](7)** for APC-A to synchronize in the thesis document.
2. **Untracked / concurrent files:** Uncommitted untracked artifacts present in checkout (`docs/reports/STRAT-003-review-gemini.md`, `docs/guide/`) were preserved and not modified or deleted.
3. **STRAT-003 status row:** Kept at `**needs-review**` per Hard Rule 2; awaiting reviewer sign-off before transition to `done`.

---

## 9. Open Questions

None blocking Phase 2 exit for STRAT-003. All review findings have been resolved, test coverage has been completed and verified against the mutation suite, and all 463 repository tests pass. Ready for review confirmation.
