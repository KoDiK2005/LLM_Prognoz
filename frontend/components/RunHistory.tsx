"use client";

import { useState } from "react";
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
  onDelete,
}: {
  runs: ForecastRun[];
  selectedRunId?: string;
  onSelect: (run: ForecastRun) => void;
  onDelete: (run: ForecastRun) => void;
}) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  if (runs.length === 0) {
    return <p className="text-sm text-zinc-600 dark:text-zinc-400">Прогнозов для этого датасета пока нет.</p>;
  }

  return (
    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
      {runs.map((run) => (
        <li
          key={run.id}
          className={`flex items-center justify-between gap-2 px-1 py-2 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 ${
            run.id === selectedRunId ? "bg-zinc-50 dark:bg-zinc-900" : ""
          }`}
        >
          <button onClick={() => onSelect(run)} className="flex-1 text-left text-zinc-700 dark:text-zinc-300">
            {new Date(run.created_at).toLocaleString()} · горизонт {run.forecast_params.horizon}
          </button>
          <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[run.status]}`}>{run.status}</span>

          {confirmingId === run.id ? (
            <span className="flex items-center gap-1.5 text-xs">
              <span className="text-zinc-600 dark:text-zinc-400">Удалить?</span>
              <button
                onClick={() => {
                  setConfirmingId(null);
                  onDelete(run);
                }}
                className="font-medium text-red-600 hover:underline dark:text-red-400"
              >
                Да
              </button>
              <button
                onClick={() => setConfirmingId(null)}
                className="text-zinc-500 hover:underline dark:text-zinc-400"
              >
                Нет
              </button>
            </span>
          ) : (
            <button
              onClick={() => setConfirmingId(run.id)}
              aria-label="Удалить прогноз"
              className="text-zinc-400 hover:text-red-600 dark:hover:text-red-400"
            >
              ×
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
