import type { AssetMetrics } from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
              <TableHead className="hidden text-right md:table-cell">Cours</TableHead>
              <TableHead className="text-right">Poids</TableHead>
              <TableHead className="text-right">Valeur</TableHead>
              <TableHead className="text-right">P/L</TableHead>
              <TableHead className="hidden text-right md:table-cell">μ</TableHead>
              <TableHead className="hidden text-right md:table-cell">σ</TableHead>
              <TableHead className="hidden text-right md:table-cell">CVaR 95 %</TableHead>
              <TableHead className="hidden text-right md:table-cell">Max DD</TableHead>
              <TableHead className="hidden text-right md:table-cell">Sharpe</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {assets.map((a) => {
              const positive = a.pnl >= 0;
              return (
                <TableRow key={a.ticker}>
                  <TableCell className="font-mono font-medium">{a.ticker}</TableCell>
                  <TableCell className="hidden text-right font-mono tabular md:table-cell">
                    {fmt.eur(a.price)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.pct(a.weight)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt.eur(a.value)}</TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-mono tabular",
                      positive ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                    )}
                  >
                    {fmt.signedEur(a.pnl)}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {fmt.signedPct(a.pnl_pct)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.pct(a.annual_return)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.pct(a.annual_vol)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular text-[hsl(var(--loss))]">
                    {fmt.signedPct(a.cvar_95)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular text-[hsl(var(--loss))]">
                    {fmt.signedPct(a.max_drawdown_observed)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.num(a.sharpe)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
