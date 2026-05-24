# ADR-009: Structure du repository

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Le projet contient deux sous-applications fortement couplées (frontend + backend) plus de la configuration de déploiement. Il faut décider entre monorepo, polyrepo, ou multi-package.

Contraintes :
- Un seul développeur principal
- Backend et frontend évoluent souvent ensemble (changement d'API = changement de hook)
- Déploiement via Docker Compose unique
- Pas de package npm à publier

## Décision

**Monorepo simple** à la racine du repo, avec séparation claire des dossiers :

```
tangent/
├── backend/                    # FastAPI app
│   ├── app/
│   │   ├── auth/
│   │   ├── db/
│   │   ├── finance/           # logique métier (optim, projection, analytics)
│   │   ├── powens/
│   │   ├── repositories/      # accès DB par concept
│   │   ├── routers/           # endpoints HTTP groupés par feature
│   │   ├── email/
│   │   └── main.py
│   ├── tests/
│   ├── alembic/                # à créer en Phase 0
│   ├── config/                 # YAML de config (brokers, envelopes, cma, powens)
│   ├── data/                   # data files (à éviter, préférer DB)
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env                    # gitignored
│
├── frontend/                   # Vite + React app
│   ├── src/
│   │   ├── components/         # composants UI par feature
│   │   ├── lib/                # utils, format, chart helpers
│   │   ├── api.ts              # hooks React Query centralisés
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docs/                       # documentation maintenue
│   ├── adr/                    # Architecture Decision Records
│   ├── runbooks/               # procédures opérationnelles
│   └── ROADMAP_PATRIMOINE_360.md
│
├── docker-compose.yml          # config dev par défaut
├── docker-compose.prod.yml     # overrides production
├── Caddyfile                   # reverse proxy
├── .github/workflows/          # CI à créer en Phase 0
├── .gitignore
├── README.md
└── CHANGELOG.md
```

**Conventions** :

1. **Backend organisé par feature** dans `routers/` et `repositories/`, pas par couche technique
2. **Logique métier** dans `app/finance/` reste **agnostique du framework** (testable sans FastAPI)
3. **Repositories** = couche d'accès DB pure, prend `AsyncSession` en paramètre, retourne ORM models
4. **Routers** = couche HTTP, dépend des repositories, gère validation Pydantic
5. **Frontend organisé par feature** dans `components/` (`auth/`, `budget/`, `patrimoine/` à venir)
6. **Pas de fichier de plus de 500 lignes** sauf justification (= signal de refactor)
7. **Un fichier par classe ORM ou par concept Pydantic** (pas de `models.py` géant à terme)

## Conséquences

### Positives

- Une seule commande `git clone` ramène tout
- Refactors cross-frontend/backend dans le même commit
- Une seule CI à maintenir
- Onboarding facile

### Négatives

- Le repo grossit avec les builds (dependencies, etc.) — mitigation via `.gitignore` discipliné
- Si un jour on veut publier la lib finance en package isolé, il faudra extraire — pas un problème aujourd'hui

## Alternatives considérées

### Option A — Polyrepo

`tangent-backend` + `tangent-frontend` séparés. Écartée car friction au quotidien pour des changements cross-stack.

### Option B — Nx / Turborepo

Monorepo avec tooling avancé. Écartée car overkill pour 1 dev, complexité ajoutée pour peu de gain.

### Option C — Backend Django avec frontend dans `static/`

Stack unifié Python. Écartée car DX React/Vite incomparable, et FastAPI mieux pour l'API.

## Notes

- **Architecture aplatie pour partage avec Claude** : convention `projet_finance_backend_app_routers_powens.py` (les `/` deviennent `_`) — utilisée uniquement pour le partage de code, jamais dans le repo réel
- **À introduire en Phase A** : module `aggregator/` pour abstraction Powens (cf ADR-008)
- **Conventional commits** obligatoires : `feat(budget):`, `fix(auth):`, `chore(deps):`, etc.
- **Branches** : `main` (prod), feature branches `feat/...`, `fix/...`
