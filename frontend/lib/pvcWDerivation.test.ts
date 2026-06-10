import { describe, it, expect } from "vitest";
import { describeWDerivation, type WDerivation } from "./pvcWDerivation";

const WD: WDerivation = {
  on_account_amount: "10000000",
  cement: "100000",
  steel_angles: "20000",
  steel_plates: "30000",
  steel_tmt: "40000",
  steel_other: "10000",
  technical_withheld: "50000",
  extra_items: "5000",
  w: "9745000",
};

describe("describeWDerivation", () => {
  it("orders steps: on-account base → named subtractions → W total", () => {
    const steps = describeWDerivation(WD);

    expect(steps[0]).toEqual({
      label: "On-account amount",
      amount: "10000000",
      kind: "base",
    });
    expect(steps.at(-1)).toEqual({
      label: "W (adjustable base)",
      amount: "9745000",
      kind: "total",
    });
    // 1 base + 7 subtractions + 1 total
    expect(steps).toHaveLength(9);
    expect(steps.slice(1, -1).every((s) => s.kind === "subtraction")).toBe(true);
  });

  it("labels the technical-withheld bucket honestly (interim approach A)", () => {
    const steps = describeWDerivation(WD);
    const tw = steps.find((s) => s.amount === "50000");
    expect(tw?.label).toBe(
      "Technical withheld (incl. PVC-affecting recoveries)",
    );
  });

  it("surfaces every named subtraction with its amount", () => {
    const steps = describeWDerivation(WD);
    const byLabel = Object.fromEntries(steps.map((s) => [s.label, s.amount]));
    expect(byLabel["Cement"]).toBe("100000");
    expect(byLabel["Steel — angles (SL4)"]).toBe("20000");
    expect(byLabel["Steel — TMT / rebar (SL1)"]).toBe("40000");
    expect(byLabel["Extra items — excluded (ineligible)"]).toBe("5000");
  });

  it("returns an empty list when W was not derived (blocked run)", () => {
    expect(describeWDerivation(null)).toEqual([]);
    expect(describeWDerivation(undefined)).toEqual([]);
  });
});
