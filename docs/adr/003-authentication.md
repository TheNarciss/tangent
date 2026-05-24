# ADR-003: Authentification utilisateur

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Tangent contient des données financières sensibles. L'authentification doit être :
- Résistante (hash de mot de passe moderne, pas de stockage en clair)
- Standard (pas d'invention crypto maison)
- Compatible cookie-based pour un OAuth callback Powens qui revient sur le frontend (sinon tokens en URL = mauvaise pratique)
- Self-host friendly (pas d'OAuth tiers obligatoire)

## Décision

**fastapi-users** comme librairie d'auth, configurée avec :

- **Hash** : argon2id via `pwdlib` (la lib moderne qui remplace `passlib`)
- **Transport** : cookies HTTP-only, `Secure` en prod, `SameSite=Lax`
- **Stratégie** : JWT signé HS256, lifetime 7 jours hard cap
- **Cookie max-age** : `None` (session-only, supprimé à la fermeture du browser)
- **Endpoints** : `/auth/login`, `/auth/logout`, `/auth/register`, `/users/me`
- **Password reset** : flow custom (voir ADR-011) car le natif fastapi-users ne s'adapte pas à notre UX

Pas d'OAuth tiers (Google, GitHub) au démarrage — peut être ajouté plus tard sans rupture.

## Conséquences

### Positives

- Librairie maintenue, vetted par la communauté
- Argon2id = state of the art en hash de mot de passe
- Cookies HTTP-only = pas accessibles en JS donc pas vol par XSS
- `SameSite=Lax` = cookies envoyés lors du retour OAuth Powens (top-level navigation)
- Session-only = pas de "remember me" implicite = bonne hygiène de sécu

### Négatives

- Cookie-based = besoin de gérer CSRF sur les POST/PUT/DELETE (à ajouter en Phase 0)
- Pas de "remember me" 30 jours par défaut = friction user mineure
- fastapi-users impose certaines conventions (table `user` notamment)

## Alternatives considérées

### Option A — JWT en localStorage

Plus simple côté frontend, pas de CSRF à gérer. Écartée car XSS = vol du token, et impossible de marquer "HTTP-only".

### Option B — Auth0 / Clerk

SaaS, fonctionne très bien. Écartée car coûts + vendor lock-in + complexité de self-host.

### Option C — Stack maison auth

Contrôle total. Écartée car risque de bugs cryptographiques (timing attack, etc.). On ne réinvente pas l'auth.

## Notes

- Rate limit obligatoire sur `/auth/login`, `/auth/register`, `/auth/password-reset/*` (cf ADR-011)
- Logger les events `AUTH_LOGIN_SUCCESS`, `AUTH_LOGIN_FAILED`, `AUTH_LOGOUT`, `AUTH_PASSWORD_CHANGED` dans la table `audit_log` (à créer en Phase 0)
- À l'avenir : ajouter 2FA TOTP (cf Roadmap Phase D)
- Le secret JWT a été régénéré le 2026-05-22 via `secrets.token_urlsafe(48)` et est dans `.env`
