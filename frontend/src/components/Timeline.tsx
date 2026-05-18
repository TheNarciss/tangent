import { useMemo, useState } from "react";

import type { TimeseriesResponse } from "@/api";
import { fmt } from "@/lib/format";
import {
  areaPath,
  formatDateTick,
  linePath,
  linearScale,
  niceTicks,
  pickIndices,
  type Scale,
} from "@/lib/chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ChartTooltip";

interface Props {
  ts: TimeseriesResponse;
}

const W = 720;
const PAD = { left: 56, right: 24, top: 12, bottom: 24 };

// vertical layout: y-origin and height for each panel + the shared date axis
const PANELS = {
  perf: { y: 36, h: 200, title: "Performance" },
  dd: { y: 280, h: 110, title: "Drawdown" },
  rs: { y: 426, h: 110, title: "Rolling Sharpe" },
};
const AXIS_Y = 552;
const TOTAL_H = AXIS_Y + 24;

/**
 * Three vertically-stacked panels sharing the X axis (date):
 *   1. Performance — portfolio vs benchmark, rebased to 100
 *   2. Drawdown   — filled area, always ≤ 0
 *   3. Rolling Sharpe — line, with reference at 0 and 1
 */
export function Timeline({ ts }: Props) {
  const n = ts.dates.length;

  // Shared X scale: index → pixel
  const xScale = useMemo(
    () => linearScale([0, Math.max(n - 1, 1)], [PAD.left, W - PAD.right]),
    [n],
  );

  // Date ticks (~6 evenly spaced)
  const dateTicks = useMemo(() => pickIndices(n, 6), [n]);

  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [wrapW, setWrapW] = useState(W);

  const handleMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setWrapW(rect.width);
    const px = ((e.clientX - rect.left) / rect.width) * W;
    if (px < PAD.left || px > W - PAD.right) {
      setHoverIdx(null);
      return;
    }
    const t = (px - PAD.left) / (W - PAD.left - PAD.right);
    const i = Math.round(t * (n - 1));
    setHoverIdx(Math.max(0, Math.min(n - 1, i)));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Évolution historique
        </CardTitle>
        <CardDescription>
          Positions actuelles maintenues sur la fenêtre (vue "as-if-held", utile pour les tendances et le risque, pas pour le PnL réel).
          Survole un point pour voir tous les chiffres au jour donné.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative w-full overflow-x-auto">
          <svg
            viewBox={`0 0 ${W} ${TOTAL_H}`}
            className="w-full h-auto"
            role="img"
            aria-label="Évolution historique"
            onMouseMove={handleMove}
            onMouseLeave={() => setHoverIdx(null)}
          >
            <PerformancePanel ts={ts} xScale={xScale} />
            <DrawdownPanel ts={ts} xScale={xScale} />
            <RollingSharpePanel ts={ts} xScale={xScale} />
            <DateAxis ts={ts} xScale={xScale} indices={dateTicks} />

            {/* Hover crosshair across all panels */}
            {hoverIdx !== null && (
              <line
                x1={xScale(hoverIdx)}
                x2={xScale(hoverIdx)}
                y1={PANELS.perf.y}
                y2={PANELS.rs.y + PANELS.rs.h}
                stroke="hsl(var(--foreground))"
                strokeDasharray="2 3"
                strokeWidth="0.8"
                opacity={0.5}
                pointerEvents="none"
              />
            )}
          </svg>

          {hoverIdx !== null && (
            <ChartTooltip
              x={(xScale(hoverIdx) / W) * wrapW}
              y={(PANELS.perf.y / TOTAL_H) * (wrapW * TOTAL_H / W)}
              containerWidth={wrapW}
            >
              <TimelineTooltipContent ts={ts} idx={hoverIdx} />
            </ChartTooltip>
          )}
        </div>

        <PerformanceLegend ts={ts} />
      </CardContent>
    </Card>
  );
}

function TimelineTooltipContent({ ts, idx }: { ts: TimeseriesResponse; idx: number }) {
  const portValue = ts.portfolio[idx];
  const benchValue = ts.benchmark?.[idx];
  const dd = ts.drawdown[idx];
  const rs = ts.rolling_sharpe[idx];

  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium text-foreground">{formatDateTick(ts.dates[idx])}</div>
      <TimelineRow label="Portefeuille" value={`${portValue.toFixed(1)} (${((portValue - 100) / 100 >= 0 ? "+" : "")}${(portValue - 100).toFixed(1)}%)`} />
      {benchValue !== undefined && ts.benchmark_ticker && (
        <TimelineRow label={ts.benchmark_ticker} value={`${benchValue.toFixed(1)} (${((benchValue - 100) >= 0 ? "+" : "")}${(benchValue - 100).toFixed(1)}%)`} muted />
      )}
      <TimelineRow label="Drawdown" value={fmt.pct(dd)} />
      <TimelineRow label={`Sharpe ${ts.rolling_window_days}j`} value={rs === null ? "—" : rs.toFixed(2)} />
      <div className="font-sans text-[10px] text-muted-foreground pt-1 leading-tight">
        Base 100 au {formatDateTick(ts.dates[0])}. Drawdown = baisse depuis le dernier plus-haut.
        Sharpe glissant calculé sur {ts.rolling_window_days} jours de bourse (≈ 6 mois).
      </div>
    </div>
  );
}

function TimelineRow({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex justify-between gap-3 font-mono tabular">
      <span className={`font-sans ${muted ? "text-muted-foreground" : ""}`}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

/* ─── Panels ─────────────────────────────────────────────────────────────── */

interface PanelProps {
  ts: TimeseriesResponse;
  xScale: Scale;
}

function PerformancePanel({ ts, xScale }: PanelProps) {
  const { y: yTop, h, title } = PANELS.perf;
  const series = ts.benchmark ? [...ts.portfolio, ...ts.benchmark] : ts.portfolio;
  const yMin = Math.min(...series);
  const yMax = Math.max(...series);
  const pad = (yMax - yMin) * 0.08;
  const yScale = linearScale([yMin - pad, yMax + pad], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, yMax, 4);
  const xAt = (i: number) => xScale(i);

  return (
    <g>
      <PanelTitle y={yTop - 14} text={title} />
      <PanelFrame y={yTop} h={h} />
      <YAxis ticks={ticks} yScale={yScale} format={(v) => v.toFixed(0)} />

      {/* Benchmark first (under) */}
      {ts.benchmark && (
        <path
          d={linePath(ts.benchmark, xAt, yScale)}
          fill="none"
          stroke="hsl(var(--muted-foreground))"
          strokeWidth="1.2"
          strokeDasharray="3 3"
        />
      )}

      <path
        d={linePath(ts.portfolio, xAt, yScale)}
        fill="none"
        stroke="hsl(var(--foreground))"
        strokeWidth="1.8"
      />
    </g>
  );
}

function DrawdownPanel({ ts, xScale }: PanelProps) {
  const { y: yTop, h, title } = PANELS.dd;
  const yMin = Math.min(...ts.drawdown);
  const yScale = linearScale([yMin * 1.05, 0], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, 0, 3);
  const xAt = (i: number) => xScale(i);
  const maxDD = yMin;

  return (
    <g>
      <PanelTitle y={yTop - 14} text={title} />
      <PanelFrame y={yTop} h={h} />
      <YAxis ticks={ticks} yScale={yScale} format={(v) => fmt.pct(v)} />

      <path d={areaPath(ts.drawdown, xAt, yScale, 0)} fill="hsl(var(--loss))" fillOpacity={0.18} />
      <path d={linePath(ts.drawdown, xAt, yScale)} fill="none" stroke="hsl(var(--loss))" strokeWidth="1.4" />

      {/* Max DD annotation */}
      <text
        x={W - PAD.right - 4}
        y={yTop + 14}
        textAnchor="end"
        className="font-mono text-[10px] fill-[hsl(var(--loss))]"
      >
        Max : {fmt.pct(maxDD)}
      </text>
    </g>
  );
}

function RollingSharpePanel({ ts, xScale }: PanelProps) {
  const { y: yTop, h, title } = PANELS.rs;
  const finite = ts.rolling_sharpe.filter((v): v is number => v !== null && isFinite(v));
  const yMin = finite.length ? Math.min(...finite, 0) : -0.5;
  const yMax = finite.length ? Math.max(...finite, 1) : 1.5;
  const yScale = linearScale([yMin - 0.1, yMax + 0.1], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, yMax, 3);
  const xAt = (i: number) => xScale(i);
  const latest = [...ts.rolling_sharpe].reverse().find((v) => v !== null);

  return (
    <g>
      <PanelTitle y={yTop - 14} text={`${title} (${ts.rolling_window_days}j)`} />
      <PanelFrame y={yTop} h={h} />
      <YAxis ticks={ticks} yScale={yScale} format={(v) => v.toFixed(2)} />

      {/* Reference at 0 (and at 1 if visible) */}
      {[0, 1].map((ref) =>
        ref >= yMin - 0.1 && ref <= yMax + 0.1 ? (
          <line
            key={ref}
            x1={PAD.left}
            x2={W - PAD.right}
            y1={yScale(ref)}
            y2={yScale(ref)}
            stroke="hsl(var(--border))"
            strokeDasharray={ref === 0 ? undefined : "2 4"}
            strokeWidth="0.8"
          />
        ) : null,
      )}

      <path
        d={linePath(ts.rolling_sharpe, xAt, yScale)}
        fill="none"
        stroke="hsl(var(--foreground))"
        strokeWidth="1.6"
      />

      {latest !== undefined && latest !== null && (
        <text
          x={W - PAD.right - 4}
          y={yTop + 14}
          textAnchor="end"
          className="font-mono text-[10px] fill-current text-muted-foreground"
        >
          Dernier : {latest.toFixed(2)}
        </text>
      )}
    </g>
  );
}

/* ─── Shared axis & framing ──────────────────────────────────────────────── */

function PanelTitle({ y, text }: { y: number; text: string }) {
  return (
    <text x={PAD.left} y={y} className="font-sans text-xs font-medium fill-current text-muted-foreground uppercase tracking-wider">
      {text}
    </text>
  );
}

function PanelFrame({ y, h }: { y: number; h: number }) {
  return (
    <rect
      x={PAD.left}
      y={y}
      width={W - PAD.left - PAD.right}
      height={h}
      fill="none"
      stroke="hsl(var(--border))"
      strokeWidth="0.5"
    />
  );
}

function YAxis({ ticks, yScale, format }: { ticks: number[]; yScale: Scale; format: (v: number) => string }) {
  return (
    <g className="font-mono text-[10px] fill-current text-muted-foreground">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left - 4} x2={PAD.left} y1={yScale(t)} y2={yScale(t)} stroke="currentColor" />
          <text x={PAD.left - 8} y={yScale(t) + 3} textAnchor="end">
            {format(t)}
          </text>
        </g>
      ))}
    </g>
  );
}

function DateAxis({ ts, xScale, indices }: { ts: TimeseriesResponse; xScale: Scale; indices: number[] }) {
  return (
    <g className="font-mono text-[10px] fill-current text-muted-foreground">
      <line x1={PAD.left} x2={W - PAD.right} y1={AXIS_Y} y2={AXIS_Y} stroke="hsl(var(--border))" />
      {indices.map((i) => (
        <g key={i}>
          <line x1={xScale(i)} x2={xScale(i)} y1={AXIS_Y} y2={AXIS_Y + 4} stroke="currentColor" />
          <text x={xScale(i)} y={AXIS_Y + 16} textAnchor="middle">
            {formatDateTick(ts.dates[i])}
          </text>
        </g>
      ))}
    </g>
  );
}

function PerformanceLegend({ ts }: { ts: TimeseriesResponse }) {
  return (
    <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
      <span className="flex items-center gap-2">
        <span className="inline-block h-0.5 w-6 bg-foreground" />
        Portefeuille ({ts.portfolio[ts.portfolio.length - 1].toFixed(1)})
      </span>
      {ts.benchmark && ts.benchmark_ticker && (
        <span className="flex items-center gap-2">
          <span
            className="inline-block h-0.5 w-6"
            style={{ backgroundImage: "repeating-linear-gradient(90deg, hsl(var(--muted-foreground)) 0 3px, transparent 3px 6px)", height: 2 }}
          />
          {ts.benchmark_ticker} ({ts.benchmark[ts.benchmark.length - 1].toFixed(1)})
        </span>
      )}
      <span className="ml-auto font-mono">Base 100 au {formatDateTick(ts.dates[0])}</span>
    </div>
  );
}