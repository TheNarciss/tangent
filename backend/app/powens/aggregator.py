"""Powens implementation of IBankAggregator (Phase A — full mapping + ADR-013).

Translates Powens-native API responses into the neutral DTOs defined in
`app/aggregator/types.py`. No side effects on DB — callers (routes) are
responsible for persistence.

Storage strategy: each DTO carries `raw_data` with the full Powens payload
(ADR-013). The persistence layer extracts "hot" fields to typed columns and
stores raw_data as JSONB.

Cf ADR-008 (aggregator interface), ADR-013 (hot+JSONB storage), ADR-019.
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
    Loan,
    Transaction,
)
from ..aggregator import (
    SyncResult as AggregatorSyncResult,
)
from ..aggregator.types import LOAN_ACCOUNT_TYPES
from . import yaml_config
from .client import PowensClient, PowensError

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────


def _powens_currency(value: Any) -> str:
    """Extract ISO 4217 code from a Powens currency field (dict or string)."""
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


def _parse_date(value: Any) -> date | None:
    """Parse a Powens date field (YYYY-MM-DD or ISO datetime). Returns None on failure."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a Powens datetime string. Returns None on failure."""
    if not isinstance(value, str) or not value:
        return None
    try:
        # Powens uses "YYYY-MM-DD HH:MM:SS" (no timezone)
        # Treat as UTC for consistency with our DB tz-aware columns
        return datetime.fromisoformat(value.replace(" ", "T")).replace(tzinfo=UTC)
    except ValueError:
        return None


def _extract_institution_name(conn: dict) -> str | None:
    """Pull institution name from a Powens connection dict.

    Supports both modern (`connector.name`) and legacy (`bank.name`) shapes.
    """
    connector = conn.get("connector")
    if isinstance(connector, dict):
        name = connector.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    bank = conn.get("bank")
    if isinstance(bank, dict):
        name = bank.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _extract_loan_dto(loan_dict: dict) -> Loan:
    """Map a Powens Loan sub-object dict into a Loan DTO.

    Hot fields are extracted; the full dict is preserved in raw_data.
    """
    return Loan(
        total_amount=loan_dict.get("total_amount"),
        available_amount=loan_dict.get("available_amount"),
        used_amount=loan_dict.get("used_amount"),
        subscription_date=_parse_date(loan_dict.get("subscription_date")),
        maturity_date=_parse_date(loan_dict.get("maturity_date")),
        start_repayment_date=_parse_date(loan_dict.get("start_repayment_date")),
        deferred=loan_dict.get("deferred"),
        next_payment_amount=loan_dict.get("next_payment_amount"),
        next_payment_date=_parse_date(loan_dict.get("next_payment_date")),
        last_payment_amount=loan_dict.get("last_payment_amount"),
        last_payment_date=_parse_date(loan_dict.get("last_payment_date")),
        nb_payments_done=loan_dict.get("nb_payments_done"),
        nb_payments_left=loan_dict.get("nb_payments_left"),
        nb_payments_total=loan_dict.get("nb_payments_total"),
        rate=loan_dict.get("rate"),
        duration_months=loan_dict.get("duration"),
        insurance_label=loan_dict.get("insurance_label"),
        insurance_amount=loan_dict.get("insurance_amount"),
        insurance_rate=loan_dict.get("insurance_rate"),
        account_label=loan_dict.get("account_label"),
        loan_type=loan_dict.get("type"),
        raw_data=loan_dict,
    )


def _extract_bank_account_dto(
    acc: dict,
    *,
    institution_name: str | None,
    synced_at: datetime,
) -> BankAccount:
    """Map a Powens account dict into a BankAccount DTO with all hot fields."""
    acc_type = _map_account_type(acc.get("type"))

    loan_dict = acc.get("loan")
    loan_dto: Loan | None = None
    if isinstance(loan_dict, dict) and acc_type in LOAN_ACCOUNT_TYPES:
        loan_dto = _extract_loan_dto(loan_dict)

    return BankAccount(
        # Identification
        provider="powens",
        provider_account_id=str(acc["id"]),
        name=acc.get("name", "") or "",
        type=acc_type,
        currency=_powens_currency(acc.get("currency")),
        institution_name=institution_name,
        # Identifiers
        iban=acc.get("iban"),
        bic=acc.get("bic"),
        number=acc.get("number"),
        # Balance & valuation
        balance=float(acc.get("balance", 0) or 0),
        valuation=acc.get("valuation"),
        coming=acc.get("coming"),
        coming_balance=acc.get("coming_balance"),
        # Gain/loss
        diff=acc.get("diff"),
        diff_percent=acc.get("diff_percent"),
        prev_diff=acc.get("prev_diff"),
        prev_diff_percent=acc.get("prev_diff_percent"),
        # Context
        usage=acc.get("usage"),
        ownership=acc.get("ownership"),
        company_name=acc.get("company_name"),
        opening_date=_parse_date(acc.get("opening_date")),
        # State
        bookmarked=bool(acc.get("bookmarked", 0)),
        display=bool(acc.get("display", True)),
        powens_deleted_at=_parse_datetime(acc.get("deleted")),
        powens_disabled_at=_parse_datetime(acc.get("disabled")),
        powens_error=acc.get("error"),
        powens_last_update=_parse_datetime(acc.get("last_update")),
        # Sync tracking
        last_synced_at=synced_at,
        # Loan sub-object
        loan=loan_dto,
        # Full raw payload (ADR-013)
        raw_data=acc,
    )


# ── Aggregator class ───────────────────────────────────────────────────────


class PowensAggregator:
    """Implements IBankAggregator for the Powens provider."""

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
        """Fetch all accounts and enrich each with its institution name.

        Two HTTP calls: /connections (for the institution map) and /accounts.
        /connections failure degrades gracefully — accounts are still returned,
        just without `institution_name`.
        """
        async with PowensClient(token=self._token) as client:
            id_to_institution: dict[int, str] = {}
            try:
                connections = await client.get_connections()
                for conn in connections:
                    conn_id = conn.get("id")
                    name = _extract_institution_name(conn)
                    if isinstance(conn_id, int) and name:
                        id_to_institution[conn_id] = name
            except PowensError as exc:
                logger.warning(
                    "Powens [user=%s]: /connections failed (institution_name will be null): %s",
                    self._user_id,
                    exc,
                )

            powens_accounts = await client.get_accounts()

        synced_at = datetime.now(UTC)

        accounts: list[BankAccount] = []
        for acc in powens_accounts:
            try:
                conn_id = acc.get("id_connection")
                institution_name: str | None = None
                if isinstance(conn_id, int):
                    institution_name = id_to_institution.get(conn_id)

                accounts.append(
                    _extract_bank_account_dto(
                        acc,
                        institution_name=institution_name,
                        synced_at=synced_at,
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
        """Fetch positions inside an investment account."""
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
                        label=inv.get("label", "") or "",
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
            tx_date = _parse_date(tx.get("date") or tx.get("rdate"))
            if tx_date is None:
                logger.debug("Skipping Powens tx %s: no parsable date", tx.get("id"))
                continue
            try:
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
        """End-to-end sync: fetch all accounts + sub-resources (per type)."""
        from ..aggregator.types import CASHFLOW_ACCOUNT_TYPES, INVEST_ACCOUNT_TYPES

        now = datetime.now(UTC)
        try:
            accounts = await self.get_accounts()

            all_investments: list[Investment] = []
            all_transactions: list[Transaction] = []

            for acc in accounts:
                if acc.type in INVEST_ACCOUNT_TYPES:
                    all_investments.extend(await self.get_investments(acc.provider_account_id))
                elif acc.type in CASHFLOW_ACCOUNT_TYPES:
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
        """Powens webhook handler — currently disabled (cf ADR-019)."""
        from .webhooks import handle_webhook as _handle

        return await _handle(payload)
