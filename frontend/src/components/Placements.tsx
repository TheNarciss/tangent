import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import {
  ApiError,
  useDashboard,
  useOptimizer,
  useRiskLevels,
  useWealthSummary,
  type AssetMetrics,
  type Insight,
  type OptimizerRequest,
  type OptimizerResponse,
  type PortfolioMetrics,
  type RiskLevel,
  type Severity,
  type StressTestResult,
} from "@/api";
import { fmt } from "@/lib/format";
import { ageFromBirthDate, ceilingsFromEnvelopes, useProfile } from "@/lib/profile";
import { useSettings } from "@/lib/settings";
import { cn } from "@/lib/utils";
import { PlacementsAdvanced } from "@/components/PlacementsAdvanced";

const COLORS = ["#60a5fa", "#f97316", "#a78bfa", "#22d3ee", "#facc15", "#f472b6", "#10b981"];
/** A proposed move is worth showing above this weight or amount (cf. état des lieux §5.3). */
const MATERIAL_WEIGHT = 0.05;
const MATERIAL_EUR = 500;

/**
 * « Mes placements » in three questions, two phone screens:
 *   1. Qu'est-ce que j'ai et ça donne quoi ?
 *   2. Est-ce que je prends trop de risque ?
 *   3. Est-ce que je peux faire mieux ?
 * Everything else (μ/σ, scatter, matrix, full optimizer, scanner) is folded
 * under « Mode avancé ».
 */
export function Placements() {
  const [settings] = useSettings();
  const dashboard = useDashboard(settings.expert);
  const [profile] = useProfile();
  const wealth = useWealthSummary();
  const riskLevels = useRiskLevels();

  const age = profile ? ageFromBirthDate(profile.birth_date) : null;
  const hasProfile = !!profile && age !== null && profile.fiscal_shares > 0;
  const profileMaxVol = hasProfile && profile ? profile.max_annual_volatility : 10;
  const ceilingsUsed = ceilingsFromEnvelopes(wealth.data?.envelopes) ?? profile?.ceilings_used;

  // One proposal, under the profile's constraints — never « max Sharpe » by default.
  const req: OptimizerRequest = {
    objective: hasProfile ? "from_strategy" : "target_volatility",
    max_volatility: profileMaxVol / 100,
    ...(hasProfile && profile
      ? {
          target_return: profile.target_annual_return / 100,
          include_envelopes: true,
          age: age!,
          rfr: profile.rfr_n_minus_2,
          fiscal_shares: profile.fiscal_shares,
          ceilings_used: ceilingsUsed,
        }
      : {}),
    expert: settings.expert,
  };
  const proposal = useOptimizer(req);

  if (dashboard.isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-xl bg-muted/30" />
        ))}
      </div>
    );
  }
  if (dashboard.isError || !dashboard.data) {
    const err = dashboard.error;
    const empty = err instanceof ApiError && err.type === "portfolio_empty";
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <p className="text-sm font-medium">
          {empty ? "Pas encore de placements" : "Analyse indisponible pour l'instant"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {empty
            ? "Connecte un compte-titres, un PEA ou une assurance vie pour voir cette page."
            : err instanceof Error
              ? err.message
              : "Réessaie dans un instant."}
        </p>
      </div>
    );
  }

  const m = dashboard.data.metrics;
  return (
    <div className="space-y-6">
      <WhatIHave metrics={m} />
      <RiskBlock
        metrics={m}
        stress={dashboard.data.stress_tests}
        levels={riskLevels.data}
        profileLevel={hasProfile && profile ? profile.risk_level : null}
      />
      <BetterBlock
        insights={dashboard.data.insights}
        proposal={proposal.data}
        error={proposal.error}
        loading={proposal.isLoading}
        hasProfile={hasProfile}
      />
      <PlacementsAdvanced dashboard={dashboard.data} />
    </div>
  );
}

/* ── 1. Qu'est-ce que j'ai ? ──────────────────────────────────────────── */

function WhatIHave({ metrics }: { metrics: PortfolioMetrics }) {
  const assets = [...metrics.assets].sort((a, b) => b.weight - a.weight);
  const gain = metrics.total_pnl;
  return (
    <Block title="Ce que j'ai">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-mono text-3xl font-semibold tabular">
          {fmt.eur(metrics.total_value)}
        </span>
        <span
          className={cn(
            "font-mono text-sm tabular",
            gain >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
          )}
        >
          {fmt.signedEur(gain)} depuis l'achat ({fmt.signedPct(metrics.total_pnl_pct)})
        </span>
      </div>

      {/* One allocation bar */}
      <div className="mt-4 flex h-3 w-full overflow-hidden rounded-full bg-muted/30">
        {assets.map((a, i) => (
          <div
            key={a.ticker}
            style={{ width: `${a.weight * 100}%`, background: COLORS[i % COLORS.length] }}
            title={`${name(a)} · ${fmt.pct(a.weight)}`}
          />
        ))}
      </div>

      <ul className="mt-3 divide-y rounded-md border text-sm">
        {assets.map((a, i) => (
          <li key={a.ticker} className="flex items-center gap-3 px-3 py-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: COLORS[i % COLORS.length] }}
            />
            <div className="min-w-0 flex-1">
              <div className="truncate">{name(a)}</div>
              <div className="text-xs text-muted-foreground">
                {fmt.pct(a.weight)} de tes placements
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className="font-mono tabular">{fmt.eur(a.value)}</div>
              <div
                className={cn(
                  "font-mono text-xs tabular",
                  a.pnl >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                )}
              >
                {fmt.signedEur(a.pnl)}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Block>
  );
}

/* ── 2. Est-ce que je prends trop de risque ? ─────────────────────────── */

function RiskBlock({
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

  return (
    <Block title="Est-ce que je prends trop de risque ?">
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

      <ul className="mt-3 space-y-2 text-sm">
        {stress.map((s) => {
          const loss = s.pnl_pct * metrics.total_value;
          return (
            <li key={s.id} className="rounded-md border px-3 py-2">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span>{s.label}</span>
                <span
                  className={cn(
                    "font-mono tabular",
                    loss < 0 ? "text-[hsl(var(--loss))]" : "text-[hsl(var(--gain))]",
                  )}
                >
                  {fmt.eur(Math.abs(loss))}{" "}
                  <span className="text-xs text-muted-foreground">
                    ({fmt.signedPct(s.pnl_pct)})
                  </span>
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                avec tes placements d'aujourd'hui, tu aurais {loss < 0 ? "perdu" : "gagné"} cette
                somme
              </div>
            </li>
          );
        })}
        <li className="rounded-md border px-3 py-2">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3">
            <span>Pire baisse vécue par ce panier</span>
            <span className="font-mono tabular text-[hsl(var(--loss))]">
              {fmt.signedPct(metrics.max_drawdown_observed)}
            </span>
          </div>
          <div className="text-xs text-muted-foreground">
            du plus-haut au creux suivant, sur l'historique
          </div>
        </li>
      </ul>
    </Block>
  );
}

/* ── 3. Est-ce que je peux faire mieux ? ──────────────────────────────── */

const SEVERITY: Record<Severity, { icon: typeof CheckCircle2; color: string }> = {
  good: { icon: CheckCircle2, color: "text-[hsl(var(--gain))]" },
  warning: { icon: AlertTriangle, color: "text-amber-500" },
  critical: { icon: XCircle, color: "text-[hsl(var(--loss))]" },
};

function BetterBlock({
  insights,
  proposal,
  error,
  loading,
  hasProfile,
}: {
  insights: Insight[];
  proposal: OptimizerResponse | undefined;
  error: unknown;
  loading: boolean;
  hasProfile: boolean;
}) {
  return (
    <Block title="Est-ce que je peux faire mieux ?">
      {insights.length === 0 ? (
        <p className="text-sm text-muted-foreground">Rien à signaler sur ta répartition.</p>
      ) : (
        <ul className="space-y-3">
          {insights.map((i, idx) => {
            const { icon: Icon, color } = SEVERITY[i.severity];
            return (
              <li key={idx} className="flex gap-3">
                <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", color)} />
                <div>
                  <p className="text-sm font-medium leading-tight">{i.title}</p>
                  <p className="text-sm leading-snug text-muted-foreground">{i.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-4 border-t pt-4">
        <h3 className="text-sm font-medium">Une piste{hasProfile ? ", selon ton profil" : ""}</h3>
        {loading && <p className="mt-1 text-sm text-muted-foreground">Calcul…</p>}
        {error ? <ProposalError error={error} /> : null}
        {proposal && <Proposal data={proposal} />}
        {!hasProfile && (
          <p className="mt-2 text-xs text-muted-foreground">
            Renseigne ton profil pour une piste adaptée à ton curseur prudent ↔ dynamique.
          </p>
        )}
      </div>
    </Block>
  );
}

function ProposalError({ error }: { error: unknown }) {
  const infeasible = error instanceof ApiError && /infeasible|impossible/i.test(error.message);
  return (
    <p className="mt-1 text-sm text-muted-foreground">
      {infeasible
        ? "Avec tes lignes actuelles, le rendement visé n'est pas atteignable au niveau de risque de ton curseur. Piste : accepter un peu plus de variations, ou viser moins haut."
        : "La piste n'a pas pu être calculée pour l'instant."}
    </p>
  );
}

function Proposal({ data }: { data: OptimizerResponse }) {
  const moves = data.actions
    .map((a, i) => ({ ...a, label: data.asset_labels[i], kind: data.asset_kinds[i] }))
    .filter(
      (a) => Math.abs(a.delta_weight) >= MATERIAL_WEIGHT || Math.abs(a.delta_value) >= MATERIAL_EUR,
    )
    .sort((a, b) => Math.abs(b.delta_value) - Math.abs(a.delta_value));

  if (moves.length === 0) {
    return (
      <p className="mt-1 text-sm text-muted-foreground">
        Rien à changer : ta répartition colle déjà à ton profil.
      </p>
    );
  }
  return (
    <div className="mt-2 space-y-2">
      <ul className="divide-y rounded-md border text-sm">
        {moves.map((a) => {
          const buy = a.delta_value > 0;
          return (
            <li key={a.ticker} className="flex items-center justify-between gap-3 px-3 py-2">
              <span className="min-w-0 truncate">
                {a.kind === "envelope" ? "Placer sur" : buy ? "Renforcer" : "Alléger"}{" "}
                <strong>{a.label}</strong>
              </span>
              <span
                className={cn(
                  "shrink-0 font-mono tabular",
                  buy ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                )}
              >
                {buy ? "+" : "−"}
                {fmt.eur(Math.abs(a.delta_value))}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-muted-foreground">
        Ce n'est qu'une piste : avant de vendre, compte les frais de courtage et l'impôt sur la
        plus-value. Le plus simple est souvent d'orienter tes prochains versements.
      </p>
    </div>
  );
}

/* ── Atoms ─────────────────────────────────────────────────────────────── */

function name(a: AssetMetrics): string {
  return a.label ?? a.ticker;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <h2 className="mb-3 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}
