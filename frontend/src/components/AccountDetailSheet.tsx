import {
  useAccountHoldings,
  useAccountTransactions,
  useUpdateHoldingTer,
  useUpdateTransactionCategory,
  type BankAccountResponse,
  type BankTransactionResponse,
  type HoldingResponse,
  type LoanResponse,
} from "@/api";
import { useT } from "@/i18n";
import {
  TRANSACTION_CATEGORY_KEYS,
  accountValue,
  categoryLabel,
  cleanName,
  groupOf,
  hasHoldings,
  hasTransactions,
  longDate,
  monthYear,
  shortDate,
  typeLabel,
} from "@/lib/accounts";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  BottomSheet,
  BottomSheetBody,
  BottomSheetContent,
  BottomSheetDescription,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { DataField } from "@/components/ui/data-field";

interface Props {
  account: BankAccountResponse | null;
  onClose: () => void;
}

/**
 * Detail of one account in a bottom sheet (centered modal on desktop):
 * loan schedule, positions or movements — two lines per row, no table.
 */
export function AccountDetailSheet({ account, onClose }: Props) {
  useT();
  return (
    <BottomSheet open={account !== null} onOpenChange={(open) => !open && onClose()}>
      <BottomSheetContent>
        {account && (
          <>
            <BottomSheetHeader>
              <BottomSheetTitle>{cleanName(account.name)}</BottomSheetTitle>
              <BottomSheetDescription>
                {typeLabel(account.type)}
                {account.institution_name ? ` · ${account.institution_name}` : ""}
              </BottomSheetDescription>
              <div
                className={cn(
                  "font-mono text-2xl font-semibold tabular",
                  groupOf(account.type) === "loan" && "text-[hsl(var(--loss))]",
                )}
              >
                {groupOf(account.type) === "loan" ? "−" : ""}
                {fmt.eur(accountValue(account))}
              </div>
            </BottomSheetHeader>
            <BottomSheetBody>
              <Detail account={account} />
            </BottomSheetBody>
          </>
        )}
      </BottomSheetContent>
    </BottomSheet>
  );
}

function Detail({ account }: { account: BankAccountResponse }) {
  const { t } = useT();
  if (groupOf(account.type) === "loan") {
    return account.loan ? (
      <LoanDetail loan={account.loan} />
    ) : (
      <Empty>{t("accounts.detail.noLoanDetail")}</Empty>
    );
  }
  if (hasHoldings(account.type)) return <Holdings accountId={account.id} />;
  if (hasTransactions(account.type)) return <Transactions accountId={account.id} />;
  return <Empty>{t("accounts.detail.noDetail")}</Empty>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/* ── Loan ─────────────────────────────────────────────────────────────── */

function LoanDetail({ loan }: { loan: LoanResponse }) {
  const { t, tn } = useT();
  const progress =
    loan.nb_payments_done !== null && loan.nb_payments_total
      ? (loan.nb_payments_done / loan.nb_payments_total) * 100
      : null;
  const rows: [string, string][] = [];
  if (loan.next_payment_amount && loan.next_payment_date)
    rows.push([
      t("accounts.loan.nextPayment"),
      t("accounts.loan.amountOnDate", {
        amount: fmt.eur(loan.next_payment_amount),
        date: longDate(loan.next_payment_date),
      }),
    ]);
  else if (loan.next_payment_amount)
    rows.push([t("accounts.loan.payment"), fmt.eur(loan.next_payment_amount)]);
  if (loan.used_amount !== null)
    rows.push([t("accounts.loan.remaining"), fmt.eur(loan.used_amount)]);
  if (loan.total_amount !== null)
    rows.push([t("accounts.loan.borrowed"), fmt.eur(loan.total_amount)]);
  if (loan.rate !== null)
    rows.push([
      t("accounts.loan.rate"),
      t("accounts.loan.rateValue", { rate: fmt.num(loan.rate) }),
    ]);
  if (loan.nb_payments_left !== null)
    rows.push([t("accounts.loan.paymentsLeft"), `${loan.nb_payments_left}`]);
  if (loan.maturity_date) rows.push([t("accounts.loan.end"), monthYear(loan.maturity_date)]);
  if (loan.insurance_amount)
    rows.push([t("accounts.loan.insurance"), fmt.eur(loan.insurance_amount)]);
  if (loan.deferred)
    rows.push([
      t("accounts.loan.repayment"),
      loan.start_repayment_date
        ? t("accounts.loan.notStartedFrom", { date: monthYear(loan.start_repayment_date) })
        : t("accounts.loan.notStarted"),
    ]);

  return (
    <div className="space-y-4">
      <dl className="divide-y rounded-md border text-sm">
        {rows.map(([label, value], i) => (
          <div
            key={label}
            className={cn("flex justify-between gap-3 px-3 py-2", i === 0 && "font-medium")}
          >
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-right font-mono tabular">{value}</dd>
          </div>
        ))}
      </dl>
      {progress !== null && (
        <div className="space-y-1">
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs text-muted-foreground">
            {tn("accounts.loan.progress", loan.nb_payments_done ?? 0, {
              total: loan.nb_payments_total ?? 0,
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Positions ────────────────────────────────────────────────────────── */

function Holdings({ accountId }: { accountId: string }) {
  const { t } = useT();
  const holdings = useAccountHoldings(accountId);
  const updateTer = useUpdateHoldingTer(accountId);

  if (holdings.isLoading) return <Empty>{t("common.loading")}</Empty>;
  if (holdings.isError) return <Empty>{t("accounts.holdings.loadFailed")}</Empty>;
  if (!holdings.data || holdings.data.length === 0)
    return <Empty>{t("accounts.holdings.empty")}</Empty>;

  return (
    <ul className="divide-y rounded-md border">
      {holdings.data.map((h) => (
        <HoldingRow key={h.id} h={h} onTer={(ter) => updateTer.mutate({ holdingId: h.id, ter })} />
      ))}
    </ul>
  );
}

function HoldingRow({ h, onTer }: { h: HoldingResponse; onTer: (ter: number) => void }) {
  const { t, tn } = useT();
  const cost = h.quantity * h.unit_price;
  const gain = cost > 0 ? h.current_value - cost : null;
  return (
    <li className="px-3 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0 truncate font-medium">{h.label || h.ticker}</span>
        <span className="shrink-0 font-mono tabular">{fmt.eur(h.current_value)}</span>
      </div>
      <div className="mt-0.5 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span className="min-w-0 truncate">
          {t("accounts.holdings.summary", {
            units: tn("accounts.holdings.units", h.quantity, { count: fmt.num(h.quantity) }),
            price: fmt.eur(h.unit_price),
          })}
        </span>
        {gain !== null && (
          <span
            className={cn(
              "shrink-0 font-mono tabular",
              gain >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
            )}
          >
            {fmt.signedEur(gain)}
          </span>
        )}
      </div>
      <div className="mt-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>{t("accounts.holdings.fees")}</span>
        <DataField
          value={h.ter}
          source={h.ter_source}
          formatValue={(v) => (typeof v === "number" ? fmt.pct(v) : String(v))}
          editable
          inputStep="0.0001"
          inputMin="0"
          inputMax="0.02"
          validate={(v) => v >= 0 && v <= 0.02}
          onEdit={onTer}
        />
      </div>
    </li>
  );
}

/* ── Movements ────────────────────────────────────────────────────────── */

function Transactions({ accountId }: { accountId: string }) {
  const { t } = useT();
  const txs = useAccountTransactions(accountId, 50);
  const updateCategory = useUpdateTransactionCategory(accountId);

  if (txs.isLoading) return <Empty>{t("common.loading")}</Empty>;
  if (txs.isError) return <Empty>{t("accounts.transactions.loadFailed")}</Empty>;
  if (!txs.data || txs.data.length === 0) return <Empty>{t("accounts.transactions.empty")}</Empty>;

  return (
    <ul className="divide-y rounded-md border">
      {txs.data.map((tx) => (
        <TransactionRow
          key={tx.id}
          tx={tx}
          onCategory={(category) => updateCategory.mutate({ transactionId: tx.id, category })}
        />
      ))}
    </ul>
  );
}

function TransactionRow({
  tx,
  onCategory,
}: {
  tx: BankTransactionResponse;
  onCategory: (category: string) => void;
}) {
  const { t } = useT();
  return (
    <li className="px-3 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0 truncate">{tx.description || "—"}</span>
        <span
          className={cn(
            "shrink-0 font-mono tabular",
            tx.amount >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
          )}
        >
          {fmt.signedEur(tx.amount)}
        </span>
      </div>
      <div className="mt-0.5 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>{shortDate(tx.transaction_date)}</span>
        <select
          aria-label={t("accounts.transactions.category")}
          value={tx.category ?? ""}
          onChange={(e) => e.target.value && onCategory(e.target.value)}
          className="max-w-[60%] cursor-pointer truncate rounded border-none bg-transparent text-right text-xs text-muted-foreground hover:text-foreground focus:outline-none"
        >
          {!tx.category && <option value="">{categoryLabel(null)}</option>}
          {TRANSACTION_CATEGORY_KEYS.map((key) => (
            <option key={key} value={key}>
              {categoryLabel(key)}
            </option>
          ))}
        </select>
      </div>
    </li>
  );
}
