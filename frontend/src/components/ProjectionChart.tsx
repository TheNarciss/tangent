import { useMemo, useState } from "react";

import type { ProjectionResponse } from "@/api";
import { linePath, linearScale, niceTicks, pickIndices } from "@/lib/chart";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Chart, Crosshair, XAxis, YAxis, indexAt, type ChartFrame } from "@/components/ui/chart";

const COLOR = {
  band: "hsl(var(--foreground))",
  base: "hsl(var(--foreground))",
  invested: "hsl(var(--muted-foreground))",
  goal: "hsl(45 95% 55%)",
};

/* ─── Fan chart ──────────────────────────────────────────────────────────── */

export function FanChart({ data }: { data: ProjectionResponse }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const n = data.months.length;
  const yMax = useMemo(() => Math.max(...data.bands.p90, ...data.invested, data.goal ?? 0), [data]);
  const scales = (frame: ChartFrame) => ({
    xScale: linearScale([0, n - 1], [frame.left, frame.right]),
    yScale: linearScale([0, yMax * 1.05], [frame.bottom, frame.top]),
  });
  const startYear = new Date().getFullYear();

  return (
    <div>
      <Chart
        ariaLabel="Projection de ton épargne"
        height={(_w, compact) => (compact ? 260 : 340)}
        pad={(compact) =>
          compact
            ? { left: 44, right: 12, top: 12, bottom: 34 }
            : { left: 64, right: 24, top: 16, bottom: 36 }
        }
        onPointer={(p, frame) => setHoverIdx(p ? indexAt(p.x, frame, n) : null)}
        tooltip={(frame) => {
          if (hoverIdx === null) return null;
          const { xScale, yScale } = scales(frame);
          return {
            x: xScale(hoverIdx),
            y: yScale(data.bands.p50[hoverIdx]),
            content: <FanTooltip data={data} idx={hoverIdx} startYear={startYear} />,
          };
        }}
      >
        {(frame) => {
          const { xScale, yScale } = scales(frame);
          const ticks = frame.compact ? 4 : 6;
          const xAt = (i: number) => xScale(i);
          const envelope = (lo: number[], hi: number[]) => {
            let p = `M${xAt(0).toFixed(2)},${yScale(lo[0]).toFixed(2)} `;
            for (let i = 1; i < lo.length; i++)
              p += `L${xAt(i).toFixed(2)},${yScale(lo[i]).toFixed(2)} `;
            for (let i = hi.length - 1; i >= 0; i--)
              p += `L${xAt(i).toFixed(2)},${yScale(hi[i]).toFixed(2)} `;
            return p + "Z";
          };
          const goalPx = data.goal ? yScale(data.goal) : null;
          return (
            <>
              <YAxis
                frame={frame}
                ticks={niceTicks(0, yMax, ticks)}
                scale={yScale}
                format={fmt.kEur}
                grid
              />
              <path
                d={envelope(data.bands.p10, data.bands.p90)}
                fill={COLOR.band}
                fillOpacity={0.1}
              />
              <path
                d={envelope(data.bands.p25, data.bands.p75)}
                fill={COLOR.band}
                fillOpacity={0.14}
              />
              {goalPx !== null && (
                <g>
                  <line
                    x1={frame.left}
                    x2={frame.right}
                    y1={goalPx}
                    y2={goalPx}
                    stroke={COLOR.goal}
                    strokeDasharray="4 4"
                  />
                  <text
                    x={frame.right - 4}
                    y={goalPx - 4}
                    textAnchor="end"
                    className="font-mono text-[11px]"
                    fill={COLOR.goal}
                  >
                    Objectif {fmt.kEur(data.goal!)}
                  </text>
                </g>
              )}
              <path
                d={linePath(data.bands.p50, xAt, yScale)}
                fill="none"
                stroke={COLOR.base}
                strokeWidth="2"
              />
              <path
                d={linePath(data.invested, xAt, yScale)}
                fill="none"
                stroke={COLOR.invested}
                strokeDasharray="3 3"
                strokeWidth="1.2"
              />
              <line
                x1={frame.left}
                x2={frame.left}
                y1={frame.top}
                y2={frame.bottom}
                stroke="hsl(var(--foreground))"
              />
              <XAxis
                frame={frame}
                ticks={pickIndices(n, ticks)}
                scale={xScale}
                format={(i) => String(startYear + Math.round(data.months[i] / 12))}
              />
              {hoverIdx !== null && (
                <g>
                  <Crosshair frame={frame} x={xAt(hoverIdx)} />
                  <circle
                    cx={xAt(hoverIdx)}
                    cy={yScale(data.bands.p50[hoverIdx])}
                    r="4"
                    fill={COLOR.base}
                  />
                </g>
              )}
            </>
          );
        }}
      </Chart>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
        <Legend
          swatch={<span className="inline-block h-3 w-6 rounded-sm bg-foreground/20" />}
          label="zone probable (8 fois sur 10)"
        />
        <Legend
          swatch={<span className="inline-block h-0.5 w-6 bg-foreground" />}
          label="le plus probable"
        />
        <Legend
          swatch={
            <span className="inline-block h-0.5 w-6 border-t border-dashed border-muted-foreground" />
          }
          label="ce que tu auras versé"
        />
        {data.goal ? (
          <Legend
            swatch={
              <span
                className="inline-block h-0.5 w-6 border-t border-dashed"
                style={{ borderColor: COLOR.goal }}
              />
            }
            label="ton objectif"
          />
        ) : null}
      </div>
    </div>
  );
}

function FanTooltip({
  data,
  idx,
  startYear,
}: {
  data: ProjectionResponse;
  idx: number;
  startYear: number;
}) {
  const months = data.months[idx];
  const prob = data.goal_prob_by_month?.[idx];
  return (
    <div className="space-y-1 font-mono tabular">
      <div className="font-sans font-medium text-foreground">
        {months < 12 ? `Dans ${months} mois` : `${startYear + Math.round(months / 12)}`}
      </div>
      <Row label="Le plus probable" value={fmt.approxEur(data.bands.p50[idx])} bold />
      <Row
        label="Zone probable"
        value={`${fmt.kEur(data.bands.p10[idx])} – ${fmt.kEur(data.bands.p90[idx])}`}
      />
      <Row label="Versé" value={fmt.approxEur(data.invested[idx])} muted />
      {prob !== undefined && (
        <Row label="Objectif atteint" value={`${Math.round(prob * 10)} chances sur 10`} />
      )}
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
      <span className={cn("font-sans", muted && "text-muted-foreground")}>{label}</span>
      <span className={cn(bold && "font-semibold")}>{value}</span>
    </div>
  );
}

function Legend({ swatch, label }: { swatch: React.ReactNode; label: string }) {
  return (
    <span className="flex items-center gap-2">
      {swatch}
      {label}
    </span>
  );
}
