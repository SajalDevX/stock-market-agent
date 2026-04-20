import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "@/lib/api";
import type { BacktestRequest, BacktestResponse } from "@/lib/backtest";

describe("api.backtest", () => {
  const original = global.fetch;
  beforeEach(() => { global.fetch = vi.fn() as unknown as typeof fetch; });
  afterEach(() => { global.fetch = original; });

  it("POSTs /backtest with strategy JSON", async () => {
    const resp: BacktestResponse = {
      summary: { n_trades: 1, n_wins: 1, n_losses: 0, win_rate_pct: 100,
                 total_return_pct: 5.0, max_drawdown_pct: -1.0,
                 avg_hold_days: 5, final_equity: 105000 },
      bars_seen: 80, trades: [], equity_curve: [],
    };
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => resp });

    const req: BacktestRequest = {
      ticker: "X", exchange: "NSE",
      start: "2024-01-01", end: "2024-12-31",
      initial_capital: 100000,
      entry: [{ indicator: "close", op: ">", indicator_ref: "ema20" }],
      exit: [{ indicator: "close", op: "<", indicator_ref: "ema20" }],
    };
    const r = await api.backtest(req);
    expect(r.summary.n_trades).toBe(1);
    const call = (global.fetch as any).mock.calls[0];
    expect(call[0]).toMatch(/\/backtest$/);
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body).ticker).toBe("X");
  });
});
