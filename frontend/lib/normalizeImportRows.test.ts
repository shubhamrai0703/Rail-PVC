import { describe, expect, it } from "vitest";
import { normalizeImportRows } from "./normalizeImportRows";
import type { Mapping } from "./normalizeImportRows";

const FULL_MAPPING: Mapping = {
  "Item Code": "item_code",
  Description: "description",
  Unit: "unit",
  "Original Qty": "original_qty",
  "Revised Qty": "revised_qty",
  "Base Rate": "base_rate",
  "Agreement Rate": "agreement_rate",
  "Is Cement": "is_cement_item",
  "Steel Subtype": "steel_subtype",
};

describe("normalizeImportRows", () => {
  it("normalizes a well-formed row", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [
        ["IC-1", "Cement bag", "bag", "100", "100", "450", "440", "TRUE", ""],
      ],
    });
    expect(out.errors).toEqual([]);
    expect(out.rows).toHaveLength(1);
    expect(out.rows[0]).toMatchObject({
      item_code: "IC-1",
      is_cement_item: true,
      steel_subtype: null,
      original_qty: 100,
      base_rate: 450,
    });
  });

  it("strips thousand separators on numerics", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [
        ["1.1", "Excavation", "Cum", "3,450.50", "", "1,200", "1,250", "", ""],
      ],
    });
    expect(out.errors).toEqual([]);
    expect(out.rows[0].original_qty).toBe(3450.5);
    expect(out.rows[0].base_rate).toBe(1200);
  });

  it("rejects garbage cement values (H-1 invariant preserved)", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [["IC", "d", "u", "1", "1", "1", "1", "Tru", ""]],
    });
    expect(out.rows).toHaveLength(0);
    expect(out.errors[0]).toMatch(/is_cement_item.*Tru/);
  });

  it("rejects unknown steel subtype", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [["IC", "d", "u", "1", "1", "1", "1", "", "TMT"]],
    });
    expect(out.rows).toHaveLength(0);
    expect(out.errors[0]).toMatch(/steel_subtype/);
  });

  it("applies value_normalizations BEFORE strict validation", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [
        ["IC", "d", "u", "1", "1", "1", "1", "Cement", "TMT Bar"],
      ],
      value_normalizations: {
        is_cement_item: { Cement: "true", "Non-cement": "false" },
        steel_subtype: { "TMT Bar": "tmt", Angles: "angles" },
      },
    });
    expect(out.errors).toEqual([]);
    expect(out.rows[0].is_cement_item).toBe(true);
    expect(out.rows[0].steel_subtype).toBe("tmt");
  });

  it("blocks the import when required targets are unmapped", () => {
    const partial: Mapping = {
      "Item Code": "item_code",
      Description: "description",
      // unit, original_qty, base_rate, agreement_rate all unmapped
    };
    const out = normalizeImportRows({ mapping: partial, rows: [["IC", "d"]] });
    expect(out.rows).toEqual([]);
    expect(out.errors[0]).toMatch(/unmapped/);
  });

  it("skips entirely-blank rows silently", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [
        ["", "", "", "", "", "", "", "", ""],
        ["IC-1", "x", "u", "1", "1", "1", "1", "", ""],
      ],
    });
    expect(out.errors).toEqual([]);
    expect(out.rows).toHaveLength(1);
  });

  it("treats unmapped is_cement_item as false (matches positional default)", () => {
    const noCement: Mapping = {
      "Item Code": "item_code",
      Description: "description",
      Unit: "unit",
      "Original Qty": "original_qty",
      "Base Rate": "base_rate",
      "Agreement Rate": "agreement_rate",
    };
    const out = normalizeImportRows({
      mapping: noCement,
      rows: [["IC", "d", "u", "1", "1", "1"]],
    });
    expect(out.errors).toEqual([]);
    expect(out.rows[0].is_cement_item).toBe(false);
    expect(out.rows[0].steel_subtype).toBe(null);
  });

  it("reports the row number on errors", () => {
    const out = normalizeImportRows({
      mapping: FULL_MAPPING,
      rows: [
        ["IC", "d", "u", "1", "1", "1", "1", "", ""],
        ["IC2", "d", "u", "not-a-number", "1", "1", "1", "", ""],
      ],
    });
    expect(out.errors[0]).toMatch(/Row 2/);
  });
});
