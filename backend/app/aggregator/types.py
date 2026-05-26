"""Neutral DTOs and enums used across all bank aggregator implementations.

These types are intentionally provider-agnostic. Each implementation
(PowensAggregator, future BridgeAggregator) is responsible for mapping its
native schema to these DTOs.

Storage strategy: each DTO with persistent fields ("hot") plus a `raw_data`
field containing the full provider payload (ADR-013). The persistence layer
(repositories) stores both: hot fields as typed columns, raw_data as JSONB.

Cf ADR-008 (Powens aggregator), ADR-013 (hot+JSONB storage).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountType(StrEnum):
    """Type of bank account — provider-agnostic taxonomy.

    Each provider implementation maps its native types to these values.
    The full Powens type catalog has 30 entries — we group some of them
    (PERP/PERCO/PER/PEE/article83/RSP/madelin → RETIREMENT or similar) to
    keep the public taxonomy manageable. The raw Powens type is always
    preserved in `raw_data['type']` for forensic inspection.
    """

    # Cash-flow
    CHECKING = "checking"
    SAVINGS = "savings"
    CARD = "card"

    # Livrets / regulated savings
    LIVRET_A = "livret_a"
    LIVRET_B = "livret_b"
    LDDS = "ldds"
    LEP = "lep"
    PEL = "pel"
    CEL = "cel"
    CSL = "csl"
    CAT = "cat"
    DEPOSIT = "deposit"

    # Investment
    PEA = "pea"
    CTO = "cto"
    LIFE_INSURANCE = "life_insurance"
    CAPITALISATION = "capitalisation"
    REAL_ESTATE = "real_estate"
    CROWDLENDING = "crowdlending"

    # Retirement
    PER = "per"
    PERP = "perp"
    PERCO = "perco"
    MADELIN = "madelin"
    ARTICLE_83 = "article_83"

    # Employee savings
    PEE = "pee"
    RSP = "rsp"

    # Loans
    LOAN = "loan"
    MORTGAGE = "mortgage"
    CONSUMER_CREDIT = "consumer_credit"
    REVOLVING_CREDIT = "revolving_credit"

    # Misc
    JOINT = "joint"
    CRYPTO = "crypto"
    OTHER = "other"


# Convenience groupings — useful in business logic
INVEST_ACCOUNT_TYPES: set[AccountType] = {
    AccountType.PEA,
    AccountType.CTO,
    AccountType.LIFE_INSURANCE,
    AccountType.CAPITALISATION,
    AccountType.PER,
    AccountType.PERP,
    AccountType.PERCO,
    AccountType.MADELIN,
    AccountType.ARTICLE_83,
    AccountType.PEE,
    AccountType.RSP,
    AccountType.REAL_ESTATE,
    AccountType.CROWDLENDING,
}

LOAN_ACCOUNT_TYPES: set[AccountType] = {
    AccountType.LOAN,
    AccountType.MORTGAGE,
    AccountType.CONSUMER_CREDIT,
    AccountType.REVOLVING_CREDIT,
}

CASHFLOW_ACCOUNT_TYPES: set[AccountType] = {
    AccountType.CHECKING,
    AccountType.SAVINGS,
    AccountType.CARD,
    AccountType.DEPOSIT,
    AccountType.JOINT,
    AccountType.LIVRET_A,
    AccountType.LIVRET_B,
    AccountType.LDDS,
    AccountType.LEP,
    AccountType.PEL,
    AccountType.CEL,
    AccountType.CSL,
    AccountType.CAT,
}


class Loan(BaseModel):
    """Loan-specific details, attached to a BankAccount of loan-like type.

    Mirrors Powens' Loan sub-object structure. All fields optional because
    different lenders / loan types expose different subsets.
    """

    model_config = ConfigDict(extra="forbid")

    # Capital
    total_amount: float | None = None
    available_amount: float | None = None
    used_amount: float | None = None

    # Dates
    subscription_date: date | None = None
    maturity_date: date | None = None
    start_repayment_date: date | None = None
    deferred: bool | None = None

    # Payments
    next_payment_amount: float | None = None
    next_payment_date: date | None = None
    last_payment_amount: float | None = None
    last_payment_date: date | None = None
    nb_payments_done: int | None = None
    nb_payments_left: int | None = None
    nb_payments_total: int | None = None

    # Rate & duration
    rate: float | None = Field(None, description="Absolute % (2.0 = 2%)")
    duration_months: int | None = None

    # Insurance
    insurance_label: str | None = None
    insurance_amount: float | None = None
    insurance_rate: float | None = Field(None, description="Ratio 0-1")

    # Misc
    account_label: str | None = None
    loan_type: str | None = Field(
        None,
        description="mortgage | consumercredit | revolvingcredit | loan",
    )

    # Full provider payload (ADR-013)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class BankAccount(BaseModel):
    """A bank account exposed by an aggregator.

    Hot fields are typed; the full provider payload sits in `raw_data`
    (ADR-013). Provider-specific data that hasn't been promoted to a column
    is queryable via JSONB operators.
    """

    model_config = ConfigDict(extra="forbid")

    # ── Identification ─────────────────────────────────────────────────────
    provider: str = Field(..., description="e.g. 'powens', 'bridge', 'plaid'")
    provider_account_id: str = Field(
        ..., description="Stable account ID from the provider (cast to str)"
    )
    name: str
    type: AccountType
    currency: str = Field(..., description="ISO 4217 (e.g. 'EUR', 'USD')")
    institution_name: str | None = Field(None, description="e.g. 'BNP Paribas'")

    # ── Identifiers ────────────────────────────────────────────────────────
    iban: str | None = None
    bic: str | None = None
    number: str | None = None

    # ── Balance & valuation ────────────────────────────────────────────────
    balance: float = Field(..., description="Raw balance from the provider")
    valuation: float | None = Field(
        None,
        description=(
            "Provider-computed sum of holdings (for invest accounts). "
            "When non-null, prefer over `balance` for display (it is fresher)."
        ),
    )
    coming: float | None = None
    coming_balance: float | None = None

    # Gain/loss (computed by Powens for invest accounts)
    diff: float | None = None
    diff_percent: float | None = None
    prev_diff: float | None = None
    prev_diff_percent: float | None = None

    # ── Account context ────────────────────────────────────────────────────
    usage: str | None = Field(None, description="PRIV | ORGA | None")
    ownership: str | None = Field(None, description="owner | co-owner | attorney")
    company_name: str | None = Field(None, description="For PEE/PERCO/etc.")
    opening_date: date | None = None

    # ── State ──────────────────────────────────────────────────────────────
    bookmarked: bool = False
    display: bool = True
    powens_deleted_at: datetime | None = None
    powens_disabled_at: datetime | None = None
    powens_error: str | None = None
    powens_last_update: datetime | None = None

    # ── Sync tracking ──────────────────────────────────────────────────────
    last_synced_at: datetime | None = None

    # ── Loan sub-object (only when type is loan-like) ──────────────────────
    loan: Loan | None = None

    # ── Full provider payload (ADR-013) ────────────────────────────────────
    raw_data: dict[str, Any] = Field(default_factory=dict)


class Investment(BaseModel):
    """A holding/position inside an investment account (PEA, CTO, life ins, etc.)."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_investment_id: str
    provider_account_id: str = Field(..., description="Parent BankAccount.provider_account_id")
    ticker: str = Field(..., description="Normalized yfinance-style ticker, e.g. 'DCAM.PA'")
    isin: str | None = None
    label: str
    quantity: float
    unit_price: float = Field(..., description="Average unit cost (PRU)")
    current_value: float = Field(..., description="Current valuation in account currency")
    currency: str
    raw_data: dict[str, Any] = Field(default_factory=dict)


class Transaction(BaseModel):
    """A bank transaction (operation on a checking, savings or card account)."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    provider_transaction_id: str
    provider_account_id: str
    amount: float = Field(..., description="Positive = credit, negative = debit")
    currency: str
    transaction_date: date = Field(..., description="Transaction date (booking date)")
    description: str
    category: str | None = Field(None, description="Provider category if available")
    raw_data: dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """Result of a full aggregator sync — returned by IBankAggregator.sync()."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    provider: str
    accounts: list[BankAccount] = Field(default_factory=list)
    investments: list[Investment] = Field(default_factory=list)
    transactions: list[Transaction] = Field(default_factory=list)
    error: str | None = None
    synced_at: datetime
