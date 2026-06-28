const PREVIEW_ROWS = 5;

export interface CsvPreview {
  headers: string[];
  rows: string[][];
}

export function parsePreview(text: string): CsvPreview {
  const lines = text.split(/\r\n|\r|\n/).filter((line) => line.length > 0);
  const headers = (lines[0] ?? "").split(",").map((h) => h.trim());
  const rows = lines.slice(1, 1 + PREVIEW_ROWS).map((line) => line.split(",").map((c) => c.trim()));
  return { headers, rows };
}

export function guessColumn(headers: string[], hints: string[], fallbackIndex: number): string {
  const match = headers.find((h) => hints.some((hint) => h.toLowerCase().includes(hint)));
  return match ?? headers[fallbackIndex] ?? "";
}
