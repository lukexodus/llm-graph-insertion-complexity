"""
bootstrap.py — Percentile Bootstrap Intervals for Empirical Analysis
===================================================================
Implements Decision D1 & Section 4.1 of the Phase 4 Analysis Plan:
- 95% percentile bootstrap over trials
- 10,000 resamples default
- Fixed seed (default 42) for reproducibility
- High performance vectorized resampling with numpy
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Sequence, Tuple
import numpy as np


def bootstrap_ci(
    data: Sequence[float],
    statistic_fn: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 10_000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Compute a two-sided percentile bootstrap confidence interval.

    Returns (lower_bound, upper_bound).
    """
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    arr = np.asarray(clean_data, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return (float("nan"), float("nan"))
    if n == 1:
        return (float(arr[0]), float(arr[0]))

    rng = np.random.default_rng(seed)
    # Vectorized bootstrap generation: shape (n_resamples, n)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resamples = arr[indices]

    if statistic_fn is np.mean or statistic_fn == np.mean:
        boot_stats = np.mean(resamples, axis=1)
    elif statistic_fn is np.median or statistic_fn == np.median:
        boot_stats = np.median(resamples, axis=1)
    else:
        boot_stats = np.apply_along_axis(statistic_fn, 1, resamples)

    alpha = (1.0 - ci_level) / 2.0
    low_pct = 100.0 * alpha
    high_pct = 100.0 * (1.0 - alpha)

    low = float(np.percentile(boot_stats, low_pct))
    high = float(np.percentile(boot_stats, high_pct))
    return (low, high)


def compute_series_stats(
    data: Sequence[float],
    seed: int = 42,
    n_resamples: int = 10_000,
) -> Dict[str, float]:
    """Compute descriptive statistics + 95% bootstrap CI for mean and median."""
    clean_data = [x for x in data if x is not None and not np.isnan(x)]
    arr = np.asarray(clean_data, dtype=np.float64)
    if len(arr) == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "median": float("nan"),
            "ci_mean_low": float("nan"),
            "ci_mean_high": float("nan"),
            "ci_median_low": float("nan"),
            "ci_median_high": float("nan"),
        }

    mean_val = float(np.mean(arr))
    median_val = float(np.median(arr))
    std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    mean_low, mean_high = bootstrap_ci(arr, statistic_fn=np.mean, n_resamples=n_resamples, seed=seed)
    med_low, med_high = bootstrap_ci(arr, statistic_fn=np.median, n_resamples=n_resamples, seed=seed)

    return {
        "n": len(arr),
        "mean": mean_val,
        "std": std_val,
        "min": min_val,
        "max": max_val,
        "median": median_val,
        "ci_mean_low": mean_low,
        "ci_mean_high": mean_high,
        "ci_median_low": med_low,
        "ci_median_high": med_high,
    }
