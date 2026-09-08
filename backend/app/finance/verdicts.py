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

import yaml
from pydantic import BaseModel, Field

from ..db.models import Profile
from ..errors import ConfigurationError, UnknownBrokerError
from ..models import Verdict, VerdictsResponse, Wealth
from . import envelopes, fees, risk_profile

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


class VerdictsConfig(BaseModel):
    fees: FeesThresholds
    next_euro: NextEuroThresholds
    risk_share: RiskShareThresholds


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


def _eur(value: float) -> str:
    """1234.5 → « 1 235 € » (narrow no-break space as thousands separator)."""
    return f"{value:,.0f} €".replace(",", " ")


def _pct(fraction: float, digits: int = 2) -> str:
    """0.0092 → « 0,92 % » ; with digits=0, 0.30 → « 30 % »."""
    return f"{fraction * 100:.{digits}f} %".replace(".", ",")


def fees_verdict(
    wealth: Wealth,
    broker_fees: fees.BrokerFees,
    monthly_contribution: float,
    thresholds: FeesThresholds | None = None,
) -> Verdict:
    """« Frais réels » : what the user's lines cost per year, all layers summed.

    Fund fees = Σ current_value × TER (TER entered by the user or resolved,
    per line). Broker fees = custody on the lines' value + fixed fee per line
    + courtage on twelve monthly contributions. Prices are already net of
    fund fees, so nothing here feeds the projection: this is a cost of
    holding, shown once a year in euros.
    """
    cfg = thresholds or config().fees

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
                    "fund_fee_eur": p.current_value * p.ter if p.ter is not None else None,
                }
            )

    positions_total = sum(line["value_eur"] for line in lines)
    if positions_total <= 0:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="unknown",
            headline=(
                "Aucune ligne de placement connue : connecte un PEA, un compte-titres "
                "ou une assurance vie pour mesurer ce que tes placements te coûtent."
            ),
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
            title="Frais réels",
            status="unknown",
            headline=(
                f"Il manque les frais annuels (TER) de {n} ligne{'s' if n > 1 else ''}, "
                f"soit {_pct(1 - coverage)} de tes placements : impossible de mesurer "
                "ce qu'ils te coûtent."
            ),
            action="Renseigne le TER de ces lignes dans Comptes (ouvre le compte, puis la ligne).",
            details=details,
        )

    at_least = "au moins " if missing else ""
    base = f"Tes placements te coûtent {at_least}{_pct(total_pct)} par an, soit {_eur(total)}"
    complete = (
        f" Renseigne le TER manquant sur {len(missing)} ligne{'s' if len(missing) > 1 else ''} "
        "pour affiner."
        if missing
        else ""
    )

    if total_pct <= cfg.green_max:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="green",
            headline=base + " : c'est bas, rien à changer.",
            impact_eur_per_year=0.0,
            action=complete.strip() or None,
            details=details,
        )
    if total_pct <= cfg.amber_max:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="amber",
            headline=(
                base + f" : la même somme en PEA en ligne avec un ETF monde coûterait "
                f"{_eur(reference_eur)}."
            ),
            impact_eur_per_year=saving,
            action=(
                f"Compare ton courtier et tes fonds : {_eur(saving)} par an d'écart avec la "
                "référence." + complete
            ),
            details=details,
        )
    return Verdict(
        id="fees",
        title="Frais réels",
        status="red",
        headline=(
            base + f", soit {_eur(saving)} de plus par an qu'un PEA en ligne avec un ETF monde."
        ),
        impact_eur_per_year=saving,
        action=(
            "Change de courtier ou remplace les fonds les plus chers par un ETF indiciel : "
            f"c'est {_eur(saving)} par an à récupérer." + complete
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
) -> Verdict:
    """« Où placer le prochain euro » : the envelope sequencing rule (étude §8.1).

    Précaution (3 months of spending in Livret A / LDDS / LEP) → long term in
    a PEA → PER only above the 30 % bracket → CTO for the rest. Each step is
    scored; the first one not satisfied decides the destination, the others
    stay visible as opportunities (LEP, PER) in the details.
    """
    cfg = thresholds or config().next_euro
    title = "Où placer le prochain euro"
    envs = envelopes.config().envelopes

    if not wealth.envelopes and not wealth.investment_accounts and not wealth.checking_accounts:
        return Verdict(
            id="next_euro",
            title=title,
            status="unknown",
            headline="Aucun compte connecté : impossible de dire où ton prochain euro sera le mieux placé.",
            action="Connecte ta banque dans Comptes.",
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
    if monthly_spending is None:
        steps.append(
            _step(
                "precaution",
                "Épargne de précaution",
                "unknown",
                f"{_eur(liquid)} sur tes livrets ; tes dépenses mensuelles ne sont pas encore "
                "connues (aucun débit synchronisé sur 90 jours), la cible de 3 mois ne peut "
                "pas être calculée.",
            )
        )
    elif precaution_short:
        assert months_covered is not None and target is not None
        steps.append(
            _step(
                "precaution",
                "Épargne de précaution",
                "red" if months_covered < cfg.precaution_min_months else "amber",
                f"{_eur(liquid)} sur tes livrets, soit {months_covered:.1f} mois de dépenses ; "
                f"la cible est {cfg.precaution_months:g} mois, {_eur(target)}.",
            )
        )
    else:
        assert months_covered is not None and target is not None
        steps.append(
            _step(
                "precaution",
                "Épargne de précaution",
                "green",
                f"{_eur(liquid)} sur tes livrets, {months_covered:.1f} mois de dépenses : "
                f"la cible de {cfg.precaution_months:g} mois ({_eur(target)}) est couverte.",
            )
        )

    # 2. LEP : best net rate, only if eligible
    lep = envs.get("lep")
    livret_a = envs.get("livret_a")
    lep_gain = 0.0
    movable = 0.0
    if lep is not None and livret_a is not None:
        if lep_eligible is None:
            steps.append(
                _step(
                    "lep",
                    "LEP",
                    "unknown",
                    "Éligibilité au LEP inconnue : renseigne ton âge, ton foyer et ton revenu fiscal dans Profil.",
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
                        "LEP",
                        "amber",
                        f"Tu as droit au LEP ({_pct(lep.rate_pct)} net) : {_eur(movable)} de tes livrets "
                        f"peuvent y aller, {_eur(lep_gain)} de plus par an"
                        + ("" if lep_acc else ", il faut l'ouvrir dans ta banque")
                        + ".",
                        lep_gain,
                    )
                )
            else:
                steps.append(
                    _step(
                        "lep",
                        "LEP",
                        "green",
                        "Ton LEP est au plafond ou tes livrets sont vides : rien à déplacer.",
                    )
                )
        else:
            steps.append(
                _step(
                    "lep",
                    "LEP",
                    "green",
                    "Pas éligible au LEP (revenu fiscal au-dessus du plafond).",
                )
            )

    # 3. Long terme : PEA
    pea_gain = 0.0
    if has_pea:
        room = max(0.0, cfg.pea_ceiling_eur - pea_value)
        steps.append(
            _step(
                "pea",
                "PEA",
                "green" if room > 0 else "amber",
                f"Ton PEA vaut {_eur(pea_value)} ; il reste {_eur(room)} avant le plafond de versements."
                if room > 0
                else "Ton PEA est au plafond de versements : le long terme continue en assurance vie ou en CTO.",
            )
        )
    else:
        pea_gain = cfg.pea_vs_cto_pct * (cto_value + dca_year)
        steps.append(
            _step(
                "pea",
                "PEA",
                "amber",
                "Pas de PEA : c'est l'enveloppe la moins taxée pour des actions à long terme "
                "(17,2 % au lieu de 30 % après 5 ans), et son horloge de 5 ans ne démarre qu'à l'ouverture."
                + (
                    f" Sur {_eur(cto_value + dca_year)} de CTO et de versements, environ {_eur(pea_gain)} par an."
                    if pea_gain > 0
                    else ""
                ),
                pea_gain if pea_gain > 0 else None,
            )
        )

    # 4. PER : only above the 30 % bracket
    per_ceiling = None
    per_gain = 0.0
    if tmi is None:
        steps.append(
            _step(
                "per",
                "PER",
                "unknown",
                "Tranche d'imposition inconnue : renseigne ton revenu fiscal et ton foyer dans Profil.",
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
                    "PER",
                    "green" if has_per else "amber",
                    f"Tu es dans la tranche à {_pct(tmi, 0)} : chaque euro versé sur un PER te rend "
                    f"{_pct(tmi, 0)} d'impôt, jusqu'à {_eur(per_ceiling)} par an. "
                    + (
                        f"Sur {_eur(per_base)} de versements, {_eur(per_gain)} d'impôt en moins."
                        if has_per or dca_year > 0
                        else f"Soit {_eur(per_gain)} d'impôt en moins au plafond."
                    )
                    + (
                        " Attention : bloqué jusqu'à la retraite, et seulement avec des frais de contrat sous 0,6 %."
                        if not has_per
                        else ""
                    ),
                    per_gain if not has_per else None,
                )
            )
        else:
            steps.append(
                _step(
                    "per",
                    "PER",
                    "green",
                    f"Tu es dans la tranche à {_pct(tmi, 0)} : un PER déductible n'est pas intéressant en dessous de 30 %, garde la liquidité du PEA.",
                )
            )

    # ── Destination and overall status ────────────────────────────────────
    if precaution_short:
        if lep_eligible and (by_type.get("lep") is None or (by_type["lep"].headroom_eur or 0) > 0):
            dest = "ton LEP" if by_type.get("lep") else "un LEP à ouvrir"
        elif by_type.get("livret_a") is not None and (by_type["livret_a"].headroom_eur or 0) > 0:
            dest = "ton Livret A"
        elif by_type.get("ldds") is not None and (by_type["ldds"].headroom_eur or 0) > 0:
            dest = "ton LDDS"
        else:
            dest = "un livret (Livret A ou LDDS)"
        reason = f"ton épargne de précaution couvre {months_covered:.1f} mois de dépenses, la cible est {cfg.precaution_months:g}"
        driving = steps[0]
    elif not has_pea:
        dest = "un PEA à ouvrir"
        reason = "c'est l'enveloppe la moins taxée pour le long terme et son horloge de 5 ans ne tourne pas encore"
        driving = next(st for st in steps if st["id"] == "pea")
    else:
        dest = "ton PEA"
        reason = (
            "ta précaution est en place"
            if not precaution_short and monthly_spending
            else "le long terme passe par le PEA"
        )
        driving = next(st for st in steps if st["id"] == "pea")

    order = {"red": 3, "amber": 2, "unknown": 1, "green": 0}
    worst = max(steps, key=lambda st: order[st["status"]])
    status = worst["status"] if worst["status"] != "unknown" else "green"
    if all(st["status"] == "unknown" for st in steps):
        status = "unknown"

    headline = f"Ton prochain euro va dans {dest} : {reason}."
    actions = [st for st in steps if st["status"] in ("amber", "red") and st is not driving]
    action: str | None = None
    if driving["status"] in ("amber", "red"):
        action = {
            "precaution": f"Mets tes prochains versements sur {dest} jusqu'à {_eur(target or 0)}.",
            "pea": "Ouvre un PEA chez un courtier en ligne, même avec 10 €, pour lancer les 5 ans.",
        }.get(driving["id"])
    elif actions:
        first = actions[0]
        action = {
            "lep": f"Ouvre un LEP dans ta banque et bascules-y {_eur(movable)} de tes livrets.",
            "per": "Étudie un PER en ligne à frais bas (contrat sous 0,6 %) pour la part de ton épargne que tu peux bloquer jusqu'à la retraite.",
            "pea": "Ton PEA est plein : oriente le long terme vers une assurance vie en ligne ou un CTO.",
        }.get(first["id"])
    if not profile_complete:
        action = (
            action + " " if action else ""
        ) + "Renseigne ton profil (âge, foyer, revenu fiscal) pour évaluer le LEP et le PER."
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
) -> Verdict:
    """« Part d'actions » : how much of the long-term pocket is in equities,
    against the share the profile's risk level puts on the market line,
    capped by the horizon (capacity for loss). Étude §5.2 principle 1, §8.1 point 3.

    Equities = accounts whose lines Tangent prices (ETF and stocks in PEA,
    CTO, AV units); the rest of the long-term pocket (fonds euros, PER or AV
    valued as a whole, PEL) counts as non-equity.
    """
    cfg = thresholds or config().risk_share
    title = "Part d'actions"

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
            headline=(
                "Pas de poche long terme connue (PEA, compte-titres, assurance vie, PER) : "
                "la part d'actions ne peut pas être mesurée."
            ),
            action="Connecte tes comptes d'investissement dans Comptes.",
        )

    level = profile.risk_level
    if level is None:
        return Verdict(
            id="risk_share",
            title=title,
            status="unknown",
            headline=(
                f"Tu as {_pct(equity / pocket, 0)} d'actions sur {_eur(pocket)} de placements long "
                "terme, mais ton curseur prudent ↔ dynamique n'est pas réglé."
            ),
            action="Règle ton curseur dans Profil pour connaître la part qui te correspond.",
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
    base = (
        f"Tu as {_pct(actual, 0)} d'actions sur {_eur(pocket)} de placements long terme ; "
        f"ton profil « {rl.label} » vise {_pct(target, 0)}"
    )
    if abs(gap) <= cfg.band:
        return Verdict(
            id="risk_share",
            title=title,
            status="green",
            headline=base + " : tu es dans la bande, rien à changer.",
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
            headline=(
                base + f" : {_eur(missing_eur)} de trop en produits de taux, soit environ "
                f"{_eur(impact)} de rendement en moins par an."
            ),
            impact_eur_per_year=impact,
            action=(
                f"Oriente tes prochains versements vers ton ETF monde jusqu'à {_pct(target, 0)} "
                "d'actions ; pas besoin de vendre quoi que ce soit."
            ),
            details=details,
        )
    excess_eur = gap * pocket
    return Verdict(
        id="risk_share",
        title=title,
        status="red" if gap >= cfg.red_gap else "amber",
        headline=(
            base + f" : {_eur(excess_eur)} d'actions au-delà de ton profil. Une mauvaise année "
            f"peut te coûter {_eur(bad_year_eur)} sur cette poche."
        ),
        impact_eur_per_year=None,
        action=(
            "Dirige tes prochains versements vers le fonds euros ou un livret plutôt que vers "
            "les actions, ou monte ton curseur si tu assumes ces variations."
        ),
        details=details,
    )


def compute_all(
    wealth: Wealth, profile: Profile, monthly_spending: float | None = None
) -> VerdictsResponse:
    """Every verdict the method can give on this patrimony, in display order.

    `monthly_spending` is the average monthly debit on current accounts
    (repositories.bank_transactions.monthly_outflow); None when unknown.
    """
    try:
        _, broker_fees = fees.get(profile.default_broker)
    except UnknownBrokerError:
        logger.warning("verdicts: unknown broker %r, using default", profile.default_broker)
        _, broker_fees = fees.get(None)
    monthly = float(profile.monthly_dca or 0.0)
    verdicts = [
        next_euro_verdict(wealth, profile, monthly_spending),
        risk_share_verdict(wealth, profile),
        fees_verdict(wealth, broker_fees, monthly),
    ]
    logger.info("verdicts computed: %s", {v.id: v.status for v in verdicts})
    return VerdictsResponse(computed_at=datetime.now(tz=UTC), verdicts=verdicts)
