import { z } from "zod";
import { ZONE_CODES } from "./zones";

// Mirror of backend `ContractCreate` / `ContractUpdate` (backend/api/contracts.py).
// Server-side rules that cannot be validated client-side (e.g. agreement_number
// uniqueness) are not duplicated here — see WORKPLAN.md Q6.
//
// overall_rebate is stored as a fraction (0.15 = 15%); DB column is
// NUMERIC(5,4), max 9.9999. UI labels must say so explicitly.
//
// REVIEW.md M-4: optional nullable-in-DB fields parse `""`/`undefined` → `null`
// (not left as `undefined`). JSON.stringify keeps `null` and drops `undefined`;
// the backend's `model_fields_set` only picks up keys present in the body. So
// `null` is the only encoding that lets the Edit form actually clear a column.

const nullableString = z
  .string()
  .optional()
  .transform((s) => (s === undefined || s === "" ? null : s));

const nullableDate = z
  .string()
  .optional()
  .refine(
    (s) => s === undefined || s === "" || /^\d{4}-\d{2}-\d{2}$/.test(s),
    "expected YYYY-MM-DD",
  )
  .transform((s) => (s === undefined || s === "" ? null : s));

const nullablePositive = z
  .number({ message: "expected a number" })
  .positive("must be > 0")
  .optional()
  .transform((n) => (n === undefined ? null : n));

export const contractCreateSchema = z
  .object({
    tender_number: z.string().min(1, "required"),
    agreement_number: nullableString,
    loa_number: nullableString,
    loa_date: nullableDate,
    contractor_name: z.string().min(1, "required"),
    work_description: nullableString,
    railway_zone: z.enum(ZONE_CODES as unknown as [string, ...string[]]),
    base_month: z
      .string()
      .regex(/^\d{4}-\d{2}-01$/, "must be the first day of the month (YYYY-MM-01)"),
    start_date: nullableDate,
    completion_date: nullableDate,
    contract_value: nullablePositive,
    bid_amount: nullablePositive,
    gst_mode: z.enum(["exclusive", "inclusive"]),
    pvc_applicable: z.boolean(),
    overall_rebate: z
      .number()
      .min(0, "must be ≥ 0")
      .max(9.9999, "must be ≤ 9.9999 (stored as fraction, 0.15 = 15%)")
      .optional(),
    // overall_rebate stays `number | undefined`. It's NOT NULL in the DB
    // (default 0); leaving it blank means "do not change" on edit and
    // "use server default" on create. Backend H-2 rejects explicit null
    // on this column, so the schema must not surface one.
  })
  .refine(
    (v) =>
      !v.start_date || !v.completion_date || v.start_date <= v.completion_date,
    { path: ["completion_date"], message: "must be on or after start date" },
  )
  .refine(
    (v) => !v.start_date || v.base_month <= v.start_date,
    { path: ["start_date"], message: "must be on or after base month" },
  )
  .refine(
    (v) =>
      v.bid_amount === null ||
      v.contract_value === null ||
      v.bid_amount <= v.contract_value,
    { path: ["bid_amount"], message: "must be ≤ contract value" },
  );

export type ContractFormValues = z.infer<typeof contractCreateSchema>;
