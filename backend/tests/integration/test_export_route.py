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
