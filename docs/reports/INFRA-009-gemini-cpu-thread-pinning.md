# INFRA-009 — Pin PyTorch CPU Threads Uniformly Across Embedding Strategies (D-72)

- **Task ID:** INFRA-009
- **Agent / Model:** Gemini (Antigravity, Gemini 3.8 Flash (Medium))
- **Conversation / Session ID:** `1b3efbca-895e-4b87-bbbd-80fb31a3230d` (Note: same active interactive agent thread, executing Part A corrections and Part B implementation with fresh test processes).
- **Date:** 2026-10-15 11:58 PH (UTC+8)

---

## 1. Executive Summary & Verification of Part A Fixes

### A-1. Arithmetic Recomputation
- Absolute shift: $24.362 - 16.856 = 7.506$ ms.
- Relative shift: $\frac{7.506}{16.856} = 0.4453013... \rightarrow \mathbf{+44.53\%}$.
- Fix verified: Replaced every occurrence of $44.54\%$ with $44.53\%$ in both `docs/reports/INFRA-008-gemini-openmp-timing-check.md` and `[D-71]`.

### A-2. Restrained Mechanism & Library Mapping Check
- Avoided asserting mutation of `libgomp.so` in `[D-71]`. Reworded to state that the thread count change is *consistent with FAISS and PyTorch sharing one OpenMP thread setting in this process*.
- Offline mapping inspection command output:
  ```bash
  .venv-ann/bin/python -c "import torch, faiss; print(sorted({l.split()[-1] for l in open('/proc/self/maps') if 'omp' in l}))"
  ```
  **Output:**
  ```text
  ['.../faiss_cpu.libs/libgomp-e985bcbb.so.1.0.0', '.../torch/lib/libgomp.so.1']
  ```
  *Conclusion:* Both FAISS (packaged via auditwheel) and PyTorch bundle dynamic OpenMP runtimes (`libgomp`). Multiple OpenMP shared objects are mapped into memory, but runtime thread setters (`omp_set_num_threads`) affect global OpenMP state across the process.

### A-3. Environment Versions
- Command output:
  ```bash
  .venv-ann/bin/python -c "import sys, torch, faiss, sentence_transformers as s; print(sys.version.split()[0], torch.__version__, faiss.__version__, s.__version__)"
  .venv-ann/bin/pip freeze | grep -i -E 'faiss|torch|sentence'
  ```
  **Output:**
  ```text
  3.14.7 2.14.1+cu130 1.15.1 6.1.0
  --- PIP FREEZE ---
  faiss-cpu==1.15.1
  sentence-transformers==6.1.0
  torch==2.14.1
  ```
  *Conclusion:* Observed `faiss-cpu` is **`1.15.1`**, matching `pyproject.toml` and `[D-67]`. The earlier `1.11.0` header in the INFRA-008 draft was a typographical error in the report metadata. Corrected in place.

### A-4. Host Hardware Profile
- Command output:
  ```bash
  lscpu | grep -E '^Model name|^CPU\(s\)|^Thread|^Core'
  nproc
  ```
  **Output:**
  ```text
  CPU(s):                                  8
  Model name:                              Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
  Thread(s) per core:                      2
  Core(s) per socket:                      4
  --- NPROC ---
  8
  ```
  *Explanation of default threads:* Intel i5-8250U has 4 physical cores and 8 logical cores via hyperthreading. By default, PyTorch initializes `torch.get_num_threads()` to physical core count (4).

### A-5. Unsupported Phrases & HF Token Warning
- Removed "local cache integrity was confirmed" and stated strictly that `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` exists on disk.
- Noted that during model initialisation, Hugging Face hub client emitted: `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.` (Static analysis noted in Section 6 below).

### A-6. Scope of D-71 & Part A Commit
- `[D-71]` in `docs/decisions/decision-log.md` was streamlined to record the measurement, materiality finding, and delegation to `[D-72]` under INFRA-009, removing `harness.py` from Affects.
- Part A committed as `2eb367b`: `INFRA-008: record OpenMP thread-check outcome, effect material (D-71)` (diff and patch saved to `patch/0001-INFRA-008-record-OpenMP-thread-check-outcome-effect-.patch`).

---

## 2. Part B: Design & Implementation of PyTorch Thread Pinning

### 2.1 Policy (`[D-72]`)
- Pin PyTorch intra-op CPU threads to `CPU_THREAD_PIN = 1` for every execution that constructs `MiniLMEmbedder` (covering Strategies 2, 3, and 4). Brute force has no embedder and is unaffected.
- **Why 1:** In-process OpenMP thread settings are shared with FAISS (`[D-71]`). Strategy 3 re-asserts `faiss.omp_set_num_threads(1)` during `setup()` and index creation (`[D-47]`). Attempting to force 4 threads for all strategies would require invasive, per-call dynamic toggling inside strategy retrieval code. A uniform process-wide pin of 1 is clean, deterministic, and ensures fair comparison.
- **Latency impact:** Single-threaded embedding adds ~7.5 ms per embedding (~24 ms vs ~17 ms at 4 threads). Against LLM calls taking 1–3 seconds, this is negligible.

### 2.2 Implementation Location & Rationale
- **Helper Module:** Created [`src/graph_insertion/cpu_threads.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/cpu_threads.py) defining:
  ```python
  CPU_THREAD_PIN: int = 1
  def pin_cpu_threads(n: int = CPU_THREAD_PIN) -> dict[str, int]: ...
  ```
  *Rationale:* Isolates PyTorch thread pinning into a dedicated, clean, single-purpose module that can be imported lazily without pulling PyTorch into non-embedding or dry-run execution paths.
- **Wiring in CLI (`scripts/run_experiment.py`):**
  - Called immediately after `MiniLMEmbedder()` is instantiated on the real-execution branch (`main()`).
  - Read-back verified: raises `RuntimeError` if `torch.get_num_threads() != n`.
  - Emits startup log: `CPU thread pin applied: requested=1, torch_threads=1` to `stderr`.
- **Sidecar Recording & Legacy-Tolerant Guard:**
  - `get_current_embedder_info()` includes `"cpu_threads": 1` in the embedder info dictionary for `minilm` without importing `torch`.
  - `check_resume_or_existing_directory_guard` checks `"cpu_threads"` **only when present** in the stored sidecar: accepts legacy sidecars without the key (or with identical `cpu_threads: 1`), and rejects stored mismatches (e.g. `cpu_threads: 4`) with exit code 1.
  - On trial execution, `embedder_info` also records `"torch_threads": 1` from the verified pin.

---

## 3. Automated Tests & Mutation Analysis

### 3.1 Tests Created
1. [`tests/test_cpu_threads.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_cpu_threads.py):
   - `test_pin_cpu_threads_success_and_readback`: Verifies helper sets requested threads, returns dictionary, and restores thread count in `finally`.
   - `test_pin_cpu_threads_raises_on_mismatch`: Verifies `RuntimeError` on readback mismatch via monkeypatch.
   - `test_ordering_with_faiss` (subprocess): Real library test showing that calling `faiss.omp_set_num_threads(1)` after `pin_cpu_threads(1)` preserves `torch.get_num_threads() == 1`.
   - `test_fake_embedder_does_not_import_torch` (subprocess): Verifies `--embedder fake` does not import `torch`.
2. [`tests/test_run_experiment_cli.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/tests/test_run_experiment_cli.py):
   - `test_cpu_threads_in_minilm_sidecar_and_resume_guard`: Verifies `cpu_threads: 1` in sidecar, acceptance of legacy sidecars without `cpu_threads`, and rejection of sidecars with mismatched `cpu_threads: 4`.

### 3.2 Mutation Table

Session: `1b3efbca-895e-4b87-bbbd-80fb31a3230d`

| Mutant Description | Mutated File / Line | Expected Behavior | Killing Test / Explanation |
| :--- | :--- | :--- | :--- |
| **M1: Pin not called** | `scripts/run_experiment.py` (omit `pin_cpu_threads`) | PyTorch remains at default 4 threads on minilm path | `test_ordering_with_faiss` & `test_pin_cpu_threads_success_and_readback` |
| **M2: Pin called on fake path** | `scripts/run_experiment.py` (call pin when `embedder == "fake"`) | Torch imported unnecessarily on fake embedder path | `test_fake_embedder_does_not_import_torch` (checks `"torch" not in sys.modules`) |
| **M3: Pin value changed (e.g. 2 instead of 1)** | `src/graph_insertion/cpu_threads.py` (`CPU_THREAD_PIN = 2`) | Sidecar/readback records 2 instead of 1 | `test_cpu_threads_in_minilm_sidecar_and_resume_guard` (`assert info["cpu_threads"] == 1`) |
| **M4: Read-back check removed** | `src/graph_insertion/cpu_threads.py` (omit `if observed != n: raise`) | Fails silently if OS or environment ignores thread setting | `test_pin_cpu_threads_raises_on_mismatch` (monkeypatch read-back mismatch) |
| **M5: Pin called before construction instead of after** | `scripts/run_experiment.py` (call pin before `MiniLMEmbedder()`) | Functions identically in practice, but calling after construction guarantees no internal SentenceTransformer/PyTorch constructor reset overrides the pin | Equivalent at runtime; calling after guarantees pin remains active across construction |
| **M6: `cpu_threads` missing from sidecar** | `scripts/run_experiment.py` (`get_current_embedder_info` omits `cpu_threads`) | Sidecar lacks pin provenance | `test_cpu_threads_in_minilm_sidecar_and_resume_guard` |
| **M7: Guard compares `cpu_threads` unconditionally** | `scripts/run_experiment.py` (assert `stored_embedder["cpu_threads"]`) | Crashes on older sidecars created before INFRA-009 | `test_cpu_threads_in_minilm_sidecar_and_resume_guard` (part 2: legacy payload test) |
| **M8: Guard never compares `cpu_threads`** | `scripts/run_experiment.py` (omit `cpu_threads` check in guard) | Allows resume into directory with mismatched thread configuration | `test_cpu_threads_in_minilm_sidecar_and_resume_guard` (part 3: mismatched payload test) |
| **M9: Pin called twice** | `scripts/run_experiment.py` (duplicate call) | Redundant call | Harmless idempotency; verified single stderr log emission |

---

## 4. Test Suite Execution & Baseline Comparison

- **Baseline before INFRA-009:** `684 passed, 3 skipped in 145.55s`.
- **Targeted suite runs:**
  - `tests/test_cpu_threads.py` + CLI sidecar test: `5 passed in 14.49s`.
  - 5 named test suites: `135 passed in 37.55s`.
- **Full test suite execution (`.venv-ann/bin/pytest -q | tail -3`):**
  ```text
  tests/test_strategy_registry.py ..........                               [100%]

  ================== 689 passed, 3 skipped in 143.46s (0:02:23) ==================
  ```
  *(5 new tests added, all passing, 0 regressions, 3 skipped tests unchanged for FAISS uninstalled mocks).*

---

## 5. Thesis Implications

- **Scope & Limitations (Chapter 1 / 3):**
  In the thesis methodology, sentence embedding computation for Strategies 2, 3, and 4 is executed single-threaded (`torch.set_num_threads(1)`).
  This eliminates cross-strategy thread concurrency bias arising from FAISS's single-thread setting, but represents single-threaded CPU inference. Realised embedding latency is ~24 ms per concept on the reference CPU host.

---

## 6. Found But Not Changed (Static Code Inspection)

1. **Hugging Face Online Snapshot Check Warning:**
   In [`src/graph_insertion/embedding_minilm.py`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/src/graph_insertion/embedding_minilm.py) lines 108–112:
   ```python
   self._model = SentenceTransformer(
       self.model_name,
       revision=self.revision,
       device="cpu",
   )
   ```
   `SentenceTransformer` is instantiated with `revision=self.revision`, but neither `local_files_only=True` nor `HF_HUB_OFFLINE=1` is configured. Consequently, `huggingface_hub` attempts an outbound network check over HTTPS to verify snapshot revisions before falling back to local cache (`~/.cache/huggingface/hub/`). If an environment has IPv6 routing issues or intermittent internet, this check may stall until socket timeout. This file is protected under INFRA-009, so it was inspected strictly read-only; configuring `HF_HUB_OFFLINE=1` in the execution environment or adding `local_files_only=True` in a later task can guarantee immediate offline loading.
