"""Tests for scripts/name_pool_supervisor.py (DATA-007).

All tests run offline against tests/stub_prompt_adapter.py inside pytest's tmp_path.
A module-scoped autouse guard fixture verifies that nothing under <repo_root>/results/datagen
is created or modified during the test session.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any

import pytest

# Ensure src/ and repo root are importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.generate_name_pool import load_completed_cache
from scripts.name_pool_supervisor import (
    SUP_EXIT_ERROR,
    SUP_EXIT_MAX_TOTAL_CALLS,
    SUP_EXIT_OK,
    SUP_EXIT_SIGNAL,
    SUP_EXIT_STALLED,
    SUP_EXIT_USAGE,
    main as supervisor_main,
)

_SUPERVISOR_SCRIPT = _REPO_ROOT / "scripts" / "name_pool_supervisor.py"
_STUB_SCRIPT = _REPO_ROOT / "tests" / "stub_prompt_adapter.py"


@pytest.fixture(autouse=True, scope="module")
def guard_results_datagen_unmodified():
    """Verify that nothing under <repo_root>/results/datagen is created or modified by tests."""
    datagen_dir = _REPO_ROOT / "results" / "datagen"

    def _snapshot() -> set[str]:
        if not datagen_dir.exists():
            return set()
        return {str(p.relative_to(datagen_dir)) for p in datagen_dir.rglob("*")}

    before = _snapshot()
    yield
    after = _snapshot()
    assert before == after, (
        f"Test suite modified results/datagen! Diff: added={after - before}, removed={before - after}"
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Check if zombie on Linux
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            content = stat_path.read_text(encoding="utf-8")
            # Format: pid (comm) state ...
            rparen = content.rfind(")")
            if rparen != -1:
                state_char = content[rparen + 2 : rparen + 3]
                if state_char == "Z":
                    return False
        except OSError:
            pass
    return True


def test_happy_path_two_shards_merged_and_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """1. Happy path: 2 shards, 2 profiles, stub succeeds -> both exit 0, merged pool built and verified."""
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_state"
    lock_dir = tmp_path / "locks"
    out_pool = tmp_path / "pool.json"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"

    rc = supervisor_main([
        "--shards", "2",
        "--profiles", "Profile_A,Profile_B",
        "--run-id-prefix", "happy2",
        "--command", stub_cmd,
        "--target-names", "120",
        "--max-calls", "5",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc == SUP_EXIT_OK

    captured = capsys.readouterr()
    assert "Merged Pool Verification PASSED" in captured.out
    assert "Pool Meta Summary" in captured.out

    assert out_pool.exists()
    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
    meta = pool_data["meta"]
    assert meta["run_ids"] == ["happy2-s1of2", "happy2-s2of2"]
    assert meta["profiles_used"] == ["Profile_A", "Profile_B"]
    assert len(pool_data["names"]) == 160  # 2 calls/shard * 2 shards * 40 names

    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    assert status["supervisor_state"] == "completed"
    assert status["total_calls"] == 4
    assert status["total_valid_names"] == 160
    assert all(s["state"] == "done" and s["last_exit_code"] == 0 for s in status["shards"])

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    event_names = [e["event"] for e in events]
    assert "supervisor_start" in event_names
    assert "merge_done" in event_names
    assert "verify_done" in event_names
    assert any(e["event"] == "verify_done" and e["exit_code"] == 0 for e in events)


def test_failover_on_rate_limit_to_spare_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """2. Failover on rate limit: 2 shards, 3 profiles; profile 1 rate-limits after K=1 calls ->
    shard 1 restarts on profile 3, resumes from cache, finishes.
    """
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_state"
    lock_dir = tmp_path / "locks"
    out_pool = tmp_path / "pool.json"
    stub_state_base = tmp_path / "stub_counter.txt"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --state-file {stub_state_base}"

    # Shard 1 needs ceil(120/2) = 60 valid names (2 calls of 40 names).
    # Profile 'rate_limit_after_1_p1' succeeds on call 1 (40 names) and rate-limits on call 2 (exit 3).
    # Supervisor cools 'rate_limit_after_1_p1' and restarts shard 1 on 'Spare_P3', which finishes call 2.
    rc = supervisor_main([
        "--shards", "2",
        "--profiles", "rate_limit_after_1_p1,Profile_2,Spare_P3",
        "--run-id-prefix", "failover",
        "--command", stub_cmd,
        "--target-names", "120",
        "--max-calls", "5",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--profile-cooldown-s", "18000",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc == SUP_EXIT_OK
    assert out_pool.exists()

    # Check shard 1 raw cache: must have 2 records, first from rate_limit_after_1_p1, second from Spare_P3
    s1_cache_path = tmp_path / "results" / "datagen" / "failover-s1of2" / "raw_responses.jsonl"
    s1_records = _read_jsonl(s1_cache_path)
    assert len(s1_records) == 2
    s1_profiles_in_cache = [r["backend_meta"]["profile_used"] for r in s1_records]
    assert s1_profiles_in_cache == ["rate_limit_after_1_p1", "Spare_P3"]

    # Check status.json and supervisor-log.jsonl
    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    assert status["supervisor_state"] == "completed"
    s1_status = next(s for s in status["shards"] if s["shard"] == "1/2")
    assert s1_status["restarts"] == 1
    assert s1_status["profile"] == "Spare_P3"
    assert s1_status["records"] == 2
    assert any(c["profile"] == "rate_limit_after_1_p1" and c["reason"] == "rate_limit" for c in status["cooling_profiles"])

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    reassign_events = [e for e in events if e["event"] == "profile_reassigned"]
    assert len(reassign_events) == 1
    assert reassign_events[0]["shard"] == "1/2"
    assert reassign_events[0]["old_profile"] == "rate_limit_after_1_p1"
    assert reassign_events[0]["new_profile"] == "Spare_P3"

    # Check merged pool built by generate_name_pool.py
    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
    assert len(pool_data["names"]) == 160
    assert pool_data["meta"]["run_ids"] == ["failover-s1of2", "failover-s2of2"]
    assert len(pool_data["meta"]["shards"]) == 2
    s1_meta = next(s for s in pool_data["meta"]["shards"] if s["shard"] == "1/2")
    s2_meta = next(s for s in pool_data["meta"]["shards"] if s["shard"] == "2/2")
    assert s1_meta["profile"] == "rate_limit_after_1_p1"
    assert s1_meta["profiles"] == ["rate_limit_after_1_p1", "Spare_P3"]
    assert s2_meta["profiles"] == ["Profile_2"]
    assert pool_data["meta"]["profiles_used"] == sorted(
        ["rate_limit_after_1_p1", "Profile_2", "Spare_P3"]
    )


def test_profile_in_use_rotates_to_next_profile_with_short_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3. Profile-in-use: shard hits exit 7 -> rotates to next profile without burning the 18000s rate-limit cooldown."""
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_state"
    lock_dir = tmp_path / "locks"
    out_pool = tmp_path / "pool.json"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"

    rc = supervisor_main([
        "--shards", "1",
        "--profiles", "profile_in_use_p1,Spare_P2",
        "--run-id-prefix", "inuse",
        "--command", stub_cmd,
        "--target-names", "40",
        "--max-calls", "3",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--profile-cooldown-s", "18000",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc == SUP_EXIT_OK

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    cd_events = [e for e in events if e["event"] == "profile_cooldown"]
    assert len(cd_events) == 1
    assert cd_events[0]["profile"] == "profile_in_use_p1"
    assert cd_events[0]["reason"] == "profile_in_use"
    # Must use 60s busy cooldown, NOT the 18000s rate_limit cooldown
    assert cd_events[0]["cooldown_s"] == 60.0

    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    assert status["shards"][0]["profile"] == "Spare_P2"
    assert status["shards"][0]["restarts"] == 1
    assert status["cooling_profiles"][0]["remaining_s"] <= 60.0

    pool_data = json.loads(out_pool.read_text(encoding="utf-8"))
    assert pool_data["meta"]["profiles_used"] == ["Spare_P2"]


def test_all_profiles_cooling_stalled_exit_caches_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """4. All profiles cooling: after --max-wait-s (set small in the test) supervisor exits with stalled code, caches intact."""
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_state"
    lock_dir = tmp_path / "locks"
    out_pool = tmp_path / "pool.json"
    stub_state_base = tmp_path / "stub_counter.txt"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --state-file {stub_state_base}"

    # 1 shard, 1 profile, target 80 names (2 calls). Profile rate-limits after 1 call.
    # Cooldown is 3600s, max-wait-s is 0.25s -> stalls after ~0.25s with SUP_EXIT_STALLED (3).
    rc = supervisor_main([
        "--shards", "1",
        "--profiles", "rate_limit_after_1_only",
        "--run-id-prefix", "stalledrun",
        "--command", stub_cmd,
        "--target-names", "80",
        "--max-calls", "5",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--profile-cooldown-s", "3600",
        "--max-wait-s", "0.25",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc == SUP_EXIT_STALLED
    assert not out_pool.exists()

    # Cache from call 1 must remain intact and resumable
    cache_path = tmp_path / "results" / "datagen" / "stalledrun-s1of1" / "raw_responses.jsonl"
    assert cache_path.exists()
    completed = load_completed_cache(cache_path)
    assert len(completed) == 1

    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    assert status["supervisor_state"] == "stalled"
    assert status["shards"][0]["state"] == "stalled"

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    assert any(e["event"] == "stalled" and e["exit_code"] == SUP_EXIT_STALLED for e in events)


def test_unknown_or_fatal_exit_code_terminates_children_and_preserves_caches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5. Unknown / fatal exit code (both a known fatal code and an arbitrary code like 99):
    supervisor terminates remaining shards and exits non-zero, caches intact.
    """
    monkeypatch.chdir(tmp_path)

    # Part A: Known fatal generator exit code 4 (login_required) while shard 2 is hanging
    state_dir_a = tmp_path / "state_fatal"
    lock_dir_a = tmp_path / "locks_fatal"
    child_pid_file_a = tmp_path / "child_fatal.pid"
    stub_cmd_a = (
        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
        f"--child-pid-file {child_pid_file_a} --hang-seconds 30"
    )

    # Pre-seed 1 valid cache line in shard 1 so we verify caches are preserved untouched
    s1_cache_a = tmp_path / "results" / "datagen" / "fatalA-s1of2" / "raw_responses.jsonl"
    s1_cache_a.parent.mkdir(parents=True, exist_ok=True)
    seed_record = {
        "round": 1,
        "subfield": "algorithms",
        "subfield_idx": 0,
        "request_system": "sys",
        "request_user": "usr",
        "response_text": json.dumps([f"seeded_concept_{i:03d}" for i in range(1, 41)]),
        "model_id": "Sonnet 5.5 Low",
        "token_usage": {},
        "timestamp_utc": "2026-10-11T00:00:00Z",
        "retries": 0,
        "latency_s": 0.01,
        "backend": "command",
        "prompt_version": "np1w",
        "backend_meta": {"thinking_requested": None, "profile_used": "login_required_p1"},
        "shard": "1/2",
    }
    s1_cache_a.write_text(json.dumps(seed_record) + "\n", encoding="utf-8")

    rc_a = supervisor_main([
        "--shards", "2",
        "--profiles", "login_required_p1,hang_p2",
        "--run-id-prefix", "fatalA",
        "--command", stub_cmd_a,
        "--target-names", "160",
        "--max-calls", "5",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir_a),
        "--lock-dir", str(lock_dir_a),
        "--output", str(tmp_path / "pool_a.json"),
        "--live",
        "--confirm",
    ])
    assert rc_a == SUP_EXIT_ERROR
    assert len(load_completed_cache(s1_cache_a)) == 1
    if child_pid_file_a.exists():
        cpid = int(child_pid_file_a.read_text(encoding="utf-8").strip())
        assert not _pid_is_alive(cpid)

    events_a = _read_jsonl(state_dir_a / "supervisor-log.jsonl")
    assert any(
        e["event"] == "supervisor_stop"
        and e.get("reason") == "fatal_or_unknown_shard_exit"
        and e.get("shard_exit_code") == 4
        for e in events_a
    )

    # Part B: Arbitrary unknown exit code 99 from a fake generator script while shard 2 is sleeping
    fake_gen = tmp_path / "fake_generator_99.py"
    shard2_pid_file = tmp_path / "shard2_sleep.pid"
    fake_gen.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, sys, time\n"
        "if '1/2' in sys.argv:\n"
        "    time.sleep(0.1)\n"
        "    sys.exit(99)\n"
        f"pathlib.Path({str(shard2_pid_file)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    state_dir_b = tmp_path / "state_unknown99"
    rc_b = supervisor_main([
        "--shards", "2",
        "--profiles", "Prof1,Prof2",
        "--run-id-prefix", "unk99",
        "--command", "true",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir_b),
        "--output", str(tmp_path / "pool_b.json"),
        "--generator-script", str(fake_gen),
        "--live",
        "--confirm",
    ])
    assert rc_b == SUP_EXIT_ERROR
    if shard2_pid_file.exists():
        s2_pid = int(shard2_pid_file.read_text(encoding="utf-8").strip())
        assert not _pid_is_alive(s2_pid)

    events_b = _read_jsonl(state_dir_b / "supervisor-log.jsonl")
    assert any(
        e["event"] == "supervisor_stop"
        and e.get("reason") == "fatal_or_unknown_shard_exit"
        and e.get("shard_exit_code") == 99
        for e in events_b
    )


def test_sigterm_propagation_kills_children_and_exits_130(tmp_path: Path) -> None:
    """6. SIGTERM propagation: send SIGTERM to supervisor while a shard's stub is sleeping ->
    child is dead and supervisor exits 130.
    """
    state_dir = tmp_path / "sup_sigterm"
    lock_dir = tmp_path / "locks_sigterm"
    child_pid_file = tmp_path / "grandchild.pid"
    stub_cmd = (
        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
        f"--child-pid-file {child_pid_file} --hang-seconds 30"
    )

    sup_proc = subprocess.Popen(
        [
            sys.executable,
            str(_SUPERVISOR_SCRIPT),
            "--shards", "1",
            "--profiles", "hang_p1",
            "--run-id-prefix", "sigtermrun",
            "--command", stub_cmd,
            "--target-names", "40",
            "--pause-s", "0",
            "--stagger-s", "0",
            "--poll-s", "0.05",
            "--state-dir", str(state_dir),
            "--lock-dir", str(lock_dir),
            "--output", str(tmp_path / "pool.json"),
            "--live",
            "--confirm",
        ],
        cwd=str(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait until the stub has spawned its child process and written grandchild.pid
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if child_pid_file.exists() and (state_dir / "status.json").exists():
            break
        time.sleep(0.05)

    assert child_pid_file.exists(), "Stub did not spawn child process before timeout"
    grandchild_pid = int(child_pid_file.read_text(encoding="utf-8").strip())
    status_before = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    shard_pid = status_before["shards"][0]["pid"]
    assert shard_pid is not None
    assert _pid_is_alive(shard_pid)
    assert _pid_is_alive(grandchild_pid)

    # Send SIGTERM to supervisor
    sup_proc.send_signal(signal.SIGTERM)
    sup_proc.wait(timeout=10.0)
    assert sup_proc.returncode == SUP_EXIT_SIGNAL  # 130

    # Both the shard process and its spawned child must be dead
    assert not _pid_is_alive(shard_pid)
    assert not _pid_is_alive(grandchild_pid)


def test_max_total_calls_stops_all_shards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """7. --max-total-calls exceeded -> supervisor stops all shards and exits non-zero."""
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_maxcalls"
    lock_dir = tmp_path / "locks_maxcalls"
    out_pool = tmp_path / "pool.json"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT} --hang-seconds 0.08"

    # 2 shards, each trying to collect 200 names (5 calls each), but --max-total-calls is 2
    rc = supervisor_main([
        "--shards", "2",
        "--profiles", "slow_success_p1,slow_success_p2",
        "--run-id-prefix", "maxcalls",
        "--command", stub_cmd,
        "--target-names", "400",
        "--max-calls", "10",
        "--max-total-calls", "2",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc == SUP_EXIT_MAX_TOTAL_CALLS
    assert not out_pool.exists()

    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    assert status["supervisor_state"] == "stopped_max_calls"
    assert status["total_calls"] >= 2

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    assert any(
        e["event"] == "max_total_calls_exceeded" and e["exit_code"] == SUP_EXIT_MAX_TOTAL_CALLS
        for e in events
    )


def test_status_cli_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """8. --status prints a table from status.json + caches and modifies nothing."""
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_status"
    lock_dir = tmp_path / "locks_status"
    out_pool = tmp_path / "pool.json"
    stub_cmd = f"{sys.executable} {_STUB_SCRIPT}"

    # Run a quick 1-shard run so status.json and cache exist
    rc_run = supervisor_main([
        "--shards", "1",
        "--profiles", "Profile_Status_1",
        "--run-id-prefix", "statustest",
        "--command", stub_cmd,
        "--target-names", "40",
        "--max-calls", "2",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(out_pool),
        "--live",
        "--confirm",
    ])
    assert rc_run == SUP_EXIT_OK
    capsys.readouterr()

    def _tree_digest(root: Path) -> dict[str, tuple[int, str]]:
        snap: dict[str, tuple[int, str]] = {}
        for p in sorted(root.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(root))
                snap[rel] = (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        return snap

    before_snap = _tree_digest(tmp_path)

    rc_status = supervisor_main(["--status", "--state-dir", str(state_dir)])
    assert rc_status == SUP_EXIT_OK

    captured = capsys.readouterr()
    assert "=== Name-Pool Supervisor Status" in captured.out
    assert "statustest-s1of1" in captured.out
    assert "Profile_Status_1" in captured.out
    assert "Total calls (cache lines): 1" in captured.out
    assert "Total deduplicated valid:  40" in captured.out

    after_snap = _tree_digest(tmp_path)
    assert before_snap == after_snap, "--status modified files in tmp_path!"


def test_refusal_without_live_and_confirm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """9a. Refusal without --live --confirm (exit 2) and creates nothing."""
    monkeypatch.chdir(tmp_path)
    base_args = [
        "--shards", "2",
        "--profiles", "Prof_1,Prof_2,Spare_3",
        "--run-id-prefix", "drytest",
        "--command", "prompt-adapter",
    ]

    assert supervisor_main(base_args) == SUP_EXIT_USAGE
    assert supervisor_main([*base_args, "--live"]) == SUP_EXIT_USAGE
    assert supervisor_main([*base_args, "--confirm"]) == SUP_EXIT_USAGE
    assert list(tmp_path.iterdir()) == []


def test_dry_run_prints_plan_and_launches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """9b. --dry-run prints the plan (shard commands, initial assignment, spares) and launches nothing."""
    monkeypatch.chdir(tmp_path)
    rc_dry = supervisor_main([
        "--shards", "2",
        "--profiles", "Prof_1,Prof_2,Spare_3",
        "--run-id-prefix", "drytest",
        "--command", "prompt-adapter",
        "--adapter-model", "sonnet",
        "--adapter-effort", "low",
        "--adapter-thinking", "off",
        "--dry-run",
    ])
    assert rc_dry == SUP_EXIT_OK
    out = capsys.readouterr().out
    assert "Initial profiles (1..N): Prof_1, Prof_2" in out
    assert "Spare profiles (1):      Spare_3" in out
    assert "unverified operator assumption" in out
    assert (
        "python3 scripts/generate_name_pool.py --backend command --command prompt-adapter "
        "--adapter-profile Prof_1 --adapter-model sonnet --adapter-effort low "
        "--adapter-thinking off --shard 1/2 --run-id drytest-s1of2 --live --confirm"
    ) in out
    assert (
        "python3 scripts/generate_name_pool.py --backend command --command prompt-adapter "
        "--adapter-profile Prof_2 --adapter-model sonnet --adapter-effort low "
        "--adapter-thinking off --shard 2/2 --run-id drytest-s2of2 --live --confirm"
    ) in out
    assert list(tmp_path.iterdir()) == []


def test_loader_value_error_stops_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """10. Loader ValueError (corrupt / conflicting cache lines mid-run) stops everything cleanly."""
    import threading

    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "sup_valerr"
    lock_dir = tmp_path / "locks_valerr"
    child_pid_file = tmp_path / "valerr_child.pid"
    stub_cmd = (
        f"{sys.executable} {_STUB_SCRIPT} --spawn-child "
        f"--child-pid-file {child_pid_file} --hang-seconds 30"
    )

    s1_cache = tmp_path / "results" / "datagen" / "valerr-s1of1" / "raw_responses.jsonl"
    rec1 = {
        "round": 1,
        "subfield": "algorithms",
        "subfield_idx": 0,
        "request_system": "s",
        "request_user": "u",
        "response_text": '["algo_concept_one"]',
        "model_id": "m",
        "token_usage": {},
        "timestamp_utc": "2026-10-11T00:00:00Z",
        "retries": 0,
        "latency_s": 0.1,
        "backend": "command",
        "prompt_version": "np1w",
    }
    rec2 = {
        **rec1,
        "subfield": "compilers",
        "subfield_idx": 2,
        "backend": "deepseek",
        "prompt_version": "np1",
    }

    def _inject_conflicting_cache_after_child_spawn() -> None:
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if child_pid_file.exists() and child_pid_file.read_text(encoding="utf-8").strip():
                break
            time.sleep(0.02)
        s1_cache.parent.mkdir(parents=True, exist_ok=True)
        s1_cache.write_text(
            json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n",
            encoding="utf-8",
        )

    injector = threading.Thread(target=_inject_conflicting_cache_after_child_spawn, daemon=True)
    injector.start()

    rc = supervisor_main([
        "--shards", "1",
        "--profiles", "hang_p1",
        "--run-id-prefix", "valerr",
        "--command", stub_cmd,
        "--target-names", "80",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir),
        "--lock-dir", str(lock_dir),
        "--output", str(tmp_path / "pool.json"),
        "--live",
        "--confirm",
    ])
    injector.join(timeout=5.0)
    assert rc == SUP_EXIT_ERROR

    assert child_pid_file.exists(), "Stub did not write child_pid_file before loader_error!"
    cpid = int(child_pid_file.read_text(encoding="utf-8").strip())
    assert not _pid_is_alive(cpid)

    events = _read_jsonl(state_dir / "supervisor-log.jsonl")
    assert any(
        e["event"] == "loader_error" and "mixed backends" in e.get("error", "")
        for e in events
    )


def test_live_adapter_flags_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """11. Live pass-through of --adapter-model, --adapter-effort, and --adapter-thinking
    reaches shard subprocesses, stdin payloads, cache backend_meta, and supervisor-log.jsonl.
    """
    monkeypatch.chdir(tmp_path)

    # Case A: primary generation settings (--adapter-model sonnet-5 --adapter-effort low --adapter-thinking off)
    state_dir_a = tmp_path / "sup_flags_a"
    lock_dir_a = tmp_path / "locks_flags_a"
    out_pool_a = tmp_path / "pool_a.json"
    payload_file_a = tmp_path / "payloads_a.jsonl"
    stub_cmd_a = f"{sys.executable} {_STUB_SCRIPT} --record-payload-file {payload_file_a}"

    rc_a = supervisor_main([
        "--shards", "2",
        "--profiles", "Prof_Flag_1,Prof_Flag_2",
        "--run-id-prefix", "flagpass",
        "--command", stub_cmd_a,
        "--adapter-model", "sonnet-5",
        "--adapter-effort", "low",
        "--adapter-thinking", "off",
        "--target-names", "120",
        "--max-calls", "5",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir_a),
        "--lock-dir", str(lock_dir_a),
        "--output", str(out_pool_a),
        "--live",
        "--confirm",
    ])
    assert rc_a == SUP_EXIT_OK

    payloads_a = _read_jsonl(payload_file_a)
    assert len(payloads_a) == 4
    for p in payloads_a:
        assert p["model"] == "sonnet-5"
        assert p["effort"] == "low"
        assert "thinking" in p
        assert p["thinking"] is False

    for rid in ("flagpass-s1of2", "flagpass-s2of2"):
        cpath = tmp_path / "results" / "datagen" / rid / "raw_responses.jsonl"
        crecs = _read_jsonl(cpath)
        assert len(crecs) == 2
        for rec in crecs:
            assert rec["backend_meta"]["thinking_requested"] is False
            assert rec["backend_meta"]["model_requested"] == "sonnet-5"
            assert rec["backend_meta"]["effort_requested"] == "low"

    events_a = _read_jsonl(state_dir_a / "supervisor-log.jsonl")
    launch_events_a = [e for e in events_a if e["event"] == "shard_launch"]
    assert len(launch_events_a) == 2
    for le in launch_events_a:
        assert "--adapter-thinking off" in le["command"]
        assert "--adapter-model sonnet-5" in le["command"]
        assert "--adapter-effort low" in le["command"]

    # Case B: non-default effort (--adapter-effort medium) so removing adapter_effort from
    # _launch_shard (where build_shard_cli_tokens defaults adapter_effort='low') is caught
    state_dir_b = tmp_path / "sup_flags_b"
    lock_dir_b = tmp_path / "locks_flags_b"
    out_pool_b = tmp_path / "pool_b.json"
    payload_file_b = tmp_path / "payloads_b.jsonl"
    stub_cmd_b = f"{sys.executable} {_STUB_SCRIPT} --record-payload-file {payload_file_b}"

    rc_b = supervisor_main([
        "--shards", "1",
        "--profiles", "Prof_Flag_Med",
        "--run-id-prefix", "flagmed",
        "--command", stub_cmd_b,
        "--adapter-model", "sonnet-5",
        "--adapter-effort", "medium",
        "--adapter-thinking", "off",
        "--target-names", "40",
        "--max-calls", "2",
        "--pause-s", "0",
        "--stagger-s", "0",
        "--poll-s", "0.05",
        "--state-dir", str(state_dir_b),
        "--lock-dir", str(lock_dir_b),
        "--output", str(out_pool_b),
        "--live",
        "--confirm",
    ])
    assert rc_b == SUP_EXIT_OK
    payloads_b = _read_jsonl(payload_file_b)
    assert len(payloads_b) == 1
    assert payloads_b[0]["model"] == "sonnet-5"
    assert payloads_b[0]["effort"] == "medium"
    assert payloads_b[0]["thinking"] is False
