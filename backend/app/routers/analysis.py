"""Analysis routes — optimizer, projection, scanner."""

from fastapi import APIRouter, Depends, Query

from ..deps import get_user_portfolio, get_user_wealth
from ..finance import optimizer, projection, scanner
from ..models import (
    OptimizerRequest,
    OptimizerResponse,
    Portfolio,
    ProjectionResponse,
    ScanRequest,
    ScanResponse,
    Wealth,
)

router = APIRouter(tags=["analysis"])


@router.post("/optimizer", response_model=OptimizerResponse)
async def read_optimizer(
    req: OptimizerRequest,
    wealth: Wealth = Depends(get_user_wealth),
) -> OptimizerResponse:
    """Phase 2 PR 5: optimizer consumes Wealth (positions aggregated by ticker)."""
    return optimizer.build(req, wealth=wealth)


@router.get("/projection", response_model=ProjectionResponse)
async def read_projection(
    wealth: Wealth = Depends(get_user_wealth),
    monthly: float = Query(200, ge=0, le=100_000, description="Monthly contribution (€)"),
    years: int = Query(10, ge=1, le=50, description="Projection horizon (years)"),
    goal: float | None = Query(None, ge=0, description="Optional target (€)"),
    broker: str | None = Query(None, description="Broker ID (see /brokers)."),
) -> ProjectionResponse:
    """Phase 2 PR 4: projection consumes Wealth."""
    return projection.build(monthly, years, goal, broker, wealth=wealth)


@router.post("/scan", response_model=ScanResponse)
async def read_scan(
    req: ScanRequest,
    pf: Portfolio = Depends(get_user_portfolio),
) -> ScanResponse:
    """Discovers PEA-eligible assets via dynamic yfinance screening,
    computes their marginal ΔSharpe against the current portfolio.

    Note: Scanner still on legacy Portfolio; will be migrated in PR 6.
    """
    return scanner.scan(req, portfolio_data=pf)
