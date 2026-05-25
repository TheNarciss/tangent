"""Unit tests for PowensAggregator — provider→DTO mapping.

Uses httpx.MockTransport to simulate Powens API responses, so no real
network call. Tests focus on the mapping correctness, not the HTTP layer.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.aggregator import AccountType, BankAccount, Investment, Transaction
from app.powens.aggregator import PowensAggregator

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_session():
    """Minimal AsyncSession stub — we don't hit DB in these tests."""
    return MagicMock()


@pytest.fixture
def aggregator(fake_session):
    return PowensAggregator(
        token="fake-token",
        user_id=uuid.uuid4(),
        session=fake_session,
    )


# ── get_accounts mapping ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_accounts_maps_pea_correctly(aggregator, monkeypatch):
    fake_data = [
        {
            "id": 1234,
            "name": "PEA Titres",
            "type": "pea",
            "currency": {"id": "EUR", "symbol": "€"},
            "balance": 15000.50,
            "iban": None,
        }
    ]

    # Patch PowensClient.get_accounts to return fake_data
    async def fake_get_accounts(self):
        return fake_data

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake_get_accounts)
    # Also patch __aenter__/__aexit__ to be no-ops
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )
    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)

    accounts = await aggregator.get_accounts()
    assert len(accounts) == 1
    a = accounts[0]
    assert isinstance(a, BankAccount)
    assert a.provider == "powens"
    assert a.provider_account_id == "1234"  # cast to str
    assert a.name == "PEA Titres"
    assert a.type == AccountType.PEA
    assert a.currency == "EUR"
    assert a.balance == 15000.50


@pytest.mark.asyncio
async def test_get_accounts_unknown_type_falls_back_to_other(aggregator, monkeypatch):
    fake_data = [
        {"id": 99, "name": "Exotic", "type": "rocket_fund", "currency": "EUR", "balance": 1}
    ]
    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )

    async def fake(self):
        return fake_data

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake)

    accounts = await aggregator.get_accounts()
    assert accounts[0].type == AccountType.OTHER


# ── get_investments mapping ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_investments_skips_zero_quantity(aggregator, monkeypatch):
    fake_data = [
        {
            "id": 1,
            "label": "Danone",
            "code": "FR0000120644",
            "stock_symbol": "BN",
            "stock_market": "Euronext Paris",
            "quantity": 0,  # closed position — must skip
            "unitprice": 0,
            "valuation": 0,
        },
        {
            "id": 2,
            "label": "Air Liquide",
            "code": "FR0000120073",
            "stock_symbol": "AI",
            "stock_market": "Euronext Paris",
            "quantity": 5,
            "unitprice": 150.0,
            "valuation": 780.0,
            "currency": {"id": "EUR"},
        },
    ]

    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )

    async def fake(self, account_id):
        return fake_data

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_investments", fake)

    invs = await aggregator.get_investments("42")
    assert len(invs) == 1
    inv = invs[0]
    assert isinstance(inv, Investment)
    assert inv.ticker == "AI.PA"
    assert inv.label == "Air Liquide"
    assert inv.quantity == 5.0
    assert inv.current_value == 780.0
    assert inv.provider_account_id == "42"


# ── get_transactions mapping ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_transactions_maps_amount_and_category(aggregator, monkeypatch):
    fake_data = [
        {
            "id": 11,
            "date": "2026-05-20",
            "value": -42.50,
            "currency": "EUR",
            "wording": "CARREFOUR",
            "simplified_wording": "Carrefour",
            "category": {"id": 1, "name": "Groceries"},
        },
        {
            "id": 12,
            "date": "not-a-date",  # must skip
            "value": 100,
            "wording": "Junk",
        },
    ]

    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )

    async def fake(self, account_id, limit=100):
        return fake_data

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_transactions", fake)

    txs = await aggregator.get_transactions("100", limit=50)
    assert len(txs) == 1  # malformed date one skipped
    tx = txs[0]
    assert isinstance(tx, Transaction)
    assert tx.amount == -42.50
    assert tx.transaction_date == date(2026, 5, 20)
    assert tx.description == "Carrefour"
    assert tx.category == "Groceries"
