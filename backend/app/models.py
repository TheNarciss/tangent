"""Pydantic schemas used both as API contracts and domain models."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetMetrics(BaseModel):
    ticker: str
    label: str | None = None  # fund name as the provider labels it (shown instead of the ticker)
    price: float
    weight: float
    value: float
    pnl: float
    pnl_pct: float
    annual_return: float
    annual_vol: float
    sharpe: float
    drawdown_estimate: float = 0.0  # = −2 × annual_vol (normal law, 97.5%)
    cvar_95: float = 0.0  # average loss on the worst 5% days (annualized)
    max_drawdown_observed: float = 0.0  # largest peak-to-trough drop in history


class PortfolioMetrics(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    expected_return: float
    volatility: float
    sharpe: float
    drawdown_estimate: float = 0.0  # = −2 × volatility
    cvar_95: float = 0.0  # CVaR 95% of the aggregated portfolio
    max_drawdown_observed: float = 0.0  # max drawdown of the reconstructed portfolio
    assets: list[AssetMetrics]
    correlation: dict[str, dict[str, float]]
    # Tickers without a forward-looking μ (not in cma.yaml): their expected
    # return is the historical one only. Surfaced so the UI can say so.
    unmapped_tickers: list[str] = Field(default_factory=list)


class Insight(BaseModel):
    severity: str  # "good" | "warning" | "critical"
    title: str
    detail: str


class DashboardResponse(BaseModel):
    as_of: date
    metrics: PortfolioMetrics
    insights: list[Insight]
    stress_tests: list["StressTestResult"] = Field(default_factory=list)


class TimeseriesResponse(BaseModel):
    dates: list[date]
    portfolio: list[float]  # rebased to 100 at first date
    benchmark: list[float] | None  # rebased to 100; None if unavailable
    benchmark_ticker: str | None
    drawdown: list[float]  # ∈ [-1, 0]
    rolling_sharpe: list[float | None]  # None for the first `window` days
    rolling_window_days: int


class ProjectionBands(BaseModel):
    bear: list[float]
    base: list[float]
    bull: list[float]
    p10: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p90: list[float]


class ProjectionResponse(BaseModel):
    months: list[int]  # 0, 1, …, n_months
    invested: list[float]  # cumulative contributions
    bands: ProjectionBands
    annual_return: float
    annual_vol: float
    goal: float | None
    goal_prob_at_end: float | None  # ∈ [0, 1] if goal provided
    goal_prob_by_month: list[float] | None
    # Broker fees impact
    broker_id: str
    broker: str  # human-readable name
    gross_p50: list[float]  # P50 without fees, for comparison
    cumulative_fees: list[float]  # cumulative fee impact at each month (€)
    multi_broker_warning: str | None = None
    # ADR-021: weighted average TER (Total Expense Ratio) applied as monthly fee
    weighted_ter: float = 0.0  # ratio (0.0025 = 0.25%/an), shown, not simulated (ADR-023)


class BrokerInfo(BaseModel):
    id: str
    name: str


class BrokersResponse(BaseModel):
    default: str
    brokers: list[BrokerInfo]


class EligibilityRequest(BaseModel):
    age: int = Field(ge=0, le=120)
    rfr: float = Field(ge=0, description="French Reference Tax Income N-2 (€)")
    fiscal_shares: float = Field(ge=0.5, le=20, description="Number of fiscal shares")


class EnvelopeEligibility(BaseModel):
    id: str
    name: str
    rate_pct: float
    ceiling_eur: float | None
    tax_status: str
    liquidity_days: int
    eligible: bool
    note: str


class EligibleEnvelopesResponse(BaseModel):
    envelopes: list[EnvelopeEligibility]


class PortfolioPoint(BaseModel):
    weights: list[float]
    expected_return: float
    volatility: float
    sharpe: float


class RebalanceAction(BaseModel):
    ticker: str
    current_weight: float
    optimal_weight: float
    delta_weight: float  # optimal − current
    delta_value: float  # delta_weight × total_value (€)


class RiskContribution(BaseModel):
    tickers: list[str]
    fraction: list[float]  # sums to 1


class FrontierCurve(BaseModel):
    vol: list[float]
    ret: list[float]
    sharpe: list[float]
    unavailable_reason: str | None = None


class ExpertSettings(BaseModel):
    """Advanced parameters for curious users; all optional with smart defaults.

    - cma_shrinkage: 0 = pure historical 5y μ (inflated), 1 = pure long-term CMA.
      Backend default: 0.70 (70% CMA, 30% historical).
    - cma_overrides: ticker → forward-looking μ (fraction) map. Overrides the YAML.
    - historical_period: yfinance period used to compute σ and correlations.
    - risk_free_rate: risk-free rate used by Sharpe and Kelly. Default 2.5%.
    - cov_estimator: "sample" (default) or "shrunk" (simplified Ledoit-Wolf).
    - cov_shrinkage: shrinkage fraction if "shrunk", default 0.20.
    """

    cma_shrinkage: float | None = Field(default=None, ge=0, le=1)
    cma_overrides: dict[str, float] = Field(default_factory=dict)
    historical_period: str | None = Field(default=None, pattern="^(1y|2y|3y|5y|10y|max)$")
    risk_free_rate: float | None = Field(default=None, ge=0, le=0.20)
    cov_estimator: str = Field(default="sample", pattern="^(sample|shrunk)$")
    cov_shrinkage: float = Field(default=0.20, ge=0, le=1)


class KellyLeverage(BaseModel):
    """Kelly indicator: how much the Kelly solver would invest under relaxed constraints."""

    full_kelly_leverage: float
    half_kelly_leverage: float
    interpretation: str


class StressTestResult(BaseModel):
    id: str
    label: str
    description: str
    start: str
    end: str
    pnl_pct: float
    drawdown_pct: float


class ScanRequest(BaseModel):
    """Scan configuration: enabled modes + ΔSharpe parameters."""

    modes: list[str] = Field(
        default_factory=lambda: ["broad_eu", "tech_growth", "defensive"],
        description="Modes to enable: broad_eu, tech_growth, defensive",
    )
    hypothesis_fraction: float = Field(
        default=0.10,
        gt=0,
        le=0.50,
        description="Simulated allocation fraction for ΔSharpe (10% = 0.10)",
    )
    n_results: int = Field(default=10, ge=1, le=50)
    expert: ExpertSettings | None = None


class ScanCandidate(BaseModel):
    ticker: str
    name: str
    sector: str
    market_cap: float
    own_mu: float  # candidate's blended μ
    own_sigma: float  # historical σ
    own_sharpe: float  # standalone Sharpe
    correlation_with_portfolio: float  # ρ with the current portfolio
    delta_sharpe: float  # ΔSharpe if added at h% of the portfolio
    pea_eligible: bool
    rationale: str  # short explanation string


class ScanResponse(BaseModel):
    candidates: list[ScanCandidate]
    universe_size: int  # raw number of tickers screened before ranking
    modes_used: list[str]
    elapsed_seconds: float


class EnvelopePoint(BaseModel):
    """Coordinates (σ, μ) of a regulated envelope on the risk-return scatter.
    σ ≈ 0 by construction (livrets, fonds €): a guaranteed-rate asset has no
    dispersion of returns. Rendered as a small marker so the user sees where
    the optimizer is placing its 'low-risk' envelopes."""

    label: str
    expected_return: float  # annualized, e.g. 0.030 for Livret A 3%
    volatility: float  # ~0, the model uses 1e-3 for SLSQP stability


class CeilingsUsed(BaseModel):
    livret_a: float = 0
    livret_a_jeune: float = 0
    ldds: float = 0
    lep: float = 0
    pel: float = 0


class OptimizerRequest(BaseModel):
    objective: str = Field(
        default="max_sharpe", pattern="^(max_sharpe|min_variance|target_volatility|from_strategy)$"
    )
    # Risk-target objective (required when objective == 'target_volatility' or 'from_strategy')
    max_volatility: float | None = Field(default=None, ge=0, le=1)
    # Return-target (required when objective == 'from_strategy')
    target_return: float | None = Field(default=None, ge=0, le=2)
    # Envelope inclusion + profile (all required together for eligibility)
    include_envelopes: bool = False
    age: int | None = Field(default=None, ge=0, le=120)
    rfr: float | None = Field(default=None, ge=0)
    fiscal_shares: float | None = Field(default=None, ge=0.5, le=20)
    ceilings_used: CeilingsUsed | None = None
    # Optional total capital pool (€). Defaults to current ETF portfolio value.
    total_capital: float | None = Field(default=None, ge=0)
    # Expert overrides (shrinkage, CMA, periods…). All optional, smart defaults.
    expert: ExpertSettings | None = None

    @model_validator(mode="after")
    def _check_objective_params(self) -> "OptimizerRequest":
        if self.objective == "target_volatility" and self.max_volatility is None:
            raise ValueError("max_volatility is required when objective='target_volatility'.")
        if self.objective == "from_strategy" and (
            self.max_volatility is None or self.target_return is None
        ):
            raise ValueError(
                "max_volatility AND target_return are required when objective='from_strategy'."
            )
        return self


class OptimizerResponse(BaseModel):
    objective: str
    # All asset universe (ETFs first, envelopes after)
    asset_ids: list[str]
    asset_kinds: list[str]  # "etf" | "envelope"
    asset_labels: list[str]  # human-readable names
    total_capital: float  # € pool used to resolve euro amounts
    current: PortfolioPoint
    optimal: PortfolioPoint
    actions: list[RebalanceAction]
    risk_contributions_current: RiskContribution
    risk_contributions_optimal: RiskContribution
    frontier_curve: FrontierCurve  # ETF-only curve (envelope-augmented frontier is just a kink)
    envelope_points: list[EnvelopePoint] = Field(default_factory=list)
    unmapped_tickers: list[str] = Field(default_factory=list)
    kelly_leverage: KellyLeverage | None = (
        None  # sanity check: does Kelly recommend leverage or cash?
    )


class StrategyRequest(BaseModel):
    """Computes the recommended strategy via glide path from the minimal profile."""

    age: int = Field(ge=0, le=120)
    horizon_years: int = Field(ge=1, le=100)
    rule: str = Field(default="120_age", pattern="^(100_age|120_age|custom)$")
    custom_multiplier: float | None = Field(default=None, ge=0, le=1)


# Forward-ref resolution: DashboardResponse references StressTestResult defined later


# ════════════════════════════════════════════════════════════════════════════
#  Wealth domain models (Phase 2 of the legacy migration)
# ════════════════════════════════════════════════════════════════════════════
#
# Models the user's complete financial picture in 5 distinct categories.
# Names prefixed with "Wealth" where they would clash with existing classes
# (e.g. `Position` above, `Envelope` in finance/envelopes.py).
#
class Verdict(BaseModel):
    """One conclusion of the method, ready to display (ADR-023).

    The engine computes, the simple screens show `status` + `headline`, the
    Méthode tab unfolds `details`, the briefing reads the same list.
    """

    id: str
    title: str
    status: Literal["green", "amber", "red", "unknown"]
    headline: str
    impact_eur_per_year: float | None = None
    action: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class VerdictsResponse(BaseModel):
    computed_at: datetime
    verdicts: list[Verdict]


# No DB equivalent — built on the fly by `deps.get_user_wealth()`.


from datetime import date as _dt_date  # noqa: E402
from uuid import UUID as _UUID  # noqa: E402


class WealthPosition(BaseModel):
    """A position inside an investment account, with current valuation."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    label: str
    isin: str | None = None
    quantity: float
    avg_cost: float = Field(..., description="Cost basis per unit (PRU)")
    current_value: float = Field(..., description="Total current valuation")
    currency: str = "EUR"
    ter: float | None = Field(
        default=None, description="Annual fund expense ratio as a fraction (0.0025 = 0.25 %)"
    )

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        return self.current_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis


class CashAccount(BaseModel):
    """Liquid cash account : checking, non-regulated savings, or PEA cash."""

    model_config = ConfigDict(extra="forbid")

    provider_account_id: str
    institution_name: str | None = None
    name: str
    balance: float
    currency: str = "EUR"
    is_pea_cash: bool = Field(
        default=False,
        description="True for PEA cash sub-accounts (investable inside PEA only)",
    )


class WealthEnvelope(BaseModel):
    """A user's regulated savings envelope. Runtime data + metadata from YAML."""

    model_config = ConfigDict(extra="forbid")

    provider_account_id: str
    institution_name: str | None = None
    name: str
    balance: float
    envelope_type: str = Field(..., description="livret_a | ldds | lep | pel | ...")
    currency: str = "EUR"

    display_name: str | None = Field(default=None, description="Human label from YAML")
    rate_pct: float | None = Field(default=None, description="Annual rate as decimal")
    ceiling_eur: float | None = Field(default=None, description="Legal ceiling")
    tax_status: str | None = Field(default=None, description='"net" or "gross"')

    @property
    def headroom_eur(self) -> float | None:
        if self.ceiling_eur is None:
            return None
        return max(0.0, self.ceiling_eur - self.balance)


class InvestmentAccount(BaseModel):
    """A wrapper account (PEA, CTO, AV, PER, PEE, real estate…) and its positions.

    `balance` is the provider-side valuation of the whole account. It is the
    fallback value when the provider exposes no line-by-line positions (fonds
    euros of a life insurance, a PER managed by the employer, real estate…).
    """

    model_config = ConfigDict(extra="forbid")

    provider_account_id: str
    institution_name: str | None = None
    name: str
    account_type: str = Field(..., description="pea | cto | life_insurance | per | pee | …")
    currency: str = "EUR"
    balance: float = Field(default=0.0, description="Provider valuation of the account")
    positions: list[WealthPosition] = []

    @property
    def positions_value(self) -> float:
        return sum(p.current_value for p in self.positions)

    @property
    def value(self) -> float:
        """What the account is worth: its positions, else the provider balance."""
        return self.positions_value if self.positions else self.balance

    @property
    def cost_basis(self) -> float:
        return sum(p.cost_basis for p in self.positions)

    @property
    def unrealized_pnl(self) -> float:
        return self.positions_value - self.cost_basis


class Loan(BaseModel):
    """Outstanding loan. `outstanding_balance` is positive (amount still owed)."""

    model_config = ConfigDict(extra="forbid")

    provider_account_id: str
    institution_name: str | None = None
    name: str
    outstanding_balance: float = Field(..., ge=0)
    currency: str = "EUR"

    interest_rate_pct: float | None = None
    monthly_payment: float | None = None
    next_payment_date: _dt_date | None = None
    deferral_until: _dt_date | None = None
    maturity_date: _dt_date | None = None

    @property
    def is_in_deferral(self) -> bool:
        if self.deferral_until is None:
            return False
        return _dt_date.today() < self.deferral_until


class Wealth(BaseModel):
    """Complete patrimony snapshot. Aggregate root."""

    model_config = ConfigDict(extra="forbid")

    user_id: _UUID
    snapshot_at: datetime

    checking_accounts: list[CashAccount] = []
    pea_cash_accounts: list[CashAccount] = []
    envelopes: list[WealthEnvelope] = []
    investment_accounts: list[InvestmentAccount] = []
    loans: list[Loan] = []

    @property
    def checking_total(self) -> float:
        return sum(a.balance for a in self.checking_accounts)

    @property
    def pea_cash_total(self) -> float:
        return sum(a.balance for a in self.pea_cash_accounts)

    @property
    def envelopes_total(self) -> float:
        return sum(e.balance for e in self.envelopes)

    @property
    def investments_total(self) -> float:
        return sum(acc.value for acc in self.investment_accounts)

    @property
    def investments_cost_basis(self) -> float:
        return sum(acc.cost_basis for acc in self.investment_accounts)

    @property
    def unrealized_pnl(self) -> float:
        # Per account: accounts valued at their balance (no positions) have no
        # cost basis, so they contribute 0 rather than their whole value.
        return sum(acc.unrealized_pnl for acc in self.investment_accounts)

    @property
    def liquid_assets(self) -> float:
        return self.checking_total

    @property
    def total_assets(self) -> float:
        return (
            self.checking_total
            + self.pea_cash_total
            + self.envelopes_total
            + self.investments_total
        )

    @property
    def total_liabilities(self) -> float:
        return sum(loan.outstanding_balance for loan in self.loans)

    @property
    def net_worth(self) -> float:
        return self.total_assets - self.total_liabilities

    @property
    def all_positions(self) -> list[WealthPosition]:
        return [p for acc in self.investment_accounts for p in acc.positions]


# ════════════════════════════════════════════════════════════════════════════
#  WealthSummary — patrimony snapshot served by GET /wealth (Phase 2 PR 2/6)
# ════════════════════════════════════════════════════════════════════════════
#
# Light DTO carrying the patrimony view. Served by GET /wealth (DB only, no
# market data) and read by the Aperçu KPI strip and the Comptes header, so the
# app shows one "patrimoine net".
#
# Sized for serialisation : we don't ship every individual position here, only
# the aggregates the frontend needs.


class EnvelopeSummary(BaseModel):
    """One regulated savings envelope as displayed in the dashboard."""

    model_config = ConfigDict(extra="forbid")

    name: str
    institution_name: str | None = None
    envelope_type: str
    balance: float
    display_name: str | None = None
    rate_pct: float | None = None
    ceiling_eur: float | None = None
    headroom_eur: float | None = None


class LoanSummary(BaseModel):
    """One outstanding loan as displayed in the dashboard."""

    model_config = ConfigDict(extra="forbid")

    name: str
    institution_name: str | None = None
    outstanding_balance: float
    interest_rate_pct: float | None = None
    monthly_payment: float | None = None
    next_payment_date: _dt_date | None = None
    deferral_until: _dt_date | None = None
    is_in_deferral: bool = False


class WealthSummary(BaseModel):
    """Patrimony snapshot, ready for the Aperçu tab."""

    model_config = ConfigDict(extra="forbid")

    # Headline figures
    net_worth: float
    total_assets: float
    total_liabilities: float

    # Per-category totals
    checking_total: float
    pea_cash_total: float
    envelopes_total: float
    investments_total: float
    unrealized_pnl: float

    # Detail for table rendering
    envelopes: list[EnvelopeSummary] = []
    loans: list[LoanSummary] = []


# Re-resolve forward references now that StressTestResult is defined.
DashboardResponse.model_rebuild()
