"""APScheduler setup for the nightly review pipeline (PR #C).

Single-instance design: the backend runs in one container, no leader
election needed. If we scale horizontally later, switch to a Redis/PG
jobstore with locking.

Jobs registered:
- submit_nightly_batch  : daily at 03:00 Europe/Paris -> batch_submitter
- poll_pending_batches  : every 15 min from 03:00 to 09:45 Paris
                          -> batch_poller (idempotent, skips finished)

Both jobs open their own AsyncSession (no FastAPI Depends in APScheduler).
Exceptions are caught and logged so the scheduler keeps running for the
next tick.
"""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import async_session_factory
from .llm import batch_poller, batch_submitter

logger = logging.getLogger(__name__)

_PARIS = ZoneInfo("Europe/Paris")


async def _job_submit_nightly() -> None:
    """Submit one nightly batch with all opt-in users.

    Called by the scheduler at 03:00 Paris.
    """
    logger.info("Scheduler: starting nightly batch submit")
    async with async_session_factory() as session:
        try:
            batch = await batch_submitter.submit_nightly_batch(session)
            if batch is None:
                logger.info("Scheduler: nightly batch skipped (no opt-in users or cap reached)")
            else:
                logger.info(
                    "Scheduler: nightly batch submitted id=%s n_requests=%d",
                    batch.id,
                    batch.n_requests,
                )
        except Exception:
            logger.exception("Scheduler: nightly batch submit failed")


async def _job_poll_pending() -> None:
    """Poll all in-progress batches.

    Called every 15 min from 03:00 to 09:45 Paris. Idempotent: already
    finished batches are skipped at the repo layer.
    """
    async with async_session_factory() as session:
        try:
            n_finalized = await batch_poller.poll_pending_batches(session)
            if n_finalized > 0:
                logger.info(
                    "Scheduler: %d batch(es) finalized this round",
                    n_finalized,
                )
        except Exception:
            logger.exception("Scheduler: batch polling failed")


def setup_scheduler() -> AsyncIOScheduler:
    """Build the scheduler with the 2 nightly jobs (not started yet).

    The caller (FastAPI lifespan) is responsible for .start() and
    .shutdown(). The scheduler uses Europe/Paris time for all crons.
    """
    scheduler = AsyncIOScheduler(timezone=_PARIS)

    scheduler.add_job(
        _job_submit_nightly,
        CronTrigger(hour=3, minute=0, timezone=_PARIS),
        id="submit_nightly_batch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _job_poll_pending,
        CronTrigger(hour="3-9", minute="0,15,30,45", timezone=_PARIS),
        id="poll_pending_batches",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        "Scheduler configured: %d jobs registered (submit_nightly_batch, poll_pending_batches)",
        len(scheduler.get_jobs()),
    )
    return scheduler
