"""The demo account looks like anyone's account, and can be refreshed (ADR-035)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app import demo
from app.db.engine import async_session_factory
from app.repositories import account_holdings as holdings_repo
from app.repositories import bank_accounts as accounts_repo


@pytest.mark.integration
async def test_seed_gives_a_person_with_accounts_positions_spending_and_readings(client):
    email = f"demo-{uuid.uuid4().hex[:8]}@test.com"
    async with async_session_factory() as session:
        user_id = await demo.seed(
            session, email=email, password="DemoPwd123!", today=date(2026, 9, 15)
        )
    async with async_session_factory() as session:
        again = await demo.seed(
            session, email=email, password="DemoPwd456!", today=date(2026, 9, 15)
        )
    assert again == user_id  # refreshed, not duplicated

    client.cookies.clear()
    resp = await client.post("/api/auth/login", data={"username": email, "password": "DemoPwd456!"})
    assert resp.status_code == 204
    me = (await client.get("/api/users/me")).json()
    assert me["is_verified"] and me["terms_version_accepted"]

    wealth = (await client.get("/api/wealth")).json()
    assert wealth["checking_total"] == pytest.approx(2340.55)
    assert wealth["investments_total"] > 8000
    assert [e["envelope_type"] for e in wealth["envelopes"]] == ["livret_a"]
    async with async_session_factory() as session:
        rows = await accounts_repo.list_accounts(session, user_id)
        held = [
            h.ticker
            for row in rows
            for h in await holdings_repo.list_holdings(session, user_id, row.id)
        ]
    assert sorted(held) == ["CW8.PA", "PE500.PA"]

    spending = (await client.get("/api/spending?months=3")).json()
    assert spending["monthly_average"] and spending["monthly_average"] > 1000
    assert any(c["category"] == "loyer" for c in spending["categories"])
    client.cookies.clear()
