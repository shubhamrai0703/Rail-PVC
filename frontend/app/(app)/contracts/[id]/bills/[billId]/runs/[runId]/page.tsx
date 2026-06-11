"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Download, FileText } from "lucide-react";
import { apiFetch, apiDownload, ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatINRWithSymbol } from "@/lib/format";
import { statusVariant, canExportRun } from "@/lib/pvcRunStatus";
import { describeWDerivation, type WDerivation } from "@/lib/pvcWDerivation";

interface PvcComponent {
  category: string;
  eligible_amount: string | number;
  base_index: string | number;
  current_avg_index: string | number;
  weight: string | number;
  pvc_value: string | number;
}

interface SnapshotLine {
  id: string;
  item_id: string;
  qty_up_to_date: string | number;
  amount_since_last: string | number;
  amount_up_to_date: string | number;
  special_condition_amount: string | number;
}

interface PvcRun {
  id: string;
  contract_id: string;
  bill_id: string;
  status: string;
  total_pvc: string | number | null;
  negative_carry_forward: string | number | null;
  quarter_used: string | null;
  superseded_by: string | null;
  w_derivation: WDerivation | null;
  /** Bill lines as they stood when this run was calculated (P7-H2).
   *  null on runs that pre-date migration 016. */
  lines_snapshot: SnapshotLine[] | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  components: PvcComponent[];
}

export default function PvcRunPage({
  params,
}: {
  params: Promise<{ id: string; billId: string; runId: string }>;
}) {
  const { id, billId, runId } = use(params);
  const queryClient = useQueryClient();

  const runQuery = useQuery<PvcRun>({
    queryKey: ["pvc-run", runId],
    queryFn: () => apiFetch<PvcRun>(`/api/pvc-runs/${runId}`),
  });

  // Approve — flips Draft/Calculated → Approved. 409 (immutable_approved_run)
  // is rendered inline rather than toasted, so `silent: true`.
  const approve = useMutation<{ status: string }, Error>({
    mutationFn: () =>
      apiFetch<{ status: string }>(`/api/pvc-runs/${runId}/approve`, {
        method: "POST",
        silent: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pvc-run", runId] });
      queryClient.invalidateQueries({ queryKey: ["contract-runs", id] });
    },
  });

  const [downloading, setDownloading] = useState<null | "excel" | "pdf">(null);

  async function handleExport(kind: "excel" | "pdf") {
    setDownloading(kind);
    try {
      const ext = kind === "excel" ? "xlsx" : "pdf";
      await apiDownload(
        `/api/pvc-runs/${runId}/export/${kind}`,
        `pvc_run_${runId}.${ext}`,
      );
    } catch {
      // apiDownload already surfaced a toast.
    } finally {
      setDownloading(null);
    }
  }

  if (runQuery.isLoading) {
    return (
      <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
    );
  }

  if (runQuery.isError || !runQuery.data) {
    const err = runQuery.error;
    const msg =
      err instanceof ApiError && err.status === 404
        ? "PVC run not found"
        : err instanceof Error
          ? err.message
          : "Failed to load run";
    return (
      <div className="space-y-4">
        <BackLink id={id} billId={billId} />
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {msg}
        </div>
      </div>
    );
  }

  const run = runQuery.data;
  const wSteps = describeWDerivation(run.w_derivation);
  const exportable = canExportRun(run.status);
  const approveError =
    approve.error instanceof ApiError ? approve.error : null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <BackLink id={id} billId={billId} />
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
              PVC run
            </h1>
            <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
          </div>
          <div className="flex items-center gap-2">
            {run.status === "Calculated" && (
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => approve.mutate()}
                disabled={approve.isPending}
              >
                {approve.isPending ? "Approving…" : "Approve run"}
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => handleExport("excel")}
              disabled={!exportable || downloading !== null}
              title={
                exportable ? undefined : "Approve the run to enable export"
              }
            >
              <Download className="h-3.5 w-3.5 mr-1" strokeWidth={1.75} />
              {downloading === "excel" ? "Exporting…" : "Excel"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => handleExport("pdf")}
              disabled={!exportable || downloading !== null}
              title={
                exportable ? undefined : "Approve the run to enable export"
              }
            >
              <FileText className="h-3.5 w-3.5 mr-1" strokeWidth={1.75} />
              {downloading === "pdf" ? "Exporting…" : "PDF"}
            </Button>
          </div>
        </div>
      </header>

      {run.status === "Superseded" && (
        <div className="text-[12px] text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          This run was superseded by a newer calculation and can no longer be
          approved.{" "}
          {run.superseded_by && (
            <Link
              href={`/contracts/${id}/bills/${billId}/runs/${run.superseded_by}`}
              className="text-slate-900 underline underline-offset-2"
            >
              View the current run
            </Link>
          )}
        </div>
      )}

      {approveError && (
        <div className="text-[12px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
          {approveError.detail?.code === "immutable_approved_run"
            ? "This run is already approved and can no longer be changed."
            : approveError.message}
        </div>
      )}

      {/* Result summary. */}
      <dl className="grid grid-cols-3 gap-4 text-[13px]">
        <Summary
          label="Total PVC"
          value={
            run.total_pvc === null
              ? "—"
              : formatINRWithSymbol(run.total_pvc)
          }
          mono
        />
        <Summary
          label="Negative carry-forward"
          value={
            run.negative_carry_forward === null
              ? "—"
              : formatINRWithSymbol(run.negative_carry_forward)
          }
          mono
        />
        <Summary label="Quarter used" value={run.quarter_used ?? "—"} />
      </dl>

      <dl className="grid grid-cols-3 gap-4 text-[13px] text-slate-500">
        <Summary label="Created" value={formatDateTime(run.created_at)} small />
        <Summary
          label="Approved by"
          value={run.approved_by ?? "—"}
          small
        />
        <Summary
          label="Approved at"
          value={run.approved_at ? formatDateTime(run.approved_at) : "—"}
          small
        />
      </dl>

      {/* W derivation — every subtraction named (PRODUCT.md rule 1). */}
      <section className="space-y-2">
        <h2 className="text-[14px] font-medium text-slate-900">W derivation</h2>
        {wSteps.length === 0 ? (
          <div className="text-[13px] text-slate-400 border border-slate-200 rounded-xl bg-white px-5 py-6">
            W was not derived for this run.
          </div>
        ) : (
          <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
            {wSteps.map((step, i) => (
              <div
                key={step.label}
                className={
                  "px-5 h-11 flex items-center justify-between text-[13px] " +
                  (step.kind === "total"
                    ? "bg-slate-50 font-medium text-slate-900 border-t border-slate-200"
                    : "text-slate-700 " +
                      (i < wSteps.length - 1 ? "border-b border-slate-100" : ""))
                }
              >
                <span>
                  {step.kind === "subtraction" && (
                    <span className="text-slate-400 mr-1">−</span>
                  )}
                  {step.label}
                </span>
                <span className="font-mono">
                  {formatINRWithSymbol(step.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Component breakdown. */}
      <section className="space-y-2">
        <h2 className="text-[14px] font-medium text-slate-900">
          Component breakdown
        </h2>
        <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div
            className="px-5 py-3 grid grid-cols-[1.2fr_repeat(5,minmax(0,1fr))] gap-4
                       text-[11px] uppercase tracking-wider text-slate-500 font-medium
                       border-b border-slate-200 bg-slate-50"
          >
            <div>Category</div>
            <div className="text-right">Eligible amt</div>
            <div className="text-right">Base index</div>
            <div className="text-right">Curr. avg index</div>
            <div className="text-right">Weight</div>
            <div className="text-right">PVC value</div>
          </div>
          {run.components.length === 0 && (
            <div className="px-5 py-6 text-[13px] text-slate-400">
              No components — this run produced no eligible categories.
            </div>
          )}
          {run.components.map((c, i) => (
            <div
              key={c.category}
              className={
                "px-5 h-11 grid grid-cols-[1.2fr_repeat(5,minmax(0,1fr))] gap-4 items-center text-[12px] " +
                (i < run.components.length - 1 ? "border-b border-slate-100" : "")
              }
            >
              <div className="text-slate-900 capitalize">{c.category}</div>
              <div className="text-right font-mono text-slate-700">
                {formatINRWithSymbol(c.eligible_amount)}
              </div>
              <div className="text-right font-mono text-slate-700">
                {String(c.base_index)}
              </div>
              <div className="text-right font-mono text-slate-700">
                {String(c.current_avg_index)}
              </div>
              <div className="text-right font-mono text-slate-700">
                {String(c.weight)}
              </div>
              <div className="text-right font-mono text-slate-900">
                {formatINRWithSymbol(c.pvc_value)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Bill lines as of this run (P7-H2). Live lines can change after a
          recalculate, so the run renders only its own snapshot. */}
      <section className="space-y-2">
        <h2 className="text-[14px] font-medium text-slate-900">
          Bill lines at calculation
        </h2>
        {run.lines_snapshot === null ? (
          <div className="text-[13px] text-slate-400 border border-slate-200 rounded-xl bg-white px-5 py-6">
            Bill lines were not captured for this run — it pre-dates line
            snapshots. The bill page shows the current lines.
          </div>
        ) : (
          <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
            <div
              className="px-5 py-3 grid grid-cols-[1fr_repeat(4,minmax(0,1fr))] gap-4
                         text-[11px] uppercase tracking-wider text-slate-500 font-medium
                         border-b border-slate-200 bg-slate-50"
            >
              <div>Item</div>
              <div className="text-right">Qty to date</div>
              <div className="text-right">Amt since last</div>
              <div className="text-right">Amt to date</div>
              <div className="text-right">Special cond.</div>
            </div>
            {run.lines_snapshot.length === 0 && (
              <div className="px-5 py-6 text-[13px] text-slate-400">
                The bill had no lines when this run was calculated.
              </div>
            )}
            {run.lines_snapshot.map((l, i) => (
              <div
                key={l.id}
                className={
                  "px-5 h-11 grid grid-cols-[1fr_repeat(4,minmax(0,1fr))] gap-4 items-center text-[12px] font-mono text-slate-700 " +
                  (i < run.lines_snapshot!.length - 1 ? "border-b border-slate-100" : "")
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
        )}
      </section>
    </div>
  );
}

function BackLink({ id, billId }: { id: string; billId: string }) {
  return (
    <Link
      href={`/contracts/${id}/bills/${billId}`}
      className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
    >
      <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
      Bill
    </Link>
  );
}

function Summary({
  label,
  value,
  mono,
  small,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wider text-slate-500 font-medium">
        {label}
      </dt>
      <dd
        className={
          "mt-0.5 " +
          (small ? "text-slate-600 " : "text-slate-900 ") +
          (mono ? "font-mono" : "")
        }
      >
        {value}
      </dd>
    </div>
  );
}

function formatDateTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}
