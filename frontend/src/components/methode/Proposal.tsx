import {
  ApiError,
  useOptimizer,
  useWealthSummary,
  type OptimizerRequest,
  type OptimizerResponse,
} from "@/api";
import { fmt } from "@/lib/format";
import { ageFromBirthDate, ceilingsFromEnvelopes, useProfile } from "@/lib/profile";
import { cn } from "@/lib/utils";

/** A proposed move is worth showing above this weight or amount. */
const MATERIAL_WEIGHT = 0.05;
const MATERIAL_EUR = 500;

/**
 * What to move to reach the share the profile targets — shown inside the
 * « part d'actions » verdict, and only when that verdict is not green.
 *
 * It used to be a block of its own on the Placements screen, where it could
 * advise selling everything two centimetres under a verdict saying « rien à
 * changer » (ADR-028).
 */
export function Proposal() {
  const [profile] = useProfile();
  const wealth = useWealthSummary();

  const age = profile ? ageFromBirthDate(profile.birth_date) : null;
  const hasProfile = !!profile && age !== null && profile.fiscal_shares > 0;
  const ceilingsUsed = ceilingsFromEnvelopes(wealth.data?.envelopes) ?? profile?.ceilings_used;

  const req: OptimizerRequest = {
    objective: hasProfile ? "from_strategy" : "target_volatility",
    max_volatility: (hasProfile && profile ? profile.max_annual_volatility : 10) / 100,
    ...(hasProfile && profile
      ? {
          target_return: profile.target_annual_return / 100,
          include_envelopes: true,
          age: age!,
          rfr: profile.rfr_n_minus_2,
          fiscal_shares: profile.fiscal_shares,
          ceilings_used: ceilingsUsed,
        }
      : {}),
  };
  const proposal = useOptimizer(req);

  if (proposal.isLoading) {
    return <p className="text-xs text-muted-foreground">Calcul de la piste…</p>;
  }
  if (proposal.error) return <ProposalError error={proposal.error} />;
  if (!proposal.data) return null;
  return (
    <div>
      <h4 className="text-sm font-medium">Une piste{hasProfile ? ", selon ton profil" : ""}</h4>
      <ProposalMoves data={proposal.data} />
      {!hasProfile && (
        <p className="mt-2 text-xs text-muted-foreground">
          Renseigne ton profil pour une piste adaptée à ton curseur prudent ↔ dynamique.
        </p>
      )}
    </div>
  );
}

function ProposalError({ error }: { error: unknown }) {
  const infeasible = error instanceof ApiError && /infeasible|impossible/i.test(error.message);
  return (
    <p className="mt-1 text-sm text-muted-foreground">
      {infeasible
        ? "Avec tes lignes actuelles, le rendement visé n'est pas atteignable au niveau de risque de ton curseur. Piste : accepter un peu plus de variations, ou viser moins haut."
        : "La piste n'a pas pu être calculée pour l'instant."}
    </p>
  );
}

function ProposalMoves({ data }: { data: OptimizerResponse }) {
  const moves = data.actions
    .map((a, i) => ({ ...a, label: data.asset_labels[i], kind: data.asset_kinds[i] }))
    .filter(
      (a) => Math.abs(a.delta_weight) >= MATERIAL_WEIGHT || Math.abs(a.delta_value) >= MATERIAL_EUR,
    )
    .sort((a, b) => Math.abs(b.delta_value) - Math.abs(a.delta_value));

  if (moves.length === 0) {
    return (
      <p className="mt-1 text-sm text-muted-foreground">
        Rien à changer : ta répartition colle déjà à ton profil.
      </p>
    );
  }
  return (
    <div className="mt-2 space-y-2">
      <ul className="divide-y rounded-md border text-sm">
        {moves.map((a) => {
          const buy = a.delta_value > 0;
          return (
            <li key={a.ticker} className="flex items-center justify-between gap-3 px-3 py-2">
              <span className="min-w-0 truncate">
                {a.kind === "envelope" ? "Placer sur" : buy ? "Renforcer" : "Alléger"}{" "}
                <strong>{a.label}</strong>
              </span>
              <span
                className={cn(
                  "shrink-0 font-mono tabular",
                  buy ? "text-[hsl(var(--gain))]" : "text-[hsl(var(--loss))]",
                )}
              >
                {buy ? "+" : "−"}
                {fmt.eur(Math.abs(a.delta_value))}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-muted-foreground">
        Ce n'est qu'une piste : avant de vendre, compte les frais de courtage et l'impôt sur la
        plus-value. Le plus simple est souvent d'orienter tes prochains versements.
      </p>
    </div>
  );
}
