import { z } from "zod";

const decimalInput = z
  .string()
  .trim()
  .min(1, "required")
  .regex(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/, "must be a valid decimal")
  .refine(fitsNumeric15_4, {
    message: "must have at most 11 digits before and 4 after the decimal",
  });

function fitsNumeric15_4(value: string): boolean {
  const unsigned = value.replace(/^[+-]/, "");
  const [integer = "", fraction = ""] = unsigned.split(".");
  const significantIntegerDigits = integer.replace(/^0+/, "").length;
  return significantIntegerDigits <= 11 && fraction.length <= 4;
}

export const billLineSchema = z.object({
  item_id: z.string().trim().min(1, "select an item"),
  qty_up_to_last: decimalInput,
  qty_since_last: decimalInput,
  qty_up_to_date: decimalInput,
  amount_up_to_last: decimalInput,
  amount_since_last: decimalInput,
  amount_up_to_date: decimalInput,
  special_condition_amount: decimalInput,
});

export type BillLineFormValues = z.infer<typeof billLineSchema>;
export type CreatedBillLine = BillLineFormValues & {
  id: string;
  bill_id: string;
};
export type BillLineDecimalField = Exclude<
  keyof BillLineFormValues,
  "item_id"
>;
