import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBengen, useDashboard } from "@/api";
import { fmt } from "@/lib/format";
import type { UserProfile } from "@/lib/profile";

interface Props {
  profile: UserProfile;
}

export function BengenWidget({ profile }: Props) {
  const { data: dashboard } = useDashboard();
  const currentCapital = dashboard?.metrics.total_value ?? 0;
  const expectedReturn = dashboard?.metrics.expected_return ?? 0.08;

  const [targetIncome, setTargetIncome] = useState<number>(100);
  const [withdrawalRate, setWithdrawalRate] = useState<number>(4); // raw %

  const baseReq = useMemo(
    () => ({
      target_monthly_income: targetIncome,
      withdrawal_rate: withdrawalRate / 100,
      current_capital: currentCapital,
      monthly_dca: profile.monthly_dca,
      expected_return: expectedReturn,
    }),
    [targetIncome, withdrawalRate, currentCapital, profile.monthly_dca, expectedReturn],
  );

  const { data: base } = useBengen(baseReq);

  // Alternatives : DCA × 1.5 et × 2.0 pour montrer l'effet d'accélération
  const altDca1 = Math.round(profile.monthly_dca * 1.5);
  const altDca2 = Math.round(profile.monthly_dca * 2.0);
  const { data: alt1 } = useBengen({ ...baseReq, monthly_dca: altDca1 });
  const { data: alt2 } = useBengen({ ...baseReq, monthly_dca: altDca2 });

  const dateLabel = (years: number | null): string => {
    if (years === null) return "jamais atteint";
    if (years === 0) return "déjà atteint";
    const target = new Date();
    target.setMonth(target.getMonth() + Math.round(years * 12));
    return target.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Objectif revenu mensuel</CardTitle>
        <CardDescription>
          Combien de capital faut-il pour générer un revenu passif soutenable selon la règle Bengen
          ?
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Inputs */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Revenu mensuel visé (€/mois)</Label>
            <Input
              type="number"
              min={0}
              step={10}
              value={targetIncome}
              onChange={(e) => setTargetIncome(Number(e.target.value) || 0)}
              className="font-mono tabular"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">
              Taux de retrait (%) — Bengen recommande 4 %
            </Label>
            <Input
              type="number"
              min={0.1}
              max={10}
              step={0.1}
              value={withdrawalRate}
              onChange={(e) => setWithdrawalRate(Number(e.target.value) || 4)}
              className="font-mono tabular"
            />
          </div>
        </div>

        {/* Résultats principaux */}
        {base && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4 sm:text-center">
              <div>
                <div className="text-xs text-muted-foreground">Capital nécessaire</div>
                <div className="font-mono text-xl font-semibold tabular sm:text-2xl">
                  {fmt.eur(base.capital_needed)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Atteint en</div>
                <div className="font-mono text-xl font-semibold tabular sm:text-2xl">
                  {base.years_to_reach === null
                    ? "—"
                    : base.years_to_reach === 0
                      ? "déjà"
                      : `${base.years_to_reach.toFixed(1)} ans`}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Date estimée</div>
                <div className="font-mono text-xl font-semibold capitalize tabular sm:text-2xl">
                  {dateLabel(base.years_to_reach)}
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground italic border-l-2 border-muted pl-3">
              {base.rationale}
            </p>
          </div>
        )}

        {/* Alternatives : effet d'un DCA plus élevé */}
        {base && base.years_to_reach !== null && base.years_to_reach > 0 && (
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">
              💡 Effet d'accélération si tu augmentes ton DCA
            </Label>
            <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div className="rounded border p-3 space-y-1">
                <div className="text-xs text-muted-foreground">DCA {altDca1} €/mois (×1,5)</div>
                <div className="font-mono tabular">
                  {alt1?.years_to_reach !== null && alt1?.years_to_reach !== undefined ? (
                    <>
                      {alt1.years_to_reach.toFixed(1)} ans · {dateLabel(alt1.years_to_reach)}
                    </>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
              <div className="rounded border p-3 space-y-1">
                <div className="text-xs text-muted-foreground">DCA {altDca2} €/mois (×2)</div>
                <div className="font-mono tabular">
                  {alt2?.years_to_reach !== null && alt2?.years_to_reach !== undefined ? (
                    <>
                      {alt2.years_to_reach.toFixed(1)} ans · {dateLabel(alt2.years_to_reach)}
                    </>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hypothèses utilisées (transparence) */}
        <div className="text-xs text-muted-foreground border-t pt-3 space-y-0.5">
          <div>
            Hypothèses : capital actuel {fmt.eur(currentCapital)} · DCA {profile.monthly_dca} €/mois
            · μ blendé {fmt.pct(expectedReturn)}
          </div>
          <div>
            Règle Bengen (1994) : sur 30 ans glissants depuis 1926, retirer 4 % du capital initial
            ajusté inflation n'a jamais épuisé un portefeuille 60/40.
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
