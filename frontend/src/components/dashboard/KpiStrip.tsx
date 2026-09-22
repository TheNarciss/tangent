import { useEffect } from "react";

import type { WealthSummary } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { useT } from "@/i18n";
import { fmt } from "@/lib/format";
import { publishWidgetSnapshot } from "@/native/widget";

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
 *
 * On the phone, the net worth tile is also what the home-screen widget
 * shows: the same words, the same amount, handed over as they are written
 * here (ADR-035).
 */
export function KpiStrip({ wealth }: KpiStripProps) {
  const { t } = useT();
  const cash = wealth.checking_total + wealth.envelopes_total;
  const invest = wealth.investments_total + wealth.pea_cash_total;
  const debts = wealth.total_liabilities;
  const pnl = wealth.unrealized_pnl;

  const netWorthLabel = t("dashboard.kpi.netWorth");
  const netWorthValue = fmt.eur(wealth.net_worth);
  const debtsLine = debts > 0 ? t("dashboard.kpi.debts", { amount: fmt.eur(debts) }) : undefined;

  useEffect(() => {
    void publishWidgetSnapshot({
      label: netWorthLabel,
      value: netWorthValue,
      sub: debtsLine,
      positive: debtsLine ? false : undefined,
    });
  }, [netWorthLabel, netWorthValue, debtsLine]);

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
      <BentoTile
        label={netWorthLabel}
        value={netWorthValue}
        sub={debtsLine ? <span className="text-muted-foreground">{debtsLine}</span> : undefined}
        size="lg"
        className="col-span-2"
      />
      <BentoTile label={t("dashboard.kpi.cash")} value={fmt.eur(cash)} />
      <BentoTile
        label={t("dashboard.kpi.investments")}
        value={fmt.eur(invest)}
        sub={
          pnl !== 0 ? (
            <span className={pnl >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]"}>
              {t("dashboard.kpi.pnl", { amount: `${pnl >= 0 ? "+" : ""}${fmt.eur(pnl)}` })}
            </span>
          ) : undefined
        }
      />
    </div>
  );
}
