/** « Méthode »: the verdict cards, their detail rows, the proposal and the stress list. */
const fr = {
  "method.unavailable": "Les verdicts ne sont pas disponibles pour l'instant",
  "method.retry": "Réessaie dans un instant.",
  "method.intro":
    "Chaque carte est un verdict : un feu, une phrase, un montant par an, une chose à faire. Elles sont rangées par urgence, puis par euros en jeu — ce qui est en haut compte le plus. Ouvre une carte pour voir le calcul.",
  "method.perYearSuffix": "/an",
  "method.gauge.zero": "0 %",
  "method.gauge.full": "100 %",

  // Verdict card chrome
  "method.status.green": "Rien à changer",
  "method.status.amber": "À surveiller",
  "method.status.red": "À corriger",
  "method.status.unknown": "Incomplet",
  "method.card.todo": "À faire : ",
  "method.card.detail": "Détail",
  "method.card.more.one": "Un autre point à regarder",
  "method.card.more.other": "{count} autres points à regarder",

  // Répartition
  "method.div.unrecognisedClass": "classe non reconnue",
  "method.div.singleSegment": " · un seul segment",
  "method.div.duplicatesAfter":
    " suivent le même indice « {index} » et pèsent ensemble {weight}. En garder plusieurs ne protège pas plus qu'un seul, et multiplie les frais fixes par ligne.",
  "method.div.concentratedAfter": " pèse {weight} et n'est pas diversifié : {reason}.",
  "method.div.singleCompany": "c'est une seule société",
  "method.div.singleMarketSegment": "il ne couvre qu'un segment du marché",
  "method.div.unrecognised":
    "Non reconnu, donc non jugé : {labels}. Tangent lit le nom officiel de chaque ligne pour savoir ce qu'elle suit ; celles-ci ne correspondent à rien de connu.",
  "method.div.note":
    "Un fonds indiciel large n'est jamais signalé, quel que soit son poids : détenir un seul ETF monde est la recommandation la plus répandue. Le seuil de {max} ne vise que les lignes qui parient sur une seule chose.",

  // Ce que tes placements ont vraiment rapporté
  "method.perf.noData":
    "Tangent enregistre chaque nuit la valeur de tes placements et les quantités qui la composent. C'est la seule façon de distinguer ce que le marché a fait de ce que tu as versé, parce que ta banque ne transmet aucune opération sur un PEA ou un compte-titres.",
  "method.perf.minDays.one": "Il faut {count} jour pour un premier chiffre.",
  "method.perf.minDays.other": "Il faut {count} jours pour un premier chiffre.",
  "method.perf.twr": "Tes fonds (TWR)",
  "method.perf.twrAnnual": "par an, versements mis à part",
  "method.perf.twrTotal": "depuis le début, versements mis à part",
  "method.perf.irr": "Ton argent (TRI)",
  "method.perf.irrSub": "par an, avec le calendrier de tes versements",
  "method.perf.irrMissing": "six mois d'historique nécessaires",
  "method.perf.gap": "Écart de comportement",
  "method.perf.gapSub": "ce que le moment de tes versements ajoute ou retire",
  "method.perf.days.one": "{count} jour",
  "method.perf.days.other": "{count} jours",
  "method.perf.history":
    "Historique du {start} au {end}, {days}. {first} au départ, {flows} versés depuis, {last} aujourd'hui. Le TWR juge la stratégie, le TRI juge ton résultat ; c'est la mesure que les fonds publient et celle que ton relevé devrait porter.",

  // Baisse depuis le plus haut
  "method.dd.below": "Sous le plus haut",
  "method.dd.peakOn": "plus haut du {date}",
  "method.dd.sinceStart": "depuis le début",
  "method.dd.inEuros": "En euros",
  "method.dd.inEurosSub": "par rapport à ce plus haut",
  "method.dd.worst": "Pire baisse connue",
  "method.dd.worstSub": "depuis que Tangent suit ton compte",
  "method.dd.contextBefore":
    "Pour situer : sur {years} ans d'actions américaines ({from}-{to}), la pire année a coûté ",
  "method.dd.contextAfter": " en pouvoir d'achat. C'est le pire connu, pas une prévision.",
  "method.dd.atPeak": "au plus haut",
  "method.dd.alertStep": "seuil d'alerte {pct}",
  "method.dd.note":
    "Un gérant doit prévenir son client le jour où le portefeuille passe 10 % sous son point de départ, puis à chaque tranche de 10 % (MiFID II, article 62). Tangent applique la même règle, mesurée hors versements. Une baisse n'est une perte qu'au moment où on vend.",

  // Épargne pour ton objectif
  "method.goal.target": "Objectif",
  "method.goal.targetSub": "dans {years} ans, en euros d'aujourd'hui",
  "method.goal.start": "Point de départ",
  "method.goal.startSub": "+ {monthly} par mois ({source})",
  "method.goal.observed": "virements observés",
  "method.goal.declared": "versement déclaré",
  "method.goal.required": "Pour 3 chances sur 4",
  "method.goal.perMonth": "{amount}/mois",
  "method.goal.extra": "soit {amount} de plus qu'aujourd'hui",
  "method.goal.already": "tu y es déjà",
  "method.goal.gauge": "{p} de chances · cible {target}",
  "method.goal.simulation":
    "Dans {years} ans, 1 fois sur 10 tu auras moins de {p10}, la moitié du temps plus de {p50}, 1 fois sur 10 plus de {p90}. Simulation de {paths} trajectoires avec {equity} d'actions (ton profil), {mu} de rendement réel par an après {inflation} d'inflation, volatilité {sigma}.",

  // Taux d'épargne
  "method.sr.saved": "Épargné par mois",
  "method.sr.savedObserved": "virements vers livrets et placements, 90 derniers jours",
  "method.sr.savedDeclared": "versement déclaré dans ton profil",
  "method.sr.income": "Revenu par mois",
  "method.sr.incomeSub": "revenu fiscal {rfr} sur 12 mois",
  "method.sr.target": "Cible",
  "method.sr.targetSub": "{pct} du revenu",
  "method.sr.gauge": "toi : {rate} · cible {target}",
  "method.sr.missing":
    "Les {missing} par mois qui manquent valent {gap} dans {years} ans à {growth} par an.",
  "method.sr.note":
    "À 20 ans, plus de la moitié du capital final vient des versements, pas du rendement. La hausse automatique de {escalation} par an (« Save More Tomorrow ») porterait ton versement à {next} l'an prochain.",

  // Où placer le prochain euro
  "method.next.liquid": "Sur tes livrets",
  "method.next.monthsOfSpending.one": "{count} mois de dépenses",
  "method.next.monthsOfSpending.other": "{count} mois de dépenses",
  "method.next.unknownSpending": "dépenses mensuelles inconnues",
  "method.next.precautionTarget": "Cible de précaution",
  "method.next.spending": "Dépenses par mois",
  "method.next.spendingSub": "débits de tes comptes courants, 90 derniers jours",
  "method.next.rule":
    "La règle, dans l'ordre : précaution sur livrets, puis actions à long terme dans le PEA, puis PER seulement au-dessus de la tranche à 30 %, le reste en compte-titres.",
  "method.next.tmi":
    "Ta tranche d'imposition estimée : {tmi}, d'après ton revenu fiscal et tes parts.",

  // Part d'actions
  "method.risk.longRunBefore":
    "Pourquoi accepter ces variations : de {from} à {to}, les actions ont rapporté ",
  "method.risk.longRunEquities": "{pct} par an",
  "method.risk.longRunAfter":
    " contre {bonds} pour les obligations d'État. C'est ce qui s'est passé, pas ce qui se passera.",
  "method.risk.share": "Part d'actions",
  "method.risk.shareSub": "{equity} en lignes cotées sur {pocket}",
  "method.risk.target": "Part visée",
  "method.risk.capped": "plafonnée par ton horizon de {years} ans ({merton} sinon)",
  "method.risk.profile": "profil « {label} », horizon {years} ans",
  "method.risk.badYear": "Mauvaise année",
  "method.risk.badYearSub": "deux fois la volatilité des actions sur ta poche actions",
  "method.risk.gaugeLeft": "0 % actions",
  "method.risk.band": "bande {lo} – {hi}",
  "method.risk.note":
    "La part visée est le point de la droite de marché que ton curseur choisit (volatilité maximale de ton cran divisée par celle des actions monde, {sigma}). C'est la part de Merton, avec une aversion au risque γ ≈ {gamma}. Les lignes cotées comptent comme actions ; fonds euros, PER ou assurance vie sans détail et PEL comptent comme produits de taux.",

  // Frais réels
  "method.fees.funds": "Frais des fonds",
  "method.fees.fundsSub": "TER de chaque ligne × sa valeur",
  "method.fees.fundsSubMissing": ", lignes sans TER exclues",
  "method.fees.broker": "Frais du courtier",
  "method.fees.brokerUnknown": "banque non renseignée : ses frais ne sont pas comptés",
  "method.fees.brokerSub": "{broker} : garde, frais par ligne, courtage sur {monthly}/mois",
  "method.fees.defaultBroker": "courtier",
  "method.fees.reference": "Référence",
  "method.fees.referenceSub": "PEA en ligne + ETF monde, {pct} par an",
  "method.fees.setTer": "TER à renseigner",
  "method.fees.perYear": "{pct} par an",
  "method.fees.source": "source",
  "method.fees.total":
    "Total {total} par an, soit {pct} de {positions}. Vert jusqu'à {green} par an, orange jusqu'à {amber}. Les frais des fonds sont déjà dans les cours : ils ne sont pas retirés une seconde fois de la projection.",
  "method.fees.uncovered": "Non mesuré, le contrat ne détaille pas ses lignes : {accounts}.",

  // Une piste (Proposal)
  "method.proposal.loading": "Calcul de la piste…",
  "method.proposal.title": "Une piste",
  "method.proposal.titleProfile": "Une piste, selon ton profil",
  "method.proposal.fillProfile":
    "Renseigne ton profil pour une piste adaptée à ton curseur prudent ↔ dynamique.",
  "method.proposal.infeasible":
    "Avec tes lignes actuelles, le rendement visé n'est pas atteignable au niveau de risque de ton curseur. Piste : accepter un peu plus de variations, ou viser moins haut.",
  "method.proposal.error": "La piste n'a pas pu être calculée pour l'instant.",
  "method.proposal.nothing": "Rien à changer : ta répartition colle déjà à ton profil.",
  "method.proposal.placeOn": "Placer sur",
  "method.proposal.buy": "Renforcer",
  "method.proposal.sell": "Alléger",
  "method.proposal.note":
    "Ce n'est qu'une piste : avant de vendre, compte les frais de courtage et l'impôt sur la plus-value. Le plus simple est souvent d'orienter tes prochains versements.",

  // Ce qu'un krach coûterait (StressList)
  "method.stress.behavesBefore": "Ton portefeuille se comporte comme un profil ",
  "method.stress.sliderBefore": " alors que ton curseur est sur ",
  "method.stress.movesMore": " : il bouge plus que ce que tu as dit accepter.",
  "method.stress.movesLess": " : il bouge moins que ce que tu acceptes.",
  "method.stress.consistent": ", comme ton curseur. Cohérent.",
  "method.stress.worstCrisis": "Pire crise rejouée : {label}",
  "method.stress.worstYear": "Pire année déjà vue sur {label}",
  "method.stress.thisClass": "cette classe",
  "method.stress.worstYearSub":
    "douze mois consécutifs, sur l'historique complet de la classe depuis 1990",
  "method.stress.worstDrawdown": "Pire baisse vécue par ce panier",
  "method.stress.worstDrawdownSub":
    "du plus-haut au creux suivant, sur {history} d'historique commun à tes lignes",
  "method.stress.tooShort": " — trop court pour être comparé aux crises ci-dessus",
  "method.stress.historyAvailable": "l'historique disponible",
  "method.stress.historyMonths.one": "{count} mois",
  "method.stress.historyMonths.other": "{count} mois",
  "method.stress.historyYears.one": "{count} an",
  "method.stress.historyYears.other": "{count} ans",
  "method.stress.allCrises": "Les {count} crises rejouées, une par une",
  "method.stress.range": "de {from} à {to}",
  "method.stress.dollar": "Dont le dollar : {effect} {amount}, soit {pct} sur tes fonds monde.",
  "method.stress.dollarGain": "il t'a fait gagner",
  "method.stress.dollarLoss": "il t'a coûté",
  "method.stress.noteBefore":
    "Les crises sont rejouées sur les classes d'actifs, pas sur les cours de tes lignes : aucun ETF français n'a d'historique avant 2009. Chaque perte est en euros, change compris, et le pourcentage porte sur ",
  "method.stress.noteStrong": "tout ton patrimoine",
  "method.stress.noteAfter":
    ", pas seulement sur tes placements. Tes livrets ne bougent pas et ton fonds euros ne perd pas sa valeur, seul son taux futur baisse.",
  "method.stress.measured.one":
    "Une de tes classes est mesurée sur son propre indice quotidien, du plus haut au creux de chaque épisode — ",
  "method.stress.measured.other":
    "{count} de tes classes sont mesurées sur son propre indice quotidien, du plus haut au creux de chaque épisode — ",
  "method.stress.replayed.one":
    "Une de tes classes est rejouée avec l'amplitude des actions monde, faute de série par épisode — ",
  "method.stress.replayed.other":
    "{count} de tes classes sont rejouées avec l'amplitude des actions monde, faute de série par épisode — ",
  "method.stress.replayedAfter":
    ". Un fonds sectoriel ou régional tombe plus fort que l'indice mondial : ces lignes sont donc sous-estimées ici.",
};

const en: Record<keyof typeof fr, string> = {
  "method.unavailable": "Verdicts are not available right now",
  "method.retry": "Try again in a moment.",
  "method.intro":
    "Each card is a verdict: a traffic light, one sentence, an amount per year, one thing to do. They are sorted by urgency, then by euros at stake — what sits at the top matters most. Open a card to see the working.",
  "method.perYearSuffix": "/yr",
  "method.gauge.zero": "0%",
  "method.gauge.full": "100%",

  // Verdict card chrome
  "method.status.green": "Nothing to change",
  "method.status.amber": "Keep an eye on it",
  "method.status.red": "Needs fixing",
  "method.status.unknown": "Incomplete",
  "method.card.todo": "To do: ",
  "method.card.detail": "Details",
  "method.card.more.one": "One more thing to look at",
  "method.card.more.other": "{count} more things to look at",

  // Diversification
  "method.div.unrecognisedClass": "unrecognised class",
  "method.div.singleSegment": " · a single segment",
  "method.div.duplicatesAfter":
    " track the same index “{index}” and together weigh {weight}. Holding several protects no more than holding one, and multiplies the fixed per-line fees.",
  "method.div.concentratedAfter": " weighs {weight} and is not diversified: {reason}.",
  "method.div.singleCompany": "it is a single company",
  "method.div.singleMarketSegment": "it covers only one segment of the market",
  "method.div.unrecognised":
    "Not recognised, so not judged: {labels}. Tangent reads each line's official name to work out what it tracks; these match nothing known.",
  "method.div.note":
    "A broad index fund is never flagged, whatever its weight: holding a single world ETF is the most common recommendation. The {max} threshold only targets lines that bet on one thing.",

  // What your investments really returned
  "method.perf.noData":
    "Every night Tangent records the value of your investments and the quantities behind it. It is the only way to tell what the market did from what you paid in, because your bank passes on no transactions for a PEA or a brokerage account.",
  "method.perf.minDays.one": "It takes {count} day for a first figure.",
  "method.perf.minDays.other": "It takes {count} days for a first figure.",
  "method.perf.twr": "Your funds (TWR)",
  "method.perf.twrAnnual": "per year, contributions aside",
  "method.perf.twrTotal": "since the start, contributions aside",
  "method.perf.irr": "Your money (IRR)",
  "method.perf.irrSub": "per year, with the timing of your contributions",
  "method.perf.irrMissing": "six months of history needed",
  "method.perf.gap": "Behaviour gap",
  "method.perf.gapSub": "what the timing of your contributions adds or takes away",
  "method.perf.days.one": "{count} day",
  "method.perf.days.other": "{count} days",
  "method.perf.history":
    "History from {start} to {end}, {days}. {first} at the start, {flows} paid in since, {last} today. TWR judges the strategy, IRR judges your result; it is the measure funds publish and the one your statement should carry.",

  // Fall from the peak
  "method.dd.below": "Below the peak",
  "method.dd.peakOn": "peak on {date}",
  "method.dd.sinceStart": "since the start",
  "method.dd.inEuros": "In euros",
  "method.dd.inEurosSub": "against that peak",
  "method.dd.worst": "Worst known fall",
  "method.dd.worstSub": "since Tangent started tracking your account",
  "method.dd.contextBefore":
    "For perspective: over {years} years of US equities ({from}-{to}), the worst year cost ",
  "method.dd.contextAfter": " in purchasing power. That is the worst on record, not a forecast.",
  "method.dd.atPeak": "at the peak",
  "method.dd.alertStep": "alert threshold {pct}",
  "method.dd.note":
    "A manager must warn their client the day the portfolio falls 10% below its starting point, then at each further 10% step (MiFID II, article 62). Tangent applies the same rule, measured excluding contributions. A fall only becomes a loss the moment you sell.",

  // Saving for your goal
  "method.goal.target": "Goal",
  "method.goal.targetSub": "in {years} years, in today's euros",
  "method.goal.start": "Starting point",
  "method.goal.startSub": "+ {monthly} a month ({source})",
  "method.goal.observed": "observed transfers",
  "method.goal.declared": "declared contribution",
  "method.goal.required": "For a 3-in-4 chance",
  "method.goal.perMonth": "{amount}/month",
  "method.goal.extra": "that is {amount} more than today",
  "method.goal.already": "you are already there",
  "method.goal.gauge": "{p} chance · target {target}",
  "method.goal.simulation":
    "In {years} years, 1 time in 10 you will have less than {p10}, half the time more than {p50}, 1 time in 10 more than {p90}. Simulation of {paths} paths with {equity} in equities (your profile), {mu} real return per year after {inflation} inflation, volatility {sigma}.",

  // Savings rate
  "method.sr.saved": "Saved per month",
  "method.sr.savedObserved": "transfers to savings accounts and investments, last 90 days",
  "method.sr.savedDeclared": "contribution declared in your profile",
  "method.sr.income": "Income per month",
  "method.sr.incomeSub": "taxable income {rfr} over 12 months",
  "method.sr.target": "Target",
  "method.sr.targetSub": "{pct} of income",
  "method.sr.gauge": "you: {rate} · target {target}",
  "method.sr.missing":
    "The missing {missing} a month are worth {gap} in {years} years at {growth} a year.",
  "method.sr.note":
    "Over 20 years, more than half of the final capital comes from contributions, not returns. An automatic {escalation} yearly rise (“Save More Tomorrow”) would bring your contribution to {next} next year.",

  // Where to put the next euro
  "method.next.liquid": "In your savings accounts",
  "method.next.monthsOfSpending.one": "{count} month of spending",
  "method.next.monthsOfSpending.other": "{count} months of spending",
  "method.next.unknownSpending": "monthly spending unknown",
  "method.next.precautionTarget": "Safety cushion target",
  "method.next.spending": "Spending per month",
  "method.next.spendingSub": "debits from your current accounts, last 90 days",
  "method.next.rule":
    "The rule, in order: a safety cushion in savings accounts, then long-term equities in the PEA, then PER only above the 30% tax bracket, the rest in a brokerage account.",
  "method.next.tmi":
    "Your estimated tax bracket: {tmi}, from your taxable income and household shares.",

  // Equity share
  "method.risk.longRunBefore":
    "Why put up with these swings: from {from} to {to}, equities returned ",
  "method.risk.longRunEquities": "{pct} a year",
  "method.risk.longRunAfter":
    " against {bonds} for government bonds. That is what happened, not what will happen.",
  "method.risk.share": "Equity share",
  "method.risk.shareSub": "{equity} in listed lines out of {pocket}",
  "method.risk.target": "Target share",
  "method.risk.capped": "capped by your {years}-year horizon ({merton} otherwise)",
  "method.risk.profile": "profile “{label}”, {years}-year horizon",
  "method.risk.badYear": "Bad year",
  "method.risk.badYearSub": "twice the volatility of equities, applied to your equity pocket",
  "method.risk.gaugeLeft": "0% equities",
  "method.risk.band": "band {lo} – {hi}",
  "method.risk.note":
    "The target share is the point on the capital market line your slider picks (your level's maximum volatility divided by that of world equities, {sigma}). It is the Merton share, with a risk aversion γ ≈ {gamma}. Listed lines count as equities; euro funds, PER or life insurance without a breakdown and PEL count as fixed-income products.",

  // Real fees
  "method.fees.funds": "Fund fees",
  "method.fees.fundsSub": "each line's TER × its value",
  "method.fees.fundsSubMissing": ", lines without a TER excluded",
  "method.fees.broker": "Broker fees",
  "method.fees.brokerUnknown": "bank not set: its fees are not counted",
  "method.fees.brokerSub": "{broker}: custody, per-line fees, brokerage on {monthly}/month",
  "method.fees.defaultBroker": "broker",
  "method.fees.reference": "Benchmark",
  "method.fees.referenceSub": "online PEA + world ETF, {pct} a year",
  "method.fees.setTer": "TER to fill in",
  "method.fees.perYear": "{pct} a year",
  "method.fees.source": "source",
  "method.fees.total":
    "Total {total} a year, that is {pct} of {positions}. Green up to {green} a year, amber up to {amber}. Fund fees are already in the prices: they are not taken off a second time in the projection.",
  "method.fees.uncovered": "Not measured, the contract does not break down its lines: {accounts}.",

  // A suggestion (Proposal)
  "method.proposal.loading": "Working out a suggestion…",
  "method.proposal.title": "A suggestion",
  "method.proposal.titleProfile": "A suggestion, based on your profile",
  "method.proposal.fillProfile":
    "Fill in your profile for a suggestion tailored to your cautious ↔ dynamic slider.",
  "method.proposal.infeasible":
    "With your current lines, the target return cannot be reached at your slider's risk level. Suggestion: accept a little more variation, or aim lower.",
  "method.proposal.error": "The suggestion could not be worked out right now.",
  "method.proposal.nothing": "Nothing to change: your allocation already matches your profile.",
  "method.proposal.placeOn": "Put into",
  "method.proposal.buy": "Top up",
  "method.proposal.sell": "Trim",
  "method.proposal.note":
    "This is only a suggestion: before selling, count brokerage fees and capital gains tax. The simplest route is often to steer your next contributions.",

  // What a crash would cost (StressList)
  "method.stress.behavesBefore": "Your portfolio behaves like the profile ",
  "method.stress.sliderBefore": " while your slider is on ",
  "method.stress.movesMore": ": it moves more than what you said you would accept.",
  "method.stress.movesLess": ": it moves less than what you accept.",
  "method.stress.consistent": ", like your slider. Consistent.",
  "method.stress.worstCrisis": "Worst replayed crisis: {label}",
  "method.stress.worstYear": "Worst year ever seen on {label}",
  "method.stress.thisClass": "this class",
  "method.stress.worstYearSub":
    "twelve consecutive months, over the class's full history since 1990",
  "method.stress.worstDrawdown": "Worst fall this basket has been through",
  "method.stress.worstDrawdownSub":
    "from the peak to the next trough, over {history} of history shared by your lines",
  "method.stress.tooShort": " — too short to be compared with the crises above",
  "method.stress.historyAvailable": "the available history",
  "method.stress.historyMonths.one": "{count} month",
  "method.stress.historyMonths.other": "{count} months",
  "method.stress.historyYears.one": "{count} year",
  "method.stress.historyYears.other": "{count} years",
  "method.stress.allCrises": "All {count} replayed crises, one by one",
  "method.stress.range": "from {from} to {to}",
  "method.stress.dollar":
    "Of which the dollar: {effect} {amount}, that is {pct} on your world funds.",
  "method.stress.dollarGain": "it earned you",
  "method.stress.dollarLoss": "it cost you",
  "method.stress.noteBefore":
    "Crises are replayed on asset classes, not on your lines' own prices: no French ETF has a history before 2009. Each loss is in euros, currency included, and the percentage applies to ",
  "method.stress.noteStrong": "your whole wealth",
  "method.stress.noteAfter":
    ", not just your investments. Your savings accounts do not move and your euro fund does not lose value, only its future rate falls.",
  "method.stress.measured.one":
    "One of your classes is measured on its own daily index, from peak to trough of each episode — ",
  "method.stress.measured.other":
    "{count} of your classes are measured on their own daily index, from peak to trough of each episode — ",
  "method.stress.replayed.one":
    "One of your classes is replayed with the amplitude of world equities, for lack of a series per episode — ",
  "method.stress.replayed.other":
    "{count} of your classes are replayed with the amplitude of world equities, for lack of a series per episode — ",
  "method.stress.replayedAfter":
    ". A sector or regional fund falls harder than the world index: these lines are therefore underestimated here.",
};

export const method = { fr, en };
