"""DCA projection service: deterministic 3-scenario + Monte-Carlo fan chart.

Uses the portfolio's actual historical daily returns as a basis. Stats and
projection geometry are pure; this module wires portfolio → market → analytics.
"""
import numpy as np

from . import analytics, market, portfolio
from .models import ProjectionBands, ProjectionResponse


def build(monthly_contribution: float, years: int, goal: float | None) -> ProjectionResponse:
    pf = portfolio.load()
    if not pf.positions:
        raise ValueError("Aucune position enregistrée.")

    tickers = [p.ticker for p in pf.positions]
    prices = market.fetch_prices(tickers, period="5y")
    quantities = {p.ticker: p.quantity for p in pf.positions}

    value_series = analytics.portfolio_value_series(prices, quantities)
    initial = float(value_series.iloc[-1])

    # Daily portfolio log returns drive Monte-Carlo geometry
    log_rets = np.log(value_series / value_series.shift(1)).dropna()
    mu_annual = float(log_rets.mean() * analytics.TRADING_DAYS)
    sigma_annual = float(log_rets.std() * np.sqrt(analytics.TRADING_DAYS))
    # Convert log to simple return for the deterministic compounding model
    mu_simple = float(np.exp(mu_annual) - 1)

    months = years * 12

    det = analytics.deterministic_projection(initial, monthly_contribution, mu_simple, sigma_annual, months)
    mc = analytics.monte_carlo_projection(log_rets, initial, monthly_contribution, months)

    paths = mc.pop("_paths")  # ndarray (n_paths, months+1)
    goal_prob_by_month: list[float] | None = None
    goal_prob_at_end: float | None = None
    if goal is not None and goal > 0:
        goal_prob_by_month = analytics.goal_probability(paths, goal)
        goal_prob_at_end = goal_prob_by_month[-1]

    return ProjectionResponse(
        months=list(range(months + 1)),
        invested=[initial + monthly_contribution * t for t in range(months + 1)],
        bands=ProjectionBands(bear=det["bear"], base=det["base"], bull=det["bull"], **mc),
        annual_return=mu_simple,
        annual_vol=sigma_annual,
        goal=goal,
        goal_prob_at_end=goal_prob_at_end,
        goal_prob_by_month=goal_prob_by_month,
    )