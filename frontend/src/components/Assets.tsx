import type { AssetMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Props {
  assets: AssetMetrics[];
}

export function Assets({ assets }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Positions
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead className="text-right">Cours</TableHead>
              <TableHead className="text-right">Poids</TableHead>
              <TableHead className="text-right">Valeur</TableHead>
              <TableHead className="text-right">P/L</TableHead>
              <TableHead className="text-right">μ</TableHead>
              <TableHead className="text-right">σ</TableHead>
              <TableHead className="text-right">Sharpe</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assets.map((a) => {
              const positive = a.pnl >= 0;
              return (
                <TableRow key={a.ticker}>
                  <TableCell className="font-mono font-medium">{a.ticker}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.eur(a.price)}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.pct(a.weight)}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.eur(a.value)}</TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-mono tabular",
                      positive ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                    )}
                  >
                    {fmt.signedEur(a.pnl)}
                    <span className="ml-2 text-xs text-muted-foreground">{fmt.signedPct(a.pnl_pct)}</span>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.pct(a.annual_return)}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.pct(a.annual_vol)}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.num(a.sharpe)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
