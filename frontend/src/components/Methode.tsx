import { Link } from "react-router-dom";

import {
  useVerdicts,
  type FeesVerdictDetails,
  type NextEuroVerdictDetails,
  type RiskShareVerdictDetails,
  type Verdict,
} from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NAV_PATHS } from "@/components/Sidebar";
import { VerdictCard, VerdictDot } from "@/components/ui/verdict-card";

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
          ) : v.id === "next_euro" ? (
            <NextEuroDetails details={v.details as NextEuroVerdictDetails} />
          ) : v.id === "risk_share" ? (
            <RiskShareDetails details={v.details as RiskShareVerdictDetails} />
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

/* ── Où placer le prochain euro ────────────────────────────────────────── */

function NextEuroDetails({ details: d }: { details: NextEuroVerdictDetails }) {
  const steps = d.steps ?? [];
  const p = d.precaution;
  if (steps.length === 0) return null;
  return (
    <div className="space-y-4">
      {p && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Figure
            label="Sur tes livrets"
            value={fmt.eur0(p.liquid_eur)}
            sub={
              p.months_covered !== null
                ? `${p.months_covered.toFixed(1).replace(".", ",")} mois de dépenses`
                : "dépenses mensuelles inconnues"
            }
          />
          <Figure
            label="Cible de précaution"
            value={p.target_eur !== null ? fmt.eur0(p.target_eur) : "—"}
            sub={`${p.target_months} mois de dépenses`}
          />
          <Figure
            label="Dépenses par mois"
            value={p.monthly_spending_eur !== null ? fmt.eur0(p.monthly_spending_eur) : "—"}
            sub="débits de tes comptes courants, 90 derniers jours"
          />
        </div>
      )}

      <ol className="divide-y rounded-md border text-sm">
        {steps.map((s, i) => (
          <li key={s.id} className="flex items-start gap-3 px-3 py-2.5">
            <span className="mt-0.5 w-4 shrink-0 font-mono text-xs text-muted-foreground">
              {i + 1}
            </span>
            <VerdictDot status={s.status} className="mt-1.5" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="font-medium">{s.label}</span>
                {s.impact_eur_per_year !== null && s.impact_eur_per_year > 0 && (
                  <span className="font-mono text-xs tabular text-muted-foreground">
                    {fmt.eur0(s.impact_eur_per_year)}/an
                  </span>
                )}
              </div>
              <p className="text-muted-foreground">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <p className="text-xs text-muted-foreground">
        La règle, dans l'ordre : précaution sur livrets, puis actions à long terme dans le PEA, puis
        PER seulement au-dessus de la tranche à 30 %, le reste en compte-titres.
        {d.tax?.tmi !== null && d.tax?.tmi !== undefined
          ? ` Ta tranche d'imposition estimée : ${fmt.pct(d.tax.tmi)}, d'après ton revenu fiscal et tes parts.`
          : ""}
      </p>
    </div>
  );
}

/* ── Part d'actions ────────────────────────────────────────────────────── */

function RiskShareDetails({ details: d }: { details: RiskShareVerdictDetails }) {
  if (d.pocket_eur === undefined || d.actual_share === undefined) return null;
  const actual = d.actual_share;
  const target = d.target_share ?? actual;
  const band = d.band ?? 0.1;
  const lo = Math.max(0, target - band);
  const hi = Math.min(1, target + band);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Part d'actions"
          value={fmt.pct0(actual)}
          sub={`${fmt.eur0(d.equity_eur ?? 0)} en lignes cotées sur ${fmt.eur0(d.pocket_eur)}`}
        />
        <Figure
          label="Part visée"
          value={fmt.pct0(target)}
          sub={
            d.horizon_cap !== undefined &&
            d.merton_share !== undefined &&
            d.horizon_cap < d.merton_share
              ? `plafonnée par ton horizon de ${d.horizon_years} ans (${fmt.pct0(d.merton_share)} sinon)`
              : `profil « ${d.risk_label ?? "?"} », horizon ${d.horizon_years ?? 10} ans`
          }
        />
        <Figure
          label="Mauvaise année"
          value={`−${fmt.eur0(d.bad_year_eur ?? 0)}`}
          sub="deux fois la volatilité des actions sur ta poche actions"
        />
      </div>

      {/* Gauge: actual vs target band, same on a phone and a desktop. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `calc(${target * 100}% - 1px)` }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${actual * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>0 % actions</span>
          <span>
            bande {fmt.pct0(lo)} – {fmt.pct0(hi)}
          </span>
          <span>100 %</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        La part visée est le point de la droite de marché que ton curseur choisit (volatilité
        maximale de ton cran divisée par celle des actions monde, {fmt.pct(d.equity_sigma ?? 0.15)}
        ). C'est la part de Merton, avec une aversion au risque γ ≈{" "}
        {d.gamma ? d.gamma.toFixed(1).replace(".", ",") : "?"}. Les lignes cotées comptent comme
        actions ; fonds euros, PER ou assurance vie sans détail et PEL comptent comme produits de
        taux.
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
