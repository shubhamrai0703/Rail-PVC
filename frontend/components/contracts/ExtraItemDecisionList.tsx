"use client";

import { useEffect, useMemo, useState } from "react";
import { useQueries, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";

interface Schedule {
  id: string;
  name: string;
  schedule_type: "DSR" | "NS" | "ExtraNS";
}

interface ContractItem {
  id: string;
  item_code: string;
  description: string;
}

interface Decision {
  id: string;
  item_id: string;
  eligible: boolean | null;
  notes: string | null;
}

type Verdict = "yes" | "no" | "undecided";

type Row = {
  item_id: string;
  item_code: string;
  description: string;
  schedule_name: string;
  serverVerdict: Verdict;
};

function verdictOf(eligible: boolean | null): Verdict {
  if (eligible === true) return "yes";
  if (eligible === false) return "no";
  return "undecided";
}

function eligibleFor(v: Verdict): boolean | null {
  if (v === "yes") return true;
  if (v === "no") return false;
  return null;
}

export function ExtraItemDecisionList({
  contractId,
  schedules,
  decisions,
  onStatusChange,
}: {
  contractId: string;
  schedules: Schedule[];
  decisions: Decision[];
  /** Reports whether every ExtraNS item has an explicit decision, so the
   * parent page can offer forward navigation once true. */
  onStatusChange?: (status: { total: number; allDecided: boolean }) => void;
}) {
  const queryClient = useQueryClient();

  const extraNsSchedules = useMemo(
    () => schedules.filter((s) => s.schedule_type === "ExtraNS"),
    [schedules],
  );

  const itemQueries = useQueries({
    queries: extraNsSchedules.map((s) => ({
      queryKey: ["schedule-items", s.id],
      queryFn: () => apiFetch<ContractItem[]>(`/api/schedules/${s.id}/items`),
    })),
  });

  const decisionsByItem = useMemo(() => {
    const m = new Map<string, Decision>();
    for (const d of decisions) m.set(d.item_id, d);
    return m;
  }, [decisions]);

  // P5-F5 — local staged map of pending verdicts, keyed by item_id. Empty
  // until the user toggles a row. Cleared after a successful save.
  const [pending, setPending] = useState<Record<string, Verdict>>({});
  const [saving, setSaving] = useState(false);

  const rows: Row[] = useMemo(() => {
    const out: Row[] = [];
    extraNsSchedules.forEach((s, i) => {
      const items = itemQueries[i]?.data ?? [];
      for (const item of items) {
        const d = decisionsByItem.get(item.id);
        out.push({
          item_id: item.id,
          item_code: item.item_code,
          description: item.description,
          schedule_name: s.name,
          serverVerdict: verdictOf(d ? d.eligible : null),
        });
      }
    });
    return out;
  }, [extraNsSchedules, itemQueries, decisionsByItem]);

  const isLoading = itemQueries.some((q) => q.isLoading);

  // Effective verdict per row = pending change if any, otherwise server state.
  // The undecided-count banner reads from this merged view so the user sees
  // what the contract will look like *after* saving.
  const effectiveVerdict = (r: Row): Verdict =>
    pending[r.item_id] ?? r.serverVerdict;

  const undecidedCount = rows.filter(
    (r) => effectiveVerdict(r) === "undecided",
  ).length;
  const pendingCount = Object.keys(pending).length;

  // Only the *saved* state (server verdicts, ignoring unsaved pending
  // toggles) should unlock forward navigation — an unsaved "Yes" shouldn't
  // let the user click through to Bills before it's actually persisted.
  useEffect(() => {
    onStatusChange?.({
      total: rows.length,
      allDecided:
        rows.length > 0 && rows.every((r) => r.serverVerdict !== "undecided"),
    });
  }, [rows, onStatusChange]);

  function toggle(itemId: string, opt: Verdict, serverVerdict: Verdict) {
    setPending((prev) => {
      const next = { ...prev };
      // If the user reverts to the server's existing value, drop the pending
      // entry so the row no longer shows as unsaved.
      if (opt === serverVerdict) {
        delete next[itemId];
      } else {
        next[itemId] = opt;
      }
      return next;
    });
  }

  async function saveChanges() {
    // REVIEW.md M-5 — snapshot the keys saved NOW so a mid-flight toggle
    // isn't blown away on success.
    // REVIEW.md L-1 — `Promise.allSettled`, not `Promise.all`. With `all`,
    // the first rejection short-circuits the await but the other POSTs have
    // already committed server-side. On the catch path `pending` stayed
    // untouched, leaving the fulfilled rows showing as unsaved while the
    // server held the new value. Now we drop only the fulfilled keys; failed
    // keys stay in `pending` for the user to retry (POST is idempotent).
    const entries = Object.entries(pending);
    if (entries.length === 0) return;
    setSaving(true);
    const results = await Promise.allSettled(
      entries.map(([item_id, v]) =>
        apiFetch(`/api/contracts/${contractId}/extra-item-decisions`, {
          method: "POST",
          body: { item_id, eligible: eligibleFor(v) },
          silent: true,
        }),
      ),
    );
    const fulfilledKeys = new Set(
      results
        .map((r, i) => (r.status === "fulfilled" ? entries[i][0] : null))
        .filter((k): k is string => k !== null),
    );
    const failures = results.filter((r) => r.status === "rejected");
    if (fulfilledKeys.size > 0) {
      setPending((prev) =>
        Object.fromEntries(
          Object.entries(prev).filter(([k]) => !fulfilledKeys.has(k)),
        ),
      );
      queryClient.invalidateQueries({
        queryKey: ["extra-item-decisions", contractId],
      });
    }
    if (failures.length === 0) {
      toast.success(
        `Saved ${fulfilledKeys.size} decision${fulfilledKeys.size === 1 ? "" : "s"}`,
      );
    } else {
      const firstReason = (failures[0] as PromiseRejectedResult).reason;
      const msg =
        firstReason instanceof ApiError
          ? firstReason.message
          : "Failed to save decisions";
      toast.error(
        `${failures.length} of ${entries.length} failed to save`,
        { description: msg },
      );
    }
    setSaving(false);
  }

  return (
    <div className="space-y-4">
      {rows.length > 0 &&
        (undecidedCount === 0 ? (
          <div className="text-[13px] text-green-800 bg-green-50 border border-green-200 rounded-lg px-4 py-2.5">
            All extra items decided — PVC run can proceed.
          </div>
        ) : (
          <div className="text-[13px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5">
            {undecidedCount} item(s) undecided — PVC run will be blocked until
            all are decided.
          </div>
        ))}

      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={pendingCount === 0 || saving}
          onClick={saveChanges}
        >
          {saving
            ? "Saving…"
            : pendingCount > 0
              ? `Save changes (${pendingCount})`
              : "Save changes"}
        </Button>
        {pendingCount > 0 && !saving && (
          <span className="text-[12px] text-amber-700">
            {pendingCount} unsaved change{pendingCount === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <div
          className="grid min-w-[760px] grid-cols-[120px_1fr_160px_240px] gap-4 px-5 py-3 text-[11px]
                     uppercase tracking-wider text-slate-500 font-medium
                     border-b border-slate-200 bg-slate-50"
        >
          <div>Code</div>
          <div>Description</div>
          <div>Schedule</div>
          <div>Eligibility</div>
        </div>
        {isLoading && (
          <div className="px-5 py-6 text-[13px] text-slate-400">Loading…</div>
        )}
        {!isLoading && rows.length === 0 && (
          <div className="px-5 py-6 text-[13px] text-slate-400">
            No extra-item rows yet. Add an ExtraNS schedule and items first.
          </div>
        )}
        {rows.map((r, i) => {
          const v = effectiveVerdict(r);
          const isDirty = pending[r.item_id] !== undefined;
          return (
            <div
              key={r.item_id}
              className={
                "grid h-12 min-w-[760px] grid-cols-[120px_1fr_160px_240px] items-center gap-4 px-5 text-[13px] " +
                (i < rows.length - 1 ? "border-b border-slate-100" : "")
              }
            >
              <div className="font-mono text-[12px] text-slate-700">
                {r.item_code}
              </div>
              <div className="text-slate-900 truncate">{r.description}</div>
              <div className="text-slate-600">{r.schedule_name}</div>
              <div className="flex gap-1 items-center">
                {(["yes", "no", "undecided"] as Verdict[]).map((opt) => (
                  <Button
                    key={opt}
                    type="button"
                    size="sm"
                    variant={v === opt ? "primary" : "secondary"}
                    onClick={() => toggle(r.item_id, opt, r.serverVerdict)}
                  >
                    {opt === "yes" ? "Yes" : opt === "no" ? "No" : "Undecided ⚠"}
                  </Button>
                ))}
                {isDirty && (
                  <span
                    title="Unsaved change"
                    aria-label="Unsaved change"
                    className="ml-1 inline-block h-2 w-2 rounded-full bg-amber-500"
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
