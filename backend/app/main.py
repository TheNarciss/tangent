"""FastAPI entry point — mount routers + middlewares + lifespan.

Endpoint business logic lives in app/routers/. main.py is intentionally thin.
"""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from time import time as _now

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from . import logging_config
from .auth import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users
from .auth.oauth_router import (
    build_google_associate_router,
    build_google_login_router,
    is_oauth_configured,
)
from .db import ping as db_ping
from .db.init_db import init_db
from .errors import AppError
from .routers import (
    account,
    accounts,
    admin,
    analysis,
    dashboard,
    envelopes,
    oauth_accounts,
    password_reset,
    planning,
    powens,
    profile,
    reviews,
    terms,
    watchlist,
)

logging_config.configure()
logger = logging.getLogger("app")


# ─── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_: FastAPI):
    """App lifespan: init DB schema at startup."""
    try:
        await init_db()
    except Exception:
        logger.exception("Failed to initialize DB schema at startup")
    yield


app = FastAPI(title="Portfolio Dashboard", version="0.9.0", lifespan=lifespan)


# ─── Rate limiter (sliding window) ────────────────────────────────────────
_AUTH_RATE_LIMITS = {
    "/auth/login": (5, 60),
    "/auth/register": (3, 3600),
    "/auth/forgot-password": (3, 3600),
    "/auth/reset-password": (5, 3600),
    "/auth/password-reset/request": (3, 3600),
    "/auth/password-reset/verify": (10, 3600),
    "/auth/password-reset/confirm": (5, 3600),
}
_attempts: dict[tuple[str, str], list[float]] = defaultdict(list)


@app.middleware("http")
async def apply_auth_rate_limits(request: Request, call_next):
    """Sliding-window rate limit on sensitive auth routes."""
    if request.method == "POST" and request.url.path in _AUTH_RATE_LIMITS:
        max_count, window_seconds = _AUTH_RATE_LIMITS[request.url.path]
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, request.url.path)
        now = _now()
        _attempts[key] = [t for t in _attempts[key] if now - t < window_seconds]
        if len(_attempts[key]) >= max_count:
            retry_after = int(window_seconds - (now - _attempts[key][0]))
            logger.warning(
                "Rate limit hit: ip=%s path=%s (%d attempts in %ds)",
                client_ip,
                request.url.path,
                len(_attempts[key]),
                window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many attempts. Retry in {retry_after}s.",
                    "type": "RateLimitExceeded",
                },
                headers={"Retry-After": str(retry_after)},
            )
        _attempts[key].append(now)
    return await call_next(request)


# ─── OAuth callback redirect middleware (cf ADR-014) ──────────────────────
# fastapi-users OAuth callback retourne un 204 No Content avec Set-Cookie.
# Pour une UX correcte (l'user vient d'une nav full-page depuis Google),
# on convertit ce 204 en 303 redirect vers le frontend, en préservant les
# cookies du auth_backend (CookieTransport).
@app.middleware("http")
async def oauth_callback_to_redirect(request: Request, call_next):
    response = await call_next(request)

    if request.url.path not in {
        "/auth/google/callback",
        "/auth/associate/google/callback",
    }:
        return response

    frontend = os.getenv("FRONTEND_URL", "/").rstrip("/")

    if response.status_code == 204:
        # Succès : cookie set, redirect vers le home frontend avec flag
        redirect = RedirectResponse(
            url=f"{frontend}/?oauth=success",
            status_code=303,
        )
        # Préserve les Set-Cookie du CookieTransport
        for header_name, header_value in response.raw_headers:
            if header_name.lower() == b"set-cookie":
                redirect.raw_headers.append((header_name, header_value))
        return redirect

    if response.status_code >= 400:
        # Échec : redirect avec code d'erreur (le body JSON est perdu mais
        # le frontend peut afficher un message générique selon le code)
        return RedirectResponse(
            url=f"{frontend}/?oauth_error={response.status_code}",
            status_code=303,
        )

    return response


# ─── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        if o.strip()
    ],
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Hardening HTTP headers — defense in depth against XSS, clickjacking, MIME sniffing."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), interest-cohort=()"
    )
    if os.getenv("ENV", "dev") == "prod":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.biapi.pro https://api.resend.com "
            "https://accounts.google.com https://oauth2.googleapis.com "
            "https://openidconnect.googleapis.com; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none'"
        )
    return response


# ─── Request tracing middleware ───────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled exception in %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.0f ms)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response


# ─── Health check ─────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    """Health endpoint — checked by Docker."""
    db_ok = await db_ping()
    return {"status": "ok", "db": "up" if db_ok else "down"}


# ─── Auth routes (FastAPI-Users) ──────────────────────────────────────────
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"])
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
)
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)

# ─── OAuth routes (Google, cf ADR-014) ────────────────────────────────────
if is_oauth_configured():
    app.include_router(
        build_google_login_router(),
        prefix="/auth/google",
        tags=["auth"],
    )
    app.include_router(
        build_google_associate_router(),
        prefix="/auth/associate/google",
        tags=["auth"],
    )
    logger.info("OAuth Google routers mounted (ADR-014)")
else:
    logger.warning(
        "OAuth Google not configured — endpoints disabled. "
        "Set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, "
        "OAUTH_STATE_SECRET, FRONTEND_URL in backend/.env to enable."
    )


# ─── Business routers (all require auth via current_active_user) ──────────
app.include_router(accounts.router)
app.include_router(password_reset.router)
app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(planning.router)
app.include_router(watchlist.router)
app.include_router(envelopes.router)
app.include_router(powens.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(account.router)
app.include_router(terms.router)
app.include_router(oauth_accounts.router)
app.include_router(reviews.router)


# ─── Exception handlers ───────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("%s on %s: %s", type(exc).__name__, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": type(exc).__name__},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "type": type(exc).__name__},
    )
