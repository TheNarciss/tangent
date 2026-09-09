"""Nightly snapshot of every user's investable pocket.

Powens exposes no transaction for investment wrappers, so the only way to
tell a contribution from a market move is to store, each day, the value and
the quantities behind it. This job is what gives the app a real history:
TWR, TRI and the −10 % alert all read the rows it writes.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from .aggregator.types import INVEST_ACCOUNT_TYPES
from .auth import User
from .db.models import BankAccount
from .deps import get_user_wealth
from .finance import performance
from .repositories import snapshots as snapshots_repo

logger = logging.getLogger(__name__)


async def performance_for(
    session: AsyncSession, user_id: uuid.UUID
) -> performance.Performance | None:
    """The user's real performance, read off the stored snapshots.

    None until the series holds two days: before that the account has no
    history the app is entitled to describe.
    """
    rows = await snapshots_repo.list_snapshots(session, user_id)
    return performance.compute(
        [
            performance.Point(day=r.snapshot_date, value=r.total_value, net_flow=r.net_flow)
            for r in rows
        ]
    )


async def _users_with_investments(session: AsyncSession) -> list[uuid.UUID]:
    stmt = select(distinct(BankAccount.user_id)).where(
        BankAccount.type.in_([t.value for t in INVEST_ACCOUNT_TYPES])
    )
    return list((await session.execute(stmt)).scalars().all())


async def record_for_user(
    session: AsyncSession,
    user: User,
    *,
    today: date | None = None,
) -> bool:
    """Write today's snapshot for one user. Returns False when there is nothing to record."""
    day = today or date.today()
    wealth = await get_user_wealth(user=user, session=session)
    total, quantities, prices = performance.snapshot_inputs(wealth)
    if not quantities:
        return False

    previous = await snapshots_repo.latest_snapshot(session, user.id)
    net_flow = 0.0
    if previous is not None and previous.snapshot_date < day:
        net_flow = snapshots_repo.net_flow_between(previous.quantities, quantities, prices)
    await snapshots_repo.record_snapshot(
        session,
        user.id,
        snapshot_date=day,
        total_value=total,
        quantities=quantities,
        net_flow=net_flow,
    )
    return True


async def record_all_users(session: AsyncSession, *, today: date | None = None) -> int:
    """Snapshot everyone holding an investment wrapper. Commits once at the end."""
    user_ids = await _users_with_investments(session)
    written = 0
    for user_id in user_ids:
        user = await session.get(User, user_id)
        if user is None:
            continue
        try:
            if await record_for_user(session, user, today=today):
                written += 1
        except Exception:
            logger.exception("snapshot failed for user=%s", user_id)
    if written:
        await session.commit()
    logger.info("snapshots recorded: %d/%d users", written, len(user_ids))
    return written
