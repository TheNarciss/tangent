import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ChevronRight,
  Compass,
  FileText,
  Link2,
  LogOut,
  Shield,
  User as UserIcon,
} from "lucide-react";

import { listOAuthAccounts, startGoogleAssociate, useCurrentUser, useLogout } from "@/api";
import { cn } from "@/lib/utils";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";

import { NAV_PATHS, type NavView } from "./Sidebar";

interface MoreSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * BottomSheet that mirrors the desktop UserMenu on mobile.
 *
 * Triggered from BottomNav "Plus" tab. Shows user identity, Google linking,
 * profile/account nav, legal links, and sign out — all in a tap-friendly
 * vertical list.
 */
export function MoreSheet({ open, onOpenChange }: MoreSheetProps) {
  const navigate = useNavigate();
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const oauthAccounts = useQuery({
    queryKey: ["user", "oauth-accounts"],
    queryFn: listOAuthAccounts,
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  if (!user) return null;

  const initial = (user.display_name?.[0] || user.email[0]).toUpperCase();
  const hasGoogle = oauthAccounts.data?.some((a) => a.oauth_name === "google") ?? false;

  const handleLinkGoogle = async () => {
    try {
      await startGoogleAssociate();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Impossible de lier le compte Google.");
    }
  };

  const handleNavigate = (v: NavView) => {
    navigate(NAV_PATHS[v]);
    onOpenChange(false);
  };

  return (
    <BottomSheet open={open} onOpenChange={onOpenChange}>
      <BottomSheetContent>
        <BottomSheetHeader>
          <BottomSheetTitle>Compte</BottomSheetTitle>
        </BottomSheetHeader>

        <div className="space-y-4 p-4">
          {/* User identity */}
          <div className="flex items-center gap-3 rounded-md border border-border bg-card/40 px-3 py-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-base font-medium">
              {initial}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {user.display_name || user.email.split("@")[0]}
              </p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              {user.is_superuser && <p className="mt-0.5 text-xs text-[hsl(var(--gain))]">Admin</p>}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-1">
            {hasGoogle ? (
              <div className="flex items-center justify-between rounded-md px-3 py-3 text-sm text-muted-foreground">
                <span className="flex items-center gap-3">
                  <Link2 className="h-4 w-4" />
                  Google lié ✓
                </span>
              </div>
            ) : (
              <MoreItem icon={Link2} label="Lier mon compte Google" onClick={handleLinkGoogle} />
            )}
            <MoreItem icon={Compass} label="Méthode" onClick={() => handleNavigate("method")} />
            <MoreItem
              icon={UserIcon}
              label="Mon profil"
              onClick={() => handleNavigate("profile")}
            />
            <MoreItem icon={Shield} label="Mon compte" onClick={() => handleNavigate("account")} />
          </div>

          {/* Legal */}
          <div className="space-y-1 border-t border-border pt-4">
            <MoreItemLink
              icon={FileText}
              label="Conditions d'utilisation"
              href="/legal/terms.html"
            />
            <MoreItemLink icon={Shield} label="Confidentialité" href="/legal/privacy.html" />
          </div>

          {/* Sign out */}
          <div className="border-t border-border pt-4">
            <button
              type="button"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
              className={cn(
                "flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-3 text-left text-sm text-[hsl(var(--loss))] hover:bg-accent",
                logout.isPending && "opacity-60",
              )}
            >
              <span className="flex items-center gap-3">
                <LogOut className="h-4 w-4" />
                {logout.isPending ? "Déconnexion…" : "Se déconnecter"}
              </span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </BottomSheetContent>
    </BottomSheet>
  );
}

interface MoreItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}

function MoreItem({ icon: Icon, label, onClick }: MoreItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-3 text-left text-sm hover:bg-accent"
    >
      <span className="flex items-center gap-3">
        <Icon className="h-4 w-4" />
        {label}
      </span>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  );
}

interface MoreItemLinkProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  href: string;
}

function MoreItemLink({ icon: Icon, label, href }: MoreItemLinkProps) {
  return (
    <a
      href={href}
      className="flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-3 text-sm hover:bg-accent"
    >
      <span className="flex items-center gap-3">
        <Icon className="h-4 w-4" />
        {label}
      </span>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </a>
  );
}
