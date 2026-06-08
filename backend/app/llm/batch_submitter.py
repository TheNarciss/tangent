"""Batch submitter — orchestrates nightly Anthropic Message Batches submissions.

Workflow (called by POST /admin/batches/submit and eventually by the
APScheduler cron in PR #C):

1. List all profiles with auto_review_enabled=True via profile_repo.
2. For each opted-in user: load the User row, compute their Wealth via
   get_user_wealth(user, session), build the anonymized snapshot + user
   prompt via prompt_builder.
3. Estimate total cost (with batch 50% discount applied conservatively
   to the whole; the actual cost is recorded by the poller from each
   message's usage block).
4. Check the global daily kill-switch via cost_tracker.is_under_cap.
5. Submit to Anthropic via client.beta.messages.batches.create().
6. Persist a ReviewBatch row with status='in_progress'.

The poller (batch_poller.py) takes over from there.

Errors during prompt construction for one user are logged and skipped —
a single misconfigured user must not block the whole batch.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from anthropic.types.beta.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.beta.messages.batch_create_params import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import ReviewBatch
from ..deps import get_user_wealth
from ..repositories import profile as profile_repo
from ..repositories import review_batches as batches_repo
from . import anthropic_client, cost_tracker
from ._retry import retry_on_overload
from .prompt_builder import SYSTEM_PROMPT, build_anonymized_snapshot, build_user_prompt

logger = logging.getLogger(__name__)

# Pre-submit estimation parameters (used for the kill-switch only —
# actual cost comes from message.usage in the poller).
_ESTIMATED_INPUT_TOKENS_PER_REVIEW = 16_000
_ESTIMATED_OUTPUT_TOKENS_PER_REVIEW = 3_000
_ESTIMATED_WEB_SEARCHES_PER_REVIEW = 4
_BATCH_DISCOUNT = 0.5


def estimate_cost_per_review() -> float:
    """Estimate one user's batched review cost in USD (conservative).

    Conservative: applies the 50% batch discount to the entire compute
    (input + output + web_search), even though web_search is not actually
    discounted. Slight under-estimate vs reality, but the kill-switch cap
    ($5/day) is loose enough that this is safe.
    """
    api_cost = cost_tracker.compute_cost_usd(
        _ESTIMATED_INPUT_TOKENS_PER_REVIEW,
        _ESTIMATED_OUTPUT_TOKENS_PER_REVIEW,
        _ESTIMATED_WEB_SEARCHES_PER_REVIEW,
    )
    return api_cost * _BATCH_DISCOUNT


@retry_on_overload
async def _create_batch_with_retry(client: Any, requests: list[Request]) -> Any:
    """Submit batch with retry on Anthropic 529/503.

    Safe to retry: batches.create() is rejected at the gate when overloaded,
    no tokens are consumed on failure. See app.llm._retry module docstring.
    """
    return await client.beta.messages.batches.create(requests=requests)


async def submit_nightly_batch(session: AsyncSession) -> ReviewBatch | None:
    """Build and submit one batch containing all opt-in users.

    Returns:
        The persisted ReviewBatch, or None if there was no work to do
        (no opt-in users, cap reached, or no valid requests built).
    """
    # 1. List opt-in users
    opted_in_profiles = await profile_repo.list_opted_in_users(session)
    if not opted_in_profiles:
        logger.info("No opt-in users for nightly batch — skipping")
        return None

    n_users = len(opted_in_profiles)
    estimated_total = n_users * estimate_cost_per_review()
    logger.info(
        "Nightly batch candidates: n=%d, estimated total cost ~$%.4f",
        n_users,
        estimated_total,
    )

    # 2. Kill-switch on global daily cost
    if not await cost_tracker.is_under_cap(session):
        logger.warning("Daily cost cap reached — refusing batch submit")
        return None

    # 3. Build per-user requests
    requests: list[Request] = []
    skipped: list[uuid.UUID] = []

    for profile in opted_in_profiles:
        user_id = profile.user_id
        try:
            user = await session.get(User, user_id)
            if user is None:
                logger.warning(
                    "Opt-in profile %s references missing User row, skipping",
                    user_id,
                )
                skipped.append(user_id)
                continue

            wealth = await get_user_wealth(user=user, session=session)
            snapshot = build_anonymized_snapshot(wealth, profile)
            user_prompt = build_user_prompt(snapshot)

            requests.append(
                Request(
                    custom_id=str(user_id),
                    params=MessageCreateParamsNonStreaming(
                        model=anthropic_client.MODEL,
                        max_tokens=anthropic_client.MAX_TOKENS,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": user_prompt}],
                        tools=[
                            {
                                "type": "web_search_20250305",
                                "name": "web_search",
                                "max_uses": anthropic_client.WEB_SEARCH_MAX_USES,
                            }
                        ],
                    ),
                )
            )
        except Exception:
            logger.exception(
                "Failed to build batch request for user %s, skipping",
                user_id,
            )
            skipped.append(user_id)

    if not requests:
        logger.warning("No valid requests built — aborting batch submit")
        return None

    if skipped:
        logger.warning(
            "Batch will skip %d/%d users: %s",
            len(skipped),
            n_users,
            [str(u) for u in skipped],
        )

    # 4. Submit to Anthropic
    client = anthropic_client.get_client()
    anthropic_batch = await _create_batch_with_retry(client, requests)
    logger.info(
        "Anthropic batch submitted: anthropic_id=%s n_requests=%d",
        anthropic_batch.id,
        len(requests),
    )

    # 5. Persist
    batch = await batches_repo.create(
        session,
        anthropic_batch_id=anthropic_batch.id,
        status="in_progress",
        n_requests=len(requests),
        estimated_cost_usd=len(requests) * estimate_cost_per_review(),
    )
    return batch
