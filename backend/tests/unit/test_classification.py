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


# ── Ce que la banque envoie vraiment ──────────────────────────────────────


def test_the_bank_label_rescues_a_typo_in_the_official_name(monkeypatch):
    """Amundi's Nasdaq tracker is registered as « NASDQ-100 », without the A."""
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            "X": [{"name": "AM PEA NASDQ-100 UCITS ETF-C", "securityType2": "Mutual Fund"}]
        },
    )

    result = classification.classify("AMUN.PEA NASDAQ-100 UC.ETF ACC", isin="X")

    assert result.asset_class == "equity_us_tech"


def test_the_official_name_rescues_an_abbreviated_bank_label(monkeypatch):
    """BNP sends « STOX.EU.600 », which no rule can reasonably match."""
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            "X": [{"name": "BNP EASY STOXX EUROPE 600 C", "securityType2": "Mutual Fund"}]
        },
    )

    result = classification.classify("BNP PAR.EASY STOX.EU.600 U.ETF", isin="X")

    assert result.asset_class == "equity_europe"
    assert result.source == "openfigi"


def test_a_sector_fund_is_not_mistaken_for_a_broad_regional_one(monkeypatch):
    """« BNP Easy BBG Europe Defense » is a bet on defence, not on Europe."""
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            "X": [{"name": "BNP EASY BBG EUROPE DEFENSE", "securityType2": "Mutual Fund"}]
        },
    )

    result = classification.classify("BNPPE BBG EUR.DEF.UC.ETF C EUR", isin="X")

    assert result.asset_class == "equity_sector"
    assert result.broad is False
    assert result.is_diversified is False


def test_a_real_portfolio_is_fully_recognised(monkeypatch):
    """The five lines of the first real user, none left unknown."""
    official = {
        "1": "AMUNDI PEA MONDE MSCI WORLD",
        "2": "AM PEA MSCI EM ESG TRN ETF-E",
        "3": "AM PEA NASDQ-100 UCITS ETF-C",
        "4": "BNP EASY STOXX EUROPE 600 C",
        "5": "BNP EASY BBG EUROPE DEFENSE",
    }
    monkeypatch.setattr(
        openfigi,
        "map_isins",
        lambda isins: {
            k: [{"name": v, "securityType2": "Mutual Fund"}] for k, v in official.items()
        },
    )

    classes = [c.asset_class for c in classification.classify_many([(None, k) for k in official])]

    assert classes == [
        "equity_world",
        "equity_emerging",
        "equity_us_tech",
        "equity_europe",
        "equity_sector",
    ]


def test_a_broad_index_is_diversified_even_without_openfigi():
    """Nothing called « MSCI World » is one company: the index answers on its own."""
    result = classification.classify("Amundi MSCI World")

    assert result.source == "label"  # no ISIN, so no instrument kind
    assert result.kind == classification.UNKNOWN_KIND
    assert result.is_diversified is True


# ── Où la ligne est cotée, pour pouvoir lire son propre cours ──────────────


def test_the_home_venue_is_preferred_over_the_others():
    """Same fund, several listings: Paris first, where a French holder's line lives."""
    quote = classification._quote(
        [
            {"exchCode": "GR", "ticker": "AMEW"},
            {"exchCode": "FP", "ticker": "CW8"},
            {"exchCode": "IM", "ticker": "CW8"},
        ]
    )

    assert quote == classification.Quote("CW8.PA", "EUR")


def test_a_us_listing_needs_no_suffix():
    assert classification._quote([{"exchCode": "UW", "ticker": "AAPL"}]) == classification.Quote(
        "AAPL", "USD"
    )


def test_london_is_left_out_because_it_quotes_in_pence():
    """Some London lines quote in pence, others in pounds: a hundredfold error."""
    assert classification._quote([{"exchCode": "LN", "ticker": "SWDA"}]) is None


def test_a_venue_with_no_ticker_is_skipped():
    quote = classification._quote(
        [{"exchCode": "FP", "ticker": ""}, {"exchCode": "NA", "ticker": "IWDA"}]
    )

    assert quote == classification.Quote("IWDA.AS", "EUR")


def test_an_instrument_without_an_isin_has_no_quote():
    """No ISIN means no OpenFIGI listing, so the line is replayed as its class."""
    assert classification.classify("Amundi MSCI World").quote is None
