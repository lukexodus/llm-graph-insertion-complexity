# DOC-004-C Report: Land the Amended Gated Thesis Diff

Date: 2026-10-15 13:38 PH (UTC+8)  
Task ID: `DOC-004-C`  
Branch: `task/DOC-004-C` (worktree `../llm-graph-insertion-complexity-DOC-004-C`)  
Decision ID: `D-77` (renumbered from D-76 per Luke's instruction after collision with INFRA-011)  

---

## 1. Identity

- **Real Agent Name:** Gemini / Antigravity
- **Exact Model Label:** `Gemini 3.8 Flash (Medium)`
- **Session / Conversation ID:** `512aecca-d185-438b-b8e7-d6dba3b507fb`
- **Date / Time:** 2026-10-15 13:38 PH (UTC+8)

---

## 2. Preconditions

Raw command outputs from Section 2 checks:

```bash
git status --short                      # expect empty in the new worktree
git log --oneline -5
T="docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
git hash-object "$T"                    # expect 7ba3c035e86006aae82918d0d37aa8925f69f2da (core landed by DOC-004-B)
sha256sum "$T"                          # expect 66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705
git hash-object docs/tasks/high-level-tasks.md   # expect a59843b89ef6fb5de9991a0a1bf77d825c741b4f
grep -o '\*\*\[D-[0-9]*\]\*\*' docs/decisions/decision-log.md | sort -t- -k2 -n -u | tail -3
                                        # renumbered to D-77 (D-76 held by INFRA-011)
ls docs/reports | grep -c 'DOC-004-C'   # expect 0
grep -c 'DOC-004-C' docs/tasks/status.md # expect 0
grep -c '^| DOC-004-B ' docs/tasks/status.md   # expect 1
```

```text
0b5198a (HEAD -> task/DOC-004-C, master) docs: sync repo-tree.txt for INFRA-010 and DOC-004-B
2a32c21 (task/DOC-004-B) DOC-004-B: land amended core thesis diff and record D-75
1591d52 INFRA-010 (B): record torch, faiss-cpu and sentence-transformers versions in manifest libraries (D-74)
a6c9fed (origin/master, origin/HEAD) INFRA-010 (A): record FAISS/PyTorch import-order finding (D-73), correct report claims
442ca1f INFRA-009-A: wiring tests through main(), both-order FAISS test, executed mutation table
7ba3c035e86006aae82918d0d37aa8925f69f2da
66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
a59843b89ef6fb5de9991a0a1bf77d825c741b4f
**[D-73]**
**[D-74]**
**[D-75]**
0
0
1
```

---

## 3. Hashes

### Raw Outputs

#### Input Files in `~/Downloads` (Section 1)
```text
8ee54b82d8a0ca7a1940e7b851a873d61a5ef9aabf305d0e1a88ce4f77fcbeba  /home/lukexodus/Downloads/DOC-004-C-thesis-gated-amended.diff
41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f  /home/lukexodus/Downloads/D-76-entry.md
fb88059c1fa70792f21cd8fbd89be9f892908fff5892a2aee936dbf907d59c77  /home/lukexodus/Downloads/DOC-004-C-apply-line81.py
```

*Note on `D-76-entry.md`: The input file was supplied as `/home/lukexodus/Downloads/D-76-entry.md` and hashed before renumbering to `[D-77]`.


#### Copied Diff in `docs/reports/` (Step 1)
```text
8ee54b82d8a0ca7a1940e7b851a873d61a5ef9aabf305d0e1a88ce4f77fcbeba  docs/reports/DOC-004-C-thesis-gated-amended.diff
```

#### Amended Gated Diff Application (Step 2)
```text
(No warnings emitted; command exited 0)
```

#### Thesis Post-Apply Verification (Step 2)
```text
8b1b95fff514fee7fec398da145171bb13529bca
fcb489a7e01a6bf1c45ff36567602a531bec922c5712f56b4f17c20c7b68040c  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
72439
303
0
4
3	3	docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
```

#### D-77 Log Append Check (Step 3)
```text
7	0	docs/decisions/decision-log.md
1
41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f  -
```

#### Line 81 Replacement Script Check (Step 4)
```text
replacing line 81
122784eab7aef45c3b23b197d91053be6b05d8d8
1	1	docs/tasks/high-level-tasks.md
```

#### Status Table Edit Check (Step 5)
```text
1	0	docs/tasks/status.md
```

### Expected vs Observed Verification Table

| Item / Metric | Expected | Observed | Match? |
| :--- | :--- | :--- | :--- |
| `DOC-004-C-thesis-gated-amended.diff` sha256 | `8ee54b82d8a0ca7a1940e7b851a873d61a5ef9aabf305d0e1a88ce4f77fcbeba` | `8ee54b82d8a0ca7a1940e7b851a873d61a5ef9aabf305d0e1a88ce4f77fcbeba` | YES |
| `D-76-entry.md` sha256 (prior to D-77 renumbering) | `41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f` | `41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f` | YES |
| `DOC-004-C-apply-line81.py` sha256 | `fb88059c1fa70792f21cd8fbd89be9f892908fff5892a2aee936dbf907d59c77` | `fb88059c1fa70792f21cd8fbd89be9f892908fff5892a2aee936dbf907d59c77` | YES |
| Precondition thesis `git hash-object` | `7ba3c035e86006aae82918d0d37aa8925f69f2da` | `7ba3c035e86006aae82918d0d37aa8925f69f2da` | YES |
| Precondition thesis sha256 | `66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705` | `66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705` | YES |
| Precondition `high-level-tasks.md` hash | `a59843b89ef6fb5de9991a0a1bf77d825c741b4f` | `a59843b89ef6fb5de9991a0a1bf77d825c741b4f` | YES |
| Precondition latest decision ID | `D-75` | `D-75` | YES |
| Post-gated thesis `git hash-object` | `8b1b95fff514fee7fec398da145171bb13529bca` | `8b1b95fff514fee7fec398da145171bb13529bca` | YES |
| Post-gated thesis sha256 | `fcb489a7e01a6bf1c45ff36567602a531bec922c5712f56b4f17c20c7b68040c` | `fcb489a7e01a6bf1c45ff36567602a531bec922c5712f56b4f17c20c7b68040c` | YES |
| Post-gated thesis byte count (`wc -c`) | 72439 | 72439 | YES |
| Post-gated thesis line count (`wc -l`) | 303 | 303 | YES |
| Post-gated inline `[D-` count | 0 | 0 | YES |
| Post-gated unescaped `$` count | 4 (all escaped dollar amounts unchanged) | 4 | YES |
| Post-gated thesis `git diff --numstat` | 3 added, 3 removed | 3 added, 3 removed | YES |
| `decision-log.md` added/removed lines | 7 added, 0 removed | 7 added, 0 removed | YES |
| `decision-log.md` D-77 entry count | 1 | 1 | YES |
| `decision-log.md` tail 6 lines sha256 | `41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f` | `41802a20e081a121293b8e0efd73a66a40537f7bdbaa3c3a0c951acda689113f` | YES |
| Post-replace `high-level-tasks.md` hash | `122784eab7aef45c3b23b197d91053be6b05d8d8` | `122784eab7aef45c3b23b197d91053be6b05d8d8` | YES |
| `high-level-tasks.md` `git diff --numstat` | 1 added, 1 removed | 1 added, 1 removed | YES |
| `status.md` `git diff --numstat` | 1 added, 0 removed | 1 added, 0 removed | YES |

---

## 4. Files Changed

Raw outputs of `git status --short` and `git diff --stat` (with `git add -N` on untracked files in worktree):

```text
 M docs/decisions/decision-log.md
 A docs/reports/DOC-004-C-gemini-thesis-gated-landing.md
 A docs/reports/DOC-004-C-thesis-gated-amended.diff
 M docs/tasks/high-level-tasks.md
 M docs/tasks/status.md
 M "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
```

```text
 docs/decisions/decision-log.md                     |   7 +
 .../DOC-004-C-gemini-thesis-gated-landing.md       | 220 +++++++++++++++++++++
 docs/reports/DOC-004-C-thesis-gated-amended.diff   |  25 +++
 docs/tasks/high-level-tasks.md                     |   2 +-
 docs/tasks/status.md                               |   1 +
 ...or Incremental LLM-Driven Graph Construction.md |   6 +-
 6 files changed, 257 insertions(+), 4 deletions(-)
```

---

## 5. status.md, decision-log and high-level-tasks diffs

Raw output of `git diff -- docs/tasks/status.md docs/decisions/decision-log.md docs/tasks/high-level-tasks.md`:

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 582f3c7..e58b388 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -624,3 +624,10 @@ Reasoning: enforces uniform single-threaded CPU embedding inference across Strat
 (6) Clarification of [D-62](3), without editing it: "mean segment size approximately 7" is an a-priori expectation from the bounds [5, 10], not a measured value; the thesis states only that a shortlist cannot exceed s_max and that realised counts are measured by the runs.
 Reasoning: removes the contradiction between the research question and the single-insertion protocol fixed by [D-68](1), removes statements with no source or no measurement (the kind [D-70](1) withdrew for Strategy 2), and keeps literature-dependent claims out of the thesis until the paper has been read. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/reports/DOC-004-B-thesis-final-core.diff`, `docs/reports/DOC-004-B-thesis-final-gated.diff`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, RQ4 (Section 1.2), Objective 4 (Section 1.3).
 
+**[D-77]** EraRAG Theorem 4 checked against the paper; gated thesis diff amended and landed; DATA-002 positive-edge total corrected; stale Phase 4 task line replaced (DOC-004-C):
+(1) Theorem 4 check (APC-A, 2026-10-15, from the full text of arXiv:2506.20963v2 dated 4 Jul 2025; Luke has not checked it independently, and the thesis reference [4] names no version, so an earlier version may differ [Unverified]): Theorem 4 states T_update(Delta) = O(Delta (nd + S_LLM)), where n is the number of stored hyperplanes, d the embedding dimension and S_LLM the cost of one LLM summarisation, under the assumption 1 < S_min <= S_max = O(1). |C|, the number of chunks already stored, is defined in the theorem but does not appear in the bound. The paper uses n for the hyperplane count in Algorithm 1 and Theorems 2 and 4, but k in its notation table and hash definition. The theorem statement does not use the word amortized; the proof invokes amortization in one sentence, and Theorem 2 uses "amortised" for the LLM summarisation time. The proof treats the layer depth as a constant. The thesis keeps "amortized" (the proof's wording supports it); the last two points are not changed in the thesis and are left for Luke and the adviser.
+(2) The condition in [D-75](4) is met: Theorem 4 uses n for the hyperplane count, so the rename n -> b stands. Two wording changes are made to the held gated diff: (a) S_LLM is described as the cost of one LLM summarisation call; the DOC-004-B gated diff said "the cost of the language-model operations triggered by the update", which is broader than the paper's definition; (b) the Section 2.2.4 statement that every dynamic-insertion experiment holds the pre-existing corpus at a fixed proportion is restricted to cost experiments, because the paper's Exp-3 varies the initial graph from 0% to 100% of the corpus and reports final accuracy and recall, not update cost; the statement that no reported experiment tests cost against pre-existing graph size is unchanged. The amended diff is `docs/reports/DOC-004-C-thesis-gated-amended.diff`; it applies to the thesis as landed by DOC-004-B (blob `7ba3c035e86006aae82918d0d37aa8925f69f2da`) and gives blob `8b1b95fff514fee7fec398da145171bb13529bca` (sha256 `fcb489a7e01a6bf1c45ff36567602a531bec922c5712f56b4f17c20c7b68040c`). It supersedes `docs/reports/DOC-004-B-thesis-final-gated.diff`, which is not edited and must not be applied. Luke reviews the thesis diff before committing.
+(3) Correction by later entry, as in [D-69](4), because the DATA-002 report is write-once: the report's positive-edge total of 577 (lines 24 and 57 of `docs/reports/DATA-002-gemini-mekg-directionality.md`) is an arithmetic error; the per-file counts 7 + 16 + 18 + 23 + 15 + 29 + 19 + 76 + 138 + 244 sum to 585. The overlap total of 425 and the reversed total of 171 ([D-69](4)) are unaffected. No other file in the APC bundle at commit `442ca1f` cites 577.
+(4) `docs/tasks/high-level-tasks.md`, Phase 4: the line promising a direct comparison of the empirical curve against Theorem 4's predicted shape is replaced with wording consistent with [D-68](1) and [D-75](3)(a): the single-insertion cost curve is compared against the structural premise of the bound, and no amortised benchmark is run. This closes the item flagged in [D-68](6)(d).
+Reasoning: records the paper check that [D-75](4) required before the gated diff, keeps the thesis's description of Theorem 4 within what the paper states, and corrects two stale statements by later entry or task-line edit rather than by editing committed reports or log entries. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/reports/DOC-004-C-thesis-gated-amended.diff`, `docs/tasks/high-level-tasks.md`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`.
diff --git i/docs/tasks/high-level-tasks.md w/docs/tasks/high-level-tasks.md
index a59843b..122784e 100644
--- i/docs/tasks/high-level-tasks.md
+++ w/docs/tasks/high-level-tasks.md
@@ -78,7 +78,7 @@ This is where the four independently-built strategies get run together, for real
 
 - Plot insertion cost (wall-clock and call count separately — the handoff's own point that separating these tells you "LLM is slow" from "algorithm makes too many calls") against n, one line per strategy, log-scale n.
 - Plot placement accuracy against n, same structure.
-- **Directly compare the bucket-capped strategy's empirical curve against EraRAG's Theorem 4's predicted shape** — this is the actual thesis contribution landing: does the measured curve look like what the theorem promises, or does it diverge, and either answer is a real finding.
+- **Compare the bucket-capped strategy's single-insertion cost curve against the structural premise of EraRAG's Theorem 4** — each sweep trial is one insertion after the graph is built, with no multi-insertion or amortised-cost benchmark ([D-68](1), [D-75](3)(a)), so the amortised bound itself is not tested; the question is whether the measured cost stays flat as the graph grows or diverges, and either answer is a real finding.
 - Write the results section around whichever outcome actually occurred (convergence or divergence across strategies), using the framing already locked in Phase 0 so the writeup isn't scrambling to justify results after the fact.
 
 ---
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index d6553c6..a781508 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -104,6 +104,7 @@ Status: **not started** (blocked on Phase 3)
 | DOC-004 | Thesis sync after strategy track: proposed edits only (Strategy D parameters and adaptation wording; Theorem 4 symbol resolution n -> b and S_LLM scope; Strategy C index parameters, efSearch {64, 256}, and synthetic recall evidence; fallback rewording and candidate citations for M=16, efConstruction=200; theta=0.6 calibration limitation). Report and unified diff only; thesis unmodified. | **needs-review** | Completed by Gemini. See report [`docs/reports/DOC-004-gemini-thesis-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-sync.md) and diff [`docs/reports/DOC-004-gemini-thesis-proposed.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-proposed.diff). Superseded by DOC-004-A; the DOC-004 diff must not be applied. |
 | DOC-004-A | Amend the DOC-004 thesis-sync proposal (core repo-backed diff and gated literature-dependent diff; plain-text maths; un-amortised single-step limitation per [D-68]; parameter and bounds sync per [D-64], [D-70]). Report and replacement unified diffs only; thesis unmodified. | **done** | Completed by Gemini. See report [`docs/reports/DOC-004-A-gemini-thesis-sync-amend.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-sync-amend.md), core diff [`docs/reports/DOC-004-A-gemini-thesis-core.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-core.diff), and gated diff [`docs/reports/DOC-004-A-gemini-thesis-gated.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-gated.diff). Accepted by APC-A with amendments ([D-75]); the amended diffs are in DOC-004-B. The gated diff is stored and not applied; it waits for Luke's check of EraRAG Theorem 4. |
 | DOC-004-B | Land the amended DOC-004-A core thesis diff (RQ4 and Objective 4 reworded, single-insertion limitation, Strategy B/C/D parameter text, single-threaded embedding sentence) and record [D-75]; gated diff stored, not applied. | **needs-review** | Completed by Gemini; see report [`docs/reports/DOC-004-B-gemini-thesis-landing.md`](docs/reports/DOC-004-B-gemini-thesis-landing.md). |
+| DOC-004-C | Land the amended gated thesis diff (EraRAG Theorem 4: n renamed b, S_LLM wording, checked against arXiv:2506.20963v2), record [D-77] including the DATA-002 positive-edge total correction, and replace the stale Phase 4 line in `docs/tasks/high-level-tasks.md`. | **needs-review** | Completed by Gemini; see report [`docs/reports/DOC-004-C-gemini-thesis-gated-landing.md`](docs/reports/DOC-004-C-gemini-thesis-gated-landing.md). |
 | DOC-005 | Record the run-plan decisions (D-68), add the run plan to the README, verify the planned-call bounds offline. | **done** | Completed by Gemini. See report [`docs/reports/DOC-005-gemini-run-plan.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-gemini-run-plan.md). Report contains errors; see DOC-005-A (D-70, originally reserved as D-69); the committed D-68 and README run-plan section are authoritative. |
 | DOC-005-A | Erratum for the DOC-005 report, correct Strategy 2 bound wording ([D-70]), and raw re-verification of the planned-call bounds. | **done** | Completed by Gemini; see report [`docs/reports/DOC-005-A-gemini-erratum.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-A-gemini-erratum.md). |
 | DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-006-gemini.md). |
```

---

## 6. Found But Not Changed

none (Gemini)

---

## 7. What I Did Not Do

- `docs/reports/DOC-004-B-thesis-final-gated.diff` was not applied or edited (superseded by `DOC-004-C-thesis-gated-amended.diff`).
- `docs/reports/DATA-002-gemini-mekg-directionality.md` was not edited (write-once report; correction recorded via [D-77](3)).
- No thesis text, decision text, or task text written by hand (applied strictly via `git apply` and script from APC-provided artifacts).
- No live calls made; no keys read; no experiments run.
- Changes left uncommitted and unstaged in worktree `llm-graph-insertion-complexity-DOC-004-C`.
- The `DOC-006` status row was not touched.
