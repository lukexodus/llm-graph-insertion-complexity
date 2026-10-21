#!/usr/bin/env python3
"""Presentation-only redraw of F4, F6, F6b from their pipeline CSVs.
Reads only figures/F4_*.csv, F6_cost_*.csv, F6_dominance.csv, F6b_*.csv. No data is recomputed or changed."""
import sys, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

src = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.linestyle": ":", "grid.alpha": 0.5})
S = {  # strategy -> code, long name, color, marker
 "brute_force":        ("S1", "Strategy 1: Brute Force",                 "#4477AA", "o"),
 "embedding_threshold":("S2", "Strategy 2: Embedding Threshold",         "#66CCEE", "s"),
 "ann_retrieval":      ("S3", "Strategy 3: ANN Retrieval (HNSW)",        "#228833", "^"),
 "bounded_bucket":     ("S4", "Strategy 4: Bounded Bucket (SimHash)",    "#CCBB44", "D"),
}
SHORT = {"S1": "S1 Brute Force", "S2": "S2 Emb. Threshold", "S3": "S3 ANN (HNSW)", "S4": "S4 Bounded Bucket"}
CORP = [("DSA_gold_standard_MEKG", "DSA (29 Nodes)"), ("metacademy_gold_standard_MEKG", "Metacademy (141 Nodes)")]

FAILS = []
def _bb(a): return a.get_window_extent()
def _hit(a, b, pad=2):
    return not (a.x1 + pad < b.x0 or b.x1 + pad < a.x0 or a.y1 + pad < b.y0 or b.y1 + pad < a.y0)
def check_overlaps(fig, name):
    """Mechanical layout check: legend, text boxes, labels, markers, bars must not overlap each other."""
    from matplotlib.patches import Rectangle
    fig.canvas.draw()
    for k, ax in enumerate(fig.axes):
        items = []  # (label, bbox)
        leg = ax.get_legend()
        if leg is not None: items.append(("legend", _bb(leg)))
        for t in ax.texts: items.append((("text:" + t.get_text()[:24].replace("\n", " ")), _bb(t.get_bbox_patch() or t)))
        for coll in ax.collections:
            for off in coll.get_offsets():
                x, y = ax.transData.transform(off); r = 9
                from matplotlib.transforms import Bbox
                items.append(("marker", Bbox([[x - r, y - r], [x + r, y + r]])))
        for p in ax.patches:
            if isinstance(p, Rectangle) and p.get_height() > 0 and p.get_width() > 0 and p is not ax.patch:
                items.append(("bar", _bb(p)))
        for line in ax.lines:
            if line.get_marker() == "*":
                for x, y in zip(*line.get_data()):
                    px, py = ax.transData.transform((x, y)); from matplotlib.transforms import Bbox
                    items.append(("star", Bbox([[px - 8, py - 8], [px + 8, py + 8]])))
        non_text_pairs_ok = {("bar", "bar"), ("bar", "star"), ("star", "bar")}
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (la, a), (lb, b) = items[i], items[j]
                kind = (la.split(":")[0], lb.split(":")[0])
                if kind in non_text_pairs_ok: continue
                if kind == ("marker", "marker"): continue
                if _hit(a, b, pad=0): FAILS.append(f"{name} panel {k}: '{la}' overlaps '{lb}'")
        # everything must lie inside the figure canvas
        fb = fig.bbox
        for lab, b in items:
            if b.x0 < fb.x0 - 1 or b.x1 > fb.x1 + 1 or b.y0 < fb.y0 - 1 or b.y1 > fb.y1 + 1:
                FAILS.append(f"{name} panel {k}: '{lab}' outside figure")

def save(fig, name):
    check_overlaps(fig, name)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{name}_redraw.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)

# ---------------- F4 ----------------
def f4():
    d = pd.read_csv(src / "F4_accuracy_by_strategy.csv")
    order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
    cols = [("precision_micro", "Micro Precision", "#4477AA"), ("recall_micro", "Micro Recall", "#66CCEE"),
            ("f1_micro", "Micro F1", "#228833"), ("shortlist_recall_micro", "Shortlist Recall", "#CCBB44")]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))
    w = 0.18
    for ax, (c, t) in zip(axes, CORP):
        g = d[d.corpus == c].set_index("strategy").loc[order]
        for j, (col, lab, colr) in enumerate(cols):
            ax.bar([i + (j - 1.5) * w for i in range(4)], g[col], w, label=lab, color=colr)
        for i, s in enumerate(order):
            b = g.loc[s, "random_baseline_recall"]
            if pd.notna(b): ax.plot(i + 1.5 * w, b, "*", color="red", ms=11, zorder=5)
        ax.set_xticks(range(4)); ax.set_xticklabels([S[s][1].replace(": ", "\n", 1) for s in order], fontsize=8.5)
        ax.set_title(f"Accuracy: {t}"); ax.set_ylabel("Metric Value"); ax.set_ylim(0, 1.05); ax.set_axisbelow(True)
        h = ax.get_legend_handles_labels()
        ax.legend(h[0] + [Line2D([], [], marker="*", color="red", ls="", ms=11)], h[1] + ["Random Baseline SR"],
                  loc="upper right", fontsize=8.5, framealpha=0.95)
    fig.tight_layout(); save(fig, "F4_accuracy_by_strategy")

# ---------------- F6 / F6b ----------------
# label anchor positions (data coords) per corpus; leader lines drawn from label to point
POS_F6 = {  # linear x
 "DSA_gold_standard_MEKG": {"S1": (23, .66), "S2": (5.5, .07), "S3": (12, .60), "S4": (9, .37)},
 "metacademy_gold_standard_MEKG": {"S1": (112, .24), "S2": (24, .42), "S3": (30, .34), "S4": (27, .05)},
}
POS_F6B = {  # log x (multiplicative offsets)
 "DSA_gold_standard_MEKG": {"S1": (30, .70), "S2": (0.9, .30), "S3": (10, .68), "S4": (5.5, .38)},
 "metacademy_gold_standard_MEKG": {"S1": (45, .30), "S2": (2.3, .44), "S3": (11, .42), "S4": (3.6, .20)},
}
def dom_text(dom, corpus):
    g = dom[dom.corpus == corpus]; lines = []
    for _, r in g.iterrows():
        a, b = S[r.strategy_a][0], S[r.strategy_b][0]
        res = r.dominance
        if res == "A dominates B": res = f"{a} dominates {b}"
        elif res == "B dominates A": res = f"{b} dominates {a}"
        elif res.startswith("not distinguishable"): res = "not distinguishable (F1 within 0.025)"
        lines.append(f"{a} vs {b}: {res}")
    return "\n".join(lines)

def scatter(csv, name, logx, pos, title_extra="", dom_csv="F6_dominance.csv", legend_inside=False):
    d = pd.read_csv(src / csv); dom = pd.read_csv(src / dom_csv)
    if "plotted" in d: d = d[d.plotted.astype(str) == "True"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
    for ax, (c, t) in zip(axes, CORP):
        g = d[d.corpus == c]
        for _, r in g.iterrows():
            code, long, colr, mk = S[r.strategy]
            ax.scatter(r.calls, r.f1, s=110, color=colr, marker=mk, zorder=4, label=long)
            x, y = pos[c][code]
            ax.annotate(f"{code} {r.strategy}\n({r.calls:.1f}, {r.f1:.3f})", (r.calls, r.f1), (x, y), fontsize=8.5,
                        ha="center", va="center", zorder=6,
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.6", lw=0.6),
                        arrowprops=dict(arrowstyle="-", color="0.45", lw=0.8, shrinkA=0, shrinkB=6))
        if logx: ax.set_xscale("log")
        ax.set_ylim(0, 1.05); ax.set_title(f"Cost vs. Accuracy{' (Log-X)' if logx else ''}: {t}" + title_extra)
        ax.set_xlabel("Mean LLM Calls per Insertion" + (" (log scale)" if logx else "")); ax.set_ylabel("Micro F1 Score")
        if not logx: ax.set_xlim(left=-2 if c.startswith("DSA") else -6)
        ax.text(0.02, 0.98, dom_text(dom, c), transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="0.5", alpha=0.95))
    handles = [Line2D([], [], marker=S[s][3], color=S[s][2], ls="", ms=9, label=S[s][1]) for s in S]
    if legend_inside:  # F6b: top-right inside, short labels
        for ax in axes:
            ax.legend([Line2D([], [], marker=S[s][3], color=S[s][2], ls="", ms=9) for s in S],
                      [SHORT[S[s][0]] for s in S], loc="upper right", fontsize=8.5, framealpha=0.95)
        fig.tight_layout()
    else:  # F6: shared legend below both panels, outside the axes
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9, frameon=True)
    save(fig, name)

f4()
scatter("F6_cost_vs_accuracy_dominance.csv", "F6_cost_vs_accuracy_dominance", False, POS_F6)
scatter("F6b_cost_vs_accuracy_logx.csv", "F6b_cost_vs_accuracy_logx", True, POS_F6B,
        title_extra="\nEXPLORATORY: log scale, not pre-registered", legend_inside=True)
print("done", sorted(p.name for p in out.iterdir()))
print("LAYOUT CHECK:", "FAIL" if FAILS else "PASS")
for f in FAILS: print("  ", f)
sys.exit(1 if FAILS else 0)
