"""Unit tests for the LLM Anthropic client wrapper.

This test file also doubles as the **canonical mock pattern** for every
future LLM-touching PR (PR4 in particular). When you need to mock the
Anthropic SDK in a new test, copy the pattern from
`test_anthropic_sdk_is_mockable` below — it shows exactly how the
streaming and non-streaming response shapes are intercepted.

No real network calls are made by these tests. The `ANTHROPIC_API_KEY`
env var is set to a fake value via `monkeypatch` so the singleton init
path is exercised, but the underlying `anthropic.AsyncAnthropic` is
patched at the class level.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import anthropic_client


@pytest.fixture(autouse=True)
def reset_client_singleton():
    """Reset the cached `AsyncAnthropic` instance between tests.

    Without this, the first test that initializes the client poisons the
    cache for the next test (especially the one that asserts on missing
    env var). Cf `anthropic_client.reset_client_for_testing()`.
    """
    anthropic_client.reset_client_for_testing()
    yield
    anthropic_client.reset_client_for_testing()


# ── get_client(): env var handling ─────────────────────────────────────────


def test_get_client_raises_runtime_error_when_key_missing(monkeypatch):
    """Without ANTHROPIC_API_KEY, get_client() must fail with a clear message
    pointing operators to backend/.env (operability concern)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        anthropic_client.get_client()


def test_get_client_raises_when_key_is_empty_string(monkeypatch):
    """A literally empty key (common with `.env` typos) is treated as missing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        anthropic_client.get_client()


def test_get_client_raises_when_key_is_whitespace_only(monkeypatch):
    """Whitespace-only key is treated as missing (trim before validation)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   \t\n  ")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        anthropic_client.get_client()


def test_get_client_returns_singleton(monkeypatch):
    """Repeated get_client() calls return the same instance (cache works)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key-12345")
    c1 = anthropic_client.get_client()
    c2 = anthropic_client.get_client()
    assert c1 is c2, "get_client() should cache the instance"


def test_constants_exposed():
    """Public constants are accessible without instantiating the client."""
    assert anthropic_client.MODEL == "claude-sonnet-4-6"
    assert anthropic_client.MAX_TOKENS == 4096
    assert anthropic_client.WEB_SEARCH_MAX_USES == 5


# ── Mock pattern reference (copy-paste for future PRs) ─────────────────────


async def test_anthropic_sdk_is_mockable_for_non_streaming(monkeypatch):
    """Canonical mock pattern for a non-streaming response.

    Reuse this shape in PR4 when testing `review_generator.generate()`
    against a fixed response payload (no real API call).
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key-12345")

    # Build a minimal Message response that mimics the SDK shape
    fake_text_block = MagicMock()
    fake_text_block.text = "Hello from mocked Claude"
    fake_text_block.type = "text"

    fake_response = MagicMock()
    fake_response.content = [fake_text_block]
    fake_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    fake_response.stop_reason = "end_turn"

    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.messages.create = AsyncMock(return_value=fake_response)
        mock_cls.return_value = mock_instance

        client = anthropic_client.get_client()
        response = await client.messages.create(
            model=anthropic_client.MODEL,
            max_tokens=anthropic_client.MAX_TOKENS,
            messages=[{"role": "user", "content": "test"}],
        )

    # Verify we got the mocked response, not a real API call
    assert response.content[0].text == "Hello from mocked Claude"
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 50

    # Verify the SDK was called with our constants
    mock_instance.messages.create.assert_awaited_once()
    call_kwargs = mock_instance.messages.create.await_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4096


async def test_anthropic_sdk_is_mockable_for_streaming(monkeypatch):
    """Canonical mock pattern for a streaming response.

    Reuse this shape in PR4 when testing the SSE pipeline:
    `messages.stream()` returns an async context manager whose
    `text_stream` yields incremental chunks.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-test-key-12345")

    # Build the streaming context manager mock
    async def fake_text_stream():
        for chunk in ["Hello ", "from ", "streaming ", "Claude"]:
            yield chunk

    fake_stream_ctx = MagicMock()
    fake_stream_ctx.text_stream = fake_text_stream()
    fake_stream_ctx.get_final_message = AsyncMock(
        return_value=MagicMock(
            usage=MagicMock(input_tokens=120, output_tokens=80),
            stop_reason="end_turn",
        )
    )
    fake_stream_ctx.__aenter__ = AsyncMock(return_value=fake_stream_ctx)
    fake_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.llm.anthropic_client.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.messages.stream = MagicMock(return_value=fake_stream_ctx)
        mock_cls.return_value = mock_instance

        client = anthropic_client.get_client()
        collected: list[str] = []
        async with client.messages.stream(
            model=anthropic_client.MODEL,
            max_tokens=anthropic_client.MAX_TOKENS,
            messages=[{"role": "user", "content": "test"}],
        ) as stream:
            async for chunk in stream.text_stream:
                collected.append(chunk)
            final = await stream.get_final_message()

    assert "".join(collected) == "Hello from streaming Claude"
    assert final.usage.input_tokens == 120
    assert final.usage.output_tokens == 80
