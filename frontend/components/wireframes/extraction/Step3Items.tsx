"use client";

import { Button } from "@/components/ui/Button";
import { formatINR } from "@/lib/format";
import { cn } from "@/lib/cn";
import {
  ITEM_FIXTURES,
  isBlocking,
  type SteelSubtype,
} from "@/lib/wireframes/extraction";
import {
  BlockedCallout,
  ConfidenceDot,
  LowConfidenceCallout,
  ManualEntryEscape,
  SectionHeading,
  SourceChip,
  StateBadge,
} from "@/components/wireframes/Primitives";
import { useFieldOverrides } from "@/components/wireframes/useFieldOverrides";

const STEEL_LABEL: Record<Exclude<SteelSubtype, null>, string> = {
  angles: "Angles",
  plates: "Plates",
  tmt: "TMT bars",
  other: "Other steel",
};

const STEEL_OPTIONS: SteelSubtype[] = [null, "angles", "plates", "tmt", "other"];

function steelText(v: SteelSubtype): string {
  return v === null ? "Not a steel item" : STEEL_LABEL[v];
}

export function Step3Items() {
  const { effective, confirm, reject, resolve } = useFieldOverrides();

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Items and classification"
        description="The item master proposed from the schedule BOQ. Cement and steel classification decides which PVC bucket a line lands in, so each one is confirmed here — once, on the item master, never again per bill."
      />

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] text-[12px]">
          <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Code</th>
              <th className="px-3 py-2 text-left font-medium">Description</th>
              <th className="px-3 py-2 text-right font-medium">Qty</th>
              <th className="px-3 py-2 text-right font-medium">Base rate</th>
              <th className="px-3 py-2 text-right font-medium">Agreement rate</th>
            </tr>
          </thead>
          <tbody>
            {ITEM_FIXTURES.map((item) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono text-slate-800">{item.code}</td>
                <td className="px-3 py-2 text-slate-700">{item.description}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-700">
                  {item.originalQty} {item.unit}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-700">
                  {formatINR(item.baseRate)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-700">
                  {formatINR(item.agreementRate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3">
        {ITEM_FIXTURES.map((item) => {
          const cementKey = `${item.id}:isCement`;
          const steelKey = `${item.id}:steelSubtype`;
          const cement = effective(cementKey, item.isCement);
          const steel = effective(steelKey, item.steelSubtype);
          const blocked = isBlocking(cement.state) || isBlocking(steel.state);

          return (
            <section
              key={item.id}
              className={cn(
                "rounded-xl border p-4",
                blocked ? "border-red-200 bg-red-50/40" : "border-slate-200 bg-white",
              )}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[13px] font-semibold text-slate-900">
                  <span className="font-mono">{item.code}</span> — {item.description}
                </h3>
                <span className="text-[11px] text-slate-500">
                  {item.originalQty} {item.unit}
                </span>
              </div>

              {blocked && (
                <div className="mt-2">
                  <BlockedCallout title="This item cannot be classified from the documents">
                    {cement.note ?? steel.note}
                  </BlockedCallout>
                </div>
              )}

              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {/* Cement */}
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[12px] font-medium text-slate-700">Cement item</span>
                    <StateBadge state={cement.state} />
                  </div>
                  <div className="mt-1.5 flex gap-1.5">
                    {[true, false].map((choice) => {
                      const active = cement.value === choice;
                      return (
                        <button
                          key={String(choice)}
                          type="button"
                          onClick={() => resolve(cementKey, choice)}
                          className={cn(
                            "rounded-md border px-2.5 py-1 text-[12px] transition-colors",
                            active
                              ? "border-slate-900 bg-slate-900 text-white"
                              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-100",
                          )}
                        >
                          {choice ? "Yes" : "No"}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-1.5 space-y-1">
                    <SourceChip source={cement.source} />
                    {cement.state === "proposed" && (
                      <ConfidenceDot confidence={cement.confidence} />
                    )}
                  </div>
                </div>

                {/* Steel subtype */}
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[12px] font-medium text-slate-700">Steel subtype</span>
                    <StateBadge state={steel.state} />
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {STEEL_OPTIONS.map((choice) => {
                      const active = steel.value === choice;
                      return (
                        <button
                          key={String(choice)}
                          type="button"
                          onClick={() => resolve(steelKey, choice)}
                          className={cn(
                            "rounded-md border px-2.5 py-1 text-[12px] transition-colors",
                            active
                              ? "border-slate-900 bg-slate-900 text-white"
                              : "border-slate-200 bg-white text-slate-700 hover:bg-slate-100",
                          )}
                        >
                          {steelText(choice)}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-1.5 space-y-1">
                    <SourceChip source={steel.source} />
                    {steel.state === "proposed" && (
                      <ConfidenceDot confidence={steel.confidence} />
                    )}
                  </div>
                </div>
              </div>

              {steel.state === "proposed" && steel.confidence === "low" && steel.note && (
                <div className="mt-2">
                  <LowConfidenceCallout>{steel.note}</LowConfidenceCallout>
                </div>
              )}

              {cement.value === true && steel.value !== null && (
                <div className="mt-2">
                  <BlockedCallout title="Cement and steel cannot both be set on one item">
                    Each routes the line to a different PVC bucket. Pick one.
                  </BlockedCallout>
                </div>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={blocked}
                  onClick={() => {
                    confirm(cementKey);
                    confirm(steelKey);
                  }}
                >
                  Confirm this item
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    reject(cementKey);
                    reject(steelKey);
                  }}
                >
                  Classify by hand later
                </Button>
              </div>
            </section>
          );
        })}
      </div>

      <ManualEntryEscape label="Discard these proposals — build the item master by hand" />
    </div>
  );
}
