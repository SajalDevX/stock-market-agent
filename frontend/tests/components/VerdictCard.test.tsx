import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictCard } from "@/components/VerdictCard";
import type { OrchestratorReport } from "@/lib/types";

const base: OrchestratorReport = {
  ticker: "RELIANCE", timeframe: "swing", verdict: "buy", conviction: 65,
  conviction_breakdown: { technical: 0.4, fundamental: 0.2, news: 0.3 },
  thesis: "Up-trending with supportive fundamentals.", risks: ["Macro shock"],
  entry: 2820, stop: 2700, target: 3000, ref_price: 2825,
  agent_reports: {}, disagreements: [],
};

describe("VerdictCard", () => {
  it("shows verdict, conviction and thesis", () => {
    render(<VerdictCard report={base} />);
    expect(screen.getByText(/BUY/i)).toBeInTheDocument();
    expect(screen.getByText(/65%/)).toBeInTheDocument();
    expect(screen.getByText(/Up-trending/)).toBeInTheDocument();
  });

  it("shows entry/stop/target when present", () => {
    render(<VerdictCard report={base} />);
    expect(screen.getByText(/2820/)).toBeInTheDocument();
    expect(screen.getByText(/2700/)).toBeInTheDocument();
    expect(screen.getByText(/3000/)).toBeInTheDocument();
  });

  it("renders disagreement banner when present", () => {
    render(<VerdictCard report={{ ...base, disagreements: [{ between: ["technical", "news"], summary: "Conflict." }] }} />);
    expect(screen.getByText(/Conflict/)).toBeInTheDocument();
  });
});
