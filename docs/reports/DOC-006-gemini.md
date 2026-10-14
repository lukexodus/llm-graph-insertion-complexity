# DOC-006 Report — Close DOC-002, Record [D-69], Narrow data-formats Orientation Claim, Fix Phase 2 Header, Report Errata

- **Task ID:** DOC-006 (prompt issued as DOC-005 by APC-A on 2026-10-14; designated DOC-006 per Luke's instruction: "another doc-005 named task is running so use another id")
- **Agent:** Gemini (Advanced Agentic Pair Programmer)
- **Model:** `gemini` (Antigravity session)
- **Date:** 2026-10-14
- **Branch:** `task/DOC-006`
- **Worktree:** `/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-006`
- **Base Commit:** `52e05c6` (master, following landing of DOC-005 which claimed `[D-68]`; decision entry renumbered to `[D-69]` with Luke's confirmation)

---

## 1. Step 0 — Pre-checks (Verbatim Output)

The pre-check commands were run in `/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-006`:

```bash
$ git rev-parse --short HEAD
52e05c6

$ git status --short

$ grep -c 'DOC-006' docs/tasks/status.md || true
0

$ grep -o '\*\*\[D-[0-9]*\]\*\*' docs/decisions/decision-log.md | sort -t- -k2 -n -u | tail -1
**[D-68]**

$ git cat-file -t f141457
commit

$ T="docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"; git rev-parse "f141457:$T"
c13d749de3af4da36fc9d1df6ec96a0ab9a1d827

$ git rev-parse f141457:docs/context/complete-context.md
6da7dcdff15da3b164642248ffac4b63013d686c
```

### Decision ID Resolution
During execution, `DOC-005` landed on `master` at commit `52e05c6`, claiming decision ID `[D-68]`. Per `AGENTS.md` Rule 4 and Prompt Step 0, the conflict was reported to Luke, and with Luke's instruction to proceed, the decision ID for this task was assigned to **`[D-69]`**.

### Pre-check verification of draft defect counts in commit `6315f35`

Before appending `[D-69]`, the 4 draft defect counts mentioned in item (1) were checked against `6315f35` thesis blob:

```bash
$ T="docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
$ git show 6315f35:"$T" | grep -c -F 'Claude 3.5'
1
$ git show 6315f35:"$T" | grep -c -F 'headless'
1
$ git show 6315f35:"$T" | grep -c -F '176'
1
$ git show 6315f35:"$T" | grep -c -F '19,881'
1
```
All four counts returned $\ge 1$ (each exactly 1), confirming all 4 defect mentions in item (1) of `[D-69]` are factual. None were removed.

---

## 2. Real Diff of the Three Edited Files

The verbatim output of `git diff -- docs/decisions/decision-log.md docs/tasks/status.md docs/context/data-formats.md` (the report file itself `docs/reports/DOC-006-gemini.md` is excluded):

```diff
diff --git i/docs/context/data-formats.md w/docs/context/data-formats.md
index d8ef1b4..826b8b7 100644
--- i/docs/context/data-formats.md
+++ w/docs/context/data-formats.md
@@ -62,7 +62,7 @@ Ten files confirmed present in `repositories/dataset/EKG-Dataset/`:
 *(Note exact filenames: 9 of the 10 files contain `with_<n>_nodes` with underscores).*
 
 - **Format:** **All 10 files are semicolon-delimited (`;`)**, matching DSA. None are space-delimited.
-- **Directionality / Semantics (CRITICAL — REVERSED FROM D-15):** in **all 10 files without exception**, `concept1.txt;concept2.txt;1` means **`concept1` is a prerequisite of `concept2`** (i.e. Column 1 is the prerequisite, Column 2 is the dependent concept). This is **unanimously reversed** from the DSA and Metacademy convention ([D-15]), where Column 2 was the prerequisite. Verified systematically across all 10 files in task DATA-002 (see report `docs/reports/DATA-002-gemini-mekg-directionality.md` and decision-log [D-19]).
+- **Directionality / Semantics (CRITICAL — REVERSED FROM D-15):** in **all 9 example files that share concepts with a gold graph**, `concept1.txt;concept2.txt;1` means **`concept1` is a prerequisite of `concept2`** (i.e. Column 1 is the prerequisite, Column 2 is the dependent concept). This is **reversed** from the DSA and Metacademy convention ([D-15]), where Column 2 was the prerequisite. Checked against the gold graphs in task DATA-002: 171 positive example rows agree with the reversed orientation and none contradict it, and the other 254 positive rows between gold-graph concepts lie on pairs the gold files label 0 (see report `docs/reports/DATA-002-gemini-mekg-directionality.md` and decision-log [D-19], [D-69]). The tenth file, `MEKG_with_8_nodes(logic).txt` (8 concepts, 15 positive rows), shares no concept with either gold graph, so its orientation could not be checked against gold; it is assumed to follow the same convention on the strength of domain reasoning only.
 - **Concept Name Extension Quirk (CRITICAL):** in all 10 files, every concept name has a `.txt` filename suffix attached (e.g. `hash_table.txt;asymptotic_complexity.txt;0`). Loaders must strip `.txt` from node names when parsing.
 - **Coverage:** each file contains $N \times N$ lines (full Cartesian product including $N$ self-loops, all labeled `0`).
 - **Concept name edge case:** `Godel's_completeness_theorem.txt` in `MEKG_with_8_nodes(logic).txt` contains an apostrophe without quoting; parses cleanly.
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 865ba8e..6f87a1d 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -563,3 +563,11 @@ Total planned calls: 159,400 sweep + 25,358 accuracy = 184,758 combined calls. S
 (5) OpenMP / PyTorch thread check procedure and decision rule (D5): `faiss.omp_set_num_threads(1)` is called only by `ann_retrieval.py` for determinism. If FAISS and PyTorch share an OpenMP runtime, Strategy 3's `embed_s` could run single-threaded while Strategies 2 and 4 run multi-threaded. Luke will run the standalone benchmark snippet documented in `scripts/README.md` (3 fresh processes per condition interleaved, measuring 200 single-name `embed()` calls after 20 warmup calls). The decision rule is pre-fixed prior to measurement: the statistic is the median of the three per-process medians. The effect is material if `torch.get_num_threads()` differs between conditions, OR the `omp1` median differs from `default` by >10% AND by more than the largest within-condition spread ($\max - \min$ of the three medians). If not material, the result is recorded as an operational limitation with no code change. If material, a follow-up task explicitly sets PyTorch thread count across all embedding strategies while keeping FAISS single-threaded ([D-47]). Non-pilot live runs of Strategies 2, 3, and 4 wait for this determination; brute force does not.
 (6) Open items: (a) The OpenMP thread check remains to be executed by Luke; (b) The live pilot (Strategy 3 on DSA) and 24 benchmark runs have not been executed; (c) Thesis text synchronization: existing statements in §2.2.4 ("directly designed to address"), §3.5 ("directly compared against that claimed bound"), and DOC-004 proposed text must reflect that the single-insertion protocol measures an un-amortised step rather than testing the amortised bound directly (for APC-A and the DOC-004 reviewer; not edited here); (d) `docs/tasks/high-level-tasks.md` Phase 4 promise of a direct comparison against Theorem 4's predicted shape is made stale by D1 (not edited here).
 Reasoning: records the operator's decisions on run phasing, dual-mode evaluation, pilot specification, off-peak scheduling, and thread checking, anchoring all 24 configurations with verified offline call bounds. Affects: `scripts/README.md`, `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/reports/DOC-005-gemini-run-plan.md`, RUN-001.
+
+**[D-69]** Close DOC-002 with the DOC-002-B text, clarify D-33 hold-out wording, record confirmed data counts and corrections to D-19 and DATA-002 (APC-A):
+(1) Accepted text: Chapter 3 of the thesis is blob `c13d749de3af4da36fc9d1df6ec96a0ab9a1d827` and `docs/context/complete-context.md` is blob `6da7dcdff15da3b164642248ffac4b63013d686c`, both landed in commit `f141457` (DOC-002-B). The text was written by the APC from the pre-DOC-002 thesis and checked against `decision.py`, `scoring.py`, `null.py` and this log; the v2 system-prompt block in Section 3.2.6 is character-identical to `SYSTEM_PROMPT` in `decision.py` [Confirmed in sandbox]. It supersedes the DOC-002 draft committed in `6315f35`, which carried unsourced or wrong claims (for example a wrong generator model name, "Claude 3.5 Sonnet", where the observed label was "Sonnet 5 Low"; a "headless" browser and "rotated browser profiles" description; 176 overlapping positive edges where the count is 171; and a Metacademy line count of 19,881 where the file has 19,740). The DOC-002-B report's section 6 diff is empty; the real diffs are `git diff acc861f c13d749` (thesis, 5 hunks, all in Sections 1.5, 3.2.6, 3.3.1, 3.3.2, 3.4 and 3.5) and `git diff dc77b62 6da7dcd` (`complete-context.md`, 1 hunk in Section 7) [Confirmed: APC read both patches]. DOC-002 is closed.
+(2) D-33 clarification, no change to D-33: item (2) records that v1 (zero-shot) was probed on six DSA pairs, so those six DSA pairs were seen before v2 existed; item (3) records that v2 itself was selected using only non-DSA, non-Metacademy pairs. Both hold. Thesis Section 3.2.6 states both. Whether the later one-call pre-sweep sanity check uses a DSA pair is not decided here.
+(3) Confirmed data facts (Luke's run of the APC's script, relayed by an agent): DSA gold has 841 lines, 54 positive edges, transitive reduction 40 edges (14 redundant); Metacademy gold has 19,740 lines (141 x 140), 318 positive edges, transitive reduction 213 edges (105 redundant). Across the nine example files that share concepts with a gold graph, 425 positive rows lie between concepts that appear in a gold graph: 171 agree with the reversed orientation, 0 contradict it, and 254 lie on pairs the gold file labels 0 (matches [D-04] and [D-05]). `MEKG_with_8_nodes(logic).txt` has 8 concepts, 15 positive rows and no overlap with either gold graph.
+(4) Corrections by later entry: the DATA-002 report's total of 176 overlapping positive edges is an arithmetic error (its per-file counts sum to 171, and 171 + 254 = 425); the report is write-once and is corrected in the DOC-006 report errata. [D-19] states that the reversed orientation was verified in all 10 example files; for `MEKG_with_8_nodes(logic).txt` it rests on domain reasoning only, so `data-formats.md` is narrowed to the nine checkable files.
+(5) Not decided here: whether thesis Section 3.5 may keep comparing the observed curve with the amortised bound in [4] (Research Question 4) given [D-62](4), under which the sweep performs one insertion per trial after `setup()`; and the Strategy 4 text sync of [D-59](8) (see DOC-004).
+Reasoning: records what was accepted and why, so later readers do not mistake the DOC-002 draft for the accepted text, and keeps the decision log append-only while correcting overstated statements. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/context/complete-context.md`, `docs/context/data-formats.md`, `docs/tasks/status.md`, `docs/decisions/decision-log.md`, `docs/reports/DOC-002-gemini.md`, `docs/reports/DOC-002-A-gemini.md`, `docs/reports/DOC-002-B-gemini.md`, `docs/reports/DATA-002-gemini-mekg-directionality.md`, DOC-002, DOC-006.
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index 42f1aaf..8284e63 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -42,7 +42,7 @@ Status: **done** (Phase 1 exit criterion INFRA-005 accepted at APC review 2026-1
 
 ## Phase 2 — Four Parallel Strategy Tracks
 
-Status: **open** (unblocked following Phase 1 completion; four parallel tracks ready for implementation)
+Status: **done** (STRAT-001 to STRAT-004 done and accepted; strategies wired into the experiment CLI under INFRA-007)
 
 | ID        | Task                                       | Status           | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
 | --------- | ------------------------------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
@@ -79,7 +79,7 @@ Status: **not started** (blocked on Phase 3)
 | ID      | Task                                                                                                  | Status   | Notes / Report                                                                                                                               |
 | ------- | ----------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
 | DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md). |
-| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3; Section 3.2.6 model specification uses official alias deepseek-flash per [D-36] and [D-37], noting that API responses report only the alias without internal model version, and timed runs are executed off-peak; Chapter 3 limitation text must report empirical DSA brute-force ceiling metrics from [D-37](2): micro F1 0.541, recall 0.611, precision 0.485, flip rate 15.38%, swap consistency 85.71%). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked; and record corrected per-file test counts (earlier "40/35" narrative was a misread report breakdown, see FIX-006 report). | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-002-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-002-gemini.md). Corrected by DOC-002-A (Gemini) and DOC-002-B; see [`docs/reports/DOC-002-B-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-002-B-gemini.md). |
+| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge; exact PROMPT_VERSION v2 text per [D-33] must be reproduced in Chapter 3; Section 3.2.6 model specification uses official alias deepseek-flash per [D-36] and [D-37], noting that API responses report only the alias without internal model version, and timed runs are executed off-peak; Chapter 3 limitation text must report empirical DSA brute-force ceiling metrics from [D-37](2): micro F1 0.541, recall 0.611, precision 0.485, flip rate 15.38%, swap consistency 85.71%). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). Also clarify that the DSA "missing pair" is one missing ordered row (reverse row exists, labeled 0); check catalogue #9's transitive-reduction wording; reconcile thesis 3.2.6 "and, if so, its type" with prerequisite-only evaluation; note that `MEKG_with_8_nodes(logic).txt` has no overlap with gold, so its orientation was not cross-checked; and record corrected per-file test counts (earlier "40/35" narrative was a misread report breakdown, see FIX-006 report). | **done** | Completed by Gemini; see [`docs/reports/DOC-002-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-002-gemini.md). Corrected by DOC-002-A (Gemini) and DOC-002-B; see [`docs/reports/DOC-002-B-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-002-B-gemini.md). Accepted at APC review 2026-10-14 (APC-A) with the DOC-002-B text, landed in f141457; see [D-69] and `docs/reports/DOC-006-gemini.md`. |
  | FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-001-gemini-infra-001-followup.md). |
  | FIX-002 | Hardening pass on INFRA-002: edge validation before graph mutation, shortlist contract validation, required keyword-only metered_embedder, single-embedding caching and unmetered detection, texts_log for D-21 enforcement, diagnostics error handling, apply_s timing, reusable StrategyConformanceSuite. | **done** | Completed by Gemini. See report [`docs/reports/FIX-002-gemini-infra-002-hardening.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-002-gemini-infra-002-hardening.md). |
  | FIX-003 | Follow-up hardening on FIX-002: enforce required non-Optional MeteredEmbedder, embedder identity check against strategy._embedder, separate validate_s from total_s equation, add embedding_calls_in_update integer metric, test setup embeddings in D-21 text compliance, and fix typing import. | **done** | Completed by Gemini. See report [`docs/reports/FIX-003-gemini-driver-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-003-gemini-driver-followup.md). |
@@ -100,4 +100,5 @@ Status: **not started** (blocked on Phase 3)
  | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
  | DOC-004 | Thesis sync after strategy track: proposed edits only (Strategy D parameters and adaptation wording; Theorem 4 symbol resolution n -> b and S_LLM scope; Strategy C index parameters, efSearch {64, 256}, and synthetic recall evidence; fallback rewording and candidate citations for M=16, efConstruction=200; theta=0.6 calibration limitation). Report and unified diff only; thesis unmodified. | **needs-review** | Completed by Gemini. See report [`docs/reports/DOC-004-gemini-thesis-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-sync.md) and diff [`docs/reports/DOC-004-gemini-thesis-proposed.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-proposed.diff). |
  | DOC-005 | Record the run-plan decisions (D-68), add the run plan to the README, verify the planned-call bounds offline. | **done** | Completed by Gemini. See report [`docs/reports/DOC-005-gemini-run-plan.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-gemini-run-plan.md). |
+| DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-006-gemini.md). |
```

Verification of diff file headers in the above diff block:
`grep -c '^diff --git' ` on the diff block yields exactly 3 (`docs/context/data-formats.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`).

---

## 3. Checks (Verbatim Output)

```bash
$ git diff --stat
 docs/context/data-formats.md   | 2 +-
 docs/decisions/decision-log.md | 8 ++++++++
 docs/tasks/status.md           | 5 +++--
 3 files changed, 12 insertions(+), 3 deletions(-)

$ grep -c '^\*\*\[D-69\]\*\*' docs/decisions/decision-log.md
1

$ git diff -U0 docs/decisions/decision-log.md | grep -c '^-[^-]' || true
0
```

Zero lines were removed from `docs/decisions/decision-log.md` (append-only preserved).

---

## 4. Errata

### 4.1 DOC-002-B Report (`docs/reports/DOC-002-B-gemini.md`)

In `docs/reports/DOC-002-B-gemini.md`, Section 6 ("Verbatim Git Diff") contains an empty code block. During generation, `git add -N` was executed on the report path before the report file existed on disk, resulting in an empty diff capture.

The real object diffs and hashes confirming the landed changes from pre-DOC-002 baseline to DOC-002-B are:

```bash
$ git diff --stat acc861f c13d749
 acc861f => c13d749 | 106 ++++++++++++++++-------------------------------------
 1 file changed, 31 insertions(+), 75 deletions(-)

$ git diff acc861f c13d749 | grep '^@@'
@@ -65,7 +65,7 @@ This study does not evaluate the narrowing strategies within an educational appl
@@ -191,59 +191,34 @@ This strategy organizes existing nodes into size-bounded groups ("buckets"), suc
@@ -251,15 +226,13 @@ This finding confirms that the language model frequently recognizes genuine indi
@@ -269,21 +242,15 @@ To extend the cost-scaling measurements beyond the ceiling of the largest availa
@@ -291,31 +258,20 @@ For each of the four candidate-narrowing strategies described in Section 3.2, an

$ git diff --stat dc77b62 6da7dcd
 dc77b62 => 6da7dcd | 13 ++++++-------
 1 file changed, 6 insertions(+), 7 deletions(-)

$ git diff dc77b62 6da7dcd | grep '^@@'
@@ -177,15 +177,14 @@ instance) means reading only what moved, not re-diffing a wall of unchanged

$ git diff acc861f c13d749 | sha256sum
b8472fb8782bac3a6484faab9c2c324e80c2bd52bb8ea80fbf5f2ff67f91fe72  -

$ git diff dc77b62 6da7dcd | sha256sum
d07fac05ca23885398019aca3cb3bb1f690b91f0f53cc013e6ecd855c7a2be92  -
```

The 5 hunks in the thesis correspond strictly to Sections 1.5, 3.2.6, 3.3.1, 3.3.2, 3.4, and 3.5. Sections 3.2.2–3.2.5 are untouched. The `complete-context.md` diff consists of exactly 1 hunk in Section 7. Both sha256 sums match the APC-A verification values identically.

### 4.2 DATA-002 Report (`docs/reports/DATA-002-gemini-mekg-directionality.md`)

In `docs/reports/DATA-002-gemini-mekg-directionality.md`, Section 3 contains the systematic verification summary table:

```markdown
| Filename | Domain | Total Nodes ($N$) | Total Positive Edges ($L=1$) | Overlap with Gold Standard ($L=1$) | Matches D-15 Forward | Matches D-15 Reversed | Convention Resolved |
|---|---|---|---|---|---|---|---|
| `MEKG_with_6_nodes(DS).txt` | Data Structures | 6 | 7 | 6 (DSA) | **0** | **5** (1 novel edge) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with7nodes.txt` | Machine Learning | 7 | 16 | 13 (Meta) | **0** | **9** (4 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_8_nodes(DS3).txt` | Data Structures | 8 | 18 | 14 (DSA) | **0** | **7** (7 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_8_nodes(DS4).txt` | Data Structures | 8 | 23 | 23 (DSA) | **0** | **11** (12 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_8_nodes(logic).txt` | Logic | 8 | 15 | 0 (None) | N/A | N/A (Domain reasoning) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_10_nodes(DS1).txt` | Data Structures | 10 | 29 | 24 (DSA) | **0** | **13** (11 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_10_nodes(DS2).txt` | Data Structures / ML | 10 | 19 | 14 (DSA + Meta) | **0** | **9** (5 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_18_nodes(ML).txt` | Machine Learning | 18 | 76 | 63 (Meta) | **0** | **24** (39 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_21_nodes(ML).txt` | Linear Algebra / ML | 21 | 138 | 127 (Meta) | **0** | **50** (77 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| `MEKG_with_35_nodes(ML1).txt` | Machine Learning | 35 | 244 | 141 (Meta) | **0** | **43** (98 novel edges) | **Reversed** ($\text{col}_1 \to \text{col}_2$) |
| **TOTAL** | — | — | **577** | **425** | **0** | **176** | **100% Reversed** |
```

Arithmetic audit of the table values:
1. **Reversed matches:** Summing the per-file counts from the table gives:
   $$5 + 9 + 7 + 11 + 13 + 9 + 24 + 50 + 43 = 171$$
   The table's TOTAL row claimed `176`, which is an arithmetic error ($176 \neq 171$).
2. **Novel / Gold-0 edges:** Summing the per-file parenthesized novel edges gives:
   $$1 + 4 + 7 + 12 + 11 + 5 + 39 + 77 + 98 = 254$$
3. **Total overlap:**
   $$171 + 254 = 425$$
   This perfectly accounts for the 425 total positive rows lying between concepts appearing in the gold graphs.

The DATA-002 report is write-once; this erratum records the arithmetic correction from 176 to 171.

### 4.3 DOC-002-A Report (`docs/reports/DOC-002-A-gemini.md`)

The claim table in `docs/reports/DOC-002-A-gemini.md` was copied from `DOC-002-gemini.md` and cites `driver.py`.

```bash
$ grep -c 'driver.py' docs/reports/DOC-002-A-gemini.md docs/reports/DOC-002-gemini.md
docs/reports/DOC-002-A-gemini.md:2
docs/reports/DOC-002-gemini.md:2

$ ls src/graph_insertion/driver.py
ls: cannot access 'src/graph_insertion/driver.py': No such file or directory
```

The module `src/graph_insertion/driver.py` does not exist in the repository (insertion driver functions reside in `harness.py`). The claim table in `docs/reports/DOC-002-A-gemini.md` copied stale narrative text and is not reliable evidence.

---

## 5. Found but Not Changed

1. **Remaining occurrences from Step 3 grep:**
   Running `grep -n -i 'all 10 files\|without exception\|unanimously' docs/context/data-formats.md docs/context/complete-context.md` after editing yields:
   ```text
   docs/context/data-formats.md:64:- **Format:** **All 10 files are semicolon-delimited (`;`)**, matching DSA. None are space-delimited.
   docs/context/data-formats.md:66:- **Concept Name Extension Quirk (CRITICAL):** in all 10 files, every concept name has a `.txt` filename suffix attached (e.g. `hash_table.txt;asymptotic_complexity.txt;0`). Loaders must strip `.txt` from node names when parsing.
   ```
   Both of these hits are factual and verified (all 10 example files are indeed semicolon-delimited and all 10 have the `.txt` extension on concept names); per prompt instructions, they were left unchanged. Zero hits exist in `docs/context/complete-context.md`.

2. **Task ID DOC-006 and Decision ID [D-69]:**
   The prompt was titled `DOC-005` with `[D-68]`. Luke noted: "another doc-005 named task is running so use another id." Task ID was renumbered to `DOC-006` for the worktree (`...-DOC-006`), branch (`task/DOC-006`), status row (`DOC-006`), and report (`DOC-006-gemini.md`). `DOC-005` landed on `master` at commit `52e05c6` claiming `[D-68]`. With Luke's authorization, our decision entry was renumbered to `[D-69]`.

---

## 6. Worktree State

`git status --short` confirms only the 3 modified documents and the untracked report:

```bash
$ git status --short
 M docs/context/data-formats.md
 M docs/decisions/decision-log.md
 M docs/tasks/status.md
?? docs/reports/DOC-006-gemini.md
```
