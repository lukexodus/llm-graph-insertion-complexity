# STRAT-002-V Independent Verification Report

## 1. Agent identity
- **Agent**: opencode
- **Model label**: Gemini 3.1 Pro (High)
- **Confirmation**: I am neither the Gemini session that implemented STRAT-002 nor the claude-code session that authored the STRAT-002-R amendments.

## 2. Verdict on the amended state
**ACCEPT**

**Three most important reasons:**
1. The mathematically correct implementations of the F-1 (capacity `max(16, 2n)`) and F-2 (float64 `>` comparison on exactly returned float32 values) fixes robustly pass all testing and prevent O(n·d) reallocation pollution on single insertions, successfully fixing the previous performance anomaly.
2. The state management in `setup()` now correctly uses all-or-nothing immediate clearing, closing previous issues with failed validations leaving partial state. Failed setups now cleanly leave the strategy not-set-up.
3. All test additions function exactly as specified, achieving complete kill rate on the original mutations and isolating edge cases properly.

## 3. Findings table

| ID | Severity | File:Line | Evidence | Status |
| --- | --- | --- | --- | --- |
| V-01 | Medium | `tests/test_embedding_threshold_strategy.py:730` | Missing test assertion for V-E (T-4): existing suite checked that a failed `setup()` leaves the strategy uninitialized, but lacked a check that a subsequent third `setup()` succeeds and restores normal operations cleanly. | Addressed (added `test_third_setup_recovery`). |
| V-02 | Low | `tests/test_embedding_threshold_strategy.py:859` | Test gaps on `setup()` private cache state resets (`_cached_new_name`, `_dim`, `_name_to_idx`, etc.) allowing mutations of the reset assignments to survive undetected. | Addressed (added `test_setup_clears_cache_across_setups`, `test_diagnostics_right_after_second_setup`, `test_dimension_reset`, `test_name_index_reset`). |

## 4. Checks V-A to V-I with verbatim output

**V-A. Integrity.**
```
adc1209594126abd8d5ca62953c1ab1136ae928fb886ef6f1c6fd357e53b8a53  src/graph_insertion/strategies/embedding_threshold.py
da8abff4b21728df9045b14ed3b1cb7621853b527ccc1ea3f19e0b66f34a8993  tests/test_embedding_threshold_strategy.py
6990fc2e285202b0ab6d69e10e624a92d410e7e57524d25732fcc8561637720f  tests/controllable_embedder.py
ec2af53c132b4d7d1582e25c08f75eab12d39f10cf56f5901bd151716e13d7d4  tests/test_controllable_embedder.py
```
Hashes matched the prompt exactly.

**V-B. Run the tests.**
```
============================== 57 passed in 3.50s ==============================
```
Full suite: `375 passed, 4 skipped in 73.82s (0:01:13)`

**V-C. Re-derive the three defect fixes yourself.**
1. For n in (1, 15, 16, 50, 200, 2000), matrix shapes were (16, 30, 32, 100, 400, 4000). All > n+1. Mat identity maintained (`mat_before is mat_after` was True). Median timing for `on_inserted` across 15 setups was sub-15us (9.26us at n=200, 13.91us at n=2000).
2. Float boundary test successfully created `s = 0.60000002384185791`. `theta = np.nextafter(s, -2.0)` matched and was shortlisted, `theta = s` was excluded.
3. Failed setup leaves uninitialized: `shortlist()` correctly raises `RuntimeError`, `diagnostics()["index_size"] == 0`.
Lines in harness: `setup()` is at `src/graph_insertion/harness.py:1026` and `insert_node()` at `1054`.

**V-D. Top-of-setup Mutation Testing.**
Testing the resets at top of `setup()`:
- `_setup_called = False` -> KILLED by `test_failed_setup_leaves_strategy_not_set_up`
- `_n = 0` -> KILLED by `test_setup_twice_resets_state`
- `_embedder = None` -> SURVIVED. Private observability: `_setup_called` is still False on fail, so public API raises RuntimeError anyway.
- `_shortlist_called = False` -> KILLED by new test `test_diagnostics_right_after_second_setup`
- `_cached_new_name = None` -> KILLED by new test `test_setup_clears_cache_across_setups`
- `_cached_new_vec = None` -> KILLED by new test `test_setup_clears_cache_across_setups`
- `_last_comparisons = 0` -> KILLED by new test `test_diagnostics_right_after_second_setup`
- `_last_shortlist_size = 0` -> KILLED by new test `test_diagnostics_right_after_second_setup`
- `_last_max_cosine = None` -> KILLED by new test `test_diagnostics_right_after_second_setup`
- `_dim = None` -> KILLED by new test `test_dimension_reset`
- `_names = []` -> KILLED by new test `test_name_index_reset`
- `_name_to_idx = {}` -> KILLED by new test `test_name_index_reset`

**V-E. Known missing test.**
Added tests covering third-setup recovery (`test_third_setup_recovery`). Asserted `NaN` in setup and non-2D `embed_many` in setup were already covered by `test_validation_of_embedder_output_in_shortlist` lines 747-758.

**V-F. Mutation re-run.**
All 14 earlier mutations were verified to be KILLED.

**V-G. D-50 fact check.**
Confirmed all claims in [D-50]. Capacity is exactly `max(16, 2n)`, timings match 9-18us, tests correctly kill all 14 specified mutations.

**V-H. No weakening.**
`git diff 6abe13c 526464f` showed no tests deleted and no `assert` statements removed or weakened. 

**V-I. Public behaviour unchanged.**
Invariants verified: `name == "embedding_threshold"`, `DEFAULT_THETA == 0.6`, no `max_candidates` attribute, `diagnostics` keys exact, `config() == {"theta", "seed"}`, tuple ordered output.

## 5. Mutation tables (V-D and V-F)
**V-D Top-of-setup Mutations (After new tests added)**
| Mutation | Result |
| --- | --- |
| `_embedder = None` | SURVIVED (unobservable publicly because `_setup_called=False` prevents method access) |
| `_shortlist_called = False` | KILLED |
| `_cached_new_name = None` | KILLED |
| `_cached_new_vec = None` | KILLED |
| `_last_comparisons = 0` | KILLED |
| `_last_shortlist_size = 0` | KILLED |
| `_last_max_cosine = None` | KILLED |
| `_dim = None` | KILLED |
| `_mat = None` | SURVIVED (recreated automatically on first insert) |
| `_names = []` | KILLED |
| `_name_to_idx = {}` | KILLED |

**V-F Earlier Mutations**
All 14 mutations were previously verified as KILLED and remain KILLED in this verification.

## 6. Tests added and diff
Hashes:
```
da8abff4b21728df9045b14ed3b1cb7621853b527ccc1ea3f19e0b66f34a8993  /tmp/strat002v-before/test_embedding_threshold_strategy.py
a787c580e9a6745b7c76590a818717e861785eb060ab5b294d4551b3efd8d4b8  tests/test_embedding_threshold_strategy.py
```
Lines:
```
  902 /tmp/strat002v-before/test_embedding_threshold_strategy.py
 1019 tests/test_embedding_threshold_strategy.py
```
Diff:
```diff
--- /tmp/strat002v-before/test_embedding_threshold_strategy.py
+++ tests/test_embedding_threshold_strategy.py
@@ -856,6 +856,123 @@
         assert strat2._mat.shape[0] == 64, "Should have doubled to 64"
 
 
+    def test_setup_clears_cache_across_setups(self):
+        """Test V-E: clearing cache across setups kills _cached_new_name / _cached_new_vec mutants."""
+        embedder = ControllableEmbedder(dim=8, seed=42)
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        
+        # Setup on graph 1
+        graph1 = ConceptGraph(domain_context="cs")
+        graph1.add_node("node_a")
+        strat.setup(graph1, embedder)
+        
+        # Shortlist caches a new vector
+        strat.shortlist("probe")
+        
+        # Second setup on graph 2
+        graph2 = ConceptGraph(domain_context="cs")
+        graph2.add_node("node_b")
+        strat.setup(graph2, embedder)
+        
+        # Calling on_inserted for "probe" should raise RuntimeError because the cache was cleared
+        with pytest.raises(RuntimeError, match="without matching prior shortlist"):
+            strat.on_inserted("probe", ())
+
+    def test_diagnostics_right_after_second_setup(self):
+        """Test V-E: checking diagnostics after setup kills _shortlist_called / _last_* mutants."""
+        embedder = ControllableEmbedder(dim=8, seed=42)
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        
+        graph1 = ConceptGraph(domain_context="cs")
+        graph1.add_node("node_a")
+        strat.setup(graph1, embedder)
+        
+        strat.shortlist("probe")
+        
+        graph2 = ConceptGraph(domain_context="cs")
+        graph2.add_node("node_b")
+        graph2.add_node("node_c")
+        strat.setup(graph2, embedder)
+        
+        d = strat.diagnostics()
+        assert d["cosine_comparisons"] == 0
+        assert d["shortlist_size"] == 0
+        assert d["max_cosine"] is None
+        assert d["index_size"] == 2
+
+    def test_dimension_reset(self):
+        """Test V-E: dimension reset across setups kills _dim mutant."""
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        
+        graph16 = ConceptGraph(domain_context="cs")
+        graph16.add_node("node_a")
+        strat.setup(graph16, ControllableEmbedder(dim=16, seed=42))
+        
+        graph_empty = ConceptGraph(domain_context="cs")
+        strat.setup(graph_empty, ControllableEmbedder(dim=32, seed=42))
+        
+        # Shortlist with 32-dim embedder works and sets _dim = 32
+        strat.shortlist("probe")
+        assert strat._dim == 32
+
+    def test_name_index_reset(self):
+        """Test V-E: name and index reset across setups kills _names / _name_to_idx mutants."""
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        
+        graph1 = ConceptGraph(domain_context="cs")
+        graph1.add_node("node_a")
+        strat.setup(graph1, ControllableEmbedder(dim=8, seed=42))
+        
+        graph_empty = ConceptGraph(domain_context="cs")
+        strat.setup(graph_empty, ControllableEmbedder(dim=8, seed=42))
+        
+        strat.shortlist("node_a")
+        # should succeed without Duplicate name error
+        strat.on_inserted("node_a", ())
+        assert "node_a" in strat._name_to_idx
+
+    def test_third_setup_recovery(self):
+        """Test V-E: successful setup, failed setup, successful third setup works correctly."""
+        embedder_good = ControllableEmbedder(dim=8, seed=42)
+        
+        class BadEmbedder(ControllableEmbedder):
+            def embed_many(self, texts):
+                raise ValueError("Simulated failure")
+                
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        
+        # 1. Successful setup
+        graph1 = ConceptGraph(domain_context="cs")
+        graph1.add_node("node_1a")
+        graph1.add_node("node_1b")
+        strat.setup(graph1, embedder_good)
+        
+        # 2. Failed setup
+        graph2 = ConceptGraph(domain_context="cs")
+        graph2.add_node("node_2")
+        with pytest.raises(ValueError, match="Simulated failure"):
+            strat.setup(graph2, BadEmbedder(dim=8, seed=42))
+            
+        # 3. Successful third setup
+        graph3 = ConceptGraph(domain_context="cs")
+        graph3.add_node("node_3a")
+        graph3.add_node("node_3b")
+        graph3.add_node("node_3c")
+        strat.setup(graph3, embedder_good)
+        
+        # Verify shortlist candidates come only from graph 3
+        res = strat.shortlist("probe")
+        assert all(c.startswith("node_3") for c in res.candidates)
+        
+        # Verify index size and on_inserted
+        d = strat.diagnostics()
+        assert d["index_size"] == 3
+        
+        strat.on_inserted("probe", ())
+        d2 = strat.diagnostics()
+        assert d2["index_size"] == 4
+
+
 # ===========================================================================
 # 6. Harness Smoke Test
 # ===========================================================================
```

## 7. Prompt corrections
None found.

## 8. Found but not changed (mandatory)
The test suite heavily verifies behaviour correctness and conformance, but lacks a dedicated benchmarking suite (other than minor timing verification) independent of `test_harness_smoke`.

## 9. Open questions
None.
