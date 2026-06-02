"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { LineChart } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { humanizeSeries } from "@/lib/indices";

interface IndexSeries {
  id: string;
  name: string;
  source_publication: string;
}

function useIndexSeries() {
  return useQuery<IndexSeries[]>({
    queryKey: ["indices"],
    queryFn: () => apiFetch<IndexSeries[]>("/api/indices"),
  });
}

export default function IndicesPage() {
  const { data: series, isLoading, isError, error } = useIndexSeries();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Index Manager
        </h1>
        <p className="text-[13px] text-slate-500 mt-1">
          RBI WPI All-Commodities and JPC steel series. Open a series to review its
          observations and add the current month.
        </p>
      </header>

      {isLoading && (
        <div className="text-[13px] text-slate-400 py-12 text-center">Loading…</div>
      )}

      {isError && (
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-xl px-5 py-4">
          {error instanceof Error ? error.message : "Failed to load index series"}
        </div>
      )}

      {!isLoading && !isError && series?.length === 0 && (
        <EmptyState
          icon={<LineChart className="h-4 w-4" strokeWidth={1.75} />}
          title="No index series yet"
          description="Run the index seeds to load RBI WPI + JPC steel series."
        />
      )}

      {series && series.length > 0 && (
        <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div className="px-5 py-3 grid grid-cols-[1fr_120px_100px] gap-4
                          text-[11px] uppercase tracking-wider text-slate-500 font-medium
                          border-b border-slate-200 bg-slate-50">
            <div>Series</div>
            <div>Source</div>
            <div />
          </div>

          {series.map((s, i) => (
            <Link
              key={s.id}
              href={`/indices/${s.name}`}
              className={`px-5 h-12 grid grid-cols-[1fr_120px_100px] gap-4 items-center
                          text-[13px] hover:bg-slate-50 transition-colors
                          ${i < series.length - 1 ? "border-b border-slate-100" : ""}`}
            >
              <div className="font-medium text-slate-900">{humanizeSeries(s.name)}</div>
              <div>
                <Badge variant="draft">{s.source_publication}</Badge>
              </div>
              <div className="flex justify-end text-[12px] text-slate-400">View →</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
