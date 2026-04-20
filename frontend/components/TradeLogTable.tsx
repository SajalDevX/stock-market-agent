import type { TradeRow } from "@/lib/backtest";

const reasonColor: Record<string, string> = {
  signal: "text-blue-500",
  stop_loss: "text-red-500",
  take_profit: "text-green-500",
  max_hold: "text-yellow-500",
  end_of_data: "text-[hsl(var(--muted))]",
};

export function TradeLogTable({ trades }: { trades: TradeRow[] }) {
  if (trades.length === 0) {
    return <div className="text-sm text-[hsl(var(--muted))]">No trades.</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-[hsl(var(--muted))] text-xs uppercase tracking-wide">
          <tr>
            <th className="text-left py-2">Entry</th>
            <th className="text-right">Price</th>
            <th className="text-left">Exit</th>
            <th className="text-right">Price</th>
            <th className="text-right">Return</th>
            <th className="text-left pl-2">Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {trades.map((t, i) => {
            const ret = ((t.exit_price - t.entry_price) / t.entry_price) * 100;
            const pos = ret >= 0;
            return (
              <tr key={i}>
                <td className="py-2">{t.entry_date}</td>
                <td className="text-right">₹{t.entry_price.toFixed(2)}</td>
                <td>{t.exit_date}</td>
                <td className="text-right">₹{t.exit_price.toFixed(2)}</td>
                <td className={`text-right font-semibold ${pos ? "text-green-500" : "text-red-500"}`}>
                  {pos ? "+" : ""}{ret.toFixed(2)}%
                </td>
                <td className={`pl-2 ${reasonColor[t.reason] || ""}`}>{t.reason}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
