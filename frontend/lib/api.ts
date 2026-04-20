import type {
  DecisionDetail, DecisionRow, Health, ResearchResponse,
  Timeframe, WatchlistEntry,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* non-JSON body */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),

  research: (body: {
    ticker: string; exchange?: string; timeframe: Timeframe;
    tier?: string; news_tier?: string; persist?: boolean; include_ohlc?: boolean;
  }) =>
    request<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify({ exchange: "NSE", persist: true, ...body }),
    }),

  listDecisions: () => request<DecisionRow[]>("/decisions"),
  getDecision:   (id: number) => request<DecisionDetail>(`/decisions/${id}`),

  listWatchlist: () => request<WatchlistEntry[]>("/watchlist"),
  addWatchlist:  (ticker: string, rules_json: string | null = null) =>
    request<WatchlistEntry>(`/watchlist/${encodeURIComponent(ticker)}`, {
      method: "POST",
      body: JSON.stringify({ rules_json }),
    }),
  removeWatchlist: (ticker: string) =>
    request<null>(`/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" })
      .catch((e: unknown) => {
        // 204 No Content returns empty body; request<null>() tries .json() which may fail
        if (e instanceof SyntaxError) return null;
        throw e;
      }),
};
