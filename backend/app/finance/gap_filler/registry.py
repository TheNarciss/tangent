"""Universal Gap-Filler — registry pattern.

Each gappable field is declared as a `GappableField` instance and registered
via `register_field()`. The engine in `engine.py` iterates over all registered
fields to detect gaps in the DB and dispatch the LLM batch.

A `GappableField` knows:
- which table/column it lives on
- how to build an LLM prompt for a given DB row (the "context")
- what JSON schema the LLM response must follow (tool_use)
- how to validate the resolved value

Constraints on field names (enforced by register_field):
- ASCII letters/digits only (no underscores) — the Anthropic batch custom_id
  format `gap_<field>_<row_uuid>` requires unambiguous parsing.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as _field
from typing import Any

# Pattern for a valid field name: alphanumeric only, no underscores
_VALID_FIELD_NAME = re.compile(r"^[a-z][a-z0-9]*$")


@dataclass(frozen=True)
class GappableField:
    """Declarative spec of a DB field that can be filled by the LLM gap-filler.

    Attributes:
        name: unique short identifier (lowercase, no underscores). Used in the
            Anthropic batch `custom_id` so must remain stable.
        table: DB table name (e.g. "account_holdings").
        value_column: the actual data column (e.g. "ter").
        source_column: the *_source tracking column (e.g. "ter_source").
        resolved_at_column: the *_resolved_at tracking column.
        source_url_column: optional column storing the document the LLM cited.
            When set, `source_url` from the tool call is persisted there.
        build_prompt: fn(orm_row) -> str, returns the user-prompt content
            describing the row's context (ticker, label, etc.).
        response_schema: Anthropic tool_use input_schema (dict).
        tool_name: name of the tool the LLM must call (visible in the prompt).
        validate_value: fn(value) -> bool, sanity check on the LLM's value.
        coerce_value: fn(value) -> Any, transform LLM output to DB-storable
            (e.g. round to 6 decimals for TER).
    """

    name: str
    table: str
    value_column: str
    source_column: str
    resolved_at_column: str
    build_prompt: Callable[[Any], str]
    response_schema: dict[str, Any]
    tool_name: str
    validate_value: Callable[[Any], bool]
    coerce_value: Callable[[Any], Any] = _field(default=lambda v: v)
    source_url_column: str | None = None
    requires_web_search: bool = False
    """If True, the LLM request includes the web_search tool. Costs ~$0.01
    extra per gap (web_search is not batch-discounted) but enables sourcing
    from official documents (KID, factsheets, regulator websites)."""


@dataclass(frozen=True)
class Gap:
    """An instance of a detected gap waiting to be filled."""

    field: GappableField
    row_id: Any  # UUID, but kept Any to avoid heavy import here
    context: dict[str, Any] = _field(default_factory=dict)
    """Optional extra context (e.g. for transactions, the description + amount)."""


# ── Module-level registry ──────────────────────────────────────────────────
_REGISTRY: dict[str, GappableField] = {}


def register_field(gf: GappableField) -> GappableField:
    """Register a GappableField in the global registry. Returns the field.

    Raises ValueError if name is invalid or already registered.
    """
    if not _VALID_FIELD_NAME.match(gf.name):
        raise ValueError(
            f"Invalid field name {gf.name!r}: must match [a-z][a-z0-9]* "
            "(no underscores, used in Anthropic batch custom_id)"
        )
    if gf.name in _REGISTRY:
        raise ValueError(f"Field {gf.name!r} already registered")
    _REGISTRY[gf.name] = gf
    return gf


def get_field(name: str) -> GappableField | None:
    """Return the registered field, or None if not found."""
    return _REGISTRY.get(name)


def get_all_fields() -> list[GappableField]:
    """Snapshot of all registered fields (order-independent)."""
    return list(_REGISTRY.values())


def clear_registry_for_testing() -> None:
    """Empty the registry. **Tests only.**"""
    _REGISTRY.clear()


# ── Anthropic batch custom_id encoding ─────────────────────────────────────
# Lives here (not in engine.py) to keep the public API of `gap_filler`
# importable without pulling in the anthropic SDK.

_CUSTOM_ID_RE = re.compile(
    r"^gap_(?P<field>[a-z][a-z0-9]*)_"
    r"(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)


def encode_custom_id(field_name: str, row_id: uuid.UUID) -> str:
    """Build a `custom_id` for an Anthropic batch request."""
    return f"gap_{field_name}_{row_id}"


def decode_custom_id(custom_id: str) -> tuple[str, uuid.UUID] | None:
    """Decode a custom_id back to `(field_name, row_id)`, or None if malformed."""
    m = _CUSTOM_ID_RE.match(custom_id)
    if not m:
        return None
    return m.group("field"), uuid.UUID(m.group("uuid"))
