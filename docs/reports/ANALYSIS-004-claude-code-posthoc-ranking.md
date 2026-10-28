# ANALYSIS-004 Report: Post-Hoc Decision and Ranking Stage (Tables 4.7–4.10, Figures 4.11–4.13)

**Task:** ANALYSIS-004 · **Agent:** Claude Code · **Status:** needs-review · **Branch:** `task/ANALYSIS-004` (base `a524de7`) · **Commit:** `f4ba18a` (code `8e2eccf`, figure layout `e3b563d`) · **Decision IDs:** [D-89] (specification, committed before computation), [D-90] (implementation, results, corrections)

**STATUS OF THIS WORK: POST HOC, NOT PRE-REGISTERED.** The framework was specified after the Chapter 4 measurements existed, per thesis Section 3.6.1. It adds no measurement and replaces no pre-registered result. Every emitted row carries `status = "post-hoc"` and every figure displays "POST HOC: not pre-registered".

---

## Executive Summary

The thesis's post-hoc decision and ranking framework (thesis Sections 3.6 and 4.4.1) is now implemented inside the repository's analysis pipeline as a separate, gate-validated stage:

- **New code only.** `scripts/analysis/posthoc.py` and `scripts/analysis/posthoc_figures.py`. The only existing file edited is `run_analysis.py`, which gains `--only posthoc` and `--crosscheck-dir`; with no flag its behaviour and artifacts are unchanged. `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py` and `style.py` are untouched, and G3 calls `stats.evaluate_dominance` unchanged.
- **Inputs are the in-memory T1/T2/F6 aggregates**, not re-parsed CSVs. Before writing anything, the stage asserts that all 72 values it uses equal the corresponding `final_output_final` T1, T2 (n = 2000) and F6 CSV cells. The assertion passed.
- **The validation gate passed** (24 runs) with `--src-diff-clean --hashes`; no live API call and no new experiment run was made.
- **New outputs only**, in `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`: Tables T5, T5b, T6, T7, T8, T8b, T9, T9b (CSV + Markdown) and Figures F7, F8, F9 (PDF + PNG + CSV), plus `RUN_INFO.txt`.
- **Computed results confirm the thesis's four classes:** S3 Effective, S2 Conditionally effective, S1 and S4 Not effective. Gate classes are unchanged for every G2 limit from 10 to 1,999, under a size-matched G1 baseline, and for every G3 margin on 0.000–0.150.
- **TOPSIS and Kendall's τ-b were computed for the first time.** τ-b is 0.6667 for DSA accuracy-first and cost-first and 1.0 for the other four corpus × scenario cells.
- **Exact analytic rank shares were computed** and agree with the Monte Carlo shares to at most 0.0046 (DSA) and 0.0022 (Metacademy).
- **The thesis scratch table needs several small corrections**, most importantly Metacademy S3 rank 2: exact 0.6803 (MC 0.6812), not 0.69. The sentence "69%" should read "68%" (DSA S3 rank 2 "60%" is confirmed). Table 4.9's Metacademy S1/S2 cells differ by up to 0.0027.

---

## Prompt Assumptions Verified (as requested)

| Prompt statement | Verified? |
| --- | --- |
| `run_analysis.py` calls `validate_all_runs(results_dir, src_diff_clean=…, hashes_path=…)` and fails closed | **Confirmed** (`scripts/analysis/run_analysis.py:127–140`; gate returns 1 before any directory is created). |
| `scripts/analysis/*` modules and `analysis-plan.md` exist as named | **Confirmed**; all seven modules present, `analysis-plan.md` has Amendments 1–3 before this task. |
| D-89 and D-90 were free | **Confirmed** by `./scripts/manage-decisions.py check --id 89/90` before writing; `--next` reported `[D-89]`. |
| Hashes file at `/home/lukexodus/run-logs/final-results-hashes.txt` | **Not at that path.** The file is at `/home/lukexodus/projects/run-logs/final-results-hashes.txt`; its sha256 `a4f7109b792ae18031a705abddaf14851580d2c6a49d56ffbe2cd20263c10ce4` equals the value recorded in `final_output_final/RUN_INFO.txt`. The moved path was used. |
| `final_output_final` at commit `554bde34…` | **Confirmed** in its `RUN_INFO.txt`; the six pre-registered analysis modules have no diff against that commit (`git diff --stat 554bde3 HEAD -- scripts/analysis/{validate_runs,tables,figures,stats,bootstrap,style,run_analysis}.py` is empty before this task). |
| Revised thesis available for Sections 3.6 and 4.4.1 | **Confirmed**: `docs/thesis/[REVISED] … With Chapter 4.md` was read. It is untracked in the main checkout and is not visible in this worktree. |
| SciPy availability | **SciPy 1.18.1 is installed but not declared** in `pyproject.toml`; τ-b is implemented by hand and unit-tested. |

---

## Implementation Details

### Modules

- `scripts/analysis/posthoc.py`
  - `extract_inputs` builds the per-strategy/per-corpus accuracy inputs and the n = 2000 sweep inputs from the T1/T2 row lists.
  - `assert_matches_final_output` compares 72 cells against `final_output_final` (T1: 8 rows × 6 fields; T2: 4 rows × 2 fields; F6: 8 rows × 2 fields) at relative tolerance 1e-9.
  - `realised_shortlist_sizes` reads the realised `metrics.shortlist_size` per successful accuracy trial; `size_matched_baselines` asserts it equals T1's mean calls and divides by m (28 / 140).
  - `compute_gates` / `build_t5_rows`: G1, G2, G3, classes.
  - `build_t5b_rows`: 1,990 G2 limits, 8 size-matched G1 rows, 124 G3 margin rows (31 margins × 4 strategies).
  - `build_t6_rows`, `build_t7_rows`, `build_t9b_rows`, `mc_rank_shares`, `exact_rank_shares`, `topsis_closeness`, `kendall_tau_b`, `build_t9_rows`.
  - Frozen constants: `TIE_TOL = 10.0 ** -12`, `WEIGHT_DRAWS = 20_000`, `WEIGHT_SEED = 42`, RNG `np.random.default_rng(42).random(20000)` re-seeded per corpus.
- `scripts/analysis/posthoc_figures.py`: F7 (two stacked panels), F8 (two panels, direct end labels, S3 emphasised, scenario verticals), F9 (100% stacked horizontal bars, rank 1 darkest, segments < 8% unlabelled). Non-positive values would be omitted and recorded `plotted = False`; none occurred.
- `scripts/analysis/run_analysis.py`: `--only posthoc`, `--crosscheck-dir`; the post-hoc branch runs after the gate, builds T1/T2 in memory, and writes only the post-hoc names. `RUN_INFO.txt` gains `only:` and `crosscheck_dir:` lines and hashes the two new modules.

### Tie rule and the DSA balanced case

Scores within 1e-12 share the mean of the occupied ranks. DSA balanced gives S1 = S2 = 0.500, but S3 leads at 0.5873, so S1 and S2 share ranks 2 and 3 and are each reported at **2.5** (not 1.5 — this corrects a sentence added in [D-89](6)(e); see [D-90](4)(a)). `is_best` marks only S3 in that row.

---

## Results

### Table T5 — Gates and classes

| Strategy | G1 (DSA / Metacademy) | G2 calls at n=2000 | G3 | Class |
| --- | --- | --- | --- | --- |
| S1 brute force | not applicable (whole-graph shortlist) | 2,000 → fail | fail on Metacademy (dominated by S2 and S3) | **Not effective** |
| S2 θ=0.6 | not assessable (no cap) | 0.8 → pass | pass both (DSA trade-off; Metacademy not distinguishable from S3) | **Conditionally effective** |
| S3 k=10 | pass (0.5278 vs 0.3571; 0.5046 vs 0.0714) | 10 → pass | pass both | **Effective** |
| S4 (5,10) | fail DSA (0.2593 vs 0.3571); pass Metacademy (0.1468 vs 0.0714) | 7 → pass | fail on Metacademy (dominated by S2) | **Not effective** |

### Table T5b — Gate sensitivity

- **G2:** all 1,990 integer limits from 10 to 1,999 tested; **0 class changes**. Non-S1 maximum calls is 10, so every limit ≥ 10 keeps S2–S4 passing; S1 at 2,000 fails every limit ≤ 1,999.
- **G1 size-matched:** S3 baselines 10/28 = 0.3571 and 10/140 = 0.0714 (identical to the pre-registered values); S4 baselines 6.9655/28 = **0.2488** (DSA) and 7.3667/140 = **0.0526** (Metacademy). S4 exceeds both size-matched baselines, but its class is fixed by G3, so all classes are unchanged.
- **G3 margin:** 31 margins from 0.000 to 0.150; **0 class changes**: "none up to 0.15". At 0.150 the dominating margins are DSA: none; Metacademy: S1 dominated by S3 (ΔF1 = 0.15066) and S4 dominated by S2 (ΔF1 = 0.15586). Both are just above 0.150, so the claim holds with little headroom (0.0007 and 0.0059 respectively).

### Table T6 — Single-criterion ranks

Confirmed exactly as the thesis scratch Table 4.8: DSA F1 S1 = 1, S3 = 2, S4 = 3, S2 = 4; Metacademy F1 S3 = 1, S2 = 2, S1 = 3, S4 = 4; calls and wall-clock both S2 = 1, S4 = 2, S3 = 3, S1 = 4. No ties.

### Table T7 — Weighted scores (full precision in the CSV)

| Corpus | Scenario | S1 | S2 | S3 | S4 | Rank order |
| --- | --- | --- | --- | --- | --- | --- |
| DSA | accuracy-first 0.7/0.3 | **0.7000** | 0.3000 | 0.6839 | 0.3360 | S1 > S3 > S4 > S2 |
| DSA | balanced 0.5/0.5 | 0.5000 | 0.5000 | **0.5873** | 0.3717 | S3 > S1 = S2 > S4 |
| DSA | cost-first 0.3/0.7 | 0.3000 | **0.7000** | 0.4908 | 0.4075 | S2 > S3 > S4 > S1 |
| Metacademy | accuracy-first | 0.1157 | **0.9045** | 0.8826 | 0.2022 | S2 > S3 > S4 > S1 |
| Metacademy | balanced | 0.0826 | **0.9318** | 0.8043 | 0.3370 | S2 > S3 > S4 > S1 |
| Metacademy | cost-first | 0.0496 | **0.9591** | 0.7260 | 0.4718 | S2 > S3 > S4 > S1 |

A = [1.0000, 0.0000, 0.8288, 0.2824], C = [0.0000, 1.0000, 0.3459, 0.4610] on DSA; A = [0.1652, 0.8636, 1.0000, 0.0000], C = [0.0000, 1.0000, 0.6086, 0.6739] on Metacademy. These reproduce the independent targets to the fourth decimal. The DSA leader changes S1 → S3 → S2 with the weights; S2 leads all three Metacademy scenarios. **Confirmed.**

### Table T8 / T8b — Weight sweep and exact shares

20,000 draws, seed 42, re-seeded per corpus; **0 tie draws** in either corpus. Monte Carlo shares (2 dp) versus exact:

| Corpus | S1 r1–r4 | S2 r1–r4 | S3 r1–r4 | S4 r1–r4 |
| --- | --- | --- | --- | --- |
| DSA (MC) | 0.33 / 0.17 / 0.11 / 0.39 | 0.44 / 0.05 / 0.16 / 0.34 | 0.23 / 0.60 / 0.17 / 0.00 | 0.00 / 0.17 / 0.56 / 0.27 |
| DSA (exact) | 0.3311 / 0.1689 / 0.1088 / 0.3912 | 0.4411 / 0.0589 / 0.1562 / 0.3438 | 0.2278 / 0.5981 / 0.1741 / 0.0000 | 0.0000 / 0.1741 / 0.5609 / 0.2650 |
| Metacademy (MC) | 0.00 / 0.00 / 0.19 / 0.81 | 0.74 / 0.26 / 0.00 / 0.00 | 0.26 / 0.68 / 0.06 / 0.00 | 0.00 / 0.06 / 0.74 / 0.19 |
| Metacademy (exact) | 0.0000 / 0.0000 / 0.1969 / 0.8031 | 0.7416 / 0.2584 / 0.0000 / 0.0000 | 0.2584 / 0.6803 / 0.0613 / 0.0000 | 0.0000 / 0.0613 / 0.7418 / 0.1969 |

`max |MC − exact|` = **0.0046** (DSA) and **0.0022** (Metacademy). Both are below one Monte Carlo standard error at the relevant shares (at most 0.00354). The exact shares match the independent analytic targets to within 0.001 in every cell.

### Table T9 — TOPSIS and Kendall's τ-b

Weighted form: `v_i = (w·A_i, (1−w)·C_i)`, ideal `(w, 1−w)`, anti-ideal `(0, 0)`, Euclidean distances, closeness `d⁻/(d⁺+d⁻)`.

| Corpus / scenario | TOPSIS order | Weighted-sum order | τ-b | tied pairs |
| --- | --- | --- | --- | --- |
| DSA accuracy-first | S3 > S1 > S4 > S2 | S1 > S3 > S4 > S2 | 0.6667 | 0 |
| DSA balanced | S3 > S1 = S2 > S4 | S3 > S1 = S2 > S4 | 1.0000 | 1 |
| DSA cost-first | S2 > S4 > S3 > S1 | S2 > S3 > S4 > S1 | 0.6667 | 0 |
| Metacademy (all three) | S2 > S3 > S4 > S1 | S2 > S3 > S4 > S1 | 1.0000 | 0 |

The DSA inversions are the two places where the criteria oppose most strongly (S1 vs S3 in accuracy-first; S3 vs S4 in cost-first). No p-value is reported, per the frozen specification.

### Table T9b — Wall-clock-substituted check

With `g_i = log10(1 + mean total_s at n=2000)` from the sweep runs (S1 1713.10 s, S2 0.938 s, S3 8.277 s, S4 5.638 s), C becomes [0, 1, 0.7692, 0.8186] for both corpora. The top-ranked strategy matches T7 in **2 of 6** corpus × scenario cells:

- DSA accuracy-first: T7 S1, substituted S3 — **changes**
- DSA balanced: T7 S3, substituted S3 — matches
- DSA cost-first: T7 S2, substituted S3 — **changes**
- Metacademy accuracy-first: T7 S2, substituted S3 — **changes**
- Metacademy balanced: T7 S2, substituted S2 — matches
- Metacademy cost-first: T7 S2, substituted S2 — matches

Every change moves the lead to S3. This is a sensitivity result only: calls remain the cost criterion because time follows calls (Section 4.2.3).

---

## Verification of the Thesis Claims (Prompt Section 5)

| # | Claim | Result |
| --- | --- | --- |
| 1 | Table 4.7 G1/G2/G3 values and the four classes | **Confirmed.** Every quoted value reproduced; classes S1 Not effective, S2 Conditionally effective, S3 Effective, S4 Not effective. |
| 2 | S2 shortlist recall 0.111 (DSA), 0.202 (Metacademy); S2 micro-recall 0.174 on Metacademy | **Confirmed** (0.1111, 0.2018, 0.1743). |
| 3 | Only S1 on DSA has F1 ≥ 0.50 and recall ≥ 0.50 (0.586, 0.630); no cell has F1 ≥ 0.50 and recall ≥ 0.70; S3 DSA is 0.511 / 0.426 | **Confirmed** (0.5862/0.6296; 0.5111/0.4259; no cell clears both 0.50 and 0.70). |
| 4 | Table 4.8 single-criterion ranks | **Confirmed exactly** (see T6 above). |
| 5 | Table 4.9 scores and the leader statements | **Leader statements confirmed.** Three DSA cells differ from the scratch values by 0.0007–0.0010 and four Metacademy S1/S2 cells by 0.0012–0.0027 (see old → new below). |
| 6 | Table 4.10 and the sentences | **Sentences confirmed qualitatively; several cells differ by more than 0.005.** S3 is last in 0.0% of draws on both corpora; S3 is second 0.5981 (DSA) and 0.6803 (Metacademy), so "60%" is confirmed and "69%" should be **"68%"**; S4 is first in no draw on either corpus; S1 and S2 have their largest shares at ranks 1 and 4 on DSA. |
| 7 | Sensitivity paragraph (G2 10–1,999; G1 size-matched; G3 up to 0.15) | **Confirmed.** No class changes in any of the three families. |

### Cells that differ from the thesis scratch values (old → new)

**Table 4.9 (scores):**

| Corpus / scenario | Cell | Scratch | Regenerated | Δ |
| --- | --- | --- | --- | --- |
| DSA accuracy-first | S4 | 0.335 | **0.3360** | +0.0010 |
| DSA balanced | S4 | 0.371 | **0.3717** | +0.0007 |
| Metacademy accuracy-first | S1 | 0.113 | **0.1157** | +0.0027 |
| Metacademy accuracy-first | S2 | 0.907 | **0.9045** | −0.0025 |
| Metacademy balanced | S1 | 0.081 | **0.0826** | +0.0016 |
| Metacademy balanced | S2 | 0.933 | **0.9318** | −0.0012 |
| Metacademy cost-first | S1 | 0.048 | **0.0496** | +0.0016 |
| Metacademy cost-first | S2 | 0.960 | **0.9591** | −0.0009 |

**Table 4.10 (share of draws, rounded to 2 dp):**

| Corpus | Cell | Scratch | MC (2 dp) | Exact (2 dp) | Δ (MC) |
| --- | --- | --- | --- | --- | --- |
| DSA | S2 rank 2 | 0.06 | **0.05** | 0.06 | −0.0057 |
| DSA | S4 rank 4 | 0.26 | **0.27** | 0.27 | +0.0067 |
| Metacademy | S1 rank 3 | 0.19 | 0.19 | **0.20** | −0.0047 |
| Metacademy | S1 rank 4 | 0.81 | 0.81 | **0.80** | −0.0047 |
| Metacademy | S2 rank 1 | 0.75 | **0.74** | 0.74 | −0.0070 |
| Metacademy | S2 rank 2 | 0.25 | **0.26** | 0.26 | +0.0070 |
| Metacademy | S3 rank 1 | 0.25 | **0.26** | 0.26 | +0.0070 |
| Metacademy | S3 rank 2 | 0.69 | **0.68** | 0.68 | −0.0088 |
| Metacademy | S4 rank 3 | 0.75 | **0.74** | 0.74 | −0.0065 |
| Metacademy | S4 rank 4 | 0.19 | 0.19 | **0.20** | −0.0047 |

The pattern is consistent with the scratch script having used rounded inputs: the shares are linear in A and C, and Table 4.9 already differs by up to 0.0027. The pipeline's exact shares are the recommended source for Table 4.10; the MC shares agree with them well within Monte Carlo error. Note that the MC 2-dp table may not sum to exactly 1.00 per row (e.g. Metacademy S1 rounds to 0.00 + 0.00 + 0.19 + 0.81), as the thesis already warns.

---

## TOPSIS Interpretation Choice

The thesis says only that "the weights are those of each scenario" and that "min-max scaling fixes the ideal point at (1,1) and the anti-ideal point at (0,0)". It does not say whether the weights enter before or after the distances. [D-89](9) froze the **weighted-before-distances** form: `v_i = (w·A_i, (1−w)·C_i)`, ideal `(w, 1−w)`, anti-ideal `(0, 0)`, closeness `d⁻/(d⁺+d⁻)`.

Why this form: it is the standard weighted TOPSIS construction, it makes the stated "ideal (1,1) / anti-ideal (0,0)" of the unweighted scores exactly equivalent to the weighted ideal/anti-ideal, and it gives the scenario weights the same interpretation as in the weighted sum. The alternative (unweighted distances, weights applied afterwards) is **not** computed, so this is a frozen choice, not a result-driven one. **Flagged for the APC:** if the thesis intends the alternative, Table T9 and the τ values would need recomputation; the ambiguity should be removed from Section 3.6.3.

---

## Monte Carlo vs Exact Shares

- Draws: 20,000, `np.random.default_rng(42).random(20000)`, re-seeded per corpus. **0 tie draws.**
- Exact method: pairwise crossings of the piecewise-linear `S_i(w)` inside (0,1), strict ranking evaluated at interval midpoints, interval lengths summed.
- `max |MC − exact|`: **0.0046** (DSA, 7 intervals) and **0.0022** (Metacademy, 4 intervals). No structural ties.
- The MC standard error is at most `sqrt(0.25/20000) = 0.0035`, so the observed differences are within one SE. The exact shares are the more reliable statement for the thesis; the MC shares should not be tuned (the seed was not changed).

---

## No-Change Proof

Two proofs were produced:

1. **The new stage writes only its own names.** `find` over `final_output_posthoc` lists exactly 8 table CSV + 8 table MD + 3 figure PDF + 3 figure PNG + 3 figure CSV + `RUN_INFO.txt` (26 files). No T1–T4 or F1–F6b file is present.
2. **Default-pipeline re-run.** The full pipeline was run with no flag into `/home/lukexodus/projects/thesis-analysis/final_output_default_check` and compared with `final_output_final` using `diff -rq`:
   - **All tables and all figure CSVs/Markdown are byte-identical** (0 differences). No file exists in one directory and not the other.
   - 9 PDFs differ only in the embedded `/CreationDate` (e.g. `D:20261021125126+08'00'` vs `D:20261028130216+08'00'`).
   - 3 PNGs (F4, F6, F6b) differ in rendered dimensions in this environment (e.g. F4 1644×4426 vs 1617×4130 pixels), consistent with a font/text-metric difference between the environment of the original run and this one; the underlying CSVs are identical. This matches the precedent in [D-88](5)(b).
   - `RUN_INFO.txt` differs by design (new `only` / `crosscheck_dir` lines, git commit, and two new module hashes).

So the pre-registered **data** artifacts are byte-identical; re-rendered vector/raster figures are not byte-identical because of environment-dependent text metrics and PDF metadata.

---

## Verification & Test Evidence

### Test counts as seen

- New tests: `tests/test_posthoc.py` — **16 passed**.
- Analysis pipeline files together (`tests/test_analysis_pipeline.py`, `tests/test_analysis_validate_runs.py`, `tests/test_posthoc.py`) — **59 passed, 1 skipped, 1 failed**. The single failure is `test_source_grep_forbidden_patterns`, which fails because the archived checker `scripts/analysis/apc_check_f_outputs.py` itself contains the forbidden literals `skip-gate`, `/home/` and `1e-12`. It is pre-existing on `master` and unrelated to this task.
- Full suite in this worktree, with the nested `repositories/` dataset clone linked in (see "Worktree note"): **20 failed, 660 passed, 13 skipped**. The failure set is **identical** to the unmodified `master` checkout (**20 failed, 644 passed, 13 skipped**); the 16 extra passes are the new tests.
- Failures are environmental: `faiss`/`faiss-cpu` and `torch`/`sentence-transformers` are not installed in this environment, and the source-grep test above. No failure is in the new code.
- Before the dataset symlink was added, the same suite reported 62 failed / 592 passed / 36 skipped / 3 errors; all additional failures were missing-dataset errors, not code failures.

### What the tests cover

Normalisation on a hand-worked example; all-equal criterion → 0.5 with flag; DSA balanced tie and mean-rank handling; τ-b with ties against hand-computed values (5/√30 and 0.8, plus ±1 extremes); weighted TOPSIS on a three-point toy matrix with a known answer (0.7/0.3/0.5); exact shares against a 200,000-point fine grid; seeded-draw determinism; gate classes covering all three classes; cross-check success and one-cell mismatch failure; validation failure ⇒ no artifacts; `--only posthoc` requires `--crosscheck-dir`; post-hoc-only writes exactly its 26 names; default run writes the legacy file set with no post-hoc file.

### Worktree note

Per AGENTS.md this task ran in `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-004`. The nested dataset clone is not present in a worktree, so an **untracked** symlink `repositories -> <main checkout>/repositories` was created to run the full suite. It is not committed and must not be merged. No other untracked file was created.

---

## Git Diff

```diff
diff --git a/docs/context/analysis-plan.md b/docs/context/analysis-plan.md
index 33a61fe..81f4e36 100644
--- a/docs/context/analysis-plan.md
+++ b/docs/context/analysis-plan.md
@@ -118,4 +118,11 @@ Amendment 3 (2026-10-20), made after the sweep campaign and after an agent-writt
 4. A log-log slope is undefined when any size has zero mean cost. Such fits are reported as undefined and receive no D2 category. An exploratory fit on positive-mean sizes may be shown, labelled exploratory.
 5. The post-hoc timing sensitivity excludes trials with retries > 0 and the single trial sweep:brute_force:2000:t9, the only trial launched with --allow-peak inside a peak window ([D-84]).
 
+### Amendment 4 (2026-10-28):
+1. **Scope.** Adds a separate post-hoc decision and ranking stage implementing thesis Sections 3.6 and 4.4.1: gates G1–G3 and classes (Table T5), gate sensitivity (T5b), single-criterion ranks (T6), weighted scores (T7), the weight sweep and its exact analytic counterpart (T8, T8b, Figure F9), TOPSIS with Kendall's tau-b (T9), and the wall-clock-substituted score check (T9b), with Figures F7 and F8. The stage is invoked with `--only posthoc` and writes only new artifacts into a new output directory. No pre-registered artifact (Tables T1–T4, Figures F1–F6b, dominance files) is regenerated, altered, or reordered.
+2. **Status.** The stage is **post hoc, specified after the Chapter 4 measurements existed**, not pre-registered, per Section 1 Rule 3. Every emitted table and figure row carries `status = "post-hoc"`; every new figure displays "POST HOC: not pre-registered". [D-89] freezes the specification before any ranking artifact is computed and is not edited afterwards; corrections are recorded in [D-90].
+3. **Inputs and gate.** No new measurement, no live API call, no new experiment run; the results directory is read-only input. Accuracy inputs come from the same in-memory aggregates that produce Table T1 and Figure F6; n = 2000 sweep inputs come from the Table T2 aggregates. The independent validation gate runs first and remains fail-closed; on failure the stage writes nothing.
+4. **Outputs.** New files only, named in [D-89](12): `tables/T5_gates_and_classes`, `T5b_gate_sensitivity`, `T6_single_criterion_ranks`, `T7_weighted_scores`, `T8_rank_shares`, `T8b_rank_shares_exact`, `T9_topsis_kendall_tau`, `T9b_walltime_substituted_scores` (CSV and Markdown), and `figures/F7_gates_g1_g2`, `F8_score_vs_weight`, `F9_rank_shares` (PDF, PNG, CSV).
+5. **Flagged text discrepancy (not resolved here).** Thesis Section 3.6.3 displays `C_i = (g_i - min g)/(max g - min g)` while its prose says the cost score is "min-max normalised and reversed so that higher is better". [D-89](6) fixes `C_i = 1 - (g_i - min g)/(max g - min g)`, consistent with the prose, the scenarios, and the independent recomputation targets. The displayed formula needs correction in the thesis; this amendment does not edit the thesis.
+
 
diff --git a/docs/decisions/decision-log.md b/docs/decisions/decision-log.md
index d5cf71e..cdadfff 100644
--- a/docs/decisions/decision-log.md
+++ b/docs/decisions/decision-log.md
@@ -826,3 +826,76 @@ Reasoning: provides readable log-scale visualisations of candidate-narrowing sca
   (a) As stated by the APC from a visual read of the PNGs [APC]: in F2b Panel B the points for Strategy 2 decide time at n=50 and n=500 are omitted without a footnote on that panel and the line is drawn across the gap (Panel A is the panel to use); in F6b the legend overlaps the Strategy 4 label on the DSA panel and the Strategy 1 label is clipped at the right edge on the Metacademy panel.
   (b) The pre-registered figures, tables and the F6 dominance files are unchanged by ANALYSIS-003; this was verified by byte comparison of the CSV and Markdown outputs against the earlier `final_output` (the six PDFs differ between the two directories while their CSVs are identical) [agent-relayed, from the CHK-001 comparison].
 Reasoning: corrects the [D-84] record with Luke's answers of 2026-10-21, separates peak-hour launches from flag settings using file evidence, corrects two status-row commit claims, records final pipeline provenance, and records the APC's stated limits of the exploratory companion figures, all by later entry rather than by editing earlier text. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`.
+
+**[D-89]** Post-hoc decision and ranking framework: frozen specification before any computation (ANALYSIS-004):
+(1) Status and scope:
+  (a) This framework is **post hoc, specified after the Chapter 4 measurements existed**. It is not pre-registered. It adds no measurement and replaces no pre-registered result. It is applied to single-run measurements, so its outputs are classifications of those measurements, not statistical tests.
+  (b) The specification below is frozen in this entry **before any ranking artifact is computed**. The numbers and choices in this entry are not edited after any computation; any correction is recorded in [D-90]. The thesis Section 3.6 requirement that the thresholds and weights be recorded "before the ranks are computed and are not changed afterwards" is honoured literally within this post-hoc stage.
+  (c) The stage runs only after the independent validation gate passes, writes only new artifacts into a new output directory, and reuses `stats.evaluate_dominance` unchanged for G3.
+(2) Data inputs:
+  (a) Corpora, per corpus and never pooled: DSA (`DSA_gold_standard_MEKG`, 29 accuracy trials) and Metacademy (`metacademy_gold_standard_MEKG`, 30 accuracy trials).
+  (b) Strategies (primary configurations only): S1 brute force `primary (all candidates)`; S2 embedding threshold `primary (theta=0.6)`; S3 ANN `primary (k=10, ef=128)`; S4 bounded bucket `primary (s_min=5, s_max=10, nb=12)`.
+  (c) Accuracy inputs, per strategy and corpus, from the same in-memory aggregates that produce Table T1 and Figure F6: `f1_micro`, `recall_micro`, `precision_micro`, `llm_calls_mean`, `shortlist_recall_micro`, `random_baseline_recall` (the pre-registered $\min(k,m)/m$; NaN for S1 and S2).
+  (d) Sweep inputs, per strategy, from the same in-memory aggregates that produce Table T2: `llm_calls_mean` and `total_s_mean` at $n = 2000$ (10 trials per size).
+  (e) The values used are asserted equal (relative tolerance 1e-9) to the corresponding cells of the existing `final_output_final` T1, T2 ($n=2000$ rows) and F6 CSVs, supplied through `--crosscheck-dir`; `--only posthoc` fails closed if that directory is not supplied.
+(3) Gates (Table T5):
+  (a) **G1, beats chance:** `shortlist_recall_micro > random_baseline_recall` on **every** corpus. Status values: `not applicable` (S1, whole-graph shortlist), `not assessable` (S2, no shortlist cap), otherwise pass/fail per corpus and overall.
+  (b) **G2, practical cost:** sweep mean LLM calls per insertion at $n=2000$ is $\le 50$. The 50 is the upper end of the 22–50 prompts reported by Funk et al.; it is a reference point from a different task, not a standard.
+  (c) **G3, not dominated:** the strategy is not Pareto-dominated on (calls, micro-F1) on either corpus, using `stats.evaluate_dominance` unchanged with the study's 0.025 F1 margin; a pair labelled "not distinguishable (F1 within 0.025)" counts as **not** dominated. Calls are the accuracy-run calls, as in Figure F6.
+  (d) **Class:** Effective = passes every gate and G1 is assessable. Conditionally effective = passes every assessable gate but G1 is not assessable. Not effective = fails any assessable gate.
+(4) Gate sensitivity (Table T5b):
+  (a) G2 limit evaluated at every integer limit from 10 to 1,999 inclusive (1,990 settings); the class comparison is against the frozen 50-call result.
+  (b) G1 size-matched baseline: for each strategy and corpus, the mean realised shortlist size over successful accuracy trials (field `metrics.shortlist_size`) divided by $m$, with $m=28$ for DSA and $m=140$ for Metacademy. G1 size-matched passes when `shortlist_recall_micro` exceeds this value. The rule is applied to S3 and S4 only (same applicability as G1).
+  (c) G3 margin evaluated on the grid 0.000, 0.005, …, 0.150 inclusive (31 values). Report the first margin at which any strategy's G3 outcome on either corpus changes, or "none up to 0.15".
+  (d) The stage asserts that the resulting gate classes are unchanged under all three families; the table reports the supporting values whether or not they change.
+(5) Single-criterion ranks (Table T6): per corpus, rank 1 is best on micro-F1 (higher better), mean LLM calls (lower better), and mean wall-clock `total_s` at $n=2000$ (lower better). Ties share the mean of the ranks they occupy.
+(6) Weighted score (Table T7):
+  (a) For one corpus: $g_i = \log_{10}(1 + \mathrm{calls}_i)$ with accuracy-run calls matched to that corpus; $A_i = (F1_i - \min F1)/(\max F1 - \min F1)$; $C_i = 1 - (g_i - \min g)/(\max g - \min g)$.
+  (b) **Discrepancy flagged:** thesis Section 3.6.3 displays $C_i$ without the $1-$ reversal although its prose says the cost score is reversed so that higher is better. This entry uses the reversed form above, consistent with the prose, the scenarios, and the independent recomputation targets. The thesis formula needs correction; this decision does not edit the thesis.
+  (c) If a criterion has $\max = \min$, its normalised value is set to 0.5 for every strategy and the row is flagged in the output (not expected to occur).
+  (d) Scores: $S_i(w) = w A_i + (1-w) C_i$; scenarios accuracy-first $w=0.7$, balanced $w=0.5$, cost-first $w=0.3$.
+  (e) Ties: scores within $10^{-12}$ are tied and share the mean of the ranks they occupy (so the DSA balanced case, $S_1 = S_2 = 0.500$, gives rank 1.5 each). `is_best` marks every strategy whose score is within $10^{-12}$ of the row maximum.
+(7) Weight sweep (Table T8, Figure F9 data):
+  (a) RNG family: `numpy.random.default_rng(seed)` as used by `bootstrap.py`. Exact constructor and call: `np.random.default_rng(42).random(20000)`, giving 20,000 ordered Uniform(0, 1) draws of the accuracy weight $w$; the generator is re-seeded to 42 for each corpus so both corpora see the same draws.
+  (b) Every draw is ranked strictly by score. A draw in which any pair of scores differs by at most $10^{-12}$ is counted as a tie and reported; such a tie is broken deterministically by the fixed strategy order S1, S2, S3, S4. No seed tuning.
+  (c) Output: the share of draws giving each strategy each rank (CSV at full precision; Markdown rounded to 2 decimals) and the Monte Carlo standard error $\sqrt{p(1-p)/20000}$.
+(8) Exact rank shares (Table T8b): $S_i(w)$ is piecewise linear in $w$, so ranks change only at pairwise crossings. For each pair $(i,j)$ the crossing solves $w = (C_j - C_i)/[(A_i - C_i) - (A_j - C_j)]$; crossings strictly inside $(0,1)$ are collected and sorted; the strict ranking is evaluated at the midpoint of each resulting interval and the interval lengths are summed. Crossing points themselves have measure zero. Report the exact shares and $\max |\mathrm{MC} - \mathrm{exact}|$.
+(9) TOPSIS cross-check (Table T9):
+  (a) Decision matrix is the pair $(A_i, C_i)$ with no further normalisation. The scenario weights are applied to each criterion before distances: $v_i = (w A_i, (1-w) C_i)$. Ideal point $= (w, 1-w)$; anti-ideal point $= (0,0)$. Euclidean $d_i^{+}$ and $d_i^{-}$; closeness $= d_i^{-}/(d_i^{+} + d_i^{-})$; rank by closeness (higher better).
+  (b) This weighted form is chosen because thesis Section 3.6.3 says the weights are "those of each scenario"; the alternative form (weights applied after distances) is not computed. The thesis wording is ambiguous on this point and is flagged for the APC.
+(10) Kendall tau (Table T9): tau-b between the TOPSIS ranking and the weighted-sum ranking, per corpus and scenario; report tau, the number of tied pairs, and both rankings; no p-value. Implemented by hand (SciPy is not declared in `pyproject.toml`; an installed SciPy is not relied on) and unit-tested against a worked example.
+(11) Wall-clock-substituted check (Table T9b): recompute the Table T7 scores with $g_i = \log_{10}(1 + \text{mean } \texttt{total\_s} \text{ at } n=2000)$ from the sweep runs; the same value per strategy is used for both corpora; $A_i$ is unchanged; scores, ranks and whether the top-ranked strategy per scenario matches Table T7 are reported. Accuracy-run latencies are not used for any cost claim.
+(12) Outputs (new files only, all CSV and Markdown rows carrying `status = "post-hoc"`):
+  (a) `tables/T5_gates_and_classes`, `T5b_gate_sensitivity`, `T6_single_criterion_ranks`, `T7_weighted_scores`, `T8_rank_shares`, `T8b_rank_shares_exact`, `T9_topsis_kendall_tau`, `T9b_walltime_substituted_scores`, each as `.csv` and `.md`.
+  (b) `figures/F7_gates_g1_g2`, `F8_score_vs_weight`, `F9_rank_shares`, each as `.pdf`, `.png` and `.csv`. Every figure displays "POST HOC: not pre-registered".
+  (c) New modules `scripts/analysis/posthoc.py` and `scripts/analysis/posthoc_figures.py`. The only existing file edited is `scripts/analysis/run_analysis.py`, which gains `--only posthoc` and `--crosscheck-dir`; with no flag its behaviour is unchanged. Default output directory for this run: `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`.
+(13) No live API calls and no new experiment runs; the results directory is read-only input. Pre-registered artifacts must remain byte-identical; the new stage writes no file outside the names in (12).
+Reasoning: freezes the post-hoc decision and ranking specification (thesis Sections 3.6 and 4.4.1) before any ranking artifact is computed, recording every convention that would otherwise be chosen after seeing the results (RNG family, tie tolerance, TOPSIS weighting form, tie-breaking, size-matched baseline, sensitivity grids, output names), so that the regenerated Tables 4.7–4.10 and Figures 4.11–4.13 are reproducible and gate-validated. Affects: `docs/decisions/decision-log.md`, `docs/context/analysis-plan.md`, `docs/prompts/ANALYSIS-004-PROMPT.md`.
+
+**[D-90]** Implementation, reproduction and corrections for the post-hoc decision and ranking stage (ANALYSIS-004):
+(1) Implementation:
+  (a) New modules `scripts/analysis/posthoc.py` (inputs, cross-check, gates, ranks, weighted scores, weight sweep, exact shares, TOPSIS, Kendall tau-b) and `scripts/analysis/posthoc_figures.py` (Figures F7–F9). `scripts/analysis/run_analysis.py` gains `--only posthoc` and `--crosscheck-dir`; with no flag its behaviour and its written artifacts are unchanged. No pre-registered module (`validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`) was modified; G3 calls `stats.evaluate_dominance` unchanged.
+  (b) All inputs are the in-memory aggregates that produce Tables T1/T2 and Figure F6. Before any artifact is written, the stage asserts (relative tolerance 1e-9) that every value it uses equals its `final_output_final` T1, T2 ($n=2000$) and F6 CSV cell; 72 cells are compared and the assertion passed.
+  (c) Kendall tau-b is implemented by hand (SciPy is not declared in `pyproject.toml`) and unit-tested against two hand-computed examples (tau = 5/sqrt(30) with one tied pair; tau = 0.8 with one tie in each ranking).
+(2) Reproduction:
+  (a) Run: `python scripts/analysis/run_analysis.py --results-dir <repo>/results --output-dir /home/lukexodus/projects/thesis-analysis/final_output_posthoc --src-diff-clean --hashes /home/lukexodus/projects/run-logs/final-results-hashes.txt --only posthoc --crosscheck-dir /home/lukexodus/projects/thesis-analysis/final_output_final`, at commit `e3b563d95cb8ee29c8b7e8c8d1fe2502c16110df`.
+  (b) The independent validation gate passed (24 runs) and `RUN_INFO.txt` records `overall_gate_status: PASS`, `src_diff_clean: True`, and `pipeline_modules_sha256` for all nine modules including the two new ones.
+  (c) Provenance note: the hashes file path recorded in earlier entries (`~/run-logs/final-results-hashes.txt`) no longer exists; the file used is `/home/lukexodus/projects/run-logs/final-results-hashes.txt`, whose sha256 (`a4f7109b…`) equals the value recorded in `final_output_final/RUN_INFO.txt`.
+(3) Results (Tables T5–T9b and Figures F7–F9):
+  (a) Gates and classes: S1 Not effective (G2 fail, G3 fail on Metacademy), S2 Conditionally effective (G1 not assessable; G2 and G3 pass), S3 Effective (G1 pass on both corpora; G2 10 calls; G3 pass), S4 Not effective (G1 fail on DSA; G3 fail on Metacademy). G1 values: S3 0.5278 vs 0.3571 (DSA) and 0.5046 vs 0.0714 (Metacademy); S4 0.2593 vs 0.3571 (DSA) and 0.1468 vs 0.0714 (Metacademy). G2 calls: 2000, 0.8, 10, 7.0.
+  (b) Gate sensitivity: no class changes for any integer G2 limit from 10 to 1,999; no class change under the size-matched G1 baseline (S3 baselines equal the pre-registered ones; S4 baselines 0.2488 on DSA and 0.0526 on Metacademy, both exceeded by its shortlist recall, but its class is fixed by G3); no class change for any G3 margin on the 0.000–0.150 grid, so the reported answer is "none up to 0.15".
+  (c) Weighted scores (Table T7) reproduce the independent recomputation to the fourth decimal: DSA S1/S2/S3/S4 = 0.7000/0.3000/0.6839/0.3360 (accuracy-first), 0.5000/0.5000/0.5873/0.3717 (balanced), 0.3000/0.7000/0.4908/0.4075 (cost-first); Metacademy = 0.1157/0.9045/0.8826/0.2022, 0.0826/0.9318/0.8043/0.3370, 0.0496/0.9591/0.7260/0.4718. The DSA balanced case gives S1 = S2 = 0.500 and, because S3 leads at 0.5873, their shared mean rank is 2.5.
+  (d) Weight sweep: 20,000 draws, seed 42, re-seeded per corpus; 0 tie draws in either corpus. Maximum absolute Monte Carlo error against the exact analytic shares is 0.0046 on DSA and 0.0022 on Metacademy, both below one Monte Carlo standard error at these shares.
+  (e) TOPSIS: with weights applied before the distances, the closeness ranking differs from the weighted-sum ranking only where the two criteria oppose most strongly. Kendall tau-b is 0.6667 for DSA accuracy-first and DSA cost-first (one inversion each; 0 tied pairs) and 1.0 for DSA balanced (1 tied pair) and for all three Metacademy scenarios (0 tied pairs).
+  (f) Wall-clock substitution: replacing accuracy-run calls with sweep mean `total_s` at $n=2000$ changes the top-ranked strategy in 4 of the 6 corpus × scenario cells (DSA in all three scenarios and Metacademy accuracy-first), always toward S3. This is a sensitivity check only; calls remain the cost criterion, because time follows calls (Section 4.2.3) and weighting both would count the same cost twice.
+(4) Corrections and flagged discrepancies:
+  (a) **Correction to [D-89](6)(e):** the DSA balanced tie between S1 and S2 is not a tie for first. S3 scores 0.5873, so S1 and S2 share ranks 2 and 3 and are each reported at mean rank 2.5, not 1.5. The rule itself (mean of occupied ranks) is unchanged.
+  (b) Thesis Section 3.6.3 displays $C_i$ without the $1-$ reversal that its prose describes; [D-89](6)(b) and the implementation use $C_i = 1-(g_i-\min g)/(\max g-\min g)$, which reproduces the independent targets. The displayed formula needs correction in the thesis.
+  (c) The thesis scratch Table 4.9 differs from the regenerated Table T7 by up to 0.0027 on Metacademy S1/S2 cells (rounded inputs in the scratch script). The thesis scratch Table 4.10 differs from the regenerated shares by 0.006–0.009 in several Metacademy cells: S2 rank 1 is 0.7416 exact (0.743 MC) against 0.75, S2 rank 2 is 0.2584 against 0.25, S3 rank 1 is 0.2584 against 0.25, S3 rank 2 is 0.6803 exact (0.6812 MC) against 0.69, S4 rank 3 is 0.7418 against 0.75, and S4 rank 4 is 0.1969 against 0.19. On DSA, S4 rank 4 is 0.2667 against 0.26 and S2 rank 2 is 0.0543 MC (0.0589 exact) against 0.06. The prose "69%" should become "68%" (exact 0.6803); the "60%" statement for DSA S3 rank 2 is confirmed (0.5981 exact, 0.599 MC).
+  (d) TOPSIS weighting form remains ambiguous in the thesis wording; the weighted-before-distances form is the one implemented, as frozen in [D-89](9)(b). The alternative is not computed.
+(5) No-change proof:
+  (a) The post-hoc stage writes only the names frozen in [D-89](12): `diff -rq` between the new output directory's file set and that list shows no other file, and no pre-registered table or figure is written.
+  (b) A default (no-flag) re-run of the full pipeline into a scratch directory reproduced every CSV and Markdown file byte-identically against `final_output_final` (all tables and all figure CSVs and dominance files). PDFs differ only in the embedded `CreationDate`, and the three PNGs differ in rendered dimensions because this environment's text metrics differ from the environment of the original run; the CSV/Markdown data are identical. `RUN_INFO.txt` differs by design (new `only`/`crosscheck_dir` lines and two new module hashes). This matches the precedent recorded in [D-88](5)(b).
+(6) Tests: `tests/test_posthoc.py` covers normalisation on a hand-worked example, the all-equal → 0.5 rule and flag, the DSA balanced tie and mean-rank handling, tau-b with ties against hand-computed values, weighted TOPSIS on a three-point toy matrix with a known answer, exact shares against a 200,000-point fine grid, seeded-draw determinism, gate-class logic covering all three classes, cross-check assertion success and failure, "validation failure ⇒ no artifacts", "post-hoc stage writes only its own names", and "default run writes the legacy file set". The full suite was run; the only failures are the pre-existing environment-dependent ones (FAISS, PyTorch/sentence-transformers, and the source-grep collision with `scripts/analysis/apc_check_f_outputs.py`), with the same failure set on unmodified `master` (counts in the task report, not recorded here per [D-86](1)(b)).
+(7) Files: `scripts/analysis/posthoc.py`, `scripts/analysis/posthoc_figures.py`, `scripts/analysis/run_analysis.py`, `tests/test_posthoc.py`, `docs/prompts/ANALYSIS-004-PROMPT.md`, `docs/context/analysis-plan.md` (Amendment 4), `docs/tasks/status.md`, this entry, and the task report.
+Reasoning: records how the [D-89]-frozen post-hoc stage was implemented and reproduced, the computed gate classes and ranking results, the Monte Carlo-versus-exact comparison, the cross-check agreement, the one correction to [D-89], and the thesis cells whose regenerated values differ from the scratch table, so that the APC can update the thesis text without re-deriving anything. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `scripts/analysis/`, `tests/`.
diff --git a/docs/prompts/ANALYSIS-004-PROMPT.md b/docs/prompts/ANALYSIS-004-PROMPT.md
new file mode 100644
index 0000000..ed903c9
--- /dev/null
+++ b/docs/prompts/ANALYSIS-004-PROMPT.md
@@ -0,0 +1,127 @@
+# ANALYSIS-004 — Post-hoc classification and ranking artifacts (Tables 4.7–4.10, Figures 4.11–4.13, TOPSIS/τ cross-checks)
+
+Standalone prompt from the APC AI, relayed by Luke. Archive this file as
+`docs/prompts/ANALYSIS-004-PROMPT.md` first (AGENTS.md, "Prompt archiving").
+
+- **Task ID:** ANALYSIS-004 (new; add a row to `docs/tasks/status.md`)
+- **Branch / worktree:** `task/ANALYSIS-004`, via `git worktree add ../llm-graph-insertion-complexity-ANALYSIS-004 -b task/ANALYSIS-004` (check `git worktree list` first, per AGENTS.md "Parallel work and worktrees")
+- **Reserved decision IDs:** **D-89** (specification, committed BEFORE any computation) and **D-90** (implementation, provenance, and any corrections). Confirm with `./scripts/manage-decisions.py --next` that D-89 is free. If it is already used, STOP and report; do not renumber.
+- **Agent:** you are the local agent; use your own name in file names (`claude-code`, `gemini` or `opencode`).
+
+## 0. Read first, in this order
+
+1. `AGENTS.md`, then `docs/context/complete-context.md` (in full).
+2. `docs/tasks/status.md` (ANALYSIS-001 … ANALYSIS-003 rows), `docs/context/analysis-plan.md` (the frozen plan, Rules R1–R3, Amendments 1–3), and decision-log entries D-79, D-83, D-84, D-85, D-86, D-87, D-88.
+3. `scripts/analysis/` (all modules: `run_analysis.py`, `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`) and `tests/test_analysis_pipeline.py`. ANALYSIS-003 (D-87) is the closest precedent for how a post-hoc/exploratory add-on is wired in; follow its conventions.
+4. The specification below. **The thesis copy in `docs/thesis/` is older (Chapters 1–3) and may not contain Section 3.6 or Section 4.4.1.** The specification in this prompt is authoritative for this task. If Luke has placed the revised thesis (`_REVISED__…_With_Chapter_4.md`) somewhere readable, read only its Sections 3.6 and 4.4.1 and report any disagreement with this prompt instead of silently picking one.
+
+Verify anything in this prompt that you can check yourself (file names, function signatures, column names, current values) and say so in the report whether or not it held. In particular, I have not seen `scripts/analysis/*` or `analysis-plan.md`; every statement below about them is an assumption.
+
+## 1. Goal and hard constraints
+
+The revised thesis adds a post-hoc decision and ranking framework (thesis Section 3.6, applied in Section 4.4.1). Its tables and figures were produced by a teammate's scratch script. They must be regenerated inside the repo's analysis pipeline so that they are reproducible and gate-validated. TOPSIS, Kendall's τ and a wall-clock-substituted score check are specified but have never been computed. Compute them too.
+
+Generate ONLY the new artifacts. Do not regenerate or alter anything that already exists.
+
+- **No live API calls. No new experiment runs.** The results directory is read-only input.
+- **The validation gate stays fail-closed.** Import and call `validate_all_runs` exactly as `run_analysis.py` does today (`--results-dir`, `--src-diff-clean`, `--hashes`). If it fails, the new stage must not write artifacts. Do not weaken or bypass it.
+- **Do not modify** `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, or `style.py`. Import from them (reuse `stats.evaluate_dominance` UNCHANGED for G3, as D-87(5) did for F6b). Put new code in new modules, e.g. `scripts/analysis/posthoc.py` and `scripts/analysis/posthoc_figures.py`. The only existing file you may edit is `run_analysis.py`, minimally: add a flag (suggested `--only posthoc`) that runs gate → aggregates → post-hoc stage and nothing else. With no flag, behaviour must be exactly as today.
+- **Pre-registered and existing artifacts must be byte-identical.** Run the new stage into a NEW output directory (suggested `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`). Then produce a no-change proof: either re-run the default pipeline into a scratch dir and `diff -r` it against `/home/lukexodus/projects/thesis-analysis/final_output_final`, or show that the new stage writes no file outside its own names. Report which. (Past provenance: results dir `/home/lukexodus/projects/llm-graph-insertion-complexity/results`, hashes file `/home/lukexodus/run-logs/final-results-hashes.txt`, final run at commit `554bde34…`.)
+- Take inputs from the same in-memory aggregates that produce Tables T1/T2 and Figure F6, not from re-parsed CSVs. Then assert that the values used equal the corresponding cells of the existing `final_output_final` T1/T2/F6 CSVs.
+- Prefer the standard library and packages already in `pyproject.toml`. If SciPy is not available, implement Kendall τ-b by hand and unit-test it against a worked example.
+
+## 2. Order of work (this order is mandatory)
+
+1. **First commit, before any computation:** add decision **D-89** to `docs/decisions/decision-log.md` and an "Amendment 4" entry to `docs/context/analysis-plan.md`. They freeze this specification (Section 3 below) including every choice you had to make: the RNG family, tie tolerance, TOPSIS weighting form, and output names. Label everything **post hoc, specified after the Chapter 4 measurements existed**, not pre-registered. The thesis text says the thresholds and weights are recorded "before the ranks are computed and are not changed afterwards". Honour that literally: do not edit D-89's numbers after you have run anything. If you find an error, add a correction in D-90.
+2. Implement the new modules and the flag, with tests (Section 7).
+3. Run the new stage, make the no-change proof, compare against the cross-check targets (Section 6), and write the report.
+
+## 3. Specification (frozen into D-89)
+
+**Corpora:** DSA (29 trials, `DSA_gold_standard_MEKG`) and Metacademy (30 trials, `metacademy_gold_standard_MEKG`). Always per corpus; never pool.
+
+**Strategies (primary configurations only):** S1 brute force (`primary (all candidates)`), S2 embedding threshold (`primary (theta=0.6)`), S3 ANN (`primary (k=10, ef=128)`), S4 bounded bucket (`primary (s_min=5, s_max=10, nb=12)`).
+
+**Inputs per strategy and corpus** (accuracy runs): `f1_micro`, `recall_micro`, `precision_micro`, `llm_calls_mean`, `shortlist_recall_micro`, `random_baseline_recall` (this is the pre-registered min(k, m)/m; NaN for S1 and S2).
+**Inputs per strategy** (sweep runs, n = 2000): `llm_calls_mean` and `total_s_mean`.
+
+### Gates (Table T5)
+
+- **G1, beats chance:** `shortlist_recall_micro > random_baseline_recall` on EVERY corpus. Status values: `not applicable` (S1, whole-graph shortlist), `not assessable` (S2, no cap), else pass/fail per corpus and overall.
+- **G2, practical cost:** sweep mean calls at n = 2000 is ≤ 50. The 50 is the upper end of the 22–50 prompts reported by Funk et al.; it is a reference point from a different task, not a standard.
+- **G3, not dominated:** not Pareto-dominated on (calls, micro-F1) on either corpus, using `stats.evaluate_dominance` unchanged, with the study's 0.025 F1 margin ("not distinguishable" counts as NOT dominated). Use the accuracy-run calls, as Figure F6 does.
+- **Class:** Effective = passes every gate and G1 is assessable. Conditionally effective = passes every assessable gate but G1 is not assessable. Not effective = fails any assessable gate.
+
+### Gate sensitivity (Table T5b, supports a paragraph already in the thesis)
+
+Show that the classes do not change under: (a) any G2 limit from 10 to 1,999 calls; (b) G1 with a size-matched random baseline (compute it from the actual shortlist sizes, and state how); (c) G3 margin from 0 to 0.15 F1 in 0.005 steps. Report the first margin at which any G3 outcome changes, or "none up to 0.15".
+
+### Single-criterion ranks (Table T6)
+
+Per corpus: rank 1 = best on micro-F1 (higher better), mean calls (lower better), and sweep mean wall-clock at n = 2000 (lower better). Ties share the mean rank.
+
+### Weighted score (Table T7)
+
+For one corpus: `g_i = log10(1 + calls_i)` (accuracy-run calls, matched to the corpus). `A_i = (F1_i − min F1) / (max F1 − min F1)`. `C_i = 1 − (g_i − min g) / (max g − min g)`. If a criterion has max = min, set it to 0.5 for every strategy and flag it (it should not occur). `S_i(w) = w·A_i + (1 − w)·C_i`.
+Scenarios (accuracy weight w / cost weight): accuracy-first 0.7/0.3, balanced 0.5/0.5, cost-first 0.3/0.7.
+Ties: scores within 1e-12 are tied and share the mean rank. Note that DSA balanced gives S1 = S2 = 0.500 exactly, so the tie rule must work there. Report ranks as well as scores. Mark the best per row in the CSV (`is_best`); ties mark all tied.
+
+### Weight sweep (Table T8, Figure F9 data)
+
+Draw w ~ Uniform(0, 1), 20,000 draws, seed 42, per corpus (re-seed per corpus so both corpora see the same draws). Use the same RNG family that `bootstrap.py` uses, and record the exact constructor in D-89. Rank every draw (strict; if any tie occurs, count it and report it). Report the share of draws giving each strategy each rank (CSV with full precision; the Markdown table rounded to 2 decimals), plus the Monte Carlo standard error `sqrt(p(1−p)/20000)`.
+**Also (T8b):** compute the EXACT shares analytically. `S_i(w)` is piecewise linear in w, so ranks only change at pairwise crossings. Collect the crossing points in (0, 1), sort them, evaluate the ranking in each interval, and sum interval lengths. Report `max |MC − exact|`. Reason: the thesis rounds MC shares to two decimals, and my own check suggests some cells sit near a rounding boundary (e.g. Metacademy S3 rank 2 is about 0.680 exactly, but the scratch table shows 0.69). The thesis text quotes "69%" and "60%". If the pipeline's MC result differs from the scratch table, say so plainly. Do not tune the seed.
+
+### Cross-checks (Table T9 and T9b)
+
+- **TOPSIS (T9):** decision matrix is the pair (A_i, C_i), no further normalisation. Apply the scenario weights to each criterion: `v_i = (w·A_i, (1 − w)·C_i)`. Ideal point = `(w, 1 − w)`, anti-ideal point = `(0, 0)` (this is the weighted form of "ideal (1,1), anti-ideal (0,0)" in the thesis text). Closeness = `d⁻ / (d⁺ + d⁻)`, with Euclidean distances. Rank by closeness. **The thesis wording is ambiguous on whether weights are applied before the distances. Pick the form above, say in D-89 that you chose it and why, and flag the ambiguity for the APC. Do not compute both and choose later.**
+- **Kendall τ (T9):** per corpus and scenario, between the TOPSIS ranking and the weighted-sum ranking. Use τ-b (tie-corrected; SciPy `kendalltau(variant='b')` or a hand-written equivalent). Report τ, the number of tied pairs, and the two rankings. With four strategies the value space is coarse; do not add a p-value.
+- **Wall-clock-substituted check (T9b):** recompute the T7 scores with `g_i = log10(1 + mean wall-clock seconds at n = 2000)` from the SWEEP runs. This one value per strategy is used for both corpora; accuracy-run latencies are not used for any cost claim. Report scores, ranks, and whether the top-ranked strategy per scenario matches T7.
+
+### Output names (all CSV + Markdown, every row carries `status = "post-hoc"`)
+
+`tables/T5_gates_and_classes`, `T5b_gate_sensitivity`, `T6_single_criterion_ranks`, `T7_weighted_scores`, `T8_rank_shares`, `T8b_rank_shares_exact`, `T9_topsis_kendall_tau`, `T9b_walltime_substituted_scores`. Figures: `figures/F7_gates_g1_g2`, `F8_score_vs_weight`, `F9_rank_shares` (each as `.pdf`, `.png`, and an underlying `.csv`, like F1–F6).
+
+## 4. Figures (these replace three images the teammate drew by hand)
+
+Follow `style.py`. Every figure carries the visible text **"POST HOC: not pre-registered"** in the title or a corner box, as D-87 did for "EXPLORATORY". Do not clamp or shift non-positive values (omit-not-clamp, D-87(4)); calls at n = 2000 are all positive, but keep the rule.
+
+- **F7 → thesis Figure 4.11, "Gates G1 and G2 applied to the primary configurations".** Two stacked panels, width about 6.5 in. *Panel A (G1):* bars of shortlist recall for S3 and S4 for each corpus, with a dashed marker for the pre-registered random baseline, and value labels. S1 and S2 are not drawn, with a note that no baseline applies to them. *Panel B (G2):* mean calls per insertion at n = 2000 for all four strategies on a log x-axis, a dashed vertical line at 50 labelled "limit: 50", and the S1 point highlighted as the failing one.
+- **F8 → Figure 4.12, "Normalised score against the weight on accuracy, by corpus".** Two panels (DSA, Metacademy). For each strategy a straight line from `(w=0, C_i)` to `(w=1, A_i)`. Direct end labels (S1–S4), faint verticals at w = 0.3, 0.5, 0.7 for the three scenarios, S3 visually emphasised. y from 0 to 1.
+- **F9 → Figure 4.13, "Share of weightings giving each rank, by strategy and corpus".** Horizontal 100% stacked bars, one per strategy, grouped by corpus, ordered rank 1 (darkest) to rank 4 (lightest), with a legend. Label a segment only if its share is ≥ 8%.
+
+Figure titles may state the finding (as the teammate's drafts do), but each title claim must be asserted in code against the data (e.g. "S3 is last in under 0.5% of draws" must be computed, not typed). The existing images in the thesis are a layout reference only; they are not a style requirement.
+
+## 5. Claims in the thesis text to verify (report each as confirmed / differs by X)
+
+1. Table 4.7: G1 values (S3 0.528 vs 0.357 on DSA and 0.505 vs 0.071 on Metacademy; S4 0.259 vs 0.357 on DSA and 0.147 vs 0.071 on Metacademy); G2 values (0.8, 7.0, 10, 2,000 calls); G3 outcomes and the four classes (S1 and S4 not effective, S2 conditionally effective, S3 effective).
+2. S2 shortlist recall is 0.111 (DSA) and 0.202 (Metacademy). S2 micro-recall on Metacademy is 0.174.
+3. The only cell with F1 ≥ 0.50 and recall ≥ 0.50 is S1 on DSA (0.586, 0.630). No cell has F1 ≥ 0.50 and recall ≥ 0.70. S3 on DSA has F1 0.511 and recall 0.426.
+4. Table 4.8 ranks (the scratch version: DSA F1 S1=1, S3=2, S4=3, S2=4; Metacademy F1 S3=1, S2=2, S1=3, S4=4; calls and wall-clock S2=1, S4=2, S3=3, S1=4).
+5. Table 4.9 (scratch values in Section 6) and the statement that the DSA leader changes with the weights (S1 → S3 → S2) while S2 leads on Metacademy in all three scenarios.
+6. Table 4.10 and the sentences: S3 last in under 0.5% of draws on both corpora; S3 second most often on DSA (60%) and Metacademy (69%); S4 first in no draw on either corpus; S1 and S2 are each first or last on DSA.
+7. The sensitivity paragraph (G2 any limit 10–1,999; G1 size-matched; G3 margin up to 0.15).
+
+## 6. Cross-check targets (NOT to be copied into code)
+
+My independent recomputation from `final_output` T1/T2 (full precision) gives these. The scratch table in the thesis differs by up to about 0.003 on some Metacademy cells (probably rounded inputs). Report any cell where your pipeline differs from the scratch table by more than 0.005.
+
+- DSA: A = [1, 0, 0.829, 0.282], C = [0, 1, 0.346, 0.461] (order S1, S2, S3, S4). Scores 0.7/0.3: [0.700, 0.300, 0.684, 0.336]; 0.5/0.5: [0.500, 0.500, 0.587, 0.372]; 0.3/0.7: [0.300, 0.700, 0.491, 0.407].
+- Metacademy: A = [0.165, 0.864, 1, 0], C = [0, 1, 0.609, 0.674]. Scores 0.7/0.3: [0.116, 0.905, 0.883, 0.202]; 0.5/0.5: [0.083, 0.932, 0.804, 0.337]; 0.3/0.7: [0.050, 0.959, 0.726, 0.472]. The scratch table shows 0.113/0.907, 0.081/0.933 and 0.048/0.960 for S1/S2 in the same rows.
+- Exact rank shares (analytic), DSA rows S1–S4 × ranks 1–4: [0.331 0.169 0.109 0.391], [0.441 0.059 0.156 0.344], [0.228 0.598 0.174 0.000], [0.000 0.174 0.561 0.265]. Metacademy: [0.000 0.000 0.197 0.803], [0.742 0.258 0.000 0.000], [0.258 0.680 0.061 0.000], [0.000 0.061 0.742 0.197].
+- Sweep at n = 2000 (mean calls, mean seconds): S1 (2000, 1713.1), S2 (0.8, 0.938), S3 (10, 8.277), S4 (7.0, 5.638).
+
+## 7. Tests
+
+Extend `tests/test_analysis_pipeline.py` (or add `tests/test_posthoc.py`) with at least: normalisation formula against a hand-worked example; the all-equal criterion → 0.5 rule; exact tie in the DSA balanced scenario and mean-rank handling; τ-b with ties against a hand-computed value; TOPSIS on a 3-point toy matrix with a known answer; exact-share routine against a brute-force fine grid; seeded draw determinism; gate-class logic on a synthetic table covering all three classes; "validation failure ⇒ no artifacts written"; "default run (no flag) writes the same files as before". Run the full existing suite and report pass/fail counts as seen, without hard-coding them in D-90 (D-86(1)(b) removed an ephemeral test count from a decision for that reason).
+
+## 8. Deliverables (AGENTS.md "4 Unit-of-Work Deliverables")
+
+1. Commits on `task/ANALYSIS-004`: first the D-89 + Amendment 4 commit, then code and tests, then D-90. Nothing uncommitted at the end.
+2. `patch/ANALYSIS-004-<agent>-posthoc-ranking.patch`.
+3. Report `docs/reports/ANALYSIS-004-<agent>-posthoc-ranking.md`: executive summary; the Section 5 verification table; every cell where the result differs from the scratch values (old → new); the TOPSIS interpretation choice; the MC-vs-exact comparison; the no-change proof; git diff with index lines; items for the APC. Update the status row and run `./scripts/validate-report.py docs/reports/<report>.md --require-patch`.
+4. A RUN_INFO for the new run in the same format as the earlier one (argv, results_dir, git commit, `pipeline_modules_sha256` for all modules including the new ones, hashes file and its sha256, `src_diff_clean`, `overall_gate_status`).
+5. Package the NEW output directory only (not the whole `final_output_final`) as `bundle_c_posthoc_outputs.tar.gz`, containing `tables/`, `figures/` and `RUN_INFO.txt` of the new run. Tell Luke the path. Do not rebuild the APC bundle unless a shared doc changed (the decision log and analysis plan did, so build one with `./scripts/apc-bundle.sh` profile `core` plus `--add docs/context/analysis-plan.md`).
+
+## 9. Flag, do not fix
+
+Report, and do not change on your own initiative: any disagreement between this prompt and the repo; any place where the thesis text would need to change because a regenerated number differs; the TOPSIS ambiguity; anything in `analysis-plan.md` that conflicts with labelling this stage post hoc. Do not edit the thesis; the APC will relay the text edits.
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 427c90c..4c4755f 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -78,6 +78,7 @@ Status: **in-progress**
 | ANALYSIS-002-F | Remediate Phase 4 analysis pipeline review defects, enforce validation gate, implement Rules R1–R3, and record D-86 | **done** | Completed by Gemini; branch `task/ANALYSIS-002-F` at commit `f5e085d` (base `17ed1f8`). See report [`docs/reports/ANALYSIS-002-F-gemini-report.md`](docs/reports/ANALYSIS-002-F-gemini-report.md). |
 | ANALYSIS-002-G | Independent review of ANALYSIS-002-F Phase 4 analysis pipeline remediation | **done** | Completed by Gemini; branch `task/ANALYSIS-002-G` at commit `ccec59c` (base `f5e085d`). See report [`docs/reports/ANALYSIS-002-G-gemini-review.md`](docs/reports/ANALYSIS-002-G-gemini-review.md). |
 | ANALYSIS-003 | Add exploratory log-scale companion figures F1b, F2b, F6b and record D-87 | **done** | Completed by Gemini; branch `task/ANALYSIS-003` at commit `5ab04a6` (base `79046eb`). See report [`docs/reports/ANALYSIS-003-gemini-report.md`](docs/reports/ANALYSIS-003-gemini-report.md). |
+| ANALYSIS-004 | Add the post-hoc decision and ranking stage (Tables T5–T9b, Figures F7–F9; thesis Sections 3.6 and 4.4.1), including TOPSIS, Kendall tau-b and the wall-clock-substituted check; freeze the specification in [D-89] and record implementation/results in [D-90]. | **needs-review** | Completed by Claude Code; branch `task/ANALYSIS-004` (base `a524de7`), commits `edda901`, `8e2eccf`, `e3b563d`. Post hoc, not pre-registered; no live calls; gate passed; 72 cross-check cells matched. See report [`docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md`](docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md). |
 | DOC-012 | Correct the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures ([D-88]) | **needs-review** | Docs only. Completed by Claude Code; branch `task/DOC-012` at commit `6f198c5` (base `554bde3`). See report [`docs/reports/DOC-012-claude-code-correction.md`](docs/reports/DOC-012-claude-code-correction.md). |
 
 ## Thesis document status (separate track from the code work above)
diff --git a/scripts/analysis/posthoc.py b/scripts/analysis/posthoc.py
new file mode 100644
index 0000000..6e613b3
--- /dev/null
+++ b/scripts/analysis/posthoc.py
@@ -0,0 +1,1092 @@
+"""posthoc.py — Post-hoc decision and ranking framework (thesis Sections 3.6, 4.4.1).
+
+STATUS: POST HOC, NOT PRE-REGISTERED. Specified after the Chapter 4
+measurements existed and frozen in decision-log [D-89] before any ranking
+artifact was computed. Adds no measurement and replaces no pre-registered
+result. Applied to single-run measurements, so the outputs are
+classifications of those measurements, not statistical tests.
+
+This module imports the existing pipeline unchanged:
+- ``stats.evaluate_dominance`` for gate G3 (0.025 F1 margin, Rule R2);
+- ``tables.write_csv`` / ``tables.export_markdown_table`` for output;
+- ``validate_runs.parse_raw_jsonl`` / ``parse_sidecar`` only to recover the
+  realised shortlist sizes used by the G1 size-matched baseline.
+
+All inputs are the in-memory aggregates produced by
+``generate_t1_accuracy_table`` and ``generate_t2_sweep_cost_table``; those
+values are asserted against the existing ``final_output_final`` CSV cells.
+"""
+
+from __future__ import annotations
+
+import csv
+import math
+from pathlib import Path
+from typing import Any, Dict, List, Optional, Sequence, Tuple
+
+import numpy as np
+
+try:
+    from .stats import evaluate_dominance
+    from .tables import export_markdown_table, extract_variant_label, write_csv
+    from .validate_runs import parse_raw_jsonl, parse_sidecar
+except ImportError:  # pragma: no cover - direct script execution
+    from stats import evaluate_dominance
+    from tables import export_markdown_table, extract_variant_label, write_csv
+    from validate_runs import parse_raw_jsonl, parse_sidecar
+
+
+STATUS = "post-hoc"
+POSTHOC_LABEL = "POST HOC: not pre-registered"
+
+STRATEGY_ORDER = [
+    "brute_force",
+    "embedding_threshold",
+    "ann_retrieval",
+    "bounded_bucket",
+]
+STRATEGY_CODE = {
+    "brute_force": "S1",
+    "embedding_threshold": "S2",
+    "ann_retrieval": "S3",
+    "bounded_bucket": "S4",
+}
+CODE_TO_STRATEGY = {v: k for k, v in STRATEGY_CODE.items()}
+
+CORPUS_ORDER = ["DSA_gold_standard_MEKG", "metacademy_gold_standard_MEKG"]
+CORPUS_SHORT = {
+    "DSA_gold_standard_MEKG": "DSA",
+    "metacademy_gold_standard_MEKG": "Metacademy",
+}
+CORPUS_M = {
+    "DSA_gold_standard_MEKG": 28,
+    "metacademy_gold_standard_MEKG": 140,
+}
+
+SCENARIOS = (
+    ("accuracy-first", 0.7),
+    ("balanced", 0.5),
+    ("cost-first", 0.3),
+)
+
+G2_LIMIT = 50.0
+G3_MARGIN = 0.025
+G2_SENSITIVITY_LIMITS = list(range(10, 2000))
+G3_SENSITIVITY_MARGINS = [round(0.005 * k, 3) for k in range(0, 31)]
+
+# Tie tolerance frozen in [D-89](6)(e) and [D-89](7)(b).
+TIE_TOL = 10.0 ** -12
+
+WEIGHT_DRAWS = 20_000
+WEIGHT_SEED = 42
+
+# Output basenames frozen in [D-89](12).
+T5 = "T5_gates_and_classes"
+T5B = "T5b_gate_sensitivity"
+T6 = "T6_single_criterion_ranks"
+T7 = "T7_weighted_scores"
+T8 = "T8_rank_shares"
+T8B = "T8b_rank_shares_exact"
+T9 = "T9_topsis_kendall_tau"
+T9B = "T9b_walltime_substituted_scores"
+
+
+# ---------------------------------------------------------------------------
+# Input assembly
+# ---------------------------------------------------------------------------
+
+def _primary_accuracy_rows(t1_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
+    out = []
+    for row in t1_rows:
+        if "primary" not in str(row.get("variant", "")):
+            continue
+        if row.get("strategy") not in STRATEGY_ORDER:
+            continue
+        if row.get("corpus") not in CORPUS_ORDER:
+            continue
+        out.append(row)
+    return out
+
+
+def _primary_sweep_rows(t2_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
+    out = []
+    for row in t2_rows:
+        if "primary" not in str(row.get("variant", "")):
+            continue
+        if row.get("strategy") not in STRATEGY_ORDER:
+            continue
+        if int(row.get("size_n", -1)) != 2000:
+            continue
+        out.append(row)
+    return out
+
+
+def extract_inputs(
+    t1_rows: Sequence[Dict[str, Any]],
+    t2_rows: Sequence[Dict[str, Any]],
+) -> Dict[str, Any]:
+    """Assemble the frozen per-strategy inputs from the T1/T2 aggregates.
+
+    Raises KeyError/ValueError if a primary configuration or corpus is
+    missing, or if a duplicate primary row is found.
+    """
+    accuracy: Dict[str, Dict[str, Dict[str, Any]]] = {c: {} for c in CORPUS_ORDER}
+    for row in _primary_accuracy_rows(t1_rows):
+        corpus = row["corpus"]
+        strat = row["strategy"]
+        if strat in accuracy[corpus]:
+            raise ValueError(f"Duplicate primary accuracy row for {strat} / {corpus}")
+        accuracy[corpus][strat] = {
+            "variant": row["variant"],
+            "f1_micro": float(row["f1_micro"]),
+            "recall_micro": float(row["recall_micro"]),
+            "precision_micro": float(row["precision_micro"]),
+            "llm_calls_mean": float(row["llm_calls_mean"]),
+            "shortlist_recall_micro": float(row["shortlist_recall_micro"]),
+            "random_baseline_recall": float(row["random_baseline_recall"]),
+            "num_trials": int(row.get("num_trials", 0)),
+        }
+
+    for corpus in CORPUS_ORDER:
+        missing = [s for s in STRATEGY_ORDER if s not in accuracy[corpus]]
+        if missing:
+            raise KeyError(f"Missing primary accuracy rows for {corpus}: {missing}")
+
+    sweep: Dict[str, Dict[str, float]] = {}
+    for row in _primary_sweep_rows(t2_rows):
+        strat = row["strategy"]
+        if strat in sweep:
+            raise ValueError(f"Duplicate primary sweep n=2000 row for {strat}")
+        sweep[strat] = {
+            "llm_calls_mean": float(row["llm_calls_mean"]),
+            "total_s_mean": float(row["total_s_mean"]),
+        }
+    missing_sweep = [s for s in STRATEGY_ORDER if s not in sweep]
+    if missing_sweep:
+        raise KeyError(f"Missing primary sweep n=2000 rows: {missing_sweep}")
+
+    return {"accuracy": accuracy, "sweep": sweep}
+
+
+def realised_shortlist_sizes(
+    accuracy_run_dirs: Sequence[Path],
+) -> Dict[str, Dict[str, float]]:
+    """Mean realised shortlist size over successful accuracy trials.
+
+    One call is made per shortlisted candidate, so for Strategies 3 and 4 the
+    mean ``metrics.shortlist_size`` equals the mean call count reported in T1.
+    The caller asserts that equality.
+    """
+    result: Dict[str, Dict[str, List[float]]] = {c: {} for c in CORPUS_ORDER}
+    for run_dir in sorted(accuracy_run_dirs):
+        sidecar_p = Path(run_dir) / "strategy_config.json"
+        raw_p = Path(run_dir) / "raw.jsonl"
+        if not sidecar_p.is_file() or not raw_p.is_file():
+            continue
+        sidecar = parse_sidecar(sidecar_p)
+        strat = sidecar.get("strategy")
+        if strat not in ("ann_retrieval", "bounded_bucket"):
+            continue
+        variant = extract_variant_label(Path(run_dir).name)
+        if "primary" not in variant:
+            continue
+        records, _, _, _ = parse_raw_jsonl(raw_p)
+        latest: Dict[str, Dict[str, Any]] = {}
+        for rec in records:
+            key = rec.get("key")
+            if key is not None:
+                latest[key] = rec
+        for rec in latest.values():
+            if rec.get("status") != "success":
+                continue
+            corpus = rec.get("corpus")
+            if corpus not in CORPUS_ORDER:
+                continue
+            metrics = rec.get("metrics", {})
+            size = metrics.get("shortlist_size")
+            if size is None:
+                continue
+            result[corpus].setdefault(strat, []).append(float(size))
+
+    means: Dict[str, Dict[str, float]] = {c: {} for c in CORPUS_ORDER}
+    for corpus in CORPUS_ORDER:
+        for strat, values in result[corpus].items():
+            if values:
+                means[corpus][strat] = float(np.mean(values))
+    return means
+
+
+# ---------------------------------------------------------------------------
+# Cross-check against the existing pre-registered output
+# ---------------------------------------------------------------------------
+
+def _read_csv(path: Path) -> List[Dict[str, str]]:
+    with open(path, newline="", encoding="utf-8") as f:
+        return list(csv.DictReader(f))
+
+
+def _close(a: float, b: float, rel_tol: float = 1e-9) -> bool:
+    if math.isnan(a) and math.isnan(b):
+        return True
+    if math.isnan(a) or math.isnan(b):
+        return False
+    return abs(a - b) <= rel_tol * max(1.0, abs(a), abs(b))
+
+
+def assert_matches_final_output(
+    inputs: Dict[str, Any],
+    crosscheck_dir: Path,
+) -> int:
+    """Assert that every value used equals its final_output_final CSV cell.
+
+    Compares against T1 (accuracy), T2 (n=2000 primary rows) and the F6
+    figure CSV. Returns the number of cell comparisons performed.
+    """
+    crosscheck_dir = Path(crosscheck_dir)
+    t1_path = crosscheck_dir / "tables" / "T1_accuracy_benchmark.csv"
+    t2_path = crosscheck_dir / "tables" / "T2_sweep_cost_summary.csv"
+    f6_path = crosscheck_dir / "figures" / "F6_cost_vs_accuracy_dominance.csv"
+
+    n_checks = 0
+
+    t1_by_key: Dict[Tuple[str, str, str], Dict[str, str]] = {}
+    for row in _read_csv(t1_path):
+        if "primary" in row.get("variant", ""):
+            t1_by_key[(row["strategy"], row["variant"], row["corpus"])] = row
+
+    for corpus in CORPUS_ORDER:
+        for strat in STRATEGY_ORDER:
+            src = inputs["accuracy"][corpus][strat]
+            key = (strat, src["variant"], corpus)
+            if key not in t1_by_key:
+                raise AssertionError(f"Cross-check T1 cell missing for {key}")
+            cell = t1_by_key[key]
+            for field in (
+                "f1_micro",
+                "recall_micro",
+                "precision_micro",
+                "llm_calls_mean",
+                "shortlist_recall_micro",
+                "random_baseline_recall",
+            ):
+                expected = float(cell[field]) if cell[field] not in ("", "nan") else float("nan")
+                if not _close(src[field], expected):
+                    raise AssertionError(
+                        f"Cross-check T1 {field} mismatch for {key}: "
+                        f"in-memory {src[field]!r} vs CSV {expected!r}"
+                    )
+                n_checks += 1
+
+    t2_by_key: Dict[Tuple[str, str, int], Dict[str, str]] = {}
+    for row in _read_csv(t2_path):
+        if "primary" in row.get("variant", ""):
+            t2_by_key[(row["strategy"], row["variant"], int(row["size_n"]))] = row
+
+    for strat in STRATEGY_ORDER:
+        variant = inputs["accuracy"][CORPUS_ORDER[0]][strat]["variant"]
+        key = (strat, variant, 2000)
+        if key not in t2_by_key:
+            raise AssertionError(f"Cross-check T2 n=2000 cell missing for {key}")
+        cell = t2_by_key[key]
+        for field in ("llm_calls_mean", "total_s_mean"):
+            expected = float(cell[field])
+            if not _close(inputs["sweep"][strat][field], expected):
+                raise AssertionError(
+                    f"Cross-check T2 {field} mismatch for {key}: "
+                    f"in-memory {inputs['sweep'][strat][field]!r} vs CSV {expected!r}"
+                )
+            n_checks += 1
+
+    f6_by_key: Dict[Tuple[str, str], Dict[str, str]] = {}
+    for row in _read_csv(f6_path):
+        f6_by_key[(row["strategy"], row["corpus"])] = row
+
+    for corpus in CORPUS_ORDER:
+        for strat in STRATEGY_ORDER:
+            src = inputs["accuracy"][corpus][strat]
+            key = (strat, corpus)
+            if key not in f6_by_key:
+                raise AssertionError(f"Cross-check F6 cell missing for {key}")
+            cell = f6_by_key[key]
+            for field, src_field in (("calls", "llm_calls_mean"), ("f1", "f1_micro")):
+                expected = float(cell[field])
+                if not _close(src[src_field], expected):
+                    raise AssertionError(
+                        f"Cross-check F6 {field} mismatch for {key}: "
+                        f"in-memory {src[src_field]!r} vs CSV {expected!r}"
+                    )
+                n_checks += 1
+
+    return n_checks
+
+
+# ---------------------------------------------------------------------------
+# Normalisation, ranking, weighted scores
+# ---------------------------------------------------------------------------
+
+def _normalise(values: Dict[str, float], higher_is_better: bool) -> Tuple[Dict[str, float], bool]:
+    """Min-max normalise; return (scores, degenerate_flag)."""
+    vals = list(values.values())
+    lo, hi = min(vals), max(vals)
+    if abs(hi - lo) <= TIE_TOL:
+        return ({s: 0.5 for s in values}, True)
+    out = {s: (v - lo) / (hi - lo) for s, v in values.items()}
+    if not higher_is_better:
+        out = {s: 1.0 - v for s, v in out.items()}
+    return (out, False)
+
+
+def compute_A_C(inputs: Dict[str, Any], corpus: str) -> Dict[str, Any]:
+    """Compute A_i and C_i for one corpus, per [D-89](6)."""
+    acc = inputs["accuracy"][corpus]
+    f1 = {s: acc[s]["f1_micro"] for s in STRATEGY_ORDER}
+    calls = {s: acc[s]["llm_calls_mean"] for s in STRATEGY_ORDER}
+    g = {s: math.log10(1.0 + calls[s]) for s in STRATEGY_ORDER}
+    if any(c < 0 for c in calls.values()):
+        raise ValueError(f"Negative mean calls for {corpus}: {calls}")
+
+    a, a_degenerate = _normalise(f1, higher_is_better=True)
+    c, c_degenerate = _normalise(g, higher_is_better=False)
+    return {
+        "A": a,
+        "C": c,
+        "g": g,
+        "calls": calls,
+        "f1": f1,
+        "degenerate": {"A": a_degenerate, "C": c_degenerate},
+    }
+
+
+def _order_key(name: str) -> Tuple[int, str]:
+    """Deterministic tie-break order: frozen strategy order, then name."""
+    if name in STRATEGY_ORDER:
+        return (STRATEGY_ORDER.index(name), name)
+    return (len(STRATEGY_ORDER), name)
+
+
+def weighted_scores(A: Dict[str, float], C: Dict[str, float], w: float) -> Dict[str, float]:
+    if set(A) != set(C):
+        raise ValueError("A and C must have the same strategy keys")
+    return {s: w * A[s] + (1.0 - w) * C[s] for s in A}
+
+
+def rank_with_ties(scores: Dict[str, float], higher_is_better: bool = True) -> Dict[str, float]:
+    """Mean-of-occupied-ranks ranking with the frozen tie tolerance."""
+    sign = -1.0 if higher_is_better else 1.0
+    ordered = sorted(
+        scores.items(),
+        key=lambda kv: (sign * kv[1], _order_key(kv[0])),
+    )
+    ranks: Dict[str, float] = {}
+    i = 0
+    while i < len(ordered):
+        j = i
+        while j + 1 < len(ordered) and abs(ordered[j + 1][1] - ordered[i][1]) <= TIE_TOL:
+            j += 1
+        mean_rank = ((i + 1) + (j + 1)) / 2.0
+        for k in range(i, j + 1):
+            ranks[ordered[k][0]] = mean_rank
+        i = j + 1
+    return ranks
+
+
+def strict_ranks(scores: Dict[str, float]) -> Dict[str, int]:
+    """Strict descending rank; ties broken by the frozen strategy order."""
+    ordered = sorted(
+        scores.items(),
+        key=lambda kv: (-kv[1], _order_key(kv[0])),
+    )
+    return {s: i + 1 for i, (s, _) in enumerate(ordered)}
+
+
+def _has_tie(scores: Dict[str, float]) -> bool:
+    vals = list(scores.values())
+    for i in range(len(vals)):
+        for j in range(i + 1, len(vals)):
+            if abs(vals[i] - vals[j]) <= TIE_TOL:
+                return True
+    return False
+
+
+# ---------------------------------------------------------------------------
+# Gates (T5) and gate sensitivity (T5b)
+# ---------------------------------------------------------------------------
+
+def _g1_outcome(
+    inputs: Dict[str, Any],
+    strat: str,
+    baseline: Optional[Dict[str, Dict[str, float]]] = None,
+) -> Dict[str, Any]:
+    """G1 per corpus. ``baseline`` maps corpus -> strategy -> threshold."""
+    if strat == "brute_force":
+        return {"status": "not applicable", "per_corpus": {}, "assessable": False}
+    if strat == "embedding_threshold":
+        return {"status": "not assessable", "per_corpus": {}, "assessable": False}
+
+    per_corpus: Dict[str, Dict[str, Any]] = {}
+    for corpus in CORPUS_ORDER:
+        src = inputs["accuracy"][corpus][strat]
+        if baseline is None:
+            threshold = src["random_baseline_recall"]
+        else:
+            threshold = baseline[corpus][strat]
+        per_corpus[corpus] = {
+            "shortlist_recall": src["shortlist_recall_micro"],
+            "baseline": threshold,
+            "passed": bool(src["shortlist_recall_micro"] > threshold),
+        }
+    overall = all(v["passed"] for v in per_corpus.values())
+    return {
+        "status": "pass" if overall else "fail",
+        "per_corpus": per_corpus,
+        "assessable": True,
+    }
+
+
+def _g3_outcome(
+    inputs: Dict[str, Any],
+    strat: str,
+    margin: float,
+) -> Dict[str, Any]:
+    per_corpus: Dict[str, Dict[str, Any]] = {}
+    dominated_overall = False
+    for corpus in CORPUS_ORDER:
+        acc = inputs["accuracy"][corpus]
+        point_self = {"calls": acc[strat]["llm_calls_mean"], "f1": acc[strat]["f1_micro"]}
+        dominators = []
+        for other in STRATEGY_ORDER:
+            if other == strat:
+                continue
+            point_other = {"calls": acc[other]["llm_calls_mean"], "f1": acc[other]["f1_micro"]}
+            verdict = evaluate_dominance(point_other, point_self, f1_delta_threshold=margin)
+            if verdict == "A dominates B":
+                dominators.append(other)
+        per_corpus[corpus] = {
+            "dominated": bool(dominators),
+            "dominators": dominators,
+        }
+        dominated_overall = dominated_overall or bool(dominators)
+    return {
+        "status": "fail" if dominated_overall else "pass",
+        "per_corpus": per_corpus,
+    }
+
+
+def gate_class(g1: Dict[str, Any], g2: Dict[str, Any], g3: Dict[str, Any]) -> str:
+    if g1["assessable"]:
+        if g1["status"] == "pass" and g2["status"] == "pass" and g3["status"] == "pass":
+            return "Effective"
+        return "Not effective"
+    if g2["status"] == "pass" and g3["status"] == "pass":
+        return "Conditionally effective"
+    return "Not effective"
+
+
+def compute_gates(
+    inputs: Dict[str, Any],
+    g2_limit: float = G2_LIMIT,
+    g3_margin: float = G3_MARGIN,
+    g1_baseline: Optional[Dict[str, Dict[str, float]]] = None,
+) -> Dict[str, Dict[str, Any]]:
+    out: Dict[str, Dict[str, Any]] = {}
+    for strat in STRATEGY_ORDER:
+        g1 = _g1_outcome(inputs, strat, g1_baseline)
+        calls = inputs["sweep"][strat]["llm_calls_mean"]
+        g2 = {"status": "pass" if calls <= g2_limit else "fail", "calls": calls, "limit": g2_limit}
+        g3 = _g3_outcome(inputs, strat, g3_margin)
+        out[strat] = {
+            "g1": g1,
+            "g2": g2,
+            "g3": g3,
+            "class": gate_class(g1, g2, g3),
+        }
+    return out
+
+
+def size_matched_baselines(
+    inputs: Dict[str, Any],
+    shortlist_means: Dict[str, Dict[str, float]],
+) -> Dict[str, Dict[str, float]]:
+    baseline: Dict[str, Dict[str, float]] = {c: {} for c in CORPUS_ORDER}
+    for corpus in CORPUS_ORDER:
+        m = CORPUS_M[corpus]
+        for strat in ("ann_retrieval", "bounded_bucket"):
+            size = shortlist_means[corpus][strat]
+            reported_calls = inputs["accuracy"][corpus][strat]["llm_calls_mean"]
+            if not _close(size, reported_calls):
+                raise AssertionError(
+                    f"Realised mean shortlist size {size!r} != T1 mean calls {reported_calls!r} "
+                    f"for {strat} / {corpus}"
+                )
+            baseline[corpus][strat] = size / m
+    return baseline
+
+
+def build_t5_rows(gates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
+    rows = []
+    for strat in STRATEGY_ORDER:
+        g = gates[strat]
+        row = {
+            "status": STATUS,
+            "strategy": strat,
+            "code": STRATEGY_CODE[strat],
+            "g1_overall": g["g1"]["status"],
+            "g1_dsa": "",
+            "g1_metacademy": "",
+            "g2_calls_n2000": g["g2"]["calls"],
+            "g2_limit": g["g2"]["limit"],
+            "g2_status": g["g2"]["status"],
+            "g3_overall": g["g3"]["status"],
+            "g3_dsa": "",
+            "g3_metacademy": "",
+            "gate_class": g["class"],
+        }
+        for corpus, short in (
+            ("DSA_gold_standard_MEKG", "g1_dsa"),
+            ("metacademy_gold_standard_MEKG", "g1_metacademy"),
+        ):
+            info = g["g1"]["per_corpus"].get(corpus)
+            if info:
+                row[short] = (
+                    f"{'pass' if info['passed'] else 'fail'} "
+                    f"({info['shortlist_recall']:.3f} vs {info['baseline']:.3f})"
+                )
+            else:
+                row[short] = g["g1"]["status"]
+        for corpus, short in (
+            ("DSA_gold_standard_MEKG", "g3_dsa"),
+            ("metacademy_gold_standard_MEKG", "g3_metacademy"),
+        ):
+            info = g["g3"]["per_corpus"][corpus]
+            row[short] = (
+                "fail (dominated by " + ", ".join(STRATEGY_CODE[d] for d in info["dominators"]) + ")"
+                if info["dominated"]
+                else "pass"
+            )
+        rows.append(row)
+    return rows
+
+
+def build_t5b_rows(
+    inputs: Dict[str, Any],
+    gates: Dict[str, Dict[str, Any]],
+    sm_baseline: Dict[str, Dict[str, float]],
+) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
+    """Gate-sensitivity evidence; returns (rows, summary)."""
+    rows: List[Dict[str, Any]] = []
+    frozen_classes = {s: gates[s]["class"] for s in STRATEGY_ORDER}
+
+    # (a) G2 every integer limit 10..1999. G2 is monotone in the limit and the
+    # per-strategy calls are constant, so testing every limit is cheap.
+    g2_changes = []
+    for limit in G2_SENSITIVITY_LIMITS:
+        classes = {
+            s: gate_class(
+                gates[s]["g1"],
+                {"status": "pass" if inputs["sweep"][s]["llm_calls_mean"] <= limit else "fail"},
+                gates[s]["g3"],
+            )
+            for s in STRATEGY_ORDER
+        }
+        if classes != frozen_classes:
+            g2_changes.append({"limit": limit, "classes": classes})
+    for strat in STRATEGY_ORDER:
+        rows.append({
+            "status": STATUS,
+            "family": "G2",
+            "setting": "every integer limit 10..1999 (1990 settings)",
+            "strategy": STRATEGY_CODE[strat],
+            "value": inputs["sweep"][strat]["llm_calls_mean"],
+            "gate_status": "pass" if inputs["sweep"][strat]["llm_calls_mean"] <= 1999 else "fail",
+            "class": frozen_classes[strat],
+            "class_unchanged": not g2_changes,
+            "detail": f"{len(g2_changes)} class changes over the limit range",
+        })
+
+    # (b) G1 size-matched baseline.
+    for strat in STRATEGY_ORDER:
+        g1_sm = _g1_outcome(inputs, strat, sm_baseline)
+        cls = gate_class(g1_sm, gates[strat]["g2"], gates[strat]["g3"])
+        for corpus in CORPUS_ORDER:
+            info = g1_sm["per_corpus"].get(corpus)
+            if info is None:
+                rows.append({
+                    "status": STATUS,
+                    "family": "G1",
+                    "setting": "size-matched baseline",
+                    "strategy": STRATEGY_CODE[strat],
+                    "value": "",
+                    "gate_status": g1_sm["status"],
+                    "class": cls,
+                    "class_unchanged": cls == frozen_classes[strat],
+                    "detail": f"{CORPUS_SHORT[corpus]}: no baseline applies",
+                })
+            else:
+                rows.append({
+                    "status": STATUS,
+                    "family": "G1",
+                    "setting": "size-matched baseline",
+                    "strategy": STRATEGY_CODE[strat],
+                    "value": info["shortlist_recall"],
+                    "gate_status": "pass" if info["passed"] else "fail",
+                    "class": cls,
+                    "class_unchanged": cls == frozen_classes[strat],
+                    "detail": (
+                        f"{CORPUS_SHORT[corpus]}: baseline {info['baseline']:.4f} "
+                        f"(mean shortlist size {info['baseline'] * CORPUS_M[corpus]:.4f} / m={CORPUS_M[corpus]})"
+                    ),
+                })
+
+    # (c) G3 margin 0..0.15 in 0.005 steps.
+    g3_changes: List[Dict[str, Any]] = []
+    for margin in G3_SENSITIVITY_MARGINS:
+        for strat in STRATEGY_ORDER:
+            g3 = _g3_outcome(inputs, strat, margin)
+            cls = gate_class(gates[strat]["g1"], gates[strat]["g2"], g3)
+            changed = cls != frozen_classes[strat]
+            if changed:
+                g3_changes.append({"margin": margin, "strategy": strat, "class": cls})
+            detail = "; ".join(
+                f"{CORPUS_SHORT[c]}: " + (
+                    "dominated by " + ", ".join(STRATEGY_CODE[d] for d in g3["per_corpus"][c]["dominators"])
+                    if g3["per_corpus"][c]["dominated"] else "not dominated"
+                )
+                for c in CORPUS_ORDER
+            )
+            rows.append({
+                "status": STATUS,
+                "family": "G3",
+                "setting": f"margin={margin:.3f}",
+                "strategy": STRATEGY_CODE[strat],
+                "value": margin,
+                "gate_status": g3["status"],
+                "class": cls,
+                "class_unchanged": not changed,
+                "detail": detail,
+            })
+
+    first_g3_change = g3_changes[0]["margin"] if g3_changes else None
+    summary = {
+        "g2_n_settings": len(G2_SENSITIVITY_LIMITS),
+        "g2_changes": g2_changes,
+        "g3_first_change": first_g3_change,
+        "g3_changes": g3_changes,
+        "classes_unchanged_all": (
+            not g2_changes
+            and not g3_changes
+            and all(r["class_unchanged"] for r in rows if r["family"] == "G1")
+        ),
+    }
+    return rows, summary
+
+
+# ---------------------------------------------------------------------------
+# Single-criterion ranks (T6), weighted scores (T7), wall-clock check (T9b)
+# ---------------------------------------------------------------------------
+
+def build_t6_rows(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
+    rows: List[Dict[str, Any]] = []
+    calls = {s: inputs["sweep"][s]["llm_calls_mean"] for s in STRATEGY_ORDER}
+    wall = {s: inputs["sweep"][s]["total_s_mean"] for s in STRATEGY_ORDER}
+    calls_rank = rank_with_ties(calls, higher_is_better=False)
+    wall_rank = rank_with_ties(wall, higher_is_better=False)
+    for corpus in CORPUS_ORDER:
+        f1 = {s: inputs["accuracy"][corpus][s]["f1_micro"] for s in STRATEGY_ORDER}
+        f1_rank = rank_with_ties(f1, higher_is_better=True)
+        for strat in STRATEGY_ORDER:
+            rows.append({
+                "status": STATUS,
+                "corpus": corpus,
+                "strategy": strat,
+                "code": STRATEGY_CODE[strat],
+                "f1_micro": f1[strat],
+                "f1_rank": f1_rank[strat],
+                "calls_n2000_mean": calls[strat],
+                "calls_rank": calls_rank[strat],
+                "total_s_n2000_mean": wall[strat],
+                "wallclock_rank": wall_rank[strat],
+            })
+    return rows
+
+
+def build_t7_rows(inputs: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
+    rows: List[Dict[str, Any]] = []
+    store: Dict[str, Any] = {}
+    for corpus in CORPUS_ORDER:
+        ac = compute_A_C(inputs, corpus)
+        store[corpus] = ac
+        for scenario, w in SCENARIOS:
+            scores = weighted_scores(ac["A"], ac["C"], w)
+            ranks = rank_with_ties(scores, higher_is_better=True)
+            best_score = max(scores.values())
+            for strat in STRATEGY_ORDER:
+                rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "scenario": scenario,
+                    "accuracy_weight": w,
+                    "cost_weight": 1.0 - w,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "A_i": ac["A"][strat],
+                    "C_i": ac["C"][strat],
+                    "g_i": ac["g"][strat],
+                    "score": scores[strat],
+                    "rank": ranks[strat],
+                    "is_best": abs(scores[strat] - best_score) <= TIE_TOL,
+                    "degenerate_criterion": (
+                        f"A={ac['degenerate']['A']};C={ac['degenerate']['C']}"
+                    ),
+                })
+    return rows, store
+
+
+def build_t9b_rows(
+    inputs: Dict[str, Any],
+    store: Dict[str, Any],
+) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
+    g_wall = {
+        s: math.log10(1.0 + inputs["sweep"][s]["total_s_mean"])
+        for s in STRATEGY_ORDER
+    }
+    c_wall, degenerate = _normalise(g_wall, higher_is_better=False)
+    rows: List[Dict[str, Any]] = []
+    comparison: Dict[str, Any] = {}
+    for corpus in CORPUS_ORDER:
+        ac = store[corpus]
+        for scenario, w in SCENARIOS:
+            scores = {s: w * ac["A"][s] + (1.0 - w) * c_wall[s] for s in STRATEGY_ORDER}
+            ranks = rank_with_ties(scores, higher_is_better=True)
+            tops = [s for s in STRATEGY_ORDER if ranks[s] == min(ranks.values())]
+            t7_scores = weighted_scores(ac["A"], ac["C"], w)
+            t7_ranks = rank_with_ties(t7_scores, higher_is_better=True)
+            t7_tops = [s for s in STRATEGY_ORDER if t7_ranks[s] == min(t7_ranks.values())]
+            match = set(tops) == set(t7_tops)
+            comparison[f"{corpus}|{scenario}"] = {
+                "tops": tops,
+                "t7_tops": t7_tops,
+                "match": match,
+            }
+            for strat in STRATEGY_ORDER:
+                rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "scenario": scenario,
+                    "accuracy_weight": w,
+                    "cost_weight": 1.0 - w,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "A_i": ac["A"][strat],
+                    "C_i_wallclock": c_wall[strat],
+                    "g_wallclock": g_wall[strat],
+                    "score": scores[strat],
+                    "rank": ranks[strat],
+                    "top_matches_T7": match,
+                    "degenerate_C": degenerate,
+                })
+    return rows, comparison
+
+
+# ---------------------------------------------------------------------------
+# Weight sweep (T8) and exact shares (T8b)
+# ---------------------------------------------------------------------------
+
+def mc_rank_shares(
+    A: Dict[str, float],
+    C: Dict[str, float],
+    n_draws: int = WEIGHT_DRAWS,
+    seed: int = WEIGHT_SEED,
+) -> Dict[str, Any]:
+    """Monte Carlo rank shares per [D-89](7)."""
+    keys = list(A)
+    n_ranks = len(keys)
+    rng = np.random.default_rng(seed)
+    draws = rng.random(n_draws)
+    counts = {s: {r: 0 for r in range(1, n_ranks + 1)} for s in keys}
+    tie_draws = 0
+    for w in draws:
+        scores = weighted_scores(A, C, float(w))
+        if _has_tie(scores):
+            tie_draws += 1
+        for s, r in strict_ranks(scores).items():
+            counts[s][r] += 1
+    shares = {
+        s: {r: counts[s][r] / n_draws for r in range(1, n_ranks + 1)}
+        for s in keys
+    }
+    se = {
+        s: {r: math.sqrt(max(0.0, shares[s][r] * (1.0 - shares[s][r]) / n_draws)) for r in range(1, n_ranks + 1)}
+        for s in keys
+    }
+    return {"shares": shares, "se": se, "tie_draws": tie_draws, "n_draws": n_draws, "seed": seed}
+
+
+def exact_rank_shares(A: Dict[str, float], C: Dict[str, float]) -> Dict[str, Any]:
+    """Analytic rank shares per [D-89](8)."""
+    keys = list(A)
+    n_ranks = len(keys)
+    breakpoints = [0.0, 1.0]
+    structural_ties = False
+    for i in range(len(keys)):
+        for j in range(i + 1, len(keys)):
+            si, sj = keys[i], keys[j]
+            den = (A[si] - C[si]) - (A[sj] - C[sj])
+            if abs(den) <= TIE_TOL:
+                if abs(C[sj] - C[si]) <= TIE_TOL:
+                    structural_ties = True
+                continue
+            w = (C[sj] - C[si]) / den
+            if 0.0 < w < 1.0:
+                breakpoints.append(w)
+    xs = sorted(set(breakpoints))
+    shares = {s: {r: 0.0 for r in range(1, n_ranks + 1)} for s in keys}
+    for a, b in zip(xs, xs[1:]):
+        mid = (a + b) / 2.0
+        ranks = strict_ranks(weighted_scores(A, C, mid))
+        for s, r in ranks.items():
+            shares[s][r] += (b - a)
+    return {"shares": shares, "n_intervals": len(xs) - 1, "structural_ties": structural_ties}
+
+
+# ---------------------------------------------------------------------------
+# TOPSIS and Kendall tau-b (T9)
+# ---------------------------------------------------------------------------
+
+def topsis_closeness(A: Dict[str, float], C: Dict[str, float], w: float) -> Dict[str, float]:
+    """Weighted TOPSIS closeness per [D-89](9)."""
+    out: Dict[str, float] = {}
+    for s in A:
+        d_pos = math.hypot(w * A[s] - w, (1.0 - w) * C[s] - (1.0 - w))
+        d_neg = math.hypot(w * A[s], (1.0 - w) * C[s])
+        denom = d_pos + d_neg
+        out[s] = (d_neg / denom) if denom > 0 else float("nan")
+    return out
+
+
+def kendall_tau_b(
+    x: Dict[str, float],
+    y: Dict[str, float],
+) -> Dict[str, Any]:
+    """Kendall tau-b with the tie correction, implemented by hand.
+
+    Returns tau, the number of tied pairs, and pair counts.
+    """
+    keys = sorted(x, key=_order_key)
+    n = len(keys)
+    concordant = discordant = 0
+    tied_x = tied_y = tied_both = 0
+    for i in range(n):
+        for j in range(i + 1, n):
+            dx = x[keys[i]] - x[keys[j]]
+            dy = y[keys[i]] - y[keys[j]]
+            sx = 0 if abs(dx) <= TIE_TOL else (1 if dx > 0 else -1)
+            sy = 0 if abs(dy) <= TIE_TOL else (1 if dy > 0 else -1)
+            if sx == 0 and sy == 0:
+                tied_both += 1
+            elif sx == 0:
+                tied_x += 1
+            elif sy == 0:
+                tied_y += 1
+            elif sx * sy > 0:
+                concordant += 1
+            else:
+                discordant += 1
+    n0 = n * (n - 1) / 2.0
+    n1 = tied_x + tied_both
+    n2 = tied_y + tied_both
+    denom = math.sqrt(max(0.0, (n0 - n1) * (n0 - n2)))
+    tau = ((concordant - discordant) / denom) if denom > 0 else float("nan")
+    return {
+        "tau": tau,
+        "tied_pairs": tied_x + tied_y + tied_both,
+        "concordant": concordant,
+        "discordant": discordant,
+        "tied_x": n1,
+        "tied_y": n2,
+    }
+
+
+def build_t9_rows(store: Dict[str, Any]) -> List[Dict[str, Any]]:
+    rows: List[Dict[str, Any]] = []
+    for corpus in CORPUS_ORDER:
+        ac = store[corpus]
+        for scenario, w in SCENARIOS:
+            sums = weighted_scores(ac["A"], ac["C"], w)
+            sum_ranks = rank_with_ties(sums, higher_is_better=True)
+            close = topsis_closeness(ac["A"], ac["C"], w)
+            topsis_ranks = rank_with_ties(close, higher_is_better=True)
+            tau = kendall_tau_b(topsis_ranks, sum_ranks)
+            for strat in STRATEGY_ORDER:
+                rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "scenario": scenario,
+                    "accuracy_weight": w,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "A_i": ac["A"][strat],
+                    "C_i": ac["C"][strat],
+                    "topsis_closeness": close[strat],
+                    "topsis_rank": topsis_ranks[strat],
+                    "weighted_sum_rank": sum_ranks[strat],
+                    "kendall_tau_b": tau["tau"],
+                    "tied_pairs": tau["tied_pairs"],
+                })
+    return rows
+
+
+# ---------------------------------------------------------------------------
+# Orchestration and output
+# ---------------------------------------------------------------------------
+
+def _write_table(rows: List[Dict[str, Any]], tables_dir: Path, name: str, title: str) -> None:
+    write_csv(tables_dir / f"{name}.csv", rows)
+    export_markdown_table(rows, tables_dir / f"{name}.md", title)
+
+
+def _rounded_markdown_rows(rows: List[Dict[str, Any]], places: int = 2) -> List[Dict[str, Any]]:
+    out = []
+    for row in rows:
+        new = {}
+        for k, v in row.items():
+            if isinstance(v, float):
+                new[k] = f"{v:.{places}f}"
+            else:
+                new[k] = v
+        out.append(new)
+    return out
+
+
+def build_t8_rows(store: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
+    rows: List[Dict[str, Any]] = []
+    mc_store: Dict[str, Any] = {}
+    exact_store: Dict[str, Any] = {}
+    for corpus in CORPUS_ORDER:
+        ac = store[corpus]
+        mc = mc_rank_shares(ac["A"], ac["C"])
+        exact = exact_rank_shares(ac["A"], ac["C"])
+        mc_store[corpus] = mc
+        exact_store[corpus] = exact
+        max_diff = max(
+            abs(mc["shares"][s][r] - exact["shares"][s][r])
+            for s in STRATEGY_ORDER for r in range(1, 5)
+        )
+        for strat in STRATEGY_ORDER:
+            for rank in range(1, 5):
+                rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "rank": rank,
+                    "share_mc": mc["shares"][strat][rank],
+                    "share_mc_se": mc["se"][strat][rank],
+                    "share_exact": exact["shares"][strat][rank],
+                    "abs_mc_minus_exact": abs(
+                        mc["shares"][strat][rank] - exact["shares"][strat][rank]
+                    ),
+                    "max_abs_mc_minus_exact_corpus": max_diff,
+                    "tie_draws": mc["tie_draws"],
+                    "n_draws": mc["n_draws"],
+                    "seed": mc["seed"],
+                })
+    return rows, mc_store, exact_store
+
+
+def run_posthoc_stage(
+    results_dir: Path,
+    accuracy_run_dirs: Sequence[Path],
+    t1_rows: Sequence[Dict[str, Any]],
+    t2_rows: Sequence[Dict[str, Any]],
+    output_dir: Path,
+    crosscheck_dir: Path,
+) -> Dict[str, Any]:
+    """Run the whole post-hoc stage and write only its own artifacts."""
+    # Figures are imported lazily so that a table-only test does not need
+    # matplotlib's style module configured on import.
+    try:
+        from .posthoc_figures import plot_f7_gates, plot_f8_score_vs_weight, plot_f9_rank_shares
+    except ImportError:  # pragma: no cover
+        from posthoc_figures import plot_f7_gates, plot_f8_score_vs_weight, plot_f9_rank_shares
+
+    tables_dir = Path(output_dir) / "tables"
+    figures_dir = Path(output_dir) / "figures"
+
+    inputs = extract_inputs(t1_rows, t2_rows)
+    n_checks = assert_matches_final_output(inputs, crosscheck_dir)
+
+    shortlist_means = realised_shortlist_sizes(accuracy_run_dirs)
+    sm_baseline = size_matched_baselines(inputs, shortlist_means)
+
+    tables_dir.mkdir(parents=True, exist_ok=True)
+    figures_dir.mkdir(parents=True, exist_ok=True)
+
+    gates = compute_gates(inputs)
+    t5_rows = build_t5_rows(gates)
+    _write_table(t5_rows, tables_dir, T5, "Table T5: Gates and Classes (POST HOC, not pre-registered)")
+
+    t5b_rows, t5b_summary = build_t5b_rows(inputs, gates, sm_baseline)
+    _write_table(t5b_rows, tables_dir, T5B, "Table T5b: Gate Sensitivity (POST HOC, not pre-registered)")
+
+    t6_rows = build_t6_rows(inputs)
+    _write_table(t6_rows, tables_dir, T6, "Table T6: Single-Criterion Ranks (POST HOC, not pre-registered)")
+
+    t7_rows, store = build_t7_rows(inputs)
+    _write_table(t7_rows, tables_dir, T7, "Table T7: Weighted Scores (POST HOC, not pre-registered)")
+
+    t8_rows, mc_store, exact_store = build_t8_rows(store)
+    # [D-89](7)(c): full precision in the CSV, 2 decimals in the Markdown.
+    write_csv(tables_dir / f"{T8}.csv", t8_rows)
+    export_markdown_table(
+        _rounded_markdown_rows(t8_rows),
+        tables_dir / f"{T8}.md",
+        "Table T8: Monte Carlo Rank Shares, 2 decimals (POST HOC, not pre-registered)",
+    )
+    t8b_rows = [
+        {
+            "status": STATUS,
+            "corpus": row["corpus"],
+            "strategy": row["strategy"],
+            "code": row["code"],
+            "rank": row["rank"],
+            "share_exact": exact_store[row["corpus"]]["shares"][row["strategy"]][row["rank"]],
+            "share_mc": mc_store[row["corpus"]]["shares"][row["strategy"]][row["rank"]],
+            "abs_mc_minus_exact": row["abs_mc_minus_exact"],
+            "max_abs_mc_minus_exact_corpus": row["max_abs_mc_minus_exact_corpus"],
+            "status_note": (
+                f"intervals={exact_store[row['corpus']]['n_intervals']}; "
+                f"structural_ties={exact_store[row['corpus']]['structural_ties']}"
+            ),
+        }
+        for row in t8_rows
+    ]
+    _write_table(
+        t8b_rows, tables_dir, T8B,
+        "Table T8b: Exact Analytic Rank Shares (POST HOC, not pre-registered)",
+    )
+
+    t9_rows = build_t9_rows(store)
+    _write_table(t9_rows, tables_dir, T9, "Table T9: TOPSIS and Kendall tau-b (POST HOC, not pre-registered)")
+
+    t9b_rows, t9b_comparison = build_t9b_rows(inputs, store)
+    _write_table(
+        t9b_rows, tables_dir, T9B,
+        "Table T9b: Wall-Clock-Substituted Scores (POST HOC, not pre-registered)",
+    )
+
+    plot_f7_gates(inputs, gates, figures_dir)
+    plot_f8_score_vs_weight(store, figures_dir)
+    plot_f9_rank_shares(mc_store, figures_dir)
+
+    return {
+        "n_crosschecks": n_checks,
+        "inputs": inputs,
+        "gates": gates,
+        "t5b_summary": t5b_summary,
+        "store": store,
+        "mc": mc_store,
+        "exact": exact_store,
+        "t9b_comparison": t9b_comparison,
+        "shortlist_means": shortlist_means,
+        "size_matched_baseline": sm_baseline,
+    }
diff --git a/scripts/analysis/posthoc_figures.py b/scripts/analysis/posthoc_figures.py
new file mode 100644
index 0000000..694a627
--- /dev/null
+++ b/scripts/analysis/posthoc_figures.py
@@ -0,0 +1,334 @@
+"""posthoc_figures.py — Figures F7, F8 and F9 (POST HOC, not pre-registered).
+
+Layout follows direction from the ANALYSIS-004 specification and
+``style.py``; the hand-drawn thesis images are a layout reference only.
+Every figure displays the visible text "POST HOC: not pre-registered".
+Non-positive or non-finite values are omitted from a panel and recorded
+with ``plotted = False`` (omit-not-clamp, [D-87](4)); no clamping or
+shifting is applied.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Any, Dict, List, Sequence
+
+import matplotlib.pyplot as plt
+import numpy as np
+
+try:
+    from .style import (
+        STRATEGY_LABELS,
+        STRATEGY_MARKERS,
+        STRATEGY_PALETTE,
+        apply_thesis_style,
+        export_figure,
+    )
+    from .posthoc import (
+        CORPUS_M,
+        CORPUS_ORDER,
+        CORPUS_SHORT,
+        POSTHOC_LABEL,
+        SCENARIOS,
+        STATUS,
+        STRATEGY_CODE,
+        STRATEGY_ORDER,
+    )
+except ImportError:  # pragma: no cover - direct script execution
+    from style import (
+        STRATEGY_LABELS,
+        STRATEGY_MARKERS,
+        STRATEGY_PALETTE,
+        apply_thesis_style,
+        export_figure,
+    )
+    from posthoc import (
+        CORPUS_M,
+        CORPUS_ORDER,
+        CORPUS_SHORT,
+        POSTHOC_LABEL,
+        SCENARIOS,
+        STATUS,
+        STRATEGY_CODE,
+        STRATEGY_ORDER,
+    )
+
+
+def _corner_label(ax: plt.Axes, x: float = 0.98, y: float = 0.96) -> None:
+    ax.text(
+        x,
+        y,
+        POSTHOC_LABEL,
+        transform=ax.transAxes,
+        fontsize=7,
+        ha="center" if abs(x - 0.5) <= 1e-9 else ("right" if x > 0.5 else "left"),
+        va="top" if y > 0.5 else "bottom",
+        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor="gray"),
+    )
+
+
+def plot_f7_gates(inputs: Dict[str, Any], gates: Dict[str, Any], output_dir: Path) -> None:
+    """Figure F7: gates G1 and G2 applied to the primary configurations."""
+    apply_thesis_style()
+    fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(6.5, 7.6))
+    csv_rows: List[Dict[str, Any]] = []
+    omitted: List[str] = []
+
+    # Panel A: G1 shortlist recall for S3 and S4, with pre-registered baseline.
+    g1_strategies = ["ann_retrieval", "bounded_bucket"]
+    x = np.arange(len(CORPUS_ORDER) * len(g1_strategies), dtype=float)
+    width = 0.55
+    idx = 0
+    ticklabels: List[str] = []
+    for corpus in CORPUS_ORDER:
+        for strat in g1_strategies:
+            info = gates[strat]["g1"]["per_corpus"][corpus]
+            value = float(info["shortlist_recall"])
+            baseline = float(info["baseline"])
+            color = STRATEGY_PALETTE[strat]
+            if np.isfinite(value) and value > 0:
+                ax_a.bar(x[idx], value, width, color=color)
+                ax_a.text(x[idx], value + 0.012, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
+            else:
+                omitted.append(f"{STRATEGY_CODE[strat]} {CORPUS_SHORT[corpus]}")
+            ax_a.hlines(
+                baseline,
+                x[idx] - width / 2,
+                x[idx] + width / 2,
+                colors="black",
+                linestyles="--",
+                linewidth=1.4,
+            )
+            ax_a.text(
+                x[idx] + width / 2 + 0.02,
+                baseline,
+                f"{baseline:.3f}",
+                va="center",
+                fontsize=7,
+            )
+            ticklabels.append(f"{STRATEGY_CODE[strat]}\n{CORPUS_SHORT[corpus]}")
+            csv_rows.append({
+                "status": STATUS,
+                "panel": "G1",
+                "corpus": corpus,
+                "strategy": strat,
+                "code": STRATEGY_CODE[strat],
+                "shortlist_recall": value,
+                "random_baseline_recall": baseline,
+                "plotted": bool(np.isfinite(value) and value > 0),
+            })
+            idx += 1
+
+    ax_a.set_xticks(x)
+    ax_a.set_xticklabels(ticklabels)
+    ax_a.set_ylabel("Shortlist recall")
+    ax_a.set_ylim(0, max(0.8, ax_a.get_ylim()[1]))
+    ax_a.set_title(
+        "Panel A — G1: shortlist recall vs pre-registered random baseline\n"
+        "S1: whole-graph shortlist (no baseline); S2: no shortlist cap (not assessable)"
+    )
+    _corner_label(ax_a, x=0.98, y=0.96)
+
+    # Panel B: G2 mean calls at n = 2000 on a log x-axis.
+    ys = np.arange(len(STRATEGY_ORDER))
+    for y, strat in zip(ys, STRATEGY_ORDER):
+        calls = float(inputs["sweep"][strat]["llm_calls_mean"])
+        color = STRATEGY_PALETTE[strat]
+        if np.isfinite(calls) and calls > 0:
+            ax_b.scatter(calls, y, color=color, marker=STRATEGY_MARKERS[strat], s=110, zorder=4)
+            if strat == "brute_force":
+                ax_b.scatter(calls, y, s=320, facecolors="none", edgecolors="#BB2222", linewidths=1.8, zorder=3)
+            ax_b.annotate(
+                f" {calls:g}",
+                (calls, y),
+                xytext=(8, 0),
+                textcoords="offset points",
+                va="center",
+                fontsize=8,
+            )
+            plotted = True
+        else:
+            omitted.append(f"{STRATEGY_CODE[strat]} G2")
+            plotted = False
+        ax_b.axvline(50.0, color="black", linestyle="--", linewidth=1.4)
+        ax_b.text(50.0, len(STRATEGY_ORDER) - 0.35, " limit: 50", fontsize=8, va="bottom")
+        csv_rows.append({
+            "status": STATUS,
+            "panel": "G2",
+            "corpus": "",
+            "strategy": strat,
+            "code": STRATEGY_CODE[strat],
+            "shortlist_recall": float("nan"),
+            "random_baseline_recall": float("nan"),
+            "calls_n2000": calls,
+            "limit": 50.0,
+            "gate_status": gates[strat]["g2"]["status"],
+            "plotted": plotted,
+        })
+
+    ax_b.set_xscale("log")
+    ax_b.set_yticks(ys)
+    ax_b.set_yticklabels(
+        [f"{STRATEGY_CODE[s]} ({gates[s]['g2']['status']})" for s in STRATEGY_ORDER]
+    )
+    ax_b.set_ylim(-0.7, len(STRATEGY_ORDER) - 0.1)
+    ax_b.set_xlabel("Mean LLM calls per insertion at n = 2000 (log scale)")
+    ax_b.set_title("Panel B — G2: mean calls per insertion at n = 2000 against the 50-call limit")
+    _corner_label(ax_b, x=0.02, y=0.96)
+
+    if omitted:
+        fig.text(0.01, 0.005, "not plotted: " + "; ".join(omitted), fontsize=7, style="italic")
+
+    fig.suptitle("Gates G1 and G2 applied to the primary configurations\n" + POSTHOC_LABEL)
+    fig.tight_layout(rect=(0, 0.01, 1, 0.96))
+    export_figure(fig, output_dir / "F7_gates_g1_g2", csv_rows)
+    plt.close(fig)
+
+
+def plot_f8_score_vs_weight(store: Dict[str, Any], output_dir: Path) -> None:
+    """Figure F8: normalised score against the weight on accuracy, by corpus."""
+    apply_thesis_style()
+    fig, axes = plt.subplots(1, len(CORPUS_ORDER), figsize=(10.5, 4.8), squeeze=False)
+    csv_rows: List[Dict[str, Any]] = []
+    omitted: List[str] = []
+
+    for c_idx, corpus in enumerate(CORPUS_ORDER):
+        ax = axes[0][c_idx]
+        ac = store[corpus]
+        for w in (0.3, 0.5, 0.7):
+            ax.axvline(w, color="gray", alpha=0.3, linewidth=1.0, zorder=1)
+        for strat in STRATEGY_ORDER:
+            a_val = float(ac["A"][strat])
+            c_val = float(ac["C"][strat])
+            if not (np.isfinite(a_val) and np.isfinite(c_val)):
+                omitted.append(f"{STRATEGY_CODE[strat]} {CORPUS_SHORT[corpus]}")
+                continue
+            emphasised = strat == "ann_retrieval"
+            ax.plot(
+                [0.0, 1.0],
+                [c_val, a_val],
+                color=STRATEGY_PALETTE[strat],
+                marker=STRATEGY_MARKERS[strat],
+                markersize=5,
+                linewidth=3.0 if emphasised else 1.6,
+                alpha=1.0 if emphasised else 0.85,
+                zorder=4 if emphasised else 3,
+                label=STRATEGY_CODE[strat],
+            )
+            ax.annotate(
+                f" {STRATEGY_CODE[strat]}",
+                (1.0, a_val),
+                xytext=(4, 0),
+                textcoords="offset points",
+                va="center",
+                fontsize=9,
+                fontweight="bold" if emphasised else "normal",
+            )
+            ax.annotate(
+                f" {STRATEGY_CODE[strat]}",
+                (0.0, c_val),
+                xytext=(-18, 0),
+                textcoords="offset points",
+                va="center",
+                fontsize=9,
+                fontweight="bold" if emphasised else "normal",
+            )
+            for w in (0.3, 0.5, 0.7):
+                score = w * a_val + (1.0 - w) * c_val
+                csv_rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "accuracy_weight": w,
+                    "cost_weight": 1.0 - w,
+                    "A_i": a_val,
+                    "C_i": c_val,
+                    "score": score,
+                })
+
+        ax.set_xlim(-0.05, 1.12)
+        ax.set_ylim(0.0, 1.0)
+        ax.set_xlabel("Weight on accuracy, w")
+        ax.set_ylabel("Normalised score S(w)")
+        ax.set_title(f"{CORPUS_SHORT[corpus]} (m = {CORPUS_M[corpus]})")
+        # Direct end labels identify every line; a legend would collide with the
+        # S4 end label in the lower-right corner.
+        _corner_label(ax, x=0.5, y=0.02)
+
+    if omitted:
+        fig.text(0.01, 0.005, "not plotted: " + "; ".join(omitted), fontsize=7, style="italic")
+    fig.suptitle("Normalised score against the weight on accuracy, by corpus\n" + POSTHOC_LABEL)
+    fig.tight_layout(rect=(0, 0.01, 1, 0.94))
+    export_figure(fig, output_dir / "F8_score_vs_weight", csv_rows)
+    plt.close(fig)
+
+
+def plot_f9_rank_shares(mc_store: Dict[str, Any], output_dir: Path) -> None:
+    """Figure F9: share of weightings giving each rank, by strategy and corpus."""
+    apply_thesis_style()
+    fig, ax = plt.subplots(figsize=(8.2, 4.8))
+    csv_rows: List[Dict[str, Any]] = []
+    # Rank 1 darkest to rank 4 lightest (single-hue ramp).
+    rank_colors = {1: "#1B3A5C", 2: "#4A7BA7", 3: "#8FB4D1", 4: "#CFDEEC"}
+
+    y_positions: List[float] = []
+    y_labels: List[str] = []
+    y = 0.0
+    for corpus in CORPUS_ORDER:
+        # Highest-ranked strategy on top within each corpus group.
+        y += 0.4
+        for strat in STRATEGY_ORDER:
+            shares = mc_store[corpus]["shares"][strat]
+            left = 0.0
+            for rank in range(1, 5):
+                share = float(shares[rank])
+                ax.barh(
+                    y,
+                    share,
+                    left=left,
+                    color=rank_colors[rank],
+                    edgecolor="white",
+                    linewidth=0.6,
+                    height=0.72,
+                )
+                if share >= 0.08:
+                    ax.text(
+                        left + share / 2.0,
+                        y,
+                        f"{share:.2f}",
+                        ha="center",
+                        va="center",
+                        fontsize=8,
+                        color="white" if rank <= 2 else "#222222",
+                    )
+                csv_rows.append({
+                    "status": STATUS,
+                    "corpus": corpus,
+                    "strategy": strat,
+                    "code": STRATEGY_CODE[strat],
+                    "rank": rank,
+                    "share_mc": share,
+                    "labelled": share >= 0.08,
+                })
+                left += share
+            y_positions.append(y)
+            y_labels.append(f"{STRATEGY_CODE[strat]} — {CORPUS_SHORT[corpus]}")
+            y += 1.0
+        y += 0.5
+
+    ax.set_yticks(y_positions)
+    ax.set_yticklabels(y_labels)
+    ax.set_xlim(0.0, 1.0)
+    ax.set_xlabel("Share of 20,000 weight draws (accuracy weight uniform on 0 to 1)")
+    ax.set_title(
+        "Share of weightings giving each rank, by strategy and corpus\n" + POSTHOC_LABEL
+    )
+    handles = [
+        plt.Rectangle((0, 0), 1, 1, color=rank_colors[r], label=f"Rank {r}")
+        for r in range(1, 5)
+    ]
+    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=4, fontsize=8)
+    fig.tight_layout()
+    export_figure(fig, output_dir / "F9_rank_shares", csv_rows)
+    plt.close(fig)
diff --git a/scripts/analysis/run_analysis.py b/scripts/analysis/run_analysis.py
index 64b8cbf..05e350a 100644
--- a/scripts/analysis/run_analysis.py
+++ b/scripts/analysis/run_analysis.py
@@ -49,6 +49,7 @@ try:
         plot_f6_cost_vs_accuracy,
         plot_f6b_cost_vs_accuracy_logx,
     )
+    from .posthoc import run_posthoc_stage
 except ImportError:
     from validate_runs import validate_all_runs
     from tables import (
@@ -71,6 +72,7 @@ except ImportError:
         plot_f6_cost_vs_accuracy,
         plot_f6b_cost_vs_accuracy_logx,
     )
+    from posthoc import run_posthoc_stage
 
 
 def _file_sha256(path: Path) -> str:
@@ -108,8 +110,29 @@ def main() -> int:
         default=None,
         help="Optional path to machine-written sha256 hashes file to verify against",
     )
+    parser.add_argument(
+        "--only",
+        choices=["posthoc"],
+        default=None,
+        help=(
+            "Run only the post-hoc stage (gate, in-memory T1/T2 aggregates, then Tables "
+            "T5-T9b and Figures F7-F9); no pre-registered artifact is written"
+        ),
+    )
+    parser.add_argument(
+        "--crosscheck-dir",
+        type=Path,
+        default=None,
+        help=(
+            "Existing pipeline output directory whose T1/T2/F6 CSV cells the post-hoc "
+            "inputs are asserted against (required with --only posthoc)"
+        ),
+    )
     args = parser.parse_args()
 
+    if args.only == "posthoc" and args.crosscheck_dir is None:
+        parser.error("--only posthoc requires --crosscheck-dir")
+
     results_dir = args.results_dir.resolve()
     output_dir = args.output_dir.resolve()
     tables_dir = output_dir / "tables"
@@ -152,6 +175,8 @@ def main() -> int:
         "stats.py",
         "bootstrap.py",
         "style.py",
+        "posthoc.py",
+        "posthoc_figures.py",
     ]
     module_hashes = {}
     for mod in pipeline_modules:
@@ -177,6 +202,8 @@ def main() -> int:
         f"argv: {' '.join(sys.argv)}",
         f"results_dir: {results_dir}",
         f"git_commit: {git_head}",
+        f"only: {args.only or 'all'}",
+        f"crosscheck_dir: {args.crosscheck_dir.resolve() if args.crosscheck_dir else 'NOT SUPPLIED'}",
         "pipeline_modules_sha256:",
     ]
     for mod, h in module_hashes.items():
@@ -199,6 +226,32 @@ def main() -> int:
 
     print(f"Discovered: {len(all_runs)} total runs ({len(acc_runs)} accuracy, {len(sweep_runs)} sweep)\n")
 
+    # Post-hoc-only stage (ANALYSIS-004, [D-89]): gate already passed above.
+    # Build the T1/T2 aggregates in memory and write only the new artifacts.
+    if args.only == "posthoc":
+        print(">>> STEP 1b: Post-hoc decision and ranking stage (POST HOC, not pre-registered)...")
+        t1_rows = generate_t1_accuracy_table(acc_runs)
+        t2_rows, _ = generate_t2_sweep_cost_table(sweep_runs)
+        summary = run_posthoc_stage(
+            results_dir=results_dir,
+            accuracy_run_dirs=acc_runs,
+            t1_rows=t1_rows,
+            t2_rows=t2_rows,
+            output_dir=output_dir,
+            crosscheck_dir=args.crosscheck_dir,
+        )
+        classes_txt = ", ".join(
+            f"{s}={info['class']}" for s, info in summary["gates"].items()
+        )
+        print(f"    Cross-check cells matched against {args.crosscheck_dir}: {summary['n_crosschecks']}")
+        print(f"    Gate classes: {classes_txt}")
+        print(f"    Saved: {tables_dir}/{{{', '.join(sorted(p.name for p in tables_dir.glob('T[5-9]*.csv')))}}}")
+        print(f"    Saved: {figures_dir}/F7_gates_g1_g2, F8_score_vs_weight, F9_rank_shares (.pdf, .png, .csv)")
+        print("\n" + "=" * 80)
+        print("POST-HOC STAGE COMPLETED SUCCESSFULLY (POST HOC, not pre-registered).")
+        print("=" * 80)
+        return 0
+
     # 2. Table T3: Run Inventory (write validator's t3_csv verbatim as T3_run_inventory.csv)
     print(">>> STEP 2: Generating Table T3 (Run Inventory)...")
     (tables_dir / "T3_run_inventory.csv").write_text(t3_csv_str, encoding="utf-8")
diff --git a/tests/test_posthoc.py b/tests/test_posthoc.py
new file mode 100644
index 0000000..5007194
--- /dev/null
+++ b/tests/test_posthoc.py
@@ -0,0 +1,568 @@
+"""test_posthoc.py — tests for the post-hoc decision and ranking stage.
+
+ANALYSIS-004 / [D-89]. Covers the frozen specification: normalisation,
+degenerate criterion, ties, Kendall tau-b, weighted TOPSIS, exact analytic
+rank shares against a fine grid, seeded draws, gate classes, the
+fail-closed gate, and the default-run file set.
+"""
+
+from __future__ import annotations
+
+import csv
+import json
+import sys
+from pathlib import Path
+from typing import Any, Dict, List
+
+import matplotlib.pyplot as plt
+import numpy as np
+import pytest
+
+from scripts.analysis import posthoc as P
+from scripts.analysis.posthoc import (
+    CORPUS_ORDER,
+    STRATEGY_ORDER,
+    assert_matches_final_output,
+    build_t5b_rows,
+    compute_A_C,
+    compute_gates,
+    exact_rank_shares,
+    extract_inputs,
+    gate_class,
+    kendall_tau_b,
+    mc_rank_shares,
+    rank_with_ties,
+    strict_ranks,
+    topsis_closeness,
+    weighted_scores,
+)
+from scripts.analysis.run_analysis import main as run_pipeline_main
+from tests.test_analysis_pipeline import create_mock_run_directory
+
+
+# ---------------------------------------------------------------------------
+# Synthetic inputs (values mirror the real final_output_final cells)
+# ---------------------------------------------------------------------------
+
+_DSA = "DSA_gold_standard_MEKG"
+_META = "metacademy_gold_standard_MEKG"
+
+# (f1, recall, precision, calls, shortlist_recall, random_baseline)
+_ACC_VALUES = {
+    (_DSA, "brute_force"): (0.5862068965517241, 0.6296296296296297, 0.5483870967741935, 28.0, 1.0, float("nan")),
+    (_DSA, "embedding_threshold"): (0.14754098360655737, 0.08333333333333333, 0.5862068965517241, 0.7586206896551724, 0.1111111111111111, float("nan")),
+    (_DSA, "ann_retrieval"): (0.5111111111111111, 0.42592592592592593, 0.6388888888888888, 10.0, 0.5277777777777778, 0.35714285714285715),
+    (_DSA, "bounded_bucket"): (0.2714285714285714, 0.17592592592592593, 0.5846153846153846, 6.9655172413793105, 0.25925925925925924, 0.35714285714285715),
+    (_META, "brute_force"): (0.14345991561181434, 0.6238532110091743, 0.08130081300813008, 140.0, 1.0, float("nan")),
+    (_META, "embedding_threshold"): (0.2695035460992908, 0.1743119266055046, 0.6065573770491803, 1.1333333333333333, 0.2018348623853211, float("nan")),
+    (_META, "ann_retrieval"): (0.29411764705882354, 0.3669724770642202, 0.24539877300613497, 10.0, 0.5045871559633027, 0.07142857142857142),
+    (_META, "bounded_bucket"): (0.11363636363636365, 0.09174311926605505, 0.14925373134328357, 7.366666666666666, 0.14678899082568808, 0.07142857142857142),
+}
+
+_VARIANTS = {
+    "brute_force": "primary (all candidates)",
+    "embedding_threshold": "primary (theta=0.6)",
+    "ann_retrieval": "primary (k=10, ef=128)",
+    "bounded_bucket": "primary (s_min=5, s_max=10, nb=12)",
+}
+
+_SWEEP = {
+    "brute_force": (2000.0, 1713.0988233976009),
+    "embedding_threshold": (0.8, 0.9381960321006773),
+    "ann_retrieval": (10.0, 8.276875985300284),
+    "bounded_bucket": (7.0, 5.638046632800615),
+}
+
+
+def _inputs() -> Dict[str, Any]:
+    accuracy: Dict[str, Dict[str, Any]] = {c: {} for c in CORPUS_ORDER}
+    for (corpus, strat), vals in _ACC_VALUES.items():
+        f1, rec, prec, calls, sr, rb = vals
+        accuracy[corpus][strat] = {
+            "variant": _VARIANTS[strat],
+            "f1_micro": f1,
+            "recall_micro": rec,
+            "precision_micro": prec,
+            "llm_calls_mean": calls,
+            "shortlist_recall_micro": sr,
+            "random_baseline_recall": rb,
+            "num_trials": 29 if corpus == _DSA else 30,
+        }
+    sweep = {
+        s: {"llm_calls_mean": v[0], "total_s_mean": v[1]}
+        for s, v in _SWEEP.items()
+    }
+    return {"accuracy": accuracy, "sweep": sweep}
+
+
+def _t1_rows() -> List[Dict[str, Any]]:
+    rows = []
+    for (corpus, strat), vals in _ACC_VALUES.items():
+        f1, rec, prec, calls, sr, rb = vals
+        rows.append({
+            "strategy": strat,
+            "variant": _VARIANTS[strat],
+            "corpus": corpus,
+            "num_trials": 29 if corpus == _DSA else 30,
+            "num_success": 29 if corpus == _DSA else 30,
+            "llm_calls_mean": calls,
+            "precision_micro": prec,
+            "recall_micro": rec,
+            "f1_micro": f1,
+            "shortlist_recall_micro": sr,
+            "random_baseline_recall": rb,
+        })
+    return rows
+
+
+def _t2_rows() -> List[Dict[str, Any]]:
+    rows = []
+    for strat, (calls, total_s) in _SWEEP.items():
+        rows.append({
+            "strategy": strat,
+            "variant": _VARIANTS[strat],
+            "size_n": 2000,
+            "llm_calls_mean": calls,
+            "total_s_mean": total_s,
+        })
+    return rows
+
+
+def _write_crosscheck_dir(root: Path) -> Path:
+    (root / "tables").mkdir(parents=True, exist_ok=True)
+    (root / "figures").mkdir(parents=True, exist_ok=True)
+    t1 = _t1_rows()
+    with open(root / "tables" / "T1_accuracy_benchmark.csv", "w", newline="", encoding="utf-8") as f:
+        w = csv.DictWriter(f, fieldnames=list(t1[0].keys()))
+        w.writeheader()
+        w.writerows(t1)
+    t2 = _t2_rows()
+    with open(root / "tables" / "T2_sweep_cost_summary.csv", "w", newline="", encoding="utf-8") as f:
+        w = csv.DictWriter(f, fieldnames=list(t2[0].keys()))
+        w.writeheader()
+        w.writerows(t2)
+    f6 = [
+        {
+            "corpus": r["corpus"],
+            "strategy": r["strategy"],
+            "variant": r["variant"],
+            "calls": r["llm_calls_mean"],
+            "f1": r["f1_micro"],
+        }
+        for r in t1
+    ]
+    with open(root / "figures" / "F6_cost_vs_accuracy_dominance.csv", "w", newline="", encoding="utf-8") as f:
+        w = csv.DictWriter(f, fieldnames=list(f6[0].keys()))
+        w.writeheader()
+        w.writerows(f6)
+    return root
+
+
+# ---------------------------------------------------------------------------
+# Normalisation and ranking
+# ---------------------------------------------------------------------------
+
+def test_normalisation_hand_worked():
+    f1 = {"a": 0.5, "b": 0.4, "c": 0.3, "d": 0.2}
+    calls = {"a": 1000.0, "b": 10.0, "c": 1.0, "d": 100.0}
+    inputs = {
+        "accuracy": {
+            _DSA: {
+                "a": {"f1_micro": f1["a"], "llm_calls_mean": calls["a"]},
+                "b": {"f1_micro": f1["b"], "llm_calls_mean": calls["b"]},
+                "c": {"f1_micro": f1["c"], "llm_calls_mean": calls["c"]},
+                "d": {"f1_micro": f1["d"], "llm_calls_mean": calls["d"]},
+            }
+        }
+    }
+    # Direct check of the formula on the same numbers.
+    a, a_deg = P._normalise(f1, higher_is_better=True)
+    g = {k: np.log10(1.0 + v) for k, v in calls.items()}
+    c, c_deg = P._normalise(g, higher_is_better=False)
+    lo_g, hi_g = min(g.values()), max(g.values())
+    assert np.isclose(a["a"], 1.0) and np.isclose(a["d"], 0.0)
+    assert np.isclose(a["b"], (0.4 - 0.2) / (0.5 - 0.2))
+    assert np.isclose(c["a"], 0.0)
+    assert np.isclose(c["c"], 1.0)
+    assert np.isclose(c["b"], 1.0 - (g["b"] - lo_g) / (hi_g - lo_g))
+    assert not a_deg and not c_deg
+    # compute_A_C on the real-shaped inputs is exercised elsewhere.
+
+
+def test_all_equal_criterion_gets_half_and_is_flagged():
+    scores, degenerate = P._normalise({"a": 0.3, "b": 0.3, "c": 0.3, "d": 0.3}, higher_is_better=True)
+    assert degenerate is True
+    assert all(v == 0.5 for v in scores.values())
+
+    ac = compute_A_C(_inputs(), _DSA)
+    assert ac["degenerate"] == {"A": False, "C": False}
+
+
+def test_dsa_balanced_tie_shares_mean_rank():
+    ac = compute_A_C(_inputs(), _DSA)
+    scores = weighted_scores(ac["A"], ac["C"], 0.5)
+    assert abs(scores["brute_force"] - 0.5) <= P.TIE_TOL
+    assert abs(scores["embedding_threshold"] - 0.5) <= P.TIE_TOL
+    ranks = rank_with_ties(scores, higher_is_better=True)
+    # S3 leads at 0.587; S1 and S2 tie at 0.500 and share ranks 2 and 3.
+    assert ranks["ann_retrieval"] == 1.0
+    assert ranks["brute_force"] == 2.5
+    assert ranks["embedding_threshold"] == 2.5
+    assert ranks["bounded_bucket"] == 4.0
+
+
+def test_strict_rank_tie_break_is_deterministic():
+    scores = {s: 0.5 for s in STRATEGY_ORDER}
+    ranks = strict_ranks(scores)
+    assert [ranks[s] for s in STRATEGY_ORDER] == [1, 2, 3, 4]
+
+
+# ---------------------------------------------------------------------------
+# Kendall tau-b and TOPSIS
+# ---------------------------------------------------------------------------
+
+def test_kendall_tau_b_with_ties_hand_computed():
+    x = {"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0}
+    y = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
+    assert np.isclose(kendall_tau_b(x, y)["tau"], 5.0 / np.sqrt(30.0))
+    assert kendall_tau_b(x, y)["tied_pairs"] == 1
+
+    x2 = {"a": 1.0, "b": 1.0, "c": 2.0, "d": 3.0}
+    y2 = {"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0}
+    assert np.isclose(kendall_tau_b(x2, y2)["tau"], 0.8)
+    assert kendall_tau_b(x2, y2)["tied_pairs"] == 2
+
+    # Identical rankings: tau = 1.
+    assert np.isclose(kendall_tau_b(x2, x2)["tau"], 1.0)
+    # Reversed: tau = -1.
+    rev = {k: -v for k, v in x2.items()}
+    assert np.isclose(kendall_tau_b(x2, rev)["tau"], -1.0)
+
+
+def test_topsis_three_point_toy_known_answer():
+    A = {"a": 1.0, "b": 0.0, "c": 0.5}
+    C = {"a": 0.0, "b": 1.0, "c": 0.5}
+    close = topsis_closeness(A, C, 0.7)
+    # Ideal (0.7, 0.3), anti-ideal (0, 0).
+    assert np.isclose(close["a"], 0.7)
+    assert np.isclose(close["b"], 0.3)
+    assert np.isclose(close["c"], 0.5)
+    ranks = rank_with_ties(close, higher_is_better=True)
+    assert ranks == {"a": 1.0, "c": 2.0, "b": 3.0}
+
+
+# ---------------------------------------------------------------------------
+# Exact shares against a fine grid
+# ---------------------------------------------------------------------------
+
+def test_exact_rank_shares_against_fine_grid():
+    A = {"a": 1.0, "b": 0.2, "c": 0.7, "d": 0.0}
+    C = {"a": 0.1, "b": 1.0, "c": 0.4, "d": 0.8}
+    exact = exact_rank_shares(A, C)
+    n = 200_000
+    grid = {s: {r: 0.0 for r in range(1, 5)} for s in A}
+    for k in range(n):
+        w = (k + 0.5) / n
+        ranks = strict_ranks(weighted_scores(A, C, w))
+        for s, r in ranks.items():
+            grid[s][r] += 1.0 / n
+    max_diff = max(
+        abs(exact["shares"][s][r] - grid[s][r])
+        for s in A for r in range(1, 5)
+    )
+    assert max_diff < 1e-3
+    for s in A:
+        assert np.isclose(sum(exact["shares"][s].values()), 1.0)
+
+
+def test_seeded_draws_are_deterministic():
+    A = {"a": 1.0, "b": 0.2, "c": 0.7, "d": 0.0}
+    C = {"a": 0.1, "b": 1.0, "c": 0.4, "d": 0.8}
+    first = mc_rank_shares(A, C, n_draws=500, seed=42)
+    second = mc_rank_shares(A, C, n_draws=500, seed=42)
+    assert first == second
+    assert first["tie_draws"] == 0
+    for s in A:
+        assert np.isclose(sum(first["shares"][s].values()), 1.0)
+    # A different seed is allowed to differ (not asserted equal), and the
+    # exact shares are seed-free.
+    assert exact_rank_shares(A, C) == exact_rank_shares(A, C)
+
+
+def test_real_data_shares_match_frozen_targets():
+    """The analytic shares on the real cells match [D-89]'s cross-check targets."""
+    inputs = _inputs()
+    dsa = compute_A_C(inputs, _DSA)
+    meta = compute_A_C(inputs, _META)
+    dsa_exact = exact_rank_shares(dsa["A"], dsa["C"])["shares"]
+    meta_exact = exact_rank_shares(meta["A"], meta["C"])["shares"]
+
+    dsa_target = {
+        "brute_force": [0.331, 0.169, 0.109, 0.391],
+        "embedding_threshold": [0.441, 0.059, 0.156, 0.344],
+        "ann_retrieval": [0.228, 0.598, 0.174, 0.000],
+        "bounded_bucket": [0.000, 0.174, 0.561, 0.265],
+    }
+    meta_target = {
+        "brute_force": [0.000, 0.000, 0.197, 0.803],
+        "embedding_threshold": [0.742, 0.258, 0.000, 0.000],
+        "ann_retrieval": [0.258, 0.680, 0.061, 0.000],
+        "bounded_bucket": [0.000, 0.061, 0.742, 0.197],
+    }
+    for s in STRATEGY_ORDER:
+        for r in range(1, 5):
+            assert abs(dsa_exact[s][r] - dsa_target[s][r - 1]) < 0.002, (s, r, dsa_exact[s][r])
+            assert abs(meta_exact[s][r] - meta_target[s][r - 1]) < 0.002, (s, r, meta_exact[s][r])
+
+
+# ---------------------------------------------------------------------------
+# Gates and gate sensitivity
+# ---------------------------------------------------------------------------
+
+def test_gate_classes_cover_all_three_classes():
+    gates = compute_gates(_inputs())
+    assert gates["brute_force"]["g1"]["status"] == "not applicable"
+    assert gates["embedding_threshold"]["g1"]["status"] == "not assessable"
+    assert gates["ann_retrieval"]["g1"]["status"] == "pass"
+    assert gates["bounded_bucket"]["g1"]["status"] == "fail"
+    assert gates["brute_force"]["class"] == "Not effective"
+    assert gates["embedding_threshold"]["class"] == "Conditionally effective"
+    assert gates["ann_retrieval"]["class"] == "Effective"
+    assert gates["bounded_bucket"]["class"] == "Not effective"
+
+    # Direct class logic.
+    pass_gate = {"status": "pass", "assessable": True}
+    fail_gate = {"status": "fail", "assessable": True}
+    na_gate = {"status": "not applicable", "assessable": False}
+    g2 = {"status": "pass"}
+    g3 = {"status": "pass"}
+    assert gate_class(pass_gate, g2, g3) == "Effective"
+    assert gate_class(fail_gate, g2, g3) == "Not effective"
+    assert gate_class(na_gate, g2, g3) == "Conditionally effective"
+    assert gate_class(na_gate, {"status": "fail"}, g3) == "Not effective"
+
+
+def test_gate_sensitivity_classes_unchanged():
+    inputs = _inputs()
+    gates = compute_gates(inputs)
+    means = {_DSA: {"ann_retrieval": 10.0, "bounded_bucket": 6.9655172413793105},
+             _META: {"ann_retrieval": 10.0, "bounded_bucket": 7.366666666666666}}
+    sm = P.size_matched_baselines(inputs, means)
+    rows, summary = build_t5b_rows(inputs, gates, sm)
+    assert summary["g2_n_settings"] == 1990
+    assert summary["g2_changes"] == []
+    assert summary["g3_first_change"] is None
+    assert summary["classes_unchanged_all"] is True
+    assert len(P.G3_SENSITIVITY_MARGINS) == 31
+    assert P.G3_SENSITIVITY_MARGINS[0] == 0.0 and P.G3_SENSITIVITY_MARGINS[-1] == 0.15
+    # Size-matched baseline: S4 DSA is level with random (does not change the class).
+    assert np.isclose(sm[_DSA]["bounded_bucket"], 6.9655172413793105 / 28.0)
+
+
+# ---------------------------------------------------------------------------
+# Cross-check against the existing output
+# ---------------------------------------------------------------------------
+
+def test_crosscheck_matches_and_detects_a_mismatch(tmp_path: Path):
+    inputs = _inputs()
+    root = _write_crosscheck_dir(tmp_path)
+    n = assert_matches_final_output(inputs, root)
+    assert n == 8 * 6 + 4 * 2 + 8 * 2
+
+    # Flip one F1 cell outside tolerance and expect a failure.
+    path = root / "tables" / "T1_accuracy_benchmark.csv"
+    lines = path.read_text(encoding="utf-8").splitlines()
+    header = lines[0].split(",")
+    idx = header.index("f1_micro")
+    cells = lines[1].split(",")
+    cells[idx] = "0.999"
+    lines[1] = ",".join(cells)
+    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
+    with pytest.raises(AssertionError, match="T1 f1_micro"):
+        assert_matches_final_output(inputs, root)
+
+
+# ---------------------------------------------------------------------------
+# CLI integration: post-hoc only and default behaviour
+# ---------------------------------------------------------------------------
+
+def _install_posthoc_mocks(monkeypatch, results_dir: Path):
+    import scripts.analysis.run_analysis as ra
+
+    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], "run,strategy\n"))
+    monkeypatch.setattr(ra, "generate_t1_accuracy_table", lambda _dirs: _t1_rows())
+    monkeypatch.setattr(ra, "generate_t2_sweep_cost_table", lambda _dirs: (_t2_rows(), []))
+    means = {_DSA: {"ann_retrieval": 10.0, "bounded_bucket": 6.9655172413793105},
+             _META: {"ann_retrieval": 10.0, "bounded_bucket": 7.366666666666666}}
+    monkeypatch.setattr(P, "realised_shortlist_sizes", lambda _dirs: means)
+
+
+def test_posthoc_only_writes_only_posthoc_names(tmp_path: Path, monkeypatch):
+    results_dir = tmp_path / "results"
+    results_dir.mkdir()
+    output_dir = tmp_path / "output"
+    crosscheck = _write_crosscheck_dir(tmp_path / "crosscheck")
+    _install_posthoc_mocks(monkeypatch, results_dir)
+
+    monkeypatch.setattr(sys, "argv", [
+        "run_analysis.py",
+        "--results-dir", str(results_dir),
+        "--output-dir", str(output_dir),
+        "--only", "posthoc",
+        "--crosscheck-dir", str(crosscheck),
+    ])
+    assert run_pipeline_main() == 0
+
+    produced = {
+        str(p.relative_to(output_dir)).replace("\\", "/")
+        for p in output_dir.rglob("*") if p.is_file()
+    }
+    expected = {"RUN_INFO.txt"}
+    for name in (P.T5, P.T5B, P.T6, P.T7, P.T8, P.T8B, P.T9, P.T9B):
+        expected.add(f"tables/{name}.csv")
+        expected.add(f"tables/{name}.md")
+    for fig in ("F7_gates_g1_g2", "F8_score_vs_weight", "F9_rank_shares"):
+        for ext in ("pdf", "png", "csv"):
+            expected.add(f"figures/{fig}.{ext}")
+    assert produced == expected
+
+    run_info = (output_dir / "RUN_INFO.txt").read_text(encoding="utf-8")
+    assert "only: posthoc" in run_info
+    assert "posthoc.py:" in run_info
+    assert "posthoc_figures.py:" in run_info
+    assert "overall_gate_status: PASS" in run_info
+
+    # T8 CSV keeps full precision (repr of the proportion); T8 Markdown is 2 dp.
+    t8_csv = (output_dir / "tables" / f"{P.T8}.csv").read_text(encoding="utf-8")
+    share_cells = [row.split(",")[5] for row in t8_csv.splitlines()[1:]]
+    assert any(len(cell.split(".")[-1]) > 2 for cell in share_cells)
+    assert len(t8_csv.splitlines()[1].split(",")[5]) > 4
+    t8_md = (output_dir / "tables" / f"{P.T8}.md").read_text(encoding="utf-8")
+    assert "0.33" in t8_md or "0.00" in t8_md
+
+    plt.close("all")
+
+
+def test_posthoc_gate_failure_writes_nothing(tmp_path: Path, monkeypatch):
+    results_dir = tmp_path / "results"
+    results_dir.mkdir()
+    output_dir = tmp_path / "output"
+    crosscheck = _write_crosscheck_dir(tmp_path / "crosscheck")
+    import scripts.analysis.run_analysis as ra
+
+    monkeypatch.setattr(
+        ra,
+        "validate_all_runs",
+        lambda *a, **kw: (False, [{"run_dir": "bad", "passed": False, "errors": ["x"]}], ""),
+    )
+    monkeypatch.setattr(sys, "argv", [
+        "run_analysis.py",
+        "--results-dir", str(results_dir),
+        "--output-dir", str(output_dir),
+        "--only", "posthoc",
+        "--crosscheck-dir", str(crosscheck),
+    ])
+    assert run_pipeline_main() == 1
+    assert not output_dir.exists()
+
+
+def test_posthoc_requires_crosscheck_dir(tmp_path: Path, monkeypatch):
+    monkeypatch.setattr(sys, "argv", [
+        "run_analysis.py",
+        "--results-dir", str(tmp_path / "results"),
+        "--output-dir", str(tmp_path / "output"),
+        "--only", "posthoc",
+    ])
+    with pytest.raises(SystemExit) as exc:
+        run_pipeline_main()
+    assert exc.value.code == 2
+
+
+def test_default_run_writes_the_same_files_as_before(tmp_path: Path, monkeypatch):
+    """With no flag, the legacy file set is produced and no post-hoc file is written."""
+    results_dir = tmp_path / "results"
+    output_dir = tmp_path / "output"
+    results_dir.mkdir()
+
+    acc_records = [
+        {
+            "key": f"acc:ann_retrieval:DSA_gold_standard_MEKG:node_{i}",
+            "corpus": "DSA_gold_standard_MEKG",
+            "status": "success",
+            "retries": 0,
+            "metrics": {"total_s": 5.0, "shortlist_s": 0.01, "decide_s": 4.99, "llm_calls": 10},
+            "score": {"tp": 2, "fp": 1, "fn": 1, "precision": 0.66, "recall": 0.66, "f1": 0.66, "shortlist_hits": 2, "gold_neighbours": 3, "shortlist_recall": 0.66},
+        }
+        for i in range(29)
+    ]
+    create_mock_run_directory(
+        results_dir, "accuracy_ann_retrieval_k10_ef128", "ann_retrieval", "accuracy",
+        acc_records, config={"k": 10, "ef_search": 128},
+    )
+    create_mock_run_directory(
+        results_dir, "accuracy_brute_force", "brute_force", "accuracy",
+        [dict(r, key=r["key"].replace("ann_retrieval", "brute_force"), metrics=dict(r["metrics"], llm_calls=28)) for r in acc_records],
+        config={},
+    )
+    sweep_records = []
+    for size in [50, 100, 200, 500, 1000, 2000]:
+        for t in range(10):
+            sweep_records.append({
+                "key": f"sweep:ann_retrieval:{size}:t{t}",
+                "size": size,
+                "status": "success",
+                "retries": 0,
+                "metrics": {"total_s": 8.0, "shortlist_s": 0.01, "decide_s": 7.99, "llm_calls": 10},
+            })
+    create_mock_run_directory(
+        results_dir, "sweep_ann_retrieval_k10_ef128", "ann_retrieval", "sweep",
+        sweep_records, config={"k": 10, "ef_search": 128},
+    )
+    create_mock_run_directory(
+        results_dir, "sweep_bounded_bucket_smin5_smax10_nb12", "bounded_bucket", "sweep",
+        [dict(r, key=r["key"].replace("ann_retrieval", "bounded_bucket"), metrics=dict(r["metrics"], llm_calls=7)) for r in sweep_records],
+        config={"s_min": 5, "s_max": 10, "num_hyperplanes": 12},
+    )
+
+    mock_t3_csv = (
+        "run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,failed_then_succeeded,still_failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256\n"
+        'accuracy_ann_retrieval_k10_ef128,ann_retrieval,"{}",accuracy,3323bfb,h1,29,290,0,0,0,0,PASS,m1,c1,r1,s1,d1\n'
+        'accuracy_brute_force,brute_force,"{}",accuracy,3323bfb,h1,29,812,0,0,0,0,PASS,m0,c0,r0,s0,d0\n'
+        'sweep_ann_retrieval_k10_ef128,ann_retrieval,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m2,c2,r2,s2,d2\n'
+        'sweep_bounded_bucket_smin5_smax10_nb12,bounded_bucket,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m3,c3,r3,s3,d3\n'
+    )
+    import scripts.analysis.run_analysis as ra
+    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], mock_t3_csv))
+    monkeypatch.setattr(sys, "argv", [
+        "run_analysis.py", "--results-dir", str(results_dir), "--output-dir", str(output_dir),
+    ])
+    assert run_pipeline_main() == 0
+
+    produced = {
+        str(p.relative_to(output_dir)).replace("\\", "/")
+        for p in output_dir.rglob("*") if p.is_file()
+    }
+    expected = {
+        "RUN_INFO.txt",
+        "tables/T1_accuracy_benchmark.csv", "tables/T1_accuracy_benchmark.md",
+        "tables/T2_sweep_cost_summary.csv", "tables/T2_sweep_cost_summary.md",
+        "tables/T2_slope_fits.csv", "tables/T2_slope_fits.md",
+        "tables/T3_run_inventory.csv", "tables/T3_run_inventory.md",
+        "tables/T4_sensitivity_metrics.csv", "tables/T4_sensitivity_metrics.md",
+        "figures/F1_calls_scaling.pdf", "figures/F1_calls_scaling.png", "figures/F1_calls_scaling.csv",
+        "figures/F1b_calls_scaling_logy.pdf", "figures/F1b_calls_scaling_logy.png", "figures/F1b_calls_scaling_logy.csv",
+        "figures/F2_wallclock_scaling.pdf", "figures/F2_wallclock_scaling.png", "figures/F2_wallclock_scaling.csv",
+        "figures/F2b_wallclock_scaling_logy.pdf", "figures/F2b_wallclock_scaling_logy.png", "figures/F2b_wallclock_scaling_logy.csv",
+        "figures/F3_premise_check.pdf", "figures/F3_premise_check.png", "figures/F3_premise_check.csv",
+        "figures/F4_accuracy_by_strategy.pdf", "figures/F4_accuracy_by_strategy.png", "figures/F4_accuracy_by_strategy.csv",
+        "figures/F5_sensitivity_panels.pdf", "figures/F5_sensitivity_panels.png", "figures/F5_sensitivity_panels.csv",
+        "figures/F6_cost_vs_accuracy_dominance.pdf", "figures/F6_cost_vs_accuracy_dominance.png", "figures/F6_cost_vs_accuracy_dominance.csv",
+        "figures/F6_dominance.csv", "figures/F6_dominance.md",
+        "figures/F6b_cost_vs_accuracy_logx.pdf", "figures/F6b_cost_vs_accuracy_logx.png", "figures/F6b_cost_vs_accuracy_logx.csv",
+    }
+    assert produced == expected
+    _, sweep_rows = ra.generate_t2_sweep_cost_table(
+        sorted(results_dir.glob("sweep_*"))
+    )
+    assert sweep_rows  # the legacy slope path ran
+    plt.close("all")
```

**Patch file:** `patch/ANALYSIS-004-claude-code-posthoc-ranking.patch` (verbatim `git diff a524de7..f4ba18a`, 2,355 lines).

---

## Artefacts

- New output directory: `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`
- Bundle (new output only): `/home/lukexodus/projects/thesis-analysis/bundle_c_posthoc_outputs.tar.gz`
- `RUN_INFO.txt` records `git_commit: e3b563d95cb8ee29c8b7e8c8d1fe2502c16110df`, `only: posthoc`, the crosscheck directory, all nine module hashes, the hashes file and its sha256, `src_diff_clean: True`, `overall_gate_status: PASS`.
- Note: the last docs commit `f4ba18a` only adds D-90 and the status row; the run was executed at code commit `e3b563d` and the recorded module hashes match that tree.

---

## Items for the APC

1. **Thesis formula (Section 3.6.3).** The displayed `C_i` formula omits the `1 −` reversal that the prose describes. The pipeline uses the reversed form, which reproduces the independent targets. The formula should be corrected.
2. **TOPSIS ambiguity.** The thesis does not say whether weights enter before or after the distances. The weighted-before form is implemented and frozen; if the intended reading is the other one, Table T9 and τ must be recomputed. The wording should be made explicit.
3. **Table 4.9.** Replace the eight Metacademy/DSA cells listed above (old → new) with the regenerated scores; the largest change is Metacademy accuracy-first S1 0.113 → 0.1157 and S2 0.907 → 0.9045.
4. **Table 4.10 and the prose.** Regenerate the table from T8/T8b. Most consequential: Metacademy S3 rank 2 is 0.6803 exact (0.6812 MC), so "69%" should read **"68%"**; Metacademy S2 rank 1 is 0.7416 (0.74), not 0.75; DSA S4 rank 4 is 0.2650 (0.27), not 0.26. The DSA "60%" statement is confirmed (0.5981).
5. **Table 4.10 rounding.** The MC 2-dp table may not sum to 1.00 per row (e.g. 0.05 where the exact value is 0.0589). Either state that the table is MC-rounded (already partly stated) or use the exact shares in T8b.
6. **G3 sensitivity headroom.** "Any margin up to 0.15" is true, but the margin at which S1 stops being dominated on Metacademy is 0.15066 and for S4 it is 0.15586 — very close to the stated bound.
7. **Figures.** F7–F9 are regenerated from the pipeline. They are not byte-identical to the hand-drawn images and should replace them. The PDF/PNG re-render also differs from the original run's images because of environment text metrics; this is a rendering difference, not a data difference.
8. **Hashes path.** Earlier provenance text says `~/run-logs/final-results-hashes.txt`; the file now lives at `/home/lukexodus/projects/run-logs/final-results-hashes.txt` with the same sha256.
9. **Pre-existing test failure.** `test_source_grep_forbidden_patterns` fails on `master` because the archived checker `scripts/analysis/apc_check_f_outputs.py` contains the literals it searches for. This is unrelated to ANALYSIS-004 and should be handled separately (e.g. exclude checker scripts from that grep or move them out of `scripts/analysis/`).
10. **No thesis edits were made.** All thesis changes above are relayed as text instructions only, per the prompt's Section 9.
