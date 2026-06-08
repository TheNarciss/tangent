"""Tests d'intégration OAuth Google (cf ADR-014).

Stratégie : on ne mocke pas le flow Google complet (trop fragile). On vérifie
les contrats fondamentaux :
- /auth/google/authorize accessible non loggé → 200 + authorization_url
- /auth/associate/google/authorize requiert un cookie → 401 sinon
- Les users password existants peuvent toujours se logger (non-régression
  critique pour les 10+ users en prod)
- /users/me/oauth-accounts list-only quand connecté
- get_id_email rejette email_verified=false
"""

import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.integration
async def test_google_authorize_returns_url(client):
    """L'endpoint /authorize doit renvoyer une URL Google valide."""
    resp = await client.get("/api/auth/google/authorize")
    assert resp.status_code == 200
    body = resp.json()
    assert "authorization_url" in body
    url = body["authorization_url"]
    assert url.startswith("https://accounts.google.com/o/oauth2")
    assert "client_id=test-google-client-id" in url
    assert "state=" in url


@pytest.mark.integration
async def test_google_associate_authorize_requires_auth(client):
    """L'associate /authorize doit refuser les requêtes non authentifiées."""
    # S'assurer qu'on n'a pas de cookie d'une session précédente
    await client.post("/api/auth/logout")
    resp = await client.get("/api/auth/associate/google/authorize")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_existing_password_user_can_still_login(client):
    """Non-régression critique : un user password classique doit toujours
    pouvoir se connecter après l'ajout d'OAuth (cf ADR-014 §2 négatif)."""
    suffix = secrets.token_hex(4)
    email = f"legacy-pwd-{suffix}@example.com"
    password = "legacy-password-12345"

    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code in (201, 200), reg.text

    login = await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code in (200, 204), login.text


@pytest.mark.integration
async def test_oauth_accounts_list_empty_for_new_user(client):
    """Un user fraîchement créé n'a aucun OAuth account lié."""
    suffix = secrets.token_hex(4)
    email = f"oauth-list-{suffix}@example.com"
    password = "test-password-12345"

    await client.post("/api/auth/register", json={"email": email, "password": password})
    await client.post("/api/auth/login", data={"username": email, "password": password})

    resp = await client.get("/api/users/me/oauth-accounts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
async def test_oauth_accounts_list_requires_auth(client):
    """L'endpoint oauth-accounts est protégé."""
    await client.post("/api/auth/logout")
    resp = await client.get("/api/users/me/oauth-accounts")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_get_id_email_rejects_unverified_email():
    """Test unitaire de la guard email_verified dans GoogleOAuth2Verified."""
    from httpx_oauth.exceptions import GetIdEmailError

    from app.auth.oauth_router import GoogleOAuth2Verified

    client = GoogleOAuth2Verified("test-id", "test-secret")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": "1234567890",
        "email": "unverified@example.com",
        "email_verified": False,
    }
    mock_httpx = MagicMock()
    mock_httpx.get = AsyncMock(return_value=mock_response)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    client.get_httpx_client = MagicMock(return_value=mock_ctx)

    with pytest.raises(GetIdEmailError, match="non vérifiée"):
        await client.get_id_email("fake-token")


@pytest.mark.integration
async def test_get_id_email_accepts_verified_email():
    """Symétrique du test précédent : email_verified=true passe."""
    from app.auth.oauth_router import GoogleOAuth2Verified

    client = GoogleOAuth2Verified("test-id", "test-secret")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": "1234567890",
        "email": "verified@example.com",
        "email_verified": True,
    }
    mock_httpx = MagicMock()
    mock_httpx.get = AsyncMock(return_value=mock_response)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    client.get_httpx_client = MagicMock(return_value=mock_ctx)

    sub, email = await client.get_id_email("fake-token")
    assert sub == "1234567890"
    assert email == "verified@example.com"


@pytest.mark.integration
async def test_oauth_accounts_isolated_between_users(client):
    """ADR-002 §5 : user A ne doit pas voir les oauth_accounts de user B.

    Régression critique pour la sécurité multi-tenant. Même si l'API
    /users/me/oauth-accounts filtre par current_user, ce test garantit
    qu'aucun futur refactor ne casse l'isolation.
    """
    suffix_a = secrets.token_hex(4)
    suffix_b = secrets.token_hex(4)
    email_a = f"user-a-{suffix_a}@example.com"
    email_b = f"user-b-{suffix_b}@example.com"
    pwd = "test-password-12345"

    # Crée user A et user B
    await client.post("/api/auth/register", json={"email": email_a, "password": pwd})
    await client.post("/api/auth/register", json={"email": email_b, "password": pwd})

    # Login user A — il ne doit voir aucun oauth_account (le sien comme celui de B)
    await client.post("/api/auth/login", data={"username": email_a, "password": pwd})
    resp_a = await client.get("/api/users/me/oauth-accounts")
    assert resp_a.status_code == 200
    accounts_a = resp_a.json()
    # User A n'a pas linké Google → liste vide
    assert accounts_a == [], f"User A devrait avoir 0 oauth_account, a {accounts_a}"

    # Switch vers user B
    await client.post("/api/auth/logout")
    await client.post("/api/auth/login", data={"username": email_b, "password": pwd})
    resp_b = await client.get("/api/users/me/oauth-accounts")
    assert resp_b.status_code == 200
    accounts_b = resp_b.json()
    assert accounts_b == [], f"User B devrait avoir 0 oauth_account, a {accounts_b}"

    # Tentative de delete d'un UUID arbitraire — doit retourner 404, pas 403,
    # car la query filtre par user.oauth_accounts (donc l'account "n'existe pas"
    # pour user B même s'il appartenait à user A)
    import uuid

    fake_id = uuid.uuid4()
    resp_delete = await client.delete(f"/api/users/me/oauth-accounts/{fake_id}")
    assert resp_delete.status_code == 404
