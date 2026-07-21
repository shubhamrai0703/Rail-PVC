"use client";

import type { ReactNode } from "react";
import {
  JOURNEY_STAGES,
  type JourneyStageId,
} from "../../lib/firstUserHelp";

export function JourneyGuide({ stage }: { stage: JourneyStageId }) {
  return (
    <nav
      aria-label="Contract to PVC journey"
      className="rounded-xl border border-slate-200 bg-white px-4 py-3"
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-500">
        Contract to PVC journey
      </p>
      <NumberedStageGuide
        ariaLabel="PVC journey stages"
        items={JOURNEY_STAGES}
        currentId={stage}
        className="sm:grid-cols-3 xl:grid-cols-6"
      />
    </nav>
  );
}

export function NumberedStageGuide({
  ariaLabel,
  items,
  currentId,
  className = "",
}: {
  ariaLabel: string;
  items: readonly { id: string; label: string }[];
  currentId?: string;
  className?: string;
}) {
  return (
    <ol
      aria-label={ariaLabel}
      className={`grid grid-cols-2 gap-2 ${className}`}
    >
      {items.map((item, index) => {
        const active = item.id === currentId;
        return (
          <li
            key={item.id}
            aria-current={active ? "step" : undefined}
            className={
              "flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-[12px] " +
              (active
                ? "bg-amber-50 font-medium text-amber-900 ring-1 ring-amber-200"
                : "bg-slate-50 text-slate-500")
            }
          >
            <span
              aria-hidden="true"
              className={
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] " +
                (active
                  ? "bg-amber-600 text-white"
                  : "border border-slate-300 bg-white text-slate-500")
              }
            >
              {index + 1}
            </span>
            <span className="min-w-0 whitespace-normal leading-4">
              {item.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function PageGuidance({
  title,
  children,
  next,
}: {
  title: string;
  children: ReactNode;
  next?: ReactNode;
}) {
  return (
    <section
      aria-label={`${title} guidance`}
      className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
    >
      <h2 className="text-[13px] font-medium text-slate-900">{title}</h2>
      <div className="mt-1 text-[12px] leading-5 text-slate-600">{children}</div>
      {next && (
        <div className="mt-2 border-t border-slate-200 pt-2 text-[12px] text-slate-700">
          <span className="font-medium">Next:</span> {next}
        </div>
      )}
    </section>
  );
}

export function SupplementaryHelp({
  summary = "Why this matters",
  children,
}: {
  summary?: string;
  children: ReactNode;
}) {
  return (
    <details className="mt-1 text-[11px] leading-4 text-slate-500">
      <summary className="w-fit cursor-pointer rounded text-slate-600 underline decoration-slate-300 underline-offset-2 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2">
        {summary}
      </summary>
      <div className="mt-1 max-w-prose text-slate-500">{children}</div>
    </details>
  );
}

export function ExcelFieldGuide() {
  return (
    <ul className="list-disc space-y-1 pl-4">
      <li>
        <span className="font-medium">Original quantity</span> is the
        tender/agreement quantity, often “Agreement Qty” in Excel.
      </li>
      <li>
        <span className="font-medium">Base rate</span> is the published DSR/NS
        schedule rate before bid discount.
      </li>
      <li>
        <span className="font-medium">Agreement rate</span> is the accepted
        billing rate after the schedule discount.
      </li>
      <li>
        Cement and steel subtype must never both be set on one item because
        each routes the bill line to a different PVC bucket.
      </li>
    </ul>
  );
}
