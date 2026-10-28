"""posthoc.py — Post-hoc decision and ranking framework (thesis Sections 3.6, 4.4.1).

STATUS: POST HOC, NOT PRE-REGISTERED. Specified after the Chapter 4
measurements existed and frozen in decision-log [D-89] before any ranking
artifact was computed. Adds no measurement and replaces no pre-registered
result. Applied to single-run measurements, so the outputs are
classifications of those measurements, not statistical tests.

This module imports the existing pipeline unchanged:
- ``stats.evaluate_dominance`` for gate G3 (0.025 F1 margin, Rule R2);
- ``tables.write_csv`` / ``tables.export_markdown_table`` for output;
- ``validate_runs.parse_raw_jsonl`` / ``parse_sidecar`` only to recover the
  realised shortlist sizes used by the G1 size-matched baseline.

All inputs are the in-memory aggregates produced by
``generate_t1_accuracy_table`` and ``generate_t2_sweep_cost_table``; those
values are asserted against the existing ``final_output_final`` CSV cells.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from .stats import evaluate_dominance
    from .tables import export_markdown_table, extract_variant_label, write_csv
    from .validate_runs import parse_raw_jsonl, parse_sidecar
except ImportError:  # pragma: no cover - direct script execution
    from stats import evaluate_dominance
    from tables import export_markdown_table, extract_variant_label, write_csv
    from validate_runs import parse_raw_jsonl, parse_sidecar


STATUS = "post-hoc"
POSTHOC_LABEL = "POST HOC: not pre-registered"

STRATEGY_ORDER = [
    "brute_force",
    "embedding_threshold",
    "ann_retrieval",
    "bounded_bucket",
]
STRATEGY_CODE = {
    "brute_force": "S1",
    "embedding_threshold": "S2",
    "ann_retrieval": "S3",
    "bounded_bucket": "S4",
}
CODE_TO_STRATEGY = {v: k for k, v in STRATEGY_CODE.items()}

CORPUS_ORDER = ["DSA_gold_standard_MEKG", "metacademy_gold_standard_MEKG"]
CORPUS_SHORT = {
    "DSA_gold_standard_MEKG": "DSA",
    "metacademy_gold_standard_MEKG": "Metacademy",
}
CORPUS_M = {
    "DSA_gold_standard_MEKG": 28,
    "metacademy_gold_standard_MEKG": 140,
}

SCENARIOS = (
    ("accuracy-first", 0.7),
    ("balanced", 0.5),
    ("cost-first", 0.3),
)

G2_LIMIT = 50.0
G3_MARGIN = 0.025
G2_SENSITIVITY_LIMITS = list(range(10, 2000))
G3_SENSITIVITY_MARGINS = [round(0.005 * k, 3) for k in range(0, 31)]

# Tie tolerance frozen in [D-89](6)(e) and [D-89](7)(b).
TIE_TOL = 10.0 ** -12

WEIGHT_DRAWS = 20_000
WEIGHT_SEED = 42

# Output basenames frozen in [D-89](12).
T5 = "T5_gates_and_classes"
T5B = "T5b_gate_sensitivity"
T6 = "T6_single_criterion_ranks"
T7 = "T7_weighted_scores"
T8 = "T8_rank_shares"
T8B = "T8b_rank_shares_exact"
T9 = "T9_topsis_kendall_tau"
T9B = "T9b_walltime_substituted_scores"


# ---------------------------------------------------------------------------
# Input assembly
# ---------------------------------------------------------------------------

def _primary_accuracy_rows(t1_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in t1_rows:
        if "primary" not in str(row.get("variant", "")):
            continue
        if row.get("strategy") not in STRATEGY_ORDER:
            continue
        if row.get("corpus") not in CORPUS_ORDER:
            continue
        out.append(row)
    return out


def _primary_sweep_rows(t2_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in t2_rows:
        if "primary" not in str(row.get("variant", "")):
            continue
        if row.get("strategy") not in STRATEGY_ORDER:
            continue
        if int(row.get("size_n", -1)) != 2000:
            continue
        out.append(row)
    return out


def extract_inputs(
    t1_rows: Sequence[Dict[str, Any]],
    t2_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assemble the frozen per-strategy inputs from the T1/T2 aggregates.

    Raises KeyError/ValueError if a primary configuration or corpus is
    missing, or if a duplicate primary row is found.
    """
    accuracy: Dict[str, Dict[str, Dict[str, Any]]] = {c: {} for c in CORPUS_ORDER}
    for row in _primary_accuracy_rows(t1_rows):
        corpus = row["corpus"]
        strat = row["strategy"]
        if strat in accuracy[corpus]:
            raise ValueError(f"Duplicate primary accuracy row for {strat} / {corpus}")
        accuracy[corpus][strat] = {
            "variant": row["variant"],
            "f1_micro": float(row["f1_micro"]),
            "recall_micro": float(row["recall_micro"]),
            "precision_micro": float(row["precision_micro"]),
            "llm_calls_mean": float(row["llm_calls_mean"]),
            "shortlist_recall_micro": float(row["shortlist_recall_micro"]),
            "random_baseline_recall": float(row["random_baseline_recall"]),
            "num_trials": int(row.get("num_trials", 0)),
        }

    for corpus in CORPUS_ORDER:
        missing = [s for s in STRATEGY_ORDER if s not in accuracy[corpus]]
        if missing:
            raise KeyError(f"Missing primary accuracy rows for {corpus}: {missing}")

    sweep: Dict[str, Dict[str, float]] = {}
    for row in _primary_sweep_rows(t2_rows):
        strat = row["strategy"]
        if strat in sweep:
            raise ValueError(f"Duplicate primary sweep n=2000 row for {strat}")
        sweep[strat] = {
            "llm_calls_mean": float(row["llm_calls_mean"]),
            "total_s_mean": float(row["total_s_mean"]),
        }
    missing_sweep = [s for s in STRATEGY_ORDER if s not in sweep]
    if missing_sweep:
        raise KeyError(f"Missing primary sweep n=2000 rows: {missing_sweep}")

    return {"accuracy": accuracy, "sweep": sweep}


def realised_shortlist_sizes(
    accuracy_run_dirs: Sequence[Path],
) -> Dict[str, Dict[str, float]]:
    """Mean realised shortlist size over successful accuracy trials.

    One call is made per shortlisted candidate, so for Strategies 3 and 4 the
    mean ``metrics.shortlist_size`` equals the mean call count reported in T1.
    The caller asserts that equality.
    """
    result: Dict[str, Dict[str, List[float]]] = {c: {} for c in CORPUS_ORDER}
    for run_dir in sorted(accuracy_run_dirs):
        sidecar_p = Path(run_dir) / "strategy_config.json"
        raw_p = Path(run_dir) / "raw.jsonl"
        if not sidecar_p.is_file() or not raw_p.is_file():
            continue
        sidecar = parse_sidecar(sidecar_p)
        strat = sidecar.get("strategy")
        if strat not in ("ann_retrieval", "bounded_bucket"):
            continue
        variant = extract_variant_label(Path(run_dir).name)
        if "primary" not in variant:
            continue
        records, _, _, _ = parse_raw_jsonl(raw_p)
        latest: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            key = rec.get("key")
            if key is not None:
                latest[key] = rec
        for rec in latest.values():
            if rec.get("status") != "success":
                continue
            corpus = rec.get("corpus")
            if corpus not in CORPUS_ORDER:
                continue
            metrics = rec.get("metrics", {})
            size = metrics.get("shortlist_size")
            if size is None:
                continue
            result[corpus].setdefault(strat, []).append(float(size))

    means: Dict[str, Dict[str, float]] = {c: {} for c in CORPUS_ORDER}
    for corpus in CORPUS_ORDER:
        for strat, values in result[corpus].items():
            if values:
                means[corpus][strat] = float(np.mean(values))
    return means


# ---------------------------------------------------------------------------
# Cross-check against the existing pre-registered output
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _close(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= rel_tol * max(1.0, abs(a), abs(b))


def assert_matches_final_output(
    inputs: Dict[str, Any],
    crosscheck_dir: Path,
) -> int:
    """Assert that every value used equals its final_output_final CSV cell.

    Compares against T1 (accuracy), T2 (n=2000 primary rows) and the F6
    figure CSV. Returns the number of cell comparisons performed.
    """
    crosscheck_dir = Path(crosscheck_dir)
    t1_path = crosscheck_dir / "tables" / "T1_accuracy_benchmark.csv"
    t2_path = crosscheck_dir / "tables" / "T2_sweep_cost_summary.csv"
    f6_path = crosscheck_dir / "figures" / "F6_cost_vs_accuracy_dominance.csv"

    n_checks = 0

    t1_by_key: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    for row in _read_csv(t1_path):
        if "primary" in row.get("variant", ""):
            t1_by_key[(row["strategy"], row["variant"], row["corpus"])] = row

    for corpus in CORPUS_ORDER:
        for strat in STRATEGY_ORDER:
            src = inputs["accuracy"][corpus][strat]
            key = (strat, src["variant"], corpus)
            if key not in t1_by_key:
                raise AssertionError(f"Cross-check T1 cell missing for {key}")
            cell = t1_by_key[key]
            for field in (
                "f1_micro",
                "recall_micro",
                "precision_micro",
                "llm_calls_mean",
                "shortlist_recall_micro",
                "random_baseline_recall",
            ):
                expected = float(cell[field]) if cell[field] not in ("", "nan") else float("nan")
                if not _close(src[field], expected):
                    raise AssertionError(
                        f"Cross-check T1 {field} mismatch for {key}: "
                        f"in-memory {src[field]!r} vs CSV {expected!r}"
                    )
                n_checks += 1

    t2_by_key: Dict[Tuple[str, str, int], Dict[str, str]] = {}
    for row in _read_csv(t2_path):
        if "primary" in row.get("variant", ""):
            t2_by_key[(row["strategy"], row["variant"], int(row["size_n"]))] = row

    for strat in STRATEGY_ORDER:
        variant = inputs["accuracy"][CORPUS_ORDER[0]][strat]["variant"]
        key = (strat, variant, 2000)
        if key not in t2_by_key:
            raise AssertionError(f"Cross-check T2 n=2000 cell missing for {key}")
        cell = t2_by_key[key]
        for field in ("llm_calls_mean", "total_s_mean"):
            expected = float(cell[field])
            if not _close(inputs["sweep"][strat][field], expected):
                raise AssertionError(
                    f"Cross-check T2 {field} mismatch for {key}: "
                    f"in-memory {inputs['sweep'][strat][field]!r} vs CSV {expected!r}"
                )
            n_checks += 1

    f6_by_key: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in _read_csv(f6_path):
        f6_by_key[(row["strategy"], row["corpus"])] = row

    for corpus in CORPUS_ORDER:
        for strat in STRATEGY_ORDER:
            src = inputs["accuracy"][corpus][strat]
            key = (strat, corpus)
            if key not in f6_by_key:
                raise AssertionError(f"Cross-check F6 cell missing for {key}")
            cell = f6_by_key[key]
            for field, src_field in (("calls", "llm_calls_mean"), ("f1", "f1_micro")):
                expected = float(cell[field])
                if not _close(src[src_field], expected):
                    raise AssertionError(
                        f"Cross-check F6 {field} mismatch for {key}: "
                        f"in-memory {src[src_field]!r} vs CSV {expected!r}"
                    )
                n_checks += 1

    return n_checks


# ---------------------------------------------------------------------------
# Normalisation, ranking, weighted scores
# ---------------------------------------------------------------------------

def _normalise(values: Dict[str, float], higher_is_better: bool) -> Tuple[Dict[str, float], bool]:
    """Min-max normalise; return (scores, degenerate_flag)."""
    vals = list(values.values())
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) <= TIE_TOL:
        return ({s: 0.5 for s in values}, True)
    out = {s: (v - lo) / (hi - lo) for s, v in values.items()}
    if not higher_is_better:
        out = {s: 1.0 - v for s, v in out.items()}
    return (out, False)


def compute_A_C(inputs: Dict[str, Any], corpus: str) -> Dict[str, Any]:
    """Compute A_i and C_i for one corpus, per [D-89](6)."""
    acc = inputs["accuracy"][corpus]
    f1 = {s: acc[s]["f1_micro"] for s in STRATEGY_ORDER}
    calls = {s: acc[s]["llm_calls_mean"] for s in STRATEGY_ORDER}
    g = {s: math.log10(1.0 + calls[s]) for s in STRATEGY_ORDER}
    if any(c < 0 for c in calls.values()):
        raise ValueError(f"Negative mean calls for {corpus}: {calls}")

    a, a_degenerate = _normalise(f1, higher_is_better=True)
    c, c_degenerate = _normalise(g, higher_is_better=False)
    return {
        "A": a,
        "C": c,
        "g": g,
        "calls": calls,
        "f1": f1,
        "degenerate": {"A": a_degenerate, "C": c_degenerate},
    }


def _order_key(name: str) -> Tuple[int, str]:
    """Deterministic tie-break order: frozen strategy order, then name."""
    if name in STRATEGY_ORDER:
        return (STRATEGY_ORDER.index(name), name)
    return (len(STRATEGY_ORDER), name)


def weighted_scores(A: Dict[str, float], C: Dict[str, float], w: float) -> Dict[str, float]:
    if set(A) != set(C):
        raise ValueError("A and C must have the same strategy keys")
    return {s: w * A[s] + (1.0 - w) * C[s] for s in A}


def rank_with_ties(scores: Dict[str, float], higher_is_better: bool = True) -> Dict[str, float]:
    """Mean-of-occupied-ranks ranking with the frozen tie tolerance."""
    sign = -1.0 if higher_is_better else 1.0
    ordered = sorted(
        scores.items(),
        key=lambda kv: (sign * kv[1], _order_key(kv[0])),
    )
    ranks: Dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and abs(ordered[j + 1][1] - ordered[i][1]) <= TIE_TOL:
            j += 1
        mean_rank = ((i + 1) + (j + 1)) / 2.0
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = mean_rank
        i = j + 1
    return ranks


def strict_ranks(scores: Dict[str, float]) -> Dict[str, int]:
    """Strict descending rank; ties broken by the frozen strategy order."""
    ordered = sorted(
        scores.items(),
        key=lambda kv: (-kv[1], _order_key(kv[0])),
    )
    return {s: i + 1 for i, (s, _) in enumerate(ordered)}


def _has_tie(scores: Dict[str, float]) -> bool:
    vals = list(scores.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            if abs(vals[i] - vals[j]) <= TIE_TOL:
                return True
    return False


# ---------------------------------------------------------------------------
# Gates (T5) and gate sensitivity (T5b)
# ---------------------------------------------------------------------------

def _g1_outcome(
    inputs: Dict[str, Any],
    strat: str,
    baseline: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """G1 per corpus. ``baseline`` maps corpus -> strategy -> threshold."""
    if strat == "brute_force":
        return {"status": "not applicable", "per_corpus": {}, "assessable": False}
    if strat == "embedding_threshold":
        return {"status": "not assessable", "per_corpus": {}, "assessable": False}

    per_corpus: Dict[str, Dict[str, Any]] = {}
    for corpus in CORPUS_ORDER:
        src = inputs["accuracy"][corpus][strat]
        if baseline is None:
            threshold = src["random_baseline_recall"]
        else:
            threshold = baseline[corpus][strat]
        per_corpus[corpus] = {
            "shortlist_recall": src["shortlist_recall_micro"],
            "baseline": threshold,
            "passed": bool(src["shortlist_recall_micro"] > threshold),
        }
    overall = all(v["passed"] for v in per_corpus.values())
    return {
        "status": "pass" if overall else "fail",
        "per_corpus": per_corpus,
        "assessable": True,
    }


def _g3_outcome(
    inputs: Dict[str, Any],
    strat: str,
    margin: float,
) -> Dict[str, Any]:
    per_corpus: Dict[str, Dict[str, Any]] = {}
    dominated_overall = False
    for corpus in CORPUS_ORDER:
        acc = inputs["accuracy"][corpus]
        point_self = {"calls": acc[strat]["llm_calls_mean"], "f1": acc[strat]["f1_micro"]}
        dominators = []
        for other in STRATEGY_ORDER:
            if other == strat:
                continue
            point_other = {"calls": acc[other]["llm_calls_mean"], "f1": acc[other]["f1_micro"]}
            verdict = evaluate_dominance(point_other, point_self, f1_delta_threshold=margin)
            if verdict == "A dominates B":
                dominators.append(other)
        per_corpus[corpus] = {
            "dominated": bool(dominators),
            "dominators": dominators,
        }
        dominated_overall = dominated_overall or bool(dominators)
    return {
        "status": "fail" if dominated_overall else "pass",
        "per_corpus": per_corpus,
    }


def gate_class(g1: Dict[str, Any], g2: Dict[str, Any], g3: Dict[str, Any]) -> str:
    if g1["assessable"]:
        if g1["status"] == "pass" and g2["status"] == "pass" and g3["status"] == "pass":
            return "Effective"
        return "Not effective"
    if g2["status"] == "pass" and g3["status"] == "pass":
        return "Conditionally effective"
    return "Not effective"


def compute_gates(
    inputs: Dict[str, Any],
    g2_limit: float = G2_LIMIT,
    g3_margin: float = G3_MARGIN,
    g1_baseline: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for strat in STRATEGY_ORDER:
        g1 = _g1_outcome(inputs, strat, g1_baseline)
        calls = inputs["sweep"][strat]["llm_calls_mean"]
        g2 = {"status": "pass" if calls <= g2_limit else "fail", "calls": calls, "limit": g2_limit}
        g3 = _g3_outcome(inputs, strat, g3_margin)
        out[strat] = {
            "g1": g1,
            "g2": g2,
            "g3": g3,
            "class": gate_class(g1, g2, g3),
        }
    return out


def size_matched_baselines(
    inputs: Dict[str, Any],
    shortlist_means: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    baseline: Dict[str, Dict[str, float]] = {c: {} for c in CORPUS_ORDER}
    for corpus in CORPUS_ORDER:
        m = CORPUS_M[corpus]
        for strat in ("ann_retrieval", "bounded_bucket"):
            size = shortlist_means[corpus][strat]
            reported_calls = inputs["accuracy"][corpus][strat]["llm_calls_mean"]
            if not _close(size, reported_calls):
                raise AssertionError(
                    f"Realised mean shortlist size {size!r} != T1 mean calls {reported_calls!r} "
                    f"for {strat} / {corpus}"
                )
            baseline[corpus][strat] = size / m
    return baseline


def build_t5_rows(gates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for strat in STRATEGY_ORDER:
        g = gates[strat]
        row = {
            "status": STATUS,
            "strategy": strat,
            "code": STRATEGY_CODE[strat],
            "g1_overall": g["g1"]["status"],
            "g1_dsa": "",
            "g1_metacademy": "",
            "g2_calls_n2000": g["g2"]["calls"],
            "g2_limit": g["g2"]["limit"],
            "g2_status": g["g2"]["status"],
            "g3_overall": g["g3"]["status"],
            "g3_dsa": "",
            "g3_metacademy": "",
            "gate_class": g["class"],
        }
        for corpus, short in (
            ("DSA_gold_standard_MEKG", "g1_dsa"),
            ("metacademy_gold_standard_MEKG", "g1_metacademy"),
        ):
            info = g["g1"]["per_corpus"].get(corpus)
            if info:
                row[short] = (
                    f"{'pass' if info['passed'] else 'fail'} "
                    f"({info['shortlist_recall']:.3f} vs {info['baseline']:.3f})"
                )
            else:
                row[short] = g["g1"]["status"]
        for corpus, short in (
            ("DSA_gold_standard_MEKG", "g3_dsa"),
            ("metacademy_gold_standard_MEKG", "g3_metacademy"),
        ):
            info = g["g3"]["per_corpus"][corpus]
            row[short] = (
                "fail (dominated by " + ", ".join(STRATEGY_CODE[d] for d in info["dominators"]) + ")"
                if info["dominated"]
                else "pass"
            )
        rows.append(row)
    return rows


def build_t5b_rows(
    inputs: Dict[str, Any],
    gates: Dict[str, Dict[str, Any]],
    sm_baseline: Dict[str, Dict[str, float]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Gate-sensitivity evidence; returns (rows, summary)."""
    rows: List[Dict[str, Any]] = []
    frozen_classes = {s: gates[s]["class"] for s in STRATEGY_ORDER}

    # (a) G2 every integer limit 10..1999. G2 is monotone in the limit and the
    # per-strategy calls are constant, so testing every limit is cheap.
    g2_changes = []
    for limit in G2_SENSITIVITY_LIMITS:
        classes = {
            s: gate_class(
                gates[s]["g1"],
                {"status": "pass" if inputs["sweep"][s]["llm_calls_mean"] <= limit else "fail"},
                gates[s]["g3"],
            )
            for s in STRATEGY_ORDER
        }
        if classes != frozen_classes:
            g2_changes.append({"limit": limit, "classes": classes})
    for strat in STRATEGY_ORDER:
        rows.append({
            "status": STATUS,
            "family": "G2",
            "setting": "every integer limit 10..1999 (1990 settings)",
            "strategy": STRATEGY_CODE[strat],
            "value": inputs["sweep"][strat]["llm_calls_mean"],
            "gate_status": "pass" if inputs["sweep"][strat]["llm_calls_mean"] <= 1999 else "fail",
            "class": frozen_classes[strat],
            "class_unchanged": not g2_changes,
            "detail": f"{len(g2_changes)} class changes over the limit range",
        })

    # (b) G1 size-matched baseline.
    for strat in STRATEGY_ORDER:
        g1_sm = _g1_outcome(inputs, strat, sm_baseline)
        cls = gate_class(g1_sm, gates[strat]["g2"], gates[strat]["g3"])
        for corpus in CORPUS_ORDER:
            info = g1_sm["per_corpus"].get(corpus)
            if info is None:
                rows.append({
                    "status": STATUS,
                    "family": "G1",
                    "setting": "size-matched baseline",
                    "strategy": STRATEGY_CODE[strat],
                    "value": "",
                    "gate_status": g1_sm["status"],
                    "class": cls,
                    "class_unchanged": cls == frozen_classes[strat],
                    "detail": f"{CORPUS_SHORT[corpus]}: no baseline applies",
                })
            else:
                rows.append({
                    "status": STATUS,
                    "family": "G1",
                    "setting": "size-matched baseline",
                    "strategy": STRATEGY_CODE[strat],
                    "value": info["shortlist_recall"],
                    "gate_status": "pass" if info["passed"] else "fail",
                    "class": cls,
                    "class_unchanged": cls == frozen_classes[strat],
                    "detail": (
                        f"{CORPUS_SHORT[corpus]}: baseline {info['baseline']:.4f} "
                        f"(mean shortlist size {info['baseline'] * CORPUS_M[corpus]:.4f} / m={CORPUS_M[corpus]})"
                    ),
                })

    # (c) G3 margin 0..0.15 in 0.005 steps.
    g3_changes: List[Dict[str, Any]] = []
    for margin in G3_SENSITIVITY_MARGINS:
        for strat in STRATEGY_ORDER:
            g3 = _g3_outcome(inputs, strat, margin)
            cls = gate_class(gates[strat]["g1"], gates[strat]["g2"], g3)
            changed = cls != frozen_classes[strat]
            if changed:
                g3_changes.append({"margin": margin, "strategy": strat, "class": cls})
            detail = "; ".join(
                f"{CORPUS_SHORT[c]}: " + (
                    "dominated by " + ", ".join(STRATEGY_CODE[d] for d in g3["per_corpus"][c]["dominators"])
                    if g3["per_corpus"][c]["dominated"] else "not dominated"
                )
                for c in CORPUS_ORDER
            )
            rows.append({
                "status": STATUS,
                "family": "G3",
                "setting": f"margin={margin:.3f}",
                "strategy": STRATEGY_CODE[strat],
                "value": margin,
                "gate_status": g3["status"],
                "class": cls,
                "class_unchanged": not changed,
                "detail": detail,
            })

    first_g3_change = g3_changes[0]["margin"] if g3_changes else None
    summary = {
        "g2_n_settings": len(G2_SENSITIVITY_LIMITS),
        "g2_changes": g2_changes,
        "g3_first_change": first_g3_change,
        "g3_changes": g3_changes,
        "classes_unchanged_all": (
            not g2_changes
            and not g3_changes
            and all(r["class_unchanged"] for r in rows if r["family"] == "G1")
        ),
    }
    return rows, summary


# ---------------------------------------------------------------------------
# Single-criterion ranks (T6), weighted scores (T7), wall-clock check (T9b)
# ---------------------------------------------------------------------------

def build_t6_rows(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    calls = {s: inputs["sweep"][s]["llm_calls_mean"] for s in STRATEGY_ORDER}
    wall = {s: inputs["sweep"][s]["total_s_mean"] for s in STRATEGY_ORDER}
    calls_rank = rank_with_ties(calls, higher_is_better=False)
    wall_rank = rank_with_ties(wall, higher_is_better=False)
    for corpus in CORPUS_ORDER:
        f1 = {s: inputs["accuracy"][corpus][s]["f1_micro"] for s in STRATEGY_ORDER}
        f1_rank = rank_with_ties(f1, higher_is_better=True)
        for strat in STRATEGY_ORDER:
            rows.append({
                "status": STATUS,
                "corpus": corpus,
                "strategy": strat,
                "code": STRATEGY_CODE[strat],
                "f1_micro": f1[strat],
                "f1_rank": f1_rank[strat],
                "calls_n2000_mean": calls[strat],
                "calls_rank": calls_rank[strat],
                "total_s_n2000_mean": wall[strat],
                "wallclock_rank": wall_rank[strat],
            })
    return rows


def build_t7_rows(inputs: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    store: Dict[str, Any] = {}
    for corpus in CORPUS_ORDER:
        ac = compute_A_C(inputs, corpus)
        store[corpus] = ac
        for scenario, w in SCENARIOS:
            scores = weighted_scores(ac["A"], ac["C"], w)
            ranks = rank_with_ties(scores, higher_is_better=True)
            best_score = max(scores.values())
            for strat in STRATEGY_ORDER:
                rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "scenario": scenario,
                    "accuracy_weight": w,
                    "cost_weight": 1.0 - w,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "A_i": ac["A"][strat],
                    "C_i": ac["C"][strat],
                    "g_i": ac["g"][strat],
                    "score": scores[strat],
                    "rank": ranks[strat],
                    "is_best": abs(scores[strat] - best_score) <= TIE_TOL,
                    "degenerate_criterion": (
                        f"A={ac['degenerate']['A']};C={ac['degenerate']['C']}"
                    ),
                })
    return rows, store


def build_t9b_rows(
    inputs: Dict[str, Any],
    store: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    g_wall = {
        s: math.log10(1.0 + inputs["sweep"][s]["total_s_mean"])
        for s in STRATEGY_ORDER
    }
    c_wall, degenerate = _normalise(g_wall, higher_is_better=False)
    rows: List[Dict[str, Any]] = []
    comparison: Dict[str, Any] = {}
    for corpus in CORPUS_ORDER:
        ac = store[corpus]
        for scenario, w in SCENARIOS:
            scores = {s: w * ac["A"][s] + (1.0 - w) * c_wall[s] for s in STRATEGY_ORDER}
            ranks = rank_with_ties(scores, higher_is_better=True)
            tops = [s for s in STRATEGY_ORDER if ranks[s] == min(ranks.values())]
            t7_scores = weighted_scores(ac["A"], ac["C"], w)
            t7_ranks = rank_with_ties(t7_scores, higher_is_better=True)
            t7_tops = [s for s in STRATEGY_ORDER if t7_ranks[s] == min(t7_ranks.values())]
            match = set(tops) == set(t7_tops)
            comparison[f"{corpus}|{scenario}"] = {
                "tops": tops,
                "t7_tops": t7_tops,
                "match": match,
            }
            for strat in STRATEGY_ORDER:
                rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "scenario": scenario,
                    "accuracy_weight": w,
                    "cost_weight": 1.0 - w,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "A_i": ac["A"][strat],
                    "C_i_wallclock": c_wall[strat],
                    "g_wallclock": g_wall[strat],
                    "score": scores[strat],
                    "rank": ranks[strat],
                    "top_matches_T7": match,
                    "degenerate_C": degenerate,
                })
    return rows, comparison


# ---------------------------------------------------------------------------
# Weight sweep (T8) and exact shares (T8b)
# ---------------------------------------------------------------------------

def mc_rank_shares(
    A: Dict[str, float],
    C: Dict[str, float],
    n_draws: int = WEIGHT_DRAWS,
    seed: int = WEIGHT_SEED,
) -> Dict[str, Any]:
    """Monte Carlo rank shares per [D-89](7)."""
    keys = list(A)
    n_ranks = len(keys)
    rng = np.random.default_rng(seed)
    draws = rng.random(n_draws)
    counts = {s: {r: 0 for r in range(1, n_ranks + 1)} for s in keys}
    tie_draws = 0
    for w in draws:
        scores = weighted_scores(A, C, float(w))
        if _has_tie(scores):
            tie_draws += 1
        for s, r in strict_ranks(scores).items():
            counts[s][r] += 1
    shares = {
        s: {r: counts[s][r] / n_draws for r in range(1, n_ranks + 1)}
        for s in keys
    }
    se = {
        s: {r: math.sqrt(max(0.0, shares[s][r] * (1.0 - shares[s][r]) / n_draws)) for r in range(1, n_ranks + 1)}
        for s in keys
    }
    return {"shares": shares, "se": se, "tie_draws": tie_draws, "n_draws": n_draws, "seed": seed}


def exact_rank_shares(A: Dict[str, float], C: Dict[str, float]) -> Dict[str, Any]:
    """Analytic rank shares per [D-89](8)."""
    keys = list(A)
    n_ranks = len(keys)
    breakpoints = [0.0, 1.0]
    structural_ties = False
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            si, sj = keys[i], keys[j]
            den = (A[si] - C[si]) - (A[sj] - C[sj])
            if abs(den) <= TIE_TOL:
                if abs(C[sj] - C[si]) <= TIE_TOL:
                    structural_ties = True
                continue
            w = (C[sj] - C[si]) / den
            if 0.0 < w < 1.0:
                breakpoints.append(w)
    xs = sorted(set(breakpoints))
    shares = {s: {r: 0.0 for r in range(1, n_ranks + 1)} for s in keys}
    for a, b in zip(xs, xs[1:]):
        mid = (a + b) / 2.0
        ranks = strict_ranks(weighted_scores(A, C, mid))
        for s, r in ranks.items():
            shares[s][r] += (b - a)
    return {"shares": shares, "n_intervals": len(xs) - 1, "structural_ties": structural_ties}


# ---------------------------------------------------------------------------
# TOPSIS and Kendall tau-b (T9)
# ---------------------------------------------------------------------------

def topsis_closeness(A: Dict[str, float], C: Dict[str, float], w: float) -> Dict[str, float]:
    """Weighted TOPSIS closeness per [D-89](9)."""
    out: Dict[str, float] = {}
    for s in A:
        d_pos = math.hypot(w * A[s] - w, (1.0 - w) * C[s] - (1.0 - w))
        d_neg = math.hypot(w * A[s], (1.0 - w) * C[s])
        denom = d_pos + d_neg
        out[s] = (d_neg / denom) if denom > 0 else float("nan")
    return out


def kendall_tau_b(
    x: Dict[str, float],
    y: Dict[str, float],
) -> Dict[str, Any]:
    """Kendall tau-b with the tie correction, implemented by hand.

    Returns tau, the number of tied pairs, and pair counts.
    """
    keys = sorted(x, key=_order_key)
    n = len(keys)
    concordant = discordant = 0
    tied_x = tied_y = tied_both = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[keys[i]] - x[keys[j]]
            dy = y[keys[i]] - y[keys[j]]
            sx = 0 if abs(dx) <= TIE_TOL else (1 if dx > 0 else -1)
            sy = 0 if abs(dy) <= TIE_TOL else (1 if dy > 0 else -1)
            if sx == 0 and sy == 0:
                tied_both += 1
            elif sx == 0:
                tied_x += 1
            elif sy == 0:
                tied_y += 1
            elif sx * sy > 0:
                concordant += 1
            else:
                discordant += 1
    n0 = n * (n - 1) / 2.0
    n1 = tied_x + tied_both
    n2 = tied_y + tied_both
    denom = math.sqrt(max(0.0, (n0 - n1) * (n0 - n2)))
    tau = ((concordant - discordant) / denom) if denom > 0 else float("nan")
    return {
        "tau": tau,
        "tied_pairs": tied_x + tied_y + tied_both,
        "concordant": concordant,
        "discordant": discordant,
        "tied_x": n1,
        "tied_y": n2,
    }


def build_t9_rows(store: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for corpus in CORPUS_ORDER:
        ac = store[corpus]
        for scenario, w in SCENARIOS:
            sums = weighted_scores(ac["A"], ac["C"], w)
            sum_ranks = rank_with_ties(sums, higher_is_better=True)
            close = topsis_closeness(ac["A"], ac["C"], w)
            topsis_ranks = rank_with_ties(close, higher_is_better=True)
            tau = kendall_tau_b(topsis_ranks, sum_ranks)
            for strat in STRATEGY_ORDER:
                rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "scenario": scenario,
                    "accuracy_weight": w,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "A_i": ac["A"][strat],
                    "C_i": ac["C"][strat],
                    "topsis_closeness": close[strat],
                    "topsis_rank": topsis_ranks[strat],
                    "weighted_sum_rank": sum_ranks[strat],
                    "kendall_tau_b": tau["tau"],
                    "tied_pairs": tau["tied_pairs"],
                })
    return rows


# ---------------------------------------------------------------------------
# Orchestration and output
# ---------------------------------------------------------------------------

def _write_table(rows: List[Dict[str, Any]], tables_dir: Path, name: str, title: str) -> None:
    write_csv(tables_dir / f"{name}.csv", rows)
    export_markdown_table(rows, tables_dir / f"{name}.md", title)


def _rounded_markdown_rows(rows: List[Dict[str, Any]], places: int = 2) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        new = {}
        for k, v in row.items():
            if isinstance(v, float):
                new[k] = f"{v:.{places}f}"
            else:
                new[k] = v
        out.append(new)
    return out


def build_t8_rows(store: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    mc_store: Dict[str, Any] = {}
    exact_store: Dict[str, Any] = {}
    for corpus in CORPUS_ORDER:
        ac = store[corpus]
        mc = mc_rank_shares(ac["A"], ac["C"])
        exact = exact_rank_shares(ac["A"], ac["C"])
        mc_store[corpus] = mc
        exact_store[corpus] = exact
        max_diff = max(
            abs(mc["shares"][s][r] - exact["shares"][s][r])
            for s in STRATEGY_ORDER for r in range(1, 5)
        )
        for strat in STRATEGY_ORDER:
            for rank in range(1, 5):
                rows.append({
                    "status": STATUS,
                    "corpus": corpus,
                    "strategy": strat,
                    "code": STRATEGY_CODE[strat],
                    "rank": rank,
                    "share_mc": mc["shares"][strat][rank],
                    "share_mc_se": mc["se"][strat][rank],
                    "share_exact": exact["shares"][strat][rank],
                    "abs_mc_minus_exact": abs(
                        mc["shares"][strat][rank] - exact["shares"][strat][rank]
                    ),
                    "max_abs_mc_minus_exact_corpus": max_diff,
                    "tie_draws": mc["tie_draws"],
                    "n_draws": mc["n_draws"],
                    "seed": mc["seed"],
                })
    return rows, mc_store, exact_store


def run_posthoc_stage(
    results_dir: Path,
    accuracy_run_dirs: Sequence[Path],
    t1_rows: Sequence[Dict[str, Any]],
    t2_rows: Sequence[Dict[str, Any]],
    output_dir: Path,
    crosscheck_dir: Path,
) -> Dict[str, Any]:
    """Run the whole post-hoc stage and write only its own artifacts."""
    # Figures are imported lazily so that a table-only test does not need
    # matplotlib's style module configured on import.
    try:
        from .posthoc_figures import plot_f7_gates, plot_f8_score_vs_weight, plot_f9_rank_shares
    except ImportError:  # pragma: no cover
        from posthoc_figures import plot_f7_gates, plot_f8_score_vs_weight, plot_f9_rank_shares

    tables_dir = Path(output_dir) / "tables"
    figures_dir = Path(output_dir) / "figures"

    inputs = extract_inputs(t1_rows, t2_rows)
    n_checks = assert_matches_final_output(inputs, crosscheck_dir)

    shortlist_means = realised_shortlist_sizes(accuracy_run_dirs)
    sm_baseline = size_matched_baselines(inputs, shortlist_means)

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    gates = compute_gates(inputs)
    t5_rows = build_t5_rows(gates)
    _write_table(t5_rows, tables_dir, T5, "Table T5: Gates and Classes (POST HOC, not pre-registered)")

    t5b_rows, t5b_summary = build_t5b_rows(inputs, gates, sm_baseline)
    _write_table(t5b_rows, tables_dir, T5B, "Table T5b: Gate Sensitivity (POST HOC, not pre-registered)")

    t6_rows = build_t6_rows(inputs)
    _write_table(t6_rows, tables_dir, T6, "Table T6: Single-Criterion Ranks (POST HOC, not pre-registered)")

    t7_rows, store = build_t7_rows(inputs)
    _write_table(t7_rows, tables_dir, T7, "Table T7: Weighted Scores (POST HOC, not pre-registered)")

    t8_rows, mc_store, exact_store = build_t8_rows(store)
    # [D-89](7)(c): full precision in the CSV, 2 decimals in the Markdown.
    write_csv(tables_dir / f"{T8}.csv", t8_rows)
    export_markdown_table(
        _rounded_markdown_rows(t8_rows),
        tables_dir / f"{T8}.md",
        "Table T8: Monte Carlo Rank Shares, 2 decimals (POST HOC, not pre-registered)",
    )
    t8b_rows = [
        {
            "status": STATUS,
            "corpus": row["corpus"],
            "strategy": row["strategy"],
            "code": row["code"],
            "rank": row["rank"],
            "share_exact": exact_store[row["corpus"]]["shares"][row["strategy"]][row["rank"]],
            "share_mc": mc_store[row["corpus"]]["shares"][row["strategy"]][row["rank"]],
            "abs_mc_minus_exact": row["abs_mc_minus_exact"],
            "max_abs_mc_minus_exact_corpus": row["max_abs_mc_minus_exact_corpus"],
            "status_note": (
                f"intervals={exact_store[row['corpus']]['n_intervals']}; "
                f"structural_ties={exact_store[row['corpus']]['structural_ties']}"
            ),
        }
        for row in t8_rows
    ]
    _write_table(
        t8b_rows, tables_dir, T8B,
        "Table T8b: Exact Analytic Rank Shares (POST HOC, not pre-registered)",
    )

    t9_rows = build_t9_rows(store)
    _write_table(t9_rows, tables_dir, T9, "Table T9: TOPSIS and Kendall tau-b (POST HOC, not pre-registered)")

    t9b_rows, t9b_comparison = build_t9b_rows(inputs, store)
    _write_table(
        t9b_rows, tables_dir, T9B,
        "Table T9b: Wall-Clock-Substituted Scores (POST HOC, not pre-registered)",
    )

    plot_f7_gates(inputs, gates, figures_dir)
    plot_f8_score_vs_weight(store, figures_dir)
    plot_f9_rank_shares(mc_store, figures_dir)

    return {
        "n_crosschecks": n_checks,
        "inputs": inputs,
        "gates": gates,
        "t5b_summary": t5b_summary,
        "store": store,
        "mc": mc_store,
        "exact": exact_store,
        "t9b_comparison": t9b_comparison,
        "shortlist_means": shortlist_means,
        "size_matched_baseline": sm_baseline,
    }
