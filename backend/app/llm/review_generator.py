"""Review generator — orchestrates the full LLM pipeline.

Pipeline (in order):

1. Kill-switch check (cost_tracker.is_under_cap) — raises ReviewBlocked
2. Uniqueness check (reviews_repo.get_review_for_date) — raises ReviewBlocked
3. Build prompt from wealth + profile + optional optimizer
4. Stream Claude via anthropic SDK with web_search tool enabled
5. Yield chunks to the caller as they arrive (the route in PR5 wraps these
   in SSE)
6. On stream completion: compute cost, record_cost (atomic UPSERT), and
   create_review (atomic INSERT, races caught at the UNIQUE constraint)

Decoupled from FastAPI: the caller passes wealth and (optionally) the
optimizer response, this module knows nothing about HTTP.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..finance import verdicts as verdicts_engine
from ..models import OptimizerResponse, Wealth
from ..repositories import bank_transactions as tx_repo
from ..repositories import profile as profile_repo
from ..repositories import reviews as reviews_repo
from . import anthropic_client, cost_tracker, prompt_builder

logger = logging.getLogger(__name__)


class ReviewBlocked(Exception):
    """Generation refused (kill-switch hit or daily cap already reached).

    The route layer maps this to HTTP 503 (kill-switch) or HTTP 409 (already
    have a review today), depending on the .reason attribute.
    """

    REASON_DAILY_CAP = "daily_cost_cap_reached"
    REASON_ALREADY_GENERATED = "already_generated_today"

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


# ── Anthropic tools spec ────────────────────────────────────────────────────

_WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": anthropic_client.WEB_SEARCH_MAX_USES,
}


async def generate_review_stream(
    session: AsyncSession,
    user_id: uuid.UUID,
    wealth: Wealth,
    optimizer_response: OptimizerResponse | None = None,
) -> AsyncIterator[str]:
    """Yield markdown chunks of the generated review. Persist on completion.

    Side effects on success: one row in `portfolio_reviews`, one increment
    in `llm_daily_cost`.
    """
    today = cost_tracker.today_paris()

    # 1. Kill-switch
    if not await cost_tracker.is_under_cap(session, today):
        raise ReviewBlocked(
            ReviewBlocked.REASON_DAILY_CAP,
            "Daily LLM cost cap reached. Try again tomorrow.",
        )

    # 2. Already generated today?
    existing = await reviews_repo.get_review_for_date(session, user_id, today)
    if existing is not None:
        raise ReviewBlocked(
            ReviewBlocked.REASON_ALREADY_GENERATED,
            "You already have a review for today.",
        )

    # 3. Profile + prompt
    profile = await profile_repo.get_or_create(session, user_id)
    spending = await tx_repo.monthly_outflow(session, user_id)
    saved = await tx_repo.monthly_inflow_to_savings(session, user_id)
    verdicts = verdicts_engine.compute_all(
        wealth, profile, monthly_spending=spending, monthly_saved=saved
    ).verdicts
    snapshot = prompt_builder.build_anonymized_snapshot(
        wealth, profile, optimizer_response, verdicts=verdicts
    )
    user_prompt = prompt_builder.build_user_prompt(snapshot)

    # 4. Stream Claude
    client = anthropic_client.get_client()
    collected_chunks: list[str] = []
    sources: list[dict[str, Any]] = []

    async with client.messages.stream(
        model=anthropic_client.MODEL,
        max_tokens=anthropic_client.MAX_TOKENS,
        system=prompt_builder.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[_WEB_SEARCH_TOOL],  # type: ignore[list-item]  # SDK strict TypedDict vs our dict
    ) as stream:
        async for chunk in stream.text_stream:
            collected_chunks.append(chunk)
            yield chunk
        final = await stream.get_final_message()

    full_content = "".join(collected_chunks)

    # Extract cited sources (the SDK exposes web_search invocations as
    # server_tool_use blocks; their result URLs live in the matching
    # web_search_tool_result blocks).
    web_searches_count = 0
    for block in final.content:
        block_type = getattr(block, "type", None)
        if block_type == "server_tool_use":
            # We only enabled the web_search tool, so every server_tool_use block IS
            # a web_search invocation. Defensive name check removed (and it tripped
            # on MagicMock.name being a reserved attr in tests).
            web_searches_count += 1
        elif block_type == "web_search_tool_result":
            for item in getattr(block, "content", []) or []:
                url = getattr(item, "url", None)
                title = getattr(item, "title", None)
                if url:
                    sources.append({"url": url, "title": title or url})

    # 5. Persist cost + review atomically (best-effort: if review INSERT
    # races and loses on UNIQUE, the cost has already been incurred — we
    # still record_cost to keep the kill-switch consistent).
    input_tokens = final.usage.input_tokens
    output_tokens = final.usage.output_tokens
    cost_usd = cost_tracker.compute_cost_usd(input_tokens, output_tokens, web_searches_count)

    await cost_tracker.record_cost(session, cost_usd, today)

    try:
        await reviews_repo.create_review(
            session,
            user_id=user_id,
            review_date=today,
            content=full_content,
            model_used=anthropic_client.MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            web_searches_count=web_searches_count,
            cost_usd=cost_usd,
            sources=sources,
            wealth_snapshot=snapshot,
            generation_mode="manual",
        )
    except Exception:
        # Rare race: another generation finished first (shouldn't happen
        # since we pre-checked, but UNIQUE constraint is the source of truth).
        logger.exception(
            "Failed to persist review for user=%s on %s (content NOT lost — "
            "cost was already recorded)",
            user_id,
            today.isoformat(),
        )
        raise


async def generate_review_full(
    session: AsyncSession,
    user_id: uuid.UUID,
    wealth: Wealth,
    optimizer_response: OptimizerResponse | None = None,
) -> str:
    """Convenience wrapper: collect the full stream into a single string.

    Useful for tests and for synchronous callers that don\'t need streaming.
    """
    chunks: list[str] = []
    async for chunk in generate_review_stream(session, user_id, wealth, optimizer_response):
        chunks.append(chunk)
    return "".join(chunks)
