"""A bank connected twice at Powens: the connection that brings nothing is removed by the sync."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.powens import aggregator as powens_aggregator

BP = {"name": "Banque Populaire"}
CHECKING = "FR7610207000012345678901234"


def _account(pid: int, connection: int, **kw) -> dict:
    account = {
        "id": pid,
        "id_connection": connection,
        "name": "COMPTE DE CHEQUES",
        "type": "checking",
        "currency": {"id": "EUR"},
        "balance": 1.0,
        "iban": CHECKING,
    }
    account.update(kw)
    return account


def _fake_powens(connections: list[dict], accounts: list[dict], deleted: list[int]):
    class FakePowens:
        def __init__(self, token: str):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get_connections(self):
            return connections

        async def get_accounts(self):
            return accounts

        async def get_transactions(self, account_id: int, limit: int = 100):
            return []

        async def get_investments(self, account_id: int):
            return []

        async def delete_connection(self, connection_id: int):
            deleted.append(connection_id)

    return FakePowens


async def _sync(monkeypatch, connections, accounts):
    deleted: list[int] = []
    monkeypatch.setattr(
        powens_aggregator, "PowensClient", _fake_powens(connections, accounts, deleted)
    )
    agg = powens_aggregator.PowensAggregator(token="t", user_id=uuid.uuid4(), session=MagicMock())
    result = await agg.sync()
    assert result.success
    return deleted, result


async def test_the_older_duplicate_connection_is_removed_at_powens(monkeypatch):
    connections = [
        {"id": 10, "bank": BP, "last_update": "2026-10-10 17:01:00", "error": None},
        {"id": 20, "bank": BP, "last_update": "2026-10-10 17:08:00", "error": None},
    ]
    accounts = [_account(101, 10), _account(201, 20)]
    deleted, result = await _sync(monkeypatch, connections, accounts)
    assert deleted == [10]
    assert [a.provider_account_id for a in result.accounts] == ["201"]
    assert result.accounts[0].raw_data["connection_works"] is True


async def test_an_old_broken_connection_with_a_loan_of_its_own_stays(monkeypatch):
    connections = [
        {"id": 10, "bank": BP, "last_update": "2026-10-09 04:00:00", "error": "wrongpass"},
        {"id": 20, "bank": BP, "last_update": "2026-10-10 17:08:00", "error": None},
    ]
    loan = _account(102, 10, type="loan", name="Prêt Jeune", iban=None, number="****7727")
    accounts = [_account(101, 10), loan, _account(201, 20)]
    deleted, result = await _sync(monkeypatch, connections, accounts)
    assert deleted == []
    works = {a.provider_account_id: a.raw_data["connection_works"] for a in result.accounts}
    assert works == {"101": False, "102": False, "201": True}


async def test_nothing_is_removed_while_the_new_connection_has_not_read_the_bank(monkeypatch):
    connections = [
        {"id": 10, "bank": BP, "last_update": "2026-10-10 17:01:00", "error": None},
        {"id": 20, "bank": BP, "last_update": None, "error": None},
    ]
    deleted, _ = await _sync(monkeypatch, connections, [_account(101, 10), _account(201, 20)])
    assert deleted == []


async def test_without_the_connections_list_nothing_is_removed(monkeypatch):
    # Whether a connection works is then unknown: nothing may go on a guess.
    deleted, _ = await _sync(monkeypatch, [], [_account(101, 10), _account(201, 20)])
    assert deleted == []
