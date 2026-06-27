"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError, clearToken, getToken } from "@/lib/api";
import type { Dataset, ForecastRun } from "@/lib/types";
import DatasetUpload from "@/components/DatasetUpload";
import ForecastChart from "@/components/ForecastChart";
import InsightsPanel from "@/components/InsightsPanel";

export default function DashboardPage() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(30);
  const [run, setRun] = useState<ForecastRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    apiFetch<Dataset[]>("/datasets")
      .then((list) => {
        setDatasets(list);
        if (list.length > 0) setSelectedDatasetId(list[0].id);
      })
      .catch(() => {});
  }, [router]);

  useEffect(() => {
    if (!run || run.status === "completed" || run.status === "failed") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      const fresh = await apiFetch<ForecastRun>(`/forecasts/${run.id}`);
      setRun(fresh);
    }, 1500);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [run]);

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  function handleUploaded(dataset: Dataset) {
    setDatasets((prev) => [dataset, ...prev]);
    setSelectedDatasetId(dataset.id);
  }

  async function handleRunForecast() {
    if (!selectedDatasetId) return;
    setError(null);
    setStarting(true);
    setRun(null);
    try {
      const created = await apiFetch<ForecastRun>("/forecasts", {
        method: "POST",
        body: JSON.stringify({ dataset_id: selectedDatasetId, horizon }),
      });
      setRun(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось запустить прогноз");
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-950 dark:text-zinc-50">LLM Prognoz</h1>
        <button onClick={handleLogout} className="text-sm text-zinc-600 underline dark:text-zinc-400">
          Выйти
        </button>
      </header>

      <DatasetUpload onUploaded={handleUploaded} />

      <section className="space-y-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="font-medium text-zinc-950 dark:text-zinc-50">Запустить прогноз</h2>

        {datasets.length === 0 ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Сначала загрузите датасет.</p>
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-sm text-zinc-600 dark:text-zinc-400">Датасет</label>
              <select
                value={selectedDatasetId ?? ""}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="mt-1 rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-zinc-600 dark:text-zinc-400">Горизонт (точек)</label>
              <input
                type="number"
                min={1}
                max={365}
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
                className="mt-1 w-24 rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
            </div>

            <button
              onClick={handleRunForecast}
              disabled={starting || !selectedDatasetId}
              className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {starting ? "Запускаем..." : "Прогнозировать"}
            </button>
          </div>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        {run && (
          <div className="space-y-2">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Статус: <span className="font-medium">{run.status}</span>
            </p>
            {run.status === "failed" && (
              <p className="text-sm text-red-600 dark:text-red-400">{run.error_message}</p>
            )}
            {run.result && <ForecastChart history={run.result.history} forecast={run.result.forecast} />}
          </div>
        )}
      </section>

      {run?.status === "completed" && <InsightsPanel runId={run.id} />}
    </div>
  );
}
