"""Portfolio optimizer service.

Supports three objectives (min_variance, target_volatility, from_strategy) and
optionally augments the asset universe with the user's eligible regulated
envelopes (Livret A, LEP, etc.) modeled as synthetic 0-σ assets with
ceiling-derived weight bounds.
"""

import logging
from typing import TypedDict, cast

import numpy as np

from ..errors import ConfigurationError, InfeasibleStrategyError, PortfolioEmptyError, SolverError
from ..models import (
    CeilingsUsed,
    EnvelopePoint,
    FrontierCurve,
    OptimizerRequest,
    OptimizerResponse,
    PortfolioPoint,
    RebalanceAction,
    RiskContribution,
    Wealth,
)
from . import analytics, classification, cma, envelopes, macro, market

logger = logging.getLogger(__name__)


class _SLSQPResult(TypedDict):
    """Contract of analytics._solve_slsqp() return value."""

    weights: list[float]
    expected_return: float
    volatility: float
    sharpe: float
    success: bool


_FRONTIER_REASON_MESSAGES: dict[str, str] = {
    "need_two_assets": (
        "Frontière non traçable : il faut au moins 2 actifs distincts. "
        "Active les livrets ou ajoute une seconde position."
    ),
    "flat_returns": (
        "Tous tes actifs ont le même rendement espéré — "
        "aucune diversification n'apporte de gain attendu, donc pas de frontière à tracer."
    ),
    "solver_failed": (
        "Le solveur n'a pas convergé. "
        "Essaie une période historique plus longue dans les Paramètres expert."
    ),
}


def _frontier_reason_message(code: str | None) -> str | None:
    if not code:
        return None
    return _FRONTIER_REASON_MESSAGES.get(code, "Frontière indisponible.")


def build(req: OptimizerRequest, wealth: "Wealth | None" = None) -> OptimizerResponse:
    if wealth is None:
        raise PortfolioEmptyError("Wealth required for optimizer.")
    positions = wealth.all_positions
    if not positions:
        raise PortfolioEmptyError("No position recorded.")

    # Aggregate quantities by ticker (same ticker may appear in PEA + CTO)
    qty_by_ticker: dict[str, float] = {}
    label_by_ticker: dict[str, str] = {}
    isin_by_ticker: dict[str, str] = {}
    for p in positions:
        qty_by_ticker[p.ticker] = qty_by_ticker.get(p.ticker, 0.0) + p.quantity
        if p.label and p.label != p.ticker:
            label_by_ticker.setdefault(p.ticker, p.label)
        if p.isin:
            isin_by_ticker.setdefault(p.ticker, p.isin)

    # Expert settings: all optional with smart defaults
    expert = req.expert
    period = expert.historical_period if expert and expert.historical_period else "5y"
    rf = (
        expert.risk_free_rate
        if expert and expert.risk_free_rate is not None
        else macro.risk_free_rate()
    )
    cma_shrink = expert.cma_shrinkage if expert and expert.cma_shrinkage is not None else None
    cma_overrides = expert.cma_overrides if expert else {}
    cov_estimator = expert.cov_estimator if expert else "sample"
    cov_shrinkage = expert.cov_shrinkage if expert else 0.20

    tickers = list(qty_by_ticker.keys())
    prices = market.fetch_prices(tickers, period=period)
    returns = analytics.daily_log_returns(prices[tickers])

    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}
    etf_values = np.array([qty_by_ticker[t] * latest[t] for t in tickers])
    portfolio_value = float(etf_values.sum())

    # Capital pool over which weights/euros are resolved
    total_capital = (
        req.total_capital if req.total_capital and req.total_capital > 0 else portfolio_value
    )

    # Resolve envelopes (only if all profile fields provided)
    envelope_assets = _resolve_envelopes(req, total_capital) if req.include_envelopes else []

    asset_ids = tickers + [e["id"] for e in envelope_assets]
    asset_kinds = ["etf"] * len(tickers) + ["envelope"] * len(envelope_assets)
    # The fund's name, not its ticker: the same line was called « AM.PEA MSCI
    # WORLD » in one block and « DCAM.PA » in the next.
    asset_labels = [label_by_ticker.get(t, t) for t in tickers] + [
        e["name"] for e in envelope_assets
    ]

    # Build augmented stats and solve
    envelope_rates = [e["rate"] for e in envelope_assets]
    envelope_max_weights = [e["max_weight"] for e in envelope_assets]

    # Blend historical μ with forward-looking CMAs (with expert overrides if provided).
    hist_mu = analytics.annualized_arithmetic_mu(returns).values
    class_of = [
        c.asset_class
        for c in classification.classify_many(
            [(label_by_ticker.get(t, t), isin_by_ticker.get(t)) for t in tickers]
        )
    ]
    blended = cma.blended_mu(
        tickers, class_of, hist_mu, shrinkage=cma_shrink, overrides=cma_overrides or None
    )
    mu_override = {t: float(blended[i]) for i, t in enumerate(tickers)}
    unmapped = cma.unmapped_tickers(tickers, class_of, cma_overrides or None)

    mu, cov, bounds = analytics.build_asset_stats(
        returns,
        envelope_rates,
        envelope_max_weights,
        mu_override=mu_override,
        cov_estimator=cov_estimator,
        cov_shrinkage=cov_shrinkage,
    )

    if req.objective == "target_volatility" and (req.max_volatility is None):
        raise ConfigurationError("Objective 'target_volatility' requires max_volatility.")
    if req.objective == "from_strategy" and (
        req.max_volatility is None or req.target_return is None
    ):
        raise ConfigurationError(
            "Objective 'from_strategy' requires max_volatility AND target_return."
        )

    optimal: _SLSQPResult = cast(
        _SLSQPResult,
        analytics._solve_slsqp(
            mu,
            cov,
            bounds,
            req.objective,
            rf,
            req.max_volatility,
            req.target_return,
        ),
    )

    # Feasibility check for from_strategy: if SLSQP failed, compute the achievable
    # benchmark (max μ at σ_max) to tell the user exactly what's blocking.
    if req.objective == "from_strategy" and not optimal.get("success", True):
        # Guarded by ConfigurationError raised above for from_strategy.
        assert req.max_volatility is not None
        assert req.target_return is not None
        try:
            best_at_vol = cast(
                _SLSQPResult,
                analytics._solve_slsqp(
                    mu,
                    cov,
                    bounds,
                    "target_volatility",
                    rf,
                    req.max_volatility,
                    None,
                ),
            )
            achievable = best_at_vol["expected_return"]
            raise InfeasibleStrategyError(
                f"Infeasible strategy: with σ ≤ {req.max_volatility * 100:.1f}%, the best achievable "
                f"return is {achievable * 100:.2f}%/year. You target {req.target_return * 100:.2f}%. "
                f"Options: relax the vol cap, lower the target return, or add higher-return assets "
                f"(enable savings envelopes if not already)."
            )
        except InfeasibleStrategyError:
            raise
        except Exception as err:
            raise InfeasibleStrategyError(
                f"Infeasible strategy: σ ≤ {req.max_volatility * 100:.1f}% and μ ≥ {req.target_return * 100:.2f}% "
                f"cannot be satisfied simultaneously with your current assets."
            ) from err

    if not optimal.get("success", True):
        raise SolverError(
            "Le solveur n'a pas convergé : aucune allocation fiable à proposer avec ces lignes. "
            "Essaie une période historique plus longue dans les Paramètres expert."
        )

    optimal_w = np.array(optimal["weights"])

    # Current weights: ETFs at their current proportion of total_capital; envelopes at 0
    current_w = np.concatenate([etf_values / total_capital, np.zeros(len(envelope_assets))])
    current_stats_etf = analytics.portfolio_stats(
        returns, etf_values / portfolio_value, risk_free=rf, mu_override=mu_override
    )

    # Actions
    actions = [
        RebalanceAction(
            ticker=asset_ids[i],
            current_weight=float(current_w[i]),
            optimal_weight=float(optimal_w[i]),
            delta_weight=float(optimal_w[i] - current_w[i]),
            delta_value=float((optimal_w[i] - current_w[i]) * total_capital),
        )
        for i in range(len(asset_ids))
    ]

    # Risk contributions in the augmented space
    rc_optimal = analytics.euler_risk_contributions(optimal_w, cov)
    rc_current = analytics.euler_risk_contributions(current_w, cov)

    # Frontier curve: ETF-only, but with BLENDED μ (CMA + historical) — otherwise
    # the curve uses raw historical μ and may yield values inconsistent with the
    # displayed assets (e.g. 30% when the max asset μ is 16%).
    # Frontier curve: matches the optimization universe.
    # - Without envelopes: ETF-only frontier (classic Markowitz curve)
    # - With envelopes: augmented frontier (ETF + 0-σ assets), gives the CAL kink
    if envelope_assets:
        frontier = analytics.efficient_frontier_curve(
            returns,
            mu=mu,
            cov=cov,
            bounds_override=bounds,
        )
    else:
        n_etf = len(tickers)
        mu_etf = mu[:n_etf]
        cov_etf = cov[:n_etf, :n_etf]
        frontier = analytics.efficient_frontier_curve(returns, mu=mu_etf, cov=cov_etf)

    logger.info(
        "optimizer: objective=%s, %d etf + %d envelope, total_capital=%.0f €, optimal σ=%.2f%% μ=%.2f%%",
        req.objective,
        len(tickers),
        len(envelope_assets),
        total_capital,
        optimal["volatility"] * 100,
        optimal["expected_return"] * 100,
    )

    return OptimizerResponse(
        objective=req.objective,
        asset_ids=asset_ids,
        asset_kinds=asset_kinds,
        asset_labels=asset_labels,
        total_capital=total_capital,
        current=PortfolioPoint(
            weights=current_w.tolist(),
            expected_return=current_stats_etf["expected_return"],
            volatility=current_stats_etf["volatility"],
            sharpe=current_stats_etf["sharpe"],
        ),
        optimal=PortfolioPoint(
            weights=optimal["weights"],
            expected_return=float(optimal["expected_return"]),
            volatility=float(optimal["volatility"]),
            sharpe=float(optimal["sharpe"]),
        ),
        actions=actions,
        risk_contributions_current=RiskContribution(tickers=asset_ids, fraction=rc_current),
        risk_contributions_optimal=RiskContribution(tickers=asset_ids, fraction=rc_optimal),
        frontier_curve=FrontierCurve(
            vol=frontier["vol"],
            ret=frontier["ret"],
            sharpe=frontier["sharpe"],
            unavailable_reason=_frontier_reason_message(frontier["reason"]),
        ),
        envelope_points=[
            EnvelopePoint(label=e["name"], expected_return=e["rate"], volatility=0.0)
            for e in envelope_assets
        ],
        unmapped_tickers=unmapped,
    )


def _resolve_envelopes(req: OptimizerRequest, total_capital: float) -> list[dict]:
    """Filter eligible envelopes for this profile and compute per-envelope max_weight."""
    if not (req.age is not None and req.rfr is not None and req.fiscal_shares is not None):
        return []
    used = req.ceilings_used or CeilingsUsed()
    used_dict = used.model_dump()
    cfg = envelopes.config()
    out: list[dict] = []
    for eid, env in cfg.envelopes.items():
        eligible, _ = envelopes.check_eligibility(env, req.age, req.rfr, req.fiscal_shares)
        if not eligible:
            continue
        # No ceiling = capped at total_capital (use 100% bound)
        if env.ceiling_eur is None:
            available = total_capital
        else:
            available = max(0.0, env.ceiling_eur - used_dict.get(eid, 0))
        if available <= 0:
            continue
        out.append(
            {
                "id": eid,
                "name": env.name,
                "rate": env.rate_pct,
                "available_eur": available,
                "max_weight": min(1.0, available / total_capital) if total_capital > 0 else 0.0,
            }
        )
    return out
