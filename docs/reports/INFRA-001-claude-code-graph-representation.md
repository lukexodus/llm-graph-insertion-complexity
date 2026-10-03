# INFRA-001 Report: Graph Representation & Semantic Invariants

## Executive Summary
Task INFRA-001 locked the in-memory graph representation and core semantic invariants for the LLM graph-insertion complexity study. NetworkX `DiGraph` was selected as the internal graph engine, wrapped in a domain-specific `ConceptGraph` class that enforces node invariants (bare concept names, [D-21]) and canonical edge directionality (`(u, v)` = `u is a prerequisite of v`, [D-23]). The dual-mapping rule (`oriented_edge`) was implemented for `GOLD` ([D-15]) and `MEKG_EXAMPLE` ([D-19]) sources and validated against real file rows and cross-source pairs (42/42 matches, 0 conflicts). A 3-state `GoldJudgmentSet` was implemented for accuracy evaluation. Empirical audits verified that gold prerequisite graphs are strict DAGs (acyclic, 0 positive self-loops), but neither DSA (25.9% transitive edges) nor Metacademy (33.0% transitive edges) is transitively reduced. A complete Python package scaffold with 38 passing pytest unit tests was established.

---

## 1. Library Evaluation and In-Memory Shape Choice

We evaluated two candidate architectures for this project's in-memory graph representation:

| Criterion | NetworkX (`nx.DiGraph`) | Thin Custom Class (`dict[str, set[str]]`) |
| :--- | :--- | :--- |
| **Data scale (~2000 nodes)** | Handles $10^5+$ nodes easily; 2000 nodes uses < 2 MB RAM. | Extremely lightweight; uses < 500 KB RAM. |
| **Node / Edge Iteration** | `G.nodes()`, `G.edges()` return fast views. | `dict.keys()`, comprehension over sets. |
| **Insertion Overhead** | `add_node`: ~0.3 µs; `add_edge`: ~0.8 µs. Chain of 2000 nodes builds in ~3.8 ms. | `add_node`: ~0.1 µs; `add_edge`: ~0.3 µs. |
| **Timing Distortion** | Insertion overhead (< 1 µs per node/edge) is negligible compared to embedding inference (~5–50 ms) and LLM API calls (~500–2000 ms). Will not distort wall-clock measurements. | Negligible overhead. |
| **Neighbour Queries** | `predecessors(n)` and `successors(n)` are $O(1)$ dict lookups. | Requires maintaining two dicts (`in_edges`, `out_edges`) manually. |
| **Graph Algorithms** | Built-in DAG check (`is_directed_acyclic_graph`), topological sort, transitive reduction, cycle detection, path search. | Must implement and maintain cycle detection, topological sorting, and transitive reachability from scratch. |
| **Standardization** | Standard Python graph library; familiar to any reviewer or examiner. | Custom code requiring bespoke maintenance and testing. |

### Decision ([D-22])
We chose **NetworkX (`nx.DiGraph`) encapsulated inside a domain-specific `ConceptGraph` class**.
- Encapsulation hides NetworkX's mutable internals while providing high-level domain methods: `add_node(name)`, `add_prereq_edge(prereq, dependent)`, `prerequisites_of(name)`, `dependents_of(name)`, and `is_acyclic()`.
- Positive self-loops (`u -> u`) raise a `ValueError` immediately.
- The raw `nx.DiGraph` is accessible via `.nx_graph` property for algorithms not yet wrapped.

---

## 2. Representation Details & Semantic Rules

### 2.1 Node Payload ([D-21])
A node is represented purely by its canonical concept name (string, with any `.txt` suffix stripped). No text description, definition, or summary attribute is attached to nodes.
- Provided pure function `embed_text(name: str) -> str`: replaces underscores with spaces (e.g., `hash_table` $\to$ `hash table`) and preserves surface form (case, apostrophes, e.g. `Godel's_completeness_theorem` $\to$ `Godel's completeness theorem`).
- Per [D-21], `embed_text` does **not** append or prepend the domain context string.

### 2.2 Graph-Level Domain Context
`ConceptGraph` carries an optional `domain_context: str | None` field at the graph level (e.g. `"data structures and algorithms"` or `"machine learning"`). This field is reserved for the shared decision-step LLM prompt in later phases and is not stored per node.

### 2.3 Canonical Internal Edge Direction ([D-23])
An edge `(u, v)` internally signifies:
$$\mathbf{u \text{ is a prerequisite of } v} \quad (\text{prerequisite} \to \text{dependent})$$
- **Reasoning:**
  1. Matches the native directionality of the ten example MEKG files ([D-19]).
  2. In this orientation, a topological sort of the graph yields a valid pedagogical learning sequence (concepts appear after all their prerequisites).
  3. Resolves the ambiguity in [D-15]'s phrase "standardize on this directionality", which established gold file semantics but did not explicitly specify the internal edge representation.

### 2.4 The Dual-Mapping Rule (`oriented_edge`)
To bridge dataset differences into the canonical internal direction, `oriented_edge` implements:
- `SourceKind.GOLD`: Row `(col1, col2)` with `label=1` means `col2` is prerequisite of `col1` ([D-15]). Returns `(col2, col1)`.
- `SourceKind.MEKG_EXAMPLE`: Row `(col1, col2)` with `label=1` means `col1` is prerequisite of `col2` ([D-19]). Returns `(col1, col2)`.

**Cross-Source Consistency Verification:**
For all positive edges in the 10 example MEKG files whose concept pair also exists in DSA or Metacademy, we verified that `oriented_edge(MEKG_EXAMPLE, c1, c2) == oriented_edge(GOLD, dsa_c1, dsa_c2)`.
- **Result:** Exactly 42 overlapping pairs were checked across the files. **42/42 matched; 0 conflicts.**

### 2.5 Gold Judgment Representation (`GoldJudgmentSet`)
Accuracy evaluation requires distinguishing between positive judgments, negative judgments, and missing pairs:
- Implemented `GoldJudgmentSet` with a 3-state enum: `_Label.ONE` (prerequisite), `_Label.ZERO` (non-prerequisite), and `_Label.MISSING` (pair not in dataset).
- `record(col1, col2, label)` enforces idempotency for duplicate rows with the same label (e.g. `binary_search_tree;recursion;1` in DSA lines 251/252), and raises a `ValueError` if duplicate rows have conflicting labels.
- `is_prerequisite(col1, col2) -> bool | None` returns `True` for 1, `False` for 0, and `None` for unjudged.
- The single missing pair in DSA (`binary_search_tree`, `asymptotic_complexity`) returns `_Label.MISSING` / `None`, distinguishing it cleanly from `_Label.ZERO`.

---

## 3. Read-Only Data Measurements

### 3.1 Acyclicity & Self-Loops in Gold Standards
We analyzed the positive-edge graphs of both gold standard datasets when converted to canonical directed edges (`prereq -> dependent`):
- **DSA Gold Standard (`DSA_gold_standard_MEKG.txt`):**
  - Total positive edges: 54 (excluding self-loops)
  - Positive self-loops: **0** (all 29 diagonal self-loops in the file are labeled `0`)
  - Acyclic: **Yes (DAG)**
- **Metacademy Gold Standard (`metacademy_gold_standard_MEKG.txt`):**
  - Total positive edges: 318
  - Positive self-loops: **0** (no self-loops present in file)
  - Acyclic: **Yes (DAG)**

### 3.2 Transitive Redundancy in Gold Standards
We tested whether positive edges in the gold graphs are transitively reduced (i.e. whether an edge $u \to v$ exists when there is already a longer directed path $u \to \dots \to v$):
- **DSA Graph:**
  - Total positive edges: 54
  - Redundant (transitive) edges: **14** (25.9% of all positive edges)
  - *Examples:*
    - `('graph', 'strongly_connected_component')`: path exists via `depth_first_search` (`graph -> depth_first_search -> strongly_connected_component`)
    - `('asymptotic_complexity', 'dijkstra_algorithm')`: path exists via `graph` and `heap`
    - `('pointer', 'hash_table')`: path exists via `linked_list`
  - Transitively reduced: **No**
- **Metacademy Graph:**
  - Total positive edges: 318
  - Redundant (transitive) edges: **105** (33.0% of all positive edges)
  - *Examples:*
    - `('conditional_independence', 'markov_models')`
    - `('spectral_decomposition', 'principal_component_analysis')`
    - `('linear_approximation', 'convex_functions')`
  - Transitively reduced: **No**

**Implications for Shared Decision Prompt (Phase 2 & Chapter 3):**
Because ~26% to 33% of expert-verified prerequisite relationships are multi-hop transitive edges, the gold-standard ground truth reflects **pedagogical reachability/prerequisite dependency** rather than a strictly pruned Hasse diagram (transitive reduction). When prompting the LLM in the shared decision step, instructions should evaluate whether concept A is a prerequisite for understanding concept B, and not instruct the model to exclude indirect prerequisites unless transitive reduction is explicitly applied as a post-processing step.

### 3.3 Concept Name Matching Across Files
We audited all concept names across DSA (29 nodes), Metacademy (141 nodes), and the 10 example MEKG files (88 distinct stripped names):
- **Set Overlaps:**
  - DSA $\cap$ Metacademy: **0 concepts** (disjoint subject domains: CS algorithms vs. ML/statistics)
  - DSA $\cap$ Example MEKGs: **16 concepts** (`asymptotic_complexity`, `bloom_filter`, `breadth_first_search`, `depth_first_search`, `dijkstra_algorithm`, `graph`, `hash_table`, `heap`, `linked_list`, `minimum_spanning_tree`, `pointer`, `queue`, `recursion`, `stack`, `strongly_connected_component`, `tree`)
  - Metacademy $\cap$ Example MEKGs: **45 concepts** (e.g. `backpropagation`, `bases`, `bayesian_networks`, `chain_rule`, `gradient_descent`, `dot_product`)
- **Case and Punctuation Variants:**
  - Combined distinct concept count: 258 concepts.
  - Case-insensitive collision audit: **0 case collisions**. No concept appears with varying capitalization across files.
  - Exactly one concept begins with an uppercase letter: `Godel's_completeness_theorem` (in `MEKG_with_8_nodes(logic).txt`).
  - Apostrophes exist in `stirling's_approximation` (DSA) and `Godel's_completeness_theorem` (Logic MEKG); both parse without quotes and embed cleanly.

### 3.4 Scope of Relation Types
We audited thesis Section 3.2.6 ("The Shared Decision Step"):
- The text states: *"an LLM is prompted with the new concept and each shortlisted candidate, and asked to determine whether a relationship exists and, if so, its type."*
- However, throughout Chapters 1–3, the only evaluated relationship is the **prerequisite relationship** (directed binary edge: prerequisite or non-prerequisite).
- `ConceptGraph` maintains untyped directed edges representing prerequisites. If future phases evaluate relationship labels (e.g. `is_a`, `requires`), NetworkX edge attributes (`G.add_edge(u, v, relation_type="prerequisite")`) can store them without changing graph topology.

---

## 4. Embeddings Design Note (for INFRA-002 / INFRA-004)

The prompt asked for a note on what embedding storage options imply for the graph representation:
1. **Option A: Embedding vectors stored as node attributes on `ConceptGraph`**
   - *Implementation:* `cg.nx_graph.nodes[name]['embedding'] = np.ndarray(...)`
   - *Trade-offs:* Self-contained in one object. However, it couples the graph structure to embedding model dimensions, complicates graph serialization/copying, and bloats memory when swapping embedding models.
2. **Option B: Embeddings stored in strategy-owned structures (Recommended)**
   - *Implementation:* `ConceptGraph` remains pure topology. Strategy 2 (Threshold) maintains an embedding matrix/cache; Strategy 3 (ANN) maintains a FAISS index; Strategy 4 (Buckets) maintains embeddings in bucket nodes.
   - *Trade-offs:* Keeps graph data structures clean and independent of vector libraries. Cleanly separates representation from retrieval mechanism.
3. **Timing of Embeddings:**
   - If embedding the new candidate node is part of the insertion pipeline, its wall-clock time must be measured.
   - Pre-computed embeddings for existing nodes should be indexed prior to the insertion trial to measure pure incremental insertion cost.

---

## 5. Practicalities & Test Suite

- Created Python package structure with `pyproject.toml` targeting `src/graph_insertion`.
- Added `pythonpath = ["src"]` to `pyproject.toml` so pytest discovers `graph_insertion` without requiring editable pip install.
- Developed full test suite in `tests/test_graph_representation.py`:
  - 38 unit tests covering `oriented_edge` (with real file rows from DSA, Metacademy, and MEKG examples), cross-source consistency (42 pairs), `embed_text`, `ConceptGraph` lifecycle and performance (2000-node chain), and `GoldJudgmentSet` 3-state logic and error handling.
  - **Results:** 38 passed in 3.35s.

---

## 6. Prompt Assumptions Verified or Corrected

- `[D-21]` was verified present in `docs/decisions/decision-log.md` prior to starting work.
- Assumed internal edge direction `(u, v)` = prerequisite $\to$ dependent: confirmed valid, natural for topological sorting, and recorded as `[D-23]`.
- Assumed cross-source edge direction agreement: confirmed 100% agreement (42/42 pairs) with 0 conflicts.

---

## 7. Found But Not Changed

1. **Missing Pair in DSA (`binary_search_tree`, `asymptotic_complexity`):**
   - Identified in DATA-001. `GoldJudgmentSet` marks it as `_Label.MISSING`. Left flagged for Luke to decide whether evaluation treats missing pairs as label-0 (implicit non-prerequisite) or ignores them in accuracy metrics.
2. **Stale text in `complete-context.md` Section 4 and `data-formats.md`:**
   - Mentions build-phase source text as an open question; already tracked for cleanup under task DOC-002 in `docs/tasks/status.md`. Left untouched per prompt scope.

---

## 8. Diffs of Edited Shared Docs

### Diff for `docs/decisions/decision-log.md`
```diff
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -218,4 +218,8 @@
 `docs/reports/DATA-003-gemini-source-text-evidence.md`. Affects: INFRA-001/002
 (no text field on nodes), Chapter 3 Section 3.2.6 and Scope and Limitations
 (wording pending, see DOC-002), STRAT-002 to STRAT-004.
+
+**[D-22]** Graph library locked: NetworkX (`nx.DiGraph`) wrapped in a domain-specific `ConceptGraph` class. Reasoning: NetworkX is the standard Python graph library; evaluation against a custom adjacency dictionary shows NetworkX adds negligible overhead at n=2000 (a 2000-node chain builds in <0.005s, neighbour lookups are O(1)), well below experimental timing noise, while providing battle-tested implementations of topological sorting, cycle detection, and DAG validation. The `ConceptGraph` wrapper encapsulates the representation and enforces domain invariants (e.g. disallowing positive self-loops). Affects: INFRA-001, INFRA-002, INFRA-003, INFRA-004, and all strategy modules.
+
+**[D-23]** Canonical internal edge direction locked: an edge `(u, v)` means "u is a prerequisite of v" (prerequisite -> dependent). Reasoning: matches the ten example MEKG files natively ([D-19]), and ensures that a topological sort yields a valid pedagogical learning sequence. This explicitly resolves the ambiguity in [D-15]'s phrase "standardize on this directionality" (which settled raw file interpretation but left internal representation orientation uncommitted). The corpus loader (INFRA-003) maps raw file rows into this canonical direction via `oriented_edge(source_kind, col1, col2)`. Affects: `ConceptGraph`, INFRA-002, INFRA-003, INFRA-004.
```

### Diff for `docs/tasks/status.md`
```diff
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -29,3 +29,3 @@
-| INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                          | **open** | Unblocked: DATA-001 and DATA-002 are done. The representation must make the two source edge conventions (D-15 for DSA/Metacademy, D-19 for the example MEKG files) an explicit, testable mapping. Node payload is name only, no text ([D-21]). |
+| INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                          | **done** | Completed. Library locked as NetworkX via `ConceptGraph` wrapper ([D-22]); canonical edge direction locked as prereq -> dependent ([D-23]); dual-mapping implemented and verified without conflict against all 10 MEKG files. See report [`docs/reports/INFRA-001-claude-code-graph-representation.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-001-claude-code-graph-representation.md). |
-| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **open** | Depends on INFRA-001.                                                                                                                                                        |
+| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **open** | Unblocked: INFRA-001 is done. Strategies operate on `ConceptGraph`, ingest/emit bare concept names ([D-21]), and obtain embedding strings via `embed_text()`.                                                                                                                                                           |
-| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                  | **open** | Depends on INFRA-001. DATA-001 and DATA-002 are done; the loader must apply D-15, D-16, and D-19 (see `docs/context/data-formats.md`).                                                                                                                                                                            |
+| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                  | **open** | Unblocked: INFRA-001 is done. Loader must construct `ConceptGraph` using `oriented_edge(source_kind, col1, col2)` per D-15, D-16, D-19, and D-23. Also populate `GoldJudgmentSet` for accuracy evaluation.                                                                                                              |
```
