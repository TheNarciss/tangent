import type { WealthSummary } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { fmt } from "@/lib/format";

interface KpiStripProps {
  wealth: WealthSummary;
}

/**
 * Top KPI strip — net worth dominates, cash and investments balance out.
 *
 * Layout:
 *   - Mobile (grid-cols-2): Net worth spans both cols (full width), then
 *     Cash + Invest sit on a single row below.
 *   - Desktop (grid-cols-4): Net worth spans 2 of 4 cols, then Cash +
 *     Invest take 1 col each.
 *
 * Unrealized P&L is shown as a sub-line on the Invest tile (signed,
 * colored). Total liabilities, if any, appear as a sub-line on the Net
 * worth tile.
 */
export function KpiStrip({ wealth }: KpiStripProps) {
  const cash = wealth.checking_total + wealth.envelopes_total;
  const invest = wealth.investments_total + wealth.pea_cash_total;
  const debts = wealth.total_liabilities;
  const pnl = wealth.unrealized_pnl;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
      <BentoTile
        label="Patrimoine net"
        value={fmt.eur(wealth.net_worth)}
        sub={
          debts > 0 ? (
            <span className="text-muted-foreground">−{fmt.eur(debts)} de dettes</span>
          ) : undefined
        }
        size="lg"
        className="col-span-2"
      />
      <BentoTile label="Cash" value={fmt.eur(cash)} />
      <BentoTile
        label="Investissements"
        value={fmt.eur(invest)}
        sub={
          pnl !== 0 ? (
            <span className={pnl >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]"}>
              {pnl >= 0 ? "+" : ""}
              {fmt.eur(pnl)} P&L latent
            </span>
          ) : undefined
        }
      />
    </div>
  );
}
