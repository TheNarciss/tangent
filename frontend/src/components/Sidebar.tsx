import { LayoutDashboard, PieChart, TrendingUp, Wallet } from "lucide-react";

import { cn } from "@/lib/utils";

export type NavView =
  | "overview"
  | "accounts"
  | "investments"
  | "projection"
  | "profile"
  | "settings";

interface NavItem {
  view: NavView;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { view: "overview", label: "Aperçu", icon: LayoutDashboard },
  { view: "accounts", label: "Comptes", icon: Wallet },
  { view: "investments", label: "Placements", icon: PieChart },
  { view: "projection", label: "Projection", icon: TrendingUp },
];

interface SidebarProps {
  currentView: NavView;
  onViewChange: (v: NavView) => void;
  /** Renders below the nav (typically a UserMenu). */
  footer?: React.ReactNode;
}

/**
 * Desktop-only left sidebar (hidden md:flex).
 *
 * Mobile navigation is handled by BottomNav + MoreSheet — see AppShell.
 */
export function Sidebar({ currentView, onViewChange, footer }: SidebarProps) {
  return (
    <aside className="hidden w-60 flex-col border-r border-border bg-card md:flex">
      {/* Logo */}
      <div className="border-b border-border px-6 py-5">
        <span className="text-lg font-semibold tracking-tight">Tangent</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = currentView === item.view;
          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onViewChange(item.view)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer (user menu, etc.) */}
      {footer && <div className="border-t border-border px-3 py-3">{footer}</div>}
    </aside>
  );
}
