import { useState } from "react";
import { X } from "lucide-react";

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

const PERIOD_OPTIONS: HistoricalPeriod[] = ["1y", "2y", "3y", "5y", "10y", "max"];

/**
 * « Options avancées » du Scanner (ex-écran Réglages) : modes, hypothèse
 * d'ajout, modèle CMA, overrides μ. Replié par défaut ; les changements sont
 * enregistrés immédiatement (localStorage, cf. lib/settings.ts).
 */
type SettingsProps = {
  settings: AppSettings;
  setSettings: (s: AppSettings) => void;
};

export function ScannerOptions() {
  const [settings, setSettings] = useSettings();
  const props = { settings, setSettings };

  return (
    <details className="group rounded-md border bg-muted/20">
      <summary className="flex cursor-pointer select-none items-center justify-between px-3 py-2 text-sm font-medium">
        Options avancées
        <span className="text-xs font-normal text-muted-foreground group-open:hidden">
          modes, hypothèses, modèle
        </span>
      </summary>
      <div className="space-y-6 border-t px-3 py-4">
        <ModesBlock {...props} />
        <ScanParamsBlock {...props} />
        <ModelBlock {...props} />
        <OverridesBlock {...props} />
        <div className="border-t pt-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSettings(DEFAULT_SETTINGS)}
            className="text-muted-foreground hover:text-foreground"
          >
            Restaurer les valeurs par défaut
          </Button>
        </div>
      </div>
    </details>
  );
}

function ModesBlock({ settings, setSettings }: SettingsProps) {
  const toggleMode = (m: ScannerMode) => {
    const has = settings.scanner.modes.includes(m);
    const next = has
      ? settings.scanner.modes.filter((x) => x !== m)
      : [...settings.scanner.modes, m];
    if (next.length === 0) return; // au moins 1 mode requis
    setSettings({ ...settings, scanner: { ...settings.scanner, modes: next } });
  };
  return (
    <Block title="Où chercher" hint="Au moins un mode.">
      <div className="space-y-2">
        {(Object.keys(SCANNER_MODE_LABELS) as ScannerMode[]).map((m) => {
          const checked = settings.scanner.modes.includes(m);
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
    </Block>
  );
}

function ScanParamsBlock({ settings, setSettings }: SettingsProps) {
  return (
    <Block title="Paramètres du scan">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NumField
          label="Hypothèse d'ajout (%)"
          hint="Pour calcul ΔSharpe : on simule l'ajout de X % du candidat"
          value={settings.scanner.hypothesis_fraction * 100}
          step={5}
          min={1}
          max={50}
          onChange={(v) =>
            setSettings({
              ...settings,
              scanner: { ...settings.scanner, hypothesis_fraction: v / 100 },
            })
          }
        />
        <NumField
          label="Nombre de candidats"
          hint="Top N à afficher après ranking"
          value={settings.scanner.n_results}
          step={1}
          min={3}
          max={50}
          onChange={(v) =>
            setSettings({ ...settings, scanner: { ...settings.scanner, n_results: v } })
          }
        />
      </div>
    </Block>
  );
}

function ModelBlock({ settings, setSettings }: SettingsProps) {
  const expert = settings.expert;
  const set = (patch: Partial<typeof expert>) =>
    setSettings({ ...settings, expert: { ...expert, ...patch } });
  return (
    <Block
      title="Modèle de rendement (CMA)"
      hint="Mélange hypothèses long terme et historique ; par défaut 70 % CMA."
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <NumField
          label="Shrinkage CMA (%)"
          hint="0 = pure historique · 100 = pure CMA long-terme"
          value={expert.cma_shrinkage * 100}
          step={5}
          min={0}
          max={100}
          onChange={(v) => set({ cma_shrinkage: v / 100 })}
        />
        <div className="space-y-1.5">
          <Label className="text-xs">Période historique</Label>
          <Select
            value={expert.historical_period}
            onValueChange={(v: HistoricalPeriod) => set({ historical_period: v })}
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
          hint="Utilisé par Sharpe. ECB deposit rate ≈ 2.5 %"
          value={expert.risk_free_rate * 100}
          step={0.1}
          min={0}
          max={10}
          onChange={(v) => set({ risk_free_rate: v / 100 })}
        />
        <div className="space-y-1.5">
          <Label className="text-xs">Estimateur Σ (covariance)</Label>
          <Select
            value={expert.cov_estimator}
            onValueChange={(v: CovEstimator) => set({ cov_estimator: v })}
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
        {expert.cov_estimator === "shrunk" && (
          <NumField
            label="Shrinkage Σ (%)"
            hint="Fraction de tirage vers la diagonale (identité × variance moyenne)"
            value={expert.cov_shrinkage * 100}
            step={5}
            min={0}
            max={100}
            onChange={(v) => set({ cov_shrinkage: v / 100 })}
          />
        )}
      </div>
    </Block>
  );
}

function OverridesBlock({ settings, setSettings }: SettingsProps) {
  const [newTicker, setNewTicker] = useState("");
  const [newMu, setNewMu] = useState<number | "">("");
  const overrides = settings.expert.cma_overrides;

  const addOverride = () => {
    if (!newTicker.trim() || newMu === "" || Number(newMu) <= 0) return;
    setSettings({
      ...settings,
      expert: {
        ...settings.expert,
        cma_overrides: { ...overrides, [newTicker.trim().toUpperCase()]: Number(newMu) / 100 },
      },
    });
    setNewTicker("");
    setNewMu("");
  };
  const removeOverride = (ticker: string) => {
    const next = { ...overrides };
    delete next[ticker];
    setSettings({ ...settings, expert: { ...settings.expert, cma_overrides: next } });
  };
  const entries = Object.entries(overrides);

  return (
    <Block
      title="Overrides μ par ticker"
      hint="Force une espérance de rendement annuel pour un ticker précis (prioritaire sur le YAML CMA et l'historique)."
    >
      {entries.length === 0 ? (
        <div className="rounded-md border border-dashed py-4 text-center text-sm text-muted-foreground">
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
      <div className="flex items-end gap-2 pt-3">
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
            onChange={(e) => setNewMu(e.target.value === "" ? "" : Number(e.target.value))}
            className="font-mono tabular"
          />
        </div>
        <Button variant="outline" size="sm" onClick={addOverride}>
          Ajouter
        </Button>
      </div>
    </Block>
  );
}

/* ─── Atoms ─────────────────────────────────────────────────────────────── */

function Block({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-sm font-medium">{title}</h4>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
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
