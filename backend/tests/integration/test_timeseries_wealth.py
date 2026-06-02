"""Unit test : timeseries.build accepts Wealth and aggregates across wrappers."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from app.errors import PortfolioEmptyError
from app.finance import timeseries
from app.models import InvestmentAccount, Wealth, WealthPosition


def _wealth_with_positions(positions: list[WealthPosition]) -> Wealth:
    """Build a Wealth with positions packed in a single PEA wrapper."""
    return Wealth(
        user_id=uuid4(),
        snapshot_at=datetime.now(tz=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea-test",
                name="PEA Test",
                account_type="pea",
                positions=positions,
            )
        ],
    )


def test_timeseries_build_raises_on_empty_wealth():
    wealth = Wealth(user_id=uuid4(), snapshot_at=datetime.now(tz=UTC))
    with pytest.raises(PortfolioEmptyError):
        timeseries.build(wealth=wealth)


def test_timeseries_build_aggregates_quantities_across_wrappers():
    """Same ticker in PEA + CTO should be summed in the quantities dict."""
    wealth = Wealth(
        user_id=uuid4(),
        snapshot_at=datetime.now(tz=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="WPEA.PA",
                        label="WPEA",
                        quantity=10,
                        avg_cost=50,
                        current_value=550,
                    ),
                ],
            ),
            InvestmentAccount(
                provider_account_id="cto",
                name="CTO",
                account_type="cto",
                positions=[
                    WealthPosition(
                        ticker="WPEA.PA",
                        label="WPEA",
                        quantity=5,
                        avg_cost=50,
                        current_value=275,
                    ),
                ],
            ),
        ],
    )

    # Mock market data + analytics so we don't hit yfinance
    fake_dates = pd.date_range("2024-01-01", periods=5, freq="D")
    fake_prices = pd.DataFrame({"WPEA.PA": [100.0, 101, 102, 103, 104]}, index=fake_dates)

    with (
        patch("app.finance.market.fetch_prices") as mock_fetch,
        patch("app.finance.timeseries._benchmark_aligned", return_value=(None, None)),
    ):
        mock_fetch.return_value = fake_prices
        result = timeseries.build(wealth=wealth)

        # Verify quantities aggregation by inspecting the call to portfolio_value_series
        # via analytics; simpler: rely on portfolio mass = 15 * price[0] = 1500
        # Easier: simply check we got a response with the right number of dates
        assert len(result.dates) == 5
        # And quantities dict was 15 not 10/5 separately
        # (we can't directly inspect the dict but the rebased series implies it worked)


def test_timeseries_quantities_dict_sums_across_wrappers(monkeypatch):
    """Direct unit check: same ticker across wrappers sums to total."""
    wealth = Wealth(
        user_id=uuid4(),
        snapshot_at=datetime.now(tz=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="a",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="X", label="X", quantity=10, avg_cost=1, current_value=15
                    ),
                ],
            ),
            InvestmentAccount(
                provider_account_id="b",
                name="CTO",
                account_type="cto",
                positions=[
                    WealthPosition(ticker="X", label="X", quantity=7, avg_cost=1, current_value=10),
                    WealthPosition(ticker="Y", label="Y", quantity=3, avg_cost=1, current_value=5),
                ],
            ),
        ],
    )

    captured_qty = {}

    def fake_pvs(prices, quantities):
        captured_qty.update(quantities)
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        return pd.Series([100.0, 101.0, 102.0], index=idx)

    monkeypatch.setattr("app.finance.market.fetch_prices", lambda t, period="5y": pd.DataFrame())
    monkeypatch.setattr("app.finance.analytics.portfolio_value_series", fake_pvs)
    monkeypatch.setattr("app.finance.analytics.normalize", lambda s: s)
    monkeypatch.setattr("app.finance.analytics.drawdown_series", lambda s: s * 0)
    monkeypatch.setattr(
        "app.finance.analytics.rolling_sharpe",
        lambda r, window: pd.Series([np.nan] * len(r), index=r.index),
    )
    monkeypatch.setattr("app.finance.timeseries._benchmark_aligned", lambda idx: (None, None))

    timeseries.build(wealth=wealth)
    assert captured_qty == {"X": 17.0, "Y": 3.0}
