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
    p = _profile()
    p.default_broker = "does-not-exist"
    resp = verdicts.compute_all(_wealth(_pos("A", 1_000, 0.002)), p)
    fees_v = next(v for v in resp.verdicts if v.id == "fees")
    assert fees_v.details["broker_name"] == fees.get(None)[1].name


def test_yaml_thresholds_load():
    cfg = verdicts.config().fees
    assert 0 < cfg.reference < cfg.green_max < cfg.amber_max


# ── « Où placer le prochain euro » ─────────────────────────────────────────

from datetime import date  # noqa: E402

from app.db.models import Profile  # noqa: E402
from app.models import CashAccount, WealthEnvelope  # noqa: E402

NEXT = verdicts.NextEuroThresholds(
    precaution_months=3,
    precaution_min_months=1,
    liquid_envelopes=["livret_a", "ldds", "lep"],
    pea_ceiling_eur=150_000,
    pea_vs_cto_pct=0.006,
    per_tmi_min=0.30,
    per_ceiling_pct=0.10,
    per_ceiling_min_eur=4637,
    per_ceiling_max_eur=37094,
    tax_brackets=[
        verdicts.TaxBracket(up_to=11497, rate=0.0),
        verdicts.TaxBracket(up_to=29315, rate=0.11),
        verdicts.TaxBracket(up_to=83823, rate=0.30),
        verdicts.TaxBracket(up_to=180294, rate=0.41),
        verdicts.TaxBracket(up_to=None, rate=0.45),
    ],
)


def _profile(rfr: float = 30_000.0, shares: float = 1.0, dca: float = 200.0) -> Profile:
    p = Profile(user_id=uuid.uuid4(), ceilings_used={})
    p.birth_date = date(1990, 1, 1)
    p.fiscal_shares = shares
    p.rfr_n_minus_2 = rfr
    p.monthly_dca = dca
    return p


def _env(kind: str, balance: float, ceiling: float | None = 22_950.0) -> WealthEnvelope:
    return WealthEnvelope(
        provider_account_id=f"{kind}-1",
        name=kind,
        balance=balance,
        envelope_type=kind,
        ceiling_eur=ceiling,
        rate_pct=0.024,
    )


def _acc(kind: str, value: float) -> InvestmentAccount:
    return InvestmentAccount(
        provider_account_id=f"{kind}-1", name=kind.upper(), account_type=kind, balance=value
    )


def _wealth2(*, envelopes=(), accounts=(), checking: float = 500.0) -> Wealth:
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 8, tzinfo=UTC),
        checking_accounts=[
            CashAccount(provider_account_id="chk", name="Courant", balance=checking)
        ],
        envelopes=list(envelopes),
        investment_accounts=list(accounts),
    )


def test_marginal_rate_uses_quotient_familial():
    assert verdicts.marginal_tax_rate(50_000, 1.0, NEXT.tax_brackets) == 0.30
    assert verdicts.marginal_tax_rate(50_000, 2.5, NEXT.tax_brackets) == 0.11
    assert verdicts.marginal_tax_rate(500_000, 1.0, NEXT.tax_brackets) == 0.45


def test_nothing_connected_is_unknown():
    w = Wealth(user_id=uuid.uuid4(), snapshot_at=datetime(2026, 9, 8, tzinfo=UTC))
    v = verdicts.next_euro_verdict(w, _profile(), 1500.0, NEXT)
    assert v.status == "unknown"


def test_precaution_under_one_month_is_red_and_goes_to_a_livret():
    w = _wealth2(envelopes=[_env("livret_a", 800.0)], accounts=[_acc("pea", 5000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=40_000), 1500.0, NEXT)
    assert v.status == "red"
    assert "ton Livret A" in v.headline
    assert v.action is not None and "4\u202f500 €" in v.action
    assert v.details["precaution"]["months_covered"] == pytest.approx(800 / 1500)


def test_lep_eligible_precaution_short_goes_to_lep():
    w = _wealth2(envelopes=[_env("livret_a", 2000.0)], accounts=[_acc("pea", 5000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=15_000), 1500.0, NEXT)
    assert v.status == "amber"
    assert "un LEP à ouvrir" in v.headline


def test_no_pea_with_cto_is_amber_with_tax_gain():
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("cto", 10_000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=40_000, dca=200), 1500.0, NEXT)
    assert v.status == "amber"
    assert "un PEA à ouvrir" in v.headline
    assert v.impact_eur_per_year == pytest.approx(0.006 * (10_000 + 2400))
    assert v.action is not None and "Ouvre un PEA" in v.action


def test_all_in_place_low_bracket_is_green():
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("pea", 20_000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=25_000), 1500.0, NEXT)
    assert v.status == "green"
    assert "ton PEA" in v.headline
    assert v.action is None
    per = next(s for s in v.details["steps"] if s["id"] == "per")
    assert per["status"] == "green" and "11 %" in per["text"]


def test_bracket_30_without_per_is_an_opportunity():
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("pea", 20_000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=50_000, dca=500), 1500.0, NEXT)
    assert v.status == "amber"
    assert (
        "ton PEA" in v.headline
    )  # destination unchanged: PER is an opportunity, not the next euro
    assert v.impact_eur_per_year == pytest.approx(0.30 * min(5000.0, 6000.0))
    assert v.action is not None and "PER" in v.action
    assert v.details["per"]["ceiling_eur"] == pytest.approx(5000.0)


def test_lep_opportunity_moves_livret_money():
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("pea", 20_000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=15_000), 1500.0, NEXT)
    lep = next(s for s in v.details["steps"] if s["id"] == "lep")
    assert lep["status"] == "amber"
    # (3,5 % − 2,4 %) × min(plafond LEP 10 000, 6 000 sur le Livret A)
    assert lep["impact_eur_per_year"] == pytest.approx(0.011 * 6000.0)
    assert v.action is not None and "LEP" in v.action


def test_unknown_spending_keeps_the_rest_of_the_rule():
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("pea", 20_000.0)])
    v = verdicts.next_euro_verdict(w, _profile(rfr=25_000), None, NEXT)
    assert v.status == "green"
    assert v.details["steps"][0]["status"] == "unknown"


def test_incomplete_profile_asks_for_it():
    p = Profile(user_id=uuid.uuid4(), ceilings_used={})
    w = _wealth2(envelopes=[_env("livret_a", 6000.0)], accounts=[_acc("pea", 20_000.0)])
    v = verdicts.next_euro_verdict(w, p, 1500.0, NEXT)
    assert v.status == "green"
    assert v.action is not None and "Renseigne ton profil" in v.action


# ── « Part d'actions » ─────────────────────────────────────────────────────

RISK = verdicts.RiskShareThresholds(
    equity_premium=0.045,
    equity_sigma=0.15,
    band=0.10,
    red_gap=0.30,
    horizon_caps=[
        verdicts.HorizonCap(max_years=3, max_share=0.10),
        verdicts.HorizonCap(max_years=5, max_share=0.30),
        verdicts.HorizonCap(max_years=8, max_share=0.60),
        verdicts.HorizonCap(max_years=None, max_share=1.0),
    ],
)


def _pea_with_lines(value: float) -> InvestmentAccount:
    return InvestmentAccount(
        provider_account_id="pea-l",
        name="PEA",
        account_type="pea",
        positions=[_pos("CW8.PA", value, 0.0038)],
    )


def test_merton_share_sits_on_the_market_line():
    assert verdicts.merton_share(0.12, 0.15) == pytest.approx(0.80)
    assert verdicts.merton_share(0.20, 0.15) == 1.0
    assert verdicts.merton_share(0.05, 0.15) == pytest.approx(1 / 3)


def test_no_long_term_pocket_is_unknown():
    v = verdicts.risk_share_verdict(
        _wealth2(envelopes=[_env("livret_a", 5000.0)]), _profile(), RISK
    )
    assert v.status == "unknown"


def test_no_risk_level_asks_for_the_slider():
    p = _profile()
    p.risk_level = None
    v = verdicts.risk_share_verdict(_wealth2(accounts=[_pea_with_lines(10_000)]), p, RISK)
    assert v.status == "unknown"
    assert v.action is not None and "curseur" in v.action


def test_within_band_is_green():
    p = _profile()
    p.risk_level = 3  # 12 % / 15 % = 80 %
    w = _wealth2(accounts=[_pea_with_lines(8_000), _acc("life_insurance", 2_000)])
    v = verdicts.risk_share_verdict(w, p, RISK)
    assert v.status == "green"
    assert v.details["target_share"] == pytest.approx(0.80)
    assert v.details["gamma"] == pytest.approx(0.045 / (0.80 * 0.15**2))


def test_under_invested_is_amber_with_premium_in_euros():
    p = _profile()
    p.risk_level = 3
    w = _wealth2(accounts=[_pea_with_lines(6_000), _acc("life_insurance", 4_000)])
    v = verdicts.risk_share_verdict(w, p, RISK)
    assert v.status == "amber"  # 60 % vs 80 %
    assert v.impact_eur_per_year == pytest.approx(0.045 * 0.20 * 10_000)
    assert v.action is not None and "ETF monde" in v.action


def test_far_under_invested_is_red():
    p = _profile()
    p.risk_level = 5
    w = _wealth2(accounts=[_pea_with_lines(1_000), _acc("life_insurance", 9_000)])
    v = verdicts.risk_share_verdict(w, p, RISK)
    assert v.status == "red"


def test_over_invested_for_a_prudent_profile_has_no_euro_gain_but_a_loss_figure():
    p = _profile()
    p.risk_level = 1  # 33 %
    w = _wealth2(accounts=[_pea_with_lines(9_000), _acc("life_insurance", 1_000)])
    v = verdicts.risk_share_verdict(w, p, RISK)
    assert v.status == "red"  # 90 % vs 33 %
    assert v.impact_eur_per_year is None
    assert "2\u202f700 €" in v.headline  # 2 × 15 % × 9 000
    assert v.action is not None and "curseur" in v.action


def test_short_horizon_caps_the_target():
    p = _profile()
    p.risk_level = 5
    p.horizon_years = 4
    w = _wealth2(accounts=[_pea_with_lines(5_000), _acc("life_insurance", 5_000)])
    v = verdicts.risk_share_verdict(w, p, RISK)
    assert v.details["target_share"] == pytest.approx(0.30)
    assert v.status == "amber"  # 50 % vs 30 %


# ── « Taux d'épargne » ─────────────────────────────────────────────────────

SAVE = verdicts.SavingsRateThresholds(
    target=0.15, amber_min=0.05, escalation=0.05, growth_for_20y=0.05, horizon_years=20
)


def test_future_value_of_monthly():
    assert verdicts.future_value_of_monthly(100.0, 0.0, 1) == pytest.approx(1200.0)
    fv = verdicts.future_value_of_monthly(100.0, 0.05, 20)
    assert 40_000 < fv < 42_000  # ≈ 41 k€, textbook


def test_no_income_is_unknown():
    p = _profile(rfr=0.0)
    v = verdicts.savings_rate_verdict(p, None, SAVE)
    assert v.status == "unknown"


def test_declared_dca_above_target_is_green_with_escalation():
    p = _profile(rfr=24_000, dca=400)  # 2 000 €/mois, 20 %
    v = verdicts.savings_rate_verdict(p, None, SAVE)
    assert v.status == "green"
    assert "20 %" in v.headline
    assert v.action is not None and "420 €" in v.action
    assert v.details["source"] == "declared"


def test_observed_transfers_win_over_declared():
    p = _profile(rfr=24_000, dca=400)
    v = verdicts.savings_rate_verdict(p, 100.0, SAVE)  # observed 5 %
    assert v.status == "amber"
    assert v.details["source"] == "observed"
    assert v.impact_eur_per_year == pytest.approx((300.0 - 100.0) * 12)
    assert v.action is not None and "200 €" in v.action


def test_under_five_percent_is_red_with_horizon_gap():
    p = _profile(rfr=36_000, dca=50)  # 3 000 €/mois, 1,7 %
    v = verdicts.savings_rate_verdict(p, None, SAVE)
    assert v.status == "red"
    gap = verdicts.future_value_of_monthly(450.0 - 50.0, 0.05, 20)
    assert v.details["gap_at_horizon_eur"] == pytest.approx(gap)
    assert "dans 20 ans" in v.headline


# ── « Épargne pour ton objectif » ──────────────────────────────────────────

import numpy as np  # noqa: E402

GOAL = verdicts.GoalThresholds(
    target_probability=0.75,
    amber_probability=0.5,
    inflation=0.02,
    risk_free=0.025,
    n_paths=500,
    seed=1,
)


def test_goal_paths_match_the_closed_form_without_risk():
    shocks = np.zeros((10, 24))
    terminal = verdicts.goal_paths(1000.0, 100.0, 24, 0.0, 0.0, shocks)
    assert np.allclose(terminal, 1000.0 + 24 * 100.0)


def test_required_monthly_reaches_the_target_probability():
    rng = np.random.default_rng(0)
    shocks = rng.standard_normal((500, 120))
    req = verdicts.required_monthly_for(50_000.0, 5_000.0, 120, 0.03, 0.10, shocks, 0.75)
    p = float(np.mean(verdicts.goal_paths(5_000.0, req, 120, 0.03, 0.10, shocks) >= 50_000.0))
    assert p >= 0.75
    p_below = float(
        np.mean(verdicts.goal_paths(5_000.0, req * 0.9, 120, 0.03, 0.10, shocks) >= 50_000.0)
    )
    assert p_below < p


def test_no_goal_is_unknown():
    v = verdicts.goal_verdict(_wealth2(), _profile(), None, GOAL, RISK)
    assert v.status == "unknown"


def test_easy_goal_is_green():
    p = _profile(dca=300)
    p.goal_amount = 10_000.0
    p.horizon_years = 10
    p.risk_level = 3
    v = verdicts.goal_verdict(_wealth2(accounts=[_acc("pea", 5_000.0)]), p, None, GOAL, RISK)
    assert v.status == "green"
    assert v.details["probability"] >= 0.75
    assert v.details["mu_real"] == pytest.approx(0.025 + 0.8 * 0.045 - 0.02)


def test_hard_goal_is_red_with_required_monthly():
    p = _profile(dca=50)
    p.goal_amount = 200_000.0
    p.horizon_years = 10
    p.risk_level = 3
    v = verdicts.goal_verdict(_wealth2(accounts=[_acc("pea", 5_000.0)]), p, None, GOAL, RISK)
    assert v.status == "red"
    assert v.details["required_monthly_eur"] > 1_000
    assert v.action is not None and "Monte ton versement" in v.action


# ── Fiscalité de sortie de la projection ───────────────────────────────────


def test_tax_on_gains_is_weighted_by_wrapper():
    from app.finance.projection import _tax_on_gains

    cfg = verdicts.config().projection
    w = _wealth2(accounts=[_acc("pea", 30_000.0), _acc("cto", 10_000.0)])
    # 3/4 de PEA à 17,2 %, 1/4 de CTO à 30 %
    assert _tax_on_gains(w, cfg) == pytest.approx(0.75 * 0.172 + 0.25 * 0.30)


def test_tax_on_gains_falls_back_to_the_flat_tax():
    from app.finance.projection import _tax_on_gains

    cfg = verdicts.config().projection
    assert _tax_on_gains(_wealth2(), cfg) == pytest.approx(cfg.default_tax_on_gains)


def test_inflation_is_declared_once_for_the_whole_app():
    """Projection and « objectif » verdict deflate with the same rate (ADR-026)."""
    from app.finance import macro

    assert macro.inflation() > 0
    # It used to live here too, and two copies of one number drift apart.
    assert not hasattr(verdicts.config(), "inflation")
    assert not hasattr(verdicts.config().goal, "inflation")
    assert not hasattr(verdicts.config().goal, "risk_free")


# ── Performance et baisse depuis le plus haut ──────────────────────────────

from app.finance import performance as perf_mod  # noqa: E402

PERF_CFG = verdicts.PerformanceThresholds(min_days=30, gap_amber=-0.01)
DD_CFG = verdicts.DrawdownThresholds(alert_step=0.10, red_at=0.20)


def _series(*points: tuple[str, float, float]) -> perf_mod.Performance | None:
    return perf_mod.compute(
        [perf_mod.Point(day=date.fromisoformat(d), value=v, net_flow=f) for d, v, f in points]
    )


def test_performance_says_when_the_history_is_too_young():
    v = verdicts.performance_verdict(
        _series(("2026-09-01", 1000, 0), ("2026-09-08", 1010, 0)), PERF_CFG
    )
    assert v.status == "unknown"
    assert "01/09/2026" in v.headline
    assert v.details["min_days"] == 30


def test_performance_with_no_history_at_all():
    v = verdicts.performance_verdict(None, PERF_CFG)
    assert v.status == "unknown"
    assert "aujourd'hui" in v.headline


def test_performance_is_green_when_the_timing_costs_nothing():
    v = verdicts.performance_verdict(
        _series(("2025-09-09", 10_000, 0), ("2026-09-09", 11_000, 0)), PERF_CFG
    )
    assert v.status == "green"
    assert "+10,00 %" in v.headline
    assert v.impact_eur_per_year == 0.0


def test_performance_names_the_behaviour_gap_in_euros():
    v = verdicts.performance_verdict(
        _series(
            ("2025-09-09", 100_000, 0),
            ("2026-03-09", 200_000, 0),
            ("2026-03-10", 400_000, 200_000),
            ("2026-09-09", 280_000, 0),
        ),
        PERF_CFG,
    )
    assert v.status == "amber"
    assert v.impact_eur_per_year is not None and v.impact_eur_per_year > 0
    assert v.action is not None and "virement automatique" in v.action


def test_drawdown_is_green_near_the_high():
    v = verdicts.drawdown_verdict(
        _series(("2026-01-01", 10_000, 0), ("2026-02-01", 9_700, 0)), DD_CFG
    )
    assert v.status == "green"
    assert "3,00 %" in v.headline


def test_drawdown_alerts_at_ten_percent_and_says_not_to_sell():
    v = verdicts.drawdown_verdict(
        _series(("2026-01-01", 10_000, 0), ("2026-02-01", 12_000, 0), ("2026-03-01", 10_800, 0)),
        DD_CFG,
    )
    assert v.status == "amber"
    assert "10,00 %" in v.headline
    assert v.action is not None and "pas vendre" in v.action
    assert v.details["steps_crossed"] == 1


def test_drawdown_turns_red_past_twenty_percent():
    v = verdicts.drawdown_verdict(
        _series(("2026-01-01", 10_000, 0), ("2026-02-01", 12_000, 0), ("2026-03-01", 9_000, 0)),
        DD_CFG,
    )
    assert v.status == "red"
    assert v.details["steps_crossed"] == 2


def test_compute_all_puts_the_drawdown_first_and_performance_last():
    resp = verdicts.compute_all(_wealth2(accounts=[_acc("pea", 1000.0)]), _profile(), 1000.0)
    assert [v.id for v in resp.verdicts] == [
        "drawdown",
        "savings_rate",
        "goal",
        "next_euro",
        "risk_share",
        "fees",
        "performance",
    ]
