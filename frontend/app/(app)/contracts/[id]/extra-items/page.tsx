"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api/client";
import { ExtraItemDecisionList } from "@/components/contracts/ExtraItemDecisionList";
import {
  JourneyGuide,
  PageGuidance,
} from "@/components/help/FirstUserHelp";

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
}

interface Decision {
  id: string;
  item_id: string;
  eligible: boolean | null;
  notes: string | null;
}

export default function ExtraItemsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [decisionStatus, setDecisionStatus] = useState({
    total: 0,
    allDecided: false,
  });

  const schedules = useQuery<Schedule[]>({
    queryKey: ["contract-schedules", id],
    queryFn: () => apiFetch<Schedule[]>(`/api/contracts/${id}/schedules`),
  });

  const decisions = useQuery<Decision[]>({
    queryKey: ["extra-item-decisions", id],
    queryFn: () =>
      apiFetch<Decision[]>(`/api/contracts/${id}/extra-item-decisions`),
  });

  const isLoading = schedules.isLoading || decisions.isLoading;

  if (schedules.isError || decisions.isError) {
    const err = schedules.error ?? decisions.error;
    const msg =
      err instanceof ApiError && err.status === 404
        ? "Contract not found"
        : err instanceof Error
          ? err.message
          : "Failed to load";
    return (
      <div className="space-y-4">
        <Link
          href={`/contracts/${id}`}
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Back to contract
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
          href={`/contracts/${id}`}
          className="inline-flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Back to contract
        </Link>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Extra-item decisions
        </h1>
        <p className="text-[13px] text-slate-500">
          Each ExtraNS item needs an explicit eligibility verdict before a PVC
          run can proceed. Undecided rows block the engine at run time.
        </p>
      </header>

      <JourneyGuide stage="decisions" />
      <PageGuidance
        title="Decide how ExtraNS items affect PVC"
        next={
          decisionStatus.allDecided ? (
            <Link
              href={`/contracts/${id}/bills`}
              className="font-medium text-amber-700 hover:text-amber-800 hover:underline"
            >
              Continue to Bills →
            </Link>
          ) : (
            "Create the bill after every extra item has an explicit decision."
          )
        }
      >
        Choose Yes when an ExtraNS item is eligible for PVC and No when it is
        excluded. Undecided items block calculation. A decision affects W only
        when that item is present in the bill lines used by the run.
      </PageGuidance>

      {isLoading ? (
        <div className="text-[13px] text-slate-400 py-12 text-center">
          Loading…
        </div>
      ) : (
        <ExtraItemDecisionList
          contractId={id}
          schedules={schedules.data ?? []}
          decisions={decisions.data ?? []}
          onStatusChange={setDecisionStatus}
        />
      )}
    </div>
  );
}
