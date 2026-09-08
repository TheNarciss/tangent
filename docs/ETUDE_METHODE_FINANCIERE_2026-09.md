# Pourquoi Tangent ne te fait pas gagner d'argent, et comment les banques construisent une méthode qui en fait gagner

Étude du 8 septembre 2026. Question posée : « pourquoi, en tant qu'utilisateur,
je ne gagne pas d'argent avec cette application ? ». Ce n'est pas une question
de produit ni de vente ; c'est une question de **méthode financière**.

Périmètre : audit mathématique ligne à ligne du moteur de Tangent (`main` à
`3c6bf1f`), la littérature académique sur ce qui fait gagner ou perdre de
l'argent à un particulier, les méthodes publiées des banques, gérants
d'actifs, banques privées et robo-advisors, les projections et simulations
telles que les font les professionnels, et le cursus en ligne (MIT, Yale,
EDHEC, CFA, Roncalli, Bouchaud, blogs quantitatifs, canon français). Environ
350 recherches et 400 documents consultés, dont une quarantaine de PDF
extraits localement (Vanguard, ESMA, AMF, Banque de France, DMS/UBS, JPM,
Amundi, Robeco, AQR, Morningstar, Jordà et al.). Les chiffres marqués « ~ »
sont approximatifs. Les sources sont en fin de document.

---

## 0. La réponse en une page

**Tangent ne te fait pas gagner d'argent parce qu'il n'agit sur aucun des
leviers qui font gagner de l'argent à un épargnant, et parce que le seul
levier sur lequel il agit (répartir 2 à 5 ETF avec un optimiseur de
Markowitz) est à la fois le moins rentable et le plus mal calculé.**

Voici d'où vient l'argent d'un épargnant français sur 20 ans, d'après les
preuves empiriques (détail en §1), et ce que Tangent en fait :

| Levier, par ordre d'importance | Impact sur 100 k€ / 20 ans | Ce que fait Tangent |
|---|---|---|
| 1. Taux d'épargne et durée | 58 % du capital final à 20 ans vient des versements, pas du rendement | Une seule question « combien par mois », rien pour l'augmenter ni l'automatiser |
| 2. Être investi en actions plutôt qu'en fonds euros / livrets | +400 à +600 pb/an, soit +200 à +300 k€ | Rien : 60 % de l'épargne des Français est en produits de taux ; Tangent exclut fonds euros, PER, AV de toutes ses analyses |
| 3. Frais : AV bancaire en UC actives vs PEA + ETF | −200 à −350 pb/an, soit −100 à −150 k€ | Un modèle de frais de courtage, avec le TER compté deux fois et les rétrocessions comptées comme un coût |
| 4. Comportement (changer de fonds, trader, paniquer) | −80 à −700 pb/an | Rien : pas de garde-fous, pas de mesure de l'écart de comportement, un briefing qui incite à « faire quelque chose cette semaine » |
| 5. Enveloppe fiscale : PEA vs CTO vs AV vs PER | −60 à −90 pb/an, soit −30 à −50 k€ ; PER : +3 à +8 k€ par 10 k€ versés au-dessus de la TMI 30 % | **Aucune fiscalité modélisée**, nulle part |
| 6. Diversification mondiale, pas d'actions en direct | La médiane des actions fait moins que le cash (Bessembinder) ; CAC 40 seul = 12 ans de perte 2000-2012 | Un scanner qui propose des **actions individuelles** d'Euronext Paris |
| 7. Rééquilibrage | +12 à +25 pb/an ajustés du risque | Rien |
| 8. Allocation fine entre ETF actions | quelques dizaines de pb, indiscernables du bruit d'estimation | **C'est tout ce que fait Tangent**, avec des erreurs (§3) |
| 9. Règle de retrait à la retraite | 4 % échoue dans plus de la moitié de l'histoire française (Pfau) ; 3 à 3,5 % dynamique | Règle des 4 % de Bengen, américaine, nominale, sans inflation |

Trois conclusions :

1. **L'ordre des leviers est inversé.** Les banques et la recherche commencent
   par le taux d'épargne, l'exposition au risque, les frais, la fiscalité et
   le comportement. L'optimisation fine entre fonds vient en dernier, et les
   praticiens la régularisent lourdement parce qu'elle amplifie les erreurs
   d'estimation (Michaud, Chopra-Ziemba, DeMiguel). Tangent a construit le
   dernier étage sans les huit premiers.
2. **Le moteur est faux là où il compte.** L'audit (§3) relève dix défauts
   classés « trompeurs » : tout ticker inconnu reçoit 7 % de rendement
   attendu avec sa propre volatilité, ce qui fait ranger un fonds monétaire
   comme meilleur actif du monde ; le TER est déduit deux fois ; le stress
   test 2020 applique le rendement d'un panier partiel à tout le capital ; la
   projection utilise la moyenne des 5 dernières années sans inflation ni
   impôt en disant « euros d'aujourd'hui » ; les cinq niveaux de risque ne
   sont sur aucune frontière ; le briefing IA reçoit « objectif 0,07 %/an ».
3. **Une méthode qui fait gagner de l'argent existe, elle est publique, et
   elle tient en une page** (§8). Elle s'appelle, selon les auteurs,
   « Advisor's Alpha » (Vanguard, ~3 %/an dont l'essentiel est
   comportemental et fiscal), « Gamma » (Morningstar, +22,6 % de revenu de
   retraite), ou simplement le consensus r/vosfinances, Épargnant 3.0,
   Bogleheads : épargne automatique, actions monde en PEA, fonds euros en AV
   pour le court terme, PER si TMI ≥ 30 %, frais < 0,5 %, rééquilibrage par
   les versements, ne rien faire d'autre. Un moteur qui fait respecter cette
   méthode, avec de vraies hypothèses de marché, une vraie fiscalité et une
   vraie simulation, vaut 200 à 600 pb/an pour l'épargnant médian. Le
   Markowitz de Tangent en vaut, au mieux, quelques dizaines, et aujourd'hui
   il en coûte.

---

## 1. D'où vient l'argent d'un épargnant : les preuves

Convention : 100 000 € placés 20 ans à 6 % brut nominal donnent 320 714 €.
Chaque 10 pb/an de frottement coûte ~6 000 € de capital final ; 50 pb ~29 k€ ;
100 pb ~55 k€ ; 200 pb ~102 k€.

### 1.1 Le tableau des leviers

| Levier | Impact typique (pb/an) | € sur 100 k€ / 20 ans | Preuve | Concerne l'épargnant français ? |
|---|---|---|---|---|
| Détenir des actions plutôt que des produits garantis | +400 à +500 (MSCI World EUR 7,7 %/an vs fonds euros 3,5 % sur 1995-2025 ; +600 vs Livret A à ~0 % réel) | +200 à +300 k€ | Ramify 1995-2025 ; Jordà et al. ; DMS 2026 ; Ibbotson-Kaplan (l'allocation explique ~100 % du niveau de rendement) | Oui, levier dominant : 60 % du patrimoine financier des ménages est en produits de taux, 4,6 % en actions cotées (Banque de France T3 2025) |
| Taux d'épargne et durée | à 20 ans / 5 %, 58 % du capital final est constitué des versements | chaque 100 €/mois de plus ≈ +41 k€ | Arithmétique ; « portfolio size effect » de Kitces ; Anarkulova (un fonds à date cible exige +61 % d'épargne pour égaler 100 % actions) | Oui |
| Frais : AV bancaire en UC actives vs PEA + ETF | −200 à −350 | −100 à −150 k€ | France Assureurs 2024 : 0,88 % de frais de contrat + 1,62 % de frais de fonds ; Nalo : 3,9 % tout compris en banque vs 1,65 % ; ESMA 2025 : 1,9 % vs 0,5 % | Oui, premier levier contrôlable |
| Frais : fonds actif vs indiciel dans la même enveloppe | −100 à −120 | −55 à −65 k€ | ESMA : frais courants 1,38 % vs 0,22 % ; Morningstar (les frais sont le meilleur prédicteur) ; SPIVA Europe : 98 % des fonds actions monde sous leur indice à 10 ans | Oui |
| Frais : AV/PER en ligne (0,5-0,6 %) vs banque (0,85-1 % + 2 % d'entrée) | −30 à −50, plus 2 % à l'entrée | −17 à −29 k€ | Finance Héros, Ramify, FranceTransactions | Oui |
| Enveloppe : PEA vs CTO | −62 de TCAM net | −28 k€ | Calcul avec les taux 2026 (PS 18,6 %, PFU 31,4 %) | Oui |
| Enveloppe : PEA vs AV (0,6 % de frais, 26,1 % à la sortie) | −90 | −52 k€ avant abattement | Calcul ; l'abattement de 4 600 / 9 200 € récupère 1,2 à 2,4 k€ d'impôt par an en phase de retrait | Oui |
| Localisation des actifs (obligations et SCPI en AV, actions en PEA) | +20 à +60 (France) ; +5 à +30 (littérature US) | +3 à +35 k€ | Vanguard juin 2026 (≤ 30 pb), Dammon-Spatt-Zhang, Betterment | Oui |
| PER : déduction à TMI 30-45 % vs sortie taxée à 11-30 % | +50 à +150 équivalent sur la poche PER | +3 à +8 k€ par 10 k€ versés | Règle Linxea / Finance Héros ; service-public | Oui, seulement au-dessus de la TMI 30 % et avec frais ≤ 0,6 % |
| Comportement : changer de fonds, courir après la performance | −80 à −160 | −45 à −85 k€ | Morningstar Mind the Gap hors US 2023 (Luxembourg −0,82 pt, fonds actions −1,32 à −1,61 pt) ; US 2025 −1,2 pt | Oui pour les détenteurs d'UC |
| Comportement : épargnant indiciel discipliné | −10 à −30 | −6 à −17 k€ | Fulkerson et al. 2026 (le mauvais timing ne coûte que 0,10 %/an) | Faible |
| Comportement : trading d'actions | −150 (moyenne) à −700 (quintile le plus actif) | −80 k€ à plus de −200 k€ | Barber-Odean 2000 ; Odean 1998 (effet de disposition : +3,4 pts) | Oui : 55 % des détenteurs d'actions français tradent au moins chaque trimestre (AMF 2025) |
| Comportement : CFD / forex | perte attendue de la mise | −10 887 € en moyenne, 89 % de perdants | AMF 2014 | Oui |
| Attendre en cash (étaler un apport) | −120 à −220 la première année | −1,2 à −2,2 k€ par 100 k€ | Vanguard 2023 : l'investissement immédiat gagne 68 % du temps | Seulement pour les rentrées exceptionnelles |
| Rééquilibrage (vs dérive) | +12 à +25 ajustés du risque ; −65 de rendement brut mais −2,8 pts de volatilité | +7 à +15 k€ | Vanguard Advisor's Alpha 2022/2025 ; Rebalancing edge 2024 | Oui, par les versements en PEA/AV, sans impôt |
| Diversification : actions en direct, biais domestique | la médiane des actions fait moins que les bons du Trésor ; CAC seul : décennie perdue 2000-2012 | perte non bornée | Bessembinder 2018 ; DMS ; Jordà (France actions 3,25 % réel sur l'échantillon complet vs 6,6 % monde) | Oui |
| Tilts factoriels (value, momentum, small) | +50 à +200 bruts historiquement ; net des contraintes PEA, TER, fiscalité et discipline ≈ 0 à +100 | 0 à +55 k€, forte dispersion | AQR Fact-Fiction ; DMS ; McLean-Pontiff (décroissance post-publication) | Limité en PEA |
| Suivi de tendance (SMA 10 mois) sur la poche actions | ≈ 0 de rendement ; divise par deux le pire drawdown | 0 en rendement ; protège 30-50 k€ dans un 2008 | Faber ; AQR « A century of evidence » | Faisable en PEA à 1 €/ordre ; difficile à tenir |
| Or, 10-20 % | −100 à −200 de rendement attendu ; −15 à −30 pts de drawdown max | −55 à −100 k€ attendu ; +30 à +50 k€ dans un 2008 | portfoliocharts France ; DMS (or 1,3 % réel/an) | Oui (hors PEA) |
| SCPI vs ETF monde | −200 à −400 récemment ; frais d'entrée ≈ −80 à −100 pb/an amortis sur 10 ans | −100 k€ et plus (2020-2025) | ASPIM 2025 (+1,46 % de performance globale) | Oui ; l'AV atténue la fiscalité |
| Produits structurés | 0,8 %/an de coût médian ; valeur en scénario de stress 15 % | −26 k€ à 0,8 % plus la queue | ESMA 2025 ; AMF/ACPR 2026 | Oui, massivement vendus en AV |
| Règle de retrait (4 % vs 3,25 % vs dynamique) | 4 % échoue dans plus de la moitié de l'histoire française (Pfau) ; ~95 % de succès à 3,5 % en portefeuille mondial | la différence entre épuisement et héritage | Pfau ; Anarkulova ; ERN ; Kitces | Oui |

### 1.2 Ce que les Français détiennent, et pourquoi le levier 2 domine

Banque de France, T3 2025 : 6 537 Md€ de placements ; produits de taux
3 921 Md€ (60 %) dont dépôts à vue 767, livrets et dépôts rémunérés 1 367,
fonds euros et retraite 1 574 ; produits de fonds propres 2 517 Md€ (38,5 %)
dont actions cotées 299 (4,6 %), UC 580, fonds actions 186. Baromètre AMF
2025 : 82 % détiennent un livret, 21 % des UC, 11 % des actions en direct,
5 % des ETF. Le rendement « satisfaisant » attendu d'un produit **sans
risque** est de 3,4 % en moyenne ; 43 % attendent plus de 5 % d'un produit
garanti. Le principal biais français n'est pas le sur-trading, c'est la
sous-exposition : attendre des rendements d'actions de produits garantis.

Rendement des fonds euros (net de frais, brut de PS) : 5,3 % en 2000, 3,4 %
en 2010, 1,3 % en 2020-21, 1,9 % en 2022 (inflation 5,2 % : −3,3 % réel),
2,6 % en 2023-2025. Moyenne 2000-2025 : ~+1,3 %/an réel avant PS, ~+0,8 %
après. Livret A : ~0 % réel à long terme, −3,6 % réel en 2022. MSCI World en
euros : 10,1 %/an dividendes réinvestis depuis 1969 (Épargnant 3.0) ;
7,71 %/an sur 1995-2025 (Ramify) ; pire baisse −57 % (2007-2009).

### 1.3 Les décompositions « valeur du conseil », tous les chiffres

| Module | Vanguard Advisor's Alpha 2022 | Vanguard 2025 | Comment c'est estimé |
|---|---|---|---|
| Allocation d'actifs adaptée, fonds diversifiés | > 0, non chiffré | > 0 | Ibbotson-Kaplan |
| Mise en œuvre à bas coût | 30 pb | « sélection 0-100 pb » | 34-38 pb moyens vs 7-9 pb indiciels aux US |
| Rééquilibrage | 14 pb | 12 pb | 60/40 1960-2021 : rééquilibré 9,23 % à 11,0 % de vol vs dérive 9,88 % à 13,8 % |
| Coaching comportemental | 100 à 200 pb | jusqu'à 200 pb et plus | TRI vs TWR des porteurs de fonds |
| Localisation des actifs | 0-60 pb | 0-60 pb | Simulation imposable vs différé |
| Stratégie de retrait | 0-120 pb | jusqu'à 100 pb et plus | Ordre des retraits |
| Total | « jusqu'à 3 % ou plus » | « environ 3 % » | Explicitement « sur une période non spécifiée » |

Morningstar Gamma (Blanchett-Kaplan 2013) : cinq décisions rapportent
+22,6 % de revenu de retraite certain-équivalent, soit +1,59 %/an
d'« alpha » : retrait dynamique 0,54 %, localisation et ordre des retraits
0,52 %, allocation tenant compte du capital humain 0,38 %, rente 0,24 %,
optimisation relative au passif 0,14 %. Russell 2026 : 4,92 %/an dont
coaching 2,30 %, fiscalité 1,23 %, planification 1,13 %, allocation 0,26 %.

Lecture : les modules robustes et reproductibles (coût, enveloppe,
rééquilibrage, ordre des retraits) valent 100 à 400 pb/an **en France**,
parce que le point de départ (AV bancaire en UC) est bien plus cher qu'aux
États-Unis. L'« allocation » au sens Markowitz pèse 0 à 26 pb dans toutes les
décompositions. C'est la partie que Tangent a choisie.

### 1.4 Retrait : la règle des 4 % ne survit pas à l'histoire française

| Étude | Données | Portefeuille | Résultat |
|---|---|---|---|
| Bengen 1994 | US 1926-1992 | 50-75 % actions | 4,0 % (cohorte 1968) |
| Bengen 2024-25 | US, diversifié | ~65 % actions | 4,7 % pire cas ; ~7 % moyen |
| Trinity 1998 | US 1926-1995 | 75/25 à 50/50 | 4 % : 95-98 % de succès ; 5 % : 67-83 % |
| Pfau 2010 | DMS, 17-19 pays, 1900-2010 | 50 % actions / 50 % bons | **France 0,82 %**, Italie 0,80 %, Allemagne 1,01 %, Japon 0,26 %, UK 3,36 %, US 3,96 %, monde 3,58 % ; 4 % échoue dans plus de la moitié des cohortes françaises (1914-1950) |
| Anarkulova et al. 2022 | 38 pays développés, bootstrap par blocs | 60/40 domestique | 2,31 % pour un couple de 65 ans à 5 % de risque de ruine |
| Early Retirement Now | US 1871-2015 | 75-100 % actions | 4 % : 90 % (30 ans), 40 % (60 ans) ; 3,5 % : 95 % / 65 % ; « 3,5 % est le nouveau 4 % » |
| Morningstar 2024/2025 | Monte-Carlo prospectif | 20-50 % actions | 3,7 % à 90 % de succès ; règles dynamiques 4,5-5 % |
| Guyton-Klinger 2006 | US | ≥ 65 % actions | 5,2-5,6 % avec règles ; Kitces : coupes réelles de 28 à 54 % sur les mauvaises cohortes |
| Kitces-Pfau 2014 | US | 30 % → 70 % actions en retraite | 95,1 % vs 93,2 % pour 60/40 statique |

Synthèse pour un retraité français : 3 à 3,5 % initial avec garde-fous,
tampon de 2-3 ans en fonds euros, séquencer PEA / AV / PER pour utiliser
l'abattement AV chaque année, retirer le PER les années à faible TMI, compter
la pension d'État comme rente plancher.

### 1.5 Stratégies simples connues, chiffres pour un investisseur en euros

| Stratégie | Rendement réel moyen (vue France, 1970-2025, portfoliocharts) | Volatilité | Pire baisse | Taux de retrait 30 ans / perpétuel | Référence nominale EUR |
|---|---|---|---|---|---|
| 100 % MSCI World (CW8 / WPEA / DCAM en PEA) | ~8,2 % (proxy US) ; base 15 ans 3,4 % | 17 % | −57 % (2007-09, EUR) | 3,5 % / 2,8 % | 10,1 %/an 1969-2026 ; 7,71 % 1995-2025 |
| 60/40 monde / obligations euro | 6,3 % | 11,4 % | −34 % | 4,1 % / 3,3 % | US 60/40 1960-2021 : 9,2 % |
| Golden Butterfly (20 % × 5, avec or et small value) | 6,1 % | 9,7 % | −17 % | 5,4 % / 4,5 % | 8,1 % USD 30 ans |
| Permanent Portfolio (25 % × 4) | 4,9 % | 7,6 % | −13 % | 5,2 % | — |
| All Seasons | 5,3 % (US) | 8,7 % | −22 % (11 ans) | 4,9 % / 4,0 % | — |
| PEA World 70 % + fonds euros 30 % (défaut français) | ~5 % réel | ~11 % | ~−40 % (2008) | ~3,5-4 % dynamique | ~6,6 %/an 1995-2025 |
| Fonds euros 100 % | ~+1,3 % réel 2000-2025 avant PS | ~0 | 0 nominal ; −3,3 % réel 2022 | — | 3,5 %/an 1995-2025 ; 2,6 % en 2025 |
| CAC 40 GR 100 % | ~6-7 % nominal depuis 1990 | ~20 % | −65 % (2000-02), −60 % (2007-09) | — | Décennie perdue 2000-2012 |

Lecture : 100 % actions gagne l'accumulation sur 20-30 ans et perd la
décumulation ; les portefeuilles avec or ou obligations longues divisent le
drawdown par 2 à 3 au prix de 2-3 pts de rendement réel. Le défaut français
raisonnable : accumulation = ETF monde en PEA plus fonds euros en AV pour
l'horizon < 5 ans ; décumulation = 40-60 % actions monde, 20-40 % fonds
euros, 0-20 % or ou obligations longues, retrait 3-3,5 % dynamique.

---

## 2. Comment une banque construit une méthode d'investissement

### 2.1 Le pipeline canonique

Toutes les institutions (UBS « CIO House View », Amundi « CASM », JPM
« LTCMA », Vanguard « VCMM / VAAM », Robeco « Expected Returns », Pictet
« Horizon », fonds de pension, FRR, ERAFP) documentent le même processus en
sept étapes :

```
1. Mandat client         → objectifs, contraintes, profil de risque (adéquation MiFID II), horizon, passifs / objectifs
2. Hypothèses de marché  → E[R], σ, ρ pour 10 à 200 classes d'actifs, horizon 5-30 ans, mise à jour annuelle ou trimestrielle
3. Allocation stratégique→ MVO régularisée (rétrécissement, Black-Litterman, rééchantillonnage, contraintes) ou CVaR / budgets de risque, test Monte-Carlo
4. Allocation tactique   → comité d'investissement mensuel ; bandes ±5-10 pts autour de la stratégique
5. Mise en œuvre         → sélection de fonds/ETF, politique de change, enveloppe fiscale
6. Rééquilibrage         → calendaire + seuils (5 pts absolus ou 20 % relatifs), d'abord par les flux
7. Suivi et reporting    → TWR/MWR, benchmark, attribution de Brinson, risque ex ante (VaR/ES, stress), dérive, GIPS
```

Trois faits structurels, documentés, qui devraient dicter la conception d'un
moteur pour particulier :

- **Les entrées dominent l'optimiseur.** Une erreur sur les rendements
  attendus coûte ~11 fois plus qu'une erreur sur les variances et ~2 fois
  plus qu'une erreur sur les covariances (Chopra-Ziemba 1993). Un Markowitz
  sur données échantillon a besoin de ~3 000 mois de données pour battre 1/N
  avec 25 actifs (DeMiguel-Garlappi-Uppal 2009). Les praticiens passent donc
  l'essentiel de l'effort sur les hypothèses de marché et sur la
  **régularisation** (contraintes, rétrécissement, Black-Litterman,
  rééchantillonnage), pas sur l'optimiseur.
- **La couche quantitative sert la robustesse, pas l'alpha.** Le programme
  CFA niveau III (« Principles of Asset Allocation ») liste exactement cette
  boîte à outils : MVO, optimisation inverse, Black-Litterman,
  rééchantillonnage, Monte-Carlo, allocation relative au passif, objectifs,
  budgets de risque, allocation factorielle, heuristiques (60/40, 120−âge,
  1/N, parité de risque, modèle des dotations).
- **Un profil de risque est une bande de volatilité.** Les mandats de détail
  et de banque privée traduisent le questionnaire MiFID en 3 à 7 profils,
  chacun défini par une volatilité cible (ou un drawdown maximal / une perte
  attendue) et une fourchette d'actions ; l'échelle SRI 1-7 des DIC/KID donne
  l'ancre réglementaire (classe 3 = 5-12 % de volatilité sous PRIIPs).

### 2.2 Les hypothèses de marché (CMA) : comment elles sont construites

Tous les gérants (JPM, Invesco, Northern Trust, Verus, BNY, Schroders,
Robeco, Amundi, AQR, Research Affiliates) construisent les rendements
attendus **par briques** :

- **Cash** : taux directeur moyen attendu sur l'horizon (Verus : ⅓ taux
  courant + ⅓ taux 10 ans + ⅓ cible long terme). JPM 2026 : cash euro 2,3 %.
- **Obligations d'État** : `cash + prime de terme` ou `rendement courant +
  roll-down + revalorisation`. Robeco : prime de terme d'équilibre 0,75 %,
  taux 10 ans d'équilibre 4 %.
- **Crédit** : `rendement d'État + spread − pertes de défaut` ; règle de
  pouce « la moitié du spread est perdue en défauts ». Robeco : IG +0,75 %,
  HY +1,75 % sur les souveraines de duration équivalente.
- **Actions** : décomposition de Gordon `E[R] ≈ rendement (dividende + rachats
  nets) + croissance réelle des bénéfices + inflation + variation de
  valorisation`. AQR : v = 0 (pas de retour à la moyenne supposé), croissance
  réelle d'équilibre 1,8 %. BNY et JPM fixent Δvalorisation = 0 car c'est
  « la première source d'erreur de prévision ». Research Affiliates : retour
  partiel du CAPE vers sa moyenne sur 10 ans. Vanguard : pas des briques mais
  un VAR (VCMM) conditionné à la valorisation initiale, 10 000 trajectoires.
- **Immobilier** : `taux de capitalisation + croissance réelle des loyers −
  capex + inflation`. **Or et matières premières** : `cash + inflation + roll
  ≈ 0`.
- **Volatilité et corrélations** : historiques longues, dé-lissées pour les
  actifs privés ; conversion géométrique → arithmétique `μ_arith ≈ μ_géo +
  σ²/2` avant toute MVO (Invesco, JPM publient les deux).
- **Devise** : pour un investisseur euro, les actifs hors euro sont montrés
  non couverts (ajoute la volatilité de change) et couverts (rendement local −
  différentiel de taux). JPM 2026 : US large cap 6,1 % non couvert / 5,9 %
  couvert ; obligations mondiales 3,7 % non couvertes (σ 6,9 %) / 3,5 %
  couvertes (σ 4,0 %). DMS : le change ajoute ~6 pts de volatilité ; les
  institutions couvrent les obligations plus que les actions.

### 2.3 Les chiffres 2026 pour un investisseur en euros (nominaux, géométriques, 10 ans sauf mention)

| Classe d'actifs (EUR) | JPM LTCMA 2026 (10-15 ans) | Amundi CMA 2026 (10 ans) | Robeco 2026-30 (5 ans) | Northern Trust 2026 | AQR (réel, local) | Ancre longue (DMS / Jordà) |
|---|---|---|---|---|---|---|
| Cash euro | **2,3 %** (σ 0,6) | ~2 % | 3,00 % | ~2 % (BCE) | ~1,3-1,7 % réel | bons réels ~0,5 % monde, **−2,5 % France** |
| Obligations d'État euro | **3,4 %** (σ 5,3) ; indexées 3,6 % | **3,5 %** (σ 5,2) | 2,75 % (AAA) | 3,8 % | ~1,6 % réel | obligations réelles ~1,7 % monde |
| Crédit IG euro | **4,0 %** (σ 4,9) | **3,4 %** (σ 4,8) | 3,00 % (couvert) | 3,7 % | — | — |
| HY euro | 5,3 % (σ 9,5) | 3,8 % (σ 12,2) | 3,25 % | — | — | — |
| Actions monde (EUR, non couvert) | **AC World 6,4 %** (σ 14,4) ; DM 6,3 % | US 6,5 %, EM 7,2 % | **DM 6,00 %** ; EM 7,50 % | monde 6,9-7,1 % | DM 4,2 % réel (≈ 6,5-7 % nominal) | réel 5,2 % monde |
| Actions zone euro / Europe | zone euro **7,2 %** (σ 17,1) ; Europe 6,4 % | **Europe 7,1 %** (σ 16,6) | — | Europe 5,7 % | zone euro **5,1 % réel** | France réel 3,3 % (1900-), 6,4 % (post-1950) |
| Immobilier | Europe core **6,3 %** (σ 10,8) ; REIT mondiaux 8,1 % | mondial **5,4 %** (σ 12,4) | coté **5,50 %** | 6,2 % | — | logement réel ~6,5 % (Jordà) |
| Or / matières premières | or **4,9 %** (σ 15,6) ; MP 4,0 % | or **6,0 %** (σ 14,2) | MP 5,25 % | — | — | or réel ~1,3 % (DMS) |
| Inflation euro | 2,0 % | ~2 % | 2,50 % | ~2 % | — | — |
| Portefeuille équilibré | 60/40 EUR ≈ **5,4 %** (σ ≈ 9 %) | profil 6 % de vol : 4,5 % ; 12 % de vol : 6,4-7,4 % | — | — | 60/40 mondial **3,4 % réel** | — |

Lecture : le consensus 2026 pour un investisseur euro est **cash 2-3 %,
obligations euro 3-4 %, IG 3,5-4 %, actions monde 6-7 % nominal (4-5 %
réel), Europe 6-7 %, immobilier 5,5-6,5 %, or 5-6 %**, inflation ~2 %. Un
portefeuille équilibré (50-60 % d'actions) est attendu à ~5 % nominal, ~3 %
réel, ~8-9 % de volatilité. La dispersion entre fournisseurs (~3 pts, Horizon
Actuarial 2024 : de 5,38 % à 8,65 % pour un portefeuille de pension) est du
même ordre que la prime de risque elle-même : d'où les **fourchettes**
(Vanguard : 25e-75e percentile ; AQR : ±3 pts/an à 50 %).

Ancre historique (UBS/DMS 2026, 126 ans, 35 marchés) : US actions 9,8 %
nominal / 6,6 % réel, obligations 4,6 % / 1,6 %, bons 3,4 % / 0,5 % ; monde
réel actions ~5,2 %, obligations ~1,7 % ; **France actions réel ~3,3-3,5 %,
obligations ~0,3 %, bons ~−2,5 %** (hyperinflation des années 1940) ; prime
de risque prospective ~3,5 % géométrique (~5 % arithmétique). Jordà et al.
1870-2015 : actifs risqués (actions + logement) ~7 % réel, actifs sûrs 1-3 % ;
France : actions 3,25 % réel sur l'échantillon complet, 6,38 % post-1950,
11,07 % post-1980 ; logement 6,54 % / 10,38 % / 6,39 %. La France est le
pays où les actifs sûrs ont été le pire placement de long terme.

Implications pour un moteur : (1) un modèle par briques explicable avec
paramètres publiés (prime de terme 0,75-1,2 %, IG +0,75 %, HY +1,75 %,
croissance réelle 1,8 %, ERP 3,5 % géométrique), recalibré chaque année sur
la fourchette JPM-Amundi-Robeco-NT ; (2) des fourchettes, pas des points ;
(3) 7 à 12 classes d'actifs pour une allocation de détail : cash,
obligations euro, IG euro, HY (optionnel), actions monde avec découpe zone
euro / émergents, immobilier coté, or.

**Comparaison avec Tangent** : `cma.yaml` contient trois nombres (7 %, 10 %,
6 %) sans date, sans source ligne à ligne, sans préciser réel ou nominal, et
un défaut de 7 % pour tout le reste. Le « 10 % Nasdaq » n'est publié par
aucun fournisseur de CMA. Le mélange 70/30 est un poids affirmé, pas un
estimateur (James-Stein ou Black-Litterman le fixeraient à partir de
SE(μ̂)² et de la variance du prior). La projection, elle, n'utilise même pas
ce mélange.

### 2.4 Construire le portefeuille : pourquoi personne ne fait tourner Markowitz sur des moyennes d'échantillon

Cinq résultats classiques expliquent la pratique :

- **Jobson-Korkie (1980-81)** : avec 20 titres et 60 mois de données, le
  portefeuille tangent estimé a un Sharpe hors échantillon de ~0,08 contre
  ~0,27 pour l'équipondération et 0,34 pour le vrai optimum.
- **Michaud (1989)** : l'optimiseur est un « maximiseur d'erreurs
  d'estimation » : il surpondère exactement les actifs dont le rendement
  estimé est le plus élevé, la corrélation la plus négative et la variance
  la plus faible, c'est-à-dire ceux dont l'erreur d'estimation est la plus
  grande.
- **Chopra-Ziemba (1993)** : à tolérance au risque moyenne, une erreur sur
  les moyennes coûte **11 fois** plus qu'une erreur sur les variances et
  **2 fois** plus qu'une erreur sur les covariances.
- **DeMiguel-Garlappi-Uppal (2009)** : sur 14 modèles et 7 jeux de données,
  aucun ne bat 1/N de façon constante ; il faut ~3 000 mois de données pour
  25 actifs.
- **Kritzman-Page-Turkington (2010)** : la contre-attaque : le problème est
  les moyennes glissantes courtes, pas l'optimiseur ; avec des primes de
  risque de long terme « même choisies arbitrairement », l'optimisation bat
  1/N.

Lecture : le désaccord ne porte pas sur l'optimiseur mais sur les moyennes.
Personne ne défend les moyennes d'échantillon. Tangent utilise 30 % de
moyenne d'échantillon sur 5 ans et 70 % d'un défaut à 7 % : le pire des deux.

Les remèdes, avec leur verdict pour un univers de 3 à 10 ETF :

| Méthode | Ce qu'elle corrige | Ce qu'il faut | Qui l'utilise | Verdict pour 3-10 ETF |
|---|---|---|---|---|
| MVO sur moyennes d'échantillon | rien (référence) | μ̂, Σ̂ historiques | personne, sauf pour enseigner | **Non** : 10-20 ans d'histoire d'ETF sont du bruit |
| MVO contrainte sur CMA par briques | erreur sur μ, solutions en coin | CMA, bornes, rotation | JPM, Invesco, NT, Mercer, la plupart des banques privées | **Oui, le cheval de labour** : à N ≤ 10 la covariance est bien estimée ; μ vient des CMA, pas des données |
| Ledoit-Wolf linéaire (δ* analytique) | bruit d'échantillonnage de Σ | T ≥ 60 observations ; une ligne de code | quants actions, robos, défaut sklearn | **Oui, assurance bon marché** ; δ* petit à N ≤ 10 mais protège contre deux ETF obligataires quasi colinéaires. Tangent fixe δ = 0,20 et jette δ* |
| Rétrécissement non linéaire (LW 2020) | Σ quand N/T grand | N ≥ 50 | quants grands univers | Inutile à N ≤ 10 |
| Bayes-Stein (Jorion 1986) | moyennes extrêmes | Σ̂, T, un prior | benchmarks académiques | φ̂ ≈ 0,5-0,9 à N = 5-10 et T = 120 mois : les données déplacent à peine les moyennes ; redondant avec des CMA |
| **Black-Litterman** | solutions en coin ; permet d'ajouter des vues sans reconstruire μ | poids de marché, λ, τ, P/Q/Ω | GSAM, comités CIO des banques privées, Morningstar | **Oui pour la couche de vues** : ancre = portefeuille stratégique du profil ; Ω selon He-Litterman rend τ sans importance |
| Rééchantillonnage (Michaud) | instabilité des poids ; région de non-transaction | Monte-Carlo 500+ tirages | New Frontier, CFA III | Diagnostic utile, pas allocateur principal (breveté, difficile à expliquer) |
| Optimisation robuste | protection pire cas sur μ | ensembles d'incertitude, SOCP | BlackRock, Axioma, assureurs | Équivalent à un rétrécissement à petit N |
| **Parité de risque / ERC / budgets de risque** | supprime μ ; risque équilibré | Σ seulement | Bridgewater, AQR, Lombard Odier, fonds multi-actifs | **Oui comme ancre par défaut des profils** (part du risque actions 20/80 → 60/40 → 80/20) ; ERC non levier sur 5 ETF ≈ 25 % d'actions, donc à combiner avec une cible de volatilité |
| HRP | Σ mal conditionnée, grand N | corrélations, clustering | quants ML | Sur-ingénierie à N ≤ 10 ; un budget de risque à deux niveaux fait mieux |
| Minimum variance | n'utilise pas μ | Σ | fonds défensifs | Seulement comme extrémité prudente ; seul ≈ 90 % obligations |
| Diversification maximale | concentration | σ, Σ | TOBAM | Même famille qu'ERC, moins lisible |
| Optimisation CVaR (Rockafellar-Uryasev) | queues épaisses, scénarios asymétriques | ≥ 1 000-10 000 scénarios | Amundi (SAA à CVaR 95 % à 10 ans), FRR, Pictet, Solvabilité II | **Oui pour le reporting et le contrôle du profil** ; seul, il surajuste la queue |
| **Contraintes** (bornes, rotation, tracking error) | tout, grossièrement et lisiblement | décisions de politique | tout le monde | **Obligatoire** : bandes d'actions par profil, ≤ 40 % par ETF, ≥ 5 % de cash, rotation ≤ 20 %/an. Jagannathan-Ma : interdire la vente à découvert équivaut à rétrécir Σ |
| Part de Merton | cohérence dynamique | γ, μ − r, σ² | modèles de cycle de vie, glide paths | Une ligne de contrôle de la part d'actions de chaque profil (γ 2-6 → 30-90 %) |
| Multi-période (Boyd, cvxportfolio) | coûts de transaction, flux prévisibles | prévisions, modèle de coût | fonds quants, robos fiscalement conscients | Seulement pour le moteur de rééquilibrage |

La chaîne, méthode par méthode, telle que la décrivent le programme CFA et
les documents des gérants : **(1) CMA par briques → (2) covariance rétrécie
sur fenêtre longue → (3) ancres de profil par budget de risque ou MVO
contrainte → (4) Black-Litterman pour tout tilt tactique → (5) Monte-Carlo /
CVaR pour reporter la queue → (6) contraintes et règle de rééquilibrage
consciente de la rotation.**

### 2.5 Ce que font vraiment les institutions

- **Norvège (GPFG, ~20 000 Md NOK)** : benchmark stratégique 70 % actions /
  30 % obligations fixé par le ministère et le Parlement ; tracking error
  plafonné à 1,25 % ; **rééquilibrage obligatoire quand la dérive dépasse 2
  points**, vérifié chaque fin de mois.
- **CalPERS (~500 Md$)** : cycle ALM de **4 ans** ; en 2021 le conseil a
  choisi, parmi une échelle de portefeuilles candidats (E[R], σ), celui à
  6,8 % attendu et 12,1 % de volatilité : actions 42 %, obligations 30 %,
  actifs réels 15 %, private equity 13 %, dette privée 5 %, levier 5 %.
- **FRR (France, ~20 Md€)** : deux poches, couverture du passif (OAT,
  cash, IG ; 19,8 % fin 2024) et actifs de performance ; allocation
  stratégique **révisée chaque année** sur deux scénarios macro (référence et
  dégradé) chacun couplé à un scénario climat NGFS, incertitude bayésienne
  sur les paramètres ; contrainte : probabilité « extrêmement faible » de
  manquer un paiement à la CADES ; **CVaR 99 % à 1 an = 18,8 % des actifs** ;
  volatilité ex post 3,0 % en 2024 ; +4,0 %/an depuis 2010 ; vues tactiques
  par le Directoire sur 3 mois à 2 ans ; comité des risques mensuel.
- **ERAFP, Ircantec, Caisse des Dépôts** : plans de 4 ans, études ALM,
  limites réglementaires (ERAFP : ≤ 40 % d'actions), ESG intégré dans
  l'allocation elle-même.
- **Pictet WM** : révision « substantielle » de l'allocation stratégique
  tous les 5 ans, sur un horizon de marché de 10 ans ; « des ajustements plus
  fréquents mais plus petits » envisagés.

Les trois horloges d'un comité d'investissement :

| Couche | Qui décide | Fréquence | Instruments |
|---|---|---|---|
| Allocation stratégique | Conseil / comité sur proposition du CIO | 3-5 ans (CalPERS, Pictet, Ircantec) ou annuelle (FRR, banques privées) | CMA → MVO/BL/budgets → candidats → Monte-Carlo/CVaR → poids et fourchettes |
| Allocation tactique | Comité d'investissement | Mensuelle ; ad hoc en crise | ±5-10 pts par classe ; budget de tracking error 1-3 % |
| Rééquilibrage | Gérants / opérations | Calendaire + seuils (GPFG 2 pts ; particulier 5 pts absolus ou 20 % relatifs) | Flux d'abord, puis vers la cible ou le bord de la bande |
| Suivi | Risques, indépendant du front | Comité mensuel, reporting trimestriel (MiFID II art. 60), VaR quotidienne | Vol/VaR/CVaR ex ante, stress, dérive, attribution |

Un moteur pour particulier devrait avoir les mêmes trois horloges : une mise
à jour annuelle des profils pilotée par les CMA (avec une règle de
stabilité), une couche de vues mensuelle optionnelle en tilts Black-
Litterman à ±5 pts, et un rééquilibrage sur flux et seuils. Tangent
re-résout l'optimiseur à chaque chargement de page, sur 5 ans d'histoire,
sans aucune horloge.

### 2.6 Gestion par objectifs : de Chhabra à l'EDHEC

- **Chhabra (2005, Merrill Lynch), « Beyond Markowitz »** : « pour le
  particulier, l'allocation du risque précède l'allocation d'actifs ». Trois
  poches : **sécurité** (dépenses essentielles, assurance, réserve ; cash,
  obligations courtes, résidence principale ; rendement sous le marché
  accepté), **marché** (maintenir le niveau de vie sur des décennies ; le
  portefeuille Markowitz diversifié), **aspiration** (paris concentrés).
  L'argent frais va dans l'ordre sécurité → marché → aspiration. UBS
  « Liquidity · Longevity · Legacy » (2-5 ans de dépenses en actifs stables,
  puis diversifié croissance, puis excédent) est la même chose étiquetée par
  horizon.
- **Das-Markowitz-Scheid-Statman (2010)** : chaque objectif est un compte
  avec un seuil de rendement H et une probabilité d'échec maximale α
  (Roy) : maximiser E[R] sous P(R < H) ≤ α. Sous normalité, H = w′μ +
  Φ⁻¹(α)√(w′Σw) fixe un point de la frontière et donc un γ implicite. Les
  investisseurs « énoncent mieux un seuil et une probabilité d'échec qu'un
  coefficient d'aversion ». Exemple : retraite (H = −10 %, α = 5 %) → γ =
  3,80 ; études (−5 %, 15 %) → 2,71 ; transmission (−15 %, 20 %) → 0,88.
  **L'agrégat des sous-portefeuilles est efficient** au sens moyenne-
  variance : la présentation par objectifs ne coûte rien en efficacité.
- **Brunel (2015)** : besoins 90-95 % de probabilité, envies 80-85 %,
  souhaits 65-75 %, rêves 50-60 % ; la conversation passe de « quelle est
  votre tolérance au risque ? » à « quels objectifs peut-on financer avec
  quelle confiance ? ». Morgan Stanley : en mars 2020, plus de 75 % des
  clients en planification par objectifs sont restés « sur la trajectoire »
  au plus bas du marché.
- **EDHEC (Martellini, Milhau, Deguest)** : LDI pour les ménages :
  portefeuille de couverture de l'objectif (pour la retraite, une échelle
  obligataire versant un revenu réel fixe) + portefeuille de performance
  (max Sharpe) ; ratio de financement FR = A / VA(objectif) ; objectif
  essentiel sécurisé, objectif aspirationnel financé par le surplus en règle
  CPPI (multiplicateur 2-4). Deux conséquences : l'actif « sûr » d'un
  objectif daté n'est pas le cash mais une obligation de duration
  appariée ; la part d'actions découle du ratio de financement, ce que la
  grille du PER approxime par le temps restant.

### 2.7 Cycle de vie et glide paths

- **Samuelson-Merton** : sous CRRA et rendements i.i.d., part risquée
  constante w* = (μ − r)/(γσ²) : avec ERP 4 %, σ 16 % → 78 % à γ = 2, 52 % à
  γ = 3, 31 % à γ = 5. La « diversification temporelle » est un sophisme :
  l'horizon seul ne justifie pas plus d'actions.
- **Bodie-Merton-Samuelson (1992)** : ce qui le justifie est le **capital
  humain** H ; si H est obligataire, la part d'actions du patrimoine
  financier est w*(F + H)/F, d'où les jeunes très investis en actions et la
  décroissance avec l'âge ; la flexibilité de l'offre de travail augmente la
  prise de risque optimale.
- **Cocco-Gomes-Maenhout (2005)** : modèle calibré (revenus PSID, contraintes
  d'emprunt, mortalité) : part optimale en actions de 60 à 100 % selon l'âge
  même avec γ = 10.
- **Fonds à date cible** : Vanguard 90 % d'actions jusqu'à 40 ans → 50 % à
  65 → 30 % à 72 ; T. Rowe 98 % → 55 % → 30 % ; le modèle VLCM de Vanguard
  choisit parmi des milliers de glide paths par utilité sur 10 000
  trajectoires VCMM et réaffirme 90 % au départ. Le « 100 − âge » est trop
  prudent avant 40 ans (60 % vs 90 %) ; le « 120 − âge » colle à 30 et 65
  ans mais est trop agressif après 72.
- **Estrada (2016)**, 19 pays sur 110 ans : entre glide path décroissant et
  croissant, choisir le décroissant, mais « 100 % actions et 60/40 statique
  sont des stratégies simples et très efficaces pour les retraités » ; les
  différences entre chemins raisonnables sont de second ordre par rapport au
  taux de retrait. **Pfau-Kitces (2014)** : commencer prudent (20-40 %) à la
  retraite et remonter (40-80 %) réduit probabilité et ampleur d'échec, à
  cause du risque de séquence ; la « tente obligataire » réconcilie les deux.
- **Ayres-Nalebuff** : levier 2:1 quand on est jeune ; +19 % de richesse
  terminale en théorie ; Samuelson s'y est opposé dans 27 articles.

Le `glide_path.py` de Tangent (120 − âge converti en multiplicateur de σ,
plafonds « CFA » non sourcés, −2σ étiqueté drawdown, aucun appelant) n'est
relié à aucune de ces références.

### 2.8 Rééquilibrage : les chiffres

- **Pourquoi** : contrôle du risque d'abord (un 60/40 laissé seul depuis
  1926 serait à ~90 % d'actions). Bonus de rééquilibrage (Bernstein,
  Willenbrock) ≈ ½(Σ wᵢσᵢ² − σₚ²) : deux actifs non corrélés à 20 % de
  volatilité → 0,91 %/an ; un 60/40 euro (σ 15 % / 5 %, ρ 0,3) → **~0,25 %/an**,
  réel mais petit ; négatif quand un actif tend durablement (actions US
  2009-2024).
- **Vanguard 2010** : mensuel, trimestriel ou annuel avec seuils 0/1/5/10 % :
  « pas de fréquence ou de seuil optimal » ; recommandation : **surveiller
  semestriellement ou annuellement, rééquilibrer à 5 points, par les flux
  d'abord**. **Vanguard 2022 (utilité, coûts simulés)** : **l'annuel est
  optimal** pour la plupart des particuliers ; bat le quotidien de 51 pb,
  le mensuel de 21-28 pb ; 80-90 % du bénéfice vient de « récolter la prime
  de risque actions en rééquilibrant moins souvent ». **Vanguard 2024**
  (gérants qui surveillent quotidiennement) : règle 200/175 (seuil 2 pts,
  retour à 1,75 pt), 15-22 pb/an en accumulation, 22-25 pb en décumulation
  vs mensuel.
- **Daryanani (2008)** : bandes **relatives de 20 %** (tolérance = moitié
  de la bande, retour au bord pas à la cible), vérification jusqu'à
  bihebdomadaire, 2-3 opérations par an, ≈ +0,5 %/an vs annuel ; ne traiter
  que l'actif qui a franchi sa bande. C'est la règle des logiciels de
  rééquilibrage américains (iRebal, Tamarac).
- **Comptes imposables** (CFA III) : l'impôt sur les plus-values amortit la
  volatilité après impôt, donc bandes après impôt = bandes avant impôt /
  (1 − t) : avec le PFU à 31,4 %, 5 pts deviennent 7,3 pts ; rééquilibrer
  avec l'argent frais, les dividendes et les retraits d'abord ; préférer les
  enveloppes où c'est sans impôt (PEA, AV, PER).
- **Chance de date (Hoffstein-Faber 2020)** : deux stratégies identiques
  rééquilibrées à des dates différentes divergent souvent de plus de 100
  pb/an ; remède : N tranches décalées, dispersion réduite de 1/N.
  **Harvey-Mazzoleni-Melone (2025)** : le rééquilibrage institutionnel de
  fin de mois coûte ~8 pb/an et fait baisser les actions de 17 pb le
  lendemain ; ne pas traiter le dernier ou le premier jour ouvré du mois.

Règles qui en découlent pour un moteur : surveiller mensuellement ou à
chaque flux, traiter seulement quand une bande est franchie, forcer une
vérification annuelle ; bande_i = max(2 pts, min(5 pts, 25 % × wᵢ)),
multipliée par 1/(1 − t) en compte imposable ; revenir à mi-chemin entre le
bord et la cible ; diriger les versements vers l'actif le plus sous-pondéré ;
ne pas ajouter de règle « rééquilibrer plus vite en crise », la bande le fait.

### 2.9 Banques privées : la machine et les profils

Trois couches, quelle que soit la marque : **(1) un CIO produit des CMA
annuelles et une « House View » mensuelle** (UBS CIO, Pictet, Julius Baer,
BNP WM, SGPB, Indosuez, Rothschild & Co, Goldman PWM) ; **(2) 5 à 8
allocations stratégiques par profil**, revues chaque année, refondues tous
les ~5 ans, chacune avec (E[R], σ), drawdown historique et fourchette
d'actions publiés ; **(3) un questionnaire MiFID II** qui produit le profil
client ; le mandat doit lui correspondre ; le gérant applique SAA + tilts
dans les fourchettes ; le risque surveille ; reporting trimestriel.

Le profil est traduit en **bande de volatilité** ancrée sur les classes
réglementaires (SRRI UCITS : classe 4 = 5-10 %, 5 = 10-15 % ; SRI PRIIPs :
3 = 5-12 %, 4 = 12-20 %). Échelle de volatilité selon la part d'actions (CMA
euro : σ_actions 15 %, σ_obligations 5 %, ρ 0,3) : **20 % → 5,7 % ; 40 % →
7,5 % ; 50 % → 8,6 % ; 60 % → 9,8 % ; 80 % → 12,3 % ; 100 % → 15 %**. D'où les
étiquettes usuelles : Prudent ≈ 20-30 % d'actions ≈ 5-6 % de vol ; Équilibré
≈ 45-55 % ≈ 8-10 % ; Dynamique ≈ 70-80 % ≈ 11-13 % ; Offensif ≈ 90-100 % ≈
14-16 %. Amundi définit directement ses profils comme des cibles de 6 % et
12 % de volatilité.

| Institution (source, devise) | Profil | Actions | Rendement attendu | Volatilité | Pire baisse |
|---|---|---|---|---|---|
| UBS GWM CIO, « Asset allocation: risk and return », février 2026 (USD, CMA 2026) | 100/0 | 100 % | 8,4 % | 16,7 % | −51 % (74 mois sous l'eau) |
| " | 80/20 | 80 % | 7,8 % | 13,4 % | −41 % (65 mois) |
| " | 60/40 | 60 % | 7,1 % | 10,2 % | −30 % (50 mois) ; baisse moyenne −19 % |
| " | 50/50 | 50 % | 6,7 % | 8,7 % | −24 % |
| " | 40/60 | 40 % | 6,3 % | 7,2 % | −17 % |
| " | 20/80 | 20 % | 5,4 % | 4,5 % | −15 % ; pire 12 mois −18 % |
| " | 0/100 | 0 % | 4,3 % | 3,5 % | −15 % (2020, pas encore récupéré) |
| Amundi CMA 2026 (EUR) | Modéré (6 % de vol) | ~30-40 % | 4,5 % | 6 % | P(10 ans < 0) publiée |
| " | Dynamique (12 % de vol) | ~70-80 % | 6,4-7,4 % | 12 % | — |
| JPM LTCMA 2026 (EUR) | 60/40 | 60 % | ~5,4 % | ~9 % | — |
| CalPERS 2021 (USD) | Politique | 55 % | 6,8 % | 12,1 % | — |
| FRR 2024 (EUR) | Politique | ~41 % + 9 % couvert | ~4 % réalisé depuis 2010 | 7,3 % ex ante | CVaR 99 % 1 an : 18,8 % |
| Rothschild & Co AM (2023) | Défensif / Équilibré / Dynamique | 0-35 / 35-70 / 70-100 % | non publié | non publié | — |
| Société Générale Gestion | Mandats 0-30 / 30-70 / 70-90 / 90-100 | tel quel | non publié | « modéré / élevé / très élevé » | horizons 5 / 5 / 7 / 8 ans |
| Gestion pilotée française (moyennes 2026) | Prudent / Équilibré / Dynamique | 20-30 / 50-60 / 80-90 % | 3-4 % / 4-6 % / 6-10 % net | — | — |

Ce qu'un moteur doit publier par profil : les mêmes quatre nombres qu'UBS
(rendement composé attendu, volatilité attendue, pire drawdown historique,
temps sous l'eau) plus la fourchette d'actions, avec des cibles de volatilité
sur la grille Amundi/SRRI (≈ 3 / 6 / 9 / 12 / 15 %) pour coller aux classes
PRIIPs et aux planchers du PER. Comparer au `risk_levels.yaml` de Tangent
(3 %/5 %, 5 %/8 %, 7 %/12 %, 9 %/16 %, 11 %/22 %) : les volatilités sont
plausibles, les rendements ne le sont pas (UBS donne 5,4 % à 4,5 % de vol,
8,4 % à 16,7 % en USD ; Amundi 4,5 % à 6 %, 6,4-7,4 % à 12 % en EUR), et
aucun drawdown n'est publié.

### 2.10 Risque et suivi

- **Mesures** : VaR/ES paramétriques, historiques, Cornish-Fisher ; les
  gérants de patrimoine reportent une VaR/ES à 1 an à 95 ou 99 % du mandat ;
  le DIC PRIIPs exprime la même chose en volatilité équivalente à 97,5 %. La
  contrainte (H, α) d'un objectif **est** une contrainte de VaR : rapport de
  risque et profil d'adéquation peuvent partager un seul nombre.
- **Stress tests** (vocabulaire EBA 2018) : sensibilité (un facteur),
  scénario (plusieurs facteurs cohérents), **stress inversé** (partir de la
  perte maximale du profil et chercher la plus petite combinaison de chocs
  qui la produit), plausibilité « sévère mais plausible ». Quatre types en
  pratique : rejeu historique (1987, 1994, 1998, 2000-02, 2008, 2011, 2020,
  2022), macro hypothétique (« actions −30 %, spreads +300 pb, EUR/USD −10 %,
  taux +200 pb »), **choc factoriel propagé** E[Δx_autres | Δx_cœur] =
  Σ_oc Σ_cc⁻¹ Δx_cœur (MSCI « predictive stress test », Aladdin), inversé.
- **Corrélations de crise** (Longin-Solnik 2001) : sous normalité la
  corrélation des dépassements *baisse* quand le seuil s'éloigne (ρ = 0,80 →
  0,48 à 1σ, 0,24 à 3σ) ; empiriquement elle *monte* à la baisse (US-UK :
  0,53 à 0 %, 0,67 à −10 %) et pas à la hausse ; « c'est le marché baissier,
  pas la volatilité, qui fait monter la corrélation ». **Ang-Bekaert (2002)** :
  deux régimes, normal (0,9 %/mois, σ 2,8 %) et baissier (0,1 %, σ 5,0 %,
  corrélations +20 %), persistants ; le coût d'ignorer les régimes monte
  quand on peut détenir du cash.
- **Ciblage de volatilité** : Moreira-Muir (2017) : +25 % de Sharpe en
  divisant l'exposition par la variance réalisée du mois précédent ; Harvey
  et al. (2018) : marche pour actions et crédit, pas pour obligations et
  devises, réduit les pertes extrêmes ; critiques (Cederburg et al. 2020 :
  disparaît hors échantillon ; AQR : contrôler le risque par l'allocation
  statique et le rééquilibrage). Lecture honnête : un plafond d'exposition
  quand la volatilité réalisée dépasse 1,5 × la cible réduit les drawdowns à
  peu de frais ; le vol-scaling proportionnel complet ajoute rotation, impôt
  et risque de modèle pour un client à 3-10 ETF.
- **Mesure de performance** : TWR chaînée pour juger la stratégie (GIPS
  2020 : valorisation à chaque flux important, liaison géométrique ;
  **performance modélisée ou rétro-testée obligatoirement étiquetée et jamais
  chaînée à la performance réelle**), TRI pour le résultat du client,
  attribution Brinson-Fachler (allocation / sélection / interaction) contre
  le benchmark de politique.
- **Le rapport client** (plancher MiFID II art. 60, trimestriel) :
  composition et valorisation, performance de la période, frais itemisés,
  comparaison au benchmark convenu, dividendes et intérêts, transactions ;
  art. 62 : **alerte le jour même dès −10 % depuis le début de la période**,
  puis à chaque multiple de 10 %. Les bonnes maisons ajoutent : positionnement
  vs SAA et dérive, TWR et TRI gross/net à 1/3/5 ans, attribution
  SAA/TAA/sélection/change, volatilité ex ante vs bande du profil, VaR/ES 1
  an, stress 2008/2020/2022 et taux ±200 pb, contributions au risque par
  facteur, ratio de financement et probabilité par objectif, années de
  liquidité couvertes.

Tangent n'affiche ni TWR ni TRI, calcule une CVaR non définie qu'il n'affiche
pas, teste trois fenêtres post-2020 sur un panier parfois partiel, et n'a
aucune alerte. La règle de l'article 62 (−10 %, le jour même) est à elle
seule une meilleure spécification d'alerte que le briefing quotidien.

---

## 3. Ce que fait le moteur de Tangent, et ce qui est faux

Audit ligne à ligne de `backend/app/finance/*`, `backend/config/*.yaml`,
`llm/prompt_builder.py` et des écrans qui affichent les chiffres. Le rapport
complet (1 000 lignes, formules citées) est dans le scratchpad de session ;
voici l'essentiel.

### 3.1 Les dix défauts qui feraient échouer une revue quantitative

| # | Défaut | Où | Effet pour l'utilisateur |
|---|---|---|---|
| 1 | **Tout ticker absent de `cma.yaml` reçoit μ = 7 %/an**, puis 70 % de poids dans le mélange, avec sa propre volatilité historique. Le fichier ne couvre que 3 tickers (DCAM, PUST, ETZ). Ni CW8 (le benchmark de l'app), ni aucune obligation, ni aucun fonds monétaire, ni aucune UC | `cma.yaml`, `cma.py:get_return` | Un ETF obligataire court (σ 1,5 %) obtient un Sharpe de 3 ; un fonds monétaire (σ 0,3 %) un Sharpe de 15. L'optimiseur y met 100 % du capital et affiche « μ 7 %, σ 0,3 % ». Aucun avertissement, aucun log |
| 2 | **Le TER est compté deux fois.** yfinance renvoie des cours ajustés, donc déjà nets des frais du fonds (la VL est calculée après frais). ADR-021 retranche encore `valeur × TER / 12` chaque mois | `fees.apply_ter_to_fee_fn`, `projection.py` | Capital final sous-estimé de ~2,5 % (0,25 %/10 ans) à ~14 % (0,5 %/30 ans). L'état des lieux §5.4 le signalait « à confirmer » ; confirmé |
| 3 | **Les rétrocessions sont facturées à l'utilisateur** (`rebates_pct` 0,19 % chez BNP) alors qu'elles sont payées par le fonds au distributeur, à l'intérieur du TER, et nulles sur ETF | `brokers.yaml`, `fees.py` | Troisième couche sur les mêmes euros ; fausse la comparaison BNP vs Trade Republic |
| 4 | **μ historique en log, CMA en arithmétique, mélangés additivement** : `mean(log) × 252` estime la dérive géométrique ; 0,07 est un rendement arithmétique. Écart σ²/2 ≈ 2 pts à σ = 20 % | `annualized_stats`, `blended_mu` | La jambe historique est biaisée à la baisse de 1 à 2 pts ; Markowitz veut des μ arithmétiques |
| 5 | **Les cinq niveaux de risque ne sont sur aucune frontière.** Sharpe implicites (rf 2,5 %) : 0,10 / 0,31 / 0,375 / 0,41 / 0,39, non monotones. Le niveau 1 (3 % à 5 % de vol) est dominé par le LEP (3,5 % à ~0 %) dans le propre `envelopes.yaml` de l'app ; les niveaux 4 et 5 (9 %/16 %, 11 %/22 %) sont infaisables sous les CMA de l'app → `InfeasibleStrategyError` sur les deux crans « ambitieux » | `risk_levels.yaml` | Un prudent est poussé vers du risque inutile ; un dynamique reçoit « vise moins haut » |
| 6 | **Deux sémantiques NaN pour la même courbe.** `analytics.portfolio_value_series` propage les NaN (correct) ; `dashboard.py:96` et `stress.py:56` utilisent `.sum(axis=1)` qui **ignore** les NaN | `stress.py`, `dashboard.py` | Pour un ETF lancé en 2021, le stress COVID 2020 est calculé sur le panier partiel, puis **multiplié par la valeur totale** dans `Placements.tsx:224` : « avec tes placements d'aujourd'hui tu aurais perdu X € » est un faux chiffre en euros |
| 7 | **Le Monte-Carlo ignore l'incertitude des paramètres.** Avec 5 ans de données et σ = 18 %, l'erreur-type de μ̂ est 8 %/an. La dispersion simulée à 10 ans (σ√10 ≈ 57 %) est **plus petite** que celle due à l'erreur sur μ (≈ 80 %) | `monte_carlo_projection` | Le cône est environ deux fois trop étroit et vendu comme « 8 fois sur 10 » |
| 8 | **Le profil arrive au LLM 100 fois trop petit.** La base stocke des fractions ; le prompt les nomme `_pct` et écrit « Objectif rendement annuel : 0.07 % », « Tolérance volatilité : 0.12 % », « Livret A taux 0.02 % ». Le test unitaire encode la mauvaise convention | `prompt_builder.py:85, 210, 238` | Le briefing raisonne sur des objectifs absurdes ; de plus le bloc optimiseur est toujours `null` en batch nocturne |
| 9 | **« Les montants sont en euros d'aujourd'hui » est faux** : tout le moteur est nominal, sans inflation. En même temps la conversion « revenu mensuel → capital » utilise les 4 % de Bengen, définis sur un retrait **réel** initial | `Projection.tsx:457`, `bengen.py` | À 2 %/an sur 10 ans, la médiane est surestimée de 22 % en pouvoir d'achat ; le capital nécessaire est sous-estimé d'autant ; deux erreurs en sens inverse, aucune documentée |
| 10 | **`res.success` n'est vérifié que pour un objectif sur quatre** ; `max_sharpe` et `from_strategy` sont non convexes, un seul point de départ, pas de redémarrage | `optimizer.py:153`, `_solve_slsqp` | Un solveur non convergé est affiché « Optimal » |

### 3.2 Les autres défauts, par module

| Module | Ce qu'il calcule | Hypothèse clé | Défaut principal | Gravité |
|---|---|---|---|---|
| `projection.py` | Valeur initiale, μ, σ, bandes, frais | μ = moyenne brute des 5 dernières années | **Troisième μ de l'app**, le plus gonflé ; `period="5y"` codé en dur ; `invested` inclut la valeur de marché actuelle sous l'étiquette « tu auras versé » ; `cumulative_fees` est un coût d'opportunité | trompeur |
| `deterministic_projection` | bear / base / bull = μ−σ, μ, μ+σ chaque année | ±1σ chaque année est un « scénario » | À 10 ans le « bull » est un événement à +3,2σ (p ≈ 0,07 %) ; à 20 ans, ±4,5σ ; mélange μ simple et σ log | cosmétique (plus affiché) |
| `monte_carlo_projection` | Cône p10-p90, probabilité d'objectif | Gaussien i.i.d. mensuel, 1 000 chemins, graine 42 | Pas de queues épaisses, pas de clustering de volatilité, pas de retour à la moyenne, pas de rééquilibrage ; composition en parts figée 30 ans ; `goal_probability` est une probabilité terminale, pas de premier passage | trompeur |
| `diagnostic.py` | 4 règles en français clair | 5 seuils sans provenance | `HIGH_CONCENTRATION = 0,40` signale « une seule ligne pèse 60 % » pour un ETF monde à 1 400 lignes, c'est-à-dire **la recommandation canonique** ; le seuil de Sharpe rend un portefeuille raisonnable muet ou « critique » selon un bouton de réglage ; texte « baisse de 30 à 40 % » codé en dur, identique à σ = 21 % et σ = 45 % | trompeur |
| `bengen.py` | Capital pour un revenu cible ; durée pour l'atteindre | 4 % transposable à la France, nominal | US 1926-1976, 60/40, taux **réel** initial appliqué à un capital **nominal** ; `r/12` au lieu du taux géométrique (+30 pb) ; route morte, constante dupliquée côté front | trompeur |
| `scanner.py` | ΔSharpe d'un ajout à 10 % | 50 jours communs suffisent | Algèbre correcte sur du bruit : top 10 de ~120 candidats sur σ̂ et ρ̂ à 50 observations = biais de sélection pur ; μ_c ≈ constant donc **écran de momentum 5 ans déguisé** ; `.PA` ⇒ éligible PEA ; renvoie des **actions** alors que l'UI promet des ETF | trompeur |
| `glide_path.py` | Âge + horizon → (σ_max, μ, DD) | CML de r_f à actions monde à σ = 20 % | Sharpe constant 0,225, **contredit `risk_levels.yaml`** ; « −2σ » étiqueté « drawdown pire année » (c'est le quantile 2,3 % d'un rendement annuel, pas un drawdown ; le vrai est −25 à −35 % pour σ = 20 %) ; plafonds « CFA Institute » non sourcés ; aucun appelant | imprécis |
| `shrunk_covariance` | Σ « Ledoit-Wolf » | δ fixé à 0,20 | δ*, tout le contenu de Ledoit-Wolf, remplacé par une constante ; cible à corrélations nulles → sous-estime w′Σw pour un livre long-only corrélé → **le plafond de risque est appliqué sur un σ sous-estimé** ; « Actuel » calculé avec Σ échantillon, « Optimal » avec Σ rétréci | imprécis |
| `stress.py` | P&L cumulé sur 3 fenêtres | Chaque ligne a un historique sur la fenêtre | Trois fenêtres, toutes post-2020 : ni 2008, ni 2000-2002, ni 2011 ; la pire baisse des 40 dernières années est structurellement exclue de l'écran « combien je peux perdre » | trompeur |
| `optimizer.py` | Allocation SLSQP, frontière, contributions au risque, Kelly | μ, Σ ponctuels sont la vérité | Poids « actuels » sur `total_capital` mais μ/σ « actuels » sur la seule poche ETF → deux pools différents comparés ; enveloppes classées brut contre net (`tax_status` lu et jamais utilisé : PEL 1,75 % brut et fonds euros 2,5 % brut classés au-dessus du Livret A 2,4 % net) ; `liquidity_days` jamais utilisé (PEL bloqué 4 ans alloué pour un horizon 1 an) ; pas de FX (cours en devise de cotation sommés comme des euros) | trompeur |
| `timeseries.py` | Base 100 vs CW8, drawdown, Sharpe glissant | Benchmark aligné sur l'index du portefeuille | `benchmark` peut être plus court que `dates` → courbe **décalée** au tracé ; Sharpe glissant 126 jours : erreur-type ≈ 1,4, c'est du bruit | imprécis |
| `dashboard.py` | Métriques, corrélation, insights, stress | Poids = poche ETF seulement | Un utilisateur 80 % Livret A / 20 % Nasdaq est décrit « très dynamique » ; CVaR à poids constants et MaxDD à parts constantes dans le même objet | imprécis |
| `analytics.cvar_95` | ES quotidien à 5 % × √252 | ES se met à l'échelle en √T | Quantité non définie ; signe contraire à la docstring ; **affiché nulle part** | cosmétique |
| `analytics.kelly_leverage` | Σ⁻¹(μ − r_f) | Σ inversible, μ connu | Σ quasi singulier sans garde ; sans contenu vu SE(μ̂) ; levier impossible en PEA ; **affiché nulle part** | cosmétique |
| `envelopes.yaml`, `cma.yaml`, `brokers.yaml`, `RISK_FREE` | Taux, plafonds, hypothèses | Fichiers à jour | Aucun champ `as_of` ; taux révisables chaque février/août sans test de fraîcheur ; r_f = 2,5 % > Livret A 2,4 % net → **l'actif sans risque de l'app a un Sharpe négatif** | imprécis |

### 3.3 Ce qui est ignoré partout, et si l'utilisateur en est informé

| Ignoré | Où ça compte | L'utilisateur est-il prévenu ? |
|---|---|---|
| Fiscalité : PFU 31,4 %, PS 18,6 % en PEA après 5 ans, abattement AV, déduction PER | projection, rééquilibrage, classement des enveloppes, Bengen | Partiellement (« avant impôt » sur Projection) |
| Inflation | tout horizon > 3 ans ; les 4 % de Bengen sont un taux réel | **Non, l'UI affirme le contraire** |
| Rééquilibrage, glide path | un Monte-Carlo 30 ans à composition figée | Non |
| Flux autres qu'un versement nominal constant | retraits, apports, indexation, interruptions | Non |
| Devise | tout titre coté hors euro sommé comme de l'euro | Non |
| Dividendes, retenue à la source | classe distribuante en CTO | Non |
| Survivance, sélection | « comme si détenu » 5 ans sur les gagnants d'aujourd'hui ; scanner sur une tranche ordonnée par Yahoo | Docstring seulement |
| Frais de transaction, spread, TTF 0,3 % | instructions de rééquilibrage | Non |
| Crédits et immobilier dans la vue risque | soustraits du patrimoine net, sans amortissement ni risque de taux | Non |
| Liquidité (PEL 4 ans) | l'optimiseur peut allouer à un produit bloqué | Non |
| Erreur d'estimation sur μ, σ, ρ | chaque chiffre de l'app | Non |

### 3.4 Six rendements attendus différents coexistent

1. Dashboard / optimiseur / scanner : mélange 70 % CMA + 30 % historique 5 ans.
2. Projection : 100 % historique 5 ans du portefeuille réel.
3. `profile.target_annual_return` : les cinq crans (3 à 11 %).
4. `glide_path.target_return` : CML r_f → 7 % à 20 % de vol.
5. `BengenRequest.expected_return` : 8 %.
6. `WITHDRAWAL_RATE = 0.04` dupliqué dans `bengen.py` et `Projection.tsx`.

Plus trois conventions de composition mensuelle (`(1+μ)^(1/12)−1`, `r/12`,
`pct/12`), deux taux sans risque, deux valorisations totales (yfinance vs
Powens), deux seuils de matérialité (5 % / 500 € vs 0,5 € / 0,5 % vs 1 %).

### 3.5 Couverture de tests

196 tests backend. **Aucun** sur `optimizer`, `projection`, `cma`, `bengen`,
`stress`, `glide_path`, `scanner`, `envelopes`, `timeseries`. Aucun sur
`monte_carlo_projection`, `deterministic_projection`, `goal_probability`,
`shrunk_covariance`, `kelly_leverage`, `annualized_stats`, `portfolio_stats`,
`_solve_slsqp`, c'est-à-dire sur chaque fonction qui produit un chiffre
affiché en gros. Le test du TER vérifie le mécanisme, jamais s'il faut
l'appliquer. Le test du profil vérifie que les cinq crans sont contigus et
monotones, jamais qu'ils sont atteignables.

---

## 4. Le fossé, levier par levier

| Levier | Ce que fait un professionnel | Ce que fait Tangent | Coût pour l'utilisateur |
|---|---|---|---|
| Mandat et profil | Questionnaire MiFID II en cinq dimensions (connaissance, expérience, situation financière, capacité de perte, objectifs et tolérance), objectifs datés avec passifs, capital humain, profil traduit en bande de volatilité **cohérente avec une frontière** | Cinq questions, un curseur 1-5 dont les paires (μ, σ) ne sont sur aucune frontière, un objectif unique | Le prudent est poussé vers du risque, le dynamique reçoit « vise moins haut » |
| Hypothèses de marché | 10 à 200 classes, par briques, datées, en fourchettes, réel et nominal, couvertes et non couvertes, recalibrées chaque année, converties en arithmétique avant MVO | 3 tickers, 7 % par défaut, sans date, sans réel/nominal, log et arithmétique mélangés, non utilisées par la projection | Un fonds monétaire classé meilleur actif ; six μ contradictoires |
| Allocation stratégique | MVO **régularisée** (Ledoit-Wolf δ*, Black-Litterman, rééchantillonnage, contraintes) ou budgets de risque, sur classes d'actifs, testée en Monte-Carlo ; 1/N et marché comme référence | SLSQP sur tickers, Σ « Ledoit-Wolf » à δ = 0,20 fixe et cible identité, `max_sharpe` non convexe à un départ, `res.success` ignoré | Recommandations en euros indiscernables du bruit (SE(Sharpe) ≈ 0,46 sur 5 ans) |
| Enveloppes et fiscalité | Localisation des actifs, séquencement avec horloges, test de TMI pour le PER, ordre des retraits, bandes fiscales élargies | `tax_status` lu et jamais utilisé ; PEL 1,75 % brut classé au-dessus du Livret A 2,4 % net ; aucune fiscalité dans la projection | 60-90 pb/an de TCAM net ; 3-8 k€ par 10 k€ de PER |
| Frais | Coût total de détention : contrat + fonds + courtage + retenue à la source, sans double compte ; le TER est dans les rendements nets | TER retranché une seconde fois ; rétrocessions facturées ; broker le plus cher par défaut ; `boursorama` autodétecté mais absent de la table | Capital final sous-estimé de 2,5 à 14 % ; comparaison de courtiers faussée |
| Rééquilibrage | Bandes 5/25, versements d'abord, étalé, avec coûts et impôts dans l'objectif | Aucun ; le Monte-Carlo 30 ans suppose une composition en parts figée | 12-25 pb/an ; dérive d'un 60/40 vers 80/20 en une décennie |
| Simulation | Bootstrap par blocs ou Student-t, inflation jointe, régimes, incertitude sur μ, 5 000-100 000 chemins, euros réels, problème inverse | Gaussien i.i.d., 1 000 chemins, nominal en disant réel, incertitude sur μ ignorée (cône deux fois trop étroit), probabilité terminale | Faux sentiment de précision : « 8 fois sur 10 » |
| Risque | ES sur l'horizon, stress historiques longs (1973, 2000, 2008, 2011, 2022) sur indices raccordés, corrélations de crise, drawdown / Ulcer | 3 fenêtres post-2020, NaN ignorés (panier partiel × capital total), CVaR quotidien × √252 non affiché, « −2σ » appelé drawdown | Le « combien je peux perdre » est faux dans les deux sens |
| Retraite | SAFEMAX sur données locales, garde-fous, sourire, ratio de financement, rente | 4 % de Bengen, US, nominal, sans inflation ; route morte, constante dupliquée | Capital nécessaire sous-estimé ; 4 % échoue dans plus de la moitié de l'histoire française |
| Comportement | Fréquence d'évaluation contrôlée, versements automatiques, garde-fous, écart de comportement mesuré | Briefing quotidien « à faire cette semaine » ; pas de TRI ; scanner d'actions | Aggrave le levier n° 4 au lieu de le réduire |
| Mesure de performance | TWR pour la stratégie, TRI pour le client, benchmark de politique, attribution | « Comme si détenu aujourd'hui » : biais de sélection, look-ahead sur les constituants ; benchmark décalé au tracé | Rendement passé gonflé, drawdown minimisé |
| Univers | Classes d'actifs à rôle économique ; jamais d'actions en direct pour un particulier | Tickers ; 60 % du patrimoine (fonds euros, PER, UC, SCPI) exclu ; scanner d'actions Euronext | L'app raisonne sur la poche la moins importante |
| Preuve | Tests sur chaque fonction produisant un chiffre ; backtests EUR ; Sharpe déflaté | Aucun test sur optimiseur, projection, CMA, Bengen, stress, glide path, scanner | Les bugs 2, 6, 8 sont en production depuis des mois |

---

## 5. Ce que le cursus enseigne, et ce qu'un moteur pour épargnant doit en retenir

Le savoir est public et gratuit. Le tableau ci-dessous est la carte du cursus,
du niveau licence au niveau praticien, avec pour chaque brique ce qu'elle
apporte à un moteur de patrimoine. Détail (80 sources, syllabus vérifiés)
dans le rapport de session « 04-curriculum ».

### 5.1 La carte

| Niveau | Question | Canon | Ce que le moteur doit en prendre |
|---|---|---|---|
| 1. Fondations | Qu'est-ce qu'un rendement, un taux réel, une obligation ? | MIT 15.401 (Lo), Yale ECON 252 (Shiller), Wharton, Khan Academy, Genève/UBS « Investment Management » (Coursera), AMF FUN-MOOC, Jacquillat-Solnik-Pérignon, Granger (Dauphine, cours CEA), Poincelot | Toute projection en **réel et nominal explicites**, en **taux géométrique** ; g ≈ μ − σ²/2 est la formule la moins enseignée aux particuliers ; le trio « rendement attendu, risque, dépendance » est l'entrée minimale |
| 2. Théorie du portefeuille | Comment combiner des actifs ? | Bodie-Kane-Marcus, Elton-Gruber, MIT 18.S096 L14-16, EDHEC (Coursera, 4 cours Python), Roncalli (risk parity, solutions libres sur arXiv), Meucci, Fabozzi (robuste), Ledoit-Wolf, Black-Litterman (Idzorek), HRP (López de Prado), DeMiguel 1/N, ISFA (revue française : paradoxe de Markowitz, rééchantillonnage, ruine) | **La part risquée y* = (μ−r)/(Aσ²) (Merton) au lieu d'un curseur arbitraire** ; Ledoit-Wolf avec δ* analytique ; 1/N et capitalisation comme hypothèse nulle ; vues explicites (BL) pour dévier du marché ; budgets de risque plutôt que poids en capital ; pipeline Meucci (invariants → estimation → projection → évaluation → optimisation) |
| 3. Prix des actifs, facteurs | D'où viennent les rendements attendus ? | Cochrane (cours libre), Ang « Asset Management », Ilmanen (monographie CFA gratuite), Fama-French (bibliothèque de K. French, jeux Europe), AQR, Pedersen, Grinold-Kahn, Damodaran (ERP mensuel), Stanford MS&E 245 | CMA **par briques** (D/P + croissance + inflation + valorisation ; obligations par rendement courant) rafraîchies chaque année ; rendements **conditionnés à la valorisation** ; loi fondamentale IR = IC√BR : avec 5 ETF rééquilibrés une fois l'an, l'« actif » discrétionnaire vaut ~0 |
| 4. Allocation en pratique | Quel portefeuille pour un ménage, et comment le tenir ? | Swensen, Bernstein (bonus de rééquilibrage, risque profond vs superficiel, portefeuille de couverture du passif), Bogleheads (règle 5/25), Vanguard (rééquilibrage, Advisor's Alpha, DCA), Kommer (« risikofrei / risikobehaftet »), Épargnant 3.0, Avenue des Investisseurs, r/vosfinances, justETF, Curvo, portfoliocharts, Newfound (chance de date de rééquilibrage), Perold-Sharpe, CPPI, Faber, Campbell-Viceira | Peu de classes d'actifs à rôle économique distinct ; **bandes 5/25, versements d'abord, rééquilibrages étalés** ; bucket sans risque dimensionné par capacité puis résidu risqué ; CPPI seulement pour un objectif à plancher dur ; backtests en EUR sur indices raccordés aux ETF UCITS ; l'actif « sûr » à 30 ans est une obligation indexée, pas le cash |
| 5. Risque | Comment mesurer et borner les pertes ? | McNeil-Frey-Embrechts (ETH), Roncalli « Handbook » (Paris-Saclay), Bouchaud-Potters (Polytechnique, queues épaisses, nettoyage RMT des corrélations), Tsay (GARCH, régimes), Glasserman (Monte-Carlo), FRM, Quantopian (notebooks archivés : instabilité des estimations), Chow-Kritzman, Ang-Bekaert | ES à 95/99 % **sur l'horizon du client** plus ES stressé ; Student-t ou bootstrap par blocs ; corrélations de crise, pas moyennes ; « pire mois / pire année » plutôt qu'écart-type ; montrer l'instabilité des estimations à qui demande un portefeuille « optimisé » |
| 6. Planification, cycle de vie, retraite | Combien, combien de temps, comment décumuler ? | Merton, Samuelson, Bodie-Merton-Samuelson (capital humain), Cocco-Gomes-Maenhout, Elm Wealth (part de Merton avec μ prospectif), Bengen, Trinity, ERN (64 parties, dont SWR conditionné au CAPE), Kitces (garde-fous par probabilité de succès, cliquet, tente obligataire), Pfau (ratio de financement, RISA), Blanchett (sourire de dépenses), Milevsky (7 équations, Gompertz, ruine), Sharpe RISMAT, Waring-Siegel ARVA, CFA niveau III Private Wealth, Stanford CME 241 | Glide path dérivé du **capital humain**, pas de l'âge ; **ratio de financement** par objectif à un taux réel sans risque ; règle de retrait = garde-fous par probabilité de succès recalculée chaque année plus cliquet, ou ARVA ; sourire de dépenses (−1 %/an réel) ; mortalité Gompertz plutôt que 30 ans fixes ; rente viagère / PER en rente comme décision d'allocation de produit |
| 7. Comportement | Pourquoi les gens échouent, comment concevoir autour ? | Kahneman-Tversky, Thaler (Nudge, Save More Tomorrow), Benartzi-Thaler (aversion myope aux pertes), Barber-Odean, Odean (disposition), Shefrin-Statman, Das-Markowitz-Scheid-Statman (comptes mentaux sur la frontière), Chhabra, Brunel, Morningstar Mind the Gap, Illinois Investments II | **Contrôler la fréquence d'évaluation** (cacher le P&L quotidien), cadrer en ratio de financement, versements automatiques avec escalade, compteur du coût de l'activité, mesurer l'écart de comportement du client (TRI vs TWR), sous-portefeuilles par objectif avec contrainte de sécurité (théoriquement efficient et comportementalement supérieur) |
| 8. Mise en œuvre, fiscalité, coûts, outillage | Comment exécuter, pas cher et fiscalement ? | Bogle, Vanguard (2 % vs 0,1 % = −43 % à 30 ans), justETF (TER vs coût total), Kitces (localisation, bandes élargies de 1/(1−t)), CFA III, r/vosfinances, Boyd et al. (cvxportfolio : optimisation avec coûts → zones de non-transaction), PyPortfolioOpt, Riskfolio-Lib, skfolio, QuantLib, López de Prado (Sharpe déflaté, PBO, validation croisée purgée), Solnik, PWL (couverture de change) | Coût total de détention avec frais d'enveloppe et retenue à la source ; **séquencement des enveloppes** (livret → PEA → AV → PER si TMI ≥ 30 % → CTO) comme règle explicite avec horloges 5 ans / 8 ans ; localisation des actifs ; rééquilibrer avec l'argent frais et dans les enveloppes sans impôt ; ne pas réimplémenter les optimiseurs ; tout tilt doit passer un test de Sharpe déflaté ; actions monde non couvertes, obligations étrangères couvertes, biais domestique plafonné et affiché |

### 5.2 Les dix principes de conception qui ressortent de tout le cursus

1. **Primitive de dimensionnement = part de Merton** avec γ élicité (2 à 4) et rendements attendus fondés sur la valorisation, pas un curseur à cinq crans.
2. **Modèle objet = objectifs avec passifs**, chacun avec un ratio de financement à un taux réel sans risque et une contrainte de sécurité (Roy, Das-Markowitz-Scheid-Statman, EDHEC, Pfau).
3. **Architecture à deux poches** : couverture du passif / plancher (fonds euros, OATi, rente) plus portefeuille de performance (Bernstein, Kommer, Swensen).
4. **Construction** : cœur mondial en capitalisation ; déviations exprimées en vues Black-Litterman ou budgets de risque ; Σ Ledoit-Wolf ou nettoyée ; HRP/ERC comme alternatives robustes ; optimisation robuste sur μ.
5. **Dynamique** : mélange constant avec bandes 5/25, versements d'abord, rééquilibrages étalés, optimisation à une période avec termes de coût et d'impôt ; CPPI seulement pour un plancher dur.
6. **Reporting du risque** : ES et drawdown (Ulcer) sur l'horizon, corrélations de stress, Monte-Carlo Student-t ou bootstrap, régimes, sensibilité à la date de départ.
7. **Cycle de vie** : glide path par capital humain ; retraite par garde-fous de probabilité de succès plus cliquet, ou ARVA ; sourire de dépenses ; Gompertz ; rente comme allocation de produit.
8. **Comportement par conception** : cadrage long terme, P&L quotidien caché, versements automatiques à escalade, compteur d'activité, rapport d'écart de comportement.
9. **Fiscalité et enveloppes** : localisation, séquencement avec horloges et test de TMI, bandes élargies, pertes récoltées en CTO.
10. **Discipline de preuve** : backtests EUR sur indices raccordés, Sharpe déflaté pour tout tilt, CMA publiées par briques.

### 5.3 Méthode par méthode : est-ce dans Tangent, et combien ça vaut pour un épargnant français

| Méthode | Source canonique | Dans Tangent ? | Valeur pour un épargnant français |
|---|---|---|---|
| Valeur actuelle, réel vs nominal, géométrique vs arithmétique | MIT 15.401 | Partiel : géométrique OK dans la projection, mais nominal partout et mélange log/arithmétique dans le blend | haute |
| Part de Merton y* = (μ−r)/(Aσ²) | BKM ch. 6 ; Merton 1969 ; Elm | Non (curseur 1-5 arbitraire) | haute |
| Contrainte de sécurité par objectif (Roy) | Elton-Gruber ; DMSS 2010 | Non | haute |
| Ledoit-Wolf avec δ* | ledoit.net/honey.pdf | Non (δ = 0,20 constant, cible identité) | haute |
| Black-Litterman | Idzorek | Non | moyenne |
| Optimisation robuste sur μ | Fabozzi ; skfolio | Non | moyenne |
| Risk parity / ERC / budgets de risque | Roncalli (arXiv 1403.1889) | Partiel : contributions d'Euler affichées, pas d'optimisation | haute |
| HRP / HERC | López de Prado 2016 | Non | moyenne |
| 1/N et capitalisation comme hypothèse nulle | DeMiguel-Garlappi-Uppal | Non | haute |
| Régression factorielle des ETF | K. French (Europe) ; Portfolio Visualizer | Non | moyenne |
| CMA par briques (D/P + g, rendements courants) | Ilmanen CFA-RF ; AQR | Non (3 tickers codés en dur, 7 % par défaut) | haute |
| Rendements conditionnés au CAPE | Cochrane ; ERN | Non | moyenne |
| Classes d'actifs à rôle économique | Swensen | Non (l'app ne connaît que des tickers) | haute |
| Bonus de rééquilibrage, risque profond, LMP | Bernstein | Non | haute |
| Bandes 5/25, versements d'abord | Bogleheads ; Vanguard | Non | haute |
| Chance de date de rééquilibrage | Newfound | Non | moyenne |
| Mélange constant vs CPPI vs buy-and-hold | Perold-Sharpe ; EDHEC | Non | haute |
| CPPI / plancher pour objectif dur | EDHEC C1 | Non | moyenne |
| Tendance (SMA 10 mois), ciblage de volatilité | Faber ; Harvey et al. | Non | basse |
| Optimisation avec coûts (zones de non-transaction) | Boyd cvxportfolio | Non | moyenne |
| Allocation discrète en parts d'ETF | PyPortfolioOpt | Non | haute |
| VaR / ES / Cornish-Fisher sur l'horizon | McNeil-Frey-Embrechts ; Roncalli | Non (CVaR quotidien × √252, non affiché) | haute |
| Max drawdown, Ulcer, CDaR | portfoliocharts ; Riskfolio | Partiel (max DD observé, avec le bug NaN) | haute |
| Monte-Carlo Student-t ou bootstrap par blocs | Portfolio Visualizer ; MIT 15.450 | Non (gaussien i.i.d.) | haute |
| GARCH, régimes, corrélations de stress | Tsay ; Kritzman | Non | moyenne |
| Glide path par capital humain | BMS 1992 ; Campbell-Viceira | Non (règle 120−âge, sans appelant) | haute |
| Obligations réelles longues comme actif sûr à long terme | Campbell-Viceira ch. 3 | Non | moyenne |
| Ratio de financement à taux réel | Pfau ; CFA III PW | Non | haute |
| SAFEMAX historique en EUR, risque de séquence | Bengen ; Pfau ; ERN | Non (4 % US nominal) | haute |
| Retrait dynamique conditionné au CAPE | ERN partie 54 | Non | moyenne |
| Garde-fous par probabilité de succès plus cliquet | Kitces | Non | haute |
| ARVA | Waring-Siegel ; Sharpe RISMAT | Non | moyenne |
| Sourire de dépenses | Blanchett | Non | moyenne |
| Gompertz, ruine, prix d'une rente | Milevsky | Non | haute |
| Glide path montant en retraite | Pfau-Kitces 2014 | Non | moyenne |
| Théorie des perspectives, fréquence d'évaluation | Kahneman-Tversky ; Benartzi-Thaler | Non (le briefing quotidien fait l'inverse) | haute |
| Défauts, auto-inscription, Save More Tomorrow | Thaler-Benartzi | Non | haute |
| Coût de l'activité, effet de disposition | Barber-Odean | Non | haute |
| Écart de comportement (TRI vs TWR) | Morningstar | Non (pas de TRI, pas de journal de transactions exploité) | moyenne |
| Comptes mentaux / sous-portefeuilles par objectif | DMSS ; Chhabra ; Brunel | Non (un seul objectif) | haute |
| Coût total de détention avec frais d'enveloppe et retenue à la source | justETF ; Vanguard | Partiel (frais de courtage, TER double compté) | haute |
| Séquencement des enveloppes (livret → PEA → AV → PER par TMI → CTO) | r/vosfinances ; Épargnant 3.0 ; ADI | Non | haute |
| Localisation des actifs, bandes fiscales | Kitces ; CFA III | Non | haute |
| Récolte de pertes en CTO | Kitces ; AQR | Non | basse |
| Actions non couvertes, obligations couvertes, biais domestique plafonné | Solnik ; PWL ; Vanguard | Non (pas de FX du tout) | haute |
| Modélisation du fonds euros (garanti, lissé, retardé sur l'OAT) | Le Blog Patrimoine ; ACPR | Non (solde exclu de toute analyse) | haute |
| Immobilier et crédit dans le bilan du ménage | ADI ; Le Blog Patrimoine | Partiel (soustraits du patrimoine net) | haute |
| Historique français long, régimes de risque profond | DMS ; Jordà ; Pfau 2010 | Non | moyenne |
| Sharpe déflaté / PBO pour tout tilt | López de Prado ; skfolio | Non (le scanner est l'exemple type du biais de sélection) | moyenne |
| Backtests EUR sur indices raccordés | Curvo | Non | haute |
| Attribution vs benchmark de politique (Brinson) | CFA III | Non | moyenne |
| Champs d'adéquation MiFID/AMF et échelle SRI dans le profil | AMF | Non (5 questions, pas de capacité de perte) | haute |

Bilan : sur 51 méthodes canoniques, Tangent en implémente 0 complètement,
6 partiellement (dont 3 avec un bug), 45 pas du tout. Les 20 méthodes
classées « valeur haute » sont toutes absentes ou cassées.

---

## 6. Robo-advisors et gestions pilotées : comment ils passent du profil au portefeuille, et ce qu'ils livrent

### 6.1 Deux architectures, et seulement deux

Toutes les offres publiées se rangent dans l'une des deux familles :

- **L'échelle de score** : le score de risque est directement une part
  d'actions ou une cible de volatilité. Indexa 0-10 (8/10 = 80 % actions),
  Nutmeg 1-10 (~15 % à ~95 %), quirion 10-100 %, Yomoni P1-P10 (P6 = 50/50,
  P10 = 100 % actions), Wealthfront 0,5-10. Simple, auditable, et c'est ce
  qu'un questionnaire MiFID produit naturellement.
- **Le glide path par objectif et horizon** : les années restantes dominent,
  la tolérance ne fait que décaler la courbe. Betterment (90 % d'actions à
  20 ans et plus → 56 % à la retraite → 30 % en décumulation, part obtenue en
  maximisant la moyenne des percentiles 5 à 50 des richesses terminales),
  Vanguard Digital Advisor (modèle de cycle de vie à utilité, plus de 1 000
  glide paths candidats notés sur 10 000 trajectoires VCMM), Nalo (85 %
  d'actions au-delà de 25 ans → 50 % à 10 ans → 30 % à 5 ans), Ramify
  (sigmoïde de l'horizon, inflexion à 8 ans), et **la grille légale du PER**.

Tangent n'est dans aucune des deux : cinq crans dont les paires ne
correspondent ni à une part d'actions cohérente ni à un horizon.

### 6.2 La grille légale du PER (arrêté du 7 août 2019, vérifiée sur Légifrance)

Part minimale d'actifs à faible risque (SRI PRIIPs ≤ 2, soit volatilité
< 5 % : fonds euros, monétaire, obligations courtes) selon les années avant
la liquidation envisagée :

| Années avant la retraite | Prudent horizon | **Équilibré horizon (défaut légal)** | Dynamique horizon |
|---|---|---|---|
| > 10 ans | ≥ 30 % | aucun minimum | aucun minimum |
| de 10 à 5 ans | ≥ 60 % | ≥ 20 % | aucun minimum |
| de 5 à 2 ans | ≥ 80 % | ≥ 50 % | ≥ 30 % |
| < 2 ans | ≥ 90 % | ≥ 70 % | ≥ 50 % |

Rien ne prescrit une part d'actions maximale ni un rendement attendu : ce
sont des planchers. Un moteur français qui projette un PER doit respecter
cette grille par construction. Tangent ne connaît pas le PER autrement que
comme un solde.

### 6.3 Ce que les acteurs publient, et ce qu'ils ont livré

| Acteur | Profils | Méthode profil → portefeuille | Rendement attendu publié | Performance nette réalisée |
|---|---|---|---|---|
| **Indexa** (ES) | 0-10 | 10 questions → échelle d'actions | **Oui** : actions 5,5 %, obligations 3,5 % (moyenne des CMA BlackRock, Franklin, JPM, State Street, Vanguard, nette de TER) ; 8/10 : σ 11,45 %, fourchette 1 an −18 % / +27 % | 8/10 : **8,2 %/an** 2016-2025, σ 9,9 %, Sharpe 0,76, pire baisse −24,8 % ; 10/10 ≈ 9-10 % ; 0/10 ≈ 1,5-2 % |
| Betterment (US) | 101 allocations, glide paths | Objectif + horizon ; Black-Litterman sur CAPM inversé moyenné avec les CMA BlackRock/Vanguard/SSGA | Non (méthode oui) | 90/10 ≈ 8-9 %/an 2015-2025 |
| Wealthfront (US) | Score 0,5-10 | min(subjectif, objectif) pondéré vers le plus prudent, pénalité d'incohérence → MVO | Table dans le livre blanc (≈ 5,8 % actions, 2,7 % obligations historiquement) | Score 8 ≈ 8-9 %/an |
| Vanguard Digital Advisor | > 1 000 glide paths | VLCM (utilité CRRA avec aversion aux pertes) sur VCMM | Fourchettes VCMM publiques (actions US 4,2-6,2 % en 2026) | ≈ 7-8 %/an (90/10) |
| Scalable Capital (DE) | VaR 3-25 % (abandonné) | Ciblage de VaR à 1 an, réallocation selon volatilité prévue | — | **Échec documenté** : 2020 de −3,85 % à −10,08 % (MSCI World +6 %) ; 2017-2023 VaR 25 % +11,4 % cumulé vs +77 % pour un ETF monde ; retiré aux nouveaux clients en 2024 |
| Ginmon (DE) | 1-10 | Échelle + tilts factoriels | **Oui** : 3,12 % (1) à 8,74 % (10) | Global 10 +128,7 % 2016-2024 (≈ 9,6 %/an) |
| **Yomoni** (FR) | P1-P10 (P6 = 50/50, P10 = 100 % actions) | Questionnaire, allocation stratégique fixe + tactique légère, 100 % ETF | Non (Linxea affiche des « objectifs » 3/5/6-7/8 % sans probabilité) | P10 : **8,6-9,2 %/an** depuis 2015 ; P6 ≈ 4,0 % ; P2 ≈ 2 % |
| **Nalo** (FR) | 404 allocations par projet | Horizon et capacité → part d'actions ; sécurisation progressive 85 → 50 → 30 % | Non | 100 % actions ≈ 9 %/an 2018-2025 ; défensif ≈ 1,7 % 2020-2025 |
| **Ramify** (FR) | 0-10 × 3 gammes | Sigmoïde de l'horizon × expérience × projet → BL-MVO avec CVaR ; livre blanc publié | Dans l'app seulement (≈ 2-3 % à 7-8 %) | Flagship 10 : 11,8 %/an depuis le lancement (backtest avant déc. 2021) ; Flagship 1 : 2,1 % |
| Goodvest, MPP, WeSave, Cashbee (FR) | 4-10 | Questionnaire → mélange fixe | Non | Goodvest 1,6 à 7,2 % (backtest jusqu'en 2021) ; MPP Intrépide 11,8 % ; WeSave P10 ≈ 8,7 % |
| BoursoBank (EdR, Sycomore), Fortuneo (Allianz GI), Linxea (OTEA, Yomoni), Meilleurtaux Pilot, Lucya Cardif | 3-5 | Choix d'un profil ; cibles de volatilité (EdR Défensif < 5 %, Dynamique < 16 %) | Non ; Linxea : « objectifs » ; Meilleurtaux : « 70 % de scénario favorable » | Fortuneo Dynamique ≈ 4,15 %/an 2016-2024 ; Lucya 2025 : 3,1 à 7,7 % |
| **Mandats bancaires et assureurs** (BNP, CA, SG, LCL, LBP, MAIF, Macif, AXA, Generali) | 3-4 | Questionnaire IDD → fourchette UC / fonds euros ; fonds actifs maison à 1,5-2 % ; mandat 0,2-0,5 % ; tout compris 2,4-3,5 %/an | Non ; souvent pas de track record public | **Good Value for Money, 475 offres, 2018-2024 : Prudent 2,20 %, Modéré 1,86 %, Équilibré 2,69 %, Offensif 3,79 %, Audacieux 6,16 %/an**, contre fonds euros 1,76 % et inflation 2,46 % |
| Référence : ETF MSCI World en EUR | — | — | — | ≈ 11-12 %/an 2015-2025 |

Trois lectures :

1. **Seul Indexa publie la méthode, les rendements attendus par profil et le
   track record complet.** Aucun acteur français ne publie ses rendements
   attendus. Tangent affiche un « rendement visé » par cran sans méthode :
   c'est le pire des deux mondes.
2. **Sur 2015-2025, chaque profil 100 % actions a battu son propre rendement
   attendu de 3 à 5 pts/an** (décennie exceptionnelle), **et a fait 2 à 3
   pts/an de moins qu'un simple ETF monde** (frais de 1,0-1,6 % en AV plus
   diversification). Les profils équilibrés ont fait ≈ 4 %/an chez les robos
   et ≈ 2,7 %/an dans les mandats bancaires, sous l'inflation. Verdict de
   Good Value for Money : « les gestions profilées prudentes ou modérées n'ont
   aucun intérêt pour l'épargnant ». C'est exactement ce qu'un moteur honnête
   devrait dire à un utilisateur qui détient une AV bancaire.
3. **Le seul échec méthodologique documenté est le ciblage dynamique de
   risque** (Scalable) : réduire l'exposition après la baisse et la remonter
   trop tard. Le marché a convergé vers des allocations stratégiques
   statiques avec rééquilibrage par bandes. Le « selon ton profil » de
   Tangent, qui re-résout un Markowitz à chaque appel sur 5 ans d'histoire,
   est une variante artisanale de ce qui a échoué.

### 6.4 Profilage du risque : ce que le régulateur exige, et ce que Tangent demande

Les lignes directrices ESMA 2023 (appliquées intégralement par l'AMF,
position DOC-2019-03) exigent de collecter séparément (a) connaissance et
expérience, (b) situation financière **avec capacité à supporter des
pertes**, (c) objectifs **avec tolérance au risque**, horizon, (d) préférences
de durabilité ; de ne pas se fier à l'auto-évaluation (« vous considérez-vous
comme preneur de risque ? ») mais à des exemples chiffrés de pertes et de
gains ; de vérifier la cohérence des réponses (« peu d'expérience et attitude
agressive ») ; et, spécifiquement pour le conseil automatisé, d'expliquer le
degré d'intervention humaine, de documenter, tester et surveiller
l'algorithme. Le contrôle SPOT de l'AMF (2021) a trouvé des questionnaires
trop courts, sans contrôle de cohérence, à scoring arbitraire ; l'expérience
Robex de l'ACPR (2023, 256 participants) montre que les explications
conversationnelles **augmentent** la confiance injustifiée dans un conseil
inadapté.

Ce que font les bons : Wealthfront pondère vers la composante la plus
prudente et pénalise exponentiellement l'incohérence ; Vanguard mesure
séparément l'aversion au risque et l'aversion aux pertes en montrant des
fourchettes de résultats ; Indexa laisse le client baisser son score, jamais
le monter, et a **relevé** la part d'actions du profil 8 de 67 à 80 % en 2026
après avoir vérifié que ses clients n'avaient pas retiré pendant les baisses.

Tangent : cinq questions, pas de capacité de perte, pas d'exemple chiffré,
pas de contrôle de cohérence, un curseur que l'utilisateur monte librement,
et un briefing conversationnel : le profil exact que Robex identifie comme le
plus risqué.

### 6.5 Afficher des scénarios : la méthode réglementée (DIC PRIIPs)

Chaque UC détenue en AV ou PER porte un DIC dont les scénarios sont calculés
selon le règlement délégué 2021/2268, annexe IV. C'est la seule façon
« réglementée » de montrer des scénarios en France, et elle est entièrement
empirique :

| Élément | Règle (PRIIP de catégorie 2 : fonds et ETF) |
|---|---|
| Données | Prix mensuels sur **au moins 10 ans**, et durée recommandée + 5 ans si elle dépasse 5 ans ; proxy si l'historique est trop court |
| Favorable | **Meilleur** rendement parmi toutes les sous-périodes glissantes de longueur égale à la durée recommandée |
| Intermédiaire | **Médiane** de ces sous-périodes |
| Défavorable | **Pire** sous-période, y compris les fenêtres tronquées finissant à la date de calcul, pour capturer un krach récent |
| Tensions | Volatilité glissante (63 jours), 95e percentile = volatilité stressée ; valeur au 5e percentile avec développement de Cornish-Fisher (asymétrie et kurtosis) |
| Présentation | Pour 10 000 € : « ce que vous pourriez obtenir après frais » à 1 an, mi-parcours, durée recommandée ; **la fenêtre historique d'où vient chaque scénario est nommée** ; mention que ce n'est pas un indicateur exact ; « vous pourriez perdre tout ou partie » |

Pour un moteur qui veut être cohérent avec ce que l'utilisateur lit déjà
dans ses DIC : au moins 10 ans de données mensuelles par classe d'actifs,
rendements glissants sur l'horizon, minimum / médiane / maximum et un chemin
stressé au 5e percentile, chacun annoté de sa fenêtre. Tangent utilise 5 ans
de données, une loi normale, et n'annote rien.

---

## 7. Projeter l'avenir : comment les professionnels le font, et comment un moteur naïf trompe

### 7.1 Ce qu'un moteur de projection doit absolument faire

1. **Dire ce que « 7 % » veut dire.** Un rendement *arithmétique* attendu de
   7 % à σ = 15 % donne une croissance *médiane* (géométrique) de ~5,9 %/an.
   La correction de dérive μ − σ²/2 est l'erreur d'implémentation la plus
   courante : l'omettre surestime la médiane à 20 ans de ~14 % ; l'appliquer à
   un chiffre qui était déjà un TCAM la sous-estime d'autant. Montrer la
   médiane et un cône, jamais une ligne « attendue ». (Tangent : correct sur
   ce point précis ; le μ est une dérive log empirique, donc pas de correction
   à ajouter, et « base » coïncide avec la médiane du Monte-Carlo.)
2. **Les rendements mensuels gaussiens i.i.d. sont le mauvais défaut** au-delà
   de ~10 ans : ils ignorent les queues épaisses (Student-t à 3-6 degrés de
   liberté en quotidien, 5-10 en mensuel), le clustering de volatilité
   (GARCH), la persistance des régimes (régime baissier à 1,8 × la volatilité
   et +20 % de corrélation, Ang-Bekaert), le retour à la moyenne lié à la
   valorisation (le CAPE explique 25 à 56 % de la variance des rendements
   réels à 10 ans), et le fait que la *séquence* des rendements, pas seulement
   leur moyenne, décide du résultat dès qu'il y a des versements ou des
   retraits. Les praticiens utilisent des VAR à variables d'état (Vanguard
   VCMM, 10 000 trajectoires), le bootstrap par blocs (ProjectionLab,
   Portfolio Visualizer), des régimes (Kritzman-Page-Turkington) ou des
   fenêtres historiques glissantes (cFIREsim, FI Calc, Bengen).
3. **Des entrées prospectives, en euros, réelles.** Le rendement réel des
   actions monde sur 125 ans est de 5,2 % ; celui de la France ~3,3 % ; les
   obligations ~1,7 % monde et négatives pour la France. Les estimations
   prospectives 2026 pour les actions développées en EUR se regroupent autour
   de **4,5-6,7 % nominal (~2,5-4,5 % réel)**, pas 7 % réel. Un « 7 %
   nominal » pour un investisseur euro suppose sans le dire (a) une histoire à
   l'américaine, (b) aucun effet USD/EUR, (c) aucune inflation. Sur 20 ans à
   500 €/mois, 5 % au lieu de 7 % réduit la médiane de ~20 % ; déflater de 2 %
   d'inflation la réduit encore d'un tiers.
4. **La « probabilité de succès » est un mauvais titre.** Kitces, Blanchett,
   Pfau et les éditeurs de logiciels eux-mêmes plaident pour probabilité *et*
   ampleur de l'ajustement, ratio de financement, garde-fous en euros. Sous
   une stratégie dynamique à 95 % de succès constant, 96 % des trajectoires
   historiques ont quand même exigé des coupes réelles de dépenses. Il faut
   afficher les percentiles 5/25/50/75/95, la taille des manques, et **la
   variation d'épargne qui rétablit l'objectif**.
5. **Mesurer le vrai compte en rendement pondéré par les flux, contre un
   benchmark aux mêmes flux.** Le TWR isole la stratégie (norme GIPS) ; le
   TRI/MWR répond à « qu'a gagné *mon* argent ». Un historique synthétique
   « comme si détenu aujourd'hui » est un backtest de l'allocation actuelle,
   pas l'historique du compte.

### 7.2 Les modèles de rendement (tableau A)

| Modèle | Ce qu'il capture | Paramètres utiles | Qui l'utilise | Ce qui se passe si on l'omet |
|---|---|---|---|---|
| Lognormal i.i.d. / mouvement brownien géométrique | Composition, asymétrie droite de la richesse, correction de dérive | μ_arith, σ ; mensuel : m = ln(1+μ)/12 − σ²/24, s = σ/√12 ; MSCI World EUR σ ≈ 13-15 % | Ibbotson/Morningstar, NaviPlan, RightCapital « Standard », Boldin, Finary, la plupart des robos, **Tangent** | Mauvaise dérive : ±14 % sur la médiane à 20 ans ; montre la moyenne au lieu de la médiane |
| Innovations Student-t | Queues épaisses, fréquence des krachs | ν ≈ 4-6 (quotidien), 5-10 (mensuel) ; renormaliser par √((ν−2)/ν) | Portfolio Visualizer (ν de 5 à 50), SOA | 5e percentile trop clément ; règles déclenchées par drawdown mal évaluées |
| Bootstrap par blocs / stationnaire | Autocorrélation, clustering, mouvements joints, vraies crises | b ≈ N^(1/3) (8-12 mois sur 50 ans mensuels) ; blocs annuels 1-5 ans | ProjectionLab, Portfolio Visualizer, cFIREsim | Limité à l'histoire observée ; ~3 fenêtres de 30 ans indépendantes |
| Changement de régime (Hamilton) | Marchés baissiers persistants, corrélations asymétriques | 2 états : (0,9 %, 2,8 %)/mois vs (0,1 %, 5,0 %)/mois ; corrélation +20 % en régime baissier | Kritzman-Page-Turkington, Ang-Bekaert | Risque de séquence et drawdowns pluriannuels sous-estimés |
| Retour à la moyenne / VAR à variables d'état | Rendements conditionnés à la valorisation, obligations pilotées par les taux, inflation | CAPE, taux, inflation ; VAR(1) mensuel depuis 1960 ; 10 000 trajectoires | Vanguard VCMM, Wealthfront, Amundi CASM, JPM | Un seul μ inconditionnel : trop optimiste à CAPE 40, trop pessimiste après un krach |
| GARCH(1,1) | Clustering de volatilité | α ≈ 0,05-0,1, β ≈ 0,85-0,93 (quotidien) | Portfolio Visualizer, RightCapital « Legacy », EDHEC | Fréquence de déclenchement des garde-fous fausse |
| Cornish-Fisher | Quantiles non gaussiens sans simulation | S ≈ −0,5, K ≈ 1-3 (mensuel) ; validité |S| ≤ 0,83 | EDHEC, PerformanceAnalytics | VaR gaussienne sous-estime la queue de 20-50 % |
| Copules / choc commun | Krachs joints, dépendance de queue | t-copule ν ≈ 4 ; corrélation des dépassements 0,55 vs 0,39 normal (Longin-Solnik) | Boldin, systèmes institutionnels | Bénéfice de diversification surestimé exactement quand on en a besoin |
| Inflation stochastique (Wilkie AR(1)) | Incertitude des objectifs réels, persistance | QMU 2-2,5 %, QA 0,5-0,6, QSD 1-1,5 % (euro) | Modèles actuariels, VCMM, eMoney, Boldin | Cibles réelles mal dimensionnées ; 2 % plat cache 1970 et 2022 |
| Obligations par duration + modèle de taux | Le rendement comme état ; pertes type 2022 ; reprise après hausse | R ≈ y + roll − D·Δy ; Vasicek κ 0,1-0,3, θ ≈ 3-4 % ; D ≈ 6-7 pour l'Euro Agg | AQR, Robeco, RA, Verus, JPM | Obligations en bruit normal à faible σ : jamais de −17 % (Euro Agg 2022 : **−17,17 %**), jamais de reprise pilotée par les taux |
| Change (UIP/PPP) | Effet USD/EUR sur le MSCI World (~70 % USD), coût de couverture | σ_FX ≈ 8-10 % ; coût de couverture ≈ r_USD − r_EUR ≈ 1,5-2 % en 2026 | AQR, Amundi, RA | L'investisseur euro voit des chiffres USD ; le dollar monte en crise (MSCI World 2007-09 : −57,8 % USD, ~−50 % EUR) |

### 7.3 Le Monte-Carlo en planification : la pratique

- **Trajectoires** : l'erreur-type d'une probabilité de succès p sur N
  chemins est √(p(1−p)/N) : à p = 0,85, ±1,6 pt à 500, ±1,1 à 1 000, ±0,5 à
  5 000, ±0,36 à 10 000. Pratique : NaviPlan 500 ; MoneyGuidePro, eMoney,
  RightCapital, Boldin 1 000 ; Finary 5 000 ; Ally 10 000 ; Vanguard Nest Egg
  5 000 → 100 000 ; VCMM 10 000 par classe. Graine fixe et **nombres
  aléatoires communs** entre scénarios pour que « épargner 50 € de plus » ne
  soit pas noyé dans le bruit (Glasserman) ; variables antithétiques gratuites.
- **Cônes** : Finary 5/50/95 ; NaviPlan et Boldin 10/50/90 ; Morningstar
  5/25/50/75/95. Recommandation : 5/25/50/75/95 en **euros réels**, médiane
  étiquetée « typique », jamais « attendue ».
- **Pourquoi la probabilité de succès trompe** : binaire et aveugle à
  l'ampleur (un plan à 85 % dont les échecs demandent −5 % domine un plan à
  90 % dont les échecs signifient vendre la maison) ; un plan dynamique change
  le sens du chiffre (à 95 % constant, 96,3 % des scénarios historiques ont
  connu des coupes réelles, 15 % de plus de 35 %) ; Blanchett recommande le
  **ratio de financement** FR = (actifs + VA des revenus futurs) / (VA des
  dépenses) avec des règles du type « à FR 1,40 : +2 %/an ; à FR 0,50 :
  −10 % » ; un Monte-Carlo i.i.d. peut être **moins** prudent que l'histoire
  parce qu'il ignore la persistance des régimes.
- **Risque de séquence** : les sommes forfaitaires sont indifférentes à
  l'ordre ; tout ce qui a des flux ne l'est pas. En accumulation, les
  mauvaises années tôt sont *bonnes* pour un épargnant régulier ; tard, elles
  frappent un gros solde (effet de taille : après 10 ans ~50 % de la
  variation annuelle vient de la croissance, 75 % après 20 ans, ~90 % après
  30 ans). Un moteur avec versements doit simuler mois par mois.
- **Versements, frais, impôts, inflation** : début vs fin de mois ≈ +0,6 % ;
  grouper 12 versements en fin d'année ≈ −2,8 % sur la médiane à 20 ans ;
  frais f/12 vs 1−(1−f)^(1/12) : < 0,1 % d'écart, ce qui compte est de les
  appliquer sur le solde (0,75 %/an retire 8,6 % de la médiane à 20 ans ;
  1 %/an sur 30 ans ~25 %) ; **le TER est déjà dans les rendements nets des
  fonds et indices** (Portfolio Visualizer, Curvo), seuls les frais de
  conseil, plateforme et enveloppe s'ajoutent ; impôts par enveloppe ; 2 %
  d'inflation transforme une médiane nominale de 227 k€ en **153 k€ réels**
  (−33 %).

### 7.4 Les moteurs de planification et leurs hypothèses (tableau B)

| Outil | Modèle de rendement | Trajectoires | Inflation | Frais | Impôts | Sortie |
|---|---|---|---|---|---|---|
| MoneyGuidePro | Normal/lognormal paramétrique sur CMA | 1 000 | Aléatoire | Entrées | Fédéral/État US | Probabilité de succès, « zone de confiance » 70-90 % |
| eMoney | Taux aléatoires selon μ, σ saisis | 1 000 | Aléatoire | Entrées | Moteur fiscal US | Probabilité à chaque âge, « âge de confiance » |
| RightCapital | Lognormal « Standard » ou volatilité stochastique « Legacy » ; géométrique (défaut) ou arithmétique (+σ²/2) | 1 000 | Hypothèse ; stress (mauvaise décennie, 0 % plat) | Entrées | Module US | Probabilité ≥ 80 %, bandes 50 %/90 % |
| NaviPlan (CMA Morningstar) | Tirages annuels normaux calés sur la moyenne géométrique | 500 | Incluse | Entrées | US/Canada | 10/50/90 |
| Morningstar / Ibbotson | Lognormal avec matrice de corrélation incluant l'inflation comme actif ; graine fixe | 500-5 000 | Simulée comme un actif | Entrées | — | 5/25/50/75/95 |
| ProjectionLab | Backtest historique (S&P 500 + dividendes, obligations, CPI US depuis 1871) et bootstrap par blocs | milliers | Historique ou fixe | Entrées | Détaillé (US) | Chance de succès, forage par essai |
| Boldin | Normal mensuel, entrée arithmétique, 100 % corrélé entre comptes | 1 000 | Aléatoire ; 3 jeux | Entrées | US | Chance de succès, 10e percentile |
| cFIREsim / FI Calc | Fenêtres historiques glissantes (Shiller 1871-) | toutes les années de départ (~120-150) | CPI historique | Frottement | Aucun | Taux de succès, trajectoires par année, règles de dépense |
| Portfolio Visualizer | Historique (mois, année, blocs), statistique (normal ou GARCH, Student-t ν 5-50), prévu, paramétré | défaut 10 000 | Historique ou paramétrée | ER intégré ; frais de conseil | Option avant/après impôt | Cônes, probabilité d'objectif, stress de séquence |
| Vanguard Nest Egg | Tirages d'années historiques depuis 1926 | 5 000 → 100 000 | Historique | Aucun | Aucun | Probabilité de survie, cône |
| Betterment | Black-Litterman (CAPM inversé moyenné avec CMA BlackRock/Vanguard/SSGA) | n.d. | Supposée | Net d'ER | Fonctions fiscales | Bande « sur la bonne voie », lignes moyenne / mauvais marché |
| Wealthfront Path | Modèle factoriel + Black-Litterman ; Monte-Carlo sur facteurs, valorisations, taux | grand | Supposée | Net d'ER | Rendements après impôt par compte | Médiane et bandes |
| Finary Predict | Monte-Carlo « simulations indépendantes puis combinées » ; paramètres non publiés ; utilisateurs signalant un sur-optimisme | 5 000 | n.d. | n.d. | n.d. | Cône 5/50/95 sur 10-30 ans |
| Yomoni | Scénarios déterministes « dérivés de la performance historique des profils », nets de frais | — | Aucune | Nets | Aucun | Une valeur par profil |
| Nalo | Monte-Carlo sur « tendance, volatilité, corrélations » ; paramètres non publiés | milliers | n.d. | n.d. | n.d. | Probabilité d'atteindre la cible |
| Kubera Fast Forward | Règles déterministes ; pas de Monte-Carlo | — | Actualisation au taux choisi | Règle | Taux estimés sur revenus | Trajectoire de patrimoine net |
| **Tangent** | Lognormal i.i.d. mensuel sur μ, σ historiques 5 ans du portefeuille ; pas de CMA | 1 000, graine 42 | **Aucune, en affirmant « euros d'aujourd'hui »** | Courtage + TER (double) | **Aucun** | 10/25/50/75/90 nominal, probabilité terminale, « atteint vers » |

Tangent est en dessous de Yomoni (qui ne prétend pas simuler) et loin de
Portfolio Visualizer (gratuit) sur chaque colonne.

### 7.5 Les rendements attendus 2026 pour les actions monde, vus d'un investisseur en euros (tableau C)

Nominaux, géométriques, 10 ans sauf mention ; « EUR » = chiffre publié en
base euro ; « USD→EUR » = chiffre USD ajusté de la dérive de change que
l'éditeur lui-même suppose (≈ −0,5 à −1,0 pt/an avec 1,5-2 pts d'écart de
taux BCE/Fed).

| Source (édition) | Actif | Horizon | Nominal EUR | Réel EUR | σ | Notes |
|---|---|---|---|---|---|---|
| **JPM LTCMA 2026**, matrice euro | Actions monde développées | 10-15 ans | **6,3 %** (7,29 % arithmétique) | ~4,2 % | **14,69 %** | AC World 6,4 % ; zone euro 7,2 % (σ 17,1) ; US 6,1 % non couvert ; cash euro 2,3 % |
| **BlackRock CMA** (août 2026), feuille EUR | MSCI World hors UEM | 10 ans | **7,16 %** | ~5,1 % | **17,71 %** | Fourchette interquartile 2,69-11,81 % ; en USD MSCI World 8,64 % : l'écart de 1,4 pt est la vue de change de BlackRock |
| **Amundi CMA 2026** | Actions monde développées | 10 ans | **6,7 %** (cash 1,8 % + prime 4,9 %) | ~4,6 % | ~16 % | Europe 7,3 % ; US 6,0 % en EUR ; profil 12 % de vol : 6,4-7,4 % |
| **Robeco 2026-2030** | Actions développées | 5 ans | **6,00 %** | **3,5 %** (inflation 2,5 %) | ~16-17 % | Régime permanent 7 % ; CAPE 31,5 vs 20 d'équilibre |
| **Vanguard VEMO 2026**, édition euro | Actions US en EUR | 10 ans | **4,3-5,3 %** | ~2,8 % | VCMM | Piloté par la valorisation des grandes capitalisations technologiques |
| **AQR 2026** | Actions développées mondiales (local) | 5-10 ans | ~6,0 % EUR | **4,2 % réel** | ~15-16 % | Zone euro 6,9 % nominal / 5,0 % réel ; 60/40 mondial 3,4 % réel |
| **Research Affiliates** | Développées hors US | 10 ans | ~7,0 % | ~5,0 % | ~17 % | US large cap seulement 3,1 % USD (retour du CAPE) |
| **Morningstar IM 2026** | Développées hors US | 10 ans | ~6,8 % | ~4,8 % | ~17 % | US 5,3 % |
| **Northern Trust 2026** | Composite mondial | 10 ans | ~6,3 % | ~4,3 % | n.d. | Décomposition : CA +3,5 %, marges +1,6 %, valorisation −0,5 %, dividende 2,0 % |
| **GMO 7 ans** (mars 2026) | Large cap internationales | 7 ans | ~2,0-2,3 % | **~−0,2 %** ; US large **−5,7 %** | ~17 % | Le plus sensible à la valorisation ; trop pessimiste sur les US depuis 2010 |
| **Schroders 2026-2055** | Actions mondiales | 30 ans | ~6,0 % | ~4,0 % | n.d. | Prime sur souverains réduite à 2,6 pts |
| **Invesco 2026** | MSCI ACWI | 10 ans | ~5,4 % | ~3,4 % | ~16-17 % | Valorisation US : −4,5 %/an |
| **Verus 2026** | MSCI ACWI | 10 ans | ~5,4 % (6,0 géo / 7,3 arith USD) | 3,3 % | **16,6 %** | EAFE 6,8 % géo, σ 17,4 % non couvert vs 15,2 % couvert |
| **Enquête Horizon Actuarial 2024** (41 cabinets) | Développées hors US | 10 / 20 ans | ~6,4 % | ~4,6 % | **18,06 %** | Dispersion entre cabinets 4,3-9,3 % |
| **Consensus Portfolio Lab 2026** (14 firmes) | Développées internationales | 10 ans | ~6,6 % (médiane 7,3 % USD) | ~4,6 % | — | Actions US : médiane 6,3 %, fourchette 3,1-9,0 % |
| Repères historiques | MSCI World net EUR : 6,64 %/an depuis 2000 ; 12,53 % sur 10 ans (σ 13,45 %) ; pire baisse −53,6 % (2001-2009) ; DMS monde réel 5,2 % ; France réel ~3,3 % | | | | | |

Lecture : les chiffres publiés en euros pour les actions monde se regroupent
à **6,0-7,2 % nominal, ≈ 3,5-5 % réel, σ 14,4-17,7 %**. Le « 7 % nominal »
naïf est au **sommet** de la fourchette professionnelle ; « 7 % réel » est
au-dessus de toutes les sources 2026. Pour un moteur mensuel lognormal, le
jeu de paramètres cohérent en 2026 pour la poche actions est **g ≈ 6,3 %
nominal EUR (μ_arith ≈ 7,3 %), σ ≈ 15 %, inflation ≈ 2,1 %**, soit une
croissance réelle médiane ≈ 4,1 %. Le 7 % par défaut de `cma.yaml`, le 10 %
du Nasdaq, le 8 % de Bengen et la moyenne 5 ans de la projection (≈ 12 % sur
2021-2026 pour un MSCI World) sont tous au-dessus.

Pourquoi « 7 % » est un défaut dangereux : c'est à la fois (a) le TCAM réel
du S&P 500 1928-2025 (10 % nominal moins 3 % d'inflation US), (b) le nominal
géométrique que montrent beaucoup de robos en euros, (c) presque la moyenne
arithmétique d'un actif à 15 % de volatilité dont la croissance médiane est
5,8 %. Chaque lecture est décalée de 1 à 3 pts des autres. Convention sûre
pour un moteur : stocker chaque hypothèse comme un quadruplet (devise, réel
ou nominal, arithmétique ou géométrique, brut ou net), afficher en EUR réel
géométrique, simuler en arithmétique, et traiter l'inflation comme une
entrée stochastique séparée.

Mélange historique / prospectif, version formelle : la moyenne historique est
un signal bruité de variance σ²/T, la CMA un prior de variance τ² ; la
moyenne a posteriori est μ̂ = w·μ_hist + (1 − w)·μ_prior avec w = τ²/(τ² +
σ²/T). Avec σ = 15 %, T = 20 ans (SE 3,4 pts) et τ = 1,5 pt (dispersion entre
éditeurs), **w = 0,16** : l'histoire pèse 16 %, la CMA 84 %. Avec T = 5 ans
(SE 6,7 pts), w = 0,05. Le 30 % historique de Tangent sur 5 ans est six fois
trop lourd ; et la projection, à 100 % historique, est hors de tout cadre.

### 7.6 Stress tests : les fenêtres qu'un moteur euro doit rejouer

Drawdowns pic-à-creux sur données de fin de mois pour un portefeuille
d'actions développées en euros (reconstruction : Fama-French développés en
USD converti en « euro synthétique » via DEM avant 1999) ; les drawdowns
quotidiens sont 2 à 8 pts plus profonds (MSCI World EUR quotidien : −53,60 %
du 24 mai 2001 au 9 mars 2009).

| Épisode | Dates | Actions monde **EUR** | USD | Obligations euro aggregate | Ce que ça teste |
|---|---|---|---|---|---|
| 1973-74 choc pétrolier | 1973 → fin 1974 | ~−45 à −50 % (en DEM) | ~−42 % | Bund > 10 %, réel fortement négatif | Stagflation : actions et obligations tombent ensemble en réel |
| 1987 | août → nov. 1987 | ~−28 à −30 % | −17 % en octobre seul | Rallye | Queue d'un jour (S&P −20,5 %), corrélations en pic |
| 1990 Golfe / Japon | juil. → sept. 1990 | **−23,5 %** | −20,3 % | Faible | Japon −50 % sur 1990-92 |
| 1998 LTCM | juil. → sept. 1998 | **−18,1 %** | −14,4 % | Rallye | Rapide, en V |
| 2000-03 dot-com | août 2000 → mars 2003 | **−52,5 %** | −44,6 % | **Positif** chaque année (+5-8 %/an) | Trois ans de glissade ; le dollar −25 % vs euro a **aggravé** la perte pour l'investisseur euro ; 60/40 ≈ −25 % |
| 2007-09 crise financière | 2007 → mars 2009 | **−48,2 %** | −53,6 % | ≈ +6 % en 2008 | Le dollar a monté : coussin pour l'investisseur euro ; MSCI World EUR 2008 ≈ −37,6 % |
| 2011 crise de l'euro | avr. → sept. 2011 | **−15,3 %** | −20,4 % | Agrégat ≈ +3 % mais Italie/Espagne −10 à −15 % ; spread OAT-Bund > 190 pb | Risque **souverain domestique** : les fonds euros (~80 % en souverain et crédit euro) étaient exposés |
| 2015-16 Chine / pétrole | avr. 2015 → fév. 2016 | **−12,1 %** | −12,5 % | ≈ 0 | Deux corrections de 10 % en six mois |
| 2018 T4 | sept. → déc. 2018 | **−12,7 %** | −14,1 % | ≈ +0,4 % | MSCI World EUR 2018 : −4,1 % |
| 2020 COVID | 19 fév. → 23 mars 2020 | **−20,4 %** fin de mois ; **≈ −30 % quotidien** | −34 % quotidien | −5 % intra-mars, +4 % sur l'année | La baisse de 30 % la plus rapide de l'histoire |
| 2022 inflation / taux | jan. → oct. 2022 | **−14,2 %** (le dollar a amorti) ; année −12,8 % | −25,5 % | **−17,17 % sur l'année**, ≈ −20 % pic-à-creux avec duration ≈ 7 et taux +2,6 pts | Les deux jambes du 60/40 tombent ; corrélation actions-obligations positive |
| 2025 droits de douane | fév. → avr. 2025 | **−11,8 %** (dollar −10 % vs euro au S1) | ≈ −5 % fin de mois / −19 % quotidien | ≈ 0 | C'est la devise, pas les actions, qui a fait la perte euro |

Deux régularités : (i) dans les crises menées par les États-Unis (2008,
2020, 2022) le dollar monte et le drawdown euro est **5 à 11 pts moins
profond** que le drawdown USD ; dans les épisodes de faiblesse du dollar
(2000-03, 2025) il est **8 à 10 pts plus profond** ; (ii) les obligations
ont amorti chaque baisse d'actions **sauf 1973-74 et 2022**, les deux
épisodes d'inflation. Une bibliothèque de stress doit contenir au moins un
régime d'inflation. Tangent en a trois, toutes post-2020, aucune
d'inflation, aucune où le dollar baisse.

Les pièges : survivance du panier (backtester les ETF d'aujourd'hui sur
2000-2026 n'utilise que les survivants : 1-3 pts/an de biais au niveau pays,
plus au niveau fonds) ; prix seul vs rendement net vs brut (un indice prix
sous-estime de ~2 pts/an ; un indice brut surestime de 0,3-0,5 pt vs ce que
touche un détenteur d'ETF UCITS) ; devise (l'euro avant 1999 est
synthétique ; couvert vs non couvert diffère du portage ≈ 1,5-2 pts/an en
2026) ; **paniers partiels et look-ahead** (rejouer seulement les poches qui
ont des données change silencieusement le portefeuille : c'est le bug
`stress.py`) ; fin de mois vs quotidien (2020 : −20 % vs −30 %) ; prix
figés des poches illiquides (SCPI, UC immobilières) ; frais et impôts dans
le rejeu. Pour les actifs sans historique : mapping vers un proxy (Portfolio
Visualizer), raccordement indice net − TER puis VL de l'ETF (Curvo),
régression sur proxy avec résidus **rééchantillonnés** (Stambaugh 1997) ;
**le fonds euros n'a pas de VL** : modéliser son taux comme une moyenne
glissante 7-8 ans des rendements IG euro, plancher 0, plus PPB ; en choc de
taux il ne marque pas au marché mais son taux futur retarde de plusieurs
années (le stress 2022 sur un fonds euros est un choc de *rendement* réel
nul 3-5 ans, pas un choc de *prix*).

### 7.7 Mesurer la performance d'un vrai compte

| Mesure | Formule | Répond à | Qui l'utilise |
|---|---|---|---|
| **TWR** (pondéré par le temps) | Chaînage des sous-périodes entre chaque flux ; valorisation à chaque flux | « Comment la *stratégie* a-t-elle performé, indépendamment du moment des versements ? » | GIPS (obligatoire), Portfolio Performance (quotidien), Ghostfolio, fiches de fonds |
| **TRI / MWR / XIRR** | Résoudre VB(1+TRI)^(RD/365) + Σ CF_t(1+TRI)^(RD_t/365) = VF | « Qu'a gagné *mon* argent, avec *mon* timing ? » | Portfolio Performance, Ghostfolio, Excel, private equity |
| **Dietz modifié** | (VF − VB − ΣC) / (VB + Σ W_i C_i) | Approximation d'ordre 1 du TRI sur une période | Sharesight, Interactive Brokers, relevés bancaires |
| Rendement simple | (VF − VB)/VB ou gain / total versé | Rien de défini dès qu'il y a des flux | Trading 212, **le P&L de Finary**, **Tangent** |

Exemple (Kitces) : 100 000 $ investis, +100 % le mois 1, versement de
200 000 $, −30 % le mois 2 : TWR **+40 %**, TRI **−10,2 %**, gain/versements
−6,7 %. Sur un ETF MSCI World en 2024 : TWR 26,33 % pour un versement unique
comme pour un plan à 100 €/mois ; TRI 26,33 % vs **25,45 %** ; le « rendement
simple » du plan sur sa valeur de départ est un 161 % dénué de sens.

Règle GIPS 2020 qui condamne le « comme si détenu aujourd'hui » : « la
performance modélisée, hypothétique ou rétro-testée doit être étiquetée
comme telle et **ne peut pas être chaînée à la performance réelle** ». La
courbe « ton portefeuille depuis 2021 » de Tangent (poids d'aujourd'hui
appliqués en arrière, flux ignorés, rééquilibrage ignoré, indices raccordés
pour des ETF qui n'existaient pas) est un backtest de l'allocation actuelle,
légitime pour dimensionner le risque, illégitime comme historique du compte.
Le vrai historique commence à la première transaction, en TWR (qualité de
l'allocation) et en TRI (résultat de l'épargnant).

Benchmark pour un épargnant français multi-enveloppes : investissable, en
EUR, net de retenue à la source, **apparié aux flux** (calculer le TRI du
benchmark avec les mêmes versements aux mêmes dates : un « portefeuille
fantôme ») ; un benchmark de politique = mélange à poids fixes des
benchmarks de poche, rééquilibré mensuellement, pour attribuer allocation
(politique vs 100 % MSCI World) et mise en œuvre (réel vs politique).

| Poche | Benchmark | Repères 2026 |
|---|---|---|
| Actions monde (PEA, CTO, UC) | MSCI World Net Total Return EUR | 6,64 %/an depuis 2000 ; 12,53 % sur 10 ans ; σ 13,45 % ; −53,6 % |
| Actions zone euro (PEA) | MSCI EMU NR EUR | — |
| Obligations euro | Bloomberg Euro Aggregate TR | 2022 −17,17 %, 2023 +7,19 %, 2024 +2,63 % ; YTM 3,57 %, duration 6,07 |
| Fonds euros | Taux moyen ACPR / France Assureurs, net de frais, avant PS | 2,63 % en 2024 et 2025 ; ≈ 2,2 % après PS ; ≈ 0,1-0,5 % réel |
| Livrets | Taux réglementé | Livret A 1,7 % ; LEP 2,7 % |
| Cash | €STR capitalisé | ≈ 2,0 % |
| **Politique ménage** 60/20/15/5 | 0,6 × World + 0,2 × Euro Agg + 0,15 × fonds euros + 0,05 × €STR | ≈ **4,9 % nominal / 2,8 % réel** attendu en 2026 |

Et l'impôt se benchmarke aussi : la même politique en CTO (PFU sur gains et
dividendes), en PEA (PS seuls après 5 ans) et en AV (7,5 % + PS après 8 ans
au-delà de l'abattement) donne trois TWR après impôt différents ; « suis-je
sur la trajectoire » se teste en TRI après impôt contre le taux après impôt
du plan.

### 7.8 Moteur de retraite et d'objectif : les quatre calculs qui manquent

**1. Part de Merton avec capital humain.** w* = (μ − r)/(γσ²) avec μ − r
arithmétique : γ = 3, μ − r = 4 %, σ = 16 % → **52 %** d'actions (γ = 2 :
78 % ; γ = 4 : 39 %) ; brancher le géométrique 5,8 % au lieu de l'arithmétique
7 % fait tomber la part à 46 %. Avec capital humain H obligataire : w_fin =
w*(W + H)/W ; un trentenaire à W = 50 k€ et H = 800 k€ tient « 100 %+ »
d'actions (contraint à 100 %) ; un fondateur ou un commercial dont le revenu
est de type actions devrait en tenir *moins*. Pour un Français, la partie
obligataire de H inclut la valeur actuelle de la pension du régime général et
de l'AGIRC-ARRCO.

**2. Probabilité terminale vs probabilité de premier passage.** Pour une
somme forfaitaire à dérive log μ, volatilité σ et seuil de perte L :
P_fin = N[(ln(1+L) − μT)/(σ√T)] ; P_pendant = P_fin + (1+L)^(2μ/σ²)·N[(ln(1+L) +
μT)/(σ√T)] (principe de réflexion). Avec μ = 5 %, σ = 15 %, L = −20 % :
P_fin = 3,4 % à 1 an, 7,9 % à 5 ans, 6,4 % à 10 ans, 3,4 % à 20 ans (elle
**baisse** avec l'horizon) ; P_pendant = 8,0 %, 27,6 %, 33,1 %, **35,9 %** (elle
**monte**). Pour l'épargnant à 500 €/mois sur 20 ans : probabilité de finir
sous 90 % des versements **3,5 %** ; probabilité d'être 10 % sous les
versements cumulés *à une fin d'année entre 5 et 20 ans* **30,8 %** : c'est ce
chiffre qui déclenche les ventes de panique. Le `goal_probability` de
Tangent est la première ; il faut afficher les deux.

**3. Le problème inverse : « combien épargner par mois pour atteindre X avec
p % de chances ? »** La richesse terminale est linéaire dans le versement C
pour un chemin donné : simuler une fois la richesse par euro mensuel, W₁ =
Σ_t Π_{k>t}(1 + r_k), puis bissecter sur C jusqu'à P(C·W₁ ≥ X) = p, sur les
**mêmes chemins** (nombres aléatoires communs) pour une réponse monotone sans
bruit. Résultats (20 ans, μ_arith 7 %, σ 15 %) :

| Objectif | p = 50 % | p = 80 % | p = 90 % | Réponse de la ligne déterministe « 7 % » |
|---|---|---|---|---|
| 200 000 € | 439 €/mois | 629 €/mois | 752 €/mois | 394 €/mois (atteint dans ~40 % des chemins seulement) |
| 300 000 € | 659 €/mois | **944 €/mois** | 1 128 €/mois | 591 €/mois (p ≈ 40 %) ; au taux médian 5,8 % : 677 €/mois (p ≈ 53 %) |

Le versement requis pour 80 % de chances est **60 % plus élevé** que la
réponse déterministe à 7 % et 43 % plus élevé que la réponse médiane. C'est
le nombre le plus utile qu'un moteur puisse montrer à un épargnant. Forme
fermée sous lognormal (Fenton-Wilkinson) : C(X, p) = X / exp(μ_ln + σ_ln
Φ⁻¹(1 − p)), à 1-5 % de la simulation ; suffisant pour un curseur.

**4. Ratio de financement et probabilité de ruine.** FR = (actifs + VA des
versements futurs et des pensions) / VA(objectifs), actualisée au taux réel
sans risque pour les objectifs essentiels (OAT€i ≈ 0,5-1 % en 2026) ; FR > 1
signifie financé sans risque ; FR < 1 chiffre le manque en euros, plus
actionnable qu'une probabilité ; pour un ménage français la pension est
souvent le plus gros actif du numérateur. **Milevsky-Robinson (2005)**,
sans simulation : la valeur actuelle stochastique de 1 €/an de dépense
réelle suit une gamma inverse avec α = (2μ + 4λ)/(σ² + λ) − 1, β = (σ² +
λ)/2, λ = ln 2 / durée de vie médiane restante, d'où P(ruine) = Γ_reg(α,
c/(W·β)). Valeurs : μ = 5 %, σ = 15 %, médiane 25 ans : 4 % → ≈ 18 %, 3,5 % →
≈ 13 % ; μ = 4 %, σ = 15 %, médiane 30 ans : 3 % → ≈ 18 %, 4 % → ≈ 31 %. Le
Bengen de Tangent n'a ni mortalité, ni inflation, ni volatilité.

### 7.9 Les erreurs d'implémentation de Monte-Carlo, chiffrées (tableau D)

Exemple calculé pour cette étude : 500 €/mois pendant 20 ans (120 k€
versés), μ arithmétique 7 %, σ 15 %, pas mensuel, 100 000 trajectoires,
graine fixe, nombres aléatoires communs entre variantes.

| Variante | p10 | p50 | p90 | Δ p50 vs 1 | Δ p10 vs 1 |
|---|---|---|---|---|---|
| 1. Lognormal correct (7 % arithmétique, dérive corrigée de σ²/2) | 132 k€ | 227 k€ | 406 k€ | — | — |
| 2. Sans correction de dérive (7 % pris comme dérive log) | 149 k€ | 260 k€ | 470 k€ | **+14,4 %** | +12,9 % |
| 3. Bandes déterministes μ−σ / μ / μ+σ (la méthode `deterministic_projection` de Tangent) | **59 k€** | 254 k€ | **1 567 k€** | +11,6 % | **−55,7 %** ; le « bull » est 3,9 fois le vrai p90 |
| 4. Student-t ν = 5, même variance | 133 k€ | 227 k€ | 409 k€ | 0,0 % | +0,4 % (la queue épaisse compte pour les règles déclenchées en cours de route, pas pour la médiane) |
| 5. + inflation 2 %/an, en euros d'aujourd'hui | 89 k€ | **153 k€** | 273 k€ | **−32,7 %** | −32,7 % |
| 6. + frais 0,75 %/an sur le solde | 122 k€ | 208 k€ | 369 k€ | −8,4 % | −7,5 % |
| 7. 1 000 trajectoires seulement | 132 k€ | 227 k€ | 412 k€ | −0,3 % | 0,0 % (l'erreur d'échantillonnage est négligeable à côté des erreurs de modèle) |
| 8. Incertitude sur μ intégrée (μ estimé sur 5 ans, SE = 6,7 pts) | **84 k€** | 226 k€ | **737 k€** | −0,6 % | **−36,8 %** ; le p90 passe de 406 à 737 k€ |
| 9. Bootstrap par blocs de rendements MSCI World EUR | non calculé (pas de série mensuelle disponible hors ligne dans cette session) | | | | |
| 10. Versements en début de mois | 132 k€ | 228 k€ | 409 k€ | +0,5 % | +0,2 % |

Lecture pour Tangent : (a) sa projection n'a pas l'erreur 2 (le μ est une
dérive log empirique, correctement exploitée) ; (b) elle a l'erreur 3 dans
ses champs `bear`/`bull` (plus affichés, encore servis par l'API) ; (c) elle
a **l'erreur 5 en affirmant le contraire** (« euros d'aujourd'hui ») : −33 %
sur chaque chiffre affiché ; (d) elle a une version double de l'erreur 6
(TER compté deux fois) ; (e) elle ignore l'erreur 8, qui est **la plus
grosse** : avec 5 ans de données, la vraie bande p10-p90 va de 84 à 737 k€,
pas de 132 à 406 k€ ; le cône affiché couvre environ la moitié de
l'incertitude réelle et est vendu « 8 fois sur 10 » ; (f) 1 000 chemins
suffisent : ce n'est pas là qu'est le problème.

---

## 8. La méthode Tangent v2 : ce qu'il faudrait construire pour que l'app fasse gagner de l'argent

Principe : ordonner le moteur selon les leviers du §1, pas selon ce qui est
amusant à coder. Chaque bloc est accompagné de sa valeur attendue pour
l'épargnant médian, de sa source canonique, et de ce qu'il remplace dans
Tangent.

### 8.1 La méthode en une page (ce que ferait un conseiller honnête et un bon moteur)

1. **Bilan et passifs.** Patrimoine complet (livrets, fonds euros, UC, PEA,
   CTO, PER, immobilier, crédits), capital humain (revenus futurs, stabilité),
   objectifs datés avec montant (précaution, projet < 5 ans, retraite,
   transmission). Un ratio de financement par objectif, actualisé au taux réel
   sans risque (OATi).
2. **Séquencement des enveloppes** (règle explicite, avec horloges) :
   épargne de précaution 3-6 mois en Livret A / LDDS / LEP → objectifs < 5 ans
   en fonds euros (AV en ligne à 0,5-0,6 %) → objectifs > 8 ans en actions
   monde dans le PEA (ETF synthétique 0,20 %, courtier à 1 €/ordre) → PER
   seulement si TMI ≥ 30 % et frais ≤ 0,6 % → CTO pour ce qui ne rentre
   nulle part. Ouvrir l'AV et le PEA tôt pour lancer les horloges 8 ans / 5 ans.
3. **Part risquée** = part de Merton `w* = (μ − r) / (γ σ²)` avec μ − r ≈ 4 %
   (actions monde EUR, CMA 2026), σ ≈ 15 %, γ élicité entre 2 et 4 (soit 45 à
   90 %), **plafonnée par la capacité de perte** (horizon, stabilité du
   capital humain) et non par un curseur. Le glide path découle du ratio
   capital humain / capital financier, pas de l'âge.
4. **Construction** : 5 à 8 classes d'actifs à rôle économique (actions
   monde, actions zone euro optionnelles, fonds euros / obligations euro,
   obligations indexées, immobilier coté ou SCPI en AV, or optionnel), poids
   de marché comme point de départ, déviations en vues explicites. Aucune
   action en direct. Aucun optimiseur sur 3 tickers.
5. **Dynamique** : versements automatiques mensuels avec escalade annuelle ;
   rééquilibrage par les versements, bandes 5/25 vérifiées mensuellement,
   jamais de vente taxable si un versement suffit ; investissement immédiat
   des rentrées exceptionnelles.
6. **Hypothèses** : CMA par briques, 8 classes, fourchettes, datées,
   recalibrées chaque année ; inflation stochastique ; fiscalité par
   enveloppe ; frais réels (contrat + fonds + courtage, sans double compte).
7. **Simulation** : bootstrap par blocs ou Student-t sur rendements mensuels
   EUR, inflation jointe, incertitude sur μ intégrée, versements mensuels,
   fiscalité à la sortie, sortie en euros d'aujourd'hui, 5/25/50/75/95, et
   surtout **le montant d'épargne qui ramène l'objectif à 75 % de chances**
   (problème inverse), pas seulement une probabilité.
8. **Retraite** : SAFEMAX recalculé sur données EUR, 3-3,5 % avec garde-fous
   par probabilité de succès, sourire de dépenses, pension d'État comme
   plancher, séquencement PEA / AV / PER avec l'abattement AV chaque année.
9. **Comportement** : pas de P&L quotidien, pas de « à faire cette
   semaine » ; alertes uniquement sur événements à impact en euros (frais
   > seuil, dérive > bande, connexion cassée, plafond de livret atteint,
   PEA 5 ans, plafond PER non utilisé avant le 31/12, taux de fonds euros
   publié) ; écart de comportement mesuré (TRI vs TWR) et affiché une fois
   par an.
10. **Preuve** : chaque tilt ou règle dynamique doit passer un backtest EUR
    sur indices raccordés et un Sharpe déflaté ; sinon il n'est pas proposé.

### 8.2 Ce que chaque bloc rapporte, et ce qu'il remplace

| Bloc | Valeur attendue pour l'épargnant médian | Source | Remplace dans Tangent | Effort |
|---|---|---|---|---|
| Séquencement des enveloppes + test TMI pour le PER | 60-90 pb/an de TCAM net (PEA vs CTO/AV) ; +3 à +8 k€ par 10 k€ de PER au-dessus de la TMI 30 % ; 200-350 pb/an si l'utilisateur sort d'une AV bancaire en UC | Calculs §1 ; r/vosfinances ; Épargnant 3.0 ; Kitces | Rien (aucune fiscalité) | 2-3 semaines : table des règles 2026 + OpenFisca pour l'IR |
| Audit de frais réel (contrat + fonds + courtage + retenue à la source) | 100-350 pb/an pour un détenteur d'UC ; c'est le motif n° 1 d'abonnement chez Finary | France Assureurs ; ESMA ; Morningstar | `fees.py` avec TER double compté et rétrocessions facturées | 1-2 semaines, à condition de résoudre les ISIN des UC (Powens + OpenFIGI + Boursorama) |
| Part de Merton avec γ élicité et capacité de perte | Remplace un curseur non fondé ; évite le niveau 1 dominé par le LEP et les niveaux 4-5 infaisables | BKM ch. 6 ; Merton ; Elm Wealth ; MiFID II | `risk_levels.yaml`, `glide_path.py` | 1 semaine |
| CMA par briques, 8 classes, datées, en fourchettes | Rend cohérents projection, optimiseur, briefing ; supprime le 7 % par défaut | Ilmanen ; JPM/Amundi/Robeco 2026 | `cma.yaml` (3 tickers), les 6 μ concurrents | 1 semaine + mapping ISIN → classe d'actifs |
| Simulation bootstrap/Student-t, inflation, fiscalité, incertitude sur μ, problème inverse | Cône honnête ; « épargne X € de plus pour 75 % de chances » est la seule sortie actionnable | Portfolio Visualizer ; MIT 15.450 ; Kitces ; Blanchett | `monte_carlo_projection`, `deterministic_projection`, `bengen.py` | 2 semaines |
| Rééquilibrage 5/25 par les versements, versements automatiques à escalade | 12-25 pb/an ajustés du risque ; +58 % du capital final vient des versements à 20 ans | Vanguard ; Bogleheads ; Thaler-Benartzi | Rien | 1 semaine (règles) ; l'automatisation réelle dépend du courtier |
| Alertes événementielles à impact en euros, briefing mensuel | Réduit l'écart de comportement (80-160 pb/an pour un chasseur de performance) au lieu de l'aggraver | Morningstar ; Benartzi-Thaler ; Copilot | Briefing quotidien « à faire cette semaine » | 1-2 semaines, remplace le batch nocturne |
| Stress tests sur 8 fenêtres (1973, 1987, 2000, 2008, 2011, 2020, 2022) avec indices raccordés, corrélations de crise | Affiche la vraie pire perte ; corrige le bug du panier partiel | DMS ; Curvo ; Longin-Solnik | `stress.py` (3 fenêtres post-2020, NaN ignorés) | 1 semaine |
| Fonds euros, UC, PER, SCPI comme classes d'actifs valorisées | Fait entrer 60 % du patrimoine financier français dans les analyses | Banque de France ; ACPR | `InvestmentAccount.balance` exclu de tout | 2 semaines (valorisation Powens stockée comme prix) |
| Retraite : SAFEMAX EUR, garde-fous, sourire, pension plancher | Différence entre épuisement et héritage ; 4 % échoue dans plus de la moitié de l'histoire française | Pfau ; Kitces ; Blanchett ; ERN | `bengen.py`, `WITHDRAWAL_RATE = 0.04` | 2 semaines |
| Ledoit-Wolf avec δ*, HRP ou ERC, 1/N comme référence, allocation discrète en parts | Enlève le bruit de l'optimiseur ; rend le « selon ton profil » faisable | Ledoit-Wolf ; Roncalli ; López de Prado ; PyPortfolioOpt | `shrunk_covariance`, `_solve_slsqp` | 1 semaine (wrapper sur skfolio ou PyPortfolioOpt) |
| Mesure de performance TRI vs TWR sur le vrai journal de transactions | Remplace le « comme si détenu » ; permet l'écart de comportement | GIPS ; Portfolio Performance | `timeseries.py` | 1-2 semaines (Powens fournit les transactions) |

### 8.3 Ce qu'il faut supprimer

| À supprimer | Pourquoi |
|---|---|
| `scanner.py` | Biais de sélection pur, écran de momentum déguisé, renvoie des actions individuelles : le contraire de la méthode |
| `kelly_leverage`, `cvar_95` quotidien × √252 | Non définis ou non informatifs ; non affichés |
| `deterministic_projection` bear/bull | Événements à ±4,5σ étiquetés scénarios |
| `risk_levels.yaml` tel quel | Sur aucune frontière ; niveau 1 dominé, 4-5 infaisables ; à dériver de la frontière CMA ou remplacer par Merton |
| `glide_path.py` | Contredit le curseur ; sans appelant |
| `rebates_pct` | Pas un coût utilisateur |
| `apply_ter_to_fee_fn` sur cours ajustés | Double compte |
| Objectif `max_sharpe` | Sature l'actif au meilleur ratio, surtout avec le 7 % par défaut |
| Optimiseur Markowitz comme fonctionnalité visible | Vaut 0-26 pb dans toutes les décompositions ; à garder comme moteur interne régularisé, jamais comme écran |

### 8.4 Ordre de mise en œuvre, par euros gagnés pour l'utilisateur

1. Corriger les dix défauts trompeurs du §3.1 (une semaine). Tant qu'ils sont
   là, chaque chiffre affiché peut être faux.
2. Fiscalité et séquencement des enveloppes (le levier contrôlable n° 1).
3. Audit de frais réel avec résolution des UC.
4. CMA par briques et part de Merton ; un seul μ dans toute l'app.
5. Simulation honnête avec problème inverse et euros d'aujourd'hui.
6. Fonds euros / PER / SCPI dans les analyses.
7. Alertes événementielles, briefing mensuel, versements à escalade.
8. Retraite EUR.
9. Stress tests longs, TRI/TWR, Ledoit-Wolf δ*.

### 8.5 Liste de lecture, dans l'ordre, pour construire ça soi-même

1. MIT 15.401 (Lo), les 12 blocs : la base commune, gratuite.
2. Vanguard « Advisor's Alpha » 2025 et Morningstar « Gamma » (Blanchett-
   Kaplan 2013) : d'où vient la valeur, chiffrée.
3. Ilmanen, « Expected Returns on Major Asset Classes » (monographie CFA
   gratuite) puis JPM LTCMA 2026 et Amundi CMA 2026 : construire des
   hypothèses par briques.
4. EDHEC, « Investment Management with Python and Machine Learning »
   (Coursera, 4 cours, notebooks sur GitHub) : le syllabus le plus proche
   d'un moteur : drawdown, VaR de Cornish-Fisher, Monte-Carlo GBM, CPPI,
   ratio de financement, Ledoit-Wolf, Black-Litterman, ERC, régimes.
5. Ledoit-Wolf « Honey, I shrunk the sample covariance matrix » ;
   DeMiguel-Garlappi-Uppal « 1/N » ; Idzorek sur Black-Litterman.
6. Roncalli, solutions du livre « Risk Parity and Budgeting » (arXiv
   1403.1889, gratuit) : budgets de risque, Euler, Cornish-Fisher.
7. Portfolio Visualizer (FAQ méthodologique) et Curvo : la spécification de
   fait d'un moteur d'analyse et de backtest EUR.
8. Kitces : garde-fous par probabilité de succès, cliquet, localisation des
   actifs, tente obligataire ; ERN, série SWR parties 1, 3, 8, 14-15, 19-20,
   54 ; Pfau 2010 sur la France.
9. Bernstein, « The Four Pillars » et « Deep Risk » ; Kommer,
   « Souverän investieren » ; Épargnant 3.0, « Créer et piloter un
   portefeuille d'ETF » ; le wiki r/vosfinances.
10. Thaler-Benartzi « Save More Tomorrow » ; Barber-Odean « Trading is
    hazardous to your wealth » ; Morningstar « Mind the Gap ».
11. López de Prado, chapitres 11-14 d'« Advances in Financial Machine
    Learning » (Sharpe déflaté, PBO) : pour ne jamais re-sortir un scanner.
12. Bouchaud-Potters et McNeil-Frey-Embrechts : queues épaisses, ES,
    corrélations de crise.
13. Milevsky, « The 7 most important equations for your retirement » ;
    Waring-Siegel ARVA ; Sharpe RISMAT.

---

## 9. Ce que cette étude ne tranche pas, et où vérifier

- Les chiffres marqués « ~ » viennent d'une seule source ou d'une lecture de
  graphique. Le ratio 11:2:1 de Chopra-Ziemba, les Sharpe de Jobson-Korkie et
  les +55 pb de Daryanani sont cités de la littérature secondaire (les PDF
  originaux sont des scans).
- Le seuil exact d'« actif à faible risque » du PER (SRI PRIIPs ≤ 2 dans le
  texte consolidé ; SRRI ≤ 3 dans l'arrêté de 2019) : même seuil économique
  (volatilité < 5 %), numéro d'échelle différent ; vérifier la version en
  vigueur avant de coder.
- Les quotas d'actifs non cotés de la loi industrie verte (2 à 15 % selon
  profil et horizon) : cellules exactes dans l'arrêté du 1er juillet 2024.
- Les prélèvements sociaux à 18,6 % en 2026 sont confirmés pour PER, PEA et
  CTO ; une page assurance-vie affiche encore 17,2 % ; vérifier la LFSS 2026
  pour l'AV.
- Le bootstrap par blocs sur MSCI World EUR (ligne 9 du tableau D) n'a pas
  été calculé faute de série mensuelle hors ligne.
- La question §8.2 de l'état des lieux (μ CMA mixte partout, double comptage
  du TER) est tranchée par cette étude sur le fond (le TER **est** double
  compté ; un seul μ par briques doit alimenter toute l'app) mais reste ta
  décision à appliquer.

## 10. Sources principales

Rapports de session (scratchpad, non versionnés) : 01 et 01b méthodes
institutionnelles, 02 preuves empiriques, 03 et 03b projections, 04 cursus,
05 robo-advisors, 06 audit du moteur ; environ 400 URL au total. Sélection :

Preuves empiriques et décompositions
- Ibbotson & Kaplan 2000, https://indexacapital.com/bundles/unaiadvisor/docs/papers/2000-Ibbbotson-Kaplan-Asset-Allocation-Explain.pdf
- Vanguard Advisor's Alpha 2022, https://www.vanguardsouthamerica.com/content/dam/intl/americas/documents/latam/en/2022/08/mx-sa-2335954-putting-a-value-on-your-value-quantifying-vanguard-advisors-alpha.pdf ; édition 2025, https://advisors.vanguard.com/content/dam/fas/pdfs/IARCQAA.pdf
- Blanchett & Kaplan, Gamma, https://www.morningstar.com/content/dam/marketing/shared/research/foundational/677796-AlphaBetaGamma.pdf
- ESMA, Costs and Performance of EU Retail Investment Products 2025, https://www.esma.europa.eu/sites/default/files/2026-03/ESMA50-1949966494-4065_Market_Report_-_Costs_and_Performance_of_EU_Retail_Investment_Products.pdf
- AMF, Analyse des frais des fonds de droit français 2024, https://www.amf-france.org/sites/institutionnel/files/private/2024-05/etude-analyse-des-frais_fr_0.pdf
- AMF, Baromètre de l'épargne 2025, https://www.amf-france.org/sites/institutionnel/files/private/2025-12/barometre-amf-2025.pdf
- AMF, Étude CFD/Forex, https://www.amf-france.org/sites/institutionnel/files/contenu_simple/rapport_etude_analyse/epargne_prestataire/Etude%20des%20resultats%20des%20investisseurs%20particuliers%20sur%20le%20trading%20de%20CFD%20et%20de%20Forex%20en%20France.pdf
- Banque de France, Épargne des ménages T3 2025, https://www.banque-france.fr/system/files/webstats/Epargne_des_menages-T3-2025_20260219/FR_Stat_info_-_Epargne_des_menages_-_2025T3.pdf
- France Assureurs, AV en UC 2024, https://www.franceassureurs.fr/nos-chiffres-cles/assurance-vie/lassurance-vie-en-unites-de-compte-en-2024/
- Morningstar Mind the Gap 2025, https://www.morningstar.com/business/insights/research/mind-the-gap ; hors US 2023, https://assets.contentstack.io/v3/assets/blt4eb669caa7dc65b2/blt79f841149f6435b0/651bdd45964d9b76a3c313b0/MTG_2023_exUS_FINAL.pdf
- Fulkerson et al. 2026, https://rpc.cfainstitute.org/research/financial-analysts-journal/2026/bad-timing-does-not-cost-investors-funds-returns
- Barber & Odean 2000, https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/individual_investor_performance_final.pdf ; Odean 1998, https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/areinvestorsreluctant.pdf
- Bessembinder 2018, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2900447
- Jordà et al., Rate of Return on Everything, https://www.frbsf.org/wp-content/uploads/wp2017-25.pdf
- UBS/DMS Global Investment Returns Yearbook 2026, https://www.ubs.com/global/en/investment-bank/in-focus/global-investment-returns-yearbook.html
- Anarkulova, Cederburg, O'Doherty 2024, https://finance-conference.wpcarey.asu.edu/sites/g/files/litvpz3416/files/2025-01/Beyond%20the%20Status%20Quo.pdf
- Pfau 2010, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1699526 ; https://retirementresearcher.com/the-shocking-international-experience-of-the-4-rule/
- Vanguard, Cost averaging 2023, https://corporate.vanguard.com/content/dam/corp/research/pdf/cost_averaging_invest_now_or_temporarily_hold_your_cash.pdf
- Vanguard, When and how asset location matters 2026, https://corporate.vanguard.com/content/dam/corp/research/pdf/when_and_how_asset_location_matters.pdf
- AQR, A Century of Evidence on Trend-Following, https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing
- ASPIM/IEIF 2025, https://www.aspim.fr/content/uploads/2026/02/ASPIM_CP-4T-2025_V4.pdf
- Early Retirement Now, série SWR, https://earlyretirementnow.com/safe-withdrawal-rate-series/
- Kitces : garde-fous, https://www.kitces.com/blog/guyton-klinger-guardrails-retirement-income-rules-risk-based/ ; risque de séquence, https://www.kitces.com/blog/understanding-sequence-of-return-risk-safe-withdrawal-rates-bear-market-crashes-and-bad-decades/ ; localisation, https://www.kitces.com/blog/asset-location-the-new-wealth-management-value-add-for-optimal-portfolio-design/
- portfoliocharts, https://portfoliocharts.com/charts/ ; Épargnant 3.0, https://www.epargnant30.fr/msci-world/ ; service-public PER, https://www.service-public.gouv.fr/particuliers/vosdroits/F34982

Méthodes institutionnelles
- JPM LTCMA 2026, https://am.jpmorgan.com/us/en/asset-management/institutional/insights/portfolio-insights/ltcma/
- Amundi CMA 2026, https://research-center.amundi.com/ ; Robeco Expected Returns 2026-2030, https://www.robeco.com/en-int/insights/expected-returns
- AQR Capital Market Assumptions 2026, https://www.aqr.com/Insights/Research/Alternative-Thinking/2026-Capital-Market-Assumptions-for-Major-Asset-Classes
- Vanguard VCMM / VLCM, https://corporate.vanguard.com/content/dam/corp/research/pdf/vanguard_life_cycle_investing_model_vlcm_a_general_portfolio_framework_for_goals_based_investing.pdf
- Michaud 1989, https://rpc.cfainstitute.org/research/financial-analysts-journal/1989/the-markowitz-optimization-enigma-is-optimized-optimal ; Michaud & Michaud 2005, https://newfrontieradvisors.com/media/rxbld4hq/estimation-error-and-portfolio-optimization-12-05.pdf
- Chopra & Ziemba 1993, https://jpm.pm-research.com/content/19/2/6
- DeMiguel, Garlappi & Uppal 2009, https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901 ; Kritzman, Page & Turkington 2010, https://rpc.cfainstitute.org/research/financial-analysts-journal/2010/in-defense-of-optimization-the-fallacy-of-1n
- Ledoit & Wolf 2004, http://www.ledoit.net/Honey_2004.pdf ; Jorion 1986, https://econpapers.repec.org/RePEc:cup:jfinqa:v:21:y:1986:i:03:p:279-292_01
- Idzorek, Black-Litterman, https://people.duke.edu/~charvey/Teaching/BA453_2006/Idzorek_onBL.pdf
- Maillard, Roncalli & Teiletche 2010, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1271972 ; Roncalli, solutions, https://arxiv.org/abs/1403.1889
- López de Prado 2016 (HRP), https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678
- Rockafellar & Uryasev, https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf
- Boyd et al., cvxportfolio, https://web.stanford.edu/~boyd/papers/pdf/cvx_portfolio.pdf
- CFA Institute, Principles of Asset Allocation, https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2025/principles-asset-allocation ; Real-World Constraints, https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/asset-allocation-with-real-world-constraints
- NBIM, https://www.nbim.no/en/investments/investment-strategy/ ; CalPERS ALM, https://www.calpers.ca.gov/about/organization/facts-at-a-glance/2021-alm-decision-frequently-asked-questions ; FRR rapport annuel 2024, https://www.fondsdereserve.fr/wp-content/uploads/2025/10/FRR-RA2024-FR-2.pdf
- Chhabra 2005, https://jwm.pm-research.com/content/7/4/8 ; Das, Markowitz, Scheid & Statman 2010, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1166899 ; Brunel, https://onlinelibrary.wiley.com/doi/book/10.1002/9781119025306
- EDHEC goal-based investing, https://climateinstitute.edhec.edu/goal-based-investing-and-application-retirement-problem
- Bodie, Merton & Samuelson 1992, https://www.nber.org/papers/w3954 ; Cocco, Gomes & Maenhout 2005, https://academic.oup.com/rfs/article-abstract/18/2/491/1599892
- Estrada 2016, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2557256 ; Pfau & Kitces 2014, https://www.financialplanningassociation.org/article/journal/JAN14-reducing-retirement-risk-rising-equity-glide-path
- Vanguard rééquilibrage 2010, 2022, 2024 : https://corporate.vanguard.com/content/dam/corp/research/pdf/rational_rebalancing_analytical_approach_to_multiasset_portfolio_rebalancing.pdf ; https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf
- Daryanani 2008, https://www.financialplanningassociation.org/sites/default/files/2020-05/9%20Opportunistic%20Rebalancing%20A%20New%20Paradigm%20for%20Wealth%20Managers.pdf ; Bernstein, https://www.efficientfrontier.com/ef/996/rebal.htm ; Hoffstein et al., https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3673910 ; Harvey et al. 2025, https://www.nber.org/system/files/working_papers/w33554/w33554.pdf
- UBS GWM CIO, Asset allocation: risk and return (février 2026) ; Rothschild & Co AM mandats, https://am.eu.rothschildandco.com/stock/lib/PDF/GSM/FR/20230515-gestion%20sous%20mandat-Marc%20Terras.pdf ; Société Générale Gestion, https://www.societegeneralegestion.fr/fra/fr/particuliers/nos-solutions/gestion-sous-mandat
- ESMA, lignes directrices adéquation MiFID II 2023, https://www.esma.europa.eu/sites/default/files/2023-04/ESMA35-43-3172_Guidelines_on_certain_aspects_of_the_MiFID_II_suitability_requirements.pdf ; AMF DOC-2019-03, https://www.amf-france.org/sites/institutionnel/files/private/2023-06/DOC-2019-03_VF2.pdf ; AMF synthèse SPOT adéquation 2021, https://www.amf-france.org/sites/institutionnel/files/private/2021-03/synthese-spot-adequation-vf_0.pdf ; ACPR Robex, https://acpr.banque-france.fr/fr/actualites/la-motivation-du-conseil-par-les-robo-advisors-vers-un-eclairage-apporte-aux-clients
- EBA stress testing 2018, https://www.eba.europa.eu/documents/10180/2282644/2b604bc8-fd08-4b17-ac4a-cdd5e662b802/Guidelines%20on%20institutions%20stress%20testing%20(EBA-GL-2018-04).pdf
- Longin & Solnik 2001, http://solnik.people.ust.hk/Articles/A6-JoFLongin.pdf ; Ang & Bekaert 2002, https://business.columbia.edu/sites/default/files-efs/pubfiles/1971/1137.pdf
- Moreira & Muir 2017, https://www.nber.org/system/files/working_papers/w22208/w22208.pdf ; Harvey et al. 2018, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538
- GIPS 2020, https://www.gipsstandards.org/wp-content/uploads/2021/03/2020_gips_standards_firms.pdf ; MiFID II RD 2017/565 art. 60 et 62, https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32017R0565

Robo-advisors et gestion pilotée
- Betterment, https://www.betterment.com/resources/portfolio-construction-methodology ; https://betterment.com/resources/research/projection-methodology
- Wealthfront, https://research.wealthfront.com/whitepapers/investment-methodology/
- Indexa Capital, https://blog.indexacapital.com/2026/02/03/pronosticos-rentabilidad-2026/ ; https://indexacapital.com/es/esp/stats
- Scalable Capital (abandon du VaR), https://financefwd.com/de/scalable-capital-value-at-risk/
- Yomoni, https://www.yomoni.fr/performances/profils-investissement ; https://www.yomoni.fr/performances
- Nalo, https://www.nalo.fr/performances ; https://blog.nalo.fr/securisation-progressive/
- Ramify, https://www.ramify.fr/performances ; https://www.ramify.fr/livre-blanc
- Goodvest, https://www.goodvest.fr/performances ; Mon Petit Placement, https://www.monpetitplacement.fr/legal/comprendre-nos-performances
- Good Value for Money, gestion profilée, https://www.goodvalueformoney.eu/espace-documentaire/performance-des-offres-de-gestion-profilee ; Moneyvox, https://www.moneyvox.fr/assurance-vie/actualites/104463/ces-contrats-assurance-vie-rapportent-bien-moins-quun-placement-a-100-dans-un-fonds-euros
- Arrêté du 7 août 2019 (PER), https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000039802054 ; Eres loi industrie verte, https://www.eres-group.com/actualites/loi-industrie-verte-mise-a-jour-des-grilles-reglementaires-de-gestion-pilotee/
- PRIIPs, règlement délégué 2021/2268, https://eur-lex.europa.eu/eli/reg_del/2021/2268/oj/eng ; ESMA JC 2020 66 ; Q&A JC 2023 22
- Finary Predict, https://finary.com/en/product-updates/predicting-the-future-with-monte-carlo

Projections et simulation
- Ibbotson, Monte Carlo white paper 2005 ; RightCapital, Boldin, ProjectionLab, Portfolio Visualizer (FAQ méthodologique), https://www.portfoliovisualizer.com/faq
- Vanguard VEMO 2026, https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html ; BlackRock CMA, https://www.blackrock.com/institutions/en-us/insights/charts/capital-market-assumptions
- Research Affiliates AAI, https://interactive.researchaffiliates.com/asset-allocation ; GMO 7-year forecast, https://www.gmo.com/europe/research-library/
- Kitces, probabilité de succès, https://www.kitces.com/blog/monte-carlo-analysis-risk-tolerance-probability-of-success-adjustment-guardrails/ ; Blanchett, funded ratio, https://www.morningstar.com/
- Politis & White 2004 (longueur de bloc) ; Ang & Bekaert 2002 ; Longin & Solnik 2001 ; Wilkie 1986/1995 ; Campbell & Shiller 1998 ; Kritzman & Rich 2002
- Curvo méthodologie, https://curvo.eu/backtest/en ; MSCI World EUR factsheet ; Bloomberg Euro Aggregate factsheet (SPDR)
- Milevsky & Robinson 2005, https://www.tandfonline.com/doi/abs/10.2469/faj.v61.n6.2776 ; Glasserman 2004 ; Meucci 2005 ch. 3.2

Cursus
- MIT OCW 15.401, 15.433, 15.450, 18.S096 : https://ocw.mit.edu/ ; Yale ECON 252, https://oyc.yale.edu/economics/econ-252
- EDHEC Coursera, https://www.coursera.org/specializations/investment-management-python-machine-learning ; Genève/UBS, https://www.coursera.org/specializations/investment-management ; Columbia FE&RM, https://www.coursera.org/specializations/financialengineering
- Cochrane, https://www.johnhcochrane.com/asset-pricing ; Damodaran, https://pages.stern.nyu.edu/adamodar/ ; Stanford CME 241, https://cme241.github.io/
- Granger (Dauphine, CEA), https://www.institutdesactuaires.com/docs/2017165801_capm-cea-2016-coursn-3.pdf ; ISFA revue, http://www.ressources-actuarielles.net/ ; Bouchaud-Potters, https://arxiv.org/abs/cond-mat/9801240
- Ilmanen, monographie CFA, https://rpc.cfainstitute.org/sites/default/files/-/media/documents/book/rf-publication/2012/rf-v2012-n1-1-pdf.PDF ; Meucci, https://www.arpm.co/book ; McNeil-Frey-Embrechts, https://www.qrmtutorial.org/
- Elm Wealth, https://elmwealth.com/research/ ; Newfound, https://www.thinknewfound.com/rebalance-timing-luck ; Quantopian lectures, https://github.com/quantopian/research_public/tree/master/notebooks/lectures
- PyPortfolioOpt, https://pyportfolioopt.readthedocs.io/ ; Riskfolio-Lib, https://riskfolio-lib.readthedocs.io/ ; skfolio, https://skfolio.org/ ; cvxportfolio, https://www.cvxportfolio.com/
- CFA niveau III, https://www.cfainstitute.org/sites/default/files/-/media/documents/study-session/2025-l3-privwealth-los-t1.pdf ; FRM, https://www.garp.org/frm/study-materials
- Avenue des Investisseurs, https://avenuedesinvestisseurs.fr/ ; Finance Héros, https://finance-heros.fr/ ; Épargnant 3.0, https://www.epargnant30.fr/ ; Kommer, https://gerd-kommer.de/en/ ; Bogleheads, https://www.bogleheads.org/wiki/Rebalancing
