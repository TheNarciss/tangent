/**
 * Profile sync: pull DB profile at mount, push localStorage edits to DB.
 *
 * Strategy: localStorage stays the authoritative cache for performance
 * (every component uses useProfile() synchronously). On app boot, we
 * fetch /profile from DB and merge into localStorage. On every save,
 * we PUT to /profile in the background. If the PUT fails, localStorage
 * still has the data — the user's not blocked.
 *
 * UNIT CONVENTION (cf profile.ts comment):
 *   - Frontend stores percentages as readable values: 7 means 7 %
 *   - Backend stores them as fractions: 0.07 means 7 %
 *   - Conversion happens here at the API boundary (both ways).
 *
 * SCHEMA: backend ProfileIn only knows a subset of UserProfile fields.
 * Extra frontend-only fields (first_name, tmi_pct, monthly_dca) are
 * stripped before PUT to avoid sending noise.
 */
import { useEffect, useRef } from "react";
import { useProfile, type UserProfile } from "@/lib/profile";

/** Backend /profile payload shape — must match ProfileIn in backend/app/routers/profile.py */
interface BackendProfileDTO {
  birth_date?: string | null;
  fiscal_shares?: number | null;
  rfr_n_minus_2?: number | null;
  target_annual_return?: number | null; // fraction (0..2)
  max_annual_volatility?: number | null; // fraction (0..1)
  horizon_years?: number | null;
  ceilings_used?: Record<string, number> | null;
  auto_review_enabled?: boolean | null;
}

/** Frontend (raw %) → backend (fraction) — only the fields the backend knows. */
function toBackendDTO(p: UserProfile): BackendProfileDTO {
  return {
    birth_date: p.birth_date || null,
    fiscal_shares: p.fiscal_shares,
    rfr_n_minus_2: p.rfr_n_minus_2,
    target_annual_return: p.target_annual_return / 100,
    max_annual_volatility: p.max_annual_volatility / 100,
    horizon_years: p.horizon_years,
    ceilings_used: p.ceilings_used as unknown as Record<string, number>,
    auto_review_enabled: p.auto_review_enabled,
  };
}

/** Backend (fraction) → frontend (raw %) — merges into local profile. */
function fromBackendDTO(dto: BackendProfileDTO): Partial<UserProfile> {
  const out: Partial<UserProfile> = {};
  if (dto.birth_date !== null && dto.birth_date !== undefined) out.birth_date = dto.birth_date;
  if (dto.fiscal_shares !== null && dto.fiscal_shares !== undefined)
    out.fiscal_shares = dto.fiscal_shares;
  if (dto.rfr_n_minus_2 !== null && dto.rfr_n_minus_2 !== undefined)
    out.rfr_n_minus_2 = dto.rfr_n_minus_2;
  if (dto.target_annual_return !== null && dto.target_annual_return !== undefined)
    out.target_annual_return = dto.target_annual_return * 100;
  if (dto.max_annual_volatility !== null && dto.max_annual_volatility !== undefined)
    out.max_annual_volatility = dto.max_annual_volatility * 100;
  if (dto.horizon_years !== null && dto.horizon_years !== undefined)
    out.horizon_years = dto.horizon_years;
  if (dto.ceilings_used && Object.keys(dto.ceilings_used).length > 0)
    out.ceilings_used = dto.ceilings_used as unknown as UserProfile["ceilings_used"];
  if (dto.auto_review_enabled !== null && dto.auto_review_enabled !== undefined)
    out.auto_review_enabled = dto.auto_review_enabled;
  return out;
}

/**
 * Mount this hook ONCE near the root (App.tsx). It pulls from /profile at
 * boot and pushes any subsequent change up to /profile.
 */
export function useProfileSync(enabled: boolean) {
  const [profile, setProfile] = useProfile();
  const didPullRef = useRef(false);

  // Pull DB → localStorage on first mount when auth becomes ready
  useEffect(() => {
    if (!enabled || didPullRef.current) return;
    didPullRef.current = true;
    (async () => {
      try {
        const res = await fetch("/profile", { credentials: "include" });
        if (!res.ok) throw new Error(`GET /profile ${res.status}`);
        const dto: BackendProfileDTO = await res.json();
        const merged = fromBackendDTO(dto);
        if (Object.keys(merged).length > 0) {
          setProfile({ ...(profile ?? {}), ...merged } as UserProfile);
        }
      } catch {
        // Silent — keep localStorage
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Push every change up to /profile (debounced)
  useEffect(() => {
    if (!enabled || !profile || !didPullRef.current) return;
    const handle = setTimeout(() => {
      fetch("/profile", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toBackendDTO(profile)),
      }).catch(() => {});
    }, 500);
    return () => clearTimeout(handle);
  }, [enabled, profile]);
}
