export type Verdict = "buy" | "hold" | "avoid";
export type Timeframe = "intraday" | "swing" | "long-term";

export type Evidence = {
  kind: "indicator" | "news" | "filing" | "fundamental" | "macro" | "price";
  label: string;
  value: number | string | null;
  asof: string;
  ref?: string | null;
};

export type NewsCitation = {
  artifact_kind: "news_article" | "filing";
  artifact_id: string;
  title?: string | null;
  url?: string | null;
};

export type TechnicalReport = {
  agent: "technical";
  score: number;
  reasoning: string;
  evidence: Evidence[];
  trend: "up" | "down" | "sideways";
  momentum: "strong" | "weak" | "neutral";
  key_levels: { support: number[]; resistance: number[] };
  signals: Array<Record<string, unknown>>;
  liquidity_warning: boolean;
  circuit_state: string;
};

export type FundamentalReport = {
  agent: "fundamental";
  score: number;
  reasoning: string;
  evidence: Evidence[];
  valuation: "cheap" | "fair" | "expensive" | "unknown";
  quality: "good" | "average" | "poor" | "unknown";
  growth: "high" | "moderate" | "low" | "negative" | "unknown";
  red_flags: string[];
  surveillance: Array<{ list: string; stage?: string | null }>;
};

export type NewsReport = {
  agent: "news";
  score: number;
  reasoning: string;
  evidence: Evidence[];
  headline_summary: string;
  material_events: string[];
  sentiment: number;
  citations: NewsCitation[];
};

export type MacroReport = {
  agent: "macro";
  score: number;
  reasoning: string;
  evidence: Evidence[];
  regime: "bullish" | "neutral" | "bearish";
  tailwinds: string[];
  headwinds: string[];
};

export type AgentReports = Partial<{
  technical: TechnicalReport;
  fundamental: FundamentalReport;
  news: NewsReport;
  macro: MacroReport;
}> &
  Record<string, unknown>;

export type Disagreement = { between: string[]; summary: string };

export type OrchestratorReport = {
  ticker: string;
  timeframe: Timeframe;
  verdict: Verdict;
  conviction: number;
  conviction_breakdown: Record<string, number>;
  thesis: string;
  risks: string[];
  entry: number | null;
  stop: number | null;
  target: number | null;
  ref_price: number;
  agent_reports: AgentReports;
  disagreements: Disagreement[];
};

export type DecisionRow = {
  id: number;
  ticker: string;
  timeframe: Timeframe;
  verdict: Verdict;
  conviction: number;
  entry: number | null;
  stop: number | null;
  target: number | null;
  ref_price: number;
  created_at: string;
};

export type DecisionDetail = DecisionRow & {
  outcomes: Array<{ horizon: "1d" | "7d" | "30d"; return_pct: number }>;
};

export type WatchlistEntry = {
  ticker: string;
  added_at: string;
  rules_json: string | null;
};

export type Health = {
  status: "ok" | "degraded";
  db: boolean;
  llm_budget_spent_today: number;
  daily_cap_inr: number;
  scheduler_running: boolean;
};
