#!/usr/bin/env bash
# task-worktree.sh — Helper script to enforce AGENTS.md worktree rules for parallel tasks.
# Run from repository root.

set -euo pipefail

REPO_ROOT="$(pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"

show_help() {
  cat <<'EOF'
Usage: ./scripts/task-worktree.sh <COMMAND> [TASK_ID]

Commands:
  start <TASK-ID>   Create a dedicated task worktree at ../<repo>-<TASK-ID> on branch task/<TASK-ID>
  list              List all active worktrees and their current branch
  status <TASK-ID>  Check git status inside the specified task worktree
  diff <TASK-ID>    Output clean unified diff from the worktree with index lines
  handoff <TASK-ID> Validate the worktree state for operator review/commit (does not delete)
  merge <TASK-ID>   Safely audit, merge task/<TASK-ID> into current branch, and clean up worktree
  remove <TASK-ID>  Safely remove a worktree (only after operator has merged/committed)
EOF
}

cmd="${1:-}"
task_id="${2:-}"

if [[ -z "$cmd" || "$cmd" == "-h" || "$cmd" == "--help" ]]; then
  show_help
  exit 0
fi

case "$cmd" in
list)
  echo "Active Git Worktrees:"
  git worktree list
  exit 0
  ;;

start)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID. Example: ./scripts/task-worktree.sh start CORE-001" >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  BRANCH_NAME="task/${task_id}"

  if [[ -d "$TARGET_DIR" ]]; then
    echo "ERROR: Worktree directory '$TARGET_DIR' already exists." >&2
    exit 1
  fi

  echo "Creating dedicated worktree for task $task_id..."
  git worktree add "$TARGET_DIR" -b "$BRANCH_NAME"
  echo "Worktree successfully created at: $TARGET_DIR"
  echo "Branch: $BRANCH_NAME"
  echo "Switch to the worktree directory before starting your local agent."
  ;;

status)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID." >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: Worktree '$TARGET_DIR' does not exist." >&2
    exit 1
  fi
  (cd "$TARGET_DIR" && git status --short)
  ;;

diff)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID." >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: Worktree '$TARGET_DIR' does not exist." >&2
    exit 1
  fi
  (cd "$TARGET_DIR" && git diff)
  ;;

handoff)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID." >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: Worktree '$TARGET_DIR' does not exist." >&2
    exit 1
  fi
  echo "=========================================="
  echo "Worktree Handoff Audit for: $task_id"
  echo "Directory: $TARGET_DIR"
  echo "Branch:    task/$task_id"
  echo "Git Status & Commit Check:"
  dirty_count=$(cd "$TARGET_DIR" && git status --porcelain | wc -l)
  if [[ "$dirty_count" -eq 0 ]]; then
    echo "  [OK] Working tree clean (changes are committed)"
    latest_commit=$(cd "$TARGET_DIR" && git log -1 --oneline)
    echo "  Latest commit: $latest_commit"
  else
    echo "  [WARNING] Worktree has $dirty_count uncommitted change(s). Please commit your work."
  fi
  echo ""
  echo "Patch File Check (in patch/):"
  patch_file=$(find "$TARGET_DIR/patch" -name "${task_id}*.patch" 2>/dev/null | head -n 1)
  if [[ -n "$patch_file" ]]; then
    echo "  [OK] Found patch file: $patch_file"
  else
    echo "  [WARNING] No patch file found in patch/ matching ${task_id}*.patch"
  fi
  echo ""
  echo "Report Check:"
  report_file=$(find "$TARGET_DIR/docs/reports" -name "${task_id}*" 2>/dev/null | head -n 1)
  if [[ -n "$report_file" ]]; then
    echo "  [OK] Found report file: $report_file"
    if [[ -f "$TARGET_DIR/scripts/validate-report.py" ]]; then
      echo "  Running report validator..."
      PYTHON_BIN="python3"
      if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
      fi
      "$PYTHON_BIN" "$TARGET_DIR/scripts/validate-report.py" "$report_file" --repo-root "$TARGET_DIR" || echo "  [WARNING] Report validation returned issues."
    fi
  else
    echo "  [WARNING] No report file found in docs/reports/ matching $task_id"
  fi
  echo "=========================================="
  ;;

merge)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID. Example: ./scripts/task-worktree.sh merge CORE-001" >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  BRANCH_NAME="task/${task_id}"

  # 1. Verify executed from main checkout
  if [[ ! -d ".git" ]]; then
    echo "ERROR: Run merge command from the main repository checkout, not from inside a worktree." >&2
    exit 1
  fi

  # 2. Check if main checkout has uncommitted tracked changes
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: Main working tree has uncommitted tracked changes." >&2
    echo "Please commit or stash changes in the main checkout before merging." >&2
    exit 1
  fi

  CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

  # 3. Check if target branch exists
  if ! git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "ERROR: Branch '$BRANCH_NAME' does not exist." >&2
    exit 1
  fi

  # 4. Check if worktree directory exists and is clean
  if [[ -d "$TARGET_DIR" ]]; then
    worktree_dirty=$(cd "$TARGET_DIR" && git status --porcelain | wc -l)
    if [[ "$worktree_dirty" -gt 0 ]]; then
      echo "ERROR: Worktree '$TARGET_DIR' has $worktree_dirty uncommitted change(s)." >&2
      echo "All changes must be committed in the worktree before merging." >&2
      exit 1
    fi
  fi

  # 5. Run handoff audit check
  echo "Running pre-merge audit..."
  "$0" handoff "$task_id"

  echo ""
  echo "Merging '$BRANCH_NAME' into '$CURRENT_BRANCH'..."
  if ! git merge --no-edit "$BRANCH_NAME"; then
    echo "ERROR: Merge conflict encountered. Resolve conflicts in main checkout or run 'git merge --abort'." >&2
    exit 1
  fi

  echo "Merge completed successfully."

  # 6. Clean up worktree if it exists
  if [[ -d "$TARGET_DIR" ]]; then
    echo "Cleaning up worktree at $TARGET_DIR..."
    git worktree remove "$TARGET_DIR"
    echo "Worktree removed."
  fi

  # 7. Delete task branch
  if git branch -d "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "Branch '$BRANCH_NAME' deleted."
  else
    echo "Note: Branch '$BRANCH_NAME' retained."
  fi

  echo ""
  echo "Task $task_id successfully merged into $CURRENT_BRANCH and worktree cleaned up."
  ;;

remove)
  if [[ -z "$task_id" ]]; then
    echo "ERROR: Missing TASK_ID." >&2
    exit 1
  fi
  TARGET_DIR="../${REPO_NAME}-${task_id}"
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: Worktree '$TARGET_DIR' does not exist." >&2
    exit 1
  fi
  echo "Removing worktree $TARGET_DIR..."
  git worktree remove "$TARGET_DIR"
  echo "Worktree removed. Note: the branch 'task/$task_id' is preserved until explicitly deleted."
  ;;

*)
  echo "ERROR: Unknown command '$cmd'" >&2
  show_help
  exit 1
  ;;
esac
