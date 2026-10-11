# FIX-016 Report: Make Dry-Run Planner Use Each Strategy's Own Candidate Bound

## 1. Agent Identity

- **Agent**: `gemini`
- **Model label**: `unknown` (tool environment does not expose a specific model version tag in the system prompt)
- **Task ID**: `FIX-016`
- **Decision ID**: `[D-61]` (assigned per operator instruction because `[D-60]` was already committed for `DATA-007`)
- **Branch**: `master`

---

## 2. What Was Asked / What I Did

### What Was Asked
1. Verify all claims in the `FIX-016` prompt against the repository (`src/graph_insertion/harness.py`, `src/graph_insertion/strategy.py`, `scripts/run_experiment.py`, `src/graph_insertion/strategies/*`, and existing test files).
2. Update `estimate_and_print_plan()` in `src/graph_insertion/harness.py` to replace the `strategy.config().get("top_k", None)` lookup and its `min(..., top_k_bound) if top_k_bound else ...` expressions with `candidate_upper_bound(strategy, nodes_count - 1)` in accuracy mode and `candidate_upper_bound(strategy, sz)` in sweep mode, importing `candidate_upper_bound` from `graph_insertion.strategy`.
3. Keep all keys and types of the returned `plan` dictionary and each `details` entry, all printed line formats, the `n_existing` fallback for strategies without `max_candidates`, and `StubNarrowingStrategy` behavior unchanged.
4. Create `tests/test_dry_run_plan.py` covering:
   - Sweep plan over the D-35 matrix (`(50, 100, 200, 500, 1000, 2000)`, 10 trials per size) and small-size clamping across `BruteForceStrategy`, `EmbeddingThresholdStrategy`, `AnnRetrievalStrategy(k=5/10/20)`, `BoundedBucketStrategy((5,10)/(2,5)/(10,20))`, and `NullStrategy(k=1/5)`.
   - Accuracy plan with small fake corpora across all strategies, including per-corpus clamping when `nodes_count - 1 < cap`.
   - Exact parity with `compute_planned_calls_upper_bound` in `scripts/run_experiment.py`.
   - Unset-up probe strategy instances before `setup()`.
   - `StubNarrowingStrategy(top_k=5)` in `scripts/run_experiment.py`.
   - Regression failure output on the pre-fix `harness.py` before applying the fix, followed by the pass output after.
5. Run the 7-mutant self-check (`F-M1` through `F-M7`) on a `/tmp` copy against `tests/test_dry_run_plan.py`.
6. Append the decision entry (with no test counts) to `docs/decisions/decision-log.md`, add the `FIX-016` row (`needs-review`) to `docs/tasks/status.md`, and per explicit operator instruction at the end of the prompt (`commit after, create the patch also (patch/)`), commit the changes and generate the patch in `patch/`.

### What I Did
1. Verified all line numbers, strategy `config()` keys, `max_candidates(n_existing)` implementations before `setup()`, `CALLS_PER_CANDIDATE`, and existing dry-run tests across the repository.
2. Created `tests/test_dry_run_plan.py` (11 test methods across 4 test classes) while `src/graph_insertion/harness.py` was still unedited, and ran `.venv-ann/bin/python -m pytest -p no:sugar --tb=short tests/test_dry_run_plan.py` once to capture the pre-fix failures (8 failed, 3 passed).
3. Edited `src/graph_insertion/harness.py` to import `candidate_upper_bound` from `graph_insertion.strategy` and use `candidate_upper_bound(strategy, nodes_count - 1)` (accuracy) and `candidate_upper_bound(strategy, sz)` (sweep) inside `estimate_and_print_plan()`. No existing test file needed editing.
4. Verified `tests/test_dry_run_plan.py` (11 passed), ran the 7-mutant self-check `F-M1`..`F-M7` on a `/tmp` copy (7/7 KILLED), ran the existing dry-run-related test files (`tests/test_harness.py` and `tests/test_live_guard.py`, 43 passed), and ran the full test suite once (`581 passed, 3 skipped`).
5. Appended `[D-61]` to `docs/decisions/decision-log.md` and added the `FIX-016` row to `docs/tasks/status.md`.

---

## 3. Prompt Corrections

### Verified Right Claims
- **Pre-edit line numbers in `src/graph_insertion/harness.py`**:
  - `estimate_and_print_plan` starts at line `596`.
  - `top_k_bound = strategy.config().get("top_k", None)` was at line `621`.
  - Accuracy mode `max_cands = min(nodes_count - 1, top_k_bound) if top_k_bound else (nodes_count - 1)` was at line `640`.
  - Sweep mode `max_cands = min(sz, top_k_bound) if top_k_bound else sz` was at line `668`.
  - The two call sites of `estimate_and_print_plan` in `harness.py` were at lines `730` (`run_accuracy_experiment`) and `963` (`run_sweep_experiment`), both passing a freshly constructed `probe_strat = strategy_factory()` before `setup()`.
- **Strategy `config()` keys and `max_candidates(n_existing)` before `setup()`**:
  - `AnnRetrievalStrategy` (`src/graph_insertion/strategies/ann_retrieval.py`) uses `"k"` in `config()` (line 369) and defines `max_candidates(self, n_existing: int) -> int` at line 161 (`return max(0, min(self.k, n_existing))`), which only reads `self.k` and works before `setup()`.
  - `BoundedBucketStrategy` (`src/graph_insertion/strategies/bounded_bucket.py`) uses `"s_min"`, `"s_max"`, `"n_bits"`, `"seed"` in `config()` (line 618) and defines `max_candidates(self, n_existing: int) -> int` at line 192 (`return max(0, min(self.s_max, n_existing))`), which only reads `self.s_max` and works before `setup()`.
  - `BruteForceStrategy` (`src/graph_insertion/strategies/brute_force.py`) uses `{"seed": self.seed}` in `config()` and defines `max_candidates(self, n_existing: int) -> int` at line 88 (`return max(0, n_existing)`), working before `setup()`.
  - `EmbeddingThresholdStrategy` (`src/graph_insertion/strategies/embedding_threshold.py`) uses `{"theta": self.theta, "seed": self.seed}` in `config()` and does not define `max_candidates`, so `candidate_upper_bound` falls back to `n_existing`.
  - `StubNarrowingStrategy` (`scripts/run_experiment.py`) defines `max_candidates(self, n_existing: int) -> int` at line 103 (`return min(self.top_k, n_existing)`), working before `setup()`.
- **Live guard and `CALLS_PER_CANDIDATE`**:
  - `scripts/run_experiment.py` calls `candidate_upper_bound(strategy, n_existing)` at lines `296`, `313`, and `333` inside `compute_planned_calls_upper_bound()`, and multiplies by `CALLS_PER_CANDIDATE` (imported from `graph_insertion.decision` line 28, where `CALLS_PER_CANDIDATE: int = 1`).
  - `compute_planned_calls_upper_bound(config, corpora=..., strategy=...)` in `scripts/run_experiment.py` can be imported and driven completely offline.
- **No circular import**: `src/graph_insertion/harness.py` already imported `DecisionStep, InsertionMetrics, InsertionResult, NarrowingStrategy, insert_node` from `graph_insertion.strategy` at lines 43–49.
- **Baseline full-suite count**: Before `FIX-016` added `tests/test_dry_run_plan.py` (11 tests), the full suite on `master` was `570 passed, 3 skipped`, matching the prompt's statement (`570 + 11 = 581 passed, 3 skipped` after `FIX-016`).
- **Existing tests**: No existing test in `tests/test_null_strategy.py`, `tests/test_harness.py`, or `tests/test_live_guard.py` asserted the defective `top_k` behavior on a non-`top_k` strategy (`SpyStrategy` in `tests/test_harness.py` only asserts `plan["total_insertions"] == 4` in dry-run mode).

### Prompt Discrepancies / Additions Found
1. **Reserved Decision ID `D-60` already in use**: The prompt specified `D-60` ("Grep `docs/decisions/decision-log.md` first; if D-60 is already present, stop and report"). `D-60` was already present in `docs/decisions/decision-log.md` at line 467 (assigned to `DATA-007` in commit `7b36f95`). We stopped, reported this to Luke via `ask_question`, and were instructed to use **`[D-61]`** for `FIX-016`.
2. **`NullStrategy` was also affected by the old `"top_k"` lookup**: In addition to Strategies 3 and 4, `NullStrategy` (`src/graph_insertion/strategies/null.py`) returns `{"seed": self.seed, "k": self.k}` from `config()` (key `"k"`, not `"top_k"`) while defining `max_candidates(n_existing) -> min(self.k, n_existing)` at line 109. Thus the pre-fix `estimate_and_print_plan()` also treated `NullStrategy` as uncapped brute force (reporting 38,500 calls instead of 60 for `k=1` or 300 for `k=5` on the D-35 sweep matrix).
3. **`PYTHONPATH` vs `pyproject.toml` during `/tmp` mutation checks**: Because `pyproject.toml` sets `pythonpath = ["src"]`, pytest prepends the repository's `src/` ahead of `PYTHONPATH` unless `-o pythonpath=/tmp/.../src` is also passed on the pytest command line.
4. **Commit & patch instruction**: Standing rule 1 says "Leave all changes uncommitted and unstaged", whereas Luke appended `commit after, create the patch also (patch/)` at the end of the prompt. Per the explicit user instruction at the end of the prompt, we capture all required pre-commit `git diff` and `git status --short` outputs for this report first, and then commit and generate the patch in `patch/`.

---

## 4. Pre-Fix Failure Output

Before editing `src/graph_insertion/harness.py`, running `.venv-ann/bin/python -m pytest -p no:sugar --tb=short tests/test_dry_run_plan.py` against the unedited `harness.py` produced:

```text
$ .venv-ann/bin/python -m pytest -p no:sugar --tb=short tests/test_dry_run_plan.py
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collected 11 items

tests/test_dry_run_plan.py FF.FF.FF..F.                                  [100%]

=================================== FAILURES ===================================
_______ TestSweepDryRunPlan.test_d35_sweep_matrix_non_faiss_strategies _________
tests/test_dry_run_plan.py:92: in test_d35_sweep_matrix_non_faiss_strategies
    assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out
E   AssertionError: assert 'ESTIMATED UPPER-BOUND LLM CALLS: 600' in '======================================================================\nDRY RUN EXECUTION PLAN: SWEEP MODE\nStrategy: bounded_bucket\nStrategy Config: {\'s_min\': 5, \'s_max\': 10, \'n_bits\': 12, \'seed\': 42}\n======================================================================\nSize:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500\nSize:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000\nSize:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000\nSize:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000\nSize: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000\nSize: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000\n----------------------------------------------------------------------\nTOTAL PLANNED INSERTIONS: 60\nESTIMATED UPPER-BOUND LLM CALLS: 38500\n======================================================================\n'
___________ TestSweepDryRunPlan.test_d35_sweep_matrix_ann_retrieval ____________
tests/test_dry_run_plan.py:134: in test_d35_sweep_matrix_ann_retrieval
    assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out
E   AssertionError: assert 'ESTIMATED UPPER-BOUND LLM CALLS: 300' in '======================================================================\nDRY RUN EXECUTION PLAN: SWEEP MODE\nStrategy: ann_retrieval\nStrategy Config: {\'k\': 5, \'M\': 16, \'ef_construction\': 200, \'ef_search\': 128, \'metric\': \'inner_product_on_unit_vectors\', \'index\': \'IndexHNSWFlat\', \'faiss_threads\': 1, \'faiss_version\': \'1.15.1\', \'seed\': 42}\n======================================================================\nSize:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500\nSize:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000\nSize:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000\nSize:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000\nSize: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000\nSize: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000\n----------------------------------------------------------------------\nTOTAL PLANNED INSERTIONS: 60\nESTIMATED UPPER-BOUND LLM CALLS: 38500\n======================================================================\n'
_ TestSweepDryRunPlan.test_sweep_clamps_when_graph_size_smaller_than_strategy_cap _
tests/test_dry_run_plan.py:154: in test_sweep_clamps_when_graph_size_smaller_than_strategy_cap
    assert cands_by_size == {3: 3, 7: 7, 10: 10, 25: 10}
E   AssertionError: assert {3: 3, 7: 7, 10: 10, 25: 25} == {3: 3, 7: 7, 10: 10, 25: 10}
__ TestAccuracyDryRunPlan.test_accuracy_plan_non_faiss_strategies_and_clamping __
tests/test_dry_run_plan.py:196: in test_accuracy_plan_non_faiss_strategies_and_clamping
    assert plan["upper_bound_llm_calls"] == expected_total_llm
E   assert 308 == 244
____ TestAccuracyDryRunPlan.test_accuracy_plan_ann_retrieval_and_clamping ______
tests/test_dry_run_plan.py:243: in test_accuracy_plan_ann_retrieval_and_clamping
    assert plan["details"][0]["max_candidates_per_trial"] == expected_small
E   assert 6 == 5
__________ TestLiveGuardParity.test_parity_with_live_guard_non_faiss ___________
tests/test_dry_run_plan.py:280: in test_parity_with_live_guard_non_faiss
    assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound
E   assert 38500 == 300
E    +  where 300 = 300.full_plan_bound
________ TestLiveGuardParity.test_parity_with_live_guard_ann_retrieval _________
tests/test_dry_run_plan.py:316: in test_parity_with_live_guard_ann_retrieval
    assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound
E   assert 38500 == 300
E    +  where 300 = 300.full_plan_bound
_ TestUnsetupProbeAndFallbackStrategies.test_unsetup_ann_retrieval_probe_works_and_remains_unsetup _
tests/test_dry_run_plan.py:368: in test_unsetup_ann_retrieval_probe_works_and_remains_unsetup
    assert plan["upper_bound_llm_calls"] == 40
E   assert 120 == 40
=========================== short test summary info ============================
FAILED tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
FAILED tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_ann_retrieval
FAILED tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_sweep_clamps_when_graph_size_smaller_than_strategy_cap
FAILED tests/test_dry_run_plan.py::TestAccuracyDryRunPlan::test_accuracy_plan_non_faiss_strategies_and_clamping
FAILED tests/test_dry_run_plan.py::TestAccuracyDryRunPlan::test_accuracy_plan_ann_retrieval_and_clamping
FAILED tests/test_dry_run_plan.py::TestLiveGuardParity::test_parity_with_live_guard_non_faiss
FAILED tests/test_dry_run_plan.py::TestLiveGuardParity::test_parity_with_live_guard_ann_retrieval
FAILED tests/test_dry_run_plan.py::TestUnsetupProbeAndFallbackStrategies::test_unsetup_ann_retrieval_probe_works_and_remains_unsetup
========================= 8 failed, 3 passed in 1.05s ==========================
```

---

## 5. Verification Output

### 5a. Pre-Edit State (`git status --short`, `sha256sum`, `wc -l`, and `sed -n '595,695p' src/graph_insertion/harness.py`)

```text
$ git status --short
 M docs/context/repo-tree.txt

$ sha256sum src/graph_insertion/harness.py && wc -l src/graph_insertion/harness.py
e2187bbef0ef31f2d33e1a18b5ce54d4dc97e2a1d218614dbb3c78f74e5a076c  src/graph_insertion/harness.py
1195 src/graph_insertion/harness.py

$ sed -n '595,695p' src/graph_insertion/harness.py
def estimate_and_print_plan(
    config: HarnessConfig,
    strategy: NarrowingStrategy,
    *,
    corpora: Optional[dict[str, LoadedCorpus]] = None,
    name_source: Optional[SyntheticNameSource] = None,
) -> dict[str, Any]:
    """Compute and print dry-run execution plan and upper-bound LLM call estimates."""
    plan: dict[str, Any] = {
        "mode": config.mode,
        "strategy": strategy.name,
        "strategy_config": strategy.config(),
        "total_insertions": 0,
        "upper_bound_llm_calls": 0,
        "details": [],
    }

    print("=" * 70)
    print(f"DRY RUN EXECUTION PLAN: {config.mode.upper()} MODE")
    print(f"Strategy: {strategy.name}")
    print(f"Strategy Config: {strategy.config()}")
    print("=" * 70)

    # Estimate max candidate shortlist size per insertion
    # If strategy provides top_k in config, use it; otherwise worst-case is N-1
    top_k_bound = strategy.config().get("top_k", None)

    if config.mode == "accuracy":
        if corpora is None:
            corpora = {
                "DSA_gold_standard_MEKG": load_corpus("DSA"),
                "metacademy_gold_standard_MEKG": load_corpus("metacademy"),
            }

        total_trials = 0
        total_llm = 0

        for corpus_name, loaded_corpus in corpora.items():
            nodes_count = len(loaded_corpus.graph.nodes())
            if "metacademy" in corpus_name.lower():
                sample_k = min(config.metacademy_sample_size, nodes_count)
            else:
                sample_k = nodes_count
            trials = sample_k * config.repeats
            max_cands = min(nodes_count - 1, top_k_bound) if top_k_bound else (nodes_count - 1)
            max_llm = trials * max_cands

            plan["details"].append({
                "corpus": corpus_name,
                "nodes_in_graph": nodes_count,
                "sample_size": sample_k,
                "held_out_trials": trials,
                "max_candidates_per_trial": max_cands,
                "upper_bound_llm_calls": max_llm,
            })
            print(f"Corpus: {corpus_name} | Sample: {sample_k} (of {nodes_count}) | Trials: {trials} | Max LLM: {max_llm}")
            total_trials += trials
            total_llm += max_llm

        plan["total_insertions"] = total_trials
        plan["upper_bound_llm_calls"] = total_llm

    elif config.mode == "sweep":
        if name_source is None:
            raise ValueError("name_source must be provided for sweep dry run.")

        pool_size = len(name_source.names)
        total_trials = 0
        total_llm = 0

        for sz in config.sweep_sizes:
            trials = config.sweep_trials_per_size
            max_cands = min(sz, top_k_bound) if top_k_bound else sz
            max_llm = trials * max_cands
            total_trials += trials
            total_llm += max_llm
            plan["details"].append({
                "size": sz,
                "trials": trials,
                "max_candidates_per_trial": max_cands,
                "upper_bound_llm_calls": max_llm,
            })
            print(f"Size: {sz:4d} | Trials: {trials:2d} | Max Candidates: {max_cands:4d} | Max LLM Calls: {max_llm:6d}")

        plan["total_insertions"] = total_trials
        plan["upper_bound_llm_calls"] = total_llm

    print("-" * 70)
    print(f"TOTAL PLANNED INSERTIONS: {plan['total_insertions']}")
    print(f"ESTIMATED UPPER-BOUND LLM CALLS: {plan['upper_bound_llm_calls']}")
    print("=" * 70)
    return plan


# ===========================================================================
# Accuracy Runner
# ===========================================================================

def run_accuracy_experiment(
```

### 5b. Post-Fix: New Test File Alone (`tests/test_dry_run_plan.py`)

```text
$ .venv-ann/bin/python -m pytest -p no:sugar -v tests/test_dry_run_plan.py
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- /home/lukexodus/projects/llm-graph-insertion-complexity/.venv-ann/bin/python
cachedir: .pytest_cache
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 11 items

tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies PASSED [  9%]
tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_ann_retrieval PASSED [ 18%]
tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_sweep_clamps_when_graph_size_smaller_than_strategy_cap PASSED [ 27%]
tests/test_dry_run_plan.py::TestAccuracyDryRunPlan::test_accuracy_plan_non_faiss_strategies_and_clamping PASSED [ 36%]
tests/test_dry_run_plan.py::TestAccuracyDryRunPlan::test_accuracy_plan_ann_retrieval_and_clamping PASSED [ 45%]
tests/test_dry_run_plan.py::TestLiveGuardParity::test_parity_with_live_guard_non_faiss PASSED [ 54%]
tests/test_dry_run_plan.py::TestLiveGuardParity::test_parity_with_live_guard_ann_retrieval PASSED [ 63%]
tests/test_dry_run_plan.py::TestUnsetupProbeAndFallbackStrategies::test_unsetup_probe_strategies_work_and_remain_unsetup PASSED [ 72%]
tests/test_dry_run_plan.py::TestUnsetupProbeAndFallbackStrategies::test_unsetup_ann_retrieval_probe_works_and_remains_unsetup PASSED [ 81%]
tests/test_dry_run_plan.py::TestUnsetupProbeAndFallbackStrategies::test_stub_narrowing_strategy_top_k_cap_unchanged PASSED [ 90%]
tests/test_dry_run_plan.py::TestUnsetupProbeAndFallbackStrategies::test_strategy_without_max_candidates_falls_back_to_n_existing PASSED [100%]

============================== 11 passed in 0.29s ==============================
```

### 5c. Post-Fix: Existing Dry-Run-Related Tests (`tests/test_harness.py` and `tests/test_live_guard.py`)

```text
$ .venv-ann/bin/python -m pytest -p no:sugar -q tests/test_harness.py tests/test_live_guard.py
============================= test session starts ==============================
platform linux -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/lukexodus/projects/llm-graph-insertion-complexity
configfile: pyproject.toml
plugins: anyio-4.15.1, cov-7.1.0
collecting ... collected 43 items

tests/test_harness.py ................                                   [ 37%]
tests/test_live_guard.py ...........................                     [100%]

============================== 43 passed in 8.85s ==============================
```

### 5d. Post-Fix: Single Full-Suite Run (`| tail -3`), `sha256sum`, `wc -l`, and `git status --short`

```text
$ .venv-ann/bin/python -m pytest -p no:sugar -q | tail -3
.....                                                                    [100%]

================== 581 passed, 3 skipped in 200.40s (0:03:20) ==================

$ sha256sum src/graph_insertion/harness.py tests/test_dry_run_plan.py
0b71ead5a98e138b8888ad1e645cf17d360758d56cd43a06f7b71d3d8aad1fd5  src/graph_insertion/harness.py
a54ceeeb63161c2f171058c5355e14f4eddbe5a189d61b17f2c64d5943ed6830  tests/test_dry_run_plan.py

$ wc -l src/graph_insertion/harness.py tests/test_dry_run_plan.py
 1192 src/graph_insertion/harness.py
  435 tests/test_dry_run_plan.py
 1627 total

$ git status --short
 M docs/context/repo-tree.txt
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M src/graph_insertion/harness.py
?? tests/test_dry_run_plan.py
```

---

## 6. Mutation Table (`F-M1`..`F-M7`)

Each mutant was applied to a temporary copy of `src/graph_insertion/harness.py` under `/tmp` and executed with `.venv-ann/bin/python -m pytest -p no:sugar -o "pythonpath=<tmp_src> <repo>" -q --tb=no tests/test_dry_run_plan.py`:

| Mutant ID | Mutation Applied to `/tmp` Copy of `harness.py` | Result | Failing Test Count | Example Killer Test in `tests/test_dry_run_plan.py` |
| --- | --- | --- | --- | --- |
| `F-M1` | Restore the `strategy.config().get("top_k", None)` lookup in accuracy and sweep modes | **KILLED** | 8 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` |
| `F-M2` | Use `candidate_upper_bound(strategy, nodes_count)` instead of `nodes_count - 1` in accuracy mode | **KILLED** | 6 / 11 | `TestAccuracyDryRunPlan::test_accuracy_plan_non_faiss_strategies_and_clamping` |
| `F-M3` | Use `sz + 1` / drop the clamp in sweep mode (`strategy.max_candidates(sz + 1) if hasattr(...) else (sz + 1)`) | **KILLED** | 5 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` (and `test_sweep_clamps_when_graph_size_smaller_than_strategy_cap`) |
| `F-M4` | Swap the `accuracy` and `sweep` mode branches in `estimate_and_print_plan` | **KILLED** | 11 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` |
| `F-M5` | Hard-code `min(10, nodes_count - 1)` and `min(10, sz)` | **KILLED** | 8 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` |
| `F-M6` | Return `0` for strategies lacking `max_candidates` (`if hasattr(strategy, "max_candidates") else 0`) | **KILLED** | 4 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` (and `test_strategy_without_max_candidates_falls_back_to_n_existing`) |
| `F-M7` | Drop `total_llm += max_llm` accumulation in sweep mode | **KILLED** | 8 / 11 | `TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies` |

Verbatim output of the mutation runner:

```text
F-M1 (restore top_k lookup): KILLED (rc=1, failed=8) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
F-M2 (use nodes_count instead of nodes_count - 1 in accuracy mode): KILLED (rc=1, failed=6) -> tests/test_dry_run_plan.py::TestAccuracyDryRunPlan::test_accuracy_plan_non_faiss_strategies_and_clamping
F-M3 (use sz + 1 / drop clamp in sweep mode): KILLED (rc=1, failed=5) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
F-M4 (swap accuracy and sweep mode branches): KILLED (rc=1, failed=11) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
F-M5 (hard-code min(10, n_existing)): KILLED (rc=1, failed=8) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
F-M6 (return 0 for strategies lacking max_candidates): KILLED (rc=1, failed=4) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
F-M7 (drop total_llm accumulation in sweep mode): KILLED (rc=1, failed=8) -> tests/test_dry_run_plan.py::TestSweepDryRunPlan::test_d35_sweep_matrix_non_faiss_strategies
```

---

## 7. Diffs

### 7a. `git diff src/graph_insertion/harness.py`

```diff
diff --git i/src/graph_insertion/harness.py w/src/graph_insertion/harness.py
index 94c6494..c9dcbc6 100644
--- i/src/graph_insertion/harness.py
+++ w/src/graph_insertion/harness.py
@@ -45,6 +45,7 @@ from graph_insertion.strategy import (
     InsertionMetrics,
     InsertionResult,
     NarrowingStrategy,
+    candidate_upper_bound,
     insert_node,
 )
 
@@ -616,10 +617,6 @@ def estimate_and_print_plan(
     print(f"Strategy Config: {strategy.config()}")
     print("=" * 70)
 
-    # Estimate max candidate shortlist size per insertion
-    # If strategy provides top_k in config, use it; otherwise worst-case is N-1
-    top_k_bound = strategy.config().get("top_k", None)
-
     if config.mode == "accuracy":
         if corpora is None:
             corpora = {
@@ -637,7 +634,7 @@ def estimate_and_print_plan(
             else:
                 sample_k = nodes_count
             trials = sample_k * config.repeats
-            max_cands = min(nodes_count - 1, top_k_bound) if top_k_bound else (nodes_count - 1)
+            max_cands = candidate_upper_bound(strategy, nodes_count - 1)
             max_llm = trials * max_cands
 
             plan["details"].append({
@@ -665,7 +662,7 @@ def estimate_and_print_plan(
 
         for sz in config.sweep_sizes:
             trials = config.sweep_trials_per_size
-            max_cands = min(sz, top_k_bound) if top_k_bound else sz
+            max_cands = candidate_upper_bound(strategy, sz)
             max_llm = trials * max_cands
             total_trials += trials
             total_llm += max_llm
```

### 7b. `git diff docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 4174a98..610e9e9 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -474,3 +474,9 @@ Reasoning: provides a deterministic, O(log M)-lookup, zero-extra-dependency impl
 (7) Tests added: `tests/test_name_pool_supervisor.py` adds 11 offline integration tests using `tests/stub_prompt_adapter.py` and `tmp_path` (`test_happy_path_two_shards_merged_and_verified`, `test_failover_on_rate_limit_to_spare_profile`, `test_profile_in_use_rotates_to_next_profile_with_short_cooldown`, `test_all_profiles_cooling_stalled_exit_caches_intact`, `test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches`, `test_sigterm_propagation_kills_children_and_exits_130`, `test_max_total_calls_stops_all_shards`, `test_status_cli_read_only`, `test_refusal_without_live_and_confirm`, `test_dry_run_prints_plan_and_launches_nothing`, `test_loader_value_error_stops_everything`) guarded by the module-scoped autouse fixture `guard_results_datagen_unmodified`. Every test was verified to fail when its corresponding line in `scripts/name_pool_supervisor.py` is mutated. (Note: the DATA-007 prompt specified `D-58`, which was already used by STRAT-003-B, and `D-59` was used by STRAT-004; `D-60` is used per operator instruction.)
 Reasoning: provides unattended multi-shard execution with automatic spare-profile failover on claude.ai usage limits and profile locks, full process-tree cleanup across child sessions, atomic status telemetry, and automatic post-shard merge and verification without modifying `generate_name_pool.py` or `claude-automator`. Affects: `scripts/name_pool_supervisor.py`, `tests/test_name_pool_supervisor.py`, `tests/stub_prompt_adapter.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/DATA-007-gemini-name-pool-supervisor.md`, DATA-006, DATA-007.
 
+**[D-61]** Strategy-aware candidate upper bound in dry-run planner `estimate_and_print_plan` (FIX-016):
+(1) The defect and where it was: `estimate_and_print_plan()` in `src/graph_insertion/harness.py` looked up a strategy's candidate cap via `strategy.config().get("top_k", None)` and clamped `nodes_count - 1` (accuracy mode) or `sz` (sweep mode) against `top_k_bound`. However, Strategy 3 (`AnnRetrievalStrategy`) names its cap `"k"` in `config()`, Strategy 4 (`BoundedBucketStrategy`) names its cap `"s_max"`, and `NullStrategy` also names its cap `"k"`. Because none of those strategies exposes a `"top_k"` config key, `estimate_and_print_plan()` treated them as uncapped brute force and overstated their planned LLM call bounds (for example, reporting 38,500 calls instead of 600 over the D-35 sweep matrix for Strategy 3 at $k = 10$ and Strategy 4 at $s_{\max} = 10$). The defect was display-only: the live guard in `scripts/run_experiment.py` (`compute_planned_calls_upper_bound`) already used `candidate_upper_bound(strategy, n_existing)` from `src/graph_insertion/strategy.py` ([D-41](1)), which delegates to `strategy.max_candidates(n_existing)` when defined and clamps to `[0, n_existing]`, falling back to `n_existing` otherwise.
+(2) The change: `estimate_and_print_plan()` in `src/graph_insertion/harness.py` removes the `strategy.config().get("top_k", None)` lookup and instead computes `max_cands = candidate_upper_bound(strategy, nodes_count - 1)` in accuracy mode and `max_cands = candidate_upper_bound(strategy, sz)` in sweep mode (`CALLS_PER_CANDIDATE == 1`, matching `compute_planned_calls_upper_bound`). Every key of the returned `plan` dictionary (`mode`, `strategy`, `strategy_config`, `total_insertions`, `upper_bound_llm_calls`, `details`) and each `details` entry, all printed line formats, the `n_existing` fallback for strategies without `max_candidates` (`EmbeddingThresholdStrategy`), and `StubNarrowingStrategy` (`max_candidates(n_existing) -> min(self.top_k, n_existing)`) remain unchanged. Every strategy in `src/graph_insertion/strategies/` (`BruteForceStrategy`, `EmbeddingThresholdStrategy`, `AnnRetrievalStrategy`, `BoundedBucketStrategy`, `NullStrategy`) works with `candidate_upper_bound` before `setup()` is called on the probe strategy instance.
+(3) Consequence for planned budgets over the D-35 sweep matrix (`sweep_sizes = (50, 100, 200, 500, 1000, 2000)`, `sweep_trials_per_size = 10`, 60 total insertions): `BruteForceStrategy` plans 38,500 LLM calls; Strategy 2 (`EmbeddingThresholdStrategy`) remains uncapped at 38,500 calls (no `max_candidates`); Strategy 3 (`AnnRetrievalStrategy`) plans 600 calls at primary $k = 10$ (300 at $k = 5$, 1,200 at $k = 20$); Strategy 4 (`BoundedBucketStrategy`) plans 600 calls at primary $(s_{\min}, s_{\max}) = (5, 10)$ (300 at $(2, 5)$, 1,200 at $(10, 20)$); and `NullStrategy` plans 60 calls at $k = 1$ (300 at $k = 5$). Any earlier dry-run printouts saved for Strategies 3 and 4 (or `NullStrategy`) prior to this fix overstated the planned LLM call upper bound.
+(4) Tests added: `tests/test_dry_run_plan.py` adds offline unit tests covering the D-35 sweep matrix and small-size clamping across all strategies, accuracy-mode candidate bounds and per-corpus clamping, exact parity with `compute_planned_calls_upper_bound` in `scripts/run_experiment.py`, pre-`setup()` probe strategy invariance, `StubNarrowingStrategy(top_k=5)` compatibility, and the uncapped `n_existing` fallback for strategies without `max_candidates`. (Note: the FIX-016 prompt specified decision ID `D-60`, which was already assigned to DATA-007; `D-61` is used per operator instruction.)
+Reasoning: aligns the dry-run execution planner with the live pre-flight guard by delegating candidate upper-bound computation to `candidate_upper_bound(strategy, n_existing)` instead of inspecting a strategy-specific `"top_k"` config key. Affects: `src/graph_insertion/harness.py`, `tests/test_dry_run_plan.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/FIX-016-gemini-dry-run-planner.md`, INFRA-004, INFRA-005, FIX-009, FIX-016, STRAT-003, STRAT-004.
```

### 7c. `git diff docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index a9f0c9e..4349689 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -89,5 +89,6 @@ Status: **not started** (blocked on Phase 3)
 | FIX-013 | Repair and test DATA-006 (shard orchestration for the name-pool generator): fix 8 defects (verify crashes on merge_run_ids/dict sha256; shards overwrite tracked pool; lock paths in ShardLockManager; bounded pipe drain after SIGKILL; merged meta fidelity; adapter error 15 mapping to exit 7; illustrative model mismatch fixture; corpus_overlap_embed assertion); add 14 unit/integration tests; Contract v1.1 ([D-54]). | **needs-review** | Completed by Gemini. All 41 generator tests passing; full test suite 394 passing, 3 skipped. See report [`docs/reports/FIX-013-gemini-repair-data-006.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-013-gemini-repair-data-006.md). |
 | FIX-014 | Finish FIX-013: rewrite D-54 in place to remove unsupported claims, close 6 test gaps (merged verify success and tampered cache, recursive results/datagen fixture, profile-lock exclusion, prompt-version-only mismatch, merged meta fidelity, exit-7 cache sha256 preservation), and correct status rows ([D-54]). | **needs-review** | Completed by Gemini. See report [`docs/reports/FIX-014-gemini-finish-fix-013.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-014-gemini-finish-fix-013.md). |
 | FIX-015 | Explicit `--adapter-thinking {auto,on,off}` control for `generate_name_pool.py` (payload, dry-run, shard commands, cache `thinking_requested`, pool `requested_thinking`, mixed-thinking merge refusal), repair `guard_results_datagen_unmodified` fixture by removing destructive cleanup loop and isolating CLI tests to `tmp_path`, replace `sleep` with ready-file handshake in `test_profile_lock_mutual_exclusion` ([D-57]). | **needs-review** | Completed by Gemini. 47 generator tests passing; full test suite 400 passing, 4 skipped. See report [`docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-015-gemini-adapter-thinking-and-fixture-repair.md). |
+| FIX-016 | Make `estimate_and_print_plan()` in `src/graph_insertion/harness.py` use `candidate_upper_bound(strategy, n_existing)` instead of `strategy.config().get("top_k", None)` so dry-run plans for Strategies 3 (`k`), 4 (`s_max`), and `NullStrategy` (`k`) match the live guard `compute_planned_calls_upper_bound`; add unit and parity tests in `tests/test_dry_run_plan.py` ([D-61]). | **needs-review** | Completed by Gemini. 11 dry-run planner tests passing; full test suite 581 passing, 3 skipped. See report [`docs/reports/FIX-016-gemini-dry-run-planner.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-016-gemini-dry-run-planner.md). |
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
```

### 7d. `diff -u /dev/null tests/test_dry_run_plan.py`

```diff
--- /dev/null	2026-10-10 17:19:57.996000018 +0800
+++ tests/test_dry_run_plan.py	2026-10-11 22:07:20.000000000 +0800
@@ -0,0 +1,435 @@
+"""
+test_dry_run_plan.py — FIX-016 Unit Tests
+=========================================
+Tests for estimate_and_print_plan() candidate upper bound calculation:
+  1. Sweep plan over the D-35 matrix across all strategies (BruteForce,
+     EmbeddingThreshold, AnnRetrieval, BoundedBucket, NullStrategy) and
+     clamping when sweep size < cap.
+  2. Accuracy plan with small fake corpora across all strategies, including
+     per-corpus clamping when (nodes_count - 1) < cap.
+  3. Parity between estimate_and_print_plan() and live guard
+     compute_planned_calls_upper_bound() in scripts/run_experiment.py.
+  4. Probe strategy instances work before setup() without mutating state.
+  5. StubNarrowingStrategy(top_k=5) preserves min(5, n) cap behavior.
+  6. Strategies without max_candidates fall back to n_existing.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any
+import pytest
+
+from graph_insertion.graph_representation import ConceptGraph
+from graph_insertion.harness import (
+    HarnessConfig,
+    SyntheticNameSource,
+    estimate_and_print_plan,
+)
+from graph_insertion.strategies.brute_force import BruteForceStrategy
+from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
+from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
+from graph_insertion.strategies.null import NullStrategy
+from graph_insertion.strategy import Shortlist, candidate_upper_bound
+from scripts.run_experiment import (
+    StubNarrowingStrategy,
+    compute_planned_calls_upper_bound,
+)
+
+
+D35_SWEEP_SIZES: tuple[int, ...] = (50, 100, 200, 500, 1000, 2000)
+D35_TRIALS_PER_SIZE: int = 10
+
+
+@dataclass
+class _FakeLoadedCorpus:
+    """Lightweight corpus stub exposing .graph.nodes() for accuracy dry-run tests."""
+
+    graph: ConceptGraph
+
+
+def _make_fake_corpus(n_nodes: int) -> _FakeLoadedCorpus:
+    graph = ConceptGraph(domain_context="testing")
+    for i in range(n_nodes):
+        graph.add_node(f"node_{i:03d}")
+    return _FakeLoadedCorpus(graph=graph)
+
+
+def _make_name_source(n: int = 32) -> SyntheticNameSource:
+    return SyntheticNameSource(
+        names=[f"concept_{i:04d}" for i in range(n)],
+        domain_context="computer science",
+    )
+
+
+class TestSweepDryRunPlan:
+    """Verify sweep dry-run candidate and LLM call bounds across strategies."""
+
+    def test_d35_sweep_matrix_non_faiss_strategies(self, capsys: pytest.CaptureFixture[str]) -> None:
+        config = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=D35_SWEEP_SIZES,
+            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
+            dry_run=True,
+        )
+        source = _make_name_source()
+
+        cases: list[tuple[Any, int]] = [
+            (BruteForceStrategy(), 38_500),
+            (EmbeddingThresholdStrategy(theta=0.45), 38_500),
+            (BoundedBucketStrategy(s_min=5, s_max=10), 600),
+            (BoundedBucketStrategy(s_min=2, s_max=5), 300),
+            (BoundedBucketStrategy(s_min=10, s_max=20), 1_200),
+            (NullStrategy(k=1), 60),
+            (NullStrategy(k=5), 300),
+        ]
+
+        for strategy, expected_calls in cases:
+            plan = estimate_and_print_plan(config, strategy, name_source=source)
+            out = capsys.readouterr().out
+            assert f"Strategy: {strategy.name}" in out
+            assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out
+
+            assert set(plan.keys()) == {
+                "mode",
+                "strategy",
+                "strategy_config",
+                "total_insertions",
+                "upper_bound_llm_calls",
+                "details",
+            }
+            assert plan["mode"] == "sweep"
+            assert plan["strategy"] == strategy.name
+            assert plan["strategy_config"] == strategy.config()
+            assert plan["total_insertions"] == 60
+            assert plan["upper_bound_llm_calls"] == expected_calls
+            assert len(plan["details"]) == len(D35_SWEEP_SIZES)
+
+            for detail, sz in zip(plan["details"], D35_SWEEP_SIZES):
+                expected_cands = candidate_upper_bound(strategy, sz)
+                assert detail == {
+                    "size": sz,
+                    "trials": D35_TRIALS_PER_SIZE,
+                    "max_candidates_per_trial": expected_cands,
+                    "upper_bound_llm_calls": D35_TRIALS_PER_SIZE * expected_cands,
+                }
+
+    def test_d35_sweep_matrix_ann_retrieval(self, capsys: pytest.CaptureFixture[str]) -> None:
+        pytest.importorskip("faiss")
+        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+
+        config = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=D35_SWEEP_SIZES,
+            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
+            dry_run=True,
+        )
+        source = _make_name_source()
+
+        for k, expected_calls in [(5, 300), (10, 600), (20, 1_200)]:
+            strategy = AnnRetrievalStrategy(k=k)
+            plan = estimate_and_print_plan(config, strategy, name_source=source)
+            out = capsys.readouterr().out
+            assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_calls}" in out
+            assert plan["total_insertions"] == 60
+            assert plan["upper_bound_llm_calls"] == expected_calls
+            for detail, sz in zip(plan["details"], D35_SWEEP_SIZES):
+                assert detail["max_candidates_per_trial"] == k
+                assert detail["upper_bound_llm_calls"] == D35_TRIALS_PER_SIZE * k
+
+    def test_sweep_clamps_when_graph_size_smaller_than_strategy_cap(self) -> None:
+        config = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=(3, 7, 10, 25),
+            sweep_trials_per_size=4,
+            dry_run=True,
+        )
+        source = _make_name_source()
+        strategy = BoundedBucketStrategy(s_min=5, s_max=10)
+
+        plan = estimate_and_print_plan(config, strategy, name_source=source)
+        cands_by_size = {d["size"]: d["max_candidates_per_trial"] for d in plan["details"]}
+        assert cands_by_size == {3: 3, 7: 7, 10: 10, 25: 10}
+        assert plan["upper_bound_llm_calls"] == 4 * (3 + 7 + 10 + 10)
+
+
+class TestAccuracyDryRunPlan:
+    """Verify accuracy dry-run candidate and LLM call bounds across strategies."""
+
+    def test_accuracy_plan_non_faiss_strategies_and_clamping(self) -> None:
+        # small_corpus has 7 nodes -> n_existing = 6 (clamps s_max=10 and s_max=20 to 6)
+        # metacademy_mini has 15 nodes -> n_existing = 14, sampled at 8 nodes
+        corpora: dict[str, Any] = {
+            "small_corpus": _make_fake_corpus(7),
+            "metacademy_mini": _make_fake_corpus(15),
+        }
+        config = HarnessConfig(
+            mode="accuracy",
+            repeats=2,
+            metacademy_sample_size=8,
+            dry_run=True,
+        )
+
+        strategies: list[Any] = [
+            BruteForceStrategy(),
+            EmbeddingThresholdStrategy(theta=0.45),
+            BoundedBucketStrategy(s_min=5, s_max=10),
+            BoundedBucketStrategy(s_min=2, s_max=5),
+            BoundedBucketStrategy(s_min=10, s_max=20),
+            NullStrategy(k=1),
+            NullStrategy(k=5),
+        ]
+
+        for strategy in strategies:
+            plan = estimate_and_print_plan(config, strategy, corpora=corpora)
+            # small_corpus: sample_k = 7, trials = 14, n_existing = 6
+            # metacademy_mini: sample_k = 8, trials = 16, n_existing = 14
+            expected_small_cands = candidate_upper_bound(strategy, 6)
+            expected_meta_cands = candidate_upper_bound(strategy, 14)
+            expected_total_llm = 14 * expected_small_cands + 16 * expected_meta_cands
+
+            assert plan["mode"] == "accuracy"
+            assert plan["total_insertions"] == 30
+            assert plan["upper_bound_llm_calls"] == expected_total_llm
+            assert len(plan["details"]) == 2
+
+            d_small, d_meta = plan["details"]
+            assert d_small == {
+                "corpus": "small_corpus",
+                "nodes_in_graph": 7,
+                "sample_size": 7,
+                "held_out_trials": 14,
+                "max_candidates_per_trial": expected_small_cands,
+                "upper_bound_llm_calls": 14 * expected_small_cands,
+            }
+            assert d_meta == {
+                "corpus": "metacademy_mini",
+                "nodes_in_graph": 15,
+                "sample_size": 8,
+                "held_out_trials": 16,
+                "max_candidates_per_trial": expected_meta_cands,
+                "upper_bound_llm_calls": 16 * expected_meta_cands,
+            }
+
+        # Explicit clamp check on BoundedBucketStrategy(5, 10): n_existing=6 < s_max=10
+        bb_plan = estimate_and_print_plan(
+            config, BoundedBucketStrategy(s_min=5, s_max=10), corpora=corpora
+        )
+        assert bb_plan["details"][0]["max_candidates_per_trial"] == 6
+        assert bb_plan["details"][1]["max_candidates_per_trial"] == 10
+        assert bb_plan["upper_bound_llm_calls"] == 14 * 6 + 16 * 10
+
+    def test_accuracy_plan_ann_retrieval_and_clamping(self) -> None:
+        pytest.importorskip("faiss")
+        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+
+        corpora: dict[str, Any] = {
+            "small_corpus": _make_fake_corpus(7),
+            "metacademy_mini": _make_fake_corpus(15),
+        }
+        config = HarnessConfig(
+            mode="accuracy",
+            repeats=2,
+            metacademy_sample_size=8,
+            dry_run=True,
+        )
+
+        for k, expected_small, expected_meta in [(5, 5, 5), (10, 6, 10), (20, 6, 14)]:
+            strategy = AnnRetrievalStrategy(k=k)
+            plan = estimate_and_print_plan(config, strategy, corpora=corpora)
+            assert plan["details"][0]["max_candidates_per_trial"] == expected_small
+            assert plan["details"][1]["max_candidates_per_trial"] == expected_meta
+            assert plan["upper_bound_llm_calls"] == 14 * expected_small + 16 * expected_meta
+
+
+class TestLiveGuardParity:
+    """Verify dry-run planner upper_bound_llm_calls matches compute_planned_calls_upper_bound."""
+
+    def test_parity_with_live_guard_non_faiss(self) -> None:
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=D35_SWEEP_SIZES,
+            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
+            dry_run=True,
+        )
+        acc_cfg = HarnessConfig(
+            mode="accuracy",
+            repeats=2,
+            metacademy_sample_size=8,
+            dry_run=True,
+        )
+        corpora: dict[str, Any] = {
+            "small_corpus": _make_fake_corpus(7),
+            "metacademy_mini": _make_fake_corpus(15),
+        }
+        source = _make_name_source()
+
+        strategies: list[Any] = [
+            BruteForceStrategy(),
+            EmbeddingThresholdStrategy(theta=0.45),
+            BoundedBucketStrategy(s_min=2, s_max=5),
+            BoundedBucketStrategy(s_min=5, s_max=10),
+            BoundedBucketStrategy(s_min=10, s_max=20),
+            NullStrategy(k=1),
+            NullStrategy(k=5),
+        ]
+
+        for strategy in strategies:
+            sweep_plan = estimate_and_print_plan(sweep_cfg, strategy, name_source=source)
+            sweep_guard = compute_planned_calls_upper_bound(sweep_cfg, strategy=strategy)
+            assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound
+            assert sweep_plan["total_insertions"] == sweep_guard.full_plan_trials
+
+            acc_plan = estimate_and_print_plan(acc_cfg, strategy, corpora=corpora)
+            acc_guard = compute_planned_calls_upper_bound(
+                acc_cfg, corpora=corpora, strategy=strategy
+            )
+            assert acc_plan["upper_bound_llm_calls"] == acc_guard.full_plan_bound
+            assert acc_plan["total_insertions"] == acc_guard.full_plan_trials
+
+    def test_parity_with_live_guard_ann_retrieval(self) -> None:
+        pytest.importorskip("faiss")
+        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=D35_SWEEP_SIZES,
+            sweep_trials_per_size=D35_TRIALS_PER_SIZE,
+            dry_run=True,
+        )
+        acc_cfg = HarnessConfig(
+            mode="accuracy",
+            repeats=2,
+            metacademy_sample_size=8,
+            dry_run=True,
+        )
+        corpora: dict[str, Any] = {
+            "small_corpus": _make_fake_corpus(7),
+            "metacademy_mini": _make_fake_corpus(15),
+        }
+        source = _make_name_source()
+
+        for k in (5, 10, 20):
+            strategy = AnnRetrievalStrategy(k=k)
+            sweep_plan = estimate_and_print_plan(sweep_cfg, strategy, name_source=source)
+            sweep_guard = compute_planned_calls_upper_bound(sweep_cfg, strategy=strategy)
+            assert sweep_plan["upper_bound_llm_calls"] == sweep_guard.full_plan_bound
+
+            acc_plan = estimate_and_print_plan(acc_cfg, strategy, corpora=corpora)
+            acc_guard = compute_planned_calls_upper_bound(
+                acc_cfg, corpora=corpora, strategy=strategy
+            )
+            assert acc_plan["upper_bound_llm_calls"] == acc_guard.full_plan_bound
+
+
+class TestUnsetupProbeAndFallbackStrategies:
+    """Verify probe strategies before setup(), StubNarrowingStrategy, and no-max_candidates fallback."""
+
+    def test_unsetup_probe_strategies_work_and_remain_unsetup(self) -> None:
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=(10, 50),
+            sweep_trials_per_size=2,
+            dry_run=True,
+        )
+        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
+        corpora: dict[str, Any] = {"mini": _make_fake_corpus(6)}
+        source = _make_name_source()
+
+        probes: list[Any] = [
+            BruteForceStrategy(),
+            EmbeddingThresholdStrategy(),
+            BoundedBucketStrategy(s_min=5, s_max=10),
+            NullStrategy(k=5),
+        ]
+        for probe in probes:
+            assert getattr(probe, "_setup_called", False) is False
+            assert getattr(probe, "_graph", None) is None
+            estimate_and_print_plan(sweep_cfg, probe, name_source=source)
+            estimate_and_print_plan(acc_cfg, probe, corpora=corpora)
+            assert getattr(probe, "_setup_called", False) is False
+            assert getattr(probe, "_graph", None) is None
+
+    def test_unsetup_ann_retrieval_probe_works_and_remains_unsetup(self) -> None:
+        pytest.importorskip("faiss")
+        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+
+        probe = AnnRetrievalStrategy(k=10)
+        assert probe._setup_called is False
+        assert probe._index is None
+
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=(10, 50),
+            sweep_trials_per_size=2,
+            dry_run=True,
+        )
+        plan = estimate_and_print_plan(sweep_cfg, probe, name_source=_make_name_source())
+        assert plan["upper_bound_llm_calls"] == 40
+        assert probe._setup_called is False
+        assert probe._index is None
+
+    def test_stub_narrowing_strategy_top_k_cap_unchanged(self) -> None:
+        stub = StubNarrowingStrategy(top_k=5)
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=(3, 5, 10, 50),
+            sweep_trials_per_size=2,
+            dry_run=True,
+        )
+        sweep_plan = estimate_and_print_plan(
+            sweep_cfg, stub, name_source=_make_name_source()
+        )
+        assert [d["max_candidates_per_trial"] for d in sweep_plan["details"]] == [3, 5, 5, 5]
+        assert sweep_plan["upper_bound_llm_calls"] == 2 * (3 + 5 + 5 + 5)
+
+        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
+        corpora: dict[str, Any] = {
+            "tiny": _make_fake_corpus(4),   # n_existing = 3 -> min(5, 3) = 3
+            "medium": _make_fake_corpus(9), # n_existing = 8 -> min(5, 8) = 5
+        }
+        acc_plan = estimate_and_print_plan(acc_cfg, stub, corpora=corpora)
+        assert [d["max_candidates_per_trial"] for d in acc_plan["details"]] == [3, 5]
+        assert acc_plan["upper_bound_llm_calls"] == 4 * 3 + 9 * 5
+
+    def test_strategy_without_max_candidates_falls_back_to_n_existing(self) -> None:
+        class NoCapStrategy:
+            name = "no_cap_custom"
+            uses_embeddings = False
+
+            def setup(self, graph: Any, embedder: Any) -> None:
+                pass
+
+            def shortlist(self, new_name: str) -> Shortlist:
+                return Shortlist(candidates=())
+
+            def on_inserted(self, new_name: str, edges: Any) -> None:
+                pass
+
+            def config(self) -> dict[str, Any]:
+                return {}
+
+            def diagnostics(self) -> dict[str, Any]:
+                return {}
+
+        strat = NoCapStrategy()
+        assert not hasattr(strat, "max_candidates")
+        assert not hasattr(EmbeddingThresholdStrategy(), "max_candidates")
+
+        sweep_cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=(12, 25),
+            sweep_trials_per_size=3,
+            dry_run=True,
+        )
+        sweep_plan = estimate_and_print_plan(
+            sweep_cfg, strat, name_source=_make_name_source()
+        )
+        assert [d["max_candidates_per_trial"] for d in sweep_plan["details"]] == [12, 25]
+        assert sweep_plan["upper_bound_llm_calls"] == 3 * (12 + 25)
+
+        acc_cfg = HarnessConfig(mode="accuracy", dry_run=True)
+        corpora: dict[str, Any] = {"c1": _make_fake_corpus(11)}
+        acc_plan = estimate_and_print_plan(acc_cfg, strat, corpora=corpora)
+        assert acc_plan["details"][0]["max_candidates_per_trial"] == 10
+        assert acc_plan["upper_bound_llm_calls"] == 11 * 10
```

---

## 8. Found But Not Changed

- **`SpyStrategy` in `tests/test_harness.py` (line 55)**: `SpyStrategy` sets `self.top_k = top_k` and returns `{"name": self.name, "top_k": self.top_k}` from `config()`, without defining `max_candidates`. None of the tests in `tests/test_harness.py` assert `upper_bound_llm_calls` or `max_candidates_per_trial` on `SpyStrategy` (all 16 tests in `tests/test_harness.py` pass unchanged), so per Section 2 ("EDIT `tests/test_null_strategy.py` or any other existing test ONLY if one of them asserts the old `top_k` behaviour and now fails ... If you find no such test, touch none"), `tests/test_harness.py` was not modified.
- **`pool_size = len(name_source.names)` in `estimate_and_print_plan()` (`src/graph_insertion/harness.py` line 660)**: Local variable `pool_size` is assigned in the sweep branch of `estimate_and_print_plan` and unused; left untouched to keep the diff strictly scoped to `top_k_bound` and `max_cands`.

---

## 9. Open Questions

- None (`APC`, `APC-A`, `Luke`, `adviser`: no open blocking questions).
