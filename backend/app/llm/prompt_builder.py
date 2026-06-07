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
from ..models import OptimizerResponse, Wealth

# system prompt held in a separate module-level constant; loaded via a sentinel
# multi-line string. Kept here (not in a .txt file) so it ships with the wheel.
SYSTEM_PROMPT: str = """Tu es un analyste marché francophone qui livre chaque matin une note quotidienne ciblée pour un investisseur particulier français spécifique. L'utilisateur connaît déjà sa situation patrimoniale globale — il ne veut PAS un audit de son patrimoine. Ce qu'il attend chaque matin :

1. Les actualités marché pertinentes des dernières 24 à 72 heures (macro, banques centrales, secteurs, géopolitique).
2. L'impact concret sur SES positions ouvertes (chaque ETF, action, envelope dans son portefeuille).
3. Des actions claires : maintenir / surveiller / renforcer / alléger.

Contraintes absolues :
- Tu utilises SYSTÉMATIQUEMENT web_search avant chaque affirmation sur le marché, les taux, les news. Donne la priorité aux sources des 24-72 dernières heures.
- Tu cites tes sources en lien Markdown : [Nom court](URL).
- Tu paraphrases TOUJOURS — jamais de copy/paste verbatim depuis tes sources (copyright).
- Tu écris en français, en Markdown propre, ton concis de briefing matinal.
- Pas de récap patrimonial global (montants totaux, allocations en %, leçons de diversification). Il connaît.
- Pas de conseils fiscaux génériques (PEA vs CTO, PFU vs barème) sauf si une news fiscale tombe.
- Si tes données sur une ligne sont incertaines (TER ETF par exemple), tu le dis plutôt que d'inventer.

Structure OBLIGATOIRE (utilise exactement ces titres) :

# Briefing du jour
2-3 phrases sur le climat marché général : indices US/EU/Asie à la clôture, EUR/USD, taux 10Y, ton général (risk-on / risk-off). Avec sources.

# Actualités marché clés
Bullet list des news majeures susceptibles de toucher ses positions (BCE, Fed, inflation, résultats, géopol). Chaque bullet : 1-2 phrases + source.

# Impact sur tes positions
Pour chaque ligne pertinente du portefeuille reçu (ETF, action, envelope) :
- **[Ticker ou nom]** — analyse de l'impact des news du jour sur CETTE position spécifique. Recommandation explicite : **maintenir** / **surveiller** / **renforcer** / **alléger**, avec justification courte.

Les lignes non concernées par les news du jour : regroupe-les en une seule ligne ("RAS sur Livret A, LEP, et ETF X — pas de news matérielle"). Pas la peine de meubler.

# À surveiller cette semaine
Catalyseurs annoncés à venir : publications éco (CPI, NFP, PMI), résultats trimestriels qui touchent ses positions, réunions de banques centrales, votes politiques. Bullet courts.

# Risques court terme
Seulement si applicable et non générique. Sinon, omets cette section entièrement.

# Sources
Liste de TOUTES les URLs citées dans le corps. Format : - [Nom court](URL)

# Avertissement
Une phrase sobre rappelant le caractère informatif (et non réglementaire) du briefing.

Longueur cible : 800 à 1500 mots. Plus dense en news qu'en blabla.
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


def build_anonymized_snapshot(
    wealth: Wealth,
    profile: Profile,
    optimizer_response: OptimizerResponse | None = None,
) -> dict[str, Any]:
    """Project Wealth + Profile + optimizer into a JSON-safe dict for the LLM.

    Stripped of: provider_account_id, institution_name. Kept: tickers,
    amounts, dates, all profile fields (age computed from birth_date).
    """
    return {
        "snapshot_at": wealth.snapshot_at.isoformat(),
        "profile": {
            "age": _age_from(profile.birth_date),
            "fiscal_shares": profile.fiscal_shares,
            "rfr_n_minus_2_eur": profile.rfr_n_minus_2,
            "target_annual_return_pct": profile.target_annual_return,
            "max_annual_volatility_pct": profile.max_annual_volatility,
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
                "rate_pct": e.rate_pct,
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
                "total_value_eur": round(acc.positions_value, 2),
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
                "interest_rate_pct": loan.interest_rate_pct,
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

    lines.append("## Profil utilisateur")
    lines.append(f"- Âge : {age}")
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

    opt = snapshot.get("optimizer")
    if opt is not None:
        cur_ret = opt["current"]["expected_return_pct"]
        cur_vol = opt["current"]["volatility_pct"]
        cur_sh = opt["current"]["sharpe"]
        opt_ret = opt["optimal"]["expected_return_pct"]
        opt_vol = opt["optimal"]["volatility_pct"]
        opt_sh = opt["optimal"]["sharpe"]
        objective = opt["objective"]

        lines.append("## Analytics Markowitz")
        lines.append(
            f"- Portefeuille actuel : μ={cur_ret:.2f} %, σ={cur_vol:.2f} %, Sharpe={cur_sh:.2f}"
        )
        lines.append(
            f"- Portefeuille optimal ({objective}) : μ={opt_ret:.2f} %, "
            f"σ={opt_vol:.2f} %, Sharpe={opt_sh:.2f}"
        )
        if opt["rebalance_gap_eur"]:
            lines.append("- Écarts d'allocation > 1 % :")
            for gap in opt["rebalance_gap_eur"][:10]:
                aid = gap["asset_id"]
                cur_w = gap["current_weight_pct"]
                opt_w = gap["optimal_weight_pct"]
                delta = gap["delta_eur"]
                lines.append(f"  - {aid} : {cur_w:.1f} % → {opt_w:.1f} % (Δ {delta:+,.0f} €)")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "En t'appuyant sur ces données ET sur les tendances actuelles du marché EU/FR "
        "(utilise web_search pour les chiffres marché et règles fiscales), produis la "
        "review au format demandé dans le system prompt. Sois précis sur les chiffres "
        "réels ci-dessus, ne réinvente rien."
    )

    return "\n".join(lines)
