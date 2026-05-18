"""FastAPI entry point. HTTP layer + global error handling + request tracing."""
import logging
import time

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import dashboard, fees, logging_config, optimizer, portfolio, projection, timeseries
from .errors import AppError
from .models import (
    BrokerInfo,
    BrokersResponse,
    DashboardResponse,
    OptimizerResponse,
    Portfolio,
    ProjectionResponse,
    TimeseriesResponse,
)

logging_config.configure()
logger = logging.getLogger("app")

app = FastAPI(title="Portfolio Dashboard", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
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
        content={"detail": "Erreur interne du serveur.", "type": type(exc).__name__},
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
def read_dashboard() -> DashboardResponse:
    return dashboard.build()


@app.get("/timeseries", response_model=TimeseriesResponse)
def read_timeseries() -> TimeseriesResponse:
    return timeseries.build()


@app.get("/projection", response_model=ProjectionResponse)
def read_projection(
    monthly: float = Query(200, ge=0, le=100_000, description="Versement mensuel (€)"),
    years: int = Query(10, ge=1, le=50, description="Horizon de projection (années)"),
    goal: float | None = Query(None, ge=0, description="Objectif optionnel (€)"),
    broker: str | None = Query(None, description="Broker ID (cf. /brokers). Default = config.default_broker."),
) -> ProjectionResponse:
    return projection.build(monthly, years, goal, broker)


@app.get("/optimizer", response_model=OptimizerResponse)
def read_optimizer(
    objective: str = Query("max_sharpe", pattern="^(max_sharpe|min_variance)$",
                            description="max_sharpe ou min_variance"),
) -> OptimizerResponse:
    return optimizer.build(objective)


@app.get("/brokers", response_model=BrokersResponse)
def read_brokers() -> BrokersResponse:
    """List of brokers available in config/brokers.yaml, with the default."""
    cfg = fees.config()
    return BrokersResponse(
        default=cfg.default_broker,
        brokers=[BrokerInfo(id=bid, name=fee.name) for bid, fee in cfg.brokers.items()],
    )