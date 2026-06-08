import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type TileAccent = "neutral" | "success" | "danger" | "info" | "warning";

interface BentoTileProps {
  /** Short uppercase label above the value (e.g. "Net worth", "Cash"). */
  label: string;
  /** The headline number, formatted as a string. Use mono/tabular nums. */
  value: string;
  /** Optional sub-line below the value (delta %, period, comment). */
  sub?: ReactNode;
  /** Color accent on the sub-line. Defaults to neutral muted. */
  accent?: TileAccent;
  /** Size variant — controls the value's font size. */
  size?: "sm" | "md" | "lg";
  /** If provided, the tile becomes a button (cursor + hover bg). */
  onClick?: () => void;
  /** Extra content slot (sparkline, badge, etc.) below the sub-line. */
  children?: ReactNode;
  className?: string;
}

const ACCENT_CLASSES: Record<TileAccent, string> = {
  neutral: "text-muted-foreground",
  success: "text-[hsl(var(--gain))]",
  danger: "text-[hsl(var(--loss))]",
  info: "text-[hsl(var(--info))]",
  warning: "text-amber-600 dark:text-amber-400",
};

const VALUE_SIZE_CLASSES: Record<"sm" | "md" | "lg", string> = {
  sm: "text-base md:text-lg",
  md: "text-lg md:text-xl",
  lg: "text-2xl md:text-3xl",
};

/**
 * Generic bento tile used throughout the Dashboard. Always renders the same
 * vertical structure (label → value → sub → children) so a grid of tiles
 * aligns perfectly regardless of which fields are filled.
 *
 * When `onClick` is provided, the tile renders as a `<button>` with hover
 * affordance — used for preview-to-expand patterns (tap a tile to open a
 * bottom sheet with the full content).
 */
export function BentoTile({
  label,
  value,
  sub,
  accent = "neutral",
  size = "md",
  onClick,
  children,
  className,
}: BentoTileProps) {
  const baseClasses = cn(
    "flex flex-col gap-1 rounded-lg border border-border bg-card p-3 text-left md:p-4",
    onClick &&
      "cursor-pointer transition-colors hover:bg-accent/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
    className,
  );

  const content = (
    <>
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span
        className={cn("font-mono tabular font-semibold tracking-tight", VALUE_SIZE_CLASSES[size])}
      >
        {value}
      </span>
      {sub !== undefined && sub !== null && (
        <span className={cn("text-xs", ACCENT_CLASSES[accent])}>{sub}</span>
      )}
      {children}
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={baseClasses}>
        {content}
      </button>
    );
  }
  return <div className={baseClasses}>{content}</div>;
}
