# INFRA-005: Null Strategy End-to-End Through Full Harness (Phase 1 Exit Criterion)

**Agent:** Claude Code (initial implementation, planning, and suite design) and Gemini (conformance & spot-check debugging, operator ergonomics, full matrix execution, verification, and documentation).  
**Task ID:** INFRA-005  
**Date:** 2026-10-07  
**Status:** needs-review (Phase 1 exit criterion pending APC AI confirmation)  
**Decision appended:** `[D-38]` in `docs/decisions/decision-log.md`

---

## 1. Executive Summary

This task implements the Phase 1 exit criterion for the LLM graph-insertion complexity benchmark: executing the baseline `NullStrategy` through the complete measurement harness in both accuracy and sweep modes without network calls or mock leaks.

Key deliverables:
1. **`NullStrategy` (`src/graph_insertion/strategies/null.py`):** Candidate-narrowing strategy producing a uniform random-k shortlist (default k=1) without embeddings. Seeded with `random.Random(seed)` over `sorted(graph.nodes())` for strict PYTHONHASHSEED independence. Discards embedders on `setup()` (`_embedder = None`), safely bypassing driver identity checks.
2. **Conformance Suite Enhancement (`tests/test_strategy_interface.py`):** Added `uses_embeddings: bool = True` class attribute to `StrategyConformanceSuite`. When `False`, embedding activity assertions invert to assert zero embedding calls, zero embedding time, empty `texts_log`, and zero update calls. Added embedder identity conformance test (`test_embedder_identity_stored_on_strategy`) and two meta-test suites (`TestEmbeddingConformanceSuiteMetaTest`, `TestNonEmbeddingConformanceSuiteMetaTest`) verifying that both strategy types conform to interface contracts.
3. **End-to-End Test Suite (`tests/test_null_strategy.py`):** 35 unit, accuracy, sweep, resume/deduplication, and names-file validation tests. All 29 DSA nodes evaluated in leave-one-out mode with exact metrics verified (`n_before == 28`, `shortlist_size == 1`, `llm_calls == 1`, `embedding_calls == 0`).
4. **Operator Ergonomics & Schedule Guard (`src/graph_insertion/schedule.py`, `scripts/run_experiment.py`, `scripts/pilot_dsa_zero_shot.py`):**
   - Progress lines emitted to `stderr` periodically (`[strategy/size] done/total elapsed=Xs ETA=Xs retries=N`) with an injectable clock for testing.
   - DeepSeek peak pricing schedule module enforcing off-peak windows per [D-37] (Mon–Fri 01:00–04:00 and 06:00–10:00 UTC). Refuses live execution intersecting peak hours unless `--allow-peak` is passed. Chinese public holidays are conservatively not modelled.
   - Corrected pilot script price defaults from stale `0.14/0.28` to off-peak Flash prices `0.15/0.60` per [D-37].
5. **Names Input Pathway & Validation (`scripts/run_experiment.py`):** Added `--names-file` accepting JSON arrays or objects with `"names"`. Enforces `len >= max_size + 1`, zero duplicates, strict snake_case, and zero overlap with any node across all 12 benchmark corpora.
6. **Full D-35 Matrix Run:** 6 sizes (50, 100, 200, 500, 1000, 2000) × 10 trials = 60 trials executed end-to-end with 100% success in 1.3 seconds wall time.

---

## 2. Prompt Assumptions Verified vs. Corrected

| Item | Prompt Stated Assumption | Repository Reality | Resolution |
|---|---|---|---|
| **Strategy Registry** | "Register it wherever `run_experiment.py` looks up strategies by name" | `run_experiment.py` had no strategy lookup; it used a hardcoded inline lambda `StubNarrowingStrategy(top_k=5)`. | Implemented `STRATEGY_REGISTRY` dict mapping `"null"` and `"stub"` to parameterizable factory callables, wired to a `--strategy` CLI argument. |
| **Shortlist Recall Formula** | Shortlist recall on single spot-checks would be 1.0 if adjacent | Per `scoring.py`, `shortlist_recall = shortlist_hits / len(gold_neighbours)`. For k=1, at most 1 hit is possible, so recall is `1.0 / len(gold_neighbours)` for nodes with gold neighbors, NOT 1.0 (e.g. `asymptotic_complexity` has 9 neighbors, so recall is 1/9 = 0.1111). | Test spot-check in `test_null_strategy.py` corrected to assert exact formula `1.0 / len(gold_neighbours)`. |
| **`--max-llm-calls` Semantics** | Counts this process only or cumulative across resume? | `harness.py` lines 107–110: `max_llm_calls` tracks in-memory `cumulative_llm_calls` in the current process only; does not carry across `--resume` invocations. | Confirmed, documented in `--max-llm-calls` CLI help text, decision log [D-38], and verified with unit test. |
| **Price Defaults** | `pilot_dsa_zero_shot.py` defaulted to 0.14/0.28 | Verified: CLI defaults were stale `0.14` and `0.28`. | Updated CLI defaults to `0.15` and `0.60` per [D-37]. Updated cost reporting to print applied rates. |
| **Peak Windows** | DeepSeek peak hours per D-37 | Mon–Fri 01:00–04:00 and 06:00–10:00 UTC. Chinese holidays are off-peak in reality. | Implemented in `src/graph_insertion/schedule.py`. Chinese holidays omitted (conservative safety). |

---

## 3. Test Suite Collection & Coverage

Total test count collected across repository: **234 items** (232 passed, 2 skipped).

### Per-File Breakdown (`pytest --collect-only -q`)

```
tests/test_decision.py:           15
tests/test_graph_representation.py: 51
tests/test_harness.py:            16
tests/test_llm.py:                12
tests/test_loader.py:             26
tests/test_null_strategy.py:      35
tests/test_pilot.py:              15
tests/test_schedule.py:           16
tests/test_scoring.py:             7
tests/test_strategy_interface.py: 41
------------------------------------
TOTAL:                           234
```

### Skipped Tests
Two tests are skipped intentionally:
1. `tests/test_strategy_interface.py::TestNonEmbeddingConformanceSuiteMetaTest::test_embedder_identity_stored_on_strategy`
2. `tests/test_null_strategy.py::TestNullStrategyConformance::test_embedder_identity_stored_on_strategy`

Both tests verify that embedding strategies retain the exact `MeteredEmbedder` instance passed to `setup()`. When `uses_embeddings = False`, non-embedding strategies leave `_embedder = None` by design (bypassing the identity check in `insert_node`), and the conformance test cleanly skips via `pytest.skip()`.

---

## 4. Full D-35 Matrix Benchmark Results (C2)

The full D-35 sweep matrix was executed end-to-end through `scripts/run_experiment.py` in sweep mode:
- **Sizes ($n$):** 50, 100, 200, 500, 1000, 2000
- **Trials per size:** 10
- **Total insertions:** 60
- **Strategy:** `NullStrategy` (seed=42, k=1)
- **Decision Step:** Offline zero-latency stub
- **Status:** 60/60 successful (0 failures, 0 retries)
- **Total Wall Time:** 1.3 seconds

### Per-Size Timing Metrics (Averaged over 10 trials)

| Graph Size ($n$) | Mean `total_s` (s) | Mean `harness_wall_s` (s) | Mean `shortlist_s` (s) | Mean `decide_s` (s) | Mean `apply_s` (s) | Mean `unaccounted_s` (s) | Mean LLM Calls |
|---|---|---|---|---|---|---|---|
| **50** | $8.41 \times 10^{-5}$ (0.084 ms) | $1.15 \times 10^{-4}$ (0.115 ms) | $5.57 \times 10^{-5}$ (0.056 ms) | $2.19 \times 10^{-5}$ | $6.17 \times 10^{-6}$ | $2.63 \times 10^{-5}$ | 1.0 |
| **100** | $8.98 \times 10^{-5}$ (0.090 ms) | $1.16 \times 10^{-4}$ (0.116 ms) | $6.49 \times 10^{-5}$ (0.065 ms) | $1.83 \times 10^{-5}$ | $6.31 \times 10^{-6}$ | $2.21 \times 10^{-5}$ | 1.0 |
| **200** | $1.34 \times 10^{-4}$ (0.134 ms) | $1.68 \times 10^{-4}$ (0.168 ms) | $1.01 \times 10^{-4}$ (0.101 ms) | $2.38 \times 10^{-5}$ | $8.96 \times 10^{-6}$ | $2.89 \times 10^{-5}$ | 1.0 |
| **500** | $1.85 \times 10^{-4}$ (0.185 ms) | $2.18 \times 10^{-4}$ (0.218 ms) | $1.56 \times 10^{-4}$ (0.156 ms) | $2.13 \times 10^{-5}$ | $7.30 \times 10^{-6}$ | $2.92 \times 10^{-5}$ | 1.0 |
| **1000** | $2.82 \times 10^{-4}$ (0.282 ms) | $3.21 \times 10^{-4}$ (0.321 ms) | $2.51 \times 10^{-4}$ (0.251 ms) | $2.27 \times 10^{-5}$ | $7.45 \times 10^{-6}$ | $3.42 \times 10^{-5}$ | 1.0 |
| **2000** | $6.20 \times 10^{-4}$ (0.620 ms) | $6.72 \times 10^{-4}$ (0.672 ms) | $5.89 \times 10^{-4}$ (0.589 ms) | $2.24 \times 10^{-5}$ | $7.72 \times 10^{-6}$ | $4.67 \times 10^{-5}$ | 1.0 |

### Scaling Observations
- **`shortlist_s` scaling:** `shortlist_s` grows from 0.056 ms at $n=50$ to 0.589 ms at $n=2000$. This growth is dominated by Python's `sorted(graph.nodes())` sort over $n$ strings on every call.
- **`harness_wall_s` vs `total_s`:** The difference (`unaccounted_s`) remains consistently small ($\approx 0.025$ to $0.047$ ms) across all sizes, representing harness overhead (dictionary allocations, snapshot deltas, and json serialization).
- **Graph Copy / Node Removal Overhead at $n=2000$:**
  Measured independently over 100 iterations on a 2000-node graph:
  - `ConceptGraph.without_node()`: **mean 5.834 ms** (median 4.317 ms)
  - `ConceptGraph._g.copy()` (NetworkX DiGraph copy): **mean 8.479 ms** (median 7.751 ms)
  In sweep mode, trials construct fresh isolated concept subgraphs rather than mutating in-place, so graph mutation does not accumulate state.

---

## 5. `--max-llm-calls` Semantics

The semantics of `--max-llm-calls` were examined in `src/graph_insertion/harness.py`:
- `max_llm_calls` tracks `cumulative_llm_calls` accumulated **in the current running process only**.
- When `--resume` is used, previously completed records loaded from `raw.jsonl` are skipped, but their historical LLM calls **do not count toward the current process's `max_llm_calls` cap**.
- The cap is checked before each insertion; it may overshoot by up to one insertion trial if a trial makes multiple calls.
- This behavior has been documented in:
  1. `scripts/run_experiment.py` `--help` text.
  2. Decision log entry `[D-38](3)`.
  3. Verified via unit test `test_max_llm_calls_is_process_local_not_cumulative` in `tests/test_null_strategy.py`.

---

## 6. Status of Embedding-Based Strategies in Harness

**Has an embedding-based strategy path been exercised through the measurement harness yet?**

**No.**
Only `NullStrategy` and `StubNarrowingStrategy` currently exist as implementations of `NarrowingStrategy`. The four candidate-narrowing strategies that utilize embeddings:
- Strategy 1: Full pairwise (no shortlist / brute force)
- Strategy 2: Pre-computed embedding threshold
- Strategy 3: Approximate nearest neighbor (ANN) retrieval
- Strategy 4: Bounded candidate clustering / graph search

are Phase 2 tasks (STRAT-001 through STRAT-004).

The embedding infrastructure itself (`Embedder`, `MeteredEmbedder`, `FakeEmbedder`) is fully tested at the unit level and within the driver contract via `insert_node()` (e.g. `TestTinyFakeStrategyConformance` in `test_strategy_interface.py`). However, **running a real embedding-based strategy through `run_experiment()` / `HarnessConfig` awaits the implementation of Strategy 2 in Phase 2**.

---

## 7. Found but Not Changed

1. **`concept_descriptions/` folder:** Retains unused markdown description files. Unused per [D-21] (bare concept names only). Not deleted to maintain repo history.
2. **`results/pilot/20261007_053743Z/`:** Staged pilot run artifacts from FIX-007 remain staged and unchanged.
3. **`docs/tasks/status.md` DOC-002 and DATA-004:** Left untouched per instruction.
4. **NetworkX version & deprecation warnings:** NetworkX functions run cleanly without warnings under Python 3.14.
5. **Chinese public holiday list:** Chinese public holidays are not integrated into `schedule.py` calendar calculations. This omission is deliberate and conservative per [D-38](4): treating holidays as potential peak hours ensures live runs never trigger peak rates unexpectedly.

---

## 8. Verification Commands Executed

```bash
# 1. Full test suite (232 passed, 2 skipped in 12.4s)
pytest -q

# 2. Per-file test count breakdown (234 total)
python -c "
import subprocess
out = subprocess.check_output(['pytest', '--collect-only'], text=True)
counts = {}
for line in out.splitlines():
    if '<Module ' in line:
        curr = line.split('<Module ')[1].split('>')[0]
        counts[curr] = 0
    elif '<Function ' in line and curr:
        counts[curr] += 1
for f, c in sorted(counts.items()):
    print(f'{f}: {c}')
print('TOTAL:', sum(counts.values()))
"

# 3. Dry-run and CLI sanity checks
python scripts/run_experiment.py --mode sweep --strategy null --sweep-sizes 5 10 --sweep-trials 2 --dry-run
python scripts/run_experiment.py --mode sweep --strategy null --sweep-sizes 5 10 --sweep-trials 2 --confirm --output-dir /tmp/test_sweep

# 4. DeepSeek peak schedule safety check
python scripts/run_experiment.py --mode sweep --strategy null --sweep-sizes 5 --sweep-trials 1 --confirm --live
python scripts/pilot_dsa_zero_shot.py --confirm

# 5. Full D-35 matrix run (60 trials, 1.3s)
python scripts/run_experiment.py --mode sweep --strategy null --sweep-sizes 50 100 200 500 1000 2000 --sweep-trials 10 --confirm --output-dir /tmp/d35_full_matrix
```
