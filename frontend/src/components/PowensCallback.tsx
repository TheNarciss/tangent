import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useSyncBankAccounts } from "@/api";

/** Detects ?powens_sync=success in the URL after the Powens OAuth callback,
 *  refreshes the auth status, triggers a sync via the new /accounts/sync
 *  endpoint (Phase A), and cleans the URL. */
interface Props {
  /** Called on ?powens_sync=success so the app can show the Comptes view. */
  onConnected?: () => void;
}

export function PowensCallbackHandler({ onConnected }: Props = {}) {
  const qc = useQueryClient();
  const sync = useSyncBankAccounts();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;

    const params = new URLSearchParams(window.location.search);
    const status = params.get("powens_sync");
    if (!status) return;
    hasRun.current = true;

    // Clean URL immediately so a refresh doesn't re-trigger
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, "", cleanUrl);

    if (status === "success") {
      // Refresh user_connected status and trigger the new multi-account sync.
      // /accounts/sync also bridges legacy positions, so dashboard/historique/
      // optimisation tabs are populated in the same call.
      qc.invalidateQueries({ queryKey: ["sync", "status"] });
      onConnected?.();
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
      const reason = params.get("error") || "unknown";
      console.error("Powens callback failed:", reason);
      window.alert(`La connexion à la banque a échoué (${reason}). Réessaie.`);
    }
  }, [qc, sync, onConnected]);

  return null;
}
