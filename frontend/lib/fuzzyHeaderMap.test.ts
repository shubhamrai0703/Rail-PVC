import { describe, expect, it } from "vitest";
import { REQUIRED_FIELDS, fuzzyHeaderMap } from "./fuzzyHeaderMap";

describe("fuzzyHeaderMap", () => {
  it("maps a clean canonical-style header row", () => {
    const result = fuzzyHeaderMap([
      "Item Code",
      "Description",
      "Unit",
      "Original Qty",
      "Revised Qty",
      "Base Rate",
      "Agreement Rate",
      "Cement",
      "Steel Subtype",
    ]);
    expect(result.mapping["Item Code"]).toBe("item_code");
    expect(result.mapping["Description"]).toBe("description");
    expect(result.mapping["Unit"]).toBe("unit");
    expect(result.mapping["Original Qty"]).toBe("original_qty");
    expect(result.mapping["Revised Qty"]).toBe("revised_qty");
    expect(result.mapping["Base Rate"]).toBe("base_rate");
    expect(result.mapping["Agreement Rate"]).toBe("agreement_rate");
    expect(result.mapping["Cement"]).toBe("is_cement_item");
    expect(result.mapping["Steel Subtype"]).toBe("steel_subtype");
    expect(result.missingRequired).toEqual([]);
  });

  it("handles railway-zone vocabulary variants", () => {
    const r = fuzzyHeaderMap([
      "BOQ Item",
      "Description of Work",
      "UOM",
      "Qty as per Agreement",
      "Executed Qty",
      "SOR Rate",
      "Quoted Rate",
    ]);
    expect(r.mapping["BOQ Item"]).toBe("item_code");
    expect(r.mapping["Description of Work"]).toBe("description");
    expect(r.mapping["UOM"]).toBe("unit");
    expect(r.mapping["Qty as per Agreement"]).toBe("original_qty");
    expect(r.mapping["Executed Qty"]).toBe("revised_qty");
    expect(r.mapping["SOR Rate"]).toBe("base_rate");
    expect(r.mapping["Quoted Rate"]).toBe("agreement_rate");
  });

  it("ignores irrelevant columns", () => {
    const r = fuzzyHeaderMap(["S. No.", "Remarks", "Page Ref"]);
    expect(r.mapping["Remarks"]).toBe(null);
    expect(r.mapping["Page Ref"]).toBe(null);
    expect(r.unmapped).toContain("Remarks");
  });

  it("flags missing required fields", () => {
    const r = fuzzyHeaderMap(["Item Code", "Description"]);
    expect(r.missingRequired).toEqual(
      expect.arrayContaining([
        "unit",
        "original_qty",
        "base_rate",
        "agreement_rate",
      ]),
    );
  });

  it("breaks ties by higher confidence (no double-mapping)", () => {
    // Both headers could match item_code; the first ("Item Code") is exact,
    // the second ("Item No") is also exact — last one wins isn't desired.
    // The collision resolver should keep ONE mapped to item_code.
    const r = fuzzyHeaderMap(["Item Code", "Item No"]);
    const targets = Object.values(r.mapping).filter((t) => t === "item_code");
    expect(targets).toHaveLength(1);
  });

  it("respects the confidence threshold", () => {
    const r = fuzzyHeaderMap(["zzzzz", "qqq"]);
    expect(r.mapping["zzzzz"]).toBe(null);
    expect(r.mapping["qqq"]).toBe(null);
  });

  it("treats 'Rate' as agreement_rate (last synonym)", () => {
    // "Rate" alone is ambiguous between base_rate and agreement_rate.
    // We prefer agreement_rate by listing it as a synonym; document that here.
    const r = fuzzyHeaderMap(["Rate"]);
    expect(r.mapping["Rate"]).toBe("agreement_rate");
  });

  it("REQUIRED_FIELDS covers what the modal expects", () => {
    expect(REQUIRED_FIELDS.has("item_code")).toBe(true);
    expect(REQUIRED_FIELDS.has("description")).toBe(true);
    expect(REQUIRED_FIELDS.has("unit")).toBe(true);
    expect(REQUIRED_FIELDS.has("original_qty")).toBe(true);
    expect(REQUIRED_FIELDS.has("base_rate")).toBe(true);
    expect(REQUIRED_FIELDS.has("agreement_rate")).toBe(true);
    expect(REQUIRED_FIELDS.has("is_cement_item")).toBe(false);
    expect(REQUIRED_FIELDS.has("steel_subtype")).toBe(false);
  });
});
