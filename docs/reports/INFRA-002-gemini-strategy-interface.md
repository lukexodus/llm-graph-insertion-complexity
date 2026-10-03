# INFRA-002 Report: Strategy Interface Contract & Conformance Harness

## Executive Summary
Task INFRA-002 locked the strategy interface contract, lifecycle protocol, and timing/metrics accounting model for all four candidate-narrowing strategies and the null baseline. Strategies are strictly narrowing modules that read `ConceptGraph` immutably and never call an LLM ([D-24]); relationship decisions are deferred to a shared external `DecisionStep` ([D-02]). We delivered `src/graph_insertion/embedding.py` (`Embedder`, `MeteredEmbedder`, deterministic `FakeEmbedder`), `src/graph_insertion/strategy.py` (`Shortlist`, `DecisionOutcome`, `InsertionMetrics`, `InsertionResult`, and the `insert_node` sequencing driver), and `ConceptGraph.copy()` for trial isolation. A one-page specification was authored at `docs/context/strategy-interface.md`. A comprehensive conformance suite was added in `tests/test_strategy_interface.py`, expanding the test suite to 62 tests (100% passing). Decisions [D-24] and [D-25] were recorded.

---

## 1. Interface Design and Implementation

### 1.1 Strategy Contract and Lifecycle ([D-24])
The `NarrowingStrategy` protocol mandates five core methods:
- `setup(graph: ConceptGraph, embedder: Embedder) -> None`: Untimed initialization (builds initial index/embeddings/buckets). Must read `graph` without mutating it.
- `shortlist(new_name: str) -> Shortlist`: Retrieves existing candidate concepts for `new_name`. Precondition: `new_name` is not already in the graph. Must not mutate the graph.
- `on_inserted(new_name: str, edges: tuple[tuple[str, str], ...]) -> None`: Incremental post-insertion hook allowing the strategy to update its internal index/state.
- `config() -> dict[str, Any]`: Emits hyperparameters (e.g. threshold, $k$, bucket cap, seed) for reporting.
- `diagnostics() -> dict[str, Any]`: Emits operational telemetry (e.g. number of comparisons, bucket ID, split flags).

### 1.2 Separation of Narrowing from Decision
Strategies never call an LLM directly. Once `shortlist()` returns candidate concept names, the shared driver passes them to `DecisionStep.decide(new_name, candidates, domain_context) -> DecisionOutcome`. The driver adds the new node and canonical edges (`prereq -> dependent`, [D-23]) to `ConceptGraph`, then calls `strategy.on_inserted(new_name, edges)`.

An empty shortlist (e.g. when similarity is below threshold) is explicitly supported: the driver bypasses the decision step, recording 0 LLM calls, 0 edges, and `decide_s = 0.0`.

### 1.3 Trial Isolation & Graph Copy
Trial isolation in the sweep harness (INFRA-004) requires each insertion trial to start from an isolated graph copy and a freshly initialized strategy. We added `ConceptGraph.copy()` returning an independent deep copy of the underlying `nx.DiGraph` and verified that mutations to the copy do not leak into the original.

### 1.4 Embedder Protocols & Accounting ([D-25])
All embedding operations route through an injected `Embedder`:
- `Embedder` protocol: defines `embed(text: str) -> np.ndarray` (1D float32) and `embed_many(texts: Sequence[str]) -> np.ndarray` (2D float32).
- `MeteredEmbedder`: transparent wrapper tracking cumulative calls, texts embedded, and wall-clock execution time (`cumulative_seconds`).
- `FakeEmbedder`: deterministic, offline pseudo-embedding generator using SHA-256 text hashing and local PRNG normalization for testing.
- `numpy>=1.26` added to package dependencies in `pyproject.toml`.

### 1.5 Timing Accounting Model ([D-25])
All insertion timings use `time.perf_counter()`. Component timings are tracked separately in `InsertionMetrics`:
- `embed_s`: Wall-clock time spent embedding `new_name` during narrowing (from meter).
- `shortlist_s`: Total wall-clock time for `strategy.shortlist()` (includes `embed_s`).
- `decide_s`: Wall-clock time awaiting LLM response in `decision_step.decide()` (0.0 if shortlist is empty).
- `update_s`: Wall-clock time for incremental state upkeep in `strategy.on_inserted()`.
- `total_s`: End-to-end wall-clock time for the full insertion operation.
- Initial index construction (`setup()`) is excluded from insertion timing.

---

## 2. Audit of Thesis Chapter 3

### 2.1 Strategy 4 Narrowing Audit (Section 3.2.5)
- **Prompt Question:** Does the Strategy 4 adaptation need an LLM during candidate narrowing?
- **Finding:** **No.** Direct review of thesis Section 3.2.5 confirms that Strategy 4 adapts EraRAG's bounded-bucket partitioning *structural principle* (size cap $B$, split on overflow, merge on underflow) to concept-node insertion. Bucket assignment and partitioning during candidate narrowing operate via vector similarity / centroids, without calling an LLM. The LLM is only called during the shared final decision step (Section 3.2.6).

### 2.2 Shared Decision Step Ambiguities (Section 3.2.6)
1. **Call Granularity:**
   - Section 3.2.2 mentions querying the LLM *"one at a time"* for Strategy A's baseline.
   - Section 3.2.6 states: *"an LLM is prompted with the new concept and each shortlisted candidate, and asked to determine whether a relationship exists and, if so, its type."*
   - It is ambiguous whether the prompt is sent pairwise ($k$ calls for $k$ candidates) or batched in a single prompt containing all $k$ candidates.
   - **Resolution:** Left strictly neutral. `DecisionStep.decide` takes the tuple of candidates and returns `DecisionOutcome(edges, llm_calls, llm_seconds)`. The strategy interface does not constrain call granularity.
2. **Relation Types:**
   - Section 3.2.6 states the LLM determines whether a relationship exists *"and, if so, its type."*
   - In Chapters 1–3, the research design and gold standard datasets evaluate exclusively binary prerequisite relationships. Flagged for alignment under task DOC-002.

---

## 3. Decisions Reserved for Luke

The following design decisions were explicitly not decided and remain reserved for Luke:
1. **LLM Call Granularity:** Pairwise prompt per candidate vs. single batched prompt for the entire shortlist. (The `DecisionOutcome.llm_calls` field captures actual API calls made in either configuration).
2. **Decision Step Concurrency:** Any asynchronous / parallel execution of LLM queries within the decision step.
3. **Evaluation Scoring for DSA Missing Pair:** How the single omitted ordered pair `(binary_search_tree, asymptotic_complexity)` is scored in precision/recall calculations (whether treated as label 0 or omitted from evaluation denominators).

---

## 4. Test Suite and Conformance Verification

We implemented a full conformance test suite in `tests/test_strategy_interface.py`:
- `test_fake_embedder_dimension_and_norm`: verifies 1D array shape and unit $L_2$ norm.
- `test_fake_embedder_determinism`: confirms identical outputs across instances with same seed.
- `test_fake_embedder_embed_many`: verifies 2D matrix shape and row consistency.
- `test_metered_embedder_accounting`: confirms call counting, text counting, timing accumulation, and meter reset.
- `test_shortlist_is_subset_and_excludes_new_node`: verifies candidates are existing nodes, non-empty, unique, and exclude `new_name`.
- `test_shortlist_does_not_mutate_graph`: confirms graph node/edge counts remain identical across `shortlist()`.
- `test_new_name_already_in_graph_raises`: confirms inserting an already-present concept raises `ValueError`.
- `test_same_seed_gives_same_shortlist`: verifies deterministic candidate selection given identical seeds.
- `test_repeated_inserts_see_previous_nodes`: verifies sequential insertions incrementally update graph topology and index visibility.
- `test_edges_involve_new_node_and_are_canonical`: confirms edges are canonical and connect to `new_name`.
- `test_edge_not_involving_new_node_raises`: verifies driver rejects edges that do not involve `new_name`.
- `test_empty_shortlist_legal_and_skips_decision_calls`: verifies that an empty shortlist bypasses the decision step (0 calls, 0 edges, `decide_s = 0.0`).
- `test_timing_and_metrics_consistency`: validates timing component inequalities (`embed_s <= shortlist_s` and `total_s >= sum(components)`).

**Test Execution:** All 62 unit tests (48 from INFRA-001/FIX-001 + 14 new conformance tests) passed in 2.90s.

---

## 5. Found But Not Changed

1. **Thesis Section 3.2.6 Wording:** Mentions deciding relationship "type"; queued for DOC-002.
2. **Missing DSA Pair Evaluation Treatment:** Reserved for Luke.
3. **New task INFRA-006 added:** Created in `docs/tasks/status.md` to house the shared decision step implementation and LLM client prior to strategy development.
4. **Catalogue #9 and Logic MEKG Notes:** Appended to DOC-002 in `docs/tasks/status.md`.

---

## 6. Diffs of Edited Shared Docs

### Diff for `pyproject.toml`
```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -6,7 +6,10 @@
 name = "graph-insertion"
 version = "0.1.0"
 requires-python = ">=3.12"
-dependencies = ["networkx>=3.0"]
+dependencies = [
+    "networkx>=3.0",
+    "numpy>=1.26",
+]
 
 [project.optional-dependencies]
 dev = ["pytest>=9.0", "pytest-cov"]
```

### Diff for `docs/context/complete-context.md`
```diff
--- a/docs/context/complete-context.md
+++ b/docs/context/complete-context.md
@@ -119,6 +119,7 @@
     ├── context/                      ← you are here; standalone context for agents
     │   ├── complete-context.md       (this file)
     │   ├── data-formats.md           (settled data-format findings)
+    │   ├── strategy-interface.md     (formal strategy contract & lifecycle spec)
     │   └── apc-handoff-template.md   (template for APC-to-APC session handoffs)
     ├── decisions/
     │   └── decision-log.md           (append-only; WHY past decisions were made)
```

### Diff for `docs/decisions/decision-log.md`
```diff
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -222,4 +222,8 @@
 **[D-22]** Graph library locked: NetworkX (`nx.DiGraph`) wrapped in a domain-specific `ConceptGraph` class. Reasoning: NetworkX is the standard Python graph library; evaluation against a custom adjacency dictionary shows NetworkX adds negligible overhead at n=2000 (a 2000-node chain builds in <0.005s, neighbour lookups are O(1)), well below experimental timing noise, while providing battle-tested implementations of topological sorting, cycle detection, and DAG validation. The `ConceptGraph` wrapper encapsulates the representation and enforces domain invariants (e.g. disallowing positive self-loops). Affects: INFRA-001, INFRA-002, INFRA-003, INFRA-004, and all strategy modules.
 
 **[D-23]** Canonical internal edge direction locked: an edge `(u, v)` means "u is a prerequisite of v" (prerequisite -> dependent). Reasoning: matches the ten example MEKG files natively ([D-19]), and ensures that a topological sort yields a valid pedagogical learning sequence. This explicitly resolves the ambiguity in [D-15]'s phrase "standardize on this directionality" (which settled raw file interpretation but left internal representation orientation uncommitted). The corpus loader (INFRA-003) maps raw file rows into this canonical direction via `oriented_edge(source_kind, col1, col2)`. Affects: `ConceptGraph`, INFRA-002, INFRA-003, INFRA-004.
+
+**[D-24]** Strategy interface contract & lifecycle locked: candidate-narrowing strategies implement candidate shortlisting and internal index upkeep (`setup`, `shortlist`, `on_inserted`), read `ConceptGraph` immutably, and never call an LLM. Reasoning: thesis Section 3.2.6 defines the shared LLM decision step as the controlled variable held constant across all strategies; placing the decision step outside strategy modules guarantees identical prompt structure and decision mechanics while isolating the narrowing mechanism under test. Affects: INFRA-002, INFRA-004, INFRA-005, INFRA-006, STRAT-001 through STRAT-004.
+
+**[D-25]** Insertion timing and metrics accounting model locked: timed insertion covers candidate narrowing (including embedding the new concept), the shared decision step, driver graph edge application, and the strategy's incremental update (`on_inserted`). Initial graph indexing (`setup()`) is excluded as pre-trial preparation. Reasoning: matches thesis Section 3.4 measurement definition while isolating incremental insertion cost from batch initialization; breaking down `embed_s`, `shortlist_s`, `decide_s`, `update_s`, and `total_s` via `time.perf_counter()` disentangles retrieval overhead from LLM latency. Affects: INFRA-002, INFRA-004, STRAT-001 through STRAT-004.
```

### Diff for `docs/tasks/status.md`
```diff
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -30,4 +30,5 @@
-| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **open** | Unblocked: INFRA-001 is done. Strategies operate on `ConceptGraph`, ingest/emit bare concept names ([D-21]), and obtain embedding strings via `embed_text()`.                                                                                                                                                           |
+| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **done** | Completed. Strategy contract, lifecycle, Embedder protocol, MeteredEmbedder, FakeEmbedder, and insert_node driver defined ([D-24], [D-25]). Conformance suite passes (62 tests). See spec [`docs/context/strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/strategy-interface.md) and report [`docs/reports/INFRA-002-gemini-strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-002-gemini-strategy-interface.md). |
 | INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                  | **open** | Unblocked: INFRA-001 is done. Loader must construct `ConceptGraph` using `oriented_edge(source_kind, col1, col2)` per D-15, D-16, D-19, and D-23. Also populate `GoldJudgmentSet` for accuracy evaluation.                                                                                                              |
-| INFRA-004 | Build the measurement harness (sweep runner: given a strategy module, run it across all graph-size checkpoints, log time/call-count/accuracy, emit one results row per strategy-size pair).                                                                                                                                                                                                                                                                   | **open** | Depends on INFRA-002. Can be scaffolded in parallel with INFRA-003 once INFRA-002 is locked, since the harness's shape depends on the interface, not the corpus's internals. |
-| INFRA-005 | Build and run the trivial "null strategy" (e.g., attach new node to a random existing node) through the full harness, end-to-end, at all graph sizes.                                                                                                                                                                                                                                                                                                         | **open** | This is Phase 1's EXIT CRITERION — Phase 2 (the four real strategies) should not start until this passes cleanly. Depends on INFRA-001 through INFRA-004.                    |
+| INFRA-004 | Build the measurement harness (sweep runner: given a strategy module, run it across all graph-size checkpoints, log time/call-count/accuracy, emit one results row per strategy-size pair).                                                                                                                                                                                                                                                                   | **open** | Depends on INFRA-002. Trial isolation requires a fresh strategy instance plus a deep copy of the graph (`ConceptGraph.copy()`). Can be scaffolded in parallel with INFRA-003 once INFRA-002 is locked, since the harness's shape depends on the interface, not the corpus's internals. |
+| INFRA-005 | Build and run the trivial "null strategy" (e.g., attach new node to a random existing node) through the full harness, end-to-end, at all graph sizes.                                                                                                                                                                                                                                                                                                         | **open** | This is Phase 1's EXIT CRITERION — Phase 2 (the four real strategies) should not start until this passes cleanly. Depends on INFRA-001 through INFRA-004, and INFRA-006 (or a stub). |
+| INFRA-006 | Build the shared decision step (the identical final step all four strategies use) and its metered LLM client: prompt semantics (is A a prerequisite of B, indirect allowed, since the gold graphs are not transitively reduced per INFRA-001), call granularity (reserved for Luke), parsing, call and time metering.                                                                                                                                         | **open** | Depends on INFRA-002. Must precede STRAT-001 to STRAT-004; INFRA-005 can use a stub.                                                                                                                                                                                                                                         |
@@ -70,3 +71,3 @@
-| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). | **open** | Prompt not yet written; can wait until after INFRA-001. |
+| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; and note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked. | **open** | Prompt not yet written; can wait until after INFRA-001. |
```
