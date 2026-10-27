"""A bank linked through Finverse: the code comes back in a POST without a cookie (ADR-037)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.auth import session as app_session
from app.db.engine import async_session_factory
from app.db.models import BankAccount, BankTransaction, FinverseConnection
from app.powens.crypto import decrypt_token
from app.routers import finverse as fv_router

PASSWORD = "TestPwd123!"


async def _user(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "fv"},
    )
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


class _FakeFinverse:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def exchange(self, code: str) -> dict:
        assert code == "the-code"
        return {
            "access_token": "li-token",
            "refresh_token": "refresh-1",
            "login_identity_id": "li-1",
        }

    async def login_identity(self, token: str) -> dict:
        return {"login_identity": {"status": "DATA_RETRIEVAL_COMPLETE"}}

    async def accounts(self, token: str) -> dict:
        return {
            "accounts": [
                {
                    "account_id": "acc-1",
                    "account_name": "My Account",
                    "account_currency": "SGD",
                    "balance": {"value": 500.0, "currency": "SGD"},
                    "account_type": {"type": "DEPOSIT", "subtype": "SAVINGS"},
                }
            ],
            "institution": {"institution_name": "DBS Bank"},
        }

    async def transactions(self, token: str) -> list[dict]:
        return [
            {
                "transaction_id": "tx-1",
                "account_id": "acc-1",
                "posted_date": "2026-10-20",
                "amount": {"value": -8.2, "currency": "SGD"},
                "description": "KOPITIAM",
            }
        ]

    async def refresh(self, refresh_token: str) -> dict:
        return {"access_token": "li-token"}

    async def unlink(self, token: str) -> None:
        return None


@pytest.mark.integration
async def test_a_linked_bank_is_stored_read_listed_and_removed(client, monkeypatch):
    email = f"fv-{uuid.uuid4().hex[:8]}@test.com"
    user_id = await _user(client, email)
    monkeypatch.setattr(fv_router, "FinverseClient", _FakeFinverse)
    state = fv_router._sign_state(user_id, "app")

    resp = await client.post(
        "/auth/finverse/callback",
        data={"code": "the-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code == 303, resp.text
    assert resp.headers["location"] == f"{app_session.APP_RETURN_BASE}banks?finverse=success"
    async with async_session_factory() as s:
        row = (
            (
                await s.execute(
                    select(FinverseConnection).where(FinverseConnection.user_id == user_id)
                )
            )
            .scalars()
            .one()
        )
        assert decrypt_token(row.encrypted_refresh_token) == "refresh-1"
        assert row.institution_name == "DBS Bank"
        accounts = (
            (await s.execute(select(BankAccount).where(BankAccount.user_id == user_id)))
            .scalars()
            .all()
        )
        assert [(a.provider, a.currency) for a in accounts] == [("finverse", "SGD")]
        txs = (
            (
                await s.execute(
                    select(BankTransaction).where(BankTransaction.bank_account_id == accounts[0].id)
                )
            )
            .scalars()
            .all()
        )
        assert [float(t.amount) for t in txs] == [-8.2]

    resp = await client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 204
    listed = (await client.get("/api/finverse/connections")).json()
    assert [(c["institution_name"], c["accounts_count"]) for c in listed] == [("DBS Bank", 1)]

    assert (await client.delete(f"/api/finverse/connections/{listed[0]['id']}")).status_code == 204
    assert (await client.get("/api/finverse/connections")).json() == []
    async with async_session_factory() as s:
        left = (
            (await s.execute(select(BankAccount).where(BankAccount.user_id == user_id)))
            .scalars()
            .all()
        )
    assert left == []


@pytest.mark.integration
async def test_the_callback_refuses_a_bad_state_and_a_cancelled_link(client, monkeypatch):
    user_id = await _user(client, f"fv-bad-{uuid.uuid4().hex[:8]}@test.com")
    monkeypatch.setattr(fv_router, "FinverseClient", _FakeFinverse)

    resp = await client.post(
        "/auth/finverse/callback", data={"code": "c", "state": "junk"}, follow_redirects=False
    )
    assert resp.status_code == 303
    assert "finverse=error&error=bad_state" in resp.headers["location"]

    resp = await client.get(
        "/auth/finverse/callback",
        params={"error": "access_denied", "state": fv_router._sign_state(user_id)},
        follow_redirects=False,
    )
    assert resp.headers["location"].endswith("/?finverse=error&error=access_denied")


@pytest.mark.integration
async def test_linking_needs_the_keys(client, monkeypatch):
    email = f"fv-cfg-{uuid.uuid4().hex[:8]}@test.com"
    await _user(client, email)
    resp = await client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 204
    monkeypatch.setattr(fv_router.settings, "client_id", "")

    assert (await client.get("/api/finverse/status")).json() == {"configured": False}
    assert (await client.post("/api/finverse/link", json={"platform": "app"})).status_code == 503
