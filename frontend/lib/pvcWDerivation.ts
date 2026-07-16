// Phase 7 (D-2d): turn the persisted `w_derivation` JSONB into an ordered
// list of named steps for display. Every subtraction is shown explicitly
// (PRODUCT.md rule 1 — "every subtraction is a named, confirmed step").
//
// P6-H1-FUP-C (2026-07-02): `recoveries_affecting_pvc` is now a dedicated
// bucket, distinct from `technical_withheld` — the two are no longer
// conflated (that was interim approach A).

export interface WDerivation {
  on_account_amount: string | number;
  cement: string | number;
  steel_angles: string | number;
  steel_plates: string | number;
  steel_tmt: string | number;
  steel_other: string | number;
  technical_withheld: string | number;
  recoveries_affecting_pvc: string | number;
  extra_items: string | number;
  w: string | number;
}

export type WStepKind = "base" | "subtraction" | "total" | "warning";

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
  ["technical_withheld", "Technical withheld"],
  ["recoveries_affecting_pvc", "Recoveries affecting PVC base"],
  ["extra_items", "Extra items — excluded (ineligible)"],
];

// P7-FUP-L2: guard against a future W-bucket silently vanishing from the
// display — assert on_account - Σ(subtractions) == w, within rounding.
const RESIDUAL_EPSILON = 0.01;

/**
 * Returns the W derivation as ordered display steps:
 * on-account base → each named subtraction → resulting W (→ an unaccounted
 * residual warning row, if the arithmetic doesn't add up).
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

  const onAccount = Number(wd.on_account_amount);
  const subtractionSum = SUBTRACTIONS.reduce((sum, [key]) => sum + Number(wd[key]), 0);
  const w = Number(wd.w);
  if (Number.isFinite(onAccount) && Number.isFinite(w)) {
    const residual = onAccount - subtractionSum - w;
    if (Math.abs(residual) > RESIDUAL_EPSILON) {
      steps.push({
        label: "⚠ Residual (unaccounted)",
        amount: residual.toFixed(2),
        kind: "warning",
      });
    }
  }

  return steps;
}
