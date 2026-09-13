import { useState } from "react";

import { ApiError, usePicks, type PicksResponse } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * La liste de l'année — cross-sectional momentum on European large caps.
 *
 * The screen states the rule before the names, because the names are the
 * output of the rule and nothing else. In order: what the rule is and what
 * it promises (a documented expectation, never a gain); the guard, when it
 * is on; the list — with what entered and what left since the last review;
 * the track record, as a pair of figures and a year-by-year chart against the
 * equal-weight universe, 2009 included. The sleeve cap is written twice: in
 * the header and next to the list.
 */
export function Picks() {
  const { data, isLoading, error } = usePicks();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-24 animate-pulse rounded-xl bg-muted/30" />
        <div className="h-64 animate-pulse rounded-xl bg-muted/30" />
      </div>
    );
  }
  if (error || !data) {
    const detail = error instanceof ApiError ? error.message : null;
    return (
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <p className="text-sm">
          La liste ne peut pas être calculée pour l'instant : une source ne répond pas.
        </p>
        {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
        <p className="mt-2 text-xs text-muted-foreground">
          Rien n'est affiché de périmé à la place : la liste est recalculée à chaque fois depuis les
          pages des indices et les cours du jour.
        </p>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <Rule data={data} />
      {data.guard_on ? <GuardOn data={data} /> : <TheList data={data} />}
      <Track data={data} />
    </div>
  );
}

/* ── The rule, stated first ────────────────────────────────────────────── */

const REVIEW_LABEL = {
  monthly: "chaque mois",
  quarterly: "chaque trimestre",
  annual: "chaque année",
};

function Rule({ data }: { data: PicksResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <p className="text-sm">
        Les <strong>{data.top} titres</strong> qui ont le plus monté sur les douze derniers mois, le
        dernier mois ignoré, parmi {data.universe_size} grandes valeurs européennes cotées en euros.
        Refait <strong>{REVIEW_LABEL[data.review]}</strong>. Ce n'est pas un pronostic : c'est une
        règle qu'on peut refaire à la main, avec un siècle de preuves derrière elle — et des années
        à −45 % dedans.
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        À traiter comme un{" "}
        <strong className="text-foreground">satellite de 10 à 20 % de tes actions</strong>, jamais
        comme le cœur. Le cœur reste l'ETF monde.
      </p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-2 text-xs text-muted-foreground hover:text-foreground hover:underline"
      >
        {open ? "Masquer la règle complète" : "Voir la règle complète"}
      </button>
      {open && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          <li>
            Univers : les constituants actuels de {data.indices.map(indexLabel).join(", ")}, lus sur
            les pages des indices à chaque calcul. Tous éligibles au PEA.
          </li>
          <li>
            Score : rendement de douze mois hors le dernier, divisé par la volatilité — les fusées
            qui explosent sont écartées.
          </li>
          <li>Poids égaux. Entre deux revues, les poids dérivent avec les cours.</li>
          <li>
            Frein : quand l'univers a perdu sur douze mois, la liste est vide et la poche reste en
            cash jusqu'à la revue suivante. C'est la configuration des krachs de momentum.
          </li>
          <li>
            L'historique ci-dessous est calculé sur les constituants d'aujourd'hui : les sortants
            d'hier manquent, il est donc flatté.
          </li>
        </ul>
      )}
    </section>
  );
}

/* ── The list ──────────────────────────────────────────────────────────── */

function TheList({ data }: { data: PicksResponse }) {
  const bought = new Set(data.bought);
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          La liste au {dateLabel(data.as_of)}
        </div>
        <div className="text-xs text-muted-foreground">
          prochaine revue le {dateLabel(data.next_review)}
        </div>
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3 md:grid-cols-5">
        {data.held.map((t, i) => (
          <li key={t} className="flex items-center gap-2 text-sm tabular-nums">
            <span className="w-5 text-right text-xs text-muted-foreground">{i + 1}</span>
            <span className="font-medium">{t}</span>
            {bought.has(t) && (
              <span className="rounded bg-[#2a78d6]/15 px-1 text-[10px] font-medium text-[#2a78d6] dark:text-[#3987e5]">
                nouveau
              </span>
            )}
          </li>
        ))}
      </ul>

      {(data.bought.length > 0 || data.sold.length > 0) && (
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded-md border p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Entrés à cette revue
            </div>
            <p className="mt-1">{data.bought.length ? data.bought.join(", ") : "—"}</p>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Sortis — à vendre
            </div>
            <p className="mt-1">{data.sold.length ? data.sold.join(", ") : "—"}</p>
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-muted-foreground">
        À poids égal : chaque titre pèse 1/{data.held.length} de la poche.
      </p>
    </section>
  );
}

function GuardOn({ data }: { data: PicksResponse }) {
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Frein actif au {dateLabel(data.as_of)}
      </div>
      <p className="mt-2 text-sm">
        L'univers a perdu de la valeur sur les douze derniers mois. C'est dans cette configuration
        que le momentum se retourne le plus violemment au rebond : la liste est{" "}
        <strong>vide</strong> et la poche reste en cash jusqu'à la prochaine revue, le{" "}
        {dateLabel(data.next_review)}.
      </p>
      {data.sold.length > 0 && (
        <p className="mt-2 text-sm text-muted-foreground">À vendre : {data.sold.join(", ")}.</p>
      )}
    </section>
  );
}

/* ── The track record ──────────────────────────────────────────────────── */

const W = 360;
const H = 170;
const PAD_TOP = 18;
const PAD_BOTTOM = 18;
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;
const GAP = 2;
const STRATEGY = "fill-[#2a78d6] dark:fill-[#3987e5]";
const UNIVERSE = "fill-[#eb6834] dark:fill-[#d95926]";

function Track({ data }: { data: PicksResponse }) {
  const t = data.track_record;
  const [hover, setHover] = useState<number | null>(null);
  const rows = t.yearly;
  const max = Math.max(...rows.flatMap((r) => [Math.abs(r.strategy), Math.abs(r.universe)]), 0.01);
  const slot = W / Math.max(rows.length, 1);
  const bar = Math.min(10, (slot * 0.7 - GAP) / 2);
  const zero = PAD_TOP + PLOT_H / 2;
  const yOf = (v: number) => zero - (v / max) * (PLOT_H / 2);

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Ce que la règle a fait depuis {t.since.slice(0, 4)}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <BentoTile
          label="Par an, la règle"
          value={fmt.signedPct(t.cagr)}
          sub={
            <span className="text-muted-foreground">univers {fmt.signedPct(t.universe_cagr)}</span>
          }
        />
        <BentoTile
          label="Pire chute"
          value={fmt.pct0(t.max_drawdown)}
          sub={
            <span className="text-muted-foreground">
              univers {fmt.pct0(t.universe_max_drawdown)}
            </span>
          }
        />
        <BentoTile
          label="Titres remplacés"
          value={fmt.pct0(t.turnover)}
          sub={<span className="text-muted-foreground">par revue</span>}
        />
        <BentoTile
          label="Frein actif"
          value={`${t.guarded_reviews} / ${t.reviews}`}
          sub={<span className="text-muted-foreground">revues</span>}
        />
      </div>

      <figure className="m-0 mt-5">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2a78d6] dark:bg-[#3987e5]" />
            La règle
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#eb6834] dark:bg-[#d95926]" />
            Univers à poids égal
          </span>
        </div>
        <div className="relative mt-2">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label="Rendement par année"
          >
            <line x1={0} x2={W} y1={zero} y2={zero} className="stroke-border" strokeWidth={1} />
            {rows.map((r, i) => {
              const xS = slot * i + slot / 2 - bar - GAP / 2;
              const xU = slot * i + slot / 2 + GAP / 2;
              return (
                <g
                  key={r.year}
                  tabIndex={0}
                  onPointerEnter={() => setHover(i)}
                  onPointerLeave={() => setHover(null)}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                  className="outline-none"
                >
                  <rect x={slot * i} y={0} width={slot} height={H} fill="transparent" />
                  <rect
                    x={xS}
                    y={Math.min(zero, yOf(r.strategy))}
                    width={bar}
                    height={Math.abs(zero - yOf(r.strategy))}
                    className={cn(STRATEGY, hover === i && "opacity-80")}
                  />
                  <rect
                    x={xU}
                    y={Math.min(zero, yOf(r.universe))}
                    width={bar}
                    height={Math.abs(zero - yOf(r.universe))}
                    className={cn(UNIVERSE, hover === i && "opacity-80")}
                  />
                  {(i % Math.ceil(rows.length / 8) === 0 || i === rows.length - 1) && (
                    <text
                      x={slot * i + slot / 2}
                      y={H - 4}
                      textAnchor="middle"
                      className="fill-muted-foreground text-[9px]"
                    >
                      {r.year}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
          {hover !== null && (
            <div
              className="pointer-events-none absolute top-0 z-10 w-36 -translate-x-1/2 rounded-md border bg-popover p-2 text-xs shadow-md"
              style={{
                left: `${Math.min(Math.max(((hover + 0.5) / rows.length) * 100, 18), 82)}%`,
              }}
            >
              <div className="text-muted-foreground">{rows[hover].year}</div>
              <div className="mt-1 flex justify-between gap-2">
                <span className="text-muted-foreground">La règle</span>
                <span className="tabular-nums font-medium">
                  {fmt.signedPct(rows[hover].strategy)}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">Univers</span>
                <span className="tabular-nums font-medium">
                  {fmt.signedPct(rows[hover].universe)}
                </span>
              </div>
            </div>
          )}
        </div>
        <figcaption className="mt-1 text-[10px] text-muted-foreground">
          Rendement de chaque année civile, coûts d'aller-retour déduits pour la règle. Calculé sur
          les constituants d'aujourd'hui : flatté.
        </figcaption>
      </figure>

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
          Voir le tableau
        </summary>
        <table className="mt-2 w-full">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1 pr-3 font-medium">Année</th>
              <th className="py-1 pr-3 text-right font-medium">La règle</th>
              <th className="py-1 pr-3 text-right font-medium">Univers</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.year} className="border-t">
                <td className="py-1 pr-3">{r.year}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{fmt.signedPct(r.strategy)}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{fmt.signedPct(r.universe)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

/* ── Labels ─────────────────────────────────────────────────────────────── */

const INDEX_LABELS: Record<string, string> = {
  cac_40: "CAC 40",
  dax: "DAX",
  aex: "AEX",
  euro_stoxx_50: "Euro Stoxx 50",
  ibex_35: "IBEX 35",
  ftse_mib: "FTSE MIB",
};

function indexLabel(key: string): string {
  return INDEX_LABELS[key] ?? key;
}

function dateLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
