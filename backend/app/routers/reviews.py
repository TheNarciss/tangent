"""HTTP routes for LLM-generated portfolio reviews.

Three endpoints (ADR-015):
- POST /reviews/generate  -> SSE stream of the generated markdown
- GET  /reviews/today     -> today\'s review (or null if absent)
- GET  /reviews           -> windowed history (newest first)

The SSE pre-check happens BEFORE returning StreamingResponse so the
kill-switch / duplicate-day errors surface as proper HTTP 503/409
(impossible once the stream has started).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user, fastapi_users
from ..deps import get_session, get_user_wealth
from ..llm import cost_tracker, review_generator
from ..models import Wealth
from ..repositories import reviews as reviews_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


class PortfolioReviewResponse(BaseModel):
    """One generated review, ready for the frontend."""

    id: uuid.UUID
    review_date: date
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    web_searches_count: int
    cost_usd: float
    sources: list[dict] = Field(default_factory=list)
    created_at: datetime


def _to_response(row) -> PortfolioReviewResponse:
    return PortfolioReviewResponse(
        id=row.id,
        review_date=row.review_date,
        content=row.content,
        model_used=row.model_used,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        web_searches_count=row.web_searches_count,
        cost_usd=row.cost_usd,
        sources=list(row.sources or []),
        created_at=row.created_at,
    )


@router.post("/generate")
async def generate_review(
    wealth: Wealth = Depends(get_user_wealth),
    user: User = Depends(fastapi_users.current_user(active=True, superuser=True)),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Stream a freshly generated review as SSE.

    Errors handled BEFORE the stream starts (proper HTTP statuses):
    - 503 if global daily cost cap reached
    - 409 if user already has a review for today
    - 500 if anything else (no chunks emitted)

    Errors mid-stream emit `event: error\ndata: {...}\n\n` and close.
    """
    today = cost_tracker.today_paris()

    if not await cost_tracker.is_under_cap(session, today):
        raise HTTPException(
            status_code=503,
            detail="Le budget LLM quotidien est atteint. Réessaye demain.",
        )

    existing = await reviews_repo.get_review_for_date(session, user.id, today)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Tu as déjà généré une review aujourd'hui. Reviens demain.",
        )

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in review_generator.generate_review_stream(session, user.id, wealth):
                payload = json.dumps({"chunk": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "event: done\ndata: {}\n\n"
        except review_generator.ReviewBlocked as exc:
            # Defensive: race between pre-check and stream start. Rare.
            payload = json.dumps({"reason": exc.reason}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"
        except Exception:
            logger.exception("Review stream failed mid-flight user=%s", user.id)
            payload = json.dumps({"reason": "internal"}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable Nginx/Caddy buffering
        },
    )


@router.get("/today", response_model=PortfolioReviewResponse | None)
async def get_today_review(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> PortfolioReviewResponse | None:
    """Returns the review generated today (Europe/Paris), or null."""
    today = cost_tracker.today_paris()
    row = await reviews_repo.get_review_for_date(session, user.id, today)
    return _to_response(row) if row else None


@router.get("", response_model=list[PortfolioReviewResponse])
async def list_reviews(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    limit: int = Query(90, ge=1, le=365),
) -> list[PortfolioReviewResponse]:
    """Returns the user\'s reviews within an optional window, newest first."""
    rows = await reviews_repo.list_reviews(
        session, user.id, from_date=from_date, to_date=to_date, limit=limit
    )
    return [_to_response(r) for r in rows]
