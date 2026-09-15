import { Link } from "react-router-dom";

import {
  useVerdicts,
  type DiversificationVerdictDetails,
  type DrawdownVerdictDetails,
  type FeesVerdictDetails,
  type GoalVerdictDetails,
  type PerformanceVerdictDetails,
  type NextEuroVerdictDetails,
  type RiskShareVerdictDetails,
  type SavingsRateVerdictDetails,
  type Verdict,
} from "@/api";
import { LOCALE_TAGS, getLocale, useT } from "@/i18n";
import { formatDate } from "@/lib/accounts";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NAV_PATHS } from "@/components/Sidebar";
import { VerdictCard, VerdictDot } from "@/components/ui/verdict-card";
import { Proposal } from "@/components/methode/Proposal";
import { StressList } from "@/components/methode/StressList";

/** Short numeric date, « 03/03/2026 » — the shape a bare toLocaleDateString gave, in the language in effect. */
function numericDate(iso: string): string {
  return formatDate(iso, { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** One decimal in the language in effect: « 3,2 » or « 3.2 ». */
function dec1(v: number): string {
  return new Intl.NumberFormat(LOCALE_TAGS[getLocale()], {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(v);
}

/**
 * « Méthode » : every verdict of the method as a folded card (ADR-023).
 * A card shows a traffic light, one sentence, an amount and an action; the
 * computation behind it only appears on tap, so the page stays readable on
 * a phone and the detail exists for whoever wants it.
 */
export function Methode() {
  const { t } = useT();
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
        <p className="text-sm font-medium">{t("method.unavailable")}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {q.error instanceof Error ? q.error.message : t("method.retry")}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <p className="text-sm text-muted-foreground">{t("method.intro")}</p>
      {q.data.verdicts.map((v) => (
        <VerdictCard key={v.id} verdict={v}>
          {v.id === "fees" ? (
            <FeesDetails details={v.details as FeesVerdictDetails} />
          ) : v.id === "next_euro" ? (
            <NextEuroDetails details={v.details as NextEuroVerdictDetails} />
          ) : v.id === "risk_share" ? (
            <div className="space-y-4">
              <RiskShareDetails details={v.details as RiskShareVerdictDetails} />
              {v.status !== "green" && <Proposal />}
            </div>
          ) : v.id === "savings_rate" ? (
            <SavingsRateDetails details={v.details as SavingsRateVerdictDetails} />
          ) : v.id === "goal" ? (
            <GoalDetails details={v.details as GoalVerdictDetails} />
          ) : v.id === "performance" ? (
            <PerformanceDetails details={v.details as PerformanceVerdictDetails} />
          ) : v.id === "drawdown" ? (
            <div className="space-y-4">
              <DrawdownDetails details={v.details as DrawdownVerdictDetails} />
              <StressList />
            </div>
          ) : v.id === "diversification" ? (
            <DiversificationDetails details={v.details as DiversificationVerdictDetails} />
          ) : (
            <GenericDetails verdict={v} />
          )}
        </VerdictCard>
      ))}
    </div>
  );
}

/* ── Répartition ───────────────────────────────────────────────────────── */

function DiversificationDetails({ details: d }: { details: DiversificationVerdictDetails }) {
  const { t } = useT();
  const lines = d.lines ?? [];
  const duplicates = d.duplicates ?? [];
  const concentrated = d.concentrated ?? [];
  const unrecognised = d.unrecognised ?? [];

  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-md border text-sm">
        {lines.map((l) => (
          <li key={l.label} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="truncate">{l.label}</div>
              <div className="truncate text-xs text-muted-foreground">
                {l.index_label ?? t("method.div.unrecognisedClass")}
                {!l.diversified && l.index_label ? t("method.div.singleSegment") : ""}
              </div>
            </div>
            <span className="shrink-0 font-mono tabular">{fmt.pct(l.weight)}</span>
          </li>
        ))}
      </ul>

      {duplicates.map((g) => (
        <p key={g.index_label} className="text-xs text-muted-foreground">
          <strong className="text-foreground">{g.labels.join(", ")}</strong>
          {t("method.div.duplicatesAfter", { index: g.index_label, weight: fmt.pct(g.weight) })}
        </p>
      ))}

      {concentrated.map((c) => (
        <p key={c.label} className="text-xs text-muted-foreground">
          <strong className="text-foreground">{c.label}</strong>
          {t("method.div.concentratedAfter", {
            weight: fmt.pct(c.weight),
            reason:
              c.kind === "stock"
                ? t("method.div.singleCompany")
                : t("method.div.singleMarketSegment"),
          })}
        </p>
      ))}

      {unrecognised.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t("method.div.unrecognised", { labels: unrecognised.join(", ") })}
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        {t("method.div.note", { max: fmt.pct(d.single_line_max ?? 0.4) })}
      </p>
    </div>
  );
}

/* ── Ce que tes placements ont vraiment rapporté ───────────────────────── */

function PerformanceDetails({ details: d }: { details: PerformanceVerdictDetails }) {
  const { t, tn } = useT();
  if (d.twr === undefined || d.twr === null) {
    return (
      <p className="text-xs text-muted-foreground">
        {t("method.perf.noData")}
        {d.min_days ? ` ${tn("method.perf.minDays", d.min_days)}` : ""}
      </p>
    );
  }
  const signed = (v: number) => `${v >= 0 ? "+" : ""}${fmt.pct(v)}`;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label={t("method.perf.twr")}
          value={signed(d.twr_annualized ?? d.twr)}
          sub={
            d.twr_annualized !== null && d.twr_annualized !== undefined
              ? t("method.perf.twrAnnual")
              : t("method.perf.twrTotal")
          }
        />
        <Figure
          label={t("method.perf.irr")}
          value={d.irr !== null && d.irr !== undefined ? signed(d.irr) : "—"}
          sub={
            d.irr !== null && d.irr !== undefined
              ? t("method.perf.irrSub")
              : t("method.perf.irrMissing")
          }
        />
        <Figure
          label={t("method.perf.gap")}
          value={
            d.behaviour_gap !== null && d.behaviour_gap !== undefined
              ? signed(d.behaviour_gap)
              : "—"
          }
          sub={t("method.perf.gapSub")}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {t("method.perf.history", {
          start: d.start ? numericDate(d.start) : "?",
          end: d.end ? numericDate(d.end) : "?",
          days: tn("method.perf.days", d.days ?? 0),
          first: fmt.eur0(d.first_value_eur ?? 0),
          flows: fmt.eur0(d.net_flows_eur ?? 0),
          last: fmt.eur0(d.last_value_eur ?? 0),
        })}
      </p>
    </div>
  );
}

/* ── Baisse depuis le plus haut ────────────────────────────────────────── */

function DrawdownDetails({ details: d }: { details: DrawdownVerdictDetails }) {
  const { t } = useT();
  if (d.drawdown === undefined) return null;
  const dd = Math.abs(d.drawdown);
  const max = Math.abs(d.max_drawdown ?? 0);
  const scale = Math.max(0.25, max * 1.2, dd * 1.2);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label={t("method.dd.below")}
          value={`−${fmt.pct(dd)}`}
          sub={
            d.peak_day
              ? t("method.dd.peakOn", { date: numericDate(d.peak_day) })
              : t("method.dd.sinceStart")
          }
        />
        <Figure
          label={t("method.dd.inEuros")}
          value={`−${fmt.eur0(d.missing_eur ?? 0)}`}
          sub={t("method.dd.inEurosSub")}
        />
        <Figure
          label={t("method.dd.worst")}
          value={`−${fmt.pct(max)}`}
          sub={t("method.dd.worstSub")}
        />
      </div>
      {d.worst_year_ever && (
        <p className="text-xs text-muted-foreground">
          {t("method.dd.contextBefore", {
            years: d.worst_year_ever.to_year - d.worst_year_ever.from_year,
            from: d.worst_year_ever.from_year,
            to: d.worst_year_ever.to_year,
          })}
          <strong className="text-foreground">{fmt.pct(Math.abs(d.worst_year_ever.return))}</strong>
          {t("method.dd.contextAfter")}
        </p>
      )}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${Math.min(100, (dd / scale) * 100)}%` }}
          />
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground/60"
            style={{ left: `calc(${Math.min(100, ((d.alert_step ?? 0.1) / scale) * 100)}% - 1px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{t("method.dd.atPeak")}</span>
          <span>{t("method.dd.alertStep", { pct: fmt.pct(d.alert_step ?? 0.1) })}</span>
          <span>−{fmt.pct(scale)}</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{t("method.dd.note")}</p>
    </div>
  );
}

/* ── Épargne pour ton objectif ─────────────────────────────────────────── */

function GoalDetails({ details: d }: { details: GoalVerdictDetails }) {
  const { t } = useT();
  if (d.probability === undefined || d.goal_eur === undefined) return null;
  const p = d.probability;
  const target = d.target_probability ?? 0.75;
  const amber = d.amber_probability ?? 0.5;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label={t("method.goal.target")}
          value={fmt.eur0(d.goal_eur)}
          sub={t("method.goal.targetSub", { years: d.horizon_years ?? 10 })}
        />
        <Figure
          label={t("method.goal.start")}
          value={fmt.eur0(d.initial_eur ?? 0)}
          sub={t("method.goal.startSub", {
            monthly: fmt.eur0(d.monthly_used_eur ?? 0),
            source:
              d.monthly_source === "observed"
                ? t("method.goal.observed")
                : t("method.goal.declared"),
          })}
        />
        <Figure
          label={t("method.goal.required")}
          value={t("method.goal.perMonth", { amount: fmt.eur0(d.required_monthly_eur ?? 0) })}
          sub={
            d.extra_monthly_eur && d.extra_monthly_eur > 0
              ? t("method.goal.extra", { amount: fmt.eur0(d.extra_monthly_eur) })
              : t("method.goal.already")
          }
        />
      </div>

      {/* Probability gauge with the two thresholds. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${amber * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-amber-500/25"
            style={{ left: `${amber * 100}%`, width: `${(target - amber) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${target * 100}%`, right: 0 }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${p * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{t("method.gauge.zero")}</span>
          <span>{t("method.goal.gauge", { p: fmt.pct0(p), target: fmt.pct0(target) })}</span>
          <span>{t("method.gauge.full")}</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {t("method.goal.simulation", {
          years: d.horizon_years ?? 10,
          p10: fmt.eur0(d.p10_eur ?? 0),
          p50: fmt.eur0(d.p50_eur ?? 0),
          p90: fmt.eur0(d.p90_eur ?? 0),
          paths: d.n_paths ?? 2000,
          equity: fmt.pct0(d.equity_share ?? 0),
          mu: fmt.pct(d.mu_real ?? 0),
          inflation: fmt.pct0(d.inflation ?? 0.02),
          sigma: fmt.pct0(d.sigma ?? 0),
        })}
      </p>
    </div>
  );
}

/* ── Taux d'épargne ────────────────────────────────────────────────────── */

function SavingsRateDetails({ details: d }: { details: SavingsRateVerdictDetails }) {
  const { t } = useT();
  if (d.rate === undefined || d.income_monthly_eur === undefined) return null;
  const rate = d.rate;
  const target = d.target_rate ?? 0.15;
  const amber = d.amber_min ?? 0.05;
  const scale = Math.max(0.3, target * 2, rate * 1.1);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label={t("method.sr.saved")}
          value={fmt.eur0(d.monthly_saved_used_eur ?? 0)}
          sub={
            d.source === "observed" ? t("method.sr.savedObserved") : t("method.sr.savedDeclared")
          }
        />
        <Figure
          label={t("method.sr.income")}
          value={fmt.eur0(d.income_monthly_eur)}
          sub={t("method.sr.incomeSub", { rfr: fmt.eur0(d.rfr_eur ?? 0) })}
        />
        <Figure
          label={t("method.sr.target")}
          value={fmt.eur0(d.target_monthly_eur ?? 0)}
          sub={t("method.sr.targetSub", { pct: fmt.pct0(target) })}
        />
      </div>

      {/* Gauge: 0 → scale, red under amber_min, amber under target, green above. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${(amber / scale) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-amber-500/25"
            style={{
              left: `${(amber / scale) * 100}%`,
              width: `${((target - amber) / scale) * 100}%`,
            }}
          />
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${(target / scale) * 100}%`, right: 0 }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${Math.min(1, rate / scale) * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{t("method.gauge.zero")}</span>
          <span>{t("method.sr.gauge", { rate: fmt.pct0(rate), target: fmt.pct0(target) })}</span>
          <span>{fmt.pct0(scale)}</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {d.missing_monthly_eur && d.missing_monthly_eur > 0
          ? `${t("method.sr.missing", {
              missing: fmt.eur0(d.missing_monthly_eur),
              gap: fmt.eur0(d.gap_at_horizon_eur ?? 0),
              years: d.horizon_years ?? 20,
              growth: fmt.pct0(d.growth_for_horizon ?? 0.05),
            })} `
          : ""}
        {t("method.sr.note", {
          escalation: fmt.pct0(d.escalation ?? 0.05),
          next: fmt.eur0(d.escalated_next_year_eur ?? 0),
        })}
      </p>
    </div>
  );
}

/* ── Où placer le prochain euro ────────────────────────────────────────── */

function NextEuroDetails({ details: d }: { details: NextEuroVerdictDetails }) {
  const { t, tn } = useT();
  const steps = d.steps ?? [];
  const p = d.precaution;
  if (steps.length === 0) return null;
  return (
    <div className="space-y-4">
      {p && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Figure
            label={t("method.next.liquid")}
            value={fmt.eur0(p.liquid_eur)}
            sub={
              p.months_covered !== null
                ? tn("method.next.monthsOfSpending", p.months_covered, {
                    count: dec1(p.months_covered),
                  })
                : t("method.next.unknownSpending")
            }
          />
          <Figure
            label={t("method.next.precautionTarget")}
            value={p.target_eur !== null ? fmt.eur0(p.target_eur) : "—"}
            sub={tn("method.next.monthsOfSpending", p.target_months)}
          />
          <Figure
            label={t("method.next.spending")}
            value={p.monthly_spending_eur !== null ? fmt.eur0(p.monthly_spending_eur) : "—"}
            sub={t("method.next.spendingSub")}
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
                    {fmt.eur0(s.impact_eur_per_year)}
                    {t("method.perYearSuffix")}
                  </span>
                )}
              </div>
              <p className="text-muted-foreground">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <p className="text-xs text-muted-foreground">
        {t("method.next.rule")}
        {d.tax?.tmi !== null && d.tax?.tmi !== undefined
          ? ` ${t("method.next.tmi", { tmi: fmt.pct(d.tax.tmi) })}`
          : ""}
      </p>
    </div>
  );
}

/* ── Part d'actions ────────────────────────────────────────────────────── */

function LongRun({ d }: { d: RiskShareVerdictDetails }) {
  const { t } = useT();
  if (!d.long_run) return null;
  return (
    <p className="text-xs text-muted-foreground">
      {t("method.risk.longRunBefore", { from: d.long_run.from_year, to: d.long_run.to_year })}
      <strong className="text-foreground">
        {t("method.risk.longRunEquities", { pct: fmt.pct(d.long_run.equities) })}
      </strong>
      {t("method.risk.longRunAfter", { bonds: fmt.pct(d.long_run.bonds) })}
    </p>
  );
}

function RiskShareDetails({ details: d }: { details: RiskShareVerdictDetails }) {
  const { t } = useT();
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
          label={t("method.risk.share")}
          value={fmt.pct0(actual)}
          sub={t("method.risk.shareSub", {
            equity: fmt.eur0(d.equity_eur ?? 0),
            pocket: fmt.eur0(d.pocket_eur),
          })}
        />
        <Figure
          label={t("method.risk.target")}
          value={fmt.pct0(target)}
          sub={
            d.horizon_cap !== undefined &&
            d.merton_share !== undefined &&
            d.horizon_cap < d.merton_share
              ? t("method.risk.capped", {
                  years: d.horizon_years ?? "?",
                  merton: fmt.pct0(d.merton_share),
                })
              : t("method.risk.profile", {
                  label: d.risk_label ?? "?",
                  years: d.horizon_years ?? 10,
                })
          }
        />
        <Figure
          label={t("method.risk.badYear")}
          value={`−${fmt.eur0(d.bad_year_eur ?? 0)}`}
          sub={t("method.risk.badYearSub")}
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
          <span>{t("method.risk.gaugeLeft")}</span>
          <span>{t("method.risk.band", { lo: fmt.pct0(lo), hi: fmt.pct0(hi) })}</span>
          <span>{t("method.gauge.full")}</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {t("method.risk.note", {
          sigma: fmt.pct(d.equity_sigma ?? 0.15),
          gamma: d.gamma ? dec1(d.gamma) : "?",
        })}
      </p>
      <LongRun d={d} />
    </div>
  );
}

/* ── Frais réels ───────────────────────────────────────────────────────── */

function FeesDetails({ details: d }: { details: FeesVerdictDetails }) {
  const { t } = useT();
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
          label={t("method.fees.funds")}
          value={fmt.eur0(d.fund_fees_eur ?? 0)}
          sub={`${t("method.fees.fundsSub")}${missing.length ? t("method.fees.fundsSubMissing") : ""}`}
        />
        <Figure
          label={t("method.fees.broker")}
          value={d.broker_known === false ? "—" : fmt.eur0(d.broker_fees_eur ?? 0)}
          sub={
            d.broker_known === false
              ? t("method.fees.brokerUnknown")
              : t("method.fees.brokerSub", {
                  broker: d.broker_name ?? t("method.fees.defaultBroker"),
                  monthly: fmt.eur(d.monthly_contribution_eur ?? 0),
                })
          }
        />
        <Figure
          label={t("method.fees.reference")}
          value={fmt.eur0(d.reference_eur ?? 0)}
          sub={t("method.fees.referenceSub", { pct: fmt.pct(d.reference_pct ?? 0) })}
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
                  {t("method.fees.setTer")}
                </Link>
              ) : (
                <>
                  <div className="font-mono tabular">{fmt.eur0(l.fund_fee_eur ?? 0)}</div>
                  <div className="font-mono text-xs tabular text-muted-foreground">
                    {t("method.fees.perYear", { pct: fmt.pct(l.ter) })}
                  </div>
                  {l.ter_source_url && (
                    <a
                      href={l.ter_source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted-foreground underline"
                    >
                      {t("method.fees.source")}
                    </a>
                  )}
                </>
              )}
            </div>
          </li>
        ))}
      </ul>

      {uncovered.length > 0 && <Uncovered accounts={uncovered} />}

      <p className="text-xs text-muted-foreground">
        {t("method.fees.total", {
          total: fmt.eur0(d.total_fees_eur ?? 0),
          pct: fmt.pct(d.total_fees_pct ?? 0),
          positions: fmt.eur0(d.positions_total_eur),
          green: fmt.pct(d.thresholds?.green_max ?? 0),
          amber: fmt.pct(d.thresholds?.amber_max ?? 0),
        })}
      </p>
    </div>
  );
}

function Uncovered({
  accounts,
}: {
  accounts: { name: string; account_type: string; value_eur: number }[];
}) {
  const { t } = useT();
  return (
    <div className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
      {t("method.fees.uncovered", {
        accounts: accounts.map((a) => `${a.name} (${fmt.eur0(a.value_eur)})`).join(", "),
      })}
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
