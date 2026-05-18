"""FastAPI entry point. HTTP layer only — all logic lives in services."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import dashboard, optimizer, portfolio, projection, timeseries
from .models import (
    DashboardResponse,
    OptimizerResponse,
    Portfolio,
    ProjectionResponse,
    TimeseriesResponse,
)

app = FastAPI(title="Portfolio Dashboard", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
)


@app.get("/portfolio", response_model=Portfolio)
def read_portfolio() -> Portfolio:
    return portfolio.load()


@app.put("/portfolio", response_model=Portfolio)
def write_portfolio(new: Portfolio) -> Portfolio:
    portfolio.save(new)
    return new


@app.get("/dashboard", response_model=DashboardResponse)
def read_dashboard() -> DashboardResponse:
    try:
        return dashboard.build()
    except dashboard.EmptyPortfolioError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/timeseries", response_model=TimeseriesResponse)
def read_timeseries() -> TimeseriesResponse:
    try:
        return timeseries.build()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/projection", response_model=ProjectionResponse)
def read_projection(
    monthly: float = Query(200, ge=0, le=100_000, description="Versement mensuel (€)"),
    years: int = Query(10, ge=1, le=50, description="Horizon de projection (années)"),
    goal: float | None = Query(None, ge=0, description="Objectif optionnel (€)"),
) -> ProjectionResponse:
    try:
        return projection.build(monthly, years, goal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/optimizer", response_model=OptimizerResponse)
def read_optimizer(
    objective: str = Query("max_sharpe", pattern="^(max_sharpe|min_variance)$",
                            description="max_sharpe ou min_variance"),
) -> OptimizerResponse:
    try:
        return optimizer.build(objective)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc