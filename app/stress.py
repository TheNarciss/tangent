"""Stress tests — performance du portefeuille pendant les crises historiques.

Chaque scénario est une fenêtre temporelle bien définie ; on calcule la performance
cumulée du portefeuille reconstruit (qty actuelles × prix historiques) sur la fenêtre.
"""
import logging
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

# Périodes calibrées sur les pires drawdowns récents.
# Format: (id, label, start, end_or_None_for_recovery).
STRESS_PERIODS: list[dict] = [
    {
        "id": "covid_2020",
        "label": "Crash COVID (fév-mar 2020)",
        "start": "2020-02-19",
        "end": "2020-03-23",
        "description": "5 semaines, S&P 500 −34 % à son point bas",
    },
    {
        "id": "inflation_2022",
        "label": "Inflation + Ukraine (jan-oct 2022)",
        "start": "2022-01-03",
        "end": "2022-10-12",
        "description": "Hausse de taux brutale, S&P 500 −25 %, Nasdaq −36 %",
    },
    {
        "id": "regional_banks_2023",
        "label": "Banques régionales US (mars 2023)",
        "start": "2023-03-08",
        "end": "2023-03-13",
        "description": "Chute SVB / Credit Suisse en 5 jours",
    },
]


def compute(prices: pd.DataFrame, quantities: dict[str, float]) -> list[dict]:
    """Pour chaque période, calcule la performance cumulée du portefeuille
    reconstruit (qty actuelles × prix historiques) sur la fenêtre.

    Retourne une liste de dicts JSON-friendly avec start, end, pnl_pct, drawdown.
    Skip silencieusement les périodes en-dehors de l'historique disponible.
    """
    if prices.empty:
        return []

    qty_series = pd.Series(quantities)
    available_tickers = [t for t in qty_series.index if t in prices.columns]
    if not available_tickers:
        return []

    qty_series = qty_series[available_tickers]
    equity = (prices[available_tickers] * qty_series).sum(axis=1)
    equity = equity.dropna()
    if equity.empty:
        return []

    results: list[dict] = []
    earliest = equity.index.min().date() if hasattr(equity.index.min(), "date") else None
    for p in STRESS_PERIODS:
        start = pd.Timestamp(p["start"])
        end = pd.Timestamp(p["end"])
        if earliest and start.date() < earliest:
            continue  # period antérieure à l'historique → skip
        # Get value at start and during window
        try:
            value_start = float(equity.loc[:start].iloc[-1])
            window = equity.loc[start:end]
            if window.empty:
                continue
            value_end = float(window.iloc[-1])
            min_value = float(window.min())
        except (KeyError, IndexError):
            continue
        pnl_pct = (value_end - value_start) / value_start if value_start else 0.0
        drawdown = (min_value - value_start) / value_start if value_start else 0.0
        results.append({
            "id": p["id"],
            "label": p["label"],
            "description": p["description"],
            "start": p["start"],
            "end": p["end"],
            "pnl_pct": pnl_pct,
            "drawdown_pct": drawdown,
        })
    logger.info("stress tests computed: %d scenarios", len(results))
    return results