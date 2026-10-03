# Task Status

Live tracker — what's actually done right now, not the plan (the plan is
`docs/tasks/high-level-tasks.md`, which describes Phases 0–4 and doesn't
change often). This file changes every time a task's state changes. A new
APC instance or agent should be able to read this file alone and know
exactly where the project stands, without reconstructing status from
scattered report files.

**Status values:** `open` (not started) · `in-progress` · `blocked` (name the
blocker) · `done` (link the report file)

---

## Phase 0 — Design Lock & Adviser Approval

Status: **done** (informally — the design is fully specified across the
thesis Chapters 1–3 and the decision log; no separate standalone design doc
was produced as a distinct artifact, but every element the high-level-tasks
plan asked this phase to contain exists somewhere in the repo).

## Phase 1 — Shared Infrastructure & Interface Contract

| ID        | Task                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Status   | Notes / Report                                                                                                                                                               |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DATA-001  | Independently re-verify every claim in `docs/context/data-formats.md` against the full raw files (not just head/tail excerpts). Specifically: confirm DSA and Metacademy delimiter/label conventions; check for delimiter-collision edge cases in both; inspect at least two of the ten example MEKG files (one small, one large) to confirm their format; inspect `concept_descriptions/` folder contents and assess sufficiency as build-phase source text. | **done** | Completed by Gemini. See report [`docs/reports/DATA-001-gemini-verify-file-formats.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-001-gemini-verify-file-formats.md). |
| DATA-002  | Resolve edge directionality convention for all ten example MEKG files (`MEKG_with*.txt`) relative to DSA/Metacademy ([D-15]).                                                                                                                                                                                                                                                                                                                               | **done** | Completed by Gemini. All 10 files confirmed reversed from D-15 (col1 = prerequisite, col2 = dependent). See report [`docs/reports/DATA-002-gemini-mekg-directionality.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-002-gemini-mekg-directionality.md). |
| DATA-003  | Decide where build-phase source text comes from now that `concept_descriptions/` is ruled out for DSA/Metacademy (D-17).                                                                                                                                                                                                                                                                                                                                     | **done** | Decided by Luke 2026-10-03: names only, no node text ([D-21]). Evidence in [`docs/reports/DATA-003-gemini-source-text-evidence.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DATA-003-gemini-source-text-evidence.md). |
| INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                                                         | **done** | Completed. Library locked as NetworkX via `ConceptGraph` wrapper ([D-22]); canonical edge direction locked as prereq -> dependent ([D-23]); dual-mapping implemented and verified without conflict against all 10 MEKG files. See report [`docs/reports/INFRA-001-claude-code-graph-representation.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/INFRA-001-claude-code-graph-representation.md). |
| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **open** | Unblocked: INFRA-001 is done. Strategies operate on `ConceptGraph`, ingest/emit bare concept names ([D-21]), and obtain embedding strings via `embed_text()`.                                                                                                                                                           |
| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **open** | Unblocked: INFRA-001 is done. Loader must construct `ConceptGraph` using `oriented_edge(source_kind, col1, col2)` per D-15, D-16, D-19, and D-23. Also populate `GoldJudgmentSet` for accuracy evaluation.                                                                                                              |
| INFRA-004 | Build the measurement harness (sweep runner: given a strategy module, run it across all graph-size checkpoints, log time/call-count/accuracy, emit one results row per strategy-size pair).                                                                                                                                                                                                                                                                   | **open** | Depends on INFRA-002. Can be scaffolded in parallel with INFRA-003 once INFRA-002 is locked, since the harness's shape depends on the interface, not the corpus's internals. |
| INFRA-005 | Build and run the trivial "null strategy" (e.g., attach new node to a random existing node) through the full harness, end-to-end, at all graph sizes.                                                                                                                                                                                                                                                                                                         | **open** | This is Phase 1's EXIT CRITERION — Phase 2 (the four real strategies) should not start until this passes cleanly. Depends on INFRA-001 through INFRA-004.                    |

## Phase 2 — Four Parallel Strategy Tracks

Status: **not started** (blocked on Phase 1's exit criterion, INFRA-005)

| ID        | Task                                       | Status | Notes                                                                          |
| --------- | ------------------------------------------ | ------ | ------------------------------------------------------------------------------ |
| STRAT-001 | Implement Strategy 1 (brute-force)         | open   | —                                                                              |
| STRAT-002 | Implement Strategy 2 (embedding-threshold) | open   | —                                                                              |
| STRAT-003 | Implement Strategy 3 (ANN retrieval)       | open   | —                                                                              |
| STRAT-004 | Implement Strategy 4 (bounded-bucket)      | open   | Most conceptually involved — recommend close review per `high-level-tasks.md`. |

## Phase 3 — Integration & Full Sweep

Status: **not started** (blocked on Phase 2)

## Phase 4 — Analysis & Writeup

Status: **not started** (blocked on Phase 3)

## Thesis document status (separate track from the code work above)

| Chapter                                           | Status                                                                                                                                                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Chapter 1 — Introduction                          | done, with flagged open items (see thesis text itself and decision-log D-11)                                                                                                                                        |
| Chapter 2 — Review of Related Literature          | done, with flagged open items (two sources need direct-read upgrade from search-snippet-only verification per earlier session notes)                                                                                |
| Chapter 3 — Methodology                           | done; data-sync corrections applied under DOC-001 (10 example MEKG files named in Section 3.3.2; Section 3.3.1 edge directionality synced per D-15 and D-19; see report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md)). Source-text question decided ([D-21]); Section 3.2.6 clarification and Scope and Limitations wording pending (DOC-002). |
| Chapter 4 — Results and Discussion                | not started (depends on Phase 3/4 code work)                                                                                                                                                                        |
| Chapter 5 — Summary, Conclusions, Recommendations | not started                                                                                                                                                                                                         |

## Housekeeping

| ID      | Task                                                                                                  | Status   | Notes / Report                                                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| DOC-001 | Sync stale shared docs and thesis text with verified data-file findings from DATA-001 and DATA-002.   | **done** | Completed by Gemini. See report [`docs/reports/DOC-001-gemini-doc-sync.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/DOC-001-gemini-doc-sync.md). |
| DOC-002 | Apply D-21 to thesis Chapter 3 (Section 3.2.6: prompts carry names plus a graph-level domain context string; Scope and Limitations: Strategies 2-4 embed bare names, accuracy rests on parametric knowledge). Also fix two stale lines: `complete-context.md` Section 4 still calls source text "an open question", and `data-formats.md` says "7 of the 10" filenames have underscores (it is 9 of 10). | **open** | Prompt not yet written; can wait until after INFRA-001. |
| FIX-001 | Follow-up fixes to INFRA-001: fix pyproject build-backend, expand cross-source test to Metacademy, add `judgment_for_edge` to `GoldJudgmentSet`, and enforce `.txt` suffix invariant on `ConceptGraph`. | **done** | Completed by Gemini. See report [`docs/reports/FIX-001-gemini-infra-001-followup.md`](file:///home/lukexodus/projects/llm-graph-insertion-complexity/docs/reports/FIX-001-gemini-infra-001-followup.md). |
