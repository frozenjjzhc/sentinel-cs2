// 自动检测 API_BASE：dev 时用 vite proxy（相对路径），生产同源（也是相对路径）
// 仅在 file:// 直接打开时切到绝对地址
export const API_BASE =
  typeof window !== "undefined" && window.location.protocol === "file:"
    ? "http://localhost:8000"
    : "";

export type Health = { ok: boolean; ts: string };
export type Freshness = {
  status: "ok" | "delayed" | "stalled" | "unknown";
  age_seconds: number | null;
  age_minutes: number | null;
  latest_data_time: string | null;
  latest_data_item: string | null;
  state_file_mtime: string | null;
  thresholds: { ok_max_min: number; delayed_max_min: number };
  now: string;
};

export type ItemSummary = {
  id: string;
  name: string;
  short_name?: string;
  url?: string;
  image_url?: string | null;
  phase?: string;
  current_stage?: string;
  price?: number | null;
  today_pct?: number | null;
  week_pct?: number | null;
  today_volume?: number | null;
  stock?: number | null;
  highest_observed?: number | null;
  lowest_observed?: number | null;
  key_levels?: Record<string, number | null>;
  position?: {
    tiers_count: number;
    avg_entry_price?: number | null;
    total_qty_pct?: number;
    total_pieces?: number;
    highest_since_first_entry?: number | null;
    tp_executed?: string[];
    pnl_pct?: number | null;
  } | null;
  legacy?: {
    quantity?: number;
    avg_entry_price?: number;
    pnl_pct?: number | null;
  } | null;
  history_len?: number;
  last_update?: string | null;
  last_signal_pushed?: string | null;
  last_signal_time?: string | null;
  rs_score_1h?: number | null;
  thresholds?: Record<string, unknown>;
  whale_floor_price?: number;
  whale_buy_in_price?: number;
  whale_active_until?: string;
  recent_signals?: Array<Record<string, unknown>>;
  recent_recommendations?: Array<Record<string, unknown>>;
};

export type HistoryEntry = {
  t: string;
  price?: number | null;
  today_pct?: number | null;
  week_pct?: number | null;
  today_volume?: number | null;
  stock?: number | null;
  market_index?: number | null;
  market_pct?: number | null;
};

export type Market = {
  current_index?: number;
  current_change_pct?: number;
  last_update?: string;
  history_24h?: HistoryEntry[];
  error?: string;
};

export type PortfolioBreakdown = {
  id: string;
  name: string;
  current_price: number | null;
  active_pieces: number;
  active_pct: number;
  active_avg: number | null;
  active_cost: number;
  active_value: number;
  legacy_qty: number;
  legacy_avg: number;
  legacy_cost: number;
  legacy_value: number;
  total_cost: number;
  total_value: number;
  pnl: number;
  pnl_pct: number;
  pct_of_budget?: number;
};

export type Portfolio = {
  empty?: boolean;
  total_cost: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  active_cost: number;
  active_value: number;
  legacy_cost: number;
  legacy_value: number;
  concentration_top_id: string | null;
  concentration_pct: number;
  planned_total_cny: number;
  budget_used_pct: number | null;
  budget_remaining: number | null;
  breakdown: PortfolioBreakdown[];
  warnings: string[];
};

export type ShadowStat = {
  count: number;
  avg_return: number;
  win_rate: number;
  max_return: number;
  min_return: number;
};

export type ShadowRecord = {
  id: string;
  strategy: string;
  item_id: string;
  label: string;
  category: string;
  entry_price: number;
  entry_time: string;
  evaluated: boolean;
  exit_price: number | null;
  exit_time: string | null;
  return_7d_pct: number | null;
  context: Record<string, unknown>;
};

export type StrategyMeta = {
  id: string;
  name: string;
  tagline?: string;
  version?: string;
  status?: string;
  description?: string;
  best_for?: string;
  weak_for?: string;
  signals?: string[];
};

export type StrategiesResp = {
  active: string;
  strategies: StrategyMeta[];
  performance: Record<string, ShadowStat>;
};

export type GridLevel = {
  level: number;
  qty_pieces: number;
  entry_price: number | null;
  entry_time: string | null;
  unlock_time: string | null;
};
export type GridState = {
  active: boolean;
  center_price: number;
  step_pct: number;
  levels: number;
  tier_size_pct: number;
  reserve_used: boolean;
  exited: boolean;
  positions: GridLevel[];
  initialized_at: string;
};

export type LLMConfig = {
  provider: string;
  model: string;
  base_url: string;
  enabled_modules: Record<string, boolean>;
  monthly_budget_cny?: number;
  configured: boolean;
  api_key_masked?: string;
};

export type SchedulerStatus = {
  mode: "embedded" | "external";
  status: {
    enabled: boolean;
    started_at: string | null;
    tasks: Record<
      string,
      {
        label?: string;
        schedule?: string;
        running: boolean;
        last_run: string | null;
        next_run: string | null;
        last_ok: string | null;
        last_error: string | null;
        errors: number;
        runs: number;
      }
    >;
  };
};

export type Fundamentals = {
  bias?: string;
  summary?: string;
  whale_signals?: Array<Record<string, unknown>>;
  recent_updates?: Array<Record<string, unknown>>;
  last_check_method?: string;
  last_check_time?: string;
  next_check_due?: string;
};

export type AIReview = {
  date?: string;
  ts?: string;
  text?: string;
  model?: string;
};

export type Proposal = {
  id: string;
  field: string;
  scope: "global" | "item" | "strategy";
  item_id?: string;
  strategy_id?: string;
  current_value: number | string;
  proposed_value: number | string;
  original_value?: number | string;
  confidence: number;
  rationale: string;
  status: "pending" | "applied" | "rejected";
  created_at?: string;
  applied_at?: string;
};

async function get<T>(path: string, timeoutMs = 6000): Promise<T | null> {
  try {
    const r = await fetch(API_BASE + path, { signal: AbortSignal.timeout(timeoutMs) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return (await r.json()) as T;
  } catch (e) {
    console.warn(`API ${path} failed:`, (e as Error).message);
    return null;
  }
}

// LAN 模式下后端要求 X-Sentinel-Token；本机请求不需要，但带上无害
const TOKEN_KEY = "sentinel_token";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function setToken(t: string): void {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

// 首次访问从 URL ?token=... 读取并写入 localStorage 后清掉 query
export function captureTokenFromQuery(): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  const t = url.searchParams.get("token");
  if (t) {
    setToken(t);
    url.searchParams.delete("token");
    window.history.replaceState({}, "", url.toString());
  }
}

async function send<T = unknown>(
  path: string,
  method: "POST" | "DELETE",
  body?: unknown,
  timeoutMs = 8000
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const tok = getToken();
    if (tok) headers["X-Sentinel-Token"] = tok;
    const r = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return { ok: false, error: (data as { detail?: string }).detail || `HTTP ${r.status}` };
    return { ok: true, data: data as T };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

// ============================================================
// 端点封装（与 backend_api.py 一一对应）
// ============================================================
export const api = {
  health: () => get<Health>("/api/health"),
  freshness: () => get<Freshness>("/api/health/freshness"),
  state: () => get<Record<string, unknown>>("/api/state"),
  items: () => get<{ count: number; items: ItemSummary[] }>("/api/items"),
  item: (id: string) => get<ItemSummary>(`/api/items/${encodeURIComponent(id)}`),
  itemHistory: (id: string, hours: number) =>
    get<{ item_id: string; hours: number; count: number; history: HistoryEntry[] }>(
      `/api/items/${encodeURIComponent(id)}/history?hours=${hours}`
    ),
  market: () => get<Market>("/api/market"),
  portfolio: () => get<Portfolio>("/api/portfolio"),
  sectors: () => get<Record<string, unknown>>("/api/sectors"),
  sectorOptions: () => get<{ sectors: string[] }>("/api/sectors/options"),
  shadowStats: () => get<{ stats: Record<string, ShadowStat>; pending: number }>("/api/shadow/stats"),
  shadowRecent: (limit = 10) => get<{ shadows: ShadowRecord[] }>(`/api/shadow/recent?limit=${limit}`),
  reviews: () => get<{ reviews: unknown[] }>("/api/reviews"),
  fundamentals: () => get<Fundamentals>("/api/fundamentals"),
  circuitBreaker: () => get<{ active: boolean; reason?: string }>("/api/circuit_breaker"),
  budget: () => get<{ planned_total_cny: number }>("/api/global/budget"),
  setBudget: (planned_total_cny: number) =>
    send<{ ok: boolean }>("/api/global/budget", "POST", { planned_total_cny }),
  whaleToggle: () => get<{ ignore_whale_signals: boolean }>("/api/global/whale_toggle"),
  setWhaleToggle: (ignore_whale_signals: boolean) =>
    send("/api/global/whale_toggle", "POST", { ignore_whale_signals }),
  dataDir: () =>
    get<{ data_dir: string; project_dir: string; state_file: string; from_env: boolean }>(
      "/api/global/data_dir"
    ),
  openDataDir: () => send("/api/global/open_data_dir", "POST"),

  lanConfig: () =>
    get<{
      enabled: boolean;
      host: string;
      trust_private: boolean;
      token: string;
      ips: string[];
      port: number;
      needs_restart: boolean;
    }>("/api/global/lan"),
  setLanConfig: (body: { enabled?: boolean; trust_private?: boolean }) =>
    send<{
      ok: boolean;
      enabled: boolean;
      trust_private: boolean;
      host: string;
      needs_restart: boolean;
      msg: string;
    }>("/api/global/lan", "POST", body),
  resetLanToken: () =>
    send<{ ok: boolean; token: string }>("/api/global/lan/reset_token", "POST"),

  strategies: () => get<StrategiesResp>("/api/strategies"),
  setActiveStrategy: (strategy_id: string) =>
    send("/api/strategies/active", "POST", { strategy_id }),

  gridState: (id: string) =>
    get<{ active: boolean; grid_state: GridState | null }>(`/api/grid/${encodeURIComponent(id)}`),
  toggleGrid: (item_id: string, active: boolean) =>
    send("/api/grid/toggle", "POST", { item_id, active }),
  restartGrid: (id: string) =>
    send(`/api/grid/${encodeURIComponent(id)}/restart`, "POST"),

  positionBuy: (id: string, price: number, qty_pieces: number) =>
    send(`/api/positions/${encodeURIComponent(id)}/buy`, "POST", { price, qty_pieces }),
  positionSell: (id: string, price: number, qty_pieces: number) =>
    send(`/api/positions/${encodeURIComponent(id)}/sell`, "POST", { price, qty_pieces }),
  positionClear: (id: string) =>
    send(`/api/positions/${encodeURIComponent(id)}/clear`, "POST"),
  setLegacy: (id: string, body: { quantity?: number; avg_entry_price?: number; action: "set" | "remove" }) =>
    send(`/api/positions/${encodeURIComponent(id)}/legacy`, "POST", body),

  addToken: (name: string, token: string) => send("/api/tokens", "POST", { name, token }),
  deleteToken: (name: string) => send(`/api/tokens/${encodeURIComponent(name)}`, "DELETE"),

  addItem: (body: {
    url: string;
    name: string;
    short_name?: string | null;
    sector: string;
    strong_support?: number | null;
    primary_support?: number | null;
    resistance_1?: number | null;
    resistance_2?: number | null;
    resistance_3?: number | null;
  }) => send<{ ok: boolean; id: string; count: number }>("/api/items", "POST", body),
  deleteItem: (id: string) => send(`/api/items/${encodeURIComponent(id)}`, "DELETE"),
  setItemImage: (id: string, image_url: string) =>
    send(`/api/items/${encodeURIComponent(id)}/image`, "POST", { image_url }),

  llmConfig: () => get<LLMConfig>("/api/llm/config"),
  saveLLMConfig: (body: {
    provider: string;
    model: string;
    api_key?: string | null;
    base_url?: string;
    enabled_modules?: Record<string, boolean>;
  }) => send("/api/llm/config", "POST", body),
  testLLM: () =>
    send<{ ok: boolean; latency_ms?: number; response?: string; model?: string; error?: string }>(
      "/api/llm/test",
      "POST",
      null,
      30000
    ),
  classifyNewsNow: () =>
    send<{ items: unknown[]; aggregate_bias: string }>(
      "/api/llm/classify_news",
      "POST",
      null,
      120000
    ),
  llmReviews: (limit = 10) => get<{ reviews: AIReview[] }>(`/api/llm/reviews?limit=${limit}`),
  generateDailyReview: () =>
    send("/api/llm/daily_review", "POST", null, 120000),
  proposals: () => get<{ proposals: Proposal[] }>("/api/llm/proposals"),
  generateProposals: () =>
    send<{ proposals: Proposal[] }>("/api/llm/propose_params", "POST", null, 120000),
  applyProposal: (id: string) =>
    send(`/api/llm/proposals/${encodeURIComponent(id)}/apply`, "POST"),
  rejectProposal: (id: string) =>
    send(`/api/llm/proposals/${encodeURIComponent(id)}/reject`, "POST"),

  schedulerStatus: () => get<SchedulerStatus>("/api/scheduler/status"),
  schedulerStart: () => send("/api/scheduler/start", "POST", null, 10000),
  schedulerStop: () => send("/api/scheduler/stop", "POST", null, 10000),
  schedulerSetMode: (mode: "embedded" | "external") =>
    send("/api/scheduler/mode", "POST", { mode }, 10000),
  schedulerRun: (name: string) =>
    send(`/api/scheduler/run/${encodeURIComponent(name)}`, "POST", null, 180000),
};
