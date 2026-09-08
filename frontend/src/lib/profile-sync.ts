/**
 * Profile sync: pull the DB profile at login, push local edits to the DB.
 *
 * localStorage stays the synchronous cache every component reads through
 * useProfile(); the DB is the source of truth across devices. On boot we
 * GET /profile and merge it over the local copy; every later change is
 * PUT (debounced). Failures are logged, never swallowed silently.
 *
 * UNIT CONVENTION (cf profile.ts): the frontend stores readable percents
 * (7 = 7 %), the backend stores fractions (0.07). Conversion happens here.
 *
 * target_annual_return / max_annual_volatility are derived server-side from
 * risk_level (config/risk_levels.yaml): we send the level and read the pair.
 */
import { useEffect, useRef } from "react";

import { http } from "@/api";
import { EMPTY_PROFILE, useProfile, type UserProfile } from "@/lib/profile";

/** Mirrors ProfileIn / ProfileOut in backend/app/routers/profile.py */
interface BackendProfileDTO {
  birth_date?: string | null;
  household_status?: "single" | "couple" | null;
  children?: number | null;
  fiscal_shares?: number | null;
  rfr_n_minus_2?: number | null;
  risk_level?: number | null;
  target_annual_return?: number | null; // fraction
  max_annual_volatility?: number | null; // fraction
  monthly_dca?: number | null;
  horizon_years?: number | null;
  default_broker?: string | null;
  ceilings_used?: Record<string, number> | null;
  auto_review_enabled?: boolean | null;
}

function toBackendDTO(p: UserProfile): BackendProfileDTO {
  return {
    birth_date: p.birth_date || null,
    household_status: p.household_status,
    children: p.children,
    fiscal_shares: p.fiscal_shares,
    rfr_n_minus_2: p.rfr_n_minus_2,
    risk_level: p.risk_level,
    monthly_dca: p.monthly_dca,
    horizon_years: p.horizon_years,
    // Only sent when the user picked one; otherwise the backend keeps the
    // broker it auto-detected at sync time (undefined → omitted from JSON).
    default_broker: p.default_broker ?? undefined,
    ceilings_used: p.ceilings_used as unknown as Record<string, number>,
    auto_review_enabled: p.auto_review_enabled,
  };
}

function fromBackendDTO(dto: BackendProfileDTO): Partial<UserProfile> {
  const out: Partial<UserProfile> = {};
  if (dto.birth_date != null) out.birth_date = dto.birth_date;
  if (dto.household_status != null) out.household_status = dto.household_status;
  if (dto.children != null) out.children = dto.children;
  if (dto.fiscal_shares != null) out.fiscal_shares = dto.fiscal_shares;
  if (dto.rfr_n_minus_2 != null) out.rfr_n_minus_2 = dto.rfr_n_minus_2;
  if (dto.risk_level != null) out.risk_level = dto.risk_level;
  if (dto.monthly_dca != null) out.monthly_dca = dto.monthly_dca;
  if (dto.target_annual_return != null) out.target_annual_return = dto.target_annual_return * 100;
  if (dto.max_annual_volatility != null)
    out.max_annual_volatility = dto.max_annual_volatility * 100;
  if (dto.horizon_years != null) out.horizon_years = dto.horizon_years;
  if (dto.default_broker != null) out.default_broker = dto.default_broker;
  if (dto.ceilings_used && Object.keys(dto.ceilings_used).length > 0)
    out.ceilings_used = dto.ceilings_used as unknown as UserProfile["ceilings_used"];
  if (dto.auto_review_enabled != null) out.auto_review_enabled = dto.auto_review_enabled;
  return out;
}

/** Mount once near the root (App.tsx). */
export function useProfileSync(enabled: boolean) {
  const [profile, setProfile] = useProfile();
  const didPullRef = useRef(false);

  // Pull DB → local on first mount once authenticated
  useEffect(() => {
    if (!enabled || didPullRef.current) return;
    didPullRef.current = true;
    http<BackendProfileDTO>("/profile")
      .then((dto) => {
        const merged = fromBackendDTO(dto);
        if (Object.keys(merged).length > 0) {
          setProfile({ ...EMPTY_PROFILE, ...(profile ?? {}), ...merged });
        }
      })
      .catch((err: unknown) => console.error("profile pull failed", err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Push every change (debounced) once the initial pull happened
  useEffect(() => {
    if (!enabled || !profile || !didPullRef.current) return;
    const handle = setTimeout(() => {
      http<BackendProfileDTO>("/profile", {
        method: "PUT",
        body: JSON.stringify(toBackendDTO(profile)),
      }).catch((err: unknown) => console.error("profile push failed", err));
    }, 500);
    return () => clearTimeout(handle);
  }, [enabled, profile]);
}
