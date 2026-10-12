# INFRA-007 Report: Wire All Four Strategies into the Experiment CLI

**Date:** 2026-10-12
**Task:** INFRA-007 — Wire all four strategies into the experiment CLI (registry, parameters, run-directory keys, real embedder)
**Decision ID:** `[D-64]` (prompt reserved `D-63`, which was already used by `FIX-017`; `D-64` used per operator instruction)
**Status:** `needs-review`

---

## 1. Agent Identity

- **Agent / Model label:** Antigravity — initial discovery/drafting under `Claude Opus 4.6 (Thinking)`, completed and verified under `Gemini 3.8 Flash (High)` (switched mid-session by operator)
- **Conversation / Session ID:** `2b098fc9-f59d-448e-82df-2e60c076a05f`
- **Repository / Branch / Base Commit:** `llm-graph-insertion-complexity`, branch `master`, base commit `78b0014` (post `FIX-017`, ahead of `0131a2b`)

---

## 2. What Was Asked / What I Did

### What Was Asked
1. **A. Strategy Registry (`src/graph_insertion/strategies/registry.py`):** Create a single source of truth `STRATEGY_FACTORIES` for `null`, `stub`, `brute_force`, `embedding_threshold`, `ann_retrieval`, and `bounded_bucket` with factory signature `factory(seed, k, **params)` (`theta`, `ef_search`, `s_min`, `s_max`, `n_bits` defaulting to `None`), preserving backward-compatible `factory(seed, k)` calls and `run_experiment.STRATEGY_REGISTRY`, lazy-importing `ann_retrieval` so `strategies/__init__.py` and `registry.py` load without `faiss` or `sentence_transformers`, and enforcing parameter applicability (exit 2) and range validation (`ValueError` -> exit 1 without traceback).
2. **B. CLI Flags (`scripts/run_experiment.py`):** Add `--theta`, `--ef-search`, `--s-min`, `--s-max`, `--n-bits` (all default `None`), change `-k/--k` default to `None` with help `"candidate shortlist size k: null, stub and ann_retrieval."`, add `--embedder {fake,minilm}` (default `fake`), refuse `--live` with `--embedder fake` for strategies where `uses_embeddings=True`, and verify D-35 sweep planned-call bounds from CLI arguments.
3. **C. Run-Directory Keys & Configuration Guard:** Derive deterministic default directories `results/<mode>_<strategy>` (for `brute_force` at seed 42) or `results/<mode>_<strategy>_<slug>` (`_seed<seed>` appended when `seed != 42`) when neither `--output-dir` nor `--run-id` is passed; write `<output_dir>/strategy_config.json` before the first trial on a fresh directory; refuse `--resume` (or runs into an existing directory with `raw.jsonl`) when `strategy_config.json` mismatches the current strategy name or `config()`; warn and proceed without overwriting when an older directory has `raw.jsonl` but no `strategy_config.json`.
4. **D. Table of Runs (`scripts/README.md`):** Document the new CLI flags and the 12-row primary + sensitivity run table (4 primary + 8 sensitivity configurations, with no `n_bits` sensitivity runs per `[D-62](1)`).
5. **E. Real Embedder (`src/graph_insertion/embedding_minilm.py`, `pyproject.toml`):** Implement `MiniLMEmbedder` (`all-MiniLM-L6-v2`, CPU, `float32`, `dim=384`, lazy `sentence_transformers` import, `identity()` dict, fail-closed pin check when `MODEL_REVISION_PIN` is `None`), and add the `embed` optional dependency group in `pyproject.toml`.
6. **F. Decision Log, Status, Tests & Mutation Self-Check:** Add decision entry `[D-64]`, update `docs/tasks/status.md`, create `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, and `tests/test_run_experiment_cli.py`, and run the 13-mutant self-check (`I-M1`..`I-M13`) on a `/tmp` copy.

### What I Did
- Created [`src/graph_insertion/strategies/registry.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/registry.py) defining `STRATEGY_FACTORIES`, `PARAM_APPLICABILITY`, `PARAM_CLI_FLAGS`, `check_applicability()`, `build_strategy_slug()`, `derive_default_run_id()`, and `register_stub()`.
- Created [`src/graph_insertion/embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py) defining `MiniLMEmbedder`, `MODEL_NAME = "all-MiniLM-L6-v2"`, `MODEL_DIM = 384`, `SENTENCE_TRANSFORMERS_VERSION_PIN = None`, and `MODEL_REVISION_PIN = None` with a fail-closed `ValueError` check in `MiniLMEmbedder.__init__`.
- Updated [`src/graph_insertion/strategies/__init__.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/__init__.py) to export `NullStrategy` eagerly and lazily resolve `BruteForceStrategy`, `EmbeddingThresholdStrategy`, `AnnRetrievalStrategy`, `BoundedBucketStrategy`, and `STRATEGY_FACTORIES` via `__getattr__`.
- Updated [`scripts/run_experiment.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py) with the new CLI flags, applicability validation (`parser.error`, exit 2), clean `ValueError`/`ImportError` handling (`ERROR: ...`, exit 1, no traceback), `--live` + `--embedder fake` refusal for embedding strategies, deterministic default run-directory derivation, `<output_dir>/strategy_config.json` sidecar writing and `--resume` mismatch guard, and `MiniLMEmbedder` wiring.
- Updated [`pyproject.toml`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/pyproject.toml) to add the `embed` optional-dependency group (`dev` and `ann` left untouched).
- Updated [`scripts/README.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/README.md) with the CLI flag documentation and the 12-row primary + sensitivity run table.
- Created [`tests/test_strategy_registry.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py), [`tests/test_embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_embedding_minilm.py), and [`tests/test_run_experiment_cli.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py) (86 new tests total; no existing test files needed modification).
- Executed the `/tmp` mutation self-check across all 13 mutants (`I-M1`..`I-M13`): **13/13 KILLED**.
- Appended `[D-64]` to [`docs/decisions/decision-log.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/decisions/decision-log.md) and added the `INFRA-007` row under Phase 3 in [`docs/tasks/status.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/tasks/status.md).

---

## 3. Prompt Corrections

| Prompt Claim | Verification Status & Evidence |
| :--- | :--- |
| "Reserved decision ID: **D-63**... Already used: D-58, D-59, D-60 (DATA-007), D-61 (FIX-016), D-62 (STRAT-004-A). D-56 is absent and NOT free. If D-63 is present, stop and report; do not renumber." | **[Confirmed Wrong on D-63 and D-56]:** Both `[D-56]` (line 494, APC-A) and `[D-63]` (line 505, `FIX-017` committed at `78b0014`) were already present in `docs/decisions/decision-log.md`. I initially stopped and reported the `D-63` collision as instructed; Luke then instructed: *"simply use another id. proceed. continue."* Confirmed `D-64` had 0 grep matches and used `[D-64]`. |
| "Luke's last full count was about 583 passed, 3 skipped before STRAT-004-A2 added 3 tests." | **[Confirmed Slightly Stale]:** Before any INFRA-007 edits (at HEAD `78b0014`, post `STRAT-004-A2` and `FIX-017`), the baseline full test suite count was **`588 passed, 3 skipped`** (`146.06s`). |
| "`scripts/run_experiment.py` has `STRATEGY_REGISTRY` with only `'null'` and `'stub'`, factory signature `(seed, k)`, and `--strategy` uses `choices=list(STRATEGY_REGISTRY)`. `-k/--k` defaults to 1 and its help says 'for null strategy'. `strategies/__init__.py` exports only `NullStrategy`." | **[Confirmed Correct]:** Verified in `scripts/run_experiment.py` (lines 130–133, 496–507) and `src/graph_insertion/strategies/__init__.py` (lines 1–6). |
| "`main()` hard-wires `embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)` for every run, live or not." | **[Confirmed Correct]:** Verified at `scripts/run_experiment.py:660` prior to edit. |
| "Trial keys (`sweep_trial_key(strategy_name, n, trial_idx)`, `accuracy_trial_key(...)`) contain the strategy name only; `--resume` into a directory produced by another configuration would silently mix results." | **[Confirmed Correct]:** Verified in `src/graph_insertion/harness.py:327-336`: `sweep_trial_key` produces `f"sweep::{strategy_name}::{n}::{trial_idx}"` and `accuracy_trial_key` produces `f"accuracy::{strategy_name}::{corpus_name}::{node}::{rep}"`, without hyperparameter values. |
| "`compute_planned_calls_upper_bound` is already strategy-aware (FIX-016 made the dry-run planner agree with it)." | **[Confirmed Correct]:** Verified in `scripts/run_experiment.py:295-348` and `src/graph_insertion/harness.py:597-685`. |
| "`status.md` may have no INFRA-007 row; check and add one under Phase 3 if absent." | **[Confirmed Correct]:** `grep -n "INFRA-007" docs/tasks/status.md` returned exit code 1 (absent). Added under Phase 3. |
| "For `null` and `stub`, `k=None` keeps today's default (null: 1; stub: 5, as `StubNarrowingStrategy.top_k` defaults today; check, and keep current CLI behaviour for them byte-for-byte)." | **[Confirmed with Nuance]:** `StubNarrowingStrategy.__init__(self, top_k: int = 5)` indeed defaults `top_k` to `5`, whereas the old CLI parser had `-k` `default=1` which previously passed `k=1` into `StubNarrowingStrategy(top_k=k)` when `-k` was omitted on the CLI. With `-k` `default=None` (Section 2.B) and `stub` factory defaulting `k=None` to `5` (Section 2.A), `stub` now uses `StubNarrowingStrategy`'s own default `top_k=5` when `-k` is omitted, while `null` uses `k=1` byte-for-byte. |
| "`brute_force` takes no parameters... Pass `seed=config.seed` where the constructor has a `seed` (Strategies 2, 3, 4 and null), as the null factory does today." | **[Confirmed with Nuance]:** `BruteForceStrategy.__init__(self, seed: int = 42)` (`src/graph_insertion/strategies/brute_force.py:57`) also accepts `seed: int = 42` and its `config()` returns `{"seed": self.seed}` (unlike `StubNarrowingStrategy`, which has no `seed`). `_factory_brute_force` passes `seed=seed` to `BruteForceStrategy(seed=seed)`, so `config()["seed"]` records the actual seed and `_seed<seed>` is appended to the default directory slug when `seed != 42`. |

---

## 4. Pre-existing Facts Found

1. **What `run_id` default (`""`) previously produced `[Confirmed]`:**
   In `scripts/run_experiment.py`, `--run-id` defaults to `""` and `--output-dir` defaults to `None`. Previously, passing `run_id=""` and `output_dir=None` into `HarnessConfig` triggered `HarnessConfig.__post_init__()` (`src/graph_insertion/harness.py:299-304`), which generated a UTC timestamp string `f"{ts}_{self.mode}"` (`YYYYMMDD_HHMMSS_<mode>`) and set `self.output_dir = Path("results") / self.run_id` (`results/YYYYMMDD_HHMMSS_<mode>`). Under INFRA-007, when neither `--output-dir` nor `--run-id` is given, the CLI deterministically derives `results/<mode>_<strategy>` (or `results/<mode>_<strategy>_<slug>`), while explicit `--run-id` or `--output-dir` continues to take precedence unchanged.
2. **What `harness.py` writes into `manifest.json` and `raw.jsonl` `[Confirmed]`:**
   - `write_manifest()` in `src/graph_insertion/harness.py:389-429` writes `manifest.json` containing `"strategy_config": strategy.config()`, `"mode": config.mode`, and `"seeds": {"seed": config.seed}`. However, `manifest.json` does not record the top-level `"strategy"` name string (except for `StubNarrowingStrategy` whose `config()` includes `"name"`), does not record `"embedder"` identity or `"command_line_params"`, and is unconditionally overwritten on `--resume` without any mismatch check.
   - Each trial line in `raw.jsonl` (`harness.py:844-860`, `1072-1087`) records `"strategy": strategy_name` and `"metrics"` (where `"metrics"["extra"]` is `strategy.diagnostics()`), but **does not record `strategy.config()`**. While `diagnostics()` includes `"threshold"` for `embedding_threshold` and `"top_k"`/`"ef_search"` for `ann_retrieval`, `BoundedBucketStrategy.diagnostics()` does not include `s_min`, `s_max`, or `n_bits`, and none of the strategies' `diagnostics()` include `seed`. Consequently, `raw.jsonl` alone is insufficient to key analysis on `config()` fields; `<output_dir>/strategy_config.json` provides the guarded, canonical keyed metadata for analysis.
3. **Embedder pins in `.venv-ann` `[Confirmed]`:**
   - `.venv-ann/bin/pip list` confirms `faiss-cpu 1.15.1` is installed, while **`sentence-transformers` and `torch` are not installed** in `.venv-ann`.
   - Local cache inspection (`~/.cache/huggingface`, `~/.cache/torch`, `~/.cache/sentence_transformers`) confirms **no local Hugging Face cache** exists for `all-MiniLM-L6-v2`.
   - Per Section 2.E, `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py` are left as `None` with a fail-closed check in `MiniLMEmbedder.__init__` that raises `ValueError` if the revision is `None` or empty.
4. **Thread-sharing inspection (`faiss.omp_set_num_threads(1)` vs `MiniLMEmbedder`) `[Confirmed / Unverified without torch]`:**
   - **[Confirmed] Code execution order:** In `AnnRetrievalStrategy.setup()` (`src/graph_insertion/strategies/ann_retrieval.py:210-235`), `embedder.embed_many(texts)` runs at line 210 *before* `faiss.omp_set_num_threads(1)` is called at line 235. Thus, in trial 0's `setup()`, batch embedding runs prior to `faiss.omp_set_num_threads(1)`, whereas trial 0's `shortlist()` (`embed(new_name)`) and all subsequent trials in the same process run *after* `faiss.omp_set_num_threads(1)` has been invoked.
   - **[Confirmed] Shared library linkage:** Running `ldd` on `.venv-ann/lib/python3.14/site-packages/faiss/_swigfaiss.abi3.so` shows that the `faiss-cpu==1.15.1` manylinux wheel links against its own bundled, auditwheel-mangled GNU OpenMP library (`faiss_cpu.libs/libgomp-e985bcbb.so.1.0.0`).
   - **[Unverified offline]:** Because `sentence-transformers` and `torch` are not installed in `.venv-ann`, whether `faiss.omp_set_num_threads(1)` affects PyTorch / `MiniLMEmbedder` inference thread count or single-string `embed()` latency on CPU cannot be measured in this session. A standalone one-liner verification script is provided in Section 8 (Open Questions) for Luke to run once `sentence-transformers` is installed.
5. **`.gitignore` and `scripts/apc-bundle.sh` side effect `[Confirmed]`:**
   - `.gitignore` line 19 contains `results/datagen/` rather than `results/` (despite `[D-35](6)` stating `results/` is untracked). All CLI tests in `tests/test_run_experiment_cli.py` use `tmp_path` / `monkeypatch.chdir(tmp_path)` so zero files are written to the repo's `results/` directory.
   - Running `tests/test_apc_bundle.py` invokes `scripts/apc-bundle.sh`, which runs `tree ... > docs/context/repo-tree.txt` at line 204 and dirties `docs/context/repo-tree.txt` when new files exist in the working tree. `docs/context/repo-tree.txt` was restored to `HEAD` so only files authorized by Section 1 Rule 2 are touched.

---

## 5. Verification Output

### 5.1 Test Counts Before and After
- **Baseline before edits (at `78b0014`):**
  `588 passed, 3 skipped in 146.06s (0:02:26)`
- **New INFRA-007 test files alone (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`):**
  `86 passed in 4.49s`
- **Existing CLI/harness test files (`test_null_strategy.py`, `test_live_guard.py`, `test_dry_run_plan.py`, `test_harness.py`, `test_harness_embedding.py`):**
  `94 passed, 1 skipped in 11.80s`
- **Final full test suite (`| tail -3`):**
```text
tests/test_strategy_registry.py::TestStrategyRegistry::test_slug_and_default_run_id_derivation PASSED [100%]

================== 674 passed, 3 skipped in 107.61s (0:01:47) ==================
```

### 5.2 Dry-Run Transcripts (All 4 Primary + 8 Sensitivity Configurations, plus `--live --dry-run` with `minilm` and `fake`)

```text
=== Primary S1: brute_force (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: brute_force
Strategy Config: {'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500
Size:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000
Size:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000
Size:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000
Size: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000
Size: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 38500
======================================================================
Default/resolved output directory: results/sweep_brute_force
Dry run complete. Plan recorded in manifest.json.

=== Primary S2: embedding_threshold (theta=0.6) (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: embedding_threshold
Strategy Config: {'theta': 0.6, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500
Size:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000
Size:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000
Size:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000
Size: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000
Size: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 38500
======================================================================
Default/resolved output directory: results/sweep_embedding_threshold_theta0.6
Dry run complete. Plan recorded in manifest.json.

=== Primary S3: ann_retrieval (k=10, ef_search=128) (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: ann_retrieval
Strategy Config: {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  100 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  200 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  500 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 1000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 2000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 600
======================================================================
Default/resolved output directory: results/sweep_ann_retrieval_k10_ef128
Dry run complete. Plan recorded in manifest.json.

=== Primary S4: bounded_bucket (s_min=5, s_max=10, n_bits=12) (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: bounded_bucket
Strategy Config: {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  100 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  200 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  500 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 1000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 2000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 600
======================================================================
Default/resolved output directory: results/sweep_bounded_bucket_smin5_smax10_nb12
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S2: embedding_threshold --theta 0.4 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: embedding_threshold
Strategy Config: {'theta': 0.4, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500
Size:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000
Size:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000
Size:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000
Size: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000
Size: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 38500
======================================================================
Default/resolved output directory: results/sweep_embedding_threshold_theta0.4
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S2: embedding_threshold --theta 0.5 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: embedding_threshold
Strategy Config: {'theta': 0.5, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   50 | Max LLM Calls:    500
Size:  100 | Trials: 10 | Max Candidates:  100 | Max LLM Calls:   1000
Size:  200 | Trials: 10 | Max Candidates:  200 | Max LLM Calls:   2000
Size:  500 | Trials: 10 | Max Candidates:  500 | Max LLM Calls:   5000
Size: 1000 | Trials: 10 | Max Candidates: 1000 | Max LLM Calls:  10000
Size: 2000 | Trials: 10 | Max Candidates: 2000 | Max LLM Calls:  20000
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 38500
======================================================================
Default/resolved output directory: results/sweep_embedding_threshold_theta0.5
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S3: ann_retrieval -k 5 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: ann_retrieval
Strategy Config: {'k': 5, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  100 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  200 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  500 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size: 1000 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size: 2000 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 300
======================================================================
Default/resolved output directory: results/sweep_ann_retrieval_k5_ef128
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S3: ann_retrieval -k 20 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: ann_retrieval
Strategy Config: {'k': 20, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  100 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  200 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  500 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size: 1000 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size: 2000 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 1200
======================================================================
Default/resolved output directory: results/sweep_ann_retrieval_k20_ef128
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S3: ann_retrieval --ef-search 64 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: ann_retrieval
Strategy Config: {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 64, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  100 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  200 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  500 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 1000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 2000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 600
======================================================================
Default/resolved output directory: results/sweep_ann_retrieval_k10_ef64
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S3: ann_retrieval --ef-search 256 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: ann_retrieval
Strategy Config: {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 256, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  100 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  200 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size:  500 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 1000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
Size: 2000 | Trials: 10 | Max Candidates:   10 | Max LLM Calls:    100
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 600
======================================================================
Default/resolved output directory: results/sweep_ann_retrieval_k10_ef256
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S4: bounded_bucket --s-min 2 --s-max 5 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: bounded_bucket
Strategy Config: {'s_min': 2, 's_max': 5, 'n_bits': 12, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  100 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  200 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size:  500 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size: 1000 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
Size: 2000 | Trials: 10 | Max Candidates:    5 | Max LLM Calls:     50
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 300
======================================================================
Default/resolved output directory: results/sweep_bounded_bucket_smin2_smax5_nb12
Dry run complete. Plan recorded in manifest.json.

=== Sensitivity S4: bounded_bucket --s-min 10 --s-max 20 (exit=0) ===
======================================================================
DRY RUN EXECUTION PLAN: SWEEP MODE
Strategy: bounded_bucket
Strategy Config: {'s_min': 10, 's_max': 20, 'n_bits': 12, 'seed': 42}
======================================================================
Size:   50 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  100 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  200 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size:  500 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size: 1000 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
Size: 2000 | Trials: 10 | Max Candidates:   20 | Max LLM Calls:    200
----------------------------------------------------------------------
TOTAL PLANNED INSERTIONS: 60
ESTIMATED UPPER-BOUND LLM CALLS: 1200
======================================================================
Default/resolved output directory: results/sweep_bounded_bucket_smin10_smax20_nb12
Dry run complete. Plan recorded in manifest.json.

=== --live --dry-run --strategy ann_retrieval --embedder minilm (exit=0) ===
STDOUT:
=================================================================
LIVE EXPERIMENT PRE-FLIGHT ESTIMATE
Strategy:                      ann_retrieval
Strategy config:               {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
Embedder:                      minilm
Output directory:              results/sweep_ann_retrieval_k10_ef128
Model alias:                   deepseek-flash
Full-plan calls (upper bound): 600
Remaining calls (upper bound): 600
Estimated duration:            600.0s (10.0 min) (assuming 1.0s/call)
Estimated cost:                $0.0146 USD
Cost assumptions:              ~152 in, ~2.5 out tokens/call at $0.15/M in, $0.60/M out
-----------------------------------------------------------------
Current UTC:  2026-10-12 05:15:56 UTC
Philippine:   2026-10-12 13:15:56 PHT (UTC+8)
DeepSeek:     off-peak
=================================================================
Peak check note: Planned execution window falls within off-peak pricing hours. A real live run would be PERMITTED.
Dry run complete (live pre-flight estimation only; no API calls or client construction).

=== --live --dry-run --strategy ann_retrieval --embedder fake (exit=1) ===
STDERR:
ERROR: Live execution for embedding strategy 'ann_retrieval' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs.
```

### 5.3 Mutation Self-Check (`I-M1` .. `I-M13` on `/tmp` copy)

| Mutant ID | Description | File Mutated | Verdict | Failed Tests | Primary Killer Test |
| :--- | :--- | :--- | :--- | ---: | :--- |
| `I-M1` | Factory ignores `theta` | `src/graph_insertion/strategies/registry.py` | **KILLED** | 6 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| `I-M2` | `ef_search` passed as `k` | `src/graph_insertion/strategies/registry.py` | **KILLED** | 5 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| `I-M3` | `s_min`/`s_max` swapped | `src/graph_insertion/strategies/registry.py` | **KILLED** | 5 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| `I-M4` | Inapplicable-flag check removed | `scripts/run_experiment.py` | **KILLED** | 15 | `tests/test_run_experiment_cli.py::TestCLIParsingAndApplicability::test_inapplicable_flag_exits_2_naming_flag_and_strategy[null-flag_tokens0---theta]` |
| `I-M5` | Slug omits `ef` or `smin` | `src/graph_insertion/strategies/registry.py` | **KILLED** | 7 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_slug_and_default_run_id_derivation` |
| `I-M6` | Sidecar not written | `scripts/run_experiment.py` | **KILLED** | 22 | `tests/test_run_experiment_cli.py::TestRunDirectoryKeysAndSidecarGuard::test_section_2d_default_run_directories_and_bounds_via_cli[primary_s1_brute_force-...]` |
| `I-M7` | Resume mismatch check always passes | `scripts/run_experiment.py` | **KILLED** | 1 | `tests/test_run_experiment_cli.py::TestRunDirectoryKeysAndSidecarGuard::test_sidecar_written_and_resume_mismatch_refused` |
| `I-M8` | `--live` with `fake` embedder not refused | `scripts/run_experiment.py` | **KILLED** | 3 | `tests/test_run_experiment_cli.py::TestLiveAndEmbedderGates::test_live_with_embedding_strategy_and_fake_embedder_refused_before_key_or_client[embedding_threshold]` |
| `I-M9` | Default `k` for `null` changed from 1 | `src/graph_insertion/strategies/registry.py` | **KILLED** | 4 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_every_strategy_constructs_with_defaults` |
| `I-M10` | Lazy import made eager | `src/graph_insertion/embedding_minilm.py` | **KILLED** | collection error (`ModuleNotFoundError`) + subprocess test | `tests/test_embedding_minilm.py` (collection error when `sentence_transformers` absent) & `test_strategies_init_and_registry_import_without_faiss_and_sentence_transformers_subprocess` |
| `I-M11` | Seed not passed to a strategy | `src/graph_insertion/strategies/registry.py` | **KILLED** | 2 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| `I-M12` | Default directory ignores `--seed` | `src/graph_insertion/strategies/registry.py` | **KILLED** | 6 | `tests/test_strategy_registry.py::TestStrategyRegistry::test_slug_and_default_run_id_derivation` |
| `I-M13` | Embedder stub accepts `revision=None` | `src/graph_insertion/embedding_minilm.py` | **KILLED** | 1 | `tests/test_embedding_minilm.py::TestMiniLMEmbedderOffline::test_refuses_when_pin_is_none_or_empty` |

### 5.4 `git status --short` (Pre-Commit)

```text
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
 M pyproject.toml
 M scripts/README.md
 M scripts/run_experiment.py
 M src/graph_insertion/strategies/__init__.py
?? docs/reports/INFRA-007-gemini-strategy-wiring.md
?? src/graph_insertion/embedding_minilm.py
?? src/graph_insertion/strategies/registry.py
?? tests/test_embedding_minilm.py
?? tests/test_run_experiment_cli.py
?? tests/test_strategy_registry.py
```

---

## 6. Files Created or Edited

### Created
- [`src/graph_insertion/strategies/registry.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/registry.py)
- [`src/graph_insertion/embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py)
- [`tests/test_strategy_registry.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py)
- [`tests/test_embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_embedding_minilm.py)
- [`tests/test_run_experiment_cli.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py)
- [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md)

### Edited
- [`src/graph_insertion/strategies/__init__.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/__init__.py)
- [`scripts/run_experiment.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py)
- [`scripts/README.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/README.md)
- [`pyproject.toml`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/pyproject.toml)
- [`docs/decisions/decision-log.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/decisions/decision-log.md)
- [`docs/tasks/status.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/tasks/status.md)

---

## 7. Verbatim Diffs

### 7.1 Edited Files (`git diff`)
#### `src/graph_insertion/strategies/__init__.py`

```diff
diff --git i/src/graph_insertion/strategies/__init__.py w/src/graph_insertion/strategies/__init__.py
index 7898ef9..5cce12b 100644
--- i/src/graph_insertion/strategies/__init__.py
+++ w/src/graph_insertion/strategies/__init__.py
@@ -1,5 +1,36 @@
-"""graph_insertion.strategies — candidate-narrowing strategy implementations."""
+"""graph_insertion.strategies — candidate-narrowing strategy implementations.
+
+Exports only NullStrategy eagerly.  All other strategies and the registry
+are imported lazily so this package loads without faiss and without
+sentence-transformers.
+"""
 
 from graph_insertion.strategies.null import NullStrategy
 
-__all__ = ["NullStrategy"]
+__all__ = [
+    "NullStrategy",
+    "BruteForceStrategy",
+    "EmbeddingThresholdStrategy",
+    "AnnRetrievalStrategy",
+    "BoundedBucketStrategy",
+    "STRATEGY_FACTORIES",
+]
+
+
+def __getattr__(name: str):  # noqa: ANN201 — lazy module-level exports
+    if name == "BruteForceStrategy":
+        from graph_insertion.strategies.brute_force import BruteForceStrategy
+        return BruteForceStrategy
+    if name == "EmbeddingThresholdStrategy":
+        from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
+        return EmbeddingThresholdStrategy
+    if name == "AnnRetrievalStrategy":
+        from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+        return AnnRetrievalStrategy
+    if name == "BoundedBucketStrategy":
+        from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
+        return BoundedBucketStrategy
+    if name == "STRATEGY_FACTORIES":
+        from graph_insertion.strategies.registry import STRATEGY_FACTORIES
+        return STRATEGY_FACTORIES
+    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```
#### `scripts/run_experiment.py`

```diff
diff --git i/scripts/run_experiment.py w/scripts/run_experiment.py
index ad796dc..b637119 100644
--- i/scripts/run_experiment.py
+++ w/scripts/run_experiment.py
@@ -54,6 +54,15 @@ from graph_insertion.llm import resolve_model_alias
 from graph_insertion.loader import LoadedCorpus, discover_corpora, load_corpus
 from graph_insertion.schedule import format_peak_status, window_intersects_peak
 from graph_insertion.strategies.null import NullStrategy
+from graph_insertion.strategies.registry import (
+    PARAM_APPLICABILITY,
+    PARAM_CLI_FLAGS,
+    STRATEGY_FACTORIES,
+    build_strategy_slug,
+    check_applicability,
+    derive_default_run_id,
+    register_stub,
+)
 from graph_insertion.strategy import (
     DecisionOutcome,
     DecisionStep,
@@ -124,13 +133,11 @@ class StubDecisionStep:
 
 
 # ===========================================================================
-# Strategy Registry
+# Strategy Registry (INFRA-007)
 # ===========================================================================
 
-STRATEGY_REGISTRY: dict[str, Callable[[int, int], NarrowingStrategy]] = {
-    "null": lambda seed, k: NullStrategy(seed=seed, k=k),
-    "stub": lambda seed, k: StubNarrowingStrategy(top_k=k),
-}
+register_stub(StubNarrowingStrategy)
+STRATEGY_REGISTRY: dict[str, Callable[..., NarrowingStrategy]] = STRATEGY_FACTORIES
 
 
 # ===========================================================================
@@ -502,8 +509,44 @@ def build_parser() -> argparse.ArgumentParser:
         "-k",
         "--k",
         type=int,
-        default=1,
-        help="Candidate shortlist size k for null strategy (default: 1).",
+        default=None,
+        help="candidate shortlist size k: null, stub and ann_retrieval.",
+    )
+    parser.add_argument(
+        "--theta",
+        type=float,
+        default=None,
+        help="Cosine similarity threshold theta for embedding_threshold (default: 0.6).",
+    )
+    parser.add_argument(
+        "--ef-search",
+        type=int,
+        default=None,
+        help="HNSW efSearch query depth for ann_retrieval (default: 128).",
+    )
+    parser.add_argument(
+        "--s-min",
+        type=int,
+        default=None,
+        help="Minimum segment size s_min for bounded_bucket (default: 5).",
+    )
+    parser.add_argument(
+        "--s-max",
+        type=int,
+        default=None,
+        help="Maximum segment size s_max for bounded_bucket (default: 10).",
+    )
+    parser.add_argument(
+        "--n-bits",
+        type=int,
+        default=None,
+        help="Number of LSH hyperplanes n_bits for bounded_bucket (default: 12).",
+    )
+    parser.add_argument(
+        "--embedder",
+        choices=["fake", "minilm"],
+        default="fake",
+        help="Embedding backend: 'fake' (offline FakeEmbedder) or 'minilm' (pinned sentence-transformers all-MiniLM-L6-v2 on CPU).",
     )
     parser.add_argument(
         "--corpus",
@@ -515,7 +558,7 @@ def build_parser() -> argparse.ArgumentParser:
         "--output-dir",
         type=str,
         default=None,
-        help="Directory to save experiment results (defaults to results/<run_id>).",
+        help="Directory to save experiment results (defaults to results/<mode>_<strategy>_<slug> or results/<run_id>).",
     )
     parser.add_argument(
         "--run-id",
@@ -629,14 +672,89 @@ def build_parser() -> argparse.ArgumentParser:
     return parser
 
 
+def build_sidecar_payload(
+    strategy: NarrowingStrategy,
+    embedder_info: dict[str, Any],
+    mode: str,
+    command_line_params: dict[str, Any],
+) -> dict[str, Any]:
+    """Construct JSON-serialisable strategy_config.json sidecar dictionary."""
+    payload = {
+        "strategy": strategy.name,
+        "config": strategy.config(),
+        "embedder": embedder_info,
+        "mode": mode,
+        "command_line_params": command_line_params,
+    }
+    # Verify JSON-safety eagerly
+    json.dumps(payload)
+    return payload
+
+
 def main() -> int:
     parser = build_parser()
     args = parser.parse_args()
 
+    # Check strategy existence
+    strat_factory_fn = STRATEGY_REGISTRY.get(args.strategy)
+    if strat_factory_fn is None:
+        print(f"Unknown strategy {args.strategy!r}. Choices: {list(STRATEGY_REGISTRY.keys())}", file=sys.stderr)
+        return 1
+
+    # Applicability check: reject flags that do not apply to the chosen strategy (exit 2)
+    for param_name in ("k", "theta", "ef_search", "s_min", "s_max", "n_bits"):
+        val = getattr(args, param_name, None)
+        if val is not None and not check_applicability(args.strategy, param_name):
+            flag_str = PARAM_CLI_FLAGS.get(param_name, f"--{param_name}")
+            parser.error(
+                f"argument {flag_str} is not applicable to strategy {args.strategy!r}"
+            )
+
+    strategy_params = {
+        "theta": args.theta,
+        "ef_search": args.ef_search,
+        "s_min": args.s_min,
+        "s_max": args.s_max,
+        "n_bits": args.n_bits,
+    }
+    strategy_factory = lambda: strat_factory_fn(args.seed, args.k, **strategy_params)
+
+    # Instantiate strategy once via factory without calling setup()
+    # Catches out-of-range ValueError and missing-faiss ImportError cleanly (exit 1, no traceback)
+    try:
+        uninitialized_strategy = strategy_factory()
+    except (ValueError, ImportError) as err:
+        print(f"ERROR: {err}", file=sys.stderr)
+        return 1
+
+    # Gate: --live with an embedding strategy refuses --embedder fake (D-35(4), D-64)
+    # Checked BEFORE any client construction, key check, or live dry-run estimate.
+    uses_embeddings = bool(getattr(uninitialized_strategy, "uses_embeddings", False))
+    if args.live and uses_embeddings and args.embedder == "fake":
+        print(
+            f"ERROR: Live execution for embedding strategy {uninitialized_strategy.name!r} "
+            "requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); "
+            "'--embedder fake' is refused for live runs.",
+            file=sys.stderr,
+        )
+        return 1
+
+    # Derive deterministic default run_id and output_dir when neither --output-dir nor --run-id is given
+    default_run_id = derive_default_run_id(args.mode, args.strategy, uninitialized_strategy.config())
+    if args.output_dir:
+        resolved_run_id = args.run_id if args.run_id else default_run_id
+        resolved_output_dir = Path(args.output_dir)
+    elif args.run_id:
+        resolved_run_id = args.run_id
+        resolved_output_dir = Path("results") / args.run_id
+    else:
+        resolved_run_id = default_run_id
+        resolved_output_dir = Path("results") / default_run_id
+
     config = HarnessConfig(
         mode=args.mode,
-        run_id=args.run_id,
-        output_dir=Path(args.output_dir) if args.output_dir else None,
+        run_id=resolved_run_id,
+        output_dir=resolved_output_dir,
         seed=args.seed,
         repeats=args.repeats,
         metacademy_sample_size=args.metacademy_sample_size,
@@ -650,14 +768,40 @@ def main() -> int:
         fail_fast=args.fail_fast,
     )
 
-    # Strategy factory from registry
-    strat_factory_fn = STRATEGY_REGISTRY.get(args.strategy)
-    if strat_factory_fn is None:
-        print(f"Unknown strategy {args.strategy!r}. Choices: {list(STRATEGY_REGISTRY.keys())}", file=sys.stderr)
-        return 1
+    output_dir = Path(config.output_dir) if config.output_dir else Path("results") / config.run_id
+    raw_jsonl_path = output_dir / "raw.jsonl"
+    sidecar_path = output_dir / "strategy_config.json"
+    has_existing_raw = raw_jsonl_path.exists()
 
-    strategy_factory = lambda: strat_factory_fn(config.seed, args.k)
-    embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)
+    # Configuration guard on --resume or any run into an existing directory with raw.jsonl
+    if has_existing_raw or (config.resume and sidecar_path.exists()):
+        if sidecar_path.exists():
+            try:
+                stored_sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
+            except Exception as err:
+                print(
+                    f"ERROR: Failed to parse existing {sidecar_path}: {err}",
+                    file=sys.stderr,
+                )
+                return 1
+            stored_strategy = stored_sidecar.get("strategy")
+            stored_config = stored_sidecar.get("config")
+            current_strategy = uninitialized_strategy.name
+            current_config = uninitialized_strategy.config()
+            if stored_strategy != current_strategy or stored_config != current_config:
+                print(
+                    f"ERROR: Strategy configuration mismatch in {output_dir}: "
+                    f"stored strategy={stored_strategy!r} config={stored_config} vs "
+                    f"current strategy={current_strategy!r} config={current_config}",
+                    file=sys.stderr,
+                )
+                return 1
+        elif has_existing_raw:
+            print(
+                f"WARNING: Existing {raw_jsonl_path} found without {sidecar_path}; "
+                "proceeding without sidecar mismatch check and not writing sidecar to non-fresh directory.",
+                file=sys.stderr,
+            )
 
     # Corpora selection
     corpora = None
@@ -682,13 +826,6 @@ def main() -> int:
         )
         return 1
 
-    # Output dir & raw_jsonl_path for resume calculation
-    output_dir = Path(config.output_dir) if config.output_dir else Path("results") / config.run_id
-    raw_jsonl_path = output_dir / "raw.jsonl"
-
-    # Instantiate strategy once via factory without calling setup()
-    uninitialized_strategy = strategy_factory()
-
     # Compute planned calls upper bound (strategy-aware, resume-aware)
     planned_calls_bound = compute_planned_calls_upper_bound(
         config=config,
@@ -720,6 +857,10 @@ def main() -> int:
 
         print("=" * 65)
         print("LIVE EXPERIMENT PRE-FLIGHT ESTIMATE")
+        print(f"Strategy:                      {uninitialized_strategy.name}")
+        print(f"Strategy config:               {uninitialized_strategy.config()}")
+        print(f"Embedder:                      {args.embedder}")
+        print(f"Output directory:              {output_dir}")
         print(f"Model alias:                   {resolved_model}")
         print(f"Full-plan calls (upper bound): {full_plan_bound}")
         print(f"Remaining calls (upper bound): {est['planned_calls']}")
@@ -774,6 +915,51 @@ def main() -> int:
         except ImportError:
             decision_step = StubDecisionStep()
 
+    # Embedder factory wiring
+    embedder_factory: Callable[[], Embedder]
+    embedder_info: dict[str, Any]
+    if not uses_embeddings or args.embedder == "fake":
+        embedder_factory = lambda: FakeEmbedder(dim=32, seed=config.seed)
+        embedder_info = {
+            "type": "fake",
+            "uses_embeddings": uses_embeddings,
+            "dim": 32,
+            "seed": int(config.seed),
+        }
+    else:
+        from graph_insertion.embedding_minilm import (
+            MODEL_DIM,
+            MODEL_NAME,
+            MODEL_REVISION_PIN,
+            SENTENCE_TRANSFORMERS_VERSION_PIN,
+            MiniLMEmbedder,
+        )
+
+        if config.dry_run:
+            embedder_factory = lambda: FakeEmbedder(dim=MODEL_DIM, seed=config.seed)
+            embedder_info = {
+                "type": "minilm",
+                "uses_embeddings": True,
+                "model_name": MODEL_NAME,
+                "dim": int(MODEL_DIM),
+                "revision": MODEL_REVISION_PIN,
+                "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
+                "device": "cpu",
+                "dtype": "float32",
+            }
+        else:
+            try:
+                minilm_instance = MiniLMEmbedder()
+            except (ImportError, ValueError) as err:
+                print(f"ERROR: {err}", file=sys.stderr)
+                return 1
+            embedder_factory = lambda: minilm_instance
+            embedder_info = {
+                "type": "minilm",
+                "uses_embeddings": True,
+                **minilm_instance.identity(),
+            }
+
     # Synthetic name source for sweep (C4, FIX-008)
     name_source = None
     if config.mode == "sweep":
@@ -803,7 +989,31 @@ def main() -> int:
     if metered_client is not None and hasattr(metered_client, "set_on_call"):
         metered_client.set_on_call(progress_reporter.on_llm_call)
 
+    command_line_params = {
+        "strategy": args.strategy,
+        "k": args.k,
+        "theta": args.theta,
+        "ef_search": args.ef_search,
+        "s_min": args.s_min,
+        "s_max": args.s_max,
+        "n_bits": args.n_bits,
+        "seed": args.seed,
+        "embedder": args.embedder,
+    }
+
     try:
+        # Write sidecar strategy_config.json BEFORE the first trial on a fresh directory
+        if not has_existing_raw and (config.dry_run or config.confirm):
+            output_dir.mkdir(parents=True, exist_ok=True)
+            sidecar_payload = build_sidecar_payload(
+                strategy=uninitialized_strategy,
+                embedder_info=embedder_info,
+                mode=config.mode,
+                command_line_params=command_line_params,
+            )
+            with open(sidecar_path, "w", encoding="utf-8") as sf:
+                json.dump(sidecar_payload, sf, indent=2)
+
         result = run_experiment(
             config=config,
             strategy_factory=strategy_factory,
@@ -814,6 +1024,7 @@ def main() -> int:
             progress_callback=progress_reporter.update,
         )
         if config.dry_run:
+            print(f"Default/resolved output directory: {output_dir}")
             print("Dry run complete. Plan recorded in manifest.json.")
         else:
             print(f"Experiment finished: status={result.get('status')} output={result.get('output_dir')}")
```
#### `scripts/README.md`

```diff
diff --git i/scripts/README.md w/scripts/README.md
index badb766..40e8e84 100644
--- i/scripts/README.md
+++ w/scripts/README.md
@@ -153,3 +153,47 @@ bash tests/test_apc_bundle.sh
 ```bash
 ./scripts/apc-bundle.sh full --list
 ```
+
+---
+
+## Experiment Runner CLI (`scripts/run_experiment.py`)
+
+`scripts/run_experiment.py` executes accuracy (leave-one-out on DSA and Metacademy) and cost-scaling sweep (D-35 matrix: sizes `50 100 200 500 1000 2000` × 10 trials) benchmarks across all registered candidate-narrowing strategies.
+
+### Registered Strategies & CLI Flags
+
+- **`--strategy {null,stub,brute_force,embedding_threshold,ann_retrieval,bounded_bucket}`**: Strategy to evaluate (default: `null`). Derived from `graph_insertion.strategies.registry.STRATEGY_FACTORIES`.
+- **`-k, --k INT`**: Candidate shortlist size $k$ (`null`, `stub`, `ann_retrieval`). Defaults to `None` (resolves to `1` for `null`, `5` for `stub`, `10` for `ann_retrieval`).
+- **`--theta FLOAT`**: Cosine similarity threshold $\theta$ (`embedding_threshold` only; default `0.6`).
+- **`--ef-search INT`**: FAISS HNSW `efSearch` query depth (`ann_retrieval` only; default `128`).
+- **`--s-min INT`**: Minimum segment size $s_{\min}$ (`bounded_bucket` only; default `5`).
+- **`--s-max INT`**: Maximum segment size $s_{\max}$ (`bounded_bucket` only; default `10`).
+- **`--n-bits INT`**: Number of LSH hyperplanes $n_{\text{bits}}$ (`bounded_bucket` only; default `12`).
+- **`--embedder {fake,minilm}`**: Embedding backend (default: `fake`). Live runs (`--live`) for any strategy with `uses_embeddings=True` (`embedding_threshold`, `ann_retrieval`, `bounded_bucket`) require `--embedder minilm` (pinned local `sentence-transformers` `all-MiniLM-L6-v2` on CPU per [D-35](4)); `--embedder fake` is refused with exit code `1`. Non-embedding strategies (`null`, `stub`, `brute_force`) ignore `--embedder`.
+- **Applicability & Range Validation**: Passing a strategy-specific flag to a strategy that does not accept it (e.g., `--theta` with `ann_retrieval`, `--s-max` with `brute_force`, `-k` with `bounded_bucket`) is rejected as a CLI usage error (`parser.error`, exit code `2`). Out-of-range parameter values raise the strategy's `ValueError`, printed as `ERROR: ...` with exit code `1` (no traceback).
+
+### Deterministic Default Run Directories & Configuration Sidecar
+
+- When neither `--output-dir` nor `--run-id` is passed, the default output directory is `results/<mode>_<strategy>` (for `brute_force` at seed 42) or `results/<mode>_<strategy>_<slug>`, where `<slug>` encodes the strategy's keyed `config()` fields in fixed order (`_seed<seed>` is appended when `--seed != 42` for strategies with a seed). Explicit `--output-dir` or `--run-id` takes precedence unchanged.
+- Before the first trial on a fresh directory, the CLI writes `<output_dir>/strategy_config.json` containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`.
+- On `--resume` (or any run into an existing directory containing `raw.jsonl`), the CLI compares the stored `strategy` and `config` in `strategy_config.json` with the current configuration and refuses with exit code `1` on mismatch. Older directories containing `raw.jsonl` without `strategy_config.json` emit a warning to `stderr` and proceed without overwriting.
+
+### Primary & Sensitivity Run Table (D-35, D-46, D-47, D-55, D-58, D-59, D-62)
+
+Note: `n_bits = 12` for `bounded_bucket` is fixed a priori ($2^{12} = 4096 > 2000$) and has **no** sensitivity runs ([D-62](1)).
+
+| Role | Strategy | CLI Flags | Default Sweep Directory (`--mode sweep`) | Default Accuracy Directory (`--mode accuracy`) | D-35 Sweep Planned Calls Bound |
+| :--- | :--- | :--- | :--- | :--- | ---: |
+| **Primary (S1)** | `brute_force` | `--strategy brute_force` | `results/sweep_brute_force` | `results/accuracy_brute_force` | 38,500 |
+| **Primary (S2)** | `embedding_threshold` | `--strategy embedding_threshold` *(θ=0.6)* | `results/sweep_embedding_threshold_theta0.6` | `results/accuracy_embedding_threshold_theta0.6` | 38,500 |
+| **Primary (S3)** | `ann_retrieval` | `--strategy ann_retrieval` *(k=10, ef_search=128)* | `results/sweep_ann_retrieval_k10_ef128` | `results/accuracy_ann_retrieval_k10_ef128` | 600 |
+| **Primary (S4)** | `bounded_bucket` | `--strategy bounded_bucket` *(s_min=5, s_max=10, n_bits=12)* | `results/sweep_bounded_bucket_smin5_smax10_nb12` | `results/accuracy_bounded_bucket_smin5_smax10_nb12` | 600 |
+| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.4` | `results/sweep_embedding_threshold_theta0.4` | `results/accuracy_embedding_threshold_theta0.4` | 38,500 |
+| **Sensitivity (S2)** | `embedding_threshold` | `--strategy embedding_threshold --theta 0.5` | `results/sweep_embedding_threshold_theta0.5` | `results/accuracy_embedding_threshold_theta0.5` | 38,500 |
+| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 5` *(ef_search=128)* | `results/sweep_ann_retrieval_k5_ef128` | `results/accuracy_ann_retrieval_k5_ef128` | 300 |
+| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval -k 20` *(ef_search=128)* | `results/sweep_ann_retrieval_k20_ef128` | `results/accuracy_ann_retrieval_k20_ef128` | 1,200 |
+| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 64` *(k=10)* | `results/sweep_ann_retrieval_k10_ef64` | `results/accuracy_ann_retrieval_k10_ef64` | 600 |
+| **Sensitivity (S3)** | `ann_retrieval` | `--strategy ann_retrieval --ef-search 256` *(k=10)* | `results/sweep_ann_retrieval_k10_ef256` | `results/accuracy_ann_retrieval_k10_ef256` | 600 |
+| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 2 --s-max 5` *(n_bits=12)* | `results/sweep_bounded_bucket_smin2_smax5_nb12` | `results/accuracy_bounded_bucket_smin2_smax5_nb12` | 300 |
+| **Sensitivity (S4)** | `bounded_bucket` | `--strategy bounded_bucket --s-min 10 --s-max 20` *(n_bits=12)* | `results/sweep_bounded_bucket_smin10_smax20_nb12` | `results/accuracy_bounded_bucket_smin10_smax20_nb12` | 1,200 |
+
```
#### `pyproject.toml`

```diff
diff --git i/pyproject.toml w/pyproject.toml
index 5a4a17e..7a69d4d 100644
--- i/pyproject.toml
+++ w/pyproject.toml
@@ -15,6 +15,7 @@ dependencies = [
 [project.optional-dependencies]
 dev = ["pytest>=9.0", "pytest-cov"]
 ann = ["faiss-cpu==1.15.1"]
+embed = ["sentence-transformers"]  # TODO(INFRA-007): pin ==<version> once supplied by Luke (see SENTENCE_TRANSFORMERS_VERSION_PIN)
 
 [tool.setuptools.packages.find]
 where = ["src"]
```
#### `docs/decisions/decision-log.md`

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 6425458..c82abf1 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -507,3 +507,12 @@ Reasoning: records the model and thinking decision with its evidence limits, cor
 (2) Metadata-only guarantee: The change touches only `meta["shards"][i]["profiles"]` and `meta["profiles_used"]` in the merged branch of `build_pool_from_cache()`. For any cache set, `"names"`, `meta["n_raw"]`, `meta["n_valid"]`, `meta["drop_counts"]`, and `meta["sha256_names"]` are byte-identical to those produced when `profile_used` is absent or before this change. `scripts/name_pool_supervisor.py` was not modified.
 (3) Tests added and repaired: (a) `test_merged_pool_records_all_profiles_per_shard_and_preserves_names_sha256` in `tests/test_generate_name_pool.py` verifies `shards[0]["profiles"] == ["A", "B"]`, `shards[0]["profile"] == "A"`, `shards[1]["profiles"] == ["C"]`, `meta["profiles_used"] == ["A", "B", "C"]`, and byte-identical `names`, `n_raw`, `n_valid`, `drop_counts`, and `sha256_names` against the same caches with `profile_used` removed from every record; (b) `test_failover_on_rate_limit_to_spare_profile` in `tests/test_name_pool_supervisor.py` adds assertions that shard 1's merged metadata has `"profiles" == ["rate_limit_after_1_p1", "Spare_P3"]` and `meta["profiles_used"] == ["Profile_2", "Spare_P3", "rate_limit_after_1_p1"]`; (c) `test_live_adapter_flags_passthrough` in `tests/test_name_pool_supervisor.py` verifies live supervisor pass-through of `--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off` (and `--adapter-effort medium` so `build_shard_cli_tokens`'s default `adapter_effort="low"` cannot mask removing `adapter_effort` from `_launch_shard`) across recorded stdin payloads, cache `backend_meta["thinking_requested"]`, and `supervisor-log.jsonl` `shard_launch` commands, resolving [D-56](7)(a); (d) `test_loader_value_error_stops_everything` in `tests/test_name_pool_supervisor.py` now injects the conflicting cache record mid-run only after polling for `child_pid_file.exists()`, removes the vacuous `if child_pid_file.exists():` guard, and asserts the child is dead, resolving [D-56](7)(b). (Note: the APC-A prompt specified task ID `FIX-016` and decision ID `D-61`, which were already used by APC-B's dry-run planner fix; `D-62` was subsequently assigned to STRAT-004-A, so `FIX-017` and `D-63` are used per operator instruction.)
 Reasoning: makes merged pool provenance self-contained after mid-shard profile failover without affecting pool names or hashes, and closes the live flag pass-through and child-termination test gaps in `tests/test_name_pool_supervisor.py`. Affects: `scripts/generate_name_pool.py`, `tests/test_generate_name_pool.py`, `tests/test_name_pool_supervisor.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/FIX-017-gemini-profile-provenance-and-supervisor-tests.md`, DATA-006, DATA-007, FIX-017.
+
+**[D-64]** Strategy registry, CLI parameter wiring, deterministic run-directory slugs, configuration sidecar guard, and `MiniLMEmbedder` integration (INFRA-007):
+(1) Unified strategy registry (`src/graph_insertion/strategies/registry.py`): `STRATEGY_FACTORIES` serves as the single source of truth mapping canonical strategy names (`"null"`, `"stub"`, `"brute_force"`, `"embedding_threshold"`, `"ann_retrieval"`, `"bounded_bucket"`) to factories with signature `factory(seed=42, k=None, *, theta=None, ef_search=None, s_min=None, s_max=None, n_bits=None, **params) -> NarrowingStrategy`. Legacy two-argument calls `factory(seed, k)` remain supported, and `scripts/run_experiment.py:STRATEGY_REGISTRY` aliases `STRATEGY_FACTORIES`. `None` parameter values resolve to each strategy's primary defaults (`null`: $k=1$; `stub`: $\text{top\_k}=5$; `embedding_threshold`: $\theta=0.6$; `ann_retrieval`: $k=10, \text{ef\_search}=128$; `bounded_bucket`: $s_{\min}=5, s_{\max}=10, n_{\text{bits}}=12$). `src/graph_insertion/strategies/__init__.py` exports `NullStrategy` eagerly and lazily loads `BruteForceStrategy`, `EmbeddingThresholdStrategy`, `AnnRetrievalStrategy`, `BoundedBucketStrategy`, and `STRATEGY_FACTORIES` via `__getattr__`, ensuring `graph_insertion.strategies` and `registry.py` import cleanly without `faiss` or `sentence_transformers`.
+(2) CLI parameter flags, applicability enforcement, and error handling (`scripts/run_experiment.py`): adds `--theta` (`float`), `--ef-search`, `--s-min`, `--s-max`, `--n-bits` (`int`), all defaulting to `None`, updates `-k/--k` default to `None` with help `"candidate shortlist size k: null, stub and ann_retrieval."`, and derives `--strategy` choices from `STRATEGY_REGISTRY`. Parameter applicability (`PARAM_APPLICABILITY`) is checked prior to strategy instantiation; passing an inapplicable flag for the selected strategy invokes `parser.error(...)` (exit code 2, naming both the flag and the strategy). Out-of-range parameter values raise `ValueError` and missing `faiss` raises `ImportError` (including under `--strategy ann_retrieval --dry-run`), both caught in `main()` and printed to `stderr` as `ERROR: ...` with exit code 1 and no traceback.
+(3) Deterministic default run-directory slugs and `<output_dir>/strategy_config.json` guard: when neither `--output-dir` nor `--run-id` is passed (replacing the prior empty `run_id=""` fallback which generated timestamped `results/<YYYYMMDD_HHMMSS>_<mode>` directories via `HarnessConfig.__post_init__`), the CLI derives `results/<mode>_<strategy>` (for `brute_force` at seed 42) or `results/<mode>_<strategy>_<slug>`, where `<slug>` encodes only the keyed `config()` fields in fixed order (`embedding_threshold`: `theta<theta>`; `ann_retrieval`: `k<k>_ef<ef_search>`; `bounded_bucket`: `smin<s_min>_smax<s_max>_nb<n_bits>`; `null`/`stub`: `k<k>`; `brute_force`: empty), plus `_seed<seed>` whenever `seed != 42` for strategies with a seed. Explicit `--output-dir` or `--run-id` retains precedence unchanged. Before the first trial on a fresh directory (no existing `raw.jsonl`), the CLI writes `<output_dir>/strategy_config.json` containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`. On `--resume` or any run targeting an existing directory with `raw.jsonl`, the CLI compares the sidecar's `strategy` and `config` with the current strategy's `.name` and `.config()`, refusing with exit code 1 on any mismatch; older directories containing `raw.jsonl` without `strategy_config.json` emit a `WARNING:` to `stderr` and proceed without writing a sidecar. (While `harness.py` already writes `strategy_config` into `manifest.json`, `raw.jsonl` records omit `config()` and `manifest.json` is overwritten on `--resume` without a mismatch check; `strategy_config.json` is the guarded keyed source for analysis.)
+(4) Primary and sensitivity run matrix and planned-call bounds: locks the 12-run CLI table (4 primary + 8 sensitivity configurations across `brute_force`, `embedding_threshold` at $\theta \in \{0.6, 0.4, 0.5\}$, `ann_retrieval` at $(k, \text{ef\_search}) \in \{(10,128), (5,128), (20,128), (10,64), (10,256)\}$, and `bounded_bucket` at $(s_{\min}, s_{\max}, n_{\text{bits}}) \in \{(5,10,12), (2,5,12), (10,20,12)\}$ with no $n_{\text{bits}}$ sensitivity runs per [D-62](1)), documented in `scripts/README.md` and verified against `compute_planned_calls_upper_bound` over the D-35 sweep matrix (38,500; 38,500; 600/300/1,200; 600/300/1,200).
+(5) `MiniLMEmbedder`, `--embedder {fake,minilm}`, and fail-closed pins (`src/graph_insertion/embedding_minilm.py`, `pyproject.toml`): implements `MiniLMEmbedder` (`model_name = "all-MiniLM-L6-v2"`, `dim = 384`, CPU, `float32`, lazy `sentence_transformers` import raising `ImportError` with `pip install -e ".[embed]"`, `identity()` metadata dict) and adds optional-dependency group `embed` in `pyproject.toml`. In `scripts/run_experiment.py`, `--embedder` defaults to `fake`; `--live` combined with any strategy where `uses_embeddings=True` refuses `--embedder fake` with exit code 1 before any client construction, API-key check, or `--live --dry-run` pre-flight estimate. Because neither `sentence-transformers` nor the local Hugging Face cache for `all-MiniLM-L6-v2` is present in `.venv-ann`, `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` are set to `None` with a fail-closed check in `MiniLMEmbedder.__init__` that refuses `None`/empty revisions with `ValueError` until Luke supplies both pins. `faiss-cpu==1.15.1` links against its own bundled `faiss_cpu.libs/libgomp-e985bcbb.so.1.0.0`, and `AnnRetrievalStrategy.setup()` calls `faiss.omp_set_num_threads(1)` after batch `embed_many()` on trial 0 (leaving `shortlist()` and subsequent trials after the call); a standalone script is provided in the INFRA-007 report to verify PyTorch/`MiniLMEmbedder` thread timing once `sentence-transformers` is installed. (Note: the INFRA-007 prompt specified decision ID `D-63`, which was already assigned to FIX-017 in commit `78b0014`; `D-64` is used per operator instruction.)
+Reasoning: completes the CLI wiring for all four candidate-narrowing strategies and sensitivity configurations, prevents cross-configuration directory collisions and silent `--resume` mixing, enforces real CPU MiniLM embeddings for live runs with fail-closed version/revision pinning, and verifies full test and mutation coverage (86 new tests, 13/13 mutants `I-M1`..`I-M13` killed). Affects: `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/embedding_minilm.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/run_experiment.py`, `scripts/README.md`, `pyproject.toml`, `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/INFRA-007-gemini-strategy-wiring.md`, INFRA-007.
+
```
#### `docs/tasks/status.md`

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 8ca4137..cc6dc6a 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -53,7 +53,11 @@ Status: **open** (unblocked following Phase 1 completion; four parallel tracks r
 
 ## Phase 3 — Integration & Full Sweep
 
-Status: **not started** (blocked on Phase 2)
+Status: **in-progress** (unblocked following Phase 2 completion)
+
+| ID        | Task                                                                                                                                                                                                 | Status           | Notes / Report                                                                                                                                                                                                                                                                                                                                           |
+| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
+| INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **needs-review** | Completed by Gemini. 86 new tests (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`), 13/13 mutants `I-M1`..`I-M13` killed; full test suite 674 passing, 3 skipped. Awaiting `sentence-transformers` version and `all-MiniLM-L6-v2` revision pins from Luke. See report [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md). |
 
 ## Phase 4 — Analysis & Writeup
```
### 7.2 New Code and Test Files (`diff -u /dev/null <path>`)
#### `src/graph_insertion/strategies/registry.py`

```diff
--- /dev/null	2026-10-12 12:52:37.308065159 +0800
+++ src/graph_insertion/strategies/registry.py	2026-10-12 13:06:21.945692105 +0800
@@ -0,0 +1,250 @@
+"""strategies/registry.py — INFRA-007
+====================================
+Single source of truth for strategy names, factory functions, parameter
+applicability rules, and deterministic run-directory slug derivation.
+
+Every narrowing strategy available to the experiment CLI is registered here.
+Factory signature: ``factory(seed=42, k=None, **params) -> NarrowingStrategy``
+with ``params`` keys ``theta``, ``ef_search``, ``s_min``, ``s_max``, ``n_bits``
+all defaulting to ``None``. Legacy two-argument calls ``factory(seed, k)``
+continue to work unchanged.
+
+Lazy imports are used for ``ann_retrieval`` so this module loads without faiss.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Callable, Optional
+
+from graph_insertion.strategy import NarrowingStrategy
+
+_STUB_CLS: Optional[type] = None
+
+
+def register_stub(stub_cls: type) -> None:
+    """Register the StubNarrowingStrategy class from scripts/run_experiment.py."""
+    global _STUB_CLS
+    _STUB_CLS = stub_cls
+
+
+def _get_stub_cls() -> type:
+    global _STUB_CLS
+    if _STUB_CLS is None:
+        from scripts.run_experiment import StubNarrowingStrategy
+        _STUB_CLS = StubNarrowingStrategy
+    return _STUB_CLS
+
+
+def _factory_null(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    from graph_insertion.strategies.null import NullStrategy
+
+    if isinstance(seed, bool) or not isinstance(seed, int):
+        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
+    actual_k = 1 if k is None else k
+    if isinstance(actual_k, bool) or not isinstance(actual_k, int) or actual_k < 1:
+        raise ValueError(f"k must be >= 1, got {actual_k}")
+    return NullStrategy(seed=seed, k=actual_k)
+
+
+def _factory_stub(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    stub_cls = _get_stub_cls()
+    actual_k = 5 if k is None else k
+    if isinstance(actual_k, bool) or not isinstance(actual_k, int) or actual_k < 1:
+        raise ValueError(f"k must be >= 1, got {actual_k}")
+    return stub_cls(top_k=actual_k)
+
+
+def _factory_brute_force(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    from graph_insertion.strategies.brute_force import BruteForceStrategy
+
+    if isinstance(seed, bool) or not isinstance(seed, int):
+        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
+    return BruteForceStrategy(seed=seed)
+
+
+def _factory_embedding_threshold(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    from graph_insertion.strategies.embedding_threshold import EmbeddingThresholdStrategy
+
+    if isinstance(seed, bool) or not isinstance(seed, int):
+        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
+    kwargs: dict[str, Any] = {"seed": seed}
+    if theta is not None:
+        kwargs["theta"] = theta
+    return EmbeddingThresholdStrategy(**kwargs)
+
+
+def _factory_ann_retrieval(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    # Lazy import so registry and strategies package load without faiss installed
+    from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
+
+    kwargs: dict[str, Any] = {"seed": seed}
+    if k is not None:
+        kwargs["k"] = k
+    if ef_search is not None:
+        kwargs["ef_search"] = ef_search
+    return AnnRetrievalStrategy(**kwargs)
+
+
+def _factory_bounded_bucket(
+    seed: int = 42,
+    k: Optional[int] = None,
+    *,
+    theta: Optional[float] = None,
+    ef_search: Optional[int] = None,
+    s_min: Optional[int] = None,
+    s_max: Optional[int] = None,
+    n_bits: Optional[int] = None,
+    **params: Any,
+) -> NarrowingStrategy:
+    from graph_insertion.strategies.bounded_bucket import BoundedBucketStrategy
+
+    kwargs: dict[str, Any] = {"seed": seed}
+    if s_min is not None:
+        kwargs["s_min"] = s_min
+    if s_max is not None:
+        kwargs["s_max"] = s_max
+    if n_bits is not None:
+        kwargs["n_bits"] = n_bits
+    return BoundedBucketStrategy(**kwargs)
+
+
+# ---------------------------------------------------------------------------
+# Single source of truth for strategy names and factories.
+# ---------------------------------------------------------------------------
+
+STRATEGY_FACTORIES: dict[str, Callable[..., NarrowingStrategy]] = {
+    "null": _factory_null,
+    "stub": _factory_stub,
+    "brute_force": _factory_brute_force,
+    "embedding_threshold": _factory_embedding_threshold,
+    "ann_retrieval": _factory_ann_retrieval,
+    "bounded_bucket": _factory_bounded_bucket,
+}
+
+
+# ---------------------------------------------------------------------------
+# Parameter applicability rules.
+# Maps each CLI parameter name to the set of strategies that accept it.
+# ---------------------------------------------------------------------------
+
+PARAM_APPLICABILITY: dict[str, frozenset[str]] = {
+    "k": frozenset({"null", "stub", "ann_retrieval"}),
+    "theta": frozenset({"embedding_threshold"}),
+    "ef_search": frozenset({"ann_retrieval"}),
+    "s_min": frozenset({"bounded_bucket"}),
+    "s_max": frozenset({"bounded_bucket"}),
+    "n_bits": frozenset({"bounded_bucket"}),
+}
+
+PARAM_CLI_FLAGS: dict[str, str] = {
+    "k": "-k/--k",
+    "theta": "--theta",
+    "ef_search": "--ef-search",
+    "s_min": "--s-min",
+    "s_max": "--s-max",
+    "n_bits": "--n-bits",
+}
+
+
+def check_applicability(strategy_name: str, param_name: str) -> bool:
+    """Return True if param_name is applicable to strategy_name."""
+    allowed = PARAM_APPLICABILITY.get(param_name)
+    if allowed is None:
+        return True
+    return strategy_name in allowed
+
+
+def build_strategy_slug(strategy_name: str, config_dict: dict[str, Any]) -> str:
+    """Build deterministic configuration slug for default run directory naming.
+
+    Encodes ONLY the keyed config() fields in fixed order and spelling:
+      - embedding_threshold: theta<theta> (e.g. theta0.6)
+      - ann_retrieval: k<k>_ef<ef_search> (e.g. k10_ef128)
+      - bounded_bucket: smin<s_min>_smax<s_max>_nb<n_bits> (e.g. smin5_smax10_nb12)
+      - null / stub: k<k> (e.g. k1, k5)
+      - brute_force: "" (empty unless seed != 42)
+    Appends _seed<seed> (or seed<seed> if base slug is empty) for every strategy
+    that has a seed in config() when seed != 42.
+    """
+    parts: list[str] = []
+    if strategy_name == "embedding_threshold":
+        parts.append(f"theta{config_dict['theta']}")
+    elif strategy_name == "ann_retrieval":
+        parts.append(f"k{config_dict['k']}")
+        parts.append(f"ef{config_dict['ef_search']}")
+    elif strategy_name == "bounded_bucket":
+        parts.append(f"smin{config_dict['s_min']}")
+        parts.append(f"smax{config_dict['s_max']}")
+        parts.append(f"nb{config_dict['n_bits']}")
+    elif strategy_name == "null":
+        parts.append(f"k{config_dict['k']}")
+    elif strategy_name == "stub":
+        k_val = config_dict.get("top_k", config_dict.get("k"))
+        parts.append(f"k{k_val}")
+    elif strategy_name == "brute_force":
+        pass
+    else:
+        raise ValueError(f"Unknown strategy for slug derivation: {strategy_name!r}")
+
+    if "seed" in config_dict and config_dict["seed"] != 42:
+        parts.append(f"seed{config_dict['seed']}")
+
+    return "_".join(parts)
+
+
+def derive_default_run_id(mode: str, strategy_name: str, config_dict: dict[str, Any]) -> str:
+    """Derive deterministic run ID `<mode>_<strategy>` or `<mode>_<strategy>_<slug>`."""
+    slug = build_strategy_slug(strategy_name, config_dict)
+    if slug:
+        return f"{mode}_{strategy_name}_{slug}"
+    return f"{mode}_{strategy_name}"
```
#### `src/graph_insertion/embedding_minilm.py`

```diff
--- /dev/null	2026-10-12 12:52:37.308065159 +0800
+++ src/graph_insertion/embedding_minilm.py	2026-10-12 13:06:44.323343720 +0800
@@ -0,0 +1,128 @@
+"""embedding_minilm.py — INFRA-007
+==================================
+MiniLMEmbedder: production embedding model for live experiment runs.
+
+Uses sentence-transformers ``all-MiniLM-L6-v2`` on CPU, float32, 384-dim.
+Imported lazily so this module loads without sentence-transformers installed.
+
+Decisions:
+  - [D-35](4): Fixed local sentence-transformers all-MiniLM-L6-v2 on CPU,
+    version pinned.
+  - [D-64]: Live runs of embedding strategies require ``--embedder minilm``;
+    ``--embedder fake`` is refused for live embedding strategies.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional, Sequence
+
+import numpy as np
+
+
+# ---------------------------------------------------------------------------
+# Pins — MUST be set to actual values before any live run.
+# If MODEL_REVISION_PIN is None the embedder refuses to initialise (fail-closed).
+# ---------------------------------------------------------------------------
+
+# Pin: sentence-transformers package version installed in .venv-ann.
+# Cannot be determined offline (sentence-transformers is not installed).
+# Luke must supply this value.
+SENTENCE_TRANSFORMERS_VERSION_PIN: Optional[str] = None
+
+# Pin: Hugging Face model revision (commit hash) for all-MiniLM-L6-v2.
+# Cannot be determined offline (model is not cached locally).
+# Luke must supply this value.
+MODEL_REVISION_PIN: Optional[str] = None
+
+MODEL_NAME: str = "all-MiniLM-L6-v2"
+MODEL_DIM: int = 384
+
+_UNSET: Any = object()
+
+
+class MiniLMEmbedder:
+    """Production embedder using sentence-transformers all-MiniLM-L6-v2.
+
+    Implements the ``Embedder`` protocol (embed, embed_many) exactly as
+    ``FakeEmbedder`` does: embed returns 1-D float32 of shape ``(384,)``,
+    embed_many returns 2-D float32 of shape ``(len(texts), 384)``.
+
+    Parameters
+    ----------
+    revision :
+        Model revision (commit hash).  Defaults to ``MODEL_REVISION_PIN``.
+        If ``None`` or empty at construction time, raises ``ValueError``
+        (fail-closed).
+
+    Attributes
+    ----------
+    model_name : str
+        Always ``"all-MiniLM-L6-v2"``.
+    dim : int
+        Always 384.
+    revision : str
+        Pinned model revision hash.
+    """
+
+    model_name: str = MODEL_NAME
+    dim: int = MODEL_DIM
+
+    def __init__(self, revision: Any = _UNSET) -> None:
+        actual_revision = MODEL_REVISION_PIN if revision is _UNSET else revision
+        if not isinstance(actual_revision, str) or not actual_revision.strip():
+            raise ValueError(
+                "MiniLMEmbedder requires a pinned model revision. "
+                "Set MODEL_REVISION_PIN in embedding_minilm.py or pass a non-empty "
+                "revision= string to the constructor. Cannot proceed without a pin (fail-closed)."
+            )
+        self.revision: str = actual_revision
+
+        # Lazy import of sentence_transformers
+        try:
+            from sentence_transformers import SentenceTransformer
+        except ImportError:
+            raise ImportError(
+                "sentence-transformers is not installed. "
+                "Install with: pip install -e \".[embed]\""
+            ) from None
+
+        self._model = SentenceTransformer(
+            self.model_name,
+            revision=self.revision,
+            device="cpu",
+        )
+
+    def embed(self, text: str) -> np.ndarray:
+        """Return 1-D float32 embedding for a single text string."""
+        vec = self._model.encode(text, convert_to_numpy=True)
+        arr = np.asarray(vec, dtype=np.float32).reshape(-1)
+        if arr.shape != (self.dim,):
+            raise ValueError(
+                f"Expected 1-D embedding of shape ({self.dim},), got {arr.shape}"
+            )
+        return arr
+
+    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
+        """Return 2-D float32 array of shape (len(texts), dim)."""
+        if not texts:
+            return np.empty((0, self.dim), dtype=np.float32)
+        mat = self._model.encode(list(texts), convert_to_numpy=True)
+        arr = np.asarray(mat, dtype=np.float32)
+        if arr.ndim == 1 and len(texts) == 1:
+            arr = arr.reshape(1, -1)
+        if arr.shape != (len(texts), self.dim):
+            raise ValueError(
+                f"Expected 2-D embedding matrix of shape ({len(texts)}, {self.dim}), got {arr.shape}"
+            )
+        return arr
+
+    def identity(self) -> dict[str, Any]:
+        """Return identifying metadata for sidecar recording."""
+        return {
+            "model_name": self.model_name,
+            "dim": int(self.dim),
+            "revision": self.revision,
+            "sentence_transformers_version_pin": SENTENCE_TRANSFORMERS_VERSION_PIN,
+            "device": "cpu",
+            "dtype": "float32",
+        }
```
#### `tests/test_strategy_registry.py`

```diff
--- /dev/null	2026-10-12 12:52:37.308065159 +0800
+++ tests/test_strategy_registry.py	2026-10-12 13:11:13.440472971 +0800
@@ -0,0 +1,195 @@
+"""tests/test_strategy_registry.py — INFRA-007
+==============================================
+Unit tests for ``graph_insertion.strategies.registry`` and lazy exports in
+``graph_insertion.strategies``.
+"""
+
+from __future__ import annotations
+
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from graph_insertion.strategies.registry import (
+    PARAM_APPLICABILITY,
+    STRATEGY_FACTORIES,
+    build_strategy_slug,
+    check_applicability,
+    derive_default_run_id,
+)
+from scripts.run_experiment import STRATEGY_REGISTRY, StubNarrowingStrategy
+
+
+class TestStrategyRegistry:
+    """Verify STRATEGY_FACTORIES registration, defaults, parameter forwarding, and lazy imports."""
+
+    def test_registry_keys_complete_and_aliased(self) -> None:
+        expected = {
+            "null",
+            "stub",
+            "brute_force",
+            "embedding_threshold",
+            "ann_retrieval",
+            "bounded_bucket",
+        }
+        assert set(STRATEGY_FACTORIES.keys()) == expected
+        assert STRATEGY_REGISTRY is STRATEGY_FACTORIES
+
+    def test_every_strategy_constructs_with_defaults(self) -> None:
+        s_null = STRATEGY_FACTORIES["null"](42, None)
+        assert s_null.name == "null"
+        assert s_null.config() == {"seed": 42, "k": 1}
+
+        s_stub = STRATEGY_FACTORIES["stub"](42, None)
+        assert isinstance(s_stub, StubNarrowingStrategy)
+        assert s_stub.config() == {"name": "stub_narrowing", "top_k": 5}
+
+        s_bf = STRATEGY_FACTORIES["brute_force"](42, None)
+        assert s_bf.name == "brute_force"
+        assert s_bf.config() == {"seed": 42}
+
+        s_et = STRATEGY_FACTORIES["embedding_threshold"](42, None)
+        assert s_et.name == "embedding_threshold"
+        assert s_et.config() == {"theta": 0.6, "seed": 42}
+
+        s_ann = STRATEGY_FACTORIES["ann_retrieval"](42, None)
+        assert s_ann.name == "ann_retrieval"
+        ann_cfg = s_ann.config()
+        assert ann_cfg["k"] == 10
+        assert ann_cfg["ef_search"] == 128
+        assert ann_cfg["M"] == 16
+        assert ann_cfg["ef_construction"] == 200
+        assert ann_cfg["seed"] == 42
+
+        s_bb = STRATEGY_FACTORIES["bounded_bucket"](42, None)
+        assert s_bb.name == "bounded_bucket"
+        assert s_bb.config() == {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
+
+    def test_legacy_two_arg_calls_work_for_null_and_stub(self) -> None:
+        s_null_default = STRATEGY_FACTORIES["null"](42, None)
+        assert s_null_default.config() == {"seed": 42, "k": 1}
+
+        s_null_custom = STRATEGY_FACTORIES["null"](99, 7)
+        assert s_null_custom.config() == {"seed": 99, "k": 7}
+
+        s_stub_default = STRATEGY_FACTORIES["stub"](42, None)
+        assert s_stub_default.config()["top_k"] == 5
+
+        s_stub_custom = STRATEGY_FACTORIES["stub"](42, 3)
+        assert s_stub_custom.config()["top_k"] == 3
+
+    def test_parameters_and_seed_reach_strategy_config(self) -> None:
+        # embedding_threshold: theta and seed
+        s_et = STRATEGY_FACTORIES["embedding_threshold"](101, None, theta=0.4)
+        assert s_et.config() == {"theta": 0.4, "seed": 101}
+
+        # ann_retrieval: k, ef_search, and seed (ensure k and ef_search are not swapped)
+        s_ann = STRATEGY_FACTORIES["ann_retrieval"](202, 5, ef_search=64)
+        ann_cfg = s_ann.config()
+        assert ann_cfg["k"] == 5
+        assert ann_cfg["ef_search"] == 64
+        assert ann_cfg["seed"] == 202
+
+        s_ann_2 = STRATEGY_FACTORIES["ann_retrieval"](203, 20, ef_search=256)
+        ann_cfg_2 = s_ann_2.config()
+        assert ann_cfg_2["k"] == 20
+        assert ann_cfg_2["ef_search"] == 256
+        assert ann_cfg_2["seed"] == 203
+
+        # bounded_bucket: s_min, s_max, n_bits, and seed (ensure s_min and s_max are not swapped)
+        s_bb = STRATEGY_FACTORIES["bounded_bucket"](
+            303, None, s_min=2, s_max=5, n_bits=10
+        )
+        assert s_bb.config() == {"s_min": 2, "s_max": 5, "n_bits": 10, "seed": 303}
+
+        # brute_force: seed
+        s_bf = STRATEGY_FACTORIES["brute_force"](404, None)
+        assert s_bf.config() == {"seed": 404}
+
+        # null: seed and k
+        s_null = STRATEGY_FACTORIES["null"](505, 4)
+        assert s_null.config() == {"seed": 505, "k": 4}
+
+    def test_applicability_matrix(self) -> None:
+        assert check_applicability("null", "k") is True
+        assert check_applicability("stub", "k") is True
+        assert check_applicability("ann_retrieval", "k") is True
+        assert check_applicability("brute_force", "k") is False
+        assert check_applicability("embedding_threshold", "k") is False
+        assert check_applicability("bounded_bucket", "k") is False
+
+        assert check_applicability("embedding_threshold", "theta") is True
+        for s in ("null", "stub", "brute_force", "ann_retrieval", "bounded_bucket"):
+            assert check_applicability(s, "theta") is False
+
+        assert check_applicability("ann_retrieval", "ef_search") is True
+        for s in ("null", "stub", "brute_force", "embedding_threshold", "bounded_bucket"):
+            assert check_applicability(s, "ef_search") is False
+
+        for p in ("s_min", "s_max", "n_bits"):
+            assert check_applicability("bounded_bucket", p) is True
+            for s in ("null", "stub", "brute_force", "embedding_threshold", "ann_retrieval"):
+                assert check_applicability(s, p) is False
+
+    def test_ann_retrieval_factory_without_faiss_raises_import_error(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        import graph_insertion.strategies.ann_retrieval as ann_mod
+
+        monkeypatch.setattr(ann_mod, "faiss", None)
+        with pytest.raises(ImportError, match="pip install"):
+            STRATEGY_FACTORIES["ann_retrieval"](42, 10)
+
+    def test_strategies_init_and_registry_import_without_faiss_and_sentence_transformers_subprocess(
+        self,
+    ) -> None:
+        repo_root = Path(__file__).resolve().parent.parent
+        src_dir = repo_root / "src"
+        code = (
+            "import sys\n"
+            "sys.modules['faiss'] = None\n"
+            "sys.modules['sentence_transformers'] = None\n"
+            "import graph_insertion.strategies as s\n"
+            "import graph_insertion.strategies.registry as r\n"
+            "import graph_insertion.embedding_minilm as em\n"
+            "assert 'faiss' not in sys.modules or sys.modules['faiss'] is None\n"
+            "assert 'sentence_transformers' not in sys.modules or sys.modules['sentence_transformers'] is None\n"
+            "assert hasattr(s, 'NullStrategy')\n"
+            "assert set(r.STRATEGY_FACTORIES.keys()) == {'null', 'stub', 'brute_force', 'embedding_threshold', 'ann_retrieval', 'bounded_bucket'}\n"
+            # Non-faiss strategies instantiate cleanly when faiss & sentence_transformers are blocked
+            "assert r.STRATEGY_FACTORIES['null'](42, None).config() == {'seed': 42, 'k': 1}\n"
+            "assert r.STRATEGY_FACTORIES['brute_force'](42, None).config() == {'seed': 42}\n"
+            "assert r.STRATEGY_FACTORIES['embedding_threshold'](42, None).config() == {'theta': 0.6, 'seed': 42}\n"
+            "assert r.STRATEGY_FACTORIES['bounded_bucket'](42, None).config() == {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}\n"
+        )
+        proc = subprocess.run(
+            [sys.executable, "-c", code],
+            cwd=str(repo_root),
+            env={"PYTHONPATH": f"{src_dir}:{repo_root}"},
+            capture_output=True,
+            text=True,
+            check=False,
+        )
+        assert proc.returncode == 0, f"stderr: {proc.stderr}"
+
+    def test_slug_and_default_run_id_derivation(self) -> None:
+        assert derive_default_run_id("sweep", "brute_force", {"seed": 42}) == "sweep_brute_force"
+        assert derive_default_run_id("sweep", "brute_force", {"seed": 7}) == "sweep_brute_force_seed7"
+        assert (
+            derive_default_run_id("sweep", "embedding_threshold", {"theta": 0.6, "seed": 42})
+            == "sweep_embedding_threshold_theta0.6"
+        )
+        assert (
+            derive_default_run_id("sweep", "ann_retrieval", {"k": 10, "ef_search": 128, "seed": 42})
+            == "sweep_ann_retrieval_k10_ef128"
+        )
+        assert (
+            derive_default_run_id(
+                "sweep", "bounded_bucket", {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
+            )
+            == "sweep_bounded_bucket_smin5_smax10_nb12"
+        )
+        assert derive_default_run_id("sweep", "null", {"k": 1, "seed": 42}) == "sweep_null_k1"
+        assert derive_default_run_id("sweep", "stub", {"top_k": 5}) == "sweep_stub_k5"
```
#### `tests/test_embedding_minilm.py`

```diff
--- /dev/null	2026-10-12 12:52:37.308065159 +0800
+++ tests/test_embedding_minilm.py	2026-10-12 13:11:43.229167455 +0800
@@ -0,0 +1,199 @@
+"""tests/test_embedding_minilm.py — INFRA-007
+==============================================
+Offline unit tests for ``graph_insertion.embedding_minilm.MiniLMEmbedder``.
+
+No network access, no model downloads, and no real ``sentence_transformers``
+import.  All tests inject a deterministic stub ``sentence_transformers``
+module via ``monkeypatch.setitem(sys.modules, "sentence_transformers", ...)``.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import json
+import subprocess
+import sys
+import types
+from pathlib import Path
+from typing import Any, Sequence
+
+import numpy as np
+import pytest
+
+import graph_insertion.embedding_minilm as minilm_mod
+from graph_insertion.embedding import Embedder, FakeEmbedder, MeteredEmbedder
+from graph_insertion.embedding_minilm import (
+    MODEL_DIM,
+    MODEL_NAME,
+    MiniLMEmbedder,
+)
+
+
+class _StubSentenceTransformer:
+    """Deterministic offline stub for ``sentence_transformers.SentenceTransformer``."""
+
+    instances: list["_StubSentenceTransformer"] = []
+
+    def __init__(
+        self,
+        model_name_or_path: str,
+        *,
+        revision: str | None = None,
+        device: str | None = None,
+        **kwargs: Any,
+    ) -> None:
+        if revision is None or not isinstance(revision, str) or not revision.strip():
+            raise AssertionError("StubSentenceTransformer must never be called with revision=None/empty")
+        self.model_name_or_path = model_name_or_path
+        self.revision = revision
+        self.device = device
+        self.kwargs = kwargs
+        self.encode_calls: list[tuple[Any, dict[str, Any]]] = []
+        _StubSentenceTransformer.instances.append(self)
+
+    @staticmethod
+    def _vec_for_text(text: str) -> np.ndarray:
+        digest = hashlib.sha256(text.encode("utf-8")).digest()
+        seed = int.from_bytes(digest[:8], "little")
+        rng = np.random.default_rng(seed)
+        return rng.standard_normal(MODEL_DIM).astype(np.float32)
+
+    def encode(self, sentences: str | Sequence[str], **kwargs: Any) -> np.ndarray:
+        self.encode_calls.append((sentences, dict(kwargs)))
+        if isinstance(sentences, str):
+            return self._vec_for_text(sentences)
+        return np.vstack([self._vec_for_text(s) for s in sentences]).astype(np.float32)
+
+
+@pytest.fixture
+def stub_st_module(monkeypatch: pytest.MonkeyPatch) -> type[_StubSentenceTransformer]:
+    """Inject stub ``sentence_transformers`` into ``sys.modules``."""
+    _StubSentenceTransformer.instances.clear()
+    mod = types.ModuleType("sentence_transformers")
+    mod.SentenceTransformer = _StubSentenceTransformer  # type: ignore[attr-defined]
+    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)
+    return _StubSentenceTransformer
+
+
+class TestMiniLMEmbedderOffline:
+    """Offline tests for MiniLMEmbedder using injected stub module."""
+
+    def test_module_imports_lazily_without_sentence_transformers(self) -> None:
+        repo_root = Path(__file__).resolve().parent.parent
+        src_dir = repo_root / "src"
+        code = (
+            "import sys\n"
+            "sys.modules['sentence_transformers'] = None\n"
+            "import graph_insertion.embedding_minilm as m\n"
+            "assert m.MODEL_NAME == 'all-MiniLM-L6-v2'\n"
+            "assert m.MODEL_DIM == 384\n"
+        )
+        proc = subprocess.run(
+            [sys.executable, "-c", code],
+            cwd=str(repo_root),
+            env={"PYTHONPATH": str(src_dir)},
+            capture_output=True,
+            text=True,
+            check=False,
+        )
+        assert proc.returncode == 0, f"stderr: {proc.stderr}"
+
+    def test_refuses_when_pin_is_none_or_empty(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: type[_StubSentenceTransformer],
+    ) -> None:
+        # 1. Default when MODEL_REVISION_PIN is None -> raises ValueError
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", None)
+        with pytest.raises(ValueError, match="pinned model revision"):
+            MiniLMEmbedder()
+        assert len(stub_st_module.instances) == 0
+
+        # 2. Explicit revision=None refused even when MODEL_REVISION_PIN is set (kills I-M13)
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "abc123456789")
+        with pytest.raises(ValueError, match="pinned model revision"):
+            MiniLMEmbedder(revision=None)
+        assert len(stub_st_module.instances) == 0
+
+        # 3. Empty/whitespace revision string refused
+        with pytest.raises(ValueError, match="pinned model revision"):
+            MiniLMEmbedder(revision="   ")
+        assert len(stub_st_module.instances) == 0
+
+    def test_missing_sentence_transformers_raises_import_error_with_install_hint(
+        self, monkeypatch: pytest.MonkeyPatch
+    ) -> None:
+        monkeypatch.setitem(sys.modules, "sentence_transformers", None)
+        with pytest.raises(ImportError, match=r'pip install -e "\.\[embed\]"'):
+            MiniLMEmbedder(revision="test-rev-001")
+
+    def test_embed_and_embed_many_shapes_dtypes_and_call_counts(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: type[_StubSentenceTransformer],
+    ) -> None:
+        monkeypatch.setattr(minilm_mod, "MODEL_REVISION_PIN", "rev-sha-42")
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.0.0-test")
+
+        emb = MiniLMEmbedder()
+        assert isinstance(emb, Embedder)
+        assert len(stub_st_module.instances) == 1
+        underlying = stub_st_module.instances[0]
+        assert underlying.model_name_or_path == MODEL_NAME
+        assert underlying.revision == "rev-sha-42"
+        assert underlying.device == "cpu"
+
+        # Single embed: 1D float32 of shape (384,), exactly 1 encode call with str
+        v1 = emb.embed("binary search tree")
+        assert isinstance(v1, np.ndarray)
+        assert v1.dtype == np.float32
+        assert v1.shape == (384,)
+        assert len(underlying.encode_calls) == 1
+        assert underlying.encode_calls[0][0] == "binary search tree"
+
+        # Determinism
+        v1_again = emb.embed("binary search tree")
+        np.testing.assert_array_equal(v1, v1_again)
+        assert len(underlying.encode_calls) == 2
+
+        # Batch embed_many: 2D float32 of shape (3, 384), 1 batch encode call
+        texts = ["graph traversal", "dynamic programming", "heap sort"]
+        mat = emb.embed_many(texts)
+        assert isinstance(mat, np.ndarray)
+        assert mat.dtype == np.float32
+        assert mat.shape == (3, 384)
+        assert len(underlying.encode_calls) == 3
+        assert underlying.encode_calls[2][0] == texts
+
+        # Empty embed_many: matches FakeEmbedder shape (0, 384) and dtype float32, 0 encode calls
+        empty_mat = emb.embed_many([])
+        fake_empty = FakeEmbedder(dim=384).embed_many([])
+        assert empty_mat.shape == fake_empty.shape == (0, 384)
+        assert empty_mat.dtype == fake_empty.dtype == np.float32
+        assert len(underlying.encode_calls) == 3
+
+        # MeteredEmbedder compatibility
+        metered = MeteredEmbedder(emb, record_texts=True)
+        mv = metered.embed("red black tree")
+        assert mv.shape == (384,)
+        assert metered.calls == 1
+        assert metered.texts_embedded == 1
+        assert metered.texts_log == ["red black tree"]
+
+    def test_identity_metadata_content_and_json_serializable(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        stub_st_module: type[_StubSentenceTransformer],
+    ) -> None:
+        monkeypatch.setattr(minilm_mod, "SENTENCE_TRANSFORMERS_VERSION_PIN", "3.1.1")
+        emb = MiniLMEmbedder(revision="commit-hash-xyz")
+        ident = emb.identity()
+        assert ident == {
+            "model_name": "all-MiniLM-L6-v2",
+            "dim": 384,
+            "revision": "commit-hash-xyz",
+            "sentence_transformers_version_pin": "3.1.1",
+            "device": "cpu",
+            "dtype": "float32",
+        }
+        assert json.loads(json.dumps(ident)) == ident
```
#### `tests/test_run_experiment_cli.py`

```diff
--- /dev/null	2026-10-12 12:52:37.308065159 +0800
+++ tests/test_run_experiment_cli.py	2026-10-12 13:12:49.424024246 +0800
@@ -0,0 +1,814 @@
+"""tests/test_run_experiment_cli.py — INFRA-007
+===============================================
+Comprehensive CLI tests for ``scripts/run_experiment.py``:
+  - Test 2: CLI parsing, applicability checks (exit 2), out-of-range ValueError (exit 1, no traceback)
+  - Test 3: ``--strategy ann_retrieval --dry-run`` with faiss blocked (exit 1, install hint)
+  - Test 4: Run-directory slugs for every row of section 2.D, ``--seed`` slug suffix,
+            ``--run-id`` / ``--output-dir`` precedence, ``strategy_config.json`` sidecar,
+            ``--resume`` mismatch refusal, and older directory warning without sidecar
+  - Test 5: ``--live`` and ``--embedder`` gates
+  - Test 6: Planned-calls upper bounds from parsed CLI arguments over the D-35 sweep matrix
+  - Test 7: End-to-end offline CLI smoke for all four strategies in sweep and accuracy modes
+"""
+
+from __future__ import annotations
+
+import json
+import re
+import sys
+from pathlib import Path
+from typing import Any
+
+import pytest
+
+from graph_insertion.harness import HarnessConfig
+from graph_insertion.strategies.registry import (
+    STRATEGY_FACTORIES,
+    derive_default_run_id,
+)
+from scripts.run_experiment import (
+    STRATEGY_REGISTRY,
+    build_parser,
+    compute_planned_calls_upper_bound,
+    main,
+)
+
+
+# ---------------------------------------------------------------------------
+# Section 2.D Table of Runs (4 primary + 8 sensitivity configurations)
+# ---------------------------------------------------------------------------
+
+SECTION_2D_RUNS: list[tuple[str, list[str], str, int, dict[str, Any]]] = [
+    # (label, cli_tokens, expected_sweep_dir, expected_d35_bound, expected_keyed_config)
+    (
+        "primary_s1_brute_force",
+        ["--strategy", "brute_force"],
+        "results/sweep_brute_force",
+        38500,
+        {"seed": 42},
+    ),
+    (
+        "primary_s2_embedding_threshold",
+        ["--strategy", "embedding_threshold"],
+        "results/sweep_embedding_threshold_theta0.6",
+        38500,
+        {"theta": 0.6, "seed": 42},
+    ),
+    (
+        "primary_s3_ann_retrieval",
+        ["--strategy", "ann_retrieval"],
+        "results/sweep_ann_retrieval_k10_ef128",
+        600,
+        {"k": 10, "ef_search": 128, "seed": 42},
+    ),
+    (
+        "primary_s4_bounded_bucket",
+        ["--strategy", "bounded_bucket"],
+        "results/sweep_bounded_bucket_smin5_smax10_nb12",
+        600,
+        {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42},
+    ),
+    (
+        "sens_s2_theta_0.4",
+        ["--strategy", "embedding_threshold", "--theta", "0.4"],
+        "results/sweep_embedding_threshold_theta0.4",
+        38500,
+        {"theta": 0.4, "seed": 42},
+    ),
+    (
+        "sens_s2_theta_0.5",
+        ["--strategy", "embedding_threshold", "--theta", "0.5"],
+        "results/sweep_embedding_threshold_theta0.5",
+        38500,
+        {"theta": 0.5, "seed": 42},
+    ),
+    (
+        "sens_s3_k_5",
+        ["--strategy", "ann_retrieval", "-k", "5"],
+        "results/sweep_ann_retrieval_k5_ef128",
+        300,
+        {"k": 5, "ef_search": 128, "seed": 42},
+    ),
+    (
+        "sens_s3_k_20",
+        ["--strategy", "ann_retrieval", "-k", "20"],
+        "results/sweep_ann_retrieval_k20_ef128",
+        1200,
+        {"k": 20, "ef_search": 128, "seed": 42},
+    ),
+    (
+        "sens_s3_ef_64",
+        ["--strategy", "ann_retrieval", "--ef-search", "64"],
+        "results/sweep_ann_retrieval_k10_ef64",
+        600,
+        {"k": 10, "ef_search": 64, "seed": 42},
+    ),
+    (
+        "sens_s3_ef_256",
+        ["--strategy", "ann_retrieval", "--ef-search", "256"],
+        "results/sweep_ann_retrieval_k10_ef256",
+        600,
+        {"k": 10, "ef_search": 256, "seed": 42},
+    ),
+    (
+        "sens_s4_smin2_smax5",
+        ["--strategy", "bounded_bucket", "--s-min", "2", "--s-max", "5"],
+        "results/sweep_bounded_bucket_smin2_smax5_nb12",
+        300,
+        {"s_min": 2, "s_max": 5, "n_bits": 12, "seed": 42},
+    ),
+    (
+        "sens_s4_smin10_smax20",
+        ["--strategy", "bounded_bucket", "--s-min", "10", "--s-max", "20"],
+        "results/sweep_bounded_bucket_smin10_smax20_nb12",
+        1200,
+        {"s_min": 10, "s_max": 20, "n_bits": 12, "seed": 42},
+    ),
+]
+
+
+class TestCLIParsingAndApplicability:
+    """Section 3 Test 2: CLI parsing, applicability checks, and out-of-range errors."""
+
+    def test_strategy_choices_match_registry_keys(self) -> None:
+        parser = build_parser()
+        strat_action = next(a for a in parser._actions if a.dest == "strategy")
+        assert list(strat_action.choices) == list(STRATEGY_FACTORIES.keys())
+        assert list(strat_action.choices) == list(STRATEGY_REGISTRY.keys())
+
+        k_action = next(a for a in parser._actions if a.dest == "k")
+        assert k_action.default is None
+        assert "null, stub and ann_retrieval" in (k_action.help or "")
+
+    @pytest.mark.parametrize(
+        "strategy,flag_tokens,expected_flag_name",
+        [
+            ("null", ["--theta", "0.5"], "--theta"),
+            ("null", ["--ef-search", "64"], "--ef-search"),
+            ("stub", ["--theta", "0.5"], "--theta"),
+            ("brute_force", ["-k", "5"], "-k/--k"),
+            ("brute_force", ["--s-max", "10"], "--s-max"),
+            ("brute_force", ["--theta", "0.5"], "--theta"),
+            ("embedding_threshold", ["-k", "5"], "-k/--k"),
+            ("embedding_threshold", ["--ef-search", "64"], "--ef-search"),
+            ("embedding_threshold", ["--s-min", "5"], "--s-min"),
+            ("ann_retrieval", ["--theta", "0.5"], "--theta"),
+            ("ann_retrieval", ["--s-min", "5"], "--s-min"),
+            ("ann_retrieval", ["--n-bits", "12"], "--n-bits"),
+            ("bounded_bucket", ["-k", "10"], "-k/--k"),
+            ("bounded_bucket", ["--theta", "0.5"], "--theta"),
+            ("bounded_bucket", ["--ef-search", "128"], "--ef-search"),
+        ],
+    )
+    def test_inapplicable_flag_exits_2_naming_flag_and_strategy(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        strategy: str,
+        flag_tokens: list[str],
+        expected_flag_name: str,
+    ) -> None:
+        monkeypatch.setattr(
+            "sys.argv",
+            ["run_experiment.py", "--dry-run", "--strategy", strategy, *flag_tokens],
+        )
+        with pytest.raises(SystemExit) as excinfo:
+            main()
+        assert excinfo.value.code == 2
+        err = capsys.readouterr().err
+        assert expected_flag_name in err
+        assert strategy in err
+
+    @pytest.mark.parametrize(
+        "cli_args",
+        [
+            ["--strategy", "embedding_threshold", "--theta", "1.5"],
+            ["--strategy", "embedding_threshold", "--theta", "-1.5"],
+            ["--strategy", "ann_retrieval", "-k", "0"],
+            ["--strategy", "ann_retrieval", "--ef-search", "0"],
+            ["--strategy", "bounded_bucket", "--s-min", "1"],
+            ["--strategy", "bounded_bucket", "--s-min", "6", "--s-max", "10"],
+            ["--strategy", "bounded_bucket", "--n-bits", "0"],
+            ["--strategy", "bounded_bucket", "--n-bits", "63"],
+            ["--strategy", "null", "-k", "0"],
+            ["--strategy", "stub", "-k", "-1"],
+        ],
+    )
+    def test_out_of_range_values_exit_1_without_traceback(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        cli_args: list[str],
+    ) -> None:
+        monkeypatch.setattr(
+            "sys.argv",
+            ["run_experiment.py", "--dry-run", *cli_args],
+        )
+        rc = main()
+        assert rc == 1
+        err = capsys.readouterr().err
+        assert err.startswith("ERROR:")
+        assert "Traceback" not in err
+
+
+class TestAnnRetrievalWithoutFaiss:
+    """Section 3 Test 3: --strategy ann_retrieval --dry-run without faiss fails cleanly."""
+
+    def test_ann_retrieval_dry_run_without_faiss_exits_1_with_install_hint(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+    ) -> None:
+        import graph_insertion.strategies.ann_retrieval as ann_mod
+
+        monkeypatch.setattr(ann_mod, "faiss", None)
+        monkeypatch.setattr(
+            "sys.argv",
+            ["run_experiment.py", "--mode", "sweep", "--strategy", "ann_retrieval", "--dry-run"],
+        )
+        rc = main()
+        assert rc == 1
+        err = capsys.readouterr().err
+        assert "ERROR:" in err
+        assert "faiss" in err.lower()
+        assert "pip install" in err
+        assert "Traceback" not in err
+
+
+class TestRunDirectoryKeysAndSidecarGuard:
+    """Section 3 Test 4: Slugs, precedence, sidecar content, and --resume mismatch refusal."""
+
+    @pytest.mark.parametrize(
+        "label,cli_tokens,expected_sweep_dir,expected_bound,expected_keyed_cfg",
+        SECTION_2D_RUNS,
+    )
+    def test_section_2d_default_run_directories_and_bounds_via_cli(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+        label: str,
+        cli_tokens: list[str],
+        expected_sweep_dir: str,
+        expected_bound: int,
+        expected_keyed_cfg: dict[str, Any],
+    ) -> None:
+        monkeypatch.chdir(tmp_path)
+        monkeypatch.setattr(
+            "sys.argv",
+            ["run_experiment.py", "--mode", "sweep", "--dry-run", *cli_tokens],
+        )
+        rc = main()
+        assert rc == 0, f"Failed for {label}: {capsys.readouterr().err}"
+        out = capsys.readouterr().out
+        assert f"Default/resolved output directory: {expected_sweep_dir}" in out
+        assert f"ESTIMATED UPPER-BOUND LLM CALLS: {expected_bound}" in out
+
+        slug_part = expected_sweep_dir.removeprefix("results/")
+        assert re.fullmatch(r"[a-z0-9._-]+", slug_part) is not None
+
+        # Verify sidecar and manifest written to expected default directory inside tmp_path
+        run_dir = tmp_path / expected_sweep_dir
+        sidecar_file = run_dir / "strategy_config.json"
+        assert sidecar_file.exists()
+        sidecar = json.loads(sidecar_file.read_text(encoding="utf-8"))
+        for k, v in expected_keyed_cfg.items():
+            assert sidecar["config"][k] == v
+
+        # Also check accuracy mode slug derivation
+        parser = build_parser()
+        args = parser.parse_args(["--mode", "accuracy", *cli_tokens])
+        strat = STRATEGY_FACTORIES[args.strategy](
+            args.seed,
+            args.k,
+            theta=args.theta,
+            ef_search=args.ef_search,
+            s_min=args.s_min,
+            s_max=args.s_max,
+            n_bits=args.n_bits,
+        )
+        acc_dir = f"results/{derive_default_run_id('accuracy', args.strategy, strat.config())}"
+        assert acc_dir == expected_sweep_dir.replace("results/sweep_", "results/accuracy_", 1)
+
+    @pytest.mark.parametrize(
+        "cli_tokens,expected_dir",
+        [
+            (
+                ["--strategy", "brute_force", "--seed", "99"],
+                "results/sweep_brute_force_seed99",
+            ),
+            (
+                ["--strategy", "embedding_threshold", "--seed", "99"],
+                "results/sweep_embedding_threshold_theta0.6_seed99",
+            ),
+            (
+                ["--strategy", "ann_retrieval", "--seed", "99"],
+                "results/sweep_ann_retrieval_k10_ef128_seed99",
+            ),
+            (
+                ["--strategy", "bounded_bucket", "--seed", "99"],
+                "results/sweep_bounded_bucket_smin5_smax10_nb12_seed99",
+            ),
+            (
+                ["--strategy", "null", "--seed", "99"],
+                "results/sweep_null_k1_seed99",
+            ),
+        ],
+    )
+    def test_non_default_seed_included_in_default_directory_and_strategy_config(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+        cli_tokens: list[str],
+        expected_dir: str,
+    ) -> None:
+        monkeypatch.chdir(tmp_path)
+        monkeypatch.setattr(
+            "sys.argv",
+            ["run_experiment.py", "--mode", "sweep", "--dry-run", *cli_tokens],
+        )
+        rc = main()
+        assert rc == 0
+        out = capsys.readouterr().out
+        assert f"Default/resolved output directory: {expected_dir}" in out
+        sidecar = json.loads((tmp_path / expected_dir / "strategy_config.json").read_text())
+        assert sidecar["config"]["seed"] == 99
+
+    def test_explicit_run_id_and_output_dir_precedence(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        monkeypatch.chdir(tmp_path)
+
+        # 1. Explicit --run-id wins over default slug
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--run-id",
+                "custom_run_123",
+                "--dry-run",
+            ],
+        )
+        assert main() == 0
+        out1 = capsys.readouterr().out
+        assert "Default/resolved output directory: results/custom_run_123" in out1
+        assert (tmp_path / "results" / "custom_run_123" / "manifest.json").exists()
+
+        # 2. Explicit --output-dir wins over both default slug and --run-id
+        explicit_dir = tmp_path / "my_explicit_dir"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--run-id",
+                "custom_run_123",
+                "--output-dir",
+                str(explicit_dir),
+                "--dry-run",
+            ],
+        )
+        assert main() == 0
+        out2 = capsys.readouterr().out
+        assert f"Default/resolved output directory: {explicit_dir}" in out2
+        assert (explicit_dir / "manifest.json").exists()
+
+    def test_sidecar_written_and_resume_mismatch_refused(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        run_dir = tmp_path / "run_ann"
+        # Run 1: real offline trial run with ann_retrieval k=10
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "ann_retrieval",
+                "-k",
+                "10",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(run_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        sidecar_path = run_dir / "strategy_config.json"
+        raw_path = run_dir / "raw.jsonl"
+        assert sidecar_path.exists()
+        assert raw_path.exists()
+
+        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
+        assert set(sidecar.keys()) == {
+            "strategy",
+            "config",
+            "embedder",
+            "mode",
+            "command_line_params",
+        }
+        assert sidecar["strategy"] == "ann_retrieval"
+        assert sidecar["config"]["k"] == 10
+        assert sidecar["config"]["ef_search"] == 128
+        assert sidecar["mode"] == "sweep"
+
+        # Mismatch 1: change k from 10 to 5 on --resume
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "ann_retrieval",
+                "-k",
+                "5",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(run_dir),
+            ],
+        )
+        assert main() == 1
+        err_k = capsys.readouterr().err
+        assert "mismatch" in err_k.lower()
+        assert "'k': 10" in err_k
+        assert "'k': 5" in err_k
+
+        # Mismatch 2: change strategy to embedding_threshold (--theta 0.5)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--theta",
+                "0.5",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(run_dir),
+            ],
+        )
+        assert main() == 1
+        err_strat = capsys.readouterr().err
+        assert "mismatch" in err_strat.lower()
+        assert "ann_retrieval" in err_strat
+        assert "embedding_threshold" in err_strat
+
+        # Mismatch 3: change theta on an embedding_threshold run
+        et_dir = tmp_path / "run_et"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--theta",
+                "0.6",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(et_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--theta",
+                "0.4",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(et_dir),
+            ],
+        )
+        assert main() == 1
+        err_theta = capsys.readouterr().err
+        assert "mismatch" in err_theta.lower()
+        assert "0.6" in err_theta
+        assert "0.4" in err_theta
+
+        # Matching --resume succeeds
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "embedding_threshold",
+                "--theta",
+                "0.6",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(et_dir),
+            ],
+        )
+        assert main() == 0
+
+    def test_older_directory_with_raw_jsonl_but_no_sidecar_warns_and_does_not_refuse(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+    ) -> None:
+        legacy_dir = tmp_path / "legacy_run"
+        legacy_dir.mkdir(parents=True)
+        raw_path = legacy_dir / "raw.jsonl"
+        raw_path.write_text(
+            json.dumps({"key": "sweep::null::6::0", "status": "success", "strategy": "null"})
+            + "\n",
+            encoding="utf-8",
+        )
+
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                "null",
+                "--sweep-sizes",
+                "6",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--resume",
+                "--output-dir",
+                str(legacy_dir),
+            ],
+        )
+        rc = main()
+        assert rc == 0
+        err = capsys.readouterr().err
+        assert "WARNING:" in err
+        assert not (legacy_dir / "strategy_config.json").exists()
+
+
+class TestLiveAndEmbedderGates:
+    """Section 3 Test 5: --live and --embedder gates."""
+
+    @pytest.mark.parametrize(
+        "strategy",
+        ["embedding_threshold", "ann_retrieval", "bounded_bucket"],
+    )
+    def test_live_with_embedding_strategy_and_fake_embedder_refused_before_key_or_client(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        strategy: str,
+    ) -> None:
+        # Remove DEEPSEEK_API_KEY and omit --names-file to prove refusal happens BEFORE both
+        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--live",
+                "--mode",
+                "sweep",
+                "--strategy",
+                strategy,
+                "--embedder",
+                "fake",
+            ],
+        )
+        rc = main()
+        assert rc == 1
+        err = capsys.readouterr().err
+        assert "ERROR:" in err
+        assert "--embedder minilm" in err
+        assert "DEEPSEEK_API_KEY" not in err
+
+    @pytest.mark.parametrize(
+        "strategy,embedder",
+        [
+            ("embedding_threshold", "minilm"),
+            ("ann_retrieval", "minilm"),
+            ("bounded_bucket", "minilm"),
+            ("brute_force", "fake"),
+            ("brute_force", "minilm"),
+            ("null", "fake"),
+            ("null", "minilm"),
+        ],
+    )
+    def test_live_dry_run_exits_0_for_all_strategies_without_api_key(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+        strategy: str,
+        embedder: str,
+    ) -> None:
+        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
+        names_file = tmp_path / "names.json"
+        names_file.write_text(
+            json.dumps([f"valid_concept_{i:04d}" for i in range(2005)]),
+            encoding="utf-8",
+        )
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--live",
+                "--dry-run",
+                "--mode",
+                "sweep",
+                "--strategy",
+                strategy,
+                "--embedder",
+                embedder,
+                "--names-file",
+                str(names_file),
+            ],
+        )
+        rc = main()
+        assert rc == 0
+        out = capsys.readouterr().out
+        assert "LIVE EXPERIMENT PRE-FLIGHT ESTIMATE" in out
+        assert f"Strategy:                      {strategy}" in out
+        assert "Dry run complete" in out
+
+
+class TestPlannedCallsBoundsFromCLI:
+    """Section 3 Test 6: Planned-calls bounds over the D-35 sweep matrix driven by parsed CLI args."""
+
+    @pytest.mark.parametrize(
+        "label,cli_tokens,expected_sweep_dir,expected_bound,expected_keyed_cfg",
+        SECTION_2D_RUNS,
+    )
+    def test_d35_sweep_matrix_planned_calls_upper_bound(
+        self,
+        tmp_path: Path,
+        label: str,
+        cli_tokens: list[str],
+        expected_sweep_dir: str,
+        expected_bound: int,
+        expected_keyed_cfg: dict[str, Any],
+    ) -> None:
+        parser = build_parser()
+        args = parser.parse_args(["--mode", "sweep", *cli_tokens])
+        strat = STRATEGY_FACTORIES[args.strategy](
+            args.seed,
+            args.k,
+            theta=args.theta,
+            ef_search=args.ef_search,
+            s_min=args.s_min,
+            s_max=args.s_max,
+            n_bits=args.n_bits,
+        )
+        cfg = HarnessConfig(
+            mode="sweep",
+            sweep_sizes=tuple(args.sweep_sizes),
+            sweep_trials_per_size=args.sweep_trials,
+            seed=args.seed,
+        )
+        bound = compute_planned_calls_upper_bound(
+            config=cfg,
+            corpora=None,
+            strategy=strat,
+            raw_jsonl_path=tmp_path / "nonexistent_raw.jsonl",
+        )
+        assert bound.full_plan_bound == expected_bound, f"Mismatch for {label}"
+        assert bound.remaining_bound == expected_bound, f"Mismatch for {label}"
+        assert bound.full_plan_trials == 60
+
+
+class TestEndToEndOfflineCLISmoke:
+    """Section 3 Test 7: End-to-end offline CLI smoke for all four strategies."""
+
+    @pytest.mark.parametrize(
+        "strategy",
+        ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"],
+    )
+    def test_sweep_and_accuracy_offline_smoke(
+        self,
+        monkeypatch: pytest.MonkeyPatch,
+        capsys: pytest.CaptureFixture[str],
+        tmp_path: Path,
+        strategy: str,
+    ) -> None:
+        # 1. Sweep mode at tiny sizes [6, 8] x 1 trial
+        sweep_dir = tmp_path / f"smoke_sweep_{strategy}"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "sweep",
+                "--strategy",
+                strategy,
+                "--sweep-sizes",
+                "6",
+                "8",
+                "--sweep-trials",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(sweep_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        for fname in ("raw.jsonl", "summary.csv", "manifest.json", "strategy_config.json"):
+            assert (sweep_dir / fname).exists(), f"Missing {fname} in {sweep_dir}"
+
+        sweep_records = [
+            json.loads(line)
+            for line in (sweep_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
+            if line.strip()
+        ]
+        assert len(sweep_records) == 2
+        assert all(r["strategy"] == strategy and r["status"] == "success" for r in sweep_records)
+        sweep_sidecar = json.loads((sweep_dir / "strategy_config.json").read_text(encoding="utf-8"))
+        assert sweep_sidecar["strategy"] == strategy
+
+        # 2. Accuracy mode on DSA (capped with --max-llm-calls 1 so smoke completes in <0.1s)
+        acc_dir = tmp_path / f"smoke_acc_{strategy}"
+        monkeypatch.setattr(
+            "sys.argv",
+            [
+                "run_experiment.py",
+                "--mode",
+                "accuracy",
+                "--corpus",
+                "DSA",
+                "--strategy",
+                strategy,
+                "--max-llm-calls",
+                "1",
+                "--confirm",
+                "--output-dir",
+                str(acc_dir),
+            ],
+        )
+        assert main() == 0
+        capsys.readouterr()
+
+        for fname in ("raw.jsonl", "summary.csv", "manifest.json", "strategy_config.json"):
+            assert (acc_dir / fname).exists(), f"Missing {fname} in {acc_dir}"
+
+        acc_records = [
+            json.loads(line)
+            for line in (acc_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines()
+            if line.strip()
+        ]
+        assert len(acc_records) >= 1
+        assert all(r["strategy"] == strategy and r["status"] == "success" for r in acc_records)
+        acc_sidecar = json.loads((acc_dir / "strategy_config.json").read_text(encoding="utf-8"))
+        assert acc_sidecar["strategy"] == strategy
```

---

## 8. Open Questions

| # | Question / Action Needed | For |
| :--- | :--- | :--- |
| 1 | **Pin values for `sentence-transformers` and `all-MiniLM-L6-v2`:** Neither `sentence-transformers` nor the local Hugging Face cache for `sentence-transformers/all-MiniLM-L6-v2` is present in `.venv-ann`. Please supply: (a) the exact `sentence-transformers==<version>` pin for `pyproject.toml` (`[project.optional-dependencies].embed`) and `SENTENCE_TRANSFORMERS_VERSION_PIN` in `src/graph_insertion/embedding_minilm.py`, and (b) the Hugging Face commit hash for `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py`. Until set, `MiniLMEmbedder` fails closed with `ValueError`. | Luke |
| 2 | **OpenMP thread-sharing check between `faiss.omp_set_num_threads(1)` and `MiniLMEmbedder`:** Once `sentence-transformers` and the model are installed in `.venv-ann`, please run the standalone timing snippet below to check whether `faiss.omp_set_num_threads(1)` alters `torch.get_num_threads()` or `MiniLMEmbedder.embed()` / `embed_many()` latency on CPU: | Luke |

```bash
.venv-ann/bin/python - <<'PY'
import time, faiss, torch
from graph_insertion.embedding_minilm import MiniLMEmbedder
emb = MiniLMEmbedder(revision='<MODEL_REVISION_PIN>')
texts = [f'computer science concept {i}' for i in range(200)]
emb.embed('warmup')
print('Before faiss.omp_set_num_threads(1): torch.get_num_threads() =', torch.get_num_threads())
t0 = time.perf_counter(); emb.embed_many(texts); t_batch_before = time.perf_counter() - t0
t0 = time.perf_counter()
for t in texts[:50]: emb.embed(t)
t_single_before = (time.perf_counter() - t0) / 50
faiss.omp_set_num_threads(1)
print('After  faiss.omp_set_num_threads(1): torch.get_num_threads() =', torch.get_num_threads())
t0 = time.perf_counter(); emb.embed_many(texts); t_batch_after = time.perf_counter() - t0
t0 = time.perf_counter()
for t in texts[:50]: emb.embed(t)
t_single_after = (time.perf_counter() - t0) / 50
print(f'Batch 200: before={t_batch_before*1000:.2f}ms, after={t_batch_after*1000:.2f}ms')
print(f'Single 1 : before={t_single_before*1000:.2f}ms, after={t_single_after*1000:.2f}ms')
PY
```
