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
}

export interface PortfolioMetrics {
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  expected_return: number;
  volatility: number;
  sharpe: number;
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

export interface DashboardResponse {
  as_of: string;
  metrics: PortfolioMetrics;
  frontier: FrontierCloud;
  insights: Insight[];
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

export interface BrokerInfo {
  id: string;
  name: string;
}

export interface BrokersResponse {
  default: string;
  brokers: BrokerInfo[];
}

/** Structured error from the backend's AppError handler. */
export class ApiError extends Error {
  constructor(public status: number, public type: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export type OptimizerObjective = "max_sharpe" | "min_variance";

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

export interface OptimizerResponse {
  objective: OptimizerObjective;
  tickers: string[];
  current: PortfolioPoint;
  optimal: PortfolioPoint;
  actions: RebalanceAction[];
  risk_contributions_current: RiskContribution;
  risk_contributions_optimal: RiskContribution;
  frontier_curve: FrontierCurve;
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

export function useOptimizer(objective: OptimizerObjective) {
  return useQuery({
    queryKey: ["optimizer", objective],
    queryFn: () => http<OptimizerResponse>(`/optimizer?objective=${objective}`),
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