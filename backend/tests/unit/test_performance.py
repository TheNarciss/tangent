"""Unit tests for app.finance.performance — TWR, TRI, drawdown (étude §7.7)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.finance import performance
from app.models import CashAccount, InvestmentAccount, Wealth, WealthPosition
from app.repositories.snapshots import net_flow_between


def _p(day: str, value: float, flow: float = 0.0) -> performance.Point:
    return performance.Point(day=date.fromisoformat(day), value=value, net_flow=flow)


# ── The sub-period return takes the contribution out ───────────────────────


def test_a_contribution_is_not_performance():
    """+1 000 € paid in on a 10 000 € pocket now worth 11 000 € is a flat month."""
    assert performance.sub_period_return(10_000, 11_000, 1_000) == pytest.approx(0.0)


def test_the_market_move_is_performance():
    assert performance.sub_period_return(10_000, 11_000, 0.0) == pytest.approx(0.10)


def test_a_pocket_worth_nothing_has_no_return():
    assert performance.sub_period_return(0.0, 1_000, 1_000) is None


# ── TWR against TRI: the Kitces example ────────────────────────────────────


def test_twr_ignores_the_timing_that_tri_punishes():
    """100 k€, +100 %, then 200 k€ paid in, then −30 %: TWR +40 %, TRI negative.

    The textbook case (étude §7.7): the strategy did well, the saver did not,
    because the big contribution landed just before the fall. Spread over a
    year so both rates are reported.
    """
    perf = performance.compute(
        [
            _p("2025-09-09", 100_000),
            _p("2026-03-09", 200_000),  # +100 %, no flow
            _p("2026-03-10", 400_000, flow=200_000),  # money in, market flat
            _p("2026-09-09", 280_000),  # −30 %
        ]
    )
    assert perf is not None
    assert perf.twr == pytest.approx(2.0 * 1.0 * 0.7 - 1.0)  # +40 %
    assert perf.irr is not None
    assert perf.irr < 0  # the saver's own money lost
    assert perf.behaviour_gap is not None and perf.behaviour_gap < 0


def test_a_short_window_reports_the_cumulative_return_only():
    """Annualizing two months would turn +50 % into a four-digit yearly rate."""
    perf = performance.compute([_p("2026-01-01", 100_000), _p("2026-03-01", 150_000)])
    assert perf is not None
    assert perf.twr == pytest.approx(0.5)
    assert perf.twr_annualized is None
    assert perf.irr is None
    assert perf.behaviour_gap is None


def test_no_flows_makes_tri_and_twr_agree():
    perf = performance.compute([_p("2025-09-09", 10_000), _p("2026-09-09", 11_000)])
    assert perf is not None
    assert perf.twr == pytest.approx(0.10)
    assert perf.irr == pytest.approx(0.10, abs=1e-3)
    assert perf.twr_annualized == pytest.approx(0.10, abs=1e-3)
    assert perf.behaviour_gap == pytest.approx(0.0, abs=2e-3)


def test_one_point_is_not_a_history():
    assert performance.compute([_p("2026-09-09", 10_000)]) is None


# ── Drawdown ───────────────────────────────────────────────────────────────


def test_drawdown_measures_the_fall_from_the_high_not_the_flows():
    perf = performance.compute(
        [
            _p("2026-01-01", 10_000),
            _p("2026-02-01", 12_000),  # high
            _p("2026-03-01", 10_800),  # −10 % from the high
            _p("2026-04-01", 11_800, flow=1_000),  # flat, money paid in
        ]
    )
    assert perf is not None
    assert perf.drawdown == pytest.approx(-0.10, abs=1e-9)
    assert perf.max_drawdown == pytest.approx(-0.10, abs=1e-9)
    assert perf.peak_day == date(2026, 2, 1)


def test_an_all_time_high_has_no_drawdown():
    perf = performance.compute([_p("2026-01-01", 10_000), _p("2026-02-01", 12_000)])
    assert perf is not None
    assert perf.drawdown == pytest.approx(0.0)


# ── Flow detection from the quantities ─────────────────────────────────────


def test_buying_a_line_is_a_flow():
    flow = net_flow_between({"CW8.PA": 10}, {"CW8.PA": 12}, {"CW8.PA": 500.0})
    assert flow == pytest.approx(1_000.0)


def test_selling_one_line_to_buy_another_is_not_a_flow():
    flow = net_flow_between({"A": 10, "B": 0}, {"A": 5, "B": 10}, {"A": 100.0, "B": 50.0})
    assert flow == pytest.approx(0.0)


def test_a_line_without_a_price_is_ignored_rather_than_guessed():
    assert net_flow_between({"A": 1}, {"A": 5}, {}) == pytest.approx(0.0)


# ── What a snapshot may measure ────────────────────────────────────────────


def _wealth(*, with_bulk_account: bool = False) -> Wealth:
    accounts = [
        InvestmentAccount(
            provider_account_id="pea",
            name="PEA",
            account_type="pea",
            positions=[
                WealthPosition(
                    ticker="CW8.PA",
                    label="Monde",
                    quantity=10.0,
                    avg_cost=400.0,
                    current_value=5_000.0,
                )
            ],
        )
    ]
    if with_bulk_account:
        accounts.append(
            InvestmentAccount(
                provider_account_id="av",
                name="Assurance vie",
                account_type="life_insurance",
                balance=20_000.0,
            )
        )
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 9, tzinfo=UTC),
        investment_accounts=accounts,
        pea_cash_accounts=[
            CashAccount(
                provider_account_id="pea-cash", name="Espèces", balance=500.0, is_pea_cash=True
            )
        ],
    )


def test_snapshot_covers_lines_and_pea_cash():
    total, quantities, prices = performance.snapshot_inputs(_wealth())
    assert total == pytest.approx(5_500.0)
    assert quantities == {"CW8.PA": 10.0, performance.CASH_KEY: 500.0}
    assert prices["CW8.PA"] == pytest.approx(500.0)


def test_a_wrapper_valued_in_bulk_is_left_out_rather_than_flattering_the_return():
    total, quantities, _ = performance.snapshot_inputs(_wealth(with_bulk_account=True))
    assert total == pytest.approx(5_500.0)
    assert "av" not in quantities
