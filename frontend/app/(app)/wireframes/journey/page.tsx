"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Circle,
  Dot,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import {
  FIRST_RUN_STEPS,
  JOURNEY_CONTRACTS,
  type JourneyContract,
  type Stage,
  type StageState,
} from "@/lib/wireframes/journey";
import { SectionHeading } from "@/components/wireframes/Primitives";

const STAGE_ICON: Record<StageState, React.ReactNode> = {
  done: <Check className="h-3 w-3" strokeWidth={2.5} />,
  current: <Dot className="h-3 w-3" strokeWidth={3} />,
  blocked: <AlertTriangle className="h-3 w-3" strokeWidth={2.5} />,
  todo: <Circle className="h-2 w-2" strokeWidth={3} />,
};

const STAGE_STYLE: Record<StageState, { chip: string; badge: string; text: string }> = {
  done: {
    chip: "border-green-200 bg-green-50",
    badge: "bg-green-600 text-white",
    text: "text-green-900",
  },
  current: {
    chip: "border-amber-300 bg-amber-50 ring-1 ring-amber-200",
    badge: "bg-amber-600 text-white",
    text: "text-amber-950",
  },
  blocked: {
    chip: "border-red-200 bg-red-50",
    badge: "bg-red-600 text-white",
    text: "text-red-900",
  },
  todo: {
    chip: "border-slate-200 bg-white",
    badge: "border border-slate-300 bg-white text-slate-400",
    text: "text-slate-500",
  },
};

function StageChip({ stage }: { stage: Stage }) {
  const style = STAGE_STYLE[stage.state];
  return (
    <li className={cn("rounded-lg border px-3 py-2.5", style.chip)}>
      <div className="flex items-start gap-2">
        <span
          className={cn(
            "mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full",
            style.badge,
          )}
        >
          {STAGE_ICON[stage.state]}
        </span>
        <div className="min-w-0">
          <p className={cn("text-[12px] font-medium", style.text)}>{stage.label}</p>
          <p className="mt-0.5 text-[11px] leading-4 text-slate-500">{stage.blurb}</p>
          {stage.blockedReason && (
            <p className="mt-1 text-[11px] leading-4 font-medium text-red-800">
              {stage.blockedReason}
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

function ContractJourney({ contract }: { contract: JourneyContract }) {
  return (
    <div className="space-y-3">
      {/* The one thing to do next, before any navigation. */}
      <div
        className={cn(
          "rounded-xl border-2 px-4 py-3.5",
          contract.blockedNote
            ? "border-red-300 bg-red-50"
            : "border-amber-300 bg-amber-50",
        )}
      >
        <p className="text-[10.5px] font-medium uppercase tracking-wider text-slate-600">
          Do this next
        </p>
        <p className="mt-1 text-[14px] font-medium leading-6 text-slate-900">
          {contract.nextAction}
        </p>
        <div className="mt-2.5">
          <Button variant="primary">
            {contract.nextActionLabel}
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} />
          </Button>
        </div>
      </div>

      {contract.phases.map((phase) => (
        <section key={phase.id} className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-[13px] font-semibold text-slate-900">{phase.title}</h3>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
              {phase.id === "billing" ? (
                <RefreshCw className="h-3 w-3" strokeWidth={1.75} />
              ) : (
                <Sparkles className="h-3 w-3" strokeWidth={1.75} />
              )}
              {phase.cadence}
            </span>
          </div>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {phase.stages.map((stage) => (
              <StageChip key={stage.id} stage={stage} />
            ))}
          </ul>
        </section>
      ))}

      {contract.blockedNote && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-5 text-slate-600">
          <span className="font-medium text-slate-800">Why this matters: </span>
          {contract.blockedNote}
        </p>
      )}
    </div>
  );
}

export default function JourneyWireframePage() {
  const [contractId, setContractId] = useState(JOURNEY_CONTRACTS[0].id);
  const [empty, setEmpty] = useState(false);

  const contract =
    JOURNEY_CONTRACTS.find((c) => c.id === contractId) ?? JOURNEY_CONTRACTS[0];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">
          Guided journey — proposed
        </h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-6 text-slate-500">
          A response to the one thing every reviewer has said: <em>&ldquo;I don&rsquo;t
          understand where to start, or what to do next.&rdquo;</em> Three changes — a real
          landing page, stage state derived from the contract&rsquo;s own data rather than a
          fixed ribbon, and setup separated from the part that repeats.
        </p>
      </header>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <p className="text-[12px] font-medium text-slate-700">What is wrong today</p>
        <ul className="mt-1.5 space-y-1 text-[12px] leading-5 text-slate-600">
          <li>
            · There is no landing page. Signing in drops you on a contracts list with no
            starting point.
          </li>
          <li>
            · The six-step ribbon shows the same labels on every page. It never says which step
            you are on, which are done, or which is blocked — and it is missing from the two
            pages people actually land on.
          </li>
          <li>
            · It reads as one linear pass. Setup happens once; the bill cycle repeats. Nothing
            communicates that, so people finish a bill and cannot tell whether they are done.
          </li>
        </ul>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-[11px] text-slate-500">
          <span>Fixture</span>
          <select
            value={contractId}
            disabled={empty}
            onChange={(e) => setContractId(e.target.value)}
            className="rounded border border-slate-200 bg-white px-2 py-1 text-[12px] text-slate-800 disabled:bg-slate-100"
          >
            {JOURNEY_CONTRACTS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.tenderNumber} — {c.contractorName}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-[12px] text-slate-600">
          <input
            type="checkbox"
            checked={empty}
            onChange={(e) => setEmpty(e.target.checked)}
          />
          Show the empty tenant (first sign-in)
        </label>
      </div>

      {empty ? (
        <div className="space-y-4">
          <SectionHeading
            title="First sign-in"
            description="What a brand-new tenant sees instead of an empty table. Three steps, one of them already possible, and an explicit statement that step one does not repeat."
          />
          <div className="rounded-xl border-2 border-amber-300 bg-amber-50 px-5 py-5">
            <p className="text-[16px] font-semibold text-slate-900">
              Start by adding your first contract
            </p>
            <p className="mt-1 max-w-2xl text-[13px] leading-6 text-slate-700">
              You will need the LOA or tender number. Everything else — schedules, the BOQ, the
              agreement PDF — can be added afterwards.
            </p>
            <div className="mt-3">
              <Button variant="primary">
                Add your first contract
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} />
              </Button>
            </div>
          </div>

          <ol className="grid gap-2 sm:grid-cols-3">
            {FIRST_RUN_STEPS.map((step, i) => (
              <li key={step.label} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
                <span className="grid h-5 w-5 place-items-center rounded-full border border-slate-300 text-[10px] text-slate-500">
                  {i + 1}
                </span>
                <p className="mt-1.5 text-[13px] font-medium text-slate-900">{step.label}</p>
                <p className="mt-0.5 text-[11px] leading-4 text-slate-500">{step.blurb}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <ContractJourney contract={contract} />
      )}

      <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p className="text-[12px] font-medium text-slate-700">
          What this needs in production
        </p>
        <ul className="mt-1.5 space-y-1 text-[12px] leading-5 text-slate-600">
          <li>
            · A derivation of stage state from data already on the contract — schedule count,
            item count, extra-item decisions, bill and run status. No new columns.
          </li>
          <li>
            · One index-coverage check per bill quarter, which is what turns the most common
            dead end into a named blocker with a link.
          </li>
          <li>· A landing route, currently absent from `NAV_ITEMS`.</li>
        </ul>
      </div>
    </div>
  );
}
