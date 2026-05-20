"use client";

import { use, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Pencil } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ContractForm } from "@/components/contracts/ContractForm";
import { ScheduleForm } from "@/components/contracts/ScheduleForm";
import { ItemsGrid } from "@/components/contracts/ItemsGrid";
import type { z } from "zod";
import { contractCreateSchema, type ContractFormValues } from "@/lib/contracts-schema";

type ContractFormInput = z.input<typeof contractCreateSchema>;

interface Contract {
  id: string;
  tender_number: string;
  agreement_number: string | null;
  loa_number: string | null;
  loa_date: string | null;
  contractor_name: string;
  work_description: string | null;
  contract_value: string | number | null;
  bid_amount: string | number | null;
  start_date: string | null;
  completion_date: string | null;
  base_month: string;
  gst_mode: string;
  pvc_applicable: boolean;
  overall_rebate: string | number | null;
  railway_zone: string;
  status: string;
}

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
  bid_discount_pct: string | number;
}

type Tab = "overview" | "schedules" | "items";

function statusVariant(s: string): "draft" | "approved" | "superseded" | "blocked" {
  if (s === "Approved") return "approved";
  if (s === "Superseded") return "superseded";
  if (s === "ExceptionFlagged") return "blocked";
  return "draft";
}

function toFormDefaults(c: Contract): Partial<ContractFormInput> {
  return {
    tender_number: c.tender_number,
    agreement_number: c.agreement_number ?? undefined,
    loa_number: c.loa_number ?? undefined,
    loa_date: c.loa_date ?? undefined,
    contractor_name: c.contractor_name,
    work_description: c.work_description ?? undefined,
    railway_zone: c.railway_zone,
    base_month: c.base_month?.slice(0, 7),  // API returns YYYY-MM-DD; month input needs YYYY-MM
    start_date: c.start_date ?? undefined,
    completion_date: c.completion_date ?? undefined,
    contract_value:
      c.contract_value === null ? undefined : Number(c.contract_value),
    bid_amount: c.bid_amount === null ? undefined : Number(c.bid_amount),
    gst_mode: (c.gst_mode === "inclusive" ? "inclusive" : "exclusive") as
      | "exclusive"
      | "inclusive",
    pvc_applicable: c.pvc_applicable,
    overall_rebate:
      c.overall_rebate === null ? undefined : Number(c.overall_rebate),
  };
}

export default function ContractDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") as Tab) || "overview";

  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery<Contract>({
    queryKey: ["contract", id],
    queryFn: () => apiFetch<Contract>(`/api/contracts/${id}`),
  });

  // Schedules query is enabled on both Schedules and Items tabs (Items needs
  // the list for its schedule selector). The page header link to extra-items
  // also depends on this.
  const schedulesEnabled = tab === "schedules" || tab === "items";
  const schedulesQuery = useQuery<Schedule[]>({
    queryKey: ["contract-schedules", id],
    queryFn: () => apiFetch<Schedule[]>(`/api/contracts/${id}/schedules`),
    enabled: schedulesEnabled,
  });

  const hasExtraNS = useMemo(
    () => (schedulesQuery.data ?? []).some((s) => s.schedule_type === "ExtraNS"),
    [schedulesQuery.data],
  );

  function setTab(next: Tab) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "overview") params.delete("tab");
    else params.set("tab", next);
    router.replace(`?${params.toString()}`, { scroll: false });
  }

  if (isLoading) {
    return (
      <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
    );
  }

  if (isError || !data) {
    const msg =
      error instanceof ApiError && error.status === 404
        ? "Contract not found"
        : error instanceof Error
          ? error.message
          : "Failed to load contract";
    return (
      <div className="space-y-4">
        <Link
          href="/contracts"
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Contracts
        </Link>
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {msg}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link
          href="/contracts"
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Contracts
        </Link>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
                {data.tender_number}
              </h1>
              <Badge variant={statusVariant(data.status)}>{data.status}</Badge>
            </div>
            <p className="text-[13px] text-slate-500 mt-1">
              {data.contractor_name} · {data.railway_zone} · base {data.base_month}
            </p>
          </div>
          {hasExtraNS && (
            <Link
              href={`/contracts/${id}/extra-items`}
              className="text-[12px] text-amber-700 hover:text-amber-900 underline-offset-2 hover:underline"
            >
              Manage extra-item decisions →
            </Link>
          )}
        </div>
      </header>

      <TabBar tab={tab} setTab={setTab} />

      {tab === "overview" && (
        <OverviewTab
          contract={data}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ["contract", id] })}
        />
      )}
      {tab === "schedules" && (
        <SchedulesTab
          contractId={id}
          schedules={schedulesQuery.data ?? []}
          isLoading={schedulesQuery.isLoading}
          onCreated={() =>
            queryClient.invalidateQueries({
              queryKey: ["contract-schedules", id],
            })
          }
        />
      )}
      {tab === "items" && (
        <ItemsTab
          schedules={schedulesQuery.data ?? []}
          isLoading={schedulesQuery.isLoading}
        />
      )}
    </div>
  );
}

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "schedules", label: "Schedules" },
    { id: "items", label: "Items" },
  ];
  return (
    <div className="border-b border-slate-200">
      <nav className="-mb-px flex gap-6">
        {tabs.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={
                "py-2 text-[13px] border-b-2 transition-colors " +
                (active
                  ? "border-amber-600 text-slate-900 font-medium"
                  : "border-transparent text-slate-500 hover:text-slate-800")
              }
            >
              {t.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function OverviewTab({
  contract,
  onSaved,
}: {
  contract: Contract;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [serverFieldError, setServerFieldError] = useState<
    { field: keyof ContractFormValues; message: string } | null
  >(null);

  const save = useMutation({
    mutationFn: (values: ContractFormValues) =>
      apiFetch<Contract>(`/api/contracts/${contract.id}`, {
        method: "PUT",
        body: values,
      }),
    onSuccess: () => {
      onSaved();
      setEditing(false);
      setServerFieldError(null);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        setServerFieldError({
          field: "agreement_number",
          message: err.message || "Agreement number already in use",
        });
      }
    },
  });

  if (editing) {
    return (
      <ContractForm
        defaultValues={toFormDefaults(contract)}
        onSubmit={async (values) => {
          await save.mutateAsync(values);
        }}
        onCancel={() => {
          setEditing(false);
          setServerFieldError(null);
        }}
        submitLabel="Save changes"
        serverFieldError={serverFieldError}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
          <Pencil className="h-3.5 w-3.5" strokeWidth={1.75} />
          Edit
        </Button>
      </div>
      <dl className="grid grid-cols-2 gap-x-8 gap-y-3 max-w-3xl text-[13px]">
        <Field label="Tender number" value={contract.tender_number} />
        <Field label="Agreement number" value={contract.agreement_number} />
        <Field label="LOA number" value={contract.loa_number} />
        <Field label="LOA date" value={contract.loa_date} />
        <Field label="Contractor" value={contract.contractor_name} />
        <Field label="Railway zone" value={contract.railway_zone} />
        <Field label="Base month" value={contract.base_month} />
        <Field label="Start date" value={contract.start_date} />
        <Field label="Completion date" value={contract.completion_date} />
        <Field label="Contract value" value={contract.contract_value} />
        <Field label="Bid amount" value={contract.bid_amount} />
        <Field label="GST mode" value={contract.gst_mode} />
        <Field
          label="PVC applicable"
          value={contract.pvc_applicable ? "Yes" : "No"}
        />
        <Field
          label="Overall rebate"
          value={
            contract.overall_rebate === null
              ? null
              : `${contract.overall_rebate} (decimal)`
          }
        />
        <Field
          label="Work description"
          value={contract.work_description}
          full
        />
      </dl>
    </div>
  );
}

function Field({
  label,
  value,
  full,
}: {
  label: string;
  value: string | number | null | undefined;
  full?: boolean;
}) {
  return (
    <div className={full ? "col-span-2" : ""}>
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

function SchedulesTab({
  contractId,
  schedules,
  isLoading,
  onCreated,
}: {
  contractId: string;
  schedules: Schedule[];
  isLoading: boolean;
  onCreated: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div
          className="px-5 py-3 grid grid-cols-[1fr_120px_140px] gap-4 text-[11px]
                     uppercase tracking-wider text-slate-500 font-medium
                     border-b border-slate-200 bg-slate-50"
        >
          <div>Name</div>
          <div>Type</div>
          <div className="text-right">Bid discount</div>
        </div>
        {isLoading && (
          <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
        )}
        {!isLoading && schedules.length === 0 && (
          <div className="px-5 py-6 text-[13px] text-slate-400">
            No schedules yet. Add the first one below.
          </div>
        )}
        {schedules.map((s, i) => (
          <div
            key={s.id}
            className={
              "px-5 h-11 grid grid-cols-[1fr_120px_140px] gap-4 items-center text-[13px] " +
              (i < schedules.length - 1 ? "border-b border-slate-100" : "")
            }
          >
            <div className="font-medium text-slate-900">{s.name}</div>
            <div>
              <Badge variant="neutral">{s.schedule_type}</Badge>
            </div>
            <div className="text-right font-mono text-[12px] text-slate-600">
              {Number(s.bid_discount_pct).toFixed(4)}
            </div>
          </div>
        ))}
      </div>

      <div className="border border-slate-200 rounded-xl p-5 bg-white">
        <h3 className="text-[14px] font-medium text-slate-900 mb-3">
          Add schedule
        </h3>
        <ScheduleForm contractId={contractId} onCreated={onCreated} />
      </div>
    </div>
  );
}

function ItemsTab({
  schedules,
  isLoading,
}: {
  schedules: Schedule[];
  isLoading: boolean;
}) {
  const [selectedId, setSelectedId] = useState<string>("");

  if (isLoading) {
    return <div className="text-[13px] text-slate-400">Loading schedules…</div>;
  }
  if (schedules.length === 0) {
    return (
      <div className="text-[13px] text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-5 py-4">
        Add a schedule first — items live under a schedule.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <label className="text-[12px] text-slate-600">Schedule:</label>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="h-8 rounded-md border border-slate-200 bg-white px-2.5 text-[13px]"
        >
          <option value="">— Select —</option>
          {schedules.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.schedule_type})
            </option>
          ))}
        </select>
      </div>
      {selectedId && <ItemsGrid scheduleId={selectedId} />}
    </div>
  );
}
