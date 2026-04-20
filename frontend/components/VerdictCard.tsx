import type { OrchestratorReport } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const verdictColor: Record<string, "success" | "muted" | "destructive"> = {
  buy: "success", hold: "muted", avoid: "destructive",
};

export function VerdictCard({ report }: { report: OrchestratorReport }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle>
            {report.ticker} · {report.timeframe}
          </CardTitle>
          <div className="text-xs text-[hsl(var(--muted))] mt-1">
            ref ₹{report.ref_price.toFixed(2)}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={verdictColor[report.verdict]} className="text-base uppercase">
            {report.verdict}
          </Badge>
          <div className="text-sm font-semibold">{report.conviction}%</div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {report.disagreements.length > 0 && (
          <div className="rounded-md bg-yellow-500/15 border border-yellow-500/40 p-2 text-sm">
            <span className="font-semibold">Disagreement:</span>{" "}
            {report.disagreements.map((d) => d.summary).join(" ")}
          </div>
        )}
        <p className="text-sm leading-relaxed">{report.thesis}</p>
        {report.risks.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[hsl(var(--muted))] mb-1">Risks</div>
            <ul className="list-disc pl-5 text-sm space-y-1">
              {report.risks.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
        {(report.entry != null || report.stop != null || report.target != null) && (
          <div className="grid grid-cols-3 gap-2 text-sm">
            {[
              ["Entry", report.entry],
              ["Stop", report.stop],
              ["Target", report.target],
            ].map(([label, v]) => (
              <div key={label as string} className="rounded-md border border-[hsl(var(--border))] p-2">
                <div className="text-xs text-[hsl(var(--muted))]">{label as string}</div>
                <div className="font-semibold">{v != null ? `₹${Number(v).toFixed(2)}` : "—"}</div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
