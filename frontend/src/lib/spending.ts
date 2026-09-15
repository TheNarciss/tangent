import type { MonthSpending } from "@/api";

/** Key of the unlabelled bucket the backend sends. */
export const UNLABELLED = "autre";
/** Key of the fold: every labelled category outside the chart's slots. */
export const OTHERS = "__autres__";
/** How many categories get a hue of their own; the rest folds into OTHERS. */
export const STACK_SLOTS = 5;

/**
 * Series of the stacked chart, bottom to top: the window's biggest labelled
 * categories in rank order (one hue each), then the fold, then the unlabelled.
 * Ranked over the whole window so every month stacks in the same order.
 */
export function stackSeries(months: MonthSpending[], slots = STACK_SLOTS): string[] {
  const totals: Record<string, number> = {};
  for (const m of months)
    for (const [c, v] of Object.entries(m.by_category)) totals[c] = (totals[c] ?? 0) + v;
  const labelled = Object.entries(totals)
    .filter(([c, v]) => c !== UNLABELLED && v > 0)
    .sort((a, b) => b[1] - a[1]);
  const series = labelled.slice(0, slots).map(([c]) => c);
  if (labelled.length > slots) series.push(OTHERS);
  if ((totals[UNLABELLED] ?? 0) > 0) series.push(UNLABELLED);
  return series;
}

/** One month's value per series, the tail of the categories folded into OTHERS. */
export function monthStack(month: MonthSpending, series: string[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const s of series) out[s] = 0;
  for (const [c, v] of Object.entries(month.by_category)) {
    if (c in out) out[c] += v;
    else if (c !== UNLABELLED && OTHERS in out) out[OTHERS] += v;
  }
  return out;
}

export interface CategoryDelta {
  category: string;
  last: number; // spent in the last complete month
  average: number; // monthly average over the earlier complete months
  delta: number; // last − average
}

export interface DeltaReport {
  month: string; // the last complete month, "2026-08"
  baseline: number; // how many earlier complete months the average is over
  rows: CategoryDelta[]; // biggest moves first
}

/**
 * The last complete month against the average of the complete months before
 * it, per labelled category. The current month is left out: it is not over,
 * and half a month against a whole one would only ever read « moins ».
 * Null until there are two complete months to compare.
 */
export function categoryDeltas(months: MonthSpending[], top = 6): DeltaReport | null {
  const complete = months.slice(0, -1).filter((m) => m.total > 0);
  if (complete.length < 2) return null;
  const last = complete[complete.length - 1];
  const earlier = complete.slice(0, -1);

  const sums: Record<string, number> = {};
  for (const m of earlier)
    for (const [c, v] of Object.entries(m.by_category)) sums[c] = (sums[c] ?? 0) + v;
  const categories = new Set([...Object.keys(sums), ...Object.keys(last.by_category)]);
  categories.delete(UNLABELLED);

  const rows = [...categories]
    .map((category) => {
      const average = (sums[category] ?? 0) / earlier.length;
      const spent = last.by_category[category] ?? 0;
      return { category, last: spent, average, delta: spent - average };
    })
    .filter((r) => Math.abs(r.delta) >= 1)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, top);
  return { month: last.month, baseline: earlier.length, rows };
}
