"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { QK, STALE } from "@/lib/query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function WatchlistPage() {
  const qc = useQueryClient();
  const [ticker, setTicker] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: QK.watchlist, queryFn: api.listWatchlist, staleTime: STALE.watchlist,
  });

  const add = useMutation({
    mutationFn: (t: string) => api.addWatchlist(t),
    onSuccess: () => { setTicker(""); setErr(null); qc.invalidateQueries({ queryKey: QK.watchlist }); },
    onError: (e: unknown) => setErr(e instanceof ApiError ? e.message : "Failed to add"),
  });

  const remove = useMutation({
    mutationFn: (t: string) => api.removeWatchlist(t),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.watchlist }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Watchlist</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <form
            className="flex gap-2"
            onSubmit={(e) => { e.preventDefault(); if (ticker.trim()) add.mutate(ticker.trim().toUpperCase()); }}
          >
            <Input placeholder="Ticker (e.g. RELIANCE)" value={ticker}
                   onChange={(e) => setTicker(e.target.value)} className="max-w-xs" />
            <Button type="submit" disabled={add.isPending}>{add.isPending ? "Adding…" : "Add"}</Button>
          </form>
          {err && <div className="text-sm text-red-500">{err}</div>}
          {isLoading && <div className="text-sm text-[hsl(var(--muted))]">Loading…</div>}
          <ul className="divide-y divide-[hsl(var(--border))]">
            {data.map((e) => (
              <li key={e.ticker} className="flex items-center justify-between py-2">
                <div>
                  <div className="font-medium">{e.ticker}</div>
                  <div className="text-xs text-[hsl(var(--muted))]">
                    added {new Date(e.added_at).toLocaleString()}
                  </div>
                </div>
                <Button variant="ghost" size="sm"
                        onClick={() => remove.mutate(e.ticker)}
                        disabled={remove.isPending}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </li>
            ))}
            {!isLoading && data.length === 0 && (
              <li className="py-6 text-sm text-[hsl(var(--muted))]">No tickers yet. Add one above.</li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
