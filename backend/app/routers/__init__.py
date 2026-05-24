"""HTTP routers split by domain.

Each router groups related endpoints + applies common auth/data dependencies.
main.py just mounts them — no business logic there anymore.

Routers:
- portfolio    : GET/PUT /portfolio
- dashboard    : GET /dashboard, GET /timeseries
- analysis     : POST /optimizer, GET /projection, POST /scan
- planning     : POST /strategy, POST /bengen
- watchlist    : GET/POST/DELETE /watchlist
- envelopes    : POST /envelopes/eligible, GET /brokers
- powens       : POST /sync/powens, GET /sync/status, POST /webhooks/powens
- admin        : GET /admin/users (superuser only)
"""
