import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError, useBrokers, useProjection, type ProjectionResponse } from "@/api";
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

/** Bengen rule: a monthly income target becomes a capital goal at 4 %/an. */
const WITHDRAWAL_RATE = 0.04;
const MONTHLY_MAX = 2000;

/**
 * Projection — one question (« si je continue à verser X € par mois, j'aurai
 * combien dans N ans ? »), pre-filled from the profile, answered with three
 * rounded figures, a chart and a « et si… » slider on the only real lever.
 * The maths (Monte-Carlo, quantiles, fee model) sit behind « Comment c'est calculé ? ».
 */
export function Projection() {
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

  const goal = goalMode === "income" ? (income * 12) / WITHDRAWAL_RATE : goalCapital || 0;
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
          Si je continue à verser{" "}
          <span className="font-mono tabular">{fmt.eur(monthly).replace(",00", "")}</span> par mois
          pendant {years} an{years > 1 ? "s" : ""}…
        </h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="monthly" className="text-xs text-muted-foreground">
              Et si je versais… (€ par mois)
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
                aria-label="Versement mensuel"
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
            label="Pendant combien d'années"
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

  return (
    <section className="grid gap-3 sm:grid-cols-3">
      <Figure
        label={`Dans ${years} an${years > 1 ? "s" : ""}, environ`}
        value={fmt.approxEur(median)}
        sub={`entre ${fmt.kEur(lo)} et ${fmt.kEur(hi)}, 8 fois sur 10`}
      />
      <Figure
        label="Capital de départ + versements"
        value={fmt.approxEur(invested)}
        sub="ce que tu auras mis, sans gain ni perte"
      />
      {data.goal !== null && data.goal > 0 && chances !== null ? (
        <Figure
          label={
            goalMode === "income"
              ? `Pour ${fmt.eur(income).replace(",00", "")} par mois à vie`
              : `Objectif ${fmt.approxEur(data.goal)}`
          }
          value={reachedYear !== null ? `vers ${reachedYear}` : "pas dans l'horizon"}
          sub={
            reachedYear !== null
              ? `${chances} chance${chances > 1 ? "s" : ""} sur 10 à la fin`
              : `${chances} chance${chances > 1 ? "s" : ""} sur 10 d'y être dans ${years} ans`
          }
        />
      ) : (
        <Figure
          label="Objectif"
          value="—"
          sub="Indique un objectif pour savoir quand tu l'atteins"
        />
      )}
    </section>
  );
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
  return (
    <section className="rounded-xl border bg-card p-4 text-sm md:p-6">
      <p>
        Chez <strong>{data.broker}</strong>, les frais te coûtent environ{" "}
        <strong className="font-mono tabular">{fmt.approxEur(fees)}</strong> sur la période
        {alt && altFees !== null && alt.broker !== data.broker && (
          <>
            {" "}
            · chez <strong>{alt.broker}</strong>, environ{" "}
            <strong className="font-mono tabular">{fmt.approxEur(altFees)}</strong>
          </>
        )}
        .
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Frais de courtage et de tenue de compte, plus ce qu'ils t'auraient rapporté s'ils étaient
        restés investis
        {data.weighted_ter
          ? `, frais des fonds (${(data.weighted_ter * 100).toFixed(2)} %/an) déjà dans les cours`
          : ""}
        .
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
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">Chez qui tu investis</Label>
      <Select value={value} onValueChange={onChange} disabled={!brokers}>
        <SelectTrigger>
          <SelectValue placeholder="Chargement…" />
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
}: {
  mode: "capital" | "income";
  onModeChange: (m: "capital" | "income") => void;
  capital: number | "";
  onCapitalChange: (v: number | "") => void;
  income: number;
  onIncomeChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5 sm:col-span-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Label className="text-xs text-muted-foreground">Mon objectif (optionnel)</Label>
        <div className="flex gap-1 text-xs">
          <ModeButton active={mode === "capital"} onClick={() => onModeChange("capital")}>
            une somme
          </ModeButton>
          <ModeButton active={mode === "income"} onClick={() => onModeChange("income")}>
            un revenu mensuel à vie
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
          placeholder="ex. 25 000"
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
            Il faut environ {fmt.approxEur((income * 12) / WITHDRAWAL_RATE)} de capital pour en
            retirer {fmt.eur(income).replace(",00", "")} par mois sans l'épuiser (règle des 4 % par
            an).
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
  return (
    <div className="rounded-xl border border-dashed p-8 text-center">
      <p className="text-sm font-medium">
        {empty ? "Pas encore de placements à projeter" : "Projection indisponible"}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        {empty
          ? "Connecte un compte-titres, un PEA ou une assurance vie : la projection part de ce que tu détiens."
          : error instanceof Error
            ? error.message
            : "Réessaie dans un instant."}
      </p>
    </div>
  );
}

/* ─── « Comment c'est calculé ? » ───────────────────────────────────────── */

function HowItWorks({ data }: { data: ProjectionResponse }) {
  const years = Math.round(data.months[data.months.length - 1] / 12);
  const last = data.months.length - 1;
  return (
    <details className="rounded-xl border bg-muted/20 text-sm">
      <summary className="cursor-pointer select-none px-4 py-3 font-medium">
        Comment c'est calculé ?
      </summary>
      <div className="space-y-2 border-t px-4 py-3 text-muted-foreground">
        <p>
          Le rendement et l'amplitude des variations viennent de l'historique de tes fonds sur 5 ans
          : rendement annuel estimé {fmt.pct(data.annual_return)}, variations annuelles de{" "}
          {fmt.pct(data.annual_vol)}.
        </p>
        <p>
          On simule 1 000 trajectoires possibles (Monte-Carlo), en tenant compte de l'incertitude
          sur le rendement estimé lui-même : 5 ans d'historique, c'est peu. « Le plus probable » est
          la médiane ; la « zone probable » va du 10ᵉ au 90ᵉ centile, donc 8 trajectoires sur 10
          finissent dedans.
        </p>
        <p>
          Les frais de courtage et de tenue de compte sont prélevés mois par mois, donc ils se
          cumulent. Sans aucun frais, la médiane serait de {fmt.approxEur(data.gross_p50[last])} au
          lieu de {fmt.approxEur(data.bands.p50[last])}.
        </p>
        <p>
          Les montants ne tiennent compte ni de l'inflation ni de l'impôt : dans {years} ans, ils
          achèteront moins qu'aujourd'hui.
        </p>
      </div>
    </details>
  );
}
