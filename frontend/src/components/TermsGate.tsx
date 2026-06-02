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
      setError(e instanceof Error ? e.message : "Erreur inconnue");
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
            {isReturningUser ? "Mise à jour de nos conditions" : "Bienvenue sur Tangent"}
          </DialogTitle>
          <DialogDescription className="pt-2 text-sm leading-relaxed">
            {isReturningUser ? (
              <>
                Nos Conditions d&apos;utilisation et/ou notre Politique de confidentialité ont
                évolué depuis votre dernière acceptation. Merci de les relire avant de continuer.
              </>
            ) : (
              <>
                Avant d&apos;utiliser Tangent, merci de prendre connaissance de nos Conditions
                d&apos;utilisation et de notre Politique de confidentialité.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-md border bg-muted/30 p-3 text-sm">
            <p className="mb-1 font-medium">À retenir</p>
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              <li>
                Tangent est un outil d&apos;analyse — pas un conseil en investissement régulé.
              </li>
              <li>
                Vos données ne sont jamais vendues, partagées à des fins publicitaires, ou utilisées
                pour entraîner de l&apos;IA tierce.
              </li>
              <li>Vous pouvez supprimer votre compte à tout moment (effacement immédiat).</li>
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
              J&apos;ai lu et j&apos;accepte les{" "}
              <a
                href="/legal/terms.html"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline underline-offset-2 hover:text-foreground"
              >
                Conditions d&apos;utilisation
              </a>{" "}
              et la{" "}
              <a
                href="/legal/privacy.html"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline underline-offset-2 hover:text-foreground"
              >
                Politique de confidentialité
              </a>
              {currentVersion && (
                <span className="text-muted-foreground"> (version {currentVersion})</span>
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
            Décliner et se déconnecter
          </Button>
          <Button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={!checked || mutation.isPending || !currentVersion}
          >
            {mutation.isPending ? "Acceptation…" : "Accepter et continuer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
