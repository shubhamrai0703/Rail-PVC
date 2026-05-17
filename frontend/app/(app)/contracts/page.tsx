"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, PlusCircle } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";

interface Contract {
  id: string;
  tender_number: string;
  contractor_name: string;
  base_month: string;
  railway_zone: string;
  status: string;
}

function statusVariant(status: string): "draft" | "approved" | "superseded" | "blocked" {
  if (status === "Approved") return "approved";
  if (status === "Superseded") return "superseded";
  if (status === "ExceptionFlagged") return "blocked";
  return "draft";
}

function useContracts() {
  return useQuery<Contract[]>({
    queryKey: ["contracts"],
    queryFn: () => apiFetch<Contract[]>("/api/contracts"),
  });
}

export default function ContractsPage() {
  const { data: contracts, isLoading, isError, error } = useContracts();

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">Contracts</h1>
          <p className="text-[13px] text-slate-500 mt-1">
            Set up a contract once, then bill against it as MBs come in.
          </p>
        </div>
        <Button variant="primary" disabled title="POST /api/contracts — coming in Phase 5">
          <PlusCircle className="h-3.5 w-3.5" strokeWidth={1.75} />
          New contract
        </Button>
      </header>

      {isLoading && (
        <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
      )}

      {isError && (
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {error instanceof Error ? error.message : "Failed to load contracts"}
        </div>
      )}

      {!isLoading && !isError && contracts?.length === 0 && (
        <EmptyState
          icon={<FileText className="h-4 w-4" strokeWidth={1.75} />}
          title="No contracts yet"
          description="Start with an LOA / tender number. You can upload the agreement after."
          action={
            <Button variant="primary" disabled>
              Add your first contract
            </Button>
          }
        />
      )}

      {contracts && contracts.length > 0 && (
        <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          {/* Header row */}
          <div className="px-5 py-3 grid grid-cols-[1fr_160px_120px_100px_100px] gap-4
                          text-[11px] uppercase tracking-wider text-slate-500 font-medium
                          border-b border-slate-200 bg-slate-50">
            <div>Tender / Contractor</div>
            <div>Base month</div>
            <div>Zone</div>
            <div>Status</div>
            <div />
          </div>

          {contracts.map((c, i) => (
            <div
              key={c.id}
              className={`px-5 h-12 grid grid-cols-[1fr_160px_120px_100px_100px] gap-4
                          items-center text-[13px]
                          ${i < contracts.length - 1 ? "border-b border-slate-100" : ""}`}
            >
              <div className="min-w-0">
                <div className="font-medium text-slate-900 truncate">{c.tender_number}</div>
                <div className="text-[12px] text-slate-500 truncate">{c.contractor_name}</div>
              </div>
              <div className="text-slate-600 font-mono text-[12px]">{c.base_month}</div>
              <div className="text-slate-600 font-mono text-[12px]">{c.railway_zone}</div>
              <div>
                <Badge variant={statusVariant(c.status)}>{c.status}</Badge>
              </div>
              <div className="flex justify-end">
                <Button variant="ghost" size="sm" disabled title="Contract detail — Phase 5">
                  View
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
