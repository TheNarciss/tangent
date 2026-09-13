"""GET /api/spending — debits on current accounts, per month and category."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_spending_requires_login(client):
    client.cookies.clear()
    assert (await client.get("/api/spending")).status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_spending_has_one_entry_per_month_even_when_empty(client):
    email = f"spend-{uuid.uuid4().hex[:8]}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "spend"},
    )
    assert resp.status_code in (200, 201)
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204

    resp = await client.get("/api/spending?months=3")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["months"]) == 3
    assert all(m["total"] == 0 for m in body["months"])
    assert body["categories"] == []
    assert body["merchants"] == []
    assert body["monthly_average"] is None
    assert body["monthly_income_average"] is None
    assert all(m["income"] == 0 for m in body["months"])
    assert body["unlabelled_share"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_a_transfer_is_internal_only_when_its_other_leg_exists(client):
    """The label says « virement_interne » on both; only one lands on an own account."""
    import uuid as _uuid
    from datetime import date, timedelta

    from sqlalchemy import select

    from app.auth.models import User
    from app.db.engine import async_session_factory
    from app.db.models import BankAccount, BankTransaction

    email = f"legs-{_uuid.uuid4().hex[:8]}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "legs"},
    )
    assert resp.status_code in (200, 201)
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204

    today = date.today()
    async with async_session_factory() as session:
        user_id = (await session.execute(select(User.id).where(User.email == email))).scalar_one()
        main = BankAccount(
            user_id=user_id,
            provider="test",
            provider_account_id="main",
            name="Courant",
            type="checking",
        )
        other = BankAccount(
            user_id=user_id,
            provider="test",
            provider_account_id="other",
            name="Second",
            type="checking",
        )
        session.add_all([main, other])
        await session.flush()

        def tx(account: BankAccount, ref: str, amount: float, days_ago: int, category: str | None):
            return BankTransaction(
                user_id=user_id,
                bank_account_id=account.id,
                provider_transaction_id=ref,
                amount=amount,
                currency="EUR",
                transaction_date=today - timedelta(days=days_ago),
                description=ref,
                category=category,
            )

        session.add_all(
            [
                # own transfer: the debit and its credit, a day apart, on two own accounts
                tx(main, "VIR VERS SECOND", -100.0, 5, "virement_interne"),
                tx(other, "VIR DEPUIS COURANT", 100.0, 4, "virement_interne"),
                # same label, no other leg: the money went to a card account we do not know
                tx(main, "INST EMIS REVOLUT", -250.0, 3, "virement_interne"),
                # ordinary spending
                tx(main, "CB TOTAL", -37.0, 2, "carburant"),
                # income, and its would-be counterpart nowhere
                tx(main, "VIR SALAIRE", 1400.0, 6, "salaire"),
            ]
        )
        await session.commit()

    resp = await client.get("/api/spending?months=1")

    assert resp.status_code == 200
    body = resp.json()
    month = body["months"][-1]
    assert month["total"] == pytest.approx(
        287.0
    )  # 250 gone + 37 fuel; the own transfer is not spending
    assert month["by_category"] == {"virement_sortant": 250.0, "carburant": 37.0}
    assert month["income"] == pytest.approx(
        1400.0
    )  # the credit from the own transfer is not income
    assert [m["name"] for m in body["merchants"]][:1] == ["inst emis revolut"]
