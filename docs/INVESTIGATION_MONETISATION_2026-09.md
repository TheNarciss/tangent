# Pourquoi Tangent ne gagne pas d'argent, et ce qu'il manque pour que ça change

Investigation du 7-8 septembre 2026. Périmètre : le dépôt tel qu'il est en prod
(`main` à `11d05ca`), le marché français et européen des apps de patrimoine,
les projets open source comparables, les benchmarks de croissance et de
rétention, la réglementation (AMF, ACPR, DSP2/DSP3, FIDA), les coûts unitaires
(agrégation, données de marché, LLM). Environ 200 recherches et 250 pages
consultées ; les chiffres marqués « ~ » sont approximatifs ou issus d'une seule
source. Les sources sont en fin de document.

---

## 0. Le verdict en une page

**Tangent est un bon projet d'ingénierie et un mauvais produit commercial.**
Ce n'est pas une question de qualité du code ni de finition des écrans (les
phases A, B, C ont réglé l'essentiel). Le problème est structurel, sur cinq
plans, et aucun des cinq ne se règle en ajoutant une fonctionnalité.

| # | Problème | En une phrase | Gravité |
|---|---|---|---|
| 1 | **Pas de distribution** | Aucun canal d'acquisition : pas de page publique, pas de SEO, pas de store, pas d'audience. Un visiteur arrive sur un formulaire de connexion. Le README dit « invitation-only, one user ». | Bloquant |
| 2 | **Mauvaise cible** | « L'épargnant novice » est le segment le plus grand, le moins intentionnel et le moins payeur. Il est servi gratuitement par sa banque, par Finary (2 synchros gratuites), par Bankin'. Finary a eu besoin de 38 M€ et d'une chaîne YouTube à 725 k abonnés pour l'atteindre. | Bloquant |
| 3 | **Pas de « pourquoi pas Finary »** | Le périmètre fonctionnel de Tangent est un sous-ensemble du tier gratuit de Finary, avec la même dépendance Powens et sans app mobile. | Bloquant |
| 4 | **Un produit « vitamine »** | Un tableau de bord ne retient personne (D30 ~5 % pour les apps budget/investissement). Les gens paient pour un résultat chiffré (impôt économisé, frais réduits, argent déplacé), pas pour voir leurs chiffres. Le briefing IA quotidien n'est pas un déclencheur d'achat (50 % refusent de payer pour de l'IA ; Monarch, Copilot, les banques l'offrent déjà). | Fort |
| 5 | **Aucune brique de monétisation** | Zéro code de facturation, zéro analytics produit, zéro suivi d'erreurs, pas de sauvegarde de base, pas d'onboarding, pas de mode démo, pas d'export RGPD alors que la politique de confidentialité le promet. | Fort mais rapide à corriger |

Et un sixième point, souvent sous-estimé : **le modèle B2C « agrégation gratuite »
perd de l'argent par utilisateur** à toute échelle. Mint (25 M d'utilisateurs)
a fermé pour cette raison en 2024. Bankin' (14 ans, 6 M d'utilisateurs)
perdait encore 919 k€ en 2024. Budgea, Linxo, Bridge, Shares ont tous fini en
B2B. Maybe (1,45 M$ levés, 54 k étoiles GitHub) a fermé avec ~200 payants sur
~6 000 nécessaires.

**Conclusion** : il n'y a pas de chemin où Tangent, tel qu'il est positionné,
devient rentable en B2C. Il y a trois chemins crédibles, détaillés en §8 :
(a) une niche à résultat chiffré avec une audience construite avant l'app,
(b) le B2B2C vers les conseillers en gestion de patrimoine (CGP), (c) la
licence du moteur. Je recommande (b), avec (a) comme canal d'acquisition
gratuit.

---

## 1. Où en est Tangent (audit du dépôt)

Faits vérifiés dans le code le 7 septembre 2026.

| Capacité | État | Preuve |
|---|---|---|
| Page publique / marketing | **Absent** | `App.tsx` : non connecté → `AuthScreen` directement |
| SEO, Open Graph, favicon, manifest, PWA, robots, sitemap | **Absent** | `index.html` ne contient que `<title>Tangent</title>` |
| Onboarding, mode démo sans banque | **Absent** | aucun composant ; états vides seulement sur Aperçu et Comptes |
| Inscription, mot de passe oublié, Google OAuth | Présent | `auth/manager.py`, `oauth_router.py` |
| Vérification d'e-mail, lien magique, 2FA | **Absent** | colonne `is_verified` jamais utilisée |
| Suppression de compte (RGPD) | Présent | `routers/account.py` |
| Export des données (RGPD) | **Absent** | promis dans `privacy.html:419`, aucun endpoint |
| Facturation, plans, droits, prix | **Absent** | zéro occurrence ; seul garde-fou : `DAILY_CAP_USD = 5` sur le LLM |
| Analytics produit, Sentry, métriques, alerting | **Absent** | ADR-010 les prévoit, rien d'installé |
| CGU, confidentialité, avertissement « pas un conseil » | Présent | `legal/terms.html`, `TermsGate`, section « # Avertissement » du prompt |
| Avertissement sur Projection / Placements | **Absent** | seulement au TermsGate à l'inscription |
| Agrégation Powens | Présent | `backend/app/powens/` |
| Webhook Powens, synchro planifiée, gestion du renouvellement SCA | **Absent** | webhook no-op ; synchro à la demande ; aucun traitement `actionNeeded` |
| Prix de marché | Partiel | yfinance, cache 1 h en mémoire, perdu au redémarrage |
| Fonds euros, PER, SCPI, immobilier, UC sans ticker | Partiel | solde uniquement ; **exclus** du dashboard, projection, optimiseur, stress |
| Frais et TER dans la projection | Présent | `fees.py`, ADR-021 |
| Inflation, fiscalité (PFU, PEA, abattement AV) | **Absent** | aucun calcul |
| Tests optimiseur / projection / CMA / Bengen / stress | **Absent** | 196 tests backend, aucun sur ces modules |
| Sauvegardes base de données | **Absent** | ADR-006 les prévoit, aucun script |
| Environnement de staging | **Absent** | une VM Oracle gratuite, tunnel Cloudflare |
| Taille | 12 k lignes Python, 10,7 k lignes TS, 70 commits depuis le 30 mai 2026 | |

Lecture : les fondations techniques sont propres (CI, ADR, sécurité, auth) mais
tout ce qui transforme un logiciel en produit vendu est absent. Ce n'est pas
grave en soi : c'est deux à quatre semaines de travail. Ce qui est grave est
que ces semaines ne servent à rien tant que les points 1 à 4 du verdict ne sont
pas tranchés.

---

## 2. Le marché : qui gagne de l'argent, et comment

### 2.1 France et Europe

| App | Cible | Prix | Modèle de revenu | Taille | IA (2025-26) | Point faible connu |
|---|---|---|---|---|---|---|
| **Finary** | Investisseurs 25-45 multi-enveloppes | Gratuit (2 synchros) / Lite 55 €/an / Plus 150 €/an / Pro 350 €/an | Abonnements (~80 % du revenu) + Finary Life (AV 0,5-0,75 %) + crypto (0,99-1,49 %) + Finary One (gestion privée) + courtage PSI (licence ACPR mars 2026) | 850 k utilisateurs, ~50 k payants, >10 M€ ARR, 38 M€ levés, rentable depuis fin 2024 | Chat IA (2023), rachat d'Affluent, « copilote IA » pour le courtage | Connecteurs Powens qui cassent (Trustpilot 3,8), support automatisé, conflit d'intérêts scanner de frais vs Finary Life |
| **Bankin'** | Budget grand public | Gratuit / Plus 40 €/an / Pro 100 €/an | Courtage crédit, cashback, Bridge (B2B) | 6 M utilisateurs, 6,7 M€ CA 2024, **−919 k€** | Catégorisation | Pubs, synchro, pas de vue investissement |
| **Linxo** | Budget | Gratuit / ~30 €/an | Racheté à 85 % par Crédit Agricole ; B2B Linxo Connect | ~3 M (2020) | Aucune | Stagnant |
| **Budgea** (Powens) | — | — | App B2C arrêtée, Powens = B2B pur | — | — | — |
| **Yomoni / Nalo / Ramify / Goodvest / Mon Petit Placement / Cashbee** | Épargnants qui délèguent | 0,5-2 % des encours par an | Frais sur encours (AUM) ; agrégation = produit d'appel | 200 M€ à 2 Md€ d'encours chacun | Ramify lit l'avis d'imposition | Pas des agrégateurs ; ils **achètent** leurs clients (TV, affiliation, 500 € de frais remboursés) |
| **Trade Republic** | Grand public | 1 €/ordre | Spreads, PFOF, intérêts, carte | 10 M utilisateurs, 1,1 M en France, 400 k PEA | Aucune : 1 000 humains 24/7 (avril 2026) | Pas d'agrégation |
| **Invvest** | Stock-pickers | Gratuit / 9,99 €/mois | Abonnement | ~19 k | Aucune | Saisie manuelle |
| **Wealthcome** | **CGP** (B2B) | Sur devis | Abonnement cabinet | 600 cabinets, 4 500 conseillers, 40 Md€ agrégés | — | — |
| **getquin / Parqet / Finanzguru** (DE) | Investisseurs DIY / multibanking | 0 à 150 €/an ; Finanzguru 2,49-4,49 €/mois | Abonnement + conseil humain (getquin 499 €) | 300-350 k chacun ; Finanzguru ~208 k$/semaine de revenu app | Q&R en langage naturel | — |
| **Sumeria, BoursoBank, bunq, Revolut** | Clients bancaires | Inclus | Banque | Millions | Assistants IA lancés en 2026 (SIA, Bourso.IA, Finn, AIR) | — |

### 2.2 États-Unis (références de prix et de modèle)

| App | Prix | Modèle | Taille | Leçon |
|---|---|---|---|---|
| Mint | Gratuit | Pub + lead-gen | 25 M, **fermé mars 2024** | « Une app gratuite de finances perso n'est pas un business viable » (ex-PM Mint) |
| Monarch | 100-199 $/an | Abonnement, pas de gratuit ; B2B2C 14,99 $/client | ~850 M$ de valorisation | Héritier de Mint ; récap hebdo IA |
| Copilot | 95 $/an | Abonnement | ~100 k abonnés, rentable 2023 | Briefing quotidien proactif (avril 2026), serveur MCP |
| YNAB | 109 $/an | Abonnement, vend une **méthode** | ~53 k MAU en Europe | « Le logiciel joue les seconds rôles » |
| Rocket Money | Gratuit / prix libre | 35-60 % des économies négociées | 5-10 M | Paie pour un résultat, pas pour un graphe |
| Cleo | 6-15 $/mois | Chat + avances de trésorerie | 300 M$ ARR | Le chat monétise, mais le revenu vient des avances |
| Kubera | 249 $/an | Abonnement | Niche patrimoines élevés | Import IA de PDF/CSV/captures |
| Origin | 99 $/an | « Conseiller IA régulé SEC » | — | Kitces : le CAC dépasse la LTV à ce prix |

### 2.3 Open source (ce que des solos ont réussi ou raté)

| Projet | Étoiles | Monétisation | Leçon pour Tangent |
|---|---|---|---|
| Maybe | 54 k (archivé) | 15 $/mois → ~200 payants | 18 mois de build avant revenu ; étoiles ≠ clients |
| Actual Budget | 28,6 k | Dons + partage de revenu hébergeur (PikaPods, 8 000 utilisateurs) | Le revenu OSS vient de l'hébergement |
| Firefly III | 24,5 k | Patreon, « side gig » | Un solo tient 10 ans avec un périmètre strict |
| Ghostfolio | 9,3 k | Premium hébergé ~48 $/an | Frère architectural le plus proche ; MCP expérimental |
| Wealthfolio | 8,8 k | **Connect** 8-25 $/mois = synchro courtiers (SnapTrade) | Viral sur « simple, privé, sans abonnement », puis vend la seule chose que le local ne fait pas : la synchro |
| Portfolio Performance | 4,1 k | Dons | Référence pour TWR/IRR, dividendes, import PDF de relevés français |
| Kresus (FR) | 340 | Aucune | L'OSS franco-français ne scale pas |
| ProjectionLab (fermé, solo) | — | 129 $/an sans aucune synchro | On paie pour la **profondeur de planification** (fiscalité, scénarios) |

Deux constantes ressortent de tous les fils HN et Reddit : la fonctionnalité
numéro un demandée est la synchronisation automatique (Tangent l'a déjà), et
le seul modèle solo qui marche est « gratuit et généreux, payant sur une couche
étroite » (synchro, nombre de lignes, export fiscal, planification).

---

## 3. Pourquoi ces apps meurent, et en quoi ça s'applique à Tangent

| Cause | Exemple | Application à Tangent |
|---|---|---|
| Le gratuit avec synchro bancaire coûte de l'argent par utilisateur | Mint, Maybe, Bankin' | Tout tier gratuit avec Powens brûle du cash avant le premier euro ; avec 0 utilisateur c'est théorique, avec 5 000 c'est une facture |
| Liste d'attente ≠ demande ; long build sans contact client | Maybe : 10 k inscrits → 50 payants | Tangent a construit agrégation + analytics + IA avant de vérifier qu'un novice français paierait |
| Les dashboards ne retiennent pas | D30 fintech hors banque ~5 % ; 44 % des abonnés budget encore là à 12 mois | Un novice n'a pas de portefeuille à analyser ; celui qui en a un utilise Finary |
| Les connexions cassent | SCA DSP2 tous les 180 jours ; ~68 % abandonnent plutôt que reconnecter | Tangent ne détecte ni n'affiche les connexions cassées ; pas de synchro planifiée |
| Confiance : un novice ne connecte pas sa banque à un inconnu | HN/IH : « je ne veux pas lier mon compte, tant pis » | Web seulement, pas de marque, pas de store, page d'accueil = login |
| L'IA générique ne fait pas payer | 50 % refusent de payer pour de l'IA ; ChatGPT + Plaid gratuit aux US | « Briefing IA » est une fonctionnalité, pas un produit ; Monarch, Copilot, BoursoBank, Sumeria l'incluent |
| On paie pour un résultat ou une formation | Plan Cash : « les gens paient pour de la formation, pas pour de l'information » ; YNAB vend une méthode | Tangent vend de l'information |
| Saturation, coût de changement nul | « N'importe qui peut vibe-coder une app de finances perso en 2026 » (HN) | Pas de réponse à « pourquoi pas Finary » |
| Le B2C finit en B2B | Budgea → Powens, Linxo → CA, Bankin' → Bridge, Shares → AXA | Le seul débouché fiable de cette techno en France est institutionnel |
| Exposition réglementaire du « conseil » | CIF obligatoire pour toute recommandation personnalisée | Un briefing qui dit « déplace X vers Y » est du conseil en investissement |

---

## 4. Ce qu'il manque, par couche

### 4.1 Distribution (le manque numéro un)

Aucun gagnant français n'a obtenu ses utilisateurs par le produit. Tous
avaient un **actif média** construit avant ou avec l'app.

| Canal | Qui l'a utilisé | Coût | Faisabilité solo |
|---|---|---|---|
| YouTube fondateur | Finary (50 % du revenu corrélé à YouTube), S'investir, ZoneBourse | 2 vidéos/semaine pendant 3 ans | Seulement si tu veux être face caméra 3 ans |
| Newsletter d'abord | Snowball (~70 k), Plan Cash, Cashbee (40 k) | Quasi nul | **Élevée** ; mais monétise par sponsors et formation |
| Simulateurs gratuits (SEO) | Tous les cabinets CGP (EpargneMalin : 52 simulateurs) | Temps de dev | **Élevée** : c'est exactement ta compétence, et leurs simulateurs sont médiocres |
| r/vosfinances (432 k membres) | — | Crédibilité | Moyenne : un outil vraiment utile passe, un post de lancement se fait bannir |
| App Store / Play Store organique | Copilot (« plus gros jour » à la fermeture de Mint) | Gratuit | 84-91 % des installs finance sont organiques : **ne pas être dans le store, c'est ne pas être sur le marché** |
| Affiliation | Yomoni, Nalo, Finary (codes −20 %) | ~50-500 € par compte ouvert | Faible comme acheteur, **possible comme vendeur** |
| Paid social, TV | MPP, Yomoni, Shares | CAC fintech 1 000-1 700 $ | Aucune |
| B2B2C vers CGP | Wealthcome, Manymore, Majors | Temps commercial | **Élevée** : acheteurs avec budget, douleur claire, moitié des cabinets à une personne |
| Licence / white-label | Shares → AXA, Bridge, Linxo Connect | 6-18 mois de cycle | Moyenne : un partenaire de design suffit |

### 4.2 Produit

- **Pas de résultat chiffré.** Tangent montre ; il ne fait rien gagner. Les
  déclencheurs de paiement observés : « ton contrat te coûte X €/an de trop »
  (scanner de frais Finary, motif n° 1 d'abonnement), « verse X € sur ton PER
  avant le 31/12 pour économiser Y € d'impôt », « tu détiens 3 fois le même
  ETF », « ton PEA passe 5 ans le 12 mars ».
- **Pas de fiscalité, pas d'inflation.** La projection ignore le PFU, les
  prélèvements sociaux, l'abattement AV, l'avantage PEA, l'inflation. Pour un
  novice français, la fiscalité est *la* question. OpenFisca-France (API
  publique) couvre tout le code fiscal.
- **Les produits typiquement français sont invisibles.** Fonds euros, UC
  d'assurance-vie, PER, SCPI sont réduits à un solde et exclus de toutes les
  analyses. Or c'est là qu'est le patrimoine financier des Français.
- **Pas d'événements.** Ni détection de connexion cassée, ni drift
  d'allocation, ni dividende reçu, ni taux de fonds euros publié.
- **Le briefing coûte cher pour rien la plupart des nuits.** Estimation :
  ~0,27-0,54 $/utilisateur/mois avec Sonnet (moitié avec l'API Batch), soit
  5-10 % d'un abonnement à 5-10 €/mois, et 100 % de la marge d'un tier
  gratuit, pour dire souvent « rien n'a bougé ».
- **Pas d'app mobile.** iOS n'autorise le push web que si la PWA est
  installée, sans widgets ni synchro en arrière-plan ; Tangent n'a même pas de
  manifest.

### 4.3 Confiance

Page publique, page sécurité (Powens agréé ACPR, lecture seule, chiffrement,
hébergement UE), politique « tes données n'entraînent aucun modèle », page de
statut, changelog, export des données, sauvegardes documentées. Les concurrents
affichent le nom de leur agrégateur certifié SOC 2 (Wealthfolio) ou publient
leurs comptes (Actual).

### 4.4 Données

| Fournisseur | Actions/ETF Euronext | OPCVM / UC par ISIN | Fonds euros / SCPI | Coût |
|---|---|---|---|---|
| yfinance | Oui | Partiel | Non | Gratuit ; **429 fréquents en 2025-26, IP datacenter bloquées, CGU Yahoo interdisent l'usage automatisé** |
| EODHD | Oui | Seulement sur le plan All-in-one 99,99 $/mois | Non | 19,99 $/mois (EOD monde) |
| Twelve Data | Marchés UE dès Pro 99 $/mois | Dès Pro | Non | 29-329 $/mois |
| OpenFIGI | Mapping ISIN → ticker | Oui | — | Gratuit |
| Boursorama / Morningstar (scraping) | Oui | **Oui** | SCPI oui | Gratuit, fragile, zone grise |
| Euronext Web API | Officiel | Fonds cotés | Non | Sur devis |
| **Powens (déjà intégré)** | Valorisation du courtier | **Valorisation de l'assureur** | Solde de l'assureur | Sur devis, B2B, Launchpad −50 % |
| BCE / Banque de France | Taux, change, inflation | — | — | Gratuit |

Le pipeline pratique : ISIN → OpenFIGI → symbole ; si non coté, valorisation
Powens comme prix principal, Boursorama en secours ; tout en base, jamais sur
le chemin de la requête. Aucune API abordable ne cote les UC françaises : c'est
pour ça que Finary stocke la valorisation de l'agrégateur.

### 4.5 Ops et produit

Facturation (Lemon Squeezy ou Paddle en « merchant of record » évite l'OSS TVA
pour une micro-entreprise ; Stripe sinon), Plausible sur le site public,
PostHog ou Sentry dans l'app, sauvegardes `pg_dump` vers B2 (ADR-006),
Postmark pour les e-mails transactionnels, lien magique + passkey, page de
statut. Rien de tout cela n'est difficile ; rien de tout cela n'est fait.

---

## 5. Cadre légal : ce que Tangent peut faire sans statut, et ce qu'il ne peut pas

| Activité | Statut requis | Situation de Tangent |
|---|---|---|
| Agréger des comptes de paiement via Powens (AISP agréé ACPR) | Aucun : Powens porte l'agrément | OK |
| Afficher, calculer, projeter, comparer des frais, expliquer | Aucun (« information à caractère général ») | OK |
| Recommandations **génériques** diffusées de façon impersonnelle | Aucun, si vraiment générique | OK, à condition que le briefing reste descriptif |
| **Recommandation personnalisée** sur un instrument financier (« vends X, achète Y », « ton allocation devrait être ») | **CIF** : examen AMF, adhésion CNCIF/ANACOFI/CNCGP, RC Pro (150 k€ minimum par sinistre), ORIAS, ~450 €/an de contribution AMF plus l'assurance et l'association ; ou PSI | **Zone rouge** : l'optimiseur « selon ton profil » et un briefing qui dit « à faire cette semaine » s'en approchent. Le disclaimer n'immunise pas |
| Percevoir une commission sur un produit souscrit (AV, PER) | Courtier en assurance (COA) pour l'AV/PER, ou apporteur d'affaires avec limites | Non fait |
| Affiliation / parrainage (liens vers Trade Republic, Linxea, etc.) | Aucun statut, mais loi influenceurs 2023, doctrine AMF/ARPP, DGCCRF | Possible ; interdit sur produits blacklistés |
| Gestion sous mandat (robo-advisor) | Société de gestion ou mandat via un PSI | Hors de portée |
| Crypto | MiCA (PSAN) | Non concerné |
| Données bancaires | RGPD : DPIA recommandée, durée de conservation, export | Suppression OK, **export manquant** |

Calendrier réglementaire à connaître : DSP3/PSR adoptés politiquement en
novembre 2025, applicables vers 2027-2028 (consentement 180 → 365 jours, API
dédiées obligatoires, toujours limité aux comptes de paiement). FIDA (open
finance : AV, PER, crédits, assurance) : trilogues bloqués début 2026,
application réaliste 2029 ou après. **Ne pas compter sur des API réglementées
pour l'assurance-vie avant 2029.** Powens et Bridge restent le seul accès, par
connecteurs propriétaires fragiles.

---

## 6. Modèles de monétisation possibles

| Modèle | Prérequis | Revenu réaliste pour un solo | Exemples |
|---|---|---|---|
| Abonnement B2C 40-150 €/an | App mobile, marque, canal d'acquisition, tier gratuit qui coûte | Conversion 2-6 % des inscrits ; il faut ~10 000 inscrits pour 300-600 payants, soit 20-60 k€/an. Sans audience, impossible | Finary, Bankin', Monarch |
| Affiliation (Tangent comme vendeur) | Audience, contenu comparatif, respect AMF | 50-500 € par contrat ouvert ; 20-50 contrats/mois = 1-25 k€/mois **si** on a le trafic | Avenue des Investisseurs, Moneyvox, Finary codes |
| Résultat chiffré payant (audit de frais, optimisation PER) | Pas de statut si générique et pédagogique | Prix à l'acte 9-29 € ou abonnement saisonnier ; virale en novembre-décembre | Scanner de frais Finary (Plus), Rocket Money |
| **B2B2C vers CGP** | Un partenaire de design, marque blanche, ISO d'affichage client | 50-150 €/mois par cabinet ; 5 600 CIF-CGP, moitié en solo, 76 % utilisent déjà un agrégateur, incumbents chers (Harvest) ou de 50 à 900 €/an (Majors, Manymore) ; 50 cabinets = 30-90 k€/an | Wealthcome, Majors, Manymore |
| Licence du moteur (optimiseur, projection, briefing) en API | Démo, un client pilote, présence LinkedIn | 1-5 clients à 10-50 k€/an ; cycle 6-18 mois | Shares → AXA, Bridge |
| Formation / méthode | Audience | Newsletter payante 80 €/an (Snowball+), cours | Plan Cash, YNAB |
| Frais sur encours | CIF ou PSI, capital, conformité | Hors de portée | Yomoni, Nalo |
| Open source + hébergement payant | Communauté, AGPL | Dons + part hébergeur ; quelques centaines d'euros par mois | Actual, Ghostfolio |

---

## 7. Coûts unitaires et prix viable

| Poste | Ordre de grandeur | Source |
|---|---|---|
| Powens | Sur devis, B2B ; −50 % via Launchpad ; les comparables (Plaid PAYG) tournent à ~1,5-2 $/utilisateur connecté/mois | Powens, Plaid |
| Données de marché licenciées | 20-100 $/mois (EODHD) | EODHD |
| Briefing LLM nocturne | 0,14-0,68 $/utilisateur/mois selon modèle et Batch | Tarifs Anthropic septembre 2026, estimation 6 k tokens entrée / 600 sortie |
| Hébergement | 0 € (Oracle Free) ; ~20-50 €/mois pour une VM digne de données financières + sauvegardes | — |
| Merchant of record | 5 % + 0,50 € par transaction | Lemon Squeezy, Paddle |
| Stores | 99 $/an Apple, 25 $ Google, 15-30 % de commission | — |

Conséquence : un utilisateur **gratuit** avec synchro Powens et briefing coûte
~2-3 €/mois. Un abonnement à 5 €/mois ne couvre pas 2 gratuits pour 1 payant.
Le tier gratuit doit donc être **sans synchro** (saisie manuelle, import CSV)
ou limité à un compte, comme Finary (2 synchros) et Wealthfolio (synchro
payante). Le prix viable en B2C est 60-150 €/an, ce qui suppose un patrimoine
> 50 k€, donc pas un novice.

---

## 8. Les trois voies, et ma recommandation

| Voie | Ce que ça veut dire | Pour | Contre | Délai avant le premier euro |
|---|---|---|---|---|
| **A. Niche à résultat chiffré + audience d'abord** | Choisir un problème daté et chiffré (PER avant le 31/12, audit de frais d'AV, suivi SCPI), sortir 3-5 simulateurs publics de qualité, une newsletter, poster sur r/vosfinances ; l'app devient la version « sauvegarde ton scénario » | Compétence dev = avantage réel ; coût nul ; SEO durable ; affiliation possible | 6-12 mois de SEO ; revenu d'abord par affiliation/sponsors, pas par l'app | 6-12 mois |
| **B. B2B2C vers CGP** | Vendre aux cabinets de CGP un portail client marque blanche : vue 360°, projection, briefing mensuel pour leurs 20-120 clients ; le CGP règle le problème de confiance (son client connecte la banque parce que le conseiller le demande) et porte le statut CIF | Acheteurs solvables, douleur explicite (MiFID II, « vue 360° », 82 % veulent de l'IA), cabinets solos joignables par e-mail, incumbents chers ou vieillissants, **résout d'un coup les problèmes 1, 2, 3 et 5** | Vente à faire, contrat Powens B2B à négocier, un pilote à trouver | 3-6 mois |
| **C. Licence du moteur** | Optimiseur, projection, briefing en API pour néobanques, assureurs, éditeurs CGP | Actif déjà construit, pas de B2C | Cycle long, un solo inspire peu confiance à une banque | 6-18 mois |

**Recommandation : B, en utilisant A comme canal d'acquisition.** Les
simulateurs publics amènent à la fois des particuliers (affiliation) et des
CGP (qui cherchent exactement ces outils pour leurs prospects). Le B2C
« épargnant novice » est abandonné comme cible commerciale ; il reste le
bénéficiaire final via le CGP. Le briefing IA reste, mais devient
**événementiel et mensuel**, adressé au client d'un conseiller, avec le
conseiller dans la boucle (ce qui règle aussi la question CIF).

Ce que ça change dans le code, par ordre : multi-tenant cabinet → clients
(la structure multi-tenant existe déjà, ADR-002), marque blanche (logo,
couleurs), vue conseiller (liste de clients, alertes), export PDF de synthèse,
événements déterministes (drift, frais, connexion cassée, PEA 5 ans, plafond
PER), fiscalité via OpenFisca, valorisations Powens des UC stockées en base,
export RGPD, facturation, Sentry, sauvegardes.

---

## 9. Plan 90 jours (si la voie B est retenue)

| Semaine | Livrable | Pourquoi |
|---|---|---|
| 1-2 | 10 entretiens de CGP solos (CNCGP, LinkedIn, cabinets à simulateurs) ; question unique : « que montrez-vous à vos clients entre deux rendez-vous, et combien ça vous coûte ? » | Valider avant de coder (leçon Maybe) |
| 1-2 | Page publique + page sécurité + export RGPD + sauvegardes + Sentry | Hygiène minimale, indépendante de la voie |
| 3-4 | Simulateur public n° 1 : « Combien verser sur mon PER avant le 31 décembre » (OpenFisca), partageable, sans compte | Premier actif SEO, saison novembre-décembre |
| 3-6 | Demande Powens Launchpad avec le cas d'usage CGP ; comparer avec Bridge | Coût d'agrégation connu avant de vendre |
| 5-8 | Vue conseiller + marque blanche + événements déterministes (5 règles) + briefing mensuel client | Le produit pilote |
| 5-8 | Simulateur n° 2 : audit de frais d'assurance-vie (TER + frais de gestion UC vs 0,5 %) | Résultat chiffré, motif n° 1 d'abonnement chez Finary |
| 9-12 | Un cabinet pilote gratuit 3 mois contre retours hebdomadaires ; facturation Lemon Squeezy prête | Premier contrat au jour 90 ou pivot |
| Continu | Un post par semaine sur LinkedIn (CGP) et un outil tous les deux mois sur r/vosfinances | Audience |

Ce qu'on **arrête** : la cible « novice », l'optimiseur comme fonctionnalité
grand public (il reste un moteur interne), le briefing quotidien pour tous, les
écrans supplémentaires en B2C.

---

## 10. Ce que cette investigation ne tranche pas

- Les volumes de recherche français des niches (PER, AV, SCPI) sont des
  estimations ; à vérifier dans Google Keyword Planner avant de choisir le
  premier simulateur.
- Le tarif Powens exact : seul un devis le donne.
- Le nombre d'utilisateurs Finary varie selon la source (600 k à 1 M).
- Le CAC fintech cité est pondéré États-Unis.
- La question ouverte §8.2 de l'état des lieux (μ CMA mixte partout dans la
  projection, double comptage du TER) reste en attente de ta décision ; elle
  est indépendante de tout ce qui précède.

---

## Sources principales

Finary et acteurs français
- https://finary.com/fr/pricing
- https://finary.com/en/product-updates/shareholder-letter-2026
- https://community.finary.com/t/ma-lettre-aux-actionnaires-2025/23042
- https://x.com/moonlaggoune/status/2026922717744918633
- https://fr.wikipedia.org/wiki/Finary et https://fr.wikipedia.org/wiki/Mounir_Laggoune
- https://www.maddyness.com/2025/09/18/la-fintech-finary-leve-25-millions-deuros-avec-paypal-et-y-combinator/
- https://finary.com/en/product-updates/finary-securities-broker-license-psi
- https://parrainduweb.fr/blog/finary-roadmap
- https://fr.trustpilot.com/review/finary.com
- https://www.mind.eu.com/fintech/services-bancaires/bankin-reduit-ses-pertes-en-2024/
- https://support.bankin.com/hc/fr/articles/360006559578-Pr%C3%A9sentation-de-Bankin-Plus
- https://www.frenchweb.fr/rachete-par-le-credit-agricole-comment-linxo-compte-accelerer-dans-lopen-banking/390791
- https://selectra.info/finance/guides/compte-bancaire/comparatif-agregateurs
- https://www.shares.io/about-us
- https://finance-heros.fr/avis-client-yomoni/
- https://www.moneyvox.fr/epargne/ramify
- https://www.cafedelabourse.com/courtier/trade-republic
- https://www.moneyvox.fr/banque-en-ligne/actualites/108411/un-nouveau-service-clients-chez-trade-republic
- https://www.dailytrend.fr/finance/assistants-ia-bancaires-sumeria-boursobank-revolution-2026
- https://www.lafabriquedunet.fr/logiciels/alternatives/alternative-finary

CGP et B2B
- https://www.invest-aide.fr/groupe/metier-cgp/etude-marche-cgp/
- https://haussmann-fusac.fr/ressources/barometre-cncgp-2025-les-chiffres-cles-dune-profession-en-pleine-croissance/
- https://support.majors.finance/ressources/agregateurs-CGP-2026.html
- https://www.professioncgp.com/article/produits-services/logiciels-et-fintechs/manymore-une-vision-a-360deg-de-la-gestion-dun-cabinet.html
- https://www.cgpdistrib.com/content/le-marche-des-logiciels-patrimoniaux-en-pleine-ebullition-5694
- https://www.wealthcome.fr/blog/lagregation-de-donnees
- https://www.epargnemalin.fr/simulateurs/

Échecs et modèles
- https://www.monarch.com/blog/mint-shutting-down
- https://newsletter.failory.com/p/3-reasons-maybe-failed
- https://x.com/Shpigford/status/1947725345244709240
- https://techcrunch.com/2024/03/21/budgeting-app-copilot-mint-6m-series-a/
- https://saasclub.io/podcast/jesse-mecham-ynab/
- https://news.ycombinator.com/item?id=47406569
- https://www.indiehackers.com/post/another-personal-finance-app-thoughts-48f893fd42
- https://www.medianes.org/plan-cash-les-gens-preferent-payer-pour-de-la-formation-plutot-que-pour-de-linformation/
- https://www.kitces.com/blog/the-latest-in-financial-advisortech-october-2025-origin-ai-financial-advisor-low-fee-stockopter-grantd/
- https://www.emarketer.com/content/consumers-unwilling-pay-ai-features-1
- https://sacra.com/c/monarch-money/ et https://sacra.com/c/cleo/
- https://releasebot.io/updates/copilot-money

Benchmarks
- https://www.revenuecat.com/state-of-subscription-apps
- https://www.appsflyer.com/blog/measurement-analytics/european-finance-apps/
- https://uxcam.com/blog/mobile-app-retention-benchmarks/
- https://apsteq.com/blog/app-retention-benchmarks/
- https://mapendo.co/blog/cost-per-install-by-app-category-2025
- https://firstpagesage.com/seo-blog/fintech-cac-benchmarks-report/
- https://sensortower.com/blog/2025-q2-unified-top-5-personal%20finance%20budgeting%20and%20planning-revenue-europe-63e363f0e1714cfff1979caa
- https://www.productgrowth.blog/p/personal-finance-app-user-retention
- https://www.strategia-x.com/blog/2026-04-12-why-budgeting-apps-fail-30-days-fintech-ux-data/
- https://gummysearch.com/r/vosfinances/
- https://snowball.substack.com/about

Réglementation
- https://www.amf-france.org/sites/institutionnel/files/private/2024-02/doc-2008-23_vf4_3.pdf (position AMF DOC-2008-23, conseil en investissement)
- https://www.amf-france.org/en/professionals/other-professionals/financial-investment-advisor-status-fia
- https://academy.invest-aide.fr/blog/devenir-cif/
- https://brokin.fr/rc-pro-cif-orias/
- https://www.professioncgp.com/article/reglementation/conditions-dexercice/les-robo-advisors-face-aux-regulateurs.html
- https://www.cafedelabourse.com/devenir-rentier/finfluenceur-influenceurs-finance
- https://www.eba.europa.eu/publications-and-media/press-releases/eba-consults-amendment-its-technical-standards-strong
- https://plaid.com/blog/180-days-is-not-enough/
- https://www.nortonrosefulbright.com/en/knowledge/publications/cedd39c6/psd3-and-psr-from-provisional-agreement-to-2026-readiness
- https://www.freshfields.com/en/our-thinking/blogs/technology-quotient/risen-from-the-ashes-fida-trilogue-set-to-move-forward-102k3at
- https://www.konsentus.com/fidas-timetable-might-shift-but-the-destination-wont/

Agrégation et données
- https://www.powens.com/fr/startup-program/
- https://www.powens.com/fr/solutions/gestion-patrimoine/
- https://www.bridgeapi.io/solutions/rapprochement-bancaire-automatise-en-continu/service-agregation-de-compte
- https://plaid.com/docs/account/billing/
- https://dev.to/johnfrandsen/the-cheapest-open-banking-apis-for-small-businesses-and-indie-builders-in-2026-5cab
- https://github.com/ranaroussi/yfinance/issues/2480
- https://eodhd.com/pricing
- https://twelvedata.com/pricing
- https://www.openfigi.com/api/documentation
- https://github.com/Mael-J/mstarpy
- https://data.ecb.europa.eu/help/api/overview
- https://help.finary.com/fr/articles/6525549-ajouter-manuellement-mon-contrat-d-assurance-vie
- https://github.com/openfisca/openfisca-france

Open source
- https://github.com/ghostfolio/ghostfolio et https://news.ycombinator.com/item?id=37337482
- https://github.com/maybe-finance/maybe et https://github.com/we-promise/sure
- https://actualbudget.org/blog/roadmap-for-2026/
- https://docs.firefly-iii.org/explanation/support/
- https://github.com/wealthfolio/wealthfolio, https://wealthfolio.app/connect/, https://news.ycombinator.com/item?id=46006016
- https://github.com/portfolio-performance/portfolio
- https://github.com/kresusapp/kresus
- https://projectionlab.com/pricing
- https://github.com/skfolio/skfolio, https://github.com/dcajasn/Riskfolio-Lib, https://github.com/PyPortfolio/PyPortfolioOpt

Technique produit
- https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
- https://capgo.app/blog/transform-pwa-to-native-app-with-capacitor/
- https://stilllater.com/dev-tools/lemonsqueezy-vs-stripe-vs-paddle/
- https://www.buildmvpfast.com/blog/posthog-vs-plausible-vs-fathom-privacy-analytics-saas-2026
- https://www.anthropic.com/news/claude-for-financial-services
