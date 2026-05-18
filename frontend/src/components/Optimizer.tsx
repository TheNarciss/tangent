import type { UseQueryResult } from "@tanstack/react-query";
import { ArrowRight, TrendingDown, TrendingUp } from "lucide-react";

import type { OptimizerObjective, OptimizerResponse, RiskContribution } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Props {
  objective: OptimizerObjective;
  onObjectiveChange: (o: OptimizerObjective) => void;
  query: UseQueryResult<OptimizerResponse>;
}

const ASSET_COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6"];

const OBJECTIVE_DESCRIPTIONS: Record<OptimizerObjective, string> = {
  max_sharpe: "Maximise (μ − r_f) / σ. Cherche le meilleur compromis rendement/risque.",
  min_variance: "Minimise σ. Le portefeuille le moins volatil possible, peu importe le rendement.",
};

export function Optimizer({ objective, onObjectiveChange, query }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Optimisation
        </CardTitle>
        <CardDescription>
          Solveur SLSQP sous contraintes long-only, sum(w)=1. {OBJECTIVE_DESCRIPTIONS[objective]}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-3 items-end">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Objectif</Label>
            <Select value={objective} onValueChange={(v: string) => onObjectiveChange(v as OptimizerObjective)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="max_sharpe">Max Sharpe</SelectItem>
                <SelectItem value="min_variance">Min variance</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {query.isLoading && <p className="text-sm text-muted-foreground">Optimisation en cours…</p>}
        {query.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">Erreur : {(query.error as Error).message}</p>
        )}

        {query.data && (
          <>
            <ComparisonTable data={query.data} />
            <ActionsList data={query.data} />
            <RiskContributions data={query.data} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* ─── Comparaison ────────────────────────────────────────────────────────── */

function ComparisonTable({ data }: { data: OptimizerResponse }) {
  const deltaSharpe = data.optimal.sharpe - data.current.sharpe;
  const deltaMu = data.optimal.expected_return - data.current.expected_return;
  const deltaSigma = data.optimal.volatility - data.current.volatility;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
            <th className="text-left py-2 pr-4 font-medium">Métrique</th>
            <th className="text-right py-2 px-3 font-medium">Actuel</th>
            <th className="text-right py-2 px-3 font-medium">Optimal</th>
            <th className="text-right py-2 pl-3 font-medium">Δ</th>
          </tr>
        </thead>
        <tbody className="font-mono tabular">
          <CompareRow label="Rendement μ" current={fmt.pct(data.current.expected_return)}
                      optimal={fmt.pct(data.optimal.expected_return)}
                      delta={fmt.signedPct(deltaMu)} deltaSign={deltaMu} />
          <CompareRow label="Volatilité σ" current={fmt.pct(data.current.volatility)}
                      optimal={fmt.pct(data.optimal.volatility)}
                      delta={fmt.signedPct(deltaSigma)} deltaSign={-deltaSigma} />
          <CompareRow label="Sharpe" current={data.current.sharpe.toFixed(2)}
                      optimal={data.optimal.sharpe.toFixed(2)}
                      delta={(deltaSharpe >= 0 ? "+" : "") + deltaSharpe.toFixed(2)} deltaSign={deltaSharpe} bold />
        </tbody>
      </table>
    </div>
  );
}

function CompareRow({
  label, current, optimal, delta, deltaSign, bold,
}: {
  label: string; current: string; optimal: string; delta: string; deltaSign: number; bold?: boolean;
}) {
  const color = Math.abs(deltaSign) < 1e-6
    ? "text-muted-foreground"
    : deltaSign > 0
      ? "text-[hsl(var(--gain))]"
      : "text-[hsl(var(--loss))]";

  return (
    <tr className="border-b last:border-0">
      <td className="py-2 pr-4 font-sans text-muted-foreground">{label}</td>
      <td className="text-right py-2 px-3">{current}</td>
      <td className={cn("text-right py-2 px-3", bold && "font-semibold")}>{optimal}</td>
      <td className={cn("text-right py-2 pl-3", color, bold && "font-semibold")}>{delta}</td>
    </tr>
  );
}

/* ─── Actions ────────────────────────────────────────────────────────────── */

function ActionsList({ data }: { data: OptimizerResponse }) {
  return (
    <div>
      <h4 className="text-xs uppercase tracking-wider text-muted-foreground mb-3">Actions de rebalancement</h4>
      <ul className="space-y-2">
        {data.actions.map((a) => {
          const sign = a.delta_value > 0.5 ? "buy" : a.delta_value < -0.5 ? "sell" : "hold";
          const Icon = sign === "buy" ? TrendingUp : sign === "sell" ? TrendingDown : null;
          const verb = sign === "buy" ? "Achète" : sign === "sell" ? "Vends" : "Conserve";
          const color = sign === "buy" ? "text-[hsl(var(--gain))]" : sign === "sell" ? "text-[hsl(var(--loss))]" : "text-muted-foreground";

          return (
            <li key={a.ticker}
                className="flex items-center justify-between gap-4 rounded-md border bg-card/50 px-3 py-2">
              <div className="flex items-center gap-2 font-mono">
                <span className="font-medium">{a.ticker}</span>
                <span className="text-muted-foreground tabular">{fmt.pct(a.current_weight)}</span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="tabular">{fmt.pct(a.optimal_weight)}</span>
              </div>
              <div className={cn("flex items-center gap-1.5 text-sm font-mono tabular", color)}>
                {Icon && <Icon className="h-3.5 w-3.5" />}
                <span>{verb} {fmt.eur(Math.abs(a.delta_value))}</span>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">
        Montants calculés sur la valorisation actuelle. Sur 3 actifs corrélés (ρ ≈ 0,9 entre DCAM et PUST),
        la solution optimale tend vers une concentration sur l'actif au meilleur Sharpe historique — c'est mathématiquement
        attendu, pas une vraie recommandation à appliquer telle quelle.
      </p>
    </div>
  );
}

/* ─── Risk contributions ─────────────────────────────────────────────────── */

function RiskContributions({ data }: { data: OptimizerResponse }) {
  return (
    <div className="space-y-3">
      <h4 className="text-xs uppercase tracking-wider text-muted-foreground">Contribution à la volatilité σ</h4>
      <div className="space-y-2">
        <RiskBar label="Actuel" rc={data.risk_contributions_current} tickers={data.tickers} />
        <RiskBar label="Optimal" rc={data.risk_contributions_optimal} tickers={data.tickers} />
      </div>
      <p className="text-xs text-muted-foreground">
        Décomposition d'Euler : σ<sub>p</sub> = Σ w<sub>i</sub> · (Σw)<sub>i</sub> / σ<sub>p</sub>.
        Indique quels actifs <em>pilotent</em> réellement le risque du portefeuille
        (pondéré par leur covariance, pas seulement par leur poids).
      </p>
    </div>
  );
}

function RiskBar({ label, rc, tickers }: { label: string; rc: RiskContribution; tickers: string[] }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
      </div>
      <div className="flex h-6 w-full rounded overflow-hidden border">
        {rc.fraction.map((f, i) => {
          if (f < 0.005) return null;
          return (
            <div
              key={tickers[i]}
              className="flex items-center justify-center text-[10px] font-mono tabular text-black/80"
              style={{
                width: `${f * 100}%`,
                background: ASSET_COLORS[i % ASSET_COLORS.length],
              }}
              title={`${tickers[i]} : ${(f * 100).toFixed(1)}% du risque total`}
            >
              {f >= 0.08 ? `${tickers[i]} ${(f * 100).toFixed(0)}%` : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}