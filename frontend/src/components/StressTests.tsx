import type { StressTestResult } from "@/api";
import { fmt } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  stressTests: StressTestResult[];
}

/** Affiche la performance simulée du portefeuille pendant 3 crises historiques. */
export function StressTests({ stressTests }: Props) {
  if (!stressTests || stressTests.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stress tests historiques</CardTitle>
        <CardDescription>
          Combien ton panier actuel aurait perdu pendant chaque crise — calculé en multipliant tes
          quantités actuelles par les prix réels de l'époque.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-3">
          {stressTests.map((s) => {
            const severity = Math.abs(s.drawdown_pct);
            const toneClass =
              severity >= 0.2
                ? "border-red-500/40 bg-red-500/5"
                : severity >= 0.1
                  ? "border-amber-500/40 bg-amber-500/5"
                  : "border-zinc-500/40 bg-zinc-500/5";

            return (
              <div key={s.id} className={`rounded-lg border ${toneClass} p-3 space-y-2`}>
                <div className="font-medium text-sm">{s.label}</div>
                <div className="text-xs text-muted-foreground italic">{s.description}</div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-dashed">
                  <div>
                    <div className="text-xs text-muted-foreground">PnL fin période</div>
                    <div className="font-mono tabular font-semibold text-[hsl(var(--loss))]">
                      {fmt.signedPct(s.pnl_pct)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Pire moment</div>
                    <div className="font-mono tabular font-semibold text-[hsl(var(--loss))]">
                      {fmt.signedPct(s.drawdown_pct)}
                    </div>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground font-mono tabular pt-1">
                  {s.start} → {s.end}
                </div>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground italic mt-4 border-t pt-3">
          Calcul : Σ(quantité actuelle × prix historique) sur chaque fenêtre. Ce sont des chiffres
          réels, pas une simulation Monte-Carlo.
        </p>
      </CardContent>
    </Card>
  );
}
