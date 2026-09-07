"""Unit tests for Wealth domain models (computed properties + invariants)."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.models import (
    CashAccount,
    InvestmentAccount,
    Loan,
    Wealth,
    WealthEnvelope,
    WealthPosition,
)

# ── WealthPosition ──────────────────────────────────────────────────────────


def test_position_cost_basis():
    p = WealthPosition(
        ticker="WPEA.PA",
        label="iShares MSCI World",
        quantity=10.0,
        avg_cost=50.0,
        current_value=600.0,
    )
    assert p.cost_basis == 500.0


def test_position_unrealized_pnl_positive():
    p = WealthPosition(
        ticker="X",
        label="X",
        quantity=10.0,
        avg_cost=50.0,
        current_value=600.0,
    )
    assert p.unrealized_pnl == 100.0
    assert p.unrealized_pnl_pct == 0.2  # 100/500


def test_position_unrealized_pnl_negative():
    p = WealthPosition(
        ticker="X",
        label="X",
        quantity=10.0,
        avg_cost=100.0,
        current_value=800.0,
    )
    assert p.unrealized_pnl == -200.0
    assert p.unrealized_pnl_pct == -0.2  # -200/1000


def test_position_zero_cost_basis_safe():
    p = WealthPosition(
        ticker="X",
        label="X",
        quantity=0.0,
        avg_cost=50.0,
        current_value=0.0,
    )
    assert p.cost_basis == 0.0
    assert p.unrealized_pnl_pct == 0.0  # no division by zero


# ── WealthEnvelope ──────────────────────────────────────────────────────────


def test_envelope_headroom_capped():
    e = WealthEnvelope(
        provider_account_id="a",
        name="Livret A",
        balance=15000.0,
        envelope_type="livret_a",
        ceiling_eur=22950.0,
    )
    assert e.headroom_eur == 7950.0


def test_envelope_headroom_at_ceiling():
    e = WealthEnvelope(
        provider_account_id="a",
        name="Livret A",
        balance=22950.0,
        envelope_type="livret_a",
        ceiling_eur=22950.0,
    )
    assert e.headroom_eur == 0.0


def test_envelope_headroom_over_ceiling_clamps():
    """Balance > ceiling shouldn't return negative headroom."""
    e = WealthEnvelope(
        provider_account_id="a",
        name="LEP",
        balance=11000.0,
        envelope_type="lep",
        ceiling_eur=10000.0,
    )
    assert e.headroom_eur == 0.0


def test_envelope_headroom_uncapped():
    """No ceiling (e.g. PEL after 12y) → headroom is None."""
    e = WealthEnvelope(
        provider_account_id="a",
        name="PEL",
        balance=50000.0,
        envelope_type="pel",
        ceiling_eur=None,
    )
    assert e.headroom_eur is None


# ── Loan ────────────────────────────────────────────────────────────────────


def test_loan_in_deferral_future_date():
    loan = Loan(
        provider_account_id="L1",
        name="Prêt",
        outstanding_balance=10000.0,
        deferral_until=date.today() + timedelta(days=365),
    )
    assert loan.is_in_deferral is True


def test_loan_past_deferral():
    loan = Loan(
        provider_account_id="L1",
        name="Prêt",
        outstanding_balance=10000.0,
        deferral_until=date.today() - timedelta(days=1),
    )
    assert loan.is_in_deferral is False


def test_loan_no_deferral():
    loan = Loan(
        provider_account_id="L1",
        name="Prêt",
        outstanding_balance=10000.0,
    )
    assert loan.is_in_deferral is False


def test_loan_outstanding_must_be_positive():
    """Negative outstanding_balance must be rejected by Pydantic."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Loan(provider_account_id="L1", name="X", outstanding_balance=-100.0)


# ── InvestmentAccount ───────────────────────────────────────────────────────


def test_investment_account_aggregates():
    acc = InvestmentAccount(
        provider_account_id="pea-1",
        name="PEA",
        account_type="pea",
        positions=[
            WealthPosition(ticker="A", label="A", quantity=10, avg_cost=10, current_value=120),
            WealthPosition(ticker="B", label="B", quantity=5, avg_cost=20, current_value=80),
        ],
    )
    assert acc.positions_value == 200.0
    assert acc.cost_basis == 200.0  # 100 + 100
    assert acc.unrealized_pnl == 0.0


# ── Wealth aggregate ────────────────────────────────────────────────────────


def _make_wealth(**overrides) -> Wealth:
    """Build a Wealth with sensible defaults."""
    return Wealth(
        user_id=uuid4(),
        snapshot_at=datetime.now(tz=UTC),
        **overrides,
    )


def test_wealth_empty_zero_everywhere():
    w = _make_wealth()
    assert w.total_assets == 0.0
    assert w.total_liabilities == 0.0
    assert w.net_worth == 0.0


def test_wealth_total_assets_aggregates_all_categories():
    w = _make_wealth(
        checking_accounts=[
            CashAccount(provider_account_id="c1", name="BNP", balance=2000.0),
        ],
        pea_cash_accounts=[
            CashAccount(
                provider_account_id="pc1", name="PEA Espèces", balance=100.0, is_pea_cash=True
            ),
        ],
        envelopes=[
            WealthEnvelope(
                provider_account_id="e1", name="Livret A", balance=5000.0, envelope_type="livret_a"
            ),
        ],
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea-titres",
                name="PEA Titres",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="X", label="X", quantity=1, avg_cost=500, current_value=600
                    ),
                ],
            ),
        ],
    )
    # 2000 (checking) + 100 (PEA cash) + 5000 (envelope) + 600 (positions) = 7700
    assert w.total_assets == 7700.0
    assert w.checking_total == 2000.0
    assert w.pea_cash_total == 100.0
    assert w.envelopes_total == 5000.0
    assert w.investments_total == 600.0
    assert w.unrealized_pnl == 100.0


def test_wealth_net_worth_with_loans():
    w = _make_wealth(
        checking_accounts=[
            CashAccount(provider_account_id="c", name="BNP", balance=2000.0),
        ],
        loans=[
            Loan(provider_account_id="L1", name="Prêt 1", outstanding_balance=10000.0),
            Loan(provider_account_id="L2", name="Prêt 2", outstanding_balance=30000.0),
        ],
    )
    assert w.total_assets == 2000.0
    assert w.total_liabilities == 40000.0
    assert w.net_worth == -38000.0


def test_wealth_liquid_assets_excludes_pea_cash_and_envelopes():
    """liquid_assets = checking only. PEA cash and livrets are NOT immediately mobilisable."""
    w = _make_wealth(
        checking_accounts=[
            CashAccount(provider_account_id="c", name="BNP", balance=2000.0),
        ],
        pea_cash_accounts=[
            CashAccount(
                provider_account_id="pc", name="PEA Espèces", balance=500.0, is_pea_cash=True
            ),
        ],
        envelopes=[
            WealthEnvelope(
                provider_account_id="e", name="Livret A", balance=10000.0, envelope_type="livret_a"
            ),
        ],
    )
    assert w.liquid_assets == 2000.0


def test_wealth_all_positions_flattens_across_accounts():
    w = _make_wealth(
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="A", label="A", quantity=1, avg_cost=10, current_value=10
                    ),
                ],
            ),
            InvestmentAccount(
                provider_account_id="cto",
                name="CTO",
                account_type="cto",
                positions=[
                    WealthPosition(
                        ticker="B", label="B", quantity=2, avg_cost=20, current_value=20
                    ),
                    WealthPosition(
                        ticker="C", label="C", quantity=3, avg_cost=30, current_value=30
                    ),
                ],
            ),
        ],
    )
    assert len(w.all_positions) == 3
    assert [p.ticker for p in w.all_positions] == ["A", "B", "C"]


def test_investment_account_without_positions_is_worth_its_balance():
    acc = InvestmentAccount(
        provider_account_id="av-1",
        name="AV fonds euros",
        account_type="life_insurance",
        balance=20000.0,
    )
    assert acc.positions_value == 0.0
    assert acc.value == 20000.0
    assert acc.unrealized_pnl == 0.0


def test_investment_account_with_positions_ignores_balance():
    acc = InvestmentAccount(
        provider_account_id="pea-1",
        name="PEA",
        account_type="pea",
        balance=999.0,
        positions=[
            WealthPosition(ticker="A", label="A", quantity=10, avg_cost=10, current_value=120),
        ],
    )
    assert acc.value == 120.0
