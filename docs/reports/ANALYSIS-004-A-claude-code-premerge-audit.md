# ANALYSIS-004-A Report: Direct Pre-Merge Audit of ANALYSIS-004

**Task:** ANALYSIS-004-A · **Agent:** Claude Code · **Status:** done · **Branch:** `task/ANALYSIS-004-A` (base `678c170`) · **Decision:** [D-92] · **Audited head:** `678c170`

**Audit adaptation (read first).** The prompt assumed `task/ANALYSIS-004` was still unmerged at head `4c6330a`. It was merged to master at **`c05d1e0`** and the docx text was synced at **`8685310`** *before* this audit ran, on Luke's instruction. The branch and its worktree no longer exist. This audit therefore examined **master `678c170`** and the pre-merge branch tip **`fa57170`** (file diff `a524de7..fa57170`). Every item was still checked directly; only the refs changed.

---

## Executive Summary

- **No code, result, table or figure defect was found.** The post-hoc stage reproduces its committed outputs byte-for-byte; an independent recomputation of T7, T8b, T9 and T9b matches the CSVs with **zero** difference; the gate passes; module hashes match the head.
- **The six pre-registered modules are untouched**, and the branch diff contains only the expected new modules, tests and docs.
- **D-89 was not edited after its freeze.** D-90 and D-91 were appended, not rewritten; the D-91 commit did not modify D-89 or D-90.
- **Four documentation corrections were found**, all text-only: the erratum's `0.2498` should be `0.2488`; D-90(4)(c)'s "0.2667 against 0.26" is an unlabelled MC-versus-scratch comparison; three other exact shares in the same sentence are unlabelled; and the S4 G3 stopping point is `0.155867`, not `0.155862` (erratum and handoff). These do not affect any number in the tables, results or thesis.
- **Nothing found should block the merge.** The merge has in fact already happened; the remaining actions are the documentation corrections in [D-92] and the open thesis/deck items.

---

## A–F Results

| Item | Verdict | Evidence |
| --- | --- | --- |
| A1 | **PASS (adapted)** | Worktrees: main `678c170`, three old task worktrees, audit worktree `task/ANALYSIS-004-A` at `678c170`. Main status: only untracked files (docx, `docs/presentation/`, `docs/thesis/buffer/`, old-chapters archive, `redraw_thesis_figures.py`). `task/ANALYSIS-004` no longer exists. Log: `678c170`, `8685310`, `c05d1e0`, `a1195da`, `fa57170`, `4c6330a`, `7ee6065`, `b32ee07`, `f4ba18a`, `e3b563d`, `8e2eccf`, `edda901`. |
| A2 | **PASS** | `fa57170` = "docs(ANALYSIS-004): add APC-to-APC handoff for 2026-10-28"; one file (the handoff), descendant of `4c6330a`; now in master through `c05d1e0`. The handoff's "head `4c6330a`" sentence predates it. |
| A3 | **FAIL (stale premise, explained)** | `master` is `678c170`, not `a524de7`; `a524de7` **is** an ancestor of master and of `fa57170`. The difference is the merge/sync that happened before the audit. |
| A4 | **PASS** | `git diff --stat a524de7 fa57170`: 11 files — the two new modules, `run_analysis.py`, `tests/test_posthoc.py`, prompt, plan, status, decision log, report, erratum, handoff. No `results/` path, no `repositories` symlink. The handoff is the only file outside the prompt's listed docs set. |
| A5 | **PASS** | Empty diff for `validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py` over `a524de7..fa57170`. |
| B1 | **PASS** | Entry-extraction across `edda901`, `f4ba18a`, `7ee6065`, `4c6330a`, `fa57170`, `678c170`: the D-89 block is byte-identical in all six; the D-90 block is byte-identical from `f4ba18a` onward. D-91 is a separate appended entry. |
| B2 | **PASS** | `posthoc.py` first appears in `8e2eccf`; `edda901` is its ancestor. |
| B3 | **PASS with note** | `4c6330a` changes the erratum (1 line) and `status.md` (2 lines: erratum link and commit list); `fa57170` adds only the handoff. |
| C1 | **PASS** | `tests/test_posthoc.py`: 16 passed. Full suite: head 20 failed / 660 passed / 13 skipped; base `a524de7` 20 failed / 644 passed / 13 skipped. The **failure-name sets are identical** (`diff` empty). |
| C2 | **PASS** | No change to `posthoc.py`, `posthoc_figures.py` or `run_analysis.py` after `e3b563d`. Scratch rerun at `678c170`: gate PASS, 72 cross-check cells. |
| C3 | **PASS** | Scratch vs `final_output_posthoc`: 0 CSV/Markdown differences; PNGs byte-identical; 3 PDFs differ (`CreationDate`); `RUN_INFO` differs only in `argv` and `git_commit`. All nine `pipeline_modules_sha256` match the files at head. |
| C4 | **PASS** | Default rerun vs `final_output_final`: 0 CSV/Markdown differences; no file only-in-one; 9 PDFs and 3 PNGs differ by rendering, as in D-90(5)(b). |
| D1 | **PASS** | Independent script (no `posthoc.py` import): max abs diff **0** for T7 A/C/score/rank, T8b exact shares, T9 closeness/τ/ranks; T9b match count 3 of 6 and per-cell agreement True. |
| D2 | **PASS** | `|MC−exact| = 0.004597`; SE ratio **2.869** with MC share 0.0543, **2.761** with exact share 0.0589. Both above 1. |
| D3 | **PASS with correction** | S1 ΔF1 = 0.150657731 (reported 0.150658, correct); S4 ΔF1 = **0.155867182**, not 0.155862. `evaluate_dominance` unchanged flips at those points. |
| E1 | **FAIL** | Erratum E10a paragraph says 0.2498; T5b CSV says 0.2488 (6.9655/28 = 0.248768…). `0.2498` appears nowhere else except the audit prompt quoting it. |
| E2 | **FAIL** | D-90(4)(c) "On DSA, S4 rank 4 is 0.2667 against 0.26": 0.2667 is the MC share; exact is 0.2650; "0.26" is the scratch value. Neighbouring clauses in the same sentence label exact/MC, so this one reads as ambiguous. |
| E3 | **FAIL** | Same sentence gives 0.2584 (S2 rank 2 and S3 rank 1), 0.7418 (S4 rank 3) and 0.1969 (S4 rank 4) as exact shares without labels; S2 rank 1, S3 rank 2 and DSA S2 rank 2 are labelled. Values correct, labelling inconsistent. Also the `0.155862` slip in E1/D3. |
| F1 | **PASS** | Table 4.9 vs T7 at 3 dp: max abs diff **0** (8 updated cells); caption says "post hoc"; bold leaders S1/S3/S2 on DSA and S2 on Metacademy. |
| F2 | **PASS** | Table 4.10 vs T8 **MC** at 2 dp: max abs diff **0** (7 updated cells). "68%" matches T8b S3 Metacademy rank 2 exact 0.6803 (MC 0.6812 also rounds to 0.68); "60%" matches 0.5981. |
| F3 | **PASS** | Table 4.11 vs T9: max abs diff **0** (τ 0.67/1.00/0.67/1.00; tied pairs 0/1/0/0). Paragraph states 3 of 6, 0.0046/0.0022, and SE at most about 0.004 — all match T9b/T8. |
| F4 | **PASS** | TOPSIS DSA accuracy-first S3 0.7194 vs S1 0.7000 (text 0.719/0.700); cost-first S4 ahead of S3 (0.4344 vs 0.4296). |
| F5 | **PASS** | "0.259 against 0.249": T5b recall 0.2593, baseline 0.2488 → 0.249. Both occurrences (4.3.2 and the 4.4.1 sensitivity paragraph). |
| F6 | **PASS** | C_i contains `1 −`; RNG sentence matches D-89(7)(a); weighted-TOPSIS wording matches D-89(9); RQ3 row reads "Tables 4.6 to 4.11". |
| F7 | **PASS with note** | All numeric statements in the new 4.4.1 text map to T5–T9b cells except "0.151 / 0.156", which are derived stopping points (T5b only samples the 0.005 grid). They are correct after the E3/D3 correction. |

---

## Work Completed

Read the required context, archived the prompt, created this audit worktree
from `678c170`, and checked A1–F7 directly with git, pytest, two scratch
pipeline runs, an independent recomputation script, and a pandoc extraction
of the docx. No audited file was edited. The only repo changes are this
report, the archived prompt, [D-92] and the new status row.

## Detailed Evidence

### A1–A5 (state and diff)

```text
worktrees: main 678c170 [master]; ANALYSIS-001-G 48037e3; ANALYSIS-002 17ed1f8;
           ANALYSIS-003 5ab04a6; ANALYSIS-004-A 678c170 [task/ANALYSIS-004-A]
main status: ?? docs/presentation/  ?? <ANALYSIS-004 docx>  ?? docs/thesis/buffer/
             ?? old-chapters archive  ?? redraw_thesis_figures.py
fa57170: 1 file changed, 242 insertions(+)  (handoff only)
4c6330a: erratum 1 line, status 2 lines
a524de7..fa57170: 11 files, 5219 insertions
A5 diff: empty
```

### B (frozen specification)

Entry hashes across the six commits compared: D-89 identical in all; D-90 identical from `f4ba18a` to `678c170`; D-91 appended at `7ee6065`. `posthoc.py` first added in `8e2eccf`, after `edda901`.

### C (reproduction)

- Failure-name files: head 20 names, base 20 names, `diff` empty. Examples include `tests/test_analysis_pipeline.py::test_source_grep_forbidden_patterns` (pre-existing checker collision) and the FAISS/torch CLI tests.
- Scratch post-hoc output: `/home/lukexodus/projects/thesis-analysis/scratch_a004a_posthoc`.
- Scratch default output: `/home/lukexodus/projects/thesis-analysis/scratch_a004a_default`.
- `RUN_INFO` module hashes: all nine `MATCH` at head.

### D (numbers)

Independent recomputation used only `final_output_final` T1/T2 CSVs and reimplemented normalisation, the exact-share crossing calculation, TOPSIS and τ-b. Max abs differences to the committed post-hoc CSVs: T7 A = 0, C = 0, score = 0, rank = 0; T8b = 0; T9 closeness = 0, τ = 0, ranks = 0; T9b per-cell match agreement True (3 of 6).

### E (documentation)

- E1: only occurrence of `0.2498` in the repo is the erratum E10a paragraph (plus the audit prompt quoting it).
- E2/E3: D-90(4)(c) is the only sentence mixing labelled and unlabelled exact/MC values. The report and D-91 label their MC/exact comparisons.
- G3 stopping points: S1 0.150657731; S4 0.155867182.

### F (docx)

Docx extracted with `pandoc -t gfm`; tables parsed and compared cell-by-cell. Table 4.9/4.10/4.11 max abs differences are all 0. The synced repo markdown carries the same text; `media/image1.png`, `image2.png`, `image9.png` are byte-identical to F7/F8/F9.

---

## Untracked Files Observed

Main checkout: `docs/presentation/`; `docs/thesis/_REVISED__…_ANALYSIS-004.docx`; `docs/thesis/buffer/`; `docs/thesis/previous-versions/An Empirical Complexity Analysis … .md`; `redraw_thesis_figures.py`.

Audit worktree: `docs/prompts/ANALYSIS-004-A-PROMPT.md` (archived by this task); `repositories` symlink (test support, not staged).

---

## Git Diff

```diff
diff --git c/docs/decisions/decision-log.md i/docs/decisions/decision-log.md
index fd1e1bd..80fad9d 100644
--- c/docs/decisions/decision-log.md
+++ i/docs/decisions/decision-log.md
@@ -906,3 +906,20 @@ Reasoning: records how the [D-89]-frozen post-hoc stage was implemented and repr
 (3) Confirmed, not corrected: the report's claim that thesis Section 3.6.3 displays $C_i$ without the `1 −` reversal is correct (the reviewer confirmed it against the docx); the implementation's reversed form stands.
 (4) The pre-registered artifacts, gate status, 72-cell cross-check, T5–T9 values, and the three review recommendations (weighted TOPSIS stays, Table 4.10 stays Monte Carlo, the DSA caveat goes in the new cross-check paragraph) are unaffected. No code, data or result changes.
 Reasoning: corrects two factual sentences in [D-90] and the task report found during independent review, by later entry rather than by editing earlier text. Affects: `docs/decisions/decision-log.md`, `docs/reports/ANALYSIS-004-claude-code-erratum.md`, `docs/tasks/status.md`.
+
+**[D-92]** Pre-merge audit of ANALYSIS-004: verified state and documentation corrections (ANALYSIS-004-A):
+(1) Audit context:
+  (a) The ANALYSIS-004 branch was merged to master at `c05d1e0` and the docx text was synced at `8685310` before this audit ran. The audit therefore examined master `678c170` and the pre-merge branch tip `fa57170` (file diff `a524de7..fa57170`). Verified head at audit time: `678c170`.
+  (b) `fa57170` is the APC-to-APC handoff commit, a descendant of `4c6330a`; it adds one file, `docs/context/apc-handoff-2026-10-28-ANALYSIS-004.md`. The handoff's "head `4c6330a`" sentence predates that commit.
+(2) No code, result, table or figure defect was found:
+  (a) `tests/test_posthoc.py` passes; the full-suite failure **names** are identical between master and `a524de7`, so the failures are pre-existing and environmental.
+  (b) A scratch rerun of `--only posthoc` reproduces every CSV and Markdown file byte-identically; a scratch default rerun reproduces `final_output_final`'s CSV/Markdown byte-identically; module hashes in `RUN_INFO.txt` match the files at head.
+  (c) An independent recomputation (not importing `posthoc.py`) reproduces T7 scores, T8b exact shares, T9 TOPSIS closeness/ranks/τ-b and the T9b match count with zero difference. The T9b match count is 3 of 6.
+  (d) The SE ratios for the DSA S2 rank-2 cell are 2.869 using the MC share (0.0543) and 2.761 using the exact share (0.0589); both exceed one SE, as [D-91] states.
+(3) Documentation corrections (no code or result changes):
+  (a) The erratum's E10a scope paragraph gives the S4 DSA size-matched baseline as **0.2498**; the correct value is **0.2488** (6.9655 / 28 = 0.248768…). The T5b CSV, the task report and [D-90] are correct. `0.2498` appears nowhere else in the repo except the audit prompt that quoted it.
+  (b) [D-90](4)(c)'s sentence "On DSA, S4 rank 4 is 0.2667 against 0.26" mixes the **Monte Carlo** share (0.2667) with the thesis scratch value; the exact share is 0.2650. It is ambiguous because neighbouring entries in the same sentence label exact vs MC.
+  (c) The same sentence gives 0.2584 (S2 rank 2 and S3 rank 1), 0.7418 (S4 rank 3) and 0.1969 (S4 rank 4) as exact shares without a label, while S2 rank 1, S3 rank 2 and DSA S2 rank 2 are labelled. The numbers are correct; only the labelling is inconsistent.
+  (d) The erratum and handoff state S4's G3 stopping point as **0.155862**; the computed value is **0.155867182** (0.269503546 − 0.113636364). S1's 0.150658 is correct (0.150657731). Both round to the same three decimals used in the thesis.
+(4) Stale prompt assumptions, not defects in the work: `master` is no longer `a524de7` (that commit is an ancestor), `task/ANALYSIS-004` no longer exists as a branch, and the A4/A5 diffs were therefore evaluated against the pre-merge tip `fa57170`. The A4 diff contains only the expected code/tests/docs plus the handoff file; it contains no `results/` path and no `repositories` symlink.
+Reasoning: records that the merged ANALYSIS-004 state reproduces and computes correctly, and records the four documentation corrections found by direct repo audit, by later entry rather than by editing the earlier text. Affects: `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md`.
diff --git c/docs/prompts/ANALYSIS-004-A-PROMPT.md i/docs/prompts/ANALYSIS-004-A-PROMPT.md
new file mode 100644
index 0000000..6388e4b
--- /dev/null
+++ i/docs/prompts/ANALYSIS-004-A-PROMPT.md
@@ -0,0 +1,92 @@
+# ANALYSIS-004-A — Pre-merge audit of ANALYSIS-004 (read-only on code and results)
+
+**Agent:** Claude Code. **Archive this prompt first** as `docs/prompts/ANALYSIS-004-A-PROMPT.md`.
+
+## 0. Read first, in order
+
+1. `AGENTS.md` and `docs/context/complete-context.md` (in full).
+2. `docs/context/data-formats.md`.
+3. `docs/decisions/decision-log.md`: at least D-79 and D-83 to D-91.
+4. `docs/tasks/status.md` (the ANALYSIS-004 row).
+5. `docs/context/analysis-plan.md` (Rules R1–R3, Amendments 1–4).
+6. `docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md` and `docs/reports/ANALYSIS-004-claude-code-erratum.md`.
+
+## 1. Purpose and hard limits
+
+ANALYSIS-004 (post-hoc decision and ranking stage) is `needs-review` on branch `task/ANALYSIS-004` and is not merged. An APC instance has reviewed the numbers from bundled copies only. Your job is to audit the branch **directly in the repo** and report what you find, so that Luke can decide on the merge.
+
+- **Do not merge, rebase, reset, clean, stash or delete any worktree** (AGENTS.md, Parallel work, items 6 and 7). Luke merges.
+- **Do not edit** any code, result, table, figure, the ANALYSIS-004 report, the erratum, or D-89/D-90/D-91. Corrections go in your own new decision entry.
+- **Do not edit the thesis docx or markdown.** Read them only.
+- No live API calls, no new experiment runs. The results directory is read-only input.
+- Do not commit or stage the untracked `repositories` symlink in the ANALYSIS-004 worktree.
+
+**Worktree.** Work in your own worktree, branched from the ANALYSIS-004 head so that branch stays untouched:
+
+```bash
+git worktree add ../llm-graph-insertion-complexity-ANALYSIS-004-A -b task/ANALYSIS-004-A task/ANALYSIS-004
+```
+
+Reserved decision ID: **D-92**. The bundle I saw ends at D-91. If D-92 already exists in the file, stop and report the conflict; do not renumber.
+
+## 2. Claims to verify (every item: report PASS / FAIL / UNABLE, with the command and its output)
+
+The claims below come from a handoff document and from bundled files, not from the repo. Check each one yourself. If any is wrong, say so rather than deferring to this prompt.
+
+### A. Branch state and provenance
+
+A1. Run `git worktree list`, `git status --short` (main checkout and the ANALYSIS-004 worktree) and `git log --oneline -10 task/ANALYSIS-004`. Report the head hash.
+A2. **Open discrepancy.** The handoff says the head is `4c6330a` (base `a524de7`; commits `edda901`, `8e2eccf`, `e3b563d`, `f4ba18a`, `b32ee07`, `7ee6065`, `4c6330a`). The APC bundle manifest instead records git commit `fa57170`, which the handoff never mentions. Identify what `fa57170` is (which branch, which tree, ancestor or descendant of `4c6330a`), or report that it does not exist.
+A3. Confirm `master` is `a524de7` and is an ancestor of `task/ANALYSIS-004`.
+A4. `git diff --stat master...task/ANALYSIS-004`. List every changed file. Confirm there is no file outside: `scripts/analysis/posthoc.py`, `scripts/analysis/posthoc_figures.py`, `scripts/analysis/run_analysis.py`, `tests/test_posthoc.py`, `docs/` (prompt, plan, status, decision log, report, erratum). Confirm no `repositories` symlink and nothing under `results/` is tracked in the diff.
+A5. Confirm the six pre-registered modules (`validate_runs.py`, `tables.py`, `figures.py`, `stats.py`, `bootstrap.py`, `style.py`) have an empty diff against `master`.
+
+### B. Frozen-specification integrity
+
+B1. Using `git log -p` on `docs/decisions/decision-log.md`, confirm the D-89 text is identical in every commit after `edda901`, and that D-90 and D-89 were not edited by the D-91 commit (`7ee6065`).
+B2. Confirm `edda901` (which freezes D-89) precedes every commit that adds `posthoc.py` or any output.
+B3. The status row for ANALYSIS-004 lists commits only up to `7ee6065`; report whether `4c6330a` (or `fa57170`) changes any file other than the erratum wording.
+
+### C. Reproduction
+
+C1. Run `tests/test_posthoc.py`. Then run the full suite on `task/ANALYSIS-004` and on `master`, and compare the **names** of failing tests (the handoff claims 20 pre-existing environment failures with an identical set on both; confirm or refute by name, and do not record counts in any decision per D-86(1)(b)).
+C2. Re-run the post-hoc stage into a **scratch directory** (not `final_output_posthoc`) using the command in D-90(2)(a), at the branch head. If the code changed after `e3b563d`, say so and note which modules.
+C3. Compare every CSV and Markdown file in the scratch output with `/home/lukexodus/projects/thesis-analysis/final_output_posthoc` (expect byte-identical). PDFs may differ in `CreationDate`; PNG dimensions may differ with text metrics. Compare `pipeline_modules_sha256` in both `RUN_INFO.txt` files against the files at head.
+C4. Confirm `final_output_final` is unchanged (re-run the default no-flag pipeline into a second scratch directory and compare CSV/Markdown byte-for-byte, as in D-90(5)(b)).
+
+### D. Numbers
+
+D1. Recompute independently of `posthoc.py` (your own short script, not imports from it): T7 scores for all 24 corpus × scenario × strategy rows; the T8b exact rank shares; T9 TOPSIS closeness and τ-b using the weighted-before-distances form of D-89(9); the T9b top-match count. Report the maximum absolute difference to the committed CSVs.
+D2. Confirm the DSA S2 rank-2 Monte Carlo cell: |MC − exact| = 0.004597, and report the SE ratio computed **both** with the MC share (0.0543) and with the exact share (0.0589). D-91 uses the first and gives about 2.9; an APC recomputation with the second gave about 2.8. Both are above one SE; state the two values.
+D3. Confirm G3 margin stopping points: S1 stops being dominated at ΔF1 = 0.150658 and S4 at 0.155862 (erratum), against `stats.evaluate_dominance` unchanged.
+
+### E. Documentation defects found by the APC (record, do not fix in place)
+
+E1. **Erratum digit slip.** `ANALYSIS-004-claude-code-erratum.md` (E10a scope paragraph) writes the S4 DSA size-matched baseline as **0.2498**. T5b, the report and D-90 give **0.2488** (6.9655 / 28 = 0.24877). Confirm which is correct from T5b's CSV, and whether 0.2498 appears anywhere else in the repo.
+E2. **D-90(4)(c) labelling.** It says "On DSA, S4 rank 4 is 0.2667 against 0.26". In T8b the exact share is 0.2650 and the Monte Carlo share is 0.2667. Confirm which D-90 means, and whether the sentence is ambiguous.
+E3. Check whether any other sentence in the report, D-90 or D-91 mixes exact and Monte Carlo values without labelling them.
+
+### F. Thesis docx against the committed outputs (read-only)
+
+Use `docs/thesis/_REVISED__An_Empirical_Complexity_Analysis_of_Candidate-Narrowing_Strategies_for_Incremental_LLM-Driven_Graph_Construction_With_Chapter_4_ANALYSIS-004.docx` (untracked in the main checkout). If it is missing, use the copy at `docs/context/handoff-inputs/`. Extract text with `pandoc` and compare these against `final_output_posthoc`:
+
+F1. Table 4.9 (8 updated cells and caption) against T7.
+F2. Table 4.10 (7 updated cells) against the **Monte Carlo** column of T8 at 2 decimals; and the "68%" statement against T8b (S3 Metacademy rank 2: exact 0.6803).
+F3. Table 4.11 and the cross-check paragraph against T9, T9b and T8b: τ-b values, the T9b match count (must read 3 of 6, not 2 or 4), the Monte Carlo-versus-exact maximums (0.0046 DSA, 0.0022 Metacademy), and the "at most about 0.004" standard-error statement.
+F4. The sentence narrowing the DSA-leader caveat: under TOPSIS, S3 leads DSA accuracy-first (0.7194 vs 0.7000 for S1). Confirm the thesis wording is true against T9, and that the cost-first S3/S4 adjacent swap is not misstated.
+F5. The two "about level" sentences (Section 4.3.2 and Section 4.4.1 / 4.7 equivalents: 0.259 against 0.249) against T5b.
+F6. The Section 3.6.3 C_i formula contains the `1 −` reversal; the RNG sentence matches D-89(7)(a); the weighted-TOPSIS wording matches D-89(9). The Section 4.7 RQ3 row reads "Tables 4.6 to 4.11".
+F7. Report any numeric statement in the new Section 4.4.1 text that has no corresponding cell in T5–T9b.
+
+## 3. Deliverables (AGENTS.md "After finishing any task")
+
+1. Commit on `task/ANALYSIS-004-A` (conventional message).
+2. Patch file: `patch/ANALYSIS-004-A-claude-code-premerge-audit.patch` (`git diff HEAD~1`).
+3. Report: `docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md`. Executive summary first, then a table of A1–F7 with PASS / FAIL / UNABLE, then the verbatim `git diff`, patch reference, and an "Items for the APC" section. List every untracked file you saw. Run `./scripts/validate-report.py docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md --require-patch`.
+4. Decision entry **D-92** recording only corrections found (E1, E2, any FAIL), by later entry. If nothing failed, record that the audit found no defects, and the verified head hash.
+5. Add your own row to `docs/tasks/status.md` for ANALYSIS-004-A; do not edit other rows.
+6. In your final message, state the branch name, worktree path, the head hash from A1, and the answer to A2 first.
+
+## 4. Do not decide
+
+Do not decide how the docx text is synced into the repo's markdown, and do not decide whether to merge. State, for Luke, anything in sections A–F that should block the merge, and anything that should not.
diff --git c/docs/tasks/status.md i/docs/tasks/status.md
index d3838da..42e49b3 100644
--- c/docs/tasks/status.md
+++ i/docs/tasks/status.md
@@ -79,6 +79,7 @@ Status: **in-progress**
 | ANALYSIS-002-G | Independent review of ANALYSIS-002-F Phase 4 analysis pipeline remediation | **done** | Completed by Gemini; branch `task/ANALYSIS-002-G` at commit `ccec59c` (base `f5e085d`). See report [`docs/reports/ANALYSIS-002-G-gemini-review.md`](docs/reports/ANALYSIS-002-G-gemini-review.md). |
 | ANALYSIS-003 | Add exploratory log-scale companion figures F1b, F2b, F6b and record D-87 | **done** | Completed by Gemini; branch `task/ANALYSIS-003` at commit `5ab04a6` (base `79046eb`). See report [`docs/reports/ANALYSIS-003-gemini-report.md`](docs/reports/ANALYSIS-003-gemini-report.md). |
 | ANALYSIS-004 | Add the post-hoc decision and ranking stage (Tables T5–T9b, Figures F7–F9; thesis Sections 3.6 and 4.4.1), including TOPSIS, Kendall tau-b and the wall-clock-substituted check; freeze the specification in [D-89] and record implementation/results in [D-90]. | **done** | Completed by Claude Code; branch `task/ANALYSIS-004` merged to master at `c05d1e0` (base `a524de7`; commits `edda901`, `8e2eccf`, `e3b563d`, `f4ba18a`, `b32ee07`, `7ee6065`, `4c6330a`, `fa57170`). Post hoc, not pre-registered; no live calls; gate passed; 72 cross-check cells matched. See report [`docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md`](docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md); review corrections in erratum [`docs/reports/ANALYSIS-004-claude-code-erratum.md`](docs/reports/ANALYSIS-004-claude-code-erratum.md) ([D-91]). |
+| ANALYSIS-004-A | Direct repo audit of the merged ANALYSIS-004 state: branch provenance, frozen-specification integrity, reproduction of the post-hoc and default outputs, independent recomputation of T7/T8b/T9/T9b, and docx-versus-outputs checks. | **done** | Completed by Claude Code; branch `task/ANALYSIS-004-A` (base `678c170`). No code/result/table/figure defect; four documentation corrections recorded in [D-92]. See report [`docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md`](docs/reports/ANALYSIS-004-A-claude-code-premerge-audit.md). |
 | DOC-012 | Correct the [D-84] record of Luke's inspection answer and peak-launch recollection, two status-row commit claims, final pipeline provenance, and known limits of the exploratory companion figures ([D-88]) | **needs-review** | Docs only. Completed by Claude Code; branch `task/DOC-012` at commit `6f198c5` (base `554bde3`). See report [`docs/reports/DOC-012-claude-code-correction.md`](docs/reports/DOC-012-claude-code-correction.md). |
 
 ## Thesis document status (separate track from the code work above)
```

**Patch file:** `patch/ANALYSIS-004-A-claude-code-premerge-audit.patch` (`git diff 678c170..HEAD`, all commits of this task).

---

## Items for the APC

1. **Apply the four documentation corrections in [D-92]**: erratum `0.2498 → 0.2488`; relabel D-90(4)(c)'s S4 rank-4 sentence as MC 0.2667 vs scratch 0.26 (exact 0.2650); label the three unlabelled exact shares in that sentence; change the S4 G3 stopping point from 0.155862 to 0.155867 (erratum and handoff).
2. **No merge blocker from this audit.** The already-performed merge is sound on code, results, tables, figures and reproduction.
3. **Thesis and deck are unaffected** by these text slips; the docx numbers match the CSVs.
4. **Stale refs to clean up later**: the handoff says head `4c6330a` and master `a524de7`; both predate the merge/sync block that now sits at the top of the same document.
5. **Do not merge the `repositories` symlink** in the audit worktree; it is test support only.
