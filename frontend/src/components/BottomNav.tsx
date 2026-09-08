import { MoreHorizontal } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

import { NAV_ITEMS, NAV_PATHS } from "./Sidebar";

interface BottomNavProps {
  onOpenMore: () => void;
  isMoreOpen?: boolean;
}

const ITEM_CLASS =
  "flex min-h-[44px] flex-1 flex-col items-center justify-center gap-1 text-xs transition-colors";

/**
 * Mobile-only bottom navigation bar (md:hidden).
 *
 * 5 items: the 4 main views (same list as the Sidebar) + a "Plus" trigger
 * that opens a MoreSheet containing the equivalent of the desktop UserMenu
 * (profile / account / Google link / legal / logout).
 */
export function BottomNav({ onOpenMore, isMoreOpen = false }: BottomNavProps) {
  return (
    <nav
      aria-label="Navigation principale"
      className="fixed inset-x-0 bottom-0 z-30 flex h-[calc(4rem+env(safe-area-inset-bottom))] items-stretch border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.view}
            to={NAV_PATHS[item.view]}
            end={item.view === "overview"}
            className={({ isActive }) =>
              cn(
                ITEM_CLASS,
                isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn("h-5 w-5", isActive && "text-primary")} />
                <span className={cn(isActive && "font-medium")}>{item.label}</span>
              </>
            )}
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
