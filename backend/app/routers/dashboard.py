"""Dashboard + timeseries — read-only analytics on the user's portfolio."""

from fastapi import APIRouter, Depends, Query

from ..deps import get_user_portfolio, get_user_wealth
from ..finance import dashboard, timeseries
from ..finance.wealth_summary import build_summary as build_wealth_summary
from ..models import DashboardResponse, Portfolio, TimeseriesResponse, Wealth

router = APIRouter(tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def read_dashboard(
    pf: Portfolio = Depends(get_user_portfolio),
    wealth: Wealth = Depends(get_user_wealth),
    cma_shrinkage: float | None = Query(
        None, ge=0, le=1, description="0=pure historical, 1=pure CMA. Backend default: 0.7"
    ),
    historical_period: str = Query(
        "5y",
        pattern="^(1y|2y|3y|5y|10y|max)$",
        description="yfinance period used for σ and correlation",
    ),
    risk_free: float | None = Query(
        None, ge=0, le=0.20, description="Risk-free rate (fraction). Default: 0.025"
    ),
) -> DashboardResponse:
    response = dashboard.build(
        cma_shrinkage=cma_shrinkage,
        historical_period=historical_period,
        risk_free=risk_free,
        portfolio_data=pf,
    )
    # Phase 2 PR 2: enrich Aperçu with Wealth context (net worth, livrets, loans)
    response.wealth = build_wealth_summary(wealth)
    return response


@router.get("/timeseries", response_model=TimeseriesResponse)
async def read_timeseries(
    wealth: Wealth = Depends(get_user_wealth),
) -> TimeseriesResponse:
    """Phase 2 PR 3: Historique consumes Wealth (was Portfolio legacy)."""
    return timeseries.build(wealth=wealth)
