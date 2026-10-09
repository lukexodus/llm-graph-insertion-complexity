# STRAT-002 — Strategy 2: Embedding-Similarity Thresholding (+ Shared Test Helper)

**Task ID:** STRAT-002  
**Decision ID:** D-46  
**Date:** 2026-10-09  

---

## 1. Agent Identity

- **Agent:** `gemini`
- **Model Label:** `Gemini 3.8 Flash (High)`

---

## 2. What Was Asked / What I Did

### What was asked
1. Verify Part 0 items (git HEAD, module export paths, embed_text format, Embedder protocol, FakeEmbedder cosine spread, conformance factory typing, harness json.dumps metrics serialization, tests packaging, strategies __init__.py).
2. Implement `tests/controllable_embedder.py` defining `ControllableEmbedder` (with D-21 key convention via `embed_text`, unnormalised vector passthrough, strict mode, copy semantics, and fallback to `FakeEmbedder`) and `vector_with_cosine(base, cosine)` helper.
3. Implement `tests/test_controllable_embedder.py` with comprehensive unit tests for `ControllableEmbedder` and `vector_with_cosine`.
4. Implement `src/graph_insertion/strategies/embedding_threshold.py` defining `EmbeddingThresholdStrategy` (`name = "embedding_threshold"`, `DEFAULT_THETA = 0.6`, `uses_embeddings = True`, no `max_candidates`, strict `>` filtering, descending score tie-broken alphabetically, O(d) amortised index update, single-embedding caching invariant, JSON-safe diagnostics).
5. Implement `tests/test_embedding_threshold_strategy.py` covering `StrategyConformanceSuite`, threshold logic, tie-breaking, strict boundary, sensitivity nesting, unnormalised vectors, zero candidates, single-embedding invariant, empty graph handling, buffer growth vs numpy reference, validation, JSON serialization, and sweep harness smoke test.
6. Append pre-assigned decision entry `[D-46]` to `docs/decisions/decision-log.md` and update `docs/tasks/status.md` STRAT-002 row to `needs-review`.

### What I did
- Verified all Part 0 items against the live repository without exception.
- Created `tests/controllable_embedder.py` with full docstring, usage example, and strict protocol conformity.
- Created `tests/test_controllable_embedder.py` (18 unit tests, all passing).
- Created `src/graph_insertion/strategies/embedding_threshold.py` following all locked thesis and decision requirements.
- Created `tests/test_embedding_threshold_strategy.py` (25 test cases across 6 test classes, all passing).
- Appended `[D-46]` to `docs/decisions/decision-log.md` and updated STRAT-002 in `docs/tasks/status.md`.
- Ran the full test suite (`365 passed, 3 skipped in 66.21s`, zero failures).

---

## 3. Prompt Corrections

Every statement in the prompt was verified against the repository:

1. **Part 0(a) Git HEAD and status:** Prompt noted potential concurrent thread changes. Verified: initial checkout at commit `20bfe62` contained concurrent unstaged edits in `docs/context/prompt-adapter-contract.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `scripts/generate_name_pool.py`, `tests/stub_prompt_adapter.py`, `tests/test_generate_name_pool.py`. Prompt was **RIGHT**.
2. **Part 0(b) Module exports:** `Shortlist`, `candidate_upper_bound`, `insert_node` in `graph_insertion.strategy`; `Embedder`, `MeteredEmbedder`, `FakeEmbedder` in `graph_insertion.embedding`; `ConceptGraph`, `embed_text` in `graph_insertion.graph_representation`. All are re-exported in `src/graph_insertion/__init__.py`. Prompt was **RIGHT**.
3. **Part 0(c) `embed_text(name)`:** Confirmed in `src/graph_insertion/graph_representation.py:110` that it returns `name.replace("_", " ")` and nothing else. Prompt was **RIGHT**.
4. **Part 0(d) `Embedder` protocol and `FakeEmbedder` spread:** `Embedder` is `@runtime_checkable` Protocol with `embed` and `embed_many`. `FakeEmbedder` vectors are L2-normalised float32; pairwise cosines between unrelated concepts concentrate near 0 (range $[-0.5023, +0.4830]$, none exceeding $\theta=0.6$). Prompt was **RIGHT**.
5. **Part 0(e) Factory typing in `StrategyConformanceSuite`:** `strategy_factory` is called with raw `FakeEmbedder` at lines 232, 249, 266, 378 and with `MeteredEmbedder` at lines 290, 324, 352, 401. Thus `setup()` must accept `Embedder` generally and not assert `isinstance(..., MeteredEmbedder)`. Prompt was **RIGHT**.
6. **Part 0(f) Diagnostics serialization in harness:** In `src/graph_insertion/harness.py:864, 1091`, records are written via `json.dumps({"metrics": asdict(res.metrics), ...})`. `asdict` leaves NumPy scalar types intact (`np.float32`, `np.int64`), which causes `json.dumps()` to raise `TypeError: Object of type float32 is not JSON serializable`. Plain Python types (`float`, `int`, `None`) are required. Prompt was **RIGHT**.
7. **Part 0(g) Test imports:** `tests/__init__.py` exists, allowing `from tests.controllable_embedder import ...`. Prompt was **RIGHT**.
8. **Part 0(h) Strategies package init:** `src/graph_insertion/strategies/__init__.py` exists. Prompt was **RIGHT**.
9. **Thesis Section 3.2.3 threshold rule:** Thesis Section 3.2.3 explicitly specifies "Only nodes whose similarity exceeds a fixed threshold are shortlisted", which requires strict `>` (not `>=`). Prompt was **RIGHT**.
10. **`candidate_upper_bound` fallback:** When `max_candidates` is omitted on a strategy, `candidate_upper_bound(strat, n)` returns `n`. Prompt was **RIGHT**.

---

## 4. Part 0 Findings (a–h)

- **a. Git start state:** Commit `20bfe62`. `git status --short` showed modified shared docs and generator scripts from another thread.
- **b. Module exports:** All specified symbols exist in their respective modules and are exported in `src/graph_insertion/__init__.py`.
- **c. `embed_text` implementation:** Exact implementation is `def embed_text(name: str) -> str: return name.replace("_", " ")`.
- **d. `FakeEmbedder` cosine spread:** Evaluated on 8 concepts (`pointer`, `linked_list`, `graph`, `recursion`, `hash_table`, `dijkstra_algorithm`, `binary_search_tree`, `heap`) with `FakeEmbedder(dim=16, seed=42)`:
  - Minimum cosine: `-0.5023` (`linked_list` vs `graph`)
  - Maximum cosine: `+0.4830` (`graph` vs `recursion`)
  - Mean cosine: `+0.0383`
  - 100% of pairs have cosine $< 0.6$. This empirically proves why `FakeEmbedder` cannot be used to test similarity thresholding logic at $\theta = 0.6$, confirming the necessity of `ControllableEmbedder`.
- **e. Conformance suite embedder types:** `StrategyConformanceSuite` exercises `strategy_factory` with both `FakeEmbedder` and `MeteredEmbedder`.
- **f. Diagnostics JSON serializability:** `harness.py` writes trial records directly via `json.dumps(rec)` after `asdict(res.metrics)`. Any `np.float32` or `np.int64` in `diagnostics()` raises a `TypeError` in `json.dumps()`. Diagnostics must use Python built-in `float`, `int`, `str`, `None`.
- **g. Test module imports:** `tests/__init__.py` exists; imports like `from tests.controllable_embedder import ControllableEmbedder, vector_with_cosine` work cleanly.
- **h. `src/graph_insertion/strategies/__init__.py`:** Exists on disk and was preserved untouched.

---

## 5. Verification Output

### Command: `pytest -q tests/test_controllable_embedder.py tests/test_embedding_threshold_strategy.py | tail -3`
```
tests/test_embedding_threshold_strategy.py .........................     [100%]

============================== 43 passed in 2.38s ==============================
```

### Command: `pytest -q | tail -3`
```
.....                                                                    [100%]

================== 365 passed, 3 skipped in 66.21s (0:01:06) ===================
```

### Command: `wc -l` and `sha256sum` of each new file
```
  300 src/graph_insertion/strategies/embedding_threshold.py
  218 tests/controllable_embedder.py
  169 tests/test_controllable_embedder.py
  497 tests/test_embedding_threshold_strategy.py
 1184 total
e863aadc35844c9acac897e1cd4acb223d65721ac9a483d38ff1d32adf6df37a  src/graph_insertion/strategies/embedding_threshold.py
6990fc2e285202b0ab6d69e10e624a92d410e7e57524d25732fcc8561637720f  tests/controllable_embedder.py
ec2af53c132b4d7d1582e25c08f75eab12d39f10cf56f5901bd151716e13d7d4  tests/test_controllable_embedder.py
5c1bf0728bacb571aa98b30d7fab2ccd39891325eb7a7f006a64996a6fe806f1  tests/test_embedding_threshold_strategy.py
```

### Command: `git status --short`
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
?? docs/reports/STRAT-002-gemini-embedding-threshold.md
?? scripts/README.md
?? src/graph_insertion/strategies/brute_force.py
?? src/graph_insertion/strategies/embedding_threshold.py
?? tests/controllable_embedder.py
?? tests/test_brute_force_strategy.py
?? tests/test_controllable_embedder.py
?? tests/test_embedding_threshold_strategy.py
```

---

## 6. Shared-Doc Diffs

### Command: `git diff -- docs/decisions/decision-log.md docs/tasks/status.md`

*(Note: the diff below includes concurrent uncommitted hunks from FIX-011 [D-44] and STRAT-001 [D-45]. The STRAT-002 hunks are `[D-46]` in `decision-log.md` and line 48 in `status.md`)*

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 80f5244..1f370ab 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -356,3 +356,31 @@ Reasoning: delivers a reproducible, fully-auditable synthetic concept pool satis
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
+
+**[D-46]** Strategy 2 embedding-similarity thresholding implementation and controllable embedder test helper (STRAT-002):
+(1) Module and contract: `src/graph_insertion/strategies/embedding_threshold.py` implements `EmbeddingThresholdStrategy` with class attributes `name = "embedding_threshold"`, `uses_embeddings = True`, module constant `DEFAULT_THETA = 0.6`, constructor parameters `theta: float = DEFAULT_THETA` (validated real, finite, within `[-1.0, 1.0]`) and `seed: int = 42`. It intentionally does NOT define `max_candidates`, allowing `candidate_upper_bound()` to fall back to brute-force $n_{\text{existing}}$ because Strategy 2 is uncapped.
+(2) Cosine similarity & normalization: similarity is computed as cosine similarity over L2-normalized float32 vectors. Concept vectors are normalized exactly once upon index ingest (during `setup()` and `on_inserted()`) and the query vector is normalized once in `shortlist()`. The index matrix is never renormalized per query, and vectors from the embedder are never assumed to be unit-length. Candidate scoring uses a vectorized matrix-vector product (`_mat[:_n] @ q`) in float32.
+(3) Strict thresholding: candidates are filtered by `score > theta` (strictly greater, following thesis Chapter 3 Section 3.2.3 "exceeds a fixed threshold", not `>=`).
+(4) Shortlist ordering and structure: shortlisted candidates are ordered by `(-score, name)` (descending score, ties broken alphabetically ascending by concept name). Scores are returned as parallel tuples of native Python `float` values. No top-k cap is applied. An empty shortlist (`Shortlist(candidates=(), scores=())`) is a valid result (resulting in 0 LLM calls in the driver). `new_name` is always excluded from candidates even if already present in the index.
+(5) Single-embedding invariant & caching: `shortlist(new_name)` always embeds `new_name` exactly once first via `self._embedder.embed(embed_text(new_name))` (even when the initial index is empty), normalizes, and caches `(new_name, vector)`. `on_inserted(new_name, edges)` reuses this cached vector and clears the cache; attempting `on_inserted()` without a matching prior `shortlist()` raises `RuntimeError`, attempting to insert an already-indexed concept raises `ValueError`, and `self._embedder` is never called during `on_inserted()`. The `edges` parameter is accepted and ignored because Strategy 2 indexing depends purely on concept embeddings without graph topology.
+(6) Amortized O(d) index updates: the internal float32 matrix buffer `_mat` is preallocated with capacity doubling (starting at $\max(16, n)$), ensuring `on_inserted()` runs in amortized $O(d)$ time without triggering $O(n \cdot d)$ copies per insertion via `np.vstack`, which would otherwise artificially distort the timed `update_s` metric ([D-25]).
+(7) Diagnostics: `diagnostics()` returns a dictionary with plain Python types (`int`, `float`, `None`): `{"cosine_comparisons": int, "threshold": float, "shortlist_size": int, "max_cosine": float | None, "index_size": int}`, surviving `json.dumps()` serialization.
+(8) Shared controllable embedder helper: `tests/controllable_embedder.py` provides `ControllableEmbedder` (supporting specified unnormalized float32 vectors for concept names converted via `embed_text()`, collision detection, strict mode, copy semantics, and fallback to `FakeEmbedder`) and `vector_with_cosine(base, cosine)` (producing exact unit-norm float32 vectors with target cosine within $10^{-6}$ via Gram-Schmidt), established as the shared helper for STRAT-003 and STRAT-004.
+(9) Sensitivity runs: sensitivity sweeps at $\theta = 0.4$ and $0.5$ retain identical strategy class identity `name = "embedding_threshold"`. Consequently, sensitivity experiments must output to separate run directories and analysis must key on `config()["theta"]` (an INFRA-007 concern).
+(10) Prompt corrections: Part 0 verified all prompt statements; prompt claim (d) regarding near-zero cosine spread for `FakeEmbedder` was confirmed (empirical cosine spread $[-0.5023, +0.4830]$ across sample concepts), affirming the necessity of `ControllableEmbedder`.
+Reasoning: delivers Strategy 2 candidate-narrowing matching thesis Section 3.2.3, enforces strict driver embedding and timing contracts, and equips downstream strategy tracks with controllable embedding fixtures. Affects: `src/graph_insertion/strategies/embedding_threshold.py`, `tests/controllable_embedder.py`, `tests/test_controllable_embedder.py`, `tests/test_embedding_threshold_strategy.py`, `docs/tasks/status.md`, STRAT-002, STRAT-003, STRAT-004, INFRA-007.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index ece2b7a..574864e 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -44,8 +44,8 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 
 | ID        | Task                                       | Status | Notes                                                                          |
 | --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
-| STRAT-001 | Implement Strategy 1 (brute-force)         | open   | —                                                                              |
-| STRAT-002 | Implement Strategy 2 (embedding-threshold) | open   | —                                                                              |
+| STRAT-001 | Implement Strategy 1 (brute-force)         | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC. See report [`docs/reports/STRAT-001-gemini-brute-force.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-001-gemini-brute-force.md). |
+| STRAT-002 | Implement Strategy 2 (embedding-threshold) | **needs-review** | Implemented by Gemini; reviewer to be assigned by APC; adds shared tests/controllable_embedder.py. See report [`docs/reports/STRAT-002-gemini-embedding-threshold.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/STRAT-002-gemini-embedding-threshold.md). |
 | STRAT-003 | Implement Strategy 3 (ANN retrieval)       | open   | —                                                                              |
 | STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |
 
@@ -83,3 +83,4 @@ Status: **not started** (blocked on Phase 3)
 | FIX-008 | Harden INFRA-005: worst-case live guard estimation and pre-flight telemetry, window_intersects_peak exact end point check, call-driven progress reporting with 30s heartbeat hook on MeteredLLMClient and retry double-count fix, embedding strategy exercised through sweep and accuracy harness runners with metrics in raw.jsonl and summary.csv, strict names validation without exception swallowing and embed_text form collision detection, and strengthened unit tests (resume, process-local --max-llm-calls, spot-check recall branches, analytic recall convergence) ([D-40]). | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07. 252 total tests collected (250 passing, 2 skipped). See report [`docs/reports/FIX-008-claude-code-infra005-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-008-claude-code-infra005-hardening.md). |
 | FIX-009 | Pre-live hardening of run_experiment.py guard and progress path: strategy-aware candidate_upper_bound and max_candidates bound deduction with CALLS_PER_CANDIDATE ([D-41](1)), resume-aware deduction via _load_existing_keys subtracting completed trials, max-llm-calls capping, wired ProgressReporter and peak check to remaining bound ([D-41](2)), live sweep --names-file DATA-004 gate, --live --dry-run zero-cost verification ([D-41](3)), isolated build_live_client factory, MeteredLLMClient on_call callback exception accounting ([D-41](4)), non-minute-aligned schedule test, StrategyConformanceSuite max_candidates bound verification, and analytic recall docstring correction. | **done** | Completed by Claude Code. Accepted at APC review 2026-10-07; follow-up FIX-010. 266 total tests collected (264 passing, 2 skipped). See report [`docs/reports/FIX-009-claude-code-prelive-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-009-claude-code-prelive-hardening.md). |
 | FIX-010 | Single-source-of-truth trial keys, held-out sampling, and resume filter in harness and guard estimator ([D-42]); live-guard tests against real harness runs; candidate bound clamping/fallback tests; clean CLI error on missing API key; model alias resolution. | **needs-review** | Completed by Gemini. 275 total tests collected (273 passing, 2 skipped). See report [`docs/reports/FIX-010-gemini-resume-estimate-unification.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-010-gemini-resume-estimate-unification.md). |
+| FIX-011 | Command backend adapter error code parsing (string error codes and process exit code fallback), process-group session termination on timeout (Popen, SIGTERM to group, 10s wait, SIGKILL), headed execution and model bias corrections ([D-44]). | **needs-review** | Completed by Gemini. Contract fixtures updated in `docs/context/prompt-adapter-contract.md`, stub and subprocess tests added in `tests/test_generate_name_pool.py`. 302 total tests collected (300 passing, 2 skipped). See report [`docs/reports/FIX-011-claude-code-command-backend-error-codes.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-011-claude-code-command-backend-error-codes.md). |
```

---

## 7. Found but Not Changed

- Untracked files present in checkout:
  - `apc-bundle-20261009-1434.tar.gz`
  - `docs/reports/FIX-011-claude-code-command-backend-error-codes.md`
  - `docs/reports/STRAT-001-gemini-brute-force.md`
  - `scripts/README.md`
  - `src/graph_insertion/strategies/brute_force.py`
  - `tests/test_brute_force_strategy.py`
- Concurrent unstaged changes from parallel threads:
  - `docs/context/prompt-adapter-contract.md`
  - `scripts/generate_name_pool.py`
  - `tests/stub_prompt_adapter.py`
  - `tests/test_generate_name_pool.py`
  - Hunks for FIX-011 and STRAT-001 in `docs/decisions/decision-log.md` and `docs/tasks/status.md`.
  None of these files were modified or reverted. All existing rules regarding untouched core modules (`harness.py`, `llm.py`, `__init__.py`, `strategy.py`, `embedding.py`, `graph_representation.py`, `strategies/null.py`, `pyproject.toml`) were strictly respected.

---

## 8. Open Questions

- None for STRAT-002 implementation. In INFRA-007 (registry wiring and CLI execution), sensitivity sweeps for Strategy 2 at $\theta \in \{0.4, 0.5, 0.6\}$ should be allocated distinct run directory paths while preserving `strategy.name == "embedding_threshold"`, with downstream analysis scripts keying on `config()["theta"]`.
