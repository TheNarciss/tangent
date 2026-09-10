"""Measuring a crisis on a real index, rather than copying a figure by hand."""

import pandas as pd
import pytest

from app.data import ecb, fred
from app.finance import episodes, stress

# A fall from 100 to 50 and back to 80, inside the window.
LEVELS = pd.Series(
    [90.0, 100.0, 70.0, 50.0, 80.0],
    index=pd.to_datetime(["2000-08-01", "2000-09-01", "2001-06-01", "2002-10-01", "2003-03-01"]),
)


def test_the_move_is_measured_from_one_end_of_the_window_to_the_other(monkeypatch):
    """Not each class's own worst day: they do not bottom together (ADR-029)."""
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)
    monkeypatch.setattr(ecb, "named", lambda *a, **k: pd.Series([1.0] * 5, index=LEVELS.index))

    move = episodes.measure("X", "fred", "USD", ("2000-08-01", "2003-03-31"))

    assert move == pytest.approx(80.0 / 90.0 - 1.0)  # 90 → 80, and not the 100 → 50 dip


def test_a_class_that_dips_and_recovers_is_not_reported_as_a_loss(monkeypatch):
    """Gold fell 18 % inside the 2008 window and still ended it up 32 %."""
    gold = pd.Series(
        [100.0, 82.0, 132.0],
        index=pd.to_datetime(["2007-10-01", "2008-10-01", "2009-03-31"]),
    )
    monkeypatch.setattr(fred, "series", lambda *a, **k: gold)

    assert episodes.measure("X", "fred", "EUR", ("2007-10-01", "2009-03-31")) == pytest.approx(0.32)


def test_the_currency_move_is_applied_at_the_two_ends_of_the_window(monkeypatch):
    """A euro that buys more dollars at the end softens a fall."""
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)
    rates = pd.Series([1.0, 1.0, 1.0, 1.0, 1.25], index=LEVELS.index)
    monkeypatch.setattr(ecb, "named", lambda *a, **k: rates)

    move = episodes.measure("X", "fred", "USD", ("2000-08-01", "2003-03-31"))

    assert move == pytest.approx((80.0 / 90.0) * (1.0 / 1.25) - 1.0)


def test_a_series_that_does_not_reach_the_episode_measures_nothing(monkeypatch):
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)

    assert episodes.measure("X", "fred", "USD", ("1975-01-01", "1975-12-31")) is None


def test_an_episode_before_the_euro_stays_in_its_own_currency(monkeypatch):
    old = pd.Series([100.0, 70.0], index=pd.to_datetime(["1990-07-02", "1990-09-28"]))
    monkeypatch.setattr(fred, "series", lambda *a, **k: old)

    assert episodes.measure("X", "fred", "USD", ("1990-07-01", "1990-09-30")) is None


def test_an_unknown_provider_measures_nothing():
    assert episodes.measure("X", "bloomberg", "USD", ("2000-01-01", "2000-12-31")) is None


def test_no_replayable_class_can_ever_count_as_zero_loss():
    """The guard against the worst possible answer: a pocket untouched by a crash.

    Every class a line can land in must end up with a figure in every episode,
    whether it declares one or borrows it. Adding a class to `class_map` and
    forgetting its `returns` used to silently price it at zero.
    """
    cfg = stress.config()
    replayable = (
        set(cfg.class_map.values())
        | set(cfg.envelope_classes.values())
        | set(cfg.account_classes.values())
        | set(cfg.class_series)
        | {cfg.default_asset_class, stress.FALLBACK_CLASS}
    )

    for scenario in cfg.scenarios:
        for asset_class in replayable:
            declared = asset_class in scenario.returns
            borrowed = cfg.fallback_class.get(asset_class) in scenario.returns
            assert declared or borrowed, f"{scenario.id} chiffrerait {asset_class} à zéro"


# ── La boucle ─────────────────────────────────────────────────────────────


def test_the_loop_prefers_a_measured_figure_over_the_declared_one(monkeypatch):
    monkeypatch.setattr(episodes, "measure", lambda *a, **k: -0.822)
    scenario = next(s for s in stress.config().scenarios if s.id == "dotcom_2000")

    measured = stress.measured_returns(scenario)

    assert measured["equity_us_tech"] == pytest.approx(-0.822)
    assert scenario.ret("equity_us_tech", measured) == pytest.approx(-0.822)


def test_the_loop_falls_back_on_the_declared_figure(monkeypatch):
    """A source that does not answer must not blank out an episode."""
    monkeypatch.setattr(episodes, "measure", lambda *a, **k: None)
    scenario = next(s for s in stress.config().scenarios if s.id == "dotcom_2000")

    measured = stress.measured_returns(scenario)

    assert measured == {}
    assert scenario.ret("equity_us_tech", measured) == scenario.returns["equity_us_tech"]


def test_adding_a_class_needs_no_code(monkeypatch):
    """The loop reads the registry: a new entry is measured without touching Python."""
    cfg = stress.config().model_copy(deep=True)
    cfg.class_series["equity_japan"] = [
        stress.IndexSeries(provider="fred", id="INVENTED", currency="USD")
    ]
    monkeypatch.setattr(episodes, "measure", lambda *a, **k: -0.4)
    scenario = next(s for s in cfg.scenarios if s.id == "gfc_2008")

    assert stress.measured_returns(scenario, cfg)["equity_japan"] == pytest.approx(-0.4)


def test_a_currency_the_ecb_does_not_publish_is_not_measured(monkeypatch):
    """Better no figure than a foreign move counted as if it were free."""
    days = pd.date_range("2020-01-01", periods=40, freq="D")
    monkeypatch.setattr(
        episodes, "_levels", lambda *a, **k: pd.Series(range(100, 140), index=days, dtype=float)
    )

    assert episodes.measure("X", "yahoo", "KRW", ("2020-01-01", "2020-02-09")) is None
