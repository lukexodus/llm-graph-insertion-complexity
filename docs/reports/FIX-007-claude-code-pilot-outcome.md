# FIX-007 Report — Record DSA Pilot Outcome and Correct D-36(3)

**Agent:** Claude Code  
**Date:** 2026-10-07  
**Task ID:** FIX-007  
**Status:** Complete  
**Staged Artifacts:** `results/pilot/20261007_053743Z/` (`summary.json`, `raw_calls.jsonl`, `pilot_run.log`) via `git add -f`  

---

## 1. Executive Summary

TASK FIX-007 records the empirical outcome of the live leave-one-out DSA pilot on the DeepSeek API, verifies the offline re-scoring determinism from raw telemetry, formally accepts prompt v2 under the pre-registered decision criteria ([D-34]), corrects the vendor off-peak schedule in the decision log ([D-36] item 3 -> [D-37] item 1), and analyzes error distributions against the gold graph transitive closure.

All changes remain **uncommitted** in the working tree (with accepted pilot artifacts force-staged per [D-35] item 6).

---

## 2. Telemetry Verification & Re-Scoring Check

### A. Independent Re-score Verification
To satisfy the rule "Verify, don't assume", `raw_calls.jsonl` from `results/pilot/20261007_053743Z/` was copied to an isolated temporary directory and re-scored using:
```bash
python3 scripts/pilot_dsa_zero_shot.py --rescore <temp_dir>/raw_calls.jsonl
```
The resulting `summary.json` was compared against the recorded pilot `summary.json`:
- **`evaluation` block equivalence:** **100% IDENTICAL** (all micro/macro precision, recall, F1, confusion matrices, swap consistency, and flip rate match exactly).
- **`acceptance` block equivalence:** **100% IDENTICAL** (G1 PASS, G2 CONDITIONAL, Overall CONDITIONAL).
- **Differences found:** Exactly 0 numerical or categorical differences.

### B. Telemetry Timestamp Accounting
- Verified that individual records in `raw_calls.jsonl` carry no per-call `timestamp` field. The run window is bounded by the output directory name (`20261007_053743Z`) and `summary.json` field `timestamp_utc` (`2026-10-07T05:49:00.879000+00:00`, run duration ~11.3 minutes from 05:37:43Z to 05:49:00Z).
- Verified that in `src/graph_insertion/harness.py`, all trial records in `raw.jsonl` (both accuracy runner and sweep runner, success and failure rows) carry an explicit UTC timestamp (`"timestamp": datetime.now(timezone.utc).isoformat()`).

---

## 3. Pilot Outcome & Evaluation Metrics

The live pilot ran across all 29 DSA nodes ($29 \times 28 = 812$ leave-one-out pairwise calls) against `deepseek-flash`:

### A. Gate 1: Protocol Validity — PASS
| Criterion | Metric Value | Threshold / Requirement | Status |
| :--- | :---: | :---: | :---: |
| Transport Failures | 0 | 0 | **PASS** |
| Parse Failures | 0 (0.0%) | $\le 8$ calls ($\le 1.0\%$) | **PASS** |
| Reasoning Tokens | 0 | 0 (non-thinking mode enforced) | **PASS** |
| Observed Model ID | `deepseek-flash` | Exactly 1 distinct observed ID | **PASS** |
| Configured == Observed | True (`deepseek-flash`) | Informational | **True** |
| Prompt Version | `"v2"` | Exactly `"v2"` | **PASS** |
| Retried Calls | 0 (0.0%) | $\le 2.0\%$ | **PASS** |

### B. Gate 2: Prompt Usefulness — CONDITIONAL
| Metric | Observed Value | Thresholds ([D-34]) | Verdict |
| :--- | :---: | :---: | :---: |
| Micro Recall | **0.6111** (66/108) | PASS $\ge 0.70$; FAIL $< 0.50$ | **CONDITIONAL** |
| Micro F1 | **0.5410** | PASS $\ge 0.50$; FAIL $< 0.35$ | **PASS** |
| Direction Flip Rate | **0.1538** (12/78) | PASS $\le 0.15$ | **CONDITIONAL** (misses PASS by 1 call) |
| **Overall Verdict** | — | — | **CONDITIONAL** |

### C. Additional Baseline & Ceiling Metrics
- **Micro Precision:** 0.4853 (66 / 136 predicted edges).
- **Macro Metrics:** Macro Precision = 0.5523, Macro Recall = 0.6064, Macro F1 = 0.5346 (all 29 nodes defined for precision and F1; 28 defined for recall).
- **3-Way Call Accuracy:** 87.65% (712 / 812 calls correct; sensitivity variant: 87.56%).
- **Swap Consistency:** 85.71% (348 of 406 unordered pairs yield symmetric decisions; 13 pairs predict the same directed edge in both orders, 45 predict edge in one order and NONE in the reverse).
- **Incident Edge Totals:** TP = 66, FP = 70, FN = 42. (On the single DSA unjudged pair `{'asymptotic_complexity', 'binary_search_tree'}`, the model predicted 1 edge, properly excluded from standard scoring).
- **Shortlist Recall:** 1.0 by construction (brute-force evaluation candidate set at $n=29$). These metrics represent the empirical brute-force accuracy ceiling for DSA.
- **Resource Usage:** Cost = $0.019802 across 123,872 input tokens and 2,035 output tokens (0 cache hits). Latency: mean 0.834s, median 0.808s, p95 1.183s, max 4.680s. 0 retries.

---

## 4. Offline Analysis: Gold Graph Transitive Closure & Directional Errors

Per prompt instruction 5, an offline, free analysis was conducted on the error distributions against the gold graph:

1. **False Positive Edges on Gold-0 Pairs ($N = 58$):**
   - Of the 58 negative pairs where the model predicted an edge (28 predicted `X_PREREQ_Y`, 30 predicted `Y_PREREQ_X`), **34 of 58 (58.62%)** are implied by the transitive closure of the DSA gold DAG:
     - 24 pairs where $X$ is an indirect prerequisite of $Y$ in the transitive closure.
     - 10 pairs where $Y$ is an indirect prerequisite of $X$ in the transitive closure.
   - Only 24 of the 58 false positives represent pairs with no ancestor/descendant relationship in the true transitive closure.
2. **Direction Flips ($N = 12$):**
   - Where the gold relationship is $X \rightarrow Y$ ($X$ is prerequisite, $Y$ dependent): **9 flips** (model predicted $Y$ prereq $X$).
   - Where the gold relationship is $Y \rightarrow X$ ($X$ is dependent, $Y$ prerequisite): **3 flips** (model predicted $X$ prereq $Y$).
   - The model showed a slight skew toward making the candidate $Y$ the prerequisite when flipping.
3. **NONE-Misses / False Negatives ($N = 30$):**
   - Where $X$ is the prerequisite ($X \rightarrow Y$): **11 misses** (model predicted NONE).
   - Where $X$ is the dependent ($Y \rightarrow X$): **19 misses** (model predicted NONE).

*Note: Per instruction, these counts are reported for analytical context only and no code or decision was altered based on them.*

---

## 5. Artifact Tracking & Git Staging

Per [D-35] item 6, the accepted pilot run was force-staged:
```bash
git add -f results/pilot/20261007_053743Z/
```
Verified via `git check-ignore results/dummy` that the rest of `results/` remains strictly untracked. All staged and modified files remain **uncommitted**.

---

## 6. Diffs of Edited Shared Docs

### A. `docs/decisions/decision-log.md`
```diff
@@ -299,6 +299,16 @@
 (3) Off-peak pricing and pilot scheduling: DeepSeek API off-peak pricing applies during 16:30–00:30 UTC (00:30–08:30 Beijing time), offering a 50% discount: input cache miss $0.15/M (vs $0.30/M peak), cache hit $0.003/M (vs $0.006/M peak), and output $0.60/M (vs $1.20/M peak). Pilot execution (812 calls) and future live sweeps should be scheduled within off-peak windows when practical.
 Reasoning: prevents silent masking of API response model anomalies or empty model telemetry, decouples G1 protocol validity from potential vendor routing alias mismatches while tracking concordance, locks official current DeepSeek model alias strings, and minimizes API budget expenditure via off-peak execution. Affects: `src/graph_insertion/llm.py`, `src/graph_insertion/harness.py`, `scripts/pilot_dsa_zero_shot.py`, `tests/test_llm.py`, `tests/test_harness.py`, `tests/test_pilot.py`, FIX-006.
 
+**[D-37]** Off-peak window correction, DSA pilot acceptance outcome, decision step locked:
+(1) Correction to [D-36] item 3: the off-peak window stated in [D-36] (16:30–00:30 UTC) was incorrect. Per DeepSeek's official pricing documentation (verified 2026-10-07): peak hours are 01:00–04:00 and 06:00–10:00 UTC, Monday through Friday, excluding Chinese public holidays; all other times (including weekends, weekdays 00:00–01:00, 04:00–06:00, 10:00–24:00 UTC, and Chinese public holidays) are off-peak. Flash pricing per 1M tokens: input cache-miss $0.15 off-peak / $0.30 peak, cache-hit $0.003 / $0.006, output $0.60 / $1.20. Additional facts omitted from [D-36]: legacy model identifiers `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` remain accepted by the API endpoint but are retired and served by DeepSeek-V4.1-Flash; the earlier v2 probe runs used the legacy name and were served by this identical model; DeepSeek's pricing page lists model version "DeepSeek-V4.1-Flash" but publishes no dated snapshot ID (updating the finding in FIX-004). All timed experiment sweeps and harness runs must be scheduled off-peak under THIS corrected window.
+(2) Pilot outcome: DSA pilot, run ID `20261007_053743Z` (executed 05:37–05:49 UTC, Wednesday, off-peak), prompt v2, configured model `deepseek-flash`, API-reported model ID `deepseek-flash` (API echoes the requested alias; no underlying version string is observable in response payloads).
+- G1 Validity: PASS across all criteria (0 transport failures, 0 parse failures / 0.0%, 0 reasoning tokens, exactly 1 observed model ID matching configured, prompt version v2, 0 retried calls / 0.0%).
+- G2 Usefulness: CONDITIONAL verdict. Micro F1 = 0.5410 (passes >=0.50 threshold), micro recall = 0.6111 (below 0.70 pass threshold, but above 0.50 fail threshold, so not FAIL), direction-flip rate = 12/78 = 0.1538 (exceeds 0.15 threshold by one call). Micro precision = 0.4853, macro F1 = 0.5346, macro precision = 0.5523, macro recall = 0.6064. 3-way call accuracy = 0.8765 (sensitivity variant = 0.8756), swap consistency = 0.8571 (348/406 unordered pairs; 13 pairs return the same directed token in both orders, 45 return edge-vs-NONE). Edge totals: TP = 66, FP = 70, FN = 42, with 1 prediction on the unjudged pair. Shortlist recall = 1.0 by construction (brute-force candidate set at n=29); these metrics define the empirical brute-force accuracy ceiling for DSA. Run resource metrics: total cost $0.0198 (123,872 input tokens, 2,035 output tokens, 0 cache hits), mean latency 0.834 s, median 0.808 s, p95 1.183 s, max latency 4.68 s, 0 retries.
+(3) Decision on decision step: per [D-34], CONDITIONAL acceptance requires proceeding with prompt v2 unchanged as the fixed shared decision step across all four strategies, documenting this performance baseline and its limitations in Chapter 3, and disallowing further prompt tuning on DSA. Rejected alternatives: further prompt tuning (risks overfitting to DSA); judging each candidate pair in both directions and ensembling (doubles LLM calls per candidate pair, violates [D-29] single-call contract, and alters the measured candidate-narrowing comparison).
+(4) Telemetry note: raw pilot call records in `raw_calls.jsonl` carry no per-call timestamps; the execution window is bounded by output directory name (`20261007_053743Z`) and summary `timestamp_utc` (`05:49:00Z`). In contrast, measurement harness records (`harness.py`) do record per-trial ISO UTC timestamps (`timestamp`).
+Reasoning: acceptance criteria were locked a priori ([D-34]); `evaluate_acceptance` pure function computed CONDITIONAL; preserves evaluation integrity and fixes accurate vendor window parameters. Affects: thesis Chapter 3 Section 3.2.6 (prompt lock, limitations, model naming), DOC-002, scheduling of all Phase 2 and Phase 3 experimental sweeps.
+
```

### B. `docs/tasks/status.md`
```diff
@@ -35,6 +35,7 @@
 | INFRA-006 | Build the shared decision step (the identical final step all four strategies use) and its metered LLM client: prompt semantics (is A a prerequisite of B, indirect allowed, since the gold graphs are not transitively reduced per INFRA-001), call granularity (reserved for Luke), parsing, call and time metering.                                                                                                                                         | **done** | Completed by Gemini. PairwiseDecisionStep, MeteredLLMClient, DeepSeekClient via httpx, and leave-one-out DSA pilot script implemented ([D-29]). 123 tests passing. See report [`docs/reports/INFRA-006-gemini-decision-step-llm-client.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-006-gemini-decision-step-llm-client.md). |
+| PILOT-001 | Execute live leave-one-out DSA pilot on DeepSeek API (prompt v2, n=29, 812 calls).                                                                                                                                                                                                                                                                                                                                            | **done** | CONDITIONAL acceptance per [D-37]. All 812 calls completed (0 retries, 0 transport/parse failures, cost $0.0198). Micro F1 0.541, recall 0.611, flip rate 15.38%, swap consistency 85.71%. Results in `results/pilot/20261007_053743Z/` (force-added per [D-35]). |
 
 ## Phase 2 — Four Parallel Strategy Tracks
@@ -71,7 +71,7 @@
 | DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md). |
-| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3; Section 3.2.6 model specification uses official alias deepseek-flash per [D-36]). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; and note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked. | **open** | Prompt not yet written; can wait until after INFRA-001. |
+| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3; Section 3.2.6 model specification uses official alias deepseek-flash per [D-36] and [D-37], noting that API responses report only the alias without internal model version, and timed runs are executed off-peak; Chapter 3 limitation text must report empirical DSA brute-force ceiling metrics from [D-37](2): micro F1 0.541, recall 0.611, precision 0.485, flip rate 15.38%, swap consistency 85.71%). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked; and record corrected per-file test counts (earlier "40/35" narrative was a misread report breakdown, see FIX-006 report). | **open** | Prompt not yet written; can wait until after INFRA-001. |
 | FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-001-gemini-infra-001-followup.md). |
@@ -77,4 +78,5 @@
 | FIX-005 | Promote decision prompt to PROMPT_VERSION v2 with 3 few-shot examples ([D-33]); pilot acceptance criteria G1/G2 and line count correction ([D-34]); sweep/eval/embedding/Strategy-2 specs ([D-35]); fix macro F1 definition and undefined handling; add evaluate_acceptance. | **needs-review** | Completed by Claude Code. 155 tests passing. See report [`docs/reports/FIX-005-claude-code-prompt-v2.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-005-claude-code-prompt-v2.md). |
 | FIX-006 | Enforce response model_id provenance in DeepSeekClient, eliminate fabricated manifest defaults, amend G1 validity model check to single observed ID with informational configured_equals_observed ([D-36]), add G2 boundary tests, update default model alias to deepseek-flash, and document off-peak execution window. | **needs-review** | Completed by Claude Code. 167 tests passing. See report [`docs/reports/FIX-006-claude-code-observed-model-integrity.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-006-claude-code-observed-model-integrity.md). |
+| FIX-007 | Record DSA pilot outcome and acceptance ([D-37]), correct off-peak window in D-36(3), verify rescore equivalence, stage accepted pilot artifacts, and analyze transitive closure implications. | **needs-review** | Completed by Claude Code. See report [`docs/reports/FIX-007-claude-code-pilot-outcome.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-007-claude-code-pilot-outcome.md). |
```

---

## 7. Found But Not Changed

1. **`scripts/pilot_dsa_zero_shot.py` CLI Default Prices:**
   The CLI parser currently defaults `--price-in` to `0.14` and `--price-out` to `0.28` (legacy defaults from initial implementation). The live pilot passed `--price-in 0.15 --price-out 0.60` explicitly. The CLI argument defaults were left untouched to avoid breaking compatibility with any scripts relying on the flags.
2. **`decision-log.md` [D-36] Historical Content:**
   Per the repository rule that `decision-log.md` is strictly append-only, entry [D-36] was preserved verbatim, with its off-peak schedule corrected via [D-37] item 1.
3. **Absence of Per-Call Timestamps in Pilot `raw_calls.jsonl`:**
   Observed that `pilot_dsa_zero_shot.py` does not log per-call ISO timestamps. The run window is adequately bounded by the directory timestamp and summary completion timestamp. No retrofit was made to the pilot script because the pilot is completed and accepted.
