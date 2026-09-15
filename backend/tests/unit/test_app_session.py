"""The session as the iPhone app needs it: renewed while in use, handed over once (ADR-035)."""

from __future__ import annotations

import time
import uuid

import pytest
from fastapi_users.jwt import decode_jwt, generate_jwt

from app.auth import session
from app.auth.backend import COOKIE_LIFETIME, JWT_SECRET


def _session_token(age_seconds: float) -> str:
    return generate_jwt(
        {"sub": str(uuid.uuid4()), "aud": session.SESSION_AUDIENCE},
        JWT_SECRET,
        COOKIE_LIFETIME - int(age_seconds),
    )


def test_a_young_token_is_left_alone():
    assert session.renewed_token(_session_token(age_seconds=60)) is None


def test_an_old_token_is_replaced_by_a_fresh_one_for_the_same_user():
    old = _session_token(age_seconds=session.RENEW_AFTER_SECONDS + 5)
    fresh = session.renewed_token(old)
    assert fresh is not None and fresh != old
    before = decode_jwt(old, JWT_SECRET, [session.SESSION_AUDIENCE])
    after = decode_jwt(fresh, JWT_SECRET, [session.SESSION_AUDIENCE])
    assert after["sub"] == before["sub"]
    assert after["exp"] - time.time() > COOKIE_LIFETIME - 5


def test_a_token_that_is_not_ours_is_never_renewed():
    other = generate_jwt({"sub": "x", "aud": "other"}, JWT_SECRET, 3600)
    assert session.renewed_token(other) is None
    assert session.renewed_token("garbage") is None


def test_exchange_code_opens_once_for_the_right_verifier():
    user_id = uuid.uuid4()
    verifier = "a" * 64
    code = session.mint_exchange_code(user_id, session.challenge_of(verifier))
    assert session.redeem_exchange_code(code, verifier) == user_id
    with pytest.raises(ValueError, match="déjà utilisé"):
        session.redeem_exchange_code(code, verifier)


def test_exchange_code_refuses_the_wrong_verifier_and_keeps_the_code_unused():
    code = session.mint_exchange_code(uuid.uuid4(), session.challenge_of("b" * 64))
    with pytest.raises(ValueError, match="verifier"):
        session.redeem_exchange_code(code, "c" * 64)
    # Not burnt by the failed attempt: the right holder can still open it.
    session.redeem_exchange_code(code, "b" * 64)


def test_exchange_code_refuses_a_session_token_and_an_expired_code():
    with pytest.raises(ValueError):
        session.redeem_exchange_code(_session_token(0), "a" * 64)
    expired = generate_jwt(
        {"sub": str(uuid.uuid4()), "aud": session.EXCHANGE_AUDIENCE, "jti": "x", "chal": "y"},
        JWT_SECRET,
        -1,
    )
    with pytest.raises(ValueError, match="expiré"):
        session.redeem_exchange_code(expired, "a" * 64)


def test_challenge_shape_and_return_url():
    assert session.is_challenge(session.challenge_of("v" * 43))
    assert not session.is_challenge("short")
    assert not session.is_challenge("bad chars!" * 6)
    assert session.app_return("auth", code="abc") == f"{session.APP_RETURN_BASE}auth?code=abc"
