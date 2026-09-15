"""Unit tests for app.llm.prompt_builder — pure functions, no DB."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.db.models import Profile
from app.llm import prompt_builder
from app.models import (
    InvestmentAccount,
    Loan,
    Wealth,
    WealthEnvelope,
    WealthPosition,
)


def _make_wealth() -> Wealth:
    """Synthetic Wealth mirroring a realistic profile (PEA + livret + loan)."""
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
        checking_accounts=[],
        pea_cash_accounts=[],
        envelopes=[
            WealthEnvelope(
                provider_account_id="env-1",
                institution_name="BNP Paribas",
                name="Livret A",
                balance=8000.0,
                envelope_type="livret_a",
                display_name="Livret A",
                rate_pct=0.03,  # fraction, as in envelopes.yaml
                ceiling_eur=22950.0,
                tax_status="net",
            ),
        ],
        investment_accounts=[
            InvestmentAccount(
                provider_account_id="pea-1",
                institution_name="BNP Paribas",
                name="PEA BNP",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker="DCAM.PA",
                        label="Amundi MSCI World",
                        isin="LU1681043599",
                        quantity=10.0,
                        avg_cost=200.0,
                        current_value=2300.0,
                    ),
                ],
            ),
        ],
        loans=[
            Loan(
                provider_account_id="loan-1",
                institution_name="BNP Paribas",
                name="Prêt étudiant",
                outstanding_balance=15000.0,
                interest_rate_pct=0.015,  # fraction, as built in deps.py
                monthly_payment=200.0,
                maturity_date=date(2030, 6, 1),
            ),
        ],
    )


def _make_profile() -> Profile:
    p = Profile(user_id=uuid.uuid4(), ceilings_used={})
    p.birth_date = date(2002, 6, 15)
    p.fiscal_shares = 1.0
    p.rfr_n_minus_2 = 18000.0
    p.target_annual_return = 0.07  # fraction, as stored in DB
    p.max_annual_volatility = 0.15
    p.horizon_years = 30
    p.default_broker = "bnp"
    return p


# ── build_anonymized_snapshot ──────────────────────────────────────────────


def test_snapshot_strips_provider_ids_and_institution_names():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)

    payload = str(snap)
    # No identifiers should leak through
    assert "env-1" not in payload
    assert "pea-1" not in payload
    assert "loan-1" not in payload
    assert "BNP Paribas" not in payload

    # But tickers and core financial data MUST be there (model needs them)
    assert "DCAM.PA" in payload
    assert "LU1681043599" in payload


def test_snapshot_includes_profile_fields():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)

    assert snap["profile"]["fiscal_shares"] == 1.0
    assert snap["profile"]["rfr_n_minus_2_eur"] == 18000.0
    assert snap["profile"]["horizon_years"] == 30


def test_snapshot_computes_age_from_birth_date():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)

    today = date.today()
    expected_age = today.year - 2002 - ((today.month, today.day) < (6, 15))
    assert snap["profile"]["age"] == expected_age


def test_snapshot_handles_missing_profile_fields_gracefully():
    """An incomplete Profile must not crash — fields become None."""
    wealth = _make_wealth()
    empty_profile = Profile(user_id=uuid.uuid4(), ceilings_used={})
    snap = prompt_builder.build_anonymized_snapshot(wealth, empty_profile)

    assert snap["profile"]["age"] is None
    assert snap["profile"]["fiscal_shares"] is None
    assert snap["profile"]["rfr_n_minus_2_eur"] is None


def test_snapshot_aggregates_match_wealth_properties():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)

    assert snap["net_worth_eur"] == pytest_approx(wealth.net_worth)
    assert snap["total_assets_eur"] == pytest_approx(wealth.total_assets)
    assert snap["total_liabilities_eur"] == pytest_approx(wealth.total_liabilities)


def pytest_approx(value, tol=0.01):
    """Local helper — pytest.approx requires importing pytest at module level."""
    import pytest

    return pytest.approx(value, abs=tol)


# ── build_user_prompt ──────────────────────────────────────────────────────


def test_user_prompt_contains_section_headers():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)
    prompt = prompt_builder.build_user_prompt(snap)

    assert "## Profil utilisateur" in prompt
    assert "## Patrimoine net" in prompt
    assert "## Enveloppes réglementées" in prompt
    assert "## Comptes d'investissement" in prompt
    assert "## Prêts en cours" in prompt


def test_user_prompt_renders_real_numbers():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)
    prompt = prompt_builder.build_user_prompt(snap)

    assert "8,000.00 €" in prompt or "8 000.00 €" in prompt  # livret balance
    assert "DCAM.PA" in prompt
    assert "Amundi MSCI World" in prompt


def test_user_prompt_omits_empty_sections():
    """No envelopes / no positions / no loans → those sections are skipped."""
    wealth = Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 6, 2, tzinfo=UTC),
    )
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)
    prompt = prompt_builder.build_user_prompt(snap)

    assert "## Enveloppes réglementées" not in prompt
    assert "## Comptes d'investissement" not in prompt
    assert "## Prêts en cours" not in prompt
    # But the core sections remain
    assert "## Patrimoine net" in prompt


# ── system prompt ──────────────────────────────────────────────────────────


def test_system_prompt_contains_required_structure():
    """System prompt must instruct the model on the daily-briefing section structure."""
    sp = prompt_builder.SYSTEM_PROMPT
    for section in (
        "# Ce qui a bougé chez toi",
        "# Ce que ça veut dire",
        "# À faire cette semaine",
        "# Pistes à regarder",
        "# Sources",
        "# Avertissement",
    ):
        assert section in sp, f"missing section header in system prompt: {section}"


def test_system_prompt_mentions_web_search_requirement():
    assert "web_search" in prompt_builder.SYSTEM_PROMPT


def test_system_prompt_is_written_for_a_passive_saver():
    sp = prompt_builder.SYSTEM_PROMPT
    assert "continue tes versements" in sp
    assert "jamais d'acheter ou de vendre" in sp
    for jargon in ("Sharpe", "risk-on", "EUR/USD", "10Y"):
        assert jargon not in sp.replace("Pas de rendement attendu, volatilité, Sharpe", ""), jargon


def test_user_prompt_has_no_markowitz_block():
    wealth = _make_wealth()
    profile = _make_profile()
    snap = prompt_builder.build_anonymized_snapshot(wealth, profile)
    prompt = prompt_builder.build_user_prompt(snap)
    assert "Markowitz" not in prompt
    assert "μ=" not in prompt


def test_snapshot_and_prompt_render_fractions_as_percents():
    """DB, envelopes.yaml and Powens loans carry fractions; the model must read percents."""
    snap = prompt_builder.build_anonymized_snapshot(_make_wealth(), _make_profile())
    assert snap["profile"]["target_annual_return_pct"] == 7.0
    assert snap["profile"]["max_annual_volatility_pct"] == 15.0
    assert snap["envelopes"][0]["rate_pct"] == 3.0
    assert snap["loans"][0]["interest_rate_pct"] == 1.5
    prompt = prompt_builder.build_user_prompt(snap)
    assert "Objectif rendement annuel : 7.0 %" in prompt
    assert "Tolérance volatilité annuelle : 15.0 %" in prompt
    assert "taux 3.00 %" in prompt
    assert "1.50 %" in prompt


def test_verdicts_are_rendered_for_the_model():
    """Verdicts reach the prompt as computed: status, sentence, euros, action."""
    from app.models import Verdict

    v = Verdict(
        id="fees",
        title="Frais réels",
        status="red",
        headline="Tes placements te coûtent 2,00 % par an, soit 1 000 €.",
        impact_eur_per_year=850.0,
        action="Change de courtier.",
    )
    snapshot = prompt_builder.build_anonymized_snapshot(
        _make_wealth(), _make_profile(), verdicts=[v]
    )
    assert snapshot["verdicts"][0]["status"] == "red"
    text = prompt_builder.build_user_prompt(snapshot)
    assert "## Verdicts de la méthode" in text
    assert "**Frais réels** [rouge] (850 € par an en jeu)" in text
    assert "À faire : Change de courtier." in text


def test_no_verdicts_means_no_section():
    snapshot = prompt_builder.build_anonymized_snapshot(_make_wealth(), _make_profile())
    assert snapshot["verdicts"] == []
    assert "Verdicts de la méthode" not in prompt_builder.build_user_prompt(snapshot)


# ── everything the app knows reaches the briefing ─────────────────────────


def _full_snapshot():
    from app.finance.performance import Performance, Point
    from app.models import PicksResponse, PicksTrackRecord
    from app.routers.spending import CategorySpending, MonthSpending, SpendingResponse

    history = [
        Point(day=date(2026, 5, 3), value=2000.0, net_flow=0.0),
        Point(day=date(2026, 5, 26), value=2100.0, net_flow=0.0),
        Point(day=date(2026, 6, 1), value=2200.0, net_flow=100.0),
        Point(day=date(2026, 6, 2), value=2300.0, net_flow=0.0),
    ]
    perf = Performance(
        start=date(2026, 1, 2),
        end=date(2026, 6, 2),
        days=151,
        twr=0.052,
        twr_annualized=0.13,
        irr=0.11,
        behaviour_gap=-0.02,
        index=[1.0, 1.052],
        drawdown=-0.01,
        max_drawdown=-0.08,
        peak_day=date(2026, 5, 20),
        net_flows=1200.0,
        first_value=1000.0,
        last_value=2300.0,
    )
    spending = SpendingResponse(
        months=[
            MonthSpending(month="2026-05", total=1500.0, income=2400.0, by_category={}),
            MonthSpending(month="2026-06", total=120.0, income=0.0, by_category={}),
        ],
        categories=[
            CategorySpending(category="logement", total=1800.0, share=0.6),
            CategorySpending(category="autre", total=300.0, share=0.1),
        ],
        merchants=[],
        monthly_average=1450.0,
        monthly_income_average=2400.0,
        current_month_total=120.0,
        unlabelled_share=0.1,
    )
    picks = PicksResponse(
        computed_at="2026-06-01T02:00:00Z",
        as_of="2026-05-29",
        next_review="2026-06-30",
        review="monthly",
        guard_on=False,
        held=["DCAM.PA", "PE500.PA"],
        bought=["PE500.PA"],
        sold=["CW8.PA"],
        universe_size=40,
        indices=["^STOXX"],
        top=2,
        track_record=PicksTrackRecord(
            since="2010-01",
            cagr=0.1,
            universe_cagr=0.07,
            max_drawdown=-0.3,
            universe_max_drawdown=-0.4,
            turnover=0.2,
            reviews=190,
            guarded_reviews=20,
            yearly=[],
        ),
    )
    return prompt_builder.build_anonymized_snapshot(
        _make_wealth(),
        _make_profile(),
        spending=spending,
        monthly_saved=350.0,
        performance=perf,
        history=history,
        watchlist=["EWLD.PA"],
        previous_review="# Ce qui a bougé chez toi\nHier, rien de notable.",
        picks=picks,
        macro={"policy_rate": 0.0215, "inflation": 0.019},
    )


def test_snapshot_carries_everything_the_app_knows():
    snap = _full_snapshot()
    assert snap["macro"] == {"policy_rate_pct": 2.15, "inflation_pct": 1.9}
    assert [h["day"] for h in snap["history"]] == [
        "2026-05-03",
        "2026-05-26",
        "2026-06-01",
        "2026-06-02",
    ]
    assert snap["performance"]["twr_pct"] == 5.2
    assert snap["performance"]["behaviour_gap_pct"] == -2.0
    assert snap["spending"]["categories"][0] == {
        "category": "logement",
        "total_eur": 1800.0,
        "share_pct": 60.0,
    }
    assert snap["monthly_saved_eur"] == 350.0
    assert snap["watchlist"] == ["EWLD.PA"]
    assert snap["picks"]["held"] == ["DCAM.PA", "PE500.PA"]
    assert snap["previous_review"].startswith("# Ce qui a bougé")


def test_user_prompt_renders_the_daily_readings_net_of_contributions():
    prompt = prompt_builder.build_user_prompt(_full_snapshot())
    assert "## Relevés quotidiens du portefeuille" in prompt
    assert "Valeur au 2026-06-02 : 2,300.00 €" in prompt
    # since yesterday: 2300 − 2200, no contribution on the 2nd
    assert "Depuis hier (2026-06-01) : +100.00 €" in prompt
    # since 7 days: 2300 − 2100 − 100 paid in on the 1st
    assert "Depuis 7 jours (2026-05-26) : +100.00 €, versements sur la période 100.00 €" in prompt
    assert "Depuis 30 jours (2026-05-03) : +200.00 €, versements sur la période 100.00 €" in prompt


def test_user_prompt_renders_the_other_sections():
    prompt = prompt_builder.build_user_prompt(_full_snapshot())
    assert "## Performance mesurée depuis le 2026-01-02 (151 jours)" in prompt
    assert "(pondéré par le temps) : +5.20 %" in prompt
    assert "Recul depuis le plus haut : -1.00 % (plus haut le 2026-05-20), pire recul" in prompt
    assert "Versé au total sur la période : 1,200.00 €" in prompt
    assert "## Dépenses et épargne" in prompt
    assert "Dépenses moyennes par mois : 1,450 €" in prompt
    assert "logement 1,800 €" in prompt
    assert "Mis de côté en moyenne par mois (livrets et placements) : 350 €" in prompt
    assert "## Contexte observé" in prompt
    assert "Taux directeur : 2.15 %" in prompt
    assert "## Liste de suivi" in prompt and "`EWLD.PA`" in prompt
    assert "## « La liste de l'année »" in prompt
    assert "Entrées à la dernière revue : `PE500.PA`" in prompt
    assert "Sorties à la dernière revue : `CW8.PA`" in prompt
    assert "## Briefing d'hier" in prompt
    assert "Hier, rien de notable." in prompt
    # order: yesterday's briefing comes last, right before the instruction
    assert prompt.index("## Briefing d'hier") > prompt.index("## « La liste de l'année »")


def test_without_the_extra_data_the_prompt_is_unchanged_in_shape():
    snap = prompt_builder.build_anonymized_snapshot(_make_wealth(), _make_profile())
    prompt = prompt_builder.build_user_prompt(snap)
    for header in (
        "## Relevés quotidiens",
        "## Performance mesurée",
        "## Dépenses et épargne",
        "## Contexte observé",
        "## Liste de suivi",
        "## « La liste de l'année »",
        "## Briefing d'hier",
    ):
        assert header not in prompt, header


def test_a_single_reading_is_not_a_movement():
    from app.finance.performance import Point

    snap = prompt_builder.build_anonymized_snapshot(
        _make_wealth(), _make_profile(), history=[Point(date(2026, 6, 2), 2300.0, 0.0)]
    )
    assert "## Relevés quotidiens" not in prompt_builder.build_user_prompt(snap)


def test_system_prompt_tells_the_model_what_the_extra_data_is_for():
    sp = prompt_builder.SYSTEM_PROMPT
    assert "relevés quotidiens" in sp.lower()
    assert "briefing d'hier" in sp.lower()
    assert "liste de l'année" in sp.lower()
    assert "pas de leçon de budget" in sp.lower()
