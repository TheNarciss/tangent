# ADR-004: Gestion des secrets

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

L'application manipule plusieurs secrets sensibles :
- JWT signing key
- Database password
- Powens client_id / client_secret
- Powens webhook secret (HMAC)
- Fernet key pour chiffrer les tokens Powens en DB
- Resend API key
- Password reset signing key

Ces secrets ne doivent jamais :
- Être commités dans Git
- Apparaître dans les logs
- Être visibles côté frontend
- Être stockés en clair en DB (sauf hash)

Le projet est self-host à une seule instance — pas besoin de Vault / Secrets Manager cloud.

## Décision

**Niveaux de stockage des secrets** :

| Type | Stockage | Outil |
|------|----------|-------|
| Config statique | Fichier `.env` à la racine de `backend/` | python-dotenv via pydantic-settings |
| Secrets chiffrés en DB (tokens Powens) | Colonne `bytea`, chiffrée Fernet | cryptography lib |
| Hashes de mots de passe | Colonne `text` | argon2id via pwdlib |
| Codes de reset (6 chiffres) | Colonne `text`, hashée argon2id | pwdlib |

**Règles** :

1. `.env` est dans `.gitignore` (déjà fait)
2. `.env.example` commité avec valeurs factices comme documentation
3. Tous les secrets sont chargés via `pydantic-settings` typé (pas de `os.getenv()` direct éparpillé)
4. Les logs ne loggent jamais un secret — utiliser `***` ou un structlog processor qui filtre
5. La Fernet key est elle-même un secret → en `.env`, jamais en DB
6. En prod, secrets via env vars du container (docker-compose.prod.yml `environment:` block) qui override `.env`
7. Rotation de tous les secrets après un soupçon de fuite (procédure documentée à écrire)

## Conséquences

### Positives

- Simple, sans dépendance externe
- Compatible Docker Compose et 12-factor app
- Pas de Vault / KMS coût ou complexité
- Pydantic-settings = validation + typage des secrets au boot

### Négatives

- Pas de rotation automatique (manuelle, documentée)
- Si la machine est compromise, le `.env` l'est aussi (mais c'est vrai partout)
- Pas d'audit log des accès aux secrets

## Alternatives considérées

### Option A — HashiCorp Vault

Industrial-grade. Écartée car overkill pour 1 instance self-host.

### Option B — AWS Secrets Manager / Doppler

SaaS. Écartée pour rester self-host friendly + coût + lock-in.

### Option C — Encrypted git-crypt

Secrets dans Git mais chiffrés. Écartée car friction (déchiffrement avant chaque deploy) et risque de leak si la clé GPG fuit.

## Notes

- **Procédure de rotation** (à formaliser) : pour chaque secret, documenter dans un fichier `docs/runbooks/rotate-secrets.md` la commande de génération et les services à redémarrer
- **Backup de la Fernet key** : la stocker dans un password manager personnel (Bitwarden / 1Password) en plus du `.env`. Si elle est perdue, tous les tokens Powens chiffrés en DB sont irrécupérables → re-OAuth obligatoire
- **Procédure post-incident** : si un secret leak, le régénérer immédiatement, puis re-deploy. Procédure suivie le 2026-05-22 après partage accidentel
