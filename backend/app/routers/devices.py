"""The phones that agreed to be told when a briefing is ready (ADR-037)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..i18n import Locale, current_locale
from ..repositories import device_tokens as tokens_repo

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceIn(BaseModel):
    """Apple's address for this app on this phone, as hexadecimal."""

    token: str = Field(..., min_length=32, max_length=200, pattern=r"^[A-Fa-f0-9]+$")
    platform: Literal["ios"] = "ios"


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(
    body: DeviceIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    locale: Locale = Depends(current_locale),
) -> None:
    """The app says hello at every launch; the same phone stays one row."""
    await tokens_repo.register(
        session, user.id, token=body.token, platform=body.platform, locale=locale
    )


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def forget_device(
    token: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Signing out, or turning the notification off. Silent if already gone."""
    await tokens_repo.forget(session, token, user_id=user.id)
