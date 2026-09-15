"""The app's way in: the browser start, the exchange, the renewal (ADR-035)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.auth import session as app_session
from app.auth.backend import COOKIE_NAME
from app.db.engine import async_session_factory


async def _register(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPwd123!", "display_name": "app"},
    )
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


@pytest.mark.integration
async def test_app_google_start_sends_the_browser_to_google_with_the_csrf_cookie(client):
    client.cookies.clear()
    challenge = app_session.challenge_of("v" * 64)
    resp = await client.get(
        f"/api/auth/app/google/start?challenge={challenge}", follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://accounts.google.com/o/oauth2")
    assert "redirect_uri=" in resp.headers["location"]
    assert "fastapiusersoauthcsrf" in resp.headers.get("set-cookie", "")
    client.cookies.clear()


@pytest.mark.integration
async def test_app_google_start_refuses_a_bad_challenge(client):
    resp = await client.get("/api/auth/app/google/start?challenge=short", follow_redirects=False)
    assert resp.status_code == 422


@pytest.mark.integration
async def test_exchange_opens_the_session_once(client):
    user_id = await _register(client, f"app-exchange-{uuid.uuid4().hex[:8]}@test.com")
    verifier = "w" * 64
    code = app_session.mint_exchange_code(user_id, app_session.challenge_of(verifier))

    resp = await client.post("/api/auth/exchange", json={"code": code, "verifier": verifier})
    assert resp.status_code == 204, resp.text
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")
    me = await client.get("/api/users/me")
    assert me.status_code == 200 and me.json()["id"] == str(user_id)

    client.cookies.clear()
    again = await client.post("/api/auth/exchange", json={"code": code, "verifier": verifier})
    assert again.status_code == 400


@pytest.mark.integration
async def test_exchange_refuses_the_wrong_verifier(client):
    user_id = await _register(client, f"app-verifier-{uuid.uuid4().hex[:8]}@test.com")
    code = app_session.mint_exchange_code(user_id, app_session.challenge_of("x" * 64))
    resp = await client.post("/api/auth/exchange", json={"code": code, "verifier": "y" * 64})
    assert resp.status_code == 400
    assert COOKIE_NAME not in resp.headers.get("set-cookie", "")


@pytest.mark.integration
async def test_users_me_renews_an_ageing_session(client, monkeypatch):
    email = f"app-renew-{uuid.uuid4().hex[:8]}@test.com"
    await _register(client, email)
    resp = await client.post("/api/auth/login", data={"username": email, "password": "TestPwd123!"})
    assert resp.status_code == 204
    first = client.cookies.get(COOKIE_NAME)

    # Young token: nothing happens.
    resp = await client.get("/api/users/me")
    assert resp.status_code == 200 and "set-cookie" not in resp.headers

    # Past the threshold: the same route hands back a fresh cookie.
    monkeypatch.setattr(app_session, "RENEW_AFTER_SECONDS", 0)
    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    assert COOKIE_NAME in resp.headers.get("set-cookie", "")
    assert client.cookies.get(COOKIE_NAME) != first
    assert (await client.get("/api/users/me")).status_code == 200
    client.cookies.clear()


@pytest.mark.integration
async def test_app_callback_turns_the_cookie_into_a_code_bound_to_the_challenge(client):
    from urllib.parse import parse_qs, urlparse

    from fastapi import Response
    from fastapi.requests import Request
    from fastapi_users.jwt import generate_jwt
    from fastapi_users.router.oauth import CSRF_TOKEN_KEY, generate_state_token

    from app.auth.app_router import CHALLENGE_KEY
    from app.auth.backend import COOKIE_LIFETIME, JWT_SECRET
    from app.auth.oauth_router import OAUTH_STATE_SECRET
    from app.main import _app_callback_to_redirect

    user_id = uuid.uuid4()
    verifier = "z" * 64
    state = generate_state_token(
        {CSRF_TOKEN_KEY: "csrf", CHALLENGE_KEY: app_session.challenge_of(verifier)},
        OAUTH_STATE_SECRET,
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "query_string": f"state={state}".encode(),
            "headers": [],
        }
    )
    token = generate_jwt(
        {"sub": str(user_id), "aud": app_session.SESSION_AUDIENCE}, JWT_SECRET, COOKIE_LIFETIME
    )
    upstream = Response(status_code=204)
    upstream.set_cookie(COOKIE_NAME, token, httponly=True)

    redirect = _app_callback_to_redirect(request, upstream)
    assert redirect.status_code == 303
    location = redirect.headers["location"]
    assert location.startswith(f"{app_session.APP_RETURN_BASE}auth?")
    assert COOKIE_NAME not in location and token not in location
    code = parse_qs(urlparse(location).query)["code"][0]
    assert app_session.redeem_exchange_code(code, verifier) == user_id

    failed = _app_callback_to_redirect(request, Response(status_code=400))
    assert failed.headers["location"] == app_session.app_return("auth", error="400")
