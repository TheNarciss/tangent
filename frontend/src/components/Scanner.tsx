import { Search, Plus, Sparkles } from "lucide-react";
import { useMemo } from "react";

import {
  useScan,
  useWatchlistAdd,
  type ScanCandidate,
  type ScanRequest,
} from "@/api";
import { useSettings, SCANNER_MODE_LABELS, type ScannerMode } from "@/lib/settings";
import { fmt } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** Composant Scanner — découverte d'actifs PEA-éligibles qui amélioreraient
    le Sharpe du portefeuille via marginal contribution. Lit toutes les
    configurations depuis Settings. */
export function Scanner() {
  const [settings] = useSettings();
  const scan = useScan();
  const watchAdd = useWatchlistAdd();

  const modesLabel = useMemo(() => {
    if (settings.scanner.modes.length === 0) return "Aucun mode actif";
    return settings.scanner.modes
      .map((m) => SCANNER_MODE_LABELS[m as ScannerMode] ?? m)
      .join(" · ");
  }, [settings.scanner.modes]);

  const runScan = () => {
    const req: ScanRequest = {
      modes: settings.scanner.modes,
      hypothesis_fraction: settings.scanner.hypothesis_fraction,
      n_results: settings.scanner.n_results,
      expert: {
        cma_shrinkage: settings.expert.cma_shrinkage,
        historical_period: settings.expert.historical_period,
        risk_free_rate: settings.expert.risk_free_rate,
        cma_overrides: settings.expert.cma_overrides,
        cov_estimator: settings.expert.cov_estimator,
        cov_shrinkage: settings.expert.cov_shrinkage,
      },
    };
    scan.mutate(req);
  };

  const addToWatchlist = async (cand: ScanCandidate) => {
    await watchAdd.mutateAsync(cand.ticker);
  };

  const canScan = settings.scanner.modes.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Découvrir des actifs
        </CardTitle>
        <CardDescription>
          Scanne le marché Euronext (PEA-éligibles) et trouve les actifs qui amélioreraient
          le Sharpe de ton portefeuille actuel via leur contribution marginale.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Bandeau récap des modes actifs */}
        <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
          <div>
            <span className="font-medium text-foreground">Modes activés :</span> {modesLabel}
          </div>
          <div className="mt-1">
            <span className="font-medium text-foreground">Hypothèse :</span>{" "}
            ajout simulé de {(settings.scanner.hypothesis_fraction * 100).toFixed(0)} %
            · top {settings.scanner.n_results} candidats
          </div>
          <div className="mt-1 italic">Configurable dans ⚙️ Réglages</div>
        </div>

        {/* Bouton de lancement */}
        <div className="flex items-center gap-3">
          <Button onClick={runScan} disabled={scan.isPending || !canScan} className="gap-2">
            <Search className="h-4 w-4" />
            {scan.isPending ? "Scan en cours…" : "Lancer le scan"}
          </Button>
          {!canScan && (
            <p className="text-xs text-[hsl(var(--loss))]">
              Active au moins un mode dans les Réglages.
            </p>
          )}
          {scan.isPending && (
            <p className="text-xs text-muted-foreground italic">
              ~30 s au 1er scan (vide cache), ~3-5 s ensuite.
            </p>
          )}
        </div>

        {/* Erreurs */}
        {scan.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">
            Erreur : {(scan.error as Error).message}
          </p>
        )}

        {/* Résultats */}
        {scan.data && <ScanResults data={scan.data.candidates} elapsed={scan.data.elapsed_seconds}
                                    universe={scan.data.universe_size}
                                    onAdd={addToWatchlist}
                                    isAdding={watchAdd.isPending} />}
      </CardContent>
    </Card>
  );
}

/* ─── Tableau résultats ────────────────────────────────────────────────── */

interface ResultsProps {
  data: ScanCandidate[];
  elapsed: number;
  universe: number;
  onAdd: (c: ScanCandidate) => void;
  isAdding: boolean;
}

function ScanResults({ data, elapsed, universe, onAdd, isAdding }: ResultsProps) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        Aucun candidat retourné. Élargis les modes dans les Réglages ou réduis les contraintes.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Univers scanné : {universe} tickers · {elapsed.toFixed(1)} s · top {data.length} par ΔSharpe
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Nom</TableHead>
              <TableHead>Catégorie</TableHead>
              <TableHead className="text-right">ΔSharpe</TableHead>
              <TableHead className="text-right">ρ</TableHead>
              <TableHead className="text-right">μ</TableHead>
              <TableHead className="text-right">σ</TableHead>
              <TableHead className="text-right">Sharpe propre</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((c) => (
              <TableRow key={c.ticker}>
                <TableCell className="font-mono font-medium">{c.ticker}</TableCell>
                <TableCell className="text-sm">
                  <div>{c.name}</div>
                  <div className="text-xs text-muted-foreground italic">{c.rationale}</div>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{c.sector}</TableCell>
                <TableCell className="text-right font-mono tabular text-[hsl(var(--gain))]">
                  {c.delta_sharpe > 0 ? "+" : ""}{c.delta_sharpe.toFixed(3)}
                </TableCell>
                <TableCell className="text-right font-mono tabular">
                  {c.correlation_with_portfolio > 0 ? "+" : ""}
                  {c.correlation_with_portfolio.toFixed(2)}
                </TableCell>
                <TableCell className="text-right font-mono tabular">{fmt.pct(c.own_mu)}</TableCell>
                <TableCell className="text-right font-mono tabular">{fmt.pct(c.own_sigma)}</TableCell>
                <TableCell className="text-right font-mono tabular">{c.own_sharpe.toFixed(2)}</TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isAdding}
                    onClick={() => onAdd(c)}
                    className="gap-1"
                  >
                    <Plus className="h-3 w-3" />
                    Suivre
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground italic mt-3 border-t pt-2">
        ΔSharpe : amélioration du Sharpe global si tu remplaces une fraction de ton portefeuille
        par ce candidat. ρ : corrélation aux returns de ton portfolio (négative = diversifier).
        Cliquer "Suivre" ajoute le ticker en quantité 0 — il apparaîtra dans le dashboard et sera
        considéré par l'optimiseur sans modifier ta valorisation actuelle.
      </p>
    </div>
  );
}