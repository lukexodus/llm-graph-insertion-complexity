# STRAT-001 — Strategy 1: Brute-Force Narrowing Implementation Report

## 1. Agent Identity

- **Agent:** `gemini`
- **Model:** Gemini 3.8 Flash (High)

---

## 2. What Was Asked / What I Did

### What was asked
Implement Strategy 1 (brute-force candidate narrowing) under task STRAT-001, adhering strictly to:
- Protocol contract `NarrowingStrategy` defined in `src/graph_insertion/strategy.py` ([D-24]).
- Pairwise decision step and cost model ([D-29]).
- Non-embedding strategy conformance semantics with `uses_embeddings = False` and `_embedder = None` ([D-38](2)).
- Candidate upper bound helper `max_candidates(n_existing) -> int` returning exact bound `max(0, n_existing)` ([D-41]).
- Full test coverage: conformance suite subclass, unit tests, driver tests via `insert_node`, 2000-node scale sanity, and harness smoke test.
- Bookkeeping: record `[D-45]` in `docs/decisions/decision-log.md` and update `docs/tasks/status.md`.

### What I did
1. Verified Part 0 questions (a–h) against live repository files prior to editing.
2. Created `src/graph_insertion/strategies/brute_force.py` with `BruteForceStrategy`:
   - Class attributes `name = "brute_force"` and `uses_embeddings = False`.
   - `__init__(seed=42)` initializes `self.seed`, `self._graph = None`, `self._embedder = None`, and `self._last_candidate_count = 0`.
   - `setup(graph, embedder)` stores graph reference, discards embedder (`_embedder` remains `None`).
   - `shortlist(new_name)` raises `RuntimeError` if called before `setup()`. Returns all existing nodes excluding `new_name` sorted ascending, with uniform `0.0` scores. Updates `_last_candidate_count`.
   - `on_inserted(new_name, edges)` is a stateless no-op.
   - `max_candidates(n_existing)` returns `max(0, n_existing)` and functions before `setup()`.
   - `config()` returns `{"seed": self.seed}`; `diagnostics()` returns `{"candidate_count": self._last_candidate_count}`.
3. Created `tests/test_brute_force_strategy.py` covering:
   - `TestBruteForceConformance(StrategyConformanceSuite)` with `uses_embeddings = False`.
   - Unit tests for sorting, exclusion, empty graph, determinism across insertion orders, `max_candidates`, D-35 matrix bound (38,500), `setup()` guard `RuntimeError`, `_embedder is None`, and JSON serializability.
   - Driver tests via `insert_node` verifying `llm_calls == n_before == shortlist_size` at sizes 1, 5, 29 with 0 embedding calls, and candidate accumulation across repeated insertions.
   - Scale sanity test with 2000 nodes.
   - Offline sweep harness smoke test asserting trial success, strategy name `"brute_force"`, and `llm_calls == n`.
4. Appended `[D-45]` to `docs/decisions/decision-log.md`.
5. Updated STRAT-001 row in `docs/tasks/status.md` to `needs-review`.

---

## 3. Prompt Corrections

Every statement and assumption in the prompt was checked against the repository:

| Prompt Statement | Status | Verification / Evidence |
| :--- | :--- | :--- |
| Pre-assigned decision ID `D-45` | **Correct** | Preceding decision in `decision-log.md` was `D-44` (from FIX-011). `D-45` appended sequentially. |
| Context and code files exist at stated paths | **Correct** | All listed files exist and matched expected roles. |
| Exported symbols in `graph_insertion/__init__.py` | **Correct** | All 6 queried symbols (`Shortlist`, `candidate_upper_bound`, `insert_node`, `ConceptGraph`, `FakeEmbedder`, `MeteredEmbedder`) are exported in `__all__`. |
| `NullStrategy` attributes & behavior | **Correct** | `name = "null"`, `uses_embeddings = False`, `_embedder = None`, uniform 0.0 scores verified in `src/graph_insertion/strategies/null.py`. |
| `StrategyConformanceSuite` with `uses_embeddings = False` | **Correct** | Verified in `tests/test_strategy_interface.py:300-340`; checks `calls == 0`, `embed_s == 0.0`, `texts_log == []`. |
| `src/graph_insertion/strategies/__init__.py` exists | **Correct** | File exists and exports `NullStrategy`. Left untouched. |
| `Shortlist.scores` requirements | **Correct** | Grep showed only `strategy.py:294-297` validates `len(scores) == len(candidates)` if not `None`. Nothing mandates non-None. |
| Test module import style | **Correct** | Existing pattern is `from tests.test_strategy_interface import ...`. |
| D-35 sweep sizes and trial counts | **Correct** | `(50, 100, 200, 500, 1000, 2000)` and `10` are default fields on `HarnessConfig`. Literals used with D-35 citation. |
| Driver accounting `llm_calls == n_existing` | **Correct** | `FakeDecisionStep` and `PairwiseDecisionStep` both make 1 call per candidate. |
| D-35 full-matrix candidate bound = 38,500 | **Correct** | $10 \times (50 + 100 + 200 + 500 + 1000 + 2000) = 10 \times 3850 = 38,500$. Verified programmatically. |

No incorrect claims were found in the prompt.

---

## 4. Part 0 Findings (a–h)

- **a. Initial git status:**
  - `git rev-parse --short HEAD`: `20bfe62`
  - `git status --short`:
    ```
     M docs/context/prompt-adapter-contract.md
     M docs/decisions/decision-log.md
     M docs/tasks/status.md
     M scripts/generate_name_pool.py
     M tests/stub_prompt_adapter.py
     M tests/test_generate_name_pool.py
    ?? apc-bundle-20261009-1434.tar.gz
    ?? apc-bundle.sh
    ?? docs/reports/FIX-011-claude-code-command-backend-error-codes.md
    ```
- **b. Package exports:** All queried symbols (`Shortlist`, `candidate_upper_bound`, `insert_node`, `ConceptGraph`, `FakeEmbedder`, `MeteredEmbedder`) are exported in `src/graph_insertion/__init__.py`.
- **c. NullStrategy contract:** Class attribute `name = "null"`, `uses_embeddings = False`, `_embedder = None` (never stored in `setup`), and scores are uniform `0.0`.
- **d. Non-embedding conformance:** When `uses_embeddings = False`, `StrategyConformanceSuite` asserts zero embedding calls, `embed_s == 0.0`, empty `texts_log`, and zero update embedding calls.
- **e. Strategies `__init__.py`:** `src/graph_insertion/strategies/__init__.py` exists. Left untouched per hard rules.
- **f. Consumers of `Shortlist.scores`:** Grep revealed only `strategy.py:294-297`, which validates length equality if `scores is not None`. No consumer requires it to be non-None.
- **g. Test import style:** Subclass tests import helper classes via `from tests.test_strategy_interface import StrategyConformanceSuite, FakeDecisionStep`.
- **h. Sweep size constants:** `HarnessConfig.sweep_sizes` defaults to `(50, 100, 200, 500, 1000, 2000)` and `HarnessConfig.sweep_trials_per_size` defaults to `10`. Used literals with explicit D-35 citation comments in unit tests.

---

## 5. Verification Output

### 5.1 `pytest -q tests/test_brute_force_strategy.py | tail -3`
```
tests/test_brute_force_strategy.py .......s...............               [100%]

======================== 22 passed, 1 skipped in 2.34s =========================
```

### 5.2 `pytest -q | tail -3`
```
.....                                                                    [100%]

================== 322 passed, 3 skipped in 71.02s (0:01:11) ===================
```

### 5.3 `wc -l` and `sha256sum` of created files
```
  102 src/graph_insertion/strategies/brute_force.py
  296 tests/test_brute_force_strategy.py
  398 total
```
```
a0d57c3cbcc95b73f27f8a198bfd74c991a0403cd7ffce9e9a9bfeb128327eee  src/graph_insertion/strategies/brute_force.py
9c687207e144d2220efe6ed20d2773a7ccd6d631ede55576723ea731040a064d  tests/test_brute_force_strategy.py
```

### 5.4 `git status --short`
```
 M docs/context/prompt-adapter-contract.md
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M scripts/generate_name_pool.py
 M tests/stub_prompt_adapter.py
 M tests/test_generate_name_pool.py
?? apc-bundle-20261009-1434.tar.gz
?? docs/reports/FIX-011-claude-code-command-backend-error-codes.md
?? docs/reports/STRAT-001-gemini-brute-force.md
?? src/graph_insertion/strategies/brute_force.py
?? src/graph_insertion/strategies/embedding_threshold.py
?? tests/controllable_embedder.py
?? tests/test_brute_force_strategy.py
?? tests/test_controllable_embedder.py
```

---

## 6. Shared-Doc Diffs

Verbatim output of `git diff -- docs/decisions/decision-log.md docs/tasks/status.md`:

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 80f5244..00b949f 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -356,3 +356,18 @@ Reasoning: delivers a reproducible, fully-auditable synthetic concept pool satis
 (5) Weaker provenance & operator controls: Claude Web UI generation lacks controllable temperature and max_tokens, and response payloads report model labels without immutable snapshot IDs. To record provenance accurately, pool metadata sets `temperature: null`, `max_tokens: null`, logs `parameter_note`, records requested settings, observed model labels, adapter version, and tier histogram. For benchmark validity, 'Generate memory from chats' must be disabled in the target Claude profile.
 (6) Cross-model independence vs [D-39] limitation: unlike the default DeepSeek generator where both generator and decision step belong to the DeepSeek family ([D-39](6)), the Claude web backend decouples the concept-name generator (Anthropic Claude 3.5 Sonnet) from the downstream experimental decision step (DeepSeek Flash, [D-29]). This eliminates potential intra-model vocabulary bias while preserving zero-overlap disjunction with benchmark corpora.
 Reasoning: provides a robust fallback generation pipeline bypassing DeepSeek API constraints, eliminates model-family co-dependence between name generation and evaluation, enforces clean failure recovery and caching across web UI sessions, and maintains rigorous data provenance. Affects: `scripts/generate_name_pool.py`, `docs/context/prompt-adapter-contract.md`, `tests/test_generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/tasks/status.md`, DATA-005.
+
+**[D-44]** Adapter contract error code parsing, process-group session termination, and headed/model bias corrections to [D-43] (FIX-011):
+(1) Error code contract parsing: `CommandGenerationBackend` in `scripts/generate_name_pool.py` parses the adapter's string error codes per Contract v1: `bad_request` -> 2, `rate_limit` -> 10, `login_required` -> 11, `timeout` -> 12, `refusal` -> 13, `model_mismatch` -> 14, and `other` or unknown string -> 1. If stdout has no usable "error" field (non-JSON output, empty error, or missing error key), it falls back to the process exit code when it is one of the contract codes (`{1, 2, 10, 11, 12, 13, 14}`), else 1. The generation loop's existing exit semantics are preserved: code 10 -> exit 3, code 11 -> exit 4, code 14 -> exit 5, code 2 -> exit 1, and 3 consecutive failures (12, 13, 1, parse errors) -> exit 6.
+(2) Process-group session termination: replaces `subprocess.run(timeout)` with `subprocess.Popen(..., start_new_session=True)` in its own session. On timeout (`timeout_s + 60`), `os.killpg` sends `SIGTERM` to the entire process group (`proc.pid`), waits up to 10 seconds (`proc.wait(timeout=10)`), and escalates to `SIGKILL` if any child process remains alive. This prevents leaked or orphaned browser/adapter child processes upon timeout.
+(3) Correction to [D-43](2) on headed execution: the adapter runs headed by default (`headless: false` in stdin payload). The operator can monitor browser execution and manually solve any interactive Cloudflare/turnstile challenges if needed.
+(4) Correction to [D-43](6) on generator model identity and bias: the generator is Sonnet-tier via the web UI with the label as observed (e.g. "Claude 3.5 Sonnet" or whatever label the web UI presents), not guaranteed immutable "Claude 3.5 Sonnet". Furthermore, using a different model family from the experimental decision step (DeepSeek Flash, [D-29]) reduces but does not eliminate shared-vocabulary bias, as both model families share internet pretraining corpora and standard computer-science curriculum terminology.
+Reasoning: hardens adapter error handling against string code mismatches and orphan processes, aligns contract doc and test stubs with exact specification, and documents precise browser and provenance realities. Affects: `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `docs/context/prompt-adapter-contract.md`, `tests/test_generate_name_pool.py`, `docs/tasks/status.md`, FIX-011.
+
+**[D-45]** Strategy 1 brute-force candidate narrowing implementation and bound (STRAT-001):
+(1) Module and contract: `src/graph_insertion/strategies/brute_force.py` defines `BruteForceStrategy` implementing `NarrowingStrategy` with class attributes `name = "brute_force"` and `uses_embeddings = False`. In `setup(graph, embedder)`, the embedder argument is discarded and `_embedder` remains `None`, bypassing the driver's embedder identity check.
+(2) Shortlist semantics: `shortlist(new_name)` raises `RuntimeError` if called before `setup()`. It produces all existing nodes in `graph.nodes()` excluding `new_name`, sorted in ascending lexicographic order to guarantee determinism independent of node insertion order and `PYTHONHASHSEED`. Scores are returned as a tuple of uniform `0.0` with length matching candidates. On an empty graph, it returns empty candidate and score tuples.
+(3) Candidate bound: `max_candidates(n_existing)` evaluates to `max(0, n_existing)` and is callable before `setup()`. Because brute force evaluates every existing node, this bound is exact; over the D-35 sweep matrix (sizes 50, 100, 200, 500, 1000, 2000 x 10 trials), the total planned calls bound evaluates exactly to 38,500.
+(4) Lifecycle and diagnostics: strategy is stateless, reading the live `ConceptGraph` without cached copies or indexes. `on_inserted(new_name, edges)` is a no-op. `config()` returns `{"seed": self.seed}` and `diagnostics()` returns `{"candidate_count": <int>}` reflecting the size of the most recent shortlist (or 0 before any shortlist).
+(5) Prompt verification: all assumptions in the task prompt were verified against the repo (no contradictions found).
+Reasoning: provides the exhaustive baseline control for incremental graph insertion complexity comparison, establishing the empirical upper bound of O(n) LLM calls per insertion. Affects: `src/graph_insertion/strategies/brute_force.py`, `tests/test_brute_force_strategy.py`, `docs/tasks/status.md`, STRAT-001.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index ece2b7a..b82a7bc 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -44,7 +44,7 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 
 | ID        | Task                                       | Status | Notes                                                                          |
 | --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
-| STRAT-001 | Implement Strategy 1 (brute-force)         | open   | —                                                                              |
+| STRAT-001 | Implement Strategy 1 (brute-force)         | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC. See report [`docs/reports/STRAT-001-gemini-brute-force.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-gemini-brute-force.md). |
 | STRAT-002 | Implement Strategy 2 (embedding-threshold) | open   | —                                                                              |
 | STRAT-003 | Implement Strategy 3 (ANN retrieval)       | open   | —                                                                              |
 | STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |
@@ -83,3 +83,4 @@ Status: **not started** (blocked on Phase 3)
 | FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
 | FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07; follow-up FIX-010. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
 | FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **needs-review** | Completed by Gemini. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
+| FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **needs-review** | Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
```

**Hunks identification:**
- In `docs/decisions/decision-log.md`:
  - `[D-44]` hunk belongs to another thread (FIX-011).
  - `[D-45]` hunk belongs to this task (STRAT-001).
- In `docs/tasks/status.md`:
  - STRAT-001 row (`needs-review`) belongs to this task (STRAT-001).
  - FIX-011 row (`needs-review`) belongs to another thread (FIX-011).

---

## 7. Found but Not Changed

1. **Concurrent thread activity in working tree:**
   - Uncommitted modifications from FIX-011 (`docs/context/prompt-adapter-contract.md`, `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `tests/test_generate_name_pool.py`, `docs/reports/FIX-011-claude-code-command-backend-error-codes.md`).
   - Concurrently created files from STRAT-002 (`src/graph_insertion/strategies/embedding_threshold.py`, `tests/controllable_embedder.py`, `tests/test_controllable_embedder.py`).
   - Neither of these sets of files was modified or deleted, preserving cross-thread isolation.

---

## 8. Open Questions

None. All interfaces and requirements for Strategy 1 are fully resolved and conformant.
