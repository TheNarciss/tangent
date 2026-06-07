"""Batch poller — checks Anthropic batches status and persists succeeded results.

Workflow (called by POST /admin/batches/{id}/poll and by the APScheduler
poll loop in PR #C):

1. List all ReviewBatch rows with status='in_progress'.
2. For each: retrieve the Anthropic batch via SDK.
3. If processing_status == 'ended':
   a. Iterate batch.results() asynchronously.
   b. For each "succeeded": parse message content (text + sources +
      web_searches), compute actual cost from usage, persist a
      portfolio_review with generation_mode='batch' + batch_id link.
   c. For each "errored"/"expired"/"canceled": log + count.
   d. Update the ReviewBatch row with final counts + actual_cost_usd.
4. Otherwise (still 'in_progress' or 'canceling'): skip until next poll.

Idempotence:
- Already-ended batches are skipped (status filter).
- UNIQUE(user_id, review_date) on portfolio_reviews catches double
  inserts (e.g. user generated manually after submit) — caught as
  IntegrityError and counted as errored.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ReviewBatch
from ..repositories import review_batches as batches_repo
from ..repositories import reviews as reviews_repo
from . import anthropic_client, cost_tracker

logger = logging.getLogger(__name__)

# Batch discount applies to input+output only, NOT to web_search invocations.
_INPUT_OUTPUT_BATCH_DISCOUNT = 0.5


def _parse_message(message: object) -> tuple[str, list[dict], int, int, int]:
    """Extract (content, sources, input_tok, output_tok, web_searches) from an Anthropic Message.

    Mirrors the streaming parser in review_generator but for the final
    Message object returned by the batch endpoint.
    """
    text_parts: list[str] = []
    sources: list[dict] = []
    web_searches_count = 0

    for block in message.content:  # type: ignore[attr-defined]
        block_type = getattr(block, "type", "")
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "server_tool_use":
            web_searches_count += 1
        elif block_type == "web_search_tool_result":
            for item in getattr(block, "content", []) or []:
                url = getattr(item, "url", None)
                title = getattr(item, "title", None)
                if url:
                    sources.append({"url": url, "title": title or url})

    full_content = "".join(text_parts)
    input_tokens = int(message.usage.input_tokens)  # type: ignore[attr-defined]
    output_tokens = int(message.usage.output_tokens)  # type: ignore[attr-defined]

    return full_content, sources, input_tokens, output_tokens, web_searches_count


def _compute_actual_cost(
    input_tokens: int,
    output_tokens: int,
    web_searches_count: int,
) -> float:
    """Actual USD cost using batch pricing.

    Batch discount applies to input+output ($/Mtok × 0.5) but NOT to
    web_search invocations (per Anthropic billing rules).
    """
    api_cost = (
        cost_tracker.compute_cost_usd(input_tokens, output_tokens, 0) * _INPUT_OUTPUT_BATCH_DISCOUNT
    )
    search_cost = cost_tracker.compute_cost_usd(0, 0, web_searches_count)
    return api_cost + search_cost


async def _process_one_batch(
    session: AsyncSession,
    batch: ReviewBatch,
) -> tuple[int, int, int, float] | None:
    """Process a single in-progress batch.

    Returns (n_succeeded, n_errored, n_expired, total_cost) on completion,
    or None if the Anthropic batch hasn't finished yet (skip + retry).
    """
    client = anthropic_client.get_client()
    anthropic_batch = await client.beta.messages.batches.retrieve(batch.anthropic_batch_id)

    processing_status = getattr(anthropic_batch, "processing_status", None)
    if processing_status != "ended":
        logger.info(
            "Batch %s (anthropic_id=%s) processing_status=%s — skipping",
            batch.id,
            batch.anthropic_batch_id,
            processing_status,
        )
        return None

    today = cost_tracker.today_paris()
    n_succeeded = 0
    n_errored = 0
    n_expired = 0
    total_cost = 0.0

    async for result in await client.beta.messages.batches.results(batch.anthropic_batch_id):
        custom_id = result.custom_id
        try:
            user_id = uuid.UUID(custom_id)
        except (ValueError, TypeError):
            logger.error(
                "Invalid custom_id=%r in batch %s — skipping",
                custom_id,
                batch.id,
            )
            n_errored += 1
            continue

        result_type = result.result.type

        if result_type == "succeeded":
            message = result.result.message  # type: ignore[union-attr]
            try:
                content, sources, in_tok, out_tok, ws_count = _parse_message(message)
                cost = _compute_actual_cost(in_tok, out_tok, ws_count)

                try:
                    await reviews_repo.create_review(
                        session,
                        user_id=user_id,
                        review_date=today,
                        content=content,
                        model_used=anthropic_client.MODEL,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        web_searches_count=ws_count,
                        cost_usd=cost,
                        sources=sources,
                        wealth_snapshot={},  # not re-stored; was used at submit time
                        generation_mode="batch",
                        batch_id=batch.id,
                    )
                except IntegrityError:
                    # Race: user already has today's review (manually generated
                    # between submit and poll).
                    await session.rollback()
                    logger.warning(
                        "User %s already has review for %s — skipping batch insert",
                        user_id,
                        today,
                    )
                    n_errored += 1
                    continue

                await cost_tracker.record_cost(session, cost, today)
                n_succeeded += 1
                total_cost += cost

            except Exception:
                logger.exception(
                    "Failed to persist succeeded result for user %s (batch %s)",
                    user_id,
                    batch.id,
                )
                n_errored += 1

        elif result_type == "errored":
            logger.warning(
                "Batch %s user %s errored: %s",
                batch.id,
                user_id,
                getattr(result.result, "error", "unknown"),
            )
            n_errored += 1
        elif result_type == "expired":
            logger.warning("Batch %s user %s expired", batch.id, user_id)
            n_expired += 1
        elif result_type == "canceled":
            logger.warning("Batch %s user %s canceled", batch.id, user_id)
            n_errored += 1
        else:  # type: ignore[unreachable]
            logger.error(  # type: ignore[unreachable]
                "Batch %s user %s unknown result type=%r",
                batch.id,
                user_id,
                result_type,
            )
            n_errored += 1

    await batches_repo.update_completion(
        session,
        batch.id,
        status="ended",
        n_succeeded=n_succeeded,
        n_errored=n_errored,
        n_expired=n_expired,
        actual_cost_usd=total_cost,
        completed_at=datetime.now(tz=UTC),
    )

    logger.info(
        "Batch %s finalized: succeeded=%d errored=%d expired=%d cost=$%.4f",
        batch.id,
        n_succeeded,
        n_errored,
        n_expired,
        total_cost,
    )

    return n_succeeded, n_errored, n_expired, total_cost


async def poll_pending_batches(session: AsyncSession) -> int:
    """Poll all in-progress batches.

    Returns the number of batches that were finalized in this pass.
    Batches still in-progress at Anthropic are left untouched.
    """
    in_progress = await batches_repo.list_in_progress(session)
    if not in_progress:
        return 0

    finalized = 0
    for batch in in_progress:
        try:
            result = await _process_one_batch(session, batch)
            if result is not None:
                finalized += 1
        except Exception:
            logger.exception(
                "Failed to process batch %s, will retry next poll",
                batch.id,
            )

    return finalized
