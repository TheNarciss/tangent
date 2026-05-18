import { useState } from "react";

import {
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
        {dashboard.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">
            Erreur : {(dashboard.error as Error).message}
          </p>
        )}

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