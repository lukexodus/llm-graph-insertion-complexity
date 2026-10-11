# STRAT-001-A — Close Test-Coverage Gap Found in STRAT-001 Review

Task: STRAT-001-A  
Written: 2026-10-09  
Target: `tests/test_brute_force_strategy.py`  
Decision ID: None (no decision-log entry written; `status.md` untouched)

---

## 1. Agent Identity

- **Agent:** `claude-code` (preferred per prompt: "Prefer Claude Code: opencode wrote the review you are acting on")
- **Model label:** Gemini 3.8 Flash (High)
- **Confirmation:** I am **NOT** the Gemini session that implemented STRAT-001 (`docs/reports/STRAT-001-gemini-brute-force.md`). This follow-up task was executed independently to close the findings in opencode's review (`docs/reports/STRAT-001-review-opencode.md`).

---

## 2. What Was Asked / What I Did

### What was asked
Close the test-coverage gap (F1) and two nits (F2, F3) documented in `docs/reports/STRAT-001-review-opencode.md`:
1. **A-1 (F1):** Add a test asserting that `BruteForceStrategy` reads `ConceptGraph` live. After `setup(graph, embedder)`, add a node directly using `graph.add_node(...)` (without calling `on_inserted`), and assert `shortlist("probe")` includes it (sorted ascending, excluding `probe`). Assert nodes added via the real driver (`insert_node`) also appear. Purpose: kill Mutation 8 (caching nodes in a private list synchronized only via `on_inserted`).
2. **A-2 (F2):** Strengthen `TestBruteForceHarnessSmoke::test_sweep_smoke` to match the null-strategy template and real `raw.jsonl` schema: assert `metrics.n_before == size`, `metrics.embed_s == 0.0`, and `metrics.extra == {"candidate_count": size}` for every record.
3. **A-3 (F3):** Keep `test_shortlist_excludes_new_name_even_if_already_in_graph`, and add a docstring stating that this state is unreachable via `insert_node` (its precondition rejects existing names at `strategy.py:261-262`), pinning the strategy's own defensive contract.

### What I did
1. Backed up `tests/test_brute_force_strategy.py` to `/tmp/strat001a-before/` and recorded `sha256sum` and `wc -l`.
2. Implemented **A-1 (F1)** in `tests/test_brute_force_strategy.py`: added `TestBruteForceUnit::test_shortlist_reads_live_graph_without_caching`.
3. Implemented **A-2 (F2)** in `tests/test_brute_force_strategy.py`: updated `TestBruteForceHarnessSmoke::test_sweep_smoke` to assert `n_before == n`, `embed_s == 0.0`, and `extra == {"candidate_count": n}` on `rec["metrics"]`.
4. Implemented **A-3 (F3)** in `tests/test_brute_force_strategy.py`: added docstring to `test_shortlist_excludes_new_name_even_if_already_in_graph` referencing `strategy.py:261-262`.
5. Ran the test suite: `tests/test_brute_force_strategy.py` now passes with 23 passed, 1 skipped.
6. Performed the 8-mutation check in `/tmp/strat001a-mut/`; verified all 8 mutations are **KILLED** (Mutation 8 is killed by `test_shortlist_reads_live_graph_without_caching`).

---

## 3. Prompt Corrections

Every statement in the prompt was verified against the repository:

| Prompt Statement | Status | Verification / Evidence |
| :--- | :--- | :--- |
| STRAT-001 reviewed by opencode with ACCEPT WITH NOTES | **Correct** | `docs/reports/STRAT-001-review-opencode.md` exists and confirms verdict. |
| Findings F1, F2, F3 in review report | **Correct** | Section 3 of `STRAT-001-review-opencode.md` details F1, F2, and F3. |
| `ConceptGraph.add_node` is the public method to add a node | **Correct** | Verified in `src/graph_insertion/graph_representation.py:158-161`. |
| Null-strategy smoke test template around lines 800-820 | **Correct** | Verified in `tests/test_null_strategy.py:810-818` (`n_before == rec["size"]`, `total_s >= 0.0`). |
| `insert_node` rejects existing names in `strategy.py` | **Correct** | Verified in `src/graph_insertion/strategy.py:261-262`: `if graph.has_node(new_name): raise ValueError(...)`. |
| Other threads share this checkout / uncommitted files present | **Correct** | Uncommitted modifications from another thread in `docs/context/prompt-adapter-contract.md`, `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`. |

No incorrect claims were found in the prompt.

---

## 4. Verification Output

### 4.1 `pytest -q tests/test_brute_force_strategy.py | tail -3`
```
tests/test_brute_force_strategy.py .......s................              [100%]

======================== 23 passed, 1 skipped in 2.60s =========================
```

*(Note: the 1 skipped test is `test_embedder_identity_stored_on_strategy` from `StrategyConformanceSuite`, intentionally skipped for non-embedding strategies where `_embedder is None`).*

### 4.2 `pytest -q | tail -3`
```
=========================== short test summary info ============================
FAILED tests/test_generate_name_pool.py::test_contract_doc_fixtures_subprocess_execution
============= 1 failed, 374 passed, 3 skipped in 85.98s (0:01:25) ==============
```

**Explanation of the 1 failure:**
The failure in `tests/test_generate_name_pool.py::test_contract_doc_fixtures_subprocess_execution` is caused by concurrent, uncommitted changes in `docs/context/prompt-adapter-contract.md` belonging to another thread (where 9 JSON code blocks are present under example responses instead of 8). It is completely unrelated to STRAT-001 / `BruteForceStrategy`. Per Hard Rule 2, those files were not touched.

### 4.3 `sha256sum` before and after
```
9c687207e144d2220efe6ed20d2773a7ccd6d631ede55576723ea731040a064d  /tmp/strat001a-before/test_brute_force_strategy.py
65e723ff7de0241c07c7172764f471235db9be385c027d216b8294c491b27834  tests/test_brute_force_strategy.py
```

### 4.4 `wc -l` before and after
```
  296 /tmp/strat001a-before/test_brute_force_strategy.py
  340 tests/test_brute_force_strategy.py
  636 total
```

### 4.5 `git status --short`
```
 M docs/context/prompt-adapter-contract.md
 M scripts/generate_name_pool.py
 M tests/stub_prompt_adapter.py
 M tests/test_brute_force_strategy.py
 M tests/test_generate_name_pool.py
?? docs/reports/STRAT-001-A-claude-code.md
?? docs/reports/STRAT-001-review-opencode.md
?? docs/reports/STRAT-003-claude-code-ann-retrieval.md
```

**Ownership:**
- `M tests/test_brute_force_strategy.py`: Mine (STRAT-001-A).
- `?? docs/reports/STRAT-001-A-claude-code.md`: Mine (STRAT-001-A).
- Other entries belong to concurrent / earlier tasks.

---

## 5. Mutation Table

Each mutation was applied in `/tmp/strat001a-mut/` to `src/graph_insertion/strategies/brute_force.py`, evaluated via `pytest -q tests/test_brute_force_strategy.py`, and the failing tests were recorded:

| # | Mutation | Result | Failing test(s) when KILLED |
| :-- | :-- | :-- | :-- |
| M1 | Delete `sorted(...)` | **KILLED** | `TestBruteForceUnit::test_shortlist_all_nodes_sorted_ascending_and_scores_zero`<br>`TestBruteForceUnit::test_shortlist_reads_live_graph_without_caching`<br>`TestBruteForceUnit::test_shortlist_order_independent_of_graph_insertion_order` |
| M2 | Drop the `!= new_name` filter | **KILLED** | `TestBruteForceUnit::test_shortlist_excludes_new_name_even_if_already_in_graph` |
| M3 | `max_candidates` returns `max(0, n_existing - 1)` | **KILLED** | `TestBruteForceConformance::test_shortlist_is_subset_and_excludes_new_node`<br>`TestBruteForceConformance::test_shortlist_does_not_mutate_graph`<br>`TestBruteForceConformance::test_same_seed_gives_same_shortlist`<br>`TestBruteForceConformance::test_repeated_inserts_see_previous_nodes`<br>`TestBruteForceConformance::test_max_candidates_bound_if_defined`<br>`TestBruteForceUnit::test_max_candidates_unsetup_instance`<br>`TestBruteForceUnit::test_full_matrix_bound_d35` |
| M4 | `setup` stores embedder (`self._embedder = embedder`) | **KILLED** | `TestBruteForceUnit::test_shortlist_reads_live_graph_without_caching`<br>`TestBruteForceUnit::test_embedder_remains_none_after_setup` |
| M5 | `shortlist` returns empty instead of raising before `setup()` | **KILLED** | `TestBruteForceUnit::test_shortlist_before_setup_raises_runtime_error` |
| M6 | Scores become `None` | **KILLED** | `TestBruteForceUnit::test_shortlist_all_nodes_sorted_ascending_and_scores_zero`<br>`TestBruteForceUnit::test_shortlist_excludes_new_name_even_if_already_in_graph`<br>`TestBruteForceUnit::test_shortlist_reads_live_graph_without_caching`<br>`TestBruteForceUnit::test_shortlist_empty_graph`<br>`TestBruteForceUnit::test_shortlist_order_independent_of_graph_insertion_order`<br>`TestBruteForceScaleSanity::test_scale_sanity_2000_nodes` |
| M7 | `diagnostics()` always reports `0` | **KILLED** | `TestBruteForceUnit::test_config_and_diagnostics_json_serializable`<br>`TestBruteForceHarnessSmoke::test_sweep_smoke` |
| M8 | `setup` seeds private list, `on_inserted` appends to it, `shortlist` reads list instead of live graph | **KILLED** | `TestBruteForceUnit::test_shortlist_reads_live_graph_without_caching` |

All 8 mutations are **KILLED**. In particular, Mutation 8 (which previously survived in the review) is killed by the new `test_shortlist_reads_live_graph_without_caching` test.

---

## 6. Diff

Verbatim output of `diff -u /tmp/strat001a-before/test_brute_force_strategy.py tests/test_brute_force_strategy.py`:

```diff
--- /tmp/strat001a-before/test_brute_force_strategy.py	2026-10-09 20:53:57.807815440 +0800
+++ tests/test_brute_force_strategy.py	2026-10-09 20:57:17.253688915 +0800
@@ -97,6 +97,12 @@
         assert len(sl.scores) == len(sl.candidates)
 
     def test_shortlist_excludes_new_name_even_if_already_in_graph(self) -> None:
+        """Verify that shortlist excludes new_name even if it is already present in the graph.
+
+        Note: this state is unreachable through insert_node (its precondition rejects
+        existing names at strategy.py:261-262), but this test pins the strategy's own
+        contract and defensive filtering.
+        """
         g = ConceptGraph(domain_context="computer science")
         for name in ["alpha", "beta", "gamma"]:
             g.add_node(name)
@@ -107,6 +113,40 @@
         assert "beta" not in sl.candidates
         assert sl.scores == (0.0, 0.0)
 
+    def test_shortlist_reads_live_graph_without_caching(self) -> None:
+        """Strategy reads ConceptGraph live; bypassing on_inserted still updates shortlist.
+
+        Guards against implementations that cache nodes during setup() and only
+        synchronize via on_inserted(). Adding a node directly via graph.add_node()
+        must be visible in the next shortlist() call, sorted ascending and excluding probe.
+        """
+        g = ConceptGraph(domain_context="computer science")
+        g.add_node("alpha")
+        g.add_node("gamma")
+
+        strat = BruteForceStrategy(seed=42)
+        strat.setup(g, FakeEmbedder())
+
+        sl_initial = strat.shortlist("probe")
+        assert sl_initial.candidates == ("alpha", "gamma")
+
+        # Mutate the graph directly WITHOUT calling on_inserted
+        g.add_node("beta")
+        sl_after_direct_add = strat.shortlist("probe")
+        assert sl_after_direct_add.candidates == ("alpha", "beta", "gamma")
+        assert "probe" not in sl_after_direct_add.candidates
+        assert sl_after_direct_add.scores == (0.0, 0.0, 0.0)
+
+        # Also add a node through the real driver (insert_node) and verify it appears
+        meter = MeteredEmbedder(FakeEmbedder())
+        decision_step = FakeDecisionStep(make_edge=False)
+        insert_node(strat, g, decision_step, "delta", metered_embedder=meter)
+
+        sl_after_insert_node = strat.shortlist("probe")
+        assert sl_after_insert_node.candidates == ("alpha", "beta", "delta", "gamma")
+        assert "probe" not in sl_after_insert_node.candidates
+        assert sl_after_insert_node.scores == (0.0, 0.0, 0.0, 0.0)
+
     def test_shortlist_empty_graph(self) -> None:
         g = ConceptGraph()
         strat = BruteForceStrategy(seed=42)
@@ -291,6 +331,10 @@
             assert rec["status"] == "success"
             assert rec["strategy"] == "brute_force"
             n = rec["size"]
-            assert rec["metrics"]["llm_calls"] == n
-            assert rec["metrics"]["shortlist_size"] == n
-            assert rec["metrics"]["embedding_calls"] == 0
+            m = rec["metrics"]
+            assert m["n_before"] == n
+            assert m["llm_calls"] == n
+            assert m["shortlist_size"] == n
+            assert m["embedding_calls"] == 0
+            assert m["embed_s"] == 0.0
+            assert m["extra"] == {"candidate_count": n}
```

---

## 7. Found but Not Changed

1. **Unrelated test failure:** `tests/test_generate_name_pool.py::test_contract_doc_fixtures_subprocess_execution` fails due to uncommitted edits in `docs/context/prompt-adapter-contract.md` made by another thread (9 code blocks found vs 8 expected). Per Hard Rule 2, I did not modify these files.
2. **Untracked / modified files in working tree:** `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/reports/STRAT-001-review-opencode.md`, `docs/reports/STRAT-003-claude-code-ann-retrieval.md`. Left untouched.

---

## 8. Open Questions

None. The coverage gap F1 and nits F2 and F3 are completely closed, all 8 mutations are killed, and no source changes to `brute_force.py` were required.
