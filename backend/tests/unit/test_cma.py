"""Unit tests for the CMA blend: unmapped tickers keep their historical μ."""

import numpy as np

from app.finance import cma


def test_mapped_ticker_is_blended_toward_cma():
    hist = np.array([0.15])
    out = cma.blended_mu(["DCAM.PA"], hist, shrinkage=0.7)
    expected = 0.3 * 0.15 + 0.7 * cma.get_return("DCAM.PA")
    assert out[0] == float(np.float64(expected))


def test_unmapped_ticker_keeps_historical_mu_not_a_default():
    """A money-market fund at σ ≈ 0.3 % must not receive an equity-like μ."""
    hist = np.array([0.021])
    out = cma.blended_mu(["MONEY.PA"], hist, shrinkage=0.7)
    assert out[0] == 0.021


def test_override_counts_as_mapped():
    out = cma.blended_mu(["XYZ.PA"], np.array([0.10]), shrinkage=1.0, overrides={"XYZ.PA": 0.05})
    assert out[0] == 0.05
    assert cma.unmapped_tickers(["XYZ.PA"], {"XYZ.PA": 0.05}) == []


def test_unmapped_tickers_lists_only_unknowns():
    assert cma.unmapped_tickers(["DCAM.PA", "MONEY.PA", "CW8.PA"]) == ["MONEY.PA"]
