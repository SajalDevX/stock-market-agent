"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TickerForm } from "@/components/TickerForm";
import { VerdictCard } from "@/components/VerdictCard";
import { AgentReportCard } from "@/components/AgentReportCard";
import type { OrchestratorReport, Timeframe } from "@/lib/types";

export default function ResearchPage() {
  const [result, setResult] = useState<OrchestratorReport | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: (body: { ticker: string; timeframe: Timeframe }) =>
      api.research({ ...body, persist: true }),
    onSuccess: (r) => { setResult(r); setErr(null); },
    onError: (e: unknown) => setErr(e instanceof ApiError ? e.message : "Failed"),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Research</CardTitle></CardHeader>
        <CardContent>
          <TickerForm onSubmit={(v) => run.mutate(v)} disabled={run.isPending} />
          {run.isPending && (
            <div className="text-sm text-[hsl(var(--muted))] mt-3">
              Running Orchestrator — this takes ~10–30s while specialists fetch data and Claude writes the thesis…
            </div>
          )}
          {err && <div className="text-sm text-red-500 mt-3">{err}</div>}
        </CardContent>
      </Card>

      {result && (
        <>
          <VerdictCard report={result} />
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
