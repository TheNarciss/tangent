"""Stress tests — performance du portefeuille pendant les crises historiques.

Chaque scénario est une fenêtre temporelle bien définie ; on calcule la performance
cumulée du portefeuille reconstruit (qty actuelles × prix historiques) sur la fenêtre.
"""

import logging

import pandas as pd

from . import analytics

logger = logging.getLogger(__name__)

# A period is only scored when every holding has a price at most this many
# calendar days before the window starts (holidays, listing gaps).
MAX_START_GAP_DAYS = 10

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
    Une période n'est scorée que si *chaque* ligne a un prix sur toute la
    fenêtre : un panier partiel (ETF lancé après la crise) donnerait un
    rendement de sous-ensemble que l'UI multiplie ensuite par la valeur totale.
    Les périodes non couvertes sont ignorées.
    """
    if prices.empty:
        return []

    quantities = {t: q for t, q in quantities.items() if t in prices.columns}
    if not quantities:
        return []

    # NaN propagates: the curve only exists on dates where every line is priced.
    equity = analytics.portfolio_value_series(prices, quantities)
    if equity.empty:
        return []

    results: list[dict] = []
    for p in STRESS_PERIODS:
        start = pd.Timestamp(p["start"])
        end = pd.Timestamp(p["end"])
        before = equity.loc[:start]
        window = equity.loc[start:end]
        if before.empty or window.empty:
            continue  # at least one holding has no history here → skip
        if (start - before.index[-1]).days > MAX_START_GAP_DAYS:
            continue  # coverage starts inside the window → partial basket → skip
        if (window.index[0] - start).days > MAX_START_GAP_DAYS:
            continue
        value_start = float(before.iloc[-1])
        value_end = float(window.iloc[-1])
        min_value = float(window.min())
        pnl_pct = (value_end - value_start) / value_start if value_start else 0.0
        drawdown = (min_value - value_start) / value_start if value_start else 0.0
        results.append(
            {
                "id": p["id"],
                "label": p["label"],
                "description": p["description"],
                "start": p["start"],
                "end": p["end"],
                "pnl_pct": pnl_pct,
                "drawdown_pct": drawdown,
            }
        )
    logger.info("stress tests computed: %d scenarios", len(results))
    return results
