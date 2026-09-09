"""A non-converged solve is an error, never an "optimal" allocation."""

from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from app.errors import SolverError
from app.finance import analytics, market, optimizer
from app.models import InvestmentAccount, OptimizerRequest, Wealth, WealthPosition


def _wealth() -> Wealth:
    return Wealth(
        user_id=uuid4(),
        snapshot_at=datetime.now(tz=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea-1",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="A.PA", label="A", quantity=10, avg_cost=10, current_value=120
                    ),
                    WealthPosition(
                        ticker="B.PA", label="B", quantity=5, avg_cost=20, current_value=80
                    ),
                ],
            )
        ],
    )


def _fake_prices(tickers, period="5y"):
    idx = pd.bdate_range("2021-01-01", "2024-12-31")
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {t: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(idx))) for t in tickers}, index=idx
    )


def test_build_raises_when_solver_does_not_converge(monkeypatch):
    monkeypatch.setattr(market, "fetch_prices", _fake_prices)

    def failed(*args, **kwargs):
        return {
            "weights": [0.5, 0.5],
            "expected_return": 0.05,
            "volatility": 0.1,
            "sharpe": 0.3,
            "success": False,
        }

    monkeypatch.setattr(analytics, "_solve_slsqp", failed)
    with pytest.raises(SolverError):
        optimizer.build(OptimizerRequest(objective="min_variance"), wealth=_wealth())


def test_build_succeeds_on_well_posed_input(monkeypatch):
    monkeypatch.setattr(market, "fetch_prices", _fake_prices)
    resp = optimizer.build(OptimizerRequest(objective="min_variance"), wealth=_wealth())
    assert sum(resp.optimal.weights) == pytest.approx(1.0)
