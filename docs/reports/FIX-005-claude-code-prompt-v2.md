# Task Report: FIX-005 — Promote Decision Prompt to PROMPT_VERSION "v2", Pilot Acceptance Criteria, Experimental Parameters, and Scoring Hardening

**Task ID:** FIX-005  
**Agent:** Claude Code (`claude-code`)  
**Date:** 2026-10-07  
**Status:** needs-review  

---

## 1. Executive Summary

This task implements the promotion of the shared pairwise prerequisite decision prompt to `PROMPT_VERSION = "v2"` with three balanced few-shot examples, establishes explicit pilot acceptance criteria G1 (validity) and G2 (usefulness) under `[D-34]`, fixes per-node and macro F1 scoring in `src/graph_insertion/scoring.py` with undefined handling, locks experimental sweep, evaluation, and embedding parameters under `[D-35]`, and wires client execution parameter extraction into the measurement manifest.

All 155 unit tests pass cleanly across 8 test modules. All changes remain **uncommitted**. No live API calls or network requests were made.

---

## 2. Requirements and Verification Results

### 2.1 Verification of Existing State
- **Prior `SYSTEM_PROMPT` in `src/graph_insertion/decision.py`:** Verified against the repository. It matched the v1 prompt text word-for-word:
  ```text
  You judge prerequisite relationships between concepts in a curriculum. A concept P is a prerequisite of a concept Q if a learner needs to understand P, directly or indirectly through other concepts, before learning Q. Answer with exactly one of: X_PREREQ_Y (X is a prerequisite of Y), Y_PREREQ_X (Y is a prerequisite of X), NONE (neither). Output only that token.
  ```
- **`results/` Directory Inspection:** Inspected `results/`. The directory exists and was completely empty; no prior pilot artifacts were present or overwritten. `results/` was subsequently added to `.gitignore` per `[D-35]`.
- **DSA Gold Standard Line Count Verification (`[D-32]` correction):**
  - Prompt requested running `wc -l` and checking distinct pairs vs duplicate rows directly on `repositories/dataset/EKG-Dataset/DSA_gold_standard_MEKG.txt`.
  - Direct measurement confirmed:
    - `wc -l`: **841 lines**.
    - Distinct lines / ordered pairs: **840**.
    - Duplicate rows: exactly **1** duplicate row (`binary_search_tree;recursion;1`, appearing twice).
  - This corrects `[D-32]` item 1 (which mistakenly stated "840 lines across 29 nodes") and reconciles the repository with `docs/context/data-formats.md`.

### 2.2 Few-Shot Example Disjointness Check
- The v2 few-shot example concepts are: `{"fractions", "ratios", "calculus", "limits", "poetry", "plumbing"}`.
- Automated test `TestPromptVersionAndCorpusDisjointness.test_few_shot_examples_disjoint_from_all_corpora` dynamically loads all 12 corpora (DSA, Metacademy, and all 10 MEKG example files) and verifies that none of these 6 concept names appears in any corpus node set.
- Result: **0 collisions** across all 12 graphs.

---

## 3. Work Completed

### 3.1 Prompt Promotion (`src/graph_insertion/decision.py`)
- Set `PROMPT_VERSION = "v2"`.
- Updated `SYSTEM_PROMPT` to append three few-shot examples without a trailing newline:
  ```text
  You judge prerequisite relationships between concepts in a curriculum. A concept P is a prerequisite of a concept Q if a learner needs to understand P, directly or indirectly through other concepts, before learning Q. Answer with exactly one of: X_PREREQ_Y (X is a prerequisite of Y), Y_PREREQ_X (Y is a prerequisite of X), NONE (neither). Output only that token.

  Examples:
  Concept X: fractions / Concept Y: ratios -> X_PREREQ_Y
  Concept X: calculus / Concept Y: limits -> Y_PREREQ_X
  Concept X: poetry / Concept Y: plumbing -> NONE
  ```
- User prompt construction in `build_user_prompt()` was preserved strictly unchanged (`embed_text()`, `Concept X: ...`, `Concept Y: ...`).

### 3.2 Scoring Hardening & Macro F1 Fix (`src/graph_insertion/scoring.py`)
- **Per-Node F1 Formulation:** Updated `score_node_insertion()` so per-node F1 is defined directly as:
  $$\text{F1} = \frac{2 \cdot \text{TP}}{2 \cdot \text{TP} + \text{FP} + \text{FN}}$$
  $\text{F1}$ is `None` if and only if $2 \cdot \text{TP} + \text{FP} + \text{FN} == 0$.
  - When a node has gold incident edges ($\text{FN} > 0$) and zero predictions ($\text{TP} = 0, \text{FP} = 0$), $\text{F1} = 0.0$ and is included in the macro F1 average (previously, undefined precision caused F1 to be `None`, incorrectly excluding zero-prediction failures).
  - When a node has no gold incident edges ($\text{FN} = 0, \text{TP} = 0$) and one false positive ($\text{FP} > 0$), $\text{F1} = 0.0$ and is included in macro F1.
  - When a node has no gold edges and no predictions ($\text{TP} = 0, \text{FP} = 0, \text{FN} = 0$), $\text{F1}$ is `None` and excluded from the macro average.
- Applied identical definition to the sensitivity variant with $\text{FP}_{\text{sens}} = \text{FP} + \text{excluded}$.
- Precision and recall retain their respective undefined rules ($\text{Precision}$ is `None` when $\text{TP} + \text{FP} == 0$; $\text{Recall}$ is `None` when $\text{TP} + \text{FN} == 0$).
- **Undefined Macro Handling:** In `aggregate_scores()`:
  - If $n_{\text{defined}} == 0$ for any macro metric (`precision_macro`, `recall_macro`, `f1_macro`, `shortlist_recall_macro`, and sensitivity counterparts), the aggregate macro attribute is `None` rather than `0.0`.
  - Console summary formatting in `print_pilot_summary()` renders `None` as `"undefined"`.

### 3.3 Pilot Acceptance Evaluator & Pilot Artifacts (`scripts/pilot_dsa_zero_shot.py`)
- Implemented pure function `evaluate_acceptance(summary: dict[str, Any]) -> dict[str, Any]` enforcing `[D-34]`:
  - **G1 Validity (run integrity; failure requires fix and rerun):**
    - `transport_failures == 0`
    - `parse_failures <= 8` and $\le 1\%$
    - `reasoning_tokens == 0`
    - Observed model IDs contains exactly one entry matching the configured model
    - `prompt_version == "v2"`
    - Retried calls $\le 2\%$ ($\le 16 / 812$)
    - Evaluates to `"PASS"` or `"FAIL"`.
  - **G2 Usefulness (prompt verdict):**
    - `"PASS"` if micro recall $\ge 0.70$ AND micro F1 $\ge 0.50$ AND direction flips $\le 15\%$ of calls where the model predicts an edge on a pair with a gold edge in either direction.
    - `"FAIL"` if micro F1 $< 0.35$ OR micro recall $< 0.50$.
    - Otherwise `"CONDITIONAL"` (proceed, document limitation, no tuning on DSA).
  - **Overall Verdict:** `"PASS"`, `"FAIL"`, `"CONDITIONAL"`, or `"INVALID"` (if G1 fails).
- Direction flip rate is computed over calls where both gold has an edge in either direction and the model predicted an edge in either direction:
  $$\text{Flip Rate} = \frac{\text{flips}}{\text{calls with gold edge and predicted edge}}$$
- `run_pilot` and `--rescore` record `summary["acceptance"] = evaluate_acceptance(summary)` directly into `summary.json`.
- Each call record in `raw_calls.jsonl` now records `"model": resp.model_id`.
- `summary.json` now explicitly records:
  - `configured_model`, `model_id`
  - `observed_model_ids`
  - `base_url`
  - `temperature`
  - `thinking_mode`
  - `max_tokens`
  - `prompt_version`
  - `parse_failure_count`
  - `retried_call_count`
  - `transport_failure_count`
  - `evaluation.node_insertion_scoring` (micro, macro with nulls, sensitivity)
  - `direction_flips`, `calls_with_gold_and_pred_edge`, `direction_flip_rate`
  - `acceptance` dictionary with per-criterion breakdown.

### 3.4 Client Parameter Exposure & Harness Manifest (`src/graph_insertion/{llm,harness}.py`)
- Exposed `temperature`, `max_tokens`, `thinking`, and `thinking_mode` on `DeepSeekClient` and `FakeLLMClient`.
- In `src/graph_insertion/harness.py`:
  - Updated `_extract_model_and_prompt_info` to inspect `client` / `inner_client` for `temperature`, `thinking`, and `max_tokens`, falling back to `0.0`, `"disabled"`, `16` only if absent.
  - Updated `write_manifest` to read these values from `model_info` rather than literal constants.

### 3.5 Decisions Appended (`docs/decisions/decision-log.md`)
Verified that `[D-32]` was the last entry before appending:
- **`[D-33]`**: Promotion of pairwise decision prompt to `PROMPT_VERSION = "v2"`.
- **`[D-34]`**: Pilot acceptance criteria (G1 validity, G2 usefulness) and correction to `[D-32]` item 1 line count (841 lines, 840 distinct pairs + 1 duplicate row).
- **`[D-35]`**: Experimental sweep sizes (50, 100, 200, 500, 1000, 2000 x 10 trials), accuracy evaluation scope (all 29 DSA + 30 seeded Metacademy), DATA-004 parameters (CS domain, >=2100 names), local sentence-transformers `all-MiniLM-L6-v2` embedding on CPU, Strategy 2 threshold (0.6 a priori; sensitivity 0.4 and 0.5), and untracked `results/` in `.gitignore`.

### 3.6 Task Tracker Updated (`docs/tasks/status.md`)
- `DATA-004`: Updated task description to reflect `[D-35]` parameters (sweep sizes, CS domain, >=2100 names, local sentence-transformers MiniLM embedding).
- `DOC-002`: Noted that the exact v2 prompt text from `[D-33]` must be reproduced in Chapter 3.
- `FIX-005`: Added row with status `needs-review`.

---

## 4. Test Suite Results

Full test suite execution (`pytest -v`):
```text
tests/test_decision.py: 15 tests (PASSED)
tests/test_graph_representation.py: 51 tests (PASSED)
tests/test_harness.py: 15 tests (PASSED)
tests/test_llm.py: 9 tests (PASSED)
tests/test_loader.py: 26 tests (PASSED)
tests/test_pilot.py: 6 tests (PASSED)
tests/test_scoring.py: 7 tests (PASSED)
tests/test_strategy_interface.py: 26 tests (PASSED)
------------------------------------------------------
Total: 155 passed in 7.68s
```

Offline pilot simulation execution:
- Executed `python3 scripts/pilot_dsa_zero_shot.py --confirm --offline-fake --output-dir /tmp/pilot_test_offline`
  - Completed all 812 calls against `FakeLLMClient`.
  - Emitted `summary.json` containing all required execution metadata, observed model IDs, macro nulls rendered as `"undefined"`, and G1/G2 acceptance evaluation.
  - Executed `--rescore` against the output; re-scored all 812 calls identically and refreshed acceptance verdict.
  - Cleaned up temporary directory `/tmp/pilot_test_offline`.

---

## 5. Found but Not Changed

1. **`tests/test_harness.py` Dummy / Mock Classes:**
   - In `tests/test_harness.py`, classes `DeterministicDecisionStep`, `FlakyDecisionStep`, and `DummyStep` define `self.PROMPT_VERSION = "v1"`. These are test-internal mock harnesses asserting that whatever `PROMPT_VERSION` is defined on a decision step is copied to the manifest. They do not test `src/graph_insertion/decision.py` and were left untouched.
2. **`scripts/run_experiment.py` `StubDecisionStep`:**
   - Updated `StubDecisionStep` to import and set `self.PROMPT_VERSION = PROMPT_VERSION` from `graph_insertion.decision` rather than hardcoding `"v1"`.
3. **Missing Directed Pair in DSA:**
   - Confirmed again during line verification: `DSA_gold_standard_MEKG.txt` line 68 contains `asymptotic_complexity;binary_search_tree;0`, but the reverse pair `binary_search_tree;asymptotic_complexity` is absent from the file. This aligns with `[D-32]` and `[D-34]`.
