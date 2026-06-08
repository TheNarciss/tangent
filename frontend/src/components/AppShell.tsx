import { useEffect, useState, type ReactNode } from "react";
import { Menu } from "lucide-react";

import { Sidebar, type NavView } from "./Sidebar";

interface AppShellProps {
  currentView: NavView;
  onViewChange: (v: NavView) => void;
  pageTitle: string;
  pageSubtitle?: ReactNode;
  headerActions?: ReactNode;
  sidebarFooter?: ReactNode;
  children: ReactNode;
}

const COLLAPSE_KEY = "tangent.sidebar.collapsed";

/**
 * Application shell — Claude Console inspired, dense + responsive.
 *
 * Desktop (≥ md):
 *   - Sidebar 224px (w-56) by default, collapsable to 56px (w-14, icons only).
 *   - Collapse state persisted in localStorage.
 *   - Header compact (py-2.5), title text-base/lg.
 *
 * Mobile (< md):
 *   - Sidebar is a slide-in drawer at full width (224px).
 *   - Hamburger button in header opens it; overlay or nav-tap closes it.
 *   - Subtitle hidden to save vertical space.
 *
 * Padding scale: p-3 mobile → md:p-4 → lg:p-6. Tight enough to see more
 * at a glance, generous enough to not feel cramped.
 */
export function AppShell({
  currentView,
  onViewChange,
  pageTitle,
  pageSubtitle,
  headerActions,
  sidebarFooter,
  children,
}: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(COLLAPSE_KEY) === "true";
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(COLLAPSE_KEY, String(collapsed));
    }
  }, [collapsed]);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        currentView={currentView}
        onViewChange={onViewChange}
        footer={sidebarFooter}
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        isCollapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-border bg-background px-3 py-2.5 md:gap-4 md:px-6 md:py-3">
          {/* Hamburger — mobile only */}
          <button
            type="button"
            aria-label="Ouvrir le menu"
            onClick={() => setMobileOpen(true)}
            className="-ml-1 rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Title block */}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold tracking-tight md:text-base">
              {pageTitle}
            </h1>
            {pageSubtitle && (
              <p className="mt-0.5 hidden truncate text-xs text-muted-foreground md:block">
                {pageSubtitle}
              </p>
            )}
          </div>

          {/* Actions */}
          {headerActions && (
            <div className="flex flex-shrink-0 items-center gap-2">{headerActions}</div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto p-3 md:p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
