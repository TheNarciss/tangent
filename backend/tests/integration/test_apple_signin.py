"""Sign in with Apple, on the site and from the phone (ADR-035).

Apple itself is never called: its published key is replaced by one made
here, and the code exchange by a stub returning an id_token signed with it.
"""

from __future__ import annotations

import base64
import time
import uuid
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import apple
from app.auth import session as app_session
from app.auth.backend import COOKIE_NAME

_RSA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC = _RSA.public_key()


def _id_token(
    email: str,
    *,
    sub: str | None = None,
    verified: object = "true",
    aud: str | None = None,
    **extra,
) -> str:
    now = int(time.time())
    claims = {
        "iss": apple.ISSUER,
        "aud": aud or apple.CLIENT_ID,
        "iat": now,
        "exp": now + 600,
        "sub": sub or f"apple-{uuid.uuid4().hex[:12]}",
        "email": email,
        "email_verified": verified,
        **extra,
    }
    return jwt.encode(claims, _RSA, algorithm="RS256", headers={"kid": "test-kid"})


@pytest.fixture(autouse=True)
def _apple_keys(monkeypatch):
    monkeypatch.setattr(apple, "signing_key", lambda _token: _PUBLIC)


# ── The pieces ──────────────────────────────────────────────────────────


def test_client_secret_is_signed_with_the_developer_key():
    secret = apple.client_secret(now=time.time())
    pem = base64.b64decode(apple.PRIVATE_KEY_B64)
    public = serialization.load_pem_private_key(pem, None).public_key()
    claims = jwt.decode(secret, public, algorithms=["ES256"], audience=apple.ISSUER)
    assert claims["iss"] == apple.TEAM_ID and claims["sub"] == apple.CLIENT_ID
    assert jwt.get_unverified_header(secret)["kid"] == apple.KEY_ID
    assert claims["exp"] - claims["iat"] == apple.CLIENT_SECRET_LIFETIME


def test_verify_id_token_accepts_site_and_app_audiences_and_refuses_the_rest():
    ident = apple.verify_id_token(_id_token("a@b.c", aud=apple.CLIENT_ID, verified=True))
    assert ident.email == "a@b.c" and ident.email_verified
    assert apple.verify_id_token(_id_token("a@b.c", aud=apple.BUNDLE_ID)).sub.startswith("apple-")
    with pytest.raises(ValueError):
        apple.verify_id_token(_id_token("a@b.c", aud="someone-else"))
    with pytest.raises(ValueError):
        apple.verify_id_token(_id_token("a@b.c", verified="false"))
    with pytest.raises(ValueError, match="nonce"):
        apple.verify_id_token(_id_token("a@b.c", nonce="n1"), nonce="n2")
    assert apple.verify_id_token(_id_token("a@b.c", nonce="n1"), nonce="n1").email == "a@b.c"


# ── The site ────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_authorize_gives_the_apple_url_and_a_csrf_cookie(client):
    client.cookies.clear()
    resp = await client.get("/api/auth/apple/authorize")
    assert resp.status_code == 200
    url = resp.json()["authorization_url"]
    assert url.startswith(apple.AUTHORIZE_URL)
    assert "response_mode=form_post" in url and f"client_id={apple.CLIENT_ID}" in url
    assert apple.CSRF_COOKIE in resp.headers.get("set-cookie", "")
    client.cookies.clear()


@pytest.mark.integration
async def test_callback_opens_the_session_and_sends_the_site_home(client, monkeypatch):
    email = f"apple-web-{uuid.uuid4().hex[:8]}@test.com"

    async def fake_exchange(code: str) -> dict:
        assert code == "the-code"
        return {"id_token": _id_token(email), "access_token": "at"}

    monkeypatch.setattr(apple, "exchange_code", fake_exchange)
    client.cookies.clear()
    state = parse_qs(
        urlparse((await client.get("/api/auth/apple/authorize")).json()["authorization_url"]).query
    )["state"][0]

    resp = await client.post(
        "/api/auth/apple/callback",
        data={"code": "the-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    assert resp.headers["location"].endswith("/?oauth=success")
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")
    me = await client.get("/api/users/me")
    assert me.status_code == 200 and me.json()["email"] == email
    client.cookies.clear()


@pytest.mark.integration
async def test_callback_without_the_csrf_cookie_or_with_a_bad_state_fails_safely(client):
    client.cookies.clear()
    state = parse_qs(
        urlparse((await client.get("/api/auth/apple/authorize")).json()["authorization_url"]).query
    )["state"][0]
    client.cookies.clear()  # the cookie Apple's POST would have to carry is gone
    resp = await client.post(
        "/api/auth/apple/callback", data={"code": "c", "state": state}, follow_redirects=False
    )
    assert resp.status_code == 303 and "oauth_error=state" in resp.headers["location"]
    assert COOKIE_NAME not in resp.headers.get("set-cookie", "")
    resp = await client.post(
        "/api/auth/apple/callback", data={"code": "c", "state": "junk"}, follow_redirects=False
    )
    assert "oauth_error=state" in resp.headers["location"]


# ── The app ─────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_native_id_token_opens_the_session_and_finds_the_same_person_again(client):
    email = f"apple-native-{uuid.uuid4().hex[:8]}@test.com"
    sub = f"apple-{uuid.uuid4().hex[:12]}"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/apple/native",
        json={
            "identity_token": _id_token(email, sub=sub, aud=apple.BUNDLE_ID, nonce="n"),
            "nonce": "n",
        },
    )
    assert resp.status_code == 204, resp.text
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")
    first = (await client.get("/api/users/me")).json()
    assert first["email"] == email

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/apple/native",
        json={"identity_token": _id_token(email, sub=sub, aud=apple.BUNDLE_ID)},
    )
    assert resp.status_code == 204
    assert (await client.get("/api/users/me")).json()["id"] == first["id"]
    client.cookies.clear()


@pytest.mark.integration
async def test_native_refuses_a_forged_or_unverified_token(client):
    client.cookies.clear()
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(
        {
            "iss": apple.ISSUER,
            "aud": apple.BUNDLE_ID,
            "exp": int(time.time()) + 60,
            "sub": "x",
            "email": "x@y.z",
            "email_verified": True,
        },
        other,
        algorithm="RS256",
    )
    assert (
        await client.post("/api/auth/apple/native", json={"identity_token": forged})
    ).status_code == 400
    unverified = _id_token("u@v.w", aud=apple.BUNDLE_ID, verified=False)
    assert (
        await client.post("/api/auth/apple/native", json={"identity_token": unverified})
    ).status_code == 400


@pytest.mark.integration
async def test_app_start_and_callback_hand_back_an_exchange_code(client, monkeypatch):
    email = f"apple-app-{uuid.uuid4().hex[:8]}@test.com"
    verifier = "q" * 64

    async def fake_exchange(code: str) -> dict:
        return {"id_token": _id_token(email)}

    monkeypatch.setattr(apple, "exchange_code", fake_exchange)
    client.cookies.clear()
    start = await client.get(
        f"/api/auth/apple/start?challenge={app_session.challenge_of(verifier)}",
        follow_redirects=False,
    )
    assert start.status_code == 302 and start.headers["location"].startswith(apple.AUTHORIZE_URL)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    resp = await client.post(
        "/api/auth/apple/callback", data={"code": "c", "state": state}, follow_redirects=False
    )
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert (
        location.startswith(f"{app_session.APP_RETURN_BASE}auth?") and COOKIE_NAME not in location
    )
    code = parse_qs(urlparse(location).query)["code"][0]
    user_id = app_session.redeem_exchange_code(code, verifier)
    session_cookie = resp.headers.get("set-cookie", "")
    assert (
        COOKIE_NAME not in session_cookie
    )  # the app gets a code, never the cookie, through the browser

    client.cookies.clear()
    code = app_session.mint_exchange_code(user_id, app_session.challenge_of(verifier))
    assert (
        await client.post("/api/auth/exchange", json={"code": code, "verifier": verifier})
    ).status_code == 204
    assert (await client.get("/api/users/me")).json()["email"] == email
    client.cookies.clear()


@pytest.mark.integration
async def test_providers_says_which_buttons_to_show(client):
    resp = await client.get("/api/auth/providers")
    assert resp.status_code == 200
    assert resp.json() == {"google": True, "apple": True}


@pytest.mark.integration
async def test_an_apple_only_account_has_no_password_and_can_be_deleted(client):
    email = f"apple-delete-{uuid.uuid4().hex[:8]}@test.com"
    client.cookies.clear()
    resp = await client.post(
        "/api/auth/apple/native", json={"identity_token": _id_token(email, aud=apple.BUNDLE_ID)}
    )
    assert resp.status_code == 204
    me = (await client.get("/api/users/me")).json()
    assert me["has_password"] is False

    # A password form for this address is refused, never a 500.
    client.cookies.clear()
    login = await client.post("/api/auth/login", data={"username": email, "password": "anything1"})
    assert login.status_code == 400

    # Back in through Apple, the account deletes with the confirmation alone (Apple 5.1.1).
    resp = await client.post(
        "/api/auth/apple/native", json={"identity_token": _id_token(email, aud=apple.BUNDLE_ID)}
    )
    assert resp.status_code == 204
    resp = await client.post("/api/users/me/delete-account", json={"confirmation": "DELETE"})
    assert resp.status_code == 204, resp.text
    assert (await client.get("/api/users/me")).status_code == 401
    client.cookies.clear()
