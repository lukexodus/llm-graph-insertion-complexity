# ANALYSIS-004 — Post-hoc classification and ranking artifacts (Tables 4.7–4.10, Figures 4.11–4.13, TOPSIS/τ cross-checks)

Standalone prompt from the APC AI, relayed by Luke. Archive this file as
`docs/prompts/ANALYSIS-004-PROMPT.md` first (AGENTS.md, "Prompt archiving").

- **Task ID:** ANALYSIS-004 (new; add a row to `docs/tasks/status.md`)
- **Branch / worktree:** `task/ANALYSIS-004`, via `git worktree add ../llm-graph-insertion-complexity-ANALYSIS-004 -b task/ANALYSIS-004` (check `git worktree list` first, per AGENTS.md "Parallel work and worktrees")
- **Reserved decision IDs:** **D-89** (specification, committed BEFORE any computation) and **D-90** (implementation, provenance, and any corrections). Confirm with `./scripts/manage-decisions.py --next` that D-89 is free. If it is already used, STOP and report; do not renumber.
- **Agent:** you are the local agent; use your own name in file names (`claude-code`, `gemini` or `opencode`).

## 0. Read first, in this order

1. `AGENTS.md`, then `docs/context/complete-context.md` (in full).
2. `docs/tasks/status.md` (ANALYSIS-001 … ANALYSIS-003 rows), `docs/context/analysis-plan.md` (the frozen plan, Rules R1–R3, Amendments 1–3), and decision-log entries D-79, D-83, D-84, D-85, D-86, D-87, D-88.
3. `scripts/analysis/` (all modules: `run_analysis.py`, `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`) and `tests/test_analysis_pipeline.py`. ANALYSIS-003 (D-87) is the closest precedent for how a post-hoc/exploratory add-on is wired in; follow its conventions.
4. The specification below. **The thesis copy in `docs/thesis/` is older (Chapters 1–3) and may not contain Section 3.6 or Section 4.4.1.** The specification in this prompt is authoritative for this task. If Luke has placed the revised thesis (`_REVISED__…_With_Chapter_4.md`) somewhere readable, read only its Sections 3.6 and 4.4.1 and report any disagreement with this prompt instead of silently picking one.

Verify anything in this prompt that you can check yourself (file names, function signatures, column names, current values) and say so in the report whether or not it held. In particular, I have not seen `scripts/analysis/*` or `analysis-plan.md`; every statement below about them is an assumption.

## 1. Goal and hard constraints

The revised thesis adds a post-hoc decision and ranking framework (thesis Section 3.6, applied in Section 4.4.1). Its tables and figures were produced by a teammate's scratch script. They must be regenerated inside the repo's analysis pipeline so that they are reproducible and gate-validated. TOPSIS, Kendall's τ and a wall-clock-substituted score check are specified but have never been computed. Compute them too.

Generate ONLY the new artifacts. Do not regenerate or alter anything that already exists.

- **No live API calls. No new experiment runs.** The results directory is read-only input.
- **The validation gate stays fail-closed.** Import and call `validate_all_runs` exactly as `run_analysis.py` does today (`--results-dir`, `--src-diff-clean`, `--hashes`). If it fails, the new stage must not write artifacts. Do not weaken or bypass it.
- **Do not modify** `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, or `style.py`. Import from them (reuse `stats.evaluate_dominance` UNCHANGED for G3, as D-87(5) did for F6b). Put new code in new modules, e.g. `scripts/analysis/posthoc.py` and `scripts/analysis/posthoc_figures.py`. The only existing file you may edit is `run_analysis.py`, minimally: add a flag (suggested `--only posthoc`) that runs gate → aggregates → post-hoc stage and nothing else. With no flag, behaviour must be exactly as today.
- **Pre-registered and existing artifacts must be byte-identical.** Run the new stage into a NEW output directory (suggested `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`). Then produce a no-change proof: either re-run the default pipeline into a scratch dir and `diff -r` it against `/home/lukexodus/projects/thesis-analysis/final_output_final`, or show that the new stage writes no file outside its own names. Report which. (Past provenance: results dir `/home/lukexodus/projects/llm-graph-insertion-complexity/results`, hashes file `/home/lukexodus/run-logs/final-results-hashes.txt`, final run at commit `554bde34…`.)
- Take inputs from the same in-memory aggregates that produce Tables T1/T2 and Figure F6, not from re-parsed CSVs. Then assert that the values used equal the corresponding cells of the existing `final_output_final` T1/T2/F6 CSVs.
- Prefer the standard library and packages already in `pyproject.toml`. If SciPy is not available, implement Kendall τ-b by hand and unit-test it against a worked example.

## 2. Order of work (this order is mandatory)

1. **First commit, before any computation:** add decision **D-89** to `docs/decisions/decision-log.md` and an "Amendment 4" entry to `docs/context/analysis-plan.md`. They freeze this specification (Section 3 below) including every choice you had to make: the RNG family, tie tolerance, TOPSIS weighting form, and output names. Label everything **post hoc, specified after the Chapter 4 measurements existed**, not pre-registered. The thesis text says the thresholds and weights are recorded "before the ranks are computed and are not changed afterwards". Honour that literally: do not edit D-89's numbers after you have run anything. If you find an error, add a correction in D-90.
2. Implement the new modules and the flag, with tests (Section 7).
3. Run the new stage, make the no-change proof, compare against the cross-check targets (Section 6), and write the report.

## 3. Specification (frozen into D-89)

**Corpora:** DSA (29 trials, `DSA_gold_standard_MEKG`) and Metacademy (30 trials, `metacademy_gold_standard_MEKG`). Always per corpus; never pool.

**Strategies (primary configurations only):** S1 brute force (`primary (all candidates)`), S2 embedding threshold (`primary (theta=0.6)`), S3 ANN (`primary (k=10, ef=128)`), S4 bounded bucket (`primary (s_min=5, s_max=10, nb=12)`).

**Inputs per strategy and corpus** (accuracy runs): `f1_micro`, `recall_micro`, `precision_micro`, `llm_calls_mean`, `shortlist_recall_micro`, `random_baseline_recall` (this is the pre-registered min(k, m)/m; NaN for S1 and S2).
**Inputs per strategy** (sweep runs, n = 2000): `llm_calls_mean` and `total_s_mean`.

### Gates (Table T5)

- **G1, beats chance:** `shortlist_recall_micro > random_baseline_recall` on EVERY corpus. Status values: `not applicable` (S1, whole-graph shortlist), `not assessable` (S2, no cap), else pass/fail per corpus and overall.
- **G2, practical cost:** sweep mean calls at n = 2000 is ≤ 50. The 50 is the upper end of the 22–50 prompts reported by Funk et al.; it is a reference point from a different task, not a standard.
- **G3, not dominated:** not Pareto-dominated on (calls, micro-F1) on either corpus, using `stats.evaluate_dominance` unchanged, with the study's 0.025 F1 margin ("not distinguishable" counts as NOT dominated). Use the accuracy-run calls, as Figure F6 does.
- **Class:** Effective = passes every gate and G1 is assessable. Conditionally effective = passes every assessable gate but G1 is not assessable. Not effective = fails any assessable gate.

### Gate sensitivity (Table T5b, supports a paragraph already in the thesis)

Show that the classes do not change under: (a) any G2 limit from 10 to 1,999 calls; (b) G1 with a size-matched random baseline (compute it from the actual shortlist sizes, and state how); (c) G3 margin from 0 to 0.15 F1 in 0.005 steps. Report the first margin at which any G3 outcome changes, or "none up to 0.15".

### Single-criterion ranks (Table T6)

Per corpus: rank 1 = best on micro-F1 (higher better), mean calls (lower better), and sweep mean wall-clock at n = 2000 (lower better). Ties share the mean rank.

### Weighted score (Table T7)

For one corpus: `g_i = log10(1 + calls_i)` (accuracy-run calls, matched to the corpus). `A_i = (F1_i − min F1) / (max F1 − min F1)`. `C_i = 1 − (g_i − min g) / (max g − min g)`. If a criterion has max = min, set it to 0.5 for every strategy and flag it (it should not occur). `S_i(w) = w·A_i + (1 − w)·C_i`.
Scenarios (accuracy weight w / cost weight): accuracy-first 0.7/0.3, balanced 0.5/0.5, cost-first 0.3/0.7.
Ties: scores within 1e-12 are tied and share the mean rank. Note that DSA balanced gives S1 = S2 = 0.500 exactly, so the tie rule must work there. Report ranks as well as scores. Mark the best per row in the CSV (`is_best`); ties mark all tied.

### Weight sweep (Table T8, Figure F9 data)

Draw w ~ Uniform(0, 1), 20,000 draws, seed 42, per corpus (re-seed per corpus so both corpora see the same draws). Use the same RNG family that `bootstrap.py` uses, and record the exact constructor in D-89. Rank every draw (strict; if any tie occurs, count it and report it). Report the share of draws giving each strategy each rank (CSV with full precision; the Markdown table rounded to 2 decimals), plus the Monte Carlo standard error `sqrt(p(1−p)/20000)`.
**Also (T8b):** compute the EXACT shares analytically. `S_i(w)` is piecewise linear in w, so ranks only change at pairwise crossings. Collect the crossing points in (0, 1), sort them, evaluate the ranking in each interval, and sum interval lengths. Report `max |MC − exact|`. Reason: the thesis rounds MC shares to two decimals, and my own check suggests some cells sit near a rounding boundary (e.g. Metacademy S3 rank 2 is about 0.680 exactly, but the scratch table shows 0.69). The thesis text quotes "69%" and "60%". If the pipeline's MC result differs from the scratch table, say so plainly. Do not tune the seed.

### Cross-checks (Table T9 and T9b)

- **TOPSIS (T9):** decision matrix is the pair (A_i, C_i), no further normalisation. Apply the scenario weights to each criterion: `v_i = (w·A_i, (1 − w)·C_i)`. Ideal point = `(w, 1 − w)`, anti-ideal point = `(0, 0)` (this is the weighted form of "ideal (1,1), anti-ideal (0,0)" in the thesis text). Closeness = `d⁻ / (d⁺ + d⁻)`, with Euclidean distances. Rank by closeness. **The thesis wording is ambiguous on whether weights are applied before the distances. Pick the form above, say in D-89 that you chose it and why, and flag the ambiguity for the APC. Do not compute both and choose later.**
- **Kendall τ (T9):** per corpus and scenario, between the TOPSIS ranking and the weighted-sum ranking. Use τ-b (tie-corrected; SciPy `kendalltau(variant='b')` or a hand-written equivalent). Report τ, the number of tied pairs, and the two rankings. With four strategies the value space is coarse; do not add a p-value.
- **Wall-clock-substituted check (T9b):** recompute the T7 scores with `g_i = log10(1 + mean wall-clock seconds at n = 2000)` from the SWEEP runs. This one value per strategy is used for both corpora; accuracy-run latencies are not used for any cost claim. Report scores, ranks, and whether the top-ranked strategy per scenario matches T7.

### Output names (all CSV + Markdown, every row carries `status = "post-hoc"`)

`tables/T5_gates_and_classes`, `T5b_gate_sensitivity`, `T6_single_criterion_ranks`, `T7_weighted_scores`, `T8_rank_shares`, `T8b_rank_shares_exact`, `T9_topsis_kendall_tau`, `T9b_walltime_substituted_scores`. Figures: `figures/F7_gates_g1_g2`, `F8_score_vs_weight`, `F9_rank_shares` (each as `.pdf`, `.png`, and an underlying `.csv`, like F1–F6).

## 4. Figures (these replace three images the teammate drew by hand)

Follow `style.py`. Every figure carries the visible text **"POST HOC: not pre-registered"** in the title or a corner box, as D-87 did for "EXPLORATORY". Do not clamp or shift non-positive values (omit-not-clamp, D-87(4)); calls at n = 2000 are all positive, but keep the rule.

- **F7 → thesis Figure 4.11, "Gates G1 and G2 applied to the primary configurations".** Two stacked panels, width about 6.5 in. *Panel A (G1):* bars of shortlist recall for S3 and S4 for each corpus, with a dashed marker for the pre-registered random baseline, and value labels. S1 and S2 are not drawn, with a note that no baseline applies to them. *Panel B (G2):* mean calls per insertion at n = 2000 for all four strategies on a log x-axis, a dashed vertical line at 50 labelled "limit: 50", and the S1 point highlighted as the failing one.
- **F8 → Figure 4.12, "Normalised score against the weight on accuracy, by corpus".** Two panels (DSA, Metacademy). For each strategy a straight line from `(w=0, C_i)` to `(w=1, A_i)`. Direct end labels (S1–S4), faint verticals at w = 0.3, 0.5, 0.7 for the three scenarios, S3 visually emphasised. y from 0 to 1.
- **F9 → Figure 4.13, "Share of weightings giving each rank, by strategy and corpus".** Horizontal 100% stacked bars, one per strategy, grouped by corpus, ordered rank 1 (darkest) to rank 4 (lightest), with a legend. Label a segment only if its share is ≥ 8%.

Figure titles may state the finding (as the teammate's drafts do), but each title claim must be asserted in code against the data (e.g. "S3 is last in under 0.5% of draws" must be computed, not typed). The existing images in the thesis are a layout reference only; they are not a style requirement.

## 5. Claims in the thesis text to verify (report each as confirmed / differs by X)

1. Table 4.7: G1 values (S3 0.528 vs 0.357 on DSA and 0.505 vs 0.071 on Metacademy; S4 0.259 vs 0.357 on DSA and 0.147 vs 0.071 on Metacademy); G2 values (0.8, 7.0, 10, 2,000 calls); G3 outcomes and the four classes (S1 and S4 not effective, S2 conditionally effective, S3 effective).
2. S2 shortlist recall is 0.111 (DSA) and 0.202 (Metacademy). S2 micro-recall on Metacademy is 0.174.
3. The only cell with F1 ≥ 0.50 and recall ≥ 0.50 is S1 on DSA (0.586, 0.630). No cell has F1 ≥ 0.50 and recall ≥ 0.70. S3 on DSA has F1 0.511 and recall 0.426.
4. Table 4.8 ranks (the scratch version: DSA F1 S1=1, S3=2, S4=3, S2=4; Metacademy F1 S3=1, S2=2, S1=3, S4=4; calls and wall-clock S2=1, S4=2, S3=3, S1=4).
5. Table 4.9 (scratch values in Section 6) and the statement that the DSA leader changes with the weights (S1 → S3 → S2) while S2 leads on Metacademy in all three scenarios.
6. Table 4.10 and the sentences: S3 last in under 0.5% of draws on both corpora; S3 second most often on DSA (60%) and Metacademy (69%); S4 first in no draw on either corpus; S1 and S2 are each first or last on DSA.
7. The sensitivity paragraph (G2 any limit 10–1,999; G1 size-matched; G3 margin up to 0.15).

## 6. Cross-check targets (NOT to be copied into code)

My independent recomputation from `final_output` T1/T2 (full precision) gives these. The scratch table in the thesis differs by up to about 0.003 on some Metacademy cells (probably rounded inputs). Report any cell where your pipeline differs from the scratch table by more than 0.005.

- DSA: A = [1, 0, 0.829, 0.282], C = [0, 1, 0.346, 0.461] (order S1, S2, S3, S4). Scores 0.7/0.3: [0.700, 0.300, 0.684, 0.336]; 0.5/0.5: [0.500, 0.500, 0.587, 0.372]; 0.3/0.7: [0.300, 0.700, 0.491, 0.407].
- Metacademy: A = [0.165, 0.864, 1, 0], C = [0, 1, 0.609, 0.674]. Scores 0.7/0.3: [0.116, 0.905, 0.883, 0.202]; 0.5/0.5: [0.083, 0.932, 0.804, 0.337]; 0.3/0.7: [0.050, 0.959, 0.726, 0.472]. The scratch table shows 0.113/0.907, 0.081/0.933 and 0.048/0.960 for S1/S2 in the same rows.
- Exact rank shares (analytic), DSA rows S1–S4 × ranks 1–4: [0.331 0.169 0.109 0.391], [0.441 0.059 0.156 0.344], [0.228 0.598 0.174 0.000], [0.000 0.174 0.561 0.265]. Metacademy: [0.000 0.000 0.197 0.803], [0.742 0.258 0.000 0.000], [0.258 0.680 0.061 0.000], [0.000 0.061 0.742 0.197].
- Sweep at n = 2000 (mean calls, mean seconds): S1 (2000, 1713.1), S2 (0.8, 0.938), S3 (10, 8.277), S4 (7.0, 5.638).

## 7. Tests

Extend `tests/test_analysis_pipeline.py` (or add `tests/test_posthoc.py`) with at least: normalisation formula against a hand-worked example; the all-equal criterion → 0.5 rule; exact tie in the DSA balanced scenario and mean-rank handling; τ-b with ties against a hand-computed value; TOPSIS on a 3-point toy matrix with a known answer; exact-share routine against a brute-force fine grid; seeded draw determinism; gate-class logic on a synthetic table covering all three classes; "validation failure ⇒ no artifacts written"; "default run (no flag) writes the same files as before". Run the full existing suite and report pass/fail counts as seen, without hard-coding them in D-90 (D-86(1)(b) removed an ephemeral test count from a decision for that reason).

## 8. Deliverables (AGENTS.md "4 Unit-of-Work Deliverables")

1. Commits on `task/ANALYSIS-004`: first the D-89 + Amendment 4 commit, then code and tests, then D-90. Nothing uncommitted at the end.
2. `patch/ANALYSIS-004-<agent>-posthoc-ranking.patch`.
3. Report `docs/reports/ANALYSIS-004-<agent>-posthoc-ranking.md`: executive summary; the Section 5 verification table; every cell where the result differs from the scratch values (old → new); the TOPSIS interpretation choice; the MC-vs-exact comparison; the no-change proof; git diff with index lines; items for the APC. Update the status row and run `./scripts/validate-report.py docs/reports/<report>.md --require-patch`.
4. A RUN_INFO for the new run in the same format as the earlier one (argv, results_dir, git commit, `pipeline_modules_sha256` for all modules including the new ones, hashes file and its sha256, `src_diff_clean`, `overall_gate_status`).
5. Package the NEW output directory only (not the whole `final_output_final`) as `bundle_c_posthoc_outputs.tar.gz`, containing `tables/`, `figures/` and `RUN_INFO.txt` of the new run. Tell Luke the path. Do not rebuild the APC bundle unless a shared doc changed (the decision log and analysis plan did, so build one with `./scripts/apc-bundle.sh` profile `core` plus `--add docs/context/analysis-plan.md`).

## 9. Flag, do not fix

Report, and do not change on your own initiative: any disagreement between this prompt and the repo; any place where the thesis text would need to change because a regenerated number differs; the TOPSIS ambiguity; anything in `analysis-plan.md` that conflicts with labelling this stage post hoc. Do not edit the thesis; the APC will relay the text edits.
