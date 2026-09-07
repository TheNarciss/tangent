"""Analysis routes — optimizer, projection, scanner."""

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..deps import get_session, get_user_wealth
from ..finance import optimizer, projection, scanner
from ..models import (
    OptimizerRequest,
    OptimizerResponse,
    ProjectionResponse,
    ScanRequest,
    ScanResponse,
    Wealth,
)
from ..repositories import account_holdings as holdings_repo
from ..repositories import profile as profile_repo

router = APIRouter(tags=["analysis"])


@router.post("/optimizer", response_model=OptimizerResponse)
async def read_optimizer(
    req: OptimizerRequest,
    wealth: Wealth = Depends(get_user_wealth),
) -> OptimizerResponse:
    # yfinance + SLSQP are blocking: keep them off the event loop.
    return await run_in_threadpool(optimizer.build, req, wealth=wealth)


@router.get("/projection", response_model=ProjectionResponse)
async def read_projection(
    wealth: Wealth = Depends(get_user_wealth),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    monthly: float = Query(200, ge=0, le=100_000, description="Monthly contribution (€)"),
    years: int = Query(10, ge=1, le=50, description="Projection horizon (years)"),
    goal: float | None = Query(None, ge=0, description="Optional target (€)"),
    broker: str | None = Query(None, description="Override broker (defaults to profile)."),
) -> ProjectionResponse:
    # Resolve broker_id: explicit query param > profile.default_broker > YAML default
    effective_broker = broker
    if effective_broker is None:
        profile = await profile_repo.get_or_create(session, user.id)
        effective_broker = profile.default_broker
    # ADR-021: subtract weighted TER as a monthly fee on top of broker fees
    weighted_ter = await holdings_repo.get_weighted_ter(session, user.id)
    return await run_in_threadpool(
        projection.build,
        monthly,
        years,
        goal,
        effective_broker,
        wealth=wealth,
        weighted_ter=weighted_ter,
    )


@router.post("/scan", response_model=ScanResponse)
async def read_scan(
    req: ScanRequest,
    wealth: Wealth = Depends(get_user_wealth),
) -> ScanResponse:
    """Discovers PEA-eligible assets via dynamic yfinance screening,
    computes their marginal ΔSharpe against the current portfolio."""
    return await run_in_threadpool(scanner.scan, req, wealth=wealth)
