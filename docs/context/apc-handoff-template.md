# APC-to-APC Handoff Template

Use this template when an APC AI session is ending (credit limit reached, or
any other reason) and a new APC AI instance needs to pick up the work. The
new instance will have NO memory of this conversation — this document, plus
the repo files it points to, is the entire transfer.

**Fill in every section below.** A handoff that skips a section because
"nothing happened there" should still say so explicitly — an empty section
left blank is ambiguous between "nothing happened" and "forgot to fill it
in."

---

## 1. Orientation (always the same — copy verbatim unless the repo structure changed)

You are the APC AI ("Analyzer, Planner, Controller") for a CS undergraduate
thesis project. You have NO filesystem access to the project repo. You
coordinate by writing standalone prompts that the human (Luke) relays to
local coding agents (Claude Code, Gemini, opencode) running on his machine,
who DO have filesystem access and report back to you (via Luke pasting their
reports, or you reading pasted report content).

Read, in this order, before doing anything else:

1. `docs/context/complete-context.md` — full project orientation
2. `docs/context/data-formats.md` — settled + open data-format findings
3. `docs/decisions/decision-log.md` — every past decision and why
4. `docs/tasks/status.md` — what's actually done right now
5. This document's Sections 2–5 below — what changed in the ending session

If Luke has pasted the current content of any of these files into this
handoff already, use that pasted content rather than asking him to paste it
again — only ask for what's genuinely not already provided.

## 2. What changed this session

[Fill in: a plain-language summary of what was decided, built, discovered,
or corrected during the session that's ending. Not a transcript — a
summary. Reference specific decision-log entries or task IDs rather than
re-explaining them in full.]

## 3. What's currently in-flight (not yet finished, actively being worked)

[Fill in: any task that's `in-progress` or `blocked` in `tasks/status.md`,
with enough context that the new APC instance knows what's actually
happening with it beyond what the one-line status tracker shows. If
nothing is in-flight, say so explicitly.]

## 4. What the new APC instance should do first

[Fill in: a concrete, specific next step — not "continue the project" but
the actual next action. E.g., "Task DATA-001's standalone prompt has not
yet been written — write it and give it to Luke" or "Gemini's report on
INFRA-002 is pasted below; review it and decide whether the interface spec
needs revision before Luke starts Phase 2."]

## 5. Anything unresolved that doesn't fit the task tracker

[Fill in: open questions, judgment calls not yet made, anything flagged
with uncertainty that a future session should know about but that isn't
cleanly expressible as a task-status row. If genuinely nothing, say so.]

## 6. Pasted content (if any)

[If Luke is relaying agent reports, file contents, or anything else
alongside this handoff, it goes here — paste it directly rather than
summarizing, so the new APC instance has the primary material, not a
summary of a summary.]

---

**For Luke:** when you start a new APC session with this document, paste
this filled-in template as your first message, along with current contents
of `tasks/status.md` and `decision-log.md` if either has changed since this
document was written (file contents drift faster than this handoff doc
will be rewritten). The new APC instance should confirm it has read
everything and briefly restate where things stand before taking any new
action — if it doesn't, ask it to.
