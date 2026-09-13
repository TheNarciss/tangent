import { useMemo, useState } from "react";

import { useSpending, type Merchant, type MonthSpending, type SpendingResponse } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Dépenses — the current accounts, read the way a budgeting app reads them.
 *
 * One filter row (the period) scopes everything below it. Then, in the order
 * a person asks: the month's four figures (spent, received, what is left, the
 * observed saving rate), money in and out month by month, where it goes by
 * category, and at whom. « Voir le tableau » is the accessibility twin: every
 * number the charts show is readable there without hovering.
 *
 * Plain SVG and divs, no charting library. Two series at most (in / out),
 * hence a legend; one hue for anything that is a single series; text never
 * wears the data colour; the current month is lighter because it is not over.
 */
export function Spending() {
  const [months, setMonths] = useState<3 | 6 | 12>(6);
  const [showTable, setShowTable] = useState(false);
  const { data, isLoading, isFetching } = useSpending(months);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dépenses</h1>
          <p className="text-sm text-muted-foreground">
            Ce qui entre et sort de tes comptes courants. Un virement vers un autre de tes comptes
            connectés, ton épargne ou un remboursement de prêt n'est pas une dépense. Un virement
            vers un compte que Tangent ne connaît pas en est une : l'argent est parti.
          </p>
        </div>
        {/* One filter row above everything it scopes. */}
        <div className="flex items-center gap-1 rounded-md border p-0.5 text-xs">
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
              {n} mois
            </button>
          ))}
        </div>
      </header>

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
          <p className="text-sm text-muted-foreground">
            Aucun mouvement synchronisé sur tes comptes courants pour l'instant. Tout apparaîtra ici
            dès la prochaine synchronisation.
          </p>
        </section>
      ) : (
        <div className={cn("space-y-6", isFetching && "opacity-70 transition-opacity")}>
          <Kpis data={data} />
          <section className="rounded-xl border bg-card p-4 md:p-6">
            <div className="flex items-start justify-between gap-3">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Entrées et sorties, par mois
              </div>
              <button
                type="button"
                onClick={() => setShowTable((v) => !v)}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground hover:underline"
              >
                {showTable ? "Voir les graphiques" : "Voir le tableau"}
              </button>
            </div>
            {showTable ? (
              <MonthTable months={data.months} />
            ) : (
              <InOutColumns months={data.months} />
            )}
          </section>
          {!showTable && (
            <div className="grid gap-6 md:grid-cols-2">
              <section className="rounded-xl border bg-card p-4 md:p-6">
                <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Où ça part
                </div>
                {data.unlabelled_share > 0.2 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {fmt.pct0(data.unlabelled_share)} des dépenses n'ont pas encore de catégorie.
                  </p>
                )}
                <CategoryBars categories={data.categories} />
              </section>
              <section className="rounded-xl border bg-card p-4 md:p-6">
                <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Chez qui
                </div>
                <MerchantBars merchants={data.merchants} />
              </section>
            </div>
          )}
          {showTable && <CategoryTable months={data.months} />}
        </div>
      )}
    </div>
  );
}

/* ── The month's four figures ──────────────────────────────────────────── */

function Kpis({ data }: { data: SpendingResponse }) {
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
        label="Dépensé ce mois-ci"
        value={fmt.eur0(current.total)}
        sub={
          delta !== null ? (
            <span className={delta > 0.1 ? "text-[hsl(var(--loss))]" : "text-muted-foreground"}>
              {fmt.signedPct(delta)} vs {fmt.eur0(data.monthly_average ?? 0)} en moyenne
            </span>
          ) : (
            <span className="text-muted-foreground">pas encore de mois complet</span>
          )
        }
      />
      <BentoTile
        label="Reçu ce mois-ci"
        value={fmt.eur0(current.income)}
        sub={
          data.monthly_income_average !== null ? (
            <span className="text-muted-foreground">
              {fmt.eur0(data.monthly_income_average)} en moyenne
            </span>
          ) : undefined
        }
      />
      <BentoTile
        label="Reste ce mois-ci"
        value={fmt.eur0(left)}
        accent={left < 0 ? "danger" : "neutral"}
        sub={<span className="text-muted-foreground">reçu moins dépensé</span>}
      />
      <BentoTile
        label="Épargné, mois complets"
        value={savedRate === null ? "—" : fmt.pct0(savedRate)}
        sub={<span className="text-muted-foreground">part du reçu non dépensée</span>}
      />
    </div>
  );
}

/* ── In and out, month by month ────────────────────────────────────────── */

const W = 360;
const H = 170;
const PAD_TOP = 22;
const PAD_BOTTOM = 18;
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;
const BAR_MAX = 18;
const GAP = 2; // the surface gap between the two bars of a month

const IN = "fill-[#2a78d6] dark:fill-[#3987e5]";
const OUT = "fill-[#eb6834] dark:fill-[#d95926]";

function InOutColumns({ months }: { months: MonthSpending[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...months.flatMap((m) => [m.total, m.income])) || 1;
  const slot = W / months.length;
  const bar = Math.min(BAR_MAX, (slot * 0.7 - GAP) / 2);
  const yOf = (v: number) => PAD_TOP + PLOT_H - (v / max) * PLOT_H;
  const last = months.length - 1;

  return (
    <figure className="m-0 mt-3">
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2a78d6] dark:bg-[#3987e5]" />
          Reçu
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#eb6834] dark:bg-[#d95926]" />
          Dépensé
        </span>
      </div>
      <div className="relative mt-2">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full"
          role="img"
          aria-label="Reçu et dépensé par mois"
        >
          <line
            x1={0}
            x2={W}
            y1={PAD_TOP + PLOT_H}
            y2={PAD_TOP + PLOT_H}
            className="stroke-border"
            strokeWidth={1}
          />
          {months.map((m, i) => {
            const xIn = slot * i + slot / 2 - bar - GAP / 2;
            const xOut = slot * i + slot / 2 + GAP / 2;
            const isCurrent = i === last;
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
                <rect x={slot * i} y={0} width={slot} height={H} fill="transparent" />
                {m.income > 0 && (
                  <path
                    d={column(xIn, yOf(m.income), bar, PAD_TOP + PLOT_H - yOf(m.income))}
                    className={cn(IN, isCurrent && "opacity-50", hover === i && "opacity-80")}
                  />
                )}
                {m.total > 0 && (
                  <path
                    d={column(xOut, yOf(m.total), bar, PAD_TOP + PLOT_H - yOf(m.total))}
                    className={cn(OUT, isCurrent && "opacity-50", hover === i && "opacity-80")}
                  />
                )}
                {isCurrent && m.total > 0 && (
                  <text
                    x={xOut + bar / 2}
                    y={yOf(m.total) - 6}
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
      <p className="mt-1 text-[10px] text-muted-foreground">
        Le mois en cours est plus clair : il n'est pas fini.
      </p>
    </figure>
  );
}

/** A column with a 4px rounded top and a square foot on the baseline. */
function column(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, h, w / 2);
  return `M ${x} ${y + h} V ${y + r} Q ${x} ${y} ${x + r} ${y} H ${x + w - r} Q ${x + w} ${y} ${x + w} ${y + r} V ${y + h} Z`;
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
  const left = ((index + 0.5) / count) * 100;
  const rows: [string, number][] = [
    ["Reçu", month.income],
    ["Dépensé", month.total],
    ["Reste", month.income - month.total],
  ];
  return (
    <div
      className="pointer-events-none absolute top-0 z-10 w-40 -translate-x-1/2 rounded-md border bg-popover p-2 text-xs shadow-md"
      style={{ left: `${Math.min(Math.max(left, 20), 80)}%` }}
    >
      <div className="text-muted-foreground">{monthLabel(month.month, true)}</div>
      {rows.map(([label, v]) => (
        <div key={label} className="mt-1 flex justify-between gap-2">
          <span className="text-muted-foreground">{label}</span>
          <span
            className={cn(
              "tabular-nums font-medium",
              label === "Reste" && v < 0 && "text-[hsl(var(--loss))]",
            )}
          >
            {fmt.eur0(v)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Where it goes, and at whom ────────────────────────────────────────── */

const SHOWN = 7;

function CategoryBars({ categories }: { categories: SpendingResponse["categories"] }) {
  const rows = useMemo(() => {
    const head = categories.slice(0, SHOWN);
    const tail = categories.slice(SHOWN);
    const out = head.map((c) => ({
      label: categoryLabel(c.category),
      total: c.total,
      hint: fmt.pct0(c.share),
    }));
    const rest = tail.reduce((s, c) => s + c.total, 0);
    if (rest > 0)
      out.push({
        label: "Autres",
        total: rest,
        hint: fmt.pct0(tail.reduce((s, c) => s + c.share, 0)),
      });
    return out;
  }, [categories]);
  return <BarList rows={rows} />;
}

function MerchantBars({ merchants }: { merchants: Merchant[] }) {
  const rows = merchants.slice(0, 8).map((m) => ({
    label: m.name,
    total: m.total,
    hint: `${m.count} fois`,
  }));
  if (rows.length === 0) {
    return <p className="mt-2 text-sm text-muted-foreground">Rien à montrer sur cette période.</p>;
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
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-muted-foreground">
            <th className="py-1 pr-3 font-medium">Mois</th>
            <th className="py-1 pr-3 text-right font-medium">Reçu</th>
            <th className="py-1 pr-3 text-right font-medium">Dépensé</th>
            <th className="py-1 pr-3 text-right font-medium">Reste</th>
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
        Par catégorie
      </div>
      <div className="mt-3 overflow-x-auto">
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
          </tbody>
        </table>
      </div>
    </section>
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
  virement_sortant: "Virements sortants",
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
