"""The verdict engine writes English when asked; French stays the default (ADR-036)."""

from __future__ import annotations

from app.finance import verdicts

from .test_verdicts import (
    DD_CFG,
    DIV,
    FREE,
    GOAL,
    NEXT,
    PERF_CFG,
    RISK,
    SAVE,
    THRESHOLDS,
    _acc,
    _env,
    _line,
    _pea_with_lines,
    _pos,
    _profile,
    _wealth,
    _wealth2,
)


def test_number_helpers_follow_the_locale():
    assert verdicts._eur(1500) == "1 500 €"
    assert verdicts._eur(1500, "en") == "€1,500"
    assert verdicts._pct(0.075, 1) == "7,5 %"
    assert verdicts._pct(0.075, 1, "en") == "7.5%"
    assert verdicts._signed_pct(0.031) == "+3,10 %"
    assert verdicts._signed_pct(-0.031, "en") == "−3.10%"
    assert verdicts._join(["A", "B", "C"]) == "A, B et C"
    assert verdicts._join(["A", "B", "C"], "en") == "A, B and C"
    assert verdicts._join(["A"], "en") == "A"


def test_fees_in_english():
    w = _wealth(_pos("CW8.PA", 10_000, 0.0038))
    v = verdicts.fees_verdict(w, FREE, 0.0, THRESHOLDS, locale="en")
    assert v.status == "green"
    assert v.title == "Real fees"
    assert (
        v.headline == "Your investments cost you 0.38% a year, €38: that is low, nothing to change."
    )
    fr = verdicts.fees_verdict(w, FREE, 0.0, THRESHOLDS)
    assert (
        fr.headline
        == "Tes placements te coûtent 0,38 % par an, soit 38 € : c'est bas, rien à changer."
    )


def test_fees_missing_ter_in_english():
    w = _wealth(_pos("A", 1_000, None), _pos("B", 1_000, None))
    v = verdicts.fees_verdict(w, FREE, 0.0, THRESHOLDS, locale="en")
    assert v.status == "unknown"
    assert v.headline.startswith("The annual fees (TER) of 2 lines are missing, 100.00% of")
    assert v.action == "Enter the TER of these lines in Accounts (open the account, then the line)."


def test_next_euro_in_english():
    w = _wealth2(envelopes=[_env("livret_a", 1000.0)], accounts=[_acc("pea", 5000.0)])
    v = verdicts.next_euro_verdict(w, _profile(), 1500.0, NEXT, locale="en")
    assert v.title == "Where the next euro goes"
    assert v.headline.startswith("Your next euro goes into ")
    assert "your emergency savings cover 0.7 months of spending, the target is 3" in v.headline
    precaution = v.details["steps"][0]
    assert precaution["label"] == "Emergency savings"
    assert precaution["text"].startswith("€1,000 in your savings accounts, 0.7 months of spending;")
    fr = verdicts.next_euro_verdict(w, _profile(), 1500.0, NEXT)
    assert fr.headline.startswith("Ton prochain euro va dans ")
    assert fr.details["steps"][0]["label"] == "Épargne de précaution"


def test_risk_share_in_english():
    w = _wealth2(accounts=[_pea_with_lines(10_000)])
    v = verdicts.risk_share_verdict(w, _profile(), RISK, locale="en")
    assert v.status == "unknown"
    assert v.title == "Equity share"
    assert v.headline == (
        "You have 100% in equities out of €10,000 of long-term investments, but your "
        "cautious ↔ dynamic slider is not set."
    )


def test_savings_rate_in_english():
    v = verdicts.savings_rate_verdict(_profile(rfr=24_000, dca=500), None, SAVE, locale="en")
    assert v.status == "green"
    assert v.title == "Savings rate"
    assert v.headline == (
        "You save €500 a month, 25% of your income (from your declared contribution): "
        "above the 15% target, this is what builds the capital."
    )
    assert v.action == (
        "Schedule an automatic 5% rise a year: €525 a month next year, without thinking about it."
    )


def test_goal_in_english():
    v = verdicts.goal_verdict(_wealth2(), _profile(), None, GOAL, RISK, locale="en")
    assert v.status == "unknown"
    assert v.title == "Saving for your goal"
    assert v.headline.startswith("You have not set a goal: ")
    assert v.action == "Set your goal in Projection (“My goal”)."


def test_performance_in_english():
    v = verdicts.performance_verdict(None, PERF_CFG, locale="en")
    assert v.title == "What your investments really returned"
    assert v.headline.startswith("Your account history starts today.")


def test_drawdown_in_english():
    v = verdicts.drawdown_verdict(None, DD_CFG, locale="en")
    assert v.title == "Drop from the peak"
    assert v.headline == "No history yet: the drop from the peak will be tracked here."


def test_diversification_in_english():
    w = _wealth(
        _line("Amundi MSCI World", 300.0),
        _line("iShares Core MSCI World", 300.0),
        _line("Lyxor MSCI World", 400.0),
    )
    v = verdicts.diversification_verdict(w, DIV, locale="en")
    assert v.status == "amber"
    assert v.title == "Allocation"
    assert v.headline.startswith(
        "Amundi MSCI World, iShares Core MSCI World and Lyxor MSCI World all track “"
    )
    assert v.headline.endswith("”: keeping several protects you no more than one.")
    fr = verdicts.diversification_verdict(w, DIV)
    assert fr.headline.startswith(
        "Amundi MSCI World, iShares Core MSCI World et Lyxor MSCI World suivent tous « "
    )


def test_compute_all_takes_the_locale_and_defaults_to_french():
    w = _wealth2(accounts=[_acc("pea", 1000.0)])
    en = {v.id: v.title for v in verdicts.compute_all(w, _profile(), 1000.0, locale="en").verdicts}
    assert en == {
        "drawdown": "Drop from the peak",
        "savings_rate": "Savings rate",
        "goal": "Saving for your goal",
        "next_euro": "Where the next euro goes",
        "risk_share": "Equity share",
        "diversification": "Allocation",
        "fees": "Real fees",
        "performance": "What your investments really returned",
    }
    fr = {v.id: v.title for v in verdicts.compute_all(w, _profile(), 1000.0).verdicts}
    assert fr["fees"] == "Frais réels"
    assert fr["next_euro"] == "Où placer le prochain euro"
