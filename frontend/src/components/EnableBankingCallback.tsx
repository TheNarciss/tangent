import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_PATHS } from "@/components/Sidebar";
import { useT, type MessageKey } from "@/i18n";

const REASONS: Record<string, MessageKey> = {
  no_linked_accounts: "system.eb.noLinkedAccounts",
  session: "system.eb.session",
  bad_state: "system.eb.badState",
  wrong_user: "system.eb.wrongUser",
  encryption_not_configured: "system.eb.encryptionNotConfigured",
};

/** After the bank's consent screen: the server already read the accounts; refresh and land on Comptes. */
export function EnableBankingCallbackHandler() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const hasRun = useRef(false);
  const { t } = useT();

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
      const key = REASONS[reason];
      window.alert(key ? t(key) : t("system.eb.failed", { reason }));
    }
  }, [qc, navigate, pathname, search, t]);

  return null;
}
