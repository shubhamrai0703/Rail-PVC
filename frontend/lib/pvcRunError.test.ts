import { describe, it, expect } from "vitest";
import { ApiError } from "./api/client";
import { describePvcRunError } from "./pvcRunError";

describe("describePvcRunError", () => {
  it("surfaces every engine validation error string", () => {
    const err = new ApiError(422, "PVC run blocked by engine validation", null, {
      code: "engine_validation_error",
      message: "PVC run blocked by engine validation",
      validation_errors: [
        "Extra item NS-1 has no eligibility decision",
        "Cement bucket not configured for schedule S-2",
      ],
    });

    const view = describePvcRunError(err);
    expect(view.validationErrors).toEqual([
      "Extra item NS-1 has no eligibility decision",
      "Cement bucket not configured for schedule S-2",
    ]);
    expect(view.message).toBe("PVC run blocked by engine validation");
  });

  it("returns no list for a non-validation ApiError, keeping the message", () => {
    const err = new ApiError(409, "Run already exists", null, {
      code: "idempotency_conflict",
      message: "Run already exists",
      run_id: "run-1",
    });
    const view = describePvcRunError(err);
    expect(view.validationErrors).toBeNull();
    expect(view.message).toBe("Run already exists");
  });

  it("falls back to a generic message for a plain Error", () => {
    const view = describePvcRunError(new Error("Network down"));
    expect(view.validationErrors).toBeNull();
    expect(view.message).toBe("Network down");
  });

  it("handles a non-Error throwable", () => {
    const view = describePvcRunError("boom");
    expect(view.validationErrors).toBeNull();
    expect(view.message).toBe("PVC run failed");
  });
});
