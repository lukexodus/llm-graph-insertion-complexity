"""
tests/test_analysis_validate_runs.py
====================================
Comprehensive test suite and executed corruption/mutation matrix for
scripts.analysis.validate_runs.

Meets all requirements of TASK ANALYSIS-001 and ANALYSIS-001-F:
- Builds completely synthetic fixtures in tmp_path (no dependence on ~ or results/).
- Tests both accuracy and sweep mode synthetic fixtures.
- Comprehensive corruption table testing every single gate check.
- Standard library + pytest only.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from scripts.analysis.validate_runs import (
    EXPECTED_EMBEDDER_MODEL,
    EXPECTED_EMBEDDER_REVISION,
    REQUIRED_LIBRARIES,
    build_strategy_slug,
    compute_directory_sha256,
    compute_file_sha256,
    derive_expected_run_id,
    get_planned_call_bound,
    parse_hashes_file,
    validate_all_runs,
    validate_single_run,
)


BASE_COMMIT = "3323bfbd03b6490aeef2d864b9d77271bd9a340e"
BASE_LIBRARIES = {lib: "1.0.0" for lib in REQUIRED_LIBRARIES}


def create_synthetic_accuracy_run(
    dest_dir: Path,
    strategy: str = "ann_retrieval",
    config: Optional[Dict[str, Any]] = None,
    git_commit: str = BASE_COMMIT,
    git_dirty: bool = False,
    libraries: Optional[Dict[str, str]] = None,
    cpu_threads: int = 1,
    torch_threads: int = 1,
    embedder_model: Optional[str] = EXPECTED_EMBEDDER_MODEL,
    embedder_revision: Optional[str] = EXPECTED_EMBEDDER_REVISION,
    dsa_trials: int = 29,
    metacademy_trials: int = 30,
    calls_per_trial: int = 5,
    total_s_per_trial: float = 1.0,
    has_duplicates: bool = False,
    duplicate_success: bool = False,
    embedder_block_override: Optional[Dict[str, Any]] = None,
) -> Path:
    """Generate a valid, fully synthetic accuracy experiment run directory in tmp_path."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    if config is None:
        if strategy == "ann_retrieval":
            config = {"k": 10, "ef_search": 128, "seed": 42}
        elif strategy == "bounded_bucket":
            config = {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
        elif strategy == "embedding_threshold":
            config = {"theta": 0.6, "seed": 42}
        elif strategy == "brute_force":
            config = {"seed": 42}
        else:
            config = {"seed": 42}

    if libraries is None:
        libraries = dict(BASE_LIBRARIES)

    # 1. manifest.json
    manifest = {
        "run_id": dest_dir.name,
        "mode": "accuracy",
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "python_version": "3.14.7",
        "libraries": libraries,
    }
    (dest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 2. strategy_config.json
    sidecar: Dict[str, Any] = {
        "strategy": strategy,
        "config": config,
        "mode": "accuracy",
    }
    if embedder_block_override is not None:
        if embedder_block_override:
            sidecar["embedder"] = embedder_block_override
    else:
        if strategy in ("embedding_threshold", "ann_retrieval", "bounded_bucket"):
            sidecar["embedder"] = {
                "type": "minilm",
                "uses_embeddings": True,
                "model_name": embedder_model,
                "revision": embedder_revision,
                "cpu_threads": cpu_threads,
                "torch_threads": torch_threads,
            }
        else:
            sidecar["embedder"] = None
    (dest_dir / "strategy_config.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    # 3. raw.jsonl
    raw_lines = []
    groups = [
        ("DSA_gold_standard_MEKG", dsa_trials),
        ("metacademy_gold_standard_MEKG", metacademy_trials),
    ]

    for corpus, n_trials in groups:
        for i in range(n_trials):
            key = f"accuracy:{strategy}:{corpus}:node_{i}:r0"
            rec = {
                "key": key,
                "strategy": strategy,
                "corpus": corpus,
                "status": "success",
                "retries": 0,
                "metrics": {
                    "llm_calls": calls_per_trial,
                    "total_s": total_s_per_trial + (i * 0.1),
                    "shortlist_s": 0.2,
                    "decide_s": 0.7,
                    "apply_s": 0.05,
                    "update_s": 0.05,
                },
                "score": {
                    "node": f"node_{i}",
                    "tp": 2,
                    "fp": 1,
                    "fn": 1,
                    "gold_positives": 3,
                    "gold_neighbours": 2,
                    "shortlist_hits": 2,
                    "shortlist_recall": 1.0,
                    "precision": 2 / 3,
                    "recall": 2 / 3,
                    "f1": 2 / 3,
                },
            }
            raw_lines.append(json.dumps(rec))

    if has_duplicates and raw_lines:
        # Legitimate resume retry: first execution was a failure, second was success
        target_key = f"accuracy:{strategy}:DSA_gold_standard_MEKG:node_0:r0"
        failed_rec = {
            "key": target_key,
            "strategy": strategy,
            "corpus": "DSA_gold_standard_MEKG",
            "status": "failed",
            "error_type": "APITimeoutError",
            "error_message": "Request timed out",
            "retries": 2,
        }
        # Insert failure at front
        raw_lines.insert(0, json.dumps(failed_rec))

    if duplicate_success and raw_lines:
        # Corrupt duplicate: append an identical success record
        raw_lines.append(raw_lines[0])

    (dest_dir / "raw.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")

    # 4. summary.csv
    summary_rows = []
    fieldnames = [
        "strategy", "mode", "corpus_or_size", "num_trials", "num_success", "num_failed",
        "n_with_retries", "n", "total_s_mean", "total_s_median", "llm_calls_sum", "llm_calls_mean",
        "precision_micro", "recall_micro", "f1_micro", "shortlist_recall_micro",
        "precision_macro", "recall_macro", "f1_macro", "shortlist_recall_macro"
    ]

    for corpus, n_trials in groups:
        if n_trials == 0:
            continue
        tot_s_vals = [total_s_per_trial + (i * 0.1) for i in range(n_trials)]
        summary_rows.append({
            "strategy": strategy,
            "mode": "accuracy",
            "corpus_or_size": corpus,
            "num_trials": str(n_trials),
            "num_success": str(n_trials),
            "num_failed": "0",
            "n_with_retries": "0",
            "n": "50",
            "total_s_mean": f"{statistics.mean(tot_s_vals):.6f}",
            "total_s_median": f"{statistics.median(tot_s_vals):.6f}",
            "llm_calls_sum": str(n_trials * calls_per_trial),
            "llm_calls_mean": f"{calls_per_trial:.4f}",
            "precision_micro": f"{(2 / 3):.6f}",
            "recall_micro": f"{(2 / 3):.6f}",
            "f1_micro": f"{(2 / 3):.6f}",
            "shortlist_recall_micro": "1.000000",
            "precision_macro": f"{(2 / 3):.6f}",
            "recall_macro": f"{(2 / 3):.6f}",
            "f1_macro": f"{(2 / 3):.6f}",
            "shortlist_recall_macro": "1.000000",
        })

    with open(dest_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    return dest_dir


def create_synthetic_sweep_run(
    dest_dir: Path,
    strategy: str = "ann_retrieval",
    config: Optional[Dict[str, Any]] = None,
    git_commit: str = BASE_COMMIT,
    git_dirty: bool = False,
    libraries: Optional[Dict[str, str]] = None,
    sizes: Optional[List[int]] = None,
    trials_per_size: int = 10,
    calls_per_trial: int = 1,
    cpu_threads: int = 1,
    torch_threads: int = 1,
    embedder_model: Optional[str] = EXPECTED_EMBEDDER_MODEL,
    embedder_revision: Optional[str] = EXPECTED_EMBEDDER_REVISION,
    embedder_block_override: Optional[Dict[str, Any]] = None,
    duplicate_success: bool = False,
) -> Path:
    """Generate a valid, fully synthetic sweep experiment run directory in tmp_path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if sizes is None:
        sizes = [50, 100, 200, 500, 1000, 2000]
    if config is None:
        if strategy == "ann_retrieval":
            config = {"k": 10, "ef_search": 128, "seed": 42}
        elif strategy == "bounded_bucket":
            config = {"s_min": 5, "s_max": 10, "n_bits": 12, "seed": 42}
        elif strategy == "embedding_threshold":
            config = {"theta": 0.6, "seed": 42}
        elif strategy == "brute_force":
            config = {"seed": 42}
        else:
            config = {"seed": 42}

    if libraries is None:
        libraries = dict(BASE_LIBRARIES)

    manifest = {
        "run_id": dest_dir.name,
        "mode": "sweep",
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "python_version": "3.14.7",
        "libraries": libraries,
    }
    (dest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    sidecar: Dict[str, Any] = {
        "strategy": strategy,
        "config": config,
        "mode": "sweep",
    }
    if embedder_block_override is not None:
        if embedder_block_override:
            sidecar["embedder"] = embedder_block_override
    else:
        if strategy in ("embedding_threshold", "ann_retrieval", "bounded_bucket"):
            sidecar["embedder"] = {
                "type": "minilm",
                "uses_embeddings": True,
                "model_name": embedder_model,
                "revision": embedder_revision,
                "cpu_threads": cpu_threads,
                "torch_threads": torch_threads,
            }
        else:
            sidecar["embedder"] = None

    (dest_dir / "strategy_config.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    raw_lines = []
    summary_rows = []
    fieldnames = [
        "strategy", "mode", "corpus_or_size", "num_trials", "num_success", "num_failed",
        "n_with_retries", "n", "total_s_mean", "total_s_median", "llm_calls_sum", "llm_calls_mean"
    ]

    for sz in sizes:
        tot_s_vals = []
        for i in range(trials_per_size):
            t_s = 0.5 + (i * 0.05)
            tot_s_vals.append(t_s)
            key = f"sweep:{strategy}:{sz}:t{i}"
            rec = {
                "key": key,
                "strategy": strategy,
                "size": sz,
                "status": "success",
                "retries": 0,
                "metrics": {
                    "llm_calls": calls_per_trial,
                    "total_s": t_s,
                    "shortlist_s": 0.1,
                    "decide_s": 0.3,
                    "apply_s": 0.05,
                    "update_s": 0.05,
                    "n_before": sz,
                },
            }
            raw_lines.append(json.dumps(rec))

        summary_rows.append({
            "strategy": strategy,
            "mode": "sweep",
            "corpus_or_size": str(sz),
            "num_trials": str(trials_per_size),
            "num_success": str(trials_per_size),
            "num_failed": "0",
            "n_with_retries": "0",
            "n": str(sz),
            "total_s_mean": f"{statistics.mean(tot_s_vals):.6f}",
            "total_s_median": f"{statistics.median(tot_s_vals):.6f}",
            "llm_calls_sum": str(trials_per_size * calls_per_trial),
            "llm_calls_mean": f"{calls_per_trial:.4f}",
        })

    if duplicate_success and raw_lines:
        raw_lines.append(raw_lines[0])

    (dest_dir / "raw.jsonl").write_text("\n".join(raw_lines) + "\n", encoding="utf-8")

    with open(dest_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    return dest_dir


# ============================================================================
# Unit Tests & Corruption Matrix
# ============================================================================

def test_baseline_control_accuracy(tmp_path: Path):
    """Baseline Control 1: Clean synthetic accuracy run must PASS."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    passed, errors, info = validate_single_run(run_dir)
    assert passed, f"Baseline accuracy control unexpectedly failed: {errors}"
    assert errors == []
    assert info["trials"] == 59
    assert info["total_calls"] == 59 * 5
    assert not info["resumed"]


def test_baseline_control_sweep(tmp_path: Path):
    """Baseline Control 2: Clean synthetic sweep run must PASS."""
    run_dir = tmp_path / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_sweep_run(run_dir)
    passed, errors, info = validate_single_run(run_dir)
    assert passed, f"Baseline sweep control unexpectedly failed: {errors}"
    assert errors == []
    assert info["trials"] == 60
    assert info["total_calls"] == 60


def test_mutant_git_dirty_true(tmp_path: Path):
    """Mutant 1: manifest git_dirty is True."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, git_dirty=True)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("git_dirty is not False" in e for e in errors)


def test_mutant_cross_run_commit_mismatch(tmp_path: Path):
    """Mutant 2: git_commit mismatch within a mode (accuracy)."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run2 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run1, config={"k": 10, "ef_search": 128}, git_commit=BASE_COMMIT)
    create_synthetic_accuracy_run(run2, config={"k": 5, "ef_search": 128}, git_commit="0000000000000000000000000000000000000000")

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    assert any(any("Intra-mode git_commit mismatch" in err for err in r.get("errors", [])) for r in results)


def test_cross_mode_commit_gate_requires_src_diff_clean(tmp_path: Path):
    """Requirement 1: Cross-mode commit mismatch fails without --src-diff-clean, passes with it."""
    results_dir = tmp_path / "results"
    run_acc = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run_swp = results_dir / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_acc, git_commit=BASE_COMMIT)
    create_synthetic_sweep_run(run_swp, git_commit="4444444444444444444444444444444444444444")

    # Fail closed without --src-diff-clean
    passed_fail, results_fail, _ = validate_all_runs(results_dir, src_diff_clean=False)
    assert not passed_fail
    assert any(any("Cross-mode git_commit mismatch" in err for err in r.get("errors", [])) for r in results_fail)

    # Pass when --src-diff-clean is provided
    passed_ok, results_ok, _ = validate_all_runs(results_dir, src_diff_clean=True)
    assert passed_ok
    assert all(len(r.get("errors", [])) == 0 for r in results_ok)


def test_mutant_cross_run_library_mismatch(tmp_path: Path):
    """Mutant 3: library versions mismatch across runs."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run2 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run1, config={"k": 10, "ef_search": 128})
    bad_libs = dict(BASE_LIBRARIES)
    bad_libs["torch"] = "9.9.9"
    create_synthetic_accuracy_run(run2, config={"k": 5, "ef_search": 128}, libraries=bad_libs)

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    assert any(any("Cross-run libraries block mismatch" in err for err in r.get("errors", [])) for r in results)


def test_mutant_cross_run_embedder_revision_mismatch(tmp_path: Path):
    """Mutant 4: embedder revision mismatch across two embedding runs."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run2 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run1, config={"k": 10, "ef_search": 128})
    create_synthetic_accuracy_run(run2, config={"k": 5, "ef_search": 128}, embedder_revision="badbadbadbadbadbadbadbadbadbadbadbadbadb")

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    all_errs = [e for r in results for e in r.get("errors", [])]
    assert any("revision mismatch" in e for e in all_errs)


def test_mutant_dir_name_vs_manifest_run_id_mismatch(tmp_path: Path):
    """Requirement 2: Directory name does not match manifest.json run_id."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    # Tamper manifest run_id
    manifest_p = run_dir / "manifest.json"
    data = json.loads(manifest_p.read_text(encoding="utf-8"))
    data["run_id"] = "accuracy_ann_retrieval_k5_ef128"
    manifest_p.write_text(json.dumps(data), encoding="utf-8")

    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("does not match manifest.json run_id" in e for e in errors)


def test_mutant_dir_name_vs_strategy_config_slug_mismatch(tmp_path: Path):
    """Requirement 2: Directory name does not match canonical strategy/config slug."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k5_ef128"
    # Create with k=10 configuration inside a k5 named directory
    create_synthetic_accuracy_run(run_dir, config={"k": 10, "ef_search": 128, "seed": 42})
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("does not match expected strategy/config slug" in e for e in errors)


def test_mutant_swapped_run_directories(tmp_path: Path):
    """Requirement 2: Swapping two run directories fails validation (Mutation h)."""
    results_dir = tmp_path / "results"
    run_k10 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run_k5 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run_k10, config={"k": 10, "ef_search": 128, "seed": 42})
    create_synthetic_accuracy_run(run_k5, config={"k": 5, "ef_search": 128, "seed": 42})

    # Swap directories on disk
    tmp_swap = results_dir / "tmp_swap"
    run_k10.rename(tmp_swap)
    run_k5.rename(run_k10)
    tmp_swap.rename(run_k5)

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    for r in results:
        assert not r["passed"]
        assert any("does not match" in err for err in r["errors"])


def test_mutant_duplicate_key_earlier_record_success(tmp_path: Path):
    """Requirement 3: Duplicate key whose earlier record is a success must fail."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, duplicate_success=True)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("earlier record at index 0 has status 'success'" in e for e in errors)


def test_failed_then_succeeded_vs_still_failed_accounting(tmp_path: Path):
    """Requirement 3: Separation of failed-then-succeeded and still-failed keys."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, has_duplicates=True)
    passed, errors, info = validate_single_run(run_dir)
    assert passed
    assert info["resumed"] is True
    assert info["failed_then_succeeded_count"] == 1
    assert info["still_failed_count"] == 0
    assert info["failed_then_succeeded_keys"] == ["accuracy:ann_retrieval:DSA_gold_standard_MEKG:node_0:r0"]


def test_zero_trial_resume_properties(tmp_path: Path):
    """Requirement 4: Verify zero-trial resume leaves no duplicate keys in raw.jsonl."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    passed, errors, info = validate_single_run(run_dir)
    assert passed
    # A completed run without duplicate keys is flagged as resumed=False
    assert not info["resumed"]
    assert info["failed_then_succeeded_count"] == 0
    assert info["still_failed_count"] == 0


def test_hashes_file_verification(tmp_path: Path):
    """Requirement 5: Optional --hashes argument verifies SHA256 against machine list."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)

    # 1. Baseline passing hash list
    hashes_file = tmp_path / "results-file-hashes.txt"
    lines = []
    for f in ["manifest.json", "strategy_config.json", "raw.jsonl", "summary.csv"]:
        sha = compute_file_sha256(run_dir / f)
        lines.append(f"{sha}  results/{run_dir.name}/{f}")
    hashes_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    passed, errors, _ = validate_single_run(run_dir, expected_hashes=parse_hashes_file(hashes_file))
    assert passed
    assert errors == []

    # 2. Mutant: tampered sha in hash file
    tampered_file = tmp_path / "tampered-hashes.txt"
    bad_lines = list(lines)
    bad_lines[2] = f"{'0' * 64}  results/{run_dir.name}/raw.jsonl"
    tampered_file.write_text("\n".join(bad_lines) + "\n", encoding="utf-8")

    passed_bad, errors_bad, _ = validate_single_run(run_dir, expected_hashes=parse_hashes_file(tampered_file))
    assert not passed_bad
    assert any("File SHA256 mismatch" in e for e in errors_bad)


def test_sweep_mutants_and_call_bounds(tmp_path: Path):
    """Requirement 6: Sweep negative tests (wrong trial count, call bound, thread pins)."""
    # 1. Wrong trial count (59 trials instead of 60)
    run_dir1 = tmp_path / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_sweep_run(run_dir1, trials_per_size=10, sizes=[50, 100, 200, 500, 1000]) # 5 sizes = 50 trials
    passed1, errors1, _ = validate_single_run(run_dir1)
    assert not passed1
    assert any("Unique trial count mismatch" in e for e in errors1)

    # 2. Call bounds violations
    # ann_retrieval k=10 bound is 600. 60 trials * 11 calls = 660 calls
    run_dir2 = tmp_path / "run_bound_k10" / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_sweep_run(run_dir2, strategy="ann_retrieval", config={"k": 10, "ef_search": 128, "seed": 42}, calls_per_trial=11)
    passed2, errors2, _ = validate_single_run(run_dir2)
    assert not passed2
    assert any("exceeds planned upper bound 600" in e for e in errors2)

    # ann_retrieval k=5 bound is 300. 60 trials * 6 calls = 360 calls
    run_dir3 = tmp_path / "run_bound_k5" / "sweep_ann_retrieval_k5_ef128"
    create_synthetic_sweep_run(run_dir3, strategy="ann_retrieval", config={"k": 5, "ef_search": 128, "seed": 42}, calls_per_trial=6)
    passed3, errors3, _ = validate_single_run(run_dir3)
    assert not passed3
    assert any("exceeds planned upper bound 300" in e for e in errors3)

    # ann_retrieval k=20 bound is 1200. 60 trials * 21 calls = 1260 calls
    run_dir4 = tmp_path / "run_bound_k20" / "sweep_ann_retrieval_k20_ef128"
    create_synthetic_sweep_run(run_dir4, strategy="ann_retrieval", config={"k": 20, "ef_search": 128, "seed": 42}, calls_per_trial=21)
    passed4, errors4, _ = validate_single_run(run_dir4)
    assert not passed4
    assert any("exceeds planned upper bound 1200" in e for e in errors4)

    # brute_force bound is 38500. 60 trials * 650 calls = 39000 calls
    run_dir5 = tmp_path / "run_bound_bf" / "sweep_brute_force"
    create_synthetic_sweep_run(run_dir5, strategy="brute_force", config={"seed": 42}, calls_per_trial=650)
    passed5, errors5, _ = validate_single_run(run_dir5)
    assert not passed5
    assert any("exceeds planned upper bound 38500" in e for e in errors5)

    # 3. Thread pin violation in sweep mode
    run_dir6 = tmp_path / "run_threads" / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_sweep_run(run_dir6, cpu_threads=4)
    passed6, errors6, _ = validate_single_run(run_dir6)
    assert not passed6
    assert any("cpu_threads != 1" in e for e in errors6)

    # 4. Duplicate success key in sweep mode
    run_dir7 = tmp_path / "run_dup_swp" / "sweep_ann_retrieval_k10_ef128"
    create_synthetic_sweep_run(run_dir7, duplicate_success=True)
    passed7, errors7, _ = validate_single_run(run_dir7)
    assert not passed7
    assert any("has status 'success'" in e for e in errors7)


def test_resumed_directory_fixture_64_lines_59_keys(tmp_path: Path):
    """Requirement 7: Resumed directory fixture: 64 lines, 59 keys, five failed-then-succeeded keys."""
    run_dir = tmp_path / "accuracy_brute_force"
    create_synthetic_accuracy_run(run_dir, strategy="brute_force")

    raw_p = run_dir / "raw.jsonl"
    lines = raw_p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 59  # 29 DSA + 30 Metacademy

    # Pick 5 Metacademy keys to have failed initially
    prepended_failures = []
    for i in range(5):
        key = f"accuracy:brute_force:metacademy_gold_standard_MEKG:node_{i}:r0"
        failed_rec = {
            "key": key,
            "strategy": "brute_force",
            "corpus": "metacademy_gold_standard_MEKG",
            "status": "failed",
            "error_type": "APITimeoutError",
            "error_message": "Request timed out during initial execution",
            "retries": 3,
        }
        prepended_failures.append(json.dumps(failed_rec))

    all_lines = prepended_failures + lines
    raw_p.write_text("\n".join(all_lines) + "\n", encoding="utf-8")

    assert len(all_lines) == 64

    passed, errors, info = validate_single_run(run_dir)
    assert passed, f"Resumed fixture failed: {errors}"
    assert errors == []
    assert info["trials"] == 59
    assert info["total_records"] == 64
    assert info["resumed"] is True
    assert info["failed_then_succeeded_count"] == 5
    assert info["still_failed_count"] == 0
    assert len(info["failed_then_succeeded_keys"]) == 5


def test_mutant_integer_summary_field_value_error(tmp_path: Path):
    """Requirement 8: Catch uncaught ValueError on integer summary fields."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)

    csv_p = run_dir / "summary.csv"
    lines = csv_p.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    idx = header.index("num_trials")
    parts = lines[1].split(",")
    parts[idx] = "NaN"
    lines[1] = ",".join(parts)
    csv_p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("Invalid integer value" in e for e in errors)


def test_mutant_short_trial_count_consistent_summary(tmp_path: Path):
    """Mutant 5: short trial count where summary.csv is also patched to agree."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, dsa_trials=28, metacademy_trials=30)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("trial count mismatch" in e.lower() for e in errors)


def test_mutant_tampered_mean_total_s(tmp_path: Path):
    """Mutant 6: tampered total_s_mean in summary.csv disagrees with raw.jsonl."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    csv_p = run_dir / "summary.csv"
    lines = csv_p.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    idx = header.index("total_s_mean")
    parts = lines[1].split(",")
    parts[idx] = "999.999"
    lines[1] = ",".join(parts)
    csv_p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("total_s_mean mismatch" in e for e in errors)


def test_mutant_even_n_median_correctness(tmp_path: Path):
    """Mutant 7: even-n median verification."""
    run_dir = tmp_path / "accuracy_brute_force"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": "accuracy_brute_force",
        "mode": "accuracy_dsa",
        "git_commit": BASE_COMMIT,
        "git_dirty": False,
        "libraries": BASE_LIBRARIES,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    sidecar = {
        "strategy": "brute_force",
        "config": {"seed": 42},
        "mode": "accuracy_dsa",
    }
    (run_dir / "strategy_config.json").write_text(json.dumps(sidecar), encoding="utf-8")

    raw_recs = []
    vals = [1.0, 2.0, 3.0, 4.0] + [2.5] * 25
    for i, v in enumerate(vals):
        raw_recs.append(json.dumps({
            "key": f"trial_{i}",
            "strategy": "brute_force",
            "corpus": "DSA_gold_standard_MEKG",
            "status": "success",
            "metrics": {"llm_calls": 1, "total_s": v},
            "score": {"tp": 1, "fp": 0, "fn": 0, "gold_neighbours": 1, "shortlist_hits": 1},
        }))
    (run_dir / "raw.jsonl").write_text("\n".join(raw_recs) + "\n", encoding="utf-8")

    csv_rows = [{
        "strategy": "brute_force",
        "mode": "accuracy_dsa",
        "corpus_or_size": "DSA_gold_standard_MEKG",
        "num_trials": "29",
        "num_success": "29",
        "num_failed": "0",
        "n_with_retries": "0",
        "llm_calls_sum": "29",
        "llm_calls_mean": "1.0",
        "total_s_mean": f"{statistics.mean(vals):.6f}",
        "total_s_median": "99.0",  # tampered median
        "precision_micro": "1.0",
        "recall_micro": "1.0",
        "f1_micro": "1.0",
        "shortlist_recall_micro": "1.0",
    }]
    with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("total_s_median mismatch" in e for e in errors)


def test_mutant_missing_embedder_block_embedding_strategy(tmp_path: Path):
    """Mutant 8: missing embedder block on an embedding strategy (fail closed)."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", embedder_block_override={})
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("missing required 'embedder' block" in e for e in errors)


def test_mutant_missing_required_field_git_dirty(tmp_path: Path):
    """Mutant 9: missing required field git_dirty in manifest."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    p = run_dir / "manifest.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    del d["git_dirty"]
    p.write_text(json.dumps(d), encoding="utf-8")

    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("git_dirty" in e for e in errors)


def test_mutant_exceeded_planned_bound(tmp_path: Path):
    """Mutant 10: realized LLM calls exceed planned upper bound."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", calls_per_trial=15)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("exceeds planned upper bound" in e for e in errors)


def test_mutant_thread_pin_violated(tmp_path: Path):
    """Mutant 11: cpu_threads != 1 in sidecar."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", cpu_threads=4)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("cpu_threads != 1" in e for e in errors)


def test_mutant_brute_force_has_embedder_model(tmp_path: Path):
    """Mutant 12: non-embedding strategy unexpectedly defines embedder model."""
    run_dir = tmp_path / "accuracy_brute_force"
    create_synthetic_accuracy_run(
        run_dir,
        strategy="brute_force",
        embedder_block_override={
            "type": "minilm",
            "model_name": EXPECTED_EMBEDDER_MODEL,
            "revision": EXPECTED_EMBEDDER_REVISION,
            "cpu_threads": 1,
            "torch_threads": 1,
        },
    )
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("unexpectedly defines an embedding model" in e for e in errors)


def test_mutant_missing_file_manifest(tmp_path: Path):
    """Mutant 13: missing manifest.json."""
    run_dir = tmp_path / "accuracy_ann_retrieval_k10_ef128"
    create_synthetic_accuracy_run(run_dir)
    (run_dir / "manifest.json").unlink()
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("Missing required file: manifest.json" in e for e in errors)


def test_table_t3_inventory_generation(tmp_path: Path):
    """Test that validate_all_runs produces a valid Table T3 CSV with failed_then_succeeded."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run2 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run1, config={"k": 10, "ef_search": 128, "seed": 42})
    create_synthetic_accuracy_run(run2, config={"k": 5, "ef_search": 128, "seed": 42})

    passed, results, t3_csv = validate_all_runs(results_dir)
    assert passed
    assert len(results) == 2
    reader = list(csv.DictReader(t3_csv.splitlines()))
    assert len(reader) == 2
    assert "dir_sha256" in reader[0]
    assert "status" in reader[0]
    assert "failed_then_succeeded" in reader[0]
    assert "still_failed" in reader[0]
    assert reader[0]["status"] == "PASS"
    assert reader[0]["failed_then_succeeded"] == "0"
    assert reader[0]["still_failed"] == "0"
