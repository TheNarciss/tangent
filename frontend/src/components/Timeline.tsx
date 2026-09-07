import { useState } from "react";

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
import { Chart, Crosshair, XAxis, YAxis, indexAt, type ChartFrame } from "@/components/ui/chart";

interface Props {
  ts: TimeseriesResponse;
}

const TITLE_H = 36; // room for a panel title above each panel
const AXIS_H = 30; // date axis below the last panel

interface Panel {
  y: number;
  h: number;
}
interface Layout {
  perf: Panel;
  dd: Panel;
  rs: Panel;
  axisY: number;
}

/** Panel heights: shorter on phones so the three panels fit one screen. */
function panelHeights(compact: boolean) {
  return compact ? { perf: 150, dd: 80, rs: 80 } : { perf: 200, dd: 110, rs: 110 };
}

function totalHeight(_width: number, compact: boolean) {
  const h = panelHeights(compact);
  return 3 * TITLE_H + h.perf + h.dd + h.rs + AXIS_H;
}

function layout(frame: ChartFrame): Layout {
  const h = panelHeights(frame.compact);
  const perf = { y: TITLE_H, h: h.perf };
  const dd = { y: perf.y + perf.h + TITLE_H, h: h.dd };
  const rs = { y: dd.y + dd.h + TITLE_H, h: h.rs };
  return { perf, dd, rs, axisY: rs.y + rs.h };
}

/**
 * Three vertically-stacked panels sharing the X axis (date):
 *   1. Performance — portfolio vs benchmark, rebased to 100
 *   2. Drawdown   — filled area, always ≤ 0
 *   3. Rolling Sharpe — line, with reference at 0 and 1
 */
export function Timeline({ ts }: Props) {
  const n = ts.dates.length;
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const xScaleFor = (frame: ChartFrame) =>
    linearScale([0, Math.max(n - 1, 1)], [frame.left, frame.right]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Évolution historique
        </CardTitle>
        <CardDescription>
          Positions actuelles maintenues sur la fenêtre (vue "as-if-held", utile pour les tendances
          et le risque, pas pour le PnL réel). Touche ou survole un point pour voir tous les
          chiffres au jour donné.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Chart
          ariaLabel="Évolution historique"
          height={totalHeight}
          pad={(compact) => ({
            left: compact ? 44 : 56,
            right: compact ? 12 : 24,
            top: 0,
            bottom: 0,
          })}
          onPointer={(p, frame) => setHoverIdx(p ? indexAt(p.x, frame, n) : null)}
          tooltip={(frame) => {
            if (hoverIdx === null) return null;
            const perf = layout(frame).perf;
            return {
              x: xScaleFor(frame)(hoverIdx),
              y: perf.y + perf.h / 2,
              content: <TimelineTooltipContent ts={ts} idx={hoverIdx} />,
            };
          }}
        >
          {(frame) => {
            const l = layout(frame);
            const xScale = xScaleFor(frame);
            return (
              <>
                <PerformancePanel ts={ts} frame={frame} panel={l.perf} xScale={xScale} />
                <DrawdownPanel ts={ts} frame={frame} panel={l.dd} xScale={xScale} />
                <RollingSharpePanel ts={ts} frame={frame} panel={l.rs} xScale={xScale} />
                <XAxis
                  frame={frame}
                  ticks={pickIndices(n, frame.compact ? 3 : 6)}
                  scale={xScale}
                  format={(i) => formatDateTick(ts.dates[i])}
                  y={l.axisY}
                />
                {hoverIdx !== null && (
                  <Crosshair
                    frame={frame}
                    x={xScale(hoverIdx)}
                    y1={l.perf.y}
                    y2={l.rs.y + l.rs.h}
                  />
                )}
              </>
            );
          }}
        </Chart>

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
      <TimelineRow
        label="Portefeuille"
        value={`${portValue.toFixed(1)} (${(portValue - 100) / 100 >= 0 ? "+" : ""}${(portValue - 100).toFixed(1)}%)`}
      />
      {benchValue !== undefined && ts.benchmark_ticker && (
        <TimelineRow
          label={ts.benchmark_ticker}
          value={`${benchValue.toFixed(1)} (${benchValue - 100 >= 0 ? "+" : ""}${(benchValue - 100).toFixed(1)}%)`}
          muted
        />
      )}
      <TimelineRow label="Drawdown" value={fmt.pct(dd)} />
      <TimelineRow
        label={`Sharpe ${ts.rolling_window_days}j`}
        value={rs === null ? "—" : rs.toFixed(2)}
      />
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
  frame: ChartFrame;
  panel: Panel;
  xScale: Scale;
}

function PerformancePanel({ ts, frame, panel, xScale }: PanelProps) {
  const { y: yTop, h } = panel;
  const series = ts.benchmark ? [...ts.portfolio, ...ts.benchmark] : ts.portfolio;
  const yMin = Math.min(...series);
  const yMax = Math.max(...series);
  const pad = (yMax - yMin) * 0.08;
  const yScale = linearScale([yMin - pad, yMax + pad], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, yMax, frame.compact ? 3 : 4);
  const xAt = (i: number) => xScale(i);

  return (
    <g>
      <PanelTitle frame={frame} y={yTop - 12} text="Performance" />
      <PanelFrame frame={frame} panel={panel} />
      <YAxis frame={frame} ticks={ticks} scale={yScale} format={(v) => v.toFixed(0)} />

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

function DrawdownPanel({ ts, frame, panel, xScale }: PanelProps) {
  const { y: yTop, h } = panel;
  const yMin = Math.min(...ts.drawdown);
  const yScale = linearScale([yMin * 1.05, 0], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, 0, frame.compact ? 2 : 3);
  const xAt = (i: number) => xScale(i);

  return (
    <g>
      <PanelTitle frame={frame} y={yTop - 12} text="Drawdown" />
      <PanelFrame frame={frame} panel={panel} />
      <YAxis frame={frame} ticks={ticks} scale={yScale} format={(v) => fmt.pct(v)} />

      <path d={areaPath(ts.drawdown, xAt, yScale, 0)} fill="hsl(var(--loss))" fillOpacity={0.18} />
      <path
        d={linePath(ts.drawdown, xAt, yScale)}
        fill="none"
        stroke="hsl(var(--loss))"
        strokeWidth="1.4"
      />

      {/* Max DD annotation */}
      <text
        x={frame.right - 4}
        y={yTop + 14}
        textAnchor="end"
        className="font-mono text-[11px] fill-[hsl(var(--loss))]"
      >
        Max : {fmt.pct(yMin)}
      </text>
    </g>
  );
}

function RollingSharpePanel({ ts, frame, panel, xScale }: PanelProps) {
  const { y: yTop, h } = panel;
  const finite = ts.rolling_sharpe.filter((v): v is number => v !== null && isFinite(v));
  const yMin = finite.length ? Math.min(...finite, 0) : -0.5;
  const yMax = finite.length ? Math.max(...finite, 1) : 1.5;
  const yScale = linearScale([yMin - 0.1, yMax + 0.1], [yTop + h, yTop]);
  const ticks = niceTicks(yMin, yMax, frame.compact ? 2 : 3);
  const xAt = (i: number) => xScale(i);
  const latest = [...ts.rolling_sharpe].reverse().find((v) => v !== null);

  return (
    <g>
      <PanelTitle
        frame={frame}
        y={yTop - 12}
        text={`Rolling Sharpe (${ts.rolling_window_days}j)`}
      />
      <PanelFrame frame={frame} panel={panel} />
      <YAxis frame={frame} ticks={ticks} scale={yScale} format={(v) => v.toFixed(2)} />

      {/* Reference at 0 (and at 1 if visible) */}
      {[0, 1].map((ref) =>
        ref >= yMin - 0.1 && ref <= yMax + 0.1 ? (
          <line
            key={ref}
            x1={frame.left}
            x2={frame.right}
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
          x={frame.right - 4}
          y={yTop + 14}
          textAnchor="end"
          className="font-mono text-[11px] fill-current text-muted-foreground"
        >
          Dernier : {latest.toFixed(2)}
        </text>
      )}
    </g>
  );
}

/* ─── Shared framing ─────────────────────────────────────────────────────── */

function PanelTitle({ frame, y, text }: { frame: ChartFrame; y: number; text: string }) {
  return (
    <text
      x={frame.left}
      y={y}
      className="font-sans text-xs font-medium fill-current text-muted-foreground uppercase tracking-wider"
    >
      {text}
    </text>
  );
}

function PanelFrame({ frame, panel }: { frame: ChartFrame; panel: Panel }) {
  return (
    <rect
      x={frame.left}
      y={panel.y}
      width={frame.innerW}
      height={panel.h}
      fill="none"
      stroke="hsl(var(--border))"
      strokeWidth="0.5"
    />
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
            style={{
              backgroundImage:
                "repeating-linear-gradient(90deg, hsl(var(--muted-foreground)) 0 3px, transparent 3px 6px)",
              height: 2,
            }}
          />
          {ts.benchmark_ticker} ({ts.benchmark[ts.benchmark.length - 1].toFixed(1)})
        </span>
      )}
      <span className="ml-auto font-mono">Base 100 au {formatDateTick(ts.dates[0])}</span>
    </div>
  );
}
