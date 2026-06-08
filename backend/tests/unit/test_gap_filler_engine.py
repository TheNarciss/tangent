"""Unit tests for app.finance.gap_filler.engine."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.finance.gap_filler.engine import (
    apply_gap_fill_response,
    build_gap_fill_requests,
)
from app.finance.gap_filler.registry import Gap, GappableField


@pytest.fixture
def fake_field() -> GappableField:
    """A minimal GappableField suitable for unit testing."""
    return GappableField(
        name="testfield",
        table="account_holdings",
        value_column="ter",
        source_column="ter_source",
        resolved_at_column="ter_resolved_at",
        build_prompt=lambda row: f"prompt for {row.id}",
        response_schema={"type": "object"},
        tool_name="resolve_testfield",
        validate_value=lambda v: isinstance(v, float) and 0 <= v <= 0.02,
    )


# ── build_gap_fill_requests ────────────────────────────────────────────────


def test_build_gap_fill_requests_creates_one_per_gap(fake_field: GappableField) -> None:
    """One Gap → one Anthropic Request with the right custom_id."""
    row1 = MagicMock()
    row1.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    row2 = MagicMock()
    row2.id = uuid.UUID("87654321-4321-8765-4321-876543218765")

    gaps = [
        Gap(field=fake_field, row_id=row1.id, context={"row": row1}),
        Gap(field=fake_field, row_id=row2.id, context={"row": row2}),
    ]
    requests = build_gap_fill_requests(gaps)
    assert len(requests) == 2
    assert requests[0]["custom_id"] == f"gap_testfield_{row1.id}"
    assert requests[1]["custom_id"] == f"gap_testfield_{row2.id}"


def test_build_gap_fill_requests_empty_input_yields_empty(fake_field: GappableField) -> None:
    """No gaps → no requests."""
    assert build_gap_fill_requests([]) == []


def test_build_gap_fill_requests_forces_tool_use(fake_field: GappableField) -> None:
    """tool_choice must force the field's specific tool name."""
    row = MagicMock()
    row.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    gaps = [Gap(field=fake_field, row_id=row.id, context={"row": row})]
    requests = build_gap_fill_requests(gaps)
    tool_choice = requests[0]["params"]["tool_choice"]
    assert tool_choice == {"type": "tool", "name": "resolve_testfield"}


# ── apply_gap_fill_response ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_response_rejects_unknown_field() -> None:
    """Custom_id referencing an unregistered field → False, no DB write."""
    session = MagicMock()
    message = MagicMock()
    row_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    custom_id = f"gap_unregisteredfield_{row_id}"
    result = await apply_gap_fill_response(session, custom_id, message)
    assert result is False


@pytest.mark.asyncio
async def test_apply_response_rejects_malformed_custom_id() -> None:
    """Custom_id that does not match the regex → False."""
    session = MagicMock()
    message = MagicMock()
    result = await apply_gap_fill_response(session, "not_a_gap_id", message)
    assert result is False
