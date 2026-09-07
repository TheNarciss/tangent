import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  fetchTermsVersion,
  useCurrentUser,
  useDashboard,
  useOptimizer,
  type OptimizerObjective,
  type OptimizerRequest,
} from "@/api";
import { ageFromBirthDate, useProfile } from "@/lib/profile";
import { useProfileSync } from "@/lib/profile-sync";

import { AppShell } from "@/components/AppShell";
import { type NavView } from "@/components/Sidebar";

import { Accounts } from "@/components/Accounts";
import { AddBankButton } from "@/components/AddBankButton";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { UserMenu } from "@/components/auth/UserMenu";
import { BengenWidget } from "@/components/BengenWidget";
import { Correlation } from "@/components/Correlation";
import { Dashboard } from "@/components/Dashboard";
import { Assets } from "@/components/Assets";
import { Insights } from "@/components/Insights";
import { Metrics } from "@/components/Metrics";
import { OAuthCallbackHandler } from "@/components/OAuthCallback";
import { Optimizer } from "@/components/Optimizer";
import { PowensCallbackHandler } from "@/components/PowensCallback";
import { ProfilePage } from "@/components/Profile";
import { Projection } from "@/components/Projection";
import { RiskReturn } from "@/components/RiskReturn";
import { Scanner } from "@/components/Scanner";
import { SettingsPage } from "@/components/Settings";
import { TermsGate } from "@/components/TermsGate";

export default function App() {
  const auth = useCurrentUser();
  useProfileSync(!!auth.data);
  const [view, setView] = useState<NavView>("overview");

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
  const dashboard = useDashboard();
  const [profile] = useProfile();

  // Title + actions vary per view
  const config = getViewConfig(view, {
    headerActions: view === "accounts" ? <AddBankButton /> : null,
  });

  return (
    <>
      <PowensCallbackHandler onConnected={() => onViewChange("accounts")} />
      <OAuthCallbackHandler />
      <AppShell
        currentView={view}
        onViewChange={onViewChange}
        pageTitle={config.title}
        pageSubtitle={config.subtitle}
        headerActions={config.headerActions}
        sidebarFooter={<UserMenu onNavigate={(v) => onViewChange(v as NavView)} />}
      >
        {view === "overview" && <Dashboard onNavigateToAccounts={() => onViewChange("accounts")} />}

        {view === "accounts" && <Accounts />}

        {view === "projection" && (
          <div className="space-y-6">
            <Projection />
            {profile && <BengenWidget profile={profile} />}
          </div>
        )}

        {view === "investments" && (
          <>
            {dashboard.data ? (
              <InvestmentsTab dashboard={dashboard.data} />
            ) : (
              <p className="text-sm text-muted-foreground">
                Analyse indisponible pour l'instant — connecte un compte d'investissement ou attends
                la fin du chargement.
              </p>
            )}
          </>
        )}

        {view === "profile" && <ProfilePage />}

        {view === "settings" && <SettingsPage />}
      </AppShell>
    </>
  );
}

interface ViewConfigInputs {
  headerActions: React.ReactNode;
}

interface ViewConfig {
  title: string;
  subtitle?: React.ReactNode;
  headerActions?: React.ReactNode;
}

function getViewConfig(view: NavView, inputs: ViewConfigInputs): ViewConfig {
  const { headerActions } = inputs;

  switch (view) {
    case "overview":
      return { title: "Aperçu", subtitle: "Ton patrimoine en un coup d'œil" };
    case "accounts":
      return {
        title: "Comptes",
        subtitle: "Tous tes comptes, mis à jour automatiquement",
        headerActions,
      };
    case "projection":
      return { title: "Projection", subtitle: "Où tu en seras dans quelques années" };
    case "investments":
      return {
        title: "Placements",
        subtitle: "Ce que tu détiens, le risque que tu prends, des pistes",
      };
    case "profile":
      return { title: "Mon profil", subtitle: "Ce que Tangent doit savoir pour calculer juste" };
    case "settings":
      return { title: "Réglages", subtitle: "Options avancées de calcul" };
  }
}

function InvestmentsTab({
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
      <Metrics metrics={dashboard.metrics} />
      <Assets assets={dashboard.metrics.assets} />
      <Insights insights={dashboard.insights} />
      <RiskReturn
        metrics={dashboard.metrics}
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
