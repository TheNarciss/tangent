import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_PATHS } from "@/components/Sidebar";

const REASONS: Record<string, string> = {
  no_linked_accounts:
    "La banque a répondu, mais aucun de ses comptes n'est lié à l'application dans la console Enable Banking.",
  session: "Enable Banking n'a pas pu ouvrir la session. Réessaie.",
  bad_state: "Le retour de la banque n'a pas pu être vérifié. Réessaie.",
  wrong_user: "Le retour de la banque concerne un autre compte Tangent.",
  encryption_not_configured: "Le serveur ne peut pas chiffrer la session (clé manquante).",
};

/** After the bank's consent screen: the server already read the accounts; refresh and land on Comptes. */
export function EnableBankingCallbackHandler() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    const params = new URLSearchParams(search);
    const status = params.get("enablebanking");
    if (!status) return;
    hasRun.current = true;

    if (status === "success") {
      for (const key of [
        "enablebanking",
        "bank-accounts",
        "bank-connections",
        "wealth",
        "transactions",
        "spending",
        "dashboard",
        "timeseries",
        "verdicts",
      ]) {
        qc.invalidateQueries({ queryKey: [key] });
      }
      navigate(NAV_PATHS.accounts, { replace: true });
    } else {
      navigate(pathname, { replace: true });
      const reason = params.get("error") || "unknown";
      window.alert(REASONS[reason] ?? `La connexion à la banque a échoué (${reason}).`);
    }
  }, [qc, navigate, pathname, search]);

  return null;
}
