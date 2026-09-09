"""Unit tests for finance.withdrawal — one rate, read from config."""

from __future__ import annotations

import pytest

from app.finance import verdicts, withdrawal


def test_the_rate_comes_from_the_config_not_from_the_code():
    assert withdrawal.default_withdrawal_rate() == verdicts.config().retirement.withdrawal_rate


def test_the_rate_is_the_european_one_not_bengen_s_four_percent():
    """Pfau 2010: 4 % fails in more than half of the French cohorts."""
    assert withdrawal.default_withdrawal_rate() == pytest.approx(0.035)


def test_the_capital_for_an_income_route_is_gone():
    """§8.3: a dead route built on the American rule."""
    assert not hasattr(withdrawal, "compute")
    assert not hasattr(withdrawal, "BengenRequest")
