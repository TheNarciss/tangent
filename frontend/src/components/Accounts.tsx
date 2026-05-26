import { useEffect, useMemo, useRef, useState } from "react";
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
  Zap,
} from "lucide-react";

import {
  useBankAccounts,
  useAccountHoldings,
  useAccountTransactions,
  useSyncBankAccounts,
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
  // Cash
  checking: "Courant",
  card: "Carte",
  joint: "Joint",
  // Savings
  savings: "Épargne",
  livret_a: "Livret A",
  livret_b: "Livret B",
  ldds: "LDDS",
  lep: "LEP",
  pel: "PEL",
  cel: "CEL",
  csl: "CSL",
  cat: "Compte à terme",
  deposit: "Dépôt",
  // Investment
  pea: "PEA",
  cto: "CTO",
  life_insurance: "Assurance vie",
  capitalisation: "Capitalisation",
  real_estate: "Immobilier",
  crowdlending: "Crowdlending",
  // Retirement
  per: "PER",
  perp: "PERP",
  perco: "PERCO",
  madelin: "Madelin",
  article_83: "Article 83",
  // Employee
  pee: "PEE",
  rsp: "RSP",
  // Loans
  loan: "Prêt",
  mortgage: "Prêt immobilier",
  consumer_credit: "Crédit conso",
  revolving_credit: "Crédit revolving",
  // Misc
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
  // Powens duplicates words sometimes: "PEA Espèces Espèces" → "PEA Espèces"
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
  if (!iban) return "";
  return `•••• ${iban.slice(-4)}`;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `il y a ${hours}h`;
  const days = Math.floor(hours / 24);
  return `il y a ${days}j`;
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
      const owed = a.loan?.used_amount ?? Math.abs(a.balance);
      return sum + owed;
    }
    return sum + a.balance;
  }, 0);
}

/* ── Root component ───────────────────────────────────────────────────────── */

export function Accounts() {
  const accounts = useBankAccounts();
  const sync = useSyncBankAccounts();
  const refresh = useRefreshBankAccounts();
  const [selected, setSelected] = useState<BankAccountResponse | null>(null);

  // Auto-sync once on mount
  const didAutoSync = useRef(false);
  useEffect(() => {
    if (!didAutoSync.current && accounts.data !== undefined) {
      didAutoSync.current = true;
      sync.mutate();
    }
  }, [accounts.data, sync]);

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

  const isSyncing = sync.isPending || refresh.isPending;
  const lastReport = refresh.data ?? sync.data;

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Mes comptes
          </CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => sync.mutate()}
              disabled={isSyncing}
              className="gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", sync.isPending && "animate-spin")} />
              Synchroniser
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refresh.mutate()}
              disabled={isSyncing}
              className="gap-2"
              title="Force la banque à renvoyer les dernières données (10-30s)"
            >
              <Zap className={cn("h-4 w-4", refresh.isPending && "animate-pulse")} />
              Forcer banque
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {sync.isError && (
            <p className="text-sm text-[hsl(var(--loss))] mb-3">
              Erreur sync : {sync.error instanceof Error ? sync.error.message : "inconnue"}
            </p>
          )}
          {refresh.isError && (
            <p className="text-sm text-[hsl(var(--loss))] mb-3">
              Erreur refresh : {refresh.error instanceof Error ? refresh.error.message : "inconnue"}
            </p>
          )}
          {lastReport && lastReport.success && (
            <p className="text-xs text-muted-foreground mb-3">
              {lastReport.from_cache ? "Cache · " : ""}
              {lastReport.accounts_persisted} comptes, {lastReport.holdings_persisted} positions,{" "}
              {lastReport.transactions_persisted} nouvelles transactions
            </p>
          )}

          {/* Net worth summary */}
          {accounts.data && accounts.data.length > 0 && (
            <div className="grid grid-cols-3 gap-4 pt-2">
              <NetWorthTile label="Actifs" value={netWorth.assets} variant="positive" />
              <NetWorthTile label="Dettes" value={netWorth.debt} variant="negative" />
              <NetWorthTile label="Net" value={netWorth.net} variant="net" />
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
                Aucun compte synchronisé. Connecte Powens et clique sur Synchroniser.
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
              selectedId={selected?.id ?? null}
              onSelect={(a) => setSelected(selected?.id === a.id ? null : a)}
            />
          );
        })}

      {/* ── Drill-down ──────────────────────────────────────────────────── */}
      {selected && INVESTMENT_TYPES.includes(selected.type) && (
        <AccountHoldings account={selected} />
      )}
      {selected && TRANSACTION_TYPES.includes(selected.type) && (
        <AccountTransactions account={selected} />
      )}
    </div>
  );
}

/* ── Net worth tile ───────────────────────────────────────────────────────── */

function NetWorthTile({
  label,
  value,
  variant,
}: {
  label: string;
  value: number;
  variant: "positive" | "negative" | "net";
}) {
  const colorClass =
    variant === "negative"
      ? "text-[hsl(var(--loss))]"
      : variant === "net" && value < 0
        ? "text-[hsl(var(--loss))]"
        : "text-foreground";
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("text-lg font-mono tabular", colorClass)}>{fmt.eur(value)}</div>
    </div>
  );
}

/* ── Section ──────────────────────────────────────────────────────────────── */

function AccountSection({
  category,
  accounts,
  selectedId,
  onSelect,
}: {
  category: Category;
  accounts: BankAccountResponse[];
  selectedId: string | null;
  onSelect: (a: BankAccountResponse) => void;
}) {
  const Icon = CATEGORY_ICON[category];
  const total = categoryTotal(accounts, category);
  const isDebt = category === "loan";

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between px-1">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {CATEGORY_LABELS[category]}
          <span className="text-xs text-muted-foreground/70 normal-case">({accounts.length})</span>
        </h2>
        <span className={cn("text-sm font-mono tabular", isDebt && "text-[hsl(var(--loss))]")}>
          {isDebt ? `−${fmt.eur(total)}` : fmt.eur(total)}
        </span>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {accounts.map((a) => (
          <AccountCard
            key={a.id}
            account={a}
            category={category}
            isSelected={selectedId === a.id}
            onClick={() => onSelect(a)}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Account card (dispatch on category) ──────────────────────────────────── */

function AccountCard({
  account,
  category,
  isSelected,
  onClick,
}: {
  account: BankAccountResponse;
  category: Category;
  isSelected: boolean;
  onClick: () => void;
}) {
  const isClickable =
    INVESTMENT_TYPES.includes(account.type) || TRANSACTION_TYPES.includes(account.type);

  return (
    <Card
      onClick={isClickable ? onClick : undefined}
      className={cn(
        "transition relative",
        isClickable && "cursor-pointer hover:border-primary/50",
        isSelected && "border-primary ring-1 ring-primary/30",
      )}
    >
      <CardContent className="p-4 space-y-3">
        <CardHeading account={account} />
        {category === "loan" && account.loan ? (
          <LoanBody account={account} loan={account.loan} />
        ) : category === "invest" || category === "retirement" || category === "employee" ? (
          <InvestBody account={account} />
        ) : (
          <CashSavingsBody account={account} />
        )}
        <Footer account={account} showCaret={isClickable} isSelected={isSelected} />
      </CardContent>
    </Card>
  );
}

function CardHeading({ account }: { account: BankAccountResponse }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <div className="text-sm font-medium truncate">{cleanName(account.name)}</div>
        <div className="text-xs text-muted-foreground truncate">
          {account.institution_name ?? account.provider}
        </div>
      </div>
      <span className="shrink-0 text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
        {TYPE_LABELS[account.type]}
      </span>
    </div>
  );
}

function CashSavingsBody({ account }: { account: BankAccountResponse }) {
  return (
    <div>
      <div className="text-2xl font-mono tabular">{fmt.eur(account.balance)}</div>
      {account.iban && (
        <div className="text-xs text-muted-foreground mt-1">{maskedIban(account.iban)}</div>
      )}
    </div>
  );
}

function InvestBody({ account }: { account: BankAccountResponse }) {
  const value = account.valuation ?? account.balance;
  const hasDiff = account.diff !== null && account.diff_percent !== null;
  const positive = (account.diff ?? 0) >= 0;

  return (
    <div className="space-y-2">
      <div>
        <div className="text-2xl font-mono tabular">{fmt.eur(value)}</div>
        {account.valuation !== null && Math.abs(account.valuation - account.balance) > 0.01 && (
          <div className="text-xs text-muted-foreground">dont {fmt.eur(account.balance)} cash</div>
        )}
      </div>
      {hasDiff && (
        <div
          className={cn(
            "inline-flex items-center gap-2 px-2 py-1 rounded text-xs font-mono tabular",
            positive
              ? "bg-[hsl(var(--gain))]/10 text-[hsl(var(--gain))]"
              : "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]",
          )}
        >
          <span>{fmt.signedEur(account.diff!)}</span>
          <span className="opacity-70">{fmt.signedPct(account.diff_percent!)}</span>
        </div>
      )}
    </div>
  );
}

function LoanBody({ account, loan }: { account: BankAccountResponse; loan: LoanResponse }) {
  const capitalRemaining = loan.used_amount ?? Math.abs(account.balance);
  const progress =
    loan.nb_payments_done !== null && loan.nb_payments_total !== null && loan.nb_payments_total > 0
      ? (loan.nb_payments_done / loan.nb_payments_total) * 100
      : null;

  return (
    <div className="space-y-3">
      <div>
        <div className="text-xs uppercase tracking-wider text-muted-foreground">
          Capital restant
        </div>
        <div className="text-2xl font-mono tabular text-[hsl(var(--loss))]">
          {fmt.eur(capitalRemaining)}
          {loan.total_amount && (
            <span className="text-xs text-muted-foreground ml-2">
              / {fmt.eur(loan.total_amount)}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        {loan.rate !== null && <Stat label="Taux" value={formatRate(loan.rate)} />}
        {loan.maturity_date && <Stat label="Échéance" value={monthYear(loan.maturity_date)} />}
        {loan.nb_payments_left !== null && (
          <Stat label="Restant" value={`${loan.nb_payments_left} mois`} />
        )}
        {loan.next_payment_amount !== null && loan.next_payment_amount > 0 && (
          <Stat label="Mensualité" value={fmt.eur(loan.next_payment_amount)} />
        )}
      </div>

      {loan.deferred && (
        <div className="text-xs text-muted-foreground italic">
          Prêt différé
          {loan.start_repayment_date && ` · début remb. ${monthYear(loan.start_repayment_date)}`}
        </div>
      )}

      {progress !== null && (
        <div className="space-y-1">
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-muted-foreground">
            {loan.nb_payments_done} / {loan.nb_payments_total} échéances
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-muted-foreground">{label}</div>
      <div className="font-mono tabular truncate">{value}</div>
    </div>
  );
}

function Footer({
  account,
  showCaret,
  isSelected,
}: {
  account: BankAccountResponse;
  showCaret: boolean;
  isSelected: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
      <span>{relativeTime(account.last_synced_at)}</span>
      {showCaret && (
        <span className="flex items-center gap-1">
          {isSelected ? "Masquer" : "Détails"}
          {isSelected ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </span>
      )}
    </div>
  );
}

/* ── Drill-down: holdings ─────────────────────────────────────────────────── */

function AccountHoldings({ account }: { account: BankAccountResponse }) {
  const holdings = useAccountHoldings(account.id);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          {cleanName(account.name)} · Positions
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

/* ── Drill-down: transactions ─────────────────────────────────────────────── */

function AccountTransactions({ account }: { account: BankAccountResponse }) {
  const txs = useAccountTransactions(account.id, 50);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          {cleanName(account.name)} · 50 dernières transactions
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
