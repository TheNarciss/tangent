import { Link2, LogOut, Shield, User as UserIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listOAuthAccounts, useCurrentUser, useLogout } from "@/api";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { startGoogleAssociate } from "@/api";
import { useT } from "@/i18n";
import { isNative } from "@/native/bridge";
import { NAV_PATHS } from "@/components/Sidebar";

export function UserMenu() {
  const navigate = useNavigate();
  const { t } = useT();
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
      window.alert(e instanceof Error ? e.message : t("menu.linkGoogleFailed"));
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label={t("menu.userMenuAria")}
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
            {initial}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">
              {user.display_name || user.email.split("@")[0]}
            </p>
            <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
            {user.is_superuser && (
              <p className="text-xs leading-none text-[hsl(var(--gain))] mt-1">{t("menu.admin")}</p>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled className="text-xs">
          <UserIcon className="mr-2 h-3.5 w-3.5" />
          <span className="text-muted-foreground">{user.id.slice(0, 8)}…</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {hasGoogle || isNative() ? (
          <DropdownMenuItem disabled className="text-xs">
            <Link2 className="mr-2 h-3.5 w-3.5" />
            <span className="text-muted-foreground">
              {hasGoogle ? t("menu.googleLinked") : t("menu.linkGoogleFromSite")}
            </span>
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={handleLinkGoogle}>
            <Link2 className="mr-2 h-3.5 w-3.5" />
            <span>{t("menu.linkGoogle")}</span>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate(NAV_PATHS.profile)} className="cursor-pointer">
          <UserIcon className="mr-2 h-3.5 w-3.5" />
          <span>{t("nav.profile")}</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate(NAV_PATHS.account)} className="cursor-pointer">
          <Shield className="mr-2 h-3.5 w-3.5" />
          <span>{t("nav.account")}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <a href="/legal/terms.html" className="cursor-pointer">
            <span>{t("menu.terms")}</span>
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href="/legal/privacy.html" className="cursor-pointer">
            <span>{t("menu.privacy")}</span>
          </a>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="text-[hsl(var(--loss))] focus:text-[hsl(var(--loss))]"
        >
          <LogOut className="mr-2 h-3.5 w-3.5" />
          <span>{logout.isPending ? t("menu.signingOut") : t("menu.signOut")}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
