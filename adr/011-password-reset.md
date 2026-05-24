# ADR-011: Flow de reset de mot de passe

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

L'utilisateur doit pouvoir réinitialiser son mot de passe en cas d'oubli, sans assistance. Le flow doit être :
- Sécurisé (résistant aux attaques de bruteforce, énumération, vol de token)
- Compréhensible (UX simple, code court à entrer)
- Self-host friendly (pas de service tiers complexe)
- Compatible avec fastapi-users qui fournit déjà `/auth/forgot-password` et `/auth/reset-password`

Le flow natif fastapi-users envoie un lien magique en email avec un JWT dedans. Limitation : si l'email leak, le compte est compromis. On veut un code court à entrer manuellement pour une étape de vérification supplémentaire.

## Décision

**Flow custom à 3 étapes avec code OTP + JWT court-lived** :

### Étape 1 : `POST /auth/password-reset/request`
- Body : `{"email": "..."}`
- Toujours retourne `204 No Content` (anti-énumération, même si email inconnu)
- Si email existe :
  - Génère code 6 chiffres aléatoire (`secrets.choice("0123456789")` × 6)
  - Hash le code via argon2id (pwdlib)
  - Insert dans `password_reset_tokens` : `(user_id, code_hash, expires_at = now + 15min, attempts = 0, used = false)`
  - Envoie email via Resend avec le code en clair (le seul moment où il est en clair)
- Délai constant côté serveur (~500ms) pour ne pas révéler par timing si l'email existe

### Étape 2 : `POST /auth/password-reset/verify`
- Body : `{"email": "...", "code": "123456"}`
- Trouve le token actif pour cet user (non `used`, non expiré)
- Si `attempts >= 5` → token invalidé, 400
- Vérifie le code via `pwdlib.verify(code, code_hash)`
- Si OK → marque `used = true`, génère un **reset JWT** (lifetime 5 min) signé HS256
- Retour : `{"reset_token": "eyJ..."}`
- Si KO → incrémente `attempts`, 400

### Étape 3 : `POST /auth/password-reset/confirm`
- Body : `{"reset_token": "...", "new_password": "..."}`
- Vérifie signature JWT + non expiré + claims (`type: "password_reset"`, `user_id`)
- Valide la complexité du nouveau mot de passe (longueur 8+ min, etc.)
- Hash le nouveau mot de passe (argon2id) et update `user.hashed_password`
- Invalide tous les tokens reset du user (au cas où)
- Audit log : `AUDIT PASSWORD_RESET_COMPLETED user_id=...`
- Retour `204 No Content`

### Sécurité transverse

| Mesure | Valeur |
|--------|--------|
| Code length | 6 chiffres |
| Code lifetime | 15 min |
| Reset JWT lifetime | 5 min après vérification |
| Max attempts | 5 par token |
| Rate limit `/request` | 3/heure par IP |
| Rate limit `/verify` | 10/heure par IP |
| Rate limit `/confirm` | 5/heure par IP |
| Single use | Token + JWT invalidés après usage |
| Anti-énumération | 204 systématique sur `/request` |
| Timing | Délai constant côté serveur |

## Conséquences

### Positives

- 2 facteurs : accès email + code court
- Si l'email leak, sans accès à l'instance, le code expire en 15min
- Rate limits empêchent le bruteforce
- Audit logs traçent toutes les tentatives

### Négatives

- 3 endpoints custom au lieu de 2 natifs fastapi-users → un peu plus de code à maintenir
- Code 6 chiffres = bruteforce théorique en 10^6 tentatives, mitigé par max 5 attempts + rate limit
- Dépendance Resend pour l'envoi email (mais gratuit jusqu'à 3000/mois)

## Alternatives considérées

### Option A — Flow natif fastapi-users (lien magique)

Plus simple, déjà implémenté dans la lib. Écartée car le lien magique entier dans l'email = vol direct sans étape supplémentaire.

### Option B — Magic link + confirmation code

Lien + code à entrer après. Écartée car UX trop chargée (cliquer ET entrer).

### Option C — TOTP / 2FA obligatoire

Pas de reset par email, juste TOTP. Écartée car friction d'onboarding trop forte et perte du TOTP = compte perdu définitivement.

## Notes

- **Implémenté le 2026-05-22** dans `app/auth/password_reset.py` + `app/routers/password_reset.py`
- **Tester en E2E régulièrement** : login → forgot password → check email → entrer code → nouveau pwd → re-login
- **Email template** dans `app/email/sender.py` — à améliorer en HTML responsive
- **Resend `from`** : `onboarding@resend.dev` en dev mode (envoie uniquement à l'email du compte) — passer à un from custom (`reset@riskybusinesses.uk`) en production
- **Aucun secret** envoyé en clair en DB. Le code est hashed argon2id, comme les mots de passe
