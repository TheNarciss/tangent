"""The stress replay reads market data when it can, and answers when it cannot.

It used to fetch ten years of prices per portfolio and cache them for a day,
which still could not reach 2000 or 2008 — no French ETF has that history.
Replaying asset classes fixed the reach; measuring each line on its own price
where Yahoo has it back that far restores the precision, without ever making
the screen depend on a source that has no service contract.

Yahoo silent must therefore cost nothing but detail.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.errors import MarketDataError
from app.finance import episodes, market, stress
from app.models import InvestmentAccount, Wealth, WealthPosition


def _wealth() -> Wealth:
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 9, tzinfo=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="CW8.PA",
                        label="Monde",
                        quantity=10.0,
                        avg_cost=100.0,
                        current_value=1_000.0,
                    )
                ],
            )
        ],
    )


def test_a_silent_market_still_produces_every_scenario(monkeypatch):
    def explode(*args: object, **kwargs: object) -> None:
        raise MarketDataError("Yahoo muet")

    episodes._QUOTED.clear()
    monkeypatch.setattr(market, "fetch_prices", explode)

    results = stress.compute(_wealth())

    assert len(results) >= 10
    assert all(r.pnl_pct is not None for r in results)


def test_a_silent_market_is_asked_once_per_line_not_once_per_episode(monkeypatch):
    """Ten episodes must not mean ten failed calls for the same line."""
    calls: list[object] = []

    def explode(tickers: list[str], **kwargs: object) -> None:
        calls.append(tickers)
        raise MarketDataError("Yahoo muet")

    episodes._QUOTED.clear()
    monkeypatch.setattr(market, "fetch_prices", explode)

    episodes.measure("CW8.PA", "yahoo", "EUR", ("2020-02-19", "2020-03-23"))
    episodes.measure("CW8.PA", "yahoo", "EUR", ("2008-06-01", "2009-03-09"))

    assert len(calls) == 1


def test_the_declared_figures_are_unchanged_when_no_source_answers(monkeypatch):
    monkeypatch.setattr(stress.episodes, "measure", lambda *a, **k: None)
    scenario = next(s for s in stress.config().scenarios if s.id == "gfc_2008")

    pocket = stress.Pocket("equity_world", 1_000.0)

    assert stress.pocket_return(pocket, scenario) == pytest.approx(scenario.returns["equity_world"])
