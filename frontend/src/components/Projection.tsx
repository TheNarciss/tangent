import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  useBrokers,
  useProjection,
  useWithdrawalRate,
  type ProjectionResponse,
} from "@/api";
import { LOCALE_TAGS, getLocale, t, tn, useT } from "@/i18n";
import { useDebouncedValue } from "@/lib/hooks";
import { fmt } from "@/lib/format";
import { useProfile } from "@/lib/profile";
import { cn } from "@/lib/utils";
import { FanChart } from "@/components/ProjectionChart";
import { NAV_PATHS } from "@/components/Sidebar";
import { VerdictLine } from "@/components/ui/verdict-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Fallback while GET /withdrawal-rate loads; the backend value wins (config/verdicts.yaml). */
const WITHDRAWAL_RATE_FALLBACK = 0.035;
const MONTHLY_MAX = 2000;

/** « 200 € » / « €200 » — the input's whole euros without the empty cents, decimals kept. */
function wholeEur(v: number): string {
  return fmt.eur(v).replace(/[.,]00(?=\D*$)/, "");
}

/** 0.035 → « 3,5 % » / « 3.5% » : the withdrawal rate, one decimal. */
function pct1(v: number): string {
  return new Intl.NumberFormat(LOCALE_TAGS[getLocale()], {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(v);
}

/**
 * Projection — one question (« si je continue à verser X € par mois, j'aurai
 * combien dans N ans ? »), pre-filled from the profile, answered with three
 * rounded figures, a chart and a « et si… » slider on the only real lever.
 * The maths (Monte-Carlo, quantiles, fee model) sit behind « Comment c'est calculé ? ».
 */
export function Projection() {
  const { t, tn } = useT();
  const [profile, setProfile] = useProfile();
  const [monthly, setMonthly] = useState(profile?.monthly_dca ?? 200);
  const [years, setYears] = useState(profile?.horizon_years ?? 10);
  const [goalMode, setGoalMode] = useState<"capital" | "income">("capital");
  const [goalCapital, setGoalCapital] = useState<number | "">(profile?.goal_amount ?? 25000);
  const [income, setIncome] = useState(500);
  const [broker, setBroker] = useState<string | undefined>(undefined);
  const touched = useRef(false);

  // Pre-fill from the profile once it is loaded, unless the user already moved something.
  useEffect(() => {
    if (touched.current || !profile) return;
    setMonthly(profile.monthly_dca);
    setYears(profile.horizon_years);
    if (profile.goal_amount) setGoalCapital(profile.goal_amount);
  }, [profile]);

  const withdrawal = useWithdrawalRate();
  const withdrawalRate = withdrawal.data?.withdrawal_rate ?? WITHDRAWAL_RATE_FALLBACK;
  const goal = goalMode === "income" ? (income * 12) / withdrawalRate : goalCapital || 0;
  const dMonthly = useDebouncedValue(monthly, 350);
  const dYears = useDebouncedValue(years, 350);
  const dGoal = useDebouncedValue(goal, 350);

  // The goal and its date are the profile's: the « épargne pour ton objectif »
  // verdict reads them. The monthly slider stays a « et si… », never saved.
  useEffect(() => {
    if (!profile || !touched.current) return;
    const nextGoal = dGoal > 0 ? Math.round(dGoal) : null;
    if (profile.goal_amount === nextGoal && profile.horizon_years === dYears) return;
    setProfile({ ...profile, goal_amount: nextGoal, horizon_years: dYears });
  }, [dGoal, dYears, profile, setProfile]);

  const brokers = useBrokers();
  const q = useProjection(dMonthly, dYears, dGoal || undefined, broker);
  // Fee comparison: same projection at another broker (the YAML default, else the next one).
  const otherBroker = useMemo(() => {
    const list = brokers.data?.brokers ?? [];
    const current = q.data?.broker_id;
    const preferred = brokers.data?.default;
    if (preferred && preferred !== current) return preferred;
    return list.find((b) => b.id !== current)?.id;
  }, [brokers.data, q.data?.broker_id]);
  const alt = useProjection(dMonthly, dYears, undefined, otherBroker, { enabled: !!otherBroker });

  const onMonthly = (v: number) => {
    touched.current = true;
    setMonthly(v);
  };
  const onYears = (v: number) => {
    touched.current = true;
    setYears(v);
  };

  return (
    <div className="space-y-6">
      <VerdictLine id="savings_rate" to={NAV_PATHS.method} />
      <VerdictLine id="goal" to={NAV_PATHS.method} />
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <h2 className="text-base font-semibold">
          {t("planning.question.before")}
          <span className="font-mono tabular">{wholeEur(monthly)}</span>
          {tn("planning.question.after", years)}
        </h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="monthly" className="text-xs text-muted-foreground">
              {t("planning.monthly.label")}
            </Label>
            <div className="flex items-center gap-3">
              <input
                id="monthly"
                type="range"
                min={0}
                max={MONTHLY_MAX}
                step={25}
                value={Math.min(monthly, MONTHLY_MAX)}
                onChange={(e) => onMonthly(Number(e.target.value))}
                className="h-2 flex-1 cursor-pointer accent-primary"
                aria-label={t("planning.monthly.aria")}
              />
              <Input
                type="number"
                min={0}
                step={25}
                value={monthly}
                onChange={(e) => onMonthly(Math.max(0, Number(e.target.value) || 0))}
                className="w-28 font-mono tabular"
              />
            </div>
          </div>
          <NumberField
            label={t("planning.years.label")}
            value={years}
            onChange={(v) => onYears(Math.min(50, Math.max(1, typeof v === "number" ? v : 1)))}
            min={1}
            max={50}
            step={1}
          />
          <BrokerField
            value={broker ?? q.data?.broker_id}
            onChange={setBroker}
            brokers={brokers.data}
          />
          <GoalField
            mode={goalMode}
            onModeChange={(m) => {
              touched.current = true;
              setGoalMode(m);
            }}
            capital={goalCapital}
            onCapitalChange={(v) => {
              touched.current = true;
              setGoalCapital(v);
            }}
            income={income}
            onIncomeChange={(v) => {
              touched.current = true;
              setIncome(v);
            }}
            withdrawalRate={withdrawalRate}
          />
        </div>
      </section>

      {q.isLoading && (
        <div className="space-y-3">
          <div className="h-28 animate-pulse rounded-xl bg-muted/30" />
          <div className="h-72 animate-pulse rounded-xl bg-muted/30" />
        </div>
      )}
      {q.isError && <ErrorState error={q.error} />}
      {q.data && (
        <>
          <Headline data={q.data} years={dYears} goalMode={goalMode} income={income} />
          <section className="rounded-xl border bg-card p-4 md:p-6">
            <FanChart data={q.data} />
          </section>
          <FeesLine data={q.data} alt={alt.data} />
          <HowItWorks data={q.data} />
        </>
      )}
    </div>
  );
}

/* ─── Three figures ─────────────────────────────────────────────────────── */

function Headline({
  data,
  years,
  goalMode,
  income,
}: {
  data: ProjectionResponse;
  years: number;
  goalMode: "capital" | "income";
  income: number;
}) {
  const last = data.months.length - 1;
  const median = data.bands.p50[last];
  const lo = data.bands.p10[last];
  const hi = data.bands.p90[last];
  const invested = data.invested[last];
  const reachedIdx = data.goal_prob_by_month?.findIndex((p) => p >= 0.5) ?? -1;
  const reachedYear =
    reachedIdx >= 0 ? new Date().getFullYear() + Math.round(data.months[reachedIdx] / 12) : null;
  const chances = data.goal_prob_at_end !== null ? Math.round(data.goal_prob_at_end * 10) : null;
  const hasGoal = data.goal !== null && data.goal > 0 && chances !== null;
  const { t, tn } = useT();

  return (
    <section
      className={cn("grid gap-3", hasGoal ? "sm:grid-cols-2 xl:grid-cols-4" : "sm:grid-cols-3")}
    >
      <Figure
        label={tn("planning.figure.inYears", years)}
        value={fmt.approxEur(median)}
        sub={t("planning.figure.range", { lo: fmt.kEur(lo), hi: fmt.kEur(hi) })}
      />
      <Figure
        label={t("planning.figure.invested")}
        value={fmt.approxEur(invested)}
        sub={t("planning.figure.investedSub")}
      />
      {hasGoal ? (
        <>
          <Figure
            label={
              goalMode === "income"
                ? t("planning.figure.forIncome", { income: wholeEur(income) })
                : t("planning.figure.goalAmount", { amount: fmt.approxEur(data.goal!) })
            }
            value={
              reachedYear !== null
                ? t("planning.figure.around", { year: reachedYear })
                : t("planning.figure.notInHorizon")
            }
            sub={
              reachedYear !== null
                ? tn("planning.figure.chancesAtEnd", chances!)
                : tn("planning.figure.chancesIn", chances!, { years })
            }
          />
          <Figure
            label={
              data.target_probability
                ? t("planning.figure.forChances", {
                    chances: chancesLabel(data.target_probability),
                  })
                : t("planning.figure.required")
            }
            value={
              data.required_monthly !== null
                ? t("planning.figure.perMonth", { amount: fmt.approxEur(data.required_monthly) })
                : t("planning.figure.outOfReach")
            }
            sub={
              data.required_monthly !== null
                ? t("planning.figure.requiredSub")
                : t("planning.figure.outOfReachSub")
            }
          />
        </>
      ) : (
        <Figure
          label={t("planning.figure.goal")}
          value={t("common.none")}
          sub={t("planning.figure.noGoalSub")}
        />
      )}
    </section>
  );
}

/** 0.75 → « 3 chances sur 4 » : the wording the Méthode tab uses too. */
function chancesLabel(p: number): string {
  for (const d of [2, 3, 4, 5, 10]) {
    const n = p * d;
    if (Math.abs(n - Math.round(n)) < 1e-9) {
      return tn("planning.chances.of", Math.round(n), { d });
    }
  }
  return t("planning.chances.pct", { pct: fmt.pct0(p) });
}

function Figure({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold tabular">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
    </div>
  );
}

/* ─── Fees ──────────────────────────────────────────────────────────────── */

function FeesLine({
  data,
  alt,
}: {
  data: ProjectionResponse;
  alt: ProjectionResponse | undefined;
}) {
  const last = data.months.length - 1;
  const fees = data.cumulative_fees[last];
  const altFees = alt ? alt.cumulative_fees[alt.months.length - 1] : null;
  const { t } = useT();
  return (
    <section className="rounded-xl border bg-card p-4 text-sm md:p-6">
      <p>
        {t("planning.fees.at")}
        <strong>{data.broker}</strong>
        {t("planning.fees.costAbout")}
        <strong className="font-mono tabular">{fmt.approxEur(fees)}</strong>
        {t("planning.fees.overPeriod")}
        {alt && altFees !== null && alt.broker !== data.broker && (
          <>
            {t("planning.fees.altAt")}
            <strong>{alt.broker}</strong>
            {t("planning.fees.altAbout")}
            <strong className="font-mono tabular">{fmt.approxEur(altFees)}</strong>
          </>
        )}
        .
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {t("planning.fees.note")}
        {data.weighted_ter ? t("planning.fees.noteTer", { ter: fmt.pct(data.weighted_ter) }) : ""}.
      </p>
      {data.multi_broker_warning && (
        <p className="mt-2 text-xs text-muted-foreground">{data.multi_broker_warning}</p>
      )}
    </section>
  );
}

/* ─── Inputs ────────────────────────────────────────────────────────────── */

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  allowEmpty,
}: {
  label: string;
  value: number | "";
  onChange: (v: number | "") => void;
  min?: number;
  max?: number;
  step?: number;
  allowEmpty?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "" && allowEmpty) return onChange("");
          const n = Number(raw);
          if (!isNaN(n)) onChange(n);
        }}
        className="font-mono tabular"
      />
    </div>
  );
}

function BrokerField({
  value,
  onChange,
  brokers,
}: {
  value: string | undefined;
  onChange: (v: string) => void;
  brokers: { default: string; brokers: { id: string; name: string }[] } | undefined;
}) {
  const { t } = useT();
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{t("planning.broker.label")}</Label>
      <Select value={value} onValueChange={onChange} disabled={!brokers}>
        <SelectTrigger>
          <SelectValue placeholder={t("common.loading")} />
        </SelectTrigger>
        <SelectContent>
          {brokers?.brokers.map((b) => (
            <SelectItem key={b.id} value={b.id}>
              {b.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function GoalField({
  mode,
  onModeChange,
  capital,
  onCapitalChange,
  income,
  onIncomeChange,
  withdrawalRate,
}: {
  mode: "capital" | "income";
  onModeChange: (m: "capital" | "income") => void;
  capital: number | "";
  onCapitalChange: (v: number | "") => void;
  income: number;
  onIncomeChange: (v: number) => void;
  withdrawalRate: number;
}) {
  const { t } = useT();
  return (
    <div className="space-y-1.5 sm:col-span-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Label className="text-xs text-muted-foreground">{t("planning.goal.label")}</Label>
        <div className="flex gap-1 text-xs">
          <ModeButton active={mode === "capital"} onClick={() => onModeChange("capital")}>
            {t("planning.goal.modeCapital")}
          </ModeButton>
          <ModeButton active={mode === "income"} onClick={() => onModeChange("income")}>
            {t("planning.goal.modeIncome")}
          </ModeButton>
        </div>
      </div>
      {mode === "capital" ? (
        <Input
          type="number"
          min={0}
          step={5000}
          value={capital}
          onChange={(e) => onCapitalChange(e.target.value === "" ? "" : Number(e.target.value))}
          placeholder={t("planning.goal.capitalPlaceholder")}
          className="font-mono tabular sm:max-w-xs"
        />
      ) : (
        <div className="space-y-1">
          <Input
            type="number"
            min={0}
            step={50}
            value={income}
            onChange={(e) => onIncomeChange(Math.max(0, Number(e.target.value) || 0))}
            className="font-mono tabular sm:max-w-xs"
          />
          <p className="text-[11px] text-muted-foreground">
            {t("planning.goal.incomeNote", {
              capital: fmt.approxEur((income * 12) / withdrawalRate),
              income: wholeEur(income),
              rate: pct1(withdrawalRate),
            })}
          </p>
        </div>
      )}
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-0.5",
        active ? "bg-accent font-medium text-accent-foreground" : "text-muted-foreground",
      )}
    >
      {children}
    </button>
  );
}

function ErrorState({ error }: { error: unknown }) {
  const empty = error instanceof ApiError && error.type === "portfolio_empty";
  const { t } = useT();
  return (
    <div className="rounded-xl border border-dashed p-8 text-center">
      <p className="text-sm font-medium">
        {empty ? t("planning.error.emptyTitle") : t("planning.error.title")}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        {empty
          ? t("planning.error.emptyBody")
          : error instanceof Error
            ? error.message
            : t("planning.error.retry")}
      </p>
    </div>
  );
}

/* ─── « Comment c'est calculé ? » ───────────────────────────────────────── */

function HowItWorks({ data }: { data: ProjectionResponse }) {
  const years = Math.round(data.months[data.months.length - 1] / 12);
  const last = data.months.length - 1;
  const { t } = useT();
  return (
    <details className="rounded-xl border bg-muted/20 text-sm">
      <summary className="cursor-pointer select-none px-4 py-3 font-medium">
        {t("planning.how.title")}
      </summary>
      <div className="space-y-2 border-t px-4 py-3 text-muted-foreground">
        <p>
          {t("planning.how.returns", {
            ret: fmt.pct(data.annual_return),
            vol: fmt.pct(data.annual_vol),
          })}
        </p>
        <p>{t("planning.how.monteCarlo")}</p>
        <p>
          {t("planning.how.fees", {
            gross: fmt.approxEur(data.gross_p50[last]),
            net: fmt.approxEur(data.bands.p50[last]),
          })}
        </p>
        <p>
          {t("planning.how.inflation", {
            inflation: fmt.pct(data.inflation),
            median: fmt.approxEur(data.bands.p50[last]),
            years,
          })}
        </p>
        <p>
          {t("planning.how.tax", {
            rate: fmt.pct(data.tax_on_gains_pct),
            afterTax: fmt.approxEur(data.median_after_tax ?? 0),
          })}
        </p>
      </div>
    </details>
  );
}
