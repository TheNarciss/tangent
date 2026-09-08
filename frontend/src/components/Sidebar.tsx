import { Compass, LayoutDashboard, PieChart, TrendingUp, Wallet } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

export type NavView =
  "overview" | "accounts" | "investments" | "projection" | "method" | "profile" | "account";

/** One URL per view, so the phone's back button, refresh and shared links work. */
export const NAV_PATHS: Record<NavView, string> = {
  overview: "/",
  accounts: "/comptes",
  investments: "/placements",
  projection: "/projection",
  method: "/methode",
  profile: "/profil",
  account: "/compte",
};

export interface NavItem {
  view: NavView;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

/** Main navigation — same list and order in the sidebar and the bottom nav. */
export const NAV_ITEMS: NavItem[] = [
  { view: "overview", label: "Aperçu", icon: LayoutDashboard },
  { view: "accounts", label: "Comptes", icon: Wallet },
  { view: "investments", label: "Placements", icon: PieChart },
  { view: "projection", label: "Projection", icon: TrendingUp },
];

/** Secondary navigation — in the sidebar on desktop, in the « Plus » sheet on
 *  a phone (the bottom bar keeps four items so it stays tappable at 390 px). */
export const SECONDARY_NAV_ITEMS: NavItem[] = [{ view: "method", label: "Méthode", icon: Compass }];

interface SidebarProps {
  /** Renders below the nav (typically a UserMenu). */
  footer?: React.ReactNode;
}

/**
 * Desktop-only left sidebar (hidden md:flex).
 *
 * Mobile navigation is handled by BottomNav + MoreSheet — see AppShell.
 */
export function Sidebar({ footer }: SidebarProps) {
  return (
    <aside className="hidden w-60 flex-col border-r border-border bg-card md:flex">
      {/* Logo */}
      <div className="border-b border-border px-6 py-5">
        <span className="text-lg font-semibold tracking-tight">Tangent</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.view} item={item} />
        ))}
        <div className="my-2 border-t border-border" />
        {SECONDARY_NAV_ITEMS.map((item) => (
          <SidebarLink key={item.view} item={item} />
        ))}
      </nav>

      {/* Footer (user menu, etc.) */}
      {footer && <div className="border-t border-border px-3 py-3">{footer}</div>}
    </aside>
  );
}

function SidebarLink({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={NAV_PATHS[item.view]}
      end={item.view === "overview"}
      className={({ isActive }) =>
        cn(
          "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          isActive
            ? "bg-accent font-medium text-accent-foreground"
            : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
        )
      }
    >
      <Icon className="h-4 w-4" />
      {item.label}
    </NavLink>
  );
}
