# ADR-022 : Profil v2 — cinq questions, curseur de risque en YAML, DB source de vérité

- **Status** : accepted
- **Date** : 2026-09-07
- **Deciders** : Clem

## Contexte

Le profil demandait 12 champs dont 4 morts (prénom, TMI, courtier, saisie
manuelle des livrets) et deux paramètres de stratégie en jargon (« rendement
cible », « volatilité max ») que personne ne sait remplir. Les soldes de
livrets étaient retapés à la main alors que Powens les remonte déjà. L'écran
Réglages (shrinkage CMA, estimateur Σ, overrides μ) n'était lu que par le
Scanner. Cf. `docs/ETAT_DES_LIEUX_2026-09.md` §5.5.

## Décision

1. **Le profil tient en cinq questions** : date de naissance, foyer
   (situation + enfants → parts fiscales dérivées côté front, règle du
   quotient familial), revenu fiscal de référence, épargne mensuelle, curseur
   « prudent ↔ dynamique ».
2. **Le curseur est une valeur métier versionnée** dans
   `backend/config/risk_levels.yaml` : chaque cran fixe le couple
   (`target_annual_return`, `max_annual_volatility`) en fractions. Le backend
   dérive ces deux colonnes à chaque `PUT /profile` portant `risk_level` ; le
   frontend lit la liste via `GET /profile/risk-levels` pour libeller le
   curseur. Une seule source de vérité, modifiable sans toucher au code.
3. **La DB est la source de vérité du profil** (`profiles`), le localStorage
   n'est qu'un cache purgé au logout (`profile-sync.ts`). Nouvelles colonnes :
   `risk_level`, `household_status`, `children`, `monthly_dca`.
4. **Les soldes de livrets viennent des comptes synchronisés**
   (`WealthSummary.envelopes`) ; `ceilings_used` ne sert plus que de repli
   manuel quand aucun livret n'est connecté.
5. **L'écran Réglages disparaît** : ses options vivent dans un accordéon
   « Options avancées » du Scanner, seul consommateur.

## Conséquences

- Positives : un néophyte peut remplir le profil sans lexique ; l'optimiseur
  (`from_strategy`) et le briefing IA lisent des contraintes cohérentes avec
  un choix compréhensible ; changer la table de risque = éditer un YAML.
- Négatives : `horizon_years` n'est plus demandé (valeur par défaut 10, lue
  par le briefing) ; l'aperçu « enveloppes éligibles » du profil est retiré,
  l'information reste disponible via l'optimiseur.

## Alternatives écartées

- **Table de risque côté frontend** : plus simple, mais duplique une valeur
  métier hors de `backend/config/` où vivent brokers, enveloppes et CMA.
- **Garder rendement cible / volatilité max en champs libres** : c'est le
  jargon qu'on retire ; un cran = un choix, pas deux nombres.

## Révision 2026-09

Les cinq paires (rendement visé, volatilité max) sont réalignées sur une droite de marché unique (r_f 2,5 %, actions monde 7 % à 15 % de volatilité) : 4 %/5 %, 5 %/8 %, 6 %/12 %, 7 %/16 %, 7,5 %/20 %. Les anciennes valeurs (3 %/5 % … 11 %/22 %) n'étaient sur aucune frontière : le cran 1 faisait moins que le LEP et les crans 4 et 5 étaient inatteignables avec les hypothèses de `cma.yaml`, ce qui faisait échouer l'objectif « selon ton profil ». Voir `docs/ETUDE_METHODE_FINANCIERE_2026-09.md` §3.1, défaut 5.
