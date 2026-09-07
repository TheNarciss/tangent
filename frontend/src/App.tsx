import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { fetchTermsVersion, useCurrentUser } from "@/api";
import { useProfile } from "@/lib/profile";
import { useProfileSync } from "@/lib/profile-sync";

import { AppShell } from "@/components/AppShell";
import { NAV_PATHS } from "@/components/Sidebar";

import { AccountTab } from "@/components/AccountTab";
import { Accounts } from "@/components/Accounts";
import { AddBankButton } from "@/components/AddBankButton";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { UserMenu } from "@/components/auth/UserMenu";
import { BengenWidget } from "@/components/BengenWidget";
import { Dashboard } from "@/components/Dashboard";
import { OAuthCallbackHandler } from "@/components/OAuthCallback";
import { Placements } from "@/components/Placements";
import { PowensCallbackHandler } from "@/components/PowensCallback";
import { ProfilePage } from "@/components/Profile";
import { Projection } from "@/components/Projection";
import { TermsGate } from "@/components/TermsGate";

export default function App() {
  const auth = useCurrentUser();
  useProfileSync(!!auth.data);

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

  return <Shell />;
}

function Shell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  // Title + actions vary per route
  const config = getViewConfig(pathname, {
    headerActions: pathname === NAV_PATHS.accounts ? <AddBankButton /> : null,
  });

  return (
    <>
      <PowensCallbackHandler />
      <OAuthCallbackHandler />
      <AppShell
        pageTitle={config.title}
        pageSubtitle={config.subtitle}
        headerActions={config.headerActions}
        sidebarFooter={<UserMenu />}
      >
        <Routes>
          <Route
            path={NAV_PATHS.overview}
            element={<Dashboard onNavigateToAccounts={() => navigate(NAV_PATHS.accounts)} />}
          />
          <Route path={NAV_PATHS.accounts} element={<Accounts />} />
          <Route path={NAV_PATHS.investments} element={<Placements />} />
          <Route path={NAV_PATHS.projection} element={<ProjectionView />} />
          <Route path={NAV_PATHS.profile} element={<ProfilePage />} />
          <Route path={NAV_PATHS.account} element={<AccountView />} />
          <Route path="*" element={<Navigate to={NAV_PATHS.overview} replace />} />
        </Routes>
      </AppShell>
    </>
  );
}

function AccountView() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-24">
      <AccountTab />
    </div>
  );
}

function ProjectionView() {
  const [profile] = useProfile();
  return (
    <div className="space-y-6">
      <Projection />
      {profile && <BengenWidget profile={profile} />}
    </div>
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

function getViewConfig(pathname: string, inputs: ViewConfigInputs): ViewConfig {
  const { headerActions } = inputs;

  switch (pathname) {
    case NAV_PATHS.accounts:
      return {
        title: "Comptes",
        subtitle: "Tous tes comptes, mis à jour automatiquement",
        headerActions,
      };
    case NAV_PATHS.projection:
      return { title: "Projection", subtitle: "Où tu en seras dans quelques années" };
    case NAV_PATHS.investments:
      return {
        title: "Placements",
        subtitle: "Ce que tu détiens, le risque que tu prends, des pistes",
      };
    case NAV_PATHS.profile:
      return { title: "Mon profil", subtitle: "Ce que Tangent doit savoir pour calculer juste" };
    case NAV_PATHS.account:
      return { title: "Mon compte", subtitle: "Connexion, sécurité, banques et briefing" };
    default:
      return { title: "Aperçu", subtitle: "Ton patrimoine en un coup d'œil" };
  }
}
