"""posthoc_figures.py — Figures F7, F8 and F9 (POST HOC, not pre-registered).

Layout follows direction from the ANALYSIS-004 specification and
``style.py``; the hand-drawn thesis images are a layout reference only.
Every figure displays the visible text "POST HOC: not pre-registered".
Non-positive or non-finite values are omitted from a panel and recorded
with ``plotted = False`` (omit-not-clamp, [D-87](4)); no clamping or
shifting is applied.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

import matplotlib.pyplot as plt
import numpy as np

try:
    from .style import (
        STRATEGY_LABELS,
        STRATEGY_MARKERS,
        STRATEGY_PALETTE,
        apply_thesis_style,
        export_figure,
    )
    from .posthoc import (
        CORPUS_M,
        CORPUS_ORDER,
        CORPUS_SHORT,
        POSTHOC_LABEL,
        SCENARIOS,
        STATUS,
        STRATEGY_CODE,
        STRATEGY_ORDER,
    )
except ImportError:  # pragma: no cover - direct script execution
    from style import (
        STRATEGY_LABELS,
        STRATEGY_MARKERS,
        STRATEGY_PALETTE,
        apply_thesis_style,
        export_figure,
    )
    from posthoc import (
        CORPUS_M,
        CORPUS_ORDER,
        CORPUS_SHORT,
        POSTHOC_LABEL,
        SCENARIOS,
        STATUS,
        STRATEGY_CODE,
        STRATEGY_ORDER,
    )


def _corner_label(ax: plt.Axes) -> None:
    ax.text(
        0.98,
        0.03,
        POSTHOC_LABEL,
        transform=ax.transAxes,
        fontsize=7,
        ha="right",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor="gray"),
    )


def plot_f7_gates(inputs: Dict[str, Any], gates: Dict[str, Any], output_dir: Path) -> None:
    """Figure F7: gates G1 and G2 applied to the primary configurations."""
    apply_thesis_style()
    fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(6.5, 7.6))
    csv_rows: List[Dict[str, Any]] = []
    omitted: List[str] = []

    # Panel A: G1 shortlist recall for S3 and S4, with pre-registered baseline.
    g1_strategies = ["ann_retrieval", "bounded_bucket"]
    x = np.arange(len(CORPUS_ORDER) * len(g1_strategies), dtype=float)
    width = 0.55
    idx = 0
    ticklabels: List[str] = []
    for corpus in CORPUS_ORDER:
        for strat in g1_strategies:
            info = gates[strat]["g1"]["per_corpus"][corpus]
            value = float(info["shortlist_recall"])
            baseline = float(info["baseline"])
            color = STRATEGY_PALETTE[strat]
            if np.isfinite(value) and value > 0:
                ax_a.bar(x[idx], value, width, color=color)
                ax_a.text(x[idx], value + 0.012, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
            else:
                omitted.append(f"{STRATEGY_CODE[strat]} {CORPUS_SHORT[corpus]}")
            ax_a.hlines(
                baseline,
                x[idx] - width / 2,
                x[idx] + width / 2,
                colors="black",
                linestyles="--",
                linewidth=1.4,
            )
            ax_a.text(
                x[idx] + width / 2 + 0.02,
                baseline,
                f"{baseline:.3f}",
                va="center",
                fontsize=7,
            )
            ticklabels.append(f"{STRATEGY_CODE[strat]}\n{CORPUS_SHORT[corpus]}")
            csv_rows.append({
                "status": STATUS,
                "panel": "G1",
                "corpus": corpus,
                "strategy": strat,
                "code": STRATEGY_CODE[strat],
                "shortlist_recall": value,
                "random_baseline_recall": baseline,
                "plotted": bool(np.isfinite(value) and value > 0),
            })
            idx += 1

    ax_a.set_xticks(x)
    ax_a.set_xticklabels(ticklabels)
    ax_a.set_ylabel("Shortlist recall")
    ax_a.set_ylim(0, max(0.8, ax_a.get_ylim()[1]))
    ax_a.set_title(
        "Panel A — G1: shortlist recall vs pre-registered random baseline\n"
        "S1: whole-graph shortlist (no baseline); S2: no shortlist cap (not assessable)"
    )
    _corner_label(ax_a)

    # Panel B: G2 mean calls at n = 2000 on a log x-axis.
    ys = np.arange(len(STRATEGY_ORDER))
    for y, strat in zip(ys, STRATEGY_ORDER):
        calls = float(inputs["sweep"][strat]["llm_calls_mean"])
        color = STRATEGY_PALETTE[strat]
        if np.isfinite(calls) and calls > 0:
            ax_b.scatter(calls, y, color=color, marker=STRATEGY_MARKERS[strat], s=110, zorder=4)
            if strat == "brute_force":
                ax_b.scatter(calls, y, s=320, facecolors="none", edgecolors="#BB2222", linewidths=1.8, zorder=3)
            ax_b.annotate(
                f" {calls:g}",
                (calls, y),
                xytext=(8, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )
            plotted = True
        else:
            omitted.append(f"{STRATEGY_CODE[strat]} G2")
            plotted = False
        ax_b.axvline(50.0, color="black", linestyle="--", linewidth=1.4)
        ax_b.text(50.0, len(STRATEGY_ORDER) - 0.35, " limit: 50", fontsize=8, va="bottom")
        csv_rows.append({
            "status": STATUS,
            "panel": "G2",
            "corpus": "",
            "strategy": strat,
            "code": STRATEGY_CODE[strat],
            "shortlist_recall": float("nan"),
            "random_baseline_recall": float("nan"),
            "calls_n2000": calls,
            "limit": 50.0,
            "gate_status": gates[strat]["g2"]["status"],
            "plotted": plotted,
        })

    ax_b.set_xscale("log")
    ax_b.set_yticks(ys)
    ax_b.set_yticklabels(
        [f"{STRATEGY_CODE[s]} ({gates[s]['g2']['status']})" for s in STRATEGY_ORDER]
    )
    ax_b.set_ylim(-0.7, len(STRATEGY_ORDER) - 0.1)
    ax_b.set_xlabel("Mean LLM calls per insertion at n = 2000 (log scale)")
    ax_b.set_title("Panel B — G2: mean calls per insertion at n = 2000 against the 50-call limit")
    _corner_label(ax_b)

    if omitted:
        fig.text(0.01, 0.005, "not plotted: " + "; ".join(omitted), fontsize=7, style="italic")

    fig.suptitle("Gates G1 and G2 applied to the primary configurations\n" + POSTHOC_LABEL)
    fig.tight_layout(rect=(0, 0.01, 1, 0.96))
    export_figure(fig, output_dir / "F7_gates_g1_g2", csv_rows)
    plt.close(fig)


def plot_f8_score_vs_weight(store: Dict[str, Any], output_dir: Path) -> None:
    """Figure F8: normalised score against the weight on accuracy, by corpus."""
    apply_thesis_style()
    fig, axes = plt.subplots(1, len(CORPUS_ORDER), figsize=(10.5, 4.8), squeeze=False)
    csv_rows: List[Dict[str, Any]] = []
    omitted: List[str] = []

    for c_idx, corpus in enumerate(CORPUS_ORDER):
        ax = axes[0][c_idx]
        ac = store[corpus]
        for w in (0.3, 0.5, 0.7):
            ax.axvline(w, color="gray", alpha=0.3, linewidth=1.0, zorder=1)
        for strat in STRATEGY_ORDER:
            a_val = float(ac["A"][strat])
            c_val = float(ac["C"][strat])
            if not (np.isfinite(a_val) and np.isfinite(c_val)):
                omitted.append(f"{STRATEGY_CODE[strat]} {CORPUS_SHORT[corpus]}")
                continue
            emphasised = strat == "ann_retrieval"
            ax.plot(
                [0.0, 1.0],
                [c_val, a_val],
                color=STRATEGY_PALETTE[strat],
                marker=STRATEGY_MARKERS[strat],
                markersize=5,
                linewidth=3.0 if emphasised else 1.6,
                alpha=1.0 if emphasised else 0.85,
                zorder=4 if emphasised else 3,
                label=STRATEGY_CODE[strat],
            )
            ax.annotate(
                f" {STRATEGY_CODE[strat]}",
                (1.0, a_val),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                fontsize=9,
                fontweight="bold" if emphasised else "normal",
            )
            ax.annotate(
                f" {STRATEGY_CODE[strat]}",
                (0.0, c_val),
                xytext=(-18, 0),
                textcoords="offset points",
                va="center",
                fontsize=9,
                fontweight="bold" if emphasised else "normal",
            )
            for w in (0.3, 0.5, 0.7):
                score = w * a_val + (1.0 - w) * c_val
                csv_rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "accuracy_weight": w,
                    "cost_weight": 1.0 - w,
                    "A_i": a_val,
                    "C_i": c_val,
                    "score": score,
                })

        ax.set_xlim(-0.05, 1.12)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Weight on accuracy, w")
        ax.set_ylabel("Normalised score S(w)")
        ax.set_title(f"{CORPUS_SHORT[corpus]} (m = {CORPUS_M[corpus]})")
        ax.legend(loc="lower right", fontsize=8, frameon=True)
        _corner_label(ax)

    if omitted:
        fig.text(0.01, 0.005, "not plotted: " + "; ".join(omitted), fontsize=7, style="italic")
    fig.suptitle("Normalised score against the weight on accuracy, by corpus\n" + POSTHOC_LABEL)
    fig.tight_layout(rect=(0, 0.01, 1, 0.94))
    export_figure(fig, output_dir / "F8_score_vs_weight", csv_rows)
    plt.close(fig)


def plot_f9_rank_shares(mc_store: Dict[str, Any], output_dir: Path) -> None:
    """Figure F9: share of weightings giving each rank, by strategy and corpus."""
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    csv_rows: List[Dict[str, Any]] = []
    # Rank 1 darkest to rank 4 lightest (single-hue ramp).
    rank_colors = {1: "#1B3A5C", 2: "#4A7BA7", 3: "#8FB4D1", 4: "#CFDEEC"}

    y_positions: List[float] = []
    y_labels: List[str] = []
    y = 0.0
    for corpus in CORPUS_ORDER:
        # Highest-ranked strategy on top within each corpus group.
        y += 0.4
        for strat in STRATEGY_ORDER:
            shares = mc_store[corpus]["shares"][strat]
            left = 0.0
            for rank in range(1, 5):
                share = float(shares[rank])
                ax.barh(
                    y,
                    share,
                    left=left,
                    color=rank_colors[rank],
                    edgecolor="white",
                    linewidth=0.6,
                    height=0.72,
                )
                if share >= 0.08:
                    ax.text(
                        left + share / 2.0,
                        y,
                        f"{share:.2f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if rank <= 2 else "#222222",
                    )
                csv_rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "rank": rank,
                    "share_mc": share,
                    "labelled": share >= 0.08,
                })
                left += share
            y_positions.append(y)
            y_labels.append(f"{STRATEGY_CODE[strat]} — {CORPUS_SHORT[corpus]}")
            y += 1.0
        y += 0.5

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("Share of 20,000 weight draws (accuracy weight uniform on 0 to 1)")
    ax.set_title(
        "Share of weightings giving each rank, by strategy and corpus\n" + POSTHOC_LABEL
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=rank_colors[r], label=f"Rank {r}")
        for r in range(1, 5)
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=4, fontsize=8)
    _corner_label(ax)
    fig.tight_layout()
    export_figure(fig, output_dir / "F9_rank_shares", csv_rows)
    plt.close(fig)
