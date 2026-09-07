import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { Scale } from "@/lib/chart";

/**
 * Responsive SVG chart frame shared by Projection, Timeline and RiskReturn.
 *
 * The SVG viewBox equals the container's CSS size, so 1 SVG unit = 1 px and
 * text set in px stays legible on a 390 px phone (no more 720-wide viewBox
 * scaled down to 5 px glyphs). Pointer events (mouse, pen, touch) are
 * reported in the same px space; the tooltip is HTML, positioned and clamped
 * inside the container.
 */

export interface ChartPad {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface ChartFrame {
  /** Container size in CSS px — also the SVG viewBox. */
  width: number;
  height: number;
  pad: ChartPad;
  innerW: number;
  innerH: number;
  /** Plot-area bounds (px). */
  left: number;
  right: number;
  top: number;
  bottom: number;
  /** Narrow container (phone): fewer ticks, smaller paddings. */
  compact: boolean;
}

export interface ChartPointer {
  x: number;
  y: number;
  /** True when the pointer is inside the plot area. */
  inside: boolean;
}

export interface ChartTooltipState {
  /** Anchor in px (SVG space). */
  x: number;
  y: number;
  content: ReactNode;
}

interface ChartProps {
  /** Height in px, or a function of the measured width. */
  height: number | ((width: number, compact: boolean) => number);
  pad: ChartPad | ((compact: boolean) => ChartPad);
  ariaLabel: string;
  className?: string;
  /**
   * Pointer position on move/tap; `null` when a mouse leaves the SVG. A touch
   * never sends `null`, so the last tapped point stays visible.
   */
  onPointer?: (p: ChartPointer | null, frame: ChartFrame) => void;
  /** Tooltip anchor + content for the current frame; `null` hides it. */
  tooltip?: (frame: ChartFrame) => ChartTooltipState | null;
  children: (frame: ChartFrame) => ReactNode;
}

/** Below this width the chart is drawn in its compact variant. */
export const COMPACT_BELOW = 480;

export function Chart({
  height,
  pad,
  ariaLabel,
  className,
  onPointer,
  tooltip,
  children,
}: ChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setWidth(el.getBoundingClientRect().width);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const compact = width < COMPACT_BELOW;
  const h = typeof height === "function" ? height(width, compact) : height;
  const p = typeof pad === "function" ? pad(compact) : pad;
  const frame: ChartFrame = {
    width,
    height: h,
    pad: p,
    innerW: Math.max(0, width - p.left - p.right),
    innerH: Math.max(0, h - p.top - p.bottom),
    left: p.left,
    right: width - p.right,
    top: p.top,
    bottom: h - p.bottom,
    compact,
  };

  const report = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!onPointer) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    onPointer(
      { x, y, inside: x >= frame.left && x <= frame.right && y >= frame.top && y <= frame.bottom },
      frame,
    );
  };
  const tip = width > 0 && tooltip ? tooltip(frame) : null;

  return (
    <div ref={ref} className={cn("relative w-full", className)}>
      {width > 0 && (
        <svg
          width={width}
          height={h}
          viewBox={`0 0 ${width} ${h}`}
          className="block touch-pan-y select-none"
          role="img"
          aria-label={ariaLabel}
          onPointerMove={report}
          onPointerDown={report}
          onPointerLeave={(e) => {
            if (e.pointerType === "mouse") onPointer?.(null, frame);
          }}
        >
          {children(frame)}
        </svg>
      )}
      {tip && (
        <TooltipBox x={tip.x} y={tip.y} width={width} height={h}>
          {tip.content}
        </TooltipBox>
      )}
    </div>
  );
}

/* ─── Tooltip ────────────────────────────────────────────────────────────── */

const TOOLTIP_W = 240;

/**
 * HTML tooltip anchored at (x, y) px. Sits to the right of the anchor on the
 * left half of the chart, to the left otherwise; above the anchor on the
 * lower half, below otherwise. Never leaves the container horizontally.
 */
function TooltipBox({
  x,
  y,
  width,
  height,
  children,
}: {
  x: number;
  y: number;
  width: number;
  height: number;
  children: ReactNode;
}) {
  const boxW = Math.min(TOOLTIP_W, width - 16);
  const preferred = x < width / 2 ? x + 12 : x - boxW - 12;
  const left = Math.max(8, Math.min(preferred, width - boxW - 8));
  const above = y > height / 2;
  return (
    <div
      className="pointer-events-none absolute z-10 rounded-md border bg-popover/95 px-3 py-2 text-xs shadow-lg backdrop-blur"
      style={{
        left,
        width: boxW,
        top: above ? y - 10 : y + 10,
        transform: above ? "translateY(-100%)" : undefined,
      }}
    >
      {children}
    </div>
  );
}

/* ─── Helpers ────────────────────────────────────────────────────────────── */

/** Index (0..n-1) of the series point nearest to pointer x, or null outside. */
export function indexAt(x: number, frame: ChartFrame, n: number): number | null {
  if (n <= 0 || x < frame.left || x > frame.right) return null;
  const t = frame.innerW > 0 ? (x - frame.left) / frame.innerW : 0;
  return Math.max(0, Math.min(n - 1, Math.round(t * (n - 1))));
}

/* ─── Axis atoms (px-sized text) ─────────────────────────────────────────── */

const TICK_TEXT = "font-mono text-[11px] fill-current text-muted-foreground";

export function YAxis({
  frame,
  ticks,
  scale,
  format,
  grid,
}: {
  frame: ChartFrame;
  ticks: number[];
  scale: Scale;
  format: (v: number) => string;
  /** Draw a faint horizontal grid line for each tick. */
  grid?: boolean;
}) {
  return (
    <g className={TICK_TEXT}>
      {ticks.map((t) => (
        <g key={t}>
          {grid && (
            <line
              x1={frame.left}
              x2={frame.right}
              y1={scale(t)}
              y2={scale(t)}
              stroke="hsl(var(--border))"
              strokeWidth="0.5"
              opacity="0.6"
            />
          )}
          <line
            x1={frame.left - 4}
            x2={frame.left}
            y1={scale(t)}
            y2={scale(t)}
            stroke="currentColor"
          />
          <text x={frame.left - 7} y={scale(t) + 3.5} textAnchor="end">
            {format(t)}
          </text>
        </g>
      ))}
    </g>
  );
}

export function XAxis({
  frame,
  ticks,
  scale,
  format,
  y,
  label,
}: {
  frame: ChartFrame;
  ticks: number[];
  scale: Scale;
  format: (v: number) => string;
  /** Axis baseline in px; defaults to the plot bottom. */
  y?: number;
  label?: string;
}) {
  const baseline = y ?? frame.bottom;
  return (
    <g className={TICK_TEXT}>
      <line
        x1={frame.left}
        x2={frame.right}
        y1={baseline}
        y2={baseline}
        stroke="hsl(var(--border))"
      />
      {ticks.map((t) => (
        <g key={t}>
          <line x1={scale(t)} x2={scale(t)} y1={baseline} y2={baseline + 4} stroke="currentColor" />
          <text x={scale(t)} y={baseline + 16} textAnchor="middle">
            {format(t)}
          </text>
        </g>
      ))}
      {label && (
        <text
          x={frame.left + frame.innerW / 2}
          y={frame.height - 6}
          textAnchor="middle"
          className="font-sans text-xs"
        >
          {label}
        </text>
      )}
    </g>
  );
}

/** Vertical dashed line at x spanning the plot area. */
export function Crosshair({
  frame,
  x,
  y1,
  y2,
}: {
  frame: ChartFrame;
  x: number;
  y1?: number;
  y2?: number;
}) {
  return (
    <line
      x1={x}
      x2={x}
      y1={y1 ?? frame.top}
      y2={y2 ?? frame.bottom}
      stroke="hsl(var(--foreground))"
      strokeDasharray="2 3"
      strokeWidth="0.8"
      opacity={0.5}
      pointerEvents="none"
    />
  );
}
