import { describe, expect, it } from "vitest";

import { contractCreateSchema } from "./contracts-schema";
import {
  buildContractFormPayload,
  buildScheduleFormPayload,
} from "./formPayloads";
import { scheduleSchema } from "./schedules-schema";
import {
  formatFractionAsPercent,
  fractionToPercent,
  optionalPercentInput,
  percentInputOrZero,
} from "./percentage";

const contractBase = {
  tender_number: "T-1",
  contractor_name: "ACME",
  railway_zone: "NR",
  base_month: "2025-04-01",
  gst_mode: "exclusive" as const,
  pvc_applicable: true,
};

describe("percentage form semantics", () => {
  it("builds both API payloads with 15 percent stored as 0.15", () => {
    const contractValues = contractCreateSchema.parse({
      ...contractBase,
      overall_rebate: 15,
    });
    const scheduleValues = scheduleSchema.parse({
      name: "A",
      schedule_type: "DSR",
      bid_discount_pct: 15,
    });

    expect(buildContractFormPayload(contractValues).overall_rebate).toBe(0.15);
    expect(buildScheduleFormPayload(scheduleValues)).toEqual({
      name: "A",
      schedule_type: "DSR",
      bid_discount_pct: 0.15,
    });
  });

  it("converts an existing 0.15 fraction to 15 for editing", () => {
    expect(fractionToPercent(0.15)).toBe(15);
  });

  it("preserves blank semantics for contract and schedule fields", () => {
    const contractValues = contractCreateSchema.parse(contractBase);
    const scheduleValues = scheduleSchema.parse({
      name: "A",
      schedule_type: "DSR",
      bid_discount_pct: percentInputOrZero(""),
    });

    expect(optionalPercentInput("")).toBeUndefined();
    expect(buildContractFormPayload(contractValues).overall_rebate).toBeUndefined();
    expect(buildScheduleFormPayload(scheduleValues).bid_discount_pct).toBe(0);
  });

  it("preserves zero", () => {
    const contractValues = contractCreateSchema.parse({
      ...contractBase,
      overall_rebate: optionalPercentInput("0"),
    });
    const scheduleValues = scheduleSchema.parse({
      name: "A",
      schedule_type: "DSR",
      bid_discount_pct: percentInputOrZero("0"),
    });

    expect(buildContractFormPayload(contractValues).overall_rebate).toBe(0);
    expect(buildScheduleFormPayload(scheduleValues).bid_discount_pct).toBe(0);
  });

  it("leaves invalid numeric input for each schema to reject", () => {
    const invalid = optionalPercentInput("not-a-number");
    expect(Number.isNaN(invalid)).toBe(true);
    expect(
      contractCreateSchema.safeParse({
        ...contractBase,
        overall_rebate: invalid,
      }).success,
    ).toBe(false);
    expect(
      scheduleSchema.safeParse({
        name: "A",
        schedule_type: "DSR",
        bid_discount_pct: invalid,
      }).success,
    ).toBe(false);
  });

  it("accepts the legacy-compatible 999.99 percent boundary in both forms", () => {
    expect(
      contractCreateSchema.safeParse({
        ...contractBase,
        overall_rebate: 999.99,
      }).success,
    ).toBe(true);
    expect(
      scheduleSchema.safeParse({
        name: "A",
        schedule_type: "DSR",
        bid_discount_pct: 999.99,
      }).success,
    ).toBe(true);
    expect(
      buildContractFormPayload(
        contractCreateSchema.parse({
          ...contractBase,
          overall_rebate: 999.99,
        }),
      ).overall_rebate,
    ).toBe(9.9999);
    expect(
      buildScheduleFormPayload(
        scheduleSchema.parse({
          name: "A",
          schedule_type: "DSR",
          bid_discount_pct: 999.99,
        }),
      ).bid_discount_pct,
    ).toBe(9.9999);
  });

  it("rejects values above the historical NUMERIC(5,4) domain", () => {
    expect(
      contractCreateSchema.safeParse({
        ...contractBase,
        overall_rebate: 1000,
      }).success,
    ).toBe(false);
    expect(
      scheduleSchema.safeParse({
        name: "A",
        schedule_type: "DSR",
        bid_discount_pct: 1000,
      }).success,
    ).toBe(false);
  });

  it("formats stored fractions for display", () => {
    expect(formatFractionAsPercent(0.15)).toBe("15.00%");
    expect(formatFractionAsPercent("1.25")).toBe("125.00%");
  });
});
