# APC-to-APC Handoff — 2026-10-28, after ANALYSIS-004

**For the incoming APC instance.** You have no filesystem access and no
memory of the session that produced this. This document plus the repo files
it names is the transfer. The core bundle referenced at the end carries the
current text of every file named here, plus the edited docx and the
ANALYSIS-004 outputs.

---

## 1. Orientation (unchanged)

You are the APC AI for a CS undergraduate thesis project. You coordinate by
writing standalone prompts that Luke relays to local coding agents (Claude
Code, Gemini, opencode) who have filesystem access. The repo — not this
document, not any chat — is the source of truth.

Read, in this order, before acting:

1. `docs/context/complete-context.md`
2. `docs/context/data-formats.md`
3. `docs/decisions/decision-log.md` (at least D-79 and D-83 through D-91)
4. `docs/tasks/status.md`
5. `docs/context/analysis-plan.md` (frozen plan, Rules R1–R3, Amendments 1–4)
6. Sections 2–5 below

The current repo state is summarised in Section 5; do not assume any earlier
APC's memory of paths, commits or numbers.

---

## 2. What changed this session

### ANALYSIS-004 — post-hoc decision and ranking stage (DONE, needs-review, unmerged)

The revised thesis's post-hoc framework (Sections 3.6 and 4.4.1) is now a
reproducible, gate-validated pipeline stage.

- **Frozen specification** in **[D-89]** (committed before any computation;
  post hoc, not pre-registered). **Implementation, results and provenance**
  in **[D-90]**. **Review erratum** in **[D-91]**.
- **Code:** new `scripts/analysis/posthoc.py` and
  `scripts/analysis/posthoc_figures.py`; `scripts/analysis/run_analysis.py`
  gains `--only posthoc` and `--crosscheck-dir`. No pre-registered module
  changed; G3 uses `stats.evaluate_dominance` unchanged.
- **Inputs:** the in-memory T1/T2/F6 aggregates; 72 cells asserted equal to
  `final_output_final` before writing. Validation gate passed, 24 runs,
  `src_diff_clean: True`.
- **Outputs (new directory, nothing pre-registered regenerated):**
  `/home/lukexodus/projects/thesis-analysis/final_output_posthoc` —
  Tables T5, T5b, T6, T7, T8, T8b, T9, T9b (CSV + MD), Figures F7, F8, F9
  (PDF + PNG + CSV), `RUN_INFO.txt`. Gate PASS; run commit `e3b563d`.
- **Results:** S3 Effective; S2 Conditionally effective; S1 and S4 Not
  effective. Gate classes unchanged for every G2 limit 10–1,999, under the
  size-matched G1 baseline, and for every G3 margin 0.000–0.150 (report the
  first change as "none up to 0.15"). TOPSIS τ-b: 0.6667 on DSA
  accuracy-first and cost-first, 1.0 on DSA balanced (1 tied pair) and all
  Metacademy scenarios. Exact shares agree with Monte Carlo to ≤0.0046 (DSA)
  and ≤0.0022 (Metacademy); the DSA S2 rank-2 cell is 2.9 SE, not under one
  SE — see [D-91].
- **Independent review outcome:** all recomputed numbers matched; two
  report sentences were wrong (T9b matches are 3 of 6, not 2; the MC
  dispersion claim above), corrected in the erratum and [D-91]. The C_i
  formula finding was confirmed.
- **Branch:** `task/ANALYSIS-004`, head `4c6330a`, base `a524de7`, worktree
  `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-004`.
  Commits: `edda901` (D-89 + Amendment 4), `8e2eccf` (code/tests),
  `e3b563d` (figure layout), `f4ba18a` (D-90 + status), `b32ee07` (report +
  status), `7ee6065` (D-91 + erratum), `4c6330a` (erratum wording).
- **Report:** `docs/reports/ANALYSIS-004-claude-code-posthoc-ranking.md`.
  **Erratum:** `docs/reports/ANALYSIS-004-claude-code-erratum.md` (this is
  the authoritative correction; the original report's two wrong sentences
  were deliberately not edited, per the one-file-per-task report rule).
- **Patch:** `patch/ANALYSIS-004-claude-code-posthoc-ranking.patch`
  (`git diff a524de7..f4ba18a`, 2,355 lines; `patch/` is gitignored).
- **Outputs bundle:** `/home/lukexodus/projects/thesis-analysis/bundle_c_posthoc_outputs.tar.gz`.

### Thesis edits applied by the ending APC (docx only)

The ending APC applied the ANALYSIS-004 delta to the docx and replaced
Figures 4.11–4.13 with F7/F8/F9. **This new text exists only in the docx in
`docs/thesis/`, not in the repo's markdown.**

- File: `docs/thesis/_REVISED__An_Empirical_Complexity_Analysis_of_Candidate-Narrowing_Strategies_for_Incremental_LLM-Driven_Graph_Construction_With_Chapter_4_ANALYSIS-004.docx`
- Text export for reading: `/home/lukexodus/projects/thesis-analysis/ANALYSIS-004_thesis_export.md`
  (pandoc gfm; the C_i formula is present as `C_i = 1 − …`).
- Verified in the docx: `numpy.random.default_rng(42)`, the exact-share
  sentence, the weighted-TOPSIS wording, `--only posthoc`, "68%",
  `about level`, "Tables 4.6 to 4.11", Table 4.11.
- Figures inside the docx keep the names `image1.png`, `image2.png`,
  `image9.png`; a pandoc export shows the new figures under those names.
- Keep-with-next applied so each figure stays with its caption.
- Two deviations from the delta: "about level" replaces "marginally above"
  for S4 against the size-matched baseline, and the paragraph narrows the
  DSA-leader caveat to brute force's accuracy-first lead only. Both are
  consistent with T5b/T9; no number changes.

---

## 3. What is in flight

- **ANALYSIS-004 is `needs-review` and its branch is unmerged.** The
  worktree remains at
  `/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-004`.
  Do not merge the untracked `repositories` symlink inside it (test support
  only).
- **Thesis text is split.** The edited docx is authoritative for the new
  Section 3.6.3/4.4.1 text; the repo's revised `.md` predates those edits
  and is untracked. The original Chapter 1–3 `.md` is **deleted in the main
  working tree** (unstaged) and also untracked new files sit beside it. No
  decision has been made on how to sync the docx text into the repo.
- **Deck:** slide 37 still needs "0.907 to 0.960" → "0.905 to 0.959" and
  "69%" → "68%"; slide 22 is Luke's image fix. Slides 27 and 36 need no
  change.
- Older `needs-review` rows (INFRA-011, DOC-004, DOC-004-B, DOC-004-C,
  DOC-006, DOC-012) are unchanged by this session.

---

## 4. What to do first

1. **Review and merge ANALYSIS-004** (or write a follow-up). Read the report,
   the erratum and [D-89]/[D-90]/[D-91]; the independent review already
   confirmed the numbers and the only corrections are the erratum's. Merge
   only after review. Do not merge the `repositories` symlink.
2. **Decide the thesis sync.** The docx holds the only current Chapter 3–4
   text. If the repo should own it, write a DOC task that lands the docx
   export (or a hand-edited markdown) into `docs/thesis/`, preserving the
   old file history and recording the source docx path; otherwise record
   that the docx is the working copy and the repo `.md` is stale.
3. **Close the deck edits** (slide 37; slide 22 is Luke's).
4. Then pick up the open thesis items in Section 5.

---

## 5. Repo state and unresolved items

### Current repo state (verified from git at handoff time)

- `master` is `a524de7`; it does **not** contain the ANALYSIS-004 branch.
- `task/ANALYSIS-004` head `4c6330a`; `task/ANALYSIS-001-G`, `-002`, `-003`
  are merged into master (their worktrees still exist).
- Main working tree is **dirty with Luke's edits**: `.gitignore` modified,
  `docs/context/repo-tree.txt` modified, original thesis `.md` deleted
  (unstaged), and untracked `docs/thesis/[REVISED] …With Chapter 4.md`,
  the ANALYSIS-004 docx, `docs/thesis/buffer/`,
  `docs/thesis/previous-versions/`, `docs/presentation/`,
  `redraw_thesis_figures.py`. Do not treat these as committed state.
- `patch/` is gitignored; patch files exist but are untracked by design.
- The hashes file recorded in earlier provenance as
  `~/run-logs/final-results-hashes.txt` now lives at
  `/home/lukexodus/projects/run-logs/final-results-hashes.txt` (same
  sha256 `a4f7109b…`).
- Full test suite has 20 pre-existing environment failures (faiss and
  torch/sentence-transformers absent, plus a source-grep collision in
  `scripts/analysis/apc_check_f_outputs.py`); the same failure set exists
  on unmodified master. The ANALYSIS-004 tests pass.

### Open thesis items (not addressed this session)

1. **Section 3.2.2 vs Chapter IV synthetic-data conflict.** Chapter 3.2.2
   and Chapter 4 describe the synthetic data differently; decide the correct
   description and fix one of them.
2. **"Section 3.5" cross-reference** in the RQ4 discussion points to the
   wrong/stale section.
3. **Nine unchecked references [14]–[22].** Verify them against sources;
   the catalogue is in `docs/rrl/catalogue.md`.
4. **TOC page numbers** may be off by one after the new 4.4.1 material; the
   TOC is static.
5. **Equations in Word.** LibreOffice did not render them; the C_i fix was
   confirmed from the pandoc export, but check the docx in Word.
6. **Figure 4.12 left-end labels** (S1–S4 at w = 0) overlap the y-axis.
   Readable, left as a small later fix. If a FIX task is written, it should
   change only annotation offsets in `posthoc_figures.py`, regenerate F8,
   and re-run the no-change proof.
7. **Table 4.10 is Monte Carlo at 2 dp.** It may not sum to 1.00 per row;
   T8b has the exact shares. The thesis already notes the rounding.
8. **G3 margin headroom.** "Any margin up to 0.15" is true but tight: S1
   stops being dominated at 0.150658 and S4 at 0.155862.
9. **DSA leader caveat.** Under TOPSIS, S3 leads DSA accuracy-first
   (0.7194 vs 0.7000); the brute-force lead in Table 4.9 is weighted-sum
   specific. Cost-first has an adjacent S4/S3 swap. The ending APC narrowed
   the thesis sentence to the accuracy-first brute-force lead only; confirm
   that wording against T9.

### Decisions already settled (do not reopen without a new entry)

- TOPSIS uses the weighted-before-distances form ([D-89](9)); no
  recomputation is needed.
- Table 4.10 stays Monte Carlo; the exact shares are a cross-check.
- The DSA caveat goes in the new cross-check paragraph, not in a slide
  change.
- ANALYSIS-004 outputs are post hoc, not pre-registered.

---

## 6. Pasted content — ending APC's final reply (verbatim)

> The edited docx passes validation. I'm now rendering it to check the figures, the new table and the formula, and diffing against the original.
>
> I've added keep-with-next so each figure stays on the same page as its caption, and I'm re-checking the rendered pages now.
>
> I applied all the text edits and replaced the three figures myself, so you don't need to do any image work. The edited docx is the `…_With_Chapter_4_ANALYSIS-004.docx` file attached to this reply. It passes the docx validator. I diffed the old and new text and the only changes are the intended ones. I also rendered the pages to check the figures. The new text is only in this docx, not in the repo.
>
> **Figure replacements**
> - The three images keep their old names inside the docx (`image1.png`, `image2.png`, `image9.png`), so a pandoc `.md` export will show the new figures under the same file names.
> - Figure 4.11 is now `F7_gates_g1_g2.png`, Figure 4.12 is `F8_score_vs_weight.png` and Figure 4.13 is `F9_rank_shares.png`.
> - I resized each to its new proportions and removed the old crop on Figure 4.12.
> - I set each figure to stay on the same page as its caption. Without that, Figure 4.13's caption landed alone at the top of the next page.
>
> **Text edits applied** (all as in the delta, with these deviations)
> - **Section 3.6.3:** the C_i formula, the RNG sentence plus the exact-share sentence, and the weighted TOPSIS wording.
> - **Section 4.1:** the fourth post-hoc group now cites D-89, Amendment 4 and `--only posthoc`.
> - **Table 4.9:** caption and eight cells updated, with the bold leaders unchanged.
> - **Table 4.10:** seven cells updated, and "69%" is now "68%".
> - **Cross-checks paragraph and Table 4.11:** added after Figure 4.13, and the Section 4.7 RQ3 row now says "Tables 4.6 to 4.11".
> - **My changes to the delta:** I used "about level" rather than "marginally above" for Strategy 4 against the size-matched baseline, to match Section 4.3.2. I also narrowed the paragraph's claim about the DSA leaders: only the accuracy-first lead of brute force depends on the weighted-sum method.
>
> **Check these in Word**
> - **Equations:** LibreOffice doesn't draw the equations in this file, and it doesn't draw them in your original either. I confirmed the C_i fix from the pandoc export (`C_i = 1 − g_i…`), but please look at it once in Word.
> - **Table of contents:** the table of contents is a static table, so its page numbers may be off by one after Section 4.4.1.
> - **Figure 4.12:** the left-end labels (S1–S4 at w = 0) overlap the y-axis. They are readable, so I left it; it's a small fix to ask the agent for later.
>
> **Still open**
> - **Thesis:** the Section 3.2.2 vs Chapter IV synthetic-data conflict, the "Section 3.5" cross-reference, and the references [14]–[22].
> - **Deck:** only slide 37 needs the 0.905 to 0.959 and 68% edits, and slide 22 is still your image fix.
> - **Repo:** the ANALYSIS-004 branch review and merge, and syncing this docx's text into the repo.

---

## 7. Bundle contents

Built from the ANALYSIS-004 worktree so that it carries the post-merge-view
status and decision log (including [D-91]). It contains the core context
files, the frozen analysis plan, the catalogue, the revised thesis markdown,
the edited ANALYSIS-004 docx, the pandoc text export, the task report and
erratum, and the current `repo-tree.txt`. Path and checksum are in the
message that accompanies this handoff.

The pre-registered and post-hoc **outputs** are not inside that bundle; they
are at `/home/lukexodus/projects/thesis-analysis/final_output_posthoc`
(re-bundled as `bundle_c_posthoc_outputs.tar.gz`).
