"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";
import { SupplementaryHelp } from "@/components/help/FirstUserHelp";

const scheduleSchema = z.object({
  name: z.string().min(1, "required"),
  schedule_type: z.enum(["DSR", "NS", "ExtraNS"]),
  bid_discount_pct: z
    .number()
    .min(0, "must be ≥ 0%")
    .max(100, "must be ≤ 100%"),
});

type FormValues = z.infer<typeof scheduleSchema>;

type Props = {
  contractId: string;
  onCreated: () => void;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

export function ScheduleForm({ contractId, onCreated }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: { schedule_type: "DSR", bid_discount_pct: 0 },
  });
  const scheduleType = useWatch({ control, name: "schedule_type" });

  async function submit(values: FormValues) {
    await apiFetch(`/api/contracts/${contractId}/schedules`, {
      method: "POST",
      body: { ...values, bid_discount_pct: values.bid_discount_pct / 100 },
    });
    reset({ name: "", schedule_type: "DSR", bid_discount_pct: 0 });
    onCreated();
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="grid grid-cols-1 items-start gap-3 md:grid-cols-[1fr_160px_200px_auto]"
      noValidate
    >
      <div>
        <label className={labelCls}>Name *</label>
        <input {...register("name")} className={inputCls} autoComplete="off" />
        {errors.name && <p className={errCls}>{errors.name.message}</p>}
      </div>
      <div>
        <label className={labelCls}>Type *</label>
        <select {...register("schedule_type")} className={inputCls}>
          <option value="DSR">DSR</option>
          <option value="NS">NS</option>
          <option value="ExtraNS">ExtraNS</option>
        </select>
        <SupplementaryHelp summary="Choose the schedule type">
          DSR is for published schedule items, NS for agreement non-schedule
          items, and ExtraNS for later extra items.
        </SupplementaryHelp>
        {scheduleType === "ExtraNS" && (
          <p className="mt-1 text-[11px] leading-4 text-amber-800">
            Every ExtraNS item needs an eligibility decision before a PVC run
            can proceed.
          </p>
        )}
      </div>
      <div>
        <label className={labelCls}>Bid discount (%)</label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          {...register("bid_discount_pct", {
            setValueAs: (v) => (v === "" || v === null ? 0 : Number(v)),
          })}
          className={inputCls}
        />
        {errors.bid_discount_pct && (
          <p className={errCls}>{errors.bid_discount_pct.message}</p>
        )}
      </div>
      <div>
        <span aria-hidden="true" className={`${labelCls} invisible`}>
          Add
        </span>
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? "Adding…" : "Add"}
        </Button>
      </div>
    </form>
  );
}
