import Link from "next/link";
import type { Route } from "next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const items: { href: Route; title: string; desc: string }[] = [
    { href: "/research" as Route, title: "Research", desc: "Run a full orchestrator pass on a stock." },
    { href: "/watchlist" as Route, title: "Watchlist", desc: "Manage tickers to monitor." },
    { href: "/decisions" as Route, title: "Decisions", desc: "Past verdicts + forward returns." },
  ];
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {items.map((it) => (
        <Link key={it.href} href={it.href}>
          <Card className="hover:border-[hsl(var(--accent))] transition-colors cursor-pointer">
            <CardHeader><CardTitle>{it.title}</CardTitle></CardHeader>
            <CardContent className="text-sm text-[hsl(var(--muted))]">{it.desc}</CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
