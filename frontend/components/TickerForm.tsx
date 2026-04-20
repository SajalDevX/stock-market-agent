"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Timeframe } from "@/lib/types";

export function TickerForm({
  onSubmit, disabled,
}: {
  onSubmit: (v: { ticker: string; timeframe: Timeframe }) => void;
  disabled?: boolean;
}) {
  const [ticker, setTicker] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("swing");

  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const t = ticker.trim().toUpperCase();
        if (t) onSubmit({ ticker: t, timeframe });
      }}
    >
      <Input
        placeholder="Ticker (e.g. RELIANCE)"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        className="max-w-xs"
      />
      <select
        className="h-10 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-3 text-sm"
        value={timeframe}
        onChange={(e) => setTimeframe(e.target.value as Timeframe)}
      >
        <option value="intraday">Intraday</option>
        <option value="swing">Swing</option>
        <option value="long-term">Long-term</option>
      </select>
      <Button type="submit" disabled={disabled}>Analyze</Button>
    </form>
  );
}
