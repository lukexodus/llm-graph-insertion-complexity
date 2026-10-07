"""
tests/test_schedule.py — INFRA-005
===================================
Unit tests for DeepSeek peak-pricing window helpers in graph_insertion.schedule.

Decisions:
  - [D-37]: Peak = Mon–Fri 01:00–04:00 and 06:00–10:00 UTC.
    All other times (weekends, off-peak hours) are off-peak.
    Chinese public holidays are not modelled (conservative approach).
"""

from __future__ import annotations

import datetime
import pytest

from graph_insertion.schedule import (
    format_peak_status,
    is_deepseek_peak,
    window_intersects_peak,
)


class TestIsDeepSeekPeak:
    """Test is_deepseek_peak across boundary hours and day transitions."""

    # 2026-10-05 is a Monday (weekday 0)
    # 2026-10-06 is a Tuesday (weekday 1)
    # 2026-10-09 is a Friday (weekday 4)
    # 2026-10-10 is a Saturday (weekday 5)
    # 2026-10-11 is a Sunday (weekday 6)

    def test_weekday_peak_window_1(self):
        """01:00 to 04:00 UTC on Monday is peak."""
        # 01:00:00 is peak (start boundary)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 1, 0, 0)) is True
        # 02:30:00 is peak (mid-window)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 2, 30, 0)) is True
        # 03:59:00 is peak (just before end boundary)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 3, 59, 0)) is True

    def test_weekday_peak_window_1_boundary_exit(self):
        """04:00:00 UTC on Monday is off-peak."""
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 4, 0, 0)) is False

    def test_weekday_inter_peak_offpeak(self):
        """04:00 to 06:00 UTC on Monday is off-peak."""
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 4, 30, 0)) is False
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 5, 0, 0)) is False
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 5, 59, 0)) is False

    def test_weekday_peak_window_2(self):
        """06:00 to 10:00 UTC on Monday is peak."""
        # 06:00:00 is peak (start boundary)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 6, 0, 0)) is True
        # 08:00:00 is peak (mid-window)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 8, 0, 0)) is True
        # 09:59:00 is peak (just before end boundary)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 9, 59, 0)) is True

    def test_weekday_peak_window_2_boundary_exit(self):
        """10:00:00 UTC on Monday is off-peak."""
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 10, 0, 0)) is False

    def test_weekday_evening_offpeak(self):
        """10:00 to 24:00 UTC on Monday is off-peak."""
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 12, 0, 0)) is False
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 18, 0, 0)) is False
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 23, 59, 0)) is False

    def test_weekday_early_morning_offpeak(self):
        """00:00 to 01:00 UTC on Monday is off-peak."""
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 0, 0, 0)) is False
        assert is_deepseek_peak(datetime.datetime(2026, 10, 5, 0, 59, 0)) is False

    def test_friday_saturday_transition(self):
        """Friday late is off-peak, Saturday all day is off-peak."""
        # Friday 09:00 is peak
        assert is_deepseek_peak(datetime.datetime(2026, 10, 9, 9, 0, 0)) is True
        # Friday 23:59 is off-peak
        assert is_deepseek_peak(datetime.datetime(2026, 10, 9, 23, 59, 0)) is False
        # Saturday 00:01 is off-peak
        assert is_deepseek_peak(datetime.datetime(2026, 10, 10, 0, 1, 0)) is False
        # Saturday at 02:00 (peak hour on weekdays, but Saturday is off-peak!)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 10, 2, 0, 0)) is False
        # Saturday at 07:00 (peak hour on weekdays, but Saturday is off-peak!)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 10, 7, 0, 0)) is False

    def test_sunday_monday_transition(self):
        """Sunday is entirely off-peak, Monday turns peak at 01:00."""
        # Sunday at 02:00 (off-peak)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 11, 2, 0, 0)) is False
        # Sunday at 08:00 (off-peak)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 11, 8, 0, 0)) is False
        # Sunday 23:59 (off-peak)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 11, 23, 59, 0)) is False
        # Monday 00:30 (off-peak)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 12, 0, 30, 0)) is False
        # Monday 01:00 (PEAK!)
        assert is_deepseek_peak(datetime.datetime(2026, 10, 12, 1, 0, 0)) is True


class TestWindowIntersectsPeak:
    """Test window_intersects_peak helper."""

    def test_window_fully_within_offpeak(self):
        # Monday 12:00 to 14:00 (2 hours)
        start = datetime.datetime(2026, 10, 5, 12, 0, 0)
        assert window_intersects_peak(start, duration_s=7200) is False

    def test_window_fully_within_peak(self):
        # Monday 02:00 to 03:00 (1 hour)
        start = datetime.datetime(2026, 10, 5, 2, 0, 0)
        assert window_intersects_peak(start, duration_s=3600) is True

    def test_window_spanning_into_peak(self):
        # Monday 00:45 with 30 min duration -> ends 01:15, intersects peak at 01:00
        start = datetime.datetime(2026, 10, 5, 0, 45, 0)
        assert window_intersects_peak(start, duration_s=1800) is True

    def test_window_starting_in_peak_and_exiting(self):
        # Monday 03:50 with 20 min duration -> ends 04:10, starts in peak
        start = datetime.datetime(2026, 10, 5, 3, 50, 0)
        assert window_intersects_peak(start, duration_s=1200) is True

    def test_weekend_window_during_weekday_peak_hours(self):
        # Saturday 01:00 to 05:00 -> weekend is never peak
        start = datetime.datetime(2026, 10, 10, 1, 0, 0)
        assert window_intersects_peak(start, duration_s=14400) is False


class TestFormatPeakStatus:
    """Test format_peak_status output format."""

    def test_format_offpeak(self):
        dt = datetime.datetime(2026, 10, 5, 12, 0, 0)
        s = format_peak_status(dt)
        assert "12:00:00 UTC" in s
        assert "20:00:00 PHT" in s  # 12 + 8 = 20
        assert "off-peak" in s

    def test_format_peak(self):
        dt = datetime.datetime(2026, 10, 5, 2, 0, 0)
        s = format_peak_status(dt)
        assert "02:00:00 UTC" in s
        assert "10:00:00 PHT" in s  # 2 + 8 = 10
        assert "PEAK" in s
