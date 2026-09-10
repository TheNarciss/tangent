import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { ApiError, useDashboard, type AssetMetrics, type PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PlacementsAdvanced } from "@/components/PlacementsAdvanced";
import { NAV_PATHS } from "@/components/Sidebar";

const COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6", "#10b981"];

/**
 * « Mes placements » answers one question: **qu'est-ce que je détiens ?**
 *
 * What to do about it — risk, fees, duplicates, what to buy next — belongs to
 * the Méthode screen, and to it alone (ADR-028). Three engines used to speak
 * here at once: the verdicts, a rule-based diagnostic and the optimiser. They
 * contradicted each other in front of the user, one saying « rien à changer »
 * while the next proposed selling everything.
 *
 * Everything quantitative (μ/σ, scatter, matrix, full optimizer) stays folded
 * under « Mode avancé ».
 */
export function Placements() {
  const dashboard = useDashboard();

  if (dashboard.isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-xl bg-muted/30" />
        ))}
      </div>
    );
  }
  if (dashboard.isError || !dashboard.data) {
    const err = dashboard.error;
    const empty = err instanceof ApiError && err.type === "portfolio_empty";
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <p className="text-sm font-medium">
          {empty ? "Pas encore de placements" : "Analyse indisponible pour l'instant"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {empty
            ? "Connecte un compte-titres, un PEA ou une assurance vie pour voir cette page."
            : err instanceof Error
              ? err.message
              : "Réessaie dans un instant."}
        </p>
      </div>
    );
  }

  const m = dashboard.data.metrics;
  return (
    <div className="space-y-6">
      <WhatIHave metrics={m} />
      <Link
        to={NAV_PATHS.method}
        className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent/30 md:px-6"
      >
        <Compass className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="min-w-0 flex-1 leading-snug">
          Ce qu'il faut en faire : risque, frais, doublons, prochain versement.
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">Méthode</span>
      </Link>
      <PlacementsAdvanced dashboard={dashboard.data} />
    </div>
  );
}

/* ── 1. Qu'est-ce que j'ai ? ──────────────────────────────────────────── */

function WhatIHave({ metrics }: { metrics: PortfolioMetrics }) {
  const assets = [...metrics.assets].sort((a, b) => b.weight - a.weight);
  const gain = metrics.total_pnl;
  return (
    <Block title="Ce que j'ai">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-mono text-3xl font-semibold tabular">
          {fmt.eur(metrics.total_value)}
        </span>
        <span
          className={cn(
            "font-mono text-sm tabular",
            gain >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
          )}
        >
          {fmt.signedEur(gain)} depuis l'achat ({fmt.signedPct(metrics.total_pnl_pct)})
        </span>
      </div>

      {/* One allocation bar */}
      <div className="mt-4 flex h-3 w-full overflow-hidden rounded-full bg-muted/30">
        {assets.map((a, i) => (
          <div
            key={a.ticker}
            style={{ width: `${a.weight * 100}%`, background: COLORS[i % COLORS.length] }}
            title={`${name(a)} · ${fmt.pct(a.weight)}`}
          />
        ))}
      </div>

      <ul className="mt-3 divide-y rounded-md border text-sm">
        {assets.map((a, i) => (
          <li key={a.ticker} className="flex items-center gap-3 px-3 py-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: COLORS[i % COLORS.length] }}
            />
            <div className="min-w-0 flex-1">
              <div className="truncate">{name(a)}</div>
              <div className="text-xs text-muted-foreground">
                {fmt.pct(a.weight)} de tes placements
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className="font-mono tabular">{fmt.eur(a.value)}</div>
              <div
                className={cn(
                  "font-mono text-xs tabular",
                  a.pnl >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                )}
              >
                {fmt.signedEur(a.pnl)}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Block>
  );
}

/* ── Atoms ─────────────────────────────────────────────────────────────── */

function name(a: AssetMetrics): string {
  return a.label ?? a.ticker;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <h2 className="mb-3 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}
