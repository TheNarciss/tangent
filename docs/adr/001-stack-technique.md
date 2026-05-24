# ADR-001: Stack technique

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Tangent est une application de gestion patrimoniale avec :
- Logique métier mathématique non-triviale (optimisation portfolio, projection Monte Carlo, stress tests)
- Données financières externes (market data via yfinance, banques via Powens)
- UI riche (graphiques, tableaux interactifs)
- Multi-utilisateur avec isolation stricte des données
- Auto-hébergement souhaité

Il faut une stack qui couvre ces besoins, soit maîtrisée par le développeur (Python + React), et reste maintenable seul.

## Décision

**Backend** : Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + uvicorn.

**Frontend** : TypeScript + React 18 + Vite + TailwindCSS + shadcn/ui + React Query.

**Database** : PostgreSQL 16.

**Aggregation bancaire** : Powens (API DSP2).

**Market data** : yfinance (Yahoo Finance).

**Conteneurisation** : Docker + Docker Compose.

## Conséquences

### Positives

- Stack mainstream → écosystème mature, doc, communauté
- Python excellent pour la finance quantitative (numpy, pandas, scipy)
- FastAPI = type-safety + OpenAPI auto + async natif
- React + Vite = DX rapide, HMR, build optim
- shadcn/ui = composants accessibles sans lock-in (le code est copié, pas importé)
- Postgres = transactions, JSONB, robuste, gratuit
- Tout self-hostable, pas de dépendance SaaS bloquante (sauf Powens)

### Négatives

- 2 langages à maintenir (Python + TS)
- Bundle JS plus lourd qu'une SSR pure
- yfinance n'est pas une API officielle → fragile (mais gratuit)

## Alternatives considérées

### Option A — Django (Python)

Plus batterie-incluse, ORM mature. Écartée car async moins idiomatique, OpenAPI moins natif, surcouches inutiles pour notre cas (templating Django pas utilisé).

### Option B — Next.js full-stack (Node)

Stack unifiée TS partout. Écartée car la logique métier financière est plus fluide en Python (numpy, scipy, pandas indispensables pour optim).

### Option C — Rust + Leptos / SvelteKit

Performance, écosystème en croissance. Écartée par manque de maturité et compétences moindres → vitesse de dev cassée.

## Notes

- Tous les modèles Pydantic doivent être exportés OpenAPI → contrats clairs frontend/backend
- yfinance peut être remplacé par EOD Historical Data ou Polygon plus tard si besoin de fiabilité accrue
- Postgres choisi vs MySQL pour les types riches (JSONB, arrays, enum natifs)
