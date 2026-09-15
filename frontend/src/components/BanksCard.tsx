import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  fetchBankConnections,
  startEnableBankingAuth,
  unlinkBankConnection,
  unlinkEnableBankingSession,
  useEnableBankingSessions,
} from "@/api";
import { useT } from "@/i18n";
import { formatDate, relativeTime } from "@/lib/accounts";
import { openExternalFlow, platform } from "@/native/flows";
import { Button } from "@/components/ui/button";

/**
 * « Mes banques » — the connections behind the accounts, managed from the
 * Comptes screen (add is the header button, unlink here, errors shown here).
 */
export function BanksCard() {
  const { t } = useT();
  const connections = useQuery({ queryKey: ["bank-connections"], queryFn: fetchBankConnections });
  const sessions = useEnableBankingSessions();
  const nothing =
    connections.data &&
    connections.data.length === 0 &&
    sessions.data &&
    sessions.data.length === 0;

  return (
    <section className="rounded-xl border bg-card p-4 md:p-6">
      <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
        {t("accounts.banks.title")}
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">{t("accounts.banks.desc")}</p>
      <div className="mt-3 space-y-2">
        {connections.isLoading && (
          <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
        )}
        {connections.isError && (
          <p className="text-sm text-[hsl(var(--loss))]">{t("accounts.banks.loadFailed")}</p>
        )}
        {nothing && (
          <p className="text-sm text-muted-foreground">
            {t("accounts.banks.emptyBefore")}
            <strong>{t("accounts.empty.addBank")}</strong>
            {t("accounts.banks.emptyAfter")}
          </p>
        )}
        {sessions.data?.map((s) => (
          <EnableBankingRow
            key={s.id}
            id={s.id}
            name={s.bank_name}
            accountsCount={s.accounts_count}
            validUntil={s.valid_until}
            expired={s.expired}
            lastSync={s.last_sync_at}
            error={s.last_error}
          />
        ))}
        {connections.data?.map((conn) => (
          <BankRow
            key={conn.connection_id}
            connectionId={conn.connection_id}
            name={conn.institution_name}
            accountsCount={conn.accounts_count}
            lastUpdate={conn.last_update}
            hasError={!!conn.error}
          />
        ))}
      </div>
    </section>
  );
}

function BankRow({
  connectionId,
  name,
  accountsCount,
  lastUpdate,
  hasError,
}: {
  connectionId: number;
  name: string;
  accountsCount: number;
  lastUpdate: string | null;
  hasError: boolean;
}) {
  const { t, tn } = useT();
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unlink = useMutation({
    mutationFn: () => unlinkBankConnection(connectionId),
    onSuccess: () => {
      for (const key of ["bank-connections", "bank-accounts", "wealth", "dashboard"]) {
        qc.invalidateQueries({ queryKey: [key] });
      }
      setConfirming(false);
    },
    onError: (e) => setError(e instanceof Error ? e.message : t("accounts.unknownError")),
  });

  return (
    <div className="rounded-md border px-3 py-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-[12rem] flex-1">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">
            {t("accounts.banks.summary", {
              accounts: tn("accounts.banks.count", accountsCount),
              when: relativeTime(lastUpdate),
            })}
            {hasError && (
              <span className="ml-2 text-[hsl(var(--loss))]">
                {t("accounts.banks.reconnectNeeded")}
              </span>
            )}
          </p>
        </div>
        {!confirming && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setConfirming(true)}
            className="ml-auto shrink-0"
          >
            {t("accounts.banks.remove")}
          </Button>
        )}
      </div>
      {confirming && (
        <div className="mt-2 flex flex-wrap items-center justify-end gap-2 text-xs">
          <span className="mr-auto text-muted-foreground">
            {t("accounts.banks.removeConfirm", {
              name,
              accounts: tn("accounts.banks.count", accountsCount),
            })}
          </span>
          <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => unlink.mutate()}
            disabled={unlink.isPending}
          >
            {unlink.isPending ? t("accounts.banks.removing") : t("accounts.banks.remove")}
          </Button>
        </div>
      )}
      {error && <p className="mt-1 text-xs text-[hsl(var(--loss))]">{error}</p>}
    </div>
  );
}

function EnableBankingRow({
  id,
  name,
  accountsCount,
  validUntil,
  expired,
  lastSync,
  error,
}: {
  id: string;
  name: string;
  accountsCount: number;
  validUntil: string;
  expired: boolean;
  lastSync: string | null;
  error: string | null;
}) {
  const { t, tn } = useT();
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const invalidate = () => {
    for (const key of ["enablebanking", "bank-accounts", "wealth", "dashboard", "spending"]) {
      qc.invalidateQueries({ queryKey: [key] });
    }
  };
  const unlink = useMutation({
    mutationFn: () => unlinkEnableBankingSession(id),
    onSuccess: () => {
      invalidate();
      setConfirming(false);
    },
    onError: (e) => setFailure(e instanceof Error ? e.message : t("accounts.unknownError")),
  });
  const navigate = useNavigate();
  const reconnect = async () => {
    setBusy(true);
    try {
      await openExternalFlow(await startEnableBankingAuth(name, "FR", platform()), navigate);
      setBusy(false);
    } catch (e) {
      setFailure(e instanceof Error ? e.message : t("accounts.unknownError"));
      setBusy(false);
    }
  };
  const until = formatDate(validUntil, { day: "numeric", month: "long" });

  return (
    <div className="rounded-md border px-3 py-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-[12rem] flex-1">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">
            {t("accounts.banks.summary", {
              accounts: tn("accounts.banks.count", accountsCount),
              when: relativeTime(lastSync),
            })}
            {expired ? (
              <span className="ml-2 text-[hsl(var(--loss))]">
                {t("accounts.banks.consentExpired")}
              </span>
            ) : (
              <span className="ml-2">{t("accounts.banks.consentUntil", { date: until })}</span>
            )}
          </p>
          {!expired && error && (
            <p className="mt-0.5 break-words text-xs text-[hsl(var(--loss))]">
              {t("accounts.banks.lastFetchFailed", { error })}
            </p>
          )}
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-1">
          {expired && (
            <Button variant="outline" size="sm" onClick={reconnect} disabled={busy}>
              {busy ? t("accounts.addBank.redirecting") : t("accounts.banks.reconnect")}
            </Button>
          )}
          {!confirming && (
            <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
              {t("accounts.banks.remove")}
            </Button>
          )}
        </div>
      </div>
      {confirming && (
        <div className="mt-2 flex flex-wrap items-center justify-end gap-2 text-xs">
          <span className="mr-auto text-muted-foreground">
            {t("accounts.banks.removeConfirm", {
              name,
              accounts: tn("accounts.banks.count", accountsCount),
            })}
          </span>
          <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => unlink.mutate()}
            disabled={unlink.isPending}
          >
            {unlink.isPending ? t("accounts.banks.removing") : t("accounts.banks.remove")}
          </Button>
        </div>
      )}
      {failure && <p className="mt-1 text-xs text-[hsl(var(--loss))]">{failure}</p>}
    </div>
  );
}
