import { Settings as SettingsIcon, X } from "lucide-react";
import { useEffect, useState } from "react";

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

const PERIOD_OPTIONS: HistoricalPeriod[] = ["1y", "2y", "3y", "5y", "10y", "max"];

export function SettingsButton() {
  const [settings, setSettings] = useSettings();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<AppSettings>(settings);

  // Sync draft à l'ouverture (au cas où settings ont changé entre temps)
  useEffect(() => {
    if (open) setDraft(settings);
  }, [open, settings]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <SettingsIcon className="h-4 w-4" />
          <span className="hidden sm:inline">Réglages</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Réglages</DialogTitle>
          <DialogDescription>
            Paramètres techniques de l'app. Stockés localement (localStorage), jamais envoyés au
            backend sauf au moment du calcul.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-8 py-4">
          <ScannerSection draft={draft} setDraft={setDraft} />
          <ExpertSection draft={draft} setDraft={setDraft} />
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => setDraft(DEFAULT_SETTINGS)}>
            Réinitialiser
          </Button>
          <div className="flex-1" />
          <Button variant="outline" onClick={() => setOpen(false)}>
            Annuler
          </Button>
          <Button
            onClick={() => {
              setSettings(draft);
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

/* ─── Scanner section ────────────────────────────────────────────────── */

function ScannerSection({
  draft,
  setDraft,
}: {
  draft: AppSettings;
  setDraft: (s: AppSettings) => void;
}) {
  const toggleMode = (m: ScannerMode) => {
    const has = draft.scanner.modes.includes(m);
    const next = has ? draft.scanner.modes.filter((x) => x !== m) : [...draft.scanner.modes, m];
    setDraft({ ...draft, scanner: { ...draft.scanner, modes: next } });
  };

  return (
    <Section
      title="Scanner d'actifs"
      description="Découverte automatique d'actifs qui amélioreraient ton portefeuille."
    >
      <div className="space-y-3">
        <Label className="text-xs text-muted-foreground">
          Modes activés (au moins 1 doit l'être)
        </Label>
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

      <div className="grid grid-cols-2 gap-4 pt-2">
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
  );
}

/* ─── Expert section ─────────────────────────────────────────────────── */

function ExpertSection({
  draft,
  setDraft,
}: {
  draft: AppSettings;
  setDraft: (s: AppSettings) => void;
}) {
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

  return (
    <Section
      title="Expert — Capital Market Assumptions"
      description="Si tu sais ce que tu fais. Tire la frontière efficiente vers tes hypothèses forward-looking au lieu du pur historique 5y."
    >
      <div className="grid grid-cols-2 gap-4">
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

        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Période historique</Label>
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
          <p className="text-[10px] text-muted-foreground">
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

        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Estimateur Σ (covariance)</Label>
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
          <p className="text-[10px] text-muted-foreground">
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

      {/* CMA overrides table */}
      <div className="space-y-2 pt-4 border-t">
        <Label className="text-xs text-muted-foreground">
          Overrides μ par ticker (forward-looking)
        </Label>
        <p className="text-[10px] text-muted-foreground">
          Forcer une espérance de rendement annuel pour un ticker précis (override le YAML CMA).
        </p>

        {Object.entries(draft.expert.cma_overrides).length > 0 && (
          <div className="space-y-1">
            {Object.entries(draft.expert.cma_overrides).map(([ticker, mu]) => (
              <div key={ticker} className="flex items-center gap-2 text-sm font-mono tabular">
                <span className="w-24">{ticker}</span>
                <span className="flex-1">{(mu * 100).toFixed(2)} %</span>
                <button
                  type="button"
                  onClick={() => removeOverride(ticker)}
                  className="text-muted-foreground hover:text-[hsl(var(--loss))]"
                  aria-label="Retirer cet override"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 pt-2">
          <div className="flex-1 space-y-1">
            <Label className="text-xs text-muted-foreground">Ticker</Label>
            <Input
              placeholder="PUST.PA"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              className="font-mono"
            />
          </div>
          <div className="flex-1 space-y-1">
            <Label className="text-xs text-muted-foreground">μ (%)</Label>
            <Input
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

/* ─── Atoms ──────────────────────────────────────────────────────────── */

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
        <h3 className="text-sm font-semibold">{title}</h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <div className="space-y-3 pl-1">{children}</div>
    </div>
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
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
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
      {hint && <p className="text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  );
}
