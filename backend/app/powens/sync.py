"""Powens → local Portfolio sync.

Workflow:
1. Pull /accounts from Powens
2. Identify PEA Titres + PEA Espèces cash account (YAML heuristics)
3. Pull /investments for PEA Titres → map to Position
4. Backup existing portfolio.json (timestamped) → write new version
5. Persist state (timestamp, counts, etc.)

Powens = SOURCE OF TRUTH for current positions (user choice).
The transactions.json history is preserved as a backup for future reference.
"""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from ..models import Portfolio, Position
from . import state, yaml_config
from .client import PowensClient, PowensError

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_PORTFOLIO_PATH = _DATA_DIR / "portfolio.json"
_TRANSACTIONS_PATH = _DATA_DIR / "transactions.json"
_BACKUP_DIR = _DATA_DIR / "backups"


class SyncResult(BaseModel):
    """Return value of sync_portfolio() — exposed via POST /sync/powens."""

    success: bool
    positions_count: int = 0
    cash_balance: float = 0.0
    total_valuation: float = 0.0
    accounts_synced: list[str] = []
    skipped_accounts: list[str] = []
    error: str | None = None
    synced_at: datetime
    positions: list[Position] = []  # for multi-tenant DB persistence


# ── Matching helpers ────────────────────────────────────────────────────────


def _match_account(account: dict, rules: dict) -> bool:
    """True if the account matches the YAML rules (type + name_contains_any)."""
    if rules.get("type") and account.get("type") != rules["type"]:
        return False
    name = (account.get("name") or "").lower()
    needles = [n.lower() for n in rules.get("name_contains_any", [])]
    if needles and not any(n in name for n in needles):
        return False
    return True


def _find_account(accounts: list[dict], rules: dict) -> dict | None:
    """First account matching the rules, or None."""
    for a in accounts:
        if _match_account(a, rules):
            return a
    return None


def _ticker_from_powens(inv: dict) -> str:
    """Builds the yfinance ticker from Powens (stock_symbol, stock_market).

    Ex: stock_symbol="DCAM", stock_market="Euronext Paris" → "DCAM.PA"
    Falls back to just the stock_symbol when the market is unknown.
    """
    symbol = inv.get("stock_symbol") or inv.get("label", "")[:6].upper()
    market = inv.get("stock_market", "")
    suffixes = yaml_config.get("market_suffixes", {})
    suffix = suffixes.get(market, "")
    return f"{symbol}{suffix}".strip(".") if suffix else symbol


# ── Backup before overwrite ─────────────────────────────────────────────────


def _backup_portfolio() -> Path | None:
    """Backs up the existing portfolio.json into data/backups/ with timestamp.

    Returns the backup path, or None if no portfolio.json exists.
    """
    if not _PORTFOLIO_PATH.exists():
        return None
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = _BACKUP_DIR / f"portfolio_{ts}.json"
    shutil.copy(_PORTFOLIO_PATH, dest)
    logger.info("Backed up portfolio.json → %s", dest.name)
    return dest


def _move_transactions_to_legacy() -> None:
    """First sync: move transactions.json out of portfolio.load()'s path.

    portfolio.load() reads transactions.json first if present. Since Powens
    becomes the source of truth, we evacuate that file after backing it up.
    Renamed with a timestamp so we don't overwrite an existing backup.
    """
    if not _TRANSACTIONS_PATH.exists():
        return
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = _BACKUP_DIR / f"transactions_legacy_{ts}.json"
    shutil.move(str(_TRANSACTIONS_PATH), dest)
    logger.info(
        "Moved transactions.json → %s (Powens is now the source of truth). "
        "Restore by copying it back to data/transactions.json if needed.",
        dest.name,
    )


# ── Main pipeline ───────────────────────────────────────────────────────────


async def sync_portfolio() -> SyncResult:
    """Pull from Powens → write Portfolio + state. Idempotent.

    On error, the existing portfolio.json is NOT modified and the error
    is recorded in state.last_error.
    """
    now = datetime.now(UTC)
    try:
        async with PowensClient() as client:
            accounts = await client.get_accounts()
            logger.info("Powens: fetched %d accounts", len(accounts))

            # 1. Identify the PEA accounts
            pea_titres = _find_account(accounts, yaml_config.get("pea_titres", {}))
            pea_cash = _find_account(accounts, yaml_config.get("pea_cash", {}))

            if pea_titres is None:
                raise PowensError(
                    "No PEA Titres account found in Powens. "
                    "Check the rules in config/powens.yaml or the account list "
                    "via GET /users/me/accounts."
                )

            # 2. Pull investments for the PEA Titres
            investments = await client.get_investments(pea_titres["id"])
            logger.info("Powens: %d investments in PEA Titres", len(investments))

            # 3. Map to Position
            positions: list[Position] = []
            for inv in investments:
                if (inv.get("quantity") or 0) <= 0:
                    continue
                positions.append(
                    Position(
                        ticker=_ticker_from_powens(inv),
                        quantity=float(inv["quantity"]),
                        avg_cost=float(inv.get("unitprice", 0)),
                        isin=inv.get("code"),
                        label=inv.get("label"),
                    )
                )

            # 4. Cash from the PEA Espèces account
            cash = float(pea_cash.get("balance", 0)) if pea_cash else 0.0

            # 5. Persist portfolio
            _backup_portfolio()
            _move_transactions_to_legacy()
            portfolio = Portfolio(positions=positions, cash=cash)
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _PORTFOLIO_PATH.write_text(portfolio.model_dump_json(indent=2), encoding="utf-8")

            # 6. Persist state
            state.save(
                state.SyncState(
                    last_sync=now,
                    last_error=None,
                    connection_id=pea_titres.get("id_connection"),
                    accounts_seen=[a["id"] for a in accounts],
                    positions_count=len(positions),
                    cash_balance=cash,
                )
            )

            total_valuation = sum(float(inv.get("valuation", 0)) for inv in investments) + cash

            return SyncResult(
                success=True,
                positions_count=len(positions),
                cash_balance=cash,
                total_valuation=total_valuation,
                accounts_synced=[pea_titres["name"]] + ([pea_cash["name"]] if pea_cash else []),
                synced_at=now,
                positions=positions,
            )

    except PowensError as exc:
        logger.exception("Powens sync failed")
        state.mark_error(str(exc))
        return SyncResult(success=False, error=str(exc), synced_at=now)
    except Exception as exc:
        logger.exception("Unexpected error during Powens sync")
        state.mark_error(f"Unexpected: {exc}")
        return SyncResult(success=False, error=f"Unexpected: {exc}", synced_at=now)
