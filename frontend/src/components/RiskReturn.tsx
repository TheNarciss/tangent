import { useMemo, useState } from "react";

import type { AssetMetrics, EnvelopePoint, FrontierCloud, FrontierCurve, PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ChartTooltip";

interface Props {
  metrics: PortfolioMetrics;
  frontier: FrontierCloud;
  smoothFrontier?: FrontierCurve;
  optimal?: { sigma: number; mu: number; label: string };
  envelopePoints?: EnvelopePoint[];
}

type HoverInfo =
  | { kind: "asset"; idx: number }
  | { kind: "portfolio" }
  | { kind: "optimal" }
  | null;

const W = 640;
const H = 380;
const PAD = { top: 24, right: 24, bottom: 48, left: 64 };
const ASSET_COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6", "#10b981", "#ef4444"];

/**
 * Chart Risque-Rendement SIMPLIFIÉ.
 *
 * Principe : aucun label texte dans le SVG (sauf axes). Toutes les infos
 * sont dans le panneau de droite — légende interactive avec dot couleur,
 * ticker, μ, σ. Hover ligne = highlight dot dans le chart. Plus de problème
 * de chevauchement, plus de placement compliqué.
 */
export function RiskReturn({ metrics, frontier, smoothFrontier, optimal, envelopePoints }: Props) {
  const [hover, setHover] = useState<HoverInfo>(null);
  const [wrapW, setWrapW] = useState(W);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const envelopeGroups = useMemo(() => groupEnvelopesByReturn(envelopePoints ?? []), [envelopePoints]);

  const { xScale, yScale, xTicks, yTicks, cloudFill, xCap, yCapMin, yCapMax } = useMemo(
    () => buildScales(
      frontier, metrics.assets,
      { sigma: metrics.volatility, mu: metrics.expected_return },
      smoothFrontier, optimal,
    ),
    [frontier, metrics.assets, metrics.volatility, metrics.expected_return, smoothFrontier, optimal],
  );

  // Sample cloud down to ~600 points
  const cloudIndices = useMemo(() => {
    const total = frontier.vol.length;
    const cap = 600;
    if (total <= cap) return Array.from({ length: total }, (_, i) => i);
    const step = total / cap;
    return Array.from({ length: cap }, (_, i) => Math.floor(i * step));
  }, [frontier.vol.length]);

  const handleSvgEnter = (e: React.MouseEvent<SVGSVGElement>) => {
    setWrapW(e.currentTarget.getBoundingClientRect().width);
  };

  const tooltipPos = (() => {
    if (!hover) return null;
    if (hover.kind === "asset") {
      const a = metrics.assets[hover.idx];
      return { cx: xScale(a.annual_vol), cy: yScale(a.annual_return) };
    }
    if (hover.kind === "portfolio") {
      return { cx: xScale(metrics.volatility), cy: yScale(metrics.expected_return) };
    }
    if (hover.kind === "optimal" && optimal) {
      return { cx: xScale(optimal.sigma), cy: yScale(optimal.mu) };
    }
    return null;
  })();

  const frontierPath = smoothFrontier && smoothFrontier.vol.length > 1
    ? smoothFrontier.vol
        .map((v, i) => `${i === 0 ? "M" : "L"}${xScale(v).toFixed(2)},${yScale(smoothFrontier.ret[i]).toFixed(2)}`)
        .join(" ")
    : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Risque–Rendement
        </CardTitle>
        <CardDescription>
          Chaque ETF est un point coloré dans l'espace (σ, μ). La courbe blanche est la frontière efficiente.
          Détails dans le panneau de droite — survole une ligne pour identifier le point dans le chart.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Chart à gauche */}
          <div className="relative flex-1 min-w-0">
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Diagramme risque-rendement"
                 onMouseEnter={handleSvgEnter}>
              {/* Gridlines */}
              <g stroke="hsl(var(--border))" strokeWidth="0.5" opacity="0.4" style={{ pointerEvents: "none" }}>
                {xTicks.map((t) => (
                  <line key={`gx-${t}`} x1={xScale(t)} x2={xScale(t)} y1={PAD.top} y2={PAD.top + innerH} />
                ))}
                {yTicks.map((t) => (
                  <line key={`gy-${t}`} x1={PAD.left} x2={PAD.left + innerW} y1={yScale(t)} y2={yScale(t)} />
                ))}
              </g>

              {/* Cloud MC — pointer-events-none */}
              <g style={{ pointerEvents: "none" }}>
                {cloudIndices.map((idx) => {
                  const v = frontier.vol[idx];
                  const r = frontier.ret[idx];
                  if (v > xCap || r < yCapMin || r > yCapMax) return null;
                  return (
                    <circle key={idx} cx={xScale(v)} cy={yScale(r)} r={1.1}
                            fill={cloudFill(frontier.sharpe[idx])} opacity={0.25} />
                  );
                })}
              </g>

              {/* Frontière efficiente */}
              {frontierPath && (
                <path d={frontierPath} fill="none" stroke="hsl(var(--foreground))" strokeWidth="2" opacity="0.8"
                      strokeLinecap="round" strokeLinejoin="round" style={{ pointerEvents: "none" }} />
              )}

              {/* Axes */}
              <g stroke="hsl(var(--foreground))" strokeWidth="1" style={{ pointerEvents: "none" }}>
                <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + innerH} />
                <line x1={PAD.left} x2={PAD.left + innerW} y1={PAD.top + innerH} y2={PAD.top + innerH} />
              </g>

              {/* X ticks */}
              <g className="font-mono text-[10px] fill-current text-muted-foreground" style={{ pointerEvents: "none" }}>
                {xTicks.map((t) => (
                  <g key={`xt-${t}`}>
                    <line x1={xScale(t)} x2={xScale(t)} y1={PAD.top + innerH} y2={PAD.top + innerH + 4} stroke="currentColor" />
                    <text x={xScale(t)} y={PAD.top + innerH + 18} textAnchor="middle">{fmt.pct(t)}</text>
                  </g>
                ))}
                <text x={PAD.left + innerW / 2} y={H - 8} textAnchor="middle" className="font-sans text-xs">
                  Volatilité σ (annualisée)
                </text>
              </g>

              {/* Y ticks */}
              <g className="font-mono text-[10px] fill-current text-muted-foreground" style={{ pointerEvents: "none" }}>
                {yTicks.map((t) => (
                  <g key={`yt-${t}`}>
                    <line x1={PAD.left - 4} x2={PAD.left} y1={yScale(t)} y2={yScale(t)} stroke="currentColor" />
                    <text x={PAD.left - 8} y={yScale(t) + 3} textAnchor="end">{fmt.pct(t)}</text>
                  </g>
                ))}
                <text x={-(PAD.top + innerH / 2)} y={16} textAnchor="middle" transform="rotate(-90)" className="font-sans text-xs">
                  Rendement μ
                </text>
              </g>

              {/* Asset dots — hit-area transparente r=14, dot visible r=8 fixe (no scaling = no flicker) */}
              {metrics.assets.map((a, i) => {
                const cx = xScale(a.annual_vol);
                const cy = yScale(a.annual_return);
                const isHover = hover?.kind === "asset" && hover.idx === i;
                return (
                  <g key={`asset-${i}`}>
                    <circle cx={cx} cy={cy} r={14} fill="transparent"
                            className="cursor-pointer"
                            onMouseEnter={() => setHover({ kind: "asset", idx: i })}
                            onMouseLeave={() => setHover(null)} />
                    <circle cx={cx} cy={cy} r={isHover ? 10 : 8}
                            fill={ASSET_COLORS[i % ASSET_COLORS.length]}
                            stroke={isHover ? "hsl(var(--foreground))" : "hsl(var(--background))"}
                            strokeWidth={isHover ? 2.5 : 2}
                            style={{ pointerEvents: "none" }} />
                  </g>
                );
              })}

              {/* Portfolio diamond */}
              <g>
                <circle cx={xScale(metrics.volatility)} cy={yScale(metrics.expected_return)} r={16}
                        fill="transparent" className="cursor-pointer"
                        onMouseEnter={() => setHover({ kind: "portfolio" })}
                        onMouseLeave={() => setHover(null)} />
                <g transform={`translate(${xScale(metrics.volatility)}, ${yScale(metrics.expected_return)})`}
                   style={{ pointerEvents: "none" }}>
                  <polygon points="0,-10 10,0 0,10 -10,0"
                    fill="hsl(var(--gain))" stroke="hsl(var(--background))" strokeWidth="2" />
                </g>
              </g>

              {/* Optimal star */}
              {optimal && (
                <g>
                  <circle cx={xScale(optimal.sigma)} cy={yScale(optimal.mu)} r={16}
                          fill="transparent" className="cursor-pointer"
                          onMouseEnter={() => setHover({ kind: "optimal" })}
                          onMouseLeave={() => setHover(null)} />
                  <g transform={`translate(${xScale(optimal.sigma)}, ${yScale(optimal.mu)})`}
                     style={{ pointerEvents: "none" }}>
                    <text x={0} y={7} textAnchor="middle" fontSize="26"
                          style={{ fill: "hsl(45 95% 55%)" }}>★</text>
                  </g>
                </g>
              )}
            </svg>

            {hover && tooltipPos && (
              <ChartTooltip cx={tooltipPos.cx} cy={tooltipPos.cy} containerW={wrapW} vbW={W} vbH={H}>
                {hover.kind === "asset" ? <AssetTooltip asset={metrics.assets[hover.idx]} />
                : hover.kind === "portfolio" ? <PortfolioTooltip metrics={metrics} />
                : optimal ? <OptimalTooltip optimal={optimal} /> : null}
              </ChartTooltip>
            )}
          </div>

          {/* Panneau droite : assets + envelopes */}
          <div className="lg:w-64 shrink-0 space-y-3">
            <AssetsLegend assets={metrics.assets} hover={hover} setHover={setHover} optimal={optimal} portfolio={metrics} />
            {envelopeGroups.length > 0 && <EnvelopesPanel groups={envelopeGroups} />}
          </div>
        </div>

        <Legend hasFrontier={!!smoothFrontier} optimalLabel={optimal?.label} />
      </CardContent>
    </Card>
  );
}

/* ─── Panneaux ─────────────────────────────────────────────────────── */

function AssetsLegend({
  assets, hover, setHover, optimal, portfolio,
}: {
  assets: AssetMetrics[];
  hover: HoverInfo;
  setHover: (h: HoverInfo) => void;
  optimal?: { sigma: number; mu: number; label: string };
  portfolio: PortfolioMetrics;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-2">
      <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        Actifs risqués
      </div>
      <div className="space-y-1">
        {assets.map((a, i) => {
          const isHover = hover?.kind === "asset" && hover.idx === i;
          return (
            <div
              key={a.ticker}
              className={`flex items-center justify-between gap-2 px-1.5 py-1 rounded text-xs cursor-pointer transition-colors ${
                isHover ? "bg-muted/60" : "hover:bg-muted/30"
              }`}
              onMouseEnter={() => setHover({ kind: "asset", idx: i })}
              onMouseLeave={() => setHover(null)}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ background: ASSET_COLORS[i % ASSET_COLORS.length] }} />
                <span className="font-mono truncate">{a.ticker}</span>
              </div>
              <div className="flex gap-2 font-mono tabular text-[10px] shrink-0">
                <span className="text-muted-foreground">σ {fmt.pct(a.annual_vol)}</span>
                <span className="text-foreground">μ {fmt.pct(a.annual_return)}</span>
              </div>
            </div>
          );
        })}
        {/* Portfolio + optimal lines */}
        <div className="pt-1.5 border-t border-border space-y-1">
          <div
            className={`flex items-center justify-between gap-2 px-1.5 py-1 rounded text-xs cursor-pointer transition-colors ${
              hover?.kind === "portfolio" ? "bg-muted/60" : "hover:bg-muted/30"
            }`}
            onMouseEnter={() => setHover({ kind: "portfolio" })}
            onMouseLeave={() => setHover(null)}
          >
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rotate-45 bg-[hsl(var(--gain))]" />
              <span className="font-sans">Position actuelle</span>
            </div>
            <span className="font-mono tabular text-[10px] text-foreground">
              μ {fmt.pct(portfolio.expected_return)}
            </span>
          </div>
          {optimal && (
            <div
              className={`flex items-center justify-between gap-2 px-1.5 py-1 rounded text-xs cursor-pointer transition-colors ${
                hover?.kind === "optimal" ? "bg-muted/60" : "hover:bg-muted/30"
              }`}
              onMouseEnter={() => setHover({ kind: "optimal" })}
              onMouseLeave={() => setHover(null)}
            >
              <div className="flex items-center gap-2">
                <span className="inline-block text-[14px] leading-none" style={{ color: "hsl(45 95% 55%)" }}>★</span>
                <span className="font-sans">{optimal.label}</span>
              </div>
              <span className="font-mono tabular text-[10px] text-foreground">
                μ {fmt.pct(optimal.mu)}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EnvelopesPanel({ groups }: { groups: EnvelopeGroup[] }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-2">
      <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        Sans risque · σ ≈ 0
      </div>
      <div className="space-y-1">
        {groups.map((g, i) => (
          <div key={i} className="flex items-center justify-between text-xs gap-2 px-1.5 py-1">
            <div className="flex items-center gap-2 min-w-0">
              <span className="inline-block h-2.5 w-2.5 shrink-0" style={{ background: "hsl(150 70% 45%)" }} />
              <span className="font-mono truncate" title={g.members.join(" · ")}>
                {g.count === 1 ? g.label : `${g.count} livrets`}
              </span>
            </div>
            <span className="font-mono tabular text-foreground shrink-0">{fmt.pct(g.expected_return)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Tooltips ─────────────────────────────────────────────────────── */

function AssetTooltip({ asset }: { asset: AssetMetrics }) {
  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium text-foreground">{asset.ticker}</div>
      <TooltipRow label="Rendement μ" value={`${fmt.pct(asset.annual_return)} /an`} />
      <TooltipRow label="Volatilité σ" value={`${fmt.pct(asset.annual_vol)} /an`} />
      <TooltipRow label="Sharpe" value={asset.sharpe.toFixed(2)} />
      <TooltipRow label="Poids" value={fmt.pct(asset.weight)} />
    </div>
  );
}

function PortfolioTooltip({ metrics }: { metrics: PortfolioMetrics }) {
  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium text-foreground">Portefeuille global</div>
      <TooltipRow label="Rendement μ" value={`${fmt.pct(metrics.expected_return)} /an`} />
      <TooltipRow label="Volatilité σ" value={`${fmt.pct(metrics.volatility)} /an`} />
      <TooltipRow label="Sharpe" value={metrics.sharpe.toFixed(2)} bold />
    </div>
  );
}

function OptimalTooltip({ optimal }: { optimal: { sigma: number; mu: number; label: string } }) {
  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium" style={{ color: "hsl(45 95% 55%)" }}>{optimal.label}</div>
      <TooltipRow label="Rendement μ" value={`${fmt.pct(optimal.mu)} /an`} />
      <TooltipRow label="Volatilité σ" value={`${fmt.pct(optimal.sigma)} /an`} />
    </div>
  );
}

function TooltipRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between gap-3 font-mono tabular">
      <span className="font-sans text-muted-foreground">{label}</span>
      <span className={bold ? "font-semibold" : ""}>{value}</span>
    </div>
  );
}

function Legend({ hasFrontier, optimalLabel }: { hasFrontier?: boolean; optimalLabel?: string }) {
  return (
    <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
      <span className="flex items-center gap-2">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: "hsl(220 65% 60%)" }} />
        Nuage : Sharpe faible
      </span>
      <span className="flex items-center gap-2">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: "hsl(0 75% 55%)" }} />
        Nuage : Sharpe élevé
      </span>
      {hasFrontier && (
        <span className="flex items-center gap-2">
          <svg width="20" height="6"><line x1="0" x2="20" y1="3" y2="3" stroke="hsl(var(--foreground))" strokeWidth="2" opacity="0.8" /></svg>
          Frontière efficiente
        </span>
      )}
    </div>
  );
}

/* ─── Helpers ──────────────────────────────────────────────────────── */

interface EnvelopeGroup {
  label: string;
  members: string[];
  count: number;
  volatility: number;
  expected_return: number;
}

function groupEnvelopesByReturn(envelopes: EnvelopePoint[]): EnvelopeGroup[] {
  const map = new Map<string, EnvelopeGroup>();
  envelopes.forEach((e) => {
    const key = (Math.round(e.expected_return * 200) / 200).toFixed(3);
    if (!map.has(key)) {
      map.set(key, {
        label: e.label, members: [e.label], count: 1,
        volatility: e.volatility, expected_return: e.expected_return,
      });
    } else {
      const g = map.get(key)!;
      g.members.push(e.label);
      g.count++;
    }
  });
  return Array.from(map.values()).sort((a, b) => b.expected_return - a.expected_return);
}

interface Extents { xMin: number; xMax: number; yMin: number; yMax: number; }

function buildScales(
  frontier: FrontierCloud,
  assets: AssetMetrics[],
  portfolio: { sigma: number; mu: number },
  smoothFrontier?: FrontierCurve,
  optimal?: { sigma: number; mu: number },
) {
  // Anchors : assets + portfolio + optimal + frontière. PAS d'envelopes (séparé).
  const anchorXs = [
    ...assets.map((a) => a.annual_vol),
    portfolio.sigma,
    ...(smoothFrontier?.vol ?? []),
    ...(optimal ? [optimal.sigma] : []),
  ];
  const anchorYs = [
    ...assets.map((a) => a.annual_return),
    portfolio.mu,
    ...(smoothFrontier?.ret ?? []),
    ...(optimal ? [optimal.mu] : []),
  ];

  const anchorXMin = Math.max(0, Math.min(...anchorXs) - 0.01);
  const anchorXMax = Math.max(...anchorXs);
  const anchorYMin = Math.min(...anchorYs);
  const anchorYMax = Math.max(...anchorYs);

  // CAPS STRICTS : limite ce que le cloud peut tirer hors range
  const xCap = anchorXMax * 1.10;
  const yRange = Math.max(anchorYMax - anchorYMin, 0.05);
  const yCapMax = anchorYMax + 0.30 * yRange;
  const yCapMin = Math.max(0, anchorYMin - 0.30 * yRange);   // pas de μ négatifs ! plancher à 0

  const cloudInXs = frontier.vol.filter((v) => v <= xCap && v >= anchorXMin);
  const cloudInYs = frontier.ret.filter((_, i) => {
    const v = frontier.vol[i];
    const r = frontier.ret[i];
    return v <= xCap && v >= anchorXMin && r >= yCapMin && r <= yCapMax;
  });

  const xMin = anchorXMin;
  const xMax = Math.max(anchorXMax, cloudInXs.length > 0 ? Math.max(...cloudInXs) : anchorXMax);
  const yMin = Math.min(anchorYMin, cloudInYs.length > 0 ? Math.min(...cloudInYs) : anchorYMin);
  const yMax = Math.max(anchorYMax, cloudInYs.length > 0 ? Math.max(...cloudInYs) : anchorYMax);

  // Padding modéré
  const xPad = (xMax - xMin) * 0.08;
  const yPad = (yMax - yMin) * 0.12;
  const ext: Extents = {
    xMin: Math.max(0, xMin - xPad),
    xMax: xMax + xPad,
    yMin: Math.max(0, yMin - yPad),       // jamais négatif
    yMax: yMax + yPad,
  };

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const xScale = (v: number) => PAD.left + ((v - ext.xMin) / (ext.xMax - ext.xMin)) * innerW;
  const yScale = (v: number) => PAD.top + innerH - ((v - ext.yMin) / (ext.yMax - ext.yMin)) * innerH;

  const sMin = Math.min(...frontier.sharpe);
  const sMax = Math.max(...frontier.sharpe);
  const cloudFill = (s: number) => {
    const t = sMax === sMin ? 0.5 : (s - sMin) / (sMax - sMin);
    const hue = 220 - t * 220;
    return `hsl(${hue} 70% 55%)`;
  };

  return {
    xScale, yScale,
    xTicks: niceTicks(ext.xMin, ext.xMax, 5),
    yTicks: niceTicks(ext.yMin, ext.yMax, 5),
    cloudFill,
    xCap, yCapMin, yCapMax,
  };
}

function niceTicks(min: number, max: number, count: number): number[] {
  const step = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step)));
  const norm = step / mag;
  const niceStep = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const start = Math.ceil(min / niceStep) * niceStep;
  const ticks: number[] = [];
  for (let v = start; v <= max; v += niceStep) ticks.push(Number(v.toFixed(10)));
  return ticks;
}