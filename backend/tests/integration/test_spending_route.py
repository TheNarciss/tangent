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
