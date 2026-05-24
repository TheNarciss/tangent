# ADR-012: Chiffrement des tokens au repos

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

L'application stocke en base de données des tokens OAuth Powens (et potentiellement d'autres aggregateurs à l'avenir). Ces tokens permettent d'accéder à toutes les données bancaires d'un utilisateur sans authentification supplémentaire.

Si la DB leak ou est accédée par un acteur malveillant, ces tokens représentent un risque catastrophique : compromission de tous les comptes bancaires des users.

Il faut donc les chiffrer **au repos** (encryption at rest), avec une clé qui n'est pas dans la DB elle-même.

## Décision

**Chiffrement Fernet (AES-128-CBC + HMAC-SHA256)** des tokens OAuth en base, clé stockée dans `.env`.

### Implémentation

```python
# app/powens/crypto.py
from cryptography.fernet import Fernet

_fernet = Fernet(settings.powens_token_encryption_key)  # 32 bytes base64

def encrypt_token(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())

def decrypt_token(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode()
```

### Stockage DB

Table `powens_credentials` :
- `user_id` UUID FK
- `encrypted_token` BYTEA (binaire chiffré)
- `created_at`, `updated_at`

Aucune colonne en clair.

### Génération et rotation de la clé

- Clé générée via `Fernet.generate_key()` = 32 random bytes encodés base64url
- Stockée dans `.env` sous `POWENS_TOKEN_ENCRYPTION_KEY=...`
- **Sauvegardée en plus** dans un password manager personnel (Bitwarden, 1Password) — c'est critique
- Rotation possible mais requiert :
  1. Décrypter tous les tokens avec l'ancienne clé
  2. Re-encrypter avec la nouvelle
  3. Mettre à jour la clé en `.env`
  4. Restart backend
- En cas de **perte de la clé** : tous les tokens chiffrés sont irrécupérables → vidage de `powens_credentials` + re-OAuth obligatoire pour tous les users (procédure validée le 2026-05-22)

## Conséquences

### Positives

- Si la DB leak, les tokens sont inexploitables sans la clé Fernet
- AES-128 + HMAC-SHA256 = standards éprouvés (pas de crypto maison)
- `cryptography` lib = vetted, maintenue
- Performance OK pour notre volume (< 1ms par décryption)

### Négatives

- La clé est dans `.env` → si la machine entière est compromise, les tokens le sont aussi (mais c'est le cas pour tous les secrets)
- Perte de la clé = données token perdues (mitigation : backup en password manager)
- Pas de KMS / HSM (overkill pour notre scale)

## Alternatives considérées

### Option A — Stocker les tokens en clair

Simple. Écartée car risque catastrophique en cas de fuite DB.

### Option B — Postgres `pgcrypto` extension

Chiffrement au niveau DB via fonctions SQL. Écartée car la clé doit être passée à chaque query (complexité applicative) et moins flexible que Fernet côté code.

### Option C — AWS KMS / GCP KMS

KMS managé, rotation automatique. Écartée car coût et dépendance cloud → conflit avec ADR-005 self-host.

### Option D — Tokens stockés ailleurs (Vault, etc.)

Externalisation totale. Écartée par complexité opérationnelle.

## Notes

- **Anti-pattern à éviter** : logger un token décrypté → tout log doit utiliser `***` ou ne pas inclure la valeur
- **Rotation manuelle** : à formaliser dans `docs/runbooks/rotate-fernet-key.md`
- **Procédure d'urgence** : si soupçon de compromission de la clé :
  1. Générer nouvelle clé immédiatement
  2. Suspendre tous les sync Powens (kill switch dans `.env` à ajouter)
  3. Notifier les users (par email) du re-OAuth nécessaire
  4. Update `.env` avec nouvelle clé + restart
  5. Vidage table `powens_credentials` (les tokens chiffrés avec l'ancienne clé sont morts)
  6. Re-OAuth de chacun
- **Audit log** : chaque chiffrement/déchiffrement de token devrait être loggé en metadata (`AUDIT TOKEN_DECRYPTED user_id=... op=sync`)
- **À étendre en Phase A** : appliquer le même pattern aux tokens d'autres aggregateurs (Bridge, etc.) si introduits
