"""Historical time-series service: portfolio value, drawdown, rolling Sharpe.

Consumes the Wealth domain model (Phase 2). Computes an "as-if-held" view
on the user's current positions — no transaction log is stored, so we cannot
reconstruct the true historical net worth.

Scope limitation: the timeseries covers titres only (positions held in
investment wrappers). Livrets balances and loan outstanding amounts are
not historised by Powens, so they are not included. A future PR may
introduce a daily snapshot table to enable a full net-worth time-series.
"""

import math

import numpy as np
import pandas as pd

from ..errors import PortfolioEmptyError
from ..models import TimeseriesResponse, Wealth
from . import analytics, classification, market

BENCHMARK_TICKER = "CW8.PA"  # Amundi MSCI World, 5y+ history, broad-market proxy
# Classes the world-equity benchmark is a fair yardstick for. A bond or gold
# portfolio compared to world equities is a comparison without object, so it
# gets no benchmark line at all rather than a misleading one.
BENCHMARKABLE_CLASSES = frozenset(
    {
        "equity_world",
        "equity_us",
        "equity_us_tech",
        "equity_sector",
        "equity_europe",
        "equity_japan",
        "equity_emerging",
    }
)
ROLLING_WINDOW = 126  # trading days ≈ 6 months


def build(wealth: Wealth) -> TimeseriesResponse:
    """Build the historical timeseries from the user's Wealth.

    Aggregates quantities across ALL investment accounts (PEA, CTO, AV).
    Positions of the same ticker held in different wrappers are summed.
    """
    positions = wealth.all_positions
    if not positions:
        raise PortfolioEmptyError("Aucune position enregistrée.")

    # Sum quantities by ticker (same ticker can appear in multiple wrappers)
    quantities: dict[str, float] = {}
    for p in positions:
        quantities[p.ticker] = quantities.get(p.ticker, 0.0) + p.quantity

    tickers = list(quantities.keys())
    prices = market.fetch_prices(tickers, period="5y")

    pf_value = analytics.portfolio_value_series(prices, quantities)
    pf_norm = analytics.normalize(pf_value)
    pf_returns = np.log(pf_value / pf_value.shift(1)).dropna()
    dd = analytics.drawdown_series(pf_value)
    rs = analytics.rolling_sharpe(pf_returns, window=ROLLING_WINDOW)

    benchmark_norm, benchmark_ticker = (None, None)
    if _is_mostly_equity(positions):
        benchmark_norm, benchmark_ticker = _benchmark_aligned(pf_value.index)

    return TimeseriesResponse(
        dates=[d.date() for d in pf_value.index],
        portfolio=pf_norm.tolist(),
        benchmark=benchmark_norm.tolist() if benchmark_norm is not None else None,
        benchmark_ticker=benchmark_ticker,
        drawdown=dd.tolist(),
        rolling_sharpe=[_nullable(v) for v in rs.reindex(pf_value.index).tolist()],
        rolling_window_days=ROLLING_WINDOW,
        is_backtest=True,
    )


def _is_mostly_equity(positions) -> bool:
    """True when equities carry most of the value: only then is the world index a yardstick."""
    classes = classification.classify_many([(p.label, p.isin) for p in positions])
    equity = sum(
        p.current_value
        for p, what in zip(positions, classes, strict=True)
        if what.asset_class in BENCHMARKABLE_CLASSES
    )
    total = sum(p.current_value for p in positions)
    return total > 0 and equity / total > 0.5


def _benchmark_aligned(index: pd.DatetimeIndex) -> tuple[pd.Series | None, str | None]:
    """Fetch benchmark, align on portfolio dates, rebase to 100. Degrades to None on failure."""
    try:
        bench_prices = market.fetch_prices([BENCHMARK_TICKER], period="5y")
        series = bench_prices[BENCHMARK_TICKER].reindex(index).ffill().dropna()
        if len(series) < 2:
            return None, None
        return analytics.normalize(series), BENCHMARK_TICKER
    except Exception:
        return None, None


def _nullable(v: float) -> float | None:
    return None if (v is None or math.isnan(v)) else float(v)
