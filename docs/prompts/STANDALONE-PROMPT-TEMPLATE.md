# Standalone Task Prompt Template

> **For Luke / APC AI:** When creating a prompt for a local coding agent, copy and populate this template. The prompt must be completely self-contained, assuming zero memory of past chat sessions.

---

```markdown
# TASK: [TASK-ID] — [Short Task Title]

## Role & Worktree Instructions
- **Assigned Agent:** [claude-code | gemini | opencode | cursor | any]
- **Task ID:** [TASK-ID]
- **Branch / Worktree:** If running concurrently with another agent or task, create and operate in a dedicated worktree:
  `git worktree add ../llm-graph-insertion-complexity-[TASK-ID] -b task/[TASK-ID]`
  (or run `./scripts/task-worktree.sh start [TASK-ID]`).

## Orientation & Required Reading
Before writing any code, inspect these repository files in order:
1. `docs/context/complete-context.md` — full project background and coordination rules
2. `docs/tasks/status.md` — confirm [TASK-ID] is marked `open` or `in-progress`
3. `docs/decisions/decision-log.md` — review past decisions ([D-01] through [latest])
4. [Relevant spec / interface files, e.g., `docs/context/data-formats.md`]

## Context & Objectives
[Explain the goal of this task, why it is needed now, and how it fits into the current phase. Mention relevant past decisions or prerequisite tasks.]

## Specific Scope & Deliverables
1. **Implementation Files:**
   - Modify / create: `path/to/file`
   - Specific requirements: [Details]
2. **Test Requirements:**
   - Modify / create: `tests/test_something.py`
   - Ensure comprehensive unit and edge-case coverage.
3. **What NOT to Touch:**
   - [Explicitly declare boundaries to prevent scope creep.]

## Verification & Acceptance Criteria
Your work is complete when:
- [ ] All tests pass via `pytest`.
- [ ] No regression or broken imports across the rest of the test suite.
- [ ] Direct assumptions have been verified against filesystem ground truth.

## Reserved Decision IDs
[If this task introduces a permanent architectural choice, allocate a reserved ID, e.g.:
- Reserved Decision ID: **[D-xx]**
- If none is needed, state: "None reserved. If a non-trivial choice is required, request reservation or report it."]

## Output & Reporting Instructions
Upon completing the work:
1. **Commit Your Changes:** Stage and commit all changes on your branch:
   `git commit -m "<type>([TASK-ID]): <description>"`
2. **Generate Patch File:** Export the unit-of-work diff into `patch/`:
   `mkdir -p patch && git diff HEAD~1 > patch/[TASK-ID]-[agent-name]-[short-slug].patch`
3. **Write Report File:** `docs/reports/[TASK-ID]-[agent-name]-[short-slug].md` following `docs/reports/TASK-TEMPLATE.md`.
4. **Update `docs/tasks/status.md`:** Change `[TASK-ID]` status to `needs-review` or `done`, linking your report.
5. **Log Decision (if reserved):** Append `[D-xx]` entry to `docs/decisions/decision-log.md`.
6. **Validate Your Report:** Run `./scripts/validate-report.py docs/reports/[TASK-ID]-[agent-name]-[short-slug].md --require-patch`.
7. **Generate Fresh Bundle (if needed):** Run `./scripts/apc-bundle.sh [profile]` if shared contracts/context were touched.
8. **Report Back to Luke:**
   - Provide an executive summary of what was accomplished and test results.
   - Reference the generated patch file in `patch/`.
   - Include the unified git diff (`git diff HEAD~1`).
   - State the branch name and worktree path. Do not merge or delete the worktree.
```
