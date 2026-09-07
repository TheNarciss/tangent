"""Integration tests: /profile persists the v2 fields and derives the risk pair."""

from __future__ import annotations

import secrets

import pytest


async def _login(client) -> None:
    suffix = secrets.token_hex(4)
    email = f"profile-{suffix}@example.com"
    pwd = "test-password-123"
    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})


@pytest.mark.integration
async def test_put_profile_derives_return_and_volatility_from_risk_level(client):
    await _login(client)

    resp = await client.put(
        "/api/profile",
        json={
            "birth_date": "1995-04-12",
            "household_status": "couple",
            "children": 1,
            "fiscal_shares": 2.5,
            "rfr_n_minus_2": 32000,
            "risk_level": 4,
            "monthly_dca": 300,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["risk_level"] == 4
    assert body["target_annual_return"] == pytest.approx(0.09)
    assert body["max_annual_volatility"] == pytest.approx(0.16)
    assert body["household_status"] == "couple"
    assert body["children"] == 1
    assert body["monthly_dca"] == 300

    # Round-trip
    resp = await client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == 4
    assert resp.json()["monthly_dca"] == 300


@pytest.mark.integration
async def test_risk_levels_endpoint_lists_the_slider(client):
    await _login(client)
    resp = await client.get("/api/profile/risk-levels")
    assert resp.status_code == 200
    levels = resp.json()
    assert [lv["level"] for lv in levels] == [1, 2, 3, 4, 5]
    assert levels[0]["label"] == "Prudent"
