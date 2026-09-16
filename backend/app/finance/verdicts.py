"""Verdicts — the method's conclusions, one per technique (ADR-023).

A verdict is a status, one sentence, an amount in euros per year and an
action (or none). The engine computes here; the simple screens show the
status and the sentence, the Méthode tab unfolds `details`, and the
briefing reads the same list. Thresholds live in `config/verdicts.yaml`.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel, Field

from ..db.models import Profile
from ..errors import ConfigurationError, UnknownBrokerError
from ..i18n import Locale, t
from ..models import Verdict, VerdictsResponse, Wealth
from . import classification, envelopes, fees, macro, performance, references, risk_profile

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "verdicts.yaml"


class FeesThresholds(BaseModel):
    green_max: float = Field(ge=0)
    amber_max: float = Field(ge=0)
    reference: float = Field(ge=0)
    min_coverage: float = Field(ge=0, le=1)


class TaxBracket(BaseModel):
    up_to: float | None
    rate: float = Field(ge=0, le=1)


class NextEuroThresholds(BaseModel):
    precaution_months: float = Field(gt=0)
    precaution_min_months: float = Field(ge=0)
    liquid_envelopes: list[str]
    pea_ceiling_eur: float = Field(gt=0)
    pea_vs_cto_pct: float = Field(ge=0)
    per_tmi_min: float = Field(ge=0, le=1)
    per_ceiling_pct: float = Field(ge=0, le=1)
    per_ceiling_min_eur: float = Field(ge=0)
    per_ceiling_max_eur: float = Field(ge=0)
    tax_brackets: list[TaxBracket]


class HorizonCap(BaseModel):
    max_years: float | None
    max_share: float = Field(ge=0, le=1)


class RiskShareThresholds(BaseModel):
    equity_premium: float = Field(gt=0)
    equity_sigma: float = Field(gt=0)
    band: float = Field(ge=0, le=1)
    red_gap: float = Field(ge=0, le=1)
    horizon_caps: list[HorizonCap]


class SavingsRateThresholds(BaseModel):
    target: float = Field(gt=0, le=1)
    amber_min: float = Field(ge=0, le=1)
    escalation: float = Field(ge=0, le=1)
    growth_for_20y: float = Field(ge=0)
    horizon_years: int = Field(gt=0)


class GoalThresholds(BaseModel):
    target_probability: float = Field(gt=0, lt=1)
    amber_probability: float = Field(gt=0, lt=1)
    n_paths: int = Field(gt=0)
    seed: int = 0


class RetirementThresholds(BaseModel):
    withdrawal_rate: float = Field(gt=0, le=0.1)


class ProjectionThresholds(BaseModel):
    target_probability: float = Field(gt=0, lt=1)
    tax_on_gains: dict[str, float]
    default_tax_on_gains: float = Field(ge=0, le=1)


class PerformanceThresholds(BaseModel):
    min_days: int = Field(gt=0)
    gap_amber: float


class DrawdownThresholds(BaseModel):
    alert_step: float = Field(gt=0, lt=1)
    red_at: float = Field(gt=0, lt=1)


class DiversificationThresholds(BaseModel):
    single_line_max: float = Field(gt=0, le=1)


class VerdictsConfig(BaseModel):
    diversification: DiversificationThresholds
    performance: PerformanceThresholds
    drawdown: DrawdownThresholds
    projection: ProjectionThresholds
    fees: FeesThresholds
    next_euro: NextEuroThresholds
    risk_share: RiskShareThresholds
    savings_rate: SavingsRateThresholds
    goal: GoalThresholds
    retirement: RetirementThresholds


def _load_config() -> VerdictsConfig:
    if not _PATH.exists():
        raise ConfigurationError(f"Fichier de config verdicts manquant: {_PATH}.")
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalide dans {_PATH.name}: {exc}") from exc
    try:
        return VerdictsConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"Schéma verdicts.yaml invalide: {exc}") from exc


_CONFIG: VerdictsConfig | None = None


def config() -> VerdictsConfig:
    """Lazy-load the thresholds; cached for the process lifetime."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_config()
    return _CONFIG


def _eur(value: float, locale: Locale = "fr") -> str:
    """1234.5 → « 1 235 € » (narrow no-break space as thousands separator); « €1,235 » in English."""
    if locale == "en":
        return f"€{value:,.0f}"
    return f"{value:,.0f} €".replace(",", " ")


def _join(names: list[str], locale: Locale = "fr") -> str:
    """'A, B et C' — so one sentence works with two funds or with five."""
    if len(names) == 1:
        return names[0]
    return t(locale, "verdicts.join.and", head=", ".join(names[:-1]), last=names[-1])


def _by_priority(verdicts: list[Verdict]) -> list[Verdict]:
    """What needs attention first, then what it is worth per year.

    The Méthode screen is read top-down, so the order *is* the advice: what is
    red or amber comes first, biggest euro impact leading; what is green sits
    at the bottom, where it reassures without competing.
    """
    rank = {"red": 0, "amber": 1, "unknown": 2, "green": 3}
    return sorted(
        verdicts,
        key=lambda v: (rank.get(v.status, 9), -(v.impact_eur_per_year or 0.0)),
    )


def _pct(fraction: float, digits: int = 2, locale: Locale = "fr") -> str:
    """0.0092 → « 0,92 % » ; with digits=0, 0.30 → « 30 % » ; « 0.92% » in English."""
    if locale == "en":
        return f"{fraction * 100:.{digits}f}%"
    return f"{fraction * 100:.{digits}f} %".replace(".", ",")


def _lines(n: int, locale: Locale) -> str:
    """« 3 lignes » / « 1 ligne » — the count with its noun."""
    return t(locale, "verdicts.fees.lines.many" if n > 1 else "verdicts.fees.lines.one", n=n)


def fees_verdict(
    wealth: Wealth,
    broker_fees: fees.BrokerFees,
    monthly_contribution: float,
    thresholds: FeesThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Frais réels » : what the user's lines cost per year, all layers summed.

    Fund fees = Σ current_value × TER (TER entered by the user or resolved,
    per line). Broker fees = custody on the lines' value + fixed fee per line
    + courtage on twelve monthly contributions. Prices are already net of
    fund fees, so nothing here feeds the projection: this is a cost of
    holding, shown once a year in euros.
    """
    cfg = thresholds or config().fees
    title = t(locale, "verdicts.fees.title")

    lines: list[dict[str, Any]] = []
    uncovered: list[dict[str, Any]] = []
    for acc in wealth.investment_accounts:
        if not acc.positions:
            if acc.value > 0:
                uncovered.append(
                    {"name": acc.name, "account_type": acc.account_type, "value_eur": acc.value}
                )
            continue
        for p in acc.positions:
            if p.current_value <= 0:
                continue
            lines.append(
                {
                    "ticker": p.ticker,
                    "label": p.label,
                    "account": acc.name,
                    "value_eur": p.current_value,
                    "ter": p.ter,
                    "ter_source_url": p.ter_source_url,
                    "fund_fee_eur": p.current_value * p.ter if p.ter is not None else None,
                }
            )

    positions_total = sum(line["value_eur"] for line in lines)
    if positions_total <= 0:
        return Verdict(
            id="fees",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.fees.headline.no_lines"),
            details={"uncovered_accounts": uncovered},
        )

    missing = [line for line in lines if line["ter"] is None]
    known_value = sum(line["value_eur"] for line in lines if line["ter"] is not None)
    coverage = known_value / positions_total
    fund_fees = sum(line["fund_fee_eur"] or 0.0 for line in lines)
    broker_eur = (
        broker_fees.fixed_per_line_eur * len(lines)
        + broker_fees.custody_pct * positions_total
        + broker_fees.courtage_pct * monthly_contribution * 12.0
    )
    total = fund_fees + broker_eur
    total_pct = total / positions_total
    reference_eur = cfg.reference * positions_total
    saving = max(0.0, total - reference_eur)

    details: dict[str, Any] = {
        "positions_total_eur": positions_total,
        "total_fees_eur": total,
        "total_fees_pct": total_pct,
        "fund_fees_eur": fund_fees,
        "broker_fees_eur": broker_eur,
        "broker_name": broker_fees.name,
        "broker_known": not broker_fees.placeholder,
        "monthly_contribution_eur": monthly_contribution,
        "reference_pct": cfg.reference,
        "reference_eur": reference_eur,
        "coverage": coverage,
        "lines": sorted(lines, key=lambda line: line["value_eur"], reverse=True),
        "missing_ter": [
            {"ticker": m["ticker"], "label": m["label"], "value_eur": m["value_eur"]}
            for m in missing
        ],
        "uncovered_accounts": uncovered,
        "thresholds": {"green_max": cfg.green_max, "amber_max": cfg.amber_max},
    }

    if coverage < cfg.min_coverage:
        n = len(missing)
        return Verdict(
            id="fees",
            title=title,
            status="unknown",
            headline=t(
                locale,
                "verdicts.fees.headline.missing_ter",
                lines=_lines(n, locale),
                share=_pct(1 - coverage, locale=locale),
            ),
            action=t(locale, "verdicts.fees.action.missing_ter"),
            details=details,
        )

    # "au moins" as soon as something is missing: an unknown TER or an unknown
    # broker both mean the real cost is above what we can show.
    at_least = t(locale, "verdicts.fees.at_least") if (missing or broker_fees.placeholder) else ""
    base = t(
        locale,
        "verdicts.fees.base",
        at_least=at_least,
        pct=_pct(total_pct, locale=locale),
        total=_eur(total, locale),
    )
    to_complete: list[str] = []
    if missing:
        to_complete.append(
            t(locale, "verdicts.fees.complete.ter", lines=_lines(len(missing), locale))
        )
    if broker_fees.placeholder:
        to_complete.append(t(locale, "verdicts.fees.complete.broker"))
    complete = (
        t(
            locale,
            "verdicts.fees.complete",
            items=t(locale, "verdicts.fees.complete.join").join(to_complete),
        )
        if to_complete
        else ""
    )

    if total_pct <= cfg.green_max:
        return Verdict(
            id="fees",
            title=title,
            status="green",
            headline=t(locale, "verdicts.fees.headline.green", base=base),
            impact_eur_per_year=0.0,
            action=complete.strip() or None,
            details=details,
        )
    if total_pct <= cfg.amber_max:
        return Verdict(
            id="fees",
            title=title,
            status="amber",
            headline=t(
                locale,
                "verdicts.fees.headline.amber",
                base=base,
                reference=_eur(reference_eur, locale),
            ),
            impact_eur_per_year=saving,
            action=t(
                locale, "verdicts.fees.action.amber", saving=_eur(saving, locale), complete=complete
            ),
            details=details,
        )
    return Verdict(
        id="fees",
        title=title,
        status="red",
        headline=t(locale, "verdicts.fees.headline.red", base=base, saving=_eur(saving, locale)),
        impact_eur_per_year=saving,
        action=t(
            locale, "verdicts.fees.action.red", saving=_eur(saving, locale), complete=complete
        ),
        details=details,
    )


def marginal_tax_rate(
    taxable_income: float, fiscal_shares: float, brackets: list[TaxBracket]
) -> float:
    """Tranche marginale d'imposition : the bracket the last euro per part falls in."""
    quotient = taxable_income / max(fiscal_shares, 0.5)
    for b in brackets:
        if b.up_to is None or quotient <= b.up_to:
            return b.rate
    return brackets[-1].rate


def _age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _step(step_id: str, label: str, status: str, text: str, impact: float | None = None) -> dict:
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "text": text,
        "impact_eur_per_year": impact,
    }


def next_euro_verdict(
    wealth: Wealth,
    profile: Profile,
    monthly_spending: float | None,
    thresholds: NextEuroThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Où placer le prochain euro » : the envelope sequencing rule (étude §8.1).

    Précaution (3 months of spending in Livret A / LDDS / LEP) → long term in
    a PEA → PER only above the 30 % bracket → CTO for the rest. Each step is
    scored; the first one not satisfied decides the destination, the others
    stay visible as opportunities (LEP, PER) in the details.
    """
    cfg = thresholds or config().next_euro
    title = t(locale, "verdicts.next_euro.title")
    envs = envelopes.config().envelopes

    if not wealth.envelopes and not wealth.investment_accounts and not wealth.checking_accounts:
        return Verdict(
            id="next_euro",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.next_euro.headline.nothing"),
            action=t(locale, "verdicts.next_euro.action.nothing"),
        )

    age = _age(profile.birth_date)
    rfr = profile.rfr_n_minus_2
    shares = profile.fiscal_shares
    profile_complete = age is not None and rfr is not None and shares is not None and shares > 0
    dca_year = float(profile.monthly_dca or 0.0) * 12.0

    # ── Accounts on hand ──────────────────────────────────────────────────
    by_type = {e.envelope_type: e for e in wealth.envelopes}
    liquid = sum(e.balance for e in wealth.envelopes if e.envelope_type in cfg.liquid_envelopes)
    kinds = {acc.account_type for acc in wealth.investment_accounts}
    has_pea = "pea" in kinds or bool(wealth.pea_cash_accounts)
    has_per = bool(kinds & {"per", "perp", "perco", "madelin", "article_83"})
    cto_value = sum(acc.value for acc in wealth.investment_accounts if acc.account_type == "cto")
    pea_value = sum(
        acc.value for acc in wealth.investment_accounts if acc.account_type == "pea"
    ) + sum(a.balance for a in wealth.pea_cash_accounts)

    # ── Eligibility and tax bracket ───────────────────────────────────────
    lep_eligible: bool | None = None
    if profile_complete and "lep" in envs:
        lep_eligible, _ = envelopes.check_eligibility(envs["lep"], age, rfr, shares)  # type: ignore[arg-type]
    tmi: float | None = (
        marginal_tax_rate(rfr, shares, cfg.tax_brackets) if profile_complete else None  # type: ignore[arg-type]
    )

    steps: list[dict] = []

    # 1. Précaution
    target = cfg.precaution_months * monthly_spending if monthly_spending else None
    months_covered = liquid / monthly_spending if monthly_spending else None
    precaution_short = target is not None and liquid < target
    precaution_label = t(locale, "verdicts.next_euro.step.precaution.label")
    months_txt = f"{months_covered:.1f}" if months_covered is not None else ""
    target_months_txt = f"{cfg.precaution_months:g}"
    if monthly_spending is None:
        steps.append(
            _step(
                "precaution",
                precaution_label,
                "unknown",
                t(
                    locale,
                    "verdicts.next_euro.step.precaution.unknown",
                    liquid=_eur(liquid, locale),
                ),
            )
        )
    elif precaution_short:
        assert months_covered is not None and target is not None
        steps.append(
            _step(
                "precaution",
                precaution_label,
                "red" if months_covered < cfg.precaution_min_months else "amber",
                t(
                    locale,
                    "verdicts.next_euro.step.precaution.short",
                    liquid=_eur(liquid, locale),
                    months=months_txt,
                    target_months=target_months_txt,
                    target=_eur(target, locale),
                ),
            )
        )
    else:
        assert months_covered is not None and target is not None
        steps.append(
            _step(
                "precaution",
                precaution_label,
                "green",
                t(
                    locale,
                    "verdicts.next_euro.step.precaution.green",
                    liquid=_eur(liquid, locale),
                    months=months_txt,
                    target_months=target_months_txt,
                    target=_eur(target, locale),
                ),
            )
        )

    # 2. LEP : best net rate, only if eligible
    lep = envs.get("lep")
    livret_a = envs.get("livret_a")
    lep_gain = 0.0
    movable = 0.0
    lep_label = t(locale, "verdicts.next_euro.step.lep.label")
    if lep is not None and livret_a is not None:
        if lep_eligible is None:
            steps.append(
                _step(
                    "lep",
                    lep_label,
                    "unknown",
                    t(locale, "verdicts.next_euro.step.lep.unknown"),
                )
            )
        elif lep_eligible:
            lep_acc = by_type.get("lep")
            headroom = (
                lep_acc.headroom_eur
                if lep_acc and lep_acc.headroom_eur is not None
                else lep.ceiling_eur
            ) or 0.0
            other_livrets = sum(
                e.balance
                for e in wealth.envelopes
                if e.envelope_type in ("livret_a", "ldds", "livret_a_jeune", "livret_b", "csl")
            )
            movable = min(headroom, other_livrets)
            lep_gain = max(0.0, (lep.rate_pct - livret_a.rate_pct) * movable)
            if movable > 0:
                steps.append(
                    _step(
                        "lep",
                        lep_label,
                        "amber",
                        t(
                            locale,
                            "verdicts.next_euro.step.lep.amber",
                            rate=_pct(lep.rate_pct, locale=locale),
                            movable=_eur(movable, locale),
                            gain=_eur(lep_gain, locale),
                            open="" if lep_acc else t(locale, "verdicts.next_euro.step.lep.open"),
                        ),
                        lep_gain,
                    )
                )
            else:
                steps.append(
                    _step(
                        "lep",
                        lep_label,
                        "green",
                        t(locale, "verdicts.next_euro.step.lep.full"),
                    )
                )
        else:
            steps.append(
                _step(
                    "lep",
                    lep_label,
                    "green",
                    t(locale, "verdicts.next_euro.step.lep.ineligible"),
                )
            )

    # 3. Long terme : PEA
    pea_gain = 0.0
    pea_label = t(locale, "verdicts.next_euro.step.pea.label")
    if has_pea:
        room = max(0.0, cfg.pea_ceiling_eur - pea_value)
        steps.append(
            _step(
                "pea",
                pea_label,
                "green" if room > 0 else "amber",
                t(
                    locale,
                    "verdicts.next_euro.step.pea.room",
                    value=_eur(pea_value, locale),
                    room=_eur(room, locale),
                )
                if room > 0
                else t(locale, "verdicts.next_euro.step.pea.full"),
            )
        )
    else:
        pea_gain = cfg.pea_vs_cto_pct * (cto_value + dca_year)
        steps.append(
            _step(
                "pea",
                pea_label,
                "amber",
                t(
                    locale,
                    "verdicts.next_euro.step.pea.none",
                    gain=(
                        t(
                            locale,
                            "verdicts.next_euro.step.pea.none_gain",
                            base=_eur(cto_value + dca_year, locale),
                            gain=_eur(pea_gain, locale),
                        )
                        if pea_gain > 0
                        else ""
                    ),
                ),
                pea_gain if pea_gain > 0 else None,
            )
        )

    # 4. PER : only above the 30 % bracket
    per_ceiling = None
    per_gain = 0.0
    per_label = t(locale, "verdicts.next_euro.step.per.label")
    if tmi is None:
        steps.append(
            _step(
                "per",
                per_label,
                "unknown",
                t(locale, "verdicts.next_euro.step.per.unknown"),
            )
        )
    else:
        per_ceiling = min(
            cfg.per_ceiling_max_eur,
            max(cfg.per_ceiling_min_eur, cfg.per_ceiling_pct * (rfr or 0.0)),
        )
        if tmi >= cfg.per_tmi_min:
            per_base = min(per_ceiling, dca_year) if dca_year > 0 else per_ceiling
            per_gain = tmi * per_base
            steps.append(
                _step(
                    "per",
                    per_label,
                    "green" if has_per else "amber",
                    t(
                        locale,
                        "verdicts.next_euro.step.per.worth",
                        tmi=_pct(tmi, 0, locale),
                        ceiling=_eur(per_ceiling, locale),
                        gain=(
                            t(
                                locale,
                                "verdicts.next_euro.step.per.gain_on",
                                base=_eur(per_base, locale),
                                gain=_eur(per_gain, locale),
                            )
                            if has_per or dca_year > 0
                            else t(
                                locale,
                                "verdicts.next_euro.step.per.gain_ceiling",
                                gain=_eur(per_gain, locale),
                            )
                        ),
                        warning=(
                            "" if has_per else t(locale, "verdicts.next_euro.step.per.warning")
                        ),
                    ),
                    per_gain if not has_per else None,
                )
            )
        else:
            steps.append(
                _step(
                    "per",
                    per_label,
                    "green",
                    t(locale, "verdicts.next_euro.step.per.low", tmi=_pct(tmi, 0, locale)),
                )
            )

    # ── Destination and overall status ────────────────────────────────────
    if precaution_short:
        if lep_eligible and (by_type.get("lep") is None or (by_type["lep"].headroom_eur or 0) > 0):
            dest = t(
                locale,
                "verdicts.next_euro.dest.lep"
                if by_type.get("lep")
                else "verdicts.next_euro.dest.lep_open",
            )
        elif by_type.get("livret_a") is not None and (by_type["livret_a"].headroom_eur or 0) > 0:
            dest = t(locale, "verdicts.next_euro.dest.livret_a")
        elif by_type.get("ldds") is not None and (by_type["ldds"].headroom_eur or 0) > 0:
            dest = t(locale, "verdicts.next_euro.dest.ldds")
        else:
            dest = t(locale, "verdicts.next_euro.dest.livret")
        reason = t(
            locale,
            "verdicts.next_euro.reason.precaution",
            months=months_txt,
            target_months=target_months_txt,
        )
        driving = steps[0]
    elif not has_pea:
        dest = t(locale, "verdicts.next_euro.dest.pea_open")
        reason = t(locale, "verdicts.next_euro.reason.pea_open")
        driving = next(st for st in steps if st["id"] == "pea")
    else:
        dest = t(locale, "verdicts.next_euro.dest.pea")
        reason = t(
            locale,
            "verdicts.next_euro.reason.precaution_ok"
            if not precaution_short and monthly_spending
            else "verdicts.next_euro.reason.pea",
        )
        driving = next(st for st in steps if st["id"] == "pea")

    order = {"red": 3, "amber": 2, "unknown": 1, "green": 0}
    worst = max(steps, key=lambda st: order[st["status"]])
    status = worst["status"] if worst["status"] != "unknown" else "green"
    if all(st["status"] == "unknown" for st in steps):
        status = "unknown"

    headline = t(locale, "verdicts.next_euro.headline", dest=dest, reason=reason)
    actions = [st for st in steps if st["status"] in ("amber", "red") and st is not driving]
    action: str | None = None
    if driving["status"] in ("amber", "red"):
        action = {
            "precaution": t(
                locale,
                "verdicts.next_euro.action.precaution",
                dest=dest,
                target=_eur(target or 0, locale),
            ),
            "pea": t(locale, "verdicts.next_euro.action.pea_open"),
        }.get(driving["id"])
    elif actions:
        first = actions[0]
        action = {
            "lep": t(locale, "verdicts.next_euro.action.lep", movable=_eur(movable, locale)),
            "per": t(locale, "verdicts.next_euro.action.per"),
            "pea": t(locale, "verdicts.next_euro.action.pea_full"),
        }.get(first["id"])
    if not profile_complete:
        action = (action + " " if action else "") + t(locale, "verdicts.next_euro.action.profile")
    impact = (
        driving.get("impact_eur_per_year")
        if driving["status"] in ("amber", "red")
        else (actions[0].get("impact_eur_per_year") if actions else 0.0)
    )

    details = {
        "destination": dest,
        "steps": steps,
        "precaution": {
            "liquid_eur": liquid,
            "monthly_spending_eur": monthly_spending,
            "target_eur": target,
            "months_covered": months_covered,
            "target_months": cfg.precaution_months,
        },
        "tax": {"tmi": tmi, "rfr_eur": rfr, "fiscal_shares": shares},
        "per": {"has_per": has_per, "ceiling_eur": per_ceiling, "gain_eur_per_year": per_gain},
        "pea": {
            "has_pea": has_pea,
            "value_eur": pea_value,
            "ceiling_eur": cfg.pea_ceiling_eur,
            "gain_eur_per_year": pea_gain,
        },
        "lep": {
            "eligible": lep_eligible,
            "has_lep": by_type.get("lep") is not None,
            "gain_eur_per_year": lep_gain,
        },
        "cto_value_eur": cto_value,
        "profile_complete": profile_complete,
    }
    return Verdict(
        id="next_euro",
        title=title,
        status=status,
        headline=headline,
        impact_eur_per_year=impact,
        action=action,
        details=details,
    )


def merton_share(max_volatility: float, equity_sigma: float) -> float:
    """Equity share that puts a two-asset portfolio (cash + world equities) at
    `max_volatility`: the point of the capital market line the risk level picks.
    Equal to Merton's (μ − r) / (γ σ²) for the γ implied by that level."""
    return min(1.0, max(0.0, max_volatility / equity_sigma))


def risk_share_verdict(
    wealth: Wealth,
    profile: Profile,
    thresholds: RiskShareThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Part d'actions » : how much of the long-term pocket is in equities,
    against the share the profile's risk level puts on the market line,
    capped by the horizon (capacity for loss). Étude §5.2 principle 1, §8.1 point 3.

    Equities = accounts whose lines Tangent prices (ETF and stocks in PEA,
    CTO, AV units); the rest of the long-term pocket (fonds euros, PER or AV
    valued as a whole, PEL) counts as non-equity.
    """
    cfg = thresholds or config().risk_share
    title = t(locale, "verdicts.risk_share.title")

    equity = sum(acc.positions_value for acc in wealth.investment_accounts if acc.positions)
    non_equity = sum(acc.value for acc in wealth.investment_accounts if not acc.positions)
    non_equity += sum(
        e.balance for e in wealth.envelopes if e.envelope_type in ("pel", "cel", "cat")
    )
    pocket = equity + non_equity
    if pocket <= 0:
        return Verdict(
            id="risk_share",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.risk_share.headline.no_pocket"),
            action=t(locale, "verdicts.risk_share.action.no_pocket"),
        )

    level = profile.risk_level
    if level is None:
        return Verdict(
            id="risk_share",
            title=title,
            status="unknown",
            headline=t(
                locale,
                "verdicts.risk_share.headline.no_level",
                share=_pct(equity / pocket, 0, locale),
                pocket=_eur(pocket, locale),
            ),
            action=t(locale, "verdicts.risk_share.action.no_level"),
            details={"equity_eur": equity, "pocket_eur": pocket, "actual_share": equity / pocket},
        )

    rl = risk_profile.resolve(level)
    merton = merton_share(rl.max_annual_volatility, cfg.equity_sigma)
    horizon = profile.horizon_years if profile.horizon_years is not None else 10
    cap = next(
        (c.max_share for c in cfg.horizon_caps if c.max_years is None or horizon <= c.max_years),
        1.0,
    )
    target = min(merton, cap)
    actual = equity / pocket
    gap = actual - target
    gamma = cfg.equity_premium / (merton * cfg.equity_sigma**2) if merton > 0 else None
    # Expected drawdown of the equity pocket in a bad year (two sigmas), in euros.
    bad_year_eur = 2 * cfg.equity_sigma * equity

    details: dict[str, Any] = {
        "actual_share": actual,
        "target_share": target,
        "merton_share": merton,
        "horizon_cap": cap,
        "horizon_years": horizon,
        "risk_level": level,
        "risk_label": rl.label,
        "gamma": gamma,
        "equity_eur": equity,
        "non_equity_eur": non_equity,
        "pocket_eur": pocket,
        "bad_year_eur": bad_year_eur,
        "band": cfg.band,
        "equity_premium": cfg.equity_premium,
        "equity_sigma": cfg.equity_sigma,
    }
    # A century of realized returns, so « pourquoi prendre ce risque » has an answer.
    long_run = references.long_run_returns()
    if long_run:
        details["long_run"] = long_run
    base = t(
        locale,
        "verdicts.risk_share.base",
        share=_pct(actual, 0, locale),
        pocket=_eur(pocket, locale),
        label=rl.label_en if locale == "en" else rl.label,
        target=_pct(target, 0, locale),
    )
    if abs(gap) <= cfg.band:
        return Verdict(
            id="risk_share",
            title=title,
            status="green",
            headline=t(locale, "verdicts.risk_share.headline.green", base=base),
            impact_eur_per_year=0.0,
            details=details,
        )
    if gap < 0:
        missing_eur = -gap * pocket
        impact = cfg.equity_premium * missing_eur
        return Verdict(
            id="risk_share",
            title=title,
            status="red" if -gap >= cfg.red_gap else "amber",
            headline=t(
                locale,
                "verdicts.risk_share.headline.low",
                base=base,
                missing=_eur(missing_eur, locale),
                impact=_eur(impact, locale),
            ),
            impact_eur_per_year=impact,
            action=t(locale, "verdicts.risk_share.action.low", target=_pct(target, 0, locale)),
            details=details,
        )
    excess_eur = gap * pocket
    return Verdict(
        id="risk_share",
        title=title,
        status="red" if gap >= cfg.red_gap else "amber",
        headline=t(
            locale,
            "verdicts.risk_share.headline.high",
            base=base,
            excess=_eur(excess_eur, locale),
            bad_year=_eur(bad_year_eur, locale),
        ),
        impact_eur_per_year=None,
        action=t(locale, "verdicts.risk_share.action.high"),
        details=details,
    )


def future_value_of_monthly(monthly: float, annual_rate: float, years: int) -> float:
    """Capital reached by saving `monthly` every month for `years` at `annual_rate`."""
    r = (1 + annual_rate) ** (1 / 12) - 1
    n = years * 12
    if r == 0:
        return monthly * n
    return monthly * ((1 + r) ** n - 1) / r


def savings_rate_verdict(
    profile: Profile,
    monthly_saved: float | None,
    thresholds: SavingsRateThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Taux d'épargne » : what goes to savings each month against income.

    Income is the RFR N-2 spread over twelve months; saving is the monthly
    contribution declared in the profile, replaced by the credits seen on
    savings and investment accounts over 90 days when transactions exist.
    Étude §1.1: at 20 years, 58 % of the final capital is contributions.
    """
    cfg = thresholds or config().savings_rate
    title = t(locale, "verdicts.savings_rate.title")
    rfr = profile.rfr_n_minus_2
    dca = float(profile.monthly_dca or 0.0)

    if not rfr or rfr <= 0:
        return Verdict(
            id="savings_rate",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.savings_rate.headline.no_income"),
            action=t(locale, "verdicts.savings_rate.action.no_income"),
            details={"monthly_saved_observed_eur": monthly_saved, "monthly_dca_eur": dca},
        )
    income = rfr / 12.0
    # The observed figure wins when we have one: it is what actually happens.
    saved = monthly_saved if monthly_saved is not None else dca
    source = "observed" if monthly_saved is not None else "declared"
    rate = saved / income if income > 0 else 0.0
    target_eur = cfg.target * income
    missing = max(0.0, target_eur - saved)
    at_horizon_gap = future_value_of_monthly(missing, cfg.growth_for_20y, cfg.horizon_years)
    escalated_next_year = saved * (1 + cfg.escalation)

    details: dict[str, Any] = {
        "income_monthly_eur": income,
        "rfr_eur": rfr,
        "monthly_dca_eur": dca,
        "monthly_saved_observed_eur": monthly_saved,
        "monthly_saved_used_eur": saved,
        "source": source,
        "rate": rate,
        "target_rate": cfg.target,
        "target_monthly_eur": target_eur,
        "missing_monthly_eur": missing,
        "gap_at_horizon_eur": at_horizon_gap,
        "horizon_years": cfg.horizon_years,
        "growth_for_horizon": cfg.growth_for_20y,
        "escalation": cfg.escalation,
        "escalated_next_year_eur": escalated_next_year,
        "amber_min": cfg.amber_min,
    }
    how = t(
        locale,
        "verdicts.savings_rate.how.observed"
        if source == "observed"
        else "verdicts.savings_rate.how.declared",
    )
    base = t(
        locale,
        "verdicts.savings_rate.base",
        saved=_eur(saved, locale),
        rate=_pct(rate, 0, locale),
        how=how,
    )

    if rate >= cfg.target:
        return Verdict(
            id="savings_rate",
            title=title,
            status="green",
            headline=t(
                locale,
                "verdicts.savings_rate.headline.green",
                base=base,
                target=_pct(cfg.target, 0, locale),
            ),
            impact_eur_per_year=0.0,
            action=t(
                locale,
                "verdicts.savings_rate.action.green",
                escalation=_pct(cfg.escalation, 0, locale),
                next_year=_eur(escalated_next_year, locale),
            ),
            details=details,
        )
    status = "amber" if rate >= cfg.amber_min else "red"
    return Verdict(
        id="savings_rate",
        title=title,
        status=status,
        headline=t(
            locale,
            "verdicts.savings_rate.headline.below",
            base=base,
            target=_pct(cfg.target, 0, locale),
            target_eur=_eur(target_eur, locale),
            gap=_eur(at_horizon_gap, locale),
            years=cfg.horizon_years,
        ),
        impact_eur_per_year=missing * 12.0,
        action=t(
            locale,
            "verdicts.savings_rate.action.below",
            missing=_eur(missing, locale),
            escalation=_pct(cfg.escalation, 0, locale),
            target_eur=_eur(target_eur, locale),
        ),
        details=details,
    )


def goal_paths(
    initial: float,
    monthly: float,
    months: int,
    mu_annual: float,
    sigma_annual: float,
    shocks: np.ndarray,
) -> np.ndarray:
    """Terminal values of `shocks.shape[0]` paths: lognormal monthly returns
    with arithmetic mean (1 + μ)^(1/12), a contribution at the end of each month.
    `shocks` is a (n_paths, months) matrix of standard normals, shared between
    calls so the required contribution is found on the same draws."""
    sigma_m = sigma_annual / np.sqrt(12.0)
    drift_m = np.log1p(mu_annual) / 12.0 - sigma_m**2 / 2.0
    value = np.full(shocks.shape[0], float(initial))
    for month in range(months):
        value = value * np.exp(drift_m + sigma_m * shocks[:, month]) + monthly
    return value


def required_monthly_for(
    goal: float,
    initial: float,
    months: int,
    mu_annual: float,
    sigma_annual: float,
    shocks: np.ndarray,
    target_probability: float,
) -> float:
    """Smallest monthly contribution whose success probability reaches the
    target, by bisection on common random numbers (the probability is
    monotone in the contribution on a fixed set of draws)."""

    def prob(m: float) -> float:
        return float(
            np.mean(goal_paths(initial, m, months, mu_annual, sigma_annual, shocks) >= goal)
        )

    lo, hi = 0.0, 100.0
    if prob(lo) >= target_probability:
        return 0.0
    while prob(hi) < target_probability and hi < 1e6:
        hi *= 2
    for _ in range(20):
        mid = (lo + hi) / 2
        if prob(mid) >= target_probability:
            hi = mid
        else:
            lo = mid
    return hi


def goal_verdict(
    wealth: Wealth,
    profile: Profile,
    monthly_saved: float | None,
    thresholds: GoalThresholds | None = None,
    risk_thresholds: RiskShareThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Combien épargner pour ton objectif » : the inverse problem of the
    projection (étude §7.1, §8.1 point 7). The goal is in today's euros, so
    the simulation runs on real returns; the expected return follows the
    equity share the profile targets (same market line as `risk_share`).
    The answer is not a probability but the monthly saving that brings the
    goal to the target probability."""
    cfg = thresholds or config().goal
    rcfg = risk_thresholds or config().risk_share
    inflation = macro.inflation()
    title = t(locale, "verdicts.goal.title")
    goal = profile.goal_amount
    if not goal or goal <= 0:
        return Verdict(
            id="goal",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.goal.headline.none"),
            action=t(locale, "verdicts.goal.action.none"),
        )
    years = profile.horizon_years if profile.horizon_years else 10
    months = int(years * 12)
    monthly = monthly_saved if monthly_saved is not None else float(profile.monthly_dca or 0.0)
    initial = wealth.investments_total + wealth.pea_cash_total

    level = profile.risk_level
    if level is not None:
        share = merton_share(risk_profile.resolve(level).max_annual_volatility, rcfg.equity_sigma)
    else:
        share = 0.5
    mu_nominal = macro.risk_free_rate() + share * rcfg.equity_premium
    mu_real = mu_nominal - inflation
    sigma = share * rcfg.equity_sigma

    rng = np.random.default_rng(cfg.seed)
    shocks = rng.standard_normal((cfg.n_paths, months))
    terminal = goal_paths(initial, monthly, months, mu_real, sigma, shocks)
    probability = float(np.mean(terminal >= goal))
    p10, p50, p90 = (float(x) for x in np.percentile(terminal, [10, 50, 90]))
    required = required_monthly_for(
        goal, initial, months, mu_real, sigma, shocks, cfg.target_probability
    )
    extra = max(0.0, required - monthly)

    details: dict[str, Any] = {
        "goal_eur": goal,
        "horizon_years": years,
        "initial_eur": initial,
        "monthly_used_eur": monthly,
        "monthly_source": "observed" if monthly_saved is not None else "declared",
        "probability": probability,
        "target_probability": cfg.target_probability,
        "amber_probability": cfg.amber_probability,
        "required_monthly_eur": required,
        "extra_monthly_eur": extra,
        "p10_eur": p10,
        "p50_eur": p50,
        "p90_eur": p90,
        "equity_share": share,
        "mu_nominal": mu_nominal,
        "mu_real": mu_real,
        "sigma": sigma,
        "inflation": inflation,
        "n_paths": cfg.n_paths,
    }
    chances = t(locale, "verdicts.goal.chances", n=f"{round(probability * 10):.0f}")
    base = t(
        locale,
        "verdicts.goal.base",
        monthly=_eur(monthly, locale),
        chances=chances,
        goal=_eur(goal, locale),
        years=years,
    )
    if probability >= cfg.target_probability:
        return Verdict(
            id="goal",
            title=title,
            status="green",
            headline=t(locale, "verdicts.goal.headline.green", base=base),
            impact_eur_per_year=0.0,
            action=(
                t(locale, "verdicts.goal.action.green", required=_eur(required, locale))
                if required < monthly
                else None
            ),
            details=details,
        )
    return Verdict(
        id="goal",
        title=title,
        status="amber" if probability >= cfg.amber_probability else "red",
        headline=t(
            locale, "verdicts.goal.headline.below", base=base, required=_eur(required, locale)
        ),
        impact_eur_per_year=None,
        action=t(locale, "verdicts.goal.action.below", extra=_eur(extra, locale)),
        details=details,
    )


def _signed_pct(fraction: float, locale: Locale = "fr") -> str:
    """0.031 → « +3,10 % » : a return without its sign reads as a promise."""
    return ("+" if fraction >= 0 else "−") + _pct(abs(fraction), locale=locale)


def performance_verdict(
    perf: performance.Performance | None,
    thresholds: PerformanceThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Ce que tes placements ont vraiment fait » : TWR against TRI (étude §7.7).

    TWR judges the allocation, TRI judges the saver's own result; the gap
    between them is what the timing of the contributions cost or won. Both
    are read off the snapshot series, which is the only real history: the
    curve on Placements applies today's weights to the past and is a
    backtest, not this account's past.
    """
    cfg = thresholds or config().performance
    title = t(locale, "verdicts.performance.title")
    if perf is None or perf.days < cfg.min_days:
        started = perf.start.strftime("%d/%m/%Y") if perf else None
        missing = cfg.min_days - perf.days if perf else cfg.min_days
        return Verdict(
            id="performance",
            title=title,
            status="unknown",
            headline=(
                t(locale, "verdicts.performance.headline.young", started=started, missing=missing)
                if started
                else t(locale, "verdicts.performance.headline.today")
            ),
            details={
                "days": perf.days if perf else 0,
                "min_days": cfg.min_days,
                "start": started,
            },
        )

    details: dict[str, Any] = {
        "start": perf.start.isoformat(),
        "end": perf.end.isoformat(),
        "days": perf.days,
        "twr": perf.twr,
        "twr_annualized": perf.twr_annualized,
        "irr": perf.irr,
        "behaviour_gap": perf.behaviour_gap,
        "net_flows_eur": perf.net_flows,
        "first_value_eur": perf.first_value,
        "last_value_eur": perf.last_value,
        "max_drawdown": perf.max_drawdown,
        "index": perf.index,
    }
    since = perf.start.strftime("%d/%m/%Y")
    twr_txt = _signed_pct(perf.twr, locale) if perf.twr is not None else "—"
    if perf.irr is None or perf.behaviour_gap is None or perf.twr_annualized is None:
        return Verdict(
            id="performance",
            title=title,
            status="green",
            headline=t(locale, "verdicts.performance.headline.twr_only", since=since, twr=twr_txt),
            impact_eur_per_year=0.0,
            details=details,
        )

    strategy = t(
        locale, "verdicts.performance.strategy", twr=_signed_pct(perf.twr_annualized, locale)
    )
    yours = t(locale, "verdicts.performance.yours", irr=_signed_pct(perf.irr, locale))
    if perf.behaviour_gap >= cfg.gap_amber:
        return Verdict(
            id="performance",
            title=title,
            status="green",
            headline=t(
                locale,
                "verdicts.performance.headline.green",
                since=since,
                strategy=strategy,
                yours=yours,
            ),
            impact_eur_per_year=0.0,
            details=details,
        )
    cost = abs(perf.behaviour_gap) * perf.last_value
    return Verdict(
        id="performance",
        title=title,
        status="amber",
        headline=t(
            locale,
            "verdicts.performance.headline.amber",
            since=since,
            strategy=strategy,
            yours=yours,
            gap=_pct(abs(perf.behaviour_gap), locale=locale),
            cost=_eur(cost, locale),
        ),
        impact_eur_per_year=cost,
        action=t(locale, "verdicts.performance.action.amber"),
        details=details,
    )


def drawdown_verdict(
    perf: performance.Performance | None,
    thresholds: DrawdownThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Où tu en es par rapport à ton plus haut » (MiFID II art. 62).

    A discretionary manager owes the client a notice the same day the
    portfolio falls 10 % below the start of the period, then at every
    further 10 %. The rule is a better alert than a daily commentary: it
    fires on the drop that makes people sell, and says not to.
    """
    cfg = thresholds or config().drawdown
    title = t(locale, "verdicts.drawdown.title")
    if perf is None or not perf.index:
        return Verdict(
            id="drawdown",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.drawdown.headline.no_history"),
        )
    dd = perf.drawdown
    peak_day = perf.peak_day.strftime("%d/%m/%Y") if perf.peak_day else "?"
    # Euros missing against the peak, at today's size of the pocket.
    missing = perf.last_value * (-dd / (1 + dd)) if dd < 0 and dd > -1 else 0.0
    # +1e-9: a drawdown of exactly one step must count as crossed.
    steps = int((abs(dd) + 1e-9) / cfg.alert_step)
    details: dict[str, Any] = {
        "drawdown": dd,
        "max_drawdown": perf.max_drawdown,
        "peak_day": perf.peak_day.isoformat() if perf.peak_day else None,
        "missing_eur": missing,
        "alert_step": cfg.alert_step,
        "red_at": cfg.red_at,
        "steps_crossed": steps,
        "last_value_eur": perf.last_value,
    }
    # 150 years of context, so « −12 % » can be placed on a scale.
    worst = references.worst_year_since_1871()
    if worst:
        details["worst_year_ever"] = {
            "return": worst[0],
            "from_year": worst[1],
            "to_year": worst[2],
        }
    if steps == 0:
        return Verdict(
            id="drawdown",
            title=title,
            status="green",
            headline=(
                t(
                    locale,
                    "verdicts.drawdown.headline.near_peak",
                    dd=_pct(abs(dd), locale=locale),
                    peak_day=peak_day,
                )
                if dd < 0
                else t(locale, "verdicts.drawdown.headline.at_peak", peak_day=peak_day)
            ),
            impact_eur_per_year=0.0,
            details=details,
        )
    return Verdict(
        id="drawdown",
        title=title,
        status="red" if abs(dd) >= cfg.red_at else "amber",
        headline=t(
            locale,
            "verdicts.drawdown.headline.down",
            dd=_pct(abs(dd), locale=locale),
            peak_day=peak_day,
            missing=_eur(missing, locale),
        ),
        action=t(locale, "verdicts.drawdown.action.down"),
        details=details,
    )


def diversification_verdict(
    wealth: Wealth,
    thresholds: DiversificationThresholds | None = None,
    locale: Locale = "fr",
) -> Verdict:
    """« Répartition » : several lines on one index, and lines that are a bet on one thing.

    Both questions used to be answered by statistics on the Placements screen —
    a correlation above 0.85 for duplicates, a weight above 40 % for
    concentration. Two trackers of the same index are not correlated, they are
    identical; and a single broad world fund at 100 % is the textbook advice,
    not a risk. Both are now read off what each line *is* (ADR-025).
    """
    cfg = thresholds or config().diversification
    title = t(locale, "verdicts.diversification.title")

    lines = [p for acc in wealth.investment_accounts for p in acc.positions if p.current_value > 0]
    total = sum(p.current_value for p in lines)
    if total <= 0:
        return Verdict(
            id="diversification",
            title=title,
            status="unknown",
            headline=t(locale, "verdicts.diversification.headline.no_lines"),
        )

    classes = classification.classify_many([(p.label, p.isin) for p in lines])
    problems: list[str] = []
    details: dict[str, Any] = {
        "positions_total_eur": total,
        "single_line_max": cfg.single_line_max,
        "lines": [
            {
                "label": p.label,
                "value_eur": p.current_value,
                "weight": p.current_value / total,
                "index_label": what.index_label,
                "asset_class": what.asset_class,
                "diversified": what.is_diversified,
            }
            for p, what in zip(lines, classes, strict=True)
        ],
    }

    # Several lines tracking one index: one group, not one card per pair.
    groups: dict[str, list[int]] = {}
    for i, what in enumerate(classes):
        if what.index_label:
            groups.setdefault(what.index_label, []).append(i)
    duplicates: list[dict[str, Any]] = []
    for index_label, members in groups.items():
        if len(members) < 2:
            continue
        names = [lines[i].label for i in members]
        weight = sum(lines[i].current_value for i in members) / total
        duplicates.append({"index_label": index_label, "labels": names, "weight": weight})
        problems.append(
            t(
                locale,
                "verdicts.diversification.duplicates",
                names=_join(names, locale),
                index=index_label,
            )
        )
    details["duplicates"] = duplicates

    # A heavy line only matters when it is not itself diversified.
    concentrated: list[dict[str, Any]] = []
    for position, what in zip(lines, classes, strict=True):
        weight = position.current_value / total
        if weight <= cfg.single_line_max or what.is_diversified:
            continue
        if what.kind == classification.STOCK:
            why = t(locale, "verdicts.diversification.why.stock")
        elif what.index_label:
            why = t(locale, "verdicts.diversification.why.segment", index=what.index_label)
        else:
            why = t(locale, "verdicts.diversification.why.unknown")
        concentrated.append(
            {
                "label": position.label,
                "weight": weight,
                "index_label": what.index_label,
                "kind": what.kind,
            }
        )
        problems.append(
            t(
                locale,
                "verdicts.diversification.concentrated",
                label=position.label,
                weight=_pct(weight, digits=0, locale=locale),
                why=why,
            )
        )
    details["concentrated"] = concentrated

    unknown = [lines[i].label for i, what in enumerate(classes) if not what.is_known]
    details["unrecognised"] = unknown

    if not problems:
        return Verdict(
            id="diversification",
            title=title,
            status="green",
            headline=t(locale, "verdicts.diversification.headline.green"),
            details=details,
        )

    return Verdict(
        id="diversification",
        title=title,
        status="amber",
        headline=problems[0],
        action=t(locale, "verdicts.diversification.action.amber"),
        details=details,
    )


def compute_all(
    wealth: Wealth,
    profile: Profile,
    monthly_spending: float | None = None,
    monthly_saved: float | None = None,
    perf: performance.Performance | None = None,
    locale: Locale = "fr",
) -> VerdictsResponse:
    """Every verdict the method can give on this patrimony, in display order.

    `monthly_spending` is the average monthly debit on current accounts,
    `monthly_saved` the average monthly credit on savings and investment
    accounts (repositories.bank_transactions); None when unknown. Every
    sentence is written in `locale`.
    """
    try:
        _, broker_fees = fees.get(profile.default_broker)
    except UnknownBrokerError:
        logger.warning("verdicts: unknown broker %r, using default", profile.default_broker)
        _, broker_fees = fees.get(None)
    monthly = float(profile.monthly_dca or 0.0)
    verdicts = _by_priority(
        [
            drawdown_verdict(perf, locale=locale),
            savings_rate_verdict(profile, monthly_saved, locale=locale),
            goal_verdict(wealth, profile, monthly_saved, locale=locale),
            next_euro_verdict(wealth, profile, monthly_spending, locale=locale),
            risk_share_verdict(wealth, profile, locale=locale),
            diversification_verdict(wealth, locale=locale),
            fees_verdict(wealth, broker_fees, monthly, locale=locale),
            performance_verdict(perf, locale=locale),
        ]
    )
    logger.info("verdicts computed: %s", {v.id: v.status for v in verdicts})
    return VerdictsResponse(computed_at=datetime.now(tz=UTC), verdicts=verdicts)
