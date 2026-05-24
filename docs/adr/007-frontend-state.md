# ADR-007: State management frontend

- **Status** : accepted
- **Date** : 2026-05-23
- **Deciders** : Clem

## Contexte

Le frontend manipule plusieurs catégories de state :
1. **Données serveur** (portfolio, dashboard, transactions) — async, doivent être à jour
2. **State UI éphémère** (modal ouverte, onglet actif, input form) — locale au composant
3. **Préférences utilisateur** (thème, devise, choix de période) — persiste cross-session
4. **State partagé** (user authentifié actuel) — utilisé par plusieurs composants

Sans discipline, on tombe vite dans le piège du Redux global pour tout, ou inversement le prop-drilling enfer.

## Décision

**Pas de Redux, MobX, Zustand, Recoil.** Une catégorie de state → une seule technologie :

| Catégorie | Outil | Exemple |
|-----------|-------|---------|
| Données serveur | **React Query** (TanStack Query v5) | `useQuery(["portfolio"], fetchPortfolio)` |
| State UI éphémère | **useState / useReducer** | Modal open/closed, form values |
| Préférences cross-session | **localStorage** via custom hook | Thème, devise affichée |
| Préférences persistantes serveur | **DB + React Query** | Profil financier (cf ADR-009) |
| State global de session | **React Query** sur `/users/me` | User authentifié |

**Règles strictes** :
1. Toute donnée serveur passe par React Query, jamais de fetch direct dans un `useEffect`
2. La même `queryKey` doit toujours retourner les mêmes données → garantie de cache cohérent
3. Mutations via `useMutation` avec invalidation explicite des queries impactées
4. localStorage uniquement pour les **préférences** (pas pour les données critiques) — quand l'user veut un truc cross-device, sync DB obligatoire (cf le pattern `useProfileSync` ajouté le 2026-05-22)
5. Pas de Context Provider pour de la data serveur (React Query fait ça mieux)
6. Context Provider acceptable pour : thème, locale, feature flags

**React Query config par défaut** :
```ts
{
  staleTime: 60_000,           // 1 min
  refetchOnWindowFocus: false, // évite refetch agressif
  retry: 1,                     // 1 retry max sur erreur
}
```

## Conséquences

### Positives

- Simple à comprendre, peu de boilerplate
- React Query gère cache, dedup, retry, optimistic updates → maintenance évitée
- Bundle plus léger (pas de Redux ni middleware)
- DX excellente avec React Query DevTools

### Négatives

- localStorage = ne fonctionne pas en SSR (mais on n'a pas de SSR)
- React Query : courbe d'apprentissage modérée pour les patterns avancés (invalidations multiples)
- Pas de "single source of truth" globale comme Redux — mais c'est voulu

## Alternatives considérées

### Option A — Redux Toolkit + RTK Query

Industry standard. Écartée car boilerplate plus lourd, React Query couvre 95% du besoin avec moins de code.

### Option B — Zustand

Léger et élégant pour le state global. Écartée car on n'a besoin de quasi rien en state global non-server.

### Option C — Tout en Context API React

Simple, natif. Écartée car re-renders non-optimisés sur gros contextes, et React Query est meilleur pour data serveur.

## Notes

- Pattern recommandé pour les hooks API : un fichier `src/api.ts` qui centralise tous les `useQuery`/`useMutation`, importables depuis n'importe où
- À l'avenir : si vraiment besoin de state global complexe (notifications toast, etc.), Zustand sera l'outil de choix
- Le hook `useProfileSync` créé le 2026-05-22 illustre le pattern correct : localStorage initial + sync DB en background avec debounce
- **Anti-pattern à éviter** : stocker des données serveur en `useState` après un fetch manuel → toujours passer par React Query
