import { useState } from "react";

import { ApiError, usePicks, type PicksResponse } from "@/api";
import { BentoTile } from "@/components/ui/bento-tile";
import { t, useT, type MessageKey } from "@/i18n";
import { formatDate } from "@/lib/accounts";
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
  const { t } = useT();
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
        <p className="text-sm">{t("market.picks.error")}</p>
        {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
        <p className="mt-2 text-xs text-muted-foreground">{t("market.picks.errorNote")}</p>
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

const REVIEW_KEYS: Record<PicksResponse["review"], MessageKey> = {
  monthly: "market.picks.review.monthly",
  quarterly: "market.picks.review.quarterly",
  annual: "market.picks.review.annual",
};

function Rule({ data }: { data: PicksResponse }) {
  const { t, tn } = useT();
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <p className="text-sm">
        {t("market.picks.rule.before")}
        <strong>{tn("market.picks.rule.titles", data.top)}</strong>
        {t("market.picks.rule.middle", { universe: data.universe_size })}
        <strong>{t(REVIEW_KEYS[data.review])}</strong>
        {t("market.picks.rule.after")}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        {t("market.picks.rule.satelliteBefore")}
        <strong className="text-foreground">{t("market.picks.rule.satellite")}</strong>
        {t("market.picks.rule.satelliteAfter")}
      </p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-2 text-xs text-muted-foreground hover:text-foreground hover:underline"
      >
        {open ? t("market.picks.rule.hide") : t("market.picks.rule.show")}
      </button>
      {open && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          <li>
            {t("market.picks.rule.universe", {
              indices: data.indices.map(indexLabel).join(", "),
            })}
          </li>
          <li>{t("market.picks.rule.score")}</li>
          <li>{t("market.picks.rule.weights")}</li>
          <li>{t("market.picks.rule.brake")}</li>
          <li>{t("market.picks.rule.history")}</li>
        </ul>
      )}
    </section>
  );
}

/* ── The list ──────────────────────────────────────────────────────────── */

function TheList({ data }: { data: PicksResponse }) {
  const { t } = useT();
  const bought = new Set(data.bought);
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {t("market.picks.list.title", { date: dateLabel(data.as_of) })}
        </div>
        <div className="text-xs text-muted-foreground">
          {t("market.picks.list.nextReview", { date: dateLabel(data.next_review) })}
        </div>
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3 md:grid-cols-5">
        {data.held.map((ticker, i) => (
          <li key={ticker} className="flex items-center gap-2 text-sm tabular-nums">
            <span className="w-5 text-right text-xs text-muted-foreground">{i + 1}</span>
            <span className="font-medium">{ticker}</span>
            {bought.has(ticker) && (
              <span className="rounded bg-[#2a78d6]/15 px-1 text-[10px] font-medium text-[#2a78d6] dark:text-[#3987e5]">
                {t("market.picks.list.new")}
              </span>
            )}
          </li>
        ))}
      </ul>

      {(data.bought.length > 0 || data.sold.length > 0) && (
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div className="rounded-md border p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {t("market.picks.list.entered")}
            </div>
            <p className="mt-1">{data.bought.length ? data.bought.join(", ") : "—"}</p>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {t("market.picks.list.left")}
            </div>
            <p className="mt-1">{data.sold.length ? data.sold.join(", ") : "—"}</p>
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-muted-foreground">
        {t("market.picks.list.equalWeight", { count: data.held.length })}
      </p>
    </section>
  );
}

function GuardOn({ data }: { data: PicksResponse }) {
  const { t } = useT();
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {t("market.picks.guard.title", { date: dateLabel(data.as_of) })}
      </div>
      <p className="mt-2 text-sm">
        {t("market.picks.guard.before")}
        <strong>{t("market.picks.guard.empty")}</strong>
        {t("market.picks.guard.after", { date: dateLabel(data.next_review) })}
      </p>
      {data.sold.length > 0 && (
        <p className="mt-2 text-sm text-muted-foreground">
          {t("market.picks.guard.toSell", { list: data.sold.join(", ") })}
        </p>
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
  const { t } = useT();
  const track = data.track_record;
  const [hover, setHover] = useState<number | null>(null);
  const rows = track.yearly;
  const max = Math.max(...rows.flatMap((r) => [Math.abs(r.strategy), Math.abs(r.universe)]), 0.01);
  const slot = W / Math.max(rows.length, 1);
  const bar = Math.min(10, (slot * 0.7 - GAP) / 2);
  const zero = PAD_TOP + PLOT_H / 2;
  const yOf = (v: number) => zero - (v / max) * (PLOT_H / 2);

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {t("market.picks.track.title", { year: track.since.slice(0, 4) })}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <BentoTile
          label={t("market.picks.track.perYear")}
          value={fmt.signedPct(track.cagr)}
          sub={
            <span className="text-muted-foreground">
              {t("market.picks.track.universeValue", { value: fmt.signedPct(track.universe_cagr) })}
            </span>
          }
        />
        <BentoTile
          label={t("market.picks.track.worstFall")}
          value={fmt.pct0(track.max_drawdown)}
          sub={
            <span className="text-muted-foreground">
              {t("market.picks.track.universeValue", {
                value: fmt.pct0(track.universe_max_drawdown),
              })}
            </span>
          }
        />
        <BentoTile
          label={t("market.picks.track.replaced")}
          value={fmt.pct0(track.turnover)}
          sub={<span className="text-muted-foreground">{t("market.picks.track.perReview")}</span>}
        />
        <BentoTile
          label={t("market.picks.track.guardOn")}
          value={`${track.guarded_reviews} / ${track.reviews}`}
          sub={<span className="text-muted-foreground">{t("market.picks.track.reviews")}</span>}
        />
      </div>

      <figure className="m-0 mt-5">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2a78d6] dark:bg-[#3987e5]" />
            {t("market.picks.track.rule")}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#eb6834] dark:bg-[#d95926]" />
            {t("market.picks.track.universeEqual")}
          </span>
        </div>
        <div className="relative mt-2">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label={t("market.picks.track.aria")}
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
                <span className="text-muted-foreground">{t("market.picks.track.rule")}</span>
                <span className="tabular-nums font-medium">
                  {fmt.signedPct(rows[hover].strategy)}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">{t("market.picks.track.universe")}</span>
                <span className="tabular-nums font-medium">
                  {fmt.signedPct(rows[hover].universe)}
                </span>
              </div>
            </div>
          )}
        </div>
        <figcaption className="mt-1 text-[10px] text-muted-foreground">
          {t("market.picks.track.caption")}
        </figcaption>
      </figure>

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
          {t("market.picks.track.showTable")}
        </summary>
        <table className="mt-2 w-full">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1 pr-3 font-medium">{t("market.picks.track.year")}</th>
              <th className="py-1 pr-3 text-right font-medium">{t("market.picks.track.rule")}</th>
              <th className="py-1 pr-3 text-right font-medium">
                {t("market.picks.track.universe")}
              </th>
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

const INDEX_KEYS: Record<string, MessageKey> = {
  stoxx_europe_600: "market.picks.index.stoxx_europe_600",
  euro_stoxx_50: "market.picks.index.euro_stoxx_50",
  dax: "market.picks.index.dax",
};

function indexLabel(key: string): string {
  const messageKey = INDEX_KEYS[key];
  return messageKey ? t(messageKey) : key;
}

/** « 3 mars 2026 » from a `YYYY-MM-DD` day, read as a local date so the day never shifts. */
function dateLabel(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return formatDate(new Date(y, m - 1, d).toISOString(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
