import { Plus } from "lucide-react";
import { useState } from "react";

import { getPowensWebviewUrl, useSyncStatus } from "@/api";
import { Button } from "@/components/ui/button";

/** Bouton header — UN seul rôle : démarrer le flux Powens d'ajout de banque.
 *
 * Toujours redirige vers le webview Powens en `mode=connect` (ajout d'un
 * nouveau connector). Pas de sync, pas de "manage" — c'est la page Accounts
 * qui gère la sync via son propre bouton "Sync" + auto-refresh au mount.
 */
export function AddBankButton() {
  const [busy, setBusy] = useState(false);
  const status = useSyncStatus();

  const handleClick = async () => {
    setBusy(true);
    try {
      const url = await getPowensWebviewUrl();
      if (url) window.location.href = url;
    } catch (e) {
      console.error(e);
      setBusy(false);
    }
  };

  // Powens pas configuré côté backend → bouton désactivé avec tooltip
  if (status.data && !status.data.configured) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled
        className="gap-2"
        title="Powens non configuré côté serveur"
      >
        <Plus className="h-4 w-4" />
        Ajouter une banque
      </Button>
    );
  }

  return (
    <Button variant="outline" size="sm" onClick={handleClick} disabled={busy} className="gap-2">
      <Plus className="h-4 w-4" />
      {busy ? "Redirection…" : "Ajouter une banque"}
    </Button>
  );
}
