"""FastAPI entry point. HTTP layer + global error handling + request tracing."""
import logging
import time

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import bengen, dashboard, envelopes, fees, glide_path, logging_config, optimizer, portfolio, projection, scanner, timeseries, watchlist
from .errors import AppError
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "PUT", "POST", "OPTIONS"],
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
def read_dashboard(
    cma_shrinkage: float | None = Query(None, ge=0, le=1, description="0=pure historique, 1=pure CMA. Défaut backend: 0.7"),
    historical_period: str = Query("5y", pattern="^(1y|2y|3y|5y|10y|max)$", description="Période yfinance pour σ et corrélation"),
    risk_free: float | None = Query(None, ge=0, le=0.20, description="Taux sans risque (fraction). Défaut: 0.025"),
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
    monthly: float = Query(200, ge=0, le=100_000, description="Versement mensuel (€)"),
    years: int = Query(10, ge=1, le=50, description="Horizon de projection (années)"),
    goal: float | None = Query(None, ge=0, description="Objectif optionnel (€)"),
    broker: str | None = Query(None, description="Broker ID (cf. /brokers). Default = config.default_broker."),
) -> ProjectionResponse:
    return projection.build(monthly, years, goal, broker)


@app.post("/optimizer", response_model=OptimizerResponse)
def read_optimizer(req: OptimizerRequest) -> OptimizerResponse:
    return optimizer.build(req)


@app.post("/strategy", response_model=glide_path.GlidePathResult)
def read_strategy(req: StrategyRequest) -> glide_path.GlidePathResult:
    """Calcule la stratégie recommandée pour ce profil via glide path."""
    return glide_path.compute(
        age=req.age,
        horizon_years=req.horizon_years,
        rule=req.rule,                                          # type: ignore[arg-type]
        custom_multiplier=req.custom_multiplier or 0.20,
    )


@app.post("/bengen", response_model=bengen.BengenResponse)
def read_bengen(req: bengen.BengenRequest) -> bengen.BengenResponse:
    """Capital nécessaire pour générer un revenu mensuel soutenable + projection inverse."""
    return bengen.compute(req)


@app.post("/scan", response_model=ScanResponse)
def read_scan(req: ScanRequest) -> ScanResponse:
    """Découvre des actifs PEA-éligibles via screening dynamique yfinance,
    calcule leur ΔSharpe marginal vs ton portfolio actuel."""
    return scanner.scan(req)


@app.get("/watchlist", response_model=list[str])
def read_watchlist() -> list[str]:
    """Liste des tickers suivis (apparaissent dans le portfolio avec quantity=0)."""
    return watchlist.load()


@app.post("/watchlist/{ticker}", response_model=list[str])
def add_watchlist(ticker: str) -> list[str]:
    """Ajoute un ticker à la watchlist."""
    return watchlist.add(ticker)


@app.delete("/watchlist/{ticker}", response_model=list[str])
def remove_watchlist(ticker: str) -> list[str]:
    """Retire un ticker de la watchlist."""
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
    """Retourne le catalogue d'enveloppes avec leur statut d'éligibilité pour ce profil."""
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