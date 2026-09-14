"""Enable Banking routes: a fresh user has no session; the callback refuses a bad state."""

from __future__ import annotations

import uuid

import pytest


async def _login(client) -> None:
    email = f"eb-{uuid.uuid4().hex[:8]}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "eb"},
    )
    assert resp.status_code in (200, 201)
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_sessions_require_login(client):
    client.cookies.clear()
    assert (await client.get("/api/enablebanking/sessions")).status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_a_fresh_user_has_no_session_and_sees_whether_it_is_configured(client):
    await _login(client)

    assert (await client.get("/api/enablebanking/sessions")).json() == []
    status = (await client.get("/api/enablebanking/status")).json()
    assert set(status) == {"configured"}


@pytest.mark.asyncio(loop_scope="session")
async def test_the_callback_sends_a_bad_state_back_to_the_app(client):
    await _login(client)

    resp = await client.get(
        "/auth/enablebanking/callback",
        params={"code": "c", "state": "junk"},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    assert "enablebanking=error&error=bad_state" in resp.headers["location"]
