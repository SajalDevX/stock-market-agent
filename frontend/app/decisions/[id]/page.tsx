"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QK, STALE } from "@/lib/query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const badgeFor: Record<string, "success" | "muted" | "destructive"> = {
  buy: "success", hold: "muted", avoid: "destructive",
};

export default function DecisionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { data, isLoading, isError } = useQuery({
    queryKey: QK.decision(id), queryFn: () => api.getDecision(id), staleTime: STALE.decisions,
  });

  if (isLoading) return <div className="text-sm text-[hsl(var(--muted))]">Loading…</div>;
  if (isError || !data) return <div className="text-sm text-red-500">Not found.</div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>{data.ticker} · {data.timeframe}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={badgeFor[data.verdict]} className="uppercase">{data.verdict}</Badge>
            <div className="text-sm font-semibold">{data.conviction}%</div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="text-xs text-[hsl(var(--muted))]">
            Decided {new Date(data.created_at).toLocaleString()}
          </div>
          <div className="grid grid-cols-4 gap-2 mt-2">
            {[
              ["Ref", data.ref_price],
              ["Entry", data.entry],
              ["Stop", data.stop],
              ["Target", data.target],
            ].map(([label, v]) => (
              <div key={label as string} className="rounded-md border border-[hsl(var(--border))] p-2">
                <div className="text-xs text-[hsl(var(--muted))]">{label as string}</div>
                <div className="font-semibold">{v != null ? `₹${Number(v).toFixed(2)}` : "—"}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Outcomes</CardTitle></CardHeader>
        <CardContent>
          {data.outcomes.length === 0 ? (
            <div className="text-sm text-[hsl(var(--muted))]">
              No horizons computed yet (1d/7d/30d fill in as dates pass — nightly job at 01:00 IST).
            </div>
          ) : (
            <ul className="divide-y divide-[hsl(var(--border))]">
              {data.outcomes.map((o) => {
                const pos = o.return_pct > 0;
                return (
                  <li key={o.horizon} className="flex items-center justify-between py-2">
                    <div className="font-medium">{o.horizon}</div>
                    <div className={pos ? "text-green-500" : "text-red-500"}>
                      {pos ? "+" : ""}{o.return_pct.toFixed(2)}%
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
