# FIG-001 — Legibility redraw of F4, F6, F6b (presentation only)

**Agent:** claude-code
**Session ID:** `264a6376-5f01-4953-b9e0-15c20524cfff`
**Model label reported by the harness:** `deepseek-flash[1m]`
**Task:** FIG-001 (prompt archived at `docs/prompts/FIG-001-prompt.md`)
**Worktree:** `/home/lukexodus/projects/llm-graph-insertion-complexity-FIG-001`
**Branch:** `task/FIG-001` (base `b0f17db`)

---

## Executive Summary

Redrew F4, F6, and F6b from the existing CSVs in
`~/projects/thesis-analysis/final_output_final/figures` into
`~/projects/thesis-analysis/final_output_redraw`. No values were recomputed
or changed.

The supplied script's first run failed its own mechanical layout check:

```
LAYOUT CHECK: FAIL
   F6_cost_vs_accuracy_dominance panel 0: 'text:S4 bounded_bucket (7.0, ' overlaps 'marker'
EXIT CODE: 1
```

The visual gap was about one pixel: the F6 DSA S4 label box bottom nearly
touched the top of the S4 diamond (7.0, 0.271). One data-coordinate value was
changed, `POS_F6["DSA_gold_standard_MEKG"]["S4"]` from `(9, .33)` to
`(9, .37)`; nothing else in the script was edited. The rerun passed:

```
LAYOUT CHECK: PASS
EXIT CODE: 0
```

An independent data-integrity script instrumented every matplotlib plotting
call and compared 124 values against the source CSVs: **PASS, 0 mismatches**.
Image inspection found no legend, label, or box covering a point or bar in any
of the three figures.

---

## Preconditions checked

```
$ git worktree list
/home/lukexodus/projects/llm-graph-insertion-complexity                b0f17db [master]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-001-G 48037e3 [task/ANALYSIS-001-G]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-002   17ed1f8 [task/ANALYSIS-002]
/home/lukexodus/projects/llm-graph-insertion-complexity-ANALYSIS-003   5ab04a6 [task/ANALYSIS-003]
/home/lukexodus/projects/llm-graph-insertion-complexity-DOC-007        0b132f7 [task/DOC-007]

$ grep -n "FIG-001" docs/tasks/status.md
NO FIG-001 in status.md
```

Session ID `264a6376-5f01-4953-b9e0-15c20524cfff` is not in the excluded-session
list and matches no excluded prefix. Worktree created with:

```
$ ./scripts/task-worktree.sh start FIG-001
Creating dedicated worktree for task FIG-001...
Preparing worktree (new branch 'task/FIG-001')
HEAD is now at b0f17db Merge branch 'task/DOC-012'
Worktree successfully created at: ../llm-graph-insertion-complexity-FIG-001
Branch: task/FIG-001
```

## Implementation Details

### Script copy and hash

| Stage | sha256 |
| --- | --- |
| Source `redraw_thesis_figures.py` in repo root | `6f44a7202e511842d98747049b787fda132d7026f47cd9679ee35c0eb1fc6166` |
| After copy to `scripts/analysis/redraw_thesis_figures.py` | `6f44a7202e511842d98747049b787fda132d7026f47cd9679ee35c0eb1fc6166` |
| After the one-coordinate layout fix (committed version) | `a33fb2165712199571524bc7133d284acd3474b672a8b318eea44950b702dbb7` |

The source hash matches the APC-supplied hash exactly. The post-copy hash also
matched before the layout fix; the only difference in the committed script is:

```diff
- "DSA_gold_standard_MEKG": {"S1": (23, .66), "S2": (5.5, .07), "S3": (12, .60), "S4": (9, .33)},
+ "DSA_gold_standard_MEKG": {"S1": (23, .66), "S2": (5.5, .07), "S3": (12, .60), "S4": (9, .37)},
```

Reason: the first run's mechanical layout check reported the S4 text box
overlapping a marker in F6 panel 0. The change moves only the label anchor in
data coordinates; it does not touch any data value, axis, legend, or text
content.

Environment used: `python` 3.x with pandas 2.3.3 and matplotlib 3.11.2, Agg
backend. No API calls, network access, or model downloads were made.

### Commands run

```
$ cp redraw_thesis_figures.py \
    /home/lukexodus/projects/llm-graph-insertion-complexity-FIG-001/scripts/analysis/redraw_thesis_figures.py
$ sha256sum scripts/analysis/redraw_thesis_figures.py
6f44a7202e511842d98747049b787fda132d7026f47cd9679ee35c0eb1fc6166  scripts/analysis/redraw_thesis_figures.py

$ python scripts/analysis/redraw_thesis_figures.py \
    ~/projects/thesis-analysis/final_output_final/figures \
    ~/projects/thesis-analysis/final_output_redraw
done ['F4_accuracy_by_strategy_redraw.pdf', 'F4_accuracy_by_strategy_redraw.png',
      'F6_cost_vs_accuracy_dominance_redraw.pdf', 'F6_cost_vs_accuracy_dominance_redraw.png',
      'F6b_cost_vs_accuracy_logx_redraw.pdf', 'F6b_cost_vs_accuracy_logx_redraw.png']
LAYOUT CHECK: FAIL
   F6_cost_vs_accuracy_dominance panel 0: 'text:S4 bounded_bucket (7.0, ' overlaps 'marker'
EXIT CODE: 1
```

After the one-line label-position change:

```
$ sha256sum scripts/analysis/redraw_thesis_figures.py
a33fb2165712199571524bc7133d284acd3474b672a8b318eea44950b702dbb7  scripts/analysis/redraw_thesis_figures.py

$ python scripts/analysis/redraw_thesis_figures.py \
    ~/projects/thesis-analysis/final_output_final/figures \
    ~/projects/thesis-analysis/final_output_redraw
done ['F4_accuracy_by_strategy_redraw.pdf', 'F4_accuracy_by_strategy_redraw.png',
      'F6_cost_vs_accuracy_dominance_redraw.pdf', 'F6_cost_vs_accuracy_dominance_redraw.png',
      'F6b_cost_vs_accuracy_logx_redraw.pdf', 'F6b_cost_vs_accuracy_logx_redraw.png']
LAYOUT CHECK: PASS
EXIT CODE: 0
```

Output directory `final_output_redraw` was newly created. The source directory
`final_output_final` was read-only from this task's perspective; its CSVs were
not modified.

## Verification & Test Evidence

### Data-integrity check

The check script (`/tmp/fig001_integrity.py`, reproduced in Appendix A) runs the
redraw script in-process with `matplotlib.axes.Axes.bar`, `.scatter`, `.plot`,
`.annotate`, and `.text` instrumented. It writes figures to a temporary
directory, then compares every value passed to those calls against the source
CSVs, independently rebuilding the expected annotation and dominance strings.

Final output:

```
$ python -I /tmp/fig001_integrity.py \
    ~/projects/thesis-analysis/final_output_final/figures \
    /home/lukexodus/projects/llm-graph-insertion-complexity-FIG-001/scripts/analysis/redraw_thesis_figures.py
done ['F4_accuracy_by_strategy_redraw.pdf', 'F4_accuracy_by_strategy_redraw.png',
      'F6_cost_vs_accuracy_dominance_redraw.pdf', 'F6_cost_vs_accuracy_dominance_redraw.png',
      'F6b_cost_vs_accuracy_logx_redraw.pdf', 'F6b_cost_vs_accuracy_logx_redraw.png']
LAYOUT CHECK: PASS
F4: 32 bar values (8 bar calls x 4 strategies) + 4 non-NaN random-baseline markers compared
F6: 8 points x (calls, f1) + 8 annotations compared
F6b: 8 points x (calls, f1) + 8 annotations compared
F6/F6b dominance: 24 text-line comparisons (12 lines x 2 figures)
TOTAL numeric values compared: 124
MISMATCH COUNT: 0
DATA INTEGRITY: PASS
EXIT CODE: 0
```

Counts:

| Figure | Values compared |
| --- | --- |
| F4 | 32 bar heights (`precision_micro`, `recall_micro`, `f1_micro`, `shortlist_recall_micro` × 4 strategies × 2 corpora) + 4 non-NaN `random_baseline_recall` stars (2 DSA, 2 Metacademy; the other four rows are NaN and are not plotted) |
| F6 | 8 points × (`calls`, `f1`) + 8 annotation strings |
| F6b | 8 points × (`calls`, `f1`) + 8 annotation strings |
| F6/F6b dominance boxes | 12 lines per figure, 24 comparisons total, equal to `F6_dominance.csv` after the S1–S4 code substitution |

Source CSV hashes (unchanged inputs):

```
ff687458a8dffab144ccb04a27b07f71da92071d673f864e3397dce441061caa  F4_accuracy_by_strategy.csv
9049a11b51a2104622af5f9ff6a18fe1fd2261400db33f249bb4f7c9a653e52e  F6_cost_vs_accuracy_dominance.csv
19d4c342341a60e52ac619e094b274face9d3cb2b1612f9954cb022f6b1d4ac0  F6b_cost_vs_accuracy_logx.csv
3cfac5ad0452c0c3771da0cdab7a99415a71f80e8c53fc6116e3801e40568047  F6_dominance.csv
```

### Image inspection

Rendered PNGs were viewed directly.

- **F4** `F4_accuracy_by_strategy_redraw.png`: no legend, label, star, or box covers a bar or marker in either panel; legend sits top-right and clears the tallest DSA shortlist bar.
- **F6** `F6_cost_vs_accuracy_dominance_redraw.png`: all eight point labels are separated from each other and from markers; leader lines connect each label to its point; the shared legend is below both axes and covers nothing; both dominance boxes sit in empty upper-left space.
- **F6b** `F6b_cost_vs_accuracy_logx_redraw.png`: short-label legends are top-right in both panels and cover no point; dominance boxes top-left and point labels do not overlap; no label clipped.

### Output file hashes

```
97c3dcb1957e46e2836257788643e987fc315e29fe638c9c7d5c828b3f2d937e  F4_accuracy_by_strategy_redraw.png
d73fc32f6a89939527c46974b2d40eee7873d0f83c02a2807ab0922e1d00e8b1  F4_accuracy_by_strategy_redraw.pdf
17ce4512ff151a42c23768381d20339542935760faccaf1a67625a6269fa3cea  F6_cost_vs_accuracy_dominance_redraw.png
8573cf0e47a842f880797e0c23060c16489130510a4166363467e6544e944a47  F6_cost_vs_accuracy_dominance_redraw.pdf
7698bada780b926923549388c836a247d0724c62220007dd9bded809c935b6fb  F6b_cost_vs_accuracy_logx_redraw.png
5987f17fb04b6dad66fcb958ce2bbc5af6ed45f63e242f301eefdf863740a830  F6b_cost_vs_accuracy_logx_redraw.pdf
```

### Report validation

```
$ ./scripts/validate-report.py docs/reports/FIG-001-claude-code-redraw-legibility.md --require-patch
Validating report: FIG-001-claude-code-redraw-legibility.md ...
  FAILED with 1 issue(s):
    - Task ID 'FIG-001' (or base 'FIG-001') was not found in 'docs/tasks/status.md'.
VALIDATOR EXIT: 1
```

The only failure is status alignment, because the FIG-001 prompt forbids editing
`docs/tasks/status.md`; the APC is to request that row separately. The report is
therefore unlinked from `status.md` by design, not by omission. The patch-file
check passes. The patch file is written to `patch/` but not committed, per the
prompt's "commit only the new script and the report".

## Git Diff

Verbatim `git diff` for the new script (the report file itself is new; a diff
of a file cannot include its own content):

```diff
diff --git i/scripts/analysis/redraw_thesis_figures.py w/scripts/analysis/redraw_thesis_figures.py
new file mode 100644
index 0000000..63f883f
--- /dev/null
+++ w/scripts/analysis/redraw_thesis_figures.py
@@ -0,0 +1,149 @@
+#!/usr/bin/env python3
+"""Presentation-only redraw of F4, F6, F6b from their pipeline CSVs.
+Reads only figures/F4_*.csv, F6_cost_*.csv, F6_dominance.csv, F6b_*.csv. No data is recomputed or changed."""
+import sys, pandas as pd, matplotlib
+matplotlib.use("Agg")
+import matplotlib.pyplot as plt
+from matplotlib.lines import Line2D
+from pathlib import Path
+
+src = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
+plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.spines.top": False,
+                     "axes.spines.right": False, "axes.grid": True, "grid.linestyle": ":", "grid.alpha": 0.5})
+S = {  # strategy -> code, long name, color, marker
+ "brute_force":        ("S1", "Strategy 1: Brute Force",                 "#4477AA", "o"),
+ "embedding_threshold":("S2", "Strategy 2: Embedding Threshold",         "#66CCEE", "s"),
+ "ann_retrieval":      ("S3", "Strategy 3: ANN Retrieval (HNSW)",        "#228833", "^"),
+ "bounded_bucket":     ("S4", "Strategy 4: Bounded Bucket (SimHash)",    "#CCBB44", "D"),
+}
+SHORT = {"S1": "S1 Brute Force", "S2": "S2 Emb. Threshold", "S3": "S3 ANN (HNSW)", "S4": "S4 Bounded Bucket"}
+CORP = [("DSA_gold_standard_MEKG", "DSA (29 Nodes)"), ("metacademy_gold_standard_MEKG", "Metacademy (141 Nodes)")]
+
+FAILS = []
+def _bb(a): return a.get_window_extent()
+def _hit(a, b, pad=2):
+    return not (a.x1 + pad < b.x0 or b.x1 + pad < a.x0 or a.y1 + pad < b.y0 or b.y1 + pad < a.y0)
+def check_overlaps(fig, name):
+    """Mechanical layout check: legend, text boxes, labels, markers, bars must not overlap each other."""
+    from matplotlib.patches import Rectangle
+    fig.canvas.draw()
+    for k, ax in enumerate(fig.axes):
+        items = []  # (label, bbox)
+        leg = ax.get_legend()
+        if leg is not None: items.append(("legend", _bb(leg)))
+        for t in ax.texts: items.append((("text:" + t.get_text()[:24].replace("\n", " ")), _bb(t.get_bbox_patch() or t)))
+        for coll in ax.collections:
+            for off in coll.get_offsets():
+                x, y = ax.transData.transform(off); r = 9
+                from matplotlib.transforms import Bbox
+                items.append(("marker", Bbox([[x - r, y - r], [x + r, y + r]])))
+        for p in ax.patches:
+            if isinstance(p, Rectangle) and p.get_height() > 0 and p.get_width() > 0 and p is not ax.patch:
+                items.append(("bar", _bb(p)))
+        for line in ax.lines:
+            if line.get_marker() == "*":
+                for x, y in zip(*line.get_data()):
+                    px, py = ax.transData.transform((x, y)); from matplotlib.transforms import Bbox
+                    items.append(("star", Bbox([[px - 8, py - 8], [px + 8, py + 8]])))
+        non_text_pairs_ok = {("bar", "bar"), ("bar", "star"), ("star", "bar")}
+        for i in range(len(items)):
+            for j in range(i + 1, len(items)):
+                (la, a), (lb, b) = items[i], items[j]
+                kind = (la.split(":")[0], lb.split(":")[0])
+                if kind in non_text_pairs_ok: continue
+                if kind == ("marker", "marker"): continue
+                if _hit(a, b, pad=0): FAILS.append(f"{name} panel {k}: '{la}' overlaps '{lb}'")
+        # everything must lie inside the figure canvas
+        fb = fig.bbox
+        for lab, b in items:
+            if b.x0 < fb.x0 - 1 or b.x1 > fb.x1 + 1 or b.y0 < fb.y0 - 1 or b.y1 > fb.y1 + 1:
+                FAILS.append(f"{name} panel {k}: '{lab}' outside figure")
+
+def save(fig, name):
+    check_overlaps(fig, name)
+    for ext in ("png", "pdf"):
+        fig.savefig(out / f"{name}_redraw.{ext}", dpi=300, bbox_inches="tight")
+    plt.close(fig)
+
+# ---------------- F4 ----------------
+def f4():
+    d = pd.read_csv(src / "F4_accuracy_by_strategy.csv")
+    order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
+    cols = [("precision_micro", "Micro Precision", "#4477AA"), ("recall_micro", "Micro Recall", "#66CCEE"),
+            ("f1_micro", "Micro F1", "#228833"), ("shortlist_recall_micro", "Shortlist Recall", "#CCBB44")]
+    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))
+    w = 0.18
+    for ax, (c, t) in zip(axes, CORP):
+        g = d[d.corpus == c].set_index("strategy").loc[order]
+        for j, (col, lab, colr) in enumerate(cols):
+            ax.bar([i + (j - 1.5) * w for i in range(4)], g[col], w, label=lab, color=colr)
+        for i, s in enumerate(order):
+            b = g.loc[s, "random_baseline_recall"]
+            if pd.notna(b): ax.plot(i + 1.5 * w, b, "*", color="red", ms=11, zorder=5)
+        ax.set_xticks(range(4)); ax.set_xticklabels([S[s][1].replace(": ", "\n", 1) for s in order], fontsize=8.5)
+        ax.set_title(f"Accuracy: {t}"); ax.set_ylabel("Metric Value"); ax.set_ylim(0, 1.05); ax.set_axisbelow(True)
+        h = ax.get_legend_handles_labels()
+        ax.legend(h[0] + [Line2D([], [], marker="*", color="red", ls="", ms=11)], h[1] + ["Random Baseline SR"],
+                  loc="upper right", fontsize=8.5, framealpha=0.95)
+    fig.tight_layout(); save(fig, "F4_accuracy_by_strategy")
+
+# ---------------- F6 / F6b ----------------
+# label anchor positions (data coords) per corpus; leader lines drawn from label to point
+POS_F6 = {  # linear x
+ "DSA_gold_standard_MEKG": {"S1": (23, .66), "S2": (5.5, .07), "S3": (12, .60), "S4": (9, .37)},
+ "metacademy_gold_standard_MEKG": {"S1": (112, .24), "S2": (24, .42), "S3": (30, .34), "S4": (27, .05)},
+}
+POS_F6B = {  # log x (multiplicative offsets)
+ "DSA_gold_standard_MEKG": {"S1": (30, .70), "S2": (0.9, .30), "S3": (10, .68), "S4": (5.5, .38)},
+ "metacademy_gold_standard_MEKG": {"S1": (45, .30), "S2": (2.3, .44), "S3": (11, .42), "S4": (3.6, .20)},
+}
+def dom_text(dom, corpus):
+    g = dom[dom.corpus == corpus]; lines = []
+    for _, r in g.iterrows():
+        a, b = S[r.strategy_a][0], S[r.strategy_b][0]
+        res = r.dominance
+        if res == "A dominates B": res = f"{a} dominates {b}"
+        elif res == "B dominates A": res = f"{b} dominates {a}"
+        elif res.startswith("not distinguishable"): res = "not distinguishable (F1 within 0.025)"
+        lines.append(f"{a} vs {b}: {res}")
+    return "\n".join(lines)
+
+def scatter(csv, name, logx, pos, title_extra="", dom_csv="F6_dominance.csv", legend_inside=False):
+    d = pd.read_csv(src / csv); dom = pd.read_csv(src / dom_csv)
+    if "plotted" in d: d = d[d.plotted.astype(str) == "True"]
+    fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
+    for ax, (c, t) in zip(axes, CORP):
+        g = d[d.corpus == c]
+        for _, r in g.iterrows():
+            code, long, colr, mk = S[r.strategy]
+            ax.scatter(r.calls, r.f1, s=110, color=colr, marker=mk, zorder=4, label=long)
+            x, y = pos[c][code]
+            ax.annotate(f"{code} {r.strategy}\n({r.calls:.1f}, {r.f1:.3f})", (r.calls, r.f1), (x, y), fontsize=8.5,
+                        ha="center", va="center", zorder=6,
+                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.6", lw=0.6),
+                        arrowprops=dict(arrowstyle="-", color="0.45", lw=0.8, shrinkA=0, shrinkB=6))
+        if logx: ax.set_xscale("log")
+        ax.set_ylim(0, 1.05); ax.set_title(f"Cost vs. Accuracy{' (Log-X)' if logx else ''}: {t}" + title_extra)
+        ax.set_xlabel("Mean LLM Calls per Insertion" + (" (log scale)" if logx else "")); ax.set_ylabel("Micro F1 Score")
+        if not logx: ax.set_xlim(left=-2 if c.startswith("DSA") else -6)
+        ax.text(0.02, 0.98, dom_text(dom, c), transform=ax.transAxes, va="top", fontsize=8,
+                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="0.5", alpha=0.95))
+    handles = [Line2D([], [], marker=S[s][3], color=S[s][2], ls="", ms=9, label=S[s][1]) for s in S]
+    if legend_inside:  # F6b: top-right inside, short labels
+        for ax in axes:
+            ax.legend([Line2D([], [], marker=S[s][3], color=S[s][2], ls="", ms=9) for s in S],
+                      [SHORT[S[s][0]] for s in S], loc="upper right", fontsize=8.5, framealpha=0.95)
+        fig.tight_layout()
+    else:  # F6: shared legend below both panels, outside the axes
+        fig.tight_layout(rect=(0, 0.07, 1, 1))
+        fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9, frameon=True)
+    save(fig, name)
+
+f4()
+scatter("F6_cost_vs_accuracy_dominance.csv", "F6_cost_vs_accuracy_dominance", False, POS_F6)
+scatter("F6b_cost_vs_accuracy_logx.csv", "F6b_cost_vs_accuracy_logx", True, POS_F6B,
+        title_extra="\nEXPLORATORY: log scale, not pre-registered", legend_inside=True)
+print("done", sorted(p.name for p in out.iterdir()))
+print("LAYOUT CHECK:", "FAIL" if FAILS else "PASS")
+for f in FAILS: print("  ", f)
+sys.exit(1 if FAILS else 0)
```

## Patch File

`patch/0001-feat-FIG-001-add-legibility-redraw-script-and-report.patch`

Command used after the single task commit:

```
$ git format-patch -1 -o patch/ HEAD
```

The prompt's suggested `git format-patch -2 -o patch/ master` was tried first.
In this git version it exported the last two non-merge commits of `master`
(the DOC-012 commits), not `master..HEAD`, because `<since>` is treated as a
revision whose history is walked. Those two output files were deleted and the
correct single-commit range was exported with `-1 HEAD`.

## Items Flagged for APC / Future Agent Attention

1. **Script was edited once, deliberately.** The APC-supplied script failed its
   own layout check in this environment. The smallest change was one label
   anchor coordinate, `.33` → `.37`, for F6 DSA S4. Full text of the change is
   above. If the APC wants the script byte-identical to its tested copy, the
   alternative is to accept the one-pixel bbox proximity that the check flags.
2. **`docs/tasks/status.md` was not edited** (forbidden by the FIG-001 prompt).
   As a result `validate-report.py` will report a status-alignment failure for
   this report. A status row must be added by the APC/Luke separately.
3. **No decision-log entry was made** (forbidden by the prompt).
4. **The data-integrity checker reproduces output only through matplotlib
   plotting calls**, not by re-reading pixel values from the PNG/PDF. It proves
   the values handed to the plotting API equal the CSV values; it does not
   independently verify that matplotlib rendered them at those coordinates.
   Rendered-image inspection was done visually.
5. The integrity checker lives at `/tmp/fig001_integrity.py` and is reproduced
   in Appendix A; it is not committed, per the prompt's allowed-file list.

---

## Appendix A — Data-integrity checker

```python
#!/usr/bin/env python3
"""FIG-001 data-integrity check.

Runs the redraw script in-process with matplotlib plotting calls instrumented,
then compares every value passed to bar/scatter/plot and every annotation/box
string against the source CSVs. Uses a temporary output directory so the
delivered figures are untouched.
"""
import math
import runpy
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.axes
import pandas as pd

SRC = Path(sys.argv[1])
REDRAW = Path(sys.argv[2])
records = {"bar": [], "scatter": [], "plot": [], "annotate": [], "text": []}


def ax_index(ax):
    try:
        return ax.figure.axes.index(ax)
    except ValueError:
        return -1


_orig_bar = matplotlib.axes.Axes.bar
_orig_scatter = matplotlib.axes.Axes.scatter
_orig_plot = matplotlib.axes.Axes.plot
_orig_annotate = matplotlib.axes.Axes.annotate
_orig_text = matplotlib.axes.Axes.text


def bar(self, x, height, *a, **k):
    records["bar"].append((ax_index(self), list(x), [float(v) for v in height], k.get("label")))
    return _orig_bar(self, x, height, *a, **k)


def scatter(self, x, y, *a, **k):
    rec = (ax_index(self), float(x), float(y), k.get("marker"), k.get("label"))
    records["scatter"].append(rec)
    return _orig_scatter(self, x, y, *a, **k)


def plot(self, *a, **k):
    marker = k.get("marker")
    if marker is None and len(a) > 2:
        marker = a[2]
    if marker == "*":
        records["plot"].append((ax_index(self), float(a[0]), float(a[1])))
    return _orig_plot(self, *a, **k)


def annotate(self, text, xy, xytext=None, *a, **k):
    records["annotate"].append((ax_index(self), text, (float(xy[0]), float(xy[1])),
                                None if xytext is None else (float(xytext[0]), float(xytext[1]))))
    return _orig_annotate(self, text, xy, xytext=xytext, *a, **k)


def text(self, x, y, s, *a, **k):
    records["text"].append((ax_index(self), s))
    return _orig_text(self, x, y, s, *a, **k)


matplotlib.axes.Axes.bar = bar
matplotlib.axes.Axes.scatter = scatter
matplotlib.axes.Axes.plot = plot
matplotlib.axes.Axes.annotate = annotate
matplotlib.axes.Axes.text = text

tmpout = Path(tempfile.mkdtemp(prefix="fig001-integrity-"))
sys.argv = [str(REDRAW), str(SRC), str(tmpout)]
try:
    runpy.run_path(str(REDRAW), run_name="__main__")
except SystemExit as e:
    if e.code not in (0, None):
        print("redraw script exited nonzero during integrity run:", e.code)
        raise

OK = True
compared = 0
mismatch = 0


def check(cond, msg):
    global OK, mismatch
    if not cond:
        OK = False
        mismatch += 1
        print("MISMATCH:", msg)


# ---------- F4: bars + random-baseline stars ----------
d4 = pd.read_csv(SRC / "F4_accuracy_by_strategy.csv")
order = ["brute_force", "embedding_threshold", "ann_retrieval", "bounded_bucket"]
metrics = ["precision_micro", "recall_micro", "f1_micro", "shortlist_recall_micro"]
bar_recs = [r for r in records["bar"] if r[2]]
check(len(bar_recs) == 8, f"F4 expected 8 bar calls (4 metrics x 2 panels), saw {len(bar_recs)}")
for k in range(8):
    panel, xs, hs, label = bar_recs[k]
    corpus = "DSA_gold_standard_MEKG" if k < 4 else "metacademy_gold_standard_MEKG"
    g = d4[d4.corpus == corpus].set_index("strategy").loc[order]
    metric = metrics[k % 4]
    check(panel == (0 if corpus.startswith("DSA") else 1), f"F4 bar k={k} wrong panel")
    check(len(hs) == 4, f"F4 bar k={k} height count {len(hs)}")
    for i, strat in enumerate(order):
        expected = float(g.loc[strat, metric])
        compared += 1
        check(math.isclose(hs[i], expected, rel_tol=0, abs_tol=0),
              f"F4 {corpus} {strat} {metric}: {hs[i]!r} != {expected!r}")

star_recs = records["plot"]
expected_stars = []
for corpus in ["DSA_gold_standard_MEKG", "metacademy_gold_standard_MEKG"]:
    g = d4[d4.corpus == corpus].set_index("strategy").loc[order]
    for strat in order:
        v = g.loc[strat, "random_baseline_recall"]
        if pd.notna(v):
            expected_stars.append((corpus, strat, float(v)))
check(len(star_recs) == len(expected_stars), f"F4 expected {len(expected_stars)} non-NaN random-baseline stars, saw {len(star_recs)}")
for (panel, x, y), (corpus, strat, expected) in zip(star_recs, expected_stars):
    compared += 1
    check(math.isclose(y, expected, rel_tol=0, abs_tol=0), f"F4 star {corpus} {strat}: {y!r} != {expected!r}")

# ---------- F6 / F6b: scatter points + annotations ----------
dsets = [
    ("F6_cost_vs_accuracy_dominance.csv", "F6"),
    ("F6b_cost_vs_accuracy_logx.csv", "F6b"),
]
expected_annotations = []
for csv_name, tag in dsets:
    d = pd.read_csv(SRC / csv_name)
    if "plotted" in d:
        d = d[d.plotted.astype(str) == "True"]
    rows = list(d.iterrows())
    check(len(rows) == 8, f"{tag} expected 8 plotted points, saw {len(rows)}")
    sc = [r for r in records["scatter"] if r[4] and r[4].startswith("Strategy")]
    if tag == "F6":
        sc = sc[:8]
    else:
        sc = sc[8:16]
    check(len(sc) == 8, f"{tag} expected 8 scatter records, saw {len(sc)}")
    for (_, row), (panel, x, y, marker, label) in zip(rows, sc):
        compared += 2
        check(math.isclose(x, float(row.calls), rel_tol=0, abs_tol=0), f"{tag} calls {row.strategy}: {x!r} != {row.calls!r}")
        check(math.isclose(y, float(row.f1), rel_tol=0, abs_tol=0), f"{tag} f1 {row.strategy}: {y!r} != {row.f1!r}")
        code = {"brute_force": "S1", "embedding_threshold": "S2",
                "ann_retrieval": "S3", "bounded_bucket": "S4"}[row.strategy]
        expected_annotations.append(f"{code} {row.strategy}\n({row.calls:.1f}, {row.f1:.3f})")
ann_recs = [r for r in records["annotate"] if r[3] is not None]
check(len(ann_recs) == 16, f"expected 16 point annotations (F6+F6b), saw {len(ann_recs)}")
ann_texts = [r[1] for r in ann_recs]
check(ann_texts == expected_annotations, "annotation texts differ from CSV-derived expected texts")
for k, (_, txt, xy, xytext) in enumerate(ann_recs):
    compared += 2
    d = pd.read_csv(SRC / dsets[k // 8][0])
    if "plotted" in d:
        d = d[d.plotted.astype(str) == "True"]
    row = list(d.iterrows())[k % 8][1]
    check(math.isclose(xy[0], float(row.calls), rel_tol=0, abs_tol=0) and
          math.isclose(xy[1], float(row.f1), rel_tol=0, abs_tol=0),
          f"annotation anchor k={k} != CSV point")

# ---------- dominance text lines ----------
dom = pd.read_csv(SRC / "F6_dominance.csv")
codes = {"brute_force": "S1", "embedding_threshold": "S2",
         "ann_retrieval": "S3", "bounded_bucket": "S4"}
expected_dom = {}
for corpus in ["DSA_gold_standard_MEKG", "metacademy_gold_standard_MEKG"]:
    lines = []
    for _, r in dom[dom.corpus == corpus].iterrows():
        a, b = codes[r.strategy_a], codes[r.strategy_b]
        res = r.dominance
        if res == "A dominates B":
            res = f"{a} dominates {b}"
        elif res == "B dominates A":
            res = f"{b} dominates {a}"
        elif res.startswith("not distinguishable"):
            res = "not distinguishable (F1 within 0.025)"
        lines.append(f"{a} vs {b}: {res}")
    expected_dom[corpus] = "\n".join(lines)
dom_texts = [r[1] for r in records["text"]]
check(len(dom_texts) == 4, f"expected 4 dominance boxes (2 figures x 2 panels), saw {len(dom_texts)}")
for k, (panel, txt) in enumerate(records["text"]):
    corpus = "DSA_gold_standard_MEKG" if panel == 0 else "metacademy_gold_standard_MEKG"
    compared += len(expected_dom[corpus].splitlines())
    check(txt == expected_dom[corpus], f"dominance text k={k} {corpus} differs")
check(len([r for r in records["bar"] if r[2]]) == 8, "F4 bar-call count drift")

print(f"F4: 32 bar values (8 bar calls x 4 strategies) + {len(expected_stars)} non-NaN random-baseline markers compared")
print(f"F6: 8 points x (calls, f1) + 8 annotations compared")
print(f"F6b: 8 points x (calls, f1) + 8 annotations compared")
print(f"F6/F6b dominance: 24 text-line comparisons (12 lines x 2 figures)")
print(f"TOTAL numeric values compared: {compared}")
print("MISMATCH COUNT:", mismatch)
print("DATA INTEGRITY:", "PASS" if OK else "FAIL")
sys.exit(0 if OK else 1)
```
