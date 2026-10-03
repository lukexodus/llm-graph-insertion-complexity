# INFRA-006: Shared Decision Step, Metered LLM Client, and Offline Pilot Script

**Agent:** Gemini  
**Task ID:** INFRA-006  
**Date:** 2026-10-03  
**Status:** Completed  
**Working tree:** Uncommitted (per task instructions)

---

## 1. Executive Summary

Task INFRA-006 implements the shared LLM decision step ([D-02], [D-24]), the metered client infrastructure, and the offline/online leave-one-out validation pilot script for DSA:
1. **Metered LLM Client & Abstractions (`src/graph_insertion/llm.py`):**
   - Defined frozen `LLMResponse` capturing text, input/output tokens, reasoning tokens, cache hit/miss tokens, successful attempt latency, model ID, attempts count, and retry wait time.
   - Defined `LLMSnapshot` supporting point-in-time metrics and snapshot subtraction (`snap2 - snap1`) for delta resource accounting.
   - Implemented `MeteredLLMClient` wrapping any `LLMClient` to track calls, attempts, retries, latency, retry waits, token totals, and parse failures.
   - Implemented `DeepSeekClient` using plain `httpx` (fewer dependencies than `openai`), configured for non-thinking mode (`{"thinking": {"type": "disabled"}}`), temperature 0, and exponential backoff retry on 429/5xx and network timeouts.
   - Implemented `FakeLLMClient` for deterministic unit testing and offline simulation.
2. **Pairwise Decision Step (`src/graph_insertion/decision.py`):**
   - Implemented `PairwiseDecisionStep` satisfying the `DecisionStep` protocol.
   - Evaluates each candidate sequentially (one call per candidate, [D-29]).
   - Formats concept names via `embed_text()` ([D-21]) without revealing graph topology.
   - Parses tokens (`X_PREREQ_Y`, `Y_PREREQ_X`, `NONE`) strictly into canonical directed edges `(prereq -> dependent)` ([D-23]).
   - Supports default `"record"` parse-failure policy (treated as no edge and logged to meter) or `strict=True` (`DecisionParseError`).
   - Returns `DecisionOutcome(edges, llm_calls, llm_seconds)`.
3. **Pilot Script (`scripts/pilot_dsa_zero_shot.py`):**
   - Executes leave-one-out brute force on DSA ($29 \times 28 = 812$ calls) with `--confirm` requirement and `--max-calls` limit.
   - Computes 3-way accuracy (standard excluding DSA unjudged row vs. sensitivity treating missing as `NONE`), confusion matrix, directed edge P/R/F1, direction flips, swap consistency, parse-failure rate, latency percentiles, token usage breakdown, and cost estimation via CLI price flags (`--price-in`, `--price-out`).
   - Emits `summary.json` and `raw_calls.jsonl` under `results/pilot/<UTC_TIMESTAMP>/`.
4. **Decisions & Status:**
   - Recorded `[D-29]` in `docs/decisions/decision-log.md`.
   - Updated `INFRA-006` to `done` and added `DATA-004` to `docs/tasks/status.md`.
   - Added `.env` to `.gitignore`.
   - Added `httpx>=0.24` to `pyproject.toml`.
   - 123 unit and integration tests passing.

---

## 2. Verification of Prompt Assumptions & DeepSeek API Details

1. **DeepSeek Official API Verification:**
   - **Base URL:** Verified as `https://api.deepseek.com` (OpenAI-compatible endpoints at `/chat/completions`).
   - **Exact Model ID:** Verified as `deepseek-v4-flash` (also aliased/routed to `deepseek-flash` following the DeepSeek-V4 release). Configurable via `DEEPSEEK_MODEL` env var or constructor arg, defaulting to `deepseek-v4-flash`.
   - **Disabling Thinking Mode:** Verified from DeepSeek's official documentation. Thinking mode is enabled by default on V4 models; to disable thinking mode in the OpenAI-compatible JSON body, requests must include:
     ```json
     "thinking": {"type": "disabled"}
     ```
   - **Prompt Cache & Reasoning Tokens:** Verified in the API response `usage` object:
     - `prompt_cache_hit_tokens` (and `prompt_tokens_details.cached_tokens`)
     - `prompt_cache_miss_tokens`
     - `completion_tokens_details.reasoning_tokens` (0 in non-thinking mode)
2. **HTTP Client Library Selection:**
   - Chose plain `httpx` over the `openai` SDK because `httpx` introduces fewer dependencies (avoids `pydantic`, `anyio`, etc.), provides direct control over HTTP status codes, headers, and timings, and is already installed in the development environment. Updated `pyproject.toml` dependencies accordingly.
3. **Gitignore Coverage:**
   - `.env` was added to `.gitignore`.
   - Note on `results/pilot/<UTC_TIMESTAMP>/`: `.gitignore` does **not** currently cover `results/`. Artifacts written by pilot runs will appear as untracked files unless `results/` is added to `.gitignore`.
4. **Corpus Loader Signature Confirmation:**
   - Confirmed that `load_corpus` accepts `root: Optional[Path | str] = None` (not `dataset_root`), and `LoadedCorpus` exposes `.judgments` (type `GoldJudgmentSet`), not `gold_judgments`.

---

## 3. Test Coverage & Verification

Implemented 22 new tests across two test modules:
- `tests/test_llm.py` (8 tests):
  - `LLMResponse` frozen immutability and attributes.
  - `LLMSnapshot` subtraction arithmetic across all token, retry, latency, and parse-failure fields.
  - `MeteredLLMClient` accounting, reset, and parse failure logging.
  - `DeepSeekClient` missing API key validation.
  - `DeepSeekClient` request payload structure, headers, `thinking: {"type": "disabled"}` validation via `httpx.MockTransport`.
  - Exponential backoff retry on 429 and 500, verifying that backoff delays are excluded from `latency_s` and captured in `retry_wait_s`.
  - Immediate failure on non-retryable 400 error without retries.
  - Retry exhaustion raising `LLMTransportError` on repeated 503 errors.
- `tests/test_decision.py` (14 tests):
  - Prompt construction with and without `domain_context`.
  - Concept formatting via `embed_text()` (no underscores, no `.txt`).
  - Strict isolation: prompt contains only Concept X and Concept Y.
  - Token parsing: `X_PREREQ_Y` $\to (new, cand)$, `Y_PREREQ_X` $\to (cand, new)$, `NONE` $\to ()$.
  - Case and whitespace insensitivity.
  - Default `"record"` parse policy logging to meter without raising.
  - `strict=True` raising `DecisionParseError`.
  - Sequential candidate ordering and call counting.
  - Pilot gold label mapping (`compute_gold_unordered_label`) on positive, reverse, none, anomaly, and unjudged pairs.
  - Token mapping to unordered pair relations.
  - End-to-end `insert_node` integration with `TinyFakeStrategy`, `ConceptGraph`, and `MeteredLLMClient`, confirming graph mutation, metric tracking, and snapshot delta accounting.

All 123 tests in the test suite pass:
`PYTHONPATH=src pytest` -> 123 passed in 8.36s.

Dry-run of the pilot script was verified offline:
`python scripts/pilot_dsa_zero_shot.py --confirm --dry-run --output-dir /tmp/pilot_test` completed all 812 calls and generated `summary.json` and `raw_calls.jsonl`.

---

## 4. Found but Not Changed

1. **Live Pilot Execution:**
   - Per instructions, no live API calls were executed; Luke will execute the live pilot run using `python scripts/pilot_dsa_zero_shot.py --confirm --price-in ... --price-out ...`.
2. **Git Tracking of Results Directory:**
   - `results/` is not currently in `.gitignore`. Luke may choose to add `results/` or keep pilot benchmark outputs tracked.
3. **Transitive Reduction in Decision Prompts:**
   - Gold graphs in DSA/Metacademy are not transitively reduced (as established in INFRA-001); prompts explicitly instruct: "directly or indirectly through other concepts", allowing the model to judge indirect prerequisite dependencies correctly.
4. **Working Tree Changes:**
   - All changes remain uncommitted in the working tree.
