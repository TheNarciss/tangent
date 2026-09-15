"""A bank consent started in the app comes back through the system browser, without a cookie (ADR-035)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.auth import session as app_session
from app.db.engine import async_session_factory
from app.db.models import EnableBankingSession, PowensCredential
from app.routers import enablebanking as eb_router
from app.routers import powens as powens_router


async def _user(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "b"},
    )
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


class _FakeEnableBanking:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def create_session(self, code: str) -> dict:
        assert code == "the-code"
        return {
            "session_id": "sess-1",
            "accounts": [{"uid": "acc-1"}],
            "aspsp": {"name": "Revolut", "country": "FR"},
            "access": {"valid_until": "2027-01-01T00:00:00Z"},
            "psu_type": "personal",
        }


@pytest.mark.integration
async def test_enablebanking_callback_from_the_app_trusts_the_signed_state(client, monkeypatch):
    user_id = await _user(client, f"eb-app-{uuid.uuid4().hex[:8]}@test.com")
    monkeypatch.setattr(eb_router, "EnableBankingClient", _FakeEnableBanking)

    async def no_sync(db, row, *, since):
        return SimpleNamespace(success=False)

    monkeypatch.setattr(eb_router, "sync_row", no_sync)
    state = eb_router._sign_state(user_id, "Revolut", "FR", "app")

    resp = await client.get(
        "/auth/enablebanking/callback",
        params={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307), resp.text
    assert resp.headers["location"] == f"{app_session.APP_RETURN_BASE}banks?enablebanking=success"
    async with async_session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(EnableBankingSession).where(EnableBankingSession.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
    assert [r.bank_name for r in rows] == ["Revolut"]


@pytest.mark.integration
async def test_enablebanking_callback_from_the_site_still_needs_the_cookie(client, monkeypatch):
    user_id = await _user(client, f"eb-web-{uuid.uuid4().hex[:8]}@test.com")
    monkeypatch.setattr(eb_router, "EnableBankingClient", _FakeEnableBanking)
    state = eb_router._sign_state(user_id, "Revolut", "FR", "web")

    resp = await client.get(
        "/auth/enablebanking/callback",
        params={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert "enablebanking=error&error=wrong_user" in resp.headers["location"]
    assert resp.headers["location"].startswith("http")  # the site, not the app


@pytest.mark.integration
async def test_powens_callback_from_the_app_stores_the_token_for_the_state_user(
    client, monkeypatch
):
    user_id = await _user(client, f"powens-app-{uuid.uuid4().hex[:8]}@test.com")

    async def fake_exchange(code: str) -> dict:
        assert code == "the-code"
        return {"access_token": "tok-123"}

    monkeypatch.setattr(powens_router, "exchange_code_for_token", fake_exchange)
    state = powens_router._sign_state(user_id, "app")

    resp = await client.get(
        "/auth/powens/callback", params={"code": "the-code", "state": state}, follow_redirects=False
    )
    assert resp.status_code in (302, 307), resp.text
    assert resp.headers["location"] == f"{app_session.APP_RETURN_BASE}banks?powens_sync=success"
    async with async_session_factory() as s:
        cred = (
            (await s.execute(select(PowensCredential).where(PowensCredential.user_id == user_id)))
            .scalars()
            .first()
        )
    assert cred is not None

    # Adding a second bank: no code, the state alone brings the person back into the app.
    resp = await client.get(
        "/auth/powens/callback",
        params={"state": state, "connection_id": "7"},
        follow_redirects=False,
    )
    assert resp.headers["location"].endswith("banks?powens_sync=success")


@pytest.mark.integration
async def test_powens_callback_without_cookie_nor_state_is_refused(client):
    client.cookies.clear()
    resp = await client.get("/auth/powens/callback", params={"code": "c"}, follow_redirects=False)
    assert resp.status_code == 401
    resp = await client.get(
        "/auth/powens/callback", params={"code": "c", "state": "junk"}, follow_redirects=False
    )
    assert "powens_sync=error&error=bad_state" in resp.headers["location"]
