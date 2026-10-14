# INFRA-007-Q — Set Embedder Version & Revision Pins and Close INFRA-007 (`[D-67]`)

- **Task ID:** `INFRA-007-Q`
- **Decision ID:** `[D-67]`
- **Date:** 2026-10-14
- **Branch:** `master` (in-place checkout, uncommitted until Step 5 per Rule 1)

---

## 1. Agent Identity

- **Agent:** `gemini` (Google Antigravity)
- **Model Label:** `Gemini 3.8 Flash (Medium)` (user switched model selection to Medium during session)
- **Session / Conversation ID:** `098dcdd4-c444-4fcd-af8f-1b2054b31802`

---

## 2. What Was Asked / What I Did

### 2.1 Section 0 Inputs
Luke supplied the exact outputs from running the install and model download commands on his machine:
```text
SENTENCE_TRANSFORMERS_VERSION = 6.1.0
MODEL_REVISION                = 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
```
- Version `6.1.0` is a valid PEP 440 version string (`[Confirmed]`).
- Revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is exactly 40 lowercase hexadecimal characters (`[Confirmed]`).

### 2.2 Summary of Actions Taken
1. **Embedder module pins (`src/graph_insertion/embedding_minilm.py`):**
   Set `SENTENCE_TRANSFORMERS_VERSION_PIN = "6.1.0"` and `MODEL_REVISION_PIN = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"`, and updated the header comments to record that pins are locked per `[D-67]`.
2. **Packaging dependency (`pyproject.toml`):**
   Updated `[project.optional-dependencies]` `embed` line to `embed = ["sentence-transformers==6.1.0"]` and dropped the TODO comment.
3. **Audit of existing tests for shipped `None` assumptions:**
   Searched `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`, and `tests/test_strategy_registry.py` for assertions assuming shipped pins are `None` or tests relying on unmonkeypatched defaults. Found that all fail-closed tests already explicitly monkeypatched `SENTENCE_TRANSFORMERS_VERSION_PIN` or `MODEL_REVISION_PIN` to `None`. No existing test assertions required modification.
4. **Added well-formedness test (`tests/test_embedding_minilm.py`):**
   Added `test_shipped_pins_well_formed_and_match_pyproject` asserting that `MODEL_REVISION_PIN` matches `^[0-9a-f]40$`, `SENTENCE_TRANSFORMERS_VERSION_PIN` is a non-empty string without whitespace, and `pyproject.toml`'s `embed` extra parsed with standard library `tomllib` matches `["sentence-transformers==" + SENTENCE_TRANSFORMERS_VERSION_PIN]` exactly.
5. **Documentation update (`scripts/README.md`):**
   Added the `Live Embedding Runs & Offline Smoke Rule ([D-67])` paragraph documenting the one-time model download prerequisite, the rule that offline smoke runs of embedding strategies with `--embedder fake` must use `--output-dir` outside `results/` to prevent default directory conflicts with subsequent live runs, and noting the OpenMP timing check.
6. **Decision log entry (`docs/decisions/decision-log.md`):**
   Appended `[D-67]` recording the locked pins, the testing convention that fail-closed behaviour is tested via monkeypatching, the offline smoke directory isolation rule, and open items.
7. **Task status update (`docs/tasks/status.md`):**
   Updated the `INFRA-007` status row from `**needs-review**` to `**done**` with the required attribution text referencing reports `INFRA-007-gemini-strategy-wiring.md` (`D-64`), `INFRA-007-R-gemini.md`, `INFRA-007-P-gemini.md` (`D-66`), and `INFRA-007-Q-gemini.md` (`D-67`).

---

## 3. Prompt Corrections

1. **Reserved Decision ID `D-67`:** `[Confirmed]` Grepped `docs/decisions/decision-log.md`; `D-67` was not present (`D-66` was the highest ID).
2. **Shipped pins were `None`:** `[Confirmed]` Prior to this task, `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` were `None` in `src/graph_insertion/embedding_minilm.py`.
3. **Existing test assumptions:** `[Confirmed]` No existing test assumed shipped pins were `None`; all fail-closed tests already used `monkeypatch.setattr(...)` to isolate their assertions.
4. **Report filenames:** `[Confirmed]` Verified that all referenced report files (`docs/reports/INFRA-007-gemini-strategy-wiring.md`, `docs/reports/INFRA-007-R-gemini.md`, `docs/reports/INFRA-007-P-gemini.md`) exist on disk under those exact filenames.

---

## 4. Verification Output

### 4.1 Pre-Edit State
```text
$ sha256sum src/graph_insertion/embedding_minilm.py pyproject.toml tests/test_embedding_minilm.py tests/test_run_experiment_cli.py tests/test_strategy_registry.py scripts/README.md docs/decisions/decision-log.md docs/tasks/status.md
95593ed28d6b6469d474255fa5bef0d3c71652ab74ec44a834664a142f3f50e1  src/graph_insertion/embedding_minilm.py
bae9cfc11fa878873c993b02e1b1abc6a52f99eb3710bf4ff76c9fdb197271f7  pyproject.toml
a42a0f707ce21a673994f37773633c346d48591060adf17dbda6205b9cf64a04  tests/test_embedding_minilm.py
af144db8c9087f7380069279a16d7eed56a1e9d11b794258fff1a5953c4b1b9c  tests/test_run_experiment_cli.py
6eff921412506b31e60aa020f8d3d2b1a1793a933c7dac8a01bc5d9b36af1478  tests/test_strategy_registry.py
faf4ad5f45c0b6dcb1a8c6397f33bc1f5366d30daa333a80a9540a4e3cd88247  scripts/README.md
8e9d0d0fc5475864886327aa8b5193cf71e35d75db8f9616be2f5970eadff87a  docs/decisions/decision-log.md
99a40706f997bc6e0b195499ed5be8d7217dcb496e353dd7bf5cca2b55294698  docs/tasks/status.md

$ wc -l src/graph_insertion/embedding_minilm.py pyproject.toml tests/test_embedding_minilm.py tests/test_run_experiment_cli.py tests/test_strategy_registry.py scripts/README.md docs/decisions/decision-log.md docs/tasks/status.md
   148 src/graph_insertion/embedding_minilm.py
    26 pyproject.toml
   308 tests/test_embedding_minilm.py
  1312 tests/test_run_experiment_cli.py
   233 tests/test_strategy_registry.py
   200 scripts/README.md
   536 docs/decisions/decision-log.md
    99 docs/tasks/status.md
  2862 total
```

### 4.2 Three INFRA-007 Test Files Run
```text
$ .venv-ann/bin/python -m pytest tests/test_strategy_registry.py tests/test_embedding_minilm.py tests/test_run_experiment_cli.py
============================= 96 passed in 46.56s ==============================
```

### 4.3 Well-Formedness Negative Demonstrations on `/tmp` Copy
Demonstrated on an isolated `/tmp` copy that `test_shipped_pins_well_formed_and_match_pyproject` catches both malformed revision hashes and packaging version drift:

1. **39-char revision hash:**
```text
=== Demonstration 1: Revision set to 39 hex characters ===
Exit code: 1
   tests/test_embedding_minilm.py::TestMiniLMEmbedderOffline::test_shipped_pins_well_formed_and_match_pyproject FAILED [100%]
   >       assert re.fullmatch(r"^[0-9a-f]40$", minilm_mod.MODEL_REVISION_PIN) is not None
   E       AssertionError: assert None is not None
```

2. **`pyproject.toml` version mismatch:**
```text
=== Demonstration 2: pyproject.toml pin differs from constant ===
Exit code: 1
   tests/test_embedding_minilm.py::TestMiniLMEmbedderOffline::test_shipped_pins_well_formed_and_match_pyproject FAILED [100%]
   >       assert embed_extra == [
   E       AssertionError: assert ['sentence-transformers==9.9.9'] == ['sentence-transformers==6.1.0']
```

### 4.4 Final Full-Suite Pytest Run
```text
$ .venv-ann/bin/python -m pytest | tail -3
tests/test_strategy_registry.py::TestStrategyRegistry::test_stub_isolated_import_and_no_scripts_dependency_kills_pm7 PASSED [100%]

================== 684 passed, 3 skipped in 168.71s (0:02:48) ==================
```

### 4.5 Post-Edit Check
```text
$ sha256sum src/graph_insertion/embedding_minilm.py pyproject.toml tests/test_embedding_minilm.py scripts/README.md docs/decisions/decision-log.md docs/tasks/status.md
c9e5446a70d5a98f8985c738612a65417db43f5502d01e7fcb66999caf40431a  src/graph_insertion/embedding_minilm.py
b6ac3907acd1cf7764e920592fc88a03e3626eb0b96a49d2d3a785c068512e3f  pyproject.toml
403740bd7ae8a66e83540b9044005e2e827d8a7285e4b4edd9f8eb8e798e87a6  tests/test_embedding_minilm.py
1384201770f4c89b28e3ae3453ad6a485ce263df99ac5c35ef9b71a3bac8416a  scripts/README.md
b216229dc68a481c287a223e72fd955f036575d041b932d876f6ba2ad57270dc  docs/decisions/decision-log.md
f993425c565db14472bb69efca119894f635aeaf20241ca7f4d2b6b121506fa7  docs/tasks/status.md

$ wc -l src/graph_insertion/embedding_minilm.py pyproject.toml tests/test_embedding_minilm.py scripts/README.md docs/decisions/decision-log.md docs/tasks/status.md
   148 src/graph_insertion/embedding_minilm.py
    26 pyproject.toml
   333 tests/test_embedding_minilm.py
   201 scripts/README.md
   543 docs/decisions/decision-log.md
    99 docs/tasks/status.md
  1350 total
```

---

## 5. Diffs

### 5.1 `src/graph_insertion/embedding_minilm.py` (`git diff`)

```diff
diff --git i/src/graph_insertion/embedding_minilm.py w/src/graph_insertion/embedding_minilm.py
index 80331d5..213379c 100644
--- i/src/graph_insertion/embedding_minilm.py
+++ w/src/graph_insertion/embedding_minilm.py
@@ -22,15 +22,15 @@ import numpy as np
 
 
 # ---------------------------------------------------------------------------
-# Pins — MUST be set to actual values before any live run.
+# Pins — locked per [D-67] for live experiment runs.
 # If either pin is None or blank, MiniLMEmbedder refuses to initialise (fail-closed).
 # ---------------------------------------------------------------------------
 
 # Pin: sentence-transformers package version installed in .venv-ann.
-SENTENCE_TRANSFORMERS_VERSION_PIN: Optional[str] = None
+SENTENCE_TRANSFORMERS_VERSION_PIN: Optional[str] = "6.1.0"
 
 # Pin: Hugging Face model revision (commit hash) for all-MiniLM-L6-v2.
-MODEL_REVISION_PIN: Optional[str] = None
+MODEL_REVISION_PIN: Optional[str] = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
 
 MODEL_NAME: str = "all-MiniLM-L6-v2"
 MODEL_DIM: int = 384
```

### 5.2 `pyproject.toml` (`git diff`)

```diff
diff --git i/pyproject.toml w/pyproject.toml
index 7a69d4d..88a07e0 100644
--- i/pyproject.toml
+++ w/pyproject.toml
@@ -15,7 +15,7 @@ dependencies = [
 [project.optional-dependencies]
 dev = ["pytest>=9.0", "pytest-cov"]
 ann = ["faiss-cpu==1.15.1"]
-embed = ["sentence-transformers"]  # TODO(INFRA-007): pin ==<version> once supplied by Luke (see SENTENCE_TRANSFORMERS_VERSION_PIN)
+embed = ["sentence-transformers==6.1.0"]
 
 [tool.setuptools.packages.find]
 where = ["src"]
```

### 5.3 `tests/test_embedding_minilm.py` (`git diff`)

```diff
diff --git i/tests/test_embedding_minilm.py w/tests/test_embedding_minilm.py
index c6f5c30..c3b49b5 100644
--- i/tests/test_embedding_minilm.py
+++ w/tests/test_embedding_minilm.py
@@ -306,3 +306,28 @@ class TestMiniLMEmbedderOffline:
         underlying.encode = lambda texts, **kw: np.ones((len(texts), 128), dtype=np.float32)  # type: ignore[assignment]
         with pytest.raises(ValueError, match=r"Expected 2-D embedding matrix of shape \(1, 384\)"):
             emb.embed_many(["test text"])
+
+    def test_shipped_pins_well_formed_and_match_pyproject(self) -> None:
+        """Prove shipped pins in embedding_minilm are well-formed and match pyproject.toml."""
+        import re
+        import tomllib
+
+        # Revision matches 40 lowercase hex characters
+        assert isinstance(minilm_mod.MODEL_REVISION_PIN, str)
+        assert re.fullmatch(r"^[0-9a-f]{40}$", minilm_mod.MODEL_REVISION_PIN) is not None
+
+        # Version is a non-empty string without whitespace
+        assert isinstance(minilm_mod.SENTENCE_TRANSFORMERS_VERSION_PIN, str)
+        assert len(minilm_mod.SENTENCE_TRANSFORMERS_VERSION_PIN) > 0
+        assert not any(c.isspace() for c in minilm_mod.SENTENCE_TRANSFORMERS_VERSION_PIN)
+
+        # pyproject.toml embed extra matches sentence-transformers==<VERSION> exactly
+        repo_root = Path(__file__).resolve().parent.parent
+        pyproject_path = repo_root / "pyproject.toml"
+        with open(pyproject_path, "rb") as f:
+            pyproject = tomllib.load(f)
+        embed_extra = pyproject["project"]["optional-dependencies"]["embed"]
+        assert embed_extra == [
+            f"sentence-transformers=={minilm_mod.SENTENCE_TRANSFORMERS_VERSION_PIN}"
+        ]
+
```

### 5.4 `scripts/README.md` (`git diff`)

```diff
diff --git i/scripts/README.md w/scripts/README.md
index e9d62ce..c845a3c 100644
--- i/scripts/README.md
+++ w/scripts/README.md
@@ -178,6 +178,7 @@ bash tests/test_apc_bundle.sh
 - `--dry-run` (both offline and `--live --dry-run`) prints the plan and resolved output directory without creating the output directory or any file on disk.
 - On a real run (`--confirm`) into a fresh directory, `<output_dir>/strategy_config.json` (containing `{"strategy", "config", "embedder", "mode", "command_line_params"}`) is written immediately after `manifest.json` and before the first trial begins, preserving clean `git_dirty` status in `manifest.json` while remaining crash-safe before trial execution.
 - On `--resume` (with an existing sidecar) or any run into an existing directory containing `raw.jsonl`, the CLI compares `strategy`, `config`, `mode`, and the `embedder` identity block (`type`, `model_name`, `dim`, `revision`, and installed `sentence_transformers_version` for `minilm`; `type`, `dim`, and `seed` for `fake`) in `strategy_config.json` with the current configuration and refuses with exit code `1` on mismatch. Older sidecars without `sentence_transformers_version` emit a single warning for that missing key and proceed; older directories containing `raw.jsonl` without `strategy_config.json` emit a warning to `stderr` and proceed without overwriting.
+- **Live Embedding Runs & Offline Smoke Rule ([D-67])**: A one-time model download is required before any live embedding run (`pip install -e ".[embed]"`, then construct `MiniLMEmbedder()` once to cache the pinned `all-MiniLM-L6-v2` snapshot). Because default run directories (`results/<mode>_<strategy>_<slug>`) do not encode the embedder backend and the resume/existing-directory guard refuses an embedder mismatch, any offline smoke run of an embedding strategy using `--embedder fake` must pass an explicit `--output-dir` outside `results/` (for example `/tmp/...`), never the default directory that a subsequent live run will target. In addition, the OpenMP/PyTorch thread-count timing check (`docs/reports/INFRA-007-P-gemini.md` section 8.2) should be run once after the pins are in to verify single-threaded CPU embedding latency alongside FAISS.
 
 ### Primary & Sensitivity Run Table (D-35, D-46, D-47, D-55, D-58, D-59, D-62)
 
```

### 5.5 `docs/decisions/decision-log.md` (`git diff`)

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index fdaf5d8..884be09 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -534,3 +534,10 @@ Reasoning: records what was run, what the adapter did differently from the smoke
 (4) Standalone `StubNarrowingStrategy` module (`src/graph_insertion/strategies/stub.py`, `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/run_experiment.py`): moved `StubNarrowingStrategy` out of `scripts/run_experiment.py` into `src/graph_insertion/strategies/stub.py` (preserving class name, `.name == "stub_narrowing"`, and `.config()` keys), re-exported it in `scripts/run_experiment.py` and lazily in `src/graph_insertion/strategies/__init__.py`, and replaced `register_stub`/`_get_stub_cls` in `registry.py` with a direct import from `graph_insertion.strategies.stub` so library callers can instantiate `STRATEGY_FACTORIES["stub"]` when `scripts/` is not on `sys.path`.
 (5) Test and mutation gaps closed (`tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`): added unit and CLI integration tests closing all seven surviving mutants from the INFRA-007-R review (`R-M11` non-`--resume` mismatch guard when `raw.jsonl` exists; `R-M16` 1-row reshape in `embed_many` when encoder returns 1-D `(384,)`; `R-M19` offline end-to-end `--embedder minilm --confirm` execution for `embedding_threshold` and `bounded_bucket`; `R-M20` explicit `float32` cast from `float64` in `embed_many`; `R-M24` lazy `graph_insertion.strategies.STRATEGY_FACTORIES` export identity; `R-M25` wrong-dimension `ValueError` in `embed()` and `embed_many()`; `R-M26` sidecar existence before trial 1 and `git_dirty == False` in a clean git repo) plus all eight INFRA-007-P mutants (`P-M1`..`P-M8`).
 Reasoning: resolves all four should-fix items and three nits from the independent INFRA-007-R review (`docs/reports/INFRA-007-R-gemini.md`) so resume guards, embedder pins, dry-run hygiene, library packaging, and mutation coverage are airtight before live runs. Affects: `scripts/run_experiment.py`, `src/graph_insertion/embedding_minilm.py`, `src/graph_insertion/strategies/registry.py`, `src/graph_insertion/strategies/stub.py`, `src/graph_insertion/strategies/__init__.py`, `scripts/README.md`, `tests/test_strategy_registry.py`, `tests/test_embedding_minilm.py`, `tests/test_run_experiment_cli.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/INFRA-007-P-gemini.md`, INFRA-007.
+
+**[D-67]** Pinned `sentence-transformers` package version and `all-MiniLM-L6-v2` snapshot revision, well-formedness validation, and offline smoke directory isolation (INFRA-007-Q):
+(1) Locked pins (`src/graph_insertion/embedding_minilm.py`, `pyproject.toml`): Locks `SENTENCE_TRANSFORMERS_VERSION_PIN = "6.1.0"` and `MODEL_REVISION_PIN = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"` in `src/graph_insertion/embedding_minilm.py`, and pins `embed = ["sentence-transformers==6.1.0"]` under `[project.optional-dependencies]` in `pyproject.toml`. Added well-formedness verification in `tests/test_embedding_minilm.py` asserting that `MODEL_REVISION_PIN` is exactly 40 lowercase hexadecimal characters, `SENTENCE_TRANSFORMERS_VERSION_PIN` is a non-empty string without whitespace, and `pyproject.toml`'s `embed` extra parses via `tomllib` to match the version pin identically, preventing drift between the library constant and packaging configuration.
+(2) Testing convention for fail-closed pin behaviour: Fail-closed initialization guards (`MiniLMEmbedder` raising `ValueError` on unset or blank pins) must always be tested by explicitly monkeypatching `SENTENCE_TRANSFORMERS_VERSION_PIN` or `MODEL_REVISION_PIN` to `None` or blank values within the test, never by relying on shipped module defaults. All existing unit and CLI tests conform to this rule.
+(3) Offline smoke directory isolation rule: Because default run directories (`results/<mode>_<strategy>_<slug>`) do not encode the embedder type (`fake` vs `minilm`) and the resume/existing-directory guard ([D-66](2)) strictly refuses embedder mismatches against existing sidecars, any offline smoke run of an embedding strategy using `--embedder fake` must specify an explicit `--output-dir` outside `results/` (e.g. under `/tmp/...`), never the default directory that a subsequent live run will target.
+(4) Open items: While the model weights snapshot is cached locally in `.venv-ann` on Luke's machine, any other execution environment requires a one-time download (`pip install -e ".[embed]"`, followed by instantiating `MiniLMEmbedder()` once). The standalone OpenMP/PyTorch thread-timing check (`docs/reports/INFRA-007-P-gemini.md` section 8.2) remains to be run on Luke's machine prior to live embedding sweeps to measure latency before and after `faiss.omp_set_num_threads(1)`.
+Reasoning: closes the final prerequisite of INFRA-007 by locking the package version and snapshot revision pins, preventing packaging/constant drift, documenting offline smoke run directory hygiene, and setting INFRA-007 to done. Affects: `src/graph_insertion/embedding_minilm.py`, `pyproject.toml`, `tests/test_embedding_minilm.py`, `scripts/README.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/INFRA-007-Q-gemini.md`, INFRA-007.
```

### 5.6 `docs/tasks/status.md` (`git diff`)

```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index bfb65ca..ac988a0 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -57,7 +57,7 @@ Status: **in-progress** (unblocked following Phase 2 completion)
 
 | ID        | Task                                                                                                                                                                                                 | Status           | Notes / Report                                                                                                                                                                                                                                                                                                                                           |
 | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
-| INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **needs-review** | Implemented by Gemini ([D-64], report [`docs/reports/INFRA-007-gemini-strategy-wiring.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-gemini-strategy-wiring.md)); independently reviewed under INFRA-007-R (report [`docs/reports/INFRA-007-R-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-R-gemini.md), ACCEPT WITH AMENDMENTS); amendments applied under INFRA-007-P ([D-66], report [`docs/reports/INFRA-007-P-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-007-P-gemini.md), 15/15 mutants killed). Pending: Luke supplying `SENTENCE_TRANSFORMERS_VERSION_PIN` and `MODEL_REVISION_PIN` in `src/graph_insertion/embedding_minilm.py` and `pyproject.toml`, one-time model download, and the OpenMP timing check. |
+| INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **done** | Implemented by Gemini (D-64); independently reviewed under INFRA-007-R (report `docs/reports/INFRA-007-R-gemini.md`, ACCEPT WITH AMENDMENTS); amendments applied under INFRA-007-P (D-66, report `docs/reports/INFRA-007-P-gemini.md`); pins set under INFRA-007-Q (D-67, report `docs/reports/INFRA-007-Q-gemini.md`). Live embedding runs still require Luke's one-time model download and the OpenMP timing check. Accepted at APC review 2026-10-12. |
 
 ## Phase 4 — Analysis & Writeup
 
```

---

## 6. Found But Not Changed

In accordance with Section 2 and Rule 1, none of the following pre-existing items noticed during this session were modified:

1. **Unstaged modification in `docs/context/repo-tree.txt`:** `git status --short` shows ` M docs/context/repo-tree.txt` (touched outside this task when `DOC-002` was merged); left untouched and unstaged.
2. **Untracked files:** `INFRA-007-P.patch` exists at the repo root and patch files exist under `patch/`; left untouched.
3. **Pre-existing worktrees:** `git worktree list` shows task worktrees `../llm-graph-insertion-complexity-FIX-017` and `../llm-graph-insertion-complexity-gen`; neither was touched.

---

## 7. Open Questions

1. **[`Luke`]** When convenient prior to starting live embedding sweeps across the 12-run matrix, please run the standalone OpenMP / PyTorch timing snippet from Section 8.2 of `docs/reports/INFRA-007-P-gemini.md` in `.venv-ann` and record whether `faiss.omp_set_num_threads(1)` affects `MiniLMEmbedder` latency on your CPU.
