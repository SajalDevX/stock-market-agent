"use client";
import Link from "next/link";
import type { Route } from "next";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QK, STALE } from "@/lib/query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const badgeFor: Record<string, "success" | "muted" | "destructive"> = {
  buy: "success", hold: "muted", avoid: "destructive",
};

export default function DecisionsPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: QK.decisions, queryFn: api.listDecisions, staleTime: STALE.decisions,
  });

  return (
    <Card>
      <CardHeader><CardTitle>Decisions</CardTitle></CardHeader>
      <CardContent>
        {isLoading && <div className="text-sm text-[hsl(var(--muted))]">Loading…</div>}
        {!isLoading && data.length === 0 && (
          <div className="text-sm text-[hsl(var(--muted))]">
            No verdicts yet. Run a research to create one.
          </div>
        )}
        <ul className="divide-y divide-[hsl(var(--border))]">
          {data.map((d) => (
            <li key={d.id}>
              <Link href={`/decisions/${d.id}` as Route} className="flex items-center justify-between py-2 hover:bg-[hsl(var(--muted)/0.05)] px-2 rounded">
                <div>
                  <div className="font-medium">{d.ticker} · {d.timeframe}</div>
                  <div className="text-xs text-[hsl(var(--muted))]">
                    {new Date(d.created_at).toLocaleString()} · ref ₹{d.ref_price.toFixed(2)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={badgeFor[d.verdict]} className="uppercase">{d.verdict}</Badge>
                  <div className="text-sm font-semibold w-12 text-right">{d.conviction}%</div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
