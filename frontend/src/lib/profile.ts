/**
 * Profil utilisateur — cache localStorage du profil DB (cf. profile-sync.ts).
 *
 * Convention d'unités : les pourcentages sont stockés en valeurs « lisibles »
 * (e.g. 7 pour 7 %, pas 0.07). La conversion en fractions se fait à la frontière
 * des appels API.
 *
 * IMPLÉMENTATION : singleton module-level + useSyncExternalStore. Garantit que
 * TOUS les composants qui appellent useProfile() voient la même valeur en temps
 * réel, sans devoir partager du contexte React.
 */
import { useSyncExternalStore } from "react";

const STORAGE_KEY = "tangent.profile";

export type HouseholdStatus = "single" | "couple";

/** Manual fallback for regulated savings balances when none is synced. */
export interface CeilingsUsed {
  livret_a: number;
  livret_a_jeune: number;
  ldds: number;
  lep: number;
  pel: number;
}

export interface UserProfile {
  birth_date: string; // ISO yyyy-mm-dd
  household_status: HouseholdStatus;
  children: number;
  fiscal_shares: number; // derived from the household, cf. fiscalSharesFor()
  rfr_n_minus_2: number; // €
  monthly_dca: number; // €/mois
  /** Slider « prudent ↔ dynamique », 1..5. The two fields below are derived
   *  from it by the backend (config/risk_levels.yaml) and mirrored here so the
   *  optimizer's "selon mon profil" objective works without a round-trip. */
  risk_level: number;
  target_annual_return: number; // raw %, e.g. 7 = 7 %
  max_annual_volatility: number; // raw %, e.g. 12 = 12 %
  horizon_years: number; // 1–50, set from the Projection page (goal date)
  goal_amount: number | null; // € d'aujourd'hui, set from the Projection page
  ceilings_used: CeilingsUsed;
  default_broker: string | null; // null = auto-detected at sync
  auto_review_enabled: boolean; // opt-in to nightly LLM portfolio review (ADR-018)
}

export const EMPTY_PROFILE: UserProfile = {
  birth_date: "",
  household_status: "single",
  children: 0,
  fiscal_shares: 1,
  rfr_n_minus_2: 0,
  monthly_dca: 250,
  risk_level: 3,
  target_annual_return: 7,
  max_annual_volatility: 12,
  horizon_years: 10,
  goal_amount: null,
  ceilings_used: { livret_a: 0, livret_a_jeune: 0, ldds: 0, lep: 0, pel: 0 },
  default_broker: null,
  auto_review_enabled: false,
};

/** Quotient familial : 1 part (2 en couple), +0,5 par enfant pour les deux
 *  premiers, +1 par enfant à partir du troisième. */
export function fiscalSharesFor(status: HouseholdStatus, children: number): number {
  const kids = Math.max(0, Math.floor(children));
  const base = status === "couple" ? 2 : 1;
  return base + Math.min(kids, 2) * 0.5 + Math.max(0, kids - 2);
}

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

/**
 * Regulated savings balances read from the synced accounts (WealthSummary
 * envelopes), in the shape the optimizer expects. `null` when nothing is
 * synced, so the caller can fall back to the manual values.
 */
export function ceilingsFromEnvelopes(
  envelopes: { envelope_type: string; balance: number }[] | undefined,
): CeilingsUsed | null {
  if (!envelopes || envelopes.length === 0) return null;
  const out: CeilingsUsed = { livret_a: 0, livret_a_jeune: 0, ldds: 0, lep: 0, pel: 0 };
  for (const e of envelopes) {
    if (e.envelope_type in out) out[e.envelope_type as keyof CeilingsUsed] += e.balance;
  }
  return out;
}

/** Tolère les payloads localStorage d'anciens schémas (drop des champs obsolètes). */
function migrate(raw: unknown): UserProfile {
  const r = (raw ?? {}) as Partial<UserProfile>;
  const known = (Object.keys(EMPTY_PROFILE) as (keyof UserProfile)[]).reduce(
    (acc, k) => (r[k] === undefined ? acc : { ...acc, [k]: r[k] }),
    {} as Partial<UserProfile>,
  );
  return {
    ...EMPTY_PROFILE,
    ...known,
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

/** Forget the local profile (logout) so the next user starts clean. */
export function clearProfile(): void {
  setSharedProfile(null);
}

export function useProfile(): [UserProfile | null, (p: UserProfile | null) => void] {
  const profile = useSyncExternalStore(_subscribe, _getSnapshot, _getServerSnapshot);
  return [profile, setSharedProfile];
}
