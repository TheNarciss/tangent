/**
 * Profil utilisateur. Persistant en localStorage, jamais envoyé au backend
 * sauf en runtime (body de requête) pour les calculs.
 *
 * Convention d'unités : les pourcentages sont stockés en valeurs « lisibles »
 * (e.g. 7 pour 7 %, pas 0.07). La conversion en fractions se fait à la frontière
 * des appels API.
 *
 * IMPLÉMENTATION : singleton module-level + useSyncExternalStore. Garantit que
 * TOUS les composants qui appellent useProfile() voient la même valeur en temps
 * réel, sans devoir partager du contexte React. Quand le modal sauvegarde, l'onglet
 * Optimisation se met à jour automatiquement.
 */
import { useSyncExternalStore } from "react";

const STORAGE_KEY = "tangent.profile";

export interface CeilingsUsed {
  livret_a: number;
  livret_a_jeune: number;
  ldds: number;
  lep: number;
  pel: number;
}

export interface UserProfile {
  first_name: string;
  birth_date: string; // ISO yyyy-mm-dd
  fiscal_shares: number; // 1, 1.5, 2, 2.5…
  rfr_n_minus_2: number; // €
  tmi_pct: number; // 0, 0.11, 0.30, 0.41, 0.45  (fraction)
  ceilings_used: CeilingsUsed;
  // Stratégie patrimoniale — 4 paramètres concrets qui dessinent la stratégie.
  horizon_years: number; // 1–50
  monthly_dca: number; // €/mois
  target_annual_return: number; // raw %, e.g. 7 = 7 %
  max_annual_volatility: number; // raw %, e.g. 12 = 12 %
}

export const EMPTY_PROFILE: UserProfile = {
  first_name: "",
  birth_date: "",
  fiscal_shares: 1,
  rfr_n_minus_2: 0,
  tmi_pct: 0.11,
  ceilings_used: { livret_a: 0, livret_a_jeune: 0, ldds: 0, lep: 0, pel: 0 },
  horizon_years: 10,
  monthly_dca: 250,
  target_annual_return: 7,
  max_annual_volatility: 12,
};

export function ageFromBirthDate(birthDate: string): number | null {
  if (!birthDate) return null;
  const dob = new Date(birthDate);
  if (Number.isNaN(dob.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const m = now.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < dob.getDate())) age--;
  return age;
}

export function isProfileComplete(p: UserProfile | null): p is UserProfile {
  return !!p && !!p.birth_date && p.fiscal_shares > 0;
}

/** Tolère les payloads localStorage d'anciens schémas (drop des champs obsolètes). */
function migrate(raw: unknown): UserProfile {
  const r = (raw ?? {}) as Partial<UserProfile>;
  return {
    ...EMPTY_PROFILE,
    ...r,
    ceilings_used: { ...EMPTY_PROFILE.ceilings_used, ...(r.ceilings_used ?? {}) },
  };
}

/* ─── Store singleton ──────────────────────────────────────────────────────
   useSyncExternalStore est le pattern React natif pour partager un state
   externe entre composants. Tous les useProfile() pointent vers _profile.
*/
let _profile: UserProfile | null = null;
let _initialized = false;
const _listeners = new Set<() => void>();

function _ensureInit(): void {
  if (_initialized) return;
  if (typeof window !== "undefined") {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      _profile = raw ? migrate(JSON.parse(raw)) : null;
    } catch {
      _profile = null;
    }
  }
  _initialized = true;
}

function _subscribe(cb: () => void): () => void {
  _listeners.add(cb);
  return () => {
    _listeners.delete(cb);
  };
}

function _getSnapshot(): UserProfile | null {
  _ensureInit();
  return _profile;
}

function _getServerSnapshot(): UserProfile | null {
  return null; // SSR : pas de localStorage
}

function setSharedProfile(next: UserProfile | null): void {
  _ensureInit();
  _profile = next;
  if (typeof window !== "undefined") {
    if (next === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  }
  // Notify all subscribed components
  _listeners.forEach((cb) => cb());
}

export function useProfile(): [UserProfile | null, (p: UserProfile | null) => void] {
  const profile = useSyncExternalStore(_subscribe, _getSnapshot, _getServerSnapshot);
  return [profile, setSharedProfile];
}
