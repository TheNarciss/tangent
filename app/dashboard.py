"""Dashboard service: composes portfolio + market + analytics + diagnostic."""
import logging
from datetime import date

import numpy as np
import pandas as pd

from . import analytics, cma, diagnostic, market, portfolio, stress
from .errors import InsufficientHistoryError, PortfolioEmptyError
from .models import AssetMetrics, DashboardResponse, FrontierCloud, PortfolioMetrics, StressTestResult

logger = logging.getLogger(__name__)


def build(
    cma_shrinkage: float | None = None,
    historical_period: str = "5y",
    risk_free: float | None = None,
) -> DashboardResponse:
    pf = portfolio.load()
    if not pf.positions:
        raise PortfolioEmptyError("Aucune position enregistrée. Ajoute des positions via PUT /portfolio.")

    tickers = [p.ticker for p in pf.positions]
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

    values = np.array([p.quantity * latest[p.ticker] for p in pf.positions])
    total_value = float(values.sum())
    weights = values / total_value

    pf_stats = analytics.portfolio_stats(returns, weights, risk_free=rf, mu_override=mu_override)

    # Risque de queue : CVaR 95 % et max drawdown observé sur la fenêtre choisie.
    qty_per_ticker = pd.Series({p.ticker: p.quantity for p in pf.positions})
    equity_curve = (prices[tickers] * qty_per_ticker).sum(axis=1)
    pf_returns = returns @ weights
    pf_cvar = analytics.cvar_95(pf_returns)
    pf_max_dd = analytics.max_drawdown(equity_curve)

    # Stress tests sur l'historique long (10y pour avoir 2020 et 2022).
    long_prices = market.fetch_prices(tickers, period="10y")
    stress_results_raw = stress.compute(long_prices, qty_per_ticker.to_dict())
    stress_results = [StressTestResult(**s) for s in stress_results_raw]

    total_cost = sum(p.quantity * p.avg_cost for p in pf.positions)
    assets = [
        _asset_metric(p, w, v, latest[p.ticker], asset_stats[p.ticker],
                      analytics.cvar_95(returns[p.ticker]),
                      analytics.max_drawdown(prices[p.ticker]))
        for p, w, v in zip(pf.positions, weights.tolist(), values.tolist())
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
    logger.info("dashboard built: %d assets, %.2f €, shrinkage=%s, period=%s, %d stress tests",
                len(assets), total_value, cma_shrinkage, historical_period, len(stress_results))
    return DashboardResponse(
        as_of=date.today(),
        metrics=metrics,
        frontier=FrontierCloud(**analytics.efficient_frontier_cloud(returns)),
        insights=diagnostic.generate(metrics),
        stress_tests=stress_results,
    )


def _asset_metric(position, weight: float, value: float, price: float, stat,
                  cvar: float, max_dd: float) -> AssetMetrics:
    cost = position.quantity * position.avg_cost
    pnl = value - cost
    return AssetMetrics(
        ticker=position.ticker,
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