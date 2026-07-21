import { describe, expect, it } from "vitest";
import {
  CONTRACT_SETUP_GUIDANCE,
  JOURNEY_STAGES,
  TOTAL_PVC_GUIDANCE,
} from "./firstUserHelp";

describe("JOURNEY_STAGES", () => {
  it("defines the full journey in contractor-facing order", () => {
    expect(JOURNEY_STAGES.map((stage) => stage.label)).toEqual([
      "Contract",
      "Items",
      "NS decisions",
      "Bill",
      "Calculate",
      "Review",
    ]);
  });

  it("uses stable unique identifiers for aria-current matching", () => {
    const ids = JOURNEY_STAGES.map((stage) => stage.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("describes calculation controls without promising unsupported behavior", () => {
    expect(TOTAL_PVC_GUIDANCE).toContain("negative-PVC policy");
    expect(TOTAL_PVC_GUIDANCE).toContain("negative carry-forward");
    expect(CONTRACT_SETUP_GUIDANCE).toContain("stored for reference");
    expect(CONTRACT_SETUP_GUIDANCE).toContain("not currently enforced");
  });
});
