"""What the Méthode screen says about how each line was replayed."""

from __future__ import annotations

from app.finance import classification, dashboard, stress


def _line(asset_class: str, index_label: str, broad: bool = True) -> classification.Classification:
    return classification.Classification(asset_class, index_label, "fund", "label", None, broad)


def test_a_sector_fund_is_still_named_when_the_world_itself_is_measured(monkeypatch):
    """Regression: once world equities were measured, everything that borrows
    their amplitude vanished from the « rejouées comme le monde » fold."""
    monkeypatch.setattr(
        stress, "measured_classes", lambda *a, **k: ["equity_world", "equity_europe"]
    )
    classes = {
        "GUARD.PA": _line("equity_sector", "Actions d'un secteur", broad=False),
        "ETZ.PA": _line("equity_europe", "Actions européennes"),
        "CW8.PA": _line("equity_world", "Actions monde"),
    }

    listed = dashboard._replayed_as_world(classes, list(classes))

    assert listed == ["Actions d'un secteur"]


def test_a_region_without_a_series_is_named_as_borrowing_the_world(monkeypatch):
    monkeypatch.setattr(stress, "measured_classes", lambda *a, **k: ["equity_world"])
    classes = {"PAEEM.PA": _line("equity_emerging", "Marchés émergents")}

    assert dashboard._replayed_as_world(classes, ["PAEEM.PA"]) == ["Marchés émergents"]
