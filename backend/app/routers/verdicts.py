"""Verdicts — the method's conclusions on the user's patrimony (ADR-023)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..deps import get_session, get_user_wealth
from ..finance import verdicts
from ..models import VerdictsResponse, Wealth
from ..repositories import bank_transactions as tx_repo
from ..repositories import profile as profile_repo

router = APIRouter(tags=["verdicts"])


@router.get("/verdicts", response_model=VerdictsResponse)
async def read_verdicts(
    wealth: Wealth = Depends(get_user_wealth),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> VerdictsResponse:
    """One status, one sentence, one amount and one action per technique.

    Read by the simple screens (status + headline), the Méthode tab (details)
    and the briefing (same list in its snapshot).
    """
    profile = await profile_repo.get_or_create(session, user.id)
    spending = await tx_repo.monthly_outflow(session, user.id)
    return verdicts.compute_all(wealth, profile, monthly_spending=spending)
