"""Watchlist routes — track tickers without holding them."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..repositories import watchlist as watchlist_repo

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[str])
async def read_watchlist(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """List of tracked tickers for the current user."""
    return await watchlist_repo.list_tickers(session, user.id)


@router.post("/{ticker}", response_model=list[str])
async def add_to_watchlist(
    ticker: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Add a ticker to the user's watchlist. Idempotent."""
    return await watchlist_repo.add(session, user.id, ticker)


@router.delete("/{ticker}", response_model=list[str])
async def remove_from_watchlist(
    ticker: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Remove a ticker from the user's watchlist. No-op if not present."""
    return await watchlist_repo.remove(session, user.id, ticker)
