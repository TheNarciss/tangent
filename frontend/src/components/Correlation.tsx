import { fmt } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  matrix: Record<string, Record<string, number>>;
}

/**
 * Colormap diverging style RdBu avec saturation pilotée par |ρ|.
 * - ρ → +1 : rouge saturé (lien fort)
 * - ρ → 0 : neutre transparent (s'intègre au fond)
 * - ρ → −1 : bleu saturé (hedge)
 *
 * Saturation au lieu de lightness pour rester lisible sur dark ET light theme.
 */
function cellStyle(rho: number): React.CSSProperties {
  const r = Math.max(-1, Math.min(1, rho));
  const intensity = Math.abs(r);
  const hue = r >= 0 ? 8 : 220;
  const alpha = 0.1 + intensity * 0.8;
  return {
    backgroundColor: `hsla(${hue} 75% 45% / ${alpha})`,
    color: intensity > 0.35 ? "white" : "hsl(var(--foreground))",
    fontWeight: intensity > 0.7 ? 600 : 500,
  };
}

export function Correlation({ matrix }: Props) {
  const tickers = Object.keys(matrix);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Corrélations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-1">
            <thead>
              <tr>
                {/* Corner: top + left sticky */}
                <th className="sticky left-0 top-0 z-20 bg-card" />
                {tickers.map((t) => (
                  <th
                    key={t}
                    scope="col"
                    className="sticky top-0 z-10 bg-card font-mono text-xs text-muted-foreground px-2 pb-1"
                  >
                    {t}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickers.map((row) => (
                <tr key={row}>
                  <th
                    scope="row"
                    className="sticky left-0 z-10 bg-card font-mono text-xs text-muted-foreground pr-2 text-right"
                  >
                    {row}
                  </th>
                  {tickers.map((col) => {
                    const rho = matrix[row][col];
                    const interp = interpRho(rho);
                    return (
                      <td
                        key={col}
                        className="font-mono text-xs tabular rounded px-2 py-1.5 md:px-3 md:py-2 text-center min-w-[56px] md:min-w-[64px] cursor-help"
                        style={cellStyle(rho)}
                        title={`Corrélation ${row} ↔ ${col} : ρ = ${rho.toFixed(2)}\n${interp}\n\nρ ∈ [-1, 1]. ≈ 1 : actifs liés (peu de diversification). ≈ 0 : indépendants. ≈ -1 : se hedgent.`}
                      >
                        {fmt.num(rho)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Légende graduée */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="font-mono">−1</span>
          <div className="flex-1 h-2 rounded overflow-hidden flex">
            {Array.from({ length: 41 }, (_, i) => {
              const rho = (i - 20) / 20;
              const hue = rho >= 0 ? 8 : 220;
              const alpha = 0.1 + Math.abs(rho) * 0.8;
              return (
                <div
                  key={i}
                  className="flex-1"
                  style={{ background: `hsla(${hue} 75% 45% / ${alpha})` }}
                />
              );
            })}
          </div>
          <span className="font-mono">+1</span>
          <span className="ml-2 italic">
            bleu = hedge · pâle = indépendants · rouge = redondants
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function interpRho(rho: number): string {
  if (rho > 0.85) return "très forte : bougent presque ensemble";
  if (rho > 0.5) return "forte : tendance commune";
  if (rho > 0.2) return "modérée";
  if (rho > -0.2) return "faible : quasi-indépendants";
  if (rho > -0.5) return "négative modérée";
  return "négative forte : se compensent";
}
