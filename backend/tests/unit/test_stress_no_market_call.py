"""The stress replay reads no market data at all.

It used to fetch ten years of prices per portfolio composition and cache the
result for a day, which still could not reach 2000 or 2008 — no French ETF
has that history. Replaying asset classes removes the call entirely.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.finance import market, stress
from app.models import InvestmentAccount, Wealth, WealthPosition


def test_computing_the_scenarios_never_calls_the_market(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - the point is not to reach it
        raise AssertionError("stress must not fetch prices")

    monkeypatch.setattr(market, "fetch_prices", explode)
    wealth = Wealth(
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
    results = stress.compute(wealth)
    assert len(results) >= 10
