import { fmt } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  matrix: Record<string, Record<string, number>>;
}

/**
 * ρ ∈ [-1, 1] mapped to a HSL color via two ramps:
 *   ρ > 0 → red ramp (hue 0)
 *   ρ < 0 → blue ramp (hue 220)
 * Lightness proportional to (1 - |ρ|) so neutral correlations stay near white/dark-gray.
 */
function cellStyle(rho: number): React.CSSProperties {
  const intensity = Math.min(Math.abs(rho), 1); // 0..1
  const hue = rho >= 0 ? 0 : 220;
  const lightness = 95 - intensity * 50; // 95 → 45
  const dark = `hsl(${hue} 70% ${100 - lightness}%)`;
  return {
    backgroundColor: `hsl(${hue} 65% ${lightness}%)`,
    color: intensity > 0.5 ? "white" : undefined,
    "--cell-bg-dark": dark,
  } as React.CSSProperties;
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
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-1">
            <thead>
              <tr>
                <th />
                {tickers.map((t) => (
                  <th key={t} className="font-mono text-xs text-muted-foreground px-2">
                    {t}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tickers.map((row) => (
                <tr key={row}>
                  <th className="font-mono text-xs text-muted-foreground pr-2 text-right">{row}</th>
                  {tickers.map((col) => {
                    const rho = matrix[row][col];
                    const interp =
                      rho > 0.85
                        ? "très forte : bougent presque ensemble"
                        : rho > 0.5
                          ? "forte : tendance commune"
                          : rho > 0.2
                            ? "modérée"
                            : rho > -0.2
                              ? "faible : quasi-indépendants"
                              : rho > -0.5
                                ? "négative modérée"
                                : "négative forte : se compensent";
                    return (
                      <td
                        key={col}
                        className="font-mono text-xs tabular rounded px-3 py-2 text-center min-w-[64px] cursor-help"
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
      </CardContent>
    </Card>
  );
}