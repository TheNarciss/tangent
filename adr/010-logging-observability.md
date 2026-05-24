# ADR-010: Logging et observabilité

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

L'application doit pouvoir être diagnostiquée à distance en cas de problème, sans intervention manuelle continue. Surveiller la santé des services, détecter les erreurs, comprendre les incidents.

Contraintes :
- Self-host = pas d'outil entreprise type Datadog
- Budget zéro / quasi-zéro
- Logs sensibles (données financières) = ne pas envoyer aveuglément à un SaaS US

## Décision

**Stack d'observabilité minimaliste mais structurée** :

### Logs

- **Lib** : `structlog` côté backend, formatage JSON en production, console human-readable en dev
- **Niveau par défaut** : INFO, WARN, ERROR. DEBUG uniquement en local
- **Format JSON** avec champs standardisés :
  ```json
  {
    "timestamp": "2026-05-23T13:20:42Z",
    "level": "info",
    "logger": "app.finance.optimizer",
    "message": "optimizer ran",
    "user_id": "b5a7b94a-...",
    "duration_ms": 1061,
    "objective": "max_sharpe"
  }
  ```
- **Pas de PII dans les logs** : pas d'email, pas de noms, pas de montants exacts (juste user_id UUID)
- **Audit log dédié** : table DB `audit_log` pour les événements critiques (login, password change, sync triggered, etc.) — survit au log rotation

### Erreurs (Sentry)

- **Sentry** free tier (5K events/mois) côté backend et frontend
- **DSN** dans `.env`, désactivé si pas configuré
- **Filtrage PII** : `before_send` hook qui retire les emails, mots de passe, tokens
- **Sample rate** : 100% des erreurs, 10% des traces de perf

### Healthcheck

- Endpoint `/health` qui vérifie :
  - DB accessible (`SELECT 1`)
  - (à venir) Powens API accessible
  - (à venir) Resend API accessible
- Retour JSON `{"status": "ok|degraded|down", "db": "up|down", ...}`
- Utilisé par Docker `healthcheck` et monitoring externe (UptimeRobot, Healthchecks.io free tier)

### Metrics (Phase D, pas avant)

- `prometheus-fastapi-instrumentator` exposé sur `/metrics`
- Scrapé par Grafana Cloud free tier OU un mini Prometheus self-host
- Métriques clés : latence par endpoint, taux d'erreur, requests/sec, taille du job de sync Powens

### Frontend logs

- Console logs en dev uniquement (stripper en prod via Vite)
- Sentry capture les erreurs JS non-catchées + les promesses rejetées
- Pas de tracking analytics au démarrage (peut-être Plausible en Phase D)

## Conséquences

### Positives

- Logs JSON exploitables par grep, jq, ou ingérables dans n'importe quel système plus tard
- Sentry capture les erreurs sans surveillance manuelle
- Stack légère, faible coût mental
- Audit log = traçabilité légale (GDPR, conformité)

### Négatives

- Pas de dashboards out-of-the-box → si besoin, ajouter Grafana plus tard
- Sentry = SaaS US → données envoyées hors EU pour les stack traces (mitigé par before_send hook qui retire la PII)
- Logs locaux non centralisés → grep dans les containers Docker

## Alternatives considérées

### Option A — Datadog / New Relic

Tout-en-un. Écartée car coût (€100+/mois minimum sérieux) et overkill.

### Option B — ELK Stack (Elasticsearch, Logstash, Kibana)

Open source, puissant. Écartée car gourmand en RAM (1GB+ par service) et complexité d'opération vs valeur pour 1 instance.

### Option C — Loki + Grafana

Plus léger qu'ELK. À considérer en Phase D si besoin de logs centralisés.

### Option D — Pas de logs structurés, juste `print`

Le néant. Écartée car débogage à distance impossible et zéro audit.

## Notes

- **Anti-pattern à éviter** : logger des `Exception` sans contexte → toujours `logger.exception("operation_failed", user_id=user.id, op="sync_portfolio")`
- **À implémenter en Phase 0** :
  - Migration des `logging.getLogger(__name__).info(...)` actuels vers `structlog`
  - Configuration `structlog` dans `app/logging_config.py`
  - Intégration Sentry backend + frontend
  - Table `audit_log` avec migration Alembic
- **Procédure post-incident** : prochaine session post-bug = checklist 1. Log Sentry, 2. Reproduit en local, 3. Test ajouté, 4. Fix, 5. Deploy, 6. Vérif logs
