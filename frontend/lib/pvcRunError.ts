import { ApiError } from "./api/client";

// P6-M4: derive what the Calculate-PVC card should display from a failed run.
// When the engine blocks with a structured `engine_validation_error`, the
// actionable `validation_errors` list must reach the UI — not just the generic
// header. The ApiProblem union's catch-all member defeats direct discriminant
// narrowing, so the array shape is guarded explicitly.
export interface PvcRunErrorView {
  validationErrors: string[] | null;
  message: string;
}

export interface PvcRunRecoveryAction {
  label: string;
  href: string;
}

export function getPvcRunRecoveryActions(
  validationErrors: string[],
  contractId: string,
  billId?: string,
): PvcRunRecoveryAction[] {
  const actions: PvcRunRecoveryAction[] = [];
  const seenHrefs = new Set<string>();

  function add(action: PvcRunRecoveryAction) {
    if (!seenHrefs.has(action.href)) {
      seenHrefs.add(action.href);
      actions.push(action);
    }
  }

  for (const error of validationErrors) {
    if (/measurement_date|measurement date|no pvc quarter/i.test(error) && billId) {
      add({
        label: "Review bill measurement date",
        href: `/contracts/${contractId}/bills/${billId}#bill-header`,
      });
      continue;
    }
    if (/extra.?item|eligibility decision/i.test(error)) {
      add({
        label: "Resolve extra-item decisions",
        href: `/contracts/${contractId}/extra-items`,
      });
      continue;
    }
    if (/index|observation|index month/i.test(error)) {
      add({ label: "Add missing index months", href: "/indices" });
      continue;
    }
    if (/cement|steel|classification|bucket/i.test(error)) {
      add({
        label: "Correct item classifications",
        href: `/contracts/${contractId}?tab=items`,
      });
      continue;
    }
    add({
      label: "Review contract setup",
      href: `/contracts/${contractId}`,
    });
  }

  return actions;
}

export function describePvcRunError(error: unknown): PvcRunErrorView {
  const detail = error instanceof ApiError ? error.detail : undefined;
  if (
    detail?.code === "engine_validation_error" &&
    Array.isArray(detail.validation_errors)
  ) {
    return {
      validationErrors: detail.validation_errors as string[],
      message:
        error instanceof Error
          ? error.message
          : "PVC run blocked by engine validation",
    };
  }
  return {
    validationErrors: null,
    message: error instanceof Error ? error.message : "PVC run failed",
  };
}
