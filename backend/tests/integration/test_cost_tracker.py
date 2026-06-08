"""Tests for app.llm.cost_tracker.

Splits cleanly into:

- Pure-math tests for `compute_cost_usd` — no DB, no fixtures
- Integration tests for the DB-backed budget guard — require Postgres,
  marked `@pytest.mark.integration`, depend on the session-scoped `client`
  fixture to guarantee migrations have run before they execute.

Cross-test isolation: every integration test runs on a date 10 years in
the future (`isolated_test_date`), and a conditional autouse fixture wipes
that future date range after each integration test. This way:

- Production rows (today, recent days) are never touched
- Concurrent CI runs of this test file serialize via the UNIQUE constraint
  on `cost_date` if they ever overlap on the same nanosecond
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import delete, select

from app.db.engine import async_session_factory
from app.db.models import LLMDailyCost
from app.llm import cost_tracker

# -- Pure math --------------------------------------------------------------


def test_compute_cost_zero_everything_is_zero():
    assert cost_tracker.compute_cost_usd(0, 0, 0) == 0.0


def test_compute_cost_input_only_matches_published_rate():
    """1M input tokens × $3/M == $3.00"""
    assert cost_tracker.compute_cost_usd(1_000_000, 0, 0) == pytest.approx(3.0)


def test_compute_cost_output_only_matches_published_rate():
    """1M output tokens × $15/M == $15.00"""
    assert cost_tracker.compute_cost_usd(0, 1_000_000, 0) == pytest.approx(15.0)


def test_compute_cost_web_search_only():
    """5 web searches × $0.01 == $0.05"""
    assert cost_tracker.compute_cost_usd(0, 0, 5) == pytest.approx(0.05)


def test_compute_cost_typical_review():
    """Typical review: 6k in + 3k out + 5 searches.

    Hand calc:
      6_000  / 1M * $3  = $0.018
      3_000  / 1M * $15 = $0.045
      5      * $0.01    = $0.050
      ---------------------------
      total              = $0.113
    """
    cost = cost_tracker.compute_cost_usd(6_000, 3_000, 5)
    assert cost == pytest.approx(0.113, abs=1e-4)


def test_today_paris_returns_a_date_not_datetime():
    """Sanity: we return a date for partitioning, not a datetime."""
    result = cost_tracker.today_paris()
    assert isinstance(result, date)


# -- Integration: DB-backed budget guard ------------------------------------


@pytest.fixture
def isolated_test_date():
    """Date 10y in the future — can't collide with real data."""
    return date.today() + timedelta(days=365 * 10)


@pytest.fixture(autouse=True)
async def _cleanup_future_dates(request):
    """After every integration test, wipe far-future rows.

    Conditional on the `integration` marker so pure-math tests don't pay
    the cost of a (possibly failing) DB connection.
    """
    yield
    if request.node.get_closest_marker("integration") is None:
        return
    async with async_session_factory() as session:
        cutoff = date.today() + timedelta(days=365 * 5)
        await session.execute(delete(LLMDailyCost).where(LLMDailyCost.cost_date >= cutoff))
        await session.commit()


@pytest.mark.integration
async def test_is_under_cap_when_no_row_yet(client, isolated_test_date):
    """Empty table -> always under cap."""
    async with async_session_factory() as session:
        assert await cost_tracker.is_under_cap(session, isolated_test_date) is True


@pytest.mark.integration
async def test_get_today_cost_returns_zero_when_no_row(client, isolated_test_date):
    """Empty table -> exactly 0.0 (not None, not error)."""
    async with async_session_factory() as session:
        cost = await cost_tracker.get_today_cost_usd(session, isolated_test_date)
        assert cost == 0.0


@pytest.mark.integration
async def test_record_cost_creates_row_on_first_call(client, isolated_test_date):
    """First call on a fresh date INSERTs."""
    async with async_session_factory() as session:
        new_total = await cost_tracker.record_cost(session, 0.10, isolated_test_date)
        assert new_total == pytest.approx(0.10)


@pytest.mark.integration
async def test_record_cost_increments_existing_row(client, isolated_test_date):
    """Second call on same date UPDATEs and accumulates."""
    async with async_session_factory() as session:
        await cost_tracker.record_cost(session, 0.10, isolated_test_date)
        await cost_tracker.record_cost(session, 0.05, isolated_test_date)
        total = await cost_tracker.get_today_cost_usd(session, isolated_test_date)
        assert total == pytest.approx(0.15)

        # reviews_count tracks the number of UPSERTs, not the cost dollars
        stmt = select(LLMDailyCost.reviews_count).where(
            LLMDailyCost.cost_date == isolated_test_date
        )
        count = (await session.execute(stmt)).scalar()
        assert count == 2


@pytest.mark.integration
async def test_is_under_cap_blocks_when_above_threshold(client, isolated_test_date):
    """Once cumulative >= DAILY_CAP_USD, the guard slams shut."""
    async with async_session_factory() as session:
        await cost_tracker.record_cost(
            session, cost_tracker.DAILY_CAP_USD + 0.01, isolated_test_date
        )
        assert await cost_tracker.is_under_cap(session, isolated_test_date) is False


@pytest.mark.integration
async def test_is_under_cap_still_open_just_below_threshold(client, isolated_test_date):
    """Just below the cap is still open for one more generation."""
    async with async_session_factory() as session:
        await cost_tracker.record_cost(
            session, cost_tracker.DAILY_CAP_USD - 0.01, isolated_test_date
        )
        assert await cost_tracker.is_under_cap(session, isolated_test_date) is True
