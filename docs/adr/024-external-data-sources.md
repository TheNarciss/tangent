# ADR-024: Sources de vérité externes dans `app/data`

- **Status** : accepted
- **Date** : 2026-09-09
- **Deciders** : Clem

## Contexte

Plusieurs chiffres affichés à l'utilisateur sont écrits en dur dans le code ou
calibrés sur un seul portefeuille : taux sans risque à 2,5 %, inflation à 2 %,
« une baisse de 30 à 40 % est possible », hypothèses de rendement long terme
listées ticker par ticker pour six ETF, frais du courtier BNP appliqués par
défaut. Aucun de ces chiffres ne se met à jour, et aucun ne se généralise à un
autre portefeuille que celui du premier utilisateur.

Par ailleurs les stress tests ne peuvent pas remonter avant 2009 : aucun ETF
PEA français n'existait, et Yahoo Finance — notre seule source — ne sert que
des cours de fonds.

Il manque une couche qui rassemble les sources publiques, dise ce qu'elles
couvrent réellement et permette de le vérifier.

## Décision

Un package `app/data`, un module par fournisseur, qui renvoie des séries pandas
brutes. Il ne connaît ni utilisateur, ni portefeuille, ni verdict : `app/finance`
décide quoi en faire.

| Module | Fournisseur | Ce qu'on y prend |
|---|---|---|
| `fred` | FRED (Fed St. Louis) | OAT 10 ans, EUR/USD, IPC harmonisé France |
| `ecb` | BCE Data Portal | taux directeur, cours de référence EUR/USD |
| `eurostat` | Eurostat | IPC harmonisé France (contre-expertise) |
| `ken_french` | Kenneth French Data Library | rendements mensuels de marché monde / Europe / US / Japon / émergents, depuis 1990 |
| `lbma` | London Bullion Market Association | fixings or et argent en USD / GBP / EUR, depuis 1968 |
| `openfigi` | OpenFIGI | ISIN → ticker, place, nom |

Trois règles :

1. **Aucune source n'exige de compte ni de clé API.** C'est un critère de
   sélection : une clé est un secret de plus à gérer, à faire tourner et à
   partager avec le runner de déploiement.
2. **Les endpoints et les identifiants de série vivent dans
   `config/data_sources.yaml`**, jamais dans le code Python.
3. **Aucun test n'appelle le réseau.** Les parseurs sont testés sur des
   réponses capturées ; `python -m app.data.probe` vérifie à la demande que
   chaque source répond, depuis quand elle couvre, et **de combien de jours
   elle est en retard**.

Yahoo Finance reste dans `finance/market.py` pour les cours quotidiens : c'est
la seule source qui connaît les fonds de l'utilisateur. `probe` l'interroge
quand même, parce que c'est la plus fragile de toutes.

## Conséquences

### Positives

- Les stress tests peuvent enfin remonter à 1990 sur des rendements réels, par
  région, au lieu de rejouer tout portefeuille en actions monde.
- Taux sans risque et inflation deviennent des observations datées, avec une
  seule source, au lieu de deux constantes dupliquées entre `analytics.py` et
  `verdicts.yaml`.
- OpenFIGI donne un ancrage ISIN → instrument qui ne dépend plus du libellé
  renvoyé par la banque.
- Le retard d'une source devient visible : la sonde a montré qu'Eurostat sert
  un instantané vieux de plusieurs mois là où FRED relaie la même série à jour.

### Négatives

- Cinq dépendances réseau de plus, toutes hors contrat : rien ne nous garantit
  qu'une URL publique ne bougera pas. La sonde est la contre-mesure, pas une
  assurance.
- Ken French publie en **dollar** et en **fin de mois** : convertir en euro
  demande une série de change, et la granularité mensuelle interdit de rejouer
  un krach de trois jours.
- Ken French couvre les actions seulement. L'or vient de la LBMA ; les
  **obligations** et les **fonds euros** n'ont toujours aucune source gratuite
  et non bridée, et restent déclaratifs.
- La LBMA ne publie la jambe euro qu'à partir de 1999 : avant, il faut passer
  par le dollar et une série de change.
- Le cache est en mémoire du process : deux workers font deux appels.

## Alternatives considérées

### Option A — justETF (classification et données de fonds)

Pas d'API officielle ; uniquement des scrapers communautaires. Écartée : une
donnée qui pilote un chiffre affiché ne peut pas dépendre d'un sélecteur HTML.

### Option B — Stooq (séries longues gratuites)

Écartée : protection anti-robot par challenge JavaScript, aucune API documentée.

### Option C — EODHD / Financial Modeling Prep (données de fonds complètes)

Écartée pour l'instant : la composition d'ETF est derrière un palier payant, et
le palier gratuit (20 appels/jour) ne tient pas un seul utilisateur.

### Option D — FRED pour les séries longues d'indices

Écartée : bridées par licence (S&P 500 à 10 ans, ICE BofA à 3 ans). FRED reste
utilisé pour le macro, où il n'y a pas de bridage.

## Notes

- Sonde : `cd backend && python -m app.data.probe`
- Ken French Data Library : <https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html>
- OpenFIGI : 25 requêtes/minute sans clé, 10 ISIN par requête.
- Cet ADR crée la couche. Le branchement des consommateurs (frais, diagnostic,
  stress, CMA) fait l'objet de PR séparées.
