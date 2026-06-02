"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { humanizeSeries } from "@/lib/indices";
import { IndexMonthForm } from "@/components/indices/IndexMonthForm";

interface Observation {
  id: string;
  month: string;
  value: string;
  source_ref: string | null;
  revision_flag: boolean;
  revised_at: string | null;
  created_at: string;
}

interface SeriesDetail {
  id: string;
  name: string;
  source_publication: string;
  observations: Observation[];
}

function useSeriesDetail(seriesName: string) {
  return useQuery<SeriesDetail>({
    queryKey: ["indices", seriesName],
    queryFn: () => apiFetch<SeriesDetail>(`/api/indices/${encodeURIComponent(seriesName)}`),
  });
}

function formatMonth(iso: string): string {
  // month comes back as a first-of-month date (e.g. "2026-01-01").
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { year: "numeric", month: "short" });
}

export default function SeriesDetailPage({
  params,
}: {
  params: Promise<{ series: string }>;
}) {
  const { series: seriesName } = use(params);
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useSeriesDetail(seriesName);

  return (
    <div className="space-y-6">
      <Link
        href="/indices"
        className="inline-flex items-center gap-1 text-[13px] text-slate-500 hover:text-slate-900"
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
        Index Manager
      </Link>

      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
            {humanizeSeries(seriesName)}
          </h1>
          {data && (
            <p className="text-[13px] text-slate-500 mt-1">
              {data.source_publication} · {data.observations.length} observation
              {data.observations.length === 1 ? "" : "s"}
            </p>
          )}
        </div>
      </header>

      {isLoading && (
        <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
      )}

      {isError && (
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {error instanceof Error ? error.message : "Failed to load series"}
        </div>
      )}

      {data && (
        <>
          <section className="border border-slate-200 rounded-xl bg-white p-5">
            <h2 className="text-[13px] font-semibold text-slate-900 mb-3">Add month</h2>
            <IndexMonthForm
              seriesName={seriesName}
              onCreated={() =>
                queryClient.invalidateQueries({ queryKey: ["indices", seriesName] })
              }
            />
          </section>

          <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
            <div className="px-5 py-3 grid grid-cols-[140px_1fr_120px] gap-4
                            text-[11px] uppercase tracking-wider text-slate-500 font-medium
                            border-b border-slate-200 bg-slate-50">
              <div>Month</div>
              <div>Value</div>
              <div>Flag</div>
            </div>

            {data.observations.length === 0 && (
              <div className="px-5 py-8 text-center text-[13px] text-slate-400">
                No observations yet.
              </div>
            )}

            {data.observations.map((o, i) => (
              <div
                key={o.id}
                className={`px-5 h-11 grid grid-cols-[140px_1fr_120px] gap-4 items-center text-[13px]
                            ${i < data.observations.length - 1 ? "border-b border-slate-100" : ""}`}
              >
                <div className="font-mono text-[12px] text-slate-600">{formatMonth(o.month)}</div>
                <div className="font-mono text-slate-900">{o.value}</div>
                <div>
                  {o.revision_flag && (
                    <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded px-1.5 py-0.5">
                      revised
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
