"""Integration tests for app.llm.review_generator.

Mocks the Anthropic SDK (no real API calls) while exercising the real
DB-backed cost tracker, reviews repo, and kill-switch logic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete

from app.db.engine import async_session_factory
from app.db.models import LLMDailyCost, PortfolioReview
from app.llm import anthropic_client, cost_tracker, review_generator
from app.models import Wealth


async def _register_and_get_user_id(client, email: str, password: str) -> uuid.UUID:
    resp = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), resp.text
    return uuid.UUID(resp.json()["id"])


@pytest.fixture(autouse=True)
def reset_anthropic_singleton(monkeypatch):
    """Each test resets the client cache + sets a fake key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-key-for-tests")
    anthropic_client.reset_client_for_testing()
    yield
    anthropic_client.reset_client_for_testing()


@pytest.fixture
async def _cleanup_far_future_rows():
    """Wipe llm_daily_cost + reviews older than 5y in the future after each test."""
    yield
    async with async_session_factory() as session:
        cutoff = date.today() + timedelta(days=365 * 5)
        await session.execute(delete(LLMDailyCost).where(LLMDailyCost.cost_date >= cutoff))
        await session.execute(delete(PortfolioReview).where(PortfolioReview.review_date >= cutoff))
        await session.commit()


def _empty_wealth(user_id: uuid.UUID) -> Wealth:
    return Wealth(
        user_id=user_id,
        snapshot_at=datetime(2026, 6, 2, tzinfo=UTC),
    )


def _mocked_stream_context(
    text_chunks: list[str],
    input_tokens: int = 6000,
    output_tokens: int = 2500,
    web_searches: int = 3,
):
    """Build a mock that quacks like client.messages.stream() return value."""

    async def fake_text_stream():
        for c in text_chunks:
            yield c

    # Server-tool-use blocks for web_search counting
    tool_use_blocks = [
        SimpleNamespace(type="server_tool_use", name="web_search") for _ in range(web_searches)
    ]
    text_block = SimpleNamespace(type="text")

    final = MagicMock()
    final.content = [*tool_use_blocks, text_block]
    final.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)

    ctx = MagicMock()
    ctx.text_stream = fake_text_stream()
    ctx.get_final_message = AsyncMock(return_value=final)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@pytest.mark.integration
async def test_generate_review_yields_chunks_and_persists(
    client, _cleanup_far_future_rows, monkeypatch
):
    """Happy path: chunks arrive, then a row is persisted with computed cost."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"gen-{run_id}@test.com", "TestPwd123!")
    wealth = _empty_wealth(user_id)

    # Pin "today" so the test does not race with real production cost rows
    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    chunks = ["Hello ", "from ", "mocked ", "Claude"]
    stream_ctx = _mocked_stream_context(chunks)

    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        instance = MagicMock()
        instance.messages.stream = MagicMock(return_value=stream_ctx)
        mock_cls.return_value = instance

        async with async_session_factory() as session:
            collected = []
            async for chunk in review_generator.generate_review_stream(session, user_id, wealth):
                collected.append(chunk)

    assert "".join(collected) == "Hello from mocked Claude"

    # Verify the row was persisted with the expected metadata
    async with async_session_factory() as session:
        from app.repositories import reviews as reviews_repo

        row = await reviews_repo.get_review_for_date(session, user_id, test_day)
        assert row is not None
        assert row.content == "Hello from mocked Claude"
        assert row.input_tokens == 6000
        assert row.output_tokens == 2500
        assert row.web_searches_count == 3
        # 6000/1M*3 + 2500/1M*15 + 3*0.01 = 0.018 + 0.0375 + 0.03 = 0.0855
        assert row.cost_usd == pytest.approx(0.0855, abs=1e-4)


@pytest.mark.integration
async def test_generate_review_blocked_when_cap_reached(
    client, _cleanup_far_future_rows, monkeypatch
):
    """If is_under_cap() is False, ReviewBlocked is raised BEFORE any SDK call."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"cap-{run_id}@test.com", "TestPwd123!")
    wealth = _empty_wealth(user_id)

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    # Push cumulative spend over the cap
    async with async_session_factory() as session:
        await cost_tracker.record_cost(session, cost_tracker.DAILY_CAP_USD + 0.01, test_day)

    # SDK must NOT be called when cap is hit
    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        async with async_session_factory() as session:
            with pytest.raises(review_generator.ReviewBlocked) as exc_info:
                async for _ in review_generator.generate_review_stream(session, user_id, wealth):
                    pass

    assert exc_info.value.reason == review_generator.ReviewBlocked.REASON_DAILY_CAP
    mock_cls.assert_not_called()


@pytest.mark.integration
async def test_generate_review_blocked_when_already_done_today(
    client, _cleanup_far_future_rows, monkeypatch
):
    """Second generate_review for (user, today) raises ReviewBlocked, no SDK call."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"dup-{run_id}@test.com", "TestPwd123!")
    wealth = _empty_wealth(user_id)

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    # Insert a pre-existing review for today
    from app.repositories import reviews as reviews_repo

    async with async_session_factory() as session:
        await reviews_repo.create_review(
            session,
            user_id=user_id,
            review_date=test_day,
            content="pre-existing",
            model_used="claude-sonnet-4-6",
            input_tokens=0,
            output_tokens=0,
            web_searches_count=0,
            cost_usd=0.0,
            sources=[],
            wealth_snapshot={},
        )

    # SDK must NOT be called
    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        async with async_session_factory() as session:
            with pytest.raises(review_generator.ReviewBlocked) as exc_info:
                async for _ in review_generator.generate_review_stream(session, user_id, wealth):
                    pass

    assert exc_info.value.reason == review_generator.ReviewBlocked.REASON_ALREADY_GENERATED
    mock_cls.assert_not_called()


@pytest.mark.integration
async def test_generate_review_extracts_sources_from_web_search_results(
    client, _cleanup_far_future_rows, monkeypatch
):
    """URLs from web_search_tool_result blocks are persisted in `sources`."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"src-{run_id}@test.com", "TestPwd123!")
    wealth = _empty_wealth(user_id)

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    # Build a stream that emits a web_search_tool_result block with 2 URLs
    async def fake_text_stream():
        yield "Some review content"

    item1 = SimpleNamespace(url="https://service-public.fr/lep", title="LEP")
    item2 = SimpleNamespace(url="https://lemonde.fr/eco", title="Macro EU")
    result_block = SimpleNamespace(type="web_search_tool_result", content=[item1, item2])
    tool_use_block = SimpleNamespace(type="server_tool_use", name="web_search")

    final = MagicMock()
    final.content = [tool_use_block, result_block]
    final.usage = MagicMock(input_tokens=100, output_tokens=50)

    ctx = MagicMock()
    ctx.text_stream = fake_text_stream()
    ctx.get_final_message = AsyncMock(return_value=final)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        instance = MagicMock()
        instance.messages.stream = MagicMock(return_value=ctx)
        mock_cls.return_value = instance

        async with async_session_factory() as session:
            async for _ in review_generator.generate_review_stream(session, user_id, wealth):
                pass

    async with async_session_factory() as session:
        from app.repositories import reviews as reviews_repo

        row = await reviews_repo.get_review_for_date(session, user_id, test_day)
        assert row is not None
        urls = {s["url"] for s in row.sources}
        assert urls == {"https://service-public.fr/lep", "https://lemonde.fr/eco"}


@pytest.mark.integration
async def test_generate_review_full_returns_concatenated_string(
    client, _cleanup_far_future_rows, monkeypatch
):
    """The convenience wrapper collects all chunks into a single string."""
    run_id = uuid.uuid4().hex[:8]
    user_id = await _register_and_get_user_id(client, f"full-{run_id}@test.com", "TestPwd123!")
    wealth = _empty_wealth(user_id)

    test_day = date.today() + timedelta(days=365 * 10)
    monkeypatch.setattr(cost_tracker, "today_paris", lambda: test_day)

    stream_ctx = _mocked_stream_context(["foo ", "bar ", "baz"])

    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        instance = MagicMock()
        instance.messages.stream = MagicMock(return_value=stream_ctx)
        mock_cls.return_value = instance

        async with async_session_factory() as session:
            result = await review_generator.generate_review_full(session, user_id, wealth)

    assert result == "foo bar baz"
