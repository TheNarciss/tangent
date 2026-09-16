"""HTTP error details and e-mails a person reads."""

FR: dict[str, str] = {
    "errors.no_bank": "Aucune banque connectée.",
    "errors.enablebanking_not_configured": "Enable Banking n'est pas configuré.",
    "errors.llm_budget": "Le budget LLM quotidien est atteint. Réessaye demain.",
    "errors.review_already_today": "Tu as déjà généré une review aujourd'hui. Reviens demain.",
    "errors.leads_not_yet": "Les pistes de marché ne sont pas encore collectées, elles arrivent cette nuit.",
    "errors.reset_code_invalid": "Code invalide ou expiré.",
    "errors.reset_token_invalid": "Token invalide ou expiré.",
    "errors.briefing_admin_only": "Le briefing du matin est réservé aux administrateurs pour l'instant.",
    "email.reset.subject": "Code de réinitialisation — Tangent",
    "email.reset.title": "Réinitialisation de ton mot de passe",
    "email.reset.intro": "Tu as demandé à réinitialiser ton mot de passe Tangent. Voici ton code de vérification :",
    "email.reset.expires_before": "Ce code expire dans ",
    "email.reset.expires_minutes": "{minutes} minutes",
    "email.reset.expires_after": ". Il ne peut être utilisé qu'une seule fois.",
    "email.reset.not_you": "Tu n'as pas demandé ce reset ? Ignore ce mail et change immédiatement ton mot de passe par sécurité.",
    "email.footer": "Tangent · Personal Portfolio Dashboard",
}

EN: dict[str, str] = {
    "errors.no_bank": "No bank connected.",
    "errors.enablebanking_not_configured": "Enable Banking is not configured.",
    "errors.llm_budget": "The daily LLM budget is spent. Try again tomorrow.",
    "errors.review_already_today": "You already generated a briefing today. Come back tomorrow.",
    "errors.leads_not_yet": "Market leads have not been collected yet; they arrive tonight.",
    "errors.reset_code_invalid": "Invalid or expired code.",
    "errors.reset_token_invalid": "Invalid or expired token.",
    "errors.briefing_admin_only": "The morning briefing is reserved to administrators for now.",
    "email.reset.subject": "Reset code — Tangent",
    "email.reset.title": "Resetting your password",
    "email.reset.intro": "You asked to reset your Tangent password. Here is your verification code:",
    "email.reset.expires_before": "This code expires in ",
    "email.reset.expires_minutes": "{minutes} minutes",
    "email.reset.expires_after": ". It can be used only once.",
    "email.reset.not_you": "You did not ask for this reset? Ignore this e-mail and change your password right away, to be safe.",
    "email.footer": "Tangent · Personal Portfolio Dashboard",
}
