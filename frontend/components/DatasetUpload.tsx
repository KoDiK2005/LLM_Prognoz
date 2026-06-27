"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { Dataset } from "@/lib/types";

export default function DatasetUpload({ onUploaded }: { onUploaded: (dataset: Dataset) => void }) {
  const [name, setName] = useState("");
  const [dateColumn, setDateColumn] = useState("date");
  const [valueColumn, setValueColumn] = useState("value");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Выберите CSV-файл");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("date_column", dateColumn);
      formData.append("value_column", valueColumn);
      formData.append("name", name || file.name);

      const dataset = await apiFetch<Dataset>("/datasets/upload", {
        method: "POST",
        body: formData,
      });
      onUploaded(dataset);
      setName("");
      setFile(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить файл");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
      <h2 className="font-medium text-zinc-950 dark:text-zinc-50">Загрузить датасет</h2>

      <div>
        <label className="block text-sm text-zinc-600 dark:text-zinc-400">CSV-файл</label>
        <input
          type="file"
          accept=".csv"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-zinc-600 dark:text-zinc-400">Колонка даты</label>
          <input
            value={dateColumn}
            onChange={(e) => setDateColumn(e.target.value)}
            className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <div>
          <label className="block text-sm text-zinc-600 dark:text-zinc-400">Колонка значения</label>
          <input
            value={valueColumn}
            onChange={(e) => setValueColumn(e.target.value)}
            className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm text-zinc-600 dark:text-zinc-400">Название (опционально)</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={file?.name}
          className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {submitting ? "Загружаем..." : "Загрузить"}
      </button>
    </form>
  );
}
