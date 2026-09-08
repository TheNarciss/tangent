"""Unit tests for the broker fee model (config/brokers.yaml)."""

from __future__ import annotations

import pytest

from app.finance import fees


def test_rebates_are_not_charged_to_the_user():
    """Retrocessions are paid out of the fund's TER to the bank, not by the client."""

    _, bnp = fees.get("bnp_start")
    assert bnp.rebates_pct > 0  # still documented in brokers.yaml
    fn = fees.monthly_fee_fn(bnp, n_lines=1, monthly_contribution=0.0)
    expected = bnp.fixed_per_line_eur / 12 + bnp.custody_pct / 12 * 100_000
    assert fn(100_000.0) == pytest.approx(expected)


def test_ter_is_not_a_simulated_cost_anymore():
    """Prices are net of fund fees: the TER is costed by the verdict, not the projection."""
    assert not hasattr(fees, "apply_ter_to_fee_fn")
