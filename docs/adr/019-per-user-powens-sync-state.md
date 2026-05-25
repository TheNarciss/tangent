# ADR-019: Per-user Powens sync state

- **Status**: accepted
- **Date**: 2026-05-25
- **Deciders**: Clem
- **Supersedes**: None (initial)

## Contexte

Avant cette ADR, `sync_portfolio()` utilisait **deux variables globales** :

1. `powens_settings.user_token` — champ Pydantic mutable, écrasé à chaque appel de `/sync/powens` par le token décrypté du user qui sync
2. `powens.state` — module singleton stockant `last_sync`, `last_webhook`, `positions_count`, `cash_balance`, `last_error` dans un fichier JSON unique

### Conséquences en multi-user

| Bug | Symptôme |
|---|---|
| Race condition sur `user_token` | Si User A et User B syncent en concurrent, le token global est écrasé → User B peut fetcher les comptes de User A |
| State `powens_state.json` partagé | `/sync/status` retourne le state du **dernier user qui a sync**, peu importe `current_user` |
| Webhook handler appelait `sync_portfolio()` sans user context | Auto-sync via webhook fait avec le token global = du dernier user |

Le code source documente le problème comme `TODO Phase 5 proper: pass token to sync_portfolio(user_id, token) directly` mais n'avait pas été fixé.

## Décision

### 1. `PowensClient(token: str)` — token requis explicite

```python
class PowensClient:
    def __init__(self, token: str) -> None:
        if not token:
            raise PowensError("PowensClient requires a non-empty token")
        ...
```

Plus de lecture de `settings.user_token`. Le caller passe explicitement le token décrypté du user concerné.

### 2. `sync_portfolio(*, token, user_id, session)` — params explicites

```python
async def sync_portfolio(
    *,
    token: str,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> SyncResult: ...
```

Signature avec kwargs-only pour forcer l'appel correct. `user_id` et `session` requis pour update les metadata de sync DB.

### 3. Sync state stocké par-user dans `powens_credentials`

Migration `cb1c9b264dca` ajoute 5 colonnes :

| Colonne | Type | Description |
|---|---|---|
| `last_sync_at` | `DateTime` nullable | Timestamp du dernier sync réussi |
| `last_webhook_at` | `DateTime` nullable | Timestamp du dernier webhook reçu (TODO Phase A) |
| `last_error` | `Text` nullable | Dernier message d'erreur de sync |
| `last_positions_count` | `Integer` NOT NULL default 0 | Nb de positions au dernier sync |
| `last_cash_balance` | `Float` NOT NULL default 0 | Cash au dernier sync |

### 4. `/sync/status` lit depuis DB filtré par `user_id`

```python
@router.get("/sync/status")
async def get_sync_status(user, session):
    cred = (await session.execute(
        select(PowensCredential).where(PowensCredential.user_id == user.id)
    )).scalars().first()
    return {...}  # built from cred.last_*
```

### 5. Webhook handler temporairement désactivé

Le payload Powens contient `id_user` (= user Powens, **pas** user Tangent). Sans mapping `powens_user_id → tangent user_id`, impossible de trigger un sync user-scoped. Le handler log un warning et retourne `status: ignored`.

**TODO Phase A** : ajouter `powens_credentials.powens_user_id` (récupéré via `GET /users/me` lors du token exchange), permettre le mapping, réactiver l'auto-sync via webhook.

### 6. `app/powens/state.py` supprimé

Module deprecated, remplacé par les colonnes DB. Plus aucune référence dans le code.

## Conséquences

### Positives

- **Isolation multi-tenant native** : filtre par `user_id` à chaque query
- **Plus de race condition** : pas de state mutable partagé
- **Source unique de vérité** : la table `powens_credentials`
- **Webhook safe par défaut** : skip silencieux jusqu'à l'ajout du mapping

### Négatives

- **Webhook auto-sync désactivé** jusqu'à Phase A (sync manuel via `POST /sync/powens` uniquement)
- **Migration DB nécessaire** (5 nouvelles colonnes, déjà appliquée en prod et dev)
- **Tests d'intégration manquants** : il faudrait un test `test_sync_isolation_two_users` pour valider qu'un sync de User A n'affecte pas le state de User B (TODO)

## Alternatives considérées

### Option A — Table dédiée `powens_sync_state(user_id, last_sync, ...)`

Une table séparée 1-to-1 avec `powens_credentials`. Écartée car overhead inutile : `powens_credentials` est déjà 1 row par user, autant y mettre les colonnes.

### Option B — Garder le state global, mais en dict `{user_id: state}`

Patch superficiel au lieu d'un fix structurel. Écarté car :
- Pas persisté entre restarts du backend
- Ne suit pas le pattern repository
- Vide naturellement le pattern multi-tenant (state hors DB → faille)

### Option C — Postgres `pg_advisory_lock` pour sérialiser les syncs

Verrouillage avancé au niveau DB. Écarté car les syncs concurrent ne sont PAS un problème (chacun touche son propre user_id), c'est le state global qui posait problème, pas la concurrence elle-même.

## Notes

- À l'avenir, si Tangent intègre d'autres aggregateurs (Bridge, Plaid), appliquer le même pattern : token + user_id + session en params explicites, plus de global
- Le test `test_sync_isolation_two_users` est tracké comme TODO
- La réactivation du webhook handler nécessite `powens_credentials.powens_user_id` (ADR-013 multi-account model devra le prévoir)
