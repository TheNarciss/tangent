"""GET /api/export — the whole account in one JSON, for debugging."""

from __future__ import annotations

import uuid

import pytest

EXPECTED_SECTIONS = {
    "meta",
    "profile",
    "wealth",
    "wealth_summary",
    "accounts",
    "holdings",
    "recent_transactions",
    "dashboard",
    "timeseries",
    "verdicts",
    "projection",
    "withdrawal_rate",
    "reviews",
    "method",
    "archive",
}


@pytest.mark.asyncio(loop_scope="session")
async def test_export_requires_login(client):
    client.cookies.clear()
    resp = await client.get("/api/export")
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_export_carries_every_section_and_no_secret(client):
    email = f"export-{uuid.uuid4().hex[:8]}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "export"},
    )
    assert resp.status_code in (200, 201)
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204

    resp = await client.get("/api/export")

    assert resp.status_code == 200
    body = resp.json()
    assert EXPECTED_SECTIONS <= set(body)
    assert body["meta"]["email"] == email
    # A section that fails is reported, never silently dropped.
    for name in EXPECTED_SECTIONS:
        assert body[name] is not None, name
    assert "hashed_password" not in resp.text
    assert "TestPwd123!" not in resp.text


@pytest.mark.asyncio(loop_scope="session")
async def test_export_carries_the_whole_archive_opened(client):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app import archive
    from app.auth.models import User
    from app.db.engine import async_session_factory

    run_id = uuid.uuid4().hex[:8]
    email = f"export-archive-{run_id}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "export"},
    )
    assert resp.status_code in (200, 201)
    async with async_session_factory() as session:
        user_id = (
            (await session.execute(select(User).where(User.email == email))).scalars().first().id
        )
        when = datetime(2050, 1, 1, 5, 45, tzinfo=UTC) + timedelta(days=int(run_id[:4], 16) % 3000)
        await archive.run(session, "morning", when=when)
        await archive.run(session, "evening", when=when + timedelta(hours=12))

    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204
    body = (await client.get("/api/export")).json()

    day = when.astimezone(archive._PARIS).date().isoformat()
    mine = [e for e in body["archive"] if e["snapshot_date"] == day]
    assert [e["slot"] for e in mine] == ["morning", "evening"]
    for entry in mine:
        assert entry["data"]["user_id"] == str(user_id)
        assert "wealth" in entry["data"] and "spending" in entry["data"]
    # Only this user's rows, never the market's nor anyone else's.
    assert all(e["data"]["user_id"] == str(user_id) for e in body["archive"] if "data" in e)
