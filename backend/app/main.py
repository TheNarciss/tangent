"""FastAPI entry point. HTTP layer + global error handling + request tracing."""
import logging
import time

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import logging_config, portfolio, watchlist
from .finance import bengen, dashboard, envelopes, fees, glide_path, optimizer, projection, scanner, timeseries
from .auth import UserCreate, UserRead, UserUpdate, auth_backend, current_active_user, fastapi_users
from .db import ping as db_ping
from .db.init_db import init_db
from .errors import AppError
from .powens import settings as powens_settings
from .powens import state as powens_state
from .powens.sync import sync_portfolio
from .powens.webhooks import handle_webhook as powens_handle_webhook
from .models import (
    BrokerInfo,
    BrokersResponse,
    DashboardResponse,
    EligibilityRequest,
    EligibleEnvelopesResponse,
    EnvelopeEligibility,
    OptimizerRequest,
    OptimizerResponse,
    Portfolio,
    ProjectionResponse,
    ScanRequest,
    ScanResponse,
    StrategyRequest,
    TimeseriesResponse,
)

logging_config.configure()
logger = logging.getLogger("app")

app = FastAPI(title="Portfolio Dashboard", version="0.7.0")

# ─── Rate limiter (sliding window) ────────────────────────────────────────
# In-house implementation: in-memory tracking of attempts per (IP, path).
# Sufficient for a single backend instance. For horizontal scale, switch to Redis.

from collections import defaultdict
from time import time as _now

_AUTH_RATE_LIMITS = {
    "/auth/login":           (5, 60),         # 5 attempts per 60 seconds
    "/auth/register":        (3, 3600),       # 3 per hour
    "/auth/forgot-password": (3, 3600),
    "/auth/reset-password":  (5, 3600),
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
        # Purge stale attempts (outside the window)
        _attempts[key] = [t for t in _attempts[key] if now - t < window_seconds]
        if len(_attempts[key]) >= max_count:
            retry_after = int(window_seconds - (now - _attempts[key][0]))
            logger.warning("Rate limit hit: ip=%s path=%s (%d attempts in %ds)",
                           client_ip, request.url.path, len(_attempts[key]), window_seconds)
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    allow_credentials=True,    # CRUCIAL: enables sending cookies cross-origin
)


# ─── Middleware ────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled exception in %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s → %d (%.0f ms)",
                request.method, request.url.path, response.status_code, duration_ms)
    return response


# ─── Health check ─────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health endpoint — checked by Docker + useful for debug.

    Returns 200 even if the DB is down (with db=false flag). The Docker
    container considers the backend healthy as long as this endpoint responds.
    """
    db_ok = await db_ping()
    return {
        "status": "ok",
        "db": "up" if db_ok else "down",
    }


# ─── Auth routes (FastAPI-Users) ──────────────────────────────────────────
# /auth/login + /auth/logout (cookie + JWT)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"])
# /auth/register (POST email + password → creates user)
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
# /auth/forgot-password, /auth/reset-password (password recovery flows)
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
# /users/me (GET to fetch profile, PATCH to update)
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])


@app.on_event("startup")
async def startup_init_db():
    """Creates DB tables at startup if they don't exist."""
    try:
        await init_db()
    except Exception:
        logger.exception("Failed to initialize DB schema at startup")
        # We don't crash — /health will report db=down


# ─── Example protected endpoint ───────────────────────────────────────────
# (to remove later — only used to test auth)


@app.get("/auth/test")
async def auth_test(user = Depends(current_active_user)):
    """Protected endpoint. Returns 401 if not connected.
    If connected: returns some info about the current user."""
    return {
        "ok": True,
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_superuser": user.is_superuser,
    }


@app.get("/admin/users")
async def admin_list_users(superuser = Depends(fastapi_users.current_user(active=True, superuser=True))):
    """List all user accounts. Reserved for superusers.

    Important note: returns id + email + flags but NEVER the hashed_password.
    """
    from sqlalchemy import select

    from .auth import User as UserModel
    from .db import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(UserModel))
        users = result.scalars().all()
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]


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


# ─── Routes ────────────────────────────────────────────────────────────────

@app.get("/portfolio", response_model=Portfolio)
def read_portfolio() -> Portfolio:
    return portfolio.load()


@app.put("/portfolio", response_model=Portfolio)
def write_portfolio(new: Portfolio) -> Portfolio:
    portfolio.save(new)
    return new


@app.get("/dashboard", response_model=DashboardResponse)
def read_dashboard(
    cma_shrinkage: float | None = Query(None, ge=0, le=1, description="0=pure historical, 1=pure CMA. Backend default: 0.7"),
    historical_period: str = Query("5y", pattern="^(1y|2y|3y|5y|10y|max)$", description="yfinance period used for σ and correlation"),
    risk_free: float | None = Query(None, ge=0, le=0.20, description="Risk-free rate (fraction). Default: 0.025"),
) -> DashboardResponse:
    return dashboard.build(
        cma_shrinkage=cma_shrinkage,
        historical_period=historical_period,
        risk_free=risk_free,
    )


@app.get("/timeseries", response_model=TimeseriesResponse)
def read_timeseries() -> TimeseriesResponse:
    return timeseries.build()


@app.get("/projection", response_model=ProjectionResponse)
def read_projection(
    monthly: float = Query(200, ge=0, le=100_000, description="Monthly contribution (€)"),
    years: int = Query(10, ge=1, le=50, description="Projection horizon (years)"),
    goal: float | None = Query(None, ge=0, description="Optional target (€)"),
    broker: str | None = Query(None, description="Broker ID (see /brokers). Default = config.default_broker."),
) -> ProjectionResponse:
    return projection.build(monthly, years, goal, broker)


@app.post("/optimizer", response_model=OptimizerResponse)
def read_optimizer(req: OptimizerRequest) -> OptimizerResponse:
    return optimizer.build(req)


@app.post("/strategy", response_model=glide_path.GlidePathResult)
def read_strategy(req: StrategyRequest) -> glide_path.GlidePathResult:
    """Computes the recommended strategy for this profile via glide path."""
    return glide_path.compute(
        age=req.age,
        horizon_years=req.horizon_years,
        rule=req.rule,                                          # type: ignore[arg-type]
        custom_multiplier=req.custom_multiplier or 0.20,
    )


@app.post("/bengen", response_model=bengen.BengenResponse)
def read_bengen(req: bengen.BengenRequest) -> bengen.BengenResponse:
    """Capital required to generate a sustainable monthly income + reverse projection."""
    return bengen.compute(req)


@app.post("/scan", response_model=ScanResponse)
def read_scan(req: ScanRequest) -> ScanResponse:
    """Discovers PEA-eligible assets via dynamic yfinance screening,
    computes their marginal ΔSharpe against the current portfolio."""
    return scanner.scan(req)


@app.get("/watchlist", response_model=list[str])
def read_watchlist() -> list[str]:
    """List of tracked tickers (appear in the portfolio with quantity=0)."""
    return watchlist.load()


@app.post("/watchlist/{ticker}", response_model=list[str])
def add_watchlist(ticker: str) -> list[str]:
    """Add a ticker to the watchlist."""
    return watchlist.add(ticker)


@app.delete("/watchlist/{ticker}", response_model=list[str])
def remove_watchlist(ticker: str) -> list[str]:
    """Remove a ticker from the watchlist."""
    return watchlist.remove(ticker)


@app.get("/brokers", response_model=BrokersResponse)
def read_brokers() -> BrokersResponse:
    """List of brokers available in config/brokers.yaml, with the default."""
    cfg = fees.config()
    return BrokersResponse(
        default=cfg.default_broker,
        brokers=[BrokerInfo(id=bid, name=fee.name) for bid, fee in cfg.brokers.items()],
    )


@app.post("/envelopes/eligible", response_model=EligibleEnvelopesResponse)
def list_eligible_envelopes(req: EligibilityRequest) -> EligibleEnvelopesResponse:
    """Returns the envelope catalog with eligibility status for this profile."""
    cfg = envelopes.config()
    results = []
    for eid, env in cfg.envelopes.items():
        eligible, note = envelopes.check_eligibility(env, req.age, req.rfr, req.fiscal_shares)
        results.append(EnvelopeEligibility(
            id=eid,
            name=env.name,
            rate_pct=env.rate_pct,
            ceiling_eur=env.ceiling_eur,
            tax_status=env.tax_status,
            liquidity_days=env.liquidity_days,
            eligible=eligible,
            note=note,
        ))
    return EligibleEnvelopesResponse(envelopes=results)


# ─── Powens integration ────────────────────────────────────────────────────


@app.post("/sync/powens")
async def post_sync_powens():
    """Triggers a manual sync from Powens. Updates data/portfolio.json."""
    result = await sync_portfolio()
    return result


@app.get("/sync/status")
def get_sync_status():
    """State of the last Powens sync (timestamp, counts, errors if any)."""
    st = powens_state.load()
    return {
        "configured": powens_settings.is_configured,
        "last_sync": st.last_sync.isoformat() if st.last_sync else None,
        "last_webhook": st.last_webhook.isoformat() if st.last_webhook else None,
        "last_error": st.last_error,
        "age_hours": st.age_hours,
        "positions_count": st.positions_count,
        "cash_balance": st.cash_balance,
        "is_stale": powens_state.is_stale(),
    }


@app.post("/webhooks/powens")
async def post_webhook_powens(payload: dict):
    """Endpoint receiving Powens webhooks (CONNECTION_SYNCED etc.).

    Configure this URL on the Powens Console after exposing via ngrok:
        https://abc-123.ngrok-free.app/webhooks/powens
    """
    return await powens_handle_webhook(payload)


@app.on_event("startup")
async def startup_powens_autosync():
    """Auto-sync from Powens at startup if configured AND stale."""
    if not powens_settings.is_configured:
        logger.info("Powens not configured, skipping autosync at startup")
        return
    if powens_state.is_stale():
        logger.info("Powens: last sync > %dh ago, autosync at startup", powens_settings.autosync_threshold_hours)
        try:
            result = await sync_portfolio()
            logger.info("Powens autosync: success=%s positions=%d", result.success, result.positions_count)
        except Exception:
            logger.exception("Powens autosync failed at startup")
    else:
        st = powens_state.load()
        logger.info("Powens: last sync %.1fh ago, skipping autosync", st.age_hours or 0)