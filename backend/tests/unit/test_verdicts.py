"""Unit tests for app.finance.verdicts — the « frais réels » verdict (ADR-023)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.finance import fees, verdicts
from app.models import InvestmentAccount, Wealth, WealthPosition

THRESHOLDS = verdicts.FeesThresholds(
    green_max=0.005, amber_max=0.010, reference=0.003, min_coverage=0.5
)
FREE = fees.BrokerFees(name="Aucun", fixed_per_line_eur=0, custody_pct=0, courtage_pct=0)


def _wealth(*positions: WealthPosition, balance_only: float = 0.0) -> Wealth:
    accounts = [
        InvestmentAccount(
            provider_account_id="pea-1",
            name="PEA",
            account_type="pea",
            positions=list(positions),
        )
    ]
    if balance_only:
        accounts.append(
            InvestmentAccount(
                provider_account_id="av-1",
                name="Assurance vie",
                account_type="life_insurance",
                balance=balance_only,
            )
        )
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 8, tzinfo=UTC),
        investment_accounts=accounts,
    )


def _pos(ticker: str, value: float, ter: float | None) -> WealthPosition:
    return WealthPosition(
        ticker=ticker, label=ticker, quantity=1.0, avg_cost=value, current_value=value, ter=ter
    )


def test_no_lines_is_unknown():
    v = verdicts.fees_verdict(_wealth(balance_only=5000.0), FREE, 0.0, THRESHOLDS)
    assert v.status == "unknown"
    assert v.details["uncovered_accounts"][0]["value_eur"] == 5000.0


def test_cheap_etf_at_free_broker_is_green():
    v = verdicts.fees_verdict(_wealth(_pos("CW8.PA", 10_000, 0.0038)), FREE, 0.0, THRESHOLDS)
    assert v.status == "green"
    assert v.impact_eur_per_year == 0.0
    assert v.action is None
    assert v.details["total_fees_eur"] == pytest.approx(38.0)
    assert "0,38 %" in v.headline and "38 €" in v.headline


def test_broker_layers_are_summed():
    """Fixed per line + custody on value + courtage on 12 monthly contributions."""
    broker = fees.BrokerFees(
        name="Banque", fixed_per_line_eur=5.0, custody_pct=0.004, courtage_pct=0.005
    )
    w = _wealth(_pos("A", 10_000, 0.002), _pos("B", 10_000, 0.002))
    v = verdicts.fees_verdict(w, broker, 200.0, THRESHOLDS)
    expected_broker = 5.0 * 2 + 0.004 * 20_000 + 0.005 * 200 * 12
    assert v.details["broker_fees_eur"] == pytest.approx(expected_broker)
    assert v.details["fund_fees_eur"] == pytest.approx(40.0)
    assert v.status == "amber"  # (40 + 102) / 20 000 = 0.71 %
    assert v.impact_eur_per_year == pytest.approx(142.0 - 60.0)


def test_expensive_fund_is_red_with_saving_in_action():
    v = verdicts.fees_verdict(_wealth(_pos("UC", 50_000, 0.02)), FREE, 0.0, THRESHOLDS)
    assert v.status == "red"
    assert v.impact_eur_per_year == pytest.approx(1000.0 - 150.0)
    assert v.action is not None and "850 €" in v.action


def test_missing_ter_on_most_of_the_value_is_unknown():
    w = _wealth(_pos("A", 8_000, None), _pos("B", 2_000, 0.002))
    v = verdicts.fees_verdict(w, FREE, 0.0, THRESHOLDS)
    assert v.status == "unknown"
    assert "1 ligne" in v.headline
    assert v.details["missing_ter"][0]["ticker"] == "A"


def test_missing_ter_on_a_minority_says_at_least():
    w = _wealth(_pos("A", 2_000, None), _pos("B", 8_000, 0.002))
    v = verdicts.fees_verdict(w, FREE, 0.0, THRESHOLDS)
    assert v.status == "green"
    assert "au moins" in v.headline
    assert v.action is not None and "Renseigne le TER" in v.action


def test_compute_all_falls_back_to_default_broker():
    class P:
        default_broker = "does-not-exist"
        monthly_dca = 100.0

    resp = verdicts.compute_all(_wealth(_pos("A", 1_000, 0.002)), P())  # type: ignore[arg-type]
    assert [v.id for v in resp.verdicts] == ["fees"]
    assert resp.verdicts[0].details["broker_name"] == fees.get(None)[1].name


def test_yaml_thresholds_load():
    cfg = verdicts.config().fees
    assert 0 < cfg.reference < cfg.green_max < cfg.amber_max
