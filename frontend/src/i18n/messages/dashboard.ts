/** Aperçu: empty state, KPI strip, sparkline tile, morning briefing tile, recent transactions. */
const fr = {
  "dashboard.welcome": "Bienvenue sur Tangent",
  "dashboard.connectFirst": "Connecte ton premier compte bancaire pour voir ton patrimoine ici.",

  "dashboard.kpi.netWorth": "Patrimoine net",
  "dashboard.kpi.debts": "−{amount} de dettes",
  "dashboard.kpi.cash": "Cash",
  "dashboard.kpi.investments": "Investissements",
  "dashboard.kpi.pnl": "{amount} P&L latent",

  "dashboard.chart.title": "Évolution",
  "dashboard.chart.noHistory":
    "Pas encore d'historique — il apparaîtra dès qu'un compte d'investissement sera synchronisé.",
  "dashboard.chart.titleDays.one": "Évolution · {count} jour",
  "dashboard.chart.titleDays.other": "Évolution · {count} jours",
  "dashboard.chart.percent": "{value} %",
  "dashboard.chart.seeDetail": "Voir le détail →",
  "dashboard.chart.sheetTitle": "Évolution du portefeuille",

  "dashboard.briefingTime": "au petit matin, avant 9 h",
  "dashboard.brief.title": "Briefing du matin",
  "dashboard.brief.noneYet":
    "Pas encore de briefing aujourd'hui. Le prochain arrive {time} : ce qui a bougé chez toi, ce que ça veut dire, et s'il y a quelque chose à faire.",
  "dashboard.brief.pitch":
    "Chaque matin, un court texte sur ce qui a bougé dans ton patrimoine et ce que ça veut dire. Rien à lire si rien n'a bougé.",
  "dashboard.brief.enable": "Activer le briefing du matin",
  "dashboard.brief.needProfile": "Renseigne d'abord ton profil pour l'activer.",
  "dashboard.brief.read": "Lire le briefing →",
  "dashboard.brief.today": "Ton briefing du jour",
  "dashboard.brief.dated": "Briefing du {date}",
  "dashboard.brief.previous": "Briefings précédents",

  "dashboard.recent.title": "Mouvements récents",
  "dashboard.recent.seeAll": "Tout voir →",
  "dashboard.recent.empty":
    "Aucun mouvement pour l'instant. Synchronise tes comptes pour voir les transactions.",
};

const en: Record<keyof typeof fr, string> = {
  "dashboard.welcome": "Welcome to Tangent",
  "dashboard.connectFirst": "Connect your first bank account to see your wealth here.",

  "dashboard.kpi.netWorth": "Net worth",
  "dashboard.kpi.debts": "−{amount} of debt",
  "dashboard.kpi.cash": "Cash",
  "dashboard.kpi.investments": "Investments",
  "dashboard.kpi.pnl": "{amount} unrealised P&L",

  "dashboard.chart.title": "Performance",
  "dashboard.chart.noHistory":
    "No history yet — it will appear as soon as an investment account is synced.",
  "dashboard.chart.titleDays.one": "Performance · {count} day",
  "dashboard.chart.titleDays.other": "Performance · {count} days",
  "dashboard.chart.percent": "{value}%",
  "dashboard.chart.seeDetail": "See the details →",
  "dashboard.chart.sheetTitle": "Portfolio performance",

  "dashboard.briefingTime": "early in the morning, before 9 am",
  "dashboard.brief.title": "Morning briefing",
  "dashboard.brief.noneYet":
    "No briefing yet today. The next one arrives {time}: what moved for you, what it means, and whether there is something to do.",
  "dashboard.brief.pitch":
    "Every morning, a short text on what moved in your wealth and what it means. Nothing to read if nothing moved.",
  "dashboard.brief.enable": "Turn on the morning briefing",
  "dashboard.brief.needProfile": "Fill in your profile first to turn it on.",
  "dashboard.brief.read": "Read the briefing →",
  "dashboard.brief.today": "Your briefing for today",
  "dashboard.brief.dated": "Briefing of {date}",
  "dashboard.brief.previous": "Previous briefings",

  "dashboard.recent.title": "Recent transactions",
  "dashboard.recent.seeAll": "See all →",
  "dashboard.recent.empty": "No transactions yet. Sync your accounts to see them.",
};

export const dashboard = { fr, en };
