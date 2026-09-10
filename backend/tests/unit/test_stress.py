"""Unit tests for finance.stress — historical episodes replayed on asset classes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.finance import classification, stress
from app.models import CashAccount, InvestmentAccount, Wealth, WealthEnvelope, WealthPosition


def _wealth(
    *,
    equity: float = 0.0,
    livret: float = 0.0,
    life: float = 0.0,
    pea_cash: float = 0.0,
    ticker: str = "CW8.PA",
    label: str | None = None,
) -> Wealth:
    accounts = []
    if equity:
        accounts.append(
            InvestmentAccount(
                provider_account_id="pea",
                name="PEA",
                account_type="pea",
                positions=[
                    WealthPosition(
                        ticker=ticker,
                        label=label or ticker,
                        quantity=1.0,
                        avg_cost=equity,
                        current_value=equity,
                    )
                ],
            )
        )
    if life:
        accounts.append(
            InvestmentAccount(
                provider_account_id="av",
                name="Assurance vie",
                account_type="life_insurance",
                balance=life,
            )
        )
    return Wealth(
        user_id=uuid.uuid4(),
        snapshot_at=datetime(2026, 9, 9, tzinfo=UTC),
        investment_accounts=accounts,
        pea_cash_accounts=(
            [
                CashAccount(
                    provider_account_id="cash", name="Espèces", balance=pea_cash, is_pea_cash=True
                )
            ]
            if pea_cash
            else []
        ),
        envelopes=(
            [
                WealthEnvelope(
                    provider_account_id="la",
                    name="Livret A",
                    balance=livret,
                    envelope_type="livret_a",
                )
            ]
            if livret
            else []
        ),
    )


def _scenario(sid: str) -> stress.Scenario:
    return next(s for s in stress.config().scenarios if s.id == sid)


# ── The library itself ─────────────────────────────────────────────────────


def test_the_library_reaches_past_2020():
    """The whole point: the deepest falls are older than any French ETF."""
    ids = {s.id for s in stress.config().scenarios}
    assert {"dotcom_2000", "gfc_2008", "euro_2011"} <= ids
    assert len(ids) >= 10


def test_the_worst_episode_is_the_dot_com_slide():
    worst = min(stress.config().scenarios, key=lambda s: s.returns["equity_world"])
    assert worst.id == "dotcom_2000"
    assert worst.returns["equity_world"] == pytest.approx(-0.525)


def test_at_least_one_inflation_regime_is_in_the_library():
    """1973-74 and 2022 are the two episodes where bonds fell with equities."""
    s = _scenario("inflation_2022")
    assert s.returns["equity_world"] < 0
    assert s.returns["bonds_euro"] < 0


# ── The dollar ─────────────────────────────────────────────────────────────


def test_the_dollar_cushioned_the_2008_fall_for_a_european():
    effect = _scenario("gfc_2008").currency_effect
    assert effect is not None and effect > 0  # −48,2 % en euros contre −53,6 % en dollars


def test_the_dollar_deepened_the_dot_com_fall():
    effect = _scenario("dotcom_2000").currency_effect
    assert effect is not None and effect < 0


def test_2025_was_the_currency_not_the_market():
    s = _scenario("tariffs_2025")
    assert s.currency_effect is not None
    assert abs(s.currency_effect) > abs(s.returns["equity_world_usd"])


def test_an_episode_without_a_comparable_dollar_figure_says_nothing():
    """COVID: the published euro loss is month-end, the dollar one is daily."""
    assert _scenario("covid_2020").currency_effect is None


# ── Exposure mapping ───────────────────────────────────────────────────────


def test_every_pocket_lands_in_a_class():
    e = stress.exposure(_wealth(equity=10_000, livret=5_000, life=20_000, pea_cash=1_000))
    assert e["equity_world"] == pytest.approx(10_000)
    assert e["cash"] == pytest.approx(6_000)  # livret + espèces du PEA
    assert e["fonds_euros"] == pytest.approx(20_000)


def test_an_unknown_ticker_is_treated_as_world_equity():
    e = stress.exposure(_wealth(equity=1_000, ticker="XYZ.PA"))
    assert e == {"equity_world": pytest.approx(1_000)}


# ── The loss ───────────────────────────────────────────────────────────────


def test_a_pure_equity_portfolio_takes_the_full_hit():
    results = stress.compute(_wealth(equity=10_000))
    worst = results[0]
    assert worst.id == "dotcom_2000"
    assert worst.loss_eur == pytest.approx(-5_250)
    assert worst.pnl_pct == pytest.approx(-0.525)


def test_a_livret_does_not_fall_and_softens_the_percentage():
    results = stress.compute(_wealth(equity=10_000, livret=10_000))
    worst = next(r for r in results if r.id == "dotcom_2000")
    # Le livret ne perd rien et gagne 8 % sur trente et un mois.
    assert worst.loss_eur == pytest.approx(-5_250 + 800)
    assert worst.pnl_pct == pytest.approx((-5_250 + 800) / 20_000)


def test_bonds_fell_with_equities_in_2022_only():
    """The 60/40 lost on both legs in 2022, and only in 2022."""
    covid = _scenario("covid_2020")
    assert _scenario("gfc_2008").returns["bonds_euro"] > 0
    assert _scenario("inflation_2022").returns["bonds_euro"] < 0
    assert covid.returns["bonds_euro"] < 0  # −5 % intra-mars


def test_results_are_ordered_worst_first():
    results = stress.compute(_wealth(equity=10_000))
    assert [r.pnl_pct for r in results] == sorted(r.pnl_pct for r in results)


def test_an_empty_patrimony_has_nothing_to_stress():
    assert stress.compute(_wealth()) == []


def test_the_currency_effect_is_priced_on_the_equity_pocket_only():
    results = stress.compute(_wealth(equity=10_000, livret=90_000))
    gfc = next(r for r in results if r.id == "gfc_2008")
    assert gfc.currency_effect_pct is not None
    assert gfc.currency_effect_eur == pytest.approx(gfc.currency_effect_pct * 10_000)


# ── L'or : la classe qui manquait ─────────────────────────────────────────


def test_gold_is_replayed_on_its_own_history_not_as_equity():
    """In 2008 gold gained 32 % in euros while world equities lost 48 %."""
    cfg = stress.config()
    gfc = next(s for s in cfg.scenarios if s.id == "gfc_2008")

    assert gfc.ret("gold") > 0.3
    assert gfc.ret("equity_world") < -0.4


def test_a_gold_line_is_recognised_and_lands_in_the_gold_class():
    wealth = _wealth(equity=10_000.0, ticker="GLD.PA", label="iShares Physical Gold ETC")

    assert stress.exposure(wealth).get("gold") == pytest.approx(10_000.0)


def test_a_gold_holder_does_not_lose_everything_in_2008():
    """The whole point of the class: a diversifier must not be replayed as equity."""
    gold_only = _wealth(equity=10_000.0, ticker="GLD.PA", label="iShares Physical Gold ETC")
    equity_only = _wealth(equity=10_000.0, ticker="CW8.PA", label="Amundi MSCI World")

    gold_2008 = next(r for r in stress.compute(gold_only) if r.id == "gfc_2008")
    equity_2008 = next(r for r in stress.compute(equity_only) if r.id == "gfc_2008")

    assert gold_2008.pnl_pct > 0
    assert equity_2008.pnl_pct < -0.4


def test_the_class_of_a_line_no_longer_depends_on_a_table_of_known_tickers():
    """Any world tracker works, not only the six that used to be listed."""
    mine = _wealth(equity=1_000.0, ticker="CW8.PA", label="Amundi MSCI World")
    someone_else = _wealth(equity=1_000.0, ticker="SWDA.L", label="iShares Core MSCI World")

    assert stress.exposure(mine) == stress.exposure(someone_else)


# ── La cascade : la ligne, puis sa classe, puis le chiffre déclaré ─────────


def _scenario(episode: str = "covid_2020") -> stress.Scenario:
    return next(s for s in stress.config().scenarios if s.id == episode)


def test_a_line_is_measured_on_its_own_price_when_yahoo_reaches_that_far(monkeypatch):
    """The finest answer available: not the class's amplitude, but this line's."""
    monkeypatch.setattr(
        stress.episodes,
        "measure",
        lambda _id, provider, *a, **k: -0.31 if provider == "yahoo" else None,
    )
    pocket = stress.Pocket("equity_world", 1_000.0, classification.Quote("CW8.PA", "EUR"))

    assert stress.pocket_return(pocket, _scenario()) == pytest.approx(-0.31)


def test_a_line_too_young_for_the_episode_falls_back_on_its_class(monkeypatch):
    """An ETF created in 2019 cannot replay 2008 — and must not blank the episode."""
    monkeypatch.setattr(stress.episodes, "measure", lambda *a, **k: None)
    scenario = _scenario("gfc_2008")
    pocket = stress.Pocket("equity_world", 1_000.0, classification.Quote("CW8.PA", "EUR"))

    assert stress.pocket_return(pocket, scenario) == scenario.returns["equity_world"]


def test_a_line_with_no_readable_venue_is_replayed_as_its_class(monkeypatch):
    monkeypatch.setattr(stress.episodes, "measure", lambda *a, **k: -0.99)
    scenario = _scenario()
    pocket = stress.Pocket("cash", 1_000.0, quote=None)

    assert stress.pocket_return(pocket, scenario) == scenario.returns["cash"]


def test_a_class_with_no_figure_borrows_one_rather_than_counting_zero():
    scenario = _scenario()

    assert scenario.ret("equity_japan", {}, {}) == 0.0
    assert scenario.ret("equity_japan", {}, {"equity_japan": "equity_world"}) == pytest.approx(
        scenario.returns["equity_world"]
    )


def test_the_first_candidate_that_covers_the_window_wins(monkeypatch):
    """Nobody checks by hand how far back an index goes: the loop tries and moves on."""
    tried: list[str] = []

    def measure(series_id: str, *a: object, **k: object) -> float | None:
        tried.append(series_id)
        return -0.2 if series_id == "SECOND" else None

    cfg = stress.config().model_copy(deep=True)
    cfg.class_series = {
        "equity_japan": [
            stress.IndexSeries(provider="yahoo", id="FIRST", currency="EUR"),
            stress.IndexSeries(provider="yahoo", id="SECOND", currency="EUR"),
            stress.IndexSeries(provider="yahoo", id="THIRD", currency="EUR"),
        ]
    }
    monkeypatch.setattr(stress.episodes, "measure", measure)

    measured = stress.measured_returns(_scenario(), cfg)

    assert measured["equity_japan"] == pytest.approx(-0.2)
    assert tried == ["FIRST", "SECOND"]  # on s'arrête au premier qui répond
