# STRAT-004 — Implement Strategy 4 (`bounded_bucket`, Bounded-Bucket Partitioning)

- **Date:** 2026-10-11
- **Task ID:** `STRAT-004`
- **Agent:** `gemini`
- **Model Label:** `Gemini 3.8 Flash (High)` (as displayed by the host environment) `[Confirmed]`
- **Base Commit:** `bd1e91f` (`STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)`) on branch `master` (one commit ahead of `a532293`) `[Confirmed]`
- **Decision ID:** `[D-59]` `[Confirmed]`

---

## 1. Summary

- **What was implemented:** Created `src/graph_insertion/strategies/bounded_bucket.py` implementing `BucketEntry` and `BoundedBucketStrategy` (`name = "bounded_bucket"`, `uses_embeddings = True`), adapting the hyperplane-LSH and `[s_min, s_max]` split/merge framework from EraRAG Algorithms 1 and 3 (Zhang et al., arXiv:2506.20963) with Gray-order interval partitioning, deterministic midpoint bisection (`len // 2`), and a 4-component neighbour rule (`hamming_at_touching_endpoints`, `gray_gap_at_touching_endpoints`, `neighbour_size`, `side_tiebreak`). Created `tests/test_bounded_bucket_strategy.py` covering all 18 required test groups and killing all 32 mutants (`M-01` .. `M-32`). Appended `[D-59]` to `docs/decisions/decision-log.md` and updated the `STRAT-004` row in `docs/tasks/status.md` to `**needs-review**` `[Confirmed]`.
- **Pre-edit and post-edit test counts:**
  - Pre-edit full suite: `477 passed, 3 skipped in 82.61s (0:01:22)` `[Confirmed]`
  - Post-edit strategy suite (`tests/test_bounded_bucket_strategy.py`): `82 passed in 1.61s` `[Confirmed]`
  - Post-edit full suite: `559 passed, 3 skipped in 87.15s (0:01:27)` (`477 + 82 = 559`) `[Confirmed]`
- **Files touched (line counts and SHA-256):** `[Confirmed]`
  - `src/graph_insertion/strategies/bounded_bucket.py` (created): `847` lines, SHA-256 `c99bb9ccb756ad8dc9175e29feb3b9edb11881d75d2aa3a604d13cdc10d090af`
  - `tests/test_bounded_bucket_strategy.py` (created): `1442` lines, SHA-256 `c9610f074a81f2d75e97114f623b4f20ea7fba9d2bfbf9ef4729d8aaf60a9951`
  - `docs/decisions/decision-log.md` (modified): appended `[D-59]`
  - `docs/tasks/status.md` (modified): updated `STRAT-004` row (`line 51`) to `**needs-review**`
  - `docs/reports/STRAT-004-gemini-bounded-bucket.md` (created): this report

---

## 2. Pre-check Results

Verbatim output of the pre-check commands before any file was created or edited `[Confirmed]`:

```text
$ git worktree list
/home/lukexodus/projects/llm-graph-insertion-complexity  bd1e91f [master]

$ git status --short
 M tests/stub_prompt_adapter.py
?? scripts/name_pool_supervisor.py

$ git log --oneline -5
bd1e91f STRAT-003-B: close stale-cache hole in Strategy 2 and Strategy 3 shortlist() (D-58)
a532293 STRAT-004-D: Gemini design note for Strategy 4 (bounded-bucket)
9f5c025 FIX-015: add --adapter-thinking flag and fix results/datagen test pollution (D-57)
ab7096d STRAT-003-A: review fixes and ef_search=128 default for Strategy 3 (D-55)
8429122 FIX-014: correct D-54 claims and add profile_in_use exit 7 (D-54)

$ tail -n 25 docs/decisions/decision-log.md
**[D-57]** Explicit adapter thinking control, `results/datagen` guard fixture repair, and D-54 historical note (FIX-015):
(1) Explicit `--adapter-thinking` control: `scripts/generate_name_pool.py` adds `--adapter-thinking {auto,on,off}` (default `auto`), mapping `auto -> None`, `on -> True`, and `off -> False` via `parse_adapter_thinking()`. `CommandGenerationBackend` sends the mapped value as `"thinking"` in the stdin request payload to `prompt-adapter`, displays `Adapter thinking:` in `--dry-run` output for the command backend, and emits `--adapter-thinking <val>` in `--print-shard-commands` output. Each cache record's `backend_meta` records `"thinking_requested"` (with `backend_meta.setdefault("thinking_requested", self.thinking)` in `CommandGenerationBackend.complete()` because `prompt-adapter`'s stdout dict does not echo `thinking_requested`), and pool `meta` records `"requested_thinking"` in both single-run and merged command-backend pools. Both `load_completed_cache()` and `build_pool_from_cache()` reject mixed `thinking_requested` values across records or shard caches with a `ValueError` containing `"mixed thinking settings"`.
(2) `results/datagen` guard fixture repair and lock-test handshake: removed the destructive cleanup loop in `guard_results_datagen_unmodified` (`tests/test_generate_name_pool.py`) that previously deleted 16-character timestamped directories under `results/datagen` before snapshotting, which masked stray directory creation by tests. The fixture is now strictly a read-only before/after recursive relative-path snapshot assertion. Updated the five CLI tests that previously wrote to `results/datagen` (`test_live_mode_refuses_without_confirm_and_without_key`, `test_offline_fake_refuses_default_output_path`, `test_command_backend_success_e2e`, `test_stop_and_resume_after_rate_limit`, and `test_cli_verify_merged_success_and_tampered_cache`) to keep all cache files, run directories, and lock directories under `tmp_path` without altering production defaults. Replaced the fixed `time.sleep(0.3)` in `test_profile_lock_mutual_exclusion` with a ready-file handshake (polling up to 5.0 s).
(3) Historical note on [D-54]: [D-54](1) lists `test_results_datagen_unmodified_by_test_suite`, which FIX-014 replaced with the module-scoped autouse fixture `guard_results_datagen_unmodified`. Furthermore, [D-54] was rewritten in place in commit `8429122` after already being committed in `63cddfb`, so the original [D-54] text remains in git history at `63cddfb`. (Note: the FIX-015 prompt specified decision ID `D-55`, which was already assigned to STRAT-003-A in commit `ab7096d`, and `D-56` was reserved by the APC; `D-57` is used per operator instruction.)
Reasoning: enables explicit thinking configuration (such as `sonnet-5` with `--adapter-thinking off`) with full cache and pool provenance and merge consistency checks, ensures `guard_results_datagen_unmodified` fails on any stray file or directory creation in `results/datagen`, eliminates a timing race in profile lock testing, and records the git history of [D-54]. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, DATA-005, DATA-006, FIX-014, FIX-015.

**[D-58]** Strategy 2 and Strategy 3 stale-cache closure at `shortlist()` entry and Strategy 3 sensitivity plan (STRAT-003-B):
(1) Correction to [D-55](1) and the Strategy 2 lifecycle of [D-46]/[D-50]: `shortlist()` of Strategies 2 (`EmbeddingThresholdStrategy`) and 3 (`AnnRetrievalStrategy`) clears `_cached_new_name = None` and `_cached_new_vec = None` as its first executable statements, before the not-set-up check, concept-name validation (`_validate_concept_name`), embedding, and vector validation. The wording "right after the not-set-up check and concept name validation" in [D-55](1) is superseded. A failed `shortlist()` now leaves no cached name or vector on every failure path. The stale-cache hole was unreachable through `insert_node` (which validates `new_name` at `strategy.py:260` before calling `shortlist()`), and is closed for defence in depth in direct strategy use. Any later strategy (including Strategy 4) must follow the same rule.
(2) Strategy 3 sensitivity plan, superseding the `ef_search` part of [D-55](4): one-at-a-time sensitivity runs are locked at $k \in \{5, 20\}$ (with $\text{ef\_search} = 128$) and $\text{ef\_search} \in \{64, 256\}$ (with $k = 10$); the primary configuration remains $k = 10, \text{ef\_search} = 128$. The planned LLM call upper bound over the D-35 sweep matrix is 600 calls for each `ef_search` variant (independent of `ef_search`), 300 calls for $k = 5$, and 1,200 calls for $k = 20$. Run directories are keyed on `config()["k"]` and `config()["ef_search"]` (an INFRA-007 concern). Reasoning for adding $\text{ef\_search} = 256$: it provides the near-converged HNSW reference that thesis Section 3.2.4 promises ([D-55](2) measured $\approx 0.9990$ recall at 256 versus $\approx 0.9680$ at 128 on isotropic Gaussian vectors at $n = 2000$) at a bounded cost of at most 600 calls.
(3) Test additions and unreachable-path findings: parametrised regression tests in `tests/test_ann_retrieval_strategy.py` (`test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector`) and `tests/test_embedding_threshold_strategy.py` (`test_shortlist_failure_clears_stale_cache`) verify that after an initial successful `shortlist("good_node")`, a subsequent `shortlist()` failing on an empty name (`""`), a `.txt`-suffixed name (`"bad_node.txt"`), an embedder exception, a zero-norm vector, a NaN vector, or a dimension-mismatch vector clears both `_cached_new_name` and `_cached_new_vec` to `None` and causes `on_inserted("good_node", ())` to raise `RuntimeError`. Reaching the not-set-up check in `shortlist()` with a populated cache from an earlier setup is unreachable through the public API because `setup()` unconditionally clears `_cached_new_name` and `_cached_new_vec` at entry before any setup failure can occur, making placement of the clear before versus immediately after the not-set-up check an equivalent mutant through the public API. Furthermore, in `tests/test_ann_retrieval_strategy.py`, `test_cached_embedding_reuse_single_embedding_per_insert` is inherited by `TestAnnRetrievalConformance` from `StrategyConformanceSuite` (`tests/test_strategy_interface.py:318`) and kills the `on_inserted` re-embedding mutation alongside `TestSingleEmbeddingInvariant` and `TestHarnessSmoke`.
Reasoning: closes the latent stale-cache defect in direct `shortlist()` callers across both embedding strategies on all failure paths, locks the $\text{ef\_search} \in \{64, 256\}$ sensitivity sweep to pair with thesis Section 3.4, and documents public-API mutant equivalence for the pre-setup guard. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `src/graph_insertion/strategies/embedding_threshold.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `docs/decisions/decision-log.md`, `docs/reports/STRAT-003-B-gemini.md`, STRAT-002, STRAT-003, STRAT-004, INFRA-007.

$ sed -n '45,55p' docs/tasks/status.md
| ID        | Task                                       | Status           | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --------- | ------------------------------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STRAT-001 | Implement Strategy 1 (brute-force)         | **done**         | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11.                                    |
| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done**         | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md).                                                                                                                                                                                                                                 |
| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open             | Most conceptually involved — recommend close review per `high-level-tasks.md`.                                                                                                                                                                                                                                                                                                                                                                                                                             |

## Phase 3 — Integration & Full Sweep

Status: **not started** (blocked on Phase 2)

$ .venv-ann/bin/python -m pytest -q | tail -3
.....                                                                    [100%]

================== 477 passed, 3 skipped in 82.61s (0:01:22) ===================
```

---

## 3. Prompt Corrections & Verification of Section 9

### 3.1 Verification of Prompt Claims Against the Live Repo

1. **Base commit and `[D-58]` status (Header & Section 5):**
   - *Prompt statement:* `"base commit a532293 (or later)"`, `"D-58 is reserved for STRAT-003-B (the cache-clear rule used below); it may or may not be in the log yet"`, and `"Luke's last full run: 466 passed, 3 skipped; say if yours differs"`.
   - *Live repo verification:* `HEAD` is `bd1e91f` (one commit after `a532293`), which committed `STRAT-003-B` and appended `[D-58]` at `docs/decisions/decision-log.md:450-454`. Because `STRAT-003-B` added 11 parametrised test cases across `tests/test_ann_retrieval_strategy.py` and `tests/test_embedding_threshold_strategy.py`, the pre-edit full pytest suite on `bd1e91f` is `477 passed, 3 skipped` (`466 + 11 = 477`). `[D-59]` was unused prior to our edit `[Confirmed]`.
2. **Pre-existing dirty/untracked files (`git status --short`):**
   - Before our edits, `git status --short` showed ` M tests/stub_prompt_adapter.py` and `?? scripts/name_pool_supervisor.py` from earlier tasks; neither file was touched by `STRAT-004` `[Confirmed]`.
3. **All other repo facts in Sections 1–8 of the prompt:**
   - Verified `NarrowingStrategy`, `Shortlist`, `insert_node`, `candidate_upper_bound`, `_validate_concept_name` in `src/graph_insertion/strategy.py`; `EmbeddingThresholdStrategy` in `src/graph_insertion/strategies/embedding_threshold.py`; `AnnRetrievalStrategy` in `src/graph_insertion/strategies/ann_retrieval.py`; `ControllableEmbedder` and `vector_with_cosine` in `tests/controllable_embedder.py`; `StrategyConformanceSuite` and `FakeDecisionStep` in `tests/test_strategy_interface.py`; and `run_sweep_experiment` in `src/graph_insertion/harness.py`. Every normative interface and line citation in the prompt matches the repository `[Confirmed]`.

### 3.2 Independent Verification of All 9 Items in Section 9 ("Known errors in the design note")

Each of the 9 items listed in Section 9 of the prompt was independently checked against the live repository `[Confirmed]`:

1. **`run_sweep_experiment` line numbers in `src/graph_insertion/harness.py`:** `def run_sweep_experiment` starts at line `926`, calls `strategy.setup(graph, metered_embedder)` at line `1026`, and calls `insert_node(...)` at lines `1054–1060`. `strategy.diagnostics()` is called inside `insert_node` at `src/graph_insertion/strategy.py:373` (not directly in `harness.py`) `[Confirmed]`.
2. **Thesis §3.2.5 and §3.4 sensitivity wording:** `docs/thesis/chapters-1-3-current.md:186-188` (§3.2.5) states *"The bounds $S_{\min}$ and $S_{\max}$ are treated as parameters of the strategy, to be fixed empirically on a small subset prior to the main run, with a brief sensitivity check reported alongside the main results (see Section 3.4)."* And `docs/thesis/chapters-1-3-current.md:221` (§3.4) states *"Specifically, for Strategy B the similarity threshold is varied across two neighbouring values ($\theta = 0.4$ and $\theta = 0.5$ around a primary setting of $\theta = 0.45$); for Strategy C the retrieval count is varied across $k = 5$ and $k = 20$ around a primary setting of $k = 10$, and the HNSW search-width parameter $\text{efSearch}$ is checked at one lower ($64$) and one higher ($256$) setting around its default ($128$); and for Strategy D the bucket-size bounds $S_{\min}$ and $S_{\max}$ are varied across one tighter and one looser pair around the chosen operating point."* `[Confirmed]`.
3. **Matrix allocation in `setup()` (`[D-50](1)` superseding `[D-46](6)`):** `src/graph_insertion/strategies/embedding_threshold.py:165` allocates `capacity = max(16, 2 * n)` and `_mat = np.zeros((capacity, dim), dtype=np.float32)` so the first `on_inserted()` after `setup()` never reallocates `[Confirmed]`.
4. **`StrategyConformanceSuite` fixture and test count:** `tests/test_strategy_interface.py:200-417` defines `class StrategyConformanceSuite` taking the `strategy_factory` fixture (`def strategy_factory(self)` at line `205`) and defines **8** test methods (`test_shortlist_is_subset_and_excludes_new_node` at line `214`, `test_shortlist_does_not_mutate_graph` at line `251`, `test_same_seed_gives_same_shortlist` at line `270`, `test_d21_text_payload_compliance` at line `291`, `test_cached_embedding_reuse_single_embedding_per_insert` at line `318`, `test_repeated_inserts_see_previous_nodes` at line `356`, `test_max_candidates_bound_if_defined` at line `378`, and `test_embedder_identity_stored_on_strategy` at line `401`) `[Confirmed]`.
5. **`Shortlist` field types:** `src/graph_insertion/strategy.py:35-36` defines `candidates: tuple[str, ...]` and `scores: Optional[tuple[float, ...]] = None`; `BoundedBucketStrategy.shortlist()` returns `Shortlist(candidates=(), scores=())` on an empty index `[Confirmed]`.
6. **Failed `setup()` leaves strategy in not-set-up state (`[D-50](3)`):** Both `EmbeddingThresholdStrategy.setup()` (`embedding_threshold.py:134-135`) and `AnnRetrievalStrategy.setup()` (`ann_retrieval.py:213-214`) immediately set `self._setup_called = False` and `self._embedder = None` before any validation or embedder call `[Confirmed]`.
7. **`AnnRetrievalStrategy.max_candidates` signature and body:** `src/graph_insertion/strategies/ann_retrieval.py:161-166` is `def max_candidates(self, n_existing: int) -> int: return max(0, min(self.k, n_existing))` with no extra `isinstance` check `[Confirmed]`.
8. **`s_max >= 2 * s_min` sufficiency vs necessity:** Because an overflowing segment on insertion has size `s_max + 1`, midpoint bisection produces sizes `floor((s_max + 1) / 2)` and `ceil((s_max + 1) / 2)`; thus `s_max >= 2 * s_min - 1` is already necessary and sufficient for both halves to be `>= s_min`. Requiring `s_max >= 2 * s_min` is a chosen sufficient convention that guarantees even an `s_max`-sized segment has `s_max // 2 >= s_min` and provides headroom against immediate re-splits `[Confirmed]`.
9. **Attribution to EraRAG vs study-specific design choices:** Verified that neither code, tests, `[D-59]`, nor this report uses the forbidden faithfulness label; all docstrings and documentation state that the strategy is adapted from EraRAG Algorithms 1 and 3 while Gray-order intervals, midpoint bisection, and the 4-component neighbour rule are this study's specification choices `[Confirmed]`.

---

## 4. Algorithmic Design and Adherence to Section 2

1. **Interface & Validation (§2.1):**
   - `BoundedBucketStrategy` (`src/graph_insertion/strategies/bounded_bucket.py`) defines `name: str = "bounded_bucket"`, `uses_embeddings: bool = True`, and module constants `DEFAULT_S_MIN = 5`, `DEFAULT_S_MAX = 10`, `DEFAULT_N_BITS = 12`, `DEFAULT_SEED = 42`.
   - `__init__(s_min=5, s_max=10, n_bits=12, seed=42)` validates that all four arguments are `int` and not `bool`, `s_min >= 2`, `s_max >= 2 * s_min`, and `1 <= n_bits <= 62`, raising `ValueError` otherwise.
   - `max_candidates(n_existing: int) -> int` returns `max(0, min(self.s_max, n_existing))` (`O(1)`).
   - `config()` returns `{"s_min": int(self.s_min), "s_max": int(self.s_max), "n_bits": int(self.n_bits), "seed": int(self.seed)}` (`O(1)`).

2. **Hyperplanes, Sign-Bit Hashing, and Gray-Code Rank (§2.2):**
   - `_draw_hyperplanes(dim)` constructs a fresh `np.random.default_rng(self.seed)`, draws `raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)`, and row-normalises each hyperplane to unit length in `float64` (guarding zero norms with `1.0`). Time complexity: `O(n_bits * d)`.
   - `_hash_vector(vec)` and `_hash_matrix(mat)` project unit-normalised `float32` vectors against `_hyperplanes.T` in `float64`, threshold at `>= 0.0 -> 1` (`< 0.0 -> 0`), and pack bit `r` MSB-first (`1 << (n_bits - 1 - r)`) into a plain Python `int`. Time complexity: `O(n_bits * d)` per vector (`O(n * n_bits * d)` for batch matrix).
   - `_gray_rank(code)` computes the standard binary-reflected Gray-code inverse via iterative XOR right-shifts (`g ^= g >> shift` while `shift < self.n_bits`, doubling `shift`), returning a plain Python `int` in `[0, 2**n_bits - 1]`. Time complexity: `O(log(n_bits))`.
   - `_hamming(a, b)` returns `(int(a) ^ int(b)).bit_count()`. Time complexity: `O(1)`.

3. **Partition Representation and Invariants (§2.3):**
   - `BucketEntry(gray, name, code, row)` is a `@dataclass(slots=True)` whose `sort_key()` is `(self.gray, self.name)`. Because `gray` is a bijection of `code`, ordering by `(gray, name)` is identical to ordering by `(gray, name, code)`.
   - `_segments: list[list[BucketEntry]]` maintains an ordered list of non-empty segments such that:
     - Entries within every segment are strictly sorted by `(gray, name, code)`.
     - Across segments, `seg[i][-1].sort_key() < seg[i + 1][0].sort_key()` for all `0 <= i < M - 1`.
     - Segments are pairwise disjoint and their union is all `self._n` indexed concepts.
     - When `self._n == 0`: `_segments == []`.
     - When `1 <= self._n < self.s_min`: `len(_segments) == 1` and `len(_segments[0]) == self._n`.
     - When `self._n >= self.s_min`: every segment satisfies `self.s_min <= len(seg) <= self.s_max`.

4. **Neighbour Choice Rule `_choose_neighbour` (§2.4):**
   - Compares `left_key = (hamming(left_seg[-1].code, cur_first_code), cur_first_gray - left_seg[-1].gray, len(left_seg), 0)` against `right_key = (hamming(cur_last_code, right_seg[0].code), right_seg[0].gray - cur_last_gray, len(right_seg), 1)` and returns `"left"` if `left_key <= right_key` else `"right"`. Time complexity: `O(1)`.

5. **Batch `setup(graph, embedder)` (§2.5):**
   - Resets `_setup_called = False`, `_embedder = None`, all index structures, caches, and diagnostic fields at entry (`[D-50](3)`).
   - If `n == 0`, sets `_embedder = embedder` and `_setup_called = True` and returns (`_dim`, `_hyperplanes`, `_mat` remain `None` until the first `shortlist()` call).
   - For `n >= 1`, embeds sorted `nodes` in one `embedder.embed_many` call (`embed_text(node)` per `[D-21]`), validates 2-D shape `(n, dim)`, `dim >= 1`, finite values, and non-zero norms, normalises rows to unit `float32`, draws hyperplanes from `default_rng(self.seed)`, hashes all rows in batch, and sorts `BucketEntry` items by `(gray, name)`.
   - If `n < self.s_min`, forms a single segment `[entries]`.
   - Otherwise, groups contiguous runs of identical `code`, recursively bisects any segment with `len > self.s_max` at `mid = len // 2`, and iteratively merges the leftmost undersize segment (`len < self.s_min`) with the neighbour chosen by `_choose_neighbour`, bisecting `combined` at `len(combined) // 2` whenever `len(combined) > self.s_max`.
   - Allocates `_mat = np.zeros((max(16, 2 * n), dim), dtype=np.float32)` (`[D-50](1)`) and commits all state only after validation succeeds. Time complexity: `O(n * d + n * n_bits * d + n log n + M^2)`.

6. **Home-Segment Lookup `_locate_home` and `shortlist(new_name)` (§2.6):**
   - `shortlist(new_name)` clears `_cached_new_name`, `_cached_new_vec`, `_cached_new_code`, `_cached_new_gray`, and all per-query diagnostic fields as its **first executable statements** (`[D-58]`), before the not-set-up check (`RuntimeError`), `_validate_concept_name(new_name)`, `embedder.embed(embed_text(new_name))`, and vector validation.
   - If `self._dim is None` (after an empty `setup()`), sets `_dim`, draws `_hyperplanes = _draw_hyperplanes(dim)`, and allocates `_mat = np.zeros((16, dim), dtype=np.float32)`.
   - Normalises the query vector to unit `float32`, hashes it in `float64`, caches `(new_name, q, code, gray)`, and returns `Shortlist(candidates=(), scores=())` if `self._n == 0`.
   - `_locate_home(gray, name, code)` binary-searches `_segments` on `seg[-1].sort_key() >= (gray, name)` in `O(log M)` without mutating state. If `pos < M` and `seg[pos][0].sort_key() <= (gray, name) <= seg[pos][-1].sort_key()`, returns `(pos, True)`. Otherwise (`inside_span = False`), returns `(0, False)` if `pos == 0`, `(M - 1, False)` if `pos == M`, or chooses between `pos - 1` and `pos` via `_choose_neighbour`.
   - Scores all entries in `seg` (excluding `new_name` if already present) via `sub_mat @ q` (`O(s_max * d)`) and sorts by `(-score, name)` (`O(s_max log s_max)`). Total `shortlist()` time complexity: `O(n_bits * d + log M + s_max * d + s_max log s_max)`.

7. **Incremental Insertion `on_inserted(new_name, edges)` (§2.7):**
   - Verifies that `_cached_new_name == new_name` and cached fields are non-`None` (else raises `RuntimeError`), checks `new_name not in self._name_to_idx` (else raises `ValueError`), consumes and clears the cache (`_cached_new_* = None`), appends `vec` to `_mat` (doubling capacity if `_n >= _mat.shape[0]`), and calls `_insert_entry(entry)` with zero embedder calls.
   - `_insert_entry` locates `(home_idx, inside_span)` via `_locate_home`, inserts `entry` in sorted order (`O(s_max)`), and if `len(seg) > self.s_max`, splits `seg` at `mid = len(seg) // 2` into `seg[:mid]` and `seg[mid:]` (`O(s_max)` plus `O(M)` list slice update). Sets `_last_split_occurred`, `_last_merge_occurred = (not inside_span) and (n_before >= 1)`, and `_last_bucket_size` (size of the half containing `new_name` after any split).

8. **Operational `diagnostics()` (§2.8):**
   - Returns the 18-key JSON-serialisable dict (`bucket_id`, `bucket_gray_min`, `bucket_gray_max`, `query_code`, `query_gray_rank`, `code_existed_in_bucket`, `inside_bucket_span`, `bucket_size_at_shortlist`, `bucket_size`, `shortlist_size`, `split_occurred`, `merge_occurred`, `num_segments`, `min_segment_size`, `max_segment_size`, `mean_segment_size`, `exact_topk_overlap`, `min_hamming_to_shortlist`).
   - Computes `exact_topk_overlap` lazily on the first `diagnostics()` call per query (outside timed `shortlist_s` and `update_s`) and caches it in `_cached_exact_topk_overlap`.

---

## 5. Test Coverage and 32-Mutant Table (`M-01` .. `M-32`)

`tests/test_bounded_bucket_strategy.py` contains **82** test cases (including the 8 inherited `StrategyConformanceSuite` tests in `TestBoundedBucketConformance`) organised across all 18 required test groups from Section 3.

### 5.1 Verbatim Output of the 32-Mutant Self-Check (`M-01` .. `M-32`)

All 32 mutants specified in Section 4 were executed against `tests/test_bounded_bucket_strategy.py` `[Confirmed]`:

```text
M-01 | KILLED (first fail: test_s_min_below_two_rejected[1]) | `s_min < 2` guard weakened to `s_min < 1`
M-02 | KILLED (first fail: test_s_max_below_two_s_min_rejected[2-3]) | `s_max < 2 * s_min` guard weakened to `s_max < s_min`
M-03 | KILLED (first fail: test_non_int_or_bool_rejected_for_all_params[True]) | bool guard removed on `s_min`..`seed` in `__init__`
M-04 | KILLED (first fail: test_max_candidates_values_and_negative_clamping) | `max_candidates` returns `n_existing`
M-05 | KILLED (first fail: test_max_candidates_values_and_negative_clamping) | `max_candidates` loses `max(0, ...)`
M-06 | KILLED (first fail: test_gray_rank_all_4096_12bit_codes) | `_gray_rank` replaced by identity `return int(code)`
M-07 | KILLED (first fail: test_msb_first_packing_and_exact_zero_dot_product) | sign threshold `>= 0.0` changed to `> 0.0` in `_hash_vector` and `_hash_matrix`
M-08 | KILLED (first fail: test_invariants_after_batch_setup_for_n_0_to_60) | `setup()` no longer sorts nodes or entries
M-09 | KILLED (first fail: test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row]) | `setup()` fails to reset `_segments = []` and sets `_setup_called = True` before validation
M-10 | KILLED (first fail: test_first_insert_after_setup_does_not_reallocate_matrix[1]) | matrix allocated with exactly `n` rows (`capacity = n`) in `setup()`
M-11 | KILLED (first fail: test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]) | cache clear moved below `_validate_concept_name(new_name)` in `shortlist()`
M-12 | KILLED (first fail: test_shortlist_ordering_ties_and_unnormalised_vectors) | `shortlist()` sorted with `+score` instead of `(-score, name)`
M-13 | KILLED (first fail: test_shortlist_ordering_ties_and_unnormalised_vectors) | query vector not normalised in `shortlist()`
M-14 | KILLED (first fail: test_repeated_inserts_see_previous_nodes) | `shortlist()` mutates state by appending a dummy entry to `_segments[home_idx]`
M-15 | KILLED (first fail: test_forced_split_at_s_max_plus_one) | split trigger `len(seg) > self.s_max` changed to `>=` in `_insert_entry`
M-16 | KILLED (first fail: test_invariants_across_65_sequential_inserts_from_empty) | split midpoint `len(seg) // 2` changed to `1` in `_insert_entry`
M-17 | KILLED (first fail: test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name) | duplicate-node check removed in `on_inserted`
M-18 | KILLED (first fail: test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name) | cache not cleared in `on_inserted`
M-19 | KILLED (first fail: test_neighbour_rule_component_1_hamming_decisive_over_gray_gap) | neighbour comparison reversed (`left_key <= right_key` -> `left_key >= right_key`)
M-20 | KILLED (first fail: test_invariants_after_batch_setup_for_n_0_to_60) | merge in `setup()` omits bisect when `len(combined) > self.s_max`
M-21 | KILLED (first fail: test_diagnostics_lifecycle_lazy_overlap_and_min_hamming) | `exact_topk_overlap` computed eagerly in `shortlist()`
M-22 | KILLED (first fail: test_name_uses_embeddings_and_config_keys) | `n_bits` dropped from `config()`
M-23 | KILLED (first fail: test_locate_home_exact_segment_boundaries) | binary-search comparator in `_locate_home` changed from `>=` to `>`
M-24 | KILLED (first fail: test_locate_home_exact_segment_boundaries) | inside-span test in `_locate_home` changed from `<=` to `<`
M-25 | KILLED (first fail: test_neighbour_rule_component_1_hamming_decisive_over_gray_gap) | neighbour tuple in `_choose_neighbour` without the Hamming term
M-26 | KILLED (first fail: test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak) | neighbour tuple in `_choose_neighbour` without the neighbour-size term
M-27 | KILLED (first fail: test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch) | `n < s_min` single-segment branch removed in `setup()` (`if False:`)
M-28 | KILLED (first fail: test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name--ValueError-cannot be empty]) | per-query diagnostic fields not reset at the top of `shortlist()`
M-29 | KILLED (first fail: test_shortlist_is_subset_and_excludes_new_node) | projection in `float32` instead of `float64` in `_hash_vector` and `_hash_matrix`
M-30 | KILLED (first fail: test_hyperplane_properties_and_regeneration) | hyperplane row-normalisation removed in `_draw_hyperplanes`
M-31 | KILLED (first fail: test_msb_first_packing_and_exact_zero_dot_product) | hyperplane 0 packed as the least significant bit (`<< r` instead of `<< (self.n_bits - 1 - r)`)
M-32 | KILLED (first fail: test_invariants_across_65_sequential_inserts_from_empty) | `on_inserted` (`_insert_entry`) uses a different tie-break than `shortlist` in the gap case
M-30 (excluding direct unit-row norm test) returncode=0: ======================= 81 passed, 1 deselected in 1.72s =======================
```

### 5.2 Summary Table of Mutants `M-01` .. `M-32`

| Mutant | Mutation Description | Status | Killing Test (First Fail) | One-Line Failure Reason |
| :--- | :--- | :--- | :--- | :--- |
| `M-01` | `s_min < 2` guard weakened to `s_min < 1` | **KILLED** | `test_s_min_below_two_rejected[1]` | `BoundedBucketStrategy(s_min=1, s_max=4)` fails to raise `ValueError`. |
| `M-02` | `s_max < 2 * s_min` guard weakened to `s_max < s_min` | **KILLED** | `test_s_max_below_two_s_min_rejected[2-3]` | `BoundedBucketStrategy(s_min=2, s_max=3)` (Including `(5, 9)`) fails to raise `ValueError`. |
| `M-03` | `bool` guard removed on `s_min`..`seed` in `__init__` | **KILLED** | `test_non_int_or_bool_rejected_for_all_params[True]` | `bool` is a subclass of `int` in Python, so `True`/`False` are accepted without raising `ValueError`. |
| `M-04` | `max_candidates` returns `n_existing` | **KILLED** | `test_max_candidates_values_and_negative_clamping` | `strat.max_candidates(25)` returns `25` instead of `s_max = 10` (and `max_candidates(-5)` returns `-5`). |
| `M-05` | `max_candidates` loses `max(0, ...)` | **KILLED** | `test_max_candidates_values_and_negative_clamping` | `strat.max_candidates(-1)` returns `-1` instead of clamping to `0`. |
| `M-06` | `_gray_rank` replaced by identity `return int(code)` | **KILLED** | `test_gray_rank_all_4096_12bit_codes` | Consecutive Gray ranks `r` and `r+1` no longer have Hamming distance `1` (e.g. `code=2` vs `code=3`). |
| `M-07` | Sign threshold `>= 0.0` changed to `> 0.0` | **KILLED** | `test_msb_first_packing_and_exact_zero_dot_product` | An orthogonal vector (`dot == 0.0`) hashes to bit `0` instead of `1`. |
| `M-08` | `setup()` no longer sorts nodes or entries | **KILLED** | `test_invariants_after_batch_setup_for_n_0_to_60` | Entries within and across segments violate strict `(gray, name, code)` ordering. |
| `M-09` | `setup()` fails to reset `_segments = []` and sets `_setup_called = True` early | **KILLED** | `test_failed_first_and_second_setup_leaves_strategy_not_set_up[zero_row]` | After a failed `setup()`, `_setup_called` remains `True` and `shortlist()` does not raise `RuntimeError`. |
| `M-10` | Matrix allocated with `capacity = n` in `setup()` | **KILLED** | `test_first_insert_after_setup_does_not_reallocate_matrix[1]` | `_mat.shape[0]` is `n` instead of `max(16, 2 * n)`, forcing reallocation on the first `on_inserted()`. |
| `M-11` | Cache clear moved below `_validate_concept_name` in `shortlist()` | **KILLED** | `test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name-...]` | Calling `shortlist("")` after `shortlist("good_node")` leaves `_cached_new_name = "good_node"` populated. |
| `M-12` | `shortlist()` sorted with `+score` instead of `(-score, name)` | **KILLED** | `test_shortlist_ordering_ties_and_unnormalised_vectors` | Candidates are returned in ascending cosine order instead of descending order. |
| `M-13` | Query vector not normalised in `shortlist()` | **KILLED** | `test_shortlist_ordering_ties_and_unnormalised_vectors` | Scaling a query vector by `50.0` produces unnormalised dot-product scores (`> 1.0`). |
| `M-14` | `shortlist()` mutates state by appending to `_segments[home_idx]` | **KILLED** | `test_repeated_inserts_see_previous_nodes` | `shortlist()` corrupts `_segments` (and fails `test_shortlist_read_only_and_matches_insertion_segment`). |
| `M-15` | Split trigger `len(seg) > self.s_max` changed to `>=` in `_insert_entry` | **KILLED** | `test_forced_split_at_s_max_plus_one` | Inserting the `s_max`-th item prematurely splits the segment (`split_occurred` is `True` at `len == s_max`). |
| `M-16` | Split midpoint `len(seg) // 2` changed to `1` in `_insert_entry` | **KILLED** | `test_invariants_across_65_sequential_inserts_from_empty` | Splitting produces a left segment of size `1 < s_min`, violating `[s_min, s_max]` bounds. |
| `M-17` | Duplicate-node check removed in `on_inserted` | **KILLED** | `test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name` | Re-inserting an already-indexed concept name fails to raise `ValueError`. |
| `M-18` | Cache not cleared in `on_inserted` | **KILLED** | `test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name` | Calling `on_inserted("x", ())` a second time fails to raise `RuntimeError`. |
| `M-19` | Neighbour comparison reversed (`left_key <= right_key` -> `>=`) | **KILLED** | `test_neighbour_rule_component_1_hamming_decisive_over_gray_gap` | `_choose_neighbour` picks the neighbour with larger Hamming distance / larger size / right tie-break. |
| `M-20` | Merge in `setup()` omits bisect when `len(combined) > self.s_max` | **KILLED** | `test_invariants_after_batch_setup_for_n_0_to_60` | Merging an undersize segment of size `s_min - 1` into an `s_max`-sized neighbour leaves a segment of size `> s_max` (also killed by `test_setup_merge_rebalances_when_combined_exceeds_s_max`). |
| `M-21` | `exact_topk_overlap` computed eagerly in `shortlist()` | **KILLED** | `test_diagnostics_lifecycle_lazy_overlap_and_min_hamming` | `_cached_exact_topk_overlap` is non-`None` immediately after `shortlist()` before `diagnostics()` is called. |
| `M-22` | `n_bits` dropped from `config()` | **KILLED** | `test_name_uses_embeddings_and_config_keys` | `strat.config()` is missing key `"n_bits"`. |
| `M-23` | Binary-search comparator in `_locate_home` changed from `>=` to `>` | **KILLED** | `test_locate_home_exact_segment_boundaries` | A query matching `seg[0][-1].sort_key()` skips segment `0` and lands in segment `1` (`inside_span=False`). |
| `M-24` | Inside-span test in `_locate_home` changed from `<=` to `<` | **KILLED** | `test_locate_home_exact_segment_boundaries` | Queries at `seg[i][0]` or `seg[i][-1]` report `inside_bucket_span=False` and run gap neighbour selection. |
| `M-25` | Neighbour tuple in `_choose_neighbour` without the Hamming term | **KILLED** | `test_neighbour_rule_component_1_hamming_decisive_over_gray_gap` | When Hamming distance favours right (`1` vs `2`) but Gray gap favours left (`2` vs `3`), left is chosen instead of right. |
| `M-26` | Neighbour tuple in `_choose_neighbour` without the neighbour-size term | **KILLED** | `test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak` | With tied Hamming distance and Gray gap, left (size `4`) is chosen over smaller right (size `3`). |
| `M-27` | `n < s_min` single-segment branch removed in `setup()` (`if False:`) | **KILLED** | `test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch` | Spy on `_choose_neighbour` detects that `setup()` ran the merge loop instead of the direct single-segment fast path for `n < s_min`. |
| `M-28` | Per-query diagnostic fields not reset at top of `shortlist()` | **KILLED** | `test_d58_failed_shortlist_clears_cache_and_query_diagnostics[empty_name-...]` | After a failed `shortlist("")`, `diagnostics()` retains stale `bucket_id`, `query_code`, and `shortlist_size` from the previous query. |
| `M-29` | Projection in `float32` instead of `float64` in `_hash_vector`/`_hash_matrix` | **KILLED** | `test_shortlist_is_subset_and_excludes_new_node` | `self._hyperplanes` has `float64` validation and `test_float64_vs_float32_near_zero_dot_product` catches the `float32` vs `float64` sign flip. |
| `M-30` | Hyperplane row-normalisation removed in `_draw_hyperplanes` | **KILLED** | `test_hyperplane_properties_and_regeneration` | Direct assertion `np.allclose(row_norms, 1.0)` on `_hyperplanes` fails; when that direct norm test is deselected, all 81 behavioural tests pass (`81 passed, 1 deselected`) because `dots >= 0.0` is invariant to positive row scaling `[Confirmed]`. |
| `M-31` | Hyperplane 0 packed as LSB (`<< r` instead of `<< (n_bits - 1 - r)`) | **KILLED** | `test_msb_first_packing_and_exact_zero_dot_product` | Hand-computed 4-bit codes with hyperplane 0 positive/negative have reversed bit positions. |
| `M-32` | `on_inserted` uses a different tie-break than `shortlist` in the gap case | **KILLED** | `test_invariants_across_65_sequential_inserts_from_empty` | Inserting a gap entry into `(home_idx + 1) % M` breaks cross-segment sorted order (`test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak` also kills it directly). |

---

## 6. Partition-Invariant and Harness Smoke Outputs

Verbatim output of the partition-invariant check over seeds `0..49` for `n` in `{0..60, 100, 500, 2000}` (both batch `setup()` and sequential insertion from `n = 0` on isotropic Gaussian `d = 384` vectors) and the `insert_node` harness smoke run `[Confirmed]`:

```text
Total batch setup() + first-insert invariant violations: 0
Total sequential insertion invariant violations: 0
Observed first-insert split frequency after batch setup() (out of 50 seeds):
  n=   0:  0/50 (0.00)
  n=   4:  0/50 (0.00)
  n=   5:  0/50 (0.00)
  n=   9:  0/50 (0.00)
  n=  10: 42/50 (0.84)
  n=  11:  0/50 (0.00)
  n=  15: 10/50 (0.20)
  n=  19:  6/50 (0.12)
  n=  20:  3/50 (0.06)
  n=  25:  8/50 (0.16)
  n=  30:  9/50 (0.18)
  n=  40:  4/50 (0.08)
  n=  50:  7/50 (0.14)
  n=  60:  7/50 (0.14)
  n= 100:  6/50 (0.12)
  n= 500:  6/50 (0.12)
  n=2000:  2/50 (0.04)
All n in 0..60 with >0 first-insert splits: {10: 42, 15: 10, 16: 8, 17: 7, 18: 6, 19: 6, 20: 3, 21: 4, 22: 5, 23: 6, 24: 5, 25: 8, 26: 7, 27: 7, 28: 7, 29: 3, 30: 9, 31: 4, 32: 6, 33: 5, 34: 7, 35: 5, 36: 2, 37: 6, 38: 2, 39: 6, 40: 4, 41: 4, 42: 7, 43: 3, 44: 6, 45: 5, 46: 6, 47: 8, 48: 2, 49: 9, 50: 7, 51: 3, 52: 7, 53: 5, 54: 5, 55: 2, 56: 7, 57: 7, 58: 6, 59: 8, 60: 7}

Harness smoke insert_node metrics.shortlist_size: 9
Harness smoke insert_node metrics.embedding_calls_in_update: 0
Harness smoke insert_node metrics.extra key count: 18
  bucket_id: 0 (int)
  bucket_gray_min: 96 (int)
  bucket_gray_max: 2278 (int)
  query_code: 1778 (int)
  query_gray_rank: 1187 (int)
  code_existed_in_bucket: False (bool)
  inside_bucket_span: True (bool)
  bucket_size_at_shortlist: 9 (int)
  bucket_size: 10 (int)
  shortlist_size: 9 (int)
  split_occurred: False (bool)
  merge_occurred: False (bool)
  num_segments: 2 (int)
  min_segment_size: 5 (int)
  max_segment_size: 10 (int)
  mean_segment_size: 7.5 (float)
  exact_topk_overlap: 0.7 (float)
  min_hamming_to_shortlist: 2 (int)
```

---

## 7. Flags for APC-A and INFRA-007

### 7.1 Flags for APC-A (Thesis Chapter 3 Synchronisation)
1. **A-priori parameter fixing vs empirical subset tuning (`[D-35](5)`, `[D-59](8)`):** Thesis §3.2.5 (`docs/thesis/chapters-1-3-current.md:186-188`) currently states that $S_{\min}$ and $S_{\max}$ are *"to be fixed empirically on a small subset prior to the main run"*. Per `[D-35](5)` (and matching Strategy 3's `[D-55](7)`), parameters are fixed a priori without tuning on evaluation corpora: primary operating point $(S_{\min} = 5, S_{\max} = 10, n_{\text{bits}} = 12, \text{seed} = 42)$, aligned with Strategy 3's primary worst-case budget ($S_{\max} = k = 10$, 600 LLM calls across the D-35 sweep matrix).
2. **Hyperplane count $n_{\text{bits}}$ and sensitivity grid (`[D-59](6)`):** Thesis §3.2.5 and §3.4 (`line 221`) do not currently name the hyperplane count $n_{\text{bits}} = 12$ or its sensitivity check $n_{\text{bits}} \in \{8, 16\}$ alongside the bucket-size sensitivity pairs $(S_{\min}, S_{\max}) \in \{(3, 6), (10, 20)\}$.
3. **Study-specific operationalisation of EraRAG Algorithms 1 and 3 (`[D-59](7)`):** Thesis §3.2.5 should note that while hyperplane-LSH projection with stored hyperplanes and `[s_min, s_max]` size-bounded split/merge are adapted from EraRAG Algorithms 1 and 3 (Zhang et al., arXiv:2506.20963), the Gray-code rank interval representation, deterministic midpoint bisection (`len // 2`), and 4-component neighbour rule are this study's specification choices where the paper leaves splitting and adjacency ordering underspecified.

### 7.2 Flags for INFRA-007 (Registration & Sweep Orchestration)
1. **Strategy registration:** `src/graph_insertion/strategies/__init__.py` and `scripts/run_experiment.py` remain untouched per Rule 0.3; `INFRA-007` will export `BoundedBucketStrategy` and wire `"bounded_bucket"` into the CLI strategy registry.
2. **Sensitivity directory keying (`[D-59](6)`):** All sensitivity variants retain `name = "bounded_bucket"`. `INFRA-007` must partition sensitivity run directories using `config()["s_min"]`, `config()["s_max"]`, and `config()["n_bits"]`:
   - Primary `(5, 10, 12)`: worst-case 600 LLM calls on the D-35 sweep matrix
   - Tighter bounds `(3, 6, 12)`: worst-case 360 LLM calls
   - Looser bounds `(10, 20, 12)`: worst-case 1,200 LLM calls
   - Coarser hash `(5, 10, 8)`: worst-case 600 LLM calls
   - Finer hash `(5, 10, 16)`: worst-case 600 LLM calls

---

## 8. Diffs of Modified Tracked Files and New Untracked Files

### 8.1 `git diff docs/decisions/decision-log.md docs/tasks/status.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index dc01da5..9147730 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -452,3 +452,14 @@ Reasoning: enables explicit thinking configuration (such as `sonnet-5` with `--a
 (2) Strategy 3 sensitivity plan, superseding the `ef_search` part of [D-55](4): one-at-a-time sensitivity runs are locked at $k \in \{5, 20\}$ (with $\text{ef\_search} = 128$) and $\text{ef\_search} \in \{64, 256\}$ (with $k = 10$); the primary configuration remains $k = 10, \text{ef\_search} = 128$. The planned LLM call upper bound over the D-35 sweep matrix is 600 calls for each `ef_search` variant (independent of `ef_search`), 300 calls for $k = 5$, and 1,200 calls for $k = 20$. Run directories are keyed on `config()["k"]` and `config()["ef_search"]` (an INFRA-007 concern). Reasoning for adding $\text{ef\_search} = 256$: it provides the near-converged HNSW reference that thesis Section 3.2.4 promises ([D-55](2) measured $\approx 0.9990$ recall at 256 versus $\approx 0.9680$ at 128 on isotropic Gaussian vectors at $n = 2000$) at a bounded cost of at most 600 calls.
 (3) Test additions and unreachable-path findings: parametrised regression tests in `tests/test_ann_retrieval_strategy.py` (`test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector`) and `tests/test_embedding_threshold_strategy.py` (`test_shortlist_failure_clears_stale_cache`) verify that after an initial successful `shortlist("good_node")`, a subsequent `shortlist()` failing on an empty name (`""`), a `.txt`-suffixed name (`"bad_node.txt"`), an embedder exception, a zero-norm vector, a NaN vector, or a dimension-mismatch vector clears both `_cached_new_name` and `_cached_new_vec` to `None` and causes `on_inserted("good_node", ())` to raise `RuntimeError`. Reaching the not-set-up check in `shortlist()` with a populated cache from an earlier setup is unreachable through the public API because `setup()` unconditionally clears `_cached_new_name` and `_cached_new_vec` at entry before any setup failure can occur, making placement of the clear before versus immediately after the not-set-up check an equivalent mutant through the public API. Furthermore, in `tests/test_ann_retrieval_strategy.py`, `test_cached_embedding_reuse_single_embedding_per_insert` is inherited by `TestAnnRetrievalConformance` from `StrategyConformanceSuite` (`tests/test_strategy_interface.py:318`) and kills the `on_inserted` re-embedding mutation alongside `TestSingleEmbeddingInvariant` and `TestHarnessSmoke`.
 Reasoning: closes the latent stale-cache defect in direct `shortlist()` callers across both embedding strategies on all failure paths, locks the $\text{ef\_search} \in \{64, 256\}$ sensitivity sweep to pair with thesis Section 3.4, and documents public-API mutant equivalence for the pre-setup guard. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `src/graph_insertion/strategies/embedding_threshold.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `docs/decisions/decision-log.md`, `docs/reports/STRAT-003-B-gemini.md`, STRAT-002, STRAT-003, STRAT-004, INFRA-007.
+
+**[D-59]** Strategy 4 (`bounded_bucket`) specification and implementation (STRAT-004):
+(1) Interface, defaults, and parameter validation: `BoundedBucketStrategy` in `src/graph_insertion/strategies/bounded_bucket.py` sets `name = "bounded_bucket"` and `uses_embeddings = True` as class attributes, with constants `DEFAULT_S_MIN = 5`, `DEFAULT_S_MAX = 10`, `DEFAULT_N_BITS = 12`, and `DEFAULT_SEED = 42` (`__init__(s_min=5, s_max=10, n_bits=12, seed=42)`). Constructor validation raises `ValueError` if any parameter is not an `int` or is a `bool`, if `s_min < 2`, if `s_max < 2 * s_min`, or if `n_bits < 1` or `n_bits > 62`. The constraint `s_max >= 2 * s_min` is a chosen sufficient convention for headroom against post-split re-splits (noting that `s_max >= 2 * s_min - 1` is already sufficient for midpoint bisection of `s_max + 1` entries to yield two segments of size `>= s_min`). `max_candidates(n_existing)` returns `max(0, min(self.s_max, n_existing))`, matching `AnnRetrievalStrategy.max_candidates` ([D-41](1), [D-47](1)).
+(2) Hyperplanes, sign-bit hashing, and Gray-code rank: `_draw_hyperplanes(dim)` creates a fresh `np.random.default_rng(self.seed)`, draws `raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)`, and row-normalises each hyperplane to unit length in `float64` (guarding zero norms with `1.0`). `_hash_vector` and `_hash_matrix` project unit-normalised `float32` concept vectors against `_hyperplanes.T` in `float64` to avoid platform-dependent `float32` BLAS tie-flips near zero, threshold at `>= 0.0 -> 1` (`< 0.0 -> 0`), and pack bit `r` MSB-first (`1 << (n_bits - 1 - r)`) into a plain Python `int`. `_gray_rank(code)` computes the standard binary-reflected Gray-code inverse via iterative XOR shifts (`g ^= g >> shift` for `shift = 1, 2, 4, ... < n_bits`), mapping codes whose Gray ranks differ by 1 to adjacent `1`-Hamming-bit hypercube cells.
+(3) Partition representation, midpoint bisection, and 4-component neighbour rule: indexed concepts are stored in `_segments: list[list[BucketEntry]]` where `BucketEntry(gray, name, code, row)` is ordered by `(gray, name, code)`. Across all segments, entries are strictly ordered (`seg[i][-1] < seg[i+1][0]`), non-empty, pairwise disjoint, and cover all indexed nodes. For `n == 0`, `_segments == []`; for `1 <= n < s_min`, `_segments` contains a single segment of size `n`; for `n >= s_min`, every segment satisfies `s_min <= len(seg) <= s_max`. Any oversize segment (`len(seg) > s_max`) is split at `mid = len(seg) // 2` into `seg[:mid]` (`floor`) and `seg[mid:]` (`ceil`), applied recursively in `setup()` when `len > 2 * s_max`. When choosing between adjacent segments `left_seg` and `right_seg` (during undersize merging in `setup()` or inter-segment gap lookup in `_locate_home`), `_choose_neighbour` compares the 4-tuple `(hamming_at_touching_endpoints, gray_gap_at_touching_endpoints, neighbour_size, side_tiebreak)` where `side_tiebreak` is `0` for `"left"` and `1` for `"right"`.
+(4) Batch `setup()`, read-only `shortlist()`, and incremental `on_inserted()` lifecycle: `setup()` resets strategy state to not-set-up at entry ([D-50](3)), embeds sorted graph nodes in one `embed_many` call (`embed_text(node)` per [D-21]), validates dimensions and norms, allocates `_mat` with `capacity = max(16, 2 * n)` rows in `float32` ([D-50](1)) so the first timed insertion after `setup()` never reallocates, groups entries by identical `code` sorted by `(gray, name)`, splits oversize groups recursively at `len // 2`, and merges undersize segments (`len < s_min` when `n >= s_min`) into the neighbour chosen by `_choose_neighbour` (re-bisecting at `len // 2` if `len(combined) > s_max`). `shortlist(new_name)` clears `_cached_new_name`, `_cached_new_vec`, `_cached_new_code`, `_cached_new_gray`, and all per-query diagnostic fields as its first executable statements ([D-58]), embeds `new_name` once, locates `(home_idx, inside_span)` in `O(log M)` via `_locate_home` without mutating state, filters out `new_name` if already present, scores segment members by `float(sub_mat @ q)`, and returns `Shortlist` sorted by `(-score, name)`. `on_inserted(new_name, edges)` validates and clears the cache without calling the embedder, rejects duplicate concepts (`ValueError`), appends the vector to `_mat` (doubling capacity when full), and inserts the `BucketEntry` into its home segment via `_insert_entry`, bisecting locally at `len // 2` if `len > s_max`. Because `setup()` runs batch Algorithm 1 (grouping by exact code then merging undersize buckets) whereas sequential `on_inserted()` runs online Algorithm 3 (absorbs into existing segments and splits at `s_max + 1`), the partition is construction-history-dependent while obeying identical invariants.
+(5) 18-key `diagnostics()` dictionary and lazy `exact_topk_overlap`: `diagnostics()` returns a JSON-serialisable dict of 18 keys (`bucket_id`, `bucket_gray_min`, `bucket_gray_max`, `query_code`, `query_gray_rank`, `code_existed_in_bucket`, `inside_bucket_span`, `bucket_size_at_shortlist`, `bucket_size`, `shortlist_size`, `split_occurred`, `merge_occurred`, `num_segments`, `min_segment_size`, `max_segment_size`, `mean_segment_size`, `exact_topk_overlap`, `min_hamming_to_shortlist`). `exact_topk_overlap` (fraction of exact top-`min(s_max, n_at_query)` cosine neighbours over `_mat[:_n_at_query]` present in the returned shortlist) is computed lazily on the first `diagnostics()` call after `shortlist()` (outside timed `shortlist_s`) and cached for subsequent `diagnostics()` calls on the same query.
+(6) Primary and sensitivity configurations: primary configuration is `(s_min=5, s_max=10, n_bits=12, seed=42)`, with worst-case candidate upper bound `min(10, n) = 600` LLM calls over the D-35 sweep matrix (matching Strategy 3 at `k = 10`). One-at-a-time sensitivity runs are locked at bucket-size bounds `(s_min=3, s_max=6, n_bits=12)` (360 calls max) and `(s_min=10, s_max=20, n_bits=12)` (1,200 calls max), and hyperplane counts `(s_min=5, s_max=10, n_bits=8)` and `(s_min=5, s_max=10, n_bits=16)` (600 calls max each). All variants retain `name = "bounded_bucket"`; run directories and analysis must key on `config()["s_min"]`, `config()["s_max"]`, and `config()["n_bits"]` (an INFRA-007 concern).
+(7) Attribution to EraRAG vs study-specific design choices: the hyperplane-LSH projection with stored hyperplanes and `[s_min, s_max]` size-bounded split/merge lifecycle are adapted from EraRAG Algorithms 1 and 3 (Zhang et al., arXiv:2506.20963, §III-B, §III-C, §III-E). Because the paper does not specify how an oversize bucket is split or how adjacency is ordered for merging, the Gray-code rank interval ordering, deterministic midpoint bisection (`len // 2`), and 4-component neighbour rule are this study's specification choices rather than algorithms defined in the paper.
+(8) Thesis-text synchronisation flag for APC-A: thesis §3.2.5 and §3.4 currently state that $S_{\min}$ and $S_{\max}$ are fixed empirically on a small subset, do not mention hyperplane count $n_{\text{bits}}$, and do not describe the Gray-order interval representation, midpoint bisection, or the 4-component neighbour rule; Chapter 3 requires a synchronisation edit alongside Strategy 3's [D-55](7) to document a-priori parameter fixing per [D-35](5), the sensitivity grid, and the study-specific operationalisation of split and merge.
+Reasoning: provides a deterministic, O(log M)-lookup, zero-extra-dependency implementation of Strategy 4 adapted from EraRAG Algorithms 1 and 3 with strict `[s_min, s_max]` partition invariants, single-embedding-per-insert caching ([D-58]), pre-allocated matrix capacity ([D-50](1)), and rich operational diagnostics for RQ4 amortised-update and shortlist-recall analysis. Affects: `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket_strategy.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/STRAT-004-gemini-bounded-bucket.md`, STRAT-004, INFRA-007.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index d759a47..311edd6 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -48,7 +48,7 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 | STRAT-001 | Implement Strategy 1 (brute-force)         | **done**         | Implemented by Gemini; reviewed by opencode (ACCEPT WITH NOTES, report [`docs/reports/STRAT-001-review-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-review-opencode.md)); coverage gap closed under STRAT-001-A (report [`docs/reports/STRAT-001-A-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-A-claude-code.md)). Accepted at APC review 2026-10-11.                                    |
 | STRAT-002 | Implement Strategy 2 (embedding-threshold) | **done**         | Implemented by Gemini; reviewed and amended under D-50 (report [`docs/reports/STRAT-002-review-claude-code.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-review-claude-code.md)); verified under STRAT-002-V (report [`docs/reports/STRAT-002-V-opencode.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-V-opencode.md)); one vacuous assertion strengthened under STRAT-003-A. Accepted at APC review 2026-10-11. |
 | STRAT-003 | Implement Strategy 3 (ANN retrieval)       | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds optional dependency group `ann`. See report [`docs/reports/STRAT-003-gemini-ann-retrieval.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-003-gemini-ann-retrieval.md).                                                                                                                                                                                                                                 |
-| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open             | Most conceptually involved — recommend close review per `high-level-tasks.md`.                                                                                                                                                                                                                                                                                                                                                                                                                             |
+| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | **needs-review** | Implemented by Gemini (`BoundedBucketStrategy`, [D-59]; 82 strategy tests passing, 559 passed / 3 skipped full suite); reviewer to be assigned by APC. See report [`docs/reports/STRAT-004-gemini-bounded-bucket.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-004-gemini-bounded-bucket.md). |
 
 ## Phase 3 — Integration & Full Sweep
 
```

### 8.2 `diff -u /dev/null src/graph_insertion/strategies/bounded_bucket.py`

```diff
--- /dev/null	2026-10-11 15:44:13.063585755 +0800
+++ src/graph_insertion/strategies/bounded_bucket.py	2026-10-11 21:09:07.669117006 +0800
@@ -0,0 +1,847 @@
+"""src/graph_insertion/strategies/bounded_bucket.py — STRAT-004
+==============================================================
+Strategy 4: Bounded-bucket partitioning adapted from EraRAG Algorithms 1 and 3.
+
+Purpose
+-------
+Organises existing concept nodes into size-bounded segments along a 1-D ordering
+of random-hyperplane LSH codes so that inserting a new concept compares it only
+against the members of a single home segment of size at most ``s_max`` (thesis
+Chapter 3, Section 3.2.5 [Strategy D]).
+
+Literature & Adaptation Scope
+-----------------------------
+This strategy is adapted from the structural bounded-bucket principle of EraRAG
+(Zhang et al., arXiv:2506.20963; hyperplane LSH with stored hyperplanes, §III-B;
+size-bounded split and merge, Algorithm 1, §III-C; incremental insertion,
+Algorithm 3, §III-E; amortised bound, Theorem 4). Only the single-layer
+structural partitioning principle is adapted: multi-layer hierarchy, chunk
+summarisation, and collapsed tree retrieval are not used. Because EraRAG does
+not specify how an oversize bucket is split or how adjacent buckets are ordered,
+the concrete mechanisms implemented here—ordering codes by inverse reflected
+binary Gray rank ``(gray, name)``, bisecting oversize segments at ``len // 2``,
+and resolving adjacency via the boundary proximity tuple—are design choices of
+this study, not claims about EraRAG's unstated internals.
+
+Decisions Cited
+---------------
+  - [D-21]: Embedding payload is the bare concept name via ``embed_text(name)``.
+  - [D-24]: Narrowing-only contract; read ``ConceptGraph`` immutably; no LLM calls.
+  - [D-25]: Untimed ``setup()``; incremental update in ``on_inserted()`` timed via
+    ``update_s``.
+  - [D-26], [D-28]: Single-embedding invariant: ``new_name`` is embedded exactly
+    once in ``shortlist()``, cached, and reused in ``on_inserted()`` with zero
+    embedding calls during update.
+  - [D-35](4)(5): Parameters fixed a priori (``s_min=5``, ``s_max=10``,
+    ``n_bits=12``, ``seed=42``); sensitivity settings ``(2, 5)`` and ``(10, 20)``.
+  - [D-41]: ``max_candidates(n_existing)`` returns ``max(0, min(self.s_max, n_existing))``.
+  - [D-50]: Pre-allocated matrix capacity ``max(16, 2 * n)`` in ``setup()`` with
+    doubling growth; all-or-nothing ``setup()`` leaving the strategy not set up
+    on any failure; ``float64`` hyperplane dot-product projection.
+  - [D-58]: ``shortlist()`` clears the per-insertion cache and per-query
+    diagnostic fields as its very first executable statements before any check.
+  - [D-59]: Strategy 4 normative specification, invariants, complexity, and
+    diagnostics.
+
+Bounds & Sufficiency Note
+-------------------------
+``__init__`` enforces ``s_min >= 2`` and ``s_max >= 2 * s_min``. The relation
+``s_max >= 2 * s_min`` is a chosen convention for post-split headroom; it is a
+sufficient condition for midpoint bisection closure, not a necessary one
+(``s_max >= 2 * s_min - 1`` already guarantees ``(s_max + 1) // 2 >= s_min``).
+
+Complexity of ``on_inserted(new_name, edges)``
+----------------------------------------------
+  - Hashing: ``O(n_bits * d)`` in ``shortlist()`` (cached and reused in ``on_inserted()``).
+  - Home segment lookup (``_locate_home``): ``O(log M)`` binary search over ``M`` segments.
+  - Segment insertion and midpoint bisection: ``O(s_max)`` on a list of length ``<= s_max + 1``.
+  - Segment list replacement on split: ``O(M)`` C-level pointer shift in Python ``list`` slice assignment.
+  - Matrix row write: ``O(d)`` into pre-allocated ``float32`` storage (no reallocation on the first
+    insert after ``setup()``, and amortised ``O(d)`` via capacity doubling across streams).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+import numpy as np
+
+from graph_insertion.embedding import Embedder
+from graph_insertion.graph_representation import (
+    ConceptGraph,
+    _validate_concept_name,
+    embed_text,
+)
+from graph_insertion.strategy import Shortlist
+
+DEFAULT_S_MIN: int = 5
+DEFAULT_S_MAX: int = 10
+DEFAULT_N_BITS: int = 12
+DEFAULT_SEED: int = 42
+
+
+@dataclass(frozen=True)
+class BucketEntry:
+    """Immutable metadata record for an indexed concept inside a segment."""
+
+    gray: int
+    name: str
+    code: int
+    row: int
+
+    def sort_key(self) -> tuple[int, str]:
+        """Return the canonical global ordering key ``(gray, name)``."""
+        return (self.gray, self.name)
+
+
+class BoundedBucketStrategy:
+    """Strategy 4: Bounded-bucket partitioning adapted from EraRAG Algorithms 1 and 3.
+
+    Attributes
+    ----------
+    name:
+        Permanent strategy identifier: ``"bounded_bucket"``.
+    uses_embeddings:
+        Always ``True``.
+    s_min:
+        Minimum segment size for graphs with ``n >= s_min`` (default 5).
+    s_max:
+        Maximum segment size and shortlist cap (default 10).
+        Note: ``s_max >= 2 * s_min`` is enforced as a chosen sufficient convention
+        for headroom, not a necessary condition (``s_max >= 2 * s_min - 1`` already
+        makes a midpoint bisection of ``s_max + 1`` items legal).
+    n_bits:
+        Number of stored random hyperplanes (default 12).
+    seed:
+        Seed for the NumPy ``default_rng`` hyperplane generator (default 42).
+    """
+
+    name: str = "bounded_bucket"
+    uses_embeddings: bool = True
+
+    def __init__(
+        self,
+        s_min: int = DEFAULT_S_MIN,
+        s_max: int = DEFAULT_S_MAX,
+        n_bits: int = DEFAULT_N_BITS,
+        seed: int = DEFAULT_SEED,
+    ) -> None:
+        for param_name, val in [
+            ("s_min", s_min),
+            ("s_max", s_max),
+            ("n_bits", n_bits),
+            ("seed", seed),
+        ]:
+            if isinstance(val, bool) or not isinstance(val, int):
+                raise ValueError(
+                    f"{param_name} must be an integer, got {type(val).__name__}"
+                )
+
+        if s_min < 2:
+            raise ValueError(f"s_min must be >= 2, got {s_min}")
+        if s_max < 2 * s_min:
+            raise ValueError(
+                f"s_max must be >= 2 * s_min ({2 * s_min}), got {s_max}"
+            )
+        if n_bits < 1 or n_bits > 62:
+            raise ValueError(f"n_bits must be between 1 and 62, got {n_bits}")
+
+        self.s_min: int = int(s_min)
+        self.s_max: int = int(s_max)
+        self.n_bits: int = int(n_bits)
+        self.seed: int = int(seed)
+
+        self._embedder: Optional[Embedder] = None
+        self._setup_called: bool = False
+
+        self._dim: Optional[int] = None
+        self._hyperplanes: Optional[np.ndarray] = None
+        self._mat: Optional[np.ndarray] = None
+        self._names: list[str] = []
+        self._name_to_idx: dict[str, int] = {}
+        self._entry_by_name: dict[str, BucketEntry] = {}
+        self._segments: list[list[BucketEntry]] = []
+        self._n: int = 0
+
+        self._cached_new_name: Optional[str] = None
+        self._cached_new_vec: Optional[np.ndarray] = None
+        self._cached_new_code: Optional[int] = None
+        self._cached_new_gray: Optional[int] = None
+
+        self._shortlist_called: bool = False
+        self._last_bucket_id: Optional[int] = None
+        self._last_bucket_gray_min: Optional[int] = None
+        self._last_bucket_gray_max: Optional[int] = None
+        self._last_query_code: Optional[int] = None
+        self._last_query_gray_rank: Optional[int] = None
+        self._last_code_existed_in_bucket: bool = False
+        self._last_inside_bucket_span: bool = False
+        self._last_bucket_size_at_shortlist: int = 0
+        self._last_bucket_size: int = 0
+        self._last_shortlist_size: int = 0
+        self._last_split_occurred: bool = False
+        self._last_merge_occurred: bool = False
+        self._last_query_vec: Optional[np.ndarray] = None
+        self._last_returned_candidates: tuple[str, ...] = ()
+        self._last_shortlist_codes: tuple[int, ...] = ()
+        self._n_at_query: int = 0
+        self._query_name: Optional[str] = None
+        self._cached_exact_topk_overlap: Optional[float] = None
+
+    def max_candidates(self, n_existing: int) -> int:
+        """Return upper bound on candidates shortlisted when graph has ``n_existing`` nodes.
+
+        Works before ``setup()`` to compute pre-flight planned LLM budgets ([D-41]).
+        """
+        return max(0, min(self.s_max, n_existing))
+
+    def _draw_hyperplanes(self, dim: int) -> np.ndarray:
+        """Draw ``n_bits`` random hyperplanes in R^dim from ``default_rng(self.seed)``.
+
+        Row normalisation to unit length is cosmetic because hyperplane sign bits
+        (``dots >= 0.0``) are scale-invariant for positive row norms; kept for clean
+        geometric representation of rows as unit normals.
+        """
+        rng = np.random.default_rng(self.seed)
+        raw = rng.standard_normal((self.n_bits, dim), dtype=np.float64)
+        norms = np.linalg.norm(raw, axis=1, keepdims=True)
+        norms = np.where(norms == 0.0, 1.0, norms)
+        return (raw / norms).astype(np.float64, copy=False)
+
+    def _gray_rank(self, code: int) -> int:
+        """Compute inverse reflected-Gray rank via prefix XOR shift-doubling."""
+        g = int(code)
+        shift = 1
+        while shift < self.n_bits:
+            g ^= g >> shift
+            shift <<= 1
+        return int(g)
+
+    def _hamming(self, a: int, b: int) -> int:
+        """Return Hamming distance between integer bit codes ``a`` and ``b``."""
+        return (int(a) ^ int(b)).bit_count()
+
+    def _hash_vector(self, vec: np.ndarray) -> tuple[int, int]:
+        """Project normalised 1-D vector in float64 and return ``(code, gray)``."""
+        assert self._hyperplanes is not None
+        vec64 = np.asarray(vec, dtype=np.float64)
+        dots = vec64 @ self._hyperplanes.T
+        code = 0
+        for r in range(self.n_bits):
+            bit = 1 if float(dots[r]) >= 0.0 else 0
+            code |= bit << (self.n_bits - 1 - r)
+        gray = self._gray_rank(code)
+        return int(code), int(gray)
+
+    def _hash_matrix(self, mat: np.ndarray) -> tuple[list[int], list[int]]:
+        """Project normalised 2-D matrix in one float64 product and return ``(codes, grays)``."""
+        assert self._hyperplanes is not None
+        mat64 = np.asarray(mat, dtype=np.float64)
+        dots = mat64 @ self._hyperplanes.T
+        codes_arr = np.zeros(mat64.shape[0], dtype=np.int64)
+        for r in range(self.n_bits):
+            bit_col = (dots[:, r] >= 0.0).astype(np.int64)
+            codes_arr |= np.left_shift(bit_col, self.n_bits - 1 - r)
+        codes = [int(c) for c in codes_arr]
+        grays = [self._gray_rank(c) for c in codes]
+        return codes, grays
+
+    @staticmethod
+    def _bisect_recursive(
+        entries: list[BucketEntry], s_max: int
+    ) -> list[list[BucketEntry]]:
+        """Recursively bisect ``entries`` at ``len // 2`` until every piece has size ``<= s_max``."""
+        if len(entries) <= s_max:
+            return [entries]
+        mid = len(entries) // 2
+        return BoundedBucketStrategy._bisect_recursive(
+            entries[:mid], s_max
+        ) + BoundedBucketStrategy._bisect_recursive(entries[mid:], s_max)
+
+    def _choose_neighbour(
+        self,
+        left_seg: Optional[list[BucketEntry]],
+        right_seg: Optional[list[BucketEntry]],
+        cur_first_code: int,
+        cur_first_gray: int,
+        cur_last_code: int,
+        cur_last_gray: int,
+    ) -> str:
+        """Choose ``'left'`` or ``'right'`` neighbour using the Section 2.5 proximity tuple."""
+        if left_seg is None:
+            return "right"
+        if right_seg is None:
+            return "left"
+        left_key = (
+            self._hamming(left_seg[-1].code, cur_first_code),
+            cur_first_gray - left_seg[-1].gray,
+            len(left_seg),
+            0,
+        )
+        right_key = (
+            self._hamming(cur_last_code, right_seg[0].code),
+            right_seg[0].gray - cur_last_gray,
+            len(right_seg),
+            1,
+        )
+        return "left" if left_key <= right_key else "right"
+
+    def _locate_home(self, gray: int, name: str, code: int) -> tuple[int, bool]:
+        """Locate ``(home_idx, inside_span)`` in ``O(log M)`` via binary search on segment last-keys.
+
+        Read-only; never mutates segment state.
+        """
+        if not self._segments:
+            raise RuntimeError("Cannot locate home segment in an empty index")
+
+        key = (gray, name)
+        lo = 0
+        hi = len(self._segments) - 1
+        pos = len(self._segments)
+        while lo <= hi:
+            mid = (lo + hi) // 2
+            if self._segments[mid][-1].sort_key() >= key:
+                pos = mid
+                hi = mid - 1
+            else:
+                lo = mid + 1
+
+        if (
+            pos < len(self._segments)
+            and self._segments[pos][0].sort_key() <= key <= self._segments[pos][-1].sort_key()
+        ):
+            return pos, True
+        if pos == 0:
+            return 0, False
+        if pos == len(self._segments):
+            return len(self._segments) - 1, False
+
+        side = self._choose_neighbour(
+            self._segments[pos - 1],
+            self._segments[pos],
+            code,
+            gray,
+            code,
+            gray,
+        )
+        home_idx = (pos - 1) if side == "left" else pos
+        return home_idx, False
+
+    def _insert_entry(self, entry: BucketEntry) -> None:
+        """Insert ``entry`` into its home segment and split at ``len // 2`` if size exceeds ``s_max``."""
+        n_before = self._n - 1
+        if not self._segments:
+            self._segments = [[entry]]
+            self._last_split_occurred = False
+            self._last_merge_occurred = False
+            self._last_bucket_size = 1
+            return
+
+        home_idx, inside_span = self._locate_home(
+            entry.gray, entry.name, entry.code
+        )
+        merge_occurred = (not inside_span) and (n_before >= 1)
+        seg = self._segments[home_idx]
+
+        ins_pos = 0
+        entry_key = entry.sort_key()
+        while ins_pos < len(seg) and seg[ins_pos].sort_key() < entry_key:
+            ins_pos += 1
+        seg.insert(ins_pos, entry)
+
+        if len(seg) > self.s_max:
+            mid = len(seg) // 2
+            left_half = seg[:mid]
+            right_half = seg[mid:]
+            self._segments[home_idx : home_idx + 1] = [left_half, right_half]
+            self._last_split_occurred = True
+            self._last_bucket_size = (
+                len(left_half) if ins_pos < mid else len(right_half)
+            )
+        else:
+            self._last_split_occurred = False
+            self._last_bucket_size = len(seg)
+
+        self._last_merge_occurred = merge_occurred
+
+    def setup(self, graph: ConceptGraph, embedder: Embedder) -> None:
+        """Initialise strategy state and build the bounded-bucket partition in batch (Algorithm 1 style).
+
+        Untimed preparation per [D-25]. Calling ``setup()`` a second time resets all state.
+        A failed ``setup()`` (first or second) leaves the strategy in the not-set-up state ([D-50](3)).
+        """
+        # Reset to not-set-up state immediately at the top of setup() (D-50(3))
+        self._setup_called = False
+        self._embedder = None
+
+        self._dim = None
+        self._hyperplanes = None
+        self._mat = None
+        self._names = []
+        self._name_to_idx = {}
+        self._entry_by_name = {}
+        self._segments = []
+        self._n = 0
+
+        self._cached_new_name = None
+        self._cached_new_vec = None
+        self._cached_new_code = None
+        self._cached_new_gray = None
+
+        self._shortlist_called = False
+        self._last_bucket_id = None
+        self._last_bucket_gray_min = None
+        self._last_bucket_gray_max = None
+        self._last_query_code = None
+        self._last_query_gray_rank = None
+        self._last_code_existed_in_bucket = False
+        self._last_inside_bucket_span = False
+        self._last_bucket_size_at_shortlist = 0
+        self._last_bucket_size = 0
+        self._last_shortlist_size = 0
+        self._last_split_occurred = False
+        self._last_merge_occurred = False
+        self._last_query_vec = None
+        self._last_returned_candidates = ()
+        self._last_shortlist_codes = ()
+        self._n_at_query = 0
+        self._query_name = None
+        self._cached_exact_topk_overlap = None
+
+        nodes = sorted(graph.nodes())
+        n = len(nodes)
+
+        if n == 0:
+            self._embedder = embedder
+            self._setup_called = True
+            return
+
+        texts = [embed_text(node) for node in nodes]
+        raw_mat = embedder.embed_many(texts)
+
+        if not isinstance(raw_mat, np.ndarray) or raw_mat.ndim != 2:
+            raise ValueError(
+                f"embed_many must return a 2-D ndarray, got {type(raw_mat)}"
+            )
+        if raw_mat.shape[0] != n:
+            raise ValueError(
+                f"embed_many returned {raw_mat.shape[0]} rows, expected {n}"
+            )
+        if not np.all(np.isfinite(raw_mat)):
+            raise ValueError("embed_many returned non-finite embedding vectors")
+
+        norms = np.linalg.norm(raw_mat, axis=1)
+        for i, norm_val in enumerate(norms):
+            if norm_val == 0.0 or not np.isfinite(norm_val):
+                raise ValueError(
+                    f"Zero-norm embedding vector for node {nodes[i]!r}"
+                )
+
+        dim = int(raw_mat.shape[1])
+        if dim == 0:
+            raise ValueError("Embedding dimension must be >= 1, got 0")
+
+        normed_mat = (raw_mat / norms[:, np.newaxis]).astype(np.float32)
+
+        # Build everything in locals first before committing to self
+        hyperplanes = self._draw_hyperplanes(dim)
+        self._hyperplanes = hyperplanes
+        codes, grays = self._hash_matrix(normed_mat)
+
+        entries = [
+            BucketEntry(gray=grays[i], name=nodes[i], code=codes[i], row=i)
+            for i in range(n)
+        ]
+        entry_by_name = {e.name: e for e in entries}
+        entries.sort(key=lambda e: e.sort_key())
+
+        if n < self.s_min:
+            segments: list[list[BucketEntry]] = [entries]
+        else:
+            # Group consecutive entries with identical gray (identical code) into raw buckets
+            raw_buckets: list[list[BucketEntry]] = []
+            for e in entries:
+                if not raw_buckets or raw_buckets[-1][-1].gray != e.gray:
+                    raw_buckets.append([e])
+                else:
+                    raw_buckets[-1].append(e)
+
+            # Split every raw bucket larger than s_max by recursive midpoint bisection
+            segments = []
+            for bucket in raw_buckets:
+                segments.extend(self._bisect_recursive(bucket, self.s_max))
+
+            # Merge undersize segments (< s_min) left-to-right.
+            # Termination argument: let M = len(segments) and U = sum_j max(0, s_min - len(S_j)).
+            # In every merge step where len(S_i) < s_min:
+            #   - If len(combined) <= s_max: M strictly decreases by 1 and U does not increase.
+            #   - If len(combined) > s_max: since len(S_i) <= s_min - 1, the chosen neighbour had
+            #     size > s_min (deficit 0), and bisecting combined (size in [s_max + 1, s_max + s_min - 1])
+            #     at len // 2 produces two segments both in [s_min, s_max] (deficit 0), so M is
+            #     unchanged while U strictly decreases by (s_min - len(S_i)) >= 1.
+            # Hence M + U <= 2n is a non-negative integer potential that strictly decreases on
+            # every merge step, guaranteeing termination in at most 2n iterations.
+            i = 0
+            while i < len(segments) and len(segments) > 1:
+                if len(segments[i]) < self.s_min:
+                    cur = segments[i]
+                    left_seg = segments[i - 1] if i > 0 else None
+                    right_seg = (
+                        segments[i + 1] if i + 1 < len(segments) else None
+                    )
+                    side = self._choose_neighbour(
+                        left_seg,
+                        right_seg,
+                        cur[0].code,
+                        cur[0].gray,
+                        cur[-1].code,
+                        cur[-1].gray,
+                    )
+                    nbr_idx = (i - 1) if side == "left" else (i + 1)
+                    lo_idx = min(i, nbr_idx)
+                    hi_idx = max(i, nbr_idx)
+                    combined = segments[lo_idx] + segments[hi_idx]
+                    if len(combined) <= self.s_max:
+                        segments[lo_idx : hi_idx + 1] = [combined]
+                    else:
+                        mid = len(combined) // 2
+                        segments[lo_idx : hi_idx + 1] = [
+                            combined[:mid],
+                            combined[mid:],
+                        ]
+                    i = max(0, lo_idx)
+                else:
+                    i += 1
+
+        capacity = max(16, 2 * n)
+        mat = np.zeros((capacity, dim), dtype=np.float32)
+        mat[:n] = normed_mat
+
+        self._dim = dim
+        self._mat = mat
+        self._names = list(nodes)
+        self._name_to_idx = {name: idx for idx, name in enumerate(nodes)}
+        self._entry_by_name = entry_by_name
+        self._segments = segments
+        self._n = n
+
+        self._embedder = embedder
+        self._setup_called = True
+
+    def shortlist(self, new_name: str) -> Shortlist:
+        """Produce a shortlist of candidate concepts from the home segment of ``new_name``.
+
+        Does not mutate ``_segments``, ``_mat``, or ``_n``. Clears per-insertion cache
+        and per-query diagnostic fields as the first executable statements ([D-58]).
+        """
+        # 1. Clear cache and per-query diagnostic fields as the FIRST executable statements (D-58)
+        self._cached_new_name = None
+        self._cached_new_vec = None
+        self._cached_new_code = None
+        self._cached_new_gray = None
+
+        self._shortlist_called = False
+        self._last_bucket_id = None
+        self._last_bucket_gray_min = None
+        self._last_bucket_gray_max = None
+        self._last_query_code = None
+        self._last_query_gray_rank = None
+        self._last_code_existed_in_bucket = False
+        self._last_inside_bucket_span = False
+        self._last_bucket_size_at_shortlist = 0
+        self._last_bucket_size = 0
+        self._last_shortlist_size = 0
+        self._last_split_occurred = False
+        self._last_merge_occurred = False
+        self._last_query_vec = None
+        self._last_returned_candidates = ()
+        self._last_shortlist_codes = ()
+        self._n_at_query = 0
+        self._query_name = None
+        self._cached_exact_topk_overlap = None
+
+        # 2. Not-set-up check and concept name validation
+        if not self._setup_called or self._embedder is None:
+            raise RuntimeError("setup() must be called before shortlist()")
+
+        _validate_concept_name(new_name)
+
+        # 3. Embed once and validate vector exactly as Strategy 3 does
+        raw_vec = self._embedder.embed(embed_text(new_name))
+
+        if not isinstance(raw_vec, np.ndarray) or raw_vec.ndim != 1:
+            got_type = (
+                type(raw_vec).__name__
+                if not isinstance(raw_vec, np.ndarray)
+                else f"{raw_vec.ndim}-D"
+            )
+            raise ValueError(
+                f"Embedding for {new_name!r} must be 1-D ndarray, got {got_type}"
+            )
+        if not np.all(np.isfinite(raw_vec)):
+            raise ValueError(
+                f"Embedding for {new_name!r} contains non-finite values"
+            )
+
+        norm = float(np.linalg.norm(raw_vec))
+        if norm == 0.0 or not np.isfinite(norm):
+            raise ValueError(
+                f"Zero-norm embedding vector for concept {new_name!r}"
+            )
+
+        if self._dim is not None:
+            if raw_vec.shape[0] != self._dim:
+                raise ValueError(
+                    f"Dimension mismatch for {new_name!r}: expected {self._dim}, got {raw_vec.shape[0]}"
+                )
+        else:
+            dim = int(raw_vec.shape[0])
+            if dim == 0:
+                raise ValueError("Embedding dimension must be >= 1, got 0")
+            self._dim = dim
+            self._hyperplanes = self._draw_hyperplanes(dim)
+            self._mat = np.zeros((16, dim), dtype=np.float32)
+
+        # 4. Normalise to float32, hash in float64, cache vector, code and gray
+        q = (raw_vec / norm).astype(np.float32, copy=False)
+        q = np.ascontiguousarray(q, dtype=np.float32)
+        code, gray = self._hash_vector(q)
+
+        self._cached_new_name = new_name
+        self._cached_new_vec = q
+        self._cached_new_code = code
+        self._cached_new_gray = gray
+
+        self._shortlist_called = True
+        self._last_query_code = code
+        self._last_query_gray_rank = gray
+        self._last_query_vec = q
+        self._n_at_query = self._n
+        self._query_name = new_name
+
+        # 5. Empty index: return empty tuples
+        if self._n == 0:
+            return Shortlist(candidates=(), scores=())
+
+        # 6. Locate home segment in O(log M), score its members, sort by (-score, name)
+        assert self._mat is not None
+        home_idx, inside_span = self._locate_home(gray, new_name, code)
+        seg = self._segments[home_idx]
+
+        self._last_bucket_id = int(home_idx)
+        self._last_bucket_gray_min = int(seg[0].gray)
+        self._last_bucket_gray_max = int(seg[-1].gray)
+        self._last_inside_bucket_span = bool(inside_span)
+        self._last_bucket_size_at_shortlist = len(seg)
+        self._last_bucket_size = len(seg)
+        self._last_code_existed_in_bucket = any(e.code == code for e in seg)
+
+        filtered_entries = [e for e in seg if e.name != new_name]
+        if not filtered_entries:
+            self._last_shortlist_size = 0
+            self._last_returned_candidates = ()
+            self._last_shortlist_codes = ()
+            return Shortlist(candidates=(), scores=())
+
+        rows = [e.row for e in filtered_entries]
+        sub_mat = self._mat[rows]
+        raw_scores = sub_mat @ q
+
+        paired = [
+            (float(raw_scores[i]), filtered_entries[i].name, filtered_entries[i].code)
+            for i in range(len(filtered_entries))
+        ]
+        paired.sort(key=lambda item: (-item[0], item[1]))
+
+        candidates = tuple(name for _, name, _ in paired)
+        scores = tuple(score for score, _, _ in paired)
+        shortlist_codes = tuple(c_code for _, _, c_code in paired)
+
+        self._last_shortlist_size = len(candidates)
+        self._last_returned_candidates = candidates
+        self._last_shortlist_codes = shortlist_codes
+
+        return Shortlist(candidates=candidates, scores=scores)
+
+    def on_inserted(
+        self, new_name: str, edges: tuple[tuple[str, str], ...]
+    ) -> None:
+        """Incrementally insert ``new_name`` into its home segment and locally split on overflow.
+
+        Reuses the cached embedding and hash from ``shortlist()``; makes zero embedder calls.
+        The ``edges`` parameter is accepted and ignored because partitioning depends only on
+        concept embeddings.
+
+        Complexity
+        ----------
+        - Hashing: ``O(n_bits * d)`` performed in ``shortlist()`` and reused from cache.
+        - Home lookup (``_locate_home``): ``O(log M)`` binary search over ``M`` segments.
+        - Segment insertion and midpoint bisection: ``O(s_max)``.
+        - Segment list slice assignment on split: ``O(M)`` C-level pointer shift, which is bounded.
+        - Matrix row write: ``O(d)`` (capacity ``max(16, 2 * n)`` prevents reallocation on the
+          first timed insert after ``setup()``, and doubling growth gives amortised ``O(d)``).
+        """
+        if (
+            self._cached_new_name is None
+            or self._cached_new_name != new_name
+            or self._cached_new_vec is None
+            or self._cached_new_code is None
+            or self._cached_new_gray is None
+        ):
+            raise RuntimeError(
+                f"on_inserted({new_name!r}) called without matching shortlist() call"
+            )
+        if new_name in self._name_to_idx:
+            raise ValueError(
+                f"Concept {new_name!r} is already present in the index"
+            )
+
+        vec = self._cached_new_vec
+        code = self._cached_new_code
+        gray = self._cached_new_gray
+
+        self._cached_new_name = None
+        self._cached_new_vec = None
+        self._cached_new_code = None
+        self._cached_new_gray = None
+
+        assert self._dim is not None
+
+        if self._mat is None:
+            self._mat = np.zeros((16, self._dim), dtype=np.float32)
+        elif self._n >= self._mat.shape[0]:
+            new_capacity = self._mat.shape[0] * 2
+            new_mat = np.zeros((new_capacity, self._dim), dtype=np.float32)
+            new_mat[: self._n] = self._mat[: self._n]
+            self._mat = new_mat
+
+        row = self._n
+        self._mat[row] = vec
+        self._names.append(new_name)
+        self._name_to_idx[new_name] = row
+        self._n += 1
+
+        entry = BucketEntry(gray=gray, name=new_name, code=code, row=row)
+        self._entry_by_name[new_name] = entry
+        self._insert_entry(entry)
+
+    def _compute_exact_topk_overlap(self) -> Optional[float]:
+        """Compute fraction of exact top-m cosine neighbours contained in the returned shortlist.
+
+        ``m = min(self.s_max, n_at_query)`` (excluding ``_query_name``, ties broken by name).
+        Returns ``1.0`` when ``n_at_query == 0``, and ``None`` before any ``shortlist()`` call.
+        """
+        if not self._shortlist_called or self._last_query_vec is None:
+            return None
+        if self._n_at_query == 0:
+            return 1.0
+
+        assert self._mat is not None
+        cosines = self._mat[: self._n_at_query] @ self._last_query_vec
+        names_at_query = self._names[: self._n_at_query]
+        valid_items = [
+            (float(cosines[i]), names_at_query[i])
+            for i in range(self._n_at_query)
+            if names_at_query[i] != self._query_name
+        ]
+        valid_items.sort(key=lambda item: (-item[0], item[1]))
+        m = min(self.s_max, len(valid_items))
+        if m == 0:
+            return 1.0
+
+        exact_set = {name for _, name in valid_items[:m]}
+        matched = sum(
+            1 for cand in self._last_returned_candidates if cand in exact_set
+        )
+        return float(matched / m)
+
+    def config(self) -> dict[str, Any]:
+        """Return strategy configuration hyperparameters as plain Python ``int`` values."""
+        return {
+            "s_min": int(self.s_min),
+            "s_max": int(self.s_max),
+            "n_bits": int(self.n_bits),
+            "seed": int(self.seed),
+        }
+
+    def diagnostics(self) -> dict[str, Any]:
+        """Return JSON-serialisable operational diagnostics for the most recent trial.
+
+        Computed outside the timed windows (``shortlist_s`` and ``update_s``).
+        Note that ``exact_topk_overlap`` measures partition loss plus embedding loss
+        together (relative to exact top-m cosine over the index), whereas
+        ``min_hamming_to_shortlist`` shows how close in Hamming space the
+        Gray-interval home segment is to the query code.
+        """
+        if self._cached_exact_topk_overlap is None and self._shortlist_called:
+            self._cached_exact_topk_overlap = self._compute_exact_topk_overlap()
+
+        num_segments = len(self._segments)
+        if num_segments > 0:
+            seg_sizes = [len(s) for s in self._segments]
+            min_seg_size = int(min(seg_sizes))
+            max_seg_size = int(max(seg_sizes))
+            mean_seg_size = float(sum(seg_sizes) / num_segments)
+        else:
+            min_seg_size = 0
+            max_seg_size = 0
+            mean_seg_size = 0.0
+
+        if (
+            self._last_query_code is not None
+            and len(self._last_shortlist_codes) > 0
+        ):
+            min_hamming: Optional[int] = int(
+                min(
+                    self._hamming(self._last_query_code, c_code)
+                    for c_code in self._last_shortlist_codes
+                )
+            )
+        else:
+            min_hamming = None
+
+        return {
+            "bucket_id": (
+                int(self._last_bucket_id)
+                if self._last_bucket_id is not None
+                else None
+            ),
+            "bucket_gray_min": (
+                int(self._last_bucket_gray_min)
+                if self._last_bucket_gray_min is not None
+                else None
+            ),
+            "bucket_gray_max": (
+                int(self._last_bucket_gray_max)
+                if self._last_bucket_gray_max is not None
+                else None
+            ),
+            "query_code": (
+                int(self._last_query_code)
+                if self._last_query_code is not None
+                else None
+            ),
+            "query_gray_rank": (
+                int(self._last_query_gray_rank)
+                if self._last_query_gray_rank is not None
+                else None
+            ),
+            "code_existed_in_bucket": bool(self._last_code_existed_in_bucket),
+            "inside_bucket_span": bool(self._last_inside_bucket_span),
+            "bucket_size_at_shortlist": int(self._last_bucket_size_at_shortlist),
+            "bucket_size": int(self._last_bucket_size),
+            "shortlist_size": int(self._last_shortlist_size),
+            "split_occurred": bool(self._last_split_occurred),
+            "merge_occurred": bool(self._last_merge_occurred),
+            "num_segments": int(num_segments),
+            "min_segment_size": int(min_seg_size),
+            "max_segment_size": int(max_seg_size),
+            "mean_segment_size": float(mean_seg_size),
+            "exact_topk_overlap": (
+                float(self._cached_exact_topk_overlap)
+                if self._cached_exact_topk_overlap is not None
+                else None
+            ),
+            "min_hamming_to_shortlist": min_hamming,
+        }
```

### 8.3 `diff -u /dev/null tests/test_bounded_bucket_strategy.py`

```diff
--- /dev/null	2026-10-11 15:44:13.063585755 +0800
+++ tests/test_bounded_bucket_strategy.py	2026-10-11 21:19:54.845269257 +0800
@@ -0,0 +1,1442 @@
+"""tests/test_bounded_bucket_strategy.py — STRAT-004
+====================================================
+Conformance, invariant, determinism, lifecycle, diagnostics, and mutation-killing
+tests for BoundedBucketStrategy (Strategy 4).
+"""
+
+from __future__ import annotations
+
+import json
+from typing import Any, Callable, Sequence
+
+import numpy as np
+import pytest
+
+from graph_insertion.decision import PairwiseDecisionStep
+from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
+from graph_insertion.graph_representation import ConceptGraph, embed_text
+from graph_insertion.harness import (
+    HarnessConfig,
+    SyntheticNameSource,
+    run_sweep_experiment,
+)
+from graph_insertion.llm import FakeLLMClient, MeteredLLMClient
+from graph_insertion.strategies.bounded_bucket import (
+    DEFAULT_N_BITS,
+    DEFAULT_S_MAX,
+    DEFAULT_S_MIN,
+    DEFAULT_SEED,
+    BoundedBucketStrategy,
+    BucketEntry,
+)
+from graph_insertion.strategy import (
+    NarrowingStrategy,
+    Shortlist,
+    candidate_upper_bound,
+    insert_node,
+)
+from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine
+from tests.test_strategy_interface import FakeDecisionStep, StrategyConformanceSuite
+
+
+def _assert_no_numpy_types(obj: Any) -> None:
+    """Assert recursively that no NumPy scalar or array types appear in a structure."""
+    if isinstance(obj, (np.generic, np.ndarray)):
+        raise AssertionError(f"Found numpy type {type(obj)} in {obj!r}")
+    if isinstance(obj, dict):
+        for k, v in obj.items():
+            _assert_no_numpy_types(k)
+            _assert_no_numpy_types(v)
+    elif isinstance(obj, (list, tuple)):
+        for item in obj:
+            _assert_no_numpy_types(item)
+
+
+def _assert_partition_invariants(
+    strat: BoundedBucketStrategy, expected_nodes: set[str]
+) -> None:
+    """Verify size bounds, global (gray, name) strict ordering, and exact node coverage."""
+    n = len(expected_nodes)
+    assert strat._n == n
+    segs = strat._segments
+
+    if n == 0:
+        assert segs == []
+        return
+
+    if n < strat.s_min:
+        assert len(segs) == 1
+        assert len(segs[0]) == n
+    else:
+        assert len(segs) >= 1
+        for seg in segs:
+            assert strat.s_min <= len(seg) <= strat.s_max
+
+    all_entries: list[BucketEntry] = []
+    for seg in segs:
+        for i in range(len(seg) - 1):
+            assert seg[i].sort_key() < seg[i + 1].sort_key()
+        all_entries.extend(seg)
+
+    for i in range(len(all_entries) - 1):
+        assert all_entries[i].sort_key() < all_entries[i + 1].sort_key()
+
+    seen_names = [e.name for e in all_entries]
+    assert len(seen_names) == n
+    assert set(seen_names) == expected_nodes
+
+
+# ===========================================================================
+# 1. StrategyConformanceSuite Subclasses
+# ===========================================================================
+
+
+class TestBoundedBucketDefaultConformance(StrategyConformanceSuite):
+    """Proves BoundedBucketStrategy satisfies the StrategyConformanceSuite contract at defaults."""
+
+    uses_embeddings: bool = True
+
+    @pytest.fixture
+    def strategy_factory(
+        self,
+    ) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
+        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
+            strat = BoundedBucketStrategy()
+            strat.setup(graph, embedder)
+            return strat
+
+        return _factory
+
+
+class TestBoundedBucketSmallParamsConformance(StrategyConformanceSuite):
+    """Proves BoundedBucketStrategy satisfies the StrategyConformanceSuite contract with small bounds."""
+
+    uses_embeddings: bool = True
+
+    @pytest.fixture
+    def strategy_factory(
+        self,
+    ) -> Callable[[ConceptGraph, Embedder], NarrowingStrategy]:
+        def _factory(graph: ConceptGraph, embedder: Embedder) -> NarrowingStrategy:
+            strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=6, seed=7)
+            strat.setup(graph, embedder)
+            return strat
+
+        return _factory
+
+
+# ===========================================================================
+# 2. Constructor Parameter Validation
+# ===========================================================================
+
+
+class TestInitValidation:
+    """Proves __init__ rejects bools, non-ints, s_min < 2, s_max < 2 * s_min, and out-of-range n_bits."""
+
+    @pytest.mark.parametrize("bad_val", [True, False, 2.5, "5", None, [5]])
+    def test_non_int_or_bool_rejected_for_all_params(self, bad_val: Any) -> None:
+        """Proves each of s_min, s_max, n_bits, and seed rejects bool and non-int values."""
+        with pytest.raises(ValueError, match="s_min must be an integer"):
+            BoundedBucketStrategy(s_min=bad_val, s_max=10)
+        with pytest.raises(ValueError, match="s_max must be an integer"):
+            BoundedBucketStrategy(s_min=5, s_max=bad_val)
+        with pytest.raises(ValueError, match="n_bits must be an integer"):
+            BoundedBucketStrategy(n_bits=bad_val)
+        with pytest.raises(ValueError, match="seed must be an integer"):
+            BoundedBucketStrategy(seed=bad_val)
+
+    @pytest.mark.parametrize("bad_s_min", [1, 0, -1, -10])
+    def test_s_min_below_two_rejected(self, bad_s_min: int) -> None:
+        """Proves s_min < 2 raises ValueError even when s_max >= 2 * s_min."""
+        with pytest.raises(ValueError, match="s_min must be >= 2"):
+            BoundedBucketStrategy(s_min=bad_s_min, s_max=10)
+
+    @pytest.mark.parametrize(
+        "s_min,bad_s_max",
+        [(2, 3), (2, 2), (3, 5), (5, 9), (5, 5), (10, 19)],
+    )
+    def test_s_max_below_two_s_min_rejected(
+        self, s_min: int, bad_s_max: int
+    ) -> None:
+        """Proves s_max < 2 * s_min raises ValueError."""
+        with pytest.raises(ValueError, match="s_max must be >= 2 \\* s_min"):
+            BoundedBucketStrategy(s_min=s_min, s_max=bad_s_max)
+
+    @pytest.mark.parametrize("bad_n_bits", [0, -1, 63, 64, 100])
+    def test_n_bits_out_of_range_rejected(self, bad_n_bits: int) -> None:
+        """Proves n_bits outside [1, 62] raises ValueError."""
+        with pytest.raises(ValueError, match="n_bits must be between 1 and 62"):
+            BoundedBucketStrategy(n_bits=bad_n_bits)
+
+    def test_valid_boundary_parameters_accepted(self) -> None:
+        """Proves boundary settings (s_min=2, s_max=4, n_bits=1 and n_bits=62) succeed."""
+        s1 = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=1, seed=-7)
+        assert (s1.s_min, s1.s_max, s1.n_bits, s1.seed) == (2, 4, 1, -7)
+        s2 = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=62, seed=0)
+        assert s2.n_bits == 62
+
+
+# ===========================================================================
+# 3. Strategy Name, uses_embeddings, and config()
+# ===========================================================================
+
+
+class TestInterfaceAndConfig:
+    """Proves permanent strategy name, uses_embeddings class attribute, and config() schema."""
+
+    def test_name_uses_embeddings_and_config_keys(self) -> None:
+        """Proves BoundedBucketStrategy exposes permanent name, uses_embeddings=True, and 4 int config keys."""
+        assert BoundedBucketStrategy.name == "bounded_bucket"
+        assert BoundedBucketStrategy.uses_embeddings is True
+
+        strat = BoundedBucketStrategy()
+        assert strat.name == "bounded_bucket"
+        assert strat.uses_embeddings is True
+        assert (strat.s_min, strat.s_max, strat.n_bits, strat.seed) == (
+            DEFAULT_S_MIN,
+            DEFAULT_S_MAX,
+            DEFAULT_N_BITS,
+            DEFAULT_SEED,
+        )
+
+        cfg = strat.config()
+        assert cfg == {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
+        assert set(cfg.keys()) == {"s_min", "s_max", "n_bits", "seed"}
+        for k, v in cfg.items():
+            assert isinstance(v, int) and not isinstance(v, bool), f"Key {k} not plain int"
+        _assert_no_numpy_types(cfg)
+        assert json.loads(json.dumps(cfg)) == cfg
+
+
+# ===========================================================================
+# 4. max_candidates and Call Bounds Over D-35 Sweep and Accuracy Mode
+# ===========================================================================
+
+
+class TestMaxCandidatesAndBudgets:
+    """Proves max_candidates formula and planned-call upper bounds across sweep and accuracy matrices."""
+
+    def test_max_candidates_values_and_negative_clamping(self) -> None:
+        """Proves max_candidates returns max(0, min(s_max, n_existing)) before setup()."""
+        strat = BoundedBucketStrategy(s_min=5, s_max=10)
+        expected = {
+            -5: 0,
+            -1: 0,
+            0: 0,
+            3: 3,
+            5: 5,
+            10: 10,
+            50: 10,
+            2000: 10,
+        }
+        for n_val, exp in expected.items():
+            assert strat.max_candidates(n_val) == exp
+            assert candidate_upper_bound(strat, n_val) == max(0, min(n_val, exp))
+
+    def test_d35_sweep_and_accuracy_planned_call_bounds(self) -> None:
+        """Proves D-35 sweep bounds (600, 300, 1200) and accuracy bounds (590, 295, 1180)."""
+        sweep_sizes = (50, 100, 200, 500, 1000, 2000)
+        sweep_trials = 10
+        accuracy_n_existing = [28] * 29 + [140] * 30
+
+        cases = [
+            (5, 10, 600, 590),
+            (2, 5, 300, 295),
+            (10, 20, 1200, 1180),
+        ]
+        for s_min, s_max, exp_sweep, exp_acc in cases:
+            strat = BoundedBucketStrategy(s_min=s_min, s_max=s_max)
+            sweep_bound = sum(
+                candidate_upper_bound(strat, sz) * sweep_trials
+                for sz in sweep_sizes
+            )
+            acc_bound = sum(
+                candidate_upper_bound(strat, n_ex)
+                for n_ex in accuracy_n_existing
+            )
+            assert sweep_bound == exp_sweep
+            assert acc_bound == exp_acc
+
+
+# ===========================================================================
+# 5. Partition Size Invariants, Global Ordering, and Node Coverage
+# ===========================================================================
+
+
+class TestPartitionInvariants:
+    """Proves size bounds, strictly increasing (gray, name) order, and exact coverage across sizes."""
+
+    def test_invariants_after_batch_setup_for_n_0_to_60(self) -> None:
+        """Proves batch setup() satisfies partition invariants for every n in 0..60."""
+        embedder = FakeEmbedder(dim=16, seed=42)
+        for n in range(0, 61):
+            graph = ConceptGraph()
+            names = {f"node_{i:03d}" for i in range(n)}
+            for name in sorted(names):
+                graph.add_node(name)
+            strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=11)
+            strat.setup(graph, embedder)
+            _assert_partition_invariants(strat, names)
+
+    @pytest.mark.parametrize("n", [100, 500, 2000])
+    def test_invariants_after_batch_setup_large_n(self, n: int) -> None:
+        """Proves batch setup() satisfies partition invariants at n in {100, 500, 2000}."""
+        embedder = FakeEmbedder(dim=32, seed=99)
+        graph = ConceptGraph()
+        names = {f"concept_{i:04d}" for i in range(n)}
+        for name in sorted(names):
+            graph.add_node(name)
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=42)
+        strat.setup(graph, embedder)
+        _assert_partition_invariants(strat, names)
+
+    def test_invariants_across_65_sequential_inserts_from_empty(self) -> None:
+        """Proves partition invariants hold after every single insert from n=0 to n=65."""
+        embedder = FakeEmbedder(dim=16, seed=77)
+        meter = MeteredEmbedder(embedder)
+        decision = FakeDecisionStep(make_edge=False)
+        graph = ConceptGraph()
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=8, seed=42)
+        strat.setup(graph, meter)
+
+        expected_nodes: set[str] = set()
+        _assert_partition_invariants(strat, expected_nodes)
+
+        for i in range(65):
+            new_name = f"seq_node_{i:03d}"
+            insert_node(
+                strat, graph, decision, new_name, metered_embedder=meter
+            )
+            expected_nodes.add(new_name)
+            _assert_partition_invariants(strat, expected_nodes)
+
+
+# ===========================================================================
+# 6. Determinism and Insertion-Order Invariance
+# ===========================================================================
+
+
+class TestDeterminism:
+    """Proves two builds on graphs with different node insertion orders produce identical state."""
+
+    def test_node_addition_order_invariance(self) -> None:
+        """Proves hyperplanes, segments, shortlists, and diagnostics are identical regardless of graph node order."""
+        names = [f"concept_{i:03d}" for i in range(35)]
+        g_forward = ConceptGraph()
+        for name in names:
+            g_forward.add_node(name)
+
+        g_reverse = ConceptGraph()
+        for name in reversed(names):
+            g_reverse.add_node(name)
+
+        emb1 = FakeEmbedder(dim=16, seed=42)
+        emb2 = FakeEmbedder(dim=16, seed=42)
+
+        s1 = BoundedBucketStrategy(s_min=4, s_max=8, n_bits=10, seed=42)
+        s2 = BoundedBucketStrategy(s_min=4, s_max=8, n_bits=10, seed=42)
+        s1.setup(g_forward, emb1)
+        s2.setup(g_reverse, emb2)
+
+        assert s1._hyperplanes is not None and s2._hyperplanes is not None
+        assert np.array_equal(s1._hyperplanes, s2._hyperplanes)
+        assert s1._names == s2._names
+        assert s1._segments == s2._segments
+
+        for q in ["probe_alpha", "probe_beta", "probe_gamma"]:
+            sl1 = s1.shortlist(q)
+            sl2 = s2.shortlist(q)
+            assert sl1 == sl2
+            assert s1.diagnostics() == s2.diagnostics()
+
+
+# ===========================================================================
+# 7. Hyperplanes Drawing, Lazy Initialisation, and Validation Rollback
+# ===========================================================================
+
+
+class TestHyperplanes:
+    """Proves hyperplane shape, dtype, unit row norms, regeneration on second setup, and lazy init."""
+
+    def test_hyperplane_properties_and_regeneration(self) -> None:
+        """Proves _hyperplanes has shape (n_bits, dim), float64, unit rows, and regenerates identically."""
+        graph = ConceptGraph()
+        graph.add_node("n0")
+        graph.add_node("n1")
+        embedder = FakeEmbedder(dim=24, seed=42)
+
+        strat = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=12, seed=123)
+        strat.setup(graph, embedder)
+
+        H1 = strat._hyperplanes
+        assert H1 is not None
+        assert H1.shape == (12, 24)
+        assert H1.dtype == np.float64
+        row_norms = np.linalg.norm(H1, axis=1)
+        assert np.allclose(row_norms, 1.0, atol=1e-12)
+
+        # Mutate copy and re-run setup() to verify identical regeneration
+        H1_copy = H1.copy()
+        strat.setup(graph, embedder)
+        assert strat._hyperplanes is not None
+        assert np.array_equal(strat._hyperplanes, H1_copy)
+
+    def test_lazy_hyperplanes_match_non_empty_setup_and_rollback_on_bad_first_query(
+        self,
+    ) -> None:
+        """Proves empty setup draws identical hyperplanes on first valid shortlist and commits nothing on failure."""
+        embedder = FakeEmbedder(dim=16, seed=42)
+        g_nonempty = ConceptGraph()
+        g_nonempty.add_node("a")
+        s_nonempty = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=10, seed=99)
+        s_nonempty.setup(g_nonempty, embedder)
+
+        s_lazy = BoundedBucketStrategy(s_min=2, s_max=5, n_bits=10, seed=99)
+        s_lazy.setup(ConceptGraph(), embedder)
+        assert s_lazy._dim is None
+        assert s_lazy._hyperplanes is None
+        assert s_lazy._mat is None
+
+        # Failing first shortlist on empty index must not commit _dim, _hyperplanes, or _mat
+        bad_emb = ControllableEmbedder(
+            {"bad_zero": np.zeros(16, dtype=np.float32)}, dim=16
+        )
+        s_fail_lazy = BoundedBucketStrategy(
+            s_min=2, s_max=5, n_bits=10, seed=99
+        )
+        s_fail_lazy.setup(ConceptGraph(), bad_emb)
+        with pytest.raises(ValueError, match="Zero-norm"):
+            s_fail_lazy.shortlist("bad_zero")
+        assert s_fail_lazy._dim is None
+        assert s_fail_lazy._hyperplanes is None
+        assert s_fail_lazy._mat is None
+
+        # Valid first shortlist on empty index initialises identical hyperplanes
+        sl = s_lazy.shortlist("a")
+        assert sl == Shortlist(candidates=(), scores=())
+        assert s_lazy._dim == 16
+        assert s_lazy._hyperplanes is not None
+        assert s_nonempty._hyperplanes is not None
+        assert np.array_equal(s_lazy._hyperplanes, s_nonempty._hyperplanes)
+
+
+# ===========================================================================
+# 8. Hash Functions, Gray Rank, MSB Packing, Exact Zero Dot, Float64 Projection
+# ===========================================================================
+
+
+class TestHashingAndGrayOrder:
+    """Proves _gray_rank bijection, MSB-first bit packing, dot==0.0 -> bit 1, and float64 projection."""
+
+    def test_gray_rank_all_4096_12bit_codes(self) -> None:
+        """Proves _gray_rank is the inverse of g ^ (g >> 1) for all 4,096 12-bit codes and adjacent ranks differ by 1 bit."""
+        strat = BoundedBucketStrategy(n_bits=12)
+        code_for_rank: dict[int, int] = {}
+        for code in range(4096):
+            g = strat._gray_rank(code)
+            assert 0 <= g < 4096
+            # Reference forward Gray code: g ^ (g >> 1) must equal code
+            assert (g ^ (g >> 1)) == code
+            code_for_rank[g] = code
+
+        assert len(code_for_rank) == 4096
+        for g in range(4095):
+            assert strat._hamming(code_for_rank[g], code_for_rank[g + 1]) == 1
+
+    def test_msb_first_packing_and_exact_zero_dot_product(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves hyperplane 0 is MSB and dot == 0.0 yields bit 1 in both batch and single-vector paths."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=3, seed=42)
+        # 3 axis-aligned hyperplanes in R^4: e_0, e_1, e_2
+        fixed_H = np.array(
+            [
+                [1.0, 0.0, 0.0, 0.0],
+                [0.0, 1.0, 0.0, 0.0],
+                [0.0, 0.0, 1.0, 0.0],
+            ],
+            dtype=np.float64,
+        )
+        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: fixed_H)
+
+        # n_pos0_neg12 has dots (+1, -1, -1) -> bits (1, 0, 0) -> MSB code = 4 (not LSB 1)
+        # n_zero_all has vector (0, 0, 0, 1) -> exact 0.0 dot with all 3 planes -> bits (1, 1, 1) -> code = 7
+        vectors = {
+            "n_msb": np.array([1.0, -1.0, -1.0, 0.0], dtype=np.float32),
+            "n_zero": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
+            "q_zero": np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
+            "q_lsb": np.array([-1.0, -1.0, 1.0, 0.0], dtype=np.float32),
+        }
+        emb = ControllableEmbedder(vectors, dim=4)
+        graph = ConceptGraph()
+        graph.add_node("n_msb")
+        graph.add_node("n_zero")
+        strat.setup(graph, emb)
+
+        assert strat._entry_by_name["n_msb"].code == 0b100
+        assert strat._entry_by_name["n_zero"].code == 0b111
+
+        strat.shortlist("q_zero")
+        assert strat.diagnostics()["query_code"] == 0b111
+
+        strat.shortlist("q_lsb")
+        assert strat.diagnostics()["query_code"] == 0b001
+
+    def test_float64_projection_distinguishes_sub_float32_cancellation(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves projection is computed in float64 rather than float32 (kills M-29)."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=1, seed=42)
+        # In float64, -0.5 - 1e-12 is strictly less than -0.5; in float32 it rounds to -0.5.
+        raw_h = np.array([[0.5, -0.5, 0.5, -0.5 - 1e-12]], dtype=np.float64)
+        raw_h /= np.linalg.norm(raw_h, axis=1, keepdims=True)
+        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: raw_h)
+
+        # v = [0.5, 0.5, 0.5, 0.5] is exact in both float32 and float64.
+        # float64 dot is negative (< 0.0 -> bit 0); float32 dot cancels to 0.0 (>= 0.0 -> bit 1).
+        v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
+        emb = ControllableEmbedder({"node_a": v, "probe_a": v}, dim=4)
+        graph = ConceptGraph()
+        graph.add_node("node_a")
+        strat.setup(graph, emb)
+
+        assert strat._entry_by_name["node_a"].code == 0
+        strat.shortlist("probe_a")
+        assert strat.diagnostics()["query_code"] == 0
+
+
+# ===========================================================================
+# 9. Forced Split and Duplicate Vectors
+# ===========================================================================
+
+
+class TestForcedSplitAndDuplicates:
+    """Proves midpoint bisection on s_max + 1 items and deterministic tie-splitting on duplicate vectors."""
+
+    def test_forced_split_at_s_max_plus_one(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves inserting the (s_max + 1)-th node into a segment splits it into len // 2 and len - len // 2."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=2, seed=42)
+        fixed_H = np.array(
+            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float64
+        )
+        monkeypatch.setattr(strat, "_draw_hyperplanes", lambda dim: fixed_H)
+
+        same_vec = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
+        names = [f"c_{i:02d}" for i in range(5)]
+        vecs = {name: same_vec for name in names}
+        vecs["c_05"] = same_vec
+        vecs["c_06"] = same_vec
+
+        emb = ControllableEmbedder(vecs, dim=4)
+        meter = MeteredEmbedder(emb)
+        graph = ConceptGraph()
+        for name in names:
+            graph.add_node(name)
+
+        strat.setup(graph, meter)
+        assert len(strat._segments) == 1
+        assert len(strat._segments[0]) == 5
+
+        # Inserting the 6th item reaches exactly s_max=6: must NOT split (kills M-15)
+        res5 = insert_node(
+            strat,
+            graph,
+            FakeDecisionStep(make_edge=False),
+            "c_05",
+            metered_embedder=meter,
+        )
+        diag5 = res5.metrics.extra
+        assert diag5["split_occurred"] is False
+        assert diag5["num_segments"] == 1
+        assert [len(s) for s in strat._segments] == [6]
+        assert diag5["bucket_size"] == 6
+
+        # Inserting the 7th item reaches s_max + 1 = 7: MUST split into (3, 4)
+        res = insert_node(
+            strat,
+            graph,
+            FakeDecisionStep(make_edge=False),
+            "c_06",
+            metered_embedder=meter,
+        )
+        diag = res.metrics.extra
+        assert diag["split_occurred"] is True
+        assert diag["num_segments"] == 2
+        assert [len(s) for s in strat._segments] == [3, 4]
+        assert [e.name for e in strat._segments[0]] == ["c_00", "c_01", "c_02"]
+        assert [e.name for e in strat._segments[1]] == [
+            "c_03",
+            "c_04",
+            "c_05",
+            "c_06",
+        ]
+        # c_06 landed in the second half of size 4
+        assert diag["bucket_size"] == 4
+
+    def test_duplicate_vectors_in_setup_and_insert_split_by_name(self) -> None:
+        """Proves 2 * s_max + 3 identical vectors terminate in setup() and insert_node() and split by name."""
+        s_min, s_max = 3, 6
+        count = 2 * s_max + 3  # 15
+        same_vec = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
+        names = [f"dup_{i:02d}" for i in range(count)]
+        vecs = {name: same_vec for name in names}
+        vecs["dup_99"] = same_vec
+
+        emb = ControllableEmbedder(vecs, dim=4)
+        meter = MeteredEmbedder(emb)
+        graph = ConceptGraph()
+        for name in names:
+            graph.add_node(name)
+
+        strat = BoundedBucketStrategy(s_min=s_min, s_max=s_max, n_bits=4, seed=42)
+        strat.setup(graph, meter)
+        _assert_partition_invariants(strat, set(names))
+        # 15 items bisected recursively: 15 -> (7, 8) -> (3, 4, 4, 4)
+        assert [len(s) for s in strat._segments] == [3, 4, 4, 4]
+
+        insert_node(
+            strat,
+            graph,
+            FakeDecisionStep(make_edge=False),
+            "dup_99",
+            metered_embedder=meter,
+        )
+        _assert_partition_invariants(strat, set(names) | {"dup_99"})
+
+
+# ===========================================================================
+# 10 & 11. Forced Merge, Gap Insertion, and 4-Component Neighbour Rule
+# ===========================================================================
+
+
+class TestMergeAndNeighbourRule:
+    """Proves forced merge in setup(), gap merge in on_inserted(), and each component of _choose_neighbour."""
+
+    @staticmethod
+    def _vec_for_code(code: int, n_bits: int) -> np.ndarray:
+        """Construct a vector in R^n_bits whose sign bits with identity hyperplanes equal code."""
+        v = np.zeros(n_bits, dtype=np.float32)
+        for r in range(n_bits):
+            bit = (code >> (n_bits - 1 - r)) & 1
+            v[r] = 1.0 if bit == 1 else -1.0
+        return v
+
+    def test_neighbour_rule_component_1_hamming_decisive_over_gray_gap(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves smaller Hamming distance wins even when the other neighbour has a smaller Gray-rank gap (kills M-25)."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+
+        # In 4-bit Gray rank:
+        # Left segment at gray=1 (code=0b0001=1), 3 nodes
+        # Middle undersized bucket at gray=4 (code=0b0110=6), 1 node:
+        #   - to Left (gray=1, code=1): hamming(1, 6) = 3, gray_gap = 4 - 1 = 3
+        #   - to Right (gray=8, code=0b1100=12): hamming(6, 12) = 2, gray_gap = 8 - 4 = 4
+        # Hamming (2 < 3) chooses Right even though Left has smaller gray_gap (3 < 4)!
+        vecs: dict[str, np.ndarray] = {}
+        for i in range(3):
+            vecs[f"left_{i}"] = self._vec_for_code(0b0001, 4)
+        vecs["mid_0"] = self._vec_for_code(0b0110, 4)
+        for i in range(3):
+            vecs[f"right_{i}"] = self._vec_for_code(0b1100, 4)
+        # Also test a gap query at gray=4 (code=0b0110) on a 2-segment index (Left and Right only)
+        vecs["gap_query"] = self._vec_for_code(0b0110, 4)
+
+        emb = ControllableEmbedder(vecs, dim=4)
+        g_merge = ConceptGraph()
+        for name in ["left_0", "left_1", "left_2", "mid_0", "right_0", "right_1", "right_2"]:
+            g_merge.add_node(name)
+
+        strat.setup(g_merge, emb)
+        assert len(strat._segments) == 2
+        # mid_0 must have merged into Right (segment 1), leaving Left of size 3 and Right of size 4
+        assert [e.name for e in strat._segments[0]] == ["left_0", "left_1", "left_2"]
+        assert [e.name for e in strat._segments[1]] == [
+            "mid_0",
+            "right_0",
+            "right_1",
+            "right_2",
+        ]
+
+        # Now test gap query on Left + Right without mid_0
+        g_gap = ConceptGraph()
+        for name in ["left_0", "left_1", "left_2", "right_0", "right_1", "right_2"]:
+            g_gap.add_node(name)
+        strat.setup(g_gap, emb)
+        sl = strat.shortlist("gap_query")
+        assert set(sl.candidates) == {"right_0", "right_1", "right_2"}
+        diag_before = strat.diagnostics()
+        assert diag_before["bucket_id"] == 1
+        assert diag_before["inside_bucket_span"] is False
+        assert diag_before["merge_occurred"] is False
+
+        strat.on_inserted("gap_query", ())
+        diag_after = strat.diagnostics()
+        assert diag_after["merge_occurred"] is True
+        assert diag_after["split_occurred"] is False
+        assert "gap_query" in [e.name for e in strat._segments[1]]
+
+    def test_neighbour_rule_component_2_gray_gap_decisive_when_hamming_tied(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves smaller Gray-rank gap wins when Hamming distances are equal, even if the other neighbour is smaller."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+
+        # Middle at gray=3 (code=0b0010=2):
+        # Left at gray=0 (code=0b0000=0): hamming(0, 2) = 1, gray_gap = 3 - 0 = 3, len = 3
+        # Right at gray=4 (code=0b0110=6): hamming(2, 6) = 1, gray_gap = 4 - 3 = 1, len = 4
+        # Both have Hamming 1; Right has smaller gray_gap (1 < 3) despite larger size (4 > 3).
+        vecs: dict[str, np.ndarray] = {}
+        for i in range(3):
+            vecs[f"left_{i}"] = self._vec_for_code(0b0000, 4)
+        vecs["mid_0"] = self._vec_for_code(0b0010, 4)
+        for i in range(4):
+            vecs[f"right_{i}"] = self._vec_for_code(0b0110, 4)
+        vecs["gap_q"] = self._vec_for_code(0b0010, 4)
+
+        emb = ControllableEmbedder(vecs, dim=4)
+        g_merge = ConceptGraph()
+        for k in vecs:
+            if k != "gap_q":
+                g_merge.add_node(k)
+        strat.setup(g_merge, emb)
+        assert [len(s) for s in strat._segments] == [3, 5]
+        assert "mid_0" in [e.name for e in strat._segments[1]]
+
+        g_gap = ConceptGraph()
+        for k in vecs:
+            if k not in {"mid_0", "gap_q"}:
+                g_gap.add_node(k)
+        strat.setup(g_gap, emb)
+        sl = strat.shortlist("gap_q")
+        assert set(sl.candidates) == {"right_0", "right_1", "right_2", "right_3"}
+
+    def test_neighbour_rule_component_3_size_decisive_and_component_4_left_tiebreak(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves smaller neighbour size wins on Hamming+Gray tie (kills M-26), and left wins on full tie (kills M-19)."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+
+        # Middle at gray=2 (code=0b0011=3):
+        # Left at gray=1 (code=0b0001=1): hamming(1, 3) = 1, gray_gap = 1
+        # Right at gray=3 (code=0b0010=2): hamming(3, 2) = 1, gray_gap = 1
+        # Case A: len(Left)=4, len(Right)=3 -> Right wins by smaller size (3 < 4)
+        vecs_a: dict[str, np.ndarray] = {}
+        for i in range(4):
+            vecs_a[f"left_{i}"] = self._vec_for_code(0b0001, 4)
+        vecs_a["mid_0"] = self._vec_for_code(0b0011, 4)
+        for i in range(3):
+            vecs_a[f"right_{i}"] = self._vec_for_code(0b0010, 4)
+        vecs_a["gap_q"] = self._vec_for_code(0b0011, 4)
+
+        emb_a = ControllableEmbedder(vecs_a, dim=4)
+        g_a = ConceptGraph()
+        for k in vecs_a:
+            if k != "gap_q":
+                g_a.add_node(k)
+        strat.setup(g_a, emb_a)
+        assert [len(s) for s in strat._segments] == [4, 4]
+        assert "mid_0" in [e.name for e in strat._segments[1]]
+
+        g_a_gap = ConceptGraph()
+        for k in vecs_a:
+            if k not in {"mid_0", "gap_q"}:
+                g_a_gap.add_node(k)
+        strat.setup(g_a_gap, emb_a)
+        sl_a = strat.shortlist("gap_q")
+        assert set(sl_a.candidates) == {"right_0", "right_1", "right_2"}
+
+        # Case B: len(Left)=3, len(Right)=3 -> full tie on (hamming=1, gray_gap=1, len=3), Left wins (0 < 1)
+        g_b = ConceptGraph()
+        for name in [
+            "left_0",
+            "left_1",
+            "left_2",
+            "mid_0",
+            "right_0",
+            "right_1",
+            "right_2",
+        ]:
+            g_b.add_node(name)
+        strat.setup(g_b, emb_a)
+        assert [len(s) for s in strat._segments] == [4, 3]
+        assert "mid_0" in [e.name for e in strat._segments[0]]
+
+        g_b_gap = ConceptGraph()
+        for name in ["left_0", "left_1", "left_2", "right_0", "right_1", "right_2"]:
+            g_b_gap.add_node(name)
+        strat.setup(g_b_gap, emb_a)
+        sl_b = strat.shortlist("gap_q")
+        assert set(sl_b.candidates) == {"left_0", "left_1", "left_2"}
+
+        # Verify on_inserted uses the exact same tie-break in the gap case (kills M-32)
+        strat.on_inserted("gap_q", ())
+        assert "gap_q" in [e.name for e in strat._segments[0]]
+
+    def test_setup_merge_rebalances_when_combined_exceeds_s_max(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves merging an undersize bucket of size 2 with a neighbour of size 5 (> s_max=6) bisects into (3, 4) (kills M-20)."""
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        vecs: dict[str, np.ndarray] = {}
+        for i in range(2):
+            vecs[f"small_{i}"] = self._vec_for_code(0b0000, 4)
+        for i in range(5):
+            vecs[f"big_{i}"] = self._vec_for_code(0b0001, 4)
+        emb = ControllableEmbedder(vecs, dim=4)
+        graph = ConceptGraph()
+        for k in vecs:
+            graph.add_node(k)
+        strat.setup(graph, emb)
+        assert [len(s) for s in strat._segments] == [3, 4]
+        _assert_partition_invariants(strat, set(vecs.keys()))
+
+
+# ===========================================================================
+# 12. Shortlist Non-Mutation, Ordering, Normalization, and Boundary Lookup
+# ===========================================================================
+
+
+class TestShortlistSemanticsAndBoundaries:
+    """Proves shortlist() is read-only, normalizes vectors, sorts by (-score, name), and matches _locate_home boundaries."""
+
+    def test_shortlist_read_only_and_matches_insertion_segment(self) -> None:
+        """Proves shortlist() never mutates _segments, _mat, or _n and selects the exact home segment used by on_inserted()."""
+        graph = ConceptGraph()
+        for i in range(18):
+            graph.add_node(f"node_{i:02d}")
+        embedder = FakeEmbedder(dim=16, seed=42)
+        strat = BoundedBucketStrategy(s_min=3, s_max=6, n_bits=8, seed=42)
+        strat.setup(graph, embedder)
+
+        segs_before = [list(s) for s in strat._segments]
+        mat_before = strat._mat[: strat._n].copy()
+        n_before = strat._n
+
+        sl1 = strat.shortlist("new_probe")
+        sl2 = strat.shortlist("new_probe")
+        assert sl1 == sl2
+        assert isinstance(sl1.candidates, tuple)
+        assert isinstance(sl1.scores, tuple)
+        assert "new_probe" not in sl1.candidates
+        assert strat._segments == segs_before
+        assert strat._n == n_before
+        assert np.array_equal(strat._mat[: strat._n], mat_before)
+
+        home_id = strat.diagnostics()["bucket_id"]
+        assert home_id is not None
+        home_members_before = {e.name for e in strat._segments[home_id]}
+        assert set(sl1.candidates) == home_members_before
+
+        # If home segment has < s_max items, after on_inserted its members equal shortlist + {"new_probe"}
+        strat.on_inserted("new_probe", ())
+        if not strat.diagnostics()["split_occurred"]:
+            home_members_after = {e.name for e in strat._segments[home_id]}
+            assert home_members_after == home_members_before | {"new_probe"}
+
+    def test_shortlist_ordering_ties_and_unnormalised_vectors(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves shortlist normalizes query and indexed vectors and sorts by (-score, name) (kills M-12, M-13)."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=6, n_bits=2, seed=42)
+        monkeypatch.setattr(
+            strat,
+            "_draw_hyperplanes",
+            lambda dim: np.array(
+                [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float64
+            ),
+        )
+        base = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float32)
+        base_unit = base / np.linalg.norm(base)
+        v_90 = vector_with_cosine(base_unit, 0.90)
+        v_80 = vector_with_cosine(base_unit, 0.80)
+
+        # Scale vectors by arbitrary positive magnitudes to test L2 normalisation
+        vecs = {
+            "zeta_tie": 5.0 * v_90,
+            "alpha_tie": 0.02 * v_90,
+            "beta_low": 12.0 * v_80,
+            "query_node": 9.5 * base_unit,
+        }
+        emb = ControllableEmbedder(vecs, dim=4)
+        graph = ConceptGraph()
+        for name in ["zeta_tie", "alpha_tie", "beta_low"]:
+            graph.add_node(name)
+
+        strat.setup(graph, emb)
+        # Also query an already-indexed name to prove defensive self-exclusion
+        sl_self = strat.shortlist("alpha_tie")
+        assert "alpha_tie" not in sl_self.candidates
+
+        sl = strat.shortlist("query_node")
+        assert sl.candidates == ("alpha_tie", "zeta_tie", "beta_low")
+        assert sl.scores is not None
+        assert np.allclose(sl.scores, (0.90, 0.90, 0.80), atol=1e-5)
+
+    def test_locate_home_exact_segment_boundaries(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves _locate_home returns inside_span=True at both seg[0].sort_key() and seg[-1].sort_key() (kills M-23, M-24)."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=4, seed=42)
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        vecs = {
+            "a0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),
+            "a1": TestMergeAndNeighbourRule._vec_for_code(0b0001, 4),
+            "b0": TestMergeAndNeighbourRule._vec_for_code(0b0110, 4),
+            "b1": TestMergeAndNeighbourRule._vec_for_code(0b1100, 4),
+        }
+        emb = ControllableEmbedder(vecs, dim=4)
+        graph = ConceptGraph()
+        for k in vecs:
+            graph.add_node(k)
+        strat.setup(graph, emb)
+        # Force 2 segments of size 2: [a0, a1] and [b0, b1]
+        strat._segments = [
+            [strat._entry_by_name["a0"], strat._entry_by_name["a1"]],
+            [strat._entry_by_name["b0"], strat._entry_by_name["b1"]],
+        ]
+
+        # Exact left boundary of segment 0 and segment 1
+        e_a0 = strat._entry_by_name["a0"]
+        assert strat._locate_home(e_a0.gray, e_a0.name, e_a0.code) == (0, True)
+        e_b0 = strat._entry_by_name["b0"]
+        assert strat._locate_home(e_b0.gray, e_b0.name, e_b0.code) == (1, True)
+
+        # Exact right boundary of segment 0 and segment 1
+        e_a1 = strat._entry_by_name["a1"]
+        assert strat._locate_home(e_a1.gray, e_a1.name, e_a1.code) == (0, True)
+        e_b1 = strat._entry_by_name["b1"]
+        assert strat._locate_home(e_b1.gray, e_b1.name, e_b1.code) == (1, True)
+
+
+# ===========================================================================
+# 13 & 14. Lifecycle, D-58 Cache & Diagnostic Clearing, and setup() Failure Semantics
+# ===========================================================================
+
+
+class _SelectiveFailingEmbedder:
+    """Test helper that fails on a specific concept text according to fail_mode."""
+
+    def __init__(
+        self, base: Embedder, fail_concept: str, fail_mode: str
+    ) -> None:
+        self.base = base
+        self.fail_text = embed_text(fail_concept)
+        self.fail_mode = fail_mode
+
+    def embed(self, text: str) -> np.ndarray:
+        if text == self.fail_text:
+            if self.fail_mode == "raises":
+                raise RuntimeError("Simulated embedder error")
+            if self.fail_mode == "zero_norm":
+                return np.zeros(16, dtype=np.float32)
+            if self.fail_mode == "nan":
+                v = np.ones(16, dtype=np.float32)
+                v[0] = np.nan
+                return v
+            if self.fail_mode == "dim_mismatch":
+                return np.ones(8, dtype=np.float32)
+            if self.fail_mode == "non_1d":
+                return np.ones((2, 8), dtype=np.float32)
+        return self.base.embed(text)
+
+    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
+        return self.base.embed_many(texts)
+
+
+class TestLifecycleAndSetupSemantics:
+    """Proves D-58 cache/diagnostic clearing on shortlist failure, on_inserted guards, and all-or-nothing setup()."""
+
+    @pytest.mark.parametrize(
+        "fail_mode,bad_arg,exc_type,exc_match",
+        [
+            ("empty_name", "", ValueError, "cannot be empty"),
+            ("txt_suffix", "bad_node.txt", ValueError, r"cannot end in '\.txt'"),
+            ("raises", "failing_node", RuntimeError, "Simulated embedder error"),
+            ("zero_norm", "failing_node", ValueError, "Zero-norm"),
+            ("nan", "failing_node", ValueError, "non-finite"),
+            ("dim_mismatch", "failing_node", ValueError, "Dimension mismatch"),
+            ("non_1d", "failing_node", ValueError, "1-D ndarray"),
+        ],
+    )
+    def test_d58_failed_shortlist_clears_cache_and_query_diagnostics(
+        self,
+        fail_mode: str,
+        bad_arg: str,
+        exc_type: type[Exception],
+        exc_match: str,
+    ) -> None:
+        """Proves any failed shortlist() clears cache and resets per-query diagnostics at entry (kills M-11, M-28)."""
+        graph = ConceptGraph()
+        graph.add_node("existing_node")
+        base_emb = FakeEmbedder(dim=16, seed=42)
+        emb = _SelectiveFailingEmbedder(base_emb, "failing_node", fail_mode)
+        strat = BoundedBucketStrategy(s_min=2, s_max=5)
+        strat.setup(graph, emb)
+
+        res = strat.shortlist("good_node")
+        assert len(res.candidates) == 1
+        assert strat._cached_new_name == "good_node"
+        assert strat._cached_new_vec is not None
+        assert strat.diagnostics()["bucket_id"] == 0
+        assert strat.diagnostics()["shortlist_size"] == 1
+        assert strat.diagnostics()["exact_topk_overlap"] == 1.0
+
+        with pytest.raises(exc_type, match=exc_match):
+            strat.shortlist(bad_arg)
+
+        assert strat._cached_new_name is None
+        assert strat._cached_new_vec is None
+        assert strat._cached_new_code is None
+        assert strat._cached_new_gray is None
+
+        # Per-query diagnostics must also be reset after the failed shortlist (kills M-28)
+        diag = strat.diagnostics()
+        assert diag["bucket_id"] is None
+        assert diag["query_code"] is None
+        assert diag["query_gray_rank"] is None
+        assert diag["shortlist_size"] == 0
+        assert diag["exact_topk_overlap"] is None
+        assert diag["min_hamming_to_shortlist"] is None
+
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("good_node", ())
+
+    def test_on_inserted_guards_twice_duplicate_unqueried_and_stale_name(
+        self,
+    ) -> None:
+        """Proves on_inserted rejects missing shortlist, second call, duplicate node, and invalidated shortlist (kills M-17, M-18)."""
+        graph = ConceptGraph()
+        graph.add_node("n0")
+        embedder = FakeEmbedder(dim=16, seed=42)
+        strat = BoundedBucketStrategy(s_min=2, s_max=5)
+        strat.setup(graph, embedder)
+
+        # 1. on_inserted without shortlist
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("unqueried", ())
+
+        # 2. Second shortlist for a different name invalidates the first
+        strat.shortlist("first_cand")
+        strat.shortlist("second_cand")
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("first_cand", ())
+
+        # 3. Valid on_inserted succeeds, and calling on_inserted a second time raises RuntimeError
+        strat.on_inserted("second_cand", ())
+        with pytest.raises(RuntimeError, match="without matching shortlist"):
+            strat.on_inserted("second_cand", ())
+
+        # 4. Duplicate node (already indexed) raises ValueError
+        strat.shortlist("n0")
+        with pytest.raises(ValueError, match="already present in the index"):
+            strat.on_inserted("n0", ())
+
+    @pytest.mark.parametrize("fail_mode", ["zero_row", "nan_row", "non_2d", "wrong_rows"])
+    def test_failed_first_and_second_setup_leaves_strategy_not_set_up(
+        self, fail_mode: str
+    ) -> None:
+        """Proves a failed first or second setup() leaves the strategy not set up and clears state (kills M-09)."""
+
+        class _BadBatchEmbedder:
+            def embed(self, text: str) -> np.ndarray:
+                return np.ones(4, dtype=np.float32)
+
+            def embed_many(self, texts: Sequence[str]) -> Any:
+                if fail_mode == "zero_row":
+                    m = np.ones((len(texts), 4), dtype=np.float32)
+                    m[0] = 0.0
+                    return m
+                if fail_mode == "nan_row":
+                    m = np.ones((len(texts), 4), dtype=np.float32)
+                    m[0, 0] = np.nan
+                    return m
+                if fail_mode == "non_2d":
+                    return np.ones(4, dtype=np.float32)
+                if fail_mode == "wrong_rows":
+                    return np.ones((len(texts) + 1, 4), dtype=np.float32)
+                raise ValueError(fail_mode)
+
+        graph = ConceptGraph()
+        graph.add_node("n0")
+        good_emb = FakeEmbedder(dim=4, seed=42)
+        bad_emb = _BadBatchEmbedder()
+
+        strat = BoundedBucketStrategy(s_min=2, s_max=4)
+        # Failed first setup
+        with pytest.raises(ValueError):
+            strat.setup(graph, bad_emb)  # type: ignore[arg-type]
+        assert not strat._setup_called
+        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
+            strat.shortlist("probe")
+
+        # Valid setup followed by shortlist
+        strat.setup(graph, good_emb)
+        strat.shortlist("probe")
+        assert strat.diagnostics()["num_segments"] == 1
+
+        # Failed second setup leaves strategy NOT set up and clears segments/caches
+        with pytest.raises(ValueError):
+            strat.setup(graph, bad_emb)  # type: ignore[arg-type]
+        assert not strat._setup_called
+        assert strat._embedder is None
+        assert strat._cached_new_name is None
+        assert strat.diagnostics()["num_segments"] == 0
+        with pytest.raises(RuntimeError, match="setup\\(\\) must be called"):
+            strat.shortlist("probe")
+
+        # Valid re-setup recovers cleanly
+        strat.setup(graph, good_emb)
+        assert strat.shortlist("probe").candidates == ("n0",)
+
+
+# ===========================================================================
+# 15 & 16. Embedding Accounting, Matrix Capacity, and Edge Cases
+# ===========================================================================
+
+
+class TestEmbeddingAccountingAndEdgeCases:
+    """Proves single-embedding reuse, no reallocation on first insert, doubling growth, and small-n edge cases."""
+
+    @pytest.mark.parametrize("n", [1, 50, 500])
+    def test_first_insert_after_setup_does_not_reallocate_matrix(
+        self, n: int
+    ) -> None:
+        """Proves _mat buffer address is unchanged on the first on_inserted() after setup() (kills M-10)."""
+        graph = ConceptGraph()
+        for i in range(n):
+            graph.add_node(f"node_{i:04d}")
+        raw_emb = FakeEmbedder(dim=16, seed=42)
+        meter = MeteredEmbedder(raw_emb)
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
+        strat.setup(graph, meter)
+        meter.reset()
+
+        assert strat._mat is not None
+        assert strat._mat.shape[0] == max(16, 2 * n)
+        ptr_before = strat._mat.ctypes.data
+
+        res = insert_node(
+            strat,
+            graph,
+            FakeDecisionStep(make_edge=False),
+            "first_inserted",
+            metered_embedder=meter,
+        )
+        assert res.metrics.embedding_calls == 1
+        assert res.metrics.embedding_calls_in_update == 0
+        assert strat._mat.ctypes.data == ptr_before
+
+    def test_doubling_growth_preserves_all_rows_over_200_inserts(self) -> None:
+        """Proves matrix doubling across 200 sequential inserts preserves every earlier normalised vector."""
+        graph = ConceptGraph()
+        raw_emb = FakeEmbedder(dim=16, seed=42)
+        meter = MeteredEmbedder(raw_emb)
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
+        strat.setup(graph, meter)
+
+        expected_vecs: dict[str, np.ndarray] = {}
+        for i in range(200):
+            name = f"grow_{i:03d}"
+            raw_v = raw_emb.embed(embed_text(name))
+            expected_vecs[name] = (raw_v / np.linalg.norm(raw_v)).astype(
+                np.float32
+            )
+            insert_node(
+                strat,
+                graph,
+                FakeDecisionStep(make_edge=False),
+                name,
+                metered_embedder=meter,
+            )
+
+        assert strat._mat is not None
+        for name, exp_v in expected_vecs.items():
+            row = strat._name_to_idx[name]
+            assert np.allclose(strat._mat[row], exp_v, atol=1e-6)
+
+    def test_edge_cases_n0_n1_n_less_than_s_min_and_single_segment_branch(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves n=0, n=1, and n < s_min single-segment branch without calling _choose_neighbour (kills M-27)."""
+        embedder = FakeEmbedder(dim=16, seed=42)
+
+        # n = 0
+        s0 = BoundedBucketStrategy(s_min=5, s_max=10)
+        s0.setup(ConceptGraph(), embedder)
+        assert s0.shortlist("first") == Shortlist(candidates=(), scores=())
+        s0.on_inserted("first", ())
+        assert len(s0._segments) == 1 and len(s0._segments[0]) == 1
+
+        # n = 1
+        g1 = ConceptGraph()
+        g1.add_node("only_node")
+        s1 = BoundedBucketStrategy(s_min=5, s_max=10)
+        s1.setup(g1, embedder)
+        sl1 = s1.shortlist("second_node")
+        assert sl1.candidates == ("only_node",)
+        s1.on_inserted("second_node", ())
+        assert len(s1._segments) == 1 and len(s1._segments[0]) == 2
+
+        # n = 3 < s_min = 5: must take the direct n < s_min single-segment branch without calling _choose_neighbour
+        g3 = ConceptGraph()
+        for name in ["c_a", "c_b", "c_c"]:
+            g3.add_node(name)
+        s3 = BoundedBucketStrategy(s_min=5, s_max=10)
+        choose_calls: list[int] = []
+        orig_choose = s3._choose_neighbour
+
+        def _spy_choose(*args: Any, **kwargs: Any) -> str:
+            choose_calls.append(1)
+            return orig_choose(*args, **kwargs)
+
+        monkeypatch.setattr(s3, "_choose_neighbour", _spy_choose)
+        s3.setup(g3, embedder)
+        assert len(s3._segments) == 1 and len(s3._segments[0]) == 3
+        assert choose_calls == []
+
+
+# ===========================================================================
+# 17. Diagnostics Schema, Lazy Overlap, Min Hamming, and Driver Smoke
+# ===========================================================================
+
+
+class TestDiagnostics:
+    """Proves 18-key JSON-safe diagnostics, lazy exact_topk_overlap, and min_hamming_to_shortlist."""
+
+    EXPECTED_KEYS = {
+        "bucket_id",
+        "bucket_gray_min",
+        "bucket_gray_max",
+        "query_code",
+        "query_gray_rank",
+        "code_existed_in_bucket",
+        "inside_bucket_span",
+        "bucket_size_at_shortlist",
+        "bucket_size",
+        "shortlist_size",
+        "split_occurred",
+        "merge_occurred",
+        "num_segments",
+        "min_segment_size",
+        "max_segment_size",
+        "mean_segment_size",
+        "exact_topk_overlap",
+        "min_hamming_to_shortlist",
+    }
+
+    def test_diagnostics_lifecycle_lazy_overlap_and_min_hamming(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        """Proves diagnostics JSON safety across all states, lazy overlap calculation (kills M-21), and min_hamming_to_shortlist."""
+        strat = BoundedBucketStrategy(s_min=2, s_max=4, n_bits=4, seed=42)
+
+        # 1. Before setup()
+        d0 = strat.diagnostics()
+        assert set(d0.keys()) == self.EXPECTED_KEYS
+        assert d0["exact_topk_overlap"] is None
+        assert d0["min_hamming_to_shortlist"] is None
+        _assert_no_numpy_types(d0)
+        json.dumps(d0)
+
+        # 2. Empty setup() and shortlist() on empty index -> overlap is 1.0, min_hamming is None
+        emb_empty = FakeEmbedder(dim=4, seed=42)
+        strat.setup(ConceptGraph(), emb_empty)
+        d_setup_empty = strat.diagnostics()
+        assert d_setup_empty["exact_topk_overlap"] is None
+
+        strat.shortlist("first_q")
+        assert strat._cached_exact_topk_overlap is None  # Lazy: not computed in shortlist()
+        d_empty_q = strat.diagnostics()
+        assert strat._cached_exact_topk_overlap == 1.0
+        assert d_empty_q["exact_topk_overlap"] == 1.0
+        assert d_empty_q["min_hamming_to_shortlist"] is None
+        _assert_no_numpy_types(d_empty_q)
+        json.dumps(d_empty_q)
+
+        # 3. Hand-built case for min_hamming_to_shortlist and exact_topk_overlap
+        monkeypatch.setattr(
+            strat, "_draw_hyperplanes", lambda dim: np.eye(4, dtype=np.float64)
+        )
+        vecs = {
+            "n0": TestMergeAndNeighbourRule._vec_for_code(0b0000, 4),  # code 0
+            "n1": TestMergeAndNeighbourRule._vec_for_code(0b0011, 4),  # code 3
+            "q": TestMergeAndNeighbourRule._vec_for_code(0b0111, 4),  # code 7 (hamming 1 to code 3, 3 to code 0)
+        }
+        emb = ControllableEmbedder(vecs, dim=4)
+        g = ConceptGraph()
+        g.add_node("n0")
+        g.add_node("n1")
+        strat.setup(g, emb)
+
+        strat.shortlist("q")
+        assert strat._cached_exact_topk_overlap is None  # Still None before diagnostics()
+        d_q = strat.diagnostics()
+        assert d_q["min_hamming_to_shortlist"] == 1
+        assert d_q["exact_topk_overlap"] == 1.0
+
+        strat.on_inserted("q", ())
+        d_ins = strat.diagnostics()
+        assert set(d_ins.keys()) == self.EXPECTED_KEYS
+        assert d_ins["bucket_size"] == 3
+        _assert_no_numpy_types(d_ins)
+        json.dumps(d_ins)
+
+    def test_exact_topk_overlap_matches_independent_float64_reference_through_driver(
+        self,
+    ) -> None:
+        """Proves exact_topk_overlap in metrics.extra matches an independent float64 brute-force top-m calculation."""
+        graph = ConceptGraph()
+        init_names = [f"node_{i:03d}" for i in range(40)]
+        for name in init_names:
+            graph.add_node(name)
+
+        raw_emb = FakeEmbedder(dim=16, seed=42)
+        meter = MeteredEmbedder(raw_emb)
+        decision = FakeDecisionStep(make_edge=False)
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=10, seed=42)
+        strat.setup(graph, meter)
+
+        for probe in ["probe_0", "probe_1", "probe_2"]:
+            existing_names = sorted(graph.nodes())
+            raw_mat = raw_emb.embed_many([embed_text(x) for x in existing_names])
+            mat64 = raw_mat.astype(np.float64)
+            mat64 /= np.linalg.norm(mat64, axis=1, keepdims=True)
+
+            q_raw = raw_emb.embed(embed_text(probe)).astype(np.float64)
+            q64 = q_raw / np.linalg.norm(q_raw)
+            cosines = mat64 @ q64
+            ranked = sorted(
+                [(float(cosines[i]), existing_names[i]) for i in range(len(existing_names))],
+                key=lambda item: (-item[0], item[1]),
+            )
+            m = min(strat.s_max, len(ranked))
+            exact_top_m = {name for _, name in ranked[:m]}
+
+            res = insert_node(
+                strat, graph, decision, probe, metered_embedder=meter
+            )
+            expected_overlap = sum(
+                1 for c in res.shortlist.candidates if c in exact_top_m
+            ) / m
+            assert set(res.metrics.extra.keys()) == self.EXPECTED_KEYS
+            assert np.isclose(
+                res.metrics.extra["exact_topk_overlap"], expected_overlap
+            )
+
+    def test_harness_sweep_smoke(self, tmp_path: Any) -> None:
+        """Proves BoundedBucketStrategy runs end-to-end through run_sweep_experiment."""
+        names = [f"concept_{i:04d}" for i in range(100)]
+        name_source = SyntheticNameSource(
+            names=names, domain_context="computer science"
+        )
+        client = MeteredLLMClient(FakeLLMClient())
+        decision_step = PairwiseDecisionStep(client)
+        cfg = HarnessConfig(
+            mode="sweep",
+            run_id="test_bb_smoke",
+            output_dir=tmp_path / "bb_smoke",
+            seed=42,
+            sweep_sizes=(15, 30),
+            sweep_trials_per_size=2,
+            confirm=True,
+        )
+        out = run_sweep_experiment(
+            config=cfg,
+            strategy_factory=lambda: BoundedBucketStrategy(
+                s_min=5, s_max=10, n_bits=12, seed=42
+            ),
+            decision_step=decision_step,
+            embedder_factory=lambda: FakeEmbedder(dim=16, seed=42),
+            name_source=name_source,
+        )
+        assert out["status"] == "completed"
+        raw_lines = (
+            (tmp_path / "bb_smoke" / "raw.jsonl").read_text().strip().splitlines()
+        )
+        assert len(raw_lines) == 4
+        for line in raw_lines:
+            rec = json.loads(line)
+            assert rec["strategy"] == "bounded_bucket"
+            assert 5 <= rec["metrics"]["shortlist_size"] <= 10
+            assert set(rec["metrics"]["extra"].keys()) == self.EXPECTED_KEYS
+
+
+# ===========================================================================
+# 18. Sequential Stream Without Cascades (m = 200 Inserts From n = 0)
+# ===========================================================================
+
+
+class TestSequentialStreamNoCascades:
+    """Proves m=200 sequential inserts from n=0 never cascade and enforce >= s_min inserts between splits."""
+
+    def test_200_sequential_inserts_no_cascades_and_amortisation_gap(
+        self,
+    ) -> None:
+        """Proves each insert alters at most 1 segment into at most 2 and any split child receives >= s_min inserts before re-splitting."""
+        embedder = FakeEmbedder(dim=16, seed=123)
+        strat = BoundedBucketStrategy(s_min=5, s_max=10, n_bits=12, seed=42)
+        strat.setup(ConceptGraph(), embedder)
+
+        # Track how many insertions each currently active segment has received since it was created by a split
+        inserts_since_split: list[int] = []
+
+        for step in range(200):
+            name = f"stream_{step:04d}"
+            segs_before = [tuple(e.name for e in s) for s in strat._segments]
+
+            sl = strat.shortlist(name)
+            home_idx = strat.diagnostics()["bucket_id"]
+            strat.on_inserted(name, ())
+
+            segs_after = [tuple(e.name for e in s) for s in strat._segments]
+            diag = strat.diagnostics()
+
+            if step == 0:
+                assert len(segs_after) == 1
+                inserts_since_split = [0]
+                continue
+
+            assert home_idx is not None
+            inserts_since_split[home_idx] += 1
+
+            if not diag["split_occurred"]:
+                # Exactly 1 segment grew by 1; all other segments are untouched
+                assert len(segs_after) == len(segs_before)
+                for idx in range(len(segs_before)):
+                    if idx != home_idx:
+                        assert segs_after[idx] == segs_before[idx]
+                    else:
+                        assert set(segs_after[idx]) == set(segs_before[idx]) | {
+                            name
+                        }
+                        assert set(sl.candidates) == set(segs_before[idx])
+            else:
+                # Split occurred: the segment must have received at least s_min insertions since its last split
+                assert inserts_since_split[home_idx] >= strat.s_min
+                # Exactly 1 segment turned into 2; all other segments untouched
+                assert len(segs_after) == len(segs_before) + 1
+                assert segs_after[:home_idx] == segs_before[:home_idx]
+                assert segs_after[home_idx + 2 :] == segs_before[home_idx + 1 :]
+                combined_after = set(segs_after[home_idx]) | set(
+                    segs_after[home_idx + 1]
+                )
+                assert combined_after == set(segs_before[home_idx]) | {name}
+                # Reset split counters for the two new child segments
+                inserts_since_split[home_idx : home_idx + 1] = [0, 0]
```

---

## 9. Post-Edit `git status --short`

```text
$ git status --short
 M docs/context/repo-tree.txt
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M tests/stub_prompt_adapter.py
?? scripts/name_pool_supervisor.py
?? src/graph_insertion/strategies/bounded_bucket.py
?? tests/test_bounded_bucket_strategy.py
?? tests/test_name_pool_supervisor.py
?? docs/reports/STRAT-004-gemini-bounded-bucket.md
```
