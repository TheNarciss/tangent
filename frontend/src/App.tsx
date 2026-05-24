import { useEffect, useState } from "react";

import {
  ApiError,
  useCurrentUser,
  useDashboard,
  useOptimizer,
  usePortfolio,
  useTimeseries,
  type OptimizerObjective,
  type OptimizerRequest,
} from "@/api";
import { ageFromBirthDate, useProfile } from "@/lib/profile";
import { Assets } from "@/components/Assets";
import { PowensCallbackHandler } from "@/components/PowensCallback";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { useProfileSync } from "@/lib/profile-sync";
import { UserMenu } from "@/components/auth/UserMenu";
import { Correlation } from "@/components/Correlation";
import { Editor } from "@/components/Editor";
import { Insights } from "@/components/Insights";
import { Metrics } from "@/components/Metrics";
import { StressTests } from "@/components/StressTests";
import { Optimizer } from "@/components/Optimizer";
import { Scanner } from "@/components/Scanner";
import { ProfileButton } from "@/components/Profile";
import { SettingsButton } from "@/components/Settings";
import { SyncButton } from "@/components/SyncButton";
import { Projection } from "@/components/Projection";
import { BengenWidget } from "@/components/BengenWidget";
import { RiskReturn } from "@/components/RiskReturn";
import { Timeline } from "@/components/Timeline";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function App() {
  const auth = useCurrentUser();
  useProfileSync(!!auth.data);

  // Auth still loading — show empty shell to avoid login flash
  if (auth.isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Chargement…</p>
      </div>
    );
  }

  // Not logged in → AuthScreen
  if (!auth.data) {
    return <AuthScreen />;
  }

  // Logged in → main dashboard
  return <Dashboard />;
}

function Dashboard() {
  const { data: user } = useCurrentUser();
  const dashboard = useDashboard();
  const portfolio = usePortfolio();
  const timeseries = useTimeseries();
  const [profile] = useProfile();

  return (
    <div className="min-h-screen bg-background">
      <PowensCallbackHandler />
      <div className="container max-w-7xl py-10 space-y-8">
        <header className="flex items-baseline justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Portfolio</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {dashboard.data ? (
                <>
                  Au {new Date(dashboard.data.as_of).toLocaleDateString("fr-FR")} ·{" "}
                  {dashboard.data.metrics.assets.length} positions
                </>
              ) : (
                <>Bienvenue {user?.display_name || user?.email}</>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <SyncButton />
            <ProfileButton />
            <SettingsButton />
            {portfolio.data && <Editor portfolio={portfolio.data} />}
            <UserMenu />
          </div>
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
              <StressTests stressTests={dashboard.data.stress_tests} />
              <Insights insights={dashboard.data.insights} />
            </TabsContent>

            <TabsContent value="history" className="space-y-6">
              {timeseries.isLoading && <p className="text-sm text-muted-foreground">Chargement de l'historique…</p>}
              {timeseries.data && <Timeline ts={timeseries.data} />}
            </TabsContent>

            <TabsContent value="projection" className="space-y-6">
              <Projection />
              {profile && <BengenWidget profile={profile} />}
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
  const [profile] = useProfile();
  const age = profile ? ageFromBirthDate(profile.birth_date) : null;
  const hasProfile = !!profile && age !== null && profile.fiscal_shares > 0;

  // Strategy: profile = explicit σ max + μ target (concrete fields, instead of an abstract slider)
  const profileMaxVol = hasProfile && profile ? profile.max_annual_volatility : 10;
  const profileTargetReturn = hasProfile && profile ? profile.target_annual_return : 7;

  const [objective, setObjective] = useState<OptimizerObjective>(() => {
    const saved = typeof window !== "undefined"
      ? window.localStorage.getItem("tangent.optimizer.objective")
      : null;
    return (saved as OptimizerObjective | null) ?? "max_sharpe";
  });
  const [includeEnvelopes, setIncludeEnvelopes] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem("tangent.optimizer.include_envelopes") === "true";
  });
  const [totalCapital, setTotalCapital] = useState<number | "">("");
  const [maxVolatility, setMaxVolatility] = useState<number | "">(profileMaxVol);

  // Persist toggles in localStorage so they survive refresh
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("tangent.optimizer.objective", objective);
    }
  }, [objective]);
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("tangent.optimizer.include_envelopes", String(includeEnvelopes));
    }
  }, [includeEnvelopes]);

  useEffect(() => {
    setMaxVolatility(profileMaxVol);
  }, [profileMaxVol]);

  const req: OptimizerRequest = {
    objective,
    ...(objective === "target_volatility" && typeof maxVolatility === "number"
        ? { max_volatility: maxVolatility / 100 } : {}),
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
            ceilings_used: profile.ceilings_used,
          }
        : {}),
    ...(typeof totalCapital === "number" && totalCapital > 0
        ? { total_capital: totalCapital } : {}),
  };

  const optimizer = useOptimizer(req);

  // Frontier curve = ETF-only frontier. Kept even with envelopes (savings shown on the
  // right panel). Still informative: it's the Pareto-optimal ceiling on the ETF side.
  const optimalPoint = optimizer.data
    ? {
        sigma: optimizer.data.optimal.volatility,
        mu: optimizer.data.optimal.expected_return,
        label: objective === "max_sharpe" ? "Max Sharpe"
             : objective === "min_variance" ? "Min variance"
             : objective === "from_strategy" ? "Selon ta stratégie"
             : "Cible vol max",
      }
    : undefined;

  return (
    <div className="space-y-6">
      <RiskReturn
        metrics={dashboard.metrics}
        frontier={dashboard.frontier}
        smoothFrontier={optimizer.data?.frontier_curve}
        optimal={optimalPoint}
        envelopePoints={includeEnvelopes ? optimizer.data?.envelope_points : undefined}
      />
      <Optimizer
        objective={objective} onObjectiveChange={setObjective}
        includeEnvelopes={includeEnvelopes} onIncludeEnvelopesChange={setIncludeEnvelopes}
        totalCapital={totalCapital} onTotalCapitalChange={setTotalCapital}
        maxVolatility={maxVolatility} onMaxVolatilityChange={setMaxVolatility}
        hasProfile={hasProfile} query={optimizer}
        profileTargetReturn={profileTargetReturn}
        profileMaxVol={profileMaxVol}
      />
      <Scanner />
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
    InfeasibleStrategyError: "Stratégie infaisable",
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
    InfeasibleStrategyError: "Augmente la volatilité max OU baisse le rendement cible dans ton profil. Active les livrets si pas déjà fait.",
  }[type] ?? null;
}