/**
 * Profile sync: pull DB profile at mount, push localStorage edits to DB.
 *
 * Strategy: localStorage stays the authoritative cache for performance
 * (every component uses useProfile() synchronously). On app boot, we
 * fetch /profile from DB and merge into localStorage. On every save,
 * we PUT to /profile in the background. If the PUT fails, localStorage
 * still has the data — the user's not blocked.
 */
import { useEffect, useRef } from "react";

import { useProfile, type UserProfile } from "@/lib/profile";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

interface ProfileDTO {
  birth_date: string | null;
  fiscal_shares: number | null;
  rfr_n_minus_2: number | null;
  target_annual_return: number | null;
  max_annual_volatility: number | null;
  horizon_years: number | null;
  ceilings_used: Record<string, unknown> | null;
}

function dtoToProfile(dto: ProfileDTO): Partial<UserProfile> {
  return {
    birthDate: dto.birth_date ?? undefined,
    fiscalShares: dto.fiscal_shares ?? undefined,
    rfrNMinus2: dto.rfr_n_minus_2 ?? undefined,
    targetAnnualReturn: dto.target_annual_return ?? undefined,
    maxAnnualVolatility: dto.max_annual_volatility ?? undefined,
    horizonYears: dto.horizon_years ?? undefined,
    ceilingsUsed: (dto.ceilings_used as UserProfile["ceilingsUsed"]) ?? undefined,
  };
}

function profileToDTO(profile: UserProfile): ProfileDTO {
  return {
    birth_date: profile.birthDate ?? null,
    fiscal_shares: profile.fiscalShares ?? null,
    rfr_n_minus_2: profile.rfrNMinus2 ?? null,
    target_annual_return: profile.targetAnnualReturn ?? null,
    max_annual_volatility: profile.maxAnnualVolatility ?? null,
    horizon_years: profile.horizonYears ?? null,
    ceilings_used: profile.ceilingsUsed ?? {},
  };
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
        const dto: ProfileDTO = await res.json();
        const merged: UserProfile = { ...(profile ?? {}), ...dtoToProfile(dto) } as UserProfile;
        // Only overwrite if DB had at least one field
        const hasDbData = Object.values(dto).some((v) => v !== null && v !== undefined && (typeof v !== "object" || Object.keys(v as object).length > 0));
        if (hasDbData) setProfile(merged);
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
        body: JSON.stringify(profileToDTO(profile)),
      }).catch(() => {});
    }, 500);
    return () => clearTimeout(handle);
  }, [enabled, profile]);
}
