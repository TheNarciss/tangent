"""Unit tests for finance.bengen — the sustainable withdrawal rate comes from config."""

from __future__ import annotations

import pytest

from app.finance import bengen, verdicts


def test_default_rate_is_the_configured_one():
    assert bengen.default_withdrawal_rate() == verdicts.config().retirement.withdrawal_rate
    assert bengen.BengenRequest(target_monthly_income=1000).withdrawal_rate == pytest.approx(0.035)


def test_capital_needed_uses_the_configured_rate():
    res = bengen.compute(bengen.BengenRequest(target_monthly_income=1000))
    assert res.capital_needed == pytest.approx(12_000 / 0.035)


def test_explicit_rate_still_wins():
    res = bengen.compute(bengen.BengenRequest(target_monthly_income=1000, withdrawal_rate=0.04))
    assert res.capital_needed == pytest.approx(300_000)
