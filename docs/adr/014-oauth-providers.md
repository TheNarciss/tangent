# ADR-014: Authentification OAuth multi-provider (Google d'abord)

- **Status** : proposed
- **Date** : 2026-05-27
- **Deciders** : Clem

## Contexte

ADR-003 a posé l'auth email/password via `fastapi-users`, en laissant explicitement
la porte ouverte à de l'OAuth tiers (« peut être ajouté plus tard sans rupture »).

À ce stade, 10+ users actifs en prod sur https://riskybusinesses.uk ont un compte
email/password. On veut ajouter une authentification OAuth pour :

- Réduire la friction d'inscription (1 clic vs email + password + verify mail)
- Permettre aux users actuels de **lier** un compte tiers à leur compte existant
- Préparer le terrain pour d'autres providers (GitHub, Apple) sans refacto

Contraintes :

- Ne pas casser l'auth email/password existante (10 users en prod).
- Cookie HTTP-only + JWT (ADR-003) reste le seul transport. Aucun token OAuth
  n'est exposé au frontend.
- Chiffrement des tokens OAuth au repos, cohérent avec ADR-012.
- Multi-tenancy stricte (ADR-002) : `oauth_account.user_id` toujours filtré.
- Self-host friendly : pas de SaaS d'identité tiers (Auth0/Clerk), conforme
  ADR-003 alternative B rejetée.

## Décision

### 1. Provider en première vague : Google uniquement

Google est gratuit, ubiquitaire et son OpenID Connect est trivial à intégrer.
L'archi est conçue **multi-provider** dès le départ (table `oauth_account`
générique avec colonne `oauth_name`), mais on n'implémente que Google maintenant.

Apple Sign In est **explicitement reporté** : il requiert un Apple Developer
Program payant ($99/an) et un client_secret JWT signé ES256 à régénérer.
GitHub/Microsoft restent triviaux à ajouter ultérieurement (15 min chacun).

### 2. Librairie : `fastapi-users[oauth]` (extension officielle)

L'extension OAuth de `fastapi-users` (s'appuyant sur `httpx-oauth`) est retenue.
Intégration native avec le `UserManager` et le `CookieTransport` existants. Pas
de stack auth parallèle.

Alternatives écartées :

- `httpx-oauth` direct : faut câbler à la main le set-cookie, le state CSRF, le
  linking par email. Réinvente ce que `fastapi-users[oauth]` fournit.
- `Authlib` (OIDC discovery) : plus puissant pour le multi-provider, mais
  stack parallèle à `fastapi-users`. Pas justifié à ce stade.

### 3. Schéma DB

Nouvelle table `oauth_account`, **one-to-many** `users` → `oauth_account` (un
user peut linker plusieurs providers). Fournie par
`SQLAlchemyBaseOAuthAccountTableUUID`.

| Colonne          | Type                          | Note                                          |
|------------------|-------------------------------|-----------------------------------------------|
| `id`             | UUID PK                       |                                               |
| `user_id`        | UUID FK `users.id` ON DELETE CASCADE | indexé                                  |
| `oauth_name`     | text                          | `"google"` au lancement                       |
| `access_token`   | text (chiffré Fernet)         | via `TypeDecorator` custom                    |
| `expires_at`     | int (Unix ts)                 | nullable                                      |
| `refresh_token`  | text (chiffré Fernet)         | nullable (Google ne le fournit que la 1ère fois) |
| `account_id`     | text                          | `sub` Google (stable, unique par provider)    |
| `account_email`  | text                          | indexé pour lookup linking                    |

Contrainte `UNIQUE(oauth_name, account_id)` pour empêcher qu'un même compte
Google soit linké à 2 users Tangent distincts.

**Modification de `users`** : `hashed_password` devient **nullable**, pour
permettre les users Google-only sans password. Les 10 users existants
conservent leur hash, aucun reset forcé.

### 4. Stratégie de linking : `associate_by_email=True` + check `email_verified` strict

Le défaut de `fastapi-users[oauth]` (`associate_by_email=True`) est **dangereux
en l'état** : si Google renvoie un email non vérifié et qu'un user Tangent
existe avec cet email, le router link automatiquement → vecteur de takeover
trivial.

Mitigation : un **callback custom** intercepte le flow et rejette toute
réponse Google où `email_verified` n'est pas `true`. Audit log
`OAUTH_LINK_REJECTED_UNVERIFIED_EMAIL` enregistré.

Comportements :

| Situation                                           | Résultat                                          |
|-----------------------------------------------------|---------------------------------------------------|
| User non loggé, email Google **vérifié + existant** | Link auto au user existant + login (cookie set)   |
| User non loggé, email Google **vérifié + inconnu**  | Création compte + login                           |
| User non loggé, email Google **non vérifié**        | 400 + audit log, redirect frontend avec erreur    |
| User loggé clique « Lier Google »                   | Router `associate`, link à son user courant       |
| `sub` Google déjà linké à un autre user Tangent     | 409 conflict + audit log                          |

### 5. Chiffrement des tokens : clé Fernet séparée

Nouvelle clé `OAUTH_TOKEN_ENCRYPTION_KEY`, **distincte** de
`POWENS_TOKEN_ENCRYPTION_KEY` (ADR-012). Justification : réduire le blast
radius en cas de compromission d'une clé.

Un `TypeDecorator` SQLAlchemy `EncryptedToken` encapsule le chiffrement :
réutilisable pour tout futur provider OAuth (GitHub, etc.) sans duplication.

Procédure de génération, sauvegarde Bitwarden et rotation : identique à
ADR-012 (Fernet 32 bytes base64url, backup obligatoire en password manager,
perte = re-OAuth forcé pour tous).

### 6. Routers et endpoints

| Path                                       | Méthode | Auth requise | Purpose                                      |
|--------------------------------------------|---------|--------------|----------------------------------------------|
| `/auth/google/authorize`                   | GET     | non          | Retourne l'URL Google à laquelle rediriger   |
| `/auth/google/callback`                    | GET     | non          | Reçoit le code, set cookie, redirect frontend |
| `/auth/associate/google/authorize`         | GET     | oui (cookie) | URL Google pour linking depuis Profile       |
| `/auth/associate/google/callback`          | GET     | oui (cookie) | Lien Google → user déjà loggé                |

**Note implémentation** : callbacks Google sont des **GET** (browser nav après redirect Google), donc le middleware `apply_auth_rate_limits` (POST-only) ne s'applique pas. La sécurité contre brute-force est couverte par (a) le `state` secret HMAC qui empêche le replay et (b) le rate-limit Google côté upstream. Si on veut un rate-limit GET dédié, c'est un ADR séparé.

**Rate limits** ajoutés à `_AUTH_RATE_LIMITS` dans `main.py` :
- `/auth/google/callback` : `(10, 60)`
- `/auth/associate/google/callback` : `(10, 60)`

### 7. CSP

Le header `Content-Security-Policy` (cf `main.py`) est étendu en prod :

- `connect-src` : ajout de `accounts.google.com oauth2.googleapis.com www.googleapis.com`
- `img-src` : ajout de `https://lh3.googleusercontent.com` (avatars Google)

### 8. GCP Setup (Google Cloud Console)

- Project dédié `tangent-prod`
- OAuth consent screen : `External`, scopes `openid email profile`
- OAuth 2.0 Client ID type `Web application`
- Authorized JavaScript origins :
  - `https://riskybusinesses.uk`
  - `http://localhost:5173` (dev frontend)
- Authorized redirect URIs (côté **backend**) :
  - `https://riskybusinesses.uk/auth/google/callback`
  - `https://riskybusinesses.uk/auth/associate/google/callback`
  - `http://localhost:8000/auth/google/callback`
  - `http://localhost:8000/auth/associate/google/callback`
- Client ID + Client Secret → `.env` : `GOOGLE_OAUTH_CLIENT_ID`,
  `GOOGLE_OAUTH_CLIENT_SECRET`. Jamais commit.

### 9. Audit events à émettre

- `OAUTH_LOGIN_SUCCESS` (oauth_name, user_id, ip)
- `OAUTH_REGISTER` (oauth_name, user_id, account_email)
- `OAUTH_LINK_SUCCESS` (oauth_name, user_id, account_email)
- `OAUTH_LINK_REJECTED_UNVERIFIED_EMAIL` (oauth_name, account_email tenté, ip)
- `OAUTH_LINK_REJECTED_CONFLICT` (oauth_name, account_id déjà pris)
- `OAUTH_ACCOUNT_DELETED` (user_id, oauth_name)

## Conséquences

### Positives

- Onboarding 1-clic via Google → friction d'inscription quasi nulle
- Users existants conservent leur password ET peuvent ajouter Google en
  parallèle (les deux modes coexistent)
- Archi extensible à GitHub/Microsoft/Apple sans refacto : il suffit
  d'instancier un nouveau client `httpx-oauth` et de monter les routers
- Tokens OAuth chiffrés au repos (cohérent avec ADR-012, principe étendu)
- Aucune dépendance à un SaaS d'identité tiers, conforme à l'esprit self-host
  de ADR-003 et ADR-005

### Négatives

- Surface d'attaque élargie (deux modes d'auth = deux vecteurs)
- Dépendance opérationnelle à Google : si OAuth Google down → bouton Google
  cassé, mais email/password fonctionne toujours (pas de single point of
  failure pour l'auth en général)
- Une clé Fernet supplémentaire à gérer (rotation, backup Bitwarden)
- Linking par email = vecteur de takeover si `email_verified` non checké →
  mitigé par check strict + audit log
- Les users Google-only n'ont pas de password : s'ils perdent l'accès à leur
  Google, ils sont coincés. Mitigation prévue dans un ADR suivant : permettre
  de **définir un password** depuis Profile en post-onboarding.

## Alternatives considérées

### Option A — `httpx-oauth` direct sans `fastapi-users[oauth]`

Plus de contrôle bas niveau. Écartée car il faudrait câbler manuellement le
set-cookie via `auth_backend.transport`, le state CSRF, le linking par email,
la gestion `email_verified`. Réinvente ce que `fastapi-users[oauth]` fournit
nativement, sans bénéfice fonctionnel.

### Option B — `Authlib` (avec OIDC discovery)

Très puissant pour le multi-provider via discovery automatique des endpoints.
Écartée car introduit une stack d'auth parallèle à `fastapi-users`, alors que
ce dernier suffit largement à notre scale.

### Option C — Magic link email au lieu d'OAuth

Plus simple côté infra (juste un email). Écartée car UX inférieure à un
bouton 1-clic Google pour la cible (mobile-first). À garder en backup si
Google nous lâche un jour.

### Option D — Forcer tous les users existants à passer à Google

Cohérent avec un futur sans password, mais hostile aux 10 users actuels.
Rejetée.

### Option E — Inclure Apple Sign In dès maintenant

Apple Sign In requiert un Apple Developer Program payant ($99/an) + un
client_secret JWT signé ES256 à régénérer. Coût + complexité non justifiés
tant qu'on n'a pas de demande utilisateur explicite. Reporté à un ADR
ultérieur si besoin.

## Notes

### Plan d'exécution

1. GCP setup (consent screen + OAuth Client ID + redirect URIs dev+prod)
2. Backend : dépendance `fastapi-users[oauth]` + settings + clé Fernet
3. Backend : modèle `OAuthAccount`, `TypeDecorator EncryptedToken`,
   `User.hashed_password` nullable
4. Migration Alembic : table `oauth_account` + `ALTER COLUMN users.hashed_password DROP NOT NULL`
5. Backend : routers OAuth + callback custom `email_verified`
6. Backend : tests (mock OAuth, link verified OK, link unverified REJECT,
   multi-tenant isolation, existing user can still login email/password)
7. Frontend : bouton "Continue with Google" sur AuthScreen + page callback
8. Frontend (PR suivante recommandée) : bouton "Lier Google" dans Profile
9. CSP/Caddy : update headers

### Tests obligatoires avant prod

- Login Google → cookie `tangent_auth` set + redirect frontend OK
- Linking par email vérifié → success
- Linking par email **non vérifié** → 400 + audit log présent
- Login email/password d'un user prod existant → toujours OK (test
  d'intégration explicite avec un fixture user avec `hashed_password` set)
- Suppression d'un `oauth_account` ne supprime pas le user (FK cascade
  inverse seulement : delete user → delete oauth_account, pas l'inverse)
- Multi-tenant : user A ne peut pas voir/modifier `oauth_account` de user B

### Rollback plan

Si bug bloquant détecté en prod après deploy :

1. Commenter les `include_router` OAuth dans `main.py`
2. Redeploy backend
3. La table `oauth_account` reste en base, inutilisée → pas de migration
   `down` nécessaire
4. Les users Google-only existants (s'il y en a déjà eu) restent coincés
   tant que les routers sont down → motivation supplémentaire pour itérer
   l'ADR « set password from Profile »

### Phase suivante (hors scope ADR-014)

- ADR à venir : permettre aux users Google-only de **définir un password**
  depuis Profile, pour ne pas être totalement dépendant du provider tiers
- Évaluation d'un 2e provider (GitHub d'abord, Apple seulement si compte
  Developer souscrit)
