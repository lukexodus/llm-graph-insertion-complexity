# INFRA-003: Corpus Loader Implementation & Verification

**Task ID:** INFRA-003  
**Agent:** Gemini  
**Date:** 2026-10-03  
**Status:** Complete  

---

## 1. Executive Summary

Task `INFRA-003` implemented the corpus loading infrastructure for the LLM graph-insertion complexity experiments. The loader normalizes all 12 evaluation corpora (`DSA_gold_standard_MEKG.txt`, `metacademy_gold_standard_MEKG.txt`, and the 10 example `MEKG_with*.txt` files) into `ConceptGraph` and `GoldJudgmentSet` representations.

All requirements were met:
- **API:** Implemented `discover_corpora()` (discovering exactly 12 corpora) and `load_corpus()` in `src/graph_insertion/loader.py`, returning `LoadedCorpus` with `ConceptGraph`, `GoldJudgmentSet`, and comprehensive `CorpusStats`.
- **Parsing:** Strict 3-field and binary label validation with filename and line numbers on failure; `.txt` suffix stripping via `removesuffix` on example files only; positive self-loop rejection; canonical edge orientation applied exclusively through `oriented_edge(source_kind, col1, col2)` ([D-15], [D-19], [D-23]).
- **Domain Context:** Established and locked the domain context table ([D-27]). `MEKG_with7nodes.txt` is defaulted to `None` in the absence of a filename tag, with `"machine learning"` proposed for Luke's confirmation.
- **Pinned Expectations:** All structural properties and counts verified against the raw files and pinned in `tests/test_loader.py`.
- **Dataset-Missing Support:** Created `tests/conftest.py` with `dataset_root` and retrofitted `test_graph_representation.py` so fresh clones without the gitignored `repositories/` directory skip cleanly.
- **Read-Only Checks:** Verified domain semantics of `MEKG_with_8_nodes(logic).txt`, confirmed acyclicity (100% DAGs) and computed transitive reductions across all 12 corpora, audited case/punctuation collisions (zero collisions), and benchmarked load times.

---

## 2. API Design & Component Overview

### `CorpusSpec` & `LoadedCorpus`
```python
@dataclass(frozen=True)
class CorpusSpec:
    name: str
    path: Path
    source_kind: SourceKind
    domain_context: Optional[str] = None
    delimiter: str = ";"
    has_txt_suffix: bool = False

@dataclass
class LoadedCorpus:
    name: str
    source_kind: SourceKind
    graph: ConceptGraph
    judgments: GoldJudgmentSet
    domain_context: Optional[str]
    stats: CorpusStats
```

`discover_corpora(root=None)` discovers the 12 files in deterministic order:
1. `DSA_gold_standard_MEKG` (`SourceKind.GOLD`, delimiter `;`, domain `"data structures and algorithms"`)
2. `metacademy_gold_standard_MEKG` (`SourceKind.GOLD`, delimiter `" "`, domain `"machine learning and supporting mathematics"`)
3–12. 10 files matching `MEKG_with*.txt` sorted alphabetically (`SourceKind.MEKG_EXAMPLE`, delimiter `;`, `.txt` suffix stripped).

`load_corpus(target, root=None)` accepts a `CorpusSpec`, a `Path`, or a string identifier (supporting exact stem, lowercase alias such as `"dsa"` or `"metacademy"`, or filename).

---

## 3. Pinned Expectations & Structural Verification

All 12 corpora were audited against the raw files on disk. The test suite pins these values:

| Corpus Identifier | Lines | Distinct Nodes | Distinct Pairs | Duplicate Rows | Self-Loops (lbl=0) | Positive Rows | Positive Edges |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DSA_gold_standard_MEKG** | 841 | 29 | 840 | 1 | 29 | 55 | 54 |
| **metacademy_gold_standard_MEKG** | 19,740 | 141 | 19,740 | 0 | 0 | 318 | 318 |
| **MEKG_with7nodes** | 49 | 7 | 49 | 0 | 7 | 16 | 16 |
| **MEKG_with_6_nodes(DS)** | 36 | 6 | 36 | 0 | 6 | 7 | 7 |
| **MEKG_with_8_nodes(DS3)** | 64 | 8 | 64 | 0 | 8 | 18 | 18 |
| **MEKG_with_8_nodes(DS4)** | 64 | 8 | 64 | 0 | 8 | 23 | 23 |
| **MEKG_with_8_nodes(logic)** | 64 | 8 | 64 | 0 | 8 | 15 | 15 |
| **MEKG_with_10_nodes(DS1)** | 100 | 10 | 100 | 0 | 10 | 29 | 29 |
| **MEKG_with_10_nodes(DS2)** | 100 | 10 | 100 | 0 | 10 | 19 | 19 |
| **MEKG_with_18_nodes(ML)** | 324 | 18 | 324 | 0 | 18 | 76 | 76 |
| **MEKG_with_21_nodes(ML)** | 441 | 21 | 441 | 0 | 21 | 138 | 138 |
| **MEKG_with_35_nodes(ML1)** | 1,225 | 35 | 1,225 | 0 | 35 | 244 | 244 |

### Notes on Special Conditions
1. **DSA Duplicate Row:** Line 251 and 252 contain identical row `binary_search_tree;recursion;1`. `duplicate_rows` increments to 1; `GoldJudgmentSet` records it idempotently; `ConceptGraph` contains 54 distinct positive edges.
2. **DSA Missing Ordered Row:** `('binary_search_tree', 'asymptotic_complexity')` is omitted from the file. Verified:
   - `judgment_for_edge('asymptotic_complexity', 'binary_search_tree')` is `None`.
   - `judgment_for_edge('binary_search_tree', 'asymptotic_complexity')` is `False` (reverse row exists labeled 0).
3. **Cartesian Product in Examples:** All 10 example files contain exactly $N \times N$ lines and $N$ self-loop rows, all labeled `0`.

---

## 4. Read-Only Checks (Requirement 6)

### 6a. `MEKG_with_8_nodes(logic).txt` Directionality Analysis
Because `MEKG_with_8_nodes(logic).txt` has 0% node overlap with DSA and Metacademy, its directionality was evaluated using pedagogical logic domain semantics across its 15 positive edges.

Six concrete examples:
1. `propositional_logic.txt;first_order_logic.txt;1`  
   **Analysis:** Propositional logic (truth tables, Boolean connectives) is universally introduced prior to first-order predicate logic (quantifiers, variable bindings, signatures). Column 1 is prerequisite, Column 2 is dependent.
2. `first_order_logic.txt;semantics_of_first_order_logic.txt;1`  
   **Analysis:** The formal syntax of first-order languages must be defined before defining model-theoretic semantics (structures, interpretations, satisfaction). Column 1 is prerequisite, Column 2 is dependent.
3. `propositional_logic.txt;propositional_proofs.txt;1`  
   **Analysis:** The formulas and language of propositional logic are prerequisite to constructing deduction trees or proofs in propositional logic. Column 1 is prerequisite, Column 2 is dependent.
4. `proofs_in_first_order_logic.txt;Godel's_completeness_theorem.txt;1`  
   **Analysis:** The formal deduction system ($\vdash$) in FOL must be established before stating or proving Gödel's Completeness Theorem ($\vdash \phi \iff \models \phi$). Column 1 is prerequisite, Column 2 is dependent.
5. `semantics_of_first_order_logic.txt;Godel's_completeness_theorem.txt;1`  
   **Analysis:** Model satisfaction ($\models$) must be defined before stating that semantic validity coincides with syntactic derivability. Column 1 is prerequisite, Column 2 is dependent.
6. `countable_sets.txt;Godel's_completeness_theorem.txt;1`  
   **Analysis:** Enumerating formulas and adding Henkin witnesses in the completeness proof requires foundational set-theoretic countability. Column 1 is prerequisite, Column 2 is dependent.

**Conclusion:** All 15 edges consistently show Column 1 as the prerequisite and Column 2 as the dependent concept. The orientation matches D-19 natively. Nothing suggests reversal.

### 6b. Acyclicity and Transitive Redundancy
All 12 corpora were tested for directed acyclicity (`is_acyclic()`) and transitive reduction redundancy (`num_edges - transitive_reduction_edges`):

| Corpus | Nodes ($N$) | Positive Edges ($E$) | Is Acyclic (DAG)? | Redundant Edges | Reduction Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: |
| DSA_gold_standard_MEKG | 29 | 54 | **True** | 14 | 25.9% |
| metacademy_gold_standard_MEKG | 141 | 318 | **True** | 105 | 33.0% |
| MEKG_with7nodes | 7 | 16 | **True** | 8 | 50.0% |
| MEKG_with_6_nodes(DS) | 6 | 7 | **True** | 2 | 28.6% |
| MEKG_with_8_nodes(DS3) | 8 | 18 | **True** | 9 | 50.0% |
| MEKG_with_8_nodes(DS4) | 8 | 23 | **True** | 13 | 56.5% |
| MEKG_with_8_nodes(logic) | 8 | 15 | **True** | 6 | 40.0% |
| MEKG_with_10_nodes(DS1) | 10 | 29 | **True** | 16 | 55.2% |
| MEKG_with_10_nodes(DS2) | 10 | 19 | **True** | 10 | 52.6% |
| MEKG_with_18_nodes(ML) | 18 | 76 | **True** | 54 | 71.1% |
| MEKG_with_21_nodes(ML) | 21 | 138 | **True** | 107 | 77.5% |
| MEKG_with_35_nodes(ML1) | 35 | 244 | **True** | 195 | 79.9% |

**Observations:**
- Every single corpus produces a valid DAG without cycles.
- DSA (14/54) and Metacademy (105/318) match the figures reported in `INFRA-001`.
- The smaller example files contain high transitive redundancy (up to 79.9% in ML1), consistent with manual or unreduced labeling where intermediate transitive edges were preserved.

### 6c. Case and Punctuation Collision Audit
All 88 unique concept names across the 10 example files were inspected:
- Case-folding check: **0 collisions** (no names differ only by upper/lower case).
- Punctuation/alphanumeric normalization check: **0 collisions** (no names differ only by underscores, hyphens, or apostrophes).
- Apostrophe names: `Godel's_completeness_theorem` (in logic file) and `stirling's_approximation` (in DSA) remain distinct and well-formed.

### 6d. Load Time Benchmarks (Setup Cost for INFRA-004)
Measured across 5 repeated runs using `load_corpus()`:
- `metacademy_gold_standard_MEKG`: **107.0 ms** (dominant, due to 19,740 pairwise rows).
- `MEKG_with_35_nodes(ML1)`: **6.9 ms**.
- `MEKG_with_21_nodes(ML)`: **2.9 ms**.
- `DSA_gold_standard_MEKG`: **2.2 ms**.
- `MEKG_with_18_nodes(ML)`: **1.8 ms**.
- `MEKG_with7nodes`: **1.6 ms**.
- All remaining 6 example files: **< 1.0 ms** each.

Trial initialization in `INFRA-004` can either reuse pre-loaded instances via `ConceptGraph.copy()` (which copies in $<0.1$ ms) or reload directly, as setup overhead is negligible.

---

## 5. Domain Context Decision ([D-27]) & Proposal for 7-Node File

The domain context table was formalized in `[D-27]` in `docs/decisions/decision-log.md`:
- Files with explicit tags inherit canonical strings (`DS` -> `"data structures and algorithms"`, `ML` -> `"machine learning"`, `logic` -> `"mathematical logic"`).
- `MEKG_with7nodes.txt` has no tag in its filename. Its concept list is:
  `['bayes_rule', 'bayesian_networks', 'conditional_independence', 'conditional_probability', 'independent_events', 'probability', 'random_variable']`.
- **Proposal for Luke:** While these concepts form the probabilistic graphical models subset of Metacademy, setting default to `None` avoids guessing. If Luke confirms a domain string during thesis experiments, `"machine learning"` or `"probability and graphical models"` can be passed explicitly in `CorpusSpec`.

---

## 6. Verification & Test Results

The test suite was run with the new loader tests and retrofitted fixtures:
```bash
PYTHONPATH=src pytest
```
Output:
```
100 passed in 1.88s
```
- 40 tests in `test_graph_representation.py` (retrofitted with dataset skip conditions).
- 34 tests in `test_strategy_interface.py`.
- 26 tests in `test_loader.py` covering discovery, parsing, pinned stats, missing pair edge semantics, determinism, and error cases.

---

## 7. Diffs of Edited Shared Docs

### A. `docs/decisions/decision-log.md`
```diff
@@ -229,4 +229,13 @@
 
 **[D-26]** Strategy interface hardening & embedder injection contract: (1) `insert_node` requires keyword-only `metered_embedder: Optional[MeteredEmbedder]`; passing `None` explicitly indicates an unmetered run, and any strategy embedding activity during such runs raises `RuntimeError`; (2) candidate shortlists are validated by the driver before invoking the decision step (candidates must be a subset of current graph nodes, contain no duplicates, and exclude the new concept); (3) decided edges are strictly validated before mutating `ConceptGraph` (edges must be canonical 2-tuples, non-self-loops, no duplicates, involve `new_name`, and have the other endpoint present in `shortlist.candidates`); failure raises `ValueError` and leaves `ConceptGraph` unchanged without notifying the strategy; (4) single-embedding invariant: strategies embedding `new_name` must compute its embedding at most once per insertion (cached in `shortlist()`, reused in `on_inserted()`), verified by `embed_in_update_s == 0.0`; (5) `apply_s` timing explicitly captures graph mutation overhead in `InsertionMetrics`, ensuring `total_s ≈ shortlist_s + decide_s + apply_s + update_s`. Reasoning: guarantees fail-fast trial isolation, protects `ConceptGraph` topology from hallucinated or invalid LLM decision edges, prevents double-embedding performance inflation in STRAT-002..004, and achieves complete timing attribution across all insertion phases. Affects: `insert_node`, `InsertionMetrics`, `StrategyConformanceSuite`, INFRA-002, FIX-002, STRAT-001 through STRAT-004.
 
+**[D-27]** Corpus domain context mapping table locked: graph-level domain context strings ([D-21]) are assigned across the 12 evaluation corpora as follows:
+(1) `DSA_gold_standard_MEKG` -> `"data structures and algorithms"`;
+(2) `metacademy_gold_standard_MEKG` -> `"machine learning and supporting mathematics"`;
+(3) Example files with `DS` tags (`MEKG_with_6_nodes(DS)`, `MEKG_with_8_nodes(DS3)`, `MEKG_with_8_nodes(DS4)`, `MEKG_with_10_nodes(DS1)`, `MEKG_with_10_nodes(DS2)`) -> `"data structures and algorithms"`;
+(4) Example files with `ML` tags (`MEKG_with_18_nodes(ML)`, `MEKG_with_21_nodes(ML)`, `MEKG_with_35_nodes(ML1)`) -> `"machine learning"`;
+(5) `MEKG_with_8_nodes(logic)` -> `"mathematical logic"`;
+(6) `MEKG_with7nodes` -> `None`. Reasoning: files with explicit subject tags inherit standard domain phrases; `MEKG_with7nodes` lacks any filename tag, so rather than guessing between 'machine learning' and 'probability theory', its default is set to `None` (proposing 'machine learning' for thesis evaluation pending Luke's confirmation). Affects: `loader.py`, `CORPUS_DOMAIN_CONTEXT_MAP`, `derive_domain_context()`, INFRA-003, INFRA-004.
```

### B. `docs/tasks/status.md`
```diff
@@ -31,2 +31,2 @@
-| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **open** | Unblocked: INFRA-001 is done. Loader must construct `ConceptGraph` using `oriented_edge(source_kind, col1, col2)` per D-15, D-16, D-19, and D-23. Also populate `GoldJudgmentSet` for accuracy evaluation.                                                                                                              |
-| INFRA-004 | Build the measurement harness (sweep runner: given a strategy module, run it across all graph-size checkpoints, log time/call-count/accuracy, emit one results row per strategy-size pair).                                                                                                                                                                                                                                                                   | **open** | Depends on INFRA-002. Trial isolation requires a fresh strategy instance plus a deep copy of the graph (`ConceptGraph.copy()`). Can be scaffolded in parallel with INFRA-003 once INFRA-002 is locked, since the harness's shape depends on the interface, not the corpus's internals. |
+| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **done** | Completed by Gemini. Discovers 12 corpora, loads into `ConceptGraph` and `GoldJudgmentSet` with strict parsing, canonical orientations via `oriented_edge` ([D-15], [D-19], [D-23]), and graph-level domain context table ([D-27]). All 12 graphs confirmed DAGs. See report [`docs/reports/INFRA-003-gemini-corpus-loader.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-003-gemini-corpus-loader.md). |
+| INFRA-004 | Build the measurement harness (sweep runner: given a strategy module, run it across all graph-size checkpoints, log time/call-count/accuracy, emit one results row per strategy-size pair).                                                                                                                                                                                                                                                                   | **open** | Unblocked: INFRA-002 and INFRA-003 are done. Trial isolation requires a fresh strategy instance plus a deep copy of the graph (`ConceptGraph.copy()`). Corpus setup costs known (<7ms for 11 corpora, ~107ms for Metacademy). |
```

---

## 8. Found but Not Changed / Attention Flags

1. **`MEKG_with7nodes.txt` domain context proposal:**
   Currently assigned `None` per [D-27]. Luke should confirm whether to set it to `"machine learning"` or `"probability and graphical models"` before running the sweep in `INFRA-004`.
2. **Missing DSA pair in accuracy scoring:**
   The loader correctly marks `('asymptotic_complexity', 'binary_search_tree')` as `None` (missing/unjudged). How this missing row is evaluated during test-suite placement metrics remains reserved for Luke.
3. **Commit status:**
   All new files and modifications remain uncommitted in the local working copy.
