"""Dashboard service: composes portfolio + market + analytics + diagnostic."""
import logging
from datetime import date

import numpy as np

from . import analytics, diagnostic, market, portfolio
from .errors import InsufficientHistoryError, PortfolioEmptyError
from .models import AssetMetrics, DashboardResponse, FrontierCloud, PortfolioMetrics

logger = logging.getLogger(__name__)


def build() -> DashboardResponse:
    pf = portfolio.load()
    if not pf.positions:
        raise PortfolioEmptyError("Aucune position enregistrée. Ajoute des positions via PUT /portfolio.")

    tickers = [p.ticker for p in pf.positions]
    prices = market.fetch_prices(tickers, period="5y")
    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}

    try:
        returns = analytics.daily_log_returns(prices[tickers])
    except ValueError as exc:
        raise InsufficientHistoryError(f"Calcul des rendements impossible: {exc}") from exc

    asset_stats = analytics.annualized_stats(returns)

    values = np.array([p.quantity * latest[p.ticker] for p in pf.positions])
    total_value = float(values.sum())
    weights = values / total_value

    pf_stats = analytics.portfolio_stats(returns, weights)

    total_cost = sum(p.quantity * p.avg_cost for p in pf.positions)
    assets = [_asset_metric(p, w, v, latest[p.ticker], asset_stats[p.ticker])
              for p, w, v in zip(pf.positions, weights.tolist(), values.tolist())]

    metrics = PortfolioMetrics(
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_value - total_cost,
        total_pnl_pct=(total_value - total_cost) / total_cost if total_cost else 0.0,
        expected_return=pf_stats["expected_return"],
        volatility=pf_stats["volatility"],
        sharpe=pf_stats["sharpe"],
        assets=assets,
        correlation=analytics.correlation_matrix(returns),
    )
    logger.info("dashboard built: %d assets, total %.2f €", len(assets), total_value)
    return DashboardResponse(
        as_of=date.today(),
        metrics=metrics,
        frontier=FrontierCloud(**analytics.efficient_frontier_cloud(returns)),
        insights=diagnostic.generate(metrics),
    )


def _asset_metric(position, weight: float, value: float, price: float, stat) -> AssetMetrics:
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
    )