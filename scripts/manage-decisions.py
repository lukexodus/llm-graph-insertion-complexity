#!/usr/bin/env python3
"""manage-decisions.py — Helper to query, reserve, and validate decision IDs in docs/decisions/decision-log.md.

Prevents decision ID collisions when multiple agents or parallel worktrees operate concurrently.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_decision_log(log_path: Path):
    if not log_path.exists():
        return []
    content = log_path.read_text(encoding="utf-8")
    matches = re.findall(r"^\*\*\[D-(\d+)\]\*\*", content, re.MULTILINE)
    if not matches:
        # Fallback to general [D-xx] occurrences
        matches = re.findall(r"\[D-(\d+)\]", content)
    return sorted(list({int(m) for m in matches}))


def main():
    parser = argparse.ArgumentParser(description="Query and reserve decision IDs in docs/decisions/decision-log.md.")
    parser.add_argument("action", choices=["next", "list", "reserve", "check"], help="Action to perform")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--title", help="Decision title when reserving")
    parser.add_argument("--id", type=int, help="Decision ID to check")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    log_path = repo_root / "docs/decisions/decision-log.md"

    if not log_path.exists():
        print(f"ERROR: Decision log file '{log_path}' not found.", file=sys.stderr)
        sys.exit(1)

    existing_ids = parse_decision_log(log_path)
    highest_id = max(existing_ids) if existing_ids else 0

    if args.action == "list":
        print(f"Existing Decision IDs ({len(existing_ids)} total):")
        for did in existing_ids:
            print(f"  [D-{did:02d}]")
        print(f"\nHighest ID: [D-{highest_id:02d}]")

    elif args.action == "next":
        next_id = highest_id + 1
        print(f"Next available Decision ID: [D-{next_id:02d}]")

    elif args.action == "check":
        if args.id is None:
            print("ERROR: --id is required for 'check'", file=sys.stderr)
            sys.exit(1)
        if args.id in existing_ids:
            print(f"[D-{args.id:02d}] is ALREADY USED in decision-log.md.")
            sys.exit(1)
        else:
            print(f"[D-{args.id:02d}] is AVAILABLE.")
            sys.exit(0)

    elif args.action == "reserve":
        next_id = highest_id + 1
        title = args.title or "Reserved by APC for upcoming task"
        entry = (
            f"\n\n**[D-{next_id:02d}]** {title}\n"
            f"- **Date / Session:** In-Flight / Reserved\n"
            f"- **Decision:** Reserved\n"
            f"- **Reasoning:** In progress\n"
            f"- **Affects:** Pending task execution\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"Successfully reserved [D-{next_id:02d}]: '{title}' in {log_path.name}")


if __name__ == "__main__":
    main()
