"""Historical time-series service: portfolio value, drawdown, rolling Sharpe.

Mirrors `dashboard.py` orchestration style (portfolio + market + analytics →
response model). The portfolio value is computed assuming positions held
constant throughout the window — a counterfactual ("as-if-held") view, useful
for trends and risk metrics but not for true PnL since we don't store a
transaction log.
"""
import math

import numpy as np
import pandas as pd

from . import analytics, market
from .. import portfolio
from ..errors import PortfolioEmptyError
from ..models import TimeseriesResponse

BENCHMARK_TICKER = "CW8.PA"  # Amundi MSCI World, 5y+ history, broad-market proxy
ROLLING_WINDOW = 126         # trading days ≈ 6 months


def build(portfolio_data=None) -> TimeseriesResponse:
    pf = portfolio_data if portfolio_data is not None else portfolio.load()
    if not pf.positions:
        raise PortfolioEmptyError("Aucune position enregistrée.")

    tickers = [p.ticker for p in pf.positions]
    prices = market.fetch_prices(tickers, period="5y")
    quantities = {p.ticker: p.quantity for p in pf.positions}

    pf_value = analytics.portfolio_value_series(prices, quantities)
    pf_norm = analytics.normalize(pf_value)
    pf_returns = np.log(pf_value / pf_value.shift(1)).dropna()
    dd = analytics.drawdown_series(pf_value)
    rs = analytics.rolling_sharpe(pf_returns, window=ROLLING_WINDOW)

    benchmark_norm, benchmark_ticker = _benchmark_aligned(pf_value.index)

    return TimeseriesResponse(
        dates=[d.date() for d in pf_value.index],
        portfolio=pf_norm.tolist(),
        benchmark=benchmark_norm.tolist() if benchmark_norm is not None else None,
        benchmark_ticker=benchmark_ticker,
        drawdown=dd.tolist(),
        rolling_sharpe=[_nullable(v) for v in rs.reindex(pf_value.index).tolist()],
        rolling_window_days=ROLLING_WINDOW,
    )


def _benchmark_aligned(index: pd.DatetimeIndex) -> tuple[pd.Series | None, str | None]:
    """Fetch benchmark, align on portfolio dates, rebase to 100. Degrades to None on failure."""
    try:
        bench_prices = market.fetch_prices([BENCHMARK_TICKER], period="5y")
        series = bench_prices[BENCHMARK_TICKER].reindex(index).ffill().dropna()
        if len(series) < 2:
            return None, None
        return analytics.normalize(series), BENCHMARK_TICKER
    except Exception:  # noqa: BLE001 — benchmark is best-effort
        return None, None


def _nullable(v: float) -> float | None:
    return None if (v is None or math.isnan(v)) else float(v)