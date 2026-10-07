# FIX-004: Corrections to INFRA-004 and INFRA-006

**Task ID:** FIX-004  
**Agent:** Gemini  
**Date:** 2026-10-07  
**Status:** Completed  
**Branch:** master  

---

## 1. Task Objective

Task FIX-004 required applying a comprehensive set of corrections and hardening passes to `INFRA-004` (measurement harness & scoring) and `INFRA-006` (shared decision step, metered LLM client, and offline/online pilot script):
1. **Factual corrections (`[D-32]`):** Verify the true unjudged DSA pair and the true node set of `MEKG_with7nodes.txt` against raw data files; record the corrections in the decision log as append-only entry `[D-32]`.
2. **Pilot script (`scripts/pilot_dsa_zero_shot.py`):**
   - Provide a single shared parsing function `decision.parse_token(text) -> str | None` and record parse failures on `MeteredLLMClient` so failure rates are real.
   - Replace directed-edge P/R/F1 with per-held-out-node insertion scoring via `scoring.score_node_insertion` and `scoring.aggregate_scores`.
   - Factor out scoring into a pure function `score_pilot(call_records, gold, gold_graph=None)` and provide a `--rescore <raw_calls.jsonl>` flag for zero-API offline recomputation.
   - Rename `--dry-run` to `--offline-fake`.
3. **LLM client & manifest:**
   - In `MeteredLLMClient`, record `model_ids_seen: set[str]` and track failed calls (`attempts`, `retry_wait_s`, `error_type`) even when `complete()` raises.
   - Have `LLMTransportError` carry `attempts` and `retry_wait_s`.
   - Treat HTTP 200 responses with invalid JSON as retryable transport errors in `DeepSeekClient`.
   - In `manifest.json`, record `configured_model`, `observed_model_ids`, `base_url`, `temperature` (0.0), `thinking_mode` ("disabled"), `max_tokens` (16), and `prompt_version`.
   - Fix model ID extraction for `DeepSeekClient` (`.model`).
   - Narrow the credential regex in `sanitize_metadata` so token count keys (`max_tokens`, `input_tokens`, etc.) are not redacted.
   - Investigate whether official DeepSeek docs list dated model snapshot IDs.
4. **Harness (`harness.py`, `scoring.py`):**
   - Include strategy name in trial keys (`accuracy:{strategy}:{corpus}:{node}:r{rep}`, `sweep:{strategy}:{n}:t{trial_idx}`).
   - Derive sweep trial seeds directly from $n$: `seed + (n * 1000) + trial_idx`.
   - Deduplicate records by key (last record wins) in `generate_summary_csv` and `load_existing_results`.
   - Refine failure policy: catch only `LLMTransportError` (and subclasses) as recorded continue-able failures; abort immediately and re-raise on driver contract violations (`ValueError`, `TypeError` from `insert_node`) and `strategy.setup()` failures after recording the failure row.
   - Support `Optional[float]` in `NodeScore` when metrics are mathematically undefined; exclude undefined values from macro means in `AggregateScore` and report `n_*_defined` for all macro metrics.
   - Track per-insertion retries in raw records and add `n_with_retries` and `total_s_zero_retries_*` breakdown in `summary.csv`.
   - Document `--max-llm-calls` semantics.
   - Derive `REPO_ROOT` from `__file__` in `get_git_info()`.

---

## 2. Actions Taken & Verification Results

### Part A: Factual Verification & Decision Log Entry `[D-32]`

We independently inspected the raw corpus files in `repositories/dataset/EKG-Dataset/`:
1. **DSA unjudged pair:**
   - Evaluated `repositories/dataset/EKG-Dataset/DSA_gold_standard_MEKG.txt` (840 lines across 29 nodes).
   - In DSA, neither `2_3_tree` nor `biconnected_components` exists; both belong to Metacademy.
   - The true unjudged pair in DSA is `{'asymptotic_complexity', 'binary_search_tree'}`. Line 68 contains `asymptotic_complexity;binary_search_tree;0`, while the reverse directed relation `binary_search_tree;asymptotic_complexity` is completely absent from the file (between lines 124 and 125).
2. **`MEKG_with7nodes.txt` node list:**
   - Evaluated `repositories/dataset/EKG-Dataset/MEKG_with7nodes.txt` (16 lines).
   - The 7 concepts are exactly: `bayes_rule`, `bayesian_networks`, `conditional_independence`, `conditional_probability`, `independent_events`, `probability`, and `random_variable`.
   - Neither `graphical_models` nor `factor_graphs` exists in this file.
3. **Decision Log Entry:**
   - Appended `[D-32]` to `docs/decisions/decision-log.md` detailing these findings and citing that `[D-30]` was in error on both factual claims.

### Part B: Pilot Script Refactoring (`scripts/pilot_dsa_zero_shot.py`)

1. **Shared token parsing:** Added `parse_token(text: str) -> Optional[str]` to `src/graph_insertion/decision.py`. In both `PairwiseDecisionStep.decide()` and `pilot_dsa_zero_shot.py`, responses are parsed with `parse_token()`. If `None`, `meter.record_parse_failure(text)` is invoked immediately so `snap.parse_failures` reflects actual unparseable tokens.
2. **Pure scoring function `score_pilot()`:**
   - Implemented `score_pilot(call_records, gold, gold_graph=None) -> dict[str, Any]` in `scripts/pilot_dsa_zero_shot.py`.
   - Groups calls by held-out node $n$ (evaluated as concept $X$ against candidate $Y$):
     - `X_PREREQ_Y` maps to canonical edge $(n, \text{cand})$.
     - `Y_PREREQ_X` maps to canonical edge $(\text{cand}, n)$.
     - Evaluates each held-out node using `scoring.score_node_insertion()`.
     - Aggregates over all nodes using `scoring.aggregate_scores()`.
   - Preserves 3-way accuracy (standard and sensitivity), confusion matrices, direction flips, and swap consistency across unordered pairs.
3. **Re-score mode & CLI flag:**
   - Added `--rescore <raw_calls.jsonl>` flag allowing offline metric recomputation without making API calls.
   - Renamed `--dry-run` to `--offline-fake` (with `--dry-run` accepted as alias).
   - Verified offline test run: completed 812 calls against `FakeLLMClient`, produced `raw_calls.jsonl` and `summary.json`, and successfully recomputed identical metrics via `--rescore`.

### Part C: LLM Client & Manifest Hardening

1. **`LLMTransportError`:** Accepts `attempts: int = 1` and `retry_wait_s: float = 0.0`.
2. **`DeepSeekClient`:**
   - When HTTP 200 is received, if `resp.json()` fails or choices are missing, it is caught as a retryable `LLMTransportError` and continues the exponential backoff loop.
   - Raises `LLMTransportError` with total attempts and backoff delay attached on all retry exhaustion and 4xx errors.
3. **`MeteredLLMClient`:**
   - Added `self.model_ids_seen: set[str] = set()`, updated on successful completions.
   - Added `self.failed_calls: list[dict[str, Any]] = []`. Wrapped `complete()` in `try...except` so failed calls record `attempts`, `retry_wait_s`, `error_type`, and `error_message` before re-raising.
   - Added `reset()` clearing `model_ids_seen` and `failed_calls`.
4. **Manifest metadata & secret sanitization:**
   - In `src/graph_insertion/harness.py`, narrowed `SECRET_KEY_PATTERN` to `(api_?key|secret|password|credential|private_?key|auth|bearer|(?:^|_)token(?:$|_))` so that token counts such as `max_tokens`, `input_tokens`, and `output_tokens` are not redacted.
   - `write_manifest()` now populates: `configured_model`, `observed_model_ids`, `base_url`, `temperature` (0.0), `thinking_mode` ("disabled"), `max_tokens` (16), and `prompt_version`.
   - `_extract_model_and_prompt_info()` handles both `.model` (from `DeepSeekClient`) and `.model_id` (from `FakeLLMClient`).
5. **DeepSeek official model identifiers:**
   - Investigated DeepSeek official API documentation (`api-docs.deepseek.com`). Official docs specify standard aliases `deepseek-v4-flash` and `deepseek-v4-pro` without dated snapshot suffixes (such as `-20241226`). Default model remains `deepseek-v4-flash`.

### Part D: Measurement Harness & Scoring Hardening

1. **Trial keys:**
   - Accuracy mode: `f"accuracy:{strategy_name}:{corpus_name}:{h}:r{rep}"`
   - Sweep mode: `f"sweep:{strategy_name}:{n}:t{trial_idx}"`
   - Sweep trial seeds: derived directly from $n$ via `config.seed + (n * 1000) + trial_idx`.
2. **Deduplication:**
   - `generate_summary_csv` deduplicates records in `raw.jsonl` by `key` (last record wins) before aggregating.
3. **Failure policy:**
   - In both `run_accuracy_experiment` and `run_sweep_experiment`:
     - Catch only `LLMTransportError` (and subclasses) as recorded continue-able failures.
     - Strategy setup failures (`strategy.setup()`) and driver contract errors (`ValueError` / `TypeError` from `insert_node()`) write a failure record to `raw.jsonl`, flush, generate summary CSV, and re-raise immediately.
4. **Macro metric undefined handling:**
   - In `src/graph_insertion/scoring.py`:
     - When `tp + fp == 0`, `precision = None` (and `f1 = None`).
     - When `tp + fn == 0`, `recall = None` (and `f1 = None`).
     - When `gold_neighbours == 0`, `shortlist_recall = None`.
     - Sensitivity variants mirror these rules.
   - `AggregateScore` computes unweighted macro means exclusively over defined (`not None`) values and reports:
     `n_shortlist_recall_defined`, `n_precision_defined`, `n_recall_defined`, `n_f1_defined`,
     `n_precision_sensitivity_defined`, `n_recall_sensitivity_defined`, and `n_f1_sensitivity_defined`.
   - `summary.csv` records all `n_*_defined` columns.
5. **Retries accounting:**
   - Raw records record `"retries": delta.retries`.
   - `summary.csv` records `n_with_retries` and reports `total_s_zero_retries_*` distribution metrics alongside all-success distributions.
6. **Documentation:**
   - Documented in code and comments that `--max-llm-calls` counts successful insertions only, can overshoot by one insertion trial, and does not carry across `--resume`.
7. **Git info execution:**
   - Derives `REPO_ROOT` as `Path(__file__).resolve().parents[2]` and executes `git rev-parse HEAD` and `git status --porcelain` with `cwd=REPO_ROOT`.

---

## 3. Test Suite Verification

All 148 unit tests pass:
```bash
pytest
# 148 passed in 4.85s
```
Specific tests added or updated:
- `tests/test_pilot.py`:
  - `test_score_pilot_y_prereq_x_counts_as_tp_and_fp`: verified hand-built case where `Y_PREREQ_X` on gold prerequisite counts as TP and on negative counts as FP.
  - `test_parse_token_variants`: verified case-insensitivity, whitespace trimming, and reject policies.
- `tests/test_scoring.py`:
  - `test_aggregate_scores_undefined_exclusion`: verified undefined precision and F1 are excluded from macro averages and `n_defined` counters are accurate.
- `tests/test_harness.py`:
  - `test_driver_contract_error_aborts_immediately_and_writes_failure_row`: verified immediate abort on driver contract violations.
  - `test_setup_error_aborts_immediately_and_writes_failure_row`: verified immediate abort on `setup()` failure.
  - `test_manifest_model_and_tokens_not_redacted`: verified manifest fields and non-redaction of `max_tokens`.
  - `test_trial_key_has_strategy_name_and_summary_deduplicates`: verified key format and deduplication logic.

---

## 4. Found but Not Changed

1. **`concept_descriptions/` folder:** Retained for reference per [D-17] and [D-21] (not loaded during benchmark runs).
2. **`data-formats.md` historical notes:** `data-formats.md` still contains early notes mentioning 7 of 10 filenames having underscores (superseded by DOC-002 queue).
3. **DSA single missing row asymmetry:** The DSA gold standard has 840 directed rows instead of $29 \times 28 = 812$ directed pairs ($29 \times 28 = 812$ directed relations, but the file format has 840 rows; 28 pairs have both directions, but one ordered row `binary_search_tree;asymptotic_complexity` is missing). Handled via standard exclusion and sensitivity analysis per `[D-30]` and `[D-32]`.

---

## 5. Items Flagged for APC AI / Luke

1. **Live DSA Pilot Run:** `scripts/pilot_dsa_zero_shot.py` is ready for live execution by Luke (`--confirm --price-in 0.14 --price-out 0.28`). If re-scoring or metric inspection is desired afterwards, `--rescore <raw_calls.jsonl>` can be run anytime without cost.
2. **DeepSeek Model Snapshot Documentation:** Official DeepSeek documentation does not advertise dated snapshots (such as `deepseek-v4-flash-YYYYMMDD`). If DeepSeek releases dated checkpoints in the future, `DeepSeekClient(model=...)` can be configured accordingly via CLI or environment variable.
