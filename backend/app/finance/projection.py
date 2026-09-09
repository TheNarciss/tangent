"""DCA projection service: deterministic 3-scenario + Monte-Carlo fan chart.

Applies broker fees (per `config/brokers.yaml`) at each simulated month so they
compound correctly. Also computes a fees-free baseline (`gross_p50`) and the
cumulative fee impact at each month for direct visualization.

Phase 2 PR 4: consumes Wealth domain model. Scope unchanged — projection is
on the investable titres only. A future PR may incorporate loan repayments
and livret accrual into the projection to surface real net-worth trajectory.
"""

import logging

import numpy as np

from ..errors import PortfolioEmptyError
from ..models import ProjectionBands, ProjectionResponse, Wealth
from . import analytics, fees, macro, market, verdicts

logger = logging.getLogger(__name__)


def build(
    monthly_contribution: float,
    years: int,
    goal: float | None,
    broker_id: str | None = None,
    wealth: Wealth | None = None,
    weighted_ter: float = 0.0,  # informational, see below
) -> ProjectionResponse:
    if wealth is None:
        raise PortfolioEmptyError("Wealth required for projection.")
    positions = wealth.all_positions
    if not positions:
        raise PortfolioEmptyError("Aucune position enregistrée.")

    # Aggregate quantities by ticker (same ticker may appear in PEA + CTO)
    quantities: dict[str, float] = {}
    for p in positions:
        quantities[p.ticker] = quantities.get(p.ticker, 0.0) + p.quantity
    tickers = list(quantities.keys())

    prices = market.fetch_prices(tickers, period="5y")

    value_series = analytics.portfolio_value_series(prices, quantities)
    initial = float(value_series.iloc[-1])

    log_rets = np.log(value_series / value_series.shift(1)).dropna()
    mu_annual = float(log_rets.mean() * analytics.TRADING_DAYS)
    sigma_annual = float(log_rets.std() * np.sqrt(analytics.TRADING_DAYS))
    mu_simple = float(np.exp(mu_annual) - 1)
    months = years * 12

    # Resolve broker and build a value→monthly_fee closure
    bid, broker_fees = fees.get(broker_id)
    broker_fee_fn = fees.monthly_fee_fn(
        broker_fees,
        n_lines=len(quantities),
        monthly_contribution=monthly_contribution,
    )
    # Prices are net of fund fees (the NAV is struck after the TER), so the TER
    # is not simulated again here; `weighted_ter` is echoed for display only
    # and costed by the « frais réels » verdict (ADR-023).
    fee_fn = broker_fee_fn

    cfg = verdicts.config()
    inflation = macro.inflation()
    # Today's euros: a nominal amount t months out is worth that much less now.
    deflator = np.array([(1.0 + inflation) ** (t / 12.0) for t in range(months + 1)])

    # Net projection (with fees compounding) — primary curves
    mc = analytics.monte_carlo_projection(
        log_rets, initial, monthly_contribution, months, monthly_fee=fee_fn
    )
    paths = np.asarray(mc.pop("_paths"))

    # Gross projection (no fees) — only the P50 is exposed, for the comparison overlay
    mc_gross = analytics.monte_carlo_projection(
        log_rets, initial, monthly_contribution, months, monthly_fee=None
    )
    gross_p50 = mc_gross["p50"]

    # Cumulative fee impact at each month = gap between fees-free and net P50
    cumulative_fees = [max(0.0, g - n) for g, n in zip(gross_p50, mc["p50"], strict=True)]

    # Everything the user reads is in today's euros, goal included.
    real_paths = paths / deflator
    goal_prob_by_month: list[float] | None = None
    goal_prob_at_end: float | None = None
    required_monthly: float | None = None
    if goal is not None and goal > 0:
        goal_prob_by_month = analytics.goal_probability(real_paths, goal)
        goal_prob_at_end = goal_prob_by_month[-1]
        required_monthly = analytics.required_monthly_contribution(
            log_rets,
            initial,
            months,
            goal=goal * float(deflator[-1]),  # the solver works in nominal euros
            probability=cfg.projection.target_probability,
            fixed_monthly=broker_fees.fixed_per_line_eur * len(quantities) / 12.0,
            proportional_monthly=broker_fees.custody_pct / 12.0,
            courtage_pct=broker_fees.courtage_pct,
        )

    # Tax on the gains at exit, weighted by the wrappers the user actually holds.
    tax_rate = _tax_on_gains(wealth, cfg.projection)
    invested_nominal = [initial + monthly_contribution * t for t in range(months + 1)]
    median_after_tax = (
        mc["p50"][-1] - tax_rate * max(0.0, mc["p50"][-1] - invested_nominal[-1])
    ) / float(deflator[-1])

    def _real(series: "list[float] | np.ndarray") -> list[float]:
        """Nominal series → today's euros, element by element."""
        return [float(x) for x in np.asarray(series, dtype=float) / deflator]

    # Detect multi-broker situation: investment wrappers at >1 distinct institutions
    institutions = {
        acc.institution_name for acc in wealth.investment_accounts if acc.institution_name
    }
    multi_broker_warning: str | None = None
    if len(institutions) > 1:
        from .fees import config as _fees_config

        broker_name = broker_fees.name
        multi_broker_warning = (
            f"Tu as des investissements chez plusieurs courtiers ({', '.join(sorted(institutions))}). "
            f"Les frais affichés sont ceux de {broker_name}. "
            "Une projection multi-courtier viendra dans une prochaine version."
        )
        del _fees_config  # quiet linter if unused

    logger.info(
        "projection: broker=%s, %d months, initial=%.0f €, contrib=%.0f €/mo, fees@end=%.0f €",
        bid,
        months,
        initial,
        monthly_contribution,
        cumulative_fees[-1],
    )

    return ProjectionResponse(
        months=list(range(months + 1)),
        invested=_real(invested_nominal),
        bands=ProjectionBands(**{k: _real(v) for k, v in mc.items()}),
        annual_return=mu_simple,
        annual_vol=sigma_annual,
        goal=goal,
        goal_prob_at_end=goal_prob_at_end,
        goal_prob_by_month=goal_prob_by_month,
        broker_id=bid,
        broker=broker_fees.name,
        gross_p50=_real(gross_p50),
        cumulative_fees=_real(cumulative_fees),
        multi_broker_warning=multi_broker_warning,
        weighted_ter=weighted_ter,
        inflation=inflation,
        required_monthly=required_monthly,
        target_probability=cfg.projection.target_probability,
        tax_on_gains_pct=tax_rate,
        median_after_tax=median_after_tax,
    )


def _tax_on_gains(wealth: Wealth, cfg: "verdicts.ProjectionThresholds") -> float:
    """Average tax rate on the gains at exit, weighted by each wrapper's value.

    A PEA held five years owes social contributions only, a securities account
    owes the flat tax; the projection covers several wrappers at once, so the
    rate shown is their weighted average. Falls back to the flat tax.
    """
    total = 0.0
    weighted = 0.0
    for acc in wealth.investment_accounts:
        value = acc.value
        if value <= 0:
            continue
        total += value
        weighted += value * cfg.tax_on_gains.get(acc.account_type, cfg.default_tax_on_gains)
    if total <= 0:
        return cfg.default_tax_on_gains
    return weighted / total
