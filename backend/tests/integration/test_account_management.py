"""Integration tests pour les endpoints de gestion de compte."""

import secrets

import pytest

# ── Change password ───────────────────────────────────────────────────


@pytest.mark.integration
async def test_change_password_success(client):
    """Happy path : current pwd correct → password mis à jour, re-login OK."""
    suffix = secrets.token_hex(4)
    email = f"chpwd-ok-{suffix}@example.com"
    old_pwd = "old-password-123"
    new_pwd = "new-password-456"

    await client.post("/auth/register", json={"email": email, "password": old_pwd})
    await client.post("/auth/login", data={"username": email, "password": old_pwd})

    resp = await client.post(
        "/users/me/change-password",
        json={"current_password": old_pwd, "new_password": new_pwd},
    )
    assert resp.status_code == 204

    # Logout, puis re-login avec le NEW password
    await client.post("/auth/logout")
    login = await client.post("/auth/login", data={"username": email, "password": new_pwd})
    assert login.status_code in (200, 204)


@pytest.mark.integration
async def test_change_password_wrong_current_returns_400(client):
    """Mauvais current_password → 400."""
    suffix = secrets.token_hex(4)
    email = f"chpwd-bad-{suffix}@example.com"
    pwd = "real-password-123"

    await client.post("/auth/register", json={"email": email, "password": pwd})
    await client.post("/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/users/me/change-password",
        json={"current_password": "wrong", "new_password": "new-password-456"},
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_change_password_requires_auth(client):
    """Sans cookie → 401."""
    await client.post("/auth/logout")
    resp = await client.post(
        "/users/me/change-password",
        json={"current_password": "x", "new_password": "yy"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_change_password_too_short_returns_422(client):
    """new_password < 8 chars → 422 (Pydantic validation)."""
    suffix = secrets.token_hex(4)
    email = f"chpwd-short-{suffix}@example.com"
    pwd = "valid-password-123"

    await client.post("/auth/register", json={"email": email, "password": pwd})
    await client.post("/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/users/me/change-password",
        json={"current_password": pwd, "new_password": "short"},
    )
    assert resp.status_code == 422


# ── Delete account ────────────────────────────────────────────────────


@pytest.mark.integration
async def test_delete_account_happy_path(client):
    """Delete account avec confirmation + password → 204, user gone."""
    suffix = secrets.token_hex(4)
    email = f"delete-{suffix}@example.com"
    pwd = "delete-password-123"

    await client.post("/auth/register", json={"email": email, "password": pwd})
    await client.post("/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/users/me/delete-account",
        json={"confirmation": "DELETE", "current_password": pwd},
    )
    assert resp.status_code == 204

    # Re-login doit fail (user gone)
    login = await client.post("/auth/login", data={"username": email, "password": pwd})
    assert login.status_code in (400, 401, 422)


@pytest.mark.integration
async def test_delete_account_wrong_confirmation_returns_400(client):
    """confirmation != 'DELETE' → 400."""
    suffix = secrets.token_hex(4)
    email = f"delete-bad-{suffix}@example.com"
    pwd = "delete-password-123"

    await client.post("/auth/register", json={"email": email, "password": pwd})
    await client.post("/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/users/me/delete-account",
        json={"confirmation": "delete", "current_password": pwd},  # lowercase
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_delete_account_wrong_password_returns_400(client):
    """Mauvais password → 400, user toujours là."""
    suffix = secrets.token_hex(4)
    email = f"delete-wrongpwd-{suffix}@example.com"
    pwd = "delete-password-123"

    await client.post("/auth/register", json={"email": email, "password": pwd})
    await client.post("/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/users/me/delete-account",
        json={"confirmation": "DELETE", "current_password": "wrong"},
    )
    assert resp.status_code == 400

    # User est toujours là
    me = await client.get("/users/me")
    assert me.status_code == 200


@pytest.mark.integration
async def test_delete_account_requires_auth(client):
    """Sans cookie → 401."""
    await client.post("/auth/logout")
    resp = await client.post(
        "/users/me/delete-account",
        json={"confirmation": "DELETE"},
    )
    assert resp.status_code == 401
