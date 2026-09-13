import { useMemo, useState } from "react";

import { useSpending, type MonthSpending } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Dépenses — what leaves the current accounts, month by month and by category.
 *
 * Three reads, in the order a person asks them: how much this month against
 * the usual (a stat tile), how it moved (six monthly columns, one series, the
 * current month lighter because it is not over), and where it goes (the
 * largest categories as horizontal bars, the tail folded into « Autres »).
 *
 * Charts are plain SVG and divs — no library. One hue for one series; text
 * never wears the data colour; every value is also readable in the table
 * behind « Voir le tableau », so the chart never gates a number.
 */
export function SpendingSection() {
  const { data, isLoading } = useSpending(6);
  const [showTable, setShowTable] = useState(false);

  if (isLoading) {
    return (
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <Heading />
        <div className="mt-3 h-40 animate-pulse rounded bg-muted/30" />
      </section>
    );
  }
  if (!data || data.months.every((m) => m.total === 0)) {
    return (
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <Heading />
        <p className="mt-2 text-sm text-muted-foreground">
          Aucune dépense synchronisée pour l'instant. Elles apparaîtront ici dès que tes comptes
          courants auront des mouvements.
        </p>
      </section>
    );
  }

  const current = data.months[data.months.length - 1];
  const average = data.monthly_average;
  const delta = average && average > 0 ? current.total / average - 1 : null;

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="flex items-start justify-between gap-3">
        <Heading />
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          className="shrink-0 text-xs text-muted-foreground hover:text-foreground hover:underline"
        >
          {showTable ? "Voir les graphiques" : "Voir le tableau"}
        </button>
      </div>

      {/* The number the section leads with. */}
      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-3xl font-semibold tracking-tight md:text-4xl">
          {fmt.eur0(current.total)}
        </span>
        <span className="text-sm text-muted-foreground">
          ce mois-ci
          {average !== null && delta !== null && (
            <>
              {" · "}
              <span
                className={cn(
                  delta > 0.1 ? "text-[hsl(var(--loss))]" : "text-foreground",
                  delta < -0.1 && "text-[hsl(var(--gain))]",
                )}
              >
                {fmt.signedPct(delta)}
              </span>{" "}
              vs {fmt.eur0(average)} en moyenne
            </>
          )}
        </span>
      </div>
      {data.unlabelled_share > 0.2 && (
        <p className="mt-1 text-xs text-muted-foreground">
          {fmt.pct0(data.unlabelled_share)} des dépenses n'ont pas encore de catégorie : la
          répartition se précisera au fil des synchronisations.
        </p>
      )}

      {showTable ? (
        <SpendingTable months={data.months} />
      ) : (
        <div className="mt-5 grid gap-6 md:grid-cols-5 md:gap-8">
          <div className="md:col-span-3">
            <MonthColumns months={data.months} average={average} />
          </div>
          <div className="md:col-span-2">
            <CategoryBars categories={data.categories} />
          </div>
        </div>
      )}
    </section>
  );
}

function Heading() {
  return (
    <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
      Dépenses
    </div>
  );
}

/* ── Monthly columns ───────────────────────────────────────────────────── */

const W = 320;
const H = 150;
const PAD_TOP = 22; // room for the direct label on the tallest column
const PAD_BOTTOM = 18; // the x-axis band, inside the height
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;
const BAR_MAX = 24; // thin marks: never fill the slot

function MonthColumns({ months, average }: { months: MonthSpending[]; average: number | null }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...months.map((m) => m.total), average ?? 0) || 1;
  const slot = W / months.length;
  const bar = Math.min(BAR_MAX, slot * 0.6);
  const yOf = (v: number) => PAD_TOP + PLOT_H - (v / max) * PLOT_H;
  const highest = months.reduce((best, m, i) => (m.total > months[best].total ? i : best), 0);
  const last = months.length - 1;

  return (
    <figure className="m-0">
      <figcaption className="text-xs text-muted-foreground">Par mois</figcaption>
      <div className="relative mt-2">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full"
          role="img"
          aria-label="Dépenses par mois"
        >
          {/* baseline: a solid hairline, one step off the surface */}
          <line
            x1={0}
            x2={W}
            y1={PAD_TOP + PLOT_H}
            y2={PAD_TOP + PLOT_H}
            className="stroke-border"
            strokeWidth={1}
          />
          {average !== null && (
            <line
              x1={0}
              x2={W}
              y1={yOf(average)}
              y2={yOf(average)}
              className="stroke-muted-foreground/50"
              strokeWidth={1}
            />
          )}
          {months.map((m, i) => {
            const x = slot * i + (slot - bar) / 2;
            const y = yOf(m.total);
            const h = PAD_TOP + PLOT_H - y;
            const isCurrent = i === last;
            const labelled = i === highest || isCurrent;
            return (
              <g
                key={m.month}
                tabIndex={0}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className="outline-none"
              >
                {/* the hit target is the whole slot, not the painted bar */}
                <rect x={slot * i} y={0} width={slot} height={H} fill="transparent" />
                {h > 0 && (
                  <path
                    d={roundedTop(x, y, bar, h, 4)}
                    className={cn(
                      "fill-[#2a78d6] dark:fill-[#3987e5]",
                      isCurrent && "opacity-50",
                      hover === i && "opacity-80",
                    )}
                  />
                )}
                {labelled && m.total > 0 && (
                  <text
                    x={x + bar / 2}
                    y={y - 6}
                    textAnchor="middle"
                    className="fill-foreground text-[10px] font-medium"
                  >
                    {fmt.kEur(m.total)}
                  </text>
                )}
                <text
                  x={slot * i + slot / 2}
                  y={H - 4}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[10px]"
                >
                  {monthLabel(m.month)}
                </text>
              </g>
            );
          })}
        </svg>
        {hover !== null && (
          <MonthTooltip month={months[hover]} index={hover} count={months.length} />
        )}
      </div>
      {average !== null && (
        <p className="mt-1 text-[10px] text-muted-foreground">
          Trait gris : moyenne des mois complets. Le mois en cours est plus clair, il n'est pas
          fini.
        </p>
      )}
    </figure>
  );
}

/** A column with a 4px rounded top and a square foot on the baseline. */
function roundedTop(x: number, y: number, w: number, h: number, r: number): string {
  const rr = Math.min(r, h, w / 2);
  return [
    `M ${x} ${y + h}`,
    `V ${y + rr}`,
    `Q ${x} ${y} ${x + rr} ${y}`,
    `H ${x + w - rr}`,
    `Q ${x + w} ${y} ${x + w} ${y + rr}`,
    `V ${y + h}`,
    "Z",
  ].join(" ");
}

function MonthTooltip({
  month,
  index,
  count,
}: {
  month: MonthSpending;
  index: number;
  count: number;
}) {
  const top = Object.entries(month.by_category)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const left = ((index + 0.5) / count) * 100;
  return (
    <div
      className="pointer-events-none absolute top-0 z-10 w-44 -translate-x-1/2 rounded-md border bg-popover p-2 text-xs shadow-md"
      style={{ left: `${Math.min(Math.max(left, 22), 78)}%` }}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-semibold">{fmt.eur0(month.total)}</span>
        <span className="text-muted-foreground">{monthLabel(month.month, true)}</span>
      </div>
      {top.map(([cat, v]) => (
        <div key={cat} className="mt-1 flex justify-between gap-2 text-muted-foreground">
          <span className="truncate">{categoryLabel(cat)}</span>
          <span className="shrink-0 tabular-nums text-foreground">{fmt.eur0(v)}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Category bars ─────────────────────────────────────────────────────── */

const SHOWN = 7; // past this, the tail folds into « Autres »

function CategoryBars({
  categories,
}: {
  categories: { category: string; total: number; share: number }[];
}) {
  const rows = useMemo(() => {
    const head = categories.slice(0, SHOWN);
    const tail = categories.slice(SHOWN);
    const rest = tail.reduce((s, c) => s + c.total, 0);
    const out = head.map((c) => ({
      label: categoryLabel(c.category),
      total: c.total,
      share: c.share,
    }));
    if (rest > 0) {
      out.push({ label: "Autres", total: rest, share: tail.reduce((s, c) => s + c.share, 0) });
    }
    return out;
  }, [categories]);
  const max = rows[0]?.total || 1;

  return (
    <figure className="m-0">
      <figcaption className="text-xs text-muted-foreground">Où ça part, sur six mois</figcaption>
      <ul className="mt-2 space-y-2">
        {rows.map((r) => (
          <li
            key={r.label}
            className="grid grid-cols-[minmax(0,7rem)_1fr_auto] items-center gap-2 text-xs"
          >
            <span className="truncate">{r.label}</span>
            <span className="relative h-2 overflow-visible" aria-hidden>
              <span
                className="absolute inset-y-0 left-0 rounded-r-[4px] bg-[#2a78d6] dark:bg-[#3987e5]"
                style={{ width: `${(r.total / max) * 100}%` }}
              />
            </span>
            <span className="tabular-nums text-muted-foreground">
              {fmt.eur0(r.total)}
              <span className="ml-1 hidden md:inline">· {fmt.pct0(r.share)}</span>
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/* ── Table view — the accessibility twin ──────────────────────────────── */

function SpendingTable({ months }: { months: MonthSpending[] }) {
  const cats = useMemo(() => {
    const totals: Record<string, number> = {};
    for (const m of months)
      for (const [c, v] of Object.entries(m.by_category)) totals[c] = (totals[c] ?? 0) + v;
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .map(([c]) => c);
  }, [months]);

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-muted-foreground">
            <th className="py-1 pr-3 font-medium">Catégorie</th>
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
          <tr className="border-t font-semibold">
            <td className="py-1 pr-3">Total</td>
            {months.map((m) => (
              <td key={m.month} className="py-1 pr-3 text-right tabular-nums">
                {fmt.eur0(m.total)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/* ── Labels ─────────────────────────────────────────────────────────────── */

const CATEGORY_LABELS: Record<string, string> = {
  alimentation: "Alimentation",
  restaurant: "Restaurants",
  transport: "Transport",
  carburant: "Carburant",
  loyer: "Loyer",
  charges_logement: "Charges du logement",
  telecom_internet: "Télécom & internet",
  assurance: "Assurances",
  sante: "Santé",
  loisirs: "Loisirs",
  abonnements: "Abonnements",
  shopping: "Shopping",
  voyages: "Voyages",
  education: "Éducation",
  impots_taxes: "Impôts & taxes",
  salaire: "Salaire",
  remboursement: "Remboursements",
  virement_interne: "Virements internes",
  epargne_investissement: "Épargne & investissement",
  frais_bancaires: "Frais bancaires",
  cadeaux_dons: "Cadeaux & dons",
  autre: "Sans catégorie",
};

function categoryLabel(key: string): string {
  return CATEGORY_LABELS[key] ?? key;
}

function monthLabel(month: string, long = false): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("fr-FR", {
    month: long ? "long" : "short",
    ...(long ? { year: "numeric" } : {}),
  });
}
