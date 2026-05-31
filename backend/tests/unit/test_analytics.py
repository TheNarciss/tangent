"""Unit tests for pure finance functions (no DB, no I/O)."""

import numpy as np
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


# ── cvar_95 ──────────────────────────────────────────────────────────────────


def test_cvar_negative_on_losing_returns():
    """CVaR is the mean of the 5% worst returns — negative when losses dominate the tail."""
    rets = pd.Series([-0.10, -0.08, -0.05, -0.02, 0.01, 0.02, 0.03, 0.05, 0.10, 0.15])
    result = analytics.cvar_95(rets)
    assert result < 0


def test_cvar_zero_or_negative_on_all_positive_returns():
    """All-positive returns: CVaR is the worst few — should be the smallest positive value, ≥ 0."""
    rets = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10])
    result = analytics.cvar_95(rets)
    # Worst 5% should still be a small positive number
    assert result >= 0


# ── portfolio_value_series ──────────────────────────────────────────────────


def test_portfolio_value_single_asset_scales_linearly():
    """For 1 ticker with qty=10, the portfolio value at each date = 10 × price."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0, 120.0]})
    result = analytics.portfolio_value_series(prices, {"AAA": 10.0})
    assert list(result) == [1000.0, 1100.0, 1200.0]


def test_portfolio_value_aggregates_multiple_tickers():
    """For 2 tickers, value = qty_1 × price_1 + qty_2 × price_2 at each date."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0], "BBB": [50.0, 60.0]})
    result = analytics.portfolio_value_series(prices, {"AAA": 1.0, "BBB": 2.0})
    # date 0: 1×100 + 2×50 = 200 ; date 1: 1×110 + 2×60 = 230
    assert list(result) == [200.0, 230.0]


# ── normalize ───────────────────────────────────────────────────────────────


def test_normalize_rebases_to_100():
    """normalize([50, 100, 150], base=100) → [100, 200, 300]."""
    result = analytics.normalize(pd.Series([50.0, 100.0, 150.0]), base=100.0)
    assert list(result) == [100.0, 200.0, 300.0]


def test_normalize_default_base_is_100():
    """Default base is 100; first value becomes 100."""
    result = analytics.normalize(pd.Series([200.0, 400.0]))
    assert result.iloc[0] == 100.0
    assert result.iloc[1] == 200.0


# ── daily_log_returns ───────────────────────────────────────────────────────


def test_log_returns_drops_first_nan_row():
    """The first row is dropped (no return possible without a prior price)."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0, 121.0]})
    result = analytics.daily_log_returns(prices)
    # Two returns: ln(110/100) ≈ 0.0953, ln(121/110) ≈ 0.0953
    assert len(result) == 2
    assert result["AAA"].iloc[0] == pytest.approx(np.log(110 / 100), abs=1e-9)


def test_log_returns_zero_for_flat_series():
    """A flat price series produces zero log returns."""
    prices = pd.DataFrame({"AAA": [100.0, 100.0, 100.0]})
    result = analytics.daily_log_returns(prices)
    assert all(result["AAA"] == 0.0)
