# INFRA-011 Report: Close Out INFRA-009, INFRA-009-A, and INFRA-010; Record D-76; Correct README Thread-Pin Wording; Update RUN-001

- **Task ID:** INFRA-011
- **Agent Name:** Gemini (Antigravity)
- **Exact Model Label:** Gemini 3.8 Flash (Medium)
- **Session ID:** `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
- **Branch:** `task/INFRA-011`
- **Worktree:** `/home/lukexodus/projects/llm-graph-insertion-complexity-INFRA-011`
- **Base Commit:** `0b5198a` (docs: sync repo-tree.txt for INFRA-010 and DOC-004-B)
- **Date:** 2026-10-15

---

## 1. Independence & Exclusions Check

- **Assigned Session:** `2ebf9668-92a8-4bf2-a6c1-13caeb3dbfa6`
- **Excluded Sessions Check:**
  - `1b3efbca-895e-4b87-bbbd-80fb31a3230d`: **PASS** (does not match)
  - `512aecca-d185-438b-b8e7-d6dba3b507fb`: **PASS** (does not match)
  - `098dcdd4-c444-4fcd-af8f-1b2054b31802`: **PASS** (does not match)
  - Prefixes `455d24de`, `b8ab4203`, `900404ed`, `2b098fc9`, `ede0cb54`: **PASS** (session starts with `2ebf9668`)
- **Status:** Clean, independent fresh session verified.

---

## 2. Preconditions (Raw Command Outputs)

### Command 1: `git log --oneline -3`
```text
0b5198a (HEAD -> task/INFRA-011, origin/master, origin/HEAD, task/DOC-004-C, master) docs: sync repo-tree.txt for INFRA-010 and DOC-004-B
2a32c21 (task/DOC-004-B) DOC-004-B: land amended core thesis diff and record D-75
1591d52 INFRA-010 (B): record torch, faiss-cpu and sentence-transformers versions in manifest libraries (D-74)
```

### Command 2: `grep -c '\*\*\[D-76\]\*\*' docs/decisions/decision-log.md`
```text
0
```

### Command 3: `grep -c 'Because FAISS and PyTorch share an OpenMP thread setting in-process, `embed_s` in Strategy 3 would run single-threaded while Strategies 2 and 4 would run on 4 threads.' scripts/README.md`
```text
1
```

### Command 4: `grep -c 'ensuring completely fair, unconfounded cross-strategy latency comparisons.' scripts/README.md`
```text
1
```

---

## 3. Actions Executed

1. **`docs/decisions/decision-log.md` (Step A):**
   - Appended `[D-76]` preceded by a single blank line, matching the style of `[D-73]` with no test counts.
   - Text records closure of INFRA-009, INFRA-009-A, and INFRA-010 based on executed mutation evidence (`infra009_mutation_check.py` on HEAD `1591d52`), import order confirmation, erratum to D-74(3), torch pin closure, session independence record, and plumbing pilot execution.

2. **`docs/tasks/status.md` (Step B):**
   - **INFRA-009:** Status changed to `**done**`. Appended sentence to notes: `"Accepted on executed mutation evidence ([D-76])."`
   - **INFRA-010:** Status changed to `**done**`. Appended sentence to notes: `"Accepted; D-74(3) corrected by [D-76]."`
   - **RUN-001:** Status changed to `**in-progress**`. Removed `"Blocked on the 290-call pilot. "`. Appended sentence to notes: `"Plumbing pilot completed 2026-10-15, output excluded ([D-76](6)); the 24 runs have not started."`
   - No other rows modified.

3. **`scripts/README.md` (Step C):**
   - Replaced `OLD1` ("Because FAISS and PyTorch share an OpenMP thread setting in-process, `embed_s` in Strategy 3 would run single-threaded while Strategies 2 and 4 would run on 4 threads.") with `NEW1` ("In the torch-first import order FAISS and PyTorch were observed to share one OpenMP thread setting ([D-71]); in the faiss-first order that real Strategy 3 runs use, no such coupling was observed ([D-73]). Whether a cross-strategy latency confound arose in real runs is unestablished.").
   - Replaced `OLD2` ("ensuring completely fair, unconfounded cross-strategy latency comparisons.") with `NEW2` ("so embedding times are uniform across strategies and independent of import order (single-threaded by protocol).").

4. **Dedicated Worktree:**
   - Followed `AGENTS.md` worktree isolation rules: created `../llm-graph-insertion-complexity-INFRA-011` on branch `task/INFRA-011` from clean master checkout. Worktree left intact for Luke.

---

## 4. Verbatim Git Diffs

### A. `docs/decisions/decision-log.md`
```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 1692833..0080ea0 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -620,3 +620,12 @@ Reasoning: records installed versions of torch, faiss-cpu, and sentence-transfor
 (5) Single-threaded embedding ([D-72](3)): Section 3.2.3 states that PyTorch is restricted to one thread for every embedding-based strategy. This sentence stands only if INFRA-009 is accepted; if it is rejected or changed, the sentence is corrected by a later entry.
 (6) Clarification of [D-62](3), without editing it: "mean segment size approximately 7" is an a-priori expectation from the bounds [5, 10], not a measured value; the thesis states only that a shortlist cannot exceed s_max and that realised counts are measured by the runs.
 Reasoning: removes the contradiction between the research question and the single-insertion protocol fixed by [D-68](1), removes statements with no source or no measurement (the kind [D-70](1) withdrew for Strategy 2), and keeps literature-dependent claims out of the thesis until the paper has been read. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/reports/DOC-004-B-thesis-final-core.diff`, `docs/reports/DOC-004-B-thesis-final-gated.diff`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, RQ4 (Section 1.2), Objective 4 (Section 1.3).
+
+**[D-76]** Closure of INFRA-009, INFRA-009-A and INFRA-010; erratum to D-74(3); plumbing pilot recorded (INFRA-011):
+(1) Mutation evidence: infra009_mutation_check.py was run in Luke's repository on 2026-10-15 at HEAD 1591d52 and the output relayed by Luke. The baseline control passed, 12 of 12 mutants were KILLED with failing assertion lines, and the control lines were `torch_first: default=4 -> control=1` and `faiss_first: default=4 -> control=4`, with 1 after the pin in both orders. The script's clone command was run with an added --no-hardlinks flag. This evidence supersedes the mutation table in the INFRA-009-A report. INFRA-009 and INFRA-009-A are accepted, which also satisfies the condition stated in D-75(5).
+(2) Import order confirmed: importing scripts/run_experiment.py loads neither torch nor faiss; ann_retrieval.py line 70 is the only faiss import under strategies/; no strategy module imports torch or sentence_transformers. Real Strategy 3 runs therefore import faiss first, and D-73(1) stands.
+(3) Erratum to D-74(3): (a) the sentence that installed versions "affect thread management, OpenMP runtime resolution, and embedding execution latencies" is withdrawn; versions are recorded as provenance, and any effect of version on thread behaviour or latency is unmeasured. (b) manifest `libraries.torch` is read with importlib.metadata.version and records the distribution version `2.14.1`; the local build tag `+cu130` appears only in torch.__version__ and is not recorded in manifest.json. The example `2.14.1+cu130` in D-74(3) is a torch.__version__ value. The build tag is reported in the thesis environment description. Torch must not be imported in harness.py to record it, because that would change the import order (D-73).
+(4) Torch pin: closes D-74(5). torch is not pinned in pyproject.toml; the manifest records the installed version.
+(5) Independence record: INFRA-009-A and INFRA-010 were executed in session 1b3efbca-895e-4b87-bbbd-80fb31a3230d although their prompts excluded it. Their claims were re-checked by the APC against repository files and by commands Luke ran.
+(6) Plumbing pilot (D-68(3)(a)): run from Luke's terminal on 2026-10-15 into /tmp/pilot-s3-dsa (Strategy 3 primary, DSA, accuracy mode): 29 trials, 290 LLM calls, 0 retries; stderr `CPU thread pin applied: requested=1, torch_threads=1`; sidecar `cpu_threads: 1`; manifest libraries list networkx, pytest, httpx, numpy, torch, faiss-cpu, sentence-transformers. Output is excluded from results and no parameter changed because of it.
+Reasoning: closes the thread-pin chain on executed evidence, corrects two overstatements in D-74, and records the pilot required before RUN-001. Affects: docs/decisions/decision-log.md, docs/tasks/status.md, scripts/README.md, docs/reports/INFRA-011-<agent>-closeout.md, RUN-001.
```

### B. `docs/tasks/status.md`
```diff
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index d6553c6..9914703 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -59,9 +59,9 @@ Status: **in-progress** (unblocked following Phase 2 completion)
 | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
 | INFRA-007 | Wire all four strategies into the experiment CLI (`strategies/registry.py`, CLI parameters and applicability checks, deterministic run-directory slugs and `strategy_config.json` guard, `MiniLMEmbedder` with fail-closed pins, and primary/sensitivity run table) ([D-64]). | **done** | Implemented by Gemini (D-64); independently reviewed under INFRA-007-R (report `docs/reports/INFRA-007-R-gemini.md`, ACCEPT WITH AMENDMENTS); amendments applied under INFRA-007-P (D-66, report `docs/reports/INFRA-007-P-gemini.md`); pins set under INFRA-007-Q (D-67, report `docs/reports/INFRA-007-Q-gemini.md`). Live embedding runs still require Luke's one-time model download and the OpenMP timing check. Accepted at APC review 2026-10-12. |
 | INFRA-008 | Standalone OpenMP / PyTorch thread-timing check ([D-68](5)) | **done** | Completed by Luke (execution) and Gemini (analysis); see report [`docs/reports/INFRA-008-gemini-openmp-timing-check.md`](docs/reports/INFRA-008-gemini-openmp-timing-check.md). Pre-fixed materiality criteria triggered (+44.53% relative latency shift, torch threads drop 4 to 1); effect declared material ([D-71]). |
-| INFRA-009 | Pin PyTorch CPU threads to 1 for all embedding strategies ([D-72]) | **needs-review** | Implemented by Gemini; helper `pin_cpu_threads(1)` in `src/graph_insertion/cpu_threads.py`, called after `MiniLMEmbedder` construction in `scripts/run_experiment.py`, recorded in sidecar as `"cpu_threads": 1`, legacy-tolerant resume guard, unit and subprocess tests in `tests/test_cpu_threads.py`. Full test suite 689 passing, 3 skipped. See report [`docs/reports/INFRA-009-gemini-cpu-thread-pinning.md`](docs/reports/INFRA-009-gemini-cpu-thread-pinning.md). Under INFRA-009-A, test gaps closed with main() wiring tests, bidirectional import order tests, and 11 executed mutants on /tmp copies; see report [`docs/reports/INFRA-009-A-gemini-test-gaps-and-mutations.md`](docs/reports/INFRA-009-A-gemini-test-gaps-and-mutations.md). Mutation results to be independently re-checked by Luke's script; some report claims corrected under INFRA-010 (D-73). |
-| INFRA-010 | Record the FAISS/PyTorch import-order finding (D-73), correct two reports' claims, and record torch / faiss-cpu / sentence-transformers versions in `manifest.json` (D-74). | **needs-review** | Part A completed: import order verified (faiss before torch in Strategy 3, faiss absent in Strategies 2 and 4), D-73 recorded, INFRA-008 §A-2 amended, INFRA-009-A errata documented. Part B completed: default packages expanded in harness.get_library_versions (D-74), tests in `tests/test_harness.py`, executed 5-mutant table on /tmp clone, suite 699 passed, 3 skipped. See report [`docs/reports/INFRA-010-gemini-import-order-and-manifest-libraries.md`](docs/reports/INFRA-010-gemini-import-order-and-manifest-libraries.md). |
-| RUN-001   | Execute the pilot and the 24-run plan (D-68) | **blocked** | OpenMP timing check completed (INFRA-008, [D-71]: material 44.5% shift); CPU thread pin implemented under INFRA-009 ([D-72]). Blocked on the 290-call pilot. Planned calls: 290 pilot + 184,758 total (159,400 sweep + 25,358 accuracy). See run plan in [`scripts/README.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/README.md). |
+| INFRA-009 | Pin PyTorch CPU threads to 1 for all embedding strategies ([D-72]) | **done** | Implemented by Gemini; helper `pin_cpu_threads(1)` in `src/graph_insertion/cpu_threads.py`, called after `MiniLMEmbedder` construction in `scripts/run_experiment.py`, recorded in sidecar as `"cpu_threads": 1`, legacy-tolerant resume guard, unit and subprocess tests in `tests/test_cpu_threads.py`. Full test suite 689 passing, 3 skipped. See report [`docs/reports/INFRA-009-gemini-cpu-thread-pinning.md`](docs/reports/INFRA-009-gemini-cpu-thread-pinning.md). Under INFRA-009-A, test gaps closed with main() wiring tests, bidirectional import order tests, and 11 executed mutants on /tmp copies; see report [`docs/reports/INFRA-009-A-gemini-test-gaps-and-mutations.md`](docs/reports/INFRA-009-A-gemini-test-gaps-and-mutations.md). Mutation results to be independently re-checked by Luke's script; some report claims corrected under INFRA-010 (D-73). Accepted on executed mutation evidence ([D-76]). |
+| INFRA-010 | Record the FAISS/PyTorch import-order finding (D-73), correct two reports' claims, and record torch / faiss-cpu / sentence-transformers versions in `manifest.json` (D-74). | **done** | Part A completed: import order verified (faiss before torch in Strategy 3, faiss absent in Strategies 2 and 4), D-73 recorded, INFRA-008 §A-2 amended, INFRA-009-A errata documented. Part B completed: default packages expanded in harness.get_library_versions (D-74), tests in `tests/test_harness.py`, executed 5-mutant table on /tmp clone, suite 699 passed, 3 skipped. See report [`docs/reports/INFRA-010-gemini-import-order-and-manifest-libraries.md`](docs/reports/INFRA-010-gemini-import-order-and-manifest-libraries.md). Accepted; D-74(3) corrected by [D-76]. |
+| RUN-001   | Execute the pilot and the 24-run plan (D-68) | **in-progress** | OpenMP timing check completed (INFRA-008, [D-71]: material 44.5% shift); CPU thread pin implemented under INFRA-009 ([D-72]). Planned calls: 290 pilot + 184,758 total (159,400 sweep + 25,358 accuracy). See run plan in [`scripts/README.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/scripts/README.md). Plumbing pilot completed 2026-10-15, output excluded ([D-76](6)); the 24 runs have not started. |
 
 ## Phase 4 — Analysis & Writeup
```

### C. `scripts/README.md`
```diff
diff --git i/scripts/README.md w/scripts/README.md
index 0544aba..ab2aa57 100644
--- i/scripts/README.md
+++ w/scripts/README.md
@@ -264,7 +264,7 @@ The CLI pre-flight guard assumes 1.0 s per call and strictly refuses live execut
 
 #### 4. OpenMP / PyTorch Thread Check Outcome & Pinning Policy (D-71, D-72)
 
-`faiss.omp_set_num_threads(1)` is called by `ann_retrieval.py` to ensure deterministic index construction and queries. Because FAISS and PyTorch share an OpenMP thread setting in-process, `embed_s` in Strategy 3 would run single-threaded while Strategies 2 and 4 would run on 4 threads.
+`faiss.omp_set_num_threads(1)` is called by `ann_retrieval.py` to ensure deterministic index construction and queries. In the torch-first import order FAISS and PyTorch were observed to share one OpenMP thread setting ([D-71]); in the faiss-first order that real Strategy 3 runs use, no such coupling was observed ([D-73]). Whether a cross-strategy latency confound arose in real runs is unestablished.
 
 The diagnostic benchmark specified below was executed on Luke's host environment under **INFRA-008** (`docs/reports/INFRA-008-gemini-openmp-timing-check.md`):
 
@@ -295,6 +295,6 @@ done
 **Pinning Policy & Implementation ([D-72], INFRA-009):**
 - PyTorch intra-op CPU threads are pinned to `CPU_THREAD_PIN = 1` for every execution constructing `MiniLMEmbedder` via `graph_insertion.cpu_threads.pin_cpu_threads(1)` called in `scripts/run_experiment.py`.
 - Recorded in `strategy_config.json` sidecar embedder block as `"cpu_threads": 1`. Resume guard checks for matching `cpu_threads` in existing sidecars (legacy-tolerant).
-- Consequence: Strategies 2, 3, and 4 all execute CPU inference single-threaded (~24 ms per embedding on the reference host), ensuring completely fair, unconfounded cross-strategy latency comparisons.
+- Consequence: Strategies 2, 3, and 4 all execute CPU inference single-threaded (~24 ms per embedding on the reference host), so embedding times are uniform across strategies and independent of import order (single-threaded by protocol).
 - The diagnostic snippet does not need to be re-run.
```

---

## 5. Anything I Could Not Do

None. All task instructions were executed strictly within constraints: docs only, no network calls, no live API access, no code modifications, no test execution, reserved decision ID `[D-76]` verified unique prior to append, and worktree isolated per `AGENTS.md`.
