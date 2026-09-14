"""APScheduler setup for the nightly review pipeline (PR #C).

Single-instance design: the backend runs in one container, no leader
election needed. If we scale horizontally later, switch to a Redis/PG
jobstore with locking.

Jobs registered:
- compute_picks         : daily at 06:30 Europe/Paris, and 20 s after boot when
                          the stored list is stale -> finance.picks
- sync_enablebanking    : daily at 07:15 Europe/Paris, every live consent
                          -> enablebanking.aggregator (PSD2 allows four a day)
- record_portfolio_snapshots : daily at 02:00 Europe/Paris -> snapshot_job
- submit_nightly_batch  : daily at 03:00 Europe/Paris -> batch_submitter
- poll_pending_batches  : every 15 min from 03:00 to 09:45 Paris
                          -> batch_poller (idempotent, skips finished)

Both jobs open their own AsyncSession (no FastAPI Depends in APScheduler).
Exceptions are caught and logged so the scheduler keeps running for the
next tick.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from .aggregator.persist import persist_sync_result
from .db import async_session_factory
from .db.models import EnableBankingSession
from .enablebanking import aggregator as enablebanking_agg
from .finance import picks
from .llm import batch_poller, batch_submitter
from .snapshot_job import record_all_users

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


async def _job_record_snapshots() -> None:
    """Store the day's portfolio value for every user, at 02:00 Paris.

    Runs before the nightly briefing so the day's figures are available to
    it. Failures on one user never stop the others.
    """
    async with async_session_factory() as session:
        try:
            await record_all_users(session)
        except Exception:
            logger.exception("Scheduler: portfolio snapshots failed")


async def _job_compute_picks() -> None:
    """Recompute « La liste de l'année » unless the stored copy is fresh.

    Minutes of Yahoo for ~300 tickers: runs in a thread so the loop keeps
    serving. Failures are logged; the route keeps serving the last list.
    """
    try:
        await asyncio.to_thread(picks.refresh_if_stale)
    except Exception:
        logger.exception("Scheduler: picks recompute failed")


async def _job_sync_enablebanking() -> None:
    """Read the rolling month of every live Enable Banking consent, one user at a time."""
    async with async_session_factory() as session:
        try:
            rows = (await session.execute(select(EnableBankingSession))).scalars().all()
            now = datetime.now(UTC)
            since = date.today() - timedelta(days=31)
            for row in rows:
                if enablebanking_agg.is_expired(row, now):
                    continue
                result = await enablebanking_agg.sync_row(session, row, since=since)
                if result.success:
                    await persist_sync_result(session, row.user_id, result)
                await session.commit()
        except Exception:
            logger.exception("Scheduler: Enable Banking sync failed")


def setup_scheduler() -> AsyncIOScheduler:
    """Build the scheduler with the nightly jobs (not started yet).

    The caller (FastAPI lifespan) is responsible for .start() and
    .shutdown(). The scheduler uses Europe/Paris time for all crons.
    """
    scheduler = AsyncIOScheduler(timezone=_PARIS)

    scheduler.add_job(
        _job_compute_picks,
        CronTrigger(hour=6, minute=30, timezone=_PARIS),
        id="compute_picks",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _job_compute_picks,
        DateTrigger(run_date=datetime.now(_PARIS) + timedelta(seconds=20)),
        id="compute_picks_at_boot",
        replace_existing=True,
    )

    scheduler.add_job(
        _job_sync_enablebanking,
        CronTrigger(hour=7, minute=15, timezone=_PARIS),
        id="sync_enablebanking",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _job_record_snapshots,
        CronTrigger(hour=2, minute=0, timezone=_PARIS),
        id="record_portfolio_snapshots",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

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
        "Scheduler configured: %d jobs registered (compute_picks, sync_enablebanking, "
        "record_portfolio_snapshots, submit_nightly_batch, poll_pending_batches)",
        len(scheduler.get_jobs()),
    )
    return scheduler
