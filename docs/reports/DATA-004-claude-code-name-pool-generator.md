# DATA-004: Synthetic Concept-Name Pool Generator

**Task ID:** DATA-004  
**Agent:** Claude Code  
**Date:** 2026-10-07  
**Status:** Complete (needs-review)  
**Assigned Decision ID:** `[D-39]`  

---

## 1. Executive Summary

Task DATA-004 delivers the synthetic concept-name pool generation toolchain (`scripts/generate_name_pool.py` and `tests/test_generate_name_pool.py`), satisfying the cost-scaling sweep prerequisites locked in [D-35]. The script generates a large-n pool of synthetic computer-science concept names disjoint from all 12 benchmark evaluation corpora, formatted as `{"meta": {...}, "names": [...]}` and validated to pass `scripts/run_experiment.py:load_and_validate_names_file` unchanged.

Key deliverables:
1. **CLI Script (`scripts/generate_name_pool.py`):**
   - Implements four operational modes: `--offline-fake` (deterministic simulation; refuses to overwrite default tracked path), `--dry-run` (pre-flight plan, cost estimate, and peak status; zero API calls and zero files), `--build-only` (offline deterministic rebuild from existing cache), and `--verify` (cryptographic SHA256 integrity, provenance check, plural resolution, and corpus disjunction).
   - Live generation (`--live`) is strictly gated by `--confirm`, `DEEPSEEK_API_KEY`, and peak-window schedule intersection checks via `graph_insertion.schedule`. Missing API keys emit a clean error to `sys.stderr` and exit with code 1 (no traceback).
   - Iterative prompting across 80 curated CS subfields (`SUBFIELDS`, `NAME_POOL_PROMPT_VERSION = "np1"`) requesting 40 concepts per call. Round 2 and later list previous concepts for that subfield (capped at 100) and instruct the model not to repeat them.
   - Comprehensive candidate validation tracking 9 distinct drop reasons, near-duplicate plural filtering, and a seeded shuffle (`random.Random(42)`).
2. **LLM Client Extension (`src/graph_insertion/llm.py`):**
   - Added backward-compatible optional keyword parameters `temperature: float = 0.0` and `max_tokens: int = 16` to `DeepSeekClient.__init__`. Verified that default values and existing behavior are unchanged.
3. **Automated Test Suite (`tests/test_generate_name_pool.py`):**
   - 16 offline unit and integration tests covering parameter defaults, end-to-end fake pool building, all 9 drop reason triggers, cache resumption with zero new calls, deterministic repeatability, `--verify` tamper detection, live mode refusal gates, and `--max-calls` looping caps.
4. **Documentation & Decision Log:**
   - Appended decision `[D-39]` to `docs/decisions/decision-log.md`.
   - Updated the `DATA-004` row in `docs/tasks/status.md` to `needs-review` ("script delivered; pool not yet generated; Luke runs the live step").

The full test suite now collects **291 tests**, with **289 passing and 2 skipped** (100% pass rate among runnable tests). Per the task instructions, live generation was not run; Luke will execute the live generation step himself.

---

## 2. Prompt Verification and Analysis

| Prompt Statement / Assumption | Verification Result | Details |
| :--- | :--- | :--- |
| **`load_and_validate_names_file` contract** | **Confirmed** | Verified against `scripts/run_experiment.py:392-478`. Requires $\ge \text{min\_required\_names}$, snake_case regex `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, no duplicates, and zero overlap with the 12 benchmark corpora on raw names or `embed_text()` form. |
| **`DeepSeekClient` constructor parameters** | **Confirmed & Extended** | Verified against `src/graph_insertion/llm.py:300`. `DeepSeekClient` previously hard-coded `temperature = 0.0` and `max_tokens = 16`. Extended `__init__` with backward-compatible keyword arguments `temperature: float = 0.0, max_tokens: int = 16`. Verified all existing tests pass with defaults intact. |
| **Module location of `embed_text`** | **Clarified / Corrected** | Prompt assumed `use graph_insertion.loader.discover_corpora / load_corpus and embed_text`. In reality, `embed_text` is defined in `graph_insertion.graph_representation` (re-exported by `graph_insertion`), not `loader`. Used `graph_insertion.graph_representation.embed_text`. |
| **80 CS Subfields & Prompt np1** | **Confirmed & Implemented** | Defined `SUBFIELDS` tuple of 80 distinct canonical computer science subfields. Prompt version pinned to `"np1"`. Round 2+ passes up to 100 previously seen concepts for that subfield. |
| **Cache & Resume semantics** | **Confirmed & Implemented** | Responses are appended to `results/datagen/<run_id>/raw_responses.jsonl`. Resumption parses existing cache entries; only entries failing JSON array parsing are re-requested on rerun. |
| **Live execution gates & schedule guard** | **Confirmed & Implemented** | `--live` strictly requires `--confirm` and `DEEPSEEK_API_KEY`. Pre-flight computes estimated tokens (250 in / 450 out) and duration, checks `window_intersects_peak()`, and refuses execution during peak hours unless `--allow-peak` is given. Missing key exits code 1 with stderr message and no traceback. |
| **Offline-fake path restriction** | **Confirmed & Implemented** | `--offline-fake` strictly refuses to write to default path `data/synthetic/cs_concept_names.json`, requiring an explicit alternate `--output` path. |

---

## 3. Implementation Details

### A. Generator Architecture (`scripts/generate_name_pool.py`)
- **Subfields (`SUBFIELDS`):** 80 curated computer science subfields covering core algorithms, theory, computer architecture, systems, networking, databases, programming languages, software engineering, AI/ML, graphics, security, and scientific computing.
- **Prompt Structure:**
  - `build_system_prompt()`: Instructs the model to act as a CS curriculum expert and output strictly a JSON array of lowercase snake_case strings (1–4 words, no `.txt` suffix, concept names only).
  - `build_user_prompt(subfield, round_num, previous_names)`: Requests 40 concepts for the subfield. In round 2+, appends the JSON array of up to 100 previously collected concepts for that subfield with explicit instructions not to repeat them.
- **Cache Format (`raw_responses.jsonl`):**
  - Logs `round`, `subfield`, `subfield_idx`, `request_system`, `request_user`, `response_text`, `model_id`, `token_usage` (input, output, reasoning, cache hit/miss), `timestamp_utc`, `retries`, and `latency_s`.
- **Validation Pipeline & Drop Reasons:**
  - Evaluates candidates in fixed deterministic order: `(round, subfield_idx, response_position)`.
  - Tracks 9 drop counts in `meta.drop_counts`:
    - `ends_with_txt`: Contains or ends with `.txt`
    - `invalid_snake_case`: Fails `_SNAKE_CASE_RE`
    - `invalid_length`: Length not in `[3, 50]`
    - `invalid_word_count`: Underscore-separated words not in `[1, 5]`
    - `corpus_overlap_exact`: Matches any node in the 12 benchmark corpora
    - `corpus_overlap_embed`: `embed_text()` matches any corpus node payload
    - `duplicate_exact`: Duplicate of an earlier accepted candidate
    - `duplicate_embed`: `embed_text()` duplicate of an earlier accepted candidate
    - `plural_pair`: Plural form of a singular concept present in the pool (e.g. $X + \text{"s"}$ or $X + \text{"es"}$)
- **Deterministic Shuffling:**
  - Candidate list after plural filtering is shuffled using `random.Random(42).shuffle(names)`.
- **Metadata (`meta`):**
  - Includes `schema_version`, `domain`, `generator`, `configured_model_alias`, `response_reported_model_ids`, `temperature`, `max_tokens`, `prompt_version`, `run_ids`, `first_utc_timestamp`, `last_utc_timestamp`, `n_raw`, `n_valid`, `drop_counts`, `seed`, `sha256_names`, `sha256_raw_responses`, and `corpora_checked` (12 corpora names).

### B. Client Extension (`src/graph_insertion/llm.py`)
- Extended `DeepSeekClient.__init__`:
  ```python
  def __init__(
      self,
      api_key: Optional[str] = None,
      base_url: Optional[str] = None,
      model: Optional[str] = None,
      *,
      timeout: float = 60.0,
      max_retries: int = 3,
      backoff_delays: Sequence[float] = (1.0, 2.0, 4.0),
      client: Optional[httpx.Client] = None,
      temperature: float = 0.0,
      max_tokens: int = 16,
  ) -> None:
  ```
  Preserves default temperature (0.0) and max_tokens (16) while allowing custom configurations for generation tasks.

---

## 4. Test Suite Verification

All **291 tests** collected across 13 test modules pass cleanly (289 passed, 2 skipped due to non-embedding identity tests on `NullStrategy` and `FakeNarrowingStrategy`).

### Per-File Collected Test Breakdown

| Test File | Collected Tests | Passed | Skipped | Failed |
| :--- | :---: | :---: | :---: | :---: |
| `tests/test_decision.py` | 15 | 15 | 0 | 0 |
| `tests/test_generate_name_pool.py` *(new)* | 16 | 16 | 0 | 0 |
| `tests/test_graph_representation.py` | 51 | 51 | 0 | 0 |
| `tests/test_harness.py` | 16 | 16 | 0 | 0 |
| `tests/test_harness_embedding.py` | 2 | 2 | 0 | 0 |
| `tests/test_live_guard.py` | 27 | 27 | 0 | 0 |
| `tests/test_llm.py` | 12 | 12 | 0 | 0 |
| `tests/test_loader.py` | 26 | 26 | 0 | 0 |
| `tests/test_null_strategy.py` | 39 | 39 | 0 | 0 |
| `tests/test_pilot.py` | 15 | 15 | 0 | 0 |
| `tests/test_schedule.py` | 21 | 21 | 0 | 0 |
| `tests/test_scoring.py` | 7 | 7 | 0 | 0 |
| `tests/test_strategy_interface.py` | 44 | 42 | 2 | 0 |
| **Total** | **291** | **289** | **2** | **0** |

### Test Runner Summary (`pytest -q | tail -3`)

```
.....                                                                    [100%]

======================= 289 passed, 2 skipped in 25.89s ========================
```

---

## 5. Found but Not Changed

1. **Pending Chapter 3 and Context Updates (DOC-002):**
   `complete-context.md` Section 4 still refers to source text as an open question, and `data-formats.md` states "7 of the 10" filenames have underscores. These items are reserved for task DOC-002 and were left untouched.
2. **Live Name Pool Generation:**
   Per task instructions, live generation against the DeepSeek API was not executed by this agent; Luke will run `scripts/generate_name_pool.py --live --confirm` himself during an off-peak pricing window to populate `data/synthetic/cs_concept_names.json`.
3. **Harness and Experiment Runner Code:**
   `scripts/run_experiment.py`, `src/graph_insertion/harness.py`, and `src/graph_insertion/decision.py` were not modified.

---

## 6. Shared Documentation Git Diffs

### Diff: `docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index cf2de98..8dbf714 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -338,3 +338,12 @@ Reasoning: prevents subtle discrepancies between guard cost estimation and harne
 (4) Model alias resolution and live pre-flight reporting: `resolve_model_alias(model: Optional[str] = None) -> str` is centralized in `src/graph_insertion/llm.py` with precedence `model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"`. `DeepSeekClient.__init__` delegates directly to this helper. In `scripts/run_experiment.py`, pre-flight telemetry logs the resolved alias explicitly as `"Model alias: <resolved>"`.
 (5) Clean live-run missing API key handling: when `--live` is specified without `--dry-run` and `DEEPSEEK_API_KEY` is unset or empty, `scripts/run_experiment.py:main()` catches `ValueError` from `build_live_client`, prints `ERROR: <msg>` to `sys.stderr`, and exits with code 1 without dumping a Python traceback.
 Reasoning: prevents subtle discrepancies between guard cost estimation and harness execution, eliminates duplicate trial-key and sampling logic, provides unambiguous operator feedback on model alias and authentication configuration, and hardens the CLI against unhandled exception traces. Affects: `src/graph_insertion/harness.py`, `src/graph_insertion/llm.py`, `src/graph_insertion/__init__.py`, `scripts/run_experiment.py`, `tests/test_live_guard.py`, `docs/tasks/status.md`, FIX-010.
+
+**[D-39]** Synthetic concept-name pool generation architecture, prompt schema, validation pipeline, and provenance controls (DATA-004):
+(1) Generator model and configuration: synthetic computer-science concept names are generated using DeepSeek V4.1 Flash via `DeepSeekClient` wrapped in `MeteredLLMClient` with official alias `deepseek-flash`, thinking mode disabled (`{"thinking": {"type": "disabled"}}`), temperature 0.7 (enabling vocabulary variety while preserving curriculum relevance), max_tokens 1500, and concurrency 1 (sequential execution). In `DeepSeekClient`, optional constructor parameters `temperature: float = 0.0` and `max_tokens: int = 16` are exposed with unchanged defaults for backward compatibility.
+(2) Subfields and iterative prompt design: generation queries a curated, version-pinned sequence of 80 distinct computer science subfields (`SUBFIELDS`, prompt version `NAME_POOL_PROMPT_VERSION = "np1"`). Each call requests 40 distinct, specific core concept names formatted as a JSON array of lowercase snake_case strings (1–4 words each, no descriptions, no file extensions). In Round 2 and later, prompts include a capped list of up to 100 concepts already collected for that subfield with explicit instructions not to repeat them. Generation loops rounds until at least 2,600 valid names exist or `--max-calls` (default 400) is reached.
+(3) Streaming raw cache and deterministic pool assembly: every generation response is logged to `results/datagen/<run_id>/raw_responses.jsonl` with full prompt, response text, reported model ID, token usage, latency, retries, round, and subfield. Resumption from cache re-requests only incomplete pairs whose cached response failed to parse as a JSON array. Pool construction is deterministic from cache: candidates are evaluated in fixed order `(round, subfield_idx, response_position)` and filtered against nine drop reasons: `.txt` suffix/containment, snake_case pattern (`^[a-z][a-z0-9]*(_[a-z0-9]+)*$`), character length `[3, 50]`, word count `[1, 5]`, exact corpus overlap, embed_text corpus overlap across all 12 benchmark corpora, exact duplicate in pool, embed_text duplicate in pool, and near-duplicate plural pairs (if both $X$ and $X+\text{"s"}$ or $X+\text{"es"}$ exist, dropping the plural form). The deduped, filtered list is shuffled with `random.Random(42)`.
+(4) Output format, location, and repository tracking: the finalized pool is written to tracked file `data/synthetic/cs_concept_names.json` in object format `{"meta": {...}, "names": [...]}`, passing `load_and_validate_names_file(path, min_required_names=2001)` unchanged. The final pool file is tracked in git because it defines the exact invariant benchmark concepts for the cost-scaling sweep across all four strategies, whereas `raw_responses.jsonl` under `results/` is gitignored to avoid checking large intermediate API generation logs into version control.
+(5) Verification and execution gates: CLI script `scripts/generate_name_pool.py` provides `--offline-fake` (simulated generator for testing, strictly refusing to write the default tracked path without explicit `--output`), `--dry-run` (zero-call cost and peak planning), `--live` (gated by `--confirm`, `DEEPSEEK_API_KEY`, and off-peak schedule guard), `--build-only` (offline deterministic rebuild from cache with load assertion), and `--verify` (cryptographic SHA256 verification of names and raw cache, regex and plural integrity, and corpus disjunction).
+(6) Known limitation: the generator utilizes the same model family (DeepSeek Flash) as the experimental decision step ([D-29]). While synthetic names are evaluated only for cost scaling and graph insertion complexity (never ground-truth accuracy), using the same model family is accepted because names function strictly as structural graph identifiers and text embedding payloads, not as evaluation judgments.
+Reasoning: delivers a reproducible, fully-auditable synthetic concept pool satisfying all sweep constraints without contaminating ground-truth corpora, enforces strict budget and schedule safety, and preserves determinism across experimental runs. Affects: `scripts/generate_name_pool.py`, `src/graph_insertion/llm.py`, `tests/test_generate_name_pool.py`, `tests/test_llm.py`, `docs/tasks/status.md`, DATA-004.
```

### Diff: `docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index a6e4eda..b3c93ff 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -28,7 +28,7 @@ Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-1
 | DATA-001  | Independently re-verify every claim in `docs/context/data-formats.md` against the full raw files (not just head/tail excerpts). Specifically: confirm DSA and Metacademy delimiter/label conventions; check for delimiter-collision edge cases in both; inspect at least two of the ten example MEKG files (one small, one large) to confirm their format; inspect `concept_descriptions/` folder contents and assess sufficiency as build-phase source text. | **done** | Completed by Gemini. See report [`docs/reports/DATA-001-gemini-verify-file-formats.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-001-gemini-verify-file-formats.md). |
 | DATA-002  | Resolve edge directionality convention for all ten example MEKG files (`MEKG_with*.txt`) relative to DSA/Metacademy ([D-15]).                                                                                                                                                                                                                                                                                                                               | **done** | Completed by Gemini. All 10 files confirmed reversed from D-15 (col1 = prerequisite, col2 = dependent). See report [`docs/reports/DATA-002-gemini-mekg-directionality.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-002-gemini-mekg-directionality.md). |
 | DATA-003  | Decide where build-phase source text comes from now that `concept_descriptions/` is ruled out for DSA/Metacademy (D-17).                                                                                                                                                                                                                                                                                                                                     | **done** | Decided by Luke 2026-10-03: names only, no node text ([D-21]). Evidence in [`docs/reports/DATA-003-gemini-source-text-evidence.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-003-gemini-source-text-evidence.md). |
-| DATA-004  | Generate the synthetic large-n concept-name sets (sweep sizes 50, 100, 200, 500, 1000, 2000 x 10 trials; CS domain, graph-level domain string "computer science", snake_case per D-21, no edges, fixed seed, cached, deduplicated, no overlap with any corpus node, >=2100 names; [D-35]). Embedding model choice is settled: local sentence-transformers all-MiniLM-L6-v2 on CPU. | **open** | Parameters and embedding choice locked per [D-35]; prompt not yet written; needed by INFRA-004's cost sweep. |
+| DATA-004  | Generate the synthetic large-n concept-name sets (sweep sizes 50, 100, 200, 500, 1000, 2000 x 10 trials; CS domain, graph-level domain string "computer science", snake_case per D-21, no edges, fixed seed, cached, deduplicated, no overlap with any corpus node, >=2100 names; [D-35]). Embedding model choice is settled: local sentence-transformers all-MiniLM-L6-v2 on CPU. | **needs-review** | Completed by Claude Code. Script delivered; pool not yet generated; Luke runs the live step ([D-39]). 291 total tests collected (289 passing, 2 skipped). See report [`docs/reports/DATA-004-claude-code-name-pool-generator.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-004-claude-code-name-pool-generator.md). |
 | INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                                                         | **done** | Completed. Library locked as NetworkX via `ConceptGraph` wrapper ([D-22]); canonical edge direction locked as prereq -> dependent ([D-23]); dual-mapping implemented and verified without conflict against all 10 MEKG files. See report [`docs/reports/INFRA-001-claude-code-graph-representation.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-001-claude-code-graph-representation.md). |
 | INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **done** | Completed. Strategy contract, lifecycle, Embedder protocol, MeteredEmbedder, FakeEmbedder, and insert_node driver defined ([D-24], [D-25]). Conformance suite passes (62 tests). See spec [`docs/context/strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/context/strategy-interface.md) and report [`docs/reports/INFRA-002-gemini-strategy-interface.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-002-gemini-strategy-interface.md). |
 | INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **done** | Completed by Gemini. Discovers 12 corpora, loads into `ConceptGraph` and `GoldJudgmentSet` with strict parsing, canonical orientations via `oriented_edge` ([D-15], [D-19], [D-23]), and graph-level domain context table ([D-27]). All 12 graphs confirmed DAGs. See report [`docs/reports/INFRA-003-gemini-corpus-loader.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-003-gemini-corpus-loader.md). |
```
