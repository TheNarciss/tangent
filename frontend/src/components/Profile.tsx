import { useEffect, useState } from "react";
import { ArrowLeft, Calculator, Shield, Target, User } from "lucide-react";
import { useBrokers } from "@/api";
import { useEligibleEnvelopes, type EnvelopeEligibility } from "@/api";
import { fmt } from "@/lib/format";
import {
  ageFromBirthDate,
  EMPTY_PROFILE,
  isProfileComplete,
  useProfile,
  type UserProfile,
} from "@/lib/profile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AccountTab } from "@/components/AccountTab";

const TMI_OPTIONS = [
  { value: "0", label: "0 % — non imposable" },
  { value: "0.11", label: "11 %" },
  { value: "0.30", label: "30 %" },
  { value: "0.41", label: "41 %" },
  { value: "0.45", label: "45 %" },
];

const LIVRETS = [
  ["livret_a", "Livret A"],
  ["livret_a_jeune", "Livret A Jeune"],
  ["ldds", "LDDS"],
  ["lep", "LEP"],
  ["pel", "PEL"],
] as const;

interface ProfilePageProps {
  onBack: () => void;
}

/** Page « Mon profil » — données utilisateur (qui je suis, situation, stratégie, compte).
 *
 * 4 sous-onglets : Identité, Fiscalité, Stratégie, Mon compte. Pattern draft + sticky
 * footer save : tant que des modifs sont en attente, un bandeau bas propose Annuler /
 * Enregistrer. Si l'user navigue avant save, on confirme pour ne rien perdre.
 */
export function ProfilePage({ onBack }: ProfilePageProps) {
  const [profile, setProfile] = useProfile();
  const [draft, setDraft] = useState<UserProfile>(profile ?? EMPTY_PROFILE);

  // Resync le draft si le profile change depuis l'extérieur (sync DB, autre tab)
  useEffect(() => {
    setDraft(profile ?? EMPTY_PROFILE);
  }, [profile]);

  const isDirty = JSON.stringify(draft) !== JSON.stringify(profile ?? EMPTY_PROFILE);

  const handleBack = () => {
    if (
      isDirty &&
      !window.confirm("Tu as des modifications non sauvegardées. Quitter sans enregistrer ?")
    ) {
      return;
    }
    onBack();
  };

  const handleSave = () => setProfile(draft);
  const handleReset = () => setDraft(profile ?? EMPTY_PROFILE);

  return (
    <div className="min-h-screen bg-background">
      <div className="container max-w-4xl py-8 pb-32">
        {/* Header */}
        <header className="flex items-start gap-3 mb-8">
          <Button variant="ghost" size="sm" onClick={handleBack} className="gap-2 mt-0.5">
            <ArrowLeft className="h-4 w-4" />
            Retour
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight">Mon profil</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Données qui alimentent les calculs (éligibilité, optimiseur, projections). Stockées
              dans ton navigateur et synchronisées avec ton compte.
            </p>
          </div>
        </header>

        {/* Sub-tabs */}
        <Tabs defaultValue="identity" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="identity" className="gap-2">
              <User className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Identité</span>
            </TabsTrigger>
            <TabsTrigger value="fiscal" className="gap-2">
              <Calculator className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Fiscalité</span>
            </TabsTrigger>
            <TabsTrigger value="strategy" className="gap-2">
              <Target className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Stratégie</span>
            </TabsTrigger>
            <TabsTrigger value="account" className="gap-2">
              <Shield className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Mon compte</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="identity" className="space-y-8 mt-6">
            <IdentityTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="fiscal" className="space-y-8 mt-6">
            <FiscalTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="strategy" className="space-y-8 mt-6">
            <StrategyTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="account" className="space-y-8 mt-6">
            <AccountTab />
          </TabsContent>
        </Tabs>
      </div>

      {/* Sticky footer : visible uniquement si modifs */}
      {isDirty && (
        <div className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur border-t z-50">
          <div className="container max-w-4xl py-3 flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">Modifications non enregistrées</p>
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
/*  Sub-tab content                                                          */
/* ────────────────────────────────────────────────────────────────────────── */

interface TabProps {
  draft: UserProfile;
  setDraft: (p: UserProfile) => void;
}

function IdentityTab({ draft, setDraft }: TabProps) {
  const age = ageFromBirthDate(draft.birth_date);
  return (
    <Section
      title="Identité"
      description="Données de base. L'âge est calculé automatiquement et conditionne notamment l'éligibilité au Livret A Jeune."
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Prénom" htmlFor="first_name">
          <Input
            id="first_name"
            value={draft.first_name}
            onChange={(e) => setDraft({ ...draft, first_name: e.target.value })}
            placeholder="Ton prénom"
          />
        </Field>
        <Field
          label="Date de naissance"
          htmlFor="birth_date"
          hint={age !== null ? `${age} ans` : "Pour calculer ton âge"}
        >
          <Input
            id="birth_date"
            type="date"
            value={draft.birth_date}
            onChange={(e) => setDraft({ ...draft, birth_date: e.target.value })}
          />
        </Field>
      </div>
    </Section>
  );
}

function FiscalTab({ draft, setDraft }: TabProps) {
  const age = ageFromBirthDate(draft.birth_date);
  const hasMinimumData = !!draft.birth_date && draft.fiscal_shares > 0;
  return (
    <>
      <Section
        title="Situation fiscale"
        description="Détermine ta TMI, ton éligibilité LEP, et l'optimisation fiscale de l'optimiseur."
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field
            label="Parts fiscales"
            htmlFor="fiscal_shares"
            hint="1 = célibataire · 2 = couple · +0,5 par enfant"
          >
            <Input
              id="fiscal_shares"
              type="number"
              step="0.5"
              min="0.5"
              value={draft.fiscal_shares}
              onChange={(e) => setDraft({ ...draft, fiscal_shares: Number(e.target.value) || 1 })}
            />
          </Field>
          <Field
            label="RFR N-2 (€)"
            htmlFor="rfr"
            hint="Revenu fiscal de référence — sur ton avis d'imposition"
          >
            <Input
              id="rfr"
              type="number"
              min="0"
              step="500"
              value={draft.rfr_n_minus_2}
              onChange={(e) => setDraft({ ...draft, rfr_n_minus_2: Number(e.target.value) || 0 })}
            />
          </Field>
          <Field
            label="TMI (Tranche Marginale d'Imposition)"
            htmlFor="tmi"
            hint="Tranche la plus haute appliquée à tes revenus"
          >
            <Select
              value={String(draft.tmi_pct)}
              onValueChange={(v) => setDraft({ ...draft, tmi_pct: Number(v) })}
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
        </div>
      </Section>

      <Section
        title="Plafonds livrets utilisés"
        description="Soldes actuels de tes livrets réglementés. Sert à connaître ta marge disponible pour chacun. Laisse à 0 si tu n'en as pas."
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
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
                    ceilings_used: {
                      ...draft.ceilings_used,
                      [key]: Number(e.target.value) || 0,
                    },
                  })
                }
              />
            </Field>
          ))}
        </div>
      </Section>

      {hasMinimumData && age !== null && (
        <EligibilityPreview
          age={age}
          rfr={draft.rfr_n_minus_2}
          fiscalShares={draft.fiscal_shares}
        />
      )}
    </>
  );
}

function StrategyTab({ draft, setDraft }: TabProps) {
  const brokersQuery = useBrokers();
  return (
    <Section
      title="Stratégie d'investissement"
      description="L'optimiseur cherche un portefeuille qui atteint ton objectif de rendement sous ta contrainte de risque. Si infaisable, il te le dit."
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Horizon (années)" htmlFor="horizon" hint="Durée avant d'utiliser cet argent">
          <Input
            id="horizon"
            type="number"
            min="1"
            max="50"
            step="1"
            value={draft.horizon_years}
            onChange={(e) => setDraft({ ...draft, horizon_years: Number(e.target.value) || 1 })}
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
            onChange={(e) => setDraft({ ...draft, monthly_dca: Number(e.target.value) || 0 })}
          />
        </Field>
        <Field
          label="Rendement annuel cible (%)"
          htmlFor="target_return"
          hint="Repères : livret 3 % · oblig 4–5 % · ETF actions 7–10 % · Nasdaq histo ~13 %"
        >
          <Input
            id="target_return"
            type="number"
            min="0"
            max="50"
            step="0.5"
            value={draft.target_annual_return}
            onChange={(e) =>
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
            onChange={(e) =>
              setDraft({ ...draft, max_annual_volatility: Number(e.target.value) || 0 })
            }
          />
        </Field>
        <Field
          label="Courtier principal"
          htmlFor="default_broker"
          hint="Auto-détecté à la 1re synchro selon ta banque. Sert au calcul des frais en Projection."
        >
          <Select
            value={draft.default_broker ?? "__auto__"}
            onValueChange={(v: string) =>
              setDraft({ ...draft, default_broker: v === "__auto__" ? null : v })
            }
            disabled={brokersQuery.isLoading}
          >
            <SelectTrigger id="default_broker">
              <SelectValue placeholder="Chargement…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__auto__">Auto-détection (recommandé)</SelectItem>
              {brokersQuery.data?.brokers.map((b: { id: string; name: string }) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
    </Section>
  );
}

/* ────────────────────────────────────────────────────────────────────────── */
/*  Atoms                                                                     */
/* ────────────────────────────────────────────────────────────────────────── */

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
    <section className="space-y-4">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        {description && (
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{description}</p>
        )}
      </div>
      <div>{children}</div>
    </section>
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
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-xs">
        {label}
      </Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground leading-relaxed">{hint}</p>}
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
    <Section
      title="Enveloppes éligibles selon ton profil"
      description="Calculé en direct depuis ton âge, RFR et parts fiscales."
    >
      {q.isLoading && <p className="text-sm text-muted-foreground">Vérification…</p>}
      {q.data && (
        <ul className="space-y-2">
          {q.data.envelopes.map((e) => (
            <EnvelopeRow key={e.id} env={e} />
          ))}
        </ul>
      )}
      {q.isError && (
        <p className="text-sm text-[hsl(var(--loss))]">
          Impossible de calculer l&apos;éligibilité. Vérifie que le backend tourne.
        </p>
      )}
    </Section>
  );
}

function EnvelopeRow({ env }: { env: EnvelopeEligibility }) {
  return (
    <li
      className={`flex flex-wrap items-baseline gap-x-3 gap-y-0.5 rounded-md border px-3 py-2 text-sm ${
        env.eligible ? "" : "opacity-50"
      }`}
    >
      <span className="font-mono w-5 text-center">{env.eligible ? "✓" : "✗"}</span>
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
