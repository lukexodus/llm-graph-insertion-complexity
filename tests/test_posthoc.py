"""test_posthoc.py — tests for the post-hoc decision and ranking stage.

ANALYSIS-004 / [D-89]. Covers the frozen specification: normalisation,
degenerate criterion, ties, Kendall tau-b, weighted TOPSIS, exact analytic
rank shares against a fine grid, seeded draws, gate classes, the
fail-closed gate, and the default-run file set.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pytest

from scripts.analysis import posthoc as P
from scripts.analysis.posthoc import (
    CORPUS_ORDER,
    STRATEGY_ORDER,
    assert_matches_final_output,
    build_t5b_rows,
    compute_A_C,
    compute_gates,
    exact_rank_shares,
    extract_inputs,
    gate_class,
    kendall_tau_b,
    mc_rank_shares,
    rank_with_ties,
    strict_ranks,
    topsis_closeness,
    weighted_scores,
)
from scripts.analysis.run_analysis import main as run_pipeline_main
from tests.test_analysis_pipeline import create_mock_run_directory


# ---------------------------------------------------------------------------
# Synthetic inputs (values mirror the real final_output_final cells)
# ---------------------------------------------------------------------------

_DSA = "DSA_gold_standard_MEKG"
_META = "metacademy_gold_standard_MEKG"

# (f1, recall, precision, calls, shortlist_recall, random_baseline)
_ACC_VALUES = {
    (_DSA, "brute_force"): (0.5862068965517241, 0.6296296296296297, 0.5483870967741935, 28.0, 1.0, float("nan")),
    (_DSA, "embedding_threshold"): (0.14754098360655737, 0.08333333333333333, 0.5862068965517241, 0.7586206896551724, 0.1111111111111111, float("nan")),
    (_DSA, "ann_retrieval"): (0.5111111111111111, 0.42592592592592593, 0.6388888888888888, 10.0, 0.5277777777777778, 0.35714285714285715),
    (_DSA, "bounded_bucket"): (0.2714285714285714, 0.17592592592592593, 0.5846153846153846, 6.9655172413793105, 0.25925925925925924, 0.35714285714285715),
    (_META, "brute_force"): (0.14345991561181434, 0.6238532110091743, 0.08130081300813008, 140.0, 1.0, float("nan")),
    (_META, "embedding_threshold"): (0.2695035460992908, 0.1743119266055046, 0.6065573770491803, 1.1333333333333333, 0.2018348623853211, float("nan")),
    (_META, "ann_retrieval"): (0.29411764705882354, 0.3669724770642202, 0.24539877300613497, 10.0, 0.5045871559633027, 0.07142857142857142),
    (_META, "bounded_bucket"): (0.11363636363636365, 0.09174311926605505, 0.14925373134328357, 7.366666666666666, 0.14678899082568808, 0.07142857142857142),
}

_VARIANTS = {
    "brute_force": "primary (all candidates)",
    "embedding_threshold": "primary (theta=0.6)",
    "ann_retrieval": "primary (k=10, ef=128)",
    "bounded_bucket": "primary (s_min=5, s_max=10, nb=12)",
}

_SWEEP = {
    "brute_force": (2000.0, 1713.0988233976009),
    "embedding_threshold": (0.8, 0.9381960321006773),
    "ann_retrieval": (10.0, 8.276875985300284),
    "bounded_bucket": (7.0, 5.638046632800615),
}


def _inputs() -> Dict[str, Any]:
    accuracy: Dict[str, Dict[str, Any]] = {c: {} for c in CORPUS_ORDER}
    for (corpus, strat), vals in _ACC_VALUES.items():
        f1, rec, prec, calls, sr, rb = vals
        accuracy[corpus][strat] = {
            "variant": _VARIANTS[strat],
            "f1_micro": f1,
            "recall_micro": rec,
            "precision_micro": prec,
            "llm_calls_mean": calls,
            "shortlist_recall_micro": sr,
            "random_baseline_recall": rb,
            "num_trials": 29 if corpus == _DSA else 30,
        }
    sweep = {
        s: {"llm_calls_mean": v[0], "total_s_mean": v[1]}
        for s, v in _SWEEP.items()
    }
    return {"accuracy": accuracy, "sweep": sweep}


def _t1_rows() -> List[Dict[str, Any]]:
    rows = []
    for (corpus, strat), vals in _ACC_VALUES.items():
        f1, rec, prec, calls, sr, rb = vals
        rows.append({
            "strategy": strat,
            "variant": _VARIANTS[strat],
            "corpus": corpus,
            "num_trials": 29 if corpus == _DSA else 30,
            "num_success": 29 if corpus == _DSA else 30,
            "llm_calls_mean": calls,
            "precision_micro": prec,
            "recall_micro": rec,
            "f1_micro": f1,
            "shortlist_recall_micro": sr,
            "random_baseline_recall": rb,
        })
    return rows


def _t2_rows() -> List[Dict[str, Any]]:
    rows = []
    for strat, (calls, total_s) in _SWEEP.items():
        rows.append({
            "strategy": strat,
            "variant": _VARIANTS[strat],
            "size_n": 2000,
            "llm_calls_mean": calls,
            "total_s_mean": total_s,
        })
    return rows


def _write_crosscheck_dir(root: Path) -> Path:
    (root / "tables").mkdir(parents=True, exist_ok=True)
    (root / "figures").mkdir(parents=True, exist_ok=True)
    t1 = _t1_rows()
    with open(root / "tables" / "T1_accuracy_benchmark.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(t1[0].keys()))
        w.writeheader()
        w.writerows(t1)
    t2 = _t2_rows()
    with open(root / "tables" / "T2_sweep_cost_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(t2[0].keys()))
        w.writeheader()
        w.writerows(t2)
    f6 = [
        {
            "corpus": r["corpus"],
            "strategy": r["strategy"],
            "variant": r["variant"],
            "calls": r["llm_calls_mean"],
            "f1": r["f1_micro"],
        }
        for r in t1
    ]
    with open(root / "figures" / "F6_cost_vs_accuracy_dominance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(f6[0].keys()))
        w.writeheader()
        w.writerows(f6)
    return root


# ---------------------------------------------------------------------------
# Normalisation and ranking
# ---------------------------------------------------------------------------

def test_normalisation_hand_worked():
    f1 = {"a": 0.5, "b": 0.4, "c": 0.3, "d": 0.2}
    calls = {"a": 1000.0, "b": 10.0, "c": 1.0, "d": 100.0}
    inputs = {
        "accuracy": {
            _DSA: {
                "a": {"f1_micro": f1["a"], "llm_calls_mean": calls["a"]},
                "b": {"f1_micro": f1["b"], "llm_calls_mean": calls["b"]},
                "c": {"f1_micro": f1["c"], "llm_calls_mean": calls["c"]},
                "d": {"f1_micro": f1["d"], "llm_calls_mean": calls["d"]},
            }
        }
    }
    # Direct check of the formula on the same numbers.
    a, a_deg = P._normalise(f1, higher_is_better=True)
    g = {k: np.log10(1.0 + v) for k, v in calls.items()}
    c, c_deg = P._normalise(g, higher_is_better=False)
    lo_g, hi_g = min(g.values()), max(g.values())
    assert np.isclose(a["a"], 1.0) and np.isclose(a["d"], 0.0)
    assert np.isclose(a["b"], (0.4 - 0.2) / (0.5 - 0.2))
    assert np.isclose(c["a"], 0.0)
    assert np.isclose(c["c"], 1.0)
    assert np.isclose(c["b"], 1.0 - (g["b"] - lo_g) / (hi_g - lo_g))
    assert not a_deg and not c_deg
    # compute_A_C on the real-shaped inputs is exercised elsewhere.


def test_all_equal_criterion_gets_half_and_is_flagged():
    scores, degenerate = P._normalise({"a": 0.3, "b": 0.3, "c": 0.3, "d": 0.3}, higher_is_better=True)
    assert degenerate is True
    assert all(v == 0.5 for v in scores.values())

    ac = compute_A_C(_inputs(), _DSA)
    assert ac["degenerate"] == {"A": False, "C": False}


def test_dsa_balanced_tie_shares_mean_rank():
    ac = compute_A_C(_inputs(), _DSA)
    scores = weighted_scores(ac["A"], ac["C"], 0.5)
    assert abs(scores["brute_force"] - 0.5) <= P.TIE_TOL
    assert abs(scores["embedding_threshold"] - 0.5) <= P.TIE_TOL
    ranks = rank_with_ties(scores, higher_is_better=True)
    # S3 leads at 0.587; S1 and S2 tie at 0.500 and share ranks 2 and 3.
    assert ranks["ann_retrieval"] == 1.0
    assert ranks["brute_force"] == 2.5
    assert ranks["embedding_threshold"] == 2.5
    assert ranks["bounded_bucket"] == 4.0


def test_strict_rank_tie_break_is_deterministic():
    scores = {s: 0.5 for s in STRATEGY_ORDER}
    ranks = strict_ranks(scores)
    assert [ranks[s] for s in STRATEGY_ORDER] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Kendall tau-b and TOPSIS
# ---------------------------------------------------------------------------

def test_kendall_tau_b_with_ties_hand_computed():
    x = {"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0}
    y = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    assert np.isclose(kendall_tau_b(x, y)["tau"], 5.0 / np.sqrt(30.0))
    assert kendall_tau_b(x, y)["tied_pairs"] == 1

    x2 = {"a": 1.0, "b": 1.0, "c": 2.0, "d": 3.0}
    y2 = {"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0}
    assert np.isclose(kendall_tau_b(x2, y2)["tau"], 0.8)
    assert kendall_tau_b(x2, y2)["tied_pairs"] == 2

    # Identical rankings: tau = 1.
    assert np.isclose(kendall_tau_b(x2, x2)["tau"], 1.0)
    # Reversed: tau = -1.
    rev = {k: -v for k, v in x2.items()}
    assert np.isclose(kendall_tau_b(x2, rev)["tau"], -1.0)


def test_topsis_three_point_toy_known_answer():
    A = {"a": 1.0, "b": 0.0, "c": 0.5}
    C = {"a": 0.0, "b": 1.0, "c": 0.5}
    close = topsis_closeness(A, C, 0.7)
    # Ideal (0.7, 0.3), anti-ideal (0, 0).
    assert np.isclose(close["a"], 0.7)
    assert np.isclose(close["b"], 0.3)
    assert np.isclose(close["c"], 0.5)
    ranks = rank_with_ties(close, higher_is_better=True)
    assert ranks == {"a": 1.0, "c": 2.0, "b": 3.0}


# ---------------------------------------------------------------------------
# Exact shares against a fine grid
# ---------------------------------------------------------------------------

def test_exact_rank_shares_against_fine_grid():
    A = {"a": 1.0, "b": 0.2, "c": 0.7, "d": 0.0}
    C = {"a": 0.1, "b": 1.0, "c": 0.4, "d": 0.8}
    exact = exact_rank_shares(A, C)
    n = 200_000
    grid = {s: {r: 0.0 for r in range(1, 5)} for s in A}
    for k in range(n):
        w = (k + 0.5) / n
        ranks = strict_ranks(weighted_scores(A, C, w))
        for s, r in ranks.items():
            grid[s][r] += 1.0 / n
    max_diff = max(
        abs(exact["shares"][s][r] - grid[s][r])
        for s in A for r in range(1, 5)
    )
    assert max_diff < 1e-3
    for s in A:
        assert np.isclose(sum(exact["shares"][s].values()), 1.0)


def test_seeded_draws_are_deterministic():
    A = {"a": 1.0, "b": 0.2, "c": 0.7, "d": 0.0}
    C = {"a": 0.1, "b": 1.0, "c": 0.4, "d": 0.8}
    first = mc_rank_shares(A, C, n_draws=500, seed=42)
    second = mc_rank_shares(A, C, n_draws=500, seed=42)
    assert first == second
    assert first["tie_draws"] == 0
    for s in A:
        assert np.isclose(sum(first["shares"][s].values()), 1.0)
    # A different seed is allowed to differ (not asserted equal), and the
    # exact shares are seed-free.
    assert exact_rank_shares(A, C) == exact_rank_shares(A, C)


def test_real_data_shares_match_frozen_targets():
    """The analytic shares on the real cells match [D-89]'s cross-check targets."""
    inputs = _inputs()
    dsa = compute_A_C(inputs, _DSA)
    meta = compute_A_C(inputs, _META)
    dsa_exact = exact_rank_shares(dsa["A"], dsa["C"])["shares"]
    meta_exact = exact_rank_shares(meta["A"], meta["C"])["shares"]

    dsa_target = {
        "brute_force": [0.331, 0.169, 0.109, 0.391],
        "embedding_threshold": [0.441, 0.059, 0.156, 0.344],
        "ann_retrieval": [0.228, 0.598, 0.174, 0.000],
        "bounded_bucket": [0.000, 0.174, 0.561, 0.265],
    }
    meta_target = {
        "brute_force": [0.000, 0.000, 0.197, 0.803],
        "embedding_threshold": [0.742, 0.258, 0.000, 0.000],
        "ann_retrieval": [0.258, 0.680, 0.061, 0.000],
        "bounded_bucket": [0.000, 0.061, 0.742, 0.197],
    }
    for s in STRATEGY_ORDER:
        for r in range(1, 5):
            assert abs(dsa_exact[s][r] - dsa_target[s][r - 1]) < 0.002, (s, r, dsa_exact[s][r])
            assert abs(meta_exact[s][r] - meta_target[s][r - 1]) < 0.002, (s, r, meta_exact[s][r])


# ---------------------------------------------------------------------------
# Gates and gate sensitivity
# ---------------------------------------------------------------------------

def test_gate_classes_cover_all_three_classes():
    gates = compute_gates(_inputs())
    assert gates["brute_force"]["g1"]["status"] == "not applicable"
    assert gates["embedding_threshold"]["g1"]["status"] == "not assessable"
    assert gates["ann_retrieval"]["g1"]["status"] == "pass"
    assert gates["bounded_bucket"]["g1"]["status"] == "fail"
    assert gates["brute_force"]["class"] == "Not effective"
    assert gates["embedding_threshold"]["class"] == "Conditionally effective"
    assert gates["ann_retrieval"]["class"] == "Effective"
    assert gates["bounded_bucket"]["class"] == "Not effective"

    # Direct class logic.
    pass_gate = {"status": "pass", "assessable": True}
    fail_gate = {"status": "fail", "assessable": True}
    na_gate = {"status": "not applicable", "assessable": False}
    g2 = {"status": "pass"}
    g3 = {"status": "pass"}
    assert gate_class(pass_gate, g2, g3) == "Effective"
    assert gate_class(fail_gate, g2, g3) == "Not effective"
    assert gate_class(na_gate, g2, g3) == "Conditionally effective"
    assert gate_class(na_gate, {"status": "fail"}, g3) == "Not effective"


def test_gate_sensitivity_classes_unchanged():
    inputs = _inputs()
    gates = compute_gates(inputs)
    means = {_DSA: {"ann_retrieval": 10.0, "bounded_bucket": 6.9655172413793105},
             _META: {"ann_retrieval": 10.0, "bounded_bucket": 7.366666666666666}}
    sm = P.size_matched_baselines(inputs, means)
    rows, summary = build_t5b_rows(inputs, gates, sm)
    assert summary["g2_n_settings"] == 1990
    assert summary["g2_changes"] == []
    assert summary["g3_first_change"] is None
    assert summary["classes_unchanged_all"] is True
    assert len(P.G3_SENSITIVITY_MARGINS) == 31
    assert P.G3_SENSITIVITY_MARGINS[0] == 0.0 and P.G3_SENSITIVITY_MARGINS[-1] == 0.15
    # Size-matched baseline: S4 DSA is level with random (does not change the class).
    assert np.isclose(sm[_DSA]["bounded_bucket"], 6.9655172413793105 / 28.0)


# ---------------------------------------------------------------------------
# Cross-check against the existing output
# ---------------------------------------------------------------------------

def test_crosscheck_matches_and_detects_a_mismatch(tmp_path: Path):
    inputs = _inputs()
    root = _write_crosscheck_dir(tmp_path)
    n = assert_matches_final_output(inputs, root)
    assert n == 8 * 6 + 4 * 2 + 8 * 2

    # Flip one F1 cell outside tolerance and expect a failure.
    path = root / "tables" / "T1_accuracy_benchmark.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    idx = header.index("f1_micro")
    cells = lines[1].split(",")
    cells[idx] = "0.999"
    lines[1] = ",".join(cells)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="T1 f1_micro"):
        assert_matches_final_output(inputs, root)


# ---------------------------------------------------------------------------
# CLI integration: post-hoc only and default behaviour
# ---------------------------------------------------------------------------

def _install_posthoc_mocks(monkeypatch, results_dir: Path):
    import scripts.analysis.run_analysis as ra

    monkeypatch.setattr(ra, "validate_all_runs", lambda *a, **kw: (True, [], "run,strategy\n"))
    monkeypatch.setattr(ra, "generate_t1_accuracy_table", lambda _dirs: _t1_rows())
    monkeypatch.setattr(ra, "generate_t2_sweep_cost_table", lambda _dirs: (_t2_rows(), []))
    means = {_DSA: {"ann_retrieval": 10.0, "bounded_bucket": 6.9655172413793105},
             _META: {"ann_retrieval": 10.0, "bounded_bucket": 7.366666666666666}}
    monkeypatch.setattr(P, "realised_shortlist_sizes", lambda _dirs: means)


def test_posthoc_only_writes_only_posthoc_names(tmp_path: Path, monkeypatch):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    output_dir = tmp_path / "output"
    crosscheck = _write_crosscheck_dir(tmp_path / "crosscheck")
    _install_posthoc_mocks(monkeypatch, results_dir)

    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
        "--only", "posthoc",
        "--crosscheck-dir", str(crosscheck),
    ])
    assert run_pipeline_main() == 0

    produced = {
        str(p.relative_to(output_dir)).replace("\\", "/")
        for p in output_dir.rglob("*") if p.is_file()
    }
    expected = {"RUN_INFO.txt"}
    for name in (P.T5, P.T5B, P.T6, P.T7, P.T8, P.T8B, P.T9, P.T9B):
        expected.add(f"tables/{name}.csv")
        expected.add(f"tables/{name}.md")
    for fig in ("F7_gates_g1_g2", "F8_score_vs_weight", "F9_rank_shares"):
        for ext in ("pdf", "png", "csv"):
            expected.add(f"figures/{fig}.{ext}")
    assert produced == expected

    run_info = (output_dir / "RUN_INFO.txt").read_text(encoding="utf-8")
    assert "only: posthoc" in run_info
    assert "posthoc.py:" in run_info
    assert "posthoc_figures.py:" in run_info
    assert "overall_gate_status: PASS" in run_info

    # T8 CSV keeps full precision (repr of the proportion); T8 Markdown is 2 dp.
    t8_csv = (output_dir / "tables" / f"{P.T8}.csv").read_text(encoding="utf-8")
    share_cells = [row.split(",")[5] for row in t8_csv.splitlines()[1:]]
    assert any(len(cell.split(".")[-1]) > 2 for cell in share_cells)
    assert len(t8_csv.splitlines()[1].split(",")[5]) > 4
    t8_md = (output_dir / "tables" / f"{P.T8}.md").read_text(encoding="utf-8")
    assert "0.33" in t8_md or "0.00" in t8_md

    plt.close("all")


def test_posthoc_gate_failure_writes_nothing(tmp_path: Path, monkeypatch):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    output_dir = tmp_path / "output"
    crosscheck = _write_crosscheck_dir(tmp_path / "crosscheck")
    import scripts.analysis.run_analysis as ra

    monkeypatch.setattr(
        ra,
        "validate_all_runs",
        lambda *a, **kw: (False, [{"run_dir": "bad", "passed": False, "errors": ["x"]}], ""),
    )
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--results-dir", str(results_dir),
        "--output-dir", str(output_dir),
        "--only", "posthoc",
        "--crosscheck-dir", str(crosscheck),
    ])
    assert run_pipeline_main() == 1
    assert not output_dir.exists()


def test_posthoc_requires_crosscheck_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--results-dir", str(tmp_path / "results"),
        "--output-dir", str(tmp_path / "output"),
        "--only", "posthoc",
    ])
    with pytest.raises(SystemExit) as exc:
        run_pipeline_main()
    assert exc.value.code == 2


def test_default_run_writes_the_same_files_as_before(tmp_path: Path, monkeypatch):
    """With no flag, the legacy file set is produced and no post-hoc file is written."""
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
        results_dir, "accuracy_ann_retrieval_k10_ef128", "ann_retrieval", "accuracy",
        acc_records, config={"k": 10, "ef_search": 128},
    )
    create_mock_run_directory(
        results_dir, "accuracy_brute_force", "brute_force", "accuracy",
        [dict(r, key=r["key"].replace("ann_retrieval", "brute_force"), metrics=dict(r["metrics"], llm_calls=28)) for r in acc_records],
        config={},
    )
    sweep_records = []
    for size in [50, 100, 200, 500, 1000, 2000]:
        for t in range(10):
            sweep_records.append({
                "key": f"sweep:ann_retrieval:{size}:t{t}",
                "size": size,
                "status": "success",
                "retries": 0,
                "metrics": {"total_s": 8.0, "shortlist_s": 0.01, "decide_s": 7.99, "llm_calls": 10},
            })
    create_mock_run_directory(
        results_dir, "sweep_ann_retrieval_k10_ef128", "ann_retrieval", "sweep",
        sweep_records, config={"k": 10, "ef_search": 128},
    )
    create_mock_run_directory(
        results_dir, "sweep_bounded_bucket_smin5_smax10_nb12", "bounded_bucket", "sweep",
        [dict(r, key=r["key"].replace("ann_retrieval", "bounded_bucket"), metrics=dict(r["metrics"], llm_calls=7)) for r in sweep_records],
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
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py", "--results-dir", str(results_dir), "--output-dir", str(output_dir),
    ])
    assert run_pipeline_main() == 0

    produced = {
        str(p.relative_to(output_dir)).replace("\\", "/")
        for p in output_dir.rglob("*") if p.is_file()
    }
    expected = {
        "RUN_INFO.txt",
        "tables/T1_accuracy_benchmark.csv", "tables/T1_accuracy_benchmark.md",
        "tables/T2_sweep_cost_summary.csv", "tables/T2_sweep_cost_summary.md",
        "tables/T2_slope_fits.csv", "tables/T2_slope_fits.md",
        "tables/T3_run_inventory.csv", "tables/T3_run_inventory.md",
        "tables/T4_sensitivity_metrics.csv", "tables/T4_sensitivity_metrics.md",
        "figures/F1_calls_scaling.pdf", "figures/F1_calls_scaling.png", "figures/F1_calls_scaling.csv",
        "figures/F1b_calls_scaling_logy.pdf", "figures/F1b_calls_scaling_logy.png", "figures/F1b_calls_scaling_logy.csv",
        "figures/F2_wallclock_scaling.pdf", "figures/F2_wallclock_scaling.png", "figures/F2_wallclock_scaling.csv",
        "figures/F2b_wallclock_scaling_logy.pdf", "figures/F2b_wallclock_scaling_logy.png", "figures/F2b_wallclock_scaling_logy.csv",
        "figures/F3_premise_check.pdf", "figures/F3_premise_check.png", "figures/F3_premise_check.csv",
        "figures/F4_accuracy_by_strategy.pdf", "figures/F4_accuracy_by_strategy.png", "figures/F4_accuracy_by_strategy.csv",
        "figures/F5_sensitivity_panels.pdf", "figures/F5_sensitivity_panels.png", "figures/F5_sensitivity_panels.csv",
        "figures/F6_cost_vs_accuracy_dominance.pdf", "figures/F6_cost_vs_accuracy_dominance.png", "figures/F6_cost_vs_accuracy_dominance.csv",
        "figures/F6_dominance.csv", "figures/F6_dominance.md",
        "figures/F6b_cost_vs_accuracy_logx.pdf", "figures/F6b_cost_vs_accuracy_logx.png", "figures/F6b_cost_vs_accuracy_logx.csv",
    }
    assert produced == expected
    _, sweep_rows = ra.generate_t2_sweep_cost_table(
        sorted(results_dir.glob("sweep_*"))
    )
    assert sweep_rows  # the legacy slope path ran
    plt.close("all")
