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
import { t, useT, type MessageKey } from "@/i18n";
import { formatDate } from "@/lib/accounts";
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
const SOURCES = [
  "all",
  "polymarket",
  "kalshi",
  "edgar_form4",
  "edgar_13f",
  "edgar_13d",
  "cftc",
] as const;

export function MarketLeads() {
  const { t } = useT();
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
        {SOURCES.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setSource(key)}
            className={cn(
              "rounded px-2.5 py-1",
              source === key ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {key === "all" ? t("market.leads.filter.all") : sourceLabel(key)}
            <span className={cn("ml-1", source === key ? "opacity-80" : "text-muted-foreground")}>
              {key === "all" ? data.leads.length : (counts[key] ?? 0)}
            </span>
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <section className="rounded-xl border bg-card p-4 md:p-6">
          <p className="text-sm text-muted-foreground">{t("market.leads.emptySource")}</p>
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
  const { t, tn } = useT();
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <p className="text-sm">
        {t("market.leads.introBefore")}
        <strong>{t("market.leads.introStrong")}</strong>
        {t("market.leads.introAfter")}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">{t("market.leads.noise")}</p>
      <p className="mt-3 text-xs text-muted-foreground">
        {tn("market.leads.collected", total, { when: when(computedAt) })}{" "}
        {t("market.leads.nextCollection")}
      </p>
    </section>
  );
}

/* ── One lead ──────────────────────────────────────────────────────────── */

const SOURCE_KEYS: Record<MarketLeadSource, MessageKey> = {
  polymarket: "market.leads.source.polymarket",
  kalshi: "market.leads.source.kalshi",
  edgar_form4: "market.leads.source.edgar_form4",
  edgar_13f: "market.leads.source.edgar_13f",
  edgar_13d: "market.leads.source.edgar_13d",
  cftc: "market.leads.source.cftc",
};

const KIND_KEYS: Record<string, MessageKey> = {
  prediction_move: "market.leads.kind.prediction_move",
  prediction_state: "market.leads.kind.prediction_state",
  insider_cluster: "market.leads.kind.insider_cluster",
  insider_buy: "market.leads.kind.insider_buy",
  fund_new_position: "market.leads.kind.fund_new_position",
  fund_exit: "market.leads.kind.fund_exit",
  fund_change: "market.leads.kind.fund_change",
  activist_stake: "market.leads.kind.activist_stake",
  positioning_extreme: "market.leads.kind.positioning_extreme",
  positioning_flip: "market.leads.kind.positioning_flip",
};

function sourceLabel(source: MarketLeadSource): string {
  return t(SOURCE_KEYS[source]);
}

function kindLabel(kind: string): string {
  const key = KIND_KEYS[kind];
  return key ? t(key) : kind;
}

function LeadCard({ lead }: { lead: MarketLead }) {
  const { t } = useT();
  return (
    <li className="rounded-xl border bg-card p-4 md:px-6">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span className="rounded-sm border px-1.5 py-0.5">{sourceLabel(lead.source)}</span>
        <span>{kindLabel(lead.kind)}</span>
        <span className="ml-auto normal-case tracking-normal">{dayLabel(lead.observed_at)}</span>
      </div>
      <p className="mt-2 text-sm font-medium">{lead.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{lead.detail}</p>
      <a
        href={lead.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground hover:underline"
      >
        {t("market.leads.viewSource")}
        <ExternalLink className="h-3 w-3" />
      </a>
    </li>
  );
}

/* ── Before the first collection ───────────────────────────────────────── */

function NotYet({ error }: { error: unknown }) {
  const { t } = useT();
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
        {notYet ? t("market.leads.notYet") : t("market.leads.unavailable")}
      </div>
      {!notYet && detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
      <p className="mt-2 text-xs text-muted-foreground">{t("market.leads.autoRefresh")}</p>
      {user?.is_superuser && (
        <div className="mt-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => collect.mutate()}
            disabled={collect.isPending || collect.isSuccess}
          >
            {collect.isSuccess ? t("market.leads.collectStarted") : t("market.leads.collectNow")}
          </Button>
          {collect.error && (
            <p className="mt-2 text-xs text-[hsl(var(--loss))]">
              {collect.error instanceof Error
                ? collect.error.message
                : t("market.leads.unknownError")}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/* ── Dates ─────────────────────────────────────────────────────────────── */

/** « le 3 mars à 02:15 » — when the collection ran. */
function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return t("market.leads.when", {
    date: formatDate(iso, { day: "numeric", month: "long" }),
    time: formatDate(iso, { hour: "2-digit", minute: "2-digit" }),
  });
}

/** « 3 mars » from a `YYYY-MM-DD` day, read as a local date so the day never shifts. */
function dayLabel(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  if (!y || !m || !d) return day;
  return formatDate(new Date(y, m - 1, d).toISOString(), { day: "numeric", month: "long" });
}
