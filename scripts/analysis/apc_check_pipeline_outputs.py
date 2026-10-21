#!/usr/bin/env python3
"""APC independent check of Phase 4 pipeline outputs.

Stdlib only. Read-only. Imports nothing from the repo, so it cannot share a bug
with the pipeline or the validator. It re-derives numbers from each run's raw.jsonl
and summary.csv and compares them with the pipeline's CSV tables.

Usage:
    python3 apc_check_pipeline_outputs.py --results-dir RESULTS --output-dir OUT

Exit code 0 only if every check passes. Run it AFTER the validation gate has passed.
Expected table files in OUT/tables: T1_accuracy_benchmark.csv, T2_sweep_cost_summary.csv,
T2_slope_fits.csv, T3_run_inventory.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

PEAK_TRIAL_KEY = "sweep:brute_force:2000:t9"
T3_REQUIRED = [
    "run", "strategy", "config", "mode", "commit", "libraries_hash", "trials", "calls",
    "failed", "failed_then_succeeded", "still_failed", "retries", "status",
    "manifest_sha256", "config_sha256", "raw_sha256", "summary_sha256", "dir_sha256",
]

fails: list[str] = []
passes = 0


def check(ok: bool, msg: str) -> None:
    global passes
    if ok:
        passes += 1
    else:
        fails.append(msg)
        print(f"FAIL  {msg}")


def close(a, b, tol=1e-9) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    if math.isnan(a) and math.isnan(b):
        return True
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def read_csv(p: Path) -> list[dict]:
    if not p.is_file():
        check(False, f"missing file {p}")
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_final(raw: Path) -> tuple[dict, dict]:
    """Return (last record per key, all records per key)."""
    last, hist = {}, {}
    with open(raw, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            k = r.get("key")
            last[k] = r
            hist.setdefault(k, []).append(r)
    return last, hist


def stats(vals):
    if not vals:
        return dict(mean=float("nan"), median=float("nan"), std=float("nan"), min=float("nan"), max=float("nan"))
    return dict(
        mean=statistics.mean(vals), median=statistics.median(vals),
        std=statistics.stdev(vals) if len(vals) > 1 else 0.0, min=min(vals), max=max(vals),
    )


def ols_slope(xs, ys):
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    mx, my = statistics.mean(lx), statistics.mean(ly)
    sxx = sum((a - mx) ** 2 for a in lx)
    sxy = sum((a - mx) * (b - my) for a, b in zip(lx, ly))
    return sxy / sxx


def d2(s: float) -> str:
    return "approximately flat" if s < 0.1 else ("sub-linear" if s <= 0.9 else "approximately linear")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    tdir = a.output_dir / "tables"
    runs = sorted(d for d in a.results_dir.iterdir() if d.is_dir() and (d / "manifest.json").is_file())
    print(f"runs found: {len(runs)}")
    check(len(runs) == 24, f"expected 24 run directories, found {len(runs)}")

    t1, t2 = read_csv(tdir / "T1_accuracy_benchmark.csv"), read_csv(tdir / "T2_sweep_cost_summary.csv")
    t3, slopes = read_csv(tdir / "T3_run_inventory.csv"), read_csv(tdir / "T2_slope_fits.csv")

    # ---------- T3 ----------
    if t3:
        missing = [c for c in T3_REQUIRED if c not in t3[0]]
        check(not missing, f"T3 lacks required columns: {missing}")
        check(len(t3) == 24, f"T3 has {len(t3)} rows, expected 24")
        by_run = {r.get("run", r.get("run_dir")): r for r in t3}
        libs = {r.get("libraries_hash") for r in t3}
        check(len(libs) == 1 and "" not in libs and None not in libs, f"T3 libraries_hash values: {libs}")
        for d in runs:
            r = by_run.get(d.name)
            if r is None:
                check(False, f"T3 missing run {d.name}")
                continue
            last, hist = load_final(d / "raw.jsonl")
            succ = [x for x in last.values() if x.get("status") == "success"]
            check(str(r.get("trials")) == str(len(last)), f"T3 {d.name}: trials={r.get('trials')} but raw has {len(last)} keys")
            calls = sum(int(x["metrics"]["llm_calls"]) for x in succ)
            check(str(r.get("calls")) == str(calls), f"T3 {d.name}: calls={r.get('calls')} but raw sums to {calls}")
            fts = sum(1 for k, h in hist.items() if last[k].get("status") == "success"
                      and any(x.get("status") != "success" for x in h[:-1]))
            check(str(r.get("failed_then_succeeded")) == str(fts),
                  f"T3 {d.name}: failed_then_succeeded={r.get('failed_then_succeeded')} but raw gives {fts}")
            sf = sum(1 for x in last.values() if x.get("status") != "success")
            check(str(r.get("still_failed")) == str(sf), f"T3 {d.name}: still_failed={r.get('still_failed')} but raw gives {sf}")
            check(len(r.get("dir_sha256", "")) == 64, f"T3 {d.name}: dir_sha256 not 64 hex chars")

    # ---------- T2 and slopes ----------
    exp_defined = {"llm_calls": [], "total_s": []}
    exp_undefined = {"llm_calls": 0, "total_s": 0}
    for d in [x for x in runs if x.name.startswith("sweep")]:
        sc = json.loads((d / "strategy_config.json").read_text(encoding="utf-8"))
        strat = sc.get("strategy")
        last, _ = load_final(d / "raw.jsonl")
        with open(d / "summary.csv", newline="", encoding="utf-8") as f:
            summ = {int(float(r["corpus_or_size"])): r for r in csv.DictReader(f)}
        sizes = sorted({int(r["size"]) for r in last.values()})
        means = {"llm_calls": [], "total_s": []}
        for n in sizes:
            succ = [r for r in last.values() if int(r["size"]) == n and r.get("status") == "success"]
            m = lambda key: [float(r["metrics"][key]) for r in succ]
            exp = {f"llm_calls_{k}": v for k, v in stats(m("llm_calls")).items()}
            for met in ("total_s", "shortlist_s", "decide_s"):
                exp.update({f"{met}_{k}": v for k, v in stats(m(met)).items()})
            clean = [r for r in succ if r.get("retries", 0) == 0 and r.get("key") != PEAK_TRIAL_KEY]
            cm = [float(r["metrics"]["total_s"]) for r in clean]
            means["llm_calls"].append(statistics.mean(m("llm_calls")) if succ else 0.0)
            means["total_s"].append(statistics.mean(m("total_s")) if succ else 0.0)
            # (1) raw recompute vs harness summary.csv (independent of the pipeline)
            for col, val in exp.items():
                if col in summ[n]:
                    check(close(summ[n][col], val), f"{d.name} n={n}: summary.csv {col}={summ[n][col]} vs raw {val}")
            # (2) pipeline T2 vs raw recompute. Match a T2 row on strategy+size+all compared values.
            cands = [r for r in t2 if r.get("strategy") == strat and str(r.get("size_n")) == str(n)]
            ok_row = None
            for r in cands:
                if all(close(r.get(c, "nan"), v) for c, v in exp.items() if c in r):
                    ok_row = r
                    break
            check(ok_row is not None, f"T2 has no row for {d.name} n={n} matching raw recompute")
            if ok_row is not None:
                for c in exp:
                    check(c in ok_row, f"T2 row {d.name} n={n} lacks column {c}")
                cn = [c for c in ok_row if c.startswith("clean_num_trials")]
                check(bool(cn) and int(float(ok_row[cn[0]])) == len(clean),
                      f"T2 {d.name} n={n}: clean trial count {ok_row.get(cn[0]) if cn else None} vs raw {len(clean)}")
                cmean = [c for c in ok_row if c.startswith("clean_total_s_mean")]
                if cm and cmean:
                    check(close(ok_row[cmean[0]], statistics.mean(cm)), f"T2 {d.name} n={n}: clean total_s mean mismatch")
                # harness zero-retry column is an independent check on the retries>0 half of the exclusion
                zr = summ[n].get("total_s_zero_retries_mean")
                if zr is not None and not (strat == "brute_force" and n == 2000):
                    check(cmean and close(ok_row[cmean[0]], zr),
                          f"T2 {d.name} n={n}: clean mean {ok_row.get(cmean[0]) if cmean else None} vs harness zero-retry mean {zr}")
        for met in ("llm_calls", "total_s"):
            if all(v > 0 for v in means[met]):
                exp_defined[met].append(ols_slope(sizes, means[met]))
            else:
                exp_undefined[met] += 1
                zs = [s for s, v in zip(sizes, means[met]) if v <= 0]
                print(f"NOTE  {d.name}: {met} mean is zero at n={zs}; the fit must be reported as undefined")

    # slope table: numeric rows must match independently fitted slopes; undefined cases must not be numeric
    pre = [r for r in slopes if str(r.get("condition", "")).startswith("pre-registered")]
    for met in ("llm_calls", "total_s"):
        rows = [r for r in pre if r.get("metric") == met]
        numeric, nonnum = [], 0
        for r in rows:
            try:
                v = float(r["slope"])
            except (TypeError, ValueError):
                v = float("nan")
            if math.isfinite(v):
                numeric.append(v)
                check(r.get("flatness_category_D2") == d2(v),
                      f"slope {met} {r.get('strategy')}/{r.get('variant')}: category "
                      f"{r.get('flatness_category_D2')!r} inconsistent with slope {v:.4f}")
            else:
                nonnum += 1
        remaining = list(exp_defined[met])
        for v in numeric:
            hit = next((e for e in remaining if close(e, v, 1e-6)), None)
            check(hit is not None, f"slope {met}: reported numeric slope {v:.6f} matches no independently fitted slope")
            if hit is not None:
                remaining.remove(hit)
        check(len(numeric) == len(exp_defined[met]),
              f"slope {met}: {len(numeric)} numeric fits reported, {len(exp_defined[met])} runs have all-positive means")
        check(nonnum == exp_undefined[met],
              f"slope {met}: {nonnum} undefined fits reported, expected {exp_undefined[met]} (zero-mean sizes)")

    # ---------- T1 (copy check against summary.csv) ----------
    for d in [x for x in runs if x.name.startswith("accuracy")]:
        sc = json.loads((d / "strategy_config.json").read_text(encoding="utf-8"))
        with open(d / "summary.csv", newline="", encoding="utf-8") as f:
            for s in csv.DictReader(f):
                cols = ["llm_calls_mean", "precision_micro", "recall_micro", "f1_micro", "shortlist_recall_micro"]
                hit = any(r.get("strategy") == sc.get("strategy") and r.get("corpus") == s["corpus_or_size"]
                          and all(close(r.get(c, "nan"), s[c]) for c in cols if c in s) for r in t1)
                check(hit, f"T1 has no row equal to summary.csv for {d.name} / {s['corpus_or_size']}")

    print(f"\n{passes} checks passed, {len(fails)} failed")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
