"""Gap-fill sends less: rows grouped per request, nothing sent twice, a budget at the door."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.finance.gap_filler import engine
from app.finance.gap_filler.fields.transaction_category import (
    BATCH_SIZE,
    FIELD_CATEGORY,
    build_batch_prompt_category,
)
from app.finance.gap_filler.registry import Gap, GappableField, decode_custom_id
from app.llm import batch_submitter, cost_tracker


def _row(**kw):
    base = dict(
        id=uuid.uuid4(),
        description="CARREFOUR MARKET",
        amount=-23.4,
        currency="EUR",
        transaction_date="2026-09-12",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _single_field() -> GappableField:
    return GappableField(
        name="ter",
        table="account_holdings",
        value_column="ter",
        source_column="ter_source",
        resolved_at_column="ter_resolved_at",
        build_prompt=lambda row: f"ter for {row.id}",
        response_schema={"type": "object"},
        tool_name="resolve_ter",
        validate_value=lambda v: isinstance(v, float),
        requires_web_search=True,
    )


def test_plan_groups_a_batched_field_and_keeps_single_fields_one_per_row():
    rows = [_row() for _ in range(BATCH_SIZE * 2 + 3)]
    gaps = [Gap(field=FIELD_CATEGORY, row_id=r.id, context={"row": r}) for r in rows]
    ter = _single_field()
    holding = _row()
    gaps.append(Gap(field=ter, row_id=holding.id, context={"row": holding}))

    planned = engine.plan_gap_fill(gaps)

    sizes = sorted(len(p.gaps) for p in planned)
    assert sizes == [1, 3, BATCH_SIZE, BATCH_SIZE]
    for p in planned:
        decoded = decode_custom_id(p.request["custom_id"])
        assert decoded is not None
        field, ident = decoded
        if field == "ter":
            assert ident == holding.id  # a single row keeps its own id
        else:
            assert p.request["params"]["max_tokens"] == 4096
            prompt = p.request["params"]["messages"][0]["content"]
            for g in p.gaps:
                assert str(g.row_id) in prompt
    again = engine.build_gap_fill_requests(gaps)
    assert len(again) == len(planned)
    assert [r["params"] for r in again] == [p.request["params"] for p in planned]


def test_batch_prompt_names_each_row_by_id():
    rows = [_row(description="UBER EATS"), _row(description="SNCF")]
    prompt = build_batch_prompt_category(rows)
    assert f"id={rows[0].id} | UBER EATS | -23.40 EUR" in prompt
    assert f"id={rows[1].id} | SNCF" in prompt
    assert "resolve_category une seule fois" in prompt


def test_batched_values_drop_made_up_ids_and_values_outside_the_taxonomy():
    good, other = uuid.uuid4(), uuid.uuid4()
    tool_input = {
        "items": [
            {"id": str(good), "category": "alimentation", "confidence": "high"},
            {"id": str(other), "category": "alimentation"},
            {"id": "not-a-uuid", "category": "transport"},
            {"id": str(uuid.uuid4()), "category": "licorne"},
            {"id": str(uuid.uuid4())},
            "garbage",
        ]
    }
    assert engine.batched_values(FIELD_CATEGORY, tool_input) == {"alimentation": [good, other]}
    assert engine.batched_values(FIELD_CATEGORY, {"items": "no"}) == {}


@pytest.mark.asyncio
async def test_apply_batched_answer_writes_one_update_per_value_and_reports_rows():
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(rowcount=2)
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    message = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name="resolve_category",
                input={
                    "items": [
                        {"id": str(a), "category": "restaurant"},
                        {"id": str(b), "category": "restaurant"},
                        {"id": str(c), "category": "transport"},
                    ]
                },
            )
        ]
    )
    custom_id = f"gap_category_{uuid.uuid4()}"

    with patch.object(engine, "get_field", return_value=FIELD_CATEGORY):
        ok = await engine.apply_gap_fill_response(session, custom_id, message)

    assert ok is True
    assert session.execute.await_count == 2  # restaurant, transport


def test_estimate_is_far_cheaper_per_row_for_a_batched_field():
    single = batch_submitter.estimate_cost_per_gap_fill()
    grouped = batch_submitter.estimate_cost_per_gap_fill(FIELD_CATEGORY)
    # One request costs a little more than a lone row's; per row it is an order
    # of magnitude less: no web search, one set of instructions for 25 rows.
    assert grouped < 2 * single
    assert grouped / BATCH_SIZE < single / 10


def test_within_budget_keeps_the_biggest_groups_that_fit():
    def planned(n: int, field: GappableField = FIELD_CATEGORY):
        rows = [_row() for _ in range(n)]
        return engine.PlannedRequest(
            request={"custom_id": "x", "params": {}},  # type: ignore[typeddict-item]
            gaps=tuple(Gap(field=field, row_id=r.id, context={"row": r}) for r in rows),
        )

    unit = batch_submitter.estimate_cost_per_gap_fill(FIELD_CATEGORY)
    items = [planned(3), planned(25), planned(25), planned(1, _single_field())]
    kept = batch_submitter._within_budget(items, unit * 2.5)
    assert [len(p.gaps) for p in kept] == [25, 25]
    assert batch_submitter._within_budget(items, 0.0) == []


@pytest.mark.asyncio
async def test_budget_counts_batches_still_in_flight():
    session = AsyncMock()
    pending = [SimpleNamespace(estimated_cost_usd=1.5), SimpleNamespace(estimated_cost_usd=None)]
    with (
        patch.object(cost_tracker, "get_today_cost_usd", AsyncMock(return_value=2.0)),
        patch("app.repositories.review_batches.list_in_progress", AsyncMock(return_value=pending)),
    ):
        left = await cost_tracker.budget_left_usd(session)
        assert left == pytest.approx(cost_tracker.DAILY_CAP_USD - 3.5)
        assert await cost_tracker.is_under_cap(session) is (left > 0)
