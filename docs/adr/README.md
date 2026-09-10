# Architecture Decision Records (ADRs)

Ce dossier contient les décisions techniques structurantes du projet Tangent.

## Pourquoi des ADRs ?

Un ADR (Architecture Decision Record) trace **une décision** technique : son contexte, le choix retenu, ses conséquences, et les alternatives écartées. C'est un format léger qui permet :

- de comprendre **pourquoi** le code est comme il est (pas juste comment)
- d'éviter de re-débattre des décisions déjà prises
- d'onboarder rapidement de nouveaux contributeurs (et soi-même dans 6 mois)
- de faire évoluer les décisions explicitement, pas par accident

## Format

Format MADR (Markdown ADR), [adr.github.io/madr](https://adr.github.io/madr/).
Template : [`TEMPLATE.md`](./TEMPLATE.md).

## Index

| # | Titre | Status |
|---|-------|--------|
| [001](./001-stack-technique.md) | Stack technique | accepted |
| [002](./002-multi-tenancy.md) | Stratégie multi-tenant | accepted |
| [003](./003-authentication.md) | Authentification utilisateur | accepted |
| [004](./004-secrets-management.md) | Gestion des secrets | accepted |
| [005](./005-deployment-topology.md) | Topologie de déploiement | accepted |
| [006](./006-persistent-storage.md) | Persistence & backups | accepted |
| [007](./007-frontend-state.md) | State management frontend | accepted |
| [008](./008-powens-aggregator.md) | Powens comme aggregateur bancaire | accepted |
| [009](./009-repository-structure.md) | Structure du repository | accepted |
| [010](./010-logging-observability.md) | Logging et observabilité | accepted |
| [011](./011-password-reset.md) | Flow de reset de mot de passe | accepted |
| [012](./012-token-encryption.md) | Chiffrement des tokens au repos | accepted |

## Workflow

1. Identifier une décision technique structurante
2. Copier `TEMPLATE.md` → `NNN-titre-court.md` (NNN = numéro suivant)
3. Remplir le contenu
4. Status `proposed` au début, `accepted` après validation
5. Pour modifier une décision : créer un nouvel ADR `accepted` qui **supersède** l'ancien (mettre l'ancien en `superseded`)

## Règles

- 1 ADR = 1 décision
- Court (1 page max), pas un dossier d'architecture complet
- Présent simple, voix active, ton décisif
- Pas de "il faudrait" / "on pourrait" → décide ou ne décide pas

- [ADR-021](021-universal-gap-filler.md) — Universal Gap-Filler for nullable provider fields
- [ADR-022](022-profile-v2-risk-slider.md) — Profil v2 : cinq questions, curseur de risque en YAML, DB source de vérité
- [ADR-023](023-verdicts.md) — Verdicts : un contrat unique du moteur vers l'écran simple, l'onglet Méthode et le briefing
- [ADR-024](024-external-data-sources.md) — Sources de vérité externes dans `app/data`
- [ADR-025](025-instrument-classification.md) — Ce qu'est un instrument, décidé sur son nom officiel
- [ADR-026](026-macro-observed.md) — Taux sans risque et inflation deviennent des valeurs observées
- [ADR-027](027-assumptions-follow-the-class.md) — Les hypothèses suivent la classe d'actifs, plus le ticker
- [ADR-028](028-one-voice-per-question.md) — Une seule voix par question, un seul sujet par écran
- [ADR-029](029-measure-the-episodes.md) — Mesurer les crises sur un indice, plutôt que recopier des chiffres
- [ADR-030](030-the-finest-series-that-exists.md) — Chercher la série la plus fine qui existe, sans table tenue à la main
