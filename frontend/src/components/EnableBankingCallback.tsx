import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_PATHS } from "@/components/Sidebar";
import { useT, type MessageKey } from "@/i18n";

const COMMON: Record<string, MessageKey> = {
  bad_state: "system.eb.badState",
  wrong_user: "system.eb.wrongUser",
  encryption_not_configured: "system.eb.encryptionNotConfigured",
};

const EB_REASONS: Record<string, MessageKey> = {
  ...COMMON,
  no_linked_accounts: "system.eb.noLinkedAccounts",
  session: "system.eb.session",
};

const FINVERSE_REASONS: Record<string, MessageKey> = {
  ...COMMON,
  exchange: "system.fv.exchange",
  bank_read: "system.fv.bankRead",
};

/** After the bank's consent screen: the server already read the accounts; refresh and land on Comptes. */
export function EnableBankingCallbackHandler() {
  useBankReturn("enablebanking", EB_REASONS);
  return null;
}

/** Back from Finverse Link (ADR-037), the same way. */
export function FinverseCallbackHandler() {
  useBankReturn("finverse", FINVERSE_REASONS);
  return null;
}

/** `?<param>=success` refreshes what the new accounts touch; anything else says why it failed. */
function useBankReturn(param: string, reasons: Record<string, MessageKey>) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const hasRun = useRef(false);
  const { t } = useT();

  useEffect(() => {
    if (hasRun.current) return;
    const params = new URLSearchParams(search);
    const status = params.get(param);
    if (!status) return;
    hasRun.current = true;

    if (status === "success") {
      for (const key of [
        param,
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
      const key = reasons[reason];
      window.alert(key ? t(key) : t("system.eb.failed", { reason }));
    }
  }, [qc, navigate, pathname, search, t, param, reasons]);
}
