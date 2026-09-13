"""« La liste de l'année » — the rule, the guard, the backtest, offline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.data import wikipedia
from app.finance import momentum


def _cfg(**over) -> momentum.MomentumConfig:
    base = {
        "universe": ["cac_40"],
        "lookback_months": 12,
        "skip_months": 1,
        "top": 3,
        "min_history_months": 12,
        "review": "quarterly",
        "cost_per_trade": 0.002,
    }
    return momentum.MomentumConfig.model_validate({**base, **over})


def _daily(paths: dict[str, list[float]], start: str = "2020-01-01") -> pd.DataFrame:
    """Daily closes from monthly anchor levels, one point per business day."""
    months = len(next(iter(paths.values())))
    days = pd.bdate_range(start, periods=months * 21)
    out = {}
    for ticker, levels in paths.items():
        series = np.repeat(levels, 21)[: len(days)]
        out[ticker] = series
    return pd.DataFrame(out, index=days, dtype=float)


# ── The parser ─────────────────────────────────────────────────────────────


def test_the_ticker_column_is_read_whatever_its_position():
    page = """
    <table class="wikitable"><tr><th>Year</th><th>Close</th></tr><tr><td>1990</td><td>100</td></tr></table>
    <table class="wikitable sortable">
      <tr><th>Company</th><th>Sector</th><th>Ticker</th></tr>
      <tr><td><a href="/x">Accor</a></td><td>Hotels</td><td>AC.PA</td></tr>
      <tr><td>Adidas</td><td>Apparel</td><td>ADS.DE</td></tr>
      <tr><td>Not listed here</td><td>-</td><td>Euronext Paris:&#160;XX</td></tr>
    </table>"""

    assert wikipedia.parse_tickers(page) == ["AC.PA", "ADS.DE"]


def test_a_non_euro_venue_is_left_out():
    page = (
        """<table><tr><th>Ticker</th></tr><tr><td>ABB.ST</td></tr><tr><td>AI.PA</td></tr></table>"""
    )

    assert wikipedia.parse_tickers(page) == ["AI.PA"]


# ── The rule ───────────────────────────────────────────────────────────────


def test_the_winners_of_the_past_year_are_picked_and_the_last_month_is_skipped():
    up = [100 + 5 * i for i in range(14)]  # steady climber
    flat = [100.0] * 14
    down = [100 - 3 * i for i in range(14)]
    spike = [100.0] * 13 + [200.0]  # only the last month, which the rule ignores
    daily = _daily({"UP.PA": up, "FLAT.PA": flat, "DOWN.PA": down, "SPIKE.PA": spike})
    monthly = momentum.month_ends(daily)

    picked = momentum.select(monthly, len(monthly) - 1, _cfg(top=1))

    assert picked == ["UP.PA"]


def test_a_stock_too_young_is_not_eligible():
    old = [100 + 2 * i for i in range(14)]
    young = [np.nan] * 8 + [100 + 20 * i for i in range(6)]
    daily = _daily({"OLD.PA": old, "YOUNG.PA": young})
    monthly = momentum.month_ends(daily)

    assert momentum.select(monthly, len(monthly) - 1, _cfg(top=2)) == ["OLD.PA"]


def test_the_guard_empties_the_list_after_a_down_year():
    a = [100 - 2 * i for i in range(14)]
    b = [100 - 1 * i for i in range(14)]
    daily = _daily({"A.PA": a, "B.PA": b})
    monthly = momentum.month_ends(daily)
    at = len(monthly) - 1

    assert momentum.market_is_falling(monthly, at, _cfg())
    assert momentum.select(monthly, at, _cfg()) == []


# ── The backtest ───────────────────────────────────────────────────────────


def test_the_backtest_pays_for_every_name_bought_and_sold():
    """Two names, equal drift: without costs the strategy tracks the universe; with
    costs it lags by exactly what the reviews charged."""
    a = [100 * 1.01**i for i in range(30)]
    b = [100 * 1.01**i for i in range(30)]
    daily = _daily({"A.PA": a, "B.PA": b})

    free = momentum.backtest(daily, _cfg(top=2, cost_per_trade=0.0))
    paid = momentum.backtest(daily, _cfg(top=2, cost_per_trade=0.01))

    assert free.strategy.iloc[-1] == pytest.approx(free.universe.iloc[-1], rel=1e-6)
    assert paid.strategy.iloc[-1] < free.strategy.iloc[-1]
    first = paid.reviews[0]
    assert first.bought == ["A.PA", "B.PA"] and first.sold == []


def test_a_review_names_what_enters_and_what_leaves():
    a = [100 * 1.02**i for i in range(20)] + [100 * 1.02**19 * 0.97**i for i in range(16)]
    b = [100.0] * 20 + [100 * 1.05**i for i in range(16)]
    c = [100.0] * 36
    daily = _daily({"A.PA": a, "B.PA": b, "C.PA": c})

    bt = momentum.backtest(daily, _cfg(top=1))

    held = [r.held for r in bt.reviews if r.held]
    assert held[0] == ["A.PA"]
    assert held[-1] == ["B.PA"]
    assert any(r.sold == ["A.PA"] for r in bt.reviews)
    assert any(r.bought == ["B.PA"] for r in bt.reviews)


def test_today_says_what_changed_since_the_last_review():
    a = [100 * 1.02**i for i in range(30)]
    b = [100.0] * 30
    daily = _daily({"A.PA": a, "B.PA": b})

    picks = momentum.current(daily, _cfg(top=1))

    assert picks.held == ["A.PA"]
    assert not picks.guard_on
    assert picks.next_review > picks.as_of


def test_an_unknown_review_cadence_is_a_configuration_error():
    with pytest.raises(Exception, match="review"):
        _ = _cfg(review="weekly").review_months


def test_the_shipped_rule_loads():
    cfg = momentum.config()
    assert cfg.top >= 10 and cfg.review_months in (1, 3, 12)
