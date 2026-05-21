"""Pydantic schemas used both as API contracts and domain models."""
from datetime import date
from pydantic import BaseModel, Field, model_validator


class Position(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(ge=0)   # 0 allowed for watchlist tickers (tracked without a transaction)
    avg_cost: float = Field(ge=0)
    # Optional fields enriched via Powens (None for legacy manual positions)
    isin: str | None = None
    label: str | None = None


class Portfolio(BaseModel):
    positions: list[Position]
    cash: float = 0.0


class AssetMetrics(BaseModel):
    ticker: str
    price: float
    weight: float
    value: float
    pnl: float
    pnl_pct: float
    annual_return: float
    annual_vol: float
    sharpe: float
    drawdown_estimate: float = 0.0      # = −2 × annual_vol (normal law, 97.5%)
    cvar_95: float = 0.0                # average loss on the worst 5% days (annualized)
    max_drawdown_observed: float = 0.0  # largest peak-to-trough drop in history


class PortfolioMetrics(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    expected_return: float
    volatility: float
    sharpe: float
    drawdown_estimate: float = 0.0      # = −2 × volatility
    cvar_95: float = 0.0                # CVaR 95% of the aggregated portfolio
    max_drawdown_observed: float = 0.0  # max drawdown of the reconstructed portfolio
    assets: list[AssetMetrics]
    correlation: dict[str, dict[str, float]]


class FrontierCloud(BaseModel):
    vol: list[float]
    ret: list[float]
    sharpe: list[float]


class Insight(BaseModel):
    severity: str  # "good" | "warning" | "critical"
    title: str
    detail: str


class DashboardResponse(BaseModel):
    as_of: date
    metrics: PortfolioMetrics
    frontier: FrontierCloud
    insights: list[Insight]
    stress_tests: list["StressTestResult"] = Field(default_factory=list)


class TimeseriesResponse(BaseModel):
    dates: list[date]
    portfolio: list[float]                   # rebased to 100 at first date
    benchmark: list[float] | None            # rebased to 100; None if unavailable
    benchmark_ticker: str | None
    drawdown: list[float]                    # ∈ [-1, 0]
    rolling_sharpe: list[float | None]       # None for the first `window` days
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
    months: list[int]                       # 0, 1, …, n_months
    invested: list[float]                   # cumulative contributions
    bands: ProjectionBands
    annual_return: float
    annual_vol: float
    goal: float | None
    goal_prob_at_end: float | None          # ∈ [0, 1] if goal provided
    goal_prob_by_month: list[float] | None
    # Broker fees impact
    broker_id: str
    broker: str                             # human-readable name
    gross_p50: list[float]                  # P50 without fees, for comparison
    cumulative_fees: list[float]            # cumulative fee impact at each month (€)


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


class Transaction(BaseModel):
    """A single dated cashflow or trade. Source of truth for portfolio state."""
    date: str = Field(description="ISO date or datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM)")
    type: str = Field(pattern="^(buy|sell|deposit|withdrawal|dividend)$")
    ticker: str | None = None
    qty: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)
    fees: float = Field(default=0, ge=0)
    amount_eur: float | None = Field(default=None, description="For deposits, withdrawals, and dividends")


class PortfolioPoint(BaseModel):
    weights: list[float]
    expected_return: float
    volatility: float
    sharpe: float


class RebalanceAction(BaseModel):
    ticker: str
    current_weight: float
    optimal_weight: float
    delta_weight: float                     # optimal − current
    delta_value: float                      # delta_weight × total_value (€)


class RiskContribution(BaseModel):
    tickers: list[str]
    fraction: list[float]                   # sums to 1


class FrontierCurve(BaseModel):
    vol: list[float]
    ret: list[float]
    sharpe: list[float]


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
    hypothesis_fraction: float = Field(default=0.10, gt=0, le=0.50,
                                       description="Simulated allocation fraction for ΔSharpe (10% = 0.10)")
    n_results: int = Field(default=10, ge=1, le=50)
    expert: ExpertSettings | None = None


class ScanCandidate(BaseModel):
    ticker: str
    name: str
    sector: str
    market_cap: float
    own_mu: float                      # candidate's blended μ
    own_sigma: float                   # historical σ
    own_sharpe: float                  # standalone Sharpe
    correlation_with_portfolio: float  # ρ with the current portfolio
    delta_sharpe: float                # ΔSharpe if added at h% of the portfolio
    pea_eligible: bool
    rationale: str                     # short explanation string


class ScanResponse(BaseModel):
    candidates: list[ScanCandidate]
    universe_size: int                 # raw number of tickers screened before ranking
    modes_used: list[str]
    elapsed_seconds: float


class EnvelopePoint(BaseModel):
    """Coordinates (σ, μ) of a regulated envelope on the risk-return scatter.
    σ ≈ 0 by construction (livrets, fonds €): a guaranteed-rate asset has no
    dispersion of returns. Rendered as a small marker so the user sees where
    the optimizer is placing its 'low-risk' envelopes."""
    label: str
    expected_return: float                  # annualized, e.g. 0.030 for Livret A 3%
    volatility: float                       # ~0, the model uses 1e-3 for SLSQP stability


class CeilingsUsed(BaseModel):
    livret_a: float = 0
    livret_a_jeune: float = 0
    ldds: float = 0
    lep: float = 0
    pel: float = 0


class OptimizerRequest(BaseModel):
    objective: str = Field(default="max_sharpe", pattern="^(max_sharpe|min_variance|target_volatility|from_strategy)$")
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
        if self.objective == "from_strategy" and (self.max_volatility is None or self.target_return is None):
            raise ValueError("max_volatility AND target_return are required when objective='from_strategy'.")
        return self


class OptimizerResponse(BaseModel):
    objective: str
    # All asset universe (ETFs first, envelopes after)
    asset_ids: list[str]
    asset_kinds: list[str]                   # "etf" | "envelope"
    asset_labels: list[str]                  # human-readable names
    total_capital: float                     # € pool used to resolve euro amounts
    current: PortfolioPoint
    optimal: PortfolioPoint
    actions: list[RebalanceAction]
    risk_contributions_current: RiskContribution
    risk_contributions_optimal: RiskContribution
    frontier_curve: FrontierCurve            # ETF-only curve (envelope-augmented frontier is just a kink)
    envelope_points: list[EnvelopePoint] = Field(default_factory=list)
    kelly_leverage: KellyLeverage | None = None  # sanity check: does Kelly recommend leverage or cash?


class StrategyRequest(BaseModel):
    """Computes the recommended strategy via glide path from the minimal profile."""
    age: int = Field(ge=0, le=120)
    horizon_years: int = Field(ge=1, le=100)
    rule: str = Field(default="120_age", pattern="^(100_age|120_age|custom)$")
    custom_multiplier: float | None = Field(default=None, ge=0, le=1)


# Forward-ref resolution: DashboardResponse references StressTestResult defined later
DashboardResponse.model_rebuild()