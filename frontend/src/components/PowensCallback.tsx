import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useSyncPowens } from "@/api";

/** Detects ?powens_sync=success in the URL after the Powens OAuth callback,
 *  refreshes the auth status, triggers a sync, and cleans the URL. */
export function PowensCallbackHandler() {
  const qc = useQueryClient();
  const sync = useSyncPowens();
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
      // Refresh user_connected status and trigger a first sync
      qc.invalidateQueries({ queryKey: ["sync", "status"] });
      sync.mutate();
    } else {
      const reason = params.get("error") || "unknown";
      console.error("Powens callback failed:", reason);
      alert(`Connexion Powens échouée : ${reason}`);
    }
  }, [qc, sync]);

  return null;
}
