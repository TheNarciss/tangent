import { Link } from "react-router-dom";

import {
  useVerdicts,
  type DiversificationVerdictDetails,
  type DrawdownVerdictDetails,
  type FeesVerdictDetails,
  type GoalVerdictDetails,
  type PerformanceVerdictDetails,
  type NextEuroVerdictDetails,
  type RiskShareVerdictDetails,
  type SavingsRateVerdictDetails,
  type Verdict,
} from "@/api";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NAV_PATHS } from "@/components/Sidebar";
import { VerdictCard, VerdictDot } from "@/components/ui/verdict-card";
import { Proposal } from "@/components/methode/Proposal";
import { StressList } from "@/components/methode/StressList";

/**
 * « Méthode » : every verdict of the method as a folded card (ADR-023).
 * A card shows a traffic light, one sentence, an amount and an action; the
 * computation behind it only appears on tap, so the page stays readable on
 * a phone and the detail exists for whoever wants it.
 */
export function Methode() {
  const q = useVerdicts();

  if (q.isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-muted/30" />
        ))}
      </div>
    );
  }
  if (q.isError || !q.data) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <p className="text-sm font-medium">Les verdicts ne sont pas disponibles pour l'instant</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {q.error instanceof Error ? q.error.message : "Réessaie dans un instant."}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <p className="text-sm text-muted-foreground">
        Chaque carte est un verdict : un feu, une phrase, un montant par an, une chose à faire.
        Elles sont rangées par urgence, puis par euros en jeu — ce qui est en haut compte le plus.
        Ouvre une carte pour voir le calcul.
      </p>
      {q.data.verdicts.map((v) => (
        <VerdictCard key={v.id} verdict={v}>
          {v.id === "fees" ? (
            <FeesDetails details={v.details as FeesVerdictDetails} />
          ) : v.id === "next_euro" ? (
            <NextEuroDetails details={v.details as NextEuroVerdictDetails} />
          ) : v.id === "risk_share" ? (
            <div className="space-y-4">
              <RiskShareDetails details={v.details as RiskShareVerdictDetails} />
              {v.status !== "green" && <Proposal />}
            </div>
          ) : v.id === "savings_rate" ? (
            <SavingsRateDetails details={v.details as SavingsRateVerdictDetails} />
          ) : v.id === "goal" ? (
            <GoalDetails details={v.details as GoalVerdictDetails} />
          ) : v.id === "performance" ? (
            <PerformanceDetails details={v.details as PerformanceVerdictDetails} />
          ) : v.id === "drawdown" ? (
            <div className="space-y-4">
              <DrawdownDetails details={v.details as DrawdownVerdictDetails} />
              <StressList />
            </div>
          ) : v.id === "diversification" ? (
            <DiversificationDetails details={v.details as DiversificationVerdictDetails} />
          ) : (
            <GenericDetails verdict={v} />
          )}
        </VerdictCard>
      ))}
    </div>
  );
}

/* ── Répartition ───────────────────────────────────────────────────────── */

function DiversificationDetails({ details: d }: { details: DiversificationVerdictDetails }) {
  const lines = d.lines ?? [];
  const duplicates = d.duplicates ?? [];
  const concentrated = d.concentrated ?? [];
  const unrecognised = d.unrecognised ?? [];

  return (
    <div className="space-y-4">
      <ul className="divide-y rounded-md border text-sm">
        {lines.map((l) => (
          <li key={l.label} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="truncate">{l.label}</div>
              <div className="truncate text-xs text-muted-foreground">
                {l.index_label ?? "classe non reconnue"}
                {!l.diversified && l.index_label ? " · un seul segment" : ""}
              </div>
            </div>
            <span className="shrink-0 font-mono tabular">{fmt.pct(l.weight)}</span>
          </li>
        ))}
      </ul>

      {duplicates.map((g) => (
        <p key={g.index_label} className="text-xs text-muted-foreground">
          <strong className="text-foreground">{g.labels.join(", ")}</strong> suivent le même indice
          « {g.index_label} » et pèsent ensemble {fmt.pct(g.weight)}. En garder plusieurs ne protège
          pas plus qu'un seul, et multiplie les frais fixes par ligne.
        </p>
      ))}

      {concentrated.map((c) => (
        <p key={c.label} className="text-xs text-muted-foreground">
          <strong className="text-foreground">{c.label}</strong> pèse {fmt.pct(c.weight)} et n'est
          pas diversifié :{" "}
          {c.kind === "stock" ? "c'est une seule société" : "il ne couvre qu'un segment du marché"}.
        </p>
      ))}

      {unrecognised.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Non reconnu, donc non jugé : {unrecognised.join(", ")}. Tangent lit le nom officiel de
          chaque ligne pour savoir ce qu'elle suit ; celles-ci ne correspondent à rien de connu.
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        Un fonds indiciel large n'est jamais signalé, quel que soit son poids : détenir un seul ETF
        monde est la recommandation la plus répandue. Le seuil de{" "}
        {fmt.pct(d.single_line_max ?? 0.4)} ne vise que les lignes qui parient sur une seule chose.
      </p>
    </div>
  );
}

/* ── Ce que tes placements ont vraiment rapporté ───────────────────────── */

function PerformanceDetails({ details: d }: { details: PerformanceVerdictDetails }) {
  if (d.twr === undefined || d.twr === null) {
    return (
      <p className="text-xs text-muted-foreground">
        Tangent enregistre chaque nuit la valeur de tes placements et les quantités qui la
        composent. C'est la seule façon de distinguer ce que le marché a fait de ce que tu as versé,
        parce que ta banque ne transmet aucune opération sur un PEA ou un compte-titres.
        {d.min_days ? ` Il faut ${d.min_days} jours pour un premier chiffre.` : ""}
      </p>
    );
  }
  const signed = (v: number) => `${v >= 0 ? "+" : ""}${fmt.pct(v)}`;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Tes fonds (TWR)"
          value={signed(d.twr_annualized ?? d.twr)}
          sub={
            d.twr_annualized !== null && d.twr_annualized !== undefined
              ? "par an, versements mis à part"
              : "depuis le début, versements mis à part"
          }
        />
        <Figure
          label="Ton argent (TRI)"
          value={d.irr !== null && d.irr !== undefined ? signed(d.irr) : "—"}
          sub={
            d.irr !== null && d.irr !== undefined
              ? "par an, avec le calendrier de tes versements"
              : "six mois d'historique nécessaires"
          }
        />
        <Figure
          label="Écart de comportement"
          value={
            d.behaviour_gap !== null && d.behaviour_gap !== undefined
              ? signed(d.behaviour_gap)
              : "—"
          }
          sub="ce que le moment de tes versements ajoute ou retire"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Historique du {d.start ? new Date(d.start).toLocaleDateString("fr-FR") : "?"} au{" "}
        {d.end ? new Date(d.end).toLocaleDateString("fr-FR") : "?"}, {d.days ?? 0} jours.{" "}
        {fmt.eur0(d.first_value_eur ?? 0)} au départ, {fmt.eur0(d.net_flows_eur ?? 0)} versés
        depuis, {fmt.eur0(d.last_value_eur ?? 0)} aujourd'hui. Le TWR juge la stratégie, le TRI juge
        ton résultat ; c'est la mesure que les fonds publient et celle que ton relevé devrait
        porter.
      </p>
    </div>
  );
}

/* ── Baisse depuis le plus haut ────────────────────────────────────────── */

function DrawdownDetails({ details: d }: { details: DrawdownVerdictDetails }) {
  if (d.drawdown === undefined) return null;
  const dd = Math.abs(d.drawdown);
  const max = Math.abs(d.max_drawdown ?? 0);
  const scale = Math.max(0.25, max * 1.2, dd * 1.2);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Sous le plus haut"
          value={`−${fmt.pct(dd)}`}
          sub={
            d.peak_day
              ? `plus haut du ${new Date(d.peak_day).toLocaleDateString("fr-FR")}`
              : "depuis le début"
          }
        />
        <Figure
          label="En euros"
          value={`−${fmt.eur0(d.missing_eur ?? 0)}`}
          sub="par rapport à ce plus haut"
        />
        <Figure
          label="Pire baisse connue"
          value={`−${fmt.pct(max)}`}
          sub="depuis que Tangent suit ton compte"
        />
      </div>
      {d.worst_year_ever && (
        <p className="text-xs text-muted-foreground">
          Pour situer : sur {d.worst_year_ever.to_year - d.worst_year_ever.from_year} ans d'actions
          américaines ({d.worst_year_ever.from_year}-{d.worst_year_ever.to_year}), la pire année a
          coûté{" "}
          <strong className="text-foreground">{fmt.pct(Math.abs(d.worst_year_ever.return))}</strong>{" "}
          en pouvoir d'achat. C'est le pire connu, pas une prévision.
        </p>
      )}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${Math.min(100, (dd / scale) * 100)}%` }}
          />
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground/60"
            style={{ left: `calc(${Math.min(100, ((d.alert_step ?? 0.1) / scale) * 100)}% - 1px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>au plus haut</span>
          <span>seuil d'alerte {fmt.pct(d.alert_step ?? 0.1)}</span>
          <span>−{fmt.pct(scale)}</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Un gérant doit prévenir son client le jour où le portefeuille passe 10 % sous son point de
        départ, puis à chaque tranche de 10 % (MiFID II, article 62). Tangent applique la même
        règle, mesurée hors versements. Une baisse n'est une perte qu'au moment où on vend.
      </p>
    </div>
  );
}

/* ── Épargne pour ton objectif ─────────────────────────────────────────── */

function GoalDetails({ details: d }: { details: GoalVerdictDetails }) {
  if (d.probability === undefined || d.goal_eur === undefined) return null;
  const p = d.probability;
  const target = d.target_probability ?? 0.75;
  const amber = d.amber_probability ?? 0.5;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Objectif"
          value={fmt.eur0(d.goal_eur)}
          sub={`dans ${d.horizon_years ?? 10} ans, en euros d'aujourd'hui`}
        />
        <Figure
          label="Point de départ"
          value={fmt.eur0(d.initial_eur ?? 0)}
          sub={`+ ${fmt.eur0(d.monthly_used_eur ?? 0)} par mois (${
            d.monthly_source === "observed" ? "virements observés" : "versement déclaré"
          })`}
        />
        <Figure
          label="Pour 3 chances sur 4"
          value={`${fmt.eur0(d.required_monthly_eur ?? 0)}/mois`}
          sub={
            d.extra_monthly_eur && d.extra_monthly_eur > 0
              ? `soit ${fmt.eur0(d.extra_monthly_eur)} de plus qu'aujourd'hui`
              : "tu y es déjà"
          }
        />
      </div>

      {/* Probability gauge with the two thresholds. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${amber * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-amber-500/25"
            style={{ left: `${amber * 100}%`, width: `${(target - amber) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${target * 100}%`, right: 0 }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${p * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>0 %</span>
          <span>
            {fmt.pct0(p)} de chances · cible {fmt.pct0(target)}
          </span>
          <span>100 %</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Dans {d.horizon_years ?? 10} ans, 1 fois sur 10 tu auras moins de {fmt.eur0(d.p10_eur ?? 0)}
        , la moitié du temps plus de {fmt.eur0(d.p50_eur ?? 0)}, 1 fois sur 10 plus de{" "}
        {fmt.eur0(d.p90_eur ?? 0)}. Simulation de {d.n_paths ?? 2000} trajectoires avec{" "}
        {fmt.pct0(d.equity_share ?? 0)} d'actions (ton profil), {fmt.pct(d.mu_real ?? 0)} de
        rendement réel par an après {fmt.pct0(d.inflation ?? 0.02)} d'inflation, volatilité{" "}
        {fmt.pct0(d.sigma ?? 0)}.
      </p>
    </div>
  );
}

/* ── Taux d'épargne ────────────────────────────────────────────────────── */

function SavingsRateDetails({ details: d }: { details: SavingsRateVerdictDetails }) {
  if (d.rate === undefined || d.income_monthly_eur === undefined) return null;
  const rate = d.rate;
  const target = d.target_rate ?? 0.15;
  const amber = d.amber_min ?? 0.05;
  const scale = Math.max(0.3, target * 2, rate * 1.1);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Épargné par mois"
          value={fmt.eur0(d.monthly_saved_used_eur ?? 0)}
          sub={
            d.source === "observed"
              ? "virements vers livrets et placements, 90 derniers jours"
              : "versement déclaré dans ton profil"
          }
        />
        <Figure
          label="Revenu par mois"
          value={fmt.eur0(d.income_monthly_eur)}
          sub={`revenu fiscal ${fmt.eur0(d.rfr_eur ?? 0)} sur 12 mois`}
        />
        <Figure
          label="Cible"
          value={fmt.eur0(d.target_monthly_eur ?? 0)}
          sub={`${fmt.pct0(target)} du revenu`}
        />
      </div>

      {/* Gauge: 0 → scale, red under amber_min, amber under target, green above. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-[hsl(var(--loss))]/25"
            style={{ width: `${(amber / scale) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 bg-amber-500/25"
            style={{
              left: `${(amber / scale) * 100}%`,
              width: `${((target - amber) / scale) * 100}%`,
            }}
          />
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${(target / scale) * 100}%`, right: 0 }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${Math.min(1, rate / scale) * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>0 %</span>
          <span>
            toi : {fmt.pct0(rate)} · cible {fmt.pct0(target)}
          </span>
          <span>{fmt.pct0(scale)}</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {d.missing_monthly_eur && d.missing_monthly_eur > 0
          ? `Les ${fmt.eur0(d.missing_monthly_eur)} par mois qui manquent valent ${fmt.eur0(
              d.gap_at_horizon_eur ?? 0,
            )} dans ${d.horizon_years ?? 20} ans à ${fmt.pct0(d.growth_for_horizon ?? 0.05)} par an. `
          : ""}
        À 20 ans, plus de la moitié du capital final vient des versements, pas du rendement. La
        hausse automatique de {fmt.pct0(d.escalation ?? 0.05)} par an (« Save More Tomorrow »)
        porterait ton versement à {fmt.eur0(d.escalated_next_year_eur ?? 0)} l'an prochain.
      </p>
    </div>
  );
}

/* ── Où placer le prochain euro ────────────────────────────────────────── */

function NextEuroDetails({ details: d }: { details: NextEuroVerdictDetails }) {
  const steps = d.steps ?? [];
  const p = d.precaution;
  if (steps.length === 0) return null;
  return (
    <div className="space-y-4">
      {p && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Figure
            label="Sur tes livrets"
            value={fmt.eur0(p.liquid_eur)}
            sub={
              p.months_covered !== null
                ? `${p.months_covered.toFixed(1).replace(".", ",")} mois de dépenses`
                : "dépenses mensuelles inconnues"
            }
          />
          <Figure
            label="Cible de précaution"
            value={p.target_eur !== null ? fmt.eur0(p.target_eur) : "—"}
            sub={`${p.target_months} mois de dépenses`}
          />
          <Figure
            label="Dépenses par mois"
            value={p.monthly_spending_eur !== null ? fmt.eur0(p.monthly_spending_eur) : "—"}
            sub="débits de tes comptes courants, 90 derniers jours"
          />
        </div>
      )}

      <ol className="divide-y rounded-md border text-sm">
        {steps.map((s, i) => (
          <li key={s.id} className="flex items-start gap-3 px-3 py-2.5">
            <span className="mt-0.5 w-4 shrink-0 font-mono text-xs text-muted-foreground">
              {i + 1}
            </span>
            <VerdictDot status={s.status} className="mt-1.5" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="font-medium">{s.label}</span>
                {s.impact_eur_per_year !== null && s.impact_eur_per_year > 0 && (
                  <span className="font-mono text-xs tabular text-muted-foreground">
                    {fmt.eur0(s.impact_eur_per_year)}/an
                  </span>
                )}
              </div>
              <p className="text-muted-foreground">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <p className="text-xs text-muted-foreground">
        La règle, dans l'ordre : précaution sur livrets, puis actions à long terme dans le PEA, puis
        PER seulement au-dessus de la tranche à 30 %, le reste en compte-titres.
        {d.tax?.tmi !== null && d.tax?.tmi !== undefined
          ? ` Ta tranche d'imposition estimée : ${fmt.pct(d.tax.tmi)}, d'après ton revenu fiscal et tes parts.`
          : ""}
      </p>
    </div>
  );
}

/* ── Part d'actions ────────────────────────────────────────────────────── */

function LongRun({ d }: { d: RiskShareVerdictDetails }) {
  if (!d.long_run) return null;
  return (
    <p className="text-xs text-muted-foreground">
      Pourquoi accepter ces variations : de {d.long_run.from_year} à {d.long_run.to_year}, les
      actions ont rapporté{" "}
      <strong className="text-foreground">{fmt.pct(d.long_run.equities)} par an</strong> contre{" "}
      {fmt.pct(d.long_run.bonds)} pour les obligations d'État. C'est ce qui s'est passé, pas ce qui
      se passera.
    </p>
  );
}

function RiskShareDetails({ details: d }: { details: RiskShareVerdictDetails }) {
  if (d.pocket_eur === undefined || d.actual_share === undefined) return null;
  const actual = d.actual_share;
  const target = d.target_share ?? actual;
  const band = d.band ?? 0.1;
  const lo = Math.max(0, target - band);
  const hi = Math.min(1, target + band);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Part d'actions"
          value={fmt.pct0(actual)}
          sub={`${fmt.eur0(d.equity_eur ?? 0)} en lignes cotées sur ${fmt.eur0(d.pocket_eur)}`}
        />
        <Figure
          label="Part visée"
          value={fmt.pct0(target)}
          sub={
            d.horizon_cap !== undefined &&
            d.merton_share !== undefined &&
            d.horizon_cap < d.merton_share
              ? `plafonnée par ton horizon de ${d.horizon_years} ans (${fmt.pct0(d.merton_share)} sinon)`
              : `profil « ${d.risk_label ?? "?"} », horizon ${d.horizon_years ?? 10} ans`
          }
        />
        <Figure
          label="Mauvaise année"
          value={`−${fmt.eur0(d.bad_year_eur ?? 0)}`}
          sub="deux fois la volatilité des actions sur ta poche actions"
        />
      </div>

      {/* Gauge: actual vs target band, same on a phone and a desktop. */}
      <div>
        <div className="relative h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="absolute inset-y-0 bg-[hsl(var(--gain))]/25"
            style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }}
          />
          <div
            className="absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `calc(${target * 100}% - 1px)` }}
          />
          <div
            className="absolute inset-y-0 w-1 rounded-full bg-primary"
            style={{ left: `calc(${actual * 100}% - 2px)` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>0 % actions</span>
          <span>
            bande {fmt.pct0(lo)} – {fmt.pct0(hi)}
          </span>
          <span>100 %</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        La part visée est le point de la droite de marché que ton curseur choisit (volatilité
        maximale de ton cran divisée par celle des actions monde, {fmt.pct(d.equity_sigma ?? 0.15)}
        ). C'est la part de Merton, avec une aversion au risque γ ≈{" "}
        {d.gamma ? d.gamma.toFixed(1).replace(".", ",") : "?"}. Les lignes cotées comptent comme
        actions ; fonds euros, PER ou assurance vie sans détail et PEL comptent comme produits de
        taux.
      </p>
      <LongRun d={d} />
    </div>
  );
}

/* ── Frais réels ───────────────────────────────────────────────────────── */

function FeesDetails({ details: d }: { details: FeesVerdictDetails }) {
  const lines = d.lines ?? [];
  const missing = d.missing_ter ?? [];
  const uncovered = d.uncovered_accounts ?? [];

  if (d.positions_total_eur === undefined) {
    return uncovered.length > 0 ? <Uncovered accounts={uncovered} /> : null;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Figure
          label="Frais des fonds"
          value={fmt.eur0(d.fund_fees_eur ?? 0)}
          sub={`TER de chaque ligne × sa valeur${missing.length ? ", lignes sans TER exclues" : ""}`}
        />
        <Figure
          label="Frais du courtier"
          value={d.broker_known === false ? "—" : fmt.eur0(d.broker_fees_eur ?? 0)}
          sub={
            d.broker_known === false
              ? "banque non renseignée : ses frais ne sont pas comptés"
              : `${d.broker_name ?? "courtier"} : garde, frais par ligne, courtage sur ${fmt.eur(
                  d.monthly_contribution_eur ?? 0,
                )}/mois`
          }
        />
        <Figure
          label="Référence"
          value={fmt.eur0(d.reference_eur ?? 0)}
          sub={`PEA en ligne + ETF monde, ${fmt.pct(d.reference_pct ?? 0)} par an`}
        />
      </div>

      <ul className="divide-y rounded-md border text-sm">
        {lines.map((l) => (
          <li key={`${l.account}-${l.ticker}`} className="flex items-center gap-3 px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="truncate">{l.label}</div>
              <div className="truncate text-xs text-muted-foreground">
                {l.account} · {fmt.eur(l.value_eur)}
              </div>
            </div>
            <div className="shrink-0 text-right">
              {l.ter === null ? (
                <Link to={NAV_PATHS.accounts} className="text-xs text-primary underline">
                  TER à renseigner
                </Link>
              ) : (
                <>
                  <div className="font-mono tabular">{fmt.eur0(l.fund_fee_eur ?? 0)}</div>
                  <div className="font-mono text-xs tabular text-muted-foreground">
                    {fmt.pct(l.ter)} par an
                  </div>
                  {l.ter_source_url && (
                    <a
                      href={l.ter_source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-muted-foreground underline"
                    >
                      source
                    </a>
                  )}
                </>
              )}
            </div>
          </li>
        ))}
      </ul>

      {uncovered.length > 0 && <Uncovered accounts={uncovered} />}

      <p className="text-xs text-muted-foreground">
        Total {fmt.eur0(d.total_fees_eur ?? 0)} par an, soit {fmt.pct(d.total_fees_pct ?? 0)} de{" "}
        {fmt.eur0(d.positions_total_eur)}. Vert jusqu'à {fmt.pct(d.thresholds?.green_max ?? 0)} par
        an, orange jusqu'à {fmt.pct(d.thresholds?.amber_max ?? 0)}. Les frais des fonds sont déjà
        dans les cours : ils ne sont pas retirés une seconde fois de la projection.
      </p>
    </div>
  );
}

function Uncovered({
  accounts,
}: {
  accounts: { name: string; account_type: string; value_eur: number }[];
}) {
  return (
    <div className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
      Non mesuré, le contrat ne détaille pas ses lignes :{" "}
      {accounts.map((a) => `${a.name} (${fmt.eur0(a.value_eur)})`).join(", ")}.
    </div>
  );
}

/* ── Atoms ─────────────────────────────────────────────────────────────── */

function Figure({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-lg font-semibold tabular">{value}</div>
      {sub && <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{sub}</div>}
    </div>
  );
}

function GenericDetails({ verdict }: { verdict: Verdict }) {
  const entries = Object.entries(verdict.details);
  if (entries.length === 0) return null;
  return (
    <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
      {entries.map(([k, v]) => (
        <div key={k} className={cn("rounded-md border px-3 py-2")}>
          <dt className="text-xs text-muted-foreground">{k}</dt>
          <dd className="font-mono tabular">{typeof v === "number" ? fmt.num(v) : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
