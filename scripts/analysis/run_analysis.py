"""
run_analysis.py — Master Orchestration Script for Phase 4 Analysis
==================================================================
Implements Section 1, Rule 2 of the Phase 4 Analysis Plan:
"One script generates every figure and table from data that has passed
the validation gate. No hand edits."

Usage:
    python scripts/analysis/run_analysis.py --results-dir /path/to/results --output-dir /path/to/output [--src-diff-clean] [--hashes /path/to/hashes]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Ensure scripts/analysis and repo root are in sys.path
_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from .validate_runs import validate_all_runs
    from .tables import (
        extract_variant_label,
        generate_t1_accuracy_table,
        generate_t2_sweep_cost_table,
        generate_t3_inventory_table,
        generate_t4_sensitivity_table,
        export_markdown_table,
        write_csv,
    )
    from .figures import (
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
    from .posthoc import run_posthoc_stage
except ImportError:
    from validate_runs import validate_all_runs
    from tables import (
        extract_variant_label,
        generate_t1_accuracy_table,
        generate_t2_sweep_cost_table,
        generate_t3_inventory_table,
        generate_t4_sensitivity_table,
        export_markdown_table,
        write_csv,
    )
    from figures import (
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
    from posthoc import run_posthoc_stage


def _file_sha256(path: Path) -> str:
    """Compute sha256 of a file in 64 KB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Master Phase 4 Empirical Analysis Pipeline")
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Path to results directory containing run folders",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Path to output directory for tables and figures (outside repo)",
    )
    parser.add_argument(
        "--src-diff-clean",
        action="store_true",
        default=False,
        help="Accept differing git commits across modes if certified clean against baseline",
    )
    parser.add_argument(
        "--hashes",
        type=Path,
        default=None,
        help="Optional path to machine-written sha256 hashes file to verify against",
    )
    parser.add_argument(
        "--only",
        choices=["posthoc"],
        default=None,
        help=(
            "Run only the post-hoc stage (gate, in-memory T1/T2 aggregates, then Tables "
            "T5-T9b and Figures F7-F9); no pre-registered artifact is written"
        ),
    )
    parser.add_argument(
        "--crosscheck-dir",
        type=Path,
        default=None,
        help=(
            "Existing pipeline output directory whose T1/T2/F6 CSV cells the post-hoc "
            "inputs are asserted against (required with --only posthoc)"
        ),
    )
    args = parser.parse_args()

    if args.only == "posthoc" and args.crosscheck_dir is None:
        parser.error("--only posthoc requires --crosscheck-dir")

    results_dir = args.results_dir.resolve()
    output_dir = args.output_dir.resolve()
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"

    print("=" * 80)
    print("PHASE 4 EMPIRICAL ANALYSIS PIPELINE")
    print(f"Results Directory: {results_dir}")
    print(f"Output Directory:  {output_dir}")
    print("=" * 80)

    # 1. Validation Gate (fail-closed: do not create output dirs or write anything on failure)
    print("\n>>> STEP 1: Running Independent Validation Gate (scripts/analysis/validate_runs.py)...")
    overall_passed, run_results, t3_csv_str = validate_all_runs(
        results_dir,
        src_diff_clean=args.src_diff_clean,
        hashes_path=args.hashes,
    )
    if not overall_passed:
        print("\n[ABORT] Validation gate failed. Analysis halted per Rule 5 of Analysis Plan.")
        for r in run_results:
            if not r.get("passed"):
                print(f"  FAILED RUN: {r.get('run_dir')}")
                for err in r.get("errors", []):
                    print(f"    -> ERROR: {err}")
        return 1

    print("\n[OK] Validation gate passed 100%. Proceeding with analysis.\n")

    # Create output directories only after the gate passes
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Write RUN_INFO.txt
    pipeline_modules = [
        "validate_runs.py",
        "run_analysis.py",
        "tables.py",
        "figures.py",
        "stats.py",
        "bootstrap.py",
        "style.py",
        "posthoc.py",
        "posthoc_figures.py",
    ]
    module_hashes = {}
    for mod in pipeline_modules:
        p = _current_dir / mod
        if p.is_file():
            module_hashes[mod] = _file_sha256(p)
        else:
            module_hashes[mod] = "MISSING"

    try:
        git_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_repo_root, text=True
        ).strip()
    except Exception:
        git_head = "UNKNOWN"

    if args.hashes and args.hashes.is_file():
        hashes_info = f"{args.hashes.resolve()} (sha256: {_file_sha256(args.hashes)})"
    else:
        hashes_info = "NOT SUPPLIED"

    run_info_lines = [
        f"argv: {' '.join(sys.argv)}",
        f"results_dir: {results_dir}",
        f"git_commit: {git_head}",
        f"only: {args.only or 'all'}",
        f"crosscheck_dir: {args.crosscheck_dir.resolve() if args.crosscheck_dir else 'NOT SUPPLIED'}",
        "pipeline_modules_sha256:",
    ]
    for mod, h in module_hashes.items():
        run_info_lines.append(f"  {mod}: {h}")
    run_info_lines.extend([
        f"hashes_file: {hashes_info}",
        f"src_diff_clean: {args.src_diff_clean}",
        "overall_gate_status: PASS",
    ])
    (output_dir / "RUN_INFO.txt").write_text("\n".join(run_info_lines) + "\n", encoding="utf-8")

    # Discover run directories
    if (results_dir / "manifest.json").is_file():
        all_runs = [results_dir]
    else:
        all_runs = sorted([d for d in results_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()])

    acc_runs = [d for d in all_runs if "accuracy" in d.name]
    sweep_runs = [d for d in all_runs if "sweep" in d.name]

    print(f"Discovered: {len(all_runs)} total runs ({len(acc_runs)} accuracy, {len(sweep_runs)} sweep)\n")

    # Post-hoc-only stage (ANALYSIS-004, [D-89]): gate already passed above.
    # Build the T1/T2 aggregates in memory and write only the new artifacts.
    if args.only == "posthoc":
        print(">>> STEP 1b: Post-hoc decision and ranking stage (POST HOC, not pre-registered)...")
        t1_rows = generate_t1_accuracy_table(acc_runs)
        t2_rows, _ = generate_t2_sweep_cost_table(sweep_runs)
        summary = run_posthoc_stage(
            results_dir=results_dir,
            accuracy_run_dirs=acc_runs,
            t1_rows=t1_rows,
            t2_rows=t2_rows,
            output_dir=output_dir,
            crosscheck_dir=args.crosscheck_dir,
        )
        classes_txt = ", ".join(
            f"{s}={info['class']}" for s, info in summary["gates"].items()
        )
        print(f"    Cross-check cells matched against {args.crosscheck_dir}: {summary['n_crosschecks']}")
        print(f"    Gate classes: {classes_txt}")
        print(f"    Saved: {tables_dir}/{{{', '.join(sorted(p.name for p in tables_dir.glob('T[5-9]*.csv')))}}}")
        print(f"    Saved: {figures_dir}/F7_gates_g1_g2, F8_score_vs_weight, F9_rank_shares (.pdf, .png, .csv)")
        print("\n" + "=" * 80)
        print("POST-HOC STAGE COMPLETED SUCCESSFULLY (POST HOC, not pre-registered).")
        print("=" * 80)
        return 0

    # 2. Table T3: Run Inventory (write validator's t3_csv verbatim as T3_run_inventory.csv)
    print(">>> STEP 2: Generating Table T3 (Run Inventory)...")
    (tables_dir / "T3_run_inventory.csv").write_text(t3_csv_str, encoding="utf-8")
    t3_rows = generate_t3_inventory_table(t3_csv_str)
    export_markdown_table(t3_rows, tables_dir / "T3_run_inventory.md", "Table T3: Empirical Run Inventory")
    print(f"    Saved: {tables_dir / 'T3_run_inventory.csv'} and .md ({len(t3_rows)} entries)")

    # 3. Accuracy Tables & Figures (if accuracy runs present)
    if acc_runs:
        print("\n>>> STEP 3: Generating Accuracy Tables (T1, T4)...")
        t1_rows = generate_t1_accuracy_table(acc_runs, tables_dir / "T1_accuracy_benchmark.csv")
        export_markdown_table(t1_rows, tables_dir / "T1_accuracy_benchmark.md", "Table T1: Accuracy Benchmark Matrix")
        print(f"    Saved: {tables_dir / 'T1_accuracy_benchmark.csv'} and .md ({len(t1_rows)} rows)")

        t4_rows = generate_t4_sensitivity_table(acc_runs, tables_dir / "T4_sensitivity_metrics.csv")
        export_markdown_table(t4_rows, tables_dir / "T4_sensitivity_metrics.md", "Table T4: Sensitivity Variants and Unjudged Predictions")
        print(f"    Saved: {tables_dir / 'T4_sensitivity_metrics.csv'} and .md ({len(t4_rows)} rows)")

        print("\n>>> STEP 4: Generating Accuracy Figures (F4, F5, F6)...")
        plot_f4_accuracy_comparison(t1_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F4_accuracy_by_strategy.pdf'} (.png, .csv)")

        plot_f5_sensitivity_panels(t1_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F5_sensitivity_panels.pdf'} (.png, .csv)")

        plot_f6_cost_vs_accuracy(t1_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F6_cost_vs_accuracy_dominance.pdf'} (.png, .csv)")
        print(f"    Saved: {figures_dir / 'F6_dominance.csv'} and .md")

        plot_f6b_cost_vs_accuracy_logx(t1_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F6b_cost_vs_accuracy_logx.pdf'} (.png, .csv)")

    # 4. Sweep Tables & Figures (if sweep runs present)
    if sweep_runs:
        print("\n>>> STEP 5: Generating Sweep Cost Table (T2) and Slope Fits...")
        t2_rows, slope_fit_rows = generate_t2_sweep_cost_table(sweep_runs, tables_dir / "T2_sweep_cost_summary.csv")
        export_markdown_table(t2_rows, tables_dir / "T2_sweep_cost_summary.md", "Table T2: Sweep Cost Summary")
        print(f"    Saved: {tables_dir / 'T2_sweep_cost_summary.csv'} and .md ({len(t2_rows)} rows)")

        if slope_fit_rows:
            write_csv(tables_dir / "T2_slope_fits.csv", slope_fit_rows)
            export_markdown_table(slope_fit_rows, tables_dir / "T2_slope_fits.md", "Table T2b: Log-Log OLS Slope Fits & Flatness Classification (D2)")
            print(f"    Saved: {tables_dir / 'T2_slope_fits.csv'} and .md ({len(slope_fit_rows)} fits)")

        # Extract primary caps for F3
        k_cap: Optional[int] = None
        smax_cap: Optional[int] = None
        for d in sweep_runs:
            sidecar_p = d / "strategy_config.json"
            if not sidecar_p.is_file():
                continue
            strat_cfg = json.loads(sidecar_p.read_text(encoding="utf-8"))
            strat = strat_cfg.get("strategy")
            strat_params = strat_cfg.get("config", {}) if isinstance(strat_cfg.get("config"), dict) else {}
            variant = extract_variant_label(d.name)

            if strat == "ann_retrieval" and "primary" in variant:
                if "k" in strat_params:
                    k_cap = int(strat_params["k"])
                elif "k" in strat_cfg:
                    k_cap = int(strat_cfg["k"])

            if strat == "bounded_bucket" and "primary" in variant:
                if "s_max" in strat_params:
                    smax_cap = int(strat_params["s_max"])
                elif "s_max" in strat_cfg:
                    smax_cap = int(strat_cfg["s_max"])

        if k_cap is None:
            raise ValueError("Missing 'k' cap in primary Strategy 3 (ann_retrieval) strategy_config.json")
        if smax_cap is None:
            raise ValueError("Missing 's_max' cap in primary Strategy 4 (bounded_bucket) strategy_config.json")

        print("\n>>> STEP 6: Generating Sweep Figures (F1, F2, F3)...")
        plot_f1_calls_scaling(t2_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F1_calls_scaling.pdf'} (.png, .csv)")

        plot_f2_wallclock_scaling(t2_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F2_wallclock_scaling.pdf'} (.png, .csv)")

        plot_f3_premise_check(t2_rows, figures_dir, k_cap=k_cap, smax_cap=smax_cap)
        print(f"    Saved: {figures_dir / 'F3_premise_check.pdf'} (.png, .csv)")

        plot_f1b_calls_scaling_logy(t2_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F1b_calls_scaling_logy.pdf'} (.png, .csv)")

        plot_f2b_wallclock_scaling_logy(t2_rows, figures_dir)
        print(f"    Saved: {figures_dir / 'F2b_wallclock_scaling_logy.pdf'} (.png, .csv)")

    print("\n" + "=" * 80)
    print("PHASE 4 ANALYSIS PIPELINE COMPLETED SUCCESSFULLY (100% PASS).")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())

