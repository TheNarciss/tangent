"""Dashboard service: composes portfolio + market + analytics + stress tests.

It describes what the user holds and what it is worth. What to *do* about it
is the verdicts' job, and theirs alone (ADR-028)."""

import logging
from datetime import date

import numpy as np

from ..data import ken_french
from ..errors import DataSourceError, InsufficientHistoryError, PortfolioEmptyError
from ..models import (
    AssetMetrics,
    DashboardResponse,
    PortfolioMetrics,
    Wealth,
)
from . import analytics, classification, cma, macro, market, stress

logger = logging.getLogger(__name__)

# Stress tests need a 10y history (2020 + 2022): fetched once a day per
# portfolio composition, not on every /dashboard call.


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
    isin_by_ticker: dict[str, str] = {}
    for p in positions:
        qty_by_ticker[p.ticker] = qty_by_ticker.get(p.ticker, 0.0) + p.quantity
        cost_by_ticker[p.ticker] = cost_by_ticker.get(p.ticker, 0.0) + p.cost_basis
        if p.label and p.label != p.ticker:
            label_by_ticker.setdefault(p.ticker, p.label)
        isin = getattr(p, "isin", None)
        if isin:
            isin_by_ticker.setdefault(p.ticker, isin)
    for t in qty_by_ticker:
        avg_cost_by_ticker[t] = cost_by_ticker[t] / qty_by_ticker[t] if qty_by_ticker[t] else 0.0

    tickers = list(qty_by_ticker.keys())
    prices = market.fetch_prices(tickers, period=historical_period)
    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}

    try:
        returns = analytics.daily_log_returns(prices[tickers])
    except ValueError as exc:
        raise InsufficientHistoryError(f"Calcul des rendements impossible: {exc}") from exc

    # What each line is (fund or share, which index): drives the CMA, the
    # verdicts and what the Positions table shows.
    classes = dict(
        zip(
            tickers,
            classification.classify_many(
                [(label_by_ticker.get(t, t), isin_by_ticker.get(t)) for t in tickers]
            ),
            strict=True,
        )
    )

    # Blend μ historiques avec CMAs forward-looking. Shrinkage overridable.
    rf = risk_free if risk_free is not None else macro.risk_free_rate()
    hist_mu = analytics.annualized_arithmetic_mu(returns).values
    class_of = [classes[t].asset_class for t in tickers]
    blended = cma.blended_mu(tickers, class_of, hist_mu, shrinkage=cma_shrinkage)
    unmapped = cma.unmapped_tickers(tickers, class_of)
    mu_override = {t: float(blended[i]) for i, t in enumerate(tickers)}

    asset_stats = analytics.annualized_stats(returns, risk_free=rf, mu_override=mu_override)

    values = np.array([qty_by_ticker[t] * latest[t] for t in tickers])
    total_value = float(values.sum())
    weights = values / total_value

    pf_stats = analytics.portfolio_stats(returns, weights, risk_free=rf, mu_override=mu_override)

    # Risque de queue : max drawdown observé sur la fenêtre choisie.
    # NaN propagates: a date where one line has no price is not a portfolio value.
    equity_curve = analytics.portfolio_value_series(prices, qty_by_ticker)
    pf_max_dd = analytics.max_drawdown(equity_curve)

    stress_results = stress.compute(wealth)

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
            analytics.max_drawdown(prices[t]),
            classes[t],
        )
        for t, w, v in zip(tickers, weights.tolist(), values.tolist(), strict=True)
    ]

    worst_year, worst_year_label = _worst_year_of_dominant_class(classes, weights, tickers)

    metrics = PortfolioMetrics(
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_value - total_cost,
        total_pnl_pct=(total_value - total_cost) / total_cost if total_cost else 0.0,
        expected_return=pf_stats["expected_return"],
        volatility=pf_stats["volatility"],
        sharpe=pf_stats["sharpe"],
        drawdown_estimate=-2.0 * pf_stats["volatility"],
        max_drawdown_observed=pf_max_dd,
        history_days=len(equity_curve.dropna()),
        worst_year_class=worst_year,
        worst_year_label=worst_year_label,
        replayed_as_world=_replayed_as_world(classes, tickers),
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
    max_dd: float,
    what: classification.Classification,
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
        max_drawdown_observed=max_dd,
        asset_class=what.asset_class,
        index_label=what.index_label,
        kind=what.kind,
        is_diversified=what.is_diversified,
    )


def _replayed_as_world(
    classes: dict[str, classification.Classification],
    tickers: list[str],
) -> list[str]:
    """Lines whose class is replayed as world equities though it is not one.

    A Nasdaq or a defence tracker falls harder than the world index; the study
    has no series per region and per episode, so the stress tests understate
    them. The screen says which lines, rather than letting the total look
    complete.
    """
    scenarios = stress.config()
    seen: list[str] = []
    for ticker in tickers:
        what = classes[ticker]
        replayed = scenarios.class_map.get(what.asset_class, scenarios.default_asset_class)
        if replayed == "equity_world" and what.asset_class != "equity_world":
            label = what.index_label or "classe non reconnue"
            if label not in seen:
                seen.append(label)
    return seen


def _worst_year_of_dominant_class(
    classes: dict[str, classification.Classification],
    weights,
    tickers: list[str],
) -> tuple[float | None, str | None]:
    """Worst twelve months ever observed for the portfolio's dominant asset class.

    (None, None) when the class has no long history or the source is
    unreachable: the screen then says what it could measure, and no more.
    """
    by_class: dict[str, float] = {}
    for ticker, weight in zip(tickers, weights.tolist(), strict=True):
        asset_class = classes[ticker].asset_class
        by_class[asset_class] = by_class.get(asset_class, 0.0) + weight
    if not by_class:
        return None, None

    dominant = max(by_class, key=lambda c: by_class[c])
    region = classification.history_region(dominant)
    if not region:
        return None, None

    try:
        worst = analytics.worst_rolling_year(ken_french.monthly_returns(region))
    except (DataSourceError, ValueError):
        logger.warning("pas d'historique long pour %s", region)
        return None, None

    return worst, classes_label(classes, dominant)


def classes_label(classes: dict[str, classification.Classification], asset_class: str) -> str:
    """Human label of a class, e.g. 'Actions monde'. Falls back to the raw key."""
    for what in classes.values():
        if what.asset_class == asset_class and what.index_label:
            return what.index_label
    return asset_class
