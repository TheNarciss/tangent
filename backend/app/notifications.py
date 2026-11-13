"""Who to tell, in which language, and forgetting the phones Apple retired.

Ties the device tokens to the sender: `app/push.py` knows how to talk to
Apple, `app/repositories/device_tokens.py` knows which phones exist, and this
module is the one place that decides a person is told something.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from . import push
from .i18n import as_locale
from .repositories import device_tokens as tokens_repo

logger = logging.getLogger(__name__)


async def notify_briefing_ready(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Their briefing is written. Returns how many phones were reached.

    Each phone is told in the language it last showed; a phone Apple no longer
    knows is forgotten on the spot, so the list does not rot.
    """
    if not push.is_configured():
        return 0
    rows = await tokens_repo.list_for_user(session, user_id)
    if not rows:
        return 0
    delivered = 0
    by_locale: dict[str, list[str]] = {}
    for row in rows:
        by_locale.setdefault(as_locale(row.locale), []).append(row.token)
    for locale, tokens in by_locale.items():
        payload = push.briefing_payload(as_locale(locale))
        # One notification a day: a second one replaces the first on the
        # lock screen rather than stacking under it.
        for result in await push.send(tokens, payload, collapse="briefing"):
            if result.delivered:
                delivered += 1
            elif result.dead:
                await tokens_repo.forget(session, result.token)
    logger.info("briefing: %d phone(s) told for user %s", delivered, user_id)
    return delivered
