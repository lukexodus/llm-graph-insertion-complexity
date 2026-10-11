# STRAT-003-B — Close the Stale-Cache Hole in Strategy 2 and Strategy 3

Task: STRAT-003-B  
Date: 2026-10-11  
Base commit: `a532293` (`master`)  
Decision ID: **[D-58]**  

---

## 1. Agent Identity

- **Agent:** `gemini`
- **Model label:** `Gemini 3.8 Flash (High)`
- **Session & Independence Disclosure:** `[Confirmed]` This prompt was dispatched by the operator into conversation session `b8ab4203-d881-4c7d-8f76-db6a0b797a9c`, which previously executed `STRAT-003`, `STRAT-003-R`, and `STRAT-003-A`. Per the prompt's transparency rule ("Suggested agent: any session that did NOT implement, review or amend STRAT-002 or STRAT-003 (independence is by session)"), this shared session history is explicitly disclosed here rather than concealed. All claims, reproductions, pre-fix failures, post-fix passes, and mutation checks (M1–M9) were executed from fresh commands against `a532293` and recorded verbatim below.

---

## 2. What Was Asked / What I Did

### What was asked
1. **Reproduce (Step 1):** Reproduce the stale-cache sequence on both `AnnRetrievalStrategy` (Strategy 3) and `EmbeddingThresholdStrategy` (Strategy 2) prior to editing code.
2. **Step 2.A (`src/graph_insertion/strategies/ann_retrieval.py`):** Move `self._cached_new_name = None` and `self._cached_new_vec = None` to be the first executable statements of `shortlist()`, before the not-set-up check (`if not self._setup_called or self._embedder is None:`). Leave `self._cached_exact_topk_overlap = None` in place and update the comment.
3. **Step 2.B (`src/graph_insertion/strategies/embedding_threshold.py`):** Add `self._cached_new_name = None` and `self._cached_new_vec = None` as the first executable statements of `shortlist()`. Leave `self._shortlist_called` untouched and note it under Section 8.
4. **Step 2.C (`tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`):** Add parametrised tests covering `shortlist("")`, one additional invalid name rejected by `_validate_concept_name` (`"bad_node.txt"`, rejected by `if name.endswith(".txt"):`), an embedder that raises, and zero-norm, NaN, and dimension-mismatch vectors. Assert `_cached_new_name is None`, `_cached_new_vec is None`, and that `on_inserted("good_node", ())` raises `RuntimeError`. Evaluate whether a not-set-up check failure after a prior successful shortlist is constructible, and run the new tests against the pre-fix code first.
5. **Step 2.D (Mutation check M1–M9):** Run M1–M9 on a copy under `/tmp` with `PYTHONPATH` and report `KILLED`/`SURVIVED` and killer tests.
6. **Step 2.E (`docs/decisions/decision-log.md`):** Append **`[D-58]`** at the end of `docs/decisions/decision-log.md` (without test counts). Do not touch `docs/tasks/status.md`.

### What I did
1. `[Confirmed]` Verified base commit `a532293` on branch `master`, backed up the four target files to `/tmp/strat003b-before/`, and ran the baseline full test suite (`466 passed, 3 skipped`).
2. `[Confirmed]` Reproduced the pre-fix stale-cache defect on both Strategy 3 (via `shortlist("")` and `shortlist("bad.txt")`) and Strategy 2 (via `""`, `"bad.txt"`, raising embedder, zero-norm, NaN, and dimension mismatch) using `/tmp/repro_stale_cache.py`.
3. `[Confirmed]` Added the 6-way parametrised stale-cache tests to `tests/test_ann_retrieval_strategy.py` and `tests/test_embedding_threshold_strategy.py`, and executed them against the unedited pre-fix code to capture verbatim failure output.
4. `[Confirmed]` Applied the `shortlist()` entry cache-clear edits to `src/graph_insertion/strategies/ann_retrieval.py` and `src/graph_insertion/strategies/embedding_threshold.py`.
5. `[Confirmed]` Re-ran both strategy test files (`71 passed` and `45 passed`) and the full repository test suite (`477 passed, 3 skipped`).
6. `[Confirmed]` Executed mutation checks M1–M9 in `/tmp/strat003b-mut` via `/tmp/run_mutations_strat003b.py` (8 killed, 1 expected equivalent survivor M8).
7. `[Confirmed]` Appended `[D-58]` to `docs/decisions/decision-log.md`.

---

## 3. Prompt Corrections

Every claim in the prompt was checked against the repository at commit `a532293`:

| Prompt Claim | Verdict | Evidence |
| :--- | :--- | :--- |
| Repo branch is `master` (not `main`), base commit `a532293` | `[Confirmed]` **Right** | `git rev-parse --short HEAD` outputs `a532293`; `git branch --show-current` outputs `master`. |
| `D-58` is absent from the committed log at `a532293` | `[Confirmed]` **Right** | `docs/decisions/decision-log.md` ends at `[D-57]` (line 449) at `a532293`. |
| "`D-56` is also absent and not referenced anywhere, do not use it" | `[Confirmed]` **Partially wrong** | No `**[D-56]**` decision entry exists, but `D-56` **is** referenced in `[D-57](3)` at `docs/decisions/decision-log.md:447` (`"and D-56 was reserved by the APC; D-57 is used per operator instruction"`). `D-58` was used as instructed. |
| Luke's last full run before edits was `466 passed, 3 skipped` | `[Confirmed]` **Right** | Baseline `.venv-ann/bin/python -m pytest -q | tail -3` at `a532293` outputs `466 passed, 3 skipped in 72.33s`. |
| In `AnnRetrievalStrategy.shortlist()`, the cache clear sits after the not-set-up check and after `_validate_concept_name(new_name)` (about lines 273 to 281) | `[Confirmed]` **Right** | In `src/graph_insertion/strategies/ann_retrieval.py:273-281` at `a532293`, the not-set-up check is at lines 273–274, `_validate_concept_name(new_name)` is at line 276, and `_cached_new_name = None; _cached_new_vec = None` is at lines 280–281. |
| `EmbeddingThresholdStrategy.shortlist()` never clears the cache on entry; it only overwrites `_cached_new_name` and `_cached_new_vec` (about lines 226 to 227) after name check, embedding, and vector validation pass | `[Confirmed]` **Right** | In `src/graph_insertion/strategies/embedding_threshold.py:196-227` at `a532293`, there is no cache clear on entry; `self._cached_new_name = new_name` and `self._cached_new_vec = q` sit at lines 226–227. |
| `_shortlist_called` in `EmbeddingThresholdStrategy` is set but never read | `[Confirmed]` **Right** | Set to `False` in `__init__` (`embedding_threshold.py:91`) and `setup` (`embedding_threshold.py:122`), and to `True` in `shortlist` (`embedding_threshold.py:228`); never read anywhere in `src/` or `tests/`. |
| Through `insert_node` the hole is unreachable because `strategy.py` validates the name (about line 260) before calling `shortlist()` | `[Confirmed]` **Right** | `src/graph_insertion/strategy.py:260` calls `_validate_concept_name(new_name)` before `strategy.shortlist(new_name)` at line 271, and `insert_node` only calls `on_inserted` at line 346 if `shortlist` in the same call succeeded. |
| Existing T-1 test (`test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector`) only exercises the zero-norm vector failure | `[Confirmed]` **Right** | At `tests/test_ann_retrieval_strategy.py:984-1030` (`a532293`), `_SelectiveFailingEmbedder.embed` only returned `np.zeros(16, dtype=np.float32)`. |
| "The STRAT-003-A report names `test_cached_embedding_reuse_single_embedding_per_insert` as the killer of its mutation 6. That test does not exist in `tests/test_ann_retrieval_strategy.py`." | `[Confirmed]` **Clarification** | `def test_cached_embedding_reuse_single_embedding_per_insert` is not defined directly in `tests/test_ann_retrieval_strategy.py`, **but** `TestAnnRetrievalConformance` (`tests/test_ann_retrieval_strategy.py:41`) inherits `StrategyConformanceSuite` (`tests/test_strategy_interface.py:200`), which defines `test_cached_embedding_reuse_single_embedding_per_insert` at `tests/test_strategy_interface.py:318`. Thus pytest collects and runs `tests/test_ann_retrieval_strategy.py::TestAnnRetrievalConformance::test_cached_embedding_reuse_single_embedding_per_insert`, and it is indeed the first of 4 tests in `test_ann_retrieval_strategy.py` that kill M9 (mutation 6). |
| Requirement 2.C.3: "Each new test must be shown to FAIL on the pre-fix code" | `[Confirmed]` **Clarification** | On pre-fix Strategy 2 (`embedding_threshold.py`), all 6 parametrised failure modes (`empty_name`, `txt_suffix`, `embedder_raises`, `zero_norm`, `nan_vec`, `dim_mismatch`) fail. On pre-fix Strategy 3 (`ann_retrieval.py` at `a532293`), D-55 had already placed the cache clear after `_validate_concept_name` and before `_embedder.embed`, so the 2 name-validation modes (`empty_name`, `txt_suffix`) fail on `a532293` while the 4 post-validation modes (`embedder_raises`, `zero_norm`, `nan_vec`, `dim_mismatch`) already pass on `a532293` (and fail under Mutation M4 when the clear is removed). |
| Requirement 2.C.2: Not-set-up check after earlier successful shortlist on a previous setup ("only if constructible; otherwise say why not") | `[Confirmed]` **Not constructible via public API** | Through the public API (`__init__`, `setup`, `shortlist`, `on_inserted`), a strategy only has `_setup_called == False` or `_embedder is None` before the first `setup()` (when no shortlist has succeeded) or after a subsequent `setup()` call fails. Because `setup()` unconditionally sets `self._cached_new_name = None` and `self._cached_new_vec = None` at its very top (`ann_retrieval.py:190-191`, `embedding_threshold.py:124-125`) before any failure can occur, reaching the not-set-up check in `shortlist()` with a populated cache is impossible without directly mutating private attributes (`_setup_called` or `_embedder`). This is the exact reason M8 survives as an equivalent mutant. |

---

## 4. Reproduction of the Stale-Cache Sequence Before the Fix

Executed `/tmp/repro_stale_cache.py` against commit `a532293` before any source edits (`[Confirmed]`):

```text
=== 1. Strategy 3 (AnnRetrievalStrategy) Stale-Cache Reproduction (Pre-Fix) ===
After shortlist('good_node'): _cached_new_name = 'good_node' _cached_new_vec is not None = True
shortlist('') raised ValueError: Concept name cannot be empty, got ''
After failed shortlist(''): _cached_new_name = 'good_node', _cached_new_vec is not None = True
shortlist('bad.txt') raised ValueError: Concept name cannot end in '.txt' (D-16/D-21: nodes must be bare names), got 'bad.txt'
After failed shortlist('bad.txt'): _cached_new_name = 'good_node', _cached_new_vec is not None = True
s3.on_inserted('good_node', ()) SUCCEEDED with stale cache! index_size = 2

=== 2. Strategy 2 (EmbeddingThresholdStrategy) Stale-Cache Reproduction (Pre-Fix) ===
[empty_name] raised ValueError("Concept name cannot be empty, got ''") -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
[txt_suffix] raised ValueError("Concept name cannot end in '.txt' (D-16/D-21: nodes must be bare names), got 'bad.txt'") -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
[embedder_raises] raised RuntimeError('boom') -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
[zero_norm] raised ValueError("Zero-norm embedding vector for concept 'other_node'") -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
[nan_vec] raised ValueError("Embedding for 'other_node' contains non-finite values") -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
[dim_mismatch] raised ValueError("Dimension mismatch for 'other_node': expected 16, got 8") -> _cached_new_name='good_node', vec_present=True, on_inserted('good_node') SUCCEEDED (index_size=2)
```

### Pre-Fix Test Failures (Requirement 2.C.3)

#### `tests/test_ann_retrieval_strategy.py` on Pre-Fix `ann_retrieval.py`
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 71 items / 65 deselected / 6 selected

tests/test_ann_retrieval_strategy.py FF....                              [100%]

=================================== FAILURES ===================================
_ TestPostReviewAmendments.test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty] _
tests/test_ann_retrieval_strategy.py:1053: in test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.ann_retrieval.AnnRetrievalStrategy object at 0x7f76c49ec2f0>._cached_new_name
_ TestPostReviewAmendments.test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt'] _
tests/test_ann_retrieval_strategy.py:1053: in test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.ann_retrieval.AnnRetrievalStrategy object at 0x7f76c4b96350>._cached_new_name
=========================== short test summary info ============================
FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty]
FAILED tests/test_ann_retrieval_strategy.py::TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt']
================== 2 failed, 4 passed, 65 deselected in 0.25s ==================
```

#### `tests/test_embedding_threshold_strategy.py` on Pre-Fix `embedding_threshold.py`
```text
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 45 items / 39 deselected / 6 selected

tests/test_embedding_threshold_strategy.py FFFFFF                        [100%]

=================================== FAILURES ===================================
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[empty_name--ValueError-cannot be empty] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873b3ba120>._cached_new_name
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt'] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873b3fa0d0>._cached_new_name
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[embedder_raises-failing_node-RuntimeError-Simulated embedder failure] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873b3fad50>._cached_new_name
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[zero_norm-failing_node-ValueError-Zero-norm] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873aeef100>._cached_new_name
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[nan_vec-failing_node-ValueError-non-finite] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873aeefce0>._cached_new_name
_ TestValidationAndContracts.test_shortlist_failure_clears_stale_cache[dim_mismatch-failing_node-ValueError-Dimension mismatch] _
tests/test_embedding_threshold_strategy.py:1057: in test_shortlist_failure_clears_stale_cache
    assert strat._cached_new_name is None
E   AssertionError: assert 'good_node' is None
E    +  where 'good_node' = <graph_insertion.strategies.embedding_threshold.EmbeddingThresholdStrategy object at 0x7f873ae82570>._cached_new_name
=========================== short test summary info ============================
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[empty_name--ValueError-cannot be empty]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt']
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[embedder_raises-failing_node-RuntimeError-Simulated embedder failure]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[zero_norm-failing_node-ValueError-Zero-norm]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[nan_vec-failing_node-ValueError-non-finite]
FAILED tests/test_embedding_threshold_strategy.py::TestValidationAndContracts::test_shortlist_failure_clears_stale_cache[dim_mismatch-failing_node-ValueError-Dimension mismatch]
======================= 6 failed, 39 deselected in 0.33s =======================
```

---

## 5. Verification Output

### 5.1 Pre-Edit Full Suite (`.venv-ann/bin/python -m pytest -q | tail -3`)
```text
.....                                                                    [100%]

================== 466 passed, 3 skipped in 72.33s (0:01:12) ===================
```
Matches Luke's last full run (`466 passed, 3 skipped`).

### 5.2 Post-Fix Strategy 3 Suite (`.venv-ann/bin/python -m pytest -q tests/test_ann_retrieval_strategy.py`)
```text
tests/test_ann_retrieval_strategy.py ................................... [ 49%]
....................................                                     [100%]

============================== 71 passed in 1.60s ==============================
```

### 5.3 Post-Fix Strategy 2 Suite (`.venv-ann/bin/python -m pytest -q tests/test_embedding_threshold_strategy.py`)
```text
tests/test_embedding_threshold_strategy.py ............................. [ 64%]
................                                                         [100%]

============================== 45 passed in 0.53s ==============================
```

### 5.4 Post-Fix Full Suite (`.venv-ann/bin/python -m pytest -q | tail -3`)
```text
.....                                                                    [100%]

================== 477 passed, 3 skipped in 87.57s (0:01:27) ===================
```

### 5.5 `sha256sum` and `wc -l` Before and After
```text
b479f32dc3a3a205fb2f1e5b368cd92375b89456f39dfb2e8b210ec39fbc3ada  /tmp/strat003b-before/ann_retrieval.py
adc1209594126abd8d5ca62953c1ab1136ae928fb886ef6f1c6fd357e53b8a53  /tmp/strat003b-before/embedding_threshold.py
46e70cdf36173dddd7546424a99df8a06502051254c8525cdd3b3292a0b8310c  /tmp/strat003b-before/test_ann_retrieval_strategy.py
136c2cf0c0f9ee16eace1e7a86278db8b39a820bd45e6db1f0054c9efc856459  /tmp/strat003b-before/test_embedding_threshold_strategy.py
50d40522c6ff7cb6fe7e8250b63a085813f08d29ead855c230c34c6cc4ffb758  src/graph_insertion/strategies/ann_retrieval.py
00a19fb9e74831decdfaf5fdfe71385f6a5b60f8f1b2d38d081a812e332626b3  src/graph_insertion/strategies/embedding_threshold.py
97456929e0686495ebd9c83e6d2312eb3b33862db265ed28162ac9a479501875  tests/test_ann_retrieval_strategy.py
910772a5ca75104747411fc31b3ece609f762134bb6fd17822e2a5ea9911f241  tests/test_embedding_threshold_strategy.py
   461 /tmp/strat003b-before/ann_retrieval.py
   323 /tmp/strat003b-before/embedding_threshold.py
  1156 /tmp/strat003b-before/test_ann_retrieval_strategy.py
  1040 /tmp/strat003b-before/test_embedding_threshold_strategy.py
   461 src/graph_insertion/strategies/ann_retrieval.py
   328 src/graph_insertion/strategies/embedding_threshold.py
  1195 tests/test_ann_retrieval_strategy.py
  1108 tests/test_embedding_threshold_strategy.py
  6072 total
```

### 5.6 `git status --short`
```text
 M docs/decisions/decision-log.md
 M src/graph_insertion/strategies/ann_retrieval.py
 M src/graph_insertion/strategies/embedding_threshold.py
 M tests/test_ann_retrieval_strategy.py
 M tests/test_embedding_threshold_strategy.py
?? docs/reports/STRAT-003-B-gemini.md
```

---

## 6. Mutation Table (M1 to M9)

Executed in `/tmp/strat003b-mut` with `PYTHONPATH=/tmp/strat003b-mut/src:/tmp/strat003b-mut` via `/tmp/run_mutations_strat003b.py`:

| ID | Target | Mutation Description | Result | Killer Test(s) / Explanation |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | Strategy 3 | Clear moved back below `_validate_concept_name` | **KILLED** | `TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector[empty_name--ValueError-cannot be empty]`, `[txt_suffix-bad_node.txt-ValueError-cannot end in '\\.txt']` (2 failures) |
| **M2** | Strategy 3 | Only `_cached_new_name` cleared on entry | **KILLED** | All 6 parameterizations of `TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` (fails `assert strat._cached_new_vec is None`) |
| **M3** | Strategy 3 | Only `_cached_new_vec` cleared on entry | **KILLED** | All 6 parameterizations of `TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` (fails `assert strat._cached_new_name is None`) |
| **M4** | Strategy 3 | Clear removed from `shortlist()` entirely | **KILLED** | All 6 parameterizations of `TestPostReviewAmendments::test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector` |
| **M5** | Strategy 2 | Clear removed from `shortlist()` (the new code) | **KILLED** | All 6 parameterizations of `TestValidationAndContracts::test_shortlist_failure_clears_stale_cache` |
| **M6** | Strategy 2 | Only `_cached_new_name` cleared on entry | **KILLED** | All 6 parameterizations of `TestValidationAndContracts::test_shortlist_failure_clears_stale_cache` (fails `assert strat._cached_new_vec is None`) |
| **M7** | Strategy 2 | Only `_cached_new_vec` cleared on entry | **KILLED** | All 6 parameterizations of `TestValidationAndContracts::test_shortlist_failure_clears_stale_cache` (fails `assert strat._cached_new_name is None`) |
| **M8** | Strategy 2 & 3 | Clear placed after not-set-up check (`if not self._setup_called or self._embedder is None:`) but before `_validate_concept_name` | **SURVIVED** | **Equivalent mutant through the public API:** Whenever `not self._setup_called or self._embedder is None` holds in `shortlist()`, the strategy is either freshly constructed (`__init__`) or had a subsequent `setup()` call fail; in both cases `_cached_new_name` and `_cached_new_vec` are already `None` because `setup()` clears both at its entry (`ann_retrieval.py:190-191`, `embedding_threshold.py:124-125`). |
| **M9** | Strategy 3 | `on_inserted()` re-embeds `new_name` (STRAT-003-A mutation 6) | **KILLED** | Killed by 4 tests: (1) `TestAnnRetrievalConformance::test_cached_embedding_reuse_single_embedding_per_insert` (inherited from `StrategyConformanceSuite` at `tests/test_strategy_interface.py:318`), (2) `TestSingleEmbeddingInvariant::test_single_embedding_and_payload_compliance`, (3) `TestSingleEmbeddingInvariant::test_empty_initial_graph_single_embedding`, and (4) `TestHarnessSmoke::test_sweep_harness_smoke` (all asserting `embedding_calls_in_update == 0`). |

---

## 7. Diffs

### 7.1 `src/graph_insertion/strategies/ann_retrieval.py`
```diff
diff --git i/src/graph_insertion/strategies/ann_retrieval.py w/src/graph_insertion/strategies/ann_retrieval.py
index 60813e3..d6ae221 100644
--- i/src/graph_insertion/strategies/ann_retrieval.py
+++ w/src/graph_insertion/strategies/ann_retrieval.py
@@ -270,16 +270,16 @@ class AnnRetrievalStrategy:
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
 
-        # Clear per-insertion cache on entry (D-55 / A-1) so a failed shortlist
-        # leaves no cached vector from an earlier successful shortlist
-        self._cached_new_name = None
-        self._cached_new_vec = None
-
         # Invalidate cached diagnostic overlap for previous query
         self._cached_exact_topk_overlap = None
 
```

### 7.2 `src/graph_insertion/strategies/embedding_threshold.py`
```diff
diff --git i/src/graph_insertion/strategies/embedding_threshold.py w/src/graph_insertion/strategies/embedding_threshold.py
index 5ead760..f34bb08 100644
--- i/src/graph_insertion/strategies/embedding_threshold.py
+++ w/src/graph_insertion/strategies/embedding_threshold.py
@@ -193,6 +193,11 @@ class EmbeddingThresholdStrategy:
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

### 7.3 `tests/test_ann_retrieval_strategy.py`
```diff
diff --git i/tests/test_ann_retrieval_strategy.py w/tests/test_ann_retrieval_strategy.py
index 2aab121..2bdc2ac 100644
--- i/tests/test_ann_retrieval_strategy.py
+++ w/tests/test_ann_retrieval_strategy.py
@@ -975,15 +975,31 @@ class TestMutationKillers:
 # ===========================================================================
 
 class _SelectiveFailingEmbedder:
-    """Local Embedder implementing protocol with failing vectors only for specified concepts."""
+    """Local Embedder implementing protocol with failing vectors or exceptions for specified concepts."""
 
-    def __init__(self, base_embedder: Embedder, fail_concept: str) -> None:
+    def __init__(
+        self,
+        base_embedder: Embedder,
+        fail_concept: str,
+        fail_mode: str = "zero_norm",
+    ) -> None:
         self.base = base_embedder
         self.fail_text = embed_text(fail_concept)
+        self.fail_mode = fail_mode
 
     def embed(self, text: str) -> np.ndarray:
         if text == self.fail_text:
-            return np.zeros(16, dtype=np.float32)
+            if self.fail_mode == "embedder_raises":
+                raise RuntimeError("Simulated embedder failure")
+            if self.fail_mode == "zero_norm":
+                return np.zeros(16, dtype=np.float32)
+            if self.fail_mode == "nan_vec":
+                vec = np.ones(16, dtype=np.float32)
+                vec[0] = np.nan
+                return vec
+            if self.fail_mode == "dim_mismatch":
+                return np.ones(8, dtype=np.float32)
+            raise ValueError(f"Unknown fail_mode: {self.fail_mode!r}")
         return self.base.embed(text)
 
     def embed_many(self, texts: Sequence[str]) -> np.ndarray:
@@ -991,12 +1007,35 @@ class _SelectiveFailingEmbedder:
 
 
 class TestPostReviewAmendments:
-    def test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector(self):
-        """Test T-1 (A-1 regression): failed shortlist clears per-insertion cache."""
+    # Note on C.2 (not-set-up check after earlier successful shortlist):
+    # Through the public API (__init__, setup, shortlist, on_inserted), a strategy
+    # cannot enter the not-set-up state while retaining a non-None cache from an
+    # earlier shortlist(), because setup() unconditionally clears _cached_new_name
+    # and _cached_new_vec at its entry before any setup failure can occur.
+    @pytest.mark.parametrize(
+        "fail_mode,bad_arg,exc_type,exc_match",
+        [
+            ("empty_name", "", ValueError, "cannot be empty"),
+            ("txt_suffix", "bad_node.txt", ValueError, r"cannot end in '\.txt'"),
+            ("embedder_raises", "failing_node", RuntimeError, "Simulated embedder failure"),
+            ("zero_norm", "failing_node", ValueError, "Zero-norm"),
+            ("nan_vec", "failing_node", ValueError, "non-finite"),
+            ("dim_mismatch", "failing_node", ValueError, "Dimension mismatch"),
+        ],
+    )
+    def test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector(
+        self,
+        fail_mode: str,
+        bad_arg: str,
+        exc_type: type[Exception],
+        exc_match: str,
+    ):
+        """Test T-1 (A-1 / D-58 regression): failed shortlist clears per-insertion cache on every path."""
         graph = ConceptGraph()
         graph.add_node("existing_node")
         base_emb = FakeEmbedder(dim=16, seed=42)
-        emb = _SelectiveFailingEmbedder(base_emb, "failing_node")
+        emb_mode = fail_mode if fail_mode in {"embedder_raises", "zero_norm", "nan_vec", "dim_mismatch"} else "zero_norm"
+        emb = _SelectiveFailingEmbedder(base_emb, "failing_node", fail_mode=emb_mode)
         strat = AnnRetrievalStrategy(k=5)
         strat.setup(graph, emb)
 
@@ -1006,11 +1045,11 @@ class TestPostReviewAmendments:
         assert strat._cached_new_name == "good_node"
         assert strat._cached_new_vec is not None
 
-        # 2. Failing shortlist("failing_node") raises ValueError
-        with pytest.raises(ValueError, match="Zero-norm"):
-            strat.shortlist("failing_node")
+        # 2. Failing shortlist(bad_arg) raises expected exception
+        with pytest.raises(exc_type, match=exc_match):
+            strat.shortlist(bad_arg)
 
-        # 3. Must leave NO cached vector from earlier successful shortlist
+        # 3. Must leave NO cached name or vector from earlier successful shortlist
         assert strat._cached_new_name is None
         assert strat._cached_new_vec is None
 
@@ -1021,12 +1060,12 @@ class TestPostReviewAmendments:
         # 5. After failed shortlist on a fresh strategy, on_inserted raises RuntimeError
         strat_fresh = AnnRetrievalStrategy(k=5)
         strat_fresh.setup(graph, emb)
-        with pytest.raises(ValueError, match="Zero-norm"):
-            strat_fresh.shortlist("failing_node")
+        with pytest.raises(exc_type, match=exc_match):
+            strat_fresh.shortlist(bad_arg)
         assert strat_fresh._cached_new_name is None
         assert strat_fresh._cached_new_vec is None
         with pytest.raises(RuntimeError, match="without matching shortlist"):
-            strat_fresh.on_inserted("failing_node", ())
+            strat_fresh.on_inserted(bad_arg or "good_node", ())
 
     def test_t2_setup_clears_cached_shortlist_vector(self):
         """Test T-2 (kills Mutation 15): setup() clears any previously cached shortlist vector."""
```

### 7.4 `tests/test_embedding_threshold_strategy.py`
```diff
diff --git i/tests/test_embedding_threshold_strategy.py w/tests/test_embedding_threshold_strategy.py
index 11f8679..8f645df 100644
--- i/tests/test_embedding_threshold_strategy.py
+++ w/tests/test_embedding_threshold_strategy.py
@@ -993,6 +993,74 @@ class TestValidationAndContracts:
         d2 = strat.diagnostics()
         assert d2["index_size"] == 4
 
+    # Note on C.2 (not-set-up check after earlier successful shortlist):
+    # Through the public API (__init__, setup, shortlist, on_inserted), a strategy
+    # cannot enter the not-set-up state while retaining a non-None cache from an
+    # earlier shortlist(), because setup() unconditionally clears _cached_new_name
+    # and _cached_new_vec at its entry before any setup failure can occur.
+    @pytest.mark.parametrize(
+        "fail_mode,bad_arg,exc_type,exc_match",
+        [
+            ("empty_name", "", ValueError, "cannot be empty"),
+            ("txt_suffix", "bad_node.txt", ValueError, r"cannot end in '\.txt'"),
+            ("embedder_raises", "failing_node", RuntimeError, "Simulated embedder failure"),
+            ("zero_norm", "failing_node", ValueError, "Zero-norm"),
+            ("nan_vec", "failing_node", ValueError, "non-finite"),
+            ("dim_mismatch", "failing_node", ValueError, "Dimension mismatch"),
+        ],
+    )
+    def test_shortlist_failure_clears_stale_cache(
+        self,
+        fail_mode: str,
+        bad_arg: str,
+        exc_type: type[Exception],
+        exc_match: str,
+    ):
+        """Test D-58: failed shortlist() clears stale _cached_new_name and _cached_new_vec on every path."""
+        base_emb = ControllableEmbedder(dim=8, seed=42)
+        fail_text = embed_text("failing_node")
+
+        class _SelectiveFailEmbedder:
+            def embed(self, text: str) -> np.ndarray:
+                if text == fail_text:
+                    if fail_mode == "embedder_raises":
+                        raise RuntimeError("Simulated embedder failure")
+                    if fail_mode == "zero_norm":
+                        return np.zeros(8, dtype=np.float32)
+                    if fail_mode == "nan_vec":
+                        vec = np.ones(8, dtype=np.float32)
+                        vec[0] = np.nan
+                        return vec
+                    if fail_mode == "dim_mismatch":
+                        return np.ones(4, dtype=np.float32)
+                return base_emb.embed(text)
+
+            def embed_many(self, texts: Sequence[str]) -> np.ndarray:
+                return base_emb.embed_many(texts)
+
+        graph = ConceptGraph(domain_context="cs")
+        graph.add_node("existing_node")
+
+        strat = EmbeddingThresholdStrategy(theta=0.6)
+        strat.setup(graph, _SelectiveFailEmbedder())
+
+        # 1. Successful shortlist("good_node") populates cache
+        strat.shortlist("good_node")
+        assert strat._cached_new_name == "good_node"
+        assert strat._cached_new_vec is not None
+
+        # 2. Failing shortlist(bad_arg) raises expected error
+        with pytest.raises(exc_type, match=exc_match):
+            strat.shortlist(bad_arg)
+
+        # 3. Both cache attributes must be cleared to None
+        assert strat._cached_new_name is None
+        assert strat._cached_new_vec is None
+
+        # 4. Subsequent on_inserted("good_node", ()) must raise RuntimeError
+        with pytest.raises(RuntimeError, match="without matching prior shortlist"):
+            strat.on_inserted("good_node", ())
+
 
 # ===========================================================================
 # 6. Harness Smoke Test
```

### 7.5 `docs/decisions/decision-log.md`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 1e4419b..dc01da5 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -446,3 +446,9 @@ Reasoning: resolves review defect F-1, improves approximation fidelity from $\ap
 (2) `results/datagen` guard fixture repair and lock-test handshake: removed the destructive cleanup loop in `guard_results_datagen_unmodified` (`tests/test_generate_name_pool.py`) that previously deleted 16-character timestamped directories under `results/datagen` before snapshotting, which masked stray directory creation by tests. The fixture is now strictly a read-only before/after recursive relative-path snapshot assertion. Updated the five CLI tests that previously wrote to `results/datagen` (`test_live_mode_refuses_without_confirm_and_without_key`, `test_offline_fake_refuses_default_output_path`, `test_command_backend_success_e2e`, `test_stop_and_resume_after_rate_limit`, and `test_cli_verify_merged_success_and_tampered_cache`) to keep all cache files, run directories, and lock directories under `tmp_path` without altering production defaults. Replaced the fixed `time.sleep(0.3)` in `test_profile_lock_mutual_exclusion` with a ready-file handshake (polling up to 5.0 s).
 (3) Historical note on [D-54]: [D-54](1) lists `test_results_datagen_unmodified_by_test_suite`, which FIX-014 replaced with the module-scoped autouse fixture `guard_results_datagen_unmodified`. Furthermore, [D-54] was rewritten in place in commit `8429122` after already being committed in `63cddfb`, so the original [D-54] text remains in git history at `63cddfb`. (Note: the FIX-015 prompt specified decision ID `D-55`, which was already assigned to STRAT-003-A in commit `ab7096d`, and `D-56` was reserved by the APC; `D-57` is used per operator instruction.)
 Reasoning: enables explicit thinking configuration (such as `sonnet-5` with `--adapter-thinking off`) with full cache and pool provenance and merge consistency checks, ensures `guard_results_datagen_unmodified` fails on any stray file or directory creation in `results/datagen`, eliminates a timing race in profile lock testing, and records the git history of [D-54]. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, DATA-005, DATA-006, FIX-014, FIX-015.
+
+**[D-58]** Strategy 2 and Strategy 3 stale-cache closure at `shortlist()` entry and Strategy 3 sensitivity plan (STRAT-003-B):
+(1) Correction to [D-55](1) and the Strategy 2 lifecycle of [D-46]/[D-50]: `shortlist()` of Strategies 2 (`EmbeddingThresholdStrategy`) and 3 (`AnnRetrievalStrategy`) clears `_cached_new_name = None` and `_cached_new_vec = None` as its first executable statements, before the not-set-up check, concept-name validation (`_validate_concept_name`), embedding, and vector validation. The wording "right after the not-set-up check and concept name validation" in [D-55](1) is superseded. A failed `shortlist()` now leaves no cached name or vector on every failure path. The stale-cache hole was unreachable through `insert_node` (which validates `new_name` at `strategy.py:260` before calling `shortlist()`), and is closed for defence in depth in direct strategy use. Any later strategy (including Strategy 4) must follow the same rule.
+(2) Strategy 3 sensitivity plan, superseding the `ef_search` part of [D-55](4): one-at-a-time sensitivity runs are locked at $k \in \{5, 20\}$ (with $\text{ef\_search} = 128$) and $\text{ef\_search} \in \{64, 256\}$ (with $k = 10$); the primary configuration remains $k = 10, \text{ef\_search} = 128$. The planned LLM call upper bound over the D-35 sweep matrix is 600 calls for each `ef_search` variant (independent of `ef_search`), 300 calls for $k = 5$, and 1,200 calls for $k = 20$. Run directories are keyed on `config()["k"]` and `config()["ef_search"]` (an INFRA-007 concern). Reasoning for adding $\text{ef\_search} = 256$: it provides the near-converged HNSW reference that thesis Section 3.2.4 promises ([D-55](2) measured $\approx 0.9990$ recall at 256 versus $\approx 0.9680$ at 128 on isotropic Gaussian vectors at $n = 2000$) at a bounded cost of at most 600 calls.
+(3) Test additions and unreachable-path findings: parametrised regression tests in `tests/test_ann_retrieval_strategy.py` (`test_t1_shortlist_cache_cleared_on_entry_failed_shortlist_leaves_no_cached_vector`) and `tests/test_embedding_threshold_strategy.py` (`test_shortlist_failure_clears_stale_cache`) verify that after an initial successful `shortlist("good_node")`, a subsequent `shortlist()` failing on an empty name (`""`), a `.txt`-suffixed name (`"bad_node.txt"`), an embedder exception, a zero-norm vector, a NaN vector, or a dimension-mismatch vector clears both `_cached_new_name` and `_cached_new_vec` to `None` and causes `on_inserted("good_node", ())` to raise `RuntimeError`. Reaching the not-set-up check in `shortlist()` with a populated cache from an earlier setup is unreachable through the public API because `setup()` unconditionally clears `_cached_new_name` and `_cached_new_vec` at entry before any setup failure can occur, making placement of the clear before versus immediately after the not-set-up check an equivalent mutant through the public API. Furthermore, in `tests/test_ann_retrieval_strategy.py`, `test_cached_embedding_reuse_single_embedding_per_insert` is inherited by `TestAnnRetrievalConformance` from `StrategyConformanceSuite` (`tests/test_strategy_interface.py:318`) and kills the `on_inserted` re-embedding mutation alongside `TestSingleEmbeddingInvariant` and `TestHarnessSmoke`.
+Reasoning: closes the latent stale-cache defect in direct `shortlist()` callers across both embedding strategies on all failure paths, locks the $\text{ef\_search} \in \{64, 256\}$ sensitivity sweep to pair with thesis Section 3.4, and documents public-API mutant equivalence for the pre-setup guard. Affects: `src/graph_insertion/strategies/ann_retrieval.py`, `src/graph_insertion/strategies/embedding_threshold.py`, `tests/test_ann_retrieval_strategy.py`, `tests/test_embedding_threshold_strategy.py`, `docs/decisions/decision-log.md`, `docs/reports/STRAT-003-B-gemini.md`, STRAT-002, STRAT-003, STRAT-004, INFRA-007.
```

---

## 8. Found But Not Changed

1. **`EmbeddingThresholdStrategy._shortlist_called` dead attribute (`src/graph_insertion/strategies/embedding_threshold.py:91, 122, 233`):** `[Confirmed]` Assigned `False` in `__init__` and `setup()` and `True` in `shortlist()`, but never read anywhere in the repository. Left untouched per Requirement 2.B.
2. **Last-query diagnostic state on failed `shortlist()`:** `[Confirmed]` In `EmbeddingThresholdStrategy`, `_last_comparisons`, `_last_shortlist_size`, and `_last_max_cosine` are only updated after embedding and vector validation succeed; in `AnnRetrievalStrategy`, `_cached_exact_topk_overlap = None` is cleared after `_validate_concept_name`, while `_last_shortlist_size` and `_last_max_cosine` remain from the prior query until a new search completes. Left untouched per Requirement 2.A/2.B.
3. **`docs/tasks/status.md`:** `[Confirmed]` Left untouched per Standing Rule 2 ("Do not edit `docs/tasks/status.md`; the APC relays status changes in a separate prompt").

---

## 9. Open Questions

- **[APC] Status transition for STRAT-003:** Once STRAT-003-B is reviewed/accepted, should `STRAT-003` in `docs/tasks/status.md` be transitioned from `**needs-review**` to `**done**` via the APC's status relay?
- **[APC-A] Thesis Section 3.4 sensitivity alignment:** Does thesis Section 3.4 already reflect the `ef_search` sensitivity pair $\{64, 256\}$ locked in `[D-58](2)` following commit `3a81e01`, or is any further wording update needed?
