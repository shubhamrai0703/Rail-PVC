export const JOURNEY_STAGES = [
  { id: "contract", label: "Contract" },
  { id: "items", label: "Items" },
  { id: "decisions", label: "NS decisions" },
  { id: "bill", label: "Bill" },
  { id: "calculate", label: "Calculate" },
  { id: "review", label: "Review" },
] as const;

export type JourneyStageId = (typeof JOURNEY_STAGES)[number]["id"];

export const TOTAL_PVC_GUIDANCE =
  "Total PVC starts with the component sum, then applies any prior negative carry-forward and the rule set's negative-PVC policy.";

export const CONTRACT_SETUP_GUIDANCE =
  "Base month and zone feed later calculations. PVC applicability and overall rebate are stored for reference and are not currently enforced or applied by the calculator.";
