"""
figures.py — Figure Generators for Phase 4 Report and Thesis
============================================================
Implements Figures F1, F2, F3, F4, F5, and F6 per Section 5 of the Analysis Plan.
Dual exports: vector PDF + PNG + CSV for each figure.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np

try:
    from .style import apply_thesis_style, export_figure, STRATEGY_PALETTE, STRATEGY_LABELS, STRATEGY_MARKERS
    from .stats import evaluate_dominance
    from .bootstrap import compute_series_stats
except ImportError:
    from style import apply_thesis_style, export_figure, STRATEGY_PALETTE, STRATEGY_LABELS, STRATEGY_MARKERS
    from stats import evaluate_dominance
    from bootstrap import compute_series_stats


def plot_f4_accuracy_comparison(
    t1_rows: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Figure F4: Accuracy by strategy and corpus.

    Shows Micro Precision, Recall, F1, and Shortlist Recall alongside Random Baseline.
    One panel per corpus (DSA, Metacademy).
    """
    apply_thesis_style()

    # Filter to primary configurations
    primaries = [r for r in t1_rows if "primary" in r.get("variant", "")]
    if not primaries:
        primaries = t1_rows

    corpora = sorted(list(set(r["corpus"] for r in primaries)))
    if not corpora:
        return

    fig, axes = plt.subplots(1, len(corpora), figsize=(7.0 * len(corpora), 5.5), squeeze=False)
    csv_data = []

    for c_idx, corpus in enumerate(corpora):
        ax = axes[0][c_idx]
        c_rows = [r for r in primaries if r["corpus"] == corpus]

        # Standard strategy ordering
        strat_order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
        c_rows.sort(key=lambda x: strat_order.index(x["strategy"]) if x["strategy"] in strat_order else 99)

        strategies = [r["strategy"] for r in c_rows]
        x = np.arange(len(strategies))
        width = 0.18

        f1_vals = [r["f1_micro"] for r in c_rows]
        p_vals = [r["precision_micro"] for r in c_rows]
        r_vals = [r["recall_micro"] for r in c_rows]
        sr_vals = [r["shortlist_recall_micro"] for r in c_rows]
        rand_vals = [r["random_baseline_recall"] for r in c_rows]

        rects1 = ax.bar(x - 1.5 * width, p_vals, width, label="Micro Precision", color="#4477AA")
        rects2 = ax.bar(x - 0.5 * width, r_vals, width, label="Micro Recall", color="#66CCEE")
        rects3 = ax.bar(x + 0.5 * width, f1_vals, width, label="Micro F1", color="#228833")
        rects4 = ax.bar(x + 1.5 * width, sr_vals, width, label="Shortlist Recall", color="#CCBB44")

        # Overlay random baseline points
        ax.plot(x + 1.5 * width, rand_vals, "r*", markersize=9, label="Random Baseline SR", zorder=5)

        clean_corpus_name = "DSA (29 Nodes)" if "DSA" in corpus else "Metacademy (141 Nodes)"
        ax.set_title(f"Accuracy: {clean_corpus_name}")
        ax.set_xticks(x)
        ax.set_xticklabels([STRATEGY_LABELS.get(s, s).replace(": ", "\n") for s in strategies], fontsize=8)
        ax.set_ylabel("Metric Value")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower right", fontsize=8)

        for r in c_rows:
            csv_data.append({
                "corpus": corpus,
                "strategy": r["strategy"],
                "variant": r["variant"],
                "precision_micro": r["precision_micro"],
                "recall_micro": r["recall_micro"],
                "f1_micro": r["f1_micro"],
                "shortlist_recall_micro": r["shortlist_recall_micro"],
                "random_baseline_recall": r["random_baseline_recall"],
            })

    fig.tight_layout()
    export_figure(fig, output_dir / "F4_accuracy_by_strategy", csv_data)
    plt.close(fig)


def plot_f5_sensitivity_panels(
    t1_rows: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Figure F5: One-at-a-time sensitivity panels.

    Panels for:
      - k in {5, 10, 20} (Strategy 3)
      - efSearch in {64, 128, 256} (Strategy 3)
      - (s_min, s_max) in {(2,5), (5,10), (10,20)} (Strategy 4)
      - theta in {0.4, 0.5, 0.6} (Strategy 2)
    """
    apply_thesis_style()

    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    csv_data = []

    # 1. Panel A: Strategy 3 - k variation
    ax_k = axes[0, 0]
    s3_k_rows = [r for r in t1_rows if r["strategy"] == "ann_retrieval" and "ef64" not in r["variant"] and "ef256" not in r["variant"]]
    if s3_k_rows:
        k_map = {5: [], 10: [], 20: []}
        for r in s3_k_rows:
            if "k=5" in r["variant"]:
                k_map[5].append(r)
            elif "k=20" in r["variant"]:
                k_map[20].append(r)
            elif "primary" in r["variant"] or "k=10" in r["variant"]:
                k_map[10].append(r)

        ks = [5, 10, 20]
        f1_means = [np.mean([x["f1_micro"] for x in k_map[k]]) if k_map[k] else np.nan for k in ks]
        sr_means = [np.mean([x["shortlist_recall_micro"] for x in k_map[k]]) if k_map[k] else np.nan for k in ks]

        ax_k.plot(ks, f1_means, "o-", label="Micro F1", color="#228833", lw=2)
        ax_k.plot(ks, sr_means, "s--", label="Shortlist Recall", color="#CCBB44", lw=2)
        ax_k.set_xlabel("Shortlist Size k")
        ax_k.set_ylabel("Score")
        ax_k.set_title("Strategy 3: k Sensitivity (ef=128)")
        ax_k.set_ylim(0, 1.05)
        ax_k.legend()
        for k, f1, sr in zip(ks, f1_means, sr_means):
            csv_data.append({"panel": "S3_k", "parameter": k, "f1_micro": f1, "shortlist_recall_micro": sr})

    # 2. Panel B: Strategy 3 - efSearch variation
    ax_ef = axes[0, 1]
    s3_ef_rows = [r for r in t1_rows if r["strategy"] == "ann_retrieval" and ("ef" in r["variant"] or "primary" in r["variant"])]
    if s3_ef_rows:
        ef_map = {64: [], 128: [], 256: []}
        for r in s3_ef_rows:
            if "ef=64" in r["variant"]:
                ef_map[64].append(r)
            elif "ef=256" in r["variant"]:
                ef_map[256].append(r)
            elif "primary" in r["variant"] or "ef=128" in r["variant"]:
                ef_map[128].append(r)

        efs = [64, 128, 256]
        f1_means = [np.mean([x["f1_micro"] for x in ef_map[e]]) if ef_map[e] else np.nan for e in efs]
        sr_means = [np.mean([x["shortlist_recall_micro"] for x in ef_map[e]]) if ef_map[e] else np.nan for e in efs]

        ax_ef.plot(efs, f1_means, "o-", label="Micro F1", color="#228833", lw=2)
        ax_ef.plot(efs, sr_means, "s--", label="Shortlist Recall", color="#CCBB44", lw=2)
        ax_ef.set_xlabel("efSearch (k=10)")
        ax_ef.set_ylabel("Score")
        ax_ef.set_title("Strategy 3: efSearch Sensitivity")
        ax_ef.set_ylim(0, 1.05)
        ax_ef.legend()
        for e, f1, sr in zip(efs, f1_means, sr_means):
            csv_data.append({"panel": "S3_efSearch", "parameter": e, "f1_micro": f1, "shortlist_recall_micro": sr})

    # 3. Panel C: Strategy 4 - (s_min, s_max) variation
    ax_bb = axes[1, 0]
    s4_rows = [r for r in t1_rows if r["strategy"] == "bounded_bucket"]
    if s4_rows:
        cfg_labels = ["(2,5)", "(5,10)", "(10,20)"]
        cfg_map = {"(2,5)": [], "(5,10)": [], "(10,20)": []}
        for r in s4_rows:
            if "s_min=2" in r["variant"]:
                cfg_map["(2,5)"].append(r)
            elif "s_min=10" in r["variant"]:
                cfg_map["(10,20)"].append(r)
            elif "primary" in r["variant"] or "s_min=5" in r["variant"]:
                cfg_map["(5,10)"].append(r)

        f1_means = [np.mean([x["f1_micro"] for x in cfg_map[c]]) if cfg_map[c] else np.nan for c in cfg_labels]
        sr_means = [np.mean([x["shortlist_recall_micro"] for x in cfg_map[c]]) if cfg_map[c] else np.nan for c in cfg_labels]

        ax_bb.plot(cfg_labels, f1_means, "o-", label="Micro F1", color="#228833", lw=2)
        ax_bb.plot(cfg_labels, sr_means, "s--", label="Shortlist Recall", color="#CCBB44", lw=2)
        ax_bb.set_xlabel("(s_min, s_max) Interval (nb=12)")
        ax_bb.set_ylabel("Score")
        ax_bb.set_title("Strategy 4: Bucket Bounds Sensitivity")
        ax_bb.set_ylim(0, 1.05)
        ax_bb.legend()
        for c, f1, sr in zip(cfg_labels, f1_means, sr_means):
            csv_data.append({"panel": "S4_bounds", "parameter": c, "f1_micro": f1, "shortlist_recall_micro": sr})

    # 4. Panel D: Strategy 2 - theta variation
    ax_th = axes[1, 1]
    s2_rows = [r for r in t1_rows if r["strategy"] == "embedding_threshold"]
    if s2_rows:
        th_map = {0.4: [], 0.5: [], 0.6: []}
        for r in s2_rows:
            if "theta=0.4" in r["variant"]:
                th_map[0.4].append(r)
            elif "theta=0.5" in r["variant"]:
                th_map[0.5].append(r)
            elif "theta=0.6" in r["variant"] or "primary" in r["variant"]:
                th_map[0.6].append(r)

        ths = [0.4, 0.5, 0.6]
        f1_means = [np.mean([x["f1_micro"] for x in th_map[t]]) if th_map[t] else np.nan for t in ths]
        calls_means = [np.mean([x["llm_calls_mean"] for x in th_map[t]]) if th_map[t] else np.nan for t in ths]

        ax_th.plot(ths, f1_means, "o-", label="Micro F1", color="#228833", lw=2)
        ax_th.set_xlabel("Cosine Threshold theta")
        ax_th.set_ylabel("Micro F1", color="#228833")
        ax_th.set_title("Strategy 2: Threshold Sensitivity")
        ax_th.set_ylim(0, 1.05)

        ax_th_calls = ax_th.twinx()
        ax_th_calls.plot(ths, calls_means, "s--", label="Mean LLM Calls", color="#EE6677", lw=2)
        ax_th_calls.set_ylabel("Mean LLM Calls", color="#EE6677")

        for t, f1, c in zip(ths, f1_means, calls_means):
            csv_data.append({"panel": "S2_theta", "parameter": t, "f1_micro": f1, "llm_calls_mean": c})

    fig.tight_layout()
    export_figure(fig, output_dir / "F5_sensitivity_panels", csv_data)
    plt.close(fig)


def plot_f6_cost_vs_accuracy(
    t1_rows: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Figure F6: Cost beside accuracy for each strategy and corpus (calls against F1).

    Evaluates Pareto dominance mechanics per Decisions D3 and D5.
    """
    apply_thesis_style()

    primaries = [r for r in t1_rows if "primary" in r.get("variant", "")]
    if not primaries:
        primaries = t1_rows

    corpora = sorted(list(set(r["corpus"] for r in primaries)))
    if not corpora:
        return

    fig, axes = plt.subplots(1, len(corpora), figsize=(7.0 * len(corpora), 5.5), squeeze=False)
    csv_data = []

    for c_idx, corpus in enumerate(corpora):
        ax = axes[0][c_idx]
        c_rows = [r for r in primaries if r["corpus"] == corpus]

        clean_corpus_name = "DSA (29 Nodes)" if "DSA" in corpus else "Metacademy (141 Nodes)"
        ax.set_title(f"Cost vs. Accuracy: {clean_corpus_name}")
        ax.set_xlabel("Mean LLM Calls per Insertion")
        ax.set_ylabel("Micro F1 Score")

        points: Dict[str, Dict[str, float]] = {}
        for r in c_rows:
            strat = r["strategy"]
            color = STRATEGY_PALETTE.get(strat, "#000000")
            marker = STRATEGY_MARKERS.get(strat, "o")
            calls = r["llm_calls_mean"]
            f1 = r["f1_micro"]

            ax.scatter(calls, f1, color=color, marker=marker, s=90, label=STRATEGY_LABELS.get(strat, strat), zorder=4)
            ax.annotate(
                f"{strat}\n({calls:.1f}, {f1:.3f})",
                (calls, f1),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
            )
            points[strat] = {"calls": calls, "f1": f1}
            csv_data.append({
                "corpus": corpus,
                "strategy": strat,
                "variant": r["variant"],
                "calls": calls,
                "f1": f1,
            })

        # Evaluate dominance pairs
        strat_names = list(points.keys())
        for i in range(len(strat_names)):
            for j in range(i + 1, len(strat_names)):
                s_a, s_b = strat_names[i], strat_names[j]
                dom = evaluate_dominance(points[s_a], points[s_b])
                csv_data.append({
                    "corpus": corpus,
                    "strategy": f"{s_a} vs {s_b}",
                    "variant": "dominance_evaluation",
                    "calls": 0.0,
                    "f1": 0.0,
                    "dominance_result": dom,
                })

        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower right", fontsize=8)

    fig.tight_layout()
    export_figure(fig, output_dir / "F6_cost_vs_accuracy_dominance", csv_data)
    plt.close(fig)


def plot_f1_calls_scaling(
    t2_rows: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Figure F1: LLM calls per insertion vs n, log-x, one line per strategy

    (primary configurations), with 95% percentile bootstrap interval bars (D1).
    """
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    csv_data = []

    # Filter to primary configurations
    primaries = [r for r in t2_rows if "primary" in r.get("variant", "")]
    if not primaries:
        primaries = t2_rows

    strategies = sorted(list(set(r["strategy"] for r in primaries)))
    strat_order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
    strategies.sort(key=lambda s: strat_order.index(s) if s in strat_order else 99)

    for strat in strategies:
        color = STRATEGY_PALETTE.get(strat, "#333333")
        marker = STRATEGY_MARKERS.get(strat, "o")
        label = STRATEGY_LABELS.get(strat, strat)

        s_rows = [r for r in primaries if r["strategy"] == strat]
        s_rows.sort(key=lambda x: int(x["size_n"]))

        sizes = [int(r["size_n"]) for r in s_rows]
        means = [float(r["llm_calls_mean"]) for r in s_rows]
        lows = [float(r.get("llm_calls_ci_mean_low", r["llm_calls_mean"])) for r in s_rows]
        highs = [float(r.get("llm_calls_ci_mean_high", r["llm_calls_mean"])) for r in s_rows]

        y_err = [
            np.array(means) - np.array(lows),
            np.array(highs) - np.array(means),
        ]
        ax.errorbar(sizes, means, yerr=y_err, label=label, color=color, marker=marker, capsize=4, lw=1.75)

        for s, m, l, h, r in zip(sizes, means, lows, highs, s_rows):
            csv_data.append({
                "strategy": strat,
                "variant": r["variant"],
                "n": s,
                "llm_calls_mean": m,
                "llm_calls_ci_low": l,
                "llm_calls_ci_high": h,
                "llm_calls_median": r.get("llm_calls_median", m),
                "llm_calls_std": r.get("llm_calls_std", 0.0),
            })

    ax.set_xscale("log")
    ax.set_xlabel("Graph Size n (log scale)")
    ax.set_ylabel("LLM Calls per Insertion")
    ax.set_title("Figure F1: LLM Calls Scaling with Graph Size (95% Bootstrap CI)")
    ax.legend(loc="upper left")

    fig.tight_layout()
    export_figure(fig, output_dir / "F1_calls_scaling", csv_data)
    plt.close(fig)


def plot_f2_wallclock_scaling(
    t2_rows: List[Dict[str, Any]],
    output_dir: Path,
) -> None:
    """Figure F2: total_s vs n, log-x layout; and a second panel splitting

    shortlist_s from decide_s.
    """
    apply_thesis_style()
    fig, (ax_tot, ax_split) = plt.subplots(1, 2, figsize=(14, 5.5))
    csv_data = []

    primaries = [r for r in t2_rows if "primary" in r.get("variant", "")]
    if not primaries:
        primaries = t2_rows

    strategies = sorted(list(set(r["strategy"] for r in primaries)))
    strat_order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
    strategies.sort(key=lambda s: strat_order.index(s) if s in strat_order else 99)

    for strat in strategies:
        color = STRATEGY_PALETTE.get(strat, "#333333")
        marker = STRATEGY_MARKERS.get(strat, "o")
        label = STRATEGY_LABELS.get(strat, strat)

        s_rows = [r for r in primaries if r["strategy"] == strat]
        s_rows.sort(key=lambda x: int(x["size_n"]))

        sizes = [int(r["size_n"]) for r in s_rows]
        tot_means = [float(r["total_s_mean"]) for r in s_rows]
        tot_lows = [float(r.get("total_s_ci_mean_low", r["total_s_mean"])) for r in s_rows]
        tot_highs = [float(r.get("total_s_ci_mean_high", r["total_s_mean"])) for r in s_rows]

        sh_means = [float(r["shortlist_s_mean"]) for r in s_rows]
        dec_means = [float(r["decide_s_mean"]) for r in s_rows]

        # Total latency in left panel
        y_err = [
            np.array(tot_means) - np.array(tot_lows),
            np.array(tot_highs) - np.array(tot_means),
        ]
        ax_tot.errorbar(sizes, tot_means, yerr=y_err, label=label, color=color, marker=marker, capsize=4, lw=1.75)

        # Split components in right panel
        ax_split.plot(sizes, sh_means, color=color, marker=marker, linestyle="--", lw=1.5, label=f"{strat} (shortlist)")
        ax_split.plot(sizes, dec_means, color=color, marker=marker, linestyle="-", lw=1.5, label=f"{strat} (decide)")

        for s, tm, tl, th, sh, dec, r in zip(sizes, tot_means, tot_lows, tot_highs, sh_means, dec_means, s_rows):
            csv_data.append({
                "strategy": strat,
                "variant": r["variant"],
                "n": s,
                "total_s_mean": tm,
                "total_s_ci_low": tl,
                "total_s_ci_high": th,
                "shortlist_s_mean": sh,
                "decide_s_mean": dec,
                "clean_total_s_mean_post_hoc": r.get("clean_total_s_mean_post_hoc_not_preregistered", tm),
            })

    ax_tot.set_xscale("log")
    ax_tot.set_xlabel("Graph Size n (log scale)")
    ax_tot.set_ylabel("Total Latency per Insertion (s)")
    ax_tot.set_title("Panel A: Total Wall-Clock Latency vs n")
    ax_tot.legend(loc="upper left")

    ax_split.set_xscale("log")
    ax_split.set_xlabel("Graph Size n (log scale)")
    ax_split.set_ylabel("Component Latency (s)")
    ax_split.set_title("Panel B: Shortlist vs. Decide Component Split")
    ax_split.legend(loc="upper left", fontsize=7)

    fig.tight_layout()
    export_figure(fig, output_dir / "F2_wallclock_scaling", csv_data)
    plt.close(fig)


def plot_f3_premise_check(
    t2_rows: List[Dict[str, Any]],
    output_dir: Path,
    k_cap: int = 10,
    smax_cap: int = 10,
) -> None:
    """Figure F3: Premise check: calls and total_s vs n for Strategies 3 and 4

    on a linear y-axis, with the cap (k, s_max) drawn as a reference line (plan line 77).
    Two panels: Left panel = LLM calls vs n; Right panel = total_s vs n.
    """
    apply_thesis_style()
    fig, (ax_calls, ax_time) = plt.subplots(1, 2, figsize=(14, 5.5))
    csv_data = []

    # Strategy 3 (primary: k=10)
    s3_rows = [r for r in t2_rows if r["strategy"] == "ann_retrieval" and "primary" in r.get("variant", "")]
    if not s3_rows:
        s3_rows = [r for r in t2_rows if r["strategy"] == "ann_retrieval" and "k=10" in r.get("variant", "")]
    s3_rows.sort(key=lambda x: int(x["size_n"]))

    # Strategy 4 (primary: s_max=10)
    s4_rows = [r for r in t2_rows if r["strategy"] == "bounded_bucket" and "primary" in r.get("variant", "")]
    if not s4_rows:
        s4_rows = [r for r in t2_rows if r["strategy"] == "bounded_bucket" and "s_max=10" in r.get("variant", "")]
    s4_rows.sort(key=lambda x: int(x["size_n"]))

    # Panel A: LLM Calls on linear scale
    if s3_rows:
        sizes_3 = [int(r["size_n"]) for r in s3_rows]
        calls_3 = [float(r["llm_calls_mean"]) for r in s3_rows]
        tot_3 = [float(r["total_s_mean"]) for r in s3_rows]
        ax_calls.plot(sizes_3, calls_3, "o-", label="Strategy 3 (ANN, k=10)", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
        ax_time.plot(sizes_3, tot_3, "o-", label="Strategy 3 (ANN, k=10)", color=STRATEGY_PALETTE["ann_retrieval"], lw=2)
        for s, c, t in zip(sizes_3, calls_3, tot_3):
            csv_data.append({"strategy": "ann_retrieval", "n": s, "llm_calls_mean": c, "total_s_mean": t, "cap": k_cap})

    if s4_rows:
        sizes_4 = [int(r["size_n"]) for r in s4_rows]
        calls_4 = [float(r["llm_calls_mean"]) for r in s4_rows]
        tot_4 = [float(r["total_s_mean"]) for r in s4_rows]
        ax_calls.plot(sizes_4, calls_4, "s-", label="Strategy 4 (Bucket, s_max=10)", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
        ax_time.plot(sizes_4, tot_4, "s-", label="Strategy 4 (Bucket, s_max=10)", color=STRATEGY_PALETTE["bounded_bucket"], lw=2)
        for s, c, t in zip(sizes_4, calls_4, tot_4):
            csv_data.append({"strategy": "bounded_bucket", "n": s, "llm_calls_mean": c, "total_s_mean": t, "cap": smax_cap})

    # Reference cap line on calls panel
    ax_calls.axhline(k_cap, color="red", linestyle="--", lw=1.5, label=f"Theoretical Bound (k = s_max = {k_cap})")

    ax_calls.set_xlabel("Graph Size n (linear scale)")
    ax_calls.set_ylabel("Realised LLM Calls per Insertion")
    ax_calls.set_title("Panel A: LLM Calls vs. Cap (Linear Scale)")
    ax_calls.set_ylim(0, max(k_cap, smax_cap) * 1.4)
    ax_calls.legend(loc="lower right")

    ax_time.set_xlabel("Graph Size n (linear scale)")
    ax_time.set_ylabel("Total Latency per Insertion (s)")
    ax_time.set_title("Panel B: Total Wall-Clock Latency (Linear Scale)")
    ax_time.legend(loc="upper left")

    fig.tight_layout()
    export_figure(fig, output_dir / "F3_premise_check", csv_data)
    plt.close(fig)
