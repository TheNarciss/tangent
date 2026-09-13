"""« La liste de l'année » — today's momentum list and its track record."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import User, current_active_user
from ..finance import picks
from ..models import PicksResponse

router = APIRouter(tags=["picks"])


@router.get("/picks", response_model=PicksResponse)
async def read_picks(user: User = Depends(current_active_user)) -> PicksResponse:
    """The list as the scheduler last computed it (daily, and after a restart).

    503 while nothing has been computed yet — the few minutes after a first
    boot — rather than a stale list presented as today's.
    """
    stored = picks.load()
    if stored is None:
        raise HTTPException(
            status_code=503,
            detail="La liste est en cours de calcul, elle arrive dans quelques minutes.",
        )
    return stored
