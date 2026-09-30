"""Unit tests for the APScheduler setup (job registration only).

The scheduler instance is not .start()ed here — we only verify that
setup_scheduler() correctly registers the expected jobs with the
expected timezone. Calling .shutdown() on a non-started scheduler
raises SchedulerNotRunningError, so we let the test scheduler get
garbage-collected without explicit cleanup.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.scheduler import missed_tonight, setup_scheduler

PARIS = ZoneInfo("Europe/Paris")


def test_setup_scheduler_registers_the_expected_jobs() -> None:
    """The factory must register the nightly jobs and the picks recompute."""
    scheduler = setup_scheduler()
    job_ids = {j.id for j in scheduler.get_jobs()}
    assert job_ids == {
        "compute_picks",
        "compute_picks_at_boot",
        "warm_sources_at_boot",
        "sync_enablebanking",
        "record_portfolio_snapshots",
        "collect_market_leads",
        "archive_morning",
        "archive_evening",
        "submit_nightly_batch",
        "catch_up_nightly_at_boot",
        "poll_pending_batches",
    }


def test_setup_scheduler_uses_paris_timezone() -> None:
    """All jobs must be configured with Europe/Paris timezone."""
    paris = ZoneInfo("Europe/Paris")
    scheduler = setup_scheduler()
    for job in scheduler.get_jobs():
        tz = getattr(job.trigger, "timezone", None) or job.trigger.run_date.tzinfo
        assert tz == paris, f"Job {job.id} has timezone {tz}, expected Paris"


def test_a_boot_after_three_catches_up_a_night_the_cron_missed() -> None:
    """The VM rebooted at 03:00 on 2026-09-30 and the briefing never came."""
    booted = datetime(2026, 9, 30, 3, 3, tzinfo=PARIS)
    yesterday = datetime(2026, 9, 29, 1, 0, tzinfo=ZoneInfo("UTC"))

    assert missed_tonight(booted, yesterday)
    assert missed_tonight(booted, None)


def test_no_catch_up_before_three_or_once_the_batch_went() -> None:
    tonight = datetime(2026, 9, 30, 1, 0, 5, tzinfo=ZoneInfo("UTC"))  # 03:00:05 in Paris

    assert not missed_tonight(datetime(2026, 9, 30, 2, 40, tzinfo=PARIS), None)
    assert not missed_tonight(datetime(2026, 9, 30, 14, 0, tzinfo=PARIS), tonight)
