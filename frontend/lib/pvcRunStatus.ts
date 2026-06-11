// Phase 7 (D-4b): shared PVC-run status helpers. The bill-detail page had
// an inline `statusVariant`; the run page needs the same mapping plus an
// export-enablement gate, so both live here as pure functions.

import type { BadgeVariant } from "@/components/ui/Badge";

/** Maps a run/bill status enum to a Badge variant. */
export function statusVariant(status: string): BadgeVariant {
  if (status === "Approved") return "approved";
  if (status === "Superseded") return "superseded";
  if (status === "ExceptionFlagged") return "blocked";
  if (status === "Draft") return "draft";
  return "neutral";
}

/**
 * Export (Excel/PDF) is allowed only for an approved run — mirrors the
 * backend's `run_not_approved` 422 gate on the export routes. The button is
 * disabled (with a tooltip) until the run is approved.
 */
export function canExportRun(status: string): boolean {
  return status === "Approved";
}
