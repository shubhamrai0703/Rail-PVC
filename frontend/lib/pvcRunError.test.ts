import { describe, it, expect } from "vitest";
import { ApiError } from "./api/client";
import {
  describePvcRunError,
  getPvcRunRecoveryActions,
} from "./pvcRunError";

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

  it("links blocking reasons back to the decision that resolves them", () => {
    const actions = getPvcRunRecoveryActions(
      [
        "Extra item NS-1 has no eligibility decision",
        "Index observation missing for cement in 2025-02",
        "Cement bucket not configured for schedule S-2",
        "Another missing index observation for 2025-03",
      ],
      "contract-1",
    );

    expect(actions).toEqual([
      {
        label: "Resolve extra-item decisions",
        href: "/contracts/contract-1/extra-items",
      },
      { label: "Add missing index months", href: "/indices" },
      {
        label: "Correct item classifications",
        href: "/contracts/contract-1?tab=items",
      },
    ]);
  });

  it("offers a contract review action for an unrecognized blocking reason", () => {
    expect(
      getPvcRunRecoveryActions(["Contract rule set is incomplete"], "contract-1"),
    ).toEqual([
      {
        label: "Review contract setup",
        href: "/contracts/contract-1",
      },
    ]);
  });

  it("routes a pre-quarter measurement date back to the bill header", () => {
    expect(
      getPvcRunRecoveryActions(
        ["measurement_date 2025-01-01 falls in or before base month"],
        "contract-1",
        "bill-1",
      ),
    ).toEqual([
      {
        label: "Review bill measurement date",
        href: "/contracts/contract-1/bills/bill-1#bill-header",
      },
    ]);
  });
});
