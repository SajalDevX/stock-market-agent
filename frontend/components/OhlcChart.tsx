"use client";
import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";

export type Bar = { time: UTCTimestamp; open: number; high: number; low: number; close: number; volume?: number };

export function OhlcChart({
  bars,
  supports = [],
  resistances = [],
  height = 380,
}: {
  bars: Bar[];
  supports?: number[];
  resistances?: number[];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: "transparent" }, textColor: "#888" },
      grid: { vertLines: { color: "#ffffff11" }, horzLines: { color: "#ffffff11" } },
      timeScale: { borderColor: "#ffffff22" },
      rightPriceScale: { borderColor: "#ffffff22" },
    });
    const series = chart.addCandlestickSeries();
    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => chart.applyOptions({ width: containerRef.current?.clientWidth || 800 });
    window.addEventListener("resize", onResize);
    onResize();

    return () => { window.removeEventListener("resize", onResize); chart.remove(); };
  }, [height]);

  useEffect(() => {
    seriesRef.current?.setData(bars);
    // draw price lines for support/resistance
    const series = seriesRef.current;
    if (!series) return;
    const lines = [
      ...supports.map((p) => ({ price: p, color: "#16a34a", lineWidth: 1 as const, title: "S" })),
      ...resistances.map((p) => ({ price: p, color: "#dc2626", lineWidth: 1 as const, title: "R" })),
    ];
    const handles = lines.map((opts) => series.createPriceLine(opts));
    return () => { handles.forEach((h) => series.removePriceLine(h)); };
  }, [bars, supports, resistances]);

  return <div ref={containerRef} className="w-full" />;
}
