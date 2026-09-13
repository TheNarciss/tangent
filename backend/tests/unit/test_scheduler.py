"""Unit tests for the APScheduler setup (job registration only).

The scheduler instance is not .start()ed here — we only verify that
setup_scheduler() correctly registers the expected jobs with the
expected timezone. Calling .shutdown() on a non-started scheduler
raises SchedulerNotRunningError, so we let the test scheduler get
garbage-collected without explicit cleanup.
"""

from zoneinfo import ZoneInfo

from app.scheduler import setup_scheduler


def test_setup_scheduler_registers_the_expected_jobs() -> None:
    """The factory must register the nightly jobs and the picks recompute."""
    scheduler = setup_scheduler()
    job_ids = {j.id for j in scheduler.get_jobs()}
    assert job_ids == {
        "compute_picks",
        "compute_picks_at_boot",
        "record_portfolio_snapshots",
        "submit_nightly_batch",
        "poll_pending_batches",
    }


def test_setup_scheduler_uses_paris_timezone() -> None:
    """All jobs must be configured with Europe/Paris timezone."""
    paris = ZoneInfo("Europe/Paris")
    scheduler = setup_scheduler()
    for job in scheduler.get_jobs():
        tz = getattr(job.trigger, "timezone", None) or job.trigger.run_date.tzinfo
        assert tz == paris, f"Job {job.id} has timezone {tz}, expected Paris"
