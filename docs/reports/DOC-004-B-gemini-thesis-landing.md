# DOC-004-B Report: Land the Amended Thesis-Sync Diff

Date: 2026-10-15 12:26 PH (UTC+8)  
Task ID: `DOC-004-B`  
Branch: `task/DOC-004-B` (worktree `../llm-graph-insertion-complexity-DOC-004-B`)  
Decision ID: `D-75` (pre-assigned as D-73, renumbered to D-75 due to master INFRA-010)  

---

## 1. Identity

- **Real Agent Name:** Gemini / Antigravity
- **Exact Model Label:** `Gemini 3.8 Flash (Medium)`
- **Session / Conversation ID:** `512aecca-d185-438b-b8e7-d6dba3b507fb`
- **Date / Time:** 2026-10-15 12:26 PH (UTC+8)

---

## 2. Preconditions

Raw command outputs from Section 2 checks:

```bash
git status --short                      # expect empty in the new worktree
git log --oneline -5
T="docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
git hash-object "$T"                    # expect c13d749de3af4da36fc9d1df6ec96a0ab9a1d827
sha256sum "$T"                          # expect 15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a
grep -o '\*\*\[D-[0-9]*\]\*\*' docs/decisions/decision-log.md | sort -t- -k2 -n -u | tail -3
                                        # expect the last one to be D-72 (or lower); STOP if D-73 or higher already exists
ls docs/reports | grep -c 'DOC-004-B'   # expect 0
grep -c 'DOC-004-B' docs/tasks/status.md # expect 0
```

```text
12fd304 (HEAD -> task/DOC-004-B, origin/master, origin/HEAD, master) docs: sync repo-tree.txt for INFRA-008 and INFRA-009
577584c INFRA-009: pin PyTorch CPU threads to 1 for all embedding strategies (D-72)
2eb367b INFRA-008: record OpenMP thread-check outcome, effect material (D-71)
517c169 DOC-004-A: amend DOC-004 thesis-sync proposal with core and gated diffs
43e3225 docs: sync repo-tree.txt with root patch directory
c13d749de3af4da36fc9d1df6ec96a0ab9a1d827
15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
**[D-70]**
**[D-71]**
**[D-72]**
0
0
```

---

## 3. Hashes

### Raw Outputs

#### Input Files in `~/Downloads` (Section 1)
```text
c41b300e92e1b1424a521776ffd44fd37e6fddf59ede136232adeac3c0ea97b2  /home/lukexodus/Downloads/DOC-004-B-thesis-final-core.diff
851105302c65ad64ed800138eb7b569e0891d52638379da1d7698eccc2d14ab3  /home/lukexodus/Downloads/DOC-004-B-thesis-final-gated.diff
7de4cc7ad07c2b89d927fd7c2d56e99babd75ca1d23dd19916b120c6f1a2c20c  /home/lukexodus/Downloads/D-73-entry.md
```

#### Copied Diffs in `docs/reports/` (Step 1)
```text
c41b300e92e1b1424a521776ffd44fd37e6fddf59ede136232adeac3c0ea97b2  docs/reports/DOC-004-B-thesis-final-core.diff
851105302c65ad64ed800138eb7b569e0891d52638379da1d7698eccc2d14ab3  docs/reports/DOC-004-B-thesis-final-gated.diff
```

#### Core Diff Application (Step 2)
```text
docs/reports/DOC-004-B-thesis-final-core.diff:19: trailing whitespace.
4. To analyze whether the cost of a single insertion under a bucket-capped strategy remains flat as the graph grows, consistent with the structural premise of the amortized bound in \[4\]; the single-insertion protocol does not test amortization itself.  
warning: 1 line adds whitespace errors.
```

#### Thesis Post-Apply Verification (Step 3)
```text
7ba3c035e86006aae82918d0d37aa8925f69f2da
66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705  docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
71869
303
0
4
18	12	docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
```

#### Gated Diff Scratch Dry-Run (Step 4)
```text
c96730e655cf04e65529122d4780f34b5595c3190d8273d5b211d21158340399  /tmp/doc004b/docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md
```

#### D-75 Log Append Check (Step 5)
```text
9	0	docs/decisions/decision-log.md
1
```

#### Status Table Edit Check (Step 6)
```text
2	1	docs/tasks/status.md
```

### Expected vs Observed Verification Table

| Item / Metric | Expected | Observed | Match? |
| :--- | :--- | :--- | :--- |
| `DOC-004-B-thesis-final-core.diff` sha256 | `c41b300e92e1b1424a521776ffd44fd37e6fddf59ede136232adeac3c0ea97b2` | `c41b300e92e1b1424a521776ffd44fd37e6fddf59ede136232adeac3c0ea97b2` | YES |
| `DOC-004-B-thesis-final-gated.diff` sha256 | `851105302c65ad64ed800138eb7b569e0891d52638379da1d7698eccc2d14ab3` | `851105302c65ad64ed800138eb7b569e0891d52638379da1d7698eccc2d14ab3` | YES |
| `D-73-entry.md` sha256 | `7de4cc7ad07c2b89d927fd7c2d56e99babd75ca1d23dd19916b120c6f1a2c20c` | `7de4cc7ad07c2b89d927fd7c2d56e99babd75ca1d23dd19916b120c6f1a2c20c` | YES |
| Precondition thesis `git hash-object` | `c13d749de3af4da36fc9d1df6ec96a0ab9a1d827` | `c13d749de3af4da36fc9d1df6ec96a0ab9a1d827` | YES |
| Precondition thesis sha256 | `15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a` | `15ae6059cb8d86076bbd187d4cfd19c88029d475038ce698132eab326b3e279a` | YES |
| Precondition latest decision ID | `D-72` | `D-72` | YES |
| Post-core thesis `git hash-object` | `7ba3c035e86006aae82918d0d37aa8925f69f2da` | `7ba3c035e86006aae82918d0d37aa8925f69f2da` | YES |
| Post-core thesis sha256 | `66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705` | `66c50724c071b12d09cd5a3148a8a682d888a7cc2810d73bb142d4d754b30705` | YES |
| Post-core thesis byte count (`wc -c`) | 71869 | 71869 | YES |
| Post-core thesis line count (`wc -l`) | 303 | 303 | YES |
| Post-core inline `[D-` count | 0 | 0 | YES |
| Post-core unescaped `$` count | 4 (all escaped dollar amounts unchanged) | 4 | YES |
| Post-core thesis `git diff --numstat` | 18 added, 12 removed | 18 added, 12 removed | YES |
| Gated dry-run scratch sha256 | `c96730e655cf04e65529122d4780f34b5595c3190d8273d5b211d21158340399` | `c96730e655cf04e65529122d4780f34b5595c3190d8273d5b211d21158340399` | YES |
| `decision-log.md` removed lines | 0 | 0 | YES |
| `decision-log.md` D-75 entry count | 1 | 1 | YES |
| `status.md` `git diff --numstat` | 2 added, 1 removed | 2 added, 1 removed | YES |

---

## 4. Files Changed

Raw outputs of `git status --short` and `git diff --stat` (with `git add -N` on untracked files in worktree):

```text
 M docs/decisions/decision-log.md
 A docs/reports/DOC-004-B-gemini-thesis-landing.md
 A docs/reports/DOC-004-B-thesis-final-core.diff
 A docs/reports/DOC-004-B-thesis-final-gated.diff
 M docs/tasks/status.md
 M "docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md"
```

```text
 docs/decisions/decision-log.md                     |   9 +
 docs/reports/DOC-004-B-gemini-thesis-landing.md    | 202 +++++++++++++++++++++
 docs/reports/DOC-004-B-thesis-final-core.diff      | 101 +++++++++++
 docs/reports/DOC-004-B-thesis-final-gated.diff     |  25 +++
 docs/tasks/status.md                               |   3 +-
 ...or Incremental LLM-Driven Graph Construction.md |  30 +--
 6 files changed, 357 insertions(+), 13 deletions(-)
```

---

## 5. status.md and decision-log diffs

Raw output of `git diff -- docs/tasks/status.md docs/decisions/decision-log.md`:

```diff
diff --git i/docs/decisions/decision-log.md w/docs/decisions/decision-log.md
index 925c2e9..582f3c7 100644
--- i/docs/decisions/decision-log.md
+++ w/docs/decisions/decision-log.md
@@ -587,3 +587,12 @@ Reasoning: records the empirical benchmark measurements and triggers the pre-fix
 (5) Snippet re-run status: The diagnostic OpenMP benchmark snippet from [D-68](5) does not need to be re-run; [D-71] stands as the definitive empirical record.
 Reasoning: enforces uniform single-threaded CPU embedding inference across Strategies 2, 3, and 4, eliminating cross-strategy latency confounds from shared OpenMP runtime thread settings. Affects: `src/graph_insertion/cpu_threads.py`, `scripts/run_experiment.py`, `scripts/README.md`, `tests/test_cpu_threads.py`, `tests/test_run_experiment_cli.py`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, `docs/reports/INFRA-009-gemini-cpu-thread-pinning.md`, RUN-001.
 
+**[D-73]** DOC-004-A accepted with amendments; thesis wording for RQ4, the single-insertion protocol, Strategy B/C/D parameters and single-threaded embedding (DOC-004-B):
+(1) Disposition: the DOC-004 proposed diff is superseded and must not be applied. DOC-004-A is accepted with the amendments in (2); the amended diffs are `docs/reports/DOC-004-B-thesis-final-core.diff` (applies to thesis blob `c13d749de3af4da36fc9d1df6ec96a0ab9a1d827`) and `docs/reports/DOC-004-B-thesis-final-gated.diff` (applies only after the core diff). DOC-004-B lands the core diff; the gated diff is stored and not applied (see (4)).
+(2) Amendments to DOC-004-A found at APC-A review: (a) the undersize-segment neighbour rule is lexicographic over (Hamming distance at the touching endpoints, Gray-rank gap, neighbour size, side), so neighbour size only breaks ties (`bounded_bucket.py` `_choose_neighbour`); DOC-004-A had it as "smaller neighbour wins on size"; (b) `update_s` is a timing component of `total_s`, LLM calls are counted per candidate in the decision step, so "call count of `update_s`" was wrong and Chapter 2 now describes the protocol in prose; (c) the claim that lower overlap with the exact top-10 is "an expected structural consequence" had no source (D-35(5) is the Strategy 2 threshold clause and D-62(4) lists two limitations, not three); it is replaced by a statement that `exact_topk_overlap` is recorded as a diagnostic; (d) the efSearch calibration is described as benchmarks on randomly generated vectors, not the study's evaluation data ([D-55](2)), and the clustered-vector recall is stated as at least 0.999 in every setting (STRAT-003-A section 6); (e) the bare asterisk in `b*d` rendered as italics under CommonMark and is written `bd`, matching the thesis's juxtaposed `nd`. Thesis text keeps no inline decision IDs and no `$` maths.
+(3) Decisions relayed from Luke on 2026-10-15 (Luke reviews the thesis diff before committing): (a) RQ4 (Section 1.2) and Objective 4 (Section 1.3) are reworded to ask whether the cost of a single insertion under a bucket-capped strategy stays flat as the graph grows, as the structural premise of the amortized bound in [4] predicts; related sentences in Sections 1.5, 1.7, 2.2.4, 3.2.5 and 3.5 and the "To Future Researchers" sentence are brought into line, with one limitation sentence in Section 1.5 stating that every strategy's sweep is a single-insertion measurement and does not test amortization ([D-68](1)); this changes the wording of a research question and awaits adviser comment; (b) no inline decision IDs in the thesis; (c) the Strategy 2 grid theta in {0.4, 0.5, 0.6} stays as planned in [D-64](4) and [D-68](2) and the absence of a stricter value is stated as a limitation; no theta = 0.7 run is added; (d) HNSW parameters M = 16 and efConstruction = 200 are stated as fixed a priori without citations to support them; (e) the decision-step micro-benchmark question stays open for the adviser ([D-68](1)).
+(4) Held for Luke: the gated diff renames EraRAG's hyperplane count from n to b and describes S_LLM; both depend on Theorem 4 of arXiv:2506.20963, which is not in the repository and which no APC or agent has read. Luke checks the notation and the meaning of S_LLM in the paper before the gated diff is applied. If Theorem 4 does not use n for the hyperplane count, the gated diff is not applied and the thesis keeps its current notation. The iText2KG claim that theta = 0.6 was fitted with a different embedding model is not in either diff.
+(5) Single-threaded embedding ([D-72](3)): Section 3.2.3 states that PyTorch is restricted to one thread for every embedding-based strategy. This sentence stands only if INFRA-009 is accepted; if it is rejected or changed, the sentence is corrected by a later entry.
+(6) Clarification of [D-62](3), without editing it: "mean segment size approximately 7" is an a-priori expectation from the bounds [5, 10], not a measured value; the thesis states only that a shortlist cannot exceed s_max and that realised counts are measured by the runs.
+Reasoning: removes the contradiction between the research question and the single-insertion protocol fixed by [D-68](1), removes statements with no source or no measurement (the kind [D-70](1) withdrew for Strategy 2), and keeps literature-dependent claims out of the thesis until the paper has been read. Affects: `docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing Strategies for Incremental LLM-Driven Graph Construction.md`, `docs/reports/DOC-004-B-thesis-final-core.diff`, `docs/reports/DOC-004-B-thesis-final-gated.diff`, `docs/decisions/decision-log.md`, `docs/tasks/status.md`, RQ4 (Section 1.2), Objective 4 (Section 1.3).
diff --git i/docs/tasks/status.md w/docs/tasks/status.md
index ab583eb..8ead8ba 100644
--- i/docs/tasks/status.md
+++ w/docs/tasks/status.md
@@ -101,7 +101,8 @@ Status: **not started** (blocked on Phase 3)
 | TOOL-001 | APC bundle script rework: relocate to `scripts/apc-bundle.sh`, support `--list <profile>` with byte counts and human sizes, add `--discover` symbol discovery, add test count reporting, add thesis size check (>300 KB), add comprehensive documentation in `scripts/README.md`. | **done** | Completed by Gemini. See report [`docs/reports/TOOL-001-claude-code-apc-bundle.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/TOOL-001-claude-code-apc-bundle.md). |
 | DOC-003 | Parallel-work and worktree rules in `AGENTS.md`: add dedicated section with 9 imperative rules for concurrent task execution, worktree isolation, shared doc editing etiquette, reserved decision IDs, and verbatim git diff reporting. | **done** | Completed by Gemini. See report [`docs/reports/DOC-003-claude-code-agents-worktree-rule.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-003-claude-code-agents-worktree-rule.md). |
 | DOC-004 | Thesis sync after strategy track: proposed edits only (Strategy D parameters and adaptation wording; Theorem 4 symbol resolution n -> b and S_LLM scope; Strategy C index parameters, efSearch {64, 256}, and synthetic recall evidence; fallback rewording and candidate citations for M=16, efConstruction=200; theta=0.6 calibration limitation). Report and unified diff only; thesis unmodified. | **needs-review** | Completed by Gemini. See report [`docs/reports/DOC-004-gemini-thesis-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-sync.md) and diff [`docs/reports/DOC-004-gemini-thesis-proposed.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-gemini-thesis-proposed.diff). Superseded by DOC-004-A; the DOC-004 diff must not be applied. |
-| DOC-004-A | Amend the DOC-004 thesis-sync proposal (core repo-backed diff and gated literature-dependent diff; plain-text maths; un-amortised single-step limitation per [D-68]; parameter and bounds sync per [D-64], [D-70]). Report and replacement unified diffs only; thesis unmodified. | **needs-review** | Completed by Gemini. See report [`docs/reports/DOC-004-A-gemini-thesis-sync-amend.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-sync-amend.md), core diff [`docs/reports/DOC-004-A-gemini-thesis-core.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-core.diff), and gated diff [`docs/reports/DOC-004-A-gemini-thesis-gated.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-gated.diff). |
+| DOC-004-A | Amend the DOC-004 thesis-sync proposal (core repo-backed diff and gated literature-dependent diff; plain-text maths; un-amortised single-step limitation per [D-68]; parameter and bounds sync per [D-64], [D-70]). Report and replacement unified diffs only; thesis unmodified. | **done** | Completed by Gemini. See report [`docs/reports/DOC-004-A-gemini-thesis-sync-amend.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-sync-amend.md), core diff [`docs/reports/DOC-004-A-gemini-thesis-core.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-core.diff), and gated diff [`docs/reports/DOC-004-A-gemini-thesis-gated.diff`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-004-A-gemini-thesis-gated.diff). Accepted by APC-A with amendments ([D-73]); the amended diffs are in DOC-004-B. The gated diff is stored and not applied; it waits for Luke's check of EraRAG Theorem 4. |
+| DOC-004-B | Land the amended DOC-004-A core thesis diff (RQ4 and Objective 4 reworded, single-insertion limitation, Strategy B/C/D parameter text, single-threaded embedding sentence) and record [D-73]; gated diff stored, not applied. | **needs-review** | Completed by Gemini; see report [`docs/reports/DOC-004-B-gemini-thesis-landing.md`](docs/reports/DOC-004-B-gemini-thesis-landing.md). |
 | DOC-005 | Record the run-plan decisions (D-68), add the run plan to the README, verify the planned-call bounds offline. | **done** | Completed by Gemini. See report [`docs/reports/DOC-005-gemini-run-plan.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-gemini-run-plan.md). Report contains errors; see DOC-005-A (D-70, originally reserved as D-69); the committed D-68 and README run-plan section are authoritative. |
 | DOC-005-A | Erratum for the DOC-005 report, correct Strategy 2 bound wording ([D-70]), and raw re-verification of the planned-call bounds. | **done** | Completed by Gemini; see report [`docs/reports/DOC-005-A-gemini-erratum.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-005-A-gemini-erratum.md). |
 | DOC-006 | Close DOC-002 with the DOC-002-B text; record [D-69] (D-33 hold-out clarification, confirmed data counts, corrections to D-19 and DATA-002); narrow the `data-formats.md` orientation sentence to the nine checkable files; fix the Phase 2 header; errata for the DOC-002-B, DOC-002-A and DATA-002 reports. | **needs-review** | Completed by Gemini; see [`docs/reports/DOC-006-gemini.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-006-gemini.md). |
```

---

## 6. Found But Not Changed

none (Gemini)

---

## 7. What I Did Not Do

- Gated diff not applied (`docs/reports/DOC-004-B-thesis-final-gated.diff` is stored for Luke's verification of EraRAG Theorem 4).
- No thesis text written or edited by hand; applied strictly via `git apply` from the APC-provided core diff.
- No live calls made; no keys read; no experiments run.
- Changes left uncommitted and unstaged in worktree `llm-graph-insertion-complexity-DOC-004-B`.
