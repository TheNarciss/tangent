import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Radar } from "lucide-react";

import {
  ApiError,
  adminRefreshMarketLeads,
  useCurrentUser,
  useMarketLeads,
  type MarketLead,
  type MarketLeadSource,
} from "@/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * « Pistes de marché » — the raw list the night collected (ADR-033).
 *
 * Deliberately noisy: every observation above the thresholds is here, and
 * the morning briefing is what keeps zero to three of them. This screen
 * shows what the triage had to choose from. One filter row (the source),
 * then the leads, biggest first as the backend orders them. Nothing here is
 * a buy or a sell, and the screen says so before the list.
 */
export function MarketLeads() {
  const { data, isLoading, error } = useMarketLeads();
  const [source, setSource] = useState<MarketLeadSource | "all">("all");

  const shown = useMemo(
    () => (data?.leads ?? []).filter((lead) => source === "all" || lead.source === source),
    [data, source],
  );
  const counts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const lead of data?.leads ?? []) out[lead.source] = (out[lead.source] ?? 0) + 1;
    return out;
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-20 animate-pulse rounded-xl bg-muted/30" />
        <div className="h-64 animate-pulse rounded-xl bg-muted/30" />
      </div>
    );
  }
  if (error || !data) {
    return <NotYet error={error} />;
  }

  return (
    <div className="space-y-6">
      <WhatThisIs computedAt={data.computed_at} total={data.leads.length} />

      {/* One filter row above everything it scopes. */}
      <div className="flex flex-wrap items-center gap-1 rounded-md border p-0.5 text-xs">
        {(["all", "polymarket", "edgar_form4", "edgar_13f"] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setSource(key)}
            className={cn(
              "rounded px-2.5 py-1",
              source === key ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {key === "all" ? "Toutes" : SOURCE_LABELS[key]}
            <span className={cn("ml-1", source === key ? "opacity-80" : "text-muted-foreground")}>
              {key === "all" ? data.leads.length : (counts[key] ?? 0)}
            </span>
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <section className="rounded-xl border bg-card p-4 md:p-6">
          <p className="text-sm text-muted-foreground">
            Rien de cette source cette nuit : aucune observation n'a passé les seuils.
          </p>
        </section>
      ) : (
        <ul className="space-y-3">
          {shown.map((lead, i) => (
            <LeadCard key={`${lead.source}-${lead.kind}-${lead.title}-${i}`} lead={lead} />
          ))}
        </ul>
      )}
    </div>
  );
}

/* ── What this is, before the list ─────────────────────────────────────── */

function WhatThisIs({ computedAt, total }: { computedAt: string; total: number }) {
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <p className="text-sm">
        Chaque nuit, Tangent lit trois sources publiques de ce que des gens{" "}
        <strong>font de leur argent</strong> : les paris qui bougent sur Polymarket, les dirigeants
        qui achètent l'action de leur propre société, les grands gérants qui ouvrent ou soldent une
        ligne. Tout ce qui dépasse un seuil est ici, sans tri.
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        C'est du bruit pour l'essentiel, et c'est voulu : ton briefing du matin en garde zéro à
        trois, avec la raison. Une piste est une chose à regarder, jamais un ordre d'acheter ou de
        vendre.
      </p>
      <p className="mt-3 text-xs text-muted-foreground">
        {total} piste{total > 1 ? "s" : ""} collectée{total > 1 ? "s" : ""} {when(computedAt)}.
        Prochaine collecte cette nuit à 02:15.
      </p>
    </section>
  );
}

/* ── One lead ──────────────────────────────────────────────────────────── */

const SOURCE_LABELS: Record<MarketLeadSource, string> = {
  polymarket: "Polymarket",
  edgar_form4: "SEC · dirigeants",
  edgar_13f: "SEC · gérants",
};

const KIND_LABELS: Record<string, string> = {
  prediction_move: "Cote qui a bougé",
  prediction_state: "État des attentes",
  insider_cluster: "Achats groupés",
  insider_buy: "Gros achat",
  fund_new_position: "Nouvelle ligne",
  fund_exit: "Ligne soldée",
  fund_change: "Ligne modifiée",
};

function LeadCard({ lead }: { lead: MarketLead }) {
  return (
    <li className="rounded-xl border bg-card p-4 md:px-6">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span className="rounded-sm border px-1.5 py-0.5">{SOURCE_LABELS[lead.source]}</span>
        <span>{KIND_LABELS[lead.kind] ?? lead.kind}</span>
        <span className="ml-auto normal-case tracking-normal">{longDate(lead.observed_at)}</span>
      </div>
      <p className="mt-2 text-sm font-medium">{lead.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{lead.detail}</p>
      <a
        href={lead.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground hover:underline"
      >
        Voir la source
        <ExternalLink className="h-3 w-3" />
      </a>
    </li>
  );
}

/* ── Before the first collection ───────────────────────────────────────── */

function NotYet({ error }: { error: unknown }) {
  const { data: user } = useCurrentUser();
  const qc = useQueryClient();
  const collect = useMutation({
    mutationFn: adminRefreshMarketLeads,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["market-leads"] }),
  });
  const notYet = error instanceof ApiError && error.status === 503;
  const detail = error instanceof ApiError ? error.message : null;

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="flex items-center gap-2 text-sm">
        <Radar className="h-4 w-4 shrink-0 text-muted-foreground" />
        {notYet
          ? "Les pistes ne sont pas encore collectées : la première lecture part cette nuit à 02:15."
          : "Les pistes ne peuvent pas être lues pour l'instant."}
      </div>
      {!notYet && detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
      <p className="mt-2 text-xs text-muted-foreground">
        Cette page se rafraîchit toute seule dès que la liste existe.
      </p>
      {user?.is_superuser && (
        <div className="mt-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => collect.mutate()}
            disabled={collect.isPending || collect.isSuccess}
          >
            {collect.isSuccess ? "Collecte lancée, quelques minutes" : "Collecter maintenant"}
          </Button>
          {collect.error && (
            <p className="mt-2 text-xs text-[hsl(var(--loss))]">
              {collect.error instanceof Error ? collect.error.message : "Erreur inconnue"}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/* ── Dates ─────────────────────────────────────────────────────────────── */

function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `le ${d.toLocaleDateString("fr-FR", { day: "numeric", month: "long" })} à ${d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
}

function longDate(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  if (!y || !m || !d) return day;
  return new Date(y, m - 1, d).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
}
