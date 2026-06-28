const PREVIEW_ROWS = 5;

export interface CsvPreview {
  headers: string[];
  rows: string[][];
}

/** Splits one CSV line into fields, respecting double-quoted fields that
 * contain commas (e.g. `"Smith, John",100`) and "" as an escaped quote.
 * Doesn't handle a quoted field spanning multiple lines — out of scope for
 * a preview of the first few rows of what's normally a date/value series.
 */
function splitCsvLine(line: string): string[] {
  const fields: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (inQuotes) {
      if (char === '"' && line[i + 1] === '"') {
        current += '"';
        i++;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        current += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      fields.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  fields.push(current.trim());
  return fields;
}

export function parsePreview(text: string): CsvPreview {
  const lines = text.split(/\r\n|\r|\n/).filter((line) => line.length > 0);
  const headers = splitCsvLine(lines[0] ?? "");
  const rows = lines.slice(1, 1 + PREVIEW_ROWS).map(splitCsvLine);
  return { headers, rows };
}

export function guessColumn(headers: string[], hints: string[], fallbackIndex: number): string {
  const match = headers.find((h) => hints.some((hint) => h.toLowerCase().includes(hint)));
  return match ?? headers[fallbackIndex] ?? "";
}
