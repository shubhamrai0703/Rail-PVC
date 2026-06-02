"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api/client";
import { humanizeSeries } from "@/lib/indices";

// <input type="month"> yields "YYYY-MM"; the backend wants a first-of-month date.
const indexMonthSchema = z.object({
  month: z.string().regex(/^\d{4}-\d{2}$/, "pick a month"),
  value: z.number({ message: "required" }).gt(0, "must be > 0"),
  source_ref: z.string().optional(),
});

type FormValues = z.infer<typeof indexMonthSchema>;

type Props = {
  seriesName: string;
  onCreated: () => void;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

export function IndexMonthForm({ seriesName, onCreated }: Props) {
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(indexMonthSchema) });

  async function submit(values: FormValues) {
    setFormError(null);
    try {
      await apiFetch(`/api/indices/${encodeURIComponent(seriesName)}/months`, {
        method: "POST",
        // silent: we render failures inline rather than as a toast.
        silent: true,
        body: {
          month: `${values.month}-01`, // first-of-month, per backend validator
          // String preserves decimal precision for the Decimal column.
          value: String(values.value),
          source_ref: values.source_ref?.trim() || undefined,
        },
      });
      reset({ month: "", value: undefined, source_ref: "" });
      onCreated();
    } catch (err) {
      if (err instanceof ApiError) {
        switch (err.detail?.code) {
          case "forbidden":
            // The form renders for everyone; the only signal a non-admin gets
            // that this action isn't theirs is this message.
            setFormError("Adding index months requires admin access.");
            break;
          case "conflict":
            setFormError(
              `An observation for ${humanizeSeries(seriesName)} in ${values.month} already exists.`,
            );
            break;
          default:
            setFormError(err.message);
        }
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="grid grid-cols-[160px_160px_1fr_auto] gap-3 items-end"
      noValidate
    >
      <div>
        <label className={labelCls}>Month *</label>
        <input type="month" {...register("month")} className={inputCls} />
        {errors.month && <p className={errCls}>{errors.month.message}</p>}
      </div>
      <div>
        <label className={labelCls}>Value *</label>
        <input
          type="number"
          step="0.01"
          {...register("value", {
            setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
          })}
          className={inputCls}
        />
        {errors.value && <p className={errCls}>{errors.value.message}</p>}
      </div>
      <div>
        <label className={labelCls}>
          Source ref <span className="text-slate-400">(optional)</span>
        </label>
        <input type="text" {...register("source_ref")} className={inputCls} />
      </div>
      <Button type="submit" variant="primary" disabled={isSubmitting}>
        {isSubmitting ? "Adding…" : "Add month"}
      </Button>

      {formError && (
        <p className="col-span-4 text-[12px] text-red-600 bg-red-50 border border-red-100 rounded-md px-3 py-2">
          {formError}
        </p>
      )}
    </form>
  );
}
