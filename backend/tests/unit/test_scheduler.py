"""Unit tests for the APScheduler setup (job registration only).

The scheduler instance is not .start()ed here — we only verify that
setup_scheduler() correctly registers the expected jobs with the
expected timezone. Calling .shutdown() on a non-started scheduler
raises SchedulerNotRunningError, so we let the test scheduler get
garbage-collected without explicit cleanup.
"""

from zoneinfo import ZoneInfo

from app.scheduler import setup_scheduler


def test_setup_scheduler_registers_two_jobs() -> None:
    """The factory must register the two expected jobs."""
    scheduler = setup_scheduler()
    job_ids = {j.id for j in scheduler.get_jobs()}
    assert "submit_nightly_batch" in job_ids
    assert "poll_pending_batches" in job_ids
    assert len(job_ids) == 2


def test_setup_scheduler_uses_paris_timezone() -> None:
    """All jobs must be configured with Europe/Paris timezone."""
    paris = ZoneInfo("Europe/Paris")
    scheduler = setup_scheduler()
    for job in scheduler.get_jobs():
        assert job.trigger.timezone == paris, (
            f"Job {job.id} has timezone {job.trigger.timezone}, expected Paris"
        )
