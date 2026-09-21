import { useMemo, useRef, useState } from "react";

import { QUOTE_SCALES, useQuoteHistory, type QuoteHistory, type QuoteScale } from "@/api";
import { useT, type MessageKey } from "@/i18n";
import { formatDate } from "@/lib/accounts";
import { areaPath, linePath, linearScale, niceTicks, pickIndices } from "@/lib/chart";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  BottomSheet,
  BottomSheetBody,
  BottomSheetContent,
  BottomSheetDescription,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { Chart, Crosshair, XAxis, YAxis, indexAt, type ChartFrame } from "@/components/ui/chart";

/**
 * One line's own price, at the scale the user picks.
 *
 * Seven buttons from one day to everything Yahoo has. On a phone, pinching
 * the chart walks the same scales: fingers apart zooms in on a shorter
 * window, together zooms out. Dragging a finger reads the price under it.
 * The curve of the previous scale stays until the next one has loaded, so
 * a change of scale never blanks the sheet.
 */

/** What a row hands over to open its price. */
export interface QuoteRef {
  symbol: string;
  isin?: string | null;
  /** The name the user knows the line by — the bank's label, or the search result. */
  label?: string | null;
}

const SCALE_KEYS: Record<QuoteScale, MessageKey> = {
  "1d": "market.quotes.scale.1d",
  "1w": "market.quotes.scale.1w",
  "1m": "market.quotes.scale.1m",
  "6m": "market.quotes.scale.6m",
  "1y": "market.quotes.scale.1y",
  "5y": "market.quotes.scale.5y",
  max: "market.quotes.scale.max",
};

/** Fingers this much further apart (or closer) than when they landed = one step. */
const PINCH_IN = 1.25;
const PINCH_OUT = 0.8;

export function QuotePanel({
  quote,
  initialScale = "1y",
}: {
  quote: QuoteRef;
  initialScale?: QuoteScale;
}) {
  const { t } = useT();
  const [scale, setScale] = useState<QuoteScale>(initialScale);
  const history = useQuoteHistory(quote.symbol, scale, quote.isin);
  const pinch = useRef<number | null>(null);

  const step = (direction: -1 | 1) => {
    const i = QUOTE_SCALES.indexOf(scale) + direction;
    if (i >= 0 && i < QUOTE_SCALES.length) setScale(QUOTE_SCALES[i]);
  };
  const distance = (touches: React.TouchList) =>
    Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY);

  return (
    <div className="space-y-3">
      {history.data && <Headline data={history.data} scale={scale} label={quote.label} />}

      <div
        role="group"
        aria-label={t("market.quotes.scale.aria")}
        className="flex flex-wrap items-center gap-1 rounded-md border p-0.5 text-xs"
      >
        {QUOTE_SCALES.map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={scale === s}
            onClick={() => setScale(s)}
            className={cn(
              "min-w-9 rounded px-2.5 py-1",
              scale === s ? "bg-primary text-primary-foreground" : "hover:bg-accent",
            )}
          >
            {t(SCALE_KEYS[s])}
          </button>
        ))}
      </div>

      <div
        onTouchStart={(e) => {
          pinch.current = e.touches.length === 2 ? distance(e.touches) : null;
        }}
        onTouchMove={(e) => {
          if (e.touches.length !== 2 || pinch.current === null) return;
          const ratio = distance(e.touches) / pinch.current;
          if (ratio > PINCH_IN || ratio < PINCH_OUT) {
            step(ratio > 1 ? -1 : 1);
            pinch.current = distance(e.touches); // one step per stretch, not one per pixel
          }
        }}
        onTouchEnd={() => {
          pinch.current = null;
        }}
      >
        {history.data ? (
          <PriceChart data={history.data} scale={scale} loading={history.isFetching} />
        ) : history.isError ? (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            {t("market.quotes.unavailable")}
          </p>
        ) : (
          <div className="h-[260px] animate-pulse rounded-md bg-muted/30" />
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        {t("market.quotes.source")}
        <span className="md:hidden"> {t("market.quotes.pinch")}</span>
      </p>
    </div>
  );
}

/* ── Last price and the move over the window ───────────────────────────── */

function move(data: QuoteHistory, scale: QuoteScale): { from: number; to: number } | null {
  if (data.points.length === 0) return null;
  const to = data.points[data.points.length - 1].close;
  // One day reads against yesterday's close, like a broker does; the other
  // scales against the first bar of their window.
  const from = scale === "1d" && data.previous_close ? data.previous_close : data.points[0].close;
  return from > 0 ? { from, to } : null;
}

function Headline({
  data,
  scale,
  label,
}: {
  data: QuoteHistory;
  scale: QuoteScale;
  label?: string | null;
}) {
  const { t } = useT();
  const m = move(data, scale);
  const pct = m ? m.to / m.from - 1 : null;
  const name = data.name && data.name !== label ? data.name : null;
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      {m && (
        <span className="font-mono text-2xl font-semibold tabular">
          {fmt.money(m.to, data.currency)}
        </span>
      )}
      {pct !== null && (
        <span
          className={cn(
            "font-mono text-sm tabular",
            pct >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
          )}
        >
          {fmt.signedPct(pct)}{" "}
          <span className="font-sans text-muted-foreground">
            {t(scale === "1d" ? "market.quotes.change.day" : "market.quotes.change.window")}
          </span>
        </span>
      )}
      {name && (
        <span className="basis-full truncate text-xs text-muted-foreground">
          {name} · {data.symbol}
        </span>
      )}
    </div>
  );
}

/* ── The curve ─────────────────────────────────────────────────────────── */

const COLOR = { line: "hsl(var(--foreground))" };

function tickLabel(iso: string, scale: QuoteScale, compact: boolean): string {
  switch (scale) {
    case "1d":
      return formatDate(iso, { hour: "2-digit", minute: "2-digit" });
    case "1w":
      return formatDate(iso, compact ? { weekday: "short" } : { weekday: "short", day: "numeric" });
    case "1m":
    case "6m":
      return formatDate(iso, { day: "numeric", month: "short" });
    default:
      return formatDate(iso, { month: "short", year: compact ? "2-digit" : "numeric" });
  }
}

/** Axis ticks: whole units once the window spans a few, cents on a tight one. */
function axisMoney(v: number, currency: string, span: number): string {
  return span > 5
    ? fmt.money(Math.round(v), currency).replace(/([.,]00)(?=\D*$)/, "")
    : fmt.money(v, currency);
}

function pointLabel(iso: string, intraday: boolean): string {
  return formatDate(
    iso,
    intraday
      ? { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }
      : { weekday: "short", day: "numeric", month: "short", year: "numeric" },
  );
}

function PriceChart({
  data,
  scale,
  loading,
}: {
  data: QuoteHistory;
  scale: QuoteScale;
  loading: boolean;
}) {
  const { t } = useT();
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const closes = useMemo(() => data.points.map((p) => p.close), [data]);
  const n = closes.length;
  const intraday =
    !data.interval.endsWith("d") && !data.interval.endsWith("wk") && !data.interval.endsWith("mo");
  const [yMin, yMax] = useMemo(() => {
    const lo = Math.min(...closes);
    const hi = Math.max(...closes);
    const pad = (hi - lo || Math.abs(hi) * 0.02 || 1) * 0.08;
    return [lo - pad, hi + pad];
  }, [closes]);
  const base = move(data, scale);
  const up = base ? base.to >= base.from : true;
  const stroke = up ? "hsl(var(--gain))" : "hsl(var(--loss))";

  const scales = (frame: ChartFrame) => ({
    xScale: linearScale([0, Math.max(1, n - 1)], [frame.left, frame.right]),
    yScale: linearScale([yMin, yMax], [frame.bottom, frame.top]),
  });

  return (
    <div className={cn("transition-opacity", loading && "opacity-60")}>
      <Chart
        ariaLabel={t("market.quotes.aria", { symbol: data.symbol })}
        height={(_w, compact) => (compact ? 240 : 300)}
        pad={(compact) =>
          compact
            ? { left: 60, right: 16, top: 12, bottom: 30 }
            : { left: 76, right: 24, top: 16, bottom: 32 }
        }
        onPointer={(p, frame) => setHoverIdx(p ? indexAt(p.x, frame, n) : null)}
        tooltip={(frame) => {
          if (hoverIdx === null || !base) return null;
          const { xScale, yScale } = scales(frame);
          const close = closes[hoverIdx];
          const pct = close / base.from - 1;
          return {
            x: xScale(hoverIdx),
            y: yScale(close),
            content: (
              <div className="space-y-0.5">
                <div className="font-sans font-medium text-foreground">
                  {pointLabel(data.points[hoverIdx].t, intraday)}
                </div>
                <div className="font-mono tabular">{fmt.money(close, data.currency)}</div>
                <div
                  className={cn(
                    "font-mono tabular",
                    pct >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                  )}
                >
                  {fmt.signedPct(pct)}
                </div>
              </div>
            ),
          };
        }}
      >
        {(frame) => {
          const { xScale, yScale } = scales(frame);
          return (
            <>
              <YAxis
                frame={frame}
                ticks={niceTicks(yMin, yMax, frame.compact ? 4 : 5)}
                scale={yScale}
                format={(v) => axisMoney(v, data.currency, yMax - yMin)}
                grid
              />
              <XAxis
                frame={frame}
                ticks={pickIndices(n, frame.compact ? 5 : 7).slice(1, -1)}
                scale={xScale}
                format={(i) => tickLabel(data.points[i].t, scale, frame.compact)}
              />
              {base && yMin < base.from && base.from < yMax && (
                <line
                  x1={frame.left}
                  x2={frame.right}
                  y1={yScale(base.from)}
                  y2={yScale(base.from)}
                  stroke={COLOR.line}
                  strokeDasharray="3 3"
                  strokeWidth="0.8"
                  opacity={0.35}
                />
              )}
              <path d={areaPath(closes, xScale, yScale, yMin)} fill={stroke} fillOpacity={0.08} />
              <path
                d={linePath(closes, xScale, yScale)}
                fill="none"
                stroke={stroke}
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              {hoverIdx !== null && (
                <>
                  <Crosshair frame={frame} x={xScale(hoverIdx)} />
                  <circle
                    cx={xScale(hoverIdx)}
                    cy={yScale(closes[hoverIdx])}
                    r={3.5}
                    fill={stroke}
                    stroke="hsl(var(--card))"
                    strokeWidth="1.5"
                  />
                </>
              )}
            </>
          );
        }}
      </Chart>
    </div>
  );
}

/* ── The sheet a row opens ─────────────────────────────────────────────── */

export function QuoteSheet({ quote, onClose }: { quote: QuoteRef | null; onClose: () => void }) {
  return (
    <BottomSheet open={quote !== null} onOpenChange={(open) => !open && onClose()}>
      <BottomSheetContent>
        {quote && (
          <>
            <BottomSheetHeader>
              <BottomSheetTitle>{quote.label || quote.symbol}</BottomSheetTitle>
              <BottomSheetDescription>{quote.symbol}</BottomSheetDescription>
            </BottomSheetHeader>
            <BottomSheetBody>
              <QuotePanel quote={quote} />
            </BottomSheetBody>
          </>
        )}
      </BottomSheetContent>
    </BottomSheet>
  );
}
