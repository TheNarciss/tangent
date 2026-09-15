import { useRecentTransactions } from "@/api";
import { useT } from "@/i18n";
import { shortDate } from "@/lib/accounts";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";

interface RecentTransactionsTileProps {
  /** Callback when user taps "Tout voir" — typically navigates to Comptes. */
  onSeeAll?: () => void;
  /** Number of transactions to fetch + display (default 5). */
  limit?: number;
}

/**
 * Recent transactions tile — the last N movements across ALL bank accounts
 * of the user, with account name + date for context. Tap "Tout voir" to
 * navigate to the full Comptes view (which has filtering, search, etc.).
 *
 * Powered by GET /api/accounts/transactions/recent — a single query
 * joined with BankAccount, no N+1 fetches.
 */
export function RecentTransactionsTile({ onSeeAll, limit = 5 }: RecentTransactionsTileProps) {
  const { t } = useT();
  const { data: txns, isLoading } = useRecentTransactions(limit);

  return (
    <div className="rounded-lg border border-border bg-card p-4 md:p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {t("dashboard.recent.title")}
        </div>
        {onSeeAll && (
          <button type="button" onClick={onSeeAll} className="text-xs text-primary hover:underline">
            {t("dashboard.recent.seeAll")}
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-muted/30" />
          ))}
        </div>
      ) : !txns || txns.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("dashboard.recent.empty")}</p>
      ) : (
        <div className="space-y-2">
          {txns.map((txn) => (
            <div key={txn.id} className="flex items-center justify-between gap-3 text-sm">
              <div className="min-w-0 flex-1">
                <div className="truncate">{txn.description || t("common.none")}</div>
                <div className="truncate text-[10px] text-muted-foreground">
                  {txn.bank_account_name} · {shortDate(txn.transaction_date)}
                </div>
              </div>
              <div
                className={cn(
                  "flex-shrink-0 font-mono text-sm tabular",
                  txn.amount >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                )}
              >
                {txn.amount >= 0 ? "+" : ""}
                {fmt.eur(txn.amount)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
