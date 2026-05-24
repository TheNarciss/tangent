/**
 * Profile sync: pull DB profile at mount, push localStorage edits to DB.
 *
 * Strategy: localStorage stays the authoritative cache for performance
 * (every component uses useProfile() synchronously). On app boot, we
 * fetch /profile from DB and merge into localStorage. On every save,
 * we PUT to /profile in the background. If the PUT fails, localStorage
 * still has the data — the user's not blocked.
 *
 * UserProfile uses snake_case to mirror the DB DTO directly — no conversion needed.
 */
import { useEffect, useRef } from "react";
import { useProfile, type UserProfile } from "@/lib/profile";

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
        const dto: Partial<UserProfile> = await res.json();
        const hasDbData = Object.values(dto).some(
          (v) =>
            v !== null &&
            v !== undefined &&
            (typeof v !== "object" || Object.keys(v as object).length > 0),
        );
        if (hasDbData) setProfile({ ...(profile ?? {}), ...dto } as UserProfile);
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
        body: JSON.stringify(profile),
      }).catch(() => {});
    }, 500);
    return () => clearTimeout(handle);
  }, [enabled, profile]);
}
