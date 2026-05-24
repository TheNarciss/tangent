import { useMemo, useRef, useState } from "react";

import { ApiError, useBrokers, useProjection, type ProjectionResponse } from "@/api";
import { formatDateTick, linePath, linearScale, niceTicks, pickIndices } from "@/lib/chart";
import { useDebouncedValue } from "@/lib/hooks";
import { fmt } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ChartTooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const W = 720;
const H = 360;
const PAD = { left: 64, right: 24, top: 16, bottom: 36 };

const COLOR = {
  band: "hsl(var(--foreground))",
  base: "hsl(var(--foreground))",
  bear: "hsl(var(--loss))",
  bull: "hsl(var(--gain))",
  invested: "hsl(var(--muted-foreground))",
  goal: "hsl(45 95% 55%)",
  gross: "hsl(var(--muted-foreground))",
};

/* ─── Public component ───────────────────────────────────────────────────── */

export function Projection() {
  const [monthly, setMonthly] = useState(200);
  const [years, setYears] = useState(10);
  const [goal, setGoal] = useState<number | "">(25000);
  const [broker, setBroker] = useState<string | undefined>(undefined);

  const dMonthly = useDebouncedValue(monthly, 350);
  const dYears = useDebouncedValue(years, 350);
  const dGoal = useDebouncedValue(typeof goal === "number" ? goal : 0, 350);

  const brokers = useBrokers();
  const q = useProjection(dMonthly, dYears, dGoal || undefined, broker);

  // First load: align local state with backend's default broker so the UI matches what's used
  if (broker === undefined && brokers.data) {
    setBroker(brokers.data.default);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Projection DCA
        </CardTitle>
        <CardDescription>
          Géométrie calibrée sur les rendements log quotidiens de ton portefeuille actuel : μ et σ
          extraits, projetés en avant avec versement mensuel fixe. Monte Carlo paramétrique (1000
          trajectoires gaussiennes). Frais broker appliqués au mois le mois (composés correctement)
          — change de broker pour comparer.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <NumberField
            label="Versement mensuel (€)"
            value={monthly}
            onChange={(v) => setMonthly(typeof v === "number" ? v : 0)}
            min={0}
            step={50}
          />
          <NumberField
            label="Horizon (années)"
            value={years}
            onChange={(v) => setYears(typeof v === "number" ? Math.max(1, v) : 1)}
            min={1}
            max={50}
            step={1}
          />
          <NumberField
            label="Objectif (€, optionnel)"
            value={goal}
            onChange={setGoal}
            min={0}
            step={5000}
            allowEmpty
          />
          <BrokerField value={broker} onChange={setBroker} brokers={brokers.data} />
        </div>

        {q.isLoading && <p className="text-sm text-muted-foreground">Calcul…</p>}
        {q.isError && <ErrorBanner error={q.error} />}
        {q.data && <FanChart data={q.data} />}
        {q.data && <Stats data={q.data} />}
      </CardContent>
    </Card>
  );
}

function BrokerField({
  value,
  onChange,
  brokers,
}: {
  value: string | undefined;
  onChange: (v: string) => void;
  brokers: { default: string; brokers: { id: string; name: string }[] } | undefined;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">Broker (frais)</Label>
      <Select value={value} onValueChange={onChange} disabled={!brokers}>
        <SelectTrigger>
          <SelectValue placeholder="Chargement…" />
        </SelectTrigger>
        <SelectContent>
          {brokers?.brokers.map((b) => (
            <SelectItem key={b.id} value={b.id}>
              {b.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function ErrorBanner({ error }: { error: unknown }) {
  const msg =
    error instanceof ApiError
      ? `${error.type} — ${error.message}`
      : error instanceof Error
        ? error.message
        : "Erreur inconnue";
  return <p className="text-sm text-[hsl(var(--loss))]">Erreur : {msg}</p>;
}

/* ─── Inputs ─────────────────────────────────────────────────────────────── */

interface NumberFieldProps {
  label: string;
  value: number | "";
  onChange: (v: number | "") => void;
  min?: number;
  max?: number;
  step?: number;
  allowEmpty?: boolean;
}

function NumberField({ label, value, onChange, min, max, step, allowEmpty }: NumberFieldProps) {
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
          if (raw === "" && allowEmpty) return onChange("");
          const n = Number(raw);
          if (!isNaN(n)) onChange(n);
        }}
        className="font-mono tabular"
      />
    </div>
  );
}

/* ─── Stats block ────────────────────────────────────────────────────────── */

function Stats({ data }: { data: ProjectionResponse }) {
  const invested = data.invested[data.invested.length - 1];
  const median = data.bands.p50[data.bands.p50.length - 1];
  const grossMedian = data.gross_p50[data.gross_p50.length - 1];
  const fees = data.cumulative_fees[data.cumulative_fees.length - 1];
  const gain = median - invested;
  const feesPctOfGross = grossMedian > 0 ? fees / grossMedian : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
        <Stat
          label="μ, σ utilisés"
          value={`${fmt.pct(data.annual_return)} / ${fmt.pct(data.annual_vol)}`}
          sub="annualisés, extraits de ton historique"
        />
        <Stat
          label="Capital investi"
          value={fmt.eur(invested)}
          sub={`${data.months.length - 1} mois`}
        />
        <Stat
          label="Valeur médiane nette (P50)"
          value={fmt.eur(median)}
          sub={`plus-value : ${fmt.signedEur(gain)}`}
        />
        {data.goal_prob_at_end !== null && data.goal && (
          <Stat
            label={`P(atteindre ${fmt.eur(data.goal)})`}
            value={fmt.pct(data.goal_prob_at_end)}
            sub="fraction des 1000 simulations qui dépassent l'objectif"
          />
        )}
      </div>

      {/* Fee impact strip — what BNP/Fortuneo/etc. actually coûte sur l'horizon */}
      <div className="rounded-md border bg-card/40 px-4 py-3">
        <div className="flex items-center justify-between text-xs uppercase tracking-wider text-muted-foreground mb-2">
          <span>Impact frais — {data.broker}</span>
          <span className="font-mono tabular text-[10px] normal-case tracking-normal">
            modèle : fixe × n_lignes + (custody + rebates) × valeur + courtage × versement
          </span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          <Stat
            label="Frais cumulés à l'horizon"
            value={fmt.eur(fees)}
            sub={`soit ${fmt.pct(feesPctOfGross)} de la médiane brute`}
          />
          <Stat
            label="Médiane brute (sans frais)"
            value={fmt.eur(grossMedian)}
            sub={`écart : ${fmt.signedEur(median - grossMedian)} vs brut`}
          />
          <Stat
            label="Frais mensuels moyens"
            value={fmt.eur(fees / Math.max(1, data.months.length - 1))}
            sub="amorti sur l'horizon, en €/mois"
          />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono font-semibold tabular">{value}</div>
      <div className="text-xs text-muted-foreground">{sub}</div>
    </div>
  );
}

/* ─── Fan chart ──────────────────────────────────────────────────────────── */

interface FanProps {
  data: ProjectionResponse;
}

function FanChart({ data }: FanProps) {
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [wrapW, setWrapW] = useState(W);

  const { xScale, yScale, yTicks, xTicks } = useMemo(() => {
    const lastIdx = data.months.length - 1;
    const allValues = [...data.bands.p10, ...data.bands.p90, ...data.bands.bull, ...data.invested];
    const yMin = 0;
    const yMax = Math.max(...allValues);

    const xScale = linearScale([0, lastIdx], [PAD.left, PAD.left + innerW]);
    const yScale = linearScale([yMin, yMax * 1.05], [PAD.top + innerH, PAD.top]);

    return {
      xScale,
      yScale,
      yTicks: niceTicks(yMin, yMax, 5),
      xTicks: pickIndices(data.months.length, 6),
    };
  }, [data, innerW, innerH]);

  const xAt = (i: number) => xScale(i);

  // mouse → nearest month index
  const handleMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setWrapW(rect.width);
    const px = ((e.clientX - rect.left) / rect.width) * W;
    if (px < PAD.left || px > W - PAD.right) {
      setHoverIdx(null);
      return;
    }
    const lastIdx = data.months.length - 1;
    const t = (px - PAD.left) / innerW;
    const i = Math.round(t * lastIdx);
    setHoverIdx(Math.max(0, Math.min(lastIdx, i)));
  };

  // For the band, we draw P10→P90 as an envelope, then P25→P75 as a darker inner one.
  const envelopePath = (lo: number[], hi: number[]) => {
    let p = `M${xAt(0).toFixed(2)},${yScale(lo[0]).toFixed(2)} `;
    for (let i = 1; i < lo.length; i++) p += `L${xAt(i).toFixed(2)},${yScale(lo[i]).toFixed(2)} `;
    for (let i = hi.length - 1; i >= 0; i--)
      p += `L${xAt(i).toFixed(2)},${yScale(hi[i]).toFixed(2)} `;
    return p + "Z";
  };

  const goalPx = data.goal !== null ? yScale(data.goal) : null;

  return (
    <div ref={wrapRef} className="relative w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto"
        role="img"
        aria-label="Projection DCA"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Grid */}
        <g stroke="hsl(var(--border))" strokeWidth="0.5" opacity="0.5">
          {yTicks.map((t) => (
            <line
              key={`yg-${t}`}
              x1={PAD.left}
              x2={PAD.left + innerW}
              y1={yScale(t)}
              y2={yScale(t)}
            />
          ))}
        </g>

        {/* P10-P90 envelope */}
        <path
          d={envelopePath(data.bands.p10, data.bands.p90)}
          fill={COLOR.band}
          fillOpacity={0.08}
        />
        {/* P25-P75 envelope */}
        <path
          d={envelopePath(data.bands.p25, data.bands.p75)}
          fill={COLOR.band}
          fillOpacity={0.14}
        />

        {/* Goal line */}
        {goalPx !== null && (
          <g>
            <line
              x1={PAD.left}
              x2={PAD.left + innerW}
              y1={goalPx}
              y2={goalPx}
              stroke={COLOR.goal}
              strokeDasharray="4 4"
              strokeWidth="1"
            />
            <text
              x={PAD.left + innerW - 4}
              y={goalPx - 4}
              textAnchor="end"
              className="font-mono text-[10px]"
              fill={COLOR.goal}
            >
              Objectif {fmt.eur(data.goal!)}
            </text>
          </g>
        )}

        {/* Deterministic lines */}
        <path
          d={linePath(data.bands.bear, xAt, yScale)}
          fill="none"
          stroke={COLOR.bear}
          strokeWidth="1.4"
          strokeOpacity={0.85}
        />
        <path
          d={linePath(data.bands.bull, xAt, yScale)}
          fill="none"
          stroke={COLOR.bull}
          strokeWidth="1.4"
          strokeOpacity={0.85}
        />
        <path
          d={linePath(data.bands.base, xAt, yScale)}
          fill="none"
          stroke={COLOR.base}
          strokeWidth="2"
        />

        {/* Gross P50 (without fees) — dashed overlay for comparison */}
        <path
          d={linePath(data.gross_p50, xAt, yScale)}
          fill="none"
          stroke={COLOR.gross}
          strokeDasharray="4 4"
          strokeWidth="1.2"
          strokeOpacity={0.65}
        />

        {/* Invested line */}
        <path
          d={linePath(data.invested, xAt, yScale)}
          fill="none"
          stroke={COLOR.invested}
          strokeDasharray="3 3"
          strokeWidth="1.2"
        />

        {/* Axes */}
        <g stroke="hsl(var(--foreground))" strokeWidth="1">
          <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + innerH} />
          <line x1={PAD.left} x2={PAD.left + innerW} y1={PAD.top + innerH} y2={PAD.top + innerH} />
        </g>

        {/* Y ticks */}
        <g className="font-mono text-[10px] fill-current text-muted-foreground">
          {yTicks.map((t) => (
            <g key={`yt-${t}`}>
              <line
                x1={PAD.left - 4}
                x2={PAD.left}
                y1={yScale(t)}
                y2={yScale(t)}
                stroke="currentColor"
              />
              <text x={PAD.left - 8} y={yScale(t) + 3} textAnchor="end">
                {compactEur(t)}
              </text>
            </g>
          ))}
        </g>

        {/* X ticks (years) */}
        <g className="font-mono text-[10px] fill-current text-muted-foreground">
          {xTicks.map((i) => (
            <g key={`xt-${i}`}>
              <line
                x1={xAt(i)}
                x2={xAt(i)}
                y1={PAD.top + innerH}
                y2={PAD.top + innerH + 4}
                stroke="currentColor"
              />
              <text x={xAt(i)} y={PAD.top + innerH + 16} textAnchor="middle">
                {data.months[i] / 12 < 1
                  ? `${data.months[i]}m`
                  : `${Math.round(data.months[i] / 12)}a`}
              </text>
            </g>
          ))}
          <text
            x={PAD.left + innerW / 2}
            y={H - 6}
            textAnchor="middle"
            className="font-sans text-xs"
          >
            Horizon
          </text>
        </g>

        {/* Hover crosshair */}
        {hoverIdx !== null && (
          <g>
            <line
              x1={xAt(hoverIdx)}
              x2={xAt(hoverIdx)}
              y1={PAD.top}
              y2={PAD.top + innerH}
              stroke="hsl(var(--foreground))"
              strokeDasharray="2 3"
              strokeWidth="0.8"
              opacity={0.5}
            />
            <circle
              cx={xAt(hoverIdx)}
              cy={yScale(data.bands.p50[hoverIdx])}
              r="4"
              fill={COLOR.base}
            />
          </g>
        )}
      </svg>

      {hoverIdx !== null && (
        <ChartTooltip
          x={(xAt(hoverIdx) / W) * wrapW}
          y={(yScale(data.bands.p50[hoverIdx]) / H) * ((wrapW * H) / W)}
          containerWidth={wrapW}
        >
          <FanTooltipContent data={data} idx={hoverIdx} />
        </ChartTooltip>
      )}

      <Legend />
    </div>
  );
}

function FanTooltipContent({ data, idx }: { data: ProjectionResponse; idx: number }) {
  const months = data.months[idx];
  const years = months / 12;
  const invested = data.invested[idx];
  const median = data.bands.p50[idx];
  const grossMedian = data.gross_p50[idx];
  const cumFees = data.cumulative_fees[idx];
  const prob = data.goal_prob_by_month?.[idx];

  return (
    <div className="space-y-1.5 font-mono tabular">
      <div className="font-sans font-medium text-foreground">
        {years < 1 ? `${months} mois` : `Année ${years.toFixed(1)} (${months} mois)`}
      </div>
      <Row label="Médiane nette (P50)" value={fmt.eur(median)} bold />
      <Row label="Médiane brute (sans frais)" value={fmt.eur(grossMedian)} muted />
      <Row label="Frais cumulés" value={fmt.eur(cumFees)} />
      <Row
        label="P10 / P90"
        value={`${compactEur(data.bands.p10[idx])} / ${compactEur(data.bands.p90[idx])}`}
      />
      <Row label="Investi" value={fmt.eur(invested)} muted />
      <Row label="Plus-value nette" value={fmt.signedEur(median - invested)} />
      {prob !== undefined && <Row label={`P(≥ ${compactEur(data.goal!)})`} value={fmt.pct(prob)} />}
      <div className="font-sans text-[10px] text-muted-foreground pt-1 leading-tight">
        Bandes P10–P90 = quantiles des 1000 simulations. Tiret gris = projection sans frais
        (comparaison).
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  bold,
  muted,
}: {
  label: string;
  value: string;
  bold?: boolean;
  muted?: boolean;
}) {
  return (
    <div className="flex justify-between gap-3">
      <span className={`font-sans ${muted ? "text-muted-foreground" : ""}`}>{label}</span>
      <span className={bold ? "font-semibold" : ""}>{value}</span>
    </div>
  );
}

function Legend() {
  return (
    <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
      <LegendItem
        swatch={<Band color={COLOR.band} />}
        label="P10–P90 / P25–P75 (Monte Carlo, net frais)"
      />
      <LegendItem swatch={<Stroke color={COLOR.base} thick />} label="Scénario base (μ)" />
      <LegendItem swatch={<Stroke color={COLOR.bull} />} label="Bull (μ+σ)" />
      <LegendItem swatch={<Stroke color={COLOR.bear} />} label="Bear (μ−σ)" />
      <LegendItem
        swatch={<Stroke color={COLOR.gross} dashed />}
        label="P50 sans frais (comparaison)"
      />
      <LegendItem swatch={<Stroke color={COLOR.invested} dashed />} label="Capital investi" />
    </div>
  );
}

function LegendItem({ swatch, label }: { swatch: React.ReactNode; label: string }) {
  return (
    <span className="flex items-center gap-2">
      {swatch}
      {label}
    </span>
  );
}

function Band({ color }: { color: string }) {
  return (
    <span className="relative inline-block h-3 w-6 overflow-hidden">
      <span className="absolute inset-0 opacity-20" style={{ background: color }} />
      <span
        className="absolute inset-y-0 left-1 right-1 opacity-40"
        style={{ background: color }}
      />
    </span>
  );
}

function Stroke({ color, dashed, thick }: { color: string; dashed?: boolean; thick?: boolean }) {
  return (
    <svg width="24" height="6" className="inline-block">
      <line
        x1="0"
        x2="24"
        y1="3"
        y2="3"
        stroke={color}
        strokeWidth={thick ? 2 : 1.4}
        strokeDasharray={dashed ? "3 3" : undefined}
      />
    </svg>
  );
}

/* ─── Small helpers ──────────────────────────────────────────────────────── */

function compactEur(v: number): string {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)} k€`;
  return `${v.toFixed(0)} €`;
}

// silence unused-import for formatDateTick (kept available if we re-add date axis)
void formatDateTick;
