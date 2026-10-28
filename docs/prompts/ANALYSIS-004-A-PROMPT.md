# ANALYSIS-004-A — Pre-merge audit of ANALYSIS-004 (read-only on code and results)

**Agent:** Claude Code. **Archive this prompt first** as `docs/prompts/ANALYSIS-004-A-PROMPT.md`.

## 0. Read first, in order

1. `AGENTS.md` and `docs/context/complete-context.md` (in full).
2. `docs/context/data-formats.md`.
3. `docs/decisions/decision-log.md`: at least D-79 and D-83 to D-91.
4. `docs/tasks/status.md` (the ANALYSIS-004 row).
5. `docs/context/analysis-plan.md` (Rules R1–R3, Amendments 1–4).
6. `docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md` and `docs/reports/ANALYSIS-004-claude-code-erratum.md`.

## 1. Purpose and hard limits

ANALYSIS-004 (post-hoc decision and ranking stage) is `needs-review` on branch `task/ANALYSIS-004` and is not merged. An APC instance has reviewed the numbers from bundled copies only. Your job is to audit the branch **directly in the repo** and report what you find, so that Luke can decide on the merge.

- **Do not merge, rebase, reset, clean, stash or delete any worktree** (AGENTS.md, Parallel work, items 6 and 7). Luke merges.
- **Do not edit** any code, result, table, figure, the ANALYSIS-004 report, the erratum, or D-89/D-90/D-91. Corrections go in your own new decision entry.
- **Do not edit the thesis docx or markdown.** Read them only.
- No live API calls, no new experiment runs. The results directory is read-only input.
- Do not commit or stage the untracked `repositories` symlink in the ANALYSIS-004 worktree.

**Worktree.** Work in your own worktree, branched from the ANALYSIS-004 head so that branch stays untouched:

```bash
git worktree add ../llm-graph-insertion-complexity-ANALYSIS-004-A -b task/ANALYSIS-004-A task/ANALYSIS-004
```

Reserved decision ID: **D-92**. The bundle I saw ends at D-91. If D-92 already exists in the file, stop and report the conflict; do not renumber.

## 2. Claims to verify (every item: report PASS / FAIL / UNABLE, with the command and its output)

The claims below come from a handoff document and from bundled files, not from the repo. Check each one yourself. If any is wrong, say so rather than deferring to this prompt.

### A. Branch state and provenance

A1. Run `git worktree list`, `git status --short` (main checkout and the ANALYSIS-004 worktree) and `git log --oneline -10 task/ANALYSIS-004`. Report the head hash.
A2. **Open discrepancy.** The handoff says the head is `4c6330a` (base `a524de7`; commits `edda901`, `8e2eccf`, `e3b563d`, `f4ba18a`, `b32ee07`, `7ee6065`, `4c6330a`). The APC bundle manifest instead records git commit `fa57170`, which the handoff never mentions. Identify what `fa57170` is (which branch, which tree, ancestor or descendant of `4c6330a`), or report that it does not exist.
A3. Confirm `master` is `a524de7` and is an ancestor of `task/ANALYSIS-004`.
A4. `git diff --stat master...task/ANALYSIS-004`. List every changed file. Confirm there is no file outside: `scripts/analysis/posthoc.py`, `scripts/analysis/posthoc_figures.py`, `scripts/analysis/run_analysis.py`, `tests/test_posthoc.py`, `docs/` (prompt, plan, status, decision log, report, erratum). Confirm no `repositories` symlink and nothing under `results/` is tracked in the diff.
A5. Confirm the six pre-registered modules (`validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`) have an empty diff against `master`.

### B. Frozen-specification integrity

B1. Using `git log -p` on `docs/decisions/decision-log.md`, confirm the D-89 text is identical in every commit after `edda901`, and that D-90 and D-89 were not edited by the D-91 commit (`7ee6065`).
B2. Confirm `edda901` (which freezes D-89) precedes every commit that adds `posthoc.py` or any output.
B3. The status row for ANALYSIS-004 lists commits only up to `7ee6065`; report whether `4c6330a` (or `fa57170`) changes any file other than the erratum wording.

### C. Reproduction

C1. Run `tests/test_posthoc.py`. Then run the full suite on `task/ANALYSIS-004` and on `master`, and compare the **names** of failing tests (the handoff claims 20 pre-existing environment failures with an identical set on both; confirm or refute by name, and do not record counts in any decision per D-86(1)(b)).
C2. Re-run the post-hoc stage into a **scratch directory** (not `final_output_posthoc`) using the command in D-90(2)(a), at the branch head. If the code changed after `e3b563d`, say so and note which modules.
C3. Compare every CSV and Markdown file in the scratch output with `/home/lukexodus/projects/thesis-analysis/final_output_posthoc` (expect byte-identical). PDFs may differ in `CreationDate`; PNG dimensions may differ with text metrics. Compare `pipeline_modules_sha256` in both `RUN_INFO.txt` files against the files at head.
C4. Confirm `final_output_final` is unchanged (re-run the default no-flag pipeline into a second scratch directory and compare CSV/Markdown byte-for-byte, as in D-90(5)(b)).

### D. Numbers

D1. Recompute independently of `posthoc.py` (your own short script, not imports from it): T7 scores for all 24 corpus × scenario × strategy rows; the T8b exact rank shares; T9 TOPSIS closeness and τ-b using the weighted-before-distances form of D-89(9); the T9b top-match count. Report the maximum absolute difference to the committed CSVs.
D2. Confirm the DSA S2 rank-2 Monte Carlo cell: |MC − exact| = 0.004597, and report the SE ratio computed **both** with the MC share (0.0543) and with the exact share (0.0589). D-91 uses the first and gives about 2.9; an APC recomputation with the second gave about 2.8. Both are above one SE; state the two values.
D3. Confirm G3 margin stopping points: S1 stops being dominated at ΔF1 = 0.150658 and S4 at 0.155862 (erratum), against `stats.evaluate_dominance` unchanged.

### E. Documentation defects found by the APC (record, do not fix in place)

E1. **Erratum digit slip.** `ANALYSIS-004-claude-code-erratum.md` (E10a scope paragraph) writes the S4 DSA size-matched baseline as **0.2498**. T5b, the report and D-90 give **0.2488** (6.9655 / 28 = 0.24877). Confirm which is correct from T5b's CSV, and whether 0.2498 appears anywhere else in the repo.
E2. **D-90(4)(c) labelling.** It says "On DSA, S4 rank 4 is 0.2667 against 0.26". In T8b the exact share is 0.2650 and the Monte Carlo share is 0.2667. Confirm which D-90 means, and whether the sentence is ambiguous.
E3. Check whether any other sentence in the report, D-90 or D-91 mixes exact and Monte Carlo values without labelling them.

### F. Thesis docx against the committed outputs (read-only)

Use `docs/thesis/_REVISED__An_Empirical_Complexity_Analysis_of_Candidate-Narrowing_Strategies_for_Incremental_LLM-Driven_Graph_Construction_With_Chapter_4_ANALYSIS-004.docx` (untracked in the main checkout). If it is missing, use the copy at `docs/context/handoff-inputs/`. Extract text with `pandoc` and compare these against `final_output_posthoc`:

F1. Table 4.9 (8 updated cells and caption) against T7.
F2. Table 4.10 (7 updated cells) against the **Monte Carlo** column of T8 at 2 decimals; and the "68%" statement against T8b (S3 Metacademy rank 2: exact 0.6803).
F3. Table 4.11 and the cross-check paragraph against T9, T9b and T8b: τ-b values, the T9b match count (must read 3 of 6, not 2 or 4), the Monte Carlo-versus-exact maximums (0.0046 DSA, 0.0022 Metacademy), and the "at most about 0.004" standard-error statement.
F4. The sentence narrowing the DSA-leader caveat: under TOPSIS, S3 leads DSA accuracy-first (0.7194 vs 0.7000 for S1). Confirm the thesis wording is true against T9, and that the cost-first S3/S4 adjacent swap is not misstated.
F5. The two "about level" sentences (Section 4.3.2 and Section 4.4.1 / 4.7 equivalents: 0.259 against 0.249) against T5b.
F6. The Section 3.6.3 C_i formula contains the `1 −` reversal; the RNG sentence matches D-89(7)(a); the weighted-TOPSIS wording matches D-89(9). The Section 4.7 RQ3 row reads "Tables 4.6 to 4.11".
F7. Report any numeric statement in the new Section 4.4.1 text that has no corresponding cell in T5–T9b.

## 3. Deliverables (AGENTS.md "After finishing any task")

1. Commit on `task/ANALYSIS-004-A` (conventional message).
2. Patch file: `patch/ANALYSIS-004-A-claude-code-premerge-audit.patch` (`git diff HEAD~1`).
3. Report: `docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md`. Executive summary first, then a table of A1–F7 with PASS / FAIL / UNABLE, then the verbatim `git diff`, patch reference, and an "Items for the APC" section. List every untracked file you saw. Run `./scripts/validate-report.py docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md --require-patch`.
4. Decision entry **D-92** recording only corrections found (E1, E2, any FAIL), by later entry. If nothing failed, record that the audit found no defects, and the verified head hash.
5. Add your own row to `docs/tasks/status.md` for ANALYSIS-004-A; do not edit other rows.
6. In your final message, state the branch name, worktree path, the head hash from A1, and the answer to A2 first.

## 4. Do not decide

Do not decide how the docx text is synced into the repo's markdown, and do not decide whether to merge. State, for Luke, anything in sections A–F that should block the merge, and anything that should not.
