/** Projection (« si je continue à verser… »), its fan chart, and the « Mon profil » page. */
const fr = {
  // ── Projection (Projection.tsx) ───────────────────────────────────────
  "planning.question.before": "Si je continue à verser ",
  "planning.question.after.one": " par mois pendant {count} an…",
  "planning.question.after.other": " par mois pendant {count} ans…",
  "planning.monthly.label": "Et si je versais… (€ par mois)",
  "planning.monthly.aria": "Versement mensuel",
  "planning.years.label": "Pendant combien d'années",
  "planning.broker.label": "Chez qui tu investis",

  "planning.goal.label": "Mon objectif (optionnel)",
  "planning.goal.modeCapital": "une somme",
  "planning.goal.modeIncome": "un revenu mensuel à vie",
  "planning.goal.capitalPlaceholder": "ex. 25 000",
  "planning.goal.incomeNote":
    "Il faut environ {capital} de capital pour en retirer {income} par mois sans l'épuiser, en retirant {rate} par an : la règle américaine des 4 % ne tient pas sur l'histoire européenne.",

  "planning.figure.inYears.one": "Dans {count} an, environ",
  "planning.figure.inYears.other": "Dans {count} ans, environ",
  "planning.figure.range": "entre {lo} et {hi}, 8 fois sur 10",
  "planning.figure.invested": "Capital de départ + versements",
  "planning.figure.investedSub": "ce que tu auras mis, sans gain ni perte",
  "planning.figure.forIncome": "Pour {income} par mois à vie",
  "planning.figure.goalAmount": "Objectif {amount}",
  "planning.figure.around": "vers {year}",
  "planning.figure.notInHorizon": "pas dans l'horizon",
  "planning.figure.chancesAtEnd.one": "{count} chance sur 10 à la fin",
  "planning.figure.chancesAtEnd.other": "{count} chances sur 10 à la fin",
  "planning.figure.chancesIn.one": "{count} chance sur 10 d'y être dans {years} ans",
  "planning.figure.chancesIn.other": "{count} chances sur 10 d'y être dans {years} ans",
  "planning.figure.forChances": "Pour {chances}",
  "planning.figure.required": "Versement requis",
  "planning.figure.perMonth": "{amount}/mois",
  "planning.figure.outOfReach": "hors de portée",
  "planning.figure.requiredSub": "le versement qu'il faudrait, frais compris",
  "planning.figure.outOfReachSub": "vise moins haut, ou plus loin",
  "planning.figure.goal": "Objectif",
  "planning.figure.noGoalSub": "Indique un objectif pour savoir quand tu l'atteins",

  "planning.chances.of.one": "{count} chance sur {d}",
  "planning.chances.of.other": "{count} chances sur {d}",
  "planning.chances.pct": "{pct} de chances",
  "planning.chances.of10.one": "{count} chance sur 10",
  "planning.chances.of10.other": "{count} chances sur 10",

  "planning.fees.at": "Chez ",
  "planning.fees.costAbout": ", les frais te coûtent environ ",
  "planning.fees.overPeriod": " sur la période",
  "planning.fees.altAt": " · chez ",
  "planning.fees.altAbout": ", environ ",
  "planning.fees.note":
    "Frais de courtage et de tenue de compte, plus ce qu'ils t'auraient rapporté s'ils étaient restés investis",
  "planning.fees.noteTer": ", frais des fonds ({ter}/an) déjà dans les cours",

  "planning.error.emptyTitle": "Pas encore de placements à projeter",
  "planning.error.title": "Projection indisponible",
  "planning.error.emptyBody":
    "Connecte un compte-titres, un PEA ou une assurance vie : la projection part de ce que tu détiens.",
  "planning.error.retry": "Réessaie dans un instant.",

  "planning.how.title": "Comment c'est calculé ?",
  "planning.how.returns":
    "Le rendement et l'amplitude des variations viennent de l'historique de tes fonds sur 5 ans : rendement annuel estimé {ret}, variations annuelles de {vol}.",
  "planning.how.monteCarlo":
    "On simule 1 000 trajectoires possibles (Monte-Carlo), en tenant compte de l'incertitude sur le rendement estimé lui-même : 5 ans d'historique, c'est peu. « Le plus probable » est la médiane ; la « zone probable » va du 10ᵉ au 90ᵉ centile, donc 8 trajectoires sur 10 finissent dedans.",
  "planning.how.fees":
    "Les frais de courtage et de tenue de compte sont prélevés mois par mois, donc ils se cumulent. Sans aucun frais, la médiane serait de {gross} au lieu de {net}.",
  "planning.how.inflation":
    "Tous les montants sont en euros d'aujourd'hui : la simulation tourne en euros courants puis les ramène au pouvoir d'achat actuel, à {inflation} d'inflation par an. Un capital de {median} dans {years} ans, c'est ce que {median} achètent aujourd'hui.",
  "planning.how.tax":
    "L'impôt n'est pas déduit des courbes : il n'est dû qu'à la sortie, et seulement sur les gains. Au taux de tes enveloppes ({rate} en moyenne), il resterait environ {afterTax} après impôt sur la médiane.",

  // ── Fan chart (ProjectionChart.tsx) ───────────────────────────────────
  "planning.chart.aria": "Projection de ton épargne",
  "planning.chart.goalLine": "Objectif {amount}",
  "planning.chart.legendBand": "zone probable (8 fois sur 10)",
  "planning.chart.legendMedian": "le plus probable",
  "planning.chart.legendInvested": "ce que tu auras versé",
  "planning.chart.legendGoal": "ton objectif",
  "planning.chart.inMonths.one": "Dans {count} mois",
  "planning.chart.inMonths.other": "Dans {count} mois",
  "planning.chart.median": "Le plus probable",
  "planning.chart.band": "Zone probable",
  "planning.chart.invested": "Versé",
  "planning.chart.goalReached": "Objectif atteint",

  // ── Mon profil (Profile.tsx) ──────────────────────────────────────────
  "planning.profile.birth.title": "1 · Ta date de naissance",
  "planning.profile.birth.description":
    "Ton âge conditionne les livrets auxquels tu as droit et l'horizon de tes placements.",
  "planning.profile.birth.label": "Date de naissance",
  "planning.profile.birth.age.one": "{count} an",
  "planning.profile.birth.age.other": "{count} ans",
  "planning.profile.birth.required": "Obligatoire pour enregistrer",

  "planning.profile.household.title": "2 · Ton foyer",
  "planning.profile.household.description":
    "Sert à calculer tes parts fiscales, et donc les plafonds de revenu des livrets (LEP).",
  "planning.profile.household.status": "Situation",
  "planning.profile.household.single": "Célibataire",
  "planning.profile.household.couple": "En couple (marié·e ou pacsé·e)",
  "planning.profile.household.children": "Enfants à charge",
  "planning.profile.household.shares.one": "= {shares} part fiscale",
  "planning.profile.household.shares.other": "= {shares} parts fiscales",

  "planning.profile.rfr.title": "3 · Ton revenu fiscal de référence",
  "planning.profile.rfr.description":
    "Il est écrit sur la première page de ton avis d'imposition (« Revenu fiscal de référence »). Prends celui d'il y a deux ans.",
  "planning.profile.rfr.label": "Revenu fiscal de référence (€)",

  "planning.profile.dca.title": "4 · Ce que tu mets de côté chaque mois",
  "planning.profile.dca.description": "Le versement que Tangent utilise pour projeter ton épargne.",
  "planning.profile.dca.label": "Épargne mensuelle (€ / mois)",

  "planning.profile.risk.title": "5 · Prudent ou dynamique ?",
  "planning.profile.risk.description":
    "Plus tu vas vers « dynamique », plus Tangent accepte que ton épargne varie d'une année à l'autre, en échange d'un rendement visé plus élevé.",
  "planning.profile.risk.aria": "Niveau de risque",
  "planning.profile.risk.cautious": "Prudent",
  "planning.profile.risk.dynamic": "Dynamique",
  "planning.profile.risk.level": "Niveau {level}",
  "planning.profile.risk.aimsBefore": "Tangent vise environ ",
  "planning.profile.risk.aimsMiddle": " par an et accepte des variations jusqu'à ",
  "planning.profile.risk.aimsAfter": " sur une année.",

  "planning.profile.livrets.title": "Tes livrets",
  "planning.profile.livrets.synced":
    "Lus automatiquement depuis tes comptes connectés : rien à saisir.",
  "planning.profile.livrets.manual":
    "Aucun livret synchronisé pour l'instant. Si tu en as ailleurs, indique leurs soldes pour que Tangent connaisse ta marge disponible. Laisse à 0 sinon.",
  "planning.profile.livrets.field": "{name} (€)",

  "planning.profile.unsaved": "Modifications non enregistrées",
  "planning.profile.needBirthDate": "Renseigne ta date de naissance pour enregistrer",
};

const en: Record<keyof typeof fr, string> = {
  // ── Projection (Projection.tsx) ───────────────────────────────────────
  "planning.question.before": "If I keep putting in ",
  "planning.question.after.one": " a month for {count} year…",
  "planning.question.after.other": " a month for {count} years…",
  "planning.monthly.label": "What if I put in… (€ a month)",
  "planning.monthly.aria": "Monthly contribution",
  "planning.years.label": "For how many years",
  "planning.broker.label": "Where you invest",

  "planning.goal.label": "My goal (optional)",
  "planning.goal.modeCapital": "a lump sum",
  "planning.goal.modeIncome": "a monthly income for life",
  "planning.goal.capitalPlaceholder": "e.g. 25,000",
  "planning.goal.incomeNote":
    "You need about {capital} of capital to draw {income} a month without running it down, withdrawing {rate} a year: the American 4% rule does not hold up against European history.",

  "planning.figure.inYears.one": "In {count} year, about",
  "planning.figure.inYears.other": "In {count} years, about",
  "planning.figure.range": "between {lo} and {hi}, 8 times out of 10",
  "planning.figure.invested": "Starting capital + contributions",
  "planning.figure.investedSub": "what you will have put in, with no gain or loss",
  "planning.figure.forIncome": "For {income} a month for life",
  "planning.figure.goalAmount": "Goal {amount}",
  "planning.figure.around": "around {year}",
  "planning.figure.notInHorizon": "not within the horizon",
  "planning.figure.chancesAtEnd.one": "{count} chance in 10 at the end",
  "planning.figure.chancesAtEnd.other": "{count} chances in 10 at the end",
  "planning.figure.chancesIn.one": "{count} chance in 10 of being there in {years} years",
  "planning.figure.chancesIn.other": "{count} chances in 10 of being there in {years} years",
  "planning.figure.forChances": "For {chances}",
  "planning.figure.required": "Contribution needed",
  "planning.figure.perMonth": "{amount}/month",
  "planning.figure.outOfReach": "out of reach",
  "planning.figure.requiredSub": "the contribution it would take, fees included",
  "planning.figure.outOfReachSub": "aim lower, or further out",
  "planning.figure.goal": "Goal",
  "planning.figure.noGoalSub": "Set a goal to find out when you reach it",

  "planning.chances.of.one": "{count} chance in {d}",
  "planning.chances.of.other": "{count} chances in {d}",
  "planning.chances.pct": "{pct} chance",
  "planning.chances.of10.one": "{count} chance in 10",
  "planning.chances.of10.other": "{count} chances in 10",

  "planning.fees.at": "At ",
  "planning.fees.costAbout": ", fees cost you about ",
  "planning.fees.overPeriod": " over the period",
  "planning.fees.altAt": " · at ",
  "planning.fees.altAbout": ", about ",
  "planning.fees.note":
    "Brokerage and account-keeping fees, plus what they would have earned had they stayed invested",
  "planning.fees.noteTer": ", fund fees ({ter}/year) already priced in",

  "planning.error.emptyTitle": "No investments to project yet",
  "planning.error.title": "Projection unavailable",
  "planning.error.emptyBody":
    "Connect a brokerage account, a PEA or a life-insurance policy: the projection starts from what you hold.",
  "planning.error.retry": "Try again in a moment.",

  "planning.how.title": "How is this worked out?",
  "planning.how.returns":
    "The return and the size of the swings come from your funds' history over 5 years: estimated annual return {ret}, annual swings of {vol}.",
  "planning.how.monteCarlo":
    "We simulate 1,000 possible paths (Monte Carlo), allowing for the uncertainty in the estimated return itself: 5 years of history is not much. “Most likely” is the median; the “likely range” runs from the 10th to the 90th percentile, so 8 paths out of 10 end up inside it.",
  "planning.how.fees":
    "Brokerage and account-keeping fees are taken month by month, so they add up. With no fees at all, the median would be {gross} instead of {net}.",
  "planning.how.inflation":
    "All amounts are in today's euros: the simulation runs in nominal euros, then brings them back to today's purchasing power, at {inflation} inflation a year. A capital of {median} in {years} years is what {median} buys today.",
  "planning.how.tax":
    "Tax is not deducted from the curves: it is only due on the way out, and only on the gains. At your wrappers' rate ({rate} on average), about {afterTax} would be left after tax on the median.",

  // ── Fan chart (ProjectionChart.tsx) ───────────────────────────────────
  "planning.chart.aria": "Projection of your savings",
  "planning.chart.goalLine": "Goal {amount}",
  "planning.chart.legendBand": "likely range (8 times out of 10)",
  "planning.chart.legendMedian": "most likely",
  "planning.chart.legendInvested": "what you will have put in",
  "planning.chart.legendGoal": "your goal",
  "planning.chart.inMonths.one": "In {count} month",
  "planning.chart.inMonths.other": "In {count} months",
  "planning.chart.median": "Most likely",
  "planning.chart.band": "Likely range",
  "planning.chart.invested": "Put in",
  "planning.chart.goalReached": "Goal reached",

  // ── Mon profil (Profile.tsx) ──────────────────────────────────────────
  "planning.profile.birth.title": "1 · Your date of birth",
  "planning.profile.birth.description":
    "Your age determines which savings accounts you are entitled to and the horizon of your investments.",
  "planning.profile.birth.label": "Date of birth",
  "planning.profile.birth.age.one": "{count} year old",
  "planning.profile.birth.age.other": "{count} years old",
  "planning.profile.birth.required": "Required to save",

  "planning.profile.household.title": "2 · Your household",
  "planning.profile.household.description":
    "Used to work out your tax shares, and so the income ceilings of regulated savings accounts (LEP).",
  "planning.profile.household.status": "Status",
  "planning.profile.household.single": "Single",
  "planning.profile.household.couple": "In a couple (married or civil partnership)",
  "planning.profile.household.children": "Dependent children",
  "planning.profile.household.shares.one": "= {shares} tax share",
  "planning.profile.household.shares.other": "= {shares} tax shares",

  "planning.profile.rfr.title": "3 · Your reference taxable income",
  "planning.profile.rfr.description":
    "It is printed on the first page of your tax notice (« Revenu fiscal de référence »). Use the one from two years ago.",
  "planning.profile.rfr.label": "Reference taxable income (€)",

  "planning.profile.dca.title": "4 · What you set aside each month",
  "planning.profile.dca.description": "The contribution Tangent uses to project your savings.",
  "planning.profile.dca.label": "Monthly savings (€ / month)",

  "planning.profile.risk.title": "5 · Cautious or dynamic?",
  "planning.profile.risk.description":
    "The further you go towards “dynamic”, the more Tangent accepts that your savings vary from one year to the next, in exchange for a higher target return.",
  "planning.profile.risk.aria": "Risk level",
  "planning.profile.risk.cautious": "Cautious",
  "planning.profile.risk.dynamic": "Dynamic",
  "planning.profile.risk.level": "Level {level}",
  "planning.profile.risk.aimsBefore": "Tangent aims for about ",
  "planning.profile.risk.aimsMiddle": " a year and accepts swings of up to ",
  "planning.profile.risk.aimsAfter": " in a single year.",

  "planning.profile.livrets.title": "Your savings accounts",
  "planning.profile.livrets.synced":
    "Read automatically from your connected accounts: nothing to enter.",
  "planning.profile.livrets.manual":
    "No savings account synced yet. If you have some elsewhere, enter their balances so Tangent knows how much room you have left. Otherwise leave at 0.",
  "planning.profile.livrets.field": "{name} (€)",

  "planning.profile.unsaved": "Unsaved changes",
  "planning.profile.needBirthDate": "Enter your date of birth to save",
};

export const planning = { fr, en };
