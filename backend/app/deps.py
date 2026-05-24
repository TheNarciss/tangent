"""Common FastAPI dependencies — auth + DB session + composite domain objects.

Most endpoints need:
1. The current authenticated user → Depends(current_active_user)
2. A DB session → Depends(get_session)
3. A Portfolio domain object (with positions + cash) built from DB

This module provides the composite dependencies so endpoints stay one-liner
clean instead of repeating glue code.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import User, current_active_user
from .db import get_session
from .models import Portfolio as DomainPortfolio
from .models import Position as DomainPosition
from .repositories import portfolio as portfolio_repo

logger = logging.getLogger(__name__)


async def get_user_portfolio(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> DomainPortfolio:
    """Build the Pydantic Portfolio domain object from the user's DB rows.

    Used by every analytics endpoint (dashboard, timeseries, optimizer, etc.)
    so they can keep their existing signature (operating on a Portfolio).
    """
    positions = await portfolio_repo.get_positions_with_watchlist(session, user.id)
    pf = await portfolio_repo.get_or_create(session, user.id)

    domain_positions = [
        DomainPosition(
            ticker=p.ticker,
            quantity=p.quantity,
            avg_cost=p.avg_cost,
            isin=p.isin,
            label=p.label,
        )
        for p in positions
    ]
    return DomainPortfolio(positions=domain_positions, cash=pf.cash)


# Re-export user/session deps so routers can do `from app.deps import current_active_user`
__all__ = [
    "current_active_user",
    "get_session",
    "get_user_portfolio",
    "User",
]