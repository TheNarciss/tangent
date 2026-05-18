import type { PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  metrics: PortfolioMetrics;
}

export function Metrics({ metrics }: Props) {
  const pnlPositive = metrics.total_pnl >= 0;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <MetricCard label="Valorisation" value={fmt.eur(metrics.total_value)} sub={`Coût ${fmt.eur(metrics.total_cost)}`} />
      <MetricCard
        label="Plus-value"
        value={fmt.signedEur(metrics.total_pnl)}
        sub={fmt.signedPct(metrics.total_pnl_pct)}
        tone={pnlPositive ? "gain" : "loss"}
      />
      <MetricCard label="E(R) annuel" value={fmt.pct(metrics.expected_return)} sub="Espérance" />
      <MetricCard label="Volatilité σ" value={fmt.pct(metrics.volatility)} sub="Annualisée" />
      <MetricCard label="Sharpe" value={fmt.num(metrics.sharpe)} sub="vs. r_f = 2,5 %" />
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
