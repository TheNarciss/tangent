"""Tests for app.llm._retry — retry_on_overload decorator + predicate."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from anthropic import APIStatusError

from app.llm._retry import is_anthropic_overloaded

# ── Predicate: is_anthropic_overloaded ─────────────────────────────────────


def _api_error(status: int) -> APIStatusError:
    """Build a fake APIStatusError with a given status code."""
    resp = Mock(status_code=status, headers={})
    return APIStatusError("test", response=resp, body=None)


def test_is_overloaded_true_for_529():
    """529 = overloaded_error → retry."""
    assert is_anthropic_overloaded(_api_error(529)) is True


def test_is_overloaded_true_for_503():
    """503 = service unavailable → retry."""
    assert is_anthropic_overloaded(_api_error(503)) is True


def test_is_overloaded_false_for_429():
    """429 = rate limit → needs Retry-After respect, NOT auto-retried."""
    assert is_anthropic_overloaded(_api_error(429)) is False


def test_is_overloaded_false_for_500():
    """500 may be deterministic, no auto-retry to avoid infinite loop."""
    assert is_anthropic_overloaded(_api_error(500)) is False


def test_is_overloaded_false_for_400():
    """4xx = client error, retry would just re-fail."""
    assert is_anthropic_overloaded(_api_error(400)) is False


def test_is_overloaded_false_for_401():
    """401 = auth, retry would re-fail."""
    assert is_anthropic_overloaded(_api_error(401)) is False


def test_is_overloaded_false_for_non_anthropic_exception():
    """Any non-APIStatusError → False (RuntimeError, ValueError, etc.)."""
    assert is_anthropic_overloaded(RuntimeError("boom")) is False
    assert is_anthropic_overloaded(ValueError("nope")) is False


# ── Decorator behavior (with mocked wait for speed) ────────────────────────


@pytest.mark.asyncio
async def test_decorator_retries_then_succeeds(monkeypatch):
    """Two 529s then a success → returns the success value, 3 calls total."""
    # Replace the wait strategy with no-wait to keep the test fast
    import tenacity

    from app.llm import _retry

    fast_retry = tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_none(),
        retry=tenacity.retry_if_exception(_retry.is_anthropic_overloaded),
        reraise=True,
    )

    call_count = 0

    @fast_retry
    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise _api_error(529)
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_decorator_gives_up_after_three_attempts():
    """Three 529s in a row → re-raises the last APIStatusError, 3 calls total."""
    import tenacity

    from app.llm import _retry

    fast_retry = tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_none(),
        retry=tenacity.retry_if_exception(_retry.is_anthropic_overloaded),
        reraise=True,
    )

    call_count = 0

    @fast_retry
    async def always_overloaded():
        nonlocal call_count
        call_count += 1
        raise _api_error(529)

    with pytest.raises(APIStatusError) as exc_info:
        await always_overloaded()

    assert exc_info.value.status_code == 529
    assert call_count == 3


@pytest.mark.asyncio
async def test_decorator_does_not_retry_on_400():
    """4xx errors are not retried (bad request is deterministic)."""
    import tenacity

    from app.llm import _retry

    fast_retry = tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_none(),
        retry=tenacity.retry_if_exception(_retry.is_anthropic_overloaded),
        reraise=True,
    )

    call_count = 0

    @fast_retry
    async def bad_request():
        nonlocal call_count
        call_count += 1
        raise _api_error(400)

    with pytest.raises(APIStatusError):
        await bad_request()

    assert call_count == 1
