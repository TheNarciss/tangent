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


# ── Courtier inconnu : on ne facture pas les frais d'une banque au hasard ──


def _wealth_with_one_line(*, value: float, ter: float):
    import uuid
    from datetime import UTC, datetime

    from app.models import InvestmentAccount, Wealth, WealthPosition

    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 9, tzinfo=UTC),
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea-1",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="CW8.PA",
                        label="Amundi MSCI World",
                        quantity=1.0,
                        avg_cost=value,
                        current_value=value,
                        ter=ter,
                    )
                ],
            )
        ],
    )


def test_the_default_broker_charges_nothing_and_says_so():
    """A user whose bank we do not recognise must not inherit BNP's fees."""
    from app.finance import fees

    broker_id, default = fees.get(None)

    assert default.placeholder is True
    assert (default.fixed_per_line_eur, default.custody_pct, default.courtage_pct) == (
        0.0,
        0.0,
        0.0,
    )
    assert broker_id == fees.config().default_broker


def test_an_unknown_broker_makes_the_verdict_say_the_cost_is_a_floor():
    from app.finance import fees, verdicts

    wealth = _wealth_with_one_line(value=10_000.0, ter=0.0038)

    verdict = verdicts.fees_verdict(wealth, fees.get(None)[1], monthly_contribution=200.0)

    assert verdict.details["broker_known"] is False
    assert "au moins" in verdict.headline
    assert "ta banque" in (verdict.action or "")


def test_a_known_broker_reports_its_fees_as_complete():
    from app.finance import fees, verdicts

    wealth = _wealth_with_one_line(value=10_000.0, ter=0.0038)

    verdict = verdicts.fees_verdict(wealth, fees.get("bnp_start")[1], monthly_contribution=200.0)

    assert verdict.details["broker_known"] is True
    assert "au moins" not in verdict.headline
    assert verdict.details["broker_fees_eur"] > 0
