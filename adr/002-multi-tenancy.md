# ADR-002: Stratégie multi-tenant

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Tangent doit pouvoir héberger plusieurs utilisateurs sur la même instance sans qu'aucun puisse jamais voir, modifier ou supprimer les données d'un autre. Les données concernées : portfolio, transactions, profil financier, tokens Powens, fichiers uploadés, configurations.

Une fuite cross-tenant serait une faute lourde (données bancaires).

## Décision

**Multi-tenancy row-level via foreign key `user_id`** sur chaque table de données utilisateur.

Règles strictes :
1. Toute table contenant des données user a une colonne `user_id` NOT NULL avec FK `ON DELETE CASCADE` vers `user.id`
2. Toute requête de lecture filtre **systématiquement** par `user_id = current_user.id`
3. Tout endpoint authentifié dépend de `current_active_user` (fastapi-users)
4. Les repositories exposent uniquement des méthodes qui prennent `user_id` en paramètre obligatoire (pas de `get_all()` sans user)
5. Les tests d'intégration incluent **obligatoirement** un test "user A ne voit pas les données de user B"

Pas de schéma Postgres séparé par tenant, pas de DB séparée, pas de RLS Postgres (overkill pour notre scale).

## Conséquences

### Positives

- Simple à implémenter et à comprendre
- Une seule DB à backup/restaurer
- Indexes partagés efficaces
- Migrations triviales
- Scaling vertical suffisant pour ~10k users sur la même instance

### Négatives

- Une bug d'oubli de filtre `user_id` = fuite cross-tenant → discipline obligatoire en code review
- Pas d'isolation stricte au niveau Postgres (RLS aurait offert ça)
- Une corruption DB impacte tous les users

## Alternatives considérées

### Option A — DB par tenant

Maximum d'isolation, simple modèle mental. Écartée car overhead opérationnel énorme (N migrations, N backups, N connexions) pour un projet self-host.

### Option B — Schema Postgres par tenant

Compromis intermédiaire. Écartée car complexité de migrations (chaque schema à upgrade) et de connexion pool.

### Option C — Row-Level Security (RLS) Postgres

Filtrage forcé au niveau DB. Excellent pour la sécurité mais ajoute une couche complexe (policies à maintenir), perf overhead, et SQLAlchemy async gère moins bien. À considérer plus tard si on grossit.

## Notes

- À chaque nouveau modèle, ajouter `user_id` FK est non-négociable
- Le test multi-tenant isolation a été validé manuellement le 2026-05-22 (cf transcript) — il doit devenir un test automatisé en CI
- Si à l'avenir on ajoute du "sharing" (couple, conseiller), passer par une table de jonction `account_shares (account_id, user_id, role)` plutôt que de relâcher l'isolation par défaut
