"""Portfolio optimizer service.

Supports three objectives (max_sharpe, min_variance, target_volatility) and
optionally augments the asset universe with the user's eligible regulated
envelopes (Livret A, LEP, etc.) modeled as synthetic 0-σ assets with
ceiling-derived weight bounds.
"""
import logging

import numpy as np

from . import analytics, cma, envelopes, market, portfolio
from .errors import ConfigurationError, InfeasibleStrategyError, PortfolioEmptyError
from .models import (
    CeilingsUsed,
    EnvelopePoint,
    FrontierCurve,
    KellyLeverage,
    OptimizerRequest,
    OptimizerResponse,
    PortfolioPoint,
    RebalanceAction,
    RiskContribution,
)

logger = logging.getLogger(__name__)


def build(req: OptimizerRequest) -> OptimizerResponse:
    pf = portfolio.load()
    if not pf.positions:
        raise PortfolioEmptyError("Aucune position enregistrée.")

    # Expert settings : tous optionnels avec défauts intelligents
    expert = req.expert
    period = expert.historical_period if expert and expert.historical_period else "5y"
    rf = expert.risk_free_rate if expert and expert.risk_free_rate is not None else analytics.RISK_FREE
    cma_shrink = expert.cma_shrinkage if expert and expert.cma_shrinkage is not None else None
    cma_overrides = expert.cma_overrides if expert else {}
    cov_estimator = expert.cov_estimator if expert else "sample"
    cov_shrinkage = expert.cov_shrinkage if expert else 0.20

    tickers = [p.ticker for p in pf.positions]
    prices = market.fetch_prices(tickers, period=period)
    returns = analytics.daily_log_returns(prices[tickers])

    latest = {t: float(prices[t].dropna().iloc[-1]) for t in tickers}
    etf_values = np.array([p.quantity * latest[p.ticker] for p in pf.positions])
    portfolio_value = float(etf_values.sum())

    # Capital pool over which weights/euros are resolved
    total_capital = req.total_capital if req.total_capital and req.total_capital > 0 else portfolio_value

    # Resolve envelopes (only if all profile fields provided)
    envelope_assets = _resolve_envelopes(req, total_capital) if req.include_envelopes else []

    asset_ids = tickers + [e["id"] for e in envelope_assets]
    asset_kinds = ["etf"] * len(tickers) + ["envelope"] * len(envelope_assets)
    asset_labels = tickers + [e["name"] for e in envelope_assets]

    # Build augmented stats and solve
    envelope_rates = [e["rate"] for e in envelope_assets]
    envelope_max_weights = [e["max_weight"] for e in envelope_assets]

    # Blend μ historiques avec CMAs forward-looking (avec overrides expert si fournis).
    hist_mu = (returns.mean() * analytics.TRADING_DAYS).values
    blended = cma.blended_mu(tickers, hist_mu, shrinkage=cma_shrink, overrides=cma_overrides or None)
    mu_override = {t: float(blended[i]) for i, t in enumerate(tickers)}

    mu, cov, bounds = analytics.build_asset_stats(
        returns, envelope_rates, envelope_max_weights,
        mu_override=mu_override,
        cov_estimator=cov_estimator,
        cov_shrinkage=cov_shrinkage,
    )

    if req.objective == "target_volatility" and (req.max_volatility is None):
        raise ConfigurationError("L'objectif 'target_volatility' requiert max_volatility.")
    if req.objective == "from_strategy" and (req.max_volatility is None or req.target_return is None):
        raise ConfigurationError("L'objectif 'from_strategy' requiert max_volatility ET target_return.")

    optimal = analytics._solve_slsqp(
        mu, cov, bounds,
        req.objective,
        rf,
        req.max_volatility,
        req.target_return,
    )

    # Feasibility check for from_strategy: if SLSQP failed, compute the achievable
    # benchmark (max μ at σ_max) to tell the user exactly what's blocking.
    if req.objective == "from_strategy" and not optimal.get("success", True):
        try:
            best_at_vol = analytics._solve_slsqp(
                mu, cov, bounds, "target_volatility", rf,
                req.max_volatility, None,
            )
            achievable = float(best_at_vol["expected_return"])
            raise InfeasibleStrategyError(
                f"Stratégie infaisable : avec σ ≤ {req.max_volatility * 100:.1f}%, le meilleur rendement "
                f"atteignable est {achievable * 100:.2f}% /an. Tu vises {req.target_return * 100:.2f}%. "
                f"Solutions : relâche la vol max, baisse l'objectif de rendement, ou ajoute des actifs plus "
                f"rentables (active les livrets si pas déjà fait)."
            )
        except InfeasibleStrategyError:
            raise
        except Exception:
            raise InfeasibleStrategyError(
                f"Stratégie infaisable : σ ≤ {req.max_volatility * 100:.1f}% et μ ≥ {req.target_return * 100:.2f}% "
                f"ne peuvent pas être satisfaits simultanément avec tes actifs actuels."
            )

    optimal_w = np.array(optimal["weights"])

    # Current weights: ETFs at their current proportion of total_capital; envelopes at 0
    current_w = np.concatenate([etf_values / total_capital, np.zeros(len(envelope_assets))])
    current_stats_etf = analytics.portfolio_stats(returns, etf_values / portfolio_value, risk_free=rf, mu_override=mu_override)

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

    # Frontier curve : ETF-only, mais avec les μ BLENDÉS (CMA + historique) — sinon
    # la courbe utilise μ historique brut et peut sortir des valeurs incohérentes
    # avec les assets affichés (genre 30% alors que max asset μ est 16%).
    n_etf = len(tickers)
    mu_etf = mu[:n_etf]
    cov_etf = cov[:n_etf, :n_etf]
    frontier = analytics.efficient_frontier_curve(returns, mu=mu_etf, cov=cov_etf)

    # Kelly leverage indicator (sur les ETFs uniquement — exclut les livrets car σ≈0 explose la formule)
    n_etf = len(tickers)
    kelly = analytics.kelly_leverage(mu[:n_etf], cov[:n_etf, :n_etf], risk_free=rf)
    half_l = kelly["half_kelly_leverage"]
    if half_l > 1.05:
        kelly_msg = (
            f"Half-Kelly recommande un levier de {half_l:.2f}× — tes actifs risqués sont très attractifs. "
            f"Sans accès au levier, investir 100 % sans réserve cash est cohérent."
        )
    elif half_l < 0.95:
        kelly_msg = (
            f"Half-Kelly recommande {half_l * 100:.0f} % du capital en risqué — "
            f"le rapport rendement/risque ne justifie pas un investissement plein. Garde {(1 - half_l) * 100:.0f} % en cash/livret."
        )
    else:
        kelly_msg = (
            f"Half-Kelly recommande {half_l * 100:.0f} % — parfait pour un investissement plein sans levier."
        )
    kelly_indicator = KellyLeverage(
        full_kelly_leverage=kelly["full_kelly_leverage"],
        half_kelly_leverage=half_l,
        interpretation=kelly_msg,
    )

    logger.info(
        "optimizer: objective=%s, %d etf + %d envelope, total_capital=%.0f €, optimal σ=%.2f%% μ=%.2f%%",
        req.objective, len(tickers), len(envelope_assets), total_capital,
        optimal["volatility"] * 100, optimal["expected_return"] * 100,
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
        frontier_curve=FrontierCurve(**frontier),
        envelope_points=[
            EnvelopePoint(label=e["name"], expected_return=e["rate"], volatility=0.0)
            for e in envelope_assets
        ],
        kelly_leverage=kelly_indicator,
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
        out.append({
            "id": eid,
            "name": env.name,
            "rate": env.rate_pct,
            "available_eur": available,
            "max_weight": min(1.0, available / total_capital) if total_capital > 0 else 0.0,
        })
    return out