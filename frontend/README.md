# Portfolio Dashboard — Frontend

React + Vite + TypeScript + Tailwind + shadcn/ui + TanStack Query.

## Setup

```bash
pnpm install   # ou npm/yarn
```

### shadcn primitives (à faire une seule fois)

Le projet est déjà configuré (`components.json`). Ajoute les composants nécessaires :

```bash
pnpm dlx shadcn@latest add button card dialog input label table
```

Cela crée `src/components/ui/{button,card,dialog,input,label,table}.tsx`.

## Run

Backend FastAPI doit tourner sur `http://localhost:8000` (sinon override avec
`VITE_API_URL=...`).

```bash
pnpm dev   # http://localhost:5173
```

## Build

```bash
pnpm build
pnpm preview
```

## Architecture

```
src/
├── main.tsx              QueryClient + dark mode
├── App.tsx               Page Dashboard
├── index.css             Tailwind + shadcn vars + fonts
├── api.ts                Types + fetch client + hooks (un seul fichier)
├── lib/{utils,format}.ts cn() + formateurs nombre/devise/%
└── components/
    ├── Metrics.tsx       Grille KPI
    ├── Assets.tsx        Table des positions
    ├── Correlation.tsx   Heatmap CSS
    ├── Insights.tsx      Diagnostic auto
    └── Editor.tsx        Dialog d'édition (CRUD positions)
```

Règles : composants présentationnels uniquement, état serveur via TanStack Query,
zéro state global, heatmap en CSS pur (pas de recharts), shadcn primitives via CLI.
