"""tests/test_generate_name_pool.py — Unit and integration tests for DATA-004.

Tests verify:
  1. DeepSeekClient defaults (temperature 0.0, max_tokens 16) and custom parameter assignment.
  2. Offline-fake end-to-end generation produces a pool passing load_and_validate_names_file.
  3. All candidate drop reasons fire and track drop counts by reason.
  4. Resuming from cache makes zero new generator calls.
  5. Deterministic pool building (identical names and sha256 hashes given the same cache).
  6. --verify detects tampered names, tampered cache, and unallowed fake generator.
  7. Live mode gates refuse execution without --confirm and without DEEPSEEK_API_KEY.
  8. Offline-fake mode refuses to write the default tracked output path.
  9. --max-calls cap cleanly halts the generation loop.
 10. --build-only rebuilds and asserts load_and_validate_names_file UNCHANGED.
 11. --dry-run prints plan without creating files or making calls.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Generator
import uuid

import pytest

from graph_insertion.graph_representation import embed_text
from graph_insertion.llm import DeepSeekClient
from scripts.generate_name_pool import (
    CacheEntry,
    DEFAULT_TRACKED_OUTPUT,
    MIN_REQUIRED_NAMES_FOR_VALIDATION,
    NAME_POOL_PROMPT_VERSION,
    NAME_POOL_PROMPT_VERSION_COMMAND,
    SUBFIELDS,
    SYSTEM_PROMPT,
    build_command_prompt,
    build_pool_from_cache,
    build_user_prompt,
    load_completed_cache,
    main as cli_main,
    parse_json_array_response,
    run_generation_loop,
    slugify_profile,
    validate_and_dedupe_candidates,
    verify_pool,
)
from scripts.run_experiment import load_and_validate_names_file


@pytest.fixture(scope="module", autouse=True)
def guard_results_datagen_unmodified() -> Generator[None, None, None]:
    """Module-scoped autouse fixture that snapshots the full recursive relative-path
    state of results/datagen before test execution and asserts exact equality after.
    Guarantees that no test in this module creates stray files or directories in results/datagen.
    """
    datagen_dir = Path("results/datagen")

    def _snapshot() -> set[str] | None:
        if not datagen_dir.exists():
            return None
        items: set[str] = set()
        for root, dirs, files in os.walk(datagen_dir):
            for d in dirs:
                items.add(os.path.relpath(os.path.join(root, d), datagen_dir))
            for f in files:
                items.add(os.path.relpath(os.path.join(root, f), datagen_dir))
        return items

    before = _snapshot()
    yield
    # Clean up any default timestamped directories created in results/datagen by CLI tests that did not specify --run-id
    if datagen_dir.exists():
        for p in datagen_dir.iterdir():
            if p.is_dir() and len(p.name) == 16 and p.name.endswith("Z") and "_" in p.name:
                shutil.rmtree(p, ignore_errors=True)
    after = _snapshot()
    assert after == before, (
        f"results/datagen was modified by tests in test_generate_name_pool!\n"
        f"Added: {after - before if (after and before) else after}\n"
        f"Removed: {before - after if (after and before) else before}"
    )


# ---------------------------------------------------------------------------
# 1. DeepSeekClient Defaults & Parameter Extension
# ---------------------------------------------------------------------------

def test_deepseek_client_defaults_and_custom_parameters() -> None:
    """Verify DeepSeekClient defaults (temp 0.0, max_tokens 16) and custom kwargs."""
    # Defaults
    c_default = DeepSeekClient(api_key="fake-key-for-test")
    assert c_default.temperature == 0.0
    assert c_default.max_tokens == 16
    assert c_default.thinking == {"type": "disabled"}

    # Custom kwargs for name generation
    c_custom = DeepSeekClient(
        api_key="fake-key-for-test",
        temperature=0.7,
        max_tokens=1500,
    )
    assert c_custom.temperature == 0.7
    assert c_custom.max_tokens == 1500


# ---------------------------------------------------------------------------
# 2. Prompt Construction & Parsing
# ---------------------------------------------------------------------------

def test_build_user_prompt_round1_and_round2() -> None:
    """Verify user prompt generation for round 1 and round 2 with collected names cap."""
    p1 = build_user_prompt("data_structures", 1, [])
    assert "data structures" in p1
    assert "40 distinct" in p1
    assert "Do NOT repeat" not in p1

    prev = [f"concept_{i}" for i in range(120)]
    p2 = build_user_prompt("data_structures", 2, prev)
    assert "Do NOT repeat any of the following 100 concepts" in p2
    assert "concept_119" in p2
    # Ensure capped to last 100 names
    assert "concept_0" not in p2


def test_parse_json_array_response() -> None:
    """Verify response parsing with and without markdown code fences."""
    raw_plain = json.dumps(["b_tree", "avl_tree"])
    assert parse_json_array_response(raw_plain) == ["b_tree", "avl_tree"]

    raw_fenced = "```json\n" + json.dumps(["b_tree", "avl_tree"]) + "\n```"
    assert parse_json_array_response(raw_fenced) == ["b_tree", "avl_tree"]

    with pytest.raises(ValueError, match="Expected JSON array"):
        parse_json_array_response(json.dumps({"concepts": ["b_tree"]}))

    with pytest.raises(ValueError, match="Failed to parse response as JSON"):
        parse_json_array_response("invalid non json text")


# ---------------------------------------------------------------------------
# 3. Candidate Validation & Drop Reasons
# ---------------------------------------------------------------------------

def test_drop_reasons_fire() -> None:
    """Verify that every drop reason fires and increments drop_counts accurately."""
    corpus_nodes = {"binary_search_tree", "sorting_algorithm"}
    corpus_embeds = {
        embed_text("binary_search_tree"),
        embed_text("sorting_algorithm"),
        "unusual concept payload",
    }

    candidates = [
        "graph_theory.txt",                 # ends_with_txt
        "InvalidCase",                      # invalid_snake_case
        "ab",                               # invalid_length (< 3)
        "a" * 55,                           # invalid_length (> 50)
        "one_two_three_four_five_six",      # invalid_word_count (> 5 words)
        "binary_search_tree",               # corpus_overlap_exact
        "sorting_algorithm",                # corpus_overlap_exact
        "unusual_concept_payload",          # corpus_overlap_embed
        "accepted_concept_one",             # valid 1
        "accepted_concept_one",             # duplicate_exact
        "accepted_concept_two",             # valid 2
        "decision_tree",                    # valid 3
        "decision_trees",                   # plural_pair (with decision_tree)
        "process",                          # valid 4
        "processes",                        # plural_pair (with process)
    ]

    fake_entry = CacheEntry(
        round=1,
        subfield="test_field",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(candidates),
        model_id="test-model",
        token_usage={},
        timestamp_utc="2026-10-07T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=candidates,
    )

    filtered, n_raw, drop_counts = validate_and_dedupe_candidates(
        [fake_entry], corpus_nodes, corpus_embeds
    )

    assert n_raw == len(candidates)
    assert drop_counts["ends_with_txt"] == 1
    assert drop_counts["invalid_snake_case"] == 1
    assert drop_counts["invalid_length"] == 2
    assert drop_counts["invalid_word_count"] == 1
    assert drop_counts["corpus_overlap_exact"] == 2
    assert drop_counts["corpus_overlap_embed"] == 1
    assert drop_counts["duplicate_exact"] == 1
    assert drop_counts["plural_pair"] == 2

    # Verify surviving valid concepts
    assert "accepted_concept_one" in filtered
    assert "accepted_concept_two" in filtered
    assert "decision_tree" in filtered
    assert "decision_trees" not in filtered
    assert "process" in filtered
    assert "processes" not in filtered
    assert "unusual_concept_payload" not in filtered


def test_corpus_overlap_embed_drop_reason() -> None:
    """Verify candidate dropping when embed_text form matches a corpus node."""
    # Suppose corpus has an unusual node
    corpus_nodes: set[str] = set()
    corpus_embeds = {"custom concept payload"}

    # Candidate has same embed_text form
    candidate = "custom_concept_payload"
    assert embed_text(candidate) == "custom concept payload"

    fake_entry = CacheEntry(
        round=1,
        subfield="test_field",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps([candidate]),
        model_id="test-model",
        token_usage={},
        timestamp_utc="2026-10-07T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=[candidate],
    )

    filtered, n_raw, drop_counts = validate_and_dedupe_candidates(
        [fake_entry], corpus_nodes, corpus_embeds
    )
    assert drop_counts["corpus_overlap_embed"] == 1
    assert len(filtered) == 0


# ---------------------------------------------------------------------------
# 4. Offline-Fake End-to-End & Load Validation
# ---------------------------------------------------------------------------

def test_offline_fake_e2e_passes_load_and_validate_names_file(tmp_path: Path) -> None:
    """End-to-end test: offline-fake generates pool passing load_and_validate_names_file."""
    pool_path = tmp_path / "synthetic_pool.json"
    cache_path = tmp_path / "raw_responses.jsonl"

    ret = run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="test_e2e_run",
        target_names=2600,
        max_calls=400,
    )
    assert ret == 0
    assert pool_path.exists()
    assert cache_path.exists()

    # Must pass load_and_validate_names_file unchanged
    loaded = load_and_validate_names_file(pool_path, min_required_names=2001)
    assert len(loaded) >= 2600

    # Verify JSON structure and metadata
    with open(pool_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    assert meta["schema_version"] == "1.0"
    assert meta["domain"] == "computer science"
    assert meta["generator"] == "offline-fake"
    assert meta["prompt_version"] == "np1"
    assert meta["seed"] == 42
    assert meta["n_valid"] == len(loaded)
    assert len(meta["corpora_checked"]) == 12


# ---------------------------------------------------------------------------
# 5. Cache Resumption & Determinism
# ---------------------------------------------------------------------------

def test_resume_from_cache_makes_zero_new_calls(tmp_path: Path) -> None:
    """Verify that re-running with an existing cache makes 0 new generator calls."""
    pool_path = tmp_path / "pool.json"
    cache_path = tmp_path / "raw.jsonl"

    # First run creates cache
    ret1 = run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="run_1",
        target_names=2600,
        max_calls=400,
    )
    assert ret1 == 0

    cache1 = load_completed_cache(cache_path)
    entries_count1 = len(cache1)

    # Second run with same cache
    pool_path2 = tmp_path / "pool2.json"
    ret2 = run_generation_loop(
        mode="offline-fake",
        output_path=pool_path2,
        cache_path=cache_path,
        run_id="run_1",
        target_names=2600,
        max_calls=400,
    )
    assert ret2 == 0

    cache2 = load_completed_cache(cache_path)
    assert len(cache2) == entries_count1


def test_deterministic_output_from_cache(tmp_path: Path) -> None:
    """Verify identical pool content and hashes when built from the same cache."""
    cache_path = tmp_path / "raw.jsonl"
    out1 = tmp_path / "pool1.json"
    out2 = tmp_path / "pool2.json"

    run_generation_loop(
        mode="offline-fake",
        output_path=out1,
        cache_path=cache_path,
        run_id="det_run",
        target_names=2600,
        max_calls=400,
    )

    build_pool_from_cache(
        cache_path=cache_path,
        output_path=out2,
        generator_kind="offline-fake",
        configured_model="deepseek-flash",
        seed=42,
        run_ids=["det_run"],
        allow_fake=True,
    )

    with open(out1, "r", encoding="utf-8") as f:
        d1 = json.load(f)
    with open(out2, "r", encoding="utf-8") as f:
        d2 = json.load(f)

    assert d1["names"] == d2["names"]
    assert d1["meta"]["sha256_names"] == d2["meta"]["sha256_names"]
    assert d1["meta"]["sha256_raw_responses"] == d2["meta"]["sha256_raw_responses"]


# ---------------------------------------------------------------------------
# 6. Verification Mode & Tamper Detection
# ---------------------------------------------------------------------------

def test_verify_detects_tampered_name(tmp_path: Path) -> None:
    """Verify that --verify detects a tampered name string."""
    pool_path = tmp_path / "pool.json"
    cache_path = tmp_path / "raw.jsonl"

    run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="verify_test",
        target_names=2600,
        max_calls=400,
    )

    # Valid check passes with allow_fake
    verify_pool(pool_path, cache_path, allow_fake=True)

    # Tamper with a name
    with open(pool_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["names"][0] = "tampered_concept_name"
    with open(pool_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(SystemExit) as exc:
        verify_pool(pool_path, cache_path, allow_fake=True)
    assert exc.value.code == 1


def test_verify_detects_tampered_cache(tmp_path: Path) -> None:
    """Verify that --verify detects cache tampering via SHA256 mismatch."""
    pool_path = tmp_path / "pool.json"
    cache_path = tmp_path / "raw.jsonl"

    run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="verify_test",
        target_names=2600,
        max_calls=400,
    )

    # Tamper with raw cache file
    with open(cache_path, "a", encoding="utf-8") as f:
        f.write('{"tampered": true}\n')

    with pytest.raises(SystemExit) as exc:
        verify_pool(pool_path, cache_path, allow_fake=True)
    assert exc.value.code == 1


def test_verify_detects_offline_fake_without_allow_fake(tmp_path: Path) -> None:
    """Verify that --verify rejects offline-fake generated pools unless --allow-fake is passed."""
    pool_path = tmp_path / "pool.json"
    cache_path = tmp_path / "raw.jsonl"

    run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="verify_test",
        target_names=2600,
        max_calls=400,
    )

    with pytest.raises(SystemExit) as exc:
        verify_pool(pool_path, cache_path, allow_fake=False)
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# 7. Live Mode Gates & Safety Limits
# ---------------------------------------------------------------------------

def test_live_mode_refuses_without_confirm_and_without_key(tmp_path: Path) -> None:
    """Verify live mode refusal without --confirm and without DEEPSEEK_API_KEY."""
    script = str(Path("scripts/generate_name_pool.py").resolve())

    # Without --confirm
    res1 = subprocess.run(
        [sys.executable, script, "--live"],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 1
    assert "confirm" in res1.stderr

    # With --confirm but missing API key
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    res2 = subprocess.run(
        [sys.executable, script, "--live", "--confirm", "--allow-peak"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res2.returncode == 1
    assert "DEEPSEEK_API_KEY" in res2.stderr
    assert "Traceback" not in res2.stderr


def test_offline_fake_refuses_default_output_path() -> None:
    """Verify offline-fake refuses to overwrite default tracked path data/synthetic/cs_concept_names.json."""
    script = str(Path("scripts/generate_name_pool.py").resolve())

    res = subprocess.run(
        [sys.executable, script, "--offline-fake"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "default tracked path" in res.stderr


def test_max_calls_stops_loop(tmp_path: Path) -> None:
    """Verify that --max-calls cleanly stops the generation loop."""
    pool_path = tmp_path / "pool.json"
    cache_path = tmp_path / "raw.jsonl"

    ret = run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="cap_test",
        target_names=5000,
        max_calls=5,
    )
    assert ret == 0
    cache = load_completed_cache(cache_path)
    assert len(cache) == 5


# ---------------------------------------------------------------------------
# 8. Build-Only and Dry-Run CLI Subcommands
# ---------------------------------------------------------------------------

def test_build_only_cli_execution(tmp_path: Path) -> None:
    """Verify --build-only subcommand loads cache and validates output UNCHANGED."""
    script = str(Path("scripts/generate_name_pool.py").resolve())
    pool_path = tmp_path / "pool.json"
    rebuilt_path = tmp_path / "rebuilt.json"
    cache_path = tmp_path / "raw.jsonl"

    # Generate initial cache
    run_generation_loop(
        mode="offline-fake",
        output_path=pool_path,
        cache_path=cache_path,
        run_id="bo_test",
        target_names=2600,
        max_calls=400,
    )

    # Rebuild
    res = subprocess.run(
        [
            sys.executable,
            script,
            "--build-only",
            "--cache-file",
            str(cache_path),
            "--output",
            str(rebuilt_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "verified UNCHANGED" in res.stdout
    assert rebuilt_path.exists()


def test_dry_run_cli_execution() -> None:
    """Verify --dry-run prints plan and cost estimate without creating files."""
    script = str(Path("scripts/generate_name_pool.py").resolve())

    res = subprocess.run(
        [sys.executable, script, "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Dry run complete" in res.stdout
    assert "Estimated round 1 cost" in res.stdout


# ---------------------------------------------------------------------------
# 9. DATA-005 Command Backend & Prompt Adapter Tests
# ---------------------------------------------------------------------------

def test_command_prompt_composition() -> None:
    """Verify build_command_prompt pure function composition (np1w)."""
    p1 = build_command_prompt("algorithms", 1, [])
    expected1 = f"{SYSTEM_PROMPT}\n\n{build_user_prompt('algorithms', 1, [])}"
    assert p1 == expected1
    assert NAME_POOL_PROMPT_VERSION_COMMAND == "np1w"

    prev = ["merge_sort", "quick_sort"]
    p2 = build_command_prompt("algorithms", 2, prev)
    expected2 = f"{SYSTEM_PROMPT}\n\n{build_user_prompt('algorithms', 2, prev)}"
    assert p2 == expected2


def test_parse_json_array_response_fallback() -> None:
    """Verify parser fallback on fenced and prose-wrapped responses."""
    # Fenced array
    fenced = "```json\n[\"b_tree\", \"avl_tree\"]\n```"
    assert parse_json_array_response(fenced) == ["b_tree", "avl_tree"]

    # Prose wrapped plain array
    prose_plain = "Here are the concept names: [\"b_tree\", \"avl_tree\"]. Hope this helps!"
    assert parse_json_array_response(prose_plain) == ["b_tree", "avl_tree"]

    # Prose wrapped with markdown code fences
    prose_fenced = (
        "Sure, here is the list:\n```json\n[\"b_tree\", \"avl_tree\"]\n```\nEnjoy!"
    )
    assert parse_json_array_response(prose_fenced) == ["b_tree", "avl_tree"]

    # Prose with dictionary containing array (must fail strict parse and not extract dict)
    with pytest.raises(ValueError, match="Expected JSON array"):
        parse_json_array_response('{"concepts": ["b_tree"]}')

    # Prose without any array -> ValueError
    with pytest.raises(ValueError, match="Failed to parse response as JSON"):
        parse_json_array_response("I cannot fulfill this request because it violates policy.")

    # Prose with malformed array -> ValueError
    with pytest.raises(ValueError, match="Failed to parse response as JSON"):
        parse_json_array_response("Here is the array: [b_tree, avl_tree]")


def test_command_backend_live_gating() -> None:
    """Verify command backend CLI gates require --confirm, --command, and --adapter-profile."""
    script = str(Path("scripts/generate_name_pool.py").resolve())

    # Live without confirm
    res1 = subprocess.run(
        [sys.executable, script, "--live", "--backend", "command"],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 1
    assert "confirm" in res1.stderr

    # Live with confirm but missing --command
    res2 = subprocess.run(
        [sys.executable, script, "--live", "--confirm", "--backend", "command"],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1
    assert "--command is required" in res2.stderr
    assert "Traceback" not in res2.stderr

    # Live with confirm and --command but missing --adapter-profile
    res3 = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            "python3 tests/stub_prompt_adapter.py",
        ],
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 1
    assert "--adapter-profile is required" in res3.stderr
    assert "Traceback" not in res3.stderr


def test_command_backend_dry_run() -> None:
    """Verify command backend --dry-run prints duration estimate and memory reminder."""
    script = str(Path("scripts/generate_name_pool.py").resolve())

    res = subprocess.run(
        [sys.executable, script, "--dry-run", "--backend", "command"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Command Backend" in res.stdout
    assert "@ 40.0s/call" in res.stdout
    assert "Generate memory from chats" in res.stdout


def test_command_backend_success_e2e(tmp_path: Path) -> None:
    """End-to-end integration test of CommandBackend with stub adapter success."""
    script = str(Path("scripts/generate_name_pool.py").resolve())
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    pool_path = tmp_path / "claude_pool.json"
    cache_path = tmp_path / "raw.jsonl"

    cmd_str = f"{sys.executable} {stub} --scenario success"
    res = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            cmd_str,
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--target-names",
            "80",
            "--max-calls",
            "5",
            "--output",
            str(pool_path),
            "--cache-file",
            str(cache_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert pool_path.exists()
    assert cache_path.exists()

    with open(pool_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    assert meta["generator"] == "claude-web-ui-via-prompt-adapter"
    assert meta["prompt_version"] == "np1w"
    assert meta["requested_model"] == "sonnet"
    assert meta["requested_effort"] == "low"
    assert meta["requested_memory"] is False
    assert meta["requested_web_search"] is False
    assert "Sonnet 5.5 Low" in meta["observed_models"]
    assert "1" in meta["tier_histogram"]
    assert "1.0.0" in meta["adapter_versions"]
    assert meta["temperature"] is None
    assert meta["max_tokens"] is None
    assert meta["n_valid"] >= 80

    # Passes load_and_validate_names_file
    loaded = load_and_validate_names_file(pool_path, min_required_names=80)
    assert len(loaded) >= 80


def test_command_backend_error_codes(tmp_path: Path) -> None:
    """Verify CommandBackend stops with specific exit codes on adapter error outcomes."""
    script = str(Path("scripts/generate_name_pool.py").resolve())
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    lock_dir = tmp_path / "locks"

    # 1. Rate limit (error 10) -> exit 3
    res_rl = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            f"{sys.executable} {stub} --scenario rate_limit",
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--output",
            str(tmp_path / "p1.json"),
            "--cache-file",
            str(tmp_path / "c1.jsonl"),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_rl.returncode == 3
    assert "Rate limit reached" in res_rl.stderr
    assert "Reset time:" in res_rl.stderr

    # 2. Login required (error 11) -> exit 4
    res_lr = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            f"{sys.executable} {stub} --scenario login_required",
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--output",
            str(tmp_path / "p2.json"),
            "--cache-file",
            str(tmp_path / "c2.jsonl"),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_lr.returncode == 4
    assert "Login/challenge required" in res_lr.stderr

    # 3. Model mismatch (error 14) -> exit 5
    res_mm = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            f"{sys.executable} {stub} --scenario model_mismatch",
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--output",
            str(tmp_path / "p3.json"),
            "--cache-file",
            str(tmp_path / "c3.jsonl"),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_mm.returncode == 5
    assert "Model mismatch" in res_mm.stderr

    # 4. Bad request (error 2) -> exit 1
    res_br = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            f"{sys.executable} {stub} --scenario bad_request",
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--output",
            str(tmp_path / "p4.json"),
            "--cache-file",
            str(tmp_path / "c4.jsonl"),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_br.returncode == 1

    # 5. Three consecutive failures (timeout, refusal, other, or garbage) -> exit 6
    for sc in ("timeout", "refusal", "other", "garbage", "unparseable"):
        res_fail = subprocess.run(
            [
                sys.executable,
                script,
                "--live",
                "--confirm",
                "--backend",
                "command",
                "--command",
                f"{sys.executable} {stub} --scenario {sc}",
                "--adapter-profile",
                "test_prof",
                "--pause-s",
                "0",
                "--output",
                str(tmp_path / f"p_{sc}.json"),
                "--cache-file",
                str(tmp_path / f"c_{sc}.jsonl"),
                "--lock-dir",
                str(lock_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert res_fail.returncode == 6, f"Expected exit 6 for scenario {sc}, got {res_fail.returncode}"
        assert "3 consecutive failures encountered" in res_fail.stderr


def test_command_backend_hang_timeout(tmp_path: Path) -> None:
    """Verify CommandBackend kills a hanging subprocess and exits 6 after 3 timeouts."""
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    from scripts.generate_name_pool import CommandGenerationBackend
    backend = CommandGenerationBackend(
        command=f"{sys.executable} {stub} --scenario hang",
        profile="test_prof",
        timeout_s=-59,  # timeout_s + 60 = 1 second
    )
    res = backend.complete(
        subfield="algorithms",
        round_num=1,
        previous_names=[],
        system_prompt="",
        user_prompt="",
    )
    assert res.ok is False
    assert res.error_code == 12
    assert "timed out" in res.error_message


def test_stop_and_resume_after_rate_limit(tmp_path: Path) -> None:
    """Verify stop on rate limit preserves cache and resuming makes zero repeated calls."""
    script = str(Path("scripts/generate_name_pool.py").resolve())
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    state_file = tmp_path / "state.txt"
    cache_path = tmp_path / "raw.jsonl"
    pool_path = tmp_path / "pool.json"

    cmd1 = f"{sys.executable} {stub} --scenario rate_limit_after_n --state-file {state_file} --limit-n 2"

    # Run 1: completes 2 calls then hits rate limit on 3rd call
    res1 = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            cmd1,
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--target-names",
            "120",
            "--max-calls",
            "10",
            "--output",
            str(pool_path),
            "--cache-file",
            str(cache_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 3
    assert cache_path.exists()

    cache1 = load_completed_cache(cache_path)
    assert len(cache1) == 2
    completed_pairs = set(cache1.keys())

    # Run 2: resume with success scenario
    cmd2 = f"{sys.executable} {stub} --scenario success"
    res2 = subprocess.run(
        [
            sys.executable,
            script,
            "--live",
            "--confirm",
            "--backend",
            "command",
            "--command",
            cmd2,
            "--adapter-profile",
            "test_prof",
            "--pause-s",
            "0",
            "--target-names",
            "120",
            "--max-calls",
            "10",
            "--output",
            str(pool_path),
            "--cache-file",
            str(cache_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 0
    assert pool_path.exists()

    cache2 = load_completed_cache(cache_path)
    assert len(cache2) > len(cache1)
    # The first 2 pairs must retain their original timestamps and parsed names unchanged
    for pair in completed_pairs:
        assert cache2[pair].timestamp_utc == cache1[pair].timestamp_utc
        assert cache2[pair].parsed_names == cache1[pair].parsed_names


def test_mixed_cache_refusal(tmp_path: Path) -> None:
    """Verify load_completed_cache raises ValueError when cache mixes backends or prompt versions."""
    cache_path = tmp_path / "mixed.jsonl"

    # 1. Mixed backends
    rec1 = {
        "round": 1,
        "subfield": "algorithms",
        "subfield_idx": 0,
        "request_system": "",
        "request_user": "",
        "response_text": json.dumps(["a", "b"]),
        "model_id": "test",
        "token_usage": {},
        "timestamp_utc": "2026-10-07T00:00:00Z",
        "retries": 0,
        "latency_s": 0.1,
        "backend": "deepseek",
        "prompt_version": "np1",
    }
    rec2 = {
        "round": 1,
        "subfield": "data_structures",
        "subfield_idx": 1,
        "request_system": "",
        "request_user": "",
        "response_text": json.dumps(["c", "d"]),
        "model_id": "test",
        "token_usage": {},
        "timestamp_utc": "2026-10-07T00:00:01Z",
        "retries": 0,
        "latency_s": 0.1,
        "backend": "command",
        "prompt_version": "np1w",
    }
    cache_path.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mixed backends"):
        load_completed_cache(cache_path)

    # 2. Mixed prompt versions with same backend
    rec2_same_be = dict(rec2)
    rec2_same_be["backend"] = "deepseek"
    cache_path.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2_same_be) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mixed prompt versions"):
        load_completed_cache(cache_path)


def test_contract_doc_fixtures_subprocess_execution(tmp_path: Path) -> None:
    """Verify exact fixtures from prompt-adapter-contract.md use string codes and pass subprocess path."""
    contract_path = Path("docs/context/prompt-adapter-contract.md")
    assert contract_path.exists(), "Contract document missing"
    content = contract_path.read_text(encoding="utf-8")

    # Extract all json code blocks under Example Responses
    example_section = content.split("### Example Responses (`stdout`)")[1]
    json_blocks = re.findall(r"```json\n(.*?)\n```", example_section, re.DOTALL)
    assert len(json_blocks) == 9, f"Expected 9 response fixtures, found {len(json_blocks)}"

    expected_codes = {
        "rate_limit": 10,
        "login_required": 11,
        "model_mismatch": 14,
        "profile_in_use": 15,
        "timeout": 12,
        "refusal": 13,
        "bad_request": 2,
        "other": 1,
    }

    from scripts.generate_name_pool import CommandGenerationBackend, parse_json_array_response

    for raw_json in json_blocks:
        parsed = json.loads(raw_json)
        is_success = parsed.get("ok") is True

        if is_success:
            exit_code = 0
            # Test success fixture
            runner_script = tmp_path / "runner_success.py"
            runner_script.write_text(
                f"import sys\nsys.stdout.write({json.dumps(raw_json)})\nsys.exit(0)\n",
                encoding="utf-8",
            )
            backend = CommandGenerationBackend(
                command=f"{sys.executable} {runner_script}",
                profile="test_prof",
            )
            res = backend.complete(
                subfield="algorithms",
                round_num=1,
                previous_names=[],
                system_prompt="",
                user_prompt="",
            )
            assert res.ok is True
            assert res.model_id == "Sonnet 5.5 Low"
            assert res.backend_meta.get("profile_used") == "Profile 24"
            concepts = parse_json_array_response(res.text)
            assert len(concepts) == 4
            assert "binary_search" in concepts
        else:
            err_str = parsed.get("error")
            # Verify the contract doc's failure fixture strictly uses a string code
            assert isinstance(err_str, str), f"Fixture error must be string, got {err_str!r}"
            assert err_str in expected_codes, f"Unknown fixture error string: {err_str}"
            exit_code = expected_codes[err_str]

            runner_script = tmp_path / f"runner_{err_str}.py"
            runner_script.write_text(
                f"import sys\nsys.stdout.write({json.dumps(raw_json)})\nsys.exit({exit_code})\n",
                encoding="utf-8",
            )
            backend = CommandGenerationBackend(
                command=f"{sys.executable} {runner_script}",
                profile="test_prof",
            )
            res = backend.complete(
                subfield="algorithms",
                round_num=1,
                previous_names=[],
                system_prompt="",
                user_prompt="",
            )
            assert res.ok is False
            assert res.error_code == exit_code
            assert res.error_message == parsed.get("message")
            if err_str == "rate_limit":
                assert res.reset_time == "2026-10-07T23:00:00Z"

    # Test exit code fallback when stdout has no usable error or is non-JSON
    # 1. Stdout has {"ok": false, "message": "..."} without error field -> exit code fallback
    no_err_script = tmp_path / "runner_no_err_key.py"
    no_err_script.write_text(
        "import sys, json\nprint(json.dumps({'ok': False, 'message': 'missing error key'}))\nsys.exit(10)\n",
        encoding="utf-8",
    )
    b_no_err = CommandGenerationBackend(command=f"{sys.executable} {no_err_script}", profile="prof")
    r_no_err = b_no_err.complete(subfield="a", round_num=1, previous_names=[], system_prompt="", user_prompt="")
    assert r_no_err.ok is False
    assert r_no_err.error_code == 10

    # 2. Stdout is non-JSON garbage with exit code 11 -> exit code fallback
    garbage_script = tmp_path / "runner_garbage.py"
    garbage_script.write_text("import sys\nsys.stdout.write('Fatal crash\\n')\nsys.exit(11)\n", encoding="utf-8")
    b_garbage = CommandGenerationBackend(command=f"{sys.executable} {garbage_script}", profile="prof")
    r_garbage = b_garbage.complete(subfield="a", round_num=1, previous_names=[], system_prompt="", user_prompt="")
    assert r_garbage.ok is False
    assert r_garbage.error_code == 11

    # 3. Stdout has unknown string error -> error_code 1
    unknown_script = tmp_path / "runner_unknown.py"
    unknown_script.write_text(
        "import sys, json\nprint(json.dumps({'ok': False, 'error': 'custom_unrecognized_code'}))\nsys.exit(1)\n",
        encoding="utf-8",
    )
    b_unknown = CommandGenerationBackend(command=f"{sys.executable} {unknown_script}", profile="prof")
    r_unknown = b_unknown.complete(subfield="a", round_num=1, previous_names=[], system_prompt="", user_prompt="")
    assert r_unknown.ok is False
    assert r_unknown.error_code == 1


def test_command_backend_process_group_timeout_kills_child(tmp_path: Path) -> None:
    """Verify CommandBackend uses process group session to terminate hung process and its spawned children."""
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    child_pid_file = tmp_path / "child.pid"

    from scripts.generate_name_pool import CommandGenerationBackend

    # 1. Normal SIGTERM termination of process group
    stub_cmd = (
        f"{sys.executable} {stub} --scenario hang --spawn-child "
        f"--child-pid-file {child_pid_file} --hang-seconds 30"
    )
    backend = CommandGenerationBackend(
        command=stub_cmd,
        profile="test_prof",
        timeout_s=-59,  # timeout_s + 60 = 1.0 second timeout limit
        sigterm_wait_s=5.0,
    )
    res = backend.complete(
        subfield="algorithms",
        round_num=1,
        previous_names=[],
        system_prompt="",
        user_prompt="",
    )
    assert res.ok is False
    assert res.error_code == 12
    assert "timed out" in res.error_message

    assert child_pid_file.exists(), "Child PID file was not created by stub"
    child_pid = int(child_pid_file.read_text(encoding="utf-8").strip())

    time.sleep(0.1)
    child_alive = True
    try:
        os.kill(child_pid, 0)
    except ProcessLookupError:
        child_alive = False
    assert not child_alive, f"Child process {child_pid} was not terminated on process-group timeout!"

    # 2. SIGKILL escalation when child ignores SIGTERM
    ign_script = tmp_path / "ign_sigterm.py"
    ign_script.write_text(
        "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    backend_ign = CommandGenerationBackend(
        command=f"{sys.executable} {ign_script}",
        profile="test_prof",
        timeout_s=-59,  # 1.0s timeout
        sigterm_wait_s=0.2,  # brief wait before SIGKILL
    )
    res_ign = backend_ign.complete(
        subfield="algorithms",
        round_num=1,
        previous_names=[],
        system_prompt="",
        user_prompt="",
    )
    assert res_ign.ok is False
    assert res_ign.error_code == 12


# ===========================================================================
# 11. FIX-013 Shard & Merge Tests (Partition, Byte-Identical, Locks, Cli, Timeout)
# ===========================================================================

def test_shard_partition_disjoint_and_union() -> None:
    """Verify that for N in {1, 2, 3, 5, 14}, the union of shards 1..N covers
    every global subfield index exactly once, with no overlap, and that
    parse_shard_arg rejects invalid specifications.
    """
    from scripts.generate_name_pool import SUBFIELDS, get_shard_subfields, parse_shard_arg

    total = len(SUBFIELDS)
    for n in (1, 2, 3, 5, 14):
        seen_indices: list[int] = []
        seen_subfields: list[str] = []
        for i in range(1, n + 1):
            sfs = get_shard_subfields(i, n)
            for idx, sf in sfs:
                seen_indices.append(idx)
                seen_subfields.append(sf)
        # Covers every global subfield index and name exactly once
        assert len(seen_indices) == total
        assert sorted(seen_indices) == list(range(total))
        assert len(seen_subfields) == total
        assert set(seen_subfields) == set(SUBFIELDS)
        assert len(set(seen_subfields)) == total

    # Rejection of invalid shard specs
    for bad in ("0/3", "4/3", "a/b", "1/0", "2", "1/2/3", "-1/3", "3/0"):
        with pytest.raises(ValueError):
            parse_shard_arg(bad)


def test_byte_identical_merge_n1_vs_n3_and_reversed(tmp_path: Path) -> None:
    """Build one synthetic record set (mixed rounds and subfields).
    Build the pool:
      (a) from one cache file,
      (b) from the same records split into 3 shard caches,
      (c) from the 3 shard caches with the run-ID list reversed.
    Assert that names and meta.sha256_names are identical in all three.

    Scope of 'identical':
    The assertion of identity strictly covers the ordered list of validated concept
    names and its cryptographic digest meta['sha256_names']. Run-specific metadata
    such as run_ids, per-shard summaries, and timestamps reflect individual execution
    contexts and are excluded from the byte-for-byte identity check.
    """
    from scripts.generate_name_pool import (
        SUBFIELDS,
        CacheEntry,
        append_cache_record,
        build_pool_from_cache,
    )

    subfields_sample = [SUBFIELDS[0], SUBFIELDS[1], SUBFIELDS[2]]
    entries: list[CacheEntry] = []

    for round_num in (1, 2):
        for sf_idx, sf in enumerate(subfields_sample):
            names = [f"synth_{sf}_r{round_num}_item_{k:02d}" for k in range(10)]
            entries.append(
                CacheEntry(
                    round=round_num,
                    subfield=sf,
                    subfield_idx=sf_idx,
                    request_system="sys",
                    request_user="user",
                    response_text=json.dumps(names),
                    model_id="test-model",
                    token_usage={},
                    timestamp_utc=f"2026-10-09T10:0{round_num}:00Z",
                    retries=0,
                    latency_s=0.1,
                    parsed_names=names,
                    backend="command",
                    prompt_version="np1w",
                    backend_meta={
                        "model_requested": "sonnet",
                        "model_observed": "Sonnet 5.5 Low",
                        "effort_requested": "low",
                        "tier": 2,
                        "profile_used": "Profile 24",
                        "adapter": {"name": "prompt-adapter", "version": "1.0"},
                    },
                )
            )

    # 1. Single cache
    single_cache = tmp_path / "single" / "raw_responses.jsonl"
    for e in entries:
        append_cache_record(single_cache, e)

    out_single = tmp_path / "out_single.json"
    res_single = build_pool_from_cache(
        cache_path=single_cache,
        output_path=out_single,
        generator_kind="command",
        configured_model="sonnet",
        seed=42,
        run_ids=["run_single"],
        allow_fake=True,
        min_required_names=10,
    )

    # 2. Split into 3 shard caches (by subfield index % 3)
    c1 = tmp_path / "shard1" / "raw_responses.jsonl"
    c2 = tmp_path / "shard2" / "raw_responses.jsonl"
    c3 = tmp_path / "shard3" / "raw_responses.jsonl"

    for e in entries:
        target_c = [c1, c2, c3][e.subfield_idx % 3]
        append_cache_record(target_c, e)

    out_shard_fwd = tmp_path / "out_shard_fwd.json"
    res_shard_fwd = build_pool_from_cache(
        cache_path=[c1, c2, c3],
        output_path=out_shard_fwd,
        generator_kind="command",
        configured_model="sonnet",
        seed=42,
        run_ids=["s1", "s2", "s3"],
        allow_fake=True,
        is_merged=True,
        min_required_names=10,
    )

    # 3. Reversed run-ID and cache order
    out_shard_rev = tmp_path / "out_shard_rev.json"
    res_shard_rev = build_pool_from_cache(
        cache_path=[c3, c2, c1],
        output_path=out_shard_rev,
        generator_kind="command",
        configured_model="sonnet",
        seed=42,
        run_ids=["s3", "s2", "s1"],
        allow_fake=True,
        is_merged=True,
        min_required_names=10,
    )

    # Assert names and sha256_names are identical in all three
    assert res_single["names"] == res_shard_fwd["names"] == res_shard_rev["names"]
    assert (
        res_single["meta"]["sha256_names"]
        == res_shard_fwd["meta"]["sha256_names"]
        == res_shard_rev["meta"]["sha256_names"]
    )


def test_duplicate_parseable_pair_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that merging caches containing the same (round, subfield) parseable response exits non-zero,
    naming the duplicate pair and both run IDs in the message."""
    from scripts.generate_name_pool import CacheEntry, append_cache_record, build_pool_from_cache

    entry = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["binary_search"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["binary_search"],
        backend="command",
        prompt_version="np1w",
    )

    c1 = tmp_path / "run_a" / "raw_responses.jsonl"
    c2 = tmp_path / "run_b" / "raw_responses.jsonl"
    append_cache_record(c1, entry)
    append_cache_record(c2, entry)

    with pytest.raises(SystemExit) as exc_info:
        build_pool_from_cache(
            cache_path=[c1, c2],
            output_path=tmp_path / "out.json",
            generator_kind="command",
            configured_model="sonnet",
            run_ids=["run_a", "run_b"],
            allow_fake=True,
            is_merged=True,
        )
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "(round 1, subfield 'algorithms')" in captured.err
    assert "run_a" in captured.err
    assert "run_b" in captured.err


def test_merge_refuses_mixed_backend_and_mixed_prompt_version(tmp_path: Path) -> None:
    """Verify that merging caches with mixed backend or mixed prompt_version raises ValueError."""
    from scripts.generate_name_pool import CacheEntry, append_cache_record, build_pool_from_cache

    e_deepseek = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["binary_search"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["binary_search"],
        backend="deepseek",
        prompt_version="np1",
    )
    e_command = CacheEntry(
        round=1,
        subfield="data_structures",
        subfield_idx=1,
        request_system="",
        request_user="",
        response_text=json.dumps(["linked_list"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["linked_list"],
        backend="command",
        prompt_version="np1w",
    )

    c1 = tmp_path / "r1" / "raw_responses.jsonl"
    c2 = tmp_path / "r2" / "raw_responses.jsonl"
    append_cache_record(c1, e_deepseek)
    append_cache_record(c2, e_command)

    with pytest.raises(ValueError, match="mixed backends"):
        build_pool_from_cache(
            cache_path=[c1, c2],
            output_path=tmp_path / "out.json",
            generator_kind="command",
            configured_model="sonnet",
            run_ids=["r1", "r2"],
            allow_fake=True,
            is_merged=True,
        )


def test_merge_refuses_mixed_prompt_version_only(tmp_path: Path) -> None:
    """Verify that merging caches with identical backend but differing prompt_version raises ValueError."""
    from scripts.generate_name_pool import CacheEntry, append_cache_record, build_pool_from_cache

    e_v1 = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_pv_concept_a"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-11T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_pv_concept_a"],
        backend="command",
        prompt_version="np1w",
    )
    e_v2 = CacheEntry(
        round=1,
        subfield="data_structures",
        subfield_idx=1,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_pv_concept_b"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-11T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_pv_concept_b"],
        backend="command",
        prompt_version="np2w",
    )

    c1 = tmp_path / "r1" / "raw_responses.jsonl"
    c2 = tmp_path / "r2" / "raw_responses.jsonl"
    append_cache_record(c1, e_v1)
    append_cache_record(c2, e_v2)

    with pytest.raises(ValueError, match="mixed prompt versions"):
        build_pool_from_cache(
            cache_path=[c1, c2],
            output_path=tmp_path / "out.json",
            generator_kind="command",
            configured_model="sonnet",
            run_ids=["r1", "r2"],
            allow_fake=True,
            is_merged=True,
        )


def test_merge_shortfall_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that a merge producing fewer than min_required_names exits non-zero with the rerun message."""
    from scripts.generate_name_pool import CacheEntry, append_cache_record, build_pool_from_cache

    e = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["binary_search"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["binary_search"],
        backend="command",
        prompt_version="np1w",
    )
    c1 = tmp_path / "r1" / "raw_responses.jsonl"
    append_cache_record(c1, e)

    with pytest.raises(SystemExit) as exc_info:
        build_pool_from_cache(
            cache_path=[c1],
            output_path=tmp_path / "out.json",
            generator_kind="command",
            configured_model="sonnet",
            run_ids=["r1"],
            allow_fake=True,
            is_merged=True,
            min_required_names=2001,
        )
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "which is below --min-required-names (2001)" in captured.err
    assert "Rerun shards with a higher --target-names (caches resume)" in captured.err


def test_shard_cli_guards_and_no_pool_written(tmp_path: Path) -> None:
    """Verify that:
    1. --shard without --run-id is rejected.
    2. A shard run writes no pool to output_path (Defect 2) and prints the build command instead.
    3. --build-only with a missing cache file fails clearly.
    """
    out_pool = tmp_path / "pool.json"
    cache_file = tmp_path / "raw.jsonl"
    lock_dir = tmp_path / "locks"

    # 1. --shard without --run-id
    res1 = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--shard",
            "1/2",
            "--offline-fake",
            "--output",
            str(out_pool),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res1.returncode == 1
    assert "requires an explicit --run-id" in res1.stderr

    # 2. Shard run writes no pool (Defect 2)
    res2 = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--shard",
            "1/2",
            "--run-id",
            "testrun-s1of2",
            "--offline-fake",
            "--max-calls",
            "1",
            "--output",
            str(out_pool),
            "--cache-file",
            str(cache_file),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 0
    assert not out_pool.exists(), "Shard run must NOT write a pool to output_path!"
    assert "--build-only --merge-run-ids" in res2.stdout

    # 3. Merge refuses missing cache
    res3 = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--build-only",
            "--merge-run-ids",
            "missing_run_id_xyz",
            "--output",
            str(out_pool),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 1
    assert "Shard cache not found" in res3.stderr


def test_shard_locks_mutual_exclusion(tmp_path: Path) -> None:
    """Verify that ShardLockManager enforces exclusive locks:
    while a helper process holds the run lock or profile lock, a second generator exits 1
    with a clear message and no traceback. Locks release when helper exits.
    """
    cache_dir = tmp_path / "my_run"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "raw_responses.jsonl"
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)

    helper_code = f"""import fcntl, os, time
fd = os.open({repr(str(cache_dir / ".lock"))}, os.O_CREAT | os.O_RDWR)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
time.sleep(3)
"""
    p_helper = subprocess.Popen([sys.executable, "-c", helper_code])
    time.sleep(0.3)

    try:
        res = subprocess.run(
            [
                sys.executable,
                "scripts/generate_name_pool.py",
                "--shard",
                "1/2",
                "--run-id",
                "my_run",
                "--cache-file",
                str(cache_file),
                "--offline-fake",
                "--output",
                str(tmp_path / "p.json"),
                "--lock-dir",
                str(lock_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 1
        assert "is locked by another process" in res.stderr
        assert "Traceback" not in res.stderr
    finally:
        p_helper.terminate()
        p_helper.wait()

    res_after = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--shard",
            "1/2",
            "--run-id",
            "my_run",
            "--cache-file",
            str(cache_file),
            "--offline-fake",
            "--max-calls",
            "1",
            "--output",
            str(tmp_path / "p.json"),
            "--lock-dir",
            str(lock_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_after.returncode == 0


def test_profile_lock_mutual_exclusion(tmp_path: Path) -> None:
    """Verify that ShardLockManager enforces exclusive profile flock:
    while a helper process holds <lock_dir>/<profile_slug>.lock, a generator targeting
    that profile exits 1 with a clear message and no traceback.
    After the helper exits, the generator successfully acquires the lock and runs.
    """
    from scripts.generate_name_pool import slugify_profile

    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = tmp_path / "cache_run"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "raw_responses.jsonl"

    profile_name = "Profile 24"
    profile_slug = slugify_profile(profile_name)  # "profile_24"
    profile_lock_file = lock_dir / f"{profile_slug}.lock"

    stub = str(Path("tests/stub_prompt_adapter.py").resolve())

    # Helper process holds exclusive lock on profile_24.lock
    helper_code = f"""import fcntl, os, time
fd = os.open({repr(str(profile_lock_file))}, os.O_CREAT | os.O_RDWR)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
time.sleep(3)
"""
    p_helper = subprocess.Popen([sys.executable, "-c", helper_code])
    time.sleep(0.3)

    cmd = [
        sys.executable,
        "scripts/generate_name_pool.py",
        "--backend",
        "command",
        "--command",
        f"{sys.executable} {stub} --scenario success",
        "--adapter-profile",
        profile_name,
        "--live",
        "--confirm",
        "--shard",
        "1/2",
        "--run-id",
        "prof_lock_run",
        "--cache-file",
        str(cache_file),
        "--output",
        str(tmp_path / "out.json"),
        "--lock-dir",
        str(lock_dir),
        "--max-calls",
        "1",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "is locked by another process" in res.stderr
        assert f"profile '{profile_name}'" in res.stderr
        assert "Traceback" not in res.stderr
    finally:
        p_helper.terminate()
        p_helper.wait()

    # After helper releases lock, generator runs and exits 0
    res_after = subprocess.run(cmd, capture_output=True, text=True)
    assert res_after.returncode == 0


def test_print_shard_commands_cli() -> None:
    """Verify --print-shard-commands enforces profile count match, emits valid commands
    with proper sharding flags, distinct run IDs, and quoted profile names."""
    res_mismatch = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--print-shard-commands",
            "--shards",
            "3",
            "--profiles",
            "Profile 1,Profile 2",
            "--run-id-prefix",
            "pfx",
        ],
        capture_output=True,
        text=True,
    )
    assert res_mismatch.returncode == 1
    assert "Profiles count (2) must equal shards count (3)" in res_mismatch.stderr

    res_ok = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--print-shard-commands",
            "--shards",
            "2",
            "--profiles",
            "Profile 24,Profile 25",
            "--run-id-prefix",
            "pool2026",
            "--command",
            "prompt-adapter",
        ],
        capture_output=True,
        text=True,
    )
    assert res_ok.returncode == 0
    lines = [ln.strip() for ln in res_ok.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) == 2
    assert "--shard 1/2" in lines[0]
    assert "--run-id pool2026-s1of2" in lines[0]
    assert "--adapter-profile 'Profile 24'" in lines[0]
    assert "--backend command" in lines[0]
    assert "--live" in lines[0]
    assert "--confirm" in lines[0]

    assert "--shard 2/2" in lines[1]
    assert "--run-id pool2026-s2of2" in lines[1]
    assert "--adapter-profile 'Profile 25'" in lines[1]


def test_cli_verify_single_and_merged(tmp_path: Path) -> None:
    """Verify that --verify operates through CLI main() for both single-run and merged pools,
    and fails clearly when a listed cache is missing."""
    from scripts.generate_name_pool import (
        CacheEntry,
        append_cache_record,
        build_pool_from_cache,
    )

    names = [f"valid_concept_{i:03d}" for i in range(1, 50)]
    entry = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(names),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=names,
        backend="deepseek",
        prompt_version="np1",
    )

    c_single = tmp_path / "single_run" / "raw_responses.jsonl"
    append_cache_record(c_single, entry)
    pool_single = tmp_path / "pool_single.json"
    build_pool_from_cache(
        cache_path=c_single,
        output_path=pool_single,
        generator_kind="deepseek",
        configured_model="deepseek-flash",
        seed=42,
        run_ids=["single_run"],
        allow_fake=True,
        min_required_names=10,
    )

    res_single = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--verify",
            "--output",
            str(pool_single),
            "--cache-file",
            str(c_single),
            "--allow-fake",
            "--min-required-names",
            "10",
        ],
        capture_output=True,
        text=True,
    )
    assert res_single.returncode == 0
    assert "Pool verification PASSED" in res_single.stdout

    c_m1 = tmp_path / "m1" / "raw_responses.jsonl"
    c_m2 = tmp_path / "m2" / "raw_responses.jsonl"
    append_cache_record(c_m1, entry)
    e2 = CacheEntry(
        round=1,
        subfield="data_structures",
        subfield_idx=1,
        request_system="",
        request_user="",
        response_text=json.dumps(["binary_heap"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["binary_heap"],
        backend="deepseek",
        prompt_version="np1",
    )
    append_cache_record(c_m2, e2)

    pool_merged = tmp_path / "pool_merged.json"
    build_pool_from_cache(
        cache_path=[c_m1, c_m2],
        output_path=pool_merged,
        generator_kind="deepseek",
        configured_model="deepseek-flash",
        seed=42,
        run_ids=["m1", "m2"],
        allow_fake=True,
        is_merged=True,
        min_required_names=10,
    )

    res_merged_missing = subprocess.run(
        [
            sys.executable,
            "scripts/generate_name_pool.py",
            "--verify",
            "--output",
            str(pool_merged),
            "--merge-run-ids",
            "m1,m2",
            "--allow-fake",
            "--min-required-names",
            "10",
        ],
        capture_output=True,
        text=True,
    )
    assert res_merged_missing.returncode == 1
    assert "Listed cache missing for run_id" in res_merged_missing.stderr


def test_cli_verify_merged_success_and_tampered_cache(tmp_path: Path) -> None:
    """Verify that --verify succeeds on a valid merged pool whose shard caches exist
    in results/datagen/<run_id>/raw_responses.jsonl, and fails with a SHA256 mismatch
    error when one of the shard caches is modified."""
    from scripts.generate_name_pool import (
        CacheEntry,
        append_cache_record,
        build_pool_from_cache,
    )

    r1_id = f"_test_verify_merge_{uuid.uuid4().hex[:8]}_1"
    r2_id = f"_test_verify_merge_{uuid.uuid4().hex[:8]}_2"
    datagen_base = Path("results/datagen")
    c1_dir = datagen_base / r1_id
    c2_dir = datagen_base / r2_id
    c1 = c1_dir / "raw_responses.jsonl"
    c2 = c2_dir / "raw_responses.jsonl"

    try:
        c1_dir.mkdir(parents=True, exist_ok=True)
        c2_dir.mkdir(parents=True, exist_ok=True)

        names1 = [f"verify_synth_concept_a_{i:03d}" for i in range(1, 25)]
        e1 = CacheEntry(
            round=1,
            subfield="algorithms",
            subfield_idx=0,
            request_system="",
            request_user="",
            response_text=json.dumps(names1),
            model_id="test",
            token_usage={},
            timestamp_utc="2026-10-11T00:00:00Z",
            retries=0,
            latency_s=0.1,
            parsed_names=names1,
            backend="deepseek",
            prompt_version="np1",
        )
        names2 = [f"verify_synth_concept_b_{i:03d}" for i in range(1, 25)]
        e2 = CacheEntry(
            round=1,
            subfield="data_structures",
            subfield_idx=1,
            request_system="",
            request_user="",
            response_text=json.dumps(names2),
            model_id="test",
            token_usage={},
            timestamp_utc="2026-10-11T00:00:00Z",
            retries=0,
            latency_s=0.1,
            parsed_names=names2,
            backend="deepseek",
            prompt_version="np1",
        )
        append_cache_record(c1, e1)
        append_cache_record(c2, e2)

        pool_merged = tmp_path / "pool_merged.json"
        build_pool_from_cache(
            cache_path=[c1, c2],
            output_path=pool_merged,
            generator_kind="deepseek",
            configured_model="deepseek-flash",
            seed=42,
            run_ids=[r1_id, r2_id],
            allow_fake=True,
            is_merged=True,
            min_required_names=10,
        )

        # 1. Success path: verify passes
        res_ok = subprocess.run(
            [
                sys.executable,
                "scripts/generate_name_pool.py",
                "--verify",
                "--output",
                str(pool_merged),
                "--merge-run-ids",
                f"{r1_id},{r2_id}",
                "--allow-fake",
                "--min-required-names",
                "10",
            ],
            capture_output=True,
            text=True,
        )
        assert res_ok.returncode == 0, f"Verify failed unexpectedly: {res_ok.stderr}"
        assert "Pool verification PASSED" in res_ok.stdout

        # 2. Tampered cache path: append a line to one cache, assert it fails with SHA256 mismatch
        with open(c1, "a", encoding="utf-8") as f:
            f.write('{"tampered": true}\n')

        res_tampered = subprocess.run(
            [
                sys.executable,
                "scripts/generate_name_pool.py",
                "--verify",
                "--output",
                str(pool_merged),
                "--merge-run-ids",
                f"{r1_id},{r2_id}",
                "--allow-fake",
                "--min-required-names",
                "10",
            ],
            capture_output=True,
            text=True,
        )
        assert res_tampered.returncode == 1
        assert f"Cache SHA256 mismatch for run_id '{r1_id}'" in res_tampered.stderr
    finally:
        shutil.rmtree(c1_dir, ignore_errors=True)
        shutil.rmtree(c2_dir, ignore_errors=True)


def test_timeout_kill_sigterm_ignored_and_grandchild_killed(tmp_path: Path) -> None:
    """Verify that when parent ignores SIGTERM and spawns a grandchild in the same process group,
    both parent and grandchild PIDs are killed via group SIGKILL on timeout."""
    p_pid_file = tmp_path / "parent.pid"
    gc_pid_file = tmp_path / "grandchild.pid"

    helper_code = f"""import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
with open({repr(str(p_pid_file))}, "w") as f:
    f.write(str(os.getpid()))

gc = subprocess.Popen([sys.executable, "-c", f'''import os, time
with open({repr(str(gc_pid_file))}, "w") as f:
    f.write(str(os.getpid()))
time.sleep(60)
'''])

time.sleep(60)
"""
    helper_script = tmp_path / "helper_ign.py"
    helper_script.write_text(helper_code, encoding="utf-8")

    from scripts.generate_name_pool import CommandGenerationBackend
    backend = CommandGenerationBackend(
        command=f"{sys.executable} {helper_script}",
        profile="test_prof",
        timeout_s=-59,  # 1.0s timeout limit
        sigterm_wait_s=0.2,
    )
    res = backend.complete(
        subfield="algorithms",
        round_num=1,
        previous_names=[],
        system_prompt="",
        user_prompt="",
    )
    assert res.ok is False
    assert res.error_code == 12

    assert p_pid_file.exists()
    assert gc_pid_file.exists()
    parent_pid = int(p_pid_file.read_text(encoding="utf-8").strip())
    gc_pid = int(gc_pid_file.read_text(encoding="utf-8").strip())

    time.sleep(0.1)
    with pytest.raises(ProcessLookupError):
        os.kill(parent_pid, 0)
    with pytest.raises(ProcessLookupError):
        os.kill(gc_pid, 0)


def test_timeout_kill_descendant_outside_group_holds_stdout_bounded(tmp_path: Path) -> None:
    """Verify that if a descendant process detaches into a new session and holds stdout open,
    the timeout path returns within a bounded time (< 6.0s) rather than hanging indefinitely."""
    child_pid_file = tmp_path / "detached_child.pid"
    helper_code = f"""import os, subprocess, sys, time
child = subprocess.Popen(
    [sys.executable, "-c", f'''import os, time
with open({repr(str(child_pid_file))}, "w") as f:
    f.write(str(os.getpid()))
time.sleep(15)
'''],
    stdout=sys.stdout,
    stderr=sys.stderr,
    start_new_session=True,
)
time.sleep(60)
"""
    helper_script = tmp_path / "helper_detached.py"
    helper_script.write_text(helper_code, encoding="utf-8")

    from scripts.generate_name_pool import CommandGenerationBackend
    backend = CommandGenerationBackend(
        command=f"{sys.executable} {helper_script}",
        profile="test_prof",
        timeout_s=-59,  # 1.0s timeout limit
        sigterm_wait_s=0.2,
    )
    t0 = time.time()
    res = backend.complete(
        subfield="algorithms",
        round_num=1,
        previous_names=[],
        system_prompt="",
        user_prompt="",
    )
    elapsed = time.time() - t0
    assert res.ok is False
    assert res.error_code == 12
    assert elapsed < 6.0, f"Call hung for {elapsed:.2f}s instead of returning bounded!"

    if child_pid_file.exists():
        try:
            cid = int(child_pid_file.read_text(encoding="utf-8").strip())
            os.kill(cid, signal.SIGKILL)
        except (ProcessLookupError, OSError, ValueError):
            pass


def test_distinct_model_labels_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that when shards contain distinct observed model labels,
    a warning is printed to stderr and meta records observed_models_warning: true."""
    from scripts.generate_name_pool import (
        CacheEntry,
        append_cache_record,
        build_pool_from_cache,
    )

    e1 = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_model_warn_concept_a"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_model_warn_concept_a"],
        backend="command",
        prompt_version="np1w",
        backend_meta={"model_observed": "Sonnet 5.5 Low"},
    )
    e2 = CacheEntry(
        round=1,
        subfield="data_structures",
        subfield_idx=1,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_model_warn_concept_b"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-09T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_model_warn_concept_b"],
        backend="command",
        prompt_version="np1w",
        backend_meta={"model_observed": "Illustrative Other Model"},
    )

    c1 = tmp_path / "s1" / "raw_responses.jsonl"
    c2 = tmp_path / "s2" / "raw_responses.jsonl"
    append_cache_record(c1, e1)
    append_cache_record(c2, e2)

    out = tmp_path / "pool.json"
    res = build_pool_from_cache(
        cache_path=[c1, c2],
        output_path=out,
        generator_kind="command",
        configured_model="sonnet",
        run_ids=["s1", "s2"],
        allow_fake=True,
        is_merged=True,
        min_required_names=2,
    )
    captured = capsys.readouterr()
    assert "WARNING: Multiple distinct model_observed labels observed" in captured.err
    assert res["meta"].get("observed_models_warning") is True
    assert set(res["meta"].get("observed_models_set", [])) == {"Illustrative Other Model", "Sonnet 5.5 Low"}


def test_profile_in_use_exit_7(tmp_path: Path) -> None:
    """Verify that adapter error profile_in_use / exit 15 stops the generator with exit code 7,
    a clear message that profile is locked, and preserves existing cache untouched."""
    stub = str(Path("tests/stub_prompt_adapter.py").resolve())
    cache_file = tmp_path / "cache.jsonl"
    initial_content = '{"existing": "data"}\n'
    cache_file.write_text(initial_content, encoding="utf-8")
    sha_before = hashlib.sha256(cache_file.read_bytes()).hexdigest()
    lock_dir = tmp_path / "locks"

    cmd = [
        sys.executable,
        "scripts/generate_name_pool.py",
        "--backend",
        "command",
        "--command",
        f"{sys.executable} {stub} --scenario profile_in_use",
        "--adapter-profile",
        "Profile 24",
        "--live",
        "--confirm",
        "--output",
        str(tmp_path / "out.json"),
        "--cache-file",
        str(cache_file),
        "--lock-dir",
        str(lock_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 7
    assert "Profile in use (error 15): profile 'Profile 24' is locked by another process" in res.stderr
    assert cache_file.exists()
    sha_after = hashlib.sha256(cache_file.read_bytes()).hexdigest()
    assert sha_after == sha_before


def test_merged_meta_fidelity_requested_fields(tmp_path: Path) -> None:
    """Verify that build_pool_from_cache with is_merged=True preserves requested fields from backend_meta."""
    from scripts.generate_name_pool import (
        CacheEntry,
        append_cache_record,
        build_pool_from_cache,
    )

    e1 = CacheEntry(
        round=1,
        subfield="algorithms",
        subfield_idx=0,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_meta_concept_a"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-11T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_meta_concept_a"],
        backend="command",
        prompt_version="np1w",
        backend_meta={
            "effort_requested": "medium",
            "model_requested": "claude-sonnet-custom",
            "memory_requested": True,
            "web_search_requested": True,
        },
    )
    e2 = CacheEntry(
        round=1,
        subfield="data_structures",
        subfield_idx=1,
        request_system="",
        request_user="",
        response_text=json.dumps(["synth_meta_concept_b"]),
        model_id="test",
        token_usage={},
        timestamp_utc="2026-10-11T00:00:00Z",
        retries=0,
        latency_s=0.1,
        parsed_names=["synth_meta_concept_b"],
        backend="command",
        prompt_version="np1w",
        backend_meta={
            "effort_requested": "medium",
            "model_requested": "claude-sonnet-custom",
            "memory_requested": True,
            "web_search_requested": True,
        },
    )

    c1 = tmp_path / "shard1" / "raw_responses.jsonl"
    c2 = tmp_path / "shard2" / "raw_responses.jsonl"
    append_cache_record(c1, e1)
    append_cache_record(c2, e2)

    out = tmp_path / "pool.json"
    res = build_pool_from_cache(
        cache_path=[c1, c2],
        output_path=out,
        generator_kind="command",
        configured_model="sonnet",
        run_ids=["shard1", "shard2"],
        allow_fake=True,
        is_merged=True,
        min_required_names=2,
    )

    meta = res["meta"]
    assert meta.get("requested_effort") == "medium"
    assert meta.get("requested_model") == "claude-sonnet-custom"
    assert meta.get("requested_memory") is True
    assert meta.get("requested_web_search") is True


