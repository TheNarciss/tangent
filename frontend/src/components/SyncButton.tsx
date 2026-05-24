import { RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";

import { useSyncPowens, useSyncStatus, getPowensWebviewUrl } from "@/api";
import { cn } from "@/lib/utils";

/** Bouton "Sync BNP" pour le header.
 *
 * États :
 * - Non configuré → bouton grisé "Connecter Powens"
 * - Stale (> 12h) → bouton orange "Sync recommandée"
 * - Fresh → bouton normal avec "il y a Xh"
 * - En cours → spinner
 * - Erreur → bouton rouge avec icône
 */
export function SyncButton() {
  const status = useSyncStatus();
  const sync = useSyncPowens();

  // Handler local pour fetch l'url et rediriger l'utilisateur vers powens
  const handleConnect = async () => {
    try {
      const url = await getPowensWebviewUrl();
      if (url) {
        window.location.href = url;
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!status.data) {
    return (
      <button className="h-9 px-3 rounded-md border border-border text-xs text-muted-foreground" disabled>
        Chargement…
      </button>
    );
  }

  if (!status.data.configured) {
    return (
      <button
        className="h-9 px-3 rounded-md border border-border text-xs text-muted-foreground cursor-not-allowed opacity-60"
        title="Powens non configuré — remplis backend/.env"
        disabled
      >
        Powens non configuré
      </button>
    );
  }

  if (!status.data.user_connected) {
    return (
      <button
        onClick={handleConnect}
        className="h-9 px-3 rounded-md border border-border text-xs text-foreground cursor-pointer hover:bg-muted/40"
        title="Se connecter à Powens"
      >
        Connecter Powens
      </button>
    );
  }

  const isStale = status.data.is_stale;
  const hasError = !!status.data.last_error && !sync.isPending;
  const ageLabel = formatAge(status.data.last_sync, status.data.age_hours);

  return (
    <button
      onClick={() => sync.mutate()}
      disabled={sync.isPending}
      className={cn(
        "h-9 px-3 rounded-md border text-xs font-medium flex items-center gap-2 transition-colors",
        sync.isPending && "bg-muted/40 border-border",
        hasError && "border-[hsl(var(--loss))] text-[hsl(var(--loss))]",
        isStale && !hasError && !sync.isPending && "border-yellow-500/60 text-yellow-700 dark:text-yellow-400",
        !isStale && !hasError && !sync.isPending && "border-border hover:bg-muted/40",
      )}
      title={
        hasError ? `Erreur: ${status.data.last_error}` :
        sync.isPending ? "Synchronisation en cours…" :
        `Cliquer pour synchroniser maintenant. Dernière sync : ${ageLabel}`
      }
    >
      {sync.isPending ? (
        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
      ) : hasError ? (
        <AlertCircle className="h-3.5 w-3.5" />
      ) : (
        <CheckCircle2 className="h-3.5 w-3.5" />
      )}
      <span className="font-mono">
        {sync.isPending ? "Sync…" : `BNP · ${ageLabel}`}
      </span>
    </button>
  );
}

function formatAge(lastSync: string | null, ageHours: number | null): string {
  if (!lastSync || ageHours === null) return "jamais sync";
  if (ageHours < 1) return "à l'instant";
  if (ageHours < 24) return `il y a ${Math.round(ageHours)}h`;
  const days = Math.round(ageHours / 24);
  return `il y a ${days}j`;
}