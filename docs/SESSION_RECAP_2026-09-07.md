# SESSION_RECAP — 7 sept. 2026 (Claude)

Suite de `ETAT_DES_LIEUX_2026-09.md`. Quatre commits prêts en local, **non poussés** : le repo
n'était pas dans les sources de la session Claude (proxy GitHub → 403). Patches livrés dans le
chat (`tangent-patches.zip`, `git am patches/*.patch` depuis `main`), à pousser dans cet ordre
(branches empilées) :

| Ordre | Branche | Commit | Contenu |
|---|---|---|---|
| 1 | `fix/mobile-layouts` | `fix(mobile)` | Comptes/Assets/Bengen/Metrics/Profil/Réglages à 390 px, safe-area, dialogs scrollables, tooltips tactiles + clampés, fan chart lisible |
| 2 | `feat/nav-wording` | `feat(nav)` | Aperçu au lieu de IA, Placements, sous-titres sans jargon, header unique Profil/Réglages, marque Tangent |
| 3 | `chore/cleanup-dead-code` | `chore(frontend)` | AI.tsx + streaming.ts supprimés, api.ts dédoublonné (−120 lignes), Section partagée, docker-compose `/api` |
| 4 | `fix/profile-sync-and-data` | `fix(profile,accounts,projection)` | profile-sync via `/api/profile`, TER exposé, broker profil respecté, auto-sync `/sync`, retour Powens → Comptes, bull/bear retirés, ChartTile état vide, Bengen debounce, purge au logout, mdp 8 partout |

Vérifié en local : `tsc`, `eslint`, `prettier`, `vitest` (15), `ruff`, `ruff format`, `pytest` (92) — tout vert.
Captures avant/après dans le chat.

## Reste à faire (ordre proposé)
- A5 `fix(wealth)` : `get_user_wealth` couvre tous les `AccountType`, Comptes lit `WealthSummary` (un seul « net »)
- A8 `perf(routes)` : yfinance en threadpool, `FrontierCloud` supprimée, stress tests cachés
- B1 `feat(router)` : react-router, 6 routes
- B3 `feat(charts)` : composant graphe responsive commun (Timeline, RiskReturn encore illisibles sur mobile)
- B4 `feat(profile-v2)` : profil 5 questions, champs morts retirés, livrets lus depuis Powens, écran Réglages → accordéon
- C1–C5 : refonte écran par écran (cf. état des lieux §7) — décisions §8 à valider
