"""Neutral DTOs and enums used across all bank aggregator implementations.

These types are intentionally provider-agnostic. Each implementation
(PowensAggregator, future BridgeAggregator) is responsible for mapping its
native schema to these DTOs.

For extensibility, each DTO has an optional `raw_data` field where providers
can stash their original payload (useful for debug and for fields not yet
promoted to the public DTO).

Cf ADR-008 (Powens aggregator + future-proof abstraction layer).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountType(StrEnum):
    """Type of bank account — provider-agnostic taxonomy.

    Each provider implementation maps its native types to these values.
    Examples:
    - Powens "checking" → CHECKING
    - Bridge "checking" → CHECKING
    - Powens "pea"      → PEA
    - Powens "lifeinsurance" → LIFE_INSURANCE
    """

    CHECKING = "checking"
    SAVINGS = "savings"
    PEA = "pea"
    CTO = "cto"
    LIFE_INSURANCE = "life_insurance"
    LOAN = "loan"
    CARD = "card"
    CRYPTO = "crypto"
    OTHER = "other"


class BankAccount(BaseModel):
    """A bank account exposed by an aggregator.

    Mandatory fields = common denominator across Powens, Bridge, Plaid.
    Provider-specific data goes in `raw_data` for opaque pass-through.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., description="e.g. 'powens', 'bridge', 'plaid'")
    provider_account_id: str = Field(
        ..., description="Stable account ID from the provider (cast to str)"
    )
    name: str
    type: AccountType
    currency: str = Field(..., description="ISO 4217 (e.g. 'EUR', 'USD')")
    balance: float = Field(..., description="Current balance in account currency")
    iban: str | None = None
    institution_name: str | None = Field(None, description="e.g. 'BNP Paribas', 'Banque Populaire'")
    last_synced_at: datetime | None = None
    raw_data: dict[str, Any] | None = Field(
        None, description="Original provider payload, for debug / extensions"
    )


class Investment(BaseModel):
    """A holding/position inside an investment account (PEA, CTO, life insurance)."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_investment_id: str
    provider_account_id: str = Field(..., description="parent BankAccount.provider_account_id")
    ticker: str = Field(..., description="Normalized yfinance-style ticker, e.g. 'DCAM.PA'")
    isin: str | None = None
    label: str
    quantity: float
    unit_price: float = Field(..., description="Average unit cost (PRU)")
    current_value: float = Field(..., description="Current valuation in account currency")
    currency: str
    raw_data: dict[str, Any] | None = None


class Transaction(BaseModel):
    """A bank transaction (operation on a checking, savings or card account)."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_transaction_id: str
    provider_account_id: str
    amount: float = Field(..., description="Positive = credit (income), Negative = debit (expense)")
    currency: str
    transaction_date: date = Field(..., description="Transaction date (booking date)")
    description: str
    category: str | None = Field(
        None, description="Provider-supplied category (Powens/Bridge auto-categorize)"
    )
    raw_data: dict[str, Any] | None = None


class SyncResult(BaseModel):
    """Outcome of a sync run, returned by IBankAggregator.sync()."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    provider: str
    accounts: list[BankAccount] = []
    investments: list[Investment] = []
    transactions: list[Transaction] = []
    error: str | None = None
    synced_at: datetime
