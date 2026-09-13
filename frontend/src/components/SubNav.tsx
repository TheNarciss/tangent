import { Check } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

import { cn } from "@/lib/utils";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";

import { NAV_PATHS, isActivePath, type NavGroup } from "./Sidebar";

/**
 * The sub-views of the active group, on a phone.
 *
 * Two doors to the same place: a strip of pills under the header, always
 * visible, and a sheet lifted by tapping the active tab again. Both are
 * plain links, so the URL stays the source of truth.
 */
export function SubNavStrip({ group, pathname }: { group: NavGroup; pathname: string }) {
  if (group.children.length < 2) return null;
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-border bg-background px-4 py-2 md:hidden">
      {group.children.map((child) => {
        const active = isActivePath(pathname, child.view);
        return (
          <NavLink
            key={child.view}
            to={NAV_PATHS[child.view]}
            className={cn(
              "shrink-0 rounded-full px-3 py-1 text-xs transition-colors",
              active
                ? "bg-primary font-medium text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {child.label}
          </NavLink>
        );
      })}
    </div>
  );
}

interface SubNavSheetProps {
  group: NavGroup | null;
  pathname: string;
  onOpenChange: (open: boolean) => void;
}

export function SubNavSheet({ group, pathname, onOpenChange }: SubNavSheetProps) {
  const navigate = useNavigate();
  return (
    <BottomSheet open={group !== null} onOpenChange={onOpenChange}>
      <BottomSheetContent>
        <BottomSheetHeader>
          <BottomSheetTitle>{group?.label}</BottomSheetTitle>
        </BottomSheetHeader>
        <div className="space-y-1 p-4">
          {group?.children.map((child) => {
            const Icon = child.icon;
            const active = isActivePath(pathname, child.view);
            return (
              <button
                key={child.view}
                type="button"
                onClick={() => {
                  navigate(NAV_PATHS[child.view]);
                  onOpenChange(false);
                }}
                className={cn(
                  "flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-3 text-left text-sm hover:bg-accent",
                  active && "font-medium",
                )}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {child.label}
                </span>
                {active && <Check className="h-4 w-4 text-primary" aria-hidden />}
              </button>
            );
          })}
        </div>
      </BottomSheetContent>
    </BottomSheet>
  );
}
