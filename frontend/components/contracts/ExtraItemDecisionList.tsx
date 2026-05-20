"use client";

import { useMemo, useState } from "react";
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
}: {
  contractId: string;
  schedules: Schedule[];
  decisions: Decision[];
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
    // REVIEW.md M-5 — snapshot the keys we are saving NOW. A toggle that
    // arrives while the request is in flight will add a key to `pending`;
    // on success we must clear only the keys in `savedKeys`, not blow away
    // the new toggle. Previously `setPending({})` ate that user action
    // silently.
    const entries = Object.entries(pending);
    if (entries.length === 0) return;
    const savedKeys = new Set(entries.map(([k]) => k));
    setSaving(true);
    try {
      await Promise.all(
        entries.map(([item_id, v]) =>
          apiFetch(`/api/contracts/${contractId}/extra-item-decisions`, {
            method: "POST",
            body: { item_id, eligible: eligibleFor(v) },
            silent: true,
          }),
        ),
      );
      setPending((prev) =>
        Object.fromEntries(
          Object.entries(prev).filter(([k]) => !savedKeys.has(k)),
        ),
      );
      toast.success(
        `Saved ${entries.length} decision${entries.length === 1 ? "" : "s"}`,
      );
      queryClient.invalidateQueries({
        queryKey: ["extra-item-decisions", contractId],
      });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Failed to save decisions";
      toast.error("Save failed", { description: msg });
    } finally {
      setSaving(false);
    }
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

      <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div
          className="px-5 py-3 grid grid-cols-[120px_1fr_160px_240px] gap-4 text-[11px]
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
                "px-5 h-12 grid grid-cols-[120px_1fr_160px_240px] gap-4 items-center text-[13px] " +
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
