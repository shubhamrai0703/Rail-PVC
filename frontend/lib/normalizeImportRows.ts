// Take a mapping (source-header → target-field) + raw row matrix and
// produce ParsedRow[] in the existing schema, preserving the strict
// token rules from parseTsvImport (REVIEW.md H-1: no silent coercion
// for is_cement_item / steel_subtype).
//
// Optional value_normalizations let the caller (or the AI mapper)
// supply per-target value-translation tables — e.g. "Cement" → "true".
// They run BEFORE the strict validator, so a normalized value still
// has to pass the accept-list.

import {
  VALID_STEEL_SUBTYPES,
  type ParseResult,
  type ParsedRow,
  type SteelSubtype,
} from "./parseTsvImport";
import { TARGET_FIELDS, type TargetField } from "./fuzzyHeaderMap";

export type Mapping = Record<string, TargetField | null>;
export type ValueNormalizations = Partial<Record<TargetField, Record<string, string>>>;

const CEMENT_TRUE = new Set(["true", "yes", "1"]);
const CEMENT_FALSE = new Set(["false", "no", "0", ""]);

const REQUIRED_TARGETS: TargetField[] = [
  "item_code",
  "description",
  "unit",
  "original_qty",
  "base_rate",
  "agreement_rate",
];

function stripThousands(s: string): string {
  // "3,450.00" → "3450.00", but leave "3,4" alone (likely a typo, will fail parseNumeric).
  return /^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(s) ? s.replace(/,/g, "") : s;
}

function parseNumeric(raw: string): { value: number | null; ok: boolean } {
  const t = stripThousands((raw ?? "").trim());
  if (t === "") return { value: null, ok: true };
  const n = Number(t);
  if (Number.isNaN(n)) return { value: null, ok: false };
  return { value: n, ok: true };
}

function applyNormalization(
  target: TargetField,
  raw: string,
  normalizations: ValueNormalizations,
): string {
  const table = normalizations[target];
  if (table === undefined) return raw;
  if (raw in table) return table[raw];
  return raw;
}

export interface NormalizeOptions {
  mapping: Mapping;
  rows: string[][];
  value_normalizations?: ValueNormalizations;
}

export function normalizeImportRows({
  mapping,
  rows,
  value_normalizations = {},
}: NormalizeOptions): ParseResult {
  // Build a source-header → column-index lookup.
  const headers = Object.keys(mapping);
  const headerIndex: Map<string, number> = new Map(headers.map((h, i) => [h, i]));

  // Validate that required targets are mapped before touching any row.
  const mappedTargets = new Set<TargetField>();
  for (const tgt of Object.values(mapping)) {
    if (tgt !== null) mappedTargets.add(tgt);
  }
  const missing = REQUIRED_TARGETS.filter((t) => !mappedTargets.has(t));
  if (missing.length > 0) {
    return {
      rows: [],
      errors: [`Required field(s) unmapped: ${missing.join(", ")}`],
    };
  }

  // Build a target → source-column-index lookup for the actual loop.
  const targetCol: Partial<Record<TargetField, number>> = {};
  for (const [source, target] of Object.entries(mapping)) {
    if (target === null) continue;
    const idx = headerIndex.get(source);
    if (idx !== undefined) targetCol[target] = idx;
  }

  const parsed: ParsedRow[] = [];
  const errors: string[] = [];

  rows.forEach((row, idx) => {
    const rowNum = idx + 1;
    // Skip entirely blank rows silently.
    if (row.every((c) => (c ?? "").trim() === "")) return;

    const cell = (target: TargetField): string => {
      const col = targetCol[target];
      if (col === undefined || col >= row.length) return "";
      return applyNormalization(target, (row[col] ?? "").trim(), value_normalizations);
    };

    const rowErrors: string[] = [];

    const item_code = cell("item_code");
    const description = cell("description");
    const unit = cell("unit");
    if (item_code === "") rowErrors.push("item_code is required");
    if (description === "") rowErrors.push("description is required");
    if (unit === "") rowErrors.push("unit is required");

    const oqty = parseNumeric(cell("original_qty"));
    if (!oqty.ok) rowErrors.push(`original_qty "${cell("original_qty")}" is not a number`);
    const rqty = parseNumeric(cell("revised_qty"));
    if (!rqty.ok) rowErrors.push(`revised_qty "${cell("revised_qty")}" is not a number`);
    const brate = parseNumeric(cell("base_rate"));
    if (!brate.ok) rowErrors.push(`base_rate "${cell("base_rate")}" is not a number`);
    const arate = parseNumeric(cell("agreement_rate"));
    if (!arate.ok) rowErrors.push(`agreement_rate "${cell("agreement_rate")}" is not a number`);

    let cement = false;
    if (targetCol["is_cement_item"] !== undefined) {
      const token = cell("is_cement_item").toLowerCase();
      if (CEMENT_TRUE.has(token)) cement = true;
      else if (CEMENT_FALSE.has(token)) cement = false;
      else
        rowErrors.push(
          `is_cement_item "${cell("is_cement_item")}" must be one of TRUE / FALSE / YES / NO / 1 / 0 (case-insensitive, blank = false)`,
        );
    }

    let subtype: SteelSubtype = null;
    if (targetCol["steel_subtype"] !== undefined) {
      const token = cell("steel_subtype");
      if (token === "") {
        subtype = null;
      } else if ((VALID_STEEL_SUBTYPES as readonly string[]).includes(token)) {
        subtype = token as SteelSubtype;
      } else {
        rowErrors.push(
          `steel_subtype "${token}" must be blank or one of ${VALID_STEEL_SUBTYPES.join(", ")}`,
        );
      }
    }

    if (rowErrors.length > 0) {
      errors.push(`Row ${rowNum}: ${rowErrors.join("; ")}`);
      return;
    }

    parsed.push({
      item_code,
      description,
      unit,
      original_qty: oqty.value,
      revised_qty: rqty.value,
      base_rate: brate.value,
      agreement_rate: arate.value,
      is_cement_item: cement,
      steel_subtype: subtype,
    });
  });

  return { rows: parsed, errors };
}

// Re-export so callers don't import from two places.
export { TARGET_FIELDS, type TargetField };
