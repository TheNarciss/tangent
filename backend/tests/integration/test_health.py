"""Smoke test: server is up and DB reachable."""

import pytest


@pytest.mark.integration
async def test_health_endpoint_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "up"
