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

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

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
    validate_and_dedupe_candidates,
    verify_pool,
)
from scripts.run_experiment import load_and_validate_names_file


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
    corpus_embeds = {embed_text("binary_search_tree"), embed_text("sorting_algorithm")}

    candidates = [
        "graph_theory.txt",                 # ends_with_txt
        "InvalidCase",                      # invalid_snake_case
        "ab",                               # invalid_length (< 3)
        "a" * 55,                           # invalid_length (> 50)
        "one_two_three_four_five_six",      # invalid_word_count (> 5 words)
        "binary_search_tree",               # corpus_overlap_exact
        "sorting_algorithm",                # corpus_overlap_exact
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

    # Also test embed_text overlap via candidate whose embed matches corpus
    # e.g., if corpus has "sorting_algorithm", its embed_text is "sorting algorithm".
    # A candidate matching that embed_text is filtered.
    filtered, n_raw, drop_counts = validate_and_dedupe_candidates(
        [fake_entry], corpus_nodes, corpus_embeds
    )

    assert n_raw == len(candidates)
    assert drop_counts["ends_with_txt"] == 1
    assert drop_counts["invalid_snake_case"] == 1
    assert drop_counts["invalid_length"] == 2
    assert drop_counts["invalid_word_count"] == 1
    assert drop_counts["corpus_overlap_exact"] == 2
    assert drop_counts["duplicate_exact"] == 1
    assert drop_counts["plural_pair"] == 2

    # Verify surviving valid concepts
    assert "accepted_concept_one" in filtered
    assert "accepted_concept_two" in filtered
    assert "decision_tree" in filtered
    assert "decision_trees" not in filtered
    assert "process" in filtered
    assert "processes" not in filtered


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
    assert "@ 20s/call" in res.stdout
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
    assert "Claude 3.5 Sonnet" in meta["observed_models"]
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
    assert len(json_blocks) == 8, f"Expected 8 response fixtures, found {len(json_blocks)}"

    expected_codes = {
        "rate_limit": 10,
        "login_required": 11,
        "model_mismatch": 14,
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
            assert res.model_id == "Claude 3.5 Sonnet"
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

