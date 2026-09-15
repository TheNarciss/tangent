/** « Placements »: what I hold, advanced mode (metrics, positions, risk/return map, optimiser, correlations, timeline), shared ui atoms. */
const fr = {
  // ── Placements.tsx ────────────────────────────────────────────────────
  "investments.empty.title": "Pas encore de placements",
  "investments.empty.desc":
    "Connecte un compte-titres, un PEA ou une assurance vie pour voir cette page.",
  "investments.unavailable.title": "Analyse indisponible pour l'instant",
  "investments.unavailable.retry": "Réessaie dans un instant.",
  "investments.methodLink": "Ce qu'il faut en faire : risque, frais, doublons, prochain versement.",
  "investments.methodLink.label": "Méthode",
  "investments.whatIHave.title": "Ce que j'ai",
  "investments.whatIHave.sinceBuy": "{gain} depuis l'achat ({pct})",
  "investments.whatIHave.share": "{pct} de tes placements",

  // ── PlacementsAdvanced.tsx ────────────────────────────────────────────
  "investments.advanced.title": "Mode avancé",
  "investments.advanced.sub": "rendement, volatilité, optimiseur, scanner, corrélations",
  "investments.objective.minVariance": "Min variance",
  "investments.objective.fromProfile": "Selon ton profil",
  "investments.objective.fromStrategy": "Selon ma stratégie",
  "investments.objective.targetVol": "Cible vol max",

  // ── Assets.tsx ────────────────────────────────────────────────────────
  "investments.positions.title": "Positions",
  "investments.positions.fund": "Fonds",
  "investments.positions.price": "Cours",
  "investments.positions.weight": "Poids",
  "investments.positions.value": "Valeur",
  "investments.positions.maxDd": "Max DD",

  // ── Correlation.tsx ───────────────────────────────────────────────────
  "investments.correlation.title": "Corrélations",
  "investments.correlation.cellTitle":
    "Corrélation {row} ↔ {col} : ρ = {rho}\n{interp}\n\nρ ∈ [-1, 1]. ≈ 1 : actifs liés (peu de diversification). ≈ 0 : indépendants. ≈ -1 : se hedgent.",
  "investments.correlation.legend": "bleu = hedge · pâle = indépendants · rouge = redondants",
  "investments.correlation.veryStrong": "très forte : bougent presque ensemble",
  "investments.correlation.strong": "forte : tendance commune",
  "investments.correlation.moderate": "modérée",
  "investments.correlation.weak": "faible : quasi-indépendants",
  "investments.correlation.negativeModerate": "négative modérée",
  "investments.correlation.negativeStrong": "négative forte : se compensent",

  // ── Metrics.tsx ───────────────────────────────────────────────────────
  "investments.metrics.value": "Valorisation",
  "investments.metrics.cost": "Coût {value}",
  "investments.metrics.pnl": "Plus-value",
  "investments.metrics.expectedReturn": "E(R) annuel",
  "investments.metrics.expectedReturnSub": "Espérance (μ blendé)",
  "investments.metrics.volatility": "Volatilité σ",
  "investments.metrics.annualised": "Annualisée",
  "investments.metrics.sharpe": "Sharpe",
  "investments.metrics.sharpeSub": "vs. r_f = 2,5 %",
  "investments.metrics.worstDrop": "Pire baisse vécue",
  "investments.metrics.worstDropHint":
    "Plus forte chute entre un plus-haut et le creux suivant, sur l'historique de ton panier",
  "investments.unmapped":
    "Sans hypothèse de rendement long terme, estimé sur l'historique seul : {tickers}.",

  // ── Optimizer.tsx ─────────────────────────────────────────────────────
  "investments.optimizer.title": "Optimisation",
  "investments.optimizer.solver": "Solveur SLSQP long-only, sum(w)=1.",
  "investments.optimizer.desc.fromStrategy":
    "Maximise Sharpe sous tes contraintes σ ≤ vol max ET μ ≥ rendement cible (depuis ton profil). Te dit si ton intention est atteignable.",
  "investments.optimizer.desc.targetVolatility":
    "Maximise μ sous contrainte σ_p ≤ cible. C'est ici que livrets et ETFs se mixent vraiment.",
  "investments.optimizer.desc.minVariance":
    "Minimise σ. Le portefeuille le moins volatil possible, peu importe le rendement.",
  "investments.optimizer.objective": "Objectif",
  "investments.optimizer.maxVol": "σ max (% /an)",
  "investments.optimizer.maxVolHint": "Pré-rempli depuis ton profil. 5 %=prudent · 15 %=actions",
  "investments.optimizer.constraints": "Contraintes (profil)",
  "investments.optimizer.fillProfile": "Renseigne ton profil",
  "investments.optimizer.editProfileHint": "Modifie via l'icône profil en haut",
  "investments.optimizer.includeEnvelopes": "Inclure mes livrets",
  "investments.optimizer.includeHint": "Selon ton profil + plafonds restants",
  "investments.optimizer.fillProfileFirst": "Renseigne ton profil d'abord",
  "investments.optimizer.capital": "Capital total (€)",
  "investments.optimizer.capitalHint": "Pool sur lequel répartir. Défaut = portefeuille actuel",
  "investments.optimizer.running": "Optimisation en cours…",
  "investments.optimizer.error": "Erreur : {error}",
  "investments.toggle.on": "✓ activé",
  "investments.toggle.off": "○ désactivé",
  "investments.compare.metric": "Métrique",
  "investments.compare.current": "Actuel (ETF seuls)",
  "investments.compare.optimal": "Optimal",
  "investments.compare.return": "Rendement μ",
  "investments.actions.title": "Allocation optimale ({capital})",
  "investments.actions.place": "Place {amount}",
  "investments.actions.buy": "Achète {amount}",
  "investments.actions.sell": "Vends {amount}",
  "investments.actions.hold": "Conserve {amount}",
  "investments.kind.envelope": "Livret",
  "investments.kind.etf": "ETF",
  "investments.composition.title": "Composition (poids w)",
  "investments.composition.current": "Actuel",
  "investments.composition.optimal": "Optimal",
  "investments.riskContribution.title": "Contribution à la volatilité σ",
  "investments.euler.before": "Décomposition d'Euler : ",
  "investments.euler.after":
    ". Les livrets contribuent ≈ 0% au risque (σ ≈ 0), même s'ils représentent une part du capital.",
  "investments.riskBar.title": "{label} : {share} du risque total",
  "investments.percent": "{value} %",

  // ── RiskReturn.tsx ────────────────────────────────────────────────────
  "investments.riskReturn.title": "Risque–Rendement",
  "investments.riskReturn.desc":
    "Carte (σ, μ) de ton univers. Touche ou survole un point pour voir ses détails.",
  "investments.riskReturn.aria": "Carte risque-rendement",
  "investments.riskReturn.xAxis": "Volatilité σ (annualisée)",
  "investments.riskReturn.yAxis": "Rendement μ annualisé",
  "investments.riskReturn.envelopesCount": "{count}× livrets",
  "investments.riskReturn.currentPosition": "Position actuelle",
  "investments.riskReturn.legendEnvelopes": "Livrets (σ ≈ 0)",
  "investments.riskReturn.frontier": "Frontière efficiente",
  "investments.riskReturn.envelopes.one": "{count} livret · σ ≈ 0",
  "investments.riskReturn.envelopes.other": "{count} livrets · σ ≈ 0",

  // ── Timeline.tsx ──────────────────────────────────────────────────────
  "investments.timeline.title": "Évolution historique",
  "investments.timeline.desc":
    'Positions actuelles maintenues sur la fenêtre (vue "as-if-held", utile pour les tendances et le risque, pas pour le PnL réel). Touche ou survole un point pour voir tous les chiffres au jour donné.',
  "investments.timeline.portfolio": "Portefeuille",
  "investments.timeline.rebased": "{value} ({delta} %)",
  "investments.timeline.drawdown": "Drawdown",
  "investments.timeline.sharpeWindow": "Sharpe {days}j",
  "investments.timeline.note":
    "Base 100 au {date}. Drawdown = baisse depuis le dernier plus-haut. Sharpe glissant calculé sur {days} jours de bourse (≈ 6 mois).",
  "investments.timeline.backtestNote":
    "Cette courbe applique tes lignes d'aujourd'hui au passé : c'est une simulation de ton allocation actuelle, pas l'historique de ton compte. Le vrai rendement de ton compte est dans Méthode.",
  "investments.timeline.performance": "Performance",
  "investments.timeline.max": "Max : {value}",
  "investments.timeline.rollingSharpe": "Rolling Sharpe ({days}j)",
  "investments.timeline.latest": "Dernier : {value}",
  "investments.timeline.legendPortfolio": "Portefeuille ({value})",
  "investments.timeline.base100": "Base 100 au {date}",

  // ── ui/* atoms ────────────────────────────────────────────────────────
  "investments.ui.confirm": "Valider",
  "investments.ui.clickToEdit": "Cliquer pour modifier",
  "investments.ui.aiEstimate": "Estimation IA, à vérifier",
  "investments.ui.ai": "IA",
  "investments.ui.editedManually": "Modifié manuellement",
  "investments.ui.you": "Vous",
  "investments.ui.close": "Fermer",
};

const en: Record<keyof typeof fr, string> = {
  // ── Placements.tsx ────────────────────────────────────────────────────
  "investments.empty.title": "No investments yet",
  "investments.empty.desc":
    "Connect a securities account, a PEA or a life insurance policy to see this page.",
  "investments.unavailable.title": "Analysis unavailable for now",
  "investments.unavailable.retry": "Try again in a moment.",
  "investments.methodLink": "What to do with it: risk, fees, duplicates, next contribution.",
  "investments.methodLink.label": "Method",
  "investments.whatIHave.title": "What I have",
  "investments.whatIHave.sinceBuy": "{gain} since purchase ({pct})",
  "investments.whatIHave.share": "{pct} of your investments",

  // ── PlacementsAdvanced.tsx ────────────────────────────────────────────
  "investments.advanced.title": "Advanced mode",
  "investments.advanced.sub": "return, volatility, optimiser, scanner, correlations",
  "investments.objective.minVariance": "Min variance",
  "investments.objective.fromProfile": "From your profile",
  "investments.objective.fromStrategy": "From my strategy",
  "investments.objective.targetVol": "Max vol target",

  // ── Assets.tsx ────────────────────────────────────────────────────────
  "investments.positions.title": "Positions",
  "investments.positions.fund": "Fund",
  "investments.positions.price": "Price",
  "investments.positions.weight": "Weight",
  "investments.positions.value": "Value",
  "investments.positions.maxDd": "Max DD",

  // ── Correlation.tsx ───────────────────────────────────────────────────
  "investments.correlation.title": "Correlations",
  "investments.correlation.cellTitle":
    "Correlation {row} ↔ {col}: ρ = {rho}\n{interp}\n\nρ ∈ [-1, 1]. ≈ 1: linked assets (little diversification). ≈ 0: independent. ≈ -1: hedge each other.",
  "investments.correlation.legend": "blue = hedge · pale = independent · red = redundant",
  "investments.correlation.veryStrong": "very strong: move almost together",
  "investments.correlation.strong": "strong: shared trend",
  "investments.correlation.moderate": "moderate",
  "investments.correlation.weak": "weak: nearly independent",
  "investments.correlation.negativeModerate": "moderately negative",
  "investments.correlation.negativeStrong": "strongly negative: offset each other",

  // ── Metrics.tsx ───────────────────────────────────────────────────────
  "investments.metrics.value": "Valuation",
  "investments.metrics.cost": "Cost {value}",
  "investments.metrics.pnl": "Gain",
  "investments.metrics.expectedReturn": "Annual E(R)",
  "investments.metrics.expectedReturnSub": "Expectation (blended μ)",
  "investments.metrics.volatility": "Volatility σ",
  "investments.metrics.annualised": "Annualised",
  "investments.metrics.sharpe": "Sharpe",
  "investments.metrics.sharpeSub": "vs. r_f = 2.5%",
  "investments.metrics.worstDrop": "Worst drop experienced",
  "investments.metrics.worstDropHint":
    "Largest fall from a peak to the following trough, over your basket's history",
  "investments.unmapped":
    "No long-term return assumption, estimated from history alone: {tickers}.",

  // ── Optimizer.tsx ─────────────────────────────────────────────────────
  "investments.optimizer.title": "Optimisation",
  "investments.optimizer.solver": "Long-only SLSQP solver, sum(w)=1.",
  "investments.optimizer.desc.fromStrategy":
    "Maximises Sharpe under your constraints σ ≤ max vol AND μ ≥ target return (from your profile). Tells you whether your intention is achievable.",
  "investments.optimizer.desc.targetVolatility":
    "Maximises μ under the constraint σ_p ≤ target. This is where savings accounts and ETFs really mix.",
  "investments.optimizer.desc.minVariance":
    "Minimises σ. The least volatile portfolio possible, whatever the return.",
  "investments.optimizer.objective": "Objective",
  "investments.optimizer.maxVol": "Max σ (% /yr)",
  "investments.optimizer.maxVolHint": "Pre-filled from your profile. 5%=cautious · 15%=equities",
  "investments.optimizer.constraints": "Constraints (profile)",
  "investments.optimizer.fillProfile": "Fill in your profile",
  "investments.optimizer.editProfileHint": "Edit via the profile icon at the top",
  "investments.optimizer.includeEnvelopes": "Include my savings accounts",
  "investments.optimizer.includeHint": "From your profile + remaining ceilings",
  "investments.optimizer.fillProfileFirst": "Fill in your profile first",
  "investments.optimizer.capital": "Total capital (€)",
  "investments.optimizer.capitalHint": "Pool to spread across. Default = current portfolio",
  "investments.optimizer.running": "Optimising…",
  "investments.optimizer.error": "Error: {error}",
  "investments.toggle.on": "✓ on",
  "investments.toggle.off": "○ off",
  "investments.compare.metric": "Metric",
  "investments.compare.current": "Current (ETFs only)",
  "investments.compare.optimal": "Optimal",
  "investments.compare.return": "Return μ",
  "investments.actions.title": "Optimal allocation ({capital})",
  "investments.actions.place": "Deposit {amount}",
  "investments.actions.buy": "Buy {amount}",
  "investments.actions.sell": "Sell {amount}",
  "investments.actions.hold": "Keep {amount}",
  "investments.kind.envelope": "Savings",
  "investments.kind.etf": "ETF",
  "investments.composition.title": "Composition (weights w)",
  "investments.composition.current": "Current",
  "investments.composition.optimal": "Optimal",
  "investments.riskContribution.title": "Contribution to volatility σ",
  "investments.euler.before": "Euler decomposition: ",
  "investments.euler.after":
    ". Savings accounts contribute ≈ 0% of the risk (σ ≈ 0), even though they make up a share of the capital.",
  "investments.riskBar.title": "{label}: {share} of total risk",
  "investments.percent": "{value}%",

  // ── RiskReturn.tsx ────────────────────────────────────────────────────
  "investments.riskReturn.title": "Risk–Return",
  "investments.riskReturn.desc":
    "(σ, μ) map of your universe. Tap or hover a point to see its details.",
  "investments.riskReturn.aria": "Risk-return map",
  "investments.riskReturn.xAxis": "Volatility σ (annualised)",
  "investments.riskReturn.yAxis": "Annualised return μ",
  "investments.riskReturn.envelopesCount": "{count}× savings accounts",
  "investments.riskReturn.currentPosition": "Current position",
  "investments.riskReturn.legendEnvelopes": "Savings accounts (σ ≈ 0)",
  "investments.riskReturn.frontier": "Efficient frontier",
  "investments.riskReturn.envelopes.one": "{count} savings account · σ ≈ 0",
  "investments.riskReturn.envelopes.other": "{count} savings accounts · σ ≈ 0",

  // ── Timeline.tsx ──────────────────────────────────────────────────────
  "investments.timeline.title": "Historical performance",
  "investments.timeline.desc":
    'Current positions held over the window (an "as-if-held" view, useful for trends and risk, not for actual PnL). Tap or hover a point to see every figure for that day.',
  "investments.timeline.portfolio": "Portfolio",
  "investments.timeline.rebased": "{value} ({delta}%)",
  "investments.timeline.drawdown": "Drawdown",
  "investments.timeline.sharpeWindow": "Sharpe {days}d",
  "investments.timeline.note":
    "Base 100 on {date}. Drawdown = fall from the last peak. Rolling Sharpe computed over {days} trading days (≈ 6 months).",
  "investments.timeline.backtestNote":
    "This curve applies today's holdings to the past: it is a simulation of your current allocation, not your account's history. Your account's real return is in Method.",
  "investments.timeline.performance": "Performance",
  "investments.timeline.max": "Max: {value}",
  "investments.timeline.rollingSharpe": "Rolling Sharpe ({days}d)",
  "investments.timeline.latest": "Latest: {value}",
  "investments.timeline.legendPortfolio": "Portfolio ({value})",
  "investments.timeline.base100": "Base 100 on {date}",

  // ── ui/* atoms ────────────────────────────────────────────────────────
  "investments.ui.confirm": "Confirm",
  "investments.ui.clickToEdit": "Click to edit",
  "investments.ui.aiEstimate": "AI estimate, to be checked",
  "investments.ui.ai": "AI",
  "investments.ui.editedManually": "Edited manually",
  "investments.ui.you": "You",
  "investments.ui.close": "Close",
};

export const investments = { fr, en };
