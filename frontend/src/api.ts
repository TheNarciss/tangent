import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/* ── Types (mirror backend Pydantic models) ─────────────────────────── */

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  isin?: string | null;
  label?: string | null;
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
  drawdown_estimate: number;        // theoretical −2σ (normal law)
  cvar_95: number;                  // mean loss on the worst 5% days (annualized)
  max_drawdown_observed: number;    // worst peak-to-trough drop observed
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

/* ── Auth types ─────────────────────────────────────────────────────── */

export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  display_name: string | null;
}

export interface UserCreate {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/* ── HTTP client ────────────────────────────────────────────────────── */

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",   // CRITICAL: send/receive auth cookies cross-origin
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
  // Some endpoints return 204 No Content (login, logout) — no body to parse
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* ── Auth hooks ─────────────────────────────────────────────────────── */

/**
 * Current logged-in user. Returns null when unauthenticated (401), throws otherwise.
 * Used by App.tsx as the route guard signal.
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ["user", "me"],
    queryFn: async (): Promise<UserRead | null> => {
      try {
        return await http<UserRead>("/users/me");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000,   // 5 min — refetch on focus by default
    retry: false,                // never retry auth check
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (req: LoginRequest) => {
      // FastAPI-Users expects OAuth2 password flow: form-encoded, field name "username".
      const body = new URLSearchParams({
        username: req.email,
        password: req.password,
      });
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (!res.ok) {
        let detail = "Invalid credentials";
        try {
          const j = await res.json();
          if (typeof j?.detail === "string") detail = j.detail;
        } catch { /* keep default */ }
        throw new ApiError(res.status, "LoginFailed", detail);
      }
      // 204 No Content — cookie set by backend
      return true;
    },
    onSuccess: async () => {
      // Clean up past data but keep the user query intact
      qc.removeQueries({ predicate: (query) => query.queryKey[0] !== "user" });
      // Trigger a fresh user fetch (will re-render App and the dashboard)
      await qc.invalidateQueries({ queryKey: ["user", "me"] });
    },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: UserCreate) =>
      http<UserRead>("/auth/register", {
        method: "POST",
        body: JSON.stringify(req),
      }),
    onSuccess: () => {
      // Register doesn't auto-login — caller must call useLogin() next.
      qc.invalidateQueries({ queryKey: ["user", "me"] });
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      http<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      // Immediate UI update: signal the user is no longer authenticated.
      // App.tsx watches ["user", "me"] === null and switches to AuthScreen.
      qc.setQueryData(["user", "me"], null);
      // Then wipe other cached data so next user doesn't see previous content.
      qc.removeQueries({ predicate: (q) => !(q.queryKey[0] === "user" && q.queryKey[1] === "me") });
    },
  });
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
  sector: string;                       // category via origin mode
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

/** Scanner — mutation (not a useQuery since triggered manually by button).
    Long (~5-30s), no retry, no RQ cache. */
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

/* ── Powens sync ─────────────────────────────────────────────────────── */

export interface SyncStatus {
  configured: boolean;
  user_connected: boolean;
  last_sync: string | null;
  last_webhook: string | null;
  last_error: string | null;
  age_hours: number | null;
  positions_count: number;
  cash_balance: number;
  is_stale: boolean;
}

export interface SyncResult {
  success: boolean;
  positions_count: number;
  cash_balance: number;
  total_valuation: number;
  accounts_synced: string[];
  skipped_accounts: string[];
  error: string | null;
  synced_at: string;
}

/** Reads the last Powens sync state. Polled every 30s to refresh the badge.
    Currently superuser-only (deprecated mono-user code, Phase 5 will rewrite). */
export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync", "status"],
    queryFn: () => http<SyncStatus>("/sync/status"),
    refetchInterval: 30 * 1000,
    retry: false,    // 403 for non-superusers — don't spam retries
  });
}

/** Triggers a manual Powens sync. Invalidates portfolio-dependent queries. */
export function useSyncPowens() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => http<SyncResult>("/sync/powens", { method: "POST" }),
    onSuccess: (result) => {
      if (result.success) {
        qc.invalidateQueries({ queryKey: ["portfolio"] });
        qc.invalidateQueries({ queryKey: ["dashboard"] });
        qc.invalidateQueries({ queryKey: ["timeseries"] });
        qc.invalidateQueries({ queryKey: ["projection"] });
        qc.invalidateQueries({ queryKey: ["optimizer"] });
        qc.invalidateQueries({ queryKey: ["sync", "status"] });
      }
    },
  });
}

export async function getPowensWebviewUrl(): Promise<string> {
  const result = await http<{ webview_url: string }>("/auth/powens/initiate");
  return result.webview_url;
}

/* ── Password reset hooks ─────────────────────────────────────────────── */
export function useRequestReset() {
  return useMutation({
    mutationFn: (email: string) =>
      http<void>("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
  });
}

export function useVerifyResetCode() {
  return useMutation({
    mutationFn: ({ email, code }: { email: string; code: string }) =>
      http<{ reset_token: string }>("/auth/password-reset/verify", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      }),
  });
}

export function useConfirmReset() {
  return useMutation({
    mutationFn: ({ reset_token, new_password }: { reset_token: string; new_password: string }) =>
      http<void>("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ reset_token, new_password }),
      }),
  });
}

