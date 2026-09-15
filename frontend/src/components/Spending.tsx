import { useMemo, useState } from "react";

import { useSpending, type Merchant, type MonthSpending, type SpendingResponse } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { Chart, XAxis, YAxis, type ChartFrame } from "@/components/ui/chart";
import { t, useT, type MessageKey } from "@/i18n";
import { formatDate } from "@/lib/accounts";
import { linearScale, niceTicks } from "@/lib/chart";
import { fmt } from "@/lib/format";
import {
  OTHERS,
  UNLABELLED,
  categoryDeltas,
  monthStack,
  stackSeries,
  type DeltaReport,
} from "@/lib/spending";
import { cn } from "@/lib/utils";

/**
 * Dépenses — the current accounts, read the way a budgeting app reads them.
 *
 * One filter row (the period) scopes everything below it. Then, in the order
 * a person asks: the month's four figures (spent, received, what is left, the
 * observed saving rate), money in and out month by month, what it went on
 * month by month, where it goes over the window, what moved against the
 * habit, and at whom. « Voir le tableau » is the accessibility twin: every
 * number the charts show is readable there without hovering.
 *
 * Plain SVG and divs, no charting library. Categorical hues only where the
 * series are the subject (the stack), in a fixed validated order; one hue for
 * anything that is a single series; gain/loss tokens where a bar means
 * better/worse; text never wears the data colour; the current month is
 * lighter because it is not over.
 */
export function Spending() {
  const { t, tn } = useT();
  const [months, setMonths] = useState<3 | 6 | 12>(6);
  const [showTable, setShowTable] = useState(false);
  const { data, isLoading, isFetching } = useSpending(months);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-prose text-sm text-muted-foreground">{t("spending.intro")}</p>
        {/* One filter row above everything it scopes. */}
        <div className="flex shrink-0 items-center gap-1 rounded-md border p-0.5 text-xs">
          {([3, 6, 12] as const).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setMonths(n)}
              className={cn(
                "rounded px-2.5 py-1",
                months === n ? "bg-primary text-primary-foreground" : "hover:bg-accent",
              )}
            >
              {tn("spending.months", n)}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg bg-muted/30" />
            ))}
          </div>
          <div className="h-56 animate-pulse rounded-xl bg-muted/30" />
        </div>
      ) : data.months.every((m) => m.total === 0 && m.income === 0) ? (
        <section className="rounded-xl border bg-card p-4 md:p-6">
          <p className="text-sm text-muted-foreground">{t("spending.empty")}</p>
        </section>
      ) : (
        <div className={cn("space-y-6", isFetching && "opacity-70 transition-opacity")}>
          <Kpis data={data} />
          <section className="rounded-xl border bg-card p-4 md:p-6">
            <div className="flex items-start justify-between gap-3">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {t("spending.inOut.title")}
              </div>
              <button
                type="button"
                onClick={() => setShowTable((v) => !v)}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground hover:underline"
              >
                {showTable ? t("spending.showCharts") : t("spending.showTable")}
              </button>
            </div>
            {showTable ? (
              <MonthTable months={data.months} />
            ) : (
              <InOutColumns months={data.months} />
            )}
          </section>
          {!showTable && (
            <>
              <section className="rounded-xl border bg-card p-4 md:p-6">
                <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {t("spending.stack.title")}
                </div>
                {data.unlabelled_share > 0.2 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("spending.stack.unlabelled", { share: fmt.pct0(data.unlabelled_share) })}
                  </p>
                )}
                <CategoryStack months={data.months} />
              </section>
              <div className="grid gap-6 md:grid-cols-3">
                <section className="rounded-xl border bg-card p-4 md:p-6">
                  <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {t("spending.where.title")}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{t("spending.where.sub")}</p>
                  <CategoryBars categories={data.categories} />
                </section>
                <section className="rounded-xl border bg-card p-4 md:p-6">
                  <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {t("spending.moved.title")}
                  </div>
                  <CategoryDeltas report={categoryDeltas(data.months)} />
                </section>
                <section className="rounded-xl border bg-card p-4 md:p-6">
                  <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {t("spending.who.title")}
                  </div>
                  <MerchantBars merchants={data.merchants} />
                </section>
              </div>
            </>
          )}
          {showTable && <CategoryTable months={data.months} />}
        </div>
      )}
    </div>
  );
}

/* ── The month's four figures ──────────────────────────────────────────── */

function Kpis({ data }: { data: SpendingResponse }) {
  const { t } = useT();
  const current = data.months[data.months.length - 1];
  const left = current.income - current.total;
  const delta =
    data.monthly_average && data.monthly_average > 0
      ? current.total / data.monthly_average - 1
      : null;
  const complete = data.months.slice(0, -1).filter((m) => m.income > 0);
  const savedRate =
    complete.length > 0
      ? complete.reduce((s, m) => s + (m.income - m.total), 0) /
        complete.reduce((s, m) => s + m.income, 0)
      : null;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
      <BentoTile
        label={t("spending.kpi.spent")}
        value={fmt.eur0(current.total)}
        sub={
          delta !== null ? (
            <span className={delta > 0.1 ? "text-[hsl(var(--loss))]" : "text-muted-foreground"}>
              {t("spending.kpi.vsAverage", {
                delta: fmt.signedPct(delta),
                average: fmt.eur0(data.monthly_average ?? 0),
              })}
            </span>
          ) : (
            <span className="text-muted-foreground">{t("spending.kpi.noCompleteMonth")}</span>
          )
        }
      />
      <BentoTile
        label={t("spending.kpi.received")}
        value={fmt.eur0(current.income)}
        sub={
          data.monthly_income_average !== null ? (
            <span className="text-muted-foreground">
              {t("spending.kpi.average", { average: fmt.eur0(data.monthly_income_average) })}
            </span>
          ) : undefined
        }
      />
      <BentoTile
        label={t("spending.kpi.left")}
        value={fmt.eur0(left)}
        accent={left < 0 ? "danger" : "neutral"}
        sub={<span className="text-muted-foreground">{t("spending.kpi.leftSub")}</span>}
      />
      <BentoTile
        label={t("spending.kpi.saved")}
        value={savedRate === null ? "—" : fmt.pct0(savedRate)}
        sub={<span className="text-muted-foreground">{t("spending.kpi.savedSub")}</span>}
      />
    </div>
  );
}

/* ── Column charts, on the shared px-true frame ────────────────────────── */

const COLUMN_H = 220;
const COLUMN_PAD = { top: 20, right: 8, bottom: 22, left: 54 }; // room for « 2,5 k€ »
const BAR_MAX = 24; // a column never thicker than this: the slot's leftover is air
const GAP = 2; // the surface gap between touching marks, in px

const IN = "fill-[#2a78d6] dark:fill-[#3987e5]";
const OUT = "fill-[#eb6834] dark:fill-[#d95926]";

/** A column with a 4px rounded top and a square foot on the baseline. */
function column(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, h, w / 2);
  return `M ${x} ${y + h} V ${y + r} Q ${x} ${y} ${x + r} ${y} H ${x + w - r} Q ${x + w} ${y} ${x + w} ${y + r} V ${y + h} Z`;
}

/** The month under the pointer, by slot; null outside the plot. */
function slotAt(x: number, frame: ChartFrame, n: number): number | null {
  if (n === 0 || x < frame.left || x > frame.right) return null;
  return Math.min(n - 1, Math.floor(((x - frame.left) / frame.innerW) * n));
}

function MonthAxis({ frame, months }: { frame: ChartFrame; months: MonthSpending[] }) {
  const slot = frame.innerW / months.length;
  return (
    <XAxis
      frame={frame}
      ticks={months.map((_, i) => i)}
      scale={(i) => frame.left + slot * i + slot / 2}
      format={(i) => monthLabel(months[i].month)}
    />
  );
}

/* ── In and out, month by month ────────────────────────────────────────── */

function InOutColumns({ months }: { months: MonthSpending[] }) {
  const { t } = useT();
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...months.flatMap((m) => [m.total, m.income])) || 1;
  const last = months.length - 1;

  return (
    <figure className="m-0 mt-3">
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2a78d6] dark:bg-[#3987e5]" />
          {t("spending.received")}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#eb6834] dark:bg-[#d95926]" />
          {t("spending.spent")}
        </span>
      </div>
      <Chart
        className="mt-2"
        height={COLUMN_H}
        pad={COLUMN_PAD}
        ariaLabel={t("spending.inOut.aria")}
        onPointer={(p, frame) => setHover(p ? slotAt(p.x, frame, months.length) : null)}
        tooltip={(frame) => {
          if (hover === null) return null;
          const slot = frame.innerW / months.length;
          const m = months[hover];
          const rows: { id: string; label: string; value: number }[] = [
            { id: "income", label: t("spending.received"), value: m.income },
            { id: "spent", label: t("spending.spent"), value: m.total },
            { id: "left", label: t("spending.left"), value: m.income - m.total },
          ];
          return {
            x: frame.left + slot * hover + slot / 2,
            y: frame.top,
            content: (
              <>
                <div className="text-muted-foreground">{monthLabel(m.month, true)}</div>
                {rows.map((r) => (
                  <div key={r.id} className="mt-1 flex justify-between gap-2">
                    <span className="text-muted-foreground">{r.label}</span>
                    <span
                      className={cn(
                        "tabular-nums font-medium",
                        r.id === "left" && r.value < 0 && "text-[hsl(var(--loss))]",
                      )}
                    >
                      {fmt.eur0(r.value)}
                    </span>
                  </div>
                ))}
              </>
            ),
          };
        }}
      >
        {(frame) => {
          const yScale = linearScale([0, max], [frame.bottom, frame.top]);
          const ticks = niceTicks(0, max, frame.compact ? 3 : 4);
          const slot = frame.innerW / months.length;
          const bar = Math.min(BAR_MAX, (slot * 0.7 - GAP) / 2);
          return (
            <>
              <YAxis frame={frame} ticks={ticks} scale={yScale} format={fmt.kEur} grid />
              <MonthAxis frame={frame} months={months} />
              {months.map((m, i) => {
                const centre = frame.left + slot * i + slot / 2;
                const xIn = centre - bar - GAP / 2;
                const xOut = centre + GAP / 2;
                const isCurrent = i === last;
                const lift = hover === i;
                return (
                  <g
                    key={m.month}
                    tabIndex={0}
                    onFocus={() => setHover(i)}
                    onBlur={() => setHover(null)}
                    className="outline-none"
                  >
                    {m.income > 0 && (
                      <path
                        d={column(xIn, yScale(m.income), bar, frame.bottom - yScale(m.income))}
                        className={cn(IN, isCurrent && "opacity-50", lift && "opacity-80")}
                      />
                    )}
                    {m.total > 0 && (
                      <path
                        d={column(xOut, yScale(m.total), bar, frame.bottom - yScale(m.total))}
                        className={cn(OUT, isCurrent && "opacity-50", lift && "opacity-80")}
                      />
                    )}
                    {isCurrent && m.total > 0 && (
                      <text
                        x={xOut + bar / 2}
                        y={yScale(m.total) - 6}
                        textAnchor="middle"
                        className="fill-foreground text-[11px] font-medium"
                      >
                        {fmt.kEur(m.total)}
                      </text>
                    )}
                  </g>
                );
              })}
            </>
          );
        }}
      </Chart>
      <p className="mt-1 text-[10px] text-muted-foreground">{t("spending.currentMonthNote")}</p>
    </figure>
  );
}

/* ── What it went on, month by month ───────────────────────────────────── */

/**
 * Categorical slots 1–5 of the validated palette, in their fixed order (the
 * order is the colour-blindness safety, not a taste). Assigned to the window's
 * biggest categories by rank; the fold and the unlabelled wear neutral greys.
 * Literal class names so Tailwind keeps them.
 */
const SLOT_FILL = [
  "fill-[#2a78d6] dark:fill-[#3987e5]",
  "fill-[#eb6834] dark:fill-[#d95926]",
  "fill-[#1baf7a] dark:fill-[#199e70]",
  "fill-[#eda100] dark:fill-[#c98500]",
  "fill-[#e87ba4] dark:fill-[#d55181]",
];
const SLOT_SWATCH = [
  "bg-[#2a78d6] dark:bg-[#3987e5]",
  "bg-[#eb6834] dark:bg-[#d95926]",
  "bg-[#1baf7a] dark:bg-[#199e70]",
  "bg-[#eda100] dark:bg-[#c98500]",
  "bg-[#e87ba4] dark:bg-[#d55181]",
];
const NEUTRAL_FILL: Record<string, string> = {
  [OTHERS]: "fill-[#898781]",
  [UNLABELLED]: "fill-[#c3c2b7] dark:fill-[#383835]",
};
const NEUTRAL_SWATCH: Record<string, string> = {
  [OTHERS]: "bg-[#898781]",
  [UNLABELLED]: "bg-[#c3c2b7] dark:bg-[#383835]",
};

function seriesFill(key: string, index: number): string {
  return NEUTRAL_FILL[key] ?? SLOT_FILL[index] ?? "fill-[#898781]";
}
function seriesSwatch(key: string, index: number): string {
  return NEUTRAL_SWATCH[key] ?? SLOT_SWATCH[index] ?? "bg-[#898781]";
}
function seriesLabel(key: string): string {
  return key === OTHERS ? t("spending.otherCategories") : categoryLabel(key);
}

function CategoryStack({ months }: { months: MonthSpending[] }) {
  const { t } = useT();
  const [hover, setHover] = useState<number | null>(null);
  const series = useMemo(() => stackSeries(months), [months]);
  const stacks = useMemo(() => months.map((m) => monthStack(m, series)), [months, series]);
  const max = Math.max(...months.map((m) => m.total)) || 1;
  const last = months.length - 1;

  if (series.length === 0) {
    return <p className="mt-2 text-sm text-muted-foreground">{t("spending.nothingToShow")}</p>;
  }

  return (
    <figure className="m-0 mt-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {series.map((key, i) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className={cn("inline-block h-2.5 w-2.5 rounded-sm", seriesSwatch(key, i))} />
            {seriesLabel(key)}
          </span>
        ))}
      </div>
      <Chart
        className="mt-2"
        height={COLUMN_H}
        pad={COLUMN_PAD}
        ariaLabel={t("spending.stack.aria")}
        onPointer={(p, frame) => setHover(p ? slotAt(p.x, frame, months.length) : null)}
        tooltip={(frame) => {
          if (hover === null) return null;
          const slot = frame.innerW / months.length;
          const m = months[hover];
          // Largest first, like a reader scans; every series at this month, zeros left out.
          const rows = series
            .map((key, i) => ({ key, i, value: stacks[hover][key] }))
            .filter((r) => r.value > 0)
            .sort((a, b) => b.value - a.value);
          return {
            x: frame.left + slot * hover + slot / 2,
            y: frame.top,
            content: (
              <>
                <div className="flex justify-between gap-2">
                  <span className="text-muted-foreground">{monthLabel(m.month, true)}</span>
                  <span className="tabular-nums font-medium">{fmt.eur0(m.total)}</span>
                </div>
                {rows.map((r) => (
                  <div key={r.key} className="mt-1 flex items-center gap-2">
                    <span
                      className={cn("inline-block h-0.5 w-3 shrink-0", seriesSwatch(r.key, r.i))}
                    />
                    <span className="min-w-0 flex-1 truncate text-muted-foreground">
                      {seriesLabel(r.key)}
                    </span>
                    <span className="tabular-nums font-medium">{fmt.eur0(r.value)}</span>
                  </div>
                ))}
              </>
            ),
          };
        }}
      >
        {(frame) => {
          const yScale = linearScale([0, max], [frame.bottom, frame.top]);
          const ticks = niceTicks(0, max, frame.compact ? 3 : 4);
          const slot = frame.innerW / months.length;
          const bar = Math.min(BAR_MAX, slot * 0.6);
          const scale = frame.innerH / max;
          return (
            <>
              <YAxis frame={frame} ticks={ticks} scale={yScale} format={fmt.kEur} grid />
              <MonthAxis frame={frame} months={months} />
              {months.map((m, i) => {
                const x = frame.left + slot * i + slot / 2 - bar / 2;
                const isCurrent = i === last;
                const lift = hover === i;
                // Segments grow from the baseline, a 2px surface gap between
                // them; only the topmost one wears the rounded data-end.
                let top = frame.bottom;
                const segments = series
                  .filter((key) => stacks[i][key] > 0)
                  .map((key, j) => {
                    const h = stacks[i][key] * scale;
                    const y = top - (j === 0 ? 0 : GAP) - h;
                    top = y;
                    return { key, y, h, index: series.indexOf(key) };
                  });
                return (
                  <g
                    key={m.month}
                    tabIndex={0}
                    onFocus={() => setHover(i)}
                    onBlur={() => setHover(null)}
                    className="outline-none"
                  >
                    {segments.map((seg, j) => {
                      const fill = cn(
                        seriesFill(seg.key, seg.index),
                        isCurrent && "opacity-50",
                        lift && "opacity-80",
                      );
                      return j === segments.length - 1 ? (
                        <path key={seg.key} d={column(x, seg.y, bar, seg.h)} className={fill} />
                      ) : (
                        <rect
                          key={seg.key}
                          x={x}
                          y={seg.y}
                          width={bar}
                          height={seg.h}
                          className={fill}
                        />
                      );
                    })}
                    {isCurrent && m.total > 0 && (
                      <text
                        x={x + bar / 2}
                        y={top - 6}
                        textAnchor="middle"
                        className="fill-foreground text-[11px] font-medium"
                      >
                        {fmt.kEur(m.total)}
                      </text>
                    )}
                  </g>
                );
              })}
            </>
          );
        }}
      </Chart>
      <p className="mt-1 text-[10px] text-muted-foreground">
        {t("spending.stack.note", { count: Math.min(series.length, SLOT_FILL.length) })}{" "}
        {t("spending.currentMonthNote")}
      </p>
    </figure>
  );
}

/* ── What moved, against the habit ─────────────────────────────────────── */

/**
 * Diverging bars from a centre line: right and in the loss colour when the
 * category cost more than usual, left and in the gain colour when less. The
 * colour means better/worse, hence the status tokens rather than a series hue.
 * Value at the tip of every bar: nothing is gated behind hover.
 */
function CategoryDeltas({ report }: { report: DeltaReport | null }) {
  const { t, tn } = useT();
  if (report === null) {
    return <p className="mt-2 text-sm text-muted-foreground">{t("spending.moved.needTwo")}</p>;
  }
  if (report.rows.length === 0) {
    return (
      <p className="mt-2 text-sm text-muted-foreground">
        {t("spending.moved.nothing", { month: monthLabel(report.month, true) })}
      </p>
    );
  }
  const max = Math.max(...report.rows.map((r) => Math.abs(r.delta))) || 1;
  return (
    <>
      <p className="mt-1 text-xs text-muted-foreground">
        {tn("spending.moved.baseline", report.baseline, {
          month: capitalize(monthLabel(report.month, true)),
        })}
      </p>
      <ul className="mt-3 space-y-2.5">
        {report.rows.map((r) => {
          const more = r.delta > 0;
          const width = (Math.abs(r.delta) / max) * 50;
          return (
            <li
              key={r.category}
              className="grid grid-cols-[minmax(0,7rem)_1fr_auto] items-center gap-x-2 gap-y-1 text-xs"
            >
              <span className="truncate">{categoryLabel(r.category)}</span>
              <span className="relative h-2" aria-hidden>
                <span className="absolute inset-y-0 left-1/2 w-px bg-border" />
                <span
                  className={cn(
                    "absolute inset-y-0",
                    more
                      ? "left-1/2 rounded-r-[4px] bg-[hsl(var(--loss))]"
                      : "right-1/2 rounded-l-[4px] bg-[hsl(var(--gain))]",
                  )}
                  style={{ width: `${width}%` }}
                />
              </span>
              <span className="whitespace-nowrap tabular-nums text-foreground">
                {fmt.signedEur0(r.delta)}
              </span>
              <span className="col-span-3 -mt-1 text-[10px] text-muted-foreground">
                {t("spending.moved.usual", {
                  last: fmt.eur0(r.last),
                  average: fmt.eur0(r.average),
                })}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[10px] text-muted-foreground">{t("spending.moved.legend")}</p>
    </>
  );
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* ── Where it goes, and at whom ────────────────────────────────────────── */

const SHOWN = 7;

function CategoryBars({ categories }: { categories: SpendingResponse["categories"] }) {
  const { t } = useT();
  // Not memoised: a handful of rows, and the labels follow the language.
  const head = categories.slice(0, SHOWN);
  const tail = categories.slice(SHOWN);
  const rows = head.map((c) => ({
    label: categoryLabel(c.category),
    total: c.total,
    hint: fmt.pct0(c.share),
  }));
  const rest = tail.reduce((s, c) => s + c.total, 0);
  if (rest > 0)
    rows.push({
      label: t("spending.others"),
      total: rest,
      hint: fmt.pct0(tail.reduce((s, c) => s + c.share, 0)),
    });
  return <BarList rows={rows} />;
}

function MerchantBars({ merchants }: { merchants: Merchant[] }) {
  const { t, tn } = useT();
  const rows = merchants.slice(0, 8).map((m) => ({
    label: m.name,
    total: m.total,
    hint: tn("spending.times", m.count),
  }));
  if (rows.length === 0) {
    return <p className="mt-2 text-sm text-muted-foreground">{t("spending.nothingToShow")}</p>;
  }
  return <BarList rows={rows} />;
}

/** Horizontal bars, one hue, value at the tip: a ranked list that reads like a table. */
function BarList({ rows }: { rows: { label: string; total: number; hint: string }[] }) {
  const max = rows[0]?.total || 1;
  return (
    <ul className="mt-3 space-y-2">
      {rows.map((r) => (
        <li
          key={r.label}
          className="grid grid-cols-[minmax(0,8rem)_1fr_auto] items-center gap-2 text-xs"
        >
          <span className="truncate capitalize" title={r.label}>
            {r.label}
          </span>
          <span className="relative h-2" aria-hidden>
            <span
              className="absolute inset-y-0 left-0 rounded-r-[4px] bg-[#2a78d6] dark:bg-[#3987e5]"
              style={{ width: `${(r.total / max) * 100}%` }}
            />
          </span>
          <span className="whitespace-nowrap tabular-nums text-muted-foreground">
            <span className="text-foreground">{fmt.eur0(r.total)}</span>
            <span className="ml-1 hidden md:inline">· {r.hint}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ── Table views ───────────────────────────────────────────────────────── */

function MonthTable({ months }: { months: MonthSpending[] }) {
  const { t } = useT();
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-muted-foreground">
            <th className="py-1 pr-3 font-medium">{t("spending.table.month")}</th>
            <th className="py-1 pr-3 text-right font-medium">{t("spending.received")}</th>
            <th className="py-1 pr-3 text-right font-medium">{t("spending.spent")}</th>
            <th className="py-1 pr-3 text-right font-medium">{t("spending.left")}</th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month} className="border-t">
              <td className="py-1 pr-3">{monthLabel(m.month, true)}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{fmt.eur0(m.income)}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{fmt.eur0(m.total)}</td>
              <td
                className={cn(
                  "py-1 pr-3 text-right tabular-nums",
                  m.income - m.total < 0 && "text-[hsl(var(--loss))]",
                )}
              >
                {fmt.eur0(m.income - m.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CategoryTable({ months }: { months: MonthSpending[] }) {
  const { t } = useT();
  const cats = useMemo(() => {
    const totals: Record<string, number> = {};
    for (const m of months)
      for (const [c, v] of Object.entries(m.by_category)) totals[c] = (totals[c] ?? 0) + v;
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .map(([c]) => c);
  }, [months]);
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {t("spending.table.byCategory")}
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1 pr-3 font-medium">{t("spending.table.category")}</th>
              {months.map((m) => (
                <th key={m.month} className="py-1 pr-3 text-right font-medium">
                  {monthLabel(m.month)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cats.map((c) => (
              <tr key={c} className="border-t">
                <td className="py-1 pr-3">{categoryLabel(c)}</td>
                {months.map((m) => (
                  <td key={m.month} className="py-1 pr-3 text-right tabular-nums">
                    {m.by_category[c] ? fmt.eur0(m.by_category[c]) : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ── Labels ─────────────────────────────────────────────────────────────── */

/** This screen's own wording of the backend taxonomy; the fold and « Autres » live in the JSX. */
const CATEGORY_KEYS: Record<string, MessageKey> = {
  alimentation: "spending.category.alimentation",
  restaurant: "spending.category.restaurant",
  transport: "spending.category.transport",
  carburant: "spending.category.carburant",
  loyer: "spending.category.loyer",
  charges_logement: "spending.category.charges_logement",
  telecom_internet: "spending.category.telecom_internet",
  assurance: "spending.category.assurance",
  sante: "spending.category.sante",
  loisirs: "spending.category.loisirs",
  abonnements: "spending.category.abonnements",
  shopping: "spending.category.shopping",
  voyages: "spending.category.voyages",
  education: "spending.category.education",
  impots_taxes: "spending.category.impots_taxes",
  salaire: "spending.category.salaire",
  remboursement: "spending.category.remboursement",
  virement_interne: "spending.category.virement_interne",
  virement_sortant: "spending.category.virement_sortant",
  epargne_investissement: "spending.category.epargne_investissement",
  frais_bancaires: "spending.category.frais_bancaires",
  cadeaux_dons: "spending.category.cadeaux_dons",
  autre: "spending.category.autre",
};

function categoryLabel(key: string): string {
  const k = CATEGORY_KEYS[key];
  return k ? t(k) : key;
}

/** « août » / « août 2026 » — "Aug" / "August 2026". Built as a local date so no timezone shifts the month. */
function monthLabel(month: string, long = false): string {
  const [y, m] = month.split("-").map(Number);
  return formatDate(new Date(y, m - 1, 1).toISOString(), {
    month: long ? "long" : "short",
    ...(long ? { year: "numeric" } : {}),
  });
}
