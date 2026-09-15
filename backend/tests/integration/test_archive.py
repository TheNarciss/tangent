"""Twice a day, one sealed row per user and one clear row for the market (ADR-034)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import archive
from app.db.engine import async_session_factory
from app.db.models import DataSnapshot


async def _user(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "TestPwd123!", "display_name": "a"}
    )
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


async def _rows(
    user_id: uuid.UUID, when: datetime
) -> tuple[list[DataSnapshot], list[DataSnapshot]]:
    day = when.astimezone(archive._PARIS).date()
    async with async_session_factory() as session:
        rows = (
            (await session.execute(select(DataSnapshot).where(DataSnapshot.snapshot_date == day)))
            .scalars()
            .all()
        )
    mine = [r for r in rows if r.user_id == user_id]
    market = [r for r in rows if r.scope == "market" and r.slot == "morning"]
    return mine, market


@pytest.mark.integration
async def test_run_writes_a_sealed_user_row_and_a_clear_market_row(client):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _user(client, f"archive-{run_id}@test.com")
    # A day of its own, so other tests' rows and reruns never collide.
    when = datetime(2030, 1, 1, 5, 45, tzinfo=UTC) + timedelta(days=int(run_id[:4], 16) % 3000)

    async with async_session_factory() as session:
        written, market_ok = await archive.run(session, "morning", when=when)
    assert market_ok
    assert written >= 1

    mine, market = await _rows(user_id, when)
    assert len(mine) == 1
    row = mine[0]
    assert row.scope == "user" and row.slot == "morning"
    assert row.payload is None and row.sealed
    assert row.size_bytes == len(row.sealed)
    payload = archive.unseal(row.sealed)
    assert payload["user_id"] == str(user_id)
    for key in ("profile", "wealth", "summary", "accounts", "holdings", "spending", "watchlist"):
        assert key in payload, key
    assert "verdicts" in payload and "dashboard" in payload

    assert len(market) == 1
    assert market[0].sealed is None
    assert set(market[0].payload) >= {"taken_at", "prices", "macro", "picks", "market_leads"}

    # The same slot run again replaces the rows rather than adding to them.
    later = when + timedelta(minutes=10)
    async with async_session_factory() as session:
        await archive.run(session, "morning", when=later)
    mine, market = await _rows(user_id, when)
    assert len(mine) == 1 and len(market) == 1
    assert mine[0].taken_at == later and market[0].taken_at == later


@pytest.mark.integration
async def test_without_the_key_the_market_is_written_and_no_user_row(client, monkeypatch):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _user(client, f"archive-nokey-{run_id}@test.com")
    when = datetime(2040, 1, 1, 17, 30, tzinfo=UTC) + timedelta(days=int(run_id[:4], 16) % 3000)
    monkeypatch.setenv("ARCHIVE_ENCRYPTION_KEY", "")

    async with async_session_factory() as session:
        written, market_ok = await archive.run(session, "evening", when=when)
    assert market_ok and written == 0

    day = when.astimezone(archive._PARIS).date()
    async with async_session_factory() as session:
        rows = (
            (await session.execute(select(DataSnapshot).where(DataSnapshot.snapshot_date == day)))
            .scalars()
            .all()
        )
    assert [r.scope for r in rows] == ["market"]
    assert all(r.user_id != user_id for r in rows)
