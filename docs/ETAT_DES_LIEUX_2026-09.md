# Tangent — État des lieux UI/UX & fonctionnel (7 sept. 2026)

Base : `main` @ `4b8a674` (dernier commit 9 juin 2026, PR #81). Repo cloné, buildé, lancé avec une API mockée, capturé à **390 px** (iPhone 13) et **1440 px**. 4 revues de code en parallèle (Comptes / Projection / Investissements / Profil-Réglages-Auth-Nav), tout ce qui est écrit ci-dessous a été vérifié dans le code ou à l'écran, sauf mention « à confirmer ».

---

## 0. Verdict en 6 lignes

1. **Rien ne casse à la CI** : `tsc`, `eslint`, `ruff`, `ruff format`, **92 tests** unitaires, **15 tests** vitest — tout est vert. Les problèmes ne sont pas des problèmes de code « sale », ce sont des problèmes de **produit** : trop de choses, mal reliées entre elles, et plusieurs qui mentent à l'utilisateur.
2. **Le profil n'est jamais synchronisé avec le serveur** (`fetch("/profile")` relatif au lieu de `/api/profile`) → 2e appareil vide, briefing IA inatteignable pour un utilisateur normal, LLM aveugle. C'est le bug n°1, il explique une bonne partie du « ça marche pas ».
3. **Mobile** : le Dashboard tient. Tout le reste déborde : tableaux à 6-10 colonnes (le solde sort de l'écran), SVG à `viewBox 720` rendus à moitié (textes ~5 px), tooltips souris-only, grilles `grid-cols-3` qui font se chevaucher les chiffres, onglets Profil/Réglages qui explosent, footer qui recouvre la nav, aucune safe-area iOS.
4. **L'app est un notebook quant habillé en React** : μ, σ, Sharpe, CVaR, P10/P90, SLSQP, Kelly, Euler, shrinkage… en première ligne, et 3 hypothèses de rendement différentes qui cohabitent sur la même page Projection.
5. **Redondances** : 2 « patrimoine net » calculés différemment, 2 tables « positions », 4 endroits qui affichent μ/σ/Sharpe, 2 menus compte, 3 mécanismes de sync, 3 listes d'invalidation React Query, interfaces TS déclarées deux fois, 3 noms de marque.
6. **Promesses non tenues à l'écran** : « synchronisé avec ton compte » (non), « prochain briefing vers 3h » (non si pas opt-in, et l'opt-in ne remonte pas), « Suivre ajoute le ticker à l'optimiseur » (la watchlist n'est lue nulle part), scanner « ETFs UCITS » (il ne renvoie que des actions), Réglages « tire la frontière efficiente » (seul le Scanner lit les réglages), colonne TER (le back ne renvoie pas le champ → affiche `undefined`).

---

## 1. Les bugs qui font que « ça marche pas » (par impact)

| # | Bug | Où | Effet utilisateur | Vérif |
|---|---|---|---|---|
| 1 | `fetch("/profile")` **relatif**, sans `API_URL` ni `/api` ; erreurs avalées par `catch {}` | `lib/profile-sync.ts:83,101` | Profil jamais poussé/tiré. Sur mon banc : **404 sur GET, 501 sur PUT**. Briefing IA (batch nocturne filtre `auto_review_enabled=True` en DB) jamais déclenché. | Reproduit |
| 2 | **TER absent de `HoldingResponse`** côté back, mais typé et affiché côté front | `routers/accounts.py:136-147` vs `api.ts:757`, `data-field.tsx:90` | Colonne « TER » affiche `undefined` ; l'édition de TER « réussit » puis disparaît au refetch | Confirmé code |
| 3 | Tableau Positions : en-têtes μ/σ/CVaR/MaxDD/Sharpe en `hidden md:table-cell`, **cellules pas cachées** | `Assets.tsx:35-39` vs `66-80` (PR #80) | À < 768 px : 10 cellules pour 5 en-têtes, colonnes décalées, page qui déborde à ~850 px | Reproduit (screenshot) |
| 4 | **Deux « patrimoine net » différents** : client-side dans Comptes (tous types), `WealthSummary` côté back dans le Dashboard (ignore `per/pee/mortgage/consumer_credit/crypto/real_estate…`, prêts en `|balance|` et non `used_amount`) | `Accounts.tsx:313-322` vs `deps.py:56-219` | Deux chiffres pour la même chose selon l'onglet dès qu'on a un PER/PEE/prêt immo | Confirmé code |
| 5 | Auto-refresh au mount de Comptes tape **`/accounts/refresh`** (force Powens + `sleep(10)`, « use sparingly ») et pas `/accounts/sync` (cache 5 min) ; le `useRef` se réinitialise à chaque changement d'onglet | `Accounts.tsx:279-295`, `routers/accounts.py:510-578` | Sync lourde à chaque passage sur Comptes, chiffres qui changent sous les yeux sans indicateur | Confirmé code |
| 6 | **Retour Powens atterrit sur l'onglet « IA »**, sync en arrière-plan sans feedback, `sync.mutate` sans `onError` ; si la 1re sync échoue : bouton Sync désactivé (`accounts.length===0`) + message « Aucune banque connectée » alors qu'une connexion existe | `PowensCallback.tsx:31-41`, `App.tsx:41`, `Accounts.tsx:281,339,379` | Onboarding cassé, dead-end sans issue autre que refaire tout le parcours | Confirmé code |
| 7 | Le broker du profil est **écrasé par le défaut YAML** : `useBrokers().default` = `bnp_start` global → `setBroker()` pendant le rendu → envoyé en query → le back ne lit jamais `profile.default_broker` | `Projection.tsx:49-51`, `envelopes.py:26`, `analysis.py:42-45` | Tout le monde est projeté avec les frais BNP (les plus chers). Le select « Courtier » du Profil est un no-op (pas envoyé, pas renvoyé par `_to_out`) | Confirmé code |
| 8 | **Bull/Bear = μ±σ appliqué chaque année** pendant N ans → hors distribution, et la courbe bull est incluse dans l'échelle Y | `analytics.py:263-267`, `Projection.tsx:281` | Le fan chart P10-P90 (le truc utile) est écrasé dans le tiers bas du graphe | Reproduit (screenshot) |
| 9 | `ChartTile` : `if (isLoading \|\| !timeseries)` → skeleton | `ChartTile.tsx:35` | Si `/timeseries` renvoie une erreur (portefeuille vide, ticker inconnu) : **tuile qui « charge » pour toujours** | Confirmé code |
| 10 | **Un seul ticker non résolu fait tomber tout `/dashboard`** ; ticker construit par repli sur 6 caractères du libellé pour les titres sans `stock_symbol` (fonds euros AV, etc.) ; et `App.tsx` confond chargement et échec (« indisponible — ajoute des positions ») | `market.py:54-59`, `powens/aggregator.py:85-94`, `App.tsx:104-110` | Onglet Investissements vide + KPI strip vide, sans message exploitable | Confirmé code |
| 11 | `from_strategy` sans profil complet → **422 brut** ; messages d'erreur du solveur et interprétation Kelly **en anglais** | `api.ts:440-442`, `models.py:275-277`, `optimizer.py:172-175,233-243` | « Infeasible strategy: with σ ≤ 10.0%… » dans une UI française | Confirmé code |
| 12 | `logout` ne vide pas `tangent.profile` / `tangent.settings` | `api.ts:381-393` | Sur un navigateur partagé, le 2e utilisateur hérite date de naissance, RFR, parts fiscales du 1er | Confirmé code |
| 13 | Toggle « Reviews IA » écrit direct dans `profile` → `Profile.tsx` resynchronise le draft → **efface les saisies non enregistrées** des autres onglets ; et la section n'est pas rendue si `profile===null` (nouvel utilisateur ne voit jamais l'opt-in) | `AccountTab.tsx:604-618`, `Profile.tsx:57-59` | Perte de saisie silencieuse ; opt-in invisible pour un nouveau compte | Confirmé code |
| 14 | Mot de passe : **min 8** à l'inscription/changement, **min 12** au reset | `RegisterForm.tsx:87`, `ForgotPasswordFlow.tsx:60`, `password_reset.py:31` | Incohérent, incompréhensible | Confirmé code |
| 15 | Comptes Google-only : « définis d'abord un mot de passe » mais **aucune route/UI pour en définir un** | `oauth_accounts.py:74`, `account.py:80` | Impasse : ne peuvent ni délier Google ni changer de méthode | Confirmé code |
| 16 | `list_bank_connections` renvoie `[]` sur erreur Powens ; suppression Powens qui échoue est avalée puis on supprime en local | `routers/accounts.py:275-277, 335-342` | Erreur maquillée en « Aucune banque » ; connexion qui reste active chez Powens | Confirmé code |
| 17 | Bengen : **pas de debounce** (3 POST par frappe), aucun `isLoading`/`isError`, `Number(v) \|\| 4` empêche de vider le champ, capital/μ tombent à `0 € / 8 %` en silence si `/dashboard` n'est pas là | `BengenWidget.tsx:15-38, 81` | Bloc qui disparaît pendant la frappe, hypothèses fausses affichées comme des faits | Confirmé code |
| 18 | `holdings.isError` / `txs.isError` non gérés → « Aucune position. » / « Aucune transaction. » sur une 500 | `Accounts.tsx:714-716, 769-771` | Erreur déguisée en état vide | Confirmé code |
| 19 | `docker-compose.yml:61` : `VITE_API_URL=http://localhost:8000` **sans `/api`** depuis ADR-020 | `docker-compose.yml` | Le dev Docker devrait 404 sur `/users/me` (à confirmer, pas testé) | À confirmer |
| 20 | Routes `async` qui appellent `yf.download` / `yf.screen` **bloquants** | `routers/dashboard.py:14`, `analysis.py:24,54`, `market.py:39`, `scanner.py:93` | Un scan de 30 s bloque l'event loop pour tous les users. Contraire aux règles du projet | Confirmé code |

Non-bug mais vérifié : `diff_percent` Powens est un **ratio** (doc POWENS_SCHEMA_REFERENCE), donc `fmt.signedPct` ×100 est correct.

---

## 2. Mobile : ce qui casse à 390 px (avec preuves)

Screenshots joints : `mobile-*.png` (vue réelle 390 px) et `mobile-*` en version « déroulée » (largeur naturelle des tableaux, pour voir ce qui déborde).

| Écran | Ce qui casse | Cause |
|---|---|---|
| **Aperçu (IA)** | ✅ Tient. Seul écran vraiment mobile. Pinaillage : « P&L latent », « 90 jours » = 90 jours de bourse (~4,3 mois), sub-titre caché sur mobile | — |
| **Comptes — header** | **Les 3 montants se chevauchent** (« +53 290,55 € -12 000,00 € +41 290,55 € » superposés), « Actifs » avec un `+` absurde | `grid-cols-3` sans breakpoint + `text-lg font-mono` + `fmt.signedEur` (`Accounts.tsx:362`) |
| **Comptes — tables** | 6 colonnes (chevron, nom+badge, banque, solde, IBAN, sync) → **scroll horizontal dans chaque carte, le solde sort de l'écran** ; nom tronqué en « Livr… » ; badge « COURANT » coupé ; `truncate` inopérant sans `min-w-0` | `Accounts.tsx:463-472, 536` ; `ui/table.tsx:7` `overflow-auto` |
| **Comptes — positions** | Table 6 colonnes **dans** une cellule `colSpan=6` d'une table déjà en overflow = **double scroll horizontal** ; boutons ✓/✕ de 12 px | `Accounts.tsx:723-732`, `data-field.tsx:76,84` |
| **Comptes — transactions** | 4 colonnes, date + libellé + `catégorie_snake_case` + montant : déborde | `Accounts.tsx:774-781` |
| **Projection — graphe** | `viewBox 720×360` rendu à ~358 px → **textes SVG ~5 px** ; tooltip `onMouseMove` uniquement (rien au doigt) et **240 px fixes** qui déborde des deux côtés ; légende 6 entrées sur 3-4 lignes | `Projection.tsx:19-21, 331-332`, `ChartTooltip.tsx:23,50` |
| **Projection — Bengen** | **« 30 000,00 € / 12,3 ans / Janvier 2039 » se chevauchent** | `grid-cols-3` + `text-2xl font-mono` sans breakpoint (`BengenWidget.tsx:90`) |
| **Projection — stats** | Badge TER 5e enfant de la grille d'inputs, `title=` hover-only ; formule des frais en `text-[10px]` mono sur 3 lignes | `Projection.tsx:92-99, 227-232` |
| **Historique (sheet)** | `viewBox 720×576` dans 358 px → 3 panneaux de ~55 px de haut, textes 5 px, souris-only ; double cadre + double titre | `Timeline.tsx:21-31, 80, 86` |
| **Investissements** | **8 blocs de chiffres** avant tout contenu (5 cartes + 3 risques) ; table Positions cassée (bug #3) ; scatter σ/μ à 5 px, `onMouseEnter` only, « Survole un point » ; matrice corrélation `min-w-[56px]`/cellule scroll dès 5 actifs, explication en `title=` ; RiskBar : segments < 8 % sans label, info en `title=` ; **page de ~4 200 px de haut = 5 écrans de téléphone** | `Metrics.tsx:15,37`, `RiskReturn.tsx:20-22,118,273-342`, `Correlation.tsx:38-39,70,72`, `Optimizer.tsx:502-504` |
| **Profil / Réglages** | **Onglets : 4 icônes sans texte ni `aria-label`, sur 2 rangées, qui débordent d'une boîte de 36 px** ; double header (« Profil » AppShell + « ← Retour / Mon profil ») ; « Retour » côte à côte avec le titre mange 1/3 de la largeur ; `min-h-screen` + `pb-32` dans un `main overflow-y-auto pb-20` → gros vide ; footer Enregistrer `fixed z-50` **recouvre la BottomNav** `z-30` ; livrets `grid-cols-2` avec labels qui wrappent | `Profile.tsx:80-113, 135, 261`, `tabs.tsx:15`, `Settings.tsx` idem |
| **Dialogs** | Changer mot de passe (3 champs), suppression compte, TermsGate : `Dialog` centré `top-50%` sans max-height ni scroll interne → **sous le clavier iOS** ; `BottomSheet` existe mais pas utilisé ici | `dialog.tsx:38`, `AccountTab.tsx`, `TermsGate.tsx` |
| **Global** | Aucun `env(safe-area-inset-bottom)`, pas de `viewport-fit=cover` → barre home iPhone qui mord la nav ; cibles < 44 px partout (`size="sm"` = 32 px, inputs `h-9`, items Select ~30 px) ; **pas de routeur** → bouton retour du téléphone = sortie du site, refresh = retour à l'accueil | `index.html:5`, `AppShell.tsx`, `App.tsx:41` |

---

## 3. Redondances

| Doublon | A | B (et C) |
|---|---|---|
| Patrimoine net | `Accounts.tsx:313` (client, tous types) | `WealthSummary.net_worth` Dashboard (règles différentes) |
| Positions / holdings | `Assets.tsx` (Ticker·Poids·Valeur·P/L·μ·σ·CVaR·MaxDD·Sharpe) | `Accounts.tsx:724` (Ticker·Libellé·Qté·PRU·Valorisation·TER) — aucun lien entre les deux |
| μ / σ / Sharpe « actuel » | `Metrics` | `Assets` (par ligne), `Optimizer` colonne Actuel, `RiskReturn` losange « Position actuelle » |
| Valorisation / Plus-value | `Metrics.tsx:16-26` (ETF seuls) | `KpiStrip.tsx:24` (ETF + cash PEA) → 2 chiffres différents |
| Frontière | `RiskReturn` (dessin) | `Optimizer` (tableau Actuel/Optimal) ; `FrontierCloud` (3 000 points Dirichlet, ~200 Ko) calculée à chaque `/dashboard` et **jamais lue** |
| Diagnostic | `Insights` (4 règles, texte en ρ/σ/Sharpe) | Briefing IA (reçoit déjà current/optimal), règle « corrélation forte » vs matrice `Correlation` |
| « Dans N ans tu auras » | `Projection` (μ historique 5 ans, frais broker + TER, Monte-Carlo) | `Bengen` (μ blendé CMA, **sans frais ni inflation ni impôt**) — deux réponses contradictoires sur la même page ; + `target_annual_return` du Profil = 3e μ |
| Inputs Projection | `monthly=200`, `years=10` codés en dur | Profil connaît `monthly_dca=250`, `horizon_years` → Bengen les lit, Projection non |
| Menu compte | `UserMenu.tsx` (desktop) | `MoreSheet.tsx` (mobile) — identité, requête OAuth, lien Google, légal, logout, `window.alert` dupliqués |
| Mécanismes de sync | auto-refresh `/refresh` (mount) | bouton Sync `/refresh` ; PowensCallback `/sync` |
| Listes d'invalidation RQ à la main | `api.ts:840,852` | `PowensCallback.tsx:30-39`, `AccountTab.tsx:444-447` |
| Cache OAuth accounts | `["user","oauth-accounts"]` (UserMenu/MoreSheet) | `["oauth-accounts"]` (AccountTab) → après « Délier », le menu dit encore « Google lié ✓ » |
| `api.ts` | `BankAccountResponse`, `HoldingResponse`, `BankTransactionResponse` **déclarés 2×** (l.700/857, 745/870, 764/889) ; `listOAuthAccounts`≡`fetchOAuthAccounts`, `deleteOAuthAccount`≡`unlinkOAuthAccount` ; commentaire de collage « Replace the existing… Lines ~670 to ~727 » (l.630) ; 5 `fetch` directs qui contournent `http()` ; 3 conventions d'URL de base (`api.ts`, `streaming.ts` sans `/api`, `profile-sync.ts` relatif) | |
| Atome `Section` | `Profile.tsx:397` | `Settings.tsx:446`, `AccountTab.tsx:641` |
| Temps relatif | `relativeTime` → « 3h » (`Accounts.tsx:202`) | `formatRelative` → « il y a 3 h » (`AccountTab.tsx:512`) |
| Prénom | `display_name` (inscription) | `first_name` (Profil, **jamais utilisé nulle part**) |
| Marque | « Tangent » (sidebar, CGU) | « Risky businesses » (`AuthScreen.tsx:22`), « Portfolio Dashboard » (`index.html:6`) |
| Chargement | « Chargement… » texte (9 occurrences) | skeletons (Dashboard) |
| Heure du briefing | « vers 3h » (`AiBriefTile`) | « entre 4h et 9h » (`AccountTab`), scheduler 3h→9h |

---

## 4. Code mort et calculs pour rien

| Élément | État |
|---|---|
| `components/AI.tsx` (382 l.) + `lib/streaming.ts` (98 l.) | Importés **nulle part**. Emportent avec eux le seul bouton « Générer ma review » → `POST /reviews/generate` orphelin |
| `components/StressTests.tsx` | Jamais monté, alors que `stress_tests` est **calculé à chaque `/dashboard` avec un 2e fetch yfinance 10 ans**. C'est pourtant la seule formulation du risque qu'un novice comprend (« en 2020 tu aurais perdu X € ») |
| `useWatchlist`, `useWatchlistRemove` | Aucun consommateur. La watchlist n'a **aucune UI de liste** et n'est lue par aucun calcul (`deps.py:get_user_wealth` ne la consulte pas). Le bouton « Suivre » du Scanner écrit en base et relance 2 calculs lourds pour rien |
| `useReviewsHistory` | Aucun consommateur → **l'historique des briefings est inaccessible** |
| `GET /strategy` (glide path) | Aucun appel front |
| `FrontierCloud` | Sérialisée, passée en prop, ignorée par `RiskReturn` |
| Profil : `first_name`, `tmi_pct` | Consommés nulle part (ni UI, ni back) |
| Profil : `default_broker` | No-op (cf. bug #7) |
| Profil : `ceilings_used` (soldes livrets tapés à la main) | Powens remonte déjà `LIVRET_A/LDDS/LEP/PEL` avec soldes → demander de retaper est absurde pour un agrégateur |
| Réglages : onglets Scanner / CMA / Overrides | Lus **uniquement** par `Scanner.tsx`. `useDashboard()` et `OptimizerRequest` n'envoient pas `expert`. Onglet « Préférences » = placeholder |
| `PUT /accounts/transactions/{id}/category` | Existe côté back, **aucune UI** — alors que la catégorie est éditable-utile et le TER (exposé) ne l'est pas |
| `LoanResponse.next_payment_date`, `insurance_rate`, `loan_type` | Renvoyés, jamais affichés — alors que « prochaine mensualité le … » est l'info n°1 d'un prêt |

---

## 5. Écran par écran : intention → réalité → ce que ça devrait être

### 5.1 Aperçu (onglet « IA »)
**Intention** : un coup d'œil sur mon patrimoine + le briefing du matin.
**Réalité** : c'est le meilleur écran. Mais il s'appelle « IA » avec une icône étincelles, sous-titre « Revues quotidiennes et conversations » (il n'y a pas de conversation), alors qu'il rend le dashboard patrimoine. Le premier mot qu'un néophyte voit est un contresens. La tuile briefing promet « le prochain arrive vers 3h » à tout le monde, opt-in ou pas.
**Le briefing lui-même** (`prompt_builder.py`) est une note de trader : indices US/EU/Asie, EUR/USD, 10Y, risk-on/off, puis « maintenir / renforcer / alléger » par ligne, plus une section « Analytics Markowitz μ σ Sharpe ». Pour un épargnant en DCA c'est incompréhensible **et** c'est une incitation quotidienne à bouger — l'inverse de la gestion passive. Le prompt interdit même le récap patrimonial et les conseils fiscaux de base, c'est-à-dire ce qu'un débutant attend. `ReviewSheet` affiche modèle, tokens in/out et **coût en $**.
**Cible** : renommer « Aperçu » (icône maison). Tuile briefing avec CTA « Activer le briefing du matin » si off, un seul message d'heure. Briefing réécrit : « ce qui a bougé chez toi, ce que ça veut dire, rien à faire cette semaine » — pas de tickers, pas de μ/σ, pas de coût.

### 5.2 Comptes
**Intention** : voir tous mes comptes, ce qu'il y a dedans, forcer une mise à jour.
**Réalité** : 7 tableaux denses pensés pour 1 200 px, dont 2 imbriqués ; le « Net » ne matche pas celui de l'Aperçu ; l'auto-refresh tape l'endpoint lourd ; l'onboarding Powens retombe sur « IA » sans feedback ; la gestion des banques est enterrée dans Profil › onglet-icône-bouclier avec « Powens, DSP2, OAuth, jetons, Argon2id, tape DELETE ». Le rapport de sync « Cache · 5 comptes, 4 positions, 0 nouvelles transactions » est un log, pas un message. Catégories `charges_logement` brutes.
**Cible** : un gros chiffre « Ton patrimoine » venant **du back uniquement** (`WealthSummary` corrigé pour tous les types). Une **carte par compte** (nom nettoyé, banque, montant, type en français), groupées par catégorie, 1 colonne mobile / 2 desktop. Zéro IBAN, zéro « sync il y a 3h » par ligne : une mention globale « Mis à jour il y a 3 min · Mettre à jour ». Détail dans un **BottomSheet** (il existe déjà) : mouvements sur 2 lignes (libellé + montant / date + catégorie en français, modifiable), positions sur 2 lignes (nom + valeur / qté + plus-value), prêt avec « Prochaine mensualité le … » en premier. « Mes banques » (ajouter/délier/erreur de connexion) **dans Comptes**, pas dans Profil. Un seul hook `useSyncAccounts` : `/sync` au mount et au retour Powens, `/refresh` seulement sur clic ; retour Powens force `view=accounts` + « Banque ajoutée, on récupère tes comptes… » + bouton Réessayer toujours actif.

### 5.3 Investissements
**Intention** : est-ce que mon portefeuille est bien construit ?
**Réalité** : 7 cartes empilées sans hiérarchie (Metrics → Assets → Insights → RiskReturn → Optimizer → Scanner → Correlation), chacune étant la sortie d'une fonction d'`analytics.py` dans le vocabulaire de la fonction. Un utilisateur qui a 4 ETF sur un PEA se voit proposer : un « Drawdown théorique » qui n'est pas un drawdown (−2σ sans μ), un « CVaR 95 % annualisé » (moyenne de queue × √252 : pas de sens statistique), un optimiseur **Max Sharpe par défaut** qui converge vers un coin et dit « vends 12 000 € de World, achète du Nasdaq » sans frais ni fiscalité (le composant l'avoue : « Honnête mais peu nuancé »), un Kelly « levier 2,8× » pour quelqu'un qui ne peut pas s'endetter sur un PEA, un scanner qui promet des ETF et renvoie des actions françaises classées au momentum 5 ans, et une matrice 4×4 avec une diagonale rouge vif. Le Diagnostic déclenche « Concentration sur CW8.PA » pour un portefeuille 60 % World — la config la plus saine possible. La seule vue qu'un débutant comprend (« combien j'aurais perdu en 2020 ») est calculée puis jetée.
**Cible** : « Mes placements », 3 questions dans l'ordre, tenant en 2 écrans de téléphone :
1. *Qu'est-ce que j'ai et ça donne quoi ?* Total, plus-value, liste avec **nom du fonds** (pas le ticker), part %, plus-value, une seule barre de répartition.
2. *Est-ce que je prends trop de risque ?* « En mars 2020 tu aurais perdu X € », « en 2022 Y € », « pire baisse vécue Z % » (StressTests + max DD, déjà calculés) + badge prudent/équilibré/dynamique.
3. *Est-ce que je peux faire mieux ?* Diagnostic réécrit en phrases sans symbole avec une action par phrase (« tes deux fonds Monde font doublon »). Optimiseur = **une** proposition sous contrainte du profil (jamais Max Sharpe par défaut), seuil de matérialité (≥ 5 % ou ≥ 500 €), rappel frais/fiscalité, présentée comme une piste.
**Mode avancé** replié : scatter, matrice (sans diagonale, avec noms), tableau complet, objectifs, contribution au risque, réglages CMA — **à condition de les brancher** sur `/dashboard` et `/optimizer`. **À supprimer** : Scanner en l'état, Kelly, « Drawdown théorique », CVaR, `FrontierCloud`, 2e fetch 10 ans si stress tests cachés.

### 5.4 Projection
**Intention** : si je continue à verser X €/mois, j'aurai combien dans N ans, et j'atteins mon objectif quand ?
**Réalité** : le moteur est sérieux (Monte-Carlo en log, frais composés mois par mois, TER) mais l'écran ouvre sur une **docstring** (« rendements log quotidiens, μ et σ extraits, Monte Carlo paramétrique 1000 trajectoires gaussiennes… »), affiche « μ, σ utilisés » en première case, des centimes à 10 ans, une proba à 2 décimales issue de 1 000 tirages, une formule de frais en mono. Trois μ cohabitent (historique pur / blendé CMA / cible profil). Le broker est forcé BNP (bug #7). « Frais cumulés » = manque à gagner total (frais + intérêts perdus), pas les frais prélevés — le libellé et le « frais mensuels moyens » qui en découle sont faux. **TER probablement compté deux fois** (VL yfinance déjà nettes de TER, puis `apply_ter_to_fee_fn` le re-soustrait — aucun ADR ne tranche, à confirmer). Bengen : formule juste mais **nominale, avant impôts, sans frais**, affichée en 2xl comme une vérité ; défaut 100 €/mois → « 30 000 € » chiffre-jouet ; « augmente le DCA ou μ » comme conseil. Objectif hors échelle → ligne qui disparaît + « 0,00 % » sans explication. Pas d'état vide : un nouvel utilisateur voit `portfolio_empty — Aucune position enregistrée.` en rouge.
**Cible** : une question, pré-remplie depuis le Profil, **un seul rendement estimé partagé par toute l'app** (le μ blendé), frais et fonds inclus, en euros d'aujourd'hui. Trois chiffres gros et arrondis : « Dans 10 ans : environ **48 000 €** (entre 35 et 65 k€, 8 fois sur 10) » · « Tu auras versé **24 000 €** » · « Objectif 25 000 € : atteint vers **2031**, 6 chances sur 10 ». Un graphe : bande grise « zone probable », ligne « le plus probable », pointillé « versé », ligne objectif, labels en années, tap pour lire. Un **curseur « et si… »** sur le versement (le seul levier réel) remplace les alternatives ×1,5/×2. Une ligne frais « Chez BNP ça te coûte ~3 200 € sur la période, chez Trade Republic ~0 € ». Bengen absorbé en toggle « objectif en revenu mensuel » qui réutilise **le même moteur**. Caché derrière « ? » : μ/σ, P10/P90, Monte-Carlo, bull/bear, P50 brut, formule frais, taux de retrait.

### 5.5 Profil / Réglages / Compte
**Intention** : dire à l'app qui je suis pour qu'elle calcule juste.
**Réalité** : 12 champs dont 4 morts, 1 no-op, 5 retapables alors que Powens les connaît ; sauvegarde bloquée sans date de naissance sans explication ; jargon (« RFR N-2 », « Parts fiscales », « Plafond σ. Drawdown attendu ≈ −2σ », « Nasdaq histo ~13 % », « TMI »). Réglages = le panneau avancé du Scanner promu au niveau de la nav globale (« Shrinkage CMA », « Estimateur Σ », « Ledoit-Wolf », « Overrides μ par ticker »). Le tout non synchronisé (bug #1), non purgé au logout (bug #12).
**Cible** : **Profil = une page courte, 5 questions** : date de naissance, foyer (célibataire/couple + enfants → parts calculées), revenu fiscal de référence (avec « où le trouver »), combien j'épargne par mois, curseur prudent ↔ dynamique à 3-5 crans (remplace rendement cible + volatilité max). Supprimer prénom (utiliser `display_name`), TMI, courtier, saisie livrets (lire les soldes agrégés, fallback manuel si aucun livret synchronisé). **Compte** : email, mot de passe (une règle de longueur, flux « définir un mot de passe » pour Google-only), Google, banques, briefing IA, suppression — en bottom sheets. **Supprimer l'écran Réglages** : Scanner/CMA/Overrides → accordéon « Options avancées » là où ils servent. Profil source de vérité en DB, localStorage = cache purgé au logout, erreurs de sync visibles.

### 5.6 Navigation
Pas de routeur : `view` est un `useState`. Refresh = retour accueil, bouton retour = sortie du site, aucun lien partageable. Profil/Réglages sont des `NavView` sans entrée de nav (via UserMenu/MoreSheet) et rendus avec un double header. Sidebar et BottomNav n'ordonnent pas Projection/Investissements pareil ; « Invest. » tronqué. Sous-titres header truffés de jargon, **masqués sur mobile** — visibles uniquement là où ils font le plus peur. → react-router (`/`, `/comptes`, `/placements`, `/projection`, `/profil`, `/compte`), header AppShell unique, un seul composant de menu compte partagé.

---

## 6. Glossaire de remplacement (ce qu'un non-initié doit lire)

| Affiché aujourd'hui | Décision | Formulation simple |
|---|---|---|
| IA (onglet) | renommer | **Aperçu** |
| Patrimoine net / Actifs / Dettes / Net | garder / renommer | Ton patrimoine / Ce que tu as / Ce que tu dois |
| P&L latent, Plus-value, Gain/perte, Coût | unifier | **Gain** (ou perte) depuis l'achat |
| Sync, Cache, positions | renommer | Mettre à jour · « Mis à jour il y a 3 min » |
| Ticker, ISIN | cacher | nom du fonds en premier, ticker en secondaire/expert |
| PRU, Valorisation, Quantité, TER | renommer | Prix d'achat moyen, Valeur actuelle, Nombre de parts, Frais annuels du fonds (?) |
| IBAN, Libellé, Catégorie `charges_logement` | cacher / mapper | Description, catégories en français |
| CTO, PER, PERCO, CSL, CAT, RSP, Art. 83, Revolving | libellés longs | Compte-titres, Plan épargne retraite, Compte à terme, Crédit renouvelable… |
| Capital restant, Échéances restantes, Prêt différé | renommer | Reste à rembourser, Mensualités restantes, Remboursement pas encore commencé |
| E(R) annuel, μ blendé, Espérance | un seul endroit | Rendement attendu (estimation) |
| Volatilité σ annualisée | remplacer | « Amplitude des variations » ou perte 2020/2022 en € ; σ brut en expert |
| Sharpe, r_f | expert | qualitatif « bonne / moyenne / faible rémunération du risque » |
| Drawdown théorique −2σ, CVaR 95 % | **supprimer** | — |
| Max DD observé, peak-to-trough | garder | **Pire baisse vécue** |
| Frontière efficiente, carte (σ, μ), univers | expert | — |
| Max Sharpe / Min variance / Cible vol max / from_strategy | renommer, jamais Max Sharpe par défaut | Meilleur équilibre / Le plus stable / Je fixe mon niveau de risque / Selon mon profil |
| SLSQP, long-only, sum(w)=1, Euler, (Σw)_i | supprimer de l'UI | — |
| Composition (poids w), Contribution à la volatilité | renommer / expert | Répartition / (expert) |
| Full/Half Kelly, levier, sanity check | **supprimer** | — |
| ρ, corrélation, hedge, redondants | renommer | « se ressemblent / se compensent » ; matrice en expert |
| Scanner, ΔSharpe, contribution marginale, modes, Euronext | supprimer en l'état | — |
| Monte-Carlo, P10/P25/P50/P75/P90, quantiles, bull/bear, DCA, gaussien | cacher | « zone probable (8 fois sur 10) », « le plus probable », « ce que tu auras versé », versement mensuel |
| Broker (frais), Horizon | renommer | Chez qui tu investis, Pendant combien d'années |
| Bengen, taux de retrait, revenu passif soutenable | cacher | « Vivre de ton épargne » — « Quel revenu mensuel voudrais-tu ? » |
| as-if-held, PnL, base 100, Rolling Sharpe 126j, benchmark CW8.PA | supprimer / renommer | « Ton portefeuille vs le marché mondial », en % depuis le début ; Sharpe glissant → expert |
| RFR N-2, Parts fiscales, TMI | renommer / supprimer | Revenu fiscal de référence (où le trouver), Situation du foyer ; TMI supprimé |
| Rendement cible, Volatilité max, stratégie, glide path | remplacer | curseur prudent ↔ dynamique |
| Shrinkage CMA, Estimateur Σ, Ledoit-Wolf, Overrides μ, taux sans risque | expert (et **brancher**) | — |
| Powens, DSP2, OAuth, jetons, Argon2id, RGPD, tape DELETE | reformuler | « Tangent se connecte à ta banque via un service agréé, on ne voit jamais tes identifiants » ; « Connexion Google » ; « tape SUPPRIMER » |
| Risky businesses / Portfolio Dashboard / Tangent | unifier | Tangent |
| claude-sonnet · tokens · $0.123 | supprimer de l'UI | — |

---

## 7. Plan de refonte proposé (PRs dans l'ordre)

Principe : d'abord arrêter de mentir et arrêter de casser, ensuite simplifier, ensuite embellir. Chaque ligne = une PR de taille raisonnable, CI verte, déployée seule.

### Phase A — Stop the bleeding (1 semaine, aucune décision produit)
| PR | Contenu |
|---|---|
| A1 `fix(profile)` | `profile-sync.ts` via `http()` + `API_URL` ; erreurs remontées ; envoyer tous les champs ; `_to_out` renvoie `default_broker` ; purge localStorage au logout ; unités uniformisées vers le prompt |
| A2 `fix(accounts)` | `HoldingResponse` expose `ter`/`ter_source` ; `isError` gérés ; `/connections` renvoie 502 au lieu de `[]` ; auto-refresh → `/sync` ; un seul `useSyncAccounts` avec une seule liste d'invalidation |
| A3 `fix(onboarding)` | Retour Powens → `view=accounts`, feedback succès/erreur, bouton Sync jamais désactivé quand une connexion existe |
| A4 `fix(mobile-tables)` | `Assets.tsx` cellules `hidden md:table-cell` alignées sur les en-têtes ; `grid-cols-3` → `grid-cols-1 sm:grid-cols-3` (Comptes header, Bengen) ; `min-w-0` sur les truncate |
| A5 `fix(wealth)` | `get_user_wealth` couvre tous les `AccountType` (PER/PEE/mortgage/…), prêts en `used_amount` ; Comptes lit `WealthSummary` au lieu de recalculer |
| A6 `fix(projection)` | Broker : ne plus écraser par le défaut YAML ; échelle Y sans bull ; objectif inclus dans l'échelle ; état vide propre ; `ChartTile` gère l'erreur |
| A7 `chore(dead-code)` | Supprimer `AI.tsx`, `streaming.ts`, hooks watchlist/history inutilisés (ou les rebrancher explicitement) ; dédoublonner `api.ts` ; un seul `Section` ; `docker-compose` `VITE_API_URL` avec `/api` ; règle mot de passe unique |
| A8 `perf(routes)` | `yf.download`/`yf.screen` via `run_in_threadpool` ; `FrontierCloud` supprimée ; stress tests cachés (calcul 1×/jour) |

### Phase B — Fondations UX (1-2 semaines)
| PR | Contenu |
|---|---|
| B1 `feat(router)` | react-router, 6 routes, header AppShell unique, plus de « Retour » maison, retour téléphone OK |
| B2 `feat(shell)` | safe-area iOS (`viewport-fit=cover`, `env(safe-area-inset-bottom)`), cibles 44 px, un seul composant menu compte, dialogs → BottomSheet sur mobile, « Aperçu » à la place de « IA », marque unique |
| B3 `feat(charts)` | Un composant graphe responsive (viewBox calculé sur la largeur réelle, tailles de texte en px CSS, `onPointer*`, tooltip contraint dans le conteneur), utilisé par Projection, Timeline, RiskReturn |
| B4 `feat(profile-v2)` | Profil 5 questions + curseur de risque ; suppression des champs morts ; livrets lus depuis Powens ; DTO back allégé (migration Alembic) ; écran Réglages supprimé, options avancées déplacées |

### Phase C — Simplification produit (2-3 semaines, décisions à valider avec toi, cf. §8)
| PR | Contenu |
|---|---|
| C1 `feat(accounts-v2)` | Cartes de comptes + détail en BottomSheet + « Mes banques » dans Comptes + catégories en français éditables |
| C2 `feat(placements-v2)` | Écran 3 questions ; StressTests en € ; diagnostic réécrit sans symboles ; optimiseur = 1 proposition sous contrainte profil, seuil de matérialité ; mode avancé replié et **branché** sur les réglages |
| C3 `feat(projection-v2)` | Un μ partagé (ADR à écrire : quel μ, TER compté une fois), 3 chiffres arrondis, curseur « et si », ligne frais comparée, Bengen absorbé (inflation + fiscalité intégrées) |
| C4 `feat(briefing-v2)` | Prompt réécrit pour un épargnant passif ; CTA d'activation ; historique accessible ; métadonnées de coût retirées de l'UI |
| C5 `refactor(scanner)` | Supprimer, ou refondre plus tard sur un univers ETF UCITS curé (ADR-016) avec une vraie watchlist visible |

---

## 8. Décisions que toi seul peux prendre

1. **Le Scanner** : on le supprime (mon avis) ou on le garde en mode expert en attendant ADR-016 ?
2. **Le μ unique** : blendé CMA 70/30 partout (Projection incluse) ? Et on tranche le double-comptage TER ?
3. **L'optimiseur** : on le garde comme « une piste » sous contrainte du profil, ou on le sort du parcours simple ?
4. **Le briefing IA** : quel public ? Si c'est toi + un proche non-initié, le prompt actuel (trader) est à jeter.
5. **Réglages** : OK pour supprimer l'écran et déplacer le peu d'utile dans un accordéon ?
6. **Profil** : OK pour lire les soldes de livrets depuis Powens et virer la saisie manuelle ?
7. **Ordre** : Phase A d'abord (je peux commencer tout de suite en local, tu pushes ou tu m'attaches le repo en push), puis B, puis C écran par écran ?
