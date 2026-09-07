import { useState, type ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { BottomNav } from "./BottomNav";
import { MoreSheet } from "./MoreSheet";

interface AppShellProps {
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
 * Mobile (< md): bottom navigation bar + a "Plus" bottom sheet.
 *
 * Navigation is URL-driven (react-router): the sidebar and bottom nav are
 * links, the active item follows the current location.
 */
export function AppShell({
  pageTitle,
  pageSubtitle,
  headerActions,
  sidebarFooter,
  children,
}: AppShellProps) {
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar footer={sidebarFooter} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-border bg-background px-4 py-3 md:gap-4 md:px-8 md:py-4">
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

        <main className="flex-1 overflow-y-auto p-4 pb-[calc(5rem+env(safe-area-inset-bottom))] md:p-6 md:pb-6 lg:p-8 lg:pb-8">
          {children}
        </main>
      </div>

      <BottomNav onOpenMore={() => setMoreOpen(true)} isMoreOpen={moreOpen} />

      <MoreSheet open={moreOpen} onOpenChange={setMoreOpen} />
    </div>
  );
}
