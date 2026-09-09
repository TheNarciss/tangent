"""PortfolioSnapshot repository — one row per user per day, idempotent.

The snapshot series is the app's only real history of the investable
pocket: Powens exposes no transaction for investment wrappers, so a
contribution can only be seen as a change in the quantities held.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PortfolioSnapshot

logger = logging.getLogger(__name__)


async def list_snapshots(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    since: date | None = None,
) -> list[PortfolioSnapshot]:
    """The user's snapshots, oldest first."""
    stmt = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id)
        .order_by(PortfolioSnapshot.snapshot_date)
    )
    if since is not None:
        stmt = stmt.where(PortfolioSnapshot.snapshot_date >= since)
    return list((await session.execute(stmt)).scalars().all())


async def latest_snapshot(session: AsyncSession, user_id: uuid.UUID) -> PortfolioSnapshot | None:
    stmt = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def net_flow_between(
    previous: dict[str, float],
    current: dict[str, float],
    prices: dict[str, float],
) -> float:
    """Money paid in between two snapshots, priced at the later day's prices.

    A line whose quantity grew was bought; one that shrank was sold. Selling
    A to buy B nets out, so what is left is the money that entered or left
    the pocket. Lines without a price contribute nothing rather than a wrong
    amount.
    """
    flow = 0.0
    for ticker in set(previous) | set(current):
        delta = float(current.get(ticker, 0.0)) - float(previous.get(ticker, 0.0))
        price = prices.get(ticker)
        if delta and price:
            flow += delta * price
    return flow


async def record_snapshot(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    snapshot_date: date,
    total_value: float,
    quantities: dict[str, float],
    net_flow: float,
) -> None:
    """Insert today's snapshot, or refresh it if the day already has one.

    Does NOT commit — the caller owns the transaction.
    """
    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            snapshot_date=snapshot_date,
            total_value=total_value,
            quantities=quantities,
            net_flow=net_flow,
            created_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            constraint="uq_snapshot_user_date",
            set_={
                "total_value": total_value,
                "quantities": quantities,
                "net_flow": net_flow,
            },
        )
    )
    await session.execute(stmt)
