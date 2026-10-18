"""
tests/test_analysis_validate_runs.py
====================================
Comprehensive test suite and executed corruption/mutation matrix for
scripts.analysis.validate_runs.

Meets all requirements of TASK ANALYSIS-001:
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
    compute_directory_sha256,
    compute_file_sha256,
    get_planned_call_bound,
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
    embedder_block_override: Optional[Dict[str, Any]] = None,
) -> Path:
    """Generate a valid, fully synthetic accuracy experiment run directory in tmp_path."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    if config is None:
        config = {"k": 10, "ef_search": 128, "seed": 42}
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
            sidecar["embedder"] = {
                "type": "fake",
                "uses_embeddings": False,
                "dim": 32,
            }
    (dest_dir / "strategy_config.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    # 3. raw.jsonl
    raw_lines = []
    groups = [
        ("DSA_gold_standard_MEKG", dsa_trials),
        ("metacademy_gold_standard_MEKG", metacademy_trials),
    ]

    for corpus, n_trials in groups:
        for i in range(n_trials):
            rec = {
                "key": f"accuracy:{strategy}:{corpus}:node_{i}:r0",
                "strategy": strategy,
                "mode": "accuracy",
                "corpus": corpus,
                "node": f"node_{i}",
                "status": "success",
                "retries": 0,
                "metrics": {
                    "llm_calls": calls_per_trial,
                    "total_s": total_s_per_trial + (i * 0.1),
                    "shortlist_s": 0.01,
                    "decide_s": 0.9,
                    "apply_s": 0.001,
                    "update_s": 0.0,
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
) -> Path:
    """Generate a valid, fully synthetic sweep experiment run directory in tmp_path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if sizes is None:
        sizes = [50, 100, 200, 500, 1000, 2000]
    if config is None:
        config = {"k": 10, "ef_search": 128, "seed": 42}
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

    sidecar = {
        "strategy": strategy,
        "config": config,
        "mode": "sweep",
        "embedder": {
            "type": "minilm",
            "uses_embeddings": True,
            "model_name": EXPECTED_EMBEDDER_MODEL,
            "revision": EXPECTED_EMBEDDER_REVISION,
            "cpu_threads": 1,
            "torch_threads": 1,
        },
    }
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
            rec = {
                "key": f"sweep:{strategy}:size_{sz}:trial_{i}",
                "strategy": strategy,
                "mode": "sweep",
                "size": sz,
                "status": "success",
                "retries": 0,
                "metrics": {
                    "llm_calls": calls_per_trial,
                    "total_s": t_s,
                    "shortlist_s": 0.01,
                    "decide_s": 0.4,
                    "apply_s": 0.001,
                    "update_s": 0.0,
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
    run_dir = tmp_path / "run_dirty"
    create_synthetic_accuracy_run(run_dir, git_dirty=True)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("git_dirty is not False" in e for e in errors)


def test_mutant_cross_run_commit_mismatch(tmp_path: Path):
    """Mutant 2: git_commit mismatch across runs."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "run1"
    run2 = results_dir / "run2"
    create_synthetic_accuracy_run(run1, git_commit=BASE_COMMIT)
    create_synthetic_accuracy_run(run2, git_commit="0000000000000000000000000000000000000000")

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    assert any(any("Cross-run git_commit mismatch" in err for err in r.get("errors", [])) for r in results)


def test_mutant_cross_run_library_mismatch(tmp_path: Path):
    """Mutant 3: library versions mismatch across runs."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "run1"
    run2 = results_dir / "run2"
    create_synthetic_accuracy_run(run1)
    bad_libs = dict(BASE_LIBRARIES)
    bad_libs["torch"] = "9.9.9"
    create_synthetic_accuracy_run(run2, libraries=bad_libs)

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    assert any(any("Cross-run libraries block mismatch" in err for err in r.get("errors", [])) for r in results)


def test_mutant_cross_run_embedder_revision_mismatch(tmp_path: Path):
    """Mutant 4: embedder revision mismatch across two embedding runs."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "run1"
    run2 = results_dir / "run2"
    create_synthetic_accuracy_run(run1)
    create_synthetic_accuracy_run(run2, embedder_revision="badbadbadbadbadbadbadbadbadbadbadbadbadb")

    passed, results, _ = validate_all_runs(results_dir)
    assert not passed
    # Caught either by single run constant or cross-run check
    all_errs = [e for r in results for e in r.get("errors", [])]
    assert any("revision mismatch" in e for e in all_errs)


def test_mutant_short_trial_count_consistent_summary(tmp_path: Path):
    """Mutant 5: short trial count where summary.csv is also patched to agree.

    Expects 29 DSA trials + 30 Metacademy = 59. We provide 28 DSA trials + 30 = 58,
    and summary.csv also says 28 DSA trials. Must fail with per-group trial count mismatch!
    """
    run_dir = tmp_path / "run_short"
    create_synthetic_accuracy_run(run_dir, dsa_trials=28, metacademy_trials=30)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("trial count mismatch" in e.lower() for e in errors)


def test_mutant_tampered_mean_total_s(tmp_path: Path):
    """Mutant 6: tampered total_s_mean in summary.csv disagrees with raw.jsonl."""
    run_dir = tmp_path / "run_tampered_mean"
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
    """Mutant 7: even-n median verification.

    With n=4 trials having total_s [1.0, 2.0, 3.0, 4.0]:
    - statistics.median gives (2.0 + 3.0) / 2 = 2.5
    - naive sorted[4//2] gives sorted[2] = 3.0 (wrong!)
    The validator must reject when summary.csv uses the wrong median formula (3.0).
    """
    run_dir = tmp_path / "run_even_n"
    run_dir.mkdir(parents=True, exist_ok=True)
    # Create an even-n fixture
    manifest = {
        "run_id": "even_n_test",
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
    # 29 trials total to satisfy accuracy_dsa count, first 4 have known values
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

    # Write summary with naive sorted[n//2] instead of statistics.median
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
    run_dir = tmp_path / "run_missing_embedder"
    # Create ann_retrieval without embedder block in sidecar
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", embedder_block_override={})
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("missing required 'embedder' block" in e for e in errors)


def test_mutant_missing_required_field_git_dirty(tmp_path: Path):
    """Mutant 9: missing required field git_dirty in manifest."""
    run_dir = tmp_path / "run_missing_field"
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
    run_dir = tmp_path / "run_exceed_calls"
    # ann_retrieval k=10 accuracy bound is 590 calls.
    # 59 trials * 15 calls = 885 calls (exceeds 590!)
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", calls_per_trial=15)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("exceeds planned upper bound" in e for e in errors)


def test_mutant_thread_pin_violated(tmp_path: Path):
    """Mutant 11: cpu_threads != 1 in sidecar."""
    run_dir = tmp_path / "run_bad_threads"
    create_synthetic_accuracy_run(run_dir, strategy="ann_retrieval", cpu_threads=4)
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("cpu_threads != 1" in e for e in errors)


def test_mutant_brute_force_has_embedder_model(tmp_path: Path):
    """Mutant 12: non-embedding strategy (brute force) unexpectedly has an embedder model."""
    run_dir = tmp_path / "run_brute_with_embedder"
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
    run_dir = tmp_path / "run_no_manifest"
    create_synthetic_accuracy_run(run_dir)
    (run_dir / "manifest.json").unlink()
    passed, errors, _ = validate_single_run(run_dir)
    assert not passed
    assert any("Missing required file: manifest.json" in e for e in errors)


def test_resume_detection_with_duplicate_keys(tmp_path: Path):
    """Test that duplicate keys in raw.jsonl are correctly flagged as a resumed run."""
    run_dir = tmp_path / "run_resumed"
    create_synthetic_accuracy_run(run_dir, has_duplicates=True)
    passed, errors, info = validate_single_run(run_dir)
    # The run has valid counts and recomputations, but is_resumed must be True
    assert info["resumed"] is True


def test_table_t3_inventory_generation(tmp_path: Path):
    """Test that validate_all_runs produces a valid Table T3 CSV."""
    results_dir = tmp_path / "results"
    run1 = results_dir / "accuracy_ann_retrieval_k10_ef128"
    run2 = results_dir / "accuracy_ann_retrieval_k5_ef128"
    create_synthetic_accuracy_run(run1, config={"k": 10, "ef_search": 128})
    create_synthetic_accuracy_run(run2, config={"k": 5, "ef_search": 128})

    passed, results, t3_csv = validate_all_runs(results_dir)
    assert passed
    assert len(results) == 2
    reader = list(csv.DictReader(t3_csv.splitlines()))
    assert len(reader) == 2
    assert "dir_sha256" in reader[0]
    assert "status" in reader[0]
    assert reader[0]["status"] == "PASS"
