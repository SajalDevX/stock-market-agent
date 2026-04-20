export type Op = "<" | "<=" | ">" | ">=" | "==" | "!=";

export type Condition = {
  indicator: string;
  op: Op;
  value?: number;
  indicator_ref?: string;
};

export type BacktestRequest = {
  ticker: string;
  exchange: "NSE" | "BSE";
  start: string;  // YYYY-MM-DD
  end: string;
  initial_capital: number;
  entry: Condition[];
  exit: Condition[];
  stop_loss_pct?: number;
  take_profit_pct?: number;
  max_hold_days?: number;
};

export type TradeRow = {
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  qty: number;
  reason: string;
};

export type BacktestSummary = {
  n_trades: number;
  n_wins: number;
  n_losses: number;
  win_rate_pct: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  avg_hold_days: number;
  final_equity: number;
};

export type BacktestResponse = {
  summary: BacktestSummary;
  bars_seen: number;
  trades: TradeRow[];
  equity_curve: Array<{ date: string; equity: number }>;
};
