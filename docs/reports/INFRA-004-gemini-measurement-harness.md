# Task Report: INFRA-004 — Measurement Harness (Accuracy Runner + Cost Sweep Runner)

- **Task ID:** INFRA-004
- **Agent:** Gemini
- **Date:** 2026-10-03
- **Git Commit (base):** `541d3fb4f8226bc800d2926d472c71997ed06a57`
- **Status:** Complete (all 141 tests passing)

---

## 1. What Was Asked

Implement the experimental measurement harness supporting two primary operational modes:
1. **Mode `"accuracy"`:** Leave-one-out insertion benchmark across ground-truth corpora DSA (all 29 nodes held out one at a time) and Metacademy (seeded sample of 30 nodes). Each held-out node $h$ is removed from the corpus graph ($G' = G \setminus \{h\}$), inserted by the strategy, decided via the shared decision step, and scored against ground-truth judgments with micro/macro precision, recall, F1, shortlist recall, and DSA unjudged row sensitivity.
2. **Mode `"sweep"`:** Cost-only scaling sweep over synthetic concept names across sizes $n \in [50, 100, 200, 500, 1000, 2000]$, 10 trials per size, using an in-memory `SyntheticNameSource` abstraction.
3. **Execution Guardrails & Safety:** `--dry-run` to print plans and upper-bound LLM calls without mutating state; live runs require `--confirm` and halt cleanly on `--max-llm-calls`; `--resume` skips completed keys in `raw.jsonl`; `--retry-failed` re-runs failures; `--fail-fast` halts on errors.
4. **Output Artifacts:** `results/<run_id>/manifest.json` (git metadata, versions, configuration, sanitizing all secrets), `raw.jsonl` (immediately flushed insertion records), and `summary.csv` (aggregated metrics).
5. **Decisions Recorded:** Record Luke's Part 0 decisions as `[D-30]` and harness architectural decisions as `[D-31]`.

---

## 2. What Was Actually Done

### Part 0: Domain Context & DSA Unjudged Row Scoring Policy ([D-30])
- Updated `CORPUS_DOMAIN_CONTEXT_MAP["MEKG_with7nodes"] = "probability and graphical models"` in `src/graph_insertion/loader.py` and updated `derive_domain_context()` docstrings.
- Updated pinned loader expectation in `tests/test_loader.py` (`MEKG_with7nodes` expectation line 163).
- Defined scoring policy for DSA's unjudged unordered pair (`{'2_3_tree', 'biconnected_components'}`): excluded from standard precision/recall/F1 scoring (`excluded_predictions`), while separately computing a sensitivity variant counting predicted edges on the pair as false positives (`fp_sensitivity`).

### Part 1: `ConceptGraph.without_node(name) -> ConceptGraph`
- Implemented `ConceptGraph.without_node(name)` in `src/graph_insertion/graph_representation.py`: returns an independent deep copy of the graph with `name` and all incident edges removed. Raises `KeyError` if `name` is absent.
- Added comprehensive unit tests in `tests/test_graph_representation.py` (`test_without_node_removes_node_and_incident_edges`, `test_without_node_nonexistent_node_raises_key_error`).

### Part 2: Scoring Module (`src/graph_insertion/scoring.py`)
- Implemented pure, unit-tested scoring functions:
  - `compute_gold_incident_edges(graph, node)`: extracts all ground-truth directed edges incident to `node`.
  - `compute_gold_neighbours(graph, node)`: extracts all ground-truth adjacent nodes.
  - `score_node_insertion(...)`: computes `NodeScore` containing TP, FP, FN, precision, recall, F1, `shortlist_recall` (narrowing recall = fraction of gold neighbours in candidate shortlist), `excluded_predictions`, and sensitivity variants (`fp_sensitivity`, `precision_sensitivity`, `recall_sensitivity`, `f1_sensitivity`).
  - `aggregate_scores(...)`: computes `AggregateScore` calculating micro-aggregates (pooled counts) and macro-aggregates (mean of per-node metrics) across both standard and sensitivity evaluations.
- Added unit tests in `tests/test_scoring.py` (5 tests covering perfect scores, unjudged pair exclusions, shortlist recall vs end-to-end recall, and aggregation).

### Part 3: Measurement Harness (`src/graph_insertion/harness.py` & `scripts/run_experiment.py`)
- Created `src/graph_insertion/harness.py`:
  - `SyntheticNameSource`: dataclass holding sequence of unique snake_case concept names and optional domain context string.
  - `HarnessConfig`: configuration for run parameters, paths, seeds, sampling sizes, and safety flags.
  - Trial Isolation ([D-31]): for each trial, builds an independent graph copy (`without_node` or fresh `ConceptGraph`), instantiates fresh strategy via `strategy_factory()`, creates a new `MeteredEmbedder` wrapping `embedder_factory()` and shares the same meter between `setup()` and `insert_node()` per [D-28].
  - Garbage Collection: calls `gc.collect()` immediately prior to the timed insertion window (GC remains enabled).
  - Timing Attribution: records `harness_wall_s` and `unaccounted_s = harness_wall_s - (total_s + validate_s)`.
  - LLM Metering: captures snapshot deltas (`snap_after - snap_before`) if the decision step exposes a `MeteredLLMClient`.
  - Safety & Guardrails: `--dry-run` produces detailed insertion plans and upper-bound LLM call estimates without executing insertions; live execution requires `--confirm`; `--max-llm-calls` cleanly halts the trial loop while saving current state; `--resume` skips completed keys; `--retry-failed` re-runs failed keys; `--fail-fast` aborts on errors.
  - Output Writers:
    - `manifest.json`: git commit hash, dirty flag, python version, platform, dependency versions (`networkx`, `pytest`, `httpx`, `numpy`), strategy configuration, model ID, prompt version, seeds, sizes, timestamp; all credential substrings (`api_key`, `secret`, `token`, `password`, `auth`, `credential`, `sk-...`, `Bearer `) scrubbed via `sanitize_metadata`.
    - `raw.jsonl`: streamed record per insertion with all `InsertionMetrics`, timings, LLM snapshot delta, scoring/error info.
    - `summary.csv`: aggregated statistics per strategy $\times$ corpus (accuracy) or strategy $\times$ size (sweep).
- Created `scripts/run_experiment.py`: CLI driver with full arguments, local stub strategy, and pluggable decision step.
- Created `tests/test_harness.py`: 11 tests verifying seeded determinism, held-out isolation, embedder meter sharing, resume/retry logic, failure logging, fail-fast abort, call limits, secret sanitization, summary aggregation, dry-run safety, and sweep scaling.

---

## 3. Findings & Verification

1. **`MEKG_with7nodes` Pinned Loader Test:**
   - Updating `CORPUS_DOMAIN_CONTEXT_MAP["MEKG_with7nodes"]` to `"probability and graphical models"` required updating the expectation in `tests/test_loader.py` line 163. The test suite passed cleanly after alignment.
2. **DSA Unjudged Row Asymmetry:**
   - In DSA raw data, `{'2_3_tree', 'biconnected_components'}` contains a directed entry for `('biconnected_components', '2_3_tree') -> 0`, but lacks the reverse directed entry.
   - `scoring.py` cleanly separates standard evaluation (which ignores predictions on this pair) from sensitivity analysis (which penalizes predictions on it as false positives).
3. **Embedder Argument Naming in Project:**
   - `FakeEmbedder` expects `dim: int`, not `dimension`. Aligned all test fixtures and CLI defaults to `dim`.
4. **Test Suite Health:**
   - Full repository test suite (`PYTHONPATH=src pytest`) passes with 141 passed tests in 15.13 seconds.

---

## 4. Found But Not Changed

1. **`CORPUS_DOMAIN_CONTEXT_MAP` item 6 in D-27:**
   - In `docs/decisions/decision-log.md`, `[D-27]` item (6) recorded `MEKG_with7nodes -> None`. Per Luke's instruction, `[D-30]` was recorded superseding item (6) of `[D-27]`. The text of `[D-27]` was left intact as historical record per append-only log conventions.
2. **`concept_descriptions/` in dataset root:**
   - Left untouched per D-17 and D-21.

---

## 5. Flags for APC AI & Next Tasks

- **Phase 1 Exit Criterion (INFRA-005):** With INFRA-001, INFRA-002, INFRA-003, INFRA-004, and INFRA-006 completed, Phase 1 is now ready for its exit criterion: INFRA-005 (Null Strategy implementation and full end-to-end dry/live run through the harness).
- **DATA-004 (Synthetic Name Pool):** The harness accepts `SyntheticNameSource`. For unit testing and dry runs, placeholder snake_case names (`concept_node_XXXX`) were used. When DATA-004 generates the full 2000-concept pool, it will plug directly into `run_sweep_experiment`.
- **Git State:** All modifications and new files are left **UNCOMMITTED** per prompt rules.
