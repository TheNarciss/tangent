"""Enable Banking: the JWT we sign, and the payloads we turn into our DTOs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.aggregator.types import AccountType
from app.db.models import EnableBankingSession
from app.enablebanking import aggregator, client


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return pem, key.public_key()


def test_the_bearer_token_is_signed_for_enable_banking(keypair):
    pem, public = keypair

    token = client.bearer_token(app_id="app-1", private_key_pem=pem)

    assert jwt.get_unverified_header(token)["kid"] == "app-1"
    claims = jwt.decode(token, public, algorithms=["RS256"], audience="api.enablebanking.com")
    assert claims["iss"] == "enablebanking.com"
    assert claims["exp"] - claims["iat"] == 3600


def test_an_account_becomes_a_checking_account_with_its_booked_balance():
    acc = {
        "uid": "u-1",
        "account_id": {"iban": "LT00REVO0000000000"},
        "name": "Main",
        "currency": "eur",
        "cash_account_type": "CACC",
        "usage": "PRIV",
    }
    balances = [
        {"balance_type": "ITAV", "balance_amount": {"amount": "120.50", "currency": "EUR"}},
        {"balance_type": "CLBD", "balance_amount": {"amount": "100.00", "currency": "EUR"}},
    ]

    dto = aggregator.account_dto(
        acc,
        balance=aggregator.pick_balance(balances),
        institution_name="Revolut",
        session_key="row-1",
        synced_at=datetime.now(UTC),
    )

    assert dto.provider == "enablebanking"
    assert dto.type == AccountType.CHECKING
    assert dto.currency == "EUR"
    assert dto.balance == 100.0  # booked beats available
    assert dto.iban == "LT00REVO0000000000"
    assert dto.institution_name == "Revolut"
    assert dto.raw_data["enablebanking_session"] == "row-1"


def test_without_a_booked_balance_the_first_one_the_bank_sends_is_used():
    assert (
        aggregator.pick_balance([{"balance_type": "ZZZZ", "balance_amount": {"amount": "7"}}])
        == 7.0
    )
    assert aggregator.pick_balance([]) is None


def test_a_debit_is_negative_and_named_after_its_remittance_or_counterparty():
    tx = {
        "entry_reference": "ref-42",
        "transaction_amount": {"amount": "12.30", "currency": "EUR"},
        "credit_debit_indicator": "DBIT",
        "creditor": {"name": "Carrefour"},
        "status": "BOOK",
        "booking_date": "2026-09-10",
        "remittance_information": ["Carrefour City Paris"],
    }

    dto = aggregator.transaction_dto(tx, account_uid="u-1")

    assert dto is not None
    assert dto.amount == -12.30
    assert dto.description == "Carrefour City Paris"
    assert dto.provider_transaction_id == "ref-42"
    assert str(dto.transaction_date) == "2026-09-10"

    no_remittance = {**tx, "remittance_information": []}
    assert aggregator.transaction_dto(no_remittance, account_uid="u-1").description == "Carrefour"


def test_a_credit_is_positive_and_a_pending_one_is_skipped():
    credit = {
        "transaction_amount": {"amount": "100", "currency": "EUR"},
        "credit_debit_indicator": "CRDT",
        "debtor": {"name": "BNP"},
        "booking_date": "2026-09-01",
    }
    assert aggregator.transaction_dto(credit, account_uid="u").amount == 100.0
    assert aggregator.transaction_dto({**credit, "status": "PDNG"}, account_uid="u") is None


def test_a_transaction_without_reference_gets_a_stable_id():
    tx = {
        "transaction_amount": {"amount": "5", "currency": "EUR"},
        "credit_debit_indicator": "DBIT",
        "booking_date": "2026-09-01",
        "remittance_information": ["Coffee"],
    }

    assert aggregator.transaction_id(tx) == aggregator.transaction_id(dict(tx))
    assert aggregator.transaction_id(tx) != aggregator.transaction_id(
        {**tx, "booking_date": "2026-09-02"}
    )


def test_a_consent_is_expired_once_valid_until_has_passed():
    row = EnableBankingSession(
        user_id=uuid.uuid4(),
        encrypted_session_id="x",
        bank_name="Revolut",
        bank_country="FR",
        valid_until=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert aggregator.is_expired(row)
    row.valid_until = datetime.now(UTC) + timedelta(days=1)
    assert not aggregator.is_expired(row)


class _FakeClient:
    """Enable Banking as seen by the aggregator: one account, transactions that fail."""

    def __init__(self, *, fail_transactions: bool):
        self.fail = fail_transactions
        self.windows: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def get_session(self, session_id):
        # As the API answers: uids only, details behind their own endpoint.
        return {"accounts": ["u-1"], "accounts_data": [{"uid": "u-1", "identification_hash": "h"}]}

    async def get_account_details(self, uid):
        return {"name": "Main", "currency": "EUR", "cash_account_type": "CACC"}

    async def get_balances(self, uid):
        return [{"balance_type": "CLBD", "balance_amount": {"amount": "10", "currency": "EUR"}}]

    async def get_transactions(self, uid, *, date_from=None, date_to=None):
        self.windows.append(date_from)
        if self.fail:
            raise client.EnableBankingError("Enable Banking a répondu 500: boom", status=500)
        if len(self.windows) == 1:
            raise client.EnableBankingError("Enable Banking a répondu 400: date_from", status=400)
        return [
            {
                "entry_reference": "r1",
                "transaction_amount": {"amount": "3", "currency": "EUR"},
                "credit_debit_indicator": "DBIT",
                "booking_date": "2026-09-10",
                "remittance_information": ["Coffee"],
            }
        ]


def _aggregator(fake, since):
    return aggregator.EnableBankingAggregator(
        session_id="s",
        session_key="k",
        institution_name="Revolut",
        user_id=uuid.uuid4(),
        since=since,
    )


@pytest.mark.asyncio
async def test_accounts_are_kept_when_their_transactions_cannot_be_read(monkeypatch):
    fake = _FakeClient(fail_transactions=True)
    monkeypatch.setattr(aggregator, "EnableBankingClient", lambda: fake)

    result = await _aggregator(fake, datetime.now(UTC).date() - timedelta(days=700)).sync()

    assert result.success
    assert [a.name for a in result.accounts] == ["Main"]
    assert result.accounts[0].provider_account_id == "u-1"
    assert result.transactions == []
    assert result.error and "Main" in result.error


@pytest.mark.asyncio
async def test_a_refused_window_is_retried_over_the_guaranteed_ninety_days(monkeypatch):
    fake = _FakeClient(fail_transactions=False)
    monkeypatch.setattr(aggregator, "EnableBankingClient", lambda: fake)
    since = datetime.now(UTC).date() - timedelta(days=700)

    result = await _aggregator(fake, since).sync()

    assert [w for w in fake.windows] == [since, datetime.now(UTC).date() - timedelta(days=89)]
    assert len(result.transactions) == 1 and result.error is None
