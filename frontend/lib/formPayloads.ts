import type { ContractFormValues } from "./contracts-schema";
import { percentToFraction } from "./percentage";
import type { ScheduleFormValues } from "./schedules-schema";

export function buildContractFormPayload(
  values: ContractFormValues,
): ContractFormValues {
  return {
    ...values,
    overall_rebate: percentToFraction(values.overall_rebate),
  };
}

export function buildScheduleFormPayload(
  values: ScheduleFormValues,
): ScheduleFormValues {
  return {
    ...values,
    bid_discount_pct: percentToFraction(values.bid_discount_pct) ?? 0,
  };
}
