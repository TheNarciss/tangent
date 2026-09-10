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


def test_the_fall_is_measured_peak_to_trough_inside_the_window(monkeypatch):
    """Not first-to-last: a crisis is judged on its deepest point."""
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)
    monkeypatch.setattr(ecb, "named", lambda *a, **k: pd.Series([1.0] * 5, index=LEVELS.index))

    fall = episodes.measure("X", "fred", "USD", ("2000-08-01", "2003-03-31"))

    assert fall == pytest.approx(-0.50)  # 100 → 50, and not 90 → 80


def test_the_currency_move_is_applied_at_the_two_days_it_picked(monkeypatch):
    """A euro that buys more dollars at the trough softens the fall."""
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)
    rates = pd.Series([1.0, 1.0, 1.0, 1.25, 1.25], index=LEVELS.index)
    monkeypatch.setattr(ecb, "named", lambda *a, **k: rates)

    fall = episodes.measure("X", "fred", "USD", ("2000-08-01", "2003-03-31"))

    assert fall == pytest.approx(0.5 * (1.0 / 1.25) - 1.0)


def test_a_series_that_does_not_reach_the_episode_measures_nothing(monkeypatch):
    monkeypatch.setattr(fred, "series", lambda *a, **k: LEVELS)

    assert episodes.measure("X", "fred", "USD", ("1975-01-01", "1975-12-31")) is None


def test_an_episode_before_the_euro_stays_in_its_own_currency(monkeypatch):
    old = pd.Series([100.0, 70.0], index=pd.to_datetime(["1990-07-02", "1990-09-28"]))
    monkeypatch.setattr(fred, "series", lambda *a, **k: old)

    assert episodes.measure("X", "fred", "USD", ("1990-07-01", "1990-09-30")) is None


def test_an_unknown_provider_measures_nothing():
    assert episodes.measure("X", "bloomberg", "USD", ("2000-01-01", "2000-12-31")) is None


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
    cfg.class_series["equity_japan"] = stress.IndexSeries(
        provider="fred", id="INVENTED", currency="USD"
    )
    monkeypatch.setattr(episodes, "measure", lambda *a, **k: -0.4)
    scenario = next(s for s in cfg.scenarios if s.id == "gfc_2008")

    assert stress.measured_returns(scenario, cfg)["equity_japan"] == pytest.approx(-0.4)
