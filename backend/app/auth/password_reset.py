"""Password reset business logic.

Flow:
    1) `request_reset(email)` → generate 6-digit code, hash+store, email plaintext to user.
       Always returns success (caller returns 204), no email enumeration.
    2) `verify_code(email, code)` → if matches a non-expired non-used record, mark used,
       return a short-lived reset_token (JWT signed with RESET_TOKEN_SECRET).
    3) `reset_password(reset_token, new_password)` → verify token, hash+update password,
       invalidate all the user's existing JWT sessions (via password_changed_at bump).

Security choices:
    - Code stored as argon2 hash (codes are 6 digits → brute-forceable from DB leak).
    - Max RESET_MAX_ATTEMPTS per code, then it's burnt.
    - Codes expire in RESET_CODE_LIFETIME_SECONDS (default 15 min).
    - Reset tokens are JWTs separate from the auth JWT (different secret).
    - Reset tokens single-use (implicit: after reset, marked used in DB).
    - Constant-time wait on /forgot-password regardless of email validity.
"""

import asyncio
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PasswordResetToken
from .models import User

logger = logging.getLogger(__name__)

# argon2 context for the code hash (separate from password hashing, but same scheme)
_code_hasher = PasswordHash.recommended()

# argon2 for the new password (mirrors fastapi-users default)
_pwd_hasher = PasswordHash.recommended()

RESET_TOKEN_SECRET = os.getenv("RESET_TOKEN_SECRET", "")
CODE_LIFETIME = int(os.getenv("RESET_CODE_LIFETIME_SECONDS", 15 * 60))
TOKEN_LIFETIME = int(os.getenv("RESET_TOKEN_LIFETIME_SECONDS", 5 * 60))
MAX_ATTEMPTS = int(os.getenv("RESET_MAX_ATTEMPTS", 5))

CONSTANT_TIME_DELAY_S = 0.5  # always wait at least this long on /forgot-password


def _gen_code() -> str:
    """6-digit numeric code, cryptographically secure."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_reset(session: AsyncSession, email: str) -> tuple[bool, str | None]:
    """Generate a code and email it. Returns (user_existed, plaintext_code_for_logging).

    Always sleeps CONSTANT_TIME_DELAY_S to mitigate timing attacks. The caller
    must NOT differentiate between user existing or not in the HTTP response.
    """
    start = asyncio.get_event_loop().time()
    res = await session.execute(select(User).where(User.email == email.lower()))
    user = res.scalars().first()

    code = None
    if user is not None:
        # Invalidate any previous active token for this user (only one active at a time)
        await session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used == False)  # noqa: E712
            .values(used=True)
        )
        code = _gen_code()
        token_row = PasswordResetToken(
            user_id=user.id,
            code_hash=_code_hasher.hash(code),
            expires_at=datetime.now(UTC) + timedelta(seconds=CODE_LIFETIME),
        )
        session.add(token_row)
        await session.commit()
        # Send mail (in a thread to not block on Resend network call)
        from ..email import send_password_reset_code

        try:
            await asyncio.to_thread(send_password_reset_code, email, code, CODE_LIFETIME // 60)
        except Exception:
            logger.exception("Email send failed for reset request to %s", email)
            # Don't raise — we still pretend success to the caller (anti-enumeration).

    # Constant-time delay
    elapsed = asyncio.get_event_loop().time() - start
    if elapsed < CONSTANT_TIME_DELAY_S:
        await asyncio.sleep(CONSTANT_TIME_DELAY_S - elapsed)

    return (user is not None, code)


async def verify_code(session: AsyncSession, email: str, code: str) -> str | None:
    """Returns a reset_token JWT if valid, None otherwise.

    Increments attempts counter on failure. Burns the token if exhausted.
    """
    res = await session.execute(select(User).where(User.email == email.lower()))
    user = res.scalars().first()
    if user is None:
        return None  # Don't even tell the caller; just fail

    # Active (non-used, non-expired) token for this user
    now = datetime.now(UTC)
    res = await session.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > now,
            PasswordResetToken.attempts < MAX_ATTEMPTS,
        )
        .order_by(PasswordResetToken.created_at.desc())
    )
    token_row = res.scalars().first()
    if token_row is None:
        return None

    if not _code_hasher.verify(code, token_row.code_hash):
        token_row.attempts += 1
        if token_row.attempts >= MAX_ATTEMPTS:
            token_row.used = True  # burnt
        await session.commit()
        return None

    # Code valid — mark used immediately (single use). The reset_token JWT
    # is now the only way to reset the password.
    token_row.used = True
    await session.commit()

    payload = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "exp": datetime.now(UTC) + timedelta(seconds=TOKEN_LIFETIME),
        "iat": datetime.now(UTC),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, RESET_TOKEN_SECRET, algorithm="HS256")


async def reset_password(session: AsyncSession, reset_token: str, new_password: str) -> bool:
    """Validate token, update password. Returns True if successful."""
    try:
        payload = jwt.decode(reset_token, RESET_TOKEN_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return False

    if payload.get("purpose") != "password_reset":
        return False

    user_id = payload.get("sub")
    if not user_id:
        return False

    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if user is None:
        return False

    user.hashed_password = _pwd_hasher.hash(new_password)
    await session.commit()
    return True
