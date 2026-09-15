import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { acceptTerms, fetchTermsVersion, useLogout } from "@/api";
import type { UserRead } from "@/api";
import { useT } from "@/i18n";

interface TermsGateProps {
  user: UserRead;
}

/**
 * Modal bloquant affiché tant que l'user n'a pas accepté la version
 * actuelle des CGU/Privacy. Non-fermable. Refus = logout.
 */
export function TermsGate({ user }: TermsGateProps) {
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const qc = useQueryClient();
  const logout = useLogout();
  const { t } = useT();

  const versionQuery = useQuery({
    queryKey: ["terms-version"],
    queryFn: fetchTermsVersion,
    staleTime: Infinity,
  });

  const mutation = useMutation({
    mutationFn: () => acceptTerms(versionQuery.data?.version ?? ""),
    onSuccess: () => {
      // Refetch user pour que App promote vers le dashboard
      qc.invalidateQueries({ queryKey: ["user", "me"] });
    },
    onError: (e) => {
      setError(e instanceof Error ? e.message : t("common.unknownError"));
    },
  });

  // Petit fallback si la version arrive pas encore
  const currentVersion = versionQuery.data?.version;

  const isReturningUser = user.terms_version_accepted !== null;

  return (
    <Dialog open={true}>
      <DialogContent
        // Cache le bouton X interne de DialogContent (shadcn). Modal
        // non-fermable : refus = bouton "Décliner et se déconnecter".
        className="max-w-lg [&>button.absolute]:hidden"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>
            {isReturningUser ? t("terms.updateTitle") : t("terms.welcomeTitle")}
          </DialogTitle>
          <DialogDescription className="pt-2 text-sm leading-relaxed">
            {isReturningUser ? t("terms.updateBody") : t("terms.welcomeBody")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-md border bg-muted/30 p-3 text-sm">
            <p className="mb-1 font-medium">{t("terms.keyPoints")}</p>
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              <li>{t("terms.point1")}</li>
              <li>{t("terms.point2")}</li>
              <li>{t("terms.point3")}</li>
            </ul>
          </div>

          <label className="flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors hover:bg-muted/30">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 h-4 w-4 cursor-pointer rounded border-border accent-foreground"
            />
            <span className="text-sm leading-relaxed">
              {t("terms.iAccept")}{" "}
              <a
                href="/legal/terms.html"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline underline-offset-2 hover:text-foreground"
              >
                {t("terms.termsLink")}
              </a>{" "}
              {t("terms.andThe")}{" "}
              <a
                href="/legal/privacy.html"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline underline-offset-2 hover:text-foreground"
              >
                {t("terms.privacyLink")}
              </a>
              {currentVersion && (
                <span className="text-muted-foreground">
                  {" "}
                  {t("terms.version", { version: currentVersion })}
                </span>
              )}
              .
            </span>
          </label>

          {error && <p className="text-sm text-[hsl(var(--loss))]">{error}</p>}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={() => logout.mutate()}
            disabled={mutation.isPending}
            className="text-muted-foreground"
          >
            {t("terms.decline")}
          </Button>
          <Button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={!checked || mutation.isPending || !currentVersion}
          >
            {mutation.isPending ? t("terms.accepting") : t("terms.accept")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
