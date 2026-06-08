# ADR-020 - Tous les endpoints backend sous le namespace /api/*

- Status: Accepted
- Date: 2026-06-08
- Deciders: @TheNarciss

## Contexte

Le Caddyfile maintenait une allowlist hardcodee des prefixes de routes
backend a reverse-proxy. A chaque ajout d'un nouveau router backend, il
fallait penser a ajouter son prefixe dans le Caddyfile. Sinon les requetes
tombaient sur le file_server SPA -> 405 Method Not Allowed en prod.

Le bug s'est produit 3 fois historiquement (derniere: PR #52 sur /reviews/*).

## Decision

Tous les endpoints backend sont namespaced sous /api/*, y compris les
callbacks OAuth et webhooks externes. Le Caddyfile matche desormais
une seule regle:

    @api { path /api/* }

## Implementation

### Backend (backend/app/main.py)
- Tous les `app.include_router(...)` business: ajout de `prefix="/api"`
- fastapi-users routers: `prefix="/api/auth"`, `prefix="/api/users"`
- OAuth routers: `prefix="/api/auth/google"`, `prefix="/api/auth/associate/google"`
- `@app.get("/health")` -> `@app.get("/api/health")`
- Exemptions CSP (callbacks Google): paths mis a jour avec `/api/...`

### Frontend (frontend/src/api.ts)
Une seule ligne touchee: le fallback `API_URL` inclut `/api`.
Le helper `http(path)` propage le prefix a tous les fetch.

### Build
- `Dockerfile.caddy`: `ENV VITE_API_URL=https://riskybusinesses.uk/api`
- `backend/Dockerfile`: `HEALTHCHECK` curl sur `/api/health`

### Migration zero downtime des callbacks externes
Sur Google Cloud Console et Powens dashboard, les nouveaux redirect URIs
(`/api/auth/google/callback`, etc.) sont ajoutes a cote des anciens
pendant la phase de transition. Une fois la prod deployee et validee,
les anciens URIs sont supprimes.

## Consequences

### Positives
- Plus jamais le trap "ajouter route -> oublier Caddy"
- Caddyfile minimal: UNE regle stable, plus de maintenance
- Convention claire: separe visuellement l'API de la SPA
- Permet `/api/docs` Swagger distinct de la SPA si besoin un jour

### Negatives
- Migration coordonnee requise sur les configs OAuth externes
- Tests integration ont du etre mis a jour (~50 paths re-prefixes auto)

## Alternatives considerees

### A - Garder l'allowlist Caddyfile
Statu quo. Rejete: le bug se reproduira.

### B - /api/* avec exceptions explicites pour les callbacks externes
Rejete au profit du strict /api/* pour la proprete long-terme.

### C - Alias de retro-compatibilite cote backend
Rejete: code mort a supprimer ensuite, complexifie pour rien.

## Exceptions au strict /api/*

### Powens (OAuth sandbox limitation)

Les routes Powens restent sur leur ancien chemin (sans prefix `/api`):
- `/auth/powens/initiate` (GET, build webview URL)
- `/auth/powens/callback` (GET, OAuth return)
- `/webhooks/powens` (POST, currently disabled per ADR-019)

**Raison**: le dashboard Powens sandbox accepte **une seule** redirect URI
configurable. On ne peut donc pas faire de migration "dual URI" comme avec
Google OAuth. Forcer le changement vers `/api/auth/powens/callback` exigerait
un downtime synchronisé entre le dashboard Powens et le deploy CD, ce qui
n'est pas tenable proprement.

Caddyfile autorise ces 2-3 paths explicites en plus de `/api/*`:

    @api {
        path /api/*
        path /auth/powens/*
        path /webhooks/powens
    }

Cette exception est **bornee a Powens uniquement** et **documentee dans le
Caddyfile**.

**Implementation cote backend**: `backend/app/routers/powens.py` definit
DEUX routers:
- `legacy_router` (sans prefix `/api`): `/auth/powens/initiate`,
  `/auth/powens/callback`, `/webhooks/powens` — routes appelees par Powens
  ou par leur dashboard config
- `router` (sous `/api` via include_router): `/sync/*` — routes appelees
  par notre frontend uniquement, namespace normal Quand on passera en compte Powens production (qui supporte des
multi-URI), on migrera proprement vers `/api/auth/powens/*` dans une PR
dediee.

Cote frontend, le call `getPowensWebviewUrl()` utilise `BACKEND_BASE`
(= API_URL sans `/api`) au lieu du helper `http()` qui prefix automatique-
ment avec `/api`.

## Notes operationnelles

### Lors de la phase de transition (J0)
1. Ajouter `/api/auth/google/callback` et `/api/auth/associate/google/callback`
   dans Google Cloud Console (sans retirer les anciens)
2. Ajouter `/api/auth/powens/callback` dans Powens dashboard (sans retirer l'ancien)
3. Merge -> CD deploy -> prod
4. Tester login Google + sync Powens en prod
5. Supprimer les anciens URIs dans Google + Powens

### Future
- Webhook Powens (desactive par ADR-019): sera re-expose sous
  `/api/webhooks/powens` lors de sa reactivation Phase A.
- Tout nouveau provider OAuth sera naturellement sous `/api/auth/<provider>/...`
  sans modification du Caddyfile.
