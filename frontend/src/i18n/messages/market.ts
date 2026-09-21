/** Market screens: « La liste de l'année » (Picks), « Pistes de marché » (MarketLeads), the briefing sheet (ReviewSheet). */
const fr = {
  // ── Cours (Quotes.tsx, QuoteChart.tsx) ────────────────────────────────
  "market.quotes.intro":
    "Cherche une action, un fonds ou un indice par son nom ou son symbole. Toucher une ligne de tes comptes ouvre le même graphique.",
  "market.quotes.search.aria": "Chercher un instrument",
  "market.quotes.search.placeholder": "Nom ou symbole, ex. Air Liquide, CW8.PA",
  "market.quotes.search.searching": "Recherche…",
  "market.quotes.search.none": "Rien trouvé sous ce nom.",
  "market.quotes.kind.equity": "Action",
  "market.quotes.kind.etf": "Fonds",
  "market.quotes.kind.index": "Indice",
  "market.quotes.scale.aria": "Échelle de temps",
  "market.quotes.scale.1d": "1J",
  "market.quotes.scale.1w": "1S",
  "market.quotes.scale.1m": "1M",
  "market.quotes.scale.6m": "6M",
  "market.quotes.scale.1y": "1A",
  "market.quotes.scale.5y": "5A",
  "market.quotes.scale.max": "Max",
  "market.quotes.change.day": "aujourd'hui",
  "market.quotes.change.window": "sur la période",
  "market.quotes.aria": "Cours de {symbol}",
  "market.quotes.unavailable":
    "Pas de cours pour cette ligne : Yahoo Finance ne la connaît pas sous ce symbole.",
  "market.quotes.source":
    "Cours Yahoo Finance, différés d'au moins quinze minutes. Ce n'est pas un conseil.",
  "market.quotes.pinch": "Pince le graphique pour changer d'échelle.",
  "market.quotes.open": "Voir le cours",

  // ── La liste de l'année (Picks.tsx) ───────────────────────────────────
  "market.picks.error":
    "La liste ne peut pas être calculée pour l'instant : une source ne répond pas.",
  "market.picks.errorNote":
    "Rien n'est affiché de périmé à la place : la liste est recalculée à chaque fois depuis les positions du jour de l'ETF et les cours du jour.",

  "market.picks.review.monthly": "chaque mois",
  "market.picks.review.quarterly": "chaque trimestre",
  "market.picks.review.annual": "chaque année",

  "market.picks.rule.before": "Les ",
  "market.picks.rule.titles.one": "{count} titre",
  "market.picks.rule.titles.other": "{count} titres",
  "market.picks.rule.middle":
    " qui ont le plus monté sur les douze derniers mois, le dernier mois ignoré, parmi {universe} grandes valeurs européennes cotées en euros. Refait ",
  "market.picks.rule.after":
    ". Ce n'est pas un pronostic : c'est une règle qu'on peut refaire à la main, avec un siècle de preuves derrière elle — et des années à −45 % dedans.",
  "market.picks.rule.satelliteBefore": "À traiter comme un ",
  "market.picks.rule.satellite": "satellite de 10 à 20 % de tes actions",
  "market.picks.rule.satelliteAfter": ", jamais comme le cœur. Le cœur reste l'ETF monde.",
  "market.picks.rule.hide": "Masquer la règle complète",
  "market.picks.rule.show": "Voir la règle complète",
  "market.picks.rule.universe":
    "Univers : les constituants actuels de {indices}, lus à chaque calcul dans les positions du jour de l'ETF qui réplique l'indice. Pour l'essentiel éligibles au PEA.",
  "market.picks.rule.score":
    "Score : rendement de douze mois hors le dernier, divisé par la volatilité — les fusées qui explosent sont écartées.",
  "market.picks.rule.weights": "Poids égaux. Entre deux revues, les poids dérivent avec les cours.",
  "market.picks.rule.brake":
    "Frein : quand l'univers a perdu sur douze mois, la liste est vide et la poche reste en cash jusqu'à la revue suivante. C'est la configuration des krachs de momentum.",
  "market.picks.rule.history":
    "L'historique ci-dessous est calculé sur les constituants d'aujourd'hui : les sortants d'hier manquent, il est donc flatté.",

  "market.picks.index.stoxx_europe_600": "Stoxx Europe 600 (en euros)",
  "market.picks.index.euro_stoxx_50": "Euro Stoxx 50",
  "market.picks.index.dax": "DAX",

  "market.picks.list.title": "La liste au {date}",
  "market.picks.list.nextReview": "prochaine revue le {date}",
  "market.picks.list.new": "nouveau",
  "market.picks.list.entered": "Entrés à cette revue",
  "market.picks.list.left": "Sortis — à vendre",
  "market.picks.list.equalWeight": "À poids égal : chaque titre pèse 1/{count} de la poche.",

  "market.picks.guard.title": "Frein actif au {date}",
  "market.picks.guard.before":
    "L'univers a perdu de la valeur sur les douze derniers mois. C'est dans cette configuration que le momentum se retourne le plus violemment au rebond : la liste est ",
  "market.picks.guard.empty": "vide",
  "market.picks.guard.after": " et la poche reste en cash jusqu'à la prochaine revue, le {date}.",
  "market.picks.guard.toSell": "À vendre : {list}.",

  "market.picks.track.title": "Ce que la règle a fait depuis {year}",
  "market.picks.track.perYear": "Par an, la règle",
  "market.picks.track.universeValue": "univers {value}",
  "market.picks.track.worstFall": "Pire chute",
  "market.picks.track.replaced": "Titres remplacés",
  "market.picks.track.perReview": "par revue",
  "market.picks.track.guardOn": "Frein actif",
  "market.picks.track.reviews": "revues",
  "market.picks.track.rule": "La règle",
  "market.picks.track.universeEqual": "Univers à poids égal",
  "market.picks.track.universe": "Univers",
  "market.picks.track.aria": "Rendement par année",
  "market.picks.track.caption":
    "Rendement de chaque année civile, coûts d'aller-retour déduits pour la règle. Calculé sur les constituants d'aujourd'hui : flatté.",
  "market.picks.track.showTable": "Voir le tableau",
  "market.picks.track.year": "Année",

  "market.picks.plain.title": "En clair",
  "market.picks.plain.do":
    "Concrètement : tu réserves 10 à 20 % de tes actions à cette poche, tu la répartis à parts égales sur les {count} titres ci-dessus, et tu n'y touches plus jusqu'au {date}. Ce jour-là, tu vends ce qui sort, tu achètes ce qui entre, et tu ne cherches pas à comprendre pourquoi : la règle ne le sait pas non plus.",
  "market.picks.plain.doGuarded":
    "Concrètement : aujourd'hui le frein est actif, la liste est vide et la poche reste en cash jusqu'au {date}. Il n'y a rien à acheter, et c'est voulu : c'est dans cette configuration que la méthode a le plus perdu par le passé.",
  "market.picks.plain.pastBefore": "Ce que le passé dit : depuis {year}, ",
  "market.picks.plain.perf.same":
    "la règle a fait {cagr} par an, à peu près comme l'univers à poids égal ({universe})",
  "market.picks.plain.perf.better":
    "la règle a fait {cagr} par an, mieux que l'univers à poids égal ({universe})",
  "market.picks.plain.perf.worse":
    "la règle a fait {cagr} par an, moins que l'univers à poids égal ({universe})",
  "market.picks.plain.pastAfter":
    ". Sa pire chute a été de {drawdown}, contre {universeDrawdown} pour l'univers : c'est là qu'elle sert, plus que dans le rendement. ",
  "market.picks.plain.negativeYears.one":
    "{count} année sur {years} a été négative, la pire à {worst} en {worstYear}.",
  "market.picks.plain.negativeYears.other":
    "{count} années sur {years} ont été négatives, la pire à {worst} en {worstYear}.",
  "market.picks.plain.cost":
    "Ce que ça coûte : environ {turnover} des titres changent à chaque revue. Hors PEA, chaque vente gagnante est imposée ; dans un PEA, seuls les frais de courtage comptent. Le frein a été actif à {guarded} revues sur {reviews}.",
  "market.picks.plain.not":
    "Ce que ce n'est pas : un pronostic ni une promesse. L'historique est calculé sur les constituants d'aujourd'hui, donc flatté, et une année à −45 % reste possible. Si tu ne veux pas t'en occuper à chaque revue, ne prends pas cette poche : l'ETF monde suffit.",

  // ── Pistes de marché (MarketLeads.tsx) ────────────────────────────────
  "market.leads.introBefore": "Chaque nuit, Tangent lit des sources publiques de ce que des gens ",
  "market.leads.introStrong": "font de leur argent",
  "market.leads.introAfter":
    " : les paris qui bougent sur Polymarket et Kalshi, les dirigeants qui achètent l'action de leur propre société, les grands gérants qui ouvrent ou soldent une ligne, les activistes qui déclarent plus de 5 % d'une société, les spéculateurs sur contrats à terme comptés chaque semaine par la CFTC. Tout ce qui dépasse un seuil est ici, sans tri.",
  "market.leads.noise":
    "C'est du bruit pour l'essentiel, et c'est voulu : ton briefing du matin en garde zéro à trois, avec la raison. Une piste est une chose à regarder, jamais un ordre d'acheter ou de vendre.",
  "market.leads.collected.one": "{count} piste collectée {when}.",
  "market.leads.collected.other": "{count} pistes collectées {when}.",
  "market.leads.nextCollection": "Prochaine collecte cette nuit à 02:15.",
  "market.leads.when": "le {date} à {time}",

  "market.leads.filter.all": "Toutes",
  "market.leads.source.polymarket": "Polymarket",
  "market.leads.source.kalshi": "Kalshi",
  "market.leads.source.edgar_form4": "SEC · dirigeants",
  "market.leads.source.edgar_13f": "SEC · gérants",
  "market.leads.source.edgar_13d": "SEC · activistes",
  "market.leads.source.cftc": "CFTC · positions",
  "market.leads.kind.prediction_move": "Cote qui a bougé",
  "market.leads.kind.prediction_state": "État des attentes",
  "market.leads.kind.insider_cluster": "Achats groupés",
  "market.leads.kind.insider_buy": "Gros achat",
  "market.leads.kind.fund_new_position": "Nouvelle ligne",
  "market.leads.kind.fund_exit": "Ligne soldée",
  "market.leads.kind.fund_change": "Ligne modifiée",
  "market.leads.kind.activist_stake": "Plus de 5 %",
  "market.leads.kind.positioning_extreme": "Extrême d'un an",
  "market.leads.kind.positioning_flip": "Changement de camp",

  "market.leads.emptySource":
    "Rien de cette source cette nuit : aucune observation n'a passé les seuils.",
  "market.leads.viewSource": "Voir la source",

  "market.leads.notYet":
    "Les pistes ne sont pas encore collectées : la première lecture part cette nuit à 02:15.",
  "market.leads.unavailable": "Les pistes ne peuvent pas être lues pour l'instant.",
  "market.leads.autoRefresh": "Cette page se rafraîchit toute seule dès que la liste existe.",
  "market.leads.collectStarted": "Collecte lancée, quelques minutes",
  "market.leads.collectNow": "Collecter maintenant",
  "market.leads.unknownError": "Erreur inconnue",

  // ── Briefing sheet (ReviewSheet.tsx) ──────────────────────────────────
  "market.review.sourcesConsulted.one": "{count} source consultée",
  "market.review.sourcesConsulted.other": "{count} sources consultées",
  "market.review.sourcesTitle": "Sources consultées",
};

const en: Record<keyof typeof fr, string> = {
  // ── Prices (Quotes.tsx, QuoteChart.tsx) ───────────────────────────────
  "market.quotes.intro":
    "Search a share, a fund or an index by name or symbol. Tapping a line in your accounts opens the same chart.",
  "market.quotes.search.aria": "Search an instrument",
  "market.quotes.search.placeholder": "Name or symbol, e.g. Air Liquide, CW8.PA",
  "market.quotes.search.searching": "Searching…",
  "market.quotes.search.none": "Nothing found under that name.",
  "market.quotes.kind.equity": "Share",
  "market.quotes.kind.etf": "Fund",
  "market.quotes.kind.index": "Index",
  "market.quotes.scale.aria": "Time scale",
  "market.quotes.scale.1d": "1D",
  "market.quotes.scale.1w": "1W",
  "market.quotes.scale.1m": "1M",
  "market.quotes.scale.6m": "6M",
  "market.quotes.scale.1y": "1Y",
  "market.quotes.scale.5y": "5Y",
  "market.quotes.scale.max": "Max",
  "market.quotes.change.day": "today",
  "market.quotes.change.window": "over the period",
  "market.quotes.aria": "Price of {symbol}",
  "market.quotes.unavailable":
    "No price for this line: Yahoo Finance does not know it under that symbol.",
  "market.quotes.source":
    "Yahoo Finance prices, delayed by at least fifteen minutes. This is not advice.",
  "market.quotes.pinch": "Pinch the chart to change the scale.",
  "market.quotes.open": "See the price",

  // ── The year's list (Picks.tsx) ───────────────────────────────────────
  "market.picks.error": "The list cannot be computed right now: a source is not responding.",
  "market.picks.errorNote":
    "Nothing stale is shown in its place: the list is recomputed every time from the ETF's holdings of the day and the day's prices.",

  "market.picks.review.monthly": "every month",
  "market.picks.review.quarterly": "every quarter",
  "market.picks.review.annual": "every year",

  "market.picks.rule.before": "The ",
  "market.picks.rule.titles.one": "{count} stock",
  "market.picks.rule.titles.other": "{count} stocks",
  "market.picks.rule.middle":
    " that rose the most over the last twelve months, the last month ignored, out of {universe} large European companies quoted in euros. Redone ",
  "market.picks.rule.after":
    ". This is not a forecast: it is a rule you can redo by hand, with a century of evidence behind it — and years at −45% along the way.",
  "market.picks.rule.satelliteBefore": "Treat it as a ",
  "market.picks.rule.satellite": "satellite of 10 to 20% of your equities",
  "market.picks.rule.satelliteAfter": ", never as the core. The core remains the world ETF.",
  "market.picks.rule.hide": "Hide the full rule",
  "market.picks.rule.show": "Show the full rule",
  "market.picks.rule.universe":
    "Universe: the current constituents of {indices}, read at each computation from the day's holdings of the ETF tracking the index. Mostly PEA-eligible.",
  "market.picks.rule.score":
    "Score: twelve-month return excluding the last month, divided by volatility — rockets that blow up are set aside.",
  "market.picks.rule.weights": "Equal weights. Between two reviews, the weights drift with prices.",
  "market.picks.rule.brake":
    "Brake: when the universe has lost ground over twelve months, the list is empty and the sleeve stays in cash until the next review. That is the setting of momentum crashes.",
  "market.picks.rule.history":
    "The track record below is computed on today's constituents: yesterday's leavers are missing, so it is flattered.",

  "market.picks.index.stoxx_europe_600": "Stoxx Europe 600 (in euros)",
  "market.picks.index.euro_stoxx_50": "Euro Stoxx 50",
  "market.picks.index.dax": "DAX",

  "market.picks.list.title": "The list as of {date}",
  "market.picks.list.nextReview": "next review on {date}",
  "market.picks.list.new": "new",
  "market.picks.list.entered": "Entered at this review",
  "market.picks.list.left": "Left — to sell",
  "market.picks.list.equalWeight": "Equal weight: each stock is 1/{count} of the sleeve.",

  "market.picks.guard.title": "Brake on as of {date}",
  "market.picks.guard.before":
    "The universe has lost value over the last twelve months. This is the setting in which momentum reverses most violently on the rebound: the list is ",
  "market.picks.guard.empty": "empty",
  "market.picks.guard.after": " and the sleeve stays in cash until the next review, on {date}.",
  "market.picks.guard.toSell": "To sell: {list}.",

  "market.picks.track.title": "What the rule has done since {year}",
  "market.picks.track.perYear": "Per year, the rule",
  "market.picks.track.universeValue": "universe {value}",
  "market.picks.track.worstFall": "Worst fall",
  "market.picks.track.replaced": "Stocks replaced",
  "market.picks.track.perReview": "per review",
  "market.picks.track.guardOn": "Brake on",
  "market.picks.track.reviews": "reviews",
  "market.picks.track.rule": "The rule",
  "market.picks.track.universeEqual": "Equal-weight universe",
  "market.picks.track.universe": "Universe",
  "market.picks.track.aria": "Return by year",
  "market.picks.track.caption":
    "Return of each calendar year, round-trip costs deducted for the rule. Computed on today's constituents: flattered.",
  "market.picks.track.showTable": "Show the table",
  "market.picks.track.year": "Year",

  "market.picks.plain.title": "In plain terms",
  "market.picks.plain.do":
    "Concretely: you set aside 10 to 20% of your equities for this sleeve, split it equally across the {count} stocks above, and leave it alone until {date}. On that day you sell what leaves, buy what enters, and do not try to understand why: the rule does not know either.",
  "market.picks.plain.doGuarded":
    "Concretely: the brake is on today, the list is empty and the sleeve stays in cash until {date}. There is nothing to buy, and that is the point: this is the configuration in which the method lost the most in the past.",
  "market.picks.plain.pastBefore": "What the past says: since {year}, ",
  "market.picks.plain.perf.same":
    "the rule returned {cagr} a year, about the same as the equal-weight universe ({universe})",
  "market.picks.plain.perf.better":
    "the rule returned {cagr} a year, better than the equal-weight universe ({universe})",
  "market.picks.plain.perf.worse":
    "the rule returned {cagr} a year, less than the equal-weight universe ({universe})",
  "market.picks.plain.pastAfter":
    ". Its worst fall was {drawdown}, against {universeDrawdown} for the universe: that is where it helps, more than in the return. ",
  "market.picks.plain.negativeYears.one":
    "{count} year out of {years} was negative, the worst at {worst} in {worstYear}.",
  "market.picks.plain.negativeYears.other":
    "{count} years out of {years} were negative, the worst at {worst} in {worstYear}.",
  "market.picks.plain.cost":
    "What it costs: about {turnover} of the stocks change at each review. Outside a tax wrapper, every winning sale is taxed; inside one, only brokerage fees count. The brake was on at {guarded} reviews out of {reviews}.",
  "market.picks.plain.not":
    "What it is not: a forecast or a promise. The history is computed on today's constituents, so it is flattered, and a −45% year remains possible. If you do not want to deal with it at every review, skip this sleeve: the world ETF is enough.",

  // ── Market leads (MarketLeads.tsx) ────────────────────────────────────
  "market.leads.introBefore": "Every night, Tangent reads public sources of what people ",
  "market.leads.introStrong": "do with their money",
  "market.leads.introAfter":
    ": the odds moving on Polymarket and Kalshi, the executives buying their own company's shares, the large managers opening or closing a position, the activists declaring more than 5% of a company, the futures speculators counted every week by the CFTC. Everything above a threshold is here, unsorted.",
  "market.leads.noise":
    "Most of it is noise, and that is deliberate: your morning briefing keeps zero to three of them, with the reason. A lead is something to look at, never an order to buy or sell.",
  "market.leads.collected.one": "{count} lead collected {when}.",
  "market.leads.collected.other": "{count} leads collected {when}.",
  "market.leads.nextCollection": "Next collection tonight at 02:15.",
  "market.leads.when": "on {date} at {time}",

  "market.leads.filter.all": "All",
  "market.leads.source.polymarket": "Polymarket",
  "market.leads.source.kalshi": "Kalshi",
  "market.leads.source.edgar_form4": "SEC · insiders",
  "market.leads.source.edgar_13f": "SEC · managers",
  "market.leads.source.edgar_13d": "SEC · activists",
  "market.leads.source.cftc": "CFTC · positioning",
  "market.leads.kind.prediction_move": "Odds that moved",
  "market.leads.kind.prediction_state": "State of expectations",
  "market.leads.kind.insider_cluster": "Cluster of purchases",
  "market.leads.kind.insider_buy": "Large purchase",
  "market.leads.kind.fund_new_position": "New position",
  "market.leads.kind.fund_exit": "Position closed",
  "market.leads.kind.fund_change": "Position changed",
  "market.leads.kind.activist_stake": "Above 5%",
  "market.leads.kind.positioning_extreme": "One-year extreme",
  "market.leads.kind.positioning_flip": "Change of side",

  "market.leads.emptySource":
    "Nothing from this source tonight: no observation passed the thresholds.",
  "market.leads.viewSource": "View the source",

  "market.leads.notYet":
    "The leads have not been collected yet: the first reading starts tonight at 02:15.",
  "market.leads.unavailable": "The leads cannot be read right now.",
  "market.leads.autoRefresh": "This page refreshes by itself as soon as the list exists.",
  "market.leads.collectStarted": "Collection started, a few minutes",
  "market.leads.collectNow": "Collect now",
  "market.leads.unknownError": "Unknown error",

  // ── Briefing sheet (ReviewSheet.tsx) ──────────────────────────────────
  "market.review.sourcesConsulted.one": "{count} source consulted",
  "market.review.sourcesConsulted.other": "{count} sources consulted",
  "market.review.sourcesTitle": "Sources consulted",
};

export const market = { fr, en };
