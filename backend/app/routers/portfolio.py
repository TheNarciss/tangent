"""Portfolio routes — multi-tenant CRUD over user's PEA positions."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..deps import get_user_portfolio
from ..models import Portfolio
from ..repositories import portfolio as portfolio_repo

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=Portfolio)
async def read_portfolio(pf: Portfolio = Depends(get_user_portfolio)) -> Portfolio:
    """Returns the current user's portfolio (positions + watchlist merged as qty=0)."""
    return pf


@router.put("/portfolio", response_model=Portfolio)
async def write_portfolio(
    new: Portfolio,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Portfolio:
    """Replace the current user's portfolio (positions + cash).

    Used by the manual editor in the UI. Powens sync uses the same repository
    method but via /sync/powens.
    """
    positions_data = [p.model_dump() for p in new.positions]
    await portfolio_repo.replace_positions(
        session, user.id,
        new_positions=positions_data,
        cash=new.cash,
    )
    # Reload the canonical state (with watchlist merged) for the response
    from ..deps import get_user_portfolio as _build
    # We can't call the dependency directly, so rebuild inline:
    positions = await portfolio_repo.get_positions_with_watchlist(session, user.id)
    pf = await portfolio_repo.get_or_create(session, user.id)
    from ..models import Position as DomainPosition
    return Portfolio(
        positions=[
            DomainPosition(ticker=p.ticker, quantity=p.quantity, avg_cost=p.avg_cost,
                           isin=p.isin, label=p.label)
            for p in positions
        ],
        cash=pf.cash,
    )