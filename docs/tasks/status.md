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
| INFRA-001 | Lock the graph representation choice (library, in-memory shape) — currently only an unconfirmed lean toward NetworkX.                                                                                                                                                                                                                                                                                                                                         | **open** | Blocked-in-spirit on DATA-001's findings, since the gold-standard files' exact structure may affect what the representation needs to hold.                                   |
| INFRA-002 | Define and document the strategy interface contract (function signature, input/output shapes every one of the four strategy modules must implement).                                                                                                                                                                                                                                                                                                          | **open** | Depends on INFRA-001.                                                                                                                                                        |
| INFRA-003 | Build the corpus loader — normalizes DSA, Metacademy, and the ten example MEKG files into the INFRA-001 graph representation.                                                                                                                                                                                                                                                                                                                                 | **open** | Depends on DATA-001, INFRA-001.                                                                                                                                              |
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
| Chapter 3 — Methodology                           | done, with corrections needed per `data-formats.md` (example-MEKG filename/count correction, Metacademy "transitive edges" clarification) — **not yet applied to the actual thesis document file**, only identified |
| Chapter 4 — Results and Discussion                | not started (depends on Phase 3/4 code work)                                                                                                                                                                        |
| Chapter 5 — Summary, Conclusions, Recommendations | not started                                                                                                                                                                                                         |

**Open housekeeping item:** the corrections identified in
`docs/context/data-formats.md` (ten MEKG files not seven; Metacademy
clarification) have NOT yet been applied to the actual thesis `.md` file in
`docs/thesis/`. This should be done as a small, explicit edit task before
Chapter 3 is considered final.
