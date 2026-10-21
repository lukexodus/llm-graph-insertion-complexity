#!/usr/bin/env python3
"""apc_check_f_outputs.py -- independent output checker for the Phase 4 pipeline.

Written by the APC (not by the pipeline author). It recomputes tables from the
RAW run files and compares them with what run_analysis.py wrote. It does NOT
import any statistics code from scripts/analysis (only, optionally, the run-name
-> variant-label helper, which is a string mapping).

Usage:
  python3 apc_check_f_outputs.py --results-dir <results> --output-dir <pipeline output> \
      [--repo-root <repo>] [--certified-t3 ~/projects/thesis-analysis/output/table_t3.csv]

Exit 0 only if every check passes. Paste the FULL output.
Rules checked: R1 (zero-mean slopes undefined), R2 (dominance), R3 (clean timing set).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np

T3_FIELDS = [
    "run", "strategy", "config", "mode", "commit", "libraries_hash",
    "trials", "calls", "failed", "failed_then_succeeded", "still_failed", "retries", "status",
    "manifest_sha256", "config_sha256", "raw_sha256", "summary_sha256", "dir_sha256",
]
T9 = "sweep:brute_force:2000:t9"
CLEAN_RULE = ("retries>0; and the single trial launched with --allow-peak inside the peak "
              "window (sweep:brute_force:2000:t9)")
CORPUS_M = {"DSA_gold_standard_MEKG": 28, "metacademy_gold_standard_MEKG": 140}

FAILS: list[str] = []
N_CHECKS = 0


def check(cond: bool, msg: str) -> None:
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        FAILS.append(msg)


def num(x):
    if x is None:
        return float("nan")
    s = str(x).strip()
    if s == "":
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def close(a, b, rel=1e-9, ab=1e-12) -> bool:
    a, b = num(a), num(b)
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))


class Row(dict):
    """CSV row that records a FAIL (instead of crashing) when a column is absent."""
    src = ""

    def __missing__(self, key):
        msg = f"column '{key}' missing in {self.src}"
        if msg not in FAILS:
            FAILS.append(msg)
        return "-1"


def read_csv(p: Path):
    with open(p, newline="", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            row = Row(r)
            row.src = p.name
            rows.append(row)
        return rows


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()


def last_per_key(raw: Path):
    """Return (last record per key, all records per key) from raw.jsonl; last record wins."""
    hist: "OrderedDict[str, list]" = OrderedDict()
    with open(raw, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "key" not in r:
                continue
            hist.setdefault(r["key"], []).append(r)
    return {k: v[-1] for k, v in hist.items()}, hist


def slope_expected(size_to_vals):
    """R1: expected (slope, category_kind). category_kind in {'undefined','flat','sub','lin'}."""
    sizes = sorted(size_to_vals)
    if len(sizes) < 2 or any(len(size_to_vals[s]) == 0 for s in sizes):
        return float("nan"), "undefined"
    means = [float(np.mean(size_to_vals[s])) for s in sizes]
    if any((not np.isfinite(m)) or m <= 0 for m in means):
        return float("nan"), "undefined"
    sl = float(np.polyfit(np.log(sizes), np.log(means), 1)[0])
    kind = "flat" if sl < 0.1 else ("sub" if sl <= 0.9 else "lin")
    return sl, kind


KIND_TEXT = {"flat": "approximately flat", "sub": "sub-linear", "lin": "approximately linear"}


def dominance(a, b):
    d = a["f1"] - b["f1"]
    if abs(d) < 0.025:
        return "not distinguishable (F1 within 0.025)"
    if a["f1"] > b["f1"] and a["calls"] <= b["calls"]:
        return "A dominates B"
    if b["f1"] > a["f1"] and b["calls"] <= a["calls"]:
        return "B dominates A"
    return "trade-off"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument("--certified-t3", type=Path, default=None)
    a = ap.parse_args()

    res, out = a.results_dir.resolve(), a.output_dir.resolve()
    tdir, fdir = out / "tables", out / "figures"
    runs = sorted(d for d in res.iterdir() if d.is_dir() and (d / "manifest.json").exists())
    acc = [d for d in runs if "accuracy" in d.name]
    swp = [d for d in runs if "sweep" in d.name]
    print(f"results: {res}\noutput:  {out}\nruns: {len(runs)} ({len(acc)} accuracy, {len(swp)} sweep)")
    check(len(runs) == len(acc) + len(swp), "some run dirs are neither 'accuracy' nor 'sweep' by name")

    label = None
    if a.repo_root:
        sys.path.insert(0, str(a.repo_root))
        try:
            from scripts.analysis.tables import extract_variant_label as label  # type: ignore
        except Exception as e:  # noqa
            print(f"(could not import label helper: {e})")

    # ---- C1 RUN_INFO ----
    ri = out / "RUN_INFO.txt"
    check(ri.is_file(), "RUN_INFO.txt missing")
    if ri.is_file():
        txt = ri.read_text(encoding="utf-8")
        check("overall_gate_status: PASS" in txt, "RUN_INFO: gate status is not PASS")
        check("hashes_file: NOT SUPPLIED" not in txt, "RUN_INFO: --hashes was NOT SUPPLIED")
        check("src_diff_clean: True" in txt, "RUN_INFO: --src-diff-clean not True")
        if a.repo_root:
            for m in re.finditer(r"^\s{2}(\w+\.py): ([0-9a-f]{64})$", txt, re.M):
                p = a.repo_root / "scripts" / "analysis" / m.group(1)
                check(p.is_file() and sha256(p) == m.group(2),
                      f"RUN_INFO hash for {m.group(1)} does not match file in --repo-root")
    # ---- C7 forbidden strings ----
    if a.repo_root:
        for p in sorted((a.repo_root / "scripts" / "analysis").glob("*.py")):
            s = p.read_text(encoding="utf-8")
            for pat in ("skip-gate", "/home/", "1e-12"):
                check(pat not in s, f"forbidden '{pat}' in {p.name}")

    # ---- C2 T3 ----
    t3p = tdir / "T3_run_inventory.csv"
    check(t3p.is_file(), "T3_run_inventory.csv missing")
    if t3p.is_file():
        rows = read_csv(t3p)
        with open(t3p, newline="", encoding="utf-8") as f:
            hdr = next(csv.reader(f))
        check(hdr == T3_FIELDS, f"T3 header != validator's 18 fields: {hdr}")
        check(len(rows) == len(runs), f"T3 has {len(rows)} rows, expected {len(runs)}")
        check(all(r.get("status") in ("PASS", "PASS (resumed)") for r in rows), "T3: a row is not PASS or PASS (resumed)")
        check(all(num(r.get("trials")) > 0 for r in rows), "T3: a row has trials <= 0")
        if a.certified_t3:
            check(t3p.read_bytes().replace(b"\r\n", b"\n") == a.certified_t3.read_bytes().replace(b"\r\n", b"\n"),
                  "T3 differs from the gate-certified table_t3.csv")

    # ---- C3 T1 ----
    t1p = tdir / "T1_accuracy_benchmark.csv"
    t1 = read_csv(t1p) if t1p.is_file() else []
    check(t1p.is_file() or not acc, "T1 missing")
    exp_t1 = []
    for d in acc:
        side = json.loads((d / "strategy_config.json").read_text(encoding="utf-8"))
        cfg = side.get("config", {}) if isinstance(side.get("config"), dict) else {}
        k = cfg.get("k", cfg.get("s_max"))
        for s in read_csv(d / "summary.csv"):
            exp_t1.append((d, side.get("strategy", d.name), s, k))
    check(len(t1) == len(exp_t1), f"T1 rows {len(t1)} != summary rows {len(exp_t1)}")
    for row, (d, strat, s, k) in zip(t1, exp_t1):
        tag = f"T1[{d.name}/{s['corpus_or_size']}]"
        check(row["strategy"] == strat and row["corpus"] == s["corpus_or_size"], f"{tag} identity mismatch")
        for col in ("num_trials", "num_success", "n_with_retries", "llm_calls_mean", "precision_micro",
                    "recall_micro", "f1_micro", "precision_macro", "recall_macro", "f1_macro",
                    "shortlist_recall_micro", "shortlist_recall_macro"):
            check(close(row[col], s[col]), f"{tag} {col}: table {row[col]} vs summary.csv {s[col]}")
        m = CORPUS_M.get(s["corpus_or_size"])
        want = float("nan") if (k is None or m is None) else min(int(k), m) / m
        check(close(row["random_baseline_recall"], want), f"{tag} random baseline {row['random_baseline_recall']} vs {want}")

    # ---- C4/C5 T2 + slopes ----
    t2p, sfp = tdir / "T2_sweep_cost_summary.csv", tdir / "T2_slope_fits.csv"
    t2 = read_csv(t2p) if t2p.is_file() else []
    sf = read_csv(sfp) if sfp.is_file() else []
    check(t2p.is_file() or not swp, "T2 missing")
    t2_by = {}
    for r in t2:
        t2_by.setdefault((r["strategy"], r["variant"]), {})[int(float(r["size_n"]))] = r
    sf_by: "OrderedDict[tuple, list]" = OrderedDict()
    for r in sf:
        sf_by.setdefault((r["strategy"], r["variant"]), []).append(r)
    n_t2_expected = 0
    for d in swp:
        side = json.loads((d / "strategy_config.json").read_text(encoding="utf-8"))
        strat = side.get("strategy", d.name)
        var = label(d.name) if label else None
        if var is None:
            cands = [v for (s, v) in t2_by if s == strat]
            var = cands[0] if len(cands) == 1 else None
        if var is None:
            check(False, f"cannot determine variant label for {d.name} (pass --repo-root)")
            continue
        last, hist = last_per_key(d / "raw.jsonl")
        by_size: dict[int, list] = {}
        for k, r in last.items():
            by_size.setdefault(int(k.split(":")[2]), []).append((k, r))
        series = {"llm_calls": {}, "total_s": {}, "clean_total_s": {}}
        for n in sorted(by_size):
            tag = f"T2[{d.name} n={n}]"
            row = t2_by.get((strat, var), {}).get(n)
            check(row is not None, f"{tag} row missing")
            if row is None:
                continue
            n_t2_expected += 1
            succ = [(k, r) for k, r in by_size[n] if r.get("status") == "success"]
            fts = [k for k, _ in succ if any(x.get("status") in ("failed", "error") for x in hist[k][:-1])]
            check(int(float(row["num_trials"])) == len(by_size[n]), f"{tag} num_trials")
            check(int(float(row["num_success"])) == len(succ), f"{tag} num_success")
            check(int(float(row["failed_then_succeeded_count"])) == len(fts), f"{tag} failed_then_succeeded_count")
            check(int(float(row["n_with_retries"])) == sum(1 for _, r in succ if r["retries"] > 0), f"{tag} n_with_retries")
            check(int(float(row["total_retries"])) == sum(r["retries"] for _, r in succ), f"{tag} total_retries")
            clean = [(k, r) for k, r in succ if r["retries"] == 0 and k != T9]
            check(row["clean_exclusion_rule"] == CLEAN_RULE, f"{tag} clean_exclusion_rule text")
            check(int(float(row["clean_num_trials_post_hoc_not_preregistered"])) == len(clean), f"{tag} clean count")
            for met in ("llm_calls", "total_s", "shortlist_s", "decide_s"):
                v = np.array([float(r["metrics"][met]) for _, r in succ])
                if len(v) == 0:
                    continue
                for stat, f in (("mean", np.mean), ("median", np.median), ("min", np.min), ("max", np.max)):
                    check(close(row[f"{met}_{stat}"], f(v)), f"{tag} {met}_{stat}: {row[f'{met}_{stat}']} vs {f(v)}")
                if len(v) > 1:
                    check(close(row[f"{met}_std"], np.std(v, ddof=1)), f"{tag} {met}_std")
                lo, hi = num(row[f"{met}_ci_mean_low"]), num(row[f"{met}_ci_mean_high"])
                check(lo <= float(np.mean(v)) + 1e-9 <= hi + 2e-9 or (lo == hi), f"{tag} {met} CI does not bracket mean")
            if clean:
                cv = np.array([float(r["metrics"]["total_s"]) for _, r in clean])
                for stat, f in (("mean", np.mean), ("median", np.median), ("min", np.min), ("max", np.max)):
                    check(close(row[f"clean_total_s_{stat}_post_hoc_not_preregistered"], f(cv)), f"{tag} clean_total_s_{stat}")
            series["llm_calls"][n] = [float(r["metrics"]["llm_calls"]) for _, r in succ]
            series["total_s"][n] = [float(r["metrics"]["total_s"]) for _, r in succ]
            series["clean_total_s"][n] = [float(r["metrics"]["total_s"]) for _, r in clean]
        # slopes: expected row sequence = for each fit: main row, then exploratory row if undefined & >=3 positive sizes
        if len(series["llm_calls"]) >= 2:
            exp = []
            for met, ser, cond in (("llm_calls", series["llm_calls"], "pre-registered (all trials)"),
                                   ("total_s", series["total_s"], "pre-registered (all trials)"),
                                   ("total_s", series["clean_total_s"], "clean (post-hoc, not pre-registered)")):
                sl, kind = slope_expected(ser)
                exp.append((met, cond, sl, kind, ser))
                pos = {s: v for s, v in ser.items() if len(v) and np.mean(v) > 0}
                if kind == "undefined" and len(pos) >= 3:
                    sl2, kind2 = slope_expected(pos)
                    exp.append((met, "exploratory (positive-mean sizes only)", sl2, kind2, pos))
            got = sf_by.get((strat, var), [])
            check(len(got) == len(exp), f"T2b[{d.name}] has {len(got)} rows, expected {len(exp)}")
            for g, (met, cond, sl, kind, ser) in zip(got, exp):
                tag = f"T2b[{d.name} {met} / {cond}]"
                check(g["metric"] == met and g["condition"] == cond, f"{tag} row identity/order")
                if kind == "undefined":
                    check(math.isnan(num(g["slope"])), f"{tag} slope should be NaN (R1) but is {g['slope']}")
                    check(g["flatness_category_D2"].startswith("undefined"), f"{tag} category should be undefined: {g['flatness_category_D2']}")
                    check(math.isnan(num(g["ci_95_low"])) and math.isnan(num(g["ci_95_high"])), f"{tag} CI should be NaN")
                else:
                    check(close(g["slope"], sl, rel=1e-7, ab=1e-9), f"{tag} slope {g['slope']} vs {sl}")
                    check(g["flatness_category_D2"] == KIND_TEXT[kind], f"{tag} category {g['flatness_category_D2']} vs {KIND_TEXT[kind]}")
                    lo, hi = num(g["ci_95_low"]), num(g["ci_95_high"])
                    check(lo <= hi, f"{tag} CI low > high")
                    check(0 < num(g["n_boot_used"]) <= 10000, f"{tag} n_boot_used {g['n_boot_used']}")
                check(int(float(g["min_trials_per_size"])) == min(len(v) for v in ser.values()), f"{tag} min_trials_per_size")
    check(len(t2) == n_t2_expected, f"T2 has {len(t2)} rows, expected {n_t2_expected}")

    # ---- C6 F6 dominance + C8 F3 caps ----
    f6p = fdir / "F6_dominance.csv"
    if acc:
        check(f6p.is_file(), "F6_dominance.csv missing")
    if f6p.is_file() and t1:
        prim = [r for r in t1 if "primary" in r["variant"]] or t1
        corpora = sorted({r["corpus"] for r in prim})
        want = {}
        for c in corpora:
            pts = OrderedDict()
            for r in prim:
                if r["corpus"] == c:
                    pts[r["strategy"]] = {"calls": num(r["llm_calls_mean"]), "f1": num(r["f1_micro"])}
            names = list(pts)
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    d = pts[names[i]]["f1"] - pts[names[j]]["f1"]
                    if abs(abs(d) - 0.025) < 1e-9:
                        print(f"NOTE boundary pair (|dF1| within 1e-9 of 0.025): {c} {names[i]} vs {names[j]}")
                    want[(c, names[i], names[j])] = dominance(pts[names[i]], pts[names[j]])
        got = {(r["corpus"], r["strategy_a"], r["strategy_b"]): r["dominance"] for r in read_csv(f6p)}
        check(got == want, "F6_dominance labels differ from independent recomputation: "
              + "; ".join(f"{k}: file={got.get(k)!r} expected={want.get(k)!r}" for k in set(got) | set(want) if got.get(k) != want.get(k)))
        fig6 = fdir / "F6_cost_vs_accuracy_dominance.csv"
        if fig6.is_file():
            check(not any(r.get("variant") == "dominance_evaluation" or r.get("dominance_result") for r in read_csv(fig6)),
                  "F6 figure CSV still carries dominance placeholder rows")
    f3p = fdir / "F3_premise_check.csv"
    if f3p.is_file():
        caps = {"ann_retrieval": None, "bounded_bucket": None}
        for d in swp:
            side = json.loads((d / "strategy_config.json").read_text(encoding="utf-8"))
            nm = label(d.name) if label else d.name
            if side.get("strategy") in caps and "primary" in nm:
                cfg = side.get("config", {})
                caps[side["strategy"]] = cfg.get("k") if side["strategy"] == "ann_retrieval" else cfg.get("s_max")
        for r in read_csv(f3p):
            if caps.get(r["strategy"]) is not None:
                check(int(float(r["cap"])) == int(caps[r["strategy"]]), f"F3 cap for {r['strategy']}: {r['cap']} vs sidecar {caps[r['strategy']]}")

    # ---- C9 exploratory companions (F1b, F2b, F6b), only if present ----
    for fn, src_rows, key_cols in (("F1b_calls_scaling_logy", t2, ("llm_calls_mean",)),
                                   ("F2b_wallclock_scaling_logy", t2, ("total_s_mean", "shortlist_s_mean", "decide_s_mean"))):
        cp = fdir / f"{fn}.csv"
        if not cp.is_file():
            continue
        crow = read_csv(cp)
        check(len(crow) == len(src_rows), f"{fn}: {len(crow)} rows vs {len(src_rows)} T2 rows")
        check(all(r["status"] == "exploratory" for r in crow), f"{fn}: a row is not marked exploratory")
        for r in crow:
            src = t2_by.get((r["strategy"], r["variant"]), {}).get(int(float(r["n"])))
            if src is None:
                check(False, f"{fn}: no T2 row for {r['strategy']}/{r['variant']}/n={r['n']}")
                continue
            for c in key_cols:
                check(close(r[c], src[c]), f"{fn} {r['strategy']} n={r['n']} {c}: {r[c]} vs T2 {src[c]}")
            first = key_cols[0]
            check((r["plotted"] == "True") == (num(src[first]) > 0), f"{fn} {r['strategy']} n={r['n']}: plotted flag inconsistent with {first}")
    cp6 = fdir / "F6b_cost_vs_accuracy_logx.csv"
    if cp6.is_file() and f6p.is_file() and (fdir / "F6_cost_vs_accuracy_dominance.csv").is_file():
        base = {(r["corpus"], r["strategy"], r["variant"]): r for r in read_csv(fdir / "F6_cost_vs_accuracy_dominance.csv")}
        for r in read_csv(cp6):
            check(r["status"] == "exploratory", "F6b: row not marked exploratory")
            b = base.get((r["corpus"], r["strategy"], r["variant"]))
            check(b is not None and close(b["calls"], r["calls"]) and close(b["f1"], r["f1"]),
                  f"F6b {r['corpus']} {r['strategy']}: calls/f1 differ from F6")

    print(f"\n{N_CHECKS} checks, {len(FAILS)} failures")
    for m in FAILS[:80]:
        print("FAIL:", m)
    if len(FAILS) > 80:
        print(f"... and {len(FAILS) - 80} more")
    print("RESULT:", "PASS" if not FAILS else "FAIL")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
