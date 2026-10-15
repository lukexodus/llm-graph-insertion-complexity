# INFRA-010: Record the FAISS/PyTorch import-order finding (D-73), correct two reports' claims, and record torch / faiss-cpu / sentence-transformers versions in `manifest.json` (D-74)

- **Task ID:** INFRA-010
- **Agent:** Gemini (Antigravity)
- **Model:** Gemini 3.8 Flash (Medium)
- **Session ID:** `1b3efbca-895e-4b87-bbbd-80fb31a3230d`
- **Independence & Session Disclosure:** The APC task specification requested a fresh session and listed `1b3efbca-895e-4b87-bbbd-80fb31a3230d` under excluded sessions. However, the human operator Luke relayed the prompt directly into this active session and instructed the agent to proceed ("continue"). Per repo operating rules and transparency standards, this session identity is explicitly disclosed and acknowledged.

---

## 1. Initial Git & Working Tree State

```text
442ca1f (HEAD -> master) INFRA-009-A: wiring tests through main(), both-order FAISS test, executed mutation table
12fd304 (origin/master, origin/HEAD, task/DOC-004-B) docs: sync repo-tree.txt for INFRA-008 and INFRA-009
577584c INFRA-009: pin PyTorch CPU threads to 1 for all embedding strategies (D-72)
2eb367b INFRA-008: record OpenMP thread-check outcome, effect material (D-71)
517c169 DOC-004-A: amend DOC-004 thesis-sync proposal with core and gated diffs
43e3225 docs: sync repo-tree.txt with root patch directory
/home/lukexodus/projects/llm-graph-insertion-complexity           442ca1f [master]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-002   e276c37 [task/DOC-002]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-002-B f141457 [task/DOC-002-B]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-004-B 12fd304 [task/DOC-004-B]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-006   67a04bc [task/DOC-006]
/home/lukexodus/projects/llm-graph-insertion-complexity-FIX-017   78b0014 [task/FIX-017]
/home/lukexodus/projects/llm-graph-insertion-complexity-gen       21d8e12 (detached HEAD)
```
Working tree on `master` was clean at commit `442ca1f`.

---

## 2. Verification of APC Findings (F-1 through F-4)

### F-1: The D-71 effect depends on import order, and real runs import `faiss` first
**Verdict:** AGREE.
**Evidence & Line Numbers:**
1. **Top-level imports in `scripts/run_experiment.py`:**
   Lines 21–81 import standard libraries (`argparse`, `os`, `sys`, `time`), dataclasses/protocols from `graph_insertion.strategy`, loader routines, and `graph_insertion.strategies.registry`. No module in top-level imports imports `torch`, `sentence_transformers`, or `faiss`.
2. **Strategy instantiation in `scripts/run_experiment.py::main()`:**
   - Line 840: `strategy_factory = lambda: strat_factory_fn(args.seed, args.k, **strategy_params)`
   - Line 845: `uninitialized_strategy = strategy_factory()`
   Executing `strategy_factory()` at line 845 invokes the registered factory function in `src/graph_insertion/strategies/registry.py`.
3. **Strategy 3 (`ann_retrieval`):**
   - In `src/graph_insertion/strategies/registry.py` line 113 (`_factory_ann_retrieval`):
     ```python
     from graph_insertion.strategies.ann_retrieval import AnnRetrievalStrategy
     ```
   - In `src/graph_insertion/strategies/ann_retrieval.py` lines 69–72:
     ```python
     try:
         import faiss
     except ImportError:
         faiss = None
     ```
   - Thus, `faiss` is imported during line 845 when the strategy instance is created.
4. **Subsequent imports of `torch` / `sentence_transformers`:**
   - At line 896 of `scripts/run_experiment.py`: `current_embedder_info = get_current_embedder_info(args, uses_embeddings, config.seed)`.
   - In `get_current_embedder_info` (lines 674–686):
     ```python
     import sentence_transformers
     ```
     This triggers sentence_transformers and PyTorch import for the first time.
   - Later, at line 1080/1083: `MiniLMEmbedder()` is instantiated, which lazily imports `sentence_transformers` and `SentenceTransformer` (line 92).
   - Therefore, in real Strategy 3 runs, **`faiss` is always imported before `torch`**.
5. **Strategies 2 and 4:**
   - Neither `src/graph_insertion/strategies/embedding_threshold.py` nor `src/graph_insertion/strategies/bounded_bucket.py` imports `faiss` (verified: 0 occurrences of `faiss`).
   - Thus, in Strategies 2 and 4, **only `torch` is imported; `faiss` is never imported**.
6. **Coupling control results:**
   - As observed in INFRA-009-A's process-isolated controls:
     - `ORDER: torch_first | CONTROL: default=4 -> control=1` (coupling observed)
     - `ORDER: faiss_first | CONTROL: default=4 -> control=4` (no coupling observed)
   - Because real Strategy 3 runs execute in the `faiss_first` order, `faiss.omp_set_num_threads(1)` does not cause PyTorch threads to drop from 4 to 1 when `torch` is initialized second.
   - Consequently, whether the thread coupling confound ever manifested in real Strategy 3 runs is unestablished.

### F-2: INFRA-009-A's claim "this proves that pinning PyTorch explicitly is necessary" is wrong
**Verdict:** AGREE.
**Evidence:** In INFRA-009-A §1, the report claimed: "The bidirectional test demonstrates that in the `torch_first` order, `faiss.omp_set_num_threads(1)` mutates PyTorch's thread count... This proves that pinning PyTorch explicitly is necessary...". This was inaccurate because the companion `faiss_first` control demonstrated that in the actual execution order used by real Strategy 3 runs, calling `faiss.omp_set_num_threads(1)` does *not* alter PyTorch's thread count. Explicit pinning is necessary as a robust policy to guarantee order-independent uniformity across strategies, but was not proven to be necessary to correct an active real-run confound.

### F-3: INFRA-009-A §5.2 claim that `manifest.json` records versions of `torch`, `sentence-transformers`, `faiss-cpu` is false
**Verdict:** AGREE.
**Evidence:**
- In `src/graph_insertion/harness.py` lines 203–205:
  ```python
  def get_library_versions(
      packages: Sequence[str] = ("networkx", "pytest", "httpx", "numpy")
  ) -> dict[str, str]:
  ```
- In `write_manifest` (line 409):
  ```python
  "libraries": get_library_versions(),
  ```
- No arguments are passed to `get_library_versions()`. Therefore, `manifest.json`'s `libraries` dictionary contains only `networkx`, `pytest`, `httpx`, and `numpy`.
- `torch` (`2.14.1+cu130` in `.venv-ann`) is not pinned in `pyproject.toml` (which only specifies `sentence-transformers==6.1.0` and `faiss-cpu==1.15.1`) and was recorded nowhere in `manifest.json`.

### F-4: INFRA-009-A's mutation table reported failure messages not printed by its runner script
**Verdict:** AGREE.
**Evidence:** The runner bash script executed during INFRA-009-A captured only return codes (`rc`) from `pytest` invocations and printed `KILLED (rc=1)`. The detailed traceback assertion snippets presented in the report table were reconstructed post-hoc rather than streamed verbatim from the mutant test runner, and no baseline control execution was run in that temporary clone prior to mutant application.

---

## 3. Part A Documentation Changes

### 3.1 Amendment to `docs/reports/INFRA-008-gemini-openmp-timing-check.md`
1. Added amendment header under report title:
   `§A-2 conclusion amended under INFRA-010 (2026-10-15).`
2. Replaced the conclusion paragraph in Section 4 with:
   > Both `faiss_cpu.libs/libgomp-*.so` and `torch/lib/libgomp.so.1` are mapped into process memory. `faiss.omp_set_num_threads(1)` lowered `torch.get_num_threads()` from 4 to 1 in the measured import order (`torch` then `faiss`); INFRA-009-A's controls show it did not in the reverse order. The mechanism is unidentified. See D-73.

### 3.2 Decision Entry `[D-73]` Appended to `docs/decisions/decision-log.md`
Appended `**[D-73]**` recording the import-order finding, preserving [D-71] as the outcome of the pre-fixed protocol, retaining the [D-72] single-thread pin as policy ensuring order-independent uniformity across Strategies 2, 3, and 4, noting the prospective exploratory timing check, and framing the thesis limitation.

### 3.3 Task Tracker Update in `docs/tasks/status.md`
1. Appended note to `INFRA-009` row: "Mutation results to be independently re-checked by Luke's script; some report claims corrected under INFRA-010 (D-73)."
2. Added `INFRA-010` row with status `**needs-review**`.

---

## 4. Errata for `docs/reports/INFRA-009-A-gemini-test-gaps-and-mutations.md`

1. **§1 (Necessity of Pinning Claim):**
   - *Original claim:* "This proves that pinning PyTorch explicitly is necessary..."
   - *Correction:* The bidirectional test proved that thread coupling occurs under the `torch`-first import order, but also proved that under the `faiss`-first order, PyTorch threads remained unaffected (`4 -> 4`). Because real runs execute in the `faiss`-first order, the pin is not proven to be necessary to correct an active in-run confound, but is justified as an order-independent policy ensuring uniformity.
2. **§5.2 (Manifest Package Version Recording Claim):**
   - *Original claim:* "The manifest records the installed library package versions (`torch`, `sentence-transformers`, `faiss-cpu`)."
   - *Correction:* False. `get_library_versions()` defaulted strictly to `("networkx", "pytest", "httpx", "numpy")`. `torch` and `faiss-cpu` were not recorded in `manifest.json`. `sentence-transformers` was recorded only in the `strategy_config.json` sidecar.
3. **§4 & §5 (Mutation Table Failure Verbatim Attribution):**
   - *Original presentation:* The table presented specific assertion messages for mutants M1 through M11.
   - *Correction:* The script executed in the session logged only `KILLED (rc=1)` without capturing and printing specific test assertion failure output streams, lacked an automated baseline control verification, and M10 survived initially before a test was modified. Those specific assertion lines are superseded by Luke's independent mutation run via `~/Downloads/infra009_mutation_check.py`.

---

## 5. Found But Not Changed
- `scripts/run_experiment.py`: Maintained strictly read-only; no code changes.
- `src/graph_insertion/strategies/*`: All strategies remained read-only.
- `src/graph_insertion/cpu_threads.py`: Unmodified in Part A.
