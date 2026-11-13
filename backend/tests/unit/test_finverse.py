"""Finverse payloads → our accounts and transactions, the client's paging, the per-link sync."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import httpx
import pytest

from app.aggregator.types import AccountType
from app.db.models import FinverseConnection
from app.finverse import aggregator as fv
from app.finverse import client as fv_client
from app.powens.crypto import decrypt_token, encrypt_token
from app.routers import finverse as routes

NOW = datetime(2026, 10, 27, 8, 0, tzinfo=UTC)


def _account(**kw) -> dict:
    acc = {
        "account_id": "acc-1",
        "account_name": "eMulti-Currency Autosave",
        "account_currency": "SGD",
        "balance": {"value": 1234.5, "currency": "SGD"},
        "account_number_masked": "XXXXXX1234",
        "account_type": {"type": "DEPOSIT", "subtype": "SAVINGS"},
        "is_closed": False,
    }
    acc.update(kw)
    return acc


def _dto(acc: dict):
    return fv.account_dto(acc, institution_name="DBS", connection_key="row-1", synced_at=NOW)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ({"type": "DEPOSIT", "subtype": "CURRENT"}, AccountType.CHECKING),
        ({"type": "DEPOSIT", "subtype": "SAVINGS"}, AccountType.SAVINGS),
        ({"type": "DEPOSIT", "subtype": "TIME_DEPOSIT"}, AccountType.DEPOSIT),
        ({"type": "DEPOSIT"}, AccountType.CHECKING),
        ({"type": "CARD", "subtype": "CREDIT_CARD"}, AccountType.CARD),
        ({"type": "LOAN", "subtype": "MORTGAGE"}, AccountType.MORTGAGE),
        ({"type": "LOAN", "subtype": "PERSONAL_LOAN"}, AccountType.LOAN),
        ({"type": "INVESTMENT", "subtype": "SECURITIES"}, AccountType.OTHER),
        ({"type": "UNKNOWN"}, AccountType.OTHER),
        (None, AccountType.OTHER),
    ],
)
def test_account_types_map_to_ours(kind, expected):
    assert fv.account_type({"account_type": kind}) == expected


def test_an_account_keeps_its_currency_number_and_link():
    dto = _dto(_account())

    assert dto is not None
    assert (dto.provider, dto.provider_account_id) == ("finverse", "acc-1")
    assert dto.currency == "SGD"
    assert dto.balance == 1234.5
    assert dto.number == "XXXXXX1234"
    assert dto.institution_name == "DBS"
    assert dto.raw_data["finverse_connection"] == "row-1"


def test_what_is_owed_reads_negative():
    card = _dto(_account(account_type={"type": "CARD", "subtype": "CREDIT_CARD"}))
    loan = _dto(_account(account_type={"type": "LOAN", "subtype": "MORTGAGE"}))

    assert card is not None and card.balance == -1234.5
    assert loan is not None and loan.balance == -1234.5


def test_closed_and_parent_accounts_are_left_out():
    assert _dto(_account(is_closed=True)) is None
    assert _dto(_account(is_parent=True)) is None


def test_a_posted_transaction_keeps_its_sign_and_date():
    tx = {
        "transaction_id": "tx-1",
        "account_id": "acc-1",
        "is_pending": False,
        "posted_date": "2026-10-20",
        "amount": {"value": -12.4, "currency": "SGD"},
        "description": "",
        "merchant_name": "Kopitiam",
    }

    dto = fv.transaction_dto(tx, currency="SGD")

    assert dto is not None
    assert dto.amount == -12.4
    assert dto.transaction_date == date(2026, 10, 20)
    assert dto.description == "Kopitiam"
    assert dto.category is None  # left to our own categorisation


def test_a_pending_transaction_waits_until_it_is_posted():
    tx = {"transaction_id": "tx-2", "account_id": "acc-1", "is_pending": True}

    assert fv.transaction_dto(tx, currency="SGD") is None


class _Status:
    def __init__(self, statuses: list[str]):
        self.statuses = statuses
        self.calls = 0

    async def login_identity(self, token: str) -> dict:
        self.calls += 1
        return {"login_identity": {"status": self.statuses.pop(0)}}


async def test_the_first_read_waits_until_finverse_has_read_the_bank():
    client = _Status(["CONNECTION_COMPLETE", "DATA_RETRIEVAL_COMPLETE", "unused"])

    status = await fv.wait_for_data(client, "tok", delay=0)  # type: ignore[arg-type]

    assert status == "DATA_RETRIEVAL_COMPLETE"
    assert client.calls == 2


def _client_with(handler) -> fv_client.FinverseClient:
    client = fv_client.FinverseClient(base_url="https://fv.test")
    client._client = httpx.AsyncClient(
        base_url="https://fv.test", transport=httpx.MockTransport(handler)
    )
    return client


async def test_transactions_are_read_page_after_page(monkeypatch):
    monkeypatch.setattr(fv_client, "PAGE_SIZE", 2)
    offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer li-token"
        offset = int(request.url.params["offset"])
        offsets.append(request.url.params["offset"])
        page = [{"transaction_id": str(i)} for i in range(offset, min(offset + 2, 3))]
        return httpx.Response(200, json={"transactions": page, "total_transactions": 3})

    async with _client_with(handler) as client:
        rows = await client.transactions("li-token")

    assert [r["transaction_id"] for r in rows] == ["0", "1", "2"]
    assert offsets == ["0", "2"]


async def test_the_customer_token_is_asked_once_and_errors_carry_finverse_message():
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/auth/customer/token":
            return httpx.Response(200, json={"access_token": "cust"})
        assert request.headers["Authorization"] == "Bearer cust"
        if request.url.path == "/auth/token/refresh":
            return httpx.Response(401, json={"error": {"message": "refresh token expired"}})
        return httpx.Response(200, json={"link_url": "https://link.test/x"})

    async with _client_with(handler) as client:
        assert await client.link_url(user_ref="u", state="s") == "https://link.test/x"
        with pytest.raises(fv_client.FinverseError, match="refresh token expired") as caught:
            await client.refresh("old")

    assert caught.value.status == 401
    assert paths == ["/auth/customer/token", "/link/token", "/auth/token/refresh"]


class _FakeFinverse:
    """Answers the calls a daily read makes."""

    fail = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def refresh(self, refresh_token: str) -> dict:
        if self.fail:
            raise fv_client.FinverseError("Finverse a répondu 401: expired", status=401)
        assert refresh_token == "refresh-1"
        return {"access_token": "li-token", "refresh_token": "refresh-2"}

    async def accounts(self, token: str) -> dict:
        return {"accounts": [_account()], "institution": {"institution_name": "DBS Bank"}}

    async def transactions(self, token: str) -> list[dict]:
        posted = {
            "transaction_id": "tx-1",
            "account_id": "acc-1",
            "posted_date": "2026-10-20",
            "amount": {"value": -3.5, "currency": "SGD"},
            "description": "GRAB",
        }
        stray = {**posted, "transaction_id": "tx-2", "account_id": "not-listed"}
        return [posted, stray]


def _row() -> FinverseConnection:
    return FinverseConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        login_identity_id="li-1",
        encrypted_refresh_token=encrypt_token("refresh-1"),
        institution_name="Banque",
    )


async def test_a_daily_read_keeps_the_new_refresh_token(monkeypatch):
    monkeypatch.setattr(fv, "FinverseClient", _FakeFinverse)
    row = _row()

    result = await fv.sync_row(row)

    assert result.success
    assert decrypt_token(row.encrypted_refresh_token) == "refresh-2"
    assert row.institution_name == "DBS Bank"
    assert row.last_error is None and row.last_sync_at is not None
    assert [a.provider_account_id for a in result.accounts] == ["acc-1"]
    assert [t.provider_transaction_id for t in result.transactions] == ["tx-1"]


async def test_a_failed_read_shows_on_the_link(monkeypatch):
    monkeypatch.setattr(fv, "FinverseClient", type("Failing", (_FakeFinverse,), {"fail": True}))
    row = _row()

    result = await fv.sync_row(row)

    assert not result.success
    assert "expired" in (row.last_error or "")
    assert decrypt_token(row.encrypted_refresh_token) == "refresh-1"


def test_the_state_names_the_user_and_fits_finverse_limit(monkeypatch):
    monkeypatch.setattr(routes, "_STATE_SECRET", "test-secret-for-the-finverse-state-32b")
    user_id = uuid.uuid4()

    state = routes._sign_state(user_id, "app")

    assert len(state) <= 100  # Finverse: « state in body should be at most 100 chars long »
    assert routes._read_state(state) == {"sub": str(user_id), "platform": "app"}


def test_a_forged_expired_or_foreign_state_is_refused(monkeypatch):
    monkeypatch.setattr(routes, "_STATE_SECRET", "test-secret-for-the-finverse-state-32b")
    state = routes._sign_state(uuid.uuid4(), "web")
    body, _, signature = state.rpartition(".")
    other_user = f"{uuid.uuid4().hex}.web.{body.split('.')[2]}"

    for bad in (f"{other_user}.{signature}", "junk", "", f"{body}.x", "a.b.c.d.e", f"{body}.é"):
        with pytest.raises(ValueError):
            routes._read_state(bad)

    monkeypatch.setattr(routes, "_STATE_SECRET", "another-secret-another-secret-123")
    with pytest.raises(ValueError):
        routes._read_state(state)

    monkeypatch.setattr(routes, "_STATE_SECRET", "test-secret-for-the-finverse-state-32b")
    monkeypatch.setattr(routes.time, "time", lambda: 4_000_000_000)
    with pytest.raises(ValueError):
        routes._read_state(state)


def test_an_error_code_from_finverse_is_made_safe_for_a_url():
    assert routes._slug("access_denied") == "access_denied"
    assert routes._slug("a&b=c<script>") == "abcscript"
    assert routes._slug("&&&") == "unknown"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            {
                "code": 604,
                "error": {
                    "error_code": "INVALID_PARAMETER",
                    "details": "client_secret in body should be at least 64 chars long",
                    "message": "The parameters provided are invalid. See details.",
                },
                "message": "client_secret in body should be at least 64 chars long",
            },
            "INVALID_PARAMETER: client_secret in body should be at least 64 chars long",
        ),
        (
            {
                "error": {
                    "code": 40003,
                    "error_code": "INVALID_CLIENT",
                    "message": "Client authentication failed. Please verify client_id and "
                    "client_secret inputs.",
                }
            },
            "INVALID_CLIENT: Client authentication failed. Please verify client_id and "
            "client_secret inputs.",
        ),
        ("not json", "not json"),
    ],
)
def test_a_refusal_says_finverse_own_reason(body, expected):
    """As the production API answered on 2026-10-27."""
    assert fv_client._reason(body) == expected
