import type { ForecastRun, ForecastRunStatus } from "@/lib/types";

const STATUS_STYLES: Record<ForecastRunStatus, string> = {
  pending: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  running: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

export default function RunHistory({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: ForecastRun[];
  selectedRunId?: string;
  onSelect: (run: ForecastRun) => void;
}) {
  if (runs.length === 0) {
    return <p className="text-sm text-zinc-600 dark:text-zinc-400">Прогнозов для этого датасета пока нет.</p>;
  }

  return (
    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
      {runs.map((run) => (
        <li key={run.id}>
          <button
            onClick={() => onSelect(run)}
            className={`flex w-full items-center justify-between px-1 py-2 text-left text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 ${
              run.id === selectedRunId ? "bg-zinc-50 dark:bg-zinc-900" : ""
            }`}
          >
            <span className="text-zinc-700 dark:text-zinc-300">
              {new Date(run.created_at).toLocaleString()} · горизонт {run.forecast_params.horizon}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[run.status]}`}>{run.status}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
