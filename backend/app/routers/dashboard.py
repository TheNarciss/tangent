"""Dashboard + timeseries — read-only analytics on the user's portfolio."""

from fastapi import APIRouter, Depends, Query

from ..deps import get_user_portfolio
from ..finance import dashboard, timeseries
from ..models import DashboardResponse, Portfolio, TimeseriesResponse

router = APIRouter(tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def read_dashboard(
    pf: Portfolio = Depends(get_user_portfolio),
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
    return dashboard.build(
        cma_shrinkage=cma_shrinkage,
        historical_period=historical_period,
        risk_free=risk_free,
        portfolio_data=pf,
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
async def read_timeseries(pf: Portfolio = Depends(get_user_portfolio)) -> TimeseriesResponse:
    return timeseries.build(portfolio_data=pf)
