# ADR-006: Persistence et backups

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Tangent stocke des données critiques :
- Identifiants utilisateurs et hashes de mots de passe
- Positions, transactions, profils financiers
- Tokens Powens chiffrés
- Historique d'audit

Une perte de données = perte de confiance utilisateur définitive. Une fuite = problème légal et éthique majeur.

Contraintes :
- Self-host sur Mac (pas de RAID, pas de SAN)
- Budget faible
- Restore Time Objective (RTO) acceptable : < 24h
- Recovery Point Objective (RPO) acceptable : ≤ 24h de perte

## Décision

**Base de données** : PostgreSQL 16 dans un container Docker, volume nommé `postgres_data` persistant sur le disque local.

**Connection** : SQLAlchemy 2.0 async avec asyncpg.

**Migrations** : Alembic à partir de la Phase 0 (aujourd'hui `create_all` au boot — **deprecated**, migration prévue).

**Conventions schéma** :
- UUID v4 pour IDs (pas BigInt auto-increment pour éviter enumeration attacks)
- Colonnes audit `created_at`, `updated_at` sur toutes les tables (via Mixin)
- Soft delete (`deleted_at` nullable) plutôt que hard delete sauf cas conformité GDPR
- Indexes sur toutes les FK + colonnes filtrées
- FK avec `ON DELETE CASCADE` quand la relation est de composition

**Backups** :
1. **Quotidien** : `pg_dump` à 03h00, compressé gzip, upload vers Backblaze B2 (10GB gratuit)
2. **Rétention** : 30 jours sur B2, 7 jours en local `/tmp`
3. **Test de restore** : trimestriel, sur DB temporaire, validation manuelle
4. **Volume Docker** : NON considéré comme un backup, juste le runtime

**Sécurité backups** :
- Chiffrement at-rest côté B2 (par défaut chez B2)
- Clés B2 dans `.env` (rotation annuelle)
- Backup contient des données sensibles → traiter les fichiers comme top secret

## Conséquences

### Positives

- Setup simple, tout dans Docker
- B2 = 10GB gratuit, ~80% moins cher que S3 pour le retain long terme
- pg_dump = format texte, restore facile sur n'importe quelle Postgres
- Volume Docker survit aux restarts containers

### Négatives

- Single disk = aucune redondance physique (un SSD défectueux = perte si pas de backup à jour)
- pg_dump = lock léger pendant l'export, peut être lent sur grosse DB (pas un problème à notre scale)
- Pas de point-in-time recovery (WAL archiving requis pour ça)

## Alternatives considérées

### Option A — SQLite

Plus simple, fichier unique. Écartée car concurrence d'écriture limitée et écosystème async moins mature.

### Option B — Postgres managé (Supabase, Neon)

Backups auto, replicas, scale. Écartée car coût et lock-in.

### Option C — Backup via réplication streaming

Replica Postgres en lecture seule sur un VPS distant. Excellent pour DR mais ajoute complexité (WAL, hot standby). À considérer si plus de 10 users actifs.

## Notes

- **Premier backup à mettre en place** dès Phase 0 — c'est non-négociable
- **Procédure de restore documentée** : `docs/runbooks/restore-db.md` (à créer)
- **Test de restore réussi le** : à effectuer après mise en place
- **Volumes Docker actuels** : `postgres_data`, `caddy_data`, `caddy_config` — tous nommés (pas anonymes)
- **GDPR** : un user qui demande suppression → endpoint `DELETE /users/me` qui supprime via CASCADE toutes ses données + supprime le compte chez Powens via API
- **Idée future** : exposer un endpoint `GET /export/data` qui produit un JSON+CSV avec toutes les données du user (droit à la portabilité GDPR)
