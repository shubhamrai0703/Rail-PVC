"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatINR } from "@/lib/format";

/**
 * Contracts placeholder for Phase 4. Real list lands in P4-004 once
 * GET /api/contracts is live on shubham/phase-3.
 *
 * This page also doubles as the visual smoke-test surface: shows the
 * type system, badges, formula bar treatment, and number cell typography.
 */
export default function ContractsPage() {
  const [boom, setBoom] = useState(false);
  if (boom) throw new Error("Smoke-test: thrown render error from contracts page");

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">Contracts</h1>
          <p className="text-[13px] text-slate-500 mt-1">
            Set up a contract once, then bill against it as MBs come in.
          </p>
        </div>
        <Button variant="primary" disabled title="Enabled when POST /api/contracts ships">
          + New contract
        </Button>
      </header>

      <EmptyState
        icon={<FileText className="h-4 w-4" strokeWidth={1.75} />}
        title="No contracts yet"
        description="Start with an LOA / tender number. You can upload the agreement after."
        action={
          <Button variant="primary" disabled>
            + Add your first contract
          </Button>
        }
      />

      {/* ─── Visual smoke-test panel — remove once P4-004 lands ─── */}
      <section className="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div className="text-[12px] uppercase tracking-wider text-slate-500 font-medium">
            Visual smoke-test · remove after P4-004
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="draft">Draft</Badge>
            <Badge variant="approved">Approved · 2026-04-12</Badge>
            <Badge variant="superseded">Superseded by #15</Badge>
            <Badge variant="blocked">Blocked · 2 errors</Badge>
          </div>
        </div>

        <div className="px-5 py-4 grid grid-cols-[1fr_120px_140px] gap-3 text-[10.5px] uppercase tracking-wider text-slate-500 border-b border-slate-100">
          <div>Item</div>
          <div className="text-right">Qty</div>
          <div className="text-right">Amount (₹)</div>
        </div>

        {[
          ["DSR 2.7 — Earthwork excavation", "1,240.00", 846300.5],
          ["Cement (OPC 43)",                "412.00",   203540],
          ["TMT rebar (SL1)",                "186.500",  1106012.2],
          ["Steel angles (SL2)",             "92.300",   562190.45],
        ].map(([name, qty, amt]) => (
          <div
            key={name as string}
            className="px-5 h-9 grid grid-cols-[1fr_120px_140px] gap-3 items-center border-b border-slate-100 text-[13px]"
          >
            <div className="text-slate-700">{name}</div>
            <div className="text-right font-mono tabular-nums text-slate-700">{qty}</div>
            <div className="text-right font-mono tabular-nums text-slate-900">
              {formatINR(amt as number)}
            </div>
          </div>
        ))}

        <div className="px-5 h-10 grid grid-cols-[1fr_120px_140px] gap-3 items-center text-[13px]">
          <div className="font-semibold text-slate-900">PVC total</div>
          <div />
          <div className="text-right font-mono tabular-nums font-semibold text-slate-900">
            {formatINR(76959.55)}
          </div>
        </div>

        {/* Excel-style formula bar — a preview of the pattern we'll use in P6 */}
        <div className="bg-slate-50 border-t border-slate-200 px-5 py-2.5 flex items-center gap-3">
          <div className="font-mono text-[11px] text-slate-500 grid place-items-center h-6 w-7 border border-slate-200 rounded bg-white">
            fx
          </div>
          <div className="font-mono text-[12px] text-slate-700 tabular-nums">
            W <span className="text-slate-400">=</span> OAB
            <span className="text-slate-400"> − </span>Cement
            <span className="text-slate-400"> − </span>Steel<sub>tmt</sub>
            <span className="text-slate-400"> − </span>Steel<sub>angles</sub>
            <span className="text-slate-400"> − </span>…
          </div>
          <div className="ml-auto flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                toast.success("Approved run #14", {
                  description: `${formatINR(76959.55)} · Q2-FY2025-26`,
                })
              }
            >
              Toast: success
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setBoom(true)}>
              Throw error
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
