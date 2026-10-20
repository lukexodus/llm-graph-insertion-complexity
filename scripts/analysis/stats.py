"""
stats.py — Statistical Modeling, Flatness Fits, and Dominance Logic
===================================================================
Implements Sections 4.2, 4.3, and Figure F6 rules from Phase 4 Analysis Plan:
- OLS regression of log(mean_cost) on log(n)
- Bootstrap confidence interval for slope (resampling trials within size)
- Categorization into pre-registered flatness bins (D2):
    * slope < 0.1: "approximately flat"
    * 0.1 <= slope <= 0.9: "sub-linear"
    * slope > 0.9: "approximately linear"
- Mechanical Pareto dominance rule (D5) with 0.025 F1 equivalence band (D3).
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple
import numpy as np


def classify_slope_flatness(slope: float) -> str:
    """Classify log-log scaling slope per Decision D2."""
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

    Returns (slope, intercept, r_squared).
    """
    x_arr = np.asarray(sizes, dtype=np.float64)
    y_arr = np.asarray(mean_costs, dtype=np.float64)

    # Filter out non-positive sizes or costs safely
    # If cost is 0, clamp to small epsilon for log calculation
    y_clamped = np.where(y_arr <= 0, 1e-12, y_arr)

    x = np.log(x_arr)
    y = np.log(y_clamped)

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
) -> Tuple[float, float, float, str, float]:
    """Resample trials within each size, compute mean per size, and fit OLS slope.

    Returns (point_estimate_slope, ci_low, ci_high, flatness_category, r_squared).
    """
    sizes = sorted(size_to_trials.keys())
    emp_means = [float(np.mean(size_to_trials[s])) if len(size_to_trials[s]) > 0 else 0.0 for s in sizes]
    point_slope, _, r_squared = fit_log_log_slope(sizes, emp_means)

    rng = np.random.default_rng(seed)
    boot_slopes = np.empty(n_resamples, dtype=np.float64)

    trials_arrays = [
        np.asarray(size_to_trials[s], dtype=np.float64) if len(size_to_trials[s]) > 0 else np.array([0.0])
        for s in sizes
    ]
    log_sizes = np.log(np.asarray(sizes, dtype=np.float64))
    x_mean = np.mean(log_sizes)
    ss_xx = np.sum((log_sizes - x_mean) ** 2)

    if ss_xx == 0:
        return (point_slope, point_slope, point_slope, classify_slope_flatness(point_slope), r_squared)

    for i in range(n_resamples):
        b_means = np.empty(len(sizes), dtype=np.float64)
        for s_idx, t_arr in enumerate(trials_arrays):
            resamp = rng.choice(t_arr, size=len(t_arr), replace=True)
            b_means[s_idx] = np.mean(resamp)

        b_clamped = np.where(b_means <= 0, 1e-12, b_means)
        log_b_means = np.log(b_clamped)
        y_mean = np.mean(log_b_means)
        ss_xy = np.sum((log_sizes - x_mean) * (log_b_means - y_mean))
        boot_slopes[i] = ss_xy / ss_xx

    alpha = (1.0 - ci_level) / 2.0
    ci_low = float(np.percentile(boot_slopes, 100.0 * alpha))
    ci_high = float(np.percentile(boot_slopes, 100.0 * (1.0 - alpha)))
    category = classify_slope_flatness(point_slope)

    return (point_slope, ci_low, ci_high, category, r_squared)


def evaluate_dominance(
    point_a: Dict[str, float],
    point_b: Dict[str, float],
    f1_delta_threshold: float = 0.025,
) -> str:
    """Evaluate mechanical dominance between strategy A and strategy B per D5 and D3.

    point_a and point_b contain keys: 'calls' and 'f1'.

    Returns one of:
      - "A dominates B"
      - "B dominates A"
      - "not distinguishable" (if F1 difference <= threshold and calls are similar)
      - "trade-off" (one has higher F1 but also higher calls)
    """
    calls_a, f1_a = point_a["calls"], point_a["f1"]
    calls_b, f1_b = point_b["calls"], point_b["f1"]

    f1_diff = f1_a - f1_b

    if abs(f1_diff) <= f1_delta_threshold:
        # F1 is indistinguishable within empirical run-to-run noise band (D3)
        if calls_a < calls_b:
            return "A dominates B (calls advantage, F1 equivalent)"
        elif calls_b < calls_a:
            return "B dominates A (calls advantage, F1 equivalent)"
        else:
            return "not distinguishable"

    # F1 difference is distinguishable (> 0.025)
    if f1_a > f1_b and calls_a <= calls_b:
        return "A dominates B"
    elif f1_b > f1_a and calls_b <= calls_a:
        return "B dominates A"
    else:
        return "trade-off"
