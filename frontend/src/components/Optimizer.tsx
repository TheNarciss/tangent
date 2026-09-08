import type { UseQueryResult } from "@tanstack/react-query";
import { ArrowRight, TrendingDown, TrendingUp, Wallet } from "lucide-react";

import type { OptimizerObjective, OptimizerResponse, RiskContribution } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Props {
  objective: OptimizerObjective;
  onObjectiveChange: (o: OptimizerObjective) => void;
  includeEnvelopes: boolean;
  onIncludeEnvelopesChange: (v: boolean) => void;
  totalCapital: number | "";
  onTotalCapitalChange: (v: number | "") => void;
  maxVolatility: number | "";
  onMaxVolatilityChange: (v: number | "") => void;
  hasProfile: boolean;
  query: UseQueryResult<OptimizerResponse>;
  profileTargetReturn: number;
  profileMaxVol: number;
}

const ETF_COLORS = ["#60a5fa", "#a78bfa", "#22d3ee", "#f472b6", "#facc15"];
const ENVELOPE_COLOR = "#10b981";

const OBJECTIVE_DESCRIPTIONS: Record<OptimizerObjective, string> = {
  from_strategy:
    "Maximise Sharpe sous tes contraintes σ ≤ vol max ET μ ≥ rendement cible (depuis ton profil). Te dit si ton intention est atteignable.",
  target_volatility:
    "Maximise μ sous contrainte σ_p ≤ cible. C'est ici que livrets et ETFs se mixent vraiment.",
  max_sharpe:
    "Maximise (μ − r_f) / σ. Sans contrainte de risque, l'optimiseur sature les actifs à plus haut ratio.",
  min_variance: "Minimise σ. Le portefeuille le moins volatil possible, peu importe le rendement.",
};

export function Optimizer({
  objective,
  onObjectiveChange,
  includeEnvelopes,
  onIncludeEnvelopesChange,
  totalCapital,
  onTotalCapitalChange,
  maxVolatility,
  onMaxVolatilityChange,
  hasProfile,
  query,
  profileTargetReturn,
  profileMaxVol,
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Optimisation
        </CardTitle>
        <CardDescription>
          Solveur SLSQP long-only, sum(w)=1. {OBJECTIVE_DESCRIPTIONS[objective]}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Objectif</Label>
            <Select
              value={objective}
              onValueChange={(v: string) => onObjectiveChange(v as OptimizerObjective)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="from_strategy">Selon ma stratégie</SelectItem>
                <SelectItem value="target_volatility">Cible vol max</SelectItem>
                <SelectItem value="max_sharpe">Max Sharpe</SelectItem>
                <SelectItem value="min_variance">Min variance</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {objective === "target_volatility" && (
            <NumberInput
              label="σ max (% /an)"
              value={maxVolatility}
              onChange={onMaxVolatilityChange}
              min={0}
              max={50}
              step={0.5}
              hint="Pré-rempli depuis ton profil. 5 %=prudent · 15 %=actions"
            />
          )}
          {objective === "from_strategy" && (
            <div className="space-y-1 col-span-1 sm:col-span-2 lg:col-span-1">
              <Label className="text-xs text-muted-foreground">Contraintes (profil)</Label>
              <div className="h-9 flex items-center px-3 rounded-md border bg-card/50 text-xs font-mono tabular">
                {hasProfile ? (
                  <span>
                    μ ≥ <strong>{profileTargetReturn}%</strong> · σ ≤{" "}
                    <strong>{profileMaxVol}%</strong>
                  </span>
                ) : (
                  <span className="text-[hsl(var(--loss))]">Renseigne ton profil</span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground">
                Modifie via l'icône profil en haut
              </p>
            </div>
          )}

          <ToggleField
            label="Inclure mes livrets"
            checked={includeEnvelopes}
            onChange={onIncludeEnvelopesChange}
            disabled={!hasProfile}
            hint={
              hasProfile ? "Selon ton profil + plafonds restants" : "Renseigne ton profil d'abord"
            }
          />

          <NumberInput
            label="Capital total (€)"
            value={totalCapital}
            onChange={onTotalCapitalChange}
            min={0}
            step={1000}
            hint="Pool sur lequel répartir. Défaut = portefeuille actuel"
            allowEmpty
          />
        </div>

        {query.isLoading && <p className="text-sm text-muted-foreground">Optimisation en cours…</p>}
        {query.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">
            Erreur : {(query.error as Error).message}
          </p>
        )}

        {query.data && (
          <>
            <ComparisonTable data={query.data} />
            <ActionsList data={query.data} />
            <RiskContributions data={query.data} />
            {query.data.unmapped_tickers.length > 0 && (
              <p className="text-xs text-muted-foreground italic border-l-2 border-muted pl-3">
                Sans hypothèse de rendement long terme, estimé sur l'historique seul :{" "}
                {query.data.unmapped_tickers.join(", ")}.
              </p>
            )}
            {includeEnvelopes && objective === "max_sharpe" && (
              <p className="text-xs text-muted-foreground italic border-l-2 border-muted pl-3">
                Note : avec livrets et <em>max Sharpe</em> sans contrainte de risque, le solveur
                sature les livrets (σ ≈ 0, Sharpe ≈ ∞). Honnête mais peu nuancé. Passe en{" "}
                <strong>« Selon ma stratégie »</strong> ou
                <strong> « Cible vol max »</strong> pour un vrai mix livrets + ETFs.
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* ─── Inputs ─────────────────────────────────────────────────────────────── */

function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
  step,
  hint,
  allowEmpty,
}: {
  label: string;
  value: number | "";
  onChange: (v: number | "") => void;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  allowEmpty?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
          const raw = e.target.value;
          if (raw === "" && allowEmpty) onChange("");
          else {
            const n = Number(raw);
            onChange(Number.isFinite(n) ? n : "");
          }
        }}
      />
      {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
  disabled,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "h-9 w-full rounded-md border px-3 text-sm font-mono tabular text-left",
          disabled
            ? "opacity-40 cursor-not-allowed bg-muted/30"
            : checked
              ? "bg-[hsl(var(--gain))]/15 border-[hsl(var(--gain))] text-foreground"
              : "hover:bg-muted/40",
        )}
      >
        {checked ? "✓ activé" : "○ désactivé"}
      </button>
      {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

/* ─── Comparison ────────────────────────────────────────────────────────── */

function ComparisonTable({ data }: { data: OptimizerResponse }) {
  const dSharpe = data.optimal.sharpe - data.current.sharpe;
  const dMu = data.optimal.expected_return - data.current.expected_return;
  const dSigma = data.optimal.volatility - data.current.volatility;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
            <th className="text-left py-2 pr-4 font-medium">Métrique</th>
            <th className="text-right py-2 px-3 font-medium">Actuel (ETF seuls)</th>
            <th className="text-right py-2 px-3 font-medium">Optimal</th>
            <th className="text-right py-2 pl-3 font-medium">Δ</th>
          </tr>
        </thead>
        <tbody className="font-mono tabular">
          <CompareRow
            label="Rendement μ"
            current={fmt.pct(data.current.expected_return)}
            optimal={fmt.pct(data.optimal.expected_return)}
            delta={fmt.signedPct(dMu)}
            sign={dMu}
          />
          <CompareRow
            label="Volatilité σ"
            current={fmt.pct(data.current.volatility)}
            optimal={fmt.pct(data.optimal.volatility)}
            delta={fmt.signedPct(dSigma)}
            sign={-dSigma}
          />
          <CompareRow
            label="Sharpe"
            current={data.current.sharpe.toFixed(2)}
            optimal={data.optimal.sharpe.toFixed(2)}
            delta={(dSharpe >= 0 ? "+" : "") + dSharpe.toFixed(2)}
            sign={dSharpe}
            bold
          />
        </tbody>
      </table>
    </div>
  );
}

function CompareRow({
  label,
  current,
  optimal,
  delta,
  sign,
  bold,
}: {
  label: string;
  current: string;
  optimal: string;
  delta: string;
  sign: number;
  bold?: boolean;
}) {
  const color =
    Math.abs(sign) < 1e-6
      ? "text-muted-foreground"
      : sign > 0
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
  // Tag each action with its ORIGINAL index so asset_kinds/labels stay aligned after filter
  const significantActions = data.actions
    .map((a, originalIdx) => ({ ...a, _idx: originalIdx }))
    .filter((a) => Math.abs(a.delta_value) > 0.5 || a.optimal_weight > 0.005);

  return (
    <div>
      <h4 className="text-xs uppercase tracking-wider text-muted-foreground mb-3">
        Allocation optimale ({fmt.eur(data.total_capital)})
      </h4>
      <ul className="space-y-2">
        {significantActions.map((a) => {
          const kind = data.asset_kinds[a._idx];
          const label = data.asset_labels[a._idx];
          const isEnvelope = kind === "envelope";
          const sign = a.delta_value > 0.5 ? "buy" : a.delta_value < -0.5 ? "sell" : "hold";
          const Icon = isEnvelope
            ? Wallet
            : sign === "buy"
              ? TrendingUp
              : sign === "sell"
                ? TrendingDown
                : null;
          const verb = isEnvelope
            ? "Place"
            : sign === "buy"
              ? "Achète"
              : sign === "sell"
                ? "Vends"
                : "Conserve";
          const color = isEnvelope
            ? "text-[hsl(160_64%_50%)]"
            : sign === "buy"
              ? "text-[hsl(var(--gain))]"
              : sign === "sell"
                ? "text-[hsl(var(--loss))]"
                : "text-muted-foreground";
          const optAmount = a.optimal_weight * data.total_capital;
          const deltaAmount = Math.abs(a.delta_value);

          return (
            <li
              key={a.ticker}
              className={cn(
                "flex flex-wrap items-center justify-between gap-3 rounded-md border px-3 py-2",
                isEnvelope ? "bg-[hsl(160_64%_50%)]/5 border-[hsl(160_64%_50%)]/30" : "bg-card/50",
              )}
            >
              <div className="flex items-center gap-2 font-mono text-sm min-w-0">
                <span
                  className={cn(
                    "inline-block px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider",
                    isEnvelope
                      ? "bg-[hsl(160_64%_50%)]/20 text-[hsl(160_64%_50%)]"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {isEnvelope ? "Livret" : "ETF"}
                </span>
                <span className="font-medium truncate">{label}</span>
                <span className="text-muted-foreground tabular text-xs">
                  {fmt.pct(a.current_weight)}
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="tabular text-xs font-semibold">{fmt.pct(a.optimal_weight)}</span>
              </div>
              <div className={cn("flex items-center gap-1.5 text-sm font-mono tabular", color)}>
                {Icon && <Icon className="h-3.5 w-3.5" />}
                <span>
                  {verb} {fmt.eur(isEnvelope ? optAmount : deltaAmount)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ─── Risk contributions ─────────────────────────────────────────────────── */

function RiskContributions({ data }: { data: OptimizerResponse }) {
  // Build weight-based pseudo-RiskContribution so we can reuse <RiskBar /> for composition.
  const weightsCurrent = {
    fraction: data.actions.map((a) => a.current_weight),
    tickers: data.asset_labels,
  };
  const weightsOptimal = {
    fraction: data.actions.map((a) => a.optimal_weight),
    tickers: data.asset_labels,
  };

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <h4 className="text-xs uppercase tracking-wider text-muted-foreground">
          Composition (poids w)
        </h4>
        <div className="space-y-2">
          <RiskBar
            label="Actuel"
            rc={weightsCurrent}
            kinds={data.asset_kinds}
            labels={data.asset_labels}
          />
          <RiskBar
            label="Optimal"
            rc={weightsOptimal}
            kinds={data.asset_kinds}
            labels={data.asset_labels}
          />
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="text-xs uppercase tracking-wider text-muted-foreground">
          Contribution à la volatilité σ
        </h4>
        <div className="space-y-2">
          <RiskBar
            label="Actuel"
            rc={data.risk_contributions_current}
            kinds={data.asset_kinds}
            labels={data.asset_labels}
          />
          <RiskBar
            label="Optimal"
            rc={data.risk_contributions_optimal}
            kinds={data.asset_kinds}
            labels={data.asset_labels}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Décomposition d'Euler : σ<sub>p</sub> = Σ w<sub>i</sub> · (Σw)<sub>i</sub> / σ<sub>p</sub>
          . Les livrets contribuent ≈ 0% au risque (σ ≈ 0), même s'ils représentent une part du
          capital.
        </p>
      </div>
    </div>
  );
}

function RiskBar({
  label,
  rc,
  kinds,
  labels,
}: {
  label: string;
  rc: RiskContribution;
  kinds: ("etf" | "envelope")[];
  labels: string[];
}) {
  let etfIdx = 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
      </div>
      <div className="flex h-6 w-full rounded overflow-hidden border bg-muted/20">
        {rc.fraction.map((f, i) => {
          if (Math.abs(f) < 0.005) return null;
          const kind = kinds[i];
          const color =
            kind === "envelope" ? ENVELOPE_COLOR : ETF_COLORS[etfIdx++ % ETF_COLORS.length];
          return (
            <div
              key={labels[i] + i}
              className="flex items-center justify-center text-[10px] font-mono tabular text-black/80"
              style={{ width: `${Math.max(0, f) * 100}%`, background: color }}
              title={`${labels[i]} : ${(f * 100).toFixed(1)}% du risque total`}
            >
              {f >= 0.08 ? `${labels[i].split(" ")[0]} ${(f * 100).toFixed(0)}%` : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
