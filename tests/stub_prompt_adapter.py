#!/usr/bin/env python3
"""tests/stub_prompt_adapter.py — Stub adapter speaking Contract v1 for testing.

Used by offline integration tests to exercise CommandBackend subprocess paths
without live browser or network access.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Stub prompt adapter for testing.")
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Forced scenario name (overrides stdin profile).",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=None,
        help="Path to persistent state file for rate_limit_after_n scenario.",
    )
    parser.add_argument(
        "--limit-n",
        type=int,
        default=2,
        help="Number of successful calls before triggering rate limit.",
    )
    parser.add_argument(
        "--child-pid-file",
        type=str,
        default=None,
        help="Path to write child process PID to when testing process groups.",
    )
    parser.add_argument(
        "--hang-seconds",
        type=float,
        default=15.0,
        help="Seconds to sleep in hang scenario.",
    )
    parser.add_argument(
        "--spawn-child",
        action="store_true",
        help="Spawn a child process that also hangs.",
    )
    args = parser.parse_args()

    # Read stdin
    raw_input = sys.stdin.read().strip()
    try:
        payload = json.loads(raw_input)
    except Exception:
        out = {
            "ok": False,
            "error": "bad_request",
            "message": "Invalid JSON on stdin",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 2

    scenario = args.scenario or payload.get("profile") or "success"
    model_req = payload.get("model", "sonnet")
    effort_req = payload.get("effort", "low")

    # Determine subfield from prompt if possible
    prompt = payload.get("prompt", "")
    subfield = "stub_domain"
    # Try to extract subfield name from prompt: e.g. for the subfield '...'
    m = re.search(r"subfield '([^']+)'", prompt)
    if m:
        subfield = m.group(1).replace(" ", "_")

    if scenario == "hang":
        if args.spawn_child:
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            if args.child_pid_file:
                Path(args.child_pid_file).write_text(str(child.pid), encoding="utf-8")
        time.sleep(args.hang_seconds)
        return 0

    if scenario == "garbage":
        print("CRITICAL: [fatal] Process crashed! Non-JSON garbage on stdout.")
        return 1

    if scenario == "rate_limit_after_n":
        state_file = Path(args.state_file) if args.state_file else Path("stub_state.json")
        count = 0
        if state_file.exists():
            try:
                count = int(state_file.read_text(encoding="utf-8").strip())
            except Exception:
                count = 0

        if count >= args.limit_n:
            out = {
                "ok": False,
                "error": "rate_limit",
                "message": f"Rate limit reached after {count} calls",
                "reset_time": "2026-10-07T23:59:59Z",
            }
            print(json.dumps(out))
            return 10
        else:
            count += 1
            state_file.write_text(str(count), encoding="utf-8")
            scenario = "success"

    if scenario == "rate_limit":
        out = {
            "ok": False,
            "error": "rate_limit",
            "message": "You have reached your usage limit for Sonnet 5.5 Low.",
            "reset_time": "2026-10-07T23:00:00Z",
        }
        print(json.dumps(out))
        return 10

    if scenario == "login_required":
        out = {
            "ok": False,
            "error": "login_required",
            "message": "Login session expired or Cloudflare turnstile challenge presented.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 11

    if scenario == "model_mismatch":
        out = {
            "ok": False,
            "error": "model_mismatch",
            "message": "Model mismatch: requested 'sonnet' but observed 'Sonnet 5.5 Low' in UI.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 14

    if scenario == "timeout":
        out = {
            "ok": False,
            "error": "timeout",
            "message": "Response generation timed out after 300 seconds.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 12

    if scenario == "refusal":
        out = {
            "ok": False,
            "error": "refusal",
            "message": "Model refused to answer the prompt.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 13

    if scenario == "bad_request":
        out = {
            "ok": False,
            "error": "bad_request",
            "message": "Missing required field 'prompt' in stdin JSON.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 2

    if scenario == "other":
        out = {
            "ok": False,
            "error": "other",
            "message": "Browser process crashed unexpectedly.",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 1

    if scenario == "no_error_field":
        out = {
            "ok": False,
            "message": "Error occurred but error key omitted",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 10

    if scenario == "unknown_error_code":
        out = {
            "ok": False,
            "error": "custom_unrecognized_error",
            "message": "Some custom error string",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 1

    if scenario == "unparseable":
        out = {
            "ok": True,
            "text": "I am sorry, but as an AI assistant I will explain concepts rather than listing JSON arrays.",
            "tier": 1,
            "model_requested": model_req,
            "model_observed": "Sonnet 5.5 Low",
            "effort_requested": effort_req,
            "memory_requested": False,
            "web_search_requested": False,
            "elapsed_s": 0.05,
            "adapter": {"name": "prompt-adapter", "version": "1.0.0"},
        }
        print(json.dumps(out))
        return 0

    if scenario == "prose_wrapped":
        names = [f"claude_pw_{subfield}_{i:03d}" for i in range(1, 41)]
        text_payload = (
            "Here are the requested computer science concepts:\n"
            "```json\n"
            + json.dumps(names)
            + "\n```\nHope this curriculum list is helpful!"
        )
        out = {
            "ok": True,
            "text": text_payload,
            "tier": 1,
            "model_requested": model_req,
            "model_observed": "Sonnet 5.5 Low",
            "effort_requested": effort_req,
            "memory_requested": False,
            "web_search_requested": False,
            "elapsed_s": 0.05,
            "adapter": {"name": "prompt-adapter", "version": "1.0.0"},
        }
        print(json.dumps(out))
        return 0

    # Default: success
    names = [f"claude_concept_{subfield}_{i:03d}" for i in range(1, 41)]
    out = {
        "ok": True,
        "text": json.dumps(names),
        "tier": 1,
        "model_requested": model_req,
        "model_observed": "Sonnet 5.5 Low",
        "effort_requested": effort_req,
        "memory_requested": False,
        "web_search_requested": False,
        "elapsed_s": 0.05,
        "adapter": {"name": "prompt-adapter", "version": "1.0.0"},
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
