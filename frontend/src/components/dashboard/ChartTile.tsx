import { useState } from "react";

import { useTimeseries } from "@/api";
import { Timeline } from "@/components/Timeline";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { cn } from "@/lib/utils";

interface ChartTileProps {
  className?: string;
}

const SPARKLINE_DAYS = 90;
const SVG_WIDTH = 300;
const SVG_HEIGHT = 60;

/**
 * Compact 90-day portfolio sparkline. Tap (mobile) or click (desktop) to
 * open the full Timeline component in a bottom sheet / modal.
 *
 * Reads from `/timeseries` which returns the portfolio rebased to 100, so
 * the delta % is computed as (last - first) / first × 100 — i.e. the
 * relative performance over the window. This is the right metric for
 * "how is the portfolio doing", not the absolute net worth (which would
 * also include cash + loans changes we do not historicize).
 */
export function ChartTile({ className }: ChartTileProps) {
  const { data: timeseries, isLoading } = useTimeseries();
  const [open, setOpen] = useState(false);

  if (isLoading || !timeseries || timeseries.portfolio.length < 2) {
    return (
      <div
        className={cn(
          "flex flex-col gap-2 rounded-lg border border-border bg-card p-4 md:p-5",
          className,
        )}
      >
        <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Évolution · 90 jours
        </div>
        <div className="mt-2 h-16 animate-pulse rounded bg-muted/30 md:h-20" />
      </div>
    );
  }

  const points = timeseries.portfolio.slice(-SPARKLINE_DAYS);
  const first = points[0];
  const last = points[points.length - 1];
  const delta = first > 0 ? ((last - first) / first) * 100 : 0;
  const isPositive = delta >= 0;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const path = points
    .map((v, i) => {
      const x = (i / (points.length - 1)) * SVG_WIDTH;
      const y = SVG_HEIGHT - ((v - min) / range) * SVG_HEIGHT;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  const colorClass = isPositive ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          "flex cursor-pointer flex-col gap-2 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5",
          className,
        )}
      >
        <div className="flex items-baseline justify-between">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Évolution · {points.length} jours
          </div>
          <div className={cn("text-xs font-medium", colorClass)}>
            {isPositive ? "+" : ""}
            {delta.toFixed(1)} %
          </div>
        </div>
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          className="h-16 w-full md:h-20"
          preserveAspectRatio="none"
        >
          <path
            d={path}
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
            className={colorClass}
          />
        </svg>
        <div className="text-[10px] text-muted-foreground">Voir le détail →</div>
      </button>

      <BottomSheet open={open} onOpenChange={setOpen}>
        <BottomSheetContent className="md:max-w-3xl">
          <BottomSheetHeader>
            <BottomSheetTitle>Évolution du portefeuille</BottomSheetTitle>
          </BottomSheetHeader>
          <div className="p-4 md:p-6">
            <Timeline ts={timeseries} />
          </div>
        </BottomSheetContent>
      </BottomSheet>
    </>
  );
}
