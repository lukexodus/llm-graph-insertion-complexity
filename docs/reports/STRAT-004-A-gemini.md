# STRAT-004-A — Amendments to Strategy 4 (`bounded_bucket`) After Review (`[D-62]`, Two Test Gaps, Full Mutation Run)

Date: 2026-10-11 · Task: `STRAT-004-A` · Agent: `gemini` (`Gemini 3.8 Flash (High)`) · Base commit: `42890e9` · Decision ID: `[D-62]`

---

## 1. Agent identity and independence statement

- **Agent slug:** `gemini` (`[Confirmed]`)
- **Model label (as displayed by tool):** `Gemini 3.8 Flash` (`Gemini 3.8 Flash (High)`) (`[Confirmed]`)
- **Conversation ID:** `455d24de-0fbf-46a4-bbe1-9c839413cd7e` (`[Confirmed]`)
- **Independence disclosure:**
  - This session is NOT session `b8ab4203-d881-4c7d-8f76-db6a0b797a9c` (the `STRAT-003` family session) (`[Confirmed]`).
  - However, Luke dispatched `STRAT-004-A` directly into conversation `455d24de-0fbf-46a4-bbe1-9c839413cd7e`, which previously ran `STRAT-004-D`, `STRAT-004`, and `STRAT-004-R` (`[Confirmed]`). Following the disclosure precedent in `docs/reports/STRAT-003-B-gemini.md:14` and `docs/reports/STRAT-004-R-gemini.md:17`, this is stated explicitly so Luke and the APC have full provenance.

---

## 2. What was asked / what I did

### What was asked
1. **A-1:** Verify the 5 claims in Section 0 of the prompt against the repository with exact line numbers, and grep the repository for every occurrence of `(3, 6)`, `s_max=6`, `n_bits=8`, and `n_bits=16`.
2. **A-2:** Close the two review test gaps in `tests/test_bounded_bucket_strategy.py` (`Gap A`: `merge_occurred` after `on_inserted()` on an empty index, inside-span without split, inside-span with split, and in a gap, both directly and through `insert_node` with `FakeDecisionStep`; `Gap B`: per-query diagnostic reset on a valid second `setup()` and a failed second `setup()` before any new `shortlist()` call) without modifying or weakening any existing test or assertion. Show that both mutants (`A-01`, `A-02`) survived before the edit and are killed by the new tests.
3. **A-3:** Run all 32 mutants from the `STRAT-004` implementation prompt (`M-01`..`M-32`) plus `A-01` and `A-02` against a copy under `/tmp/strat004a-mut` and record `KILLED` / `SURVIVED` with code locations and first failing tests.
4. **A-4:** Append decision entry `[D-62]` at the end of `docs/decisions/decision-log.md` (without editing `[D-59]` or `docs/tasks/status.md`, and without test counts in `[D-62]`).
5. **Section 6:** Commit the changes (`STRAT-004-A: amend Strategy 4 decision record and tests after review (D-62)`) and generate the patch in `patch/` via `git format-patch -1 -o patch/`.

### What I did
1. Copied `src/graph_insertion/strategies/bounded_bucket.py` and `tests/test_bounded_bucket_strategy.py` to `/tmp/strat004a-before/` before making any edit, recorded `sha256sum` and `wc -l`, verified `git status --short`, `git log --oneline -5`, and `.venv-ann/bin/python -m pytest --co -q`, and confirmed `D-62` was unused in `docs/decisions/decision-log.md` (`[Confirmed]`).
2. Verified all 5 claims in Section 0 (`A-1`) with exact file and line citations (reported in Section 3 below) (`[Confirmed]`).
3. Added `class TestPostReviewAmendments` at the end of `tests/test_bounded_bucket_strategy.py` containing `test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty` (`Gap A`) and `test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup` (`Gap B`). Confirmed `src/graph_insertion/strategies/bounded_bucket.py` required zero edits (`[Confirmed]`).
4. Verified that `A-01` and `A-02` survived against `/tmp/strat004a-before/test_bounded_bucket_strategy.py` and that all **34 / 34** mutants (`M-01`..`M-32`, `A-01`, `A-02`) are **KILLED** by the updated `tests/test_bounded_bucket_strategy.py` (`[Confirmed]`).
5. Re-read `docs/decisions/decision-log.md` and appended `[D-62]` covering items (1)–(7) without test counts (`[Confirmed]`).
6. Ran the post-edit verification suite (`2 passed` on the new tests alone; `84 passed` on `tests/test_bounded_bucket_strategy.py`; `583 passed, 3 skipped` on the full suite) and cleaned up `/tmp` (`[Confirmed]`).

---

## 3. Prompt corrections (`A-1` results)

Every claim in Section 0 and Section 1 of the prompt was checked against the repository:

1. **Section 0 item 1 (`D-59(6)` sensitivity pair `(3, 6)` and `n_bits in {8, 16}` vs code, tests, and design):**
   - **Verified RIGHT** (`[Confirmed]`):
     - `docs/decisions/decision-log.md:462` (`[D-59](6)`) locks the tighter sensitivity pair at `(s_min=3, s_max=6, n_bits=12)` (`360` calls max) and adds hyperplane sensitivity runs at `(s_min=5, s_max=10, n_bits=8)` and `(s_min=5, s_max=10, n_bits=16)` (`600` calls max each).
     - `src/graph_insertion/strategies/bounded_bucket.py:36` (`sensitivity settings (2, 5) and (10, 20)`), `tests/test_bounded_bucket_strategy.py:58,243-245` (`(5, 10, 600, 590)`, `(2, 5, 300, 295)`, `(10, 20, 1200, 1180)`), and `[D-61](3)` (`docs/decisions/decision-log.md:480`) all use `(2, 5)` (`300` sweep / `295` accuracy calls) and `(10, 20)` (`1,200` sweep / `1,180` accuracy calls), with no `n_bits` sensitivity runs.
     - Repository-wide grep for `(3, 6)`, `s_max=6`, `n_bits=8`, and `n_bits=16`:
       ```text
       $ grep -rnE "\(3,\s*6\)|s_max\s*=\s*6|n_bits\s*=\s*8|n_bits\s*=\s*16|n_bits\s+in\s+\{8,\s*16\}" src/ tests/ docs/
       tests/test_bounded_bucket_strategy.py:277:            strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=11)
       tests/test_bounded_bucket_strategy.py:299:        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=42)
       tests/test_bounded_bucket_strategy.py:520:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=2, seed=42)
       tests/test_bounded_bucket_strategy.py:542:        # Inserting the 6th item reaches exactly s_max=6: must NOT split (kills M-15)
       tests/test_bounded_bucket_strategy.py:630:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
       tests/test_bounded_bucket_strategy.py:688:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
       tests/test_bounded_bucket_strategy.py:726:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
       tests/test_bounded_bucket_strategy.py:790:        """Proves merging an undersize bucket of size 2 with a neighbour of size 5 (> s_max=6) bisects into (3, 4) (kills M-20)."""
       tests/test_bounded_bucket_strategy.py:791:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
       tests/test_bounded_bucket_strategy.py:823:        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=8, seed=42)
       tests/test_bounded_bucket_strategy.py:855:        strat = BoundedBucketStrategy(s_min=2, s_max=6, n_bits=2, seed=42)
       docs/decisions/decision-log.md:462:(6) Primary and sensitivity configurations: ... `(s_min=3, s_max=6, n_bits=12)` (360 calls max) ... `(s_min=5, s_max=10, n_bits=8)` and `(s_min=5, s_max=10, n_bits=16)` ...
       docs/reports/STRAT-004-gemini-bounded-bucket.md:299,306-309,333:...
       docs/reports/STRAT-004-R-gemini.md:24,35,243,265,266,283,531,541,549:...
       ```
       - In `src/`: **0** matches.
       - In `tests/`: matches at lines `277, 299, 520, 542, 630, 688, 726, 790-791, 823, 855` of `tests/test_bounded_bucket_strategy.py` are unit-test fixtures for small-dimension split/merge tests; `n_bits=16` and `(3, 6)` as a sensitivity pair do not appear in `src/` or `tests/`.
       - As sensitivity-grid specifications, `(3, 6)` and `n_bits in {8, 16}` appear **only** in `docs/decisions/decision-log.md:462` (`[D-59](6)`) and `docs/reports/STRAT-004-gemini-bounded-bucket.md:299,306-309,333` (plus `STRAT-004-R-gemini.md` where that discrepancy was flagged as `F-A1`).

2. **Section 0 item 2 (`D-59` lacks accuracy bounds, shortlist-capacity caveat, and two limitations):**
   - **Verified RIGHT** (`[Confirmed]`): `docs/decisions/decision-log.md:456-465` (`[D-59](1)`–`(8)`) omits the accuracy-mode bounds (`590` / `295` / `1,180`), the shortlist-capacity caveat (mean segment size $\approx 7$ vs worst-case `s_max = 10`), the single-insert-per-trial un-amortised `update_s` limitation, the fixed-seed hyperplane-draw limitation, and `"seed"` in the `INFRA-007` config keying list.

3. **Section 0 item 3 (`D-59(3)` wording nit on `(gray, name, code)` vs `(gray, name)`):**
   - **Verified RIGHT** (`[Confirmed]`): `docs/decisions/decision-log.md:459` (`[D-59](3)`) says `BucketEntry(gray, name, code, row) is ordered by (gray, name, code)`, whereas `BucketEntry.sort_key()` at `src/graph_insertion/strategies/bounded_bucket.py:93-95` returns `(self.gray, self.name)`.

4. **Section 0 item 4 (Test gap A and Test gap B):**
   - **Verified RIGHT** (`[Confirmed]`):
     - **Test gap A:** `src/graph_insertion/strategies/bounded_bucket.py:344` sets `merge_occurred = (not inside_span) and (n_before >= 1)`. Before our edit, `tests/test_bounded_bucket_strategy.py` asserted `merge_occurred is False` *before* `on_inserted()` (line `676`) and `merge_occurred is True` *after* `on_inserted()` on a gap insertion (line `680`), but never asserted `merge_occurred is False` *after* `on_inserted()` when `inside_bucket_span is True` (e.g., lines `564-576` or `1294-1299`). Mutating line `344` to `merge_occurred = True` (`A-01`) survived against `/tmp/strat004a-before/test_bounded_bucket_strategy.py`.
     - **Test gap B:** `src/graph_insertion/strategies/bounded_bucket.py:392-410` resets `_shortlist_called`, `_last_*`, and `_cached_exact_topk_overlap` in `setup()`. Before our edit, `test_failed_first_and_second_setup_leaves_strategy_not_set_up` (lines `1090-1106`) checked only `strat.diagnostics()["num_segments"] == 0` after a failed second `setup()` and immediately called `strat.shortlist("probe")` after a valid second `setup()`. Removing lines `392-410` (`A-02`) survived against `/tmp/strat004a-before/test_bounded_bucket_strategy.py`.

5. **Section 0 item 5 (Reviewer vs Implementation prompt mutant numbering):**
   - **Verified RIGHT (with nuance on the implementer's report)** (`[Confirmed]`):
     - `docs/reports/STRAT-004-R-gemini.md:290-335` (Section 5) used the `STRAT-004-R` review prompt's `M-01`..`M-32` list, which had a different numbering from the `STRAT-004` implementation prompt's `M-01`..`M-32` and omitted several of the implementation prompt's mutants (`M-01` `s_min < 1`, `M-10` `capacity = n`, `M-13` un-normalised query, `M-16` split midpoint `1`, `M-17` duplicate check removed, `M-21` eager overlap, `M-22` `config()` key dropped, `M-23` binary search `>=` to `>`, `M-24` inside-span `<=` to `<`, `M-29` `float32` projection, `M-30` hyperplane row-normalisation removed).
     - Note that `docs/reports/STRAT-004-gemini-bounded-bucket.md:166-239` (Section 5) did use the implementation prompt's `M-01`..`M-32` numbering; in Section 5 below we independently run all 32 of those mutants plus `A-01` and `A-02` against `/tmp/strat004a-mut`.

6. **Section 1 test count (`581 passed, 3 skipped`) and decision IDs (`D-58`..`D-61`, `D-56` absent):**
   - **Verified RIGHT** (`[Confirmed]`): Before our edit, `.venv-ann/bin/python -m pytest --co -q` collected `584` items (`581` non-skipped + `3` skipped) at commit `42890e9` (`FIX-016`), and `docs/decisions/decision-log.md` contained `[D-57]`, `[D-58]`, `[D-59]`, `[D-60]`, and `[D-61]`, with `[D-56]` absent and `[D-62]` unused.

---

## 4. Verification output

### 4.1 Pre-edit state (`git status --short`, `git log --oneline -5`, `sha256sum`, `wc -l`, `--co -q`)

```text
=== git status --short ===
 M docs/context/repo-tree.txt
?? docs/reports/STRAT-004-R-gemini.md
=== git log --oneline -5 ===
42890e9 (HEAD -> master, origin/master, origin/HEAD, task/FIX-017) FIX-016: make the dry-run planner use each strategy's own candidate bound
7b36f95 DATA-007: thesis-side supervisor for sharded name-pool generation (D-60)
7b52e0f STRAT-004: implement Strategy 4 bounded-bucket retrieval (D-59)
bd1e91f STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)
a532293 feat(scripts): auto-generate repo-tree.txt in apc-bundle and bundle docs
=== sha256sum & wc -l (before) ===
c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af  src/graph_insertion/strategies/bounded_bucket.py
c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951  tests/test_bounded_bucket_strategy.py
c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af  /tmp/strat004a-before/bounded_bucket.py
c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951  /tmp/strat004a-before/test_bounded_bucket_strategy.py
  847 src/graph_insertion/strategies/bounded_bucket.py
 1442 tests/test_bounded_bucket_strategy.py
 2289 total
=== pytest --co -q | tail -5 ===
        <Function test_timing_components_consistency_with_apply_s>
        <Function test_diagnostics_error_recorded>
        <Function test_empty_shortlist_skips_decide_and_llm>

========================= 584 tests collected in 0.67s =========================
```

### 4.2 Step A-2 & A-4(2): New tests alone, pre-edit survival of `A-01`/`A-02`, and `candidate_upper_bound` verification

```text
=== 1. Step A-2: Run ONLY the two new tests (TestPostReviewAmendments) on committed code ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collected 2 items

tests/test_bounded_bucket_strategy.py ..                                 [100%]

============================== 2 passed in 0.68s ===============================

=== 2. Step A-2: Verify A-01 and A-02 SURVIVED on unedited test file (/tmp/strat004a-before) ===
  BEFORE edit: A-01 | SURVIVED | - | merge_occurred = True unconditionally in _insert_entry
  BEFORE edit: A-02 | SURVIVED | - | setup() does not reset _last_* diagnostic fields and _cached_exact_topk_overlap

=== 4. Step A-4(2): Verify call bounds directly from candidate_upper_bound ===
  (s_min= 5, s_max=10): sweep= 600, accuracy= 590 (DSA: 29*10=290 + Meta: 30*10=300)
  (s_min= 2, s_max= 5): sweep= 300, accuracy= 295 (DSA: 29*5=145 + Meta: 30*5=150)
  (s_min=10, s_max=20): sweep=1200, accuracy=1180 (DSA: 29*20=580 + Meta: 30*20=600)
```

### 4.3 Post-edit verification (`tests/test_bounded_bucket_strategy.py` once, full suite `| tail -3`, `sha256sum` & `wc -l`, `git status --short`)

```text
=== 1. Whole tests/test_bounded_bucket_strategy.py once ===
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 84 items

tests/test_bounded_bucket_strategy.py .................................. [ 40%]
..................................................                       [100%]

============================== 84 passed in 2.00s ==============================
=== 2. Full suite | tail -3 ===
.....                                                                    [100%]

================== 583 passed, 3 skipped in 135.82s (0:02:15) ==================
=== 3. sha256sum and wc -l (before and after) ===
c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af  /tmp/strat004a-before/bounded_bucket.py
c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951  /tmp/strat004a-before/test_bounded_bucket_strategy.py
c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af  src/graph_insertion/strategies/bounded_bucket.py
53ed26166682f682b19c3624e97aed900474d480feeb0425c05f01e188844d40  tests/test_bounded_bucket_strategy.py
   847 /tmp/strat004a-before/bounded_bucket.py
  1442 /tmp/strat004a-before/test_bounded_bucket_strategy.py
   847 src/graph_insertion/strategies/bounded_bucket.py
  1689 tests/test_bounded_bucket_strategy.py
  4825 total
=== 4. git status --short ===
 M docs/context/repo-tree.txt
 M docs/decisions/decision-log.md
 M tests/test_bounded_bucket_strategy.py
?? docs/reports/STRAT-004-R-gemini.md
```

---

## 5. Mutation table: `M-01`..`M-32`, `A-01`, `A-02`

Verbatim results from running `.venv-ann/bin/python /tmp/run_strat004a_mutations.py` (`34 / 34 KILLED`) (`[Confirmed]`):

```text
Total: 34/34 KILLED
M-01 | bounded_bucket.py:141      | KILLED   | tests/test_bounded_bucket_strategy.py::TestInitValidation::test_s_min_below_two_rejected[1] | s_min < 2 guard weakened to s_min < 1
M-02 | bounded_bucket.py:143      | KILLED   | tests/test_bounded_bucket_strategy.py::TestInitValidation::test_s_max_below_two_s_min_rejected[2-3] | s_max < 2 * s_min guard weakened to s_max < s_min
M-03 | bounded_bucket.py:136      | KILLED   | tests/test_bounded_bucket_strategy.py::TestInitValidation::test_non_int_or_bool_rejected_for_all_params[True] | bool guard removed on s_min..seed in __init__
M-04 | bounded_bucket.py:197      | KILLED   | tests/test_bounded_bucket_strategy.py::TestMaxCandidatesAndBudgets::test_max_candidates_values_and_negative_clamping | max_candidates returns n_existing
M-05 | bounded_bucket.py:197      | KILLED   | tests/test_bounded_bucket_strategy.py::TestMaxCandidatesAndBudgets::test_max_candidates_values_and_negative_clamping | max_candidates loses max(0, ...)
M-06 | bounded_bucket.py:214-219  | KILLED   | tests/test_bounded_bucket_strategy.py::TestHashingAndGrayOrder::test_gray_rank_all_4096_12bit_codes | _gray_rank replaced by identity return int(code)
M-07 | bounded_bucket.py:232,244  | KILLED   | tests/test_bounded_bucket_strategy.py::TestHashingAndGrayOrder::test_msb_first_packing_and_exact_zero_dot_product | sign threshold >= 0.0 changed to > 0.0 in _hash_vector and _hash_matrix
M-08 | bounded_bucket.py:412,457  | KILLED   | tests/test_bounded_bucket_strategy.py::TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60 | setup() no longer sorts nodes or entries
M-09 | bounded_bucket.py:375-385  | KILLED   | tests/test_bounded_bucket_strategy.py::TestLifecycleAndSetupSemantics::test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row] | setup() fails to reset _setup_called = False and _segments = [] before validation
M-10 | bounded_bucket.py:517      | KILLED   | tests/test_bounded_bucket_strategy.py::TestEmbeddingAccountingAndEdgeCases::test_first_insert_after_setup_does_not_reallocate_matrix[1] | matrix allocated with exactly n rows (capacity = n) in setup()
M-11 | bounded_bucket.py:539-568  | KILLED   | tests/test_bounded_bucket_strategy.py::TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot | cache clear moved below _validate_concept_name in shortlist()
M-12 | bounded_bucket.py:655      | KILLED   | tests/test_bounded_bucket_strategy.py::TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors | shortlist() sorted with +score instead of (-score, name)
M-13 | bounded_bucket.py:607      | KILLED   | tests/test_bounded_bucket_strategy.py::TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors | query vector not normalised in shortlist()
M-14 | bounded_bucket.py:630      | KILLED   | tests/test_bounded_bucket_strategy.py::TestBoundedBucketDefaultConformance::test_repeated_inserts_see_previous_nodes | shortlist() appends the entry to a segment (mutating _segments)
M-15 | bounded_bucket.py:353      | KILLED   | tests/test_bounded_bucket_strategy.py::TestForcedSplitAndDuplicates::test_forced_split_at_s_max_plus_one | split trigger len(seg) > self.s_max changed to >=
M-16 | bounded_bucket.py:354      | KILLED   | tests/test_bounded_bucket_strategy.py::TestPartitionInvariants::test_invariants_across_65_sequential_inserts_from_empty | split midpoint len(seg) // 2 changed to 1
M-17 | bounded_bucket.py:695-698  | KILLED   | tests/test_bounded_bucket_strategy.py::TestLifecycleAndSetupSemantics::test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name | duplicate-node check removed in on_inserted
M-18 | bounded_bucket.py:704-707  | KILLED   | tests/test_bounded_bucket_strategy.py::TestLifecycleAndSetupSemantics::test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name | cache not cleared at the end of on_inserted
M-19 | bounded_bucket.py:288      | KILLED   | tests/test_bounded_bucket_strategy.py::TestMergeAndNeighbourRule::test_neighbour_rule_component_1_hamming_decisive_over_gray_gap | neighbour comparison reversed (left_key <= right_key -> >=)
M-20 | bounded_bucket.py:505-512  | KILLED   | tests/test_bounded_bucket_strategy.py::TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60 | merge in setup() without the bisect when combined > s_max
M-21 | bounded_bucket.py:664      | KILLED   | tests/test_bounded_bucket_strategy.py::TestDiagnostics::test_diagnostics_lifecycle_lazy_overlap_and_min_hamming | exact_topk_overlap computed eagerly in shortlist()
M-22 | bounded_bucket.py:764      | KILLED   | tests/test_bounded_bucket_strategy.py::TestInterfaceAndConfig::test_name_uses_embeddings_and_config_keys | n_bits dropped from config()
M-23 | bounded_bucket.py:304      | KILLED   | tests/test_bounded_bucket_strategy.py::TestShortlistSemanticsAndBoundaries::test_locate_home_exact_segment_boundaries | binary-search comparator in _locate_home >= changed to >
M-24 | bounded_bucket.py:312      | KILLED   | tests/test_bounded_bucket_strategy.py::TestShortlistSemanticsAndBoundaries::test_locate_home_exact_segment_boundaries | inside-span test <= changed to <
M-25 | bounded_bucket.py:277,283  | KILLED   | tests/test_bounded_bucket_strategy.py::TestMergeAndNeighbourRule::test_neighbour_rule_component_1_hamming_decisive_over_gray_gap | neighbour tuple without the Hamming term
M-26 | bounded_bucket.py:279,285  | KILLED   | tests/test_bounded_bucket_strategy.py::TestMergeAndNeighbourRule::test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak | neighbour tuple without the neighbour-size term
M-27 | bounded_bucket.py:459      | KILLED   | tests/test_bounded_bucket_strategy.py::TestEmbeddingAccountingAndEdgeCases::test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch | n < s_min single-segment branch removed in setup()
M-28 | bounded_bucket.py:544-562  | KILLED   | tests/test_bounded_bucket_strategy.py::TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot | per-query diagnostic fields not reset at the top of shortlist()
M-29 | bounded_bucket.py:228-229,240-241 | KILLED   | tests/test_bounded_bucket_strategy.py::TestHashingAndGrayOrder::test_float64_projection_distinguishes_sub_float32_cancellation | projection in float32 instead of float64 in _hash_vector and _hash_matrix
M-30 | bounded_bucket.py:210      | KILLED   | tests/test_bounded_bucket_strategy.py::TestHyperplanes::test_hyperplane_properties_and_regeneration | hyperplane row-normalisation removed in _draw_hyperplanes
M-31 | bounded_bucket.py:233,245  | KILLED   | tests/test_bounded_bucket_strategy.py::TestHashingAndGrayOrder::test_msb_first_packing_and_exact_zero_dot_product | hyperplane 0 packed as the least significant bit
M-32 | bounded_bucket.py:341-343  | KILLED   | tests/test_bounded_bucket_strategy.py::TestPartitionInvariants::test_invariants_across_65_sequential_inserts_from_empty | on_inserted uses a different tie-break than shortlist in the gap case
A-01 | bounded_bucket.py:344      | KILLED   | tests/test_bounded_bucket_strategy.py::TestPostReviewAmendments::test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty | merge_occurred = True unconditionally in _insert_entry
A-02 | bounded_bucket.py:392-410  | KILLED   | tests/test_bounded_bucket_strategy.py::TestPostReviewAmendments::test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup | setup() does not reset _last_* diagnostic fields and _cached_exact_topk_overlap
```

- **Note on `M-30` (hyperplane row-normalisation removed in `_draw_hyperplanes`, `bounded_bucket.py:210`):** Killed by the direct structural check `assert np.allclose(row_norms, 1.0)` in `TestHyperplanes::test_hyperplane_properties_and_regeneration`. For all input-output hashing and shortlist behaviour, `M-30` is mathematically equivalent because for any hyperplane row $h_r$ with $\|h_r\|_2 > 0$, $(v \cdot (h_r / \|h_r\|_2)) \ge 0.0 \iff (v \cdot h_r) \ge 0.0$.
- **Note on `M-09` (`bounded_bucket.py:375-385`):** `BoundedBucketStrategy.setup()` already resets `self._setup_called = False`, `self._embedder = None`, and `self._segments = []` at lines `375–385` before validation (`[D-50](3)`). Removing that pre-validation reset (`M-09`) is killed by `TestLifecycleAndSetupSemantics::test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row]`.

---

## 6. Diffs

### 6.1 `git diff tests/test_bounded_bucket_strategy.py docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 610e9e9..bf43fef 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -480,3 +480,14 @@ Reasoning: provides unattended multi-shard execution with automatic spare-profil
 (3) Consequence for planned budgets over the D-35 sweep matrix (`sweep_sizes = (50, 100, 200, 500, 1000, 2000)`, `sweep_trials_per_size = 10`, 60 total insertions): `BruteForceStrategy` plans 38,500 LLM calls; Strategy 2 (`EmbeddingThresholdStrategy`) remains uncapped at 38,500 calls (no `max_candidates`); Strategy 3 (`AnnRetrievalStrategy`) plans 600 calls at primary $k = 10$ (300 at $k = 5$, 1,200 at $k = 20$); Strategy 4 (`BoundedBucketStrategy`) plans 600 calls at primary $(s_{\min}, s_{\max}) = (5, 10)$ (300 at $(2, 5)$, 1,200 at $(10, 20)$); and `NullStrategy` plans 60 calls at $k = 1$ (300 at $k = 5$). Any earlier dry-run printouts saved for Strategies 3 and 4 (or `NullStrategy`) prior to this fix overstated the planned LLM call upper bound.
 (4) Tests added: `tests/test_dry_run_plan.py` adds offline unit tests covering the D-35 sweep matrix and small-size clamping across all strategies, accuracy-mode candidate bounds and per-corpus clamping, exact parity with `compute_planned_calls_upper_bound` in `scripts/run_experiment.py`, pre-`setup()` probe strategy invariance, `StubNarrowingStrategy(top_k=5)` compatibility, and the uncapped `n_existing` fallback for strategies without `max_candidates`. (Note: the FIX-016 prompt specified decision ID `D-60`, which was already assigned to DATA-007; `D-61` is used per operator instruction.)
 Reasoning: aligns the dry-run execution planner with the live pre-flight guard by delegating candidate upper-bound computation to `candidate_upper_bound(strategy, n_existing)` instead of inspecting a strategy-specific `"top_k"` config key. Affects: `src/graph_insertion/harness.py`, `tests/test_dry_run_plan.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/FIX-016-gemini-dry-run-planner.md`, INFRA-004, INFRA-005, FIX-009, FIX-016, STRAT-003, STRAT-004.
+
+**[D-62]** Strategy 4 (`bounded_bucket`) decision-log corrections, review test-gap closure, and full mutation verification (STRAT-004-A):
+(1) Sensitivity grid and fixed `n_bits` (superseding [D-59](6) without editing [D-59]): the one-at-a-time sensitivity runs for Strategy 4 (`BoundedBucketStrategy`) are `(s_min, s_max) = (2, 5)` and `(10, 20)` with `n_bits = 12, seed = 42`, around the primary configuration `(s_min = 5, s_max = 10, n_bits = 12, seed = 42)` (matching `src/graph_insertion/strategies/bounded_bucket.py:36`, `tests/test_bounded_bucket_strategy.py:243-245`, and [D-61](3)). There are no `n_bits` sensitivity runs: `n_bits = 12` is fixed a priori and justified by code space ($2^{12} = 4096$ exceeds the largest sweep graph size, $2000$), not by recall. The `(3, 6)` bucket-size pair and the `n_bits` `8` and `16` runs stated in [D-59](6) are withdrawn.
+(2) Planned LLM call upper bounds: over the D-35 sweep matrix (`sweep_sizes = (50, 100, 200, 500, 1000, 2000)` with `sweep_trials_per_size = 10`), summing `candidate_upper_bound(strategy, sz) * 10` yields `600` calls at `(5, 10)`, `300` calls at `(2, 5)`, and `1,200` calls at `(10, 20)` (since `candidate_upper_bound(strategy, sz) == min(s_max, sz) == s_max` for every `sz >= 50`). In accuracy mode (29 DSA leave-one-out trials at `n_existing = 28` plus 30 Metacademy leave-one-out trials at `n_existing = 140`), `29 * candidate_upper_bound(strategy, 28) + 30 * candidate_upper_bound(strategy, 140)` yields `590` calls at `(5, 10)` (`29 * 10 + 30 * 10`), `295` calls at `(2, 5)` (`29 * 5 + 30 * 5`), and `1,180` calls at `(10, 20)` (`29 * 20 + 30 * 20`).
+(3) Shortlist-capacity caveat: at the primary setting `s_max = 10`, the worst-case candidate upper bound (`600` sweep / `590` accuracy calls) equals Strategy 3's at `k = 10`, but because segment sizes lie in `[s_min, s_max] = [5, 10]`, the mean segment size is approximately `7`, so actual LLM call counts are lower on average than Strategy 3's and the comparison does not isolate partitioning geometry from shortlist capacity.
+(4) Methodological limitations: first, the sweep protocol performs a single insertion per trial after `setup()`, so `update_s` measures one un-amortised insertion step and the sweep does not test EraRAG's multi-insertion amortised claim (Theorem 4; a separate multi-insertion offline benchmark is a later task requiring Luke's and the adviser's agreement). Second, `seed = 42` is fixed across trials, so variation across random hyperplane draws is not sampled.
+(5) Wording correction to [D-59](3): `BucketEntry` is ordered by `(gray, name)` via `BucketEntry.sort_key()`; `code` is a bijection of `gray` and never breaks ties.
+(6) Keying for INFRA-007: run directories and analysis key on `config()["s_min"]`, `config()["s_max"]`, `config()["n_bits"]`, and `config()["seed"]`.
+(7) Review test-gap closure and mutation verification: `TestPostReviewAmendments` in `tests/test_bounded_bucket_strategy.py` adds `test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty` (verifying directly and through `insert_node` with `FakeDecisionStep` that `merge_occurred` is `False` on an empty index and on inside-span insertions both with and without a split, and `True` on gap insertions) and `test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup` (verifying that both a valid second `setup()` and a failed second `setup()` reset `bucket_id`, `exact_topk_overlap`, `query_code`, `query_gray_rank`, `shortlist_size`, `bucket_size`, `split_occurred`, `merge_occurred`, `min_hamming_to_shortlist`, and all other per-query fields before any new `shortlist()` call). All mutants in `M-01`..`M-32` plus `A-01` and `A-02` are killed (with `M-30`, removing hyperplane row normalisation, killed by the direct unit-row-norm check in `test_hyperplane_properties_and_regeneration` and behaviourally equivalent otherwise because `dots >= 0.0` is invariant to positive row scaling).
+Reasoning: reconciles [D-59] with the implemented code, tests, and a-priori experimental design on sensitivity parameters, planned call budgets, shortlist-capacity and single-insert limitations, and `BucketEntry` ordering, while closing both review test gaps and verifying the full mutation suite under the specification's mutant IDs. Affects: `tests/test_bounded_bucket_strategy.py`, `docs/decisions/decision-log.md`, `docs/reports/STRAT-004-A-gemini.md`, STRAT-004, STRAT-004-R, STRAT-004-A, INFRA-007.
+
diff --git i/tests/test_bounded_bucket_strategy.py w/tests/test_bounded_bucket_strategy.py
index a6249ea..2cb6593 100644
--- i/tests/test_bounded_bucket_strategy.py
+++ w/tests/test_bounded_bucket_strategy.py
@@ -1440,3 +1440,250 @@ class TestSequentialStreamNoCascades:
                 assert combined_after == set(segs_before[home_idx]) | {name}
                 # Reset split counters for the two new child segments
                 inserts_since_split[home_idx : home_idx + 1] = [0, 0]
+
+
+# ===========================================================================
+# 19. Post-Review Amendments (STRAT-004-A: Gap A and Gap B)
+# ===========================================================================
+
+
+class TestPostReviewAmendments:
+    """Closes STRAT-004-R review test gaps A (merge_occurred inside span) and B (second setup diagnostics reset)."""
+
+    def test_merge_occurred_false_inside_span_true_in_gap_and_false_on_empty(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves merge_occurred is False on empty index and inside-span inserts (with/without split) and True in gaps (kills A-01)."""
+        vecs = {
+            "a_0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # gray=0
+            "a_1": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # gray=0
+            "b_0": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
+            "b_1": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
+            "b_2": TestMergeAndNeighbourRule._vec_for_code(0b0010, 4),  # gray=3
+            "in_no_split": TestMergeAndNeighbourRule._vec_for_code(0b0001, 4),  # gray=1 (inside [0, 3])
+            "in_with_split": TestMergeAndNeighbourRule._vec_for_code(0b0011, 4),  # gray=2 (inside [0, 3])
+            "gap_node": TestMergeAndNeighbourRule._vec_for_code(0b1100, 4),  # gray=8 (outside [0, 3])
+        }
+        emb = ControllableEmbedder(vecs, dim=4)
+
+        # 1. Insertion into an EMPTY index (n_before == 0): merge_occurred is False (direct and via insert_node)
+        strat_empty = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat_empty, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        strat_empty.setup(ConceptGraph(), emb)
+        strat_empty.shortlist("a_0")
+        strat_empty.on_inserted("a_0", ())
+        d_empty_direct = strat_empty.diagnostics()
+        assert d_empty_direct["merge_occurred"] is False
+        assert d_empty_direct["split_occurred"] is False
+
+        strat_empty_drv = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat_empty_drv, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        g_empty_drv = ConceptGraph()
+        meter_empty = MeteredEmbedder(emb)
+        strat_empty_drv.setup(g_empty_drv, meter_empty)
+        res_empty = insert_node(
+            strat_empty_drv,
+            g_empty_drv,
+            FakeDecisionStep(make_edge=False),
+            "a_0",
+            metered_embedder=meter_empty,
+        )
+        assert res_empty.metrics.extra["merge_occurred"] is False
+        assert res_empty.metrics.extra["split_occurred"] is False
+
+        # 2. Direct strategy calls: inside-span without split, inside-span with split, and gap insertion
+        strat_direct = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat_direct, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        g_direct = ConceptGraph()
+        for init_name in ["a_0", "a_1", "b_0", "b_1", "b_2"]:
+            g_direct.add_node(init_name)
+        strat_direct.setup(g_direct, emb)
+        assert [len(s) for s in strat_direct._segments] == [5]
+
+        # 2a. Inside span, no split (size 5 -> 6 <= s_max=6)
+        strat_direct.shortlist("in_no_split")
+        assert strat_direct.diagnostics()["inside_bucket_span"] is True
+        strat_direct.on_inserted("in_no_split", ())
+        d_in_no_split = strat_direct.diagnostics()
+        assert d_in_no_split["inside_bucket_span"] is True
+        assert d_in_no_split["split_occurred"] is False
+        assert d_in_no_split["merge_occurred"] is False
+
+        # 2b. Inside span, with split (size 6 -> 7 > s_max=6, splits into [3, 4])
+        strat_direct.shortlist("in_with_split")
+        assert strat_direct.diagnostics()["inside_bucket_span"] is True
+        strat_direct.on_inserted("in_with_split", ())
+        d_in_split = strat_direct.diagnostics()
+        assert d_in_split["inside_bucket_span"] is True
+        assert d_in_split["split_occurred"] is True
+        assert d_in_split["merge_occurred"] is False
+
+        # 2c. Gap insertion (gray=8 > max gray=3): inside_bucket_span is False, merge_occurred is True
+        strat_direct.shortlist("gap_node")
+        assert strat_direct.diagnostics()["inside_bucket_span"] is False
+        strat_direct.on_inserted("gap_node", ())
+        d_gap = strat_direct.diagnostics()
+        assert d_gap["inside_bucket_span"] is False
+        assert d_gap["split_occurred"] is False
+        assert d_gap["merge_occurred"] is True
+
+        # 3. Same sequence through insert_node with FakeDecisionStep
+        strat_drv = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat_drv, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        g_drv = ConceptGraph()
+        for init_name in ["a_0", "a_1", "b_0", "b_1", "b_2"]:
+            g_drv.add_node(init_name)
+        meter = MeteredEmbedder(emb)
+        strat_drv.setup(g_drv, meter)
+
+        res_no_split = insert_node(
+            strat_drv,
+            g_drv,
+            FakeDecisionStep(make_edge=False),
+            "in_no_split",
+            metered_embedder=meter,
+        )
+        assert res_no_split.metrics.extra["inside_bucket_span"] is True
+        assert res_no_split.metrics.extra["split_occurred"] is False
+        assert res_no_split.metrics.extra["merge_occurred"] is False
+
+        res_split = insert_node(
+            strat_drv,
+            g_drv,
+            FakeDecisionStep(make_edge=False),
+            "in_with_split",
+            metered_embedder=meter,
+        )
+        assert res_split.metrics.extra["inside_bucket_span"] is True
+        assert res_split.metrics.extra["split_occurred"] is True
+        assert res_split.metrics.extra["merge_occurred"] is False
+
+        res_gap = insert_node(
+            strat_drv,
+            g_drv,
+            FakeDecisionStep(make_edge=False),
+            "gap_node",
+            metered_embedder=meter,
+        )
+        assert res_gap.metrics.extra["inside_bucket_span"] is False
+        assert res_gap.metrics.extra["split_occurred"] is False
+        assert res_gap.metrics.extra["merge_occurred"] is True
+
+    def test_second_setup_resets_per_query_diagnostics_on_valid_and_failed_setup(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves a second setup() (valid or failed) resets all per-query diagnostics before any new shortlist() (kills A-02)."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        vecs = {
+            f"n_{i:02d}": TestMergeAndNeighbourRule._vec_for_code(i % 16, 4)
+            for i in range(16)
+        }
+        vecs["a"] = TestMergeAndNeighbourRule._vec_for_code(0b1111, 4)
+        emb = ControllableEmbedder(vecs, dim=4)
+
+        g1 = ConceptGraph()
+        for i in range(6):
+            g1.add_node(f"n_{i:02d}")
+        strat.setup(g1, emb)
+
+        # Populate all per-query fields, cached overlap, split_occurred, and merge_occurred
+        strat.shortlist("a")
+        d_populated = strat.diagnostics()
+        assert d_populated["bucket_id"] is not None
+        assert d_populated["exact_topk_overlap"] is not None
+        assert d_populated["query_code"] is not None
+        assert d_populated["query_gray_rank"] is not None
+        assert d_populated["shortlist_size"] == 6
+        assert d_populated["bucket_size"] == 6
+        assert d_populated["min_hamming_to_shortlist"] is not None
+        strat.on_inserted("a", ())
+        assert strat.diagnostics()["split_occurred"] is True
+        assert strat.diagnostics()["merge_occurred"] is True
+
+        # 1. Valid second setup() on a larger 12-node graph g2 BEFORE any new shortlist()
+        g2 = ConceptGraph()
+        for i in range(12):
+            g2.add_node(f"n_{i:02d}")
+        strat.setup(g2, emb)
+
+        d_after_valid_setup = strat.diagnostics()
+        _assert_no_numpy_types(d_after_valid_setup)
+        json.dumps(d_after_valid_setup)
+        assert d_after_valid_setup["bucket_id"] is None
+        assert d_after_valid_setup["bucket_gray_min"] is None
+        assert d_after_valid_setup["bucket_gray_max"] is None
+        assert d_after_valid_setup["exact_topk_overlap"] is None
+        assert d_after_valid_setup["query_code"] is None
+        assert d_after_valid_setup["query_gray_rank"] is None
+        assert d_after_valid_setup["code_existed_in_bucket"] is False
+        assert d_after_valid_setup["inside_bucket_span"] is False
+        assert d_after_valid_setup["bucket_size_at_shortlist"] == 0
+        assert d_after_valid_setup["bucket_size"] == 0
+        assert d_after_valid_setup["shortlist_size"] == 0
+        assert d_after_valid_setup["split_occurred"] is False
+        assert d_after_valid_setup["merge_occurred"] is False
+        assert d_after_valid_setup["min_hamming_to_shortlist"] is None
+        # Partition-level diagnostics must describe the NEW 12-node graph g2
+        assert d_after_valid_setup["num_segments"] == len(strat._segments) >= 2
+        assert d_after_valid_setup["min_segment_size"] >= 3
+        assert d_after_valid_setup["max_segment_size"] <= 6
+        assert np.isclose(
+            d_after_valid_setup["mean_segment_size"],
+            12.0 / d_after_valid_setup["num_segments"],
+        )
+
+        # 2. Re-populate per-query diagnostics on g2, then call a FAILED second setup() (zero-norm row)
+        strat.shortlist("a")
+        assert strat.diagnostics()["bucket_id"] is not None
+        assert strat.diagnostics()["exact_topk_overlap"] is not None
+
+        class _ZeroRowBatchEmbedder:
+            def embed(self, text: str) -> np.ndarray:
+                return np.ones(4, dtype=np.float32)
+
+            def embed_many(self, texts: Sequence[str]) -> np.ndarray:
+                m = np.ones((len(texts), 4), dtype=np.float32)
+                m[0] = 0.0
+                return m
+
+        with pytest.raises(ValueError, match="Zero-norm"):
+            strat.setup(g2, _ZeroRowBatchEmbedder())  # type: ignore[arg-type]
+
+        assert not strat._setup_called
+        assert strat._embedder is None
+        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
+            strat.shortlist("a")
+
+        d_after_failed_setup = strat.diagnostics()
+        _assert_no_numpy_types(d_after_failed_setup)
+        json.dumps(d_after_failed_setup)
+        assert d_after_failed_setup["bucket_id"] is None
+        assert d_after_failed_setup["bucket_gray_min"] is None
+        assert d_after_failed_setup["bucket_gray_max"] is None
+        assert d_after_failed_setup["exact_topk_overlap"] is None
+        assert d_after_failed_setup["query_code"] is None
+        assert d_after_failed_setup["query_gray_rank"] is None
+        assert d_after_failed_setup["code_existed_in_bucket"] is False
+        assert d_after_failed_setup["inside_bucket_span"] is False
+        assert d_after_failed_setup["bucket_size_at_shortlist"] == 0
+        assert d_after_failed_setup["bucket_size"] == 0
+        assert d_after_failed_setup["shortlist_size"] == 0
+        assert d_after_failed_setup["split_occurred"] is False
+        assert d_after_failed_setup["merge_occurred"] is False
+        assert d_after_failed_setup["min_hamming_to_shortlist"] is None
+        assert d_after_failed_setup["num_segments"] == 0
+        assert d_after_failed_setup["min_segment_size"] == 0
+        assert d_after_failed_setup["max_segment_size"] == 0
+        assert d_after_failed_setup["mean_segment_size"] == 0.0
+
```

### 6.2 `diff -u` against `/tmp/strat004a-before/` copies

- `diff -u /tmp/strat004a-before/bounded_bucket.py src/graph_insertion/strategies/bounded_bucket.py` produced empty output (exit code `0`; `bounded_bucket.py` is unchanged) (`[Confirmed]`).
- `diff -u /tmp/strat004a-before/test_bounded_bucket_strategy.py tests/test_bounded_bucket_strategy.py` is identical to the `tests/test_bounded_bucket_strategy.py` hunk in Section 6.1 above (`[Confirmed]`).

---

## 7. Found but not changed

Per Section 1 Rules, the following items outside the allowed edit scope were confirmed and left untouched:

1. **Strategy 2 (`EmbeddingThresholdStrategy.shortlist()`) vector-validation asymmetry (`src/graph_insertion/strategies/embedding_threshold.py:208,216`, `[Confirmed]`):**
   - Unlike `AnnRetrievalStrategy.shortlist()` (`ann_retrieval.py:289,296`) and `BoundedBucketStrategy.shortlist()` (`bounded_bucket.py:573,588`), which require `isinstance(raw_vec, np.ndarray)` and reject `if norm == 0.0 or not np.isfinite(norm):`, `EmbeddingThresholdStrategy.shortlist()` uses `vec_arr = np.asarray(raw_vec)` (silently coercing Python `list`/`tuple` inputs) and checks only `if norm == 0.0:` without `or not np.isfinite(norm):`. Consequently, a finite `float32` vector such as `np.array([1e20, 1e20, 1e20, 1e20], dtype=np.float32)` whose L2 norm overflows `float32` to `+inf` is accepted by Strategy 2 and caches `vec_arr / inf == [0., 0., 0., 0.]`.
2. **Empty-graph lazy `_dim` lock across Strategies 2, 3, and 4 (`embedding_threshold.py:226`, `ann_retrieval.py:309`, `bounded_bucket.py:602`, `[Confirmed]`):**
   - After `setup()` on an empty graph (`n == 0`), a valid `shortlist("x")` call that is not followed by `on_inserted("x", ())` initializes `self._dim` lazily (and `_hyperplanes` / `_index` / `_mat`), locking the expected embedding dimension even though `_n == 0`.
3. **Pre-existing working-tree files left untouched (`[Confirmed]`):**
   - `docs/context/repo-tree.txt` (unstaged modification from an earlier `apc-bundle.sh` run) and `docs/reports/STRAT-004-R-gemini.md` (untracked report from `STRAT-004-R`) were left untouched and excluded from the `STRAT-004-A` commit and patch.

---

## 8. Open questions

1. **[APC-A] Thesis Chapter 3 (§3.2.5 and §3.4) synchronisation with `[D-62]`:** When APC-A updates Chapter 3 alongside Strategy 3's `[D-55](7)` and `[D-58](2)`, should §3.2.5 and §3.4 explicitly state that $n_{\text{bits}} = 12$ is fixed a priori by code-space size ($2^{12} = 4096 > 2000$) with no $n_{\text{bits}}$ sensitivity sweep, and that the bucket-size sensitivity pairs are $(2, 5)$ and $(10, 20)$ around $(5, 10)$?
2. **[Luke / adviser / APC] Multi-insertion offline benchmark for EraRAG Theorem 4 amortisation (`[D-62](4)`):** Because the D-35 sweep protocol performs a single insertion per trial after `setup()`, do Luke and the adviser want a separate offline multi-insertion stream benchmark (pure NumPy + MiniLM embeddings, zero LLM calls) scheduled after `INFRA-007` to measure multi-insert split frequency and amortised `update_s` directly?
