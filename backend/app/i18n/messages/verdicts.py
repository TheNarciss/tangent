"""What the verdict engine writes: titles, headlines, actions and step texts (ADR-023)."""

FR: dict[str, str] = {
    "verdicts.join.and": "{head} et {last}",
    # ── Frais réels ────────────────────────────────────────────────────────
    "verdicts.fees.title": "Frais réels",
    "verdicts.fees.headline.no_lines": (
        "Aucune ligne de placement connue : connecte un PEA, un compte-titres "
        "ou une assurance vie pour mesurer ce que tes placements te coûtent."
    ),
    "verdicts.fees.lines.one": "{n} ligne",
    "verdicts.fees.lines.many": "{n} lignes",
    "verdicts.fees.headline.missing_ter": (
        "Il manque les frais annuels (TER) de {lines}, soit {share} de tes placements : "
        "impossible de mesurer ce qu'ils te coûtent."
    ),
    "verdicts.fees.action.missing_ter": (
        "Renseigne le TER de ces lignes dans Comptes (ouvre le compte, puis la ligne)."
    ),
    "verdicts.fees.at_least": "au moins ",
    "verdicts.fees.base": "Tes placements te coûtent {at_least}{pct} par an, soit {total}",
    "verdicts.fees.complete.ter": "le TER de {lines}",
    "verdicts.fees.complete.broker": "ta banque (ses frais ne sont pas comptés)",
    "verdicts.fees.complete.join": " et ",
    "verdicts.fees.complete": " Renseigne {items} pour affiner.",
    "verdicts.fees.headline.green": "{base} : c'est bas, rien à changer.",
    "verdicts.fees.headline.amber": (
        "{base} : la même somme en PEA en ligne avec un ETF monde coûterait {reference}."
    ),
    "verdicts.fees.action.amber": (
        "Compare ton courtier et tes fonds : {saving} par an d'écart avec la référence.{complete}"
    ),
    "verdicts.fees.headline.red": (
        "{base}, soit {saving} de plus par an qu'un PEA en ligne avec un ETF monde."
    ),
    "verdicts.fees.action.red": (
        "Change de courtier ou remplace les fonds les plus chers par un ETF indiciel : "
        "c'est {saving} par an à récupérer.{complete}"
    ),
    # ── Où placer le prochain euro ─────────────────────────────────────────
    "verdicts.next_euro.title": "Où placer le prochain euro",
    "verdicts.next_euro.headline.nothing": (
        "Aucun compte connecté : impossible de dire où ton prochain euro sera le mieux placé."
    ),
    "verdicts.next_euro.action.nothing": "Connecte ta banque dans Comptes.",
    "verdicts.next_euro.step.precaution.label": "Épargne de précaution",
    "verdicts.next_euro.step.precaution.unknown": (
        "{liquid} sur tes livrets ; tes dépenses mensuelles ne sont pas encore connues "
        "(aucun débit synchronisé sur 90 jours), la cible de 3 mois ne peut pas être calculée."
    ),
    "verdicts.next_euro.step.precaution.short": (
        "{liquid} sur tes livrets, soit {months} mois de dépenses ; "
        "la cible est {target_months} mois, {target}."
    ),
    "verdicts.next_euro.step.precaution.green": (
        "{liquid} sur tes livrets, {months} mois de dépenses : "
        "la cible de {target_months} mois ({target}) est couverte."
    ),
    "verdicts.next_euro.step.lep.label": "LEP",
    "verdicts.next_euro.step.lep.unknown": (
        "Éligibilité au LEP inconnue : renseigne ton âge, ton foyer et ton revenu fiscal "
        "dans Profil."
    ),
    "verdicts.next_euro.step.lep.amber": (
        "Tu as droit au LEP ({rate} net) : {movable} de tes livrets peuvent y aller, "
        "{gain} de plus par an{open}."
    ),
    "verdicts.next_euro.step.lep.open": ", il faut l'ouvrir dans ta banque",
    "verdicts.next_euro.step.lep.full": (
        "Ton LEP est au plafond ou tes livrets sont vides : rien à déplacer."
    ),
    "verdicts.next_euro.step.lep.ineligible": (
        "Pas éligible au LEP (revenu fiscal au-dessus du plafond)."
    ),
    "verdicts.next_euro.step.pea.label": "PEA",
    "verdicts.next_euro.step.pea.room": (
        "Ton PEA vaut {value} ; il reste {room} avant le plafond de versements."
    ),
    "verdicts.next_euro.step.pea.full": (
        "Ton PEA est au plafond de versements : le long terme continue en assurance vie ou en CTO."
    ),
    "verdicts.next_euro.step.pea.none": (
        "Pas de PEA : c'est l'enveloppe la moins taxée pour des actions à long terme "
        "(17,2 % au lieu de 30 % après 5 ans), et son horloge de 5 ans ne démarre "
        "qu'à l'ouverture.{gain}"
    ),
    "verdicts.next_euro.step.pea.none_gain": (
        " Sur {base} de CTO et de versements, environ {gain} par an."
    ),
    "verdicts.next_euro.step.per.label": "PER",
    "verdicts.next_euro.step.per.unknown": (
        "Tranche d'imposition inconnue : renseigne ton revenu fiscal et ton foyer dans Profil."
    ),
    "verdicts.next_euro.step.per.worth": (
        "Tu es dans la tranche à {tmi} : chaque euro versé sur un PER te rend {tmi} d'impôt, "
        "jusqu'à {ceiling} par an. {gain}{warning}"
    ),
    "verdicts.next_euro.step.per.gain_on": "Sur {base} de versements, {gain} d'impôt en moins.",
    "verdicts.next_euro.step.per.gain_ceiling": "Soit {gain} d'impôt en moins au plafond.",
    "verdicts.next_euro.step.per.warning": (
        " Attention : bloqué jusqu'à la retraite, et seulement avec des frais de contrat "
        "sous 0,6 %."
    ),
    "verdicts.next_euro.step.per.low": (
        "Tu es dans la tranche à {tmi} : un PER déductible n'est pas intéressant en dessous "
        "de 30 %, garde la liquidité du PEA."
    ),
    "verdicts.next_euro.dest.lep": "ton LEP",
    "verdicts.next_euro.dest.lep_open": "un LEP à ouvrir",
    "verdicts.next_euro.dest.livret_a": "ton Livret A",
    "verdicts.next_euro.dest.ldds": "ton LDDS",
    "verdicts.next_euro.dest.livret": "un livret (Livret A ou LDDS)",
    "verdicts.next_euro.dest.pea_open": "un PEA à ouvrir",
    "verdicts.next_euro.dest.pea": "ton PEA",
    "verdicts.next_euro.reason.precaution": (
        "ton épargne de précaution couvre {months} mois de dépenses, la cible est {target_months}"
    ),
    "verdicts.next_euro.reason.pea_open": (
        "c'est l'enveloppe la moins taxée pour le long terme et son horloge de 5 ans "
        "ne tourne pas encore"
    ),
    "verdicts.next_euro.reason.precaution_ok": "ta précaution est en place",
    "verdicts.next_euro.reason.pea": "le long terme passe par le PEA",
    "verdicts.next_euro.headline": "Ton prochain euro va dans {dest} : {reason}.",
    "verdicts.next_euro.action.precaution": (
        "Mets tes prochains versements sur {dest} jusqu'à {target}."
    ),
    "verdicts.next_euro.action.pea_open": (
        "Ouvre un PEA chez un courtier en ligne, même avec 10 €, pour lancer les 5 ans."
    ),
    "verdicts.next_euro.action.lep": (
        "Ouvre un LEP dans ta banque et bascules-y {movable} de tes livrets."
    ),
    "verdicts.next_euro.action.per": (
        "Étudie un PER en ligne à frais bas (contrat sous 0,6 %) pour la part de ton épargne "
        "que tu peux bloquer jusqu'à la retraite."
    ),
    "verdicts.next_euro.action.pea_full": (
        "Ton PEA est plein : oriente le long terme vers une assurance vie en ligne ou un CTO."
    ),
    "verdicts.next_euro.action.profile": (
        "Renseigne ton profil (âge, foyer, revenu fiscal) pour évaluer le LEP et le PER."
    ),
    # ── Part d'actions ─────────────────────────────────────────────────────
    "verdicts.risk_share.title": "Part d'actions",
    "verdicts.risk_share.headline.no_pocket": (
        "Pas de poche long terme connue (PEA, compte-titres, assurance vie, PER) : "
        "la part d'actions ne peut pas être mesurée."
    ),
    "verdicts.risk_share.action.no_pocket": "Connecte tes comptes d'investissement dans Comptes.",
    "verdicts.risk_share.headline.no_level": (
        "Tu as {share} d'actions sur {pocket} de placements long terme, mais ton curseur "
        "prudent ↔ dynamique n'est pas réglé."
    ),
    "verdicts.risk_share.action.no_level": (
        "Règle ton curseur dans Profil pour connaître la part qui te correspond."
    ),
    "verdicts.risk_share.base": (
        "Tu as {share} d'actions sur {pocket} de placements long terme ; "
        "ton profil « {label} » vise {target}"
    ),
    "verdicts.risk_share.headline.green": "{base} : tu es dans la bande, rien à changer.",
    "verdicts.risk_share.headline.low": (
        "{base} : {missing} de trop en produits de taux, soit environ {impact} de rendement "
        "en moins par an."
    ),
    "verdicts.risk_share.action.low": (
        "Oriente tes prochains versements vers ton ETF monde jusqu'à {target} d'actions ; "
        "pas besoin de vendre quoi que ce soit."
    ),
    "verdicts.risk_share.headline.high": (
        "{base} : {excess} d'actions au-delà de ton profil. Une mauvaise année peut te coûter "
        "{bad_year} sur cette poche."
    ),
    "verdicts.risk_share.action.high": (
        "Dirige tes prochains versements vers le fonds euros ou un livret plutôt que vers "
        "les actions, ou monte ton curseur si tu assumes ces variations."
    ),
    # ── Taux d'épargne ─────────────────────────────────────────────────────
    "verdicts.savings_rate.title": "Taux d'épargne",
    "verdicts.savings_rate.headline.no_income": (
        "Ton revenu fiscal n'est pas renseigné : le taux d'épargne ne peut pas être calculé."
    ),
    "verdicts.savings_rate.action.no_income": (
        "Renseigne ton revenu fiscal de référence dans Profil."
    ),
    "verdicts.savings_rate.how.observed": "d'après tes virements des 90 derniers jours",
    "verdicts.savings_rate.how.declared": "d'après ton versement déclaré",
    "verdicts.savings_rate.base": "Tu épargnes {saved} par mois, {rate} de ton revenu ({how})",
    "verdicts.savings_rate.headline.green": (
        "{base} : au-dessus des {target} visés, c'est ce qui fait le capital."
    ),
    "verdicts.savings_rate.action.green": (
        "Programme une hausse automatique de {escalation} par an : {next_year} par mois "
        "l'an prochain, sans y penser."
    ),
    "verdicts.savings_rate.headline.below": (
        "{base} ; la cible est {target}, soit {target_eur} par mois. "
        "L'écart vaut {gap} dans {years} ans."
    ),
    "verdicts.savings_rate.action.below": (
        "Monte ton virement automatique de {missing} par mois, ou par paliers : "
        "+{escalation} à chaque augmentation de salaire jusqu'à {target_eur}."
    ),
    # ── Épargne pour ton objectif ──────────────────────────────────────────
    "verdicts.goal.title": "Épargne pour ton objectif",
    "verdicts.goal.headline.none": (
        "Tu n'as pas fixé d'objectif : donne une somme et une échéance dans Projection "
        "et la méthode te dira combien épargner chaque mois."
    ),
    "verdicts.goal.action.none": "Fixe ton objectif dans Projection (« Mon objectif »).",
    "verdicts.goal.chances": "{n} chances sur 10",
    "verdicts.goal.base": (
        "Avec {monthly} par mois, tu as {chances} d'avoir {goal} dans {years} ans, "
        "en euros d'aujourd'hui"
    ),
    "verdicts.goal.headline.green": "{base} : ton objectif est sur les rails.",
    "verdicts.goal.action.green": (
        "Garde le rythme ; {required} par mois suffiraient pour 3 chances sur 4."
    ),
    "verdicts.goal.headline.below": "{base} ; il faut {required} par mois pour 3 chances sur 4.",
    "verdicts.goal.action.below": (
        "Monte ton versement de {extra} par mois, ou repousse l'échéance, ou revois la somme visée."
    ),
    # ── Ce que tes placements ont vraiment rapporté ────────────────────────
    "verdicts.performance.title": "Ce que tes placements ont vraiment rapporté",
    "verdicts.performance.headline.young": (
        "L'historique de ton compte commence le {started} : encore {missing} jours "
        "avant un rendement qui veut dire quelque chose."
    ),
    "verdicts.performance.headline.today": (
        "L'historique de ton compte commence aujourd'hui. Tangent en enregistre "
        "la valeur chaque nuit ; le vrai rendement s'affichera dans un mois."
    ),
    "verdicts.performance.headline.twr_only": (
        "Depuis le {since}, tes placements ont fait {twr}, versements mis à part."
    ),
    "verdicts.performance.strategy": "{twr} par an pour tes fonds",
    "verdicts.performance.yours": "{irr} par an pour ton argent",
    "verdicts.performance.headline.green": (
        "Depuis le {since} : {strategy}, {yours}. Le moment de tes versements ne t'a rien coûté."
    ),
    "verdicts.performance.headline.amber": (
        "Depuis le {since} : {strategy}, mais seulement {yours}. Le calendrier de tes "
        "versements te coûte {gap} par an, soit {cost}."
    ),
    "verdicts.performance.action.amber": (
        "Verse le même montant tous les mois, par virement automatique, plutôt qu'au "
        "moment où le marché te semble bien orienté."
    ),
    # ── Baisse depuis le plus haut ─────────────────────────────────────────
    "verdicts.drawdown.title": "Baisse depuis le plus haut",
    "verdicts.drawdown.headline.no_history": (
        "Pas encore d'historique : la baisse depuis le plus haut sera suivie ici."
    ),
    "verdicts.drawdown.headline.near_peak": (
        "Tes placements sont à {dd} de leur plus haut du {peak_day} : rien d'anormal."
    ),
    "verdicts.drawdown.headline.at_peak": (
        "Tes placements sont à leur plus haut, atteint le {peak_day}."
    ),
    "verdicts.drawdown.headline.down": (
        "Tes placements ont baissé de {dd} depuis leur plus haut du {peak_day}, soit {missing}."
    ),
    "verdicts.drawdown.action.down": (
        "Rien à faire, et surtout pas vendre : une baisse ne devient une perte qu'au "
        "moment où on vend. Continue tes versements, ils achètent moins cher."
    ),
    # ── Répartition ────────────────────────────────────────────────────────
    "verdicts.diversification.title": "Répartition",
    "verdicts.diversification.headline.no_lines": (
        "Aucune ligne de placement connue : impossible de dire si ta répartition tient debout."
    ),
    "verdicts.diversification.duplicates": (
        "{names} suivent tous « {index} » : en garder plusieurs ne te protège pas plus qu'un seul."
    ),
    "verdicts.diversification.why.stock": "c'est une seule société",
    "verdicts.diversification.why.segment": "« {index} » ne couvre qu'un segment du marché",
    "verdicts.diversification.why.unknown": "on ne sait pas ce qu'il y a dedans",
    "verdicts.diversification.concentrated": "{label} pèse {weight} et {why}.",
    "verdicts.diversification.headline.green": (
        "Tes lignes ne font pas doublon et aucune ne concentre le risque : "
        "rien à changer de ce côté."
    ),
    "verdicts.diversification.action.amber": (
        "Oriente tes prochains versements plutôt que de vendre : "
        "vendre coûte des frais et de l'impôt sur la plus-value."
    ),
}

EN: dict[str, str] = {
    "verdicts.join.and": "{head} and {last}",
    # ── Real fees ──────────────────────────────────────────────────────────
    "verdicts.fees.title": "Real fees",
    "verdicts.fees.headline.no_lines": (
        "No investment line known: connect a PEA, a brokerage account "
        "or a life-insurance policy to measure what your investments cost you."
    ),
    "verdicts.fees.lines.one": "{n} line",
    "verdicts.fees.lines.many": "{n} lines",
    "verdicts.fees.headline.missing_ter": (
        "The annual fees (TER) of {lines} are missing, {share} of your investments: "
        "impossible to measure what they cost you."
    ),
    "verdicts.fees.action.missing_ter": (
        "Enter the TER of these lines in Accounts (open the account, then the line)."
    ),
    "verdicts.fees.at_least": "at least ",
    "verdicts.fees.base": "Your investments cost you {at_least}{pct} a year, {total}",
    "verdicts.fees.complete.ter": "the TER of {lines}",
    "verdicts.fees.complete.broker": "your bank (its fees are not counted)",
    "verdicts.fees.complete.join": " and ",
    "verdicts.fees.complete": " Enter {items} to refine this.",
    "verdicts.fees.headline.green": "{base}: that is low, nothing to change.",
    "verdicts.fees.headline.amber": (
        "{base}: the same sum in an online PEA with a world ETF would cost {reference}."
    ),
    "verdicts.fees.action.amber": (
        "Compare your broker and your funds: {saving} a year above the reference.{complete}"
    ),
    "verdicts.fees.headline.red": (
        "{base}, {saving} a year more than an online PEA with a world ETF."
    ),
    "verdicts.fees.action.red": (
        "Change broker or replace the dearest funds with an index ETF: "
        "that is {saving} a year to recover.{complete}"
    ),
    # ── Where the next euro goes ───────────────────────────────────────────
    "verdicts.next_euro.title": "Where the next euro goes",
    "verdicts.next_euro.headline.nothing": (
        "No account connected: impossible to say where your next euro is best placed."
    ),
    "verdicts.next_euro.action.nothing": "Connect your bank in Accounts.",
    "verdicts.next_euro.step.precaution.label": "Emergency savings",
    "verdicts.next_euro.step.precaution.unknown": (
        "{liquid} in your savings accounts; your monthly spending is not known yet "
        "(no debit synced over 90 days), the 3-month target cannot be worked out."
    ),
    "verdicts.next_euro.step.precaution.short": (
        "{liquid} in your savings accounts, {months} months of spending; "
        "the target is {target_months} months, {target}."
    ),
    "verdicts.next_euro.step.precaution.green": (
        "{liquid} in your savings accounts, {months} months of spending: "
        "the {target_months}-month target ({target}) is covered."
    ),
    "verdicts.next_euro.step.lep.label": "LEP",
    "verdicts.next_euro.step.lep.unknown": (
        "LEP eligibility unknown: enter your age, household and taxable income in Profile."
    ),
    "verdicts.next_euro.step.lep.amber": (
        "You qualify for the LEP ({rate} net): {movable} of your savings can move there, "
        "{gain} more a year{open}."
    ),
    "verdicts.next_euro.step.lep.open": ", you need to open one at your bank",
    "verdicts.next_euro.step.lep.full": (
        "Your LEP is at its ceiling or your savings accounts are empty: nothing to move."
    ),
    "verdicts.next_euro.step.lep.ineligible": (
        "Not eligible for the LEP (taxable income above the ceiling)."
    ),
    "verdicts.next_euro.step.pea.label": "PEA",
    "verdicts.next_euro.step.pea.room": (
        "Your PEA is worth {value}; {room} left before the contribution ceiling."
    ),
    "verdicts.next_euro.step.pea.full": (
        "Your PEA is at its contribution ceiling: the long term carries on in life insurance "
        "or a brokerage account."
    ),
    "verdicts.next_euro.step.pea.none": (
        "No PEA: it is the least-taxed wrapper for long-term equities "
        "(17.2% instead of 30% after 5 years), and its 5-year clock only starts "
        "when it is opened.{gain}"
    ),
    "verdicts.next_euro.step.pea.none_gain": (
        " On {base} of brokerage holdings and contributions, about {gain} a year."
    ),
    "verdicts.next_euro.step.per.label": "PER",
    "verdicts.next_euro.step.per.unknown": (
        "Tax bracket unknown: enter your taxable income and household in Profile."
    ),
    "verdicts.next_euro.step.per.worth": (
        "You are in the {tmi} bracket: every euro paid into a PER gives you {tmi} back in tax, "
        "up to {ceiling} a year. {gain}{warning}"
    ),
    "verdicts.next_euro.step.per.gain_on": "On {base} of contributions, {gain} less tax.",
    "verdicts.next_euro.step.per.gain_ceiling": "That is {gain} less tax at the ceiling.",
    "verdicts.next_euro.step.per.warning": (
        " Careful: locked until retirement, and only with contract fees under 0.6%."
    ),
    "verdicts.next_euro.step.per.low": (
        "You are in the {tmi} bracket: a deductible PER is not worth it below 30%, "
        "keep the liquidity of the PEA."
    ),
    "verdicts.next_euro.dest.lep": "your LEP",
    "verdicts.next_euro.dest.lep_open": "a LEP to open",
    "verdicts.next_euro.dest.livret_a": "your Livret A",
    "verdicts.next_euro.dest.ldds": "your LDDS",
    "verdicts.next_euro.dest.livret": "a savings account (Livret A or LDDS)",
    "verdicts.next_euro.dest.pea_open": "a PEA to open",
    "verdicts.next_euro.dest.pea": "your PEA",
    "verdicts.next_euro.reason.precaution": (
        "your emergency savings cover {months} months of spending, the target is {target_months}"
    ),
    "verdicts.next_euro.reason.pea_open": (
        "it is the least-taxed wrapper for the long term and its 5-year clock is not running yet"
    ),
    "verdicts.next_euro.reason.precaution_ok": "your emergency savings are in place",
    "verdicts.next_euro.reason.pea": "the long term goes through the PEA",
    "verdicts.next_euro.headline": "Your next euro goes into {dest}: {reason}.",
    "verdicts.next_euro.action.precaution": (
        "Put your next contributions into {dest} up to {target}."
    ),
    "verdicts.next_euro.action.pea_open": (
        "Open a PEA with an online broker, even with €10, to start the 5-year clock."
    ),
    "verdicts.next_euro.action.lep": (
        "Open a LEP at your bank and move {movable} of your savings into it."
    ),
    "verdicts.next_euro.action.per": (
        "Look into a low-fee online PER (contract under 0.6%) for the part of your savings "
        "you can lock away until retirement."
    ),
    "verdicts.next_euro.action.pea_full": (
        "Your PEA is full: steer the long term towards an online life-insurance policy "
        "or a brokerage account."
    ),
    "verdicts.next_euro.action.profile": (
        "Fill in your profile (age, household, taxable income) to assess the LEP and the PER."
    ),
    # ── Equity share ───────────────────────────────────────────────────────
    "verdicts.risk_share.title": "Equity share",
    "verdicts.risk_share.headline.no_pocket": (
        "No long-term pocket known (PEA, brokerage account, life insurance, PER): "
        "the equity share cannot be measured."
    ),
    "verdicts.risk_share.action.no_pocket": "Connect your investment accounts in Accounts.",
    "verdicts.risk_share.headline.no_level": (
        "You have {share} in equities out of {pocket} of long-term investments, but your "
        "cautious ↔ dynamic slider is not set."
    ),
    "verdicts.risk_share.action.no_level": (
        "Set your slider in Profile to find out the share that suits you."
    ),
    "verdicts.risk_share.base": (
        "You have {share} in equities out of {pocket} of long-term investments; "
        "your “{label}” profile aims for {target}"
    ),
    "verdicts.risk_share.headline.green": "{base}: you are within the band, nothing to change.",
    "verdicts.risk_share.headline.low": (
        "{base}: {missing} too much in fixed income, roughly {impact} less return a year."
    ),
    "verdicts.risk_share.action.low": (
        "Steer your next contributions to your world ETF until equities reach {target}; "
        "no need to sell anything."
    ),
    "verdicts.risk_share.headline.high": (
        "{base}: {excess} in equities beyond your profile. A bad year can cost you "
        "{bad_year} on this pocket."
    ),
    "verdicts.risk_share.action.high": (
        "Direct your next contributions to the euro fund or a savings account rather than "
        "equities, or raise your slider if you accept these swings."
    ),
    # ── Savings rate ───────────────────────────────────────────────────────
    "verdicts.savings_rate.title": "Savings rate",
    "verdicts.savings_rate.headline.no_income": (
        "Your taxable income is not filled in: the savings rate cannot be worked out."
    ),
    "verdicts.savings_rate.action.no_income": ("Enter your reference taxable income in Profile."),
    "verdicts.savings_rate.how.observed": "from your transfers over the last 90 days",
    "verdicts.savings_rate.how.declared": "from your declared contribution",
    "verdicts.savings_rate.base": "You save {saved} a month, {rate} of your income ({how})",
    "verdicts.savings_rate.headline.green": (
        "{base}: above the {target} target, this is what builds the capital."
    ),
    "verdicts.savings_rate.action.green": (
        "Schedule an automatic {escalation} rise a year: {next_year} a month next year, "
        "without thinking about it."
    ),
    "verdicts.savings_rate.headline.below": (
        "{base}; the target is {target}, {target_eur} a month. "
        "The gap is worth {gap} in {years} years."
    ),
    "verdicts.savings_rate.action.below": (
        "Raise your standing order by {missing} a month, or in steps: "
        "+{escalation} at each pay rise, up to {target_eur}."
    ),
    # ── Saving for your goal ───────────────────────────────────────────────
    "verdicts.goal.title": "Saving for your goal",
    "verdicts.goal.headline.none": (
        "You have not set a goal: give an amount and a deadline in Projection "
        "and the method will tell you how much to save each month."
    ),
    "verdicts.goal.action.none": "Set your goal in Projection (“My goal”).",
    "verdicts.goal.chances": "{n} chances in 10",
    "verdicts.goal.base": (
        "With {monthly} a month, you have {chances} of having {goal} in {years} years, "
        "in today's euros"
    ),
    "verdicts.goal.headline.green": "{base}: your goal is on track.",
    "verdicts.goal.action.green": (
        "Keep the pace; {required} a month would be enough for 3 chances in 4."
    ),
    "verdicts.goal.headline.below": "{base}; it takes {required} a month for 3 chances in 4.",
    "verdicts.goal.action.below": (
        "Raise your contribution by {extra} a month, or push back the deadline, "
        "or revise the amount."
    ),
    # ── What your investments really returned ──────────────────────────────
    "verdicts.performance.title": "What your investments really returned",
    "verdicts.performance.headline.young": (
        "Your account history starts on {started}: {missing} more days "
        "before a return that means something."
    ),
    "verdicts.performance.headline.today": (
        "Your account history starts today. Tangent records its value every night; "
        "the real return will show in a month."
    ),
    "verdicts.performance.headline.twr_only": (
        "Since {since}, your investments made {twr}, contributions aside."
    ),
    "verdicts.performance.strategy": "{twr} a year for your funds",
    "verdicts.performance.yours": "{irr} a year for your money",
    "verdicts.performance.headline.green": (
        "Since {since}: {strategy}, {yours}. The timing of your contributions cost you nothing."
    ),
    "verdicts.performance.headline.amber": (
        "Since {since}: {strategy}, but only {yours}. The timing of your contributions "
        "costs you {gap} a year, {cost}."
    ),
    "verdicts.performance.action.amber": (
        "Pay in the same amount every month, by standing order, rather than "
        "when the market looks good to you."
    ),
    # ── Drop from the peak ─────────────────────────────────────────────────
    "verdicts.drawdown.title": "Drop from the peak",
    "verdicts.drawdown.headline.no_history": (
        "No history yet: the drop from the peak will be tracked here."
    ),
    "verdicts.drawdown.headline.near_peak": (
        "Your investments are {dd} off their peak of {peak_day}: nothing unusual."
    ),
    "verdicts.drawdown.headline.at_peak": (
        "Your investments are at their peak, reached on {peak_day}."
    ),
    "verdicts.drawdown.headline.down": (
        "Your investments have dropped {dd} from their peak of {peak_day}, {missing}."
    ),
    "verdicts.drawdown.action.down": (
        "Nothing to do, and above all do not sell: a drop only becomes a loss "
        "when you sell. Keep up your contributions, they buy cheaper."
    ),
    # ── Allocation ─────────────────────────────────────────────────────────
    "verdicts.diversification.title": "Allocation",
    "verdicts.diversification.headline.no_lines": (
        "No investment line known: impossible to say whether your allocation holds up."
    ),
    "verdicts.diversification.duplicates": (
        "{names} all track “{index}”: keeping several protects you no more than one."
    ),
    "verdicts.diversification.why.stock": "it is a single company",
    "verdicts.diversification.why.segment": "“{index}” covers only one segment of the market",
    "verdicts.diversification.why.unknown": "nobody knows what is inside it",
    "verdicts.diversification.concentrated": "{label} weighs {weight} and {why}.",
    "verdicts.diversification.headline.green": (
        "Your lines do not duplicate each other and none concentrates the risk: "
        "nothing to change on that side."
    ),
    "verdicts.diversification.action.amber": (
        "Steer your next contributions rather than selling: "
        "selling costs fees and capital-gains tax."
    ),
}
