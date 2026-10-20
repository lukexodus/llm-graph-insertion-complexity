"""
stats.py — Statistical Modeling, Flatness Fits, and Dominance Logic
===================================================================
Implements Sections 4.2, 4.3, and Figure F6 rules from Phase 4 Analysis Plan
and APC Rules R1 and R2:
- OLS regression of log(mean_cost) on log(n)
- R1 Zero-mean rule: log-log fit with any non-positive or non-finite size mean is
  UNDEFINED (NaN slope, no CI, no D2 category, category text "undefined (zero mean at n=...)").
  No clamp. Bootstrap resamples with zero-mean sizes are dropped and n_boot_used reported.
- Categorization into pre-registered flatness bins (D2):
    * slope < 0.1: "approximately flat"
    * 0.1 <= slope <= 0.9: "sub-linear"
    * slope > 0.9: "approximately linear"
- R2 Mechanical Pareto dominance rule:
    * |F1 diff| < 0.025: "not distinguishable (F1 within 0.025)" regardless of calls
    * |F1 diff| >= 0.025: A dominates B if F1_A > F1_B and calls_A <= calls_B; otherwise "trade-off".
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple
import numpy as np


def classify_slope_flatness(slope: float) -> str:
    """Classify log-log scaling slope per Decision D2."""
    if np.isnan(slope):
        return "undefined"
    if slope < 0.1:
        return "approximately flat"
    elif slope <= 0.9:
        return "sub-linear"
    else:
        return "approximately linear"


def fit_log_log_slope(
    sizes: Sequence[int | float],
    mean_costs: Sequence[float],
) -> Tuple[float, float, float]:
    """Fits OLS: log(mean_cost) = slope * log(n) + intercept.

    Per Rule R1: A log-log fit with any size whose mean is <= 0 or non-finite
    is UNDEFINED (returns NaN slope, intercept, and r_squared). No clamp.


    Returns (slope, intercept, r_squared).
    """
    x_arr = np.asarray(sizes, dtype=np.float64)
    y_arr = np.asarray(mean_costs, dtype=np.float64)

    if len(x_arr) < 2 or len(y_arr) < 2 or len(x_arr) != len(y_arr):
        return (float("nan"), float("nan"), float("nan"))

    if np.any(x_arr <= 0) or not np.all(np.isfinite(x_arr)):
        return (float("nan"), float("nan"), float("nan"))

    if np.any(y_arr <= 0) or not np.all(np.isfinite(y_arr)):
        return (float("nan"), float("nan"), float("nan"))

    x = np.log(x_arr)
    y = np.log(y_arr)

    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_yy = np.sum((y - y_mean) ** 2)

    if ss_xx == 0 or np.isnan(ss_xy):
        return (0.0, float(y_mean), 0.0)

    slope = float(ss_xy / ss_xx)
    intercept = float(y_mean - slope * x_mean)
    r_squared = float((ss_xy ** 2) / (ss_xx * ss_yy)) if ss_yy > 0 else 1.0

    return (slope, intercept, r_squared)


def bootstrap_slope_ci(
    size_to_trials: Dict[int, List[float]],
    n_resamples: int = 10_000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float, str, float, int]:
    """Resample trials within each size, compute mean per size, and fit OLS slope.

    Per Rule R1:
    - If any size has no trials or an empirical mean <= 0 / non-finite:
      returns (NaN, NaN, NaN, "undefined (zero mean at n=...)", NaN, 0).
    - In bootstrap resamples, drops any resample with a zero-mean size.
    - Reports n_boot_used (NaN CIs if n_boot_used == 0).

    Returns:
      (point_estimate_slope, ci_low, ci_high, flatness_category, r_squared, n_boot_used)
    """
    sizes = sorted(size_to_trials.keys())
    if len(sizes) < 2:
        return (float("nan"), float("nan"), float("nan"), "undefined (< 2 sizes)", float("nan"), 0)

    empty_sizes = [s for s in sizes if len(size_to_trials[s]) == 0]
    if empty_sizes:
        cat_str = f"undefined (no trials at n={', '.join(str(s) for s in empty_sizes)})"
        return (float("nan"), float("nan"), float("nan"), cat_str, float("nan"), 0)

    emp_means = [float(np.mean(size_to_trials[s])) for s in sizes]
    zero_sizes = [sizes[i] for i, m in enumerate(emp_means) if m <= 0 or not np.isfinite(m)]
    if zero_sizes:
        cat_str = f"undefined (zero mean at n={', '.join(str(s) for s in zero_sizes)})"
        return (float("nan"), float("nan"), float("nan"), cat_str, float("nan"), 0)

    point_slope, _, r_squared = fit_log_log_slope(sizes, emp_means)
    if np.isnan(point_slope):
        return (float("nan"), float("nan"), float("nan"), "undefined", float("nan"), 0)

    rng = np.random.default_rng(seed)
    trials_arrays = [np.asarray(size_to_trials[s], dtype=np.float64) for s in sizes]
    log_sizes = np.log(np.asarray(sizes, dtype=np.float64))
    x_mean = np.mean(log_sizes)
    ss_xx = np.sum((log_sizes - x_mean) ** 2)

    if ss_xx == 0:
        return (point_slope, point_slope, point_slope, classify_slope_flatness(point_slope), r_squared, n_resamples)

    valid_slopes: List[float] = []
    for _ in range(n_resamples):
        b_means = np.empty(len(sizes), dtype=np.float64)
        has_zero_or_nonfinite = False
        for s_idx, t_arr in enumerate(trials_arrays):
            resamp = rng.choice(t_arr, size=len(t_arr), replace=True)
            m = np.mean(resamp)
            if m <= 0 or not np.isfinite(m):
                has_zero_or_nonfinite = True
                break
            b_means[s_idx] = m
        if has_zero_or_nonfinite:
            continue

        log_b_means = np.log(b_means)
        y_mean = np.mean(log_b_means)
        ss_xy = np.sum((log_sizes - x_mean) * (log_b_means - y_mean))
        valid_slopes.append(float(ss_xy / ss_xx))

    n_boot_used = len(valid_slopes)
    if n_boot_used == 0:
        ci_low = float("nan")
        ci_high = float("nan")
    else:
        alpha = (1.0 - ci_level) / 2.0
        ci_low = float(np.percentile(valid_slopes, 100.0 * alpha))
        ci_high = float(np.percentile(valid_slopes, 100.0 * (1.0 - alpha)))

    category = classify_slope_flatness(point_slope)
    return (point_slope, ci_low, ci_high, category, r_squared, n_boot_used)


def evaluate_dominance(
    point_a: Dict[str, float],
    point_b: Dict[str, float],
    f1_delta_threshold: float = 0.025,
) -> str:
    """Evaluate mechanical dominance between strategy A and strategy B per D5, D3, and Rule R2.

    point_a and point_b contain keys: 'calls' and 'f1'.

    Per Rule R2:
    - |F1 difference| < 0.025 => "not distinguishable (F1 within 0.025)", regardless of calls.
    - At or above 0.025: A dominates B if A has higher F1 and calls <= B's;
      B dominates A if B has higher F1 and calls <= A's;
      otherwise "trade-off".
    """
    calls_a, f1_a = point_a["calls"], point_a["f1"]
    calls_b, f1_b = point_b["calls"], point_b["f1"]

    f1_diff = f1_a - f1_b

    if abs(f1_diff) < f1_delta_threshold:
        return "not distinguishable (F1 within 0.025)"

    if f1_a > f1_b and calls_a <= calls_b:
        return "A dominates B"
    elif f1_b > f1_a and calls_b <= calls_a:
        return "B dominates A"
    else:
        return "trade-off"

