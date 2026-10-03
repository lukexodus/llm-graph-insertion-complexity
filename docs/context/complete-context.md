# Complete Context — LLM Graph Insertion Complexity Thesis

**Read this file first, in full, before touching any code or data in this
repo.** This document assumes you (the reading agent) have no prior memory of
any conversation about this project — everything you need is either here or
linked from here.

## 1. What this project is

A fourth-year undergraduate Computer Science thesis (Philippines). The student
(Luke) is the thesis author and project lead. The full, formal thesis text
(Chapters 1–3 so far) lives at
`docs/thesis/An Empirical Complexity Analysis of Candidate-Narrowing
Strategies for Incremental LLM-Driven Graph Construction.md` — **that file is
the authoritative statement of the research question, objectives, scope, and
planned methodology. This document summarizes it for quick orientation; the
thesis file is the source of truth if the two ever disagree.**

**One-sentence summary:** the thesis empirically measures and compares the
cost (time, LLM API calls) and accuracy of four different strategies for
inserting a new concept-node into an already-existing, LLM-constructed
knowledge graph, as the existing graph's size grows from ~29 nodes to
~2000 nodes — testing whether a specific published theoretical complexity
bound (EraRAG's Theorem 4) actually holds in practice.

**Why this matters (the actual research gap, briefly):** published systems
for LLM-driven incremental knowledge graph construction (iText2KG, DIAL-KG,
SAC-KG, EraRAG, and others) each propose their own method for deciding where
a new node connects to an existing graph, but (a) none of them measures
insertion cost as an explicit function of how large the existing graph
already is — they report aggregate cost figures instead — and (b) none of
them compares more than one narrowing strategy head-to-head under identical
conditions. This thesis fills both gaps. Full literature trail, with every
source's specific contribution, is in `docs/rrl/catalogue.md`.

## 2. The four strategies being compared (the actual thing being built)

1. **Brute-force comparison** — LLM compares the new node against every
   single existing node. No filtering. This is the control/baseline;
   expected to scale badly, by design — that's the point of including it.
2. **Embedding-similarity thresholding** — compute cosine similarity between
   the new node's embedding and every existing node's embedding; only nodes
   above a fixed threshold (~0.6, per iText2KG's published value) get passed
   to the LLM for a final decision.
3. **Approximate nearest-neighbor (ANN) retrieval** — use an ANN index
   (FAISS or similar) to retrieve the top-k most similar existing nodes in
   sub-linear time, then LLM decides among those k.
4. **Bounded-bucket partitioning** — existing nodes live in size-capped
   buckets; inserting a node only ever touches one bucket (split/merge logic
   when a bucket overflows/underflows), inspired by EraRAG's architecture
   but adapted to concept-node insertion rather than EraRAG's own
   text-chunk-summarization task (these are NOT the same underlying
   operation — see the thesis Chapter 3, Section 3.2.5, for why this
   distinction matters and must be stated explicitly in any writeup).

All four strategies share one final step: once a shortlist of candidates is
produced (by whichever method), an LLM call determines the actual
relationship between the new node and each shortlisted candidate. This final
step is held IDENTICAL across all four strategies on purpose — it's what
makes the comparison fair. Only the narrowing/shortlisting mechanism differs
between strategies.

## 3. What gets measured

For every (strategy, graph-size) combination, across repeated insertion
trials:

- **Wall-clock time** per insertion
- **LLM API call count** per insertion (deliberately separate from time — it
  disentangles "the LLM is slow" from "the algorithm makes too many calls")
- **Placement accuracy** (precision/recall) — ONLY where gold-standard
  ground truth exists (see Section 4 below); not measurable on synthetic data

## 4. Data sources — READ `docs/context/data-formats.md` BEFORE WRITING ANY LOADER CODE

The evaluation dataset `cemaytekin/EKG-Dataset` lives at
`repositories/dataset/EKG-Dataset/` inside this repo (nested git clone from
the authors of the ACE paper; see catalogue entry #9). It contains the
gold-standard graphs this thesis reuses for accuracy evaluation.

**Do not assume you know these files' formats from their names alone.**
`docs/context/data-formats.md` documents everything known about every file
in this dataset. All file formats, delimiters, node counts, and edge
semantics have been independently and exhaustively verified in tasks
**DATA-001** and **DATA-002** (see `docs/reports/DATA-001-gemini-verify-file-formats.md`
and `docs/reports/DATA-002-gemini-mekg-directionality.md` for full details).

In brief (full detail in `data-formats.md`):

- `DSA_gold_standard_MEKG.txt` — 29-node graph, semicolon-delimited triples
  `concept1;concept2;label`. Directionality: `label = 1` means `concept2` is a
  prerequisite of `concept1` (`concept1 requires concept2`; [D-15]).
- `metacademy_gold_standard_MEKG.txt` — 141-node graph, SPACE-delimited
  triples `concept1 concept2 label`. Directionality: same as DSA (`concept2`
  is prerequisite of `concept1`; [D-15]). Different delimiter than DSA — do not
  assume one parser handles both files.
- Ten `MEKG_with*nodes*.txt` example files (6 to 35 nodes) — confirmed
  semicolon-delimited; all node names carry a `.txt` filename suffix ([D-16]);
  directionality is REVERSED from gold standards: `concept1.txt;concept2.txt;1`
  means `concept1` is a prerequisite of `concept2` ([D-19]).
- Ten `*.csv` files (`0-100.csv` to `900-1000.csv`) — CONFIRMED to be unrelated
  crowdsourced A-B-test data (10 files, not four), NOT graph data of any size.
  Do not use these for the size sweep.
- `concept_descriptions/` folder — inspected and confirmed unusable for
  DSA/Metacademy: contains 152 elementary math texts matching the CSV files,
  with 0% overlap with DSA or Metacademy ([D-17]). Where build-phase source text
  will come from remains an open question (see `docs/tasks/status.md` and
  `docs/decisions/decision-log.md` for current state).

## 5. Project structure and where things live

```
.
├── AGENTS.md                         (operational rules for all local agents)
├── repositories/
│   └── dataset/
│       └── EKG-Dataset/              (nested clone of cemaytekin/EKG-Dataset)
└── docs/
    ├── context/                      ← you are here; standalone context for agents
    │   ├── complete-context.md       (this file)
    │   ├── data-formats.md           (settled data-format findings)
    │   └── apc-handoff-template.md   (template for APC-to-APC session handoffs)
    ├── decisions/
    │   └── decision-log.md           (append-only; WHY past decisions were made)
    ├── reports/                      (one file per completed agent task)
    ├── rrl/
    │   └── catalogue.md              (full literature trail, every source's contribution)
    ├── tasks/
    │   ├── high-level-tasks.md       (the static Phase 0–4 project plan)
    │   └── status.md                 (live status; what's actually done right now)
    └── thesis/
        └── An Empirical Complexity Analysis...md   (the actual thesis text, Ch. 1–3)
```

**Reading order recommendation for a new agent or new APC instance:** this
file → `data-formats.md` → `decision-log.md` → `tasks/status.md` → only then
the full thesis text or catalogue if deeper detail is needed. The thesis and
catalogue are long; the ToC-generation skill should be used to find the
specific section needed rather than reading either end-to-end by default.

## 6. The coordination model (why this document exists at all)

This project is run by a human (Luke) relaying work between:

- **The APC AI** ("Analyzer, Planner, Controller") — an AI assistant with NO
  filesystem access to this repo. It reasons about the thesis, plans tasks,
  and writes STANDALONE PROMPTS that Luke manually copies to local agents.
  It has no memory between sessions beyond what is written in this repo —
  due to API credit limits, the APC role will be handed off between
  different AI instances over the project's lifetime. See
  `apc-handoff-template.md` for how that handoff is done.
- **Local coding agents** (Claude Code, Gemini, opencode, run on Luke's own
  machine) — these DO have full filesystem access to this repo and are
  the ones that actually write and run code against the real data files.

**The critical implication:** nothing is "remembered" by any single AI
across sessions. Everything that needs to survive must be written into this
repo — the decision log, the task-status file, the per-task report files.
**If you are a local agent completing a task, you MUST write a report file**
at `docs/reports/<task-id>-<agent-name>-<short-slug>.md` describing what you
did, what you found, and anything the APC AI or a future agent needs to know
— per the convention in `AGENTS.md`. An undocumented change is, for the
purposes of this project, equivalent to a change that never happened, because
no future session will know to look for it.

**This repo — not the APC AI, not any chat transcript — is the sole source
of truth.** The APC AI has no filesystem access and no memory beyond what's
written here; anything it says that conflicts with the repo's actual current
state is simply stale, not authoritative. When the APC AI produces an edit
to an existing file, it should be relayed as a delta (diff or before/after
excerpt), not a full-file paste — the same rule `AGENTS.md` sets for local
agents reporting back, now applied symmetrically in the other direction, so
that reviewing any change (by a human, by a local agent, by a future APC
instance) means reading only what moved, not re-diffing a wall of unchanged
text by eye.  

## 7. Open items — things that are genuinely unresolved right now

- **Active/Open task status**: See `docs/tasks/status.md` for live task states
  (DATA-001 and DATA-002 are complete).
- **Graph representation choice**: not yet locked. Default lean (not yet
  confirmed as a decision) is NetworkX, given Python, small data size, and
  built-in directed-graph support — but this has not been formally decided
  per the decision-log convention and should be before Phase 1's interface
  spec is finalized.
- **Reference [8]** in the thesis reference list is an open citation slot
  (see decision-log D-11) — unrelated to the coding work, but worth knowing
  about if any agent is asked to touch the thesis document itself.
- **Citation style** (IEEE, per D-09) is a working default pending adviser
  confirmation — again, only relevant if the thesis document itself is being
  edited, not for code/data work.
