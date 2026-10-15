"""Telling a phone that its briefing is ready (ADR-037).

Apple's push service speaks HTTP/2 and nothing else, and authenticates the
sender with a short JWT signed by a developer key (ES256), not with a
password. One connection, one token reused for the whole batch: Apple asks
that it not be regenerated more often than every twenty minutes.

Nothing personal travels: the notification carries a fixed sentence in the
person's language, never a figure and never their name. What it is about is
already on their phone once they open the app.

Not configured (no key on this machine) means no notification and no error:
the briefing is written all the same.
"""

from __future__ import annotations

import base64
import logging
import os
import time
import uuid
from dataclasses import dataclass

import httpx
import jwt

from .i18n import Locale, t

logger = logging.getLogger(__name__)

TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
KEY_ID = os.getenv("APNS_KEY_ID", "")
PRIVATE_KEY_B64 = os.getenv("APNS_PRIVATE_KEY_B64", "")
BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", "")
# Apple runs two separate services: a build signed for distribution talks to
# the first, one signed for development to the second, and a token from one is
# unknown to the other.
HOSTS = {
    "production": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}
ENVIRONMENT = os.getenv("APNS_ENVIRONMENT", "production")
TOKEN_LIFETIME = 45 * 60  # Apple refuses a JWT older than an hour
TIMEOUT = httpx.Timeout(10.0)


def is_configured() -> bool:
    return all((TEAM_ID, KEY_ID, PRIVATE_KEY_B64, BUNDLE_ID))


def host() -> str:
    return HOSTS.get(ENVIRONMENT, HOSTS["production"])


@dataclass
class _CachedToken:
    value: str
    issued_at: float


_token: _CachedToken | None = None


def provider_token(*, now: float | None = None) -> str:
    """The bearer Apple expects, kept for as long as it stays valid."""
    global _token
    now = now if now is not None else time.time()
    if _token is not None and now - _token.issued_at < TOKEN_LIFETIME:
        return _token.value
    key = base64.b64decode(PRIVATE_KEY_B64).decode()
    value = jwt.encode(
        {"iss": TEAM_ID, "iat": int(now)},
        key,
        algorithm="ES256",
        headers={"kid": KEY_ID},
    )
    _token = _CachedToken(value=value, issued_at=now)
    return value


def briefing_payload(locale: Locale) -> dict:
    """The one notification we send, in the person's language."""
    return {
        "aps": {
            "alert": {
                "title": t(locale, "push.briefing.title"),
                "body": t(locale, "push.briefing.body"),
            },
            "sound": "default",
            "thread-id": "briefing",
        }
    }


# What Apple answers when a token leads nowhere: the phone reinstalled, the app
# was deleted, or the token belongs to the other environment. Forget it.
DEAD_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}


@dataclass
class Delivery:
    token: str
    delivered: bool
    dead: bool
    reason: str | None = None


async def send(tokens: list[str], payload: dict, *, collapse: str | None = None) -> list[Delivery]:
    """Push one payload to several phones. Never raises: a notification is not the app."""
    if not tokens:
        return []
    if not is_configured():
        logger.info("APNs not configured — %d notification(s) not sent", len(tokens))
        return [
            Delivery(token=tok, delivered=False, dead=False, reason="unconfigured")
            for tok in tokens
        ]

    headers = {
        "authorization": f"bearer {provider_token()}",
        "apns-topic": BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    if collapse:
        headers["apns-collapse-id"] = collapse

    results: list[Delivery] = []
    try:
        async with httpx.AsyncClient(http2=True, timeout=TIMEOUT, base_url=host()) as client:
            for token in tokens:
                results.append(await _send_one(client, headers, token, payload))
    except httpx.HTTPError as exc:
        logger.warning("APNs unreachable: %s", exc)
        sent = {d.token for d in results}
        results += [
            Delivery(token=tok, delivered=False, dead=False, reason="unreachable")
            for tok in tokens
            if tok not in sent
        ]
    return results


async def _send_one(
    client: httpx.AsyncClient, headers: dict[str, str], token: str, payload: dict
) -> Delivery:
    try:
        response = await client.post(
            f"/3/device/{token}",
            json=payload,
            headers={**headers, "apns-id": str(uuid.uuid4())},
        )
    except httpx.HTTPError as exc:
        logger.warning("APNs: %s", exc)
        return Delivery(token=token, delivered=False, dead=False, reason="unreachable")
    if response.status_code == 200:
        return Delivery(token=token, delivered=True, dead=False)
    reason = _reason_of(response)
    dead = reason in DEAD_REASONS
    logger.info("APNs refused a token (%s, %s)", response.status_code, reason)
    return Delivery(token=token, delivered=False, dead=dead, reason=reason)


def _reason_of(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("reason") if isinstance(body, dict) else None
