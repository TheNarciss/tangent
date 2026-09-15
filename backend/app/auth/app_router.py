"""Routes the iPhone app uses to log in through the system browser (ADR-035).

- GET  /api/auth/app/google/start?challenge=…  opened in the system browser:
  sets the OAuth CSRF cookie in that browser and sends it to Google.
- GET  /api/auth/app/google/callback            fastapi-users' own callback,
  whose 204 the middleware in main.py turns into a jump back to the app
  carrying a single-use exchange code.
- POST /api/auth/exchange {code, verifier}       called by the app itself:
  opens the session (sets the cookie in the app's native cookie store).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi_users.router.oauth import (
    CSRF_TOKEN_COOKIE_NAME,
    CSRF_TOKEN_KEY,
    generate_csrf_token,
    generate_state_token,
)
from pydantic import BaseModel

from . import fastapi_users
from .backend import COOKIE_SECURE, auth_backend
from .manager import get_user_manager
from .oauth_router import OAUTH_STATE_SECRET, _build_client
from .session import is_challenge, redeem_exchange_code

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
APP_GOOGLE_CALLBACK_PATH = "/api/auth/app/google/callback"
CHALLENGE_KEY = "chal"


def build_app_google_router() -> APIRouter:
    """`/start` plus fastapi-users' `/callback`, both under /api/auth/app/google."""
    client = _build_client()
    router = fastapi_users.get_oauth_router(
        client,
        auth_backend,
        OAUTH_STATE_SECRET,
        redirect_url=f"{BACKEND_URL}{APP_GOOGLE_CALLBACK_PATH}",
        is_verified_by_default=True,
        associate_by_email=True,
    )

    @router.get("/start", name="app_google_start")
    async def start(request: Request, challenge: str = Query(...)) -> RedirectResponse:
        """Meant for a browser, not for fetch: the CSRF cookie must land where the callback lands."""
        if not is_challenge(challenge):
            raise HTTPException(status_code=422, detail="challenge invalide")
        csrf = generate_csrf_token()
        state = generate_state_token(
            {CSRF_TOKEN_KEY: csrf, CHALLENGE_KEY: challenge}, OAUTH_STATE_SECRET
        )
        url = await client.get_authorization_url(f"{BACKEND_URL}{APP_GOOGLE_CALLBACK_PATH}", state)
        response = RedirectResponse(url=url, status_code=302)
        response.set_cookie(
            CSRF_TOKEN_COOKIE_NAME,
            csrf,
            max_age=3600,
            path="/",
            secure=COOKIE_SECURE,
            httponly=True,
            samesite="lax",
        )
        return response

    return router


class ExchangeIn(BaseModel):
    code: str
    verifier: str


def build_exchange_router() -> APIRouter:
    router = APIRouter()

    @router.post("/exchange", status_code=204)
    async def exchange(
        body: ExchangeIn,
        user_manager=Depends(get_user_manager),
        strategy=Depends(auth_backend.get_strategy),
    ) -> Response:
        """The app trades its code and verifier for the session cookie."""
        try:
            user_id = redeem_exchange_code(body.code, body.verifier)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        user = await user_manager.get(user_id)
        if not user.is_active:
            raise HTTPException(status_code=400, detail="compte inactif")
        return await auth_backend.login(strategy, user)

    return router
