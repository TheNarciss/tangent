"""The archive seals what is personal and refuses to write it without the key (ADR-034)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app import archive


def test_seal_then_unseal_gives_the_payload_back_with_plain_types():
    payload = {
        "user_id": uuid.uuid4(),
        "taken_at": datetime(2026, 9, 15, 5, 45, tzinfo=UTC),
        "day": date(2026, 9, 15),
        "amount": 12.5,
        "nested": {"tickers": ["CW8.PA", "PE500.PA"]},
    }
    token = archive.seal(payload)
    assert "CW8" not in token  # nothing personal readable in the row
    back = archive.unseal(token)
    assert back["user_id"] == str(payload["user_id"])
    assert back["taken_at"] == "2026-09-15 05:45:00+00:00"
    assert back["day"] == "2026-09-15"
    assert back["amount"] == 12.5
    assert back["nested"] == {"tickers": ["CW8.PA", "PE500.PA"]}


def test_a_token_sealed_with_another_key_does_not_open(monkeypatch):
    token = archive.seal({"secret": 1})
    monkeypatch.setenv("ARCHIVE_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(InvalidToken):
        archive.unseal(token)


def test_without_the_key_nothing_personal_is_sealed(monkeypatch):
    monkeypatch.setenv("ARCHIVE_ENCRYPTION_KEY", "")
    with pytest.raises(archive.ArchiveKeyMissing):
        archive.seal({"secret": 1})
    monkeypatch.setenv("ARCHIVE_ENCRYPTION_KEY", "not-a-fernet-key")
    with pytest.raises(archive.ArchiveKeyMissing):
        archive.seal({"secret": 1})


def test_slot_is_named_by_the_paris_hour():
    assert archive.slot_for(datetime(2026, 9, 15, 5, 45, tzinfo=UTC)) == "morning"  # 07:45 Paris
    assert archive.slot_for(datetime(2026, 9, 15, 17, 30, tzinfo=UTC)) == "evening"  # 19:30 Paris


async def test_an_unknown_slot_is_refused():
    with pytest.raises(ValueError):
        await archive.run(None, "noon")  # type: ignore[arg-type]
