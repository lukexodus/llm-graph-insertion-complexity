# AGENTS.md

You are a local coding agent (Claude Code, Gemini, or opencode) working on
this repository. **Before doing anything else, read
`docs/context/complete-context.md` in full.** It explains what this project
is, how work is coordinated, and where everything lives. This file covers
only the operational rules for working in this specific repo.

## The one rule that matters most

**You have no memory across sessions. Neither does the AI planning your
tasks (the "APC AI" — see `complete-context.md` Section 6).** Anything you
learn, decide, or build that isn't written into this repo's files is lost
the moment this session ends. Write it down. When in doubt, write it down
anyway — a redundant note costs almost nothing; a lost finding costs a
future agent having to re-derive it from scratch, or worse, silently redoing
work already done.

**This repo is the sole source of truth, always — never the APC AI, never
any chat transcript, never any AI's stated memory of a past conversation.**
The APC AI has no filesystem access and no persistent memory across its own
sessions; if something it says ever conflicts with what's actually in a
repo file, the repo file is correct and the APC AI's statement is stale.
This applies to you too: if a task prompt or a piece of relayed context
seems to assume something about this repo that you can check directly (you
have filesystem access; the APC AI does not), check it, and say so in your
report if it was wrong — don't silently defer to a prompt's assumption over
what you can see yourself.

## Reporting changes efficiently — send deltas, not full files

**When you edit or add to a file that already exists in the repo (shared
docs like `decision-log.md`, `data-formats.md`, `status.md`, or anything
else), relay your change back to Luke/the APC AI as a diff or a clear
before/after excerpt of just the changed part — not the full resulting
file.** A full-file paste forces whoever's reading it to hunt for what
actually changed, which defeats the purpose of writing efficient,
scannable reports. A standard unified diff (`git diff` output) is the
easiest format for this — if you're working in a git-tracked checkout, just
include the relevant diff output in your report rather than re-typing the
change.

**Exceptions, where a full file genuinely is the right thing to send:**
- You created a brand-new file (there's no "before" to diff against).
- The change is a near-total rewrite where a diff would be longer and
  harder to read than the whole file.
- You're asked explicitly for full content.

If you're ever unsure which applies, default to the diff — it's easy for
the reader to ask for more context, but hard to un-paste a wall of
mostly-unchanged text.

## Before starting any task

1. Read `docs/context/complete-context.md` if you haven't already this
   session.
2. Check `docs/tasks/status.md` for the current state of all tasks — don't
   start work that's already marked done or in-progress by someone else.
3. If your task touches data files, read `docs/context/data-formats.md`
   first. It documents what's already known (and what's still unverified)
   about every data file in this repo. Don't re-derive a format from
   scratch if it's already documented there — and don't trust an
   unverified claim in that file as settled fact either; check what its
   verification status actually says.
4. Check `docs/decisions/decision-log.md` for any past decision relevant to
   your task. If you're about to make a choice that decision log doesn't
   cover (e.g., picking a graph library, picking a threshold value), make
   the choice, then add an entry to the decision log yourself before you
   finish — don't leave it for someone else to infer from your code.

## While working

- If a prompt or task description seems to assume something about a file's
  format or content that you can verify directly (you have filesystem
  access; the APC AI does not), **verify it** before proceeding, and report
  the result even if it confirms the assumption was correct. Silence reads
  as "nobody checked," not as "it was fine."
- If you find something that contradicts what's written in
  `data-formats.md`, `decision-log.md`, or the thesis text itself, do not
  silently work around it. Note the discrepancy clearly in your report.
  These documents are the project's shared memory; an uncorrected error in
  them will mislead every future agent and APC session that reads them.

## After finishing any task

**Write a report file.** This is not optional, even for a task that found
nothing noteworthy — "nothing noteworthy" is itself useful information to a
future session that might otherwise re-check the same thing.

- **Location:** `docs/reports/<task-id>-<agent-name>-<short-slug>.md`
  - `<task-id>` matches the ID in `docs/tasks/status.md` (e.g., `DATA-001`)
  - `<agent-name>` is whichever of `claude-code`, `gemini`, `opencode` you are
  - `<short-slug>` is a few words, hyphenated, describing the task
  - Example: `docs/reports/DATA-001-claude-code-verify-file-formats.md`
- **Never append to another agent's report file or to a shared log.** One
  file per completed task, written once by the agent that did it. If you
  revisit a task later, write a new report file rather than editing an old
  one, and reference the earlier one by filename.
- **What to include:** what you were asked to do, what you actually did,
  what you found (including anything that contradicted an existing
  assumption), and anything explicitly flagged for the APC AI's attention
  or a future agent's attention.
- **Update `docs/tasks/status.md`** to reflect your task's new status
  (done / blocked / needs-followup) as part of finishing — don't leave the
  tracker stale.
- **If you made a non-trivial decision** (chose a library, chose a
  threshold, chose a data format to standardize on) that isn't already in
  `docs/decisions/decision-log.md`, add an entry. Keep it to the same
  format as existing entries: decision, one-line reasoning, what it
  affects.

## Recommended (not mandatory) agent-role split

This is a recommendation from the APC AI based on what each agent seems
best suited for here, not a hard rule — Luke may reassign as needed:

- **Claude Code** — first-draft implementation of the core infrastructure:
  the strategy interface, the graph representation, the corpus loader, the
  measurement harness, the four strategy modules themselves.
- **Gemini** — independent review and verification specifically because it
  is a different model lineage than the APC AI. Best used for checking
  work the APC AI specified (e.g., "does this loader's actual output match
  what's really in the raw file", "review this interface spec for
  ambiguity before four strategies get built against it") rather than for
  first-draft implementation — the value here is a genuinely independent
  second look, not a faster first pass.
- **opencode** — role not yet assigned; insufficient information about its
  configuration to recommend one. Default to using it wherever makes
  sense until a clearer pattern emerges, and consider noting what it
  turns out to be good at in the decision log once that's known.

## Standalone prompts

You may receive a task as a "standalone prompt" written by the APC AI and
relayed by Luke. These prompts are written assuming you have zero memory of
any prior conversation — treat them as fully self-contained, and expect
them to point you to specific files in this repo (especially
`complete-context.md`, `data-formats.md`, and `decision-log.md`) rather
than re-explaining everything inline. If a prompt seems to assume context
you don't have and can't find in this repo, say so in your report rather
than guessing.
