"""The server's translations: negotiation, lookup, and English mirroring French."""

from app.i18n import as_locale, keys, negotiate, t


def test_negotiate_reads_the_first_language():
    assert negotiate(None) == "fr"
    assert negotiate("") == "fr"
    assert negotiate("en-US,en;q=0.9,fr;q=0.8") == "en"
    assert negotiate("en") == "en"
    assert negotiate("fr-FR,fr;q=0.9,en;q=0.8") == "fr"
    assert negotiate("de-DE,de;q=0.9") == "fr"
    assert negotiate("*") == "fr"


def test_as_locale_only_knows_ours():
    assert as_locale("en") == "en"
    assert as_locale("fr") == "fr"
    assert as_locale(None) == "fr"
    assert as_locale("de") == "fr"


def test_t_follows_the_locale_and_fills_slots():
    assert t("fr", "errors.no_bank") == "Aucune banque connectée."
    assert t("en", "errors.no_bank") == "No bank connected."
    assert t("en", "email.reset.expires_minutes", minutes=15) == "15 minutes"
    assert t("en", "not.a.key") == "not.a.key"


def test_english_mirrors_french():
    per_locale = keys()
    assert per_locale["en"] == per_locale["fr"]
