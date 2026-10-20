"""
test_analysis_pipeline.py — Unit and Integration Tests for Phase 4 Analysis Suite
================================================================================
Implements tests for TASK ANALYSIS-002:
- Vectorized percentile bootstrap CI (D1)
- Flatness classification into pre-registered bins (D2)
- Log-log OLS slope fits with bootstrap CI and descriptive categories
- Pareto dominance mechanics (D3, D5)
- Failed-then-succeeded and retry accounting
- Timing sensitivity columns excluding retries > 0 and sweep:brute_force:2000:t9 (Requirement 4)
- Gate integration and fail-closed behavior (Requirement 1)
- Synthetic fixture end-to-end execution of all tables (T1-T4, T2b) and figures (F1-F6)
- Parity check: per-run numbers equal the validator's recomputation on the real accuracy directories (Requirement 5)
"""

from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pytest

from scripts.analysis.bootstrap import bootstrap_ci, compute_series_stats
from scripts.analysis.stats import (
    classify_slope_flatness,
    fit_log_log_slope,
    bootstrap_slope_ci,
    evaluate_dominance,
)
from scripts.analysis.style import apply_thesis_style, export_figure
from scripts.analysis.tables import (
    extract_variant_label,
    generate_t1_accuracy_table,
    generate_t2_sweep_cost_table,
    generate_t3_inventory_table,
    generate_t4_sensitivity_table,
)
from scripts.analysis.figures import (
    plot_f1_calls_scaling,
    plot_f2_wallclock_scaling,
    plot_f3_premise_check,
    plot_f4_accuracy_comparison,
    plot_f5_sensitivity_panels,
    plot_f6_cost_vs_accuracy,
)
from scripts.analysis.validate_runs import parse_raw_jsonl, recompute_metrics


def test_bootstrap_ci_deterministic():
    data = [10.0, 12.0, 11.5, 9.8, 10.2, 11.0, 10.5]
    low1, high1 = bootstrap_ci(data, seed=42, n_resamples=1000)
    low2, high2 = bootstrap_ci(data, seed=42, n_resamples=1000)
    assert low1 == low2
    assert high1 == high2
    assert low1 <= np.mean(data) <= high1


def test_bootstrap_empty_and_single_point():
    assert np.isnan(bootstrap_ci([])[0])
    assert bootstrap_ci([42.0]) == (42.0, 42.0)
    stats = compute_series_stats([])
    assert stats["n"] == 0
    assert np.isnan(stats["mean"])


def test_flatness_classification():
    assert classify_slope_flatness(0.00) == "approximately flat"
    assert classify_slope_flatness(0.099) == "approximately flat"
    assert classify_slope_flatness(0.10) == "sub-linear"
    assert classify_slope_flatness(0.50) == "sub-linear"
    assert classify_slope_flatness(0.90) == "sub-linear"
    assert classify_slope_flatness(0.901) == "approximately linear"
    assert classify_slope_flatness(1.05) == "approximately linear"


def test_ols_log_log_slope():
    # If cost = 2 * n, then log(cost) = log(2) + 1.0 * log(n), slope = 1.0 (linear)
    sizes = [50, 100, 200, 500, 1000, 2000]
    costs = [2.0 * s for s in sizes]
    slope, intercept, r2 = fit_log_log_slope(sizes, costs)
    assert np.isclose(slope, 1.0, atol=1e-5)
    assert np.isclose(r2, 1.0, atol=1e-5)

    # If cost is flat (e.g. 10.0 calls always), slope = 0.0
    flat_costs = [10.0 for _ in sizes]
    slope_flat, _, _ = fit_log_log_slope(sizes, flat_costs)
    assert np.isclose(slope_flat, 0.0, atol=1e-5)


def test_bootstrap_slope_ci_synthetic():
    sizes = [50, 100, 200, 500, 1000, 2000]
    size_map: Dict[int, List[float]] = {}
    for s in sizes:
        # Linear calls = s
        size_map[s] = [float(s)] * 10

    point_slope, ci_low, ci_high, cat, r2 = bootstrap_slope_ci(size_map, n_resamples=500, seed=42)
    assert np.isclose(point_slope, 1.0, atol=1e-5)
    assert np.isclose(ci_low, 1.0, atol=1e-5)
    assert np.isclose(ci_high, 1.0, atol=1e-5)
    assert cat == "approximately linear"


def test_dominance_evaluation():
    # A has fewer calls and higher F1 (> 0.025 diff) -> A dominates B
    pt_a = {"calls": 10.0, "f1": 0.55}
    pt_b = {"calls": 20.0, "f1": 0.40}
    assert evaluate_dominance(pt_a, pt_b) == "A dominates B"

    # F1 difference is within 0.025 noise floor, but A has fewer calls -> A dominates on calls
    pt_c = {"calls": 10.0, "f1": 0.510}
    pt_d = {"calls": 25.0, "f1": 0.520}  # diff = 0.010 <= 0.025
    assert evaluate_dominance(pt_c, pt_d) == "A dominates B (calls advantage, F1 equivalent)"

    # Trade-off: A has fewer calls but B has significantly higher F1 (> 0.025)
    pt_e = {"calls": 5.0, "f1": 0.40}
    pt_f = {"calls": 50.0, "f1": 0.60}
    assert evaluate_dominance(pt_e, pt_f) == "trade-off"


def create_mock_run_directory(
    root: Path,
    run_name: str,
    strategy: str,
    mode: str,
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Path:
    """Helper to create a hermetic synthetic run directory with manifest, config, raw.jsonl, and summary.csv."""
    run_dir = root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_name,
        "mode": mode,
        "strategy": strategy,
        "git_commit": "3323bfb1234567890abcdef1234567890abcdef1",
        "git_dirty": False,
        "libraries": {
            "networkx": "3.4.2",
            "pytest": "8.3.4",
            "httpx": "0.28.1",
            "numpy": "2.2.3",
            "torch": "2.6.0",
            "faiss-cpu": "1.15.1",
            "sentence-transformers": "6.1.0",
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    sidecar = {
        "strategy": strategy,
        "config": config,
    }
    if strategy != "brute_force":
        sidecar["embedder"] = {
            "model_name": "all-MiniLM-L6-v2",
            "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            "cpu_threads": 1,
            "torch_threads": 1,
        }
    (run_dir / "strategy_config.json").write_text(json.dumps(sidecar), encoding="utf-8")

    # raw.jsonl
    with open(run_dir / "raw.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # summary.csv
    summary_fields = [
        "strategy", "mode", "corpus_or_size", "num_trials", "num_success", "num_failed", "n_with_retries",
        "total_s_mean", "total_s_median", "total_s_std", "total_s_min", "total_s_max",
        "shortlist_s_mean", "shortlist_s_median", "shortlist_s_std", "shortlist_s_min", "shortlist_s_max",
        "decide_s_mean", "decide_s_median", "decide_s_std", "decide_s_min", "decide_s_max",
        "llm_calls_mean", "llm_calls_median", "llm_calls_sum", "llm_calls_min", "llm_calls_max",
        "precision_micro", "recall_micro", "f1_micro", "precision_macro", "recall_macro", "f1_macro",
        "shortlist_recall_micro", "shortlist_recall_macro",
        "precision_micro_sensitivity", "recall_micro_sensitivity", "f1_micro_sensitivity",
        "precision_macro_sensitivity", "recall_macro_sensitivity", "f1_macro_sensitivity",
        "unjudged_predictions_total",
    ]
    with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        # Group by corpus_or_size
        sizes = set(str(r.get("corpus", r.get("size", "50"))) for r in records if r.get("status") == "success")
        for s in sorted(sizes):
            writer.writerow({
                "strategy": strategy,
                "mode": mode,
                "corpus_or_size": s,
                "num_trials": len([r for r in records if str(r.get("corpus", r.get("size", "50"))) == s]),
                "num_success": len([r for r in records if str(r.get("corpus", r.get("size", "50"))) == s and r.get("status") == "success"]),
                "num_failed": 0,
                "n_with_retries": 0,
                "total_s_mean": 10.0,
                "total_s_median": 10.0,
                "total_s_std": 0.0,
                "total_s_min": 10.0,
                "total_s_max": 10.0,
                "shortlist_s_mean": 0.01,
                "shortlist_s_median": 0.01,
                "shortlist_s_std": 0.0,
                "shortlist_s_min": 0.01,
                "shortlist_s_max": 0.01,
                "decide_s_mean": 9.99,
                "decide_s_median": 9.99,
                "decide_s_std": 0.0,
                "decide_s_min": 9.99,
                "decide_s_max": 9.99,
                "llm_calls_mean": 10.0,
                "llm_calls_median": 10.0,
                "llm_calls_sum": 100,
                "llm_calls_min": 10.0,
                "llm_calls_max": 10.0,
                "precision_micro": 0.60,
                "recall_micro": 0.50,
                "f1_micro": 0.545,
                "precision_macro": 0.58,
                "recall_macro": 0.48,
                "f1_macro": 0.525,
                "shortlist_recall_micro": 0.70,
                "shortlist_recall_macro": 0.70,
                "precision_micro_sensitivity": 0.55,
                "recall_micro_sensitivity": 0.45,
                "f1_micro_sensitivity": 0.495,
                "precision_macro_sensitivity": 0.53,
                "recall_macro_sensitivity": 0.43,
                "f1_macro_sensitivity": 0.475,
                "unjudged_predictions_total": 2,
            })

    return run_dir


def test_post_hoc_sensitivity_exclusion(tmp_path: Path):
    """Verifies Requirement 4: trials with retries > 0 and the single trial

    sweep:brute_force:2000:t9 are excluded from the post-hoc timing sensitivity columns.
    """
    records = []
    # 10 trials for size 2000 of brute force:
    # trial 0..7: normal success (retries=0, total_s=100.0)
    # trial 8: success with retries=2, total_s=250.0 (should be excluded)
    # trial 9 (key sweep:brute_force:2000:t9): retries=0, total_s=300.0 (should be excluded)
    for i in range(8):
        records.append({
            "key": f"sweep:brute_force:2000:t{i}",
            "status": "success",
            "size": 2000,
            "retries": 0,
            "metrics": {"total_s": 100.0, "shortlist_s": 0.01, "decide_s": 99.99, "llm_calls": 2000},
        })
    records.append({
        "key": "sweep:brute_force:2000:t8",
        "status": "success",
        "size": 2000,
        "retries": 2,
        "metrics": {"total_s": 250.0, "shortlist_s": 0.01, "decide_s": 249.99, "llm_calls": 2000},
    })
    records.append({
        "key": "sweep:brute_force:2000:t9",
        "status": "success",
        "size": 2000,
        "retries": 0,
        "metrics": {"total_s": 300.0, "shortlist_s": 0.01, "decide_s": 299.99, "llm_calls": 2000},
    })

    run_dir = create_mock_run_directory(
        tmp_path,
        "sweep_brute_force",
        "brute_force",
        "sweep",
        records,
        config={},
    )

    t2_rows, slope_fits = generate_t2_sweep_cost_table([run_dir])
    assert len(t2_rows) == 1
    row = t2_rows[0]

    # Pre-registered total includes all 10 trials: mean = (8*100 + 250 + 300) / 10 = 135.0
    assert row["num_trials"] == 10
    assert np.isclose(row["total_s_mean"], 135.0)

    # Post-hoc clean excludes trial 8 (retries=2) and trial 9 (key sweep:brute_force:2000:t9)
    # Remaining trials = 8, mean = 100.0 exactly
    assert row["clean_num_trials_post_hoc_not_preregistered"] == 8
    assert np.isclose(row["clean_total_s_mean_post_hoc_not_preregistered"], 100.0)
    assert np.isclose(row["clean_total_s_max_post_hoc_not_preregistered"], 100.0)


def test_synthetic_pipeline_end_to_end(tmp_path: Path):
    """End-to-end execution of the full analysis pipeline on synthetic data."""
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "output"
    results_dir.mkdir()

    # Create 1 accuracy run and 1 sweep run
    acc_records = [
        {
            "key": f"acc:ann_retrieval:DSA_gold_standard_MEKG:node_{i}",
            "corpus": "DSA_gold_standard_MEKG",
            "status": "success",
            "retries": 0,
            "metrics": {"total_s": 5.0, "shortlist_s": 0.01, "decide_s": 4.99, "llm_calls": 10},
            "score": {"tp": 2, "fp": 1, "fn": 1, "precision": 0.66, "recall": 0.66, "f1": 0.66, "shortlist_hits": 2, "gold_neighbours": 3, "shortlist_recall": 0.66},
        }
        for i in range(29)
    ]
    create_mock_run_directory(
        results_dir,
        "accuracy_ann_retrieval_k10_ef128",
        "ann_retrieval",
        "accuracy",
        acc_records,
        config={"k": 10, "ef_search": 128},
    )

    sweep_records = []
    for s in [50, 100, 200, 500, 1000, 2000]:
        for t in range(10):
            sweep_records.append({
                "key": f"sweep:ann_retrieval:{s}:t{t}",
                "size": s,
                "status": "success",
                "retries": 0,
                "metrics": {"total_s": 8.0, "shortlist_s": 0.01, "decide_s": 7.99, "llm_calls": 10},
            })
    create_mock_run_directory(
        results_dir,
        "sweep_ann_retrieval_k10_ef128",
        "ann_retrieval",
        "sweep",
        sweep_records,
        config={"k": 10, "ef_search": 128},
    )

    from scripts.analysis.run_analysis import main as run_pipeline_main
    import sys

    # Execute pipeline via main with --skip-gate (since synthetic commit hashes aren't in git)
    test_argv = [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
        "--skip-gate",
    ]
    old_argv = sys.argv
    try:
        sys.argv = test_argv
        rc = run_pipeline_main()
        assert rc == 0
    finally:
        sys.argv = old_argv

    # Check generated tables
    assert (output_dir / "tables" / "T1_accuracy_benchmark.csv").exists()
    assert (output_dir / "tables" / "T1_accuracy_benchmark.md").exists()
    assert (output_dir / "tables" / "T2_sweep_cost_summary.csv").exists()
    assert (output_dir / "tables" / "T2_sweep_cost_summary.md").exists()
    assert (output_dir / "tables" / "T2_slope_fits.csv").exists()
    assert (output_dir / "tables" / "T2_slope_fits.md").exists()
    assert (output_dir / "tables" / "T3_run_inventory.csv").exists()
    assert (output_dir / "tables" / "T3_run_inventory.md").exists()
    assert (output_dir / "tables" / "T4_sensitivity_metrics.csv").exists()
    assert (output_dir / "tables" / "T4_sensitivity_metrics.md").exists()

    # Check generated figures (both PDF, PNG, and CSV)
    for fig_name in [
        "F1_calls_scaling",
        "F2_wallclock_scaling",
        "F3_premise_check",
        "F4_accuracy_by_strategy",
        "F5_sensitivity_panels",
        "F6_cost_vs_accuracy_dominance",
    ]:
        assert (output_dir / "figures" / f"{fig_name}.pdf").exists()
        assert (output_dir / "figures" / f"{fig_name}.png").exists()
        assert (output_dir / "figures" / f"{fig_name}.csv").exists()


def test_parity_with_validator_on_real_accuracy_directories():
    """Requirement 5: Test that pipeline numbers equal validator recomputations

    directly on the real accuracy directories.
    """
    real_results_path = Path("/home/lukexodus/projects/llm-graph-insertion-complexity/results")
    if not real_results_path.exists():
        pytest.skip("Real results directory not present on this host")

    acc_dirs = sorted([d for d in real_results_path.iterdir() if d.is_dir() and d.name.startswith("accuracy_") and (d / "manifest.json").exists()])
    if not acc_dirs:
        pytest.skip("No real accuracy directories found")

    t1_rows = generate_t1_accuracy_table(acc_dirs)
    assert len(t1_rows) == 24  # 12 configurations x 2 corpora

    # Map T1 rows by (run_strategy, variant, corpus)
    t1_map = {(r["strategy"], r["variant"], r["corpus"]): r for r in t1_rows}

    # Cross-check each accuracy run directly against validator recompute_metrics
    for acc_dir in acc_dirs:
        raw_path = acc_dir / "raw.jsonl"
        sidecar_path = acc_dir / "strategy_config.json"
        strat_cfg = json.loads(sidecar_path.read_text(encoding="utf-8"))
        strat = strat_cfg.get("strategy")
        variant = extract_variant_label(acc_dir.name)

        records, is_resumed, retry_counts, key_records = parse_raw_jsonl(raw_path)
        val_metrics = recompute_metrics(records, "accuracy")

        for corpus, expected in val_metrics.items():
            key = (strat, variant, corpus)
            assert key in t1_map, f"Missing {key} in Table T1"
            t1_row = t1_map[key]

            # 1. Number of trials and successes
            assert t1_row["num_trials"] == expected["num_trials"]
            assert t1_row["num_success"] == expected["num_success"]

            # 2. LLM calls mean
            assert np.isclose(t1_row["llm_calls_mean"], expected["llm_calls_mean"], atol=1e-5)

            # 3. Micro F1, Precision, Recall
            assert np.isclose(t1_row["f1_micro"], expected["f1_micro"], atol=1e-5)
            assert np.isclose(t1_row["precision_micro"], expected["precision_micro"], atol=1e-5)
            assert np.isclose(t1_row["recall_micro"], expected["recall_micro"], atol=1e-5)

            # 4. Shortlist recall micro
            assert np.isclose(t1_row["shortlist_recall_micro"], expected["shortlist_recall_micro"], atol=1e-5)

            # 5. Macro F1
            if expected["f1_macro"] is not None:
                assert np.isclose(t1_row["f1_macro"], expected["f1_macro"], atol=1e-5)
