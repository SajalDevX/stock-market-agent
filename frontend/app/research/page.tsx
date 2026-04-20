"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { UTCTimestamp } from "lightweight-charts";
import { api, ApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TickerForm } from "@/components/TickerForm";
import { VerdictCard } from "@/components/VerdictCard";
import { AgentReportCard } from "@/components/AgentReportCard";
import { OhlcChart } from "@/components/OhlcChart";
import type { ResearchResponse, Timeframe } from "@/lib/types";

export default function ResearchPage() {
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: (body: { ticker: string; timeframe: Timeframe }) =>
      api.research({ ...body, persist: true, include_ohlc: true }),
    onSuccess: (r) => { setResult(r); setErr(null); },
    onError: (e: unknown) => setErr(e instanceof ApiError ? e.message : "Failed"),
  });

  const bars = (result?.ohlc ?? []).map((b) => ({ ...b, time: b.time as UTCTimestamp }));
  const supports = result?.agent_reports.technical?.key_levels.support ?? [];
  const resistances = result?.agent_reports.technical?.key_levels.resistance ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Research</CardTitle></CardHeader>
        <CardContent>
          <TickerForm onSubmit={(v) => run.mutate(v)} disabled={run.isPending} />
          {run.isPending && (
            <div className="text-sm text-[hsl(var(--muted))] mt-3">
              Running Orchestrator — this takes ~10–30s…
            </div>
          )}
          {err && <div className="text-sm text-red-500 mt-3">{err}</div>}
        </CardContent>
      </Card>

      {result && (
        <>
          <VerdictCard report={result} />

          {bars.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Price</CardTitle></CardHeader>
              <CardContent>
                <OhlcChart bars={bars} supports={supports} resistances={resistances} />
              </CardContent>
            </Card>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(result.agent_reports).map(([name, r]) => (
              <AgentReportCard key={name} name={name} report={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
