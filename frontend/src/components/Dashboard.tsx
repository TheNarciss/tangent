import { useWealthSummary } from "@/api";

import { AiBriefTile } from "./dashboard/AiBriefTile";
import { ChartTile } from "./dashboard/ChartTile";
import { KpiStrip } from "./dashboard/KpiStrip";
import { RecentTransactionsTile } from "./dashboard/RecentTransactionsTile";

interface DashboardProps {
  /** Called when user taps "Tout voir" on the transactions tile. */
  onNavigateToAccounts?: () => void;
}

/**
 * Main dashboard view — the bento layout that replaces the old AI tab.
 *
 * Combines:
 *   - Patrimony summary (KPI tiles, KpiStrip)
 *   - Portfolio sparkline (90-day, tap to expand full Timeline)
 *   - Today's AI brief (preview, tap to expand full markdown)
 *   - Recent transactions across all accounts (5 latest)
 *
 * Adaptive: bento grid on desktop (≥768px), single-column stacked on
 * mobile with KPIs in a 2-col grid (Net worth full-width on top).
 *
 * Data: `useWealthSummary()` (GET /wealth, DB only) powers the KPI strip,
 * so the patrimony figures show even when market data is unavailable.
 * Sparkline, AI brief, and transactions each have their own dedicated
 * query (different cache key, independent refetch).
 */
export function Dashboard({ onNavigateToAccounts }: DashboardProps = {}) {
  const { data: wealth, isLoading, error } = useWealthSummary();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !wealth) {
    return <DashboardEmptyState />;
  }

  return (
    <div className="space-y-3 md:space-y-4">
      <KpiStrip wealth={wealth} />
      <div className="grid gap-3 md:grid-cols-3 md:gap-4">
        <ChartTile className="md:col-span-2" />
        <AiBriefTile />
      </div>
      <RecentTransactionsTile onSeeAll={onNavigateToAccounts} />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-3 md:space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <div className="col-span-2 h-28 animate-pulse rounded-lg bg-muted/30" />
        <div className="h-28 animate-pulse rounded-lg bg-muted/30" />
        <div className="h-28 animate-pulse rounded-lg bg-muted/30" />
      </div>
      <div className="grid gap-3 md:grid-cols-3 md:gap-4">
        <div className="h-48 animate-pulse rounded-lg bg-muted/30 md:col-span-2" />
        <div className="h-48 animate-pulse rounded-lg bg-muted/30" />
      </div>
      <div className="h-56 animate-pulse rounded-lg bg-muted/30" />
    </div>
  );
}

function DashboardEmptyState() {
  return (
    <div className="rounded-lg border border-border bg-card p-8 text-center">
      <h2 className="mb-2 text-lg font-semibold">Bienvenue sur Tangent</h2>
      <p className="text-sm text-muted-foreground">
        Connecte ton premier compte bancaire pour voir ton patrimoine ici.
      </p>
    </div>
  );
}
