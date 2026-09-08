"""Stress tests are scored on the full basket or not at all."""

import numpy as np
import pandas as pd

from app.finance import stress


def _prices(start: str, end: str, tickers: dict[str, str]) -> pd.DataFrame:
    """One column per ticker; each starts trading at its own date (NaN before)."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(0)
    out = {}
    for t, listed in tickers.items():
        s = pd.Series(100 * np.cumprod(1 + rng.normal(0.0002, 0.01, len(idx))), index=idx)
        s[idx < pd.Timestamp(listed)] = np.nan
        out[t] = s
    return pd.DataFrame(out)


def test_period_skipped_when_one_holding_has_no_history_in_window():
    """An ETF listed in 2021 must not turn COVID-2020 into a partial-basket return."""
    prices = _prices("2019-01-01", "2024-12-31", {"OLD.PA": "2019-01-01", "NEW.PA": "2021-06-01"})
    ids = [r["id"] for r in stress.compute(prices, {"OLD.PA": 10.0, "NEW.PA": 5.0})]
    assert "covid_2020" not in ids
    assert "inflation_2022" in ids
    assert "regional_banks_2023" in ids


def test_all_periods_scored_on_a_fully_covered_basket():
    prices = _prices("2019-01-01", "2024-12-31", {"A.PA": "2019-01-01", "B.PA": "2019-01-01"})
    results = stress.compute(prices, {"A.PA": 10.0, "B.PA": 5.0})
    assert [r["id"] for r in results] == ["covid_2020", "inflation_2022", "regional_banks_2023"]
    assert all(-1.0 < r["pnl_pct"] < 1.0 for r in results)


def test_partial_basket_pnl_is_not_the_subset_pnl():
    """With the old skipna sum, COVID-2020 would have been the return of OLD.PA alone."""
    prices = _prices("2019-01-01", "2024-12-31", {"OLD.PA": "2019-01-01", "NEW.PA": "2021-06-01"})
    alone = stress.compute(prices[["OLD.PA"]], {"OLD.PA": 10.0})
    both = stress.compute(prices, {"OLD.PA": 10.0, "NEW.PA": 5.0})
    assert any(r["id"] == "covid_2020" for r in alone)
    assert not any(r["id"] == "covid_2020" for r in both)
