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
        compute_directory_sha256,
        parse_manifest,
        parse_sidecar,
        parse_summary_csv,
        parse_raw_jsonl,
        validate_single_run,
    )
    from .bootstrap import compute_series_stats
    from .stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness
except ImportError:
    from validate_runs import (
        compute_directory_sha256,
        parse_manifest,
        parse_sidecar,
        parse_summary_csv,
        parse_raw_jsonl,
        validate_single_run,
    )
    from bootstrap import compute_series_stats
    from stats import bootstrap_slope_ci, fit_log_log_slope, classify_slope_flatness


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


def write_csv(output_path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write rows to a CSV file with deterministic column order."""
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen_keys: Dict[str, None] = {}
    for r in rows:
        for k in r.keys():
            seen_keys[k] = None
    fieldnames = list(seen_keys.keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_markdown_table(rows: List[Dict[str, Any]], output_md_path: Path, title: str) -> None:
    """Write table rows as a GitHub-flavored markdown table."""
    if not rows:
        return
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
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

        # Parse raw.jsonl for failure / retry inspection per corpus
        failed_then_succ_by_corpus: Dict[str, List[str]] = {}
        retries_by_corpus: Dict[str, int] = {}
        n_with_retries_by_corpus: Dict[str, int] = {}

        if raw_p.exists():
            records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_p)
            for k, rec_list in key_records.items():
                corp = rec_list[-1].get("corpus", "")
                earlier_failed = any(x.get("status") in ("failed", "error") for x in rec_list[:-1])
                final_success = rec_list[-1].get("status") == "success"
                if earlier_failed and final_success:
                    failed_then_succ_by_corpus.setdefault(corp, []).append(k)

                r_cnt = retry_counts.get(k, 0)
                if r_cnt > 0 and final_success:
                    retries_by_corpus[corp] = retries_by_corpus.get(corp, 0) + r_cnt
                    n_with_retries_by_corpus[corp] = n_with_retries_by_corpus.get(corp, 0) + 1

        # Effective shortlist size k for random baseline
        cfg = strat_cfg.get("config", {}) if isinstance(strat_cfg.get("config"), dict) else {}
        k_val = cfg.get("k", strat_cfg.get("k"))
        if k_val is None:
            k_val = cfg.get("s_max", strat_cfg.get("s_max"))

        summary_rows = parse_summary_csv(summary_p)
        for s in summary_rows:
            corpus = s.get("corpus_or_size", "")
            m = corpus_m.get(corpus, 28)
            rand_baseline = (min(k_val, m) / m) if k_val is not None else 1.0

            fts_keys = failed_then_succ_by_corpus.get(corpus, [])
            n_with_retries = int(s.get("n_with_retries", n_with_retries_by_corpus.get(corpus, 0)))

            row = {
                "strategy": strat,
                "variant": variant,
                "corpus": corpus,
                "num_trials": int(s.get("num_trials", 0)),
                "num_success": int(s.get("num_success", 0)),
                "failed_then_succeeded_count": len(fts_keys),
                "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
                "n_with_retries": n_with_retries,
                "llm_calls_mean": float(s.get("llm_calls_mean", 0.0)),
                "precision_micro": float(s.get("precision_micro", 0.0)),
                "recall_micro": float(s.get("recall_micro", 0.0)),
                "f1_micro": float(s.get("f1_micro", 0.0)),
                "precision_macro": float(s.get("precision_macro", 0.0)),
                "recall_macro": float(s.get("recall_macro", 0.0)),
                "f1_macro": float(s.get("f1_macro", 0.0)),
                "shortlist_recall_micro": float(s.get("shortlist_recall_micro", 0.0)),
                "shortlist_recall_macro": float(s.get("shortlist_recall_macro", 0.0)),
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
                "corpus": s.get("corpus_or_size", ""),
                "precision_micro_sensitivity": float(s.get("precision_micro_sensitivity", 0.0)),
                "recall_micro_sensitivity": float(s.get("recall_micro_sensitivity", 0.0)),
                "f1_micro_sensitivity": float(s.get("f1_micro_sensitivity", 0.0)),
                "precision_macro_sensitivity": float(s.get("precision_macro_sensitivity", 0.0)),
                "recall_macro_sensitivity": float(s.get("recall_macro_sensitivity", 0.0)),
                "f1_macro_sensitivity": float(s.get("f1_macro_sensitivity", 0.0)),
                "unjudged_predictions_total": int(s.get("unjudged_predictions_total", 0)),
            }
            rows.append(row)

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows


def generate_t3_inventory_table(
    all_run_dirs: List[Path],
    output_csv_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Generate Table T3: Run inventory for reproducibility and provenance."""
    rows = []
    for r_dir in sorted(all_run_dirs):
        manifest_p = r_dir / "manifest.json"
        if not manifest_p.exists():
            continue

        passed, errors, info = validate_single_run(r_dir)
        manifest = parse_manifest(manifest_p)

        fts_keys = info.get("failed_then_succeeded_keys", [])
        still_failed_keys = info.get("still_failed_keys", [])

        row = {
            "run_dir": r_dir.name,
            "strategy": info.get("strategy", ""),
            "mode": info.get("mode", ""),
            "variant": extract_variant_label(r_dir.name),
            "git_commit": str(info.get("git_commit", ""))[:7],
            "git_dirty": info.get("git_dirty", ""),
            "total_trials": info.get("total_trials", 0),
            "total_calls": info.get("total_calls", 0),
            "call_bound": info.get("call_bound", ""),
            "failed_trials": info.get("failed_trials", 0),
            "failed_then_succeeded_count": len(fts_keys),
            "failed_then_succeeded_keys": "; ".join(fts_keys) if fts_keys else "none",
            "still_failed_count": len(still_failed_keys),
            "retries": info.get("total_retries", 0),
            "gate_status": "PASS (resumed)" if (passed and info.get("resumed")) else ("PASS" if passed else "FAIL"),
            "dir_sha256": info.get("dir_sha256", ""),
        }
        rows.append(row)

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows


def generate_t2_sweep_cost_table(
    sweep_run_dirs: List[Path],
    output_csv_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate Table T2: Sweep cost metrics per (strategy, size).

    Includes:
    - calls, total_s, shortlist_s, decide_s distributions (mean, median, std, min, max, 95% bootstrap CIs)
    - failed-then-succeeded keys and n_with_retries
    - timing sensitivity columns that exclude trials with retries > 0 and the single trial
      sweep:brute_force:2000:t9, labelled "post-hoc, not pre-registered" (Requirement 4).
    - log-log OLS slope fits with 95% bootstrap CIs and D2 flatness classifications (Requirement 3).

    Returns (t2_rows, slope_fit_rows).
    """
    rows = []
    slope_fit_rows = []

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
        records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_p)

        # Deduplicate records by trial key, keeping latest record per key
        records_by_key: Dict[str, Dict[str, Any]] = {}
        for r in records:
            k = r.get("key")
            if k:
                records_by_key[k] = r
        deduped = list(records_by_key.values())

        # Group by size
        by_size: Dict[int, List[Dict[str, Any]]] = {}
        for r in deduped:
            s_val = int(r.get("size", r.get("metrics", {}).get("n_before", 0)))
            by_size.setdefault(s_val, []).append(r)

        # Track per-size arrays for slope fitting
        size_calls_map: Dict[int, List[float]] = {}
        size_total_s_map: Dict[int, List[float]] = {}
        size_total_s_clean_map: Dict[int, List[float]] = {}

        for size_n in sorted(by_size.keys()):
            size_records = by_size[size_n]
            successes = [r for r in size_records if r.get("status") == "success"]

            # Failure and retry tracking
            fts_keys = []
            for r in successes:
                k = r.get("key", "")
                rec_hist = key_records.get(k, [])
                if any(x.get("status") in ("failed", "error") for x in rec_hist[:-1]):
                    fts_keys.append(k)

            n_with_retries = sum(1 for r in successes if r.get("retries", 0) > 0)
            total_retries = sum(r.get("retries", 0) for r in successes)

            # Metric series across all pre-registered successful trials
            calls_list = [float(r.get("metrics", {}).get("llm_calls", 0.0)) for r in successes]
            tot_s_list = [float(r.get("metrics", {}).get("total_s", 0.0)) for r in successes]
            short_s_list = [float(r.get("metrics", {}).get("shortlist_s", 0.0)) for r in successes]
            dec_s_list = [float(r.get("metrics", {}).get("decide_s", 0.0)) for r in successes]

            size_calls_map[size_n] = calls_list
            size_total_s_map[size_n] = tot_s_list

            calls_stats = compute_series_stats(calls_list)
            tot_stats = compute_series_stats(tot_s_list)
            short_stats = compute_series_stats(short_s_list)
            dec_stats = compute_series_stats(dec_s_list)

            # Post-hoc timing sensitivity: exclude trials with retries > 0 and sweep:brute_force:2000:t9
            clean_successes = [
                r for r in successes
                if r.get("retries", 0) == 0 and r.get("key") != "sweep:brute_force:2000:t9"
            ]
            clean_tot_s_list = [float(r.get("metrics", {}).get("total_s", 0.0)) for r in clean_successes]
            clean_short_s_list = [float(r.get("metrics", {}).get("shortlist_s", 0.0)) for r in clean_successes]
            clean_dec_s_list = [float(r.get("metrics", {}).get("decide_s", 0.0)) for r in clean_successes]

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
                # Pre-registered components: shortlist_s and decide_s
                "shortlist_s_mean": short_stats["mean"],
                "shortlist_s_median": short_stats["median"],
                "shortlist_s_std": short_stats["std"],
                "shortlist_s_min": short_stats["min"],
                "shortlist_s_max": short_stats["max"],
                "decide_s_mean": dec_stats["mean"],
                "decide_s_median": dec_stats["median"],
                "decide_s_std": dec_stats["std"],
                "decide_s_min": dec_stats["min"],
                "decide_s_max": dec_stats["max"],
                # Post-hoc sensitivity timing (labelled "post-hoc, not pre-registered")
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

        # Compute log-log OLS slope fits across the 6 sizes for this run
        if len(size_calls_map) >= 2:
            # 1. LLM calls slope fit
            calls_slope, calls_ci_low, calls_ci_high, calls_cat, calls_r2 = bootstrap_slope_ci(size_calls_map)
            # 2. total_s slope fit (pre-registered)
            tot_slope, tot_ci_low, tot_ci_high, tot_cat, tot_r2 = bootstrap_slope_ci(size_total_s_map)
            # 3. total_s clean slope fit (post-hoc)
            tot_clean_slope, tot_clean_ci_low, tot_clean_ci_high, tot_clean_cat, tot_clean_r2 = bootstrap_slope_ci(
                size_total_s_clean_map
            )

            slope_fit_rows.append({
                "strategy": strat,
                "variant": variant,
                "metric": "llm_calls",
                "condition": "pre-registered (all trials)",
                "slope": calls_slope,
                "ci_95_low": calls_ci_low,
                "ci_95_high": calls_ci_high,
                "r_squared": calls_r2,
                "flatness_category_D2": calls_cat,
            })
            slope_fit_rows.append({
                "strategy": strat,
                "variant": variant,
                "metric": "total_s",
                "condition": "pre-registered (all trials)",
                "slope": tot_slope,
                "ci_95_low": tot_ci_low,
                "ci_95_high": tot_ci_high,
                "r_squared": tot_r2,
                "flatness_category_D2": tot_cat,
            })
            slope_fit_rows.append({
                "strategy": strat,
                "variant": variant,
                "metric": "total_s",
                "condition": "clean (post-hoc, not pre-registered)",
                "slope": tot_clean_slope,
                "ci_95_low": tot_clean_ci_low,
                "ci_95_high": tot_clean_ci_high,
                "r_squared": tot_clean_r2,
                "flatness_category_D2": tot_clean_cat,
            })

    if output_csv_path and rows:
        write_csv(output_csv_path, rows)

    return rows, slope_fit_rows
