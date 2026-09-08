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
import {
  TRANSACTION_CATEGORIES,
  TYPE_LABELS,
  accountValue,
  categoryLabel,
  cleanName,
  groupOf,
  hasHoldings,
  hasTransactions,
  longDate,
  monthYear,
  shortDate,
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
  return (
    <BottomSheet open={account !== null} onOpenChange={(open) => !open && onClose()}>
      <BottomSheetContent>
        {account && (
          <>
            <BottomSheetHeader>
              <BottomSheetTitle>{cleanName(account.name)}</BottomSheetTitle>
              <BottomSheetDescription>
                {TYPE_LABELS[account.type]}
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
  if (groupOf(account.type) === "loan") {
    return account.loan ? (
      <LoanDetail loan={account.loan} />
    ) : (
      <Empty>Ta banque ne donne pas le détail de ce prêt.</Empty>
    );
  }
  if (hasHoldings(account.type)) return <Holdings accountId={account.id} />;
  if (hasTransactions(account.type)) return <Transactions accountId={account.id} />;
  return <Empty>Aucun détail disponible pour ce compte.</Empty>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

/* ── Loan ─────────────────────────────────────────────────────────────── */

function LoanDetail({ loan }: { loan: LoanResponse }) {
  const progress =
    loan.nb_payments_done !== null && loan.nb_payments_total
      ? (loan.nb_payments_done / loan.nb_payments_total) * 100
      : null;
  const rows: [string, string][] = [];
  if (loan.next_payment_amount && loan.next_payment_date)
    rows.push([
      "Prochaine mensualité",
      `${fmt.eur(loan.next_payment_amount)} le ${longDate(loan.next_payment_date)}`,
    ]);
  else if (loan.next_payment_amount) rows.push(["Mensualité", fmt.eur(loan.next_payment_amount)]);
  if (loan.used_amount !== null) rows.push(["Reste à rembourser", fmt.eur(loan.used_amount)]);
  if (loan.total_amount !== null) rows.push(["Montant emprunté", fmt.eur(loan.total_amount)]);
  if (loan.rate !== null) rows.push(["Taux", `${loan.rate.toFixed(2).replace(".", ",")} %`]);
  if (loan.nb_payments_left !== null)
    rows.push(["Mensualités restantes", `${loan.nb_payments_left}`]);
  if (loan.maturity_date) rows.push(["Fin du prêt", monthYear(loan.maturity_date)]);
  if (loan.insurance_amount) rows.push(["Assurance par mois", fmt.eur(loan.insurance_amount)]);
  if (loan.deferred)
    rows.push([
      "Remboursement",
      loan.start_repayment_date
        ? `pas encore commencé · à partir de ${monthYear(loan.start_repayment_date)}`
        : "pas encore commencé",
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
            {loan.nb_payments_done} mensualités payées sur {loan.nb_payments_total}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Positions ────────────────────────────────────────────────────────── */

function Holdings({ accountId }: { accountId: string }) {
  const holdings = useAccountHoldings(accountId);
  const updateTer = useUpdateHoldingTer(accountId);

  if (holdings.isLoading) return <Empty>Chargement…</Empty>;
  if (holdings.isError) return <Empty>Impossible de charger les positions.</Empty>;
  if (!holdings.data || holdings.data.length === 0) return <Empty>Aucune position.</Empty>;

  return (
    <ul className="divide-y rounded-md border">
      {holdings.data.map((h) => (
        <HoldingRow key={h.id} h={h} onTer={(ter) => updateTer.mutate({ holdingId: h.id, ter })} />
      ))}
    </ul>
  );
}

function HoldingRow({ h, onTer }: { h: HoldingResponse; onTer: (ter: number) => void }) {
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
          {fmt.num(h.quantity)} part{h.quantity > 1 ? "s" : ""} · achetées {fmt.eur(h.unit_price)}
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
        <span>Frais annuels du fonds</span>
        <DataField
          value={h.ter}
          source={h.ter_source}
          formatValue={(v) => (typeof v === "number" ? `${(v * 100).toFixed(2)} %` : String(v))}
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
  const txs = useAccountTransactions(accountId, 50);
  const updateCategory = useUpdateTransactionCategory(accountId);

  if (txs.isLoading) return <Empty>Chargement…</Empty>;
  if (txs.isError) return <Empty>Impossible de charger les mouvements.</Empty>;
  if (!txs.data || txs.data.length === 0) return <Empty>Aucun mouvement.</Empty>;

  return (
    <ul className="divide-y rounded-md border">
      {txs.data.map((t) => (
        <TransactionRow
          key={t.id}
          t={t}
          onCategory={(category) => updateCategory.mutate({ transactionId: t.id, category })}
        />
      ))}
    </ul>
  );
}

function TransactionRow({
  t,
  onCategory,
}: {
  t: BankTransactionResponse;
  onCategory: (category: string) => void;
}) {
  return (
    <li className="px-3 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0 truncate">{t.description || "—"}</span>
        <span
          className={cn(
            "shrink-0 font-mono tabular",
            t.amount >= 0 ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
          )}
        >
          {fmt.signedEur(t.amount)}
        </span>
      </div>
      <div className="mt-0.5 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>{shortDate(t.transaction_date)}</span>
        <select
          aria-label="Catégorie"
          value={t.category ?? ""}
          onChange={(e) => e.target.value && onCategory(e.target.value)}
          className="max-w-[60%] cursor-pointer truncate rounded border-none bg-transparent text-right text-xs text-muted-foreground hover:text-foreground focus:outline-none"
        >
          {!t.category && <option value="">{categoryLabel(null)}</option>}
          {Object.entries(TRANSACTION_CATEGORIES).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </li>
  );
}
