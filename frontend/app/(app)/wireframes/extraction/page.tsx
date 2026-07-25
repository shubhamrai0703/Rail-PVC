"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { NumberedStageGuide } from "@/components/help/FirstUserHelp";
import { CONTRACT_FIXTURES } from "@/lib/wireframes/extraction";
import { Step1Upload } from "@/components/wireframes/extraction/Step1Upload";
import { Step2Pricing } from "@/components/wireframes/extraction/Step2Pricing";
import { Step3Items } from "@/components/wireframes/extraction/Step3Items";
import { Step4Bills } from "@/components/wireframes/extraction/Step4Bills";
import { Step5Reconcile } from "@/components/wireframes/extraction/Step5Reconcile";

const STEPS = [
  { id: "upload", label: "Upload & classify" },
  { id: "pricing", label: "Contract & pricing" },
  { id: "items", label: "Items" },
  { id: "bills", label: "Bill bundle" },
  { id: "reconcile", label: "Reconcile" },
] as const;

export default function ExtractionWireframePage() {
  const [stepIdx, setStepIdx] = useState(0);
  const [contractId, setContractId] = useState(CONTRACT_FIXTURES[0].id);

  const contract =
    CONTRACT_FIXTURES.find((c) => c.id === contractId) ?? CONTRACT_FIXTURES[0];
  const step = STEPS[stepIdx];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Document-assisted prefill
        </h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-6 text-slate-500">
          Upload the tender bundle, and we propose values instead of asking you to type them.
          Nothing reaches the contract, schedules, items or bills until you confirm it — a
          silently wrong prefill on a Railways submission is worse than no prefill at all.
        </p>
      </header>

      <nav aria-label="Extraction steps" className="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-500">
          Extraction steps
        </p>
        <NumberedStageGuide
          ariaLabel="Extraction steps"
          items={STEPS}
          currentId={step.id}
          className="sm:grid-cols-3 xl:grid-cols-5"
        />
      </nav>

      <div className="min-h-[60vh]">
        {step.id === "upload" && <Step1Upload />}
        {step.id === "pricing" && (
          <Step2Pricing contract={contract} onSelectContract={setContractId} />
        )}
        {step.id === "items" && <Step3Items />}
        {step.id === "bills" && <Step4Bills />}
        {step.id === "reconcile" && <Step5Reconcile />}
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 pt-4">
        <Button
          variant="secondary"
          disabled={stepIdx === 0}
          onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
        >
          <ChevronLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
          Back
        </Button>
        <span className="text-[12px] text-slate-500">
          Step {stepIdx + 1} of {STEPS.length} — {step.label}
        </span>
        <Button
          variant="primary"
          disabled={stepIdx === STEPS.length - 1}
          onClick={() => setStepIdx((i) => Math.min(STEPS.length - 1, i + 1))}
        >
          Next
          <ChevronRight className="h-3.5 w-3.5" strokeWidth={1.75} />
        </Button>
      </div>
    </div>
  );
}
