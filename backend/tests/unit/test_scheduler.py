"""Unit tests for the APScheduler setup (job registration only)."""

from zoneinfo import ZoneInfo

from app.scheduler import setup_scheduler


def test_setup_scheduler_registers_two_jobs() -> None:
    """The factory must register the two expected jobs."""
    scheduler = setup_scheduler()
    try:
        job_ids = {j.id for j in scheduler.get_jobs()}
        assert "submit_nightly_batch" in job_ids
        assert "poll_pending_batches" in job_ids
        assert len(job_ids) == 2
    finally:
        scheduler.shutdown(wait=False)


def test_setup_scheduler_uses_paris_timezone() -> None:
    """All jobs must be configured with Europe/Paris timezone."""
    paris = ZoneInfo("Europe/Paris")
    scheduler = setup_scheduler()
    try:
        for job in scheduler.get_jobs():
            assert job.trigger.timezone == paris, (
                f"Job {job.id} has timezone {job.trigger.timezone}, expected Paris"
            )
    finally:
        scheduler.shutdown(wait=False)
