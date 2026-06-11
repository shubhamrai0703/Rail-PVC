// Phase 7 (D-2d): turn the persisted `w_derivation` JSONB into an ordered
// list of named steps for display. Every subtraction is shown explicitly
// (PRODUCT.md rule 1 — "every subtraction is a named, confirmed step").
//
// Honest-label note (decision 2026-06-09, P6-H1-FUP-C deferred): interim
// approach A folds `affects_pvc_base=TRUE` recoveries into the engine's
// `technical_withheld` bucket, so the two can't be disaggregated yet. We
// label that line to say so rather than implying it's pure technical
// withholding. When the dedicated W bucket lands (approach C), split this
// into two rows.

export interface WDerivation {
  on_account_amount: string | number;
  cement: string | number;
  steel_angles: string | number;
  steel_plates: string | number;
  steel_tmt: string | number;
  steel_other: string | number;
  technical_withheld: string | number;
  extra_items: string | number;
  w: string | number;
}

export type WStepKind = "base" | "subtraction" | "total";

export interface WStep {
  label: string;
  amount: string | number;
  kind: WStepKind;
}

const SUBTRACTIONS: ReadonlyArray<readonly [keyof WDerivation, string]> = [
  ["cement", "Cement"],
  ["steel_angles", "Steel — angles (SL4)"],
  ["steel_plates", "Steel — plates (SL4)"],
  ["steel_tmt", "Steel — TMT / rebar (SL1)"],
  ["steel_other", "Steel — other sections (SL4)"],
  // Honest label: interim approach A conflates PVC-affecting recoveries here.
  ["technical_withheld", "Technical withheld (incl. PVC-affecting recoveries)"],
  ["extra_items", "Extra items — excluded (ineligible)"],
];

/**
 * Returns the W derivation as ordered display steps:
 * on-account base → each named subtraction → resulting W.
 * Returns an empty array when the derivation is null/undefined (e.g. a run
 * blocked before W was derived).
 */
export function describeWDerivation(
  wd: WDerivation | null | undefined,
): WStep[] {
  if (!wd) return [];
  const steps: WStep[] = [
    { label: "On-account amount", amount: wd.on_account_amount, kind: "base" },
  ];
  for (const [key, label] of SUBTRACTIONS) {
    steps.push({ label, amount: wd[key], kind: "subtraction" });
  }
  steps.push({ label: "W (adjustable base)", amount: wd.w, kind: "total" });
  return steps;
}
