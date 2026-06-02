"""Build a serialisable WealthSummary from a Wealth domain object."""

from __future__ import annotations

from ..models import (
    EnvelopeSummary,
    LoanSummary,
    Wealth,
    WealthSummary,
)


def build_summary(wealth: Wealth) -> WealthSummary:
    """Project a Wealth aggregate into a lightweight DTO for the dashboard.

    Only aggregates and per-envelope/per-loan details — positions stay in
    `PortfolioMetrics.assets`, not duplicated here.
    """
    return WealthSummary(
        net_worth=wealth.net_worth,
        total_assets=wealth.total_assets,
        total_liabilities=wealth.total_liabilities,
        checking_total=wealth.checking_total,
        pea_cash_total=wealth.pea_cash_total,
        envelopes_total=wealth.envelopes_total,
        investments_total=wealth.investments_total,
        unrealized_pnl=wealth.unrealized_pnl,
        envelopes=[
            EnvelopeSummary(
                name=e.name,
                institution_name=e.institution_name,
                envelope_type=e.envelope_type,
                balance=e.balance,
                display_name=e.display_name,
                rate_pct=e.rate_pct,
                ceiling_eur=e.ceiling_eur,
                headroom_eur=e.headroom_eur,
            )
            for e in wealth.envelopes
        ],
        loans=[
            LoanSummary(
                name=loan.name,
                institution_name=loan.institution_name,
                outstanding_balance=loan.outstanding_balance,
                interest_rate_pct=loan.interest_rate_pct,
                monthly_payment=loan.monthly_payment,
                next_payment_date=loan.next_payment_date,
                deferral_until=loan.deferral_until,
                is_in_deferral=loan.is_in_deferral,
            )
            for loan in wealth.loans
        ],
    )
