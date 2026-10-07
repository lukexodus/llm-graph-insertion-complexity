#!/usr/bin/env python3
"""
pilot_dsa_zero_shot.py — INFRA-006 / FIX-004
============================================
Offline/online pilot script for zero-shot leave-one-out prerequisite evaluation on DSA.

Features:
  - Brute-force leave-one-out: 29 nodes * 28 candidates = 812 calls ([D-29])
  - Strict guardrails: requires --confirm, checks --max-calls limit
  - No hardcoded prices: accepts --price-in and --price-out (per million tokens)
  - Full evaluation: 3-way accuracy, confusion matrix, per-held-out-node scoring,
    direction flips, swap consistency, parse failure rate, latency percentiles,
    token totals (including reasoning and prompt cache), and estimated cost.
  - Sensitivity analysis for DSA unjudged row ([D-30], [D-32])
  - Pure scoring function score_pilot() callable offline or via --rescore
  - Saves raw call records (JSONL) and aggregate metrics (JSON) under results/pilot/<UTC_TIMESTAMP>/
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np

# Add src to sys.path if not present
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_insertion.decision import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    DecisionParseError,
    PairwiseDecisionStep,
    parse_token,
)
from graph_insertion.graph_representation import ConceptGraph, embed_text
from graph_insertion.llm import (
    DeepSeekClient,
    FakeLLMClient,
    LLMClient,
    MeteredLLMClient,
)
from graph_insertion.loader import load_corpus
from graph_insertion.scoring import (
    NodeScore,
    aggregate_scores,
    score_node_insertion,
)


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


def score_pilot(
    call_records: Sequence[dict[str, Any]],
    gold: Any,
    gold_graph: Optional[ConceptGraph] = None,
) -> dict[str, Any]:
    """Pure evaluation function over recorded pilot pairwise calls.

    Computes 3-way accuracy, confusion matrix, direction flips, swap consistency,
    and per-held-out-node insertion scores (micro/macro/sensitivity).

    Parameters
    ----------
    call_records:
        Sequence of recorded call dicts containing 'new_name', 'candidate',
        and 'response_text' (or 'raw_token').
    gold:
        GoldJudgmentSet ground truth.
    gold_graph:
        Optional reference ConceptGraph. If None, loaded from DSA corpus.

    Returns
    -------
    dict[str, Any]
        Dictionary containing 'evaluation', 'node_scores', and 'aggregate'.
    """
    if gold_graph is None:
        corpus = load_corpus("DSA_gold_standard_MEKG")
        gold_graph = corpus.graph

    call_results: dict[tuple[str, str], dict[str, Any]] = {
        (r["new_name"], r["candidate"]): r for r in call_records
    }
    nodes = sorted(list({r["new_name"] for r in call_records} | {r["candidate"] for r in call_records}))

    # 1. Unordered pair swap consistency
    unordered_pairs = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            unordered_pairs.append((nodes[i], nodes[j]))

    total_unordered = len(unordered_pairs)
    swap_consistent_pairs = 0
    excluded_unordered = 0

    for a, b in unordered_pairs:
        if (a, b) in call_results and (b, a) in call_results:
            rec_ab = call_results[(a, b)]
            rec_ba = call_results[(b, a)]
            tok_ab = parse_token(rec_ab.get("response_text", rec_ab.get("raw_token", ""))) or "PARSE_FAILURE"
            tok_ba = parse_token(rec_ba.get("response_text", rec_ba.get("raw_token", ""))) or "PARSE_FAILURE"

            rel_ab = map_token_to_unordered_relation(tok_ab, a, b, a, b)
            rel_ba = map_token_to_unordered_relation(tok_ba, b, a, a, b)

            gold_label, is_unjudged = compute_gold_unordered_label(gold, a, b)
            if is_unjudged:
                excluded_unordered += 1

            if rel_ab == rel_ba and rel_ab != "PARSE_FAILURE":
                swap_consistent_pairs += 1

    swap_consistency_rate = (
        swap_consistent_pairs / total_unordered if total_unordered > 0 else 0.0
    )

    # 2. 3-way evaluation on calls
    classes = ["X_PREREQ_Y", "Y_PREREQ_X", "NONE"]
    pred_col_names = ["X_PREREQ_Y", "Y_PREREQ_X", "NONE", "PARSE_FAILURE"]
    conf_matrix = {g: {p: 0 for p in pred_col_names} for g in classes}
    conf_matrix_sensitivity = {g: {p: 0 for p in pred_col_names} for g in classes}

    correct_calls_standard = 0
    total_calls_standard = 0
    correct_calls_sensitivity = 0
    total_calls_sensitivity = 0
    direction_flips = 0
    calls_with_gold_and_pred_edge = 0

    for (new_name, cand), rec in call_results.items():
        is_prereq_gold = gold.judgment_for_edge(new_name, cand)
        is_reverse_gold = gold.judgment_for_edge(cand, new_name)

        tok = parse_token(rec.get("response_text", rec.get("raw_token", "")))
        pred_token = tok if tok in classes else "PARSE_FAILURE"

        gold_token_standard: Optional[str] = None
        gold_token_sens: str

        if is_prereq_gold is None or is_reverse_gold is None:
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
            gold_token_standard = "ANOMALY"
            gold_token_sens = "ANOMALY"

        if gold_token_standard in classes:
            total_calls_standard += 1
            conf_matrix[gold_token_standard][pred_token] += 1
            if pred_token == gold_token_standard:
                correct_calls_standard += 1
            if gold_token_standard in ("X_PREREQ_Y", "Y_PREREQ_X") and pred_token in ("X_PREREQ_Y", "Y_PREREQ_X"):
                calls_with_gold_and_pred_edge += 1
                if (gold_token_standard == "X_PREREQ_Y" and pred_token == "Y_PREREQ_X") or (
                    gold_token_standard == "Y_PREREQ_X" and pred_token == "X_PREREQ_Y"
                ):
                    direction_flips += 1

        if gold_token_sens in classes:
            total_calls_sensitivity += 1
            conf_matrix_sensitivity[gold_token_sens][pred_token] += 1
            if pred_token == gold_token_sens:
                correct_calls_sensitivity += 1

    accuracy_standard = (
        correct_calls_standard / total_calls_standard if total_calls_standard > 0 else 0.0
    )
    accuracy_sensitivity = (
        correct_calls_sensitivity / total_calls_sensitivity if total_calls_sensitivity > 0 else 0.0
    )
    direction_flip_rate = (
        direction_flips / calls_with_gold_and_pred_edge if calls_with_gold_and_pred_edge > 0 else 0.0
    )

    # 3. Per-held-out-node insertion evaluation
    node_scores: list[NodeScore] = []
    for n in nodes:
        node_calls = [r for r in call_records if r["new_name"] == n]
        candidates = [r["candidate"] for r in node_calls]
        decided_edges = []
        for r in node_calls:
            tok = parse_token(r.get("response_text", r.get("raw_token", "")))
            cand = r["candidate"]
            if tok == "X_PREREQ_Y":
                # new_node n is prereq of cand -> edge (n, cand)
                decided_edges.append((n, cand))
            elif tok == "Y_PREREQ_X":
                # cand is prereq of new_node n -> edge (cand, n)
                decided_edges.append((cand, n))

        n_score = score_node_insertion(
            node=n,
            gold_graph=gold_graph,
            judgments=gold,
            shortlist_candidates=candidates,
            decided_edges=decided_edges,
        )
        node_scores.append(n_score)

    agg = aggregate_scores(node_scores)

    evaluation = {
        "accuracy_3way_standard": round(accuracy_standard, 4),
        "accuracy_3way_sensitivity_missing_as_none": round(accuracy_sensitivity, 4),
        "node_insertion_scoring": {
            "micro": {
                "precision": round(agg.precision_micro, 4),
                "recall": round(agg.recall_micro, 4),
                "f1": round(agg.f1_micro, 4),
                "shortlist_recall": round(agg.shortlist_recall_micro, 4),
            },
            "macro": {
                "precision": round(agg.precision_macro, 4) if agg.precision_macro is not None else None,
                "recall": round(agg.recall_macro, 4) if agg.recall_macro is not None else None,
                "f1": round(agg.f1_macro, 4) if agg.f1_macro is not None else None,
                "shortlist_recall": round(agg.shortlist_recall_macro, 4) if agg.shortlist_recall_macro is not None else None,
                "n_precision_defined": agg.n_precision_defined,
                "n_recall_defined": agg.n_recall_defined,
                "n_f1_defined": agg.n_f1_defined,
                "n_shortlist_recall_defined": agg.n_shortlist_recall_defined,
            },
            "sensitivity": {
                "precision_micro": round(agg.precision_micro_sensitivity, 4),
                "recall_micro": round(agg.recall_micro_sensitivity, 4),
                "f1_micro": round(agg.f1_micro_sensitivity, 4),
                "precision_macro": round(agg.precision_macro_sensitivity, 4) if agg.precision_macro_sensitivity is not None else None,
                "recall_macro": round(agg.recall_macro_sensitivity, 4) if agg.recall_macro_sensitivity is not None else None,
                "f1_macro": round(agg.f1_macro_sensitivity, 4) if agg.f1_macro_sensitivity is not None else None,
                "n_precision_sensitivity_defined": agg.n_precision_sensitivity_defined,
                "n_recall_sensitivity_defined": agg.n_recall_sensitivity_defined,
                "n_f1_sensitivity_defined": agg.n_f1_sensitivity_defined,
            },
            "totals": {
                "tp": agg.tp_total,
                "fp": agg.fp_total,
                "fn": agg.fn_total,
                "fp_sensitivity": agg.fp_total_sensitivity,
                "unjudged_predictions": agg.excluded_total,
            },
        },
        "direction_flips": direction_flips,
        "calls_with_gold_and_pred_edge": calls_with_gold_and_pred_edge,
        "direction_flip_rate": round(direction_flip_rate, 4),
        "swap_consistency": {
            "consistent_pairs": swap_consistent_pairs,
            "total_unordered_pairs": total_unordered,
            "swap_consistency_rate": round(swap_consistency_rate, 4),
        },
        "confusion_matrix_standard": conf_matrix,
        "confusion_matrix_sensitivity": conf_matrix_sensitivity,
    }

    return {
        "evaluation": evaluation,
        "node_scores": [asdict(s) for s in node_scores],
        "aggregate": asdict(agg),
    }


def evaluate_acceptance(summary: dict[str, Any]) -> dict[str, Any]:
    """Evaluate DSA pilot against G1 validity and G2 usefulness criteria ([D-34]).

    Parameters
    ----------
    summary:
        Pilot summary dictionary containing configuration, usage, retries,
        and evaluation results.

    Returns
    -------
    dict[str, Any]
        Per-criterion evaluations and overall PASS / FAIL / CONDITIONAL verdict.
    """
    total_calls = summary.get("total_calls", 812) or 812

    # G1 Validity quantities
    tf = summary.get("transport_failure_count", summary.get("transport_failures", 0))
    pf = summary.get("parse_failure_count", summary.get("retries_and_errors", {}).get("parse_failures", 0))
    pf_rate = summary.get("retries_and_errors", {}).get("parse_failure_rate", (pf / total_calls) if total_calls else 0.0)
    rt = summary.get("token_usage", {}).get("reasoning_tokens", 0)

    conf_m = summary.get("configured_model") or summary.get("model_id") or ""
    obs_m = summary.get("observed_model_ids", [])
    pv = summary.get("prompt_version") or summary.get("PROMPT_VERSION") or ""

    retries = summary.get("retried_call_count", summary.get("retries_and_errors", {}).get("retries", 0))
    retry_rate = (retries / total_calls) if total_calls else 0.0

    g1_tf_pass = (tf == 0)
    g1_pf_pass = (pf <= 8) and (pf_rate <= 0.01)
    g1_rt_pass = (rt == 0)
    obs_set = set(obs_m)
    g1_model_pass = (len(obs_set) == 1)
    configured_equals_observed = bool(obs_set) and (obs_set == {conf_m})
    g1_pv_pass = (pv == "v2")
    g1_retries_pass = (retry_rate <= 0.02)

    g1_pass = (
        g1_tf_pass
        and g1_pf_pass
        and g1_rt_pass
        and g1_model_pass
        and g1_pv_pass
        and g1_retries_pass
    )
    g1_verdict = "PASS" if g1_pass else "FAIL"

    # G2 Usefulness quantities
    ev = summary.get("evaluation", {})
    nis = ev.get("node_insertion_scoring", {})
    micro = nis.get("micro", {})
    recall = micro.get("recall", ev.get("recall_micro", 0.0))
    f1 = micro.get("f1", ev.get("f1_micro", 0.0))

    flips = ev.get("direction_flips", 0)
    flip_denom = ev.get("calls_with_gold_and_pred_edge", 0)
    if "direction_flip_rate" in ev:
        flip_rate = ev["direction_flip_rate"]
    else:
        flip_rate = (flips / flip_denom) if flip_denom > 0 else 0.0

    g2_recall_pass = (recall >= 0.70)
    g2_f1_pass = (f1 >= 0.50)
    g2_flips_pass = (flip_rate <= 0.15)

    if g2_recall_pass and g2_f1_pass and g2_flips_pass:
        g2_verdict = "PASS"
    elif f1 < 0.35 or recall < 0.50:
        g2_verdict = "FAIL"
    else:
        g2_verdict = "CONDITIONAL"

    overall_verdict = g2_verdict if g1_pass else "INVALID"

    return {
        "g1_validity": {
            "transport_failures": {"value": tf, "passed": g1_tf_pass},
            "parse_failures": {"value": pf, "rate": round(pf_rate, 4), "passed": g1_pf_pass},
            "reasoning_tokens": {"value": rt, "passed": g1_rt_pass},
            "model_identity": {
                "configured": conf_m,
                "observed": obs_m,
                "configured_equals_observed": configured_equals_observed,
                "passed": g1_model_pass,
            },
            "prompt_version": {"value": pv, "passed": g1_pv_pass},
            "retries": {"value": retries, "rate": round(retry_rate, 4), "passed": g1_retries_pass},
            "verdict": g1_verdict,
        },
        "g2_usefulness": {
            "recall_micro": {"value": round(recall, 4), "threshold_pass": 0.70, "threshold_fail": 0.50, "passed": g2_recall_pass},
            "f1_micro": {"value": round(f1, 4), "threshold_pass": 0.50, "threshold_fail": 0.35, "passed": g2_f1_pass},
            "direction_flip_rate": {"value": round(flip_rate, 4), "flips": flips, "denominator": flip_denom, "threshold_pass": 0.15, "passed": g2_flips_pass},
            "verdict": g2_verdict,
        },
        "overall_verdict": overall_verdict,
    }


def print_pilot_summary(summary: dict[str, Any]) -> None:
    """Print readable summary to stdout."""
    def _format_metric(val: Optional[float]) -> str:
        if val is None:
            return "undefined"
        return f"{val:.2%}"

    ev = summary.get("evaluation", {})
    nis = ev.get("node_insertion_scoring", {})
    micro = nis.get("micro", {})
    macro = nis.get("macro", {})
    totals = nis.get("totals", {})
    swap = ev.get("swap_consistency", {})

    print("\n--- PILOT SUMMARY ---")
    print(f"3-Way Accuracy (Standard): {_format_metric(ev.get('accuracy_3way_standard'))}")
    print(f"3-Way Accuracy (Sensitivity: Missing as NONE): {_format_metric(ev.get('accuracy_3way_sensitivity_missing_as_none'))}")
    print(
        f"Node Insertion Micro: Precision={_format_metric(micro.get('precision'))}, "
        f"Recall={_format_metric(micro.get('recall'))}, F1={_format_metric(micro.get('f1'))}"
    )
    print(
        f"Node Insertion Macro: Precision={_format_metric(macro.get('precision'))}, "
        f"Recall={_format_metric(macro.get('recall'))}, F1={_format_metric(macro.get('f1'))}"
    )
    print(
        f"Totals: TP={totals.get('tp', 0)}, FP={totals.get('fp', 0)}, FN={totals.get('fn', 0)}, "
        f"Unjudged Predictions={totals.get('unjudged_predictions', 0)}"
    )
    print(
        f"Direction Flips: {ev.get('direction_flips', 0)} "
        f"({_format_metric(ev.get('direction_flip_rate'))} of {ev.get('calls_with_gold_and_pred_edge', 0)} edge calls)"
    )
    print(
        f"Swap Consistency Rate: {_format_metric(swap.get('swap_consistency_rate'))} "
        f"({swap.get('consistent_pairs', 0)}/{swap.get('total_unordered_pairs', 0)})"
    )

    acc = summary.get("acceptance", {})
    if acc:
        g1 = acc.get("g1_validity", {})
        g2 = acc.get("g2_usefulness", {})
        print(f"Acceptance G1 Validity: {g1.get('verdict', 'N/A')}")
        print(f"Acceptance G2 Usefulness: {g2.get('verdict', 'N/A')}")
        print(f"Overall Acceptance Verdict: {acc.get('overall_verdict', 'N/A')}")

    retries = summary.get("retries_and_errors", {})
    if "parse_failures" in retries:
        print(f"Parse Failures: {retries.get('parse_failures')} ({retries.get('parse_failure_rate', 0.0):.2%})")
    timing = summary.get("timing_s", {})
    if "median_latency" in timing:
        print(f"Latency: Median={timing.get('median_latency', 0.0):.3f}s, P95={timing.get('p95_latency', 0.0):.3f}s")
    usage = summary.get("token_usage", {})
    if "input_tokens" in usage:
        print(
            f"Tokens: In={usage.get('input_tokens')}, Out={usage.get('output_tokens')}, "
            f"Reasoning={usage.get('reasoning_tokens')}, CacheHit={usage.get('cache_hit_tokens')}"
        )
        print(f"Estimated Cost: ${usage.get('estimated_cost_usd', 0.0):.4f}")


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
    call_index = 0

    with raw_calls_file.open("w", encoding="utf-8") as f_raw:
        for new_node in nodes:
            # Leave-one-out candidates: all nodes except new_node
            candidates = tuple(n for n in nodes if n != new_node)
            for cand in candidates:
                call_index += 1
                user_prompt = decision_step.build_user_prompt(new_node, cand, domain_context)
                resp = meter.complete(system=SYSTEM_PROMPT, user=user_prompt)

                parsed = parse_token(resp.text)
                if parsed is None:
                    meter.record_parse_failure(resp.text)
                    if strict_parse:
                        raise DecisionParseError(
                            f"Unparseable response for pair ({new_node!r}, {cand!r}): {resp.text!r}"
                        )
                raw_token = parsed if parsed is not None else "PARSE_FAILURE"

                rec = {
                    "call_index": call_index,
                    "new_name": new_node,
                    "candidate": cand,
                    "domain_context": domain_context,
                    "user_prompt": user_prompt,
                    "response_text": resp.text,
                    "raw_token": raw_token,
                    "latency_s": resp.latency_s,
                    "model": resp.model_id,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "reasoning_tokens": resp.reasoning_tokens,
                    "cache_hit_tokens": resp.cache_hit_tokens,
                    "cache_miss_tokens": resp.cache_miss_tokens,
                    "attempts": resp.attempts,
                    "retry_wait_s": resp.retry_wait_s,
                }
                call_records.append(rec)
                f_raw.write(json.dumps(rec) + "\n")

    print(f"Completed {call_index} calls. Computing evaluation metrics...")

    # 2. Pure scoring function execution
    scored = score_pilot(call_records, gold, graph)

    # Latency percentiles
    latencies = [r["latency_s"] for r in call_records]
    mean_latency = float(np.mean(latencies)) if latencies else 0.0
    median_latency = float(np.median(latencies)) if latencies else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0

    # Token totals & cost
    snap = meter.snapshot()
    total_cost = (snap.input_tokens * price_in + snap.output_tokens * price_out) / 1_000_000

    # Client parameters extraction
    inner_client = getattr(client, "client", client)
    base_url = getattr(inner_client, "base_url", getattr(client, "base_url", None))
    temperature = getattr(inner_client, "temperature", getattr(client, "temperature", None))
    t_obj = getattr(inner_client, "thinking", getattr(client, "thinking", None))
    thinking_mode = t_obj.get("type", None) if isinstance(t_obj, dict) else (str(t_obj) if t_obj is not None else None)
    max_tokens = getattr(inner_client, "max_tokens", getattr(client, "max_tokens", None))

    observed_model_ids = sorted(list(set(r.get("model", "") for r in call_records if r.get("model"))))
    if not observed_model_ids and hasattr(client, "model_ids_seen"):
        observed_model_ids = sorted(list(client.model_ids_seen))

    summary: dict[str, Any] = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "configured_model": model_name,
        "model_id": model_name,
        "observed_model_ids": observed_model_ids,
        "base_url": base_url,
        "temperature": temperature,
        "thinking_mode": thinking_mode,
        "max_tokens": max_tokens,
        "dataset": "DSA_gold_standard_MEKG",
        "num_nodes": num_nodes,
        "total_calls": call_index,
        "planned_calls": planned_calls,
        "parse_failure_count": snap.parse_failures,
        "retried_call_count": snap.retries,
        "transport_failure_count": 0,
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
        "evaluation": scored["evaluation"],
    }
    summary["acceptance"] = evaluate_acceptance(summary)

    summary_file = output_dir / "summary.json"
    with summary_file.open("w", encoding="utf-8") as f_sum:
        json.dump(summary, f_sum, indent=2)

    print_pilot_summary(summary)
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
        "--offline-fake",
        "--dry-run",
        dest="offline_fake",
        action="store_true",
        help="Execute offline simulation using FakeLLMClient without calling external APIs.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="DeepSeek model identifier (default from env DEEPSEEK_MODEL or 'deepseek-flash').",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail fast on unparseable responses (default: record failure and treat as NONE).",
    )
    parser.add_argument(
        "--rescore",
        type=str,
        default=None,
        help="Recompute evaluation summary from an existing raw_calls.jsonl file without making API calls.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Re-scoring existing raw_calls.jsonl
    if args.rescore:
        rescore_path = Path(args.rescore)
        if not rescore_path.exists():
            print(f"ERROR: {rescore_path} does not exist.", file=sys.stderr)
            sys.exit(1)

        records: list[dict[str, Any]] = []
        with rescore_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        corpus = load_corpus("DSA_gold_standard_MEKG")
        scored = score_pilot(records, corpus.judgments, corpus.graph)

        output_dir = rescore_path.parent
        summary_file = output_dir / "summary.json"
        summary: dict[str, Any] = {}
        if summary_file.exists():
            try:
                with summary_file.open("r", encoding="utf-8") as f:
                    summary = json.load(f)
            except Exception:
                pass

        summary["evaluation"] = scored["evaluation"]
        summary["acceptance"] = evaluate_acceptance(summary)
        summary["re-scored_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print(f"Successfully re-scored {len(records)} calls from {rescore_path}")
        print_pilot_summary(summary)
        return

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
        print("  python scripts/pilot_dsa_zero_shot.py --confirm --offline-fake")
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

    if args.offline_fake:
        print("[OFFLINE-FAKE MODE] Initializing FakeLLMClient...")
        client = FakeLLMClient(
            responses=lambda s, u: "NONE",
            latency_s=0.005,
            model_id="fake-deepseek-flash",
        )
        model_name = "fake-deepseek-flash"
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
