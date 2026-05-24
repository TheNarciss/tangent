/**
 * Settings — paramètres techniques de l'app (comportement des calculs).
 *
 * Distinct de `profile` qui décrit l'utilisateur (qui il est, sa situation).
 * Settings = comment l'app calcule (shrinkage, scanner, overrides μ, etc.).
 *
 * Même pattern singleton que profile.ts (useSyncExternalStore + localStorage).
 * Garantit que tous les composants voient les mêmes settings en temps réel.
 */
import { useSyncExternalStore } from "react";

const STORAGE_KEY = "tangent.settings";

/* ─── Types ────────────────────────────────────────────────────────────── */

export type ScannerMode = "broad_eu" | "tech_growth" | "defensive";
export type HistoricalPeriod = "1y" | "2y" | "3y" | "5y" | "10y" | "max";
export type CovEstimator = "sample" | "shrunk";

export interface ScannerSettings {
  modes: ScannerMode[]; // par défaut les 3
  hypothesis_fraction: number; // 0-1, défaut 0.10 (hypothèse d'ajout 10 % pour ΔSharpe)
  n_results: number; // nombre de candidats top à afficher, défaut 10
}

export interface ExpertSettings {
  cma_shrinkage: number; // 0-1, défaut 0.70 (70 % CMA, 30 % historique)
  historical_period: HistoricalPeriod;
  risk_free_rate: number; // fraction, défaut 0.025
  cov_estimator: CovEstimator; // défaut "sample"
  cov_shrinkage: number; // si "shrunk", fraction de shrinkage vers identité
  cma_overrides: Record<string, number>; // ticker → μ forcé (fraction)
}

export interface AppSettings {
  scanner: ScannerSettings;
  expert: ExpertSettings;
}

export const DEFAULT_SETTINGS: AppSettings = {
  scanner: {
    modes: ["broad_eu", "tech_growth", "defensive"],
    hypothesis_fraction: 0.1,
    n_results: 10,
  },
  expert: {
    cma_shrinkage: 0.7,
    historical_period: "5y",
    risk_free_rate: 0.025,
    cov_estimator: "sample",
    cov_shrinkage: 0.2,
    cma_overrides: {},
  },
};

export const SCANNER_MODE_LABELS: Record<ScannerMode, string> = {
  broad_eu: "PEA Élargi (large caps EU + ETFs UCITS)",
  tech_growth: "Croissance Tech (tech ETFs + growth stocks)",
  defensive: "Défensif (bond ETFs + conservative funds)",
};

/* ─── Migration ────────────────────────────────────────────────────────── */

function migrate(raw: unknown): AppSettings {
  // Tolère anciens schémas, fusionne avec defaults
  const r = (raw ?? {}) as Partial<AppSettings>;
  return {
    scanner: { ...DEFAULT_SETTINGS.scanner, ...(r.scanner ?? {}) },
    expert: {
      ...DEFAULT_SETTINGS.expert,
      ...(r.expert ?? {}),
      cma_overrides: { ...(r.expert?.cma_overrides ?? {}) },
    },
  };
}

/* ─── Singleton store (useSyncExternalStore) ───────────────────────────── */

let _settings: AppSettings = DEFAULT_SETTINGS;
let _initialized = false;
const _listeners = new Set<() => void>();

function _ensureInit(): void {
  if (_initialized) return;
  if (typeof window !== "undefined") {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      _settings = raw ? migrate(JSON.parse(raw)) : DEFAULT_SETTINGS;
    } catch {
      _settings = DEFAULT_SETTINGS;
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

function _getSnapshot(): AppSettings {
  _ensureInit();
  return _settings;
}

function _getServerSnapshot(): AppSettings {
  return DEFAULT_SETTINGS;
}

function setSharedSettings(next: AppSettings): void {
  _ensureInit();
  _settings = next;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }
  _listeners.forEach((cb) => cb());
}

export function useSettings(): [AppSettings, (s: AppSettings) => void] {
  const s = useSyncExternalStore(_subscribe, _getSnapshot, _getServerSnapshot);
  return [s, setSharedSettings];
}
