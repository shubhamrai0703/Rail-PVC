import { describe, it, expect } from "vitest";
import { contractCreateSchema } from "./contracts-schema";

// Pin REVIEW.md M-4: clearing a nullable optional field must produce
// `null` in the parsed output (so the backend's `model_fields_set` picks
// it up and writes NULL), not `undefined` (which JSON.stringify silently
// drops and leaves the column untouched).

const base = {
  tender_number: "T-1",
  contractor_name: "ACME",
  railway_zone: "NR",
  base_month: "2025-04-01",
  gst_mode: "exclusive" as const,
  pvc_applicable: true,
};

describe("contractCreateSchema null semantics", () => {
  it("maps cleared optional string fields to null, not undefined", () => {
    const parsed = contractCreateSchema.parse({
      ...base,
      agreement_number: "",
      loa_number: "",
      work_description: "",
    });
    expect(parsed.agreement_number).toBeNull();
    expect(parsed.loa_number).toBeNull();
    expect(parsed.work_description).toBeNull();
  });

  it("maps cleared optional date fields to null", () => {
    const parsed = contractCreateSchema.parse({
      ...base,
      loa_date: "",
      start_date: "",
      completion_date: "",
    });
    expect(parsed.loa_date).toBeNull();
    expect(parsed.start_date).toBeNull();
    expect(parsed.completion_date).toBeNull();
  });

  it("keeps non-empty optional string values intact", () => {
    const parsed = contractCreateSchema.parse({
      ...base,
      agreement_number: "AG-42",
    });
    expect(parsed.agreement_number).toBe("AG-42");
  });

  it("rejects malformed dates with a structured zod error", () => {
    const result = contractCreateSchema.safeParse({
      ...base,
      loa_date: "not-a-date",
    });
    expect(result.success).toBe(false);
  });
});
