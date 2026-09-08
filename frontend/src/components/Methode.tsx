import { Link } from "react-router-dom";

import { useVerdicts, type FeesVerdictDetails, type Verdict } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NAV_PATHS } from "@/components/Sidebar";
import { VerdictCard } from "@/components/ui/verdict-card";

/**
 * « Méthode » : every verdict of the method as a folded card (ADR-023).
 * A card shows a traffic light, one sentence, an amount and an action; the
 * computation behind it only appears on tap, so the page stays readable on
 * a phone and the detail exists for whoever wants it.
 */
export function Methode() {
  const q = useVerdicts();

  if (q.isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-muted/30" />
        ))}
      </div>
    );
  }
  if (q.isError || !q.data) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <p className="text-sm font-medium">Les verdicts ne sont pas disponibles pour l'instant</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {q.error instanceof Error ? q.error.message : "Réessaie dans un instant."}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <p className="text-sm text-muted-foreground">
        Chaque carte est un verdict : un feu, une phrase, un montant par an, une chose à faire.
        Ouvre une carte pour voir le calcul.
      </p>
      {q.data.verdicts.map((v) => (
        <VerdictCard key={v.id} verdict={v}>
          {v.id === "fees" ? (
            <FeesDetails details={v.details as FeesVerdictDetails} />
          ) : (
            <GenericDetails verdict={v} />
          )}
        </VerdictCard>
      ))}
      <p className="text-xs text-muted-foreground">
        Prochains verdicts : où placer le prochain euro (enveloppes et impôt), part d'actions selon
        ton profil, rééquilibrage, épargne nécessaire pour ton objectif.
      </p>
    </div>
  );
}

/* ── Frais réels ───────────────────────────────────────────────────────── */

function FeesDetails({ details: d }: { details: FeesVerdictDetails }) {
  const lines = d.lines ?? [];
  const missing = d.missing_ter ?? [];
  const uncovered = d.uncovered_accounts ?? [];

  if (d.positions_total_eur === undefined) {
    return uncovered.length > 0 ? <Uncovered accounts={uncovered} /> : null;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Frais des fonds"
          value={fmt.eur0(d.fund_fees_eur ?? 0)}
          sub={`TER de chaque ligne × sa valeur${missing.length ? ", lignes sans TER exclues" : ""}`}
        />
        <Figure
          label="Frais du courtier"
          value={fmt.eur0(d.broker_fees_eur ?? 0)}
          sub={`${d.broker_name ?? "courtier"} : garde, frais par ligne, courtage sur ${fmt.eur(
            d.monthly_contribution_eur ?? 0,
          )}/mois`}
        />
        <Figure
          label="Référence"
          value={fmt.eur0(d.reference_eur ?? 0)}
          sub={`PEA en ligne + ETF monde, ${fmt.pct(d.reference_pct ?? 0)} par an`}
        />
      </div>

      <ul className="divide-y rounded-md border text-sm">
        {lines.map((l) => (
          <li key={`${l.account}-${l.ticker}`} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="truncate">{l.label}</div>
              <div className="truncate text-xs text-muted-foreground">
                {l.account} · {fmt.eur(l.value_eur)}
              </div>
            </div>
            <div className="shrink-0 text-right">
              {l.ter === null ? (
                <Link to={NAV_PATHS.accounts} className="text-xs text-primary underline">
                  TER à renseigner
                </Link>
              ) : (
                <>
                  <div className="font-mono tabular">{fmt.eur0(l.fund_fee_eur ?? 0)}</div>
                  <div className="font-mono text-xs tabular text-muted-foreground">
                    {fmt.pct(l.ter)} par an
                  </div>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>

      {uncovered.length > 0 && <Uncovered accounts={uncovered} />}

      <p className="text-xs text-muted-foreground">
        Total {fmt.eur0(d.total_fees_eur ?? 0)} par an, soit {fmt.pct(d.total_fees_pct ?? 0)} de{" "}
        {fmt.eur0(d.positions_total_eur)}. Vert jusqu'à {fmt.pct(d.thresholds?.green_max ?? 0)} par
        an, orange jusqu'à {fmt.pct(d.thresholds?.amber_max ?? 0)}. Les frais des fonds sont déjà
        dans les cours : ils ne sont pas retirés une seconde fois de la projection.
      </p>
    </div>
  );
}

function Uncovered({
  accounts,
}: {
  accounts: { name: string; account_type: string; value_eur: number }[];
}) {
  return (
    <div className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
      Non mesuré, le contrat ne détaille pas ses lignes :{" "}
      {accounts.map((a) => `${a.name} (${fmt.eur0(a.value_eur)})`).join(", ")}.
    </div>
  );
}

/* ── Atoms ─────────────────────────────────────────────────────────────── */

function Figure({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-lg font-semibold tabular">{value}</div>
      {sub && <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{sub}</div>}
    </div>
  );
}

function GenericDetails({ verdict }: { verdict: Verdict }) {
  const entries = Object.entries(verdict.details);
  if (entries.length === 0) return null;
  return (
    <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
      {entries.map(([k, v]) => (
        <div key={k} className={cn("rounded-md border px-3 py-2")}>
          <dt className="text-xs text-muted-foreground">{k}</dt>
          <dd className="font-mono tabular">{typeof v === "number" ? fmt.num(v) : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
