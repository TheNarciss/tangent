# Portfolio Dashboard — Backend

Backend FastAPI pour analyser un portefeuille d'ETF/actions : valorisation live,
métriques de Markowitz (μ, σ, Sharpe, corrélations) et insights automatiques.

## Setup

```bash
pip install -e .
```

## Run

```bash
uvicorn app.main:app --reload
```

Docs interactives : <http://localhost:8000/docs>

## API

| Méthode | Endpoint | Rôle |
|---|---|---|
| `GET` | `/portfolio` | Lit les positions |
| `PUT` | `/portfolio` | Remplace les positions |
| `GET` | `/dashboard` | Valorisation + métriques + insights |

## Configuration du portefeuille

Éditer `data/portfolio.json` ou `PUT /portfolio` avec :

```json
{
  "positions": [
    {"ticker": "CW8.PA", "quantity": 41, "avg_cost": 5.891}
  ],
  "cash": 0.0
}
```

Les tickers sont des symboles Yahoo Finance (suffixe `.PA` pour Euronext Paris,
`.DE` pour Xetra, etc.).

## Architecture

```
app/
├── main.py        HTTP routes (FastAPI)
├── dashboard.py   Orchestration: build full DashboardResponse
├── portfolio.py   Persistence (JSON file)
├── market.py      yfinance + TTL cache
├── analytics.py   Pure math (returns, μ, σ, Sharpe, corr)
├── diagnostic.py  Rule-based insights
└── models.py      Pydantic schemas
```

Règles : un module = une responsabilité, `analytics.py` zéro I/O,
pas de cycle d'imports, types stricts.
