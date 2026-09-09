"""What an instrument is, decided on its official name rather than on statistics."""

import pytest

from app.data import openfigi
from app.errors import DataSourceError
from app.finance import classification


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Nothing here calls OpenFIGI unless a test says what it answers."""
    monkeypatch.setattr(openfigi, "map_isins", lambda isins: {})


def test_two_trackers_of_the_same_index_land_on_the_same_class():
    amundi = classification.classify("AM MSCI WORLD SP ETF EUR ACC")
    ishares = classification.classify("ISHARES CORE MSCI WORLD")

    assert amundi.asset_class == ishares.asset_class == "equity_world"
    assert amundi.index_label == "Actions monde"


def test_the_most_precise_rule_wins():
    # "Nasdaq-100" must not be caught by a broader US rule placed after it.
    assert classification.classify("AM NASDAQ-100 SP ETF").asset_class == "equity_us_tech"


def test_accents_and_case_do_not_matter():
    assert classification.classify("ETF Marchés Émergents").asset_class == "equity_emerging"


def test_an_unrecognised_instrument_stays_unknown():
    result = classification.classify("Fonds maison Truc 2035")

    assert result.asset_class == "unknown"
    assert result.is_known is False
    assert result.index_label is None


def test_the_official_name_beats_the_bank_label(monkeypatch):
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            "LU1681043599": [{"name": "AM MSCI WORLD SP ETF", "securityType2": "Mutual Fund"}]
        },
    )

    result = classification.classify("PEA - ligne 4", isin="LU1681043599")

    assert result.asset_class == "equity_world"
    assert result.source == "openfigi"
    assert result.official_name == "AM MSCI WORLD SP ETF"


def test_a_fund_is_diversified_and_a_share_is_not(monkeypatch):
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            "LU1681043599": [{"name": "AM MSCI WORLD SP ETF", "securityType2": "Mutual Fund"}],
            "FR0000120073": [{"name": "AIR LIQUIDE SA", "securityType2": "Common Stock"}],
        },
    )

    fund, share = classification.classify_many([("", "LU1681043599"), ("", "FR0000120073")])

    assert fund.kind == classification.FUND and fund.is_diversified
    assert share.kind == classification.STOCK and not share.is_diversified


def test_openfigi_being_down_falls_back_to_the_label(monkeypatch):
    def _down(isins):
        raise DataSourceError("OpenFIGI injoignable")

    monkeypatch.setattr(openfigi, "map_isins", _down)

    result = classification.classify("Amundi MSCI World", isin="LU1681043599")

    assert result.asset_class == "equity_world"  # the page still works
    assert result.source == "label"


def test_a_batch_asks_openfigi_once(monkeypatch):
    calls = {"n": 0}

    def _count(isins):
        calls["n"] += 1
        return {}

    monkeypatch.setattr(openfigi, "map_isins", _count)

    classification.classify_many([("A", "X1"), ("B", "X2"), ("C", "X3")])

    assert calls["n"] == 1


def test_no_label_and_no_isin_is_unknown():
    assert classification.classify(None).asset_class == "unknown"
