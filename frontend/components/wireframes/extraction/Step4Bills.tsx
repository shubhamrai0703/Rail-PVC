"use client";

import { useState } from "react";
import { CalendarClock, Paperclip } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { formatINRWithSymbol } from "@/lib/format";
import { cn } from "@/lib/cn";
import {
  BILL_FIXTURES,
  DOC_KIND_LABEL,
  isBlocking,
} from "@/lib/wireframes/extraction";
import {
  FieldRow,
  ManualEntryEscape,
  SectionHeading,
  SourceChip,
  parseNumber,
  parseText,
} from "@/components/wireframes/Primitives";
import { useFieldOverrides } from "@/components/wireframes/useFieldOverrides";

export function Step4Bills() {
  const [slots, setSlots] = useState(3);
  const { effective, confirm, reject, resolve, enterManually } = useFieldOverrides();

  const visible = BILL_FIXTURES.slice(0, slots);

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Bill bundle intake"
        description="Tell us how many bills have been raised, then fill each slot with its measurement book and signed bill. Recoveries are optional. Each slot is prefilled independently — one unreadable bill does not block the others."
      />

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
        <label htmlFor="bill-slots" className="text-[13px] font-medium text-slate-700">
          How many bills have been raised?
        </label>
        <input
          id="bill-slots"
          type="number"
          min={1}
          max={BILL_FIXTURES.length}
          value={slots}
          onChange={(e) =>
            setSlots(
              Math.min(BILL_FIXTURES.length, Math.max(1, Number(e.target.value) || 1)),
            )
          }
          className="w-20 rounded border border-slate-200 px-2 py-1 font-mono text-[13px]"
        />
        <span className="text-[11px] text-slate-500">
          Fixture data covers {BILL_FIXTURES.length} slots.
        </span>
      </div>

      {/* The measurement-date rule, stated once and prominently. */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex items-start gap-2">
          <CalendarClock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" strokeWidth={1.75} />
          <p className="text-[12px] leading-5 text-slate-600">
            A measurement book prints a period, e.g.{" "}
            <span className="font-mono">From 09/05/2025 to 18/06/2025</span>. The{" "}
            <span className="font-medium text-slate-900">period end</span> is the measurement date
            that selects the quarter. The start is kept as evidence and never drives the
            calculation. Both are shown on every bill below.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {visible.map((bill) => {
          const k = (field: string) => `${bill.id}:${field}`;
          const billNumber = effective(k("billNumber"), bill.billNumber);
          const billDate = effective(k("billDate"), bill.billDate);
          const start = effective(k("measurementPeriodStart"), bill.measurementPeriodStart);
          const end = effective(k("measurementPeriodEnd"), bill.measurementPeriodEnd);
          const gross = effective(k("grossValue"), bill.grossValue);
          const empty = bill.attached.length === 0;

          return (
            <section
              key={bill.id}
              className={cn(
                "rounded-xl border p-4",
                empty ? "border-dashed border-slate-300 bg-slate-50" : "border-slate-200 bg-white",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-[13px] font-semibold text-slate-900">
                    Bill slot {bill.slot}
                  </h3>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {bill.lineCount > 0
                      ? `${bill.lineCount} lines proposed`
                      : "No documents in this slot yet"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {bill.attached.map((kind) => (
                    <span
                      key={kind}
                      className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10.5px] text-slate-600"
                    >
                      <Paperclip className="h-2.5 w-2.5" strokeWidth={1.75} />
                      {DOC_KIND_LABEL[kind]}
                    </span>
                  ))}
                  {bill.missing.map((kind) => (
                    <Badge key={kind} variant="blocked">
                      {DOC_KIND_LABEL[kind]} missing
                    </Badge>
                  ))}
                </div>
              </div>

              {empty ? (
                <div className="mt-3 rounded-lg border border-dashed border-slate-300 bg-white px-4 py-6 text-center">
                  <p className="text-[12px] text-slate-600">
                    Drop this bill&rsquo;s measurement book and signed bill here.
                  </p>
                  <div className="mt-2">
                    <ManualEntryEscape label="Or enter bill 3 by hand" />
                  </div>
                </div>
              ) : (
                <>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <FieldRow
                      label="Bill number"
                      field={billNumber}
                      format={(v) => v}
                      onConfirm={() => confirm(k("billNumber"))}
                      onReject={() => reject(k("billNumber"))}
                      onResolve={(v) => resolve(k("billNumber"), v)}
                      onEnterManually={(v) => enterManually(k("billNumber"), v)}
                      parse={parseText}
                      inputHint="e.g. 3rd on-account"
                    />
                    <FieldRow
                      label="Bill date"
                      field={billDate}
                      format={(v) => v}
                      onConfirm={() => confirm(k("billDate"))}
                      onReject={() => reject(k("billDate"))}
                      onResolve={(v) => resolve(k("billDate"), v)}
                      onEnterManually={(v) => enterManually(k("billDate"), v)}
                      parse={parseText}
                      inputHint="YYYY-MM-DD"
                    />
                  </div>

                  {/* Period start and end, visibly different weights. */}
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500">
                        Period start — evidence only
                      </p>
                      <p className="mt-0.5 font-mono text-[14px] tabular-nums text-slate-600">
                        {start.value ?? "—"}
                      </p>
                      <div className="mt-0.5">
                        <SourceChip source={start.source} />
                      </div>
                    </div>
                    <div className="rounded-lg border-2 border-amber-300 bg-amber-50 px-3 py-2.5">
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-amber-800">
                        Period end — selects the quarter
                      </p>
                      <p className="mt-0.5 font-mono text-[14px] tabular-nums text-amber-950">
                        {end.value ?? "—"}
                      </p>
                      <div className="mt-0.5">
                        <SourceChip source={end.source} />
                      </div>
                    </div>
                  </div>

                  <div className="mt-2">
                    <FieldRow
                      label="Gross value of work done"
                      help="The on-account MB total. PVC exclusions are deducted at run time, not here."
                      field={gross}
                      highStakes
                      format={(v) => formatINRWithSymbol(v)}
                      onConfirm={() => confirm(k("grossValue"))}
                      onReject={() => reject(k("grossValue"))}
                      onResolve={(v) => resolve(k("grossValue"), v)}
                      onEnterManually={(v) => enterManually(k("grossValue"), v)}
                      parse={parseNumber}
                      inputHint="Rupees, e.g. 3412775.00"
                    />
                  </div>

                  {isBlocking(gross.state) && (
                    <p className="mt-2 text-[11px] text-red-700">
                      This bill cannot be saved until the gross value is resolved. The other bills
                      in this bundle are unaffected.
                    </p>
                  )}

                  <div className="mt-3">
                    <ManualEntryEscape
                      label={`Enter bill ${bill.slot} by hand instead`}
                    />
                  </div>
                </>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
