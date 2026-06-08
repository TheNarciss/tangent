import { useState } from "react";
import { Check, Sparkles, User, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type DataSource = "api" | "llm" | "user" | null;

interface DataFieldProps {
  /** Raw value to display, or null if unknown. */
  value: number | string | null;
  /** Provenance of the value. Drives the badge. */
  source: DataSource;
  /** Render the value as a string (e.g. percent, currency, ISIN). */
  formatValue?: (v: number | string) => string;
  /** Enable click-to-edit + inline input. Requires onEdit. */
  editable?: boolean;
  /** Called with the parsed numeric value when the user submits. */
  onEdit?: (newValue: number) => void;
  /** Optional client-side validation (return false to reject submit). */
  validate?: (newValue: number) => boolean;
  /** What to show when value === null. */
  placeholder?: string;
  inputStep?: string;
  inputMin?: string;
  inputMax?: string;
}

/**
 * Universal data field — shows a value, its source badge, and lets the user
 * override it inline. ADR-021 surface.
 */
export function DataField({
  value,
  source,
  formatValue = (v) => String(v),
  editable = false,
  onEdit,
  validate,
  placeholder = "—",
  inputStep = "0.0001",
  inputMin,
  inputMax,
}: DataFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string>(value !== null ? String(value) : "");

  if (editing && editable && onEdit) {
    const submit = () => {
      const n = parseFloat(draft);
      if (isNaN(n)) return;
      if (validate && !validate(n)) return;
      onEdit(n);
      setEditing(false);
    };
    return (
      <span className="inline-flex items-center gap-1">
        <input
          autoFocus
          type="number"
          step={inputStep}
          min={inputMin}
          max={inputMax}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
            if (e.key === "Escape") setEditing(false);
          }}
          className="h-6 w-20 rounded border bg-background px-1 text-right font-mono text-xs"
        />
        <button
          type="button"
          onClick={submit}
          className="text-emerald-600 hover:text-emerald-700"
          aria-label="Valider"
        >
          <Check className="h-3 w-3" />
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="text-muted-foreground hover:text-foreground"
          aria-label="Annuler"
        >
          <X className="h-3 w-3" />
        </button>
      </span>
    );
  }

  const display = value === null ? placeholder : formatValue(value);
  const baseClasses = cn("font-mono tabular", value === null && "text-muted-foreground");

  if (editable && onEdit) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setEditing(true)}
          className={cn(
            baseClasses,
            "cursor-pointer border-0 bg-transparent p-0 text-inherit hover:underline",
          )}
          title="Cliquer pour modifier"
        >
          {display}
        </button>
        <SourceBadge source={source} />
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={baseClasses}>{display}</span>
      <SourceBadge source={source} />
    </span>
  );
}

function SourceBadge({ source }: { source: DataSource }) {
  if (source === "api" || source === null) return null;

  if (source === "llm") {
    return (
      <span
        title="Estimation IA, à vérifier"
        className="inline-flex items-center rounded-full border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400"
      >
        <Sparkles className="mr-0.5 h-2.5 w-2.5" />
        IA
      </span>
    );
  }

  if (source === "user") {
    return (
      <span
        title="Modifié manuellement"
        className="inline-flex items-center rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400"
      >
        <User className="mr-0.5 h-2.5 w-2.5" />
        Vous
      </span>
    );
  }

  return null;
}
