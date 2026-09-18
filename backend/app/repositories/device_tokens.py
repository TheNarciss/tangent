"""Device tokens — which phones to tell, and forgetting the ones Apple retired.

A phone re-registers at every launch: the same token comes back and only its
`last_seen_at` moves. A token that moved to another account follows the person
who is signed in now, because Apple addresses the app on the phone, not the
account.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DeviceToken

logger = logging.getLogger(__name__)


async def register(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    token: str,
    platform: str = "ios",
    locale: str | None = None,
) -> None:
    """Remember this phone for this person. Commits."""
    now = datetime.now(UTC)
    stmt = (
        pg_insert(DeviceToken)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            token=token,
            platform=platform,
            locale=locale,
            created_at=now,
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=[DeviceToken.token],
            set_={"user_id": user_id, "locale": locale, "last_seen_at": now},
        )
    )
    await session.execute(stmt)
    await session.commit()


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[DeviceToken]:
    rows = await session.execute(select(DeviceToken).where(DeviceToken.user_id == user_id))
    return list(rows.scalars().all())


async def forget(session: AsyncSession, token: str, *, user_id: uuid.UUID | None = None) -> None:
    """Drop one token: signing out, or Apple saying it leads nowhere. Commits."""
    stmt = delete(DeviceToken).where(DeviceToken.token == token)
    if user_id is not None:
        stmt = stmt.where(DeviceToken.user_id == user_id)
    await session.execute(stmt)
    await session.commit()
