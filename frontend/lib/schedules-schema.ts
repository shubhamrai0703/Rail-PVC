import { z } from "zod";

import { MAX_PERCENT_INPUT } from "./percentage";

export const scheduleSchema = z.object({
  name: z.string().min(1, "required"),
  schedule_type: z.enum(["DSR", "NS", "ExtraNS"]),
  bid_discount_pct: z
    .number()
    .min(0, "must be ≥ 0%")
    .max(MAX_PERCENT_INPUT, `must be ≤ ${MAX_PERCENT_INPUT}%`),
});

export type ScheduleFormValues = z.infer<typeof scheduleSchema>;
