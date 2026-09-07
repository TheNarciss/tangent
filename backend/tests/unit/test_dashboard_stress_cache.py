"""Unit test: stress tests are computed once a day per portfolio composition."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.finance import dashboard, market


def _fake_prices(tickers: list[str]) -> pd.DataFrame:
    idx = pd.bdate_range("2019-01-01", "2024-12-31")
    rng = np.random.default_rng(0)
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(idx))) for t in tickers}
    return pd.DataFrame(data, index=idx)


def test_stress_tests_fetch_10y_history_once_per_day(monkeypatch):
    calls: list[tuple[list[str], str]] = []

    def fake_fetch(tickers, period="5y"):
        calls.append((list(tickers), period))
        return _fake_prices(list(tickers))

    monkeypatch.setattr(market, "fetch_prices", fake_fetch)
    dashboard._STRESS_CACHE.clear()

    qty = {"CW8.PA": 10.0, "PUST.PA": 5.0}
    first = dashboard._stress_tests(qty)
    second = dashboard._stress_tests({"PUST.PA": 5.0, "CW8.PA": 10.0})  # same composition

    assert len(calls) == 1
    assert calls[0][1] == "10y"
    assert first == second
    assert [s.id for s in first] == ["covid_2020", "inflation_2022", "regional_banks_2023"]

    # A different composition is its own entry.
    dashboard._stress_tests({"CW8.PA": 11.0})
    assert len(calls) == 2
