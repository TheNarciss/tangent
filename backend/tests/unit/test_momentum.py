"""« La liste de l'année » — the rule, the guard, the backtest, offline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.data import xtrackers
from app.errors import DataSourceError
from app.finance import classification, momentum


def _cfg(**over) -> momentum.MomentumConfig:
    base = {
        "universe": ["stoxx_europe_600"],
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


# ── The universe ───────────────────────────────────────────────────────────

HOLDINGS = """ShareClass ISIN;Constituent ISIN;Constituent Name;Constituent Country;Constituent Currency ISO Code;Constituent Weighting;Constituent Rating;Constituent Main Exchange Name;Constituent Industry Classification Name
LU0328475792;NL0010273215;ASML HOLDING;Pays-Bas;EUR;0.0433594240;Baa2;Euronext Amsterdam;Technologie
LU0328475792;GB0005405286;HSBC HOLDINGS PLC;Royaume-Uni;GBP;0.0231685545;Aa3;London Stock Exchange;"Sociétés financières "
LU0328475792;FR0014010OO5;L AIR LIQUIDE;France;EUR;0.0052711370;;;inconnu
LU0328475792;FI4000552500;SAMPO CLASS A;Finlande;EUR;0.0017624400;;;"Sociétés financières "
"""


def test_the_holdings_file_is_read_by_column_name():
    lines = xtrackers.parse(HOLDINGS)

    assert [x.isin for x in lines] == [
        "NL0010273215",
        "GB0005405286",
        "FR0014010OO5",
        "FI4000552500",
    ]
    assert lines[0].currency == "EUR" and lines[0].exchange == "Euronext Amsterdam"
    assert lines[1].currency == "GBP"
    assert lines[2].exchange == ""  # a fresh listing, the fund names no venue yet
    assert lines[0].weight == pytest.approx(0.043359424)


def test_the_fund_names_the_venue_openfigi_should_answer_for():
    lines = xtrackers.parse(HOLDINGS)

    assert lines[0].venue == "NA"
    assert lines[2].venue is None  # no exchange named: the ISIN's home venue will do


def test_a_reorganized_holdings_file_is_refused():
    with pytest.raises(DataSourceError, match="colonnes absentes"):
        xtrackers.parse("ISIN;Name\nNL0010273215;ASML\n")


def test_the_universe_keeps_euro_lines_that_have_a_readable_quote(monkeypatch):
    monkeypatch.setattr(xtrackers, "constituents", lambda fund: xtrackers.parse(HOLDINGS))
    asked: dict = {}

    def _quotes(isins, prefer=None):
        asked["isins"], asked["prefer"] = isins, prefer
        return {
            "NL0010273215": classification.Quote("ASML.AS", "EUR"),
            "FI4000552500": classification.Quote("SAMPO.HE", "EUR"),
            # FR0014010OO5 is a rights line OpenFIGI does not know: absent.
        }

    monkeypatch.setattr(classification, "quotes", _quotes)

    assert momentum.universe(_cfg()) == ["ASML.AS", "SAMPO.HE"]
    assert asked["isins"] == ["NL0010273215", "FR0014010OO5", "FI4000552500"]  # euro lines only
    assert asked["prefer"] == {"NL0010273215": "NA"}


def test_an_empty_universe_is_an_error_not_a_silent_zero(monkeypatch):
    monkeypatch.setattr(xtrackers, "constituents", lambda fund: xtrackers.parse(HOLDINGS))
    monkeypatch.setattr(classification, "quotes", lambda isins, prefer=None: {})

    with pytest.raises(DataSourceError):
        momentum.universe(_cfg())


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
