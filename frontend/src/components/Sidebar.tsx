import {
  Compass,
  LayoutDashboard,
  ListOrdered,
  PieChart,
  Radar,
  Receipt,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useT, type MessageKey } from "@/i18n";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";

export type NavView =
  | "overview"
  | "accounts"
  | "spending"
  | "investments"
  | "picks"
  | "leads"
  | "projection"
  | "method"
  | "profile"
  | "account";

/** One URL per view, so the phone's back button, refresh and shared links work. */
export const NAV_PATHS: Record<NavView, string> = {
  overview: "/",
  accounts: "/comptes",
  spending: "/depenses",
  investments: "/placements",
  picks: "/placements/liste",
  leads: "/placements/pistes",
  projection: "/projection",
  method: "/methode",
  profile: "/profil",
  account: "/compte",
};

export interface NavItem {
  view: NavView;
  /** Translation key of the label — read it with `t(item.labelKey)`. */
  labelKey: MessageKey;
  icon: LucideIcon;
}

/** A main tab and the views it opens onto. `children[0]` is the tab's own page. */
export interface NavGroup extends NavItem {
  children: NavItem[];
}

/**
 * Main navigation — four groups, the same everywhere.
 *
 * Desktop: the sidebar lists the groups and unfolds the active one's
 * sub-views beneath it. Phone: the bottom bar keeps the four groups (it
 * stays tappable at 390 px); the sub-views of the active group sit in a
 * strip under the header, and tapping the active tab again lifts them in a
 * sheet.
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    view: "overview",
    labelKey: "nav.overview",
    icon: LayoutDashboard,
    children: [
      { view: "overview", labelKey: "nav.overview", icon: LayoutDashboard },
      { view: "method", labelKey: "nav.method", icon: Compass },
    ],
  },
  {
    view: "accounts",
    labelKey: "nav.accounts",
    icon: Wallet,
    children: [
      { view: "accounts", labelKey: "nav.accounts", icon: Wallet },
      { view: "spending", labelKey: "nav.spending", icon: Receipt },
    ],
  },
  {
    view: "investments",
    labelKey: "nav.investments",
    icon: PieChart,
    children: [
      { view: "investments", labelKey: "nav.investments", icon: PieChart },
      { view: "picks", labelKey: "nav.picks", icon: ListOrdered },
      { view: "leads", labelKey: "nav.leads", icon: Radar },
    ],
  },
  {
    view: "projection",
    labelKey: "nav.projection",
    icon: TrendingUp,
    children: [{ view: "projection", labelKey: "nav.projection", icon: TrendingUp }],
  },
];

/** Exact match for the root, prefix match elsewhere — `/placements/liste` lights up Placements. */
export function isActivePath(pathname: string, view: NavView): boolean {
  const path = NAV_PATHS[view];
  return path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`);
}

/** The group the current URL belongs to, if it is one of the four. */
export function groupOf(pathname: string): NavGroup | null {
  return NAV_GROUPS.find((g) => g.children.some((c) => isActivePath(pathname, c.view))) ?? null;
}

interface SidebarProps {
  /** Renders below the nav (typically a UserMenu). */
  footer?: React.ReactNode;
  pathname: string;
}

/**
 * Desktop-only left sidebar (hidden md:flex).
 *
 * Mobile navigation is handled by BottomNav + SubNavSheet + MoreSheet — see AppShell.
 */
export function Sidebar({ footer, pathname }: SidebarProps) {
  const active = groupOf(pathname);
  return (
    <aside className="hidden w-60 flex-col border-r border-border bg-card md:flex">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-border px-6 py-5">
        <Logo size={26} className="shrink-0" />
        <span className="text-lg font-semibold tracking-tight">Tangent</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => {
          const unfolded = active?.view === group.view && group.children.length > 1;
          return (
            <div key={group.view}>
              <SidebarLink item={group} active={active?.view === group.view} />
              {unfolded && (
                <div className="ml-4 mt-1 space-y-0.5 border-l border-border pl-3">
                  {group.children.map((child) => (
                    <SidebarSubLink
                      key={child.view}
                      item={child}
                      active={isActivePath(pathname, child.view)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer (user menu, etc.) */}
      {footer && <div className="border-t border-border px-3 py-3">{footer}</div>}
    </aside>
  );
}

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const { t } = useT();
  const Icon = item.icon;
  return (
    <NavLink
      to={NAV_PATHS[item.view]}
      className={cn(
        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
        active
          ? "bg-accent font-medium text-accent-foreground"
          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
      )}
    >
      <Icon className="h-4 w-4" />
      {t(item.labelKey)}
    </NavLink>
  );
}

function SidebarSubLink({ item, active }: { item: NavItem; active: boolean }) {
  const { t } = useT();
  return (
    <NavLink
      to={NAV_PATHS[item.view]}
      className={cn(
        "flex w-full items-center rounded-md px-3 py-1.5 text-sm transition-colors",
        active ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {t(item.labelKey)}
    </NavLink>
  );
}
