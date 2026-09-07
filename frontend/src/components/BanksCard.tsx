import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2 } from "lucide-react";

import { fetchBankConnections, unlinkBankConnection } from "@/api";
import { relativeTime } from "@/lib/accounts";
import { Button } from "@/components/ui/button";

/**
 * « Mes banques » — the connections behind the accounts, managed from the
 * Comptes screen (add is the header button, unlink here, errors shown here).
 */
export function BanksCard() {
  const connections = useQuery({ queryKey: ["bank-connections"], queryFn: fetchBankConnections });

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
        Mes banques
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Tangent se connecte à ta banque via un service agréé (Powens) : on ne voit jamais tes
        identifiants. Retirer une banque supprime aussi ses comptes ici.
      </p>
      <div className="mt-3 space-y-2">
        {connections.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {connections.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">Impossible de charger tes banques.</p>
        )}
        {connections.data && connections.data.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Aucune banque connectée. Utilise <strong>+ Ajouter une banque</strong> en haut de la
            page.
          </p>
        )}
        {connections.data?.map((conn) => (
          <BankRow
            key={conn.connection_id}
            connectionId={conn.connection_id}
            name={conn.institution_name}
            accountsCount={conn.accounts_count}
            lastUpdate={conn.last_update}
            hasError={!!conn.error}
          />
        ))}
      </div>
    </section>
  );
}

function BankRow({
  connectionId,
  name,
  accountsCount,
  lastUpdate,
  hasError,
}: {
  connectionId: number;
  name: string;
  accountsCount: number;
  lastUpdate: string | null;
  hasError: boolean;
}) {
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unlink = useMutation({
    mutationFn: () => unlinkBankConnection(connectionId),
    onSuccess: () => {
      for (const key of ["bank-connections", "bank-accounts", "wealth", "dashboard"]) {
        qc.invalidateQueries({ queryKey: [key] });
      }
      setConfirming(false);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "Erreur inconnue"),
  });

  return (
    <div className="rounded-md border px-3 py-2">
      <div className="flex items-center gap-3">
        <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">
            {accountsCount} compte{accountsCount > 1 ? "s" : ""} · mis à jour{" "}
            {relativeTime(lastUpdate)}
            {hasError && (
              <span className="ml-2 text-[hsl(var(--loss))]">
                connexion à refaire (mot de passe changé ?)
              </span>
            )}
          </p>
        </div>
        {!confirming && (
          <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
            Retirer
          </Button>
        )}
      </div>
      {confirming && (
        <div className="mt-2 flex flex-wrap items-center justify-end gap-2 text-xs">
          <span className="mr-auto text-muted-foreground">
            Retirer {name} et ses {accountsCount} compte{accountsCount > 1 ? "s" : ""} ?
          </span>
          <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
            Annuler
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => unlink.mutate()}
            disabled={unlink.isPending}
          >
            {unlink.isPending ? "Retrait…" : "Retirer"}
          </Button>
        </div>
      )}
      {error && <p className="mt-1 text-xs text-[hsl(var(--loss))]">{error}</p>}
    </div>
  );
}
