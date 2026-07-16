import { describe, expect, it } from "vitest";
import { applyTemplateMapping, headerSignature } from "./importTemplates";

describe("headerSignature", () => {
  it("is stable for the same headers", () => {
    const headers = ["Item Code", "Description", "Unit"];
    expect(headerSignature(headers)).toBe(headerSignature(headers));
  });

  it("ignores order, case, punctuation, and extra whitespace", () => {
    const a = headerSignature(["Item Code", "Description", "Unit"]);
    expect(headerSignature(["Unit", "Description", "Item Code"])).toBe(a);
    expect(headerSignature(["item  code", "DESCRIPTION", "unit."])).toBe(a);
  });

  it("ignores empty headers", () => {
    expect(headerSignature(["Item Code", "", "Unit"])).toBe(
      headerSignature(["Item Code", "Unit"]),
    );
  });

  it("changes when a column is added, removed, or renamed", () => {
    const base = headerSignature(["Item Code", "Unit"]);
    expect(headerSignature(["Item Code", "Unit", "Rate"])).not.toBe(base);
    expect(headerSignature(["Item Code"])).not.toBe(base);
    expect(headerSignature(["Item Number", "Unit"])).not.toBe(base);
  });

  it("stays within the backend's 200-char signature limit", () => {
    const many = Array.from({ length: 100 }, (_, i) => `Column ${i}`);
    const sig = headerSignature(many);
    expect(sig.length).toBeLessThanOrEqual(200);
    expect(sig).toMatch(/^v1-[0-9a-f]{8}$/);
  });
});

describe("applyTemplateMapping", () => {
  const template = {
    mapping: {
      "Item Code": "item_code",
      "Description": "description",
      "Qty": "original_qty",
      "Old Column": "unit",
      "Bogus": "not_a_real_field",
    },
  };

  it("maps current headers through the template", () => {
    const out = applyTemplateMapping(template, ["Item Code", "Description", "Qty"]);
    expect(out).toEqual({
      "Item Code": "item_code",
      "Description": "description",
      "Qty": "original_qty",
    });
  });

  it("matches headers case/punctuation-insensitively", () => {
    const out = applyTemplateMapping(template, ["ITEM-CODE", "description"]);
    expect(out).toEqual({ "ITEM-CODE": "item_code", "description": "description" });
  });

  it("maps headers the template does not know to null", () => {
    const out = applyTemplateMapping(template, ["Item Code", "Brand New"]);
    expect(out["Brand New"]).toBeNull();
  });

  it("drops targets that are no longer valid fields", () => {
    const out = applyTemplateMapping(template, ["Bogus"]);
    expect(out["Bogus"]).toBeNull();
  });

  it("ignores template entries for headers not in the current source", () => {
    const out = applyTemplateMapping(template, ["Item Code"]);
    expect(Object.keys(out)).toEqual(["Item Code"]);
  });

  it("maps null template targets to null (explicit ignore)", () => {
    const out = applyTemplateMapping({ mapping: { Remark: null } }, ["Remark"]);
    expect(out).toEqual({ Remark: null });
  });
});
