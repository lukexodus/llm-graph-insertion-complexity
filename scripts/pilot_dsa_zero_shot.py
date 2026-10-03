#!/usr/bin/env python3
"""
pilot_dsa_zero_shot.py — INFRA-006
==================================
Offline/online pilot script for zero-shot leave-one-out prerequisite evaluation on DSA.

Features:
  - Brute-force leave-one-out: 29 nodes * 28 candidates = 812 calls ([D-29])
  - Strict guardrails: requires --confirm, checks --max-calls limit
  - No hardcoded prices: accepts --price-in and --price-out (per million tokens)
  - Full evaluation: 3-way accuracy, confusion matrix, directed edge P/R/F1,
    direction flips, swap consistency, parse failure rate, latency percentiles,
    token totals (including reasoning and prompt cache), and estimated cost.
  - Sensitivity analysis for DSA unjudged row (default excluded vs. treated as NONE)
  - Saves raw call records (JSONL) and aggregate metrics (JSON) under results/pilot/<UTC_TIMESTAMP>/
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Add src to sys.path if not present
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_insertion.decision import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    PairwiseDecisionStep,
)
from graph_insertion.graph_representation import embed_text
from graph_insertion.llm import (
    DeepSeekClient,
    FakeLLMClient,
    LLMClient,
    MeteredLLMClient,
)
from graph_insertion.loader import load_corpus


def compute_gold_unordered_label(
    gold_judgments: Any, a: str, b: str
) -> tuple[str, bool]:
    """Compute gold relation for unordered pair {a, b} where a < b.

    Returns
    -------
    tuple[str, bool]
        (label, is_unjudged):
        label in ("A_PREREQ_B", "B_PREREQ_A", "NONE", "ANOMALY", "EXCLUDED")
        is_unjudged is True if either direction was None in gold.
    """
    j_ab = gold_judgments.judgment_for_edge(a, b)
    j_ba = gold_judgments.judgment_for_edge(b, a)

    if j_ab is None or j_ba is None:
        return "EXCLUDED", True
    if j_ab is True and j_ba is True:
        return "ANOMALY", False
    if j_ab is True:
        return "A_PREREQ_B", False
    if j_ba is True:
        return "B_PREREQ_A", False
    return "NONE", False


def map_token_to_unordered_relation(
    token: str, new_name: str, cand: str, a: str, b: str
) -> str:
    """Map a directional model token (X_PREREQ_Y, Y_PREREQ_X, NONE) to {a, b} representation."""
    if token not in ("X_PREREQ_Y", "Y_PREREQ_X", "NONE"):
        return "PARSE_FAILURE"

    if new_name == a and cand == b:
        # X is A, Y is B
        if token == "X_PREREQ_Y":
            return "A_PREREQ_B"
        if token == "Y_PREREQ_X":
            return "B_PREREQ_A"
        return "NONE"
    elif new_name == b and cand == a:
        # X is B, Y is A
        if token == "X_PREREQ_Y":
            return "B_PREREQ_A"
        if token == "Y_PREREQ_X":
            return "A_PREREQ_B"
        return "NONE"
    else:
        raise ValueError(f"Pair ({new_name}, {cand}) does not match ({a}, {b})")


def run_pilot(
    *,
    client: LLMClient,
    model_name: str,
    output_dir: Path,
    price_in: float,
    price_out: float,
    max_calls: int = 900,
    strict_parse: bool = False,
    dataset_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute the leave-one-out pilot experiment on DSA."""
    # 1. Load DSA corpus
    corpus = load_corpus("DSA_gold_standard_MEKG", root=dataset_root)
    graph = corpus.graph
    gold = corpus.judgments
    domain_context = graph.domain_context

    nodes = sorted(graph.nodes())
    num_nodes = len(nodes)
    planned_calls = num_nodes * (num_nodes - 1)

    if planned_calls > max_calls:
        raise RuntimeError(
            f"Planned calls ({planned_calls}) exceeds max allowed calls ({max_calls})."
        )

    meter = MeteredLLMClient(client)
    decision_step = PairwiseDecisionStep(meter, strict=strict_parse)

    print(f"Loaded DSA: {num_nodes} nodes, domain context: {domain_context!r}")
    print(f"Executing {planned_calls} leave-one-out pairwise queries...")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_calls_file = output_dir / "raw_calls.jsonl"

    call_records: list[dict[str, Any]] = []
    # Store call results by (new_name, cand)
    call_results: dict[tuple[str, str], dict[str, Any]] = {}

    call_index = 0
    with raw_calls_file.open("w", encoding="utf-8") as f_raw:
        for new_node in nodes:
            # Leave-one-out candidates: all nodes except new_node
            candidates = tuple(n for n in nodes if n != new_node)
            for cand in candidates:
                call_index += 1
                user_prompt = decision_step.build_user_prompt(new_node, cand, domain_context)
                resp = meter.complete(system=SYSTEM_PROMPT, user=user_prompt)
                raw_token = resp.text.strip().upper()

                rec = {
                    "call_index": call_index,
                    "new_name": new_node,
                    "candidate": cand,
                    "domain_context": domain_context,
                    "user_prompt": user_prompt,
                    "response_text": resp.text,
                    "raw_token": raw_token,
                    "latency_s": resp.latency_s,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "reasoning_tokens": resp.reasoning_tokens,
                    "cache_hit_tokens": resp.cache_hit_tokens,
                    "cache_miss_tokens": resp.cache_miss_tokens,
                    "attempts": resp.attempts,
                    "retry_wait_s": resp.retry_wait_s,
                }
                call_records.append(rec)
                call_results[(new_node, cand)] = rec
                f_raw.write(json.dumps(rec) + "\n")

    print(f"Completed {call_index} calls. Computing evaluation metrics...")

    # 2. Evaluation across unordered pairs
    unordered_pairs = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            unordered_pairs.append((nodes[i], nodes[j]))

    # Stats counters
    total_unordered = len(unordered_pairs)  # 29 * 28 / 2 = 406
    swap_consistent_pairs = 0
    excluded_unordered = 0

    # 3-way evaluation on calls (excluding vs sensitivity including)
    classes = ["X_PREREQ_Y", "Y_PREREQ_X", "NONE"]
    # Confusion matrix for non-excluded calls: gold_idx x pred_idx
    # Pred classes: X_PREREQ_Y, Y_PREREQ_X, NONE, PARSE_FAILURE
    pred_col_names = ["X_PREREQ_Y", "Y_PREREQ_X", "NONE", "PARSE_FAILURE"]
    conf_matrix = {g: {p: 0 for p in pred_col_names} for g in classes}
    conf_matrix_sensitivity = {g: {p: 0 for p in classes} for g in classes}
    for g in conf_matrix_sensitivity:
        conf_matrix_sensitivity[g] = {p: 0 for p in pred_col_names}

    correct_calls_standard = 0
    total_calls_standard = 0

    correct_calls_sensitivity = 0
    total_calls_sensitivity = 0

    direction_flips = 0

    # Directed edge metrics: TP, FP, FN
    # Ground truth edges (prereq -> dependent)
    tp = 0
    fp = 0
    fn = 0

    # Check each call
    for (new_name, cand), rec in call_results.items():
        # Gold for this directed pair (new_name is prereq of cand?)
        is_prereq_gold = gold.judgment_for_edge(new_name, cand)
        # Gold for reverse directed pair (cand is prereq of new_name?)
        is_reverse_gold = gold.judgment_for_edge(cand, new_name)

        pred_token = rec["raw_token"] if rec["raw_token"] in classes else "PARSE_FAILURE"

        # Determine gold token for call where X=new_name, Y=cand
        gold_token_standard: Optional[str] = None
        gold_token_sens: str

        if is_prereq_gold is None or is_reverse_gold is None:
            # Missing in gold
            gold_token_standard = None
            gold_token_sens = "NONE"
        elif is_prereq_gold is True and is_reverse_gold is False:
            gold_token_standard = "X_PREREQ_Y"
            gold_token_sens = "X_PREREQ_Y"
        elif is_reverse_gold is True and is_prereq_gold is False:
            gold_token_standard = "Y_PREREQ_X"
            gold_token_sens = "Y_PREREQ_X"
        elif is_prereq_gold is False and is_reverse_gold is False:
            gold_token_standard = "NONE"
            gold_token_sens = "NONE"
        else:
            # Anomaly / both true
            gold_token_standard = "ANOMALY"
            gold_token_sens = "ANOMALY"

        # Standard accounting
        if gold_token_standard in classes:
            total_calls_standard += 1
            conf_matrix[gold_token_standard][pred_token] += 1
            if pred_token == gold_token_standard:
                correct_calls_standard += 1
            # Direction flip check
            if (gold_token_standard == "X_PREREQ_Y" and pred_token == "Y_PREREQ_X") or (
                gold_token_standard == "Y_PREREQ_X" and pred_token == "X_PREREQ_Y"
            ):
                direction_flips += 1

        # Sensitivity accounting (missing pair counted as NONE)
        if gold_token_sens in classes:
            total_calls_sensitivity += 1
            conf_matrix_sensitivity[gold_token_sens][pred_token] += 1
            if pred_token == gold_token_sens:
                correct_calls_sensitivity += 1

        # Directed edge precision/recall
        # Model predicted (new_name -> cand) if pred_token == "X_PREREQ_Y"
        # Model predicted (cand -> new_name) if pred_token == "Y_PREREQ_X"
        if is_prereq_gold is not None:
            if pred_token == "X_PREREQ_Y":
                if is_prereq_gold is True:
                    tp += 1
                else:
                    fp += 1
            else:
                if is_prereq_gold is True:
                    fn += 1

    # Swap consistency across unordered pairs {a, b}
    for a, b in unordered_pairs:
        rec_ab = call_results[(a, b)]
        rec_ba = call_results[(b, a)]

        rel_ab = map_token_to_unordered_relation(rec_ab["raw_token"], a, b, a, b)
        rel_ba = map_token_to_unordered_relation(rec_ba["raw_token"], b, a, a, b)

        gold_label, is_unjudged = compute_gold_unordered_label(gold, a, b)
        if is_unjudged:
            excluded_unordered += 1

        if rel_ab == rel_ba and rel_ab != "PARSE_FAILURE":
            swap_consistent_pairs += 1

    accuracy_standard = (
        correct_calls_standard / total_calls_standard if total_calls_standard > 0 else 0.0
    )
    accuracy_sensitivity = (
        correct_calls_sensitivity / total_calls_sensitivity
        if total_calls_sensitivity > 0
        else 0.0
    )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    swap_consistency_rate = (
        swap_consistent_pairs / total_unordered if total_unordered > 0 else 0.0
    )

    # Latency percentiles
    latencies = [r["latency_s"] for r in call_records]
    mean_latency = float(np.mean(latencies)) if latencies else 0.0
    median_latency = float(np.median(latencies)) if latencies else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0

    # Token totals & cost
    snap = meter.snapshot()
    total_cost = (snap.input_tokens * price_in + snap.output_tokens * price_out) / 1_000_000

    summary: dict[str, Any] = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model_id": model_name,
        "dataset": "DSA_gold_standard_MEKG",
        "num_nodes": num_nodes,
        "total_calls": call_index,
        "planned_calls": planned_calls,
        "prices": {
            "price_in_per_m": price_in,
            "price_out_per_m": price_out,
        },
        "token_usage": {
            "input_tokens": snap.input_tokens,
            "output_tokens": snap.output_tokens,
            "reasoning_tokens": snap.reasoning_tokens,
            "cache_hit_tokens": snap.cache_hit_tokens,
            "cache_miss_tokens": snap.cache_miss_tokens,
            "estimated_cost_usd": round(total_cost, 6),
        },
        "timing_s": {
            "mean_latency": round(mean_latency, 4),
            "median_latency": round(median_latency, 4),
            "p95_latency": round(p95_latency, 4),
            "cumulative_latency": round(snap.latency_s, 4),
            "cumulative_retry_wait": round(snap.retry_wait_s, 4),
        },
        "retries_and_errors": {
            "attempts": snap.attempts,
            "retries": snap.retries,
            "parse_failures": snap.parse_failures,
            "parse_failure_rate": round(snap.parse_failures / call_index, 4) if call_index else 0.0,
        },
        "evaluation": {
            "accuracy_3way_standard": round(accuracy_standard, 4),
            "accuracy_3way_sensitivity_missing_as_none": round(accuracy_sensitivity, 4),
            "directed_edge_metrics": {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            },
            "direction_flips": direction_flips,
            "swap_consistency": {
                "consistent_pairs": swap_consistent_pairs,
                "total_unordered_pairs": total_unordered,
                "swap_consistency_rate": round(swap_consistency_rate, 4),
            },
            "confusion_matrix_standard": conf_matrix,
            "confusion_matrix_sensitivity": conf_matrix_sensitivity,
        },
    }

    summary_file = output_dir / "summary.json"
    with summary_file.open("w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, indent=2)

    print("\n--- PILOT SUMMARY ---")
    print(f"3-Way Accuracy (Standard): {accuracy_standard:.2%}")
    print(f"3-Way Accuracy (Sensitivity: Missing as NONE): {accuracy_sensitivity:.2%}")
    print(f"Directed Edge: Precision={precision:.2%}, Recall={recall:.2%}, F1={f1:.2%}")
    print(f"Direction Flips: {direction_flips}")
    print(f"Swap Consistency Rate: {swap_consistency_rate:.2%} ({swap_consistent_pairs}/{total_unordered})")
    print(f"Parse Failures: {snap.parse_failures} ({summary['retries_and_errors']['parse_failure_rate']:.2%})")
    print(f"Latency: Median={median_latency:.3f}s, P95={p95_latency:.3f}s")
    print(f"Tokens: In={snap.input_tokens}, Out={snap.output_tokens}, Reasoning={snap.reasoning_tokens}, CacheHit={snap.cache_hit_tokens}")
    print(f"Estimated Cost: ${total_cost:.4f}")
    print(f"Saved artifacts to {output_dir}")

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run zero-shot leave-one-out prerequisite evaluation pilot on DSA."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicit confirmation required to execute the pilot run.",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=900,
        help="Maximum allowable LLM calls (safety limit; default: 900).",
    )
    parser.add_argument(
        "--price-in",
        type=float,
        default=0.14,
        help="Price per 1M input tokens in USD (required for accurate cost accounting; default: 0.14).",
    )
    parser.add_argument(
        "--price-out",
        type=float,
        default=0.28,
        help="Price per 1M output tokens in USD (required for accurate cost accounting; default: 0.28).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to store pilot output artifacts (default: results/pilot/<UTC_TIMESTAMP>/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute offline simulation using FakeLLMClient without calling external APIs.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="DeepSeek model identifier (default from env DEEPSEEK_MODEL or 'deepseek-v4-flash').",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail fast on unparseable responses (default: record failure and treat as NONE).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Safety confirmation guard
    planned_calls = 29 * 28  # 812
    if not args.confirm:
        print("=" * 60)
        print("DSA PILOT PRE-FLIGHT CHECK")
        print(f"Planned calls: {planned_calls} (29 nodes * 28 candidates)")
        print("To proceed with execution, re-run with '--confirm'.")
        print("Example live run:")
        print("  python scripts/pilot_dsa_zero_shot.py --confirm --price-in 0.14 --price-out 0.28")
        print("Example offline test run:")
        print("  python scripts/pilot_dsa_zero_shot.py --confirm --dry-run")
        print("=" * 60)
        sys.exit(0)

    if planned_calls > args.max_calls:
        print(
            f"ERROR: Planned calls ({planned_calls}) exceeds --max-calls limit ({args.max_calls}). Refusing to run.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        output_dir = REPO_ROOT / "results" / "pilot" / now_str

    if args.dry_run:
        print("[DRY-RUN MODE] Initializing FakeLLMClient...")
        client = FakeLLMClient(
            responses=lambda s, u: "NONE",
            latency_s=0.005,
            model_id="fake-deepseek-v4-flash",
        )
        model_name = "fake-deepseek-v4-flash"
    else:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("ERROR: DEEPSEEK_API_KEY environment variable is required for live runs.", file=sys.stderr)
            sys.exit(1)
        client = DeepSeekClient(api_key=api_key, model=args.model)
        model_name = client.model

    run_pilot(
        client=client,
        model_name=model_name,
        output_dir=output_dir,
        price_in=args.price_in,
        price_out=args.price_out,
        max_calls=args.max_calls,
        strict_parse=args.strict,
    )


if __name__ == "__main__":
    main()
