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
    args = parser.parse_args()

    # Read stdin
    raw_input = sys.stdin.read().strip()
    try:
        payload = json.loads(raw_input)
    except Exception:
        out = {
            "ok": False,
            "error": 2,
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
        # Sleep long enough to trigger timeout in test
        time.sleep(15)
        return 0

    if scenario == "garbage":
        print("CRITICAL: [fatal] Process crashed! Non-JSON garbage on stdout.")
        return 0

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
                "error": 10,
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
            "error": 10,
            "message": "Usage limit reached for Claude 3.5 Sonnet",
            "reset_time": "2026-10-07T23:59:59Z",
        }
        print(json.dumps(out))
        return 10

    if scenario == "login_required":
        out = {
            "ok": False,
            "error": 11,
            "message": "Session expired or Cloudflare turnstile challenge",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 11

    if scenario == "model_mismatch":
        out = {
            "ok": False,
            "error": 14,
            "message": "Observed model 'haiku' did not match requested 'sonnet'",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 14

    if scenario == "timeout":
        out = {
            "ok": False,
            "error": 12,
            "message": "Browser automation timed out after 300 seconds",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 12

    if scenario == "refusal":
        out = {
            "ok": False,
            "error": 13,
            "message": "Model refused to generate concept names",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 13

    if scenario == "bad_request":
        out = {
            "ok": False,
            "error": 2,
            "message": "Missing required field 'prompt' in request",
            "reset_time": None,
        }
        print(json.dumps(out))
        return 2

    if scenario == "other":
        out = {
            "ok": False,
            "error": 1,
            "message": "Internal adapter crash or unknown failure",
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
            "model_observed": "Claude 3.5 Sonnet",
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
            "model_observed": "Claude 3.5 Sonnet",
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
        "model_observed": "Claude 3.5 Sonnet",
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
