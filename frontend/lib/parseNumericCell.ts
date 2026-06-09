// P6-M3: numeric grid-cell parsing for the Items grid.
//
// The previous inline parser coerced *any* unparseable input to `null`, which
// silently erased rates/quantities on a bad paste (e.g. "1,23,456" or "abc")
// and let that null flow into a POST/PUT payload. This parser instead:
//   * treats empty/blank as an explicit clear (null) — clearing is allowed
//   * strips thousand separators and spaces so "1,23,456" → 123456
//   * REJECTS any remaining non-finite input (`ok: false`) so the caller can
//     keep the prior value and surface an error instead of writing null.
export interface NumericCellParse {
  ok: boolean;
  value: number | null;
}

export function parseNumericCell(raw: unknown): NumericCellParse {
  if (raw == null) return { ok: true, value: null };
  const s = String(raw).trim();
  if (s === "") return { ok: true, value: null };

  // Strip thousand separators (Indian or Western grouping) and stray spaces.
  const stripped = s.replace(/[,\s]/g, "");
  // Reject hex/octal/binary/exponent shorthands and other non-decimal noise:
  // only a plain decimal number is acceptable.
  if (!/^[+-]?(\d+(\.\d*)?|\.\d+)$/.test(stripped)) {
    return { ok: false, value: null };
  }
  const n = Number(stripped);
  if (!Number.isFinite(n)) return { ok: false, value: null };
  return { ok: true, value: n };
}
