"""Integration test: GET /wealth is the DB-only patrimony endpoint."""

from __future__ import annotations

import secrets

import pytest


@pytest.mark.integration
async def test_wealth_endpoint_is_db_only(client):
    """GET /wealth answers 200 with an empty summary for a fresh user
    (no market data involved, unlike /dashboard)."""
    suffix = secrets.token_hex(4)
    email = f"wealth-{suffix}@example.com"
    pwd = "test-password-123"

    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})

    resp = await client.get("/api/wealth")
    assert resp.status_code == 200
    body = resp.json()
    assert body["net_worth"] == 0
    assert body["total_assets"] == 0
    assert body["total_liabilities"] == 0
    assert body["envelopes"] == []
    assert body["loans"] == []
