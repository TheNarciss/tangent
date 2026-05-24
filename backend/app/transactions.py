"""Transactions service: ground-truth source for portfolio state.

Reads `data/transactions.json` (list of dated cashflows + trades) and derives:
- current positions (per-ticker qty and weighted average cost incl. fees)
- cash balance

Preferred over the legacy `portfolio.json` because trades carry fees and dates,
enabling true cost basis, fee attribution, and future TRI/IRR computation.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from .errors import PortfolioCorruptedError
from .models import Portfolio, Position, Transaction

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "data" / "transactions.json"


def exists() -> bool:
    return _PATH.exists()


def load() -> list[Transaction]:
    if not _PATH.exists():
        return []
    try:
        raw = json.loads(_PATH.read_text())
        return [Transaction.model_validate(t) for t in raw]
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        raise PortfolioCorruptedError(f"Impossible de lire transactions.json: {exc}") from exc


def derive_portfolio(txns: list[Transaction]) -> Portfolio:
    """Aggregate transactions into current positions + cash.

    PAMP = (Σ qty × unit_price + Σ fees) / Σ qty — i.e. cost basis includes fees,
    matching BNP's "Prix de revient" displayed in the positions export.
    """
    qty: dict[str, float] = defaultdict(float)
    cost: dict[str, float] = defaultdict(float)
    cash = 0.0

    for t in txns:
        if t.type == "deposit":
            cash += t.amount_eur or 0
        elif t.type == "withdrawal":
            cash -= t.amount_eur or 0
        elif t.type == "dividend":
            cash += t.amount_eur or 0
        elif t.type == "buy":
            if not t.ticker:
                continue
            total_cost = t.qty * t.unit_price + t.fees
            qty[t.ticker] += t.qty
            cost[t.ticker] += total_cost
            cash -= total_cost
        elif t.type == "sell":
            if not t.ticker or qty[t.ticker] <= 0:
                continue
            # Simple weighted-average accounting: PAMP unchanged, qty reduced
            pamp = cost[t.ticker] / qty[t.ticker]
            cost[t.ticker] -= t.qty * pamp
            qty[t.ticker] -= t.qty
            cash += t.qty * t.unit_price - t.fees

    positions = [
        Position(ticker=tk, quantity=q, avg_cost=cost[tk] / q) for tk, q in qty.items() if q > 0
    ]
    logger.info(
        "derived %d positions + %.2f € cash from %d transactions", len(positions), cash, len(txns)
    )
    return Portfolio(positions=positions, cash=cash)
