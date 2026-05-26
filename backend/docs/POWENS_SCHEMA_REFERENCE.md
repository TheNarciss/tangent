# Powens API — Référence de schéma consolidée

> Compilation manuelle de la doc Powens publique (docs.powens.com) au 26/05/2026.
> **Pour régénérer ou compléter** : `bash scripts/fetch_powens_docs.sh`
> **Source officielle** : https://docs.powens.com/api-reference/

---

## Table des matières

1. [Types de comptes (30 supportés)](#types-de-comptes)
2. [BankAccount — champs communs](#bankaccount)
3. [BankAccount — sous-objets selon type](#sous-objets)
4. [Investment](#investment)
5. [InvestmentDetails (expand)](#investmentdetails)
6. [Transaction](#transaction)
7. [Connection](#connection)
8. [Connector / Bank](#connector)
9. [Loan](#loan)
10. [LoanAmortization](#loanamortization)
11. [Pocket (employee savings)](#pocket)
12. [MarketOrder](#marketorder)
13. [Stratégie fresh-first par type](#fresh-first)

---

## Types de comptes

`GET /account_types` retourne 30 types. Voici la liste avec leur sous-objet typique.

| Type | Display name | is_invest | Sous-objet | Notes |
|---|---|---|---|---|
| `unknown` | Inconnu | | | |
| `checking` | Compte courant | | transactions | RIB, IBAN |
| `savings` | Compte épargne | | transactions | |
| `deposit` | Compte de dépots | | transactions | |
| `joint` | Comptes joint | | transactions | |
| `card` | Compte carte | | transactions | `id_parent` ≠ null |
| `livret_a` | Livret A | | transactions | plafond 22 950 € |
| `livret_b` | Livret B | | transactions | |
| `ldds` | LDDS | | transactions | plafond 12 000 € |
| `lep` | LEP | | transactions | sous condition, taux boosté |
| `csl` | Compte sur Livret | | transactions | |
| `cel` | CEL | | transactions | |
| `pel` | PEL | | transactions | bloqué 4 ans min |
| `cat` | Compte à terme | | transactions | |
| `loan` | Compte de prêt | | loan + amortizations | |
| `mortgage` | Crédit immobilier | | loan + amortizations | |
| `consumercredit` | Crédit conso | | loan + amortizations | |
| `revolvingcredit` | Crédit renouvelable | | loan + amortizations | |
| `market` | Compte titres (CTO) | ✓ | investments + marketorders | |
| `pea` | PEA | ✓ | investments + marketorders | enveloppe fiscale FR |
| `capitalisation` | Contrat capitalisation | ✓ | investments | |
| `lifeinsurance` | Assurance vie | ✓ | investments | enveloppe fiscale FR |
| `per` | PER (Plan Épargne Retraite) | ✓ | investments | déblocage retraite |
| `perp` | PERP (ancien PER) | ✓ | investments | remplacé par PER |
| `perco` | PERCO (épargne entreprise retraite) | ✓ | investments + pockets | |
| `pee` | PEE (Plan Épargne Entreprise) | ✓ | investments + pockets | parts gratuites |
| `madelin` | Contrat retraite Madelin | ✓ | investments | TNS |
| `article83` | Article 83 | ✓ | investments + pockets | retraite collective |
| `rsp` | Réserve spéciale participation | ✓ | investments + pockets | |
| `real_estate` | Placement immobilier | ✓ | investments | SCPI, etc. |
| `crowdlending` | Financement participatif | ✓ | investments | |

---

## BankAccount

Champs communs à TOUS les types de comptes (`GET /users/me/accounts`).

| Champ | Type | Description |
|---|---|---|
| `id` | Integer | ID interne Powens |
| `id_user` | Integer | User propriétaire |
| `id_connection` | Integer | Connection (= banque) liée |
| `id_source` | Integer | Source de la connection (openapi/directaccess) |
| `id_parent` | Integer\|null | Parent account (cas comptes carte rattachés à un courant) |
| `id_type` | Integer | ID du type (mapping voir `account_types`) |
| `type` | String | Code technique du type (cf liste ci-dessus) |
| `name` | String | Nom display (peut être overridé par l'utilisateur) |
| `original_name` | String | Nom natif tel que sur la banque |
| `number` | String\|null | Numéro de compte (souvent masqué) |
| `iban` | String\|null | IBAN |
| `bic` | String\|null | BIC |
| `webid` | String\|null | ID interne Powens (web-friendly) |
| `currency` | Currency dict | `{id: "EUR", symbol: "€", prefix: false, crypto: false}` |
| `balance` | Decimal\|null | Solde (snapshot reçu de la banque) |
| `coming` | Decimal\|null | Montant des opérations à venir |
| `coming_balance` | Decimal\|null | balance + coming |
| `formatted_balance` | String | Solde formaté locale-aware |
| `last_update` | DateTime\|null | Dernier sync réussi |
| `opening_date` | Date\|null | Date d'ouverture du compte |
| `usage` | String | `PRIV` (privé) / `ORGA` (pro) / null |
| `ownership` | String\|null | `owner` / `co-owner` / `attorney` (déprécié) |
| `bookmarked` | Integer | Bookmark utilisateur (0/1) |
| `display` | Boolean | Doit-il être affiché ? |
| `deleted` | DateTime\|null | Si supprimé chez la banque |
| `disabled` | DateTime\|null | Si désactivé par user |
| `error` | String\|null | Code erreur si dernier sync KO |
| `company_name` | String\|null | Nom de l'entreprise (PEE/PERCO) |
| `information` | Dict | Champs custom additionnels |
| `loan` | Loan object\|null | Détails prêt si type=loan/mortgage/etc |

### Champs CALCULÉS par Powens (pour comptes invest uniquement)

Présents si `type` ∈ {market, pea, lifeinsurance, capitalisation, per, perp, perco, pee, article83, rsp, madelin, real_estate, crowdlending}.

**Le champ `calculated[]` liste explicitement ces champs**, signalant qu'ils sont dérivés (= sum holdings) plutôt que reçus brut de la banque.

| Champ | Description | À utiliser ? |
|---|---|---|
| `valuation` | **Sum(investments.valuation)** — la VRAIE valeur du compte | ✅ OUI, à préférer à `balance` |
| `diff` | Plus/moins-value totale absolue (€) | Pour afficher gain/perte |
| `diff_percent` | Plus/moins-value totale relative (ratio, 1 = 100%) | Pour afficher % perf |
| `prev_diff` | Diff vs synchro précédente | Pour sparkline J-1 |
| `prev_diff_percent` | Diff % vs synchro précédente | |
| `calculated[]` | `["valuation", "diff", "diff_percent", "prev_diff", "prev_diff_percent"]` | Métadonnée |

---

## Sous-objets

### Account.loan (inliné dans BankAccount si type=loan/mortgage/etc)

| Champ | Type | Description |
|---|---|---|
| `total_amount` | Decimal | Capital emprunté |
| `available_amount` | Decimal\|null | Capital débloqué et dispo |
| `used_amount` | Decimal\|null | Capital déjà utilisé |
| `subscription_date` | Date\|null | Date de souscription |
| `maturity_date` | Date\|null | Date de fin estimée |
| `start_repayment_date` | Date\|null | Date début remboursement (utile pour prêts différés) |
| `deferred` | Boolean | True si prêt en différé (remboursement pas encore commencé) |
| `next_payment_amount` | Decimal\|null | Montant prochaine mensualité |
| `next_payment_date` | Date\|null | Date prochaine mensualité |
| `last_payment_amount` | Decimal\|null | Montant dernière mensualité |
| `last_payment_date` | Date\|null | Date dernière mensualité |
| `nb_payments_done` | Integer\|null | Échéances payées |
| `nb_payments_left` | Integer\|null | Échéances restantes |
| `nb_payments_total` | Integer\|null | Total échéances |
| `rate` | Decimal\|null | Taux nominal du prêt (% absolu, ex 2.0 = 2%) |
| `duration` | Integer\|null | Durée totale en mois |
| `insurance_label` | String\|null | Label de l'assurance emprunteur |
| `insurance_amount` | Decimal\|null | Montant assurance |
| `insurance_rate` | Decimal\|null | Taux assurance (ratio 0-1) |
| `account_label` | String\|null | Compte débité |
| `type` | String | `mortgage` / `consumercredit` / `revolvingcredit` / `loan` |

---

## Investment

`GET /users/me/accounts/{id}/investments` ou `GET /users/me/investments`

| Champ | Type | Description |
|---|---|---|
| `id` | Integer | ID interne Powens |
| `id_account` | Integer | Compte parent |
| `label` | String | Nom display (ex: "AM.PEA MSCI WORLD UCITS ETF") |
| `code` | String\|null | Code technique (ISIN ou AMF) |
| `code_type` | String | `ISIN` ou `AMF` |
| `source` | String | `website` ou `notFound` |
| `description` | String\|null | Description optionnelle |
| `stock_symbol` | String\|null | Ticker bourse (ex: "DCAM") |
| `stock_market` | String\|null | Place de cotation (ex: "Euronext Paris") |
| `quantity` | Decimal | Quantité détenue |
| `unitprice` | Decimal | **Prix d'achat (PRU)** |
| `unitvalue` | Decimal | **Prix courant unitaire** |
| `valuation` | Decimal | `quantity × unitvalue` (valeur totale courante) |
| `diff` | Decimal | Plus/moins-value absolue (€) |
| `diff_percent` | Decimal | Plus/moins-value relative (ratio) |
| `prev_diff` | Decimal\|null | Diff vs synchro précédente |
| `prev_diff_percent` | Decimal\|null | Diff % vs synchro précédente |
| `prev_vdate` | Date\|null | Date de la synchro précédente |
| `vdate` | Date | Date de valorisation |
| `portfolio_share` | Decimal | Allocation dans le portefeuille (ratio 0-1) |
| `calculated[]` | Array\<String\> | Liste des champs dérivés (vs reçus brut) |
| `deleted` | Date\|null | Date de suppression si position fermée |
| `last_update` | DateTime | Dernière sync |
| `details` | InvestmentDetails\|null | Méta (avec `?expand=details`) |

### Champs originaux (currency étrangère)

Pour investissements internationaux dans une devise ≠ devise du compte :

| Champ | Description |
|---|---|
| `original_currency` | Currency dict |
| `original_valuation` | Valuation en devise originale |
| `original_unitvalue` | Prix courant en devise originale |
| `original_unitprice` | PRU en devise originale |
| `original_diff` | Diff en devise originale |

---

## InvestmentDetails

Disponible via `?expand=details` sur un Investment.

| Champ | Type | Description |
|---|---|---|
| `performance_1_year` | Decimal\|null | Perf sur 1 an (ratio 0-1) |
| `performance_3_years` | Decimal\|null | Perf sur 3 ans |
| `performance_5_years` | Decimal\|null | Perf sur 5 ans |
| `srri` | Decimal\|null | **Synthetic Risk Reward Indicator (1 à 7)** |
| `asset_category` | String\|null | "Actions" / "Obligations" / "Diversifié" / etc. |
| `recommended_period` | String\|null | Période d'investissement recommandée |
| `last_update` | DateTime\|null | Dernière sync des détails |

**Application directe** : `srri` peut alimenter notre classification risk dans le portfolio. `asset_category` aussi pour la diversification automatique.

---

## Transaction

`GET /users/me/accounts/{id}/transactions`. **40 champs**, très riche.

| Champ | Type | Description |
|---|---|---|
| `id` | Integer | ID interne |
| `id_account` | Integer | Compte parent |
| `id_category` | Integer\|null | Catégorie (mapping voir `/categories`) |
| `id_cluster` | Integer\|null | Si la tx appartient à un cluster (récurrences) |
| `date` | Date | Date opération |
| `rdate` | Date | Date réelle (rare quand ≠ date) |
| `vdate` | Date\|null | Date valeur (souvent null) |
| `bdate` | Date\|null | Booking date |
| `datetime` | DateTime\|null | Timestamp complet si dispo |
| `rdatetime` | DateTime\|null | Real datetime |
| `vdatetime` | DateTime\|null | Value datetime |
| `bdatetime` | DateTime\|null | Booking datetime |
| `application_date` | Date | Date à utiliser pour le filtrage par défaut |
| `date_scraped` | DateTime | Date à laquelle Powens l'a vue |
| `value` | Decimal | Montant signé (- = débit) |
| `gross_value` | Decimal\|null | Valeur brute (avant commission) |
| `commission` | Decimal\|null | Commission |
| `commission_currency` | Currency\|null | Devise commission |
| `formatted_value` | String | Montant formaté locale |
| `original_value` | Decimal\|null | Si devise étrangère |
| `original_gross_value` | Decimal\|null | |
| `original_currency` | Currency\|null | |
| `wording` | String | Libellé court |
| `simplified_wording` | String | Libellé simplifié (parsé) |
| `original_wording` | String | Libellé brut tel quel |
| `stemmed_wording` | String | Libellé "stemmed" pour ML/recherche |
| `type` | String | `transfer` / `card` / `withdrawal` / `payment` / `order` / etc. |
| `state` | String | `parsed` / etc. |
| `card` | String\|null | Numéro carte (masqué) |
| `counterparty` | Object\|null | Bénéficiaire (entreprise/personne) |
| `coming` | Boolean | Pas encore postée |
| `active` | Boolean | False = ignorée par PFM |
| `deleted` | DateTime\|null | Supprimée chez banque |
| `country` | String\|null | Code pays |
| `comment` | String\|null | Commentaire utilisateur |
| `details` | Object\|null | Détails additionnels |
| `documents_count` | Integer | Documents attachés |
| `informations` | Dict | Custom fields |
| `last_update` | DateTime | Dernière sync |
| `webid` | String\|null | ID web |

### Filtrage côté API

- `min_date` / `max_date` (sur `application_date` ou `date` selon `date_field`)
- `min_value` / `max_value`
- `search` (cherche dans wording, dates, values, categories)
- `deleted` flag pour inclure les supprimées
- `last_update` pour filtrer par date de dernière modif (utile pour sync incrémental)

---

## Connection

`GET /users/me/connections` (utiliser `?expand=connector,bank` pour avoir les noms)

| Champ | Type | Description |
|---|---|---|
| `id` | Integer | ID connection |
| `id_user` | Integer | User propriétaire |
| `id_connector` | Integer | Connecteur (BNP, Crédit Agri, etc) |
| `id_bank` | Integer | Banque (legacy) |
| `id_provider` | Integer | Provider |
| `connector_uuid` | String | UUID du connecteur |
| `connector` | Connector object (expand) | Objet complet du connecteur |
| `bank` | Bank object (expand) | Objet complet de la banque (legacy) |
| `active` | Boolean | Activée pour sync ? |
| `created` | DateTime | Date de création |
| `expire` | DateTime\|null | Expiration |
| `last_update` | DateTime\|null | Dernier sync |
| `last_push` | DateTime\|null | Dernier webhook |
| `next_try` | DateTime\|null | Prochaine tentative auto |
| `state` | String\|null | Code erreur dernier sync (null = OK) |
| `error` | String\|null | Code erreur user-facing |
| `error_message` | String\|null | Message d'erreur user-facing |
| `sources` | Array | Sources de sync (PSD2, scraping, etc.) |

### États possibles (state)

| State | Sens |
|---|---|
| `null` | Sync OK |
| `SCARequired` | SCA renforcée nécessaire (login) |
| `wrongpass` | Mauvais identifiants |
| `additionalInformationNeeded` | Champ supplémentaire requis |
| `actionNeeded` | Action utilisateur requise (CGU) |
| `decoupled` | Validation app banque |
| `webauthRequired` | Re-auth web requise |
| `passwordExpired` | Mot de passe expiré |

---

## Connector

`GET /connectors/{id}?expand=fields` (l'expand donne les fields du formulaire de credentials)

| Champ | Type | Description |
|---|---|---|
| `id` | Integer | ID connecteur |
| `uuid` | String | UUID stable |
| `name` | String | "BNP Paribas" |
| `slug` | String | "BNP" (short) |
| `code` | String | Code banque (ex: "30004") |
| `color` | String | Hex color de la marque |
| `hidden` | Boolean | Caché de la liste |
| `restricted` | Boolean | Restreint à certains users |
| `charged` | Boolean | Facturé |
| `beta` | Boolean | Mode beta |
| `account_types[]` | Array\<String\> | Types de comptes supportés |
| `account_usages[]` | Array\<String\> | `PRIV` / `ORGA` |
| `capabilities[]` | Array\<String\> | `bank` / `wealth` / `document` / `transfer` / etc. |
| `categories[]` | Array | Catégories |
| `countries[]` | Array | Pays supportés |
| `auth_mechanism` | String | `webauth` / `credentials` |
| `available_auth_mechanisms[]` | Array | Toutes les mécaniques possibles |
| `documents_type[]` | Array | Types de documents disponibles |
| `available_transfer_mechanisms[]` | Array | Pour les virements |
| `transfer_beneficiary_types[]` | Array | Types de bénéficiaires |
| `transfer_execution_date_types[]` | Array | `deferred` / `first_open_day` / `instant` |
| `payment_settings` | Dict | Settings paiement détaillés |
| `sync_periodicity` | Integer\|null | Périodicité automatique de sync |
| `months_to_fetch` | Integer\|null | Mois d'historique disponibles |
| `siret` | String\|null | SIRET de la banque |
| `stability` | Object | `{status: "stable"\|"unstable", last_update}` |
| `products[]` | Array | `bank` / `pay` / `wealth` |

---

## Loan

Inliné dans `account.loan` (cf [#sous-objets](#sous-objets)).

---

## LoanAmortization

`GET /users/me/accounts/{id}/loanamortizations`

Tableau d'amortissement détaillé. **404 si le prêt est différé** ou n'a pas commencé à rembourser.

| Champ probable | Description |
|---|---|
| `date` | Date de l'échéance |
| `principal` | Part de capital remboursée |
| `interest` | Part d'intérêts |
| `insurance` | Part d'assurance |
| `total` | Mensualité totale |
| `balance_after` | Capital restant dû après cette échéance |

> ⚠️ Pas pu confirmer les noms exacts (404 sur sandbox tant que ton prêt est différé). À vérifier quand tu rentreras en phase remboursement.

---

## Pocket

`GET /users/me/accounts/{id}/pockets`

Pour les comptes d'épargne salariale (PEE/PERCO/etc.). Représente les "parts gratuites" attribuées par l'entreprise.

| Champ probable | Description |
|---|---|
| `id` | ID pocket |
| `id_investment` | Investment lié |
| `label` | Nom du fonds |
| `quantity` | Quantité de parts |
| `availability_date` | Date à laquelle les parts deviennent disponibles |
| `condition` | Condition de déblocage |

> ⚠️ Pas testé directement (pas de PEE dans ton setup). À vérifier quand tu ouvriras un compte épargne entreprise.

---

## MarketOrder

`GET /users/me/accounts/{id}/marketorders`

Historique des ordres de bourse passés sur un PEA/CTO.

| Champ | Description |
|---|---|
| `id` | ID order |
| `id_account` | Compte parent |
| `number` | Numéro de l'ordre |
| `label` | Nom de l'investissement |
| `code` | ISIN |
| `stock_symbol` | Ticker bourse |
| `direction` | `buy` / `sell` |
| `order_type` | `limit` / `market` / `stop` / etc. |
| `state` | `Executed` / `Pending` / `Cancelled` |
| `stock_market` | "NASDAQ" / "Xetra" / etc. |
| `payment_method` | `CASH` / `DEFERRED` / `UNKNOWN` |
| `creation_date` | Date de création |
| `execution_date` | Date d'exécution |
| `validity_date` | Date de validité |
| `quantity` | Quantité achetée/vendue |
| `total_amount` | Montant total |

**Application directe** : on peut reconstruire l'historique des transactions PEA exactes pour calcul du PRU et de l'historique de DCA.

---

## Fresh-first

Règles "prendre la donnée la plus à jour" par type de compte.

### Comptes invest (`market`, `pea`, `lifeinsurance`, `capitalisation`, `per`, `perp`, `perco`, `pee`, `article83`, `rsp`, `madelin`, `real_estate`, `crowdlending`)

| Donnée | Sources possibles | Choix fresh-first |
|---|---|---|
| Balance compte | `account.balance` OU `account.valuation` (calculé) | ✅ **`account.valuation`** (toujours plus fresh) |
| Position individuelle | `investment.valuation` | `investment.valuation` (Powens) ou `quantity × yfinance_live` (option intraday) |
| PRU | `investment.unitprice` | `investment.unitprice` (Powens) |
| Gain/perte total compte | `account.diff` / `account.diff_percent` | ✅ Powens calcule, on prend |
| Allocation % | `investment.portfolio_share` | ✅ Powens calcule, on prend |

### Comptes cash (`checking`, `savings`, `livret_a`, `ldds`, `lep`, `cel`, `pel`, `csl`, `cat`, `deposit`, `joint`, `card`)

| Donnée | Source | Note |
|---|---|---|
| Balance | `account.balance` | Pas mieux, c'est la source unique |
| Balance projeté | `account.coming_balance` | balance + opérations à venir |
| Transactions | `transactions[]` | Filtrer par `application_date` |

### Comptes prêt (`loan`, `mortgage`, `consumercredit`, `revolvingcredit`)

| Donnée | Source | Note |
|---|---|---|
| Capital restant dû | `account.balance` (signé négatif) | |
| Mensualité | `account.loan.next_payment_amount` | |
| Date prochain remb | `account.loan.next_payment_date` | |
| Taux | `account.loan.rate` | % absolu (2.0 = 2%) |
| Échéances restantes | `account.loan.nb_payments_left` | |
| Tableau amortissement | `GET /accounts/{id}/loanamortizations` | 404 si prêt différé |

### Comptes épargne entreprise (`pee`, `perco`, `article83`, `rsp`)

| Donnée | Source | Note |
|---|---|---|
| Valeur totale | `account.valuation` (calculé par Powens) | inclut investissements |
| Parts gratuites | `pockets[]` | À sommer pour vue complète |

---

## TL;DR — Quand on dev une nouvelle feature

1. **Identifier les types de comptes concernés** (tableau Types de comptes en haut)
2. **Identifier la donnée à récupérer** (BankAccount / Investment / Transaction / Loan / Pocket / MarketOrder)
3. **Vérifier la stratégie fresh-first** (tableau ci-dessus)
4. **Implémenter le mapping** dans `app/powens/aggregator.py`
5. **Si la doc est incomplète, regarder `backend/docs/powens_reference/`** (résultat de `bash scripts/fetch_powens_docs.sh`)
