"""Unit tests for batch_poller helpers (pure functions)."""

from types import SimpleNamespace

import pytest

from app.llm import batch_poller, cost_tracker


def test_compute_actual_cost_zero() -> None:
    """Zero tokens + zero searches → zero cost."""
    assert batch_poller._compute_actual_cost(0, 0, 0) == 0.0


def test_compute_actual_cost_input_output_discounted() -> None:
    """Input + output must be discounted 50% in batch."""
    full = cost_tracker.compute_cost_usd(10_000, 5_000, 0)
    discounted = batch_poller._compute_actual_cost(10_000, 5_000, 0)
    assert discounted == pytest.approx(full * 0.5)


def test_compute_actual_cost_web_search_not_discounted() -> None:
    """Web search invocations are NOT discounted in batch (Anthropic rule)."""
    full_search = cost_tracker.compute_cost_usd(0, 0, 4)
    batch_search = batch_poller._compute_actual_cost(0, 0, 4)
    assert batch_search == pytest.approx(full_search)


def test_compute_actual_cost_combined() -> None:
    """Combined: in/out × 0.5 + search × 1.0."""
    api_full = cost_tracker.compute_cost_usd(10_000, 5_000, 0)
    search_full = cost_tracker.compute_cost_usd(0, 0, 3)
    expected = api_full * 0.5 + search_full
    actual = batch_poller._compute_actual_cost(10_000, 5_000, 3)
    assert actual == pytest.approx(expected)


def test_parse_message_text_only() -> None:
    """A message with just text blocks → content + zero sources/web_searches."""
    message = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Hello "),
            SimpleNamespace(type="text", text="world"),
        ],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )
    content, sources, in_tok, out_tok, ws = batch_poller._parse_message(message)
    assert content == "Hello world"
    assert sources == []
    assert in_tok == 100
    assert out_tok == 50
    assert ws == 0


def test_parse_message_with_sources_and_searches() -> None:
    """Message with web_search_tool_result blocks → sources extracted, count incremented."""
    message = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Result: "),
            SimpleNamespace(type="server_tool_use"),
            SimpleNamespace(
                type="web_search_tool_result",
                content=[
                    SimpleNamespace(url="https://example.com", title="Example"),
                    SimpleNamespace(url="https://x.com", title=None),
                ],
            ),
            SimpleNamespace(type="text", text="see sources"),
        ],
        usage=SimpleNamespace(input_tokens=200, output_tokens=80),
    )
    content, sources, _in_tok, _out_tok, ws = batch_poller._parse_message(message)
    assert content == "Result: see sources"
    assert sources == [
        {"url": "https://example.com", "title": "Example"},
        {"url": "https://x.com", "title": "https://x.com"},
    ]
    assert ws == 1


def test_parse_message_url_none_skipped() -> None:
    """web_search_tool_result entries without url are skipped."""
    message = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="web_search_tool_result",
                content=[
                    SimpleNamespace(url=None, title="No URL"),
                    SimpleNamespace(url="https://valid.com", title="Valid"),
                ],
            ),
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    _, sources, _, _, _ = batch_poller._parse_message(message)
    assert sources == [{"url": "https://valid.com", "title": "Valid"}]
