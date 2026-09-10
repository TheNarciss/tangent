import { ChevronDown } from "lucide-react";

import {
  useDashboard,
  useRiskLevels,
  type PortfolioMetrics,
  type RiskLevel,
  type StressTestResult,
} from "@/api";
import { fmt } from "@/lib/format";
import { useProfile } from "@/lib/profile";
import { cn } from "@/lib/utils";

/**
 * What a crash would cost, inside the « baisse » verdict (ADR-028).
 *
 * Three reference figures stay visible because they answer three different
 * questions; the ten replayed crises fold, because ten of anything is a wall.
 */
export function StressList() {
  const dashboard = useDashboard();
  const levels = useRiskLevels();
  const [profile] = useProfile();
  if (!dashboard.data) return null;
  return (
    <RiskDetail
      metrics={dashboard.data.metrics}
      stress={dashboard.data.stress_tests}
      levels={levels.data}
      profileLevel={profile ? profile.risk_level : null}
    />
  );
}

function RiskDetail({
  metrics,
  stress,
  levels,
  profileLevel,
}: {
  metrics: PortfolioMetrics;
  stress: StressTestResult[];
  levels: RiskLevel[] | undefined;
  profileLevel: number | null;
}) {
  // The portfolio behaves like the first slider position whose ceiling it fits under.
  const behaves =
    levels?.find((l) => metrics.volatility <= l.max_annual_volatility) ?? levels?.at(-1);
  const chosen = levels?.find((l) => l.level === profileLevel);

  // The list arrives worst-first: the heaviest crisis stays visible, the rest folds.
  const [worst, ...others] = stress;

  return (
    <div className="space-y-3">
      {behaves && (
        <p className="text-sm">
          Ton portefeuille se comporte comme un profil{" "}
          <span className="rounded-full border px-2 py-0.5 text-xs font-medium">
            {behaves.label}
          </span>
          {chosen && chosen.level !== behaves.level && (
            <span className="text-muted-foreground">
              {" "}
              alors que ton curseur est sur{" "}
              <strong className="text-foreground">{chosen.label}</strong>
              {behaves.level > chosen.level
                ? " : il bouge plus que ce que tu as dit accepter."
                : " : il bouge moins que ce que tu acceptes."}
            </span>
          )}
          {chosen && chosen.level === behaves.level && (
            <span className="text-muted-foreground">, comme ton curseur. Cohérent.</span>
          )}
        </p>
      )}

      {/* Les deux repères restent visibles ; les dix crises se déplient. */}
      <ul className="mt-3 space-y-2 text-sm">
        {worst && (
          <li className="rounded-md border px-3 py-2">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <span>Pire crise rejouée : {worst.label}</span>
              <Loss eur={worst.loss_eur} pct={worst.pnl_pct} />
            </div>
            <div className="text-xs text-muted-foreground">
              {worst.start} → {worst.end}
            </div>
          </li>
        )}
        {metrics.worst_year_class !== null && (
          <li className="rounded-md border px-3 py-2">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <span>Pire année déjà vue sur {metrics.worst_year_label ?? "cette classe"}</span>
              <span className="font-mono tabular text-[hsl(var(--loss))]">
                {fmt.signedPct(metrics.worst_year_class)}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              douze mois consécutifs, sur l'historique complet de la classe depuis 1990
            </div>
          </li>
        )}
        <li className="rounded-md border px-3 py-2">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3">
            <span>Pire baisse vécue par ce panier</span>
            <span className="font-mono tabular text-[hsl(var(--loss))]">
              {fmt.signedPct(metrics.max_drawdown_observed)}
            </span>
          </div>
          <div className="text-xs text-muted-foreground">
            du plus-haut au creux suivant, sur {historyLabel(metrics.history_days)} d'historique
            commun à tes lignes
            {metrics.history_days > 0 && metrics.history_days < SHORT_HISTORY_DAYS
              ? " — trop court pour être comparé aux crises ci-dessus"
              : ""}
          </div>
        </li>
      </ul>

      {others.length > 0 && (
        <details className="group mt-2 rounded-md border">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm">
            <span>
              Les {stress.length} crises rejouées, une par une
              <span className="ml-2 text-xs text-muted-foreground">
                de {fmt.eur0(Math.abs(worst?.loss_eur ?? 0))} à{" "}
                {fmt.eur0(Math.abs(others[others.length - 1].loss_eur))}
              </span>
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
          </summary>

          <ul className="space-y-2 border-t p-3 text-sm">
            {stress.map((crisis) => {
              const fx = crisis.currency_effect_eur;
              return (
                <li key={crisis.id} className="rounded-md border px-3 py-2">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <span>{crisis.label}</span>
                    <Loss eur={crisis.loss_eur} pct={crisis.pnl_pct} />
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {crisis.start} → {crisis.end} · {crisis.description}
                  </div>
                  {fx !== null && Math.abs(fx) >= 1 && (
                    <div className="text-xs text-muted-foreground">
                      Dont le dollar : {fx > 0 ? "il t'a fait gagner" : "il t'a coûté"}{" "}
                      {fmt.eur0(Math.abs(fx))}, soit{" "}
                      {fmt.signedPct(crisis.currency_effect_pct ?? 0)} sur tes fonds monde.
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          <p className="border-t px-3 py-2 text-xs text-muted-foreground">
            Les crises sont rejouées sur les classes d'actifs, pas sur les cours de tes lignes :
            aucun ETF français n'a d'historique avant 2009. Chaque perte est en euros, change
            compris, et le pourcentage porte sur <strong>tout ton patrimoine</strong>, pas seulement
            sur tes placements. Tes livrets ne bougent pas et ton fonds euros ne perd pas sa valeur,
            seul son taux futur baisse. Un fonds sectoriel est rejoué avec l'amplitude des actions
            monde, ce qui le sous-estime.
          </p>
        </details>
      )}
    </div>
  );
}

function Loss({ eur, pct }: { eur: number; pct: number }) {
  return (
    <span
      className={cn(
        "font-mono tabular",
        eur < 0 ? "text-[hsl(var(--loss))]" : "text-[hsl(var(--gain))]",
      )}
    >
      {fmt.eur0(Math.abs(eur))}{" "}
      <span className="text-xs text-muted-foreground">({fmt.signedPct(pct)})</span>
    </span>
  );
}

/** Below this, the basket's own history says more about a fund's launch date
 * than about risk: a single recent line truncates every other one. */
const SHORT_HISTORY_DAYS = 3 * 252;

function historyLabel(days: number): string {
  if (days <= 0) return "l'historique disponible";
  const months = Math.round(days / 21);
  if (months < 24) return `${months} mois`;
  return `${Math.round(months / 12)} ans`;
}
