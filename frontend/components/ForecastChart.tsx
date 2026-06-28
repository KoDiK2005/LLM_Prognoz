"use client";

import { useState } from "react";
import type { ForecastPoint } from "@/lib/types";

const WIDTH = 720;
const HEIGHT = 280;
const PADDING_LEFT = 56;
const PADDING = 16;
const PADDING_BOTTOM = 28;
const Y_TICKS = 4;

function buildPath(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" });
}

function formatValue(v: number): string {
  return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export default function ForecastChart({
  history,
  forecast,
}: {
  history: ForecastPoint[];
  forecast: ForecastPoint[];
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const allPoints = [...history, ...forecast];
  const allValues = allPoints.map((p) => p.value);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;
  const totalPoints = allPoints.length;
  const step = (WIDTH - PADDING_LEFT - PADDING) / Math.max(totalPoints - 1, 1);

  const xFor = (i: number) => PADDING_LEFT + i * step;
  const yFor = (v: number) =>
    HEIGHT - PADDING_BOTTOM - ((v - min) / range) * (HEIGHT - PADDING_BOTTOM - PADDING);

  const historyPoints = history.map((p, i) => ({ x: xFor(i), y: yFor(p.value) }));
  const forecastPoints = forecast.map((p, i) => ({
    x: xFor(history.length - 1 + i),
    y: yFor(p.value),
  }));
  // Connect the forecast line to the last historical point so it reads as continuous.
  const forecastLine =
    history.length > 0 ? [historyPoints[historyPoints.length - 1], ...forecastPoints] : forecastPoints;

  const yTicks = Array.from({ length: Y_TICKS + 1 }, (_, i) => min + (range * i) / Y_TICKS);

  // A handful of evenly-spaced x labels — every point would be unreadable.
  const xLabelCount = Math.min(6, totalPoints);
  const xLabelIndices = Array.from({ length: xLabelCount }, (_, i) =>
    Math.round((i * (totalPoints - 1)) / Math.max(xLabelCount - 1, 1))
  );

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const scaleX = WIDTH / rect.width;
    const x = (e.clientX - rect.left) * scaleX;
    const idx = Math.round((x - PADDING_LEFT) / step);
    setHoverIndex(Math.min(Math.max(idx, 0), totalPoints - 1));
  }

  const hovered = hoverIndex !== null ? allPoints[hoverIndex] : null;
  const hoveredX = hoverIndex !== null ? xFor(hoverIndex) : null;
  const hoveredY = hovered ? yFor(hovered.value) : null;
  const isHoveredForecast = hoverIndex !== null && hoverIndex >= history.length;

  // Keep the tooltip box inside the viewBox even near the edges.
  const tooltipWidth = 96;
  const tooltipX =
    hoveredX !== null ? Math.min(Math.max(hoveredX - tooltipWidth / 2, 0), WIDTH - tooltipWidth) : 0;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full"
      role="img"
      aria-label="Forecast chart"
      onMouseMove={handleMove}
      onMouseLeave={() => setHoverIndex(null)}
    >
      {yTicks.map((value, i) => {
        const y = yFor(value);
        return (
          <g key={i}>
            <line
              x1={PADDING_LEFT}
              y1={y}
              x2={WIDTH - PADDING}
              y2={y}
              className="stroke-zinc-200 dark:stroke-zinc-800"
            />
            <text
              x={PADDING_LEFT - 8}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-zinc-500 text-[10px] dark:fill-zinc-400"
            >
              {formatValue(value)}
            </text>
          </g>
        );
      })}

      {xLabelIndices.map((idx) => (
        <text
          key={idx}
          x={xFor(idx)}
          y={HEIGHT - PADDING_BOTTOM + 16}
          textAnchor="middle"
          className="fill-zinc-500 text-[10px] dark:fill-zinc-400"
        >
          {formatDate(allPoints[idx].date)}
        </text>
      ))}

      <path
        d={buildPath(historyPoints)}
        fill="none"
        className="stroke-zinc-900 dark:stroke-zinc-100"
        strokeWidth={2}
      />
      <path
        d={buildPath(forecastLine)}
        fill="none"
        className="stroke-blue-500"
        strokeWidth={2}
        strokeDasharray="6 4"
      />
      {historyPoints.map((p, i) => (
        <circle key={`h-${i}`} cx={p.x} cy={p.y} r={2} className="fill-zinc-900 dark:fill-zinc-100" />
      ))}
      {forecastPoints.map((p, i) => (
        <circle key={`f-${i}`} cx={p.x} cy={p.y} r={2.5} className="fill-blue-500" />
      ))}

      {hovered && hoveredX !== null && hoveredY !== null && (
        <g>
          <line
            x1={hoveredX}
            y1={PADDING}
            x2={hoveredX}
            y2={HEIGHT - PADDING_BOTTOM}
            className="stroke-zinc-400 dark:stroke-zinc-600"
            strokeDasharray="3 3"
          />
          <circle
            cx={hoveredX}
            cy={hoveredY}
            r={4}
            className={isHoveredForecast ? "fill-blue-500" : "fill-zinc-900 dark:fill-zinc-100"}
          />
          <g transform={`translate(${tooltipX}, ${PADDING})`}>
            <rect
              width={tooltipWidth}
              height={34}
              rx={4}
              className="fill-white stroke-zinc-300 dark:fill-zinc-900 dark:stroke-zinc-700"
            />
            <text
              x={tooltipWidth / 2}
              y={14}
              textAnchor="middle"
              className="fill-zinc-500 text-[10px] dark:fill-zinc-400"
            >
              {formatDate(hovered.date)}
              {isHoveredForecast ? " (прогноз)" : ""}
            </text>
            <text
              x={tooltipWidth / 2}
              y={27}
              textAnchor="middle"
              className="fill-zinc-950 text-xs font-medium dark:fill-zinc-50"
            >
              {formatValue(hovered.value)}
            </text>
          </g>
        </g>
      )}
    </svg>
  );
}
