export const QK = {
  health: ["health"] as const,
  watchlist: ["watchlist"] as const,
  decisions: ["decisions"] as const,
  decision: (id: number) => ["decisions", id] as const,
  research: (ticker: string, tf: string) => ["research", ticker, tf] as const,
};

export const STALE = {
  health: 15_000,
  watchlist: 60_000,
  decisions: 30_000,
  research: 60 * 60_000,
};
