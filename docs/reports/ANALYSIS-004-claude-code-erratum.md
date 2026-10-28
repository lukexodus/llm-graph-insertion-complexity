# ANALYSIS-004 Erratum: T9b Match Count and Monte Carlo Dispersion

**Task:** ANALYSIS-004 · **Agent:** Claude Code · **Status:** needs-review · **Branch:** `task/ANALYSIS-004` · **Corrects:** [`ANALYSIS-004-claude-code-posthoc-ranking.md`](ANALYSIS-004-claude-code-posthoc-ranking.md) and [D-90] · **Recorded in:** [D-91]

**STATUS: POST HOC, NOT PRE-REGISTERED.** This erratum changes no code, data, table or result. It corrects two factual sentences in the task report and [D-90] found during the APC's independent review.

---

## Executive Summary

The APC's review confirmed the pipeline outputs and found two wrong sentences in the report:

1. **T9b match count.** The report says the wall-clock-substituted top strategy matches T7 in "2 of 6" cells. The correct count is **3 of 6** (the report's own list already showed three matches). The leader changes in three cells, each time to S3: DSA accuracy-first, DSA cost-first and Metacademy accuracy-first. DSA balanced is *not* a change: S3 already leads there in T7. The chat summary's "DSA leader to S3 in all scenarios" is therefore also wrong.
2. **Monte Carlo vs exact.** The report says the largest Monte Carlo difference is "below one Monte Carlo standard error". That is false for one of the 32 cells: DSA S2 rank 2 differs by 0.004597 with SE = 0.001602, about **2.9 SE**. This is plausible chance across 32 cells, and the reviewer reproduced the same Monte Carlo numbers, so there is no generator defect.
3. **Not an error.** The report's claim that thesis Section 3.6.3 displays `C_i` without the `1 −` reversal is confirmed by the reviewer against the docx. The implementation's reversed form stands.

The unit's substantive results are unchanged: gate PASS, 72 cross-check cells matched, T5–T9 values and classes confirmed by the reviewer, and all pre-registered artifacts untouched.

---

## Changes Made

- Added [D-91] to `docs/decisions/decision-log.md`, correcting [D-90](3)(d) and (3)(f) by later entry rather than editing the frozen text.
- Added this erratum file; the original task report is **not** edited, per the one-file-per-task report rule.
- Updated the `ANALYSIS-004` row of `docs/tasks/status.md` to link this erratum.
- No code, test, table, figure, RUN_INFO or bundle change.

### Corrected sentences

| Location | Wrong text | Correct text |
| --- | --- | --- |
| Report, Table T9b section; [D-90](3)(f) | "matches T7 in 2 of 6" / "changes … in 4 of the 6" | matches in **3 of 6**; changes in **3 of 6** |
| [D-90](3)(f) | "DSA in all three scenarios" | DSA accuracy-first and DSA cost-first |
| Report, T8 section; [D-90](3)(d) | "Both are below one Monte Carlo standard error" | Largest is 2.9 SE (DSA S2 rank 2); 30 of 32 cells are below 1.5 SE |
| Chat summary | "DSA leader to S3 in all scenarios" | DSA leader changes to S3 in two of three scenarios; S3 already led balanced |

The T9b table itself, its `top_matches_T7` column (three `True`), and the exact-share table were already correct; only the prose miscounted.

---

## Verification & Test Evidence

Recomputed in this worktree from the committed outputs:

- **T9b matches:** 3 of 6 (`DSA balanced`, `Metacademy balanced`, `Metacademy cost-first` are `True`; the other three are `False`).
- **Dispersion:** worst cell DSA S2 rank 2, p = 0.0543, |MC − exact| = 0.004597, SE = sqrt(0.0543 × 0.9457 / 20000) = 0.001602, ratio 2.87. Next worst DSA S2 rank 3 at 1.57 SE; all others below 1.5 SE.
- **C_i formula:** confirmed in the revised thesis file (line 408 displays the unreversed ratio while line 402's prose says "reversed so that higher is better").
- **APC E11 (notes under Tables 4.4 and 4.10):** text search found "to be regenerated" only in the Table 4.9 caption (line 628). No such wording under Tables 4.4 or 4.10.
- **E10a scope:** the phrase "level with random" also occurs in the sensitivity paragraph (line 615: "level with a size-matched one"). The APC's E10a covers only the line after Table 4.7 (line 609). Both sentences are inaccurate against T5b (0.2593 vs 0.2498) and should be changed together.
- **Exact G3 margin stopping points:** S1 stops being dominated at ΔF1 = 0.150658 and S4 at 0.155862, so the APC's "0.151 / 0.156" is correct.

Test suite unchanged; no code was touched, so the earlier counts stand.

---

## Git Diff

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index cdadfff..fd1e1bd 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -899,3 +899,10 @@ Reasoning: freezes the post-hoc decision and ranking specification (thesis Secti
 (6) Tests: `tests/test_posthoc.py` covers normalisation on a hand-worked example, the all-equal → 0.5 rule and flag, the DSA balanced tie and mean-rank handling, tau-b with ties against hand-computed values, weighted TOPSIS on a three-point toy matrix with a known answer, exact shares against a 200,000-point fine grid, seeded-draw determinism, gate-class logic covering all three classes, cross-check assertion success and failure, "validation failure ⇒ no artifacts", "post-hoc stage writes only its own names", and "default run writes the legacy file set". The full suite was run; the only failures are the pre-existing environment-dependent ones (FAISS, PyTorch/sentence-transformers, and the source-grep collision with `scripts/analysis/apc_check_f_outputs.py`), with the same failure set on unmodified `master` (counts in the task report, not recorded here per [D-86](1)(b)).
 (7) Files: `scripts/analysis/posthoc.py`, `scripts/analysis/posthoc_figures.py`, `scripts/analysis/run_analysis.py`, `tests/test_posthoc.py`, `docs/prompts/ANALYSIS-004-PROMPT.md`, `docs/context/analysis-plan.md` (Amendment 4), `docs/tasks/status.md`, this entry, and the task report.
 Reasoning: records how the [D-89]-frozen post-hoc stage was implemented and reproduced, the computed gate classes and ranking results, the Monte Carlo-versus-exact comparison, the cross-check agreement, the one correction to [D-89], and the thesis cells whose regenerated values differ from the scratch table, so that the APC can update the thesis text without re-deriving anything. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `scripts/analysis/`, `tests/`.
+
+**[D-91]** Erratum to [D-90] and the ANALYSIS-004 report: T9b match count and Monte Carlo-versus-exact dispersion (ANALYSIS-004 independent review):
+(1) Correction to [D-90](3)(f): the wall-clock substitution changes the top-ranked strategy in **3 of 6** corpus × scenario cells, not 4. T7 and T9b agree on DSA balanced (S3 leads both), Metacademy balanced and Metacademy cost-first (S2 leads both); they differ on DSA accuracy-first, DSA cost-first and Metacademy accuracy-first, each change moving the lead to S3. The phrase "DSA in all three scenarios" is wrong: S3 already led DSA balanced under the weighted sum. The same correction applies to the ANALYSIS-004 report's "2 of 6" sentence (its own list already showed three matches) and to the chat summary's "DSA leader to S3 in all scenarios".
+(2) Correction to [D-90](3)(d) and the report: the maximum absolute Monte Carlo error is not "below one Monte Carlo standard error". For DSA S2 rank 2 the difference is 0.004597 against a standard error of sqrt(0.0543 × 0.9457 / 20000) = 0.001602, about 2.9 SE; the next-largest is 1.6 SE (DSA S2 rank 3) and the remaining 30 cells are below 1.5 SE. This is consistent with chance across 32 cells; the reviewer independently reproduced the Monte Carlo numbers, so there is no defect in the generator. The thesis statement that the standard error is at most about 0.004 remains correct.
+(3) Confirmed, not corrected: the report's claim that thesis Section 3.6.3 displays $C_i$ without the `1 −` reversal is correct (the reviewer confirmed it against the docx); the implementation's reversed form stands.
+(4) The pre-registered artifacts, gate status, 72-cell cross-check, T5–T9 values, and the three review recommendations (weighted TOPSIS stays, Table 4.10 stays Monte Carlo, the DSA caveat goes in the new cross-check paragraph) are unaffected. No code, data or result changes.
+Reasoning: corrects two factual sentences in [D-90] and the task report found during independent review, by later entry rather than by editing earlier text. Affects: `docs/decisions/decision-log.md`, `docs/reports/ANALYSIS-004-claude-code-erratum.md`, `docs/tasks/status.md`.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 7723ad9..b554c65 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -78,7 +78,7 @@ Status: **in-progress**
 | ANALYSIS-002-F | Remediate Phase 4 analysis pipeline review defects, enforce validation gate, implement Rules R1–R3, and record D-86 | **done** | Completed by Gemini; branch `task/ANALYSIS-002-F` at commit `f5e085d` (base `17ed1f8`). See report [`docs/reports/ANALYSIS-002-F-gemini-report.md`](docs/reports/ANALYSIS-002-F-gemini-report.md). |
 | ANALYSIS-002-G | Independent review of ANALYSIS-002-F Phase 4 analysis pipeline remediation | **done** | Completed by Gemini; branch `task/ANALYSIS-002-G` at commit `ccec59c` (base `f5e085d`). See report [`docs/reports/ANALYSIS-002-G-gemini-review.md`](docs/reports/ANALYSIS-002-G-gemini-review.md). |
 | ANALYSIS-003 | Add exploratory log-scale companion figures F1b, F2b, F6b and record D-87 | **done** | Completed by Gemini; branch `task/ANALYSIS-003` at commit `5ab04a6` (base `79046eb`). See report [`docs/reports/ANALYSIS-003-gemini-report.md`](docs/reports/ANALYSIS-003-gemini-report.md). |
-| ANALYSIS-004 | Add the post-hoc decision and ranking stage (Tables T5–T9b, Figures F7–F9; thesis Sections 3.6 and 4.4.1), including TOPSIS, Kendall tau-b and the wall-clock-substituted check; freeze the specification in [D-89] and record implementation/results in [D-90]. | **needs-review** | Completed by Claude Code; branch `task/ANALYSIS-004` (base `a524de7`), commits `edda901`, `8e2eccf`, `e3b563d`, `f4ba18a`, plus the final report/patch commit. Post hoc, not pre-registered; no live calls; gate passed; 72 cross-check cells matched. See report [`docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md`](docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md). |
+| ANALYSIS-004 | Add the post-hoc decision and ranking stage (Tables T5–T9b, Figures F7–F9; thesis Sections 3.6 and 4.4.1), including TOPSIS, Kendall tau-b and the wall-clock-substituted check; freeze the specification in [D-89] and record implementation/results in [D-90]. | **needs-review** | Completed by Claude Code; branch `task/ANALYSIS-004` (base `a524de7`), commits `edda901`, `8e2eccf`, `e3b563d`, `f4ba18a`, plus the final report/patch commit. Post hoc, not pre-registered; no live calls; gate passed; 72 cross-check cells matched. See report [`docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md`](docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md); review corrections in erratum [`docs/reports/ANALYSIS-004-claude-code-erratum.md`](docs/reports/ANALYSIS-004-claude-code-erratum.md) ([D-91]). |
 | DOC-012 | Correct the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures ([D-88]) | **needs-review** | Docs only. Completed by Claude Code; branch `task/DOC-012` at commit `6f198c5` (base `554bde3`). See report [`docs/reports/DOC-012-claude-code-correction.md`](docs/reports/DOC-012-claude-code-correction.md). |
 
 ## Thesis document status (separate track from the code work above)
```

---

## Items for the APC

1. **Q1–Q3:** all three recommendations are consistent with the implemented stage; no recomputation or code change is needed. Q1: the weighted-before-distances form is already the frozen one. Q2: Table 4.10 is already the Monte Carlo table, and T8b carries the exact shares. Q3: the DSA caveat is already in T9, and the new 4.4.1 paragraph states it.
2. **E5 values confirmed:** 0.336, 0.372, 0.116/0.905, 0.083/0.932, 0.050/0.959 at three decimals. Leaders unchanged.
3. **E6 values confirmed** against T8 (MC, 2 dp): DSA S2 rank 2 0.05; DSA S4 rank 4 0.27; Metacademy S2 0.74/0.26; S3 0.26/0.68; S4 rank 3 0.74. The "60%/68%" prose is correct (exact 0.5981/0.6803).
4. **E8 values confirmed** against T9: τ-b 0.6667 on the two DSA swaps, 1.0 with one tied pair on DSA balanced, 1.0 with no ties on Metacademy; TOPSIS closeness 0.7194 (S3) vs 0.7000 (S1) at DSA accuracy-first; S3 is top-two in all six wall-clock cells and in five of six under TOPSIS (third on DSA cost-first).
5. **E10:** apply the "marginally above" wording to both line 609 and line 615.
6. **E11:** only the Table 4.9 caption carries "to be regenerated"; the handoff's mention of notes under Tables 4.4 and 4.10 is not supported by the current revised thesis file.
7. **Deck:** slide 37's 0.905/0.959 and 68% are confirmed. The DSA accuracy-first TOPSIS swap (S3 over S1) is the expected panel question; the weighted-sum answer and the TOPSIS answer should be stated separately.
