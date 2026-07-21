"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";

// Mirrors backend VALID_RECOVERY_TYPES (api/bills.py) / recovery_type ENUM.
export const RECOVERY_TYPES = [
  { value: "security_deposit", label: "Security deposit" },
  { value: "income_tax", label: "Income tax" },
  { value: "labour_cess", label: "Labour cess" },
  { value: "water", label: "Water" },
  { value: "other", label: "Other" },
] as const;

const recoverySchema = z.object({
  recovery_type: z.enum([
    "security_deposit",
    "income_tax",
    "labour_cess",
    "water",
    "other",
  ]),
  amount: z.number({ message: "required" }).gt(0, "must be > 0"),
  affects_pvc_base: z.boolean(),
});

type FormValues = z.infer<typeof recoverySchema>;

type Props = {
  billId: string;
  onCreated: () => void;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

export function RecoveryForm({ billId, onCreated }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(recoverySchema),
    defaultValues: { recovery_type: "security_deposit", affects_pvc_base: false },
  });

  async function submit(values: FormValues) {
    await apiFetch(`/api/bills/${billId}/recoveries`, {
      method: "POST",
      body: {
        recovery_type: values.recovery_type,
        // String preserves decimal precision for money.
        amount: String(values.amount),
        affects_pvc_base: values.affects_pvc_base,
      },
    });
    reset({
      recovery_type: "security_deposit",
      amount: undefined,
      affects_pvc_base: false,
    });
    onCreated();
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="grid grid-cols-1 items-end gap-3 md:grid-cols-[1fr_180px_220px_auto]"
      noValidate
    >
      <div>
        <label className={labelCls}>Type *</label>
        <select {...register("recovery_type")} className={inputCls}>
          {RECOVERY_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className={labelCls}>
          Amount <span className="text-slate-400">(₹)</span> *
        </label>
        <input
          type="number"
          step="0.01"
          {...register("amount", {
            setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
          })}
          className={inputCls}
        />
        {errors.amount && <p className={errCls}>{errors.amount.message}</p>}
      </div>
      <div>
        <label className="flex h-9 items-center gap-2 text-[12px] text-slate-700">
          <input
            type="checkbox"
            {...register("affects_pvc_base")}
            className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
          />
          Affects PVC base
        </label>
        <p className="text-[11px] leading-4 text-slate-500">
          Select only when this recovery reduces W in your PVC working.
          Unselected recoveries affect the bill&apos;s net amount, not W.
        </p>
      </div>
      <Button type="submit" variant="primary" disabled={isSubmitting}>
        {isSubmitting ? "Adding…" : "Add recovery"}
      </Button>
    </form>
  );
}
