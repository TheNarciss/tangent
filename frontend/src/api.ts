import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/* ── Types (mirror backend Pydantic models) ─────────────────────────── */

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
}

export interface Portfolio {
  positions: Position[];
  cash: number;
}

export interface AssetMetrics {
  ticker: string;
  price: number;
  weight: number;
  value: number;
  pnl: number;
  pnl_pct: number;
  annual_return: number;
  annual_vol: number;
  sharpe: number;
  drawdown_estimate: number;        // −2σ théorique (loi normale)
  cvar_95: number;                  // perte moyenne 5 % pires jours (annualisé)
  max_drawdown_observed: number;    // pire chute peak-to-trough vécue
}

export interface PortfolioMetrics {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  expected_return: number;
  volatility: number;
  sharpe: number;
  drawdown_estimate: number;
  cvar_95: number;
  max_drawdown_observed: number;
  assets: AssetMetrics[];
  correlation: Record<string, Record<string, number>>;
}

export type Severity = "good" | "warning" | "critical";

export interface Insight {
  severity: Severity;
  title: string;
  detail: string;
}

export interface FrontierCloud {
  vol: number[];
  ret: number[];
  sharpe: number[];
}

export interface StressTestResult {
  id: string;
  label: string;
  description: string;
  start: string;
  end: string;
  pnl_pct: number;
  drawdown_pct: number;
}

export interface DashboardResponse {
  as_of: string;
  metrics: PortfolioMetrics;
  frontier: FrontierCloud;
  insights: Insight[];
  stress_tests: StressTestResult[];
}

export interface TimeseriesResponse {
  dates: string[];
  portfolio: number[];
  benchmark: number[] | null;
  benchmark_ticker: string | null;
  drawdown: number[];
  rolling_sharpe: (number | null)[];
  rolling_window_days: number;
}

export interface ProjectionBands {
  bear: number[];
  base: number[];
  bull: number[];
  p10: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p90: number[];
}

export interface ProjectionResponse {
  months: number[];
  invested: number[];
  bands: ProjectionBands;
  annual_return: number;
  annual_vol: number;
  goal: number | null;
  goal_prob_at_end: number | null;
  goal_prob_by_month: number[] | null;
  // Broker fee impact
  broker_id: string;
  broker: string;
  gross_p50: number[];                       // P50 without fees, for comparison
  cumulative_fees: number[];                 // €, per-month cumulative
}

export interface BengenRequest {
  target_monthly_income: number;
  withdrawal_rate?: number;     // default 0.04
  current_capital?: number;     // default 0
  monthly_dca?: number;         // default 0
  expected_return?: number;     // default 0.08
}

export interface BengenResponse {
  target_monthly_income: number;
  yearly_passive_income: number;
  capital_needed: number;
  years_to_reach: number | null;
  months_to_reach: number | null;
  rationale: string;
}

export interface BrokerInfo {
  id: string;
  name: string;
}

export interface BrokersResponse {
  default: string;
  brokers: BrokerInfo[];
}

export interface EnvelopeEligibility {
  id: string;
  name: string;
  rate_pct: number;
  ceiling_eur: number | null;
  tax_status: string;
  liquidity_days: number;
  eligible: boolean;
  note: string;
}

export interface EligibleEnvelopesResponse {
  envelopes: EnvelopeEligibility[];
}

export interface EligibilityRequest {
  age: number;
  rfr: number;
  fiscal_shares: number;
}

/** Structured error from the backend's AppError handler. */
export class ApiError extends Error {
  constructor(public status: number, public type: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type OptimizerObjective = "max_sharpe" | "min_variance" | "target_volatility" | "from_strategy";

export interface PortfolioPoint {
  weights: number[];
  expected_return: number;
  volatility: number;
  sharpe: number;
}

export interface RebalanceAction {
  ticker: string;
  current_weight: number;
  optimal_weight: number;
  delta_weight: number;
  delta_value: number;
}

export interface RiskContribution {
  tickers: string[];
  fraction: number[];
}

export interface FrontierCurve {
  vol: number[];
  ret: number[];
  sharpe: number[];
}

export interface EnvelopePoint {
  label: string;
  expected_return: number;
  volatility: number;
}

export interface CeilingsUsedDTO {
  livret_a: number;
  livret_a_jeune: number;
  ldds: number;
  lep: number;
  pel: number;
}

export interface OptimizerRequest {
  objective: OptimizerObjective;
  max_volatility?: number;
  target_return?: number;
  include_envelopes?: boolean;
  age?: number;
  rfr?: number;
  fiscal_shares?: number;
  ceilings_used?: CeilingsUsedDTO;
  total_capital?: number;
}

export interface KellyLeverage {
  full_kelly_leverage: number;
  half_kelly_leverage: number;
  interpretation: string;
}

export interface OptimizerResponse {
  objective: OptimizerObjective;
  asset_ids: string[];
  asset_kinds: ("etf" | "envelope")[];
  asset_labels: string[];
  total_capital: number;
  current: PortfolioPoint;
  optimal: PortfolioPoint;
  actions: RebalanceAction[];
  risk_contributions_current: RiskContribution;
  risk_contributions_optimal: RiskContribution;
  frontier_curve: FrontierCurve;
  envelope_points: EnvelopePoint[];
  kelly_leverage: KellyLeverage | null;
}

/* ── HTTP client ────────────────────────────────────────────────────── */

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // Backend errors return {detail, type}; surface both for typed handling upstream.
    let detail = `${res.status} ${res.statusText}`;
    let type = "HttpError";
    try {
      const body = await res.json();
      if (body && typeof body === "object") {
        if (typeof body.detail === "string") detail = body.detail;
        if (typeof body.type === "string") type = body.type;
      }
    } catch {
      /* response wasn't JSON; keep status text */
    }
    throw new ApiError(res.status, type, detail);
  }
  return res.json() as Promise<T>;
}

/* ── Query hooks ────────────────────────────────────────────────────── */

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => http<DashboardResponse>("/dashboard"),
  });
}

export function useTimeseries() {
  return useQuery({
    queryKey: ["timeseries"],
    queryFn: () => http<TimeseriesResponse>("/timeseries"),
  });
}

export function useProjection(monthly: number, years: number, goal?: number, brokerId?: string) {
  return useQuery({
    queryKey: ["projection", monthly, years, goal ?? null, brokerId ?? null],
    queryFn: () => {
      const params = new URLSearchParams({ monthly: String(monthly), years: String(years) });
      if (goal !== undefined && goal > 0) params.set("goal", String(goal));
      if (brokerId) params.set("broker", brokerId);
      return http<ProjectionResponse>(`/projection?${params.toString()}`);
    },
    enabled: monthly >= 0 && years > 0,
  });
}

export function useBrokers() {
  return useQuery({
    queryKey: ["brokers"],
    queryFn: () => http<BrokersResponse>("/brokers"),
    staleTime: Infinity,  // config rarely changes during a session
  });
}

export function useOptimizer(req: OptimizerRequest) {
  return useQuery({
    queryKey: ["optimizer", req],
    queryFn: () => http<OptimizerResponse>("/optimizer", {
      method: "POST",
      body: JSON.stringify(req),
    }),
    enabled: req.objective !== "target_volatility" || (req.max_volatility !== undefined && req.max_volatility >= 0),
  });
}

export function useBengen(req: BengenRequest) {
  return useQuery({
    queryKey: ["bengen", req],
    queryFn: () => http<BengenResponse>("/bengen", {
      method: "POST",
      body: JSON.stringify(req),
    }),
    enabled: req.target_monthly_income > 0,
  });
}

/* ── Scanner types ──────────────────────────────────────────────────── */

export interface ExpertSettingsPayload {
  cma_shrinkage?: number;
  historical_period?: string;
  risk_free_rate?: number;
  cma_overrides?: Record<string, number>;
  cov_estimator?: "sample" | "shrunk";
  cov_shrinkage?: number;
}

export interface ScanRequest {
  modes: string[];
  hypothesis_fraction: number;
  n_results: number;
  expert?: ExpertSettingsPayload;
}

export interface ScanCandidate {
  ticker: string;
  name: string;
  sector: string;                       // catégorie via mode d'origine
  market_cap: number;
  own_mu: number;
  own_sigma: number;
  own_sharpe: number;
  correlation_with_portfolio: number;
  delta_sharpe: number;
  pea_eligible: boolean;
  rationale: string;
}

export interface ScanResponse {
  candidates: ScanCandidate[];
  universe_size: number;
  modes_used: string[];
  elapsed_seconds: number;
}

/** Scanner — mutation (pas un useQuery car déclenché manuellement par bouton).
    Long (~5-30s), pas de retry, pas de cache RQ. */
export function useScan() {
  return useMutation({
    mutationFn: (req: ScanRequest) =>
      http<ScanResponse>("/scan", { method: "POST", body: JSON.stringify(req) }),
  });
}

/* ── Watchlist ──────────────────────────────────────────────────────── */

export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: () => http<string[]>("/watchlist"),
  });
}

export function useWatchlistAdd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker: string) =>
      http<string[]>(`/watchlist/${encodeURIComponent(ticker)}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["optimizer"] });
    },
  });
}

export function useWatchlistRemove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker: string) =>
      http<string[]>(`/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlist"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["optimizer"] });
    },
  });
}

export function usePortfolio() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () => http<Portfolio>("/portfolio"),
  });
}

export function useUpdatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: Portfolio) =>
      http<Portfolio>("/portfolio", { method: "PUT", body: JSON.stringify(p) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["timeseries"] });
      qc.invalidateQueries({ queryKey: ["projection"] });
      qc.invalidateQueries({ queryKey: ["optimizer"] });
    },
  });
}

export function useEligibleEnvelopes(req: EligibilityRequest | null) {
  return useQuery({
    queryKey: ["envelopes", "eligible", req],
    queryFn: () => http<EligibleEnvelopesResponse>("/envelopes/eligible", {
      method: "POST",
      body: JSON.stringify(req),
    }),
    enabled: req !== null,
    staleTime: 5 * 60 * 1000,
  });
}