import type { PortfolioMetrics } from "@/api";
import { useT } from "@/i18n";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  metrics: PortfolioMetrics;
}

export function Metrics({ metrics }: Props) {
  const { t } = useT();
  const pnlPositive = metrics.total_pnl >= 0;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <MetricCard
          label={t("investments.metrics.value")}
          value={fmt.eur(metrics.total_value)}
          sub={t("investments.metrics.cost", { value: fmt.eur(metrics.total_cost) })}
        />
        <MetricCard
          label={t("investments.metrics.pnl")}
          value={fmt.signedEur(metrics.total_pnl)}
          sub={fmt.signedPct(metrics.total_pnl_pct)}
          tone={pnlPositive ? "gain" : "loss"}
        />
        <MetricCard
          label={t("investments.metrics.expectedReturn")}
          value={fmt.pct(metrics.expected_return)}
          sub={t("investments.metrics.expectedReturnSub")}
        />
        <MetricCard
          label={t("investments.metrics.volatility")}
          value={fmt.pct(metrics.volatility)}
          sub={t("investments.metrics.annualised")}
        />
        <MetricCard
          label={t("investments.metrics.sharpe")}
          value={fmt.num(metrics.sharpe)}
          sub={t("investments.metrics.sharpeSub")}
        />
      </div>

      {metrics.unmapped_tickers.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("investments.unmapped", { tickers: metrics.unmapped_tickers.join(", ") })}
        </p>
      )}

      <div className="grid gap-3 rounded-lg border bg-muted/20 p-3">
        <RiskCard
          label={t("investments.metrics.worstDrop")}
          value={fmt.signedPct(metrics.max_drawdown_observed)}
          hint={t("investments.metrics.worstDropHint")}
        />
      </div>
    </div>
  );
}

interface CardProps {
  label: string;
  value: string;
  sub: string;
  tone?: "gain" | "loss";
}

function MetricCard({ label, value, sub, tone }: CardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div
          className={cn(
            "font-mono text-2xl font-semibold tabular tracking-tight",
            tone === "gain" && "text-[hsl(var(--gain))]",
            tone === "loss" && "text-[hsl(var(--loss))]",
          )}
        >
          {value}
        </div>
        <div className="font-mono text-xs text-muted-foreground tabular">{sub}</div>
      </CardContent>
    </Card>
  );
}

function RiskCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-lg font-semibold tabular text-[hsl(var(--loss))]">{value}</div>
      <div className="text-xs text-muted-foreground italic">{hint}</div>
    </div>
  );
}
