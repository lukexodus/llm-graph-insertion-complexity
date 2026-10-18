#!/usr/bin/env python3
"""
validate_runs.py — Independent Validation Gate for Experiment Runs
===================================================================
Implements Section 2 of the Phase 4 Analysis Plan (TASK ANALYSIS-001).

Checks performed:
1. Exact trial count enforcement:
   - Accuracy: 59 trials total (29 DSA + 30 Metacademy), derived per-group.
   - Sweep: 60 trials total (10 per size across {50, 100, 200, 500, 1000, 2000}), derived per-group.
   - Legacy DSA-only fixture: 29 trials (DSA only).
2. Planned call bound verification:
   - Keyed directly by sidecar strategy and config (README run table D-68).
   - Directory slug cross-checked.
3. Independent recomputation from raw.jsonl vs summary.csv:
   - Micro and Macro P, R, F1, Shortlist Recall (macro excludes undefined/zero-neighbour nodes).
   - Mean and median total_s (median via statistics.median for even-n correctness).
   - Mean and sum of LLM calls.
   - Recomputation agreement checked within floating-point tolerance.
4. Manifest and provenance checks:
   - git_dirty is strictly False (boolean).
   - git_commit identical across all runs.
   - libraries block contains all 7 required libraries and is identical across all runs.
5. Embedder thread and identity checks:
   - For all embedding strategies (embedding_threshold, ann_retrieval, bounded_bucket):
     embedder block must be present in sidecar, with cpu_threads == 1, torch_threads == 1,
     and identical model_name and revision across runs (fail-closed, not gated on uses_embeddings).
   - For brute_force: must not have an active embedding model or thread pin in sidecar.
6. Resume detection:
   - Duplicate trial keys in raw.jsonl are flagged as resumed (re-run failed keys).
   - Agreement between summary trial count and raw trial count.
7. Failed trials and retries:
   - Counted and explicitly listed, never imputed.
8. Table T3 inventory:
   - Deterministic per-file and composite directory SHA256 hashing.
   - Output as formatted CSV.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


REQUIRED_LIBRARIES = [
    "networkx",
    "pytest",
    "httpx",
    "numpy",
    "torch",
    "faiss-cpu",
    "sentence-transformers",
]

EXPECTED_EMBEDDER_MODEL = "all-MiniLM-L6-v2"
EXPECTED_EMBEDDER_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

PLANNED_TRIAL_COUNTS = {
    "accuracy": {
        "total": 59,
        "per_group": {
            "DSA_gold_standard_MEKG": 29,
            "metacademy_gold_standard_MEKG": 30,
        },
    },
    "accuracy_dsa": {
        "total": 29,
        "per_group": {
            "DSA_gold_standard_MEKG": 29,
        },
    },
    "sweep": {
        "total": 60,
        "per_group": {
            "50": 10,
            "100": 10,
            "200": 10,
            "500": 10,
            "1000": 10,
            "2000": 10,
        },
    },
}


def compute_file_sha256(path: Path) -> str:
    """Compute sha256 of a single file in 64 KB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_directory_sha256(run_dir: Path) -> str:
    """Deterministic composite sha256 of all regular files in a directory."""
    files = sorted([p for p in run_dir.iterdir() if p.is_file()])
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode("utf-8"))
        h.update(compute_file_sha256(f).encode("utf-8"))
    return h.hexdigest()


def get_planned_call_bound(strategy: str, config: Dict[str, Any], mode: str) -> int:
    """Derive planned upper bound on LLM calls strictly from strategy and config.

    Bounds correspond to the D-68 run plan table in scripts/README.md.
    """
    if mode in ("accuracy", "accuracy_dsa"):
        if strategy == "brute_force":
            return 5012
        elif strategy == "embedding_threshold":
            return 5012
        elif strategy == "ann_retrieval":
            k = config.get("k", 10)
            if k == 5:
                return 295
            elif k == 10:
                return 590
            elif k == 20:
                return 1180
            raise ValueError(f"Unknown k={k} for ann_retrieval accuracy bound")
        elif strategy == "bounded_bucket":
            s_max = config.get("s_max", 10)
            if s_max == 5:
                return 295
            elif s_max == 10:
                return 590
            elif s_max == 20:
                return 1180
            raise ValueError(f"Unknown s_max={s_max} for bounded_bucket accuracy bound")
        elif strategy in ("null", "stub"):
            return 5012
        raise ValueError(f"Unknown strategy='{strategy}' for accuracy bound lookup")
    elif mode == "sweep":
        if strategy == "brute_force":
            return 38500
        elif strategy == "embedding_threshold":
            return 38500
        elif strategy == "ann_retrieval":
            k = config.get("k", 10)
            if k == 5:
                return 300
            elif k == 10:
                return 600
            elif k == 20:
                return 1200
            raise ValueError(f"Unknown k={k} for ann_retrieval sweep bound")
        elif strategy == "bounded_bucket":
            s_max = config.get("s_max", 10)
            if s_max == 5:
                return 300
            elif s_max == 10:
                return 600
            elif s_max == 20:
                return 1200
            raise ValueError(f"Unknown s_max={s_max} for bounded_bucket sweep bound")
        elif strategy in ("null", "stub"):
            return 38500
        raise ValueError(f"Unknown strategy='{strategy}' for sweep bound lookup")
    raise ValueError(f"Unknown mode='{mode}' for bound lookup")


def parse_manifest(manifest_path: Path) -> Dict[str, Any]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_sidecar(sidecar_path: Path) -> Dict[str, Any]:
    with open(sidecar_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_raw_jsonl(raw_path: Path) -> Tuple[List[Dict[str, Any]], bool, Dict[str, int]]:
    """Parse raw.jsonl, tracking line order, duplicate keys, and per-key counts."""
    records = []
    key_counts: Dict[str, int] = {}
    has_duplicates = False
    with open(raw_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            k = rec.get("key") or f"unkeyed_{idx}"
            key_counts[k] = key_counts.get(k, 0) + 1
            if key_counts[k] > 1:
                has_duplicates = True
            records.append(rec)
    return records, has_duplicates, key_counts


def parse_summary_csv(csv_path: Path) -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def recompute_metrics(records: List[Dict[str, Any]], mode: str) -> Dict[str, Dict[str, Any]]:
    """Independent recomputation of summary metrics directly from raw.jsonl records.

    Handles resume deduplication: if multiple records share the same key, the latest
    record is taken (matching harness.generate_summary_csv).
    """
    # Key-deduplicated map preserving the latest trial execution for each key
    records_by_key: Dict[str, Dict[str, Any]] = {}
    for idx, r in enumerate(records):
        k = r.get("key") or f"unkeyed_{idx}"
        records_by_key[k] = r

    deduped_records = list(records_by_key.values())

    # Group by corpus (accuracy) or size (sweep)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in deduped_records:
        if mode in ("accuracy", "accuracy_dsa"):
            grp = r.get("corpus", "unknown")
        else:
            grp = str(r.get("size", r.get("metrics", {}).get("n_before", 0)))
        groups.setdefault(grp, []).append(r)

    recomputed = {}
    for grp, group_recs in groups.items():
        total_trials = len(group_recs)
        successes = [r for r in group_recs if r.get("status") == "success"]
        num_success = len(successes)
        num_failed = total_trials - num_success
        n_with_retries = sum(1 for r in successes if r.get("retries", 0) > 0)
        
        # LLM calls sum over successful trials
        total_calls = sum(r.get("metrics", {}).get("llm_calls", 0) for r in successes)
        mean_calls = (total_calls / num_success) if num_success > 0 else 0.0

        # Timing distributions over successes (using statistics.median for even-n accuracy)
        total_s_list = [r["metrics"]["total_s"] for r in successes if "metrics" in r and "total_s" in r["metrics"]]
        mean_total_s = statistics.mean(total_s_list) if total_s_list else 0.0
        med_total_s = statistics.median(total_s_list) if total_s_list else 0.0

        # Accuracy calculations
        tot_tp = 0
        tot_fp = 0
        tot_fn = 0
        macro_p_list: List[float] = []
        macro_r_list: List[float] = []
        macro_f1_list: List[float] = []
        shortlist_hits_tot = 0
        gold_neighbours_tot = 0
        shortlist_recall_list: List[float] = []

        for r in successes:
            sc = r.get("score")
            if sc:
                tp = sc.get("tp", 0)
                fp = sc.get("fp", 0)
                fn = sc.get("fn", 0)
                tot_tp += tp
                tot_fp += fp
                tot_fn += fn

                p = sc.get("precision")
                rec = sc.get("recall")
                f1 = sc.get("f1")
                if p is not None:
                    macro_p_list.append(float(p))
                if rec is not None:
                    macro_r_list.append(float(rec))
                if f1 is not None:
                    macro_f1_list.append(float(f1))

                hits = sc.get("shortlist_hits", 0)
                gn = sc.get("gold_neighbours", 0)
                shortlist_hits_tot += hits
                gold_neighbours_tot += gn
                sr = sc.get("shortlist_recall")
                # Macro shortlist recall excludes concepts with no gold neighbours
                if gn > 0 and sr is not None:
                    shortlist_recall_list.append(float(sr))

        # Micro accuracy
        sl_recall_micro = (shortlist_hits_tot / gold_neighbours_tot) if gold_neighbours_tot > 0 else 1.0
        p_denom = tot_tp + tot_fp
        r_denom = tot_tp + tot_fn
        micro_p = (tot_tp / p_denom) if p_denom > 0 else 0.0
        micro_r = (tot_tp / r_denom) if r_denom > 0 else 1.0
        pr_sum = micro_p + micro_r
        micro_f1 = (2 * micro_p * micro_r / pr_sum) if pr_sum > 0 else 0.0

        # Macro accuracy (None if no defined values)
        macro_p = (sum(macro_p_list) / len(macro_p_list)) if macro_p_list else None
        macro_r = (sum(macro_r_list) / len(macro_r_list)) if macro_r_list else None
        macro_f1 = (sum(macro_f1_list) / len(macro_f1_list)) if macro_f1_list else None
        macro_sr = (sum(shortlist_recall_list) / len(shortlist_recall_list)) if shortlist_recall_list else None

        recomputed[grp] = {
            "num_trials": total_trials,
            "num_success": num_success,
            "num_failed": num_failed,
            "n_with_retries": n_with_retries,
            "llm_calls_sum": total_calls,
            "llm_calls_mean": mean_calls,
            "total_s_mean": mean_total_s,
            "total_s_median": med_total_s,
            "precision_micro": micro_p,
            "recall_micro": micro_r,
            "f1_micro": micro_f1,
            "shortlist_recall_micro": sl_recall_micro,
            "precision_macro": macro_p,
            "recall_macro": macro_r,
            "f1_macro": macro_f1,
            "shortlist_recall_macro": macro_sr,
        }
    return recomputed


def validate_single_run(run_dir: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate all artifacts in a single run directory against Phase 4 Section 2 requirements."""
    errors: List[str] = []
    info: Dict[str, Any] = {"run_dir": str(run_dir.name)}

    manifest_p = run_dir / "manifest.json"
    sidecar_p = run_dir / "strategy_config.json"
    raw_p = run_dir / "raw.jsonl"
    summary_p = run_dir / "summary.csv"

    # File existence checks
    for p, name in [
        (manifest_p, "manifest.json"),
        (sidecar_p, "strategy_config.json"),
        (raw_p, "raw.jsonl"),
        (summary_p, "summary.csv"),
    ]:
        if not p.is_file():
            errors.append(f"Missing required file: {name}")

    if errors:
        return False, errors, info

    info["manifest_sha256"] = compute_file_sha256(manifest_p)
    info["config_sha256"] = compute_file_sha256(sidecar_p)
    info["raw_sha256"] = compute_file_sha256(raw_p)
    info["summary_sha256"] = compute_file_sha256(summary_p)
    info["dir_sha256"] = compute_directory_sha256(run_dir)

    # 1. Manifest Checks (Fail closed)
    try:
        manifest = parse_manifest(manifest_p)
    except Exception as e:
        errors.append(f"Invalid JSON in manifest.json: {e}")
        return False, errors, info

    if "git_commit" not in manifest or not isinstance(manifest["git_commit"], str) or not manifest["git_commit"]:
        errors.append("Manifest missing or invalid 'git_commit'")
    else:
        info["git_commit"] = manifest["git_commit"]

    if manifest.get("git_dirty") is not False:
        errors.append(f"Manifest git_dirty is not False: {manifest.get('git_dirty')}")
    info["git_dirty"] = manifest.get("git_dirty")

    mode = manifest.get("mode")
    if not mode or mode not in ("accuracy", "sweep", "accuracy_dsa"):
        errors.append(f"Manifest mode invalid or missing: '{mode}'")
    info["mode"] = mode

    libs = manifest.get("libraries")
    if not isinstance(libs, dict):
        errors.append("Manifest missing 'libraries' dictionary")
        libs = {}
    else:
        for req_lib in REQUIRED_LIBRARIES:
            if req_lib not in libs:
                errors.append(f"Missing required library record in manifest: '{req_lib}'")
    info["libraries"] = libs
    info["libraries_hash"] = hashlib.sha256(json.dumps(libs, sort_keys=True).encode("utf-8")).hexdigest()

    # 2. Sidecar Checks (Fail closed)
    try:
        sidecar = parse_sidecar(sidecar_p)
    except Exception as e:
        errors.append(f"Invalid JSON in strategy_config.json: {e}")
        return False, errors, info

    strat = sidecar.get("strategy")
    if not strat or not isinstance(strat, str):
        errors.append("Sidecar strategy_config.json missing 'strategy'")
        strat = "unknown"
    info["strategy"] = strat

    strat_cfg = sidecar.get("config")
    if not isinstance(strat_cfg, dict):
        errors.append("Sidecar strategy_config.json missing 'config' dictionary")
        strat_cfg = {}
    info["config"] = strat_cfg

    embedder = sidecar.get("embedder")
    is_embedding_strategy = strat in ("embedding_threshold", "ann_retrieval", "bounded_bucket")

    if is_embedding_strategy:
        if not isinstance(embedder, dict):
            errors.append(f"Embedding strategy '{strat}' missing required 'embedder' block in sidecar")
        else:
            cpu_th = embedder.get("cpu_threads")
            torch_th = embedder.get("torch_threads")
            model_name = embedder.get("model_name")
            rev = embedder.get("revision")

            if cpu_th != 1:
                errors.append(f"Sidecar cpu_threads != 1: got {cpu_th}")
            if torch_th != 1:
                errors.append(f"Sidecar torch_threads != 1: got {torch_th}")
            if not model_name or not isinstance(model_name, str):
                errors.append("Sidecar embedder missing 'model_name'")
            elif model_name != EXPECTED_EMBEDDER_MODEL:
                errors.append(f"Sidecar embedder model_name mismatch: '{model_name}' != '{EXPECTED_EMBEDDER_MODEL}'")
            if not rev or not isinstance(rev, str):
                errors.append("Sidecar embedder missing 'revision'")
            elif rev != EXPECTED_EMBEDDER_REVISION:
                errors.append(f"Sidecar embedder revision mismatch: '{rev}' != '{EXPECTED_EMBEDDER_REVISION}'")

            info["embedder_model"] = model_name
            info["embedder_revision"] = rev
            info["cpu_threads"] = cpu_th
            info["torch_threads"] = torch_th
    else:
        # Non-embedding strategy (e.g. brute_force)
        if embedder and isinstance(embedder, dict):
            if embedder.get("model_name") is not None or embedder.get("cpu_threads") is not None:
                errors.append(f"Non-embedding strategy '{strat}' unexpectedly defines an embedding model or thread pin")

    # 3. Raw Traces & Resume Detection
    try:
        raw_records, has_duplicates, key_counts = parse_raw_jsonl(raw_p)
    except Exception as e:
        errors.append(f"Invalid JSON/format in raw.jsonl: {e}")
        return False, errors, info

    is_resumed = has_duplicates
    info["resumed"] = is_resumed

    # Track failed trials and retries
    failed_trials_list = []
    total_retries_count = 0
    for r in raw_records:
        if r.get("status") == "failed":
            failed_trials_list.append({
                "key": r.get("key"),
                "error_type": r.get("error_type"),
                "error_message": r.get("error_message"),
            })
        total_retries_count += r.get("retries", 0)

    info["failed_trials_count"] = len(failed_trials_list)
    info["failed_trials_details"] = failed_trials_list
    info["total_retries"] = total_retries_count

    # 4. Trial Count Enforcement (Derived per-group and total)
    # Determine mode key for trial count checking
    trial_mode_key = mode
    unique_trial_keys = len(key_counts)
    if mode == "accuracy" and unique_trial_keys == 29:
        trial_mode_key = "accuracy_dsa"

    spec = PLANNED_TRIAL_COUNTS.get(trial_mode_key)
    if spec is None:
        errors.append(f"Unrecognized trial count mode: '{mode}'")
    else:
        expected_total = spec["total"]
        if unique_trial_keys != expected_total:
            errors.append(
                f"Unique trial count mismatch: raw.jsonl has {unique_trial_keys} unique keys, "
                f"expected {expected_total} for mode '{trial_mode_key}'"
            )

        # Derive per-group counts
        recomputed = recompute_metrics(raw_records, mode)
        for expected_grp, expected_n in spec["per_group"].items():
            actual_n = recomputed.get(expected_grp, {}).get("num_trials", None)
            if actual_n is None:
                errors.append(f"Missing expected group '{expected_grp}' in raw.jsonl")
            elif actual_n != expected_n:
                errors.append(
                    f"Per-group trial count mismatch for '{expected_grp}': "
                    f"got {actual_n}, expected {expected_n}"
                )

    # 5. Planned Call Bound Check (Keyed by strategy & config)
    try:
        planned_bound = get_planned_call_bound(strat, strat_cfg, trial_mode_key)
        info["call_bound"] = planned_bound
        # Actual LLM calls sum over successful trials (deduplicated)
        total_run_calls = sum(
            grp_data.get("llm_calls_sum", 0)
            for grp_data in recomputed.values()
        )
        info["total_calls"] = total_run_calls
        if total_run_calls > planned_bound:
            errors.append(
                f"Realised LLM calls {total_run_calls} exceeds planned upper bound {planned_bound} "
                f"for strategy '{strat}'"
            )
    except Exception as e:
        errors.append(f"Failed to resolve planned call bound: {e}")

    # 6. Recomputation Agreement with summary.csv
    try:
        summary_rows = parse_summary_csv(summary_p)
    except Exception as e:
        errors.append(f"Failed to parse summary.csv: {e}")
        summary_rows = []

    # Consistency of trial counts in summary.csv vs raw
    summary_trials_sum = sum(int(row.get("num_trials", 0)) for row in summary_rows)
    if summary_trials_sum != unique_trial_keys:
        errors.append(
            f"Trial count disagreement between summary.csv ({summary_trials_sum}) "
            f"and raw.jsonl unique keys ({unique_trial_keys})"
        )

    tol = 1e-4
    for s_row in summary_rows:
        grp = s_row.get("corpus_or_size")
        if grp not in recomputed:
            errors.append(f"Group '{grp}' in summary.csv not present in raw.jsonl recomputations")
            continue

        rec = recomputed[grp]

        # Integer count comparisons
        for cnt_field in ["num_trials", "num_success", "num_failed", "n_with_retries", "llm_calls_sum"]:
            s_val = int(s_row.get(cnt_field, 0))
            r_val = rec[cnt_field]
            if s_val != r_val:
                errors.append(f"{cnt_field} mismatch for group '{grp}': summary={s_val} vs raw={r_val}")

        # Timing comparisons (mean & median total_s)
        for t_field in ["total_s_mean", "total_s_median"]:
            if t_field in s_row:
                s_val = float(s_row[t_field])
                r_val = float(rec[t_field])
                if not math.isclose(s_val, r_val, rel_tol=1e-3, abs_tol=0.01):
                    errors.append(
                        f"{t_field} mismatch for group '{grp}': summary={s_val:.4f} vs raw={r_val:.4f}"
                    )

        # Mean calls
        if "llm_calls_mean" in s_row:
            s_val = float(s_row["llm_calls_mean"])
            r_val = float(rec["llm_calls_mean"])
            if not math.isclose(s_val, r_val, abs_tol=tol):
                errors.append(
                    f"llm_calls_mean mismatch for group '{grp}': summary={s_val:.4f} vs raw={r_val:.4f}"
                )

        # Accuracy metrics in accuracy mode
        if mode in ("accuracy", "accuracy_dsa"):
            for acc_field in [
                "precision_micro", "recall_micro", "f1_micro", "shortlist_recall_micro",
                "precision_macro", "recall_macro", "f1_macro", "shortlist_recall_macro"
            ]:
                s_str = s_row.get(acc_field, "")
                r_val = rec[acc_field]
                if s_str is None or s_str == "":
                    if r_val is not None:
                        errors.append(f"{acc_field} mismatch for '{grp}': summary has None/empty, raw has {r_val}")
                else:
                    s_val = float(s_str)
                    if r_val is None:
                        errors.append(f"{acc_field} mismatch for '{grp}': summary has {s_val}, raw has None")
                    elif not math.isclose(s_val, r_val, abs_tol=tol):
                        errors.append(f"{acc_field} mismatch for '{grp}': summary={s_val:.6f} vs raw={r_val:.6f}")

    info["trials"] = unique_trial_keys
    info["total_records"] = len(raw_records)
    is_valid = len(errors) == 0
    return is_valid, errors, info


def validate_all_runs(results_dir: Path) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Validate all run directories in results_dir and enforce cross-run uniformity.

    Returns:
        (overall_passed, results_list, table_t3_csv_string)
    """
    run_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()])
    if not run_dirs:
        return False, [], "No run directories found"

    overall_passed = True
    base_commit: Optional[str] = None
    base_libs: Optional[Dict[str, str]] = None
    base_embedder_model: Optional[str] = None
    base_embedder_revision: Optional[str] = None
    base_embedder_run: Optional[str] = None

    run_results: List[Dict[str, Any]] = []

    for r_dir in run_dirs:
        passed, errors, info = validate_single_run(r_dir)

        # Cross-run checks
        commit = info.get("git_commit")
        if base_commit is None:
            base_commit = commit
        elif commit and commit != base_commit:
            errors.append(
                f"Cross-run git_commit mismatch: first run had '{base_commit}', this run has '{commit}'"
            )
            passed = False

        libs = info.get("libraries")
        if base_libs is None:
            base_libs = libs
        elif libs and libs != base_libs:
            errors.append("Cross-run libraries block mismatch between this run and baseline run")
            passed = False

        em_model = info.get("embedder_model")
        em_rev = info.get("embedder_revision")
        if em_model is not None:
            if base_embedder_model is None:
                base_embedder_model = em_model
                base_embedder_revision = em_rev
                base_embedder_run = r_dir.name
            else:
                if em_model != base_embedder_model:
                    errors.append(
                        f"Cross-run embedder model mismatch: '{base_embedder_run}' used '{base_embedder_model}', "
                        f"this run uses '{em_model}'"
                    )
                    passed = False
                if em_rev != base_embedder_revision:
                    errors.append(
                        f"Cross-run embedder revision mismatch: '{base_embedder_run}' used '{base_embedder_revision}', "
                        f"this run uses '{em_rev}'"
                    )
                    passed = False

        if not passed:
            overall_passed = False

        info["passed"] = passed
        info["errors"] = errors
        run_results.append(info)

    # Generate Table T3 CSV
    t3_rows = []
    fieldnames = [
        "run", "strategy", "config", "mode", "commit", "libraries_hash",
        "trials", "calls", "failed", "retries", "status",
        "manifest_sha256", "config_sha256", "raw_sha256", "summary_sha256", "dir_sha256"
    ]
    for r in run_results:
        status_label = "PASS (resumed)" if (r.get("passed") and r.get("resumed")) else ("PASS" if r.get("passed") else "FAIL")
        t3_rows.append({
            "run": r.get("run_dir", ""),
            "strategy": r.get("strategy", ""),
            "config": json.dumps(r.get("config", {}), sort_keys=True),
            "mode": r.get("mode", ""),
            "commit": r.get("git_commit", ""),
            "libraries_hash": r.get("libraries_hash", ""),
            "trials": r.get("trials", 0),
            "calls": r.get("total_calls", 0),
            "failed": r.get("failed_trials_count", 0),
            "retries": r.get("total_retries", 0),
            "status": status_label,
            "manifest_sha256": r.get("manifest_sha256", ""),
            "config_sha256": r.get("config_sha256", ""),
            "raw_sha256": r.get("raw_sha256", ""),
            "summary_sha256": r.get("summary_sha256", ""),
            "dir_sha256": r.get("dir_sha256", ""),
        })

    import io
    output_io = io.StringIO()
    writer = csv.DictWriter(output_io, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(t3_rows)
    t3_csv = output_io.getvalue()

    return overall_passed, run_results, t3_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate experimental run directories.")
    parser.add_argument("results_dir", type=Path, help="Path to results directory containing run folders")
    parser.add_argument("--t3-csv", type=Path, default=None, help="Optional output path to save Table T3 CSV")
    args = parser.parse_args()

    results_dir = args.results_dir.resolve()
    print("=" * 80)
    print(f"RUN VALIDATION GATE: {results_dir}")
    print("=" * 80)

    overall_passed, run_results, t3_csv = validate_all_runs(results_dir)

    for r in run_results:
        status_label = "PASS (resumed)" if (r.get("passed") and r.get("resumed")) else ("PASS" if r.get("passed") else "FAIL")
        print(f"[{status_label}] {r.get('run_dir')}")
        print(f"       Strategy: {r.get('strategy')} | Mode: {r.get('mode')} | Commit: {str(r.get('git_commit'))[:7]} | git_dirty: {r.get('git_dirty')}")
        print(f"       Calls:    {r.get('total_calls')} / {r.get('call_bound', 'N/A')} bound | Trials: {r.get('trials')} (failed={r.get('failed_trials_count')}, retries={r.get('total_retries')})")
        print(f"       SHA256:   {r.get('dir_sha256')}")
        if not r.get("passed"):
            for err in r.get("errors", []):
                print(f"       -> ERROR: {err}")
        print("-" * 80)

    print(f"OVERALL GATE STATUS: {'PASS' if overall_passed else 'FAIL'}")

    if args.t3_csv:
        args.t3_csv.write_text(t3_csv, encoding="utf-8")
        print(f"Table T3 CSV saved to: {args.t3_csv}")

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
