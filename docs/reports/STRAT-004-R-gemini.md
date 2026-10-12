# STRAT-004-R — Review of Strategy 4 (`bounded_bucket`) and Verification of `STRAT-003-B`

Date: 2026-10-11 · Task: `STRAT-004-R` · Agent: `gemini` (`Gemini 3.8 Flash (High)`) · Base commit: `7b36f95` (`STRAT-004` at `7b52e0f`, `STRAT-003-B` at `bd1e91f`)

---

## 1. Agent identity and independence statement

- **Agent slug:** `gemini` (`[Confirmed]`)
- **Model label (as displayed by tool):** `Gemini 3.8 Flash` (`Gemini 3.8 Flash (High)`) (`[Confirmed]`)
- **Is this a Gemini model?** Yes (`[Confirmed]`). Per the prompt preamble, the APC should review this report directly rather than relaying it as a non-Gemini check.
- **Conversation ID:** `455d24de-0fbf-46a4-bbe1-9c839413cd7e` (`[Confirmed]`)
- **Independence disclosure (Part A vs Part B):**
  - **Part B (`STRAT-003-B`, commit `bd1e91f`, decision `[D-58]`):** **Session-independent** (`[Confirmed]`). This session (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`) is NOT session `b8ab4203-d881-4c7d-8f76-db6a0b797a9c` (which ran `STRAT-003`, `STRAT-003-R`, `STRAT-003-A`, and `STRAT-003-B`).
  - **Part A (`STRAT-004`, commit `7b52e0f`, decision `[D-59]`):** **Same-session review (independence caveat)** (`[Confirmed]`). Luke dispatched `STRAT-004-R` into this conversation (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`), which previously executed `STRAT-004-D` and `STRAT-004`. Following the disclosure precedent in `docs/reports/STRAT-003-B-gemini.md:14` and Rule 0.6, this is stated explicitly here so Luke and the APC can decide whether to accept the mechanical/mutation/reference evidence in Part A directly or re-run Part A in a separate session.

---

## 2. Verdicts

- **Part A (`STRAT-004` — `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket_strategy.py`, `[D-59]`):** **`pass-with-nits`** (`0` `must-fix`, `2` `should-fix`, `2` `nit`).
  - Every normative requirement in `A2` (1–16) is satisfied in `src/graph_insertion/strategies/bounded_bucket.py` (`[Confirmed]`).
  - An independent `float64` reference implementation from the `A2` specification produces zero hash-code mismatches, zero segment-partition mismatches, zero invariant violations, and zero `shortlist()`-vs-`on_inserted()` home-segment discrepancies across 20 seeds (`0..19`) $\times$ 2 synthetic distributions (isotropic Gaussian and 8-centre clustered in $\mathbb{R}^{384}$) across sequential insertions up to $n = 2{,}000$ and batch `setup()` at $n \in \{0..12, 20, 60, 100, 500, 2000\}$ (`[Confirmed]`).
  - Of the 32 specified mutants (`M-01`..`M-32`) plus 11 reviewer-designed mutants (`R-01`..`R-11`), **40/43 are killed** (`31/32` of `M-01`..`M-32` and `9/11` of `R-01`..`R-11`). The single surviving mutant from `M-01`..`M-32` is **`M-28`** (`merge_occurred = True` unconditionally in `_insert_entry`), because `tests/test_bounded_bucket_strategy.py` asserted `merge_occurred is False` before `on_inserted()` and `merge_occurred is True` after `on_inserted()` on a gap insertion, but omitted an assertion that `merge_occurred is False` after `on_inserted()` when `inside_bucket_span is True` (`F-A2`). The other `should-fix` item (`F-A1`) is a documentation/decision-log sync between `[D-59](6)` (`(3, 6)` sensitivity pair, missing accuracy call bounds and methodological caveats) and `bounded_bucket.py:36` / `test_bounded_bucket_strategy.py:244` (`(2, 5)` sensitivity pair).
- **Part B (`STRAT-003-B` — commit `bd1e91f`, `[D-58]`):** **`pass`** (`0` `must-fix`, `0` `should-fix`, `2` `nit`).
  - Commit `bd1e91f` cleanly and minimally fixes `T-1` (`F-B1`) from `STRAT-003-R` in both `AnnRetrievalStrategy.shortlist()` and `EmbeddingThresholdStrategy.shortlist()` (`[Confirmed]`).
  - Both new regression tests fail against `bd1e91f~1` and pass against `bd1e91f`, and all 4 non-equivalent spot-checked mutants (`M9`, `M1`, `M4`, `M5`) are killed when invoked with `-o pythonpath=...` (`[Confirmed]`).

---

## 3. Findings table

| ID | Part | Severity | Location (`file:line`) | Description | Concrete fix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `F-A1` | Part A | `should-fix` | `docs/decisions/decision-log.md:462`, `src/graph_insertion/strategies/bounded_bucket.py:36` | **Sensitivity pair & `[D-59]` completeness sync:** (1) `bounded_bucket.py:36` and `tests/test_bounded_bucket_strategy.py:244` use `(s_min=2, s_max=5)` as the tighter sensitivity pair (`300` sweep / `295` accuracy calls), whereas `[D-59](6)` (`decision-log.md:462`) and `STRAT-004-gemini-bounded-bucket.md` (§7.2) state `(s_min=3, s_max=6)` (`360` sweep / `354` accuracy calls). (2) `[D-59](6)` states only the sweep upper bounds and omits: (a) the accuracy-mode upper bounds (`590` at `(5, 10)`, `295` at `(2, 5)` / `354` at `(3, 6)`, `1,180` at `(10, 20)`), (b) the caveat that while worst-case `max_candidates` (`600`) equals Strategy 3's (`k = 10`), the mean shortlist size is smaller ($\approx 6.5\text{--}7.9$ for `(5, 10)`), and (c) the two methodological limitations (single-insert-per-trial does not directly stress EraRAG's multi-insertion amortised Theorem 4 bound; fixed `seed=42` does not sample variance across hyperplane draws). | Amend `[D-59](6)` in `docs/decisions/decision-log.md` to align the tighter sensitivity pair with `(2, 5)` (or record both `(2, 5)` and `(3, 6)`), add the accuracy-mode upper bounds (`590` / `295` / `1,180`), and append the mean-shortlist-size and single-insert / fixed-seed caveats. |
| `F-A2` | Part A | `should-fix` | `tests/test_bounded_bucket_strategy.py:565`, `tests/test_bounded_bucket_strategy.py:1296` | **Surviving mutant `M-28` (`merge_occurred = True` when `inside_bucket_span is True`):** In `STRAT-004-gemini-bounded-bucket.md`, the implementer tested the mutant `merge_occurred = False` (which was killed at line 680), but did not assert `diag["merge_occurred"] is False` *after* `on_inserted()` for an insertion where `inside_bucket_span is True`. As a result, mutating `merge_occurred = (not inside_span) and (n_before >= 1)` at `bounded_bucket.py:344` to `merge_occurred = True` survives the test suite. | Add `assert diag["merge_occurred"] is False` at `tests/test_bounded_bucket_strategy.py:566` (in `test_forced_split_at_s_max_plus_one`, where `inside_bucket_span` is `True`) and `assert d_ins["merge_occurred"] is False` at line 1297. |
| `F-A3` | Part A | `nit` | `tests/test_bounded_bucket_strategy.py:1091` | **Surviving reviewer mutant `R-03` (`setup()` reset of `_last_*` diagnostics):** `test_failed_first_and_second_setup_leaves_strategy_not_set_up` checks `strat.diagnostics()["num_segments"] == 0` after a second `setup()`, which is computed from `len(self._segments)`, but no test asserts that `_last_bucket_id` and `_cached_exact_topk_overlap` are reset to `None` immediately after a second `setup()` before any new `shortlist()` call. | In `test_failed_first_and_second_setup_leaves_strategy_not_set_up` (after line 1105 `strat.setup(graph, good_emb)`), assert `strat.diagnostics()["bucket_id"] is None` and `strat.diagnostics()["exact_topk_overlap"] is None` before calling `strat.shortlist("probe")`. |
| `F-A4` | Part A | `nit` | `docs/decisions/decision-log.md:458`, `src/graph_insertion/strategies/bounded_bucket.py:93-95` | **`[D-59](3)` tuple wording vs `BucketEntry.sort_key()`:** `[D-59](3)` states `BucketEntry(gray, name, code, row) is ordered by (gray, name, code)`, whereas `BucketEntry.sort_key()` returns `(self.gray, self.name)`. Mathematically equivalent because `gray` is a bijection of `code`, so `code` never breaks ties between equal `gray` values. | Align `[D-59](3)` wording to `ordered by (gray, name)` when touching `[D-59]`. |
| `F-B1` | Part B | `nit` | `src/graph_insertion/strategies/embedding_threshold.py:208,216` | **Cross-strategy vector validation asymmetry (`B7`):** `AnnRetrievalStrategy.shortlist()` (`ann_retrieval.py:289,296`) and `BoundedBucketStrategy.shortlist()` (`bounded_bucket.py:573,588`) enforce `isinstance(raw_vec, np.ndarray)` and `if norm == 0.0 or not np.isfinite(norm):`. `EmbeddingThresholdStrategy.shortlist()` (`embedding_threshold.py:208,216`) uses `vec_arr = np.asarray(raw_vec)` (silently accepting Python `list`/`tuple`) and checks only `if norm == 0.0:` without `or not np.isfinite(norm)`—so a finite `float32` vector such as `np.array([1e20, 1e20, 1e20, 1e20], dtype=np.float32)` whose L2 norm overflows `float32` to `+inf` is accepted and caches a zero vector `[0., 0., 0., 0.]`. | Add `if not isinstance(raw_vec, np.ndarray): raise ValueError(...)` and `if norm == 0.0 or not np.isfinite(norm):` in `EmbeddingThresholdStrategy.shortlist()` during a future cleanup pass. |
| `F-B2` | Part B | `nit` | `src/graph_insertion/strategies/embedding_threshold.py:198-205,226`, `src/graph_insertion/strategies/ann_retrieval.py:275-285,309` | **Diagnostic reset ordering & empty-graph lazy `_dim` lock (`B7`):** (1) Unlike `BoundedBucketStrategy.shortlist()` (`bounded_bucket.py:544-562`), which resets all `_last_*` diagnostic fields at the top of `shortlist()` before `_validate_concept_name`, Strategies 2 and 3 clear `_cached_new_name`/`_cached_new_vec` first but leave `_last_shortlist_size`/`_last_max_cosine`/`_cached_exact_topk_overlap` from a prior query intact if `_validate_concept_name` raises. (2) In all three embedding strategies (`embedding_threshold.py:226`, `ann_retrieval.py:309`, `bounded_bucket.py:602`), a valid `shortlist("x")` on an empty-graph `setup()` (`n == 0`) that is not followed by `on_inserted("x", ())` initializes `self._dim` lazily, locking the expected dimension while `_n == 0`. | Optional minor cleanup if a future task touches Strategies 2/3. |

---

## 4. Part A checks A1 to A7

### A1. Integrity and scope

- **`git log --oneline -6` and `git status --short` (`[Confirmed]`):**
  ```text
  $ git log --oneline -6
  7b36f95 (HEAD -> master) DATA-007: thesis-side supervisor for sharded name-pool generation (D-60)
  7b52e0f (origin/master, origin/HEAD) STRAT-004: implement Strategy 4 bounded-bucket retrieval (D-59)
  bd1e91f STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)
  a532293 feat(scripts): auto-generate repo-tree.txt in apc-bundle and bundle docs
  d9f7797 FIX-015: explicit adapter thinking control, results/datagen fixture repair (D-57)
  6cd360a docs(guide): add sequential name-pool generation runbook

  $ git status --short
   M docs/context/repo-tree.txt
  ```
  - Commit `7b52e0f` holds `STRAT-004` (`[Confirmed]`).
  - `docs/context/repo-tree.txt` has an unstaged modification from another thread's `apc-bundle.sh` run; per Rule 0.2 it is left untouched (`[Confirmed]`).
- **Files in `7b52e0f` (`git show --stat 7b52e0f` and `git diff --name-only bd1e91f 7b52e0f`) (`[Confirmed]`):**
  ```text
  $ git diff --name-only bd1e91f 7b52e0f
  docs/context/repo-tree.txt
  docs/decisions/decision-log.md
  docs/reports/STRAT-004-gemini-bounded-bucket.md
  docs/tasks/status.md
  src/graph_insertion/strategies/bounded_bucket.py
  tests/test_bounded_bucket_strategy.py
  ```
  - Only the 5 allowed `STRAT-004` deliverables (plus Luke's `docs/context/repo-tree.txt` commit snapshot) are in `7b52e0f` (`[Confirmed]`).
  - Neither `tests/stub_prompt_adapter.py` nor `scripts/name_pool_supervisor.py` is inside `7b52e0f`; those two files belong to commit `7b36f95` (`DATA-007`) (`[Confirmed]`).
  - None of the forbidden files (`harness.py`, `llm.py`, `__init__.py`, `strategy.py`, `embedding.py`, `graph_representation.py`, `strategies/null.py`, `strategies/__init__.py`, `strategies/brute_force.py`, `strategies/embedding_threshold.py`, `strategies/ann_retrieval.py`, `scripts/run_experiment.py`, `scripts/generate_name_pool.py`, `tests/test_strategy_interface.py`, `tests/controllable_embedder.py`, `tests/test_controllable_embedder.py`, existing strategy tests, `pyproject.toml`) were modified in `7b52e0f` (`[Confirmed]`).
  - Inspecting `git show 7b52e0f -- docs/decisions/decision-log.md docs/tasks/status.md` confirms that `7b52e0f` appended only `[D-59]` to `docs/decisions/decision-log.md` and updated only the `STRAT-004` row in `docs/tasks/status.md` (`[Confirmed]`).
- **SHA-256 and line-count verification (`[Confirmed]`):**
  ```text
  $ sha256sum src/graph_insertion/strategies/bounded_bucket.py tests/test_bounded_bucket_strategy.py && wc -l src/graph_insertion/strategies/bounded_bucket.py tests/test_bounded_bucket_strategy.py
  c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af  src/graph_insertion/strategies/bounded_bucket.py
  c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951  tests/test_bounded_bucket_strategy.py
     847 src/graph_insertion/strategies/bounded_bucket.py
    1442 tests/test_bounded_bucket_strategy.py
    2289 total
  ```
  - Rebuilding both files from `patch/STRAT-004_code.patch` into `/tmp` produced identical SHA-256 digests (`c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af` and `c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951`) (`[Confirmed]`).
- **Collect-only per-file test count verification (Rule 0.5) (`[Confirmed]`):**
  ```text
  $ .venv-ann/bin/python -m pytest --co -q | tail -n 25
  tests/test_ann_retrieval_strategy.py: 71
  tests/test_bounded_bucket_strategy.py: 82
  tests/test_brute_force_strategy.py: 24
  tests/test_controllable_embedder.py: 18
  tests/test_decision.py: 15
  tests/test_embedding_threshold_strategy.py: 45
  tests/test_generate_name_pool.py: 47
  tests/test_graph_representation.py: 51
  tests/test_harness_embedding.py: 2
  tests/test_harness.py: 16
  tests/test_live_guard.py: 27
  tests/test_llm.py: 12
  tests/test_loader.py: 26
  tests/test_name_pool_supervisor.py: 11
  tests/test_null_strategy.py: 39
  tests/test_pilot.py: 15
  tests/test_schedule.py: 21
  tests/test_scoring.py: 7
  tests/test_strategy_interface.py: 44

  573 tests collected in 0.25s
  ```
  - The 11-test difference between the implementer's reported `559 passed, 3 skipped` (`562` collected) and Luke's `570 passed, 3 skipped` (`573` collected) is `tests/test_name_pool_supervisor.py` (`11` tests) added by `DATA-007` in commit `7b36f95` (`[Confirmed]`).
- **Single baseline run of `tests/test_bounded_bucket_strategy.py` (Rule 0.5(a)) (`[Confirmed]`):**
  ```text
  $ .venv-ann/bin/python -m pytest tests/test_bounded_bucket_strategy.py -q
  ........................................................................ [ 87%]
  ..........                                                               [100%]
  82 passed in 1.44s
  ```

---

### A2. Specification audit of `src/graph_insertion/strategies/bounded_bucket.py`

| Item | Requirement summary | Verified location (`bounded_bucket.py`) | Status |
| :--- | :--- | :--- | :--- |
| **1. Class & attributes** | `BoundedBucketStrategy`, `name = "bounded_bucket"`, `uses_embeddings = True`, defaults `s_min=5, s_max=10, n_bits=12, seed=42`; NumPy + stdlib only; `strategies/__init__.py` untouched. | Lines `63-81`, `98-129` | **PASS** (`[Confirmed]`) |
| **2. `__init__` validation** | Rejects `bool` (`isinstance(val, bool) or not isinstance(val, int)`), non-`int` for all 4 params; `s_min < 2`, `s_max < 2 * s_min`, `n_bits < 1` or `n_bits > 62` raise `ValueError`. Docstring notes `s_max >= 2 * s_min` is a chosen convention for headroom (sufficient, not necessary; `s_max >= 2 * s_min - 1` suffices). | Lines `48-51`, `111-113`, `130-153` | **PASS** (`[Confirmed]`) |
| **3. `max_candidates`** | `max(0, min(self.s_max, n_existing))`, works before `setup()`. | Lines `192-197` | **PASS** (`[Confirmed]`) |
| **4. Hyperplanes** | `rng = np.random.default_rng(self.seed)`, `raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)`, row-normalised (`norms == 0.0 -> 1.0`). Drawn in `setup()` when `n > 0` or lazily on first valid `shortlist()` after empty `setup()` *after* vector validation; docstring notes row normalisation is cosmetic. | Lines `199-210`, `448-449`, `573-605` | **PASS** (`[Confirmed]`) |
| **5. Hashing & Gray order** | `vec` normalised to unit `float32`, projected against `_hyperplanes` in `float64`; bit `r` is `1 if dot >= 0.0 else 0`, packed MSB-first (`bit << (n_bits - 1 - r)`); `_gray_rank` uses prefix-XOR shift-doubling; `BucketEntry(gray, name, code, row)` ordered by `(gray, name)` (`sort_key()`). | Lines `84-95`, `212-248` | **PASS** (`[Confirmed]`) |
| **6. `setup(graph, embedder)`** | Resets `_setup_called = False` and all state at top; `nodes = sorted(graph.nodes())`; `n == 0` sets `_embedder`, `_setup_called = True`, leaves `_dim`/`_hyperplanes` `None`; `n > 0` calls `embedder.embed_many([embed_text(u) for u in nodes])` once, validates 2-D, row count, finite, non-zero norm, `dim >= 1`, normalises to `float32`, hashes in one matrix product; builds partition (`n < s_min` single segment; else group by `gray`, `_bisect_recursive` at `len // 2`, left-to-right merge `< s_min` with `i = max(0, lo_idx)` and `len(segments) > 1` guard); pre-allocates `_mat` with `max(16, 2 * n)`. Failed 1st or 2nd `setup()` leaves strategy not set up. | Lines `368-530` | **PASS** (`[Confirmed]`) |
| **7. Neighbour rule** | `_choose_neighbour` compares `left_key = (hamming(left[-1].code, cur_first_code), cur_first_gray - left[-1].gray, len(left), 0)` vs `right_key = (hamming(cur_last_code, right[0].code), right[0].gray - cur_last_gray, len(right), 1)`. Used identically in `setup()` step 3 and `_locate_home()`. | Lines `262-289`, `320-328`, `493-501` | **PASS** (`[Confirmed]`) |
| **8. `_locate_home`** | Read-only $O(\log M)$ binary search on `seg[-1].sort_key() >= (gray, name)`; returns `(pos, True)` if inside `seg[pos]` span, `(0, False)` if `pos == 0`, `(M - 1, False)` if `pos == M`, else chooses `pos - 1` or `pos` via `_choose_neighbour` with `(home_idx, False)`. | Lines `290-329` | **PASS** (`[Confirmed]`) |
| **9. `shortlist(new_name)`** | First executable statements clear `_cached_new_name`, `_cached_new_vec`, `_cached_new_code`, `_cached_new_gray` and reset all `_last_*` per-query diagnostics ([D-58]); checks `_setup_called`; calls `_validate_concept_name(new_name)`; embeds once via `embed_text(new_name)`; validates 1-D `ndarray`, finite, non-zero finite norm, matching `_dim`; normalises & hashes; caches `(name, vec, code, gray)`; returns empty `Shortlist` if `_n == 0`; locates home segment in $O(\log M)$ without mutating `_segments`, `_mat`, or `_n`; scores `sub_mat @ q`, filters `e.name != new_name`, sorts by `(-score, name)`. | Lines `532-665` | **PASS** (`[Confirmed]`) |
| **10. `on_inserted(new_name, edges)`** | Requires cached quartet matching `new_name` (`RuntimeError` otherwise), rejects already-indexed `new_name` (`ValueError`), consumes & clears cache, makes zero embedder calls, appends `vec` to `_mat[self._n]` (doubling capacity if `_n >= _mat.shape[0]`), inserts `BucketEntry` into home segment (`ins_pos`), bisects at `len // 2` if `len(seg) > self.s_max`, sets `split_occurred`, `merge_occurred = (not inside_span) and (n_before >= 1)`, and `bucket_size` to the post-split half containing `new_name`. | Lines `331-366`, `667-727` | **PASS** (`[Confirmed]`) |
| **11.Partition invariants** | For $n = 0$: `_segments == []`. For $1 \le n < s_{\min}$: 1 segment of size $n$. For $n \ge s_{\min}$: every segment has $s_{\min} \le \text{len}(S_j) \le s_{\max}$, flattened `(gray, name)` keys are strictly increasing across the entire index, and union of segment names equals indexed node set of size `_n`. | Lines `251-260`, `353-361`, `459-516` | **PASS** (`[Confirmed]`) |
| **12. `config()`** | Returns `{"s_min": int, "s_max": int, "n_bits": int, "seed": int}` as plain Python `int`s. | Lines `759-766` | **PASS** (`[Confirmed]`) |
| **13. `diagnostics()`** | All 18 required keys present, cast to plain Python `int`/`float`/`bool`/`None` (`json.dumps`-safe in every lifecycle state); `exact_topk_overlap` computed lazily in `diagnostics()` over `_mat[:_n_at_query]` with `m = min(self.s_max, n_at_query)` (`1.0` when `n_at_query == 0`, `None` before any `shortlist()` or after a failed `shortlist()`); `min_hamming_to_shortlist` is `min(hamming(query_code, c.code))` (`None` when shortlist empty or before `shortlist()`). | Lines `729-757`, `768-847` | **PASS** (`[Confirmed]`) |
| **14. Complexity docstring** | Docstring states $O(n_{\text{bits}} \cdot d)$ hashing (cached in `shortlist()`), $O(\log M)$ binary search, $O(s_{\max})$ segment insert/split, $O(M)$ pointer shift on split, $O(d)$ row write, and does not claim $O(1)$ worst-case split. | Lines `53-60`, `676-684` | **PASS** (`[Confirmed]`) |
| **15. EraRAG attribution** | Module docstring cites Zhang et al. (`arXiv:2506.20963`), §III-B, §III-C (Algorithm 1), §III-E (Algorithm 3), Theorem 4, and explicitly distinguishes adapted principles from this study's design choices (Gray rank, `len // 2` bisection, 4-component proximity tuple). | Lines `12-25` | **PASS** (`[Confirmed]`) |
| **16. Merge termination proof** | Comment at lines `476-484` proves strict decrease of $M + U \le 2n$ ($M = \text{len}(\text{segments})$, $U = \sum_j \max(0, s_{\min} - |S_j|)$) on every merge step and guarantees termination in at most $2n$ steps, with `len(segments) > 1` guard at line `486`. | Lines `476-486` | **PASS** (`[Confirmed]`) |

---

### A3. Independent numerical and invariant verification

An independent `float64` reference implementation (`/tmp/strat004r_ref_check.py`, removed after run) was written from the `A2` specification and compared against `BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=seed)` across 20 seeds (`0..19`) and two synthetic distributions in $\mathbb{R}^{384}$ (isotropic Gaussian and 8-centre clustered with $\sigma = 0.25$) for both:
1. Sequential insertions from $n = 0$ up to $2{,}000$ (checking `query_code`, `query_gray_rank`, `_locate_home`, `shortlist()` candidates vs home segment before `on_inserted()`, and post-insert segment partition), and
2. Batch `setup()` at $n \in \{0..12, 20, 60, 100, 500, 2000\}$ followed by one `shortlist()` + `on_inserted()` step, plus $2 s_{\max} + 3 = 23$ identical vectors.

Verbatim command output (`[Confirmed]`):
```text
=== A3 Results (gaussian) ===
  invariant_violations: 0
  ref_code_mismatches: 0
  ref_seg_mismatches: 0
  shortlist_vs_insert_home_mismatches: 0
  sampled_cases: inside_span=32372, gap=7608, unseen_code=31225
  n    | split_freq | mean_exact_topk_overlap
     0 |  0/20 (0.00) | 1.0000
     1 |  0/20 (0.00) | 1.0000
     2 |  0/20 (0.00) | 1.0000
     3 |  0/20 (0.00) | 1.0000
     4 |  0/20 (0.00) | 1.0000
     5 |  0/20 (0.00) | 1.0000
     6 |  0/20 (0.00) | 1.0000
     7 |  0/20 (0.00) | 1.0000
     8 |  0/20 (0.00) | 1.0000
     9 |  0/20 (0.00) | 1.0000
    10 | 18/20 (0.90) | 0.9500
    11 |  0/20 (0.00) | 0.5150
    12 |  0/20 (0.00) | 0.4950
    20 |  0/20 (0.00) | 0.3350
    60 |  2/20 (0.10) | 0.1100
   100 |  3/20 (0.15) | 0.0900
   500 |  3/20 (0.15) | 0.0150
  2000 |  2/20 (0.10) | 0.0000
=== A3 Results (clustered) ===
  invariant_violations: 0
  ref_code_mismatches: 0
  ref_seg_mismatches: 0
  shortlist_vs_insert_home_mismatches: 0
  sampled_cases: inside_span=32224, gap=7756, unseen_code=30779
  n    | split_freq | mean_exact_topk_overlap
     0 |  0/20 (0.00) | 1.0000
     1 |  0/20 (0.00) | 1.0000
     2 |  0/20 (0.00) | 1.0000
     3 |  0/20 (0.00) | 1.0000
     4 |  0/20 (0.00) | 1.0000
     5 |  0/20 (0.00) | 1.0000
     6 |  0/20 (0.00) | 1.0000
     7 |  0/20 (0.00) | 1.0000
     8 |  0/20 (0.00) | 1.0000
     9 |  0/20 (0.00) | 1.0000
    10 | 18/20 (0.90) | 0.9500
    11 |  0/20 (0.00) | 0.5450
    12 |  0/20 (0.00) | 0.5500
    20 |  5/20 (0.25) | 0.3950
    60 |  5/20 (0.25) | 0.1350
   100 |  1/20 (0.05) | 0.0700
   500 |  4/20 (0.20) | 0.0250
  2000 |  2/20 (0.10) | 0.0200

=== A3.5 Duplicate vectors (2*s_max+3 = 23) ===
  segment sizes after setup(): [5, 6, 6, 6]
  matches reference bisection by name: True
  invariants violations: 0
```

---

### A4. Test quality and mutation check

- **Test suite inspection (`tests/test_bounded_bucket_strategy.py`) (`[Confirmed]`):**
  - 82 test cases across 14 test classes, using only `FakeEmbedder`, `ControllableEmbedder`, `FakeDecisionStep`, and `FakeLLMClient` (zero live API calls, zero model downloads, zero real corpus files).
  - Covers `STRATEGY_CONFORMANCE_CASES` at both default `(5, 10)` and small `(2, 5)` parameters so split and merge paths execute under the shared conformance suite (`[Confirmed]`).
- **Mutation testing methodology (`[Confirmed]`):**
  - Because `pyproject.toml` sets `pythonpath = ["src", "tests"]`, setting `PYTHONPATH=/tmp/...` in the environment is shadowed by `src`. Every mutant run in `/tmp/run_strat004r_mutations.py` passed `-o pythonpath="/tmp/strat004r_mut_<ID> tests"` and `-x -q --tb=line` to ensure the mutated module was imported and execution stopped at the first failure.
  - **Score:** **40 / 43 mutants killed** (`31 / 32` of `M-01`..`M-32` and `9 / 11` of `R-01`..`R-11`).
  - Full 43-row table is in **Section 5** below.
  - **Analysis of the 3 survivors (`M-28`, `R-03`, `R-04`):**
    1. **`M-28` (`merge_occurred = True` even when `inside_bucket_span is True`):** Genuine test-assertion gap (`F-A2`, `should-fix`). The implementer's own mutation table (`STRAT-004-gemini-bounded-bucket.md` §6, `M-16`) mutated `merge_occurred` to `False` (which is killed at line `680`), and checked `merge_occurred is False` *before* `on_inserted()` (line `676`), but never asserted `diag["merge_occurred"] is False` *after* `on_inserted()` when `inside_bucket_span is True`.
    2. **`R-03` (`setup()` omits resetting `_shortlist_called` and `_last_*` diagnostic fields):** Minor test gap (`F-A3`, `nit`). After a second `setup()`, tests either immediately call `shortlist()` (which resets `_last_*` at entry) or check `diagnostics()["num_segments"]` (computed from `len(self._segments)`), without checking `diagnostics()["bucket_id"] is None` or `diagnostics()["exact_topk_overlap"] is None` in the window between the second `setup()` and the next `shortlist()`.
    3. **`R-04` (`on_inserted()` omits `or self._cached_new_code is None or self._cached_new_gray is None`):** **Equivalent mutant** under the public interface. `_cached_new_name`, `_cached_new_vec`, `_cached_new_code`, and `_cached_new_gray` are initialized, populated, and cleared together as an atomic quartet in `__init__()`, `setup()`, `shortlist()`, and `on_inserted()`; `_cached_new_code` / `_cached_new_gray` are never `None` when `_cached_new_name == new_name` and `_cached_new_vec is not None`.

---

### A5. Integration, call-budget and timing check

Verbatim output from `/tmp/strat004r_ref_check.py` and `/tmp/run_a5_rest.py` (`[Confirmed]`):
```text
=== A5.1 Harness Smoke (sizes=(12, 30), trials=2) ===
  run status: completed, record count: 4
  rec[0]: status=success, strategy=bounded_bucket, n_before=12, shortlist_size=6, llm_calls=6, emb_calls=1, emb_in_update=0, extra_keys=18
  rec[1]: status=success, strategy=bounded_bucket, n_before=12, shortlist_size=6, llm_calls=6, emb_calls=1, emb_in_update=0, extra_keys=18
  rec[2]: status=success, strategy=bounded_bucket, n_before=30, shortlist_size=10, llm_calls=10, emb_calls=1, emb_in_update=0, extra_keys=18
  rec[3]: status=success, strategy=bounded_bucket, n_before=30, shortlist_size=7, llm_calls=7, emb_calls=1, emb_in_update=0, extra_keys=18

=== A5.2 Planned Call Upper Bounds (candidate_upper_bound & compute_planned_calls_upper_bound) ===
  (s_min= 5, s_max=10): sweep_bound= 600 (trials=60), accuracy_bound= 590 (trials=59)
  (s_min= 2, s_max= 5): sweep_bound= 300 (trials=60), accuracy_bound= 295 (trials=59)
  (s_min= 3, s_max= 6): sweep_bound= 360 (trials=60), accuracy_bound= 354 (trials=59)
  (s_min=10, s_max=20): sweep_bound=1200 (trials=60), accuracy_bound=1180 (trials=59)

=== A5.3 Timing Sanity & Mean Shortlist Size (median of 15 fresh setups, d=384) ===
  n=  50: median shortlist= 119.0 us, median first on_inserted= 16.8 us, matrix_reallocations=0/15, mean_shortlist_size=6.40
  n= 100: median shortlist= 158.2 us, median first on_inserted= 20.8 us, matrix_reallocations=0/15, mean_shortlist_size=6.93
  n= 200: median shortlist= 156.8 us, median first on_inserted= 16.6 us, matrix_reallocations=0/15, mean_shortlist_size=7.93
  n= 500: median shortlist= 172.6 us, median first on_inserted= 19.7 us, matrix_reallocations=0/15, mean_shortlist_size=6.53
  n=1000: median shortlist= 195.7 us, median first on_inserted= 21.9 us, matrix_reallocations=0/15, mean_shortlist_size=6.80
  n=2000: median shortlist= 214.3 us, median first on_inserted= 25.2 us, matrix_reallocations=0/15, mean_shortlist_size=6.47
```
- Every trial record in `raw.jsonl` has `status == "success"`, `strategy == "bounded_bucket"`, `embedding_calls == 1`, `embedding_calls_in_update == 0`, `llm_calls == shortlist_size <= min(s_max, n_before)`, and all 18 diagnostic keys in `metrics.extra` (`[Confirmed]`).
- Median `shortlist()` and first `on_inserted()` times at $d = 384$ are well under 1 millisecond at $n \in \{50, 500, 2000\}$ (`119.0..214.3 us` and `16.6..25.2 us`), with `0/15` matrix reallocations on the first insert after `setup()` (`[Confirmed]`).

---

### A6. Decision-log and status-file check

- **`docs/decisions/decision-log.md` (`[D-59]`, lines `451-466`) (`[Confirmed]`):**
  - Appended at the end of `docs/decisions/decision-log.md` in `7b52e0f` (`DATA-007` subsequently appended `[D-60]` after `[D-59]` in `7b36f95`).
  - Covers items (1) EraRAG attribution vs study design choices, (2) hyperparameter defaults and `s_max >= 2 * s_min` sufficiency note, (3) hashing/Gray ordering, (4) `setup()` algorithm and `M + U` termination argument, (5) $O(\log M)$ lookup and $O(s_{\max})$ split with $O(M)$ pointer shift, (6) `max_candidates` and sweep call bounds, and (7) the 18-key `diagnostics()` schema and `[D-58]` cache-clear contract (`[Confirmed]`).
  - **Discrepancies flagged in `F-A1` and `F-A4`:**
    1. `[D-59](6)` (`decision-log.md:462`) lists the tighter sensitivity pair as `(s_min=3, s_max=6, n_bits=12)` (`360` sweep calls), whereas `bounded_bucket.py:36` and `test_bounded_bucket_strategy.py:244` use `(2, 5)` (`300` sweep / `295` accuracy calls).
    2. `[D-59](6)` omits the accuracy-mode upper bounds (`590` at `(5, 10)`, `295` at `(2, 5)` / `354` at `(3, 6)`, `1,180` at `(10, 20)`).
    3. `[D-59](6)` omits noting that while the worst-case upper bound (`600` sweep / `590` accuracy at `s_max=10`) matches Strategy 3 (`k=10`), the mean shortlist size is smaller ($\approx 6.4\text{--}7.9$ across $n \in \{50..2000\}$ per `A5.3` above) because segment sizes range over $[s_{\min}, s_{\max}] = [5, 10]$.
    4. `[D-59]` omits the two methodological limitations: (a) each sweep/accuracy trial performs a single insertion after `setup()`, so EraRAG's multi-insertion amortised Theorem 4 bound is not directly stressed by the one-insert-per-trial protocol; and (b) hyperplane generation uses a fixed `seed = 42` across trials, so variance across hyperplane draws is not sampled.
    5. `[D-59](3)` writes `ordered by (gray, name, code)`, whereas `BucketEntry.sort_key()` returns `(self.gray, self.name)` (mathematically equivalent since `gray` is a bijection of `code`).
- **`docs/tasks/status.md` (`[Confirmed]`):**
  - Only the `STRAT-004` row (`status.md:54`) was changed by `7b52e0f`, setting status to `needs-review` with a one-line summary and `docs/reports/STRAT-004-gemini-bounded-bucket.md`.

---

### A7. Check of the implementer's report (`docs/reports/STRAT-004-gemini-bounded-bucket.md`)

- **Command outputs, line counts, and SHA-256 hashes:** Verified against the repo and `A1`/`A3`/`A5` above (`847` lines, `c99bb9cc...`; `1442` lines, `c9610f07...`; `82 passed`). All reported numbers match (`[Confirmed]`).
- **Mutation claim check:** The implementer's report (§6) tested 32 self-chosen mutants (`M-01`..`M-32` in the implementer's numbering) and killed `32/32` of those, because its `M-16` mutated `merge_occurred` to `False` (`Never set merge_occurred = True on gap insertion`). The review prompt's `M-28` tests the opposite direction (`merge_occurred = True` when `inside_bucket_span is True`), which survived (`F-A2`).
- **Prompt corrections in §8 of the implementer's report (`[Confirmed]`):**
  - The implementer made 5 claims in §8 ("Prompt corrections & verification"). Each is verified below:
    1. *Repo state & base commit (`a532293` vs `bd1e91f`):* **Accurate** (`[Confirmed]`). `bd1e91f` (`STRAT-003-B`, `[D-58]`) was already committed on top of `a532293` when `STRAT-004` ran, and the prompt explicitly said "`a532293` (or later)" and noted `[D-58]` "may or may not be in the log yet".
    2. *Existing strategies' `[D-58]` cache-clear pattern:* **Accurate** (`[Confirmed]`). Both `embedding_threshold.py` and `ann_retrieval.py` already cleared `_cached_new_name` and `_cached_new_vec` at the top of `shortlist()`.
    3. *`[D-35]` and `[D-41]` alignment:* **Accurate** (`[Confirmed]`), except that the implementer tested `(2, 5)` in `test_bounded_bucket_strategy.py:244` and `bounded_bucket.py:36` while writing `(3, 6)` in `[D-59](6)` and §7.2 (`F-A1`).
    4. *Sufficiency vs necessity of `s_max >= 2 * s_min`:* **Accurate** (`[Confirmed]`). Both the prompt and the code correctly note that `s_max >= 2 * s_min - 1` is necessary and sufficient for `len // 2` bisection of `s_max + 1` to yield halves $\ge s_{\min}$, while `s_max >= 2 * s_min` is enforced as a chosen headroom convention.
    5. * Untracked files (`scripts/name_pool_supervisor.py`, `tests/stub_prompt_adapter.py`):* **Accurate** (`[Confirmed]`). Those belonged to a concurrent `DATA-007` thread (subsequently committed in `7b36f95`).

---

## 5. Mutation table: `M-01`..`M-32` and `R-01`..`R-11`

Verbatim results from `.venv-ann/bin/python /tmp/run_strat004r_mutations.py` (`40/43` killed: `31/32` of `M-01`..`M-32` and `9/11` of `R-01`..`R-11`) (`[Confirmed]`):

| ID | Mutant description | Result | First failing test in `tests/test_bounded_bucket_strategy.py` |
| :--- | :--- | :--- | :--- |
| `M-01` | `max_candidates` returns `s_max` (ignores `n_existing`) | **KILLED** | `TestMaxCandidatesAndBudgets::test_max_candidates_values_and_negative_clamping` |
| `M-02` | `max_candidates` returns `min(s_max - 1, n_existing)` | **KILLED** | `TestBoundedBucketSmallParamsConformance::test_repeated_inserts_see_previous_nodes` |
| `M-03` | `shortlist()` cache clear removed | **KILLED** | `TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]` |
| `M-04` | `shortlist()` cache clear moved below `_validate_concept_name` | **KILLED** | `TestLifecycleAndSetupSemantics::test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]` |
| `M-05` | `on_inserted()` re-embeds instead of using `_cached_new_vec` | **KILLED** | `TestBoundedBucketDefaultConformance::test_cached_embedding_reuse_single_embedding_per_insert` |
| `M-06` | `on_inserted()` does not clear cache after use | **KILLED** | `TestLifecycleAndSetupSemantics::test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name` |
| `M-07` | `setup()` does not reset `_setup_called = False` at top | **KILLED** | `TestLifecycleAndSetupSemantics::test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row]` |
| `M-08` | Hyperplane RNG ignores `self.seed` (`default_rng()`) | **KILLED** | `TestDeterminism::test_node_addition_order_invariance` |
| `M-09` | Sign rule uses `> 0` instead of `>= 0` | **KILLED** | `TestHashingAndGrayOrder::test_msb_first_packing_and_exact_zero_dot_product` |
| `M-10` | Uses raw integer code instead of Gray rank | **KILLED** | `TestHashingAndGrayOrder::test_gray_rank_all_4096_12bit_codes` |
| `M-11` | Uses forward Gray map `code ^ (code >> 1)` instead of inverse prefix-XOR | **KILLED** | `TestHashingAndGrayOrder::test_gray_rank_all_4096_12bit_codes` |
| `M-12` | Drops `name` tiebreak in `sort_key` (sorts by `gray` only) | **KILLED** | `TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60` |
| `M-13` | `setup()` skips `n < s_min` single-segment short-circuit | **KILLED** | `TestEmbeddingAccountingAndEdgeCases::test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch` |
| `M-14` | `setup()` skips step 2 (oversize raw bucket bisection) | **KILLED** | `TestForcedSplitAndDuplicates::test_duplicate_vectors_in_setup_and_insert_split_by_name` |
| `M-15` | `setup()` splits oversize raw bucket once instead of recursively | **KILLED** | `TestForcedSplitAndDuplicates::test_duplicate_vectors_in_setup_and_insert_split_by_name` |
| `M-16` | `setup()` skips step 3 (undersize merge) | **KILLED** | `TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60` |
| `M-17` | `setup()` merge does not re-split when `len(combined) > s_max` | **KILLED** | `TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60` |
| `M-18` | `setup()` merge advances `i` past merged segment without re-checking if still `< s_min` | **KILLED** | `TestPartitionInvariants::test_invariants_after_batch_setup_for_n_0_to_60` |
| `M-19` | Swaps primary (Hamming) and secondary (Gray gap) in `_choose_neighbour` | **KILLED** | `TestMergeAndNeighbourRule::test_neighbour_rule_component_1_hamming_decisive_over_gray_gap` |
| `M-20` | Drops tertiary (size) tiebreak in `_choose_neighbour` | **KILLED** | `TestMergeAndNeighbourRule::test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak` |
| `M-21` | `_locate_home` in a gap always picks `pos` instead of calling `_choose_neighbour` | **KILLED** | `TestMergeAndNeighbourRule::test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak` |
| `M-22` | `shortlist()` returns only entries with `e.code == code` instead of full home segment | **KILLED** | `TestBoundedBucketDefaultConformance::test_shortlist_is_subset_and_excludes_new_node` |
| `M-23` | `shortlist()` sorts candidates by ascending score instead of descending | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors` |
| `M-24` | `shortlist()` tie-breaks equal scores in reverse alphabetical order | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors` |
| `M-25` | `on_inserted()` splits at `== s_max` instead of `> s_max` | **KILLED** | `TestForcedSplitAndDuplicates::test_forced_split_at_s_max_plus_one` |
| `M-26` | `on_inserted()` never splits | **KILLED** | `TestPartitionInvariants::test_invariants_across_65_sequential_inserts_from_empty` |
| `M-27` | `on_inserted()` sets `bucket_size = len(left_half)` even when `new_name` went to `right_half` | **KILLED** | `TestForcedSplitAndDuplicates::test_forced_split_at_s_max_plus_one` |
| `M-28` | `merge_occurred` is always `True` even when `inside_bucket_span` is `True` | **SURVIVED** | — (See `F-A2`: tests assert `merge_occurred is False` before `on_inserted()` and `True` after gap `on_inserted()`, but omit `assert diag["merge_occurred"] is False` after `on_inserted()` when `inside_bucket_span is True`.) |
| `M-29` | `exact_topk_overlap` computed over `_n` after `on_inserted` instead of `_n_at_query` | **KILLED** | `TestDiagnostics::test_exact_topk_overlap_matches_independent_float64_reference_through_driver` |
| `M-30` | `__init__` accepts `bool` for `s_min` | **KILLED** | `TestInitValidation::test_non_int_or_bool_rejected_for_all_params[True]` |
| `M-31` | `__init__` accepts `s_max < 2 * s_min` | **KILLED** | `TestInitValidation::test_s_max_below_two_s_min_rejected[2-3]` |
| `M-32` | `shortlist()` mutates `_segments` (violating shortlist purity) | **KILLED** | `TestBoundedBucketDefaultConformance::test_repeated_inserts_see_previous_nodes` |
| `R-01` | Quaternary left-first tiebreak flipped to right-first in `_choose_neighbour` | **KILLED** | `TestMergeAndNeighbourRule::test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak` |
| `R-02` | `_hash_matrix` packs bits LSB-first while `_hash_vector` packs MSB-first | **KILLED** | `TestHashingAndGrayOrder::test_msb_first_packing_and_exact_zero_dot_product` |
| `R-03` | `setup()` fails to reset `_shortlist_called` and `_last_*` diagnostic fields | **SURVIVED** | — (See `F-A3`: no test queries `diagnostics()["bucket_id"]` or `diagnostics()["exact_topk_overlap"]` immediately after a second `setup()` before calling `shortlist()`.) |
| `R-04` | `on_inserted()` skips checking `_cached_new_code is None or _cached_new_gray is None` | **SURVIVED** | — (Equivalent mutant under the public API: `_cached_new_name`, `_cached_new_vec`, `_cached_new_code`, and `_cached_new_gray` are always set and cleared atomically.) |
| `R-05` | `_insert_entry` records `_last_bucket_size` before splitting (`s_max + 1` instead of post-split half) | **KILLED** | `TestForcedSplitAndDuplicates::test_forced_split_at_s_max_plus_one` |
| `R-06` | `_locate_home` inverts side mapping in gap lookup (`pos` when left, `pos - 1` when right) | **KILLED** | `TestMergeAndNeighbourRule::test_neighbour_rule_component_1_hamming_decisive_over_gray_gap` |
| `R-07` | `shortlist()` draws hyperplanes lazily before validating vector finiteness on empty setup | **KILLED** | `TestHyperplanes::test_lazy_hyperplanes_match_non_empty_setup_and_rollback_on_bad_first_query` |
| `R-08` | `on_inserted()` capacity doubling fails to copy existing `_mat[:_n]` rows | **KILLED** | `TestEmbeddingAccountingAndEdgeCases::test_doubling_growth_preserves_all_rows_over_200_inserts` |
| `R-09` | `shortlist()` does not exclude `new_name` from candidates when already in segment | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors` |
| `R-10` | `diagnostics()` computes `min_hamming_to_shortlist` against `0` instead of `_last_query_code` | **KILLED** | `TestDiagnostics::test_diagnostics_lifecycle_lazy_overlap_and_min_hamming` |
| `R-11` | `setup()` fails to L2-normalise rows of `raw_mat` before hashing and storing in `_mat` | **KILLED** | `TestShortlistSemanticsAndBoundaries::test_shortlist_ordering_ties_and_unnormalised_vectors` |

---

## 6. Part B checks B1 to B7 (`STRAT-003-B`)

### B1. Commit and scope check (`bd1e91f`)

- **`git show --stat bd1e91f` (`[Confirmed]`):**
  ```text
  $ git show --stat bd1e91f
  commit bd1e91f48e04e3230f33a8b9444622b2e9fb5d9a
  Author: Luke <lukexodus@users.noreply.github.com>
  Date:   Mon Oct 12 03:07:20 2026 +0800

      STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)

   docs/decisions/decision-log.md                     | 13 ++++
   docs/reports/STRAT-003-B-gemini.md                 | 92 ++++++++++++++++++++++
   src/graph_insertion/strategies/ann_retrieval.py    |  7 +-
   .../strategies/embedding_threshold.py              |  4 +
   tests/test_ann_retrieval_strategy.py               | 71 +++++++++++++++++
   tests/test_embedding_threshold_strategy.py         | 56 +++++++++++++
   6 files changed, 240 insertions(+), 3 deletions(-)
  ```
  - Only the 6 expected files were touched; `docs/tasks/status.md` was not touched (`[Confirmed]`).
- **SHA-256 and line-count verification (`[Confirmed]`):**
  ```text
  $ sha256sum src/graph_insertion/strategies/ann_retrieval.py src/graph_insertion/strategies/embedding_threshold.py tests/test_ann_retrieval_strategy.py tests/test_embedding_threshold_strategy.py && wc -l src/graph_insertion/strategies/ann_retrieval.py src/graph_insertion/strategies/embedding_threshold.py tests/test_ann_retrieval_strategy.py tests/test_embedding_threshold_strategy.py
  50d40522c6ff7cb6fe7e8250b63a085813f08d29ead855c230c34c6cc4ffb758  src/graph_insertion/strategies/ann_retrieval.py
  00a19fb9e74831decdfaf5fdfe71385f6a5b60f8f1b2d38d081a812e332626b3  src/graph_insertion/strategies/embedding_threshold.py
  97456929e0686495ebd9c83e6d2312eb3b33862db265ed28162ac9a479501875  tests/test_ann_retrieval_strategy.py
  910772a5ca75104747411fc31b3ece609f762134bb6fd17822e2a5ea9911f241  tests/test_embedding_threshold_strategy.py
     461 src/graph_insertion/strategies/ann_retrieval.py
     328 src/graph_insertion/strategies/embedding_threshold.py
    1195 tests/test_ann_retrieval_strategy.py
    1108 tests/test_embedding_threshold_strategy.py
    3092 total
  ```
  - Every hash and line count matches `docs/reports/STRAT-003-B-gemini.md` §5.5 (`[Confirmed]`).

---

### B2. Code-change verification

- **`git show bd1e91f -- src/graph_insertion/strategies/ann_retrieval.py src/graph_insertion/strategies/embedding_threshold.py` (`[Confirmed]`):**
  ```diff
  diff --git a/src/graph_insertion/strategies/ann_retrieval.py b/src/graph_insertion/strategies/ann_retrieval.py
  index 4fc1ba9..b2ae83d 100644
  --- a/src/graph_insertion/strategies/ann_retrieval.py
  +++ b/src/graph_insertion/strategies/ann_retrieval.py
  @@ -270,13 +270,14 @@ class AnnRetrievalStrategy:
           1.0 in such cases). This is unreachable through `insert_node` but
           documented for completeness per [D-50](4) and [D-55].
           """
  +        # Clear per-insertion cache as first executable statement (D-58) so any
  +        # failed shortlist() call leaves no cached vector from an earlier shortlist
  +        self._cached_new_name = None
  +        self._cached_new_vec = None
  +
           if not self._setup_called or self._embedder is None:
               raise RuntimeError("setup() must be called before shortlist()")
   
           _validate_concept_name(new_name)
   
  -        # Clear any stale cached vector before embedding so a failed shortlist leaves no cache
  -        self._cached_new_name = None
  -        self._cached_new_vec = None
           # Invalidate cached diagnostic overlap for previous query
           self._cached_exact_topk_overlap = None
  diff --git a/src/graph_insertion/strategies/embedding_threshold.py b/src/graph_insertion/strategies/embedding_threshold.py
  index f626df1..5bf5262 100644
  --- a/src/graph_insertion/strategies/embedding_threshold.py
  +++ b/src/graph_insertion/strategies/embedding_threshold.py
  @@ -193,6 +193,10 @@ class EmbeddingThresholdStrategy:
           Shortlist:
               Candidates ordered by (-score, name) and matching float scores.
           """
  +        # Clear per-insertion cache as first executable statement (D-58) so any
  +        # failed shortlist() call leaves no cached vector from an earlier shortlist
  +        self._cached_new_name = None
  +        self._cached_new_vec = None
  +
           if not self._setup_called or self._embedder is None:
               raise RuntimeError("setup() must be called before shortlist()")
  ```
- In both `AnnRetrievalStrategy.shortlist()` (`ann_retrieval.py:275-276`) and `EmbeddingThresholdStrategy.shortlist()` (`embedding_threshold.py:198-199`), `self._cached_new_name = None` and `self._cached_new_vec = None` are the very first executable statements, before `if not self._setup_called or self._embedder is None:`, `_validate_concept_name(new_name)`, and `self._embedder.embed(...)`. No duplicate cache-clear remains lower in `AnnRetrievalStrategy.shortlist()`, and nothing else in either file changed (`[Confirmed]`).

---

### B3. Pre-fix failure and post-fix pass

Extracting `bd1e91f~1` versions of `ann_retrieval.py` and `embedding_threshold.py` to `/tmp/strat003b_prefix` and running ONLY the two new parameterized regression tests (`-k test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` and `-k test_shortlist_failure_clears_stale_cache`; note that both tests live inside test classes `TestPostReviewAmendments` and `TestValidationAndContracts`, see Section 8) (`[Confirmed]`):

```text
--- PRE-FIX (tests/test_ann_retrieval_strategy.py -k test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector) [rc=1] ---
collected 71 items / 65 deselected / 6 selected

tests/test_ann_retrieval_strategy.py FF....                              [100%]
FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty]
FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt']
================== 2 failed, 4 passed, 65 deselected in 0.09s ==================

--- POST-FIX (tests/test_ann_retrieval_strategy.py -k test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector) [rc=0] ---
collected 71 items / 65 deselected / 6 selected

tests/test_ann_retrieval_strategy.py ......                              [100%]
======================= 6 passed, 65 deselected in 0.18s =======================

--- PRE-FIX (tests/test_embedding_threshold_strategy.py -k test_shortlist_failure_clears_stale_cache) [rc=1] ---
collected 45 items / 39 deselected / 6 selected

tests/test_embedding_threshold_strategy.py FFFFFF                        [100%]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[empty_name--ValueError-cannot be empty]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt']
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[embedder_raises-failing_node-RuntimeError-Simulated embedder failure]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[zero_norm-failing_node-ValueError-Zero-norm]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[nan_vec-failing_node-ValueError-non-finite]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[dim_mismatch-failing_node-ValueError-Dimension mismatch]
======================= 6 failed, 39 deselected in 0.10s =======================

--- POST-FIX (tests/test_embedding_threshold_strategy.py -k test_shortlist_failure_clears_stale_cache) [rc=0] ---
collected 45 items / 39 deselected / 6 selected

tests/test_embedding_threshold_strategy.py ......                        [100%]
======================= 6 passed, 39 deselected in 0.04s =======================
```
- This confirms the exact asymmetry between Strategy 3 (2 pre-fix failures on `_validate_concept_name`: `empty_name` and `txt_suffix`) and Strategy 2 (all 6 pre-fix failures across validation and embedder errors), and confirms all 12 parameterized cases pass on `bd1e91f` (`[Confirmed]`).

---

### B4. Mutation spot-check (5 mutants with `-o pythonpath=...`)

Verbatim output from `/tmp/run_part_b_checks.py` (`[Confirmed]`):
```text
=== B4: Spot-check 5 mutants (M9, M1, M4, M5, M8) with -o pythonpath ===
  M9  | KILLED   | FAILED tests/test_ann_retrieval_strategy.py::TestAnnRetrievalConformance::test_cached_embedding_reuse_single_embedding_per_insert | on_inserted() re-embeds instead of using _cached_new_vec (previously survived in STRAT-003-R due to PYTHONPATH shadowing)
  M1  | KILLED   | FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty] | Move cache clear below _validate_concept_name in AnnRetrievalStrategy.shortlist()
  M4  | KILLED   | FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty] | Remove cache clear at top of AnnRetrievalStrategy.shortlist()
  M5  | KILLED   | FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[empty_name--ValueError-cannot be empty] | Remove cache clear at top of EmbeddingThresholdStrategy.shortlist()
  M8  | SURVIVED | - | Move cache clear after not-set-up check in EmbeddingThresholdStrategy.shortlist()
```
- **Why `M9` survived in `STRAT-003-R` and is killed here:** `pyproject.toml` sets `pythonpath = ["src", "tests"]`, which pytest prepends ahead of `PYTHONPATH`. Passing `-o pythonpath="/tmp/... tests"` overrides `pyproject.toml` so the mutated `ann_retrieval.py` is actually loaded, and `M9` is immediately killed by `TestAnnRetrievalConformance::test_cached_embedding_reuse_single_embedding_per_insert` (`[Confirmed]`).
- **Why `M8` is an equivalent mutant under the public API:** `_cached_new_name` and `_cached_new_vec` can only become non-`None` inside `shortlist()` *after* `self._setup_called` is `True`, and `setup()` unconditionally resets `_setup_called = False` and `_cached_new_name = _cached_new_vec = None` as its first statements. Therefore, via the public API, whenever `not self._setup_called or self._embedder is None` is true on entry to `shortlist()`, the cache is already `(None, None)` (`[Confirmed]`).

---

### B5. Test-count and `[D-58]` check

- **Test-count delta across `bd1e91f~1` $\to$ `bd1e91f` (`[Confirmed]`):**
  - `tests/test_ann_retrieval_strategy.py`: `66` (`bd1e91f~1`) $\to$ `71` (`bd1e91f`, `+5` net: `1` unparameterized test replaced by `6` parameterized cases).
  - `tests/test_embedding_threshold_strategy.py`: `39` (`bd1e91f~1`) $\to$ `45` (`bd1e91f`, `+6` parameterized cases).
  - Total suite at `bd1e91f`: `466` $\to$ `477` (`+11` tests: `474 passed, 3 skipped`).
- **`[D-58]` in `docs/decisions/decision-log.md` (lines `438-449`) (`[Confirmed]`):**
  - Accurately records the `shortlist()` entry cache-clear invariant across all embedding-based strategies (`EmbeddingThresholdStrategy`, `AnnRetrievalStrategy`, and future strategies) and why `pyproject.toml`'s `pythonpath = ["src", "tests"]` requires `-o pythonpath=...` for out-of-tree mutation testing.

---

### B6. Independence note on `STRAT-003-B`

- As noted in Section 1, session `b8ab4203-d881-4c7d-8f76-db6a0b797a9c` ran `STRAT-003`, `STRAT-003-R`, `STRAT-003-A`, and `STRAT-003-B`. Our independent verification in this session (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`) confirms every claim, hash, pre-fix failure, post-fix pass, and mutation result in `docs/reports/STRAT-003-B-gemini.md` (`[Confirmed]`).

---

### B7. Cross-strategy audit (Strategies 2, 3, and 4)

A line-by-line comparison of `setup()`, `shortlist()`, `on_inserted()`, and `diagnostics()` across `embedding_threshold.py` (Strategy 2), `ann_retrieval.py` (Strategy 3), and `bounded_bucket.py` (Strategy 4) confirmed that all three obey `[D-50](3)` (all-or-nothing `setup()` resetting `_setup_called = False` at entry) and `[D-58]` (clearing `_cached_new_*` at the top of `shortlist()`), and uncovered two minor defensive asymmetries (`F-B1` and `F-B2` in Section 3):
1. **`float32` norm overflow & `ndarray` type check in `EmbeddingThresholdStrategy.shortlist()` (`F-B1`):**
   ```text
   === B7: Cross-strategy edge-case audit (Strategies 2, 3, 4) ===
   Strategy 2 (EmbeddingThreshold): float32 norm=inf vector ACCEPTED; cached_vec=[0. 0. 0. 0.]
   Strategy 3 (AnnRetrieval): float32 norm=inf vector REJECTED (Zero-norm embedding vector for concept 'b')
   Strategy 4 (BoundedBucket): float32 norm=inf vector REJECTED (Zero-norm embedding vector for concept 'b')
   ```
   Because `embedding_threshold.py:216` checks `if norm == 0.0:` without `or not np.isfinite(norm):` (whereas Strategies 3 and 4 check `if norm == 0.0 or not np.isfinite(norm):`), a finite `float32` vector whose L2 norm overflows `float32` to `inf` is accepted by Strategy 2 and normalises to `[0., 0., 0., 0.]` (`[Confirmed]`).
2. **Per-query diagnostic reset on failed `shortlist()` & empty-graph lazy `_dim` lock (`F-B2`):** Strategy 4 resets all `_last_*` diagnostic fields at the very top of `shortlist()` before `_validate_concept_name`, whereas Strategies 2 and 3 reset `_last_*` only after `_validate_concept_name` / embedding validation (`[Confirmed]`).

---

## 7. Recommended status relay

Do not edit `docs/tasks/status.md` or `docs/decisions/decision-log.md` in this review task (Rule 0.1). The APC / Luke can apply:
- **`STRAT-004` (`docs/tasks/status.md`):** Ready to mark `done` (or after applying the two small `should-fix` items `F-A1` in `docs/decisions/decision-log.md` and `F-A2` in `tests/test_bounded_bucket_strategy.py`).
- **`STRAT-003-B` (`docs/tasks/status.md`):** Independently verified (`pass`); `STRAT-003` remains `done`.

---

## 8. Prompt corrections

Per Rule 0.6, every factual claim in the `STRAT-004-R` prompt was checked against the live repository:

1. **Commit holding `STRAT-004` (`A1`):** Prompt stated "the patch header says `7b52e0f`, unverified". **Verified right** (`[Confirmed]`): commit `7b52e0f` (`7b52e0f3e6087da0bf3bf133e3410164a4caaa26`) holds `STRAT-004`, and `HEAD` is `7b36f95` (`DATA-007`, one commit later).
2. **Test count difference (`570 passed, 3 skipped` vs `559 passed, 3 skipped` in Rule 0.5):** Prompt stated "Luke's last full run on the current tree: `570 passed, 3 skipped` (the implementer reported 559 on a tree 11 tests smaller; the difference is other threads' tests)". **Verified right** (`[Confirmed]`): `--co -q` collects `573` items (`570` non-skipped + `3` skipped), and the 11-test difference is `tests/test_name_pool_supervisor.py` (`11` tests) committed in `7b36f95` (`DATA-007`).
3. **Untracked files mentioned in `A1` (`tests/stub_prompt_adapter.py`, `scripts/name_pool_supervisor.py`):** Prompt asked to confirm neither is inside `7b52e0f`. **Verified right** (`[Confirmed]`): neither is in `7b52e0f`; both were committed in `7b36f95` (`DATA-007`).
4. **Tighter sensitivity pair in `A5` and `A6` (`(2, 5)` vs `(3, 6)`):** Prompt `A5` and `A6` state the tighter sensitivity pair as `(2, 5)` (`300` sweep / `295` accuracy calls) and claim `[D-59]` records `600 / 300 / 1,200`. **Partially wrong as a description of `[D-59]`** (`[Confirmed]`): `bounded_bucket.py:36` and `test_bounded_bucket_strategy.py:244` indeed use `(2, 5)` (`300` / `295`), but `[D-59](6)` (`decision-log.md:462`) and `STRAT-004-gemini-bounded-bucket.md` (§7.2) actually wrote `(s_min=3, s_max=6, n_bits=12)` (`360` sweep calls). This discrepancy is logged as `F-A1`.
5. **Pytest node IDs in `B3`:** Prompt `B3` wrote the node IDs as `tests/test_ann_retrieval_strategy.py::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` and `tests/test_embedding_threshold_strategy.py::test_shortlist_failure_clears_stale_cache`. **Minor node-path omission** (`[Confirmed]`): both functions are methods inside test classes (`TestPostReviewAmendments` and `TestValidationAndContracts`), so top-level `::func_name` collects 0 items (`rc=4`); passing the class name or `-k <func_name>` selects the 6 parameterized cases in each file.
6. **All other claims in `A2`, `B1`–`B6`:** **Verified right** (`[Confirmed]`).

---

## 9. Found but not changed

Per Rule 0.1 (read-only review), no repository files were modified. All items uncovered during review are recorded in Section 3 (`F-A1`..`F-A4`, `F-B1`, `F-B2`), including:
- `docs/context/repo-tree.txt`: unstaged modification present from an earlier thread's `apc-bundle.sh` run; left untouched.
- `F-A1` (`docs/decisions/decision-log.md:462`): `[D-59](6)` sensitivity pair `(3, 6)` vs `(2, 5)`, accuracy bounds, mean shortlist size note, and single-insert / fixed-seed caveats.
- `F-A2` (`tests/test_bounded_bucket_strategy.py:565,1296`): missing `assert diag["merge_occurred"] is False` after `on_inserted()` when `inside_bucket_span is True` (allowing mutant `M-28` to survive).
- `F-B1` (`src/graph_insertion/strategies/embedding_threshold.py:208,216`): `np.asarray` coercion and missing `or not np.isfinite(norm)` check on `float32` norm overflow.

---

## 10. Open questions

1. **Sensitivity pair in `[D-59](6)` (`(2, 5)` vs `(3, 6)`):** When updating `[D-59](6)` for `F-A1`, does the APC prefer to standardize `[D-59](6)` on `(s_min=2, s_max=5)` (`300` sweep / `295` accuracy calls, matching `bounded_bucket.py:36`, `test_bounded_bucket_strategy.py:244`, and `[D-35](4)`), or list both `(2, 5)` and `(3, 6)`?
2. **Part A session independence:** Because Luke ran `STRAT-004-R` in the same session (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`) that ran `STRAT-004`, does the APC accept the automated `float64` reference and 43-mutant verification above (which caught `F-A1` and `F-A2`), or want a separate non-Gemini session to spot-check Part A?
