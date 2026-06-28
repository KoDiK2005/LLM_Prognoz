"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { guessColumn, parsePreview, type CsvPreview } from "@/lib/csv";
import type { Dataset } from "@/lib/types";

export default function DatasetUpload({ onUploaded }: { onUploaded: (dataset: Dataset) => void }) {
  const [name, setName] = useState("");
  const [dateColumn, setDateColumn] = useState("date");
  const [valueColumn, setValueColumn] = useState("value");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleFileChange(selected: File | null) {
    setFile(selected);
    setPreview(null);
    if (!selected) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";
      const parsed = parsePreview(text);
      if (parsed.headers.length === 0) return;
      setPreview(parsed);
      setDateColumn(guessColumn(parsed.headers, ["date", "дата", "time"], 0));
      setValueColumn(guessColumn(parsed.headers, ["value", "значени", "amount", "revenue"], 1));
    };
    reader.readAsText(selected.slice(0, 64 * 1024)); // first 64KB is plenty for a header + a few rows
  }

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
      setPreview(null);
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
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm"
        />
      </div>

      {preview && (
        <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50 dark:bg-zinc-900">
              <tr>
                {preview.headers.map((h) => (
                  <th key={h} className="px-2 py-1 font-medium text-zinc-600 dark:text-zinc-400">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row, i) => (
                <tr key={i} className="border-t border-zinc-100 dark:border-zinc-800">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1 text-zinc-700 dark:text-zinc-300">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-zinc-600 dark:text-zinc-400">Колонка даты</label>
          {preview ? (
            <select
              value={dateColumn}
              onChange={(e) => setDateColumn(e.target.value)}
              className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {preview.headers.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={dateColumn}
              onChange={(e) => setDateColumn(e.target.value)}
              className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          )}
        </div>
        <div>
          <label className="block text-sm text-zinc-600 dark:text-zinc-400">Колонка значения</label>
          {preview ? (
            <select
              value={valueColumn}
              onChange={(e) => setValueColumn(e.target.value)}
              className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {preview.headers.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={valueColumn}
              onChange={(e) => setValueColumn(e.target.value)}
              className="mt-1 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          )}
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
