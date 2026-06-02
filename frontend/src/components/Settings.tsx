import { useEffect, useState } from "react";
import { ArrowLeft, Palette, Radar, Settings2, Sliders, X } from "lucide-react";

import {
  DEFAULT_SETTINGS,
  SCANNER_MODE_LABELS,
  useSettings,
  type AppSettings,
  type CovEstimator,
  type HistoricalPeriod,
  type ScannerMode,
} from "@/lib/settings";
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

const PERIOD_OPTIONS: HistoricalPeriod[] = ["1y", "2y", "3y", "5y", "10y", "max"];

interface SettingsPageProps {
  onBack: () => void;
}

/** Page « Réglages » — paramètres techniques de l'app.
 *
 * 4 sous-onglets : Scanner, Modèle (CMA), Overrides, Préférences. Pattern draft + sticky
 * footer save identique à ProfilePage.
 */
export function SettingsPage({ onBack }: SettingsPageProps) {
  const [settings, setSettings] = useSettings();
  const [draft, setDraft] = useState<AppSettings>(settings);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const isDirty = JSON.stringify(draft) !== JSON.stringify(settings);

  const handleBack = () => {
    if (
      isDirty &&
      !window.confirm("Tu as des modifications non sauvegardées. Quitter sans enregistrer ?")
    ) {
      return;
    }
    onBack();
  };

  const handleSave = () => setSettings(draft);
  const handleReset = () => setDraft(settings);
  const handleResetDefaults = () => setDraft(DEFAULT_SETTINGS);

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
            <h1 className="text-2xl font-semibold tracking-tight">Réglages</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Paramètres techniques de l&apos;app : comment les algos calculent et ce qui
              s&apos;affiche. Stockés localement.
            </p>
          </div>
        </header>

        <Tabs defaultValue="scanner" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="scanner" className="gap-2">
              <Radar className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Scanner</span>
            </TabsTrigger>
            <TabsTrigger value="cma" className="gap-2">
              <Sliders className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Modèle CMA</span>
            </TabsTrigger>
            <TabsTrigger value="overrides" className="gap-2">
              <Settings2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Overrides</span>
            </TabsTrigger>
            <TabsTrigger value="prefs" className="gap-2">
              <Palette className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Préférences</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="scanner" className="space-y-8 mt-6">
            <ScannerTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="cma" className="space-y-8 mt-6">
            <CmaTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="overrides" className="space-y-8 mt-6">
            <OverridesTab draft={draft} setDraft={setDraft} />
          </TabsContent>

          <TabsContent value="prefs" className="space-y-8 mt-6">
            <PreferencesTab />
          </TabsContent>
        </Tabs>

        {/* Reset to defaults — placé à l'écart du save/cancel pour éviter le clic accidentel */}
        <div className="mt-12 pt-6 border-t">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetDefaults}
            className="text-muted-foreground hover:text-foreground"
          >
            Restaurer les valeurs par défaut
          </Button>
        </div>
      </div>

      {/* Sticky footer */}
      {isDirty && (
        <div className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur border-t z-50">
          <div className="container max-w-4xl py-3 flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">Modifications non enregistrées</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleReset}>
                Annuler
              </Button>
              <Button size="sm" onClick={handleSave}>
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
  draft: AppSettings;
  setDraft: (s: AppSettings) => void;
}

function ScannerTab({ draft, setDraft }: TabProps) {
  const toggleMode = (m: ScannerMode) => {
    const has = draft.scanner.modes.includes(m);
    const next = has ? draft.scanner.modes.filter((x) => x !== m) : [...draft.scanner.modes, m];
    if (next.length === 0) return; // au moins 1 mode requis
    setDraft({ ...draft, scanner: { ...draft.scanner, modes: next } });
  };

  return (
    <>
      <Section
        title="Scanner d'actifs"
        description="Découverte automatique d'actifs qui amélioreraient ton portefeuille."
      >
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">Modes activés (au moins 1 requis)</Label>
          <div className="space-y-2">
            {(Object.keys(SCANNER_MODE_LABELS) as ScannerMode[]).map((m) => {
              const checked = draft.scanner.modes.includes(m);
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => toggleMode(m)}
                  className={[
                    "w-full text-left rounded-md border px-3 py-2 text-sm transition",
                    checked
                      ? "bg-[hsl(var(--gain))]/15 border-[hsl(var(--gain))]"
                      : "hover:bg-muted/40",
                  ].join(" ")}
                >
                  <span className="font-mono mr-2">{checked ? "☑" : "☐"}</span>
                  {SCANNER_MODE_LABELS[m]}
                </button>
              );
            })}
          </div>
        </div>
      </Section>

      <Section title="Paramètres du scan" description="Ajuste la sensibilité et la verbosité.">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <NumField
            label="Hypothèse d'ajout (%)"
            hint="Pour calcul ΔSharpe : on simule l'ajout de X % du candidat"
            value={draft.scanner.hypothesis_fraction * 100}
            step={5}
            min={1}
            max={50}
            onChange={(v) =>
              setDraft({
                ...draft,
                scanner: { ...draft.scanner, hypothesis_fraction: v / 100 },
              })
            }
          />
          <NumField
            label="Nombre de candidats"
            hint="Top N à afficher après ranking"
            value={draft.scanner.n_results}
            step={1}
            min={3}
            max={50}
            onChange={(v) => setDraft({ ...draft, scanner: { ...draft.scanner, n_results: v } })}
          />
        </div>
      </Section>
    </>
  );
}

function CmaTab({ draft, setDraft }: TabProps) {
  return (
    <>
      <Section
        title="Capital Market Assumptions"
        description="Tire la frontière efficiente vers tes hypothèses forward-looking au lieu du pur historique."
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <NumField
            label="Shrinkage CMA (%)"
            hint="0 = pure historique · 100 = pure CMA long-terme"
            value={draft.expert.cma_shrinkage * 100}
            step={5}
            min={0}
            max={100}
            onChange={(v) =>
              setDraft({ ...draft, expert: { ...draft.expert, cma_shrinkage: v / 100 } })
            }
          />

          <div className="space-y-1.5">
            <Label className="text-xs">Période historique</Label>
            <Select
              value={draft.expert.historical_period}
              onValueChange={(v: HistoricalPeriod) =>
                setDraft({ ...draft, expert: { ...draft.expert, historical_period: v } })
              }
            >
              <SelectTrigger className="font-mono tabular">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PERIOD_OPTIONS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Période pour calculer σ et corrélations
            </p>
          </div>

          <NumField
            label="Taux sans risque r_f (%)"
            hint="Utilisé par Sharpe et Kelly. ECB deposit rate ≈ 2.5 %"
            value={draft.expert.risk_free_rate * 100}
            step={0.1}
            min={0}
            max={10}
            onChange={(v) =>
              setDraft({ ...draft, expert: { ...draft.expert, risk_free_rate: v / 100 } })
            }
          />

          <div className="space-y-1.5">
            <Label className="text-xs">Estimateur Σ (covariance)</Label>
            <Select
              value={draft.expert.cov_estimator}
              onValueChange={(v: CovEstimator) =>
                setDraft({ ...draft, expert: { ...draft.expert, cov_estimator: v } })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sample">Sample (classique)</SelectItem>
                <SelectItem value="shrunk">Shrunk (Ledoit-Wolf simplifié)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[11px] text-muted-foreground">
              Shrunk stabilise Σ si historique court
            </p>
          </div>

          {draft.expert.cov_estimator === "shrunk" && (
            <NumField
              label="Shrinkage Σ (%)"
              hint="Fraction de tirage vers la diagonale (identité × variance moyenne)"
              value={draft.expert.cov_shrinkage * 100}
              step={5}
              min={0}
              max={100}
              onChange={(v) =>
                setDraft({ ...draft, expert: { ...draft.expert, cov_shrinkage: v / 100 } })
              }
            />
          )}
        </div>
      </Section>
    </>
  );
}

function OverridesTab({ draft, setDraft }: TabProps) {
  const [newTicker, setNewTicker] = useState("");
  const [newMu, setNewMu] = useState<number | "">("");

  const addOverride = () => {
    if (!newTicker.trim() || newMu === "" || Number(newMu) <= 0) return;
    setDraft({
      ...draft,
      expert: {
        ...draft.expert,
        cma_overrides: {
          ...draft.expert.cma_overrides,
          [newTicker.trim().toUpperCase()]: Number(newMu) / 100,
        },
      },
    });
    setNewTicker("");
    setNewMu("");
  };

  const removeOverride = (ticker: string) => {
    const next = { ...draft.expert.cma_overrides };
    delete next[ticker];
    setDraft({ ...draft, expert: { ...draft.expert, cma_overrides: next } });
  };

  const entries = Object.entries(draft.expert.cma_overrides);

  return (
    <Section
      title="Overrides μ par ticker"
      description="Force une espérance de rendement annuel pour un ticker précis (prioritaire sur le YAML CMA et l'historique)."
    >
      {entries.length === 0 ? (
        <div className="rounded-md border border-dashed py-6 text-center text-sm text-muted-foreground">
          Aucun override actif.
        </div>
      ) : (
        <div className="rounded-md border divide-y">
          {entries.map(([ticker, mu]) => (
            <div
              key={ticker}
              className="flex items-center gap-3 px-3 py-2 text-sm font-mono tabular"
            >
              <span className="w-28 font-medium">{ticker}</span>
              <span className="flex-1 text-muted-foreground">μ = {(mu * 100).toFixed(2)} %</span>
              <button
                type="button"
                onClick={() => removeOverride(ticker)}
                className="text-muted-foreground hover:text-[hsl(var(--loss))] p-1"
                aria-label={`Retirer l'override pour ${ticker}`}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="pt-4 space-y-3 border-t mt-6">
        <Label className="text-xs">Ajouter un override</Label>
        <div className="flex items-end gap-2">
          <div className="flex-1 space-y-1">
            <Label htmlFor="new_ticker" className="text-[11px] text-muted-foreground">
              Ticker
            </Label>
            <Input
              id="new_ticker"
              placeholder="PUST.PA"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              className="font-mono"
            />
          </div>
          <div className="flex-1 space-y-1">
            <Label htmlFor="new_mu" className="text-[11px] text-muted-foreground">
              μ (%)
            </Label>
            <Input
              id="new_mu"
              type="number"
              step={0.1}
              placeholder="8.0"
              value={newMu}
              onChange={(e) => {
                const raw = e.target.value;
                setNewMu(raw === "" ? "" : Number(raw));
              }}
              className="font-mono tabular"
            />
          </div>
          <Button variant="outline" size="sm" onClick={addOverride}>
            Ajouter
          </Button>
        </div>
      </div>
    </Section>
  );
}

function PreferencesTab() {
  return (
    <Section
      title="Préférences"
      description="Thème, devise, format des chiffres. Sera enrichi dans une prochaine itération."
    >
      <div className="rounded-md border bg-muted/30 p-8 text-center">
        <Palette className="h-10 w-10 mx-auto text-muted-foreground/60 mb-3" />
        <p className="text-sm font-medium">Section en cours de développement</p>
        <p className="text-xs text-muted-foreground mt-2 max-w-md mx-auto leading-relaxed">
          Pour l&apos;instant, le thème suit automatiquement les réglages de ton OS. Choix manuel
          light / dark / system, devise et format des chiffres arrivent prochainement.
        </p>
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

function NumField({
  label,
  hint,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) onChange(n);
        }}
        className="font-mono tabular"
      />
      {hint && <p className="text-[11px] text-muted-foreground leading-relaxed">{hint}</p>}
    </div>
  );
}
