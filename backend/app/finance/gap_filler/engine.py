"""Universal Gap-Filler — engine.

Three public coroutines orchestrate the whole gap-fill flow:

1. `collect_gaps(session)` walks every registered GappableField and queries
   the DB for rows where the value is NULL and source is NOT "user" (to
   avoid overwriting user overrides on re-runs).

2. `build_gap_fill_requests(gaps)` converts each Gap into an Anthropic batch
   Request with tool_use forcing a structured response.

3. `apply_gap_fill_response(session, custom_id, message)` decodes the
   custom_id back into (field, row_id), validates the LLM response, and
   writes the resolved value with source="llm" + resolved_at=now().

The custom_id format is `gap_<field>_<uuid>` for unambiguous parsing (field
names cannot contain underscores, enforced by registry). For a batched field
the uuid names the group, and the rows come back inside the answer, each
with its own id.

`*_resolved_at` is the last time the LLM looked at the row, set when the
request is submitted and again when the answer is written. A row it looked
at recently is not a gap, whatever it answered: a request still in flight
is not sent twice, and a row it could not fill is not asked again every
night — only after `RETRY_AFTER_DAYS`.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from anthropic.types.beta.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.beta.messages.batch_create_params import Request
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import AccountHolding, BankTransaction
from ...llm import anthropic_client
from .registry import (
    Gap,
    GappableField,
    decode_custom_id,
    encode_custom_id,
    get_all_fields,
    get_field,
)

logger = logging.getLogger(__name__)


# Map table name → ORM model. Centralized here so fields don't need to import models.
_TABLE_TO_MODEL: dict[str, Any] = {
    "account_holdings": AccountHolding,
    "bank_transactions": BankTransaction,
}


# encode_custom_id and decode_custom_id live in registry.py (no anthropic dep)

# A row the LLM already looked at is asked again only after this long: the
# answer may still be on its way, or there was nothing to find.
RETRY_AFTER_DAYS = 30

# ── collect_gaps ────────────────────────────────────────────────────────────


async def collect_gaps(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    fields: Sequence[GappableField] | None = None,
) -> list[Gap]:
    """Walk every registered GappableField and collect rows that need filling.

    A "gap" is a row where `<value_column>` IS NULL **and** `<source_column>`
    is NOT 'user'. The 'user' check protects manual overrides: even if the
    user set value=NULL on purpose, we won't fill it.

    Args:
        session: async SQLAlchemy session.
        user_id: if provided, restrict to this user's rows (multi-tenant).
        fields: if provided, restrict to these fields. Default: all registered.

    Returns:
        List of Gap instances ready for `build_gap_fill_requests()`.
    """
    fields = list(fields) if fields is not None else get_all_fields()
    gaps: list[Gap] = []

    for gf in fields:
        model = _TABLE_TO_MODEL.get(gf.table)
        if model is None:
            logger.warning(
                "GappableField %s: unknown table %s, skipping",
                gf.name,
                gf.table,
            )
            continue

        value_col = getattr(model, gf.value_column)
        source_col = getattr(model, gf.source_column)
        looked_at = getattr(model, gf.resolved_at_column)
        retry_before = datetime.now(UTC) - timedelta(days=RETRY_AFTER_DAYS)

        stmt = select(model).where(
            value_col.is_(None),
            source_col.is_distinct_from("user"),
            or_(looked_at.is_(None), looked_at < retry_before),
        )
        if user_id is not None and hasattr(model, "user_id"):
            stmt = stmt.where(model.user_id == user_id)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            gaps.append(Gap(field=gf, row_id=row.id, context={"row": row}))

        logger.info(
            "collect_gaps: field=%s, %d gaps found%s",
            gf.name,
            len(rows),
            f" for user {user_id}" if user_id else "",
        )

    return gaps


# ── build_gap_fill_requests ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PlannedRequest:
    """One Anthropic request and the gaps it carries: one, or a group of them."""

    request: Request
    gaps: tuple[Gap, ...]


def build_gap_fill_requests(gaps: Sequence[Gap]) -> list[Request]:
    """The requests alone; `plan_gap_fill` keeps which gaps each one carries."""
    return [planned.request for planned in plan_gap_fill(gaps)]


def plan_gap_fill(gaps: Sequence[Gap]) -> list[PlannedRequest]:
    """Convert the gaps into Anthropic Batch Requests with tool_use forcing.

    The LLM is forced to call the field's declared tool, returning structured
    JSON validated by the field's response_schema. This eliminates free-form
    hallucinations. A batched field takes `batch_size` rows per request.
    """
    out: list[PlannedRequest] = []
    by_field: dict[str, list[Gap]] = {}
    for gap in gaps:
        by_field.setdefault(gap.field.name, []).append(gap)

    for field_gaps in by_field.values():
        gf = field_gaps[0].field
        size = max(1, gf.batch_size) if gf.build_batch_prompt else 1
        for start in range(0, len(field_gaps), size):
            group = tuple(field_gaps[start : start + size])
            if size > 1 and gf.build_batch_prompt is not None:
                prompt = gf.build_batch_prompt([g.context["row"] for g in group])
                custom_id = encode_custom_id(gf.name, uuid.uuid4())
            else:
                prompt = gf.build_prompt(group[0].context["row"])
                custom_id = encode_custom_id(gf.name, group[0].row_id)
            out.append(PlannedRequest(_request(gf, prompt, custom_id), group))
    return out


def _request(gf: GappableField, user_prompt: str, custom_id: str) -> Request:

    resolve_tool: dict[str, Any] = {
        "name": gf.tool_name,
        "description": gf.response_schema.get("description", f"Resolve {gf.name} for this row."),
        "input_schema": gf.response_schema,
    }

    # A field read from a document on the web (TER, ISIN) goes to the model
    # that searches and reasons a little; a closed classification (category)
    # to the small one, forced onto its tool. Forced tool use and thinking do
    # not go together: the sourcing model is asked, not forced.
    sourcing = gf.requires_web_search
    tools_list: list[dict[str, Any]] = [resolve_tool]
    if sourcing:
        tools_list.append(anthropic_client.web_search_tool(max_uses=2))

    system = (
        "Tu es un assistant qui résout des valeurs manquantes dans "
        "une base de données financière. Tu réponds UNIQUEMENT en "
        f"appelant l'outil {gf.tool_name!r}. Si tu n'as pas de "
        "donnée fiable, utilise la valeur null appropriée plutôt "
        "que d'inventer."
    )
    if sourcing:
        params = MessageCreateParamsNonStreaming(
            model=anthropic_client.SOURCING_MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            output_config={"effort": anthropic_client.SOURCING_EFFORT},  # type: ignore[typeddict-item]
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools_list,  # type: ignore[typeddict-item]
            tool_choice={"type": "auto"},
        )
    else:
        params = MessageCreateParamsNonStreaming(
            model=anthropic_client.CATEGORY_MODEL,
            max_tokens=4096 if gf.batch_size > 1 else 1024,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools_list,  # type: ignore[typeddict-item]
            tool_choice={"type": "tool", "name": gf.tool_name},
        )

    return Request(custom_id=custom_id, params=params)


async def mark_submitted(session: AsyncSession, gaps: Sequence[Gap]) -> None:
    """Stamp the rows just sent: the LLM is looking at them, do not ask again."""
    now = datetime.now(UTC)
    by_field: dict[str, list[Any]] = {}
    for gap in gaps:
        by_field.setdefault(gap.field.name, []).append(gap.row_id)
    for name, ids in by_field.items():
        gf = get_field(name)
        if gf is None:
            continue
        model = _TABLE_TO_MODEL[gf.table]
        await session.execute(
            update(model).where(model.id.in_(ids)).values({gf.resolved_at_column: now})
        )


# ── apply_gap_fill_response ─────────────────────────────────────────────────


async def apply_gap_fill_response(
    session: AsyncSession,
    custom_id: str,
    message: Any,
) -> bool:
    """Parse a successful Anthropic message and write the resolved value.

    The message must contain a tool_use block matching the field's tool_name.
    The value is extracted, validated, coerced, and persisted with
    source='llm' + resolved_at=now().

    Returns True iff a value was written (False if the LLM returned null,
    the response was malformed, or validation failed).
    """
    decoded = decode_custom_id(custom_id)
    if decoded is None:
        logger.warning("apply_gap_fill_response: bad custom_id %r", custom_id)
        return False

    field_name, row_id = decoded
    gf = get_field(field_name)
    if gf is None:
        logger.warning("apply_gap_fill_response: unknown field %r", field_name)
        return False

    # Extract the tool_use block from the message content
    tool_input: dict[str, Any] | None = None
    for block in message.content:
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == gf.tool_name
        ):
            tool_input = block.input
            break

    if tool_input is None:
        logger.warning(
            "apply_gap_fill_response: no tool_use block for field=%s custom_id=%s",
            field_name,
            custom_id,
        )
        return False

    if gf.batch_size > 1:
        return await _apply_batched(session, gf, tool_input)

    # The LLM's value lives under the schema's key — assume it's the field name itself
    # (this is the convention: schema has a top-level property matching gf.name)
    raw_value = tool_input.get(gf.name)

    if raw_value is None:
        logger.info(
            "apply_gap_fill_response: LLM returned null for field=%s row=%s (honestly unknown)",
            field_name,
            row_id,
        )
        return False

    if not gf.validate_value(raw_value):
        logger.warning(
            "apply_gap_fill_response: invalid value for field=%s row=%s: %r",
            field_name,
            row_id,
            raw_value,
        )
        return False

    coerced = gf.coerce_value(raw_value)

    # Write to DB
    model = _TABLE_TO_MODEL[gf.table]
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        gf.value_column: coerced,
        gf.source_column: "llm",
        gf.resolved_at_column: now,
    }
    # The prompt asks the LLM to cite the document it read. Keeping the citation
    # is what makes the figure checkable later.
    if gf.source_url_column:
        cited = tool_input.get("source_url")
        values[gf.source_url_column] = str(cited)[:500] if isinstance(cited, str) else None
    stmt = update(model).where(model.id == row_id).values(**values)
    await session.execute(stmt)
    logger.info(
        "apply_gap_fill_response: wrote field=%s row=%s value=%s",
        field_name,
        row_id,
        coerced,
    )
    return True


def batched_values(gf: GappableField, tool_input: dict[str, Any]) -> dict[Any, list[uuid.UUID]]:
    """Value → row ids, from a batched answer. Pure: bad ids and bad values are dropped."""
    out: dict[Any, list[uuid.UUID]] = {}
    items = tool_input.get("items")
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            row_id = uuid.UUID(str(item.get("id")))
        except ValueError:
            continue
        raw = item.get(gf.name)
        if raw is None or not gf.validate_value(raw):
            continue
        out.setdefault(gf.coerce_value(raw), []).append(row_id)
    return out


async def _apply_batched(
    session: AsyncSession, gf: GappableField, tool_input: dict[str, Any]
) -> bool:
    """Write a batched answer: one update per value, only on rows still empty.

    An id the model made up, or a row the user decided meanwhile, matches
    nothing: the WHERE clause is the guard.
    """
    model = _TABLE_TO_MODEL[gf.table]
    value_col = getattr(model, gf.value_column)
    source_col = getattr(model, gf.source_column)
    now = datetime.now(UTC)
    written = 0
    for value, ids in batched_values(gf, tool_input).items():
        result = await session.execute(
            update(model)
            .where(model.id.in_(ids), value_col.is_(None), source_col.is_distinct_from("user"))
            .values({gf.value_column: value, gf.source_column: "llm", gf.resolved_at_column: now})
        )
        written += int(getattr(result, "rowcount", 0) or 0)
    logger.info(
        "apply_gap_fill_response: field=%s, %d rows written from one answer", gf.name, written
    )
    return written > 0


# ── get_source_audit ────────────────────────────────────────────────────────


async def get_source_audit(session: AsyncSession) -> dict[str, dict[str, int]]:
    """Audit gap-fill state: counts per (table.field, source).

    For each registered field, returns a dict mapping source name
    ('api', 'llm', 'user', or 'null' for NULL) to row count.

    Used by GET /api/admin/data-sources to monitor coverage.
    """
    audit: dict[str, dict[str, int]] = {}
    for gf in get_all_fields():
        model = _TABLE_TO_MODEL.get(gf.table)
        if model is None:
            continue
        source_col = getattr(model, gf.source_column)

        stmt = select(source_col, func.count().label("n")).group_by(source_col)
        rows = (await session.execute(stmt)).all()
        key = f"{gf.table}.{gf.value_column}"
        audit[key] = {(row[0] if row[0] is not None else "null"): int(row.n) for row in rows}
    return audit
