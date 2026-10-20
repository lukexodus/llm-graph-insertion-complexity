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
      python3 "$TARGET_DIR/scripts/validate-report.py" "$report_file" --repo-root "$TARGET_DIR" || echo "  [WARNING] Report validation returned issues."
    fi
  else
    echo "  [WARNING] No report file found in docs/reports/ matching $task_id"
  fi
  echo "=========================================="
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
