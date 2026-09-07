"""Dashboard + timeseries — read-only analytics on the user's portfolio."""

from fastapi import APIRouter, Depends, Query

from ..deps import get_user_wealth
from ..finance import dashboard, timeseries
from ..finance.wealth_summary import build_summary as build_wealth_summary
from ..models import DashboardResponse, TimeseriesResponse, Wealth, WealthSummary

router = APIRouter(tags=["analytics"])


@router.get("/wealth", response_model=WealthSummary)
async def read_wealth(wealth: Wealth = Depends(get_user_wealth)) -> WealthSummary:
    """Patrimony snapshot built from the DB only (no market data).

    The single source of truth for "ton patrimoine" across the app: the
    Aperçu KPI strip and the Comptes header both read it.
    """
    return build_wealth_summary(wealth)


@router.get("/dashboard", response_model=DashboardResponse)
async def read_dashboard(
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
    return dashboard.build(
        cma_shrinkage=cma_shrinkage,
        historical_period=historical_period,
        risk_free=risk_free,
        wealth=wealth,
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
async def read_timeseries(
    wealth: Wealth = Depends(get_user_wealth),
) -> TimeseriesResponse:
    return timeseries.build(wealth=wealth)
