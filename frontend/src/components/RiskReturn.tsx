import { useMemo, useState } from "react";

import type { EnvelopePoint, FrontierCurve, PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { linearScale, niceTicks } from "@/lib/chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Chart, XAxis, YAxis, type ChartFrame } from "@/components/ui/chart";

interface Props {
  metrics: PortfolioMetrics;
  smoothFrontier?: FrontierCurve;
  optimal?: { sigma: number; mu: number; label: string };
  envelopePoints?: EnvelopePoint[];
}

/** Everything that can be tapped on the map, in data space. */
type Marker =
  | { kind: "etf"; label: string; sigma: number; mu: number; color: string }
  | { kind: "portfolio"; label: string; sigma: number; mu: number }
  | { kind: "optimal"; label: string; sigma: number; mu: number }
  | { kind: "envelopes"; sigma: number; mu: number; items: EnvelopePoint[] };

const ETF_COLORS = [
  "#60a5fa",
  "#f97316",
  "#a78bfa",
  "#22d3ee",
  "#facc15",
  "#f472b6",
  "#10b981",
  "#ef4444",
];
const HIT_RADIUS = 24; // px around a marker that selects it (finger-friendly)

export function RiskReturn({ metrics, smoothFrontier, optimal, envelopePoints }: Props) {
  const [hover, setHover] = useState<Marker | null>(null);

  const envelopes = useMemo(
    () => (envelopePoints ?? []).slice().sort((a, b) => b.expected_return - a.expected_return),
    [envelopePoints],
  );
  const hasEnvelopes = envelopes.length > 0;

  // Data-space domain + the markers to draw / hit-test
  const { xMin, xMax, yMin, yMax, markers } = useMemo(() => {
    const sigmas = [
      ...metrics.assets.map((a) => a.annual_vol),
      ...envelopes.map((e) => e.volatility),
      metrics.volatility,
      ...(optimal ? [optimal.sigma] : []),
      ...(smoothFrontier?.vol ?? []),
    ];
    const mus = [
      ...metrics.assets.map((a) => a.annual_return),
      ...envelopes.map((e) => e.expected_return),
      metrics.expected_return,
      ...(optimal ? [optimal.mu] : []),
      ...(smoothFrontier?.ret ?? []),
    ];
    const markers: Marker[] = [
      ...metrics.assets.map<Marker>((a, i) => ({
        kind: "etf",
        label: a.ticker,
        sigma: a.annual_vol,
        mu: a.annual_return,
        color: ETF_COLORS[i % ETF_COLORS.length],
      })),
      {
        kind: "portfolio",
        label: "Position actuelle",
        sigma: metrics.volatility,
        mu: metrics.expected_return,
      },
    ];
    if (optimal) markers.push({ kind: "optimal", ...optimal });
    if (hasEnvelopes) {
      const mid =
        (Math.min(...envelopes.map((e) => e.expected_return)) +
          Math.max(...envelopes.map((e) => e.expected_return))) /
        2;
      markers.push({ kind: "envelopes", sigma: 0, mu: mid, items: envelopes });
    }
    return {
      xMin: hasEnvelopes ? 0 : Math.max(0, Math.min(...sigmas) - 0.005),
      xMax: Math.max(...sigmas) + 0.015,
      yMin: Math.min(...mus) - 0.015,
      yMax: Math.max(...mus) + 0.015,
      markers,
    };
  }, [metrics, envelopes, optimal, smoothFrontier, hasEnvelopes]);

  const scales = (frame: ChartFrame) => ({
    xScale: linearScale([xMin, xMax], [frame.left, frame.right]),
    yScale: linearScale([yMin, yMax], [frame.bottom, frame.top]),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Risque–Rendement
        </CardTitle>
        <CardDescription>
          Carte (σ, μ) de ton univers. Touche ou survole un point pour voir ses détails.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {smoothFrontier?.unavailable_reason && (
          <div className="mb-3 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-700 dark:text-yellow-400">
            {smoothFrontier.unavailable_reason}
          </div>
        )}
        <Chart
          ariaLabel="Carte risque-rendement"
          height={(_w, compact) => (compact ? 300 : 440)}
          pad={(compact) =>
            compact
              ? { top: 16, right: 16, bottom: 46, left: 52 }
              : { top: 20, right: 30, bottom: 60, left: 90 }
          }
          onPointer={(p, frame) => {
            if (!p) return setHover(null);
            const { xScale, yScale } = scales(frame);
            // Nearest marker within HIT_RADIUS px, else nothing
            let best: Marker | null = null;
            let bestD = HIT_RADIUS;
            for (const m of markers) {
              const d = Math.hypot(xScale(m.sigma) - p.x, yScale(m.mu) - p.y);
              if (d < bestD) {
                bestD = d;
                best = m;
              }
            }
            setHover(best);
          }}
          tooltip={(frame) => {
            if (!hover) return null;
            const { xScale, yScale } = scales(frame);
            return {
              x: xScale(hover.sigma),
              y: yScale(hover.mu),
              content: <MarkerTooltip marker={hover} />,
            };
          }}
        >
          {(frame) => {
            const { xScale, yScale } = scales(frame);
            const nTicks = frame.compact ? 4 : 6;
            const xTicks = niceTicks(xMin, xMax, nTicks);
            const yTicks = niceTicks(yMin, yMax, nTicks);
            const frontierPath =
              smoothFrontier && smoothFrontier.vol.length > 1
                ? smoothFrontier.vol
                    .map(
                      (v, i) =>
                        `${i === 0 ? "M" : "L"}${xScale(v).toFixed(2)},${yScale(smoothFrontier.ret[i]).toFixed(2)}`,
                    )
                    .join(" ")
                : null;
            const env = markers.find((m) => m.kind === "envelopes");
            const isHovered = (m: Marker) => hover === m;

            return (
              <>
                {/* Grid */}
                <g stroke="hsl(var(--border))" strokeWidth="0.5" opacity="0.3">
                  {xTicks.map((t) => (
                    <line
                      key={`gx-${t}`}
                      x1={xScale(t)}
                      x2={xScale(t)}
                      y1={frame.top}
                      y2={frame.bottom}
                    />
                  ))}
                  {yTicks.map((t) => (
                    <line
                      key={`gy-${t}`}
                      x1={frame.left}
                      x2={frame.right}
                      y1={yScale(t)}
                      y2={yScale(t)}
                    />
                  ))}
                </g>

                {/* Axes */}
                <line
                  x1={frame.left}
                  x2={frame.left}
                  y1={frame.top}
                  y2={frame.bottom}
                  stroke="hsl(var(--foreground))"
                />
                <XAxis
                  frame={frame}
                  ticks={xTicks}
                  scale={xScale}
                  format={(t) => fmt.pct(t)}
                  label={frame.compact ? "Volatilité σ" : "Volatilité σ (annualisée)"}
                />
                <YAxis frame={frame} ticks={yTicks} scale={yScale} format={(t) => fmt.pct(t)} />
                {!frame.compact && (
                  <text
                    x={-(frame.top + frame.innerH / 2)}
                    y={16}
                    textAnchor="middle"
                    transform="rotate(-90)"
                    className="font-sans text-xs fill-current text-muted-foreground"
                  >
                    Rendement μ annualisé
                  </text>
                )}

                {/* Frontière */}
                {frontierPath && (
                  <path
                    d={frontierPath}
                    fill="none"
                    stroke="hsl(var(--foreground))"
                    strokeWidth="2"
                    opacity="0.7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {/* Zone livrets (σ ≈ 0) */}
                {env && env.kind === "envelopes" && (
                  <g>
                    <rect
                      x={xScale(0) - 8}
                      y={yScale(Math.max(...env.items.map((e) => e.expected_return))) - 4}
                      width={16}
                      height={
                        yScale(Math.min(...env.items.map((e) => e.expected_return))) -
                        yScale(Math.max(...env.items.map((e) => e.expected_return))) +
                        8
                      }
                      fill="#10b981"
                      opacity={isHovered(env) ? 1 : 0.7}
                      rx={3}
                      stroke="hsl(var(--background))"
                      strokeWidth={1.5}
                    />
                    <text
                      x={xScale(0) + 14}
                      y={yScale(env.mu) + 4}
                      className="font-mono text-[11px] fill-current"
                    >
                      {env.items.length}× livrets
                    </text>
                  </g>
                )}

                {/* ETFs */}
                {markers.map((m, i) => {
                  if (m.kind !== "etf") return null;
                  const cx = xScale(m.sigma);
                  const cy = yScale(m.mu);
                  return (
                    <g key={`etf-${i}`}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isHovered(m) ? 9 : 7}
                        fill={m.color}
                        stroke="hsl(var(--background))"
                        strokeWidth={2}
                      />
                      <text x={cx + 12} y={cy + 4} className="font-mono text-[11px] fill-current">
                        {m.label.replace(".PA", "")}
                      </text>
                    </g>
                  );
                })}

                {/* Position actuelle */}
                {markers.map((m, i) => {
                  if (m.kind !== "portfolio") return null;
                  const cx = xScale(m.sigma);
                  const cy = yScale(m.mu);
                  const r = isHovered(m) ? 12 : 10;
                  return (
                    <polygon
                      key={`pf-${i}`}
                      points={`${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`}
                      fill="#22c55e"
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  );
                })}

                {/* Optimal */}
                {markers.map((m, i) =>
                  m.kind === "optimal"
                    ? drawStar(
                        xScale(m.sigma),
                        yScale(m.mu),
                        isHovered(m) ? 14 : 12,
                        "#fbbf24",
                        "hsl(var(--background))",
                        2,
                        `opt-${i}`,
                      )
                    : null,
                )}
              </>
            );
          }}
        </Chart>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
          <LegendItem swatch={<Dot color="#60a5fa" />} label="ETF" />
          {hasEnvelopes && (
            <LegendItem swatch={<Square color="#10b981" />} label="Livrets (σ ≈ 0)" />
          )}
          <LegendItem swatch={<Diamond />} label="Position actuelle" />
          {optimal && <LegendItem swatch={<StarSwatch />} label={optimal.label} />}
          {smoothFrontier && smoothFrontier.vol.length > 1 && (
            <LegendItem swatch={<Line />} label="Frontière efficiente" />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function MarkerTooltip({ marker }: { marker: Marker }) {
  if (marker.kind === "envelopes") {
    return (
      <div className="space-y-1">
        <div className="font-semibold" style={{ color: "#10b981" }}>
          {marker.items.length} livret{marker.items.length > 1 ? "s" : ""} · σ ≈ 0
        </div>
        {marker.items.map((e, i) => (
          <div key={i} className="flex justify-between gap-3 font-mono tabular">
            <span className="truncate">{e.label}</span>
            <span className="font-semibold" style={{ color: "#10b981" }}>
              {fmt.pct(e.expected_return)}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="space-y-0.5">
      <div className="font-semibold text-foreground">{marker.label}</div>
      <div className="font-mono tabular text-muted-foreground">
        σ {fmt.pct(marker.sigma)} · μ {fmt.pct(marker.mu)}
      </div>
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
function Dot({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />;
}
function Square({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5" style={{ background: color }} />;
}
function Diamond() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14">
      <polygon points="7,2 12,7 7,12 2,7" fill="#22c55e" />
    </svg>
  );
}
function StarSwatch() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14">
      {drawStar(7, 7, 5, "#fbbf24")}
    </svg>
  );
}
function Line() {
  return (
    <svg width="20" height="6">
      <line x1="0" x2="20" y1="3" y2="3" stroke="currentColor" strokeWidth="2" opacity="0.8" />
    </svg>
  );
}

function drawStar(
  cx: number,
  cy: number,
  r: number,
  fill: string,
  stroke?: string,
  strokeWidth?: number,
  key?: string,
) {
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const angle = (Math.PI * i) / 5 - Math.PI / 2;
    const radius = i % 2 === 0 ? r : r * 0.45;
    pts.push(
      `${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`,
    );
  }
  return (
    <polygon
      key={key}
      points={pts.join(" ")}
      fill={fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
    />
  );
}
