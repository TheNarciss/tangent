import type { ReactNode } from "react";

/** Tooltip props: either absolute pixel coords (x/y) or SVG coords (cx/cy + vbW/vbH)
 *  containerWidth / containerW is the CSS pixel width of the SVG's container. */
type PixelProps = {
  x: number;
  y: number;
  containerWidth: number;
  children: ReactNode;
};

type SvgProps = {
  cx: number; // SVG coord (viewBox space)
  cy: number; // SVG coord (viewBox space)
  containerW: number; // container width in CSS px
  vbW: number; // viewBox width (e.g. W)
  vbH: number; // viewBox height (e.g. H) — kept for clarity
  children: ReactNode;
};

type Props = PixelProps | SvgProps;

const W = 240;

/**
 * Absolute-positioned tooltip card. The parent must be `relative`. Flips to the
 * left of the cursor when the cursor is past the midpoint of the container.
 * Accepts either pixel coords (x/y) or SVG coords (cx/cy + vbW). When SVG coords
 * are provided we convert to CSS pixels assuming the SVG scales uniformly to
 * fit the container width ("w-full h-auto").
 */
export function ChartTooltip(props: Props) {
  let x: number;
  let y: number;
  let containerWidth: number;

  if ("x" in props) {
    x = props.x;
    y = props.y;
    containerWidth = props.containerWidth;
  } else {
    // SVG coords -> CSS pixels. With responsive SVG (w-full h-auto) both axes
    // scale by containerWidth / vbW.
    const scale = props.containerW / props.vbW;
    x = props.cx * scale;
    y = props.cy * scale;
    containerWidth = props.containerW;
  }

  const width = Math.min(W, containerWidth - 16);
  const preferred = x < containerWidth / 2 ? x + 12 : x - width - 12;
  const left = Math.max(8, Math.min(preferred, containerWidth - width - 8));
  return (
    <div
      className="pointer-events-none absolute z-10 rounded-md border bg-popover/95 backdrop-blur px-3 py-2 text-xs shadow-lg"
      style={{ left, top: Math.max(8, y - 12), width }}
    >
      {props.children}
    </div>
  );
}
