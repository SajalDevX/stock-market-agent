"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { BacktestRequest, BacktestResponse, Condition, Op } from "@/lib/backtest";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EquityCurve } from "@/components/EquityCurve";
import { TradeLogTable } from "@/components/TradeLogTable";

const DEFAULT: BacktestRequest = {
  ticker: "RELIANCE", exchange: "NSE",
  start: "2024-01-01", end: "2024-12-31",
  initial_capital: 100000,
  entry: [{ indicator: "close", op: ">", indicator_ref: "ema20" }],
  exit:  [{ indicator: "close", op: "<", indicator_ref: "ema20" }],
  stop_loss_pct: 5, take_profit_pct: 15, max_hold_days: 30,
};

function ConditionEditor({ c, onChange, onRemove }: {
  c: Condition; onChange: (c: Condition) => void; onRemove: () => void;
}) {
  const rhsMode = c.indicator_ref ? "ref" : "val";
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <Input value={c.indicator} onChange={(e) => onChange({ ...c, indicator: e.target.value })} className="w-28" />
      <select className="h-10 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2"
              value={c.op}
              onChange={(e) => onChange({ ...c, op: e.target.value as Op })}>
        {["<", "<=", ">", ">=", "==", "!="].map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <select className="h-10 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-2"
              value={rhsMode}
              onChange={(e) => {
                if (e.target.value === "ref") onChange({ indicator: c.indicator, op: c.op, indicator_ref: "ema50" });
                else onChange({ indicator: c.indicator, op: c.op, value: 30 });
              }}>
        <option value="val">value</option>
        <option value="ref">indicator</option>
      </select>
      {c.indicator_ref !== undefined ? (
        <Input value={c.indicator_ref} onChange={(e) => onChange({ indicator: c.indicator, op: c.op, indicator_ref: e.target.value })} className="w-28" />
      ) : (
        <Input type="number" value={c.value ?? 0}
               onChange={(e) => onChange({ indicator: c.indicator, op: c.op, value: Number(e.target.value) })}
               className="w-28" />
      )}
      <Button variant="ghost" size="sm" onClick={onRemove}>remove</Button>
    </div>
  );
}

export default function BacktestPage() {
  const [req, setReq] = useState<BacktestRequest>(DEFAULT);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: (body: BacktestRequest) => api.backtest(body),
    onSuccess: (r) => { setResult(r); setErr(null); },
    onError: (e: unknown) => setErr(e instanceof ApiError ? e.message : "Failed"),
  });

  const setEntry = (entry: Condition[]) => setReq({ ...req, entry });
  const setExit  = (exit:  Condition[]) => setReq({ ...req, exit });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Backtest</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <label className="flex flex-col text-xs gap-1">Ticker
              <Input value={req.ticker} onChange={(e) => setReq({ ...req, ticker: e.target.value.toUpperCase() })} />
            </label>
            <label className="flex flex-col text-xs gap-1">Start
              <Input type="date" value={req.start} onChange={(e) => setReq({ ...req, start: e.target.value })} />
            </label>
            <label className="flex flex-col text-xs gap-1">End
              <Input type="date" value={req.end} onChange={(e) => setReq({ ...req, end: e.target.value })} />
            </label>
            <label className="flex flex-col text-xs gap-1">Capital ₹
              <Input type="number" value={req.initial_capital}
                     onChange={(e) => setReq({ ...req, initial_capital: Number(e.target.value) })} />
            </label>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wide text-[hsl(var(--muted))] mb-2">Entry — all must match</div>
            <div className="space-y-2">
              {req.entry.map((c, i) => (
                <ConditionEditor key={i} c={c}
                  onChange={(nc) => setEntry(req.entry.map((x, j) => j === i ? nc : x))}
                  onRemove={() => setEntry(req.entry.filter((_, j) => j !== i))} />
              ))}
              <Button size="sm" variant="outline"
                onClick={() => setEntry([...req.entry, { indicator: "rsi", op: "<", value: 30 }])}>
                + Add entry condition
              </Button>
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wide text-[hsl(var(--muted))] mb-2">Exit — any triggers</div>
            <div className="space-y-2">
              {req.exit.map((c, i) => (
                <ConditionEditor key={i} c={c}
                  onChange={(nc) => setExit(req.exit.map((x, j) => j === i ? nc : x))}
                  onRemove={() => setExit(req.exit.filter((_, j) => j !== i))} />
              ))}
              <Button size="sm" variant="outline"
                onClick={() => setExit([...req.exit, { indicator: "rsi", op: ">", value: 70 }])}>
                + Add exit condition
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              ["Stop-loss %",  "stop_loss_pct"],
              ["Take-profit %", "take_profit_pct"],
              ["Max hold (d)",  "max_hold_days"],
            ].map(([label, key]) => (
              <label key={key} className="flex flex-col text-xs gap-1">
                {label}
                <Input type="number" value={(req as any)[key] ?? ""}
                       onChange={(e) => setReq({ ...req, [key]: e.target.value ? Number(e.target.value) : undefined } as any)} />
              </label>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={() => run.mutate(req)} disabled={run.isPending}>
              {run.isPending ? "Running…" : "Run backtest"}
            </Button>
            {err && <span className="text-sm text-red-500">{err}</span>}
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          <Card>
            <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                {[
                  ["Trades", result.summary.n_trades],
                  ["Win rate", `${result.summary.win_rate_pct.toFixed(1)}%`],
                  ["Total return", `${result.summary.total_return_pct.toFixed(2)}%`],
                  ["Max drawdown", `${result.summary.max_drawdown_pct.toFixed(2)}%`],
                  ["Avg hold (d)", result.summary.avg_hold_days],
                  ["Final equity", `₹${result.summary.final_equity.toFixed(0)}`],
                  ["Bars seen", result.bars_seen],
                ].map(([label, v]) => (
                  <div key={String(label)} className="rounded-md border border-[hsl(var(--border))] p-2">
                    <div className="text-xs text-[hsl(var(--muted))]">{String(label)}</div>
                    <div className="font-semibold">{v}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Equity curve</CardTitle></CardHeader>
            <CardContent>
              <EquityCurve data={result.equity_curve} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Trades</CardTitle></CardHeader>
            <CardContent>
              <TradeLogTable trades={result.trades} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
