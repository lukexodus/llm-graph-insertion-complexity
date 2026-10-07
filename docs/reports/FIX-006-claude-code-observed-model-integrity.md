# FIX-006 Report — Observed-Model Integrity, G1 Amendment, Boundary Tests

**Agent:** Claude Code  
**Date:** 2026-10-07  
**Task ID:** FIX-006  
**Status:** Complete (all 167 tests passing, uncommitted in working tree)  
**Patch File:** `patch/FIX-006.patch`

---

## 1. Executive Summary

TASK FIX-006 addresses model identification integrity and test coverage follow-ups to FIX-005:
1. **Model ID Provenance in `DeepSeekClient`:** Verified and fixed the provenance of `LLMResponse.model_id`. Previously, `DeepSeekClient._request` fell back to `self.model` if the API response lacked a `"model"` field, silently fabricating telemetry. It now strictly extracts `data.get("model") or ""` (empty string if missing or None). A mock test asserting `resp.model_id == ""` on HTTP 200 responses lacking `"model"` was added.
2. **Elimination of Fabricated Manifest Defaults:**
   - In `scripts/pilot_dsa_zero_shot.py`, removed the fallback `observed_model_ids = [model_name]`, which masked missing observed model telemetry. Client configuration extraction now defaults `temperature`, `thinking_mode`, and `max_tokens` to `None` when unexposed by the client (removing artificial `0.0`, `"disabled"`, and `16` fallbacks).
   - In `src/graph_insertion/harness.py`, `_extract_model_and_prompt_info` now leaves `temperature`, `thinking_mode`, and `max_tokens` as `None` when the underlying client does not expose them.
   - In `FakeLLMClient`, `max_tokens` is locked to a constant `16` (previously mirrored `output_tokens`).
3. **Amendment of G1 Validity in `evaluate_acceptance` ([D-36]):**
   - Amends the model identity criterion from [D-34]: G1 validity now passes if and only if `len(set(observed_model_ids)) == 1` (exactly one distinct observed model ID across all calls; an empty observed list fails).
   - Added an informational, un-gated metric `configured_equals_observed: bool` in `g1_validity["model_identity"]` to report concordance without gating validity.
   - Comprehensive unit tests added for empty list (FAIL), two distinct IDs (FAIL), and single distinct ID differing from configured (PASS with `configured_equals_observed=False`).
4. **G2 Usefulness Boundary Tests:**
   - Added five exact boundary tests in `TestG2AcceptanceBoundaries`:
     - `recall=0.70`, `f1=0.50`, `flip_rate=0.15` -> `PASS`
     - `recall=0.50`, `f1=0.35`, `flip_rate=0.00` -> `CONDITIONAL`
     - `recall=0.50`, `f1=0.3499`, `flip_rate=0.00` -> `FAIL`
     - `recall=0.4999`, `f1=0.50`, `flip_rate=0.00` -> `FAIL`
     - `recall=0.70`, `f1=0.50`, `flip_rate=0.1501` -> `CONDITIONAL`
5. **Default Model Alias Migration:**
   - Migrated the default model name from `"deepseek-v4-flash"` to the standard official DeepSeek API alias `"deepseek-flash"` across `DeepSeekClient`, `FakeLLMClient` (`"fake-deepseek-flash"`), pilot scripts, and test suites.
6. **Decisions & Status Updates:**
   - Appended `[D-36]` to `docs/decisions/decision-log.md` (read live immediately prior to editing).
   - Updated `docs/tasks/status.md`: added `FIX-006` row (`needs-review`) and updated the `DOC-002` note.
7. **Test Count & Historical Investigation:**
   - Investigated and documented the evolution of `test_graph_representation.py` and `test_strategy_interface.py` test counts across git history, resolving why the current counts (51 and 26) differed from earlier remembered values (40 and 35).

All changes are left **uncommitted** in the working tree, and the full unified diff is captured in `patch/FIX-006.patch`.

---

## 2. Test Counts & Historical Discrepancy Investigation

### A. Current Real Per-File Test Counts

Running `pytest --collect-only -q` across the entire repository yields **167 collected tests** (up from 155 in FIX-005):

| Test File | Test Count | Description / Delta |
| :--- | :---: | :--- |
| `tests/test_decision.py` | 15 | Unchanged |
| `tests/test_graph_representation.py` | 51 | Unchanged |
| `tests/test_harness.py` | 16 | +1 (`test_manifest_client_parameters_recorded_when_exposed`) |
| `tests/test_llm.py` | 12 | +3 (`test_default_model_is_deepseek_flash`, `test_response_missing_model_yields_empty_model_id`, `test_fake_llm_client_properties_and_max_tokens_constant`) |
| `tests/test_loader.py` | 26 | Unchanged |
| `tests/test_pilot.py` | 14 | +8 (+3 G1 model identity edge cases, +5 G2 boundary tests) |
| `tests/test_scoring.py` | 7 | Unchanged |
| `tests/test_strategy_interface.py` | 26 | Unchanged |
| **Total** | **167** | **167 passed in 5.34s** |

### B. Investigation of "Earlier Known 40 and 35" vs Current 51 and 26

The prompt requested an investigation into why `test_graph_representation.py` (51) vs `test_strategy_interface.py` (26) differed from earlier remembered numbers ("40 and 35").

#### 1. Commit-by-Commit Test Count Evolution
Using `git show <commit>:<path>`, we traced the exact test function counts in both files from repo inception to HEAD:

| Commit | Task / Author | `test_graph_representation.py` | `test_strategy_interface.py` | Combined Total |
| :--- | :--- | :---: | :---: | :---: |
| `3dae0d8` | INFRA-001 (Gemini) | 38 | 0 (did not exist) | 38 |
| `f07146b` | FIX-001 (Gemini) | 48 (+10 tests) | 0 | 48 |
| `3505908` | INFRA-002 (Gemini) | 49 (+1 test) | 13 (created) | 62 |
| `8d5c181` | FIX-002 (Gemini) | 49 | 25 (+12 tests) | 74 |
| `27a6061` | INFRA-003 (Gemini) | 49 | 25 | 74 |
| `b863faa` | FIX-003 (Gemini) | 49 | 26 (+1 net test) | 75 |
| `e3ccfd0` | INFRA-004 (Gemini) | 51 (+2 tests) | 26 | 77 |
| `HEAD` | FIX-005 / FIX-006 | 51 | 26 | 77 |

Specific function diffs between `8d5c181` (FIX-002) and `HEAD`:
- `tests/test_graph_representation.py`:
  - Added in `e3ccfd0` (INFRA-004): `test_without_node_removes_node_and_incident_edges` and `test_without_node_nonexistent_node_raises_key_error` (49 -> 51).
  - Zero tests removed.
- `tests/test_strategy_interface.py`:
  - Added in `b863faa` (FIX-003): `test_metered_embedder_none_or_invalid_raises_type_error`, `test_embedder_mismatch_raises_value_error_and_graph_untouched`, `test_strategy_without_embedder_accepts_any_metered_embedder`.
  - Removed in `b863faa` (FIX-003): `test_explicit_none_metered_embedder_allowed`, `test_unmetered_embedding_detected_and_raises` (superseded by D-28 non-Optional contract). Net change: 25 -> 26.
  - Zero tests moved between the two files.

#### 2. Root Cause of the "40 and 35" Figures
Searching repository reports reveals the exact origin of "40 and 35":
- In `docs/reports/FIX-002-gemini-infra-002-hardening.md` (line 88), Gemini wrote:
  > "74 passed in 2.64s. All existing tests from `INFRA-001` and `FIX-001` (40 tests) continue to pass cleanly, and all 34 interface and hardening tests pass."
- In `docs/reports/INFRA-003-gemini-corpus-loader.md` (line 168), Gemini echoed:
  > "- 40 tests in `test_graph_representation.py` (retrofitted with dataset skip conditions)."

**Finding:** The total test count of 74 at FIX-002 was completely accurate, but Gemini's narrative breakdown misattributed the numbers as "40" and "34" (which sum to 74). In reality:
- `test_graph_representation.py` actually contained **49 tests** (not 40).
- `test_strategy_interface.py` actually contained **25 tests** (not 34).

The later prompt and memory noted "earlier known 40 and 35" (~34) by reading the text of the FIX-002 report rather than inspecting the test files directly. **No tests were ever lost, moved, or deleted between `test_graph_representation.py` and `test_strategy_interface.py`.** The true count grew monotonically from 38 -> 48 -> 49 -> 51 for graph representation, and 13 -> 25 -> 26 for strategy interface.

---

## 3. Detailed Verification of Completed Items

### A. Provenance Verification in `src/graph_insertion/llm.py`
- Checked `DeepSeekClient._request`: Line 358 previously read:
  ```python
  model_id = data.get("model", self.model)
  ```
- If the HTTP response from DeepSeek API omitted the `"model"` field, this line silently assigned `self.model`, falsely claiming that the configured model had been observed in the response.
- Fixed to:
  ```python
  model_id = data.get("model") or ""
  ```
- Added unit test `test_response_missing_model_yields_empty_model_id` in `tests/test_llm.py` using `httpx.MockTransport`, confirming that a response lacking `"model"` returns `resp.model_id == ""` while parsing usage and content normally.

### B. Removal of Fabricated Manifest & Client Defaults
- In `scripts/pilot_dsa_zero_shot.py`:
  - Deleted the fallback:
    ```python
    if not observed_model_ids:
        observed_model_ids = [model_name]
    ```
    Now, if no call returns an observed model ID, `observed_model_ids` remains `[]`, accurately triggering a G1 validity failure.
  - In `run_pilot`, client parameter extraction now uses `None` as fallback:
    ```python
    temperature = getattr(inner_client, "temperature", getattr(client, "temperature", None))
    t_obj = getattr(inner_client, "thinking", getattr(client, "thinking", None))
    thinking_mode = t_obj.get("type", None) if isinstance(t_obj, dict) else (str(t_obj) if t_obj is not None else None)
    max_tokens = getattr(inner_client, "max_tokens", getattr(client, "max_tokens", None))
    ```
- In `src/graph_insertion/harness.py`:
  - `_extract_model_and_prompt_info` removed default fallbacks of `0.0`, `"disabled"`, and `16`, returning `None` for unexposed parameters.
  - Updated `tests/test_harness.py`: `test_manifest_model_and_tokens_not_redacted` verifies that unexposed parameters serialize as `None`, and `test_manifest_client_parameters_recorded_when_exposed` verifies that exposed parameters serialize faithfully without redaction.
- In `FakeLLMClient`:
  - Changed `self.max_tokens = 16` constant (was `output_tokens`).
  - Added unit test `test_fake_llm_client_properties_and_max_tokens_constant` verifying `fake.max_tokens == 16` even when `output_tokens = 3`.

### C. Amendment of G1 Model Validity in `evaluate_acceptance`
- Updated `evaluate_acceptance`:
  ```python
  obs_set = set(obs_m)
  g1_model_pass = (len(obs_set) == 1)
  configured_equals_observed = bool(obs_set) and (obs_set == {conf_m})
  ```
- Evaluated and tested:
  - `obs_m = []` -> `g1_model_pass = False`, `configured_equals_observed = False`, G1 `FAIL`.
  - `obs_m = ["deepseek-flash", "deepseek-chat"]` -> `g1_model_pass = False`, `configured_equals_observed = False`, G1 `FAIL`.
  - `obs_m = ["deepseek-chat"]`, `conf_m = "deepseek-flash"` -> `g1_model_pass = True`, `configured_equals_observed = False`, G1 `PASS`.
  - `obs_m = ["deepseek-flash"]`, `conf_m = "deepseek-flash"` -> `g1_model_pass = True`, `configured_equals_observed = True`, G1 `PASS`.

### D. G2 Usefulness Boundary Tests
- Created `TestG2AcceptanceBoundaries` in `tests/test_pilot.py` covering:
  1. Exact Pass Boundary: `recall=0.70`, `f1=0.50`, `flip_rate=0.15` (15/100) -> G2 `PASS`.
  2. Conditional Boundary: `f1=0.35`, `recall=0.50`, `flip_rate=0.00` -> G2 `CONDITIONAL`.
  3. F1 Fail Boundary: `f1=0.3499`, `recall=0.50`, `flip_rate=0.00` -> G2 `FAIL`.
  4. Recall Fail Boundary: `recall=0.4999`, `f1=0.50`, `flip_rate=0.00` -> G2 `FAIL`.
  5. Direction Flip Conditional Boundary: `recall=0.70`, `f1=0.50`, `flip_rate=0.1501` (1501/10000) -> G2 `CONDITIONAL`.

### E. Default Model Migration to `deepseek-flash`
- `DeepSeekClient.DEFAULT_MODEL = "deepseek-flash"`
- `FakeLLMClient(model_id="fake-deepseek-flash")`
- `pilot_dsa_zero_shot.py` CLI help and `--offline-fake` default model updated to `fake-deepseek-flash`.
- All tests in `test_llm.py`, `test_harness.py`, `test_pilot.py` updated to `"deepseek-flash"`.

---

## 4. Diffs of Shared Docs

### A. `docs/decisions/decision-log.md`
```diff
@@ -293,5 +293,12 @@
 (6) Artifact tracking: `results/` untracked in `.gitignore` except the accepted pilot run, which will be force-added.
 Reasoning: fixes experimental matrix before execution, isolates embedding computation timing from network jitter, prevents post-hoc threshold tuning on evaluation graphs, and keeps repository clean from intermediate sweep artifacts. Affects: `docs/tasks/status.md` (DATA-004), `.gitignore`, `harness.py`, `scripts/run_experiment.py`, STRAT-002, DATA-004.
 
+**[D-36]** Model identity integrity, G1 validity amendment, default model alias, and off-peak pilot scheduling:
+(1) Model identifier & alias: `DeepSeekClient` default model is updated to `"deepseek-flash"` (standard official API model alias replacing `"deepseek-v4-flash"`). API response `model_id` provenance is strictly enforced from the response `"model"` field (`""` if absent or None, never falling back to configured model name). In offline simulation, `FakeLLMClient` defaults to `"fake-deepseek-flash"` and exposes constant `max_tokens = 16`; unexposed client parameters in manifest extraction default to `None` without fabrication.
+(2) G1 validity model check amended (supersedes model identity criterion in [D-34]): G1 validity requires `len(set(observed_model_ids)) == 1` (exactly one observed model ID across all calls; an empty observed list fails). Model concordance with configured name (`configured_equals_observed: bool`) is recorded as an informational, un-gated metric.
+(3) Off-peak pricing and pilot scheduling: DeepSeek API off-peak pricing applies during 16:30–00:30 UTC (00:30–08:30 Beijing time), offering a 50% discount: input cache miss $0.15/M (vs $0.30/M peak), cache hit $0.003/M (vs $0.006/M peak), and output $0.60/M (vs $1.20/M peak). Pilot execution (812 calls) and future live sweeps should be scheduled within off-peak windows when practical.
+Reasoning: prevents silent masking of API response model anomalies or empty model telemetry, decouples G1 protocol validity from potential vendor routing alias mismatches while tracking concordance, locks official current DeepSeek model alias strings, and minimizes API budget expenditure via off-peak execution. Affects: `src/graph_insertion/llm.py`, `src/graph_insertion/harness.py`, `scripts/pilot_dsa_zero_shot.py`, `tests/test_llm.py`, `tests/test_harness.py`, `tests/test_pilot.py`, FIX-006.
+
+
```

### B. `docs/tasks/status.md`
```diff
@@ -71,7 +71,7 @@
 | DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](docs/reports/DOC-001-gemini-doc-sync.md). |
-| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; and note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked. | **open** | Prompt not yet written; can wait until after INFRA-001. |
+| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3; Section 3.2.6 model specification uses official alias deepseek-flash per [D-36]). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; and note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked. | **open** | Prompt not yet written; can wait until after INFRA-001. |
 | FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](docs/reports/FIX-001-gemini-infra-001-followup.md). |
 | FIX-002 | Hardening pass on INFRA-002: edge validation before graph mutation, shortlist contract validation, required keyword-only metered_embedder, single-embedding caching and unmetered detection, texts_log for D-21 enforcement, diagnostics error handling, apply_s timing, reusable StrategyConformanceSuite. | **done** | Completed by Gemini. See report [`docs/reports/FIX-002-gemini-infra-002-hardening.md`](docs/reports/FIX-002-gemini-infra-002-hardening.md). |
 | FIX-003 | Follow-up hardening on FIX-002: enforce required non-Optional MeteredEmbedder, embedder identity check against strategy._embedder, separate validate_s from total_s equation, add embedding_calls_in_update integer metric, test setup embeddings in D-21 text compliance, and fix typing import. | **done** | Completed by Gemini. See report [`docs/reports/FIX-003-gemini-driver-followup.md`](docs/reports/FIX-003-gemini-driver-followup.md). |
@@ -75,3 +75,5 @@
 | FIX-005 | Promote decision prompt to PROMPT_VERSION v2 with 3 few-shot examples ([D-33]); pilot acceptance criteria G1/G2 and line count correction ([D-34]); sweep/eval/embedding/Strategy-2 specs ([D-35]); fix macro F1 definition and undefined handling; add evaluate_acceptance. | **needs-review** | Completed by Claude Code. 155 tests passing. See report [`docs/reports/FIX-005-claude-code-prompt-v2.md`](docs/reports/FIX-005-claude-code-prompt-v2.md). |
+| FIX-006 | Enforce response model_id provenance in DeepSeekClient, eliminate fabricated manifest defaults, amend G1 validity model check to single observed ID with informational configured_equals_observed ([D-36]), add G2 boundary tests, update default model alias to deepseek-flash, and document off-peak execution window. | **needs-review** | Completed by Claude Code. 167 tests passing. See report [`docs/reports/FIX-006-claude-code-observed-model-integrity.md`](docs/reports/FIX-006-claude-code-observed-model-integrity.md). |
```

---

## 5. Found But Not Changed

1. **Historical Agent Reports Referencing `deepseek-v4-flash`:**
   Earlier report files (`docs/reports/INFRA-006-gemini-decision-step-llm-client.md` and `docs/reports/FIX-004-gemini-harness-pilot-corrections.md`) document the initial model evaluation as `deepseek-v4-flash`. Per AGENTS.md ("Never append to another agent's report file or to a shared log. One file per completed task, written once by the agent that did it"), historical reports were left unmodified.
2. **Decision Log `[D-29]` Prose:**
   Decision entry `[D-29]` references `DeepSeek V4 Flash`. Because `decision-log.md` is strictly append-only, `[D-29]` was preserved as recorded, and the updated official model string `deepseek-flash` was formally recorded in `[D-36]`.
3. **Off-Peak Execution Automation:**
   The DeepSeek API off-peak discount window (16:30–00:30 UTC) is documented in `[D-36]`. The pilot execution script `scripts/pilot_dsa_zero_shot.py` accepts pricing inputs via `--price-in` and `--price-out`. Rather than hard-coding time-of-day execution enforcement into Python code, the scheduling recommendation is documented so Luke can run the live pilot with the corresponding rates (`--price-in 0.15 --price-out 0.60`).
