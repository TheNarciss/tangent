import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Banknote,
  Building2,
  ChevronDown,
  ChevronRight,
  Landmark,
  PiggyBank,
  RefreshCw,
  TrendingUp,
  Wallet,
} from "lucide-react";

import {
  useBankAccounts,
  useAccountHoldings,
  useAccountTransactions,
  useUpdateHoldingTer,
  useRefreshBankAccounts,
  type BankAccountResponse,
  type BankAccountType,
  type LoanResponse,
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
import { DataField } from "@/components/ui/data-field";

/* ── Categories & labels ──────────────────────────────────────────────────── */

type Category = "cash" | "savings" | "invest" | "retirement" | "employee" | "loan" | "other";

const CATEGORY_LABELS: Record<Category, string> = {
  cash: "Comptes courants",
  savings: "Épargne",
  invest: "Investissement",
  retirement: "Retraite",
  employee: "Épargne salariale",
  loan: "Prêts",
  other: "Autres",
};

const CATEGORY_ORDER: Category[] = [
  "cash",
  "savings",
  "invest",
  "retirement",
  "employee",
  "loan",
  "other",
];

const CATEGORY_ICON: Record<Category, typeof Wallet> = {
  cash: Wallet,
  savings: PiggyBank,
  invest: TrendingUp,
  retirement: Landmark,
  employee: Building2,
  loan: Banknote,
  other: Banknote,
};

const TYPE_LABELS: Record<BankAccountType, string> = {
  checking: "Courant",
  card: "Carte",
  joint: "Joint",
  savings: "Épargne",
  livret_a: "Livret A",
  livret_b: "Livret B",
  ldds: "LDDS",
  lep: "LEP",
  pel: "PEL",
  cel: "CEL",
  csl: "CSL",
  cat: "CAT",
  deposit: "Dépôt",
  pea: "PEA",
  cto: "CTO",
  life_insurance: "Assurance vie",
  capitalisation: "Capitalisation",
  real_estate: "Immobilier",
  crowdlending: "Crowdlending",
  per: "PER",
  perp: "PERP",
  perco: "PERCO",
  madelin: "Madelin",
  article_83: "Art. 83",
  pee: "PEE",
  rsp: "RSP",
  loan: "Prêt",
  mortgage: "Prêt immo",
  consumer_credit: "Crédit conso",
  revolving_credit: "Revolving",
  crypto: "Crypto",
  other: "Autre",
};

const INVESTMENT_TYPES: BankAccountType[] = [
  "pea",
  "cto",
  "life_insurance",
  "capitalisation",
  "per",
  "perp",
  "perco",
  "madelin",
  "article_83",
  "pee",
  "rsp",
  "real_estate",
  "crowdlending",
];

const TRANSACTION_TYPES: BankAccountType[] = [
  "checking",
  "savings",
  "card",
  "joint",
  "livret_a",
  "livret_b",
  "ldds",
  "lep",
  "pel",
  "cel",
  "csl",
  "cat",
  "deposit",
];

function categorize(type: BankAccountType): Category {
  switch (type) {
    case "checking":
    case "card":
    case "joint":
      return "cash";
    case "savings":
    case "livret_a":
    case "livret_b":
    case "ldds":
    case "lep":
    case "pel":
    case "cel":
    case "csl":
    case "cat":
    case "deposit":
      return "savings";
    case "pea":
    case "cto":
    case "life_insurance":
    case "capitalisation":
    case "real_estate":
    case "crowdlending":
      return "invest";
    case "per":
    case "perp":
    case "perco":
    case "madelin":
    case "article_83":
      return "retirement";
    case "pee":
    case "rsp":
      return "employee";
    case "loan":
    case "mortgage":
    case "consumer_credit":
    case "revolving_credit":
      return "loan";
    default:
      return "other";
  }
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function cleanName(name: string): string {
  const words = name.split(/\s+/);
  const seen = new Set<string>();
  return words
    .filter((w) => {
      const k = w.toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .join(" ");
}

function maskedIban(iban: string | null): string {
  if (!iban) return "—";
  return `•••• ${iban.slice(-4)}`;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}j`;
}

const MONTH_FR = [
  "janv.",
  "févr.",
  "mars",
  "avr.",
  "mai",
  "juin",
  "juil.",
  "août",
  "sept.",
  "oct.",
  "nov.",
  "déc.",
];

function monthYear(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${MONTH_FR[d.getMonth()]} ${d.getFullYear()}`;
}

function formatRate(rate: number): string {
  return `${rate.toFixed(2).replace(".", ",")} %`;
}

function categoryTotal(accounts: BankAccountResponse[], category: Category): number {
  return accounts.reduce((sum, a) => {
    if (category === "invest" || category === "retirement" || category === "employee") {
      return sum + (a.valuation ?? a.balance);
    }
    if (category === "loan") {
      return sum + (a.loan?.used_amount ?? Math.abs(a.balance));
    }
    return sum + a.balance;
  }, 0);
}

/* ── Root component ───────────────────────────────────────────────────────── */

export function Accounts() {
  const accounts = useBankAccounts();
  const refresh = useRefreshBankAccounts();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Synchronous in-flight guard — closes the race window between
  // refresh.mutate() being called and React Query's isPending state
  // propagating to the next render. Without it, two rapid sources
  // (double-click, touchscreen, manual click while the auto-refresh
  // useEffect is in flight) can both pass the disabled/isPending check
  // and trigger two parallel POST /accounts/refresh. Cf Bug 2 of
  // SESSION_RECAP_2026-05-31.md.
  const syncInFlight = useRef(false);
  const startSync = useCallback(() => {
    if (syncInFlight.current) return;
    syncInFlight.current = true;
    refresh.mutate(undefined, {
      onSettled: () => {
        syncInFlight.current = false;
      },
    });
  }, [refresh]);

  // AUTO-REFRESH au mount si stale (oldest last_synced_at > 5 min).
  // Garantit data fraîche à l'arrivée sans hammer Powens à chaque mount.
  const STALENESS_MINUTES = 5;
  const didAutoRefresh = useRef(false);
  useEffect(() => {
    if (didAutoRefresh.current) return;
    if (!accounts.data || accounts.data.length === 0) return;

    const syncTimes = accounts.data
      .map((a) => a.last_synced_at)
      .filter((ts): ts is string => ts !== null)
      .map((ts) => new Date(ts).getTime());

    const isStale =
      syncTimes.length === 0 || (Date.now() - Math.min(...syncTimes)) / 60_000 > STALENESS_MINUTES;

    if (isStale) {
      didAutoRefresh.current = true;
      startSync();
    }
  }, [accounts.data, startSync]);

  const grouped = useMemo(() => {
    const out: Record<Category, BankAccountResponse[]> = {
      cash: [],
      savings: [],
      invest: [],
      retirement: [],
      employee: [],
      loan: [],
      other: [],
    };
    for (const a of accounts.data ?? []) {
      out[categorize(a.type)].push(a);
    }
    return out;
  }, [accounts.data]);

  const netWorth = useMemo(() => {
    const assets =
      categoryTotal(grouped.cash, "cash") +
      categoryTotal(grouped.savings, "savings") +
      categoryTotal(grouped.invest, "invest") +
      categoryTotal(grouped.retirement, "retirement") +
      categoryTotal(grouped.employee, "employee");
    const debt = categoryTotal(grouped.loan, "loan");
    return { assets, debt, net: assets - debt };
  }, [grouped]);

  const isSyncing = refresh.isPending;
  const lastReport = refresh.data;

  return (
    <div className="space-y-4">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Mes comptes
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={startSync}
            disabled={isSyncing || !accounts.data || accounts.data.length === 0}
            className="gap-2"
            title="Force la banque à renvoyer les dernières données (10-30s)"
          >
            <RefreshCw className={cn("h-4 w-4", isSyncing && "animate-spin")} />
            {isSyncing ? "Sync…" : "Sync"}
          </Button>
        </CardHeader>
        <CardContent>
          {refresh.isError && (
            <p className="text-sm text-[hsl(var(--loss))] mb-3">
              Erreur sync : {refresh.error instanceof Error ? refresh.error.message : "inconnue"}
            </p>
          )}
          {lastReport && lastReport.success && (
            <p className="text-xs text-muted-foreground mb-3">
              {lastReport.from_cache ? "Cache · " : ""}
              {lastReport.accounts_persisted} comptes, {lastReport.holdings_persisted} positions,{" "}
              {lastReport.transactions_persisted} nouvelles transactions
            </p>
          )}

          {accounts.data && accounts.data.length > 0 && (
            <div className="grid grid-cols-3 gap-4 pt-2">
              <NetWorthTile label="Actifs" value={netWorth.assets} />
              <NetWorthTile label="Dettes" value={-netWorth.debt} negative />
              <NetWorthTile label="Net" value={netWorth.net} bold />
            </div>
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
                Aucune banque connectée pour l&apos;instant.
              </p>
              <p className="text-xs text-muted-foreground">
                Clique sur <strong>+ Ajouter une banque</strong> en haut de la page pour commencer.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Sections by category ────────────────────────────────────────── */}
      {accounts.data &&
        accounts.data.length > 0 &&
        CATEGORY_ORDER.map((cat) => {
          const list = grouped[cat];
          if (list.length === 0) return null;
          return (
            <AccountSection
              key={cat}
              category={cat}
              accounts={list}
              selectedId={selectedId}
              onToggle={(id) => setSelectedId((prev) => (prev === id ? null : id))}
            />
          );
        })}
    </div>
  );
}

/* ── Net worth tile ───────────────────────────────────────────────────────── */

function NetWorthTile({
  label,
  value,
  negative,
  bold,
}: {
  label: string;
  value: number;
  negative?: boolean;
  bold?: boolean;
}) {
  const colorClass = negative || value < 0 ? "text-[hsl(var(--loss))]" : "text-foreground";
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("text-lg font-mono tabular", colorClass, bold && "font-semibold")}>
        {fmt.signedEur(value)}
      </div>
    </div>
  );
}

/* ── Section ──────────────────────────────────────────────────────────────── */

function AccountSection({
  category,
  accounts,
  selectedId,
  onToggle,
}: {
  category: Category;
  accounts: BankAccountResponse[];
  selectedId: string | null;
  onToggle: (id: string) => void;
}) {
  const Icon = CATEGORY_ICON[category];
  const total = categoryTotal(accounts, category);
  const isDebt = category === "loan";

  return (
    <Card>
      <CardHeader className="flex flex-row items-baseline justify-between py-3">
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {CATEGORY_LABELS[category]}
          <span className="text-xs text-muted-foreground/70 normal-case">({accounts.length})</span>
        </CardTitle>
        <span className={cn("text-sm font-mono tabular", isDebt && "text-[hsl(var(--loss))]")}>
          {isDebt ? `−${fmt.eur(total)}` : fmt.eur(total)}
        </span>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>Nom</TableHead>
              <TableHead>Banque</TableHead>
              <TableHead>{category === "loan" ? "Capital restant" : "Solde"}</TableHead>
              <SecondaryColumnHead category={category} />
              <TableHead className="text-right text-xs">Sync</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {accounts.map((a) => (
              <AccountRowGroup
                key={a.id}
                account={a}
                category={category}
                isOpen={selectedId === a.id}
                onToggle={() => onToggle(a.id)}
              />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function SecondaryColumnHead({ category }: { category: Category }) {
  if (category === "invest" || category === "retirement" || category === "employee") {
    return <TableHead>Gain / perte</TableHead>;
  }
  if (category === "loan") {
    return <TableHead>Taux · Échéance</TableHead>;
  }
  return <TableHead className="text-muted-foreground">IBAN</TableHead>;
}

/* ── Row + inline accordion ───────────────────────────────────────────────── */

function AccountRowGroup({
  account,
  category,
  isOpen,
  onToggle,
}: {
  account: BankAccountResponse;
  category: Category;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const expandable =
    INVESTMENT_TYPES.includes(account.type) ||
    TRANSACTION_TYPES.includes(account.type) ||
    category === "loan";

  return (
    <>
      <TableRow
        onClick={expandable ? onToggle : undefined}
        className={cn("min-h-[44px]", expandable && "cursor-pointer", isOpen && "bg-accent/30")}
      >
        <TableCell className="w-8">
          {expandable ? (
            isOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          ) : null}
        </TableCell>
        <TableCell className="font-medium">
          <div className="flex items-center gap-2">
            <span className="truncate">{cleanName(account.name)}</span>
            <span className="shrink-0 text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {TYPE_LABELS[account.type]}
            </span>
          </div>
        </TableCell>
        <TableCell className="text-muted-foreground text-sm">
          {account.institution_name ?? "—"}
        </TableCell>
        <PrimaryValueCell account={account} category={category} />
        <SecondaryCell account={account} category={category} />
        <TableCell className="text-right text-xs text-muted-foreground">
          {relativeTime(account.last_synced_at)}
        </TableCell>
      </TableRow>

      {isOpen && (
        <TableRow className="bg-muted/30 hover:bg-muted/30">
          <TableCell colSpan={6} className="p-0">
            <ExpandedRow account={account} category={category} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function PrimaryValueCell({
  account,
  category,
}: {
  account: BankAccountResponse;
  category: Category;
}) {
  if (category === "loan") {
    const owed = account.loan?.used_amount ?? Math.abs(account.balance);
    return (
      <TableCell className="text-right font-mono tabular text-[hsl(var(--loss))]">
        −{fmt.eur(owed)}
      </TableCell>
    );
  }
  if (category === "invest" || category === "retirement" || category === "employee") {
    const value = account.valuation ?? account.balance;
    return <TableCell className="text-right font-mono tabular">{fmt.eur(value)}</TableCell>;
  }
  return <TableCell className="text-right font-mono tabular">{fmt.eur(account.balance)}</TableCell>;
}

function SecondaryCell({
  account,
  category,
}: {
  account: BankAccountResponse;
  category: Category;
}) {
  if (category === "loan") {
    const loan = account.loan;
    if (!loan) return <TableCell className="text-muted-foreground text-xs">—</TableCell>;
    const parts: string[] = [];
    if (loan.rate !== null) parts.push(formatRate(loan.rate));
    if (loan.maturity_date) parts.push(monthYear(loan.maturity_date));
    return (
      <TableCell className="text-xs font-mono tabular text-muted-foreground">
        {parts.join(" · ") || "—"}
      </TableCell>
    );
  }
  if (category === "invest" || category === "retirement" || category === "employee") {
    if (account.diff === null || account.diff_percent === null) {
      return <TableCell className="text-muted-foreground text-xs">—</TableCell>;
    }
    const positive = account.diff >= 0;
    return (
      <TableCell>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded text-xs font-mono tabular",
            positive
              ? "bg-[hsl(var(--gain))]/10 text-[hsl(var(--gain))]"
              : "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]",
          )}
        >
          <span>{fmt.signedEur(account.diff)}</span>
          <span className="opacity-70">{fmt.signedPct(account.diff_percent)}</span>
        </span>
      </TableCell>
    );
  }
  return (
    <TableCell className="text-muted-foreground text-xs font-mono tabular">
      {maskedIban(account.iban)}
    </TableCell>
  );
}

/* ── Expanded inline content (drill-down) ─────────────────────────────────── */

function ExpandedRow({ account, category }: { account: BankAccountResponse; category: Category }) {
  if (category === "loan" && account.loan) {
    return <LoanDetails loan={account.loan} />;
  }
  if (INVESTMENT_TYPES.includes(account.type)) {
    return <HoldingsInline accountId={account.id} />;
  }
  if (TRANSACTION_TYPES.includes(account.type)) {
    return <TransactionsInline accountId={account.id} />;
  }
  return <div className="p-4 text-sm text-muted-foreground">Aucun détail disponible.</div>;
}

function LoanDetails({ loan }: { loan: LoanResponse }) {
  const progress =
    loan.nb_payments_done !== null && loan.nb_payments_total !== null && loan.nb_payments_total > 0
      ? (loan.nb_payments_done / loan.nb_payments_total) * 100
      : null;

  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {loan.total_amount !== null && (
          <Stat label="Capital initial" value={fmt.eur(loan.total_amount)} />
        )}
        {loan.used_amount !== null && (
          <Stat label="Capital restant" value={fmt.eur(loan.used_amount)} />
        )}
        {loan.rate !== null && <Stat label="Taux" value={formatRate(loan.rate)} />}
        {loan.duration_months !== null && (
          <Stat label="Durée totale" value={`${loan.duration_months} mois`} />
        )}
        {loan.next_payment_amount !== null && loan.next_payment_amount > 0 && (
          <Stat label="Mensualité" value={fmt.eur(loan.next_payment_amount)} />
        )}
        {loan.nb_payments_left !== null && (
          <Stat label="Échéances restantes" value={`${loan.nb_payments_left} mois`} />
        )}
        {loan.maturity_date && <Stat label="Fin du prêt" value={monthYear(loan.maturity_date)} />}
        {loan.insurance_amount !== null && loan.insurance_amount > 0 && (
          <Stat label="Assurance / mois" value={fmt.eur(loan.insurance_amount)} />
        )}
      </div>

      {loan.deferred && (
        <div className="text-xs text-muted-foreground italic">
          Prêt différé
          {loan.start_repayment_date &&
            ` · début remboursement : ${monthYear(loan.start_repayment_date)}`}
        </div>
      )}

      {progress !== null && (
        <div className="space-y-1">
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-muted-foreground">
            Progression : {loan.nb_payments_done} / {loan.nb_payments_total} échéances (
            {progress.toFixed(1).replace(".", ",")} %)
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-muted-foreground uppercase tracking-wider text-[10px]">{label}</div>
      <div className="font-mono tabular truncate">{value}</div>
    </div>
  );
}

function HoldingsInline({ accountId }: { accountId: string }) {
  const holdings = useAccountHoldings(accountId);
  const updateTer = useUpdateHoldingTer(accountId);

  if (holdings.isLoading) return <p className="p-4 text-sm text-muted-foreground">Chargement…</p>;
  if (!holdings.data || holdings.data.length === 0)
    return <p className="p-4 text-sm text-muted-foreground">Aucune position.</p>;

  const formatTer = (v: number | string) =>
    typeof v === "number" ? (v * 100).toFixed(2) + " %" : String(v);

  return (
    <div className="p-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
            <TableHead>Libellé</TableHead>
            <TableHead className="text-right">Quantité</TableHead>
            <TableHead className="text-right">PRU</TableHead>
            <TableHead className="text-right">Valorisation</TableHead>
            <TableHead className="text-right">TER</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {holdings.data.map((h) => (
            <TableRow key={h.id}>
              <TableCell className="font-mono font-medium">{h.ticker}</TableCell>
              <TableCell className="text-muted-foreground">{h.label}</TableCell>
              <TableCell className="text-right font-mono tabular">{fmt.num(h.quantity)}</TableCell>
              <TableCell className="text-right font-mono tabular">
                {fmt.eur(h.unit_price)}
              </TableCell>
              <TableCell className="text-right font-mono tabular">
                {fmt.eur(h.current_value)}
              </TableCell>
              <TableCell className="text-right">
                <DataField
                  value={h.ter}
                  source={h.ter_source}
                  formatValue={formatTer}
                  editable
                  inputStep="0.0001"
                  inputMin="0"
                  inputMax="0.02"
                  validate={(v) => v >= 0 && v <= 0.02}
                  onEdit={(ter) => updateTer.mutate({ holdingId: h.id, ter })}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function TransactionsInline({ accountId }: { accountId: string }) {
  const txs = useAccountTransactions(accountId, 50);
  if (txs.isLoading) return <p className="p-4 text-sm text-muted-foreground">Chargement…</p>;
  if (!txs.data || txs.data.length === 0)
    return <p className="p-4 text-sm text-muted-foreground">Aucune transaction.</p>;
  return (
    <div className="p-2">
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
                <TableCell className="text-xs text-muted-foreground">{t.category ?? "—"}</TableCell>
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
    </div>
  );
}
