import { describe, it, expect } from "vitest";
import type { OrchestratorReport, Verdict, Timeframe } from "@/lib/types";

describe("types", () => {
  it("accepts a valid OrchestratorReport", () => {
    const r: OrchestratorReport = {
      ticker: "RELIANCE",
      timeframe: "swing",
      verdict: "buy",
      conviction: 65,
      conviction_breakdown: { technical: 0.4 },
      thesis: "t",
      risks: ["r"],
      entry: 2800, stop: 2700, target: 3000,
      ref_price: 2825,
      agent_reports: {},
      disagreements: [],
    };
    expect(r.verdict).toBe("buy");
  });

  it("enforces verdict literal", () => {
    const v: Verdict = "buy";
    expect(v).toBe("buy");
  });

  it("enforces timeframe literal", () => {
    const t: Timeframe = "swing";
    expect(t).toBe("swing");
  });
});
