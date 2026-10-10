"""A bank connected again lists its accounts under new ids: which ones are the same?"""

from __future__ import annotations

from datetime import UTC, datetime

from app.aggregator import AccountType
from app.aggregator import BankAccount as BankAccountDTO
from app.repositories.bank_accounts import identity, one_per_account

IBAN = "FR76 1020 7000 0123 4567 8901 234"


def _acc(pid: str, connection: int = 10, **kw) -> BankAccountDTO:
    fields = {
        "provider": "powens",
        "provider_account_id": pid,
        "name": "Compte courant",
        "type": AccountType.CHECKING,
        "currency": "EUR",
        "institution_name": "Banque Populaire",
        "balance": 100.0,
        "iban": IBAN,
        "raw_data": {"id": int(pid), "id_connection": connection},
    }
    fields.update(kw)
    return BankAccountDTO(**fields)


def test_the_iban_names_the_account_whatever_its_spacing_or_case():
    assert identity(_acc("1")) == identity(_acc("2", iban=IBAN.replace(" ", "").lower()))


def test_a_card_or_another_currency_is_another_account():
    assert identity(_acc("1")) != identity(_acc("2", type=AccountType.CARD))
    assert identity(_acc("1")) != identity(_acc("2", currency="USD"))


def test_without_an_iban_the_number_at_the_same_bank_decides():
    card = {"iban": None, "type": AccountType.CARD, "number": "4974 XXXX XXXX 1234"}
    assert identity(_acc("1", **card)) == identity(_acc("2", **card))
    assert identity(_acc("1", **card)) != identity(
        _acc("2", **card, institution_name="BNP Paribas")
    )
    assert identity(_acc("1", iban=None, number=None)) is None


def test_ids_that_survive_a_new_consent_are_left_alone():
    assert identity(_acc("1", provider="enablebanking")) is None


def test_the_freshest_of_two_listings_is_kept_and_the_order_with_it():
    old = _acc("101", powens_last_update=datetime(2026, 10, 9, tzinfo=UTC))
    savings = _acc("102", type=AccountType.SAVINGS, iban="FR76 1020 7000 0999 9999 9999 999")
    new = _acc("201", 20, powens_last_update=datetime(2026, 10, 10, tzinfo=UTC))
    no_id = _acc("103", iban=None, number=None)
    assert one_per_account([old, savings, new, no_id]) == [savings, new, no_id]


def test_without_a_date_the_newest_id_wins():
    assert one_per_account([_acc("999"), _acc("1000", 20)]) == [_acc("1000", 20)]


def test_look_alikes_within_one_connection_are_distinct_accounts():
    loan = {"iban": None, "type": AccountType.LOAN, "number": "****7727"}
    two_loans = [_acc("201", 13, **loan), _acc("202", 13, **loan)]
    assert one_per_account(two_loans) == two_loans
    # Connected again: which old loan is which new one cannot be told, all stay.
    assert one_per_account([*two_loans, _acc("301", 14, **loan)]) == [
        *two_loans,
        _acc("301", 14, **loan),
    ]
    # Without the connection, nothing says they are one.
    blind = [_acc("1", raw_data={}), _acc("2", raw_data={})]
    assert one_per_account(blind) == blind
