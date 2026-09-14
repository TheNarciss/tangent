"""Categories decided by the bank's own codes, before any LLM."""

from __future__ import annotations

import pytest

from app.errors import ConfigurationError
from app.finance import categorization
from app.finance.gap_filler.fields.transaction_category import CATEGORIES


def test_every_rule_names_a_category_of_the_taxonomy():
    rules = categorization.rules()

    assert rules.mcc and rules.bank_transaction_code
    assert all(r.category in CATEGORIES for r in rules.mcc)
    assert all(r.category in CATEGORIES for r in rules.bank_transaction_code)


def test_a_merchant_code_names_the_shop():
    assert categorization.from_mcc(5411) == "alimentation"  # supermarket
    assert categorization.from_mcc("5812") == "restaurant"
    assert categorization.from_mcc(4511) == "voyages"  # airline
    assert categorization.from_mcc(3021) == "voyages"  # airline range
    assert categorization.from_mcc(5541) == "carburant"
    assert categorization.from_mcc(7372) == "abonnements"  # SaaS
    assert categorization.from_mcc(9311) == "impots_taxes"


def test_an_unknown_or_missing_code_decides_nothing():
    assert categorization.from_mcc(None) is None
    assert categorization.from_mcc("") is None
    assert categorization.from_mcc("abc") is None
    assert categorization.from_mcc(1) is None
    assert categorization.from_mcc(6011) is None  # ATM: no rule on purpose


def test_the_operation_code_recognises_a_withdrawal_or_a_fee():
    assert categorization.from_bank_code("PMNT/CCRD/CWDL") == "autre"
    assert (
        categorization.from_bank_code({"domain": "PMNT", "family": "CCRD", "sub_family": "CWDL"})
        == "autre"
    )
    assert (
        categorization.from_bank_code({"code": "CCRD", "sub_code": "CWDL"}) == "autre"
    )  # Enable Banking's shape
    assert categorization.from_bank_code("ACMT/MDOP/CHRG") == "frais_bancaires"
    assert categorization.from_bank_code("PMNT/ICDT/ESCT") is None  # a transfer: the LLM's job
    assert categorization.from_bank_code(None) is None


def test_the_merchant_code_wins_over_the_operation_code():
    assert categorization.decide(mcc=5411, bank_code="PMNT/CCRD/CWDL") == "alimentation"
    assert categorization.decide(mcc=None, bank_code="PMNT/CCRD/CWDL") == "autre"
    assert categorization.decide() is None


def test_a_broken_table_is_a_configuration_error(monkeypatch, tmp_path):
    bad = tmp_path / "t.yaml"
    bad.write_text("mcc:\n  - {mcc: 5411, category: nope}\n")
    monkeypatch.setattr(categorization, "_PATH", bad)
    categorization.rules.cache_clear()
    try:
        with pytest.raises(ConfigurationError, match="catégorie inconnue"):
            categorization.rules()
    finally:
        categorization.rules.cache_clear()
