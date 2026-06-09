"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { apiFetch, ApiError } from "@/lib/api/client";

const schema = z.object({
  bill_number: z.number({ message: "required" }).int("whole number").gt(0, "must be > 0"),
  bill_date: z.string().optional(),
  measurement_date: z.string().min(1, "required"),
  gross_amount: z.number({ message: "required" }).gt(0, "must be > 0"),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  billId: string;
  initial: {
    bill_number: number;
    bill_date: string | null;
    measurement_date: string;
    gross_amount: string | number | null;
  };
  onSaved: () => void;
  onCancel: () => void;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

export function BillHeaderForm({ billId, initial, onSaved, onCancel }: Props) {
  const [conflict, setConflict] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      bill_number: initial.bill_number,
      bill_date: initial.bill_date ?? "",
      measurement_date: initial.measurement_date,
      gross_amount:
        initial.gross_amount === null || initial.gross_amount === undefined
          ? undefined
          : Number(initial.gross_amount),
    },
  });

  async function submit(values: FormValues) {
    setConflict(null);
    try {
      await apiFetch(`/api/bills/${billId}`, {
        method: "PUT",
        silent: true,
        body: {
          bill_number: values.bill_number,
          // Empty date input clears the (nullable) bill_date.
          bill_date: values.bill_date ? values.bill_date : null,
          measurement_date: values.measurement_date,
          // String preserves decimal precision for money.
          gross_amount: String(values.gross_amount),
        },
      });
      onSaved();
    } catch (e) {
      // bill_number uniqueness is server-owned (UNIQUE(contract_id, bill_number));
      // surface the 409 inline rather than as a toast.
      if (e instanceof ApiError && e.detail?.code === "conflict") {
        setConflict(e.detail.message);
        return;
      }
      throw e;
    }
  }

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="border border-slate-200 rounded-xl p-5 bg-white space-y-4 max-w-2xl"
      noValidate
    >
      <div className="grid grid-cols-2 gap-x-8 gap-y-4">
        <div>
          <label className={labelCls}>Bill number *</label>
          <input
            type="number"
            {...register("bill_number", {
              setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
            })}
            className={inputCls}
          />
          {errors.bill_number && <p className={errCls}>{errors.bill_number.message}</p>}
          {conflict && <p className={errCls}>{conflict}</p>}
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
          {errors.gross_amount && <p className={errCls}>{errors.gross_amount.message}</p>}
        </div>
        <div>
          <label className={labelCls}>Bill date</label>
          <input type="date" {...register("bill_date")} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Measurement date *</label>
          <input type="date" {...register("measurement_date")} className={inputCls} />
          {errors.measurement_date && (
            <p className={errCls}>{errors.measurement_date.message}</p>
          )}
        </div>
      </div>
      <div className="flex gap-2">
        <Button type="submit" variant="primary" size="sm" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
