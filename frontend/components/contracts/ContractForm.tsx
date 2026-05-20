"use client";

import { useEffect } from "react";
import { useForm, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { Button } from "@/components/ui/Button";
import {
  contractCreateSchema,
  type ContractFormValues,
} from "@/lib/contracts-schema";
import { ZoneSelect } from "./ZoneSelect";

// The schema's *input* type is what react-hook-form sees pre-resolver
// (i.e. raw form values: `string | undefined`). The schema's *output* type
// — `ContractFormValues` — is what the resolver hands back. The form is
// typed against both so M-4's `"" → null` transform doesn't break the
// resolver type contract.
type FormInput = z.input<typeof contractCreateSchema>;

type Props = {
  defaultValues?: Partial<FormInput>;
  onSubmit: (values: ContractFormValues) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  /** Set per-field server errors (e.g. agreement_number 409 conflict). */
  serverFieldError?: { field: keyof FormInput; message: string } | null;
};

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 placeholder:text-slate-400 focus:outline-none " +
  "focus:ring-2 focus:ring-amber-500";
const errCls = "mt-1 text-[11px] text-red-600";

function defaultFormValues(
  d?: Partial<FormInput>,
): Partial<FormInput> {
  return {
    gst_mode: "exclusive",
    pvc_applicable: true,
    ...d,
  };
}

export function ContractForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "Create contract",
  serverFieldError,
}: Props) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, ContractFormValues>({
    resolver: zodResolver(contractCreateSchema),
    defaultValues: defaultFormValues(defaultValues),
  });

  // REVIEW.md H-3 — `setError` is a state mutation. Calling it in the render
  // body queues a re-render on every render where `serverFieldError` is truthy,
  // which then re-runs the render body and re-calls setError. React-hook-form's
  // internal guard keeps this from looping today, but the contract that
  // setState can't run during render is broken. Run the translation as an
  // effect keyed on the (stable) serverFieldError identity.
  useEffect(() => {
    if (serverFieldError) {
      setError(serverFieldError.field, { message: serverFieldError.message });
    }
  }, [serverFieldError, setError]);

  const submit: SubmitHandler<ContractFormValues> = async (values) => {
    await onSubmit(values);
  };

  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="space-y-5 max-w-3xl"
      noValidate
    >
      {/* Identification */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Tender number *</label>
          <input
            {...register("tender_number")}
            className={inputCls}
            autoComplete="off"
          />
          {errors.tender_number && (
            <p className={errCls}>{errors.tender_number.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>Agreement number</label>
          <input
            {...register("agreement_number")}
            className={inputCls}
            autoComplete="off"
          />
          {errors.agreement_number && (
            <p className={errCls}>{errors.agreement_number.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>LOA number</label>
          <input {...register("loa_number")} className={inputCls} />
          {errors.loa_number && (
            <p className={errCls}>{errors.loa_number.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>LOA date</label>
          <input
            type="date"
            {...register("loa_date")}
            className={inputCls}
          />
          {errors.loa_date && (
            <p className={errCls}>{errors.loa_date.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className={labelCls}>Contractor name *</label>
        <input {...register("contractor_name")} className={inputCls} />
        {errors.contractor_name && (
          <p className={errCls}>{errors.contractor_name.message}</p>
        )}
      </div>

      <div>
        <label className={labelCls}>Work description</label>
        <textarea
          {...register("work_description")}
          rows={3}
          className={inputCls.replace("h-9", "min-h-[72px] py-2")}
        />
      </div>

      {/* Zone + base month */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Railway zone *</label>
          <ZoneSelect
            {...register("railway_zone")}
            error={errors.railway_zone?.message}
          />
          {errors.railway_zone && (
            <p className={errCls}>{errors.railway_zone.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>Base month *</label>
          {/* `<input type="month">` yields YYYY-MM; the parent page appends -01. */}
          <input
            type="month"
            {...register("base_month", {
              setValueAs: (v) =>
                typeof v === "string" && /^\d{4}-\d{2}$/.test(v)
                  ? `${v}-01`
                  : v,
            })}
            className={inputCls}
          />
          {errors.base_month && (
            <p className={errCls}>{errors.base_month.message}</p>
          )}
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Start date</label>
          <input
            type="date"
            {...register("start_date")}
            className={inputCls}
          />
          {errors.start_date && (
            <p className={errCls}>{errors.start_date.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>Completion date</label>
          <input
            type="date"
            {...register("completion_date")}
            className={inputCls}
          />
          {errors.completion_date && (
            <p className={errCls}>{errors.completion_date.message}</p>
          )}
        </div>
      </div>

      {/* Money */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Contract value</label>
          <input
            type="number"
            step="0.01"
            {...register("contract_value", {
              setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
            })}
            className={inputCls}
          />
          {errors.contract_value && (
            <p className={errCls}>{errors.contract_value.message}</p>
          )}
        </div>
        <div>
          <label className={labelCls}>
            Bid amount <span className="text-slate-400">(≤ contract value)</span>
          </label>
          <input
            type="number"
            step="0.01"
            {...register("bid_amount", {
              setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
            })}
            className={inputCls}
          />
          {errors.bid_amount && (
            <p className={errCls}>{errors.bid_amount.message}</p>
          )}
        </div>
      </div>

      {/* GST + PVC + rebate */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className={labelCls}>GST mode *</label>
          <select {...register("gst_mode")} className={inputCls}>
            <option value="exclusive">Exclusive</option>
            <option value="inclusive">Inclusive</option>
          </select>
        </div>
        <div className="flex items-end pb-1">
          <label className="inline-flex items-center gap-2 text-[13px] text-slate-700">
            <input
              type="checkbox"
              {...register("pvc_applicable")}
              className="h-4 w-4 rounded border-slate-300"
            />
            PVC applicable
          </label>
        </div>
        <div>
          <label className={labelCls}>
            Overall rebate{" "}
            <span className="text-slate-400">(as decimal, 0.15 = 15%)</span>
          </label>
          <input
            type="number"
            step="0.0001"
            {...register("overall_rebate", {
              setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
            })}
            className={inputCls}
          />
          {errors.overall_rebate && (
            <p className={errCls}>{errors.overall_rebate.message}</p>
          )}
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
