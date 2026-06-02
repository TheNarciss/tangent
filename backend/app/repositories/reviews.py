"""PortfolioReview repository — INSERT atomic + history fetch.

Multi-tenancy enforced via user_id filter on every read/write (ADR-002).
The UNIQUE constraint on (user_id, review_date) caps generation at 1/day
per user (ADR-015); concurrent INSERTs race on the DB and the loser gets
IntegrityError, which the caller maps to HTTP 409.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PortfolioReview

logger = logging.getLogger(__name__)


async def create_review(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    review_date: date,
    content: str,
    model_used: str,
    input_tokens: int,
    output_tokens: int,
    web_searches_count: int,
    cost_usd: float,
    sources: list[dict[str, Any]],
    wealth_snapshot: dict[str, Any],
) -> PortfolioReview:
    """Insert a new review for (user_id, review_date).

    Raises sqlalchemy.exc.IntegrityError if a review already exists for this
    (user_id, review_date) tuple — caller should catch and translate to a
    user-facing 409 ("you already have a review today").
    """
    row = PortfolioReview(
        user_id=user_id,
        review_date=review_date,
        content=content,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        web_searches_count=web_searches_count,
        cost_usd=cost_usd,
        sources=sources,
        wealth_snapshot=wealth_snapshot,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(
        "Review persisted user=%s date=%s tokens=%d/%d cost=$%.4f",
        user_id,
        review_date.isoformat(),
        input_tokens,
        output_tokens,
        cost_usd,
    )
    return row


async def get_review_for_date(
    session: AsyncSession,
    user_id: uuid.UUID,
    review_date: date,
) -> PortfolioReview | None:
    """Return the user\'s review for a given calendar day, or None."""
    stmt = select(PortfolioReview).where(
        PortfolioReview.user_id == user_id,
        PortfolioReview.review_date == review_date,
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def list_reviews(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 90,
) -> list[PortfolioReview]:
    """Return reviews for user_id within an optional date window, newest first."""
    stmt = select(PortfolioReview).where(PortfolioReview.user_id == user_id)
    if from_date is not None:
        stmt = stmt.where(PortfolioReview.review_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(PortfolioReview.review_date <= to_date)
    stmt = stmt.order_by(PortfolioReview.review_date.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
