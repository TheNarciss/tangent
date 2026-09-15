/** Plumbing the user still reads: OAuth and bank callbacks, the Face ID gate, API errors. */
const fr = {
  "system.eb.noLinkedAccounts":
    "La banque a répondu, mais aucun de ses comptes n'est lié à l'application dans la console Enable Banking.",
  "system.eb.session": "Enable Banking n'a pas pu ouvrir la session. Réessaie.",
  "system.eb.badState": "Le retour de la banque n'a pas pu être vérifié. Réessaie.",
  "system.eb.wrongUser": "Le retour de la banque concerne un autre compte Tangent.",
  "system.eb.encryptionNotConfigured":
    "Le serveur ne peut pas chiffrer la session (clé manquante).",
  "system.eb.failed": "La connexion à la banque a échoué ({reason}).",

  "system.powens.firstSyncFailed":
    "Banque ajoutée, mais la première récupération des comptes a échoué. Réessaie avec « Mettre à jour ».",
  "system.powens.failed": "La connexion à la banque a échoué ({reason}). Réessaie.",

  "system.oauth.failed":
    "Connexion échouée ({code}). Réessaie, ou contacte le support si le problème persiste.",

  "system.gate.unlockReason": "Déverrouiller Tangent",
  "system.gate.locked": "Tangent est verrouillé",
  "system.gate.protects": "Face ID ou ton code protège ton patrimoine.",
  "system.gate.checking": "Vérification…",
  "system.gate.unlock": "Déverrouiller",

  "system.session.failed": "Connexion échouée ({error}).",
  "system.session.restart": "Connexion à reprendre depuis le début.",
  "system.flows.unexpectedReturn": "Retour inattendu du navigateur.",

  "system.api.appleStartFailed": "Impossible de démarrer la connexion Apple.",
  "system.api.googleStartFailed": "Impossible de démarrer l'authentification Google.",
  "system.api.googleLinkFailed": "Impossible de lier le compte Google.",
  "system.api.reviewFailed": "La génération a échoué ({reason}).",
};

const en: Record<keyof typeof fr, string> = {
  "system.eb.noLinkedAccounts":
    "The bank answered, but none of its accounts is linked to the application in the Enable Banking console.",
  "system.eb.session": "Enable Banking could not open the session. Try again.",
  "system.eb.badState": "The bank's response could not be verified. Try again.",
  "system.eb.wrongUser": "The bank's response belongs to another Tangent account.",
  "system.eb.encryptionNotConfigured": "The server cannot encrypt the session (missing key).",
  "system.eb.failed": "The bank connection failed ({reason}).",

  "system.powens.firstSyncFailed":
    "Bank added, but the first retrieval of the accounts failed. Try again with “Update”.",
  "system.powens.failed": "The bank connection failed ({reason}). Try again.",

  "system.oauth.failed":
    "Sign-in failed ({code}). Try again, or contact support if the problem persists.",

  "system.gate.unlockReason": "Unlock Tangent",
  "system.gate.locked": "Tangent is locked",
  "system.gate.protects": "Face ID or your passcode protects your wealth.",
  "system.gate.checking": "Checking…",
  "system.gate.unlock": "Unlock",

  "system.session.failed": "Sign-in failed ({error}).",
  "system.session.restart": "Sign-in must be started again from the beginning.",
  "system.flows.unexpectedReturn": "Unexpected return from the browser.",

  "system.api.appleStartFailed": "Could not start the Apple sign-in.",
  "system.api.googleStartFailed": "Could not start the Google authentication.",
  "system.api.googleLinkFailed": "Could not link the Google account.",
  "system.api.reviewFailed": "The generation failed ({reason}).",
};

export const system = { fr, en };
