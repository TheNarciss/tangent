"""Dashboard service: composes portfolio + market + analytics + diagnostic."""

import logging
from datetime import date

import numpy as np

from ..errors import InsufficientHistoryError, PortfolioEmptyError
from ..models import (
    AssetMetrics,
    DashboardResponse,
    PortfolioMetrics,
    StressTestResult,
    Wealth,
)
from . import analytics, cma, diagnostic, market, stress

logger = logging.getLogger(__name__)

# Stress tests need a 10y history (2020 + 2022): fetched once a day per
# portfolio composition, not on every /dashboard call.
_StressKey = tuple[tuple[str, float], ...]
_STRESS_CACHE: dict[_StressKey, tuple[date, list[StressTestResult]]] = {}


def _stress_tests(qty_by_ticker: dict[str, float]) -> list[StressTestResult]:
    key: _StressKey = tuple(sorted((t, round(q, 6)) for t, q in qty_by_ticker.items()))
    today = date.today()
    cached = _STRESS_CACHE.get(key)
    if cached is not None and cached[0] == today:
        return cached[1]

    long_prices = market.fetch_prices(list(qty_by_ticker), period="10y")
    results = [StressTestResult(**s) for s in stress.compute(long_prices, qty_by_ticker)]

    # Drop yesterday's entries so the cache stays bounded by live compositions.
    for stale in [k for k, (day, _) in _STRESS_CACHE.items() if day != today]:
        _STRESS_CACHE.pop(stale, None)
    _STRESS_CACHE[key] = (today, results)
    return results


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
    label_by_ticker: dict[str, str] = {}
    for p in positions:
        qty_by_ticker[p.ticker] = qty_by_ticker.get(p.ticker, 0.0) + p.quantity
        cost_by_ticker[p.ticker] = cost_by_ticker.get(p.ticker, 0.0) + p.cost_basis
        if p.label and p.label != p.ticker:
            label_by_ticker.setdefault(p.ticker, p.label)
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
    hist_mu = analytics.annualized_arithmetic_mu(returns).values
    blended = cma.blended_mu(tickers, hist_mu, shrinkage=cma_shrinkage)
    unmapped = cma.unmapped_tickers(tickers)
    mu_override = {t: float(blended[i]) for i, t in enumerate(tickers)}

    asset_stats = analytics.annualized_stats(returns, risk_free=rf, mu_override=mu_override)

    values = np.array([qty_by_ticker[t] * latest[t] for t in tickers])
    total_value = float(values.sum())
    weights = values / total_value

    pf_stats = analytics.portfolio_stats(returns, weights, risk_free=rf, mu_override=mu_override)

    # Risque de queue : CVaR 95 % et max drawdown observé sur la fenêtre choisie.
    # NaN propagates: a date where one line has no price is not a portfolio value.
    equity_curve = analytics.portfolio_value_series(prices, qty_by_ticker)
    pf_returns = returns @ weights
    pf_cvar = analytics.cvar_95(pf_returns)
    pf_max_dd = analytics.max_drawdown(equity_curve)

    stress_results = _stress_tests(qty_by_ticker)

    total_cost = sum(cost_by_ticker.values())
    assets = [
        _asset_metric(
            t,
            label_by_ticker.get(t),
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
        unmapped_tickers=unmapped,
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
        insights=diagnostic.generate(metrics),
        stress_tests=stress_results,
    )


def _asset_metric(
    ticker: str,
    label: str | None,
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
        label=label,
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
