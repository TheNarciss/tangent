# Rapport de diagnostic complet — Tangent

Date: 2026-06-08  
Périmètre: backend + frontend (revue statique du code)

## Résumé exécutif

Le socle est globalement solide (isolation multi-tenant bien présente dans les repos, chiffrement des tokens Powens/OAuth, CI sécurité existante).  
Cependant, plusieurs points bloquants empêchent d’atteindre une « perfection absolue » aujourd’hui, surtout côté sécurité opérationnelle (secrets/reset), robustesse (rate limiting), et rigueur technique (dette frontend).

## Constats priorisés

## 🔴 Critique

### 1) Secret de reset password potentiellement vide (signature JWT faible)
- **Preuve**: `backend/app/auth/password_reset.py:42`
- `RESET_TOKEN_SECRET = os.getenv("RESET_TOKEN_SECRET", "")`
- Impact: si la variable n’est pas configurée, les tokens de reset sont signés avec une clé vide (`""`), ce qui est une faiblesse majeure.
- Recommandation:
  - Bloquer le démarrage si `RESET_TOKEN_SECRET` absent/placeholder (comme déjà fait pour `JWT_SECRET`).
  - Ajouter `RESET_TOKEN_SECRET` à `.env.example` avec placeholder explicite.

## 🟠 Élevé

### 2) Logs de reset password exposent l’existence d’un compte (PII + enumération via logs)
- **Preuves**:
  - `backend/app/routers/password_reset.py:42`
  - `backend/app/routers/password_reset.py:54`
  - `backend/app/routers/password_reset.py:56`
- Le log contient `email=...` et surtout `existed={True|False}`.
- Impact: fuite d’information sensible dans les journaux; utile pour attaque d’énumération si accès logs.
- Recommandation:
  - Retirer `existed` des logs.
  - Hacher/tronquer l’email en audit (ou utiliser un user_id si connu).
  - Uniformiser les événements d’échec/succès sans révélation d’état utilisateur.

### 3) Rate limiting auth en mémoire locale (contournable en multi-instance + risque mémoire)
- **Preuve**: `backend/app/main.py:82` et logique middleware `main.py:85-112`
- Le stockage des tentatives est un dictionnaire process-local (`_attempts`) sans stratégie globale distribuée.
- Impact:
  - Bypass facile derrière plusieurs instances/pods.
  - Croissance potentielle de la map (IP/route), donc surface DoS mémoire.
- Recommandation:
  - Migrer vers Redis/shared store (ou rate limit en reverse-proxy).
  - Ajouter TTL/garbage collection des clés inactives.

## 🟡 Moyen

### 4) Suppression de cookie hardcodée (nom + secure)
- **Preuve**: `backend/app/routers/account.py:189`
- `delete_cookie(key="tangent_auth", ..., secure=True)` ignore la config runtime (`COOKIE_NAME`, `COOKIE_SECURE`).
- Impact: risque de logout incomplet selon environnement/config.
- Recommandation:
  - Réutiliser la config centralisée d’auth backend (nom cookie + secure + samesite cohérents).

### 5) CSP permissive avec `unsafe-inline`
- **Preuve**: `backend/app/main.py:184-187`
- `script-src 'self' 'unsafe-inline'` et `style-src ... 'unsafe-inline'`.
- Impact: affaiblit significativement la protection XSS.
- Recommandation:
  - Passer à CSP nonce/hash-based.
  - Éliminer progressivement les scripts/styles inline.

### 6) Erreurs d’initialisation DB avalées au démarrage
- **Preuve**: `backend/app/main.py:54-57`
- En cas d’échec migrations/init DB, l’app continue quand même à démarrer.
- Impact: service démarré dans un état partiellement cassé (erreurs runtime plus tardives).
- Recommandation:
  - Faire échouer le démarrage si `init_db()` échoue (fail-fast).

### 7) Webhooks Powens désactivés (dette fonctionnelle explicite)
- **Preuve**: `backend/app/powens/webhooks.py:22-42`
- Handler volontairement désactivé tant que mapping `powens_user_id -> user_id` n’est pas implémenté.
- Impact: dépendance accrue au refresh manuel; fraîcheur des données dégradée.
- Recommandation:
  - Prioriser la phase A indiquée (mapping per-user) puis réactiver webhook de manière sûre.

## 🔵 Faible / Rigueur

### 8) Dette frontend dans `api.ts` (duplication de types + commentaire de remplacement laissé)
- **Preuves**:
  - `frontend/src/api.ts:629` (commentaire “Replace the existing ...”)
  - `frontend/src/api.ts:699` et `frontend/src/api.ts:827` (`BankAccountResponse` défini 2 fois)
- Impact: maintenance fragile, risque d’incohérences silencieuses via fusion d’interfaces TypeScript.
- Recommandation:
  - Nettoyer les doublons et ne garder qu’une définition canonique par type.

## Points positifs notables

- Isolation multi-tenant bien appliquée sur les repositories clés (`user_id` systématique).
- Chiffrement des tokens sensibles (Powens/OAuth) présent.
- CI structurée: lint/typecheck/tests + scans sécurité + audit dépendances.
- Présence d’ADR et documentation d’architecture, utile pour la traçabilité.

## Plan d’action recommandé (ordre)

1. Corriger immédiatement la gestion de `RESET_TOKEN_SECRET` (fail-fast + env template).  
2. Assainir les logs du flux password reset (retirer `existed`, minimiser PII).  
3. Remplacer le rate limiter in-memory par un mécanisme distribué.  
4. Corriger la suppression de cookie (config centralisée).  
5. Durcir CSP (sortie de `unsafe-inline`).  
6. Passer `init_db` en fail-fast au startup.  
7. Réactiver webhooks Powens après implémentation du mapping per-user.  
8. Nettoyer la dette `frontend/src/api.ts`.

---

Si tu veux, je peux enchaîner directement avec un **plan de remédiation lot par lot** (PR1 sécurité critique, PR2 robustesse, PR3 dette technique), puis l’implémenter.
