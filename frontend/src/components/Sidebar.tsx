import { Sparkles, Target, TrendingUp, Wallet, X } from "lucide-react";

import { cn } from "@/lib/utils";

export type NavView = "ai" | "accounts" | "projection" | "optimization" | "profile" | "settings";

interface NavItem {
  view: NavView;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { view: "ai", label: "IA", icon: Sparkles },
  { view: "accounts", label: "Comptes", icon: Wallet },
  { view: "projection", label: "Projection", icon: TrendingUp },
  { view: "optimization", label: "Optimisation", icon: Target },
];

interface SidebarProps {
  currentView: NavView;
  onViewChange: (v: NavView) => void;
  /** Renders below the nav (typically a UserMenu). */
  footer?: React.ReactNode;
  /** Drawer state on mobile (md:hidden). Desktop always-visible. */
  isMobileOpen?: boolean;
  /** Called when the user taps the overlay or close button on mobile. */
  onMobileClose?: () => void;
}

export function Sidebar({
  currentView,
  onViewChange,
  footer,
  isMobileOpen = false,
  onMobileClose,
}: SidebarProps) {
  const handleNavClick = (v: NavView) => {
    onViewChange(v);
    onMobileClose?.(); // auto-close drawer on mobile after nav
  };

  return (
    <>
      {/* Overlay (mobile only) */}
      {isMobileOpen && (
        <button
          type="button"
          aria-label="Fermer le menu"
          onClick={onMobileClose}
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
        />
      )}

      {/* Sidebar — fixed drawer on mobile, static column on desktop */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 transform flex-col border-r border-border bg-card transition-transform duration-200 ease-out",
          "md:static md:translate-x-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Logo + mobile close button */}
        <div className="flex items-center justify-between border-b border-border px-6 py-5">
          <span className="text-lg font-semibold tracking-tight">Tangent</span>
          {onMobileClose && (
            <button
              type="button"
              aria-label="Fermer le menu"
              onClick={onMobileClose}
              className="md:hidden"
            >
              <X className="h-5 w-5 text-muted-foreground hover:text-foreground" />
            </button>
          )}
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
                onClick={() => handleNavClick(item.view)}
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
    </>
  );
}
