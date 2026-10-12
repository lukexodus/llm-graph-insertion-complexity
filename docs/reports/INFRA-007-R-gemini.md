# INFRA-007-R: Independent Review of the Strategy Wiring (Registry, CLI, Run-Directory Keys, MiniLM Embedder)

- **Task ID:** `INFRA-007-R`
- **Date:** 2026-10-12
- **Reviewer Agent:** `gemini` (Antigravity)
- **Model Label:** `Gemini 3.8 Flash (High)` (`is Gemini: yes`)
- **Session / Conversation ID:** `ede0cb54-0124-4d2a-b94b-45d52a9541f9`
- **Target Commit Reviewed:** `fda97db` (`INFRA-007: wire four strategies, parameters, run-directory keys and pinned embedder into the experiment CLI (D-64)`) on branch `master` (`HEAD` at `e276c37`)
- **Target Report Reviewed:** [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md)
- **Target Decision Reviewed:** `[D-64]` in [`docs/decisions/decision-log.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/decisions/decision-log.md#L511-L517)

---

## 1. Agent Identity and Independence Statement

- **Model Label:** `Gemini 3.8 Flash (High)` `[Confirmed]`
- **Is Gemini:** `yes` (Note: the review prompt expressed a preference for a non-Gemini model; this review was invoked in an Antigravity Gemini 3.8 Flash (High) session and compensates via exhaustive programmatic verification and 26-mutant testing, killing 19 and exposing 7 surviving mutants.)
- **Session ID:** `ede0cb54-0124-4d2a-b94b-45d52a9541f9` `[Confirmed]`
- **Independence Verification:** `[Confirmed]` This session (`ede0cb54-0124-4d2a-b94b-45d52a9541f9`) is completely independent of:
  - The `INFRA-007` implementer session (`2b098fc9-f59d-448e-82df-2e60c076a05f`, which switched mid-session from Claude Opus 4.6 Thinking to Gemini 3.8 Flash High),
  - The `STRAT-004` / `-R` / `-A` / `-A2` conversation (`455d24de-0fbf-46a4-bbe1-9c839413cd7e`),
  - The `STRAT-003` family (`b8ab4203-d881-4c7d-8f76-db6a0b797a9c`),
  - The `STRAT-004-R2` session (`900404ed-8ba1-4026-9ef6-f04be8b69e63`).
- **Read-Only / Budget Compliance:** `[Confirmed]`
  - Zero repository source, test, decision-log, status, or configuration files were edited.
  - Only this report (`docs/reports/INFRA-007-R-gemini.md`) was created.
  - Pytest budget strictly respected:
    1. One baseline run of the three new test files (`86 passed in 6.56s`),
    2. One `-x` run per mutant against a `/tmp` copy (`26` mutants total: `19 killed`, `7 survived`),
    3. One full-suite run at the end (`674 passed, 3 skipped in 134.32s`).

---

## 2. Verdict

**Verdict: `ACCEPT WITH AMENDMENTS`** (0 blockers, 4 `should-fix` items to fold into the already-planned `INFRA-007-P` follow-up task before any live embedding run, and 3 `nit` items).

### Three Most Important Reasons for the Verdict

1. **Sidecar resume/directory guard ignores embedder identity and allows `fake` $\leftrightarrow$ `minilm` or revision-change mixing (`F-1`, `should-fix`):** [`check_or_prepare_sidecar()`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L787-L798) compares only `sidecar["strategy"]` and `sidecar["config"]`, ignoring `sidecar["embedder"]` and `sidecar["mode"]`. In addition, `--embedder` is not part of the default run directory slug (`results/sweep_<strategy>_<slug>`). As demonstrated in Check R-C.3, resuming an offline `fake` run with `--embedder minilm` (or resuming a `minilm` run after `MODEL_REVISION_PIN` changes) exits `0` without warning or error, mixing incompatible embeddings in `raw.jsonl` while leaving the initial `strategy_config.json` untouched on disk.
2. **Incomplete `SENTENCE_TRANSFORMERS_VERSION_PIN` enforcement and 0% CLI test coverage of the `--embedder minilm` instantiation path (`F-2`, `F-3`, `should-fix`):** [`MiniLMEmbedder.__init__()`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py#L67-L94) checks only `MODEL_REVISION_PIN`; it neither fails closed when `SENTENCE_TRANSFORMERS_VERSION_PIN is None` nor verifies at runtime that `sentence_transformers.__version__ == SENTENCE_TRANSFORMERS_VERSION_PIN` (it only records the constant in `identity()`). Furthermore, every CLI test in [`tests/test_run_experiment_cli.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L637-L684) that passes `--embedder minilm` also passes `--live --dry-run`, which returns at line 890 before reaching the `minilm` instantiation block at [`scripts/run_experiment.py:929-961`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L929-L961) — proved by mutant `R-M19` surviving when the entire CLI `minilm` branch is bypassed.
3. **Plain `--dry-run` creates files in `results/` and causes `manifest.json` to record `"git_dirty": true` on a clean checkout (`F-4`, `should-fix`):** Plain offline `--dry-run` writes `strategy_config.json` (at [`scripts/run_experiment.py:1007-1015`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L1007-L1015)) and `manifest.json` (in `harness.py`). Because `.gitignore` ignores `results/datagen/` rather than `results/`, creating `results/<run_id>/strategy_config.json` *before* `run_experiment()` calls `write_manifest()` causes `get_git_info()` (`git status --porcelain`) to see the untracked `results/<run_id>/` directory and record `"git_dirty": true` in `manifest.json` even when the working tree was clean prior to the command.

---

## 3. Findings Table

| ID | Severity | Location (`file:line`) | Evidence (`[Confirmed]`) | Suggested Change (do not apply in `INFRA-007-R`) |
| :--- | :--- | :--- | :--- | :--- |
| **F-1** | `should-fix` | [`scripts/run_experiment.py:787-798`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L787-L798), [`743-753`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L743-L753) | `check_or_prepare_sidecar()` checks `stored_strategy != current_strategy or stored_config != current_config` and ignores `sidecar["embedder"]` and `sidecar["mode"]`. Verified in Check R-C.3: (a) running trial 0 with `--embedder fake` and resuming trial 1 with `--embedder minilm` exits `0`, appending `minilm` trials into the `fake` `raw.jsonl` while `strategy_config.json` still says `"type": "fake"`; (b) resuming after changing `MODEL_REVISION_PIN` from `rev-AAA` to `rev-BBB` exits `0`. Also, default run directories (`results/sweep_<strategy>_<slug>`) do not distinguish `fake` from `minilm`. | In `check_or_prepare_sidecar()`, compare `sidecar.get("embedder")` against current `embedder_info` (at minimum whenever `uses_embeddings` is `True`, or unconditionally) and `sidecar.get("mode")` against `config.mode`, refusing on mismatch with `ERROR:` and exit code `1`. Consider also encoding `_fake` in default directory names for offline `fake` runs or refusing non-`--resume` reuse. |
| **F-2** | `should-fix` | [`scripts/run_experiment.py:929-961`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L929-L961), [`tests/test_run_experiment_cli.py:637-684`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L637-L684) | Every test in `test_run_experiment_cli.py` that passes `--embedder minilm` also passes `--live --dry-run`, which returns early at line 890 (`if args.dry_run: return 0`). Lines 929–961 (`MiniLMEmbedder()` construction, `ImportError`/`ValueError` handling, `embedder_info` population, and `embedder_factory`) have 0% test coverage (`R-M19` survived). Additionally, in offline mode without `--dry-run` or `--confirm`, `MiniLMEmbedder()` is constructed at line 952 *before* `run_experiment()` checks `config.confirm` at line 1017 (`harness.py:944`). | Add offline CLI tests in `test_run_experiment_cli.py` with `--embedder minilm` (both with `MODEL_REVISION_PIN=None` verifying exit `1` and with stubbed `sentence_transformers` + `--confirm` verifying `strategy_config.json["embedder"]`). Also check `not args.dry_run and not args.confirm` before constructing `MiniLMEmbedder()`. |
| **F-3** | `should-fix` | [`src/graph_insertion/embedding_minilm.py:67-94, 115-128`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py#L67-L94) | `MiniLMEmbedder.__init__()` only checks `actual_revision` (`MODEL_REVISION_PIN`). Verified in Check R-D.2: (a) when `SENTENCE_TRANSFORMERS_VERSION_PIN = None` and `revision="rev-test"`, `MiniLMEmbedder()` succeeds; (b) when `SENTENCE_TRANSFORMERS_VERSION_PIN = "3.0.0"` and `sentence_transformers.__version__ = "99.99.99-mismatch"`, `MiniLMEmbedder()` succeeds without error. Also, `SentenceTransformer(...)` is called without `local_files_only=True`, so an uncached revision can trigger a network download. | In `MiniLMEmbedder.__init__()`, fail closed with `ValueError` if `SENTENCE_TRANSFORMERS_VERSION_PIN` is `None`/empty or if `getattr(sentence_transformers, "__version__", None) != SENTENCE_TRANSFORMERS_VERSION_PIN`, and record actual `sentence_transformers_version` in `identity()`. Pass `local_files_only=True` (or support an explicit cache check) once the snapshot is cached. |
| **F-4** | `should-fix` | [`scripts/run_experiment.py:1006-1015`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/run_experiment.py#L1006-L1015), [`.gitignore:42-43`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/.gitignore#L42-L43), [`src/graph_insertion/harness.py:591-614, 938`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/harness.py#L591-L614) | Plain `--dry-run` creates `<output_dir>/strategy_config.json` (and `harness.py` writes `<output_dir>/manifest.json`), whereas `--live --dry-run` writes nothing to disk. Because `.gitignore` only ignores `results/datagen/` (not `results/`), creating `results/<run_id>/strategy_config.json` before `run_experiment()` calls `write_manifest()` causes `get_git_info()` to see `?? results/<run_id>/` and record `"git_dirty": true` in `manifest.json` on a clean worktree. Moreover, mutant `R-M26` survived because no test verifies that `strategy_config.json` is written *before* `run_experiment()` executes or when a run aborts after trial 1. | Either (a) skip writing `strategy_config.json` on `--dry-run` (`if not has_existing_raw and config.confirm:`) and add `results/` to `.gitignore`, or (b) compute `get_git_info()` before creating `output_dir`. Add a test asserting `strategy_config.json` exists inside the first trial callback (before `run_experiment` finishes). |
| **F-5** | `nit` | [`src/graph_insertion/strategies/registry.py:21-36`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/strategies/registry.py#L21-L36) | `_get_stub_cls()` runs `from scripts.run_experiment import StubNarrowingStrategy` when `_STUB_CLS is None`. Verified in Check R-B.4: in a fresh interpreter with `cwd=/tmp` and `PYTHONPATH=src` (matching an editable/wheel install where `scripts/` is not a package), `STRATEGY_FACTORIES["stub"](42, None)` raises `ModuleNotFoundError: No module named 'scripts'`. | Move `StubNarrowingStrategy` into `src/graph_insertion/strategies/registry.py` (or `src/graph_insertion/strategies/stub.py`) and import/re-export it in `scripts/run_experiment.py`, eliminating the `src/` $\to$ `scripts/` upward import and `register_stub()` indirection. |
| **F-6** | `nit` | [`docs/reports/INFRA-007-gemini-strategy-wiring.md:2562`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md#L2562) | 1. The implementer report omits the mandatory **"Found but not changed"** section. 2. In Section 8's standalone OpenMP thread-check snippet (line 2562), `emb = MiniLMEmbedder(revision='<MODEL_REVISION_PIN>')` passes the literal placeholder string `'<MODEL_REVISION_PIN>'` instead of `emb = MiniLMEmbedder()` (which uses `MODEL_REVISION_PIN` once set in `embedding_minilm.py`), causing Hugging Face Hub to look for a snapshot literally named `<MODEL_REVISION_PIN>`. | When running the Section 8 timing snippet after `INFRA-007-P` sets the pins, invoke `emb = MiniLMEmbedder()` with no arguments rather than `revision='<MODEL_REVISION_PIN>'`. |
| **F-7** | `nit` | [`tests/test_embedding_minilm.py:57-66, 130-182`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_embedding_minilm.py#L57-L66), [`tests/test_strategy_registry.py:173-195`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py#L173-L195) | Four defensive branches in `embedding_minilm.py`, `strategies/__init__.py`, and `run_experiment.py` are not exercised by the new tests, allowing mutants `R-M11`, `R-M16`, `R-M20`, `R-M24`, and `R-M25` to survive: (1) `embed_many` 1-row 1-D $\to$ 2-D reshape (`embedding_minilm.py:111-112`), (2) `embed_many` `float64` $\to$ `float32` coercion (`_StubSentenceTransformer` already returns `float32`), (3) wrong-dimension `ValueError` guards (`embedding_minilm.py:99-102, 113-116`), (4) `strategies.__getattr__("STRATEGY_FACTORIES")` (`strategies/__init__.py:34-36`), and (5) sidecar mismatch check when `raw.jsonl` exists and `--resume` is omitted (`run_experiment.py:787`). | Add unit assertions covering a 1-D/float64/wrong-dim stub return in `test_embedding_minilm.py`, `strategies_pkg.STRATEGY_FACTORIES is STRATEGY_FACTORIES` in `test_strategy_registry.py`, and non-`--resume` sidecar mismatch refusal in `test_run_experiment_cli.py`. |

---

## 4. Checks R-A .. R-G with Verbatim Output

### Check R-A: Integrity and Scope

- **`git worktree list`, `git log --oneline -8`, `git status --short`, and `git show --stat fda97db`:** `[Confirmed]`
  - Commit `fda97db` is the `INFRA-007` commit. Two subsequent commits exist on `master` (`8d55ca6` and `e276c37`, recording `DATA-004` pool acceptance `[D-65]` and runbook updates).
  - `git status --short` shows only ` M docs/context/repo-tree.txt` (pre-existing unstaged modification; left untouched per Rule 0.2).
  - `git show --stat fda97db` touches **only** the 12 allowed files (`4492 insertions(+), 27 deletions(-)`). All 21 forbidden files/groups (`harness.py`, `strategy.py`, `embedding.py`, `llm.py`, `graph_representation.py`, `decision.py`, `schedule.py`, `loader.py`, `scoring.py`, all 5 strategy modules, `scripts/generate_name_pool.py`, `scripts/name_pool_supervisor.py`, `tests/test_strategy_interface.py`, `tests/controllable_embedder.py`, and `tests/test_brute_force.py` / `test_embedding_threshold.py` / `test_ann_retrieval.py` / `test_bounded_bucket.py`) have **zero** diff lines in `fda97db`.

```text
=== git worktree list ===
/home/lukexodus/projects/llm-graph-insertion-complexity          e276c37 [master]
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017  78b0014 [task/FIX-017]
/home/lukexodus/projects/llm-graph-insertion-complexity-gen      21d8e12 (detached HEAD)

=== git log --oneline -8 ===
e276c37 (HEAD -> master, origin/master, origin/HEAD) docs: update name-pool generation runbook for sharded supervisor flow (D-65)
8d55ca6 docs: record DATA-004 pool acceptance (D-65), close DATA-004 and FIX-017
fda97db INFRA-007: wire four strategies, parameters, run-directory keys and pinned embedder into the experiment CLI (D-64)
4f6de3d DATA-004: add generated name pool np1w (2254 names, 3 shards, Sonnet 5 Low, adapter ba3a8a2)
78b0014 (task/FIX-017) FIX-017: per-shard multi-profile provenance in merged pool meta and supervisor test gaps
0131a2b (master_local_ref) docs: regenerate repo-tree.txt
bbb75d7 STRAT-004-R2: independent post-amendment review of Strategy 4 and FIX-016
360ebf2 STRAT-004-R: independent review of Strategy 4 bounded-bucket and STRAT-003-B

=== git status --short ===
 M docs/context/repo-tree.txt

=== git show --stat fda97db ===
commit fda97db364f0ec4774ebdf379060d2d705e1268c
Author: Luke <luke@localhost>
Date:   Mon Oct 12 13:20:32 2026 +0800

    INFRA-007: wire four strategies, parameters, run-directory keys and pinned embedder into the experiment CLI (D-64)

 docs/decisions/decision-log.md                 |    9 +
 docs/reports/INFRA-007-gemini-strategy-wiring.md | 2579 ++++++++++++++++++++++
 docs/tasks/status.md                           |    3 +-
 pyproject.toml                                 |    4 +
 scripts/README.md                              |   41 +
 scripts/run_experiment.py                      |  260 ++-
 src/graph_insertion/embedding_minilm.py        |  128 ++
 src/graph_insertion/strategies/__init__.py     |   33 +-
 src/graph_insertion/strategies/registry.py     |  250 +++
 tests/test_embedding_minilm.py                 |  199 ++
 tests/test_run_experiment_cli.py               |  814 +++++++
 tests/test_strategy_registry.py                |  195 ++
 12 files changed, 4492 insertions(+), 27 deletions(-)

=== Check forbidden files in fda97db ===
Forbidden files touched in fda97db: NONE (0 lines)
```

- **`sha256sum`, `wc -l`, and Patch Rebuild Comparison:** `[Confirmed]`
  - Rebuilding the 6 new files (`src/graph_insertion/strategies/registry.py`, `src/graph_insertion/embedding_minilm.py`, `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`, `docs/reports/INFRA-007-gemini-strategy-wiring.md`) from `patch/0001-INFRA-007-wire-four-strategies-parameters-run-direct.patch` in `/tmp` produced **identical SHA-256 hashes (6/6 exact matches)**.
  - Note on `decision-log.md` and `status.md`: their current `HEAD` (`e276c37`) includes commit `8d55ca6` (`DATA-004` / `FIX-017` closure and `[D-65]`), whereas at commit `fda97db` their hashes matched the implementer's report (`b872a76571072227920740a6ddba4bb003dc743db49cfda261586df6fb5d611a` and `25219d2b02527fd0ac67c3be5a4a4419790e26b032fb788dc9a16f710d0f22f5`).

```text
=== sha256sum and wc -l of created/edited files ===
e8b596ce52f9e2239f2d8b7cfbe6d96e8d08957a51a934eea5d53334014b3e7a  src/graph_insertion/strategies/registry.py
73cf5c85d55e0782a5fd2497fdc5c5467a1963e433f99105e133b4d1ef08723a  src/graph_insertion/embedding_minilm.py
130d5d62b8e41c9ec783df80a2fe8f050c86ce515ed99c79d885996ae628b291  src/graph_insertion/strategies/__init__.py
944969492d8d3c5e75713c127d3e5262c7d2d1ca3beada4df11c3639afa2fbce  scripts/run_experiment.py
c800a37d021c63210ad795d30812cb38bb979625fcf06c2b4a91d6b49d7bf9ab  scripts/README.md
bae9cfc11fa878873c993b02e1b1abc6a52f99eb3710bf4ff76c9fdb197271f7  pyproject.toml
27c646b28c96eaf105c25e5174f48a1602cdbcfda7d70db282fb43f3e63d4bec  tests/test_strategy_registry.py
36b2c4326cbcd14cde2ce4fd9a71c315c95d0a889c8afb76841c3248cfc36369  tests/test_embedding_minilm.py
66b5472a55cdda5ce7059e344f546e85d5b67db2e4929ae2876e37140727168a  tests/test_run_experiment_cli.py
66517502485d323747108062c9876c3254887c90cf531fa26341ebd7cfb8e4e2  docs/decisions/decision-log.md
ceb1d20a3b54d6d19f78a1b3cbcb8e52e684a56063ea1b057e9292a4eb650c89  docs/tasks/status.md
1ddcd3bb9825c4c2ab6212f14960bb589f2d9e7ecbe6aaab473f8612b3a8c903  docs/reports/INFRA-007-gemini-strategy-wiring.md
   250 src/graph_insertion/strategies/registry.py
   128 src/graph_insertion/embedding_minilm.py
    36 src/graph_insertion/strategies/__init__.py
  1038 scripts/run_experiment.py
   199 scripts/README.md
    26 pyproject.toml
   195 tests/test_strategy_registry.py
   199 tests/test_embedding_minilm.py
   814 tests/test_run_experiment_cli.py
   530 docs/decisions/decision-log.md
    99 docs/tasks/status.md
  2579 docs/reports/INFRA-007-gemini-strategy-wiring.md
  6093 total

=== Patch rebuild comparison ===
MATCH: docs/reports/INFRA-007-gemini-strategy-wiring.md -> 1ddcd3bb9825c4c2ab6212f14960bb589f2d9e7ecbe6aaab473f8612b3a8c903
MATCH: src/graph_insertion/embedding_minilm.py -> 73cf5c85d55e0782a5fd2497fdc5c5467a1963e433f99105e133b4d1ef08723a
MATCH: src/graph_insertion/strategies/registry.py -> e8b596ce52f9e2239f2d8b7cfbe6d96e8d08957a51a934eea5d53334014b3e7a
MATCH: tests/test_embedding_minilm.py -> 36b2c4326cbcd14cde2ce4fd9a71c315c95d0a889c8afb76841c3248cfc36369
MATCH: tests/test_run_experiment_cli.py -> 66b5472a55cdda5ce7059e344f546e85d5b67db2e4929ae2876e37140727168a
MATCH: tests/test_strategy_registry.py -> 27c646b28c96eaf105c25e5174f48a1602cdbcfda7d70db282fb43f3e63d4bec
```

- **Decision IDs check:** `[Confirmed]`
  - `[D-56]` (line 494) and `[D-63]` (line 505) pre-existed in `fda97db~1`.
  - `[D-64]` (line 511) was the **only** decision ID added by `fda97db` and appears as a decision heading (`### [D-64]`) **exactly once** in `docs/decisions/decision-log.md`.
  - `[D-65]` (line 519) was added later by commit `8d55ca6`. Zero duplicate `[D-..]` headings exist across all 65 decisions in `docs/decisions/decision-log.md`.

```text
=== Decision IDs check ===
Decision headings containing D-56, D-63, D-64, D-65:
494:### [D-56] Name-pool validation relaxations and resumable generation — 2026-04-12
505:### [D-63] Bounded-bucket hyperplane seed, diagnostics schema and tie-break — 2026-10-12
511:### [D-64] Strategy registry, CLI wiring, keyed run directories, and pinned MiniLM embedder — 2026-10-12
519:### [D-65] Acceptance of the generated concept name pool (`np1w`) for DATA-004 — 2026-04-12
--- git show fda97db -- docs/decisions/decision-log.md ---
@@ -508,3 +508,12 @@ Strategy 4 (`BoundedBucketStrategy`) draws its $b$-bit random hyperplane matrix
 - **Affects:** `src/graph_insertion/strategies/bounded_bucket.py`, `tests/test_bounded_bucket.py`.
 
+### [D-64] Strategy registry, CLI wiring, keyed run directories, and pinned MiniLM embedder — 2026-10-12
+- **Decision:** Centralise all strategy constructors (`null`, `stub`, `brute_force`, `embedding_threshold`, `ann_retrieval`, `bounded_bucket`), parameter applicability rules, and deterministic configuration slugs in `src/graph_insertion/strategies/registry.py` (`STRATEGY_FACTORIES`, aliased as `STRATEGY_REGISTRY` in `scripts/run_experiment.py`). Inapplicable CLI flags are rejected with exit code 2 (`parser.error`); out-of-range strategy parameters are caught and reported cleanly with exit code 1. Default run directories (`results/<mode>_<strategy>_<slug>`) encode only the keyed `config()` fields (`theta` for Strategy 2, `k` and `ef_search` for Strategy 3, `s_min`/`s_max`/`n_bits` for Strategy 4, `k` for `null`/`stub`, plus `_seed<seed>` when `--seed != 42`) and write a `strategy_config.json` sidecar before the first trial so resume/reuse against an existing directory refuses any strategy or `config()` mismatch. Live runs (`--live`) of embedding strategies (`uses_embeddings == True`) require `--embedder minilm` (`MiniLMEmbedder` in `src/graph_insertion/embedding_minilm.py`, which fails closed when `MODEL_REVISION_PIN` is `None`) and refuse `--embedder fake` before any API client or key check.
+- **Reasoning:** Prevents silent flag ignoring, accidental overwriting or cross-parameter mixing of sensitivity sweeps in `results/sweep_<strategy>`, and accidental execution of live paid LLM runs with synthetic `FakeEmbedder` vectors or unpinned embedding models.
+- **Affects:** `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/__init__.py`, `src/graph_insertion/embedding_minilm.py`, `scripts/run_experiment.py`, `scripts/README.md`, `pyproject.toml`, `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`.
--- Check D-56 and D-63 in fda97db~1 ---
494:### [D-56] Name-pool validation relaxations and resumable generation — 2026-04-12
505:### [D-63] Bounded-bucket hyperplane seed, diagnostics schema and tie-break — 2026-10-12
Duplicate decision IDs in decision-log.md: {} (total headings: 65)
```

---

### Check R-B: Registry and Parameters

1. **`STRATEGY_FACTORIES`, aliasing, legacy `factory(seed, k)` calls, and defaults:** `[Confirmed]`
   - `list(STRATEGY_FACTORIES.keys()) == ['null', 'stub', 'brute_force', 'embedding_threshold', 'ann_retrieval', 'bounded_bucket']`.
   - `STRATEGY_REGISTRY is STRATEGY_FACTORIES` in `scripts/run_experiment.py` is `True`.
   - Legacy 2-argument positional calls `factory(seed, k)` work (`null(99, 3)` $\to$ `{'seed': 99, 'k': 3}`, `stub(99, 3)` $\to$ `{'name': 'stub_narrowing', 'top_k': 3}`, `ann_retrieval(99, 15)` $\to$ `k=15, seed=99`).
   - Passing `None` (or omitting parameters) yields the primary defaults from `[D-35]`/`[D-64]`: `embedding_threshold` $\theta = 0.6$, `ann_retrieval` $k = 10, \text{ef\_search} = 128$, `bounded_bucket` $(s_{\min}, s_{\max}, b) = (5, 10, 12)$, `null` $k = 1$, `stub` $\text{top\_k} = 5$.
2. **Full $6 \times 6$ Applicability Matrix and Out-of-Range Validation:** `[Confirmed]`
   - Tested all 36 `(param, strategy)` combinations independently through `scripts/run_experiment.py:main()`. All 28 inapplicable combinations exited with code `2` naming both the flag and the strategy; all 8 applicable combinations exited with code `0`.
   - Specifically confirmed that `-k` / `--k` with `bounded_bucket`, `embedding_threshold`, and `brute_force` is refused with exit code `2`.
   - Out-of-range values (`--theta 1.5`, `--theta -1.5`, `--s-min 10 --s-max 5`, `--k 0`, `--ef-search 0`, `--n-bits 0`) exit with code `1`, `ERROR:` on `stderr`, and no Python traceback.
3. **`ann_retrieval` without `faiss` (`sys.modules["faiss"] = None` in a subprocess):** `[Confirmed]`
   - `graph_insertion.strategies` and `graph_insertion.strategies.registry` import cleanly when `faiss` is blocked.
   - `null`, `stub`, `brute_force`, `embedding_threshold`, and `bounded_bucket` instantiate and run unaffected.
   - `--strategy ann_retrieval --dry-run` exits with code `1` and prints `ERROR: FAISS is not installed. Install with \`pip install -e '.[ann]'\` or \`pip install faiss-cpu==1.15.1\`.`
4. **`registry._get_stub_cls` importing `scripts.run_experiment` from library code:** `[Confirmed]` (See Finding **F-5**)
   - When `repo_root` is on `sys.path`, importing `graph_insertion.strategies.registry` first and calling `STRATEGY_FACTORIES["stub"](42, None)` succeeds without a circular-import error because `scripts.run_experiment` calls `register_stub(StubNarrowingStrategy)` after `registry` is already initialized in `sys.modules`.
   - **However**, in a fresh interpreter with `cwd=/tmp` and `PYTHONPATH=src` (where `src/` is importable as a package but `scripts/` is not on `sys.path`), calling `STRATEGY_FACTORIES["stub"](42, None)` fails with `ModuleNotFoundError: No module named 'scripts'`.
5. **Seed rule (`--seed` propagation and effect on Strategy 4 and Strategy 3):** `[Confirmed]`
   - `--seed` (default `42`) is passed to `brute_force`, `embedding_threshold`, `ann_retrieval`, `bounded_bucket`, and `null`, recorded in `config()["seed"]`, and appended as `_seed<seed>` to the default run directory slug whenever `seed != 42` (`stub` does not store `seed` in `config()`).
   - Confirmed empirically: changing `--seed` from `42` to `99` changes Strategy 4's (`BoundedBucketStrategy`) random hyperplane matrix (`np.allclose` is `False`, max absolute entry difference `0.982211`) and changes Strategy 3's (`AnnRetrievalStrategy`) stored (unused) `config()["seed"]` from `42` to `99`.

```text
=== R-B.1: Registry keys, aliasing, defaults, legacy (seed, k) ===
STRATEGY_FACTORIES keys: ['null', 'stub', 'brute_force', 'embedding_threshold', 'ann_retrieval', 'bounded_bucket']
STRATEGY_REGISTRY is STRATEGY_FACTORIES: True
  default null                 -> class=NullStrategy                 name=null                 config={'seed': 42, 'k': 1}
  default stub                 -> class=StubNarrowingStrategy        name=stub_narrowing       config={'name': 'stub_narrowing', 'top_k': 5}
  default brute_force          -> class=BruteForceStrategy           name=brute_force          config={'seed': 42}
  default embedding_threshold  -> class=EmbeddingThresholdStrategy   name=embedding_threshold  config={'theta': 0.6, 'seed': 42}
  default ann_retrieval        -> class=AnnRetrievalStrategy         name=ann_retrieval        config={'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
  default bounded_bucket       -> class=BoundedBucketStrategy        name=bounded_bucket       config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
Legacy 2-arg calls:
  null(99, 3): {'seed': 99, 'k': 3}
  stub(99, 3): {'name': 'stub_narrowing', 'top_k': 3}
  ann_retrieval(99, 15): {'k': 15, 'ef_search': 128, 'seed': 99}

=== R-B.2: Full 6x6 Applicability Matrix via CLI ===
  k         : null=OK(0) | stub=OK(0) | brute_force=REFUSED(2) | embedding_threshold=REFUSED(2) | ann_retrieval=OK(0) | bounded_bucket=REFUSED(2)
  theta     : null=REFUSED(2) | stub=REFUSED(2) | brute_force=REFUSED(2) | embedding_threshold=OK(0) | ann_retrieval=REFUSED(2) | bounded_bucket=REFUSED(2)
  ef_search : null=REFUSED(2) | stub=REFUSED(2) | brute_force=REFUSED(2) | embedding_threshold=REFUSED(2) | ann_retrieval=OK(0) | bounded_bucket=REFUSED(2)
  s_min     : null=REFUSED(2) | stub=REFUSED(2) | brute_force=REFUSED(2) | embedding_threshold=REFUSED(2) | ann_retrieval=REFUSED(2) | bounded_bucket=OK(0)
  s_max     : null=REFUSED(2) | stub=REFUSED(2) | brute_force=REFUSED(2) | embedding_threshold=REFUSED(2) | ann_retrieval=REFUSED(2) | bounded_bucket=OK(0)
  n_bits    : null=REFUSED(2) | stub=REFUSED(2) | brute_force=REFUSED(2) | embedding_threshold=REFUSED(2) | ann_retrieval=REFUSED(2) | bounded_bucket=OK(0)

=== R-B.3: Subprocess with faiss=None ===
Imported strategies and registry with faiss=None successfully
  Instantiated null: {'seed': 42, 'k': 1}
  Instantiated stub: {'name': 'stub_narrowing', 'top_k': 5}
  Instantiated brute_force: {'seed': 42}
  Instantiated embedding_threshold: {'theta': 0.6, 'seed': 42}
  Instantiated bounded_bucket: {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
CLI --strategy ann_retrieval --dry-run rc=1, stderr="ERROR: FAISS is not installed. Install with `pip install -e '.[ann]'` or `pip install faiss-cpu==1.15.1`."

=== R-B.4: Fresh interpreter test for registry._get_stub_cls ===
Case A (repo_root on sys.path, registry first): <class 'scripts.run_experiment.StubNarrowingStrategy'> {'name': 'stub_narrowing', 'top_k': 5}
Case B (CLI imported first): <class 'scripts.run_experiment.StubNarrowingStrategy'> {'name': 'stub_narrowing', 'top_k': 5}
Case C (CWD=/tmp, PYTHONPATH=src only): rc = 1
  stderr last line: ModuleNotFoundError: No module named 'scripts'

=== R-B.5: Seed rule & effect on Strategy 4 hyperplanes and Strategy 3 stored seed ===
Strategy 4 hyperplanes equal for seed=42 vs seed=99? False (max abs diff: 0.982211)
Strategy 3 config seed for 42 vs 99: 42 vs 99
  brute_force         : seed=42 -> sweep_brute_force                             | seed=99 -> sweep_brute_force_seed99
  embedding_threshold : seed=42 -> sweep_embedding_threshold_theta0.6            | seed=99 -> sweep_embedding_threshold_theta0.6_seed99
  ann_retrieval       : seed=42 -> sweep_ann_retrieval_k10_ef128                 | seed=99 -> sweep_ann_retrieval_k10_ef128_seed99
  bounded_bucket      : seed=42 -> sweep_bounded_bucket_smin5_smax10_nb12        | seed=99 -> sweep_bounded_bucket_smin5_smax10_nb12_seed99
  null                : seed=42 -> sweep_null_k1                                 | seed=99 -> sweep_null_k1_seed99
  stub                : seed=42 -> sweep_stub_k5                                 | seed=99 -> sweep_stub_k5
```

---

### Check R-C: Run Directories, Sidecar, Resume Guard

1. **Default directories for all 12 README configurations (`sweep` and `accuracy`), float canonicalisation, and `--run-id` / `--output-dir` precedence:** `[Confirmed]`
   - All 12 configurations produce 12 distinct `sweep` directories and 12 distinct `accuracy` directories (`24/24` distinct total).
   - Float canonicalisation works because `argparse` parses `--theta` as `float(value)` and `EmbeddingThresholdStrategy` stores `float(theta)` in `config()["theta"]`: `--theta 0.6` and `--theta 0.60` both produce `sweep_embedding_threshold_theta0.6`; omitting flags vs passing primary defaults explicitly produces identical directories. (Minor edge case noted: `--theta -0.0` produces `float("-0.0")` which formats as `theta-0.0` while `0.0 == -0.0` in Python.)
   - Precedence: `--output-dir` overrides both default directory and `--run-id` for the filesystem path (while `--run-id`, if also given, sets `config.run_id`).
2. **Dry-run disk side effects (`--dry-run` vs `--live --dry-run` vs pre-INFRA-007 `--dry-run`):** `[Confirmed]` (See Finding **F-4**)
   - Pre-`INFRA-007` (`fda97db~1`): plain `--dry-run` already created `<output_dir>/manifest.json` via `harness.py:run_experiment()` (`write_manifest(config, plan)` at line 938).
   - Post-`INFRA-007` (`fda97db`): plain `--dry-run` now creates `<output_dir>/strategy_config.json` **before** `run_experiment()` and `<output_dir>/manifest.json` inside `run_experiment()`. Because `results/` is not in `.gitignore` (only `results/datagen/` is), creating `results/<run_id>/strategy_config.json` before `write_manifest()` runs `get_git_info()` causes `manifest.json` to record `"git_dirty": true` even when starting from a clean worktree!
   - By contrast, `--live --dry-run` returns at `scripts/run_experiment.py:890` before `check_or_prepare_sidecar()` or `run_experiment()`, so `--live --dry-run` creates **zero** files or directories on disk.
   - Neither `--dry-run` nor `--confirm` (offline or `--live`): exits `1` without creating any directory or file on disk.
3. **Resume guard and the embedder-identity gap:** `[Confirmed]` (See Finding **F-1**)
   - Changing `s_max` (`10` $\to$ `12`), `(s_min, s_max)` (`(5,10)` $\to$ `(2,5)`), `n_bits` (`12` $\to$ `8`), `seed` (`42` $\to$ `99`), `ef_search` (`128` $\to$ `64`), or `strategy` (`bounded_bucket` $\to$ `ann_retrieval`), or corrupting `strategy_config.json`, all exit `1` with a clear `ERROR:` message on `stderr`.
   - Legacy directories containing `raw.jsonl` without `strategy_config.json` print a `WARNING:` to `stderr` and proceed without overwriting or refusing.
   - **Demonstrated Gap (`F-1`):**
     1. Running trial 0 in `/tmp/rc_checks/gap_embedder` with `--strategy bounded_bucket --embedder fake --confirm`, then resuming in the same directory with `--strategy bounded_bucket --embedder minilm --confirm --resume` (with stubbed `MiniLMEmbedder`) **exited `0` with no warning or error**, producing a 2-record `raw.jsonl` where trial 0 used `FakeEmbedder` (`32-d`) and trial 1 used `MiniLMEmbedder` (`384-d`), while `strategy_config.json` still reported `"embedder": {"type": "fake", ...}`.
     2. Running trial 0 with `MiniLMEmbedder(revision="rev-AAA")` and resuming trial 1 with `MiniLMEmbedder(revision="rev-BBB")` **exited `0` with no warning or error**.
4. **Inspection of `raw.jsonl` and `manifest.json` for `bounded_bucket` and `ann_retrieval`:** `[Confirmed]`
   - `raw.jsonl` records `strategy` (`"bounded_bucket"` / `"ann_retrieval"`), `mode`, `size`, `trial`, `node`, and full strategy diagnostics under `metrics.extra` (`18` keys for `bounded_bucket` per `[D-63]`; `6` keys for `ann_retrieval`).
   - `manifest.json` records `strategy_config` (`strategy.config()`) at top level, while `strategy_config.json` records `strategy`, `config`, `embedder`, `mode`, and `command_line_params`.

```text
=== R-C.1: 12 README configurations (sweep and accuracy) ===
  primary_s1_brute_force           | results/sweep_brute_force                          | results/accuracy_brute_force
  primary_s2_embedding_threshold   | results/sweep_embedding_threshold_theta0.6         | results/accuracy_embedding_threshold_theta0.6
  primary_s3_ann_retrieval         | results/sweep_ann_retrieval_k10_ef128              | results/accuracy_ann_retrieval_k10_ef128
  primary_s4_bounded_bucket        | results/sweep_bounded_bucket_smin5_smax10_nb12     | results/accuracy_bounded_bucket_smin5_smax10_nb12
  sens_s2_theta_0.4                | results/sweep_embedding_threshold_theta0.4         | results/accuracy_embedding_threshold_theta0.4
  sens_s2_theta_0.5                | results/sweep_embedding_threshold_theta0.5         | results/accuracy_embedding_threshold_theta0.5
  sens_s3_k_5                      | results/sweep_ann_retrieval_k5_ef128               | results/accuracy_ann_retrieval_k5_ef128
  sens_s3_k_20                     | results/sweep_ann_retrieval_k20_ef128              | results/accuracy_ann_retrieval_k20_ef128
  sens_s3_ef_64                    | results/sweep_ann_retrieval_k10_ef64               | results/accuracy_ann_retrieval_k10_ef64
  sens_s3_ef_256                   | results/sweep_ann_retrieval_k10_ef256              | results/accuracy_ann_retrieval_k10_ef256
  sens_s4_smin2_smax5              | results/sweep_bounded_bucket_smin2_smax5_nb12      | results/accuracy_bounded_bucket_smin2_smax5_nb12
  sens_s4_smin10_smax20            | results/sweep_bounded_bucket_smin10_smax20_nb12    | results/accuracy_bounded_bucket_smin10_smax20_nb12
Distinct sweep dirs: 12/12; Distinct accuracy dirs: 12/12; Combined distinct: 24/24
  Compare ['--strategy', 'embedding_threshold', '--theta', '0.6'] vs ['--strategy', 'embedding_threshold', '--theta', '0.60']:
    config equal? True | run_id1='sweep_embedding_threshold_theta0.6' vs run_id2='sweep_embedding_threshold_theta0.6'
  Compare ['--strategy', 'embedding_threshold'] vs ['--strategy', 'embedding_threshold', '--theta', '0.6']:
    config equal? True | run_id1='sweep_embedding_threshold_theta0.6' vs run_id2='sweep_embedding_threshold_theta0.6'
  Compare ['--strategy', 'ann_retrieval'] vs ['--strategy', 'ann_retrieval', '-k', '10', '--ef-search', '128']:
    config equal? True | run_id1='sweep_ann_retrieval_k10_ef128' vs run_id2='sweep_ann_retrieval_k10_ef128'
  Compare ['--strategy', 'embedding_threshold', '--theta', '0.0'] vs ['--strategy', 'embedding_threshold', '--theta', '-0.0']:
    config equal? True | run_id1='sweep_embedding_threshold_theta0.0' vs run_id2='sweep_embedding_threshold_theta-0.0'

=== R-C.2: Dry-run disk writes & --confirm / --live combinations ===
Plain --dry-run: rc=0, files created=['manifest.json', 'strategy_config.json']
--live --dry-run: rc=0, dir exists=False
--live without --confirm: rc=1, dir exists=False, stderr="ERROR: Live execution requires explicit '--confirm' flag to proceed."
Offline neither --dry-run nor --confirm: rc=1, dir exists=False, stderr='Experiment execution failed: Live experiment runs require explicit confirmation via config.confirm=True (or CLI flag --confirm) to prevent accidental API consumption.'

=== R-C.3: Resume guard checks (mismatches, corrupt sidecar, embedder-identity gap) ===
  Guard test (change s_max to 12): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_test: stored strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42} vs current strategy='bounded_bucket' config={'s_min': 5, 's_max': 12, 'n_bits': 12, 'seed': 42}"
  Guard test (change s_min to 2, s_max to 5): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_test: stored strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42} vs current strategy='bounded_bucket' config={'s_min': 2, 's_max': 5, 'n_bits': 12, 'seed': 42}"
  Guard test (change n_bits to 8): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_test: stored strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42} vs current strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 8, 'seed': 42}"
  Guard test (change seed to 99): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_test: stored strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42} vs current strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 99}"
  Guard test (change strategy to ann_retrieval): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_test: stored strategy='bounded_bucket' config={'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42} vs current strategy='ann_retrieval' config={'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}"
  Guard test (change ef_search 128->64): rc=1, stderr="ERROR: Strategy configuration mismatch in /tmp/rc_checks/guard_ann: stored strategy='ann_retrieval' config={'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42} vs current strategy='ann_retrieval' config={'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 64, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}"
  Guard test (corrupt sidecar): rc=1, stderr='ERROR: Failed to parse existing /tmp/rc_checks/guard_corrupt/strategy_config.json: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)'
  GAP DEMO 1 (resume fake run with minilm): rc=0, stderr=''
    raw.jsonl now has 2 records (trial 0 from fake, trial 1 from minilm!), sidecar still says embedder.type='fake'
  GAP DEMO 2 (resume minilm rev-AAA run with rev-BBB): rc=0 (0 = NOT CAUGHT)

=== R-C.4: Inspect raw.jsonl and manifest.json for bounded_bucket and ann_retrieval ===
--- bounded_bucket ---
  raw.jsonl top-level keys: ['key', 'run_id', 'timestamp', 'status', 'strategy', 'mode', 'size', 'trial', 'node', 'retries', 'metrics', 'harness_wall_s', 'unaccounted_s', 'llm_snapshot_delta']
  raw.jsonl metrics.extra (diagnostics) keys: ['bucket_id', 'bucket_gray_min', 'bucket_gray_max', 'query_code', 'query_gray_rank', 'code_existed_in_bucket', 'inside_bucket_span', 'bucket_size_at_shortlist', 'bucket_size', 'shortlist_size', 'split_occurred', 'merge_occurred', 'num_segments', 'min_segment_size', 'max_segment_size', 'mean_segment_size', 'exact_topk_overlap', 'min_hamming_to_shortlist']
  manifest.json strategy_config: {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}
  manifest.json has strategy name? False
  manifest.json has embedder? False
  strategy_config.json: {'strategy': 'bounded_bucket', 'config': {'s_min': 5, 's_max': 10, 'n_bits': 12, 'seed': 42}, 'embedder': {'type': 'fake', 'uses_embeddings': True, 'dim': 32, 'seed': 42}, 'mode': 'sweep', 'command_line_params': {'strategy': 'bounded_bucket', 'k': None, 'theta': None, 'ef_search': None, 's_min': None, 's_max': None, 'n_bits': None, 'seed': 42, 'embedder': 'fake'}}
--- ann_retrieval ---
  raw.jsonl top-level keys: ['key', 'run_id', 'timestamp', 'status', 'strategy', 'mode', 'size', 'trial', 'node', 'retries', 'metrics', 'harness_wall_s', 'unaccounted_s', 'llm_snapshot_delta']
  raw.jsonl metrics.extra (diagnostics) keys: ['top_k', 'index_size', 'shortlist_size', 'max_cosine', 'ef_search', 'exact_topk_overlap']
  manifest.json strategy_config: {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}
  manifest.json has strategy name? False
  manifest.json has embedder? False
  strategy_config.json: {'strategy': 'ann_retrieval', 'config': {'k': 10, 'M': 16, 'ef_construction': 200, 'ef_search': 128, 'metric': 'inner_product_on_unit_vectors', 'index': 'IndexHNSWFlat', 'faiss_threads': 1, 'faiss_version': '1.15.1', 'seed': 42}, 'embedder': {'type': 'fake', 'uses_embeddings': True, 'dim': 32, 'seed': 42}, 'mode': 'sweep', 'command_line_params': {'strategy': 'ann_retrieval', 'k': None, 'theta': None, 'ef_search': None, 's_min': None, 's_max': None, 'n_bits': None, 'seed': 42, 'embedder': 'fake'}}
```

---

### Check R-D: Live Gates and `MiniLMEmbedder`

1. **`--live` gates across all strategies (`--embedder fake` vs `minilm`, with and without `--dry-run`, without API key):** `[Confirmed]`
   - For all 3 embedding strategies (`embedding_threshold`, `ann_retrieval`, `bounded_bucket`), `--live --embedder fake` (both with and without `--dry-run`) exits `1` **before** `--names-file`, `--confirm`, peak-window, or API-key checks, printing `ERROR: Live execution for embedding strategy '<name>' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs.`
   - For non-embedding strategies (`brute_force`, `null`), `--live --dry-run` exits `0` with either `--embedder fake` or `--embedder minilm` (no API key or `sentence_transformers` needed).
   - For embedding strategies, `--live --dry-run --embedder minilm` exits `0` without importing `sentence_transformers`, needing pins, or needing an API key.
2. **`MiniLMEmbedder` pins, version check, and protocol parity with `FakeEmbedder`:** `[Confirmed]` (See Finding **F-3**)
   - Shipped constants in `src/graph_insertion/embedding_minilm.py`: `SENTENCE_TRANSFORMERS_VERSION_PIN = None` and `MODEL_REVISION_PIN = None`.
   - `MiniLMEmbedder()` fails closed with `ValueError` when `MODEL_REVISION_PIN is None`.
   - **However (`F-3`):** `MiniLMEmbedder.__init__()` does **not** check `SENTENCE_TRANSFORMERS_VERSION_PIN`: passing `revision="rev-test"` when `SENTENCE_TRANSFORMERS_VERSION_PIN is None` succeeds, and setting `SENTENCE_TRANSFORMERS_VERSION_PIN = "3.0.0"` when `sentence_transformers.__version__ == "99.99.99-mismatch"` also succeeds without raising.
   - Return shapes and dtypes match `FakeEmbedder` (`dim=384`): `embed("hello")` $\to$ `(384,) float32`; `embed_many([])` $\to$ `(0, 384) float32` without calling `encode()`; `embed_many(["one"])` $\to$ `(1, 384) float32`; `embed_many(["a", "b", "c"])` $\to$ `(3, 384) float32`.
3. **`MeteredEmbedder` wrapping per trial (`scripts/run_experiment.py:958-961`, `harness.py:725`):** `[Confirmed]`
   - In `scripts/run_experiment.py:958-961`, `shared_minilm = MiniLMEmbedder()` is constructed once and `embedder_factory = lambda _seed: shared_minilm` returns that shared instance for each trial.
   - In `src/graph_insertion/harness.py:725-727`, `run_single_trial()` wraps the returned embedder in a fresh `MeteredEmbedder(base_embedder)` per trial (`embedder.reset()` is also called before each insertion step inside the trial at line 752), while the underlying `SentenceTransformer` model is loaded only once per CLI invocation.
4. **OpenMP / BLAS thread-check snippet in Section 8 of the implementer's report:** `[Confirmed]` (See Finding **F-6**)
   - Inspected `.venv-ann/lib/python3.14/site-packages/faiss/../faiss_cpu.libs/`: `faiss-cpu 1.15.1` links against its bundled `libgomp-e985bcbb.so.1.0.0` and `libopenblaso-r0-d77a1985.3.15.so`. Because PyTorch (used by `sentence-transformers`) links its own OpenMP runtime (`libgomp` / `libiomp5`) and manages CPU threads via `torch.get_num_threads()`, `faiss.omp_set_num_threads(1)` controls FAISS's `libgomp` pool and may or may not alter PyTorch's intra-op thread count depending on symbol resolution order.
   - In Section 8 of `docs/reports/INFRA-007-gemini-strategy-wiring.md` (line 2562), the one-liner works in `.venv-ann` without `PYTHONPATH=src` (because `graph_insertion` is installed editable via `_graph_insertion.pth`), **except** that it hardcodes `emb = MiniLMEmbedder(revision='<MODEL_REVISION_PIN>')` with the literal string `'<MODEL_REVISION_PIN>'`. Once `MODEL_REVISION_PIN` is set in `embedding_minilm.py`, Luke should run `emb = MiniLMEmbedder()` (no arguments).

```text
=== R-D.1: --live gates across strategies ===
  --live (no dry-run) strat=embedding_threshold  emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'embedding_threshold' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live --dry-run    strat=embedding_threshold  emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'embedding_threshold' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live (no dry-run) strat=embedding_threshold  emb=minilm -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=embedding_threshold  emb=minilm -> rc=0 stderr=''
  --live (no dry-run) strat=ann_retrieval        emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'ann_retrieval' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live --dry-run    strat=ann_retrieval        emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'ann_retrieval' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live (no dry-run) strat=ann_retrieval        emb=minilm -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=ann_retrieval        emb=minilm -> rc=0 stderr=''
  --live (no dry-run) strat=bounded_bucket       emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'bounded_bucket' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live --dry-run    strat=bounded_bucket       emb=fake   -> rc=1 stderr="ERROR: Live execution for embedding strategy 'bounded_bucket' requires '--embedder minilm' (pinned sentence-transformers all-MiniLM-L6-v2 per D-35(4)); '--embedder fake' is refused for live runs."
  --live (no dry-run) strat=bounded_bucket       emb=minilm -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=bounded_bucket       emb=minilm -> rc=0 stderr=''
  --live (no dry-run) strat=brute_force          emb=fake   -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=brute_force          emb=fake   -> rc=0 stderr=''
  --live (no dry-run) strat=brute_force          emb=minilm -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=brute_force          emb=minilm -> rc=0 stderr=''
  --live (no dry-run) strat=null                 emb=fake   -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=null                 emb=fake   -> rc=0 stderr=''
  --live (no dry-run) strat=null                 emb=minilm -> rc=1 stderr='ERROR: Live execution in sweep mode requires an external names file (--names-file) generated from the verified DATA-004 concept name pool. Placeholder names are only permitted for offline/non-live runs.'
  --live --dry-run    strat=null                 emb=minilm -> rc=0 stderr=''

=== R-D.2: MiniLMEmbedder vs FakeEmbedder comparison & pin behavior ===
Shipped SENTENCE_TRANSFORMERS_VERSION_PIN: None
Shipped MODEL_REVISION_PIN: None
Constructed MiniLMEmbedder when sentence_transformers.__version__='99.99.99-mismatch' and PIN='3.0.0': SUCCEEDED (no runtime version check!)
  identity(): {'model_name': 'all-MiniLM-L6-v2', 'dim': 384, 'revision': 'rev-test', 'sentence_transformers_version_pin': '3.0.0', 'device': 'cpu', 'dtype': 'float32'}
Constructed MiniLMEmbedder when SENTENCE_TRANSFORMERS_VERSION_PIN=None and revision='rev-test': SUCCEEDED (only MODEL_REVISION_PIN is checked!)
  embed('hello')            : MiniLM=(shape=(384,), dtype=float32) | Fake=(shape=(384,), dtype=float32)
  embed_many([])            : MiniLM=(shape=(0, 384), dtype=float32) | Fake=(shape=(0, 384), dtype=float32)
  embed_many(['one'])       : MiniLM=(shape=(1, 384), dtype=float32) | Fake=(shape=(1, 384), dtype=float32)
  embed_many(['a', 'b', 'c']): MiniLM=(shape=(3, 384), dtype=float32) | Fake=(shape=(3, 384), dtype=float32)
  embed_many(['single']) when encode returns 1D float64 (384,): shape=(1, 384), dtype=float32
```

---

### Check R-E: Call Bounds and Dry-Run

1. **Sweep mode call bounds across all 12 README configurations (`sizes = [50, 100, 200, 500, 1000, 2000]`, `10` trials/size):** `[Confirmed]`
   - `brute_force` and `embedding_threshold` ($\theta \in \{0.6, 0.4, 0.5\}$): `38500` planned calls.
   - `ann_retrieval`: $k=10, \text{ef} \in \{128, 64, 256\} \to 600$; $k=5 \to 300$; $k=20 \to 1200$.
   - `bounded_bucket`: $(5, 10, 12) \to 600$; $(2, 5, 12) \to 300$; $(10, 20, 12) \to 1200$.
   - Cross-checked one of each strategy directly against ` sum(10 * candidate_upper_bound(n, strategy))` and `compute_planned_calls_upper_bound()` in `scripts/run_experiment.py`: exact match across all 4 strategies.
2. **Accuracy mode call bounds (`DSA_gold_standard_MEKG`: 29 nodes $\to$ $n_{\text{existing}}=28$, 29 trials; `metacademy_gold_standard_MEKG`: 141 nodes $\to$ $n_{\text{existing}}=140$, 30 trials; 59 trials total):** `[Confirmed]`
   - `bounded_bucket`: $(5, 10) \to 590$ (`290 + 300`); $(2, 5) \to 295$ (`145 + 150`); $(10, 20) \to 1180$ (`580 + 600`).
   - `ann_retrieval`: $k=10, \text{ef} \in \{128, 64, 256\} \to 590$ (`290 + 300`); $k=5 \to 295$ (`145 + 150`); $k=20 \to 1180$ (`580 + 600`).

```text
=== R-E: Call bounds and dry-run (12 sweep configs + accuracy mode) ===
  Sweep primary_s1_brute_force          : CLI dry-run bound =  38500 (expected  38500)
  Sweep primary_s2_embedding_threshold  : CLI dry-run bound =  38500 (expected  38500)
  Sweep primary_s3_ann_retrieval        : CLI dry-run bound =    600 (expected    600)
  Sweep primary_s4_bounded_bucket       : CLI dry-run bound =    600 (expected    600)
  Sweep sens_s2_theta_0.4               : CLI dry-run bound =  38500 (expected  38500)
  Sweep sens_s2_theta_0.5               : CLI dry-run bound =  38500 (expected  38500)
  Sweep sens_s3_k_5                     : CLI dry-run bound =    300 (expected    300)
  Sweep sens_s3_k_20                    : CLI dry-run bound =   1200 (expected   1200)
  Sweep sens_s3_ef_64                   : CLI dry-run bound =    600 (expected    600)
  Sweep sens_s3_ef_256                  : CLI dry-run bound =    600 (expected    600)
  Sweep sens_s4_smin2_smax5             : CLI dry-run bound =    300 (expected    300)
  Sweep sens_s4_smin10_smax20           : CLI dry-run bound =   1200 (expected   1200)

Cross-check one of each strategy against candidate_upper_bound & compute_planned_calls_upper_bound:
  brute_force         : sum(10*candidate_upper_bound)= 38500 | compute_planned_calls_upper_bound= 38500 (full=38500)
  embedding_threshold : sum(10*candidate_upper_bound)= 38500 | compute_planned_calls_upper_bound= 38500 (full=38500)
  ann_retrieval       : sum(10*candidate_upper_bound)=   600 | compute_planned_calls_upper_bound=   600 (full=600)
  bounded_bucket      : sum(10*candidate_upper_bound)=   600 | compute_planned_calls_upper_bound=   600 (full=600)

Accuracy mode dry-run bounds (DSA n_existing=28 x 29 trials + Metacademy n_existing=140 x 30 trials):
  Accuracy bounded_bucket (5,10)     : bound= 590 (expected  590) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 290 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 300
  Accuracy bounded_bucket (2,5)      : bound= 295 (expected  295) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 145 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 150
  Accuracy bounded_bucket (10,20)    : bound=1180 (expected 1180) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 580 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 600
  Accuracy ann_retrieval k=10 ef=128 : bound= 590 (expected  590) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 290 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 300
  Accuracy ann_retrieval k=5 ef=128  : bound= 295 (expected  295) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 145 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 150
  Accuracy ann_retrieval k=20 ef=128 : bound=1180 (expected 1180) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 580 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 600
  Accuracy ann_retrieval k=10 ef=64  : bound= 590 (expected  590) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 290 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 300
  Accuracy ann_retrieval k=10 ef=256 : bound= 590 (expected  590) | Corpus: DSA_gold_standard_MEKG | Sample: 29 (of 29) | Trials: 29 | Max LLM: 290 | Corpus: metacademy_gold_standard_MEKG | Sample: 30 (of 141) | Trials: 30 | Max LLM: 300
```

---

### Check R-F: Tests and Mutants

1. **Baseline run of the three new test files (one run):** `[Confirmed]`
   - `.venv-ann/bin/python -m pytest tests/test_strategy_registry.py tests/test_embedding_minilm.py tests/test_run_experiment_cli.py -v` $\to$ **`86 passed in 6.56s`**.
2. **Spot-check of 10 tests across the three new files:** `[Confirmed]`
   - [`test_registry_keys_complete_and_aliased`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py#L29-L41): asserts exact key set and `STRATEGY_REGISTRY is STRATEGY_FACTORIES`.
   - [`test_parameters_and_seed_reach_strategy_config`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py#L64-L90): asserts non-default parameters and seeds propagate into `strategy.config()`.
   - [`test_strategies_init_and_registry_import_without_faiss_and_sentence_transformers_subprocess`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py#L144-L171): runs a real subprocess with `sys.modules['faiss'] = None` and `sys.modules['sentence_transformers'] = None` and verifies non-FAISS strategies instantiate while `ann_retrieval` raises `ImportError`.
   - [`test_lazy_exports_from_strategies_package`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_strategy_registry.py#L173-L195): tests lazy `__getattr__` for the 5 strategy classes, **but omits `strategies_pkg.STRATEGY_FACTORIES`** (which is why mutant `R-M24` survived).
   - [`test_refuses_when_pin_is_none_or_empty`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_embedding_minilm.py#L103-L128): verifies `MODEL_REVISION_PIN=None`, `revision=None`, `revision=""`, `revision="   "`, and `revision=123` all raise `ValueError` without importing `sentence_transformers`.
   - [`test_embed_and_embed_many_shapes_dtypes_and_call_counts`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_embedding_minilm.py#L130-L182): verifies `embed()`, `embed_many([])`, `embed_many(["alpha", "beta", "gamma"])`, and `MeteredEmbedder` wrapping, **but uses a stub that already returns `float32` and `2-D` arrays and never tests 1-element `embed_many(["single"])` or wrong-dimension vectors** (which is why mutants `R-M16`, `R-M20`, and `R-M25` survived).
   - [`test_inapplicable_flag_exits_2_naming_flag_and_strategy`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L91-L133): tests 15 parametrised inapplicable `(strategy, flag)` pairs and asserts exit code `2` and both flag and strategy in `stderr`.
   - [`test_sidecar_written_and_resume_mismatch_refused`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L465-L561): tests sidecar creation and refusal on `s_max`, `(s_min, s_max)`, `n_bits`, `seed`, and `strategy` mismatches when `--resume` is passed, **but never tests mismatch refusal when `--resume` is omitted (`R-M11`) or whether `strategy_config.json` is written before vs after `run_experiment()` (`R-M26`)**.
   - [`test_live_with_embedding_strategy_and_fake_embedder_refused_before_key_or_client`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L611-L635): deletes `DEEPSEEK_API_KEY` and verifies `--live --embedder fake` exits `1` naming `--embedder minilm`.
   - [`test_live_dry_run_exits_0_for_all_strategies_without_api_key`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py#L637-L684): tests `--live --dry-run` with `minilm` and `fake`, **but because `--live --dry-run` returns at line 890, no test in the file ever executes the `--embedder minilm` branch at lines 929–961 (`R-M19`)**.
3. **Final full-suite pytest run (one run):** `[Confirmed]`
   - `.venv-ann/bin/python -m pytest` $\to$ **`674 passed, 3 skipped in 134.32s (0:02:14)`** (exact match to 588 baseline + 86 new tests).

```text
=== Baseline run of 3 new test files ===
$ .venv-ann/bin/python -m pytest tests/test_strategy_registry.py tests/test_embedding_minilm.py tests/test_run_experiment_cli.py -v
============================== 86 passed in 6.56s ==============================

=== Final single run of full test suite ===
$ .venv-ann/bin/python -m pytest
================== 674 passed, 3 skipped in 134.32s (0:02:14) ==================
```

---

### Check R-G: Decision `[D-64]` and Implementer Report Verification

- **Decision `[D-64]` vs code:** `[Confirmed]`
  - Every positive claim in `[D-64]` matches the implementation in `registry.py`, `embedding_minilm.py`, and `scripts/run_experiment.py`.
  - Note: `[D-64]` accurately states that `MiniLMEmbedder` "fails closed when `MODEL_REVISION_PIN` is `None`" and that `strategy_config.json` refuses "any strategy or `config()` mismatch"; once `INFRA-007-P` adds `SENTENCE_TRANSFORMERS_VERSION_PIN` validation and embedder-identity resume checking (`F-1`, `F-3`), `[D-64]` (or a new decision `[D-66]`) should note those tightenings.
- **Implementer report (`docs/reports/INFRA-007-gemini-strategy-wiring.md`) verification:** `[Confirmed]`
  - Programmatically compared all 6 unified diffs in Section 7.1 of `docs/reports/INFRA-007-gemini-strategy-wiring.md` against `git show fda97db --format= -- <file>`: **6/6 matched verbatim**.
  - Programmatically compared all 6 created files in Section 7.2 and `patch/0001-INFRA-007-wire-four-strategies-parameters-run-direct.patch`: **6/6 matched byte-for-byte**.
  - As noted in Finding **F-6**, the report lacks a **"Found but not changed"** section and has a placeholder literal `revision='<MODEL_REVISION_PIN>'` in Section 8's timing snippet (line 2562).

```text
Diff check src/graph_insertion/strategies/__init__.py: exact_match_in_report=True (len=43 lines)
Diff check scripts/run_experiment.py: exact_match_in_report=True (len=350 lines)
Diff check scripts/README.md: exact_match_in_report=True (len=52 lines)
Diff check pyproject.toml: exact_match_in_report=True (len=12 lines)
Diff check docs/decisions/decision-log.md: exact_match_in_report=True (len=17 lines)
Diff check docs/tasks/status.md: exact_match_in_report=True (len=17 lines)
```

---

## 5. Mutation Table (`R-M01` .. `R-M26`)

All 26 mutants (the 18 required by the review prompt `R-M01`..`R-M18` plus 8 additional reviewer mutants `R-M19`..`R-M26`) were executed one at a time with `-x` against an isolated `/tmp/infra007_mutants` copy using only the single relevant new test file.

**Summary:** `19/26 KILLED`, `7/26 SURVIVED` (`R-M11`, `R-M16`, `R-M19`, `R-M20`, `R-M24`, `R-M25`, `R-M26`).

| Mutant | Target `file:line` | Mutation Applied | Test File Run (`-x`) | Result | Killer Test / Survival Explanation (`[Confirmed]`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-M01** | `src/graph_insertion/strategies/registry.py:163` | Remove `"ann_retrieval"` from `PARAM_APPLICABILITY["k"]` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_applicability_matrix` |
| **R-M02** | `src/graph_insertion/strategies/registry.py:113-116` | Swap `k` and `ef_search` kwargs in `_factory_ann_retrieval` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| **R-M03** | `src/graph_insertion/strategies/registry.py:138-139` | Ignore `n_bits` (`pass`) in `_factory_bounded_bucket` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| **R-M04** | `scripts/run_experiment.py:518-520` | Change `--theta` parser type from `type=float` to `type=int` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestCLIParsingAndApplicability::test_out_of_range_values_exit_1_without_traceback[cli_args0]` (`--theta 1.5` exits `2` instead of `1`) |
| **R-M05** | `src/graph_insertion/strategies/registry.py:53` | Change `stub` default `k` from `5` to `1` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_every_strategy_constructs_with_defaults` |
| **R-M06** | `src/graph_insertion/strategies/registry.py:202-203` | Drop `theta` from `build_strategy_slug` for `embedding_threshold` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_slug_and_default_run_id_derivation` |
| **R-M07** | `src/graph_insertion/strategies/registry.py:221-222` | Drop non-default `seed<seed>` suffix from `build_strategy_slug` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_slug_and_default_run_id_derivation` |
| **R-M08** | `src/graph_insertion/strategies/registry.py:229-232` | `derive_default_run_id` hardcodes `sweep_` instead of `f"{mode}_..."` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_section_2d_default_run_directories_and_bounds_via_cli` (accuracy directory check) |
| **R-M09** | `scripts/run_experiment.py:1007-1026` | Move sidecar write after `run_experiment` and check `not raw_jsonl_path.exists()` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_sidecar_written_and_resume_mismatch_refused` (`raw.jsonl` exists after run so sidecar is never written) |
| **R-M10** | `scripts/run_experiment.py:798` | Resume guard compares only `stored_strategy != current_strategy`, ignoring `config()` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_sidecar_written_and_resume_mismatch_refused` |
| **R-M11** | `scripts/run_experiment.py:787` | Require `config.resume` before checking sidecar even when `has_existing_raw` is `True` | `tests/test_run_experiment_cli.py` | **SURVIVED** | All mismatch tests in `test_sidecar_written_and_resume_mismatch_refused` pass `--resume`; no test exercises a mismatched sidecar without `--resume` (**F-7**). |
| **R-M12** | `scripts/run_experiment.py:865-873` | Remove pre-key/pre-client `--live` + `--embedder fake` refusal | `tests/test_run_experiment_cli.py` | **KILLED** | `TestLiveAndEmbedderGates::test_live_with_embedding_strategy_and_fake_embedder_refused_before_key_or_client` |
| **R-M13** | `scripts/run_experiment.py:866` | Refuse `--live` + `--embedder fake` for non-embedding strategies (`brute_force`, `null`) too | `tests/test_run_experiment_cli.py` | **KILLED** | `TestLiveAndEmbedderGates::test_live_dry_run_exits_0_for_all_strategies_without_api_key[brute_force-fake]` |
| **R-M14** | `src/graph_insertion/embedding_minilm.py:70-75` | Remove fail-closed `MODEL_REVISION_PIN` check in `MiniLMEmbedder.__init__` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_refuses_when_pin_is_none_or_empty` |
| **R-M15** | `src/graph_insertion/embedding_minilm.py:110` | Change `embed_many` cast to `dtype=np.float64` | `tests/test_embedding_minilm.py` | **KILLED** | `TestMiniLMEmbedderOffline::test_embed_and_embed_many_shapes_dtypes_and_call_counts` |
| **R-M16** | `src/graph_insertion/embedding_minilm.py:111-112` | Remove `if arr.ndim == 1 and len(texts) == 1: arr = arr.reshape(1, -1)` in `embed_many` | `tests/test_embedding_minilm.py` | **SURVIVED** | `_StubSentenceTransformer.encode` always returns a 2-D array for list inputs and no test calls `embed_many` with a 1-D stub return (**F-7**). |
| **R-M17** | `src/graph_insertion/embedding_minilm.py:19` | Add top-level `from sentence_transformers import SentenceTransformer` | `tests/test_embedding_minilm.py` | **KILLED** | Collection error (`ModuleNotFoundError: No module named 'sentence_transformers'`) |
| **R-M18** | `src/graph_insertion/strategies/__init__.py:9` | Add top-level `import faiss` in `strategies/__init__.py` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_strategies_init_and_registry_import_without_faiss_and_sentence_transformers_subprocess` |
| **R-M19** | `scripts/run_experiment.py:929` | Replace `if not uses_embeddings or args.embedder == "fake":` with `if True:` (bypass CLI `minilm` branch) | `tests/test_run_experiment_cli.py` | **SURVIVED** | Every CLI test passing `--embedder minilm` also passes `--live --dry-run`, which returns at line 890 before reaching line 929 (**F-2**). |
| **R-M20** | `src/graph_insertion/embedding_minilm.py:110` | Replace `np.asarray(mat, dtype=np.float32)` with `np.asarray(mat)` | `tests/test_embedding_minilm.py` | **SURVIVED** | `_StubSentenceTransformer.encode` already returns `float32`, so omitting the cast in `embed_many` is not caught (**F-7**). |
| **R-M21** | `scripts/run_experiment.py:1007` | Remove `not has_existing_raw` guard when writing `strategy_config.json` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_older_directory_with_raw_jsonl_but_no_sidecar_warns_and_does_not_refuse` |
| **R-M22** | `src/graph_insertion/strategies/registry.py:134-137` | Swap `s_min` and `s_max` in `_factory_bounded_bucket` | `tests/test_strategy_registry.py` | **KILLED** | `TestStrategyRegistry::test_parameters_and_seed_reach_strategy_config` |
| **R-M23** | `scripts/run_experiment.py:743-749` | Invert precedence so `--run-id` overrides `--output-dir` | `tests/test_run_experiment_cli.py` | **KILLED** | `TestRunDirectoryKeysAndSidecarGuard::test_explicit_run_id_and_output_dir_precedence` |
| **R-M24** | `src/graph_insertion/strategies/__init__.py:34-36` | Remove `STRATEGY_FACTORIES` branch from `strategies/__init__.py:__getattr__` | `tests/test_strategy_registry.py` | **SURVIVED** | `test_lazy_exports_from_strategies_package` never accesses `strategies_pkg.STRATEGY_FACTORIES` (**F-7**). |
| **R-M25** | `src/graph_insertion/embedding_minilm.py:99-102` | Remove `if arr.shape != (self.dim,): raise ValueError(...)` in `MiniLMEmbedder.embed` | `tests/test_embedding_minilm.py` | **SURVIVED** | `_StubSentenceTransformer` always returns `dim=384`; no test exercises a wrong-dimension return (**F-7**). |
| **R-M26** | `scripts/run_experiment.py:1007-1026` | Move sidecar write *after* `run_experiment()` while keeping `if not has_existing_raw:` | `tests/test_run_experiment_cli.py` | **SURVIVED** | No test inspects `strategy_config.json` inside the first trial callback or simulates an mid-run exception before `run_experiment()` returns (**F-4**). |

**Comparison with Implementer's Mutants (`I-M1` .. `I-M13`):**
All 13 of the implementer's reported mutants (`I-M1`..`I-M13` in Section 5.3 of `docs/reports/INFRA-007-gemini-strategy-wiring.md`) are confirmed killed (`R-M02`/`R-M03`/`R-M05`/`R-M06`/`R-M07`/`R-M09`/`R-M10`/`R-M12`/`R-M14`/`R-M17`/`R-M18`/`R-M22` cover the same logic). Our finer-grained mutants (`R-M11`, `R-M16`, `R-M19`, `R-M20`, `R-M24`, `R-M25`, `R-M26`) exposed 7 untested paths that `I-M1`..`I-M13` did not probe.

---

## 6. Recommended Status Relay (Do Not Edit `status.md` or `decision-log.md`)

- **`docs/tasks/status.md`:**
  - `INFRA-007` is currently marked `done (report: docs/reports/INFRA-007-gemini-strategy-wiring.md, commit fda97db, D-64; live embedding runs gated on sentence-transformers version and all-MiniLM-L6-v2 revision pins)`.
  - Recommend appending a row (or updating `INFRA-007` notes) to record `INFRA-007-R`: `done — ACCEPT WITH AMENDMENTS (report: docs/reports/INFRA-007-R-gemini.md; 0 blockers, 4 should-fix items F-1..F-4 and 3 nits F-5..F-7 to fold into INFRA-007-P before live runs)`.
- **`docs/decisions/decision-log.md`:**
  - No edit needed for `INFRA-007-R`.
  - When `INFRA-007-P` is assigned, **note that `[D-65]` is already taken** in `docs/decisions/decision-log.md` (used by `8d55ca6` for `DATA-004` pool acceptance), so the **next free decision ID is `[D-66]`**.

---

## 7. Prompt Corrections (Where the Prompt / APC Context Disagreed with the Repo)

1. **Third test file name in Check R-F:** The review prompt refers to the third new test file as `test_cli_strategy_wiring.py`. In the repository (commit `fda97db` and `[D-64]`), the file is actually named [`tests/test_run_experiment_cli.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py) (`[Confirmed]`).
2. **Next free decision ID and `DATA-004` status in APC notes:** The APC's accompanying summary stated that "the next free ID is probably D-65" and "`DATA-004` is still not generated. A live sweep cannot start without it." In the live repository (`HEAD` at `e276c37`), commit `4f6de3d` (`DATA-004: add generated name pool np1w (2254 names, 3 shards, Sonnet 5 Low, adapter ba3a8a2)`) and commit `8d55ca6` (`docs: record DATA-004 pool acceptance (D-65), close DATA-004 and FIX-017`) have **already** generated and accepted the `DATA-004` name pool (`data/concept_names/pool_np1w.json`) and used decision ID **`[D-65]`**. Thus `DATA-004` is `done`, and the next free decision ID is **`[D-66]`** (`[Confirmed]`).
3. **`MiniLMEmbedder` fail-closed pin check scope:** The review prompt states under Check R-D.2 that "`MiniLMEmbedder()` with no arguments raises `ValueError` while either pin is `None`." In the actual code ([`src/graph_insertion/embedding_minilm.py:67-75`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py#L67-L75)), `MiniLMEmbedder.__init__()` checks **only** `MODEL_REVISION_PIN` (`actual_revision`), not `SENTENCE_TRANSFORMERS_VERSION_PIN` (`[Confirmed]`, documented as Finding **F-3**).
4. **Pre-`INFRA-007` `--dry-run` disk behavior in Check R-C.2:** The APC's summary asked "whether the old dry-run wrote anything." Checked against `git show fda97db~1:scripts/run_experiment.py` and `src/graph_insertion/harness.py:938`: the pre-`INFRA-007` offline `--dry-run` **already** created `<output_dir>/manifest.json` (`write_manifest(config, plan)`). `INFRA-007` added `<output_dir>/strategy_config.json` before `run_experiment()`, which additionally triggers `"git_dirty": true` in `manifest.json` because `results/` is not in `.gitignore` (`[Confirmed]`, documented as Finding **F-4**).

---

## 8. Found But Not Changed

In accordance with Rule 0.1, none of the following pre-existing or adjacent items noticed during the review were modified:

1. **Unstaged modification in `docs/context/repo-tree.txt`:** `git status --short` showed ` M docs/context/repo-tree.txt` upon session start; left untouched.
2. **Existing task worktrees:** `git worktree list` shows two additional worktrees (`../llm-graph-insertion-complexity-FIX-017` at `78b0014 [task/FIX-017]` and `../llm-graph-insertion-complexity-gen` at `21d8e12`); neither was touched.
3. **`.gitignore` coverage of `results/`:** `.gitignore` (lines 42–43) ignores `results/datagen/` but not `results/`, so any default run directory created under `results/` appears as untracked (`?? results/...`) in `git status --porcelain` and causes `harness.py:get_git_info()` to record `"git_dirty": true` in `manifest.json` if files are written to `results/` prior to `write_manifest()`.
4. **Negative-zero float slug formatting (`build_strategy_slug`):** Passing `--theta -0.0` produces `config()["theta"] == -0.0` (which compares equal to `0.0` in Python dictionaries) but formats as `f"theta{config_dict['theta']}"` $\to$ `"theta-0.0"`. Normalizing `0.0 if theta == 0.0 else theta` in `EmbeddingThresholdStrategy.__init__` or `build_strategy_slug` would prevent `-0.0` slug divergence.
5. **Misleading offline missing-`--confirm` error wording in `harness.py:703`:** When running `scripts/run_experiment.py` in offline mode (without `--live`) and omitting both `--dry-run` and `--confirm`, `HarnessConfig.__post_init__` raises `ValueError("Live experiment runs require explicit confirmation via config.confirm=True (or CLI flag --confirm)...")`, even though the run is offline (`StubDecisionStep`).

---

## 9. Open Questions

1. **[`APC` / `APC-A`] Should default run directories encode `--embedder` (`fake` vs `minilm`) or should `results/sweep_<strategy>_<slug>` be reserved for canonical runs?**
   Currently (`scripts/run_experiment.py:739-753`), an offline smoke run with `--confirm` (default `--embedder fake`) and a live run with `--live --embedder minilm --confirm` resolve to the **exact same** default directory (`results/sweep_<strategy>_<slug>`). Even after `INFRA-007-P` adds `sidecar["embedder"]` checking to `check_or_prepare_sidecar()` (`F-1`), an earlier offline `--dry-run` or `--confirm` run in `results/sweep_ann_retrieval_k10_ef128` will leave a `"type": "fake"` `strategy_config.json` that blocks a subsequent live run unless deleted or unless offline `fake` runs default to a `_fake` directory suffix.
2. **[`Luke`] What are the exact `sentence-transformers` version and `all-MiniLM-L6-v2` snapshot revision hash in `.venv-ann`, and does `faiss.omp_set_num_threads(1)` affect `MiniLMEmbedder` latency on your machine?**
   Needed for `INFRA-007-P` to set `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py` and `pyproject.toml`. When running the Section 8 timing check from the implementer's report, remember to call `emb = MiniLMEmbedder()` (not `revision='<MODEL_REVISION_PIN>'`, per Finding **F-6**).
3. **[`APC`] Should plain offline `--dry-run` stop writing `strategy_config.json` (and/or `manifest.json`) to disk, or should `results/` be added to `.gitignore`?**
   See Finding **F-4**: writing `results/<run_id>/strategy_config.json` before `run_experiment()` writes `manifest.json` currently dirties the git working tree (`?? results/<run_id>/`) so `manifest.json` records `"git_dirty": true`.
