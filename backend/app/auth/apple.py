"""Sign in with Apple (ADR-035): the web flow and the phone's native flow, one backend.

Apple is not Google. It answers the web flow by a cross-site **POST** (its
`form_post` mode, mandatory when the email scope is asked for), it proves
the identity with an `id_token` signed by keys it publishes, and it does
not hand out a client secret: the server signs one itself, with the `.p8`
key from the developer account. On the phone the app gets the same
`id_token` natively and posts it here; no browser, no code exchange.

Everything the site and the app share about a person ends in the same
place: `UserManager.oauth_callback`, the provider named `apple`, the user
matched by verified email like Google (ADR-014).

Configuration (backend/.env): APPLE_TEAM_ID, APPLE_KEY_ID,
APPLE_PRIVATE_KEY_B64 (the .p8, base64 in one line), APPLE_CLIENT_ID (the
Services ID the site uses), APPLE_BUNDLE_ID (the app).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt, generate_jwt
from fastapi_users.router.oauth import STATE_TOKEN_AUDIENCE
from pydantic import BaseModel

from . import session as app_session
from .backend import COOKIE_SECURE, auth_backend
from .manager import get_user_manager
from .oauth_router import OAUTH_STATE_SECRET

logger = logging.getLogger(__name__)

PROVIDER = "apple"
AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
TOKEN_URL = "https://appleid.apple.com/auth/token"
KEYS_URL = "https://appleid.apple.com/auth/keys"
ISSUER = "https://appleid.apple.com"
CSRF_COOKIE = "tangent_apple_csrf"
STATE_LIFETIME = 600
CLIENT_SECRET_LIFETIME = 3600  # Apple allows up to six months; an hour is plenty for one exchange

TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
KEY_ID = os.getenv("APPLE_KEY_ID", "")
PRIVATE_KEY_B64 = os.getenv("APPLE_PRIVATE_KEY_B64", "")
CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")  # the Services ID, for the web flow
BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", "")  # the app, for the native flow
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CALLBACK_PATH = "/api/auth/apple/callback"


def is_configured() -> bool:
    return all((TEAM_ID, KEY_ID, PRIVATE_KEY_B64, CLIENT_ID))


def audiences() -> list[str]:
    """Who an id_token may be for: the site's Services ID and the app's bundle."""
    return [a for a in (CLIENT_ID, BUNDLE_ID) if a]


# ── The secret the server signs itself ──────────────────────────────────────


def client_secret(*, now: float | None = None) -> str:
    """Apple's client secret is a JWT signed with the developer key (ES256)."""
    key = base64.b64decode(PRIVATE_KEY_B64).decode()
    now = now if now is not None else time.time()
    return jwt.encode(
        {
            "iss": TEAM_ID,
            "iat": int(now),
            "exp": int(now) + CLIENT_SECRET_LIFETIME,
            "aud": ISSUER,
            "sub": CLIENT_ID,
        },
        key,
        algorithm="ES256",
        headers={"kid": KEY_ID},
    )


# ── Verifying what Apple says about a person ─────────────────────────────


_jwks = jwt.PyJWKClient(KEYS_URL, cache_keys=True, lifespan=24 * 3600)


def signing_key(id_token: str) -> Any:
    """The public key that signed this token, from Apple's published set (cached)."""
    return _jwks.get_signing_key_from_jwt(id_token).key


class AppleIdentity(BaseModel):
    sub: str
    email: str
    email_verified: bool


def verify_id_token(id_token: str, *, nonce: str | None = None) -> AppleIdentity:
    """The identity behind an Apple id_token, or ValueError.

    Signature by an Apple key, issuer, audience among ours, not expired; the
    email must be there and verified (Apple relays a private relay address
    when the person hides theirs: it is verified all the same).
    """
    try:
        claims = jwt.decode(
            id_token,
            signing_key(id_token),
            algorithms=["RS256"],
            audience=audiences(),
            issuer=ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"id_token Apple refusé : {exc}") from exc
    if nonce is not None and claims.get("nonce") != nonce:
        raise ValueError("nonce Apple incorrect")
    email = claims.get("email")
    verified = claims.get("email_verified", False)
    verified = verified is True or str(verified).lower() == "true"
    if not email or not verified:
        logger.warning(
            "AUDIT OAUTH_LINK_REJECTED_UNVERIFIED_EMAIL oauth_name=apple email=%s", email
        )
        raise ValueError("Adresse e-mail Apple absente ou non vérifiée.")
    return AppleIdentity(sub=str(claims["sub"]), email=str(email), email_verified=True)


async def _login(
    identity: AppleIdentity, token: str, request: Request, user_manager, strategy
) -> Response:
    """The shared tail: find or create the person, open the session."""
    try:
        user = await user_manager.oauth_callback(
            PROVIDER,
            token,
            identity.sub,
            identity.email,
            None,
            None,
            request,
            associate_by_email=True,
            is_verified_by_default=True,
        )
    except UserAlreadyExists as exc:
        raise HTTPException(status_code=400, detail="OAUTH_USER_ALREADY_EXISTS") from exc
    if not user.is_active:
        raise HTTPException(status_code=400, detail="LOGIN_BAD_CREDENTIALS")
    response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, response)
    return response


# ── Routes ──────────────────────────────────────────────────────────────


class NativeIn(BaseModel):
    identity_token: str
    nonce: str | None = None


def build_router() -> APIRouter:
    router = APIRouter()

    def _authorize_url(state: str) -> str:
        return (
            f"{AUTHORIZE_URL}?response_type=code&response_mode=form_post"
            f"&client_id={CLIENT_ID}&redirect_uri={BACKEND_URL}{CALLBACK_PATH}"
            f"&scope=name%20email&state={state}"
        )

    def _csrf_cookie(response: Response, csrf: str) -> None:
        # Apple comes back by a cross-site POST: only a SameSite=None cookie travels with it.
        response.set_cookie(
            CSRF_COOKIE,
            csrf,
            max_age=STATE_LIFETIME,
            path="/",
            secure=COOKIE_SECURE,
            httponly=True,
            samesite="none" if COOKIE_SECURE else "lax",
        )

    @router.get("/authorize")
    async def authorize(response: Response) -> dict[str, str]:
        """The site: where to send the browser (same contract as Google's /authorize)."""
        csrf = secrets.token_urlsafe(16)
        state = generate_jwt(
            {"csrftoken": csrf, "aud": STATE_TOKEN_AUDIENCE}, OAUTH_STATE_SECRET, STATE_LIFETIME
        )
        _csrf_cookie(response, csrf)
        return {"authorization_url": _authorize_url(state)}

    @router.get("/start")
    async def start(challenge: str = Query(...)) -> RedirectResponse:
        """The app, through the system browser: same as Google's app start (ADR-035)."""
        if not app_session.is_challenge(challenge):
            raise HTTPException(status_code=422, detail="challenge invalide")
        csrf = secrets.token_urlsafe(16)
        state = generate_jwt(
            {"csrftoken": csrf, "chal": challenge, "aud": STATE_TOKEN_AUDIENCE},
            OAUTH_STATE_SECRET,
            STATE_LIFETIME,
        )
        response = RedirectResponse(url=_authorize_url(state), status_code=302)
        _csrf_cookie(response, csrf)
        return response

    @router.post("/callback")
    async def callback(
        request: Request,
        code: str | None = Form(None),
        state: str | None = Form(None),
        error: str | None = Form(None),
        user_manager=Depends(get_user_manager),
        strategy=Depends(auth_backend.get_strategy),
    ) -> Response:
        """Apple posts the code here; the session opens, then back to the site or the app."""
        try:
            state_data = decode_jwt(state or "", OAUTH_STATE_SECRET, [STATE_TOKEN_AUDIENCE])
        except jwt.PyJWTError:
            return _back(None, error="state")
        challenge = state_data.get("chal")
        csrf = request.cookies.get(CSRF_COOKIE)
        if not csrf or not secrets.compare_digest(csrf, str(state_data.get("csrftoken", ""))):
            return _back(challenge, error="state")
        if error or not code:
            return _back(challenge, error=error or "no_code")
        try:
            tokens = await exchange_code(code)
            identity = verify_id_token(tokens["id_token"])
        except (ValueError, KeyError, httpx.HTTPError) as exc:
            logger.warning("Sign in with Apple: %s", exc)
            return _back(challenge, error="apple")
        try:
            opened = await _login(
                identity, tokens.get("access_token") or "apple", request, user_manager, strategy
            )
        except HTTPException as exc:
            return _back(challenge, error=str(exc.status_code))
        token = _cookie_value(opened)
        if challenge and token:
            claims = decode_jwt(token, app_session.JWT_SECRET, [app_session.SESSION_AUDIENCE])
            back: Response = RedirectResponse(
                url=app_session.app_return(
                    "auth", code=app_session.mint_exchange_code(claims["sub"], challenge)
                ),
                status_code=303,
            )
        else:
            back = RedirectResponse(url=f"{FRONTEND_URL}/?oauth=success", status_code=303)
            for name, value in opened.raw_headers:
                if name.lower() == b"set-cookie":
                    back.raw_headers.append((name, value))
        back.delete_cookie(CSRF_COOKIE, path="/")
        return back

    @router.post("/native", status_code=204)
    async def native(
        body: NativeIn,
        request: Request,
        user_manager=Depends(get_user_manager),
        strategy=Depends(auth_backend.get_strategy),
    ) -> Response:
        """The app got the id_token from iOS itself: verify it, open the session."""
        try:
            identity = verify_id_token(body.identity_token, nonce=body.nonce)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return await _login(identity, "apple-native", request, user_manager, strategy)

    return router


async def exchange_code(code: str) -> dict[str, Any]:
    """Apple's token endpoint: the code and our self-signed secret for the tokens."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{BACKEND_URL}{CALLBACK_PATH}",
            },
        )
    if response.status_code >= 400:
        raise ValueError(f"échange du code refusé ({response.status_code}): {response.text[:200]}")
    return dict(json.loads(response.text))


def _cookie_value(response: Response) -> str | None:
    from .backend import COOKIE_NAME

    prefix = f"{COOKIE_NAME}=".encode()
    for name, value in response.raw_headers:
        if name.lower() == b"set-cookie" and value.startswith(prefix):
            return value[len(prefix) :].split(b";", 1)[0].decode()
    return None


def _back(challenge: str | None, *, error: str) -> RedirectResponse:
    """Where a failed attempt lands: the app when the flow was the app's, else the site."""
    if challenge:
        return RedirectResponse(url=app_session.app_return("auth", error=error), status_code=303)
    return RedirectResponse(url=f"{FRONTEND_URL}/?oauth_error={error}", status_code=303)


__all__ = [
    "AppleIdentity",
    "build_router",
    "client_secret",
    "exchange_code",
    "is_configured",
    "verify_id_token",
]
