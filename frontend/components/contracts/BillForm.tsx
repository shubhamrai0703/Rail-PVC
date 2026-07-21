"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";

// Mirrors backend BillCreate (api/bills.py). net_amount is intentionally
// absent: it is derived server-side, never a client input.
const billSchema = z.object({
  bill_number: z
    .number({ message: "required" })
    .int("must be a whole number")
    .min(1, "must be ≥ 1"),
  bill_date: z.string().min(1, "required"),
  measurement_date: z.string().min(1, "required"),
  gross_amount: z.number({ message: "required" }).gt(0, "must be > 0"),
});

type FormValues = z.infer<typeof billSchema>;

type Props = {
  contractId: string;
  onCreated: () => void;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

export function BillForm({ contractId, onCreated }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(billSchema),
  });

  async function submit(values: FormValues) {
    try {
      await apiFetch(`/api/contracts/${contractId}/bills`, {
        method: "POST",
        body: {
          bill_number: values.bill_number,
          bill_date: values.bill_date,
          measurement_date: values.measurement_date,
          // Send as string to preserve decimal precision for money.
          gross_amount: String(values.gross_amount),
        },
        // We render the conflict inline on the field, so suppress the toast
        // for the one case we handle ourselves.
        silent: true,
      });
    } catch (err) {
      const { ApiError } = await import("@/lib/api/client");
      if (err instanceof ApiError && err.detail?.code === "conflict") {
        setError("bill_number", { message: err.detail.message });
        return;
      }
      // Anything else: re-surface via the default toast path.
      const { toast } = await import("sonner");
      toast.error("Could not create bill", {
        description: err instanceof Error ? err.message : undefined,
      });
      return;
    }
    reset({
      bill_number: undefined,
      bill_date: "",
      measurement_date: "",
      gross_amount: undefined,
    });
    onCreated();
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="grid grid-cols-1 items-end gap-3 md:grid-cols-2 xl:grid-cols-[120px_1fr_1fr_220px_auto]"
      noValidate
    >
      <div>
        <label className={labelCls}>Bill no. *</label>
        <input
          type="number"
          step="1"
          {...register("bill_number", {
            setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
          })}
          className={inputCls}
          autoComplete="off"
        />
        {errors.bill_number && (
          <p className={errCls}>{errors.bill_number.message}</p>
        )}
      </div>
      <div>
        <label className={labelCls}>Bill date *</label>
        <input type="date" {...register("bill_date")} className={inputCls} />
        {errors.bill_date && <p className={errCls}>{errors.bill_date.message}</p>}
      </div>
      <div>
        <label className={labelCls}>Measurement date *</label>
        <input
          type="date"
          {...register("measurement_date")}
          className={inputCls}
        />
        <p className="mt-1 text-[11px] leading-4 text-slate-500">
          Use the Measurement Book date. It determines the bill&apos;s rolling
          three-month quarter from the contract base month.
        </p>
        {errors.measurement_date && (
          <p className={errCls}>{errors.measurement_date.message}</p>
        )}
      </div>
      <div>
        <label className={labelCls}>
          Gross amount <span className="text-slate-400">(₹)</span> *
        </label>
        <input
          type="number"
          step="0.01"
          {...register("gross_amount", {
            setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
          })}
          className={inputCls}
        />
        <p className="mt-1 text-[11px] leading-4 text-slate-500">
          On-account bill total from the Measurement Book. Cement/steel and
          other PVC exclusions are deducted during the PVC run, not here.
        </p>
        {errors.gross_amount && (
          <p className={errCls}>{errors.gross_amount.message}</p>
        )}
      </div>
      <Button type="submit" variant="primary" disabled={isSubmitting}>
        {isSubmitting ? "Adding…" : "Add bill"}
      </Button>
    </form>
  );
}
