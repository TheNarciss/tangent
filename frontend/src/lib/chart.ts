/**
 * Minimal chart utilities. Used by Timeline and (eventually) RiskReturn.
 *
 * Design: data-agnostic. Inputs are plain numbers and indices, outputs are SVG
 * strings or scaled coordinates. No d3, no recharts — the surface is small enough
 * that pulling a chart lib would cost more than it saves.
 */

export type Scale = (v: number) => number;

export function linearScale(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** Round (min, max) to ~`count` human-friendly ticks. */
export function niceTicks(min: number, max: number, count: number): number[] {
  if (!isFinite(min) || !isFinite(max) || min === max) return [min];
  const step = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(Math.abs(step))));
  const norm = step / mag;
  const niceStep = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const start = Math.ceil(min / niceStep) * niceStep;
  const ticks: number[] = [];
  for (let v = start; v <= max + 1e-12; v += niceStep) ticks.push(Number(v.toFixed(10)));
  return ticks;
}

/** Pick `count` evenly-spaced indices from an array of length `n`. */
export function pickIndices(n: number, count: number): number[] {
  if (n <= count) return [...Array(n).keys()];
  const step = (n - 1) / (count - 1);
  return Array.from({ length: count }, (_, i) => Math.round(i * step));
}

/**
 * Build an SVG path from index-keyed values, breaking the line on null/NaN.
 * @param values array of values (some possibly null)
 * @param x function index → x pixel
 * @param y function value → y pixel
 */
export function linePath(
  values: (number | null)[],
  x: (i: number) => number,
  y: Scale,
): string {
  let out = "";
  let pen: "M" | "L" = "M";
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v === null || !isFinite(v)) {
      pen = "M";
      continue;
    }
    out += `${pen}${x(i).toFixed(2)},${y(v).toFixed(2)} `;
    pen = "L";
  }
  return out.trim();
}

/**
 * Build an SVG filled-area path from a value series down to a baseline.
 * Assumes no nulls (caller should pre-fill with the baseline value).
 */
export function areaPath(
  values: number[],
  x: (i: number) => number,
  y: Scale,
  baseline: number,
): string {
  if (values.length === 0) return "";
  const yBase = y(baseline);
  let path = `M${x(0).toFixed(2)},${yBase.toFixed(2)} `;
  for (let i = 0; i < values.length; i++) {
    path += `L${x(i).toFixed(2)},${y(values[i]).toFixed(2)} `;
  }
  path += `L${x(values.length - 1).toFixed(2)},${yBase.toFixed(2)} Z`;
  return path;
}

/** Compact "MMM YYYY" for FR locale, e.g. "mars 2025". */
const fmtMonth = new Intl.DateTimeFormat("fr-FR", { month: "short", year: "numeric" });
export function formatDateTick(iso: string): string {
  return fmtMonth.format(new Date(iso));
}