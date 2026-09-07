import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Banknote,
  Building2,
  Landmark,
  PiggyBank,
  RefreshCw,
  TrendingUp,
  Wallet,
} from "lucide-react";

import {
  useBankAccounts,
  useRefreshBankAccounts,
  useSyncBankAccounts,
  useWealthSummary,
  type BankAccountResponse,
} from "@/api";
import {
  GROUP_LABELS,
  GROUP_ORDER,
  TYPE_LABELS,
  accountValue,
  cleanName,
  groupOf,
  groupTotal,
  longDate,
  relativeTime,
  type AccountGroup,
} from "@/lib/accounts";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AccountDetailSheet } from "@/components/AccountDetailSheet";
import { BanksCard } from "@/components/BanksCard";

const GROUP_ICON: Record<AccountGroup, typeof Wallet> = {
  cash: Wallet,
  savings: PiggyBank,
  invest: TrendingUp,
  retirement: Landmark,
  employee: Building2,
  loan: Banknote,
  other: Banknote,
};

/**
 * Comptes — « Ton patrimoine » (one figure, from GET /wealth), then one card
 * per account grouped by family, one column on phones / two on desktop.
 * Tap a card for its detail (movements, positions, loan schedule) in a
 * bottom sheet. Banks are managed at the bottom of the page.
 */
export function Accounts() {
  const accounts = useBankAccounts();
  const wealth = useWealthSummary();
  const refresh = useRefreshBankAccounts();
  const sync = useSyncBankAccounts();
  const [selected, setSelected] = useState<BankAccountResponse | null>(null);

  // Synchronous in-flight guard: two rapid taps must not fire two POST /refresh.
  const syncInFlight = useRef(false);
  const startRefresh = useCallback(() => {
    if (syncInFlight.current) return;
    syncInFlight.current = true;
    refresh.mutate(undefined, {
      onSettled: () => {
        syncInFlight.current = false;
      },
    });
  }, [refresh]);

  // Auto-sync on mount when stale (> 5 min) via /accounts/sync (cached 5 min
  // server-side). /accounts/refresh (forces the bank) stays behind the button.
  const STALENESS_MINUTES = 5;
  const didAutoSync = useRef(false);
  useEffect(() => {
    if (didAutoSync.current || sync.isPending) return;
    if (!accounts.data || accounts.data.length === 0) return;
    const times = accounts.data
      .map((a) => a.last_synced_at)
      .filter((ts): ts is string => ts !== null)
      .map((ts) => new Date(ts).getTime());
    const stale =
      times.length === 0 || (Date.now() - Math.min(...times)) / 60_000 > STALENESS_MINUTES;
    if (stale) {
      didAutoSync.current = true;
      sync.mutate();
    }
  }, [accounts.data, sync]);

  const grouped = useMemo(() => {
    const out: Record<AccountGroup, BankAccountResponse[]> = {
      cash: [],
      savings: [],
      invest: [],
      retirement: [],
      employee: [],
      loan: [],
      other: [],
    };
    for (const a of accounts.data ?? []) out[groupOf(a.type)].push(a);
    return out;
  }, [accounts.data]);

  const lastSyncedAt = useMemo(() => {
    const times = (accounts.data ?? [])
      .map((a) => a.last_synced_at)
      .filter((ts): ts is string => ts !== null);
    return times.length ? times.sort().at(-1)! : null;
  }, [accounts.data]);

  const isSyncing = refresh.isPending || sync.isPending;
  const syncError = refresh.error ?? sync.error;
  const newMovements = refresh.data?.transactions_persisted ?? 0;
  const hasAccounts = !!accounts.data && accounts.data.length > 0;

  return (
    <div className="space-y-6">
      {/* ── Ton patrimoine ─────────────────────────────────────────────── */}
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Ton patrimoine
        </div>
        {wealth.data ? (
          <>
            <div
              className={cn(
                "mt-1 font-mono text-3xl font-semibold tabular md:text-4xl",
                wealth.data.net_worth < 0 && "text-[hsl(var(--loss))]",
              )}
            >
              {signedEur(wealth.data.net_worth)}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span>
                Ce que tu as :{" "}
                <span className="font-mono tabular text-foreground">
                  {fmt.eur(wealth.data.total_assets)}
                </span>
              </span>
              {wealth.data.total_liabilities > 0 && (
                <span>
                  Ce que tu dois :{" "}
                  <span className="font-mono tabular text-[hsl(var(--loss))]">
                    {fmt.eur(wealth.data.total_liabilities)}
                  </span>
                </span>
              )}
            </div>
          </>
        ) : (
          <div className="mt-2 h-9 w-48 animate-pulse rounded bg-muted/30" />
        )}

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-t pt-3 text-xs text-muted-foreground">
          <span>
            {isSyncing
              ? "Mise à jour en cours…"
              : hasAccounts
                ? `Mis à jour ${relativeTime(lastSyncedAt)}`
                : "Aucun compte pour l'instant"}
          </span>
          {newMovements > 0 && !isSyncing && (
            <span className="text-foreground">
              {newMovements} nouveau{newMovements > 1 ? "x" : ""} mouvement
              {newMovements > 1 ? "s" : ""}
            </span>
          )}
          {hasAccounts && (
            <Button
              variant="outline"
              size="sm"
              onClick={startRefresh}
              disabled={isSyncing}
              className="ml-auto gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", isSyncing && "animate-spin")} />
              Mettre à jour
            </Button>
          )}
        </div>
        {syncError && !isSyncing && (
          <p className="mt-2 text-sm text-[hsl(var(--loss))]">
            La mise à jour a échoué : {syncError instanceof Error ? syncError.message : "erreur"}.
            Réessaie dans un instant.
          </p>
        )}
      </section>

      {accounts.isLoading && (
        <div className="grid gap-3 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-muted/30" />
          ))}
        </div>
      )}
      {accounts.isError && (
        <p className="text-sm text-[hsl(var(--loss))]">
          Impossible de charger tes comptes :{" "}
          {accounts.error instanceof Error ? accounts.error.message : "erreur"}
        </p>
      )}
      {accounts.data && accounts.data.length === 0 && (
        <div className="rounded-xl border border-dashed py-12 text-center">
          <Banknote className="mx-auto h-8 w-8 text-muted-foreground" />
          <p className="mt-2 text-sm text-muted-foreground">Aucune banque connectée.</p>
          <p className="text-xs text-muted-foreground">
            Utilise <strong>+ Ajouter une banque</strong> en haut de la page pour commencer.
          </p>
        </div>
      )}

      {/* ── Groups of cards ────────────────────────────────────────────── */}
      {hasAccounts &&
        GROUP_ORDER.map((g) => {
          const list = grouped[g];
          if (list.length === 0) return null;
          const Icon = GROUP_ICON[g];
          const total = groupTotal(list);
          return (
            <section key={g} className="space-y-2">
              <div className="flex items-baseline justify-between px-1">
                <h2 className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-muted-foreground">
                  <Icon className="h-4 w-4" />
                  {GROUP_LABELS[g]}
                </h2>
                <span
                  className={cn(
                    "font-mono text-sm tabular",
                    g === "loan" && "text-[hsl(var(--loss))]",
                  )}
                >
                  {g === "loan" ? `−${fmt.eur(total)}` : fmt.eur(total)}
                </span>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {list.map((a) => (
                  <AccountCard key={a.id} account={a} onOpen={() => setSelected(a)} />
                ))}
              </div>
            </section>
          );
        })}

      <BanksCard />

      <AccountDetailSheet account={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

/* ── Card ─────────────────────────────────────────────────────────────── */

function AccountCard({ account, onOpen }: { account: BankAccountResponse; onOpen: () => void }) {
  const group = groupOf(account.type);
  const value = accountValue(account);
  const isLoan = group === "loan";
  const gain = !isLoan && group !== "cash" && group !== "savings" ? account.diff : null;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex min-h-[72px] w-full items-center gap-3 rounded-xl border bg-card px-4 py-3 text-left transition-colors hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{cleanName(account.name)}</div>
        <div className="truncate text-xs text-muted-foreground">
          {TYPE_LABELS[account.type]}
          {account.institution_name ? ` · ${account.institution_name}` : ""}
        </div>
        {isLoan && account.loan?.next_payment_date && account.loan.next_payment_amount ? (
          <div className="mt-0.5 truncate text-xs text-muted-foreground">
            Prochaine mensualité {fmt.eur(account.loan.next_payment_amount)} le{" "}
            {longDate(account.loan.next_payment_date)}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 text-right">
        <div className={cn("font-mono text-base tabular", isLoan && "text-[hsl(var(--loss))]")}>
          {isLoan ? `−${fmt.eur(value)}` : fmt.eur(value)}
        </div>
        {gain !== null && gain !== undefined && (
          <div
            className={cn(
              "font-mono text-xs tabular",
              gain >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
            )}
          >
            {fmt.signedEur(gain)}
            {account.diff_percent !== null && (
              <span className="hidden sm:inline"> ({fmt.signedPct(account.diff_percent)})</span>
            )}
          </div>
        )}
      </div>
    </button>
  );
}

function signedEur(v: number): string {
  return v < 0 ? `−${fmt.eur(-v)}` : fmt.eur(v);
}
