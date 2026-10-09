# Task Report: DOC-003 Parallel-Work Rule for AGENTS.md

**Date:** 2026-10-09  
**Agent:** Gemini (reporting under requested task artifact name `DOC-003-claude-code-agents-worktree-rule.md`)  
**Task ID:** DOC-003  

---

## 1. What Changed

### 1.1 `## Before starting any task` (Lines 73–93)
- Added rule `0`: `"0. If you will run alongside another task, follow 'Parallel work and worktrees' first."`
- Added rule `5`: Awareness note regarding `scripts/apc-bundle.sh --discover` and `scripts/README.md`.

### 1.2 `## Parallel work and worktrees` (Lines 95–106)
- Inserted a new top-level section immediately after `## Before starting any task` and before `## While working`.
- Total length: 12 lines (well under the 40-line ceiling).
- Formatted as 9 imperative rules (1–9) covering pre-flight checks, dedicated worktree creation, shared doc editing rules, decision ID reservations, verbatim diff generation, completion handoffs, protected state operations, shared `.git` directory safety, and pre-live run clean worktree checks.

---

## 2. Git Diff Outputs

### 2.1 Unified Diff (`git diff AGENTS.md`)

```diff
diff --git i/AGENTS.md w/AGENTS.md
index 9d26816..bc40a6c 100644
--- i/AGENTS.md
+++ w/AGENTS.md
@@ -72,6 +72,7 @@ mostly-unchanged text.
 
 ## Before starting any task
 
+0. If you will run alongside another task, follow 'Parallel work and worktrees' first.
 1. Read `docs/context/complete-context.md` if you haven't already this
    session.
 2. Check `docs/tasks/status.md` for the current state of all tasks — don't
@@ -87,6 +88,21 @@ mostly-unchanged text.
    cover (e.g., picking a graph library, picking a threshold value), make
    the choice, then add an entry to the decision log yourself before you
    finish — don't leave it for someone else to infer from your code.
+5. Use `scripts/apc-bundle.sh --discover` if you need to find which files
+   define core symbols (`Shortlist`, `ConceptGraph`, `MeteredEmbedder`,
+   etc.). See `scripts/README.md` for bundle profiles and usage.
+
+## Parallel work and worktrees
+
+1. **Check status:** Run `git worktree list` and `git status --short`. If another task is in progress in this checkout, or the working tree is dirty with files you did not create, do not start in the main checkout.
+2. **Dedicated task worktrees:** Any task that runs at the same time as another task must use its own worktree: `git worktree add ../<repo-name>-<TASK-ID> -b task/<TASK-ID>` from the main checkout. Use the task ID exactly as in `docs/tasks/status.md`. Do not reuse a worktree across tasks.
+3. **Shared doc editing:** Only one agent may edit a given shared doc (`docs/tasks/status.md`, `docs/decisions/decision-log.md`, `AGENTS.md`, `docs/context/*.md`) at a time. In a worktree, edit only your own rows and your own appended decision entries, and re-read the file immediately before writing (see "Before editing a shared doc").
+4. **Reserved decision IDs:** Decision IDs are reserved per task by the APC, not chosen by the agent. If a reserved ID is already used in the file, stop and report the conflict; do not renumber.
+5. **Verbatim diffs:** Diffs pasted into a report must come from `git diff` run in the worktree that made the change, and must include the index lines. Never retype a diff (see "Reporting changes efficiently").
+6. **Handoff upon completion:** When the task is finished: do not merge, rebase, or delete the worktree yourself. Leave the branch and worktree for Luke, and state the branch name and the worktree path in the report.
+7. **Protected operations:** Never run `git worktree remove`, `git clean`, `git reset --hard`, `git checkout --` or `git stash` in a worktree you did not create in this session, or in the main checkout without Luke's instruction.
+8. **Shared `.git` safety:** Worktrees share the `.git` directory. Never commit a file that exists only in a worktree's untracked state without listing it in the report.
+9. **Clean live runs:** Before any live API run, check `git worktree list` and confirm that the run uses a clean worktree at the commit the report names.
 
 ## While working
 
```

### 2.2 Diff Stat (`git diff --stat AGENTS.md`)

```
 AGENTS.md | 16 ++++++++++++++++
 1 file changed, 16 insertions(+)
```

---

## 3. Grep Output (`grep -n "worktree" AGENTS.md`)

```
75:0. If you will run alongside another task, follow 'Parallel work and worktrees' first.
95:## Parallel work and worktrees
97:1. **Check status:** Run `git worktree list` and `git status --short`. If another task is in progress in this checkout, or the working tree is dirty with files you did not create, do not start in the main checkout.
98:2. **Dedicated task worktrees:** Any task that runs at the same time as another task must use its own worktree: `git worktree add ../<repo-name>-<TASK-ID> -b task/<TASK-ID>` from the main checkout. Use the task ID exactly as in `docs/tasks/status.md`. Do not reuse a worktree across tasks.
99:3. **Shared doc editing:** Only one agent may edit a given shared doc (`docs/tasks/status.md`, `docs/decisions/decision-log.md`, `AGENTS.md`, `docs/context/*.md`) at a time. In a worktree, edit only your own rows and your own appended decision entries, and re-read the file immediately before writing (see "Before editing a shared doc").
101:5. **Verbatim diffs:** Diffs pasted into a report must come from `git diff` run in the worktree that made the change, and must include the index lines. Never retype a diff (see "Reporting changes efficiently").
102:6. **Handoff upon completion:** When the task is finished: do not merge, rebase, or delete the worktree yourself. Leave the branch and worktree for Luke, and state the branch name and the worktree path in the report.
103:7. **Protected operations:** Never run `git worktree remove`, `git clean`, `git reset --hard`, `git checkout --` or `git stash` in a worktree you did not create in this session, or in the main checkout without Luke's instruction.
104:8. **Shared `.git` safety:** Worktrees share the `.git` directory. Never commit a file that exists only in a worktree's untracked state without listing it in the report.
105:9. **Clean live runs:** Before any live API run, check `git worktree list` and confirm that the run uses a clean worktree at the commit the report names.
```

---

## 4. Found But Not Changed

Under Section `## Reporting changes efficiently — send deltas, not full files` in `AGENTS.md`:
- **Line 60 (formerly 59):**
  > `"A standard unified diff (`git diff` output) is the easiest format for this — if you're working in a git-tracked checkout, just include the relevant diff output in your report rather than re-typing the change."`

This mentions a git-tracked checkout and is compatible with worktrees (each worktree being its own git-tracked checkout); per instruction 5, it was left unedited.

---

## 5. Verification Notes Against the Repository

1. **Git Version & Worktree CLI Support:**
   - Git version on host is `git version 2.55.0`.
   - Command syntax `git worktree add <path> -b <branch>` was verified via isolated test execution: git accepts `-b <branch>` both before and after `<path>`.
2. **Repository Name:**
   - Evaluated `basename "$(git rev-parse --show-toplevel)"`: `llm-graph-insertion-complexity`.
   - Worktree path template `../llm-graph-insertion-complexity-<TASK-ID>` correctly places sibling directories alongside the main checkout.
3. **Default Branch:**
   - `git worktree list` reports `/home/lukexodus/projects/llm-graph-insertion-complexity 130f950 [master]`. The primary branch is `master`, not `main`.
4. **State of Working Copy:**
   - Per instructions, `AGENTS.md` and this report file are left unstaged and uncommitted.
