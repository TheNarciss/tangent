"""Integration tests for /reviews/* routes (PR5)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import delete

from app.db.engine import async_session_factory
from app.db.models import LLMDailyCost, PortfolioReview
from app.llm import anthropic_client, cost_tracker
from app.repositories import reviews as reviews_repo


async def _register(client, email, password):
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), resp.text
    return uuid.UUID(resp.json()["id"])


async def _login(client, email, password):
    resp = await client.post(
        "/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture(autouse=True)
def reset_anthropic_singleton(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-key-for-tests")
    anthropic_client.reset_client_for_testing()
    yield
    anthropic_client.reset_client_for_testing()


@pytest.fixture(autouse=True)
async def _cleanup_far_future(request):
    yield
    if request.node.get_closest_marker("integration") is None:
        return
    async with async_session_factory() as session:
        cutoff = date.today() + timedelta(days=365 * 5)
        await session.execute(delete(LLMDailyCost).where(LLMDailyCost.cost_date >= cutoff))
        await session.execute(delete(PortfolioReview).where(PortfolioReview.review_date >= cutoff))
        await session.commit()


@pytest.mark.integration
async def test_generate_review_requires_auth(client):
    resp = await client.post("/reviews/generate")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_today_requires_auth(client):
    resp = await client.get("/reviews/today")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_list_requires_auth(client):
    resp = await client.get("/reviews")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_generate_returns_503_when_cap_reached(client, monkeypatch):
    """When the daily cost cap is reached, POST /reviews/generate returns 503
    BEFORE starting the SSE stream (kill-switch enforced at the edge)."""
    run_id = uuid.uuid4().hex[:8]
    email = f"cap-{run_id}@test.com"
    await _register(client, email, "TestPwd123!")
    await _login(client, email, "TestPwd123!")

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    async with async_session_factory() as session:
        await cost_tracker.record_cost(session, cost_tracker.DAILY_CAP_USD + 0.01, test_day)

    resp = await client.post("/reviews/generate")
    assert resp.status_code == 503
    assert "budget" in resp.json()["detail"].lower()


@pytest.mark.integration
async def test_generate_returns_409_when_already_done_today(client, monkeypatch):
    """A second generate for the same day returns 409."""
    run_id = uuid.uuid4().hex[:8]
    email = f"dup-{run_id}@test.com"
    user_id = await _register(client, email, "TestPwd123!")
    await _login(client, email, "TestPwd123!")

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    async with async_session_factory() as session:
        await reviews_repo.create_review(
            session,
            user_id=user_id,
            review_date=test_day,
            content="already there",
            model_used="claude-sonnet-4-6",
            input_tokens=0,
            output_tokens=0,
            web_searches_count=0,
            cost_usd=0.0,
            sources=[],
            wealth_snapshot={},
        )

    resp = await client.post("/reviews/generate")
    assert resp.status_code == 409


@pytest.mark.integration
async def test_today_returns_null_when_no_review(client):
    run_id = uuid.uuid4().hex[:8]
    email = f"today1-{run_id}@test.com"
    await _register(client, email, "TestPwd123!")
    await _login(client, email, "TestPwd123!")

    resp = await client.get("/reviews/today")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.integration
async def test_today_returns_existing_review(client, monkeypatch):
    run_id = uuid.uuid4().hex[:8]
    email = f"today2-{run_id}@test.com"
    user_id = await _register(client, email, "TestPwd123!")
    await _login(client, email, "TestPwd123!")

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    async with async_session_factory() as session:
        await reviews_repo.create_review(
            session,
            user_id=user_id,
            review_date=test_day,
            content="# Vue d'ensemble\n\nHello",
            model_used="claude-sonnet-4-6",
            input_tokens=100,
            output_tokens=50,
            web_searches_count=2,
            cost_usd=0.0,
            sources=[{"url": "https://x.com", "title": "X"}],
            wealth_snapshot={},
        )

    resp = await client.get("/reviews/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["content"].startswith("# Vue d'ensemble")
    assert body["web_searches_count"] == 2


@pytest.mark.integration
async def test_list_returns_only_user_own_reviews(client, monkeypatch):
    """Multi-tenant: user A never sees user B\'s reviews via GET /reviews."""
    run_id = uuid.uuid4().hex[:8]
    email_a = f"isoA-{run_id}@test.com"
    email_b = f"isoB-{run_id}@test.com"
    user_a = await _register(client, email_a, "TestPwd123!")
    user_b = await _register(client, email_b, "TestPwd123!")

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    async with async_session_factory() as session:
        for uid in (user_a, user_b):
            await reviews_repo.create_review(
                session,
                user_id=uid,
                review_date=test_day,
                content=f"review for {uid}",
                model_used="claude-sonnet-4-6",
                input_tokens=0,
                output_tokens=0,
                web_searches_count=0,
                cost_usd=0.0,
                sources=[],
                wealth_snapshot={},
            )

    await _login(client, email_a, "TestPwd123!")
    resp = await client.get("/reviews")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert str(user_a) in body[0]["content"]
