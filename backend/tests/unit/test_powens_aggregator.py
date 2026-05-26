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

    async def fake_get_accounts(self):
        return fake_data

    async def fake_get_connections(self):
        return []

    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_connections", fake_get_connections)
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake_get_accounts)

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

    async def fake_get_accounts(self):
        return fake_data

    async def fake_get_connections(self):
        return []

    monkeypatch.setattr("app.powens.aggregator.PowensClient.__init__", lambda self, token: None)
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aenter__",
        lambda self: AsyncMock(return_value=self)(),
    )
    monkeypatch.setattr(
        "app.powens.aggregator.PowensClient.__aexit__",
        lambda self, *_: AsyncMock()(),
    )
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_connections", fake_get_connections)
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake_get_accounts)

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


# ── institution_name mapping via /connections ──────────────────────────────


@pytest.mark.asyncio
async def test_get_accounts_maps_institution_name_from_connections(aggregator, monkeypatch):
    """Each account is enriched with institution_name via id_connection → connector.name."""
    fake_connections = [
        {"id": 10, "connector": {"id": 59, "name": "BNP Paribas"}},
        {"id": 20, "connector": {"id": 99, "name": "Banque Populaire"}},
    ]
    fake_accounts = [
        {
            "id": 1234,
            "id_connection": 10,
            "name": "PEA Titres",
            "type": "pea",
            "currency": {"id": "EUR"},
            "balance": 15000.0,
        },
        {
            "id": 5678,
            "id_connection": 20,
            "name": "Livret A",
            "type": "savings",
            "currency": {"id": "EUR"},
            "balance": 5000.0,
        },
        {
            "id": 9999,
            # No id_connection — institution_name should be None
            "name": "Orphan",
            "type": "checking",
            "currency": {"id": "EUR"},
            "balance": 0.0,
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

    async def fake_conns(self):
        return fake_connections

    async def fake_accs(self):
        return fake_accounts

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_connections", fake_conns)
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake_accs)

    accounts = await aggregator.get_accounts()
    assert len(accounts) == 3
    by_name = {a.name: a for a in accounts}
    assert by_name["PEA Titres"].institution_name == "BNP Paribas"
    assert by_name["Livret A"].institution_name == "Banque Populaire"
    assert by_name["Orphan"].institution_name is None


@pytest.mark.asyncio
async def test_get_accounts_falls_back_when_connections_fail(aggregator, monkeypatch):
    """If /connections fails, accounts still returned with institution_name=None."""
    from app.powens.client import PowensError

    fake_accounts = [
        {
            "id": 1,
            "id_connection": 10,
            "name": "PEA Titres",
            "type": "pea",
            "currency": "EUR",
            "balance": 1.0,
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

    async def boom(self):
        raise PowensError("simulated /connections outage")

    async def fake_accs(self):
        return fake_accounts

    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_connections", boom)
    monkeypatch.setattr("app.powens.aggregator.PowensClient.get_accounts", fake_accs)

    accounts = await aggregator.get_accounts()
    assert len(accounts) == 1
    assert accounts[0].institution_name is None
