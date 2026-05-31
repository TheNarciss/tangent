import {
  AlertTriangle,
  Briefcase,
  Building2,
  Coins,
  PiggyBank,
  TrendingDown,
  Wallet,
} from "lucide-react";

import type { WealthSummary } from "@/api";
import { fmt } from "@/lib/format";

/**
 * Patrimoine — bloc affiché dans Aperçu si `dashboard.wealth` est présent.
 *
 * 3 sections :
 * - Net Worth + per-category breakdown
 * - Livrets (avec rate + headroom vs plafond)
 * - Prêts (avec différé éventuel)
 */
export function Patrimony({ wealth }: { wealth: WealthSummary }) {
  return (
    <div className="space-y-6">
      <NetWorthBlock wealth={wealth} />
      {wealth.envelopes.length > 0 && <EnvelopesBlock envelopes={wealth.envelopes} />}
      {wealth.loans.length > 0 && <LoansBlock loans={wealth.loans} />}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Net Worth block                                                          */
/* ────────────────────────────────────────────────────────────────────────── */

function NetWorthBlock({ wealth }: { wealth: WealthSummary }) {
  const isNegative = wealth.net_worth < 0;

  return (
    <section className="rounded-lg border bg-card p-5 space-y-4">
      <header className="flex items-baseline justify-between">
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Patrimoine net
          </h3>
          <p
            className={`text-3xl font-semibold tabular ${
              isNegative ? "text-[hsl(var(--loss))]" : "text-foreground"
            }`}
          >
            {fmt.eur(wealth.net_worth)}
          </p>
        </div>
        <div className="text-right text-xs text-muted-foreground space-y-0.5">
          <p>
            Actifs <span className="font-mono tabular">{fmt.eur(wealth.total_assets)}</span>
          </p>
          <p>
            Passifs <span className="font-mono tabular">−{fmt.eur(wealth.total_liabilities)}</span>
          </p>
        </div>
      </header>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t">
        <Tile
          icon={<Wallet className="h-4 w-4" />}
          label="Liquide"
          value={wealth.checking_total}
          hint="Comptes courants"
        />
        <Tile
          icon={<PiggyBank className="h-4 w-4" />}
          label="Épargne"
          value={wealth.envelopes_total}
          hint="Livrets réglementés"
        />
        <Tile
          icon={<Briefcase className="h-4 w-4" />}
          label="Investi"
          value={wealth.investments_total + wealth.pea_cash_total}
          hint={
            wealth.unrealized_pnl !== 0
              ? `${wealth.unrealized_pnl > 0 ? "+" : ""}${fmt.eur(wealth.unrealized_pnl)} latent`
              : "Titres + cash PEA"
          }
        />
        <Tile
          icon={<TrendingDown className="h-4 w-4" />}
          label="Dettes"
          value={-wealth.total_liabilities}
          hint="Prêts en cours"
          negative
        />
      </div>
    </section>
  );
}

function Tile({
  icon,
  label,
  value,
  hint,
  negative = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  hint?: string;
  negative?: boolean;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p
        className={`text-base font-medium font-mono tabular ${
          negative && value < 0 ? "text-[hsl(var(--loss))]" : ""
        }`}
      >
        {fmt.eur(value)}
      </p>
      {hint && <p className="text-[11px] text-muted-foreground leading-tight">{hint}</p>}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Envelopes block                                                          */
/* ────────────────────────────────────────────────────────────────────────── */

function EnvelopesBlock({ envelopes }: { envelopes: WealthSummary["envelopes"] }) {
  return (
    <section className="rounded-lg border bg-card p-5 space-y-3">
      <header className="flex items-center gap-2">
        <Coins className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Livrets réglementés</h3>
      </header>
      <div className="divide-y">
        {envelopes.map((env, i) => {
          const ratio =
            env.ceiling_eur && env.ceiling_eur > 0 ? Math.min(env.balance / env.ceiling_eur, 1) : 0;
          return (
            <div key={i} className="py-2.5 space-y-1.5">
              <div className="flex items-baseline gap-3">
                <span className="text-sm font-medium flex-1 min-w-0 truncate">
                  {env.display_name || env.name}
                </span>
                {env.rate_pct != null && (
                  <span className="text-xs text-muted-foreground font-mono tabular shrink-0">
                    {(env.rate_pct * 100).toFixed(2)} %
                  </span>
                )}
                <span className="text-sm font-mono tabular shrink-0">{fmt.eur(env.balance)}</span>
              </div>
              {env.ceiling_eur != null && (
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-[hsl(var(--gain))]"
                      style={{ width: `${ratio * 100}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-muted-foreground font-mono tabular shrink-0">
                    {env.headroom_eur != null ? `${fmt.eur(env.headroom_eur)} dispo` : ""}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Loans block                                                              */
/* ────────────────────────────────────────────────────────────────────────── */

function LoansBlock({ loans }: { loans: WealthSummary["loans"] }) {
  const anyDeferred = loans.some((l) => l.is_in_deferral);
  return (
    <section className="rounded-lg border bg-card p-5 space-y-3">
      <header className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Prêts en cours</h3>
      </header>
      {anyDeferred && (
        <div className="flex items-start gap-2 rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>
            Certains prêts sont en différé — pas de remboursement immédiat mais à anticiper.
          </span>
        </div>
      )}
      <div className="divide-y">
        {loans.map((loan, i) => (
          <div key={i} className="py-2.5 flex items-baseline gap-3 text-sm">
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{loan.name}</p>
              {loan.institution_name && (
                <p className="text-xs text-muted-foreground truncate">{loan.institution_name}</p>
              )}
            </div>
            <div className="text-right space-y-0.5 shrink-0">
              <p className="font-mono tabular text-[hsl(var(--loss))]">
                −{fmt.eur(loan.outstanding_balance)}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {loan.is_in_deferral
                  ? `différé jusqu'au ${loan.deferral_until}`
                  : loan.monthly_payment
                    ? `${fmt.eur(loan.monthly_payment)} / mois`
                    : ""}
                {loan.interest_rate_pct != null && (
                  <> · {(loan.interest_rate_pct * 100).toFixed(2)} %</>
                )}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
