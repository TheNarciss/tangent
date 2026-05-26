# ADR-013 : Stratégie de stockage "hot+JSONB" pour les données Powens

| Status | Date | Decision-makers |
| --- | --- | --- |
| Accepted | 2026-05-26 | @clem |

Lié à : [ADR-008 Powens aggregator](./008-powens-aggregator.md), [ADR-006 Persistent storage](./006-persistent-storage.md)

## Contexte

Powens normalise 30 types de comptes (`checking`, `pea`, `loan`, `mortgage`,
`per`, `pee`, `livret_a`, etc.) et plusieurs ressources liées (Loan,
Investment, InvestmentDetails, Pocket, MarketOrder, LoanAmortization,
Transaction) avec 20 à 40 champs chacune.

L'inventaire empirique du sandbox actuel a montré :
- Beaucoup de champs non-utilisés mais potentiellement intéressants
  (ex: `investment.portfolio_share`, `account.diff_percent`,
  `transaction.stemmed_wording`)
- Quelques champs non-documentés présents dans la réponse
  (ex: `webid`, `bic`, `id_source`, `coming_balance`)
- Powens enrichit régulièrement son schéma sans toujours documenter

On veut un stockage qui :
1. **Ne perde rien** — toute l'info renvoyée par Powens doit pouvoir être
   retrouvée plus tard, même les champs non-documentés.
2. **Soit performant sur les usages courants** — list/filter/join sur les
   champs critiques doit rester en SQL natif.
3. **N'impose pas une migration à chaque ajout Powens** — Powens fait évoluer
   son API en continu.
4. **Soit lisible** — les colonnes nommées sont plus explicites qu'un blob.

## Décision

On adopte le pattern **"hot fields + raw_data JSONB"** sur chaque table qui
stocke des données Powens (`bank_accounts`, `loans`, `account_holdings`,
`investment_details`, `bank_transactions`, `pockets`, `market_orders`,
`loan_amortizations`).

### Structure-type

Chaque table contient :

1. **Colonnes typées** pour les champs "hot" (utilisés en UI, queries, calculs)
2. **`raw_data JSONB NOT NULL DEFAULT '{}'`** contenant **la totalité** de la
   réponse Powens pour cette ressource

```sql
CREATE TABLE bank_accounts (
    -- ... colonnes typées hot ...
    balance NUMERIC(15, 4),
    valuation NUMERIC(15, 4),
    -- ... etc ...
    raw_data JSONB NOT NULL DEFAULT '{}'
);
```

### Critères "hot field"

Un champ Powens devient une colonne typée si **au moins une** des conditions :
- Affiché dans une vue de liste ou une card principale
- Utilisé dans un `WHERE`, `ORDER BY`, ou `JOIN`
- Agrégé / calculé (somme, moyenne, projection)
- Indexé pour la performance

Sinon → reste uniquement dans `raw_data`.

### Workflow de promotion

Quand un champ "cold" devient "hot" (ex: on veut filtrer par `bookmarked`) :
1. Migration Alembic : `ALTER TABLE ... ADD COLUMN <field>`
2. Backfill optionnel : `UPDATE ... SET <field> = (raw_data->>'<field>')::TYPE`
3. Le aggregator extrait désormais le champ dans la colonne au prochain sync

Le champ reste aussi dans `raw_data` → double source, pas de perte.

### Pattern aggregator

```python
# Dans PowensAggregator.get_accounts()
for acc in powens_accounts:
    extracted = {
        "balance": acc.get("balance"),
        "valuation": acc.get("valuation"),
        # ... autres hot fields
    }
    dto = BankAccount(**extracted, raw_data=acc)  # raw_data = dict complet
```

### Pattern query

```python
# Hot field (SQL classique)
stmt = select(BankAccount).where(BankAccount.bookmarked.is_(True))

# Cold field (JSONB operator)
stmt = select(BankAccount).where(
    BankAccount.raw_data["webid"].astext == "abc123"
)
```

## Conséquences

### Positives
- ✅ Aucune perte d'information — `raw_data` est exhaustif
- ✅ Résilient aux ajouts/changements Powens — nouveaux champs auto-stockés
- ✅ Performance préservée — queries fréquentes sur colonnes typées indexées
- ✅ Lisibilité — colonnes nommées pour les champs courants
- ✅ Migration faible — promouvoir un champ = 1 `ADD COLUMN` (additif, idempotent)

### Négatives
- ⚠️ Légère redondance — hot fields stockés deux fois (colonne + raw_data)
  → coût stockage marginal (quelques %), bénéfice de robustesse > coût.
- ⚠️ Queries JSONB plus verbeuses
  → acceptable car rare; quand récurrent → promouvoir en colonne.

### Indexation
- Pas d'index GIN sur `raw_data` par défaut (coût d'écriture).
- À activer ponctuellement si une query JSONB devient fréquente :
  `CREATE INDEX ... ON ... USING GIN (raw_data jsonb_path_ops);`

### Schéma Powens documenté
Référence des champs disponibles par ressource :
- Cheat sheet : `backend/docs/POWENS_SCHEMA_REFERENCE.md`
- Doc Powens en local : `backend/docs/powens_reference/` (re-sync via
  `bash scripts/fetch_powens_docs.sh`)

## Alternatives considérées

| Option | Verdict |
| --- | --- |
| **Tout typé** (1 colonne par champ Powens) | Refusé : 30+ colonnes par table, migration à chaque évolution Powens, rigide |
| **Tout JSONB** (uniquement `raw_data`) | Refusé : pas d'indexation, queries lentes, pas de typage Pydantic |
| **JSON Schema versionné** | Sur-engineered pour le volume actuel, à reconsidérer en Phase C+ |

## Suivi

- Si une colonne `raw_data` dépasse régulièrement 50 KB → reconsidérer la structure
- Si plus de 50% des queries vont sur JSONB → reconsidérer le découpage hot/cold
- Tracker la croissance via `pg_total_relation_size('bank_accounts')`
