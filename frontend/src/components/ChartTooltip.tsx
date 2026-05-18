import type { ReactNode } from "react";

interface Props {
  /** Pixel x within the parent container (left). */
  x: number;
  /** Pixel y within the parent container (top). */
  y: number;
  /** Total container width — used to flip the tooltip if too close to the right edge. */
  containerWidth: number;
  children: ReactNode;
}

const W = 240;

/**
 * Absolute-positioned tooltip card. The parent must be `relative`. Flips to the
 * left of the cursor when the cursor is past the midpoint of the container.
 */
export function ChartTooltip({ x, y, containerWidth, children }: Props) {
  const left = x < containerWidth / 2 ? x + 12 : x - W - 12;
  return (
    <div
      className="pointer-events-none absolute z-10 rounded-md border bg-popover/95 backdrop-blur px-3 py-2 text-xs shadow-lg"
      style={{ left, top: Math.max(8, y - 12), width: W }}
    >
      {children}
    </div>
  );
}