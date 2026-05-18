"""Pydantic schemas used both as API contracts and domain models."""
from datetime import date
from pydantic import BaseModel, Field


class Position(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)


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


class PortfolioMetrics(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    expected_return: float
    volatility: float
    sharpe: float
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


class OptimizerResponse(BaseModel):
    objective: str
    tickers: list[str]
    current: PortfolioPoint
    optimal: PortfolioPoint
    actions: list[RebalanceAction]
    risk_contributions_current: RiskContribution
    risk_contributions_optimal: RiskContribution
    frontier_curve: FrontierCurve