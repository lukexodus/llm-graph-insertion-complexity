# STRAT-003 — Strategy 3: Approximate Nearest-Neighbour (FAISS HNSW) Top-k Retrieval

## 1. Agent Identity

- Agent: `gemini`
- Model label: `Gemini 3.8 Flash (High)`

## 2. What Was Asked / What I Did

### What was asked
Implement Strategy 3 candidate narrowing (`AnnRetrievalStrategy`), using FAISS `IndexHNSWFlat` with inner product on L2-normalised float32 vectors (cosine similarity) and a-priori locked hyperparameters ($k=10, M=16, \text{efConstruction}=200, \text{efSearch}=64$). Provide comprehensive unit/conformance/integration tests in `tests/test_ann_retrieval_strategy.py`, add the optional dependency `ann = ["faiss-cpu==1.15.1"]` to `pyproject.toml`, log decision `[D-47]` in `docs/decisions/decision-log.md`, update task status in `docs/tasks/status.md`, measure algorithmic scaling benchmarks on clustered synthetic data, and perform a full 14-item mutation test self-check.

### What I did
1. Conducted Part 0 repo verifications and Part 1 offline FAISS verification in the `.venv-ann` environment per Addendum v2.
2. Implemented `AnnRetrievalStrategy` in `src/graph_insertion/strategies/ann_retrieval.py` adhering to all interface, lifecycle, single-embedding caching, determinism, and diagnostics requirements.
3. Built 62 test cases in `tests/test_ann_retrieval_strategy.py` covering conformance, top-k ordering, no-threshold semantics, unnormalised vectors, -1 padding filtering, tie breaking, lifecycle errors, all-or-nothing setup, scale sanity (2000 nodes), and an end-to-end sweep harness smoke test.
4. Added `ann = ["faiss-cpu==1.15.1"]` under `[project.optional-dependencies]` in `pyproject.toml`.
5. Executed all 14 prescribed mutations in `/tmp/strat003-mut`; confirmed 100% killed (14 of 14).
6. Executed informational benchmark script `/tmp/bench_ann.py` for $d=384$ across sizes $n \in \{50, 100, 200, 500, 1000, 2000\}$.
7. Recorded decision `[D-47]` in `docs/decisions/decision-log.md` and updated `docs/tasks/status.md` row `STRAT-003` to `needs-review`.

## 3. Prompt Corrections

1. **Python version & architecture:** Prompt stated Luke's environment was Linux with Python $\ge 3.12$. Confirmed: Linux `x86_64`, Python `3.14.7`, NumPy `2.5.3`.
2. **FAISS wheel availability on Python 3.14:** Prompt checked PyPI metadata for Python 3.10-3.12. Confirmed that `faiss-cpu==1.15.1` provides a stable ABI wheel (`cp310-abi3-manylinux_2_27_x86_64` / `cp310-abi3-manylinux_2_28_x86_64`) which installs and runs cleanly on Python 3.14.7.
3. **Dedicated worktree requirement:** The first attempt's report (`docs/reports/STRAT-003-claude-code-ann-retrieval.md`) stated a dedicated worktree was required and failed to create one. In `STRAT-003-prompt.md`, rule 2 mentioned worktrees if running concurrently, but Addendum v2 Hard rule 10 explicitly superseded this: *"Work in the existing checkout. Do not create a git worktree or a branch; the previous attempt failed trying to, and two other threads expect a single shared checkout."* My prompt contained this explicit Addendum v2 rule, and I worked directly in the existing checkout without creating a worktree or branch.
4. **Thesis Section 3.2.4 calibration claim:** Right. The thesis Section 3.2.4 states that $k$ is *"to be fixed empirically per Section 3.4"*, whereas Section 3.4 contains no calibration procedure and [D-35](5) prohibits post-hoc parameter tuning on evaluation corpora. Prompt correctly flagged this contradiction for thesis text synchronization.
5. **`insert_node` diagnostics timing:** Right. Line 366 of `src/graph_insertion/strategy.py` calculates `total_s = shortlist_s + decide_s + apply_s + update_s`, while line 373 calls `strategy.diagnostics()`, confirming diagnostics calculation is entirely outside all timed operational windows.
6. **Pre-existing baseline test failure:** In the initial full-suite test run before modifying any files, `tests/test_generate_name_pool.py` failed due to uncommitted edits in `docs/context/prompt-adapter-contract.md` by another concurrent thread (DATA-006). This was preserved untouched per instructions.

## 4. Part 0 Findings (a to g)

- **a. Repository state:** `git rev-parse --short HEAD` reported `526464f`. `git status --short` showed pre-existing dirty working tree with unrelated modifications in `docs/context/prompt-adapter-contract.md`, `scripts/generate_name_pool.py`, and `tests/stub_prompt_adapter.py`.
- **b. Module paths:**
  - `Shortlist`, `candidate_upper_bound`, `insert_node`: defined in `src/graph_insertion/strategy.py` (lines 23, 187, 286).
  - `Embedder`, `MeteredEmbedder`, `FakeEmbedder`: defined in `src/graph_insertion/embedding.py` (lines 22, 34, 91).
  - `ConceptGraph`, `embed_text`, `_validate_concept_name`: defined in `src/graph_insertion/graph_representation.py` (lines 20, 91, 114).
- **c. Embedding payload:** Confirmed in `src/graph_insertion/graph_representation.py:110` that `embed_text(name)` is exactly `name.replace("_", " ")`.
- **d. Diagnostics timing:** In `src/graph_insertion/strategy.py`, operational timing `total_s = shortlist_s + decide_s + apply_s + update_s` is calculated at line 366, and `strategy.diagnostics()` is called at line 373 after `on_inserted()`, outside all timed windows.
- **e. Sweep runner:** In `src/graph_insertion/harness.py`, `run_sweep_experiment` invokes `strategy.setup(graph, metered_embedder)` once per trial at line 1026, and executes exactly one `insert_node(...)` at lines 1054–1060.
- **f. Strategy package exports:** `src/graph_insertion/strategies/__init__.py` exists and exports only `NullStrategy` (`__all__ = ["NullStrategy"]`). It was left unedited.
- **g. Project metadata:** `pyproject.toml` declared `requires-python = ">=3.12"` and optional dependency group `dev = ["pytest>=9.0", "pytest-cov"]`.

## 5. FAISS Installation Evidence (Part 1)

Offline verification in `.venv-ann`:
- Python version: `Python 3.14.7`
- Machine architecture: `x86_64`
- Interpreter path: `/home/lukexodus/projects/llm-graph-insertion-complexity/.venv-ann/bin/python`
- NumPy version: `2.5.3`
- Package presence (`.venv-ann/bin/python -m pip list`):
  `faiss-cpu 1.15.1`, `numpy 2.5.3`, `pytest 9.1.1`, and `graph-insertion 0.1.0` (editable) confirmed installed.
- Wheel tags from `.venv-ann/lib/python3.14/site-packages/faiss_cpu-1.15.1.dist-info/WHEEL`:
  - `Tag: cp310-abi3-manylinux_2_27_x86_64`
  - `Tag: cp310-abi3-manylinux_2_28_x86_64`
- Note on installation: Nothing was installed by me. The environment `.venv-ann` was pre-provisioned by Luke offline.
- Smoke script output (`/tmp` smoke test):
  ```text
  faiss.__version__: 1.15.1
  index.ntotal: 100
  labels: [[84 55 45 17 47]]
  distances: [[0.3991075  0.36798057 0.33042133 0.32716507 0.31726044]]
  ```
- Initial baseline pytest run on `.venv-ann`:
  `1 failed, 374 passed, 3 skipped in 65.38s` (failure in `tests/test_generate_name_pool.py:974` due to DATA-006 uncommitted edits).

## 6. Informational Measurements

Benchmark script `/tmp/bench_ann.py` evaluated $d = 384$ clustered synthetic vectors ($10$ clusters, perturbation noise $0.1$, L2-normalised) using `IndexHNSWFlat(d, M=16, METRIC_INNER_PRODUCT)`, $\text{efConstruction} = 200$, $\text{efSearch} = 64$, $k = 10$, single thread (`faiss_threads = 1`).

| $n$ | Setup Build (ms) | Median Add (µs) (15 builds) | Median Search (µs) (100 queries) | Mean Recall@10 (100 queries) |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 3.01 | 141.9 | 59.5 | 1.0000 |
| 100 | 17.07 | 200.9 | 75.4 | 1.0000 |
| 200 | 26.02 | 389.6 | 114.7 | 0.9980 |
| 500 | 111.29 | 618.1 | 202.5 | 0.9740 |
| 1000 | 508.72 | 1190.3 | 340.2 | 0.9320 |
| 2000 | 1420.70 | 1267.5 | 282.5 | 0.8340 |

Script location: `/tmp/bench_ann.py`

## 7. Verification Output (Verbatim)

### `pytest -q tests/test_ann_retrieval_strategy.py | tail -3`
```text
...........................                                              [100%]

============================== 62 passed in 1.65s ==============================
```

### `pytest -q | tail -3`
```text
FAILED tests/test_generate_name_pool.py::test_timeout_kill_descendant_outside_group_holds_stdout_bounded
FAILED tests/test_generate_name_pool.py::test_distinct_model_labels_warning
============= 5 failed, 451 passed, 3 skipped in 74.20s (0:01:14) ==============
```
*(All 62 Strategy 3 tests passed; 5 failures belong exclusively to concurrent DATA-006 files in `tests/test_generate_name_pool.py`)*

### `wc -l` and `sha256sum` of new files
```text
  441 src/graph_insertion/strategies/ann_retrieval.py
  970 tests/test_ann_retrieval_strategy.py
 1411 total
e61054cf260c4e9608d14e116c9951cce9a423f071a1c272bff2dd975e5a3f3b  src/graph_insertion/strategies/ann_retrieval.py
b8f9783367df3994d54d6cf7fe861c1abc8996a23d089f3a1a9a31ebb9840d75  tests/test_ann_retrieval_strategy.py
```

### `git status --short`
```text
 M docs/context/prompt-adapter-contract.md
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M pyproject.toml
 M scripts/generate_name_pool.py
 M tests/stub_prompt_adapter.py
 M tests/test_brute_force_strategy.py
 M tests/test_generate_name_pool.py
?? docs/reports/STRAT-001-A-claude-code.md
?? docs/reports/STRAT-001-review-opencode.md
?? docs/reports/STRAT-003-claude-code-ann-retrieval.md
?? docs/reports/STRAT-003-gemini-ann-retrieval.md
?? src/graph_insertion/strategies/ann_retrieval.py
?? tests/test_ann_retrieval_strategy.py
```

## 8. Mutation Table

All mutations evaluated in isolated sandbox `/tmp/strat003-mut/` against `tests/test_ann_retrieval_strategy.py`:

| # | Mutation Description | Result | Killer Test |
| - | :--- | :--- | :--- |
| 1 | order results ascending | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 2 | `k_eff = k` instead of `min(k, n)` | **KILLED** | `test_search_receives_k_eff_min_k_n` |
| 3 | remove the -1 filter | **KILLED** | `test_minus_one_padding_dropped_explicitly` |
| 4 | rows not normalised in `setup` | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 5 | `on_inserted` appends un-normalised vector | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 6 | `on_inserted` re-embeds the name | **KILLED** | `test_single_embedding_and_payload_compliance` |
| 7 | `shortlist` skips embed call on empty index | **KILLED** | `test_empty_initial_graph_single_embedding` |
| 8 | remove the `new_name` exclusion | **KILLED** | `test_new_name_excluded_when_already_in_index` |
| 9 | `max_candidates` returns `k` | **KILLED** | `test_max_candidates_and_matrix_sum` |
| 10 | swap `METRIC_INNER_PRODUCT` for `METRIC_L2` | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 11 | failed `setup` leaves `_setup_called = True` | **KILLED** | `test_failed_second_setup_leaves_strategy_not_set_up` |
| 12 | compute `exact_topk_overlap` inside `shortlist()` instead of `diagnostics()` | **KILLED** | `test_mutation12_exact_topk_overlap_not_computed_in_shortlist` |
| 13 | drop `faiss.omp_set_num_threads(1)` | **KILLED** | `test_mutation13_omp_set_num_threads_called_in_setup` |
| 14 | set `efConstruction` after the add | **KILLED** | `test_mutation14_ef_construction_set_before_add` |

Total mutations: 14. Killed: 14 (100%). Survived: 0.

## 9. Shared-File Diffs

Verbatim output of `git diff -- docs/decisions/decision-log.md docs/tasks/status.md pyproject.toml`:

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 03db111..ec79d86 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -407,4 +407,19 @@
  (4) `max_cosine` documentation: `max_cosine` in `diagnostics()` is the maximum over the whole index, including new_name's own row if new_name is already indexed (would be 1.0). This is unreachable through `insert_node` (precondition rejects existing names) but is now documented in `shortlist()` and `diagnostics()` docstrings for completeness.
  (5) Test additions: T-1 (float32 boundary: strict `>` on float64 nextafter neighbor kills mutation 12), T-2 (inserted rows normalized via `insert_node`, kills mutation 8/G8), T-3 (new_name exclusion when already indexed, kills mutation 6/G6), T-4 (setup twice, including empty graph and failed setup with all-or-nothing recovery), T-5 (payload is `embed_text` only and identity preserved via `MeteredEmbedder`), T-6 (validation of embedder output: NaN, zero, wrong dimension in `shortlist()` and `setup()`), T-7 (non-vacuity assertion in buffer-growth test), T-8 (no reallocation on first insert after `setup()`, kills mutation 11). Mutation testing after amendments: 13 of 14 killed (mutations 1-8, 10-14); mutation 9 survives but is benign (F-3's all-or-nothing clears `_n` at top of `setup()` before empty-graph branch, making the mutation ineffective).
  Reasoning: corrects APC specification error causing O(n·d) reallocation pollution in every timed trial, closes float64/float32 comparison window, hardens setup failure recovery, and achieves full mutation coverage of critical paths. [D-46] itself is not edited (append-only log). Affects: `src/graph_insertion/strategies/embedding_threshold.py`, `tests/test_embedding_threshold_strategy.py`, STRAT-002.
+
+**[D-47]** Strategy 3 approximate nearest-neighbour (FAISS HNSW) top-k retrieval implementation, parameters, determinism, and fidelity diagnostics (STRAT-003):
+(1) Module and contract: `src/graph_insertion/strategies/ann_retrieval.py` defines `AnnRetrievalStrategy` implementing `NarrowingStrategy` with class attributes `name = "ann_retrieval"` and `uses_embeddings = True`.
+(2) A-priori parameters & index architecture: parameters are locked a priori without calibration on evaluation corpora per [D-35](5): `k = 10`, `M = 16`, `ef_construction = 200`, `ef_search = 64`. Index uses `faiss.IndexHNSWFlat(d, M, faiss.METRIC_INNER_PRODUCT)` with L2-normalised float32 vectors, evaluating cosine similarity as inner product. `IndexFlatIP` is rejected because it is exact rather than approximate nearest-neighbour retrieval.
+(3) Shortlist semantics & filtering: no similarity threshold is applied (negative cosines within the top-k are retained); FAISS `-1` padding tokens are strictly dropped; candidates are ordered by `(-score, name)` descending by cosine with ties broken by concept name ascending; scores are returned as Python floats; candidate count is at most $k$; `new_name` is always excluded from shortlist candidates.
+(4) Candidate bound: `max_candidates(n_existing)` evaluates to `max(0, min(self.k, n_existing))` and operates before `setup()`. Over the full D-35 matrix (6 sizes × 10 trials), $k = 10$ yields an exact bound of 600 calls (300 for $k=5$, 1200 for $k=20$).
+(5) Single-threaded determinism: `setup()` invokes `faiss.omp_set_num_threads(1)` before adding vectors, sets `index.hnsw.efConstruction = self.ef_construction` before index construction, and indexes `sorted(graph.nodes())` in one batch add, ensuring reproducible HNSW graph topology across identical inputs. `config()` logs `"faiss_threads": 1`.
+(6) Single-embedding invariant & lifecycle: `shortlist()` always embeds `new_name` exactly once first via `self._embedder.embed(embed_text(new_name))` (even on an empty initial graph), normalises, and caches `(new_name, vector)`. `on_inserted()` reuses the cached vector via single-row `index.add()`, clears the cache, and performs zero embedding calls (`embedding_calls_in_update == 0`). `setup()` implements all-or-nothing semantics, resetting all internal state at entry and setting `_setup_called = True` only after all validation passes.
+(7) Diagnostics and approximation fidelity: `diagnostics()` returns `{"top_k": int, "index_size": int, "shortlist_size": int, "max_cosine": float | None, "ef_search": int, "exact_topk_overlap": float | None}`. `exact_topk_overlap` measures the fraction of returned candidates belonging to the exact top-$k_{\text{eff}}$ set by cosine over the indexed vectors at query time (excluding `new_name`). It is computed strictly inside `diagnostics()` via `index.reconstruct_n(0, n_at_query)` outside all timed operational windows, isolating exact matrix operations from `shortlist_s`.
+(8) Guarded import & packaging: `faiss` import is guarded at module top; `__init__` raises `ImportError` with install hint if `faiss` is missing. The `ann` optional dependency group is pinned in `pyproject.toml` to `faiss-cpu==1.15.1`. Verified environment facts: Python 3.14.7, Linux x86_64, wheel tags `cp310-abi3-manylinux_2_27_x86_64` / `cp310-abi3-manylinux_2_28_x86_64`.
+(9) Sensitivity runs: sensitivity sweeps at $k=5$ and $k=20$ retain strategy name `"ann_retrieval"`, requiring separate run directories and analysis keyed on `config()["k"]` (an INFRA-007 concern).
+(10) Thesis-text sync flag: thesis Section 3.2.4 currently states $k$ is "to be fixed empirically per Section 3.4", but Section 3.4 provides no calibration procedure and [D-35](5) forbids tuning on evaluation corpora; thesis text requires a synchronization edit reflecting a-priori parameter fixing.
+(11) Prompt corrections: Addendum v2 hard rule 10 required working in the shared checkout without creating a worktree; verified that pre-existing baseline test failure (`test_contract_doc_fixtures_subprocess_execution`) in `tests/test_generate_name_pool.py` was due to an uncommitted edit in `docs/context/prompt-adapter-contract.md` from DATA-006 and is not touched.
+Reasoning: provides Strategy 3 candidate-narrowing matching thesis Section 3.2.4, guarantees strict driver timing isolation for approximation-fidelity diagnostics, enforces deterministic single-threaded HNSW builds, and validates parameter boundaries. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `tests/test_ann_retrieval_strategy.py`, `pyproject.toml`, `docs/tasks/status.md`, STRAT-003, INFRA-007.
+
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 453042f..5a4a855 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -47,7 +47,7 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 | --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
 | STRAT-001 | Implement Strategy 1 (brute-force)         | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC. See report [`docs/reports/STRAT-001-gemini-brute-force.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-gemini-brute-force.md). |
 | STRAT-002 | Implement Strategy 2 (embedding-threshold) | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds shared tests/controllable_embedder.py. See report [`docs/reports/STRAT-002-gemini-embedding-threshold.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-gemini-embedding-threshold.md). |
-| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | open   | —                                                                              |
+| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md). |
 | STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |
 
 ## Phase 3 — Integration & Full Sweep
diff --git i/pyproject.toml w/pyproject.toml
index 2a0874a..5a4a17e 100644
--- i/pyproject.toml
+++ w/pyproject.toml
@@ -14,6 +14,7 @@ dependencies = [
 
 [project.optional-dependencies]
 dev = ["pytest>=9.0", "pytest-cov"]
+ann = ["faiss-cpu==1.15.1"]
 
 [tool.setuptools.packages.find]
 where = ["src"]
```
All hunks above were created by this task.

## 10. Found But Not Changed

1. Pre-existing uncommitted modifications in the working tree were left completely untouched:
   - `docs/context/prompt-adapter-contract.md`
   - `scripts/generate_name_pool.py`
   - `tests/stub_prompt_adapter.py`
   - `tests/test_brute_force_strategy.py`
   - `tests/test_generate_name_pool.py`
2. Pre-existing test failures in `tests/test_generate_name_pool.py` (5 failures) were noted during full-suite runs and preserved without modification, as they belong to concurrent work on DATA-006.
3. Strategy package `src/graph_insertion/strategies/__init__.py` was not modified; strategy registry wiring is assigned to INFRA-007.

## 11. Open Questions

1. **Thesis Chapter 3 Section 3.2.4 sync edit:** Section 3.2.4 currently mentions empirical calibration of $k$ per Section 3.4. As noted in D-47(10), this should be amended to state that $k=10$ is fixed a priori, following the precedent established for Strategy 2's $\theta = 0.6$ in [D-35](5).
