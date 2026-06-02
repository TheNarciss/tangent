"""Integration tests for the reviews repository.

Validates multi-tenancy isolation (ADR-002) and the UNIQUE(user_id, review_date)
constraint that enforces 1 review per day per user (ADR-015).
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.db.engine import async_session_factory
from app.db.models import PortfolioReview
from app.repositories import reviews as reviews_repo


async def _register_and_get_user_id(client, email: str, password: str) -> uuid.UUID:
    """Register a user via API and return their id."""
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), resp.text
    return uuid.UUID(resp.json()["id"])


async def _cleanup_user(user_id: uuid.UUID) -> None:
    """Wipe reviews for a test user (CASCADE doesn\'t touch us if we delete first)."""
    async with async_session_factory() as session:
        await session.execute(delete(PortfolioReview).where(PortfolioReview.user_id == user_id))
        await session.commit()


def _sample_kwargs(user_id: uuid.UUID, day: date) -> dict:
    return dict(
        user_id=user_id,
        review_date=day,
        content="# Vue d'ensemble\n\nLorem ipsum.",
        model_used="claude-sonnet-4-6",
        input_tokens=6000,
        output_tokens=2500,
        web_searches_count=3,
        cost_usd=0.085,
        sources=[{"url": "https://service-public.fr", "title": "LEP"}],
        wealth_snapshot={"net_worth_eur": 50000.0, "test": True},
    )


@pytest.mark.integration
async def test_create_review_persists_all_fields(client):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"rev-{run_id}@test.com", "TestPwd123!")
    try:
        today = date.today() + timedelta(days=365 * 10)
        async with async_session_factory() as session:
            row = await reviews_repo.create_review(session, **_sample_kwargs(user_id, today))
            assert row.id is not None
            assert row.user_id == user_id
            assert row.review_date == today
            assert row.input_tokens == 6000
            assert row.cost_usd == pytest.approx(0.085)
            assert row.sources == [{"url": "https://service-public.fr", "title": "LEP"}]
            assert row.wealth_snapshot["net_worth_eur"] == 50000.0
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_unique_constraint_blocks_second_insert_same_day(client):
    """A second create_review for (user, same date) must IntegrityError."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"rev2-{run_id}@test.com", "TestPwd123!")
    try:
        today = date.today() + timedelta(days=365 * 10)
        async with async_session_factory() as session:
            await reviews_repo.create_review(session, **_sample_kwargs(user_id, today))

        async with async_session_factory() as session:
            with pytest.raises(IntegrityError):
                await reviews_repo.create_review(session, **_sample_kwargs(user_id, today))
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_two_users_can_have_reviews_same_day(client):
    """UNIQUE is per-user — User A and User B can both have a review for today."""
    run_id = uuid.uuid4().hex[:8]
    user_a = await _register_and_get_user_id(client, f"revA-{run_id}@test.com", "TestPwd123!")
    user_b = await _register_and_get_user_id(client, f"revB-{run_id}@test.com", "TestPwd123!")
    try:
        today = date.today() + timedelta(days=365 * 10)
        async with async_session_factory() as session:
            await reviews_repo.create_review(session, **_sample_kwargs(user_a, today))
            await reviews_repo.create_review(session, **_sample_kwargs(user_b, today))

            a = await reviews_repo.get_review_for_date(session, user_a, today)
            b = await reviews_repo.get_review_for_date(session, user_b, today)
            assert a is not None and b is not None
            assert a.id != b.id
    finally:
        await _cleanup_user(user_a)
        await _cleanup_user(user_b)


@pytest.mark.integration
async def test_get_review_for_date_returns_none_when_absent(client):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"rev3-{run_id}@test.com", "TestPwd123!")
    try:
        far_future = date.today() + timedelta(days=365 * 11)
        async with async_session_factory() as session:
            assert await reviews_repo.get_review_for_date(session, user_id, far_future) is None
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_list_reviews_returns_window_newest_first(client):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"rev4-{run_id}@test.com", "TestPwd123!")
    try:
        base = date.today() + timedelta(days=365 * 10)
        async with async_session_factory() as session:
            for i in range(5):
                kwargs = _sample_kwargs(user_id, base + timedelta(days=i))
                await reviews_repo.create_review(session, **kwargs)

            all_rows = await reviews_repo.list_reviews(session, user_id)
            assert len(all_rows) == 5
            dates = [r.review_date for r in all_rows]
            assert dates == sorted(dates, reverse=True), "newest first"

            window = await reviews_repo.list_reviews(
                session,
                user_id,
                from_date=base + timedelta(days=1),
                to_date=base + timedelta(days=3),
            )
            assert len(window) == 3
    finally:
        await _cleanup_user(user_id)


@pytest.mark.integration
async def test_list_reviews_isolates_users(client):
    """A list_reviews call for user A never returns user B\'s rows."""
    run_id = uuid.uuid4().hex[:8]
    user_a = await _register_and_get_user_id(client, f"isoA-{run_id}@test.com", "TestPwd123!")
    user_b = await _register_and_get_user_id(client, f"isoB-{run_id}@test.com", "TestPwd123!")
    try:
        base = date.today() + timedelta(days=365 * 10)
        async with async_session_factory() as session:
            await reviews_repo.create_review(session, **_sample_kwargs(user_a, base))
            await reviews_repo.create_review(session, **_sample_kwargs(user_b, base))

            a_reviews = await reviews_repo.list_reviews(session, user_a)
            assert len(a_reviews) == 1
            assert a_reviews[0].user_id == user_a
    finally:
        await _cleanup_user(user_a)
        await _cleanup_user(user_b)
