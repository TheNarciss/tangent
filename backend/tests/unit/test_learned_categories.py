"""A merchant categorised once is categorised for good; the user's word wins."""

from __future__ import annotations

from datetime import UTC, datetime

from app.aggregator.types import AccountType, BankAccount
from app.enablebanking.aggregator import disambiguate
from app.finance import merchants
from app.repositories.bank_transactions import learn


def test_the_bank_noise_is_folded_away():
    assert merchants.fold("CB CARREFOUR CITY 12/09") == "carrefour city"
    assert merchants.fold("PAIEMENT CB 0912 CARREFOUR CITY") == "carrefour city"
    assert merchants.fold("PRLV SEPA EDF 123456") == "edf"
    assert merchants.fold("") == "sans libellé"
    assert merchants.fold(None) == "sans libellé"


def test_the_latest_decision_wins_unless_the_user_spoke():
    t1 = datetime(2026, 1, 1, tzinfo=UTC)
    t2 = datetime(2026, 2, 1, tzinfo=UTC)
    rows = [
        ("CB CARREFOUR 01/01", "shopping", "llm", t1),
        ("CB CARREFOUR 01/02", "alimentation", "llm", t2),
        ("Netflix 01/01", "loisirs", "user", t1),
        ("Netflix 01/02", "abonnements", "llm", t2),
    ]

    learned = learn(rows)

    assert learned["carrefour"] == "alimentation"  # the later LLM answer
    assert learned["netflix"] == "loisirs"  # the user's, older but theirs


def _account(name: str, currency: str, kind: AccountType) -> BankAccount:
    return BankAccount(
        provider="enablebanking",
        provider_account_id=f"{name}-{currency}-{kind}",
        name=name,
        type=kind,
        currency=currency,
        institution_name="Revolut",
        balance=0.0,
    )


def test_pockets_named_after_their_holder_are_told_apart():
    accounts = disambiguate(
        [
            _account("Clément", "EUR", AccountType.CHECKING),
            _account("Clément", "GBP", AccountType.CHECKING),
            _account("Clément", "EUR", AccountType.SAVINGS),
            _account("Compte pro", "EUR", AccountType.CHECKING),
        ]
    )

    assert [a.name for a in accounts] == [
        "Revolut EUR",
        "Revolut GBP",
        "Revolut EUR épargne",
        "Compte pro",
    ]


def test_two_identical_pockets_still_get_distinct_names():
    accounts = disambiguate(
        [_account("X", "EUR", AccountType.CHECKING), _account("X", "EUR", AccountType.CHECKING)]
    )

    assert [a.name for a in accounts] == ["Revolut EUR", "Revolut EUR (2)"]
