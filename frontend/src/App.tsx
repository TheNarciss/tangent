import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  ApiError,
  fetchTermsVersion,
  useCurrentUser,
  useDashboard,
  useOptimizer,
  useTimeseries,
  type OptimizerObjective,
  type OptimizerRequest,
} from "@/api";
import { ageFromBirthDate, useProfile } from "@/lib/profile";
import { useProfileSync } from "@/lib/profile-sync";

import { AppShell } from "@/components/AppShell";
import { type NavView } from "@/components/Sidebar";

import { Accounts } from "@/components/Accounts";
import { AddBankButton } from "@/components/AddBankButton";
import { AI } from "@/components/AI";
import { Assets } from "@/components/Assets";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { UserMenu } from "@/components/auth/UserMenu";
import { BengenWidget } from "@/components/BengenWidget";
import { Correlation } from "@/components/Correlation";
import { Insights } from "@/components/Insights";
import { Metrics } from "@/components/Metrics";
import { OAuthCallbackHandler } from "@/components/OAuthCallback";
import { Optimizer } from "@/components/Optimizer";
import { Patrimony } from "@/components/Patrimony";
import { PowensCallbackHandler } from "@/components/PowensCallback";
import { ProfilePage } from "@/components/Profile";
import { Projection } from "@/components/Projection";
import { RiskReturn } from "@/components/RiskReturn";
import { Scanner } from "@/components/Scanner";
import { SettingsPage } from "@/components/Settings";
import { StressTests } from "@/components/StressTests";
import { TermsGate } from "@/components/TermsGate";
import { Timeline } from "@/components/Timeline";

export default function App() {
  const auth = useCurrentUser();
  useProfileSync(!!auth.data);
  const [view, setView] = useState<NavView>("ai");

  const termsVersionQuery = useQuery({
    queryKey: ["terms-version"],
    queryFn: fetchTermsVersion,
    enabled: !!auth.data,
    staleTime: Infinity,
  });

  if (auth.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Chargement…</p>
      </div>
    );
  }

  if (!auth.data) {
    return <AuthScreen />;
  }

  const currentTermsVersion = termsVersionQuery.data?.version;
  if (currentTermsVersion && auth.data.terms_version_accepted !== currentTermsVersion) {
    return <TermsGate user={auth.data} />;
  }

  return <Shell view={view} onViewChange={setView} />;
}

function Shell({ view, onViewChange }: { view: NavView; onViewChange: (v: NavView) => void }) {
  const { data: user } = useCurrentUser();
  const dashboard = useDashboard();
  const timeseries = useTimeseries();
  const [profile] = useProfile();

  // Title + actions vary per view
  const config = getViewConfig(view, {
    user,
    dashboard,
    headerActions: view === "accounts" || view === "overview" ? <AddBankButton /> : null,
  });

  return (
    <>
      <PowensCallbackHandler />
      <OAuthCallbackHandler />
      <AppShell
        currentView={view}
        onViewChange={onViewChange}
        pageTitle={config.title}
        pageSubtitle={config.subtitle}
        headerActions={config.headerActions}
        sidebarFooter={<UserMenu onNavigate={(v) => onViewChange(v as NavView)} />}
      >
        {view === "ai" && <AI />}

        {view === "overview" && (
          <div className="space-y-6">
            {dashboard.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
            {dashboard.isError && <DashboardErrorPanel error={dashboard.error} />}
            {dashboard.data && (
              <>
                {dashboard.data.wealth && <Patrimony wealth={dashboard.data.wealth} />}
                <Metrics metrics={dashboard.data.metrics} />
                <Assets assets={dashboard.data.metrics.assets} />
                <StressTests stressTests={dashboard.data.stress_tests} />
                <Insights insights={dashboard.data.insights} />
              </>
            )}
          </div>
        )}

        {view === "accounts" && <Accounts />}

        {view === "history" && (
          <div className="space-y-6">
            {timeseries.isLoading && (
              <p className="text-sm text-muted-foreground">Chargement de l'historique…</p>
            )}
            {timeseries.data && <Timeline ts={timeseries.data} />}
            {timeseries.isError && !timeseries.isLoading && (
              <p className="text-sm text-muted-foreground">
                Historique indisponible — ajoute des positions ou synchronise un compte d'abord.
              </p>
            )}
          </div>
        )}

        {view === "projection" && (
          <div className="space-y-6">
            <Projection />
            {profile && <BengenWidget profile={profile} />}
          </div>
        )}

        {view === "optimization" && (
          <>
            {dashboard.data ? (
              <OptimizationTab dashboard={dashboard.data} />
            ) : (
              <p className="text-sm text-muted-foreground">
                Optimisation indisponible — ajoute des positions ou synchronise un compte d'abord.
              </p>
            )}
          </>
        )}

        {view === "profile" && <ProfilePage onBack={() => onViewChange("ai")} />}

        {view === "settings" && <SettingsPage onBack={() => onViewChange("ai")} />}
      </AppShell>
    </>
  );
}

interface ViewConfigInputs {
  user: ReturnType<typeof useCurrentUser>["data"];
  dashboard: ReturnType<typeof useDashboard>;
  headerActions: React.ReactNode;
}

interface ViewConfig {
  title: string;
  subtitle?: React.ReactNode;
  headerActions?: React.ReactNode;
}

function getViewConfig(view: NavView, inputs: ViewConfigInputs): ViewConfig {
  const { user, dashboard, headerActions } = inputs;

  const subtitleOverview = dashboard.data ? (
    <>
      Au {new Date(dashboard.data.as_of).toLocaleDateString("fr-FR")} ·{" "}
      {dashboard.data.metrics.assets.length} positions
    </>
  ) : (
    <>Bienvenue {user?.display_name || user?.email}</>
  );

  switch (view) {
    case "ai":
      return { title: "IA", subtitle: "Revues quotidiennes et conversations" };
    case "overview":
      return { title: "Aperçu", subtitle: subtitleOverview, headerActions };
    case "accounts":
      return {
        title: "Comptes",
        subtitle: "Comptes bancaires, positions, transactions",
        headerActions,
      };
    case "history":
      return { title: "Historique", subtitle: "Évolution du patrimoine dans le temps" };
    case "projection":
      return { title: "Projection", subtitle: "Monte-Carlo, frais et indépendance financière" };
    case "optimization":
      return { title: "Optimisation", subtitle: "Frontière efficiente, scanner, corrélations" };
    case "profile":
      return { title: "Profil", subtitle: "Informations personnelles et stratégie" };
    case "settings":
      return { title: "Paramètres", subtitle: "Compte, banques, sécurité" };
  }
}

function OptimizationTab({
  dashboard,
}: {
  dashboard: NonNullable<ReturnType<typeof useDashboard>["data"]>;
}) {
  const [profile] = useProfile();
  const age = profile ? ageFromBirthDate(profile.birth_date) : null;
  const hasProfile = !!profile && age !== null && profile.fiscal_shares > 0;

  const profileMaxVol = hasProfile && profile ? profile.max_annual_volatility : 10;
  const profileTargetReturn = hasProfile && profile ? profile.target_annual_return : 7;

  const [objective, setObjective] = useState<OptimizerObjective>(() => {
    const saved =
      typeof window !== "undefined"
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
      ? { max_volatility: maxVolatility / 100 }
      : {}),
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
      ? { total_capital: totalCapital }
      : {}),
  };

  const optimizer = useOptimizer(req);

  const optimalPoint = optimizer.data
    ? {
        sigma: optimizer.data.optimal.volatility,
        mu: optimizer.data.optimal.expected_return,
        label:
          objective === "max_sharpe"
            ? "Max Sharpe"
            : objective === "min_variance"
              ? "Min variance"
              : objective === "from_strategy"
                ? "Selon ta stratégie"
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
        objective={objective}
        onObjectiveChange={setObjective}
        includeEnvelopes={includeEnvelopes}
        onIncludeEnvelopesChange={setIncludeEnvelopes}
        totalCapital={totalCapital}
        onTotalCapitalChange={setTotalCapital}
        maxVolatility={maxVolatility}
        onMaxVolatilityChange={setMaxVolatility}
        hasProfile={hasProfile}
        query={optimizer}
        profileTargetReturn={profileTargetReturn}
        profileMaxVol={profileMaxVol}
      />
      <Scanner />
      <Correlation matrix={dashboard.metrics.correlation} />
    </div>
  );
}

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
    <div className="space-y-1.5 rounded-md border border-[hsl(var(--loss))] bg-card/40 p-4">
      <div className="text-sm font-medium text-[hsl(var(--loss))]">{humanType(error.type)}</div>
      <div className="text-sm text-muted-foreground">{error.message}</div>
      {advice && <div className="text-xs italic text-muted-foreground">{advice}</div>}
    </div>
  );
}

function humanType(type: string): string {
  return (
    {
      PortfolioEmptyError: "Portefeuille vide",
      PortfolioCorruptedError: "Données du portefeuille corrompues",
      TickerNotFoundError: "Ticker introuvable",
      MarketDataError: "Données de marché indisponibles",
      InsufficientHistoryError: "Historique insuffisant",
      ConfigurationError: "Erreur de configuration",
      UnknownBrokerError: "Broker inconnu",
      InfeasibleStrategyError: "Stratégie infaisable",
    }[type] ?? "Erreur"
  );
}

function errorAdvice(type: string): string | null {
  return (
    {
      PortfolioEmptyError:
        "Va dans l'onglet « Comptes » pour synchroniser une banque, ou clique sur « Modifier positions » pour ajouter manuellement.",
      TickerNotFoundError:
        "Vérifie l'orthographe Yahoo Finance (ex: CW8.PA pour Amundi MSCI World, .PA pour Paris, .DE pour Frankfurt).",
      MarketDataError:
        "Yahoo Finance est peut-être en panne ou ta connexion ne passe pas. Réessaie dans quelques minutes.",
      InsufficientHistoryError:
        "Tes tickers n'ont pas assez d'historique commun. Ajoute des ETFs plus anciens (5+ ans) ou retire les plus récents.",
      ConfigurationError: "Vérifie config/brokers.yaml côté serveur.",
      UnknownBrokerError: "Choisis un broker dans la liste du dropdown (cf. /brokers).",
      InfeasibleStrategyError:
        "Augmente la volatilité max OU baisse le rendement cible dans ton profil. Active les livrets si pas déjà fait.",
    }[type] ?? null
  );
}
