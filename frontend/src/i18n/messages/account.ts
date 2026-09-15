/** « Mon compte »: email, language, password, linked accounts, briefing, export, admin, danger zone. */
const fr = {
  "account.email.title": "Email",
  "account.email.desc": "Identifiant principal de ton compte.",
  "account.admin": "Admin",

  "account.language.title": "Langue",
  "account.language.desc":
    "Par défaut, Tangent suit la langue du navigateur ou du téléphone. Le choix vaut pour cet appareil.",
  "account.language.auto": "Automatique",
  "account.language.autoHint": "suit l'appareil : {language}",
  "account.language.fr": "Français",
  "account.language.en": "English",

  "account.password.title": "Mot de passe",
  "account.password.desc":
    "Le mot de passe est haché avec Argon2id. Jamais lisible, même par l'administrateur.",
  "account.password.change": "Changer mon mot de passe",
  "account.password.none":
    "Tu te connectes uniquement via Google ou Apple. Aucun mot de passe défini sur ce compte.",
  "account.password.dialogDesc":
    "Renseigne ton mot de passe actuel pour confirmer ton identité, puis choisis-en un nouveau (8 caractères minimum).",
  "account.password.current": "Mot de passe actuel",
  "account.password.new": "Nouveau mot de passe",
  "account.password.confirmNew": "Confirme le nouveau mot de passe",
  "account.password.updated": "Mot de passe mis à jour.",
  "account.password.tooShort": "Le nouveau mot de passe doit faire au moins 8 caractères.",
  "account.password.differ": "Les mots de passe ne correspondent pas.",
  "account.password.sameAsOld": "Le nouveau mot de passe doit différer de l'ancien.",

  "account.oauth.title": "Comptes liés",
  "account.oauth.desc": "Comptes externes que tu peux utiliser pour te connecter à Tangent.",
  "account.oauth.loadFailed": "Impossible de charger les comptes liés.",
  "account.oauth.none": "Aucun compte externe lié pour l'instant.",
  "account.oauth.unlink": "Délier",
  "account.oauth.unlinkNamed": "Délier {provider}",
  "account.oauth.unlinkBlocked":
    "Définis d'abord un mot de passe — sinon tu perdrais l'accès à ton compte",
  "account.oauth.unlinkTitle": "Délier {provider} ?",
  "account.oauth.unlinkDesc":
    "Tu ne pourras plus utiliser {provider} pour te connecter. Ton compte Tangent reste actif via ton email et ton mot de passe.",

  "account.briefing.title": "Briefing du matin",
  "account.briefing.desc":
    "Chaque matin ({time}), un court texte sur ce qui a bougé dans ton patrimoine, ce que ça veut dire et s'il y a quelque chose à faire. Écrit par une IA à partir de tes comptes ; activable et désactivable à tout moment.",
  "account.briefing.receive": "Recevoir le briefing du matin",
  "account.briefing.on": "Activé — ton briefing t'attend chaque matin sur l'Aperçu.",
  "account.briefing.off": "Désactivé — active pour recevoir ton premier briefing demain matin.",

  "account.export.title": "Exporter mes données",
  "account.export.desc":
    "Tout ce que Tangent sait et calcule sur ton compte, en un fichier JSON : comptes, lignes, verdicts, stress tests, projection, les étapes intermédiaires de la méthode et l'archive quotidienne. Utile pour signaler un chiffre qui semble faux.",
  "account.export.preparing": "Préparation…",
  "account.export.download": "Télécharger l'export",
  "account.export.failed": "Export impossible",

  "account.adminSection.title": "Administration",
  "account.adminSection.desc":
    "Tout ce qui appelle le LLM à la demande, pour vérifier sans attendre la nuit. Chaque appel compte dans le budget du jour.",
  "account.adminSection.generating": "Génération, une à deux minutes…",
  "account.adminSection.generate": "Générer mon briefing maintenant",
  "account.adminSection.categorizing": "Catégorisation…",
  "account.adminSection.categorize": "Catégoriser maintenant",
  "account.adminSection.briefReady": "Briefing généré : il t'attend sur l'Aperçu.",
  "account.adminSection.learned.one": "{count} opération catégorisée d'après l'historique",
  "account.adminSection.learned.other": "{count} opérations catégorisées d'après l'historique",
  "account.adminSection.sent.one": " · {count} envoyée au LLM",
  "account.adminSection.sent.other": " · {count} envoyées au LLM",
  "account.adminSection.nothingSent": " · rien à envoyer au LLM",

  "account.danger.title": "Zone dangereuse",
  "account.danger.desc": "Actions irréversibles.",
  "account.danger.delete": "Supprimer mon compte",
  "account.danger.deleteDesc":
    "Efface définitivement ton compte Tangent et toutes les données associées (portfolios, comptes bancaires, transactions, jetons OAuth). Cette action est irréversible et conforme au droit à l'effacement (RGPD).",
  "account.danger.dialogTitle": "Supprimer définitivement mon compte",
  "account.danger.dialogBefore": "Cette action est ",
  "account.danger.irreversible": "irréversible",
  "account.danger.dialogAfter":
    ". Tous tes portfolios, comptes bancaires, transactions et jetons OAuth seront effacés. Aucune sauvegarde n'est conservée.",
  "account.danger.currentPassword": "Mot de passe actuel",
  "account.danger.typeToConfirm": "Tape",
  "account.danger.toConfirm": "pour confirmer",
  "account.danger.deleteForever": "Supprimer définitivement",
};

const en: Record<keyof typeof fr, string> = {
  "account.email.title": "Email",
  "account.email.desc": "The main identifier of your account.",
  "account.admin": "Admin",

  "account.language.title": "Language",
  "account.language.desc":
    "By default Tangent follows the language of the browser or the phone. The choice applies to this device.",
  "account.language.auto": "Automatic",
  "account.language.autoHint": "follows the device: {language}",
  "account.language.fr": "Français",
  "account.language.en": "English",

  "account.password.title": "Password",
  "account.password.desc":
    "The password is hashed with Argon2id. Never readable, not even by the administrator.",
  "account.password.change": "Change my password",
  "account.password.none":
    "You sign in with Google or Apple only. No password is set on this account.",
  "account.password.dialogDesc":
    "Enter your current password to confirm your identity, then choose a new one (8 characters minimum).",
  "account.password.current": "Current password",
  "account.password.new": "New password",
  "account.password.confirmNew": "Confirm the new password",
  "account.password.updated": "Password updated.",
  "account.password.tooShort": "The new password must be at least 8 characters.",
  "account.password.differ": "The passwords do not match.",
  "account.password.sameAsOld": "The new password must differ from the old one.",

  "account.oauth.title": "Linked accounts",
  "account.oauth.desc": "External accounts you can use to sign in to Tangent.",
  "account.oauth.loadFailed": "Could not load the linked accounts.",
  "account.oauth.none": "No external account linked yet.",
  "account.oauth.unlink": "Unlink",
  "account.oauth.unlinkNamed": "Unlink {provider}",
  "account.oauth.unlinkBlocked":
    "Set a password first — otherwise you would lose access to your account",
  "account.oauth.unlinkTitle": "Unlink {provider}?",
  "account.oauth.unlinkDesc":
    "You will no longer be able to sign in with {provider}. Your Tangent account stays active through your email and password.",

  "account.briefing.title": "Morning briefing",
  "account.briefing.desc":
    "Every morning ({time}), a short text on what moved in your wealth, what it means and whether there is something to do. Written by an AI from your accounts; can be turned on and off at any time.",
  "account.briefing.receive": "Receive the morning briefing",
  "account.briefing.on": "On — your briefing waits for you every morning on the Overview.",
  "account.briefing.off": "Off — turn on to receive your first briefing tomorrow morning.",

  "account.export.title": "Export my data",
  "account.export.desc":
    "Everything Tangent knows and computes about your account, in one JSON file: accounts, holdings, verdicts, stress tests, projection, the intermediate steps of the method and the daily archive. Useful to report a number that looks wrong.",
  "account.export.preparing": "Preparing…",
  "account.export.download": "Download the export",
  "account.export.failed": "Export failed",

  "account.adminSection.title": "Administration",
  "account.adminSection.desc":
    "Everything that calls the LLM on demand, to check without waiting for the night. Each call counts against the day's budget.",
  "account.adminSection.generating": "Generating, one to two minutes…",
  "account.adminSection.generate": "Generate my briefing now",
  "account.adminSection.categorizing": "Categorising…",
  "account.adminSection.categorize": "Categorise now",
  "account.adminSection.briefReady": "Briefing generated: it waits for you on the Overview.",
  "account.adminSection.learned.one": "{count} transaction categorised from history",
  "account.adminSection.learned.other": "{count} transactions categorised from history",
  "account.adminSection.sent.one": " · {count} sent to the LLM",
  "account.adminSection.sent.other": " · {count} sent to the LLM",
  "account.adminSection.nothingSent": " · nothing to send to the LLM",

  "account.danger.title": "Danger zone",
  "account.danger.desc": "Irreversible actions.",
  "account.danger.delete": "Delete my account",
  "account.danger.deleteDesc":
    "Permanently erases your Tangent account and all associated data (portfolios, bank accounts, transactions, OAuth tokens). This action is irreversible and complies with the right to erasure (GDPR).",
  "account.danger.dialogTitle": "Permanently delete my account",
  "account.danger.dialogBefore": "This action is ",
  "account.danger.irreversible": "irreversible",
  "account.danger.dialogAfter":
    ". All your portfolios, bank accounts, transactions and OAuth tokens will be erased. No backup is kept.",
  "account.danger.currentPassword": "Current password",
  "account.danger.typeToConfirm": "Type",
  "account.danger.toConfirm": "to confirm",
  "account.danger.deleteForever": "Delete permanently",
};

export const account = { fr, en };
