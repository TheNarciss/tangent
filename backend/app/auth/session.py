"""The session as the iPhone app needs it (ADR-035): renewed while in use, handed over after OAuth.

The app talks to the same backend as the site, with the same cookie, sent by
the phone's native HTTP stack. Two things the browser does for free do not
happen there, so the backend does them:

- A session that is used stays open. `renewed_token` mints a fresh token
  once the current one is older than `RENEW_AFTER_SECONDS`; the site gets
  the same treatment, so both behave alike.
- An OAuth login runs in the system browser, whose cookies the app never
  sees. The callback therefore hands the app a short, single-use exchange
  code bound to a PKCE challenge the app created; `redeem_exchange_code`
  gives back the user id, once, to whoever holds the verifier.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
import uuid
from base64 import urlsafe_b64encode
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import jwt
from fastapi_users.jwt import decode_jwt, generate_jwt

from .backend import COOKIE_LIFETIME, JWT_SECRET

RENEW_AFTER_SECONDS = int(os.getenv("SESSION_RENEW_AFTER_SECONDS", str(24 * 3600)))
"""A token older than this, seen on `/users/me`, is replaced by a fresh one."""

EXCHANGE_LIFETIME_SECONDS = 60
EXCHANGE_AUDIENCE = "tangent:app-exchange"
SESSION_AUDIENCE = "fastapi-users:auth"  # JWTStrategy's default token audience
APP_RETURN_URL = os.getenv("APP_RETURN_URL", "tangent://auth")
"""Where the system browser sends the app back after OAuth, code or error attached."""

_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")  # base64url of a SHA-256, PKCE-style
_redeemed: dict[str, float] = {}  # jti → expiry, so a code opens one session, not two


# ── Sliding renewal ─────────────────────────────────────────────────────────


def renewed_token(token: str, *, now: float | None = None) -> str | None:
    """A fresh token for the same user when this one has aged past the threshold.

    None when the token is still young, or not ours at all: renewal never
    turns a bad token into a good one, it only extends a session that the
    route just accepted.
    """
    try:
        data = decode_jwt(token, JWT_SECRET, [SESSION_AUDIENCE])
    except jwt.PyJWTError:
        return None
    now = now if now is not None else time.time()
    issued_at = float(data["exp"]) - COOKIE_LIFETIME
    if now - issued_at < RENEW_AFTER_SECONDS:
        return None
    return generate_jwt({"sub": data["sub"], "aud": SESSION_AUDIENCE}, JWT_SECRET, COOKIE_LIFETIME)


# ── Exchange code, PKCE-bound ──────────────────────────────────────────────


def is_challenge(value: str | None) -> bool:
    return bool(value and _CHALLENGE.match(value))


def challenge_of(verifier: str) -> str:
    """S256: the challenge the app derives from its verifier, base64url without padding."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return urlsafe_b64encode(digest).decode().rstrip("=")


def mint_exchange_code(user_id: uuid.UUID | str, challenge: str) -> str:
    return generate_jwt(
        {
            "sub": str(user_id),
            "aud": EXCHANGE_AUDIENCE,
            "jti": secrets.token_urlsafe(16),
            "chal": challenge,
        },
        JWT_SECRET,
        EXCHANGE_LIFETIME_SECONDS,
    )


def redeem_exchange_code(code: str, verifier: str) -> uuid.UUID:
    """The user id behind the code, once, for the holder of the matching verifier.

    Raises ValueError for anything else: expired, forged, already used, or a
    verifier that does not hash to the challenge the code was minted with.
    """
    try:
        data: dict[str, Any] = decode_jwt(code, JWT_SECRET, [EXCHANGE_AUDIENCE])
    except jwt.PyJWTError as exc:
        raise ValueError("code invalide ou expiré") from exc
    jti = str(data.get("jti", ""))
    now = time.time()
    for used, until in list(_redeemed.items()):
        if until < now:
            del _redeemed[used]
    if not jti or jti in _redeemed:
        raise ValueError("code déjà utilisé")
    if not secrets.compare_digest(challenge_of(verifier), str(data.get("chal", ""))):
        raise ValueError("verifier incorrect")
    _redeemed[jti] = float(data["exp"])
    return uuid.UUID(str(data["sub"]))


def app_return(**params: str) -> str:
    """The URL that brings the user back into the app, with the given query."""
    return f"{APP_RETURN_URL}?{urlencode(params)}"


def now_utc() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "APP_RETURN_URL",
    "EXCHANGE_LIFETIME_SECONDS",
    "RENEW_AFTER_SECONDS",
    "app_return",
    "challenge_of",
    "is_challenge",
    "mint_exchange_code",
    "redeem_exchange_code",
    "renewed_token",
]
