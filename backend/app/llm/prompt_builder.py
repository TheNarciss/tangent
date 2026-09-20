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

from datetime import date, timedelta
from typing import Any

from ..db.models import Profile
from ..finance.performance import Performance, Point
from ..i18n import Locale
from ..models import MarketLead, OptimizerResponse, PicksResponse, Verdict, Wealth
from ..routers.spending import SpendingResponse

# system prompt held in a separate module-level constant; loaded via a sentinel
# multi-line string. Kept here (not in a .txt file) so it ships with the wheel.
SYSTEM_PROMPT: str = """Tu écris chaque matin un court briefing pour un épargnant français qui investit régulièrement (versements mensuels sur des fonds indiciels, livrets, parfois un prêt) et qui n'a pas de culture financière. Il ne veut pas devenir trader : il veut savoir si quelque chose le concerne, et sinon être rassuré. Tu tutoies, tu écris en français simple, sans jargon, sans symbole grec, sans ratio.

Ce que tu fais :
1. Tu regardes ce qui a bougé dans SON patrimoine depuis hier ou cette semaine (ses fonds, ses livrets, ses échéances de prêt). Les relevés quotidiens fournis dans les données (valeur du portefeuille hier, il y a 7 jours, il y a 30 jours, versements déduits) sont ta première source pour les chiffres ; web_search sert à expliquer le mouvement avec les cours et les actualités récentes (24-72 h), pas à deviner le chiffre. Tu parles de « ton fonds Monde » ou du nom du fonds, jamais du ticker seul.
2. Tu expliques ce que ça veut dire pour lui, en une ou deux phrases par point, avec un ordre de grandeur en euros plutôt qu'en pourcentage quand c'est parlant.
3. Tu dis clairement s'il y a quelque chose à faire. Presque toujours, la réponse est « rien » : continuer ses versements. Tu ne recommandes jamais d'acheter ou de vendre une ligne à cause d'une news du jour. Une action n'est proposée que pour une raison structurelle (un livret qui arrive à son plafond, une échéance de prêt inhabituelle, un versement manqué, une règle fiscale qui change) et tu la présentes comme une piste, pas un ordre.

Contraintes :
- Tu utilises web_search avant toute affirmation sur les marchés ou l'actualité, en privilégiant les sources des 24-72 dernières heures, et tu cites tes sources en lien Markdown : [Nom court](URL). Tu paraphrases toujours, jamais de copie mot pour mot.
- Pas de tour d'horizon des indices, devises et taux : tu ne mentionnes un marché que s'il explique un mouvement de SES fonds.
- Pas de rendement attendu, volatilité, Sharpe, corrélation, frontière efficiente. Pas de liste de recommandations par ligne.
- Si tu n'es pas sûr d'un chiffre, tu le dis.
- Le briefing d'hier est fourni pour la continuité : tu ne le répètes pas, tu dis ce qui a changé depuis.
- « La liste de l'année » et sa liste de suivi sont fournies pour information : tu n'en fais jamais un ordre d'achat ou de vente ; tu signales seulement, comme un fait, si une ligne qu'il détient vient d'y entrer ou d'en sortir.
- Les dépenses et l'épargne mensuelle servent à situer ses versements ; pas de leçon de budget, pas de détail par catégorie sauf s'il explique un versement manqué.
- 250 à 500 mots, Markdown propre.

Structure OBLIGATOIRE (utilise exactement ces titres) :

# Ce qui a bougé chez toi
Deux à quatre phrases : les mouvements notables de ses fonds et livrets depuis hier ou cette semaine, en euros quand c'est possible, avec sources. S'il ne s'est rien passé de notable, dis-le en une phrase.

# Ce que ça veut dire
Une explication simple de la cause (une hausse de taux, un résultat d'entreprise, une décision politique…) et de ce que ça change ou ne change pas pour un épargnant qui verse tous les mois.

# À faire cette semaine
Par défaut une seule ligne : « Rien à faire : continue tes versements. » Sinon, une à deux pistes concrètes, chacune avec sa raison structurelle. Les verdicts de la méthode fournis dans les données sont déjà calculés : un verdict orange ou rouge est la piste à proposer en premier, avec son montant en euros tel quel ; tu ne recalcules pas et tu ne contredis pas un verdict vert.

# Pistes à regarder
Les données peuvent contenir une liste brute de « pistes de marché » collectée dans la nuit : des paris Polymarket ou Kalshi qui ont bougé, des dirigeants qui achètent l'action de leur propre société, de grands gérants qui ouvrent ou soldent une ligne, des activistes connus qui déclarent plus de 5 % d'une société, des spéculateurs sur contrats à terme à un extrême d'un an (CFTC). C'est du bruit pour l'essentiel, et c'est voulu : c'est toi qui tries. Tu en gardes zéro à trois, celles qui peuvent concerner un épargnant en fonds indiciels (les taux, une récession, l'inflation, un secteur ou une région qu'il détient), et tu dis en une phrase ce que chacune raconte et pourquoi la regarder. Une piste est une chose à suivre, jamais un ordre d'acheter ou de vendre, et tu ne cites une société que comme un fait déclaré, pas comme une idée. Si rien ne mérite l'attention, une seule ligne : « Rien de notable cette nuit. » Si les données ne contiennent pas de pistes, tu omets cette section.

# Sources
Liste de toutes les URLs citées : - [Nom court](URL)

# Avertissement
Une phrase sobre : ce briefing informe, il ne constitue pas un conseil en investissement.
"""

SYSTEM_PROMPT_EN: str = """Every morning you write a short briefing for a saver living in France who invests regularly (monthly contributions into index funds and regulated savings accounts such as the Livret A, sometimes with a loan running) and who has no financial background. They do not want to become a trader: they want to know whether something concerns them, and otherwise to be reassured. You address them as "you", you write in plain English, without jargon, Greek letters or ratios. You keep the French names of their products (Livret A, LDDS, PEA, PER, assurance-vie, fonds euros): those are the words they see at their bank.

What you do:
1. You look at what moved in THEIR wealth since yesterday or this week (their funds, their savings accounts, their loan instalments). The daily readings supplied in the data (portfolio value yesterday, 7 days ago, 30 days ago, contributions deducted) are your first source for the figures; web_search serves to explain the move with recent prices and news (24-72 h), not to guess the figure. You say "your World fund" or the fund's name, never the ticker alone.
2. You explain what it means for them, in one or two sentences per point, with an order of magnitude in euros rather than in percent when that speaks better.
3. You say clearly whether there is anything to do. Almost always, the answer is "nothing": keep up the contributions. You never recommend buying or selling a line because of the day's news. An action is only suggested for a structural reason (a savings account reaching its ceiling, an unusual loan instalment, a missed contribution, a tax rule that changes) and you present it as a lead, not an order.

Constraints:
- You use web_search before any statement about markets or the news, favouring sources from the last 24-72 hours, and you cite your sources as Markdown links: [Short name](URL). You always paraphrase, never copy word for word.
- No tour of indices, currencies and rates: you only mention a market if it explains a move in THEIR funds.
- No expected return, volatility, Sharpe, correlation, efficient frontier. No list of recommendations per line.
- If you are not sure of a figure, you say so.
- Yesterday's briefing is supplied for continuity: you do not repeat it, you say what has changed since.
- "The list of the year" and its watchlist are supplied for information: you never turn them into a buy or sell order; you only point out, as a fact, if a line they hold has just entered or left it.
- Spending and monthly savings serve to put their contributions in context; no budget lecture, no breakdown by category unless it explains a missed contribution.
- 250 to 500 words, clean Markdown.

MANDATORY structure (use exactly these headings):

# What moved for you
Two to four sentences: the notable moves in their funds and savings accounts since yesterday or this week, in euros when possible, with sources. If nothing notable happened, say so in one sentence.

# What it means
A simple explanation of the cause (a rate rise, a company's results, a political decision…) and of what it changes or does not change for a saver who contributes every month.

# To do this week
By default a single line: "Nothing to do: keep up your contributions." Otherwise, one or two concrete leads, each with its structural reason. The method's verdicts supplied in the data are already computed: an amber or red verdict is the lead to put forward first, with its amount in euros as given; you do not recompute and you do not contradict a green verdict.

# Leads to watch
The data may contain a raw list of "market leads" collected overnight: Polymarket or Kalshi bets that moved, executives buying their own company's shares, large managers opening or closing a line, known activists declaring more than 5% of a company, futures speculators at a one-year extreme (CFTC). Most of it is noise, and that is intended: you do the sorting. You keep zero to three, the ones that may concern a saver in index funds (rates, a recession, inflation, a sector or a region they hold), and you say in one sentence what each one tells and why to watch it. A lead is something to follow, never an order to buy or sell, and you only name a company as a declared fact, not as an idea. If nothing deserves attention, a single line: "Nothing notable last night." If the data contains no leads, you omit this section.

# Sources
List of every URL cited: - [Short name](URL)

# Disclaimer
One sober sentence: this briefing informs, it is not investment advice.
"""


def system_prompt(locale: Locale) -> str:
    """The briefing's system prompt in the person's language (``SYSTEM_PROMPT`` is the French one)."""
    return SYSTEM_PROMPT_EN if locale == "en" else SYSTEM_PROMPT


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
    market_leads: list[MarketLead] | None = None,
    *,
    spending: SpendingResponse | None = None,
    monthly_saved: float | None = None,
    performance: Performance | None = None,
    history: list[Point] | None = None,
    watchlist: list[str] | None = None,
    previous_review: str | None = None,
    picks: PicksResponse | None = None,
    macro: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Project everything the app knows into a JSON-safe dict for the LLM.

    Stripped of: provider_account_id, institution_name. Kept: tickers,
    amounts, dates, all profile fields (age computed from birth_date). The
    market leads, the list of the year and the observed rates are the same
    for everyone: raw, the briefing sorts them.
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
        "market_leads": [
            {
                "source": lead.source,
                "title": lead.title,
                "detail": lead.detail,
                "url": lead.url,
                "observed_at": lead.observed_at,
            }
            for lead in (market_leads or [])
        ],
        "macro": ({f"{name}_pct": _pct(value) for name, value in macro.items()} if macro else None),
        "history": [
            {
                "day": pt.day.isoformat(),
                "value_eur": round(pt.value, 2),
                "net_flow_eur": round(pt.net_flow, 2),
            }
            for pt in (history or [])
        ],
        "performance": (
            {
                "since": performance.start.isoformat(),
                "days": performance.days,
                "twr_pct": _pct(performance.twr),
                "twr_annualized_pct": _pct(performance.twr_annualized),
                "irr_pct": _pct(performance.irr),
                "behaviour_gap_pct": _pct(performance.behaviour_gap),
                "drawdown_pct": _pct(performance.drawdown),
                "max_drawdown_pct": _pct(performance.max_drawdown),
                "peak_day": performance.peak_day.isoformat() if performance.peak_day else None,
                "net_flows_eur": round(performance.net_flows, 2),
            }
            if performance is not None
            else None
        ),
        "spending": (
            {
                "monthly_average_eur": spending.monthly_average,
                "monthly_income_average_eur": spending.monthly_income_average,
                "current_month_total_eur": round(spending.current_month_total, 2),
                "unlabelled_share_pct": _pct(spending.unlabelled_share),
                "categories": [
                    {
                        "category": c.category,
                        "total_eur": round(c.total, 2),
                        "share_pct": _pct(c.share),
                    }
                    for c in spending.categories[:8]
                ],
                "months": [
                    {
                        "month": m.month,
                        "spent_eur": round(m.total, 2),
                        "income_eur": round(m.income, 2),
                    }
                    for m in spending.months
                ],
            }
            if spending is not None
            else None
        ),
        "monthly_saved_eur": round(monthly_saved, 2) if monthly_saved is not None else None,
        "watchlist": list(watchlist or []),
        "picks": (
            {
                "as_of": picks.as_of,
                "next_review": picks.next_review,
                "review": picks.review,
                "guard_on": picks.guard_on,
                "held": list(picks.held),
                "bought": list(picks.bought),
                "sold": list(picks.sold),
            }
            if picks is not None
            else None
        ),
        "previous_review": previous_review or None,
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


def build_user_prompt(snapshot: dict[str, Any], locale: Locale = "fr") -> str:
    """Format the anonymized snapshot as a Markdown brief for Claude.

    Mirrors the structure of the snapshot dict; the model has been told via
    the system prompt what sections to produce in return. The figures keep
    their French field names whatever the language; the sentences that
    instruct the model follow ``locale``.
    """
    en = locale == "en"
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
        lines.append(
            "## The method's verdicts (already computed, to be taken as they are)"
            if en
            else "## Verdicts de la méthode (déjà calculés, à reprendre tels quels)"
        )
        for v in snapshot["verdicts"]:
            status = _STATUS_FR.get(v["status"], v["status"])
            impact = v["impact_eur_per_year"]
            impact_txt = f" ({impact:,.0f} € par an en jeu)" if impact else ""
            if en:
                action = f" To do: {v['action']}" if v["action"] else " Nothing to do."
            else:
                action = f" À faire : {v['action']}" if v["action"] else " Rien à faire."
            lines.append(f"- **{v['title']}** [{status}]{impact_txt} : {v['headline']}{action}")
        lines.append("")

    _render_history(lines, snapshot.get("history") or [])
    _render_performance(lines, snapshot.get("performance"))
    _render_spending(lines, snapshot.get("spending"), snapshot.get("monthly_saved_eur"))
    _render_macro(lines, snapshot.get("macro"))
    if snapshot.get("watchlist"):
        lines.append("## Liste de suivi (lignes qu'il surveille sans les détenir)")
        lines.append("- " + ", ".join(f"`{t}`" for t in snapshot["watchlist"]))
        lines.append("")
    _render_picks(lines, snapshot.get("picks"), en)

    if snapshot.get("market_leads"):
        lines.append(
            "## Market leads (raw, collected overnight — most of them are noise)"
            if en
            else "## Pistes de marché (brutes, collectées cette nuit — la plupart sont du bruit)"
        )
        for lead in snapshot["market_leads"]:
            lines.append(
                f"- [{lead['source']}] {lead['title']} — {lead['detail']} "
                f"({lead['observed_at']}, {lead['url']})"
            )
        lines.append("")

    if snapshot.get("previous_review"):
        lines.append(
            "## Yesterday's briefing (for continuity: do not repeat it, say what has changed)"
            if en
            else "## Briefing d'hier (pour la continuité : ne le répète pas, dis ce qui a changé)"
        )
        lines.append("")
        lines.append(snapshot["previous_review"].strip())
        lines.append("")

    lines.append("---")
    lines.append("")
    if en:
        lines.append(
            "Drawing on these data AND on recent news (use web_search for the prices of their "
            "funds and the news that concerns them), write the briefing in English, in the "
            "format requested in the system prompt. Be precise about the real figures above, "
            "invent nothing. The field names above are in French, as at their bank."
        )
    else:
        lines.append(
            "En t'appuyant sur ces données ET sur l'actualité récente (utilise web_search pour "
            "les cours de ses fonds et les nouvelles qui les concernent), écris le briefing au "
            "format demandé dans le system prompt. Sois précis sur les chiffres réels "
            "ci-dessus, ne réinvente rien."
        )

    return "\n".join(lines)


def _reading_before(history: list[dict[str, Any]], days_back: int) -> dict[str, Any] | None:
    """The latest reading at least `days_back` days before the last one."""
    last = date.fromisoformat(history[-1]["day"])
    target = last - timedelta(days=days_back)
    earlier = [h for h in history if date.fromisoformat(h["day"]) <= target]
    return earlier[-1] if earlier else None


def _render_history(lines: list[str], history: list[dict[str, Any]]) -> None:
    if len(history) < 2:
        return
    last = history[-1]
    lines.append(
        "## Relevés quotidiens du portefeuille (valeur des placements, versements déduits)"
    )
    lines.append(f"- Valeur au {last['day']} : {last['value_eur']:,.2f} €")
    for label, days_back in (("hier", 1), ("7 jours", 7), ("30 jours", 30)):
        then = _reading_before(history, days_back)
        if then is None or then is last:
            continue
        flows = sum(h["net_flow_eur"] for h in history if then["day"] < h["day"] <= last["day"])
        move = last["value_eur"] - then["value_eur"] - flows
        flows_txt = f", versements sur la période {flows:,.2f} €" if flows else ""
        lines.append(f"- Depuis {label} ({then['day']}) : {move:+,.2f} €{flows_txt}")
    lines.append("")


def _render_performance(lines: list[str], perf: dict[str, Any] | None) -> None:
    if not perf:
        return
    lines.append(f"## Performance mesurée depuis le {perf['since']} ({perf['days']} jours)")
    for label, key in (
        ("Rendement du portefeuille (pondéré par le temps)", "twr_pct"),
        ("Le même, annualisé", "twr_annualized_pct"),
        ("Son résultat à lui, versements compris (TRI annualisé)", "irr_pct"),
        ("Écart dû au calendrier de ses versements", "behaviour_gap_pct"),
    ):
        if perf.get(key) is not None:
            lines.append(f"- {label} : {perf[key]:+.2f} %")
    peak = f" (plus haut le {perf['peak_day']})" if perf.get("peak_day") else ""
    lines.append(
        f"- Recul depuis le plus haut : {perf['drawdown_pct']:.2f} %{peak}, "
        f"pire recul sur la période : {perf['max_drawdown_pct']:.2f} %"
    )
    lines.append(f"- Versé au total sur la période : {perf['net_flows_eur']:,.2f} €")
    lines.append("")


def _render_spending(
    lines: list[str], spending: dict[str, Any] | None, monthly_saved: float | None
) -> None:
    if not spending and monthly_saved is None:
        return
    lines.append("## Dépenses et épargne (comptes courants, trois derniers mois)")
    if spending:
        if spending["monthly_average_eur"] is not None:
            lines.append(f"- Dépenses moyennes par mois : {spending['monthly_average_eur']:,.0f} €")
        if spending["monthly_income_average_eur"] is not None:
            lines.append(
                f"- Revenus moyens par mois : {spending['monthly_income_average_eur']:,.0f} €"
            )
        lines.append(f"- Mois en cours : {spending['current_month_total_eur']:,.0f} € dépensés")
        if spending["categories"]:
            cats = ", ".join(
                f"{c['category']} {c['total_eur']:,.0f} €" for c in spending["categories"][:5]
            )
            lines.append(f"- Principales catégories sur la fenêtre : {cats}")
        if spending["unlabelled_share_pct"]:
            lines.append(f"- Part encore sans catégorie : {spending['unlabelled_share_pct']:.0f} %")
    if monthly_saved is not None:
        lines.append(
            f"- Mis de côté en moyenne par mois (livrets et placements) : {monthly_saved:,.0f} €"
        )
    lines.append("")


def _render_macro(lines: list[str], macro: dict[str, Any] | None) -> None:
    if not macro:
        return
    lines.append("## Contexte observé (sources publiques, déjà lues par l'app)")
    if macro.get("policy_rate_pct") is not None:
        lines.append(f"- Taux directeur : {macro['policy_rate_pct']:.2f} %")
    if macro.get("inflation_pct") is not None:
        lines.append(f"- Inflation : {macro['inflation_pct']:.2f} %")
    lines.append("")


def _render_picks(lines: list[str], picks: dict[str, Any] | None, en: bool = False) -> None:
    if not picks:
        return
    if en:
        lines.append(
            f'## "The list of the year" (published rule, review {picks["review"]}, '
            f"as of {picks['as_of']}, next review {picks['next_review']} — information, not an instruction)"
        )
    else:
        lines.append(
            f"## « La liste de l'année » (règle publiée, revue {picks['review']}, "
            f"arrêtée au {picks['as_of']}, prochaine revue {picks['next_review']} — information, pas une consigne)"
        )
    lines.append("- Tenues : " + (", ".join(f"`{t}`" for t in picks["held"]) or "aucune"))
    if picks["bought"]:
        lines.append(
            "- Entrées à la dernière revue : " + ", ".join(f"`{t}`" for t in picks["bought"])
        )
    if picks["sold"]:
        lines.append(
            "- Sorties à la dernière revue : " + ", ".join(f"`{t}`" for t in picks["sold"])
        )
    if picks["guard_on"]:
        lines.append(
            "- Guard-rail on: the market was falling at the review, the rule holds nothing."
            if en
            else "- Garde-fou actif : le marché baissait à la revue, la règle ne tient rien."
        )
    lines.append("")
