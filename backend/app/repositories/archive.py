"""The archive rows (ADR-034): one per user and per slot, one per slot for the market."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DataSnapshot


async def record_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    snapshot_date: date,
    slot: str,
    taken_at: datetime,
    sealed: str,
) -> None:
    """Write a user's sealed snapshot for the slot, replacing the slot's earlier row if any."""
    stmt = (
        pg_insert(DataSnapshot)
        .values(
            id=uuid.uuid4(),
            scope="user",
            user_id=user_id,
            snapshot_date=snapshot_date,
            slot=slot,
            taken_at=taken_at,
            sealed=sealed,
            payload=None,
            size_bytes=len(sealed),
        )
        .on_conflict_do_update(
            index_elements=["user_id", "snapshot_date", "slot"],
            index_where=text("user_id IS NOT NULL"),
            set_={"taken_at": taken_at, "sealed": sealed, "size_bytes": len(sealed)},
        )
    )
    await session.execute(stmt)


async def record_market(
    session: AsyncSession,
    *,
    snapshot_date: date,
    slot: str,
    taken_at: datetime,
    payload: dict[str, Any],
    size_bytes: int,
) -> None:
    """Write the market snapshot for the slot, replacing the slot's earlier row if any."""
    stmt = (
        pg_insert(DataSnapshot)
        .values(
            id=uuid.uuid4(),
            scope="market",
            user_id=None,
            snapshot_date=snapshot_date,
            slot=slot,
            taken_at=taken_at,
            payload=payload,
            sealed=None,
            size_bytes=size_bytes,
        )
        .on_conflict_do_update(
            index_elements=["scope", "snapshot_date", "slot"],
            index_where=text("user_id IS NULL"),
            set_={"taken_at": taken_at, "payload": payload, "size_bytes": size_bytes},
        )
    )
    await session.execute(stmt)


async def list_for_day(session: AsyncSession, snapshot_date: date) -> list[DataSnapshot]:
    stmt = (
        select(DataSnapshot)
        .where(DataSnapshot.snapshot_date == snapshot_date)
        .order_by(DataSnapshot.scope, DataSnapshot.slot)
    )
    return list((await session.execute(stmt)).scalars().all())
