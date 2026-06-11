import { describe, it, expect } from "vitest";
import { statusVariant, canExportRun } from "./pvcRunStatus";

describe("statusVariant", () => {
  it("maps known statuses to their badge variants", () => {
    expect(statusVariant("Approved")).toBe("approved");
    expect(statusVariant("Superseded")).toBe("superseded");
    expect(statusVariant("ExceptionFlagged")).toBe("blocked");
    expect(statusVariant("Draft")).toBe("draft");
  });

  it("falls back to neutral for unknown statuses", () => {
    expect(statusVariant("Calculated")).toBe("neutral");
    expect(statusVariant("")).toBe("neutral");
  });
});

describe("canExportRun", () => {
  it("allows export only for an approved run (mirrors the 422 gate)", () => {
    expect(canExportRun("Approved")).toBe(true);
    expect(canExportRun("Calculated")).toBe(false);
    expect(canExportRun("Draft")).toBe(false);
    expect(canExportRun("Superseded")).toBe(false);
  });
});
