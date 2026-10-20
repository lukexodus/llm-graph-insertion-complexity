# Task Report: [TASK-ID] — [Short Task Title]

**Date:** [YYYY-MM-DD]  
**Agent:** [claude-code | gemini | opencode | cursor | other]  
**Task ID:** [TASK-ID]  
**Status:** [done | needs-review | blocked]  
**Commit:** [git commit hash / message]  
**Patch File:** `patch/[TASK-ID]-[agent-name]-[short-slug].patch`  

---

## 1. Executive Summary

[Provide a concise 1-2 paragraph overview of what was requested, what was implemented or verified, key decisions made, and test outcomes.]

---

## 2. Implementation Details

### 2.1 Changes Made
[Detail files created or modified and the structural rationale for each change.]

- `path/to/file1`: [Description of change]
- `path/to/file2`: [Description of change]

### 2.2 Conformance to Specifications & Decisions
[Explain how this work adheres to the interface contracts and past decision-log entries (e.g., [D-xx]).]

---

## 3. Verification & Test Evidence

### 3.1 Test Execution
Command executed:
```bash
pytest path/to/tests
```

**Results:**
- Tests passed: [N]
- Tests failed: [0]
- Tests skipped: [N]

[Paste relevant excerpt of test output showing clean execution.]

### 3.2 Edge Cases & Negative Testing
[Document edge cases evaluated or mutation tests executed.]

---

## 4. Decisions Recorded

[If a reserved Decision ID was assigned to this task, state the entry added to `docs/decisions/decision-log.md`:]

- **[D-xx]**: [Summary of decision and why]

---

## 5. Unified Git Diff

[Include the verbatim unified diff of changes made, with index lines. Run `git diff` inside the worktree.]

```diff
[PASTE git diff OUTPUT HERE]
```

---

## 6. Flagged for APC / Operator Attention

[Explicitly list any discrepancies found, open questions, recommended follow-up tasks, or decisions requiring human/APC confirmation.]
- [ ] [Item 1]
- [ ] [Item 2]
