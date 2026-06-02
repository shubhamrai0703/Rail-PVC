import { describe, it, expect } from "vitest";
import { humanizeSeries } from "./indices";

describe("humanizeSeries", () => {
  it("uses canonical labels for known series", () => {
    expect(humanizeSeries("steel_tmt")).toBe("Steel — TMT bars");
    expect(humanizeSeries("plant_machinery")).toBe("Plant & machinery");
    expect(humanizeSeries("steel_other_sections")).toBe("Steel — Other sections");
  });

  it("falls back to Title Case for unknown snake_case names", () => {
    expect(humanizeSeries("labour")).toBe("Labour");
    expect(humanizeSeries("fuel")).toBe("Fuel");
    expect(humanizeSeries("some_new_series")).toBe("Some New Series");
  });

  it("handles a single-word name", () => {
    expect(humanizeSeries("cement")).toBe("Cement");
  });
});
