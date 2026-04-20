"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

type Point = { date: string; equity: number };

export function EquityCurve({ data }: { data: Point[] }) {
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff11" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#888" />
          <YAxis tick={{ fontSize: 11 }} stroke="#888" domain={["dataMin", "dataMax"]} />
          <Tooltip
            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
            formatter={(v: number) => [`₹${v.toFixed(2)}`, "equity"]}
          />
          <Line type="monotone" dataKey="equity" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
