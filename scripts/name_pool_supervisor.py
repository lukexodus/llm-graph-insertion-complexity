#!/usr/bin/env python3
"""scripts/name_pool_supervisor.py — Thesis-side supervisor for sharded name-pool generation.

Launches N shard processes (scripts/generate_name_pool.py in --shard i/N mode) in
their own process groups, monitors shard caches, rotates a shard onto an unassigned
non-cooling spare profile on rate-limit (generator exit 3) or profile-in-use
(generator exit 7), writes <state-dir>/status.json atomically and appends lifecycle
events to <state-dir>/supervisor-log.jsonl, and runs --build-only --merge-run-ids
followed by --verify --merge-run-ids when all shards complete with exit 0.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
from typing import Any, IO, Optional

# Ensure src/ and repo root are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.generate_name_pool import (
    DEFAULT_TRACKED_OUTPUT,
    MAX_CALLS_DEFAULT,
    MIN_REQUIRED_NAMES_FOR_VALIDATION,
    TARGET_NAMES_DEFAULT,
    load_benchmark_corpus_concepts,
    load_completed_cache,
    validate_and_dedupe_candidates,
)

_GENERATOR_SCRIPT = Path(__file__).resolve().parent / "generate_name_pool.py"

# Generator exit codes (derived from scripts/generate_name_pool.py)
GEN_EXIT_OK = 0
GEN_EXIT_ERROR = 1
GEN_EXIT_USAGE = 2
GEN_EXIT_RATE_LIMIT = 3       # Adapter error 10 (rate_limit)
GEN_EXIT_LOGIN_REQUIRED = 4   # Adapter error 11 (login_required)
GEN_EXIT_MODEL_MISMATCH = 5   # Adapter error 14 (model_mismatch)
GEN_EXIT_CONSEC_FAILURES = 6  # 3 consecutive transient/parse failures (errors 1, 12, 13, parse)
GEN_EXIT_PROFILE_IN_USE = 7   # Adapter error 15 (profile_in_use)

# Supervisor exit codes
SUP_EXIT_OK = 0
SUP_EXIT_ERROR = 1
SUP_EXIT_USAGE = 2
SUP_EXIT_STALLED = 3
SUP_EXIT_MAX_TOTAL_CALLS = 4
SUP_EXIT_SIGNAL = 130

# Default supervisor timing and cap constants
DEFAULT_POLL_S = 30.0
DEFAULT_MAX_RESTARTS_PER_SHARD = 20
DEFAULT_PROFILE_COOLDOWN_S = 18000.0  # 5 hours (unverified operator assumption)
PROFILE_BUSY_COOLDOWN_S = 60.0        # 60 seconds on profile_in_use (generator exit 7)
DEFAULT_MAX_WAIT_S = 21600.0          # 6 hours
DEFAULT_MAX_TOTAL_CALLS = 600


@dataclass
class CoolingEntry:
    profile: str
    until_mono: float
    until_utc: str
    reason: str
    cooldown_s: float


@dataclass
class ShardState:
    shard_idx: int          # 1-based (1..N)
    shard_total: int        # N
    run_id: str             # <prefix>-s<i>of<N>
    cache_path: Path        # results/datagen/<run_id>/raw_responses.jsonl
    profile: Optional[str] = None
    proc: Optional[subprocess.Popen[bytes]] = None
    log_fh: Optional[IO[bytes]] = None
    pid: Optional[int] = None
    state: str = "pending"  # pending | running | waiting_for_profile | done | failed | stopped | stalled
    restarts: int = 0
    records: int = 0
    valid_names: int = 0
    last_exit_code: Optional[int] = None

    @property
    def shard_label(self) -> str:
        return f"{self.shard_idx}/{self.shard_total}"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_supervisor_log(state_dir: Path, event: str, **fields: Any) -> None:
    """Append a structured JSON event with UTC timestamp to <state-dir>/supervisor-log.jsonl."""
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "supervisor-log.jsonl"
    record: dict[str, Any] = {
        "timestamp_utc": _now_utc_iso(),
        "event": event,
    }
    record.update(fields)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def _write_status_atomic(state_dir: Path, payload: dict[str, Any]) -> None:
    """Atomically write <state-dir>/status.json via a temporary sibling file and os.replace."""
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path = state_dir / "status.json"
    tmp_path = state_dir / f".status.json.tmp.{os.getpid()}"
    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, status_path)


def build_shard_cli_tokens(
    *,
    shard_idx: int,
    shards: int,
    run_id_prefix: str,
    profile: str,
    command: Optional[str],
    adapter_model: str = "sonnet",
    adapter_effort: str = "low",
    adapter_thinking: str = "auto",
    adapter_timeout: int = 300,
    pause_s: float = 3.0,
    stagger_s: float = 20.0,
    max_calls: int = MAX_CALLS_DEFAULT,
    target_names: int = TARGET_NAMES_DEFAULT,
    lock_dir: Optional[Path] = None,
    for_display: bool = False,
    generator_script: Path = _GENERATOR_SCRIPT,
) -> list[str]:
    """Construct the CLI argument list for a single shard using the exact flag set
    of scripts/generate_name_pool.py --print-shard-commands (plus --lock-dir pass-through).
    """
    if for_display:
        tokens = ["python3", "scripts/generate_name_pool.py", "--backend", "command"]
    else:
        tokens = [sys.executable, str(generator_script), "--backend", "command"]

    if command:
        tokens.extend(["--command", command])
    tokens.extend(["--adapter-profile", profile])
    tokens.extend(["--adapter-model", adapter_model])
    tokens.extend(["--adapter-effort", str(adapter_effort)])
    tokens.extend(["--adapter-thinking", str(adapter_thinking)])

    if adapter_timeout != 300:
        tokens.extend(["--adapter-timeout", str(adapter_timeout)])
    if pause_s != 3.0:
        tokens.extend(["--pause-s", str(pause_s)])
    if stagger_s != 20.0:
        tokens.extend(["--stagger-s", str(stagger_s)])
    if max_calls != MAX_CALLS_DEFAULT:
        tokens.extend(["--max-calls", str(max_calls)])
    if target_names != TARGET_NAMES_DEFAULT:
        tokens.extend(["--target-names", str(target_names)])
    if lock_dir is not None:
        tokens.extend(["--lock-dir", str(lock_dir)])

    tokens.extend([
        "--shard",
        f"{shard_idx}/{shards}",
        "--run-id",
        f"{run_id_prefix}-s{shard_idx}of{shards}",
        "--live",
        "--confirm",
    ])
    return tokens


def format_command_for_display(tokens: list[str]) -> str:
    """Format a token list as a shell-quoted command line matching --print-shard-commands."""
    out: list[str] = []
    # Match generate_name_pool.py --print-shard-commands quoting style
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("--command", "--adapter-profile", "--adapter-model", "--adapter-effort", "--adapter-thinking", "--lock-dir") and i + 1 < len(tokens):
            out.append(tok)
            out.append(shlex.quote(tokens[i + 1]))
            i += 2
        else:
            out.append(tok)
            i += 1
    return " ".join(out)


def _pid_alive(pid: int) -> bool:
    """Return True if pid exists and is not a zombie."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            content = stat_path.read_text(encoding="utf-8")
            rparen = content.rfind(")")
            if rparen != -1 and content[rparen + 2 : rparen + 3] == "Z":
                return False
        except OSError:
            pass
    return True


def _collect_descendant_pids_and_pgids(root_pids: list[int]) -> tuple[set[int], set[int]]:
    """Discover all descendant PIDs and process group IDs of root_pids via /proc.

    Needed because CommandGenerationBackend in generate_name_pool.py spawns the
    adapter with start_new_session=True (putting the adapter and its children into
    a separate process group from the shard generator process).
    """
    all_pids: set[int] = set(root_pids)
    all_pgids: set[int] = set(root_pids)

    # Build ppid -> children map and pid -> pgid map from /proc/[0-9]*/stat
    children_map: dict[int, set[int]] = {}
    pid_to_pgid: dict[int, int] = {}
    proc_root = Path("/proc")
    if proc_root.exists():
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            # Check /proc/<pid>/task/<tid>/children
            task_dir = entry / "task"
            if task_dir.exists():
                try:
                    for tdir in task_dir.iterdir():
                        ch_file = tdir / "children"
                        if ch_file.exists():
                            for tok in ch_file.read_text(encoding="utf-8").split():
                                if tok.isdigit():
                                    children_map.setdefault(pid, set()).add(int(tok))
                except OSError:
                    pass
            # Also parse /proc/<pid>/stat for ppid and pgrp
            stat_file = entry / "stat"
            if stat_file.exists():
                try:
                    raw = stat_file.read_text(encoding="utf-8")
                    rparen = raw.rfind(")")
                    if rparen != -1:
                        rest = raw[rparen + 2 :].split()
                        if len(rest) >= 3:
                            ppid = int(rest[1])
                            pgrp = int(rest[2])
                            children_map.setdefault(ppid, set()).add(pid)
                            pid_to_pgid[pid] = pgrp
                except (OSError, ValueError):
                    pass

    queue = list(root_pids)
    while queue:
        curr = queue.pop(0)
        try:
            pg = os.getpgid(curr)
            if pg > 1:
                all_pgids.add(pg)
        except OSError:
            if curr in pid_to_pgid and pid_to_pgid[curr] > 1:
                all_pgids.add(pid_to_pgid[curr])
        for child_pid in children_map.get(curr, set()):
            if child_pid not in all_pids:
                all_pids.add(child_pid)
                queue.append(child_pid)

    return all_pids, all_pgids


def _terminate_all_children(shards: list[ShardState], sigterm_wait_s: float = 5.0) -> None:
    """Send SIGTERM to all active child process groups and descendant sessions, wait up to sigterm_wait_s, then SIGKILL."""
    active: list[ShardState] = []
    root_pids: list[int] = []
    for s in shards:
        if s.proc is not None and s.proc.poll() is None:
            active.append(s)
            root_pids.append(s.proc.pid)

    if not active:
        for s in shards:
            if s.log_fh is not None:
                try:
                    s.log_fh.close()
                except OSError:
                    pass
                s.log_fh = None
        return

    desc_pids, desc_pgids = _collect_descendant_pids_and_pgids(root_pids)

    for pgid in desc_pgids:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    for pid in desc_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    deadline = time.monotonic() + sigterm_wait_s
    for s in active:
        assert s.proc is not None
        rem = max(0.0, deadline - time.monotonic())
        try:
            s.proc.wait(timeout=rem)
        except subprocess.TimeoutExpired:
            pass

    while time.monotonic() < deadline:
        if not any(_pid_alive(p) for p in desc_pids):
            break
        time.sleep(0.02)

    # Re-scan any remaining live PIDs and escalate to SIGKILL
    live_roots = [p for p in desc_pids if _pid_alive(p)]
    if live_roots:
        more_pids, more_pgids = _collect_descendant_pids_and_pgids(live_roots)
        desc_pids.update(more_pids)
        desc_pgids.update(more_pgids)

    for pgid in desc_pgids:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    for pid in desc_pids:
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass

    for s in active:
        assert s.proc is not None
        if s.proc.poll() is None:
            try:
                s.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass

    kill_deadline = time.monotonic() + 2.0
    while time.monotonic() < kill_deadline:
        if not any(_pid_alive(p) for p in desc_pids):
            break
        time.sleep(0.02)

    for s in shards:
        if s.log_fh is not None:
            try:
                s.log_fh.close()
            except OSError:
                pass
            s.log_fh = None


def _count_raw_cache_lines(cache_path: Path) -> int:
    """Count non-empty lines in a shard's raw_responses.jsonl file."""
    if not cache_path.exists():
        return 0
    count = 0
    with open(cache_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def print_status_from_state_dir(state_dir: Path) -> int:
    """Read <state-dir>/status.json and shard caches (read-only) and print a formatted status table."""
    status_path = state_dir / "status.json"
    if not status_path.exists():
        print(f"ERROR: Status file not found at {status_path}", file=sys.stderr)
        return SUP_EXIT_ERROR

    try:
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"ERROR: Failed to read status file {status_path}: {exc}", file=sys.stderr)
        return SUP_EXIT_ERROR

    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()

    print(f"=== Name-Pool Supervisor Status ({state_dir}) ===")
    print(f"Run ID prefix:    {data.get('run_id_prefix', 'unknown')}")
    print(f"Supervisor PID:   {data.get('supervisor_pid', 'none')}")
    print(f"Supervisor state: {data.get('supervisor_state', 'unknown')}")
    print(f"Updated at (UTC): {data.get('updated_at_utc', 'unknown')}")
    print()

    header = f"{'Shard':<7} {'Run ID':<22} {'Profile':<18} {'PID':<8} {'State':<20} {'Restarts':<8} {'Records':<8} {'Valid':<8} {'LastExit':<8}"
    print(header)
    print("-" * len(header))

    total_live_records = 0
    all_entries = []
    for s in data.get("shards", []):
        shard_lbl = str(s.get("shard", "?"))
        rid = str(s.get("run_id", "?"))
        prof = str(s.get("profile") or "-")
        pid_str = str(s.get("pid") if s.get("pid") is not None else "-")
        st = str(s.get("state", "?"))
        restarts = int(s.get("restarts", 0))
        last_exit = str(s.get("last_exit_code") if s.get("last_exit_code") is not None else "-")

        cpath = Path(s.get("cache_path") or f"results/datagen/{rid}/raw_responses.jsonl")
        rec_count = int(s.get("records", 0))
        val_count = int(s.get("valid_names", 0))
        if cpath.exists():
            try:
                cdict = load_completed_cache(cpath)
                rec_count = _count_raw_cache_lines(cpath)
                vnames, _, _ = validate_and_dedupe_candidates(
                    list(cdict.values()), corpus_nodes, corpus_embeds
                )
                val_count = len(vnames)
                all_entries.extend(cdict.values())
            except Exception:
                pass
        total_live_records += rec_count
        print(
            f"{shard_lbl:<7} {rid:<22} {prof:<18} {pid_str:<8} {st:<20} "
            f"{restarts:<8} {rec_count:<8} {val_count:<8} {last_exit:<8}"
        )

    print("-" * len(header))
    global_valid = data.get("total_valid_names", 0)
    if all_entries:
        gv, _, _ = validate_and_dedupe_candidates(all_entries, corpus_nodes, corpus_embeds)
        global_valid = len(gv)

    print(f"Total calls (cache lines): {total_live_records} / {data.get('max_total_calls', DEFAULT_MAX_TOTAL_CALLS)}")
    print(f"Total deduplicated valid:  {global_valid} / {data.get('target_names', TARGET_NAMES_DEFAULT)}")

    cooling = data.get("cooling_profiles", [])
    if cooling:
        print("Cooling profiles:")
        for c in cooling:
            print(
                f"  - {c.get('profile')}: reason={c.get('reason')}, "
                f"until={c.get('until_utc')} (remaining={c.get('remaining_s')}s)"
            )
    else:
        print("Cooling profiles: none")

    return SUP_EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thesis-side supervisor for sharded synthetic CS concept-name pool generation."
    )
    parser.add_argument(
        "--shards",
        type=int,
        default=None,
        help="Number of shards N (N >= 1).",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default=None,
        help="Comma-separated browser profiles 'P1,...,Pk' (k >= N; first N initial, rest spares in order).",
    )
    parser.add_argument(
        "--run-id-prefix",
        type=str,
        default=None,
        help="Run ID prefix for shards (<prefix>-s<i>of<N>).",
    )
    parser.add_argument(
        "--command",
        type=str,
        default=None,
        help="Command string for command backend (passed through to generate_name_pool.py).",
    )
    parser.add_argument(
        "--adapter-model",
        type=str,
        default="sonnet",
        help="Model identifier requested for command adapter (default: sonnet).",
    )
    parser.add_argument(
        "--adapter-effort",
        type=str,
        default="low",
        help="Effort tier for command adapter: low, medium, high, extra, max (default: low).",
    )
    parser.add_argument(
        "--adapter-thinking",
        type=str,
        choices=["auto", "on", "off"],
        default="auto",
        help="Thinking mode control for command adapter: auto (null), on (true), off (false) (default: auto).",
    )
    parser.add_argument(
        "--adapter-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for adapter conversation (default: 300).",
    )
    parser.add_argument(
        "--pause-s",
        type=float,
        default=3.0,
        help="Pause in seconds between command backend calls (default: 3.0).",
    )
    parser.add_argument(
        "--stagger-s",
        type=float,
        default=20.0,
        help="Seconds to stagger shard execution before first call (default: 20.0; 0 disables).",
    )
    parser.add_argument(
        "--target-names",
        type=int,
        default=TARGET_NAMES_DEFAULT,
        help=f"Target number of valid names to collect across shards (default: {TARGET_NAMES_DEFAULT}).",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=MAX_CALLS_DEFAULT,
        help=f"Maximum calls per shard invocation (default: {MAX_CALLS_DEFAULT}).",
    )
    parser.add_argument(
        "--lock-dir",
        type=Path,
        default=None,
        help="Directory for profile locks (passed through to generate_name_pool.py; default: results/datagen/.locks).",
    )
    parser.add_argument(
        "--poll-s",
        type=float,
        default=DEFAULT_POLL_S,
        help=f"Supervisor polling interval in seconds (default: {DEFAULT_POLL_S}).",
    )
    parser.add_argument(
        "--max-restarts-per-shard",
        type=int,
        default=DEFAULT_MAX_RESTARTS_PER_SHARD,
        help=f"Maximum restarts allowed per shard before aborting (default: {DEFAULT_MAX_RESTARTS_PER_SHARD}).",
    )
    parser.add_argument(
        "--profile-cooldown-s",
        type=float,
        default=DEFAULT_PROFILE_COOLDOWN_S,
        help=(
            f"Seconds to retire a rate-limited profile before reuse "
            f"(default: {int(DEFAULT_PROFILE_COOLDOWN_S)}; unverified operator assumption)."
        ),
    )
    parser.add_argument(
        "--max-wait-s",
        type=float,
        default=DEFAULT_MAX_WAIT_S,
        help=(
            f"Maximum seconds to wait when no profile is free before stopping with stalled exit code "
            f"(default: {int(DEFAULT_MAX_WAIT_S)})."
        ),
    )
    parser.add_argument(
        "--max-total-calls",
        type=int,
        default=DEFAULT_MAX_TOTAL_CALLS,
        help=(
            f"Maximum total calls counted as cache lines across all shards; stop everything when exceeded "
            f"(default: {DEFAULT_MAX_TOTAL_CALLS})."
        ),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Supervisor state directory for status.json and supervisor-log.jsonl (default: results/datagen/<prefix>-supervisor).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_TRACKED_OUTPUT,
        help=f"Output pool JSON path (default: {DEFAULT_TRACKED_OUTPUT}).",
    )
    parser.add_argument(
        "--min-required-names",
        type=int,
        default=None,
        help=f"Optional override for minimum required valid names during merge/verify (default: {MIN_REQUIRED_NAMES_FOR_VALIDATION}).",
    )
    parser.add_argument(
        "--generator-script",
        type=Path,
        default=_GENERATOR_SCRIPT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print shard commands, initial profile assignment, and spares; launch nothing and create no files.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Read-only status table from <state-dir>/status.json and shard caches.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live execution of shard subprocesses (requires --confirm).",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm live execution of shard subprocesses (requires --live).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve state_dir early for --status mode
    if args.status:
        if args.state_dir is not None:
            state_dir = Path(args.state_dir)
        elif args.run_id_prefix:
            state_dir = Path("results/datagen") / f"{args.run_id_prefix}-supervisor"
        else:
            print("ERROR: --status requires either --state-dir or --run-id-prefix.", file=sys.stderr)
            return SUP_EXIT_USAGE
        return print_status_from_state_dir(state_dir)

    # Validate required orchestration arguments for --dry-run and live execution
    if args.shards is None or args.shards < 1:
        print("ERROR: --shards N is required and must satisfy N >= 1.", file=sys.stderr)
        return SUP_EXIT_USAGE

    if not args.profiles:
        print("ERROR: --profiles 'P1,...,Pk' is required.", file=sys.stderr)
        return SUP_EXIT_USAGE

    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    if len(profiles) < args.shards:
        print(
            f"ERROR: Profiles count ({len(profiles)}) must be >= shards count ({args.shards}).",
            file=sys.stderr,
        )
        return SUP_EXIT_USAGE

    if len(set(profiles)) != len(profiles):
        print("ERROR: Duplicate profile names found in --profiles.", file=sys.stderr)
        return SUP_EXIT_USAGE

    if not args.run_id_prefix or not args.run_id_prefix.strip():
        print("ERROR: --run-id-prefix is required.", file=sys.stderr)
        return SUP_EXIT_USAGE

    run_id_prefix = args.run_id_prefix.strip()
    state_dir = Path(args.state_dir) if args.state_dir is not None else Path("results/datagen") / f"{run_id_prefix}-supervisor"
    output_path = Path(args.output)
    lock_dir = Path(args.lock_dir) if args.lock_dir is not None else Path("results/datagen/.locks")

    initial_profiles = profiles[: args.shards]
    spare_profiles = profiles[args.shards :]

    # --dry-run mode: print shard commands, profile assignment, and spares; launch nothing
    if args.dry_run:
        print("=== DATA-007 Name-Pool Supervisor Plan (Dry Run) ===")
        print(f"Shards (N):              {args.shards}")
        print(f"Run ID prefix:           {run_id_prefix}")
        print(f"Initial profiles (1..N): {', '.join(initial_profiles)}")
        print(f"Spare profiles ({len(spare_profiles)}):      {', '.join(spare_profiles) if spare_profiles else '[none]'}")
        print(f"State dir:               {state_dir}")
        print(f"Output pool path:        {output_path}")
        print(f"Poll interval:           {args.poll_s} s")
        print(f"Max restarts / shard:    {args.max_restarts_per_shard}")
        print(f"Profile cooldown:        {args.profile_cooldown_s} s (unverified operator assumption)")
        print(f"Max wait (all cooling):  {args.max_wait_s} s")
        print(f"Max total calls cap:     {args.max_total_calls}")
        print("\n--- Initial Shard Commands ---")
        for i in range(1, args.shards + 1):
            prof = initial_profiles[i - 1]
            display_tokens = build_shard_cli_tokens(
                shard_idx=i,
                shards=args.shards,
                run_id_prefix=run_id_prefix,
                profile=prof,
                command=args.command,
                adapter_model=args.adapter_model,
                adapter_effort=args.adapter_effort,
                adapter_thinking=args.adapter_thinking,
                adapter_timeout=args.adapter_timeout,
                pause_s=args.pause_s,
                stagger_s=args.stagger_s,
                max_calls=args.max_calls,
                target_names=args.target_names,
                lock_dir=args.lock_dir,
                for_display=True,
                generator_script=args.generator_script,
            )
            print(format_command_for_display(display_tokens))
        print("\nDry run complete (nothing launched, no files created).")
        return SUP_EXIT_OK

    # Guard: require both --live and --confirm to launch (exit 2)
    if not (args.live and args.confirm):
        print(
            "ERROR: Refusing to launch supervisor without both --live and --confirm (or pass --dry-run / --status).",
            file=sys.stderr,
        )
        return SUP_EXIT_USAGE

    if not args.command or not args.command.strip():
        print("ERROR: --command is required for live execution.", file=sys.stderr)
        return SUP_EXIT_USAGE

    # Load benchmark corpora once for fast cache validation across polls
    corpus_nodes, corpus_embeds, _ = load_benchmark_corpus_concepts()

    shards: list[ShardState] = []
    for i in range(1, args.shards + 1):
        rid = f"{run_id_prefix}-s{i}of{args.shards}"
        cpath = Path("results/datagen") / rid / "raw_responses.jsonl"
        shards.append(
            ShardState(
                shard_idx=i,
                shard_total=args.shards,
                run_id=rid,
                cache_path=cpath,
                profile=initial_profiles[i - 1],
                state="pending",
            )
        )

    # Profile pool tracking
    profile_order: dict[str, int] = {p: idx for idx, p in enumerate(profiles)}
    times_assigned: dict[str, int] = {p: 0 for p in profiles}
    cooling: dict[str, CoolingEntry] = {}

    # Signal handling state
    received_signal: list[int] = []

    def _on_signal(signum: int, _frame: Any) -> None:
        received_signal.append(signum)

    prev_sigint = signal.signal(signal.SIGINT, _on_signal)
    prev_sigterm = signal.signal(signal.SIGTERM, _on_signal)

    def _expire_cooldowns(now_mono: float) -> None:
        expired = [p for p, ce in cooling.items() if ce.until_mono <= now_mono]
        for p in expired:
            del cooling[p]

    def _active_profiles() -> set[str]:
        return {
            s.profile
            for s in shards
            if s.profile is not None and s.state == "running"
        }

    def _pick_next_profile(now_mono: float) -> Optional[str]:
        """Return the next unassigned, non-cooling profile, prioritizing fresh spares in order."""
        _expire_cooldowns(now_mono)
        in_use = _active_profiles()
        candidates = [
            p
            for p in profiles
            if p not in in_use and p not in cooling
        ]
        if not candidates:
            return None
        # Fresh spares (times_assigned == 0) in original --profiles order come first,
        # followed by previously used profiles whose cooldown expired.
        candidates.sort(key=lambda p: (times_assigned[p], profile_order[p]))
        return candidates[0]

    def _launch_shard(s: ShardState, prof: str, is_restart: bool) -> None:
        s.profile = prof
        times_assigned[prof] = times_assigned.get(prof, 0) + 1
        cmd_tokens = build_shard_cli_tokens(
            shard_idx=s.shard_idx,
            shards=s.shard_total,
            run_id_prefix=run_id_prefix,
            profile=prof,
            command=args.command,
            adapter_model=args.adapter_model,
            adapter_effort=args.adapter_effort,
            adapter_thinking=args.adapter_thinking,
            adapter_timeout=args.adapter_timeout,
            pause_s=args.pause_s,
            stagger_s=args.stagger_s,
            max_calls=args.max_calls,
            target_names=args.target_names,
            lock_dir=args.lock_dir,
            for_display=False,
            generator_script=args.generator_script,
        )
        state_dir.mkdir(parents=True, exist_ok=True)
        shard_log_path = state_dir / f"shard-{s.shard_idx}.log"
        if s.log_fh is not None:
            try:
                s.log_fh.close()
            except OSError:
                pass
        s.log_fh = open(shard_log_path, "ab")
        proc = subprocess.Popen(
            cmd_tokens,
            stdin=subprocess.DEVNULL,
            stdout=s.log_fh,
            stderr=s.log_fh,
            start_new_session=True,
        )
        s.proc = proc
        s.pid = proc.pid
        s.state = "running"
        _append_supervisor_log(
            state_dir,
            "shard_restart" if is_restart else "shard_launch",
            shard=s.shard_label,
            run_id=s.run_id,
            profile=prof,
            pid=proc.pid,
            restarts=s.restarts,
            command=format_command_for_display(cmd_tokens),
        )

    def _refresh_caches_and_write_status(supervisor_state: str) -> tuple[int, int]:
        """Re-read all shard caches via load_completed_cache, update ShardState counts,
        and atomically write <state-dir>/status.json.
        Raises ValueError if load_completed_cache raises ValueError.
        Returns (total_calls, total_valid_names).
        """
        now_mono = time.monotonic()
        _expire_cooldowns(now_mono)

        total_calls = 0
        all_entries = []
        for s in shards:
            if s.cache_path.exists():
                cdict = load_completed_cache(s.cache_path)
                s.records = _count_raw_cache_lines(s.cache_path)
                vnames, _, _ = validate_and_dedupe_candidates(
                    list(cdict.values()), corpus_nodes, corpus_embeds
                )
                s.valid_names = len(vnames)
                all_entries.extend(cdict.values())
            else:
                s.records = 0
                s.valid_names = 0
            total_calls += s.records

        if all_entries:
            global_valid_list, _, _ = validate_and_dedupe_candidates(
                all_entries, corpus_nodes, corpus_embeds
            )
            total_valid_names = len(global_valid_list)
        else:
            total_valid_names = 0

        cooling_list = []
        for p in sorted(cooling.keys(), key=lambda k: profile_order.get(k, 999)):
            ce = cooling[p]
            rem_s = max(0.0, round(ce.until_mono - now_mono, 2))
            cooling_list.append({
                "profile": ce.profile,
                "reason": ce.reason,
                "until_utc": ce.until_utc,
                "remaining_s": rem_s,
            })

        in_use = _active_profiles()
        spares_avail = [
            p for p in profiles if p not in in_use and p not in cooling
        ]

        status_payload: dict[str, Any] = {
            "run_id_prefix": run_id_prefix,
            "supervisor_pid": os.getpid(),
            "supervisor_state": supervisor_state,
            "updated_at_utc": _now_utc_iso(),
            "total_calls": total_calls,
            "max_total_calls": args.max_total_calls,
            "total_valid_names": total_valid_names,
            "target_names": args.target_names,
            "shards": [
                {
                    "shard": s.shard_label,
                    "shard_index": s.shard_idx,
                    "run_id": s.run_id,
                    "cache_path": str(s.cache_path),
                    "profile": s.profile,
                    "pid": s.pid,
                    "state": s.state,
                    "restarts": s.restarts,
                    "records": s.records,
                    "valid_names": s.valid_names,
                    "last_exit_code": s.last_exit_code,
                }
                for s in shards
            ],
            "cooling_profiles": cooling_list,
            "spares_available": spares_avail,
        }
        _write_status_atomic(state_dir, status_payload)
        return total_calls, total_valid_names

    try:
        _append_supervisor_log(
            state_dir,
            "supervisor_start",
            shards=args.shards,
            profiles=profiles,
            initial_profiles=initial_profiles,
            spare_profiles=spare_profiles,
            run_id_prefix=run_id_prefix,
            max_total_calls=args.max_total_calls,
            profile_cooldown_s=args.profile_cooldown_s,
            max_wait_s=args.max_wait_s,
        )

        # Launch initial shards
        for s in shards:
            assert s.profile is not None
            _launch_shard(s, s.profile, is_restart=False)

        wait_for_profile_since: Optional[float] = None

        while True:
            # 1. Check signal interruption
            if received_signal:
                sig = received_signal[0]
                print(
                    f"\nReceived signal {sig}; terminating shard process groups cleanly...",
                    file=sys.stderr,
                )
                _terminate_all_children(shards)
                for s in shards:
                    if s.state in ("running", "waiting_for_profile"):
                        s.state = "stopped"
                        s.pid = None
                try:
                    _refresh_caches_and_write_status("interrupted")
                except Exception:
                    pass
                _append_supervisor_log(state_dir, "signal_received", signal=sig, exit_code=SUP_EXIT_SIGNAL)
                return SUP_EXIT_SIGNAL

            # 2. Check exited child processes
            now_mono = time.monotonic()
            _expire_cooldowns(now_mono)

            for s in shards:
                if s.state == "running" and s.proc is not None:
                    rc = s.proc.poll()
                    if rc is not None:
                        exited_pid = s.pid
                        old_prof = s.profile
                        s.last_exit_code = rc
                        s.pid = None
                        if s.log_fh is not None:
                            try:
                                s.log_fh.close()
                            except OSError:
                                pass
                            s.log_fh = None

                        _append_supervisor_log(
                            state_dir,
                            "shard_exit",
                            shard=s.shard_label,
                            run_id=s.run_id,
                            profile=old_prof,
                            pid=exited_pid,
                            exit_code=rc,
                        )

                        if rc == GEN_EXIT_OK:
                            s.state = "done"
                        elif rc in (GEN_EXIT_RATE_LIMIT, GEN_EXIT_PROFILE_IN_USE):
                            # Put current profile into cooldown
                            if old_prof is not None:
                                cd_s = (
                                    float(args.profile_cooldown_s)
                                    if rc == GEN_EXIT_RATE_LIMIT
                                    else PROFILE_BUSY_COOLDOWN_S
                                )
                                reason = "rate_limit" if rc == GEN_EXIT_RATE_LIMIT else "profile_in_use"
                                until_dt = datetime.now(timezone.utc) + timedelta(seconds=cd_s)
                                cooling[old_prof] = CoolingEntry(
                                    profile=old_prof,
                                    until_mono=time.monotonic() + cd_s,
                                    until_utc=until_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    reason=reason,
                                    cooldown_s=cd_s,
                                )
                                _append_supervisor_log(
                                    state_dir,
                                    "profile_cooldown",
                                    shard=s.shard_label,
                                    run_id=s.run_id,
                                    profile=old_prof,
                                    reason=reason,
                                    cooldown_s=cd_s,
                                    until_utc=cooling[old_prof].until_utc,
                                )

                            s.restarts += 1
                            if s.restarts > args.max_restarts_per_shard:
                                msg = (
                                    f"ERROR: Shard {s.shard_label} ({s.run_id}) exceeded "
                                    f"--max-restarts-per-shard ({args.max_restarts_per_shard}). Stopping all shards."
                                )
                                print(msg, file=sys.stderr)
                                s.state = "failed"
                                _terminate_all_children(shards)
                                for other in shards:
                                    if other.state in ("running", "waiting_for_profile"):
                                        other.state = "stopped"
                                        other.pid = None
                                try:
                                    _refresh_caches_and_write_status("failed")
                                except Exception:
                                    pass
                                _append_supervisor_log(
                                    state_dir,
                                    "supervisor_stop",
                                    reason="max_restarts_exceeded",
                                    shard=s.shard_label,
                                    restarts=s.restarts,
                                    exit_code=SUP_EXIT_ERROR,
                                )
                                return SUP_EXIT_ERROR

                            s.state = "waiting_for_profile"
                        else:
                            # Fatal or unknown exit code -> stop all shards cleanly, keep caches, exit non-zero
                            msg = (
                                f"ERROR: Shard {s.shard_label} ({s.run_id}) on profile {old_prof!r} "
                                f"exited with fatal/unexpected code {rc}. Stopping all shards."
                            )
                            print(msg, file=sys.stderr)
                            s.state = "failed"
                            _terminate_all_children(shards)
                            for other in shards:
                                if other.state in ("running", "waiting_for_profile"):
                                    other.state = "stopped"
                                    other.pid = None
                            try:
                                _refresh_caches_and_write_status("failed")
                            except Exception:
                                pass
                            _append_supervisor_log(
                                state_dir,
                                "supervisor_stop",
                                reason="fatal_or_unknown_shard_exit",
                                shard=s.shard_label,
                                run_id=s.run_id,
                                profile=old_prof,
                                shard_exit_code=rc,
                                exit_code=SUP_EXIT_ERROR,
                            )
                            return SUP_EXIT_ERROR

            # 3. Assign available profiles to any shards waiting for a profile
            now_mono = time.monotonic()
            for s in shards:
                if s.state == "waiting_for_profile":
                    next_prof = _pick_next_profile(now_mono)
                    if next_prof is not None:
                        old_prof = s.profile
                        _append_supervisor_log(
                            state_dir,
                            "profile_reassigned",
                            shard=s.shard_label,
                            run_id=s.run_id,
                            old_profile=old_prof,
                            new_profile=next_prof,
                            restarts=s.restarts,
                        )
                        _launch_shard(s, next_prof, is_restart=True)

            # Track waiting time if any shard is still waiting for a free profile
            any_waiting = any(s.state == "waiting_for_profile" for s in shards)
            if any_waiting:
                if wait_for_profile_since is None:
                    wait_for_profile_since = time.monotonic()
            else:
                wait_for_profile_since = None

            # 4. Re-read shard caches via generator loader & update status.json atomically
            try:
                total_calls, total_valid_names = _refresh_caches_and_write_status("running")
            except ValueError as exc:
                msg = f"ERROR: Cache loader raised ValueError: {exc}. Stopping all shards."
                print(msg, file=sys.stderr)
                _terminate_all_children(shards)
                for s in shards:
                    if s.state in ("running", "waiting_for_profile"):
                        s.state = "stopped"
                        s.pid = None
                _append_supervisor_log(
                    state_dir,
                    "loader_error",
                    error=str(exc),
                    exit_code=SUP_EXIT_ERROR,
                )
                return SUP_EXIT_ERROR

            # Print one-line poll summary
            running_cnt = sum(1 for s in shards if s.state == "running")
            done_cnt = sum(1 for s in shards if s.state == "done")
            waiting_cnt = sum(1 for s in shards if s.state == "waiting_for_profile")
            print(
                f"[poll {_now_utc_iso()}] shards: {running_cnt} running, {done_cnt}/{len(shards)} done, "
                f"{waiting_cnt} waiting | calls: {total_calls}/{args.max_total_calls} | "
                f"valid_names: {total_valid_names}/{args.target_names} | cooling: {len(cooling)}"
            )
            sys.stdout.flush()

            all_done = all(s.state == "done" for s in shards)

            # 5. Enforce --max-total-calls cap
            if total_calls > args.max_total_calls or (total_calls >= args.max_total_calls and not all_done):
                msg = (
                    f"ERROR: Total calls across shards ({total_calls}) reached/exceeded "
                    f"--max-total-calls ({args.max_total_calls}). Stopping all shards."
                )
                print(msg, file=sys.stderr)
                _terminate_all_children(shards)
                for s in shards:
                    if s.state in ("running", "waiting_for_profile"):
                        s.state = "stopped"
                        s.pid = None
                try:
                    _refresh_caches_and_write_status("stopped_max_calls")
                except Exception:
                    pass
                _append_supervisor_log(
                    state_dir,
                    "max_total_calls_exceeded",
                    total_calls=total_calls,
                    max_total_calls=args.max_total_calls,
                    exit_code=SUP_EXIT_MAX_TOTAL_CALLS,
                )
                return SUP_EXIT_MAX_TOTAL_CALLS

            # 6. Check if all shards have completed with exit 0
            if all_done:
                break

            # 7. Check if stalled waiting for a free profile beyond --max-wait-s
            if wait_for_profile_since is not None:
                waited_s = time.monotonic() - wait_for_profile_since
                if waited_s >= args.max_wait_s:
                    msg = (
                        f"STALLED: No free profile became available within --max-wait-s "
                        f"({args.max_wait_s}s). Stopping cleanly; caches are intact and resumable."
                    )
                    print(msg, file=sys.stderr)
                    _terminate_all_children(shards)
                    for s in shards:
                        if s.state in ("running", "waiting_for_profile"):
                            s.state = "stalled"
                            s.pid = None
                    try:
                        _refresh_caches_and_write_status("stalled")
                    except Exception:
                        pass
                    _append_supervisor_log(
                        state_dir,
                        "stalled",
                        waited_s=round(waited_s, 3),
                        max_wait_s=args.max_wait_s,
                        exit_code=SUP_EXIT_STALLED,
                    )
                    return SUP_EXIT_STALLED

            # 8. Compute sleep duration until next poll, earliest cooldown expiry, or max_wait deadline
            now_mono = time.monotonic()
            sleep_s = float(args.poll_s)
            if any_waiting and cooling:
                earliest_cd = min(ce.until_mono for ce in cooling.values())
                cd_rem = max(0.01, earliest_cd - now_mono)
                sleep_s = min(sleep_s, cd_rem)
            if wait_for_profile_since is not None:
                wait_rem = max(0.01, (wait_for_profile_since + args.max_wait_s) - now_mono)
                sleep_s = min(sleep_s, wait_rem)

            # Sleep in small slices so SIGINT/SIGTERM is handled promptly
            sleep_deadline = time.monotonic() + sleep_s
            while time.monotonic() < sleep_deadline:
                if received_signal:
                    break
                # Also wake early if any running child exits
                if any(s.proc is not None and s.proc.poll() is not None for s in shards if s.state == "running"):
                    break
                rem_slice = sleep_deadline - time.monotonic()
                time.sleep(min(0.05, max(0.005, rem_slice)))

        # All shards exited 0 -> Run merge (--build-only --merge-run-ids) then verify (--verify --merge-run-ids)
        merge_ids = ",".join(s.run_id for s in shards)
        effective_min_req = (
            args.min_required_names
            if args.min_required_names is not None
            else min(MIN_REQUIRED_NAMES_FOR_VALIDATION, args.target_names)
        )

        _refresh_caches_and_write_status("merging")
        build_cmd = [
            sys.executable,
            str(args.generator_script),
            "--build-only",
            "--backend",
            "command",
            "--adapter-model",
            args.adapter_model,
            "--merge-run-ids",
            merge_ids,
        ]
        if output_path.resolve() != DEFAULT_TRACKED_OUTPUT.resolve():
            build_cmd.extend(["--output", str(output_path)])
        if effective_min_req != MIN_REQUIRED_NAMES_FOR_VALIDATION:
            build_cmd.extend(["--min-required-names", str(effective_min_req)])

        _append_supervisor_log(state_dir, "merge_start", command=" ".join(build_cmd))
        res_build = subprocess.run(build_cmd, capture_output=True, text=True)
        _append_supervisor_log(
            state_dir,
            "merge_done",
            exit_code=res_build.returncode,
            stdout=res_build.stdout.strip(),
            stderr=res_build.stderr.strip(),
        )
        if res_build.returncode != 0:
            print(f"ERROR: Merge (--build-only) failed (exit {res_build.returncode}):\n{res_build.stderr}", file=sys.stderr)
            _refresh_caches_and_write_status("failed")
            return SUP_EXIT_ERROR

        _refresh_caches_and_write_status("verifying")
        verify_cmd = [
            sys.executable,
            str(args.generator_script),
            "--verify",
            "--merge-run-ids",
            merge_ids,
        ]
        if output_path.resolve() != DEFAULT_TRACKED_OUTPUT.resolve():
            verify_cmd.extend(["--output", str(output_path)])
        if effective_min_req != MIN_REQUIRED_NAMES_FOR_VALIDATION:
            verify_cmd.extend(["--min-required-names", str(effective_min_req)])

        _append_supervisor_log(state_dir, "verify_start", command=" ".join(verify_cmd))
        res_verify = subprocess.run(verify_cmd, capture_output=True, text=True)
        _append_supervisor_log(
            state_dir,
            "verify_done",
            exit_code=res_verify.returncode,
            stdout=res_verify.stdout.strip(),
            stderr=res_verify.stderr.strip(),
        )
        if res_verify.returncode != 0:
            print(f"ERROR: Verification (--verify) failed (exit {res_verify.returncode}):\n{res_verify.stderr}", file=sys.stderr)
            _refresh_caches_and_write_status("failed")
            return SUP_EXIT_ERROR

        _refresh_caches_and_write_status("completed")
        _append_supervisor_log(
            state_dir,
            "supervisor_stop",
            reason="completed",
            output_path=str(output_path),
            exit_code=SUP_EXIT_OK,
        )

        # Print pool meta summary
        with open(output_path, "r", encoding="utf-8") as f:
            pool_data = json.load(f)
        meta = pool_data.get("meta", {})
        summary_meta = {k: v for k, v in meta.items() if k != "corpora_checked"}
        print("\n=== Merged Pool Verification PASSED ===")
        print(res_verify.stdout.strip())
        print("=== Pool Meta Summary ===")
        print(json.dumps(summary_meta, indent=2, ensure_ascii=False))
        return SUP_EXIT_OK

    finally:
        _terminate_all_children(shards)
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)


if __name__ == "__main__":
    sys.exit(main())
