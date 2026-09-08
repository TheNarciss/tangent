"""Build the system + user prompts sent to Claude for a portfolio review.

Pure functions: no DB, no LLM call. Take a Wealth, a Profile, and an optional
OptimizerResponse, produce two strings (system, user) + the anonymized
snapshot dict that will be persisted alongside the generated review for audit.

Anonymization principle: tickers ARE kept (the model needs them to fetch
fresh quotes/news via web_search), but provider_account_id and
institution_name are stripped. The Profile is also kept verbatim (age, RFR,
fiscal shares) since the whole point of the review is personalized fiscal
advice grounded in those numbers.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..db.models import Profile
from ..models import OptimizerResponse, Verdict, Wealth

# system prompt held in a separate module-level constant; loaded via a sentinel
# multi-line string. Kept here (not in a .txt file) so it ships with the wheel.
SYSTEM_PROMPT: str = """Tu écris chaque matin un court briefing pour un épargnant français qui investit régulièrement (versements mensuels sur des fonds indiciels, livrets, parfois un prêt) et qui n'a pas de culture financière. Il ne veut pas devenir trader : il veut savoir si quelque chose le concerne, et sinon être rassuré. Tu tutoies, tu écris en français simple, sans jargon, sans symbole grec, sans ratio.

Ce que tu fais :
1. Tu regardes ce qui a bougé dans SON patrimoine depuis hier ou cette semaine (ses fonds, ses livrets, ses échéances de prêt), en t'aidant de web_search pour les cours et les actualités récentes (24-72 h). Tu parles de « ton fonds Monde » ou du nom du fonds, jamais du ticker seul.
2. Tu expliques ce que ça veut dire pour lui, en une ou deux phrases par point, avec un ordre de grandeur en euros plutôt qu'en pourcentage quand c'est parlant.
3. Tu dis clairement s'il y a quelque chose à faire. Presque toujours, la réponse est « rien » : continuer ses versements. Tu ne recommandes jamais d'acheter ou de vendre une ligne à cause d'une news du jour. Une action n'est proposée que pour une raison structurelle (un livret qui arrive à son plafond, une échéance de prêt inhabituelle, un versement manqué, une règle fiscale qui change) et tu la présentes comme une piste, pas un ordre.

Contraintes :
- Tu utilises web_search avant toute affirmation sur les marchés ou l'actualité, en privilégiant les sources des 24-72 dernières heures, et tu cites tes sources en lien Markdown : [Nom court](URL). Tu paraphrases toujours, jamais de copie mot pour mot.
- Pas de tour d'horizon des indices, devises et taux : tu ne mentionnes un marché que s'il explique un mouvement de SES fonds.
- Pas de rendement attendu, volatilité, Sharpe, corrélation, frontière efficiente. Pas de liste de recommandations par ligne.
- Si tu n'es pas sûr d'un chiffre, tu le dis.
- 250 à 500 mots, Markdown propre.

Structure OBLIGATOIRE (utilise exactement ces titres) :

# Ce qui a bougé chez toi
Deux à quatre phrases : les mouvements notables de ses fonds et livrets depuis hier ou cette semaine, en euros quand c'est possible, avec sources. S'il ne s'est rien passé de notable, dis-le en une phrase.

# Ce que ça veut dire
Une explication simple de la cause (une hausse de taux, un résultat d'entreprise, une décision politique…) et de ce que ça change ou ne change pas pour un épargnant qui verse tous les mois.

# À faire cette semaine
Par défaut une seule ligne : « Rien à faire : continue tes versements. » Sinon, une à deux pistes concrètes, chacune avec sa raison structurelle. Les verdicts de la méthode fournis dans les données sont déjà calculés : un verdict orange ou rouge est la piste à proposer en premier, avec son montant en euros tel quel ; tu ne recalcules pas et tu ne contredis pas un verdict vert.

# Sources
Liste de toutes les URLs citées : - [Nom court](URL)

# Avertissement
Une phrase sobre : ce briefing informe, il ne constitue pas un conseil en investissement.
"""


def _age_from(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _pct(fraction: float | None) -> float | None:
    """Domain rates are fractions (0.07 = 7 %); the snapshot keys are named ``*_pct``."""
    return None if fraction is None else round(fraction * 100, 2)


def build_anonymized_snapshot(
    wealth: Wealth,
    profile: Profile,
    optimizer_response: OptimizerResponse | None = None,
    verdicts: list[Verdict] | None = None,
) -> dict[str, Any]:
    """Project Wealth + Profile + optimizer + verdicts into a JSON-safe dict for the LLM.

    Stripped of: provider_account_id, institution_name. Kept: tickers,
    amounts, dates, all profile fields (age computed from birth_date).
    """
    return {
        "snapshot_at": wealth.snapshot_at.isoformat(),
        "profile": {
            "age": _age_from(profile.birth_date),
            "risk_level": getattr(profile, "risk_level", None),
            "fiscal_shares": profile.fiscal_shares,
            "rfr_n_minus_2_eur": profile.rfr_n_minus_2,
            "target_annual_return_pct": _pct(profile.target_annual_return),
            "max_annual_volatility_pct": _pct(profile.max_annual_volatility),
            "horizon_years": profile.horizon_years,
            "default_broker": profile.default_broker,
        },
        "net_worth_eur": round(wealth.net_worth, 2),
        "total_assets_eur": round(wealth.total_assets, 2),
        "total_liabilities_eur": round(wealth.total_liabilities, 2),
        "checking_total_eur": round(wealth.checking_total, 2),
        "pea_cash_total_eur": round(wealth.pea_cash_total, 2),
        "envelopes": [
            {
                "type": e.envelope_type,
                "display_name": e.display_name,
                "balance_eur": round(e.balance, 2),
                "rate_pct": _pct(e.rate_pct),
                "ceiling_eur": e.ceiling_eur,
                "headroom_eur": e.headroom_eur,
                "tax_status": e.tax_status,
            }
            for e in wealth.envelopes
        ],
        "investment_accounts": [
            {
                "account_type": acc.account_type,
                "currency": acc.currency,
                "total_value_eur": round(acc.value, 2),
                "unrealized_pnl_eur": round(acc.unrealized_pnl, 2),
                "positions": [
                    {
                        "ticker": p.ticker,
                        "label": p.label,
                        "isin": p.isin,
                        "quantity": p.quantity,
                        "avg_cost_eur": round(p.avg_cost, 4),
                        "current_value_eur": round(p.current_value, 2),
                        "unrealized_pnl_eur": round(p.unrealized_pnl, 2),
                        "unrealized_pnl_pct": round(p.unrealized_pnl_pct * 100, 2),
                    }
                    for p in acc.positions
                ],
            }
            for acc in wealth.investment_accounts
        ],
        "loans": [
            {
                "outstanding_eur": round(loan.outstanding_balance, 2),
                "interest_rate_pct": _pct(loan.interest_rate_pct),
                "monthly_payment_eur": loan.monthly_payment,
                "next_payment_date": (
                    loan.next_payment_date.isoformat() if loan.next_payment_date else None
                ),
                "is_in_deferral": loan.is_in_deferral,
                "maturity_date": loan.maturity_date.isoformat() if loan.maturity_date else None,
            }
            for loan in wealth.loans
        ],
        "optimizer": _serialize_optimizer(optimizer_response),
        "verdicts": [
            {
                "id": v.id,
                "title": v.title,
                "status": v.status,
                "headline": v.headline,
                "impact_eur_per_year": v.impact_eur_per_year,
                "action": v.action,
            }
            for v in (verdicts or [])
        ],
    }


def _serialize_optimizer(opt: OptimizerResponse | None) -> dict[str, Any] | None:
    if opt is None:
        return None
    return {
        "objective": opt.objective,
        "current": {
            "expected_return_pct": round(opt.current.expected_return * 100, 2),
            "volatility_pct": round(opt.current.volatility * 100, 2),
            "sharpe": round(opt.current.sharpe, 3),
        },
        "optimal": {
            "expected_return_pct": round(opt.optimal.expected_return * 100, 2),
            "volatility_pct": round(opt.optimal.volatility * 100, 2),
            "sharpe": round(opt.optimal.sharpe, 3),
        },
        "rebalance_gap_eur": [
            {
                "asset_id": a.ticker,
                "current_weight_pct": round(a.current_weight * 100, 2),
                "optimal_weight_pct": round(a.optimal_weight * 100, 2),
                "delta_eur": round(a.delta_value, 2),
            }
            for a in opt.actions
            if abs(a.delta_weight) > 0.01
        ],
    }


_STATUS_FR = {"green": "vert", "amber": "orange", "red": "rouge", "unknown": "incomplet"}


def build_user_prompt(snapshot: dict[str, Any]) -> str:
    """Format the anonymized snapshot as a Markdown brief for Claude.

    Mirrors the structure of the snapshot dict; the model has been told via
    the system prompt what sections to produce in return.
    """
    lines: list[str] = []
    snapshot_at = snapshot["snapshot_at"]
    lines.append(f"# Données patrimoniales (snapshot {snapshot_at})")
    lines.append("")

    p = snapshot["profile"]
    age = p["age"] if p["age"] is not None else "non renseigné"
    fs = p["fiscal_shares"] if p["fiscal_shares"] is not None else "non renseigné"
    rfr = p["rfr_n_minus_2_eur"] if p["rfr_n_minus_2_eur"] is not None else "non renseigné"
    horizon = p["horizon_years"] if p["horizon_years"] is not None else "non renseigné"
    tgt_ret = (
        p["target_annual_return_pct"]
        if p["target_annual_return_pct"] is not None
        else "non renseigné"
    )
    max_vol = (
        p["max_annual_volatility_pct"]
        if p["max_annual_volatility_pct"] is not None
        else "non renseigné"
    )
    broker = p["default_broker"] if p["default_broker"] is not None else "non renseigné"

    risk = p.get("risk_level")
    lines.append("## Profil utilisateur")
    lines.append(f"- Âge : {age}")
    if risk is not None:
        lines.append(f"- Curseur de risque : {risk} sur 5 (1 = prudent, 5 = dynamique)")
    lines.append(f"- Parts fiscales : {fs}")
    lines.append(f"- RFR N-2 : {rfr} €")
    lines.append(f"- Horizon : {horizon} ans")
    lines.append(f"- Objectif rendement annuel : {tgt_ret} %")
    lines.append(f"- Tolérance volatilité annuelle : {max_vol} %")
    lines.append(f"- Broker par défaut : {broker}")
    lines.append("")

    net = snapshot["net_worth_eur"]
    ta = snapshot["total_assets_eur"]
    tl = snapshot["total_liabilities_eur"]
    lines.append("## Patrimoine net")
    lines.append(f"- Total actifs : {ta:,.2f} €")
    lines.append(f"- Total passifs : {tl:,.2f} €")
    lines.append(f"- **Net : {net:,.2f} €**")
    lines.append("")

    chk = snapshot["checking_total_eur"]
    pea_cash = snapshot["pea_cash_total_eur"]
    lines.append("## Liquidités")
    lines.append(f"- Comptes courants : {chk:,.2f} €")
    lines.append(f"- Espèces sur PEA : {pea_cash:,.2f} €")
    lines.append("")

    if snapshot["envelopes"]:
        lines.append("## Enveloppes réglementées")
        for e in snapshot["envelopes"]:
            label = e["display_name"] or e["type"]
            balance = e["balance_eur"]
            ceiling = f"{e['ceiling_eur']:,.0f}" if e["ceiling_eur"] else "—"
            headroom = f"{e['headroom_eur']:,.0f}" if e["headroom_eur"] else "—"
            rate = f"{e['rate_pct']:.2f} %" if e["rate_pct"] else "—"
            tax = e["tax_status"] or "?"
            lines.append(
                f"- **{label}** : {balance:,.2f} € (plafond {ceiling} €, "
                f"headroom {headroom} €, taux {rate}, fiscalité {tax})"
            )
        lines.append("")

    if snapshot["investment_accounts"]:
        lines.append("## Comptes d'investissement")
        for acc in snapshot["investment_accounts"]:
            atype = acc["account_type"].upper()
            tot = acc["total_value_eur"]
            pnl = acc["unrealized_pnl_eur"]
            lines.append(f"### {atype} — total {tot:,.2f} € (PnL latent : {pnl:+,.2f} €)")
            if not acc["positions"]:
                lines.append("- (aucune position)")
                continue
            for pos in acc["positions"]:
                ticker = pos["ticker"]
                plabel = pos["label"]
                qty = pos["quantity"]
                pru = pos["avg_cost_eur"]
                cv = pos["current_value_eur"]
                pct = pos["unrealized_pnl_pct"]
                lines.append(
                    f"- `{ticker}` ({plabel}) : {qty:g} × PRU {pru:.2f} € → "
                    f"{cv:,.2f} € ({pct:+.1f} %)"
                )
        lines.append("")

    if snapshot["loans"]:
        lines.append("## Prêts en cours")
        for loan in snapshot["loans"]:
            outs = loan["outstanding_eur"]
            rate = f"{loan['interest_rate_pct']:.2f} %" if loan["interest_rate_pct"] else "—"
            mens = (
                f"{loan['monthly_payment_eur']:.2f} €/mois" if loan["monthly_payment_eur"] else "—"
            )
            deferral = " (en différé)" if loan["is_in_deferral"] else ""
            maturity = loan["maturity_date"] or "?"
            lines.append(
                f"- {outs:,.2f} € restant, taux {rate}, {mens}{deferral}, échéance {maturity}"
            )
        lines.append("")

    if snapshot.get("verdicts"):
        lines.append("## Verdicts de la méthode (déjà calculés, à reprendre tels quels)")
        for v in snapshot["verdicts"]:
            status = _STATUS_FR.get(v["status"], v["status"])
            impact = v["impact_eur_per_year"]
            impact_txt = f" ({impact:,.0f} € par an en jeu)" if impact else ""
            action = f" À faire : {v['action']}" if v["action"] else " Rien à faire."
            lines.append(f"- **{v['title']}** [{status}]{impact_txt} : {v['headline']}{action}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "En t'appuyant sur ces données ET sur l'actualité récente (utilise web_search pour "
        "les cours de ses fonds et les nouvelles qui les concernent), écris le briefing au "
        "format demandé dans le system prompt. Sois précis sur les chiffres réels "
        "ci-dessus, ne réinvente rien."
    )

    return "\n".join(lines)
