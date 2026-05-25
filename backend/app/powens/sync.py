"""Powens → Portfolio sync (multi-tenant safe).

Workflow:
1. Caller looks up the user's PowensCredential (encrypted_token)
2. Call sync_portfolio(token=..., user_id=..., session=...)
3. Pull /accounts + /investments using user-scoped token
4. Return SyncResult — caller persists positions to DB via portfolio_repo

No file IO, no global state. All sync metadata persisted per-user in
powens_credentials (last_sync_at, last_error, last_positions_count, etc.).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PowensCredential
from ..models import Position
from . import yaml_config
from .client import PowensClient, PowensError

logger = logging.getLogger(__name__)


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
    positions: list[Position] = []  # caller persists these via portfolio_repo


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
    """Builds the yfinance ticker from Powens (stock_symbol, stock_market)."""
    symbol = inv.get("stock_symbol") or inv.get("label", "")[:6].upper()
    market = inv.get("stock_market", "")
    suffixes = yaml_config.get("market_suffixes", {})
    suffix = suffixes.get(market, "")
    return f"{symbol}{suffix}".strip(".") if suffix else symbol


# ── Sync state persistence (per-user) ──────────────────────────────────────


async def _update_sync_state(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    success: bool,
    positions_count: int = 0,
    cash_balance: float = 0.0,
    error: str | None = None,
) -> None:
    """Update PowensCredential.last_sync_* columns for this user."""
    stmt = select(PowensCredential).where(PowensCredential.user_id == user_id)
    res = await session.execute(stmt)
    cred = res.scalars().first()
    if cred is None:
        logger.warning("Cannot update sync state: no PowensCredential for user_id=%s", user_id)
        return
    cred.last_sync_at = datetime.now(UTC)
    cred.last_error = error
    if success:
        cred.last_positions_count = positions_count
        cred.last_cash_balance = cash_balance
    await session.commit()


# ── Main pipeline ───────────────────────────────────────────────────────────


async def sync_portfolio(
    *,
    token: str,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> SyncResult:
    """Pull from Powens for a SPECIFIC user → return SyncResult.

    Multi-tenant safe:
    - `token` is passed explicitly (no global state)
    - `user_id` is required to update sync metadata in DB
    - `session` is required to persist sync state

    The caller is responsible for persisting positions to DB via
    portfolio_repo.replace_positions(session, user_id, ...).

    On error, sync metadata is updated with last_error and SyncResult.success=False.
    """
    now = datetime.now(UTC)
    try:
        async with PowensClient(token=token) as client:
            accounts = await client.get_accounts()
            logger.info("Powens [user=%s]: fetched %d accounts", user_id, len(accounts))

            pea_titres = _find_account(accounts, yaml_config.get("pea_titres", {}))
            pea_cash = _find_account(accounts, yaml_config.get("pea_cash", {}))

            if pea_titres is None:
                raise PowensError(
                    "No PEA Titres account found in Powens. "
                    "Check the rules in config/powens.yaml or the account list."
                )

            investments = await client.get_investments(pea_titres["id"])
            logger.info(
                "Powens [user=%s]: %d investments in PEA Titres",
                user_id,
                len(investments),
            )

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

            cash = float(pea_cash.get("balance", 0)) if pea_cash else 0.0
            total_valuation = sum(float(inv.get("valuation", 0)) for inv in investments) + cash

            await _update_sync_state(
                session,
                user_id,
                success=True,
                positions_count=len(positions),
                cash_balance=cash,
            )

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
        logger.exception("Powens sync failed for user=%s", user_id)
        await _update_sync_state(session, user_id, success=False, error=str(exc))
        return SyncResult(success=False, error=str(exc), synced_at=now)
    except Exception as exc:
        logger.exception("Unexpected error during Powens sync for user=%s", user_id)
        await _update_sync_state(session, user_id, success=False, error=f"Unexpected: {exc}")
        return SyncResult(success=False, error=f"Unexpected: {exc}", synced_at=now)
