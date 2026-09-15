/** Words every screen shares: states, buttons, relative time. */
const fr = {
  "common.loading": "Chargement…",
  "common.unknownError": "Erreur inconnue.",
  "common.cancel": "Annuler",
  "common.save": "Enregistrer",
  "common.saved": "Sauvegardé",
  "common.never": "jamais",
  "common.justNow": "à l'instant",
  "common.minutesAgo": "il y a {count} min",
  "common.hoursAgo": "il y a {count} h",
  "common.daysAgo": "il y a {count} j",
  "common.none": "—",
};

const en: Record<keyof typeof fr, string> = {
  "common.loading": "Loading…",
  "common.unknownError": "Unknown error.",
  "common.cancel": "Cancel",
  "common.save": "Save",
  "common.saved": "Saved",
  "common.never": "never",
  "common.justNow": "just now",
  "common.minutesAgo": "{count} min ago",
  "common.hoursAgo": "{count} h ago",
  "common.daysAgo": "{count} d ago",
  "common.none": "—",
};

export const common = { fr, en };
