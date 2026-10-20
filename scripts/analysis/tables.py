"""
tables.py — Table Generators for Phase 4 Report and Thesis
=========================================================
Implements Tables T1, T2, T3, and T4 from Section 5 of the Analysis Plan.
Includes:
- Table T1: Accuracy Benchmark Matrix (12 accuracy configurations)
- Table T2: Sweep Cost Summary (12 sweep configurations across sizes, with shortlist_s, decide_s,
            bootstrap CIs, log-log OLS slope fits, and post-hoc timing sensitivity columns)
- Table T3: Empirical Run Inventory (reproducibility and provenance)
- Table T4: Sensitivity Variants and Unjudged Predictions
Exports to CSV and GitHub-flavored Markdown.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    from .validate_runs import (
        parse_sidecar,
        parse_summary_csv,
        parse_raw_jsonl,
    )
    from .bootstrap import compute_series_stats
    from .stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness
except ImportError:
    from validate_runs import (
        parse_sidecar,
        parse_summary_csv,
        parse_raw_jsonl,
    )
    from bootstrap import compute_series_stats
    from stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness


def _require_col(row: Dict[str, Any], col: str, run_name: str) -> Any:
    """Strictly access a required column, raising KeyError naming run and column if missing."""
    if col not in row or row[col] == "" or row[col] is None:
        raise KeyError(f"Run '{run_name}' missing required column '{col}'")
    return row[col]


def extract_variant_label(run_name: str) -> str:
    """Extract a clean human-readable variant label from run directory name."""
    if "k10_ef128" in run_name and "smin" not in run_name:
        return "primary (k=10, ef=128)"
    elif "k5_ef128" in run_name:
        return "k=5 (ef=128)"
    elif "k20_ef128" in run_name:
        return "k=20 (ef=128)"
    elif "ef64" in run_name:
        return "ef=64 (k=10)"
    elif "ef256" in run_name:
        return "ef=256 (k=10)"
    elif "smin5_smax10" in run_name:
        return "primary (s_min=5, s_max=10, nb=12)"
    elif "smin2_smax5" in run_name:
        return "s_min=2, s_max=5 (nb=12)"
    elif "smin10_smax20" in run_name:
        return "s_min=10, s_max=20 (nb=12)"
    elif "theta0.6" in run_name:
        return "primary (theta=0.6)"
    elif "theta0.5" in run_name:
        return "theta=0.5"
    elif "theta0.4" in run_name:
        return "theta=0.4"
    elif "brute_force" in run_name:
        return "primary (all candidates)"
    return run_name


def write_csv(output_path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    """Write rows to a CSV file with deterministic column order."""
    if not rows and not fieldnames:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        seen_keys: Dict[str, None] = {}
        for r in rows:
            for k in r.keys():
                seen_keys[k] = None
        fieldnames = list(seen_keys.keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def export_markdown_table(
    rows: List[Dict[str, Any]],
    output_md_path: Path,
    title: str,
    headers: Optional[List[str]] = None,
) -> None:
    """Write table rows as a GitHub-flavored markdown table."""
    if not rows and not headers:
        return
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    if not headers:
        seen_keys: Dict[str, None] = {}
        for r in rows:
            for k in r.keys():
                seen_keys[k] = None
        headers = list(seen_keys.keys())

    lines = [f"# {title}\n", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        formatted_vals = []
        for h in headers:
            v = r.get(h, "")
            if isinstance(v, float):
                if np.isnan(v):
                    formatted_vals.append("NaN")
                elif abs(v) < 0.0001 and v != 0.0:
                    formatted_vals.append(f"{v:.4e}")
                elif abs(v) < 100:
                    formatted_vals.append(f"{v:.4f}")
                else:
                    formatted_vals.append(f"{v:.2f}")
            else:
                formatted_vals.append(str(v))
        lines.append("| " + " | ".join(formatted_vals) + " |")

    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def generate_t1_accuracy_table(
    accuracy_run_dirs: List[Path],
    output_csv_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Generate Table T1: All 12 accuracy configurations side-by-side.

    Excludes sensitivity variants (which belong in T4).
    Reports failed-then-succeeded keys and n_with_retries per Requirement 4.
    """
    rows = []
    # Gold corpus sizes for random baseline: min(k, m) / m
    corpus_m = {
        "DSA_gold_standard_MEKG": 28,         # 29 nodes total - 1 held out = 28 potential neighbours
        "metacademy_gold_standard_MEKG": 140,  # 141 nodes total - 1 held out = 140 potential neighbours
    }

    for r_dir in sorted(accuracy_run_dirs):
        summary_p = r_dir / "summary.csv"
        sidecar_p = r_dir / "strategy_config.json"
        raw_p = r_dir / "raw.jsonl"
        if not summary_p.exists():
            continue

        strat_cfg = parse_sidecar(sidecar_p) if sidecar_p.exists() else {}
        strat = strat_cfg.get("strategy", r_dir.name)
        variant = extract_variant_label(r_dir.name)

        # Parse raw.jsonl for failure tracking per corpus
        failed_then_succ_by_corpus: Dict[str, List[str]] = {}
        if raw_p.exists():
            records, is_resumed, _, key_records = parse_raw_jsonl(raw_p)
            for k, rec_list in key_records.items():
                corp = rec_list[-1].get("corpus", "")
                earlier_failed = any(x.get("status") in ("failed", "error") for x in rec_list[:-1])
                final_success = rec_list[-1].get("status") == "success"
                if earlier_failed and final_success:
                    failed_then_succ_by_corpus.setdefault(corp, []).append(k)

        # Effective shortlist size k for random baseline
        cfg = strat_cfg.get("config", {}) if isinstance(strat_cfg.get("config"), dict) else {}
        k_val = cfg.get("k", strat_cfg.get("k"))
        if k_val is None:
            k_val = cfg.get("s_max", strat_cfg.get("s_max"))

        summary_rows = parse_summary_csv(summary_p)
        for s in summary_rows:
            corpus = _require_col(s, "corpus_or_size", r_dir.name)
            m = corpus_m.get(corpus, 28)
            # Random baseline is blank/NaN where the strategy has no k or s_max cap
            rand_baseline = (min(k_val, m) / m) if k_val is not None else float("nan")

            fts_keys = failed_then_succ_by_corpus.get(corpus, [])
            # T1 n_with_retries comes only from summary.csv
            n_with_retries = int(_require_col(s, "n_with_retries", r_dir.name))

            row = {
                "strategy": strat,
                "variant": variant,
                "corpus": corpus,
                "num_trials": int(_require_col(s, "num_trials", r_dir.name)),
                "num_success": int(_require_col(s, "num_success", r_dir.name)),
                "failed_then_succeeded_count": len(fts_keys),
                "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
                "n_with_retries": n_with_retries,
                "llm_calls_mean": float(_require_col(s, "llm_calls_mean", r_dir.name)),
                "precision_micro": float(_require_col(s, "precision_micro", r_dir.name)),
                "recall_micro": float(_require_col(s, "recall_micro", r_dir.name)),
                "f1_micro": float(_require_col(s, "f1_micro", r_dir.name)),
                "precision_macro": float(_require_col(s, "precision_macro", r_dir.name)),
                "recall_macro": float(_require_col(s, "recall_macro", r_dir.name)),
                "f1_macro": float(_require_col(s, "f1_macro", r_dir.name)),
                "shortlist_recall_micro": float(_require_col(s, "shortlist_recall_micro", r_dir.name)),
                "shortlist_recall_macro": float(_require_col(s, "shortlist_recall_macro", r_dir.name)),
                "random_baseline_recall": rand_baseline,
            }
            rows.append(row)

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows


def generate_t4_sensitivity_table(
    accuracy_run_dirs: List[Path],
    output_csv_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Generate Table T4: Sensitivity-variant metrics and unjudged predictions."""
    rows = []
    for r_dir in sorted(accuracy_run_dirs):
        summary_p = r_dir / "summary.csv"
        sidecar_p = r_dir / "strategy_config.json"
        if not summary_p.exists():
            continue

        strat_cfg = parse_sidecar(sidecar_p) if sidecar_p.exists() else {}
        strat = strat_cfg.get("strategy", r_dir.name)
        variant = extract_variant_label(r_dir.name)

        summary_rows = parse_summary_csv(summary_p)
        for s in summary_rows:
            row = {
                "strategy": strat,
                "variant": variant,
                "corpus": _require_col(s, "corpus_or_size", r_dir.name),
                "precision_micro_sensitivity": float(_require_col(s, "precision_micro_sensitivity", r_dir.name)),
                "recall_micro_sensitivity": float(_require_col(s, "recall_micro_sensitivity", r_dir.name)),
                "f1_micro_sensitivity": float(_require_col(s, "f1_micro_sensitivity", r_dir.name)),
                "precision_macro_sensitivity": float(_require_col(s, "precision_macro_sensitivity", r_dir.name)),
                "recall_macro_sensitivity": float(_require_col(s, "recall_macro_sensitivity", r_dir.name)),
                "f1_macro_sensitivity": float(_require_col(s, "f1_macro_sensitivity", r_dir.name)),
                "unjudged_predictions_total": int(_require_col(s, "unjudged_predictions_total", r_dir.name)),
            }
            rows.append(row)

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows


def generate_t3_inventory_table(
    t3_csv_content_or_path: str | Path,
    output_csv_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Parse validator's Table T3 CSV verbatim and optionally write to output_csv_path."""
    if isinstance(t3_csv_content_or_path, Path):
        content = t3_csv_content_or_path.read_text(encoding="utf-8")
    else:
        content = str(t3_csv_content_or_path)

    reader = csv.DictReader(content.splitlines())
    rows = list(reader)

    if output_csv_path:
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)
        output_csv_path.write_text(content, encoding="utf-8")

    return rows


def _fit_metric_slopes(
    strat: str,
    variant: str,
    metric: str,
    condition: str,
    size_map: Dict[int, List[float]],
    slope_fit_rows: List[Dict[str, Any]],
) -> None:
    """Helper to compute log-log slope fit and bootstrap CI per Rule R1."""
    sizes = sorted(size_map.keys())
    min_trials = min((len(size_map[s]) for s in sizes), default=0)
    point_slope, ci_low, ci_high, cat, r2, n_boot = bootstrap_slope_ci(size_map)
    slope_fit_rows.append({
        "strategy": strat,
        "variant": variant,
        "metric": metric,
        "condition": condition,
        "slope": point_slope,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "r_squared": r2,
        "flatness_category_D2": cat,
        "min_trials_per_size": min_trials,
        "n_boot_used": n_boot,
    })

    # If undefined due to zero mean, but at least 3 sizes have positive mean, emit exploratory row per R1
    pos_sizes = {
        s: trials for s, trials in size_map.items()
        if len(trials) > 0 and np.mean(trials) > 0 and np.isfinite(np.mean(trials))
    }
    if (np.isnan(point_slope) or "undefined (zero mean" in cat) and len(pos_sizes) >= 3:
        p_min_trials = min(len(pos_sizes[s]) for s in pos_sizes)
        p_slope, p_low, p_high, p_cat, p_r2, p_n_boot = bootstrap_slope_ci(pos_sizes)
        slope_fit_rows.append({
            "strategy": strat,
            "variant": variant,
            "metric": metric,
            "condition": "exploratory (positive-mean sizes only)",
            "slope": p_slope,
            "ci_95_low": p_low,
            "ci_95_high": p_high,
            "r_squared": p_r2,
            "flatness_category_D2": p_cat,
            "min_trials_per_size": p_min_trials,
            "n_boot_used": p_n_boot,
        })


def generate_t2_sweep_cost_table(
    sweep_run_dirs: List[Path],
    output_csv_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate Table T2: Sweep cost metrics per (strategy, size).

    Includes:
    - calls, total_s, shortlist_s, decide_s distributions (mean, median, std, min, max, 95% bootstrap CIs)
    - failed-then-succeeded keys and n_with_retries
    - timing sensitivity columns that exclude trials with retries > 0 and the single trial
      sweep:brute_force:2000:t9, labelled "post-hoc, not pre-registered" (Requirement 4 / R3).
    - log-log OLS slope fits with 95% bootstrap CIs, min_trials_per_size, n_boot_used,
      and D2 flatness classifications (Requirement 3 / R1).

    Returns (t2_rows, slope_fit_rows).
    """
    rows = []
    slope_fit_rows: List[Dict[str, Any]] = []

    for r_dir in sorted(sweep_run_dirs):
        summary_p = r_dir / "summary.csv"
        sidecar_p = r_dir / "strategy_config.json"
        raw_p = r_dir / "raw.jsonl"
        if not summary_p.exists() or not raw_p.exists():
            continue

        strat_cfg = parse_sidecar(sidecar_p) if sidecar_p.exists() else {}
        strat = strat_cfg.get("strategy", r_dir.name)
        variant = extract_variant_label(r_dir.name)

        # Parse raw.jsonl
        records, is_resumed, _, key_records = parse_raw_jsonl(raw_p)

        # Deduplicate records by trial key, keeping latest record per key
        records_by_key: Dict[str, Dict[str, Any]] = {}
        for r in records:
            k = _require_col(r, "key", r_dir.name)
            records_by_key[k] = r
        deduped = list(records_by_key.values())

        # Group by size
        by_size: Dict[int, List[Dict[str, Any]]] = {}
        for r in deduped:
            if "size" in r:
                s_val = int(r["size"])
            elif "metrics" in r and "n_before" in r["metrics"]:
                s_val = int(r["metrics"]["n_before"])
            else:
                raise KeyError(f"Run '{r_dir.name}' missing required size field in trial record")
            by_size.setdefault(s_val, []).append(r)

        # Track per-size arrays for slope fitting
        size_calls_map: Dict[int, List[float]] = {}
        size_total_s_map: Dict[int, List[float]] = {}
        size_total_s_clean_map: Dict[int, List[float]] = {}

        for size_n in sorted(by_size.keys()):
            size_records = by_size[size_n]
            successes = [r for r in size_records if _require_col(r, "status", r_dir.name) == "success"]

            # Failure and retry tracking
            fts_keys = []
            for r in successes:
                k = _require_col(r, "key", r_dir.name)
                rec_hist = key_records.get(k, [])
                if any(x.get("status") in ("failed", "error") for x in rec_hist[:-1]):
                    fts_keys.append(k)

            n_with_retries = sum(1 for r in successes if int(_require_col(r, "retries", r_dir.name)) > 0)
            total_retries = sum(int(_require_col(r, "retries", r_dir.name)) for r in successes)

            # Metric series across all pre-registered successful trials
            calls_list = []
            tot_s_list = []
            short_s_list = []
            dec_s_list = []
            for r in successes:
                metrics = _require_col(r, "metrics", r_dir.name)
                calls_list.append(float(_require_col(metrics, "llm_calls", r_dir.name)))
                tot_s_list.append(float(_require_col(metrics, "total_s", r_dir.name)))
                short_s_list.append(float(_require_col(metrics, "shortlist_s", r_dir.name)))
                dec_s_list.append(float(_require_col(metrics, "decide_s", r_dir.name)))

            size_calls_map[size_n] = calls_list
            size_total_s_map[size_n] = tot_s_list

            calls_stats = compute_series_stats(calls_list)
            tot_stats = compute_series_stats(tot_s_list)
            short_stats = compute_series_stats(short_s_list)
            dec_stats = compute_series_stats(dec_s_list)

            # Post-hoc timing sensitivity per Rule R3: exclude retries > 0 and sweep:brute_force:2000:t9
            clean_successes = [
                r for r in successes
                if int(_require_col(r, "retries", r_dir.name)) == 0
                and _require_col(r, "key", r_dir.name) != "sweep:brute_force:2000:t9"
            ]
            clean_tot_s_list = [float(_require_col(r["metrics"], "total_s", r_dir.name)) for r in clean_successes]
            clean_short_s_list = [float(_require_col(r["metrics"], "shortlist_s", r_dir.name)) for r in clean_successes]
            clean_dec_s_list = [float(_require_col(r["metrics"], "decide_s", r_dir.name)) for r in clean_successes]

            size_total_s_clean_map[size_n] = clean_tot_s_list
            clean_tot_stats = compute_series_stats(clean_tot_s_list)
            clean_short_stats = compute_series_stats(clean_short_s_list)
            clean_dec_stats = compute_series_stats(clean_dec_s_list)

            row = {
                "strategy": strat,
                "variant": variant,
                "size_n": size_n,
                "num_trials": len(size_records),
                "num_success": len(successes),
                "failed_then_succeeded_count": len(fts_keys),
                "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
                "n_with_retries": n_with_retries,
                "total_retries": total_retries,
                # Pre-registered calls
                "llm_calls_mean": calls_stats["mean"],
                "llm_calls_median": calls_stats["median"],
                "llm_calls_std": calls_stats["std"],
                "llm_calls_min": calls_stats["min"],
                "llm_calls_max": calls_stats["max"],
                "llm_calls_ci_mean_low": calls_stats["ci_mean_low"],
                "llm_calls_ci_mean_high": calls_stats["ci_mean_high"],
                # Pre-registered total_s
                "total_s_mean": tot_stats["mean"],
                "total_s_median": tot_stats["median"],
                "total_s_std": tot_stats["std"],
                "total_s_min": tot_stats["min"],
                "total_s_max": tot_stats["max"],
                "total_s_ci_mean_low": tot_stats["ci_mean_low"],
                "total_s_ci_mean_high": tot_stats["ci_mean_high"],
                # Pre-registered components: shortlist_s and decide_s with 95% bootstrap CIs
                "shortlist_s_mean": short_stats["mean"],
                "shortlist_s_median": short_stats["median"],
                "shortlist_s_std": short_stats["std"],
                "shortlist_s_min": short_stats["min"],
                "shortlist_s_max": short_stats["max"],
                "shortlist_s_ci_mean_low": short_stats["ci_mean_low"],
                "shortlist_s_ci_mean_high": short_stats["ci_mean_high"],
                "decide_s_mean": dec_stats["mean"],
                "decide_s_median": dec_stats["median"],
                "decide_s_std": dec_stats["std"],
                "decide_s_min": dec_stats["min"],
                "decide_s_max": dec_stats["max"],
                "decide_s_ci_mean_low": dec_stats["ci_mean_low"],
                "decide_s_ci_mean_high": dec_stats["ci_mean_high"],
                # Post-hoc sensitivity timing (labelled "post-hoc, not pre-registered") per Rule R3
                "clean_exclusion_rule": "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)",
                "clean_num_trials_post_hoc_not_preregistered": len(clean_successes),
                "clean_total_s_mean_post_hoc_not_preregistered": clean_tot_stats["mean"],
                "clean_total_s_median_post_hoc_not_preregistered": clean_tot_stats["median"],
                "clean_total_s_std_post_hoc_not_preregistered": clean_tot_stats["std"],
                "clean_total_s_min_post_hoc_not_preregistered": clean_tot_stats["min"],
                "clean_total_s_max_post_hoc_not_preregistered": clean_tot_stats["max"],
                "clean_shortlist_s_mean_post_hoc_not_preregistered": clean_short_stats["mean"],
                "clean_decide_s_mean_post_hoc_not_preregistered": clean_dec_stats["mean"],
            }
            rows.append(row)

        # Compute log-log OLS slope fits across sizes for this run per Rule R1
        if len(size_calls_map) >= 2:
            # 1. LLM calls slope fit
            _fit_metric_slopes(
                strat, variant, "llm_calls", "pre-registered (all trials)", size_calls_map, slope_fit_rows
            )
            # 2. total_s slope fit (pre-registered)
            _fit_metric_slopes(
                strat, variant, "total_s", "pre-registered (all trials)", size_total_s_map, slope_fit_rows
            )
            # 3. total_s clean slope fit (post-hoc)
            _fit_metric_slopes(
                strat, variant, "total_s", "clean (post-hoc, not pre-registered)", size_total_s_clean_map, slope_fit_rows
            )

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows, slope_fit_rows

