import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

/** Detects ?oauth=success or ?oauth_error=NNN in the URL after the Google
 *  OAuth callback (cf ADR-014). Cleans the URL and triggers a user refetch
 *  so the App promotes from AuthScreen to Dashboard immediately. */
export function OAuthCallbackHandler() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;

    const params = new URLSearchParams(search);
    const success = params.get("oauth");
    const errorCode = params.get("oauth_error");
    if (!success && !errorCode) return;
    hasRun.current = true;

    // Clean URL immediately (replace) so a refresh doesn't re-trigger
    navigate(pathname, { replace: true });

    if (success === "success") {
      // Cookie is set by backend. Refetch user to flip App to Dashboard.
      qc.invalidateQueries({ queryKey: ["user", "me"] });
    } else if (errorCode) {
      // Show a friendly message; nothing fancy yet
      // (codes : 400 = email non vérifié / state invalide, 409 = sub déjà pris,
      //  401 = pas loggé pour /associate, etc.)
      window.alert(
        `Connexion Google échouée (code ${errorCode}). ` +
          "Réessaie, ou contacte le support si le problème persiste.",
      );
    }
  }, [qc, navigate, pathname, search]);

  return null;
}
