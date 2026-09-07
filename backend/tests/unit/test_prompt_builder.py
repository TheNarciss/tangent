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
                rate_pct=3.0,
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
                interest_rate_pct=1.5,
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
    p.target_annual_return = 7.0
    p.max_annual_volatility = 15.0
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
