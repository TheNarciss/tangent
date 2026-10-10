"""A bank connected again lists its accounts under new ids: which ones are the same,
which listing is kept, and which connection brings nothing."""

from __future__ import annotations

from app.aggregator import AccountType
from app.aggregator import BankAccount as BankAccountDTO
from app.aggregator.same_account import identity, one_per_account, redundant_connections

IBAN = "FR76 1020 7000 0123 4567 8901 234"
SAVINGS_IBAN = "FR76 1020 7000 0999 9999 9999 999"


def _acc(pid: str, connection: int = 10, works: bool | None = True, **kw) -> BankAccountDTO:
    fields = {
        "provider": "powens",
        "provider_account_id": pid,
        "name": "Compte courant",
        "type": AccountType.CHECKING,
        "currency": "EUR",
        "institution_name": "Banque Populaire",
        "balance": 100.0,
        "iban": IBAN,
        "raw_data": {"id": int(pid), "id_connection": connection, "connection_works": works},
    }
    fields.update(kw)
    return BankAccountDTO(**fields)


LOAN = {"iban": None, "type": AccountType.LOAN, "number": "****7727"}


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


def test_the_newest_connection_that_works_keeps_the_account_order_kept():
    old = _acc("101")
    savings = _acc("102", type=AccountType.SAVINGS, iban=SAVINGS_IBAN)
    new = _acc("201", 20)
    no_id = _acc("103", iban=None, number=None)
    assert one_per_account([old, savings, new, no_id]) == [savings, new, no_id]
    # A newer connection that does not read the bank does not take the account.
    broken = _acc("201", 20, works=False)
    assert one_per_account([old, broken]) == [old]


def test_look_alikes_within_one_connection_are_distinct_accounts():
    two_loans = [_acc("201", 13, **LOAN), _acc("202", 13, **LOAN)]
    assert one_per_account(two_loans) == two_loans
    # Connected again: which old loan is which new one cannot be told, all stay.
    third = _acc("301", 14, **LOAN)
    assert one_per_account([*two_loans, third]) == [*two_loans, third]
    # Without the connection, nothing says they are one.
    blind = [_acc("1", raw_data={}), _acc("2", raw_data={})]
    assert one_per_account(blind) == blind


def test_a_connection_a_newer_working_one_fully_lists_brings_nothing():
    card = {"iban": None, "type": AccountType.CARD, "number": "4974XXXXXXXX1234"}
    listed = [_acc("101"), _acc("102", **card), _acc("201", 20), _acc("202", 20, **card)]
    assert redundant_connections(listed) == {10}


def test_a_connection_with_an_account_of_its_own_stays():
    listed = [_acc("101", works=False), _acc("102", works=False, **LOAN), _acc("201", 20)]
    assert redundant_connections(listed) == set()
    assert one_per_account(listed) == listed[1:]


def test_nothing_goes_while_the_newer_connection_is_not_reading_yet():
    assert redundant_connections([_acc("101"), _acc("201", 20, works=False)]) == set()
    assert redundant_connections([_acc("101"), _acc("201", 20, works=None)]) == set()


def test_the_newest_connection_is_never_the_one_that_goes():
    assert redundant_connections([_acc("101", works=False), _acc("201", 20, works=False)]) == set()
    assert redundant_connections([_acc("201", 20)]) == set()


def test_look_alikes_are_never_counted_as_covered():
    listed = [_acc("201", 13, **LOAN), _acc("202", 13, **LOAN), _acc("301", 14, **LOAN)]
    assert redundant_connections(listed) == set()
