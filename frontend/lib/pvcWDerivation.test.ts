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
  recoveries_affecting_pvc: "15000",
  extra_items: "5000",
  w: "9730000",
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
      amount: "9730000",
      kind: "total",
    });
    // 1 base + 8 subtractions + 1 total, no residual (arithmetic is consistent)
    expect(steps).toHaveLength(10);
    expect(steps.slice(1, -1).every((s) => s.kind === "subtraction")).toBe(true);
  });

  it("keeps technical_withheld and recoveries_affecting_pvc as distinct rows (P6-H1-FUP-C)", () => {
    const steps = describeWDerivation(WD);
    const tw = steps.find((s) => s.label === "Technical withheld");
    const rap = steps.find((s) => s.label === "Recoveries affecting PVC base");
    expect(tw?.amount).toBe("50000");
    expect(rap?.amount).toBe("15000");
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

  it("appends no residual row when the arithmetic is consistent", () => {
    const steps = describeWDerivation(WD);
    expect(steps.some((s) => s.kind === "warning")).toBe(false);
  });

  it("appends a residual warning row when W doesn't match the subtraction sum (P7-FUP-L2)", () => {
    const inconsistent: WDerivation = { ...WD, w: "9000000" };
    const steps = describeWDerivation(inconsistent);
    const warning = steps.find((s) => s.kind === "warning");
    expect(warning).toBeDefined();
    expect(warning?.label).toBe("⚠ Residual (unaccounted)");
    // expected w was 9730000, actual is 9000000 → 730000 unaccounted
    expect(warning?.amount).toBe("730000.00");
  });
});
