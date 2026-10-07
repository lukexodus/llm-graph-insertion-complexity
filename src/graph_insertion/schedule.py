"""
schedule.py — INFRA-005
=======================
Peak-hour guard helpers for DeepSeek API scheduling.

Decisions:
  - Peak window definition per [D-37]: Mon–Fri, 01:00–04:00 and 06:00–10:00 UTC.
  - Chinese public holidays are NOT modelled. They are off-peak in reality,
    so ignoring them is conservative: we may incorrectly flag a Chinese holiday
    as peak, but we will never incorrectly flag a true peak hour as off-peak.
    This is the safe direction for budget control.
"""

from __future__ import annotations

import datetime
from typing import Union

# Peak windows as (start_hour_inclusive, end_hour_exclusive) in UTC, Mon–Fri only.
# [D-37]: 01:00–04:00 and 06:00–10:00 UTC.
_PEAK_WINDOWS: list[tuple[int, int]] = [(1, 4), (6, 10)]


def is_deepseek_peak(dt_utc: datetime.datetime) -> bool:
    """Return True if *dt_utc* falls in a DeepSeek peak-pricing window.

    Peak is defined as Monday–Friday (weekday 0–4) during either
    01:00–03:59:59 UTC or 06:00–09:59:59 UTC [D-37].

    Chinese public holidays are NOT modelled (ignoring them is conservative —
    they are off-peak in reality, so we may over-report peak, never under-report).

    Parameters
    ----------
    dt_utc:
        A timezone-aware or naive datetime in UTC.
    """
    # weekday(): 0 = Monday … 6 = Sunday
    if dt_utc.weekday() >= 5:  # Saturday or Sunday → always off-peak
        return False
    h = dt_utc.hour
    m = dt_utc.minute
    # Fractional hour for boundary comparisons
    frac_hour = h + m / 60.0
    for start, end in _PEAK_WINDOWS:
        if start <= frac_hour < end:
            return True
    return False


def window_intersects_peak(
    start_utc: datetime.datetime,
    duration_s: Union[int, float],
) -> bool:
    """Return True if the time window [start_utc, start_utc + duration_s] overlaps any peak.

    Checks one sample point per minute across the window (upper-bound 24 × 60 = 1440 checks).

    Parameters
    ----------
    start_utc:
        Window start in UTC (naive or aware).
    duration_s:
        Estimated duration in seconds.
    """
    end_utc = start_utc + datetime.timedelta(seconds=duration_s)
    # Check at 1-minute resolution
    step = datetime.timedelta(minutes=1)
    current = start_utc
    while current <= end_utc:
        if is_deepseek_peak(current):
            return True
        current += step
    return False


def format_peak_status(dt_utc: datetime.datetime) -> str:
    """Return a human-readable peak/off-peak status string for *dt_utc*."""
    ph_time = dt_utc + datetime.timedelta(hours=8)
    peak = is_deepseek_peak(dt_utc)
    status = "PEAK (charged at peak rates)" if peak else "off-peak"
    return (
        f"Current UTC:  {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Philippine:   {ph_time.strftime('%Y-%m-%d %H:%M:%S')} PHT (UTC+8)\n"
        f"DeepSeek:     {status}"
    )
