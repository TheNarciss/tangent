"""Admin routes — restricted to superusers."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, fastapi_users
from ..db import get_session
from ..db.models import ReviewBatch
from ..llm import batch_poller, batch_submitter
from ..repositories import review_batches as batches_repo

router = APIRouter(prefix="/admin", tags=["admin"])

_superuser = fastapi_users.current_user(active=True, superuser=True)


@router.get("/users")
async def list_users(
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
):
    """List all user accounts. Reserved for superusers.

    Important: returns id + email + flags but NEVER the hashed_password.
    """
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


# ---------------------------------------------------------------------------
# Batches (nightly review pipeline — PR #B)
# ---------------------------------------------------------------------------


def _batch_to_dict(b: ReviewBatch) -> dict:
    """Serialize a ReviewBatch row for admin endpoints."""
    return {
        "id": str(b.id),
        "anthropic_batch_id": b.anthropic_batch_id,
        "status": b.status,
        "submitted_at": b.submitted_at.isoformat() if b.submitted_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "n_requests": b.n_requests,
        "n_succeeded": b.n_succeeded,
        "n_errored": b.n_errored,
        "n_expired": b.n_expired,
        "estimated_cost_usd": b.estimated_cost_usd,
        "actual_cost_usd": b.actual_cost_usd,
    }


@router.get("/batches")
async def list_batches(
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
) -> list[dict]:
    """List recent review batches (newest first). Superuser-only."""
    batches = await batches_repo.list_recent(session, limit=limit)
    return [_batch_to_dict(b) for b in batches]


@router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: uuid.UUID,
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get a single batch by id."""
    batch = await batches_repo.get_by_id(session, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_dict(batch)


@router.post("/batches/submit")
async def submit_batch(
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Manually trigger a nightly batch submit.

    Useful for testing PR #B end-to-end before the APScheduler (PR #C)
    takes over. Returns the created ReviewBatch or {status: skipped}
    if no work was done.
    """
    batch = await batch_submitter.submit_nightly_batch(session)
    if batch is None:
        return {"status": "skipped", "reason": "no opt-in users or cost cap reached"}
    return _batch_to_dict(batch)


@router.post("/batches/poll-all")
async def poll_all_batches(
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Poll all in-progress batches. Returns how many were finalized."""
    n_finalized = await batch_poller.poll_pending_batches(session)
    return {"finalized": n_finalized}
