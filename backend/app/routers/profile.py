"""Profile endpoints — user's financial profile persisted in DB.

This complements (and will eventually replace) the frontend's localStorage-based
profile. The frontend syncs both ways: pull from DB at login, push on every edit.
"""

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db.engine import get_session
from ..finance import risk_profile
from ..repositories import profile as profile_repo

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    birth_date: date | None = None
    household_status: Literal["single", "couple"] | None = None
    children: int | None = Field(default=None, ge=0, le=20)
    fiscal_shares: float | None = Field(default=None, ge=0.5, le=20)
    rfr_n_minus_2: float | None = Field(default=None, ge=0)
    # Slider position; target_annual_return / max_annual_volatility are derived
    # from it server-side (config/risk_levels.yaml) and echoed back read-only.
    risk_level: int | None = Field(default=None, ge=1, le=5)
    target_annual_return: float | None = Field(default=None, ge=0, le=2)
    max_annual_volatility: float | None = Field(default=None, ge=0, le=1)
    monthly_dca: float | None = Field(default=None, ge=0)
    horizon_years: int | None = Field(default=None, ge=1, le=80)
    default_broker: str | None = Field(default=None, max_length=50)
    ceilings_used: dict[str, Any] | None = None
    auto_review_enabled: bool | None = None


class ProfileOut(ProfileIn):
    pass


def _to_out(prof) -> ProfileOut:
    return ProfileOut(
        birth_date=prof.birth_date,
        household_status=prof.household_status,
        children=prof.children,
        fiscal_shares=prof.fiscal_shares,
        rfr_n_minus_2=prof.rfr_n_minus_2,
        risk_level=prof.risk_level,
        target_annual_return=prof.target_annual_return,
        max_annual_volatility=prof.max_annual_volatility,
        monthly_dca=prof.monthly_dca,
        horizon_years=prof.horizon_years,
        default_broker=prof.default_broker,
        ceilings_used=prof.ceilings_used or {},
        auto_review_enabled=prof.auto_review_enabled,
    )


@router.get("/risk-levels", response_model=list[risk_profile.RiskLevel])
async def get_risk_levels(user: User = Depends(current_active_user)):
    """Slider positions with their labels and derived constraints (YAML-backed)."""
    return risk_profile.levels()


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
    if updates.get("risk_level") is not None:
        lv = risk_profile.resolve(updates["risk_level"])
        updates["target_annual_return"] = lv.target_annual_return
        updates["max_annual_volatility"] = lv.max_annual_volatility
    prof = await profile_repo.update(session, user.id, updates)
    return _to_out(prof)
