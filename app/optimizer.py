"""Portfolio optimizer service: solves for optimal weights and concrete actions.

Computes the SLSQP-optimal portfolio under a chosen objective, the per-asset
weight delta to reach it, the Euler risk decomposition for both current and
optimal allocations, and the smooth efficient frontier curve as visual aid.
"""
import numpy as np

from . import analytics, market, portfolio
from .models import (
    FrontierCurve,
    OptimizerResponse,
    PortfolioPoint,
    RebalanceAction,
    RiskContribution,
)

VALID_OBJECTIVES = ("max_sharpe", "min_variance")


def build(objective: str) -> OptimizerResponse:
    if objective not in VALID_OBJECTIVES:
        raise ValueError(f"Objectif inconnu: {objective!r}. Valeurs: {VALID_OBJECTIVES}.")

    pf = portfolio.load()
    if not pf.positions:
        raise ValueError("Aucune position enregistrée.")

    tickers = [p.ticker for p in pf.positions]
    prices = market.fetch_prices(tickers, period="5y")
    returns = analytics.daily_log_returns(prices[tickers])

    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}
    values = np.array([p.quantity * latest[p.ticker] for p in pf.positions])
    total_value = float(values.sum())
    current_w = values / total_value

    current_stats = analytics.portfolio_stats(returns, current_w)
    optimal = analytics.optimize_portfolio(returns, objective)
    optimal_w = np.array(optimal["weights"])

    actions = [
        RebalanceAction(
            ticker=tickers[i],
            current_weight=float(current_w[i]),
            optimal_weight=float(optimal_w[i]),
            delta_weight=float(optimal_w[i] - current_w[i]),
            delta_value=float((optimal_w[i] - current_w[i]) * total_value),
        )
        for i in range(len(tickers))
    ]

    return OptimizerResponse(
        objective=objective,
        tickers=tickers,
        current=PortfolioPoint(
            weights=current_w.tolist(),
            expected_return=current_stats["expected_return"],
            volatility=current_stats["volatility"],
            sharpe=current_stats["sharpe"],
        ),
        optimal=PortfolioPoint(
            weights=optimal_w.tolist(),
            expected_return=float(optimal["expected_return"]),
            volatility=float(optimal["volatility"]),
            sharpe=float(optimal["sharpe"]),
        ),
        actions=actions,
        risk_contributions_current=RiskContribution(**analytics.risk_contributions(returns, current_w)),
        risk_contributions_optimal=RiskContribution(**analytics.risk_contributions(returns, optimal_w)),
        frontier_curve=FrontierCurve(**analytics.efficient_frontier_curve(returns)),
    )