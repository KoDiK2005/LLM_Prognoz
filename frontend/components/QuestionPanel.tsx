"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { AskQuestionResponse, LLMProvider } from "@/lib/types";

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "ollama", label: "Ollama (self-hosted)" },
];

export default function QuestionPanel({ runId }: { runId: string }) {
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [answer, setAnswer] = useState<AskQuestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setError(null);
    setAsking(true);
    try {
      const resp = await apiFetch<AskQuestionResponse>(`/forecasts/${runId}/ask`, {
        method: "POST",
        body: JSON.stringify({ question, provider }),
      });
      setAnswer(resp);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось получить ответ");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
      <h2 className="font-medium text-zinc-950 dark:text-zinc-50">Спросить про прогноз</h2>

      <form onSubmit={handleAsk} className="flex flex-wrap items-end gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Например: когда ожидается пик?"
          className="min-w-[240px] flex-1 rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value as LLMProvider)}
          className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={asking || !question.trim()}
          className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {asking ? "Спрашиваем..." : "Спросить"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {answer && (
        <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {answer.question} <span className="text-xs">({answer.provider})</span>
          </p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-800 dark:text-zinc-200">{answer.answer}</p>
        </div>
      )}
    </div>
  );
}
