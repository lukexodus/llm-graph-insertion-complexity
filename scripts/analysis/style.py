"""
style.py — Unified Styling and Export Module for Phase 4 Figures
================================================================
Implements styling specifications from Section 5 of the Analysis Plan.
- Fixed palette across all strategies.
- Typography and formatting for publication / thesis figures.
- Dual export: vector PDF + underlying data CSV for every figure.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib.pyplot as plt

# Strategy color palette (colorblind-friendly, publication standard)
STRATEGY_PALETTE = {
    "brute_force": "#4477AA",          # Blue
    "embedding_threshold": "#66CCEE",  # Cyan
    "ann_retrieval": "#228833",        # Green
    "bounded_bucket": "#CCBB44",       # Yellow / Olive
    "null": "#BBBBBB",                 # Grey
}

STRATEGY_LABELS = {
    "brute_force": "Strategy 1: Brute Force",
    "embedding_threshold": "Strategy 2: Embedding Threshold",
    "ann_retrieval": "Strategy 3: ANN Retrieval (HNSW)",
    "bounded_bucket": "Strategy 4: Bounded Bucket (SimHash)",
    "null": "Baseline: Null Strategy",
}

STRATEGY_MARKERS = {
    "brute_force": "o",
    "embedding_threshold": "s",
    "ann_retrieval": "^",
    "bounded_bucket": "D",
    "null": "x",
}


def apply_thesis_style() -> None:
    """Configure matplotlib rcParams for clear vector figures."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
        "lines.linewidth": 1.75,
        "lines.markersize": 6,
        "axes.grid": True,
        "grid.alpha": 0.4,
        "grid.linestyle": ":",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def export_figure(
    fig: plt.Figure,
    base_path: Path,
    csv_rows: Optional[List[Dict[str, Any]]] = None,
    csv_fieldnames: Optional[List[str]] = None,
    dpi: int = 300,
) -> None:
    """Export figure as vector PDF (and PNG for quick preview)

    and simultaneously save the underlying data as CSV per Section 5.
    """
    base_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = base_path.with_suffix(".pdf")
    png_path = base_path.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight", format="pdf")
    fig.savefig(png_path, bbox_inches="tight", dpi=dpi, format="png")

    if csv_rows is not None and len(csv_rows) > 0:
        csv_path = base_path.with_suffix(".csv")
        if csv_fieldnames:
            fields = csv_fieldnames
        else:
            # Deterministic union of all keys across all dicts preserving insertion order
            seen_keys: Dict[str, None] = {}
            for r in csv_rows:
                for k in r.keys():
                    seen_keys[k] = None
            fields = list(seen_keys.keys())

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(csv_rows)
