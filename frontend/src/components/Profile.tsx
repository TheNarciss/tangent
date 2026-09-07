import { useEffect, useState } from "react";

import { useRiskLevels, useWealthSummary, type RiskLevel } from "@/api";
import { fmt } from "@/lib/format";
import {
  ageFromBirthDate,
  EMPTY_PROFILE,
  fiscalSharesFor,
  isProfileComplete,
  useProfile,
  type CeilingsUsed,
  type HouseholdStatus,
  type UserProfile,
} from "@/lib/profile";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LIVRETS: [keyof CeilingsUsed, string][] = [
  ["livret_a", "Livret A"],
  ["ldds", "LDDS"],
  ["lep", "LEP"],
  ["pel", "PEL"],
  ["livret_a_jeune", "Livret A Jeune"],
];

/** Page « Mon profil » — les 5 réponses dont Tangent a besoin pour calculer juste.
 *
 * Pattern draft + sticky footer : tant que des modifs sont en attente, un bandeau
 * bas propose Annuler / Enregistrer. Le titre de page est porté par AppShell.
 */
export function ProfilePage() {
  const [profile, setProfile] = useProfile();
  const [draft, setDraft] = useState<UserProfile>(profile ?? EMPTY_PROFILE);
  const riskLevels = useRiskLevels();

  // Resync le draft si le profile change depuis l'extérieur (sync DB, autre tab)
  useEffect(() => {
    setDraft(profile ?? EMPTY_PROFILE);
  }, [profile]);

  const isDirty = JSON.stringify(draft) !== JSON.stringify(profile ?? EMPTY_PROFILE);
  const handleSave = () => setProfile(draft);
  const handleReset = () => setDraft(profile ?? EMPTY_PROFILE);

  const age = ageFromBirthDate(draft.birth_date);
  const setHousehold = (status: HouseholdStatus, children: number) =>
    setDraft({
      ...draft,
      household_status: status,
      children,
      fiscal_shares: fiscalSharesFor(status, children),
    });
  const setRiskLevel = (level: number) => {
    const lv = riskLevels.data?.find((l) => l.level === level);
    setDraft({
      ...draft,
      risk_level: level,
      // Mirror the derived pair so the optimizer works before the server echoes it
      ...(lv
        ? {
            target_annual_return: lv.target_annual_return * 100,
            max_annual_volatility: lv.max_annual_volatility * 100,
          }
        : {}),
    });
  };

  return (
    <div>
      <div className="mx-auto max-w-2xl space-y-8 pb-24">
        <Section
          title="1 · Ta date de naissance"
          description="Ton âge conditionne les livrets auxquels tu as droit et l'horizon de tes placements."
        >
          <Field
            label="Date de naissance"
            htmlFor="birth_date"
            hint={age !== null ? `${age} ans` : "Obligatoire pour enregistrer"}
          >
            <Input
              id="birth_date"
              type="date"
              value={draft.birth_date}
              onChange={(e) => setDraft({ ...draft, birth_date: e.target.value })}
              className="sm:max-w-xs"
            />
          </Field>
        </Section>

        <Section
          title="2 · Ton foyer"
          description="Sert à calculer tes parts fiscales, et donc les plafonds de revenu des livrets (LEP)."
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Situation" htmlFor="household">
              <Select
                value={draft.household_status}
                onValueChange={(v: HouseholdStatus) => setHousehold(v, draft.children)}
              >
                <SelectTrigger id="household">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Célibataire</SelectItem>
                  <SelectItem value="couple">En couple (marié·e ou pacsé·e)</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field
              label="Enfants à charge"
              htmlFor="children"
              hint={`= ${fmtShares(draft.fiscal_shares)} fiscale${draft.fiscal_shares > 1 ? "s" : ""}`}
            >
              <Input
                id="children"
                type="number"
                min="0"
                max="20"
                step="1"
                value={draft.children}
                onChange={(e) =>
                  setHousehold(draft.household_status, Math.max(0, Number(e.target.value) || 0))
                }
              />
            </Field>
          </div>
        </Section>

        <Section
          title="3 · Ton revenu fiscal de référence"
          description="Il est écrit sur la première page de ton avis d'imposition (« Revenu fiscal de référence »). Prends celui d'il y a deux ans."
        >
          <Field label="Revenu fiscal de référence (€)" htmlFor="rfr">
            <Input
              id="rfr"
              type="number"
              min="0"
              step="500"
              value={draft.rfr_n_minus_2}
              onChange={(e) => setDraft({ ...draft, rfr_n_minus_2: Number(e.target.value) || 0 })}
              className="sm:max-w-xs"
            />
          </Field>
        </Section>

        <Section
          title="4 · Ce que tu mets de côté chaque mois"
          description="Le versement que Tangent utilise pour projeter ton épargne."
        >
          <Field label="Épargne mensuelle (€ / mois)" htmlFor="dca">
            <Input
              id="dca"
              type="number"
              min="0"
              step="50"
              value={draft.monthly_dca}
              onChange={(e) => setDraft({ ...draft, monthly_dca: Number(e.target.value) || 0 })}
              className="sm:max-w-xs"
            />
          </Field>
        </Section>

        <Section
          title="5 · Prudent ou dynamique ?"
          description="Plus tu vas vers « dynamique », plus Tangent accepte que ton épargne varie d'une année à l'autre, en échange d'un rendement visé plus élevé."
        >
          <RiskSlider
            value={draft.risk_level}
            levels={riskLevels.data}
            fallback={{
              target_annual_return: draft.target_annual_return / 100,
              max_annual_volatility: draft.max_annual_volatility / 100,
            }}
            onChange={setRiskLevel}
          />
        </Section>

        <LivretsSection draft={draft} setDraft={setDraft} />
      </div>

      {/* Sticky footer : visible uniquement si modifs */}
      {isDirty && (
        <div className="fixed inset-x-0 bottom-16 z-40 border-t bg-background/95 backdrop-blur md:bottom-0 md:pb-[env(safe-area-inset-bottom)]">
          <div className="mx-auto flex max-w-2xl items-center justify-between gap-3 px-4 py-3">
            <p className="text-sm text-muted-foreground">
              {isProfileComplete(draft)
                ? "Modifications non enregistrées"
                : "Renseigne ta date de naissance pour enregistrer"}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleReset}>
                Annuler
              </Button>
              <Button size="sm" onClick={handleSave} disabled={!isProfileComplete(draft)}>
                Enregistrer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Risk slider                                                              */
/* ────────────────────────────────────────────────────────────────────────── */

function RiskSlider({
  value,
  levels,
  fallback,
  onChange,
}: {
  value: number;
  levels: RiskLevel[] | undefined;
  fallback: { target_annual_return: number; max_annual_volatility: number };
  onChange: (level: number) => void;
}) {
  const max = levels?.length ?? 5;
  const current = levels?.find((l) => l.level === value);
  const target = current?.target_annual_return ?? fallback.target_annual_return;
  const vol = current?.max_annual_volatility ?? fallback.max_annual_volatility;

  return (
    <div className="space-y-3">
      <input
        id="risk_level"
        type="range"
        min={1}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Niveau de risque"
        className="h-2 w-full cursor-pointer accent-primary"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Prudent</span>
        <span className="font-medium text-foreground">{current?.label ?? `Niveau ${value}`}</span>
        <span>Dynamique</span>
      </div>
      <p className="text-sm text-muted-foreground">
        Tangent vise environ <strong className="text-foreground">{wholePct(target)}</strong> par an
        et accepte des variations jusqu'à{" "}
        <strong className="text-foreground">±{wholePct(vol)}</strong> sur une année.
      </p>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Livrets : lus depuis les comptes synchronisés, saisie manuelle en repli    */
/* ────────────────────────────────────────────────────────────────────────── */

function LivretsSection({
  draft,
  setDraft,
}: {
  draft: UserProfile;
  setDraft: (p: UserProfile) => void;
}) {
  const wealth = useWealthSummary();
  const synced = wealth.data?.envelopes ?? [];

  if (synced.length > 0) {
    return (
      <Section
        title="Tes livrets"
        description="Lus automatiquement depuis tes comptes connectés : rien à saisir."
      >
        <ul className="divide-y rounded-md border text-sm">
          {synced.map((e, i) => (
            <li key={i} className="flex items-center justify-between gap-3 px-3 py-2">
              <span className="truncate">{e.display_name ?? e.name}</span>
              <span className="font-mono tabular">{fmt.eur(e.balance)}</span>
            </li>
          ))}
        </ul>
      </Section>
    );
  }

  return (
    <Section
      title="Tes livrets"
      description="Aucun livret synchronisé pour l'instant. Si tu en as ailleurs, indique leurs soldes pour que Tangent connaisse ta marge disponible. Laisse à 0 sinon."
    >
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {LIVRETS.map(([key, label]) => (
          <Field key={key} label={`${label} (€)`} htmlFor={key}>
            <Input
              id={key}
              type="number"
              min="0"
              step="100"
              value={draft.ceilings_used[key]}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  ceilings_used: { ...draft.ceilings_used, [key]: Number(e.target.value) || 0 },
                })
              }
            />
          </Field>
        ))}
      </div>
    </Section>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Atoms                                                                     */
/* ────────────────────────────────────────────────────────────────────────── */

function wholePct(fraction: number): string {
  return `${Math.round(fraction * 100)} %`;
}

function fmtShares(n: number): string {
  return `${n.toLocaleString("fr-FR")} part${n > 1 ? "s" : ""}`;
}

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-xs">
        {label}
      </Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground leading-relaxed">{hint}</p>}
    </div>
  );
}
