import { useState } from "react";
import { Banknote, RefreshCw } from "lucide-react";

import {
  useBankAccounts,
  useAccountHoldings,
  useAccountTransactions,
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

export function Accounts() {
  const accounts = useBankAccounts();
  const sync = useSyncBankAccounts();
  const [selected, setSelected] = useState<BankAccountResponse | null>(null);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Mes comptes
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => sync.mutate()}
            disabled={sync.isPending}
            className="gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", sync.isPending && "animate-spin")} />
            Synchroniser
          </Button>
        </CardHeader>
        <CardContent>
          {sync.isError && (
            <p className="text-sm text-[hsl(var(--loss))] mb-3">
              Erreur sync : {sync.error instanceof Error ? sync.error.message : "inconnue"}
            </p>
          )}
          {sync.data && sync.data.success && (
            <p className="text-xs text-muted-foreground mb-3">
              Dernière sync : {sync.data.accounts_persisted} comptes, {sync.data.holdings_persisted}{" "}
              positions, {sync.data.transactions_persisted} nouvelles transactions.
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
          {accounts.data && accounts.data.length > 0 && (
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
                {accounts.data.map((a) => (
                  <TableRow
                    key={a.id}
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
                ))}
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
