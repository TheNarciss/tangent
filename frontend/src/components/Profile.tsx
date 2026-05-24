import { User } from "lucide-react";
import { useEffect, useState } from "react";

import { useEligibleEnvelopes, type EnvelopeEligibility } from "@/api";
import {
  ageFromBirthDate,
  EMPTY_PROFILE,
  isProfileComplete,
  useProfile,
  type UserProfile,
} from "@/lib/profile";
import { fmt } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TMI_OPTIONS = [
  { value: "0", label: "0 % — non imposable" },
  { value: "0.11", label: "11 %" },
  { value: "0.30", label: "30 %" },
  { value: "0.41", label: "41 %" },
  { value: "0.45", label: "45 %" },
];

export function ProfileButton() {
  const [profile, setProfile] = useProfile();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<UserProfile>(profile ?? EMPTY_PROFILE);

  useEffect(() => {
    if (open) setDraft(profile ?? EMPTY_PROFILE);
  }, [open, profile]);

  const age = ageFromBirthDate(draft.birth_date);
  const hasMinimumData = !!draft.birth_date && draft.fiscal_shares > 0;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <User className="h-4 w-4" />
          <span className="hidden sm:inline">{profile?.first_name || "Profil"}</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Profil</DialogTitle>
          <DialogDescription>
            Stocké uniquement dans ton navigateur (localStorage). Utilisé pour déterminer tes
            enveloppes éligibles, tes plafonds disponibles, et la pondération de l'optimiseur.
            Jamais envoyé sauf au moment du calcul.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-2">
          <Section title="Identité">
            <Field label="Prénom" htmlFor="first_name">
              <Input
                id="first_name"
                value={draft.first_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, first_name: e.target.value })
                }
              />
            </Field>
            <Field
              label="Date de naissance"
              htmlFor="birth_date"
              hint={age !== null ? `${age} ans` : undefined}
            >
              <Input
                id="birth_date"
                type="date"
                value={draft.birth_date}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, birth_date: e.target.value })
                }
              />
            </Field>
          </Section>

          <Section title="Situation fiscale">
            <Field
              label="Parts fiscales"
              htmlFor="fiscal_shares"
              hint="1 = célibataire, 2 = couple, +0,5 par enfant"
            >
              <Input
                id="fiscal_shares"
                type="number"
                step="0.5"
                min="0.5"
                value={draft.fiscal_shares}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, fiscal_shares: Number(e.target.value) || 1 })
                }
              />
            </Field>
            <Field
              label="RFR N-2 (€)"
              htmlFor="rfr"
              hint="Revenu fiscal de référence, dispo sur ton avis d'imposition"
            >
              <Input
                id="rfr"
                type="number"
                min="0"
                step="500"
                value={draft.rfr_n_minus_2}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, rfr_n_minus_2: Number(e.target.value) || 0 })
                }
              />
            </Field>
            <Field label="TMI (Tranche Marginale d'Imposition)" htmlFor="tmi">
              <Select
                value={String(draft.tmi_pct)}
                onValueChange={(v: string) => setDraft({ ...draft, tmi_pct: Number(v) })}
              >
                <SelectTrigger id="tmi">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TMI_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </Section>

          <Section
            title="Plafonds livrets utilisés"
            description="Soldes actuels de tes livrets (laisse à 0 si tu n'en as pas)."
          >
            <Field label="Livret A (€)" htmlFor="livret_a">
              <Input
                id="livret_a"
                type="number"
                min="0"
                step="100"
                value={draft.ceilings_used.livret_a}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({
                    ...draft,
                    ceilings_used: {
                      ...draft.ceilings_used,
                      livret_a: Number(e.target.value) || 0,
                    },
                  })
                }
              />
            </Field>
            <Field label="Livret A Jeune (€)" htmlFor="livret_a_jeune">
              <Input
                id="livret_a_jeune"
                type="number"
                min="0"
                step="100"
                value={draft.ceilings_used.livret_a_jeune}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({
                    ...draft,
                    ceilings_used: {
                      ...draft.ceilings_used,
                      livret_a_jeune: Number(e.target.value) || 0,
                    },
                  })
                }
              />
            </Field>
            <Field label="LDDS (€)" htmlFor="ldds">
              <Input
                id="ldds"
                type="number"
                min="0"
                step="100"
                value={draft.ceilings_used.ldds}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({
                    ...draft,
                    ceilings_used: { ...draft.ceilings_used, ldds: Number(e.target.value) || 0 },
                  })
                }
              />
            </Field>
            <Field label="LEP (€)" htmlFor="lep">
              <Input
                id="lep"
                type="number"
                min="0"
                step="100"
                value={draft.ceilings_used.lep}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({
                    ...draft,
                    ceilings_used: { ...draft.ceilings_used, lep: Number(e.target.value) || 0 },
                  })
                }
              />
            </Field>
            <Field label="PEL (€)" htmlFor="pel">
              <Input
                id="pel"
                type="number"
                min="0"
                step="100"
                value={draft.ceilings_used.pel}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({
                    ...draft,
                    ceilings_used: { ...draft.ceilings_used, pel: Number(e.target.value) || 0 },
                  })
                }
              />
            </Field>
          </Section>

          <Section
            title="Stratégie d'investissement"
            description="L'optimiseur cherche un portefeuille qui atteint ton objectif sous ta contrainte de risque. Si infaisable, il te le dit."
          >
            <Field
              label="Horizon (années)"
              htmlFor="horizon"
              hint="Durée avant d'utiliser cet argent"
            >
              <Input
                id="horizon"
                type="number"
                min="1"
                max="50"
                step="1"
                value={draft.horizon_years}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, horizon_years: Number(e.target.value) || 1 })
                }
              />
            </Field>
            <Field
              label="Capacité d'épargne (€/mois)"
              htmlFor="dca"
              hint="Combien tu peux verser chaque mois"
            >
              <Input
                id="dca"
                type="number"
                min="0"
                step="50"
                value={draft.monthly_dca}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, monthly_dca: Number(e.target.value) || 0 })
                }
              />
            </Field>
            <Field
              label="Rendement annuel cible (%)"
              htmlFor="target_return"
              hint="Repères : livret 3 %, oblig 4–5 %, ETF actions 7–10 %, Nasdaq histo ~13 %"
            >
              <Input
                id="target_return"
                type="number"
                min="0"
                max="50"
                step="0.5"
                value={draft.target_annual_return}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, target_annual_return: Number(e.target.value) || 0 })
                }
              />
            </Field>
            <Field
              label="Volatilité annuelle max (%)"
              htmlFor="max_vol"
              hint={`Plafond σ. Drawdown attendu ≈ −${(draft.max_annual_volatility * 2).toFixed(0)} % en année stressée. 5 %=prudent · 15 %=actions`}
            >
              <Input
                id="max_vol"
                type="number"
                min="0"
                max="50"
                step="0.5"
                value={draft.max_annual_volatility}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setDraft({ ...draft, max_annual_volatility: Number(e.target.value) || 0 })
                }
              />
            </Field>
          </Section>

          {hasMinimumData && age !== null && (
            <EligibilityPreview
              age={age}
              rfr={draft.rfr_n_minus_2}
              fiscalShares={draft.fiscal_shares}
            />
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          {profile && (
            <Button
              variant="outline"
              onClick={() => {
                setProfile(null);
                setOpen(false);
              }}
            >
              Effacer
            </Button>
          )}
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Annuler
          </Button>
          <Button
            disabled={!isProfileComplete(draft)}
            onClick={() => {
              setProfile(draft);
              setOpen(false);
            }}
          >
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-xs uppercase tracking-wider text-muted-foreground">{title}</h3>
        {description && <p className="text-[11px] text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{children}</div>
    </div>
  );
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
    <div className="space-y-1">
      <Label htmlFor={htmlFor} className="text-xs">
        {label}
      </Label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function EligibilityPreview({
  age,
  rfr,
  fiscalShares,
}: {
  age: number;
  rfr: number;
  fiscalShares: number;
}) {
  const q = useEligibleEnvelopes({ age, rfr, fiscal_shares: fiscalShares });

  return (
    <div className="rounded-md border bg-card/40 p-4">
      <h3 className="text-xs uppercase tracking-wider text-muted-foreground mb-3">
        Enveloppes éligibles selon ton profil
      </h3>
      {q.isLoading && <p className="text-xs text-muted-foreground">Vérification…</p>}
      {q.data && (
        <ul className="space-y-1.5 text-sm">
          {q.data.envelopes.map((e) => (
            <EnvelopeRow key={e.id} env={e} />
          ))}
        </ul>
      )}
      {q.isError && (
        <p className="text-xs text-[hsl(var(--loss))]">Vérifie que le backend tourne.</p>
      )}
    </div>
  );
}

function EnvelopeRow({ env }: { env: EnvelopeEligibility }) {
  return (
    <li
      className={`flex flex-wrap items-baseline gap-x-3 gap-y-0.5 ${env.eligible ? "" : "opacity-40"}`}
    >
      <span className="font-mono">{env.eligible ? "✓" : "✗"}</span>
      <span className="font-medium">{env.name}</span>
      <span className="font-mono tabular text-xs text-muted-foreground">
        {fmt.pct(env.rate_pct)}
      </span>
      {env.ceiling_eur !== null && (
        <span className="font-mono tabular text-xs text-muted-foreground">
          plafond {fmt.eur(env.ceiling_eur)}
        </span>
      )}
      <span className="text-xs text-muted-foreground italic basis-full sm:basis-auto sm:ml-auto">
        {env.note}
      </span>
    </li>
  );
}
