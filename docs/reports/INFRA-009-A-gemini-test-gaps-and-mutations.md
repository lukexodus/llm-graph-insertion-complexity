# INFRA-009-A — Close Test Gaps in CPU-Thread Pin and Executed Mutation Table

- **Task ID:** INFRA-009-A
- **Agent / Model:** Gemini (Antigravity, Gemini 3.8 Flash (Medium))
- **Conversation / Session ID:** `1b3efbca-895e-4b87-bbbd-80fb31a3230d` (Note: same active interactive agent thread, continuing directly from INFRA-009 with freshly invoked test/mutation processes).
- **Date:** 2026-10-15 12:25 PH (UTC+8)

---

## 1. Git State & Independence Checks

### Git History and Commit Lineage
- `git log --oneline -6`:
  ```text
  12fd304 (HEAD -> master) docs: sync repo-tree.txt for INFRA-008 and INFRA-009
  577584c INFRA-009: pin PyTorch CPU threads to 1 for all embedding strategies (D-72)
  2eb367b INFRA-008: record OpenMP thread-check outcome, effect material (D-71)
  517c169 (origin/master, origin/HEAD) DOC-004-A: amend DOC-004 thesis-sync proposal with core and gated diffs
  43e3225 docs: sync repo-tree.txt with root patch directory
  dcc187c docs: regenerate repo-tree.txt for DOC-004..DOC-006
  ```
  *(Note on commit `12fd304`: immediately after commit `577584c` in the INFRA-009 session, running the bundle tool generated a housekeeping commit `12fd304` to sync `docs/context/repo-tree.txt` on master. All commits are intact).*

- `git worktree list`:
  ```text
  /home/lukexodus/projects/llm-graph-insertion-complexity           12fd304 [master]
  /home/lukexodus/projects/llm-graph-insertion-complexity-DOC-002   e276c37 [task/DOC-002]
  /home/lukexodus/projects/llm-graph-insertion-complexity-DOC-002-B f141457 [task/DOC-002-B]
  /home/lukexodus/projects/llm-graph-insertion-complexity-DOC-006   67a04bc [task/DOC-006]
  /home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017   78b0014 [task/FIX-017]
  /home/lukexodus/projects/llm-graph-insertion-complexity-gen       21d8e12 (detached HEAD)
  ```
- `git status --short`: clean before task edits.

---

## 2. Verification of APC Findings (F-1 to F-4)

- **F-1 (main() wiring untested): AGREE.** The 5 tests added in INFRA-009 only exercised the helper, the standalone ordering script, and the sidecar/resume helper functions in isolation. None invoked `main()`. Removing or misplacing the pin in `scripts/run_experiment.py` would not fail any test.
- **F-2 (mutation table unexecuted): AGREE.** The table in the INFRA-009 report outlined expected theoretical behavior rather than pasting real command outputs from mutated runs on `/tmp` copies.
- **F-3 (test_ordering_with_faiss weakness): AGREE.** In the original test, `try...except ImportError: sys.exit(0)` caused the subprocess to exit 0 without printing the invariant line, triggering an assertion failure rather than skipping when dependencies were absent. Furthermore, it only tested `torch` imported before `faiss`, not the reverse order.
- **F-4 (overstated docstring mechanism): AGREE.** Describing the mechanism as "due to a shared OpenMP runtime thread setting across the process" is an unverified assertion when two separate `libgomp` dynamic shared objects are loaded in process memory.

---

## 3. Test Changes & Implemented Fixes

### 3.1 Main Wiring Tests (`tests/test_run_experiment_cli.py`)
Added class `TestCPUThreadsMainWiring` containing 4 comprehensive test methods:
1. `test_minilm_real_execution_calls_pin_exactly_once_after_construction`:
   - Spies on `MiniLMEmbedder.__init__` and `pin_cpu_threads`.
   - Asserts execution order: `event_order == ["minilm_init", "pin_cpu_threads"]`.
   - Spies on `pin_cpu_threads` returning a distinct `torch_threads: 100` and asserts that `embedder_info` and the written `strategy_config.json` sidecar record `cpu_threads: 1` and `torch_threads: 100` (killing M1, M5, M9, M10).
2. `test_pin_runtime_error_aborts_main_with_exit_1`:
   - Simulates `RuntimeError` raised by `pin_cpu_threads`.
   - Verifies `main()` returns 1, prints `ERROR: simulated read-back mismatch`, and halts before invoking the harness (killing M4, M11).
3. `test_fake_embedder_never_calls_pin` (parametrized over `dry_run` False and True):
   - Verifies `--embedder fake` (both real execution with `--confirm` and `--dry-run`) never calls `pin_cpu_threads` (killing M2).
4. `test_minilm_dry_run_never_calls_pin`:
   - Verifies `--embedder minilm --dry-run` prints pre-flight estimate and exits 0 without calling `pin_cpu_threads`.

### 3.2 Ordering Test Over Both Import Orders (`tests/test_cpu_threads.py`)
- Added `pytest.importorskip("torch")` and `pytest.importorskip("faiss")`.
- Parametrized over `order` in `["torch_first", "faiss_first"]`.
- In both orders, asserts that after `pin_cpu_threads(1)` followed by `faiss.omp_set_num_threads(1)`, `torch.get_num_threads() == 1` holds invariant.
- Informational control lines captured and printed:
  - **`torch_first`:** `ORDER: torch_first | CONTROL: default=4 -> control=1 | INVARIANT: after=1`
  - **`faiss_first`:** `ORDER: faiss_first | CONTROL: default=4 -> control=4 | INVARIANT: after=1`
  - *Crucial Finding:* When `torch` is imported before `faiss`, `faiss.omp_set_num_threads(1)` mutates PyTorch's thread count (`default=4 -> control=1`). But when `faiss` is imported before `torch`, `faiss.omp_set_num_threads(1)` called before PyTorch initialization does *not* lower PyTorch's default thread count (`default=4 -> control=4`)! However, calling `pin_cpu_threads(1)` guarantees `after=1` in both orders. This proves that pinning PyTorch explicitly is necessary and eliminates import-order sensitivity.

### 3.3 Docstring Rewording (`src/graph_insertion/cpu_threads.py`)
Updated docstring to state observed facts neutrally:
```python
"""cpu_threads.py — INFRA-009 / D-72
==================================
Deterministic CPU thread-count pinning for PyTorch inference.

In the INFRA-008 measurement ([D-71]), calling faiss.omp_set_num_threads(1)
was observed to lower torch.get_num_threads() from default (4 on the reference host)
down to 1. The precise underlying mechanism was not identified (inspection of
process mappings showed two distinct OpenMP library files loaded: one bundled with
faiss-cpu and one with PyTorch). Under [D-72], PyTorch intra-op CPU threads are
explicitly pinned to CPU_THREAD_PIN (1) for every execution that constructs
MiniLMEmbedder (covering Strategies 2, 3, and 4), eliminating cross-strategy
embedding latency bias while keeping FAISS single-threaded ([D-47]) regardless of
how OpenMP symbols or runtimes interact.
"""
```

---

## 4. Executed Mutation Table

Executed across isolated `/tmp` workspace copies using Python subprocesses invoking `.venv-ann/bin/pytest`.

Session: `1b3efbca-895e-4b87-bbbd-80fb31a3230d`

| Mutant ID | Description | File / Line Modified | Test Command Run | Result |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | Pin call deleted in `main()` | `scripts/run_experiment.py`: replaced pin call with dummy dictionary | `pytest tests/test_run_experiment_cli.py -k 'test_minilm_real_execution_calls_pin_exactly_once_after_construction'` | **KILLED** (rc=1, `assert event_order == ['minilm_init', 'pin_cpu_threads']` failed) |
| **M2** | Pin called on fake path | `scripts/run_experiment.py`: added `pin_cpu_threads(1)` in fake embedder branch | `pytest tests/test_run_experiment_cli.py -k 'test_fake_embedder_never_calls_pin'` | **KILLED** (rc=1, `assert pin_called == []` failed) |
| **M3** | `CPU_THREAD_PIN` changed to 2 | `src/graph_insertion/cpu_threads.py`: `CPU_THREAD_PIN = 2` | `pytest tests/test_run_experiment_cli.py -k 'test_cpu_threads_in_minilm_sidecar_and_resume_guard'` | **KILLED** (rc=1, `assert info['cpu_threads'] == 1` failed: 2 != 1) |
| **M4** | Read-back check removed in `pin_cpu_threads` | `src/graph_insertion/cpu_threads.py`: removed `if observed != n: raise` | `pytest tests/test_cpu_threads.py -k 'test_pin_cpu_threads_raises_on_mismatch'` | **KILLED** (rc=1, did not raise RuntimeError) |
| **M5** | Pin moved before construction in `main()` | `scripts/run_experiment.py`: called pin before `MiniLMEmbedder()` | `pytest tests/test_run_experiment_cli.py -k 'test_minilm_real_execution_calls_pin_exactly_once_after_construction'` | **KILLED** (rc=1, `event_order == ['pin_cpu_threads', 'minilm_init']` failed) |
| **M6** | `cpu_threads` missing from sidecar | `scripts/run_experiment.py`: omitted `"cpu_threads": CPU_THREAD_PIN` | `pytest tests/test_run_experiment_cli.py -k 'test_cpu_threads_in_minilm_sidecar_and_resume_guard'` | **KILLED** (rc=1, `KeyError: 'cpu_threads'` in info) |
| **M7** | Guard compares `cpu_threads` unconditionally | `scripts/run_experiment.py`: omitted `if "cpu_threads" in stored_embedder` | `pytest tests/test_run_experiment_cli.py -k 'test_cpu_threads_in_minilm_sidecar_and_resume_guard'` | **KILLED** (rc=1, failed legacy sidecar acceptance) |
| **M8** | Guard never compares `cpu_threads` | `scripts/run_experiment.py`: replaced mismatch check with `pass` | `pytest tests/test_run_experiment_cli.py -k 'test_cpu_threads_in_minilm_sidecar_and_resume_guard'` | **KILLED** (rc=1, allowed mismatch payload rc=0 instead of rc=1) |
| **M9** | Pin called twice in `main()` | `scripts/run_experiment.py`: duplicated `pin_cpu_threads(CPU_THREAD_PIN)` | `pytest tests/test_run_experiment_cli.py -k 'test_minilm_real_execution_calls_pin_exactly_once_after_construction'` | **KILLED** (rc=1, `event_order` had 2 pin calls) |
| **M10** | `torch_threads` taken from requested value instead of read-back | `scripts/run_experiment.py`: passed `pin_result["requested"]` to embedder info | `pytest tests/test_run_experiment_cli.py -k 'test_minilm_real_execution_calls_pin_exactly_once_after_construction'` | **KILLED** (rc=1, `assert sidecar_emb['torch_threads'] == 100` failed: 1 != 100) |
| **M11** | `RuntimeError` removed from `except` tuple in `main()` | `scripts/run_experiment.py`: `except (ImportError, ValueError) as err:` | `pytest tests/test_run_experiment_cli.py -k 'test_pin_runtime_error_aborts_main_with_exit_1'` | **KILLED** (rc=1, unhandled RuntimeError propagated traceback) |

---

## 5. Read-Only Checks & Static Observations

### 5.1 RuntimeError in MiniLM Initialization
- Inspection of [`src/graph_insertion/embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py) `__init__` lines 70–113 reveals that `MiniLMEmbedder` raises `ValueError` for unset/blank version pins or mismatched model revision pins, and `ImportError` if `sentence_transformers` is missing.
- It does not explicitly raise `RuntimeError`.
- Prior to INFRA-009, `main()` caught `except (ImportError, ValueError) as err:`. Adding `RuntimeError` to that tuple catches read-back verification failures from `pin_cpu_threads()` and does not alter the handling of any existing `MiniLMEmbedder` validation check.

### 5.2 Destination of Embedder Info in Manifest
- Reading `harness.write_manifest()` in [`src/graph_insertion/harness.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/harness.py) lines 388–429 reveals that `write_manifest` does **not** receive `embedder_info` directly. Instead, `write_manifest` captures:
  - `libraries`: versions of installed packages via `importlib.metadata`.
  - `strategy_config`: the strategy's `config()` dictionary.
  - `model_info`: LLM client parameters.
- Consequently, `embedder_info` (which includes `"cpu_threads": 1` and `"torch_threads": 1`) lands in `<output_dir>/strategy_config.json` (the sidecar written by `run_experiment.py`), while `manifest.json` records the installed library package versions (`torch`, `sentence-transformers`, `faiss-cpu`). This matches the intended separation of responsibilities without modifying `harness.py`.

### 5.3 Provenance of torch 2.10.0 and faiss-cpu 1.11.0 in INFRA-008 Header
- Git log inspection (`git log -S "2.10.0"`) shows that `2.10.0` and `1.11.0` never appeared in any command output in repository history.
- The INFRA-008 draft was drafted manually without running a command for package versions, and those placeholder version numbers were written from memory/assumption.
- Crucially, `pyproject.toml` pins `faiss-cpu==1.15.1` and `sentence-transformers==6.1.0`, but **does NOT pin `torch`** (it specifies only `torch>=2.0.0` or pulls it transitively). On Luke's reference host, `.venv-ann` has `torch==2.14.1+cu130`.

### 5.4 Correction to INFRA-008 Report §A-2 Conclusion
The INFRA-008 report §A-2 currently states:
> *"While multiple dynamic OpenMP library files are mapped, global OpenMP runtime thread control symbols or vendor interop resolve to a shared thread setting across the process."*

This sentence should become:
> *"While both `faiss_cpu.libs/libgomp-*.so` and `torch/lib/libgomp.so.1` are mapped into process memory, calling `faiss.omp_set_num_threads(1)` changes `torch.get_num_threads()` in the measured import order (`torch` then `faiss`); the precise inter-library symbol resolution mechanism remains unidentified, but uniform pinning ensures behavior is independent of it."*

---

## 6. Test Suite Execution & Counts

- **Full test suite execution (`.venv-ann/bin/pytest -q | tail -3`):**
  ```text
  tests/test_strategy_registry.py ..........                               [100%]

  ================== 695 passed, 3 skipped in 152.42s (0:02:32) ==================
  ```
  *(Baseline after INFRA-009 was 689 passed, 3 skipped; +6 new tests added: 1 ordering test variant + 5 main() wiring tests, all passing, 0 regressions, 3 skipped tests unchanged for uninstalled FAISS mocks).*
