"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Trash2 } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RecoveryForm, RECOVERY_TYPES } from "@/components/contracts/RecoveryForm";
import { BillLineForm } from "@/components/contracts/BillLineForm";
import { BillHeaderForm } from "@/components/contracts/BillHeaderForm";
import { formatINRWithSymbol } from "@/lib/format";
import {
  describePvcRunError,
  getPvcRunRecoveryActions,
} from "@/lib/pvcRunError";
import { statusVariant } from "@/lib/pvcRunStatus";
import {
  JourneyGuide,
  PageGuidance,
} from "@/components/help/FirstUserHelp";
import { TOTAL_PVC_GUIDANCE } from "@/lib/firstUserHelp";
import type { CreatedBillLine } from "@/lib/billLine";

interface Bill {
  id: string;
  contract_id: string;
  bill_number: number;
  bill_date: string | null;
  measurement_date: string;
  gross_amount: string | number | null;
  net_amount: string | number | null;
  status: string;
}

interface BillLine {
  id: string;
  bill_id: string;
  item_id: string;
  qty_up_to_last: string | number;
  qty_since_last: string | number;
  qty_up_to_date: string | number;
  amount_up_to_last: string | number;
  amount_since_last: string | number;
  amount_up_to_date: string | number;
  special_condition_amount: string | number;
}

interface Recovery {
  id: string;
  bill_id: string;
  recovery_type: string;
  amount: string | number;
  affects_pvc_base: boolean;
}

interface PvcRunResult {
  id: string;
  total_pvc: string | number;
  negative_carry_forward: string | number;
  quarter_used: string | number;
}

const RECOVERY_LABELS: Record<string, string> = Object.fromEntries(
  RECOVERY_TYPES.map((t) => [t.value, t.label]),
);

interface RunSummary {
  id: string;
  bill_id: string;
  bill_number: number;
  status: string;
  total_pvc: string | number | null;
  negative_carry_forward: string | number | null;
  quarter_used: string | null;
  approved_at: string | null;
  created_at: string;
}

export default function BillDetailPage({
  params,
}: {
  params: Promise<{ id: string; billId: string }>;
}) {
  const { id, billId } = use(params);
  const queryClient = useQueryClient();

  const billQuery = useQuery<Bill>({
    queryKey: ["bill", billId],
    queryFn: () => apiFetch<Bill>(`/api/bills/${billId}`),
  });

  const linesQuery = useQuery<BillLine[]>({
    queryKey: ["bill-lines", billId],
    queryFn: () => apiFetch<BillLine[]>(`/api/bills/${billId}/lines`),
  });
  const existingBillLineItemIds = useMemo(
    () => (linesQuery.data ?? []).map((line) => line.item_id),
    [linesQuery.data],
  );

  const recoveriesQuery = useQuery<Recovery[]>({
    queryKey: ["bill-recoveries", billId],
    queryFn: () => apiFetch<Recovery[]>(`/api/bills/${billId}/recoveries`),
  });

  // Run history for this contract, narrowed to this bill (D-4a). Re-fetched
  // after a new run so the freshly created run appears immediately.
  const runsQuery = useQuery<RunSummary[]>({
    queryKey: ["contract-runs", id],
    queryFn: () => apiFetch<RunSummary[]>(`/api/contracts/${id}/pvc-runs`),
  });
  // P7-M4: the backend emits lowercase UUIDs but the URL segment may carry an
  // uppercase one (bookmark/manual entry) — compare case-insensitively.
  const billRuns = (runsQuery.data ?? []).filter(
    (r) => r.bill_id.toLowerCase() === billId.toLowerCase(),
  );

  // Calculate PVC — calls the engine synchronously (POST /pvc-runs). A run
  // reads and snapshots the bill lines that already exist; it does not create
  // line inputs. `silent: true` because the failure is rendered inline below.
  const pvcRun = useMutation<PvcRunResult, Error>({
    mutationFn: () =>
      apiFetch<PvcRunResult>(`/api/contracts/${id}/pvc-runs`, {
        method: "POST",
        body: { bill_id: billId },
        headers: { "Idempotency-Key": crypto.randomUUID() },
        silent: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bill", billId] });
      queryClient.invalidateQueries({ queryKey: ["bill-lines", billId] });
      queryClient.invalidateQueries({ queryKey: ["contract-runs", id] });
    },
  });

  const pvcError = describePvcRunError(pvcRun.error);
  const recoveryActions = getPvcRunRecoveryActions(
    pvcError.validationErrors ?? [],
    id,
    billId,
  );

  const [editing, setEditing] = useState(false);

  // C-3: delete a recovery. Invalidate both the recoveries list and the bill —
  // net_amount is computed from recoveries, so it changes when one is removed.
  const deleteRecovery = useMutation<void, Error, string>({
    mutationFn: (recoveryId) =>
      apiFetch<void>(`/api/bills/${billId}/recoveries/${recoveryId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bill-recoveries", billId] });
      queryClient.invalidateQueries({ queryKey: ["bill", billId] });
    },
  });

  if (billQuery.isLoading) {
    return (
      <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
    );
  }

  if (billQuery.isError || !billQuery.data) {
    const err = billQuery.error;
    const msg =
      err instanceof ApiError && err.status === 404
        ? "Bill not found"
        : err instanceof Error
          ? err.message
          : "Failed to load bill";
    return (
      <div className="space-y-4">
        <BackLink id={id} />
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {msg}
        </div>
      </div>
    );
  }

  const bill = billQuery.data;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <BackLink id={id} />
        <div className="flex items-center gap-3">
          <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
            Bill #{bill.bill_number}
          </h1>
          <Badge variant={statusVariant(bill.status)}>{bill.status}</Badge>
        </div>
      </header>

      <JourneyGuide stage="calculate" />
      <PageGuidance
        title="Check the bill, then calculate"
        next="Open the result, compare W and components, then approve only when accepted."
      >
        The run uses this bill&apos;s measurement date, gross amount, selected
        PVC-base recoveries, existing bill lines, contract rules, item
        classifications, and required index months. Re-running creates a new
        auditable result and supersedes the previous draft.
      </PageGuidance>

      {/* Header fields — read-only with an inline edit toggle (C-3). */}
      {editing ? (
        <BillHeaderForm
          billId={billId}
          initial={{
            bill_number: bill.bill_number,
            bill_date: bill.bill_date,
            measurement_date: bill.measurement_date,
            gross_amount: bill.gross_amount,
          }}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ["bill", billId] });
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <div id="bill-header" className="max-w-2xl space-y-3">
          <dl className="grid grid-cols-1 gap-x-8 gap-y-3 text-[13px] sm:grid-cols-2">
            <Field label="Bill number" value={bill.bill_number} />
            <Field label="Status" value={bill.status} />
            <Field label="Bill date" value={bill.bill_date} />
            <Field label="Measurement date" value={bill.measurement_date} />
            <Field label="Gross amount" value={formatINRWithSymbol(bill.gross_amount)} />
            <Field
              label="Net amount (net of non-PVC recoveries)"
              value={
                bill.net_amount === null || bill.net_amount === undefined
                  ? "—"
                  : formatINRWithSymbol(bill.net_amount)
              }
            />
          </dl>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setEditing(true)}
          >
            Edit bill
          </Button>
        </div>
      )}

      {/* Calculate PVC uses the bill inputs and existing lines as they stand. */}
      <section className="border border-slate-200 rounded-xl p-5 bg-white space-y-3">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
          <div>
            <h2 className="text-[14px] font-medium text-slate-900">
              Price Variation (PVC)
            </h2>
            <p className="text-[12px] text-slate-500 mt-0.5 max-w-md">
              Calculates an immutable draft result from the bill data and any
              existing lines. It does not create bill-line inputs. Re-running
              supersedes the previous draft run.
            </p>
          </div>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => pvcRun.mutate()}
            disabled={pvcRun.isPending}
          >
            {pvcRun.isPending ? "Calculating…" : "Calculate PVC"}
          </Button>
        </div>

        {pvcRun.isError && (
          <div className="text-[12px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {/* P6-M4: surface the actionable engine validation list, not just
                the generic header, so the user knows what to fix. */}
            {pvcError.validationErrors ? (
              <>
                <p className="font-medium">{pvcError.message}</p>
                <ul className="list-disc list-inside mt-1 space-y-0.5">
                  {pvcError.validationErrors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
                {recoveryActions.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t border-red-200 pt-2">
                    {recoveryActions.map((action) => (
                      <Link
                        key={action.href}
                        href={action.href}
                        className="font-medium text-red-800 underline underline-offset-2"
                      >
                        {action.label} →
                      </Link>
                    ))}
                  </div>
                )}
              </>
            ) : (
              pvcError.message
            )}
          </div>
        )}

        {pvcRun.isSuccess && pvcRun.data && (
          <>
            <dl className="grid grid-cols-1 gap-4 border-t border-slate-100 pt-1 text-[13px] sm:grid-cols-3">
              <div className="pt-3">
                <dt className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
                  Total PVC
                </dt>
                <dd className="text-slate-900 mt-0.5 font-mono">
                  {formatINRWithSymbol(pvcRun.data.total_pvc)}
                </dd>
              </div>
              <div className="pt-3">
                <dt className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
                  Negative carry-forward
                </dt>
                <dd className="text-slate-900 mt-0.5 font-mono">
                  {formatINRWithSymbol(pvcRun.data.negative_carry_forward)}
                </dd>
              </div>
              <div className="pt-3">
                <dt className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
                  Quarter used
                </dt>
                <dd className="text-slate-900 mt-0.5">
                  {String(pvcRun.data.quarter_used)}
                </dd>
              </div>
            </dl>
            <p className="text-[12px] leading-5 text-slate-600">
              {TOTAL_PVC_GUIDANCE} Confirm the quarter against the annexure
              first, then open the full result to review W and every component
              before approval.
            </p>
            <Link
              href={`/contracts/${id}/bills/${billId}/runs/${pvcRun.data.id}`}
              className="inline-flex items-center gap-1 text-[12px] font-medium text-slate-700 hover:text-slate-900"
            >
              View full results →
            </Link>
          </>
        )}
      </section>

      {/* Run history (D-4a) — every run for this bill, newest first. */}
      {billRuns.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-[14px] font-medium text-slate-900">Run history</h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <div
              className="grid min-w-[620px] grid-cols-[1fr_140px_120px_100px] gap-4 px-5 py-3
                         text-[11px] uppercase tracking-wider text-slate-500 font-medium
                         border-b border-slate-200 bg-slate-50"
            >
              <div>Created</div>
              <div className="text-right">Total PVC</div>
              <div>Status</div>
              <div className="sr-only">View</div>
            </div>
            {billRuns.map((r, i) => (
              <Link
                key={r.id}
                href={`/contracts/${id}/bills/${billId}/runs/${r.id}`}
                className={
                  "grid h-11 min-w-[620px] grid-cols-[1fr_140px_120px_100px] items-center gap-4 px-5 text-[13px] hover:bg-slate-50 " +
                  (i < billRuns.length - 1 ? "border-b border-slate-100" : "")
                }
              >
                <div className="text-slate-700">
                  {new Date(r.created_at).toLocaleString()}
                </div>
                <div className="text-right font-mono text-[12px] text-slate-900">
                  {r.total_pvc === null ? "—" : formatINRWithSymbol(r.total_pvc)}
                </div>
                <div>
                  <Badge variant={statusVariant(r.status)}>{r.status}</Badge>
                </div>
                <div className="text-right text-[12px] text-slate-400">View →</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Bill-line inputs feed item-classified deductions in the next PVC run. */}
      <section className="space-y-3">
        <h2 className="text-[14px] font-medium text-slate-900">Bill lines</h2>
        <p className="text-[12px] leading-5 text-slate-500">
          Add one item-wise line for each billed contract item. TenderAudit uses
          the item&apos;s classification and these amounts to derive cement,
          steel, and ExtraNS deductions in the next PVC run.
        </p>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-3 text-[14px] font-medium text-slate-900">
            Add bill line
          </h3>
          {linesQuery.isLoading ? (
            <p className="text-[12px] text-slate-400">
              Loading existing bill lines…
            </p>
          ) : linesQuery.isError ? (
            <p className="text-[12px] text-red-600" role="alert">
              Existing bill lines could not be loaded. Refresh the page before
              adding another line.
            </p>
          ) : (
            <BillLineForm
              billId={billId}
              contractId={bill.contract_id}
              existingItemIds={existingBillLineItemIds}
              onCreated={async (createdLine: CreatedBillLine) => {
                await queryClient.cancelQueries({
                  queryKey: ["bill-lines", billId],
                });
                queryClient.setQueryData<BillLine[]>(
                  ["bill-lines", billId],
                  (current) => [...(current ?? []), createdLine],
                );
                await queryClient.invalidateQueries({
                  queryKey: ["bill-lines", billId],
                });
              }}
            />
          )}
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <div
            className="grid min-w-[760px] grid-cols-[1fr_repeat(4,minmax(0,1fr))] gap-4 px-5 py-3
                       text-[11px] uppercase tracking-wider text-slate-500 font-medium
                       border-b border-slate-200 bg-slate-50"
          >
            <div>Item</div>
            <div className="text-right">Qty to date</div>
            <div className="text-right">Amt since last</div>
            <div className="text-right">Amt to date</div>
            <div className="text-right">Special cond.</div>
          </div>
          {linesQuery.isLoading && (
            <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
          )}
          {linesQuery.isError && (
            <div className="px-5 py-6 text-[13px] text-red-600" role="alert">
              Bill lines could not be loaded. Refresh the page and try again.
            </div>
          )}
          {!linesQuery.isLoading &&
            !linesQuery.isError &&
            (linesQuery.data?.length ?? 0) === 0 && (
              <div className="px-5 py-6 text-[13px] text-slate-400">
                No bill lines yet. Add the first billed item above before
                calculating PVC when item-wise deductions apply.
              </div>
            )}
          {linesQuery.data?.map((l, i) => (
            <div
              key={l.id}
              className={
                "grid h-11 min-w-[760px] grid-cols-[1fr_repeat(4,minmax(0,1fr))] items-center gap-4 px-5 text-[12px] font-mono text-slate-700 " +
                (i < linesQuery.data!.length - 1 ? "border-b border-slate-100" : "")
              }
            >
              <div className="truncate">{l.item_id}</div>
              <div className="text-right">{String(l.qty_up_to_date)}</div>
              <div className="text-right">
                {formatINRWithSymbol(l.amount_since_last)}
              </div>
              <div className="text-right">
                {formatINRWithSymbol(l.amount_up_to_date)}
              </div>
              <div className="text-right">
                {formatINRWithSymbol(l.special_condition_amount)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Recoveries — manually entered. */}
      <section className="space-y-2">
        <h2 className="text-[14px] font-medium text-slate-900">Recoveries</h2>
        <p className="text-[12px] leading-5 text-slate-500">
          Only recoveries marked Affects PVC base reduce W. Other recoveries
          remain part of the bill&apos;s net amount calculation only.
        </p>
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <div
            className="grid min-w-[620px] grid-cols-[1fr_160px_160px_60px] gap-4 px-5 py-3
                       text-[11px] uppercase tracking-wider text-slate-500 font-medium
                       border-b border-slate-200 bg-slate-50"
          >
            <div>Type</div>
            <div className="text-right">Amount</div>
            <div>Affects PVC base</div>
            <div className="sr-only">Actions</div>
          </div>
          {recoveriesQuery.isLoading && (
            <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
          )}
          {!recoveriesQuery.isLoading &&
            (recoveriesQuery.data?.length ?? 0) === 0 && (
              <div className="px-5 py-6 text-[13px] text-slate-400">
                No recoveries yet. Add one below.
              </div>
            )}
          {recoveriesQuery.data?.map((r, i) => (
            <div
              key={r.id}
              className={
                "grid h-11 min-w-[620px] grid-cols-[1fr_160px_160px_60px] items-center gap-4 px-5 text-[13px] " +
                (i < recoveriesQuery.data!.length - 1
                  ? "border-b border-slate-100"
                  : "")
              }
            >
              <div className="text-slate-900">
                {RECOVERY_LABELS[r.recovery_type] ?? r.recovery_type}
              </div>
              <div className="text-right font-mono text-[12px] text-slate-700">
                {formatINRWithSymbol(r.amount)}
              </div>
              <div>
                {r.affects_pvc_base ? (
                  <Badge variant="blocked">Yes</Badge>
                ) : (
                  <span className="text-slate-400 text-[12px]">No</span>
                )}
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  aria-label={`Delete ${RECOVERY_LABELS[r.recovery_type] ?? r.recovery_type} recovery`}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Delete this recovery? This also updates the bill's net amount.",
                      )
                    ) {
                      deleteRecovery.mutate(r.id);
                    }
                  }}
                  disabled={deleteRecovery.isPending}
                  className="text-slate-400 hover:text-red-600 disabled:opacity-40"
                >
                  <Trash2 className="h-4 w-4" strokeWidth={1.75} />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="border border-slate-200 rounded-xl p-5 bg-white">
          <h3 className="text-[14px] font-medium text-slate-900 mb-3">
            Add recovery
          </h3>
          <RecoveryForm
            billId={billId}
            onCreated={() =>
              queryClient.invalidateQueries({
                queryKey: ["bill-recoveries", billId],
              })
            }
          />
        </div>
      </section>
    </div>
  );
}

function BackLink({ id }: { id: string }) {
  return (
    <Link
      href={`/contracts/${id}/bills`}
      className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
    >
      <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
      Bills
    </Link>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
        {label}
      </dt>
      <dd className="text-slate-900 mt-0.5">
        {value === null || value === undefined || value === "" ? (
          <span className="text-slate-400">—</span>
        ) : (
          String(value)
        )}
      </dd>
    </div>
  );
}
