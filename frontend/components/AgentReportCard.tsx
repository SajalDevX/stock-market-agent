"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function scoreBadge(score: number) {
  if (score >= 0.25) return <Badge variant="success">+{score.toFixed(2)}</Badge>;
  if (score <= -0.25) return <Badge variant="destructive">{score.toFixed(2)}</Badge>;
  return <Badge variant="muted">{score.toFixed(2)}</Badge>;
}

export function AgentReportCard({ name, report }: { name: string; report: any }) {
  const [open, setOpen] = useState(false);
  if (!report) return null;
  const score = typeof report.score === "number" ? report.score : 0;

  return (
    <Card>
      <CardHeader
        className="flex flex-row items-center justify-between gap-3 cursor-pointer"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <CardTitle className="capitalize text-base">{name}</CardTitle>
        </div>
        {scoreBadge(score)}
      </CardHeader>
      {open && (
        <CardContent className="space-y-3 text-sm">
          {report.reasoning && <p className="leading-relaxed">{report.reasoning}</p>}

          {name === "technical" && report.key_levels && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-[hsl(var(--muted))]">Support</div>
                <div>{report.key_levels.support.map((v: number) => `₹${v.toFixed(2)}`).join(", ") || "—"}</div>
              </div>
              <div>
                <div className="text-xs text-[hsl(var(--muted))]">Resistance</div>
                <div>{report.key_levels.resistance.map((v: number) => `₹${v.toFixed(2)}`).join(", ") || "—"}</div>
              </div>
            </div>
          )}

          {name === "fundamental" && (
            <div className="flex flex-wrap gap-2 text-xs">
              {report.valuation && <Badge variant="muted">valuation: {report.valuation}</Badge>}
              {report.quality && <Badge variant="muted">quality: {report.quality}</Badge>}
              {report.growth && <Badge variant="muted">growth: {report.growth}</Badge>}
              {(report.red_flags || []).map((f: string, i: number) => (
                <Badge key={i} variant="warning">{f}</Badge>
              ))}
            </div>
          )}

          {name === "news" && (
            <>
              {report.headline_summary && (
                <p className="text-[hsl(var(--muted))]">{report.headline_summary}</p>
              )}
              {(report.citations || []).length > 0 && (
                <ul className="text-xs space-y-1">
                  {report.citations.map((c: any, i: number) => (
                    <li key={i}>
                      <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                        {c.title || c.artifact_id}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {name === "macro" && (
            <div className="text-xs">
              <Badge variant="muted">regime: {report.regime}</Badge>
              {report.tailwinds?.length > 0 && <div className="mt-2">Tailwinds: {report.tailwinds.join("; ")}</div>}
              {report.headwinds?.length > 0 && <div>Headwinds: {report.headwinds.join("; ")}</div>}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
