"""Profile endpoints — user's financial profile persisted in DB.

This complements (and will eventually replace) the frontend's localStorage-based
profile. The frontend syncs both ways: pull from DB at login, push on every edit.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db.engine import get_session
from ..repositories import profile as profile_repo

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    birth_date: date | None = None
    fiscal_shares: float | None = Field(default=None, ge=0.5, le=20)
    rfr_n_minus_2: float | None = Field(default=None, ge=0)
    target_annual_return: float | None = Field(default=None, ge=0, le=2)
    max_annual_volatility: float | None = Field(default=None, ge=0, le=1)
    horizon_years: int | None = Field(default=None, ge=1, le=80)
    default_broker: str | None = Field(default=None, max_length=50)
    ceilings_used: dict[str, Any] | None = None


class ProfileOut(ProfileIn):
    pass


def _to_out(prof) -> ProfileOut:
    return ProfileOut(
        birth_date=prof.birth_date,
        fiscal_shares=prof.fiscal_shares,
        rfr_n_minus_2=prof.rfr_n_minus_2,
        target_annual_return=prof.target_annual_return,
        max_annual_volatility=prof.max_annual_volatility,
        horizon_years=prof.horizon_years,
        ceilings_used=prof.ceilings_used or {},
    )


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Returns the profile for the current user, creating an empty one if missing."""
    prof = await profile_repo.get_or_create(session, user.id)
    return _to_out(prof)


@router.put("", response_model=ProfileOut)
async def update_profile(
    body: ProfileIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Patch the profile. Only fields explicitly set in body are touched."""
    updates = body.model_dump(exclude_unset=True)
    prof = await profile_repo.update(session, user.id, updates)
    return _to_out(prof)
