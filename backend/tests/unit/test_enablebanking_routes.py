"""The state we round-trip through the bank, and the consent length we ask for."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.routers import enablebanking as routes


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(routes, "_STATE_SECRET", "test-secret")


def test_the_state_names_the_user_and_the_bank():
    user_id = uuid.uuid4()

    claims = routes._read_state(routes._sign_state(user_id, "Revolut", "FR"))

    assert claims["sub"] == str(user_id)
    assert claims["bank"] == "Revolut"
    assert claims["country"] == "FR"


def test_a_state_for_another_purpose_is_refused():
    other = jwt.encode({"sub": "x", "purpose": "oauth"}, "test-secret", algorithm="HS256")

    with pytest.raises(jwt.PyJWTError):
        routes._read_state(other)


def test_the_consent_asks_for_180_days_or_the_bank_maximum():
    now = datetime.now(UTC)

    assert routes._consent_end(None) - now > timedelta(days=179)
    assert routes._consent_end(90 * 86400) - now < timedelta(days=91)
    assert routes._consent_end(0) - now > timedelta(days=179)


def test_valid_until_is_read_with_its_timezone_or_defaulted():
    parsed = routes._parse_valid_until("2027-03-01T12:00:00.000000+00:00")
    assert parsed.tzinfo is not None and parsed.year == 2027

    fallback = routes._parse_valid_until(None)
    assert fallback - datetime.now(UTC) > timedelta(days=179)
