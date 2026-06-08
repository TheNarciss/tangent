import { useState, type ReactNode } from "react";
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

/**
 * Application shell — Claude Console inspired.
 *
 * Desktop (≥ md): left sidebar 240px fixed in flex layout, full-width main.
 * Mobile (< md): sidebar becomes a slide-in drawer triggered by a hamburger
 *   button in the header; an overlay closes it on tap; the drawer also
 *   auto-closes when navigating.
 *
 * Uses existing CSS variables only (no new color tokens).
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

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        currentView={currentView}
        onViewChange={onViewChange}
        footer={sidebarFooter}
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-border bg-background px-4 py-3 md:gap-4 md:px-8 md:py-4">
          {/* Hamburger — mobile only */}
          <button
            type="button"
            aria-label="Ouvrir le menu"
            onClick={() => setMobileOpen(true)}
            className="-ml-1 rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Title block — grows to fill */}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-semibold tracking-tight md:text-xl">
              {pageTitle}
            </h1>
            {pageSubtitle && (
              <p className="mt-0.5 hidden truncate text-sm text-muted-foreground md:block">
                {pageSubtitle}
              </p>
            )}
          </div>

          {/* Actions — right side */}
          {headerActions && (
            <div className="flex flex-shrink-0 items-center gap-2">{headerActions}</div>
          )}
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
