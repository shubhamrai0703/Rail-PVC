import Link from "next/link";
import { ArrowRight } from "lucide-react";

const WIREFRAMES = [
  {
    href: "/wireframes/extraction",
    title: "Document-assisted prefill",
    blurb:
      "Five screens: upload and classify, contract and pricing confirmation, items and classification, bill bundle intake, reconciliation. Extraction proposes; a human confirms; nothing writes until every check passes.",
    context: "tasks/handoffs/2026-07-25-shubham-extraction-wireframe.md",
  },
  {
    href: "/wireframes/journey",
    title: "Guided journey",
    blurb:
      "A response to the recurring review feedback that it is not clear where to start or what to do next. Landing page, data-derived stage state, and setup separated from the repeating bill cycle.",
    context: "Reviewer feedback, 2026-07-25",
  },
];

export default function WireframesIndexPage() {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">Wireframes</h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-6 text-slate-500">
          Design artefacts, not features. Every screen here runs on static fixtures — no API
          calls, no writes, and no real contractor data. These routes do not exist in production
          builds.
        </p>
      </header>

      <ul className="grid gap-3 sm:grid-cols-2">
        {WIREFRAMES.map((w) => (
          <li key={w.href}>
            <Link
              href={w.href}
              className="group flex h-full flex-col rounded-xl border border-slate-200 bg-white px-4 py-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-[14px] font-semibold text-slate-900">{w.title}</h2>
                <ArrowRight
                  className="h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform group-hover:translate-x-0.5"
                  strokeWidth={1.75}
                />
              </div>
              <p className="mt-1 flex-1 text-[12px] leading-5 text-slate-600">{w.blurb}</p>
              <p className="mt-2 font-mono text-[10.5px] text-slate-400">{w.context}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
