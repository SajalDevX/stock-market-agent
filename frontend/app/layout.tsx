import "./globals.css";
import Link from "next/link";
import type { Route } from "next";
import { Providers } from "./providers";
import { HealthBadge } from "@/components/HealthBadge";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

export const metadata = { title: "Quant Copilot", description: "Personal equity research" };

const nav: { href: Route; label: string }[] = [
  { href: "/research" as Route, label: "Research" },
  { href: "/watchlist" as Route, label: "Watchlist" },
  { href: "/decisions" as Route, label: "Decisions" },
  { href: "/backtest" as Route, label: "Backtest" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <Providers>
          <DisclaimerBanner />
          <header className="flex items-center justify-between border-b border-[hsl(var(--border))] px-6 py-3">
            <nav className="flex items-center gap-4">
              <Link href="/" className="font-semibold tracking-tight">Quant Copilot</Link>
              <div className="flex gap-3 text-sm text-[hsl(var(--muted))]">
                {nav.map((n) => (
                  <Link key={n.href} href={n.href} className="hover:text-[hsl(var(--fg))]">{n.label}</Link>
                ))}
              </div>
            </nav>
            <HealthBadge />
          </header>
          <main className="px-6 py-6 max-w-6xl mx-auto">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
