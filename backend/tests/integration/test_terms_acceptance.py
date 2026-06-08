"""Tests d'intégration pour l'acceptation des CGU."""

import secrets

import pytest

from app.auth.terms_version import CURRENT_TERMS_VERSION


@pytest.mark.integration
async def test_terms_version_endpoint_is_public(client):
    """GET /auth/terms-version doit fonctionner sans auth."""
    await client.post("/api/auth/logout")
    resp = await client.get("/api/auth/terms-version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == CURRENT_TERMS_VERSION


@pytest.mark.integration
async def test_new_user_has_no_terms_accepted(client):
    """Un user fraîchement créé a terms_version_accepted = None."""
    suffix = secrets.token_hex(4)
    email = f"new-terms-{suffix}@example.com"
    pwd = "test-password-12345"

    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})

    me = await client.get("/api/users/me")
    assert me.status_code == 200
    data = me.json()
    assert data.get("terms_version_accepted") is None
    assert data.get("terms_accepted_at") is None


@pytest.mark.integration
async def test_accept_terms_sets_version_and_date(client):
    """POST /users/me/accept-terms persiste version + date."""
    suffix = secrets.token_hex(4)
    email = f"accept-{suffix}@example.com"
    pwd = "test-password-12345"

    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/api/users/me/accept-terms",
        json={"version": CURRENT_TERMS_VERSION},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == CURRENT_TERMS_VERSION
    assert body["accepted_at"] is not None

    # Vérifie persistance via /users/me
    me = await client.get("/api/users/me")
    assert me.json()["terms_version_accepted"] == CURRENT_TERMS_VERSION


@pytest.mark.integration
async def test_accept_wrong_version_returns_409(client):
    """Si le client envoie une version obsolète → 409 conflict."""
    suffix = secrets.token_hex(4)
    email = f"wrongver-{suffix}@example.com"
    pwd = "test-password-12345"

    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    await client.post("/api/auth/login", data={"username": email, "password": pwd})

    resp = await client.post(
        "/api/users/me/accept-terms",
        json={"version": "1999-01-01"},
    )
    assert resp.status_code == 409


@pytest.mark.integration
async def test_accept_terms_requires_auth(client):
    """POST /users/me/accept-terms sans cookie → 401."""
    await client.post("/api/auth/logout")
    resp = await client.post(
        "/api/users/me/accept-terms",
        json={"version": CURRENT_TERMS_VERSION},
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_terms_acceptance_isolated_between_users(client):
    """ADR-002 §5 : user A accepte ne fait pas accepter user B."""
    suffix_a = secrets.token_hex(4)
    suffix_b = secrets.token_hex(4)
    email_a = f"iso-a-{suffix_a}@example.com"
    email_b = f"iso-b-{suffix_b}@example.com"
    pwd = "test-password-12345"

    await client.post("/api/auth/register", json={"email": email_a, "password": pwd})
    await client.post("/api/auth/register", json={"email": email_b, "password": pwd})

    # User A accepte
    await client.post("/api/auth/login", data={"username": email_a, "password": pwd})
    await client.post(
        "/api/users/me/accept-terms",
        json={"version": CURRENT_TERMS_VERSION},
    )

    # User B regarde son état — ne doit PAS être impacté
    await client.post("/api/auth/logout")
    await client.post("/api/auth/login", data={"username": email_b, "password": pwd})
    me_b = await client.get("/api/users/me")
    assert me_b.json()["terms_version_accepted"] is None
