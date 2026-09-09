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

The custom_id format is `gap_<field>_<row_uuid>` for unambiguous parsing
(field names cannot contain underscores, enforced by registry).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from anthropic.types.beta.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.beta.messages.batch_create_params import Request
from sqlalchemy import func, select, update
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

        stmt = select(model).where(
            value_col.is_(None),
            source_col.is_distinct_from("user"),
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


def build_gap_fill_requests(gaps: Sequence[Gap]) -> list[Request]:
    """Convert each Gap into an Anthropic Batch Request with tool_use forcing.

    The LLM is forced to call the field's declared tool, returning structured
    JSON validated by the field's response_schema. This eliminates free-form
    hallucinations.

    Args:
        gaps: list of detected gaps.

    Returns:
        Anthropic batch Request list, ready for `batches.create()`.
    """
    requests: list[Request] = []

    for gap in gaps:
        gf = gap.field
        row = gap.context["row"]
        user_prompt = gf.build_prompt(row)

        resolve_tool: dict[str, Any] = {
            "name": gf.tool_name,
            "description": gf.response_schema.get(
                "description", f"Resolve {gf.name} for this row."
            ),
            "input_schema": gf.response_schema,
        }

        # Conditionally include web_search for fields that need sourcing
        # from official documents (e.g. ETF KIDs, factsheets).
        tools_list: list[dict[str, Any]] = [resolve_tool]
        if gf.requires_web_search:
            tools_list.append(
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 2,
                }
            )

        params = MessageCreateParamsNonStreaming(
            model=anthropic_client.MODEL,
            max_tokens=1024,
            system=(
                "Tu es un assistant qui résout des valeurs manquantes dans "
                "une base de données financière. Tu réponds UNIQUEMENT en "
                f"appelant l'outil {gf.tool_name!r}. Si tu n'as pas de "
                "donnée fiable, utilise la valeur null appropriée plutôt "
                "que d'inventer."
            ),
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools_list,  # type: ignore[typeddict-item]
            tool_choice={"type": "any"}
            if gf.requires_web_search
            else {"type": "tool", "name": gf.tool_name},
        )

        requests.append(
            Request(
                custom_id=encode_custom_id(gf.name, gap.row_id),
                params=params,
            )
        )

    return requests


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
