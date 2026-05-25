"""Powens implementation of IBankAggregator (Phase A — full mapping).

Translates Powens-native API responses into the neutral DTOs defined in
`app/aggregator/types.py`. No side effects on DB — callers (routes) are
responsible for persistence (this keeps the aggregator pure and testable).

Cf ADR-008, ADR-019.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import (
    AccountType,
    BankAccount,
    Investment,
    Transaction,
)
from ..aggregator import (
    SyncResult as AggregatorSyncResult,
)
from . import yaml_config
from .client import PowensClient, PowensError

logger = logging.getLogger(__name__)


def _powens_currency(value: Any) -> str:
    """Extract ISO 4217 currency code from a Powens currency field.

    Powens returns `currency` either as a dict `{"id": "EUR", "symbol": "€"}`
    or as a string code. Normalize to the string code, fallback to 'EUR'.
    """
    if isinstance(value, dict):
        return value.get("id") or "EUR"
    if isinstance(value, str) and value:
        return value
    return "EUR"


def _map_account_type(powens_type: str | None) -> AccountType:
    """Map a Powens native type string to a neutral AccountType."""
    mapping: dict[str, str] = yaml_config.get("account_type_to_neutral", {})
    neutral_str = mapping.get((powens_type or "").lower(), "other")
    try:
        return AccountType(neutral_str)
    except ValueError:
        return AccountType.OTHER


def _build_ticker(inv: dict) -> str:
    """Build a yfinance-style ticker from Powens investment fields."""
    suffixes: dict[str, str] = yaml_config.get("market_suffixes", {})
    symbol = inv.get("stock_symbol") or ""
    if not symbol:
        label = inv.get("label", "") or ""
        symbol = label[:6].upper() if label else ""
    market = inv.get("stock_market", "")
    suffix = suffixes.get(market, "")
    return f"{symbol}{suffix}".strip(".") if suffix else symbol


def _parse_powens_date(s: Any) -> date | None:
    """Parse a Powens date field. Accepts YYYY-MM-DD or ISO datetime strings."""
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


class PowensAggregator:
    """Implements IBankAggregator for the Powens provider.

    Instantiated per-user with a decrypted token. No global mutable state.
    """

    provider_name: str = "powens"

    def __init__(
        self,
        *,
        token: str,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        self._token = token
        self._user_id = user_id
        self._session = session

    # ── IBankAggregator methods ────────────────────────────────────────────

    async def get_accounts(self) -> list[BankAccount]:
        """Fetch all accounts the user has connected, mapped to BankAccount DTOs.

        Also fetches `/users/me/connections` to enrich each account with
        `institution_name` (e.g. "BNP Paribas"). If the /connections call fails,
        institution_name is left None and a warning is logged — the sync is not
        aborted, since institution_name is purely cosmetic.
        """
        powens_connections: list[dict] = []
        async with PowensClient(token=self._token) as client:
            try:
                powens_connections = await client.get_connections()
            except PowensError as exc:
                logger.warning(
                    "Failed to fetch Powens connections for user=%s, "
                    "institution_name will be null: %s",
                    self._user_id,
                    exc,
                )
            powens_accounts = await client.get_accounts()
        # Build {id_connection: bank_name} lookup.
        # Modern Powens uses `connector.name`; legacy responses use `bank.name`.
        bank_by_connection: dict[int, str] = {}
        for conn in powens_connections:
            conn_id = conn.get("id")
            if conn_id is None:
                continue
            connector = conn.get("connector") or conn.get("bank") or {}
            if isinstance(connector, dict):
                name = connector.get("name")
                if isinstance(name, str) and name:
                    try:
                        bank_by_connection[int(conn_id)] = name
                    except (TypeError, ValueError):
                        continue

        accounts: list[BankAccount] = []
        for acc in powens_accounts:
            try:
                institution_name: str | None = None
                id_connection = acc.get("id_connection")
                if id_connection is not None:
                    try:
                        institution_name = bank_by_connection.get(int(id_connection))
                    except (TypeError, ValueError):
                        institution_name = None

                accounts.append(
                    BankAccount(
                        provider=self.provider_name,
                        provider_account_id=str(acc["id"]),
                        name=acc.get("name", ""),
                        type=_map_account_type(acc.get("type")),
                        currency=_powens_currency(acc.get("currency")),
                        balance=float(acc.get("balance", 0) or 0),
                        iban=acc.get("iban"),
                        institution_name=institution_name,
                        last_synced_at=None,
                        raw_data=acc,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed Powens account %s: %s",
                    acc.get("id"),
                    exc,
                )
        return accounts

    async def get_investments(self, account_id: str) -> list[Investment]:
        """Fetch positions inside an investment account (PEA / CTO / life insurance)."""
        async with PowensClient(token=self._token) as client:
            powens_invs = await client.get_investments(int(account_id))

        investments: list[Investment] = []
        for inv in powens_invs:
            qty = inv.get("quantity") or 0
            if qty <= 0:
                continue  # closed positions
            try:
                investments.append(
                    Investment(
                        provider=self.provider_name,
                        provider_investment_id=str(inv["id"]),
                        provider_account_id=account_id,
                        ticker=_build_ticker(inv),
                        isin=inv.get("code"),
                        label=inv.get("label", ""),
                        quantity=float(qty),
                        unit_price=float(inv.get("unitprice", 0) or 0),
                        current_value=float(inv.get("valuation", 0) or 0),
                        currency=_powens_currency(inv.get("currency")),
                        raw_data=inv,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed Powens investment %s: %s",
                    inv.get("id"),
                    exc,
                )
        return investments

    async def get_transactions(
        self,
        account_id: str,
        limit: int = 100,
    ) -> list[Transaction]:
        """Fetch the most recent transactions for an account."""
        async with PowensClient(token=self._token) as client:
            powens_txs = await client.get_transactions(int(account_id), limit=limit)

        transactions: list[Transaction] = []
        for tx in powens_txs:
            tx_date = _parse_powens_date(tx.get("date") or tx.get("rdate"))
            if tx_date is None:
                logger.debug("Skipping Powens tx %s: no parsable date", tx.get("id"))
                continue
            try:
                # Category may be a dict {"id": ..., "name": "Food"} or absent
                cat_raw = tx.get("category")
                category = (
                    cat_raw.get("name")
                    if isinstance(cat_raw, dict)
                    else (cat_raw if isinstance(cat_raw, str) else None)
                )

                transactions.append(
                    Transaction(
                        provider=self.provider_name,
                        provider_transaction_id=str(tx["id"]),
                        provider_account_id=account_id,
                        amount=float(tx.get("value", 0) or 0),
                        currency=_powens_currency(tx.get("currency")),
                        transaction_date=tx_date,
                        description=tx.get("simplified_wording") or tx.get("wording") or "",
                        category=category,
                        raw_data=tx,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed Powens tx %s: %s", tx.get("id"), exc)
        return transactions

    async def sync(self) -> AggregatorSyncResult:
        """End-to-end sync: fetch all accounts + their investments/transactions.

        Pure function — no DB side effect. Caller is responsible for persistence.

        Behavior per account type:
        - PEA / CTO / LIFE_INSURANCE → get_investments
        - CHECKING / SAVINGS / CARD  → get_transactions (limit 100)
        - Others (LOAN, CRYPTO, OTHER) → balance only, no sub-fetch
        """
        now = datetime.now(UTC)
        try:
            accounts = await self.get_accounts()

            all_investments: list[Investment] = []
            all_transactions: list[Transaction] = []
            invest_types = {AccountType.PEA, AccountType.CTO, AccountType.LIFE_INSURANCE}
            tx_types = {AccountType.CHECKING, AccountType.SAVINGS, AccountType.CARD}

            for acc in accounts:
                if acc.type in invest_types:
                    all_investments.extend(await self.get_investments(acc.provider_account_id))
                elif acc.type in tx_types:
                    all_transactions.extend(
                        await self.get_transactions(acc.provider_account_id, limit=100)
                    )

            return AggregatorSyncResult(
                success=True,
                provider=self.provider_name,
                accounts=accounts,
                investments=all_investments,
                transactions=all_transactions,
                synced_at=now,
            )

        except PowensError as exc:
            logger.exception("PowensAggregator.sync failed for user=%s", self._user_id)
            return AggregatorSyncResult(
                success=False,
                provider=self.provider_name,
                error=str(exc),
                synced_at=now,
            )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Powens webhook handler — currently disabled (cf ADR-019).

        Re-enable in Phase A2 once we have powens_user_id mapping in DB.
        """
        from .webhooks import handle_webhook as _handle

        return await _handle(payload)
