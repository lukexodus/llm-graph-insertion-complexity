# STRAT-003-R — Independent Review of Strategy 3 (FAISS HNSW ANN Retrieval)

## 1. Agent Identity

- **Agent:** `gemini`
- **Model label as displayed:** `Gemini 3.1 Pro (High)`
- **Lineage confirmation:** I am **not** the implementing Gemini session (which ran under `Gemini 3.8 Flash (High)`). However, I am **not** a non-Gemini model; this session is running on Google DeepMind's Gemini model family (`Gemini 3.1 Pro (High)`). As instructed by the prompt ("if you cannot, say so plainly in section 1 of your report. Report the model label exactly as your tool displays it, or `unknown`; do not guess"), this is stated plainly here so the APC is aware that this review comes from a fresh, higher-tier Gemini model session rather than Claude Code or opencode.

---

## 2. Verdict

**Verdict: ACCEPT WITH AMENDMENTS**

The three most important reasons:
1. **Core algorithmic correctness and contract compliance:** The Strategy 3 implementation (`AnnRetrievalStrategy` in `src/graph_insertion/strategies/ann_retrieval.py`) is exceptionally clean, robust, and mathematically sound. It adheres to all strategy interface contracts ([D-21], [D-24], [D-25], [D-26], [D-28], [D-35], [D-41], [D-47]): single-embedding invariant holds, determinism is enforced via single-threaded builds and sorted concept ingest, scores are native float cosines ordered by `(-score, name)`, negative cosines are preserved without thresholding, and the candidate pre-flight bound is strictly $600$ calls over the full D-35 sweep matrix. All 62 Strategy 3 tests pass.
2. **Defect F-1 (`should-fix`): Stale cached vector after failed `shortlist()`:** In `AnnRetrievalStrategy.shortlist()`, `self._cached_new_name` and `self._cached_new_vec` are only assigned at lines 304–305 after vector validation. If a valid `shortlist("good")` succeeds and a subsequent `shortlist("bad")` raises `ValueError` during embedding validation, the cache still retains `"good"`. Consequently, a later call `on_inserted("good", ())` erroneously succeeds instead of raising `RuntimeError`. The required fix is trivial: invalidate the cached vector at the top of `shortlist()`.
3. **Rigorous verification across independent reference and mutation testing:** An independent float64 reference benchmark verified exact agreement with cosine scores (maximum discrepancy $< 1.8 \times 10^{-7}$, well within float32 precision, $0$ deviations $> 1 \times 10^{-5}$ across 1,200 query probes). Across 19 evaluated mutations, 16 were killed; the 3 survivors (mutations 15, 17, and 18) were thoroughly analyzed and reflect minor testing coverage omissions in lifecycle sequences rather than structural bugs in the implementation.

---

## 3. Findings Table

| ID | Severity | File:Line | Evidence | Suggested Change |
| :--- | :--- | :--- | :--- | :--- |
| **F-1** | `should-fix` | `src/graph_insertion/strategies/ann_retrieval.py:268-270` | If `shortlist("a")` succeeds (caching `"a"`), and a subsequent call `shortlist("b")` raises `ValueError` on an invalid vector (e.g. zero-norm or non-finite), `self._cached_new_name` and `self._cached_new_vec` are never cleared. `on_inserted("a", ())` will then succeed despite the contract stating that a failed shortlist must leave no cached vector. Confirmed via reproducer script `/tmp/check_b_investigation.py`. | Add `self._cached_new_name = None` and `self._cached_new_vec = None` at line 270 (immediately alongside `self._cached_exact_topk_overlap = None`) at the entry of `shortlist()`. |
| **F-2** | `nit` | `src/graph_insertion/strategies/ann_retrieval.py:348` | `self._last_max_cosine` takes the maximum over `valid_dists` from raw FAISS search results before `new_name` is excluded from the returned candidates. If `new_name` was already indexed, `max_cosine` reports `1.0`. While unreachable through `insert_node` (precondition rejects existing nodes), the docstring does not document this edge case, whereas Strategy 2 explicitly documents it per [D-50](4). | Document in `shortlist()` and `diagnostics()` docstrings that `max_cosine` is the maximum over the whole index including `new_name`'s own row if already indexed. |
| **F-3** | `nit` | `tests/test_ann_retrieval_strategy.py:757-770` | In `test_exact_topk_overlap_lifecycle`, `diagnostics()` is called immediately after `shortlist()` without an intervening `on_inserted()`. At that moment, `strat._index.ntotal == strat._n_at_query`. Consequently, Mutation 18 (`reconstructed = self._index.reconstruct_n(0, self._index.ntotal)`) survives. In real usage via `insert_node`, `on_inserted()` is called before `diagnostics()`, so `_index.ntotal == _n_at_query + 1`. | Add an assertion in `test_exact_topk_overlap_lifecycle` calling `on_inserted()` before `diagnostics()` to verify `exact_topk_overlap` reconstructs only the $n$ vectors present at query time. |
| **F-4** | `nit` | `tests/test_ann_retrieval_strategy.py:455-520` | Mutation 15 (omitting cache clearing `_cached_new_name = None; _cached_new_vec = None` at the top of `setup()`) survived because the existing test suite does not exercise the lifecycle sequence `setup() -> shortlist() -> setup() -> on_inserted()`. | Add a test in `TestSetupSemantics` verifying that a second `setup()` invalidates any vector cached from a previous setup session. |

---

## 4. Checks A to J (Verbatim Output & Detailed Findings)

### Check A: Integrity

Verification of `sha256sum`, `wc -l`, git commit status, and diff on shared files:

```bash
$ sha256sum src/graph_insertion/strategies/ann_retrieval.py tests/test_ann_retrieval_strategy.py
e61054cf260c4e9608d14e116c9951cce9a423f071a1c272bff2dd975e5a3f3b  src/graph_insertion/strategies/ann_retrieval.py
b8f9783367df3994d54d6cf7fe861c1abc8996a23d089f3a1a9a31ebb9840d75  tests/test_ann_retrieval_strategy.py

$ wc -l src/graph_insertion/strategies/ann_retrieval.py tests/test_ann_retrieval_strategy.py
  441 src/graph_insertion/strategies/ann_retrieval.py
  970 tests/test_ann_retrieval_strategy.py
 1411 total

$ git log -1 --oneline bf78a4a
bf78a4a STRAT-003: Strategy 3 approximate nearest-neighbour (FAISS HNSW) top-k retrieval (D-47)
```

**Git commit state:** The implementation work **is committed** in commit `bf78a4a` on `main`.
Inspection of `git diff bf78a4a~1..bf78a4a -- docs/decisions/decision-log.md docs/tasks/status.md pyproject.toml` confirms that commit `bf78a4a` touched strictly and exclusively STRAT-003's designated hunks:
- `docs/decisions/decision-log.md`: appended D-47 only (+15 lines).
- `docs/tasks/status.md`: updated the STRAT-003 row only (`open` -> `needs-review`).
- `pyproject.toml`: added one line `ann = ["faiss-cpu==1.15.1"]` under `[project.optional-dependencies]`.

---

### Check B: Code Review Against the Specification

Line-by-line review of `src/graph_insertion/strategies/ann_retrieval.py` confirms:
- `name = "ann_retrieval"` (line 102), `uses_embeddings = True` (line 103).
- Guarded import at lines 66–69; `__init__` raises informative `ImportError` at line 114 if `faiss is None`.
- Strict parameter validation: `isinstance(val, bool)` and non-`int` are rejected with `ValueError` (lines 125, 130). Minimum values ($k \ge 1$, $M \ge 2$, $\text{efConstruction} \ge 1$, $\text{efSearch} \ge 1$) enforced.
- Embedder injection contract: `self._embedder = embedder` (line 244) stores the exact object passed to `setup()`.
- One `embed_many` call during `setup()` on a non-empty graph (line 208) and zero calls on an empty graph (line 195).
- `shortlist()` always embeds `new_name` exactly once first via `self._embedder.embed(embed_text(new_name))` (line 272).
- FAISS padding tokens (`label == -1`) are strictly dropped (line 331).
- Ordered strictly by `(-score, name)` descending by cosine with tie-breaking by concept name ascending (line 340).
- Candidate count is at most $k$; scores are converted to native Python `float` (line 337).
- `max_candidates(n_existing)` computes `max(0, min(self.k, n_existing))` (line 200) without requiring `setup()`.
- `on_inserted()` makes zero embedding calls; consumes and clears `self._cached_new_vec` (lines 377–379).
- `config()` and `diagnostics()` contain only native Python types (`int`, `float`, `str`, `None`).

**Investigation of points 1–5:**
1. **Stale cache after failed `shortlist()` (Point 1):**
   **CONFIRMED DEFECT (Finding F-1).** Running `/tmp/check_b_investigation.py` yielded:
   ```text
   === Point 1: Stale cache after failed shortlist ===
   After valid shortlist('good_node'): _cached_new_name=good_node
   shortlist('fail_node') raised ValueError as expected: Zero-norm embedding vector for concept 'fail_node'
   After failed shortlist: _cached_new_name=good_node
   CONFIRMED DEFECT: on_inserted('good_node') SUCCEEDED because stale cache survived!
   ```
   The existing test `test_failed_shortlist_leaves_no_cached_vector` tested a failed shortlist on a fresh strategy instance where `_cached_new_name` was initially `None`, so it failed to detect that an existing cache is not invalidated on entry.
2. **Lazy index creation before validation completes (Point 2):**
   **CONFIRMED CLEAN.** On an empty graph setup, `self._index` and `self._dim` remain `None`. In `shortlist()`, lines 274–282 validate `raw_vec` (ndarray, 1-D, finite, non-zero norm) *before* lines 290–299 instantiate `faiss.IndexHNSWFlat`. If vector validation fails, `_index` is never created.
3. **`max_cosine` includes `new_name` if already indexed (Point 3):**
   **CONFIRMED (Finding F-2).** Querying an existing node yields `max_cosine = 1.0` (as observed: `max_cosine when querying existing node 'alpha': 1.0`), because `max_cosine` is taken over `valid_dists` from the raw search results prior to `new_name` candidate exclusion.
4. **`diagnostics()` after `on_inserted` (Point 4):**
   **CONFIRMED EQUIVALENT.** Running `/tmp/check_b_investigation.py` confirmed that `reconstruct_n(0, self._n_at_query)` retrieves exactly the vectors present at query time. Because FAISS sequential `add` assigns contiguous IDs starting from 0, subsequent inserts at indices $\ge n_{\text{at\_query}}$ do not disturb indices $0 \dots n_{\text{at\_query}} - 1$. The overlap matches an independent NumPy exact top-k both before and after subsequent inserts.
5. **Other defects:** None found.

---

### Check C: Test Suite Execution & Independent Failure Verification

Running `tests/test_ann_retrieval_strategy.py` in `.venv-ann`:
```bash
$ .venv-ann/bin/python -m pytest -q tests/test_ann_retrieval_strategy.py | tail -3
...........................                                              [100%]

============================== 62 passed in 2.14s ==============================
```

Running the full repository test suite in `.venv-ann`:
```bash
$ .venv-ann/bin/python -m pytest -q | tail -3
FAILED tests/test_generate_name_pool.py::test_offline_fake_refuses_default_output_path
ERROR tests/test_generate_name_pool.py::test_merged_meta_fidelity_requested_fields
========= 1 failed, 458 passed, 3 skipped, 1 error in 77.41s (0:01:17) =========
```

Running the test suite excluding `tests/test_generate_name_pool.py`:
```bash
$ .venv-ann/bin/python -m pytest --ignore=tests/test_generate_name_pool.py -q | tail -3
.....                                                                    [100%]

======================= 415 passed, 3 skipped in 15.76s ========================
```

**Verification of failures:**
- The 2 failing tests are:
  1. `tests/test_generate_name_pool.py::test_offline_fake_refuses_default_output_path`
  2. `tests/test_generate_name_pool.py::test_merged_meta_fidelity_requested_fields`
- Inspection of `git diff --stat tests/test_generate_name_pool.py` reveals 374 lines modified (363 insertions, 11 deletions) belonging to uncommitted work from DATA-006 / FIX-013 / FIX-014.
- None of the failing tests touch or import `AnnRetrievalStrategy`, FAISS, or Strategy 3.
- All 415 tests across the remainder of the repository pass without error.

---

### Check D: Independent Reference Benchmark

Evaluated in scratch script `/tmp/check_d_ref.py` against float64 NumPy exact cosine top-10 across 100 query probes per configuration ($k=10, M=16, \text{efConstruction}=200, \text{efSearch}=64$):

```text
d= 64 | dist=clustered | n=  50 | mean_overlap=1.0000 | all_sorted=True | max_diff=1.46e-07 | >1e-5: 0
d= 64 | dist=clustered | n= 500 | mean_overlap=1.0000 | all_sorted=True | max_diff=1.79e-07 | >1e-5: 0
d= 64 | dist=clustered | n=2000 | mean_overlap=1.0000 | all_sorted=True | max_diff=1.72e-07 | >1e-5: 0
d= 64 | dist=gaussian  | n=  50 | mean_overlap=1.0000 | all_sorted=True | max_diff=7.73e-08 | >1e-5: 0
d= 64 | dist=gaussian  | n= 500 | mean_overlap=1.0000 | all_sorted=True | max_diff=8.58e-08 | >1e-5: 0
d= 64 | dist=gaussian  | n=2000 | mean_overlap=0.9810 | all_sorted=True | max_diff=8.15e-08 | >1e-5: 0
d=384 | dist=clustered | n=  50 | mean_overlap=1.0000 | all_sorted=True | max_diff=7.33e-08 | >1e-5: 0
d=384 | dist=clustered | n= 500 | mean_overlap=1.0000 | all_sorted=True | max_diff=8.19e-08 | >1e-5: 0
d=384 | dist=clustered | n=2000 | mean_overlap=0.9970 | all_sorted=True | max_diff=8.45e-08 | >1e-5: 0
d=384 | dist=gaussian  | n=  50 | mean_overlap=1.0000 | all_sorted=True | max_diff=4.47e-08 | >1e-5: 0
d=384 | dist=gaussian  | n= 500 | mean_overlap=0.9940 | all_sorted=True | max_diff=3.89e-08 | >1e-5: 0
d=384 | dist=gaussian  | n=2000 | mean_overlap=0.8390 | all_sorted=True | max_diff=5.33e-08 | >1e-5: 0
```

**Key takeaways:**
1. In all 12 experimental conditions, every returned candidate list is strictly sorted by `(-score, name)`.
2. The maximum difference between returned float32 cosine scores and double-precision float64 cosines is $1.79 \times 10^{-7}$ (well within float32 machine epsilon $\approx 1.19 \times 10^{-7}$). Exactly zero scores differed by more than $1 \times 10^{-5}$.
3. Mean overlap for $d=384$, isotropic Gaussian, $n=2000$ was $0.8390$, precisely matching the $\approx 0.83$ reported by the APC.

---

### Check E: Recall Context Analysis (Informational)

Evaluated in `/tmp/check_e_recall.py` in Python 3.14.7 with `faiss-cpu==1.15.1`:

```text
=== Check E: Recall sensitivity at n=2000, d=384, efConstruction=200, M=16 ===
dist=gaussian     | efSearch= 64 | recall@10=0.8470
dist=gaussian     | efSearch=128 | recall@10=0.9630
dist=gaussian     | efSearch=256 | recall@10=1.0000
dist=clustered_10 | efSearch= 64 | recall@10=1.0000
dist=clustered_10 | efSearch=128 | recall@10=1.0000
dist=clustered_10 | efSearch=256 | recall@10=1.0000
dist=clustered_5  | efSearch= 64 | recall@10=0.9930
dist=clustered_5  | efSearch=128 | recall@10=0.9990
dist=clustered_5  | efSearch=256 | recall@10=1.0000

=== Check E: Recall sensitivity at n=500, d=384 ===
dist=gaussian     | efSearch= 64 | recall@10=0.9940
dist=gaussian     | efSearch=128 | recall@10=0.9990
dist=clustered_10 | efSearch= 64 | recall@10=1.0000
dist=clustered_10 | efSearch=128 | recall@10=1.0000
```

**Observations:**
- `/tmp/bench_ann.py` from the implementer's session was purged, but line 69 of `docs/reports/STRAT-003-gemini-ann-retrieval.md` documented its generator: "10 clusters, perturbation noise 0.1, L2-normalised".
- The recall gap is purely data-dependent: on clustered distributions, recall@10 is $0.993 \dots 1.000$ at $\text{efSearch}=64$. On uniformly dispersed isotropic Gaussians at $n=2000$, $\text{efSearch}=64$ yields $\approx 0.847$, which climbs to $0.963$ at $\text{efSearch}=128$ and $1.000$ at $\text{efSearch}=256$.
- This confirms the APC's hypothesis: the divergence between generators is intrinsic to HNSW graph connectivity in different geometric data distributions, not an implementation flaw.

---

### Check F: Determinism and Threading

Output from `/tmp/check_f_determinism.py`:
```text
=== Check F: Determinism and threading ===
os.cpu_count(): 8
Initial faiss.omp_get_max_threads(): 8
faiss.omp_get_max_threads() after setup(): 1
Two strategies return identical shortlists for 100 probes: True

--- Investigating Mutation 13 (omitting omp_set_num_threads(1)) ---
Multi-threaded index.add produced IDENTICAL search results in 5 trials (or differences are rare/subtle).

--- Investigating Mutation 14 (setting efConstruction AFTER add) ---
Setting efConstruction after add produces different search results: False
```

**Assessment of spy-based tests for Mutations 13 and 14:**
- On this 8-core host, default `faiss.omp_get_max_threads()` is 8. After `setup()`, it is strictly 1.
- In FAISS HNSW, multi-threaded `add` introduces thread-scheduling nondeterminism in graph edge creation; however, on small or moderate datasets, 5 consecutive runs with 8 threads produced identical top-10 candidate shortlists.
- Similarly, setting `efConstruction` after `add` leaves HNSW built with default `efConstruction=40` instead of `200`. On small graphs ($n \le 100$), `efConstruction=40` still finds identical top-10 candidates.
- Therefore, a purely behavioural (non-spy) test on unit test fixtures would either be flaky or survive. The implementer's choice of spy-based checks (`test_mutation13_omp_set_num_threads_called_in_setup` and `test_mutation14_ef_construction_set_before_add`) is necessary and justified.

---

### Check G: Mutation Check

Evaluated in `/tmp/strat003r-mut` across all 19 mutations using `/tmp/run_all_mutations.py` and `/tmp/test_mut6.py`:

| # | Mutation Description | Result | Killer Test |
| - | :--- | :--- | :--- |
| 1 | results ascending | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 2 | `k_eff = k` | **KILLED** | `test_search_receives_k_eff_min_k_n` |
| 3 | no -1 filter | **KILLED** | `test_minus_one_padding_dropped_explicitly` |
| 4 | rows not normalised in setup | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 5 | on_inserted stores un-normalised vector | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 6 | on_inserted re-embeds | **KILLED** | `test_cached_embedding_reuse_single_embedding_per_insert` |
| 7 | shortlist skips embed on empty index | **KILLED** | `test_empty_initial_graph_single_embedding` |
| 8 | no new_name exclusion | **KILLED** | `test_new_name_excluded_when_already_in_index` |
| 9 | max_candidates returns k | **KILLED** | `test_max_candidates_and_matrix_sum` |
| 10 | METRIC_L2 | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 11 | failed setup leaves `_setup_called = True` | **KILLED** | `test_failed_second_setup_leaves_strategy_not_set_up[zero_row]` |
| 12 | overlap computed inside shortlist() | **KILLED** | `test_exact_topk_overlap_lifecycle` |
| 13 | no `omp_set_num_threads(1)` | **KILLED** | `test_faiss_omp_threads_set_to_one` |
| 14 | `efConstruction` set after add | **KILLED** | `test_mutation14_ef_construction_set_before_add` |
| 15 | delete cache clearing at setup top | **SURVIVED** | `-` |
| 16 | delete `_index = None` at setup top | **KILLED** | `test_setup_nonempty_then_empty` |
| 17 | delete `_names = [] / _name_to_idx = {}` at setup top | **SURVIVED** | `-` |
| 18 | `diagnostics()` uses `_index.ntotal` instead of `_n_at_query` | **SURVIVED** | `-` |
| 19 | shortlist forgets to refresh `_last_query_vec` | **KILLED** | `test_exact_topk_overlap_lifecycle` |

**Analysis of survivors:**
- **Mutation 15:** Observable through the public API. If a caller calls `shortlist("a")`, then re-runs `setup()` with a new graph, and subsequently calls `on_inserted("a", ())`, it will succeed without a new `shortlist("a")`. (Finding F-4).
- **Mutation 17:** Not observable on successful setup because lines 240–241 unconditionally overwrite `self._names = list(nodes)` and `self._name_to_idx = {name: i ...}`. On a failed setup, `_setup_called` is set to `False` and `_embedder` is `None`, so any subsequent `shortlist()` or `on_inserted()` raises `RuntimeError`.
- **Mutation 18:** Observable through the public API when calling `shortlist()`, then `on_inserted()`, then `diagnostics()`. It survived because `test_exact_topk_overlap_lifecycle` queried `diagnostics()` immediately after `shortlist()` without intermediate insertion, so $n_{\text{indexed}} = n_{\text{at\_query}}$. (Finding F-3).

---

### Check H: Real Harness Smoke & Pre-flight Bound

Output from `/tmp/check_h_harness.py`:
```text
=== Check H: Real Harness Smoke & Pre-flight Bound ===
Harness status: completed
Total raw records: 4
All 4 records passed check: True
Sample extra diagnostics from record 0: {"top_k": 10, "index_size": 13, "shortlist_size": 10, "max_cosine": 0.35536032915115356, "ef_search": 64, "exact_topk_overlap": 1.0}
Pre-flight bound k=10 full_plan_bound: 600 (expected 600)
Pre-flight bound k=5 full_plan_bound: 300 (expected 300)
Pre-flight bound k=20 full_plan_bound: 1200 (expected 1200)
```

Across all 4 sweep records ($2 \text{ sizes} \times 2 \text{ trials}$):
- `status == "success"`
- `strategy == "ann_retrieval"`
- `shortlist_size == llm_calls == min(10, size)`
- `embedding_calls == 1`, `embedding_calls_in_update == 0`
- `metrics.extra["top_k"] == 10`
- `exact_topk_overlap` is present, native float, and JSON-clean.
- Pre-flight bounds evaluated via `compute_planned_calls_upper_bound` match exactly: 600 ($k=10$), 300 ($k=5$), 1200 ($k=20$).

---

### Check I: Timing Sanity & Timing Isolation

Output from `/tmp/check_i_timing.py` (median of 15 fresh setups each, $d=384$):
```text
=== Check I: Timing Sanity (15 fresh setups each) ===
Parameters: d=384, k=10, M=16, efConstruction=200, efSearch=64
n=  50 | Median shortlist() search:  270.7 µs | Median first on_inserted() add:  123.0 µs
n= 500 | Median shortlist() search:  400.8 µs | Median first on_inserted() add:  488.7 µs
n=2000 | Median shortlist() search:  820.1 µs | Median first on_inserted() add: 1374.0 µs
```

**Verification of timing window isolation in `src/graph_insertion/strategy.py`:**
- `shortlist_s` is timed at lines 294–297 (`t0 = time.perf_counter()`, `shortlist_res = strategy.shortlist(...)`, `t1 = time.perf_counter()`).
- `update_s` is timed at lines 354–357 (`t4 = time.perf_counter()`, `strategy.on_inserted(...)`, `t5 = time.perf_counter()`).
- `total_s = shortlist_s + decide_s + apply_s + update_s` is collated at line 366.
- `diag = strategy.diagnostics()` is invoked at line 373 in Step 5, strictly outside and after all timed intervals. The cost of `reconstruct_n` and matrix multiplication never enters `shortlist_s`, `update_s`, or `total_s`.

---

### Check J: Bookkeeping & Report Integrity

1. **D-47 factual statements:**
   - Parameter locks ($k=10, M=16, \text{efConstruction}=200, \text{efSearch}=64$): confirmed.
   - Bound evaluations (600 for $k=10$, 300 for $k=5$, 1200 for $k=20$): confirmed.
   - `config()` and `diagnostics()` keys: confirmed against lines 390–403 and 434–441.
   - Wheel tags (`cp310-abi3-manylinux_2_27_x86_64` / `cp310-abi3-manylinux_2_28_x86_64`) and Python 3.14.7 on Linux x86_64: confirmed from `.venv-ann/lib/python3.14/site-packages/faiss_cpu-1.15.1.dist-info/WHEEL`.
2. **Prompt corrections item 3 in implementer report:**
   - The implementer's report claimed that Addendum v2 Hard Rule 10 prohibited worktrees.
   - The APC prompt notes that its copy of Rule 2 said only that several threads share the checkout.
   - Verification: `STRAT-003-prompt.md` rule 2 does indeed state: "Several threads share this checkout. Immediately before editing docs/decisions/decision-log.md, docs/tasks/status.md or pyproject.toml, re-read the file from disk and touch only your own lines...". It makes no mention of worktrees. The worktree instructions originated from `AGENTS.md` and Addendum v2. The implementer conflated Rule 2 with Addendum v2.
3. **Model label:**
   - The implementer reported `Gemini 3.8 Flash (High)`. As reviewer, this cannot be independently verified from git objects alone; Luke should verify against UI session logs.

---

## 5. Mutation Table

Summary of all 19 evaluated mutations:

| # | Mutation Description | Target Location | Result | Killer Test / Analysis |
| :-: | :--- | :--- | :-: | :--- |
| 1 | Results ordered ascending | `ann_retrieval.py:340` | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 2 | `k_eff = k` instead of `min(k, n)` | `ann_retrieval.py:322` | **KILLED** | `test_search_receives_k_eff_min_k_n` |
| 3 | Remove `-1` padding filter | `ann_retrieval.py:331` | **KILLED** | `test_minus_one_padding_dropped_explicitly` |
| 4 | Rows not normalised in `setup` | `ann_retrieval.py:228` | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 5 | `on_inserted` stores un-normalised vector | `ann_retrieval.py:300` | **KILLED** | `test_setup_and_insert_with_unnormalised_vectors` |
| 6 | `on_inserted` re-embeds concept | `ann_retrieval.py:377` | **KILLED** | `test_cached_embedding_reuse_single_embedding_per_insert` |
| 7 | `shortlist` skips embed on empty index | `ann_retrieval.py:272` | **KILLED** | `test_empty_initial_graph_single_embedding` |
| 8 | Remove `new_name` exclusion | `ann_retrieval.py:334` | **KILLED** | `test_new_name_excluded_when_already_in_index` |
| 9 | `max_candidates` returns `k` | `ann_retrieval.py:200` | **KILLED** | `test_max_candidates_and_matrix_sum` |
| 10 | Swap `METRIC_INNER_PRODUCT` for `METRIC_L2` | `ann_retrieval.py:233,296` | **KILLED** | `test_topk_descending_order_and_no_threshold` |
| 11 | Failed `setup` leaves `_setup_called = True` | `ann_retrieval.py:191` | **KILLED** | `test_failed_second_setup_leaves_strategy_not_set_up[zero_row]` |
| 12 | Compute overlap in `shortlist()` | `ann_retrieval.py:269` | **KILLED** | `test_exact_topk_overlap_lifecycle` |
| 13 | Drop `faiss.omp_set_num_threads(1)` | `ann_retrieval.py:232,295` | **KILLED** | `test_faiss_omp_threads_set_to_one` (spy) |
| 14 | Set `efConstruction` after `add` | `ann_retrieval.py:234` | **KILLED** | `test_mutation14_ef_construction_set_before_add` (spy) |
| 15 | Delete cache clearing at `setup()` top | `ann_retrieval.py:188-189` | **SURVIVED** | Publicly observable via `setup -> shortlist -> setup -> on_inserted` (Finding F-4). |
| 16 | Delete `_index = None` at `setup()` top | `ann_retrieval.py:186` | **KILLED** | `test_setup_nonempty_then_empty` |
| 17 | Delete `_names = []` at `setup()` top | `ann_retrieval.py:184-185` | **SURVIVED** | Non-observable on success (overwritten at end); non-observable on failure (`_setup_called` blocks queries). |
| 18 | `diagnostics()` uses `_index.ntotal` | `ann_retrieval.py:412` | **SURVIVED** | Publicly observable when calling `diagnostics()` after `on_inserted()` (Finding F-3). |
| 19 | Shortlist forgets to set `_last_query_vec` | `ann_retrieval.py:310` | **KILLED** | `test_exact_topk_overlap_lifecycle` |

Total mutations evaluated: 19. Killed: 16 (84.2%). Survived: 3 (15.8%).

---

## 6. Prompt Corrections

1. **Right:** Line count and SHA256 checksums in Check A match the commit objects byte-for-byte.
2. **Right:** The 5 test failures mentioned in the implementer report belong entirely to `tests/test_generate_name_pool.py`. In the current working tree, 2 tests in that file remain failing due to active concurrent edits in DATA-006 / FIX-013 / FIX-014.
3. **Right:** Pre-flight bound yields exactly 600 ($k=10$), 300 ($k=5$), and 1200 ($k=20$) via `compute_planned_calls_upper_bound`.
4. **Right:** The recall drop to $\approx 0.84$ at $n=2000, \text{efSearch}=64$ is data-dependent (isotropic Gaussian dispersion) and is not a bug.
5. **Wrong / Correction in prompt:** Check H refers to `compute_planned_calls_upper_bound` in `scripts/run_experiment.py` or `harness.py`. In the repository, `compute_planned_calls_upper_bound` is defined in `scripts/run_experiment.py`, not in `graph_insertion/harness.py`. Furthermore, its return type `PlannedCallsBound` exposes the total bound as attribute `.full_plan_bound`, not `.total_calls`.
6. **Wrong / Correction in prompt:** In Check I, the prompt says "Confirm diagnostics() cost does not enter shortlist_s/update_s by reading insert_node (give line numbers)". In `src/graph_insertion/strategy.py`, `update_s` is measured across lines 354–357, `total_s` is calculated at line 366, and `diagnostics()` is called at line 373.

---

## 7. Found But Not Changed

The following items were observed in the repository during review and were intentionally left unmodified per the read-only constraints:
1. `src/graph_insertion/strategies/ann_retrieval.py`: Defect F-1 (stale cache on failed shortlist) and docstring clarification F-2 (`max_cosine` note) were identified but left untouched.
2. `tests/test_ann_retrieval_strategy.py`: Test additions for F-3 and F-4 were analyzed in scratch scripts but not added to the test suite.
3. Uncommitted working-tree modifications in `docs/decisions/decision-log.md`, `docs/tasks/status.md`, and `tests/test_generate_name_pool.py`: Left untouched; these belong to concurrent thread FIX-014 / DATA-006.
4. Scratch artifacts created during review: `/tmp/check_b_investigation.py`, `/tmp/check_d_ref.py`, `/tmp/check_e_recall.py`, `/tmp/check_f_determinism.py`, `/tmp/run_all_mutations.py`, `/tmp/test_mut6.py`, `/tmp/check_h_harness.py`, `/tmp/check_i_timing.py`, and `/tmp/strat003r-mut/`.

---

## 8. Open Questions

1. **Adoption of Fix F-1:** Will the APC / Luke apply the single-line fix for F-1 (`self._cached_new_name = None; self._cached_new_vec = None` at line 270 of `ann_retrieval.py`) before final strategy acceptance?
2. **Registry Wiring (INFRA-007):** `AnnRetrievalStrategy` is ready for integration into `STRATEGY_REGISTRY` once Phase 2 reviews conclude.
