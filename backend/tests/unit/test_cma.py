"""The CMA blend keys on what an instrument is, not on a list of six tickers."""

import numpy as np

from app.finance import cma


def test_a_known_class_is_blended_toward_its_long_term_assumption():
    hist = np.array([0.15])

    out = cma.blended_mu(["DCAM.PA"], ["equity_world"], hist, shrinkage=0.7)

    expected = 0.3 * 0.15 + 0.7 * cma.get_return("DCAM.PA", "equity_world")
    assert out[0] == float(np.float64(expected))


def test_any_world_tracker_gets_the_same_assumption():
    """The point of the change: it no longer depends on the ticker being listed."""
    hist = np.array([0.15, 0.15])

    out = cma.blended_mu(["DCAM.PA", "SWDA.L"], ["equity_world"] * 2, hist, shrinkage=0.7)

    assert out[0] == out[1]


def test_an_unrecognised_class_keeps_its_historical_mu():
    """A money-market fund at σ ≈ 0,3 % must not receive an equity-like μ."""
    hist = np.array([0.021])

    out = cma.blended_mu(["MONEY.PA"], ["unknown"], hist, shrinkage=0.7)

    assert out[0] == 0.021


def test_a_class_with_no_declared_assumption_keeps_its_historical_mu():
    hist = np.array([0.03])

    out = cma.blended_mu(["AGGH.PA"], ["bonds"], hist, shrinkage=0.7)

    assert out[0] == 0.03


def test_an_override_wins_over_the_class():
    out = cma.blended_mu(
        ["XYZ.PA"], ["equity_world"], np.array([0.10]), shrinkage=1.0, overrides={"XYZ.PA": 0.05}
    )

    assert out[0] == 0.05
    assert cma.unmapped_tickers(["XYZ.PA"], ["unknown"], {"XYZ.PA": 0.05}) == []


def test_unmapped_lists_the_tickers_whose_class_has_no_assumption():
    tickers = ["DCAM.PA", "MONEY.PA", "SWDA.L"]
    classes = ["equity_world", "unknown", "equity_world"]

    assert cma.unmapped_tickers(tickers, classes) == ["MONEY.PA"]
