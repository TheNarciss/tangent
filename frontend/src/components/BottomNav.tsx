import { ChevronUp, MoreHorizontal } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

import { NAV_GROUPS, NAV_PATHS, groupOf, type NavGroup } from "./Sidebar";

interface BottomNavProps {
  pathname: string;
  onOpenMore: () => void;
  onOpenSubNav: (group: NavGroup) => void;
  isMoreOpen?: boolean;
}

const ITEM_CLASS =
  "flex min-h-[44px] flex-1 flex-col items-center justify-center gap-1 text-xs transition-colors";

/**
 * Mobile-only bottom navigation bar (md:hidden).
 *
 * 5 items: the 4 groups (same list as the Sidebar) + a "Plus" trigger that
 * opens the MoreSheet (profile / account / Google link / legal / logout).
 * Tapping the active group again lifts its sub-views in a sheet — the tab
 * shows a small chevron when it has some.
 */
export function BottomNav({
  pathname,
  onOpenMore,
  onOpenSubNav,
  isMoreOpen = false,
}: BottomNavProps) {
  const active = groupOf(pathname);
  return (
    <nav
      aria-label="Navigation principale"
      className="fixed inset-x-0 bottom-0 z-30 flex h-[calc(4rem+env(safe-area-inset-bottom))] items-stretch border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {NAV_GROUPS.map((group) => {
        const Icon = group.icon;
        const isActive = active?.view === group.view;
        const hasSubViews = group.children.length > 1;
        return (
          <NavLink
            key={group.view}
            to={NAV_PATHS[group.view]}
            onClick={(e) => {
              if (isActive && hasSubViews) {
                e.preventDefault();
                onOpenSubNav(group);
              }
            }}
            className={cn(
              ITEM_CLASS,
              isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className={cn("h-5 w-5", isActive && "text-primary")} />
            <span className={cn("flex items-center gap-0.5", isActive && "font-medium")}>
              {group.label}
              {isActive && hasSubViews && <ChevronUp className="h-3 w-3" aria-hidden />}
            </span>
          </NavLink>
        );
      })}
      <button
        type="button"
        onClick={onOpenMore}
        className={cn(
          ITEM_CLASS,
          isMoreOpen ? "text-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <MoreHorizontal className={cn("h-5 w-5", isMoreOpen && "text-primary")} />
        <span className={cn(isMoreOpen && "font-medium")}>Plus</span>
      </button>
    </nav>
  );
}
