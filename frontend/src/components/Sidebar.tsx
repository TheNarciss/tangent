import {
  ChevronsLeft,
  ChevronsRight,
  Clock,
  LayoutGrid,
  Sparkles,
  Target,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";

export type NavView =
  | "ai"
  | "overview"
  | "accounts"
  | "history"
  | "projection"
  | "optimization"
  | "profile"
  | "settings";

interface NavItem {
  view: NavView;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { view: "ai", label: "IA", icon: Sparkles },
  { view: "overview", label: "Aperçu", icon: LayoutGrid },
  { view: "accounts", label: "Comptes", icon: Wallet },
  { view: "history", label: "Historique", icon: Clock },
  { view: "projection", label: "Projection", icon: TrendingUp },
  { view: "optimization", label: "Optimisation", icon: Target },
];

interface SidebarProps {
  currentView: NavView;
  onViewChange: (v: NavView) => void;
  footer?: React.ReactNode;
  /** Drawer state on mobile. */
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
  /** Collapsed state on desktop (icons only, narrow). */
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({
  currentView,
  onViewChange,
  footer,
  isMobileOpen = false,
  onMobileClose,
  isCollapsed = false,
  onToggleCollapse,
}: SidebarProps) {
  const handleNavClick = (v: NavView) => {
    onViewChange(v);
    onMobileClose?.();
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

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex transform flex-col border-r border-border bg-card transition-[width,transform] duration-200 ease-out",
          // Width depends on collapsed state (desktop) — drawer always opens at full width on mobile
          isCollapsed ? "w-14 md:w-14" : "w-56 md:w-56",
          // Mobile : always full width when open
          isMobileOpen ? "w-56 translate-x-0" : "-translate-x-full",
          // Desktop : static layout, always translated to 0
          "md:static md:translate-x-0",
        )}
      >
        {/* Logo + close button (mobile) / collapse toggle (desktop) */}
        <div
          className={cn(
            "flex items-center border-b border-border",
            isCollapsed ? "justify-center px-2 py-3" : "justify-between px-4 py-3",
          )}
        >
          {!isCollapsed && <span className="text-base font-semibold tracking-tight">Tangent</span>}
          {/* Mobile close button */}
          {onMobileClose && (
            <button
              type="button"
              aria-label="Fermer le menu"
              onClick={onMobileClose}
              className="md:hidden"
            >
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
          )}
          {/* Desktop collapse toggle */}
          {onToggleCollapse && (
            <button
              type="button"
              aria-label={isCollapsed ? "Déplier le menu" : "Replier le menu"}
              onClick={onToggleCollapse}
              className="hidden text-muted-foreground hover:text-foreground md:block"
              title={isCollapsed ? "Déplier" : "Replier"}
            >
              {isCollapsed ? (
                <ChevronsRight className="h-4 w-4" />
              ) : (
                <ChevronsLeft className="h-4 w-4" />
              )}
            </button>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = currentView === item.view;
            return (
              <button
                key={item.view}
                type="button"
                onClick={() => handleNavClick(item.view)}
                title={isCollapsed ? item.label : undefined}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-md text-sm transition-colors",
                  isCollapsed ? "justify-center p-2" : "px-2.5 py-1.5",
                  active
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        {footer && (
          <div className={cn("border-t border-border", isCollapsed ? "p-2" : "p-2")}>{footer}</div>
        )}
      </aside>
    </>
  );
}
