"""
test_analysis_pipeline.py — Unit and Integration Tests for Phase 4 Analysis Suite
================================================================================
Implements tests for TASK ANALYSIS-002-F:
- Vectorized percentile bootstrap CI (D1)
- Flatness classification into pre-registered bins (D2)
- Log-log OLS slope fits with R1 zero-mean rule (NaN slope, undefined category, dropping resamples)
- Pareto dominance mechanics per Rule R2 (< 0.025 indistinguishable; >= 0.025 dominance / trade-off)
- Post-hoc timing sensitivity exclusion per Rule R3 (retries>0 and t9 peak trial excluded)
- Gate integration: fail-closed on failure (exit 1, write nothing) and success without skip-gate
- Table T3 header matching 18 validator fieldnames and trial count on 60-trial fixture
- Strict accessor raising KeyError naming run and column
- Source grep test verifying absence of "skip-gate", "/home/", and "1e-12" in scripts/analysis/*.py
- Parity test with validator taking path from PHASE4_RESULTS_DIR (skipping if unset)
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import matplotlib.pyplot as plt
import matplotlib.text as mtext
from matplotlib.backends.backend_agg import FigureCanvasAgg
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
    _require_col,
    _fit_metric_slopes,
)
from scripts.analysis.figures import (
    plot_f1_calls_scaling,
    plot_f1b_calls_scaling_logy,
    plot_f2_wallclock_scaling,
    plot_f2b_wallclock_scaling_logy,
    plot_f3_premise_check,
    plot_f4_accuracy_comparison,
    plot_f5_sensitivity_panels,
    plot_f6_cost_vs_accuracy,
    plot_f6b_cost_vs_accuracy_logx,
)
from scripts.analysis.validate_runs import parse_raw_jsonl, recompute_metrics, validate_all_runs
from scripts.analysis.run_analysis import main as run_pipeline_main


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
    assert classify_slope_flatness(float("nan")) == "undefined"


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


def test_r1_zero_mean_undefined_and_all_positive():
    """Rule R1: A log-log fit with any size whose mean is <= 0 or non-finite is UNDEFINED.

    (NaN slope, no D2 category, no CI, category text "undefined (zero mean at n=...)").
    Remove the 1e-12 clamp everywhere. If at least 3 sizes have positive mean,
    emit one extra row labelled "exploratory (positive-mean sizes only)".
    In bootstrap resamples drop any resample with a zero-mean size and report n_boot_used.
    """
    sizes = [50, 100, 200, 500, 1000, 2000]

    # S2-like data: zero calls at n=50 and n=100, positive at 200, 500, 1000, 2000
    s2_data: Dict[int, List[float]] = {
        50: [0.0] * 5,
        100: [0.0] * 5,
        200: [2.0] * 5,
        500: [5.0] * 5,
        1000: [10.0] * 5,
        2000: [20.0] * 5,
    }

    # Direct fit_log_log_slope test
    emp_means = [float(np.mean(s2_data[s])) for s in sizes]
    slope, intercept, r2 = fit_log_log_slope(sizes, emp_means)
    assert np.isnan(slope)
    assert np.isnan(intercept)
    assert np.isnan(r2)

    # bootstrap_slope_ci test
    point_slope, ci_low, ci_high, cat, r2, n_boot = bootstrap_slope_ci(s2_data, n_resamples=500, seed=42)
    assert np.isnan(point_slope)
    assert np.isnan(ci_low)
    assert np.isnan(ci_high)
    assert np.isnan(r2)
    assert cat == "undefined (zero mean at n=50, 100)"
    assert n_boot == 0

    # Test table slope row generation helper: emits main undefined row + extra exploratory row
    slope_rows: List[Dict[str, Any]] = []
    _fit_metric_slopes("embedding_threshold", "primary", "llm_calls", "pre-registered (all trials)", s2_data, slope_rows)
    assert len(slope_rows) == 2
    # Row 0: Pre-registered undefined
    assert slope_rows[0]["condition"] == "pre-registered (all trials)"
    assert np.isnan(slope_rows[0]["slope"])
    assert np.isnan(slope_rows[0]["ci_95_low"])
    assert slope_rows[0]["flatness_category_D2"] == "undefined (zero mean at n=50, 100)"
    assert slope_rows[0]["min_trials_per_size"] == 5
    assert slope_rows[0]["n_boot_used"] == 0
    # Row 1: Exploratory positive-mean sizes only
    assert slope_rows[1]["condition"] == "exploratory (positive-mean sizes only)"
    assert not np.isnan(slope_rows[1]["slope"])
    assert np.isclose(slope_rows[1]["slope"], 1.0, atol=1e-5)
    assert slope_rows[1]["flatness_category_D2"] == "approximately linear"
    assert slope_rows[1]["min_trials_per_size"] == 5
    assert slope_rows[1]["n_boot_used"] == 10000

    # Unchanged behaviour on all-positive data
    pos_data = {s: [float(s)] * 5 for s in sizes}
    pos_slope, pos_low, pos_high, pos_cat, pos_r2, pos_n_boot = bootstrap_slope_ci(pos_data, n_resamples=500, seed=42)
    assert np.isclose(pos_slope, 1.0, atol=1e-5)
    assert np.isclose(pos_low, 1.0, atol=1e-5)
    assert np.isclose(pos_high, 1.0, atol=1e-5)
    assert pos_cat == "approximately linear"
    assert pos_n_boot == 500


def test_r2_dominance_including_boundary():
    """Rule R2: |F1 difference| < 0.025 => "not distinguishable (F1 within 0.025)", regardless of calls.

    At or above 0.025: A dominates B if A has higher F1 and calls <= B's; otherwise "trade-off".
    """
    # 1. Strictly below 0.025 (|diff| = 0.010 and 0.024) -> not distinguishable even with calls advantage
    pt_a = {"calls": 10.0, "f1": 0.500}
    pt_b = {"calls": 100.0, "f1": 0.524}
    assert evaluate_dominance(pt_a, pt_b) == "not distinguishable (F1 within 0.025)"
    assert evaluate_dominance(pt_b, pt_a) == "not distinguishable (F1 within 0.025)"

    pt_c = {"calls": 10.0, "f1": 0.510}
    pt_d = {"calls": 25.0, "f1": 0.520}  # diff = 0.010 < 0.025
    assert evaluate_dominance(pt_c, pt_d) == "not distinguishable (F1 within 0.025)"

    # 2. Boundary condition: EXACTLY 0.025
    # A has higher F1 (+0.025) and fewer calls -> A dominates B
    pt_e = {"calls": 10.0, "f1": 0.525}
    pt_f = {"calls": 20.0, "f1": 0.500}
    assert evaluate_dominance(pt_e, pt_f) == "A dominates B"

    # A has higher F1 (+0.025) but more calls -> trade-off
    pt_g = {"calls": 30.0, "f1": 0.525}
    pt_h = {"calls": 20.0, "f1": 0.500}
    assert evaluate_dominance(pt_g, pt_h) == "trade-off"

    # Inverse boundary: B has higher F1 (+0.025) and fewer calls -> B dominates A
    assert evaluate_dominance(pt_f, pt_e) == "B dominates A"

    # 3. Strictly above 0.025 (e.g. diff = 0.050)
    pt_i = {"calls": 10.0, "f1": 0.600}
    pt_j = {"calls": 20.0, "f1": 0.500}
    assert evaluate_dominance(pt_i, pt_j) == "A dominates B"

    pt_k = {"calls": 50.0, "f1": 0.600}
    pt_l = {"calls": 10.0, "f1": 0.500}
    assert evaluate_dominance(pt_k, pt_l) == "trade-off"


def create_mock_run_directory(
    root: Path,
    run_name: str,
    strategy: str,
    mode: str,
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Path:
    """Helper to create a synthetic run directory with manifest, config, raw.jsonl, and summary.csv."""
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


def test_r3_post_hoc_sensitivity_exclusion(tmp_path: Path):
    """Rule R3: trials with retries > 0 and the single trial sweep:brute_force:2000:t9

    are excluded from the post-hoc timing sensitivity columns.
    clean_exclusion_rule column records exact exclusion rule.
    """
    records = []
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

    # Post-hoc clean excludes trial 8 (retries=2) and trial 9 (sweep:brute_force:2000:t9)
    assert row["clean_num_trials_post_hoc_not_preregistered"] == 8
    assert np.isclose(row["clean_total_s_mean_post_hoc_not_preregistered"], 100.0)
    assert np.isclose(row["clean_total_s_max_post_hoc_not_preregistered"], 100.0)

    # Check clean_exclusion_rule column
    expected_rule = "retries>0; and the single trial launched with --allow-peak inside the peak window (sweep:brute_force:2000:t9)"
    assert row["clean_exclusion_rule"] == expected_rule


def test_strict_accessor_raises_on_missing_column(tmp_path: Path):
    """Verifies that _require_col raises KeyError naming run and column."""
    with pytest.raises(KeyError) as exc_info:
        _require_col({"a": 1}, "missing_col", "run_xyz")
    assert "run_xyz" in str(exc_info.value)
    assert "missing_col" in str(exc_info.value)

    with pytest.raises(KeyError) as exc_info_empty:
        _require_col({"col_b": ""}, "col_b", "run_xyz")
    assert "run_xyz" in str(exc_info_empty.value)
    assert "col_b" in str(exc_info_empty.value)

    # Verify generate_t1_accuracy_table fails strictly on missing required column
    run_dir = tmp_path / "bad_acc_run"
    run_dir.mkdir(parents=True)
    (run_dir / "strategy_config.json").write_text(json.dumps({"strategy": "brute_force"}), encoding="utf-8")
    with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["corpus_or_size", "num_trials"])
        writer.writeheader()
        writer.writerow({"corpus_or_size": "DSA_gold_standard_MEKG", "num_trials": "29"})

    with pytest.raises(KeyError) as exc_info_table:
        generate_t1_accuracy_table([run_dir])
    assert "bad_acc_run" in str(exc_info_table.value)


def test_t3_header_and_trial_count(tmp_path: Path):
    """Verifies Table T3 header equals the 18 validator fieldnames and trials == 60 on a 60-trial fixture."""
    expected_18_fields = [
        "run", "strategy", "config", "mode", "commit", "libraries_hash",
        "trials", "calls", "failed", "failed_then_succeeded", "still_failed", "retries", "status",
        "manifest_sha256", "config_sha256", "raw_sha256", "summary_sha256", "dir_sha256"
    ]

    # Build 60-trial sweep fixture (6 sizes x 10 trials)
    records = []
    for s in [50, 100, 200, 500, 1000, 2000]:
        for t in range(10):
            records.append({
                "key": f"sweep:brute_force:{s}:t{t}",
                "size": s,
                "status": "success",
                "retries": 0,
                "metrics": {"total_s": 5.0, "shortlist_s": 0.01, "decide_s": 4.99, "llm_calls": s},
            })

    run_dir = create_mock_run_directory(
        tmp_path,
        "sweep_brute_force",
        "brute_force",
        "sweep",
        records,
        config={},
    )

    passed, results, t3_csv_str = validate_all_runs(tmp_path)
    header_line = t3_csv_str.splitlines()[0]
    actual_fields = header_line.split(",")
    assert actual_fields == expected_18_fields

    t3_rows = generate_t3_inventory_table(t3_csv_str)
    assert len(t3_rows) == 1
    assert int(t3_rows[0]["trials"]) == 60
    assert "total_trials" not in t3_rows[0]


def test_gate_failure_aborts_and_writes_nothing(tmp_path: Path, monkeypatch):
    """Verifies that gate failure exits 1 and writes no output files."""
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "output"
    results_dir.mkdir()

    # Monkeypatch validate_all_runs to fail
    def mock_validate_fail(*args, **kwargs):
        return (False, [{"run_dir": "failing_run", "passed": False, "errors": ["Mock error"]}], "")

    import scripts.analysis.run_analysis as ra
    monkeypatch.setattr(ra, "validate_all_runs", mock_validate_fail)

    test_argv = [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
    ]
    monkeypatch.setattr(sys, "argv", test_argv)

    rc = run_pipeline_main()
    assert rc == 1
    assert not output_dir.exists()


def test_gate_success_and_run_info(tmp_path: Path, monkeypatch):
    """Verifies that gate success writes RUN_INFO.txt with all required fields."""
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "output"
    results_dir.mkdir()

    # Create dummy primary runs for F3 caps
    create_mock_run_directory(
        results_dir,
        "sweep_ann_retrieval_k10_ef128",
        "ann_retrieval",
        "sweep",
        [{"key": "sweep:ann_retrieval:50:t0", "size": 50, "status": "success", "retries": 0, "metrics": {"total_s": 1.0, "shortlist_s": 0.01, "decide_s": 0.99, "llm_calls": 10}}],
        config={"k": 10, "ef_search": 128},
    )
    create_mock_run_directory(
        results_dir,
        "sweep_bounded_bucket_smin5_smax10_nb12",
        "bounded_bucket",
        "sweep",
        [{"key": "sweep:bounded_bucket:50:t0", "size": 50, "status": "success", "retries": 0, "metrics": {"total_s": 1.0, "shortlist_s": 0.01, "decide_s": 0.99, "llm_calls": 10}}],
        config={"s_min": 5, "s_max": 10, "num_hyperplanes": 12},
    )

    mock_t3_csv = (
        "run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,failed_then_succeeded,still_failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256\n"
        'sweep_ann_retrieval_k10_ef128,ann_retrieval,"{}",sweep,3323bfb,h1,1,10,0,0,0,0,PASS,m1,c1,r1,s1,d1\n'
    )

    import scripts.analysis.run_analysis as ra
    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], mock_t3_csv))

    test_argv = [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
        "--src-diff-clean",
    ]
    monkeypatch.setattr(sys, "argv", test_argv)

    rc = run_pipeline_main()
    assert rc == 0
    assert (output_dir / "RUN_INFO.txt").exists()

    run_info = (output_dir / "RUN_INFO.txt").read_text(encoding="utf-8")
    assert "argv:" in run_info
    assert "results_dir:" in run_info
    assert "git_commit:" in run_info
    assert "pipeline_modules_sha256:" in run_info
    assert "validate_runs.py:" in run_info
    assert "run_analysis.py:" in run_info
    assert "tables.py:" in run_info
    assert "figures.py:" in run_info
    assert "stats.py:" in run_info
    assert "bootstrap.py:" in run_info
    assert "style.py:" in run_info
    assert "hashes_file: NOT SUPPLIED" in run_info
    assert "src_diff_clean: True" in run_info
    assert "overall_gate_status: PASS" in run_info


def test_end_to_end_without_skip_gate(tmp_path: Path, monkeypatch):
    """End-to-end execution of the full analysis pipeline on synthetic data WITHOUT skip-gate."""
    results_dir = tmp_path / "results"
    output_dir = tmp_path / "output"
    results_dir.mkdir()

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

    acc_bf_records = [
        {
            "key": f"acc:brute_force:DSA_gold_standard_MEKG:node_{i}",
            "corpus": "DSA_gold_standard_MEKG",
            "status": "success",
            "retries": 0,
            "metrics": {"total_s": 15.0, "shortlist_s": 0.0, "decide_s": 14.99, "llm_calls": 28},
            "score": {"tp": 2, "fp": 1, "fn": 1, "precision": 0.66, "recall": 0.66, "f1": 0.66, "shortlist_hits": 28, "gold_neighbours": 3, "shortlist_recall": 1.0},
        }
        for i in range(29)
    ]
    create_mock_run_directory(
        results_dir,
        "accuracy_brute_force",
        "brute_force",
        "accuracy",
        acc_bf_records,
        config={},
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
    create_mock_run_directory(
        results_dir,
        "sweep_bounded_bucket_smin5_smax10_nb12",
        "bounded_bucket",
        "sweep",
        sweep_records,
        config={"s_min": 5, "s_max": 10, "num_hyperplanes": 12},
    )

    mock_t3_csv = (
        "run,strategy,config,mode,commit,libraries_hash,trials,calls,failed,failed_then_succeeded,still_failed,retries,status,manifest_sha256,config_sha256,raw_sha256,summary_sha256,dir_sha256\n"
        'accuracy_ann_retrieval_k10_ef128,ann_retrieval,"{}",accuracy,3323bfb,h1,29,290,0,0,0,0,PASS,m1,c1,r1,s1,d1\n'
        'accuracy_brute_force,brute_force,"{}",accuracy,3323bfb,h1,29,812,0,0,0,0,PASS,m0,c0,r0,s0,d0\n'
        'sweep_ann_retrieval_k10_ef128,ann_retrieval,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m2,c2,r2,s2,d2\n'
        'sweep_bounded_bucket_smin5_smax10_nb12,bounded_bucket,"{}",sweep,3323bfb,h1,60,600,0,0,0,0,PASS,m3,c3,r3,s3,d3\n'
    )

    import scripts.analysis.run_analysis as ra
    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], mock_t3_csv))

    test_argv = [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
    ]
    monkeypatch.setattr(sys, "argv", test_argv)

    rc = run_pipeline_main()
    assert rc == 0

    # Verify generated tables
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

    # Verify generated figures
    for fig_name in [
        "F1_calls_scaling",
        "F1b_calls_scaling_logy",
        "F2_wallclock_scaling",
        "F2b_wallclock_scaling_logy",
        "F3_premise_check",
        "F4_accuracy_by_strategy",
        "F5_sensitivity_panels",
        "F6_cost_vs_accuracy_dominance",
        "F6b_cost_vs_accuracy_logx",
    ]:
        assert (output_dir / "figures" / f"{fig_name}.pdf").exists()
        assert (output_dir / "figures" / f"{fig_name}.png").exists()
        assert (output_dir / "figures" / f"{fig_name}.csv").exists()

    # Verify F6 dominance files
    assert (output_dir / "figures" / "F6_dominance.csv").exists()
    assert (output_dir / "figures" / "F6_dominance.md").exists()


def test_source_grep_forbidden_patterns():
    """Verifies that 'skip-gate', '/home/', and '1e-12' are absent from scripts/analysis/*.py."""
    repo_root = Path(__file__).resolve().parent.parent
    analysis_dir = repo_root / "scripts" / "analysis"
    py_files = sorted(list(analysis_dir.glob("*.py")))
    assert len(py_files) >= 6

    forbidden = ["skip-gate", "/home/", "1e-12"]

    for pf in py_files:
        content = pf.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in content, f"Forbidden pattern '{pattern}' found in {pf.name}"


def test_parity_with_validator_on_real_accuracy_directories():
    """Requirement 5: Test that pipeline numbers equal validator recomputations

    directly on real accuracy directories from PHASE4_RESULTS_DIR (skips if unset).
    """
    res_env = os.environ.get("PHASE4_RESULTS_DIR")
    if not res_env:
        pytest.skip("PHASE4_RESULTS_DIR environment variable is unset")

    real_results_path = Path(res_env).resolve()
    if not real_results_path.exists():
        pytest.skip(f"PHASE4_RESULTS_DIR path '{real_results_path}' does not exist")

    acc_dirs = sorted([d for d in real_results_path.iterdir() if d.is_dir() and d.name.startswith("accuracy_") and (d / "manifest.json").exists()])
    if not acc_dirs:
        pytest.skip(f"No accuracy directories found in '{real_results_path}'")

    t1_rows = generate_t1_accuracy_table(acc_dirs)
    assert len(t1_rows) == 24  # 12 configurations x 2 corpora

    t1_map = {(r["strategy"], r["variant"], r["corpus"]): r for r in t1_rows}

    for acc_dir in acc_dirs:
        raw_path = acc_dir / "raw.jsonl"
        sidecar_path = acc_dir / "strategy_config.json"
        strat_cfg = json.loads(sidecar_path.read_text(encoding="utf-8"))
        strat = strat_cfg.get("strategy")
        variant = extract_variant_label(acc_dir.name)

        records, is_resumed, _, key_records = parse_raw_jsonl(raw_path)
        val_metrics = recompute_metrics(records, "accuracy")

        for corpus, expected in val_metrics.items():
            key = (strat, variant, corpus)
            assert key in t1_map, f"Missing {key} in Table T1"
            t1_row = t1_map[key]

            assert t1_row["num_trials"] == expected["num_trials"]
            assert t1_row["num_success"] == expected["num_success"]
            assert np.isclose(t1_row["llm_calls_mean"], expected["llm_calls_mean"], atol=1e-5)
            assert np.isclose(t1_row["f1_micro"], expected["f1_micro"], atol=1e-5)
            assert np.isclose(t1_row["precision_micro"], expected["precision_micro"], atol=1e-5)
            assert np.isclose(t1_row["recall_micro"], expected["recall_micro"], atol=1e-5)
            assert np.isclose(t1_row["shortlist_recall_micro"], expected["shortlist_recall_micro"], atol=1e-5)
            if expected["f1_macro"] is not None:
                assert np.isclose(t1_row["f1_macro"], expected["f1_macro"], atol=1e-5)


def test_companion_figures_output_files_and_scales(tmp_path: Path):
    """Verifies that F1b, F2b, and F6b export .pdf, .png, and .csv, set log scales,

    include the exploratory marker in figure text and CSV, and keep dominance consistent.
    """
    t2_rows = [
        {
            "strategy": "brute_force",
            "variant": "primary (all candidates)",
            "size_n": 50,
            "llm_calls_mean": 50.0,
            "llm_calls_ci_mean_low": 50.0,
            "llm_calls_ci_mean_high": 50.0,
            "llm_calls_median": 50.0,
            "llm_calls_std": 0.0,
            "total_s_mean": 1.25,
            "total_s_ci_mean_low": 1.10,
            "total_s_ci_mean_high": 1.40,
            "shortlist_s_mean": 0.01,
            "decide_s_mean": 1.24,
        },
        {
            "strategy": "brute_force",
            "variant": "primary (all candidates)",
            "size_n": 100,
            "llm_calls_mean": 100.0,
            "llm_calls_ci_mean_low": 100.0,
            "llm_calls_ci_mean_high": 100.0,
            "llm_calls_median": 100.0,
            "llm_calls_std": 0.0,
            "total_s_mean": 2.50,
            "total_s_ci_mean_low": 2.30,
            "total_s_ci_mean_high": 2.70,
            "shortlist_s_mean": 0.01,
            "decide_s_mean": 2.49,
        },
    ]

    t1_rows = [
        {
            "corpus": "DSA_gold_standard_MEKG",
            "strategy": "brute_force",
            "variant": "primary (all candidates)",
            "llm_calls_mean": 28.0,
            "f1_micro": 0.5862,
        },
        {
            "corpus": "DSA_gold_standard_MEKG",
            "strategy": "embedding_threshold",
            "variant": "primary (theta=0.6)",
            "llm_calls_mean": 0.8,
            "f1_micro": 0.1475,
        },
    ]

    # 1. F1b
    fig1 = plot_f1b_calls_scaling_logy(t2_rows, tmp_path)
    for ext in [".pdf", ".png", ".csv"]:
        assert (tmp_path / f"F1b_calls_scaling_logy{ext}").exists()
    ax1 = fig1.axes[0]
    assert ax1.get_yscale() == "log", "F1b y scale must be log"
    assert ax1.get_xscale() == "log", "F1b x scale must be log"

    fig1_texts = [t.get_text() for t in fig1.findobj(mtext.Text)]
    assert any("EXPLORATORY: log scale, not pre-registered" in txt for txt in fig1_texts)

    with open(tmp_path / "F1b_calls_scaling_logy.csv", newline="", encoding="utf-8") as f:
        r1 = list(csv.DictReader(f))
        assert len(r1) == 2
        assert all(row["status"] == "exploratory" for row in r1)
        assert all(row["plotted"] in ("True", True) for row in r1)

    # 2. F2b
    fig2 = plot_f2b_wallclock_scaling_logy(t2_rows, tmp_path)
    for ext in [".pdf", ".png", ".csv"]:
        assert (tmp_path / f"F2b_wallclock_scaling_logy{ext}").exists()
    assert fig2.axes[0].get_yscale() == "log", "F2b panel A y scale must be log"
    assert fig2.axes[1].get_yscale() == "log", "F2b panel B y scale must be log"

    fig2_texts = [t.get_text() for t in fig2.findobj(mtext.Text)]
    assert any("EXPLORATORY: log scale, not pre-registered" in txt for txt in fig2_texts)

    with open(tmp_path / "F2b_wallclock_scaling_logy.csv", newline="", encoding="utf-8") as f:
        r2 = list(csv.DictReader(f))
        assert len(r2) == 2
        assert all(row["status"] == "exploratory" for row in r2)
        assert all(row["plotted"] in ("True", True) for row in r2)

    # 3. F6b
    fig6 = plot_f6b_cost_vs_accuracy_logx(t1_rows, tmp_path)
    for ext in [".pdf", ".png", ".csv"]:
        assert (tmp_path / f"F6b_cost_vs_accuracy_logx{ext}").exists()
    ax6 = fig6.axes[0]
    assert ax6.get_xscale() == "log", "F6b x scale must be log"
    assert ax6.get_ylim() == (0.0, 1.05), "F6b y scale must be linear (0, 1.05)"

    fig6_texts = [t.get_text() for t in fig6.findobj(mtext.Text)]
    assert any("EXPLORATORY: log scale, not pre-registered" in txt for txt in fig6_texts)

    with open(tmp_path / "F6b_cost_vs_accuracy_logx.csv", newline="", encoding="utf-8") as f:
        r6 = list(csv.DictReader(f))
        assert len(r6) == 2
        assert all(row["status"] == "exploratory" for row in r6)
        assert all(row["plotted"] in ("True", True) for row in r6)


def test_omitted_non_positive_points_and_no_clamping(tmp_path: Path):
    """Verifies that non-positive points are omitted (never clamped to 1e-6 or any substitute),

    recorded with plotted=False in CSV, named in a footnote, and confidence bounds <= 0 are unedited.
    """
    t2_rows = [
        {
            "strategy": "embedding_threshold",
            "variant": "primary (theta=0.6)",
            "size_n": 50,
            "llm_calls_mean": 0.0,
            "llm_calls_ci_mean_low": 0.0,
            "llm_calls_ci_mean_high": 0.0,
            "llm_calls_median": 0.0,
            "llm_calls_std": 0.0,
            "total_s_mean": 0.01,
            "total_s_ci_mean_low": 0.0,
            "total_s_ci_mean_high": 0.02,
            "shortlist_s_mean": 0.01,
            "decide_s_mean": 0.0,
        },
        {
            "strategy": "embedding_threshold",
            "variant": "primary (theta=0.6)",
            "size_n": 100,
            "llm_calls_mean": 0.1,
            "llm_calls_ci_mean_low": 0.0,
            "llm_calls_ci_mean_high": 0.3,
            "llm_calls_median": 0.0,
            "llm_calls_std": 0.316,
            "total_s_mean": 0.02,
            "total_s_ci_mean_low": 0.01,
            "total_s_ci_mean_high": 0.03,
            "shortlist_s_mean": 0.01,
            "decide_s_mean": 0.01,
        },
    ]

    fig = plot_f1b_calls_scaling_logy(t2_rows, tmp_path)
    ax = fig.axes[0]

    drawn_y = [y for y in ax.lines[0].get_ydata() if not np.isnan(y)]
    assert len(drawn_y) == 1, "Only positive points should be drawn"
    assert drawn_y[0] == 0.1
    assert not any(np.isclose(y, 1e-6) for y in drawn_y), "Zero-mean point was clamped to 1e-6 instead of omitted"
    assert not any(y <= 0 for y in drawn_y), "Non-positive points must not be drawn"

    with open(tmp_path / "F1b_calls_scaling_logy.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert len(rows) == 2
        r50 = [r for r in rows if r["n"] in ("50", 50)][0]
        r100 = [r for r in rows if r["n"] in ("100", 100)][0]
        assert r50["plotted"] in ("False", False), "Omitted point must have plotted=False in CSV"
        assert r100["plotted"] in ("True", True), "Plotted point must have plotted=True in CSV"
        assert float(r100["llm_calls_ci_low"]) == 0.0

    fig_texts = [t.get_text() for t in fig.findobj(mtext.Text)]
    assert any("not plotted: embedding_threshold n=50: zero mean" in txt for txt in fig_texts)


def test_f6b_annotations_no_overlap_and_leader_lines(tmp_path: Path):
    """Verifies F6b on fixture with calls 1.1, 7.4, 10.0, 140.0 and micro-F1 0.27, 0.11, 0.29, 0.14.

    Computes window extents of every annotation with the renderer and asserts no pairwise intersection.
    Also asserts leader lines and alternating offsets are used, and dominance box matches evaluate_dominance.
    """
    t1_rows = [
        {
            "corpus": "metacademy_gold_standard_MEKG",
            "strategy": "embedding_threshold",
            "variant": "primary (theta=0.6)",
            "llm_calls_mean": 1.1,
            "f1_micro": 0.27,
        },
        {
            "corpus": "metacademy_gold_standard_MEKG",
            "strategy": "bounded_bucket",
            "variant": "primary (s_min=5, s_max=10, nb=12)",
            "llm_calls_mean": 7.4,
            "f1_micro": 0.11,
        },
        {
            "corpus": "metacademy_gold_standard_MEKG",
            "strategy": "ann_retrieval",
            "variant": "primary (k=10, ef=128)",
            "llm_calls_mean": 10.0,
            "f1_micro": 0.29,
        },
        {
            "corpus": "metacademy_gold_standard_MEKG",
            "strategy": "brute_force",
            "variant": "primary (all candidates)",
            "llm_calls_mean": 140.0,
            "f1_micro": 0.14,
        },
    ]

    fig = plot_f6b_cost_vs_accuracy_logx(t1_rows, tmp_path)
    ax = fig.axes[0]

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()

    annotations = [t for t in ax.texts if hasattr(t, "xyann") and t.arrowprops is not None]
    assert len(annotations) == 4, f"Expected 4 point annotations, got {len(annotations)}"

    assert all(ann.arrowprops is not None for ann in annotations), "Every point annotation must have a leader line"
    offsets = [ann.xyann for ann in annotations]
    assert len(set(offsets)) > 1, "F6b annotations must alternate offsets, not use fixed offset for all points"

    bboxes = [ann.get_window_extent(renderer) for ann in annotations]
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            assert not bboxes[i].overlaps(bboxes[j]), (
                f"Pairwise intersection detected between annotation {i} and {j}: {bboxes[i]} vs {bboxes[j]}"
            )

    dom_texts = [t.get_text() for t in ax.texts if " vs " in t.get_text()]
    assert len(dom_texts) == 1
    dom_content = dom_texts[0]
    expected_pairs = [
        ("embedding_threshold", "bounded_bucket"),
        ("embedding_threshold", "ann_retrieval"),
        ("embedding_threshold", "brute_force"),
        ("bounded_bucket", "ann_retrieval"),
        ("bounded_bucket", "brute_force"),
        ("ann_retrieval", "brute_force"),
    ]
    pts = {r["strategy"]: {"calls": r["llm_calls_mean"], "f1": r["f1_micro"]} for r in t1_rows}
    for s_a, s_b in expected_pairs:
        expected_dom = evaluate_dominance(pts[s_a], pts[s_b])
        assert f"{s_a} vs {s_b}: {expected_dom}" in dom_content


def test_f6b_plots_micro_f1_not_macro(tmp_path: Path):
    """Verifies that F6b plots micro-F1, not macro-F1."""
    t1_rows = [
        {
            "corpus": "DSA_gold_standard_MEKG",
            "strategy": "brute_force",
            "variant": "primary",
            "llm_calls_mean": 28.0,
            "f1_micro": 0.27,
            "f1_macro": 0.85,
        }
    ]
    fig = plot_f6b_cost_vs_accuracy_logx(t1_rows, tmp_path)
    with open(tmp_path / "F6b_cost_vs_accuracy_logx.csv", newline="", encoding="utf-8") as f:
        r = list(csv.DictReader(f))[0]
        assert np.isclose(float(r["f1"]), 0.27), "F6b must plot f1_micro (0.27), not f1_macro"
    ax = fig.axes[0]
    offsets = ax.collections[0].get_offsets()
    assert np.isclose(offsets[0][1], 0.27), "F6b scatter y-position must be f1_micro"

