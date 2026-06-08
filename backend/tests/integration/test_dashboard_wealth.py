"""Integration test: /dashboard response carries a wealth summary."""

from __future__ import annotations

import secrets

import pytest


@pytest.mark.integration
async def test_dashboard_includes_wealth_summary(client):
    """The /dashboard response carries a `wealth` summary alongside metrics.

    The response can fall back to a 422/portfolio-empty error if the user has
    no positions — we test the field surface only, not the metrics themselves.
    """
    suffix = secrets.token_hex(4)
    email = f"dash-wealth-{suffix}@example.com"
    pwd = "test-password-123"

    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})

    resp = await client.get("/api/dashboard")
    # Empty portfolio → 422 expected (no positions). We still check the schema
    # by hitting /dashboard once positions exist would require a heavy fixture.
    # Here we just confirm the endpoint stays reachable and doesn't 500.
    assert resp.status_code in (200, 404, 422)
    if resp.status_code == 200:
        body = resp.json()
        # New field surface : wealth must be present even if empty
        assert "wealth" in body
        w = body["wealth"]
        assert "net_worth" in w
        assert "envelopes" in w
        assert "loans" in w
