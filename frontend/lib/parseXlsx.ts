// Thin wrapper around ExcelJS that returns a normalized sheet matrix
// suitable for feeding into fuzzyHeaderMap + normalizeImportRows.
//
// Lazy-imports ExcelJS so non-import pages don't pay the bundle cost.

export interface XlsxSheet {
  name: string;
  rows: string[][]; // header row + data rows, all stringified
}

export interface XlsxWorkbook {
  sheets: XlsxSheet[];
}

const MAX_ROWS_PER_SHEET = 5000;

function cellToString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "object") {
    const v = value as Record<string, unknown>;
    if ("text" in v && typeof v.text === "string") return v.text;
    if ("result" in v && v.result != null) return cellToString(v.result);
    if ("richText" in v && Array.isArray(v.richText)) {
      return (v.richText as Array<{ text: string }>).map((r) => r.text).join("");
    }
    if ("hyperlink" in v && typeof v.text === "string") return v.text;
  }
  return String(value);
}

function trimMatrix(rows: string[][]): string[][] {
  // Drop trailing entirely-empty rows.
  let last = rows.length;
  while (last > 0 && rows[last - 1].every((c) => c === "")) last -= 1;
  const trimmed = rows.slice(0, last);
  if (trimmed.length === 0) return trimmed;

  // Drop trailing entirely-empty columns.
  let maxNonEmpty = 0;
  for (const row of trimmed) {
    for (let i = row.length - 1; i >= maxNonEmpty; i -= 1) {
      if (row[i] !== "") {
        if (i + 1 > maxNonEmpty) maxNonEmpty = i + 1;
        break;
      }
    }
  }
  return trimmed.map((r) => {
    const sliced = r.slice(0, maxNonEmpty);
    while (sliced.length < maxNonEmpty) sliced.push("");
    return sliced;
  });
}

export async function parseXlsx(file: File | ArrayBuffer): Promise<XlsxWorkbook> {
  const ExcelJS = (await import("exceljs")).default;
  const workbook = new ExcelJS.Workbook();
  const buffer = file instanceof ArrayBuffer ? file : await file.arrayBuffer();
  await workbook.xlsx.load(buffer);

  const sheets: XlsxSheet[] = [];
  workbook.eachSheet((worksheet) => {
    const rows: string[][] = [];
    const cap = Math.min(worksheet.rowCount ?? 0, MAX_ROWS_PER_SHEET);
    for (let r = 1; r <= cap; r += 1) {
      const row = worksheet.getRow(r);
      // row.values is 1-indexed (slot 0 is empty). Strip it.
      const raw = Array.isArray(row.values) ? row.values.slice(1) : [];
      rows.push(raw.map((v) => cellToString(v).trim()));
    }
    // Pad to the widest row.
    const width = rows.reduce((m, r) => Math.max(m, r.length), 0);
    for (const r of rows) {
      while (r.length < width) r.push("");
    }
    sheets.push({ name: worksheet.name, rows: trimMatrix(rows) });
  });

  return { sheets };
}

export function splitHeaderAndBody(
  rows: string[][],
  headerRowIndex = 0,
): { headers: string[]; body: string[][] } {
  if (rows.length === 0 || headerRowIndex >= rows.length) {
    return { headers: [], body: [] };
  }
  const headers = rows[headerRowIndex].map((h) => h.trim());
  const body = rows.slice(headerRowIndex + 1);
  return { headers, body };
}
