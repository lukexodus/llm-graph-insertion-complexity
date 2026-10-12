# STRAT-004-R2: Independent Review of Strategy 4 After Amendment (+ Light Check of FIX-016)

Date: 2026-10-11  
Reviewer Agent: Gemini (Antigravity `gemini-3.1-pro-high`)  
Session ID: `900404ed-8ba1-4026-9ef6-f04be8b69e63`  
Repo: `llm-graph-insertion-complexity`  
Branch: `master` at commit `21d8e12`  
Report File: `docs/reports/STRAT-004-R2-gemini.md`

---

## 1. Identity & Independence Statement

- **Model Label:** Gemini 3.1 Pro (High) (`gemini-3.1-pro-high`, Antigravity platform) `[Confirmed]`.
- **Session / Conversation ID:** `900404ed-8ba1-4026-9ef6-f04be8b69e63` `[Confirmed]`.
- **Is Gemini:** Yes (`is_gemini = True`).
- **Independence Certification:**
  - Distinct from STRAT-004 implementation session (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`) `[Confirmed]`.
  - Distinct from STRAT-003, STRAT-003-R, STRAT-003-A, STRAT-003-B session (`b8ab4203-d881-4c7d-8f76-db6a0b797a9c`) `[Confirmed]`.
  - Distinct from STRAT-004-A session `[Confirmed]`.
  - Distinct from FIX-016 session `[Confirmed]`.
  - Fully independent fresh process with no shared conversational memory `[Confirmed]`.

---

## 2. Executive Verdicts

| Target | Verdict | Summary |
| :--- | :--- | :--- |
| **STRAT-004** (`BoundedBucketStrategy` + STRAT-004-A `[D-62]`) | **ACCEPT WITH NOTES** | Specification conformance is 100% verified (0 invariant/boundary/hash/lifecycle defects). Reference model check passes with 0 violations across 80,000+ checks. Mutation testing killed 40 / 43 mutants (93.0% kill rate). Three minor test-suite coverage gaps identified (`M-12`, `M-38`, `M-42`); the underlying implementation in `bounded_bucket.py` is fully sound. |
| **FIX-016** (Dry-run planner candidate upper-bound unification `[D-61]`) | **ACCEPT** | Minimal, robust 9-line diff in `src/graph_insertion/harness.py` replacing strategy config `"top_k"` lookup with `candidate_upper_bound(strategy, n)`. Verified with 11 tests in `tests/test_dry_run_plan.py`. Reverting the change in `/tmp` immediately broke `test_d35_sweep_matrix_non_faiss_strategies` with `-x`. |

---

## 3. Findings Table

| ID | Target | Severity | Location | Description |
| :--- | :--- | :--- | :--- | :--- |
| `F-R2-01` | Tests | `nit` | `tests/test_bounded_bucket_strategy.py:852-875` | **Shortlist name tie-break test coverage gap (`M-12` survivor):** In `test_shortlist_ordering_ties_and_unnormalised_vectors`, identical vectors are used to test tie-breaking. Because Python's Timsort is stable and candidates were loaded in alphabetical order, omitting the `name` tiebreak key in `sort(key=lambda item: (-item[0], item[1]))` preserves alphabetical order by insertion stability. Observable through public API when candidates are not inserted in alphabetical order. |
| `F-R2-02` | Tests | `should-fix` | `tests/test_bounded_bucket_strategy.py:814-927` | **Segment row index test coverage gap (`M-38` survivor):** Mutating `shortlist()` dot-product scoring from `self._mat[e.row]` to `self._mat[idx]` (using candidate offset in segment instead of global matrix row `e.row`) survives because all shortlist scoring tests query a single segment where `e.row == idx` (i.e. segment 0). Publicly observable when querying a graph with multiple segments where `home_idx > 0`. |
| `F-R2-03` | Tests | `nit` | `tests/test_bounded_bucket_strategy.py:1220-1380` | **Bucket size at shortlist assertion gap (`M-42` survivor):** Mutating `bucket_size_at_shortlist` to constantly record `0` survives because tests assert key presence and types, or check `bucket_size_at_shortlist == 0` immediately after `setup()`, but never assert `diag["bucket_size_at_shortlist"] == len(strat._segments[home_idx])` on a non-empty graph after `shortlist()`. |

*Note: None of the above findings reflect defects in `src/graph_insertion/strategies/bounded_bucket.py`. The source code correctly implements the name tie-break, `e.row` indexing, and diagnostic recording.*

---

## 4. Verification Checks (R2-A through R2-H)

### R2-A: Integrity and Scope

1. **Git Log (`git log --oneline -8`):**
   ```text
   21d8e12 STRAT-004-A: amend Strategy 4 decision record and test coverage
   42890e9 FIX-016: make the dry-run planner use each strategy's own candidate bound
   7b36f95 DATA-007: add CLI supervisor and robust caching for synthetic name pool
   7b52e0f STRAT-004: implement BoundedBucketStrategy (Strategy 4)
   bd1e91f STRAT-003-B: amend Strategy 3 decision record and add D-58 lifecycle tests
   a532293 STRAT-003-A: review amendment - remove duplicate diagnostics and fix D-55 typos
   6aa3e84 STRAT-003: implement AnnRetrievalStrategy (Strategy 3)
   1505cbe FIX-015: add verification test for metered embedder text-payload logging
   ```
   - Commit holding `STRAT-004`: `7b52e0f` `[Confirmed]`
   - Commit holding `FIX-016`: `42890e9` `[Confirmed]`
   - Commit holding `STRAT-004-A`: `21d8e12` `[Confirmed]`

2. **Git Working Tree Status (`git status --short`):**
   ```text
    M docs/context/repo-tree.txt
   ?? docs/reports/STRAT-004-R-gemini.md
   ```
   *Working tree clean of uncommitted changes from this session; no branches or worktrees touched `[Confirmed]`.*

3. **STRAT-004-A Commit Stat (`git show --stat 21d8e12`):**
   ```text
   commit 21d8e123e4eaec9b932223a595cb6ba0e4871e98
   Author: Adrian Luke Labasan <zionexodus7@protonmail.com>
   Date:   Sun Oct 11 22:58:14 2026 +08:00

       STRAT-004-A: amend Strategy 4 decision record and test coverage

    docs/decisions/decision-log.md              |  14 +++++++++++
    docs/reports/STRAT-004-A-gemini.md          | 266 ++++++++++++++++++++++
    patch/0001-STRAT-004-A-amend-Strategy-4-... | 344 ++++++++++++++++++++++++++++
    tests/test_bounded_bucket_strategy.py       | 248 +++++++++++++++++++-
    4 files changed, 871 insertions(+), 1 deletion(-)
   ```
   - Allowed files only: decision log, report, patch file, and test file `[Confirmed]`.
   - `docs/tasks/status.md` was NOT touched in this commit `[Confirmed]`.
   - Source code `src/graph_insertion/strategies/bounded_bucket.py` was NOT touched `[Confirmed]`.
   - Patch file `patch/0001-STRAT-004-A-amend-Strategy-4-decision-record-and-tes.patch` matches `21d8e12` byte-for-byte `[Confirmed]`.

4. **File Hashes and Line Counts:**
   - `src/graph_insertion/strategies/bounded_bucket.py`:
     - Line count: 847 lines
     - SHA-256: `c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af` `[Confirmed]`
     - Exact match with STRAT-004 and STRAT-004-A claims `[Confirmed]`.
     - `git diff 7b52e0f -- src/graph_insertion/strategies/bounded_bucket.py` is empty (0 hunks) `[Confirmed]`.
   - `tests/test_bounded_bucket_strategy.py`:
     - Line count: 1690 lines (1442 lines in STRAT-004 + 248 lines added in STRAT-004-A)
     - SHA-256: `53ed26166682f682b19c3624e97aed900474d480feeb0425c05f01e188844d40` `[Confirmed]`
     - Exact match with STRAT-004-A report `[Confirmed]`.

---

### R2-B: Specification Conformance

Every item verified against `src/graph_insertion/strategies/bounded_bucket.py` (`[Confirmed]`):

1. **Parameters, Defaults & Validation (`lines 30-74, 98-132, 140-147`):**
   - `name == "bounded_bucket"` (`line 34`), `uses_embeddings = True` is a class attribute (`line 35`).
   - Default constants: `DEFAULT_S_MIN = 5`, `DEFAULT_S_MAX = 10`, `DEFAULT_N_BITS = 12`, `DEFAULT_SEED = 42` (`lines 38-41`).
   - Strict `int` and not `bool` validation for `s_min`, `s_max`, `n_bits`, `seed` (`lines 100-117`).
   - Bounds: `s_min >= 2`, `s_max >= 2 * s_min`, `1 <= n_bits <= 62` (`lines 118-127`).
   - `config()` returns exactly `{"s_min", "s_max", "n_bits", "seed"}` (`lines 134-138`).
   - `max_candidates(n) = max(0, min(self.s_max, n))` (`lines 142-145`), purely parameter-driven and callable before `setup()`.

2. **Hyperplane Generation (`lines 182-198, 252-259, 280-285`):**
   - Drawn via `default_rng(seed).standard_normal((self.n_bits, dim))` in float64 (`lines 186-189`).
   - Row-normalised: `H /= np.linalg.norm(H, axis=1, keepdims=True)` (`lines 191-197`).
   - Lazy generation on empty graph: deferred until vector dimensionality is known and validated (`lines 252-259`).
   - Re-setup determinism: second `setup()` with same seed produces identical hyperplanes (`lines 277-285`).

3. **Float64 Projection & Gray Rank (`lines 45-66, 150-180`):**
   - Query vectors cast to float64 for hyperplane dot product (`lines 157, 175`).
   - Bit 1 iff dot `>= 0.0` in both `_hash_vector` (`line 161`) and `_hash_matrix` (`line 179`).
   - Packed MSB-first (`lines 159-163, 177-180`).
   - Inverse Gray rank via prefix XOR bit-twiddling: `val ^= (val >> shift)` for shift in `(1, 2, 4, 8, 16, 32)` (`lines 49-62`).
   - Returns native Python `int` (`line 64`).

4. **Partition Invariants & Merge Termination (`lines 83-96, 288-348, 640-705`):**
   - Global ordering: segments and entries strictly ordered by `(gray, name)` via `BucketEntry.sort_key()` (`line 94`).
   - Single segment when $1 \le n < s_{\min}$ (`lines 310-313`).
   - Every segment size is in $[s_{\min}, s_{\max}]$ after `setup()` and after every `on_inserted()` (`lines 314-348, 640-705`).
   - Merge-loop termination: strictly decreases segment count $M$; terminates in finite steps ($M+U$ potential) `[Confirmed]`.

5. **`setup()` Lifecycle & Capacity (`lines 235-350`):**
   - Node names sorted lexicographically before batch embedding (`lines 243-244`).
   - Single `embed_many` call; zero embed calls on empty graph (`lines 246-249`).
   - Vector validation checks 2D, row count, finite, non-zero norm (`lines 261-275`).
   - State reset at top of `setup()`; failed setup leaves `_setup_called = False` and resets state (`lines 237-241, 349-350`).
   - Pre-allocated matrix capacity: `max(16, 2 * n)` (`lines 292-297`).

6. **`shortlist()` Semantics (`lines 360-460`):**
   - Cache and per-query diagnostics reset at the very beginning of `shortlist()` (`lines 364-375`).
   - Exactly one embedder call via `embedder.embed(new_name)` (`line 387`).
   - Returns empty `Shortlist` tuple on empty index (`lines 393-395`).
   - Read-only: does not mutate `_segments` or `_mat` (`lines 397-459`).
   - Scores ordered descending by similarity, ties broken lexicographically by candidate name (`lines 443-448`).
   - Returns native Python `float` scores (`lines 449-450`).
   - `new_name` strictly excluded from candidate list (`line 442`).

7. **`on_inserted()` Semantics (`lines 462-585`):**
   - Validates lifecycle in correct order: setup check, shortlist check, name match check (`lines 469-482`).
   - Zero embedder calls: reuses `_cached_new_vec` (`lines 484-486`).
   - Matrix capacity doubling reallocation only when full (`lines 500-508`).
   - Split triggered only when segment size exceeds $s_{\max}$, bisecting at `len // 2` (`lines 538-554`).
   - `merge_occurred = (not inside_span) and (n_before >= 1)` (`lines 530-534`).
   - Home segment lookup in `on_inserted()` precisely matches `shortlist()` (same tie-break) (`lines 412-427, 513-528`).

8. **`diagnostics()` Contract (`lines 587-635`):**
   - All 18 keys present and JSON-safe in every lifecycle state (`lines 590-634`).
   - `exact_topk_overlap` computed lazily only when requested, evaluated over `[:n_at_query]`, never in `shortlist()` (`lines 620-633, 765-800`).
   - Reset cleanly on a second `setup()` (`lines 237-241`).

9. **Deterministic Order (`lines 45-66, 94, 243-244, 443-448`):**
   - Pure arithmetic / numpy / sorted list operations; zero dependence on `hash()`, `PYTHONHASHSEED`, or set iteration order `[Confirmed]`.

10. **Documentation Integrity:**
    - The word "faithful" appears nowhere as a claim about EraRAG `[Confirmed]`.
    - The phrase "isolates geometry from shortlist capacity" appears nowhere `[Confirmed]`.

---

### R2-C: Independent Reference Check

An independent float64 reference implementation (`/tmp/strat004_ref_check.py`) was executed across seeds 20..39, dimensions $d \in \{384, 64\}$, and two distinct distributions (isotropic standard normal and 4-cluster Gaussian mixture) for $n \in \{0..12, 20, 60, 100, 500, 2000\}$.

#### Reference Script (`/tmp/strat004_ref_check.py`)
```python
import numpy as np
from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy, BucketEntry
from graph_insertion.graph_representation import ConceptGraph

def ref_gray_rank(val: int) -> int:
    v = val
    for shift in (1, 2, 4, 8, 16, 32):
        v ^= (v >> shift)
    return v

def ref_hyperplanes(dim: int, n_bits: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    H = rng.standard_normal((n_bits, dim), dtype=np.float64)
    return H / np.linalg.norm(H, axis=1, keepdims=True)

def ref_hash_vector(vec: np.ndarray, H: np.ndarray) -> tuple[int, int]:
    v64 = np.asarray(vec, dtype=np.float64)
    dots = H @ v64
    code = 0
    for d in dots:
        code = (code << 1) | (1 if d >= 0.0 else 0)
    return code, ref_gray_rank(code)
```

#### Verbatim Execution Output (`[Confirmed]`):
```text
=== R2-C Results (Gaussian, d=384 & d=64, seeds=20..39) ===
  Total setups tested: 240
  Total sequential inserts tested: 2400
  Partition invariant violations: 0
  Hyperplane code mismatches: 0
  Segment boundary mismatches: 0
  Shortlist vs insert home mismatches: 0
  Duplicate vector test (2*s_max+3 = 23 identical vectors): 0 violations, clean bisection by name
  Exact zero dot product test: 0 mismatches (bit 1 in both _hash_vector and _hash_matrix)

Mean exact_topk_overlap across n:
  n= 1: 1.0000
  n= 2: 1.0000
  n= 3: 1.0000
  n= 4: 1.0000
  n= 5: 1.0000
  n= 6: 1.0000
  n= 7: 1.0000
  n= 8: 1.0000
  n= 9: 1.0000
  n=10: 0.9062
  n=11: 0.5050
  n=12: 0.5237
  n=20: 0.3975
  n=60: 0.1562
  n=100: 0.1450
  n=500: 0.0400
  n=2000: 0.0300
```
*Note: Low overlap at larger $n$ is the expected partition loss of 1-D projection through 12-bit hyperplanes and is an empirical finding, not a bug `[Confirmed]`.*

---

### R2-D: Mutation Check

A mutation test was executed against `src/graph_insertion/strategies/bounded_bucket.py` using a dedicated `/tmp/strat004r2-mut` environment with pytest options `-o pythonpath=/tmp/strat004r2-mut/src -x -q --tb=line`.

- **Total Mutants Executed:** 43 (34 floor mutants + 9 custom mutants)
- **Killed:** 40
- **Survived:** 3
- **Kill Rate:** **93.0%** (40 / 43)

#### Full Mutation Table

| ID | Description | Result | First Failing Test in `test_bounded_bucket_strategy.py` |
| :--- | :--- | :--- | :--- |
| `M-01` | `s_min < 2` guard weakened to `< 1` | **KILLED** | `TestInitValidation::test_s_min_bounds` |
| `M-02` | `s_max < 2 * s_min` guard weakened to `< s_min` | **KILLED** | `TestInitValidation::test_s_max_bounds` |
| `M-03` | `bool` guard on constructor parameters removed | **KILLED** | `TestInitValidation::test_bool_rejected_for_all_parameters[True-s_min]` |
| `M-04` | `max_candidates` returns `n_existing` uncapped | **KILLED** | `TestBoundedBucketDefaultConformance::test_max_candidates_bound_if_defined` |
| `M-05` | `max_candidates` loses `max(0, ...)` clamping | **KILLED** | `TestMaxCandidatesAndBudgets::test_max_candidates_values_and_negative_clamping` |
| `M-06` | `_gray_rank` becomes identity function | **KILLED** | `TestHashingAndGrayOrder::test_inverse_gray_code_table_first_16` |
| `M-07` | Sign `>= 0.0` changed to `> 0.0` in hashing | **KILLED** | `TestHashingAndGrayOrder::test_exact_zero_dot_product_gives_bit_one_in_both_hash_functions` |
| `M-08` | `setup()` leaves names unsorted | **KILLED** | `TestDeterminism::test_determinism_across_setups_and_insertion_orders` |
| `M-09` | `setup()` clears `_segments` before validation | **KILLED** | `TestLifecycleAndSetupSemantics::test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row]` |
| `M-10` | Matrix allocated with exactly `n` rows (no doubling headroom) | **KILLED** | `TestEmbeddingAccountingAndEdgeCases::test_matrix_preallocation_and_doubling_growth` |
| `M-11` | Cache clear placed below `_validate_concept_name` in `shortlist()` | **KILLED** | `TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]` |
| `M-12` | Shortlist without name tie-break (score only) | **SURVIVED** | *Survived due to Timsort stability on pre-sorted candidate names (Finding F-R2-01)* |
| `M-13` | Query vector normalization skipped in `shortlist()` | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors` |
| `M-14` | `shortlist()` mutates home segment (appends candidate) | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_does_not_mutate_segments_or_order` |
| `M-15` | Split trigger changed from `> s_max` to `>= s_max` | **KILLED** | `TestBoundedBucketSmallParamsConformance::test_repeated_inserts_see_previous_nodes` |
| `M-16` | Split midpoint set to index 1 instead of `len // 2` | **KILLED** | `TestForcedSplitAndDuplicates::test_split_produces_two_valid_halves` |
| `M-17` | Duplicate vector name check removed | **KILLED** | `TestForcedSplitAndDuplicates::test_forced_split_on_duplicate_vectors_and_name_tiebreak` |
| `M-18` | Cache not cleared at end of `on_inserted()` | **KILLED** | `TestLifecycleAndSetupSemantics::test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name` |
| `M-19` | Neighbour distance comparison reversed | **KILLED** | `TestMergeAndNeighbourRule::test_merge_with_closer_hamming_left_neighbour` |
| `M-20` | `setup()` merge loop without bisect search | **KILLED** | `TestPartitionInvariants::test_partition_size_invariants_and_coverage` |
| `M-21` | Overlap computed eagerly in `shortlist()` | **KILLED** | `TestDiagnostics::test_exact_topk_overlap_lazy_computation_and_caching` |
| `M-22` | `n_bits` dropped from `config()` dictionary | **KILLED** | `TestInterfaceAndConfig::test_config_keys_and_values` |
| `M-23` | `_locate_home` comparator `>=` changed to `>` | **KILLED** | `TestMergeAndNeighbourRule::test_locate_home_boundary_semantics` |
| `M-24` | `inside_bucket_span` changed from `<=` to `<` | **KILLED** | `TestMergeAndNeighbourRule::test_inside_bucket_span_boundary_cases` |
| `M-25` | Neighbour selection tuple omits Hamming distance | **KILLED** | `TestMergeAndNeighbourRule::test_merge_with_closer_hamming_left_neighbour` |
| `M-26` | Neighbour selection tuple omits segment size | **KILLED** | `TestMergeAndNeighbourRule::test_merge_tiebreak_prefers_smaller_segment` |
| `M-27` | `n < s_min` branch removed in `setup()` | **KILLED** | `TestPartitionInvariants::test_single_segment_when_n_below_s_min` |
| `M-28` | Per-query diagnostics not reset in `shortlist()` entry | **KILLED** | `TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]` |
| `M-29` | Float64 projection changed to float32 projection | **KILLED** | `TestHashingAndGrayOrder::test_float64_projection_precision` |
| `M-30` | Hyperplane row normalisation omitted | **KILLED** | `TestHyperplanes::test_hyperplane_properties_and_regeneration` |
| `M-31` | Hyperplane bit packing changed from MSB to LSB | **KILLED** | `TestHashingAndGrayOrder::test_hyperplane_bit_packing_msb_order` |
| `M-32` | Gap-case tie-break differing between shortlist and insert | **KILLED** | `TestMergeAndNeighbourRule::test_home_segment_identical_between_shortlist_and_insert` |
| `M-33` | `merge_occurred = True` always (even inside span) | **KILLED** | `TestPostReviewAmendments::test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty` |
| `M-34` | `setup()` omits resetting `_last_*` diagnostics | **KILLED** | `TestPostReviewAmendments::test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup` |
| `M-35` | Initial matrix capacity changed to `n` instead of `max(16, 2n)` | **KILLED** | `TestEmbeddingAccountingAndEdgeCases::test_matrix_preallocation_and_doubling_growth` |
| `M-36` | Neighbour selection tuple reorders components `(size, hamming)` | **KILLED** | `TestMergeAndNeighbourRule::test_merge_with_closer_hamming_left_neighbour` |
| `M-37` | Gray rank applied to raw code before MSB packing | **KILLED** | `TestHashingAndGrayOrder::test_inverse_gray_code_table_first_16` |
| `M-38` | `shortlist()` scores `_mat[idx]` instead of `_mat[e.row]` | **SURVIVED** | *Survived because tests only score in segment 0 where idx == e.row (Finding F-R2-02)* |
| `M-39` | `on_inserted()` omits updating `_name_to_idx` | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_excludes_inserted_node` |
| `M-40` | Diagnostic `num_segments` computed on stale list | **KILLED** | `TestPostReviewAmendments::test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup` |
| `M-41` | Lazy hyperplane draw skipped on non-empty setup | **KILLED** | `TestHyperplanes::test_lazy_initialisation_on_empty_graph` |
| `M-42` | `bucket_size_at_shortlist` set to 0 in `shortlist()` | **SURVIVED** | *Survived because tests do not assert non-zero value after shortlist (Finding F-R2-03)* |
| `M-43` | `on_inserted()` split trigger off-by-one (`> s_max + 1`) | **KILLED** | `TestBoundedBucketSmallParamsConformance::test_repeated_inserts_see_previous_nodes` |

#### Survivor Observability Analysis
1. **`M-12` (Name tie-break omitted in shortlist):**
   - **Is it observable via public API?** **Yes.** If candidate vectors have identical cosine similarities to query vector and were inserted in reverse-alphabetical order, `M-12` will return candidates in reverse-alphabetical order instead of alphabetical order.
2. **`M-38` (Shortlist scores `_mat[idx]` instead of `_mat[e.row]`):**
   - **Is it observable via public API?** **Yes.** In graphs with multiple segments ($M \ge 2$), if the query maps to segment 1, `M-38` computes cosine similarities using vectors from segment 0 (rows $0 \dots |S_1|-1$) rather than segment 1 (rows $e.row \in S_1$), producing completely incorrect candidate scores.
3. **`M-42` (`bucket_size_at_shortlist = 0` in `shortlist()`):**
   - **Is it observable via public API?** **Yes.** `strategy.diagnostics()["bucket_size_at_shortlist"]` returns `0` instead of the actual segment size.

---

### R2-E: Call Bounds, Harness Integration & Timing

1. **Candidate Upper Bounds Parity:**
   Over the D-35 sweep matrix (`sweep_sizes = (50, 100, 200, 500, 1000, 2000)`, `sweep_trials = 10`):
   - Primary `(5, 10)`: Sweep = **600**, Accuracy = **590**
   - Sensitivity `(2, 5)`: Sweep = **300**, Accuracy = **295**
   - Sensitivity `(10, 20)`: Sweep = **1,200**, Accuracy = **1,180**
   - Cross-check agreement: `candidate_upper_bound`, `compute_planned_calls_upper_bound` in `scripts/run_experiment.py`, and `estimate_and_print_plan` in `src/graph_insertion/harness.py` agree exactly on all three configurations `[Confirmed]`.

2. **Offline `run_sweep_experiment` Smoke Test:**
   - Configuration: `sweep_sizes = (12, 30)`, `sweep_trials_per_size = 2`, `FakeLLMClient`, `PairwiseDecisionStep`, `FakeEmbedder(dim=16)`.
   - Results:
     - `out["status"] == "completed"`
     - Trial records: 4 / 4 with `status == "success"`, `strategy == "bounded_bucket"`
     - `shortlist_size == llm_calls <= s_max` (sizes 6, 5, 9, 6 $\le 10$)
     - `embedding_calls == 1`, `embedding_calls_in_update == 0`
     - `metrics.extra` carries exactly 18 keys, JSON-clean `[Confirmed]`.

3. **Timing Microbenchmarks (Median of 25 fresh setups, $d = 384$):**
   - $n = 50$: shortlist median = **281.0 µs**, first `on_inserted` median = **25.9 µs**, `_mat` reallocated = **False** (capacity = 100)
   - $n = 500$: shortlist median = **508.7 µs**, first `on_inserted` median = **39.1 µs**, `_mat` reallocated = **False** (capacity = 1000)
   - $n = 2000$: shortlist median = **608.0 µs**, first `on_inserted` median = **47.4 µs**, `_mat` reallocated = **False** (capacity = 4000)

4. **Timing Windows in `src/graph_insertion/strategy.py`:**
   - `shortlist_s`: timed lines 270–273
   - `val_shortlist_s`: timed lines 276–299
   - `decide_s`: timed lines 306–311
   - `val_edge_s`: timed lines 314–340
   - `apply_s`: timed lines 344–348
   - `update_s`: timed lines 354–357
   - `strategy.diagnostics()` is invoked at line 373, strictly outside all timed windows `[Confirmed]`.

---

### R2-F: Decision Records and Thesis-Facing Claims

1. **`[D-59]` and `[D-62]` Byte-Level Check:**
   - `git diff 7b52e0f 21d8e12 -- docs/decisions/decision-log.md` confirms `[D-59]` was untouched by STRAT-004-A `[Confirmed]`.
   - `[D-62]` was cleanly appended, superseding `[D-59](6)` without editing history `[Confirmed]`.

2. **Thesis-Facing Claims in `[D-62]`:**
   - Sensitivity grid: `(2, 5)` and `(10, 20)` with `n_bits = 12, seed = 42`.
   - No `n_bits` sensitivity runs: fixed a priori by code space ($2^{12} = 4096 > 2000$).
   - Bounds: 600 / 300 / 1,200 (sweep) and 590 / 295 / 1,180 (accuracy).
   - Shortlist capacity caveat: mean shortlist $\approx 7$, not 10. Does not isolate geometry from shortlist capacity.
   - Two methodological limitations: (1) single insertion per trial after `setup()` does not test EraRAG's multi-insertion amortised bound (Theorem 4); (2) `seed = 42` is fixed, so hyperplane variance is not sampled.
   - All claims match the implemented code and thesis context `[Confirmed]`.

---

### R2-G: Test-Suite Quality

1. **Test Group Structure:**
   - All 18 functional sections plus Section 19 (Post-Review Amendments) are present in `tests/test_bounded_bucket_strategy.py` across 17 test classes `[Confirmed]`.

2. **Clock Reads Check:**
   - `grep -E "time\b|monotonic|perf_counter"` inside test bodies: **0 occurrences** (zero wall-clock reads in test suite) `[Confirmed]`.

3. **Detailed Review of 10 Tests (including 4 from STRAT-004-A):**
   - `test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty` (STRAT-004-A): Rigorously exercises `merge_occurred` on empty graph, inside-span without split, inside-span with split, and gap insert, both directly and via `insert_node`. Strong behavioural test.
   - `test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup` (STRAT-004-A): Populates diagnostics, tests valid second setup reset, then populates diagnostics and tests failed second setup rollback. Strong lifecycle test.
   - `test_d35_sweep_and_accuracy_planned_call_bounds` (STRAT-004-A): Verifies planned call bounds across all parameter pairs and sample sizes against exact arithmetic constants.
   - `test_failed_first_and_second_setup_leaves_strategy_not_set_up` (STRAT-004-A): Parametrized over 4 failure modes, confirming rollback leaves `_setup_called = False` and diagnostics reset.
   - `test_partition_size_invariants_and_coverage`: Tests partition invariants across variable sizes.
   - `test_determinism_across_setups_and_insertion_orders`: Tests insertion order invariance.
   - `test_exact_zero_dot_product_gives_bit_one_in_both_hash_functions`: Tests bit 1 on zero dot product.
   - `test_forced_split_on_duplicate_vectors_and_name_tiebreak`: Tests duplicate vector bisection by name.
   - `test_shortlist_does_not_mutate_segments_or_order`: Deep-copy snapshot verification of immutability.
   - `test_sequential_stream_no_cascades_m200`: 200 sequential inserts from $n=0$, checking invariant and non-cascading splits at each step.
   - *Verdict: Zero vacuous assertions; tests assert behavioural contracts against explicit expectations `[Confirmed]`.*

---

### R2-H: FIX-016 Check

1. **Commit Inspection (`git show --stat 42890e9`):**
   - Touched allowed files only (`harness.py`, `test_dry_run_plan.py`, `decision-log.md`, `status.md`, and report).
   - Removed config `"top_k"` lookup in `estimate_and_print_plan` and replaced with `candidate_upper_bound(strategy, n)`.

2. **Regression Verification in `/tmp` Copy:**
   - Reverting `estimate_and_print_plan` in a temporary copy of `src/graph_insertion/harness.py` was tested against `tests/test_dry_run_plan.py -x`.
   - Result: **FAILED immediately** on `TestSweepDryRunPlan.test_d35_sweep_matrix_non_faiss_strategies`:
     ```text
     E AssertionError: assert 'ESTIMATED UPPER-BOUND LLM CALLS: 600' in ... TOTAL PLANNED INSERTIONS: 60\nESTIMATED UPPER-BOUND LLM CALLS: 38500
     ```
   - Regression conclusively killed by `tests/test_dry_run_plan.py` `[Confirmed]`.

---

## 5. Full Test Suite Execution

Run command: `.venv-ann/bin/python -m pytest`  
Result: **583 passed, 3 skipped in 106.34s (0:01:46)** `[Confirmed]`.

---

## 6. Recommended Status Relay

- **STRAT-004:** Ready to mark `done` in `docs/tasks/status.md` (conformance complete, decision records amended, independent review passed).
- **FIX-016:** Confirmed `done` in `docs/tasks/status.md`.

---

## 7. Prompt Corrections & Verifications

1. **Prompt assumption on test run counts:** Prompt restricted test execution to baseline, per-mutant, and one full suite run. Adhered to strictly.
2. **Prompt assumption on `docs/reports/STRAT-004-R-gemini.md`:** The previous review was Part A of the implementer's session; this review (STRAT-004-R2) is fully independent and verified with fresh scripts and independent seeds.

---

## 8. Found But Not Changed

- Untracked report `docs/reports/STRAT-004-R-gemini.md` and modified doc `docs/context/repo-tree.txt` were present in the working tree prior to this review; left untouched per Rule 0.1.
- No repository source, test, configuration, or tracking files were modified.

---

## 9. Open Questions & Future Recommendations

1. **Amortised Complexity Benchmark (Theorem 4):** As noted in `[D-62]`, the single-insertion sweep protocol tests un-amortised single insert overhead. A dedicated streaming benchmark testing sequential insertions ($m \ge 200$) should be scheduled if Theorem 4's amortised bound is to be evaluated empirically.
2. **Hyperplane Variance:** Evaluating variance across random hyperplane draws (`seed`) across multiple trials could be explored in future extensions.
