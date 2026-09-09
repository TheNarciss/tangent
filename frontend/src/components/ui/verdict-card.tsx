import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { useVerdicts, type Verdict, type VerdictStatus } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";

export const VERDICT_STATUS: Record<VerdictStatus, { label: string; dot: string; text: string }> = {
  green: { label: "Rien à changer", dot: "bg-[hsl(var(--gain))]", text: "text-[hsl(var(--gain))]" },
  amber: { label: "À surveiller", dot: "bg-amber-500", text: "text-amber-600 dark:text-amber-400" },
  red: { label: "À corriger", dot: "bg-[hsl(var(--loss))]", text: "text-[hsl(var(--loss))]" },
  unknown: { label: "Incomplet", dot: "bg-muted-foreground/40", text: "text-muted-foreground" },
};

/** The traffic light alone — used inline on the simple screens. */
export function VerdictDot({ status, className }: { status: VerdictStatus; className?: string }) {
  return (
    <span
      aria-label={VERDICT_STATUS[status].label}
      className={cn(
        "inline-block h-2.5 w-2.5 shrink-0 rounded-full",
        VERDICT_STATUS[status].dot,
        className,
      )}
    />
  );
}

interface VerdictCardProps {
  verdict: Verdict;
  /** The breakdown shown once the card is opened. */
  children?: ReactNode;
  defaultOpen?: boolean;
}

/**
 * One verdict, folded (ADR-023): status, sentence, euros and action are
 * always visible; the computation only appears on tap. Same layout on a
 * phone (stacked) and a desktop (the amount sits on the right).
 */
export function VerdictCard({ verdict, children, defaultOpen = false }: VerdictCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const status = VERDICT_STATUS[verdict.status];
  const impact = verdict.impact_eur_per_year;

  return (
    <details
      className="group rounded-xl border bg-card"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="flex min-h-[44px] cursor-pointer select-none list-none items-start gap-3 p-4 md:p-5 [&::-webkit-details-marker]:hidden">
        <VerdictDot status={verdict.status} className="mt-1.5" />
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span className="text-base font-semibold">{verdict.title}</span>
            <span className={cn("text-xs font-medium", status.text)}>{status.label}</span>
          </div>
          <p className="text-sm leading-snug">{verdict.headline}</p>
          {verdict.action && (
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">À faire : </span>
              {verdict.action}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {impact !== null && impact > 0 && (
            <span className={cn("font-mono text-sm tabular md:text-base", status.text)}>
              {fmt.eur0(impact)}
              <span className="ml-1 text-xs text-muted-foreground">/an</span>
            </span>
          )}
          <ChevronDown
            className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180"
            aria-hidden
          />
        </div>
      </summary>
      {open && children && <div className="border-t p-4 md:p-5">{children}</div>}
    </details>
  );
}

/**
 * One verdict on a simple screen (ADR-023): the traffic light and the
 * sentence, nothing else, linking to the Méthode tab for the computation.
 * Renders nothing while loading or when the verdict is absent.
 */
export function VerdictLine({
  id,
  to,
  hideWhenGreen = false,
}: {
  id: string;
  to: string;
  /** For alerts: say nothing while there is nothing to say. */
  hideWhenGreen?: boolean;
}) {
  const q = useVerdicts();
  const v = q.data?.verdicts.find((x) => x.id === id);
  if (!v) return null;
  if (hideWhenGreen && (v.status === "green" || v.status === "unknown")) return null;
  return (
    <Link
      to={to}
      className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent/30 md:px-6"
    >
      <VerdictDot status={v.status} />
      <span className="min-w-0 flex-1 leading-snug">{v.headline}</span>
      <span className="shrink-0 text-xs text-muted-foreground">Détail</span>
    </Link>
  );
}
