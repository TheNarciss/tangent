"""The phones that agreed to be told when a briefing is ready (ADR-037)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app import notifications, push
from app.db.engine import async_session_factory
from app.db.models import DeviceToken

TOKEN = "a1b2c3d4" * 8  # 64 hexadecimal characters, the shape Apple hands out


async def _signed_in(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "TestPwd123!", "display_name": "a"}
    )
    assert resp.status_code in (200, 201), resp.text
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204, resp.text
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


async def _tokens(user_id: uuid.UUID) -> list[DeviceToken]:
    async with async_session_factory() as session:
        rows = await session.execute(select(DeviceToken).where(DeviceToken.user_id == user_id))
        return list(rows.scalars().all())


@pytest.mark.asyncio
async def test_a_phone_registers_once_however_often_it_says_hello(client):
    user_id = await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")

    resp = await client.post("/api/devices", json={"token": TOKEN})
    assert resp.status_code == 204, resp.text
    resp = await client.post(
        "/api/devices", json={"token": TOKEN}, headers={"Accept-Language": "en-GB"}
    )
    assert resp.status_code == 204

    rows = await _tokens(user_id)
    assert len(rows) == 1
    # The language follows the app: the second hello came from an English screen.
    assert rows[0].locale == "en" and rows[0].platform == "ios"
    client.cookies.clear()


@pytest.mark.asyncio
async def test_signing_out_of_a_phone_forgets_it(client):
    user_id = await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    await client.post("/api/devices", json={"token": TOKEN})

    resp = await client.delete(f"/api/devices/{TOKEN}")
    assert resp.status_code == 204
    assert await _tokens(user_id) == []
    # Doing it twice is not an error.
    assert (await client.delete(f"/api/devices/{TOKEN}")).status_code == 204
    client.cookies.clear()


@pytest.mark.asyncio
async def test_nobody_can_forget_someone_else_s_phone(client):
    mine = await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    await client.post("/api/devices", json={"token": TOKEN})
    client.cookies.clear()

    await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    assert (await client.delete(f"/api/devices/{TOKEN}")).status_code == 204
    assert len(await _tokens(mine)) == 1  # untouched
    client.cookies.clear()


@pytest.mark.asyncio
async def test_a_token_that_is_not_hexadecimal_is_refused(client):
    await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.post("/api/devices", json={"token": "pas-un-jeton"})
    assert resp.status_code == 422
    client.cookies.clear()


@pytest.mark.asyncio
async def test_a_signed_out_visitor_registers_nothing(client):
    client.cookies.clear()
    assert (await client.post("/api/devices", json={"token": TOKEN})).status_code == 401


@pytest.mark.asyncio
async def test_the_briefing_tells_every_phone_and_drops_the_retired_ones(client, monkeypatch):
    user_id = await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    alive, dead = TOKEN, "f" * 64
    await client.post("/api/devices", json={"token": alive})
    await client.post("/api/devices", json={"token": dead})
    client.cookies.clear()

    async def fake_send(tokens, payload, *, collapse=None):
        assert collapse == "briefing"
        assert payload["aps"]["alert"]["title"]
        return [push.Delivery(token=tok, delivered=tok != dead, dead=tok == dead) for tok in tokens]

    monkeypatch.setattr(push, "send", fake_send)
    monkeypatch.setattr(push, "is_configured", lambda: True)

    async with async_session_factory() as session:
        told = await notifications.notify_briefing_ready(session, user_id)

    assert told == 1
    assert [row.token for row in await _tokens(user_id)] == [alive]


@pytest.mark.asyncio
async def test_without_a_key_the_briefing_still_goes_through(client, monkeypatch):
    user_id = await _signed_in(client, f"dev-{uuid.uuid4().hex[:8]}@test.com")
    await client.post("/api/devices", json={"token": TOKEN})
    client.cookies.clear()

    monkeypatch.setattr(push, "is_configured", lambda: False)
    async with async_session_factory() as session:
        assert await notifications.notify_briefing_ready(session, user_id) == 0
    assert len(await _tokens(user_id)) == 1  # nothing forgotten by mistake
