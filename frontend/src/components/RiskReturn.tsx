import { useMemo, useState } from "react";

import type { AssetMetrics, EnvelopePoint, FrontierCloud, FrontierCurve, PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  metrics: PortfolioMetrics;
  frontier?: FrontierCloud;
  smoothFrontier?: FrontierCurve;
  optimal?: { sigma: number; mu: number; label: string };
  envelopePoints?: EnvelopePoint[];
}

type Hover =
  | { kind: "point"; x: number; y: number; label: string; sigma: number; mu: number }
  | { kind: "envelopes"; x: number; y: number; items: EnvelopePoint[] }
  | null;

const W = 720;
const H = 440;
const PAD = { top: 20, right: 30, bottom: 60, left: 90 };
const ETF_COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6", "#10b981", "#ef4444"];

export function RiskReturn({ metrics, smoothFrontier, optimal, envelopePoints }: Props) {
  const [hover, setHover] = useState<Hover>(null);
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const envelopes = (envelopePoints ?? []).slice().sort((a, b) => b.expected_return - a.expected_return);
  const hasEnvelopes = envelopes.length > 0;

  const { xScale, yScale, xTicks, yTicks, envBand } = useMemo(() => {
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
    const xMin = hasEnvelopes ? 0 : Math.max(0, Math.min(...sigmas) - 0.005);
    const xMax = Math.max(...sigmas) + 0.015;
    const yMin = Math.min(...mus) - 0.015;
    const yMax = Math.max(...mus) + 0.015;

    const xS = (x: number) => PAD.left + (innerW * (x - xMin)) / Math.max(xMax - xMin, 1e-9);
    const yS = (y: number) => PAD.top + innerH - (innerH * (y - yMin)) / Math.max(yMax - yMin, 1e-9);

    let band: { x: number; y: number; w: number; h: number; muMin: number; muMax: number } | null = null;
    if (hasEnvelopes) {
      const muMinEnv = Math.min(...envelopes.map((e) => e.expected_return));
      const muMaxEnv = Math.max(...envelopes.map((e) => e.expected_return));
      const y1 = yS(muMaxEnv) - 4;
      const y2 = yS(muMinEnv) + 4;
      band = { x: xS(0) - 8, y: y1, w: 16, h: y2 - y1, muMin: muMinEnv, muMax: muMaxEnv };
    }

    return {
      xScale: xS,
      yScale: yS,
      xTicks: niceTicks(xMin, xMax, 6),
      yTicks: niceTicks(yMin, yMax, 6),
      envBand: band,
    };
  }, [metrics, envelopes, optimal, smoothFrontier, hasEnvelopes, innerW, innerH]);

  const frontierPath = smoothFrontier && smoothFrontier.vol.length > 1
    ? smoothFrontier.vol
        .map((v, i) => `${i === 0 ? "M" : "L"}${xScale(v).toFixed(2)},${yScale(smoothFrontier.ret[i]).toFixed(2)}`)
        .join(" ")
    : null;

  const portfolioCx = xScale(metrics.volatility);
  const portfolioCy = yScale(metrics.expected_return);
  const optimalCx = optimal ? xScale(optimal.sigma) : 0;
  const optimalCy = optimal ? yScale(optimal.mu) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Risque–Rendement
        </CardTitle>
        <CardDescription>
          Carte (σ, μ) de ton univers. Survole un point pour voir ses détails.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img">
          {/* Grid */}
          <g stroke="hsl(var(--border))" strokeWidth="0.5" opacity="0.3" style={{ pointerEvents: "none" }}>
            {xTicks.map((t) => (
              <line key={`gx-${t}`} x1={xScale(t)} x2={xScale(t)} y1={PAD.top} y2={PAD.top + innerH} />
            ))}
            {yTicks.map((t) => (
              <line key={`gy-${t}`} x1={PAD.left} x2={PAD.left + innerW} y1={yScale(t)} y2={yScale(t)} />
            ))}
          </g>

          {/* Axes */}
          <g stroke="hsl(var(--foreground))" strokeWidth="1" style={{ pointerEvents: "none" }}>
            <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + innerH} />
            <line x1={PAD.left} x2={PAD.left + innerW} y1={PAD.top + innerH} y2={PAD.top + innerH} />
          </g>

          {/* X labels */}
          <g className="font-mono text-[10px] fill-current text-muted-foreground" style={{ pointerEvents: "none" }}>
            {xTicks.map((t) => (
              <g key={`xl-${t}`}>
                <line x1={xScale(t)} x2={xScale(t)} y1={PAD.top + innerH} y2={PAD.top + innerH + 4} stroke="currentColor" />
                <text x={xScale(t)} y={PAD.top + innerH + 18} textAnchor="middle">{fmt.pct(t)}</text>
              </g>
            ))}
            <text x={PAD.left + innerW / 2} y={H - 14} textAnchor="middle" className="font-sans text-xs">
              Volatilité σ (annualisée)
            </text>
          </g>

          {/* Y labels */}
          <g className="font-mono text-[10px] fill-current text-muted-foreground" style={{ pointerEvents: "none" }}>
            {yTicks.map((t) => (
              <g key={`yl-${t}`}>
                <line x1={PAD.left - 4} x2={PAD.left} y1={yScale(t)} y2={yScale(t)} stroke="currentColor" />
                <text x={PAD.left - 8} y={yScale(t) + 3} textAnchor="end">{fmt.pct(t)}</text>
              </g>
            ))}
            <text x={-(PAD.top + innerH / 2)} y={28} textAnchor="middle" transform="rotate(-90)" className="font-sans text-xs">
              Rendement μ annualisé
            </text>
          </g>

          {/* Frontière */}
          {frontierPath && (
            <path d={frontierPath} fill="none" stroke="hsl(var(--foreground))" strokeWidth="2" opacity="0.7"
                  strokeLinecap="round" strokeLinejoin="round" style={{ pointerEvents: "none" }} />
          )}

          {/* Zone livrets unique */}
          {envBand && (
            <g>
              <rect x={envBand.x} y={envBand.y} width={envBand.w} height={envBand.h}
                    fill="#10b981" opacity={0.7} rx={3}
                    stroke="hsl(var(--background))" strokeWidth={1.5}
                    className="cursor-pointer"
                    onMouseEnter={() => setHover({
                      kind: "envelopes",
                      x: envBand.x + envBand.w / 2,
                      y: envBand.y + envBand.h / 2,
                      items: envelopes,
                    })}
                    onMouseLeave={() => setHover(null)} />
              <text x={envBand.x + envBand.w + 6} y={envBand.y + envBand.h / 2 + 4}
                    className="font-mono text-[10px] fill-current"
                    style={{ pointerEvents: "none" }}>
                {envelopes.length}× livrets
              </text>
            </g>
          )}

          {/* ETFs */}
          {metrics.assets.map((a, i) => {
            const cx = xScale(a.annual_vol);
            const cy = yScale(a.annual_return);
            const color = ETF_COLORS[i % ETF_COLORS.length];
            return (
              <g key={`etf-${i}`}
                 onMouseEnter={() => setHover({ kind: "point", x: cx, y: cy, label: a.ticker, sigma: a.annual_vol, mu: a.annual_return })}
                 onMouseLeave={() => setHover(null)}>
                <circle cx={cx} cy={cy} r={10} fill={color} stroke="hsl(var(--background))" strokeWidth={2} className="cursor-pointer" />
                <text x={cx + 15} y={cy + 4} className="font-mono text-[11px] fill-current" style={{ pointerEvents: "none" }}>
                  {a.ticker.replace(".PA", "")}
                </text>
              </g>
            );
          })}

          {/* Position actuelle */}
          <g onMouseEnter={() => setHover({ kind: "point", x: portfolioCx, y: portfolioCy, label: "Position actuelle",
                                            sigma: metrics.volatility, mu: metrics.expected_return })}
             onMouseLeave={() => setHover(null)}>
            <polygon
              points={`${portfolioCx},${portfolioCy - 11} ${portfolioCx + 11},${portfolioCy} ${portfolioCx},${portfolioCy + 11} ${portfolioCx - 11},${portfolioCy}`}
              fill="#22c55e" stroke="hsl(var(--background))" strokeWidth={2} className="cursor-pointer" />
          </g>

          {/* Optimal */}
          {optimal && (
            <g onMouseEnter={() => setHover({ kind: "point", x: optimalCx, y: optimalCy, label: optimal.label, sigma: optimal.sigma, mu: optimal.mu })}
               onMouseLeave={() => setHover(null)} className="cursor-pointer">
              {drawStar(optimalCx, optimalCy, 13, "#fbbf24", "hsl(var(--background))", 2)}
            </g>
          )}

          {/* Tooltip — point simple OU liste livrets */}
          {hover && hover.kind === "point" && (
            <g style={{ pointerEvents: "none" }}>
              <rect x={Math.min(hover.x + 14, PAD.left + innerW - 160)}
                    y={Math.max(hover.y - 40, PAD.top + 4)}
                    width={155} height={40} fill="hsl(var(--card))"
                    stroke="hsl(var(--border))" strokeWidth={1} rx={4} opacity={0.96} />
              <text x={Math.min(hover.x + 22, PAD.left + innerW - 152)}
                    y={Math.max(hover.y - 22, PAD.top + 22)}
                    className="font-semibold text-[12px] fill-current">
                {hover.label}
              </text>
              <text x={Math.min(hover.x + 22, PAD.left + innerW - 152)}
                    y={Math.max(hover.y - 8, PAD.top + 36)}
                    className="font-mono text-[10px] fill-current text-muted-foreground">
                σ {fmt.pct(hover.sigma)} · μ {fmt.pct(hover.mu)}
              </text>
            </g>
          )}

          {hover && hover.kind === "envelopes" && (() => {
            const lineH = 16;
            const headerH = 22;
            const padding = 8;
            const tooltipW = 200;
            const tooltipH = headerH + hover.items.length * lineH + padding;
            const tx = Math.min(hover.x + 14, PAD.left + innerW - tooltipW - 4);
            const ty = Math.min(Math.max(hover.y - tooltipH / 2, PAD.top + 4), PAD.top + innerH - tooltipH - 4);
            return (
              <g style={{ pointerEvents: "none" }}>
                <rect x={tx} y={ty} width={tooltipW} height={tooltipH}
                      fill="hsl(var(--card))" stroke="hsl(var(--border))" strokeWidth={1} rx={4} opacity={0.97} />
                <text x={tx + 10} y={ty + 16} className="font-semibold text-[12px] fill-current" style={{ fill: "#10b981" }}>
                  {hover.items.length} livret{hover.items.length > 1 ? 's' : ''} · σ ≈ 0
                </text>
                {hover.items.map((e, i) => (
                  <g key={i}>
                    <text x={tx + 10} y={ty + headerH + (i + 1) * lineH - 4}
                          className="font-mono text-[10px] fill-current">
                      {e.label.length > 24 ? e.label.slice(0, 22) + '…' : e.label}
                    </text>
                    <text x={tx + tooltipW - 10} y={ty + headerH + (i + 1) * lineH - 4}
                          textAnchor="end"
                          className="font-mono text-[10px] font-semibold fill-current"
                          style={{ fill: "#10b981" }}>
                      {fmt.pct(e.expected_return)}
                    </text>
                  </g>
                ))}
              </g>
            );
          })()}
        </svg>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
          <LegendItem swatch={<Dot color="#60a5fa" />} label="ETF" />
          {hasEnvelopes && <LegendItem swatch={<Square color="#10b981" />} label="Livrets (σ ≈ 0)" />}
          <LegendItem swatch={<Diamond />} label="Position actuelle" />
          {optimal && <LegendItem swatch={<StarSwatch />} label={optimal.label} />}
          {frontierPath && <LegendItem swatch={<Line />} label="Frontière efficiente" />}
        </div>
      </CardContent>
    </Card>
  );
}

function LegendItem({ swatch, label }: { swatch: React.ReactNode; label: string }) {
  return <span className="flex items-center gap-2">{swatch}{label}</span>;
}
function Dot({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />;
}
function Square({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5" style={{ background: color }} />;
}
function Diamond() {
  return <svg width="14" height="14" viewBox="0 0 14 14"><polygon points="7,2 12,7 7,12 2,7" fill="#22c55e" /></svg>;
}
function StarSwatch() {
  return <svg width="14" height="14" viewBox="0 0 14 14">{drawStar(7, 7, 5, "#fbbf24")}</svg>;
}
function Line() {
  return <svg width="20" height="6"><line x1="0" x2="20" y1="3" y2="3" stroke="currentColor" strokeWidth="2" opacity="0.8" /></svg>;
}

function drawStar(cx: number, cy: number, r: number, fill: string, stroke?: string, strokeWidth?: number) {
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const angle = (Math.PI * i) / 5 - Math.PI / 2;
    const radius = i % 2 === 0 ? r : r * 0.45;
    pts.push(`${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`);
  }
  return <polygon points={pts.join(" ")} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
}

function niceTicks(min: number, max: number, n: number): number[] {
  const range = Math.max(max - min, 1e-9);
  const step0 = range / n;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const norm = step0 / mag;
  let step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
  step *= mag;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) out.push(Math.round(v / step) * step);
  return out;
}