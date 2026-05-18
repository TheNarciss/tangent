import { useState } from "react";

import {
  ApiError,
  useDashboard,
  useOptimizer,
  usePortfolio,
  useTimeseries,
  type OptimizerObjective,
} from "@/api";
import { Assets } from "@/components/Assets";
import { Correlation } from "@/components/Correlation";
import { Editor } from "@/components/Editor";
import { Insights } from "@/components/Insights";
import { Metrics } from "@/components/Metrics";
import { Optimizer } from "@/components/Optimizer";
import { Projection } from "@/components/Projection";
import { RiskReturn } from "@/components/RiskReturn";
import { Timeline } from "@/components/Timeline";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function App() {
  const dashboard = useDashboard();
  const portfolio = usePortfolio();
  const timeseries = useTimeseries();

  return (
    <div className="min-h-screen bg-background">
      <div className="container max-w-7xl py-10 space-y-8">
        <header className="flex items-baseline justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Portfolio</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {dashboard.data && (
                <>
                  Au {new Date(dashboard.data.as_of).toLocaleDateString("fr-FR")} ·{" "}
                  {dashboard.data.metrics.assets.length} positions
                </>
              )}
            </p>
          </div>
          {portfolio.data && <Editor portfolio={portfolio.data} />}
        </header>

        {dashboard.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {dashboard.isError && <DashboardErrorPanel error={dashboard.error} />}

        {dashboard.data && (
          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid grid-cols-2 sm:grid-cols-4 w-full max-w-2xl">
              <TabsTrigger value="overview">Aperçu</TabsTrigger>
              <TabsTrigger value="history">Historique</TabsTrigger>
              <TabsTrigger value="projection">Projection</TabsTrigger>
              <TabsTrigger value="optimization">Optimisation</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <Metrics metrics={dashboard.data.metrics} />
              <Assets assets={dashboard.data.metrics.assets} />
              <Insights insights={dashboard.data.insights} />
            </TabsContent>

            <TabsContent value="history" className="space-y-6">
              {timeseries.isLoading && <p className="text-sm text-muted-foreground">Chargement de l'historique…</p>}
              {timeseries.data && <Timeline ts={timeseries.data} />}
            </TabsContent>

            <TabsContent value="projection" className="space-y-6">
              <Projection />
            </TabsContent>

            <TabsContent value="optimization" className="space-y-6">
              <OptimizationTab dashboard={dashboard.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}

function OptimizationTab({ dashboard }: { dashboard: NonNullable<ReturnType<typeof useDashboard>["data"]> }) {
  const [objective, setObjective] = useState<OptimizerObjective>("max_sharpe");
  const optimizer = useOptimizer(objective);

  const optimalPoint = optimizer.data
    ? {
        sigma: optimizer.data.optimal.volatility,
        mu: optimizer.data.optimal.expected_return,
        label: objective === "max_sharpe" ? "Max Sharpe" : "Min variance",
      }
    : undefined;

  return (
    <div className="space-y-6">
      <RiskReturn
        metrics={dashboard.metrics}
        frontier={dashboard.frontier}
        smoothFrontier={optimizer.data?.frontier_curve}
        optimal={optimalPoint}
      />
      <Optimizer objective={objective} onObjectiveChange={setObjective} query={optimizer} />
      <Correlation matrix={dashboard.metrics.correlation} />
    </div>
  );
}

/* Friendly error panel: maps known AppError types from the backend to actionable messages. */
function DashboardErrorPanel({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return (
      <p className="text-sm text-[hsl(var(--loss))]">
        Erreur : {error instanceof Error ? error.message : "inconnue"}
      </p>
    );
  }
  const advice = errorAdvice(error.type);
  return (
    <div className="rounded-md border border-[hsl(var(--loss))] bg-card/40 p-4 space-y-1.5">
      <div className="text-sm font-medium text-[hsl(var(--loss))]">
        {humanType(error.type)}
      </div>
      <div className="text-sm text-muted-foreground">{error.message}</div>
      {advice && <div className="text-xs text-muted-foreground italic">{advice}</div>}
    </div>
  );
}

function humanType(type: string): string {
  return {
    PortfolioEmptyError: "Portefeuille vide",
    PortfolioCorruptedError: "Données du portefeuille corrompues",
    TickerNotFoundError: "Ticker introuvable",
    MarketDataError: "Données de marché indisponibles",
    InsufficientHistoryError: "Historique insuffisant",
    ConfigurationError: "Erreur de configuration",
    UnknownBrokerError: "Broker inconnu",
  }[type] ?? "Erreur";
}

function errorAdvice(type: string): string | null {
  return {
    PortfolioEmptyError: "Clique sur « Modifier positions » pour ajouter au moins une ligne.",
    TickerNotFoundError: "Vérifie l'orthographe Yahoo Finance (ex: CW8.PA pour Amundi MSCI World, .PA pour Paris, .DE pour Frankfurt).",
    MarketDataError: "Yahoo Finance est peut-être en panne ou ta connexion ne passe pas. Réessaie dans quelques minutes.",
    InsufficientHistoryError: "Tes tickers n'ont pas assez d'historique commun. Ajoute des ETFs plus anciens (5+ ans) ou retire les plus récents.",
    ConfigurationError: "Vérifie config/brokers.yaml côté serveur.",
    UnknownBrokerError: "Choisis un broker dans la liste du dropdown (cf. /brokers).",
  }[type] ?? null;
}