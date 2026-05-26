import { useEffect, useMemo, useRef, useState } from "react";
import { Banknote, ChevronRight, RefreshCw, Zap } from "lucide-react";

import {
  useBankAccounts,
  useAccountHoldings,
  useAccountTransactions,
  useRefreshBankAccounts,
  useSyncBankAccounts,
  type BankAccountResponse,
  type BankAccountType,
} from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const TYPE_LABELS: Record<BankAccountType, string> = {
  checking: "Courant",
  savings: "Épargne",
  pea: "PEA",
  cto: "CTO",
  life_insurance: "Assurance vie",
  loan: "Prêt",
  card: "Carte",
  crypto: "Crypto",
  other: "Autre",
};

const INVESTMENT_TYPES: BankAccountType[] = ["pea", "cto", "life_insurance"];
const TRANSACTION_TYPES: BankAccountType[] = ["checking", "savings", "card"];

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "il y a quelques minutes";
  if (hours < 24) return `il y a ${hours}h`;
  const days = Math.floor(hours / 24);
  return `il y a ${days}j`;
}

type AccountGroup =
  | { kind: "single"; key: string; account: BankAccountResponse }
  | {
      kind: "bundle";
      key: string;
      label: string;
      institution: string | null;
      type: BankAccountType;
      accounts: BankAccountResponse[];
      totalBalance: number;
      latestSync: string | null;
    };

function groupAccounts(accounts: BankAccountResponse[]): AccountGroup[] {
  const peaByInstitution = new Map<string, BankAccountResponse[]>();
  const others: BankAccountResponse[] = [];

  for (const acc of accounts) {
    if (acc.type === "pea") {
      const key = acc.institution_name ?? "_unknown";
      if (!peaByInstitution.has(key)) peaByInstitution.set(key, []);
      peaByInstitution.get(key)!.push(acc);
    } else {
      others.push(acc);
    }
  }

  const groups: AccountGroup[] = [];

  for (const [inst, peas] of peaByInstitution) {
    if (peas.length === 1) {
      groups.push({ kind: "single", key: peas[0].id, account: peas[0] });
    } else {
      const totalBalance = peas.reduce((s, a) => s + a.balance, 0);
      const latestSync =
        peas
          .map((a) => a.last_synced_at)
          .filter((s): s is string => !!s)
          .sort()
          .reverse()[0] ?? null;
      groups.push({
        kind: "bundle",
        key: `pea-${inst}`,
        label: inst === "_unknown" ? "PEA" : `PEA · ${inst}`,
        institution: inst === "_unknown" ? null : inst,
        type: "pea",
        accounts: peas,
        totalBalance,
        latestSync,
      });
    }
  }

  for (const acc of others) {
    groups.push({ kind: "single", key: acc.id, account: acc });
  }

  return groups;
}

export function Accounts() {
  const accounts = useBankAccounts();
  const sync = useSyncBankAccounts();
  const refresh = useRefreshBankAccounts();
  const [selected, setSelected] = useState<BankAccountResponse | null>(null);
  const [expandedBundles, setExpandedBundles] = useState<Set<string>>(new Set());

  // Auto-sync at mount, but only if user already has accounts (= Powens connected).
  // Backend cache (5 min) absorbs spam — calling /sync repeatedly is cheap.
  const autoSyncDoneRef = useRef(false);
  useEffect(() => {
    if (autoSyncDoneRef.current) return;
    if (!accounts.data || accounts.data.length === 0) return;
    autoSyncDoneRef.current = true;
    sync.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accounts.data]);

  const groups = useMemo(() => groupAccounts(accounts.data ?? []), [accounts.data]);

  const toggleBundle = (key: string) => {
    setExpandedBundles((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const syncBusy = sync.isPending || refresh.isPending;
  const syncError = sync.isError || refresh.isError;
  const syncErrorMessage = refresh.isError
    ? refresh.error instanceof Error
      ? refresh.error.message
      : "inconnue"
    : sync.error instanceof Error
      ? sync.error.message
      : "inconnue";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Mes comptes
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => sync.mutate()}
              disabled={syncBusy}
              className="gap-2"
              title="Lit le cache Powens (rapide, 5 min de TTL)"
            >
              <RefreshCw className={cn("h-4 w-4", sync.isPending && "animate-spin")} />
              Synchroniser
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refresh.mutate()}
              disabled={syncBusy}
              className="gap-2"
              title="Force Powens à re-contacter la banque (lent, ~15s)"
            >
              <Zap className={cn("h-4 w-4", refresh.isPending && "animate-pulse")} />
              {refresh.isPending ? "Connexion banque…" : "Forcer banque"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {syncError && (
            <p className="text-sm text-[hsl(var(--loss))] mb-3">Erreur sync : {syncErrorMessage}</p>
          )}
          {refresh.data && refresh.data.success && (
            <p className="text-xs text-muted-foreground mb-3">
              Refresh forcé OK · {refresh.data.accounts_persisted} comptes ·{" "}
              {refresh.data.holdings_persisted} positions
            </p>
          )}
          {sync.data && sync.data.success && !refresh.data && (
            <p className="text-xs text-muted-foreground mb-3">
              {sync.data.from_cache ? (
                <>
                  Affichage du cache (sync &lt; 5 min). Bouton « Forcer banque » pour fraîcheur
                  garantie.
                </>
              ) : (
                <>
                  Dernière sync : {sync.data.accounts_persisted} comptes,{" "}
                  {sync.data.holdings_persisted} positions, {sync.data.transactions_persisted}{" "}
                  nouvelles transactions.
                </>
              )}
            </p>
          )}

          {accounts.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
          {accounts.isError && (
            <p className="text-sm text-[hsl(var(--loss))]">
              Erreur : {accounts.error instanceof Error ? accounts.error.message : "inconnue"}
            </p>
          )}
          {accounts.data && accounts.data.length === 0 && (
            <div className="text-center py-12 space-y-2">
              <Banknote className="h-8 w-8 mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Aucun compte synchronisé. Connecte Powens et clique sur Synchroniser.
              </p>
            </div>
          )}
          {groups.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Banque</TableHead>
                  <TableHead className="text-right">Solde</TableHead>
                  <TableHead className="text-right">Dernière sync</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groups.map((g) => {
                  if (g.kind === "single") {
                    const a = g.account;
                    return (
                      <TableRow
                        key={g.key}
                        onClick={() => setSelected(selected?.id === a.id ? null : a)}
                        className={cn("cursor-pointer", selected?.id === a.id && "bg-accent")}
                      >
                        <TableCell className="font-medium">{a.name}</TableCell>
                        <TableCell>{TYPE_LABELS[a.type]}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {a.institution_name ?? "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular">
                          {fmt.eur(a.balance)}
                        </TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground">
                          {relativeTime(a.last_synced_at)}
                        </TableCell>
                      </TableRow>
                    );
                  }

                  const isExpanded = expandedBundles.has(g.key);
                  return (
                    <>
                      <TableRow
                        key={g.key}
                        onClick={() => toggleBundle(g.key)}
                        className="cursor-pointer hover:bg-accent/50"
                      >
                        <TableCell className="font-medium">
                          <span className="inline-flex items-center gap-1.5">
                            <ChevronRight
                              className={cn(
                                "h-3.5 w-3.5 transition-transform",
                                isExpanded && "rotate-90",
                              )}
                            />
                            {g.label}
                            <span className="text-xs text-muted-foreground font-normal ml-1">
                              ({g.accounts.length} sous-comptes)
                            </span>
                          </span>
                        </TableCell>
                        <TableCell>{TYPE_LABELS[g.type]}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {g.institution ?? "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular font-medium">
                          {fmt.eur(g.totalBalance)}
                        </TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground">
                          {relativeTime(g.latestSync)}
                        </TableCell>
                      </TableRow>
                      {isExpanded &&
                        g.accounts.map((sub) => (
                          <TableRow
                            key={sub.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(selected?.id === sub.id ? null : sub);
                            }}
                            className={cn(
                              "cursor-pointer bg-muted/30",
                              selected?.id === sub.id && "bg-accent",
                            )}
                          >
                            <TableCell className="pl-9 text-sm text-muted-foreground">
                              ↳ {sub.name}
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {TYPE_LABELS[sub.type]}
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">—</TableCell>
                            <TableCell className="text-right font-mono tabular text-sm">
                              {fmt.eur(sub.balance)}
                            </TableCell>
                            <TableCell className="text-right text-xs text-muted-foreground">
                              {relativeTime(sub.last_synced_at)}
                            </TableCell>
                          </TableRow>
                        ))}
                    </>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selected && INVESTMENT_TYPES.includes(selected.type) && (
        <AccountHoldings account={selected} />
      )}
      {selected && TRANSACTION_TYPES.includes(selected.type) && (
        <AccountTransactions account={selected} />
      )}
    </div>
  );
}

function AccountHoldings({ account }: { account: BankAccountResponse }) {
  const holdings = useAccountHoldings(account.id);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          {account.name} · Positions
        </CardTitle>
      </CardHeader>
      <CardContent>
        {holdings.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {holdings.data && holdings.data.length === 0 && (
          <p className="text-sm text-muted-foreground">Aucune position.</p>
        )}
        {holdings.data && holdings.data.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead>Libellé</TableHead>
                <TableHead className="text-right">Quantité</TableHead>
                <TableHead className="text-right">PRU</TableHead>
                <TableHead className="text-right">Valorisation</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {holdings.data.map((h) => (
                <TableRow key={h.id}>
                  <TableCell className="font-mono font-medium">{h.ticker}</TableCell>
                  <TableCell className="text-muted-foreground">{h.label}</TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.num(h.quantity)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.eur(h.unit_price)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {fmt.eur(h.current_value)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function AccountTransactions({ account }: { account: BankAccountResponse }) {
  const txs = useAccountTransactions(account.id, 50);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          {account.name} · 50 dernières transactions
        </CardTitle>
      </CardHeader>
      <CardContent>
        {txs.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {txs.data && txs.data.length === 0 && (
          <p className="text-sm text-muted-foreground">Aucune transaction.</p>
        )}
        {txs.data && txs.data.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Libellé</TableHead>
                <TableHead>Catégorie</TableHead>
                <TableHead className="text-right">Montant</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {txs.data.map((t) => {
                const positive = t.amount >= 0;
                return (
                  <TableRow key={t.id}>
                    <TableCell className="font-mono tabular text-xs">
                      {new Date(t.transaction_date).toLocaleDateString("fr-FR")}
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">{t.description}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {t.category ?? "—"}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono tabular",
                        positive ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                      )}
                    >
                      {fmt.signedEur(t.amount)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
