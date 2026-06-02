"""Version actuelle des CGU/Politique de confidentialité.

Bumpez cette constante quand les pages /legal/terms.html et /legal/privacy.html
changent de manière substantielle. Tous les users existants seront forcés
de re-accepter à leur prochaine connexion (le frontend affiche TermsGate
si user.terms_version_accepted != CURRENT_TERMS_VERSION).

Convention : `YYYY-MM-DD` matchant la "Dernière mise à jour" dans les pages HTML.
"""

CURRENT_TERMS_VERSION = "2026-05-27"
