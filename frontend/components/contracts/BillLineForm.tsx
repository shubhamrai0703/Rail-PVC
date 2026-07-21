"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api/client";
import {
  billLineSchema,
  type CreatedBillLine,
  type BillLineDecimalField,
  type BillLineFormValues,
} from "@/lib/billLine";
import type { SteelSubtype } from "@/lib/parseTsvImport";

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
}

interface ContractItem {
  id: string;
  item_code: string;
  description: string | null;
  unit: string | null;
  is_cement_item: boolean;
  steel_subtype: SteelSubtype;
}

type ItemOption = ContractItem & {
  scheduleName: string;
  scheduleType: Schedule["schedule_type"];
};

type Props = {
  billId: string;
  contractId: string;
  existingItemIds: string[];
  onCreated: (line: CreatedBillLine) => void | Promise<void>;
};

const DEFAULT_VALUES: BillLineFormValues = {
  item_id: "",
  qty_up_to_last: "0",
  qty_since_last: "0",
  qty_up_to_date: "0",
  amount_up_to_last: "0",
  amount_since_last: "0",
  amount_up_to_date: "0",
  special_condition_amount: "0",
};

const QUANTITY_FIELDS: Array<{
  name: BillLineDecimalField;
  label: string;
}> = [
  { name: "qty_up_to_last", label: "Up to last bill" },
  { name: "qty_since_last", label: "Since last bill" },
  { name: "qty_up_to_date", label: "Up to date" },
];

const AMOUNT_FIELDS: Array<{
  name: BillLineDecimalField;
  label: string;
}> = [
  { name: "amount_up_to_last", label: "Up to last bill" },
  { name: "amount_since_last", label: "Since last bill" },
  { name: "amount_up_to_date", label: "Up to date" },
  { name: "special_condition_amount", label: "Special condition" },
];

const labelCls = "block text-[12px] font-medium text-slate-700 mb-1";
const inputCls =
  "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-[13px] " +
  "text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500 " +
  "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";
const errCls = "mt-1 text-[11px] text-red-600";

function itemLabel(option: ItemOption): string {
  const classification = option.is_cement_item
    ? "cement"
    : option.steel_subtype
      ? `steel: ${option.steel_subtype.replaceAll("_", " ")}`
      : null;
  const detail = option.description?.trim() || "No description";
  const unit = option.unit?.trim() ? ` [${option.unit}]` : "";
  const tag = classification ? ` · ${classification}` : "";
  return `${option.scheduleName} (${option.scheduleType}) · ${option.item_code} — ${detail}${unit}${tag}`;
}

export function BillLineForm({
  billId,
  contractId,
  existingItemIds,
  onCreated,
}: Props) {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const schedulesQuery = useQuery<Schedule[]>({
    queryKey: ["contract-schedules", contractId],
    queryFn: () =>
      apiFetch<Schedule[]>(`/api/contracts/${contractId}/schedules`),
  });
  const schedules = useMemo(
    () => schedulesQuery.data ?? [],
    [schedulesQuery.data],
  );

  const itemQueries = useQueries({
    queries: schedules.map((schedule) => ({
      queryKey: ["schedule-items", schedule.id],
      queryFn: () =>
        apiFetch<ContractItem[]>(`/api/schedules/${schedule.id}/items`),
    })),
  });

  // A bill has no schedule_id. Load every schedule under its actual contract,
  // then preserve schedule context in each flattened option instead of
  // silently assuming the contract has only one schedule.
  const allOptions = useMemo<ItemOption[]>(
    () =>
      schedules.flatMap((schedule, index) =>
        (itemQueries[index]?.data ?? []).map((item) => ({
          ...item,
          scheduleName: schedule.name,
          scheduleType: schedule.schedule_type,
        })),
      ),
    [itemQueries, schedules],
  );
  const existingItemIdSet = useMemo(
    () => new Set(existingItemIds),
    [existingItemIds],
  );
  const availableOptions = useMemo(
    () => allOptions.filter((option) => !existingItemIdSet.has(option.id)),
    [allOptions, existingItemIdSet],
  );
  const optionsLoading =
    schedulesQuery.isLoading || itemQueries.some((query) => query.isLoading);
  const optionsError =
    schedulesQuery.isError || itemQueries.some((query) => query.isError);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BillLineFormValues>({
    resolver: zodResolver(billLineSchema),
    defaultValues: DEFAULT_VALUES,
  });

  async function submit(values: BillLineFormValues) {
    setSubmitError(null);
    try {
      const createdLine = await apiFetch<CreatedBillLine>(
        `/api/bills/${billId}/lines`,
        {
          method: "POST",
          // zodResolver returns the schema-parsed strings, including trimming.
          body: values,
          silent: true,
        },
      );
      await onCreated(createdLine);
      reset(DEFAULT_VALUES);
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Failed to add bill line",
      );
    }
  }

  const optionsReady = !optionsLoading && !optionsError;
  const optionsUnavailable = !optionsReady || availableOptions.length === 0;
  const noSchedules = optionsReady && schedules.length === 0;
  const noItems =
    optionsReady && schedules.length > 0 && allOptions.length === 0;
  const allItemsUsed =
    optionsReady &&
    allOptions.length > 0 &&
    availableOptions.length === 0;

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <div>
        <label htmlFor="bill-line-item" className={labelCls}>
          Contract item *
        </label>
        <select
          id="bill-line-item"
          {...register("item_id")}
          className={inputCls}
          disabled={optionsUnavailable}
        >
          <option value="">
            {optionsLoading ? "Loading contract items…" : "Select an item"}
          </option>
          {availableOptions.map((option) => (
            <option key={option.id} value={option.id}>
              {itemLabel(option)}
            </option>
          ))}
        </select>
        {errors.item_id && <p className={errCls}>{errors.item_id.message}</p>}
        {optionsError && (
          <p className={errCls} role="alert">
            Contract items could not be loaded. Refresh the page and try again.
          </p>
        )}
        {noSchedules && (
          <p className="mt-1 text-[11px] text-slate-500">
            Add a schedule and its contract items before entering bill lines.
          </p>
        )}
        {noItems && (
          <p className="mt-1 text-[11px] text-slate-500">
            No contract items are available in this contract&apos;s schedules.
          </p>
        )}
        {allItemsUsed && (
          <p className="mt-1 text-[11px] text-slate-500">
            Every contract item already has a line on this bill.
          </p>
        )}
      </div>

      <fieldset className="space-y-2">
        <legend className="text-[12px] font-medium text-slate-700">
          Quantities
        </legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {QUANTITY_FIELDS.map((field) => (
            <DecimalField
              key={field.name}
              name={field.name}
              label={field.label}
              register={register}
              error={errors[field.name]?.message}
            />
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-[12px] font-medium text-slate-700">
          Amounts <span className="text-slate-400">(₹)</span>
        </legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {AMOUNT_FIELDS.map((field) => (
            <DecimalField
              key={field.name}
              name={field.name}
              label={field.label}
              register={register}
              error={errors[field.name]?.message}
            />
          ))}
        </div>
      </fieldset>

      {submitError && (
        <p
          className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-600"
          role="alert"
        >
          {submitError}
        </p>
      )}

      <div className="flex justify-end">
        <Button
          type="submit"
          variant="primary"
          disabled={isSubmitting || optionsUnavailable}
        >
          {isSubmitting ? "Adding…" : "Add bill line"}
        </Button>
      </div>
    </form>
  );
}

function DecimalField({
  name,
  label,
  register,
  error,
}: {
  name: BillLineDecimalField;
  label: string;
  register: ReturnType<typeof useForm<BillLineFormValues>>["register"];
  error: string | undefined;
}) {
  const id = `bill-line-${name}`;
  return (
    <div>
      <label htmlFor={id} className={labelCls}>
        {label} *
      </label>
      <input
        id={id}
        type="number"
        step="0.0001"
        inputMode="decimal"
        {...register(name)}
        className={inputCls}
        aria-invalid={error ? "true" : "false"}
      />
      {error && <p className={errCls}>{error}</p>}
    </div>
  );
}
