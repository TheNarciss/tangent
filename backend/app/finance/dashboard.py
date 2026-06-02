"""Dashboard service: composes portfolio + market + analytics + diagnostic."""

import logging
from datetime import date

import numpy as np
import pandas as pd

from ..errors import InsufficientHistoryError, PortfolioEmptyError
from ..models import (
    AssetMetrics,
    DashboardResponse,
    FrontierCloud,
    PortfolioMetrics,
    StressTestResult,
    Wealth,
)
from . import analytics, cma, diagnostic, market, stress

logger = logging.getLogger(__name__)


def build(
    cma_shrinkage: float | None = None,
    historical_period: str = "5y",
    risk_free: float | None = None,
    wealth: "Wealth | None" = None,
) -> DashboardResponse:
    if wealth is None:
        raise PortfolioEmptyError("Wealth required for dashboard.")
    positions = wealth.all_positions
    if not positions:
        raise PortfolioEmptyError(
            "Aucune position enregistrée. Ajoute des positions via PUT /portfolio."
        )

    # Aggregate by ticker across wrappers (PEA + CTO + ...)
    qty_by_ticker: dict[str, float] = {}
    avg_cost_by_ticker: dict[str, float] = {}
    cost_by_ticker: dict[str, float] = {}
    for p in positions:
        qty_by_ticker[p.ticker] = qty_by_ticker.get(p.ticker, 0.0) + p.quantity
        cost_by_ticker[p.ticker] = cost_by_ticker.get(p.ticker, 0.0) + p.cost_basis
    for t in qty_by_ticker:
        avg_cost_by_ticker[t] = cost_by_ticker[t] / qty_by_ticker[t] if qty_by_ticker[t] else 0.0

    tickers = list(qty_by_ticker.keys())
    prices = market.fetch_prices(tickers, period=historical_period)
    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}

    try:
        returns = analytics.daily_log_returns(prices[tickers])
    except ValueError as exc:
        raise InsufficientHistoryError(f"Calcul des rendements impossible: {exc}") from exc

    # Blend μ historiques avec CMAs forward-looking. Shrinkage overridable.
    rf = risk_free if risk_free is not None else analytics.RISK_FREE
    hist_mu = (returns.mean() * analytics.TRADING_DAYS).values
    blended = cma.blended_mu(tickers, hist_mu, shrinkage=cma_shrinkage)
    mu_override = {t: float(blended[i]) for i, t in enumerate(tickers)}

    asset_stats = analytics.annualized_stats(returns, risk_free=rf, mu_override=mu_override)

    values = np.array([qty_by_ticker[t] * latest[t] for t in tickers])
    total_value = float(values.sum())
    weights = values / total_value

    pf_stats = analytics.portfolio_stats(returns, weights, risk_free=rf, mu_override=mu_override)

    # Risque de queue : CVaR 95 % et max drawdown observé sur la fenêtre choisie.
    qty_per_ticker = pd.Series(qty_by_ticker)
    equity_curve = (prices[tickers] * qty_per_ticker).sum(axis=1)
    pf_returns = returns @ weights
    pf_cvar = analytics.cvar_95(pf_returns)
    pf_max_dd = analytics.max_drawdown(equity_curve)

    # Stress tests sur l'historique long (10y pour avoir 2020 et 2022).
    long_prices = market.fetch_prices(tickers, period="10y")
    stress_results_raw = stress.compute(long_prices, qty_per_ticker.to_dict())
    stress_results = [StressTestResult(**s) for s in stress_results_raw]

    total_cost = sum(cost_by_ticker.values())
    assets = [
        _asset_metric(
            t,
            qty_by_ticker[t],
            avg_cost_by_ticker[t],
            w,
            v,
            latest[t],
            asset_stats[t],
            analytics.cvar_95(returns[t]),
            analytics.max_drawdown(prices[t]),
        )
        for t, w, v in zip(tickers, weights.tolist(), values.tolist(), strict=True)
    ]

    metrics = PortfolioMetrics(
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_value - total_cost,
        total_pnl_pct=(total_value - total_cost) / total_cost if total_cost else 0.0,
        expected_return=pf_stats["expected_return"],
        volatility=pf_stats["volatility"],
        sharpe=pf_stats["sharpe"],
        drawdown_estimate=-2.0 * pf_stats["volatility"],
        cvar_95=pf_cvar,
        max_drawdown_observed=pf_max_dd,
        assets=assets,
        correlation=analytics.correlation_matrix(returns),
    )
    logger.info(
        "dashboard built: %d assets, %.2f €, shrinkage=%s, period=%s, %d stress tests",
        len(assets),
        total_value,
        cma_shrinkage,
        historical_period,
        len(stress_results),
    )
    return DashboardResponse(
        as_of=date.today(),
        metrics=metrics,
        frontier=FrontierCloud(**analytics.efficient_frontier_cloud(returns)),
        insights=diagnostic.generate(metrics),
        stress_tests=stress_results,
    )


def _asset_metric(
    ticker: str,
    quantity: float,
    avg_cost: float,
    weight: float,
    value: float,
    price: float,
    stat,
    cvar: float,
    max_dd: float,
) -> AssetMetrics:
    cost = quantity * avg_cost
    pnl = value - cost
    return AssetMetrics(
        ticker=ticker,
        price=price,
        weight=weight,
        value=value,
        pnl=pnl,
        pnl_pct=pnl / cost if cost else 0.0,
        annual_return=stat["mu"],
        annual_vol=stat["sigma"],
        sharpe=stat["sharpe"],
        drawdown_estimate=-2.0 * stat["sigma"],
        cvar_95=cvar,
        max_drawdown_observed=max_dd,
    )
