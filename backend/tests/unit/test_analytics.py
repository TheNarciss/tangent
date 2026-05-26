"""Unit tests for pure finance functions (no DB, no I/O)."""

import pandas as pd
import pytest

from app.finance import analytics


def test_max_drawdown_zero_for_monotonic_series():
    """A strictly increasing series has 0 drawdown."""
    series = pd.Series([100, 110, 120, 130, 140])
    result = analytics.max_drawdown(series)
    assert result == 0.0


def test_max_drawdown_negative_for_crashing_series():
    """A peak-then-crash returns the magnitude of the crash (negative)."""
    series = pd.Series([100, 150, 90, 95])
    result = analytics.max_drawdown(series)
    # crash: peak=150 → trough=90 → -40%
    assert result == pytest.approx(-0.40, abs=0.01)


def test_max_drawdown_empty_series_returns_zero():
    """Empty input returns 0 (not NaN, not raise)."""
    result = analytics.max_drawdown(pd.Series([], dtype=float))
    assert result == 0.0
