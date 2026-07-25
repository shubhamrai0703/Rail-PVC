"use client";

import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { formatINRWithSymbol } from "@/lib/format";
import { cn } from "@/lib/cn";
import {
  CONTRACT_FIXTURES,
  RATE_SOURCE_SUGGESTIONS,
  grossOfferValue,
  isBlocking,
  netOfferValue,
  totalAdvertised,
  type ContractFixture,
  type ScheduleFixture,
} from "@/lib/wireframes/extraction";
import {
  FieldRow,
  ManualEntryEscape,
  SchemaGapNote,
  SectionHeading,
  SourceChip,
  parseNumber,
  parseText,
} from "@/components/wireframes/Primitives";
import { useFieldOverrides } from "@/components/wireframes/useFieldOverrides";

function pct(n: number): string {
  return `${n.toFixed(2)} %`;
}

/** One rung of the derivation chain. */
function ChainStep({
  caption,
  children,
  emphasis = false,
}: {
  caption: string;
  children: React.ReactNode;
  emphasis?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2",
        emphasis ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white",
      )}
    >
      <p
        className={cn(
          "text-[10.5px] font-medium uppercase tracking-wider",
          emphasis ? "text-slate-300" : "text-slate-500",
        )}
      >
        {caption}
      </p>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}

function Arrow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 pl-3">
      <ArrowDown className="h-3.5 w-3.5 shrink-0 text-slate-400" strokeWidth={1.75} />
      <span className="text-[11px] text-slate-500">{label}</span>
    </div>
  );
}

function ScheduleCard({
  schedule,
  contractId,
  overrides,
}: {
  schedule: ScheduleFixture;
  contractId: string;
  overrides: ReturnType<typeof useFieldOverrides>;
}) {
  const { effective, confirm, reject, resolve, enterManually, confirmMany } = overrides;
  const k = (field: string) => `${contractId}:${schedule.id}:${field}`;

  const rateSource = effective(k("rateSource"), schedule.rateSource);
  const isExtraItems = effective(k("isExtraItems"), schedule.isExtraItems);
  const basicCost = effective(k("basicCost"), schedule.basicCost);
  const escalation = effective(k("escalationPct"), schedule.escalationPct);
  const advertised = effective(k("advertisedValue"), schedule.advertisedValue);
  const bidPct = effective(k("bidBelowPct"), schedule.bidBelowPct);
  const bidAmount = effective(k("bidAmount"), schedule.bidAmount);

  const all = [
    { key: k("basicCost"), field: basicCost },
    { key: k("advertisedValue"), field: advertised },
    { key: k("bidBelowPct"), field: bidPct },
    { key: k("bidAmount"), field: bidAmount },
  ];
  const acceptable = all.filter((f) => !isBlocking(f.field.state)).map((f) => f.key);
  const blockedCount = all.filter((f) => isBlocking(f.field.state)).length;

  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-[13px] font-semibold text-slate-900">{schedule.name}</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Priced from the {rateSource.value ?? "—"} rate book
          </p>
        </div>
        <Button
          size="sm"
          variant="secondary"
          disabled={acceptable.length === 0}
          onClick={() => confirmMany(acceptable)}
        >
          Accept this whole schedule
        </Button>
      </div>

      {blockedCount > 0 && (
        <p className="mt-2 text-[11px] text-red-700">
          {blockedCount} field{blockedCount === 1 ? "" : "s"} in this schedule cannot be accepted
          in bulk — resolve {blockedCount === 1 ? "it" : "them"} individually below.
        </p>
      )}

      {/* Schedule identity — the two fields the axis split introduces. */}
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5">
          <label
            htmlFor={`${k("rateSource")}-input`}
            className="text-[12px] font-medium text-slate-700"
          >
            Rate source
          </label>
          <input
            id={`${k("rateSource")}-input`}
            list="rate-source-suggestions"
            defaultValue={rateSource.value ?? ""}
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1 font-mono text-[13px] text-slate-900"
          />
          <p className="mt-1 text-[11px] leading-4 text-slate-500">
            Which rate book this schedule prices from. Suggestions only — type any rate book,
            including one we have never seen.
          </p>
          <div className="mt-1">
            <SourceChip source={rateSource.source} />
          </div>
        </div>

        <FieldRow
          label="Contains extra items"
          help="Drives the PVC extra-item eligibility gate. Getting this wrong changes the calculation, so it is never a checkbox you skim past."
          field={isExtraItems}
          highStakes
          format={(v) => (v ? "Yes — items need an eligibility decision" : "No")}
          onConfirm={() => confirm(k("isExtraItems"))}
          onReject={() => reject(k("isExtraItems"))}
          onResolve={(v) => resolve(k("isExtraItems"), v)}
          onEnterManually={(v) => enterManually(k("isExtraItems"), v)}
          choices={[
            { value: true, label: "Yes — needs an eligibility decision" },
            { value: false, label: "No" },
          ]}
        />
      </div>

      {/* The chain, per schedule. */}
      <div className="mt-3 space-y-1.5">
        <ChainStep caption="Basic cost">
          <span className="font-mono text-[14px] tabular-nums text-slate-900">
            {formatINRWithSymbol(basicCost.value)}
          </span>
          <div className="mt-0.5">
            <SourceChip source={basicCost.source} />
          </div>
        </ChainStep>

        <Arrow
          label={
            escalation.value === 0
              ? "escalation At Par — no change"
              : `escalation ${pct(escalation.value ?? 0)} per item`
          }
        />

        <ChainStep caption="Advertised value">
          <span className="font-mono text-[14px] tabular-nums text-slate-900">
            {formatINRWithSymbol(advertised.value)}
          </span>
          <div className="mt-0.5">
            <SourceChip source={advertised.source} />
          </div>
        </ChainStep>

        <Arrow label={`bid ${pct(bidPct.value ?? 0)} below`} />

        <ChainStep caption="Schedule bid amount">
          <span className="font-mono text-[14px] tabular-nums text-slate-900">
            {formatINRWithSymbol(bidAmount.value)}
          </span>
          <div className="mt-0.5">
            <SourceChip source={bidAmount.source} />
          </div>
        </ChainStep>
      </div>

      <div className="mt-3">
        <SchemaGapNote>
          Escalation is printed per item on the tabulation statement ({pct(escalation.value ?? 0)}{" "}
          here) and is what turns basic cost into advertised value. `contract_items` has no column
          for it, so it is proposed and shown, not stored. Deciding whether to model it is an open
          schema question.
        </SchemaGapNote>
      </div>

      {/* Per-field confirmation for the numbers that matter. */}
      <div className="mt-3 space-y-2">
        <FieldRow
          label="Basic cost"
          field={basicCost}
          highStakes
          format={(v) => formatINRWithSymbol(v)}
          onConfirm={() => confirm(k("basicCost"))}
          onReject={() => reject(k("basicCost"))}
          onResolve={(v) => resolve(k("basicCost"), v)}
          onEnterManually={(v) => enterManually(k("basicCost"), v)}
          parse={parseNumber}
          inputHint="Rupees, e.g. 12000000.00"
        />
        <FieldRow
          label="Advertised value"
          help="What the work was advertised at. This is not what the contractor was paid."
          field={advertised}
          highStakes
          format={(v) => formatINRWithSymbol(v)}
          onConfirm={() => confirm(k("advertisedValue"))}
          onReject={() => reject(k("advertisedValue"))}
          onResolve={(v) => resolve(k("advertisedValue"), v)}
          onEnterManually={(v) => enterManually(k("advertisedValue"), v)}
          parse={parseNumber}
          inputHint="Rupees, e.g. 10800000.00"
        />
        <FieldRow
          label="Bid percentage below"
          field={bidPct}
          highStakes
          format={(v) => pct(v)}
          onConfirm={() => confirm(k("bidBelowPct"))}
          onReject={() => reject(k("bidBelowPct"))}
          onResolve={(v) => resolve(k("bidBelowPct"), v)}
          onEnterManually={(v) => enterManually(k("bidBelowPct"), v)}
          parse={parseNumber}
          inputHint="Percent, e.g. 45 for 45.00 % below"
        />
        <FieldRow
          label="Schedule bid amount"
          field={bidAmount}
          highStakes
          format={(v) => formatINRWithSymbol(v)}
          onConfirm={() => confirm(k("bidAmount"))}
          onReject={() => reject(k("bidAmount"))}
          onResolve={(v) => resolve(k("bidAmount"), v)}
          onEnterManually={(v) => enterManually(k("bidAmount"), v)}
          parse={parseNumber}
          inputHint="Rupees, e.g. 5940000.00"
        />
      </div>
    </section>
  );
}

export function Step2Pricing({
  contract,
  onSelectContract,
}: {
  contract: ContractFixture;
  onSelectContract: (id: string) => void;
}) {
  const overrides = useFieldOverrides();
  const { effective, confirm, reject, resolve, enterManually } = overrides;
  const k = (field: string) => `${contract.id}:${field}`;

  const gross = grossOfferValue(contract);
  const advertisedTotal = totalAdvertised(contract);
  const rebate = effective(k("overallRebatePct"), contract.overallRebatePct);
  const net = netOfferValue(contract);
  const rebateAmount = gross - net;

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Contract and pricing"
        description="Every number below came from a document, and every one of them is inspectable. Confirm them field by field, or accept a whole schedule at once. Nothing is written until the last step."
        aside={
          <label className="flex flex-col items-end gap-1 rounded-lg border border-dashed border-violet-300 bg-violet-50 px-2.5 py-1.5">
            <span className="text-[10px] font-medium uppercase tracking-wider text-violet-800">
              Wireframe control — not part of the screen
            </span>
            <select
              value={contract.id}
              onChange={(e) => onSelectContract(e.target.value)}
              className="rounded border border-violet-200 bg-white px-2 py-1 text-[12px] text-slate-800"
            >
              {CONTRACT_FIXTURES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-violet-700">
              Swaps the sample contract so both shapes are reviewable
            </span>
          </label>
        }
      />

      <p className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-[12px] leading-5 text-slate-600">
        {contract.blurb}
      </p>

      <datalist id="rate-source-suggestions">
        {RATE_SOURCE_SUGGESTIONS.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>

      {/* Contract identity */}
      <div className="grid gap-2 sm:grid-cols-2">
        <FieldRow
          label="Tender number"
          field={effective(k("tenderNumber"), contract.tenderNumber)}
          format={(v) => v}
          onConfirm={() => confirm(k("tenderNumber"))}
          onReject={() => reject(k("tenderNumber"))}
          onResolve={(v) => resolve(k("tenderNumber"), v)}
          onEnterManually={(v) => enterManually(k("tenderNumber"), v)}
          parse={parseText}
          inputHint="e.g. TA-24-25-101"
        />
        <FieldRow
          label="Contractor"
          field={effective(k("contractorName"), contract.contractorName)}
          format={(v) => v}
          onConfirm={() => confirm(k("contractorName"))}
          onReject={() => reject(k("contractorName"))}
          onResolve={(v) => resolve(k("contractorName"), v)}
          onEnterManually={(v) => enterManually(k("contractorName"), v)}
          parse={parseText}
          inputHint="As printed on the LOA"
        />
        <FieldRow
          label="Base month"
          help="Quarter 1 is the month after the base month. Every quarter in every calculation is counted from here."
          field={effective(k("baseMonth"), contract.baseMonth)}
          highStakes
          format={(v) => v}
          onConfirm={() => confirm(k("baseMonth"))}
          onReject={() => reject(k("baseMonth"))}
          onResolve={(v) => resolve(k("baseMonth"), v)}
          onEnterManually={(v) => enterManually(k("baseMonth"), v)}
          parse={parseText}
          inputHint="YYYY-MM, e.g. 2024-12"
        />
        <FieldRow
          label="Railway zone"
          field={effective(k("railwayZone"), contract.railwayZone)}
          format={(v) => v}
          onConfirm={() => confirm(k("railwayZone"))}
          onReject={() => reject(k("railwayZone"))}
          onResolve={(v) => resolve(k("railwayZone"), v)}
          onEnterManually={(v) => enterManually(k("railwayZone"), v)}
          parse={parseText}
          inputHint="e.g. WR, CR, JRH"
        />
      </div>

      {/* Schedules — count is variable, so these stack rather than sitting in columns. */}
      <div className="space-y-3">
        {contract.schedules.map((s) => (
          <ScheduleCard
            key={s.id}
            schedule={s}
            contractId={contract.id}
            overrides={overrides}
          />
        ))}
      </div>

      {/* Contract level. The rebate lives HERE, one level above the schedules. */}
      <section className="rounded-xl border-2 border-slate-300 bg-white p-4">
        <h3 className="text-[13px] font-semibold text-slate-900">
          Contract level — offer value
        </h3>
        <p className="mt-0.5 text-[11px] leading-4 text-slate-500">
          The overall rebate applies to the gross total of all schedules. It does not touch any
          item rate, and it is not the same thing as a schedule&rsquo;s bid percentage.
        </p>

        <div className="mt-3 space-y-1.5">
          <ChainStep caption={`Gross offer value — sum of ${contract.schedules.length} schedules`}>
            <span className="font-mono text-[14px] tabular-nums text-slate-900">
              {formatINRWithSymbol(gross)}
            </span>
            <p className="mt-0.5 text-[11px] text-slate-500">
              {contract.schedules
                .map((s) => formatINRWithSymbol(s.bidAmount.value))
                .join("  +  ")}
            </p>
          </ChainStep>

          <Arrow
            label={
              (rebate.value ?? 0) === 0
                ? "rebate on gross value 0.00 % — no reduction"
                : `rebate on gross value ${pct(rebate.value ?? 0)} = −${formatINRWithSymbol(rebateAmount)}`
            }
          />

          <ChainStep caption="Net offer value — this is the accepted value" emphasis>
            <span className="font-mono text-[16px] tabular-nums">
              {formatINRWithSymbol(net)}
            </span>
          </ChainStep>
        </div>

        <div className="mt-3">
          <FieldRow
            label="Rebate on gross value"
            help="Applies once, to the gross schedule total."
            field={rebate}
            highStakes
            format={(v) => pct(v)}
            onConfirm={() => confirm(k("overallRebatePct"))}
            onReject={() => reject(k("overallRebatePct"))}
            onResolve={(v) => resolve(k("overallRebatePct"), v)}
            onEnterManually={(v) => enterManually(k("overallRebatePct"), v)}
            parse={parseNumber}
            inputHint="Percent, e.g. 2.75 — or 0 if the statement says 0.00"
          />
        </div>

        {/* Advertised and accepted, side by side and never conflated. */}
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
            <p className="text-[10.5px] font-medium uppercase tracking-wider text-slate-500">
              Total advertised value
            </p>
            <p className="mt-0.5 font-mono text-[16px] tabular-nums text-slate-900">
              {formatINRWithSymbol(advertisedTotal)}
            </p>
            <p className="mt-1 text-[11px] leading-4 text-slate-500">
              What the work was put out at, before any bid percentage.
            </p>
          </div>
          <div className="rounded-lg border border-slate-900 bg-slate-900 px-3 py-2.5 text-white">
            <p className="text-[10.5px] font-medium uppercase tracking-wider text-slate-300">
              Accepted value
            </p>
            <p className="mt-0.5 font-mono text-[16px] tabular-nums">
              {formatINRWithSymbol(net)}
            </p>
            <p className="mt-1 text-[11px] leading-4 text-slate-300">
              What the contract was awarded at. This is the figure that bills draw against.
            </p>
          </div>
        </div>
      </section>

      <ManualEntryEscape label="Reject all of this and fill the contract form by hand" />
    </div>
  );
}
