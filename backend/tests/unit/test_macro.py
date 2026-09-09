"""One declaration for the risk-free rate and for inflation (ADR-026).

The conftest fixture cuts every outbound call, so the default here is the
degraded path. Tests that want a live value patch their own provider.
"""

import pandas as pd
import pytest

from app.data import ecb, fred
from app.finance import macro


def test_the_risk_free_rate_comes_from_the_ecb(monkeypatch):
    monkeypatch.setattr(
        ecb, "named", lambda name, **kw: pd.Series([2.4], index=pd.to_datetime(["2026-09-09"]))
    )

    assert macro.risk_free_rate() == pytest.approx(0.024)


def test_the_risk_free_rate_falls_back_when_the_ecb_is_down():
    """The conftest fixture blocks the network: this is the production fallback."""
    assert macro.risk_free_rate() == pytest.approx(macro.config().risk_free.fallback)


def test_inflation_is_averaged_over_the_window_not_taken_from_one_month(monkeypatch):
    # +2 % a year for three years, with a noisy last month that must not dominate.
    index = pd.Series(
        [100.0, 102.0, 104.04, 110.0],
        index=pd.to_datetime(["2023-07-01", "2024-07-01", "2025-07-01", "2026-07-01"]),
    )
    monkeypatch.setattr(fred, "named", lambda name, **kw: index)

    over_three_years = (110.0 / 100.0) ** (1 / 3) - 1  # ≈ 3,2 %
    last_twelve_months = 110.0 / 104.04 - 1  # ≈ 5,7 %

    assert macro.inflation() == pytest.approx(over_three_years)
    assert macro.inflation() < last_twelve_months


def test_inflation_needs_an_observation_at_the_start_of_the_window(monkeypatch):
    index = pd.Series([100.0, 103.0], index=pd.to_datetime(["2026-01-01", "2026-07-01"]))
    monkeypatch.setattr(fred, "named", lambda name, **kw: index)

    assert macro.inflation() == pytest.approx(macro.config().inflation.fallback)


def test_inflation_falls_back_when_the_source_is_down():
    assert macro.inflation() == pytest.approx(macro.config().inflation.fallback)


def test_the_fallbacks_are_the_values_that_used_to_be_hardcoded():
    """Nothing changes for a user when the sources are unreachable."""
    assert macro.config().risk_free.fallback == pytest.approx(0.025)
    assert macro.config().inflation.fallback == pytest.approx(0.02)
