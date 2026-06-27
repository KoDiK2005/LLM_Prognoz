import type { ForecastPoint } from "@/lib/types";

const WIDTH = 720;
const HEIGHT = 280;
const PADDING = 32;

function buildPath(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
}

export default function ForecastChart({
  history,
  forecast,
}: {
  history: ForecastPoint[];
  forecast: ForecastPoint[];
}) {
  const allValues = [...history, ...forecast].map((p) => p.value);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;
  const totalPoints = history.length + forecast.length;

  const xFor = (i: number) =>
    PADDING + (i / Math.max(totalPoints - 1, 1)) * (WIDTH - 2 * PADDING);
  const yFor = (v: number) => HEIGHT - PADDING - ((v - min) / range) * (HEIGHT - 2 * PADDING);

  const historyPoints = history.map((p, i) => ({ x: xFor(i), y: yFor(p.value) }));
  const forecastPoints = forecast.map((p, i) => ({
    x: xFor(history.length - 1 + i),
    y: yFor(p.value),
  }));
  // Connect the forecast line to the last historical point so it reads as continuous.
  const forecastLine = history.length > 0 ? [historyPoints[historyPoints.length - 1], ...forecastPoints] : forecastPoints;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img" aria-label="Forecast chart">
      <line
        x1={PADDING}
        y1={HEIGHT - PADDING}
        x2={WIDTH - PADDING}
        y2={HEIGHT - PADDING}
        className="stroke-zinc-300 dark:stroke-zinc-700"
      />
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
    </svg>
  );
}
