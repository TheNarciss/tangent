# Portfolio Dashboard — Backend

[![CI](https://github.com/TheNarciss/tangent/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/TheNarciss/tangent/actions/workflows/ci.yml)
[![Semgrep](https://github.com/TheNarciss/tangent/actions/workflows/semgrep.yml/badge.svg?branch=dev)](https://github.com/TheNarciss/tangent/actions/workflows/semgrep.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5-blue?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)


# Tangent

A self-hosted personal patrimony dashboard for people who prefer Markowitz over budget categories.

The name is a nod to the tangent portfolio: the one point on the efficient frontier that touches the capital market line, the one your livret A actually helps you reach.

## What this is

Tangent connects to your French banks via Powens (DSP2), pulls your holdings and transactions, then runs the kind of portfolio analysis that personal finance apps would charge you a subscription for and still get wrong. It also generates a daily AI briefing on your portfolio, written by Claude with web search enabled, because the alternative is reading 14 newsletters and still not knowing why SPY moved.

It is built for one user (me), works for two (me and my partner), and would probably scale to ten before something breaks. That is not a goal.

## Why it exists

Personal finance apps optimize for engagement. You log in, see a pie chart, feel briefly informed, close the tab. The ones with real analysis tend to either:

1. cost more than the alpha they claim to find, or
2. keep your bank credentials on someone else's server.

Tangent goes the other direction. The data lives on your machine. The math is in the open. The dashboard does not exist to hold your attention, it exists to answer specific questions:

- Is my portfolio on the efficient frontier?
- What is my actual Sharpe ratio after fees?
- How much will I have at 65 if today's contributions hold?
- Did anything happen this week that I should care about?

If that resonates with one person and confuses ten, good. Tangent was built for the one.

## What is in it

### Banking aggregation (Powens DSP2)

- Multi-account import: balances, holdings, transactions
- Loan tracking with rate, maturity, remaining principal
- Manual edits when the aggregator misclassifies something (rare, but it happens)

### Portfolio analysis

- Mean-variance optimizer with Tobin CAL, because livret A is a legitimate risk-free asset and the textbook never said otherwise
- Per-asset risk metrics: annualized return, volatility, Sharpe, CVaR 95 percent, max drawdown
- Correlation matrix as a sticky-header heatmap, mobile-friendly
- Asset scanner: find ETFs that would improve your portfolio's Sharpe ratio
- Weighted-average TER with manual editing and an LLM-resolved fallback for the missing values

### Projection and retirement planning

- Monte Carlo simulation with custom Capital Market Assumptions
- Bengen 4 percent rule with capital target and timeline
- Stress tests against 2008, COVID, 2022, and other historical scenarios
- Glide path support: age-dependent equity allocation, configurable

### AI portfolio reviews

- Generated nightly via the Anthropic API, streamed over SSE
- Web search enabled, the model can actually look up news on your positions
- Markdown output, sources cited, cost tracked per request
- Does not say "diversification is important". Says "SPY fell 2.1 percent this week, here is what moved, here are the three things to actually look at"

### French fiscal context

- PEA, Assurance Vie, CTO, livrets (A, LDDS, LEP) modeled with their actual rules
- PFU vs barème progressif handled where it matters
- IFI awareness, because real estate exists and a wealth report without it is fiction
- Tax-aware optimization: the optimizer can include or exclude tax-advantaged envelopes

### Mobile and desktop UX

- Mobile: bento layout, balance-first dashboard, 5-item bottom navigation, responsive tables that hide non-essential columns
- Desktop: console-style sidebar inspired by Linear and Claude Code, 4 main views plus a Plus menu
- Dark mode by default, because finance at 11 pm is a real use case

## Stack

### Backend

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, asyncpg
- PostgreSQL 16 with JSONB for hot Powens snapshots (see `docs/adr/013`)
- fastapi-users for auth, Alembic for migrations, Ruff and mypy for the gates

### Frontend

- React 18, Vite, TypeScript in strict mode
- Tailwind, shadcn/ui, custom SVG charts via `lib/chart.ts` (no Recharts, no D3 wrappers, just math)
- React Query for server state, localStorage for preferences, no global store

### Infrastructure

- Docker Compose for dev and prod
- Caddy reverse proxy, Cloudflare Tunnel for public exposure (zero inbound ports)
- Oracle Cloud Always Free tier on ARM64, because 24 GB of RAM for zero euros a month is hard to beat
- Self-hosted GitHub Actions runner for continuous deployment

### Data sources

- Powens (DSP2 aggregator)
- yfinance for historical prices
- Financial Modeling Prep for fundamentals, cached 7 days (free tier)
- Anthropic API for the portfolio reviews

## Quick start

You need Docker, Docker Compose, a Powens client ID (free tier is enough), and an Anthropic API key if you want the AI reviews.

```bash
git clone https://github.com/TheNarciss/tangent.git
cd tangent
cp .env.example .env
# Open .env, fill in POWENS_CLIENT_ID, ANTHROPIC_API_KEY, etc.
docker compose up -d
```

Then open http://localhost:5173, create an account, link a bank via the "Add bank" button, wait for the first sync. That is it.

For a production deployment with Caddy and Cloudflare Tunnel, read `docs/adr/005-deployment-topology.md`. It walks through Oracle Cloud setup, SSL, security headers, and the self-hosted runner.

## Project structure
tangent/
backend/                  FastAPI app
app/
routers/              HTTP endpoints
repositories/         DB access, filtered by user_id (ADR-002)
finance/              Pure portfolio math, no I/O
llm/                  Anthropic review pipeline
powens/               DSP2 aggregator client
auth/                 fastapi-users plus Google OAuth
tests/                  pytest, integration tests use real Postgres
frontend/                 React + Vite
src/
components/           UI organized by feature
lib/                  chart, format, hooks, profile sync
api.ts                all server hooks in one file
docs/adr/                 Architecture Decision Records
docker-compose.yml        dev
docker-compose.prod.yml   prod

Every significant technical decision is recorded as an ADR. If you find yourself thinking "why did they do X this way", the answer is probably in `docs/adr/`. If it is not, open an issue.

## Status

Tangent is a personal project running in production for one user (me, on `https://riskybusinesses.uk`, but invitation-only). It has tests, CI, a real deployment pipeline, and ADRs documenting the architecture. It is not a startup, there is no roadmap committee, features land when they scratch an itch.

That said, contributions, bug reports, and "have you considered" issues are welcome. The current direction is tracked in `docs/ROADMAP_PATRIMOINE_360.md` (in French, sorry).

### Known limitations

- French fiscal context is baked in (PEA, IFI, etc.). Other jurisdictions would need adapter work
- Powens is the only supported aggregator. Plaid would work in principle but I do not live in the US
- Multi-user works but is not battle-tested past two users
- No native mobile app. The web UI is mobile-responsive, and that is the answer

## License

MIT. Use it, fork it, ship a paid version (be my guest). If you build something neat on top, ping me. I am curious.

## Acknowledgements

Built with substantial help from Claude (the model that also writes the portfolio reviews). When you see "discussed with my Claude assistant" in a commit message, that is not a euphemism, that is how the work actually happens.

Thanks to the usual open-source heroes: FastAPI, React, Vite, Tailwind, shadcn/ui, Tanstack Query, Pydantic, SQLAlchemy, Alembic, and the rest of the crew without whom this would be a Notion page with too many formulas.
