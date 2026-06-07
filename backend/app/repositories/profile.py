"""Profile repository — profil financier d'un user."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Profile

logger = logging.getLogger(__name__)


async def get_or_create(session: AsyncSession, user_id: uuid.UUID) -> Profile:
    """Retourne le profil de l'user. Crée un profil vide si absent."""
    stmt = select(Profile).where(Profile.user_id == user_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user_id, ceilings_used={})
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


async def update(session: AsyncSession, user_id: uuid.UUID, updates: dict) -> Profile:
    """Met à jour les champs fournis. Les autres restent inchangés.

    `updates` est un dict des champs à modifier. Les clés inconnues sont ignorées.
    """
    profile = await get_or_create(session, user_id)
    allowed_fields = {
        "birth_date",
        "fiscal_shares",
        "rfr_n_minus_2",
        "target_annual_return",
        "max_annual_volatility",
        "horizon_years",
        "default_broker",
        "ceilings_used",
        "auto_review_enabled",
    }
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return profile


async def list_opted_in_users(session: AsyncSession) -> list[Profile]:
    """Return all profiles with auto_review_enabled=True.

    Used by the nightly batch submitter (PR #B) to know which users
    should be included in tonight's batch.
    """
    stmt = select(Profile).where(Profile.auto_review_enabled.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())
