import { describe, expect, it } from "vitest";
import { guessColumn, parsePreview } from "./csv";

describe("parsePreview", () => {
  it("splits headers and up to 5 data rows", () => {
    const csv = "date,value\n2024-01-01,100\n2024-01-02,102\n2024-01-03,105\n";
    const { headers, rows } = parsePreview(csv);
    expect(headers).toEqual(["date", "value"]);
    expect(rows).toEqual([
      ["2024-01-01", "100"],
      ["2024-01-02", "102"],
      ["2024-01-03", "105"],
    ]);
  });

  it("caps preview rows at 5 even for a longer file", () => {
    const lines = ["h1,h2", ...Array.from({ length: 20 }, (_, i) => `a${i},b${i}`)];
    const { rows } = parsePreview(lines.join("\n"));
    expect(rows).toHaveLength(5);
  });

  it("handles CRLF line endings", () => {
    const csv = "a,b\r\n1,2\r\n3,4\r\n";
    const { headers, rows } = parsePreview(csv);
    expect(headers).toEqual(["a", "b"]);
    expect(rows).toEqual([
      ["1", "2"],
      ["3", "4"],
    ]);
  });

  it("trims whitespace around header and cell values", () => {
    const csv = " date , value \n 2024-01-01 , 100 \n";
    const { headers, rows } = parsePreview(csv);
    expect(headers).toEqual(["date", "value"]);
    expect(rows).toEqual([["2024-01-01", "100"]]);
  });

  it("returns empty headers for an empty string", () => {
    expect(parsePreview("")).toEqual({ headers: [""], rows: [] });
  });
});

describe("guessColumn", () => {
  it("matches a header containing one of the hints, case-insensitively", () => {
    expect(guessColumn(["order_date", "revenue"], ["date"], 0)).toBe("order_date");
    expect(guessColumn(["OrderDate", "Revenue"], ["date"], 0)).toBe("OrderDate");
  });

  it("falls back to the column at fallbackIndex when no hint matches", () => {
    expect(guessColumn(["a", "b", "c"], ["nope"], 1)).toBe("b");
  });

  it("returns an empty string when headers are empty", () => {
    expect(guessColumn([], ["date"], 0)).toBe("");
  });
});
