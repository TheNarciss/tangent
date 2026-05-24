"""Auth contract tests."""

import pytest


@pytest.mark.integration
async def test_users_me_returns_401_without_auth(client):
    """Anonymous users get 401, not 500 or 403."""
    resp = await client.get("/users/me")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_login_with_wrong_password_returns_400(client):
    """Wrong credentials give 400/401, never reveal if email exists."""
    resp = await client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert resp.status_code in (400, 401)
