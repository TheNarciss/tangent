"""ReviewBatch repository — tracks Anthropic Message Batches submissions.

Multi-tenancy note: this table is NOT user-scoped. A single batch contains
N requests across multiple users (one request per opted-in user). Per-user
enforcement happens at the portfolio_reviews level via user_id FK on each
generated review.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ReviewBatch

logger = logging.getLogger(__name__)


async def create(
    session: AsyncSession,
    *,
    anthropic_batch_id: str,
    status: str,
    n_requests: int,
    estimated_cost_usd: float | None = None,
) -> ReviewBatch:
    """Persist a new batch submission.

    Typically called right after a successful
    client.beta.messages.batches.create() with status="in_progress" and
    estimated_cost_usd from the pre-submit estimate.
    """
    row = ReviewBatch(
        anthropic_batch_id=anthropic_batch_id,
        status=status,
        n_requests=n_requests,
        estimated_cost_usd=estimated_cost_usd,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(
        "ReviewBatch persisted: anthropic_id=%s status=%s n_requests=%d est_cost=$%.4f",
        anthropic_batch_id,
        status,
        n_requests,
        estimated_cost_usd or 0.0,
    )
    return row


async def get_by_id(
    session: AsyncSession,
    batch_id: uuid.UUID,
) -> ReviewBatch | None:
    stmt = select(ReviewBatch).where(ReviewBatch.id == batch_id)
    return (await session.execute(stmt)).scalars().first()


async def get_by_anthropic_id(
    session: AsyncSession,
    anthropic_batch_id: str,
) -> ReviewBatch | None:
    stmt = select(ReviewBatch).where(ReviewBatch.anthropic_batch_id == anthropic_batch_id)
    return (await session.execute(stmt)).scalars().first()


async def list_in_progress(session: AsyncSession) -> list[ReviewBatch]:
    """All batches still being processed by Anthropic. Used by the poller."""
    stmt = select(ReviewBatch).where(ReviewBatch.status == "in_progress")
    return list((await session.execute(stmt)).scalars().all())


async def list_recent(
    session: AsyncSession,
    limit: int = 20,
) -> list[ReviewBatch]:
    """Recent batches, newest first. Used by GET /admin/batches."""
    stmt = select(ReviewBatch).order_by(ReviewBatch.submitted_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def update_completion(
    session: AsyncSession,
    batch_id: uuid.UUID,
    *,
    status: str,
    n_succeeded: int,
    n_errored: int,
    n_expired: int,
    actual_cost_usd: float,
    completed_at: datetime | None = None,
) -> ReviewBatch:
    """Mark a batch as completed (status='ended', 'canceled', 'errored', ...).

    Called by the poller once the Anthropic batch has finished processing
    and all per-request results have been persisted as portfolio_reviews.
    """
    batch = await get_by_id(session, batch_id)
    if batch is None:
        raise ValueError(f"ReviewBatch {batch_id} not found")
    batch.status = status
    batch.n_succeeded = n_succeeded
    batch.n_errored = n_errored
    batch.n_expired = n_expired
    batch.actual_cost_usd = actual_cost_usd
    batch.completed_at = completed_at or datetime.now(tz=UTC)
    await session.commit()
    await session.refresh(batch)
    logger.info(
        "ReviewBatch %s completed: status=%s succeeded=%d errored=%d expired=%d actual=$%.4f",
        batch_id,
        status,
        n_succeeded,
        n_errored,
        n_expired,
        actual_cost_usd,
    )
    return batch
