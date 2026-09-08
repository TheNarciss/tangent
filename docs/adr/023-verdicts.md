# ADR-023 : Verdicts — un contrat unique du moteur vers l'écran simple, l'onglet Méthode et le briefing

- **Status** : accepted
- **Date** : 2026-09-08
- **Deciders** : Clem

## Contexte

L'étude `docs/ETUDE_METHODE_FINANCIERE_2026-09.md` (§5.3, §8) recense une
vingtaine de techniques institutionnelles à valeur haute pour un épargnant
français, toutes absentes de l'app. Les ajouter une par une dans les écrans
existants produirait ce qu'on a retiré en phase C : des paramètres, des
ratios, des matrices, illisibles pour quelqu'un qui n'a pas de culture
financière. Le briefing IA, lui, reçoit des données brutes et doit refaire
les calculs, ce qui coûte des tokens et produit des chiffres non vérifiés.

## Décision

1. **Le moteur ne livre que des verdicts.** Chaque technique de la méthode
   produit un objet `Verdict` (`app/models.py`) et rien d'autre côté UI :

   | Champ | Rôle |
   |---|---|
   | `id`, `title` | identifiant stable (`fees`, `envelopes`, …) et libellé |
   | `status` | `green` / `amber` / `red` / `unknown` (données manquantes) |
   | `headline` | une phrase en français, tutoiement, pas de jargon |
   | `impact_eur_per_year` | ce que la situation coûte ou rapporte, en euros par an, `null` si sans objet |
   | `action` | une chose à faire, ou `null` si rien à faire |
   | `details` | dict libre pour l'onglet Méthode (décomposition, lignes, hypothèses) |

   Une technique qui ne se traduit pas en euros et en action reste un
   moteur interne et n'a pas de verdict.
2. **Trois consommateurs, une seule source.** `finance/verdicts.py` calcule
   la liste ; `GET /api/verdicts` la sert. L'écran simple concerné
   (Placements, Projection, Comptes) n'affiche que `status` + `headline` ;
   l'onglet **Méthode** affiche chaque verdict en carte repliée, le détail
   n'apparaît qu'au clic ; le briefing reçoit la même liste dans son
   snapshot et se contente de la hiérarchiser et de la dire.
3. **Les seuils sont des valeurs métier versionnées** dans
   `backend/config/verdicts.yaml` (fractions annuelles, date de revue),
   comme `brokers.yaml`, `envelopes.yaml`, `cma.yaml`, `risk_levels.yaml`.
4. **Premier verdict : `fees` (frais réels).** Frais des fonds (TER saisi ou
   résolu par ligne × valeur) + frais du courtier (droits de garde, frais par
   ligne, courtage sur le versement mensuel). Le TER sort de la projection
   (`apply_ter_to_fee_fn` supprimé) : les cours yfinance sont nets de frais
   de fonds, le retrancher une seconde fois sous-estimait le capital final
   (étude §3.1, défaut 2). Le TER est une information de coût, pas un flux
   à simuler.

## Conséquences

### Positives

- Un néophyte lit un feu, une phrase, un montant, une action ; le détail
  existe pour qui le veut, sans polluer l'écran.
- Le briefing ne recalcule rien : moins de tokens, pas de chiffre inventé,
  et il peut devenir événementiel (n'écrire que quand un verdict change).
- Chaque technique de l'étude devient une PR bornée : « ajouter un verdict ».

### Négatives

- `details` est non typé ; chaque carte de l'onglet Méthode connaît la
  forme du sien. Acceptable tant qu'il y a moins d'une dizaine de verdicts.
- Les verdicts sont recalculés à chaque appel (pas de persistance) ; la
  détection de changement de couleur pour le briefing viendra avec un
  stockage dédié si le besoin se confirme.

## Alternatives considérées

### Option A — Un écran par technique

Chaque bloc de l'étude a son onglet avec ses paramètres. Écartée : c'est
l'app d'avant la phase C, et personne ne l'utilisait.

### Option B — Tout dans le briefing, calculé par le LLM

Le modèle reçoit les données brutes et écrit les recommandations. Écartée :
non reproductible, coûteux, et les chiffres ne sont pas vérifiables.

## Notes

- Étude : `docs/ETUDE_METHODE_FINANCIERE_2026-09.md` §8.1 (la méthode en une
  page), §8.2 (valeur de chaque bloc), §3.1 défaut 2 (double compte TER).
- Ordre prévu des verdicts suivants : enveloppes et fiscalité, part risquée
  (Merton), rééquilibrage 5/25, épargne pour l'objectif (problème inverse).
