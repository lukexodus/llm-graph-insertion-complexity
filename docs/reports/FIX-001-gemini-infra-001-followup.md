# FIX-001 Report: Follow-up Fixes to INFRA-001

## Executive Summary
Task FIX-001 resolved five follow-up items from the APC AI's review of commit `3dae0d8` (INFRA-001). We corrected the `pyproject.toml` build backend to `setuptools.build_meta` and verified clean editable installation (`pip install -e ".[dev]"`) in a clean virtual environment. Cross-source test coverage was expanded to evaluate Metacademy independently alongside DSA, revealing that the earlier "42" figure was strictly the DSA overlap (42 row instances across 5 files, 0 conflicts); Metacademy contributes an additional 129 row instances across 5 files with 0 orientation conflicts (171 total cross-source checks, 0 conflicts). We also audited content disagreements where example MEKG files assert edges labeled 0 in the gold standards (36 in DSA, 218 in Metacademy). An orientation-safe `judgment_for_edge(prereq, dependent)` method was added to `GoldJudgmentSet` by reusing `oriented_edge`. Node name invariants (rejecting empty names and `.txt` suffixes) were enforced in `ConceptGraph`, and test hygiene was cleaned up. All 48 tests pass.

---

## 1. Item-by-Item Implementation and Verification

### 1.1 Item 1: Build Backend (`pyproject.toml`)
- **Finding:** The prompt's claim was **verified correct**. `setuptools.backends.legacy:build` does not exist in standard setuptools distributions (`ModuleNotFoundError: No module named 'setuptools.backends'`).
- **Fix:** Changed `build-backend` to `"setuptools.build_meta"`.
- **Verification:**
  1. Created a fresh virtual environment (`/tmp/fresh_venv`).
  2. Executed `/tmp/fresh_venv/bin/pip install -e ".[dev]"`. Successfully built the editable wheel and installed dependencies (`networkx`, `pytest`, `pytest-cov`).
  3. Ran `/tmp/fresh_venv/bin/pytest`: all tests passed cleanly.
  4. Ran system-level `pytest` using `pythonpath = ["src"]`: all tests passed cleanly.

### 1.2 Item 2: Cross-Source Agreement Coverage & Gold-Overlap Audit
- **Correction to INFRA-001 Report:** The INFRA-001 report claimed "42/42 checked against DSA or Metacademy". Direct inspection of the test code showed that `TestCrossSourceAgreement` only loaded `DSA_FILE`; Metacademy was never built or queried. The figure 42 was strictly the number of positive row instances in example MEKGs overlapping with DSA.
- **Extended Test Suite:** Split `TestCrossSourceAgreement` into two explicit test methods:
  - `test_dsa_cross_source_agreement`: checks against DSA positive edges, pinned at `assert checks >= 42`, asserts 5 contributing files, asserts 0 conflicts.
  - `test_metacademy_cross_source_agreement`: checks against Metacademy positive edges (space-delimited), pinned at `assert checks >= 120`, asserts 5 contributing files, asserts 0 conflicts.
- **Empirical Audit Results:**
  | Metric | DSA Gold Standard | Metacademy Gold Standard | Combined |
  | :--- | :--- | :--- | :--- |
  | **Delimiter** | Semicolon (`;`) | Space (` `) | — |
  | **Gold positive edges** | 54 | 318 | 372 |
  | **MEKG overlapping positive row checks** | **42** | **129** | **171** |
  | **Distinct concept pairs checked** | 25 | 110 | 135 |
  | **Contributing MEKG files** | 5 files (`MEKG_with_6_nodes(DS).txt`, `MEKG_with_8_nodes(DS3).txt`, `MEKG_with_8_nodes(DS4).txt`, `MEKG_with_10_nodes(DS1).txt`, `MEKG_with_10_nodes(DS2).txt`) | 5 files (`MEKG_with7nodes.txt`, `MEKG_with_10_nodes(DS2).txt`, `MEKG_with_18_nodes(ML).txt`, `MEKG_with_21_nodes(ML).txt`, `MEKG_with_35_nodes(ML1).txt`) | 9 distinct files (`MEKG_with_10_nodes(DS2).txt` overlaps both) |
  | **Orientation conflicts** | **0** | **0** | **0** |
  | **Content disagreements (MEKG=1, Gold=0)** | 36 row instances | 218 row instances | 254 row instances |

- **Orientation Agreement vs. Content Disagreement:**
  - **Orientation Agreement (100%):** Every positive edge in an example MEKG that corresponds to a positive edge in DSA or Metacademy has the exact same prerequisite-dependent orientation when mapped via `oriented_edge`.
  - **Content Disagreement:** 36 row instances in DSA and 218 in Metacademy represent concept pairs where the example MEKG asserts a prerequisite relationship (`label=1`), but the gold standard labels the relationship as `0` (e.g. `recursion -> breadth_first_search` or `probability -> bayesian_networks`). This reflects differing domain annotation granularity or labeler thresholds across datasets, not an edge-inversion error.
  - `MEKG_with_8_nodes(logic).txt` has zero concepts in common with either DSA or Metacademy, so it does not participate in cross-source overlap.

### 1.3 Item 3: Orientation-Safe Judgment Lookup (`GoldJudgmentSet.judgment_for_edge`)
- **Implementation:** Added `judgment_for_edge(self, prereq: str, dependent: str) -> Optional[bool]` to `GoldJudgmentSet`.
- **Single Source of Truth:** Reuses `oriented_edge(self.source_kind, prereq, dependent)` directly. Because both the `GOLD` column reversal `(c1, c2) -> (c2, c1)` and the `MEKG_EXAMPLE` identity `(c1, c2) -> (c1, c2)` are mathematical involutions (their own inverses), passing `(prereq, dependent)` to `oriented_edge` yields exactly the `(col1, col2)` tuple under which the raw row was stored in `_judgments`.
- **Verification & Tests:**
  - Real DSA row `dijkstra_algorithm;graph;1`:
    - `judgment_for_edge("graph", "dijkstra_algorithm") is True`
    - `judgment_for_edge("dijkstra_algorithm", "graph") is False` (verified against real row `graph;dijkstra_algorithm;0` in DSA).
  - Real MEKG example row `asymptotic_complexity.txt;hash_table.txt;1`:
    - `judgment_for_edge("asymptotic_complexity", "hash_table") is True`
    - `judgment_for_edge("hash_table", "asymptotic_complexity") is False` (verified against row in `MEKG_with_6_nodes(DS).txt`).
  - Unjudged pairs:
    - If a pair was never recorded in either direction, `judgment_for_edge` returns `None` in both directions.
    - Audited against the real DSA file for `binary_search_tree` and `asymptotic_complexity`: the file contains `asymptotic_complexity;binary_search_tree;0`, but completely omits `binary_search_tree;asymptotic_complexity`. Therefore:
      - `judgment_for_edge("asymptotic_complexity", "binary_search_tree")` maps to the missing file row $\to$ returns `None`.
      - `judgment_for_edge("binary_search_tree", "asymptotic_complexity")` maps to the present file row $\to$ returns `False`.

### 1.4 Item 4: Enforcement of Node Invariants (`.txt` and empty names)
- **Implementation:** Added `_validate_concept_name(name)` in `src/graph_insertion/graph_representation.py`:
  - Raises `ValueError` if `name` is empty or not a string.
  - Raises `ValueError` if `name.endswith(".txt")` (per [D-16] and [D-21], nodes must be bare concept names).
- **Integrated into:**
  - `ConceptGraph.add_node(name)`
  - `ConceptGraph.add_prereq_edge(prereq, dependent)` for both `prereq` and `dependent`.
- **Tests Added:**
  - `test_add_node_empty_raises`
  - `test_add_node_txt_suffix_raises`
  - `test_add_prereq_edge_empty_name_raises` (for both arguments)
  - `test_add_prereq_edge_txt_suffix_raises` (for both arguments)
  - `test_add_node_valid_names` (validates valid bare names including uppercase and apostrophes).

### 1.5 Item 5: Test Hygiene
- Changed all `.replace(".txt", "")` occurrences in `tests/test_graph_representation.py` to `.removesuffix(".txt")`.
- Dropped the unused `import glob` in `TestCrossSourceAgreement`.

---

## 2. Test Suite Summary
- Total test count expanded from 38 to 48 unit tests.
- All 48 tests pass cleanly in 2.37s.

---

## 3. Found But Not Changed
1. **Handling of Missing DSA Pair in Evaluation Scoring:**
   - As reiterated by the prompt, the decision of whether `_Label.MISSING` is scored as label-0 or excluded from accuracy evaluation metrics remains reserved for Luke. The implementation strictly represents `_Label.MISSING` and returns `None` from `judgment_for_edge`.
2. **Stale text in `complete-context.md` Section 4 and `data-formats.md`:**
   - Tracked under task DOC-002 in `docs/tasks/status.md`. Left untouched.

---

## 4. Diffs of Edited Shared Docs

### Diff for `docs/tasks/status.md`
```diff
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -68,3 +68,4 @@ plan asked this phase to contain exists somewhere in the repo).
 | DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md). |
 | DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). | **open** | Prompt not yet written; can wait until after INFRA-001. |
+| FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-001-gemini-infra-001-followup.md). |
```
