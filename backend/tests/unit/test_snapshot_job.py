"""The nightly reading asks the market only for the lines it can price in euros."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app import snapshot_job
from app.finance import market
from app.models import InvestmentAccount, Wealth, WealthPosition


def _position(ticker: str, quantity: float) -> WealthPosition:
    return WealthPosition(
        ticker=ticker, label=ticker, quantity=quantity, avg_cost=1.0, current_value=quantity * 10
    )


async def test_the_reading_asks_closes_for_euro_lines_held_only(monkeypatch):
    asked: list[list[str]] = []

    def fake(tickers: list[str]) -> dict[str, float]:
        asked.append(tickers)
        return {"CW8.PA": 520.0}

    monkeypatch.setattr(market, "latest_closes", fake)
    wealth = Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 10, 10, tzinfo=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea",
                name="PEA",
                account_type="pea",
                positions=[
                    _position("CW8.PA", 2.0),
                    _position("PE500.PA", 0.0),  # sold: nothing to price
                    _position("AAPL", 3.0),  # dollars: keeps the bank's figure
                ],
            )
        ],
    )

    assert await snapshot_job._closes(wealth) == {"CW8.PA": 520.0}
    assert asked == [["CW8.PA"]]
