"""« Pistes de marché » — what the night collected, raw, before the briefing's triage."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import User, current_active_user
from ..finance import market_leads
from ..models import MarketLeadsResponse

router = APIRouter(tags=["market-leads"])


@router.get("/market-leads", response_model=MarketLeadsResponse)
async def read_market_leads(user: User = Depends(current_active_user)) -> MarketLeadsResponse:
    """The leads as the scheduler last collected them. 503 before the first collection."""
    stored = market_leads.load()
    if stored is None:
        raise HTTPException(
            status_code=503,
            detail="Les pistes de marché ne sont pas encore collectées, elles arrivent cette nuit.",
        )
    return stored
