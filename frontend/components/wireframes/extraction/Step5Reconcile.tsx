"use client";

import { CheckCircle2, MinusCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { RECON_CHECKS, type CheckStatus } from "@/lib/wireframes/extraction";
import { ManualEntryEscape, SectionHeading } from "@/components/wireframes/Primitives";

const STATUS_ICON: Record<CheckStatus, React.ReactNode> = {
  pass: <CheckCircle2 className="h-4 w-4 text-green-600" strokeWidth={2} />,
  fail: <XCircle className="h-4 w-4 text-red-600" strokeWidth={2} />,
  skipped: <MinusCircle className="h-4 w-4 text-amber-600" strokeWidth={2} />,
};

const STATUS_STYLE: Record<CheckStatus, string> = {
  pass: "border-slate-200 bg-white",
  fail: "border-red-200 bg-red-50",
  skipped: "border-amber-200 bg-amber-50",
};

export function Step5Reconcile() {
  const failed = RECON_CHECKS.filter((c) => c.status === "fail");
  const skipped = RECON_CHECKS.filter((c) => c.status === "skipped");
  const passed = RECON_CHECKS.filter((c) => c.status === "pass");
  const canSave = failed.length === 0 && skipped.length === 0;

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Reconciliation"
        description="Deterministic checks against the values you confirmed. These are arithmetic and cross-document comparisons — no model is involved, and a check that cannot run is reported rather than passed."
      />

      {/* The verdict, stated before the detail. This screen exists for the failure case. */}
      <div
        className={cn(
          "rounded-xl border-2 px-4 py-3.5",
          canSave ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50",
        )}
      >
        <p
          className={cn(
            "text-[15px] font-semibold",
            canSave ? "text-green-900" : "text-red-900",
          )}
        >
          {canSave
            ? "All checks passed — this extraction is ready to write"
            : `Nothing will be saved — ${failed.length} check${failed.length === 1 ? "" : "s"} failed${
                skipped.length > 0
                  ? ` and ${skipped.length} could not run`
                  : ""
              }`}
        </p>
        <p
          className={cn(
            "mt-1 text-[12px] leading-5",
            canSave ? "text-green-800" : "text-red-800",
          )}
        >
          {canSave
            ? "Writing creates the contract, schedules, items and bills in one transaction. You can still review each screen before committing."
            : "A check that fails or cannot run blocks the write entirely. Partial saves are not offered here — half a contract is harder to repair than none."}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button variant="primary" disabled={!canSave}>
            Write contract, items and bills
          </Button>
          <span className="text-[11px] text-slate-600">
            {passed.length} of {RECON_CHECKS.length} checks passing
          </span>
        </div>
      </div>

      <ol className="space-y-2">
        {RECON_CHECKS.map((check) => (
          <li
            key={check.id}
            className={cn("rounded-xl border px-4 py-3", STATUS_STYLE[check.status])}
          >
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 shrink-0">{STATUS_ICON[check.status]}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium text-slate-900">{check.label}</p>
                <p className="mt-0.5 text-[11px] leading-4 text-slate-500">{check.detail}</p>

                {check.status === "fail" && (
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg border border-red-200 bg-white px-2.5 py-2">
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-red-700">
                        Found
                      </p>
                      <p className="mt-0.5 font-mono text-[12px] text-slate-900">
                        {check.observed}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white px-2.5 py-2">
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500">
                        Expected
                      </p>
                      <p className="mt-0.5 font-mono text-[12px] text-slate-900">
                        {check.expected}
                      </p>
                    </div>
                  </div>
                )}

                {check.status === "skipped" && (
                  <p className="mt-2 rounded-lg border border-amber-200 bg-white px-2.5 py-2 text-[12px] leading-5 text-amber-900">
                    <span className="font-medium">Could not run. </span>
                    {check.skipReason}
                  </p>
                )}

                {check.fixLabel && (
                  <div className="mt-2">
                    <Button size="sm" variant="secondary">
                      {check.fixLabel}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <p className="text-[12px] font-medium text-slate-700">If the documents are wrong</p>
        <p className="mt-1 text-[12px] leading-5 text-slate-600">
          Sometimes the paperwork genuinely disagrees with itself and no amount of re-reading
          fixes it. Reject the extraction and enter the contract by hand — the checks above run
          the same way on hand-entered data, so nothing is lost by doing it manually.
        </p>
        <div className="mt-2">
          <ManualEntryEscape label="Discard this extraction and start from the blank form" />
        </div>
      </div>
    </div>
  );
}
