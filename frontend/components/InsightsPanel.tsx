"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { LLMInsight, LLMProvider } from "@/lib/types";

const ALL_PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "ollama", label: "Ollama (self-hosted)" },
];

export default function InsightsPanel({ runId }: { runId: string }) {
  const [insights, setInsights] = useState<LLMInsight[]>([]);
  const [selected, setSelected] = useState<LLMProvider[]>(["openai"]);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    apiFetch<LLMInsight[]>(`/forecasts/${runId}/insights`).then(setInsights).catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [runId]);

  useEffect(() => {
    const hasPending = insights.some((i) => i.status === "pending");
    if (!hasPending) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      const fresh = await apiFetch<LLMInsight[]>(`/forecasts/${runId}/insights`);
      setInsights(fresh);
    }, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [insights, runId]);

  function toggleProvider(provider: LLMProvider) {
    setSelected((prev) =>
      prev.includes(provider) ? prev.filter((p) => p !== provider) : [...prev, provider]
    );
  }

  async function handleGenerate() {
    if (selected.length === 0) return;
    setError(null);
    setGenerating(true);
    try {
      const created = await apiFetch<LLMInsight[]>(`/forecasts/${runId}/insights`, {
        method: "POST",
        body: JSON.stringify({ providers: selected }),
      });
      setInsights((prev) => [...created, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось запустить генерацию");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
      <h2 className="font-medium text-zinc-950 dark:text-zinc-50">LLM-интерпретации</h2>

      <div className="flex flex-wrap gap-3">
        {ALL_PROVIDERS.map((p) => (
          <label key={p.value} className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={selected.includes(p.value)}
              onChange={() => toggleProvider(p.value)}
            />
            {p.label}
          </label>
        ))}
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <button
        onClick={handleGenerate}
        disabled={generating || selected.length === 0}
        className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {generating ? "Запускаем..." : "Сгенерировать"}
      </button>

      <ul className="space-y-3">
        {insights.map((insight) => (
          <li key={insight.id} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-zinc-950 dark:text-zinc-50">
                {insight.provider} {insight.model_name && `(${insight.model_name})`}
              </span>
              <StatusBadge status={insight.status} />
            </div>
            {insight.status !== "pending" && (
              <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
                {insight.response_text}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatusBadge({ status }: { status: LLMInsight["status"] }) {
  const styles: Record<LLMInsight["status"], string> = {
    pending: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs ${styles[status]}`}>{status}</span>;
}
