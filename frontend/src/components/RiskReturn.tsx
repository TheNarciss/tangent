import { useMemo, useState } from "react";

import type { AssetMetrics, FrontierCloud, FrontierCurve, PortfolioMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartTooltip } from "@/components/ChartTooltip";

interface Props {
  metrics: PortfolioMetrics;
  frontier: FrontierCloud;
  /** Smooth efficient frontier from SLSQP (optional). Drawn as a line overlay. */
  smoothFrontier?: FrontierCurve;
  /** Optimal portfolio point (optional). Drawn as a star. */
  optimal?: { sigma: number; mu: number; label: string };
}

type HoverInfo =
  | { kind: "asset"; idx: number }
  | { kind: "portfolio" }
  | { kind: "optimal" }
  | null;

const W = 720;
const H = 420;
const PAD = { top: 24, right: 24, bottom: 48, left: 64 };
const ASSET_COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6"];

/**
 * Risk–return chart (σ, μ) with the Monte-Carlo simplex cloud as background.
 * Each cloud point is shaded by Sharpe ratio. Each asset of the portfolio is a
 * labeled colored dot. The current portfolio is a green diamond.
 */
export function RiskReturn({ metrics, frontier, smoothFrontier, optimal }: Props) {
  const { xScale, yScale, xTicks, yTicks, cloudFill } = useMemo(
    () => buildScales(frontier, metrics.assets,
                      { sigma: metrics.volatility, mu: metrics.expected_return },
                      smoothFrontier, optimal),
    [frontier, metrics.assets, metrics.volatility, metrics.expected_return, smoothFrontier, optimal],
  );

  const [hover, setHover] = useState<HoverInfo>(null);
  const [wrapW, setWrapW] = useState(W);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const handleSvgEnter = (e: React.MouseEvent<SVGSVGElement>) => {
    setWrapW(e.currentTarget.getBoundingClientRect().width);
  };

  // Hovered position in container-pixel space (for tooltip placement)
  const tooltipPos = (() => {
    if (!hover) return null;
    if (hover.kind === "asset") {
      return { cx: xScale(metrics.assets[hover.idx].annual_vol), cy: yScale(metrics.assets[hover.idx].annual_return) };
    }
    if (hover.kind === "portfolio") {
      return { cx: xScale(metrics.volatility), cy: yScale(metrics.expected_return) };
    }
    if (hover.kind === "optimal" && optimal) {
      return { cx: xScale(optimal.sigma), cy: yScale(optimal.mu) };
    }
    return null;
  })();

  // Build smooth-frontier path
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
          Nuage de {frontier.vol.length} portefeuilles long-only simulés. La frontière efficiente est l'enveloppe supérieure-gauche.
          Survole les points pour les détails.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative w-full overflow-x-auto">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Diagramme risque-rendement"
               onMouseEnter={handleSvgEnter}>
            {/* Gridlines */}
            <g stroke="hsl(var(--border))" strokeWidth="0.5" opacity="0.5">
              {xTicks.map((t) => (
                <line key={`vx-${t}`} x1={xScale(t)} x2={xScale(t)} y1={PAD.top} y2={PAD.top + innerH} />
              ))}
              {yTicks.map((t) => (
                <line key={`vy-${t}`} x1={PAD.left} x2={PAD.left + innerW} y1={yScale(t)} y2={yScale(t)} />
              ))}
            </g>

            {/* Monte-Carlo cloud */}
            <g>
              {frontier.vol.map((v, i) => (
                <circle key={i} cx={xScale(v)} cy={yScale(frontier.ret[i])} r={1.5} fill={cloudFill(frontier.sharpe[i])} opacity={0.55} />
              ))}
            </g>

            {/* Smooth efficient frontier (SLSQP) */}
            {frontierPath && (
              <path d={frontierPath} fill="none" stroke="hsl(var(--foreground))" strokeWidth="2" opacity="0.7"
                    strokeLinecap="round" strokeLinejoin="round" />
            )}

            {/* Axes */}
            <g stroke="hsl(var(--foreground))" strokeWidth="1">
              <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + innerH} />
              <line x1={PAD.left} x2={PAD.left + innerW} y1={PAD.top + innerH} y2={PAD.top + innerH} />
            </g>

            {/* X ticks + labels */}
            <g className="font-mono text-[10px] fill-current text-muted-foreground">
              {xTicks.map((t) => (
                <g key={`xt-${t}`}>
                  <line x1={xScale(t)} x2={xScale(t)} y1={PAD.top + innerH} y2={PAD.top + innerH + 4} stroke="currentColor" />
                  <text x={xScale(t)} y={PAD.top + innerH + 18} textAnchor="middle">{fmt.pct(t)}</text>
                </g>
              ))}
              <text x={PAD.left + innerW / 2} y={H - 8} textAnchor="middle" className="font-sans text-xs">
                Volatilité annualisée (σ)
              </text>
            </g>

            {/* Y ticks + labels */}
            <g className="font-mono text-[10px] fill-current text-muted-foreground">
              {yTicks.map((t) => (
                <g key={`yt-${t}`}>
                  <line x1={PAD.left - 4} x2={PAD.left} y1={yScale(t)} y2={yScale(t)} stroke="currentColor" />
                  <text x={PAD.left - 8} y={yScale(t) + 3} textAnchor="end">{fmt.pct(t)}</text>
                </g>
              ))}
              <text
                x={-(PAD.top + innerH / 2)}
                y={16}
                textAnchor="middle"
                transform="rotate(-90)"
                className="font-sans text-xs"
              >
                Rendement attendu (μ)
              </text>
            </g>

            {/* Asset points */}
            {metrics.assets.map((a, i) => (
              <g key={a.ticker}>
                <circle
                  cx={xScale(a.annual_vol)}
                  cy={yScale(a.annual_return)}
                  r={hover?.kind === "asset" && hover.idx === i ? 10 : 8}
                  fill={ASSET_COLORS[i % ASSET_COLORS.length]}
                  stroke="hsl(var(--background))"
                  strokeWidth="2"
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHover({ kind: "asset", idx: i })}
                  onMouseLeave={() => setHover(null)}
                />
                <text
                  x={xScale(a.annual_vol) + 12}
                  y={yScale(a.annual_return) + 4}
                  className="font-mono text-[11px] fill-current pointer-events-none"
                >
                  {a.ticker}
                </text>
              </g>
            ))}

            {/* Portfolio point */}
            <g transform={`translate(${xScale(metrics.volatility)}, ${yScale(metrics.expected_return)})`}>
              <polygon
                points="0,-10 10,0 0,10 -10,0"
                fill="hsl(var(--gain))"
                stroke="hsl(var(--background))"
                strokeWidth="2"
                className="cursor-pointer"
                onMouseEnter={() => setHover({ kind: "portfolio" })}
                onMouseLeave={() => setHover(null)}
              />
              <text x={14} y={4} className="font-mono text-[11px] font-semibold fill-current pointer-events-none">
                Portefeuille
              </text>
            </g>

            {/* Optimal point (star) */}
            {optimal && (
              <g transform={`translate(${xScale(optimal.sigma)}, ${yScale(optimal.mu)})`}>
                <polygon
                  points="0,-12 3,-4 11,-4 5,2 7,11 0,6 -7,11 -5,2 -11,-4 -3,-4"
                  fill="hsl(45 95% 55%)"
                  stroke="hsl(var(--background))"
                  strokeWidth="1.5"
                  className="cursor-pointer"
                  onMouseEnter={() => setHover({ kind: "optimal" })}
                  onMouseLeave={() => setHover(null)}
                />
                <text x={16} y={4} className="font-mono text-[11px] font-semibold fill-current pointer-events-none"
                      style={{ fill: "hsl(45 95% 55%)" }}>
                  {optimal.label}
                </text>
              </g>
            )}
          </svg>

          {hover && tooltipPos && (
            <ChartTooltip
              x={(tooltipPos.cx / W) * wrapW}
              y={(tooltipPos.cy / H) * (wrapW * H / W)}
              containerWidth={wrapW}
            >
              {hover.kind === "asset" ? (
                <AssetTooltip asset={metrics.assets[hover.idx]} />
              ) : hover.kind === "portfolio" ? (
                <PortfolioTooltip metrics={metrics} />
              ) : optimal ? (
                <OptimalTooltip optimal={optimal} />
              ) : null}
            </ChartTooltip>
          )}
        </div>

        <Legend hasFrontier={!!smoothFrontier} optimalLabel={optimal?.label} />
      </CardContent>
    </Card>
  );
}

function AssetTooltip({ asset }: { asset: AssetMetrics }) {
  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium text-foreground">{asset.ticker}</div>
      <TooltipRow label="Rendement μ" value={`${fmt.pct(asset.annual_return)} /an`} />
      <TooltipRow label="Volatilité σ" value={`${fmt.pct(asset.annual_vol)} /an`} />
      <TooltipRow label="Sharpe" value={asset.sharpe.toFixed(2)} />
      <TooltipRow label="Poids" value={fmt.pct(asset.weight)} />
      <div className="font-sans text-[10px] text-muted-foreground pt-1 leading-tight">
        μ = moyenne annualisée des rendements log<br />
        σ = écart-type annualisé (mesure du risque)<br />
        Sharpe = (μ − r_f) / σ, avec r_f = 2,5 %
      </div>
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
      <div className="font-sans text-[10px] text-muted-foreground pt-1 leading-tight">
        Position du portefeuille pondéré dans l'espace risque-rendement. La frontière efficiente passe au-dessus de cette zone.
      </div>
    </div>
  );
}

function OptimalTooltip({ optimal }: { optimal: { sigma: number; mu: number; label: string } }) {
  return (
    <div className="space-y-1.5">
      <div className="font-sans font-medium" style={{ color: "hsl(45 95% 55%)" }}>{optimal.label}</div>
      <TooltipRow label="Rendement μ" value={`${fmt.pct(optimal.mu)} /an`} />
      <TooltipRow label="Volatilité σ" value={`${fmt.pct(optimal.sigma)} /an`} />
      <div className="font-sans text-[10px] text-muted-foreground pt-1 leading-tight">
        Point solution du solveur SLSQP. La courbe blanche est la frontière efficiente : tous les portefeuilles
        sur cette ligne sont Pareto-optimaux (impossible d'avoir plus de rendement à risque égal ou moins de risque à rendement égal).
      </div>
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
        Sharpe faible (nuage)
      </span>
      <span className="flex items-center gap-2">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: "hsl(0 75% 55%)" }} />
        Sharpe élevé (nuage)
      </span>
      {hasFrontier && (
        <span className="flex items-center gap-2">
          <svg width="20" height="6"><line x1="0" x2="20" y1="3" y2="3" stroke="hsl(var(--foreground))" strokeWidth="2" opacity="0.7" /></svg>
          Frontière efficiente
        </span>
      )}
      <span className="flex items-center gap-2">
        <span className="inline-block h-2.5 w-2.5 rotate-45 bg-[hsl(var(--gain))]" />
        Position actuelle
      </span>
      {optimalLabel && (
        <span className="flex items-center gap-2">
          <span className="inline-block text-[14px] leading-none" style={{ color: "hsl(45 95% 55%)" }}>★</span>
          {optimalLabel}
        </span>
      )}
    </div>
  );
}

interface Extents {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
}

function buildScales(
  frontier: FrontierCloud,
  assets: AssetMetrics[],
  portfolio: { sigma: number; mu: number },
  smoothFrontier?: FrontierCurve,
  optimal?: { sigma: number; mu: number },
) {
  const xs = [
    ...frontier.vol,
    ...assets.map((a) => a.annual_vol),
    portfolio.sigma,
    ...(smoothFrontier?.vol ?? []),
    ...(optimal ? [optimal.sigma] : []),
  ];
  const ys = [
    ...frontier.ret,
    ...assets.map((a) => a.annual_return),
    portfolio.mu,
    ...(smoothFrontier?.ret ?? []),
    ...(optimal ? [optimal.mu] : []),
  ];
  const ext: Extents = padExtent({
    xMin: Math.min(...xs),
    xMax: Math.max(...xs),
    yMin: Math.min(...ys),
    yMax: Math.max(...ys),
  });

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const xScale = (v: number) => PAD.left + ((v - ext.xMin) / (ext.xMax - ext.xMin)) * innerW;
  const yScale = (v: number) => PAD.top + innerH - ((v - ext.yMin) / (ext.yMax - ext.yMin)) * innerH;

  const sMin = Math.min(...frontier.sharpe);
  const sMax = Math.max(...frontier.sharpe);
  const cloudFill = (s: number) => {
    const t = sMax === sMin ? 0.5 : (s - sMin) / (sMax - sMin); // 0..1
    const hue = 220 - t * 220; // 220 (blue) → 0 (red)
    return `hsl(${hue} 70% 55%)`;
  };

  return {
    xScale,
    yScale,
    xTicks: niceTicks(ext.xMin, ext.xMax, 5),
    yTicks: niceTicks(ext.yMin, ext.yMax, 5),
    cloudFill,
  };
}

function padExtent({ xMin, xMax, yMin, yMax }: Extents): Extents {
  const xPad = (xMax - xMin) * 0.08;
  const yPad = (yMax - yMin) * 0.08;
  return { xMin: xMin - xPad, xMax: xMax + xPad, yMin: yMin - yPad, yMax: yMax + yPad };
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