import { useEffect, useState } from "react";

import {
  useOptimizer,
  useWealthSummary,
  type DashboardResponse,
  type OptimizerObjective,
  type OptimizerRequest,
} from "@/api";
import { ageFromBirthDate, ceilingsFromEnvelopes, useProfile } from "@/lib/profile";
import { Assets } from "@/components/Assets";
import { Correlation } from "@/components/Correlation";
import { Metrics } from "@/components/Metrics";
import { Optimizer } from "@/components/Optimizer";
import { RiskReturn } from "@/components/RiskReturn";

/**
 * « Mode avancé » of Placements: the quant views (μ/σ/Sharpe, positions
 * table, risk/return map, full optimizer, scanner, correlations), folded by
 * default and only mounted once opened so the extra /optimizer call is not
 * paid by people who never look.
 */
export function PlacementsAdvanced({ dashboard }: { dashboard: DashboardResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="group rounded-xl border bg-muted/20"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="flex cursor-pointer select-none items-center justify-between px-4 py-3 text-sm font-medium">
        Mode avancé
        <span className="text-xs font-normal text-muted-foreground group-open:hidden">
          rendement, volatilité, optimiseur, scanner, corrélations
        </span>
      </summary>
      {open && (
        <div className="space-y-6 border-t p-4 md:p-6">
          <AdvancedContent dashboard={dashboard} />
        </div>
      )}
    </details>
  );
}

function AdvancedContent({ dashboard }: { dashboard: DashboardResponse }) {
  const [profile] = useProfile();
  const wealth = useWealthSummary();
  const age = profile ? ageFromBirthDate(profile.birth_date) : null;
  const hasProfile = !!profile && age !== null && profile.fiscal_shares > 0;
  const ceilingsUsed = ceilingsFromEnvelopes(wealth.data?.envelopes) ?? profile?.ceilings_used;

  const profileMaxVol = hasProfile && profile ? profile.max_annual_volatility : 10;
  const profileTargetReturn = hasProfile && profile ? profile.target_annual_return : 7;

  const [objective, setObjective] = useState<OptimizerObjective>(() => {
    const saved = window.localStorage.getItem("tangent.optimizer.objective");
    // « Max Sharpe » is gone (§8.3): a stored one falls back on the profile.
    const fallback: OptimizerObjective = hasProfile ? "from_strategy" : "target_volatility";
    return saved === "min_variance" || saved === "target_volatility" || saved === "from_strategy"
      ? saved
      : fallback;
  });
  const [includeEnvelopes, setIncludeEnvelopes] = useState<boolean>(
    () => window.localStorage.getItem("tangent.optimizer.include_envelopes") === "true",
  );
  const [totalCapital, setTotalCapital] = useState<number | "">("");
  const [maxVolatility, setMaxVolatility] = useState<number | "">(profileMaxVol);

  useEffect(() => {
    window.localStorage.setItem("tangent.optimizer.objective", objective);
  }, [objective]);
  useEffect(() => {
    window.localStorage.setItem("tangent.optimizer.include_envelopes", String(includeEnvelopes));
  }, [includeEnvelopes]);
  useEffect(() => {
    setMaxVolatility(profileMaxVol);
  }, [profileMaxVol]);

  const req: OptimizerRequest = {
    objective,
    ...(objective === "target_volatility" && typeof maxVolatility === "number"
      ? { max_volatility: maxVolatility / 100 }
      : {}),
    ...(objective === "from_strategy" && hasProfile && profile
      ? {
          max_volatility: profile.max_annual_volatility / 100,
          target_return: profile.target_annual_return / 100,
        }
      : {}),
    ...(includeEnvelopes && hasProfile && profile
      ? {
          include_envelopes: true,
          age: age!,
          rfr: profile.rfr_n_minus_2,
          fiscal_shares: profile.fiscal_shares,
          ceilings_used: ceilingsUsed,
        }
      : {}),
    ...(typeof totalCapital === "number" && totalCapital > 0
      ? { total_capital: totalCapital }
      : {}),
  };
  const optimizer = useOptimizer(req);

  const optimalPoint = optimizer.data
    ? {
        sigma: optimizer.data.optimal.volatility,
        mu: optimizer.data.optimal.expected_return,
        label:
          objective === "min_variance"
            ? "Min variance"
            : objective === "from_strategy"
              ? "Selon ton profil"
              : "Cible vol max",
      }
    : undefined;

  return (
    <>
      <Metrics metrics={dashboard.metrics} />
      <Assets assets={dashboard.metrics.assets} />
      <RiskReturn
        metrics={dashboard.metrics}
        smoothFrontier={optimizer.data?.frontier_curve}
        optimal={optimalPoint}
        envelopePoints={includeEnvelopes ? optimizer.data?.envelope_points : undefined}
      />
      <Optimizer
        objective={objective}
        onObjectiveChange={setObjective}
        includeEnvelopes={includeEnvelopes}
        onIncludeEnvelopesChange={setIncludeEnvelopes}
        totalCapital={totalCapital}
        onTotalCapitalChange={setTotalCapital}
        maxVolatility={maxVolatility}
        onMaxVolatilityChange={setMaxVolatility}
        hasProfile={hasProfile}
        query={optimizer}
        profileTargetReturn={profileTargetReturn}
        profileMaxVol={profileMaxVol}
      />
      <Correlation matrix={dashboard.metrics.correlation} />
    </>
  );
}
