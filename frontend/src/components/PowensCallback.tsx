import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { useSyncBankAccounts } from "@/api";
import { NAV_PATHS } from "@/components/Sidebar";

/** Detects ?powens_sync=success in the URL after the Powens OAuth callback,
 *  refreshes the auth status, triggers a sync via the new /accounts/sync
 *  endpoint (Phase A), and lands on Comptes with a clean URL. */
export function PowensCallbackHandler() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const sync = useSyncBankAccounts();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;

    const params = new URLSearchParams(search);
    const status = params.get("powens_sync");
    if (!status) return;
    hasRun.current = true;

    if (status === "success") {
      // Refresh user_connected status and trigger the new multi-account sync.
      // /accounts/sync also bridges legacy positions, so dashboard/historique/
      // optimisation tabs are populated in the same call.
      qc.invalidateQueries({ queryKey: ["sync", "status"] });
      // Replace (not push) so a refresh or "back" doesn't re-trigger the callback.
      navigate(NAV_PATHS.accounts, { replace: true });
      sync.mutate(undefined, {
        onSuccess: () => {
          // Invalidate legacy queries too — /accounts/sync writes the bridge
          // and the user expects all tabs to refresh.
          qc.invalidateQueries({ queryKey: ["portfolio"] });
          qc.invalidateQueries({ queryKey: ["dashboard"] });
          qc.invalidateQueries({ queryKey: ["timeseries"] });
          qc.invalidateQueries({ queryKey: ["projection"] });
          qc.invalidateQueries({ queryKey: ["optimizer"] });
        },
        onError: () => {
          window.alert(
            "Banque ajoutée, mais la première récupération des comptes a échoué. Réessaie avec « Mettre à jour ».",
          );
        },
      });
    } else {
      navigate(pathname, { replace: true });
      const reason = params.get("error") || "unknown";
      console.error("Powens callback failed:", reason);
      window.alert(`La connexion à la banque a échoué (${reason}). Réessaie.`);
    }
  }, [qc, sync, navigate, pathname, search]);

  return null;
}
