import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "@/lib/api";

describe("api client", () => {
  const originalFetch = global.fetch;
  beforeEach(() => { global.fetch = vi.fn() as unknown as typeof fetch; });
  afterEach(() => { global.fetch = originalFetch; });

  it("GETs /health", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: "ok", db: true, llm_budget_spent_today: 12.5,
        daily_cap_inr: 500, scheduler_running: true,
      }),
    });
    const h = await api.health();
    expect(h.status).toBe("ok");
    expect(h.scheduler_running).toBe(true);
    expect((global.fetch as any).mock.calls[0][0]).toMatch(/\/health$/);
  });

  it("POSTs /research with JSON body", async () => {
    const report = {
      ticker: "RELIANCE", timeframe: "swing", verdict: "buy", conviction: 60,
      conviction_breakdown: {}, thesis: "t", risks: [],
      entry: null, stop: null, target: null, ref_price: 2800,
      agent_reports: {}, disagreements: [],
    };
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => report });
    const r = await api.research({ ticker: "RELIANCE", timeframe: "swing" });
    expect(r.verdict).toBe("buy");
    const call = (global.fetch as any).mock.calls[0];
    expect(call[0]).toMatch(/\/research$/);
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body).ticker).toBe("RELIANCE");
  });

  it("throws ApiError on non-OK responses with detail", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false, status: 404, statusText: "Not Found",
      json: async () => ({ detail: "Unknown ticker: XYZ" }),
    });
    await expect(api.addWatchlist("XYZ")).rejects.toThrow(/Unknown ticker/);
  });

  it("lists decisions", async () => {
    (global.fetch as any).mockResolvedValueOnce({ ok: true, json: async () => [] });
    const rows = await api.listDecisions();
    expect(rows).toEqual([]);
  });
});
