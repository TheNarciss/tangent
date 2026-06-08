import { Sparkles, Wallet, Target, TrendingUp, MoreHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

import { type NavView } from "./Sidebar";

interface BottomNavProps {
  currentView: NavView;
  onViewChange: (v: NavView) => void;
  onOpenMore: () => void;
  isMoreOpen?: boolean;
}

interface BottomNavItem {
  view: NavView | "more";
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: BottomNavItem[] = [
  { view: "ai", label: "IA", icon: Sparkles },
  { view: "accounts", label: "Comptes", icon: Wallet },
  { view: "optimization", label: "Optim.", icon: Target },
  { view: "projection", label: "Projection", icon: TrendingUp },
  { view: "more", label: "Plus", icon: MoreHorizontal },
];

/**
 * Mobile-only bottom navigation bar (md:hidden).
 *
 * 5 items: 4 main views + a "Plus" trigger that opens a MoreSheet
 * containing the equivalent of the desktop UserMenu (profile / settings /
 * Google link / legal / logout).
 */
export function BottomNav({
  currentView,
  onViewChange,
  onOpenMore,
  isMoreOpen = false,
}: BottomNavProps) {
  return (
    <nav
      aria-label="Navigation principale"
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 items-stretch border-t border-border bg-background md:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isMore = item.view === "more";
        const active = isMore ? isMoreOpen : currentView === item.view;
        return (
          <button
            key={item.view}
            type="button"
            onClick={() => (isMore ? onOpenMore() : onViewChange(item.view as NavView))}
            className={cn(
              "flex min-h-[44px] flex-1 flex-col items-center justify-center gap-1 text-xs transition-colors",
              active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className={cn("h-5 w-5", active && "text-primary")} />
            <span className={cn(active && "font-medium")}>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
